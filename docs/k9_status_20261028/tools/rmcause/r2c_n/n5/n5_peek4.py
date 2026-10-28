import json,sys,os,collections
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
f=os.path.join(D,sys.argv[1])
o=json.load(open(f,encoding='utf-8'))
j=o['metadata']['joint_leader_selection']
t=j['tangent_derivatives'][0]
cp=t['surrogate_prediction']['central_physical']
names=cp['names']; vals=cp['values']
print(len(names), len(vals), cp['scope'])
pref=collections.Counter(n.split(':')[0] if isinstance(n,str) else str(type(n)) for n in names)
print(pref.most_common(30))
fw=[(n,v) for n,v in zip(names,vals) if isinstance(n,str) and ('FW_E' in n or 'RM_C10681' in n)]
print(len(fw)); 
for n,v in fw[:60]: print(n, v)
coord=j['coordinates']
mi=[i for i,a in enumerate(coord) if a['kind']=='meter']
print('meter idx', mi)
print([ (coord[i]['key'],coord[i]['block'],coord[i].get('reference_value'),coord[i].get('allowed')) for i in mi])
cj=t['cost_jacobian']
for r,row in enumerate(cj):
    print(r, [round(row[i],5) for i in mi])
