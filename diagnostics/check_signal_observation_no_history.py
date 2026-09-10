"""Run installed observer tests with Git/history subprocesses denied.

Only the existing cscript and PowerShell fake-COM/config tests may launch.
The actual consumer and original production VBS/PS source are read unchanged.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,shlex,subprocess,sys,time,unittest
ROOT=Path(__file__).resolve().parents[1]
MODULE='diagnostics.test_signal_observation_window_patch'
PRODUCTION=('evaluation/controllers/vissim_stackelberg_adapter.py',
            'evaluation/controllers/signal_head_observation.py',
            'scripts/run_real_world_stackelberg_controller.vbs',
            'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1')


def main():
    before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PRODUCTION}
    calls=[];blocked=[];began=time.monotonic()
    def audit(event,args):
        if event!='subprocess.Popen':return
        command=args[0]
        if command is None:
            command=args[1][0] if isinstance(args[1],(list,tuple)) else shlex.split(args[1],posix=False)[0]
        executable=Path(str(command).strip('"')).name.lower()
        if executable not in {'cscript.exe','powershell.exe'}:
            blocked.append(executable)
            raise RuntimeError('History/undeclared subprocess denied: '+executable)
        calls.append(executable)
    sys.addaudithook(audit)
    try:
        subprocess.run(['git','show','HEAD:never-read'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        raise AssertionError('Git audit guard did not block')
    except RuntimeError as exc:
        if 'denied: git' not in str(exc):raise
    suite=unittest.defaultTestLoader.loadTestsFromName(MODULE)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    after={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PRODUCTION}
    output={'schema':'signal-observation-no-history-validation/v1','tests':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'success':result.wasSuccessful(),
        'blocked_guard_probe':blocked[:1],'test_attempted_undeclared_subprocesses':blocked[1:],
        'allowed_subprocess_counts':dict(Counter(calls)),'production_source_sha256':before,
        'production_source_changes':[p for p in before if before[p]!=after[p]],
        'elapsed_sec':time.monotonic()-began,
        'test_sha256':hashlib.sha256((ROOT/'diagnostics/test_signal_observation_window_patch.py').read_bytes()).hexdigest(),
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output['valid']=output['success'] and not output['test_attempted_undeclared_subprocesses'] and not output['production_source_changes']
    (ROOT/'diagnostics/signal_observation_no_history_validation.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(output,indent=2))
    if not output['valid']:raise SystemExit(1)


if __name__=='__main__':main()
