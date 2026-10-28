# -*- coding: utf-8 -*-
"""fwe_heavy.py - heavy FZP jobs one at a time under the shared lock (D-K9-106, PRE_FWE section 9). 2026-10-27 KST.

Usage: python -B fwe_heavy.py <jobs.json>
jobs.json = {"name": "...", "jobs": [{"job": "H1", "fzp": "...", "expect_sha256": "...",
                                       "tools": [{"tool": "fwe_scan"|"linkbin"|"firstseen", "tag": "..."}]}]}
Rules (PRE_FWE section 9, section 10 S-1/S-9/S-10):
- lock D:/VISSIM-merge/k8_gate_trees/heavy.lock created exclusively (O_CREAT|O_EXCL); busy -> retry after 30 s;
  one job (one FZP, its 1-3 tools) = one lock; released after the job; >= 20 s pause before the next acquire.
- only our own lock (token match) is removed; only our own child PIDs are killed.
- S-9: one job cannot get the lock for 60 min -> stop all remaining heavy jobs.
- S-10: a tool runs > 10 min -> kill own child, retry once; again -> mark 'not produced'.
- S-1: fwe_scan / linkbin outputs carry the FZP sha256 they computed; != expect_sha256 -> output renamed *.REJECTED.
- children: python -B, PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1, OMP/OPENBLAS/MKL threads 1, BELOW_NORMAL.
Reads only FZPs (through the pinned existing tools). Writes only FD/out/heavy and FD/logs/heavy.
"""
import json, os, sys, time, uuid, subprocess, datetime

FD = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/fwe_decomp'
SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
OUT = FD + '/out/heavy'
LOGD = FD + '/logs/heavy'
LOCK = 'D:/VISSIM-merge/k8_gate_trees/heavy.lock'
PY = sys.executable
TOOLS = {
    'fwe_scan': SP + '/rmcause/phys/fwe_scan.py',
    'linkbin': SP + '/rmcause/o1o4/work/linkbin_scan.py',
    'firstseen': FD + '/tools/fwe_wrap_vhr.py',
}
LOCK_RETRY_S = 30
LOCK_GIVEUP_S = 3600
PAUSE_S = 25
TOOL_TIMEOUT_S = 600
BELOW_NORMAL = 0x00004000


def kst():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' KST'


def note(log, msg):
    with open(log, 'a', encoding='utf-8') as f:
        f.write(f'{kst()} [pid={os.getpid()}] {msg}\n')


def acquire(log, job, token):
    t0 = time.time()
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            body = json.dumps({'owner': 'fwe_decomp', 'pid': os.getpid(), 'started_kst': kst(), 'job': 'fwe_decomp R3 ' + job,
                               'token': token})
            os.write(fd, body.encode('utf-8'))
            os.close(fd)
            note(log, f'LOCK_TAKEN {job} waited_s={round(time.time() - t0, 1)}')
            return True
        except FileExistsError:
            if time.time() - t0 > LOCK_GIVEUP_S:
                note(log, f'LOCK_GIVEUP {job} (S-9)')
                return False
            try:
                holder = open(LOCK, encoding='utf-8', errors='replace').read()
            except OSError:
                holder = '?'
            note(log, f'LOCK_BUSY {job} retry {LOCK_RETRY_S}s holder={holder}')
            time.sleep(LOCK_RETRY_S)


def release(log, token):
    try:
        cur = open(LOCK, encoding='utf-8', errors='replace').read()
        if token in cur:
            os.remove(LOCK)
            note(log, 'LOCK_RELEASED')
        else:
            note(log, 'LOCK_NOT_OURS left as is: ' + cur)
    except OSError as e:
        note(log, 'LOCK_RELEASE_ERROR ' + repr(e))


def child_env():
    e = dict(os.environ)
    e.update({'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONIOENCODING': 'utf-8',
              'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'})
    return e


def run_tool(log, job, t, fzp):
    tool, tag = t['tool'], t['tag']
    args = [PY, '-B', TOOLS[tool]]
    if tool == 'firstseen':
        args += [tag, fzp, OUT]
    else:
        args += [tag, fzp, OUT]
    for attempt in (1, 2):
        lo = open(f'{LOGD}/{job}_{tag}_{attempt}.out.txt', 'w', encoding='utf-8')
        t0 = time.time()
        p = subprocess.Popen(args, stdout=lo, stderr=subprocess.STDOUT, env=child_env(), creationflags=BELOW_NORMAL)
        note(log, f'TOOL_BEGIN {job} {tool} {tag} attempt={attempt} child_pid={p.pid} args={args[2:]}')
        try:
            rc = p.wait(timeout=TOOL_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            lo.close()
            note(log, f'TOOL_TIMEOUT {job} {tag} attempt={attempt} killed own child_pid={p.pid} (S-10)')
            continue
        lo.close()
        note(log, f'TOOL_END {job} {tool} {tag} rc={rc} sec={round(time.time() - t0, 1)}')
        return rc
    note(log, f'TOOL_NOT_PRODUCED {job} {tag} (S-10 twice)')
    return -9


def out_path(t):
    if t['tool'] == 'firstseen':
        return f"{OUT}/first_{t['tag']}.json"
    return f"{OUT}/{t['tag']}.json"


def main():
    spec = json.load(open(sys.argv[1], encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(LOGD, exist_ok=True)
    log = f"{LOGD}/{spec['name']}.log"
    token = uuid.uuid4().hex
    note(log, f'START fwe_heavy {spec["name"]} token={token} jobs={[j["job"] for j in spec["jobs"]]}')
    status = {}
    first = True
    for j in spec['jobs']:
        if all(os.path.exists(out_path(t)) for t in j['tools']):
            note(log, f'SKIP {j["job"]} outputs already exist')
            status[j['job']] = 'exists'
            continue
        if not first:
            time.sleep(PAUSE_S)
        first = False
        if not acquire(log, j['job'], token):
            status[j['job']] = 'lock_giveup'
            for k in spec['jobs']:
                status.setdefault(k['job'], 'not_run_after_S9')
            break
        try:
            shas = {}
            for t in j['tools']:
                if os.path.exists(out_path(t)):
                    note(log, f'TOOL_SKIP exists {out_path(t)}')
                    continue
                rc = run_tool(log, j['job'], t, j['fzp'])
                if rc != 0:
                    status[j['job'] + ':' + t['tag']] = f'rc={rc}'
                    continue
                if t['tool'] in ('fwe_scan', 'linkbin'):
                    d = json.load(open(out_path(t), encoding='utf-8'))
                    shas[t['tag']] = d.get('fzp_sha256')
        finally:
            release(log, token)
        bad = {k: v for k, v in shas.items() if v != j['expect_sha256']}
        if bad:
            note(log, f'S-1 SHA_MISMATCH {j["job"]} expect={j["expect_sha256"]} got={bad}')
            for t in j['tools']:
                if os.path.exists(out_path(t)):
                    os.replace(out_path(t), out_path(t) + '.REJECTED')
            status[j['job']] = 'S-1 rejected'
        else:
            note(log, f'SHA_OK {j["job"]} {shas}')
            status.setdefault(j['job'], 'done')
    json.dump({'name': spec['name'], 'status': status, 'end_kst': kst()},
              open(f"{LOGD}/{spec['name']}.status.json", 'w', encoding='utf-8'), indent=1)
    note(log, f'END status={status}')


if __name__ == '__main__':
    main()
