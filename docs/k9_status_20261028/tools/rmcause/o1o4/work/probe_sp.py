# -*- coding: utf-8 -*-
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal
below_normal()
d = json.load(open(sys.argv[1], encoding='utf-8'))
sel = d['selection']
td = sel['tangent_derivatives']
for i, t in enumerate(td):
    print('== td', i, [(k, type(v).__name__, len(json.dumps(v))) for k, v in t.items()])
sp = td[0]['surrogate_prediction']
print('surrogate_prediction keys:', [(k, type(v).__name__, len(json.dumps(v))) for k, v in sp.items()])
for k in ('quantities', 'control_area', 'model_constraint_coverage'):
    v = sp.get(k)
    if isinstance(v, dict):
        print('--', k, [(kk, type(vv).__name__, len(json.dumps(vv))) for kk, vv in v.items()])
print('top-level keys:', [(k, len(json.dumps(v))) for k, v in d.items()])
print('selection sizes:', sorted([(len(json.dumps(v)), k) for k, v in sel.items()])[-12:])
prc = d.get('physical_response_cache')
if isinstance(prc, dict):
    print('prc keys', [(k, type(v).__name__, len(json.dumps(v))) for k, v in prc.items()])
