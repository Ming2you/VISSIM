# -*- coding: utf-8 -*-
import json, sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal
below_normal()
d = json.load(open(sys.argv[1], encoding='utf-8'))
sel = d['selection']
for i, td in enumerate(sel['tangent_derivatives']):
    fc = td['surrogate_prediction']['control_area']['flow_counts']
    print('== td', i, 'n flow keys', len(fc))
    for k, v in fc.items():
        if re.search(sys.argv[2], k): print('  ', k, v)
    print('   ttt', td['surrogate_prediction']['control_area']['ttt_veh_h'])
    lc = td['surrogate_prediction'].get('local_costs')
    print('   local_costs keys', list(lc.keys())[:30] if isinstance(lc, dict) else lc)
    ram = td['surrogate_prediction'].get('resource_summary')
    print('   resource_summary', json.dumps(ram)[:600])
    print('   streamed', json.dumps(td['surrogate_prediction'].get('streamed_model_checks'))[:1200])
