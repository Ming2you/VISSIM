"""Check three bounded forecasts against already closed native observations."""
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from qualify_native2400 import validate_scope
from evaluation.controllers import obs150_contract as oc

read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=HERE/'assessment.json'
    assert not out.exists()
    native=read(H/'native2400_assessment.json')
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    before=read(H/'sc6_queue/assessment.json')
    source=read(H/'sc12_source/assessment.json')
    summary=read(HERE/'forecast2400_checked/summary.json')
    assert summary['status']=='complete' and summary['forecasts']==2
    late=read(HERE/'forecast3300/summary.json')
    assert late['status']=='complete' and late['forecasts']==1 and late['depth']==1
    for report in (summary,late):
        assert report['native_runs']==report['optimizer_calls']==0 and not report['future_observation_inputs']
        for path,digest in report['source_pins'].items(): assert sha(Path(path))==digest,path
    results=summary['results']
    delta=results['selected']['omega_ttt_veh_h']-results['hold']['omega_ttt_veh_h']
    fw_delta=sum(results['selected']['costs_by_stock'].get(k,0)-v
                 for k,v in results['hold']['costs_by_stock'].items() if k.startswith('freeway:'))
    merge_delta=results['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-results['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']
    heads={}
    for arm,r in results.items():
        assert r['resource_max_exceedance'] < 1e-7 and r['writer_validated'] and r['conservation_states']==4
        heads[arm]={}
        for group in ('SC12_S','SC6_S'):
            actual=[w['heads'][group]['crossings'] for w in source['native_path_witnesses'][arm]]
            predicted=[sum(b['by_movement'].values()) for b in r['local'][group]['bins']]
            if group=='SC6_S':
                prior=before['pair2400']['service']['SC6_south_head'][arm]['predicted_all']
                prior_label='previous_sc6_queue_service'
            else:
                prior=[sum(v for m,v in b['sc12_movement_departures_veh'].items() if m.startswith('movement:SC12_S_SC16_')) for b in source['model'][arm]]
                prior_label='original_pre_sc6_queue_service'
            heads[arm][group]=dict(actual=actual,previous=prior,previous_label=prior_label,predicted=predicted,
                previous_absolute_error_sum=sum(abs(a-b) for a,b in zip(actual,prior)),
                absolute_error_sum=sum(abs(a-b) for a,b in zip(actual,predicted)))
    raw_path=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29/state_003450.json')
    bundle=oc.load_bundle(read(raw_path))
    ds,_=oc.read_detector_csv(bundle.obs['detector_config']['path'],bundle.obs['detector_config']['sha256'])
    oc.validate_raw(bundle.obs,ds,expected_simres=10)
    boundaries=oc.evaluate_boundaries(bundle.obs,ds,bundle.frame_end,bundle.frame_start,bundle.err_rows)
    later={}
    for group,link in [('SC6_S',1210018302),('SC12_S',1210012700),('SC16_S',1210009503)]:
        counters={str(d.lane):boundaries[d.boundary_ref].cross for d in ds if d.role=='head' and d.link==link}
        assert len(counters)==4,(group,counters)
        predicted=sum(late['results']['applied']['local'][group]['bins'][0]['by_movement'].values())
        later[group]=dict(actual=sum(counters.values()),predicted=predicted,actual_head_by_lane=counters,
                          absolute_error=abs(predicted-sum(counters.values())))
    later['SC6_S']['previous']=before['later3300']['variants']['service']['predicted_all']
    actual=native['delta_omega_veh_h']['actual']
    record=dict(status='bounded_validation_complete',tests_passed=8,forecasts_completed=3,
        coefficients_fitted=0,new_native=0,full_selections=0,
        delta_definition='Selected joint urban/RM command minus held, same Omega701 and common2400state',
        delta_omega_veh_h=dict(actual=actual,previous=before['pair2400']['service']['delta_omega_veh_h'],predicted=delta,
            error=delta-actual,previous_error=before['pair2400']['service']['delta_error_veh_h']),
        delta_mainline_veh_h=dict(actual=native['delta_mainline_veh_h']['actual'],predicted=fw_delta),
        incremental_merge10681_veh=dict(actual=84,predicted=merge_delta),head_departures2400=heads,later3300=later,
        shared_caps_feasible={arm:r['shared_constraints']['feasible'] for arm,r in results.items()},
        calibration_control_gate_passed=False,runtime_pair_launched=False,
        limitations=['3300 is an unused saved state of seed29, not independent seed validation.',
            'Exact native routing agreement does not establish forecast accuracy or whole-controller improvement.',
            'Missing SC12 east head observation and other service/arrival errors remain unresolved.',
            'Original exact-byte-prefix failure retained; newer pair causal/common observation qualification reused.'],
        source_pins={str(p):sha(p) for p in (Path(__file__),HERE/'forecast2400_checked/summary.json',HERE/'forecast3300/summary.json',
            H/'sc6_queue/assessment.json',H/'sc12_source/assessment.json',raw_path)})
    out.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in record.items() if k in ('delta_omega_veh_h','delta_mainline_veh_h','head_departures2400','later3300')},indent=2))

if __name__=='__main__':main()
