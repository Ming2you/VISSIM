# VerifyVA r2: compare fresh_r2.json (fresh code) with numbers printed in VA_REPORT.md r2 (typed here from the report text).
# Light: reads two JSON files only (fresh output, analysis va_metrics.json for full-precision cross check). No run data.
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
F = json.load(open(os.path.join(HERE, 'out', 'fresh_r2.json'), encoding='utf-8'))
S = ['31', '41', '43']
rows = []


def ck(name, fresh, rep, tol):
    if isinstance(rep, (int, float)) and fresh is not None and not isinstance(fresh, (list, dict, str, bool)):
        ok = abs(fresh - rep) <= tol
        diff = fresh - rep
    else:
        ok = fresh == rep
        diff = None
    rows.append(dict(check=name, fresh=fresh, report=rep, ok=bool(ok), diff=diff))


T1 = 0.051   # one-decimal print
T2 = 0.0051  # two-decimal print
T4 = 0.00006  # four-decimal print
L = F['levels']
PA, PB = F['pairs']['A'], F['pairs']['B']
# ---- levels and d, pair A (U6VA) and pair B (U9)
REP = {
    'nc3_om': [6853.0, 7128.7, 7003.4], 'va_om': [6363.7, 6469.4, 6386.9], 'j1_om': [6834.3, 6402.8, 6799.8],
    'nc3_a4': [9240.2, 9696.2, 9484.2], 'va_a4': [9040.5, 9295.7, 9189.8], 'j1_a4': [9606.1, 9297.3, 9687.4],
    'nc3_f4_U6VA': [13104.8, 12925.2, 12774.8], 'va_f4_U6VA': [12737.1, 12407.1, 12421.8],
    'nc3_b4_U6VA': [3864.6, 3229.0, 3290.5], 'va_b4_U6VA': [3696.6, 3111.5, 3231.9],
    'nc3_oa_U6VA': [6251.8, 5796.5, 5771.4], 'va_oa_U6VA': [6373.5, 5937.7, 6034.8],
    'nc3_f4_U9': [13146.3, 12941.9, 12787.1], 'j1_f4_U9': [13240.9, 12407.5, 12947.8], 'va_f4_U9': [12778.7, 12434.3, 12435.0],
    'nc3_b4_U9': [3906.2, 3245.7, 3302.9], 'j1_b4_U9': [3634.8, 3110.1, 3260.3], 'va_b4_U9': [3738.2, 3138.7, 3245.2],
    'nc3_oa_U9': [6293.4, 5813.2, 5783.8], 'j1_oa_U9': [6406.6, 6004.7, 6148.0], 'va_oa_U9': [6415.1, 5964.9, 6048.1],
    'nc3_rA': [261, 318, 272], 'j1_rA': [348, 352, 388], 'va_rA': [274, 308, 287],
    'nc3_rB': [186, 205, 175], 'j1_rB': [183, 233, 196], 'va_rB': [186, 219, 195],
    'nc3_u1098_U6VA': [2186.2, 1725.5, 1995.2], 'va_u1098_U6VA': [2400.3, 1724.6, 2059.0], 'j1_u1098_U6VA': [2112.9, 1689.2, 1936.7],
    'nc3_u1099_U6VA': [1208.5, 1021.9, 675.0], 'va_u1099_U6VA': [887.3, 899.1, 623.8], 'j1_u1099_U6VA': [876.7, 900.8, 617.3],
}
for k, v in REP.items():
    arm, key = k.split('_', 1)
    for i, s in enumerate(S):
        tol = 0 if key in ('rA', 'rB') else T1
        ck('level.%s.s%s' % (k, s), L[s][arm][key], v[i], tol)
DREP = {
    'A': dict(d3=[-489.3, -659.3, -616.5], d4=[-367.7, -518.1, -353.0], d4a=[-199.6, -400.6, -294.4], d4b=[-168.0, -117.5, -58.6],
              doa=[121.7, 141.2, 263.5], dob=[289.7, 258.7, 322.1], drA=[13, -10, 15], drB=[0, 14, 20]),
    'B': dict(d3=[-470.6, 66.7, -412.9], d4=[-462.2, 26.9, -512.8], d4a=[-565.5, -1.7, -497.6], d4b=[103.4, 28.5, -15.2],
              doa=[8.5, -39.8, -99.9], dob=[-94.9, -68.3, -84.7], drA=[-74, -44, -101], drB=[3, -14, -1]),
}
SREP = {
    'A': dict(d3=(-588.3, 88.4, -737.4, -439.3), d4=(-412.9, 91.4, -567.0, -258.8), d4a=(-298.2, 100.5, -467.7, -128.7),
              d4b=(-114.7, 54.8, -207.1, -22.4), doa=(175.4, 76.9, 45.8, 305.0), dob=(290.1, 31.7, 236.7, 343.6),
              drA=(6.0, 13.9, -17.4, 29.4), drB=(11.3, 10.3, -6.0, 28.6)),
    'B': dict(d3=(-272.3, 295.0, -769.6, 225.0), d4=(-316.0, 298.0, -818.4, 186.4), d4a=(-354.9, 307.8, -873.9, 164.0),
              d4b=(38.9, 59.9, -62.2, 140.0), doa=(-43.7, 54.3, -135.2, 47.8), dob=(-82.6, 13.4, -105.2, -60.0),
              drA=(-73.0, 28.5, -121.1, -24.9), drB=(-4.0, 8.9, -19.0, 11.0)),
}
CIX = {'A': dict(d3=True, d4=True, d4a=True, d4b=True, doa=True, dob=True, drA=False, drB=False),
       'B': dict(d3=False, d4=False, d4a=False, d4b=False, doa=False, dob=True, drA=True, drB=False)}
PCT = {'A': dict(d3=-8.41, d4=-3.19, doa=2.95), 'B': dict(d3=-3.89, d4=-2.44, doa=-0.73)}
for P in ('A', 'B'):
    pp = F['pairs'][P]
    for key, v in DREP[P].items():
        for i, s in enumerate(S):
            ck('d.%s.%s.s%s' % (P, key, s), pp['per_seed'][s][key], v[i], 0 if key in ('drA', 'drB') else T1)
    for key, (m, sd, lo, hi) in SREP[P].items():
        st = pp['stats'][key]
        ck('stat.%s.%s.mean' % (P, key), st['mean'], m, T1)
        ck('stat.%s.%s.sd' % (P, key), st['sd'], sd, T1)
        ck('stat.%s.%s.ci_lo' % (P, key), st['ci'][0], lo, T1)
        ck('stat.%s.%s.ci_hi' % (P, key), st['ci'][1], hi, T1)
        ck('stat.%s.%s.ci_excl0' % (P, key), st['ci_excl0'], CIX[P][key], 0)
    for key, v in PCT[P].items():
        ck('pct.%s.%s' % (P, key), pp['pct'][key], v, T2)
# ---- labels
MV, SAME, NA = '대기 이전(Ω 밖으로)', '같은 방향(K8 §5.5 표시 조건 충족, 판정 아님)', '해당 없음(Ω 감소 아님)'
LREP = {'A': {s: dict(N=MV, W_A=MV, W_B=MV) for s in S + ['mean']},
        'B': {'31': dict(N=MV, W_A=MV, W_B=MV), '41': dict(N=NA, W_A=NA, W_B=NA), '43': dict(N=SAME, W_A=SAME, W_B=SAME),
              'mean': dict(N=SAME, W_A=MV, W_B=MV)}}
for P in ('A', 'B'):
    for s, d in LREP[P].items():
        for k, v in d.items():
            ck('label.%s.%s.%s' % (P, s, k), F['pairs'][P]['labels'][s][k], v, 0)
# ---- unions
ck('union.U6VA', F['unions']['U6VA'], [194, 282, 1064, 1085, 1086, 1087, 1093, 1098, 1099, 1102], 0)
ck('union.U9', F['unions']['U9'], [194, 282, 1064, 1083, 1085, 1086, 1087, 1091, 1093, 1098, 1099, 1102], 0)
ck('union.U6J1', F['unions']['U6J1'], [194, 282, 1064, 1083, 1085, 1086, 1087, 1091, 1093, 1098, 1099, 1102], 0)
# ---- link 174, 21, east links
LK = F['links']
for arm, v in dict(nc3=[43.1, 43.4, 46.1], j1=[339.5, 66.2, 361.4], va=[59.0, 60.9, 62.0]).items():
    for i, s in enumerate(S):
        ck('link174.vh.%s.s%s' % (arm, s), LK[s][arm]['174'], v[i], T1)
for arm, v in dict(nc3=[12.9, 12.2, 12.7], j1=[72.6, 17.7, 76.5], va=[12.7, 12.3, 12.7]).items():
    for i, s in enumerate(S):
        ck('link21.vh.%s.s%s' % (arm, s), LK[s][arm]['21'], v[i], T1)
R = F['runs']
for arm, v in dict(nc3=[17.2, 18.2, 17.8], j1=[259.2, 26.6, 275.5], va=[25.0, 31.2, 27.2]).items():
    for i, s in enumerate(S):
        ck('link174.vh_after4350.%s.s%s' % (arm, s), R[s][arm]['l174']['vh_after4350'], v[i], 0.15)
for arm, v in dict(nc3=[(17.3, 57, 2265.1), (17.4, 62, 2575.1), (18.5, 61, 3025.1)],
                   j1=[(135.9, 286, 5090.1), (26.5, 72, 2665.1), (144.7, 274, 5105.1)],
                   va=[(23.6, 88, 3595.1), (24.4, 75, 2555.1), (24.8, 92, 4155.1)]).items():
    for i, s in enumerate(S):
        ck('link174.frame_mean.%s.s%s' % (arm, s), R[s][arm]['l174']['mean'], v[i][0], T1)
        ck('link174.frame_max.%s.s%s' % (arm, s), R[s][arm]['l174']['max'], v[i][1], 0)
        ck('link174.frame_tmax.%s.s%s' % (arm, s), R[s][arm]['l174']['tmax'], v[i][2], 0.001)
for arm, v in dict(nc3=[9.9, 9.5, 10.6], j1=[21.2, 12.3, 21.8], va=[17.1, 16.1, 17.4]).items():
    for i, s in enumerate(S):
        ck('link704.vh.%s.s%s' % (arm, s), LK[s][arm]['1220000704'], v[i], T1)
for arm, v in dict(nc3=[24.8, 24.8, 25.5], j1=[23.8, 25.7, 23.0], va=[26.1, 26.3, 26.6]).items():
    for i, s in enumerate(S):
        ck('link803.vh.%s.s%s' % (arm, s), LK[s][arm]['1220000803'], v[i], T1)
E = F['east']
for i, s in enumerate(S):
    ck('d704.A.s%s' % s, E['A']['d'][i], [7.17, 6.62, 6.85][i], T2)
    ck('d704.B.s%s' % s, E['B']['d'][i], [-4.10, 3.82, -4.34][i], T2)
ck('d704.A.mean', E['A']['mean'], 6.9, T1)
ck('d704.A.ci', [round(x, 1) for x in E['A']['ci']], [6.4, 7.3], 0)
ck('d704.B.mean', E['B']['mean'], -1.5, T1)
ck('d704.B.ci', [round(x, 1) for x in E['B']['ci']], [-9.4, 6.3], 0)
ck('d803.A.mean', E['A_803']['mean'], 1.3, T1)
ck('d803.A.ci', [round(x, 1) for x in E['A_803']['ci']], [1.0, 1.6], 0)
ck('d803.B.ci_excl0', E['B_803']['ci_excl0'], False, 0)
# ---- inputs 1083 and 282
for arm, v in dict(nc3=[(0, 1312, 18.6), (0, 1275, 14.3), (0, 1279, 5.1)], j1=[(89, 1221, 142.6), (0, 1275, 14.3), (184, 1094, 145.6)],
                   va=[(0, 1312, 18.6), (0, 1275, 14.3), (0, 1279, 5.1)]).items():
    for i, s in enumerate(S):
        ck('in1083.remain.%s.s%s' % (arm, s), R[s][arm]['inp1083']['remain'], v[i][0], 0)
        ck('in1083.seen.%s.s%s' % (arm, s), R[s][arm]['inp1083']['seen'], v[i][1], 0)
        ck('in1083.delay.%s.s%s' % (arm, s), R[s][arm]['inp1083']['delay'], v[i][2], T1)
for arm, v in dict(nc3=[(0, 115.6), (0, 109.5), (0, 111.8)], j1=[(13, 248.3), (16, 246.9), (0, 243.2)],
                   va=[(0, 195.6), (36, 259.1), (18, 265.3)]).items():
    for i, s in enumerate(S):
        ck('in282.remain.%s.s%s' % (arm, s), R[s][arm]['inp282']['remain'], v[i][0], 0)
        ck('in282.delay.%s.s%s' % (arm, s), R[s][arm]['inp282']['delay'], v[i][1], T1)
for i, s in enumerate(S):
    d1083 = R[s]['va']['unins_per']['1083'] - R[s]['j1']['unins_per']['1083']
    ck('in1083.d4b_share.B.s%s' % s, d1083, [-124.0, 0.0, -140.5][i], T1)
# ---- SC109 p3 and decisions
for arm, v in dict(j1=[(22, 3900, 9), (0, None, 0), (35, 3750, 19)], va=[(6, 8100, 5), (5, 7200, 2), (6, 6750, 3)]).items():
    for i, s in enumerate(S):
        p3 = R[s][arm]['dec']['p3']
        ck('p3.n_sdmpc.%s.s%s' % (arm, s), p3['n_sdmpc'], 55, 0)
        ck('p3.n_le245.%s.s%s' % (arm, s), p3['n_le245'], v[i][0], 0)
        ck('p3.first.%s.s%s' % (arm, s), p3['first'], v[i][1], 0)
        ck('p3.longest.%s.s%s' % (arm, s), p3['longest'], v[i][2], 0)
for arm, v in dict(j1=[(33.8, 23.5), (73.5, 79.3), (33.2, 21.5)], va=[(44.8, 38.0), (42.9, 31.4), (44.0, 31.6)]).items():
    for i, s in enumerate(S):
        p3 = R[s][arm]['dec']['p3']
        ck('p3.mean_all.%s.s%s' % (arm, s), p3['mean_all'], v[i][0], T1)
        ck('p3.mean_ge4350.%s.s%s' % (arm, s), p3['mean_ge4350'], v[i][1], T1)
for arm, v in dict(j1=[(3, 3750), (4, 3300), (0, None)], va=[(9, 3450), (10, 2550), (14, 2850)]).items():
    for i, s in enumerate(S):
        vs = R[s][arm]['dec']['vsl']
        ck('vsl.fwe_lt110.%s.s%s' % (arm, s), vs['fwe_lt110'], v[i][0], 0)
        ck('vsl.fwe_first.%s.s%s' % (arm, s), vs['fwe_first'], v[i][1], 0)
        ck('vsl.fww_lt110.%s.s%s' % (arm, s), vs['fww_lt110'], 0, 0)
for arm, v in dict(j1=[[5700], [4200, 4500, 6450, 8550], []], va=[[5700, 8550], [4350, 4650, 4800], []]).items():
    for i, s in enumerate(S):
        ck('prev_plan_kept.%s.s%s' % (arm, s), R[s][arm]['dec']['prev_plan_kept'], v[i], 0)
        ck('holds.%s.s%s' % (arm, s), R[s][arm]['dec']['holds'], [], 0)
        ck('n_action.%s.s%s' % (arm, s), R[s][arm]['dec']['n_action'], 61, 0)
for i, s in enumerate(S):
    ck('k92_keys.va.s%s' % s, R[s]['va']['dec']['k92_keys'], 61, 0)
    ck('k92_keys.j1.s%s' % s, R[s]['j1']['dec']['k92_keys'], 0, 0)
    ck('s7.va.n.s%s' % s, R[s]['va']['dec']['s7']['n'], [271, 307, 287][i], 0)
    ck('s7.va.late.s%s' % s, R[s]['va']['dec']['s7']['late'], [207, 232, 231][i], 0)
    ck('s7.j1.n.s%s' % s, R[s]['j1']['dec']['s7']['n'], [348, 349, 384][i], 0)
    ck('s7.j1.late.s%s' % s, R[s]['j1']['dec']['s7']['late'], [266, 251, 272][i], 0)
    wv, wj = R[s]['va']['dec']['wall'], R[s]['j1']['dec']['wall']
    ck('wall.va.median.s%s' % s, wv['sdmpc_median'], [536.5, 559.4, 473.0][i], T1)
    ck('wall.j1.median.s%s' % s, wj['sdmpc_median'], [469.6, 409.6, 490.0][i], T1)
    ck('wall.ratio.s%s' % s, wv['sdmpc_median'] / wj['sdmpc_median'], [1.1426, 1.3657, 0.9654][i], T4)
    ck('wall.va.max.s%s' % s, wv['sdmpc_max'], [743.7, 818.6, 782.8][i], T1)
    ck('wall.va.exits.s%s' % s, wv['exits'], [0], 0)
    ck('wall.va.n.s%s' % s, wv['n'], 61, 0)
# ---- end state, seen vehicles
for arm, v in dict(nc3=[(2631, 2019, 67217), (2627, 1949, 67602), (2355, 1724, 67969)],
                   j1=[(2562, 1906, 67239), (2447, 1719, 67586), (2528, 1822, 67783)],
                   va=[(2323, 1693, 67343), (2466, 1693, 67566), (2313, 1637, 67950)]).items():
    for i, s in enumerate(S):
        ck('end_in_net.%s.s%s' % (arm, s), R[s][arm]['end_in_net'], v[i][0], 0)
        ck('end_omega.%s.s%s' % (arm, s), R[s][arm]['end_omega'], v[i][1], 0)
        ck('n_seen.%s.s%s' % (arm, s), R[s][arm]['n_seen'], v[i][2], 0)
# ---- pairing (first differing frame)
for i, s in enumerate(S):
    ck('pair.A.first_frame.s%s' % s, F['seeds'][s]['pairing']['va-nc3']['first_diff_frame'], [905.1, 905.1, 915.1][i], 0.001)
    ck('pair.B.first_frame.s%s' % s, F['seeds'][s]['pairing']['va-j1']['first_diff_frame'], [905.1, 910.1, 905.1][i], 0.001)
# ---- cumulative d at marks (report sec.11), looser tolerance (bin assignment of trapezoid segments)
CUM = {
    'A': dict(cum3={'1800': [-26.1, -19.0, -31.9], '3600': [-106.2, -120.3, -124.8], '5400': [-250.8, -294.8, -284.4], '7200': [-398.8, -516.0, -498.8], '9000': [-489.3, -659.3, -616.5]},
              cum4={'1800': [-7.7, -7.3, -11.9], '3600': [31.5, -58.9, -41.0], '5400': [-60.9, -225.8, -164.9], '7200': [-219.5, -423.5, -309.5], '9000': [-367.7, -518.1, -353.0]},
              cumoa={'1800': [18.4, 11.7, 20.0], '3600': [137.7, 61.4, 83.8], '5400': [189.9, 69.0, 119.5], '7200': [179.3, 92.5, 189.3], '9000': [121.7, 141.2, 263.5]}),
    'B': dict(cum3={'1800': [-5.9, -7.0, -13.6], '3600': [-32.8, 16.2, -45.2], '5400': [-219.3, 103.3, -147.5], '7200': [-374.2, 69.8, -304.6], '9000': [-470.6, 66.7, -412.9]},
              cum4={'1800': [-7.6, -1.3, -2.2], '3600': [-33.7, 20.6, -33.1], '5400': [-196.4, 48.0, -157.4], '7200': [-323.8, 13.6, -325.8], '9000': [-462.2, 26.9, -512.8]},
              cumoa={'1800': [-1.7, 5.7, 11.4], '3600': [-0.9, 4.5, 12.1], '5400': [22.9, -55.3, -9.9], '7200': [50.4, -56.3, -21.3], '9000': [8.5, -39.8, -99.9]}),
}
for P, dd in CUM.items():
    for nm, marks in dd.items():
        for T, v in marks.items():
            for i, s in enumerate(S):
                ck('cum.%s.%s.%s.s%s' % (P, nm, T, s), F['pairs'][P]['cum'][nm][s][T], v[i], 0.3)
for s in S:
    sg = F['pairs']['A']['sign'][s]
    ck('sign.A.c3_neg_from_1800.s%s' % s, sg['c3_neg_from_1800'], True, 0)
    ck('sign.A.coa_pos_from_1800.s%s' % s, sg['coa_pos_from_1800'], True, 0)
    ck('sign.A.c4_neg_from_5400.s%s' % s, sg['c4_neg_from_5400'], True, 0)
    for P in ('A', 'B'):
        ck('sign.%s.pre900_zero.s%s' % (P, s), F['pairs'][P]['sign'][s]['pre900_maxabs'], 0.0, 1e-9)
# ---- data health
for s in S:
    for arm in ('nc3', 'j1', 'va'):
        r = R[s][arm]
        ck('health.frames.%s.s%s' % (arm, s), r['frames'], 1799, 0)
        ck('health.t_first.%s.s%s' % (arm, s), r['t_first'], 5.1, 1e-6)
        ck('health.t_last.%s.s%s' % (arm, s), r['t_last'], 8995.1, 1e-6)
        ck('health.regular.%s.s%s' % (arm, s), r['regular'], True, 0)
        ck('health.unknown_links.%s.s%s' % (arm, s), r['unknown_links'], [], 0)
        ck('health.ambiguous.%s.s%s' % (arm, s), r['n_ambiguous'], 0, 0)
        ck('health.unattributed.%s.s%s' % (arm, s), r['n_unattributed'], 0, 0)
        ck('health.removal_links_unknown.%s.s%s' % (arm, s), r['removal_links_unknown'], [], 0)
        if not (s == '31' and arm == 'nc3'):
            ck('health.same_net.%s.s%s' % (arm, s), r['same_net_as_ref'], True, 0)
bad = [r for r in rows if not r['ok']]
out = dict(n=len(rows), n_ok=len(rows) - len(bad), bad=bad,
           max_abs_diff_veh_h=max(abs(r['diff']) for r in rows if r['diff'] is not None and not r['check'].startswith(('cum.', 'wall.ratio', 'pct.', 'p3.', 'link174.frame_tmax'))),
           max_abs_diff_cum=max(abs(r['diff']) for r in rows if r['diff'] is not None and r['check'].startswith('cum.')),
           rows=rows)
p = os.path.join(HERE, 'out', 'compare_r2.json')
json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('%d/%d %s' % (out['n_ok'], out['n'], 'ALL_OK' if not bad else 'NOT_OK'))
print('max |diff| veh.h-like (non-cum) %.4f, cum %.4f' % (out['max_abs_diff_veh_h'], out['max_abs_diff_cum']))
for r in bad:
    print('BAD', r['check'], r['fresh'], r['report'], r['diff'])
