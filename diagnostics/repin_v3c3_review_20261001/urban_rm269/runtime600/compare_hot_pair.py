"""Same-command summary and full cost/resource/state Jacobian comparison."""
import json
from pathlib import Path
import pickle
import sys
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc_tangent_surrogate import check_scalar_upgrade

def main():
    old,new=HERE/'upgrade_replay',HERE/'hot_validation'
    assert json.loads((new/'execution.json').read_bytes())['status']=='complete_pending_comparison'
    assert not (new/'comparison.json').exists()
    evidence={}
    contents={}
    for folder in (old,new):
        contents[folder.name]={m:pickle.loads((folder/(m+'.result.pickle')).read_bytes()) for m in ('scalar','ad')}
    for mode in ('scalar','ad'):
        a,b=contents[old.name][mode],contents[new.name][mode]
        assert 'error' not in a and 'error' not in b
        left=dict(a['surrogate_prediction']);right=dict(b['surrogate_prediction'])
        witnesses=[left.pop('diagnostic_transfer_witness'),right.pop('diagnostic_transfer_witness')]
        # Only the opt-in runtime policy/source identities differ by preparation.
        for item in (left,right):
            item.pop('frozen_context_token')
        check_scalar_upgrade(left,right,1e-7)
        groups=[{tuple(r['key']):r for r in w['groups']} for w in witnesses]
        maximum=0.
        for key in groups[0].keys() | groups[1].keys():
            for field in ('vehicles','ttd_veh','entered_veh'):
                x=groups[0].get(key,{}).get(field,0.);y=groups[1].get(key,{}).get(field,0.)
                assert np.isfinite(x) and np.isfinite(y)
                maximum=max(maximum,abs(x-y))
                assert abs(x-y)<=1e-7+1e-12*max(abs(x),abs(y)),(key,field,x,y)
        assert witnesses[0]['uncaptured_count']==witnesses[1]['uncaptured_count']
        evidence[mode]=dict(physical_summary_equivalent=True,route_clock_max_abs_error=maximum,
                           runtime_stats=b.get('stock_geometry_hotpath'))
    a,b=contents[old.name]['ad'],contents[new.name]['ad']
    assert not b['fallback_reasons'] and a['ad_axes']==b['ad_axes']
    matrices={}
    for name,x,y in [('owner_costs',a['cost_jacobian'],b['cost_jacobian']),
                     ('np_nuf_resources',a['resource_jacobian'],b['resource_jacobian']),
                     ('central_physical_states',a['central_physical']['jacobian'],b['central_physical']['jacobian'])]:
        x,y=np.asarray(x),np.asarray(y)
        assert x.shape==y.shape and np.isfinite(x).all() and np.isfinite(y).all()
        diff=np.abs(x-y)
        assert np.allclose(x,y,atol=1e-7,rtol=1e-10),(name,float(diff.max()))
        matrices[name]=dict(shape=list(x.shape),max_absolute_error=float(diff.max(initial=0.)),equivalent=True)
    assert a['central_physical']['names']==b['central_physical']['names']
    times={folder.name:json.loads((folder/'execution.json').read_bytes())['results'] for folder in (old,new)}
    result=dict(status='equivalent',same_trial=True,physical=evidence,jacobians=matrices,times=times,
                new_predictions=0,full_selections=0,native_runs=0,
                limitations=['One trial, not a complete decision or10min validation.',
                             'Competing native workload can affect observed wall time.',
                             'Read-only assertion graph removed; original physical assertions still execute.'])
    (new/'comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
