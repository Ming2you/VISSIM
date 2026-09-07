import pandas as pd, numpy as np, json, glob, os, sys
sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width',250); pd.set_option('display.max_rows',300); pd.set_option('display.max_columns',40)
ROOT="C:/Users/TRLAB/Desktop/찐찐막/VISSIM"; OUT=ROOT+"/outputs/lcd_fzp_analysis_20260907/D"
runs={'h11':'h11_canon0905_lcd1000_x18_20260907','b0':'b0_rl_b0_lcd1000_x18_20260907','g1':'g1_base_x18_20260905','h0':'h0_nocontrol_lcd1000_x18_20260906','nc200':'nc_rampbn_x18_20260901'}
lt={k:pd.read_parquet(f'{OUT}/{v}_link_time.parquet') for k,v in runs.items()}
L={k:v.groupby('link').n.sum()*5/3600 for k,v in lt.items()}
cmp=pd.DataFrame(L).fillna(0)
print('TTT totals', cmp.sum().round(1).to_dict())
cmp['ctl200']=cmp.g1-cmp.nc200; cmp['ctl1000_h11']=cmp.h11-cmp.h0; cmp['ctl1000_b0']=cmp.b0-cmp.h0
cmp['DiD_h11']=cmp.ctl1000_h11-cmp.ctl200; cmp['DiD_b0']=cmp.ctl1000_b0-cmp.ctl200; cmp['net_nc']=cmp.h0-cmp.nc200
cmp.to_csv(OUT+'/link_ttt_DiD.csv')
print('\n== control effect by link: lcd200 (g1-nc200) vs lcd1000 (h11-h0, b0-h0); DiD = lcd1000 effect - lcd200 effect. Top 20 by DiD_h11')
print(cmp.sort_values('DiD_h11',ascending=False).head(20).round(1).to_string())
print('\n== bottom 10 by DiD_h11'); print(cmp.sort_values('DiD_h11').head(10).round(1).to_string())
print('\n== network effect on no-control (h0 - nc200) top/bottom 8')
print(cmp.sort_values('net_nc',ascending=False).head(8).round(1).to_string()); print(cmp.sort_values('net_nc').head(8).round(1).to_string())
sel=[32,31,26,2,74,24,10491,10481,10482,10480,10490,10484,30,38,39,66,69,70,68,420,329,10644,10639,10646,10681]
print('\n== selected'); print(cmp.loc[[x for x in sel if x in cmp.index]].round(1).to_string())
# 10481 stock nc200
grid=[x+1 for x in range(900,5401,150)]
d=lt['nc200'][(lt['nc200'].link==10481)&(lt['nc200'].t.isin(grid))].set_index('t')
print('\n== nc200 10481 stock n/stopped:', list(zip(d.index.tolist(), d.n.tolist(), d.stopped.tolist())))
# freeway 26 near R_D_W merge (10482 -> 26 @3830; 10480 @3525; off-ramp 10491 leaves 26 @3651, 10479 @3425): density by 500 m bin at T
sub={k:pd.read_parquet(f'{OUT}/{v}_subset.parquet') for k,v in runs.items()}
T=[x+1 for x in [1500,2100,2700,3000,3600,4500]]
for link,bins in [(26,list(range(2500,5501,500))),(2,list(range(3000,4701,500)))]:
    print(f'\n== link {link}: mean vehicles per 500 m bin (all lanes) averaged over T snapshots {T}, and share stopped')
    rows={}
    for k in runs:
        s=sub[k]; d=s[(s.link==link)&(s.t.isin(T))].copy(); d['pb']=(d.pos//500)*500
        g=d.groupby('pb').agg(n=('no','size'),st=('speed',lambda x:(x<5).mean()),v=('speed','mean'))
        rows[k+'_n']=(g.n/len(T)).round(1); rows[k+'_v']=g.v.round(0)
    print(pd.DataFrame(rows).fillna(0).loc[[b for b in bins if b in pd.DataFrame(rows).index]].to_string())
# ---- contiguous stopline queue for link 32 from queue_bins (adapter algorithm) per lane
LEN32=1963.4; HEAD=30.0; BINM=7.0
def contig(qb, link='32'):
    by={}
    for k,v in qb.items():
        p=k.split('|')
        if p[0]!=link: continue
        by.setdefault(p[1],{})[int(p[2])]=(float(v[0]),float(v[1]))
    out={}
    for lane,bins in by.items():
        occ=[i for i,(t,s) in bins.items() if t>0]
        if not occ: out[lane]=0.0; continue
        head=(max(occ)+1)*BINM
        if LEN32-head>HEAD: out[lane]=0.0; continue
        q=0.0
        for i in sorted(bins,reverse=True):
            t,s=bins[i]
            if t<=0: continue
            if t>s: break
            q+=s
        out[lane]=q
    return out
rows=[]
for k in ['h11','b0','g1','h0']:
    d=f"{ROOT}/evaluation/runs/{runs[k]}/decisions_{runs[k]}/"
    for sf in sorted(glob.glob(d+'state_*.json')):
        t=int(os.path.basename(sf)[6:12])
        if t<900: continue
        s=json.load(open(sf,encoding='utf-8'))
        lo=s['local_observation']; c=contig(lo.get('queue_bins',{}))
        r={'run':k,'t':t,'lc_32':lo['link_counts'].get('32'),'ls_32':lo['link_stopped_counts'].get('32'),'contig_L1':c.get('1',0),'contig_L2':c.get('2',0),'contig_L3':c.get('3',0)}
        r['contig_sum']=sum(c.values()); rows.append(r)
cq=pd.DataFrame(rows)
f=pd.read_csv(OUT+'/fzp_truth_link_lane_cls.csv'); short={v:k for k,v in runs.items()}; f['run']=f.run.map(short); f['t']=f.t-1
d32=f[f.link==32]
def agg(g):
    ramp=g[g.cls.isin(['ramp_R_D_W','ramp_R_D_E'])]; sig=g[g.cls=='signal_or_other']; unk=g[g.cls=='unknown_or_exit']
    return pd.Series({'fzp_ramp_stop':ramp.stopped.sum(),'fzp_sig_stop':sig.stopped.sum(),'fzp_unk_stop':unk.stopped.sum(),'fzp_sig_stop_L3':sig[sig.lane==3].stopped.sum(),'fzp_stop_all':g.stopped.sum(),'fzp_n':g.n.sum()})
fz=d32.groupby(['run','t']).apply(agg).reset_index()
m=cq.merge(fz,on=['run','t'],how='left')
v=pd.read_csv(OUT+'/ctrl_view_timeseries.csv'); v['run']=v.run.map(short)
m=m.merge(v[['run','t','rc_R_D_W','g_SC1001_p3','g_SC1001_p1','meter_R_D_W','md_ramp_obs_R_D_W_queue_veh','pred_ramp_queue_R_D_W']],on=['run','t'],how='left')
m['queue_frac_model']=(m.contig_sum/m.lc_32).round(2)
m['true_ramp_total']=m.rc_R_D_W+m.fzp_ramp_stop
m.to_csv(OUT+'/model_vs_truth_link32_ramp.csv',index=False)
TT=[1500,1800,2100,2400,2700,3000,3600,4500]
for k in ['h11','b0','g1']:
    print(f'\n== {k}: MODEL stopline-contiguous queue on link 32 (adapter walk from queue_bins, per lane) vs FZP truth by class; ramp reservoir model (rc_R_D_W=connector stock) vs truth (connector + ramp-bound stopped on 32)')
    print(m[(m.run==k)&(m.t.isin(TT))].set_index('t')[['lc_32','ls_32','contig_L1','contig_L2','contig_L3','contig_sum','queue_frac_model','fzp_sig_stop','fzp_ramp_stop','fzp_unk_stop','fzp_stop_all','rc_R_D_W','md_ramp_obs_R_D_W_queue_veh','pred_ramp_queue_R_D_W','true_ramp_total','meter_R_D_W','g_SC1001_p1','g_SC1001_p3']].round(0).to_string())
