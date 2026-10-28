# meter-neighbor audit selected deltas and executed meter greens (fresh)
import glob, json, re
from collections import Counter, defaultdict
D='D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
sel=[]; greens=defaultdict(Counter); guard=[]
for p in sorted(glob.glob(f'{D}/action_??????.json')):
    t=int(re.search(r'action_(\d{6})\.json$',p).group(1))
    if t<900: continue
    d=json.load(open(p,encoding='utf-8'))
    for k,v in (d.get('diagnostics') or {}).items():
        if k.startswith('rw_meter_green_'): greens[k[len('rw_meter_green_'):]][v]+=1
    j=d.get('metadata',{}).get('joint_leader_selection')
    if j is None or t>7950: continue
    m=j['meter_neighbor_audit']; s=m['selected']
    c=[x for x in m['candidates'] if x['candidate']==s]
    best=min(c,key=lambda x:x['objective']) if c else None
    sel.append((t,s,best['delta_veh_h'] if best else None,len(c)))
    mob=j.get('meter_operating_bounds')
    guard.append((t,json.dumps(mob)[:0] if mob is None else (mob.get('triggered') if isinstance(mob,dict) else None)))
    del d
dl=[x[2] for x in sel if x[2] is not None]
out=dict(n=len(sel),neg=sum(x<0 for x in dl),sum=sum(dl),min=min(dl),argmin=[x[0] for x in sel if x[2]==min(dl)],pos=[(x[0],x[2]) for x in sel if x[2] is not None and x[2]>0],
         multi=[(x[0],x[3]) for x in sel if x[3]>1][:5],greens={k:dict(sorted(v.items())) for k,v in greens.items()})
json.dump(out,open('meter_out.json','w'),indent=1)
print(json.dumps(out,indent=0)[:3000])
