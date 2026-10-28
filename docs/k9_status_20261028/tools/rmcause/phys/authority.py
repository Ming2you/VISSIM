# Metering authority arithmetic on v3c3 NC (read-only, uses scan outputs). 2026-10-24
import json
D=json.load(open('out_all.json',encoding='utf-8'))
# storage behind meter head: connector length upstream of head * lanes + from-link length on the feeding lanes, 7 m per vehicle (assumption)
GEOM={'10639':dict(lanes=1,head=314.8,from_len=180.5,from_lanes=1),
      '10681':dict(lanes=2,head=290.7,from_len=118.0,from_lanes=2),
      '10490':dict(lanes=1,head=272.6,from_len=301.9,from_lanes=1),
      '10484':dict(lanes=1,head=377.1,from_len=412.3,from_lanes=1)}
JAM=7.0
MINLANE=360.0  # g2 = 1 veh/10 s/lane (memory exact-pass count, not re-measured here)
out={}
for r,g in GEOM.items():
    g['storage_head_veh']=round(g['head']*g['lanes']/JAM)
    g['storage_from_veh']=round(g['from_len']*g['from_lanes']/JAM)
    g['storage_total_veh']=g['storage_head_veh']+g['storage_from_veh']
    g['min_rate_g2']=MINLANE*g['lanes']
out['geom']=GEOM
rows={}
for t in ['nc_s31','nc_s41','nc_s43','nc_s47','nc_s53']:
    f=D[t]['flows']
    row={}
    for r,g in GEOM.items():
        a=(f['1800-2700']['arr_'+r]+f['2700-3600']['arr_'+r])/2
        red=max(0.0,a-g['min_rate_g2'])
        fill=(g['storage_total_veh']/red*60) if red>0 else None
        fill_close=g['storage_total_veh']/a*60
        nc_q=max(f['1800-2700']['qmax_'+r],f['2700-3600']['qmax_'+r])
        row[r]=dict(arrival_vph=a,restrictable_g2_vph=red,fill_min_at_g2=round(fill,1) if fill else None,fill_min_closed=round(fill_close,1),nc_qmax_peak=nc_q)
    rows[t]=row
out['peak_1800_3600']=rows
# upper bound of mainline delay removable: zone delay minus stage1-RM residual (mean of 4 stage1 RM runs), floor 0
rm=['st1v1_s31_rm','st1v1_s41_rm','st1v2_s31_rm','st1v2_s41_rm']
res={z:sum(D[t]['zones'][z]['delay_veh_h_vref108'] for t in rm)/4 for z in ['B1_4200_5300','M_5300_6800','B2_6800_7900']}
out['stage1_rm_residual_delay']={k:round(v,1) for k,v in res.items()}
ub={}
for t in ['nc_s31','nc_s41','nc_s43','nc_s47','nc_s53','cf_s29_none']:
    z=D[t]['zones']
    floor_ub=sum(max(0.0,z[k]['delay_veh_h_vref108']-res[k]) for k in res)
    gen_ub=z['M_5300_6800']['delay_veh_h_vref108']+z['B2_6800_7900']['delay_veh_h_vref108']+max(0.0,z['B1_4200_5300']['delay_veh_h_vref108']-60.7)
    ub[t]=dict(fw_e_chain=D[t]['chain_veh_h_5s'],ub_stage1floor=round(floor_ub,1),ub_stage1floor_pct=round(100*floor_ub/D[t]['chain_veh_h_5s'],1),
              ub_generous=round(gen_ub,1),ub_generous_pct=round(100*gen_ub/D[t]['chain_veh_h_5s'],1))
out['upper_bound']=ub
json.dump(out,open('authority.json','w',encoding='utf-8'),indent=1)
print(json.dumps(out,indent=1))
