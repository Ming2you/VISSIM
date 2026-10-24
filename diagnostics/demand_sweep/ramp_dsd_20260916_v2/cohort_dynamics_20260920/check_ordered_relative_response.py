"""NC falsification gate for the existing ordered restart model's IDM option."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import math
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_restart as r
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import current_gap_response as g

K,e=r.d.HERE,r.d.e
OUT=K/'ordered_relative_response_v1'


def evaluate(states,frames,initial,start,located):
    result={}
    for horizon in (5,10,30):
        rows=[];censored=0
        for vid in initial:
            cell=located[start][vid]['cell']
            if cell<15:continue
            if any(vid not in frames[start+dt] or frames[start+dt][vid]['link']!=24 for dt in range(1,horizon+1)):
                censored+=1;continue
            actual=frames[start+horizon][vid];pred=states[horizon][vid]
            speed_error=pred['v']-actual['v']
            displacement_error=pred['pos']-actual['pos']
            changed=any(frames[start+dt][vid]['lane']!=initial[vid]['lane'] for dt in range(1,horizon+1))
            rows.append(dict(vehicle=vid,cell=cell,speed_error=speed_error,displacement_error=displacement_error,
                actual_speed=actual['v'],predicted_speed=pred['v'],actual_displacement=actual['pos']-initial[vid]['pos'],
                predicted_displacement=pred['pos']-initial[vid]['pos'],own_future_lane_change=changed,
                braking_envelope_exceeded=pred.get('braking_envelope_exceeded',False)))
        result[horizon]=dict(rows=rows,censored=censored)
    return result


def summarize(runs):
    summary={}
    for mode in ('old_gap','relative_idm'):
        completed=[r for r in runs if r['mode']==mode and r['status']=='completed']
        groups={}
        for horizon in (5,10,30):
            rows=[v for run in completed for v in run['scores'][horizon]['rows']]
            groups[horizon]=dict(n=len(rows),censored=sum(run['scores'][horizon]['censored'] for run in completed),
                speed_rmse=math.sqrt(sum(v['speed_error']**2 for v in rows)/len(rows)) if rows else None,
                position_mae=sum(abs(v['displacement_error']) for v in rows)/len(rows) if rows else None,
                own_future_lane_changed=sum(v['own_future_lane_change'] for v in rows),
                braking_envelope_exceeded=sum(v['braking_envelope_exceeded'] for v in rows))
        summary[mode]=dict(completed_lanes=len(completed),failed_lanes=sum(v['mode']==mode and v['status']=='failed' for v in runs),horizons=groups)
    common=[]
    for current in (v for v in runs if v['mode']=='relative_idm' and v['status']=='completed'):
        old=next(v for v in runs if v['start']==current['start'] and v['lane']==current['lane'] and v['mode']=='old_gap')
        if old['status']=='completed':common.extend([old,current])
    return summary,common


def main():
    if (OUT/'result.json').exists():raise FileExistsError('Completed results are immutable')
    gp=r.d.H/'controller_response_s23_v1/none/geometry.json';geometry=e.load(gp)
    network=r.d.H/'source_dsd/baseline.inpx'
    params=r.native_parameters(network,include_deceleration=True)
    spec=importlib.util.spec_from_file_location('frozen_restart_before_relative',OUT/'source_before.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    assert old.native_parameters(network)==r.native_parameters(network)
    native=K/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    saved=r.d.END
    try:r.d.END=2730;frames,receipt=g.read(native,True,2279)
    finally:r.d.END=saved
    from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_spatial_rollout as spatial
    located=spatial.locate(frames,geometry)
    runs=[];bank={};exact=0
    for start in (2280,2400,2550,2700):
        bank[start]={}
        for lane in (1,2,3):
            initial={vid:{key:row[key] for key in ('pos','lane','v','desired','length')} for vid,row in frames[start].items() if row['link']==24 and row['lane']==lane}
            bank[start][lane]=initial
            def call(module,interaction=None):
                try:
                    kwargs={} if interaction is None else dict(interaction=interaction)
                    states,checks=module.rollout(initial,params,30,step=.2,**kwargs)
                    return dict(status='completed',states=states,checks=checks)
                except (ArithmeticError,KeyError,ValueError) as exc:
                    return dict(status='failed',reason=str(exc),exception_type=type(exc).__name__)
            before=call(old);after=call(r)
            assert before==after;exact+=1
            for mode,data in (('old_gap',after),('relative_idm',call(r,dict(law='idm',delta=4.)))):
                run=dict(start=start,lane=lane,mode=mode,initial_vehicles=len(initial),**{k:v for k,v in data.items() if k!='states'})
                if data['status']=='completed':
                    run['scores']=evaluate(data['states'],frames,initial,start,located)
                    e.save(OUT/f'{start}_{lane}_{mode}.json',data['states'])
                runs.append(run)
            print('ORDERED',start,lane,[(v['mode'],v['status'],v.get('reason')) for v in runs[-2:]],flush=True)
    summary,common=summarize(runs)
    common_summary,_=summarize(common) if common else ({},[])
    e.save(OUT/'initials.json',bank);e.save(OUT/'parameters.json',params)
    files=[Path(__file__),Path(r.__file__),Path(g.__file__),gp,network,OUT/'source_before.py',OUT/'initials.json',OUT/'parameters.json']
    e.save(OUT/'result.json',dict(qualified=False,production_adopted=False,new_native_runs=0,future_inputs=False,
        summary=summary,common_support=common_summary,runs=runs,default_replays_exact=exact,
        source_receipt=receipt,source_pins={p.relative_to(r.d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        law=dict(name='IDM',delta=4.,step=.2,a='native mean desired acceleration at zero speed',
            b='native mean desired deceleration at zero speed',T='native CC1',s0='native CC0',desired_speed='current native vehicle DESSPEED'),
        reference='https://traffic-simulation.de/info/info_IDM.html',
        limitations=['A parameter-transfer hypothesis, not calibrated Wiedemann or a complete control plant.',
            'Initial lane cohorts only; no new entries, future lane changes or native target replay.',
            'Completed trajectories may violate native braking envelopes; counted explicitly, not declared physically qualified.',
            'Initial projected overlaps/touches remain unsupported and are not repaired by moving/deleting vehicles.',
            'Own future lane changes and censoring are scoring labels, never model selection inputs.',
            'Scores across differing support are not a paired performance comparison; common support is separate.',
            'NC-only development gate; no450s gain, RM/VSL, unused holdout, or canonical integration claim.']))
    print(json.dumps(dict(summary=summary,common=common_summary)))


if __name__=='__main__':main()
