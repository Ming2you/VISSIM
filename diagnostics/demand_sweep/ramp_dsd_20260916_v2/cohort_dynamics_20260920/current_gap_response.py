"""NC-trained conditional gap/relative-speed response identification.

Not a macro model or recursive450s forecast. All features use records at t or
earlier; future records supply labels only. No future interaction targets used.
"""
from pathlib import Path
from collections import defaultdict,Counter
import sys,math,hashlib,json,bisect
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_wave_audit as d
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_restart as restart

HORIZONS=(1,5,10)
MODES=('speed_density','gap_relative','gap_relative_order')
MIN_SUPPORT=30  # Diagnostic histogram support, not a plant parameter.


def keys(record):
    v,rho,gap,closing,changed=record['feature_bins']
    return ((v,rho),(v,rho,gap,closing),(v,rho,gap,closing,changed))


def read(path,extended,lo):
    saved=d.START
    try:
        d.START=lo+150
        return d.extract(path,extended)
    finally:d.START=saved


def build(frames,geometry,parameters,lo,initial_lengths=None):
    shifts={x['link']:x['offset_m'] for x in geometry['chains']['FW_E']}
    cells={x['cell']:x for x in geometry['cells'] if x['road']=='FW_E'}
    bounds=[cells[c]['end_m'] for c in sorted(cells)]
    lengths=initial_lengths or {}
    preceding={};records=[];counts=Counter();examples=[]
    for t in sorted(frames):
        frame=frames[t];lane=defaultdict(list);densities=Counter();locations={}
        for vid,v in frame.items():
            x=shifts[v['link']]+v['pos'];c=min(20,bisect.bisect_right(bounds,x))
            locations[vid]=(x,c);lane[v['lane']].append((x,vid));densities[c,v['lane']]+=1
        leaders={}
        for queue in lane.values():
            queue.sort()
            for (_,vid),(_,ahead) in zip(queue,queue[1:]):leaders[vid]=ahead
        if t<lo or t>=2850:preceding=leaders;continue
        for vid,v in frame.items():
            c=locations[vid][1]
            # Cell13 starts on10613, absent from the reused reader. Train and
            # score complete observed cells14..20 only.
            if c<14:continue
            counts['candidate_vehicle_seconds']+=1
            lead=leaders.get(vid)
            if lead is None:counts['no_geometric_leader']+=1;continue
            if initial_lengths is not None and (vid not in lengths or lead not in lengths):
                counts['outside_known_initial_cohort']+=1;continue
            front=frame[lead]
            length=front.get('length',lengths.get(lead))
            assert length is not None
            gap=locations[lead][0]-locations[vid][0]-length
            if gap<0:counts['overlapping_lane_projection']+=1;continue
            if vid not in frames[t+1]:counts['next_second_censored']+=1;continue
            desired_gap=parameters['stand_m']+parameters['headway_s']*v['v']/3.6
            ratio=gap/desired_gap
            rho=densities[c,v['lane']]/cells[c]['length_km']
            relative=v['v']-front['v']
            changed=int(preceding.get(vid)!=lead)
            features=(bisect.bisect_right((30,60,90),v['v']),bisect.bisect_right((15,30,50),rho),
                      bisect.bisect_right((.5,1.,2.),ratio),bisect.bisect_right((-5.,5.),relative),changed)
            labels={h:frames[t+h][vid]['v']-v['v'] for h in HORIZONS if t+h<=2850 and vid in frames[t+h]}
            future_leader_changed=None
            if lead in frames[t+1]:
                future_leader_changed=frames[t+1][lead]['lane']!=front['lane']
            rec=dict(time_s=t,vehicle=vid,cell=c,lane=v['lane'],feature_bins=features,
                     labels=labels,brake=labels[1]<-7.2,
                     future_lane_change=v['lane']!=frames[t+1][vid]['lane'] or future_leader_changed is True)
            records.append(rec)
            if vid==17532 and 2418<=t<=2440:
                examples.append(dict(time_s=t,vehicle=vid,gap_m=gap,relative_kmh=relative,
                    current_speed=v['v'],leader=lead,feature_bins=features,labels=labels))
        preceding=leaders
    return records,dict(counts),examples


def fit(records):
    accum=[defaultdict(lambda:defaultdict(list)) for _ in MODES]
    train=[r for r in records if 900<=r['time_s'] and r['time_s']+max(HORIZONS)<=2100]
    assert train and max(r['time_s'] for r in train)==2090
    for r in train:
        for bank,key in zip(accum,keys(r)):
            for h,y in r['labels'].items():bank[key][str(h)].append(y)
            bank[key]['brake'].append(float(r['brake']))
    fitted=[]
    for bank in accum:
        fitted.append({k:{h:dict(n=len(v),mean=sum(v)/len(v)) for h,v in ys.items()} for k,ys in bank.items()})
    global_mean={str(h):sum(r['labels'][h] for r in train if h in r['labels'])/sum(h in r['labels'] for r in train) for h in HORIZONS}
    global_mean['brake']=sum(r['brake'] for r in train)/len(train)
    return fitted,global_mean,len(train)


def predict(record,model,global_mean,mode,target):
    ks=keys(record)
    for level in range(mode,-1,-1):
        entry=model[level].get(ks[level],{}).get(target)
        if entry and entry['n']>=MIN_SUPPORT:return entry['mean'],level
    return global_mean[target],-1


def score(records,model,global_mean,lo,hi):
    use=[r for r in records if lo<=r['time_s'] and r['time_s']+max(HORIZONS)<=hi]
    result={}
    for mode,name in enumerate(MODES):
        errors=defaultdict(list);fallback=Counter();pvalues=[];actual=[];stable=[]
        for r in use:
            for h,y in r['labels'].items():
                p,level=predict(r,model,global_mean,mode,str(h));errors[h].append(p-y)
                fallback[(h,level)]+=1
            p,_=predict(r,model,global_mean,mode,'brake');pvalues.append(p);actual.append(int(r['brake']))
            if not r['future_lane_change']:stable.append((r,p))
        result[name]=dict(n=len(use),errors={str(h):dict(n=len(v),rmse_kmh=math.sqrt(sum(x*x for x in v)/len(v)),bias_kmh=sum(v)/len(v)) for h,v in errors.items()},
            brake_rate=sum(actual)/len(actual),brake_brier=sum((p-y)**2 for p,y in zip(pvalues,actual))/len(actual),
            fallback_counts={str(k):v for k,v in fallback.items()},
            stable_next_lane=dict(n=len(stable),brake_brier=sum((p-r['brake'])**2 for r,p in stable)/len(stable)) if stable else None)
    persistence={str(h):dict(n=sum(h in r['labels'] for r in use),rmse_kmh=math.sqrt(
        sum(r['labels'][h]**2 for r in use if h in r['labels'])/sum(h in r['labels'] for r in use))) for h in HORIZONS}
    return dict(models=result,persistence=persistence)


def paired_prediction(a,b,model,global_mean):
    """Same CURRENT initial IDs at the same cutoff; no new-ID matching."""
    one={(r['time_s'],r['vehicle']):r for r in a if 2400<=r['time_s']<=2840}
    two={(r['time_s'],r['vehicle']):r for r in b if 2400<=r['time_s']<=2840}
    rows=[]
    for lo,hi in ((2400,2550),(2550,2700),(2700,2850)):
        pairs=[(x,two[k]) for k,x in one.items() if k in two and lo<=k[0]<hi]
        by_h={}
        for h in HORIZONS:
            eligible=[(x,y) for x,y in pairs if h in x['labels'] and h in y['labels']]
            if not eligible:continue
            by_h[str(h)]=dict(n=len(eligible),actual_mean_delta_kmh=sum(y['labels'][h]-x['labels'][h] for x,y in eligible)/len(eligible),
                predicted_mean_delta_kmh={name:sum(predict(y,model,global_mean,m,str(h))[0]-predict(x,model,global_mean,m,str(h))[0] for x,y in eligible)/len(eligible) for m,name in enumerate(MODES)})
        rows.append(dict(start_s=lo,end_s=hi,conditional_response=by_h))
    return rows


def main():
    out=d.HERE/'current_gap_response_v1';out.mkdir(exist_ok=False)
    gp=d.H/'controller_response_s23_v1/none/geometry.json';geom=d.e.load(gp)
    network=d.H/'source_dsd/baseline.inpx';params=restart.native_parameters(network)
    paths={a:d.HERE/f'route_state_native_v1/{a}_s23/run_retry1/vissim_eval/baseline_001.fzp' for a in ('none','vsl')}
    frames,receipt=read(paths['none'],True,899)
    # Only cars present at intervention time receive inherited immutable
    # lengths in9-column RM/both files. New IDs are never matched.
    initial_lengths={i:r['length'] for i,r in frames[2400].items()}
    nc,counters,examples=build(frames,geom,params,900)
    nc_initial,initial_counters,_=build(frames,geom,params,2400,initial_lengths)
    model,global_mean,train_n=fit(nc)
    summaries={'none':dict(train=score(nc,model,global_mean,900,2100),validation=score(nc,model,global_mean,2100,2400),
                          control=score(nc,model,global_mean,2400,2850),counters=counters)}
    receipts={'none':receipt};pairs={};initial_scores={'none':score(nc_initial,model,global_mean,2400,2850)}
    counts={'none':initial_counters};prefix=[r for r in nc if r['time_s']+10<=2400];del frames
    print('NC',train_n,summaries['none']['validation']['models'],flush=True)
    for arm in ('vsl','rm_ramp','both'):
        path=paths.get(arm,d.H/'response_late_s23_v1'/f'run_{arm}/vissim_eval/baseline_001.fzp')
        frames,receipts[arm]=read(path,arm=='vsl',899 if arm=='vsl' else 2399)
        if arm=='vsl':
            records,ct,_=build(frames,geom,params,900)
            assert [r for r in records if r['time_s']+10<=2400]==prefix
            summaries[arm]=dict(control=score(records,model,global_mean,2400,2850),counters=ct)
        records,counts[arm],_ =build(frames,geom,params,2400,initial_lengths)
        initial_scores[arm]=score(records,model,global_mean,2400,2850)
        pairs[arm]=paired_prediction(nc_initial,records,model,global_mean)
        del frames
        print('SCORED',arm,len(records),flush=True)
    table={name:[dict(key=list(k),targets=v) for k,v in bank.items()] for name,bank in zip(MODES,model)}
    d.e.save(out/'training_table.json',dict(models=table,global_mean=global_mean,train_n=train_n,min_support=MIN_SUPPORT,
        cutoff_max_s=2090,label_max_s=2100))
    files=[Path(__file__),Path(d.__file__),Path(restart.__file__),gp,network,out/'training_table.json']
    d.e.save(out/'result.json',dict(status='CONDITIONAL_GAP_IDENTIFICATION_NOT_QUALIFIED',
        full_extended_scores=summaries,initial_cohort_scores=initial_scores,initial_coverage=counts,
        paired_initial_conditional_response=pairs,examples=examples,
        train_rows=train_n,identical_precontrol_feature_label_rows=len(prefix),sources=receipts,
        pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        feature_definition=dict(speed_edges_kmh=[30,60,90],lane_density_edges=[15,30,50],
            gap_over_CC0_CC1_spacing_edges=[.5,1.,2.],closing_speed_edges_kmh=[-5,5],recent_leader_change='current versus previous geometric leader'),
        limitations=['Conditional1/5/10s fits reset to actual current states, not a recursive450s plant or gain prediction.',
            'One inspected seed; overlapping vehicle-second rows are correlated and not independent trials.',
            'Cells14..20 only; same-lane geometric leaders omit side-lane interaction and entering vehicles not yet on the selected chain.',
            'Histogram edges and30row backoff are fixed diagnostics, not calibrated physical thresholds.',
            'RM/both use only immutable lengths of vehicles present on the selected chain at2400; excluded new/other initial vehicles are counted.',
            'Longer labels can be censored at the selected-chain exit; each horizon records its sample count.',
            'Future labels and future lane-change flags are scoring fields only, never feature inputs.'],
        future_features=False,new_native_runs=0,production_changes=0,qualified=False))
    print('COMPLETE_NOT_QUALIFIED',flush=True)


if __name__=='__main__':main()
