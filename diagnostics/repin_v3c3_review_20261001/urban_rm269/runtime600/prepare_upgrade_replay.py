"""Recreate the failed PFO trial from its existing reference AD; zero forecasts."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import importlib.util
import json
import pickle
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=H.parents[2]
OUT=HERE/'upgrade_replay'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
os.environ['NUMSIM_REPO_ROOT']=str(ROOT/'vendor/NumSim-mine')
sys.argv=['verify.py','--at','2400','--out',str(OUT),'--no-prediction',
          '--tuning',str(HERE/'lazy_config.json'),'--decisions',
          'D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29']
spec=importlib.util.spec_from_file_location('upgrade_verifier',H.parent/'urban260/verify.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo
from evaluation.controllers.sdmpc_tangent_surrogate import Query,token
original_main=adapter.main
original_pfo=sdmpc_pfo.solve

def wrapped():
    def audit(reference,coord,policy,options,evaluate,derivative,quantities,budget,emit):
        query=derivative.__self__
        assert isinstance(query,Query) and query.stats()['total_rollouts']==0
        old_request=pickle.loads((HERE/'profile_baseline_v2/request.pickle').read_bytes())
        saved=pickle.loads((HERE/'profile_baseline_v2/result.pickle').read_bytes())
        assert token(old_request['action'])==token(reference)
        assert old_request['axes']==coord.axes
        item=saved['surrogate_prediction']
        historical=json.loads((H/'runtime_pair2400_numericfix/cache_on/unused.joint.json').read_bytes())
        trials=[r for r in historical['selection']['pfo_warm_start']['trial_rows'] if r['iteration']==0]
        target=min((r for r in trials if r['feasible']),key=lambda r:r['owned_cost'])['action_token']
        failed=json.loads((HERE/'lazy_full/unused.joint.json').read_bytes())
        expected=[r['action_token'] for r in failed['physical_response_cache']['rows'] if not r['derivatives']]
        def score(actions,**kwargs):
            if len(actions)==1 and token(actions[0])==token(reference):return [item]
            assert [token(a) for a in actions]==expected,'Changed first PFO proposals'
            chosen=next(a for a in actions if token(a)==target)
            request=pickle.loads(query.template)
            request.update(action=chosen,surrogate_context_sha256=query.context_token)
            (OUT/'request.pickle').write_bytes(pickle.dumps(request,protocol=5))
            (OUT/'prepared.json').write_text(json.dumps(dict(status='prepared',
                target_action_token=target,all_three_proposal_tokens=expected,
                existing_reference_ad_reused=True,new_forecasts=0,full_selections=0,
                reason='Inspect failed scalar-to-AD event-count comparison on the exact accepted first PFO trial'),indent=2)+'\n',encoding='utf8')
            raise verifier.Done()
        return original_pfo(reference,coord,policy,options,score,lambda a:saved,
                            quantities,budget,emit)
    sdmpc_pfo.solve=audit
    return original_main()

adapter.main=wrapped
verifier.main()
