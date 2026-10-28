# -*- coding: utf-8 -*-
"""Format extra tables for VSL_REPORT.md from VS/out/vsl_metrics.json only (no new formulas). 2026-10-27 KST, vsl_v3c3.

Written AFTER the analysis outputs existed (formatting only). Every number printed here is a value already stored in
vsl_metrics.json (written by the pinned vsl_metrics.py 160c23c7...), or a difference VSL - NC3 that vsl_metrics.json
also stores under 'diff'. Rounding once at print. Output: VS/out/report_tables.md
Usage: python -B vsl_report_tables.py
"""
import json, sys

VS = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_v3c3'
SEEDS = (31, 41, 43)
ZONES = ['U', 'B1', 'M1', 'Mu', 'VS0', 'B2', 'D']
WINDOWS = ['0_900', '900_1350', '1350_1800', '1800_2250', '2250_2700', '2700_3600', '3600_4500', '4500_6300', '6300_8100',
           '8100_9000', '900_4500', '4500_9000', '900_9000']
CWIN = ['900_1350', '1350_1800', '1800_2250', '2250_2700', '2700_3600', '3600_4500', '4500_6300', '6300_9000', '900_9000']
LINES = ['4200', '5300', '6300', '6800', '7300', '7700', '8500']
RAMPS = ['10639', '10681', '10490', '10484']
CELLS = [str(k) for k in list(range(8, 15)) + list(range(16, 26))]


def f(x, nd=1, sign=True):
    if x is None:
        return '없음'
    s = (('%+.' if sign else '%.') + str(nd) + 'f') % x
    return s.replace('-', '−')


def w(s):
    a, b = s.split('_')
    return '%s–%s' % ('{:,}'.format(int(a)), '{:,}'.format(int(b)))


def main():
    R = json.load(open(VS + '/out/vsl_metrics.json', encoding='utf-8'))
    L = ['# report_tables (vsl_report_tables.py, vsl_metrics.json 값만 옮김)', '']
    S = {s: R['seeds'][str(s)] for s in SEEDS}
    use = [s for s in SEEDS if 'unusable' not in S[s]]
    L.append('- 쓸 수 있는 시드: ' + ', '.join('v3c3-s%d' % s for s in use) + ' (시드 %d)' % len(use))
    L.append('')
    # ---- level values T1
    for form in ('ours_9000', 'codex_8100'):
        L += ['## 수준값 %s (VSL / NC3, veh·h)' % form, '', '| 줄 | ' + ' | '.join('v3c3-s%d' % s for s in use) + ' |', '|---|' + '---:|' * len(use)]
        for k, name in (('O701', 'Ω701'), ('O635', 'Ω635'), ('A4a', '④a'), ('FWE7', '①'), ('LOCAL19', '②')):
            L.append('| %s | %s |' % (name, ' | '.join('%s / %s' % (f(S[s]['omega'][form]['level_a'][k], 1, False), f(S[s]['omega'][form]['level_b'][k], 1, False)) for s in use)))
        L.append('| S(W) 미삽입 | %s |' % ' | '.join('%s / %s' % (f(S[s]['omega'][form]['U_level_a'], 1, False), f(S[s]['omega'][form]['U_level_b'], 1, False)) for s in use))
        L.append('')
    # ---- T2 zone veh-h diff
    for s in use:
        P = S[s]['phys']
        L += ['## T2 v3c3-s%d' % s, '', '### 구역 Δveh·h (VSL − NC3)', '', '| 창 s | ' + ' | '.join(ZONES) + ' | 합 |', '|---|' + '---:|' * (len(ZONES) + 1)]
        for win in WINDOWS:
            d = P[win]['diff']['zones']
            L.append('| %s | %s | %s |' % (w(win), ' | '.join(f(d[z]['veh_h']) for z in ZONES), f(sum(d[z]['veh_h'] for z in ZONES))))
        L += ['', '### 구역 속도 km/h VSL / NC3', '', '| 창 s | ' + ' | '.join(ZONES) + ' |', '|---|' + '---|' * len(ZONES)]
        for win in WINDOWS:
            a, b = P[win]['vsl']['zones'], P[win]['nc3']['zones']
            L.append('| %s | %s |' % (w(win), ' | '.join('%s / %s' % (f(a[z]['speed_kmh'], 1, False), f(b[z]['speed_kmh'], 1, False)) for z in ZONES)))
        L += ['', '### 단면 흐름 Δveh/h · 합류 Δveh/h · 램프 대기 Δveh·h · 삽입 74 Δveh/h', '',
              '| 창 s | ' + ' | '.join('q' + x for x in LINES) + ' | ' + ' | '.join('m' + r for r in RAMPS) + ' | ' + ' | '.join('rq' + r for r in RAMPS) + ' | ins74 |',
              '|---|' + '---:|' * (len(LINES) + 2 * len(RAMPS) + 1)]
        for win in WINDOWS:
            d = P[win]['diff']
            L.append('| %s | %s | %s | %s | %s |' % (w(win), ' | '.join(f(d['flow_vph'][x], 0) for x in LINES), ' | '.join(f(d['merge_vph'][r], 0) for r in RAMPS),
                                                    ' | '.join(f(d['ramp_queued_veh_h'][r], 1) for r in RAMPS), f(d['ins_74_vph'], 0)))
        L += ['', '### 6,700–8,000 m 차로별 속도 km/h VSL / NC3 (Δ) · 번짐 분 VSL / NC3 · 꼬리 최상류 m VSL / NC3', '',
              '| 창 s | 차로1 | 차로2 | 차로3 | 차로4 | B1 번짐 분 | M 번짐 분 | B1 꼬리 | B2 꼬리 |', '|---|---|---|---|---|---|---|---|---|']
        for win in WINDOWS:
            a, b = P[win]['vsl'], P[win]['nc3']
            lanes = []
            for g in '1234':
                x, y = a['lane_speed_6700_8000'][g], b['lane_speed_6700_8000'][g]
                lanes.append('%s / %s (%s)' % (f(x, 1, False), f(y, 1, False), f(None if x is None or y is None else x - y)))
            L.append('| %s | %s | %d / %d | %d / %d | %s / %s | %s / %s |' % (w(win), ' | '.join(lanes), a['b1_spill_min'], b['b1_spill_min'], a['m_spill_min'], b['m_spill_min'],
                                                                      a['b1_tail_min_m'], b['b1_tail_min_m'], a['b2_tail_min_m'], b['b2_tail_min_m']))
        L.append('')
    # ---- T3 cells by window
    for s in use:
        C = S[s]['cells']
        for key, name, nd in (('speed_kmh', 'Δ속도 km/h', 1), ('flow_vph', 'Δ흐름 veh/h', 0), ('density_veh_km_lane', 'Δ밀도 veh/km/차로', 1)):
            L += ['## T3 v3c3-s%d 셀 %s (VSL − NC3)' % (s, name), '', '| 셀 | ' + ' | '.join(w(x) for x in CWIN) + ' |', '|---|' + '---:|' * len(CWIN)]
            for k in CELLS:
                L.append('| %s | %s |' % (k, ' | '.join(f(C[x]['diff'][k][key], nd) for x in CWIN)))
            L.append('')
        L += ['## T3 v3c3-s%d 셀 수준값 900–9,000 s (속도 VSL/NC3 · 흐름 VSL/NC3 · 밀도 VSL/NC3 · 희망 89–93 몫 VSL)' % s, '', '| 셀 | 범위 m | 속도 | 흐름 | 밀도 | 몫 |', '|---|---|---|---|---|---|']
        for k in CELLS:
            a, b = C['900_9000']['vsl'][k], C['900_9000']['nc3'][k]
            L.append('| %s | %.0f–%.0f | %s / %s | %s / %s | %s / %s | %s |' % (k, a['from_m'], a['to_m'], f(a['speed_kmh'], 1, False), f(b['speed_kmh'], 1, False),
                     f(a['flow_vph'], 0, False), f(b['flow_vph'], 0, False), f(a['density_veh_km_lane'], 1, False), f(b['density_veh_km_lane'], 1, False),
                     f(a['share_des_89_93'], 3, False)))
        L.append('')
    # ---- T4 compliance detail
    L += ['## T4 준수 상세 (VSL 런; 희망 89–93 차의 실현 속도 칸 몫 · 구역 veh·h VSL / NC3)', '',
          '| 시드 | 창 s | 0–60 | 60–80 | 80–88 | 88–95 | 95–100 | ≥100 | 실현 속도 전체 VSL / NC3 | 구역 veh·h VSL / NC3 | 처음 든 차 VSL / NC3 |', '|---|---|---:|---:|---:|---:|---:|---:|---|---|---|']
    for s in use:
        for x in CWIN:
            z = S[s]['zone'][x]; a, b = z['vsl'], z['nc3']
            h = a['cmd_speed_hist_share']
            L.append('| v3c3-s%d | %s | %s | %s / %s | %s / %s | %d / %d |' % (s, w(x), ' | '.join(f(h[k], 3, False) for k in ('0_60', '60_80', '80_88', '88_95', '95_100', 'ge100')),
                     f(a['speed_kmh_all'], 1, False), f(b['speed_kmh_all'], 1, False), f(a['veh_h_zone'], 1, False), f(b['veh_h_zone'], 1, False),
                     a['vehicles_first_zone_frame'], b['vehicles_first_zone_frame']))
    L.append('')
    open(VS + '/out/report_tables.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('written', VS + '/out/report_tables.md')


if __name__ == '__main__':
    main()
