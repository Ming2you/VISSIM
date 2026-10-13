"""Bounded offline cap equivalence witness; saved-state initializer, no native run."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'): os.environ[k]='1'
import argparse, copy, hashlib, importlib.util, json, pickle, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
p=argparse.ArgumentParser();p.add_argument('--at',type=int,default=2400);p.add_argument('--tag',default='');a=p.parse_args()
OUT=HERE/f'cap_probe{a.at}{a.tag}'
F=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
T=HERE.parent/'goal8_265/spillback2000/coupling268/config.json'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),PYTHONDONTWRITEBYTECODE='1')
sys.argv=['verify.py','--at',str(a.at),'--out',str(OUT),'--no-prediction','--decisions',str(F),'--tuning',str(T)]
loader=importlib.util.spec_from_file_location('verifier',HERE.parent/'urban260/verify.py')
verify=importlib.util.module_from_spec(loader);loader.loader.exec_module(verify)
from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_pfo
from evaluation.controllers.sdmpc_tangent_surrogate import Query,validate_prediction
from src.models.state import ControlAction
queries=[];query_init=Query.__init__
def capture(self,*args,**kwargs):
    query_init(self,*args,**kwargs);queries.append(self)
Query.__init__=capture
orig_main=adapter.main
def main():
    old=sdmpc_pfo.solve
    def audit(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit):
        try:old(reference,coord,policy,options,evaluate,derivative,quantities,check_budget,emit)
        except verify.Done:pass
        query=queries[-1];request=pickle.loads(query.template)
        cfg=request['owned'][0].cfg
        action=adapter.control_from_json(F/f'action_{a.at:06}.json',cfg,ControlAction)
        coord.validate(action)
        request.update(action=action,surrogate_context_sha256=query.context_token)
        (OUT/'request.pickle').write_bytes(pickle.dumps(request,protocol=5))
        results=[];baseline=None
        for label,delta in [('original',0.),('larger_nuf_cap',1000.)]:
            r=copy.deepcopy(request);r['action'].N_UF_star+=delta;r['surrogate_evaluation']='scalar'
            begin=time.perf_counter();receipt=query.runner(r);item=receipt['surrogate_prediction']
            validate_prediction(item,r['action'],query.context_token)
            comparable={k:v for k,v in item.items() if k not in ('action_token','response_token')}
            if baseline is None: baseline=comparable
            assert comparable==baseline, 'NUF cap changed physical prediction'
            results.append(dict(label=label,seconds=time.perf_counter()-begin,cap=r['action'].N_UF_star,
                objective=item['objective_veh_h'],exact_physical_response_equal=True))
            print(label,results[-1],flush=True)
        (OUT/'cap_equivalence.json').write_text(json.dumps(dict(rows=results,
            scope='Independently executed continuous-model scalar responses. Every exported physical state, cost, quantity and audit field exact; action identity excluded.',
            tuning=str(T),tuning_sha256=hashlib.sha256(T.read_bytes()).hexdigest()),indent=2)+'\n',encoding='utf8')
        raise verify.Done()
    sdmpc_pfo.solve=audit
    return orig_main()
adapter.main=main
verify.main()
