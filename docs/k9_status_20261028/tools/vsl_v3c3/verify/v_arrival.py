# v_arrival.py — VERIFY_VSL (2026-10-27 KST). Fresh, light (reads v_scan outputs only).
# Tests the assumption behind 4b (same seed + same network => same arrival sequence at every input).
# Per first-observed link L: sequences of first-seen vehicles in (time, No) order for VSL and NC3.
#  - first index where (desspeed, length) differs, and the first-seen time there (VSL / NC3);
#  - after 900 s: multiset overlap of first-seen TIMES alone (ignores attributes);
#  - for inputs that never queue (first-seen pos < 30 m and identical time grid before divergence) the time overlap
#    shows whether arrival times themselves changed.
import json, sys
from collections import Counter

V = sys.argv[1]
res = {}
for s in (31, 41, 43):
    a = json.load(open(f'{V}/out/scan_vsl_s{s}.json', encoding='utf-8'))['first']
    b = json.load(open(f'{V}/out/scan_nc3_s{s}.json', encoding='utf-8'))['first']

    def seq(f):
        g = {}
        for no, r in f.items():
            g.setdefault(r[1], []).append((r[0], int(no), r[4], r[5], r[3]))
        for k in g:
            g[k].sort()
        return g
    ga, gb = seq(a), seq(b)
    rows = {}
    tot = {'1098': [0, 0, 0], '1099': [0, 0, 0], 'urban': [0, 0, 0]}
    firstbreak = {'1098': [], '1099': [], 'urban': []}
    for L in sorted(set(ga) | set(gb), key=lambda x: int(x)):
        xa, xb = ga.get(L, []), gb.get(L, [])
        brk = None
        for i, (u, w) in enumerate(zip(xa, xb)):
            if (u[2], u[3]) != (w[2], w[3]):
                brk = (i, u[0], w[0])
                break
        ta = Counter(round(x[0], 2) for x in xa if x[0] >= 900)
        tb = Counter(round(x[0], 2) for x in xb if x[0] >= 900)
        inter = sum((ta & tb).values())
        key = '1098' if L == '74' else ('1099' if L == '26' else 'urban')
        tot[key][0] += sum(ta.values()); tot[key][1] += sum(tb.values()); tot[key][2] += inter
        if brk is not None and len(xa) > 50:
            firstbreak[key].append((L, brk[0], brk[1], brk[2], len(xa)))
        if len(xa) > 300 or L in ('74', '26'):
            rows[L] = dict(n_vsl=len(xa), n_nc3=len(xb), attr_break_index=None if brk is None else brk[0],
                           attr_break_t_vsl=None if brk is None else brk[1], attr_break_t_nc3=None if brk is None else brk[2],
                           post900_time_overlap=[sum(ta.values()), sum(tb.values()), inter])
    fb = {k: sorted(v, key=lambda r: r[2])[:8] for k, v in firstbreak.items()}
    res[str(s)] = dict(time_overlap_post900=tot, earliest_attr_breaks=fb, big_links=rows,
                       n_links_with_break={k: len(v) for k, v in firstbreak.items()})
    print('seed', s, 'time overlap post900 [n_vsl, n_nc3, overlap]', tot)
    print('   earliest attribute breaks (link, index, t_vsl, t_nc3, n):', {k: v[:4] for k, v in fb.items()})
    print('   74:', rows.get('74'), ' 26:', rows.get('26'))
json.dump(res, open(f'{V}/out/arrival.json', 'w', encoding='utf-8'), indent=1)
