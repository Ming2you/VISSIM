# VerifyVA r1 - compare fresh_va.json (verifier's own recomputation) with (1) the analysis JSON outputs and
# (2) the numbers printed in VA_REPORT.md section 0 / tables (typed in here from the report text as read by the verifier).
# Reads only. Writes <this folder>/out/compare_fresh.json and prints a summary.
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
AV = os.path.dirname(os.path.dirname(HERE))
F = json.load(io.open(os.path.join(HERE, 'out', 'fresh_va.json'), encoding='utf-8'))
AM = json.load(io.open(os.path.join(AV, 'out', 'va_metrics.json'), encoding='utf-8'))
AC = json.load(io.open(os.path.join(AV, 'out', 'va_control.json'), encoding='utf-8'))
AF = json.load(io.open(os.path.join(AV, 'out', 'va_followup.json'), encoding='utf-8'))
AL = json.load(io.open(os.path.join(AV, 'out', 'va_local.json'), encoding='utf-8'))
S = ['31', '41', '43']
rows = []


def ck(name, fresh, other, tol):
    if isinstance(fresh, (int, float)) and isinstance(other, (int, float)) and tol is not None:
        ok = abs(fresh - other) <= tol
    else:
        ok = fresh == other
    rows.append(dict(check=name, fresh=fresh, other=other, ok=bool(ok)))


# ---- 1. fresh vs analysis JSON (unrounded), veh.h tolerance 0.05
KM = {'M3': 'M3', 'M4a': 'M4a', 'M4b': 'M4b', 'M4': 'M4', 'OUTa': 'OUT_a', 'OUTb': 'OUT_b'}
for u in ('U6VA', 'U9', 'U6J1'):
    ck('union.%s' % u, [str(x) for x in F['unions'][u]], AM['unions'][u], None)
for key, lev in F['levels'].items():
    a = AM['per_run'].get(key)
    if a is None:
        continue
    for fk, ak in KM.items():
        ck('level.%s.%s' % (key, fk), lev[fk], a['full'][ak], 0.05)
    for no, v in lev['unins_by_input'].items():
        if no in ('1098', '1099'):
            ck('level.%s.unins_%s' % (key, no), v, a['full']['unins_%s' % no], 0.05)
PK = {'A': 'A', 'B': 'B', 'Bp': 'Bp', 'J1R': 'J1R'}
for pk in PK:
    fs, ap = F['pairs'][pk]['stats'], AM['pairs'][pk]['summary']
    for fk, ak in KM.items():
        for i, s in enumerate(S):
            ck('pair.%s.%s.d.s%s' % (pk, fk, s), fs[fk]['d'][i], ap[ak]['per_seed'][s], 0.05)
        ck('pair.%s.%s.mean' % (pk, fk), fs[fk]['mean'], ap[ak]['mean'], 0.05)
        ck('pair.%s.%s.sd' % (pk, fk), fs[fk]['sd'], ap[ak]['sd'], 0.05)
        ck('pair.%s.%s.ci' % (pk, fk), [round(x, 1) for x in fs[fk]['ci']], [round(x, 1) for x in ap[ak]['ci90']], None)
        ck('pair.%s.%s.ci_excl0' % (pk, fk), fs[fk]['ci_excl0'], ap[ak]['ci_excludes_0'], None)
    for fk, ak in (('remA', 'REM'), ('remB', 'REM_B')):
        for i, s in enumerate(S):
            ck('pair.%s.%s.d.s%s' % (pk, fk, s), fs[fk]['d'][i], ap[ak]['per_seed'][s], 1e-9)
    if pk in ('A', 'B'):
        al = AM['pairs'][pk]['labels']
        for s in S + ['mean']:
            fl = F['pairs'][pk]['labels'][s]
            for k in ('N', 'W_A', 'W_B'):
                want = {'same': '같은 방향', 'shift': '대기 이전', '해당 없음': '해당 없음'}[fl[k]]
                ck('label.%s.%s.%s' % (pk, s, k), want, al[s][k][:len(want)], None)
# end state: seen, removals, remains
for s in S:
    for arm in ('nc3', 'j1', 'va'):
        t = '%s_s%s' % (arm, s)
        pr, es = F['per_run'][t], AM['per_run']['U9|' + t]['end_state']
        ck('end.%s.seen' % t, pr['vehicles_seen'], es['vehicles_seen'], None)
        ck('end.%s.removals_A' % t, pr['removals_A'], es['removals'], None)
        ck('end.%s.removals_B' % t, pr['removals_B_outside'], es['removals_membership']['outside_omega'], None)
        ck('end.%s.remains' % t, pr['remains'], es['remains'], None)
        lv = AF['link174_chain']['link_vh']['174'][t]
        ck('l174.%s.full' % t, pr['link174_ttt'], lv['full'], 0.05)
        ck('l174.%s.from4350' % t, pr['link174_ttt_after4350'], lv['from_4350'], 0.05)
        oc = AL['runs'][t]['occ_174']['F_all']
        ck('l174.%s.frame_max' % t, pr['link174_frame_max'], oc['max'], None)
        ck('l174.%s.frame_max_t' % t, pr['link174_frame_max_t'], oc['max_t'], None)
        ck('l174.%s.frame_mean' % t, pr['link174_frame_mean'], oc['mean'], 1e-6)
        ck('l704.%s' % t, pr['link1220000704_ttt'], AF['sc109_east']['link_vh']['1220000704'][t]['full'], 0.05)
        ck('l803.%s' % t, pr['link1220000803_ttt'], AF['sc109_east']['link_vh']['1220000803'][t]['full'], 0.05)
        r83 = AF['input_1083']['runs'][t]
        ck('i1083.%s.inserted' % t, pr['inserted_1083'], r83['inserted'], None)
        ck('i1083.%s.delay' % t, F['unins_1083_nc3anchor'][t], r83['delay_veh_h_nc3_anchor'], 0.05)
    for arm in ('j1', 'va'):
        t = '%s_s%s' % (arm, s)
        fc, ac = F['control'][t], AC['runs'][t]
        ck('ctl.%s.p3' % t, [fc['p3_le_245'], fc['p3_first_T'], fc['p3_longest']],
           [ac['sc109_p3']['le_24_5_count'], ac['sc109_p3']['first_T'], ac['sc109_p3']['longest_run']], None)
        ck('ctl.%s.n_action' % t, fc['n_action'], ac['n_action_json'], None)
        ck('ctl.%s.vsl_fwe_frac' % t, fc['vsl_fwe_lt110'] / 55.0, ac['vsl_stats']['FW_E']['frac_any_lt110'], 1e-9)
        ck('ctl.%s.k92' % t, [fc['k92_w'], fc['k92_hb']], [ac['floor_173_p4']['k92_present']['k92_w'], ac['floor_173_p4']['k92_present']['k92_hb']], None)
        pp = ac['previous_plan_kept']
        ck('ctl.%s.prev_plan' % t, [fc['prev_plan_a'], fc['prev_plan_b'], fc['prev_plan_c'], fc['prev_plan_all']],
           [pp['ga_same_green_offsets'], pp['na_no_prediction_sequence'], pp['da_selected_repr_eq_held'], pp['all_three_T']], None)
        ck('ctl.%s.wall_median' % t, fc['sdmpc_wall_median'], ac['wall_sdmpc']['median'], 1e-9)
    ck('ctl.ratio.s%s' % s, F['wall_ratio'][s], AC['wall_ratio']['s' + s]['ratio'], 1e-9)

# ---- 2. fresh vs numbers printed in VA_REPORT.md (as read by the verifier; 1-decimal rounding -> tol 0.051)
REP = {
    # section 0 items 2/4 and section 3.1/3.2 (d per seed)
    'A.M3': [-489.3, -659.3, -616.5], 'A.M4': [-367.7, -518.1, -353.0], 'A.OUTa': [121.7, 141.2, 263.5], 'A.M4b': [-168.0, -117.5, -58.6],
    'B.M3': [-470.6, 66.7, -412.9], 'B.M4': [-462.2, 26.9, -512.8], 'B.OUTa': [8.5, -39.8, -99.9], 'B.M4b': [103.4, 28.5, -15.2],
    'A.M3.mean': -588.3, 'A.M4.mean': -412.9, 'A.OUTa.mean': 175.4, 'B.M3.mean': -272.3, 'B.M4.mean': -316.0, 'B.OUTa.mean': -43.7,
    'B.M4b.mean': 38.9,
    'A.M3.ci': [-737.4, -439.3], 'A.M4.ci': [-567.0, -258.8], 'A.OUTa.ci': [45.8, 305.0],
    'B.M3.ci': [-769.6, 225.0], 'B.M4.ci': [-818.4, 186.4], 'B.OUTa.ci': [-135.2, 47.8],
    'A.M3.sd': 88.4, 'A.M4.sd': 91.4, 'A.OUTa.sd': 76.9, 'B.M3.sd': 295.0, 'B.M4.sd': 298.0, 'B.OUTa.sd': 54.3,
    'A.remA': [13, -10, 15], 'B.remA': [-74, -44, -101],
    # levels (section 3.1): V-A [U6(V-A)] M3, M4, M4b, OUTa
    'lvl.va.M3': [6363.7, 6469.4, 6386.9], 'lvl.va.U6VA.M4': [12737.1, 12407.1, 12421.8], 'lvl.va.U6VA.M4b': [3696.6, 3111.5, 3231.9],
    'lvl.va.U6VA.OUTa': [6373.5, 5937.7, 6034.8], 'lvl.nc3.M3': [6853.0, 7128.7, 7003.4], 'lvl.j1.M3': [6834.3, 6402.8, 6799.8],
    'lvl.nc3.U6VA.M4': [13104.8, 12925.2, 12774.8], 'lvl.j1.U9.M4': [13240.9, 12407.5, 12947.8], 'lvl.va.U9.M4': [12778.7, 12434.3, 12435.0],
    # section 0 item 7 / section 5: link 174 TTT
    'l174.va': [59.0, 60.9, 62.0], 'l174.j1': [339.5, 66.2, 361.4], 'l174.nc3': [43.1, 43.4, 46.1],
    'l174max.va': [88, 75, 92],
    # section 0 item 8 / 6.1: SC109 p3 <= 24.5
    'p3.va': [6, 5, 6], 'p3.j1': [22, 0, 35], 'p3first.va': [8100, 7200, 6750], 'p3first.j1': [3900, None, 3750],
    # item 9: input 282 remain
    'rem282.va': [0, 36, 18], 'rem282.nc3': [0, 0, 0], 'rem282.j1': [13, 16, 0],
    'unins282.va': [195.6, 259.1, 265.3], 'unins282.nc3': [115.6, 109.5, 111.8],
    # item 10: 1220000704 d
    'd704.A': [7.17, 6.62, 6.85], 'd704.B': [-4.10, 3.82, -4.34],
    # item 11/12/13
    'vsl.va': [9, 10, 14], 'vsl.j1': [3, 4, 0], 'prev.va': [2, 3, 0], 'prev.j1': [1, 4, 0],
    'ratio': [1.1426, 1.3657, 0.9654],
    # 1083 inserted (section 5)
    'ins1083.va': [1312, 1275, 1279], 'ins1083.nc3': [1312, 1275, 1279], 'ins1083.j1': [1221, 1275, 1094],
}
P = F['pairs']
for pk in ('A', 'B'):
    for m in ('M3', 'M4', 'OUTa', 'M4b'):
        st = P[pk]['stats'][m]
        for i, s in enumerate(S):
            ck('rep.%s.%s.s%s' % (pk, m, s), st['d'][i], REP['%s.%s' % (pk, m)][i], 0.051)
        if '%s.%s.mean' % (pk, m) in REP:
            ck('rep.%s.%s.mean' % (pk, m), st['mean'], REP['%s.%s.mean' % (pk, m)], 0.051)
        if '%s.%s.ci' % (pk, m) in REP:
            for j in (0, 1):
                ck('rep.%s.%s.ci%d' % (pk, m, j), st['ci'][j], REP['%s.%s.ci' % (pk, m)][j], 0.051)
        if '%s.%s.sd' % (pk, m) in REP:
            ck('rep.%s.%s.sd' % (pk, m), st['sd'], REP['%s.%s.sd' % (pk, m)], 0.051)
    for i, s in enumerate(S):
        ck('rep.%s.remA.s%s' % (pk, s), P[pk]['stats']['remA']['d'][i], REP['%s.remA' % pk][i], 1e-9)
L = F['levels']
for i, s in enumerate(S):
    ck('rep.lvl.va.M3.s%s' % s, L['U6VA|va_s%s' % s]['M3'], REP['lvl.va.M3'][i], 0.051)
    ck('rep.lvl.nc3.M3.s%s' % s, L['U6VA|nc3_s%s' % s]['M3'], REP['lvl.nc3.M3'][i], 0.051)
    ck('rep.lvl.j1.M3.s%s' % s, L['U9|j1_s%s' % s]['M3'], REP['lvl.j1.M3'][i], 0.051)
    for k in ('M4', 'M4b', 'OUTa'):
        ck('rep.lvl.va.U6VA.%s.s%s' % (k, s), L['U6VA|va_s%s' % s][k], REP['lvl.va.U6VA.%s' % k][i], 0.051)
    ck('rep.lvl.nc3.U6VA.M4.s%s' % s, L['U6VA|nc3_s%s' % s]['M4'], REP['lvl.nc3.U6VA.M4'][i], 0.051)
    ck('rep.lvl.j1.U9.M4.s%s' % s, L['U9|j1_s%s' % s]['M4'], REP['lvl.j1.U9.M4'][i], 0.051)
    ck('rep.lvl.va.U9.M4.s%s' % s, L['U9|va_s%s' % s]['M4'], REP['lvl.va.U9.M4'][i], 0.051)
    for arm in ('va', 'j1', 'nc3'):
        pr = F['per_run']['%s_s%s' % (arm, s)]
        ck('rep.l174.%s.s%s' % (arm, s), pr['link174_ttt'], REP['l174.%s' % arm][i], 0.051)
        ck('rep.rem282.%s.s%s' % (arm, s), pr['remains'].get('282', 0), REP['rem282.%s' % arm][i], None)
        ck('rep.ins1083.%s.s%s' % (arm, s), pr['inserted_1083'], REP['ins1083.%s' % arm][i], None)
    ck('rep.l174max.va.s%s' % s, F['per_run']['va_s%s' % s]['link174_frame_max'], REP['l174max.va'][i], None)
    for arm in ('va', 'nc3'):
        ck('rep.unins282.%s.s%s' % (arm, s), L['U6VA|%s_s%s' % (arm, s)]['unins_by_input']['282'], REP['unins282.%s' % arm][i], 0.051)
    ck('rep.d704.A.s%s' % s, P['A']['stats']['l704']['d'][i], REP['d704.A'][i], 0.0051)
    ck('rep.d704.B.s%s' % s, P['B']['stats']['l704']['d'][i], REP['d704.B'][i], 0.0051)
    for arm in ('va', 'j1'):
        c = F['control']['%s_s%s' % (arm, s)]
        ck('rep.p3.%s.s%s' % (arm, s), c['p3_le_245'], REP['p3.%s' % arm][i], None)
        ck('rep.p3first.%s.s%s' % (arm, s), c['p3_first_T'], REP['p3first.%s' % arm][i], None)
        ck('rep.vsl.%s.s%s' % (arm, s), c['vsl_fwe_lt110'], REP['vsl.%s' % arm][i], None)
        ck('rep.prev.%s.s%s' % (arm, s), len(c['prev_plan_all']), REP['prev.%s' % arm][i], None)
    ck('rep.ratio.s%s' % s, F['wall_ratio'][s], REP['ratio'][i], 0.00005)
ck('rep.d704.A.mean', P['A']['stats']['l704']['mean'], 6.9, 0.051)
ck('rep.d704.A.ci', [round(x, 1) for x in P['A']['stats']['l704']['ci']], [6.4, 7.3], None)
ck('rep.d704.A.ci_excl0', P['A']['stats']['l704']['ci_excl0'], True, None)
ck('rep.d704.B.mean', P['B']['stats']['l704']['mean'], -1.5, 0.051)
ck('net_same', all(F['net_same_as_nc3_s31'].values()), True, None)
ck('unknown_links', sorted({l for t, pr in F['per_run'].items() for l in pr['unknown_links']}), [], None)

bad = [r for r in rows if not r['ok']]
with io.open(os.path.join(HERE, 'out', 'compare_fresh.json'), 'w', encoding='utf-8') as f:
    json.dump(dict(n=len(rows), bad=len(bad), rows=rows), f, ensure_ascii=False, indent=1, default=str)
for r in bad:
    print('BAD', r['check'], r['fresh'], r['other'])
print('CHECKS %d/%d' % (len(rows) - len(bad), len(rows)))
print('ALL_OK' if not bad else 'NOT_OK')
