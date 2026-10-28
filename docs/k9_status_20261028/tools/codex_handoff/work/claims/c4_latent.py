# R_CLAIMS c4: uninserted (latent) bracket for NC 0-8100 and ④ comparisons (read only; inference, assumptions printed)
import json, csv
E='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/handoff/evidence/'
R={r['condition']:r for r in json.load(open(E+'run_metadata.json',encoding='utf-8'))}
F=json.load(open(E+'independent_fzp_counts.json',encoding='utf-8'))
M={}
for r in csv.DictReader(open(E+'metrics_0_8100.csv',encoding='utf-8-sig')): M[(r['condition'],r['metric'])]=float(r['veh_h'])
dem=[r for r in csv.DictReader(open(E+'demand_34_inputs.csv',encoding='utf-8-sig')) if r['input']=='1099']
iv=[(float(r['start_s']),float(r['volume_veh_h'])) for r in dem]; iv.sort()
def cum(T):
    s=0.0
    for i,(a,q) in enumerate(iv):
        b=iv[i+1][0] if i+1<len(iv) else 1e9
        lo,hi=a,min(b,T)
        if hi>lo: s+=q*(hi-lo)/3600
    return s
D8100,D9000=cum(8100),cum(9000)
print(f'1099 expected demand 0-8100 {D8100:.1f}, 0-9000 {D9000:.1f}')
for c,T in [('nc',9000),('joint',8100),('window',8100),('off',8100),('freeway_only',8100),('urban_only',8100)]:
    L=R[c]['native_uninserted_end_vehicles']; D=cum(T)
    print(f'  {c:12s} end latent {L:.0f} / expected demand {D:.1f} = {L/D*100:.1f}% ; implied inserted {D-L:.0f} -> {(D-L)/(T/3600):.0f} veh/h avg')
# bracket NC latent integral 0-8100
L9=R['nc']['native_uninserted_end_vehicles']; Ltot=R['nc']['native_uninserted_wait_veh_h']; q_last=6336.0
res=[]
for Q in (3500,4337,5000,6336,7000):
    L81=L9-(q_last-Q)*0.25
    tail=(L81+L9)/2*0.25
    res.append((Q,L81,tail,Ltot-tail))
    print(f'  Q={Q}: NC latent(8100)~{L81:.0f}, tail 8100-9000 {tail:.1f} veh·h -> NC ④b(0-8100) ~{Ltot-tail:.1f}')
lo=min(x[3] for x in res); hi=max(x[3] for x in res)
nc4a=F['nc']['whole_observed']; nc_om=F['nc']['Omega701']
print(f'NC ④b(0-8100) bracket [{lo:.1f}, {hi:.1f}] ; NC ④a(0-8100,FZP) {nc4a:.3f} ; NC ④ bracket [{nc4a+lo:.1f}, {nc4a+hi:.1f}]')
for c in ['joint','window','off','freeway_only','urban_only']:
    a4=F[c]['whole_observed'] if c in F else M[(c,'network_sampled_residence')]
    om=F[c]['Omega701'] if c in F else M[(c,'Omega701')]
    b4=R[c]['native_uninserted_wait_veh_h']
    d4a=a4-nc4a; d4b=(b4-hi,b4-lo); d4=(d4a+d4b[0],d4a+d4b[1]); dom=om-nc_om
    print(f'  {c:12s} dΩ {dom:+8.1f} | d④a {d4a:+8.1f} | d④b [{d4b[0]:+7.1f},{d4b[1]:+7.1f}] | d④ [{d4[0]:+7.1f},{d4[1]:+7.1f}] ({100*d4[0]/(nc4a+hi):+.2f}%..{100*d4[1]/(nc4a+lo):+.2f}%) | dΩ밖(a)=d④-dΩ [{d4[0]-dom:+7.1f},{d4[1]-dom:+7.1f}] | dΩ밖(b, links) {d4a-dom:+7.1f}')
print('== controlled arms among themselves (native 0-8100 road+latent, all same interval)')
for a,b in [('joint','off'),('joint','window'),('window','off'),('joint','freeway_only'),('joint','urban_only')]:
    ta=R[a]['native_road_plus_uninserted_veh_h']; tb=R[b]['native_road_plus_uninserted_veh_h']
    oa=F[a]['Omega701'] if a in F else M[(a,'Omega701')]; ob=F[b]['Omega701'] if b in F else M[(b,'Omega701')]
    print(f'  {a}-{b}: dΩ {oa-ob:+8.1f} d④(native) {ta-tb:+8.1f} d④b {R[a]["native_uninserted_wait_veh_h"]-R[b]["native_uninserted_wait_veh_h"]:+8.1f} dΩ밖(a) {(ta-tb)-(oa-ob):+8.1f}')
