"""Native local inventory and lane-change audit, after both runs have ended."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from collections import defaultdict
import math

HERE=Path(__file__).resolve().parent;H=HERE.parent
BOUNDS=[(400.,1305.3887036831929),(1305.3887036831929,1651.8060404357457),
        (1651.8060404357457,1964.2176840051573),(1964.2176840051573,2307.3794608258345),
        (2307.3794608258345,2652.027349)]


def extract(path):
    bins=defaultdict(lambda:[0.,0.,0.,0.,0.,0.]);previous={};endpoints={};per_sec=defaultdict(int)
    with path.open('rb') as f:
        for line in f:
            if not line[:1].isdigit():continue
            p=line.rstrip(b'\r\n;').split(b';');t=int(float(p[0]))
            if t<2400:continue
            if t>2850:break
            if int(p[2])!=2:continue
            vid=int(p[1]);lane=int(p[3]);pos=float(p[4]);v=float(p[6])
            old=previous.get(vid);previous[vid]=(t,lane,pos)
            for i,(a,b) in enumerate(BOUNDS):
                if a<pos<=b:
                    if t in [2400,2850]:
                        for g in [0,lane]:endpoints.setdefault((t,i,g),[]).append(vid)
                    if t>2400:
                        per_sec[t,i]+=1
                        for g in [0,lane]:
                            row=bins[i,g];row[0]+=1;row[1]+=v;row[2]+=v*v
                            row[3]+=int(v<30);row[4]+=int(v<60)
                            row[5]+=int(bool(old and old[0]==t-1 and old[1]!=lane))
    output=[]
    for (i,lane),x in sorted(bins.items()):
        n=x[0]
        output.append({'start_m':BOUNDS[i][0],'end_m':BOUNDS[i][1],'lane':lane,
            'vehicle_seconds':n,'ttt_veh_h':n/3600,'n_mean':n/450,
            'n_initial':len(endpoints.get((2400,i,lane),[])),
            'n_final':len(endpoints.get((2850,i,lane),[])),
            'space_time_speed_mean_kmh':x[1]/n,'space_time_speed_sd_kmh':math.sqrt(max(0,x[2]/n-(x[1]/n)**2)),
            'slow_lt30_veh_sec':x[3],'slow_lt60_veh_sec':x[4],
            'lane_changes_arriving_lane':x[5]})
    return output


def main():
    out=HERE/'local_queue_v1';out.mkdir(exist_ok=False)
    paths={'none':H/'rules_4500_s23_v1/run_none/vissim_eval/baseline_001.fzp',
           'vsl':HERE/'native_v2/run_retry1/vissim_eval/baseline_001.fzp'}
    data={arm:extract(p) for arm,p in paths.items()}
    key=lambda r:(r['start_m'],r['end_m'],r['lane'])
    base={key(r):r for r in data['none']};pairs=[]
    for r in data['vsl']:
        old=base[key(r)]
        assert old['n_initial']==r['n_initial'],'Different initial physical inventory'
        delta={k:r[k]-old[k] for k in r if k not in ['start_m','end_m','lane']}
        pairs.append({'none':old,'vsl':r,'delta':delta})
        if r['lane']==0:print(r['start_m'],r['end_m'],delta,flush=True)
    e.save(out/'comparisons.json',pairs)
    # No entries/exits/merges between these two stations in the pinned geometry.
    stations=e.load(HERE/'station_v1/comparisons.json')
    gates={r['none']['pos_m']:r for r in stations if r['none']['link']==2 and r['none']['lane']==0 and
           r['none']['start_s']==2400 and r['none']['end_s']==2850}
    check=pairs[0]
    balances={}
    for arm in ['none','vsl']:
        r=check[arm];entry=gates[400.][arm]['passages'];exit=gates[1305.3887036831929][arm]['passages']
        residual=r['n_final']-r['n_initial']-entry+exit
        balances[arm]={'initial':r['n_initial'],'final':r['n_final'],'entries':entry,'exits':exit,'residual':residual}
        assert residual==0,('Unexplained disappearance / missed crossing',balances)
    e.save(out/'conservation.json',balances)


if __name__=='__main__':main()
