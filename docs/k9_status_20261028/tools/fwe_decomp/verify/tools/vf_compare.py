# -*- coding: utf-8 -*-
"""vf_compare.py - VERIFY_FWE: pair differences from vf_fzp.py / vf_meter.py outputs and comparison with the
hand-transcribed claims of FWE_DECOMP.md r1 (claims_r1.py). Light job: reads only verify/out JSON, provenance JSON
and the codex summary (level anchor). 2026-10-27 KST.

Integration forms (PRE_FWE.md section 7.2):
  ours  : frames t >= 1.0 s (0.1 s frame skipped) and t <= W, trapezoid between consecutive frames, no end extension.
  codex : from (t=0, empty), all frames t <= W, trapezoid, last frame stock held to W.
  bin   : rows t >= 1.0 s, 300 s bins, vehicle-frames x 5 s / 3600.
4b (uninserted) pair difference: dU(a, b, W) = S(b) - S(a), S = sum over first-seen t <= W of (W - t) / 3600.
Same-seed pairs inside one network only; 64cf and v3c3 are never subtracted from each other.
Usage: python -B vf_compare.py <verify_dir>
"""
import hashlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claims_r1 as C  # noqa: E402

VD = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FZ = os.path.join(VD, 'out', 'fzp')
S7 = ('74', '10699', '2', '10613', '119', '10702', '24')
ONR_FROM = {'10639': '70', '10681': '68', '10490': '129', '10484': '31'}
OFR = ('10643', '10682', '10481', '10483')
S19 = S7 + tuple(ONR_FROM) + tuple(ONR_FROM.values()) + OFR
ZONES = ('U', 'B1', 'M', 'B2', 'D')
PROV = {
    'nc_s31': 'D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/run/run.json',
    'nc_s41': 'D:/VISSIM_runs/20261001_v3c3/s41_v3c3nc/run/run.json',
    'nc_s43': 'D:/VISSIM_runs/20261001_v3c3/s43_v3c3nc/run/run.json',
    'va_s31': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/run_provenance_sdmpc31_v3c3_k92va_s31.json',
    'va_s41': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/run_provenance_sdmpc31_v3c3_k92va_s41.json',
    'va_s43': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/run_provenance_sdmpc31_v3c3_k92va_s43.json',
    'b_s31': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/run_provenance_sdmpc31_sdmpc9000_s31.json',
    'b_s41': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/run_provenance_sdmpc31_sdmpc9000_s41.json',
    'b_s43': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/run_provenance_sdmpc31_sdmpc9000_s43.json',
    'vsl_s41': 'D:/VISSIM_runs/20261027_vsl_v3c3/s41/run/run.json',
    'vsl_s43': 'D:/VISSIM_runs/20261027_vsl_v3c3/s43/run/run.json',
    'j1_s41': 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s41/run_provenance_sdmpc31_v3c3_k8j1_s41.json',
    'cxnc_s29': 'D:/VISSIM_handoff/20261024/raw/nc/run_provenance_sdmpc31_nc9000_s29.json',
    'cxj_s29': 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/run_provenance_sdmpc31_sdmpc8100_s29.json',
}
NET = {t: ('64cf' if t.endswith('s29') else 'v3c3') for t in PROV}
PAIRS = {  # name -> (arm tag prefix, base tag prefix, seeds, form, W, nbins)
    'P-VA': ('va', 'nc', ('s31', 's41', 's43')), 'P-B': ('b', 'nc', ('s31', 's41', 's43')),
    'P-BVA': ('b', 'va', ('s31', 's41', 's43')), 'P-VSL': ('vsl', 'nc', ('s41', 's43')), 'P-J1': ('j1', 'nc', ('s41',)),
    'Q-joint': ('cxj', 'cxnc', ('s29',)),
}
SUMMARY = 'D:/VISSIM_handoff/20261024/analysis/comparison/summary.json'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(tag):
    p = os.path.join(FZ, tag + '.json')
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding='utf-8'))
    d['_sha_out'] = sha(p)
    return d


def integ(d, group, form, W):
    f = np.asarray(d['frames_t10'], dtype=np.int64)
    n = np.asarray(d['fc'][group] if group in d['fc'] else d['fcl'][group], dtype=float)
    W10 = int(round(W * 10))
    if form == 'ours':
        m = (f >= 10) & (f <= W10)
        f, n = f[m], n[m]
        return float(np.sum((n[1:] + n[:-1]) / 2.0 * np.diff(f) / 10.0) / 3600.0)
    m = f <= W10
    f = np.concatenate([[0], f[m]]); n = np.concatenate([[0.0], n[m]])
    a = np.sum((n[1:] + n[:-1]) / 2.0 * np.diff(f) / 10.0) + n[-1] * (W10 - f[-1]) / 10.0
    return float(a / 3600.0)


def integ_set(d, links, form, W):
    return sum(integ(d, l, form, W) for l in links)


def S_int(d, W, cats=None):
    tot = 0.0
    for c, dd in d['first_seen'].items():
        if cats and c not in cats:
            continue
        for tt, k in dd.items():
            t = int(tt) / 10.0
            if t <= W:
                tot += k * (W - t)
    return tot / 3600.0


def bins(d, key, sub=None):
    src = d[key] if sub is None else d[key][sub]
    return np.asarray(src, dtype=float) * 5.0 / 3600.0


def d1_bins(d):
    return sum(bins(d, 'b300_link', l) for l in S7)


def d2_bins(d):
    return sum(bins(d, 'b300_link', l) for l in S19)


def merge_counts(d, c):
    return np.asarray(d['merge300'][c], dtype=float)


def stock_bins(d, conns):
    return sum(bins(d, 'b300_link', c) + bins(d, 'b300_link', ONR_FROM[c]) for c in conns)


def w900(arr, start, nb):  # sum of 300 s bins in [start, start+900)
    b0 = start // 300
    return float(np.sum(arr[b0:min(b0 + 3, nb)]))


def tgain(dd, nb):
    a = None; half = None
    for b in range(3, nb):
        if dd[b] <= -2.0 and a is None:
            a = b
    cum = np.cumsum(dd[3:nb]); fin = cum[-1]
    if fin < 0:
        for i, v in enumerate(cum):
            if v <= fin / 2.0:
                half = i + 3; break
    return a, half, float(fin)


def main():
    R = {'tool_sha256': sha(os.path.abspath(__file__)), 'claims_sha256': sha(C.__file__), 'runs': {}, 'pairs': {}, 'checks': {}, 'cmp': []}
    D = {}
    for t, pp in PROV.items():
        d = load(t)
        if d is None:
            R['runs'][t] = 'missing'; continue
        seed = json.load(open(pp, encoding='utf-8-sig')).get('seed')
        D[t] = d
        m = d['meta']
        R['runs'][t] = {'seed_provenance': seed, 'provenance_sha256': sha(pp), 'fzp_sha256': m['sha256'], 'sha_eq_expected': m['sha256'] == m['expected_sha256'],
                        'rows': m['rows'], 'rows_t_lt_1': m['rows_t_lt_1'], 'frames': m['frames'], 't10_first': m['t10_first'], 't10_last': m['t10_last'],
                        'n_vehicles': m['n_vehicles'], 'other_chain_entries': m['other_chain_entries'], 'out_sha256': d['_sha_out'], 'tool_sha256': m['tool_sha256'],
                        'L1_ours_9000': integ_set(d, S7, 'ours', 9000), 'L1_codex_8100': integ_set(d, S7, 'codex', 8100),
                        'zone_sum_eq_link_sum': bool(np.allclose(sum(np.asarray(d['b300_zone'][z]) for z in ZONES), sum(np.asarray(d['b300_link'][l]) for l in S7)))}
    # level anchor: codex summary (codex form 0-8100) for codex NC and joint
    summ = json.load(open(SUMMARY, encoding='utf-8-sig'))['reporting_partition']['parts']
    anc = {}
    for t, k in (('cxnc_s29', 'nc'), ('cxj_s29', 'joint')):
        if t in D:
            d = D[t]
            mine = {'FW_E': integ(d, 'S7', 'codex', 8100), 'urban_roads': integ(d, 'URBAN', 'codex', 8100), 'omega': integ(d, 'O701', 'codex', 8100),
                    'FW_W': integ(d, 'FWW3', 'codex', 8100)}
            anc[k] = {q: {'mine': v, 'codex': summ[k][q], 'diff': v - summ[k][q]} for q, v in mine.items()}
    R['checks']['codex_summary_anchor'] = anc
    R['checks']['summary_sha256'] = sha(SUMMARY)

    def cmp(key, mine, claim, tol):
        if claim is None or mine is None:
            return
        ok = abs(mine - claim) <= tol
        R['cmp'].append({'key': key, 'mine': round(mine, 4), 'claim': claim, 'diff': round(mine - claim, 4), 'ok': bool(ok), 'tol': tol})

    for pn, (a, b, seeds) in PAIRS.items():
        for s in seeds:
            A, B = a + '_' + s, b + '_' + s
            if A not in D or B not in D:
                R['pairs'][pn + '|' + s] = 'missing'; continue
            sa, sb = R['runs'][A]['seed_provenance'], R['runs'][B]['seed_provenance']
            assert sa == sb and NET[A] == NET[B], (A, B)
            da, db = D[A], D[B]
            form, W = ('codex', 8100) if NET[A] == '64cf' else ('ours', 9000)
            nb = 27 if NET[A] == '64cf' else 30
            P = {'seed': sa, 'net': NET[A], 'form': form, 'W': W}
            P['d1'] = integ(da, 'S7', form, W) - integ(db, 'S7', form, W)
            P['d2'] = integ(da, 'S19', form, W) - integ(db, 'S19', form, W)
            P['d1_codex8100'] = integ(da, 'S7', 'codex', 8100) - integ(db, 'S7', 'codex', 8100)
            for g in ('O701', 'URBAN', 'ALL', 'FWW3', 'L66'):
                P[g] = integ(da, g, form, W) - integ(db, g, form, W)
            P['U'] = S_int(db, W) - S_int(da, W)
            P['u1098'] = S_int(db, W, {'74'}) - S_int(da, W, {'74'})
            P['u1099'] = S_int(db, W, {'26'}) - S_int(da, W, {'26'})
            P['A4'] = P['ALL'] + P['U']; P['outa'] = P['A4'] - P['O701']; P['outb'] = P['ALL'] - P['O701']
            base_lvl = integ(db, 'S7', form, W) if pn != 'P-BVA' else integ(D['nc_' + s], 'S7', form, W)
            P['pct'] = 100.0 * P['d1'] / base_lvl
            # bin form
            d1a, d1b = d1_bins(da), d1_bins(db)
            dd1 = (d1a - d1b)[:nb]
            P['d1_bin300'] = dd1.tolist(); P['d2_bin300'] = (d2_bins(da) - d2_bins(db))[:nb].tolist()
            P['pre900_abs_d2'] = float(np.sum(np.abs((d2_bins(da) - d2_bins(db))[:3])))
            zd = {z: (bins(da, 'b300_zone', z) - bins(db, 'b300_zone', z))[:nb] for z in ZONES}
            P['zone_900_end'] = {z: float(np.sum(v[3:nb])) for z, v in zd.items()}
            P['zone_w900'] = {z: {str(w): w900(v, w, nb) for w in range(900, nb * 300, 900)} for z, v in zd.items()}
            c59c = (bins(da, 'b300_cell59', 'center') - bins(db, 'b300_cell59', 'center'))[:nb]
            c59x = (bins(da, 'b300_cell59', 'exact') - bins(db, 'b300_cell59', 'exact'))[:nb]
            P['cell59_center_900_end'] = float(np.sum(c59c[3:])); P['cell59_exact_900_end'] = float(np.sum(c59x[3:]))
            P['resid_d1_minus_cell59'] = P['d1'] - P['cell59_center_900_end']
            P['d1_bin_900_end'] = float(np.sum(dd1[3:]))
            ta, th, fin = tgain(dd1, nb)
            P['Tgain_a_start'] = None if ta is None else ta * 300; P['Thalf_start'] = None if th is None else th * 300
            P['d1_w900'] = {str(w): w900(dd1, w, nb) for w in range(900, nb * 300, 900)}
            P['merge_w900_vph'] = {}; P['merge_arm_w900_vph'] = {}; P['merge_base_w900_vph'] = {}
            for c in ONR_FROM:
                ma, mb = merge_counts(da, c)[:nb], merge_counts(db, c)[:nb]
                P['merge_w900_vph'][c] = {str(w): 4.0 * (w900(ma, w, nb) - w900(mb, w, nb)) for w in range(900, nb * 300, 900)}
                P['merge_arm_w900_vph'][c] = {str(w): 4.0 * w900(ma, w, nb) for w in range(900, nb * 300, 900)}
                P['merge_base_w900_vph'][c] = {str(w): 4.0 * w900(mb, w, nb) for w in range(900, nb * 300, 900)}
            st4 = (stock_bins(da, ONR_FROM) - stock_bins(db, ONR_FROM))[:nb]
            st1 = (stock_bins(da, ['10639']) - stock_bins(db, ['10639']))[:nb]
            P['stock4_all'] = float(np.sum(st4)); P['stock4_900_end'] = float(np.sum(st4[3:]))
            P['stock10639_all'] = float(np.sum(st1)); P['stock10639_900_end'] = float(np.sum(st1[3:]))
            P['stock4_w900'] = {str(w): w900(st4, w, nb) for w in range(900, nb * 300, 900)}
            P['stock_by_meter_900_end'] = {c: float(np.sum((stock_bins(da, [c]) - stock_bins(db, [c]))[3:nb])) for c in ONR_FROM}
            off = (bins(da, 'b300_link', '10643') - bins(db, 'b300_link', '10643'))[:nb]
            P['off10643_all'] = float(np.sum(off)); P['off10643_900_end'] = float(np.sum(off[3:]))
            R['pairs'][pn + '|' + s] = P
            # --- compare with claims
            k = (pn, s)
            if k in C.T2:
                for col, cl in zip(C.T2_COLS, C.T2[k]):
                    mine = {'d1': P['d1'], 'pct': P['pct'], 'd2': P['d2'], 'urban': P['URBAN'], 'O701': P['O701'], 'A4': P['A4'],
                            'outa': P['outa'], 'outb': P['outb'], 'u1098': P['u1098'], 'u1099': P['u1099']}[col]
                    cmp('T2|%s|%s|%s' % (pn, s, col), mine, cl, 0.006 if col == 'pct' else 0.06)
            if k in C.RF1_CODEX:
                cmp('RF1codex|%s|%s' % (pn, s), P['d1_codex8100'], C.RF1_CODEX[k], 0.06)
            if k in C.T3:
                for col, cl in zip(C.T3_COLS, C.T3[k]):
                    if col in ZONES:
                        cmp('T3|%s|%s|%s' % (pn, s, col), P['zone_900_end'][col], cl, 0.06)
                    elif col == 'cell59':
                        cmp('T3|%s|%s|cell59' % (pn, s), P['cell59_center_900_end'], cl, 0.06)
                    elif col == 'resid':
                        cmp('T3|%s|%s|resid' % (pn, s), P['resid_d1_minus_cell59'], cl, 0.11)
                    elif col == 'Tgain_a':
                        cmp('T3|%s|%s|Tgain_a' % (pn, s), P['Tgain_a_start'], cl, 0)
                    elif col == 'Thalf':
                        cmp('T3|%s|%s|Thalf' % (pn, s), P['Thalf_start'], cl, 0)
            if k in C.T4_MERGE:
                for w, (dv, lv) in zip(('1800', '2700'), C.T4_MERGE[k]):
                    cmp('T4|%s|%s|merge10639_%s' % (pn, s, w), P['merge_w900_vph']['10639'][w], dv, 0.5)
                    cmp('T4|%s|%s|merge10639_arm_%s' % (pn, s, w), P['merge_arm_w900_vph']['10639'][w], lv, 0.5)
            if k in C.T4_STOCK:
                cmp('T4|%s|%s|stock4_900_end' % (pn, s), P['stock4_900_end'], C.T4_STOCK[k][0], 0.11)
                cmp('T4|%s|%s|stock10639_900_end' % (pn, s), P['stock10639_900_end'], C.T4_STOCK[k][1], 0.06)
            for (p2, s2, col), vals in C.T5.items():
                if (p2, s2) != k:
                    continue
                for w, cl in zip(C.W6, vals):
                    if col == 'merge10639':
                        mine = P['merge_w900_vph']['10639'][str(w)]; tol = 0.5
                    elif col == 'stock4':
                        mine = P['stock4_w900'][str(w)]; tol = 0.06
                    elif col == 'd1':
                        mine = P['d1_w900'][str(w)]; tol = 0.06
                    else:
                        mine = P['zone_w900'][col][str(w)]; tol = 0.06
                    cmp('T5|%s|%s|%s|%d' % (pn, s, col, w), mine, cl, tol)
            if k in C.EXTRA['RF8_off10643']:
                cmp('RF8|%s|%s|off10643_900_end' % (pn, s), P['off10643_900_end'], C.EXTRA['RF8_off10643'][k], 0.06)
            if pn == 'P-BVA':
                cmp('M3|%s|B1+B2' % s, P['zone_900_end']['B1'] + P['zone_900_end']['B2'], C.EXTRA['M3_BVA_B1B2'][s], 0.06)
            if pn == 'P-B' and s == 's43':
                cmp('M4|B_s43|merge10639_5400', P['merge_w900_vph']['10639']['5400'], C.EXTRA['M4_B_s43_merge10639_5400'], 0.5)
                cmp('M4|B_s43|merge10639_7200', P['merge_w900_vph']['10639']['7200'], C.EXTRA['M4_B_s43_merge10639_7200'], 0.5)
    # levels
    for (arm, s), (o, cx) in C.T1_LEVEL.items():
        t = {'NC': ('cxnc' if s == 's29' else 'nc'), 'VA': 'va', 'B': 'b'}[arm] + '_' + s
        if t in D:
            cmp('T1|%s|%s|L1_ours' % (arm, s), R['runs'][t]['L1_ours_9000'], o, 0.06)
            if cx is not None:
                cmp('T1|%s|%s|L1_codex' % (arm, s), R['runs'][t]['L1_codex_8100'], cx, 0.06)
    for s in ('s31', 's41', 's43'):
        lv = C.NC_MERGE_LEVEL[s]
        pv = R['pairs'].get('P-B|' + s)
        if isinstance(pv, dict):
            cmp('RF5|NC_%s|merge10639_1800' % s, pv['merge_base_w900_vph']['10639']['1800'], lv[0], 0.5)
            cmp('RF5|NC_%s|merge10639_2700' % s, pv['merge_base_w900_vph']['10639']['2700'], lv[1], 0.5)
    qj = R['pairs'].get('Q-joint|s29')
    if isinstance(qj, dict):
        lv = [qj['merge_arm_w900_vph']['10639'][str(w)] for w in (900, 1800, 2700, 3600)]
        R['checks']['M10_cxj_10639_level_900_4500'] = lv
        R['checks']['M10_cxj_10639_diff_900_4500'] = [qj['merge_w900_vph']['10639'][str(w)] for w in (900, 1800, 2700, 3600)]
        cmp('M10|cxj|10639_level_min', min(lv), C.EXTRA['M10_cxj_10639_level_900_4500'][0], 0.5)
        cmp('M10|cxj|10639_level_max', max(lv), C.EXTRA['M10_cxj_10639_level_900_4500'][1], 0.5)
    # meters
    mp = os.path.join(VD, 'out', 'meter.json')
    if os.path.exists(mp):
        M = json.load(open(mp, encoding='utf-8'))
        R['meter_sha256'] = sha(mp)
        for tag, (cnt, mg) in C.T4_METER.items():
            run = M['runs'][tag]
            src = 'ldp' if tag == 'CXJ_s29' else 'readback'
            for c, cc, gg in zip(C.METER_ORDER, cnt, mg):
                mm = run['meters'][c][src]
                cmp('T4|%s|%s|n_tight10(%s)' % (tag, c, src), mm['n_tight10'], cc, 0)
                cmp('T4|%s|%s|mean_green(%s)' % (tag, c, src), mm['mean_green'], gg, 0.006)
                pref = tag.split('_')[0]
                if pref in C.T_TIGHT:
                    cmp('M1|%s|%s|T_tight10' % (tag, c), mm['T_tight10'], C.T_TIGHT[pref][0], 0)
                    cmp('M1|%s|%s|T_tight6' % (tag, c), mm['T_tight6'], C.T_TIGHT[pref][1], 0)
    R['n_cmp'] = len(R['cmp']); R['n_fail'] = sum(1 for c in R['cmp'] if not c['ok'])
    out = os.path.join(VD, 'out', 'VERIFY_NUMBERS.json')
    json.dump(R, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('DONE cmp', R['n_cmp'], 'fail', R['n_fail'])
    for c in R['cmp']:
        if not c['ok']:
            print('FAIL', c['key'], 'mine', c['mine'], 'claim', c['claim'], 'diff', c['diff'])


if __name__ == '__main__':
    main()
