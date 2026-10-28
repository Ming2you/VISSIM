r"""J1 report correction (D-K9-89 7; method D-K9-87 = first-observation difference).  Compares the J1_REPORT.md cells
of 4b, 4 and Omega outside (a) (pair d = J1 - NC3) with the recount made by the pinned r4 tools (path-constant copies in
AN/corr/tools), applies the J1 label rule (ANALYSIS_METHOD.md sec.2.5 = va_common.label, checked K4) and counts cells.
  python -B j1c_compare.py              real run: reads AN/corr/out/r4_firstobs.json (the recount)
  python -B j1c_compare.py --identity   self-test: new := the J1_REPORT values (no recount read); expects 0 changed
Read-only: AN/J1_REPORT.md (sha256 must stay 4bf31b13...), AN/out/an_metrics.json, AN/verify/out/v_metrics.json,
AV/out/va_metrics.json, AV/r4/out/r4_firstobs.json (published r4), AN/corr/out/r4_firstobs.json.
Writes AN/corr/out/j1c_compare.json, j1c_cells.csv, j1c_tables.json (AN/corr/selftest/ with --identity).
Exit 2 = a STOP check failed (nothing for the memo).  Rule: AN/corr/COMPARE_RULE_J1C.md."""
import csv
import io
import os
import re
import sys

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402

SP = r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8'
AN = os.path.join(SP, 'j1', 'analysis')
CORR = os.path.join(AN, 'corr')
AV = os.path.join(SP, 'k92', 'va', 'analysis')
sys.path.insert(0, os.path.join(AV, 'tools'))
import va_common as V  # noqa: E402  (pinned r3 common: stats, label, sha, jload; read-only import)

J1_REPORT = os.path.join(AN, 'J1_REPORT.md')
J1_REPORT_SHA = '4bf31b134845401524c2a04032e79b41772cb0f6a8f7aef7b2d9e94d41f0bc52'
AN_METRICS = os.path.join(AN, 'out', 'an_metrics.json')
V_METRICS = os.path.join(AN, 'verify', 'out', 'v_metrics.json')
VA_METRICS = os.path.join(AV, 'out', 'va_metrics.json')
PUB = os.path.join(AV, 'r4', 'out', 'r4_firstobs.json')
NEW = os.path.join(CORR, 'out', 'r4_firstobs.json')
SEEDS = ('31', '41', '43')
CPS = (900, 1800, 3600, 5400, 7200, 9000)
ROWS = ('M4', 'M4b', 'OUT_a', 'unins_1098', 'unins_1099', 'unins_other')
RN = {'M3': '③ Ω (635링크)', 'M4a': '④a 전체 링크 TTT', 'M4': '④ 전체 + 미삽입', 'M4b': '④b 미삽입',
      'OUT_a': 'Ω 밖 (a) ④ − ③', 'unins_1098': '④b 중 입력 1098', 'unins_1099': '④b 중 입력 1099',
      'unins_other': '④b 중 그 밖 입력'}
SN = {'31': 'v3c3-s31 (재실행)', '41': 'v3c3-s41', '43': 'v3c3-s43', 'mean': '3시드 평균'}
# J1_REPORT first-column texts of the compared rows
L0 = {'M4': '**④ 전체 + 미삽입**', 'OUT_a': '**Ω 밖 (a) ④ − ③**', 'M4b': '④b 미삽입'}
L31 = {'M4': '**④ 전체 + 미삽입**', 'M4b': '④b 미삽입 (12입력 합집합, NC 앵커)', 'OUT_a': '**Ω 밖 (a) ④ − ③** (veh·h)'}
L32 = dict(L31, unins_1098='④b 중 입력 1098 (FW_E 입구)', unins_1099='④b 중 입력 1099 (FW_W 입구)',
           unins_other='④b 중 그 밖 10입력')
L41 = {'M4': '(같은 표) ④ 전체 + 미삽입', 'OUT_a': '(같은 표) Ω 밖 (a) ④ − ③', 'M4b': '(같은 표) ④b 미삽입'}
L6 = {'M4': '④', 'OUT_a': 'Ω 밖 (a)', 'M3': '③ Ω'}
STOPS = []
CHECK = {}


def stop(msg):
    STOPS.append(msg)
    print('STOP', msg)


def f(x, nd=1, sign=False):
    if x is None:
        return '–'
    return ('%+.*f' % (nd, x)) if sign else ('%.*f' % (nd, x))


def sgn(x):
    return 0 if x == 0 else (1 if x > 0 else -1)


def close(a, b, tol):
    return abs(float(a) - float(b)) <= tol


# ------------------------------------------------------------------ J1_REPORT parsing (read-only)
def report_cells():
    lines = io.open(J1_REPORT, encoding='utf-8').read().split('\n')
    keys = ('## 0.', '## 1.', '### 3.1', '### 3.2', '### 3.3', '## 4.', '### 4.1', '### 4.2', '### 4.3', '## 5.', '## 6.',
            '## 7.')
    idx = {}
    for i, l in enumerate(lines):
        for k in keys:
            if k not in idx and l.startswith(k + ' '):
                idx[k] = i
    if len(idx) != len(keys):
        stop('K6 report headings missing %s' % sorted(set(keys) - set(idx)))
        return None

    def rows(a, b):
        out = {}
        for l in lines[idx[a]:idx[b]]:
            if l.startswith('|') and not l.startswith('|---'):
                c = [x.strip() for x in l.strip().strip('|').split('|')]
                out.setdefault(c[0], []).append(c)
        return out
    R = {'s0': rows('## 0.', '## 1.'), 's31': rows('### 3.1', '### 3.2'), 's32': rows('### 3.2', '### 3.3'),
         's33': rows('### 3.3', '## 4.'), 's41': rows('### 4.1', '### 4.2'), 's43': rows('### 4.3', '## 5.'),
         's6': rows('## 6.', '## 7.')}
    m = None
    for l in lines[idx['## 5.']:idx['## 6.']]:
        if '입력 1083 몫의 d는' in l:
            m = re.search(r'v3c3-s31 재실행 ([+\-]?\d+\.\d), v3c3-s41 ([+\-]?\d+\.\d), v3c3-s43 ([+\-]?\d+\.\d) veh·h', l)
    R['s5'] = list(m.groups()) if m else None
    return R


def one(R, sec, label):
    v = R[sec].get(label)
    if not v or len(v) != 1:
        stop('K6 row %s %r found %d' % (sec, label, 0 if not v else len(v)))
        return None
    return v[0]


def ci_split(t):
    m = re.match(r'^\[([+\-]?\d+\.\d), ([+\-]?\d+\.\d)\]\s*(.*)$', t)
    if not m:
        return None, None, None
    return m.group(1), m.group(2), m.group(3).strip()


# ------------------------------------------------------------------ loading
def load(identity):
    an = V.jload(AN_METRICS)
    vm = V.jload(V_METRICS)
    va = V.jload(VA_METRICS)
    old = {'d': {s: dict(an['deltas'][s]) for s in SEEDS}, 'st': an['summary'], 'labels': an['labels_k8_5_5'],
           'bins': an['bins_delta'], 'ui': an['unins_by_input'], 'union': list(an['union_inputs'])}
    for s in SEEDS:
        e = vm['extra']
        old['d'][s]['REM_B'] = float(e['rm_j1_s%s' % s]['outside_omega'] - e['rm_nc3_s%s' % s]['outside_omega'])
    # K1: J1 analysis values = the V-A r3 J1R values the r4 recount uses (d3, d4a, removals, NC levels, scans)
    k1 = 0.0
    P = va['pairs']['J1R']
    for s in SEEDS:
        for k in ('M3', 'M4a', 'M4', 'M4b', 'OUT_a', 'REM', 'REM_B', 'unins_1098', 'unins_1099', 'unins_other'):
            k1 = max(k1, abs(old['d'][s][k] - P['deltas'][s][k]))
        for k in ROWS:
            k1 = max(k1, abs(an['summary'][k]['nc'][s] - P['summary'][k]['nc'][s]))
    CHECK['K1_max_abs_an_minus_va_J1R'] = k1
    if k1 > 1e-9:
        stop('K1 an_metrics vs va_metrics J1R %.3g' % k1)
    if sorted(va['unions']['U6J1'], key=int) != sorted(old['union'], key=int):
        stop('K1 union U6J1 differs from the J1 union')
    if identity:
        nf = None
        new = {'4b': {s: {k: old['d'][s][k] for k in ('M4b', 'unins_1098', 'unins_1099', 'unins_other')} for s in SEEDS},
               'perk': {s: {k: (old['ui'][k]['j1_s' + s]['veh_h_nc_anchor'] - old['ui'][k]['nc3_s' + s]['veh_h_nc_anchor'])
                            for k in old['union']} for s in SEEDS},
               'bins4b': {s: np.asarray(old['bins']['M4b'][s], float) for s in SEEDS}}
        return an, old, new, nf
    nf = V.jload(NEW)
    if 'STOPS' in nf:
        stop('recount r4_firstobs STOPS %s' % nf['STOPS'])
    J = nf['new_deltas']['J1R']
    new = {'4b': {s: {k: J[s][k] for k in ('M4b', 'unins_1098', 'unins_1099', 'unins_other')} for s in SEEDS},
           'perk': {s: dict(nf['per_input_new']['J1R'][s]) for s in SEEDS},
           'bins4b': {s: np.asarray(nf['bins_new']['J1R'][s]['M4b'], float) for s in SEEDS}}
    # K1 (scans): the recount read the same stage-1 scans as the J1 analysis
    for s in SEEDS:
        for arm in ('j1', 'nc3'):
            tag = '%s_s%s' % (arm, s)
            if nf['inputs_info'][tag]['sha256'] != an['per_run'][tag]['scan_sha256']:
                stop('K1 scan sha %s' % tag)
    for s in SEEDS:
        if not close(J[s]['REM_B'], old['d'][s]['REM_B'], 1e-9) or not close(J[s]['REM'], old['d'][s]['REM'], 1e-9):
            stop('K1 removals %s' % s)
    # K2: recount J1R = published r4 J1R
    pub = V.jload(PUB)
    k2 = 0.0
    for s in SEEDS:
        for k, v in nf['new_deltas']['J1R'][s].items():
            k2 = max(k2, abs(v - pub['new_deltas']['J1R'][s][k]))
        for k, v in nf['per_input_new']['J1R'][s].items():
            k2 = max(k2, abs(v - pub['per_input_new']['J1R'][s][k]))
    for s in SEEDS + ('mean',):
        for k in ('M4b', 'M4', 'OUT_a'):
            k2 = max(k2, float(np.max(np.abs(np.asarray(nf['bins_new']['J1R'][s][k]) - np.asarray(pub['bins_new']['J1R'][s][k])))))
    for k, st in nf['summary_new']['J1R'].items():
        for q in ('mean', 'sd'):
            k2 = max(k2, abs(st[q] - pub['summary_new']['J1R'][k][q]))
    for s, q in nf['omega701_reference']['pairs']['J1R'].items():
        for kk, v in q.items():
            k2 = max(k2, abs(v - pub['omega701_reference']['pairs']['J1R'][s][kk]))
    CHECK['K2_max_abs_recount_minus_published_r4_J1R'] = k2
    CHECK['K2_labels_equal'] = nf['labels_new']['J1R'] == pub['labels_new']['J1R']
    if k2 > 1e-9 or not CHECK['K2_labels_equal']:
        stop('K2 recount vs published r4 J1R %.3g labels_equal=%s' % (k2, CHECK['K2_labels_equal']))
    return an, old, new, nf


# ------------------------------------------------------------------ main computation
def main():
    identity = '--identity' in sys.argv
    prio = V.set_below_normal()
    outdir = os.path.join(CORR, 'selftest' if identity else 'out')
    os.makedirs(outdir, exist_ok=True)
    sha0 = V.sha(J1_REPORT)
    CHECK['K0_j1_report_sha_before'] = sha0
    if sha0 != J1_REPORT_SHA:
        stop('K0 J1_REPORT bytes changed before')
    an, old, new, nf = load(identity)
    od = old['d']
    # new per-seed d (4b from the recount; 3, 4a, removals from the J1 analysis)
    nd = {}
    for s in SEEDS:
        x = dict(new['4b'][s])
        x['M3'], x['M4a'], x['REM'], x['REM_B'] = od[s]['M3'], od[s]['M4a'], od[s]['REM'], od[s]['REM_B']
        x['M4'] = od[s]['M4a'] + x['M4b']
        x['OUT_a'] = x['M4'] - od[s]['M3']
        nd[s] = x
    # stats with the J1_REPORT denominators (an summary nc)
    ost = {k: old['st'][k] for k in ROWS}
    nst = {}
    for k in ROWS:
        ncs = [old['st'][k]['nc'][s] for s in SEEDS]
        st = V.stats([nd[s][k] for s in SEEDS], ncs)
        st['per_seed'] = {s: nd[s][k] for s in SEEDS}
        nst[k] = st
    # K3: the J1 stats function (copied in va_common) reproduces an summary for all 14 rows; recount agreement
    k3 = 0.0
    for k, _ in an['metrics']:
        st = V.stats([od[s][k] for s in SEEDS], [old['st'][k]['nc'][s] for s in SEEDS])
        for q in ('mean', 'sd', 'pct_of_nc'):
            k3 = max(k3, abs(st[q] - old['st'][k][q]))
        k3 = max(k3, abs(st['ci90'][0] - old['st'][k]['ci90'][0]), abs(st['ci90'][1] - old['st'][k]['ci90'][1]))
        if st['ci_excludes_0'] != old['st'][k]['ci_excludes_0'] or st['neg'] != old['st'][k]['neg'] or st['pos'] != old['st'][k]['pos']:
            stop('K3 stats text %s' % k)
    CHECK['K3_stats_reproduce_an_summary_max_abs'] = k3
    if k3 > 1e-9:
        stop('K3 stats reproduce %.3g' % k3)
    if nf is not None:
        J = nf['new_deltas']['J1R']
        k3b = max(abs(nd[s][k] - J[s][k]) for s in SEEDS for k in ('M4', 'OUT_a', 'M4b', 'unins_1098', 'unins_1099', 'unins_other'))
        for k in ROWS:
            for q in ('mean', 'sd'):
                k3b = max(k3b, abs(nst[k][q] - nf['summary_new']['J1R'][k][q]))
            k3b = max(k3b, abs(nst[k]['ci90'][0] - nf['summary_new']['J1R'][k]['ci90'][0]))
        CHECK['K3_compare_minus_recount_max_abs'] = k3b
        if k3b > 1e-9:
            stop('K3 compare vs recount %.3g' % k3b)
    # labels (J1 method 2.5 via va_common.label); K4 = reproduces an labels from an values
    olab = {s: V.label(od[s]) for s in SEEDS}
    omean = {k: old['st'][k]['mean'] for k in ('M3', 'M4', 'OUT_a', 'M4b', 'REM')}
    omean['REM_B'] = float(np.mean([od[s]['REM_B'] for s in SEEDS]))
    olab['mean'] = V.label(omean)
    for s in SEEDS + ('mean',):
        if olab[s]['N'] != old['labels'][s]['N'] or olab[s]['W_A'] != old['labels'][s]['W']:
            stop('K4 label reproduce %s' % s)
    nlab = {s: V.label(nd[s]) for s in SEEDS}
    nmean = {k: nst[k]['mean'] for k in ('M4', 'OUT_a', 'M4b')}
    nmean.update({k: omean[k] for k in ('M3', 'REM', 'REM_B')})
    nlab['mean'] = V.label(nmean)
    if nf is not None and nlab != nf['labels_new']['J1R']:
        stop('K4 labels differ from recount labels')
    # 150 s bins (an bins: 4a = M4 - M4b; new 4 = 4a + new 4b; new outside (a) = new 4 - M3)
    B = old['bins']
    nb = {}
    k5 = {}
    for s in SEEDS:
        m4a = np.asarray(B['M4'][s], float) - np.asarray(B['M4b'][s], float)
        k5['M4a|' + s] = float(m4a.sum() - od[s]['M4a'])
        k5['M4b|' + s] = float(new['bins4b'][s].sum() - nd[s]['M4b'])
        if abs(k5['M4a|' + s]) > 0.01 or abs(k5['M4b|' + s]) > 0.001:
            stop('K5 bins %s %s' % (s, k5))
        m4 = m4a + new['bins4b'][s]
        nb[s] = {'M4': m4, 'OUT_a': m4 - np.asarray(B['M3'][s], float), 'M4b': new['bins4b'][s]}
    nb['mean'] = {k: np.mean([nb[s][k] for s in SEEDS], axis=0) for k in ('M4', 'OUT_a', 'M4b')}
    CHECK['K5_bins'] = k5
    if nf is not None:
        k5b = 0.0
        for s in SEEDS + ('mean',):
            for k in ('M4', 'OUT_a'):
                k5b = max(k5b, float(np.max(np.abs(nb[s][k] - np.asarray(nf['bins_new']['J1R'][s][k])))))
        CHECK['K5_bins_vs_recount_max_abs'] = k5b
        if k5b > 1e-3:
            stop('K5 bins vs recount %.3g' % k5b)
    cum_old = {k: {s: [float(sum(B[k][s][:c // 150])) for c in CPS] for s in SEEDS + ('mean',)} for k in ('M3', 'M4', 'OUT_a')}
    cum_new = {k: {s: [float(np.sum(nb[s][k][:c // 150])) for c in CPS] for s in SEEDS + ('mean',)} for k in ('M4', 'OUT_a')}
    # per input
    allk = sorted(set(old['union']) | set(new['perk']['31']), key=int)
    perk_old = {s: {k: ((old['ui'][k]['j1_s' + s]['veh_h_nc_anchor'] - old['ui'][k]['nc3_s' + s]['veh_h_nc_anchor'])
                        if k in old['union'] else None) for k in allk} for s in SEEDS}
    perk_new = {s: {k: new['perk'][s].get(k, 0.0) for k in allk} for s in SEEDS}
    # 14 declared rows: CI excluding 0, old and new
    ci14_old = [k for k, _ in an['metrics'] if old['st'][k]['ci_excludes_0']]
    ci14_new = [k for k, _ in an['metrics'] if (nst[k]['ci_excludes_0'] if k in ROWS else old['st'][k]['ci_excludes_0'])]

    # ---------------------------------------------------------------- cells + K6 (old text = report text)
    R = report_cells()
    cells = []

    def add(loc, row, col, o, n, nd_=1, sign=True, rep=None, txt=None):
        if txt is not None:
            ot, nt = txt
            c = dict(loc=loc, row=row, col=col, old_raw=None, new_raw=None, old=ot, new=nt, changed=ot != nt,
                     sign_changed=False, report=rep)
        else:
            ot, nt = f(o, nd_, sign), f(n, nd_, sign)
            c = dict(loc=loc, row=row, col=col, old_raw=o, new_raw=n, old=ot, new=nt, changed=ot != nt,
                     sign_changed=bool(o is not None and n is not None and sgn(o) != sgn(n)), report=rep)
        if rep is not None and rep != c['old']:
            stop('K6 report text %s|%s|%s report=%r formatted=%r' % (loc, row, col, rep, c['old']))
        cells.append(c)

    def citxt(st):
        return '관측된 차이' if st['ci_excludes_0'] else '0 포함'
    if R is not None:
        # sec.0 table
        for k in ('M4', 'OUT_a', 'M4b'):
            r = one(R, 's0', L0[k])
            if r is None:
                continue
            o, n = ost[k], nst[k]
            for i, s in enumerate(SEEDS):
                add('§0 표', k, 'd ' + s, o['per_seed'][s], n['per_seed'][s], rep=r[1 + i])
            add('§0 표', k, '평균 d', o['mean'], n['mean'], rep=r[4])
            add('§0 표', k, 'sd', o['sd'], n['sd'], 1, False, rep=r[5])
            lo, hi, _ = ci_split(r[6])
            add('§0 표', k, 'CI 아래', o['ci90'][0], n['ci90'][0], rep=lo)
            add('§0 표', k, 'CI 위', o['ci90'][1], n['ci90'][1], rep=hi)
            add('§0 표', k, '음/양', None, None, rep=r[7], txt=('%d/%d' % (o['neg'], o['pos']), '%d/%d' % (n['neg'], n['pos'])))
            add('§0 표', k, 'CI 표시', None, None, rep=r[8], txt=(citxt(o), citxt(n)))
        # sec.3.1 d columns
        for k in ('M4', 'M4b', 'OUT_a'):
            r = one(R, 's31', L31[k])
            if r is None:
                continue
            for i, s in enumerate(SEEDS):
                add('§3.1 d', k, 'd ' + s, od[s][k], nd[s][k], rep=r[3 + 3 * i])
        # sec.3.2 summary
        for k in ROWS:
            r = one(R, 's32', L32[k])
            if r is None:
                continue
            o, n = ost[k], nst[k]
            for i, s in enumerate(SEEDS):
                add('§3.2 요약', k, 'd ' + s, o['per_seed'][s], n['per_seed'][s], rep=r[1 + i])
            add('§3.2 요약', k, '평균 d', o['mean'], n['mean'], rep=r[4])
            add('§3.2 요약', k, 'sd', o['sd'], n['sd'], 1, False, rep=r[5])
            lo, hi, _ = ci_split(r[6])
            add('§3.2 요약', k, 'CI 아래', o['ci90'][0], n['ci90'][0], rep=lo)
            add('§3.2 요약', k, 'CI 위', o['ci90'][1], n['ci90'][1], rep=hi)
            add('§3.2 요약', k, '음/양', None, None, rep=r[7], txt=('%d/%d' % (o['neg'], o['pos']), '%d/%d' % (n['neg'], n['pos'])))
            add('§3.2 요약', k, '평균/NC %', o['pct_of_nc'], n['pct_of_nc'], 2, rep=r[8])
            pp = r[9].split(' / ')
            for i, s in enumerate(SEEDS):
                add('§3.2 요약', k, '시드별 d/NC % ' + s, o['per_seed_pct'][i], n['per_seed_pct'][i],
                    rep=pp[i] if len(pp) == 3 else None)
            add('§3.2 요약', k, 'CI 표시', None, None, rep=r[11], txt=(citxt(o), citxt(n)))
        # sec.3.3 labels
        for s in SEEDS + ('mean',):
            r = one(R, 's33', SN[s])
            if r is None:
                continue
            if s == 'mean':
                o = {k: old['st'][k]['mean'] for k in ('M4', 'OUT_a', 'M4b')}
                n = {k: nst[k]['mean'] for k in ('M4', 'OUT_a', 'M4b')}
            else:
                o, n = od[s], nd[s]
            add('§3.3 표시', 'M4', s, o['M4'], n['M4'], rep=r[2])
            add('§3.3 표시', 'OUT_a', s, o['OUT_a'], n['OUT_a'], rep=r[3])
            add('§3.3 표시', 'M4b', s, o['M4b'], n['M4b'], rep=r[4])
            add('§3.3 표시', 'label N', s, None, None, rep=r[7], txt=(olab[s]['N'], nlab[s]['N']))
            if olab[s]['W_A'] != olab[s]['W_B']:
                stop('K4 old W_A != W_B at %s (single W column)' % s)
            nw = nlab[s]['W_A'] if nlab[s]['W_A'] == nlab[s]['W_B'] else 'A: %s / B: %s' % (nlab[s]['W_A'], nlab[s]['W_B'])
            add('§3.3 표시', 'label W', s, None, None, rep=r[8], txt=(olab[s]['W_A'], nw))
        # sec.4.1 "(같은 표)" rows
        for k in ('M4', 'OUT_a', 'M4b'):
            r = one(R, 's41', L41[k])
            if r is None:
                continue
            o, n = ost[k], nst[k]
            for i, s in enumerate(SEEDS):
                parts = r[1 + i].split(' / ')
                add('§4.1 같은 표', k, 'd ' + s, o['per_seed'][s], n['per_seed'][s], rep=parts[2] if len(parts) == 3 else None)
            add('§4.1 같은 표', k, '평균 d', o['mean'], n['mean'], rep=r[4])
            lo, hi, tx = ci_split(r[5])
            add('§4.1 같은 표', k, 'CI 아래', o['ci90'][0], n['ci90'][0], rep=lo)
            add('§4.1 같은 표', k, 'CI 위', o['ci90'][1], n['ci90'][1], rep=hi)
            add('§4.1 같은 표', k, 'CI 표시', None, None, rep=tx,
                txt=('관측된 차이' if o['ci_excludes_0'] else '', '관측된 차이' if n['ci_excludes_0'] else ''))
            add('§4.1 같은 표', k, '음/양', None, None, rep=r[6], txt=('%d/%d' % (o['neg'], o['pos']), '%d/%d' % (n['neg'], n['pos'])))
        # sec.4.3 per input (union rows of the J1 table)
        for k in old['union']:
            r = one(R, 's43', k)
            if r is None:
                continue
            for i, s in enumerate(SEEDS):
                m = re.match(r'^(\S+) / (\S+) / (\S+) \(', r[2 + i])
                add('§4.3 입력별', k, 'd ' + s, perk_old[s][k], perk_new[s][k], rep=m.group(3) if m else None)
        # sec.5 text (input 1083 share)
        for i, s in enumerate(SEEDS):
            rep = R['s5'][i] if R['s5'] else None
            o, n = perk_old[s]['1083'], perk_new[s]['1083']
            if rep is None or abs(float(rep) - o) > 0.05:
                stop('K6 sec.5 1083 text %s %r vs %.4f' % (s, rep, o))
            add('§5 1083 몫', 'unins_1083', 'd ' + s, o, n)
        # sec.6 cumulative
        for k in ('M4', 'OUT_a'):
            rr = R['s6'].get(L6[k], [])
            for s in SEEDS + ('mean',):
                r = [x for x in rr if len(x) > 1 and x[1] == SN[s]]
                if len(r) != 1:
                    stop('K6 sec.6 row %s %s' % (k, s))
                    continue
                for j, c in enumerate(CPS):
                    add('§6 누적', k, '%s @%d' % (s, c), cum_old[k][s][j], cum_new[k][s][j], rep=r[0][2 + j])
    sha1 = V.sha(J1_REPORT)
    CHECK['K0_j1_report_sha_after'] = sha1
    if sha1 != J1_REPORT_SHA:
        stop('K0 J1_REPORT bytes changed after')
    CHECK['K6_cells_with_report_text'] = sum(1 for c in cells if c['report'] is not None)
    CHECK['identity_mode'] = identity

    res = {'schema': 'j1-correction-compare/v1', 'doc': __doc__, 'priority': hex(prio), 'identity': identity,
           'script_sha256': V.sha(os.path.abspath(__file__)), 'va_common_sha256': V.sha(V.__file__),
           'sources': {p: V.sha(p) for p in (J1_REPORT, AN_METRICS, V_METRICS, VA_METRICS) + (() if identity else (PUB, NEW))},
           'checks': CHECK, 'STOPS': STOPS}
    if STOPS:
        V.jdump(res, os.path.join(outdir, 'j1c_compare_STOPPED.json'))
        print('STOPPED', len(STOPS))
        sys.exit(2)
    res.update({'old_deltas': od, 'new_deltas': nd, 'summary_old': ost, 'summary_new': nst,
                'labels_old': olab, 'labels_new': nlab, 'cum_old': cum_old, 'cum_new': cum_new,
                'per_input_old': perk_old, 'per_input_new': perk_new, 'union': old['union'],
                'ci14_old': ci14_old, 'ci14_new': ci14_new, 'n_declared_rows': len(an['metrics'])})
    if nf is not None:
        res['recount_checks_J1R'] = {
            'C4_pairs': {s: nf['C4']['pairs']['J1R|' + s] for s in SEEDS},
            'C4_runs': {t: nf['C4']['runs'][t] for t in ('j1_s31', 'nc3_s31', 'j1_s41', 'nc3_s41', 'j1_s43', 'nc3_s43')},
            'C5': {s: nf['C5']['cells']['j1-nc3|' + s] for s in SEEDS},
            'window_effect': {s: nf['C5']['window_effect_r4_minus_0_9000']['J1R|' + s] for s in SEEDS},
            'C8_pre900_max_abs_d4b': {s: nf['C8_pre900_max_abs_d4b']['J1R|' + s] for s in SEEDS},
            'C3': {t: nf['C3_max_abs_grid_minus_closed'][t] for t in ('j1_s31', 'nc3_s31', 'j1_s41', 'nc3_s41', 'j1_s43', 'nc3_s43')},
            'M4b_r3union': {s: nf['new_deltas']['J1R'][s]['M4b_r3union'] for s in SEEDS},
            'omega701_J1R': nf['omega701_reference']['pairs']['J1R'],
            'inputs_info': {t: {'sha256': nf['inputs_info'][t]['sha256'], 'C2': nf['inputs_info'][t]['C2']}
                            for t in ('j1_s31', 'nc3_s31', 'j1_s41', 'nc3_s41', 'j1_s43', 'nc3_s43')}}
    res['cells'] = cells
    res['cells_count'] = {'total': len(cells), 'changed': sum(c['changed'] for c in cells),
                          'sign_changed': sum(c['sign_changed'] for c in cells)}
    byloc = {}
    for c in cells:
        q = byloc.setdefault(c['loc'], {'total': 0, 'changed': 0, 'sign_changed': 0})
        q['total'] += 1
        q['changed'] += int(c['changed'])
        q['sign_changed'] += int(c['sign_changed'])
    res['cells_count_by_loc'] = byloc
    res['sign_changed_cells'] = [c for c in cells if c['sign_changed']]
    res['text_changed_cells'] = [c for c in cells if c['old_raw'] is None and c['changed']]
    with io.open(os.path.join(outdir, 'j1c_cells.csv'), 'w', newline='', encoding='utf-8') as h:
        w = csv.writer(h)
        w.writerow(['loc', 'row', 'col', 'report_old', 'new', 'changed', 'sign_changed', 'report_text', 'old_raw', 'new_raw'])
        for c in cells:
            w.writerow([c['loc'], c['row'], c['col'], c['old'], c['new'], int(c['changed']), int(c['sign_changed']),
                        '' if c['report'] is None else c['report'], '' if c['old_raw'] is None else repr(c['old_raw']),
                        '' if c['new_raw'] is None else repr(c['new_raw'])])
    res['tables'] = tables(res, an, byloc)
    V.jdump(res['tables'], os.path.join(outdir, 'j1c_tables.json'))
    V.jdump(res, os.path.join(outdir, 'j1c_compare.json'))
    print('DONE identity=%s cells=%d changed=%d sign_changed=%d report_text_checked=%d ci14 %d->%d' % (
        identity, len(cells), res['cells_count']['changed'], res['cells_count']['sign_changed'],
        CHECK['K6_cells_with_report_text'], len(ci14_old), len(ci14_new)))


def mark(o, n, nd=1, sign=True):
    ot, nt = f(o, nd, sign), f(n, nd, sign)
    flag = ''
    if o is not None and n is not None and sgn(o) != sgn(n):
        flag = ' †'
    elif ot != nt:
        flag = ' *'
    return '%s → %s%s' % (ot, nt, flag)


def tables(res, an, byloc):
    T = {}
    od, nd, ost, nst = res['old_deltas'], res['new_deltas'], res['summary_old'], res['summary_new']
    hs = ' | '.join('%s 보고 → 고침' % SN[s] for s in SEEDS)
    lines = ['| 줄 (d = J1 − NC3) | %s |' % hs, '|---|---|---|---|',
             '| ③ Ω (635링크) (안 바뀜) | %s |' % ' | '.join(f(od[s]['M3'], 1, True) for s in SEEDS),
             '| ④a 전체 링크 TTT (안 바뀜) | %s |' % ' | '.join(f(od[s]['M4a'], 1, True) for s in SEEDS)]
    for k in ('M4b', 'M4', 'OUT_a', 'unins_1098', 'unins_1099', 'unins_other'):
        lines.append('| %s | %s |' % (RN[k], ' | '.join(mark(od[s][k], nd[s][k]) for s in SEEDS)))
    rc = res.get('recount_checks_J1R')
    if rc:
        lines.append('| (참고) ④b 를 보고 합집합 12입력만 셈 | %s |' % ' | '.join(
            '%s → %s' % (f(od[s]['M4b'], 1, True), f(rc['M4b_r3union'][s], 1, True)) for s in SEEDS))
    T['PERSEED'] = '\n'.join(lines)
    lines = ['| 줄 (d = J1 − NC3) | 판 | d s31 | d s41 | d s43 | 평균 d | sd | 90 % CI | 음/양 | 평균/NC % | 시드별 d/NC % | CI 표시 |',
             '|---|---|---:|---:|---:|---:|---:|---|---|---:|---|---|']
    st3 = an['summary']['M3']
    lines.append('| ③ Ω (635링크) (안 바뀜) | 보고 = 고침 | %s | %s | %s | %s | %s | [%s, %s] | %d/%d | %s | %s | %s |' % (
        f(st3['per_seed']['31'], 1, True), f(st3['per_seed']['41'], 1, True), f(st3['per_seed']['43'], 1, True),
        f(st3['mean'], 1, True), f(st3['sd'], 1), f(st3['ci90'][0], 1, True), f(st3['ci90'][1], 1, True), st3['neg'],
        st3['pos'], f(st3['pct_of_nc'], 2, True), ' / '.join(f(x, 1, True) for x in st3['per_seed_pct']),
        '관측된 차이' if st3['ci_excludes_0'] else '0 포함'))
    for k in ROWS:
        for tag, st in (('보고', ost[k]), ('**고침**', nst[k])):
            lines.append('| %s | %s | %s | %s | %s | %s | %s | [%s, %s] | %d/%d | %s | %s | %s |' % (
                RN[k], tag, f(st['per_seed']['31'], 1, True), f(st['per_seed']['41'], 1, True),
                f(st['per_seed']['43'], 1, True), f(st['mean'], 1, True), f(st['sd'], 1), f(st['ci90'][0], 1, True),
                f(st['ci90'][1], 1, True), st['neg'], st['pos'], f(st['pct_of_nc'], 2, True),
                ' / '.join(f(x, 1, True) for x in st['per_seed_pct']), '관측된 차이' if st['ci_excludes_0'] else '0 포함'))
    T['SUMMARY'] = '\n'.join(lines)
    lo, ln = res['labels_old'], res['labels_new']
    lines = ['| 대상 | d(③) | d(④) 보고 → 고침 | d(④ − ③) 보고 → 고침 | d(④b) 보고 → 고침 | d(제거 A) | d(제거 B, 사후) | 읽는 법 N 보고 → 고침 | 읽는 법 W (제거 A·B) 보고 → 고침 |',
             '|---|---:|---|---|---|---:|---:|---|---|']
    for s in SEEDS + ('mean',):
        if s == 'mean':
            o = {k: ost[k]['mean'] for k in ('M4', 'OUT_a', 'M4b')}
            n = {k: nst[k]['mean'] for k in ('M4', 'OUT_a', 'M4b')}
            m3, ra, rb = an['summary']['M3']['mean'], an['summary']['REM']['mean'], float(np.mean([od[x]['REM_B'] for x in SEEDS]))
        else:
            o, n = od[s], nd[s]
            m3, ra, rb = od[s]['M3'], od[s]['REM'], od[s]['REM_B']
        nw = ln[s]['W_A'] if ln[s]['W_A'] == ln[s]['W_B'] else 'A: %s / B: %s' % (ln[s]['W_A'], ln[s]['W_B'])
        cn = lo[s]['N'] if lo[s]['N'] == ln[s]['N'] else '%s → **%s**' % (lo[s]['N'], ln[s]['N'])
        cw = lo[s]['W_A'] if lo[s]['W_A'] == nw else '%s → **%s**' % (lo[s]['W_A'], nw)
        lines.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            SN[s], f(m3, 1, True), mark(o['M4'], n['M4']), mark(o['OUT_a'], n['OUT_a']), mark(o['M4b'], n['M4b']),
            f(ra, 1, True), f(rb, 1, True), cn, cw))
    T['LABELS'] = '\n'.join(lines)
    co, cn_ = res['cum_old'], res['cum_new']
    lines = ['| 지표 | 시드 | %s |' % ' | '.join('누적 d ~%d s 보고 → 고침' % c for c in CPS), '|---|---|' + '---|' * len(CPS)]
    for k, nm in (('M3', '③ Ω (안 바뀜)'), ('M4', '④'), ('OUT_a', 'Ω 밖 (a)')):
        for s in SEEDS + ('mean',):
            if k == 'M3':
                cl = [f(x, 1, True) for x in co[k][s]]
            else:
                cl = [mark(a, b) for a, b in zip(co[k][s], cn_[k][s])]
            lines.append('| %s | %s | %s |' % (nm, SN[s], ' | '.join(cl)))
    T['CUM'] = '\n'.join(lines)
    po, pn = res['per_input_old'], res['per_input_new']
    allk = sorted(pn['31'], key=int)
    show = [k for k in allk if k in res['union'] or any(abs(pn[s][k]) >= 0.05 for s in SEEDS)]
    rest = [k for k in allk if k not in show]
    lines = ['| 입력 | 보고 합집합 | %s |' % ' | '.join('d %s 보고 → 고침' % SN[s] for s in SEEDS), '|---|---|---|---|---|']
    for k in show:
        lines.append('| %s | %s | %s |' % (k, '안' if k in res['union'] else '밖', ' | '.join(
            ('밖 → %s' % f(pn[s][k], 1, True)) if po[s][k] is None else mark(po[s][k], pn[s][k]) for s in SEEDS)))
    lines.append('| 나머지 %d입력 합 | 밖 | %s |' % (len(rest), ' | '.join(f(sum(pn[s][k] for k in rest), 2, True) for s in SEEDS)))
    T['PER_INPUT'] = '\n'.join(lines)
    rc = res.get('recount_checks_J1R')
    if rc:
        lines = ['| 시드 | d④b 재셈 (stage-1 첫 관측, 주 값) | d④b 새 FZP 스캔 | 차 | [0, 9000] 꼴 vhr 값 (VERIFY §2.2) | 창 효과 (주 값 − [0, 9000]) | 900 s 전 칸 최대 \\|d④b\\| |',
                 '|---|---:|---:|---:|---:|---:|---:|']
        for s in SEEDS:
            q = rc['C4_pairs'][s]
            lines.append('| %s | %s | %s | %s | %s | %s | %s |' % (
                SN[s], f(q['stage1'], 3, True), f(q['fzp'], 3, True), f(q['diff'], 4, True), f(rc['C5'][s]['got'], 2, True),
                f(rc['window_effect'][s], 2, True), f(rc['C8_pre900_max_abs_d4b'][s], 4)))
        T['CHECKS'] = '\n'.join(lines)
        lines = ['| 시드 | d(Ω701) | d(④) 고침 | Ω 밖 (a) Ω701 기준: 보고 방법 → 고침 | Ω 밖 (a) Ω635 기준: 보고 → 고침 |', '|---|---:|---:|---|---|']
        for s in SEEDS:
            q = rc['omega701_J1R'][s]
            lines.append('| %s | %s | %s | %s | %s |' % (SN[s], f(q['d_O701'], 1, True), f(nd[s]['M4'], 1, True),
                                                       mark(q['OUT_a_O701_r3method'], q['OUT_a_O701_r4']),
                                                       mark(od[s]['OUT_a'], nd[s]['OUT_a'])))
        T['O701'] = '\n'.join(lines)
    lines = ['| 보고 위치 | 대조 칸 | 글자 바뀜 | 부호 바뀜 |', '|---|---:|---:|---:|']
    for loc, q in byloc.items():
        lines.append('| %s | %d | %d | %d |' % (loc, q['total'], q['changed'], q['sign_changed']))
    lines.append('| 합 | %d | %d | %d |' % (res['cells_count']['total'], res['cells_count']['changed'], res['cells_count']['sign_changed']))
    T['COUNTS'] = '\n'.join(lines)
    nm = dict((k, v) for k, v in an['metrics'])
    T['CI14'] = '보고 %d행 (%s) → 고침 %d행 (%s), 선언 %d행 중' % (
        len(res['ci14_old']), ', '.join(nm[k] for k in res['ci14_old']), len(res['ci14_new']),
        ', '.join(nm[k] for k in res['ci14_new']), res['n_declared_rows'])
    return T


if __name__ == '__main__':
    main()
