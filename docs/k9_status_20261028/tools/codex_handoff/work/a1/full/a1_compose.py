# a1_compose.py - format the A1 analysis outputs (trace / fzpdiff / a1_table JSON) as Markdown table fragments.
# No new numbers: only formatting and differences/ratios of values already in those JSON files.
# usage: python -B a1_compose.py <out.md> [--smoke]
import json, sys

SMOKE = '--smoke' in sys.argv
SFX = '_smoke' if SMOKE else ''
F = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a1/full'
TR = json.load(open(F + '/trace' + SFX + '.json', encoding='utf-8'))
FD = json.load(open(F + '/fzpdiff' + SFX + '.json', encoding='utf-8'))
TB = json.load(open(F + '/a1_table' + SFX + '.json', encoding='utf-8'))
L = []


def f1(x, nd=1, sign=False):
    if x is None:
        return '—'
    if isinstance(x, bool):
        return 'Y' if x else 'N'
    if isinstance(x, (int, float)):
        s = ('%+.' + str(nd) + 'f') % x if sign else ('%.' + str(nd) + 'f') % x
        return s.replace('-', '−')
    return str(x)


# ---- decision trace table
L.append('### T1 결정 추적 (A1 대 codex joint 기록, T ≥ 900)\n')
L.append('| T | R1 | 다른 행 | signal/sg/meter/vsl | SC 수 | 최대 녹색 차 s | 최대 offset 차 s | 녹색 차 ≥1 s 칸 | 미터 차 칸 | VSL 차 행 | 상태 값 잎 차 | 상태 최대 차 | selected_objective 차 | A1 exit/상태 | codex exit/상태 |')
L.append('|---:|:-:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|')
for g in TR['growth']:
    bk = g['by_kind'] or {}
    kinds = '/'.join(str(bk.get(k, 0)) for k in ('signal', 'signal_sg', 'ramp_meter', 'vsl'))
    L.append('| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s/%s | %s/%s |' % (
        g['T'], 'Y' if g['R1_equal'] else 'N', f1(g['n_rows_diff'], 0), kinds, f1(g['n_sc_diff'], 0), f1(g['max_green_delta'], 3),
        f1(g['max_offset_delta'], 3), f1(g['green_ge_1s'], 0), f1(g['meter_diff'], 0), f1(g['vsl_diff'], 0), f1(g['state_value_leaves'], 0),
        f1(g['state_value_max_abs'], 4), f1(g['sel_obj_delta'], 4, True), f1(g['a1_exit'], 0), g['a1_status'], f1(g['codex_exit'], 0), g['codex_status']))
L.append('')
# ---- meters per T (only where A1 and codex differ, plus the values)
L.append('### T2 램프 미터 명령 (rate_vph/green_sec, A1 대 codex; 다른 칸만)\n')
L.append('| T | 다른 미터 (A1 대 codex) |')
L.append('|---:|---|')
nm = 0
for t in [x for x in TR['per_T'] if int(x) >= 900]:
    r = TR['per_T'][t]
    la, lc = (r['a1'].get('levers') or {}), (r['codex'].get('levers') or {})
    ma, mc = la.get('meters') or {}, lc.get('meters') or {}
    diff = ['%s %s/%s 대 %s/%s' % (k, f1(ma.get(k, [None, None])[0], 0), f1(ma.get(k, [None, None])[1], 0), f1(mc.get(k, [None, None])[0], 0), f1(mc.get(k, [None, None])[1], 0))
            for k in sorted(set(ma) | set(mc)) if ma.get(k) != mc.get(k)]
    if diff:
        nm += 1
        L.append('| %s | %s |' % (t, '; '.join(diff)))
if nm == 0:
    L.append('| — | 다른 미터 명령 없음 |')
L.append('')
L.append('### T3 VSL 속도값 (A1 대 codex)\n')
vs = {}
for t in [x for x in TR['per_T'] if int(x) >= 900]:
    r = TR['per_T'][t]
    a = tuple((r['a1'].get('levers') or {}).get('vsl_speeds') or [])
    c = tuple((r['codex'].get('levers') or {}).get('vsl_speeds') or [])
    vs.setdefault((a, c), []).append(t)
for (a, c), ts in vs.items():
    L.append('- A1 %s 대 codex %s : T = %s' % (list(a), list(c), ', '.join(ts)))
L.append('')
# ---- holds
L.append('### T4 유지(hold)와 원인\n')
L.append('| 런 | 유지 T | 원인(runlog DECISION_HOLD_ATTEMPT 또는 error.txt 마지막 줄) |')
L.append('|---|---|---|')
for s in ('a1', 'codex'):
    hs = TR['summary']['a1_holds'] if s == 'a1' else TR['summary']['codex_holds']
    if not hs:
        L.append('| %s | 없음 | — |' % s)
    for h in hs:
        r = TR['per_T'][str(h)][s]
        L.append('| %s | %s | %s |' % (s, h, (r.get('error_txt_last') or (r.get('hold_attempt') or ''))[:200].replace('|', '/')))
L.append('- 종료 코드 ≠ 0: A1 %s, codex %s' % (TR['summary']['a1_nonzero_exit'], TR['summary']['codex_nonzero_exit']))
L.append('')
# ---- A0b
L.append('### T5 A0b 재생과 대조 (T = 1050–2550)\n')
L.append('| T | A1 = A0b (R1) | A0b = codex (R1) | A1 = codex (R1) | A1 대 A0b 다른 행 |')
L.append('|---:|:-:|:-:|:-:|---:|')
for t in range(1050, 2551, 150):
    r = TR['per_T'][str(t)]
    z = r.get('a0b')
    if z:
        L.append('| %d | %s | %s | %s | %s |' % (t, f1(z['R1_equal_a1_a0b']), f1(z['R1_equal_a0b_codex']), f1(r['R1_equal']), f1((z['rows_a1_vs_a0b'] or {}).get('n_differing_rows'), 0)))
L.append('')
# ---- wall
L.append('### T6 결정 벽시계 (runlog wall_sec, decision_budget wall_sec)\n')
L.append('| T | A1 runlog s | codex runlog s | 배수 | A1 budget s | codex budget s | 배수 |')
L.append('|---:|---:|---:|---:|---:|---:|---:|')
for g in TR['growth']:
    ra = (g['a1_wall'] / g['codex_wall']) if g['a1_wall'] and g['codex_wall'] else None
    rb = (g['a1_budget'] / g['codex_budget']) if isinstance(g['a1_budget'], float) and isinstance(g['codex_budget'], float) and g['codex_budget'] else None
    L.append('| %d | %s | %s | %s | %s | %s | %s |' % (g['T'], f1(g['a1_wall'], 1), f1(g['codex_wall'], 1), f1(ra, 2), f1(g['a1_budget'] if isinstance(g['a1_budget'], float) else None, 1),
                                                    f1(g['codex_budget'] if isinstance(g['codex_budget'], float) else None, 1), f1(rb, 2)))
sm = TR['summary']
L.append('- 합: A1 %s s, codex %s s; 최대 A1 %s s, codex %s s; A1 > 1,500 s %d개, > 1,800 s %d개.' % (f1(sm['a1_wall_sum'], 1), f1(sm['codex_wall_sum'], 1),
         f1(sm['a1_wall_max'], 1), f1(sm['codex_wall_max'], 1), sm['a1_wall_gt1500'], sm['a1_wall_gt1800']))
L.append('')
# ---- FZP
L.append('### T7 FZP 프레임 대조 (t ≤ 8,100)\n')
L.append('| 짝 | 895.1 s 까지 같음 | 처음 다른 프레임 s | 그 프레임: 한쪽만/다른 행 | 비교 프레임 | 다른 프레임 |')
L.append('|---|:-:|---:|---|---:|---:|')
for p in FD['pairs']:
    fd = p['first_diff'] or {}
    L.append('| %s | %s | %s | %s | %d | %d |' % (p['pair'], f1(p['prefix_equal_le_895_1']), f1(p['first_diff_t'], 1),
                                                 ('%s/%s/%s' % (fd.get('only_a'), fd.get('only_b'), fd.get('changed'))) if fd else '—', p['frames_compared'], p['frames_differing']))
L.append('')
# ---- result table
P, LEV = TB['pairs'], TB['levels']
ROWS = [('Omega701', 'Ω701'), ('Omega635', 'Ω635'), ('Omega701_minus_635', 'Ω701 − Ω635'), ('link66', '링크 66'), ('a4', '④a 망 전체 링크'),
        ('b4', '④b 미삽입 (짝 차 = 첫 관측 차분)'), ('four', '④ = ④a + ④b'), ('out_a_Omega701', 'Ω 밖 (a) Ω701 기준'), ('out_b_Omega701', 'Ω 밖 (b) Ω701 기준'),
        ('out_a_Omega635', 'Ω 밖 (a) Ω635 기준'), ('out_b_Omega635', 'Ω 밖 (b) Ω635 기준'), ('FW_E7', '① FW_E 본선 7링크'), ('local19', '② 국소 19링크'),
        ('urban_roads_codex', '도시도로 (codex 분할)'), ('urban_roads_ours', '도시도로 (우리 분할)'), ('onramps_E_codex', '진입 E (codex 분할)'),
        ('onramps_W_codex', '진입 W (codex 분할)'), ('onramps_E_ours', '진입 E (우리 분할)'), ('onramps_W_ours', '진입 W (우리 분할)')]
L.append('### T8 결과 표 — codex 꼴 0–8,100 s, veh·h\n')
L.append('| 칸 | A1 | LNC | **A1 − LNC** | codex joint | codex NC | **joint − NC** | A1 − joint |')
L.append('|---|---:|---:|---:|---:|---:|---:|---:|')
for k, nmk in ROWS:
    pk = 'b4_first_obs' if k == 'b4' else k
    L.append('| %s | %s | %s | %s | %s | %s | %s | %s |' % (nmk, f1(LEV['a1'][k]), f1(LEV['lnc_B'][k]), f1(P['a1-lnc'][pk], 1, True), f1(LEV['joint'][k]),
                                                      f1(LEV['nc_B'][k]), f1(P['joint-nc'][pk], 1, True), f1(P['a1-joint'][pk], 1, True)))
for k, nmk in (('b4_1098', '④b 입력 1098 (FW_E 입구, 링크 74)'), ('b4_1099', '④b 입력 1099 (FW_W 입구, 링크 26)'), ('b4_urban', '④b 도시 입력 합 (그 밖 링크)')):
    L.append('| %s | — | — | %s | — | — | %s | %s |' % (nmk, f1(P['a1-lnc'][k], 1, True), f1(P['joint-nc'][k], 1, True), f1(P['a1-joint'][k], 1, True)))
L.append('')
L.append('- ④b 수준: A1 native %s, joint native %s, NC 경로 A %s / 경로 B %s. 수준 열의 ④·Ω 밖 (a) 는 NC 경로 B 로 적음(경로 A 면 1.5 작음).' % (
    f1(TB['b4_levels']['a1']), f1(TB['b4_levels']['joint']), f1(TB['b4_levels']['lnc_A']), f1(TB['b4_levels']['lnc_B'])))
L.append('- ④b 참고(native − NC 수준): A1 − LNC %s(경로 A) / %s(경로 B); joint − NC %s / %s. A1 − joint native 차 %s, 첫 관측 차 %s.' % (
    f1(P['a1-lnc']['b4_native_minus_ncA'], 1, True), f1(P['a1-lnc']['b4_native_minus_ncB'], 1, True), f1(P['joint-nc']['b4_native_minus_ncA'], 1, True),
    f1(P['joint-nc']['b4_native_minus_ncB'], 1, True), f1(P['a1-joint']['b4_native_diff'], 2, True), f1(P['a1-joint']['b4_first_obs'], 2, True)))
L.append('')
L.append('| 백분율 (NC 수준 경로 B 대비) | Ω701 % | Ω635 % | ④a % | ④ % | ① % | ② % | 도시도로 codex % | 도시도로 우리 % |')
L.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|')
for pk, nmk in (('a1-lnc', 'A1 − LNC'), ('joint-nc', 'joint − NC')):
    q = TB['pct_vs_nc_level_routeB'][pk]
    L.append('| %s | %s |' % (nmk, ' | '.join(f1(q.get(k), 2, True) for k in ('Omega701', 'Omega635', 'a4', 'four', 'FW_E7', 'local19', 'urban_roads_codex', 'urban_roads_ours'))))
L.append('')
ac = TB['arrival_check']
L.append('- 도착열 점검: 링크 74 첫 관측 수(≤ 8,100 s) %s; 1099 도착(링크 26 첫 관측 + remain) %s; remain(.err) %s; LNC 첫 관측 = codex NC 첫 관측: %s.' % (
    json.dumps(ac['inserted_by_8100_link74']), json.dumps(ac['A1099_8100']), json.dumps(ac['remain_err']), ac['lnc_equals_nc_raw_firstseen']))
L.append('- 표 도구 검산: %s' % json.dumps(TB['checks'], ensure_ascii=False))
L.append('')
OP, OL = TB['ours_pairs'], TB['ours_levels']
L.append('### T9 우리 꼴 0–8,100 s (링크 칸만), veh·h\n')
L.append('| 칸 | A1 | LNC | A1 − LNC | joint | joint − LNC |')
L.append('|---|---:|---:|---:|---:|---:|')
for k, nmk in [r for r in ROWS if r[0] in OL['a1']] + [('out_b_Omega701', 'Ω 밖 (b) Ω701 기준'), ('out_b_Omega635', 'Ω 밖 (b) Ω635 기준')]:
    if k in OL['a1']:
        L.append('| %s | %s | %s | %s | %s | %s |' % (nmk, f1(OL['a1'][k]), f1(OL['lnc'][k]), f1(OP['a1-lnc'][k], 1, True), f1(OL['joint'][k]), f1(OP['joint-lnc'][k], 1, True)))
    else:
        L.append('| %s | — | — | %s | — | %s |' % (nmk, f1(OP['a1-lnc'][k], 1, True), f1(OP['joint-lnc'][k], 1, True)))
L.append('- 우리 꼴 창: %s' % json.dumps(TB['ours_windows']))
open(sys.argv[1], 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('written', len(L), 'lines')
