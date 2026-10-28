# structure probe only (keys, types, lengths); no numbers used for analysis
import json, sys, collections
o = json.load(open(sys.argv[1], encoding='utf-8'))
print('top', list(o.keys()))
print('vsl type', type(o.get('vsl')).__name__, list((o.get('vsl') or {}).items())[:6])
md = o['metadata']
print('md keys', list(md.keys())[:60])
j = md.get('joint_leader_selection') or {}
print('j keys', list(j.keys()))
for k in ('coordinates','gradient_rows','local_rows','trial_rows','candidates'):
    v = j.get(k)
    print(k, type(v).__name__, len(v) if hasattr(v,'__len__') else v)
c = j['coordinates']
print('coord kinds', collections.Counter(x['kind'] for x in c))
print('vsl coords', [ (x['owner'],x['key'],x.get('block'),x.get('scale')) for x in c if x['kind']=='vsl'][:40])
print('coord sample', json.dumps(c[0])[:400])
g = [r for r in j['gradient_rows'] if r['kind']=='vsl']
print('grad vsl rows', len(g), json.dumps(g[0])[:600] if g else None)
print('local sample keys', list(j['local_rows'][0].keys()))
print('trial sample', json.dumps(j['trial_rows'][0])[:400] if j['trial_rows'] else None)
print('cand', json.dumps(j['candidates'])[:800])
print('policy vsl', {k:v for k,v in j['policy'].items() if 'vsl' in k.lower()})
print('omega_partition keys', list((j.get('omega_partition') or {}).keys())[:20])
print('price_state', json.dumps(j.get('price_state'))[:500])
print('control_sequence', json.dumps(j.get('control_sequence'))[:300])
