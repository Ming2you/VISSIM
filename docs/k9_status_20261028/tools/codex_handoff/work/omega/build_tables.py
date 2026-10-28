# Build markdown table fragments and CSVs from omega701_v3c3.json (no FZP read). Read only toward V-A outputs.
import csv
import io
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
D = json.load(io.open(os.path.join(HERE, 'omega701_v3c3.json'), encoding='utf-8'))
VAM = json.load(io.open(SP + '/k92/va/analysis/out/va_metrics.json', encoding='utf-8'))
SEEDS = (31, 41, 43)
ROWS = [
    ('Omega635', 'Ω635 (우리 목적 영역, 635링크)'),
    ('Omega701', 'Ω701 (codex 목적 영역, 701링크)'),
    ('d701_635', 'Ω701 − Ω635 (더한 66링크)'),
    ('Omega701_minus_west', 'Ω701 − 서측 본선(26·10771·120)'),
    ('urban_roads', '도시도로 (codex 분할)'),
    ('offramps701', '진출램프 (Ω701 안 6개)'),
    ('onramps_E', '동측 진입 커넥터 4'),
    ('onramps_W', '서측 진입 커넥터 4'),
    ('FW_E7', '① FW_E 본선 7링크'),
    ('FW_W_main', '서측 본선 3원소'),
    ('local19', '② 국소 19링크'),
    ('M4a', '④a 전체 링크'),
    ('M4b', '④b 미삽입 (U9, NC3 앵커)'),
    ('M4', '④ = ④a + ④b'),
    ('out_a_635', 'Ω 밖 (a) ④ − Ω635'),
    ('out_b_635', 'Ω 밖 (b) ④a − Ω635'),
    ('out_a_701', 'Ω 밖 (a) ④ − Ω701'),
    ('out_b_701', 'Ω 밖 (b) ④a − Ω701'),
    ('unins_1098', '④b 중 입력 1098 (FW_E 입구)'),
    ('unins_1099', '④b 중 입력 1099 (FW_W 입구)'),
    ('unins_urban', '④b 중 도시 입력 (1098·1099 밖)'),
]
# codex 64cf-s29 joint - NC, 0-8100, codex convention (EV metrics_0_8100.csv via VERIFY v1; 4b/4/out(a) = VT 2.2 estimate)
CODEX = {'Omega701': '−494.66', 'Omega701_minus_west': '−498.00', 'urban_roads': '−294.56', 'offramps701': '−15.36',
         'onramps_E': '+85.02', 'onramps_W': '+10.56', 'FW_E7': '−283.65', 'FW_W_main': '+3.34', 'local19': '−156.58',
         'M4a': '−448.99', 'out_b_701': '+45.67', 'M4b': '≈ −214.0 (−204.0 ~ −223.9, 추정)',
         'M4': '≈ −663.0 (−653.0 ~ −672.9, 추정)', 'out_a_701': '≈ −168.4 (−158.4 ~ −178.3, 추정)',
         'Omega635': '모름 (codex 미산출)', 'd701_635': '모름', 'out_a_635': '모름', 'out_b_635': '모름',
         'unins_1098': '모름 (raw §4-5)', 'unins_1099': '모름 (raw §4-5)', 'unins_urban': '모름 (raw §4-5)'}


def val(m, k):
    if k == 'd701_635':
        return m['Omega701'] - m['Omega635']
    return m[k]


def f1(x):
    s = '%+.1f' % x
    return s.replace('-', '−')


def lv(x):
    return ('%.1f' % x).replace('-', '−')


def key(tag, cw, u='U9'):
    return '%s|%s|%s' % (tag, cw, u)


def pair(p, s, cw, u='U9'):
    return D['pairs']['%s|s%d|%s|%s' % (p, s, cw, u)]


out = {}
# ------------------------------------------------------------------ verification vs V-A report numbers (ours 0-9000)
MAP = [('M1', 'FW_E7'), ('M2', 'local19'), ('M3', 'Omega635'), ('M4a', 'M4a'), ('M4b', 'M4b'), ('M4', 'M4'),
       ('OUT_a', 'out_a_635'), ('OUT_b', 'out_b_635'), ('unins_1098', 'unins_1098'), ('unins_1099', 'unins_1099'),
       ('unins_other', 'unins_urban')]
ver_rows, maxabs = [], {}
for u in ('U6VA', 'U9', 'U6J1'):
    for s in SEEDS:
        for arm in ('va', 'j1', 'nc3'):
            tag = '%s_s%d' % (arm, s)
            k_old = '%s|%s' % (u, tag)
            if k_old not in VAM['per_run']:
                continue
            old = VAM['per_run'][k_old]['full']
            new = D['table'][key(tag, 'ours_9000', u)]
            for a, b in MAP:
                dd = new[b] - old[a]
                maxabs[a] = max(maxabs.get(a, 0.0), abs(dd))
                ver_rows.append((u, tag, a, old[a], new[b], dd))
with io.open(os.path.join(HERE, 'verify_vs_va_report.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['union', 'run', 'va_metric', 'va_report_value', 'this_tool', 'diff'])
    for r in ver_rows:
        w.writerow(r)
lines = ['| V-A 보고 지표 | 대조 칸 수 | 최대 |이 도구 − V-A 보고| (veh·h) |', '|---|---:|---:|']
for a, _ in MAP:
    n = sum(1 for r in ver_rows if r[2] == a)
    lines.append('| %s | %d | %.4f |' % (a, n, maxabs[a]))
out['T_VERIFY'] = '\n'.join(lines)
# Omega635 level check table (report rounding 0.1)
lines = ['| 런 | Ω635 V-A 보고 (`va_metrics.json`) | Ω635 이 도구 | 차 | ④a 보고 | ④a 이 도구 | 차 | ④ [U9] 보고 → 이 도구 | Ω 밖 (a) [U9] 보고 → 이 도구 |', '|---|---:|---:|---:|---:|---:|---:|---|---|']
for s in SEEDS:
    for arm, nm in (('nc3', 'NC3'), ('j1', 'J1'), ('va', 'V-A')):
        tag = '%s_s%d' % (arm, s)
        old = VAM['per_run']['U9|' + tag]['full']
        new = D['table'][key(tag, 'ours_9000')]
        lines.append('| %s v3c3-s%d | %.4f | %.4f | %+.4f | %.4f | %.4f | %+.4f | %.4f → %.4f | %.4f → %.4f |' % (
            nm, s, old['M3'], new['Omega635'], new['Omega635'] - old['M3'], old['M4a'], new['M4a'],
            new['M4a'] - old['M4a'], old['M4'], new['M4'], old['OUT_a'], new['out_a_635']))
out['T_OMEGA635'] = '\n'.join(lines)
# pair A report reproduction (U6VA) for headline rows
lines = ['| 짝 · 합집합 | 지표 | s31 (보고 → 이 도구) | s41 | s43 |', '|---|---|---|---|---|']
for pname, u, p_old in (('V-A − NC3', 'U6VA', 'A'), ('V-A − J1', 'U9', 'B'), ('J1 − NC3', 'U9', 'Bp')):
    for a, b in (('M3', 'Omega635'), ('M4', 'M4'), ('OUT_a', 'out_a_635')):
        cells = []
        for s in SEEDS:
            A, B = {'A': ('va', 'nc3'), 'B': ('va', 'j1'), 'Bp': ('j1', 'nc3')}[p_old]
            o = VAM['per_run']['%s|%s_s%d' % (u, A, s)]['full'][a] - VAM['per_run']['%s|%s_s%d' % (u, B, s)]['full'][a]
            n = D['table'][key('%s_s%d' % (A, s), 'ours_9000', u)][b] - D['table'][key('%s_s%d' % (B, s), 'ours_9000', u)][b]
            cells.append('%s → %s' % (f1(o), f1(n)))
        lines.append('| %s [%s] | %s | %s |' % (pname, u, a, ' | '.join(cells)))
out['T_PAIR_REPRO'] = '\n'.join(lines)
# ------------------------------------------------------------------ level tables
for cw, label in (('ours_9000', '우리 꼴 0–9000 s'), ('codex_8100', 'codex 꼴 0–8100 s'),
                  ('ours_8100', '우리 꼴 0–8100 s'), ('codex_9000', 'codex 꼴 0–9000 s')):
    hdr = ['지표 (veh·h, ' + label + ')']
    for s in SEEDS:
        hdr += ['NC3 s%d' % s, 'J1 s%d' % s, 'V-A s%d' % s]
    lines = ['| ' + ' | '.join(hdr) + ' |', '|---' + '|---:' * 9 + '|']
    for k, nm in ROWS:
        cells = []
        for s in SEEDS:
            for arm in ('nc3', 'j1', 'va'):
                cells.append(lv(val(D['table'][key('%s_s%d' % (arm, s), cw)], k)))
        lines.append('| %s | %s |' % (nm, ' | '.join(cells)))
    out['T_LEVEL_' + cw] = '\n'.join(lines)
# ------------------------------------------------------------------ pair tables
for cw, label, with_codex in (('ours_9000', '우리 꼴 0–9000 s', False), ('codex_8100', 'codex 꼴 0–8100 s', True),
                              ('ours_8100', '우리 꼴 0–8100 s', True), ('codex_9000', 'codex 꼴 0–9000 s', False)):
    hdr = ['d (veh·h, %s, U9)' % label]
    for p in ('V-A − NC3', 'J1 − NC3', 'V-A − J1'):
        hdr += ['%s s%d' % (p, s) for s in SEEDS]
    if with_codex:
        hdr.append('codex 64cf-s29 joint − NC (다른 망, 한 시드, v3c3 와 짝 아님; codex 꼴 0–8100)')
    lines = ['| ' + ' | '.join(hdr) + ' |', '|---' + '|---:' * 9 + ('|---' if with_codex else '') + '|']
    for k, nm in ROWS:
        cells = []
        for p in ('VA-NC3', 'J1-NC3', 'VA-J1'):
            for s in SEEDS:
                m = pair(p, s, cw)
                cells.append(f1(m['Omega701'] - m['Omega635'] if k == 'd701_635' else m[k]))
        if with_codex:
            cells.append(CODEX.get(k, ''))
        lines.append('| %s | %s |' % (nm, ' | '.join(cells)))
    out['T_PAIR_' + cw] = '\n'.join(lines)
# ------------------------------------------------------------------ convention gap
lines = ['| 지표 | 수준값 최대 |codex − 우리| 0–9000 | 수준값 0–8100 | 짝 d 최대 |codex − 우리| 0–9000 | 짝 d 0–8100 |',
         '|---|---:|---:|---:|---:|']
for k, nm in ROWS:
    lvl = {}
    dd = {}
    for T in (9000, 8100):
        lvl[T] = max(abs(val(D['table'][key('%s_s%d' % (a, s), 'codex_%d' % T)], k) -
                         val(D['table'][key('%s_s%d' % (a, s), 'ours_%d' % T)], k)) for a in ('va', 'j1', 'nc3') for s in SEEDS)
        dd[T] = 0.0
        for p in ('VA-NC3', 'J1-NC3', 'VA-J1'):
            for s in SEEDS:
                mc, mo = pair(p, s, 'codex_%d' % T), pair(p, s, 'ours_%d' % T)
                vc = mc['Omega701'] - mc['Omega635'] if k == 'd701_635' else mc[k]
                vo = mo['Omega701'] - mo['Omega635'] if k == 'd701_635' else mo[k]
                dd[T] = max(dd[T], abs(vc - vo))
    lines.append('| %s | %.2f | %.2f | %.2f | %.2f |' % (nm, lvl[9000], lvl[8100], dd[9000], dd[8100]))
out['T_CONV_GAP'] = '\n'.join(lines)
# ------------------------------------------------------------------ U6VA vs U9 for pair A (union-dependent rows)
lines = ['| V-A − NC3, 우리 꼴 0–9000 | 합집합 | s31 | s41 | s43 |', '|---|---|---:|---:|---:|']
for k, nm in (('M4b', '④b'), ('M4', '④'), ('out_a_635', 'Ω 밖 (a) Ω635'), ('out_a_701', 'Ω 밖 (a) Ω701'),
              ('unins_urban', '④b 도시 입력')):
    for u in ('U6VA', 'U9'):
        lines.append('| %s | %s | %s |' % (nm, u, ' | '.join(f1(pair('VA-NC3', s, 'ours_9000', u)[k]) for s in SEEDS)))
out['T_UNION'] = '\n'.join(lines)
# ------------------------------------------------------------------ csv of all pairs and levels
with io.open(os.path.join(HERE, 'omega701_pairs.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['pair', 'seed', 'convention_window', 'union'] + [k for k, _ in ROWS])
    for kk, m in sorted(D['pairs'].items()):
        p, s, cw, u = kk.split('|')
        w.writerow([p, s, cw, u] + ['%.6f' % (m['Omega701'] - m['Omega635'] if k == 'd701_635' else m[k]) for k, _ in ROWS])
with io.open(os.path.join(HERE, 'omega701_levels.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['run', 'convention_window', 'union'] + [k for k, _ in ROWS])
    for kk, m in sorted(D['table'].items()):
        tag, cw, u = kk.split('|')
        w.writerow([tag, cw, u] + ['%.6f' % val(m, k) for k, _ in ROWS])
with io.open(os.path.join(HERE, 'tables.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print('ok', {k: len(v) for k, v in out.items()}, 'maxabs', {k: round(v, 5) for k, v in maxabs.items()})
