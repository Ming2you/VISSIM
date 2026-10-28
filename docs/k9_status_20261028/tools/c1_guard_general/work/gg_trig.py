# -*- coding: utf-8 -*-
"""gg_trig.py (guard/general design r0, 2026-10-27 KST) — read-only, light.

Adds two "observed full" trigger variants to the DATA comparison, using ONLY the existing scan outputs
(<run>.npz + segments.json from gd_scan.py; no FZP read, no VISSIM, no lock needed: 12 small npz files).
All thresholds/windows are "data after" (same definitions as gd_analyze.py, LOG_GENERAL 17:10 KST).

Rules evaluated at decision snapshots T = 900..8850 (frame T + 0.1 s):
  lane6_1.0  : vehicles / (len / 6 m) >= 1.0               (user words, literal)
  lane6_0.9  : >= 0.9                                      (codex theta)
  laneL_1.0  : sum(len + 1.51) / len >= 1.0                (length based)
  S_T        : spill flag S at T (queue from the upper 12 m reaches the lower end, gaps <= 20 m)
  U          : lane6_1.0 OR S_T
  S0_T       : stopped (< 5 km/h) vehicle within the upper 12 m at T
Episodes = S frames merged (gap <= 60 s); compare = gd_analyze.compare (lead window 300 s; false = no S in [T-150, T+300]).
Note: S_T false triggers are 0 by construction (S at T is itself an S frame).
Chains and kinds exclude short segments (6 m capacity < 2 vehicles); 'short' reports them separately.
Usage: python -B gg_trig.py <scan_dir> <out.json>
"""
import hashlib
import json
import os
import sys
from collections import defaultdict

import numpy as np

ARMS = ['NC3', 'VSL', 'VA', 'B']
SEEDS = ['s31', 's41', 's43']
RUNS = ['%s_%s' % (a, s) for a in ARMS for s in SEEDS]
DEC = list(range(900, 8851, 150))
KINDS = ('approach_lane', 'feeder_lane', 'meter_prehead_lane', 'meter_approach_lane', 'offramp_landing_lane')
RULES = ('lane6_1.0', 'lane6_0.9', 'laneL_1.0', 'S_T', 'U', 'S0_T')
CHAINS = {
    'c127_urban': ['A:127:1:2', 'A:127:2:2', 'L:10481:127:1', 'L:10481:127:2', 'F:129:1', 'D5:129:1', 'L:10491:129:1', 'F:10491:1'],
    'c127_head_only': ['A:127:1:2', 'A:127:2:2'],
    'c10643_fwe': ['A:71:3:2', 'A:71:4:5', 'F:10641:2', 'F:126:1', 'F:126:2', 'L:10643:126:1', 'L:10643:126:2', 'F:10643:1', 'F:10643:2'],
    'meters_fwe_prehead': ['M:RM_C10484:1', 'M:RM_C10490:1', 'M:RM_C10639:1', 'M:RM_C10681:1', 'M:RM_C10681:2'],
    'meters_fww_prehead': ['M:RM_C10480:1', 'M:RM_C10482:1', 'M:RM_C10482:2', 'M:RM_C10644:1', 'M:RM_C10646:1'],
}
KEY_SEG = ['A:127:1:2', 'L:10481:127:1', 'D5:129:1', 'L:10491:129:1', 'F:10491:1', 'A:71:3:2', 'F:10641:2', 'F:126:2',
           'M:RM_C10639:1', 'M:RM_C10681:2', 'MA:RM_C10639:1', 'M:RM_C10490:1', 'MA:RM_C10490:1']


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def episodes(times, mask):
    idx = np.nonzero(mask)[0]
    if not len(idx):
        return []
    t = times[idx]
    out, s0, prev = [], t[0], t[0]
    for x in t[1:]:
        if x - prev > 65.0:
            out.append((float(s0), float(prev)))
            s0 = x
        prev = x
    out.append((float(s0), float(prev)))
    return out


def compare(eps, trig_T, s_times):
    res = dict(n_ep30=0, lead30=0, late30=0, miss30=0, n_trig=len(trig_T), false_trig=0, lead_s=[], lag_s=[])
    tt = np.array(trig_T, float)
    for t0, t1 in eps:
        if (t1 - t0 + 5.0) < 30.0 - 1e-6:
            continue
        res['n_ep30'] += 1
        w = tt[(tt >= t0 - 300.0 - 1e-6) & (tt <= t0 + 0.1 + 1e-6)]
        if len(w):
            res['lead30'] += 1
            res['lead_s'].append(t0 - float(w.min()))
            continue
        w = tt[(tt > t0 + 0.1) & (tt <= t1 + 1e-6)]
        if len(w):
            res['late30'] += 1
            res['lag_s'].append(float(w.min()) - t0)
        else:
            res['miss30'] += 1
    st = np.array(s_times, float)
    for T in trig_T:
        if not (len(st) and np.any((st >= T - 150.0) & (st <= T + 300.2))):
            res['false_trig'] += 1
    return res


def main():
    scan_dir, out = sys.argv[1:3]
    segj = json.loads(open(os.path.join(scan_dir, 'segments.json'), 'rb').read().decode('utf-8'))
    seg = segj['segments']
    ids = [s['id'] for s in seg]
    idx = {s: i for i, s in enumerate(ids)}
    L = np.array([s['to_m'] - s['from_m'] for s in seg])
    Lp = np.where(L > 0, L, np.nan)
    cap6 = Lp / 6.0
    short = ~(cap6 >= 2.0)
    res = dict(schema='c1g-general-trigger-variants/v1', note='data after; no verdicts; S_T false triggers are 0 by construction',
               tool_sha256=sha(__file__), segments_json_sha256=sha(os.path.join(scan_dir, 'segments.json')), npz={},
               decisions=DEC, rules=RULES, agg={}, dec_any={}, chains={}, key_seg={}, per_sc_va={}, short={})
    for run in RUNS:
        p = os.path.join(scan_dir, run + '.npz')
        res['npz'][run] = sha(p)
        z = np.load(p)
        cnt = z['cnt'].astype(np.float64)
        lsum = z['lsum'].astype(np.float64)
        flg = z['flg']
        times = z['times']
        tix = {round(float(t), 1): k for k, t in enumerate(times)}
        F = np.array([tix[round(T + 0.1, 1)] for T in DEC])
        fm = times >= 900.0
        SP = (flg & 2) > 0
        S0 = (flg & 1) > 0
        occ6 = cnt / cap6[:, None]
        occL = lsum / Lp[:, None]
        trig = {
            'lane6_1.0': occ6[:, F] >= 1.0 - 1e-9,
            'lane6_0.9': occ6[:, F] >= 0.9 - 1e-9,
            'laneL_1.0': occL[:, F] >= 1.0 - 1e-9,
            'S_T': SP[:, F],
            'S0_T': S0[:, F],
        }
        trig['U'] = trig['lane6_1.0'] | trig['S_T']
        for r in trig:
            trig[r] = np.where(np.isfinite(occ6[:, F]) | (r in ('S_T', 'S0_T')), trig[r], False)
        # per kind aggregation (non-short, L > 0)
        for kind in KINDS:
            ki = [i for i, s in enumerate(seg) if s['kind'] == kind and not short[i] and L[i] > 0]
            for r in RULES:
                t = dict(n_ep30=0, lead30=0, late30=0, miss30=0, n_trig=0, false_trig=0)
                ls, gs = [], []
                for i in ki:
                    sp = SP[i] & fm
                    eps = episodes(times, sp)
                    T_ = [DEC[k] for k in np.nonzero(trig[r][i])[0]]
                    c = compare(eps, T_, times[sp])
                    for x in t:
                        t[x] += c[x]
                    ls += c['lead_s']
                    gs += c['lag_s']
                t['lead_s_median'] = float(np.median(ls)) if ls else None
                t['lag_s_median'] = float(np.median(gs)) if gs else None
                t['lead_share'] = round(t['lead30'] / t['n_ep30'], 4) if t['n_ep30'] else None
                t['miss_share'] = round(t['miss30'] / t['n_ep30'], 4) if t['n_ep30'] else None
                res['agg']['%s|%s|%s' % (run, kind, r)] = t
            res['dec_any']['%s|%s' % (run, kind)] = {r: int(trig[r][ki].any(0).sum()) for r in RULES} if ki else None
        hf = [i for i, s in enumerate(seg) if s['kind'] in ('approach_lane', 'feeder_lane') and not short[i] and L[i] > 0]
        res['dec_any']['%s|head+feeder' % run] = {r: int(trig[r][hf].any(0).sum()) for r in RULES}
        res['dec_any']['%s|head+feeder|segments_ever' % run] = {r: int(trig[r][hf].any(1).sum()) for r in RULES}
        # short segments: how often S_T / lane6 fire
        sh = [i for i in range(len(seg)) if short[i] and L[i] > 0]
        res['short'][run] = dict(n_seg=len(sh), seg_ever={r: int(trig[r][sh].any(1).sum()) for r in RULES},
                                 dec_any={r: int(trig[r][sh].any(0).sum()) for r in RULES})
        # chains: first decision any member fires; first spill of A:127:1:2 etc.
        ch = {}
        for c, members in CHAINS.items():
            mi = [idx[m] for m in members if m in idx and not short[idx[m]]]   # short (< 2 veh at 6 m) segments are not sources
            e = {}
            for r in RULES:
                hit = trig[r][mi].any(0)
                e['first_' + r] = DEC[int(np.argmax(hit))] if hit.any() else None
                e['n_' + r] = int(hit.sum())
            fs = []
            for m in mi:
                sp = SP[m] & fm
                if sp.any():
                    fs.append(float(times[np.argmax(sp)]))
            e['first_spill_any_member'] = min(fs) if fs else None
            ch[c] = e
        res['chains'][run] = ch
        ks = {}
        for m in KEY_SEG:
            if m not in idx:
                continue
            i = idx[m]
            sp = SP[i] & fm
            ks[m] = dict(first_spill=float(times[np.argmax(sp)]) if sp.any() else None, spill_s=int(sp.sum()) * 5,
                         **{'first_' + r: (DEC[int(np.argmax(trig[r][i]))] if trig[r][i].any() else None) for r in RULES},
                         **{'n_' + r: int(trig[r][i].sum()) for r in RULES})
        res['key_seg'][run] = ks
        if run.startswith('VA'):
            per = {}
            for sc in sorted(set(s.get('sc') for s in seg if s['kind'] == 'approach_lane')):
                ki = [i for i, s in enumerate(seg) if s['kind'] == 'approach_lane' and s.get('sc') == sc and not short[i] and L[i] > 0]
                if ki:
                    per[sc] = {r: int(trig[r][ki].any(0).sum()) for r in RULES}
            res['per_sc_va'][run] = per
    with open(out + '.tmp', 'w', encoding='utf-8') as g:
        json.dump(res, g, ensure_ascii=False, sort_keys=True, allow_nan=False)
    os.replace(out + '.tmp', out)
    print(sha(out))


if __name__ == '__main__':
    main()
