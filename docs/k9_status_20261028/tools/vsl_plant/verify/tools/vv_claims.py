"""VERIFY_VP claim check (verifier tool, 2026-10-27 KST).  Compares the numbers printed in VP_RESULTS.md r1
(f7f105fe...; the expected values below are copied from that document's text, not from any producer output) with
the independent recompute (vv_recompute.py output).  A printed value d with k decimals matches when
|recomputed - d| <= 0.5 * 10^-k + 1e-9 (display rounding); counts match exactly.

    python -B vv_claims.py <vv_recompute.json> <out.json>"""
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
CHECKS = []


def tol(k):
    return 0.5 * 10 ** (-k) + 1e-9


def num(cid, got, want, k):
    ok = got is not None and abs(got - want) <= tol(k)
    CHECKS.append({'id': cid, 'want': want, 'got': got, 'ok': bool(ok)})


def eq(cid, got, want):
    CHECKS.append({'id': cid, 'want': want, 'got': got, 'ok': got == want})


# section 1.1 rows: label, T, tag, rec head10, dJ101, dJ100, dJ90, d(101-100), dFWE100, drest100, ARM110-REC
T11 = [('v3c3-s31', 3300, 'A1', [110, 110, 110], .380, .442, 1.193, -.061, .515, -.073, 0.000),
       ('v3c3-s31', 3450, 'A2', [100, 110, 110], .118, .154, .682, -.036, .175, -.022, -.097),
       ('v3c3-s31', 4050, 'A3', [100, 100, 100], .547, .628, 1.578, -.080, .661, -.033, -.628),
       ('v3c3-s31', 4800, 'A4', [110, 110, 100], .817, .918, 2.025, -.101, .971, -.053, -.026),
       ('v3c3-s41', 2400, 'A1', [110, 110, 110], .231, .281, .966, -.050, .297, -.015, 0.000),
       ('v3c3-s41', 2550, 'A2', [100, 100, 110], .009, .036, .484, -.026, .031, .005, -.035),
       ('v3c3-s41', 3300, 'A3', [100, 100, 100], -.059, -.036, .413, -.023, -.054, .018, .036),
       ('v3c3-s41', 4200, 'A4', [110, 100, 100], -.083, -.068, .272, -.015, -.209, .142, -.015),
       ('v3c3-s43', 2700, 'A1', [110, 110, 110], .186, .229, .861, -.043, .282, -.054, 0.000),
       ('v3c3-s43', 2850, 'A2', [100, 100, 110], .052, .075, .435, -.023, .054, .021, -.073),
       ('v3c3-s43', 3750, 'A3', [100, 100, 100], -.155, -.145, .167, -.010, -.191, .046, .145),
       ('v3c3-s43', 5100, 'A4', [110, 110, 110], .709, .801, 1.849, -.092, .921, -.120, 0.000)]
# section 1.2 zone veh*h (arm - 110): median, min, max, + count
Z12 = {100: {'B1': (.048, .015, .069, 12), 'M1': (.598, -.337, .683, 10), 'VSa': (-.324, -.950, .489, 4),
             "VS0'": (-.145, -.219, .146, 3), 'VSb': (.213, .015, .691, 12), 'D': (-.241, -.563, .338, 3)},
       90: {'B1': (.116, .094, .170, 12), 'M1': (1.399, .313, 1.580, 12), 'VSa': (-.053, -1.197, 1.065, 5),
            "VS0'": (-.136, -.247, .313, 4), 'VSb': (.447, .133, 1.057, 12), 'D': (-.964, -1.212, -.128, 0)}}
# section 1.3: resp median/min/max (2 dec), bias median/min/max (1 dec), ratio median (1 dec), count > 1
R13 = {'M1': (5.25, 1.05, 7.62, 3.7, 1.2, 18.3, 0.5, 5), 'VSa': (2.77, 0.74, 6.59, 20.6, 2.0, 40.0, 5.4, 10),
       "VS0'": (1.50, 0.50, 4.21, 27.3, 1.1, 51.1, 13.4, 11), 'VSb': (1.40, 0.82, 3.81, 11.3, 0.0, 20.6, 6.0, 11)}
ONOFF = {'on': (22, {'B1': 36.3, 'VSa': -18.4, "VS0'": -22.9, 'VSb': 4.3, 'D': -19.3}),
         'off': (14, {'B1': 32.1, 'VSa': -26.0, "VS0'": -36.1, 'VSb': 2.8, 'D': -14.3})}
# section 1.4: P1 9-state e speed (min, max, sign, count), 12-state e speed (min, max, sign, count),
# p speed range, v speed range, P1 stock e (min, max, sign, count)
T14 = {'U': ((-4.8, 9.2, '+', 8), (2.4, 7.6, '+', 12), (98.0, 103.8), (91.8, 108.6), (-33.6, 25.7, '-', 7)),
       'B1': ((7.8, 36.0, '+', 9), (21.4, 41.6, '+', 12), (99.7, 109.9), (67.3, 102.2), (-27.6, -1.1, '-', 9)),
       'cell12': ((23.1, 63.9, '+', 9), (51.7, 62.9, '+', 12), (95.1, 109.4), (35.5, 86.3), None),
       'M1': ((2.3, 6.5, '+', 9), (-2.4, 18.3, '+', 9), (99.4, 109.2), (93.9, 106.8), (-8.5, 0.0, '-', 9)),
       'VSa': ((-32.5, -20.3, '-', 9), (-40.0, 2.3, '-', 10), (68.8, 89.5), (97.0, 109.8), (4.0, 15.3, '+', 9)),
       "VS0'": ((-48.5, -32.1, '-', 9), (-51.1, 1.1, '-', 11), (54.5, 74.2), (86.6, 110.1), (3.6, 9.4, '+', 9)),
       'VSb': ((-17.8, 18.4, '-', 8), (-17.3, 20.6, '-', 3), (79.5, 94.2), (61.0, 107.0), (-35.1, 17.8, '+', 8)),
       'D': ((-15.1, -7.4, '-', 9), (-21.0, -10.6, '-', 12), (92.0, 102.6), (107.1, 110.5), (1.0, 25.4, '+', 9))}
# section 1.5: per candidate, 5 metrics (median R 2 dec, band, n>=0.5, n), J d (median, min, max)
MET = ['m1', 'm2', 'm3', 'm4', 'm5']
T15 = {'C1_vfree': ([(.02, 'C', 0, 9), (.62, 'A', 8, 9), (.06, 'C', 0, 9), (.02, 'C', 0, 9), (.02, 'C', 0, 9)], (.19, .13, .22, 2)),
       'C2_rhocrit': ([(.38, 'B', 1, 9), (-.99, 'C', 0, 9), (.48, 'B', 2, 9), (.46, 'B', 2, 9), (.25, 'B', 0, 9)], (-1.46, -1.97, -.82, 2)),
       'C3_merge': ([(.02, 'C', 0, 9), (-.11, 'C', 0, 9), (.14, 'C', 0, 9), (.15, 'C', 0, 9), (.01, 'C', 0, 9)], (-.31, -.43, -.19, 2)),
       'C4_lanedrop': ([(.63, 'A', 9, 9), (-.18, 'C', 0, 9), (.16, 'C', 1, 9), (.24, 'B', 0, 9), (.58, 'A', 9, 9)], (-.83, -.97, -.57, 2)),
       'C7_initial': ([(-.00, 'C', 0, 9), (-.02, 'C', 0, 5), (-.00, 'C', 0, 9), (-.00, 'C', 0, 8), (-.00, 'C', 0, 9)], (.002, -.018, .015, 3)),
       'C8_antic18': ([(.15, 'C', 0, 9), (-.05, 'C', 0, 9), (.01, 'C', 0, 9), (.03, 'C', 0, 9), (.11, 'C', 0, 9)], (-.11, -.24, 1.13, 2)),
       'C9_lanedrop_both': ([(.92, 'A', 9, 9), (-.23, 'C', 0, 9), (.30, 'B', 2, 9), (.41, 'B', 2, 9), (.94, 'A', 9, 9)], (-1.24, -1.43, -.86, 2))}
RULE = {('C1_vfree', 'm2'), ('C4_lanedrop', 'm1'), ('C4_lanedrop', 'm5'), ('C9_lanedrop_both', 'm1'),
        ('C9_lanedrop_both', 'm5')}
GROWS = {('C2_rhocrit', 'm2'), ('C9_lanedrop_both', 'm2')}


def main():
    rc = json.load(open(sys.argv[1], encoding='utf-8'))
    A = {(r['label'], r['T']): r for r in rc['A_rows']}
    S = rc['A_summary']
    for lab, T, tag, head, d101, d100, d90, d1, dfw, drest, a110 in T11:
        r = A[(lab, T)]
        cid = '1.1 %s T%d' % (lab, T)
        eq(cid + ' tag', r['tag'], tag)
        eq(cid + ' rec_head10', [x[0] if len(x) == 1 else x for x in r['rec_head10']], head)
        for name, got, want in (('dJ101', r['dJ101'], d101), ('dJ100', r['dJ100'], d100), ('dJ90', r['dJ90'], d90),
                                ('d101-100', r['dJ101_100'], d1), ('dFWE100', r['dFWE100'], dfw),
                                ('drest100', r['drest100'], drest), ('ARM110-REC', r['ARM110_minus_REC'], a110)):
            num(cid + ' ' + name, got, want, 3)
    for key, want in (('sign_VSL_100', (2, 0, 4, -.145, .628)), ('sign_VSL_90', (0, 0, 6, .167, 1.578)),
                      ('sign_110_100', (1, 0, 5, -.068, .918)), ('sign_110_90', (0, 0, 6, .272, 2.025))):
        g = S[key]
        eq('1.2 ' + key + ' counts', [g['neg'], g['zero'], g['pos']], list(want[:3]))
        num('1.2 ' + key + ' min', g['range'][0], want[3], 3)
        num('1.2 ' + key + ' max', g['range'][1], want[4], 3)
    for arm, zz in Z12.items():
        for z, (m, lo, hi, pos) in zz.items():
            g = S['zone_vehh_%d' % arm][z]
            num('1.2 vehh %d %s median' % (arm, z), g['median'], m, 3)
            num('1.2 vehh %d %s min' % (arm, z), g['range'][0], lo, 3)
            num('1.2 vehh %d %s max' % (arm, z), g['range'][1], hi, 3)
            eq('1.2 vehh %d %s pos' % (arm, z), g['pos'], pos)
        g = S['zone_vehh_%d' % arm]['U']
        eq('1.2 vehh %d U all 0<d<0.001' % arm, bool(g['range'][0] > 0 and g['range'][1] < 0.001), True)
    eq('1.2 origin queue all 0', S['origin_queue_max_abs_vehh'] == 0.0, True)
    eq('0.1 dJ100 pos 9 neg 3', [S['dJ100_all']['pos'], S['dJ100_all']['neg']], [9, 3])
    eq('0.1 dJ90 pos 12', S['dJ90_all']['pos'], 12)
    eq('0.1 dJ101-100 neg 12', S['dJ101_100_all']['neg'], 12)
    eq('0.2 ARM110<REC (<=-0.01) in VSL states', S['ARM110_lt_REC_count_le_-0.01'], 4)
    eq('2.1 dFWE100 pos 9/12', S['dFWE100_pos'], 9)
    for z, (rm, rl, rh, bm, bl, bh, qm, qn) in R13.items():
        g = S['resp_vs_bias'][z]
        num('1.3 %s resp median' % z, g['resp_median'], rm, 2)
        num('1.3 %s resp min' % z, g['resp_range'][0], rl, 2)
        num('1.3 %s resp max' % z, g['resp_range'][1], rh, 2)
        num('1.3 %s bias median' % z, g['bias_median'], bm, 1)
        num('1.3 %s bias min' % z, g['bias_range'][0], bl, 1)
        num('1.3 %s bias max' % z, g['bias_range'][1], bh, 1)
        num('1.3 %s ratio median' % z, g['ratio_median'], qm, 1)
        eq('1.3 %s ratio>1 count' % z, g['ratio_gt1'], qn)
    for k, (n, zz) in ONOFF.items():
        g = S['block_groups'][k]
        eq('1.3 block group %s n' % k, g['n'], n)
        for z, v in zz.items():
            num('1.3 block group %s %s' % (k, z), g[z], v, 1)
    num('1.3 start speed max', S['start_max_abs_speed'], 9.2, 1)
    num('1.3 start stock max', S['start_max_abs_stock'], 6.0, 1)
    P = rc['P_base']
    E12 = S['exec_e_speed_w450_12']
    for z, (p9, p12, pr, vr, st) in T14.items():
        g = P[z]
        num('1.4 %s P1 e speed min' % z, g['e_speed_range'][0], p9[0], 1)
        num('1.4 %s P1 e speed max' % z, g['e_speed_range'][1], p9[1], 1)
        eq('1.4 %s P1 e speed sign count' % z, g['e_speed_pos'] if p9[2] == '+' else g['e_speed_neg'], p9[3])
        h = E12[z]
        num('1.4 %s 12 e speed min' % z, h['range'][0], p12[0], 1)
        num('1.4 %s 12 e speed max' % z, h['range'][1], p12[1], 1)
        eq('1.4 %s 12 e speed sign count' % z, h['pos'] if p12[2] == '+' else h['neg'], p12[3])
        num('1.4 %s P1 p speed min' % z, g['p_speed_range'][0], pr[0], 1)
        num('1.4 %s P1 p speed max' % z, g['p_speed_range'][1], pr[1], 1)
        num('1.4 %s P1 v speed min' % z, g['v_speed_range'][0], vr[0], 1)
        num('1.4 %s P1 v speed max' % z, g['v_speed_range'][1], vr[1], 1)
        if st:
            num('1.4 %s P1 e stock min' % z, g['e_stock_range'][0], st[0], 1)
            num('1.4 %s P1 e stock max' % z, g['e_stock_range'][1], st[1], 1)
            eq('1.4 %s P1 e stock sign count' % z, g['e_stock_pos'] if st[2] == '+' else g['e_stock_neg'], st[3])
    eq('1.4 VSb 12 e speed pos count (+8)', E12['VSb']['pos'], 8)
    U = rc['union21']
    for z, s in (('B1', 'pos'), ('cell12', 'pos'), ('D', 'neg')):
        eq('1.6 21/21 same sign %s' % z, U[z][s], 21)
    T = rc['P_Rtable']
    for c, (mets, (jm, jl, jh, jk)) in T15.items():
        for mid, (mR, band, kk, n) in zip(MET, mets):
            g = T[c][mid]
            num('1.5 %s %s median R' % (c, mid), g['median_R'], mR, 2)
            eq('1.5 %s %s band' % (c, mid), g['band'], band)
            eq('1.5 %s %s n>=0.5/n' % (c, mid), [g['n_ge_0.5'], g['n']], [kk, n])
            eq('1.5 %s %s rule' % (c, mid), g['rule'], (c, mid) in RULE)
            eq('1.5 %s %s grows' % (c, mid), g['grows'], (c, mid) in GROWS)
        num('1.5 %s J median' % c, T[c]['J_d']['median'], jm, jk)
        num('1.5 %s J min' % c, T[c]['J_d']['range'][0], jl, jk)
        num('1.5 %s J max' % c, T[c]['J_d']['range'][1], jh, jk)
    for c in ('C5_capdrop', 'C6_compliance'):
        eq('1.5 %s bit-equal base 9/9' % c, T[c]['bit_equal_base_states'], 9)
    R = rc['P_residual']
    num('1.5 C9 residual VSa median', R['C9_lanedrop_both']['m1']['median_ec'], -1.9, 1)
    num("1.5 C9 residual VS0' median", R['C9_lanedrop_both']['m5']['median_ec'], -2.4, 1)
    num("1.5 C9 residual VS0' max (+15.1)", R['C9_lanedrop_both']['m5']['range_ec'][1], 15.1, 1)
    num('1.5 C8 R min VSa', T['C8_antic18']['m1']['min_R'], -1.18, 2)
    num("1.5 C8 R min VS0'", T['C8_antic18']['m5']['min_R'], -0.81, 2)
    PC = rc['P_checks']
    eq('1.7 P exit0 9', PC['exit0'], 9)
    eq('1.7 P jobcheck hits 0', PC['jobcheck_hits'], 0)
    eq('1.7 P R1 obj <= 1e-9', PC['R1_obj_max_abs'] <= 1e-9, True)
    eq('1.7 P R1 bit-diff states 2', len(PC['R1_obj_bit_diff']), 2)
    eq('1.7 P R1 bit-diff max <= 1.14e-13', max(abs(x[2]) for x in PC['R1_obj_bit_diff']) <= 1.14e-13 + 1e-16, True)
    eq('1.7 P R3 9', PC['R3_bit'], 9)
    eq('1.7 P null 9', PC['null_bit'], 9)
    eq('1.7 P reach 90/90', [PC['reach_ok'], PC['reach_n']], [90, 90])
    eq('1.7 A exit0 12', S['exit0'], 12)
    eq('1.7 A jobcheck hits 0', S['jobcheck_hits'], 0)
    eq('1.7 A R1 obj <= 1e-9', S['R1_obj_max_abs'] <= 1e-9, True)
    eq('1.7 A R1 bit-diff states 4', len(S['R1_obj_bit_diff_states']), 4)
    eq('1.7 A R1 bit-diff max <= 1.7e-13', max(abs(x[2]) for x in S['R1_obj_bit_diff_states']) <= 1.71e-13, True)
    eq('1.7 A R3 12', S['R3_bit_all'], 12)
    eq('1.4 X1 = 0 (A all plans, P all plans)', [S['X1_max_all_plans'], PC['X1_all_plans_max']], [0.0, 0.0])
    F = rc['P1P_fd']['cells']
    for c, v in ((12, 9.0), (13, 9.1), (14, 3.1), (15, 2.4)):
        num('1.4 FD-VISSIM cell %d' % c, F[str(c)]['fd_minus_vissim'] if str(c) in F else F[c]['fd_minus_vissim'], v, 1)
    for c in (16, 17, 18):
        g = F[str(c)] if str(c) in F else F[c]
        eq('1.4 FD-VISSIM cell %d in [-1.3,-1.2] (1 dec)' % c, -1.35 <= g['fd_minus_vissim'] <= -1.15, True)
    num('1.6 M1 FD-VISSIM mean (+2.76)', rc['P1P_fd']['M1_mean_fd_minus_vissim'], 2.76, 2)
    ok = sum(c['ok'] for c in CHECKS)
    res = {'schema': 'vv-claims/1', 'n': len(CHECKS), 'ok': ok, 'fail': [c for c in CHECKS if not c['ok']],
           'checks': CHECKS}
    outp = Path(sys.argv[2])
    tmp = outp.with_name(outp.name + '.tmp%d' % os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    os.replace(tmp, outp)
    print('VV_CLAIMS n=%d ok=%d fail=%d' % (len(CHECKS), ok, len(CHECKS) - ok))


if __name__ == '__main__':
    main()
