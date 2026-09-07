import pandas as pd, numpy as np, json, glob, os, sys
sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width',250); pd.set_option('display.max_rows',300); pd.set_option('display.max_columns',40)
ROOT="C:/Users/TRLAB/Desktop/찐찐막/VISSIM"; OUT=ROOT+"/outputs/lcd_fzp_analysis_20260907/D"
runs={'h11':'h11_canon0905_lcd1000_x18_20260907','b0':'b0_rl_b0_lcd1000_x18_20260907','g1':'g1_base_x18_20260905','h0':'h0_nocontrol_lcd1000_x18_20260906','nc200':'nc_rampbn_x18_20260901'}
# (a) observability gap
m=json.load(open(ROOT+'/evaluation/real_world_modi_control_distributed_20260728/detector_local_mapping_distributed_core17legs4f_20260903_blindfix20260905b.json',encoding='utf-8'))
s=json.load(open(f"{ROOT}/evaluation/runs/{runs['h11']}/decisions_{runs['h11']}/state_003000.json",encoding='utf-8'))
obs=set(str(x) for x in m['observable_links']); have=set(s['local_observation']['link_counts'].keys())
miss=obs-have
print(f"(a) adapter mapping observable={len(obs)}, scanned link_counts={len(have)}, observable-but-not-scanned={len(miss)}; 31 missing? {'31' in miss}, 68? {'68' in miss}, 69? {'69' in miss}, 70? {'70' in miss}, 31 in l2m? {'31' in m['link_to_movements']}, 68 in l2m? {'68' in m['link_to_movements']}")
print('    l2m[31]=',[x['movement'] for x in m['link_to_movements'].get('31',[])][:6], ' l2m[68]=',[x['movement'] for x in m['link_to_movements'].get('68',[])][:6])
# (b) vehicle creation + link-32 entries per 300 s
print('\n(b) vehicles created (total) and link-32 boundary entries per 300 s bin')
rows={}
for k,R in runs.items():
    veh=pd.read_parquet(f'{OUT}/{R}_vehicles.parquet')
    e=veh[veh.link_in==32].copy(); e['bin']=(e.t_in//300)*300
    rows[k]=e.groupby('bin').size(); print(f'   {k}: total vehicles created={len(veh)}, on link32 input={len(e)}')
print(pd.DataFrame(rows).fillna(0).astype(int).T.to_string())
# (c) FW_E (74+2) TTT per 300 s and 10481 stock
lt={k:pd.read_parquet(f'{OUT}/{v}_link_time.parquet') for k,v in runs.items()}
print('\n(c) FW_E links 74+2 TTT per 300 s bin (veh.h)')
rows={}
for k in runs:
    d=lt[k][lt[k].link.isin([74,2])].copy(); d['bin']=(d.t//300)*300; rows[k]=d.groupby('bin').n.sum()*5/3600
print(pd.DataFrame(rows).fillna(0).round(0).astype(int).T.to_string())
print('\n(c2) 10481 off-ramp stock (n) at 300 s bins (mean over bin)')
rows={}
for k in runs:
    d=lt[k][lt[k].link==10481].copy(); d['bin']=(d.t//300)*300; rows[k]=d.groupby('bin').n.mean()
print(pd.DataFrame(rows).fillna(0).round(0).astype(int).T.to_string())
# (d) leader penalties across decisions
print('\n(d) leader ramp-queue vs density penalty per decision (h11 / g1 / b0)')
for k in ['h11','g1','b0']:
    R=runs[k]; out=[]
    for af in sorted(glob.glob(f'{ROOT}/evaluation/runs/{R}/decisions_{R}/action_*.json')):
        t=int(os.path.basename(af)[7:13]); 
        if t<900: continue
        dg=json.load(open(af,encoding='utf-8'))['diagnostics']
        out.append((t,round(dg.get('leader_ramp_queue_veh',np.nan)),dg.get('leader_ramp_queue_penalty'),round(dg.get('leader_density_penalty',np.nan)),round(dg.get('leader_search_density_stress',np.nan),2),dg.get('leader_candidate_best_intent_N_UF_star'),dg.get('leader_selected_N_UF_star')))
    df=pd.DataFrame(out,columns=['t','ramp_q_veh','ramp_q_pen','dens_pen','dens_stress','best_intent_NUF','selected_NUF'])
    print(f'  {k}: ramp_q_pen nonzero in {int((df.ramp_q_pen>0).sum())}/{len(df)}; ramp_q_veh median {df.ramp_q_veh.median():.0f} max {df.ramp_q_veh.max():.0f}; dens_pen median {df.dens_pen.median():.0f}; dens_stress median {df.dens_stress.median():.2f}; best_intent_NUF==1440 in {int((df.best_intent_NUF==1440).sum())}/{len(df)}; selected_NUF median {df.selected_NUF.median():.0f}')
    df.to_csv(f'{OUT}/leader_penalties_{k}.csv',index=False)
# (e) compact decision-time table
mv=pd.read_csv(OUT+'/model_vs_truth_link32_ramp.csv'); T=[1500,1800,2100,2400,2700,3000,3600,4500]
mv[mv.t.isin(T)].to_csv(OUT+'/decision_time_truth_vs_model.csv',index=False); print('\n(e) saved decision_time_truth_vs_model.csv')
