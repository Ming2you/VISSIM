"""One existing1s coupled scalar response after optional coarse boundary support."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import ctypes,hashlib,json,pickle,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];BASE=HERE.parent/'route_interval'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8')


def main():
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    receipt_path=HERE/'default_execution.json';assert not receipt_path.exists(),'No duplicate or automatic retry'
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    request=pickle.loads((BASE/'new_hold.pickle').read_bytes());changed=[]
    allowed={'physical_urban_transport.py','physical_ramp_boundary.py','known_wout_causal_response.py',
             'lane_ramp_runtime.py','lane_offramp_runtime.py','lane_coupling.py'}
    for name,old in list(request['bootstrap']['runtime_sources'].items()):
        now=sha(Path(name))
        if now!=old:
            assert Path(name).name in allowed,name
            changed.append(dict(path=name,old=old,new=now));request['bootstrap']['runtime_sources'][name]=now
    new=ROOT/'evaluation/controllers/multirate_ramp_boundary.py'
    request['bootstrap']['runtime_sources'][str(new)]=sha(new)
    request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    request['surrogate_evaluation']='scalar'
    payload=pickle.dumps(request,protocol=5);src=HERE/'default_request.pickle';dst=HERE/'default_result.pickle'
    src.write_bytes(payload)
    receipt=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),changed_sources=changed,
        source_pins={str(p):sha(p) for p in (ROOT/'evaluation/controllers').glob('*.py')})
    save(receipt_path,receipt);started=time.perf_counter()
    cmd=[sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),str(src),str(dst),hashlib.sha256(payload).hexdigest(),'reverse-v1']
    with (HERE/'default_stdout.log').open('w') as stdout,(HERE/'default_stderr.log').open('w') as stderr:
        child=subprocess.Popen(cmd,cwd=ROOT,stdout=stdout,stderr=stderr)
        receipt.update(child_pid=child.pid,child_started_utc=datetime.now(timezone.utc).isoformat());save(receipt_path,receipt)
        code=child.wait()
    receipt.update(exit_code=code,wall_sec=time.perf_counter()-started)
    if code:
        receipt['status']='failed_no_retry';save(receipt_path,receipt);return code
    result=pickle.loads(dst.read_bytes());old=pickle.loads((BASE/'new_hold.scalar.result.pickle').read_bytes())
    errors={}
    for k in ('costs','resources'):
        errors[k]=float(np.max(abs(np.asarray(result[k])-np.asarray(old[k]))));assert errors[k]<1e-7
    r,b=result['surrogate_prediction'],old['surrogate_prediction']
    assert r['central_physical']['names']==b['central_physical']['names']
    errors['central']=float(np.max(abs(np.asarray(r['central_physical']['values'])-np.asarray(b['central_physical']['values']))));assert errors['central']<1e-7
    for k in ('quantities','model_constraint_coverage','resource_summary'):
        assert r[k]==b[k],k
    for p,h in receipt['source_pins'].items():assert sha(Path(p))==h,p
    receipt.update(status='complete_reviewed',max_abs_errors=errors,default_clock_sec=request['owned'][0].cfg.simulation.T_f_sec)
    save(receipt_path,receipt)
    print(json.dumps(dict(status=receipt['status'],errors=errors,wall_sec=receipt['wall_sec'])))
    return 0


if __name__=='__main__':raise SystemExit(main())
