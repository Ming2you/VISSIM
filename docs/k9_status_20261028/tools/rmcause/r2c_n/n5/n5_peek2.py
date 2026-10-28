import json,sys,os
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
f=os.path.join(D,sys.argv[1])
o=json.load(open(f,encoding='utf-8'))
j=o['metadata']['joint_leader_selection']
t=j['tangent_derivatives'][0]
print('costs', json.dumps(t['costs']))
print('resources', json.dumps(t['resources']))
cj=t['cost_jacobian']
print('cost_jacobian type', type(cj).__name__, (len(cj) if hasattr(cj,'__len__') else ''), json.dumps(cj)[:600])
print('active_axes', json.dumps(t['active_axes'])[:300])
print('exact_anchor_costs', json.dumps(t['exact_anchor_costs']))
print('anchor_correction_costs', json.dumps(t['anchor_correction_costs']))
print('trace', json.dumps(t['trace'])[:1200])
print('sp objective', t['surrogate_prediction']['objective_veh_h'], 'token', t['surrogate_prediction']['action_token'])
print('local_base_costs', json.dumps(t['surrogate_prediction']['local_base_costs']))
print('local_costs', json.dumps(t['surrogate_prediction']['local_costs'])[:1500])
gr=j['gradient_rows']; print('gradient_rows n', len(gr), json.dumps(gr[0])[:1500])
lr=j['local_rows']; print('local_rows n', len(lr), json.dumps(lr[0])[:1500])
sq=j['surrogate_query']; print('sq keys', list(sq.keys())); print(json.dumps(sq['rows'][:3])[:2000])
