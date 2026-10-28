# b_report_lines.py - markdown for COMPARE_RULE_B s4 lines and s5 checks, from work/b/b_report_tables.json only. New 2026-10-27 KST.
# Read only. Output work/b/b_report_lines.md. No percentages, no verdict words.
import json

CW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
r = json.load(open(CW + '/b/b_report_tables.json', encoding='utf-8'))
L, C = r['lines'], r['checks']
SEEDS = (31, 41, 43)
DAG = {31: '†', 41: '†', 43: ''}


def fmt(x, nd=1):
    if x is None:
        return '없음'
    v = round(x, nd)
    if v == 0:
        v = 0.0
    s = ('%.' + str(nd) + 'f') % abs(v)
    return ('+' if v > 0 else ('−' if v < 0 else '±')) + s


def lv(x, nd=1):
    return ('%.' + str(nd) + 'f') % x


def num(v):
    s = repr(v)
    return s[:-2] if s.endswith('.0') else s


md = []
# ---------------------------------------------------------------- link 66
md.append('#### 링크 66 (SC1004 남측) — veh·h, 시드 3\n')
md.append('| 꼴 · 짝 | v3c3-s31 | v3c3-s41 | v3c3-s43 |')
md.append('|---|---:|---:|---:|')
for f, fl in (('ours_9000', '우리 꼴 [0, 9000]'), ('codex_8100', 'codex 꼴 [0, 8100]')):
    md.append('| %s · B − NC3 | %s |' % (fl, ' | '.join(fmt(L['link66']['BN|%s|s%d' % (f, s)]) + DAG[s] for s in SEEDS)))
    md.append('| %s · B − V-A | %s |' % (fl, ' | '.join(fmt(L['link66']['BV|%s|s%d' % (f, s)]) for s in SEEDS)))
    md.append('| %s · 수준 B / NC3 / V-A | %s |' % (fl, ' | '.join(
        '%s / %s / %s' % tuple(lv(L['link66']['level|%s|%s_s%d' % (f, tg, s)]) for tg in ('j1', 'nc3', 'va')) for s in SEEDS)))
md.append('')
# ---------------------------------------------------------------- urban roads
U = L['urban']
md.append('#### 도시도로 두 규칙 (H12) — veh·h, 시드 3\n')
md.append('| 꼴 · 규칙 · 줄 · 짝 | v3c3-s31 | v3c3-s41 | v3c3-s43 | 출처 |')
md.append('|---|---:|---:|---:|---|')
for rule, rl in (('codex', 'codex 규칙'), ('ours', '우리 규칙(미터 상류 70·68·129·31 / 124·32·121·69 를 진입 쪽)')):
    for mk, ml in (('urban_roads', '도시도로'), ('onramps_E', '진입 E'), ('onramps_W', '진입 W')):
        md.append('| codex 꼴 [0, 8100] · %s · %s · B − NC3 | %s | M `%s.joint − nc` |' % (
            rl, ml, ' | '.join(fmt(U['BN|codex_8100|%s|%s|s%d' % (rule, mk, s)]) + DAG[s] for s in SEEDS),
            'codex_rule' if rule == 'codex' else 'alt_rule'))
md.append('| 우리 꼴 [0, 9000] · codex 규칙 · 도시도로 · B − NC3 | %s | O `urban_roads` |' % ' | '.join(
    fmt(U['BN|ours_9000|codex|urban_roads|s%d' % s]) + DAG[s] for s in SEEDS))
md.append('| 우리 꼴 [0, 9000] · codex 규칙 · 도시도로 · B − V-A | %s | −O `VA-J1 urban_roads` |' % ' | '.join(
    fmt(U['BV|ours_9000|codex|urban_roads|s%d' % s]) for s in SEEDS))
md.append('| codex 꼴 [0, 8100] · codex 규칙 · 도시도로 · B − V-A | %s | −O `VA-J1 urban_roads` |' % ' | '.join(
    fmt(U['BV|codex_8100|codex|urban_roads|s%d' % s]) for s in SEEDS))
md.append('')
md.append('- 수준(codex 꼴, B / NC3): ' + '; '.join(
    'v3c3-s%d 도시도로 codex 규칙 %s / %s, 우리 규칙 %s / %s' % (
        s, lv(U['level|codex_8100|codex|urban_roads|B|s%d' % s]), lv(U['level|codex_8100|codex|urban_roads|NC3|s%d' % s]),
        lv(U['level|codex_8100|ours|urban_roads|B|s%d' % s]), lv(U['level|codex_8100|ours|urban_roads|NC3|s%d' % s])) for s in SEEDS) + '.')
md.append('- B − V-A 의 우리 규칙 도시도로는 M 에 V-A 칸이 없어 "없음" 입니다.')
md.append('- 미터 상류 링크 체류 B − NC3 (codex 꼴, veh·h): ' + '; '.join(
    'v3c3-s%d ' % s + ', '.join('%s %s' % (k, fmt(U['upstream|s%d' % s]['B'][k] - U['upstream|s%d' % s]['NC3'][k]))
                               for k in ('70', '68', '129', '31', '124', '32', '121', '69')) for s in SEEDS) + '.')
md.append('')
# ---------------------------------------------------------------- meter distribution
M = L['meter']
md.append('#### 미터 녹색(초)·rate 분포 (B-7) — 결정 JSON, T = 900–8,850 s (결정 54개), 칸 = 값:결정 수\n')
meters = sorted(M['s31']['green'])
md.append('| 미터 | 녹색 v3c3-s31 | 녹색 v3c3-s41 | 녹색 v3c3-s43 |')
md.append('|---|---|---|---|')
for m in meters:
    md.append('| %s | %s |' % (m, ' | '.join(' · '.join('%s:%d' % (num(v), n) for v, n in M['s%d' % s]['green'][m]) for s in SEEDS)))
md.append('')
md.append('| 미터 | rate(`rm_out`) v3c3-s31 | v3c3-s41 | v3c3-s43 |')
md.append('|---|---|---|---|')
for m in meters:
    md.append('| %s | %s |' % (m, ' | '.join(' · '.join('%s:%d' % (num(v), n) for v, n in M['s%d' % s]['rate'][m]) for s in SEEDS)))
md.append('')
# ---------------------------------------------------------------- wall
W = L['wall']
md.append('#### 결정 벽시계 (T ≥ 900, `walltimes_out.json`; 동시 실행 아래 잰 값) — 초\n')
md.append('| 시드 | n | 평균 | 중앙 | 최소 | 최대 | > 360 | > 1,500 | > 1,800 | > 2,400 | budget 평균 / 최대 | 결과 | 큰 다섯 (T: 초) |')
md.append('|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|')
for s in SEEDS:
    w = W['s%d' % s]
    md.append('| v3c3-s%d | %d | %.1f | %.1f | %.1f | %.1f | %d | %d | %d | %d | %.1f / %.1f | %s | %s |' % (
        s, w['n_ge900'], w['wall']['mean'], w['wall']['median'], w['wall']['min'], w['wall']['max'], w['wall']['gt360'], w['gt1500'],
        w['wall']['gt1800'], w['gt2400'], w['budget_wall']['mean'], w['budget_wall']['max'], ' '.join(w['results']),
        ', '.join('%d: %.1f' % (t, v) for t, v, _ in w['top5'])))
md.append('')
md.append('| 시드 | 남의 VISSIM 있음: n · 평균 · 최대 | 없음: n · 평균 · 최대 | 모름: n · 평균 | 함께 돈 B 결정 수 (시간 가중): 평균 · 최소 · 최대 |')
md.append('|---|---|---|---|---|')
for s in SEEDS:
    c = W['s%d' % s]['concurrency']
    md.append('| v3c3-s%d | %d · %.1f · %.1f | %d · %.1f · %.1f | %d · %.1f | %.1f · %.2f · %.2f |' % (
        s, c['other_vissim_yes']['n'], c['other_vissim_yes']['mean'], c['other_vissim_yes']['max'], c['other_vissim_no']['n'],
        c['other_vissim_no']['mean'], c['other_vissim_no']['max'], c['other_vissim_unknown']['n'], c['other_vissim_unknown']['mean'],
        c['mean_concurrent_b']['mean'], c['mean_concurrent_b']['min'], c['mean_concurrent_b']['max']))
md.append('')
md.append('#### 유지(hold)·예외 (H9)\n')
md.append('| 시드 | DECISIONS_OK / FAILED / HELD_PREVIOUS / HELD_ON_EXCEPTION | `held` (T) | `DECISION_HOLD_ATTEMPT` 줄 | `DECISION_HELD_PREVIOUS` 줄 |')
md.append('|---|---|---|---|---|')
for s in SEEDS:
    w = W['s%d' % s]
    d = w['DECISIONS']
    md.append('| v3c3-s%d | %s / %s / %s / %s | %s | %d | %d |' % (
        s, d['DECISIONS_OK'][0], d['DECISIONS_FAILED'][0], d['DECISIONS_HELD_PREVIOUS'][0], d['DECISIONS_HELD_ON_EXCEPTION'][0],
        (', '.join(map(str, w['held'])) or '없음(0)'), len(w['hold_attempts']), len(w['held_previous'])))
md.append('')
# ---------------------------------------------------------------- ramp forecasts
RF = L['ramp_fc']
md.append('#### 램프 도착 예측 (H8) — `forecast_ramp_arrival_total_vph`(결정 JSON 메타데이터 = `ramp_fc_out.json` 의 logged), T = 900–8,850 s\n')
md.append('| 시드 | 결정 수 | 값 있음 | 최소 | 중앙 | 평균 | 최대 (vph) |')
md.append('|---|---:|---:|---:|---:|---:|---:|')
for s in SEEDS:
    x = RF['s%d' % s]
    md.append('| v3c3-s%d | %d | %d | %.1f | %.1f | %.1f | %.1f |' % (s, x['n'], x['n_logged'], x['min'], x['median'], x['mean'], x['max']))
md.append('')
# ---------------------------------------------------------------- VSL
md.append('- VSL 명령(`vsl_out`, T = 900–8,850 s): ' + '; '.join(
    'v3c3-s%d 값:결정 수 %s, 110 밖 %d' % (s, ' · '.join('%s:%d' % (num(v), n) for v, n in L['vsl']['s%d' % s]['values']),
                                       len(L['vsl']['s%d' % s]['non110'])) for s in SEEDS) + '.')
md.append('- 결정 JSON 상태: ' + '; '.join('v3c3-s%d controller_status %s, selection_status %s' % (
    s, L['vsl']['s%d' % s]['controller_status'], L['vsl']['s%d' % s]['selection_status']) for s in SEEDS) + '.')
md.append('')
# ---------------------------------------------------------------- appendix: per-decision ramp forecast
md.append('#### 부록: 결정별 램프 도착 예측 합 (vph)\n')
md.append('| T (s) | v3c3-s31 | v3c3-s41 | v3c3-s43 |')
md.append('|---:|---:|---:|---:|')
rows = {s: dict(RF['s%d' % s]['per_decision']) for s in SEEDS}
for t in sorted(rows[31]):
    md.append('| %d | %s |' % (t, ' | '.join(('%.1f' % rows[s][t]) if rows[s].get(t) is not None else '없음' for s in SEEDS)))
md.append('')
# ---------------------------------------------------------------- checks
md.append('#### 점검 X1–X5 값\n')
md.append('- X1: V 대 O(같은 짝·꼴, dΩ701·dΩ635·d①·d④a; 짝 2 × 꼴 2 × 시드 3 × 지표 4 = 48 값) 차 최대 %.6f veh·h, 0.05 넘는 값 %d.' % (C['X1_max_abs'], len(C['X1_over_0_05'])))
md.append('- X2: codex 꼴 도시도로 codex 규칙 M 대 O 짝 차의 차: ' + ', '.join('v3c3-s%d %.2e' % (x['seed'], x['diff']) for x in C['X2']) + '.')
x3 = C['X3']
md.append('- X3: 원본 V sha `%s…`, 원본 O sha `%s…`. V 의 va-nc3 %d칸 중 다른 칸 %d. O 의 `VA-NC3|*|*|U6VA` %d값 차 최대 %.3g. 통과 = %s.' % (
    x3['orig_V_sha'][:8], x3['orig_O_sha'][:8], x3['V_cells'], x3['V_cells_differing'], x3['O_values'], x3['O_max_abs_diff'], x3['pass']))
md.append('- X4: 링크 66 우리 꼴 B − NC3, P 대 top66.json 차: ' + ', '.join('v3c3-s%d %.2e' % (x['seed'], x['diff']) for x in C['X4']) + '.')
md.append('')
md.append('| X5 | B v3c3-s31 | NC3 v3c3-s31 | V-A v3c3-s31 | B v3c3-s41 | NC3 v3c3-s41 | V-A v3c3-s41 | B v3c3-s43 | NC3 v3c3-s43 | V-A v3c3-s43 |')
md.append('|---|' + '---:|' * 9)
for k, kl in (('arrivals_first_obs_9000', '첫 관측 차 수 (≤ 9,000 s)'), ('first_obs_74', '첫 관측 링크 74 (입력 1098)'),
              ('first_obs_26', '첫 관측 링크 26'), ('remain_1099', '`.err` 1099 남은 수'), ('arr_1099', '1099 도착 = 링크 26 + 남은 수')):
    md.append('| %s | %s |' % (kl, ' | '.join(str(C['X5']['s%d' % s][tg][k]) for s in SEEDS for tg in ('j1', 'nc3', 'va'))))
md.append('| `.err` 남은 수 전체 | %s |' % ' | '.join(
    (', '.join('%s:%d' % kv for kv in C['X5']['s%d' % s][tg]['remains_all'].items()) or '0') for s in SEEDS for tg in ('j1', 'nc3', 'va')))
md.append('')
with open(CW + '/b/b_report_lines.md', 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(md) + '\n')
print('ok', len(md))
