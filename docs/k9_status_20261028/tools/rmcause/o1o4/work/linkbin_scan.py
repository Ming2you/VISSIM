# -*- coding: utf-8 -*-
"""Read-only per-link x 150 s FZP scan for W264_READ (2026-10-24 KST, rmcause/o1o4).

Usage: python -B linkbin_scan.py <tag> <fzp_path> <out_dir>

Reads only the FZP. Writes only <out_dir>/<tag>.json.
Per link/connector and 150 s bin (frame time t -> bin int(t // 150)):
  vf[link][bin]  = vehicle-frames (5 s frames -> veh*h = vf * 5 / 3600, rectangle rule)
  qf[link][bin]  = vehicle-frames with speed < 15 km/h ("queued")
  ins[link][bin] = first appearance of a vehicle number (insertion proxy)
  qmax[link][bin]= max queued vehicles on that link in one frame
Also frame count per bin, SHA-256 of the whole file, row count.
No decision or plant replay.
"""
import hashlib
import json
import os
import sys
import time

BIN = 150.0
NB = 60
QS = 15.0


def main():
    tag, path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    t0 = time.time()
    h = hashlib.sha256()
    vf, qf, ins, qmax = {}, {}, {}, {}
    frames = [0] * NB
    seen = set()
    cur_t = None
    cur_q = {}
    rows = 0
    first_t = None
    last_t = None

    def flush(t):
        b = int(t // BIN)
        if b >= NB:
            return
        frames[b] += 1
        for lk, n in cur_q.items():
            a = qmax.get(lk)
            if a is None:
                a = qmax[lk] = [0] * NB
            if n > a[b]:
                a[b] = n
        cur_q.clear()

    with open(path, 'rb') as f:
        for raw in f:
            h.update(raw)
            c0 = raw[:1]
            if c0 in (b'$', b'*', b'\r', b'\n') or not raw.strip():
                continue
            p = raw.split(b';', 7)
            try:
                t = float(p[0])
            except ValueError:
                continue
            if t < 1.0:
                continue
            rows += 1
            if cur_t is None:
                cur_t = t
                first_t = t
            elif t != cur_t:
                flush(cur_t)
                cur_t = t
            last_t = t
            b = int(t // BIN)
            if b >= NB:
                continue
            veh = int(p[1])
            lk = int(p[2])
            spd = float(p[6])
            a = vf.get(lk)
            if a is None:
                a = vf[lk] = [0] * NB
                qf[lk] = [0] * NB
            a[b] += 1
            if spd < QS:
                qf[lk][b] += 1
                cur_q[lk] = cur_q.get(lk, 0) + 1
            if veh not in seen:
                seen.add(veh)
                s = ins.get(lk)
                if s is None:
                    s = ins[lk] = [0] * NB
                s[b] += 1
    if cur_t is not None:
        flush(cur_t)
    out = {
        'schema': 'w264-linkbin/v1', 'tag': tag, 'fzp': path, 'fzp_bytes': os.path.getsize(path),
        'fzp_sha256': h.hexdigest(), 'rows_used': rows, 'first_t': first_t, 'last_t': last_t,
        'bin_s': BIN, 'nb': NB, 'qspeed_kmh': QS, 'frames': frames, 'n_vehicles': len(seen),
        'vf': {str(k): v for k, v in vf.items()}, 'qf': {str(k): v for k, v in qf.items()},
        'ins': {str(k): v for k, v in ins.items()}, 'qmax': {str(k): v for k, v in qmax.items()},
        'elapsed_s': time.time() - t0,
    }
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, tag + '.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(out, g)
    os.replace(tmp, os.path.join(out_dir, tag + '.json'))
    print('done', tag, rows, round(time.time() - t0, 1))


if __name__ == '__main__':
    main()
