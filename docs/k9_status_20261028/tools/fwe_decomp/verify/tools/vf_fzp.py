# -*- coding: utf-8 -*-
"""vf_fzp.py - VERIFY_FWE independent FZP reducer (read-only on the FZP). 2026-10-27 KST.

Independent of fwe_scan.py / vhr_scan.py / omega701_recount.py / linkbin_scan.py: columns are found by
header name, rows are parsed with pandas (C engine), everything after that is vectorised numpy.
Definitions (link sets, chain offsets, zone and cell bounds, Omega701, codex partition) are the
pre-declared ones of PRE_FWE.md (sha c7cc0e6c...ce94) section 2 / 7.

Usage: python -B vf_fzp.py <tag> <fzp_path> <out_json> [<expected_sha256>]
Exit codes: 0 ok, 3 sha mismatch (nothing parsed, <out_json>.REJECTED written).
Output (one JSON):
  meta            sha256, bytes, line counts, header columns, rows, 0.1 s rows, frames, monotonic check
  frames_t10      sorted frame times x 10 (int)
  fc              per-frame vehicle counts per group (S7, S19, O701, URBAN, ALL, FWW3, L66) and per link of S19
  b300_link       per S19 link, vehicle-frames per 300 s bin (rows t >= 1.0), bins 0..30
  b300_zone       chain zones U/B1/M/B2/D vehicle-frames per 300 s bin (rows t >= 1.0, x = offset + pos)
  b300_cell59     cells 5-9: 'center' (100 m chain bin centre rule) and 'exact' (vehicle x) per 300 s bin
  merge300        on-ramp connector -> chain transitions per 300 s bin (time of first chain record; rows t >= 1.0)
  first_seen      per first-link category ('74', '26', 'other'): {t10: vehicles first seen at that frame} (all rows)
"""
import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

H = 'D:/VISSIM_handoff/20261024'
DEF_FILES = {
    H + '/derived/omega_membership_exact.json': 'efdfaeb1b9d0d670119c8e158eabd615033bb1127cabd84d187b064ba64cd473',
    H + '/derived/reporting_partition.json': '3142f69c0502f6d9d12416b5b6131d57799bf8f2d17d207b4b0312e854f1dd2b',
}
S7 = (74, 10699, 2, 10613, 119, 10702, 24)
CHAIN_OFF = {74: 0.0, 10699: 2701.577, 2: 2734.527, 10613: 6841.743, 119: 6847.981, 10702: 7431.364, 24: 7438.047}
ONR_FROM = {10639: 70, 10681: 68, 10490: 129, 10484: 31}
OFR = (10643, 10682, 10481, 10483)
S19 = S7 + tuple(ONR_FROM) + tuple(ONR_FROM.values()) + OFR
FWW3 = (26, 10771, 120)
ZONE_NAMES = ('U', 'B1', 'M', 'B2', 'D')
ZONE_EDGES = (4200.0, 5300.0, 6800.0, 7900.0)
CELL59 = (2631.4396, 4542.5389)  # vsl_cell_scan cell_bounds_m[5], [10]
CHAIN_BIN_M = 100.0
CHAIN_NB = 108  # ceil(10784.028 / 100)
NB300 = 31


def sha256_file(path, chunk=8 << 20):
    h = hashlib.sha256(); nl = 0; nbytes = 0
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b); nl += b.count(b'\n'); nbytes += len(b)
    return h.hexdigest(), nl, nbytes


def load_sets():
    got = {}
    for p, want in DEF_FILES.items():
        s = sha256_file(p)[0]
        if s != want:
            raise SystemExit('definition sha mismatch ' + p)
        got[p] = s
    mem = json.load(open(H + '/derived/omega_membership_exact.json', encoding='utf-8-sig'))
    part = json.load(open(H + '/derived/reporting_partition.json', encoding='utf-8-sig'))
    o701 = set(int(x) for x in mem['inside_links'])
    onr8 = set(int(x) for x in part['onramp_roads'])
    off8 = set(int(x) for x in part['offramp_links'])
    urban = o701 - set(S7) - set(FWW3) - onr8 - (off8 & o701)
    return o701, urban, onr8, off8, got


def read_header(path):
    with open(path, 'rb') as f:
        for i, line in enumerate(f):
            if line.startswith(b'$VEHICLE:'):
                cols = line.decode('latin-1').strip().split(':', 1)[1].split(';')
                return i + 1, cols
    raise SystemExit('no $VEHICLE header')


def bincount_t(idx, w, n):
    return np.bincount(idx, weights=w, minlength=n) if w is not None else np.bincount(idx, minlength=n)


def reduce_fzp(path, o701, urban):
    t0 = time.time()
    nhead, cols = read_header(path)
    bs = chr(92)
    names = ['SIMSEC', 'NO', 'LANE' + bs + 'LINK' + bs + 'NO', 'LANE' + bs + 'INDEX', 'POS', 'SPEED']
    ci = [cols.index(n) for n in names]
    df = pd.read_csv(path, sep=';', header=None, skiprows=nhead, usecols=ci, engine='c', encoding='latin-1',
                     dtype={ci[0]: np.float64, ci[1]: np.int64, ci[2]: np.int64, ci[3]: np.int64, ci[4]: np.float64, ci[5]: np.float64})
    t = df[ci[0]].to_numpy(); veh = df[ci[1]].to_numpy(); link = df[ci[2]].to_numpy(); pos = df[ci[4]].to_numpy()
    del df
    t10 = np.rint(t * 10.0).astype(np.int64)
    if np.any(np.abs(t10 / 10.0 - t) > 1e-6):
        raise SystemExit('non 0.1 s time stamp')
    mono = bool(np.all(np.diff(t10) >= 0))
    if not mono:
        raise SystemExit('rows not time ordered')
    nrows = int(t10.size)
    frames, fidx = np.unique(t10, return_inverse=True)
    nF = frames.size
    is7 = np.isin(link, S7); is19 = np.isin(link, S19)
    groups = {
        'S7': is7, 'S19': is19, 'O701': np.isin(link, list(o701)), 'URBAN': np.isin(link, list(urban)),
        'ALL': np.ones(nrows, bool), 'FWW3': np.isin(link, FWW3), 'L66': link == 66,
    }
    fc = {g: np.bincount(fidx[m], minlength=nF).tolist() for g, m in groups.items()}
    fcl = {str(l): np.bincount(fidx[link == l], minlength=nF).tolist() for l in S19}
    # bin form (rows t >= 1.0)
    ge1 = t10 >= 10
    b = np.minimum(t10 // 3000, NB300 - 1)
    b300_link = {str(l): np.bincount(b[ge1 & (link == l)], minlength=NB300).tolist() for l in S19}
    m7 = ge1 & is7
    off = np.zeros(nrows);
    for l, o in CHAIN_OFF.items():
        off[link == l] = o
    x = off + pos
    z = np.searchsorted(np.array(ZONE_EDGES), x[m7], side='right')
    bz = b[m7]
    b300_zone = {}
    for k, zn in enumerate(ZONE_NAMES):
        b300_zone[zn] = np.bincount(bz[z == k], minlength=NB300).tolist()
    xm = x[m7]
    cb = np.minimum(np.floor(xm / CHAIN_BIN_M), CHAIN_NB - 1)
    centre = cb * CHAIN_BIN_M + CHAIN_BIN_M / 2.0
    in_c = (centre >= CELL59[0]) & (centre < CELL59[1])
    in_x = (xm >= CELL59[0]) & (xm < CELL59[1])
    b300_cell59 = {'center': np.bincount(bz[in_c], minlength=NB300).tolist(),
                   'exact': np.bincount(bz[in_x], minlength=NB300).tolist()}
    # merges: consecutive records of one vehicle (rows t >= 1.0), previous on an FW_E on-ramp connector, current on the chain
    sel = np.nonzero(ge1)[0]
    order = sel[np.lexsort((t10[sel], veh[sel]))]
    vs = veh[order]; ls = link[order]; ts = t10[order]
    same = np.zeros(order.size, bool); same[1:] = vs[1:] == vs[:-1]
    prev = np.zeros(order.size, np.int64); prev[1:] = ls[:-1]
    cur7 = np.isin(ls, S7)
    merge300 = {}
    for c in ONR_FROM:
        mm = same & (prev == c) & cur7
        merge300[str(c)] = np.bincount(np.minimum(ts[mm] // 3000, NB300 - 1), minlength=NB300).tolist()
    # also: any non-chain -> chain step that is not from these 4 connectors and not first appearance (report only)
    other_entry = same & ~np.isin(prev, S7) & cur7 & ~np.isin(prev, list(ONR_FROM))
    # first seen (all rows, file order = time order)
    order_all = np.lexsort((t10, veh))
    va = veh[order_all]
    first_mask = np.ones(va.size, bool); first_mask[1:] = va[1:] != va[:-1]
    fi = order_all[first_mask]
    ft = t10[fi]; fl = link[fi]
    cat = np.where(fl == 74, 0, np.where(fl == 26, 1, 2))
    first_seen = {}
    for k, cn in enumerate(('74', '26', 'other')):
        tt, cnt = np.unique(ft[cat == k], return_counts=True)
        first_seen[cn] = {str(int(a)): int(c) for a, c in zip(tt, cnt)}
    return {
        'meta': {'header_lines': nhead, 'n_cols': len(cols), 'col_idx': dict(zip(names, ci)), 'rows': nrows,
                 'rows_t_lt_1': int((~ge1).sum()), 'frames': int(nF), 't10_first': int(frames[0]), 't10_last': int(frames[-1]),
                 'monotonic': mono, 'n_vehicles': int(fi.size), 'other_chain_entries': int(other_entry.sum()),
                 'parse_s': round(time.time() - t0, 1)},
        'frames_t10': frames.tolist(), 'fc': fc, 'fcl': fcl, 'b300_link': b300_link, 'b300_zone': b300_zone,
        'b300_cell59': b300_cell59, 'merge300': merge300, 'first_seen': first_seen,
    }


def main():
    tag, path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    want = sys.argv[4] if len(sys.argv) > 4 else None
    t0 = time.time()
    sha, nl, nbytes = sha256_file(path)
    if want and sha != want:
        with open(out + '.REJECTED', 'w', encoding='utf-8') as g:
            json.dump({'tag': tag, 'path': path, 'sha256': sha, 'expected': want}, g)
        print('SHA_MISMATCH', tag, sha, flush=True)
        sys.exit(3)
    o701, urban, onr8, off8, defsha = load_sets()
    res = reduce_fzp(path, o701, urban)
    res['meta'].update({'tag': tag, 'path': path, 'sha256': sha, 'expected_sha256': want, 'bytes': nbytes, 'newlines': nl,
                        'def_sha256': defsha, 'n_o701': len(o701), 'n_urban': len(urban), 'elapsed_s': round(time.time() - t0, 1),
                        'tool_sha256': sha256_file(os.path.abspath(__file__))[0]})
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(res, g)
    os.replace(tmp, out)
    print('DONE', tag, res['meta']['rows'], res['meta']['elapsed_s'], flush=True)


if __name__ == '__main__':
    main()
