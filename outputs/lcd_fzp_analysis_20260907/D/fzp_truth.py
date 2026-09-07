import pandas as pd, numpy as np, sys
try:
    import ctypes; ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)
except Exception: pass
OUT="C:/Users/TRLAB/Desktop/찐찐막/VISSIM/outputs/lcd_fzp_analysis_20260907/D"
RUNS=["h11_canon0905_lcd1000_x18_20260907","b0_rl_b0_lcd1000_x18_20260907","g1_base_x18_20260905","h0_nocontrol_lcd1000_x18_20260906"]
RAMP_NEXT={32:{10482:'R_D_W',10490:'R_D_E'},31:{10480:'R_D_W',10484:'R_D_E'},68:{10646:'R_F_W',10681:'R_F_E'},69:{10644:'R_F_W'},70:{10639:'R_F_E'}}
CONN_POS={32:{10482:1029,10490:1331},31:{10480:735,10484:412},68:{10646:352,10681:117},69:{10644:1740},70:{10639:180}}
def cls(link,nl):
    m=RAMP_NEXT[link]
    if nl in m: return 'ramp_'+m[nl]
    if nl==-1: return 'unknown_or_exit'
    return 'signal_or_other'
rows=[]; conn_rows=[]; prev_rows=[]
for R in RUNS:
    sub=pd.read_parquet(f"{OUT}/{R}_subset.parquet")
    grid=[x+1 for x in range(900,5401,150)]
    for L in [32,31,68,69,70]:
        d=sub[(sub.link==L)&(sub.t.isin(grid))].copy()
        d['cls']=[cls(L,x) for x in d.next_link]
        d['stopped']=d.speed<5
        for (t,ln,c),g in d.groupby(['t','lane','cls']):
            st=g[g.stopped]
            rows.append({'run':R,'t':t,'link':L,'lane':ln,'cls':c,'n':len(g),'stopped':int(g.stopped.sum()),
                         'min_pos':g.pos.min(),'max_pos':g.pos.max(),'q_up_end_pos':st.pos.min() if len(st) else np.nan,'q_down_end_pos':st.pos.max() if len(st) else np.nan,
                         'vmean':g.speed.mean()})
        # prev link distribution at t grid (where did link-L vehicles come from)
        for (t,pl,c),g in d.groupby(['t','prev_link','cls']):
            prev_rows.append({'run':R,'t':t,'link':L,'prev_link':pl,'cls':c,'n':len(g)})
    for L in [10482,10490,10480,10484,10646,10681,10644,10639]:
        d=sub[(sub.link==L)&(sub.t.isin(grid))]
        for t,g in d.groupby('t'):
            conn_rows.append({'run':R,'t':t,'conn':L,'n':len(g),'stopped':int((g.speed<5).sum()),'vmean':g.speed.mean()})
    print(R,'done',flush=True)
pd.DataFrame(rows).to_csv(f"{OUT}/fzp_truth_link_lane_cls.csv",index=False)
pd.DataFrame(conn_rows).to_csv(f"{OUT}/fzp_truth_connectors.csv",index=False)
pd.DataFrame(prev_rows).to_csv(f"{OUT}/fzp_truth_prevlink.csv",index=False)
