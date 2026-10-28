# vc_report1099.py -- derived numbers from vc_fzp1099 outputs + command CSVs (verify_c V3 report). Light, read-only.
import json, sys, csv, math, bisect

D = sys.argv[1]
CMD = {
    'b31': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/action_sdmpc31_sdmpc9000_s31.csv',
    'b43': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/action_sdmpc31_sdmpc9000_s43.csv',
}

def load(tag):
    return json.load(open(f'{D}/fzp_{tag}.json', encoding='utf-8'))

def frames(a, b):
    # frame index i has time 0.1+5i ; frames with a <= t < b
    lo = max(0, math.ceil((a - 0.1) / 5)); hi = math.ceil((b - 0.1) / 5)
    return range(lo, min(hi, 1801))

def vehh(series, a, b):
    return sum(series[i] for i in frames(a, b)) * 5 / 3600

def fav(series, a, b):
    fr = list(frames(a, b)); return sum(series[i] for i in fr) / len(fr)

def cnt(times, a, b):
    return bisect.bisect_left(times, b) - bisect.bisect_left(times, a)

def pearson(x, y):
    n = len(x); mx = sum(x) / n; my = sum(y) / n
    sxx = sum((u - mx) ** 2 for u in x); syy = sum((v - my) ** 2 for v in y); sxy = sum((u - mx) * (v - my) for u, v in zip(x, y))
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else float('nan')

def greens(tag, sc):
    rows = [r for r in csv.DictReader(open(CMD[tag], encoding='utf-8-sig')) if r['kind'] == 'ramp_meter' and r['sc_no'] == str(sc)]
    return sorted((int(float(r['sim_sec'])), float(r['green_sec'])) for r in rows)

def g_at(cmds, t):
    g = None
    for tc, gg in cmds:
        if tc <= t: g = gg
    return g

out = {}
R = {tag: load(tag) for tag in ('b31', 'nc31', 'va31', 'b43', 'nc43', 'va43')}
for s in ('31', '43'):
    b, n, v = R['b' + s], R['nc' + s], R['va' + s]
    o = {}
    o['S1099'] = {k: R[k + s]['S1099_W9000_vehh'] for k in ('b', 'nc', 'va')}
    o['d4b1099_B_minus_NC3'] = n['S1099_W9000_vehh'] - b['S1099_W9000_vehh']
    o['d4b1099_VA_minus_NC3'] = n['S1099_W9000_vehh'] - v['S1099_W9000_vehh']
    o['d4b1099_B_minus_NC3_by900'] = []
    for a in range(0, 9000, 900):
        def part(times):
            return sum(max(0.0, min(a + 900, 9000) - max(a, t)) for t in times if t <= 9000) / 3600
        o['d4b1099_B_minus_NC3_by900'].append(round(part(n['ins1099_times']) - part(b['ins1099_times']), 2))
    ins = {k: R[k + s]['ins1099_times'] for k in ('b', 'nc', 'va')}
    o['inserted_by900'] = {k: [cnt(ins[k], a, a + 900) for a in (1800, 2700, 3600, 4500)] for k in ins}
    o['inserted_2700_4500'] = {k: cnt(ins[k], 2700, 4500) for k in ins}
    o['ins_pct_B_vs_NC3_2700_4500'] = 100 * (o['inserted_2700_4500']['b'] - o['inserted_2700_4500']['nc']) / o['inserted_2700_4500']['nc']
    o['cum_NC3_minus_B'] = {str(T): cnt(ins['nc'], 0, T) - cnt(ins['b'], 0, T) for T in (2700, 3600, 4500, 5400, 9000.2)}
    o['ins_total'] = {k: len(ins[k]) for k in ins}
    zf = {}
    for k in ins:
        per = [0] * 1801
        for t in ins[k]:
            i = int(round((t - 0.1) / 5))
            if 0 <= i < 1801: per[i] += 1
        for lab, lo in (('1_1800', 1), ('180_1800', 180)):
            z = [i for i in range(lo, 1801) if per[i] == 0]
            run = best = 0
            for i in range(lo, 1801):
                run = run + 1 if per[i] == 0 else 0; best = max(best, run)
            zf[f'{k}_{lab}'] = {'zero_frames': len(z), 'longest_zero_run_s': best * 5}
        zf[f'{k}_offgrid_inserts'] = sum(1 for t in ins[k] if abs(t - (0.1 + 5 * round((t - 0.1) / 5))) > 1e-6)
    o['zero_insert_frames'] = zf
    # link 26 lane 1 tail-reach bins: 300 s bin where cells 36..0 all have obs and mean < 40 km/h
    tail = {}
    for k in ('b', 'nc', 'va'):
        g = R[k + s]['g26L1']; bins = []
        for bi in range(30):
            ok = True
            for c in range(36, -1, -1):
                ssum, nn = g[bi][c]
                if nn == 0 or ssum / nn >= 40.0: ok = False; break
            if ok: bins.append(bi * 300)
        tail[k] = bins
    o['tail_reach_bins'] = tail
    o['tail_reach_count'] = {k: len(v) for k, v in tail.items()}
    def tt(run, pair): return sorted(run['trans_times'].get(pair, []))
    o['x127_30_900_2700'] = {k: cnt(tt(R[k + s], '127>30'), 900, 2700) for k in ('b', 'nc', 'va')}
    o['x2_127_0_9000'] = {k: cnt(tt(R[k + s], '2>127'), 0, 9001) for k in ('b', 'nc', 'va')}
    sp = {}
    for k in ('b', 'nc', 'va'):
        a = R[k + s]['s127_L12_0_50']; ss = sum(a[i][0] for i in (6, 7, 8)); nn = sum(a[i][1] for i in (6, 7, 8))
        sp[k] = ss / nn if nn else None
    o['spd127_0_50_L12_1800_2700'] = sp
    ser = {k: R[k + s]['series'] for k in ('b', 'nc', 'va')}
    o['slow127_vehh_1800_2700'] = {k: vehh(ser[k]['slow127'], 1800, 2700) for k in ser}
    o['slow129_vehh_1800_3600'] = {k: vehh(ser[k]['slow129'], 1800, 3600) for k in ser}
    o['slow10491_vehh_1800_3600'] = {k: vehh(ser[k]['slow10491'], 1800, 3600) for k in ser}
    o['x26_129_1800_3600'] = {k: cnt(tt(R[k + s], '26>129'), 1800, 3600) for k in ('b', 'nc', 'va')}
    o['slow120_vehh_0_9000'] = {k: vehh(ser[k]['slow120'], 0, 9000.2) for k in ser}
    o['dwell124_vehh_0_9000'] = {k: vehh(ser[k]['n124'], 0, 9000.2) for k in ser}
    o['slow10480_vehh_0_9000'] = {k: vehh(ser[k]['slow10480'], 0, 9000.2) for k in ser}
    o['slow10490_vehh_0_9000'] = {k: vehh(ser[k]['slow10490'], 0, 9000.2) for k in ser}
    o['x124_26_0_9000'] = {k: cnt(tt(R[k + s], '124>26'), 0, 9001) for k in ('b', 'nc', 'va')}
    ex = {}
    for k in ('b', 'nc', 'va'):
        allx = sorted(tt(R[k + s], '26>125') + tt(R[k + s], '26>129') + tt(R[k + s], '26>120'))
        ex[k] = {'2700_3600': cnt(allx, 2700, 3600), 'cum4500': cnt(allx, 0, 4500)}
    o['x26_exits'] = ex
    o['cons_4500_B_minus_NC3'] = {'inserted': cnt(ins['b'], 0, 4500) - cnt(ins['nc'], 0, 4500),
                                  'exits': ex['b']['cum4500'] - ex['nc']['cum4500']}
    on = {}
    TH = (('slow127', 100), ('slow129L1_150', 3), ('slow10491', 2), ('slow26L1_3500', 5), ('slow26L1', 150))
    for k in ser:
        row = {}
        for name, th in TH:
            hits = [T for T in range(900, 9000, 150) if fav(ser[k][name], T, T + 150) >= th]
            row[name] = [hits[0] if hits else None, len(hits)]
        on[k] = row
    o['onset150'] = on
    cb = {}
    tag = 'b' + s
    g10490 = greens(tag, 9107); g10480 = greens(tag, 9101)
    Ts = list(range(900, 9000, 150))
    x1 = [g_at(g10490, T) for T in Ts]; y1 = [fav(ser['b']['slow129L1_150'], T, T + 150) for T in Ts]
    x2 = [g_at(g10480, T) for T in Ts]; y2 = [fav(ser['b']['slow26L1_3500'], T, T + 150) for T in Ts]
    y3 = [fav(ser['b']['slow10490'], T, T + 150) for T in Ts]
    cb['n_intervals'] = len(Ts)
    cb['r_g10490_vs_slow129L1_150'] = pearson(x1, y1)
    cb['r_g10480_vs_slow26L1_3500'] = pearson(x2, y2)
    cb['r_g10490_vs_slow10490'] = pearson(x1, y3)
    o['corr_B'] = cb
    out['s' + s] = o
json.dump(out, open(f'{D}/report1099.json', 'w', encoding='utf-8'), indent=1)
print(json.dumps(out, indent=1)[:200])
