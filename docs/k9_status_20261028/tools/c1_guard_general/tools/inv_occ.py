# -*- coding: utf-8 -*-
"""inv_occ.py (guard/general, 2026-10-27 KST) — read-only: decision-time lane occupancy of inventory segments.

Usage: python -B inv_occ.py <inventory.json> <spacing.json> <out.json>
Reads existing decision-time state files (the controller's own observation, /vehicle_records/records) of
V-A and B, v3c3-s31/s41/s43, T >= 900. For every inventory segment: vehicles with link_no == link, lane_no in
lanes, from_m <= position_m <= to_m (codex USG occupancy rule, CX USG:51-56). Fill = vehicles / (length / spacing)
per lane; link-level fill = vehicles on all listed lanes / sum of lane capacities. Spacings: 6.0 m, the FZP median
(pre-declared rule) and the FZP mean (added after seeing the scan). Also a length rule: sum of the lane-frame
vehicle lengths + FZP median gap over the segment length (added after seeing the scan).
Writes only <out.json>. No VISSIM, no COM, no plant. Numbers are exploratory ("데이터 뒤").
"""
import glob
import hashlib
import json
import os
import sys
from collections import defaultdict

RUNS = {
    'VA_s31': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31',
    'VA_s41': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/decisions_sdmpc31_v3c3_k92va_s41',
    'VA_s43': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/decisions_sdmpc31_v3c3_k92va_s43',
    'B_s31': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/decisions_sdmpc31_sdmpc9000_s31',
    'B_s41': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/decisions_sdmpc31_sdmpc9000_s41',
    'B_s43': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/decisions_sdmpc31_sdmpc9000_s43',
}


def segments(inv):
    seg = []
    for a in inv['approach_lanes']:
        if a['role'] != 'controlled_phase':
            continue
        seg.append(dict(id='A:%s:%s:%s' % (a['link'], a['lane'], a['sg']), kind='approach_lane', group='%s:%s' % (a['sc'], a['link']),
                        link=a['link'], lanes=[a['lane']], from_m=a['segment_start_m'], to_m=a['head_pos_m'],
                        sc=a['sc'], sg=a['sg'], phases=a['phases']))
    for f in inv['feeders']:
        for ln in range(1, f['link_lanes'] + 1):
            seg.append(dict(id='F:%s:%s' % (f['link'], ln), kind='feeder_lane', group='F:%s' % f['link'], link=f['link'],
                            lanes=[ln], from_m=f['from_m'], to_m=f['to_m'], servers=f['servers']))
    for name, m in inv['meters'].items():
        for h in m['heads']:
            seg.append(dict(id='M:%s:%s' % (name, h['lane']), kind='meter_prehead_lane', group='M:' + name, link=m['connector'],
                            lanes=[h['lane']], from_m=0.0, to_m=h['head_pos_m'], meter=name))
        a = m['approach_segment']
        for ln in a['lanes']:
            seg.append(dict(id='MA:%s:%s' % (name, ln), kind='meter_approach_lane', group='MA:' + name, link=a['link'],
                            lanes=[ln], from_m=a['from_m'], to_m=a['to_m'], meter=name))
    seg.append(dict(id='D5:129:1', kind='special', group='D5', link='129', lanes=[1], from_m=239.38, to_m=299.99,
                    note='10491 landing to 10490 diverge (METER_NEXT2 D5)'))
    return seg


def main():
    inv_p, sp_p, out = sys.argv[1], sys.argv[2], sys.argv[3]
    inv = json.loads(open(inv_p, 'rb').read().decode('utf-8'))
    sp = json.loads(open(sp_p, 'rb').read().decode('utf-8'))
    S = segments(inv)
    spac = {'6m': 6.0, 'fzp': float(sp['recommended_spacing_m']), 'fzp_mean': float(sp['all']['mean_d_m'])}
    by_link = defaultdict(list)
    for i, s in enumerate(S):
        by_link[s['link']].append(i)
    groups = defaultdict(list)
    for i, s in enumerate(S):
        groups[s['group']].append(i)
    res_runs = {}
    len_runs = {}
    files_meta = {}
    GAP = float(sp['all']['gap_pct']['0.5'])
    for run, d in RUNS.items():
        files = sorted(glob.glob(d + '/state_*.json'))
        rows = []
        lrows = []
        for fp in files:
            T = int(os.path.basename(fp)[6:12])
            if T < 900:
                continue
            raw = open(fp, 'rb').read()
            files_meta[run + ':' + str(T)] = hashlib.sha256(raw).hexdigest()[:16]
            st = json.loads(raw.decode('utf-8-sig'))
            vr = st['vehicle_records']
            if vr.get('complete') is not True:
                raise SystemExit('incomplete records ' + fp)
            # lane frame of the same decision (vehicle lengths); sha must match the state's pointer
            fr = st['obs150']['frames']['current']
            fraw = open(os.path.join(d, fr['path']), 'rb').read()
            if hashlib.sha256(fraw).hexdigest() != fr['sha256']:
                raise SystemExit('lane frame sha mismatch ' + fp)
            ftxt = fraw.decode('utf-16') if fraw[:2] in (bytes([255, 254]), bytes([254, 255])) else fraw.decode('utf-8-sig')
            vlen = {int(r[0]): float(r[5]) for r in json.loads(ftxt)['vehicles']}
            cnt = [0] * len(S)
            used = [0.0] * len(S)
            for v in vr['records']:
                lk = str(v['link_no'])
                if lk not in by_link:
                    continue
                ln = int(v['lane_no'])
                p = float(v['position_m'])
                for i in by_link[lk]:
                    s = S[i]
                    if ln in s['lanes'] and s['from_m'] - 1e-9 <= p <= s['to_m'] + 1e-9:
                        cnt[i] += 1
                        used[i] += vlen[int(v['veh_no'])] + GAP
            rows.append((T, cnt))
            lrows.append((T, used))
        res_runs[run] = rows
        len_runs[run] = lrows
    # summaries
    seg_out = []
    for i, s in enumerate(S):
        L = s['to_m'] - s['from_m']
        r = dict(s)
        r['len_m'] = L
        r['cap_veh'] = {k: (L / v if L > 0 else None) for k, v in spac.items()}
        per = {}
        for run, rows in res_runs.items():
            c = [x[1][i] for x in rows]
            mx = max(c) if c else 0
            e = dict(max_veh=mx)
            for k, v in spac.items():
                cap = L / v if L > 0 else None
                if cap:
                    e['max_fill_' + k] = mx / cap
                    e['n_ge_1.0_' + k] = sum(1 for x in c if x / cap >= 1.0 - 1e-9)
                    e['n_ge_0.9_' + k] = sum(1 for x in c if x / cap >= 0.9 - 1e-9)
                    e['first_T_ge_1.0_' + k] = next((rows[j][0] for j, x in enumerate(c) if x / cap >= 1.0 - 1e-9), None)
            ul = [x[1][i] for x in len_runs[run]]
            if L > 0:
                e['max_fill_len'] = max(ul) / L if ul else 0.0
                e['n_ge_1.0_len'] = sum(1 for x in ul if x / L >= 1.0 - 1e-9)
                e['n_ge_0.9_len'] = sum(1 for x in ul if x / L >= 0.9 - 1e-9)
            per[run] = e
        r['runs'] = per
        seg_out.append(r)
    grp_out = {}
    for g, idx in groups.items():
        Ls = [S[i]['to_m'] - S[i]['from_m'] for i in idx]
        per = {}
        for run, rows in res_runs.items():
            tot = [sum(x[1][i] for i in idx) for x in rows]
            e = dict(max_veh=max(tot) if tot else 0)
            for k, v in spac.items():
                cap = sum(l / v for l in Ls if l > 0)
                if cap:
                    e['max_fill_' + k] = e['max_veh'] / cap
                    e['n_ge_1.0_' + k] = sum(1 for x in tot if x / cap >= 1.0 - 1e-9)
                    e['n_ge_0.9_' + k] = sum(1 for x in tot if x / cap >= 0.9 - 1e-9)
            ul = [sum(x[1][i] for i in idx) for x in len_runs[run]]
            Lt = sum(l for l in Ls if l > 0)
            if Lt > 0:
                e['max_fill_len'] = max(ul) / Lt if ul else 0.0
                e['n_ge_1.0_len'] = sum(1 for x in ul if x / Lt >= 1.0 - 1e-9)
            per[run] = e
        grp_out[g] = dict(members=[S[i]['id'] for i in idx], cap_veh={k: sum(l / v for l in Ls if l > 0) for k, v in spac.items()}, runs=per)
    # decisions with any approach lane >= 1.0 (per spacing)
    dec = {}
    for run, rows in res_runs.items():
        e = {}
        for k, v in spac.items():
            for kind in ('approach_lane', 'feeder_lane', 'meter_prehead_lane', 'meter_approach_lane'):
                n = 0
                for T, c in rows:
                    if any(S[i]['kind'] == kind and (S[i]['to_m'] - S[i]['from_m']) > 0 and c[i] / ((S[i]['to_m'] - S[i]['from_m']) / v) >= 1.0 - 1e-9
                           for i in range(len(S))):
                        n += 1
                e['%s_decisions_any_ge_1.0_%s' % (kind, k)] = n
        e['decisions'] = len(rows)
        dec[run] = e
    res = dict(tool='inv_occ.py', inventory_sha256=hashlib.sha256(open(inv_p, 'rb').read()).hexdigest(),
               spacing_sha256=hashlib.sha256(open(sp_p, 'rb').read()).hexdigest(), spacings=spac,
               length_rule=dict(gap_m=GAP, text='fill_len = sum over vehicles in segment of (lane-frame length + FZP median gap) / segment length (added after seeing the scan)'),
               n_segments=len(S), runs=list(RUNS), state_sha16=files_meta, decisions=dec, segments=seg_out, groups=grp_out,
               raw_counts={run: [[T] + c for T, c in rows] for run, rows in res_runs.items()},
               raw_used_m={run: [[T] + [round(x, 3) for x in c] for T, c in rows] for run, rows in len_runs.items()},
               segment_ids=[s['id'] for s in S])
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(res, g, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, out)
    print('segments', len(S), {r: len(v) for r, v in res_runs.items()})
    print(json.dumps(dec, indent=0))
    print(hashlib.sha256(open(out, 'rb').read()).hexdigest())


if __name__ == '__main__':
    main()
