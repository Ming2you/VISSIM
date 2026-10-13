"""One unchanged FW5/urban1 full450s regression after receipt API changes."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import hashlib,json,pickle,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];M=HERE.parent/'multirate271'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
def main():
    receipt=HERE/'default_execution.json';assert not receipt.exists()
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    previous=json.loads((HERE.parent/'urban_clock275/plan.json').read_bytes())
    pins=dict(previous['source_pins'])
    for backup in HERE.glob('*.py.before'):
        rel='evaluation/controllers/'+backup.name[:-7]
        if rel in pins:assert sha(backup)==pins[rel],rel
        pins[rel]=sha(ROOT/rel)
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    request=pickle.loads((M/'macro_hold_ad_v3_request.pickle').read_bytes())
    for p,h in request['bootstrap']['runtime_sources'].items():
        actual=sha(Path(p))
        if actual!=h:
            assert pins[Path(p).relative_to(ROOT).as_posix()]==actual,p
            request['bootstrap']['runtime_sources'][p]=actual
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    request['surrogate_evaluation']='scalar'
    request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    src=HERE/'default_request.pickle';dst=HERE/'default_result.pickle';src.write_bytes(pickle.dumps(request,protocol=5))
    record=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),source_pins=pins,
                full_rollouts=1,full_sdmpc_selections=0,native_runs=0)
    save(receipt,record);t0=time.perf_counter()
    with (HERE/'default_stdout.log').open('w') as out,(HERE/'default_stderr.log').open('w') as err:
        child=subprocess.Popen([sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),str(src),str(dst),sha(src),'reverse-v1'],
            cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS|subprocess.CREATE_NO_WINDOW)
        record['child_pid']=child.pid;save(receipt,record);code=child.wait()
    record.update(exit_code=code,wall_sec=time.perf_counter()-t0)
    if code:
        record['status']='failed_preserved';save(receipt,record);return code
    old=pickle.loads((M/'macro_hold_v2_result.pickle').read_bytes());new=pickle.loads(dst.read_bytes())
    errors={k:max(abs(a-b) for a,b in zip(new[k],old[k])) for k in ('costs','resources')}
    a,b=[r['surrogate_prediction']['central_physical'] for r in (new,old)]
    assert a['names']==b['names']
    errors['states']=max(abs(x-y) for x,y in zip(a['values'],b['values']))
    assert max(errors.values())<1e-7,errors
    prediction=new['surrogate_prediction']
    assert prediction['conditional_model_feasibility_witness'] and prediction['model_constraint_coverage']['complete']
    assert prediction['resource_summary']['max_exceedance_veh']<1e-7
    assert all(sha(ROOT/p)==h for p,h in pins.items())
    record.update(status='complete_reviewed',max_errors=errors,physical_states=len(a['names']))
    save(receipt,record);print(json.dumps({k:v for k,v in record.items() if k!='source_pins'}))
    return 0
if __name__=='__main__':raise SystemExit(main())
