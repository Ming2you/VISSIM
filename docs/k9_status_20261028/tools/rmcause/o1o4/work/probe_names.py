# -*- coding: utf-8 -*-
import json, sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal
below_normal()
d = json.load(open(sys.argv[1], encoding='utf-8'))
cp = d['selection']['tangent_derivatives'][0]['surrogate_prediction']['central_physical']
print(cp['scope'])
names, values = cp['names'], cp['values']
pref = collections.Counter(re.sub(r'[:/].*', '', n) for n in names)
print(pref.most_common(40))
for n, v in zip(names, values):
    if re.search(sys.argv[2], n):
        print(n, v)
