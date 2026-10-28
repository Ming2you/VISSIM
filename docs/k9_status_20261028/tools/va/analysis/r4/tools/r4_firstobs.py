r"""V-A r4 step 2 (D-K9-87): recount 4b (per input and total), 4 and Omega outside (a) of the r3 report with the
first-observation difference, compare every affected r3 cell (va_metrics.json) and apply the r3 label rule unchanged.
python -B r4_firstobs.py [--preflight]
  --preflight: load and check every input's structure only (no 4b value is computed or printed).
Sources (read-only):
  * stage-1 scan.json of the 9 runs (sha256 must equal r3 va_metrics.json per_run scan_sha256; J1/NC3 also the sha16 of
    amendment 34 sec.8.1).  Per input k: insertions[k].first_seen_times = first FZP frame of each vehicle attributed
    to k by the stage-1 rule (direct link or upstream trace) - the same attribution as the r3 per-input rows.
  * r3 va_metrics.json: d(3), d(4a), removals, NC3 levels (pct denominators), bins_delta, unins_by_input.
  * AV/r4/out/fzp_first_<tag>.json (r4_fzp_first.py): independent totals (check C4).
  * work/vhr/scan_out/first_<tag>.json: reproduction of the verified [0, 9000] values (check C5).
  * handoff omega_membership_exact.json (Omega701 links, reference rows only).
Definitions (COMPARE_RULE_R4.md): window [5.1, 8995.1], 0.5 s midpoint grid, 150 s bins; d4b_k(a - b) = S_b,k - S_a,k;
4b = all inputs (no union); other = all inputs except 1098, 1099; d4 = d4a(r3) + d4b(r4); OUT_a = d4 - d3(r3); stats =
va_common.stats with the r3 NC3 levels of the pair's r3 union; labels = va_common.label.
Writes AV/r4/out/r4_firstobs.json, r4_cells.csv, r4_tables.json.  Exit 2 = a STOP check failed (nothing published)."""
import csv
import io
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r4_common as RC  # noqa: E402
import numpy as np  # noqa: E402

V = RC.V
f = RC.f
SN = {'31': 'v3c3-s31', '41': 'v3c3-s41', '43': 'v3c3-s43', 'mean': '3시드 평균'}
PN = {'A': '짝 A d(V-A − NC3)', 'B': '짝 B d(V-A − J1)', 'Bp': '짝 B′ d(J1 − NC3)', 'J1R': 'J1R d(J1 − NC3)'}
RN = {'M4b': '④b 미삽입', 'M4': '④ 전체 + 미삽입', 'OUT_a': 'Ω 밖 (a) ④ − ③', 'unins_1098': '④b 중 입력 1098',
      'unins_1099': '④b 중 입력 1099', 'unins_other': '④b 중 그 밖 입력', 'M3': '③ Ω (635링크)'}
STOPS = []


def stop(msg):
    STOPS.append(msg)
    print('STOP', msg)


def load(preflight):
    M = RC.jload(RC.VA_METRICS)
    scans, info = {}, {}
    for tag in RC.TAGS:
        pr = M['per_run']['U9|' + tag]
        p = os.path.join(pr['scan_dir'], 'scan.json')
        h = V.sha(p)
        info[tag] = {'scan': p, 'sha256': h, 'r3_sha256': pr['scan_sha256']}
        if h != pr['scan_sha256']:
            stop('C1 scan sha %s' % tag)
        if not tag.startswith('va_') and h[:16] != V.J1_SCAN_SHA16[tag][0]:
            stop('C1 sha16 %s' % tag)
        sc = RC.jload(p)
        fr = sc['frames']
        ia = sc['insertion_attribution']
        nfs = sum(len(v['first_seen_times']) for v in sc['insertions'].values())
        c2 = {'first_sec': fr['first_sec'], 'last_sec': fr['last_sec'], 'n': fr['n'], 'irregular': fr['irregular_steps'],
              'n_bins': sc['n_bins'], 'bin_sec': sc['bin_sec'], 'ambiguous': ia.get('ambiguous', 0),
              'unattributed': ia.get('unattributed', 0), 'attributed_sum': nfs, 'vehicles_seen': sc['vehicles_seen'],
              'inputs': len(sc['insertions']), 'fzp_bytes': sc.get('fzp_bytes'),
              'min_first_seen': min(min(v['first_seen_times']) for v in sc['insertions'].values() if v['first_seen_times']),
              'max_first_seen': max(max(v['first_seen_times']) for v in sc['insertions'].values() if v['first_seen_times'])}
        info[tag]['C2'] = c2
        if not (abs(fr['first_sec'] - RC.T0) < 1e-9 and abs(fr['last_sec'] - RC.T1) < 1e-9 and fr['n'] == 1799
                and fr['irregular_steps'] == 0 and sc['n_bins'] == RC.NB and sc['bin_sec'] == RC.BIN
                and c2['ambiguous'] == 0 and c2['unattributed'] == 0 and nfs == sc['vehicles_seen']
                and c2['min_first_seen'] >= RC.T0 - 1e-9 and c2['max_first_seen'] <= RC.T1 + 1e-9):
            stop('C2 structure %s %s' % (tag, c2))
        scans[tag] = sc
    keys = [sorted(scans[t]['insertions'], key=int) for t in RC.TAGS]
    if any(k != keys[0] for k in keys):
        stop('C2 input sets differ between runs')
    for pk in RC.PAIRS:
        P = M['pairs'][pk]
        for k in ('M3', 'M4a', 'M4', 'M4b', 'OUT_a', 'REM', 'REM_B', 'unins_1098', 'unins_1099', 'unins_other'):
            if k not in P['summary'] or any(str(s) not in P['deltas'] for s in RC.SEEDS):
                stop('C2 va_metrics keys %s %s' % (pk, k))
        for k in ('M3', 'M4', 'M4b', 'OUT_a'):
            if any(len(P['bins_delta'][k][s]) != RC.NB for s in ('31', '41', '43', 'mean')):
                stop('C2 bins_delta %s %s' % (pk, k))
    fz = {}
    for tag in RC.TAGS:
        p = os.path.join(RC.OUT, 'fzp_first_%s.json' % tag)
        if not os.path.isfile(p):
            if not preflight:
                stop('C4 missing %s' % p)
            continue
        fz[tag] = RC.jload(p)
    vh = {}
    for tag in RC.TAGS:
        p = os.path.join(RC.VHR_SCAN, 'first_%s.json' % tag)
        vh[tag] = {'path': p, 'sha256': V.sha(p), 'data': RC.jload(p)}
    o701 = RC.jload(RC.O701_FILE)
    return M, scans, info, fz, vh, o701


def per_input(scans):
    S, c3 = {}, {}
    for tag, sc in scans.items():
        S[tag] = {}
        worst = 0.0
        for k, v in sc['insertions'].items():
            b = RC.grid_bins(v['first_seen_times'])
            cf = RC.closed_form(v['first_seen_times'])
            worst = max(worst, abs(float(b.sum()) - cf))
            S[tag][k] = b
        c3[tag] = worst
        if worst > 1e-5:
            stop('C3 grid vs closed form %s %.3g' % (tag, worst))
    return S, c3


def vhr_sint(d, W):
    tot = 0.0
    for c, dd in d['by_cat'].items():
        for tt, k in dd.items():
            t = int(tt) / 10
            if t <= W:
                tot += k * (W - t)
    return tot / 3600


def main():
    preflight = '--preflight' in sys.argv
    prio = V.set_below_normal()
    M, scans, info, fz, vh, o701 = load(preflight)
    if preflight:
        print('PREFLIGHT', 'stops=%d' % len(STOPS), {t: info[t]['C2']['inputs'] for t in RC.TAGS},
              'fzp_first files=%d' % len(fz), 'vhr files=%d' % len(vh), 'o701 links=%d' % len(o701['inside_links']))
        sys.exit(2 if STOPS else 0)
    if STOPS:
        RC.jdump({'STOPS': STOPS, 'stage': 'load', 'inputs_info': info}, os.path.join(RC.OUT, 'r4_firstobs_STOPPED.json'))
        print('STOPPED at load', len(STOPS))
        sys.exit(2)
    S, c3 = per_input(scans)
    inputs = sorted(S[RC.TAGS[0]], key=int)
    res = {'schema': 'k92-va-r4-firstobs/v1', 'doc': __doc__, 'priority': hex(prio),
           'script_sha256': V.sha(os.path.abspath(__file__)), 'r4_common_sha256': V.sha(RC.__file__),
           'va_common_sha256': V.sha(V.__file__), 'va_metrics_sha256': V.sha(RC.VA_METRICS),
           'va_report_r3_sha256_now': V.sha(RC.VA_REPORT), 'inputs_info': info, 'C3_max_abs_grid_minus_closed': c3,
           'n_inputs': len(inputs)}
    if res['va_report_r3_sha256_now'] != RC.VA_REPORT_SHA:
        stop('r3 report bytes changed')
    # ---------------- pair differences
    new, bins4b, perk = {}, {}, {}
    for pk, (a, b0, u) in RC.PAIRS.items():
        new[pk], bins4b[pk], perk[pk] = {}, {}, {}
        U = set(M['unions'][u])
        for s in RC.SEEDS:
            ta, tb = '%s_s%d' % (a, s), '%s_s%d' % (b0, s)
            d = {k: S[tb][k] - S[ta][k] for k in inputs}
            tot = sum(d[k] for k in inputs)
            r3d = M['pairs'][pk]['deltas'][str(s)]
            m4b = float(tot.sum())
            m4 = r3d['M4a'] + m4b
            row = {'M4b': m4b, 'M4': m4, 'OUT_a': m4 - r3d['M3'], 'unins_1098': float(d['1098'].sum()),
                   'unins_1099': float(d['1099'].sum()),
                   'unins_other': float(sum(d[k].sum() for k in inputs if k not in ('1098', '1099'))),
                   'M4b_r3union': float(sum(d[k].sum() for k in inputs if k in U)),
                   'unins_other_r3union': float(sum(d[k].sum() for k in inputs if k in U and k not in ('1098', '1099'))),
                   'M3': r3d['M3'], 'M4a': r3d['M4a'], 'REM': r3d['REM'], 'REM_B': r3d['REM_B']}
            new[pk][str(s)] = row
            bins4b[pk][str(s)] = tot
            perk[pk][str(s)] = {k: float(d[k].sum()) for k in inputs}
    res['new_deltas'] = new
    res['per_input_new'] = perk
    # ---------------- statistics and labels (r3 rule, unchanged code)
    summ, labels, labels_r3chk = {}, {}, {}
    for pk in RC.PAIRS:
        P = M['pairs'][pk]
        summ[pk] = {}
        for k in RC.ROWS + ('M4b_r3union', 'unins_other_r3union'):
            base_row = k.replace('_r3union', '') if k.endswith('_r3union') else k
            ncs = [P['summary'][base_row]['nc'][str(s)] for s in RC.SEEDS]
            st = V.stats([new[pk][str(s)][k] for s in RC.SEEDS], ncs)
            st['per_seed'] = {str(s): new[pk][str(s)][k] for s in RC.SEEDS}
            summ[pk][k] = st
        labels[pk] = {str(s): V.label(new[pk][str(s)]) for s in RC.SEEDS}
        mean_dd = {k: summ[pk][k]['mean'] for k in ('M4', 'OUT_a', 'M4b')}
        mean_dd.update({k: P['summary'][k]['mean'] for k in ('M3', 'REM', 'REM_B')})
        labels[pk]['mean'] = V.label(mean_dd)
        labels_r3chk[pk] = {str(s): V.label(P['deltas'][str(s)]) for s in RC.SEEDS}
        labels_r3chk[pk]['mean'] = V.label({k: P['summary'][k]['mean'] for k in ('M3', 'M4', 'OUT_a', 'M4b', 'REM', 'REM_B')})
        if pk in ('A', 'B') and labels_r3chk[pk] != P['labels']:
            stop('r3 labels not reproduced %s' % pk)
    res['summary_new'] = summ
    res['labels_new'] = labels
    res['labels_r3_recomputed'] = labels_r3chk
    # ---------------- checks C4 (fresh FZP), C5 (vhr reproduction), C7, C8
    c4 = {'runs': {}, 'pairs': {}}
    for tag in RC.TAGS:
        z = fz[tag]
        sc = scans[tag]
        cf_stage1 = sum(RC.closed_form(v['first_seen_times']) for v in sc['insertions'].values())
        h = z['hist_by_first_link_t10']
        n74 = sum(h.get('74', {}).values())
        n26 = sum(h.get('26', {}).values())
        c4['runs'][tag] = {'vehicles_fzp': z['vehicles'], 'vehicles_stage1': sc['vehicles_seen'],
                           'frames': z['frames'], 'first': z['first_frame_sec'], 'last': z['last_frame_sec'],
                           'irregular': z['irregular_steps'], 'skipped_0p10_rows': z['skipped_0p10_rows'],
                           'fzp_bytes_equal_scan': z['fzp_bytes'] == sc.get('fzp_bytes'),
                           'closed_form_fzp': z['closed_form_window_veh_h'], 'closed_form_stage1': cf_stage1,
                           'first_link_74': n74, 'stage1_input_1098': len(sc['insertions']['1098']['first_seen_times']),
                           'first_link_26': n26, 'stage1_input_1099': len(sc['insertions']['1099']['first_seen_times'])}
        r = c4['runs'][tag]
        if not (r['vehicles_fzp'] == r['vehicles_stage1'] and r['frames'] == 1799 and abs(r['first'] - RC.T0) < 1e-9
                and abs(r['last'] - RC.T1) < 1e-9 and r['irregular'] == 0 and r['fzp_bytes_equal_scan']
                and abs(r['closed_form_fzp'] - r['closed_form_stage1']) <= 1e-4):
            stop('C4 run %s %s' % (tag, r))
    for pk, (a, b0, u) in RC.PAIRS.items():
        for s in RC.SEEDS:
            ta, tb = '%s_s%d' % (a, s), '%s_s%d' % (b0, s)
            dz = fz[tb]['closed_form_window_veh_h'] - fz[ta]['closed_form_window_veh_h']
            c4['pairs']['%s|%d' % (pk, s)] = {'fzp': dz, 'stage1': new[pk][str(s)]['M4b'], 'diff': dz - new[pk][str(s)]['M4b']}
            if abs(dz - new[pk][str(s)]['M4b']) > 0.01:
                stop('C4 pair %s %d %.4f' % (pk, s, dz - new[pk][str(s)]['M4b']))
    res['C4'] = c4
    c5 = {}
    for (a, b0, s), want in RC.VHR_EXPECT_0_9000.items():
        got = vhr_sint(vh['%s_s%d' % (b0, s)]['data'], 9000) - vhr_sint(vh['%s_s%d' % (a, s)]['data'], 9000)
        c5['%s-%s|%d' % (a, b0, s)] = {'got': got, 'want': want, 'ok': abs(got - want) <= 0.050001}
        if not c5['%s-%s|%d' % (a, b0, s)]['ok']:
            stop('C5 vhr reproduction %s-%s %d got %.3f want %.1f' % (a, b0, s, got, want))
    res['C5'] = {'cells': c5, 'vhr_files': {t: {'path': vh[t]['path'], 'sha256': vh[t]['sha256']} for t in RC.TAGS},
                 'window_effect_r4_minus_0_9000': {'%s|%d' % (pk, s): new[pk][str(s)]['M4b'] - (
                     vhr_sint(vh['%s_s%d' % (RC.PAIRS[pk][1], s)]['data'], 9000) - vhr_sint(vh['%s_s%d' % (RC.PAIRS[pk][0], s)]['data'], 9000))
                     for pk in RC.PAIRS for s in RC.SEEDS}}
    c7, c8 = {}, {}
    newbins = {}
    for pk in RC.PAIRS:
        bd = M['pairs'][pk]['bins_delta']
        newbins[pk] = {}
        for s in ('31', '41', '43'):
            m4a = np.asarray(bd['M4'][s]) - np.asarray(bd['M4b'][s])
            c7['%s|%s' % (pk, s)] = float(m4a.sum() - M['pairs'][pk]['deltas'][s]['M4a'])
            if abs(c7['%s|%s' % (pk, s)]) > 0.01:
                stop('C7 %s %s' % (pk, s))
            m4 = m4a + bins4b[pk][s]
            newbins[pk][s] = {'M4b': bins4b[pk][s], 'M4': m4, 'OUT_a': m4 - np.asarray(bd['M3'][s])}
            c8['%s|%s' % (pk, s)] = float(np.abs(bins4b[pk][s][:int(V.T_ACT // RC.BIN)]).max())
        newbins[pk]['mean'] = {k: np.mean([newbins[pk][s][k] for s in ('31', '41', '43')], axis=0) for k in ('M4b', 'M4', 'OUT_a')}
    res['C7_m4a_bins_sum_minus_r3'] = c7
    res['C8_pre900_max_abs_d4b'] = c8
    res['bins_new'] = {pk: {s: {k: [round(float(x), 6) for x in v] for k, v in d.items()} for s, d in nb_.items()}
                       for pk, nb_ in newbins.items()}
    # ---------------- Omega701 reference rows (not r3 cells, no label)
    o701_links = {str(x) for x in o701['inside_links']}
    om = {}
    for tag in RC.TAGS:
        lv = scans[tag]['link_vh']
        om[tag] = {'O701': float(sum(sum(v) for lk, v in lv.items() if lk in o701_links)),
                   'all_links': float(sum(sum(v) for v in lv.values())), 'all_ttt': scans[tag]['totals']['all_ttt_veh_h']}
        if abs(om[tag]['all_links'] - om[tag]['all_ttt']) > 0.05:
            stop('O701 link_vh sum vs all_ttt %s' % tag)
    o7 = {}
    for pk, (a, b0, u) in RC.PAIRS.items():
        o7[pk] = {}
        for s in RC.SEEDS:
            dO = om['%s_s%d' % (a, s)]['O701'] - om['%s_s%d' % (b0, s)]['O701']
            o7[pk][str(s)] = {'d_O701': dO, 'OUT_a_O701_r4': new[pk][str(s)]['M4'] - dO,
                              'OUT_a_O701_r3method': M['pairs'][pk]['deltas'][str(s)]['M4'] - dO}
    res['omega701_reference'] = {'file': RC.O701_FILE, 'sha256': V.sha(RC.O701_FILE), 'n_links': len(o701_links),
                                 'per_run': om, 'pairs': o7}
    # ---------------- 1083 share and r3-implied per-input d
    ui = M['unins_by_input']
    r3k = {}
    for pk, (a, b0, u) in RC.PAIRS.items():
        r3k[pk] = {}
        for s in RC.SEEDS:
            r3k[pk][str(s)] = {}
            for k in ui[u]:
                va, vb = ui[u][k].get('%s_s%d' % (a, s)), ui[u][k].get('%s_s%d' % (b0, s))
                r3k[pk][str(s)][k] = (va['veh_h_nc_anchor'] - vb['veh_h_nc_anchor']) if (va and vb) else None
    res['per_input_r3_implied'] = r3k
    # consistency: r3 1098/1099 rows equal the r3-implied per-input d
    cons = {}
    for pk in RC.PAIRS:
        for s in RC.SEEDS:
            for k, row in (('1098', 'unins_1098'), ('1099', 'unins_1099')):
                cons['%s|%d|%s' % (pk, s, k)] = r3k[pk][str(s)][k] - M['pairs'][pk]['deltas'][str(s)][row]
    res['r3_per_input_consistency'] = cons
    if STOPS:
        res['STOPS'] = STOPS
        RC.jdump(res, os.path.join(RC.OUT, 'r4_firstobs_STOPPED.json'))
        print('STOPPED', len(STOPS))
        sys.exit(2)
    # ---------------- cell comparison
    cells = []

    def add(loc, pk, row, col, r3v, r4v, nd=1, sign=True, txt=None):
        if txt is not None:
            r3t, r4t = txt
            cells.append(dict(loc=loc, pair=pk, row=row, col=col, r3_raw=None, r4_raw=None, r3=r3t, r4=r4t,
                              changed=r3t != r4t, sign_changed=False))
            return
        r3t, r4t = f(r3v, nd, sign), f(r4v, nd, sign)
        sc_ = (r3v is not None and r4v is not None and RC.sgn(r3v) != RC.sgn(r4v))
        cells.append(dict(loc=loc, pair=pk, row=row, col=col, r3_raw=r3v, r4_raw=r4v, r3=r3t, r4=r4t,
                          changed=r3t != r4t, sign_changed=bool(sc_)))
    for pk in RC.PAIRS:
        P = M['pairs'][pk]
        for k in RC.ROWS:
            for s in ('31', '41', '43'):
                add('§3.1 d', pk, k, s, P['summary'][k]['per_seed'][s], summ[pk][k]['per_seed'][s])
        if pk == 'Bp':
            continue
        for k in RC.ROWS:
            o, n = P['summary'][k], summ[pk][k]
            for s in ('31', '41', '43'):
                add('§3.2 요약', pk, k, 'd ' + s, o['per_seed'][s], n['per_seed'][s])
            add('§3.2 요약', pk, k, '평균 d', o['mean'], n['mean'])
            add('§3.2 요약', pk, k, 'sd', o['sd'], n['sd'], 1, False)
            add('§3.2 요약', pk, k, 'CI 아래', o['ci90'][0], n['ci90'][0])
            add('§3.2 요약', pk, k, 'CI 위', o['ci90'][1], n['ci90'][1])
            add('§3.2 요약', pk, k, '음/양', None, None, txt=('%d/%d' % (o['neg'], o['pos']), '%d/%d' % (n['neg'], n['pos'])))
            add('§3.2 요약', pk, k, '평균/NC %', o['pct_of_nc'], n['pct_of_nc'], 2)
            for i, s in enumerate(('31', '41', '43')):
                add('§3.2 요약', pk, k, '시드별 d/NC % ' + s, o['per_seed_pct'][i], n['per_seed_pct'][i])
            add('§3.2 요약', pk, k, 'CI 표시', None, None, txt=('관측된 차이' if o['ci_excludes_0'] else '0 포함',
                                                              '관측된 차이' if n['ci_excludes_0'] else '0 포함'))
    for pk in ('A', 'B'):
        P = M['pairs'][pk]
        for s in ('31', '41', '43', 'mean'):
            for rk in ('N', 'W_A', 'W_B'):
                add('§3.3 표시', pk, 'label ' + rk, s, None, None, txt=(P['labels'][s][rk], labels[pk][s][rk]))
            for k in ('M4', 'OUT_a', 'M4b'):
                o = P['summary'][k]['mean'] if s == 'mean' else P['deltas'][s][k]
                n = summ[pk][k]['mean'] if s == 'mean' else new[pk][s][k]
                add('§3.3 표시', pk, k, s, o, n)
        # sec.4.1 "(같은 표)" rows: d per seed, mean, CI, CI text, sign counts (same numbers as sec.3.2)
        for k in ('M4', 'OUT_a', 'M4b'):
            o, n = P['summary'][k], summ[pk][k]
            for s in ('31', '41', '43'):
                add('§4.1 같은 표', pk, k, 'd ' + s, o['per_seed'][s], n['per_seed'][s])
            add('§4.1 같은 표', pk, k, '평균 d', o['mean'], n['mean'])
            add('§4.1 같은 표', pk, k, 'CI 아래', o['ci90'][0], n['ci90'][0])
            add('§4.1 같은 표', pk, k, 'CI 위', o['ci90'][1], n['ci90'][1])
            add('§4.1 같은 표', pk, k, 'CI 표시', None, None, txt=('관측된 차이' if o['ci_excludes_0'] else '',
                                                                '관측된 차이' if n['ci_excludes_0'] else ''))
            add('§4.1 같은 표', pk, k, '음/양', None, None, txt=('%d/%d' % (o['neg'], o['pos']), '%d/%d' % (n['neg'], n['pos'])))
        # sec.11 cumulative (4 and Omega outside (a)) at the r3 checkpoints
        bd = P['bins_delta']
        for k in ('M4', 'OUT_a'):
            for s in ('31', '41', '43', 'mean'):
                for c in RC.CPS:
                    o = sum(bd[k][s][:c // 150])
                    n = float(np.sum(newbins[pk][s][k][:c // 150]))
                    add('§11 누적', pk, k, '%s @%d' % (s, c), o, n)
        # sec.5 1083 share
        u = RC.PAIRS[pk][2]
        for s in ('31', '41', '43'):
            o = r3k[pk][s].get('1083')
            add('§5 1083 몫', pk, 'unins_1083', s, 0.0 if o is None else o, perk[pk][s]['1083'])
    # CI-excluding-0 row counts of the 15-row summary tables
    cnt = {}
    for pk in ('A', 'B', 'J1R'):
        P = M['pairs'][pk]
        r3n = sum(1 for k, _ in M['metrics'] if P['summary'][k]['ci_excludes_0'])
        r4n = sum(1 for k, _ in M['metrics'] if (summ[pk][k]['ci_excludes_0'] if k in RC.ROWS else P['summary'][k]['ci_excludes_0']))
        cnt[pk] = {'r3': r3n, 'r4': r4n, 'rows_r4': [k for k, _ in M['metrics'] if (summ[pk][k]['ci_excludes_0'] if k in RC.ROWS
                                                                                    else P['summary'][k]['ci_excludes_0'])]}
    res['ci_excl0_row_counts'] = cnt
    res['cells'] = cells
    res['cells_count'] = {'total': len(cells), 'changed': sum(1 for c in cells if c['changed']),
                          'sign_changed': sum(1 for c in cells if c['sign_changed'])}
    byloc = {}
    for c in cells:
        q = byloc.setdefault('%s|%s' % (c['loc'], c['pair']), {'total': 0, 'changed': 0, 'sign_changed': 0})
        q['total'] += 1
        q['changed'] += int(c['changed'])
        q['sign_changed'] += int(c['sign_changed'])
    res['cells_count_by_loc_pair'] = byloc
    res['sign_changed_cells'] = [c for c in cells if c['sign_changed']]
    res['text_changed_cells'] = [c for c in cells if c['r3_raw'] is None and c['changed']]
    # J1R labels (reference only; J1_REPORT is a separate document)
    res['labels_J1R_reference'] = {'r3_method': labels_r3chk['J1R'], 'r4': labels['J1R']}
    RC.jdump(res, os.path.join(RC.OUT, 'r4_firstobs.json'))
    with io.open(os.path.join(RC.OUT, 'r4_cells.csv'), 'w', newline='', encoding='utf-8') as h:
        w = csv.writer(h)
        w.writerow(['loc', 'pair', 'row', 'col', 'r3', 'r4', 'changed', 'sign_changed', 'r3_raw', 'r4_raw'])
        for c in cells:
            w.writerow([c['loc'], c['pair'], c['row'], c['col'], c['r3'], c['r4'], int(c['changed']), int(c['sign_changed']),
                        '' if c['r3_raw'] is None else repr(c['r3_raw']), '' if c['r4_raw'] is None else repr(c['r4_raw'])])
    tables(M, res, new, summ, labels, newbins, perk, r3k, o7, c4, c5)
    print('DONE cells=%d changed=%d sign_changed=%d' % (len(cells), res['cells_count']['changed'], res['cells_count']['sign_changed']))


def mark(o, n, nd=1, sign=True):
    ot, nt = f(o, nd, sign), f(n, nd, sign)
    flag = ''
    if o is not None and n is not None and RC.sgn(o) != RC.sgn(n):
        flag = ' †'
    elif ot != nt:
        flag = ' *'
    return '%s → %s%s' % (ot, nt, flag)


def tables(M, res, new, summ, labels, newbins, perk, r3k, o7, c4, c5):
    T = {}
    # per-seed d, r3 -> r4
    for pk, title in (('A', 'd(V-A − NC3)'), ('B', 'd(V-A − J1)'), ('J1R', 'd(J1 − NC3) (짝 B′ [U9] = J1R [U6(J1)])')):
        P = M['pairs'][pk]
        lines = ['| 줄 (%s) | v3c3-s31 r3 → r4 | v3c3-s41 r3 → r4 | v3c3-s43 r3 → r4 |' % title, '|---|---|---|---|',
                 '| ③ Ω (635링크) (안 바뀜) | %s | %s | %s |' % tuple(f(P['deltas'][s]['M3'], 1, True) for s in ('31', '41', '43')),
                 '| ④a 전체 링크 (안 바뀜) | %s | %s | %s |' % tuple(f(P['deltas'][s]['M4a'], 1, True) for s in ('31', '41', '43'))]
        for k in RC.ROWS:
            lines.append('| %s | %s |' % (RN[k], ' | '.join(mark(P['summary'][k]['per_seed'][s], summ[pk][k]['per_seed'][s])
                                                         for s in ('31', '41', '43'))))
        lines.append('| (참고) ④b 를 r3 합집합 입력만 셈 | %s |' % ' | '.join(
            '%s → %s' % (f(P['summary']['M4b']['per_seed'][s], 1, True), f(new[pk][s]['M4b_r3union'], 1, True)) for s in ('31', '41', '43')))
        T['PERSEED_' + pk] = '\n'.join(lines)
    # 3-seed summaries
    for pk, title in (('A', 'd(V-A − NC3)'), ('B', 'd(V-A − J1)'), ('J1R', 'd(J1 − NC3)')):
        P = M['pairs'][pk]
        lines = ['| 줄 (%s) | 판 | d s31 | d s41 | d s43 | 평균 d | sd | 90 %% CI | 음/양 | 평균/NC %% | 시드별 d/NC %% | CI 표시 |' % title,
                 '|---|---|---:|---:|---:|---:|---:|---|---|---:|---|---|']
        st3 = P['summary']['M3']
        lines.append('| ③ Ω (635링크) (안 바뀜) | r3 = r4 | %s | %s | %s | %s | %s | [%s, %s] | %d/%d | %s | %s | %s |' % (
            f(st3['per_seed']['31'], 1, True), f(st3['per_seed']['41'], 1, True), f(st3['per_seed']['43'], 1, True),
            f(st3['mean'], 1, True), f(st3['sd'], 1), f(st3['ci90'][0], 1, True), f(st3['ci90'][1], 1, True), st3['neg'], st3['pos'],
            f(st3['pct_of_nc'], 2, True), ' / '.join(f(x, 1, True) for x in st3['per_seed_pct']),
            '관측된 차이' if st3['ci_excludes_0'] else '0 포함'))
        for k in RC.ROWS:
            for tag, st in (('r3', P['summary'][k]), ('**r4**', summ[pk][k])):
                lines.append('| %s | %s | %s | %s | %s | %s | %s | [%s, %s] | %d/%d | %s | %s | %s |' % (
                    RN[k], tag, f(st['per_seed']['31'], 1, True), f(st['per_seed']['41'], 1, True), f(st['per_seed']['43'], 1, True),
                    f(st['mean'], 1, True), f(st['sd'], 1), f(st['ci90'][0], 1, True), f(st['ci90'][1], 1, True), st['neg'], st['pos'],
                    f(st['pct_of_nc'], 2, True), ' / '.join(f(x, 1, True) for x in st['per_seed_pct']),
                    '관측된 차이' if st['ci_excludes_0'] else '0 포함'))
        T['SUMMARY_' + pk] = '\n'.join(lines)
    # labels
    for pk in ('A', 'B', 'J1R'):
        P = M['pairs'][pk]
        lab_old = P['labels'] if pk in ('A', 'B') else res['labels_r3_recomputed']['J1R']
        lines = ['| 대상 | d(③) | d(④) r3 → r4 | d(④ − ③) r3 → r4 | d(④b) r3 → r4 | d(제거 A) | d(제거 B) | 읽는 법 N r3 → r4 | W (제거 A) r3 → r4 | W (제거 B) r3 → r4 |',
                 '|---|---:|---|---|---|---:|---:|---|---|---|']
        for s in ('31', '41', '43', 'mean'):
            if s == 'mean':
                o = {k: P['summary'][k]['mean'] for k in ('M3', 'M4', 'OUT_a', 'M4b', 'REM', 'REM_B')}
                n = {k: summ[pk][k]['mean'] for k in ('M4', 'OUT_a', 'M4b')}
            else:
                o = P['deltas'][s]
                n = new[pk][s]
            lo, ln = lab_old[s], labels[pk][s]
            lines.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                SN[s], f(o['M3'], 1, True), mark(o['M4'], n['M4']), mark(o['OUT_a'], n['OUT_a']), mark(o['M4b'], n['M4b']),
                f(o['REM'], 1, True), f(o['REM_B'], 1, True),
                *[(lo[r] if lo[r] == ln[r] else '%s → **%s**' % (lo[r], ln[r])) for r in ('N', 'W_A', 'W_B')]))
        T['LABELS_' + pk] = '\n'.join(lines)
    # cumulative
    for pk in ('A', 'B'):
        bd = M['pairs'][pk]['bins_delta']
        lines = ['| 줄 | 시드 | %s |' % ' | '.join('누적 d ~%d s r3 → r4' % c for c in RC.CPS), '|---|---|' + '---|' * len(RC.CPS)]
        for k, nm in (('M3', '③ Ω (안 바뀜)'), ('M4', '④'), ('OUT_a', 'Ω 밖 (a)')):
            for s in ('31', '41', '43', 'mean'):
                if k == 'M3':
                    cells_ = [f(sum(bd[k][s][:c // 150]), 1, True) for c in RC.CPS]
                else:
                    cells_ = [mark(sum(bd[k][s][:c // 150]), float(np.sum(newbins[pk][s][k][:c // 150]))) for c in RC.CPS]
                lines.append('| %s | %s | %s |' % (nm, SN[s], ' | '.join(cells_)))
        T['CUM_' + pk] = '\n'.join(lines)
    # per input
    inputs = sorted(perk['A']['31'], key=int)
    show = [k for k in inputs if any(abs(perk[pk][s][k]) >= 0.05 for pk in ('A', 'B', 'J1R') for s in ('31', '41', '43'))
            or any(r3k[pk][s].get(k) for pk in ('A', 'B', 'J1R') for s in ('31', '41', '43'))]
    lines = ['| 입력 | 짝 A d(V-A − NC3) r3 → r4 (s31 / s41 / s43) | 짝 B d(V-A − J1) r3 → r4 | J1R d(J1 − NC3) r3 → r4 |', '|---|---|---|---|']
    for k in show:
        cells_ = []
        for pk in ('A', 'B', 'J1R'):
            cells_.append(' / '.join('%s → %s' % ('밖' if r3k[pk][s].get(k) is None else f(r3k[pk][s][k], 1, True),
                                                   f(perk[pk][s][k], 1, True)) for s in ('31', '41', '43')))
        lines.append('| %s | %s |' % (k, ' | '.join(cells_)))
    rest = [k for k in inputs if k not in show]
    lines.append('| 나머지 %d입력 합 | %s |' % (len(rest), ' | '.join(' / '.join(f(sum(perk[pk][s][k] for k in rest), 2, True)
                                                                          for s in ('31', '41', '43')) for pk in ('A', 'B', 'J1R'))))
    T['PER_INPUT'] = '\n'.join(lines)
    res['per_input_shown'] = show
    # Omega701 reference
    lines = ['| 짝 | 시드 | d(Ω701) | d(④) r4 | Ω 밖 (a) Ω701 기준: r3 방법 → r4 | Ω 밖 (a) Ω635 기준 (§3) r3 → r4 |', '|---|---|---:|---:|---|---|']
    for pk in ('A', 'B', 'J1R'):
        for s in ('31', '41', '43'):
            q = o7[pk][s]
            lines.append('| %s | %s | %s | %s | %s | %s |' % (PN[pk], SN[s], f(q['d_O701'], 1, True), f(new[pk][s]['M4'], 1, True),
                                                       mark(q['OUT_a_O701_r3method'], q['OUT_a_O701_r4']),
                                                       mark(M['pairs'][pk]['deltas'][s]['OUT_a'], new[pk][s]['OUT_a'])))
    T['O701_REF'] = '\n'.join(lines)
    # checks
    lines = ['| 짝 | 시드 | d④b stage-1 첫 관측 (주 값) | d④b 새 FZP 스캔 | 차 | [0, 9000] 꼴 vhr 값 (VERIFY §2.2) | 창 효과 (주 값 − [0, 9000]) |',
             '|---|---|---:|---:|---:|---:|---:|']
    for pk in ('A', 'B', 'J1R'):
        a, b0, _ = RC.PAIRS[pk]
        for s in RC.SEEDS:
            q = c4['pairs']['%s|%d' % (pk, s)]
            v = c5['%s-%s|%d' % (a, b0, s)]
            lines.append('| %s | %s | %s | %s | %s | %s | %s |' % (PN[pk], SN[str(s)], f(q['stage1'], 3, True), f(q['fzp'], 3, True),
                                                                f(q['diff'], 4, True), f(v['got'], 2, True),
                                                                f(res['C5']['window_effect_r4_minus_0_9000']['%s|%d' % (pk, s)], 2, True)))
    T['CHECKS'] = '\n'.join(lines)
    RC.jdump(T, os.path.join(RC.OUT, 'r4_tables.json'))
    RC.jdump(res, os.path.join(RC.OUT, 'r4_firstobs.json'))


if __name__ == '__main__':
    main()
