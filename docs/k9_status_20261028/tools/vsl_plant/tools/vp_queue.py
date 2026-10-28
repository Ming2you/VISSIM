"""vsl_plant heavy job queue (PRE_VP section 8).  Started detached by vp_launch.ps1 (WMI, BELOW_NORMAL,
PYTHONHASHSEED=0, python -B).

    python -B vp_queue.py <jobs.json>

jobs.json = {"name": ..., "jobs": [{"tag": ..., "kind": "job", "mode": "A|P|S", "run": ..., "T": ..., "spec": ...,
                                     "dir": ...},
                                    {"tag": ..., "kind": "py", "args": [script, arg, ...]}]}
Per job: skip when <VP>/logs/<name>/<tag>.done exists (resume); stop before the next job when <VP>/STOP_VP exists;
take the shared LOCK (exclusive create; our own last release must be >= 20 s ago), look for STOP_VP once more right
after taking the LOCK (r3, D-K9-109: another queue may have written it while we waited; then release the LOCK, run
nothing, write no .done and stop), run the job as a BELOW_NORMAL
child with the K9-2 environment (vp_common.child_env), release the LOCK, write <tag>.done with the exit code.  A job
of mode A/P is followed by vp_jobcheck.py (stop rules of PRE_VP section 7); a nonzero job exit, a probe stop or a
jobcheck hit writes STOP_VP and the queue stops (user decision).  Kills nothing except a job's own process tree (vp_job.py watchdog)."""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402


def main():
    jobs_path = Path(sys.argv[1])
    spec = C.read_json(jobs_path)
    logdir = C.VP / 'logs' / spec['name']
    logdir.mkdir(parents=True, exist_ok=True)
    log = C.make_logger(logdir / 'queue.log')
    C.set_below_normal()
    log('QUEUE_START jobs=%s sha256=%s n=%d queue_sha256=%s' % (jobs_path, C.sha256_file(jobs_path), len(spec['jobs']),
                                                               C.sha256_file(__file__)))
    stop = C.VP / 'STOP_VP'
    for j in spec['jobs']:
        done = logdir / (j['tag'] + '.done')
        if done.is_file():
            log('SKIP %s (done)' % j['tag'])
            continue
        if stop.is_file():
            log('STOP_VP present: stop before %s' % j['tag'])
            break
        C.require_space(log)
        env = C.child_env(C.GT / 'numba_cache')
        if j['kind'] == 'job':
            argv = [C.PY, '-B', str(C.TOOLS / 'vp_job.py'), j['mode'], j['run'], str(j['T']), j['spec'], j['dir']]
        else:
            argv = [C.PY, '-B'] + [str(a) for a in j['args']]
        C.lock_acquire('vsl_plant %s/%s' % (spec['name'], j['tag']), log)
        if stop.is_file():
            # r3 (D-K9-109): STOP_VP written while this queue waited on the LOCK -> no job, no .done.
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
        if j['kind'] == 'job' and j['mode'] in ('A', 'P'):
            summ = C.read_json(Path(j['dir']) / 'job_summary.json') or {}
            crc, _ = C.run_capture([C.PY, '-B', str(C.TOOLS / 'vp_jobcheck.py'), j['dir'], j['mode'],
                                    str(Path(j['dir']) / 'jobcheck.json')], logdir / (j['tag'] + '.check.txt'), env)
            log('JOBCHECK %s exit=%d' % (j['tag'], crc))
            if rc != 0 or summ.get('stop') or crc != 0:
                C.write_json(stop, {'by': j['tag'], 'exit': rc, 'stop': summ.get('stop'), 'jobcheck_exit': crc,
                                    'kst': C.kst()})
                log('STOP_VP written by %s (exit=%d stop=%s jobcheck=%d)' % (j['tag'], rc, summ.get('stop'), crc))
                break
    log('QUEUE_END')


if __name__ == '__main__':
    main()
