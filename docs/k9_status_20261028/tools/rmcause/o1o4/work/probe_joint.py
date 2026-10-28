# -*- coding: utf-8 -*-
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal
below_normal()
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
def walk(o, p='', depth=0, maxd=3):
    if depth > maxd: return
    if isinstance(o, dict):
        for k, v in list(o.items())[:60]:
            s = type(v).__name__
            if isinstance(v, (list, dict)): s += ' len=%d' % len(v)
            else: s += ' ' + repr(v)[:70]
            print('  ' * depth + p + str(k), s)
            walk(v, '', depth + 1, maxd)
    elif isinstance(o, list) and o:
        walk(o[0], '[0].', depth + 1, maxd)
walk(d, maxd=int(sys.argv[2]) if len(sys.argv) > 2 else 2)
