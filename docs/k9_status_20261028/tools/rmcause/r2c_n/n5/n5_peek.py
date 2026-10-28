import json,sys,os
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
f=os.path.join(D,sys.argv[1])
o=json.load(open(f,encoding='utf-8'))
j=o['metadata']['joint_leader_selection']
print('omega_partition:', json.dumps(j['omega_partition'])[:3000])
print('candidates:', json.dumps(j['candidates']))
print('trial_rows n', len(j['trial_rows']), json.dumps(j['trial_rows'][0])[:1500])
td=j['tangent_derivatives']
print('tangent n', len(td))
for i,t in enumerate(td):
    print(i, {k:(len(json.dumps(v))) for k,v in t.items()})
    if i==0:
        sp=t.get('surrogate_prediction',{})
        print(' sp keys', {k:len(json.dumps(v)) for k,v in sp.items()})
        ca=sp.get('control_area',{})
        print(' ca keys', {k:len(json.dumps(v)) for k,v in ca.items()})
print('prediction', json.dumps(o['prediction'])[:2000])
print('pfo', {k:len(json.dumps(v)) for k,v in j['pfo_warm_start'].items()})
print('central_multiplier n', len(j['central_multiplier']), {k:len(json.dumps(v)) for k,v in j['central_multiplier'][0].items()})
print('coord n', len(j['coordinates']), json.dumps(j['coordinates'][0]))
kinds={}
for a in j['coordinates']: kinds[a['kind']]=kinds.get(a['kind'],0)+1
print(kinds)
