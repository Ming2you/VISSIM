r"""Where along the freeway does the model's metering response diverge from native?

Native: map each FZP row (link, pos) to a canonical cell via geometry['chains'] offsets,
average the per-cell occupancy over the window, and difference rm - none.
Model: same window from the same common state, difference replay - hold.
"""
import sys, json, importlib.util
from collections import defaultdict
from pathlib import Path

OUTJSON = 'D:\\VISSIM-merge\\evidence\\spatial_cells.json'
ROOT=Path(r'D:\VISSIM-merge\sim3')
CAL=ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
RD=ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2'
BASE=CAL/'res10_20260922/boundary_literature_v1'
Q=Path(r'D:\VISSIM_runs\20260922_fw080_urban090_controls')
sys.path[:0]=[str(CAL),str(RD),str(ROOT/'.review-deps'),str(ROOT)]
from canonical_harness import load_base_model
import evaluate_response as er
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))

CUT=float(__import__('os').environ.get('SR_CUTOFF','3450.1')); WIN=450.
FZP={'none':Path(r'D:\VISSIM_runs\20260922_both_off_half\fw080_urban090_nc9000\run\vissim_eval\baseline_001.fzp'),
     'rm'  :Q/'rm/run/vissim_eval/baseline_001.fzp'}

def cellmap(geom):
    """(link)->(road, offset_m); plus cell boundary lookup per road"""
    link={}
    for road,rs in geom['chains'].items():
        for r in rs: link[str(r['link'])]=(road,float(r['offset_m']))
    bounds=defaultdict(list)
    for c in geom['cells']: bounds[c['road']].append((c['start_m'],c['end_m'],c['cell']))
    for road in bounds: bounds[road].sort()
    return link,bounds

def to_cell(bounds,road,x):
    for a,b,i in bounds[road]:
        if a-1e-6 <= x < b: return i
    return bounds[road][-1][2] if x>=bounds[road][-1][0] else None

def scan_native(path,link,bounds):
    acc=defaultdict(float); frames=0; seen=set()
    with path.open('rb') as f:
        for raw in f:
            if not raw[:1].isdigit(): continue
            p=raw.split(b';',6); t=float(p[0])
            if t<CUT-1e-6: continue
            if t>CUT+WIN+1e-6: break
            seen.add(t)
            lk=p[2].decode('ascii')
            if lk not in link: continue
            road,off=link[lk]
            i=to_cell(bounds,road,off+float(p[4]))
            if i is not None: acc[(road,i)]+=1
    frames=len(seen)
    return {k:v/frames for k,v in acc.items()}, frames

if __name__=='__main__':
    spec=importlib.util.spec_from_file_location('h',ROOT/'diagnostics/offramp_dynamic_20260922/study.py')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    data,_=m.corrected_data()
    link,bounds=cellmap(data.geometry)
    nat={}
    for arm,p in FZP.items():
        print(f'scanning native {arm} ...',flush=True)
        nat[arm],fr=scan_native(p,link,bounds); print(f'  frames={fr}')
    model=load_base_model(data.geometry,BASE/'boundary_config.json')
    params=load(BASE/'family_parameters.json')['boundary']
    profile=load(RD/'controller_response_4500_v1/model_v3/port_profile.json')
    policy=load(Q/'rules/prepared_rm/rule_policy.json'); zd=policy['zone_dsds']
    B=(int(CUT-0.1),int(CUT-0.1)+150,int(CUT-0.1)+300)
    plan={t:(dict(load(Q/f'rm/run/decision_{t}.json')['history']['greens']),
             dict(load(Q/f'rm/run/decision_{t}.json')['history']['states'])) for t in B}
    ids={d:120. for z,v in zd.items() for d in v}
    def run(rep):
        def c(t):
            if not rep: return {},ids
            g,s=plan[B[min(2,int((t-CUT)//150))]]
            return {k:v for k,v in g.items() if v<10 or k in s},ids
        w=er.window(data,model,CUT,'history_forecast',profile,c)
        pred=er.simulate(model,w,params)
        acc=defaultdict(float); n=defaultdict(int)
        for x in pred['cells']:
            acc[(x['road'],x['cell'])]+=x['n_veh']; n[(x['road'],x['cell'])]+=1
        return {k:acc[k]/n[k] for k in acc}
    mh,mr=run(False),run(True)
    print(f"\n{'셀':>10} {'구간(m)':>14} | {'native Δ':>10} {'모형 Δ':>10} | {'native none':>12} {'모형 hold':>10}")
    tot_n=tot_m=0.
    for road in ('FW_E','FW_W'):
        for a,b,i in bounds[road]:
            dn=nat['rm'].get((road,i),0)-nat['none'].get((road,i),0)
            dm=mr.get((road,i),0)-mh.get((road,i),0)
            tot_n+=dn; tot_m+=dm
            if road=='FW_E' and (abs(dn)>0.5 or abs(dm)>0.5):
                print(f"{road}{i:>3}    {int(a):>6}-{int(b):<6} | {dn:>10.3f} {dm:>10.3f} | {nat['none'].get((road,i),0):>12.2f} {mh.get((road,i),0):>10.2f}")
    print(f"\n  합계 Δ대수: native {tot_n:+.3f}  모형 {tot_m:+.3f}")
    out=[]
    for road in ('FW_E','FW_W'):
        for a,b,i in bounds[road]:
            c=[x for x in data.geometry['cells'] if x['road']==road and x['cell']==i][0]
            out.append(dict(road=road,cell=i,start_m=a,end_m=b,length_m=b-a,
                lanes=c.get('effective_lanes'),canon_lanes=c.get('canonical_segment_lanes'),
                native_none=nat['none'].get((road,i),0.),native_rm=nat['rm'].get((road,i),0.),
                model_hold=mh.get((road,i),0.),model_replay=mr.get((road,i),0.),
                native_d=nat['rm'].get((road,i),0.)-nat['none'].get((road,i),0.),
                model_d=mr.get((road,i),0.)-mh.get((road,i),0.)))
    Path(OUTJSON).write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
    print('  -> '+OUTJSON)
