# -*- coding: utf-8 -*-
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal
below_normal()
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
sel = d['selection']
print('selection keys:', list(sel.keys()))
fc = sel['final_constraints']
print('final.window', fc['window'])
print('final.nuf', json.dumps(fc['nuf'])[:800])
prm = fc['physical_ramp_merge']
print('final.prm', json.dumps({k: v for k, v in prm.items()})[:1500])
bi = sel.get('budget_initialization')
print('budget_init', json.dumps(bi)[:1800])
pfo = sel.get('pfo_warm_start') or {}
print('pfo keys', list(pfo.keys()))
for k in ('trial_rows', 'tangent_derivatives', 'candidates'):
    v = sel.get(k)
    print('==', k, type(v).__name__, len(v) if hasattr(v, '__len__') else '')
    if isinstance(v, list) and v:
        print(json.dumps(v[0])[:2500])
# search for any key containing 'merge' recursively (paths only, limited)
hits = []
def find(o, path, depth):
    if depth > 7 or len(hits) > 200: return
    if isinstance(o, dict):
        for k, v in o.items():
            if 'merge' in str(k).lower() or 'ramp_release' in str(k).lower() or 'freeway_frames' in str(k):
                hits.append((path + '/' + str(k), type(v).__name__, (len(v) if hasattr(v, '__len__') else v)))
            find(v, path + '/' + str(k), depth + 1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            find(v, path + '[%d]' % i, depth + 1)
find(d, '', 0)
for h in hits: print(h)
