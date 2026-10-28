"""VERIFY_VP re-run queue (verifier wrapper, 2026-10-27 KST).  Started detached by vv_launch.ps1 (WMI, BELOW_NORMAL,
PYTHONHASHSEED=0, python -B, NUMBA_NUM_THREADS removed).

    python -B vv_queue.py <jobs.json>

Runs the pinned, unchanged producer job runner tools/vp_job.py (same probe tools/vp_probe.py, same hook, same code copy
GT/code_va, same K9-2 environment via vp_common.child_env) for each listed job into a NEW job folder under
GT/verify, one job at a time under the shared LOCK (vp_common.lock_acquire / lock_release: exclusive create, own
lock only, >= 20 s after our last release).  Unlike vp_queue.py it never runs vp_jobcheck.py and never writes STOP_VP
(the re-run P spec carries one ablation only, so the producer stop checks would flag the 8 absent ablations);
the bit identity check is vv_bitcompare.py.  Stops (no further job) on STOP_VP present or a nonzero job exit.
Kills nothing (vp_job.py's own watchdog kills only its own child tree)."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
             r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_plant/tools')
sys.path.insert(0, str(TOOLS))
import vp_common as C  # noqa: E402

VV = C.VP / 'verify'


def main():
    jobs_path = Path(sys.argv[1])
    spec = C.read_json(jobs_path)
    logdir = VV / 'logs' / spec['name']
    logdir.mkdir(parents=True, exist_ok=True)
    log = C.make_logger(logdir / 'queue.log')
    C.set_below_normal()
    log('VVQUEUE_START jobs_sha256=%s n=%d queue_sha256=%s vp_job_sha256=%s vp_probe_sha256=%s hook_sha256=%s' % (
        C.sha256_file(jobs_path), len(spec['jobs']), C.sha256_file(__file__), C.sha256_file(C.TOOLS / 'vp_job.py'),
        C.sha256_file(C.TOOLS / 'vp_probe.py'), C.sha256_file(C.TOOLS / 'vp_hooks' / 'sitecustomize.py')))
    for j in spec['jobs']:
        done = logdir / (j['tag'] + '.done')
        if done.is_file():
            log('SKIP %s (done)' % j['tag'])
            continue
        if (C.VP / 'STOP_VP').is_file():
            log('STOP_VP present: stop before %s' % j['tag'])
            break
        C.require_space(log)
        env = C.child_env(C.GT / 'numba_cache')
        argv = [C.PY, '-B', str(C.TOOLS / 'vp_job.py'), j['mode'], j['run'], str(j['T']), j['spec'], j['dir']]
        C.lock_acquire('vsl_plant verify_vp/%s' % j['tag'], log)
        if (C.VP / 'STOP_VP').is_file():
            log('STOP_VP present after LOCK: stop before %s' % j['tag'])
            C.lock_release(log)
            break
        try:
            log('JOB_BEGIN %s %s' % (j['tag'], ' '.join(argv[2:])[:400]))
            rc, sec = C.run_capture(argv, logdir / (j['tag'] + '.out.txt'), env)
            log('JOB_END %s exit=%d sec=%.0f' % (j['tag'], rc, sec))
        finally:
            C.lock_release(log)
        C.write_json(done, {'tag': j['tag'], 'exit': rc, 'sec': round(sec, 1), 'kst': C.kst()})
        if rc != 0:
            log('NONZERO exit %d: stop' % rc)
            break
    log('VVQUEUE_END')


if __name__ == '__main__':
    main()
