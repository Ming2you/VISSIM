# -*- coding: utf-8 -*-
"""gr_check.py — review of GENERAL_GUARD_DESIGN r0 (2026-10-27 KST). Read-only, light.

Inputs: existing scan outputs only (<run>.npz + segments.json), inventory.json, native clock plan.
No FZP, no VISSIM/COM, no plant, no decision replay. All counts are "data after".

What it computes
  1. segment overlaps (same link/lane, overlap > 0.05 m) by kind pair
  2. head lanes without receivers / with only short receivers; receiver coverage by scanned segments
  3. head-lane weight emulation per decision (U rule, codex score form with max(1, n/C) floor):
       score(h) = -1 if receivers known & all covered receivers F (uncovered -> not F)
                = max(1, n/C) if not short & F & receivers
                = 0 otherwise
     + landing L:10481 on SC1001 p3 lanes (sum = r0, max = r1)
     direction per signal as CX USG constrain (axes from native clock basis; SC7 concurrent_p1_p2)
     -> decisions with >= 1 row, rows, rows with max|w| < 0.5 (needs > 4 s at r = 2),
        rows that exist only because of the concurrent basis (all live weights equal),
        -1 lane-decisions
  4. S/U 'lead' decomposition: lead by recurrence (S at a decision strictly before t0) vs at start
  5. variants (head lanes only, no landing): U_U (sources U, receivers U), U_shortcount (sources U, short
     receivers count-only n >= C), N_N (sources and receivers count-only = user words literally)
Feeder chains and meters are NOT emulated (design rule underspecified on the r0 segment table).
Usage: python -B gr_check.py <scan_dir> <inventory.json> <native_clock_plan.json> <out.json>
"""
import collections
import hashlib
import json
import os
import sys

import numpy as np

ARMS = ['NC3', 'VSL', 'VA', 'B']
SEEDS = ['s31', 's41', 's43']
RUNS = ['%s_%s' % (a, s) for a in ARMS for s in SEEDS]
DEC = list(range(900, 8851, 150))


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    scan_dir, inv_p, plan_p, out = sys.argv[1:5]
    seg = json.loads(open(os.path.join(scan_dir, 'segments.json'), 'rb').read().decode('utf-8'))['segments']
    inv = json.loads(open(inv_p, 'rb').read().decode('utf-8'))
    plan = json.loads(open(plan_p, 'rb').read().decode('utf-8'))
    ids = [s['id'] for s in seg]
    L = np.array([s['to_m'] - s['from_m'] for s in seg])
    cap6 = np.where(L > 0, L, np.nan) / 6.0
    short = ~(cap6 >= 2.0)
    res = dict(schema='c1g-general-review-check/v1', note='data after; no verdicts; head lanes only for weights',
               tool_sha256=sha(__file__), segments_json_sha256=sha(os.path.join(scan_dir, 'segments.json')),
               inventory_sha256=sha(inv_p), plan_sha256=sha(plan_p), npz={})

    # 1. overlaps
    by = collections.defaultdict(list)
    for i, s in enumerate(seg):
        by[(s['link'], s['lane'])].append(i)
    ov = []
    for k, v in by.items():
        for a in range(len(v)):
            for b in range(a + 1, len(v)):
                x, y = seg[v[a]], seg[v[b]]
                o = min(x['to_m'], y['to_m']) - max(x['from_m'], y['from_m'])
                if o > 0.05:
                    ov.append(dict(a=x['id'], b=y['id'], kinds='|'.join(sorted((x['kind'], y['kind']))), overlap_m=round(o, 2)))
    res['overlaps'] = dict(n_pairs=len(ov), by_kind=dict(collections.Counter(o['kinds'] for o in ov)),
                           segments_in_any=len({o['a'] for o in ov} | {o['b'] for o in ov}), pairs=ov)

    # 2. head lanes and receivers
    al = [a for a in inv['approach_lanes'] if a['phases']]
    aid = {}
    for i, s in enumerate(seg):
        if s['kind'] == 'approach_lane':
            aid[(s['link'], s['lane'], s['sg'])] = i
    rec_map, cov_n, tot_n = {}, 0, 0
    lanes = []
    for a in al:
        i = aid[(a['link'], a['lane'], a['sg'])]
        recs = []
        for r in a['receivers']:
            tot_n += 1
            lo, hi = r['landing_pos_m'], r['segment_end_m']
            ln = hi - lo
            best = None
            for j in by.get((r['link'], r['lane']), []):
                s = seg[j]
                o = min(hi, s['to_m']) - max(lo, s['from_m'])
                if o >= 0.8 * ln - 0.5 and (s['to_m'] - s['from_m']) <= 1.25 * ln + 2:
                    if best is None or (s['to_m'] - s['from_m']) < (seg[best]['to_m'] - seg[best]['from_m']):
                        best = j
            if best is not None:
                cov_n += 1
            recs.append(best)
        lanes.append(dict(i=i, sc=a['sc'], phases=a['phases'], recs=recs, n_rec=len(recs)))
    res['receivers'] = dict(total=tot_n, covered_by_scanned_segment=cov_n,
                            head_lanes_no_receiver=[ids[x['i']] for x in lanes if not x['n_rec']],
                            head_lanes_all_receivers_covered=sum(1 for x in lanes if x['n_rec'] and all(r is not None for r in x['recs'])),
                            head_lanes_with_receivers=sum(1 for x in lanes if x['n_rec']),
                            head_lanes_all_receivers_short=[ids[x['i']] for x in lanes if x['n_rec'] and all(r is not None and short[r] for r in x['recs'])])
    # live phases / axes
    live, conc = {}, {}
    for k, v in plan['controllers'].items():
        sc = 'SC' + k
        order = inv['plan_phase_order'][sc]
        live[sc] = [p for p in order if v['axis_green_sec'].get(p, 0.) > 0.]
        conc[sc] = v['native_clock_basis']['kind'] == 'concurrent_p1_p2'
    res['axes'] = {sc: dict(live=live[sc], concurrent=conc[sc]) for sc in live}
    landing = [ids.index(x) for x in ('L:10481:127:1', 'L:10481:127:2')]
    landing_head = {ids.index('L:10481:127:1'): ids.index('A:127:1:2'), ids.index('L:10481:127:2'): ids.index('A:127:2:2')}

    def direction(sc, W):
        lv = live[sc]
        scale = max([abs(W.get(p, 0.)) for p in lv], default=0.)
        if scale == 0:
            return None
        if conc[sc]:
            ax = [W.get('p1', 0.), W.get('p2', 0.) - W.get('p4', 0.)]
        else:
            ax = [W.get(p, 0.) - W.get(lv[-1], 0.) for p in lv[:-1]]
        w = np.array(ax) / scale
        return w

    runs = {}
    for run in RUNS:
        p = os.path.join(scan_dir, run + '.npz')
        res['npz'][run] = sha(p)
        z = np.load(p)
        cnt = z['cnt'].astype(np.float64)
        flg = z['flg']
        times = z['times']
        tix = {round(float(t), 1): k for k, t in enumerate(times)}
        Fi = np.array([tix[round(T + 0.1, 1)] for T in DEC])
        SP = (flg & 2) > 0
        occ6 = cnt / cap6[:, None]
        F = (occ6[:, Fi] >= 1.0 - 1e-9) | SP[:, Fi]
        F = np.where(np.isfinite(cap6)[:, None], F, SP[:, Fi])
        occ = np.nan_to_num(occ6[:, Fi])
        r = dict(rows_sum=0, rows_max=0, dec_with_row_sum=0, dec_with_row_max=0, minus1_lane_dec=0,
                 minus1_dec=0, rows_weak_lt05=0, rows_weak_lt025=0, rows_conc_only=0, rows_by_sc=collections.Counter(),
                 minus1_by_lane=collections.Counter(), sc1001_p3_landing_double=0)
        for k, T in enumerate(DEC):
            Wsum = collections.defaultdict(lambda: collections.defaultdict(float))
            Wmax_l = collections.defaultdict(lambda: collections.defaultdict(float))
            m1 = 0
            hscore = {}
            for x in lanes:
                i = x['i']
                if x['n_rec'] and all(rr is not None and F[rr, k] for rr in x['recs']):
                    s = -1.0
                    m1 += 1
                    r['minus1_by_lane'][ids[i]] += 1
                elif x['n_rec'] and (not short[i]) and F[i, k]:
                    s = max(1.0, occ[i, k])
                else:
                    s = 0.0
                hscore[i] = s
                for ph in x['phases']:
                    Wsum[x['sc']][ph] += s
                    Wmax_l[x['sc']][ph] += s
            # landing L:10481 (lane with head A:127:x, p3)
            for li in landing:
                hi_ = landing_head[li]
                if F[li, k] and hscore[hi_] >= 0:
                    sl = max(1.0, occ[li, k])
                    Wsum['SC1001']['p3'] += sl
                    # r1: max per lane instead of sum
                    Wmax_l['SC1001']['p3'] += max(sl, hscore[hi_]) - hscore[hi_]
                    if hscore[hi_] > 0:
                        r['sc1001_p3_landing_double'] += 1
            r['minus1_lane_dec'] += m1
            r['minus1_dec'] += int(m1 > 0)
            any_s = any_m = False
            for sc in live:
                w = direction(sc, Wsum[sc])
                if w is not None and np.max(np.abs(w)) >= 1e-10:
                    r['rows_sum'] += 1
                    any_s = True
                    r['rows_by_sc'][sc] += 1
                    mx = float(np.max(np.abs(w)))
                    r['rows_weak_lt05'] += int(mx < 0.5)
                    r['rows_weak_lt025'] += int(mx < 0.25)
                    vals = [Wsum[sc].get(pp, 0.) for pp in live[sc]]
                    if conc[sc] and max(vals) - min(vals) < 1e-12:
                        r['rows_conc_only'] += 1
                w2 = direction(sc, Wmax_l[sc])
                if w2 is not None and np.max(np.abs(w2)) >= 1e-10:
                    r['rows_max'] += 1
                    any_m = True
            r['dec_with_row_sum'] += int(any_s)
            r['dec_with_row_max'] += int(any_m)
        # variants: (source F, receiver F for short receivers)
        Fn = np.where(np.isfinite(cap6)[:, None], occ6[:, Fi] >= 1.0 - 1e-9, False)
        var = {}
        for vname, Fsrc, short_rec_rule in (('U_U', F, 'U'), ('U_shortcount', F, 'N'), ('N_N', Fn, 'N')):
            dec_row = rows = m1d = m1l = 0
            for k in range(len(DEC)):
                W = collections.defaultdict(lambda: collections.defaultdict(float))
                m1 = 0
                for x in lanes:
                    i = x['i']
                    def rf(rr):
                        if rr is None:
                            return False
                        if short[rr] and short_rec_rule == 'N':
                            return bool(Fn[rr, k])
                        return bool(Fsrc[rr, k]) if vname != 'U_U' else bool(F[rr, k])
                    if x['n_rec'] and all(rf(rr) for rr in x['recs']):
                        sc_ = -1.0; m1 += 1
                    elif x['n_rec'] and (not short[i]) and Fsrc[i, k]:
                        sc_ = max(1.0, occ[i, k])
                    else:
                        sc_ = 0.0
                    for ph in x['phases']:
                        W[x['sc']][ph] += sc_
                anyr = False
                for sc in live:
                    w = direction(sc, W[sc])
                    if w is not None and np.max(np.abs(w)) >= 1e-10:
                        rows += 1; anyr = True
                dec_row += int(anyr); m1d += int(m1 > 0); m1l += m1
            var[vname] = dict(dec_with_row=dec_row, rows=rows, minus1_dec=m1d, minus1_lane_dec=m1l)
        r['variants'] = var
        r['rows_by_sc'] = dict(r['rows_by_sc'])
        r['minus1_by_lane'] = dict(r['minus1_by_lane'].most_common(8))
        # 4. lead decomposition for head lanes, U
        lead_n = rec_n = start_n = cnt_only = 0
        for x in lanes:
            i = x['i']
            if short[i]:
                continue
            sp = SP[i] & (times >= 900.0)
            idx = np.nonzero(sp)[0]
            if not len(idx):
                continue
            t = times[idx]
            eps, s0, prev = [], t[0], t[0]
            for v in t[1:]:
                if v - prev > 65.0:
                    eps.append((s0, prev))
                    s0 = v
                prev = v
            eps.append((s0, prev))
            for t0, t1 in eps:
                if (t1 - t0 + 5.0) < 30.0 - 1e-6:
                    continue
                win = [kk for kk, T in enumerate(DEC) if t0 - 300.0 - 1e-6 <= T <= t0 + 0.1 + 1e-6 and F[i, kk]]
                if not win:
                    continue
                lead_n += 1
                sw = [kk for kk in win if SP[i, Fi[kk]]]
                if any(DEC[kk] + 0.1 < t0 - 0.05 for kk in sw):
                    rec_n += 1
                elif sw:
                    start_n += 1
                else:
                    cnt_only += 1
        r['lead_U_head'] = dict(lead=lead_n, by_recurrence_prior_S=rec_n, at_start_S=start_n, count_only=cnt_only)
        runs[run] = r
    res['runs'] = runs
    with open(out + '.tmp', 'w', encoding='utf-8') as g:
        json.dump(res, g, ensure_ascii=False, sort_keys=True, allow_nan=False)
    os.replace(out + '.tmp', out)
    print(sha(out))


if __name__ == '__main__':
    main()
