import pandas as pd, numpy as np, json, glob, os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width',250); pd.set_option('display.max_rows',300); pd.set_option('display.max_columns',40)
ROOT="C:/Users/TRLAB/Desktop/찐찐막/VISSIM"; OUT=ROOT+"/outputs/lcd_fzp_analysis_20260907/D"
runs={'h11':'h11_canon0905_lcd1000_x18_20260907','b0':'b0_rl_b0_lcd1000_x18_20260907','g1':'g1_base_x18_20260905','h0':'h0_nocontrol_lcd1000_x18_20260906','nc200':'nc_rampbn_x18_20260901'}
# 1) route shares of boundary-input vehicles on link 32 (link_in == 32)
print('== vehicles whose FIRST link is 32 (in_SC1001_W boundary input): next link after 32, t_in>=900')
for k,R in runs.items():
    veh=pd.read_parquet(f'{OUT}/{R}_vehicles.parquet'); tr=pd.read_parquet(f'{OUT}/{R}_transitions.parquet')
    v32=veh[(veh.link_in==32)&(veh.t_in>=900)]
    nxt=tr[(tr.from_link==32)].drop_duplicates('no').set_index('no').to_link
    d=nxt.reindex(v32.index).fillna(-1).astype(int).map({10482:'R_D_W',10490:'R_D_E',-1:'never_left'}).fillna('signal')
    c=d.value_counts(); tot=len(d)
    print(f"  {k:6s} n={tot:5d}  " + '  '.join(f"{i}={c.get(i,0)} ({c.get(i,0)/tot:.0%})" for i in ['R_D_W','R_D_E','signal','never_left']))
    # R_D_W feed split 10482 (from 32) vs 10480 (from 31)
    f=tr[tr.to_link.isin([10482,10480])&(tr.t>=900)].to_link.value_counts()
    print(f"         R_D_W feed t>=900: via 10482(link32,pre-signal)={f.get(10482,0)}  via 10480(link31,W_out)={f.get(10480,0)}  share pre-signal={f.get(10482,0)/max(1,f.sum()):.2f}")
# 2) gate peel-off / in_SC1001_W keys and metering rationale keys in h11 actions
def dump(R,t,pats,sec=('diagnostics','metadata')):
    a=json.load(open(f'{ROOT}/evaluation/runs/{R}/decisions_{R}/action_{t:06d}.json',encoding='utf-8'))
    for s in sec:
        for k,v in a[s].items():
            if re.search(pats,k) and not k.startswith('meta_'):
                print(f'   [{s}] {k} = {repr(v)[:110]}')
for t in [2100,3600]:
    print(f'\n== h11 t={t}: gate peel-off / in_SC1001_W keys'); dump(runs['h11'],t,r'peel|in_SC1001_W|gate_.*1001|arrival.*1001|1001.*arriv')
print('\n== h11 t=2700: leader/freeway metering rationale keys (nuf|N_UF|meter|alloc|F_W|density|blocked|ramp_queue)')
dump(runs['h11'],2700,r'nuf|N_UF|leader_meter|alloc|agent_F_W|density|blocked|ramp_queue|far_ramp|merge_R_D_W|R_D_W',sec=('diagnostics',))
print('\n== g1 t=2700: same keys')
dump(runs['g1'],2700,r'nuf|N_UF|leader_meter|alloc|agent_F_W|density|blocked|ramp_queue|far_ramp|merge_R_D_W|R_D_W',sec=('diagnostics',))
# 3) vertex flips
v=pd.read_csv(OUT+'/ctrl_view_timeseries.csv'); short={vv:k for k,vv in runs.items()}; v['run']=v.run.map(short)
v=v[v.t>=900]
print('\n== SC1001 vertex flips (p3<=25) and meter R_D_W closure stats per run, decisions t>=900 (31 decisions)')
for k in ['h11','b0','g1']:
    d=v[v.run==k]
    print(f"  {k}: p3<=25 at t={d[d.g_SC1001_p3<=25].t.tolist()} ; meter_R_D_W==0: {int((d.meter_R_D_W==0).sum())}/31, <=300: {int((d.meter_R_D_W<=300).sum())}/31, >=1200: {int((d.meter_R_D_W>=1200).sum())}/31 ; rc_R_D_W>=115: {int((d.rc_R_D_W>=115).sum())}/31")
# 4) plot
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    ts=pd.read_csv(OUT+'/timeline_R_D_W_link32.csv')
    fig,axes=plt.subplots(3,1,figsize=(13,11),sharex=True)
    for ax,k,title in zip(axes,['h11','b0','g1'],['h11 (lcd1000, canon0905) TTT 8629','b0 (lcd1000, RL_B0) TTT 8313','g1 (lcd200, canon0905) TTT 7741']):
        d=ts[ts.run==k].set_index('t')
        ax.bar(d.index,d.meter_R_D_W/10,width=140,color='#bbb',label='meter R_D_W /10 [veh/h]')
        ax.plot(d.index,d.rc_R_D_W,'k--',label='model ramp_counts R_D_W (=connector stock)')
        ax.plot(d.index,d.L1_ramp_stop+d.L2_ramp_stop,'r-o',ms=3,label='fzp ramp-bound stopped on link32 L1+L2')
        ax.plot(d.index,d.unk_n,'m-',label='fzp link32 vehicles that never leave (stuck)')
        ax.plot(d.index,d.L1_ramp_qlen_m/5,'b-',label='L1 ramp queue length /5 [m]')
        ax.plot(d.index,d.g_SC1001_p3,'g-',label='SC1001 p3 green [s]')
        ax.set_title(title); ax.grid(alpha=.3); ax.set_ylim(0,300)
        if k=='h11': ax.legend(fontsize=8,ncol=3,loc='upper left')
    axes[-1].set_xlabel('sim sec')
    plt.tight_layout(); plt.savefig(OUT+'/timeline_meter_vs_link32_queue.png',dpi=110); print('\nplot saved')
except Exception as e: print('plot failed',e)
