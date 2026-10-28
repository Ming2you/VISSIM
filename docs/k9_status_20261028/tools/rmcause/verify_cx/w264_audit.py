import json,glob,os,re,sys,time
D=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/decisions_sdmpc31_sdmpc9000_s29'
files=sorted(glob.glob(os.path.join(D,'action_*.json')))
files=[f for f in files if re.search(r"action_[0-9]{6}[.]json$",f)]
if len(sys.argv)>1: files=[f for f in files if any(a in f for a in sys.argv[1:])]
dec=json.JSONDecoder()
out=[]
t0=time.time()
for f in files:
    s=open(f,encoding='utf-8',errors='replace').read()
    hits=[m.start() for m in re.finditer(r'"meter_neighbor_audit"\s*:\s*\{',s)]
    rec={'file':os.path.basename(f),'n_hits':len(hits)}
    best=None
    for h in hits:
        j=s.index('{',h)
        try:
            obj,_=dec.raw_decode(s,j)
        except Exception as e:
            continue
        if isinstance(obj,dict) and 'baseline_objective' in obj:
            if best is None or len(json.dumps(obj))>len(json.dumps(best)): best=obj
    # also selected objective
    m=re.search(r'"prediction_ttt_reduction"\s*:\s*(-?[0-9.eE+-]+)',s)
    rec['prediction_ttt_reduction_first']=float(m.group(1)) if m else None
    if best:
        rows=best.get('candidates',[])
        base=best.get('baseline_objective')
        sel=best.get('selected')
        feas=[r for r in rows if r.get('feasible')]
        mind=min((r['delta_veh_h'] for r in feas),default=None)
        rec.update(selected=sel, baseline=base, n_cand=len(rows), n_feas=len(feas), min_delta=mind,
                   n_budget=best.get('distinct_budget_incumbents'))
    out.append(rec)
    print(json.dumps(rec), flush=True)
print('elapsed',time.time()-t0, file=sys.stderr)
