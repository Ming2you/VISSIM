"""Check conditional-study feature causality, training bounds and receipts."""
from pathlib import Path
import sys,copy,hashlib,math
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import current_gap_history as history
g=history.g;d=g.d


def main():
    out=d.HERE/'current_gap_history_v1';paths=[Path(__file__)];pin_checks=0
    for folder in ('current_gap_response_v1','current_gap_cohort_v2','current_gap_history_v1'):
        p=d.HERE/folder/'result.json';doc=d.e.load(p);paths.append(p)
        assert doc['qualified'] is False and doc['production_changes']==doc['new_native_runs']==0
        for name,h in doc['pins'].items():
            assert hashlib.sha256((d.ROOT/name).read_bytes()).hexdigest()==h;pin_checks+=1
        for r in doc.get('source_receipts',doc.get('sources',{})).values():
            path=d.ROOT/r['path'];assert (path.stat().st_size,path.stat().st_mtime_ns)==(r['size'],r['mtime_ns'])
    geom=d.e.load(d.H/'controller_response_s23_v1/none/geometry.json')
    params=g.restart.native_parameters(d.H/'source_dsd/baseline.inpx')
    # Synthetic frames test data dependencies only, not a physical trajectory.
    frames={t:{1:dict(link=24,lane=1,pos=100.,v=36.,length=4.211),
               2:dict(link=24,lane=1,pos=110.,v=30.,length=4.610)} for t in range(2399,2851)}
    def target(fs):
        rs,ct,_=g.build(fs,geom,params,2400);history.attach(rs,fs)
        return next((r for r in rs if r['time_s']==2400 and r['vehicle']==1),None),ct
    initial,_=target(frames);assert initial is not None
    changed=copy.deepcopy(frames)
    for t in range(2401,2851):changed[t][1]['v']=60.;changed[t][1]['lane']=2
    future,_=target(changed)
    assert initial['feature_bins']==future['feature_bins'] and initial['history_bin']==future['history_bin']
    assert initial['labels']!=future['labels']
    past=copy.deepcopy(frames);past[2399][1]['v']=10.;past_r,_=target(past)
    assert past_r['history_bin']!=initial['history_bin'] and past_r['feature_bins']==initial['feature_bins']
    gap=copy.deepcopy(frames);gap[2400][2]['pos']=140.;gap_r,_=target(gap)
    assert gap_r['feature_bins'][:2]==initial['feature_bins'][:2]
    assert gap_r['feature_bins'][2]!=initial['feature_bins'][2]
    overlap=copy.deepcopy(frames);overlap[2400][2]['pos']=102.;overlap_r,ct=target(overlap)
    assert overlap_r is None and ct['overlapping_lane_projection']==1
    # Alter excluded training times dramatically. Both fitters must stay exact.
    a=copy.deepcopy(initial);a.update(time_s=900,labels={1:1.,5:2.,10:3.},brake=False)
    b=copy.deepcopy(a);b.update(time_s=2090)
    excluded=copy.deepcopy(a);excluded.update(time_s=2091,labels={1:1e9,5:1e9,10:1e9})
    assert g.fit([a,b])==g.fit([a,b,excluded])
    assert history.fit([a,b])==history.fit([a,b,excluded])
    base=d.e.load(d.HERE/'current_gap_response_v1/training_table.json')
    mem=d.e.load(out/'training_table.json')
    for doc in (base,mem):assert doc['cutoff_max_s']==2090 and doc['label_max_s']==2100 and doc['train_n']==211842
    cohort=d.e.load(d.HERE/'current_gap_cohort_v2/result.json')
    assert cohort['initial_global_vehicles']==5189 and cohort['full_training_histograms_exact']
    assert cohort['label_leakage_canary_checks']==9
    for arm,counts in cohort['initial_coverage'].items():
        excluded=sum(v for k,v in counts.items() if k!='candidate_vehicle_seconds')
        # score excludes final9cutoffs, so use source candidate count only to
        # check nonnegative complete feature support; do not equate score n.
        assert counts['candidate_vehicle_seconds']-excluded>60000
    old=d.e.load(d.HERE/'transport_step_work_v1/checkpoint.json');core={}
    for path,h in old['sha256'].items():
        if path.startswith('evaluation') or path.endswith('canonical_harness.py'):
            assert hashlib.sha256((d.ROOT/path).read_bytes()).hexdigest()==h;core[path]=h
    result=dict(status='CONDITIONAL_IDENTIFICATION_CHECKED_NOT_QUALIFIED',source_pin_checks=pin_checks,
        training_rows=211842,initial_global_vehicles=5189,exact_training_histogram_refit=True,
        tests=['Future speed/lane labels leave current gap and history features unchanged',
               'Previous speed affects history only','Current spacing changes gap feature at same speed/density',
               'Negative geometric body gap is explicitly unsupported','Post2090 rows do not enter either fitter',
               'Source receipts stable; core hashes unchanged'],core_hashes_unchanged=core,
        future_features=False,qualified=False,
        remaining=['Recursive state propagation','Conservation and component costs','450s RM/VSL/both gains and ranking','NC guards and fresh holdout'],
        pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    d.e.save(out/'validation.json',result);print(dict(pin_checks=pin_checks,tests=result['tests'],qualified=False),flush=True)


if __name__=='__main__':main()
