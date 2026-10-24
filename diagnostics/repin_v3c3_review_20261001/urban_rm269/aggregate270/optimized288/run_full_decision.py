"""One VSL-enabled saved-state choice, preserving the PFO2/SDMPC2 budget."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key] = '1'
import ctypes
import hashlib
import json
import runpy
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
save = lambda p,v: p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    plan = read(HERE/'plan.json')
    failed = read(HERE/'full_decision_execution.json')
    assert failed['status'] == 'failed_preserved' and 'FileNotFoundError' in failed['error']
    assert not Path(failed['output']).exists(), 'Previous failure must be before initialization'
    context = Path(plan['output'])/'context3300'
    assert 'prior price/application context mismatch' in read(HERE/'full_decision_execution_r2.json')['error']
    assert read(context/'completion.json')['status'] == 'complete'
    context_protocol = read(context/'protocol.json')
    assert context_protocol['max_predictions'] == context_protocol['optimization_iterations'] == 0
    assert not context_protocol['cold_prices']
    axes = read(context/'coordinates.json')['axes']
    assert len(axes) == 237 and sum(a['kind']=='vsl' for a in axes) == 24
    receipt, out = HERE/'full_decision_execution_r3.json', Path(plan['output'])/'full3300_r3'
    assert not receipt.exists() and not out.exists(), 'No automatic repeated full selection'
    assert not any((p/'STOP').exists() for p in (ROOT,HERE,HERE.parent,HERE.parent.parent,out.parent))
    assert plan['full_decisions_limit'] == 1 and plan['coefficient_fits'] == 0
    assert (HERE/'parameters_pass.json').exists()
    pins = dict(read(HERE.parent/'decision285/full_decision_execution.json')['source_pins'])
    pins.update(plan['source_pins'])
    for p in (Path(__file__), HERE/'plan.json', HERE/'parameters_pass.json', context/'protocol.json', context/'completion.json', context/'coordinates.json'):
        pins[str(p)] = sha(p)
    assert all(sha(Path(p)) == digest for p,digest in pins.items())
    config = HERE/'config.json'
    tuning = read(config)
    assert 'sdmpc_fixed_vsl' not in tuning['adapter']
    assert tuning['freeway']['multirate_exchange_sec'] == 5 and tuning['urban']['multirate_exchange_sec'] == 10
    sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
    from evaluation import parameters
    policy = parameters.load()
    assert policy['sdmpc']['max_iterations'] == policy['sdmpc_pfo_cap']['max_iterations'] == 2
    decisions = str(Path(context_protocol['state']).parent)
    for name in ('state_003300.json','action_003150.json','action_003150.csv','action_003150.json.applied'):
        p = Path(decisions)/name
        pins[str(p)] = sha(p)
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    record = dict(status='running',pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        source_pins=pins,config_sha256=sha(config),native_runs=0,full_decisions=1,retries=0,
        iterations_per_stage=2,output=str(out),decisions=decisions,vsl_optimized=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    save(receipt,record)
    t0 = time.perf_counter()
    script = ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
    sys.argv = [str(script),'--at','3300','--out',str(out),'--full-selection','--tuning',str(config),'--decisions',decisions]
    try:
        runpy.run_path(str(script),run_name='__main__')
        assert read(out/'completion.json')['full_selection']
        assert all(sha(Path(p)) == digest for p,digest in pins.items())
        record['status'] = 'complete_pending_review'
    except BaseException as error:
        record.update(status='failed_preserved',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        record.update(wall_sec=time.perf_counter()-t0,ended_utc=datetime.now(timezone.utc).isoformat())
        save(receipt,record)
    print('FULL_OPTIMIZED_VSL_COMPLETE',record['wall_sec'],flush=True)


if __name__ == '__main__':
    main()
