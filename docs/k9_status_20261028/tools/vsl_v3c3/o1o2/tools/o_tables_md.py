# -*- coding: utf-8 -*-
"""Render o1o2_tables.json into markdown tables (no new numbers; formatting only). vsl_v3c3 o1o2, 2026-10-27 KST.
Usage: python -B o_tables_md.py <O dir>"""
import json, os, sys

O = sys.argv[1]
d = json.load(open(os.path.join(O, 'out', 'o1o2_tables.json'), encoding='utf-8'))
L = []
f = lambda x, n=3: ('—' if x is None else ('%+.*f' % (n, x)))
g = lambda x, n=1: ('—' if x is None else ('%.*f' % (n, x)))
ORDER = ['base', 'p0.95_r1.00', 'p0.90_r1.00', 'p0.85_r1.00', 'p1.00_r0.90', 'p1.00_r1.10', 'p0.95_r0.90', 'p0.90_r0.90',
         'p0.85_r0.90', 'p0.95_r1.10', 'p0.90_r1.10', 'p0.85_r1.10', 'base_repeat']

L.append('## O1 표 A — ΔJ (veh·h, 450 s, v − 110) 와 부호 (|ΔJ| < 0.01 = 0)\n')
L.append('| 상태 | 설정 | J_110 | ΔJ_100 | 부호 | ΔJ_90 | 부호 | 바뀜 100/90 | FW_E 자기 Δ 100/90 | 셀16–25 ρ>ρc 초 110/100/90 |')
L.append('|---|---|---:|---:|:-:|---:|:-:|:-:|---|---|')
for lab, r in d['o1'].items():
    if r.get('status') != 'ok':
        L.append('| %s | %s | | | | | | | | |' % (r.get('name', lab), r.get('status')))
        continue
    for c in ORDER:
        row = r['configs'].get(c)
        if row is None:
            L.append('| %s | %s | 못 냄 | | | | | | | |' % (r['name'], c))
            continue
        fl = '/'.join(('엄격' if row.get('strict_flip_' + v) else ('느슨' if row.get('flip_' + v) else '·')) for v in ('v100', 'v90'))
        ex = row.get('exceed_sec_cells16_25') or {}
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s / %s | %s / %s / %s |' % (
            r['name'], c, g((row['J'] or {}).get('v110'), 2), f(row.get('dJ_v100')), row.get('sign_v100') or '—',
            f(row.get('dJ_v90')), row.get('sign_v90') or '—', fl, f(row.get('dOwn_v100')), f(row.get('dOwn_v90')),
            g(ex.get('v110'), 0), g(ex.get('v100'), 0), g(ex.get('v90'), 0)))
L.append('')
L.append('## O1 표 B — 구역 시간평균 속도 Δ (km/h, v90 − v110; 450 s)\n')
L.append('| 상태 | 설정 | U | B1 | M1 | VSa | VSb | D | VSL 셀(90) |')
L.append('|---|---|---:|---:|---:|---:|---:|---:|---|')
for lab, r in d['o1'].items():
    if r.get('status') != 'ok':
        continue
    for c in ('base', 'p0.85_r1.00', 'p1.00_r0.90', 'p1.00_r1.10', 'p0.85_r0.90', 'p0.85_r1.10'):
        row = r['configs'].get(c)
        if not row or 'dSpeed_v90' not in row:
            continue
        s = row['dSpeed_v90']
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (r['name'], c, *(f(s[z], 2) for z in ('U', 'B1', 'M1', 'VSa', 'VSb', 'D')),
                                                          ','.join(map(str, row.get('vsl_cells_v90') or []))))
L.append('')
L.append('## O1 점검 — 결정성·VSL_OFFLINE 대조\n')
for lab, r in d['o1'].items():
    if r.get('status') != 'ok':
        continue
    reg = r.get('regression_vs_vsl_offline')
    L.append('- %s: base−base_repeat 최대 |ΔJ| = %s; 경로 %s; 원래 φ %s·링크 ρc %s%s' % (
        r['name'], r.get('determinism_max_abs_dJ'), 'lane_group ' + str(r.get('lane_group_roads')), r['original_params'].get('phi'),
        r['original_params'].get('rho_link'),
        ('' if not reg else '; VSL_OFFLINE J 110/100/90 = %s / %s / %s, 이번 = %s / %s / %s' % (
            g(reg['old_J'].get('v110_all'), 4), g(reg['old_J'].get('v100_all'), 4), g(reg['old_J'].get('v90_all'), 4),
            g(reg['new_J'].get('v110'), 4), g(reg['new_J'].get('v100'), 4), g(reg['new_J'].get('v90'), 4)))))
L.append('')
o2 = d['o2']
L.append('## O2 표 C — 64cf-s29 plant − VISSIM 편향 (6상태 평균; 괄호 = 평균 |e|)\n')
L.append('| 팔 | 블록 | 구역 | n | 속도 km/h | 재고 veh | 흐름 veh/h |')
L.append('|---|---:|---|---:|---:|---:|---:|')
for arm, name in (('win', 'window (VSL 90 켬)'), ('off', 'off (110)')):
    for b in ('0', '1', '2'):
        for z in ('B1', 'M1', 'VSa', 'VSb', 'D'):
            s = o2['summary'].get(arm, {}).get('%s|%s' % (b, z))
            if not s:
                continue
            L.append('| %s | %s | %s | %d | %s (%s) | %s (%s) | %s (%s) |' % (name, b, z, s['n'], f(s['bias_speed'], 1), g(s['mae_speed']),
                                                                         f(s['bias_stock'], 1), g(s['mae_stock']), f(s['bias_flow'], 0), g(s['mae_flow'], 0)))
L.append('')
L.append('## O2 표 D — 켬 − 끔 편향 차 (평균 e(window) − 평균 e(off))\n')
L.append('| 블록 | 구역 | 속도 | 재고 | 흐름 |')
L.append('|---:|---|---:|---:|---:|')
for b in ('0', '1', '2'):
    for z in ('B1', 'M1', 'VSa', 'VSb', 'D'):
        a, c = o2['summary'].get('win', {}).get('%s|%s' % (b, z)), o2['summary'].get('off', {}).get('%s|%s' % (b, z))
        if not a or not c or a['bias_speed'] is None or c['bias_speed'] is None:
            continue
        L.append('| %s | %s | %s | %s | %s |' % (b, z, f(a['bias_speed'] - c['bias_speed'], 1), f(a['bias_stock'] - c['bias_stock'], 1), f(a['bias_flow'] - c['bias_flow'], 0)))
L.append('')
L.append('## O2 표 E — 상태별: plant 반사실 (90 − 110) 대 VISSIM window − off, 구역 속도 km/h (블록 0 / 1 / 2)\n')
L.append('| T | 구역 | plant@window 상태 | plant@off 상태 | VISSIM window − off | plant ΔJ@window / @off |')
L.append('|---:|---|---|---|---|---|')
for T in (1800, 1950, 2100, 2250, 2400, 2550):
    sw, so = o2['states'].get('o2_win_T%06d' % T, {}), o2['states'].get('o2_off_T%06d' % T, {})
    wo = o2['vissim_window_minus_off'].get(str(T))
    for z in ('M1', 'VSa', 'VSb', 'D'):
        pw = ' / '.join(f(sw['plant_d90m110'][b][z]['speed'], 1) for b in ('0', '1', '2')) if sw.get('plant_d90m110') else '못 냄'
        po = ' / '.join(f(so['plant_d90m110'][b][z]['speed'], 1) for b in ('0', '1', '2')) if so.get('plant_d90m110') else '못 냄'
        vw = ' / '.join(f(wo[b][z]['speed'], 1) for b in ('0', '1', '2')) if wo else '못 냄'
        L.append('| %d | %s | %s | %s | %s | %s / %s |' % (T, z, pw, po, vw, f(sw.get('plant_dJ_90m110')), f(so.get('plant_dJ_90m110'))))
L.append('')
L.append('## O2 표 F — 상태별 VSa·VSb 속도 (plant / VISSIM, km/h; 블록 0 / 1 / 2)\n')
L.append('| 상태 | VSa plant | VSa VISSIM | VSb plant | VSb VISSIM | M1 plant | M1 VISSIM |')
L.append('|---|---|---|---|---|---|---|')
for lab, st in o2['states'].items():
    fi = st.get('fidelity')
    if not fi:
        L.append('| %s | %s | | | | | |' % (lab, st.get('status')))
        continue
    cell = lambda z, k: ' / '.join(g(fi[b]['zones'][z][k]) for b in ('0', '1', '2') if b in fi)
    L.append('| %s | %s | %s | %s | %s | %s | %s |' % (lab, cell('VSa', 'speed_p'), cell('VSa', 'speed_v'), cell('VSb', 'speed_p'), cell('VSb', 'speed_v'), cell('M1', 'speed_p'), cell('M1', 'speed_v')))
L.append('')
L.append('## O2 표 G — 미터 명령 (rate veh/h; held T−150 → T / T+150 / T+300), FW_E 미터\n')
L.append('| 상태 | RM_C10639 | RM_C10681 | RM_C10490 | RM_C10484 |')
L.append('|---|---|---|---|---|')
for lab, st in o2['states'].items():
    m = st.get('meters')
    if not m:
        continue
    ts = sorted(m, key=int)
    L.append('| %s | %s |' % (lab, ' | '.join(' → '.join(g((m[t].get(r) or [None])[0], 0) for t in ts) for r in ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484'))))
L.append('')
L.append('## O2 표 H — v3c3 B 상태 VSL 끔 충실도 (plant v110 − B 런 VISSIM; 블록 0 / 1 / 2)\n')
L.append('| 상태 | 구역 | 속도 e | 재고 e | 흐름 e | plant 속도 | VISSIM 속도 |')
L.append('|---|---|---|---|---|---|---|')
for lab, st in o2['v3c3_B_vsl_off_fidelity'].items():
    fi = st.get('fidelity')
    if not fi:
        L.append('| %s | %s | | | | | |' % (lab, st.get('status')))
        continue
    for z in ('B1', 'M1', 'VSa', 'VSb', 'D'):
        c = lambda k, n: ' / '.join((f if k.startswith('e_') else g)(fi[b]['zones'][z][k], n) for b in ('0', '1', '2') if b in fi)
        L.append('| %s | %s | %s | %s | %s | %s | %s |' % (lab, z, c('e_speed', 1), c('e_stock', 1), c('e_flow', 0), c('speed_p', 1), c('speed_v', 1)))
L.append('')
L.append('## O2 표 I — v3c3 부호 대조: plant Δ(90−110)@B 상태 대 VISSIM Δ(VSL 단독 − NC3), 구역 속도 km/h (블록 0 / 1 / 2)\n')
L.append('| 시드·T | 구역 | plant | VISSIM | 상태 |')
L.append('|---|---|---|---|---|')
for s in ('31', '41', '43'):
    for T in (1800, 3600):
        pl = o2['v3c3_B_vsl_off_fidelity'].get('o1_b%s_T%06d' % (s, T), {}).get('plant_d90m110')
        vn = o2['v3c3_vissim_vsl_minus_nc3'].get('s%s_T%d' % (s, T), {})
        for z in ('M1', 'VSa', 'VSb', 'D'):
            p = ' / '.join(f(pl[b][z]['speed'], 1) for b in ('0', '1', '2')) if pl else '못 냄'
            v = ' / '.join(f(vn['d'][b][z]['speed'], 1) for b in ('0', '1', '2')) if vn.get('status') == 'ok' else vn.get('status', '—')
            L.append('| v3c3-s%s T=%d | %s | %s | %s | %s |' % (s, T, z, p, v, vn.get('status', '—')))
open(os.path.join(O, 'out', 'o1o2_tables.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('ok', len(L))
