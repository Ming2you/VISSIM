# -*- coding: utf-8 -*-
"""vf_tables.py - VERIFY_FWE: markdown tables from VERIFY_NUMBERS.json / VERIFY_EXTRA*.json / meter.json (formatting only,
no new numbers). Usage: python -B vf_tables.py <verify_dir>  -> <verify_dir>/out/VERIFY_TABLES.md"""
import collections
import hashlib
import json
import os
import sys

VD = sys.argv[1]
O = os.path.join(VD, 'out')
R = json.load(open(os.path.join(O, 'VERIFY_NUMBERS.json'), encoding='utf-8'))
X2 = json.load(open(os.path.join(O, 'VERIFY_EXTRA2.json'), encoding='utf-8'))
M = json.load(open(os.path.join(O, 'meter.json'), encoding='utf-8'))
P = R['pairs']
L = []


def f1(v, d=1):
    s = ('%+.' + str(d) + 'f') % v
    return s.replace('-', '−')


L.append('### V1. 대조 묶음별 (원자료 독립 재계산 대 FWE_DECOMP r1)\n')
L.append('| 묶음 | 칸 수 | 허용 안 | 허용 밖 | 최대 |차| |')
L.append('|---|---:|---:|---:|---:|')
agg = collections.OrderedDict()
for c in R['cmp']:
    k = c['key'].split('|')
    t = k[0] if k[0] not in ('T2', 'T3', 'T4', 'T5') else k[0] + ' ' + (k[3] if k[0] == 'T5' else k[-1])
    a = agg.setdefault(t, [0, 0, 0.0]); a[0] += 1; a[1] += 0 if c['ok'] else 1; a[2] = max(a[2], abs(c['diff']))
for t, (n, f, mx) in agg.items():
    L.append('| %s | %d | %d | %d | %.3f |' % (t, n, n - f, f, mx))
L.append('| **합** | **%d** | **%d** | **%d** | |' % (R['n_cmp'], R['n_cmp'] - R['n_fail'], R['n_fail']))
L.append('\n허용 밖 칸:\n')
for c in R['cmp']:
    if not c['ok']:
        L.append('- `%s`: 다시 셈 %.3f, r1 %s, 차 %+.3f' % (c['key'], c['mine'], c['claim'], c['diff']))

L.append('\n### V2. 총합 다시 셈 (v3c3 우리 꼴 [0, 9000] s, 64cf codex 꼴 [0, 8100] s; veh·h)\n')
L.append('| 짝 · 시드 | d① | d① codex 꼴 | d② | 도시도로 (codex 분할) | Ω701 | ④ | Ω 밖 (a) | Ω 밖 (b) | ④b 1098 | 감시: ④b 1099 |')
L.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
for pn in ('P-VA', 'P-B', 'P-BVA', 'P-VSL', 'P-J1', 'Q-joint'):
    for s in ('s31', 's41', 's43', 's29'):
        p = P.get(pn + '|' + s)
        if not isinstance(p, dict):
            continue
        net = '64cf' if s == 's29' else 'v3c3'
        L.append('| %s %s-%s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            pn, net, s, f1(p['d1']), f1(p['d1_codex8100']), f1(p['d2']), f1(p['URBAN']), f1(p['O701']), f1(p['A4']), f1(p['outa']), f1(p['outb']),
            f1(p['u1098']), f1(p['u1099'])))
L.append('\n### V3. 구역 d① (bin 꼴, 900 s–끝) · 셀 5–9 · 이득 시각 (veh·h, s)\n')
L.append('| 짝 · 시드 | U | B1 | M | B2 | D | 셀 5–9 (칸 가운데) | 셀 5–9 (차 위치) | T_gain_a | T_half |')
L.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
for pn in ('P-VA', 'P-B', 'P-BVA', 'P-VSL', 'P-J1', 'Q-joint'):
    for s in ('s31', 's41', 's43', 's29'):
        p = P.get(pn + '|' + s)
        if not isinstance(p, dict):
            continue
        z = p['zone_900_end']
        L.append('| %s %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (pn, s, f1(z['U']), f1(z['B1']), f1(z['M']), f1(z['B2']), f1(z['D']),
                                                                       f1(p['cell59_center_900_end']), f1(p['cell59_exact_900_end']),
                                                                       p['Tgain_a_start'], p['Thalf_start']))
L.append('\n### V4. 미터 (GREEN 초만; readback 초별 상태 재구성, codex joint 는 LDP 와 readback 둘 다)\n')
L.append('| 런 | 원천 | 10639 | 10681 | 10490 | 10484 | readback = 명령 주기 | LDP = readback 주기 |')
L.append('|---|---|---|---|---|---|---|---|')
for tag, R1 in M['runs'].items():
    for src in ('readback', 'ldp'):
        cells = []; eq = []; eq2 = []
        for c in ('10639', '10681', '10490', '10484'):
            m = R1['meters'][c]
            if src not in m:
                break
            s = m[src]
            cells.append('%d/%d · %s · %s · %.2f' % (s['n_tight10'], s['n_cycles'], s['T_tight10'] or '—', s['T_tight6'] or '—', s['mean_green']))
            eq.append(str(m.get('cmd_eq_readback_cycles', '—'))); eq2.append(str(m.get('ldp_eq_readback_cycles', '—')))
        if len(cells) == 4:
            L.append('| %s | %s | %s | %s | %s |' % (tag, src, ' | '.join(cells), '/'.join(eq), '/'.join(eq2)))
L.append('\n칸 = GREEN<10 주기 / 전체 · T_tight10 · T_tight6 · 평균 GREEN 초.\n')
L.append('\n### V5. 10639 합류와 미터 GREEN, 900 s 칸 (합류 차 veh/h (팔 / 기준) · 평균 GREEN · 조임 몫 · 10639 쪽 재고 차 veh·h)\n')
for pn in ('P-B|s31', 'P-B|s41', 'P-B|s43', 'Q-joint|s29'):
    rows = X2[pn]['10639']
    ws = list(rows)
    L.append('| %s | %s |' % (pn, ' | '.join('%s–%s' % (w, int(w) + 900) for w in ws)))
    L.append('|---|' + '---:|' * len(ws))
    L.append('| 합류 차 (팔/기준) | %s |' % ' | '.join('%s (%d/%d)' % (f1(rows[w]['d'], 0), rows[w]['arm'], rows[w]['base']) for w in ws))
    L.append('| 평균 GREEN · 조임 몫 | %s |' % ' | '.join('%.1f · %.2f' % (rows[w]['g'], rows[w]['tight']) if rows[w]['g'] is not None else '—' for w in ws))
    L.append('| 10639 쪽 재고 차 | %s |\n' % ' | '.join(f1(rows[w]['stock_d']) for w in ws))
L.append('\n### V6. 런 (시드는 provenance `/seed`, FZP sha256 은 이번에 다시 냄)\n')
L.append('| 꼬리표 | seed | FZP sha256 앞 16 | 목록과 같음 | 행 | 0.1 s 행 | 프레임 | 차 | ① 우리 꼴 | ① codex 꼴 | 구역 합 = 링크 합 |')
L.append('|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|')
for t, v in R['runs'].items():
    if isinstance(v, dict):
        L.append('| %s | %s | `%s` | %s | %d | %d | %d | %d | %.1f | %.1f | %s |' % (t, v['seed_provenance'], v['fzp_sha256'][:16], v['sha_eq_expected'], v['rows'], v['rows_t_lt_1'],
                                                                                v['frames'], v['n_vehicles'], v['L1_ours_9000'], v['L1_codex_8100'], v['zone_sum_eq_link_sum']))
a = R['checks']['codex_summary_anchor']
L.append('\n### V7. 도시도로 codex 분할 점검 (codex 꼴 [0, 8100], codex `analysis/comparison/summary.json` 수준값과 차)\n')
L.append('| 런 | FW_E | 도시도로 | Ω701 | FW_W (감시) |')
L.append('|---|---:|---:|---:|---:|')
for k in ('nc', 'joint'):
    L.append('| codex %s | %.3f (차 %.1e) | %.3f (차 %.1e) | %.3f (차 %.1e) | %.3f (차 %.1e) |' % (
        k, a[k]['FW_E']['mine'], a[k]['FW_E']['diff'], a[k]['urban_roads']['mine'], a[k]['urban_roads']['diff'], a[k]['omega']['mine'], a[k]['omega']['diff'],
        a[k]['FW_W']['mine'], a[k]['FW_W']['diff']))
out = os.path.join(O, 'VERIFY_TABLES.md')
open(out, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('DONE', out, hashlib.sha256(open(out, 'rb').read()).hexdigest())
