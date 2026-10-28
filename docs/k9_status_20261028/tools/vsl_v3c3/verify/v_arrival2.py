# v_arrival2.py — VERIFY_VSL (2026-10-27 KST). Fresh, light (reads v_scan outputs only).
# Per demand interval (inpx timeIntervals 0/900/1800/2700/3600/4500) and input group: first-seen counts VSL vs NC3,
# share of identical first-seen times in sorted order, and the 4b contribution S_NC3 - S_VSL restricted to vehicles
# first seen in that interval (W = 9000). Urban links are also split into 'calm' links (every first sighting at
# pos >= 5 m, i.e. no stand-still insertion in either run) and the rest.
import json, sys
from collections import defaultdict

V = sys.argv[1]
EDGES = [0, 900, 1800, 2700, 3600, 4500, 9000.1]
W = 9000.0
res = {}
for s in (31, 41, 43):
    a = json.load(open(f'{V}/out/scan_vsl_s{s}.json', encoding='utf-8'))['first']
    b = json.load(open(f'{V}/out/scan_nc3_s{s}.json', encoding='utf-8'))['first']
    minpos = defaultdict(lambda: 1e9)
    for f in (a, b):
        for r in f.values():
            minpos[r[1]] = min(minpos[r[1]], r[3])

    def grp(L):
        if L == '74':
            return '1098'
        if L == '26':
            return '1099'
        return 'urban_calm' if minpos[L] >= 5.0 else 'urban_other'

    def bins(f):
        d = defaultdict(list)
        for r in f.values():
            t = r[0]
            for k in range(len(EDGES) - 1):
                if EDGES[k] <= t < EDGES[k + 1]:
                    d[(grp(r[1]), r[1], k)].append(t)
                    break
        return d
    da, db = bins(a), bins(b)
    out = {}
    for key in sorted(set(da) | set(db)):
        g, L, k = key
        ta, tb = sorted(da.get(key, [])), sorted(db.get(key, []))
        same = sum(1 for x, y in zip(ta, tb) if abs(x - y) < 1e-6)
        contrib = (sum(W - x for x in tb) - sum(W - x for x in ta)) / 3600.0
        o = out.setdefault(g, {}).setdefault(str(k), [0, 0, 0, 0.0, 0])
        o[0] += len(ta); o[1] += len(tb); o[2] += same; o[3] += contrib; o[4] += 1
    res[str(s)] = out
    print('seed', s, '[n_vsl, n_nc3, n_same_time_in_order, 4b_contrib_veh_h, n_links] by interval index (0=0-900 .. 5=4500-9000)')
    for g in ('1098', '1099', 'urban_calm', 'urban_other'):
        if g in out:
            print('  ', g, {k: [v[0], v[1], v[2], round(v[3], 1), v[4]] for k, v in sorted(out[g].items())})
json.dump(res, open(f'{V}/out/arrival2.json', 'w', encoding='utf-8'), indent=1)
