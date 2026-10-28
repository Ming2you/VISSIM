import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
js = d['metadata']['joint_leader_selection']
td = js['tangent_derivatives']
print('n tangent', len(td))
for i, t in enumerate(td):
    sp = t['surrogate_prediction']
    print(i, 'sp keys', list(sp.keys())[:40])
    cp = sp.get('central_physical')
    print('  central_physical type', type(cp).__name__, (len(cp) if hasattr(cp,'__len__') else ''))
    if isinstance(cp, dict):
        ks = list(cp.keys())[:10]; print('  cp keys', ks)
        for k,v in cp.items():
            if isinstance(v, list): print('   ', k, len(v), v[:3])
            else: print('   ', k, str(v)[:200])
    q = sp['quantities']['predicted_ramp_merge']['rate_veh_h_by_ramp']
    print('  predicted 10681', q.get('RM_C10681'), '10490', q.get('RM_C10490'), '10484', q.get('RM_C10484'))
