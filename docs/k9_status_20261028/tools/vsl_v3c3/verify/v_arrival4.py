# v_arrival4.py — VERIFY_VSL (2026-10-27 KST). Fresh, light. Multiset overlap of exact (desired speed, length) values
# of vehicles first seen at link 74 / 26 / urban, by first-seen period. Same vehicles in another order -> overlap ~1;
# new draws -> overlap ~0 (continuous desired speed to 3 decimals).
import json, sys
from collections import Counter
V = sys.argv[1]
P = [(0, 900), (900, 1800), (1800, 2700), (2700, 4500), (4500, 9001)]
out = {}
for s in (31, 41, 43):
    a = json.load(open(f'{V}/out/scan_vsl_s{s}.json', encoding='utf-8'))['first']
    b = json.load(open(f'{V}/out/scan_nc3_s{s}.json', encoding='utf-8'))['first']
    r = {}
    for name, sel in (('1098', lambda L: L == '74'), ('1099', lambda L: L == '26'), ('urban', lambda L: L not in ('74', '26'))):
        for lo, hi in P:
            ca = Counter((round(x[4], 3), round(x[5], 3), x[1]) for x in a.values() if sel(x[1]) and lo <= x[0] < hi)
            cb = Counter((round(x[4], 3), round(x[5], 3), x[1]) for x in b.values() if sel(x[1]) and lo <= x[0] < hi)
            n = max(sum(ca.values()), 1)
            r['%s_%d_%d' % (name, lo, hi)] = [sum(ca.values()), sum(cb.values()), round(sum((ca & cb).values()) / n, 3)]
    out[str(s)] = r
    print(s, r)
json.dump(out, open(f'{V}/out/arrival4.json', 'w', encoding='utf-8'), indent=1)
