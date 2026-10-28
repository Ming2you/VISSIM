# b_report_tables.py - B analysis tables per COMPARE_RULE_B (f902f7f0...) s3-s6, from the pinned tools' outputs only.
# New 2026-10-27 KST. Read only: never opens a FZP, never writes outside work/b. No percentages, no verdict words.
# Inputs: V = work/vhr_b/v3c3_all.json, O = work/omega_b/omega701_v3c3.json, P = work/omega_b/omega701_per_link.csv,
#         top66 = work/omega_b/top66.json, M = work/rawcheck_b/s<s>/metrics_out.json, first_<tag>.json (vhr_b/scan_out),
#         B native_network_performance.json, walltimes_out.json, dec_s<s>.json, ramp_fc_out.json, b_concurrency.json,
#         b_run_summary_s<s>.json; originals work/vhr/v3c3_all.json (bf26275e...) and work/omega/omega701_v3c3.json (fa6d24cf...) for X3.
# Outputs: work/b/b_report_tables.json, work/b/b_report_tables.md
import csv, hashlib, json, os, sys
from collections import Counter

CH = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff'
CW = CH + '/work'
R = 'D:/VISSIM_runs/20261026_codex_b_v3c3'
SEEDS = (31, 41, 43)
FORMS = ('ours_9000', 'codex_8100')
FORM_LABEL = {'ours_9000': '우리 꼴 [0, 9000] s', 'codex_8100': 'codex 꼴 [0, 8100] s (시각축 사다리꼴)'}
CAVEAT = ('단서(COMPARE_RULE_B §4-10): 64cf-s29 로 맞춘 D 부류 계수와 64cf 유도 codex 계약 11개를 v3c3 에 그대로 얹은 런'
          '(계수 불일치와 기구 효과 없음을 가를 수 없음, PRE_B §7).')
PREFIX_DIFF = {31: True, 41: True, 43: False}   # B_RUNS s7: lf_sha_le_895_1 B != NC3 for s31, s41 (0.1 s row only)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jl(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def fmt(x, nd=1):
    if x is None:
        return '없음'
    if isinstance(x, str):
        return x
    v = round(x, nd)
    if v == 0:
        v = 0.0
    s = ('%.' + str(nd) + 'f') % abs(v)
    return ('+' if v > 0 else ('−' if v < 0 else '±')) + s


def lvl(x, nd=1):
    return '없음' if x is None else (('%.' + str(nd) + 'f') % x)


V = jl(CW + '/vhr_b/v3c3_all.json')
O = jl(CW + '/omega_b/omega701_v3c3.json')
VC = {(c['form'], c['pair'], c['seed'], c['metric']): c['mine'] for c in V['cells']}
inputs_sha = {p: sha(p) for p in (CW + '/vhr_b/v3c3_all.json', CW + '/omega_b/omega701_v3c3.json',
                                   CW + '/omega_b/omega701_per_link.csv', CW + '/omega_b/top66.json',
                                   *[CW + '/rawcheck_b/s%d/metrics_out.json' % s for s in SEEDS])}


def vget(form, pairname, s, metric):
    """pairname 'BN' = B - NC3 (V j1-nc3), 'BV' = B - V-A (-1 x V va-j1)."""
    if pairname == 'BN':
        return VC[(form, 'j1-nc3', s, metric)]
    return -VC[(form, 'va-j1', s, metric)]


def oget(form, pairname, s, metric):
    if pairname == 'BN':
        return O['pairs']['J1-NC3|s%d|%s|U6J1' % (s, form)][metric]
    return -O['pairs']['VA-J1|s%d|%s|U9' % (s, form)][metric]


ROWS = [
    ('O635', 'Ω635 (우리 목적 영역 635링크)', lambda f, p, s: vget(f, p, s, 'O635'), 'V O635'),
    ('O701', 'Ω701 (codex 목적 영역 701링크)', lambda f, p, s: vget(f, p, s, 'O701'), 'V O701'),
    ('O701m635', 'Ω701 − Ω635 (더한 66링크)', lambda f, p, s: vget(f, p, s, 'O701') - vget(f, p, s, 'O635'), '[계산] V O701 − V O635'),
    ('A4a', '④a 망 전체 링크', lambda f, p, s: vget(f, p, s, 'A4a'), 'V A4a'),
    ('U', '④b 미삽입 (주 값, 첫 관측 차분)', lambda f, p, s: vget(f, p, s, 'U'), 'V U'),
    ('A4', '④ = ④a + ④b', lambda f, p, s: vget(f, p, s, 'A4'), 'V A4'),
    ('outa701', 'Ω 밖 (a) Ω701 기준 = ④ − Ω701', lambda f, p, s: vget(f, p, s, 'outa701'), 'V outa701'),
    ('outb701', 'Ω 밖 (b) Ω701 기준 = ④a − Ω701', lambda f, p, s: vget(f, p, s, 'outb701'), 'V outb701'),
    ('outa635', 'Ω 밖 (a) Ω635 기준 = ④ − Ω635', lambda f, p, s: vget(f, p, s, 'outa635'), 'V outa635'),
    ('outb635', 'Ω 밖 (b) Ω635 기준 = ④a − Ω635', lambda f, p, s: vget(f, p, s, 'A4a') - vget(f, p, s, 'O635'), '[계산] V A4a − V O635'),
    ('FWE7', '① FW_E 본선 7링크', lambda f, p, s: vget(f, p, s, 'FWE7'), 'V FWE7'),
    ('local19', '② 동측 국소 19링크', lambda f, p, s: oget(f, p, s, 'local19'), 'O local19'),
    ('u1098', '④b 중 입력 1098 (FW_E 입구, 첫 관측 링크 74)', lambda f, p, s: vget(f, p, s, 'u1098'), 'V u1098'),
    ('u1099', '④b 중 입력 1099 (FW_W 입구, 첫 관측 링크 26)', lambda f, p, s: vget(f, p, s, 'u1099'), 'V u1099'),
    ('ucity', '④b 중 도시 입력 (그 밖 첫 관측 링크)', lambda f, p, s: vget(f, p, s, 'ucity'), 'V ucity'),
    ('M4b', '참고: ④b stage-1 재구성 (NC3 앵커)', lambda f, p, s: oget(f, p, s, 'M4b'), 'O M4b (B − NC3: U6J1, B − V-A: U9)'),
    ('r1098', '참고: 재구성 중 입력 1098', lambda f, p, s: oget(f, p, s, 'unins_1098'), 'O unins_1098'),
    ('r1099', '참고: 재구성 중 입력 1099', lambda f, p, s: oget(f, p, s, 'unins_1099'), 'O unins_1099'),
    ('rurban', '참고: 재구성 중 도시 입력', lambda f, p, s: oget(f, p, s, 'unins_urban'), 'O unins_urban'),
]

res = {'inputs_sha256': inputs_sha, 'tables': {}, 'checks': {}, 'levels': {}, 'lines': {}}
md = []


def colname(p, s):
    return ('B − NC3 v3c3-s%d' % s + ('†' if PREFIX_DIFF[s] else '')) if p == 'BN' else ('B − V-A v3c3-s%d' % s)


for p, pl in (('BN', '주 표 T1: B − NC3 (같은 시드)'), ('BV', '보조 표 T2: B − V-A (같은 시드, V-A − B 의 부호를 뒤집음)')):
    for f in FORMS:
        key = '%s|%s' % (p, f)
        tab = {}
        md.append('#### %s — %s\n' % (pl, FORM_LABEL[f]))
        md.append('- 시드 3: v3c3-s31·s41·s43 (시드끼리 평균 내지 않음). veh·h. ' + CAVEAT)
        if p == 'BN':
            md.append('- † = 900 s 전 접두가 NC3 와 다름(COMPARE_RULE_B §1). 다른 것은 0.1 s 프레임 1행뿐(B_RUNS §7).')
        md.append('')
        md.append('| 줄 | ' + ' | '.join(colname(p, s) for s in SEEDS) + ' | 출처 |')
        md.append('|---|' + '---:|' * len(SEEDS) + '---|')
        for rk, rl, fn, src in ROWS:
            vals = [fn(f, p, s) for s in SEEDS]
            tab[rk] = dict(zip(['s%d' % s for s in SEEDS], vals))
            bold = rk in ('O701', 'U', 'A4', 'outa701')
            cells = [('**%s**' % fmt(v)) if bold else fmt(v) for v in vals]
            md.append('| %s | %s | %s |' % (rl, ' | '.join(cells), src))
        md.append('')
        res['tables'][key] = tab

# ------------------------------------------------------------------ T0 levels (reference)
md.append('#### 참고 표 T0: 수준값 (O `table`, 합집합 U6J1; 링크 지표는 합집합과 무관) — veh·h\n')
md.append('- ' + CAVEAT)
md.append('')
LV = [('Omega635', 'Ω635'), ('Omega701', 'Ω701'), ('M4a', '④a'), ('FW_E7', '①'), ('local19', '②'), ('urban_roads', '도시도로 (codex 분할)'),
      ('M4b', '④b 재구성 (참고, U6J1)')]
for f in FORMS:
    md.append('%s:\n' % FORM_LABEL[f])
    md.append('| 줄 | ' + ' | '.join('%s v3c3-s%d' % (r, s) for s in SEEDS for r in ('B', 'NC3', 'V-A')) + ' |')
    md.append('|---|' + '---:|' * 9)
    for mk, ml in LV:
        row = []
        for s in SEEDS:
            for tg in ('j1', 'nc3', 'va'):
                v = O['table']['%s_s%d|%s|U6J1' % (tg, s, f)][mk]
                res['levels']['%s_s%d|%s|%s' % (tg, s, f, mk)] = v
                row.append(lvl(v))
        md.append('| %s | %s |' % (ml, ' | '.join(row)))
    md.append('')
nat = {}
for s in SEEDS:
    d = jl('%s/s%d/sdmpc/native_network_performance.json' % (R, s))
    nat[s] = {'DelayLatent_veh_h': d['native']['DelayLatent'] / 3600.0, 'to_sec': d['to_sec'], 'from_sec': d['from_sec'],
              'TravTmTot_veh_h': d['native']['TravTmTot'] / 3600.0, 'DemandLatent': d['native']['DemandLatent'],
              'VehArr': d['native']['VehArr'], 'VehAct': d['native']['VehAct']}
res['levels']['native_B'] = nat
md.append('- ④b 수준값 B (native `DelayLatent` / 3600, from_sec 0, to_sec 9000): ' + ' · '.join(
    'v3c3-s%d %.1f veh·h' % (s, nat[s]['DelayLatent_veh_h']) for s in SEEDS) + '. NC3·V-A 에는 이 파일이 없어 짝 차는 내지 않음.')
md.append('')

# ------------------------------------------------------------------ checks
# X1: V vs O same pair/form
x1 = []
for p in ('BN', 'BV'):
    for f in FORMS:
        for s in SEEDS:
            for vm, om in (('O701', 'Omega701'), ('O635', 'Omega635'), ('FWE7', 'FW_E7'), ('A4a', 'M4a')):
                a, b = vget(f, p, s, vm), oget(f, p, s, om)
                x1.append({'pair': p, 'form': f, 'seed': s, 'metric': vm, 'V': a, 'O': b, 'diff': a - b})
res['checks']['X1_max_abs'] = max(abs(r['diff']) for r in x1)
res['checks']['X1_over_0_05'] = [r for r in x1 if abs(r['diff']) > 0.05]
# X2: codex-form urban roads, M vs O
M = {s: jl(CW + '/rawcheck_b/s%d/metrics_out.json' % s) for s in SEEDS}
x2 = []
for s in SEEDS:
    m = M[s]['codex_rule']['joint']['urban_roads'] - M[s]['codex_rule']['nc']['urban_roads']
    o = oget('codex_8100', 'BN', s, 'urban_roads')
    x2.append({'seed': s, 'M': m, 'O': o, 'diff': m - o})
res['checks']['X2'] = x2
# X3: V va-nc3 cells and O VA-NC3|*|*|U6VA equal to the originals
Vo = jl(CW + '/vhr/v3c3_all.json')
Oo = jl(CW + '/omega/omega701_v3c3.json')
va = {(c['form'], c['seed'], c['metric']): c['mine'] for c in Vo['cells'] if c['pair'] == 'va-nc3'}
vb = {(c['form'], c['seed'], c['metric']): c['mine'] for c in V['cells'] if c['pair'] == 'va-nc3'}
x3v = sum(1 for k in va if va[k] != vb.get(k)) + len(set(va) ^ set(vb))
x3o_max, x3o_n = 0.0, 0
for k, v in Oo['pairs'].items():
    if k.startswith('VA-NC3|') and k.endswith('|U6VA'):
        nv = O['pairs'][k]
        for mk in v:
            x3o_max = max(x3o_max, abs(v[mk] - nv[mk])); x3o_n += 1
res['checks']['X3'] = {'orig_V_sha': sha(CW + '/vhr/v3c3_all.json'), 'orig_O_sha': sha(CW + '/omega/omega701_v3c3.json'),
                       'V_cells': len(va), 'V_cells_differing': x3v, 'O_values': x3o_n, 'O_max_abs_diff': x3o_max,
                       'pass': x3v == 0 and x3o_max <= 1e-6 and x3o_n > 0}
# X4: link 66 ours, P vs top66
P = {}
with open(CW + '/omega_b/omega701_per_link.csv', encoding='utf-8') as fh:
    for r in csv.DictReader(fh):
        if r['link'] == '66':
            P[(r['run'], r['convention_window'])] = float(r['veh_h'])
t66 = jl(CW + '/omega_b/top66.json')
row66 = [r for r in t66['rows'] if r[0] == 66][0]
x4 = []
for s in SEEDS:
    pv = P[('j1_s%d' % s, 'ours_9000')] - P[('nc3_s%d' % s, 'ours_9000')]
    tv = row66[1]['J1-NC3|s%d' % s]
    x4.append({'seed': s, 'P': pv, 'top66': tv, 'diff': pv - tv})
res['checks']['X4'] = x4
# X5: arrivals (first-observed vehicles <= 9000 s) and input 1099 arrivals (link 26 first obs + .err remain)
F = {t: jl(CW + '/vhr_b/scan_out/first_%s.json' % t) for t in ['%s_s%d' % (a, s) for s in SEEDS for a in ('j1', 'nc3', 'va')]}


def n26(t, W=9000):
    return sum(k for tt, k in F[t]['by_cat'].get('26', {}).items() if int(tt) / 10 <= W)


def n74(t, W=9000):
    return sum(k for tt, k in F[t]['by_cat'].get('74', {}).items() if int(tt) / 10 <= W)


x5 = {}
for s in SEEDS:
    row = {}
    for tg in ('j1', 'nc3', 'va'):
        t = '%s_s%d' % (tg, s)
        rem = O['remains'].get(t, {})
        row[tg] = {'arrivals_first_obs_9000': V['arrival_totals_9000'][t], 'first_obs_74': n74(t), 'first_obs_26': n26(t),
                   'remain_1099': rem.get('1099', 0), 'arr_1099': n26(t) + rem.get('1099', 0), 'remains_all': rem}
    x5['s%d' % s] = row
res['checks']['X5'] = x5
res['checks']['removals'] = O['removals']
res['checks']['unions'] = O['unions']
res['checks']['sets'] = O['checks']['sets']
res['checks']['vs_stage1_scans_summary'] = {k: {kk: v[kk] for kk in ('omega635_diff', 'all_diff', 'per_link_max_abs_diff_vs_rounded_bins',
                                                                       'uninserted_total_old', 'uninserted_total_new')}
                                            for k, v in O['checks']['vs_stage1_scans'].items()}
res['checks']['B_scan_meta'] = {t: {k: O['scan_meta'][t][k] for k in ('rows', 'frames', 'first_sec', 'last_sec', 'skip_rows_0p10', 'fzp_sha256', 'vehicles_seen_ours')}
                                for t in O['scan_meta'] if t.startswith('j1_')}

# ------------------------------------------------------------------ s4 lines
# 4-1 link 66
L66 = {}
for f in FORMS:
    for s in SEEDS:
        L66['BN|%s|s%d' % (f, s)] = P[('j1_s%d' % s, f)] - P[('nc3_s%d' % s, f)]
        L66['BV|%s|s%d' % (f, s)] = P[('j1_s%d' % s, f)] - P[('va_s%d' % s, f)]
        for tg in ('j1', 'nc3', 'va'):
            L66['level|%s|%s_s%d' % (f, tg, s)] = P[('%s_s%d' % (tg, s), f)]
res['lines']['link66'] = L66
# 4-2 urban roads
UR = {}
for s in SEEDS:
    for rule, rk in (('codex', 'codex_rule'), ('ours', 'alt_rule')):
        for mk in ('urban_roads', 'onramps_E', 'onramps_W'):
            UR['BN|codex_8100|%s|%s|s%d' % (rule, mk, s)] = M[s][rk]['joint'][mk] - M[s][rk]['nc'][mk]
            UR['level|codex_8100|%s|%s|B|s%d' % (rule, mk, s)] = M[s][rk]['joint'][mk]
            UR['level|codex_8100|%s|%s|NC3|s%d' % (rule, mk, s)] = M[s][rk]['nc'][mk]
    UR['BN|ours_9000|codex|urban_roads|s%d' % s] = oget('ours_9000', 'BN', s, 'urban_roads')
    UR['BV|ours_9000|codex|urban_roads|s%d' % s] = oget('ours_9000', 'BV', s, 'urban_roads')
    UR['BV|codex_8100|codex|urban_roads|s%d' % s] = oget('codex_8100', 'BV', s, 'urban_roads')
    UR['upstream|s%d' % s] = {'B': M[s]['upstream']['joint'], 'NC3': M[s]['upstream']['nc']}
res['lines']['urban'] = UR
# 4-5 meter green / rate distribution, T in [900, 8850]
MT = {}
VS = {}
for s in SEEDS:
    d = [x for x in jl(CW + '/rawcheck_b/dec_s%d.json' % s) if 900 <= x['t'] <= 8850]
    g, r = {}, {}
    for x in d:
        for k, v in x['rm_green'].items():
            g.setdefault(k, Counter())[v] += 1
        for k, v in x['rm_out'].items():
            r.setdefault(k, Counter())[v] += 1
    MT['s%d' % s] = {'n': len(d), 'green': {k: sorted(c.items()) for k, c in g.items()}, 'rate': {k: sorted(c.items()) for k, c in r.items()}}
    vv = Counter(v for x in d for v in x['vsl_out'])
    VS['s%d' % s] = {'n': len(d), 'values': sorted(vv.items()), 'non110': [(x['t'], x['vsl_out']) for x in d if any(v != 110.0 for v in x['vsl_out'])],
                     'controller_status': sorted(Counter(x['controller_status'] for x in d).items()),
                     'selection_status': sorted(Counter(x['selection_status'] for x in d).items())}
res['lines']['meter'] = MT
res['lines']['vsl'] = VS
# 4-6 wall times, 4-7 holds
WT = {}
CC = jl(CW + '/b/b_concurrency.json')
for s in SEEDS:
    w = jl(CW + '/rawcheck_b/s%d/walltimes_out.json' % s)['joint']
    per = w['per_decision']
    S = jl(CW + '/b/b_run_summary_s%d.json' % s)['runlog']
    WT['s%d' % s] = {'n_ge900': w['n_decisions_ge900'], 'wall': w['wall'], 'budget_wall': w['budget_wall'], 'results': w['results'],
                     'gt1500': sum(1 for x in per if x[1] > 1500), 'gt2400': sum(1 for x in per if x[1] > 2400),
                     'held': w['held'], 'hold_attempts': S['hold_attempts'], 'held_previous': S['held_previous'],
                     'DECISIONS': {k: S[k] for k in ('DECISIONS_OK', 'DECISIONS_FAILED', 'DECISIONS_HELD_PREVIOUS', 'DECISIONS_HELD_ON_EXCEPTION')},
                     'concurrency': CC['summary']['s%d' % s],
                     'top5': sorted(per, key=lambda x: -x[1])[:5]}
res['lines']['wall'] = WT
# 4-8 ramp arrival forecasts
RF = {}
for s in SEEDS:
    rows = jl(CW + '/rawcheck_b/s%d/ramp_fc_out.json' % s)
    rows = [x for x in rows if 900 <= x[0] <= 8850]
    vals = [x[1] for x in rows if x[1] is not None]
    vs = sorted(vals)
    RF['s%d' % s] = {'n': len(rows), 'n_logged': len(vals), 'min': min(vals), 'max': max(vals), 'median': vs[len(vs) // 2] if len(vs) % 2 else (vs[len(vs) // 2 - 1] + vs[len(vs) // 2]) / 2,
                     'mean': sum(vals) / len(vals), 'per_decision': [(x[0], x[1]) for x in rows]}
res['lines']['ramp_fc'] = RF

with open(CW + '/b/b_report_tables.json', 'w', encoding='utf-8') as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)
with open(CW + '/b/b_report_tables.md', 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(md) + '\n')
print('X1 max', res['checks']['X1_max_abs'], 'over0.05', len(res['checks']['X1_over_0_05']))
print('X2', [(r['seed'], round(r['diff'], 6)) for r in x2])
print('X3', res['checks']['X3'])
print('X4', [(r['seed'], r['diff']) for r in x4])
print('X5', json.dumps({s: {t: {k: v for k, v in d.items() if k != 'remains_all'} for t, d in r.items()} for s, r in x5.items()}))
