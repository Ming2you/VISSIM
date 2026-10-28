# -*- coding: utf-8 -*-
import json, sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal
below_normal()
d = json.load(open(sys.argv[1], encoding='utf-8'))
cp = d['selection']['tangent_derivatives'][0]['surrogate_prediction']['central_physical']
names = cp['names']
pref = collections.Counter('/'.join(re.split(r'/', n)[:1] + [re.split(r'/', n)[2] if len(re.split(r'/', n))>2 else '']) for n in names)
print(pref.most_common(60))
st = [n for n in names if n.startswith('state')]
print(st[:30])
print([n for n in names if 'FW_E' in n][:40])
