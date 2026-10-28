# vhr_v3c3_all.py - all 9 v3c3 runs: fresh Ω701/Ω635/①/④a + first-seen ④b differences, vs OMEGA701_V3C3 tables.
import json, re

S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr/scan_out'
B = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff'
mem = json.load(open('D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json', encoding='utf-8'))
O701 = set(map(str, mem['inside_links']))
O635 = set(map(str, json.load(open('D:/VISSIM-merge/sim3-n31-k8/diagnostics/control_area_membership.json', encoding='utf-8'))['inside_links']))
FWE7 = {'74', '10699', '2', '10613', '119', '10702', '24'}
runs = [f'{a}_s{s}' for s in (31, 41, 43) for a in ('va', 'j1', 'nc3')]
L = {}; F = {}
for r in runs:
    d = json.load(open(f'{S}/{r}.json'))
    L[r] = {}
    for form in ('codex_8100', 'ours_9000', 'codex_9000'):
        I = d['integrals'][form]
        L[r][form] = dict(O701=sum(v for l, v in I.items() if l in O701), O635=sum(v for l, v in I.items() if l in O635),
                          FWE7=sum(v for l, v in I.items() if l in FWE7), A4a=sum(I.values()), link66=I.get('66', 0.0))
    F[r] = json.load(open(f'{S}/first_{r}.json'))


def Sint(r, W, cats=None):
    tot = 0.0; n = 0
    for c, dd in F[r]['by_cat'].items():
        if cats and c not in cats:
            continue
        for tt, k in dd.items():
            t = int(tt) / 10
            if t <= W:
                tot += k * (W - t); n += k
    return tot / 3600, n


def dU(a, b, W, cats=None):
    return Sint(b, W, cats)[0] - Sint(a, W, cats)[0]


# OM tables (codex 0-8100 §4.2 lines 220-242; codex 0-9000 A.2 lines 424-446; ours 0-9000 §4.1 lines 191-213)
OM = open(f'{B}/OMEGA701_V3C3.md', encoding='utf-8').read().splitlines()


def num(s):
    s = s.replace('−', '-').replace('+', '').replace(',', '').strip()
    m = re.match(r'^[≈ ]*(-?\d+(?:\.\d+)?)', s)
    return float(m.group(1)) if m else None


def omtab(a, b):
    out = {}
    for l in OM[a - 1:b]:
        if l.startswith('|') and not l.startswith('|---'):
            c = [x.strip() for x in l.strip().strip('|').split('|')]
            out[c[0]] = [num(x) for x in c[1:10]]
    return out


tabs = {'codex_8100': omtab(220, 242), 'codex_9000': omtab(424, 446), 'ours_9000': omtab(191, 213)}
pairs = [('va', 'nc3'), ('j1', 'nc3'), ('va', 'j1')]
col = {(p, s): i for i, (p, s) in enumerate([(p, s) for p in pairs for s in (31, 41, 43)])}
rowname = {'O701': 'Ω701 (codex 목적 영역, 701링크)', 'O635': 'Ω635 (우리 목적 영역, 635링크)', 'FWE7': '① FW_E 본선 7링크', 'A4a': '④a 전체 링크',
           'U': '④b 미삽입 (U9, NC3 앵커)', 'A4': '④ = ④a + ④b', 'outa701': 'Ω 밖 (a) ④ − Ω701', 'outb701': 'Ω 밖 (b) ④a − Ω701', 'outa635': 'Ω 밖 (a) ④ − Ω635',
           'u1098': '④b 중 입력 1098 (FW_E 입구)', 'u1099': '④b 중 입력 1099 (FW_W 입구)', 'ucity': '④b 중 도시 입력 (1098·1099 밖)'}
res = {'arrival_totals_9000': {}, 'cells': [], 'max_abs_diff': {}}
for r in runs:
    res['arrival_totals_9000'][r] = Sint(r, 9000)[1]
for form, W in (('codex_8100', 8100), ('codex_9000', 9000), ('ours_9000', 9000)):
    for (a, b) in pairs:
        for s in (31, 41, 43):
            A, Bn = f'{a}_s{s}', f'{b}_s{s}'
            x, y = L[A][form], L[Bn][form]
            d = {k: x[k] - y[k] for k in x}
            U = dU(A, Bn, W); d['U'] = U; d['A4'] = d['A4a'] + U; d['outa701'] = d['A4'] - d['O701']; d['outb701'] = d['A4a'] - d['O701']
            d['outa635'] = d['A4'] - d['O635']; d['u1098'] = dU(A, Bn, W, {'74'}); d['u1099'] = dU(A, Bn, W, {'26'}); d['ucity'] = dU(A, Bn, W, {'other'})
            for k, rn in rowname.items():
                om = tabs[form].get(rn, [None] * 9)[col[((a, b), s)]]
                res['cells'].append(dict(form=form, pair=f'{a}-{b}', seed=s, metric=k, mine=round(d[k], 3), om=om, diff=(None if om is None else round(d[k] - om, 2))))
for c in res['cells']:
    key = (c['form'], c['metric'])
    if c['diff'] is not None:
        res['max_abs_diff'][str(key)] = max(res['max_abs_diff'].get(str(key), 0), abs(c['diff']))
json.dump(res, open(f'{S}/../v3c3_all.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('arrivals', res['arrival_totals_9000'])
for k, v in sorted(res['max_abs_diff'].items()):
    print(k, v)
print('--- codex_8100 U/A4/outa701 per pair/seed (mine vs OM)')
for c in res['cells']:
    if c['form'] == 'codex_8100' and c['metric'] in ('U', 'A4', 'outa701', 'O701', 'FWE7'):
        print(c['pair'], c['seed'], c['metric'], c['mine'], c['om'], c['diff'])
