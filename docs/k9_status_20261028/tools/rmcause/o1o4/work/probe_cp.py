# -*- coding: utf-8 -*-
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal
below_normal()
d = json.load(open(sys.argv[1], encoding='utf-8'))
td = d['selection']['tangent_derivatives'][0]
def show(o, name, depth=0, maxd=3):
    if depth > maxd: return
    if isinstance(o, dict):
        for k, v in list(o.items())[:50]:
            s = type(v).__name__
            if isinstance(v, (list, dict)): s += ' len=%d sz=%d' % (len(v), len(json.dumps(v)))
            else: s += ' ' + repr(v)[:70]
            print('  ' * depth + str(k), s)
            show(v, k, depth + 1, maxd)
    elif isinstance(o, list) and o:
        print('  ' * depth + '[0]:')
        show(o[0], '[0]', depth + 1, maxd)
print('=== td.central_physical'); show(td['central_physical'], 'cp', 0, 3)
print('=== sp.central_physical'); show(td['surrogate_prediction']['central_physical'], 'cp', 0, 2)
