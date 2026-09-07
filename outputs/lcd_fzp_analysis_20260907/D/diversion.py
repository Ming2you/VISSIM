import pandas as pd, numpy as np, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width',250); pd.set_option('display.max_rows',300); pd.set_option('display.max_columns',40)
ROOT="C:/Users/TRLAB/Desktop/찐찐막/VISSIM"; OUT=ROOT+"/outputs/lcd_fzp_analysis_20260907/D"
runs={'h11':'h11_canon0905_lcd1000_x18_20260907','b0':'b0_rl_b0_lcd1000_x18_20260907','g1':'g1_base_x18_20260905','h0':'h0_nocontrol_lcd1000_x18_20260906'}
if os.path.exists(OUT+'/nc_rampbn_x18_20260901_transitions.parquet'): runs['nc200']='nc_rampbn_x18_20260901'
# 1) transitions out of link 32 per 300 s bin, by destination
rows=[]
for k,R in runs.items():
    tr=pd.read_parquet(f'{OUT}/{R}_transitions.parquet')
    t32=tr[tr.from_link==32].copy(); t32['bin']=(t32.t//300)*300
    t32['dest']=t32.to_link.map({10482:'R_D_W',10490:'R_D_E'}).fillna('signal')
    p=t32.pivot_table(index='bin',columns='dest',values='no',aggfunc='count',fill_value=0)
    p['ramp_share']=(p.get('R_D_W',0)+p.get('R_D_E',0))/p.sum(axis=1).replace(0,np.nan)
    p['run']=k; rows.append(p.reset_index())
    # arrivals to 10481 / 10491 per bin and total vehicles created per bin
    a=tr[tr.to_link.isin([10481,10491,10482,10480])].copy(); a['bin']=(a.t//300)*300
    pa=a.pivot_table(index='bin',columns='to_link',values='no',aggfunc='count',fill_value=0)
    print(f'\n== {k}: transitions INTO off-ramps 10481(FW_E->32) 10491(FW_W->32) and on-ramp conns 10482 10480 per 300 s'); print(pa.T.to_string())
div=pd.concat(rows); div.to_csv(OUT+'/link32_exit_by_dest_300s.csv',index=False)
for k in runs:
    d=div[div.run==k].set_index('bin')
    print(f'\n== {k}: vehicles LEAVING link 32 per 300 s by destination (ramp_share = ramp / all exits)')
    print(d.drop(columns='run').T.round(2).to_string())
# 2) totals over control period 900-5400
print('\n== total exits from link 32 t>=900 by dest')
print(div[div.bin>=900].groupby('run')[[c for c in ['R_D_W','R_D_E','signal'] if c in div.columns]].sum())
# 3) position histogram of ramp-bound vehicles on link 32 by lane while connector saturated
sub={k:pd.read_parquet(f'{OUT}/{R}_subset.parquet') for k,R in runs.items() if k in ('h11','g1','b0')}
def hist(k,ts,label):
    s=sub[k]; d=s[(s.link==32)&(s.t.isin(ts))&(s.next_link.isin([10482,10490]))]
    d=d.assign(posbin=(d.pos//200)*200)
    p=d.pivot_table(index='posbin',columns='lane',values='no',aggfunc='count',fill_value=0)
    st=d[d.speed<5].pivot_table(index='posbin',columns='lane',values='no',aggfunc='count',fill_value=0)
    print(f'\n== {k} {label}: ramp-bound (next 10482/10490) vehicles on link 32 by 200 m pos bin x lane  [all | stopped]  (summed over {len(ts)} snapshots)')
    print(pd.concat({'all':p,'stopped':st},axis=1).fillna(0).astype(int).to_string())
hist('h11',[x+1 for x in range(2250,3001,150)],'t=2250..3000 (rc saturated 116-143)')
hist('g1',[x+1 for x in range(2400,2701,150)]+[x+1 for x in range(4650,5251,150)],'t=2400..2700 & 4650..5250 (rc 107-140)')
hist('b0',[x+1 for x in range(2250,2701,150)],'t=2250..2700 (rc 78-140)')
# 4) dwell time of link-32 vehicles by class at T (h11): time since first appearance on link 32
T=[x+1 for x in [2400,3000,3600,4500]]
for k in ['h11','b0','g1']:
    s=sub[k]; d32=s[s.link==32]
    first=d32.groupby('no').t.min()
    for t in T:
        snap=d32[d32.t==t].copy(); snap['dwell']=t-first.reindex(snap.no).values
        snap['cls']=snap.next_link.map({10482:'R_D_W',10490:'R_D_E',-1:'unk'}).fillna('sig')
        g=snap.groupby('cls').dwell.describe()[['count','mean','50%','max']]
        print(f'\n== {k} t={t}: dwell time on link 32 so far [s] by class'); print(g.round(0).to_string())
