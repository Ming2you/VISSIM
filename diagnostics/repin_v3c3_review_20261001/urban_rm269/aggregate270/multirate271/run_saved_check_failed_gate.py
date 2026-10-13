"""Bounded saved-state response or unchanged-budget decision. No native work."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')


def main():
    mode = sys.argv[1]
    assert mode in ('response', 'full')
    label = 'unseen3300' if mode == 'response' else 'full2400'
    out = HERE/(label+'_fw5')
    receipt_path = HERE/(label+'_execution.json')
    assert not out.exists() and not receipt_path.exists(), 'Preserve previous attempts; no retry'
    assert not any((p/'STOP').exists() for p in (ROOT, HERE, HERE.parent, HERE.parent.parent))
    plan = read(HERE/'plan.json')
    for name, digest in plan['source_pins'].items():
        assert sha(ROOT/name) == digest, name
    if mode == 'full':
        assert read(HERE/'unseen3300_fw5/comparison.json')['physical_and_major_response_gate_pass']
        assert plan['full_sdmpc_selections'] == 0
    os.environ['NUMSIM_REPO_ROOT'] = str(ROOT/'vendor/NumSim-mine')
    sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
    from evaluation import parameters
    policy = parameters.load()
    assert policy['sdmpc']['max_iterations'] == policy['sdmpc_pfo_cap']['max_iterations'] == 2
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    # Record Windows process creation time, not an approximate launch timestamp.
    class FT(ctypes.Structure):
        _fields_ = [('low', ctypes.c_ulong), ('high', ctypes.c_ulong)]
    values = [FT() for _ in range(4)]
    kernel.GetProcessTimes.argtypes = [ctypes.c_void_p]+[ctypes.POINTER(FT)]*4
    assert kernel.GetProcessTimes(kernel.GetCurrentProcess(), *[ctypes.byref(v) for v in values])
    ticks = (values[0].high << 32) | values[0].low
    birth = datetime.fromtimestamp(ticks/1e7-11644473600, timezone.utc).isoformat()
    helper = HERE.parent.parent/'validate_unseen_window.py'
    verifier = ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
    config = HERE/'config_fw5_urban1.json'
    sources = list((ROOT/'evaluation/controllers').glob('*.py')) + [Path(__file__), helper, verifier, config]
    sources += list((ROOT/'evaluation').glob('*parameters*'))
    pins = {str(p):sha(p) for p in sources if p.is_file()}
    receipt = dict(status='running', mode=mode, pid=os.getpid(), creation_utc=birth,
        started_utc=datetime.now(timezone.utc).isoformat(), source_pins=pins,
        native_runs=0, retries=0, full_decisions_max=int(mode == 'full'),
        iterations_per_stage=2, output=str(out))
    save(receipt_path, receipt)
    if mode == 'full':
        plan['full_sdmpc_selections'] = 1
        save(HERE/'plan.json', plan)
        decisions = 'E:/VISSIM_runs/20261008_coupling268_window_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
        sys.argv = [str(verifier), '--at', '2400', '--out', str(out), '--full-selection',
                    '--tuning', str(config), '--decisions', decisions]
    else:
        sys.argv = [str(helper), '--freeway5']
    started = time.perf_counter()
    try:
        runpy.run_path(sys.argv[0], run_name='__main__')
        assert read(out/'completion.json')['status'] == 'complete'
        if mode == 'full':
            assert read(out/'completion.json')['full_selection']
        assert all(sha(Path(p)) == h for p,h in pins.items())
        receipt.update(status='complete_pending_review', source_pins_unchanged=True, exit_code=0)
    except BaseException as error:
        receipt.update(status='failed_preserved', error=repr(error), traceback=traceback.format_exc(), exit_code=1)
        raise
    finally:
        receipt.update(wall_sec=time.perf_counter()-started, ended_utc=datetime.now(timezone.utc).isoformat())
        save(receipt_path, receipt)
    print('SAVED_CHECK_COMPLETE', mode, receipt['wall_sec'], flush=True)


if __name__ == '__main__':
    main()
