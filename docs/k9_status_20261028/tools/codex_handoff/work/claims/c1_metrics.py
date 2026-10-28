# R_CLAIMS c1: recompute percentages and partition identities from git evidence (read only)
import csv, json
E='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/handoff/evidence/'
rows=list(csv.DictReader(open(E+'metrics_0_8100.csv',encoding='utf-8-sig')))
M={}
for r in rows: M[(r['condition'],r['metric'])]=float(r['veh_h'])
conds=['nc','joint','freeway_only','urban_only']
mets=['FW_E_7','local_19','Omega701','outside_Omega_residence','network_sampled_residence','urban_roads','urban','onramps_E','onramps_W','offramps','Omega_minus_W_mainline']
print('== recompute delta/% vs nc; compare to csv fields')
maxerr=0
for r in rows:
    b=M[('nc',r['metric'])]; v=float(r['veh_h'])
    d=v-b; imp=100*(1-v/b)
    e1=abs(d-float(r['delta_veh_h'])); e2=abs(imp-float(r['improvement_percent'])); e3=abs(float(r['baseline_veh_h'])-b)
    maxerr=max(maxerr,e1,e2,e3)
print('max abs err (delta, improvement%, baseline):',maxerr)
for c in conds:
    print(f'-- {c}')
    for m in mets:
        v=M[(c,m)]; b=M[('nc',m)]
        print(f'  {m:28s} {v:12.6f}  d={v-b:+11.6f}  imp={100*(1-v/b):+10.6f}%')
print('== identities')
for c in conds:
    W=M[(c,'Omega701')]-M[(c,'Omega_minus_W_mainline')]
    E_rest=M[(c,'Omega_minus_W_mainline')]-M[(c,'urban_roads')]-M[(c,'onramps_E')]-M[(c,'onramps_W')]-M[(c,'offramps')]
    print(f'{c}: W_main(=Om-OmW)={W:.6f}  E_main_implied={E_rest:.6f}  FW_E_7={M[(c,"FW_E_7")]:.6f}  diff={E_rest-M[(c,"FW_E_7")]:+.2e}')
    print(f'   urban - (urban_roads+offramps) = {M[(c,"urban")]-M[(c,"urban_roads")]-M[(c,"offramps")]:+.2e}')
    print(f'   network - (Omega+outside) = {M[(c,"network_sampled_residence")]-M[(c,"Omega701")]-M[(c,"outside_Omega_residence")]:+.2e}')
    l19x=M[(c,'local_19')]-M[(c,'FW_E_7')]
    print(f'   local19-FW_E7={l19x:.6f} ; minus onramps_E = {l19x-M[(c,"onramps_E")]:.6f} (=4 offramp links + 129/31/68/70 if onramps_E==4 connectors)')
print('== joint delta decomposition of Omega701')
c='joint'
parts={'urban_roads':None,'offramps':None,'onramps_E':None,'onramps_W':None,'FW_E_7':None}
tot=0
for p in parts:
    d=M[(c,p)]-M[('nc',p)]; tot+=d; print(f'  {p:12s} {d:+10.4f}')
dW=(M[(c,'Omega701')]-M[(c,'Omega_minus_W_mainline')])-(M[('nc','Omega701')]-M[('nc','Omega_minus_W_mainline')])
tot+=dW; print(f'  W_main      {dW:+10.4f}'); print(f'  sum         {tot:+10.4f} vs Omega701 delta {M[(c,"Omega701")]-M[("nc","Omega701")]:+.4f}')
for c in ['freeway_only','urban_only']:
    print('== decomposition',c)
    tot=0
    for p in parts:
        d=M[(c,p)]-M[('nc',p)]; tot+=d; print(f'  {p:12s} {d:+10.4f}')
    dW=(M[(c,'Omega701')]-M[(c,'Omega_minus_W_mainline')])-(M[('nc','Omega701')]-M[('nc','Omega_minus_W_mainline')]); tot+=dW
    print(f'  W_main      {dW:+10.4f}  sum {tot:+.4f}')
# independent fzp
F=json.load(open(E+'independent_fzp_counts.json',encoding='utf-8'))
print('== independent FZP vs metrics csv')
for c in ['nc','joint']:
    for k,m in [('FW_E_7','FW_E_7'),('local_19','local_19'),('Omega701','Omega701'),('whole_observed','network_sampled_residence')]:
        print(f'  {c} {k}: fzp={F[c][k]:.9f} csv={M[(c,m)]:.9f} diff={F[c][k]-M[(c,m)]:+.2e}')
print('== window/off (fzp only) vs nc')
for c in ['window','off']:
    for k in ['FW_E_7','local_19','Omega701','whole_observed']:
        v=F[c][k]; b=F['nc'][k]; print(f'  {c} {k}: {v:.6f} d={v-b:+.6f} imp={100*(1-v/b):+.6f}%')
    print(f'  {c} outside(=whole-Omega) {F[c]["whole_observed"]-F[c]["Omega701"]:.6f} vs nc {F["nc"]["whole_observed"]-F["nc"]["Omega701"]:.6f} d={(F[c]["whole_observed"]-F[c]["Omega701"])-(F["nc"]["whole_observed"]-F["nc"]["Omega701"]):+.6f}')
print('== pairwise joint vs off / window (fzp)')
for a,b in [('off','joint'),('window','joint'),('window','off')]:
    for k in ['FW_E_7','local_19','Omega701','whole_observed']:
        print(f'  {a}-{b} {k}: {F[a][k]-F[b][k]:+.6f}  ({100*(F[a][k]/F[b][k]-1):+.4f}%)')
# native
R=json.load(open(E+'run_metadata.json',encoding='utf-8'))
print('== native vs fzp whole')
for r in R:
    c=r['condition']; w=F.get(c,{}).get('whole_observed') or M.get((c,'network_sampled_residence'))
    print(f"  {c}: native_road={r['native_road_veh_h']:.4f} interval={r['native_interval_s']} sampled_0_8100={w:.4f} diff={r['native_road_veh_h']-w:+.4f} latent={r['native_uninserted_wait_veh_h']:.3f} end_latent={r['native_uninserted_end_vehicles']} sum={r['native_road_plus_uninserted_veh_h']:.3f} check={r['native_road_veh_h']+r['native_uninserted_wait_veh_h']-r['native_road_plus_uninserted_veh_h']:+.1e}")
