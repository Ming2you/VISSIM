# b_results_tables.py -- read-only table maker for codex_handoff/B_RESULTS.md (2026-10-27 KST).
# Reads fixed analysis outputs (V, O, P) and prints Markdown tables. Writes nothing but stdout
# and work/b/b_results_tables.json. No VISSIM, no FZP scan.
import csv, json, sys, hashlib
from collections import defaultdict

CW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
V_PATH = CW + '/vhr_b/v3c3_all.json'
O_PATH = CW + '/omega_b/omega701_v3c3.json'
P_PATH = CW + '/omega_b/omega701_per_link.csv'
SEEDS = (31, 41, 43)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


V = json.load(open(V_PATH, encoding='utf-8'))
O = json.load(open(O_PATH, encoding='utf-8'))
P = defaultdict(lambda: defaultdict(dict))  # P[form][run][link]
for r in csv.DictReader(open(P_PATH, encoding='utf-8')):
    P[r['convention_window']][r['run']][int(r['link'])] = float(r['veh_h'])

vcell = {}
for c in V['cells']:
    vcell[(c['form'], c['pair'], c['seed'], c['metric'])] = c['mine']


def v_pair(form, pair, metric):
    """pair in {'B-NC3','VA-NC3','B-VA'}; returns list over seeds."""
    out = []
    for s in SEEDS:
        if pair == 'B-NC3':
            out.append(vcell[(form, 'j1-nc3', s, metric)])
        elif pair == 'VA-NC3':
            out.append(vcell[(form, 'va-nc3', s, metric)])
        else:
            out.append(-vcell[(form, 'va-j1', s, metric)])
    return out


def o_pair(form, pair, key):
    out = []
    for s in SEEDS:
        if pair == 'B-NC3':
            out.append(O['pairs']['J1-NC3|s%d|%s|U6J1' % (s, form)][key])
        elif pair == 'VA-NC3':
            out.append(O['pairs']['VA-NC3|s%d|%s|U6VA' % (s, form)][key])
        else:
            out.append(-O['pairs']['VA-J1|s%d|%s|U9' % (s, form)][key])
    return out


def p_pair(form, pair, link):
    out = []
    for s in SEEDS:
        b = P[form]['j1_s%d' % s][link]
        n = P[form]['nc3_s%d' % s][link]
        v = P[form]['va_s%d' % s][link]
        out.append({'B-NC3': b - n, 'VA-NC3': v - n, 'B-VA': b - v}[pair])
    return out


def f(x):
    r = round(x + 0.0, 1)
    if r == 0:
        return '±0.0'
    return ('+%.1f' % r) if r > 0 else ('\u2212%.1f' % -r)


ROWS = [
    ('Ω701 (codex 목적 영역 701링크)', 'V', 'O701', True),
    ('Ω635 (우리 목적 영역 635링크)', 'V', 'O635', False),
    ('Ω701 − Ω635 (더한 66링크)', 'Vdiff', None, False),
    ('④a 망 전체 링크', 'V', 'A4a', False),
    ('④b 미삽입 (첫 관측 차분)', 'V', 'U', True),
    ('④ = ④a + ④b', 'V', 'A4', True),
    ('Ω 밖 (a) Ω701 기준 = ④ − Ω701', 'V', 'outa701', True),
    ('Ω 밖 (a) Ω635 기준 = ④ − Ω635', 'V', 'outa635', False),
    ('Ω 밖 (b) Ω701 기준 = ④a − Ω701', 'V', 'outb701', False),
    ('① FW_E 본선 7링크', 'V', 'FWE7', False),
    ('② 동측 국소 19링크', 'O', 'local19', False),
    ('④b 중 입력 1098 (FW_E 입구)', 'V', 'u1098', False),
    ('④b 중 입력 1099 (FW_W 입구)', 'V', 'u1099', True),
    ('④b 중 도시 입력', 'V', 'ucity', False),
    ('링크 66 (SC1004 남측)', 'P', 66, False),
    ('도시도로 (codex 분할)', 'O', 'urban_roads', False),
    ('참고·선언 밖: FW_W 본선 (O FW_W_main)', 'O', 'FW_W_main', False),
]
PAIRS = ('B-NC3', 'VA-NC3', 'B-VA')
PAIR_LABEL = {'B-NC3': 'B − NC3', 'VA-NC3': 'V-A − NC3', 'B-VA': 'B − V-A'}
DAG = {('B-NC3', 31): '†', ('B-NC3', 41): '†', ('VA-NC3', 31): '†', ('VA-NC3', 41): '†'}

result = {'inputs_sha256': {'V': sha(V_PATH), 'O': sha(O_PATH), 'P': sha(P_PATH)}, 'tables': {}}


def table(vform, oform, pform, title):
    hdr = '| 줄 (veh·h) | ' + ' | '.join('%s v3c3-s%d%s' % (PAIR_LABEL[p], s, DAG.get((p, s), '')) for p in PAIRS for s in SEEDS) + ' |'
    sep = '|---|' + '---:|' * 9
    lines = ['#### ' + title, '', hdr, sep]
    tab = {}
    for (label, src, key, bold) in ROWS:
        cells = []
        for p in PAIRS:
            if src == 'V':
                vals = v_pair(vform, p, key)
            elif src == 'Vdiff':
                a = v_pair(vform, p, 'O701'); b = v_pair(vform, p, 'O635')
                vals = [x - y for x, y in zip(a, b)]
            elif src == 'O':
                vals = o_pair(oform, p, key)
            else:
                vals = p_pair(pform, p, key)
            tab[(label, p)] = vals
            cells += vals
        txt = [f(x) for x in cells]
        if bold:
            txt = ['**%s**' % t for t in txt]
        lines.append('| %s | %s |' % (label, ' | '.join(txt)))
    result['tables'][title] = {'%s|%s' % k: v for k, v in tab.items()}
    return '\n'.join(lines)


print(table('ours_9000', 'ours_9000', 'ours_9000', 'T1 우리 꼴 [0, 9000] s'))
print()
print(table('codex_8100', 'codex_8100', 'codex_8100', 'T2 codex 꼴 [0, 8100] s'))
print()

# post-hoc per-link levels (ours_9000): meter upstream links/connectors, FW_W entrance
lines = ['#### T5 링크 수준값 (우리 꼴, veh·h) — 데이터 뒤 참고, 선언 밖', '',
         '| 링크 | 뜻 | B / NC3 / V-A v3c3-s31 | v3c3-s41 | v3c3-s43 |', '|---|---|---|---|---|']
LINKS = [(124, 'RM_C10480 상류 링크'), (10480, 'RM_C10480 커넥터'), (70, 'RM_C10639 상류 링크'),
         (10639, 'RM_C10639 커넥터'), (26, 'FW_W 입구 첫 링크(입력 1099 첫 관측)'), (120, 'FW_W 본선(RM_C10482·10646·10644 합류)')]
post = {}
for (L, what) in LINKS:
    cells = []
    for s in SEEDS:
        b = P['ours_9000']['j1_s%d' % s][L]; n = P['ours_9000']['nc3_s%d' % s][L]; v = P['ours_9000']['va_s%d' % s][L]
        post['%d|s%d' % (L, s)] = [b, n, v]
        cells.append('%.1f / %.1f / %.1f' % (b, n, v))
    lines.append('| %d | %s | %s |' % (L, what, ' | '.join(cells)))
result['tables']['T5'] = post
print('\n'.join(lines))

json.dump(result, open(CW + '/b/b_results_tables.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print()
print('inputs', json.dumps(result['inputs_sha256']))
