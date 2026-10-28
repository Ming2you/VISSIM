# -*- coding: utf-8 -*-
"""gd_analyze.py (guard/general DATA, 2026-10-27 KST) — read-only analysis of gd_scan.py outputs.

Usage: python -B gd_analyze.py <scan_dir> <inventory.json> <usg_b.json> <occ.json> <out.json>
Light job (numpy on 12 small npz files). No VISSIM, no COM, no FZP reads. All thresholds/windows are "data after".
Definitions fixed in LOG_GENERAL 17:10 KST before the scan:
  occupancy  = vehicles / (len / spacing), spacing 6.0 / FZP median / FZP mean; length occupancy = sum(len + 1.51) / len
  decisions  = T = 900..8850 step 150 (FZP frame T + 0.1; the FZP has no 9,000.1 frame)
  bins       = 300 s, 900..9,000 s (27), time mean and max of 5 s frames
  spill S    = see gd_scan.py; episode = S frames merged when the off gap <= 60 s
  lead       = a trigger decision in [t0 - 300, t0]; late = first trigger in (t0, t1]; miss = neither
  false trig = trigger decision T with no S frame in [T - 150, T + 300]
  freeway block = S0 on any lane of the off-ramp connector AND >= 1 vehicle < 20 km/h in [diverge - 100, diverge]
"""
import hashlib
import json
import os
import sys
from collections import defaultdict

import numpy as np

ARMS = ['NC3', 'VSL', 'VA', 'B']
SEEDS = ['s31', 's41', 's43']
RUNS = ['%s_%s' % (a, s) for s in SEEDS for a in ARMS]
if os.environ.get('GD_TEST_RUNS'):
    RUNS = os.environ['GD_TEST_RUNS'].split(',')  # dry test only
DEC = list(range(900, 8851, 150))
BINS = list(range(900, 9000, 300))
RULES = [('lane6_1.0', 'occ6', 1.0), ('lane6_0.9', 'occ6', 0.9), ('laneL_1.0', 'occL', 1.0), ('laneF_1.0', 'occF', 1.0),
         ('laneM_1.0', 'occM', 1.0), ('laneL_0.9', 'occL', 0.9)]
MAIN_RULES = ['lane6_1.0', 'lane6_0.9', 'laneL_1.0']
GRULES = [('link6_1.0', 'occ6', 1.0), ('link6_0.9', 'occ6', 0.9), ('linkL_1.0', 'occL', 1.0)]

CHAINS = {
    'c127': ['A:127:1:2', 'A:127:2:2', 'A:127:3:5', 'L:10481:127:1', 'L:10481:127:2', 'F:10481:1', 'F:10481:2', 'W:10481',
             'F:10777:1', 'F:10777:2', 'F:10777:3', 'F:129:1', 'F:129:2', 'F:129:3', 'D5:129:1', 'L:10491:129:1', 'F:10491:1', 'W:10491'],
    'c10643': ['A:71:1:2', 'A:71:2:2', 'A:71:3:2', 'A:71:4:5', 'A:71:5:5', 'F:10641:1', 'F:10641:2', 'F:10700:1', 'F:126:1', 'F:126:2',
               'L:10643:126:1', 'L:10643:126:2', 'F:10643:1', 'F:10643:2', 'W:10643', 'F:10776:1', 'F:10776:2', 'F:70:1', 'F:70:2'],
    'c10483': ['M:RM_C10480:1', 'MA:RM_C10480:1', 'F:124:1', 'L:10483:124:1', 'F:10483:1', 'W:10483'],
    'c10682': ['M:RM_C10646:1', 'MA:RM_C10646:1', 'F:121:1', 'L:10682:121:1', 'F:10682:1', 'W:10682'],
    'rm10484': ['M:RM_C10484:1', 'MA:RM_C10484:1', 'F:31:1', 'F:10119:1', 'F:10119:2', 'F:10121:1', 'F:10698:1', 'F:10703:1', 'F:10703:2'],
    'rm10490': ['M:RM_C10490:1', 'MA:RM_C10490:1', 'D5:129:1', 'F:10778:1', 'F:10778:2', 'F:10778:3', 'F:32:1'],
    'rm10639': ['M:RM_C10639:1', 'MA:RM_C10639:1', 'F:70:1', 'L:10638:70:1', 'F:10637:1', 'F:10637:2', 'F:10638:1', 'F:10638:2', 'W:10638'],
    'rm10681': ['M:RM_C10681:1', 'M:RM_C10681:2', 'MA:RM_C10681:1', 'MA:RM_C10681:2', 'F:68:1', 'F:68:2', 'F:10625:1', 'F:10629:1',
                'F:10629:2', 'F:10629:3', 'F:10633:1'],
}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def episodes(times, mask):
    idx = np.nonzero(mask)[0]
    if not len(idx):
        return []
    t = times[idx]
    out = []
    s0 = t[0]
    prev = t[0]
    for x in t[1:]:
        if x - prev > 65.0:
            out.append((float(s0), float(prev)))
            s0 = x
        prev = x
    out.append((float(s0), float(prev)))
    return out


def compare(eps, trig_T, s_times):
    """eps: list of (t0, t1); trig_T: sorted decision times with trigger; s_times: sorted S frame times."""
    res = dict(n_ep=len(eps), lead=0, late=0, miss=0, lead_s=[], lag_s=[], n_trig=len(trig_T), true_trig=0, false_trig=0,
               n_ep30=0, lead30=0, late30=0, miss30=0)
    tt = np.array(trig_T, float)
    for t0, t1 in eps:
        long_ = (t1 - t0 + 5.0) >= 30.0 - 1e-6   # episode lasting >= 30 s (data after)
        res['n_ep30'] += int(long_)
        w = tt[(tt >= t0 - 300.0 - 1e-6) & (tt <= t0 + 0.1 + 1e-6)]
        if len(w):
            res['lead'] += 1
            res['lead30'] += int(long_)
            res['lead_s'].append(round(t0 - float(w.min()), 1))
            continue
        w = tt[(tt > t0 + 0.1) & (tt <= t1 + 1e-6)]
        if len(w):
            res['late'] += 1
            res['late30'] += int(long_)
            res['lag_s'].append(round(float(w.min()) - t0, 1))
        else:
            res['miss'] += 1
            res['miss30'] += int(long_)
    st = np.array(s_times, float)
    for T in trig_T:
        if len(st) and np.any((st >= T - 150.0) & (st <= T + 300.0 + 0.2)):
            res['true_trig'] += 1
        else:
            res['false_trig'] += 1
    return res


def clean(o):
    if isinstance(o, float):
        return o if np.isfinite(o) else None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.generic):
        return clean(o.item())
    return o


def main():
    scan_dir, inv_p, usg_p, occ_p, out = sys.argv[1:6]
    inv = json.loads(open(inv_p, 'rb').read().decode('utf-8'))
    segj = json.loads(open(os.path.join(scan_dir, 'segments.json'), 'rb').read().decode('utf-8'))
    seg = segj['segments']
    fws = segj['fws']
    ids = [s['id'] for s in seg]
    idx = {s: i for i, s in enumerate(ids)}
    S = len(seg)
    spac = {'6': 6.0, 'F': float(inv['spacing']['fzp_m']), 'M': float(inv['spacing']['fzp_mean_m'])}
    L = np.array([s['to_m'] - s['from_m'] for s in seg])
    Lp = np.where(L > 0, L, np.nan)
    cap6 = Lp / 6.0
    short = cap6 < 2.0
    groups = defaultdict(list)
    for i, s in enumerate(seg):
        groups[s['group']].append(i)
    gnames = sorted(groups)
    sources = dict(inventory_sha256=sha(inv_p), segments_json_sha256=sha(os.path.join(scan_dir, 'segments.json')),
                   usg_b_sha256=sha(usg_p), occ_json_sha256=sha(occ_p), tool_sha256=sha(__file__), npz={}, fzp={})
    per_seg = {sid: dict(meta={k: v for k, v in seg[i].items() if k not in ('id',)}, len_m=float(L[i]),
                         cap_veh={k: (float(L[i] / v) if L[i] > 0 else None) for k, v in spac.items()}, short=bool(short[i]), runs={})
               for i, sid in enumerate(ids)}
    per_grp = {g: dict(members=[ids[i] for i in groups[g]], cap6=float(np.nansum(cap6[groups[g]])), runs={}) for g in gnames}
    series = {}
    chain_out = {c: {} for c in CHAINS}
    fw_out = {}
    xcheck = {}
    arm_sum = {}
    upstream_block = {}
    occ = json.loads(open(occ_p, 'rb').read().decode('utf-8'))
    key_ids = sorted(set(x for v in CHAINS.values() for x in v if not x.startswith('W:')))
    dec_store = {}
    for run in RUNS:
        npz = os.path.join(scan_dir, run + '.npz')
        meta = json.loads(open(npz[:-4] + '.meta.json', 'rb').read().decode('utf-8'))
        sources['npz'][run] = sha(npz)
        sources['fzp'][run] = dict(name=meta['fzp_name'], sha256=meta['fzp_sha256'], frames=meta['frames'], rows=meta['rows'])
        assert meta['seg_ids'] == ids
        z = np.load(npz)
        cnt = z['cnt'].astype(np.float64)
        lsum = z['lsum'].astype(np.float64)
        flg = z['flg']
        times = z['times']
        w_n, w_v, w_s = z['w_n'], z['w_v'], z['w_s']
        tix = {round(float(t), 1): k for k, t in enumerate(times)}
        F = np.array([tix[round(T + 0.1, 1)] for T in DEC])
        fm = times >= 900.0
        tt = times[fm]
        occ6 = cnt / cap6[:, None]
        occL = lsum / Lp[:, None]
        occF = cnt / (Lp / spac['F'])[:, None]
        occM = cnt / (Lp / spac['M'])[:, None]
        SP = (flg & 2) > 0
        S0 = (flg & 1) > 0
        nqa = z['nq'].astype(np.float64)
        SQ = SP & (nqa >= 0.8 * cnt - 1e-9)   # strict variant (data after): S and >= 80 % of segment vehicles < 5 km/h
        D = dict(occ6=occ6[:, F], occL=occL[:, F], occF=occF[:, F], occM=occM[:, F])
        dec_store[run] = D
        # group level
        gcnt = np.array([cnt[groups[g]].sum(0) for g in gnames])
        gcap = np.array([np.nansum(cap6[groups[g]]) for g in gnames])
        gL = np.array([np.nansum(Lp[groups[g]]) for g in gnames])
        glsum = np.array([lsum[groups[g]].sum(0) for g in gnames])
        GSP = np.array([SP[groups[g]].any(0) for g in gnames])
        GD = dict(occ6=(gcnt / gcap[:, None])[:, F], occL=(glsum / gL[:, None])[:, F])
        # bins
        bmask = [(times >= b) & (times < b + 300.0) for b in BINS]
        # cross-check with controller observation (V-A, B)
        if run.startswith('VA') or run.startswith('B_'):
            oid = occ['segment_ids']
            R = np.array(occ['raw_counts'][run])
            ok = [k for k, T in enumerate(R[:, 0]) if round(T + 0.1, 1) in tix]
            FF = np.array([tix[round(R[k, 0] + 0.1, 1)] for k in ok])
            oi = np.array([idx[s] for s in oid])
            d = cnt[oi][:, FF].T - R[ok, 1:]
            u, c = np.unique(d.astype(int), return_counts=True)
            xcheck[run] = dict(decisions=len(ok), cells=int(d.size), equal_share=float((d == 0).mean()),
                               diff_hist={str(a): int(b) for a, b in zip(u, c)})
        # per segment
        for i, sid in enumerate(ids):
            e = {}
            if L[i] > 0:
                for name, key, th in RULES:
                    v = D[key][i]
                    hit = v >= th - 1e-9
                    e['n_' + name] = int(hit.sum())
                    e['first_' + name] = int(DEC[int(np.argmax(hit))]) if hit.any() else None
                e['max_occ6'] = round(float(np.nanmax(D['occ6'][i])), 4)
                e['max_occL'] = round(float(np.nanmax(D['occL'][i])), 4)
                e['max_veh'] = int(cnt[i, F].max())
                bm6 = [float(occ6[i, m].mean()) for m in bmask]
                bx6 = [float(occ6[i, m].max()) for m in bmask]
                e['bins_mean_ge1_6'] = int(sum(x >= 1.0 - 1e-9 for x in bm6))
                e['bins_mean_ge09_6'] = int(sum(x >= 0.9 - 1e-9 for x in bm6))
                e['bins_max_ge1_6'] = int(sum(x >= 1.0 - 1e-9 for x in bx6))
                e['bins_max_ge09_6'] = int(sum(x >= 0.9 - 1e-9 for x in bx6))
            sp = SP[i] & fm
            e['spill_s'] = int(sp.sum()) * 5
            e['s0_s'] = int((S0[i] & fm).sum()) * 5
            if L[i] > 0:
                e['frames_ge1_6_s'] = int(((occ6[i] >= 1.0 - 1e-9) & fm).sum()) * 5
                e['frames_ge09_6_s'] = int(((occ6[i] >= 0.9 - 1e-9) & fm).sum()) * 5
                e['frames_ge1_L_s'] = int(((occL[i] >= 1.0 - 1e-9) & fm).sum()) * 5
                if sp.any():
                    e['occ6_at_S_q'] = [round(float(x), 3) for x in np.percentile(occ6[i][sp], [10, 50, 90])]
                    e['occL_at_S_q'] = [round(float(x), 3) for x in np.percentile(occL[i][sp], [10, 50, 90])]
            eps = episodes(times, sp)
            e['n_ep'] = len(eps)
            e['first_spill'] = round(eps[0][0], 1) if eps else None
            e['ep_head'] = [[round(a, 1), round(b, 1)] for a, b in eps[:12]]
            st = times[sp]
            spq = SQ[i] & fm
            epq = episodes(times, spq)
            e['spill_q_s'] = int(spq.sum()) * 5
            e['n_ep_q'] = len(epq)
            e['first_spill_q'] = round(epq[0][0], 1) if epq else None
            if L[i] > 0:
                cq = {}
                for name, key, th in RULES:
                    if name in MAIN_RULES:
                        trig = [DEC[k] for k in np.nonzero(D[key][i] >= th - 1e-9)[0]]
                        cq[name] = compare(epq, trig, times[spq])
                gq = gnames.index(seg[i]['group'])
                for name, key, th in GRULES:
                    trig = [DEC[k] for k in np.nonzero(GD[key][gq] >= th - 1e-9)[0]]
                    cq[name] = compare(epq, trig, times[spq])
                e['cmp_q'] = cq
                if spq.any():
                    e['occ6_at_SQ_q'] = [round(float(x), 3) for x in np.percentile(occ6[i][spq], [10, 50, 90])]
            if L[i] > 0:
                cmp_ = {}
                for name, key, th in RULES:
                    if name not in MAIN_RULES:
                        continue
                    trig = [DEC[k] for k in np.nonzero(D[key][i] >= th - 1e-9)[0]]
                    cmp_[name] = compare(eps, trig, st)
                g = seg[i]['group']
                gi = gnames.index(g)
                for name, key, th in GRULES:
                    trig = [DEC[k] for k in np.nonzero(GD[key][gi] >= th - 1e-9)[0]]
                    cmp_[name] = compare(eps, trig, st)
                e['cmp'] = cmp_
            if sid in key_ids:
                series.setdefault(sid, {})[run] = dict(
                    dec_occ6=[round(float(x), 3) for x in D['occ6'][i]], dec_occL=[round(float(x), 3) for x in D['occL'][i]],
                    dec_veh=[int(x) for x in cnt[i, F]],
                    bin_mean_occ6=[round(float(occ6[i, m].mean()), 3) for m in bmask],
                    bin_max_occ6=[round(float(occ6[i, m].max()), 3) for m in bmask],
                    bin_spill_s=[int(SP[i, m].sum()) * 5 for m in bmask], bin_s0_s=[int(S0[i, m].sum()) * 5 for m in bmask])
            per_seg[sid]['runs'][run] = e
        # per group
        for gi, g in enumerate(gnames):
            e = {}
            for name, key, th in GRULES:
                hit = GD[key][gi] >= th - 1e-9
                e['n_' + name] = int(hit.sum())
                e['first_' + name] = int(DEC[int(np.argmax(hit))]) if hit.any() else None
            e['max_occ6'] = round(float(np.nanmax(GD['occ6'][gi])), 4)
            e['max_occL'] = round(float(np.nanmax(GD['occL'][gi])), 4)
            sp = GSP[gi] & fm
            e['spill_s'] = int(sp.sum()) * 5
            eps = episodes(times, sp)
            e['n_ep'] = len(eps)
            e['first_spill'] = round(eps[0][0], 1) if eps else None
            st = times[sp]
            cmp_ = {}
            for name, key, th in GRULES:
                trig = [DEC[k] for k in np.nonzero(GD[key][gi] >= th - 1e-9)[0]]
                cmp_[name] = compare(eps, trig, st)
            e['cmp'] = cmp_
            per_grp[g]['runs'][run] = e
        # freeway windows and freeway block
        fwr = {}
        for j, w in enumerate(fws):
            lanes = [k for k, s in enumerate(seg) if s['kind'] == 'feeder_lane' and s['link'] == w['offramp']]
            s0c = S0[lanes].any(0)
            spc = SP[lanes].any(0)
            fb = s0c & (w_s[j] >= 1) & fm
            eps = episodes(times, fb)
            vv = w_v[j].astype(float)
            fwr[w['id']] = dict(road=w['road'], offramp=w['offramp'], block_s=int(fb.sum()) * 5, n_ep=len(eps),
                                first_block=round(eps[0][0], 1) if eps else None, ep_head=[[round(a, 1), round(b, 1)] for a, b in eps[:12]],
                                offramp_S_s=int((spc & fm).sum()) * 5, offramp_S0_s=int((s0c & fm).sum()) * 5,
                                slow_last100_s=int(((w_s[j] >= 1) & fm).sum()) * 5,
                                bin_mean_speed=[(round(float(np.nanmean(vv[m])), 1) if np.isfinite(vv[m]).any() else None) for m in bmask],
                                bin_block_s=[int((fb & m).sum()) * 5 for m in bmask],
                                bin_slow_s=[int(((w_s[j] >= 1) & m).sum()) * 5 for m in bmask])
        fw_out[run] = fwr
        # chains: first spill / first trigger per element
        for c, members in CHAINS.items():
            rows = []
            for sid in members:
                if sid.startswith('W:'):
                    f = fwr[sid]
                    rows.append(dict(id=sid, first_spill=f['first_block'], spill_s=f['block_s']))
                    continue
                e = per_seg[sid]['runs'][run]
                rows.append(dict(id=sid, first_spill=e['first_spill'], spill_s=e['spill_s'], n_ep=e['n_ep'],
                                 first_spill_q=e['first_spill_q'], spill_q_s=e['spill_q_s'],
                                 max_occ6=e.get('max_occ6'), max_occL=e.get('max_occL'), max_veh=e.get('max_veh'),
                                 first_lane6_1=e.get('first_lane6_1.0'), first_lane6_09=e.get('first_lane6_0.9'),
                                 first_laneL_1=e.get('first_laneL_1.0'), n_lane6_1=e.get('n_lane6_1.0'), n_lane6_09=e.get('n_lane6_0.9'),
                                 n_laneL_1=e.get('n_laneL_1.0'),
                                 group=seg[idx[sid]]['group'],
                                 first_link6_1=per_grp[seg[idx[sid]]['group']]['runs'][run]['first_link6_1.0'],
                                 first_link6_09=per_grp[seg[idx[sid]]['group']]['runs'][run]['first_link6_0.9']))
            chain_out[c][run] = rows
        # upstream intersection blocking (feeders whose upstream boundary is a stop line)
        ub = []
        for i, s in enumerate(seg):
            if s['kind'] == 'feeder_lane' and s.get('upstream_stopline'):
                e = per_seg[s['id']]['runs'][run]
                if e['spill_s'] > 0:
                    ub.append((s['id'], e['spill_s'], e['n_ep'], e['first_spill']))
        ub.sort(key=lambda x: -x[1])
        upstream_block[run] = dict(n_feeder_lanes=sum(1 for s in seg if s['kind'] == 'feeder_lane' and s.get('upstream_stopline')),
                                   n_with_spill=len(ub), total_spill_s=int(sum(x[1] for x in ub)), top=ub[:15])
        # arm summary: decisions with any trigger (non-short), spill totals by kind
        a = {}
        for kind in ('approach_lane', 'feeder_lane', 'meter_prehead_lane', 'meter_approach_lane', 'offramp_landing_lane', 'special'):
            ki = np.array([i for i, s in enumerate(seg) if s['kind'] == kind and not short[i] and L[i] > 0])
            if not len(ki):
                continue
            a[kind] = dict(n_seg=int(len(ki)),
                           dec_any_lane6_1=int((D['occ6'][ki] >= 1.0 - 1e-9).any(0).sum()),
                           dec_any_lane6_09=int((D['occ6'][ki] >= 0.9 - 1e-9).any(0).sum()),
                           dec_any_laneL_1=int((D['occL'][ki] >= 1.0 - 1e-9).any(0).sum()),
                           seg_ever_lane6_1=int((D['occ6'][ki] >= 1.0 - 1e-9).any(1).sum()),
                           seg_ever_lane6_09=int((D['occ6'][ki] >= 0.9 - 1e-9).any(1).sum()),
                           seg_ever_laneL_1=int((D['occL'][ki] >= 1.0 - 1e-9).any(1).sum()),
                           seg_with_spill=int((SP[ki][:, fm]).any(1).sum()),
                           spill_s=int(SP[ki][:, fm].sum()) * 5)
        for kind in list(a):
            ki = np.array([i for i, s in enumerate(seg) if s['kind'] == kind and not short[i] and L[i] > 0])
            m = SP[ki][:, fm]
            if m.any():
                o6 = occ6[ki][:, fm][m]
                oL = occL[ki][:, fm][m]
                a[kind]['occ6_at_S_q10_50_90'] = [round(float(x), 3) for x in np.percentile(o6, [10, 50, 90])]
                a[kind]['occL_at_S_q10_50_90'] = [round(float(x), 3) for x in np.percentile(oL, [10, 50, 90])]
                a[kind]['share_S_frames_occ6_ge1'] = round(float((o6 >= 1.0 - 1e-9).mean()), 4)
                a[kind]['share_S_frames_occL_ge1'] = round(float((oL >= 1.0 - 1e-9).mean()), 4)
                a[kind]['share_S_frames_occ6_ge09'] = round(float((o6 >= 0.9 - 1e-9).mean()), 4)
            a[kind]['frames_any_ge1_6_s'] = int(((occ6[ki] >= 1.0 - 1e-9).any(0) & fm).sum()) * 5
            mq = SQ[ki][:, fm]
            a[kind]['seg_with_spill_q'] = int(mq.any(1).sum())
            a[kind]['spill_q_s'] = int(mq.sum()) * 5
            if mq.any():
                o6 = occ6[ki][:, fm][mq]
                oL = occL[ki][:, fm][mq]
                a[kind]['occ6_at_SQ_q10_50_90'] = [round(float(x), 3) for x in np.percentile(o6, [10, 50, 90])]
                a[kind]['occL_at_SQ_q10_50_90'] = [round(float(x), 3) for x in np.percentile(oL, [10, 50, 90])]
                a[kind]['share_SQ_frames_occ6_ge1'] = round(float((o6 >= 1.0 - 1e-9).mean()), 4)
                a[kind]['share_SQ_frames_occ6_ge09'] = round(float((o6 >= 0.9 - 1e-9).mean()), 4)
                a[kind]['share_SQ_frames_occL_ge1'] = round(float((oL >= 1.0 - 1e-9).mean()), 4)
        # sensitivity (data after): approach + feeder lanes with capacity >= 5 / >= 10 vehicles (6 m)
        for cmin in (5.0, 10.0):
            ki = np.array([i for i, s in enumerate(seg) if s['kind'] in ('approach_lane', 'feeder_lane') and L[i] > 0 and cap6[i] >= cmin])
            a['cap_ge_%d' % int(cmin)] = dict(n_seg=int(len(ki)),
                                              dec_any_lane6_1=int((D['occ6'][ki] >= 1.0 - 1e-9).any(0).sum()),
                                              dec_any_lane6_09=int((D['occ6'][ki] >= 0.9 - 1e-9).any(0).sum()),
                                              dec_any_laneL_1=int((D['occL'][ki] >= 1.0 - 1e-9).any(0).sum()))
        # per signal (approach lanes, non-short): decisions with any lane trigger
        per_sc = {}
        for sc in sorted(set(s['sc'] for s in seg if s['kind'] == 'approach_lane')):
            ki = np.array([i for i, s in enumerate(seg) if s['kind'] == 'approach_lane' and s['sc'] == sc and not short[i] and L[i] > 0])
            if not len(ki):
                continue
            per_sc[sc] = [int((D['occ6'][ki] >= 1.0 - 1e-9).any(0).sum()), int((D['occ6'][ki] >= 0.9 - 1e-9).any(0).sum()),
                          int((D['occL'][ki] >= 1.0 - 1e-9).any(0).sum()), int(SP[ki][:, fm].any(0).sum()) * 5]
        a['per_sc'] = per_sc
        ki = np.array([i for i in range(S) if short[i]])
        a['short_cap_lt2'] = dict(n_seg=int(len(ki)), seg_with_spill=int((SP[ki][:, fm]).any(1).sum()),
                                  seg_ever_lane6_1=int((D['occ6'][ki] >= 1.0 - 1e-9).any(1).sum()))
        arm_sum[run] = a
    # aggregate comparison per rule, per arm, per kind (non-short)
    agg = {}
    aggq = {}
    for run in RUNS:
        for kind in ('approach_lane', 'feeder_lane', 'meter_prehead_lane', 'meter_approach_lane', 'offramp_landing_lane'):
            for rule in MAIN_RULES + [r[0] for r in GRULES]:
                k = '%s|%s|%s' % (run, kind, rule)
                t = dict(n_ep=0, lead=0, late=0, miss=0, n_trig=0, true_trig=0, false_trig=0, lead_s=[], lag_s=[],
                         n_ep30=0, lead30=0, late30=0, miss30=0)
                for i, s in enumerate(seg):
                    if s['kind'] != kind or short[i] or not L[i] > 0:
                        continue
                    c = per_seg[s['id']]['runs'][run]['cmp'][rule]
                    for x in ('n_ep', 'lead', 'late', 'miss', 'n_trig', 'true_trig', 'false_trig', 'n_ep30', 'lead30', 'late30', 'miss30'):
                        t[x] += c[x]
                    t['lead_s'] += c['lead_s']
                    t['lag_s'] += c['lag_s']
                t['lead_s_median'] = float(np.median(t['lead_s'])) if t['lead_s'] else None
                t['lag_s_median'] = float(np.median(t['lag_s'])) if t['lag_s'] else None
                del t['lead_s'], t['lag_s']
                agg[k] = t
                tq = dict(n_ep=0, lead=0, late=0, miss=0, n_trig=0, true_trig=0, false_trig=0, n_ep30=0, lead30=0, late30=0, miss30=0)
                for i, s in enumerate(seg):
                    if s['kind'] != kind or short[i] or not L[i] > 0:
                        continue
                    c = per_seg[s['id']]['runs'][run]['cmp_q'][rule]
                    for x in tq:
                        tq[x] += c[x]
                aggq[k] = tq
    # V-A trigger list (non-short)
    va = {}
    for sid in ids:
        i = idx[sid]
        if short[i] or not L[i] > 0:
            continue
        r = {}
        for run in [x for x in ('VA_s31', 'VA_s41', 'VA_s43') if x in RUNS]:
            e = per_seg[sid]['runs'][run]
            r[run] = [e['n_lane6_1.0'], e['n_lane6_0.9'], e['n_laneL_1.0'], e['spill_s']]
        if any(v[0] or v[1] or v[2] for v in r.values()):
            va[sid] = r
    # USG (B)
    usg = json.loads(open(usg_p, 'rb').read().decode('utf-8'))
    a_map = {}
    for i, s in enumerate(seg):
        if s['kind'] == 'approach_lane':
            a_map.setdefault(('SC' + s['sc'].replace('SC', ''), s['link'], int(s['lane'])), []).append(i)
    usg_out = {}
    for seed, rows in usg['runs'].items():
        run = 'B_' + seed
        if run not in RUNS:
            continue
        D = dec_store[run]
        npz = np.load(os.path.join(scan_dir, run + '.npz'))
        times = npz['times']
        SP = (npz['flg'] & 2) > 0
        fired = []
        crowded_not_fired = 0
        veh_eq = veh_tot = 0
        for r in rows:
            T = r['T']
            if T not in DEC or 'lanes' not in r:
                continue
            k = DEC.index(T)
            for l in r['lanes']:
                key = (l['signal'], l['link'], l['lane'])
                ii = a_map.get(key)
                if not ii:
                    continue
                i = ii[0]
                mine = int(round(D['occ6'][i, k] * cap6[i]))
                veh_tot += 1
                veh_eq += int(mine == l['veh'])
                if l['pressure'] == 0:
                    if l['crowded']:
                        crowded_not_fired += 1
                    continue
                sp = SP[i][(times >= T - 150.0) & (times <= T + 300.2)].any()
                gi = gnames.index(seg[i]['group'])
                fired.append(dict(T=T, signal=l['signal'], phase=l['phase'], link=l['link'], lane=l['lane'], seg=ids[i],
                                  score=round(l['pressure'], 4), codex_veh=l['veh'], codex_fill=round(l['fill'], 4),
                                  fzp_veh=mine, lane6=round(float(D['occ6'][i, k]), 4), laneL=round(float(D['occL'][i, k]), 4),
                                  all_full=l['all_full'], crowded=l['crowded'], spill_near=bool(sp), short=bool(short[i]),
                                  link6=round(float((np.array([dec_store[run]['occ6'][j, k] * cap6[j] for j in groups[seg[i]['group']]]).sum())
                                                    / np.nansum(cap6[groups[seg[i]['group']]])), 4)))
        rec = defaultdict(int)
        for r in rows:
            for b in r.get('receipts', []):
                rec[b['status']] += 1
        n_dec_fired = len(set(f['T'] for f in fired))
        by_sp = defaultdict(lambda: dict(n=0, ge1_6=0, ge1_L=0, spill_near=0, all_full=0, T=[], short=False))
        for f in fired:
            b = by_sp['%s|%s|%s:%s' % (f['signal'], f['phase'], f['link'], f['lane'])]
            b['n'] += 1
            b['ge1_6'] += int(f['lane6'] >= 1.0 - 1e-9)
            b['ge1_L'] += int(f['laneL'] >= 1.0 - 1e-9)
            b['spill_near'] += int(f['spill_near'])
            b['all_full'] += int(f['all_full'])
            b['T'].append(f['T'])
            b['short'] = f['short']
        usg_out[run] = dict(decisions=len([r for r in rows if r['T'] in DEC]), decisions_fired=n_dec_fired, lane_fires=len(fired),
                            fires_score_pos=sum(1 for f in fired if f['score'] > 0), fires_all_full=sum(1 for f in fired if f['all_full']),
                            fires_lane6_ge1=sum(1 for f in fired if f['lane6'] >= 1.0 - 1e-9),
                            fires_laneL_ge1=sum(1 for f in fired if f['laneL'] >= 1.0 - 1e-9),
                            fires_spill_near=sum(1 for f in fired if f['spill_near']),
                            fires_link6_ge1=sum(1 for f in fired if f['link6'] >= 1.0 - 1e-9),
                            crowded_without_receiver=crowded_not_fired, receipts=dict(rec),
                            fires_short=sum(1 for f in fired if f['short']),
                            fires_long=sum(1 for f in fired if not f['short']),
                            fires_long_lane6_ge1=sum(1 for f in fired if not f['short'] and f['lane6'] >= 1.0 - 1e-9),
                            fires_long_laneL_ge1=sum(1 for f in fired if not f['short'] and f['laneL'] >= 1.0 - 1e-9),
                            fires_long_spill_near=sum(1 for f in fired if not f['short'] and f['spill_near']),
                            fires_long_all_full=sum(1 for f in fired if not f['short'] and f['all_full']),
                            veh_match=dict(equal=veh_eq, total=veh_tot),
                            by_lane=dict(sorted(((k, dict(v)) for k, v in by_sp.items()), key=lambda kv: -kv[1]['n'])),
                            fires=fired)
    res = dict(schema='c1g-general-data/v1', created_note='data after; no verdicts', sources=sources,
               definitions=__doc__, runs=RUNS, decisions=DEC, bins=BINS, spacing=spac, xcheck_controller=xcheck,
               arm_summary=arm_sum, agg_compare=agg, agg_compare_strict=aggq, chains=chain_out, freeway=fw_out, upstream_block=upstream_block,
               va_triggers=va, usg=usg_out, series=series, per_group=per_grp, per_segment=per_seg)
    with open(out + '.tmp', 'w', encoding='utf-8') as g:
        json.dump(clean(res), g, ensure_ascii=False, sort_keys=True, allow_nan=False)
    os.replace(out + '.tmp', out)
    print(sha(out))


if __name__ == '__main__':
    main()
