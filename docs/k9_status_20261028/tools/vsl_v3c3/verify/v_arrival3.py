# v_arrival3.py — VERIFY_VSL (2026-10-27 KST). Fresh, light (reads v_scan outputs only).
# D(t) = N_NC3(t) - N_VSL(t): cumulative first sightings at input link 74 (1098) and 26 (1099), per 5 s frame.
# If both runs had the same arrival times, D(t) = queue_VSL(t) - queue_NC3(t) and the 4b line = integral of D.
# Prints D at interval edges, extremes, number of sign changes, and integral by interval.
import json, sys, bisect

V = sys.argv[1]
EDGES = [900, 1800, 2700, 3600, 4500, 6300, 8100, 9000]
out = {}
for s in (31, 41, 43):
    a = json.load(open(f'{V}/out/scan_vsl_s{s}.json', encoding='utf-8'))
    b = json.load(open(f'{V}/out/scan_nc3_s{s}.json', encoding='utf-8'))
    T = a['frames']
    res = {}
    for L, name in (('74', '1098'), ('26', '1099')):
        ta = sorted(r[0] for r in a['first'].values() if r[1] == L)
        tb = sorted(r[0] for r in b['first'].values() if r[1] == L)
        D = [bisect.bisect_right(tb, t + 1e-6) - bisect.bisect_right(ta, t + 1e-6) for t in T]
        at = {e: D[max(i for i, t in enumerate(T) if t <= e)] for e in EDGES}
        sc = sum(1 for x, y in zip(D, D[1:]) if (x > 0 > y) or (x < 0 < y))
        integ = {}
        for lo, hi in zip(EDGES, EDGES[1:]):
            integ['%d-%d' % (lo, hi)] = round(sum(D[i] * 5.0 for i, t in enumerate(T) if lo <= t < hi) / 3600.0, 1)
        res[name] = dict(D_at=at, D_min=min(D), D_max=max(D), sign_changes=sc,
                         t_at_min=T[D.index(min(D))], t_at_max=T[D.index(max(D))], integral_veh_h=integ,
                         integral_total=round(sum(D) * 5.0 / 3600.0, 1))
    out[str(s)] = res
    for name, r in res.items():
        print(s, name, 'D_at', r['D_at'], 'min', r['D_min'], '@', r['t_at_min'], 'max', r['D_max'], '@', r['t_at_max'],
              'signchg', r['sign_changes'], 'int', r['integral_veh_h'], 'tot', r['integral_total'])
json.dump(out, open(f'{V}/out/arrival3.json', 'w', encoding='utf-8'), indent=1)
