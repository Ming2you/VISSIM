"""Conditional current-acceleration memory test; no future feature input."""
from pathlib import Path
from collections import defaultdict,Counter
import sys,bisect,math,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import current_gap_cohort_check as c
g=c.g;d=g.d
NAMES=('history','gap_relative_history')


def attach(records,frames):
    for r in records:
        t,i=r['time_s'],r['vehicle'];old=frames[t-1].get(i)
        # A missing previous selected-chain row stays unknown; never infer
        # its acceleration from the next actual row.
        r['history_bin']=-1 if old is None else bisect.bisect_right((-7.2,-1.,1.,7.2),frames[t][i]['v']-old['v'])


def key(r,name):
    base=r['feature_bins'][:2 if name=='history' else 4]
    return tuple(base)+(r['history_bin'],)


def fit(records):
    banks={name:defaultdict(lambda:defaultdict(lambda:[0,0.])) for name in NAMES}
    count=0
    for r in records:
        if not 900<=r['time_s']<=2090:continue
        count+=1
        for name in NAMES:
            row=banks[name][key(r,name)]
            for h,y in r['labels'].items():row[h][0]+=1;row[h][1]+=y
    return {name:{k:{h:(n,total/n) for h,(n,total) in row.items()} for k,row in bank.items()} for name,bank in banks.items()},count


def predict(r,name,h,banks,base,means):
    entry=banks[name].get(key(r,name),{}).get(h)
    if entry and entry[0]>=g.MIN_SUPPORT:return entry[1]
    return g.predict(r,base,means,0 if name=='history' else 1,str(h))[0]


def score(records,banks,base,means,lo,hi):
    rs=[r for r in records if lo<=r['time_s'] and r['time_s']+10<=hi]
    return {name:{str(h):dict(n=sum(h in r['labels'] for r in rs),rmse_kmh=math.sqrt(
        sum((predict(r,name,h,banks,base,means)-r['labels'][h])**2 for r in rs if h in r['labels'])/sum(h in r['labels'] for r in rs)))
        for h in g.HORIZONS} for name in NAMES}


def pair(a,b,banks,base,means):
    left={(r['time_s'],r['vehicle']):r for r in a if 2400<=r['time_s']<=2840}
    right={(r['time_s'],r['vehicle']):r for r in b if 2400<=r['time_s']<=2840}
    rows=[]
    for lo in (2400,2550,2700):
        rs=[(r,right[k]) for k,r in left.items() if lo<=k[0]<lo+150 and k in right]
        fields={}
        for h in g.HORIZONS:
            both=[(x,y) for x,y in rs if h in x['labels'] and h in y['labels']]
            if not both:continue
            fields[str(h)]=dict(n=len(both),actual=sum(y['labels'][h]-x['labels'][h] for x,y in both)/len(both),
                predicted={name:sum(predict(y,name,h,banks,base,means)-predict(x,name,h,banks,base,means) for x,y in both)/len(both) for name in NAMES})
        rows.append(dict(start_s=lo,conditional_response=fields))
    return rows


def main():
    out=d.HERE/'current_gap_history_v1';out.mkdir(exist_ok=False)
    gp=d.H/'controller_response_s23_v1/none/geometry.json';geometry=d.e.load(gp)
    network=d.H/'source_dsd/baseline.inpx';params=g.restart.native_parameters(network)
    table_path=d.HERE/'current_gap_response_v1/training_table.json';table=d.e.load(table_path)
    base=[{tuple(r['key']):r['targets'] for r in table['models'][name]} for name in g.MODES];means=table['global_mean']
    native=d.HERE/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    initial,initial_receipt=c.f.extended(native,2400,2400);lengths={i:r['length'] for i,r in initial[2400].items()}
    frames,receipt=g.read(native,True,899);full,_,_=g.build(frames,geometry,params,900);attach(full,frames)
    banks,n=fit(full);assert n==table['train_n']
    validation=score(full,banks,base,means,2100,2400)
    full_scores={'none':score(full,banks,base,means,2400,2850)}
    nc,coverage,_=g.build(frames,geometry,params,2400,lengths);attach(nc,frames)
    initial_scores={'none':score(nc,banks,base,means,2400,2850)};pairs={};receipts={'none':receipt}
    # No future target or scoring field contributes to any history feature.
    before={tuple(r['feature_bins'])+(r['history_bin'],):None for r in full if r['time_s']==2090}
    assert before
    del frames,full
    print('NC_VALIDATION',validation,flush=True)
    for arm in ('vsl','rm_ramp','both'):
        path=(d.HERE/'route_state_native_v1/vsl_s23/run_retry1/vissim_eval/baseline_001.fzp' if arm=='vsl'
              else d.H/'response_late_s23_v1'/f'run_{arm}/vissim_eval/baseline_001.fzp')
        frames,receipts[arm]=g.read(path,arm=='vsl',2399)
        rs,_,_=g.build(frames,geometry,params,2400,lengths);attach(rs,frames)
        initial_scores[arm]=score(rs,banks,base,means,2400,2850);pairs[arm]=pair(nc,rs,banks,base,means)
        if arm=='vsl':
            all_rs,_,_=g.build(frames,geometry,params,2400);attach(all_rs,frames)
            full_scores[arm]=score(all_rs,banks,base,means,2400,2850)
        del frames
        print('SCORED',arm,flush=True)
    fit_rows={name:[dict(key=list(k),targets={str(h):dict(n=v[0],mean=v[1]) for h,v in ys.items()}) for k,ys in bank.items()] for name,bank in banks.items()}
    d.e.save(out/'training_table.json',dict(models=fit_rows,train_n=n,cutoff_max_s=2090,label_max_s=2100))
    paths=[Path(__file__),Path(g.__file__),Path(c.__file__),gp,network,table_path,out/'training_table.json']
    d.e.save(out/'result.json',dict(status='CONDITIONAL_ACCELERATION_MEMORY_TEST_NOT_QUALIFIED',
        validation=validation,full_extended_control_scores=full_scores,initial_scores=initial_scores,paired_initial_conditional_response=pairs,
        train_rows=n,history_definition='Bin of current speed minus previous-second speed: -7.2,-1,1,7.2km/h; unknown if missing previous row.',
        source_receipts=receipts,initial_receipt=initial_receipt,
        pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        limitations=['Native current acceleration is known at each conditional cutoff. Its future evolution is not yet predicted.',
            'Not a recursive450s model; no TTT, conservation, cost or controller-gain claim.',
            'Single inspected seed, correlated rows, full initial-cohort exclusions inherited from current_gap_cohort_v2.',
            'The new bins are diagnostic features, not runtime parameters or calibrated physical thresholds.'],
        future_features=False,production_changes=0,new_native_runs=0,qualified=False))
    print('COMPLETE_NOT_QUALIFIED',flush=True)


if __name__=='__main__':main()
