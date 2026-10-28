# Structure-only probe: VSL coordinate key strings and local_rows field types (no numeric values printed).
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
j = d['metadata']['joint_leader_selection']
vk = sorted({(r['owner'], r['key'], r['block']) for r in j['gradient_rows'] if r['kind']=='vsl'})
print('vsl grad keys n', len(vk), vk[:8])
print('gradient kinds', sorted({r['kind'] for r in j['gradient_rows']}))
print('coord kinds', sorted({c['kind'] for c in j['coordinates']}))
lr = j['local_rows'][0]
for k, v in lr.items():
    print(' local_rows[0]', k, type(v).__name__, (len(v) if isinstance(v,(list,dict)) else ''), (list(v.keys())[:5] if isinstance(v, dict) else ''))
pf = j['pfo_warm_start']
print('pfo local_rows[0] keys', list(pf['local_rows'][0].keys()) if pf['local_rows'] else None)
print('pfo trial_rows[0] keys', list(pf['trial_rows'][0].keys()) if pf['trial_rows'] else None)
print('original_held_candidate keys', list(j['original_held_candidate'].keys()))
ma = j['meter_neighbor_audit']; print('mna selected type', type(ma['selected']).__name__, 'cand[0] keys', list(ma['candidates'][0].keys()) if ma['candidates'] else None)
ps = j['price_state']; print('prices_scaled type', type(ps['prices_scaled']).__name__, list(ps['prices_scaled'].keys())[:10] if isinstance(ps['prices_scaled'], dict) else '')
print('iteration_dual_updates[0] before type', type(j['iteration_dual_updates'][0]['before']).__name__)
print('control_sequence blocks type', type(j['control_sequence']['blocks']).__name__, len(j['control_sequence']['blocks']))
b0 = j['control_sequence']['blocks'][0]; print(' block0 type', type(b0).__name__, list(b0.keys())[:20] if isinstance(b0, dict) else '')
print('top keys', list(d.keys())[:30])
