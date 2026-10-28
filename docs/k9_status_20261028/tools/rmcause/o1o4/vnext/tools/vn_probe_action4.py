import json, sys, collections
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
js = d['metadata']['joint_leader_selection']
gr = js['gradient_rows']
c = collections.Counter((r['owner'], r['kind']) for r in gr)
print(c)
for r in gr:
    if 'RM_' in str(r['key']) or r['kind'] in ('meter','ramp','ramp_meter'):
        print(r['owner'], r['kind'], r['key'], r['block'], r['scale'], 'own', r['own'], 'ext', r['external'], 'tot', r['total'], 'res', r['resource_derivatives_scaled'], r['derivative_method'])
print('js keys', list(js.keys()))
