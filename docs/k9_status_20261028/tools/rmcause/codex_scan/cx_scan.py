# -*- coding: utf-8 -*-
"""Read-only FZP region scan for INV_CODEX (2026-10-24 rmcause).

Usage: python -B cx_scan.py <tag> <fzp_path> <out_dir>

Reads only the FZP. Writes only <out_dir>/<tag>.json.
Region link sets = stage-1 scan regions (fw_e_main 7 links etc.) and the codex
east_link_sets_source.json 19-link local set. No decision or plant replay.
Integration: (a) trapezoid over frames (stage-1 style, 5.1..last),
(b) rectangle N*dt plus last-frame hold to 9000 s (codex area_metrics style).
Also: SHA-256 of raw data rows with SimSec < 900 (pairing check).
"""
import hashlib
import json
import os
import sys
import time

REG = {
    'fw_e_main': {2, 24, 74, 119, 10613, 10699, 10702},
    'fw_w_main': {26, 120, 10771},
    'on_conn_e': {10484, 10490, 10639, 10681},
    'off_conn_e': {10481, 10483, 10643, 10682},
    'on_appr_e': {129, 31, 68, 70},
    'onramp_w': {124, 10480, 32, 10482, 69, 10644, 121, 10646},
}
BIN = 150.0


def main():
    tag, path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    t0 = time.time()
    cols = None
    frames = []          # (t, counts dict, total)
    cur_t = None
    cur = None
    cur_tot = 0
    pre = hashlib.sha256()
    pre_rows = 0
    rows = 0
    with open(path, 'rb') as f:
        for raw in f:
            if cols is None:
                if raw.startswith(b'$VEHICLE:'):
                    cols = raw.decode('ascii').strip().split(':', 1)[1].split(';')
                    i_t = cols.index('SIMSEC')
                    i_l = cols.index('LANE\\LINK\\NO')
                continue
            line = raw.rstrip(b'\r\n')
            if not line:
                continue
            p = line.split(b';', 4)
            t = float(p[i_t])
            if t < 900.0:
                pre.update(line + b'\n')
                pre_rows += 1
            rows += 1
            if t != cur_t:
                if cur_t is not None:
                    frames.append((cur_t, cur, cur_tot))
                cur_t = t
                cur = {k: 0 for k in REG}
                cur_tot = 0
            link = int(p[i_l])
            cur_tot += 1
            for k, s in REG.items():
                if link in s:
                    cur[k] += 1
    if cur_t is not None:
        frames.append((cur_t, cur, cur_tot))
    ts = [fr[0] for fr in frames]
    dts = [round(b - a, 6) for a, b in zip(ts, ts[1:])]
    dt_set = sorted(set(dts))
    keys = list(REG) + ['all']

    def val(fr, k):
        return fr[2] if k == 'all' else fr[1][k]

    trap = {k: 0.0 for k in keys}
    for a, b in zip(frames, frames[1:]):
        h = b[0] - a[0]
        for k in keys:
            trap[k] += 0.5 * (val(a, k) + val(b, k)) * h / 3600.0
    rect = {k: 0.0 for k in keys}
    for a, b in zip(frames, frames[1:]):
        h = b[0] - a[0]
        for k in keys:
            rect[k] += val(a, k) * h / 3600.0
    last = frames[-1]
    hold = 9000.0 - last[0]
    for k in keys:
        rect[k] += val(last, k) * hold / 3600.0
    nb = int(9000 // BIN)
    bins = {k: [0.0] * nb for k in keys}
    for a, b in zip(frames, frames[1:]):
        h = b[0] - a[0]
        bi = min(int(a[0] // BIN), nb - 1)
        for k in keys:
            bins[k][bi] += 0.5 * (val(a, k) + val(b, k)) * h / 3600.0
    out = {
        'schema': 'inv-codex-scan/v1', 'tag': tag, 'fzp': path,
        'fzp_bytes': os.path.getsize(path), 'rows': rows, 'frames': len(frames),
        'first_sec': ts[0], 'last_sec': ts[-1], 'dt_set': dt_set[:10],
        'pre900_rows': pre_rows, 'pre900_sha256': pre.hexdigest(),
        'regions': {k: sorted(v) for k, v in REG.items()},
        'trapezoid_veh_h': trap, 'rect_hold9000_veh_h': rect,
        'bins150_trap_veh_h': bins, 'scan_sec': time.time() - t0,
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, tag + '.json'), 'w', encoding='utf-8') as g:
        json.dump(out, g, indent=1)


if __name__ == '__main__':
    main()
