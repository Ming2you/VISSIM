"""Two independent full AD sweeps then verify guarded cache binding of one."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import copy,ctypes,hashlib,json,pickle,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=HERE/'cap_ad_v2'
OUT.mkdir(exist_ok=False)
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),PYTHONDONTWRITEBYTECODE='1')
k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
from evaluation.controllers.sdmpc_tangent_surrogate import Query,validate_prediction
from evaluation.controllers.sdmpc_response_cache import validate_binding
from evaluation.controllers.sdmpc_tangent import _evaluate_single
request=pickle.loads((HERE/'cap_probe2400_verified_env/request.pickle').read_bytes())
# Explicitly repin only this reviewed cache patch. Every other saved source must
# still match; the worker enforces the resulting full manifest on each run.
repinned={}
for name,expected in request['bootstrap']['runtime_sources'].items():
    path=Path(name);observed=hashlib.sha256(path.read_bytes()).hexdigest()
    if observed!=expected:
        before=HERE/'before'/path.name
        assert path.parent==ROOT/'evaluation/controllers' and before.is_file()
        assert hashlib.sha256(before.read_bytes()).hexdigest()==expected
        request['bootstrap']['runtime_sources'][name]=observed
        repinned[name]=dict(before=expected,after=observed)
(HERE/'cap_ad_source_pins.json').write_text(json.dumps(repinned,indent=2)+'\n',encoding='utf8')
request['owned'][0].cfg.network.sdmpc_options['response_cap_cache']=True
query=Query(request,lambda *a:None,lambda *a,**kw:None)
base=copy.deepcopy(request['action']);other=copy.deepcopy(base);other.N_UF_star+=1000.
receipts=[];rows=[]
for label,action in [('original',base),('larger_cap',other)]:
    r=copy.deepcopy(request);r.update(action=action,surrogate_evaluation='ad',reverse_worker_limit=2,
                                    surrogate_context_sha256=query.context_token)
    begin=time.perf_counter();result=_evaluate_single(r);elapsed=time.perf_counter()-begin
    assert not result['fallback_reasons'] and len(result['ad_axes'])==len(r['axes'])
    validate_prediction(result['surrogate_prediction'],action,query.context_token)
    receipts.append(result);rows.append(dict(label=label,seconds=elapsed,axes=len(r['axes'])))
    (OUT/f'{label}.pickle').write_bytes(pickle.dumps(result,protocol=5))
    print(label,rows[-1],flush=True)
for key in ('costs','resources','cost_jacobian','resource_jacobian'):
    assert receipts[0][key]==receipts[1][key],key
for key in ('names','values','jacobian','scope'):
    assert receipts[0]['central_physical'][key]==receipts[1]['central_physical'][key],key
def physical(item):return {k:v for k,v in item.items() if k not in ('action_token','response_token')}
assert physical(receipts[0]['surrogate_prediction'])==physical(receipts[1]['surrogate_prediction'])
calls=[]
def once(r):
    calls.append(1);assert len(calls)==1
    return copy.deepcopy(receipts[0])
query.runner=once
q0=query.evaluate([base],derivatives=True)[0]
begin=time.perf_counter();q1=query.evaluate([other],derivatives=True)[0];d1=query.derivative(other);reuse_sec=time.perf_counter()-begin
validate_binding(other,q1)
assert q1['response_token']==q0['response_token'] and query.ad==1 and query.hits==1
for key in ('costs','resources','cost_jacobian','resource_jacobian'):
    assert d1[key]==receipts[1][key],key
for key in ('names','values','jacobian','scope'):
    assert d1['central_physical'][key]==receipts[1]['central_physical'][key],key
out=dict(status='passed',rows=rows,reuse_seconds=reuse_sec,full_ad_exact=True,
         physical_states_costs_quantities_exact=True,cache_stats=query.stats(),
         scope='Same saved2400 state, unchanged actuators, two independently executed full AD predictions. Actual resource values reused; constraint thresholds remain target-specific.')
(OUT/'verification.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print('CAP_AD_VERIFIED',reuse_sec,flush=True)
