import sys, os, glob, time
try:
    import ctypes; ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)  # BELOW_NORMAL
except Exception: pass
import numpy as np, pandas as pd
ROOT="C:/Users/TRLAB/Desktop/찐찐막/VISSIM"
OUT=ROOT+"/outputs/lcd_fzp_analysis_20260907/D"
RUNS=sys.argv[1:] or ["h11_canon0905_lcd1000_x18_20260907","b0_rl_b0_lcd1000_x18_20260907","g1_base_x18_20260905","h0_nocontrol_lcd1000_x18_20260906"]
LINKS={32,31,68,69,70,66,420,329,26,2,24,30,38,39,10482,10490,10480,10484,10646,10681,10644,10639,10636,10637,10640}
for R in RUNS:
    t0=time.time()
    f=glob.glob(f"{ROOT}/evaluation/runs/{R}/vissim_eval/*.fzp")[0]
    # find header line
    skip=0
    with open(f,'r',encoding='latin-1') as fh:
        for i,line in enumerate(fh):
            if line.startswith('$VEHICLE'): skip=i+1; break
    parts=[]; trans_parts=[]
    reader=pd.read_csv(f,sep=';',skiprows=skip,header=None,usecols=[0,1,2,3,4,6],
                       names=['t','no','link','lane','pos','speed'],
                       dtype={'t':'float32','no':'int32','link':'int64','lane':'int8','pos':'float32','speed':'float32'},
                       chunksize=2_000_000,encoding='latin-1')
    allrows=[]
    for ch in reader:
        allrows.append(ch)
    df=pd.concat(allrows,ignore_index=True); del allrows
    n=len(df); print(R,'rows',n,'load',round(time.time()-t0,1),flush=True)
    df['t']=df['t'].round().astype('int32')
    df.sort_values(['no','t'],inplace=True,kind='stable'); df.reset_index(drop=True,inplace=True)
    # transitions
    same=(df['no'].values[1:]==df['no'].values[:-1])
    chg=same & (df['link'].values[1:]!=df['link'].values[:-1])
    idx=np.nonzero(chg)[0]
    trans=pd.DataFrame({'no':df['no'].values[idx],'t':df['t'].values[idx+1],'from_link':df['link'].values[idx],'to_link':df['link'].values[idx+1]})
    trans.to_parquet(f"{OUT}/{R}_transitions.parquet",index=False)
    # per-vehicle route string (link sequence)
    # first-appearance link per vehicle
    first=df.groupby('no',sort=False).agg(t_in=('t','min'),t_out=('t','max'),link_in=('link','first'),link_out=('link','last'),nrows=('t','size'))
    first.to_parquet(f"{OUT}/{R}_vehicles.parquet")
    # subset rows
    sub=df[df['link'].isin(LINKS)].copy()
    # next link after each (no,link) segment: use transitions (first transition from that link for that vehicle)
    tr=trans.drop_duplicates(['no','from_link'],keep='first').set_index(['no','from_link'])['to_link']
    key=pd.MultiIndex.from_arrays([sub['no'].values,sub['link'].values])
    sub['next_link']=tr.reindex(key).values
    sub['next_link']=sub['next_link'].fillna(-1).astype('int64')
    # previous link
    trp=trans.drop_duplicates(['no','to_link'],keep='last').set_index(['no','to_link'])['from_link']
    sub['prev_link']=trp.reindex(key).values
    sub['prev_link']=sub['prev_link'].fillna(-1).astype('int64')
    sub.to_parquet(f"{OUT}/{R}_subset.parquet",index=False)
    # network-wide per-second totals (TTT integrand) and stopped counts
    tot=df.groupby('t').agg(n=('no','size'),stopped=('speed',lambda s:(s<5).sum()))
    tot.to_csv(f"{OUT}/{R}_network_totals.csv")
    # per link per t counts for all links (for link×time loss)
    lk=df.groupby(['link','t']).agg(n=('no','size'),stopped=('speed',lambda s:(s<5).sum()),vmean=('speed','mean')).reset_index()
    lk.to_parquet(f"{OUT}/{R}_link_time.parquet",index=False)
    print(R,'done',round(time.time()-t0,1),'TTT veh.h',n*5/3600,flush=True)
    del df,sub,trans
