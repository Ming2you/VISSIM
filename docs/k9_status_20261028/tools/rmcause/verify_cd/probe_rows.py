import json, sys
p = sys.argv[1]
j = json.load(open(p, encoding='utf-8-sig'))
s = j['selection']
co = s['coordinates']
print('coord[0]', co[0])
meters = [(i, c) for i, c in enumerate(co) if c.get('kind') == 'meter']
print('n meter coords', len(meters))
for i, c in meters[:10]: print(i, c)
fw = [r for r in s['local_rows'] if r['owner'].startswith('FW')]
for r in fw[:2]:
    print({k: (v if not isinstance(v, list) else len(v)) for k, v in r.items()})
pfw = [r for r in s['pfo_warm_start']['local_rows'] if r['owner'].startswith('FW')]
for r in pfw[:2]:
    print({k: (v if not isinstance(v, list) else len(v)) for k, v in r.items()})
print('owners', sorted(set(r['owner'] for r in s['local_rows'])))
print('trial_rows[0] keys', list(s['trial_rows'][0].keys()))
print('pfo trial_rows', s['pfo_warm_start']['trial_rows'])
print('pfo status', s['pfo_warm_start']['status'], s['pfo_warm_start']['executed_iterations'], s['pfo_warm_start']['accepted_iterations'])
print('candidates', [{k: v for k, v in c.items()} for c in s['candidates']])
print('control_sequence', {k: (v if not isinstance(v, (list, dict)) else type(v).__name__) for k, v in s['control_sequence'].items()})
