"""Inspect retained trial evidence once, without additional predictions."""
import importlib.util
import json
import math
from pathlib import Path
import pickle
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
OUT=HERE/'upgrade_replay'
spec=importlib.util.spec_from_file_location('runtime_comparator',HERE.parent/'runtime_pair2400_numericfix/compare.py')
compare=importlib.util.module_from_spec(spec);spec.loader.exec_module(compare)

def main():
    receipt=json.loads((OUT/'execution.json').read_bytes())
    assert receipt['status']=='complete_pending_comparison'
    assert not (OUT/'comparison.json').exists()
    data={mode:pickle.loads((OUT/(mode+'.result.pickle')).read_bytes()) for mode in ('scalar','ad')}
    responses={m:data[m]['surrogate_prediction'] for m in data}
    witness={m:responses[m].pop('diagnostic_transfer_witness') for m in data}
    for m in responses:
        for key in ('action_token','response_token'):responses[m].pop(key)
    groups={m:{tuple(row['key']):{k:row[k] for k in ('vehicles','ttd_veh','entered_veh')}
               for row in witness[m]['groups']} for m in data}
    assert all(len(groups[m])==len(witness[m]['groups']) for m in data)
    changed=[];max_error=0.;missing=[]
    for key in groups['scalar'].keys() | groups['ad'].keys():
        a=groups['scalar'].get(key,dict(vehicles=0.,ttd_veh=0.,entered_veh=0.))
        b=groups['ad'].get(key,dict(vehicles=0.,ttd_veh=0.,entered_veh=0.))
        if key not in groups['scalar'] or key not in groups['ad']:
            missing.append(dict(key=list(key),scalar=a,ad=b))
        for metric in a:
            assert math.isfinite(a[metric]) and math.isfinite(b[metric])
            error=abs(a[metric]-b[metric]);max_error=max(max_error,error)
            if not math.isclose(a[metric],b[metric],rel_tol=1e-12,abs_tol=1e-7):
                changed.append(dict(key=list(key),metric=metric,scalar=a[metric],ad=b[metric],absolute_error=error))
    counts={m:dict(event_count=responses[m]['control_area']['event_count'],
                  captured_count=witness[m]['captured_count'],uncaptured_count=witness[m]['uncaptured_count'],
                  grouped_records=len(groups[m])) for m in data}
    prefix_equal=counts['scalar']['uncaptured_count']==counts['ad']['uncaptured_count']
    count_identity=all(v['event_count']==v['captured_count']+v['uncaptured_count'] for v in counts.values())
    differences=compare.difference(responses['scalar'],responses['ad'])
    non_counter=[r for r in differences if r['path']!='/control_area/event_count']
    result=dict(status='sparse_record_count_only' if not changed and not non_counter and prefix_equal and count_identity
                else 'additional_differences_require_review',
                counts=counts,event_count_identity=count_identity,uncaptured_prefix_equal=prefix_equal,
                route_clock_max_absolute_amount_error=max_error,material_route_clock_differences=changed,
                missing_route_clock_groups=missing,response_differences=differences,
                response_differences_excluding_verified_event_counter=non_counter,
                costs={m:data[m]['costs'] for m in data},times=receipt['results'],
                new_forecasts=0,new_optimizations=0,new_native_runs=0,
                scope='One exact failed PFO trial. No equality check was relaxed to produce these records.')
    (OUT/'comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','counts','route_clock_max_absolute_amount_error','response_differences')},ensure_ascii=False))
if __name__=='__main__':main()
