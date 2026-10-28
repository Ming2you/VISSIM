# -*- coding: utf-8 -*-
"""VERIFY_A1_B0: V-A r4 고침 메모 칸 독립 재계산 (r4 도구·va_common 재사용 없음).

입력: vfy_fzp_scan.py 출력 9개(--skip010 --tmax 8995.1), r3 va_metrics.json(③·④a·제거 A·B·150 s 칸; 읽기만),
      인계 omega_membership_exact.json(Ω701·Ω635 링크), demand_34_inputs.csv(입력->링크, 1083 근사 귀속).
식: S = sum_{t_first<=U} (U - t_first)/3600, U = 8995.1(창 끝) 또는 누적 c+0.1. d4b(a-b) = S_b - S_a.
    d4 = d4a(r3) + d4b, OUT_a = d4 - d3(r3). 통계: 평균, sd(n-1), CI = 평균 +- 2.920 sd/sqrt(3). 표시 규칙 직접 구현.
보고 값은 아래 REP 에 메모 글자 그대로. 허용: 3자리 칸 0.002, 1자리 칸 0.06, Ω701·③·④a 보조 칸 0.5.
"""
import json, gzip, os, sys, math, csv

OUT = sys.argv[1]
SC = os.path.dirname(OUT)
AV = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/va/analysis'
HO = 'D:/VISSIM_handoff/20261024/derived/'
U = 8995.1
SEEDS = (31, 41, 43)
PAIRS = {'A': ('va', 'nc3'), 'B': ('va', 'j1'), 'J1R': ('j1', 'nc3')}
T2 = 2.920
SAME = '같은 방향(K8 §5.5 표시 조건 충족, 판정 아님)'
MOVED = '대기 이전(Ω 밖으로)'
NA = '해당 없음(Ω 감소 아님)'

REP = {
    'd4b3': {'A': (-174.135, -105.642, -61.978), 'B': (90.168, 28.871, -52.142), 'J1R': (-264.303, -134.512, -9.836)},
    'd1098': {'A': (214.1, -0.9, 63.8), 'B': (287.3, 36.1, 122.3), 'J1R': (-73.2, -37.0, -58.5)},
    'd1099': {'A': (-329.4, -126.0, -55.9), 'B': (9.2, -2.4, 6.4), 'J1R': (-338.6, -123.5, -62.3)},
    'dother': {'A': (-58.8, 21.2, -69.8), 'B': (-206.3, -4.8, -180.8), 'J1R': (147.5, 26.0, 111.0)},
    'd4': {'A': (-373.8, -506.2, -356.4), 'B': (-475.4, 27.2, -549.7), 'J1R': (101.6, -533.4, 193.4)},
    'out': {'A': (115.6, 153.1, 260.1), 'B': (-4.7, -39.4, -136.8), 'J1R': (120.3, 192.5, 396.9)},
    'r3_d3': {'A': (-489.3, -659.3, -616.5), 'B': (-470.6, 66.7, -412.9), 'J1R': (-18.7, -725.9, -203.6)},
    'r3_d4a': {'A': (-199.6, -400.6, -294.4), 'B': (-565.5, -1.7, -497.6), 'J1R': (365.9, -398.9, 203.2)},
    'stats': {  # 줄: (mean, sd, lo, hi, neg, pos, excludes0)
        'A': {'M4b': (-113.9, 56.5, -209.2, -18.6, 3, 0, True), 'M4': (-412.1, 81.9, -550.3, -274.0, 3, 0, True),
              'OUT': (176.2, 75.0, 49.8, 302.7, 0, 3, True)},
        'B': {'M4b': (22.3, 71.4, -98.0, 142.6, 1, 2, False), 'M4': (-332.6, 313.8, -861.7, 196.5, 2, 1, False),
              'OUT': (-60.3, 68.5, -175.8, 55.1, 3, 0, False)},
        'J1R': {'M4b': (-136.2, 127.2, -350.7, 78.3, 3, 0, False), 'M4': (-79.5, 395.8, -746.7, 587.8, 1, 2, False),
                'OUT': (236.6, 143.5, -5.3, 478.5, 0, 3, False)},
    },
    'labels': {
        'A': {'31': (MOVED, MOVED, MOVED), '41': (MOVED, MOVED, MOVED), '43': (MOVED, MOVED, MOVED), 'mean': (MOVED, MOVED, MOVED)},
        'B': {'31': (SAME, MOVED, MOVED), '41': (NA, NA, NA), '43': (SAME, SAME, SAME), 'mean': (SAME, MOVED, MOVED)},
        'J1R': {'31': (MOVED, MOVED, MOVED), '41': (MOVED, MOVED, MOVED), '43': (MOVED, MOVED, MOVED), 'mean': (MOVED, MOVED, MOVED)},
    },
    'cum': {  # (pair, seed|'mean', row, c) -> r4 값
        ('B', '31', 'OUT', 1800): -1.8, ('B', '31', 'OUT', 3600): -10.4, ('B', '31', 'OUT', 5400): 12.8,
        ('B', '31', 'OUT', 7200): 39.9, ('B', '31', 'OUT', 9000): -4.7, ('B', 'mean', 'OUT', 3600): -0.5,
        ('B', '43', 'OUT', 3600): 4.4, ('A', '41', 'M4', 3600): -50.3, ('A', '31', 'OUT', 9000): 115.6,
        ('B', '43', 'M4', 7200): -356.6,
    },
    'in1083': {'A': (0.0125, -0.0028, 0.0042), 'B': (-125.5, -0.0, -165.5), 'J1R': (125.5, 0.0, 165.5)},
    'in1091': {'A': (0.1, 12.4, 0.9)},
    'in1092': {'B': (-11.2, -0.1, -11.8)},
    'o701': {'A': (-240.6, -421.7, -309.5), 'B': (-590.1, 58.3, -488.4), 'J1R': (349.5, -480.0, 178.9)},
    'out701': {'A': (-133.2, -84.5, -46.9), 'B': (114.7, -31.1, -61.4), 'J1R': (-247.9, -53.4, 14.5)},
}


def load(tag):
    with gzip.open(os.path.join(SC, 'scan_%s.json.gz' % tag), 'rt', encoding='utf-8') as g:
        return json.load(g)


def S(scan, upto, pred=None):
    tot = 0.0
    for v, (t, l) in scan['first'].items():
        if t <= upto + 1e-9 and (pred is None or pred(l)):
            tot += (upto - t)
    return tot / 3600.0


def area(scan, links, form):
    fr = scan['frames']
    tot = 0.0
    K = len(fr)
    for k in range(K):
        if fr[k] > U + 1e-9:
            break
        if form == 'F1' and k == K - 1:
            break
        n = sum(c for l, c in scan['flc'][k] if links is None or l in links)
        tot += n * 5.0
    return tot / 3600.0


def stats(v):
    n = len(v)
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    h = T2 * sd / math.sqrt(n)
    return {'mean': m, 'sd': sd, 'lo': m - h, 'hi': m + h, 'neg': sum(1 for x in v if x < 0),
            'pos': sum(1 for x in v if x > 0), 'excl0': (m - h) > 0 or (m + h) < 0}


def lab(d3, d4, out, d4b, rem, remb):
    if d3 >= 0:
        return (NA, NA, NA)
    n = d4 <= 0 and out <= 0
    wa = n and d4b <= 0 and rem <= 0
    wb = n and d4b <= 0 and remb <= 0
    return (SAME if n else MOVED, SAME if wa else MOVED, SAME if wb else MOVED)


def main():
    r3 = json.load(open(AV + '/out/va_metrics.json', encoding='utf-8'))
    om = json.load(open(HO + 'omega_membership_exact.json', encoding='utf-8'))
    O701 = set(int(x) for x in om['inside_links'])
    O635 = set(int(x) for x in om['controlled_intersection_expansion']['previous_inside_links'])
    inlink = {}
    with open(HO + 'demand_34_inputs.csv', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            inlink[int(row['input'])] = int(row['link'])
    scans = {}
    meta = {}
    for arm in ('va', 'j1', 'nc3'):
        for s in SEEDS:
            sc = load('%s_s%d' % (arm, s))
            scans[(arm, s)] = sc
            meta['%s_s%d' % (arm, s)] = {k: sc[k] for k in ('fzp', 'bytes', 'data_rows', 'skipped_010_rows', 'n_frames',
                                                            'first_frame', 'last_frame', 'irregular_steps', 'n_vehicles')}
    res = {'meta': meta, 'input_links_used': {k: inlink.get(k) for k in (1083, 1091, 1092, 1098, 1099)}}
    lk = {k: inlink.get(k) for k in (1083, 1091, 1092)}
    Sv = {}
    for key, sc in scans.items():
        x = {'all': S(sc, U), '74': S(sc, U, lambda l: l == 74), '26': S(sc, U, lambda l: l == 26)}
        for inp, l in lk.items():
            x['in%d' % inp] = S(sc, U, lambda q, l=l: q == l)
        for c in (900, 1800, 3600, 5400, 7200):
            x['cum%d' % c] = S(sc, c + 0.1)
        x['cum9000'] = x['all']
        x['n74'] = sum(1 for v, (t, l) in sc['first'].items() if l == 74 and t <= U)
        x['n26'] = sum(1 for v, (t, l) in sc['first'].items() if l == 26 and t <= U)
        for form in ('F1', 'F2'):
            x['O701_' + form] = area(sc, O701, form)
            x['O635_' + form] = area(sc, O635, form)
            x['M4a_' + form] = area(sc, None, form)
        Sv['%s_s%d' % key] = x
    res['per_run'] = Sv
    cmp = []

    def chk(name, mine, rep, tol):
        st = 'match' if abs(mine - rep) <= tol else 'MISMATCH'
        cmp.append({'cell': name, 'reported': rep, 'mine': round(mine, 4), 'diff': round(mine - rep, 4), 'status': st})

    D = {}
    for p, (a, b) in PAIRS.items():
        D[p] = {}
        for i, s in enumerate(SEEDS):
            A_, B_ = Sv['%s_s%d' % (a, s)], Sv['%s_s%d' % (b, s)]
            d = {k: B_[k] - A_[k] for k in ('all', '74', '26', 'cum900', 'cum1800', 'cum3600', 'cum5400', 'cum7200', 'cum9000')
                 + tuple('in%d' % q for q in lk)}
            d['other'] = d['all'] - d['74'] - d['26']
            for form in ('F1', 'F2'):
                for m in ('O701', 'O635', 'M4a'):
                    d['%s_%s' % (m, form)] = A_['%s_%s' % (m, form)] - B_['%s_%s' % (m, form)]
            dl = r3['pairs'][p]['deltas'][str(s)]
            d['r3_M3'], d['r3_M4a'], d['r3_REM'], d['r3_REM_B'] = dl['M3'], dl['M4a'], dl['REM'], dl['REM_B']
            d['M4'] = d['r3_M4a'] + d['all']
            d['OUT'] = d['M4'] - d['r3_M3']
            d['label'] = lab(d['r3_M3'], d['M4'], d['OUT'], d['all'], d['r3_REM'], d['r3_REM_B'])
            D[p][s] = d
            chk('%s s%d d4b(3자리)' % (p, s), d['all'], REP['d4b3'][p][i], 0.002)
            chk('%s s%d d1098' % (p, s), d['74'], REP['d1098'][p][i], 0.06)
            chk('%s s%d d1099' % (p, s), d['26'], REP['d1099'][p][i], 0.06)
            chk('%s s%d dother' % (p, s), d['other'], REP['dother'][p][i], 0.06)
            chk('%s s%d d4' % (p, s), d['M4'], REP['d4'][p][i], 0.06)
            chk('%s s%d OUTa' % (p, s), d['OUT'], REP['out'][p][i], 0.06)
            chk('%s s%d r3 d3 인용' % (p, s), d['r3_M3'], REP['r3_d3'][p][i], 0.06)
            chk('%s s%d r3 d4a 인용' % (p, s), d['r3_M4a'], REP['r3_d4a'][p][i], 0.06)
            chk('%s s%d 1083(첫링크 근사)' % (p, s), d['in1083'], REP['in1083'][p][i], 0.5)
            # 보조: Omega701, ③, ④a 두 꼴 중 가까운 것
            for m, repv in (('O701', REP['o701'][p][i]),):
                best = min((abs(d['%s_%s' % (m, f)] - repv), f) for f in ('F1', 'F2'))
                chk('%s s%d dO701(보조, %s)' % (p, s, best[1]), d['%s_%s' % (m, best[1])], repv, 0.5)
            out701 = d['M4'] - d['O701_F1']
            chk('%s s%d OUTa Ω701(보조 F1)' % (p, s), out701, REP['out701'][p][i], 0.5)
            for m, r3k in (('O635', 'r3_M3'), ('M4a', 'r3_M4a')):
                best = min((abs(d['%s_%s' % (m, f)] - d[r3k]), f) for f in ('F1', 'F2'))
                chk('%s s%d %s 재계산 대 r3(보조, %s)' % (p, s, m, best[1]), d['%s_%s' % (m, best[1])], d[r3k], 0.5)
            if p == 'A':
                chk('A s%d 1091(첫링크 근사)' % s, d['in1091'], REP['in1091']['A'][i], 0.5)
            if p == 'B':
                chk('B s%d 1092(첫링크 근사)' % s, d['in1092'], REP['in1092']['B'][i], 0.5)
            chk('%s s%d cum900 d4b = 0' % (p, s), d['cum900'], 0.0, 1e-9)
        # 통계·표시
        for row, key in (('M4b', 'all'), ('M4', 'M4'), ('OUT', 'OUT')):
            st = stats([D[p][s][key] for s in SEEDS])
            rp = REP['stats'][p][row]
            chk('%s %s 평균' % (p, row), st['mean'], rp[0], 0.06)
            chk('%s %s sd' % (p, row), st['sd'], rp[1], 0.06)
            chk('%s %s CI 아래' % (p, row), st['lo'], rp[2], 0.06)
            chk('%s %s CI 위' % (p, row), st['hi'], rp[3], 0.06)
            cmp.append({'cell': '%s %s 음/양·CI 표시' % (p, row), 'reported': [rp[4], rp[5], rp[6]],
                        'mine': [st['neg'], st['pos'], st['excl0']],
                        'status': 'match' if [st['neg'], st['pos'], st['excl0']] == [rp[4], rp[5], rp[6]] else 'MISMATCH'})
            D[p]['stats_' + row] = st
        for s in SEEDS:
            cmp.append({'cell': '%s s%d 표시(N,W_A,W_B)' % (p, s), 'reported': REP['labels'][p][str(s)], 'mine': D[p][s]['label'],
                        'status': 'match' if tuple(D[p][s]['label']) == tuple(REP['labels'][p][str(s)]) else 'MISMATCH'})
        mm = {k: sum(D[p][s][k] for s in SEEDS) / 3 for k in ('r3_M3', 'M4', 'OUT', 'all', 'r3_REM', 'r3_REM_B')}
        ml = lab(mm['r3_M3'], mm['M4'], mm['OUT'], mm['all'], mm['r3_REM'], mm['r3_REM_B'])
        cmp.append({'cell': '%s 평균 표시' % p, 'reported': REP['labels'][p]['mean'], 'mine': ml,
                    'status': 'match' if tuple(ml) == tuple(REP['labels'][p]['mean']) else 'MISMATCH'})
    # 누적
    bd = {p: r3['pairs'][p]['bins_delta'] for p in ('A', 'B')}  # r3 J1R 에는 bins_delta 없음(§6 은 A·B 만)
    cum = {}
    for p in ('A', 'B'):
        for s in SEEDS:
            for c in (900, 1800, 3600, 5400, 7200, 9000):
                nb = c // 150
                m4 = sum(bd[p]['M4'][str(s)][:nb]) - sum(bd[p]['M4b'][str(s)][:nb]) + D[p][s]['cum%d' % c]
                m3 = sum(bd[p]['M3'][str(s)][:nb])
                cum[(p, str(s), 'M4', c)] = m4
                cum[(p, str(s), 'OUT', c)] = m4 - m3
        for c in (900, 1800, 3600, 5400, 7200, 9000):
            for row in ('M4', 'OUT'):
                cum[(p, 'mean', row, c)] = sum(cum[(p, str(s), row, c)] for s in SEEDS) / 3
    for k, v in REP['cum'].items():
        chk('누적 %s' % (k,), cum[k], v, 0.06)
    res['cum'] = {'|'.join(map(str, k)): v for k, v in cum.items()}
    res['pairs'] = {p: {str(s): {k: v for k, v in D[p][s].items()} for s in SEEDS} for p in PAIRS}
    res['stats'] = {p: {r: D[p]['stats_' + r] for r in ('M4b', 'M4', 'OUT')} for p in PAIRS}
    res['compare'] = cmp
    res['n_match'] = sum(1 for c in cmp if c['status'] == 'match')
    res['n_mismatch'] = sum(1 for c in cmp if c['status'] == 'MISMATCH')
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps({'n_match': res['n_match'], 'n_mismatch': res['n_mismatch'],
                      'mismatches': [c for c in cmp if c['status'] == 'MISMATCH']}, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
