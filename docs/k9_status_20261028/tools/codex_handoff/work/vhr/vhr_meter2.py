import glob, json, re
D='D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
rows=[]
for p in sorted(glob.glob(f'{D}/action_??????.json')):
    t=int(re.search(r'action_(\d{6})\.json$',p).group(1))
    if not 900<=t<=7950: continue
    d=json.load(open(p,encoding='utf-8')); j=d['metadata'].get('joint_leader_selection')
    if j is None: continue
    m=j['meter_neighbor_audit']; s=m['selected']
    c=[x for x in m['candidates'] if x['candidate']==s]
    npf=d.get('N_P_star'); nuf=d.get('N_UF_star')
    match=[x for x in c if x.get('np_cap') is not None and abs(x['np_cap']-npf)<1e-6 and (x.get('nuf_target') is None or nuf is None or abs(x['nuf_target']-nuf)<1e-6)]
    selobj=j.get('selected_objective'); mo=[x for x in c if abs(x['objective']-selobj)<1e-9]
    rows.append(dict(t=t,sel=s,n_same=len(c),deltas=[round(x['delta_veh_h'],4) for x in c],match_np=[round(x['delta_veh_h'],4) for x in match],match_obj=[round(x['delta_veh_h'],4) for x in mo],
                     first=c[0]['delta_veh_h'] if c else None, base=m.get('baseline_objective'), selobj=selobj))
    del d
def summ(key):
    v=[r[key] if not isinstance(r[key],list) else (r[key][0] if r[key] else None) for r in rows]
    v=[x for x in v if x is not None]
    return dict(n=len(v),neg=sum(x<0 for x in v),sum=round(sum(v),3),min=round(min(v),4),argmin=[r['t'] for r in rows if (r[key][0] if isinstance(r[key],list) and r[key] else r[key])==min(v)],pos=[(r['t'],r[key]) for r in rows if (r[key][0] if isinstance(r[key],list) and r[key] else (r[key] if not isinstance(r[key],list) else None)) is not None and (r[key][0] if isinstance(r[key],list) else r[key])>0])
print('first', summ('first')); print('match_np', summ('match_np')); print('match_obj', summ('match_obj'))
for r in rows[:6]+[r for r in rows if r['t'] in (2850,3450,3600)]: print(r)
json.dump(rows,open('meter2_out.json','w'),indent=1)
