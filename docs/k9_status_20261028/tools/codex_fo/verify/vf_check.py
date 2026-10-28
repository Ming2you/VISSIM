# vf_check.py - VERIFY_FO: compare FO_REPORT.json / FO_REPORT.md values with the verifier's own outputs (2026-10-28 KST).
# Written after reading FO_REPORT (needs its key names). The verifier numbers come only from vf_scan / vf_runfiles /
# vf_pairs / vf_extra outputs. Read only.
# usage: python -B vf_check.py <verify_out_dir> <FO_REPORT.json> <FO_REPORT.md> <out_json>
import sys, os, json, re

ROWMAP = {
    'Ω701 (codex 목적 영역 701링크)': 'O701', 'Ω635 (우리 목적 영역 635링크)': 'O635',
    'Ω701 − Ω635 (더한 66링크)': 'O701mO635', '④a 망 전체 링크': 'A4a', '④b 미삽입 (첫 관측 차분)': 'U',
    '④ = ④a + ④b': 'A4', 'Ω 밖 (a) Ω701 기준 = ④ − Ω701': 'outa701', 'Ω 밖 (a) Ω635 기준 = ④ − Ω635': 'outa635',
    'Ω 밖 (b) Ω701 기준 = ④a − Ω701': 'outb701', 'Ω 밖 (b) Ω635 기준 = ④a − Ω635': 'outb635',
    '① FW_E 본선 7링크': 'FWE7', '② 동측 국소 19링크': 'LOC19', '④b 중 입력 1098 (FW_E 입구)': 'u1098',
    '④b 중 입력 1099 (FW_W 입구, 감시)': 'u1099', '④b 중 도시 입력': 'ucity', '링크 66 (SC1004 남측)': 'L66',
    '도시도로 (codex 분할, O)': 'URB', '도시도로 codex 규칙 M (codex 꼴만, X2 대조)': 'URB',
    '감시: FW_W 본선 (O FW_W_main)': 'FWW3'}
FORMS = {'ours_9000': 'ours', 'codex_8100': 'codex'}
SEEDS = ['31', '41', '43']
ZONES = {'U': (0, 4200), 'B1': (4200, 5300), 'M': (5300, 6800), 'B2': (6800, 7900), 'D': (7900, 10800)}
FWE_METERS = {'10639': ('RM_C10639', '70'), '10681': ('RM_C10681', '68'), '10490': ('RM_C10490', '129'), '10484': ('RM_C10484', '31')}


def jl(p):
    with open(p, encoding='utf-8-sig') as fh:
        return json.load(fh)


def num(cell):
    c = cell.replace('*', '').replace('−', '-').replace('±', '').replace('†', '').strip()
    try:
        return float(c)
    except ValueError:
        return None


def main():
    vo, rep_json, rep_md, out = sys.argv[1:5]
    P = jl(os.path.join(vo, 'pairs.json'))
    RF = jl(os.path.join(vo, 'runfiles.json'))
    EX = jl(os.path.join(vo, 'extra.json'))
    SC = {k: jl(os.path.join(vo, 'scan_%s.json' % k)) for k in [a + s for a in ('fo', 'b', 'nc', 'va') for s in SEEDS]}
    J = jl(rep_json)
    res = {'cmp': [], 'fails': []}

    def cmp(name, mine, theirs, tol):
        if mine is None or theirs is None:
            ok = (mine is None and theirs is None)
            dev = None
        else:
            dev = abs(float(mine) - float(theirs))
            ok = dev <= tol
        rec = [name, mine, theirs, dev, tol, ok]
        res['cmp'].append(rec)
        if not ok:
            res['fails'].append(rec)

    # 1. T1/T2 rows (JSON, unrounded)
    for form_j, form_m in FORMS.items():
        for label, key in ROWMAP.items():
            rows = J['tables']['rows'][form_j].get(label)
            if rows is None:
                continue
            for s in SEEDS:
                cell = rows.get('s' + s, {})
                for pj, pm in (('FO-NC3', 'FO-NC3'), ('B-FO', 'B-FO'), ('FO-VA', 'FO-VA'), ('B-NC3_calc', 'B-NC3')):
                    v = cell.get(pj)
                    if isinstance(v, (int, float)):
                        cmp('T|%s|%s|%s|s%s' % (form_m, key, pj, s), P['pairs']['%s|%s|%s' % (pm, form_m, s)][key], v, 0.05)
    # 2. T1/T2 tables in the markdown (rounded)
    md = open(rep_md, encoding='utf-8').read().splitlines()
    sect = None
    pair_cols = [('FO-NC3', s) for s in SEEDS] + [('B-FO', s) for s in SEEDS] + [('FO-VA', s) for s in SEEDS]
    n_md = 0
    for line in md:
        if line.startswith('#### T1'):
            sect = 'ours'
            continue
        if line.startswith('#### T2'):
            sect = 'codex'
            continue
        if line.startswith('## ') or line.startswith('- [계산] 세 시드'):
            sect = None
        if sect and line.startswith('| ') and not line.startswith('| 줄') and not line.startswith('|---'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            label = cells[0]
            if label not in ROWMAP:
                continue
            for (pm, s), c in zip(pair_cols, cells[1:]):
                v = num(c)
                if v is None:
                    continue
                n_md += 1
                cmp('MD|%s|%s|%s|s%s' % (sect, ROWMAP[label], pm, s), P['pairs']['%s|%s|%s' % (pm, sect, s)][ROWMAP[label]], v, 0.06)
    res['n_md_cells'] = n_md
    # 3. entry E/W (codex form level sums of the onramp connectors of the codex partition)
    for s in SEEDS:
        for side, key in (('onramps_E', 'ONR_E'), ('onramps_W', 'ONR_W')):
            e = J['entry_EW']['seeds']['s' + s][side]
            cmp('EW|%s|FO_level|s%s' % (side, s), P['levels']['fo' + s]['codex'][key], e['FO_joint'], 0.05)
            cmp('EW|%s|NC3_level|s%s' % (side, s), P['levels']['nc' + s]['codex'][key], e['FO_nc'], 0.05)
            cmp('EW|%s|B_level|s%s' % (side, s), P['levels']['b' + s]['codex'][key], e['B_joint'], 0.05)
            cmp('EW|%s|FO-NC3|s%s' % (side, s), P['pairs']['FO-NC3|codex|' + s][key], e['FO-NC3'], 0.05)
            cmp('EW|%s|B-FO|s%s' % (side, s), P['pairs']['B-FO|codex|' + s][key], e['B-FO'], 0.05)
    # 4. FW_E cells
    PM = {'X-NC3': ('fo', 'nc', 'FO-NC3'), 'B-X': ('b', 'fo', 'B-FO'), 'X-VA': ('fo', 'va', 'FO-VA')}
    for s in SEEDS:
        F = J['fwe']['seeds']['v3c3-s' + s]
        for pj, (x, y, pm) in PM.items():
            pr = F['pairs'][pj]
            for form_j, form_m in FORMS.items():
                cmp('RF1|%s|%s|s%s' % (pj, form_m, s), P['pairs']['%s|%s|%s' % (pm, form_m, s)]['FWE7'], pr['RF1'][form_j], 0.051)
                cmp('RF2|%s|%s|s%s' % (pj, form_m, s), P['pairs']['%s|%s|%s' % (pm, form_m, s)]['LOC19'], pr['RF2'][form_j], 0.051)
            cmp('RF7|%s|s%s' % (pj, s), P['pairs']['%s|ours|%s' % (pm, s)]['u1098'], pr['RF7']['total'], 0.051)
            # RF3 zones per 900 s window, both chain conventions
            for conv in ('cum', 'geom'):
                for z, (a, b) in ZONES.items():
                    for w in range(1, 10):
                        def zsum(run):
                            return sum(c for ww, bb, c in SC[run]['fwe_cells_' + conv] if ww == w and a <= 100 * bb < b) * 5.0 / 3600.0
                        mine = zsum(x + s) - zsum(y + s)
                        cmp('RF3|%s|%s|%s|w%d|s%s' % (conv, pj, z, w, s), mine, pr['RF3'][z]['bins900'][w], 0.051 if conv == 'cum' else 9e9)
            # RF8 exit connectors: link-level, bin form 900-end and ours form
            for lk, v in pr['RF8'].items():
                bx = SC[x + s]['links_bin900'].get(lk, [0.0] * 10)
                by = SC[y + s]['links_bin900'].get(lk, [0.0] * 10)
                cmp('RF8_bin900end|%s|%s|s%s' % (pj, lk, s), (sum(bx[1:]) - sum(by[1:])) * 5.0 / 3600.0, v, 0.051)
                cmp('RF8_ours|%s|%s|s%s' % (pj, lk, s), SC[x + s]['links_ours'].get(lk, 0.0) - SC[y + s]['links_ours'].get(lk, 0.0), v, 9e9)
            # RF6 meter side: connector + approach link, bin form 900-end (candidate definition)
            if pr.get('RF6_stock_d'):
                for m, v in pr['RF6_stock_d'].items():
                    conn, appr = m, FWE_METERS[m][1]
                    def st(run):
                        b9 = SC[run]['links_bin900']
                        return sum(sum(b9.get(k, [0.0] * 10)[1:]) for k in (conn, appr)) * 5.0 / 3600.0
                    cmp('RF6cand_bin900end|%s|%s|s%s' % (pj, m, s), st(x + s) - st(y + s), v, 9e9)
            # DA1
            for conv in ('cum', 'geom'):
                d = P['fwe']['%s|%s|%s' % (pm, conv, s)]
                da = F['DA']['DA1'][pj]
                cmp('DA1_cell59_900end|%s|%s|s%s' % (conv, pj, s), d['cell59_900end'], da['cells5_9_900_end'], 0.02 if conv == 'cum' else 9e9)
                for w in range(1, 10):
                    cmp('DA1_cell59_w%d|%s|%s|s%s' % (w, conv, pj, s), d['cell59'][w], da['cells5_9_per_900s'][w], 0.02 if conv == 'cum' else 9e9)
                cmp('DA1_d1_900end_bin|%s|%s|s%s' % (conv, pj, s), d['fwe7_bin_900end'], da['d1_900_end'], 9e9)
            cmp('DA1_d1_900end_vs_ours_total|%s|s%s' % (pj, s), P['pairs']['%s|ours|%s' % (pm, s)]['FWE7'], F['DA']['DA1'][pj]['d1_900_end'], 0.05)
        # RF4 arms (FW_E meters), FO from runfiles + extra, B from extra
        for arm, src in (('X', 'FO'), ('B', 'B')):
            for m, (mid, _) in FWE_METERS.items():
                a = F['arms'][arm]['RF4'][m]
                mine = EX['%s%s' % (src, s)]['meter_readback'][mid]
                cmp('RF4|%s|%s|n_tight10|s%s' % (src, m, s), mine['n_green_lt10'], a['n_tight10'], 0)
                cmp('RF4|%s|%s|T_tight10|s%s' % (src, m, s), mine['T_tight10'], a['T_tight10'], 0)
                cmp('RF4|%s|%s|T_tight6|s%s' % (src, m, s), mine['T_tight6'], a['T_tight6'], 0)
                cmp('RF4|%s|%s|mean_green|s%s' % (src, m, s), mine['mean_green'], a['mean_green'], 0.006)
                hist_t = {k: v for k, v in a['green_hist'].items() if v}
                cmp('RF4|%s|%s|hist_equal|s%s' % (src, m, s), 1.0 if hist_t == mine['hist'] else 0.0, 1.0, 0)
        # FO readback checks: runfiles vs extra agree, and vs report runcheck
        rc = J['runcheck']['seeds']['s' + s]
        R = RF['seeds'][s]
        cmp('V3_meter_rows|s%s' % s, R['readback_rows'].get('meter|immediate', 0) + R['readback_rows'].get('meter|post_step', 0), rc['V3_meter_rows'], 0)
        cmp('V3_bad|s%s' % s, sum(v for k, v in R['readback_bad'].items() if k.startswith('meter')), rc['V3_bad'], 0)
        for mid, mm in rc['V3_per_meter'].items():
            mine = R['meters'][mid]
            cmp('V3|%s|mismatch|s%s' % (mid, s), mine['mismatch_n'], mm['mismatch'], 0)
            cmp('V3|%s|lt10|s%s' % (mid, s), mine['n_green_lt10'], mm['cycles_green_lt10'], 0)
            cmp('V3|%s|hist|s%s' % (mid, s), 1.0 if mine['green_hist'] == {k: v for k, v in mm['readback_green_hist'].items()} else 0.0, 1.0, 0)
        v4 = rc['V4']
        cmp('V4_signal_rows|s%s' % s, R['csv_signal_rows']['ge900'], v4['signal_rows_T_ge_900'], 0)
        cmp('V4_off_baseline|s%s' % s, R['csv_signal_mismatch_vs_baseline']['ge900'], v4['signal_rows_off_baseline'], 0)
        cmp('V4_sg_schedules_one|s%s' % s, 1 if R['csv_signal_sg']['all_equal'] else 2, v4['signal_sg_distinct_schedules'], 0)
        cmp('V4_written_sg|s%s' % s, R['urban_written_sg'], rc['V4_written_sg']['written_sg'], 0)
        cmp('V4_written_frames_shift1|s%s' % s, R['urban_readback_vs_native']['1']['frames'], rc['V4_written_sg']['differing_frames_total'], 0)
        cmp('V4_unwritten_n|s%s' % s, R['unwritten_sg']['n'], v4['d_not_written_sg_in_lsa'], 0)
        cmp('V4_unwritten_diff|s%s' % s, R['unwritten_sg']['sg_with_diff'], v4['d_not_written_sg_with_difference'], 0)
        cmp('V4_urban_rb_rows|s%s' % s, R['readback_rows'].get('urban17|immediate', 0) + R['readback_rows'].get('urban17|post_step', 0), v4['e_urban_readback_rows'], 0)
        cmp('V4_urban_rb_bad|s%s' % s, sum(v for k, v in R['readback_bad'].items() if k.startswith('urban17')), v4['e_urban_readback_bad'], 0)
        cmp('V5_vsl_rows|s%s' % s, R['csv_vsl_rows'], J['runcheck']['seeds']['s' + s]['V5']['action_vsl_values'].get('110.0'), 0)
        cmp('V5_vsl_not110|s%s' % s, R['csv_vsl_not110_n'], 0, 0)
        cmp('V5_readback_rows|s%s' % s, sum(R['vsl_readback']['rows'].values()), rc['V5']['vsl_readback_rows'], 0)
        cmp('V5_readback_bad|s%s' % s, R['vsl_readback']['bad'], rc['V5']['vsl_readback_not_110_or_not_ok'], 0)
        # X5
        x5 = J['X5']['seeds']['s' + s]
        cmp('X5_first_FO|s%s' % s, SC['fo' + s]['first_seen']['9000']['n_all'], x5['first_seen_FO'], 0)
        cmp('X5_first_NC3|s%s' % s, SC['nc' + s]['first_seen']['9000']['n_all'], x5['first_seen_NC3'], 0)
        cmp('X5_first_B|s%s' % s, SC['b' + s]['first_seen']['9000']['n_all'], x5['first_seen_B_read'], 0)
        cmp('X5_err_FO|s%s' % s, 1.0 if EX['FO' + s]['err_remain'] == x5['err_remain_FO'] else 0.0, 1.0, 0)
        cmp('X5_err_NC3|s%s' % s, 1.0 if EX['NC3' + s]['err_remain'] == x5['err_remain_NC3_read'] else 0.0, 1.0, 0)
        cmp('X5_err_B|s%s' % s, 1.0 if EX['B' + s]['err_remain'] == x5['err_remain_B_read'] else 0.0, 1.0, 0)
        # walltimes
        wt = J['walltimes']['seeds']['s' + s]
        mw = EX['FO' + s]['wall_ge900']
        cmp('wall_n|s%s' % s, mw['n'], wt['n_decisions_ge900'], 0)
        for k in ('mean', 'median', 'max', 'min'):
            cmp('wall_%s|s%s' % (k, s), mw[k], wt['wall'][k], 0.051)
        cmp('wall_gt360|s%s' % s, mw['n_gt360'], wt['wall']['gt360'], 0)
        cmp('wall_gt1800|s%s' % s, mw['n_gt1800'], wt['wall']['gt1800'], 0)
        # meter commands (54 decisions)
        for arm in ('FO', 'B'):
            mc = J['meter_commands']['runs'].get('%s_s%s' % (arm, s))
            if mc is None:
                continue
            for mid, mm in mc['meters'].items():
                mine = EX['%s%s' % (arm, s)]['meter_cmd_54'][mid]
                for k in ('n', 'n_green10', 'n_green2', 'min', 'max'):
                    cmp('MC|%s|%s|%s|s%s' % (arm, mid, k, s), mine[k], mm[k], 0)
        # NC3 level of (1) and pct
        cmp('NC3_FWE7_level|s%s' % s, P['levels']['nc' + s]['ours']['FWE7'],
            {'31': 1816.6, '41': 1963.8, '43': 1876.5}[s], 0.051)
        cmp('pct_FO-NC3|s%s' % s, 100.0 * P['pairs']['FO-NC3|ours|' + s]['FWE7'] / P['levels']['nc' + s]['ours']['FWE7'],
            J['fwe']['seeds']['v3c3-s' + s]['pct_FO-NC3_d1_of_NC3_level_calc'], 0.006)
    # ratios quoted in the text
    for s, (r1, r1c, r2o, rrest) in {'31': (0.88, 0.89, 0.90, 0.87), '41': (1.06, 1.06, 0.84, 1.09), '43': (0.86, 0.85, 0.88, 0.85)}.items():
        pr = P['pairs']
        cmp('ratio_d1_ours|s%s' % s, pr['FO-NC3|ours|' + s]['FWE7'] / pr['B-NC3|ours|' + s]['FWE7'], r1, 0.0051)
        cmp('ratio_d1_codex|s%s' % s, pr['FO-NC3|codex|' + s]['FWE7'] / pr['B-NC3|codex|' + s]['FWE7'], r1c, 0.0051)
        cmp('ratio_d2_ours|s%s' % s, pr['FO-NC3|ours|' + s]['LOC19'] / pr['B-NC3|ours|' + s]['LOC19'], r2o, 0.0051)
        for conv in ('cum', 'geom'):
            f = P['fwe']['FO-NC3|%s|%s' % (conv, s)]
            b = P['fwe']['B-NC3|%s|%s' % (conv, s)]
            mine = (pr['FO-NC3|ours|' + s]['FWE7'] - f['cell59_900end']) / (pr['B-NC3|ours|' + s]['FWE7'] - b['cell59_900end'])
            cmp('ratio_rest_%s|s%s' % (conv, s), mine, rrest, 0.0051 if conv == 'cum' else 9e9)
    for s in SEEDS:
        cmp('VA_meter_nongreen|s%s' % s, EX['VA' + s]['non_green_rows'], 0, 0)
    res['n_cmp'] = len(res['cmp'])
    res['n_fail'] = len(res['fails'])
    tmp = out + '.tmp' + str(os.getpid())
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=0)
    os.replace(tmp, out)
    print('VF_CHECK n_cmp', res['n_cmp'], 'n_fail', res['n_fail'], 'n_md_cells', n_md, flush=True)


if __name__ == '__main__':
    main()
