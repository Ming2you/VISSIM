import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
js = d['metadata']['joint_leader_selection']
fc = js['final_constraints']['physical_ramp_merge']
print(json.dumps({k: v for k, v in fc.items() if not isinstance(v, (list,)) or len(v) < 10}, indent=1)[:3000])
gr = js['gradient_rows']
print('gradient_rows type', type(gr).__name__, len(gr))
g0 = gr[0]
print('g0 keys', list(g0.keys())[:60])
for k, v in g0.items():
    if isinstance(v, (list, dict)):
        s = json.dumps(v)[:600]
    else:
        s = repr(v)
    print(' ', k, ':', s)
print('applied_block', json.dumps(js['control_sequence'].get('applied_block'))[:500])
