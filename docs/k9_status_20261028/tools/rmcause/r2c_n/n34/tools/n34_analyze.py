# -*- coding: utf-8 -*-
"""N34 analysis (2026-10-24). Reads n34/out/scan_*.json, n34/out/model_va_*.json, RM decision_<T>.json (green), and
O4 rows (cross-check only). Writes n34/out/n34_analysis.json. No FZP reads.

Definitions fixed before the scan outputs were read (also in N34_FLOWS.md section 2):
N3 window = (T+0.1, T+450.1] in FZP frame time (k = T/5+1 .. T/5+90), T = V-A decision with window end <= 9000.
  VISSIM: E = 129->10490 transitions; I32 = first records on link 32 (input 1102); I3 = those with route 1136:3;
  S3_0 / S3_1 = route-1136:3 vehicles on links 32+129 at frame k0 = T/5 / k0+90.
  Model: A = arrival:SC1001_W_to_onE, G = input:gate:in_SC1001_W, beta = gate_onramp_beta_SC1001_W_to_onE.
  A - E = (beta*G - I3) + ((A - beta*G) - (E - I3)).
N4 block = (T+0.1, T+150.1] (k = T/5+1 .. T/5+30), green = decision_<T>.json meters[m].green_sec (RM arms; V-A all g10).
  Per lane: crossings of the head (cross + entry_past_head) x 24 = veh/h/lane.
  Q (standing queue): all 30 frames have >= 1 vehicle on that lane within 50 m upstream of the head at < 15 km/h.
  B (not blocked downstream): block mean of slow (< 15 km/h) vehicles past the head on that lane < 0.5 x post-head storage
      (post-head length / 6.0 m).
  Primary = Q and B. Secondary = (>= 24 of 30 frames) and B.
  Model service table per lane = 360 x per_lane_veh_per_cycle[g] (CFG actuation.real_world_ramp_metering);
  PRB:476-495 rate_vph = g x capacity_vph(900) / cycle(10) = 90 g per meter (per lane = 90 g / lanes).
"""
import csv
import glob
import json
import os
import statistics as st

N34 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(N34, 'out')
O1O4 = os.path.join(os.path.dirname(os.path.dirname(N34)), 'o1o4')
TABLE = {2: 0.71, 3: 0.99, 4: 1.44, 5: 1.89, 6: 2.34, 7: 2.79, 8: 3.24, 9: 3.69, 10: 4.2}
LANES = {10639: 1, 10681: 2, 10490: 1, 10484: 1, 10480: 1, 10482: 2, 10646: 1, 10644: 1}
CONNLEN = {10639: 408.45, 10681: 437.52, 10490: 368.38, 10484: 541.91, 10480: 249.76, 10482: 528.87, 10646: 395.88, 10644: 1023.2}
MID = {10480: 'RM_C10480', 10482: 'RM_C10482', 10646: 'RM_C10646', 10644: 'RM_C10644', 10639: 'RM_C10639', 10681: 'RM_C10681',
       10490: 'RM_C10490', 10484: 'RM_C10484'}
RMDIR = {'rm_s31': r'D:\VISSIM_runs\20261001_v3c3\s31_v3c3rm\run', 'rm_s41': r'D:\VISSIM_runs\20261001_v3c3\s41_v3c3rm\run'}


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    i = (len(xs) - 1) * p
    lo = int(i)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def summ(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {'n': len(xs), 'median': st.median(xs), 'p10': q(xs, 0.1), 'p90': q(xs, 0.9), 'min': min(xs), 'max': max(xs),
            'mean': sum(xs) / len(xs)}


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def index_scan(S):
    tr = {}
    for k, a, b, tg, n in S['trans']:
        tr.setdefault((a, b), []).append((k, tg, n))
    stock = {}
    for k, L, ln, tg, s, n in S['stock']:
        key = (k, L, tg)
        stock[key] = stock.get(key, 0) + n
    stock_slow = {}
    for k, L, ln, tg, s, n in S['stock']:
        if s:
            key = (k, L, tg)
            stock_slow[key] = stock_slow.get(key, 0) + n
    ins = {int(k): n for k, n in S['ins32'].items()}
    return tr, stock, stock_slow, ins


def count_tr(tr, pairs, k1, k2, tags=None):
    n = 0
    for pr in pairs:
        for k, tg, c in tr.get(pr, ()):
            if k1 <= k <= k2 and (tags is None or tg in tags):
                n += c
    return n


def n3():
    res = {'per_run': {}, 'rows': []}
    allrows = []
    for tag in ('va_s31', 'va_s41', 'va_s43'):
        S = load(os.path.join(OUT, 'scan_%s.json' % tag))
        M = load(os.path.join(OUT, 'model_%s.json' % tag))
        tr, stock, stock_slow, ins = index_scan(S)
        veh = S['veh32']
        rows = []
        for r in M['records']:
            T = r['T']
            k0 = int(round(T / 5.0))
            k1, k2 = k0 + 1, k0 + 90
            E = count_tr(tr, [(129, 10490)], k1, k2)
            E3 = count_tr(tr, [(129, 10490)], k1, k2, {'1136:3'})
            E_prev = count_tr(tr, [(129, 10490)], k0 - 29, k0)
            E10482 = count_tr(tr, [(32, 10482)], k1, k2)
            X129 = count_tr(tr, [(32, 129), (10778, 129)], k1, k2)
            X127 = count_tr(tr, [(129, 127), (10777, 127)], k1, k2)
            X127_r2 = count_tr(tr, [(129, 127), (10777, 127)], k1, k2, {'1136:2'})
            X127_r3 = count_tr(tr, [(129, 127), (10777, 127)], k1, k2, {'1136:3'})
            L10491 = count_tr(tr, [(10491, 129)], k1, k2)
            I32 = sum(ins.get(k, 0) for k in range(k1, k2 + 1))
            I32_prev = sum(ins.get(k, 0) for k in range(k0 - 29, k0 + 1))
            I3 = sum(1 for v in veh if k1 <= v[0] <= k2 and v[1] == '1136:3')
            I3_prev = sum(1 for v in veh if k0 - 29 <= v[0] <= k0 and v[1] == '1136:3')
            S0 = sum(stock.get((k0, L, '1136:3'), 0) for L in (32, 129))
            S1 = sum(stock.get((k2, L, '1136:3'), 0) for L in (32, 129))
            S0_slow = sum(stock_slow.get((k0, L, '1136:3'), 0) for L in (32, 129))
            slow3_mean = sum(stock_slow.get((k, L, '1136:3'), 0) for k in range(k1, k2 + 1) for L in (32, 129)) / 90.0
            slow1_32_mean = sum(stock_slow.get((k, 32, '1136:1'), 0) for k in range(k1, k2 + 1)) / 90.0
            st129_10491 = sum(stock.get((k, 129, '1132:2'), 0) for k in range(k1, k2 + 1)) / 90.0
            slow129_all = sum(v for (k, L, tg), v in stock_slow.items() if L == 129 and k1 <= k <= k2) / 90.0
            tt = [(v[2] - v[0]) * 5.0 for v in veh if k1 <= v[0] <= k2 and v[1] == '1136:3' and v[2] is not None]
            f = r['flows']
            A = f.get('arrival:SC1001_W_to_onE')
            Mv = f.get('movement:SC1001_W_to_onE')
            G = f.get('input:gate:in_SC1001_W')
            beta = r['betas'].get('gate_onramp_beta_SC1001_W_to_onE')
            beta_w = r['betas'].get('gate_onramp_beta_SC1001_W_to_onW')
            v490 = r['far_link_volume_veh_h'].get('10490')
            init3 = r['init_by_link_tag'].get('32|1136:3', 0) + r['init_by_link_tag'].get('129|1136:3', 0)
            AW = sum(f.get('arrival:SC1001_W_to_' + m, 0.0) for m in ('onE', 'onW', 'E_SC1002', 'N_SC2002', 'S_SC1003'))
            off_w = sum(f.get('movement:SC1001_offW_to_' + m, 0.0) for m in ('E_SC1002', 'N_SC2002', 'S_SC1003', 'W_RAMP'))
            row = {'run': tag, 'T': T, 'A_model': A, 'M_model': Mv, 'G_model': G, 'beta_onE': beta, 'beta_onW': beta_w,
                   'beta_total': r['betas'].get('gate_onramp_beta_total_in_SC1001_W'),
                   'v10490_far': v490, 'gate_v_implied': (v490 / beta) if (v490 and beta) else None,
                   'A_onW_model': f.get('arrival:SC1001_W_to_onW'), 'M_onW_model': f.get('movement:SC1001_W_to_onW'),
                   'A_W_total_model': AW, 'offW_model': off_w,
                   'E_vis': E, 'E3_vis': E3, 'E_prev150_vis': E_prev, 'E10482_vis': E10482, 'X32_129_vis': X129,
                   'X129_127_vis': X127, 'X129_127_r2': X127_r2, 'X129_127_r3': X127_r3, 'L10491_129_vis': L10491,
                   'I32_vis': I32, 'I32_prev150_vis': I32_prev, 'I3_vis': I3, 'I3_prev150_vis': I3_prev,
                   'S3_0_vis': S0, 'S3_1_vis': S1, 'S3_0_slow_vis': S0_slow, 'init3_obsframe': init3,
                   'slow_r3_mean_vis': slow3_mean, 'slow_r1_on32_mean_vis': slow1_32_mean, 'r1132_on129_mean': st129_10491,
                   'slow129_all_mean': slow129_all, 'tt_ins_to_10490_median_s': st.median(tt) if tt else None, 'n_tt': len(tt)}
            if A is not None and beta is not None and G is not None:
                row['new_part_model'] = beta * G
                row['resid_model'] = A - beta * G
                row['new_part_vis'] = I3
                row['resid_vis'] = E - I3
                row['d_total'] = A - E
                row['d_new'] = beta * G - I3
                row['d_new_gate'] = beta * (G - I32)
                row['d_new_share'] = beta * I32 - I3
                row['d_resid'] = (A - beta * G) - (E - I3)
                row['ratio_A_E'] = A / E if E else None
                row['ratio_G_I'] = G / I32 if I32 else None
                row['ratio_beta_share'] = beta / (I3 / I32) if I3 and I32 else None
            rows.append(row)
        allrows += rows
        res['per_run'][tag] = {'n': len(rows), 'scan_sha256': S['sha256'], 'scan_rows': S['rows'],
                               'model_records': len(M['records'])}
    keys = ['ratio_A_E', 'ratio_G_I', 'ratio_beta_share', 'A_model', 'E_vis', 'G_model', 'I32_vis', 'I3_vis', 'beta_onE',
            'd_total', 'd_new', 'd_new_gate', 'd_new_share', 'd_resid', 'resid_model', 'resid_vis', 'S3_0_vis', 'S3_1_vis',
            'tt_ins_to_10490_median_s', 'E_prev150_vis', 'v10490_far', 'gate_v_implied', 'I32_prev150_vis', 'I3_prev150_vis',
            'slow_r3_mean_vis', 'slow_r1_on32_mean_vis', 'L10491_129_vis', 'X129_127_r3', 'E10482_vis', 'A_onW_model',
            'M_onW_model', 'A_W_total_model', 'M_model', 'r1132_on129_mean', 'slow129_all_mean', 'beta_total', 'offW_model']
    res['summary_all'] = {k: summ([r.get(k) for r in allrows]) for k in keys}
    per = {}
    for name, a, b in (('900-1650', 900, 1650), ('1800-3450', 1800, 3450), ('3600-5250', 3600, 5250),
                       ('5400-7050', 5400, 7050), ('7200-8550', 7200, 8550)):
        sub = [r for r in allrows if a <= r['T'] <= b]
        per[name] = {k: summ([r.get(k) for r in sub]) for k in keys}
    res['summary_by_period'] = per
    res['summary_by_run'] = {t: {k: summ([r.get(k) for r in allrows if r['run'] == t]) for k in keys}
                             for t in ('va_s31', 'va_s41', 'va_s43')}
    # cross-check vs O4 rows
    o4 = {}
    p = os.path.join(O1O4, 'out', 'o4_final_rows.csv')
    if os.path.isfile(p):
        with open(p, encoding='utf-8') as f:
            for x in csv.DictReader(f):
                if x['ramp'] == 'RM_C10490' and x['tag'].startswith('va_'):
                    o4[(x['tag'], int(x['T']))] = x
    diffs_entry, diffs_arr = [], []
    for r in allrows:
        x = o4.get((r['run'], r['T']))
        if x is None:
            continue
        if x['vis_entry_rate']:
            diffs_entry.append(r['E_vis'] * 8.0 - float(x['vis_entry_rate']))
        if x.get('model_sc1001_onE_arrival_rate') and r['A_model'] is not None:
            diffs_arr.append(r['A_model'] * 8.0 - float(x['model_sc1001_onE_arrival_rate']))
    res['crosscheck_o4'] = {'n': len(diffs_entry), 'entry_rate_diff': summ(diffs_entry), 'model_arrival_rate_diff': summ(diffs_arr)}
    res['rows'] = allrows
    return res


def n4():
    res = {'blocks': [], 'table': {}, 'checks': {}}
    for tag in ('rm_s31', 'rm_s41', 'va_s31', 'va_s41', 'va_s43'):
        S = load(os.path.join(OUT, 'scan_%s.json' % tag))
        cross, mf, lv = {}, {}, {}
        for k, c, ln, n in S['cross']:
            cross[(k, c, ln)] = cross.get((k, c, ln), 0) + n
        for k, c, ln, n in S['cross_entry']:
            cross[(k, c, ln)] = cross.get((k, c, ln), 0) + n
        for row in S['mframe']:
            mf[(row[0], row[1], row[2])] = row[3:]
        for k, c, ln, nx, n in S['leave']:
            lv[(k, c)] = lv.get((k, c), 0) + n
        greens = {}
        if tag.startswith('rm_'):
            for p in glob.glob(os.path.join(RMDIR[tag], 'decision_[0-9]*.json')):
                d = json.load(open(p, encoding='ascii'))
                greens[d['sec']] = {m: d['meters'][MID[m]]['green_sec'] for m in MID}
        Ts = sorted(greens) if greens else list(range(900, 8851, 150))
        for T in Ts:
            k0 = T // 5
            for c in MID:
                g = greens[T][c] if greens else 10
                for ln in range(1, LANES[c] + 1):
                    hp = S['head']['%d|%d' % (c, ln)] if ('%d|%d' % (c, ln)) in S['head'] else S['head']['%d|1' % c]
                    store = (CONNLEN[c] - hp) / 6.0
                    fr = [mf.get((k, c, ln), [0, 0, 0, 0, 0]) for k in range(k0 + 1, k0 + 31)]
                    qf = sum(1 for x in fr if x[1] >= 1)
                    sigf = sum(1 for x in fr if x[2] >= 1)
                    post_slow = sum(x[4] for x in fr) / 30.0
                    pre = sum(x[0] for x in fr) / 30.0
                    ncr = sum(cross.get((k, c, ln), 0) for k in range(k0 + 1, k0 + 31))
                    B = post_slow < 0.5 * store
                    res['blocks'].append({'run': tag, 'T': T, 'meter': c, 'lane': ln, 'green': g, 'cross': ncr,
                                          'rate_lane': ncr * 24.0, 'q_frames': qf, 'sig_frames': sigf,
                                          'pre_mean': pre, 'post_slow_mean': post_slow, 'post_store': store,
                                          'primary': qf == 30 and B, 'secondary': qf >= 24 and B, 'B': B})
        # totals cross vs leave per meter
        tot = {}
        for c in MID:
            tot[str(c)] = {'cross': sum(n for (k, cc, ln), n in cross.items() if cc == c),
                           'leave': sum(n for (k, cc), n in lv.items() if cc == c)}
        res['checks'][tag] = {'sha256': S['sha256'], 'rows': S['rows'], 'totals': tot}
        if tag == 'rm_s41':
            # VN/O1 check: 10490 departures 2,400-4,200 s (k 481..840)
            dep = sum(n for (k, cc), n in lv.items() if cc == 10490 and 481 <= k <= 840)
            crs = sum(n for (k, cc, ln), n in cross.items() if cc == 10490 and 481 <= k <= 840)
            res['checks']['rm_s41_10490_2400_4200'] = {'leave_veh_h': dep * 2.0, 'cross_veh_h': crs * 2.0}
    tab = {}
    for b in res['blocks']:
        key = '%s|%d|%d' % ('rm' if b['run'].startswith('rm') else 'va', b['meter'], b['green'])
        e = tab.setdefault(key, {'all': [], 'primary': [], 'secondary': [], 'primary_runs': set(), 'lane_rates': {}})
        e['all'].append(b['rate_lane'])
        if b['primary']:
            e['primary'].append(b['rate_lane'])
            e['primary_runs'].add(b['run'])
            e['lane_rates'].setdefault(str(b['lane']), []).append(b['rate_lane'])
        if b['secondary']:
            e['secondary'].append(b['rate_lane'])
    for key, e in tab.items():
        src, c, g = key.split('|')
        c, g = int(c), int(g)
        tbl = 360.0 * TABLE[g]
        res['table'][key] = {'source': src, 'meter': c, 'green': g, 'lanes': LANES[c], 'n_lane_blocks': len(e['all']),
                             'all': summ(e['all']), 'primary': summ(e['primary']), 'secondary': summ(e['secondary']),
                             'primary_runs': sorted(e['primary_runs']),
                             'primary_by_lane': {ln: summ(v) for ln, v in e['lane_rates'].items()},
                             'model_table_lane': tbl, 'g90_lane': 90.0 * g / LANES[c],
                             'ratio_primary_median_to_table': (st.median(e['primary']) / tbl) if e['primary'] else None}
    return res


def main():
    out = {'n3': n3(), 'n4': n4()}
    with open(os.path.join(OUT, 'n34_analysis.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    s = out['n3']['summary_all']
    for k, v in s.items():
        if v:
            print('N3', k, {a: round(b, 3) for a, b in v.items()})
    print('N3 crosscheck', out['n3']['crosscheck_o4'])
    for key in sorted(out['n4']['table'], key=lambda x: (x.split('|')[0], int(x.split('|')[1]), int(x.split('|')[2]))):
        t = out['n4']['table'][key]
        pm = t['primary']
        print('N4', key, 'nb', t['n_lane_blocks'], 'prim', pm and (pm['n'], round(pm['median']), round(pm['min']), round(pm['max'])),
              'sec', t['secondary'] and (t['secondary']['n'], round(t['secondary']['median'])), 'table', round(t['model_table_lane'], 1),
              'g90', t['g90_lane'], 'ratio', t['ratio_primary_median_to_table'] and round(t['ratio_primary_median_to_table'], 2))
    print('N4 checks', json.dumps(out['n4']['checks'])[:1500])


if __name__ == '__main__':
    main()
