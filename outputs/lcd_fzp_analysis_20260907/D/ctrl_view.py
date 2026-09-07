import json,re,glob,os,collections
import pandas as pd
try:
    import ctypes; ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)
except Exception: pass
ROOT="C:/Users/TRLAB/Desktop/찐찐막/VISSIM"; OUT=ROOT+"/outputs/lcd_fzp_analysis_20260907/D"
RUNS=["h11_canon0905_lcd1000_x18_20260907","b0_rl_b0_lcd1000_x18_20260907","g1_base_x18_20260905","h0_nocontrol_lcd1000_x18_20260906"]
rows=[]; rwkeys=set()
for R in RUNS:
    d=f"{ROOT}/evaluation/runs/{R}/decisions_{R}/"
    for sf in sorted(glob.glob(d+"state_*.json")):
        t=int(os.path.basename(sf)[6:12])
        s=json.load(open(sf,encoding='utf-8'))
        af=d+f"action_{t:06d}.json"
        a=json.load(open(af,encoding='utf-8')) if os.path.exists(af) else {}
        lo=s.get('local_observation',{})
        r={'run':R,'t':t}
        for k,v in s.get('ramp_counts',{}).items(): r['rc_'+k]=v
        for L in ['32','29','37','40','66','420','329']:
            r[f'lc_{L}']=lo.get('link_counts',{}).get(L); r[f'ls_{L}']=lo.get('link_stopped_counts',{}).get(L); r[f'lt_{L}']=lo.get('link_queue_tail_pos_m',{}).get(L)
        fm=lo.get('far_measurement',{}).get('link_volume_veh_h',{})
        for c in ['10482','10490','10480','10484','10646','10681']: r['far_'+c]=fm.get(c)
        # queue_bins for link 32 per lane
        qb=lo.get('queue_bins',{})
        for L in ['32']:
            for ln in [1,2,3]:
                items=[(int(k.split('|')[2]),v) for k,v in qb.items() if k.startswith(f'{L}|{ln}|')]
                r[f'qb_{L}_L{ln}_n']=sum(v[0] for _,v in items); r[f'qb_{L}_L{ln}_stop']=sum(v[1] for _,v in items)
                sb=[b for b,v in items if v[1]>0]; r[f'qb_{L}_L{ln}_minstopbin_m']=min(sb)*7 if sb else None
        recs=s.get('vehicle_records',{}).get('records',[])
        for L in [32,31,68]:
            for ln in [1,2,3,4]:
                sel=[x for x in recs if x['link_no']==L and x['lane_no']==ln]
                r[f'vr_{L}_L{ln}_n']=len(sel); r[f'vr_{L}_L{ln}_stop']=sum(1 for x in sel if x['stopped'])
                stp=[x['position_m'] for x in sel if x['stopped']]
                r[f'vr_{L}_L{ln}_minstoppos']=min(stp) if stp else None
        for c in [10482,10490,10480,10484,10646,10681]:
            r[f'vr_{c}_n']=sum(1 for x in recs if x['link_no']==c)
        r['stopped_vehicles']=s.get('stopped_vehicles'); r['total_vehicles']=s.get('total_vehicles'); r['ramp_vehicles']=s.get('ramp_vehicles')
        if a:
            for k,v in a.get('ramp_metering',{}).items(): r['meter_'+k]=v
            for k,v in a.get('green_times',{}).items():
                if k.startswith('SC1001_') or k.startswith('SC1004_'): r['g_'+k]=v
            dg=a.get('diagnostics',{}); md=a.get('metadata',{})
            for k,v in dg.items():
                if k.startswith('wu_pre_refine_SC1001') or k.startswith('wu_phase_price_SC1001') or k.startswith('rw_meter') or k.startswith('leader_selected') or k in ('leader_ramp_queue_veh','leader_ramp_queue_penalty','leader_search_ramp_queue_stress') or 'R_D_W' in k:
                    r['dg_'+k]=v
                    if k.startswith('rw_meter'): rwkeys.add(k)
            for k,v in md.items():
                if k.startswith('ramp_obs_R_D_W') or k.startswith('far_rate_') and 'R_D_W' in k or k.startswith('boundary_out_ramp_split_SC1001') or k in ('controller','controller_variant','tuning_name','F_ramp_mode'):
                    r['md_'+k]=v
            ss=a.get('prediction',{}).get('state_summary',{}) or {}
            r['pred_ramp_queue_R_D_W']=(ss.get('ramp_queue') or {}).get('R_D_W'); r['pred_ramp_queue_total']=ss.get('ramp_queue_total_veh')
            r['N_UF_star']=a.get('N_UF_star'); r['N_P_star']=a.get('N_P_star')
        rows.append(r)
df=pd.DataFrame(rows); df.to_csv(OUT+"/ctrl_view_timeseries.csv",index=False)
print('rw_meter keys:',sorted(rwkeys))
print(df.groupby('run').size())
