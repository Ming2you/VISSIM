# -*- coding: utf-8 -*-
"""fwe_heavy_r2.py - D-K9-106 R2 heavy-job queue (PRE_FWE §8.2, §9, §10 S-1/S-9/S-10). Started detached by fwe_launch_r2.ps1.

Usage: python -B fwe_heavy_r2.py <job> [<job> ...]     (job names from JOBS, run in the given order)
Self-test only (env): FWE2_LOCK, FWE2_OUT, FWE2_JOBS_JSON, FWE2_WAIT_S, FWE2_REST_S, FWE2_LOCK_MAX_S, FWE2_STEP_MAX_S

One job = one FZP, the pinned linkbin_scan.py (unchanged), ONE acquisition of the shared lock:
  - lock D:/VISSIM-merge/k8_gate_trees/heavy.lock: exclusive create; if present wait 30 s and retry; give up after 60 min
    (S-9: then the remaining jobs are not run); content {owner: fwe_decomp, pid, started_kst, job}; removed only when
    it still names owner fwe_decomp and this pid.
  - after a release rest >= 20 s before the next acquisition (other workflows get turns).
  - child = python -B, BELOW_NORMAL, PYTHONHASHSEED=0, thread vars 1; > 10 min -> kill own child pid, retry once (S-10).
  - FZP sha256 written by the tool must equal the inventory sha (S-1); else the output is moved to rejected/.
  - a STOP file <OUT>/STOP stops the queue before the next job.
Status -> <OUT>/heavy_r2_status.json. Reads only FZPs and the tool. Writes only under <OUT>.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
FD = SP + '/fwe_decomp'
PY = 'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
LOCK = os.environ.get('FWE2_LOCK', 'D:/VISSIM-merge/k8_gate_trees/heavy.lock')
OUT = os.environ.get('FWE2_OUT', FD + '/out/heavy_r2')
WAIT_S = float(os.environ.get('FWE2_WAIT_S', '30'))
REST_S = float(os.environ.get('FWE2_REST_S', '20'))
LOCK_MAX_S = float(os.environ.get('FWE2_LOCK_MAX_S', str(60 * 60)))
STEP_MAX_S = float(os.environ.get('FWE2_STEP_MAX_S', str(10 * 60)))
BELOW_NORMAL = 0x00004000
LINKBIN = (SP + '/rmcause/o1o4/work/linkbin_scan.py', 'a22d5fa69aff12b5206041437613ad0b7a0decdf56cb5ec7d7e5a071d974b82b')
H = 'D:/VISSIM_handoff/20261024/raw'
V = 'D:/VISSIM_runs/20261027_vsl_v3c3'
JOBS = {   # FZP path and sha256 = FD/out/inventory.json (f51abd20...) rows
    'H6': {'tag': 'lb_cx_joint_s29', 'fzp': H + '/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
           'sha': 'c0aa41bbdfc1cee4ac5d9531d555e317fac9dd208da52c751d8c449e1d2f0ac6'},
    'H7': {'tag': 'lb_cx_window_s29', 'fzp': H + '/window/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
           'sha': 'ce2742b7f6934dda970dd8d3045683303cb716a0bb7d55f836f39b24f697a6c1'},
    'H8': {'tag': 'lb_cx_off_s29', 'fzp': H + '/off/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
           'sha': '73a20cbb813152f0f79a7955c3fe68ee508bc32f365382a3ca0898245f8a63c9'},
    'H9': {'tag': 'lb_vsl_s31', 'fzp': V + '/s31/run/vissim_eval/baseline_s31_v3c3vsl_001.fzp',
           'sha': '63a827fe47606bee0ae17fd2eefaff01067c54e9024436dd7a4d6e12ce9eea54'},
    'H10': {'tag': 'lb_vsl_s41', 'fzp': V + '/s41/run/vissim_eval/baseline_s41_v3c3vsl_001.fzp',
            'sha': 'ea91826e675e899bfbc889a713cc7400a1d75a6d4292bc5305a2f494a4d78177'},
    'H11': {'tag': 'lb_vsl_s43', 'fzp': V + '/s43/run/vissim_eval/baseline_s43_v3c3vsl_001.fzp',
            'sha': '5492358d78386b8bea1c32ea884bf6c073068b5205127ad4e4a7fa661387a3c8'},
    'H12': {'tag': 'lb_a1_s29', 'fzp': 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
            'sha': '9bf7c8c6f56099fb295cd5451377869fe9c73c0c725324ede74c4f3b7a31b6fb'},
}
if os.environ.get('FWE2_JOBS_JSON'):          # self-test only
    _j = json.load(open(os.environ['FWE2_JOBS_JSON'], encoding='utf-8'))
    JOBS = _j['jobs']
    LINKBIN = tuple(_j['tool'])
ME = os.getpid()
STATUS = os.path.join(OUT, 'heavy_r2_status.json')


def kst():
    return time.strftime('%Y-%m-%d %H:%M:%S KST')


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 24), b''):
            h.update(ch)
    return h.hexdigest()


def save(st):
    os.makedirs(OUT, exist_ok=True)
    tmp = STATUS + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(st, g, ensure_ascii=False, indent=1)
    os.replace(tmp, STATUS)


def lock_acquire(job, st):
    t0 = time.time()
    tries = 0
    while True:
        tries += 1
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w', encoding='utf-8') as g:
                json.dump({'owner': 'fwe_decomp', 'pid': ME, 'started_kst': kst(), 'job': 'fwe_decomp R2 ' + job}, g)
            return {'ok': True, 'tries': tries, 'wait_s': round(time.time() - t0, 1), 'at': kst()}
        except FileExistsError:
            try:
                other = open(LOCK, encoding='utf-8').read()[:300]
            except OSError:
                other = '?'
            if time.time() - t0 > LOCK_MAX_S:
                return {'ok': False, 'tries': tries, 'wait_s': round(time.time() - t0, 1), 'held_by': other, 'at': kst()}
            st['now'] = {'job': job, 'state': 'waiting_lock', 'since_s': round(time.time() - t0), 'holder': other, 'at': kst()}
            save(st)
            time.sleep(WAIT_S)


def lock_release():
    try:
        d = json.load(open(LOCK, encoding='utf-8'))
    except (OSError, ValueError):
        return 'missing_or_unreadable'
    if d.get('owner') == 'fwe_decomp' and d.get('pid') == ME:
        os.remove(LOCK)
        return 'released'
    return 'not_ours:' + json.dumps(d)[:200]


def run_linkbin(job, st):
    tool, tsha = LINKBIN
    got = sha_file(tool)
    if got != tsha:
        return {'ok': False, 'why': 'tool sha mismatch %s' % got}
    stage = os.path.join(OUT, '_stage')
    os.makedirs(stage, exist_ok=True)
    cmd = [PY, '-B', tool, job['tag'], job['fzp'], stage]
    env = dict(os.environ)
    env.update(PYTHONHASHSEED='0', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               PYTHONDONTWRITEBYTECODE='1')
    rec = {'cmd': cmd, 'tool_sha256': got, 'attempts': []}
    for attempt in (1, 2):
        t0 = time.time()
        logp = os.path.join(OUT, 'log_%s_a%d.txt' % (job['tag'], attempt))
        with open(logp, 'w', encoding='utf-8') as lg:
            p = subprocess.Popen(cmd, stdout=lg, stderr=subprocess.STDOUT, env=env, creationflags=BELOW_NORMAL)
            st.setdefault('own_pids', []).append(p.pid)
            st['now'] = {'job': job['tag'], 'state': 'running', 'child_pid': p.pid, 'attempt': attempt, 'at': kst()}
            save(st)
            try:
                rc = p.wait(timeout=STEP_MAX_S)
                a = {'attempt': attempt, 'pid': p.pid, 'rc': rc, 'sec': round(time.time() - t0, 1), 'log': logp}
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
                a = {'attempt': attempt, 'pid': p.pid, 'rc': None, 'killed_own_pid': True,
                     'sec': round(time.time() - t0, 1), 'log': logp}
        rec['attempts'].append(a)
        if a['rc'] == 0:
            rec['ok'] = True
            return rec
    rec['ok'] = False
    rec['why'] = 'failed twice (S-10 or error)'
    return rec


def main():
    os.makedirs(OUT, exist_ok=True)
    st = {'tool': os.path.abspath(__file__), 'tool_sha256': sha_file(os.path.abspath(__file__)), 'pid': ME,
          'started': kst(), 'lock': LOCK, 'out': OUT, 'jobs': {}, 'own_pids': [ME]}
    save(st)
    last_release = None
    stop_rest = None
    for name in sys.argv[1:]:
        job = dict(JOBS[name])
        jr = {'name': name, 'tag': job['tag'], 'fzp': job['fzp'], 'expect_sha': job['sha']}
        st['jobs'][name] = jr
        final = os.path.join(OUT, job['tag'] + '.json')
        if stop_rest:
            jr['result'] = 'not_run (%s)' % stop_rest
            save(st)
            continue
        if os.path.exists(os.path.join(OUT, 'STOP')):
            stop_rest = 'STOP file'
            jr['result'] = 'not_run (STOP file)'
            save(st)
            continue
        if os.path.exists(final):
            try:
                have = json.load(open(final, encoding='utf-8')).get('fzp_sha256')
            except (OSError, ValueError):
                have = None
            if have == job['sha']:
                jr['result'] = 'skipped_existing_ok'
                jr['output'] = final
                jr['output_sha256'] = sha_file(final)
                save(st)
                continue
        if last_release is not None:
            gap = time.time() - last_release
            if gap < REST_S:
                time.sleep(REST_S - gap)
        lk = lock_acquire(name, st)
        jr['lock'] = lk
        if not lk['ok']:
            jr['result'] = 'lock_timeout (S-9)'
            stop_rest = 'S-9 lock timeout at ' + name
            save(st)
            continue
        try:
            jr['step'] = run_linkbin(job, st)
        finally:
            jr['lock_release'] = lock_release()
            jr['released_at'] = kst()
            last_release = time.time()
        staged = os.path.join(OUT, '_stage', job['tag'] + '.json')
        got = None
        if os.path.exists(staged):
            try:
                got = json.load(open(staged, encoding='utf-8')).get('fzp_sha256')
            except (OSError, ValueError):
                got = None
        jr['fzp_sha256_from_tool'] = got
        if jr['step'].get('ok') and got == job['sha']:
            os.replace(staged, final)
            jr['result'] = 'ok'
            jr['output'] = final
            jr['output_sha256'] = sha_file(final)
        else:
            if os.path.exists(staged):
                rej = os.path.join(OUT, 'rejected')
                os.makedirs(rej, exist_ok=True)
                shutil.move(staged, os.path.join(rej, job['tag'] + '.json'))
            jr['result'] = 'sha_mismatch (S-1)' if (jr['step'].get('ok') and got != job['sha']) else 'step_failed'
        st['now'] = {'job': name, 'state': 'done', 'at': kst()}
        save(st)
    st['finished'] = kst()
    st['now'] = {'state': 'all_done', 'at': kst()}
    save(st)


if __name__ == '__main__':
    main()
