# -*- coding: utf-8 -*-
"""vf_runner.py - VERIFY_FWE heavy queue: one FZP per lock hold, one at a time. 2026-10-27 KST.

Usage: python -B vf_runner.py <jobs.json> [<lock_path>] [<pause_s>]
jobs.json: [{"tag":..., "fzp":..., "sha256":...}, ...]
Rules (task HARD RULES): exclusive-create the shared lock (retry every 30 s), owner/pid/time/job/token inside,
delete only our own (token check), pause >= 20 s after each release, give up a job after 60 min without the lock
(remaining jobs skipped), child = vf_fzp.py at BELOW_NORMAL with PYTHONHASHSEED=0 and python -B, kill only our own
child after 10 min (one retry). Writes only under verify/out and verify/logs.
"""
import json
import os
import subprocess
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
VD = os.path.dirname(HERE)
OUT = os.environ.get('VF_OUT', os.path.join(VD, 'out', 'fzp'))  # override only in the self-test
LOGP = os.environ.get('VF_LOG', os.path.join(VD, 'logs', 'runner.log'))
MAXWAIT = float(os.environ.get('VF_MAXWAIT', '3600'))
RETRY = float(os.environ.get('VF_RETRY', '30'))
LOCK_DEFAULT = 'D:/VISSIM-merge/k8_gate_trees/heavy.lock'
BELOW_NORMAL = 0x00004000


def kst():
    return time.strftime('%Y-%m-%d %H:%M:%S KST', time.localtime())


def log(msg):
    os.makedirs(os.path.dirname(LOGP), exist_ok=True)
    with open(LOGP, 'a', encoding='utf-8') as g:
        g.write(kst() + ' ' + msg + '\n')


def acquire(lock, job, max_wait=3600.0, retry=30.0):
    token = uuid.uuid4().hex
    t0 = time.time()
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w', encoding='utf-8') as g:
                json.dump({'owner': 'fwe_verify', 'pid': os.getpid(), 'started_kst': kst(), 'job': 'fwe_verify ' + job, 'token': token}, g)
            return token, time.time() - t0
        except FileExistsError:
            if time.time() - t0 > max_wait:
                return None, time.time() - t0
            try:
                holder = open(lock, encoding='utf-8').read().strip()[:160]
            except OSError:
                holder = '?'
            log('LOCK_BUSY %s holder=%s' % (job, holder))
            time.sleep(retry)


def release(lock, token):
    try:
        d = json.load(open(lock, encoding='utf-8'))
    except (OSError, ValueError):
        log('RELEASE_SKIP lock missing or unreadable'); return False
    if d.get('token') != token:
        log('RELEASE_SKIP not our token'); return False
    os.remove(lock)
    return True


def run_child(job, timeout=600.0):
    env = dict(os.environ)
    env.update({'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'})
    out = os.path.join(OUT, job['tag'] + '.json')
    cmd = [sys.executable, '-B', os.path.join(HERE, 'vf_fzp.py'), job['tag'], job['fzp'], out, job['sha256']]
    with open(os.path.join(os.path.dirname(LOGP), 'child_' + job['tag'] + '.txt'), 'a', encoding='utf-8') as lg:
        p = subprocess.Popen(cmd, stdout=lg, stderr=subprocess.STDOUT, env=env, creationflags=BELOW_NORMAL)
        log('CHILD_START %s pid=%d' % (job['tag'], p.pid))
        try:
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill(); p.wait()
            log('CHILD_KILLED_OWN %s pid=%d (timeout %.0f s)' % (job['tag'], p.pid, timeout))
            return None
    return rc


def main():
    jobs = json.load(open(sys.argv[1], encoding='utf-8'))
    lock = sys.argv[2] if len(sys.argv) > 2 else LOCK_DEFAULT
    pause = float(sys.argv[3]) if len(sys.argv) > 3 else 25.0
    os.makedirs(OUT, exist_ok=True)
    log('START pid=%d jobs=%s lock=%s' % (os.getpid(), ','.join(j['tag'] for j in jobs), lock))
    for job in jobs:
        out = os.path.join(OUT, job['tag'] + '.json')
        if os.path.exists(out):
            log('SKIP_EXISTS ' + job['tag']); continue
        if os.path.exists(os.path.join(VD, 'STOP')):
            log('STOP_FILE'); break
        token, waited = acquire(lock, job['tag'], MAXWAIT, RETRY)
        if token is None:
            log('LOCK_TIMEOUT %s waited=%.0f s; remaining jobs not run' % (job['tag'], waited)); break
        log('LOCK_ACQUIRED %s waited=%.0f s' % (job['tag'], waited))
        t0 = time.time()
        try:
            rc = run_child(job)
            if rc is None:
                rc = run_child(job)
        finally:
            ok = release(lock, token)
            log('LOCK_RELEASED %s ok=%s held=%.1f s rc=%s' % (job['tag'], ok, time.time() - t0, rc))
        time.sleep(pause)
    log('END pid=%d' % os.getpid())


if __name__ == '__main__':
    main()
