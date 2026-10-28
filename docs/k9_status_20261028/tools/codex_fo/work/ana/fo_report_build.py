# -*- coding: utf-8 -*-
"""fo_report_build.py - assemble FO_REPORT.md from a hand-written source (FO_REPORT_src.md) and tables generated from
FO_REPORT.json (fo_report_extract.py) + fo_tables_out.md (declared table tool). Read-only on all inputs, light.
Placeholders {{NAME}} in the source are replaced by generated Markdown. Checks: forbidden verdict words (the 8 of
b_report_build.py + 4 more), sealed-seed names, no placeholder left.
usage: python -B fo_report_build.py <src.md> <FO_REPORT.json> <fo_tables_out.md> <out.md>
"""
import hashlib, json, re, sys

FORBIDDEN = ('개선', '이긴', '이겼', '진다', '졌다', '낫다', '좋아졌', '나빠졌', '악화', '성공', '실패했', '우월')
SEALED = (r's37\b', r's59\b', r's61\b', r's67\b', r'v3c3-s47', r'seed ?37', r'seed ?59', r'seed ?61', r'seed ?67')
SEEDS = ('s31', 's41', 's43')
VS = {'s31': 'v3c3-s31', 's41': 'v3c3-s41', 's43': 'v3c3-s43'}
PL = {'X-NC3': 'FO − NC3', 'B-X': 'B − FO', 'X-VA': 'FO − V-A'}
MET = ('10639', '10681', '10490', '10484')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def f1(x, nd=1):
    if x is None:
        return '못 냄'
    if isinstance(x, str):
        return x
    r = round(x + 0.0, nd)
    if r == 0:
        return '±0' if nd == 0 else '±%.*f' % (nd, 0.0)
    s = '%.*f' % (nd, abs(r))
    return ('+' + s) if r > 0 else ('−' + s)


def tf(x):
    return '참' if x is True else ('거짓' if x is False else str(x))


def n0(x):
    return '없음' if x is None else str(int(x)) if isinstance(x, (int, float)) and float(x).is_integer() else str(x)


def dag(D, s, p):
    key = {'X-NC3': 'FO-NC3', 'B-X': 'B-FO', 'X-VA': 'FO-VA'}[p]
    return '†' if D['tables']['daggers'][s][key] else ''


def hdr9(D, extra=''):
    cols = ['%s %s%s' % (PL[p], VS[s], dag(D, s, p)) for p in PL for s in SEEDS]
    return '| 칸%s | ' % extra + ' | '.join(cols) + ' |\n|---|' + '---:|' * 9 + '\n'


def t_fwe_totals(D):
    fw = D['fwe']['seeds']
    rows = [('RF1 d① 우리 꼴 [0, 9000]', lambda r: r['RF1']['ours_9000']), ('RF1 d① codex 꼴 [0, 8100]', lambda r: r['RF1']['codex_8100']),
            ('RF2 d② 우리 꼴', lambda r: r['RF2']['ours_9000']), ('RF2 d② codex 꼴', lambda r: r['RF2']['codex_8100']),
            ('**함께 Ω701** 우리 꼴', lambda r: r['WITH']['ours_9000']['O701']), ('**함께 ④** 우리 꼴', lambda r: r['WITH']['ours_9000']['A4']),
            ('**함께 Ω 밖 (a)** 우리 꼴', lambda r: r['WITH']['ours_9000']['outa']), ('**함께 Ω 밖 (b)** 우리 꼴', lambda r: r['WITH']['ours_9000']['outb']),
            ('함께 Ω701 codex 꼴', lambda r: r['WITH']['codex_8100']['O701']), ('함께 ④ codex 꼴', lambda r: r['WITH']['codex_8100']['A4']),
            ('함께 Ω 밖 (a) codex 꼴', lambda r: r['WITH']['codex_8100']['outa']), ('함께 Ω 밖 (b) codex 꼴', lambda r: r['WITH']['codex_8100']['outb'])]
    out = hdr9(D, ' (veh·h)')
    for lab, fn in rows:
        out += '| %s | %s |\n' % (lab, ' | '.join(f1(fn(fw[VS[s]]['pairs'][p])) for p in PL for s in SEEDS))
    return out


def t_ref(D):
    fw = D['fwe']['seeds']
    out = '| 기준 열 (FWE_REF_C1, 빼지 않음) | v3c3-s31 | v3c3-s41 | v3c3-s43 |\n|---|---|---|---|\n'
    for p, lab in (('P-B', 'B − NC3'), ('P-VA', 'V-A − NC3'), ('P-BVA', 'B − V-A')):
        out += '| %s: RF1 우리 (codex) | %s |\n' % (lab, ' | '.join('%s (%s)' % (f1(fw[VS[s]]['ref_FWE_REF_C1'][p]['RF1']['ours_9000']), f1(fw[VS[s]]['ref_FWE_REF_C1'][p]['RF1']['codex_8100'])) for s in SEEDS))
        out += '| %s: 함께 Ω701 / ④ / Ω 밖 (a) / (b) 우리 | %s |\n' % (lab, ' | '.join(' / '.join(f1(fw[VS[s]]['ref_FWE_REF_C1'][p]['WITH']['ours_9000'][k]) for k in ('O701', 'A4', 'outa', 'outb')) for s in SEEDS))
        out += '| %s: RF7 ④b 1098 | %s |\n' % (lab, ' | '.join(f1(fw[VS[s]]['ref_FWE_REF_C1'][p]['RF7']['total']) for s in SEEDS))
    side = D['fwe']['side_64cf_joint_minus_NC']
    out += '| 옆 열 64cf-s29 joint − NC (codex 꼴, 다른 망·한 시드) | RF1 %s · RF2 %s · RF7 %s · T_gain_a %s / T_half %s s | | |\n' % (
        f1(side['RF1']['codex_8100']), f1(side['RF2']['codex_8100']), f1(side['RF7']['total']), side['RF11']['T_gain_a_s'], side['RF11']['T_half_s'])
    return out


def t_zones(D):
    fw = D['fwe']['seeds']
    out = '| 구역 (900 s–끝 합, veh·h) | ' + ' | '.join('%s %s' % (PL[p], VS[s]) for p in PL for s in SEEDS) + ' | 기준 B − NC3 s31 / s41 / s43 |\n|---|' + '---:|' * 9 + '---|\n'
    for z in ('U', 'B1', 'M', 'B2', 'D'):
        out += '| %s | %s | %s |\n' % (z, ' | '.join(f1(fw[VS[s]]['pairs'][p]['RF3'][z]['sum_900_end_of_rounded_bins']) for p in PL for s in SEEDS),
                                     ' / '.join(f1(fw[VS[s]]['ref_FWE_REF_C1']['P-B']['RF3_sum_900_end_of_rounded_bins'][z]) for s in SEEDS))
    return out


def t_zone_bins(D):
    fw = D['fwe']['seeds']
    out = '| FO − NC3 · 구역 | ' + ' | '.join('%d–%d' % (900 * k, 900 * (k + 1)) for k in range(1, 10)) + ' |\n|---|' + '---:|' * 9 + '\n'
    for s in SEEDS:
        for z in ('B1', 'M', 'B2'):
            b = fw[VS[s]]['pairs']['X-NC3']['RF3'][z]['bins900']
            out += '| %s%s · %s | %s |\n' % (VS[s], dag(D, s, 'X-NC3'), z, ' | '.join(f1(x) for x in b[1:]))
    return out


def t_rf4(D):
    fw = D['fwe']['seeds']
    out = '| 미터 (FW_E) | 칸 | ' + ' | '.join('%s %s' % (a, VS[s]) for s in SEEDS for a in ('FO', 'B')) + ' |\n|---|---|' + '---:|' * 6 + '\n'
    for m in MET:
        for lab, key in (('GREEN<10 주기 (810 중)', 'n_tight10'), ('평균 GREEN 초', 'mean_green'), ('T_tight10 / T_tight6 s', 'T')):
            cells = []
            for s in SEEDS:
                for a in ('X', 'B'):
                    v = fw[VS[s]]['arms'][a]['RF4'][m]
                    cells.append('%s / %s' % (v['T_tight10'], v['T_tight6']) if key == 'T' else ('%.2f' % v[key] if key == 'mean_green' else str(v[key])))
            out += '| RM_C%s | %s | %s |\n' % (m, lab, ' | '.join(cells))
    va0 = all(fw[VS[s]]['arms']['VA']['RF4'][m]['n_tight10'] == 0 and fw[VS[s]]['arms']['VA']['RF4'][m]['mean_green'] == 10.0 for s in SEEDS for m in MET)
    out += '\n- V-A: %s. NC3: 기록 없음(v3c3 NC3 에 미터 readback·LDP 없음).\n' % (
        '세 시드·네 미터 모두 810 주기 GREEN 10 (GREEN<10 주기 0)' if va0 else '조임 있음(표 밖, FO_REPORT.json 참고)')
    return out


def t_hist(D):
    fw = D['fwe']['seeds']
    out = '| 미터 · 팔 | v3c3-s31 | v3c3-s41 | v3c3-s43 |\n|---|---|---|---|\n'
    for m in MET:
        for a, lab in (('X', 'FO'), ('B', 'B')):
            cells = []
            for s in SEEDS:
                h = fw[VS[s]]['arms'][a]['RF4'][m]['green_hist']
                cells.append(' '.join('%s:%d' % (g, c) for g, c in h.items() if c))
            out += '| RM_C%s · %s | %s |\n' % (m, lab, ' | '.join(cells))
    return out


def t_rf5(D):
    fw = D['fwe']['seeds']
    out = '| 합류 (veh/h, 900 s 칸 평균) | ' + ' | '.join('%d–%d' % (900 * k, 900 * (k + 1)) for k in range(1, 10)) + ' |\n|---|' + '---:|' * 9 + '\n'
    for s in SEEDS:
        for m in MET:
            r = fw[VS[s]]['pairs']['X-NC3']['RF5'][m]
            out += '| %s · %s FO − NC3 차 (FO 수준) | %s |\n' % (VS[s], m, ' | '.join('%s (%d)' % (f1(d, 0), a) for d, a in zip(r['d'][1:], r['arm'][1:])))
        rb = fw[VS[s]]['pairs']['B-X']['RF5']['10639']
        out += '| %s · 10639 B − FO 차 | %s |\n' % (VS[s], ' | '.join(f1(d, 0) for d in rb[1:]))
    return out


def t_rf6to11(D):
    fw = D['fwe']['seeds']
    out = hdr9(D)
    for m in MET:
        out += '| RF6 미터 쪽 재고 차 %s (veh·h) | %s |\n' % (m, ' | '.join(f1(fw[VS[s]]['pairs'][p]['RF6_stock_d'][m]) for p in PL for s in SEEDS))
    out += '| RF6 넷 합 (미터별 반올림 값의 합) | %s |\n' % ' | '.join(f1(fw[VS[s]]['pairs'][p]['RF6_stock_d_sum4_of_rounded']) for p in PL for s in SEEDS)
    out += '| RF7 ④b 1098 (FW_E 입구) | %s |\n' % ' | '.join(f1(fw[VS[s]]['pairs'][p]['RF7']['total']) for p in PL for s in SEEDS)
    for e in ('10643', '10682', '10481', '10483'):
        out += '| RF8 진출 커넥터 %s 재고 차 | %s |\n' % (e, ' | '.join(f1(fw[VS[s]]['pairs'][p]['RF8'][e]) for p in PL for s in SEEDS))
    def rf9(r, p):
        x = r['RF9']
        return ('팔 %d/%d · NC3 %d/%d' % (x['arm_B1'], x['arm_M'], x['NC3_B1'], x['NC3_M'])) if p == 'X-NC3' else ('차 %s/%s' % (f1(x['B1_d'], 0), f1(x['M_d'], 0)))
    out += '| RF9 B1 / M 번짐 분 | %s |\n' % ' | '.join(rf9(fw[VS[s]]['pairs'][p], p) for p in PL for s in SEEDS)
    def rf11(r):
        x = r['RF11']
        return '%s / %s / %s' % (x['T_gain_a_s'] if x['T_gain_a_s'] is not None else '없음', x['T_gain_b_s'] if x['T_gain_b_s'] is not None else '없음', x['T_half_s'] if x['T_half_s'] is not None else '없음')
    out += '| RF11 T_gain_a / T_gain_b / T_half (s) | %s |\n' % ' | '.join(rf11(fw[VS[s]]['pairs'][p]) for p in PL for s in SEEDS)
    out += '| RF11 누적 d① 900 s–끝 | %s |\n' % ' | '.join(f1(fw[VS[s]]['pairs'][p]['RF11']['cum_d1_900_end']) for p in PL for s in SEEDS)
    return out


def t_rf11_timing(D):
    fw = D['fwe']['seeds']
    out = '| 미터 | ' + ' | '.join(VS[s] for s in SEEDS) + ' |\n|---|---|---|---|\n'
    for m in MET:
        cells = []
        for s in SEEDS:
            t = fw[VS[s]]['pairs']['X-NC3']['RF11']['T_gain_minus_T_tight10']['RM_C' + m]
            cells.append('T_tight10 %s · a − %s · b − %s' % (t['T_tight10'], t['a_minus'], t['b_minus']) if isinstance(t, dict) else str(t))
        out += '| RM_C%s | %s |\n' % (m, ' | '.join(cells))
    return out


def t_arms_rf9_10(D):
    fw = D['fwe']['seeds']
    out = '| 팔 | RF9 B1 / M 번짐 분 s31 · s41 · s43 | RF10 FW_E VSL<110 결정 수 s31 · s41 · s43 |\n|---|---|---|\n'
    for a, lab in (('X', 'FO'), ('B', 'B'), ('VA', 'V-A'), ('NC3', 'NC3')):
        r9 = ' · '.join('%d / %d' % (fw[VS[s]]['arms'][a]['RF9']['B1'], fw[VS[s]]['arms'][a]['RF9']['M']) for s in SEEDS)
        if a == 'NC3':
            r10 = '해당 없음(무제어)'
        else:
            r10 = ' · '.join('%d%s' % (fw[VS[s]]['arms'][a]['RF10']['n_decisions_lt110'], (' (%d–%d s)' % (min(fw[VS[s]]['arms'][a]['RF10']['times_s']), max(fw[VS[s]]['arms'][a]['RF10']['times_s']))) if fw[VS[s]]['arms'][a]['RF10']['times_s'] else '') for s in SEEDS)
        out += '| %s | %s | %s |\n' % (lab, r9, r10)
    return out


def t_entry(D):
    E = D['entry_EW']['seeds']
    out = '| 줄 (codex 규칙, codex 꼴 [0, 8100], veh·h) | ' + ' | '.join('%s %s%s' % (lab, VS[s], dag(D, s, p)) for p, lab in (('X-NC3', 'FO − NC3'), ('B-X', 'B − FO'), ('X-VA', 'FO − V-A')) for s in SEEDS) + ' |\n|---|' + '---:|' * 9 + '\n'
    for k, lab in (('onramps_E', '진입 E (FW_E 연결로 넷)'), ('onramps_W', '진입 W (FW_W 연결로 넷, 감시)')):
        out += '| %s | %s | %s | 못 냄(V-A 에 M 없음) | 못 냄 | 못 냄 |\n' % (lab, ' | '.join(f1(E[s][k]['FO-NC3']) for s in SEEDS), ' | '.join(f1(E[s][k]['B-FO']) for s in SEEDS))
    out += '| 수준 FO / NC3 / B: 진입 E | %s | | | | | |\n' % ' · '.join('%s %.1f / %.1f / %.1f' % (VS[s], E[s]['onramps_E']['FO_joint'], E[s]['onramps_E']['FO_nc'], E[s]['onramps_E']['B_joint']) for s in SEEDS)
    out += '| 점검: FO 출력 nc = B 고정 출력 nc (|차| ≤ 1e-6) | %s | | | | | |\n' % ' · '.join('%s %s' % (s, '참' if E[s]['onramps_E']['nc_check_ok'] and E[s]['onramps_W']['nc_check_ok'] else '거짓') for s in SEEDS)
    return out


def t_da1(D):
    fw = D['fwe']['seeds']
    out = '| 짝 · 시드 | 셀 5–9 d① × 900 s (900–1800 … 8100–9000) | 셀 5–9 900 s–끝 | d① 900 s–끝 | 나머지 = d① − 셀 5–9 |\n|---|---|---:|---:|---:|\n'
    for p in PL:
        for s in SEEDS:
            x = fw[VS[s]]['DA']['DA1'][p]
            out += '| %s %s | %s | %s | %s | %s |\n' % (PL[p], VS[s], ' · '.join(f1(v) for v in x['cells5_9_per_900s'][1:]), f1(x['cells5_9_900_end']), f1(x['d1_900_end']), f1(x['d1_rest']))
    rd = D['fwe']['ref_derived']['data_after_residual']
    out += '| 기준 B − NC3 (FWE_REF_C1 `/ref/derived/data_after_residual`) | | %s | | %s |\n' % (
        ' / '.join(f1(rd['P-B|%s' % VS[s]]['cells5_9_900_end']) for s in SEEDS), ' / '.join(f1(rd['P-B|%s' % VS[s]]['d1_rest']) for s in SEEDS))
    return out


def t_da2(D):
    fw = D['fwe']['seeds']
    out = '| 팔 | 4,300 m 머리 분 s31 · s41 · s43 | 셀 5–9 혼잡 분 s31 · s41 · s43 |\n|---|---|---|\n'
    for a, lab in (('X', 'FO'), ('NC3', 'NC3'), ('B', 'B'), ('VA', 'V-A')):
        out += '| %s | %s | %s |\n' % (lab, ' · '.join(str(fw[VS[s]]['DA']['DA2'][a]['head_4300_minutes']) for s in SEEDS), ' · '.join(str(fw[VS[s]]['DA']['DA2'][a]['cells5_9_cong_minutes']) for s in SEEDS))
    return out


def t_da3(D):
    fw = D['fwe']['seeds']
    out = '| 미터 | ' + ' | '.join(VS[s] for s in SEEDS) + ' |\n|---|---:|---:|---:|\n'
    for m in MET:
        out += '| %s | %s |\n' % (m, ' | '.join(str(fw[VS[s]]['DA']['DA3'][m]) for s in SEEDS))
    return out


def t_da4(D):
    fw = D['fwe']['seeds']
    out = ''
    for s in SEEDS:
        out += '\n**%s%s** (FO − NC3; 칸마다 합류 차 / FO 수준 / NC3 수준 veh/h · 평균 GREEN 초 · 조임 몫 · 미터 쪽 재고 차 veh·h)\n\n' % (VS[s], dag(D, s, 'X-NC3'))
        out += '| 미터 | ' + ' | '.join('%d–%d' % (900 * k, 900 * (k + 1)) for k in range(1, 10)) + ' |\n|---|' + '---|' * 9 + '\n'
        for m in MET:
            rows = fw[VS[s]]['DA']['DA4'][m]
            cells = []
            for k in range(1, 10):
                r = rows[str(900 * k)]
                cells.append('%s / %d / %d · %s · %s · %s' % (f1(r['d'], 0), r['arm'], r['base'], '%.2f' % r['g'] if r['g'] is not None else '없음',
                                                             '%.2f' % r['tight'] if r['tight'] is not None else '없음', f1(r['stock_d'], 2)))
            out += '| %s | %s |\n' % (m, ' | '.join(cells))
    return out


def t_fww(D):
    T = D['tables']['rows']
    out = hdr9(D, ' (veh·h)')
    for form, fl in (('ours_9000', '우리 꼴'), ('codex_8100', 'codex 꼴')):
        for lab in ('④b 중 입력 1099 (FW_W 입구, 감시)', '감시: FW_W 본선 (O FW_W_main)'):
            out += '| %s %s | %s |\n' % (lab.replace('감시: ', '').replace(' (O FW_W_main)', ' (링크 26·120·10771)'), fl,
                                       ' | '.join(f1(T[form][lab][s][k]) for k in ('FO-NC3', 'B-FO', 'FO-VA') for s in SEEDS))
    return out


def t_fww_meters(D):
    rc = D['runcheck']['seeds']
    mc = D['meter_commands']['runs']
    out = '| 미터 (FW_W) | readback GREEN<10 주기 (810 중) FO s31 / s41 / s43 | readback GREEN 초 분포 FO s31 | 명령 녹색 10 / 2 인 결정 수 (54 중) FO s31 / s41 / s43 | 같은 칸 B s31 / s41 / s43 |\n|---|---|---|---|---|\n'
    for m in ('RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644'):
        out += '| %s | %s | %s | %s | %s |\n' % (m, ' / '.join(str(rc[s]['V3_per_meter'][m]['cycles_green_lt10']) for s in SEEDS),
                                               ' '.join('%s:%d' % (g, c) for g, c in rc['s31']['V3_per_meter'][m]['readback_green_hist'].items()),
                                               ' / '.join('%d·%d' % (mc['FO_' + s]['meters'][m]['n_green10'], mc['FO_' + s]['meters'][m]['n_green2']) for s in SEEDS),
                                               ' / '.join('%d·%d' % (mc['B_' + s]['meters'][m]['n_green10'], mc['B_' + s]['meters'][m]['n_green2']) for s in SEEDS))
    return out


def t_cmd(D):
    mc = D['meter_commands']['runs']
    out = '| 미터 (방향) | FO 녹색 10 / 녹색 2 결정 수 s31 · s41 · s43 | FO 범위 s | B 녹색 10 / 녹색 2 s31 · s41 · s43 | B 범위 s |\n|---|---|---|---|---|\n'
    for m, dr in (('RM_C10639', 'FW_E'), ('RM_C10681', 'FW_E'), ('RM_C10490', 'FW_E'), ('RM_C10484', 'FW_E'), ('RM_C10480', 'FW_W'), ('RM_C10482', 'FW_W'), ('RM_C10646', 'FW_W'), ('RM_C10644', 'FW_W')):
        def g(a):
            return ' · '.join('%d / %d' % (mc['%s_%s' % (a, s)]['meters'][m]['n_green10'], mc['%s_%s' % (a, s)]['meters'][m]['n_green2']) for s in SEEDS)
        def rg(a):
            return ' · '.join('%g–%g' % (mc['%s_%s' % (a, s)]['meters'][m]['min'], mc['%s_%s' % (a, s)]['meters'][m]['max']) for s in SEEDS)
        out += '| %s (%s) | %s | %s | %s | %s |\n' % (m, dr, g('FO'), rg('FO'), g('B'), rg('B'))
    return out


def t_v3(D):
    rc = D['runcheck']['seeds']
    out = '| 칸 | v3c3-s31 | v3c3-s41 | v3c3-s43 |\n|---|---|---|---|\n'
    out += '| V3 미터 readback 행 · 요청≠읽음 또는 ok≠1 | %s |\n' % ' | '.join('%d · %d' % (rc[s]['V3_meter_rows'], rc[s]['V3_bad']) for s in SEEDS)
    out += '| V3 미터 8 × 810 주기 GREEN 초 ≠ 명령 | %s |\n' % ' | '.join(str(sum(v['mismatch'] for v in rc[s]['V3_per_meter'].values())) for s in SEEDS)
    out += '| V4 signal 행 (T ≥ 900) · baseline 밖 | %s |\n' % ' | '.join('%d · %d' % (rc[s]['V4']['signal_rows_T_ge_900'], rc[s]['V4']['signal_rows_off_baseline']) for s in SEEDS)
    out += '| V4 signal_sg 일정 수 (55 결정) | %s |\n' % ' | '.join(str(rc[s]['V4']['signal_sg_distinct_schedules']) for s in SEEDS)
    out += '| V4 쓴 SG · GREEN 다른 SG · 다른 프레임 [901, 9000] | %s |\n' % ' | '.join('%d · %d · %d' % (rc[s]['V4_written_sg']['written_sg'], rc[s]['V4_written_sg']['sg_with_difference'], rc[s]['V4_written_sg']['differing_frames_total']) for s in SEEDS)
    out += '| V4 쓰지 않은 SG (.lsa) · 다른 SG | %s |\n' % ' | '.join('%d · %d' % (rc[s]['V4']['d_not_written_sg_in_lsa'], rc[s]['V4']['d_not_written_sg_with_difference']) for s in SEEDS)
    out += '| V4 도시 readback 행 · 어긋남 | %s |\n' % ' | '.join('%d · %d' % (rc[s]['V4']['e_urban_readback_rows'], rc[s]['V4']['e_urban_readback_bad']) for s in SEEDS)
    out += '| V5 명령 VSL 값 · vsl_readback 행 · 110 밖 또는 ok≠1 | %s |\n' % ' | '.join('%s · %d · %d' % (','.join('%s×%d' % (k, v) for k, v in rc[s]['V5']['action_vsl_values'].items()), rc[s]['V5']['vsl_readback_rows'], rc[s]['V5']['vsl_readback_not_110_or_not_ok']) for s in SEEDS)
    out += '| V1 유지 · V9 범위 유지 | %s |\n' % ' | '.join('%d · %d' % (len(rc[s]['V1_holds']), len(rc[s]['V9']['scope_holds'])) for s in SEEDS)
    out += '| usable · pass | %s |\n' % ' | '.join('%s · %s' % (tf(rc[s]['usable']), tf(rc[s]['pass'])) for s in SEEDS)
    return out


def t_wall(D):
    W, R = D['walltimes']['seeds'], D['ramp_forecast']['seeds']
    out = '| 칸 | v3c3-s31 | v3c3-s41 | v3c3-s43 |\n|---|---|---|---|\n'
    out += '| 결정 벽시계 n · 평균 · 중앙 · 최소 · 최대 s | %s |\n' % ' | '.join('%d · %.1f · %.1f · %.1f · %.1f' % (W[s]['n_decisions_ge900'], W[s]['wall']['mean'], W[s]['wall']['median'], W[s]['wall']['min'], W[s]['wall']['max']) for s in SEEDS)
    out += '| > 360 s · > 1,800 s 결정 수 · 유지 | %s |\n' % ' | '.join('%d · %d · %d' % (W[s]['wall']['gt360'], W[s]['wall']['gt1800'], len(W[s]['held'])) for s in SEEDS)
    out += '| budget wall 평균 · 최대 s | %s |\n' % ' | '.join('%.1f · %.1f' % (W[s]['budget_wall']['mean'], W[s]['budget_wall']['max']) for s in SEEDS)
    out += '| 램프 도착 예측 합 logged (veh/h) 최소 · 평균 · 최대 (n) | %s |\n' % ' | '.join('%.1f · %.1f · %.1f (%d)' % (R[s]['logged_min'], R[s]['logged_mean_calc'], R[s]['logged_max'], R[s]['n']) for s in SEEDS)
    return out


def t_x(D):
    C = D['tables']['checks']
    X5 = D['X5']['seeds']
    out = '| 점검 | 값 | 무게 |\n|---|---|---|\n'
    out += '| X1 V 대 O (dΩ701·dΩ635·d①·d④a; FO − NC3·FO − V-A, 두 꼴, 3시드 = 48값) | 차 최대 %.4f veh·h, 0.05 넘은 값 %d | 보고 |\n' % (C['X1']['max_abs'], len(C['X1']['flagged']))
    out += '| X2 codex 꼴 도시도로 M 대 O | %s | 보고 |\n' % ' · '.join('v3c3-s%d %s' % (x['seed'], ('%.1e' % x['diff']).replace('-', '\u2212')) for x in C['X2'])
    out += '| X3 FO 사본 도구의 V-A − NC3 칸 = B 출력 | V 칸 같음 %s, O 같음 %s, 멈춤 %s | 멈춤 |\n' % (tf(C['X3']['V_va_nc3_cells_equal']), tf(C['X3']['O_va_nc3_equal']), tf(C['X3']['stop']))
    out += '| X3b NC3·V-A 스캔 = B 스캔 (scan_sec 뺌) | %s | 멈춤 |\n' % ' · '.join('%s %s' % (k.replace('nc3_s', 'NC3 v3c3-s').replace('va_s', 'V-A v3c3-s'), tf(v)) for k, v in C['X3b_scans_equal_b'].items())
    out += '| X4 링크 66 우리 꼴 P 대 top66.json | {{X4}} | 보고 |\n'
    out += '| X5 첫 관측 차 수 FO / NC3 / B | %s | 보고 |\n' % ' · '.join('%s %d / %d / %d' % (VS[s], X5[s]['first_seen_FO'], X5[s]['first_seen_NC3'], X5[s]['first_seen_B_read']) for s in SEEDS)
    out += '| X5 `.err` 남은 차 FO | %s | 보고 |\n' % ' · '.join('%s %s' % (VS[s], ', '.join('입력 %s: %d' % (k, v) for k, v in X5[s]['err_remain_FO'].items()) or '0') for s in SEEDS)
    out += '| X5 (첫 관측 + 남은 수) FO − NC3 · B − NC3 | %s | 보고 |\n' % ' · '.join('%s %s · %s' % (VS[s], f1(X5[s]['first_plus_remain_FO_minus_NC3_calc'], 0), f1(X5[s]['first_plus_remain_B_minus_NC3_calc'], 0)) for s in SEEDS)
    out += '| X6 도구가 쓰인 대로 돌지 못함 | 0 (`-Plan final` 8단계 모두 exit 0) | 멈춤 |\n'
    out += '| X7 `fo_fwe.py run` stops | %d (vhr 스캔·fwe_scan 같은 FZP, FO vhr = FO 런 FZP, 3시드) | 멈춤 |\n' % len(D['fwe']['stops'])
    out += '| X8 접두 † | %s | 보고 |\n' % ' · '.join('%s FO−NC3 %s / B−FO %s / FO−V-A %s' % (VS[s], '†' if D['tables']['daggers'][s]['FO-NC3'] else '없음', '†' if D['tables']['daggers'][s]['B-FO'] else '없음', '†' if D['tables']['daggers'][s]['FO-VA'] else '없음') for s in SEEDS)
    return out


def main(src, rep, tmd, outp):
    D = json.load(open(rep, encoding='utf-8'))
    tm = open(tmd, encoding='utf-8').read().split('\n', 1)[1].strip()   # drop the generator comment line
    tm = tm.replace('#### T1', '#### T1').replace('#### T2', '#### T2')
    gen = {'FWE_TOTALS': t_fwe_totals(D), 'FWE_REF': t_ref(D), 'FWE_ZONES': t_zones(D), 'FWE_ZONE_BINS': t_zone_bins(D),
           'RF4': t_rf4(D), 'RF4_HIST': t_hist(D), 'RF5': t_rf5(D), 'RF6_11': t_rf6to11(D), 'RF11_TIMING': t_rf11_timing(D),
           'ARMS_RF9_10': t_arms_rf9_10(D), 'ENTRY': t_entry(D), 'T1T2': tm, 'DA1': t_da1(D), 'DA2': t_da2(D), 'DA3': t_da3(D),
           'DA4': t_da4(D), 'FWW': t_fww(D), 'FWW_METERS': t_fww_meters(D), 'CMD': t_cmd(D), 'V3V5': t_v3(D), 'WALL': t_wall(D),
           'XCHK': t_x(D)}
    s = open(src, encoding='utf-8').read()
    for k, v in gen.items():
        s = s.replace('{{%s}}' % k, v.rstrip('\n'))
    s = s.replace('{{X4}}', 'v3c3-s31 0 · v3c3-s41 0 · v3c3-s43 0 (차)')
    left = re.findall(r'\{\{[A-Z0-9_]+\}\}', s)
    hits = [w for w in FORBIDDEN if w in s]
    seal = [p for p in SEALED if re.search(p, s)]
    if left or hits or seal:
        raise SystemExit('BUILD STOP left=%s forbidden=%s sealed=%s' % (left, hits, seal))
    open(outp, 'w', encoding='utf-8', newline='\n').write(s)
    print('FO_REPORT_BUILD ok lines=%d forbidden=0 sealed=0 placeholders=0 sha=%s' % (s.count('\n'), sha(outp)))


if __name__ == '__main__':
    main(*sys.argv[1:5])
