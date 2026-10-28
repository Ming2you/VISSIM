# N34 probe (read-only): flow_counts keys around SC1001 W leg / OR_D_W in one V-A joint decision
import json, sys, re
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8-sig'))
sel = d['selection']
tds = sel.get('tangent_derivatives') or []
fc = ((tds[0].get('surrogate_prediction') or {}).get('control_area') or {}).get('flow_counts') or {}
print('n flow keys', len(fc))
for k in sorted(fc):
    if re.search(r'SC1001|OR_D_W|R_D_E|RM_C10490|in_SC1001|shared_12|129', k):
        print(' ', k, round(fc[k], 3))
print('top keys', list(d.keys())[:40])
print('sel keys', list(sel.keys())[:60])
