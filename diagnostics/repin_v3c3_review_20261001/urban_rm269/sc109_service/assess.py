"""Evaluate discharge, unused state and whole-area command ranking together."""
import hashlib,json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from qualify_native2400 import validate_scope
from evaluation.controllers import obs150_contract as oc
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NAME='SC109_W_SC108_to_N_SC16'

def main():
    out=HERE/'assessment.json';assert not out.exists()
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    native=read(H/'native2400_assessment.json');old=read(H/'native_beta/assessment.json')
    chain=read(H/'source_chain/assessment.json')
    current=read(HERE/'forecast2400/summary.json');later=read(HERE/'forecast3300/summary.json')
    for r,num,depth in ((current,2,3),(later,1,1)):
        assert r['status']=='complete' and r['forecasts']==num and r['depth']==depth
        assert not r['future_observation_inputs'] and r['optimizer_calls']==r['native_runs']==0
        for p,d in r['source_pins'].items():assert sha(Path(p))==d,p
    arms=current['results']
    delta=arms['selected']['omega_ttt_veh_h']-arms['hold']['omega_ttt_veh_h']
    mainline=sum(arms['selected']['costs_by_stock'].get(k,0)-v for k,v in arms['hold']['costs_by_stock'].items() if k.startswith('freeway:'))
    local={}
    for arm,r in arms.items():
        assert r['writer_validated'] and r['resource_max_exceedance']<1e-7 and r['conservation_states']==4
        previous=read(H/'native_beta/forecast2400_checked'/(arm+'.json'))
        observed=chain['native'][arm]
        a=[sum(x['crossings'] for x in b['heads']['SC109_W']['rows'] if x['lane'] in (4,5)) for b in observed]
        b=[t['by_movement'][NAME] for t in r['local']['SC109_W']['bins']]
        prior=[b['minima'][NAME]['accepted_veh'] for b in chain['model'][arm]]
        local[arm]={'SC109_left':dict(actual=a,previous=prior,predicted=b,
            previous_abs_error=sum(abs(x-y) for x,y in zip(a,prior)),abs_error=sum(abs(x-y) for x,y in zip(a,b)))}
        for group in ('SC16_S','SC12_S','SC6_S'):
            a=[b['heads'][group]['crossings'] for b in observed]
            b=[sum(t['by_movement'].values()) for t in r['local'][group]['bins']]
            prior=[sum(t['by_movement'].values()) for t in previous['local'][group]['bins']]
            local[arm][group]=dict(actual=a,previous=prior,predicted=b,
                previous_abs_error=sum(abs(x-y) for x,y in zip(a,prior)),abs_error=sum(abs(x-y) for x,y in zip(a,b)))
    raw_path=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29/state_003450.json')
    bundle=oc.load_bundle(read(raw_path));ds,_=oc.read_detector_csv(bundle.obs['detector_config']['path'],bundle.obs['detector_config']['sha256'])
    oc.validate_raw(bundle.obs,ds,expected_simres=10)
    boundaries=oc.evaluate_boundaries(bundle.obs,ds,bundle.frame_end,bundle.frame_start,bundle.err_rows)
    actual=sum(boundaries[d.boundary_ref].cross for d in ds if d.role=='head' and d.link==173 and d.lane in (4,5))
    later_result=later['results']['applied']
    previous=read(H/'native_beta/forecast3300/summary.json')['results']['applied']
    # Previous diagnostic did not have an SC109 group; recover its saved transfer ledger.
    import gzip
    with gzip.open(H/'native_beta/forecast3300/applied.response.json.gz','rt',encoding='utf8') as f:response=json.load(f)
    prior_left=sum(t['vehicles'] for t in response['transfers'] if t['source']=='movement:'+NAME and t['target']!=t['source'])
    predicted=later_result['local']['SC109_W']['bins'][0]['by_movement'][NAME]
    detail={'SC109_left':dict(actual=actual,previous=prior_left,predicted=predicted,
        previous_abs_error=abs(prior_left-actual),abs_error=abs(predicted-actual))}
    for group in ('SC16_S','SC12_S','SC6_S'):
        p=sum(later_result['local'][group]['bins'][0]['by_movement'].values())
        a=old['later3300'][group]['actual'];pr=old['later3300'][group]['predicted']
        detail[group]=dict(actual=a,previous=pr,predicted=p,previous_abs_error=abs(pr-a),abs_error=abs(p-a))
    component=read(H/'native2400_analysis/initial_support_cost_diagnostic.json')
    costs=[]
    for row in component['groups']:
        predicted=sum(arms['selected']['costs_by_stock'].get(k,0)-arms['hold']['costs_by_stock'].get(k,0) for k in row['stocks'])
        costs.append(dict(stocks=row['stocks'],links=row['links'],native_delta=row['native_delta'],predicted_delta=predicted,
            error=predicted-row['native_delta']))
    report=dict(status='bounded_validation_complete',tests_passed=28,forecasts=3,new_native=0,new_optimizations=0,coefficients_fitted=0,
        delta_definition='Selected joint city/RM minus held,450seconds,sameOmega701',
        delta_omega_veh_h=dict(actual=native['delta_omega_veh_h']['actual'],previous=old['delta_omega_veh_h']['predicted'],predicted=delta,
            error=delta-native['delta_omega_veh_h']['actual']),
        delta_mainline_veh_h=dict(actual=native['delta_mainline_veh_h']['actual'],predicted=mainline),
        merge10681_added=arms['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']-arms['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'],
        head_departures=local,later3300=detail,shared_caps_feasible={a:r['shared_constraints']['feasible'] for a,r in arms.items()},
        initial_support_cost_scope=component['scope'],cost_diagnostic=costs,
        calibration_control_gate_passed=False,runtime_pair_launched=False,
        source_pins={str(p):sha(p) for p in (Path(__file__),HERE/'forecast2400/summary.json',HERE/'forecast3300/summary.json',
            H/'native_beta/assessment.json',H/'source_chain/assessment.json',raw_path)},
        limitations=['Unused3300 same-seed150s only, not independent-seed joint-command validation.',
          'Past achieved service is not saturation capacity or a guarantee that arrivals/receiving allow future discharge.',
          'Initial support geography is diagnostic and omits unmatched future transit; the exact totalOmega comparison remains separate.'])
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k in ('delta_omega_veh_h','delta_mainline_veh_h','head_departures','later3300','shared_caps_feasible')},indent=2))

if __name__=='__main__':main()
