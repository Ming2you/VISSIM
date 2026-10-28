import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
js = d['metadata']['joint_leader_selection']
cp = js['tangent_derivatives'][1]['surrogate_prediction']['central_physical']
for n, v in zip(cp['names'], cp['values']):
    if 'RM_C10681' in n or ('10681' in n):
        print(n, v)
kinds = sorted(set(n.split('/')[2] for n in cp['names']))
print(kinds)
