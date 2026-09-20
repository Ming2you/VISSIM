"""Broaden conditional tests to all initial vehicles; separate gap/closing.

The first local-cohort audit is preserved. No new native run or gain fit.
"""
from pathlib import Path
from collections import defaultdict
import sys,hashlib,math,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import current_gap_response as g
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import first_merge_response as f
d=g.d


def ablations(table):
    result={}
    for name,indices in (('gap_only',(0,1,2)),('relative_only',(0,1,3))):
        groups=defaultdict(lambda:defaultdict(lambda:[0,0.]))
        for entry in table['models']['gap_relative']:
            key=tuple(entry['key'][i] for i in indices)
            for h,row in entry['targets'].items():
                groups[key][h][0]+=row['n'];groups[key][h][1]+=row['n']*row['mean']
        result[name]=(indices,{k:{h:dict(n=x[0],mean=x[1]/x[0]) for h,x in v.items()} for k,v in groups.items()})
    return result


def predict(r,name,h,extra,model,global_mean):
    indices,bank=extra[name];entry=bank.get(tuple(r['feature_bins'][i] for i in indices),{}).get(str(h))
    if entry and entry['n']>=g.MIN_SUPPORT:return entry['mean']
    return g.predict(r,model,global_mean,0,str(h))[0]


def score_extra(records,extra,model,global_mean,lo,hi):
    use=[r for r in records if lo<=r['time_s'] and r['time_s']+10<=hi]
    result={}
    for name in extra:
        errors={str(h):[predict(r,name,h,extra,model,global_mean)-r['labels'][h] for r in use if h in r['labels']] for h in g.HORIZONS}
        result[name]={h:dict(n=len(xs),rmse_kmh=math.sqrt(sum(x*x for x in xs)/len(xs))) for h,xs in errors.items()}
    return result


def main():
    out=d.HERE/'current_gap_cohort_v2';out.mkdir(exist_ok=False)
    table_path=d.HERE/'current_gap_response_v1/training_table.json';table=d.e.load(table_path)
    model=[{tuple(r['key']):r['targets'] for r in table['models'][name]} for name in g.MODES]
    global_mean=table['global_mean'];extra=ablations(table)
    assert table['cutoff_max_s']==2090 and table['label_max_s']==2100
    geometry_path=d.H/'controller_response_s23_v1/none/geometry.json';geom=d.e.load(geometry_path)
    network=d.H/'source_dsd/baseline.inpx';params=g.restart.native_parameters(network)
    native_nc=d.HERE/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    full_initial,initial_receipt=f.extended(native_nc,2400,2400)
    lengths={i:r['length'] for i,r in full_initial[2400].items()}
    assert len(lengths)==5189
    frames,receipt=g.read(native_nc,True,899)
    full_nc,_,_=g.build(frames,geom,params,900)
    # Re-fit the same frozen NC900..2100 histogram, independently of all
    # validation/control records. Check the whole table, not just scores.
    fit,means,n=g.fit(full_nc)
    assert fit==model and means==global_mean and n==table['train_n']
    before_score=score_extra(full_nc,extra,model,global_mean,2100,2400)
    nc,coverage,_=g.build(frames,geom,params,2400,lengths)
    assert len(nc)>13234
    records={'none':nc};coverages={'none':coverage};receipts={'none':receipt}
    scores={'none':g.score(nc,model,global_mean,2400,2850)}
    ablation_scores={'none':score_extra(nc,extra,model,global_mean,2400,2850)}
    examples={};del frames
    for arm in ('vsl','rm_ramp','both'):
        path=(d.HERE/'route_state_native_v1/vsl_s23/run_retry1/vissim_eval/baseline_001.fzp' if arm=='vsl'
              else d.H/'response_late_s23_v1'/f'run_{arm}/vissim_eval/baseline_001.fzp')
        frames,receipts[arm]=g.read(path,arm=='vsl',2399)
        for vid,r in frames[2400].items():assert r['original9']==list(full_initial[2400][vid]['original9'])
        rs,coverages[arm],examples[arm]=g.build(frames,geom,params,2400,lengths)
        records[arm]=rs;scores[arm]=g.score(rs,model,global_mean,2400,2850)
        ablation_scores[arm]=score_extra(rs,extra,model,global_mean,2400,2850)
        del frames
        print('INITIAL5189',arm,len(rs),flush=True)
    # Canary: target labels and future scoring flags cannot affect prediction.
    original=records['none'][100];changed=copy.deepcopy(original)
    changed['labels']={h:999999. for h in g.HORIZONS};changed['brake']=not original['brake']
    changed['future_lane_change']=not original['future_lane_change']
    for m in range(3):
        for h in g.HORIZONS:
            assert g.predict(original,model,global_mean,m,str(h))==g.predict(changed,model,global_mean,m,str(h))
    pairs={a:g.paired_prediction(nc,records[a],model,global_mean) for a in ('vsl','rm_ramp','both')}
    # Observed-current-label comparisons by150s are diagnostic, not a
    # cumulative450s gain. Preserve the full tables for signs/small effects.
    paths=[Path(__file__),Path(g.__file__),Path(f.__file__),table_path,geometry_path,network]
    result=dict(status='BROADER_INITIAL_COHORT_CONDITIONAL_TEST_NOT_QUALIFIED',
        initial_global_vehicles=len(lengths),refit_training_rows=n,full_training_histograms_exact=True,
        label_leakage_canary_checks=9,precontrol_validation_ablations=before_score,
        initial_scores=scores,initial_ablations=ablation_scores,initial_coverage=coverages,
        paired_initial_conditional_response=pairs,examples=examples,
        source_receipts=receipts,global_initial_receipt=initial_receipt,
        pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        limitations=['All5189initial vehicles are eligible, but later newly generated IDs are still excluded.',
            'Only cells14..20 and supported geometric current leaders; these are conditional predictions from actual current states.',
            'Ablation means are marginalized from the same NC training histogram; no controlled result selects them.',
            'No450s recursive gain, component cost, fresh-seed or production qualification claim.'],
        qualified=False,new_native_runs=0,production_changes=0)
    d.e.save(out/'result.json',result)
    print('COMPLETE_NOT_QUALIFIED',before_score,flush=True)


if __name__=='__main__':main()
