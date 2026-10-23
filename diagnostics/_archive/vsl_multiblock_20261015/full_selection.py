"""One full offline selection; explicit cold prices for the changed search policy."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[k]='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import datetime, hashlib, importlib.util, json, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=Path('E:/VISSIM_workspaces/vsl349_causal_20261011')
OUT=HERE/'full_selection3300'
DEC=Path('E:/VISSIM_runs/20261012_adopted355_optimized_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
CFG=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n',encoding='utf8')

def main():
    assert not OUT.exists() and not (HERE/'STOP').exists()
    installation=read(HERE/'search_installation.json')
    for p, expected in installation['source_pins'].items(): assert sha(p)==expected,p
    verify=ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ['NUMSIM_REPO_ROOT']=str(ROOT/'vendor/NumSim-mine')
    sys.argv=[str(verify),'--at','3300','--out',str(OUT),'--tuning',str(CFG),'--decisions',str(DEC),'--full-selection']
    spec=importlib.util.spec_from_file_location('vsl_schedule_full_verifier',verify)
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    import numpy as np
    from evaluation.controllers import sdmpc
    def cold_prices(previous_path,state,policy):
        assert policy.get('vsl_schedule_audit') is True
        return np.zeros(2),dict(source='explicit_offline_changed_search_policy',committed=False,
            actual_previous_controls=True,native_policy_continuation=False)
    sdmpc.load_prices=cold_prices
    record=dict(status='running_one_full_selection',pid=os.getpid(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        full_selection_budget=1,retries=0,native_runs=0,explicit_cold_prices=True,
        native_policy_continuation=False,source_pins=installation['source_pins'],
        config=str(CFG),out=str(OUT),state=str(DEC/'state_003300.json'),
        code_sha256=sha(__file__),scope='Changed finite search with same adopted355 dynamics and objective; source immutable while running')
    save(HERE/'full_selection_state.json',record)
    started=time.perf_counter()
    verifier.main()
    completion=read(OUT/'completion.json')
    assert completion['status']=='complete' and completion['full_selection']
    for p,expected in record['source_pins'].items(): assert sha(p)==expected,p
    record.update(status='complete_validation_pending',seconds=time.perf_counter()-started,
                  finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),completion=completion)
    save(HERE/'full_selection_state.json',record)
    print('FULL_SELECTION_COMPLETE',record['seconds'],flush=True)

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        import traceback
        save(HERE/'full_selection_failure.json',dict(error=repr(exc),traceback=traceback.format_exc(),
            native_runs=0,retry_allowed=False))
        raise
