"""Use the identical retained trial/state; change runtime flag and source pins only."""
import hashlib
import json
from pathlib import Path
import pickle
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.sdmpc import policy_token
from evaluation.controllers.sdmpc_tangent_surrogate import token,check_scalar_upgrade

def save(path,data):path.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
def main():
    trial=HERE/'upgrade_replay'
    assert json.loads((trial/'comparison.json').read_bytes())['status']=='sparse_record_count_only'
    retained=[]
    for name in ('scalar','ad'):
        item=pickle.loads((trial/(name+'.result.pickle')).read_bytes())['surrogate_prediction']
        item.pop('diagnostic_transfer_witness');retained.append(item)
    check_scalar_upgrade(*retained,1e-7)
    save(trial/'fix_validation.json',dict(status='PASS',all_quantitative_summaries_checked=True,
        event_record_counts=[r['control_area']['event_count'] for r in retained],
        new_predictions=0,new_full_selections=0))
    out=HERE/'hot_validation'
    out.mkdir(exist_ok=False)
    request=pickle.loads((trial/'request.pickle').read_bytes())
    policy=request['owned'][0].cfg.network.sdmpc_options
    before=policy_token(policy)
    assert policy['prediction_hotpath'] and policy['compact_audit'] and not policy.get('stock_geometry_hotpath')
    policy['stock_geometry_hotpath']=True
    assert policy_token(policy)==before
    changed=[]
    allowed={'sdmpc.py','sdmpc_tangent_surrogate.py','sdmpc_tangent_worker.py'}
    for name,expected in list(request['bootstrap']['runtime_sources'].items()):
        observed=hashlib.sha256(Path(name).read_bytes()).hexdigest()
        if observed!=expected:
            assert Path(name).name in allowed,name
            changed.append(dict(path=name,before=expected,after=observed))
            request['bootstrap']['runtime_sources'][name]=observed
    module=ROOT/'evaluation/controllers/sdmpc_stock_geometry.py'
    request['bootstrap']['runtime_sources'][str(module)]=hashlib.sha256(module.read_bytes()).hexdigest()
    request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    (out/'request.pickle').write_bytes(pickle.dumps(request,protocol=5))
    config=json.loads((HERE/'lazy_config.json').read_bytes())
    config['adapter']['sdmpc_stock_geometry_hotpath']=True
    save(HERE/'hot_config.json',config)
    pins=dict(request['bootstrap']['runtime_sources'])
    for name in ('sdmpc.py','sdmpc_tangent_surrogate.py','sdmpc_tangent_worker.py','sdmpc_stock_geometry.py',
                 'sdmpc_tangent_transport.py','sdmpc_tangent_spatial.py'):
        path=ROOT/'evaluation/controllers'/name
        pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    save(out/'prepared.json',dict(status='prepared',source_pins=pins,changed_source_pins=changed,
        baseline=str(trial),maximum_predictions=2,maximum_ad_predictions=1,full_selections=0,native_runs=0,
        action_token=token(request['action']),horizon_sec=450,
        only_runtime_policy_change='stock_geometry_hotpath=true',
        compare=['all physical summary fields','all owner/resource and central-state Jacobians','feasibility','wall time']))
    print('Retained upgrade check PASS; stock/geometry pair prepared without forecasts')
if __name__=='__main__':main()
