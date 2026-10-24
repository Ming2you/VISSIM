"""One fixed previous selected command under freeway5; no re-optimization."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from datetime import datetime,timezone
import hashlib,json,pickle,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def main():
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_sequence as seq
    from evaluation.controllers.sdmpc_tangent_surrogate import token
    from src.models.state import ControlAction
    receipt=HERE/'previous_choice_execution.json'
    assert not receipt.exists(),'No duplicate or automatic retry'
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent))
    request=pickle.loads((HERE/'macro_hold_ad_v3_request.pickle').read_bytes())
    old=HERE.parent/'full2400_lane_offer/unused.json'
    current=json.loads((HERE/'plan.json').read_bytes())['source_pins']
    changed=[]
    for path,expected in request['bootstrap']['runtime_sources'].items():
        p=Path(path);now=sha(p)
        if now!=expected:
            assert p.relative_to(ROOT).as_posix() in current,path
            assert now==current[p.relative_to(ROOT).as_posix()]
            changed.append(path)
            request['bootstrap']['runtime_sources'][path]=now
    cfg=request['owned'][0].cfg
    action=adapter.control_from_json(old,cfg,ControlAction)
    assert len(seq.actions(action,3))==3 and cfg.simulation.T_f_sec==5
    request['action']=action
    request['surrogate_evaluation']='scalar'
    request['surrogate_context_sha256']=token((request['owned'],request['runtime'],request['bootstrap'],request['horizon']))
    src=HERE/'previous_choice_request.pickle';dst=HERE/'previous_choice_result.pickle'
    src.write_bytes(pickle.dumps(request,protocol=5))
    record=dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        action_source=str(old),action_sha256=sha(old),input_sha256=sha(src),changed_sources=changed,
        max_predictions=1,optimizations=0,native_runs=0,retries=0,
        source_pins=request['bootstrap']['runtime_sources'])
    save(receipt,record);start=time.perf_counter()
    with (HERE/'previous_choice_stdout.log').open('w') as out,(HERE/'previous_choice_stderr.log').open('w') as err:
        child=subprocess.Popen([sys.executable,'-B',str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),str(src),str(dst),sha(src),'reverse-v1'],
            cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        record['child_pid']=child.pid;save(receipt,record)
        code=child.wait()
    record.update(status='complete_pending_review' if code==0 else 'failed_preserved',exit_code=code,
        wall_sec=time.perf_counter()-start,source_pins_unchanged=all(sha(Path(p))==h for p,h in record['source_pins'].items()))
    save(receipt,record)
    return code


if __name__=='__main__':raise SystemExit(main())
