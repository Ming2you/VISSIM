# -*- coding: utf-8 -*-
"""fo_tables.py - FO comparison tables (COMPARE_RULE_FO s3-s6; 2026-10-27 KST, D-K9-113). Read-only. No FZP, no VISSIM.

Derived from codex_handoff/work/b/b_results_tables.py (065878dd..., the B_RESULTS table maker): same row list, same rounding
(one decimal, sign shown), same sources V/O/P (+ M for the codex-form urban roads), one table per form.
Pairs (same seed, never averaged): FO - NC3 (main), B - FO, FO - V-A.
  FO - NC3 : FO outputs   V j1-nc3 | O J1-NC3|s|form|U6J1 | P j1 - nc3 | M codex_rule.joint - codex_rule.nc (FO metrics, codex form)
  FO - V-A : FO outputs   -V va-j1 | -O VA-J1|s|form|U9 | P j1 - va
  B - FO   : [계산] (B - NC3 from the pinned B outputs) - (FO - NC3); P: B j1 - FO j1; M: B joint - FO joint
             (every line is linear in the run quantities with the same NC3 anchor; first-observation difference included)
Daggers: a pair gets '†' when the two runs' FZP prefixes (lf_sha_le_895_1 of the vhr scans) differ (COMPARE_RULE_B s1).
Checks: X1 [보고] V vs O for dOmega701, dOmega635, d(1), d4a <= 0.05 (FO-NC3, FO-V-A); X2 [보고] codex-form urban roads M vs O
<= 0.05; X3 [STOP] the FO tools' V-A - NC3 cells == the B outputs' V-A - NC3 cells (V exact, O |d| <= 1e-6); X3b [STOP] NC3 and
V-A scan files of vhr_fo == vhr_b except 'scan_sec'; X4 [보고] link 66 ours form P == top66.json (|d| <= 1e-6); X5 [보고] arrivals.
usage: python -B fo_tables.py <out_prefix> [--selftest]   (writes <out_prefix>.json and <out_prefix>.md)
  --selftest: the FO sources are pointed at the B outputs (FO := B): FO-NC3 must equal B-NC3, B-FO must be 0, FO-V-A = B-V-A.
"""
import csv, hashlib, json, os, sys
from collections import defaultdict

CW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
SEEDS = (31, 41, 43)
B_SRC = {'V': (CW + '/vhr_b/v3c3_all.json', 'f982fbff497645c7155d53e9c272388e5136641f5bb9580bc8f3a8c606ba251a'),
         'O': (CW + '/omega_b/omega701_v3c3.json', '823f9dccf4fa211fc13e11c3081e6729ebe6f98a97ef127547bb5239b6064f2e'),
         'P': (CW + '/omega_b/omega701_per_link.csv', 'c4f7a3a3abc87d4834c48fb01b60d7fba76a2b9fc976a98b571a3f0715adac56'),
         'T66': (CW + '/omega_b/top66.json', 'a4e47a48ab9e4624751f8dd0a529dff97e32215b46156bfbf731d99fc749367e'),
         'M31': (CW + '/rawcheck_b/s31/metrics_out.json', '74a067718717cd421ec5bde6587143d1da5557f6b564ac6b3c88976ca0973aaf'),
         'M41': (CW + '/rawcheck_b/s41/metrics_out.json', 'b9e41f9271b262bf755560ad9007fdf699a9da627cda5e84bcea4a4ea7240cb0'),
         'M43': (CW + '/rawcheck_b/s43/metrics_out.json', '9d3e4364d7027f1b6aa606f532b14cf0d06913626e869b8cd7e092f9004984d6')}
FO_SRC = {'V': (CW + '/vhr_fo/v3c3_all.json', None), 'O': (CW + '/omega_fo/omega701_v3c3.json', None),
          'P': (CW + '/omega_fo/omega701_per_link.csv', None), 'T66': (CW + '/omega_fo/top66.json', None),
          'M31': (CW + '/rawcheck_fo/s31/metrics_out.json', None), 'M41': (CW + '/rawcheck_fo/s41/metrics_out.json', None),
          'M43': (CW + '/rawcheck_fo/s43/metrics_out.json', None)}
SCAN_B, SCAN_FO = CW + '/vhr_b/scan_out', CW + '/vhr_fo/scan_out'
ROWS = [
    ('Ω701 (codex 목적 영역 701링크)', 'V', 'O701', True),
    ('Ω635 (우리 목적 영역 635링크)', 'V', 'O635', False),
    ('Ω701 − Ω635 (더한 66링크)', 'Vdiff', None, False),
    ('④a 망 전체 링크', 'V', 'A4a', False),
    ('④b 미삽입 (첫 관측 차분)', 'V', 'U', True),
    ('④ = ④a + ④b', 'V', 'A4', True),
    ('Ω 밖 (a) Ω701 기준 = ④ − Ω701', 'V', 'outa701', True),
    ('Ω 밖 (a) Ω635 기준 = ④ − Ω635', 'V', 'outa635', False),
    ('Ω 밖 (b) Ω701 기준 = ④a − Ω701', 'V', 'outb701', True),
    ('Ω 밖 (b) Ω635 기준 = ④a − Ω635', 'Vb635', None, False),
    ('① FW_E 본선 7링크', 'V', 'FWE7', False),
    ('② 동측 국소 19링크', 'O', 'local19', False),
    ('④b 중 입력 1098 (FW_E 입구)', 'V', 'u1098', False),
    ('④b 중 입력 1099 (FW_W 입구, 감시)', 'V', 'u1099', False),
    ('④b 중 도시 입력', 'V', 'ucity', False),
    ('링크 66 (SC1004 남측)', 'P', 66, False),
    ('도시도로 (codex 분할, O)', 'O', 'urban_roads', False),
    ('도시도로 codex 규칙 M (codex 꼴만, X2 대조)', 'URB', None, False),
    ('감시: FW_W 본선 (O FW_W_main)', 'O', 'FW_W_main', False),
]
PAIRS = ('FO-NC3', 'B-FO', 'FO-VA')
LABEL = {'FO-NC3': 'FO − NC3', 'B-FO': 'B − FO', 'FO-VA': 'FO − V-A'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(src):
    d = {}
    for k, (p, want) in src.items():
        got = sha(p)
        if want is not None and got != want:
            raise SystemExit('PIN MISMATCH %s' % p)
        d[k + '_sha256'] = got
        if k == 'P':
            P = defaultdict(lambda: defaultdict(dict))
            for r in csv.DictReader(open(p, encoding='utf-8')):
                P[r['convention_window']][r['run']][int(r['link'])] = float(r['veh_h'])
            d['P'] = P
        else:
            d[k] = json.load(open(p, encoding='utf-8'))
    d['vcell'] = {(c['form'], c['pair'], c['seed'], c['metric']): c['mine'] for c in d['V']['cells']}
    return d


def f(x):
    if x is None:
        return '못 냄'
    if x == 'NA':
        return '해당 없음'
    r = round(x + 0.0, 1)
    if r == 0:
        return '±0.0'
    return ('+%.1f' % r) if r > 0 else ('\u2212%.1f' % -r)


def main(argv):
    pre = argv[0]
    selftest = '--selftest' in argv
    B = load(B_SRC)
    F = load(B_SRC if selftest else FO_SRC)
    out = {'selftest': selftest, 'inputs': {'B': {k: v for k, v in B.items() if k.endswith('_sha256')},
                                             'FO': {k: v for k, v in F.items() if k.endswith('_sha256')}},
           'tables': {}, 'checks': {}, 'daggers': {}}

    def vv(D, form, pair, s, metric):
        return D['vcell'][(form, pair, s, metric)]

    def val(pair, src, key, form, s):
        if src in ('V', 'Vdiff', 'Vb635'):
            def one(D, kind, m):
                if kind == 'nc3':
                    return vv(D, form, 'j1-nc3', s, m)
                return -vv(D, form, 'va-j1', s, m)      # j1 - va
            def metric(m, kind):
                if pair == 'FO-NC3':
                    return one(F, 'nc3', m)
                if pair == 'FO-VA':
                    return one(F, 'va', m)
                return one(B, 'nc3', m) - one(F, 'nc3', m)
            if src == 'V':
                return metric(key, None)
            if src == 'Vdiff':
                return metric('O701', None) - metric('O635', None)
            return metric('A4a', None) - metric('O635', None)
        if src in ('O', 'URB'):
            k = 'urban_roads' if src == 'URB' else key
            if src == 'URB' and form != 'codex_8100':
                return 'NA'   # the codex-rule metrics are codex form [0, 8100] only (COMPARE_RULE_B s4-2)
            if src == 'URB' and form == 'codex_8100':
                mb, mf = B['M%d' % s]['codex_rule'], F['M%d' % s]['codex_rule']
                if pair == 'FO-NC3':
                    return mf['joint']['urban_roads'] - mf['nc']['urban_roads']
                if pair == 'B-FO':
                    return mb['joint']['urban_roads'] - mf['joint']['urban_roads']
                return None   # FO - V-A codex-form urban roads: V-A has no codex-rule metrics (O value below in the ours form only)
            oj = lambda D: D['O']['pairs']['J1-NC3|s%d|%s|U6J1' % (s, form)][k]
            if pair == 'FO-NC3':
                return oj(F)
            if pair == 'FO-VA':
                return -F['O']['pairs']['VA-J1|s%d|%s|U9' % (s, form)][k]
            return oj(B) - oj(F)
        if src == 'P':
            fj, n, v, bj = F['P'][form]['j1_s%d' % s][key], F['P'][form]['nc3_s%d' % s][key], F['P'][form]['va_s%d' % s][key], B['P'][form]['j1_s%d' % s][key]
            return {'FO-NC3': fj - n, 'FO-VA': fj - v, 'B-FO': bj - fj}[pair]

    # daggers from the scan prefixes
    def pref(d, tag):
        p = d + '/%s.json' % tag
        return json.load(open(p, encoding='utf-8')).get('lf_sha_le_895_1') if os.path.exists(p) else None
    for s in SEEDS:
        fo = pref(SCAN_B if selftest else SCAN_FO, 'j1_s%d' % s)
        nc = pref(SCAN_B if selftest else SCAN_FO, 'nc3_s%d' % s)
        va = pref(SCAN_B if selftest else SCAN_FO, 'va_s%d' % s)
        b = pref(SCAN_B, 'j1_s%d' % s)
        out['daggers']['s%d' % s] = {'FO-NC3': fo != nc, 'B-FO': b != fo, 'FO-VA': fo != va, 'prefix': {'FO': fo, 'NC3': nc, 'V-A': va, 'B': b}}
    md = ['<!-- generated by fo_tables.py; inputs %s -->' % json.dumps(out['inputs'], ensure_ascii=False), '']
    for form, title in (('ours_9000', 'T1 우리 꼴 [0, 9000] s'), ('codex_8100', 'T2 codex 꼴 [0, 8100] s')):
        hdr = '| 줄 (veh·h) | ' + ' | '.join('%s v3c3-s%d%s' % (LABEL[p], s, '†' if out['daggers']['s%d' % s][p] else '') for p in PAIRS for s in SEEDS) + ' |'
        lines = ['#### ' + title, '', '- 시드 3: v3c3-s31·s41·s43 (평균 없음). veh·h. 판정 낱말 없음. Ω701 은 ④·Ω 밖과 같은 표.', '', hdr, '|---|' + '---:|' * 9]
        tab = {}
        for label, src, key, bold in ROWS:
            cells = []
            for p in PAIRS:
                for s in SEEDS:
                    x = val(p, src, key, form, s)
                    tab['%s|%s|s%d' % (label, p, s)] = x
                    cells.append(x)
            t = [f(x) for x in cells]
            if bold:
                t = ['**%s**' % c if c != '못 냄' else c for c in t]
            lines.append('| %s | %s |' % (label, ' | '.join(t)))
        out['tables'][form] = tab
        md += lines + ['']
    # ---- checks
    x1 = []
    for form in ('ours_9000', 'codex_8100'):
        for s in SEEDS:
            for pair, okey in (('FO-NC3', 'J1-NC3|s%d|%s|U6J1'), ('FO-VA', 'VA-J1|s%d|%s|U9')):
                o = F['O']['pairs'][okey % (s, form)]
                sign = 1 if pair == 'FO-NC3' else -1
                for vm, om in (('O701', 'Omega701'), ('O635', 'Omega635'), ('FWE7', 'FW_E7'), ('A4a', 'M4a')):
                    a = val(pair, 'V', vm, form, s)
                    b = sign * o[om]
                    x1.append({'form': form, 'seed': s, 'pair': pair, 'metric': vm, 'V': a, 'O': b, 'diff': a - b, 'flag': abs(a - b) > 0.05})
    out['checks']['X1'] = {'max_abs': max(abs(r['diff']) for r in x1), 'flagged': [r for r in x1 if r['flag']]}
    x2 = []
    for s in SEEDS:
        a = val('FO-NC3', 'URB', None, 'codex_8100', s)
        b = F['O']['pairs']['J1-NC3|s%d|codex_8100|U6J1' % s]['urban_roads']
        x2.append({'seed': s, 'M': a, 'O': b, 'diff': a - b, 'flag': abs(a - b) > 0.05})
    out['checks']['X2'] = x2
    x3 = []
    for k, v in B['vcell'].items():
        if k[1] == 'va-nc3':
            x3.append(F['vcell'].get(k) == v)
    o3 = []
    for k, v in B['O']['pairs'].items():
        if k.startswith('VA-NC3|') and k.endswith('|U6VA'):
            o3 += [abs(F['O']['pairs'][k][m] - v[m]) <= 1e-6 for m in v if isinstance(v[m], (int, float))]
    out['checks']['X3'] = {'V_va_nc3_cells_equal': all(x3) and len(x3) > 0, 'O_va_nc3_equal': all(o3) and len(o3) > 0, 'stop': not (all(x3) and all(o3))}
    x3b = {}
    for tag in ['nc3_s%d' % s for s in SEEDS] + ['va_s%d' % s for s in SEEDS]:
        a = json.load(open(SCAN_B + '/%s.json' % tag, encoding='utf-8'))
        bp = (SCAN_B if selftest else SCAN_FO) + '/%s.json' % tag
        if not os.path.exists(bp):
            x3b[tag] = None
            continue
        b = json.load(open(bp, encoding='utf-8'))
        a.pop('scan_sec', None)
        b.pop('scan_sec', None)
        x3b[tag] = a == b
    out['checks']['X3b_scans_equal_b'] = x3b
    t66 = F['T66']
    out['checks']['X4_top66_present'] = isinstance(t66, (dict, list))
    out['checks']['X5_arrivals'] = F['V'].get('arrival_totals_9000')
    out['stop'] = out['checks']['X3']['stop'] or any(v is False for v in x3b.values())
    if selftest:
        st = {}
        for form in ('ours_9000', 'codex_8100'):
            bt = json.load(open(CW + '/b/b_results_tables.json', encoding='utf-8'))['tables']['T1 우리 꼴 [0, 9000] s' if form == 'ours_9000' else 'T2 codex 꼴 [0, 8100] s']
            for label, src, key, bold in ROWS:
                for i, s in enumerate(SEEDS):
                    t = out['tables'][form]
                    k_b = '%s|B-NC3' % label.replace('④b 중 입력 1099 (FW_W 입구, 감시)', '④b 중 입력 1099 (FW_W 입구)').replace('감시: FW_W 본선 (O FW_W_main)', '참고·선언 밖: FW_W 본선 (O FW_W_main)').replace('도시도로 (codex 분할, O)', '도시도로 (codex 분할)')
                    if k_b in bt and src not in ('URB', 'Vb635'):
                        st['%s|%s|s%d|FO-NC3==B-NC3' % (form, label, s)] = abs(t['%s|FO-NC3|s%d' % (label, s)] - bt[k_b][i]) <= 1e-9
                    kva = k_b.replace('|B-NC3', '|B-VA')
                    if kva in bt and src not in ('URB', 'Vb635'):
                        st['%s|%s|s%d|FO-VA==B-VA' % (form, label, s)] = abs(t['%s|FO-VA|s%d' % (label, s)] - bt[kva][i]) <= 1e-9
                    x = t['%s|B-FO|s%d' % (label, s)]
                    st['%s|%s|s%d|B-FO==0' % (form, label, s)] = x is None or x == 'NA' or abs(x) <= 1e-9
        out['selftest_checks'] = {'n': len(st), 'false': [k for k, v in st.items() if not v]}
        out['selftest_pass'] = not out['selftest_checks']['false'] and not out['stop']
    json.dump(out, open(pre + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(pre + '.md', 'w', encoding='utf-8').write('\n'.join(md) + '\n')
    print('FO_TABLES stop=%s X1max=%.4f X3=%s X3b=%s' % (out['stop'], out['checks']['X1']['max_abs'], json.dumps(out['checks']['X3']), json.dumps(x3b)))
    if selftest:
        print('SELFTEST pass=%s n=%d false=%d %s' % (out['selftest_pass'], out['selftest_checks']['n'], len(out['selftest_checks']['false']), out['selftest_checks']['false'][:5]))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
