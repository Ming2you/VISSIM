"""Separate observed10490 origin cohorts from through traffic, using past events.

Cached native labels only; no forecasts, fits, COM or FZP reads. Vehicle-origin
cohorts are defined by the last observed ramp departure at or before each frame.
"""
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
import ctypes
import gzip
import json
from pathlib import Path
import time

from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
START=2670.1
END=3120.1
RAMPS={'10639','10681','10490','10484'}


def csvread(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    assert not (HERE/'completion.json').exists()
    began=time.perf_counter()
    core=h.read(h.R/'restart_supply210/protocol.json')['source_sha256']
    stop=h.read(h.R/'restart_supply210/protocol.json')['STOP']
    assert all(h.sha(h.ROOT/p)==v for p,v in core.items()) and h.sha(stop['path'])==stop['sha256']
    h.save(HERE/'protocol.json',dict(previous_goal_turn='PROGRESS211: exact accepted-flow budget shows restart ablation still restricted by predicted lane21 supply.',
        question='Does observed lane21/22 occupation and its VSL change originate mainly in vehicles from10490, or in through vehicles? Do new merge cohorts visibly change lane differently?',
        cohort='Latest observed FW_E ramp departure at or before the current snapshot is10490. Other means not last observed entering at10490; not a destination label.',
        region=[21,22],cells_zero_based=True,lanes_one_based=True,window=[START,END],sample_sec=5,
        sources='29late hold pair and67four arms cached frames plus native port_events.csv; no new file scan.',
        labels='Current cohort inventory and slow<5; next5s endpoint lane labels split by any-followed versus same-region survivors. First lane departure competing/censored outcomes are descriptive only.',
        restrictions=['No assumption that an endpoint lane change happened in the source cell.',
                      'No conversion of5s snapshots to exact microscopic residence or continuous hazard.',
                      'No causal decomposition of VSL effect into independent cohort contributions.',
                      'No coefficient fitting or new physical candidate before assessing support.'],
        budget=dict(fits=0,forecasts=0,native=0,FZP=0),source_sha256=core,STOP=stop))
    cases={}
    for r in h.read(h.C/'data_catalog.json')['checked_records']:
        if r['case']=='s29_late' and r['arm'] in ('hold','hold_vsl90'):
            cases['29_'+r['arm']]=(h.F/f"vsl_native_exposure/s29_late_{r['arm']}_frames.json.gz",Path(r['truth']))
    for arm in ('hold','hold_vsl90','release','release_vsl90'):
        cases['67_'+arm]=(h.R/f'blocking176/{arm}_frames.json.gz',h.I/f'heldout67_freeway_20260930/observations/{arm}')
    assert len(cases)==6
    pins={};groups=[];observations=[];passages=[];source_checks=[];initial={}
    for case,(frame_path,truth) in cases.items():
        event_path=truth/'port_events.csv';flow_path=truth/'flows_30s.csv'
        for p in (frame_path,event_path,flow_path):pins[str(p)]=h.sha(p)
        data=h.read(frame_path);ix={k:i for i,k in enumerate(data['fields'])}
        vi=ix['speed'] if 'speed' in ix else ix['speed_kmh'];ci=ix['cell'];li=ix['lane']
        frames={round(float(t),1):({str(k):v for k,v in z.items()} if isinstance(z,dict)
                else {str(int(v[ix['vehicle']])):v for v in z}) for t,z in data['frames'].items()}
        assert START in frames and END in frames
        raw_events=csvread(event_path)
        events=[z for z in raw_events if z['kind']=='departure' and z['connector'] in RAMPS]
        history=defaultdict(list)
        for e in events:
            if float(e['time_s'])<=END:
                history[e['vehicle']].append((float(e['time_s']),e['connector']))
        for e in history.values():e.sort()
        initial_key=case.split('_')[0]
        # Rich and small caches have different fields across seeds, but each
        # within-seed policy arm must share the exact initial observations.
        xi=ix['x'] if 'x' in ix else ix['x_m']
        initial_physical={vid:[z[ci],z[li],z[vi],z[xi]] for vid,z in frames[START].items()}
        if initial_key in initial:assert initial[initial_key]==initial_physical
        else:initial[initial_key]=initial_physical
        def origin(vid,t):
            seq=history.get(vid,[]);k=bisect_right(seq,(t,'\uffff'))-1
            return seq[k][1] if k>=0 else 'no_observed_ramp_departure'
        aggregates=defaultdict(lambda:defaultdict(float))
        for step in range(90):
            t=round(START+5*step,1);future=frames[round(t+5,1)];current=frames[t]
            frame_counts=Counter()
            for vid,z in current.items():
                if z[ci] not in (21,22):continue
                frame_counts[z[ci],z[li]]+=1
                cohort='10490' if origin(vid,t)=='10490' else 'other'
                next_z=future.get(vid);followed=next_z is not None
                survivor=followed and next_z[ci] in (21,22)
                row=dict(case=case,time=t,cell=z[ci],lane=z[li],id=vid,cohort=cohort,
                    speed=z[vi],slow=z[vi]<5,next_seen=followed,next_region=survivor,
                    next_cell=next_z[ci] if followed else None,next_lane=next_z[li] if followed else None,
                    next_speed=next_z[vi] if followed else None)
                observations.append(row)
                block=step//30;key=(block,z[ci],z[li],cohort);g=aggregates[key]
                g['samples']+=1;g['speed_sum']+=z[vi];g['slow_samples']+=z[vi]<5
                g['followed']+=followed;g['region_survivors']+=survivor
                g['lane_changed_any_followed']+=bool(followed and next_z[li]!=z[li])
                g['lane_changed_region_survivors']+=bool(survivor and next_z[li]!=z[li])
                g['slow_followed']+=bool(z[vi]<5 and followed)
                g['restart_any_followed']+=bool(z[vi]<5 and followed and next_z[vi]>=5)
            # Cohort split closes exactly to all current vehicles by cell/lane.
            for cell in (21,22):
                for lane in (1,2,3):
                    expected=sum(z[ci]==cell and z[li]==lane for z in current.values())
                    actual=frame_counts[cell,lane]
                    assert expected==actual
        for block in range(3):
            for cell in (21,22):
                for lane in (1,2,3):
                    for cohort in ('10490','other'):
                        g=dict(aggregates[block,cell,lane,cohort])
                        samples=g.get('samples',0)
                        groups.append(dict(case=case,block=block,cell=cell,lane=lane,cohort=cohort,
                            mean_n=samples/30,mean_slow=g.get('slow_samples',0)/30,
                            sampled_residence_s=5*samples,
                            vehicle_sample_mean_speed=g.get('speed_sum',0)/samples if samples else None,**g))
        # First observed departure from lane1 after10490 entry. Window exits and
        # changes first seen beyond22 are competing/censored, never successes.
        merges=[e for e in events if e['connector']=='10490' and START<float(e['time_s'])<=END]
        assert len({(e['vehicle'],e['time_s']) for e in merges})==len(merges)
        for e in merges:
            vid=e['vehicle'];entry=float(e['time_s']);lo=float(e['lower_time_s']);hi=float(e['upper_time_s'])
            assert lo<=entry<=hi and hi-lo<=5.000001
            samples=[];outcome='window_censored';last=entry;event_time=None
            for t in sorted(frames):
                if t<entry:continue
                z=frames[t].get(vid)
                if z is None:
                    outcome='unobserved_after_merge';event_time=t;break
                if z[ci]>22:
                    outcome='region_exit_lane1' if z[li]==1 else 'lane_change_or_exit_order_unknown'
                    event_time=t;break
                if z[ci]<21:
                    outcome='unexpected_upstream_position';event_time=t;break
                samples.append([t,z[ci],z[li],z[vi]])
                if z[li]!=1:
                    outcome='other_lane_first_sample' if len(samples)==1 else 'lane_change_observed_in_region'
                    event_time=t;break
                last=t
            passages.append(dict(case=case,id=vid,entry_lower=lo,entry_upper=hi,
                outcome=outcome,outcome_time=event_time,last_lane1_time=last,samples=samples,
                lane1_sampled_seconds=5*sum(z[2]==1 for z in samples)))
        flow=[z for z in csvread(flow_path) if z['road']=='FW_E' and int(z['cell'])==21 and START<float(z['window_end_s'])<=END+1e-6]
        assert len(flow)==15
        for block in range(3):
            lo=START+150*block;hi=lo+150
            count=sum(lo<float(e['time_s'])<=hi+1e-6 for e in merges)
            truth_count=sum(float(z['ramp_merges']) for z in flow if lo<float(z['window_end_s'])<=hi+1e-6)
            assert count==truth_count
            source_checks.append(dict(case=case,block=block,merge_events=count,native_flow_merges=truth_count))
    with gzip.open(HERE/'observations.json.gz','wt',encoding='utf8') as f:json.dump(observations,f,allow_nan=False)
    h.save(HERE/'cohort_groups.json',groups);h.save(HERE/'passages.json',passages)
    h.save(HERE/'source_checks.json',source_checks);h.save(HERE/'input_pins.json',pins)
    h.save(HERE/'passage_summary.json',[dict(case=c,merges=sum(p['case']==c for p in passages),
        outcomes=dict(Counter(p['outcome'] for p in passages if p['case']==c))) for c in cases])
    assert all(h.sha(h.ROOT/p)==v for p,v in core.items()) and h.sha(stop['path'])==stop['sha256']
    result=dict(status='COMPLETE_OBSERVED_COHORT_PARTITION',vehicle_samples=len(observations),
        groups=len(groups),new_merge_passages=len(passages),native_flow_comparisons=len(source_checks),
        source_count=len(pins),seconds=time.perf_counter()-began,core_preserved=len(core),
        fits=0,forecasts=0,native=0,FZP=0,adopted=False,goal='ACTIVE_NOT_QUALIFIED')
    h.save(HERE/'completion.json',result)
    print(json.dumps(result))
    for r in groups:
        if r['case'].startswith('67_release') and r['cell']==21 and r['lane']==1 and r['block']==1:print(json.dumps(r))


if __name__=='__main__': main()
