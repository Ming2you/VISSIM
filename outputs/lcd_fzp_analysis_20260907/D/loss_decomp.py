import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_rows',300); pd.set_option('display.max_columns',40)
runs={'h11':'h11_canon0905_lcd1000_x18_20260907','b0':'b0_rl_b0_lcd1000_x18_20260907','g1':'g1_base_x18_20260905','h0':'h0_nocontrol_lcd1000_x18_20260906'}
lt={k:pd.read_parquet(f'{v}_link_time.parquet') for k,v in runs.items()}
# link-level TTT (veh.h) full run and after 900
def link_ttt(df,t0=0): 
    d=df[df.t>=t0]; return d.groupby('link').agg(ttt=('n',lambda s:s.sum()*5/3600), stop_h=('stopped',lambda s:s.sum()*5/3600))
L={k:link_ttt(v) for k,v in lt.items()}
tot={k:v.ttt.sum() for k,v in L.items()}; print('TTT veh.h by run:',{k:round(x,1) for k,x in tot.items()})
cmp=pd.DataFrame({'h11':L['h11'].ttt,'b0':L['b0'].ttt,'h0':L['h0'].ttt,'g1':L['g1'].ttt}).fillna(0)
cmp['h11-h0']=cmp.h11-cmp.h0; cmp['b0-h0']=cmp.b0-cmp.h0
cmp.to_csv('link_ttt_by_run.csv')
print('\n== top 25 links by h11-h0 (veh.h)'); print(cmp.sort_values('h11-h0',ascending=False).head(25).round(1).to_string())
print('\n== bottom 8 links by h11-h0'); print(cmp.sort_values('h11-h0').head(8).round(1).to_string())
print('\n== top 15 links by b0-h0'); print(cmp.sort_values('b0-h0',ascending=False).head(15).round(1).to_string())
sel=[32,31,26,2,24,10491,10481,10479,10483,10482,10480,10490,10484,30,38,39,66,69,70,68,420,329]
print('\n== selected links'); print(cmp.loc[[x for x in sel if x in cmp.index]].round(1).to_string())
# time profile of h11-h0 loss for link 32, 26, 2, 10491, 10481 per 300 s
def prof(link):
    out={}
    for k in ['h11','b0','h0','g1']:
        d=lt[k][lt[k].link==link].copy(); d['bin']=(d.t//300)*300
        out[k]=d.groupby('bin').n.sum()*5/3600
    return pd.DataFrame(out).fillna(0)
for link in [32,10491,10481,26,2]:
    p=prof(link); p['h11-h0']=p.h11-p.h0; p['b0-h0']=p.b0-p.h0
    print(f'\n== link {link} TTT per 300 s bin (veh.h)'); print(p.round(1).T.to_string())
# stopped counts time series at 150s grid for off-ramps and freeway
grid=[x+1 for x in range(900,5401,150)]
for link in [10491,10481]:
    rows={}
    for k in ['h11','b0','g1','h0']:
        d=lt[k][(lt[k].link==link)&(lt[k].t.isin(grid))].set_index('t')
        rows[k+'_n']=d.n; rows[k+'_stop']=d.stopped
    print(f'\n== off-ramp connector {link}: n / stopped at 150 s grid'); print(pd.DataFrame(rows).fillna(0).astype(int).T.to_string())
