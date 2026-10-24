"""Review the three bounded checks; no additional forecasts or calibration."""
import hashlib
import importlib.util
import json
import pickle
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
R=HERE.parent/'urban_clock277'
M=HERE.parent/'multirate271'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    spec=importlib.util.spec_from_file_location('clock277_review',R/'review_response.py')
    previous=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    rows={}
    for clock,baseline in (('urban1','default_v1'),('urban10','hold_v5')):
        label='vsl110_'+clock
        receipt=read(HERE/(label+'_execution.json'))
        assert receipt['exit_code']==0 and receipt['source_pins_unchanged']
        assert all(sha(path)==digest for path,digest in receipt['source_pins'].items())
        base=previous.row(pickle.loads((R/(baseline+'_result.pickle')).read_bytes()))
        off=previous.row(pickle.loads((HERE/(label+'_result.pickle')).read_bytes()))
        rows[clock]=dict(vsl90=base,vsl110=off,
            delta_90_minus_110_omega_veh_h=base['omega_veh_h']-off['omega_veh_h'],
            owner_deltas={key:base['owner_costs'][key]-off['owner_costs'][key] for key in base['owner_costs']},
            merge_deltas={key:base['merges_veh'][key]-off['merges_veh'][key] for key in base['merges_veh']},
            vsl110_wall_sec=receipt['wall_sec'])
    before=read(M/'unseen3300_fw5_joint2/response_validation.json')
    after=read(HERE/'unseen3300_fw5_urban10/response_validation.json')
    assert read(HERE/'unseen3300_fw5_urban10/completion.json')['status']=='complete'
    assert before['command_pins']==after['command_pins'] and before['target_pins']==after['target_pins']
    assert before['native_stocks']==after['native_stocks'] and before['initial_group_errors']==after['initial_group_errors']
    assert before['native_windows']==after['native_windows']
    assert after['resource_max_exceedance_veh'] < 1e-7
    assert all(sha(path)==digest for path,digest in after['source_pins'].items())
    targets={name:sum(row[name] for row in after['native_windows']) for name in ('arrival','merge','removed')}
    groups={key:dict(native=value['native'],urban1=before['stock_changes'][key]['predicted'],urban10=value['predicted'])
            for key,value in after['stock_changes'].items()}
    response=dict(native=targets,urban1={key:before[key] for key in ('predicted_merge10681','predicted_arrival10681','predicted_omega_ttt_veh_h','wall_sec')},
        urban10={key:after[key] for key in ('predicted_merge10681','predicted_arrival10681','predicted_omega_ttt_veh_h','wall_sec')},
        groups=groups,initial_errors=after['initial_group_errors'])
    report=dict(status='bounded_clock_checks_complete',unseen3300=response,vsl2400=rows,
        vsl_omega_direction_retained=rows['urban1']['delta_90_minus_110_omega_veh_h']*rows['urban10']['delta_90_minus_110_omega_veh_h']>0,
        new_predictions=3,new_full_selections=0,new_fits=0,new_native_runs=0,
        limits=['VSL contrast is model-only same-state timing parity, not VISSIM VSL gain validation.',
                '3300 actual commands are supplied; no claim of common-state causal policy effect.',
                '52+58 inventory direction remains wrong in both clocks. Do not attribute it solely to the larger step.',
                'All evidence is seed29. No independent-seed or full native adoption claim.'])
    (HERE/'review.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(unseen3300=response,vsl={k:{f:r[f] for f in ('delta_90_minus_110_omega_veh_h','owner_deltas','merge_deltas')} for k,r in rows.items()},
        vsl_direction_retained=report['vsl_omega_direction_retained']),ensure_ascii=False))


if __name__=='__main__':main()
