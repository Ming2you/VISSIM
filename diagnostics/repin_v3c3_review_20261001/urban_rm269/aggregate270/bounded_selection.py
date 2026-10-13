"""One changed-budget comparison; reuse canonical existing1+1 experiment."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time
import traceback

A=Path(__file__).resolve().parent
ROOT=A.parents[3]
OUT=A/'bounded2400_lane_offer'
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf8')


def main():
    assert not OUT.exists(),'No repeated optimization'
    assert not any((p/'STOP').exists() for p in (ROOT,A.parent,A))
    plan=read(A/'bounded_selection_plan.json')
    assert plan['launches_consumed']==0
    baseline=read(A/'full_selection_review.json')
    assert baseline['status']=='one_complete_decision_reviewed' and not baseline['full_time_target_met']
    for p,d in plan['source_pins'].items():assert sha(Path(p))==d,p
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ.update(PYTHONDONTWRITEBYTECODE='1',NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'))
    plan.update(status='running',python_pid=os.getpid(),launches_consumed=1)
    save(A/'bounded_selection_plan.json',plan)
    sys.argv=[str(A.parent/'runtime600/bounded_selection.py'),'--at','2400','--out',str(OUT),
              '--full-selection','--tuning',str(A/'config_dt10.json'),'--decisions',plan['decisions']]
    started=time.perf_counter()
    try:
        runpy.run_path(sys.argv[0],run_name='__main__')
        assert read(OUT/'completion.json')['full_selection']
        for p,d in plan['source_pins'].items():assert sha(Path(p))==d,p
    except BaseException as err:
        plan['status']='failed_preserved';save(A/'bounded_selection_plan.json',plan)
        save(A/'bounded_execution.json',dict(status='failed_preserved',error=repr(err),
             traceback=traceback.format_exc(),elapsed_seconds=time.perf_counter()-started))
        raise
    plan['status']='complete_pending_comparison';save(A/'bounded_selection_plan.json',plan)
    elapsed=time.perf_counter()-started
    save(A/'bounded_execution.json',dict(status='complete_pending_comparison',elapsed_seconds=elapsed,
         iterations_per_stage=1,model_unchanged=True,native_runs=0,retries=0))
    print('BOUNDED_DECISION_COMPLETE',elapsed,flush=True)


if __name__=='__main__':main()
