# -*- coding: utf-8 -*-
"""N34 detached chain (2026-10-24): one heavy read at a time, BELOW_NORMAL, PYTHONHASHSEED=0, python -B.
FZP scans take the shared lock r2c_n/fzp.lock (exclusive create; wait while it exists; delete own lock when done).
Model (decision JSON) extraction runs after the FZP scans, without the FZP lock. Read-only toward run folders.
Writes only under r2c_n/n34/ (out/, logs/)."""
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

N34 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R2C = os.path.dirname(N34)
LOCK = os.path.join(R2C, 'fzp.lock')
PY = r'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
LOG = os.path.join(N34, 'logs', 'chain.log')
BELOW = 0x4000
FZP = [
    ('va_s31', r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s31\vissim_eval\sdmpc31_sdmpc31_v3c3_k92va_s31_001.fzp'),
    ('va_s41', r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s41\vissim_eval\sdmpc31_sdmpc31_v3c3_k92va_s41_001.fzp'),
    ('va_s43', r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s43\vissim_eval\sdmpc31_sdmpc31_v3c3_k92va_s43_001.fzp'),
    ('rm_s31', r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3rm\run\vissim_eval\baseline_s31_v3c3rm_001.fzp'),
    ('rm_s41', r'D:\VISSIM_runs\20261001_v3c3\s41_v3c3rm\run\vissim_eval\baseline_s41_v3c3rm_001.fzp'),
]
MODEL = [
    ('va_s31', r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s31'),
    ('va_s41', r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s41'),
    ('va_s43', r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s43'),
]


def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write('%s %s\n' % (time.strftime('%Y-%m-%dT%H:%M:%S'), msg))


def below_normal():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    k.SetPriorityClass(k.GetCurrentProcess(), BELOW)


def take_lock(job):
    token = 'n34 pid=%d job=%s at=%s\n' % (os.getpid(), job, time.strftime('%Y-%m-%dT%H:%M:%S'))
    waited, last_note = 0, -60
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if waited - last_note >= 60:
                try:
                    holder = open(LOCK, encoding='utf-8', errors='replace').read().strip()
                except OSError:
                    holder = '?'
                log('lock busy (%s), waiting %d s for %s' % (holder, waited, job))
                last_note = waited
            if waited > 3 * 3600:
                log('lock wait > 3 h, giving up %s' % job)
                return None
            time.sleep(15)
            waited += 15
            continue
        os.write(fd, token.encode('utf-8'))
        os.close(fd)
        log('lock taken for %s' % job)
        return token


def drop_lock(token):
    try:
        cur = open(LOCK, encoding='utf-8').read()
    except OSError:
        log('lock already gone')
        return
    if cur == token:
        os.remove(LOCK)
        log('lock released')
    else:
        log('lock content not mine, left in place: %r' % cur[:120])


def run(args, tag):
    env = dict(os.environ)
    env['PYTHONHASHSEED'] = '0'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    with open(os.path.join(N34, 'logs', tag + '.out.txt'), 'w', encoding='utf-8') as o, \
            open(os.path.join(N34, 'logs', tag + '.err.txt'), 'w', encoding='utf-8') as e:
        p = subprocess.Popen([PY, '-B'] + args, stdout=o, stderr=e, env=env, creationflags=BELOW)
        log('start %s pid=%d' % (tag, p.pid))
        rc = p.wait()
    log('end %s rc=%d' % (tag, rc))
    return rc


def main():
    below_normal()
    log('CHAIN_START pid=%d' % os.getpid())
    for tag, fzp in FZP:
        out = os.path.join(N34, 'out', 'scan_%s.json' % tag)
        if os.path.exists(out):
            log('skip scan %s' % tag)
            continue
        tok = take_lock('scan_' + tag)
        if tok is None:
            continue
        try:
            run([os.path.join(N34, 'tools', 'n34_fzp_scan.py'), fzp, out], 'scan_' + tag)
        finally:
            drop_lock(tok)
    for tag, root in MODEL:
        out = os.path.join(N34, 'out', 'model_%s.json' % tag)
        if os.path.exists(out):
            log('skip model %s' % tag)
            continue
        run([os.path.join(N34, 'tools', 'n34_model.py'), tag, root, out], 'model_' + tag)
    log('CHAIN_DONE')


if __name__ == '__main__':
    main()
