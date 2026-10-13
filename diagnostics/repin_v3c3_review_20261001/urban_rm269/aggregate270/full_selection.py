"""One complete unchanged-budget SDMPC decision on the opt-in aggregate plant."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=HERE/'full2400_lane_offer'
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def main():
    assert not OUT.exists(),'Keep previous attempts; no duplicate decision'
    assert not any((p/'STOP').exists() for p in (ROOT,HERE.parent,HERE))
    plan=read(HERE/'full_selection_plan.json')
    assert plan['launches_consumed']==0
    assert read(HERE/'ad2400_lane_offer/verification.json')['status']=='scalar_ad_forward_equivalence_passed'
    assert read(HERE/'isolated_pair_assessment.json')['large_tradeoff_directions_pass']
    for path,digest in plan['source_pins'].items():assert sha(Path(path))==digest,path
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
        os.environ[k]='1'
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ.update(PYTHONDONTWRITEBYTECODE='1',NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'))
    from evaluation import parameters
    policy=parameters.load()
    assert policy['sdmpc']['max_iterations']==policy['sdmpc_pfo_cap']['max_iterations']==2
    plan.update(status='running',launches_consumed=1,python_pid=os.getpid())
    save(HERE/'full_selection_plan.json',plan)
    sys.argv=[str(ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'),
              '--at','2400','--out',str(OUT),'--full-selection',
              '--tuning',str(HERE/'config_dt10.json'),'--decisions',plan['decisions']]
    start=time.perf_counter();cpu=time.process_time()
    try:
        runpy.run_path(sys.argv[0],run_name='__main__')
        assert read(OUT/'completion.json')['full_selection']
        for path,digest in plan['source_pins'].items():assert sha(Path(path))==digest,path
    except BaseException as error:
        save(HERE/'full_selection_execution.json',dict(status='failed_preserved',
             elapsed_seconds=time.perf_counter()-start,error=repr(error),traceback=traceback.format_exc(),
             native_runs=0,retries=0))
        plan['status']='failed_preserved';save(HERE/'full_selection_plan.json',plan)
        raise
    elapsed=time.perf_counter()-start
    save(HERE/'full_selection_execution.json',dict(status='complete_pending_review',
         elapsed_seconds=elapsed,parent_cpu_seconds=time.process_time()-cpu,
         full_time_target_met=elapsed<=600,iterations_per_stage=2,
         native_runs=0,retries=0,scope='Single saved-state complete decision under competing native workload; not a matched-baseline speedup measurement.'))
    plan['status']='complete_pending_review';save(HERE/'full_selection_plan.json',plan)
    print('FULL_DECISION_COMPLETE',elapsed,flush=True)


if __name__=='__main__':main()
