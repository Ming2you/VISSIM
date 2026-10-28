# -*- coding: utf-8 -*-
"""Markdown tables for W264_READ.md from w264_analysis.json / w264_bins150.csv / decisions.json (read-only)."""
import csv, json
W = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/rmcause/o1o4/work'
A = json.load(open(W + '/w264_analysis.json', encoding='utf-8'))
D = json.load(open(W + '/decisions.json', encoding='utf-8'))
P = A['periods']
out = []

# 1. shifted-waiting table, whole run
rows = [('FW_E 본선 7링크 (주 지표)', 'main7'), ('FW_E 진입 커넥터 4', 'on_conn_e'), ('FW_E 진입 접근로 4', 'on_appr_e'),
        ('FW_E 진출 커넥터 4', 'off_conn_e'), ('국소 19링크 (=7+4+4+4)', 'local19'), ('진출 수신 공유 4 (121·124·126·127)', 'off_recv_shared'),
        ('FW_W 본선 3 (26·120·10771)', 'fw_w_main'), ('서측 미터 커넥터 4', 'w_ramp_conn'),
        ('Ω701 (W264 목적 영역)', 'om701'), ('Ω635 (이전 영역)', 'om635'), ('Ω701 중 위 고속도로 묶음 밖(도시 쪽)', 'om701_rest'),
        ('Ω701 밖', 'outside_om701'), ('망 안 전체', 'all')]
out.append('| 묶음 | NC | W264 | Δ W264−NC | Δ % | 참고: VSL 단독 Δ |')
out.append('|---|---:|---:|---:|---:|---:|')
p = P['0-9000']
for name, k in rows:
    n, w, d = p[k]['N'], p[k]['W'], p[k]['d']
    out.append(f"| {name} | {n:,.1f} | {w:,.1f} | {d:+,.1f} | {100*d/n:+.2f} | {p['V'][k]['d']:+,.1f} |")
dl, dv = p['dlat'], p['V']['dlat']
out.append(f"| 미삽입 대기 Δ: 1098(FW_E 입구) | | | {dl['1098']:+.1f} | | {dv['1098']:+.1f} |")
out.append(f"| 미삽입 대기 Δ: 1099(FW_W 입구) | | | {dl['1099']:+.1f} | | {dv['1099']:+.1f} |")
out.append(f"| 미삽입 대기 Δ: 도시 입력 32개 | | | {dl['urban']:+.1f} | | {dv['urban']:+.1f} |")
out.append(f"| 전체+미삽입 Δ (대리 계산) | | | {p['all_plus_lat_d']:+.1f} | | {p['V']['all_plus_lat_d']:+.1f} |")
out.append('')

# 2. period table
pers = ['0-900', '900-1800', '1800-2700', '2700-3600', '3600-4500', '4500-5700', '5700-7200', '7200-9000', '0-1800', '1800-5700', '5700-9000', '0-9000']
out.append('| 구간(s) | 본선7 Δ | 본선7 Δ% | 링크 2 Δ | 링크 119 Δ | 진입 커넥터+접근로 Δ | 국소19 Δ | Ω701 Δ | 도시 쪽 Ω Δ | 미삽입 Δ(1098/1099/도시) | 전체+미삽입 Δ | B1 번짐 분 N/W/V | M 번짐 분 N/W/V | VSL 단독 본선7 Δ |')
out.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|---:|')
for k in pers:
    q = P[k]
    n7 = q['main7']['N']
    pct = 100 * q['main7']['d'] / n7 if n7 else 0
    ramp = q['on_conn_e']['d'] + q['on_appr_e']['d']
    out.append(f"| {k} | {q['main7']['d']:+.1f} | {pct:+.1f} | {q['m_2']['d']:+.1f} | {q['m_119']['d']:+.1f} | {ramp:+.1f} | {q['local19']['d']:+.1f} | "
               f"{q['om701']['d']:+.1f} | {q['om701_rest']['d']:+.1f} | {q['dlat']['1098']:+.1f}/{q['dlat']['1099']:+.1f}/{q['dlat']['urban']:+.1f} | "
               f"{q['all_plus_lat_d']:+.1f} | {q['b1spill_min']['N']}/{q['b1spill_min']['W']}/{q['b1spill_min']['V']} | "
               f"{q['mspill_min']['N']}/{q['mspill_min']['W']}/{q['mspill_min']['V']} | {q['V']['main7']['d']:+.1f} |")
out.append('')

# 3. zone delay per 900 s block
out.append('| 900 s 칸 시작 | ' + ' | '.join(str(900 * i) for i in range(10)) + ' | 합 |')
out.append('|---|' + '---:|' * 11)
for z in ['U', 'B1', 'M', 'B2', 'D']:
    for a, lab in (('N', 'NC'), ('W', 'W264'), ('V', 'VSL 단독')):
        v = A['phys'][a]['zone_delay_900'][z]
        out.append(f"| {z} {lab} | " + ' | '.join(f'{x:.1f}' for x in v) + f" | {sum(v):.1f} |")
out.append('')

# 4. 150 s appendix table
r = list(csv.DictReader(open(W + '/w264_bins150.csv', encoding='utf-8')))
out.append('| t(s) | VSL | g10480(서) | g10639 | g10681 | g10490 | g10484 | 본선7 NC | 본선7 W | Δ | 누적 Δ | VSL 단독 누적 Δ | B1 번짐 N/W/V(분) | M 번짐 N/W/V(분) | 동측 램프 대기 W/N(대) | 국소19 Δ | Ω701 Δ | 전체+미삽입 누적 Δ |')
out.append('|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|---:|---:|')
for x in r:
    t = int(x['bin_start_s'])
    if t < 900:
        continue
    qW = (float(x['qon_e_W'])) * 24
    qN = (float(x['qon_e_N'])) * 24
    out.append(f"| {t} | {x['vsl_dsd63_66']} | {x['g_RM_C10480']} | {x['g_RM_C10639']} | {x['g_RM_C10681']} | {x['g_RM_C10490']} | {x['g_RM_C10484']} | "
               f"{float(x['main7_N']):.1f} | {float(x['main7_W']):.1f} | {float(x['main7_d']):+.1f} | {float(x['main7_cumd']):+.1f} | {float(x['V_main7_cumd']):+.1f} | "
               f"{x['b1spill_N']}/{x['b1spill_W']}/{x['b1spill_V']} | {x['mspill_N']}/{x['mspill_W']}/{x['mspill_V']} | {qW:.0f}/{qN:.0f} | "
               f"{float(x['local19_d']):+.1f} | {float(x['om701_d']):+.1f} | {float(x['cum_all_plus_lat_d']):+.1f} |")
open(W + '/tables.md', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('\n'.join(out[:60]))
