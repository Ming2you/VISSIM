"""Audit the first native RM response, without matching newly created IDs.

This is retrospective identification, not a new prediction or gain fit.
The source run's original columns are checked against its extended recording.
"""
from pathlib import Path
from collections import defaultdict
import sys, csv, hashlib, math
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import counterfactual_first_difference as first

d=first.d


def extended(path, lo=2400, hi=2460):
    stamp=(path.stat().st_size,path.stat().st_mtime_ns)
    frames=defaultdict(dict)
    header=None
    with path.open('rb') as stream:
        for line in stream:
            if line.startswith(b'$VEHICLE:'):header=line.decode().strip()
            if not line.strip() or line[:1] not in b'0123456789':continue
            t=float(line.split(b';',1)[0])
            if t>hi:break
            if t<lo:continue
            assert t==int(t)
            a=[v.strip() for v in line.rstrip(b'\r\n').split(b';')]
            row=dict(vehicle=int(a[1]),link=int(a[2]),lane=int(a[3]),pos=float(a[4]),
                     lateral=float(a[5]),speed=float(a[6]),desired=float(a[9]),length=float(a[10]),
                     lane_change=a[16].decode(),interaction=a[17].decode(),target_type=a[18].decode(),
                     target=int(a[19]) if a[19] else None,original9=tuple(a[:9]))
            assert row['vehicle'] not in frames[int(t)]
            frames[int(t)][row['vehicle']]=row
    assert set(frames)==set(range(lo,hi+1))
    assert stamp==(path.stat().st_size,path.stat().st_mtime_ns)
    assert header and 'INTERACTTARGNO' in header
    return frames,dict(path=str(path.relative_to(d.ROOT)),size=stamp[0],mtime_ns=stamp[1],header=header)


def primitive(a):
    return dict(link=int(a[2]),lane=int(a[3]),pos=float(a[4]),lateral=float(a[5]),speed=float(a[6]))


def neighbor(frame,vid,shifts,initial_lengths):
    """Geometric nearest same-lane body. Not asserted to be VISSIM's target."""
    car=primitive(frame[vid])
    if car['link'] not in shifts:return None
    x=shifts[car['link']]+car['pos']
    ahead=[]
    for other,a in frame.items():
        r=primitive(a)
        if other==vid or r['link'] not in shifts or r['lane']!=car['lane']:continue
        y=shifts[r['link']]+r['pos']
        if y>x:ahead.append((y,other,r))
    if not ahead:return None
    y,lead,r=min(ahead)
    length=initial_lengths.get(lead)
    return dict(vehicle=lead,link=r['link'],lane=r['lane'],speed=r['speed'],front_distance_m=y-x,
                gap_m=y-x-length if length is not None else None,
                length_source='identical_initial_vehicle' if length is not None else 'unavailable',
                target_is_geometric_not_native=True)


def main():
    out=d.HERE/'first_merge_response_v2';out.mkdir(exist_ok=False)
    paths={'none':d.H/'rules_4500_s23_v1/run_none/vissim_eval/baseline_001.fzp',
           'rm_ramp':d.H/'response_late_s23_v1/run_rm_ramp/vissim_eval/baseline_001.fzp'}
    frames={};receipts={}
    for arm,path in paths.items():frames[arm],receipts[arm]=first.frames(path)
    ext_path=d.HERE/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    ext,receipts['none_extended']=extended(ext_path)
    exact=0
    for t in ext:
        assert {i:r['original9'] for i,r in ext[t].items()}==frames['none'][t]
        exact+=len(ext[t])
    assert frames['none'][2400]==frames['rm_ramp'][2400]
    initial=set(frames['none'][2400]);lengths={i:r['length'] for i,r in ext[2400].items()}
    geom_path=d.H/'controller_response_s23_v1/none/geometry.json';geometry=d.e.load(geom_path)
    shifts={r['link']:r['offset_m'] for r in geometry['chains']['FW_E']}
    cells={r['cell']:r for r in geometry['cells'] if r['road']=='FW_E'}
    focus=(18665,17532)
    assert set(focus)<=initial
    timeline=[];events={};paired={};lane_stats=[]
    for arm,series in frames.items():
        events[arm]=[]
        for t in range(2401,2461):
            for vid,a in series[t].items():
                old=series[t-1].get(vid)
                if old and old[2]==b'10490' and a[2]!=old[2]:
                    assert a[2]==b'119'
                    events[arm].append(dict(time_s=t,vehicle=vid,speed=float(a[6]),initial_cohort=vid in initial))
            grouped=defaultdict(list)
            for vid,a in series[t].items():
                r=primitive(a)
                if r['link'] not in shifts:continue
                x=shifts[r['link']]+r['pos']
                if cells[13]['start_m']<=x<cells[14]['end_m']:grouped[r['lane']].append(r['speed'])
            for lane,speeds in grouped.items():
                avg=sum(speeds)/len(speeds)
                lane_stats.append(dict(arm=arm,time_s=t,lane=lane,n=len(speeds),speed_mean=avg,
                                       speed_sd=math.sqrt(sum((v-avg)**2 for v in speeds)/len(speeds)),
                                       stopped5=sum(v<5 for v in speeds)))
        for t in range(2408,2441):
            for vid in focus:
                assert vid in series[t]
                row=dict(arm=arm,time_s=t,vehicle=vid,**primitive(series[t][vid]),
                         geometric_leader=neighbor(series[t],vid,shifts,lengths))
                if arm=='none':
                    row['native_recorded_interaction']={k:ext[t][vid][k] for k in ('lane_change','interaction','target_type','target')}
                timeline.append(row)
    # Initial IDs alone are used for individual counterfactual comparisons.
    for vid in focus:
        own={}
        for arm,series in frames.items():
            rows=[(t,primitive(series[t][vid])) for t in range(2400,2461)]
            assert all(vid in series[t] for t in range(2400,2461))
            own[arm]=dict(merge_time=next((r['time_s'] for r in events[arm] if r['vehicle']==vid),None),
                         link24_first_time=next((t for t,r in rows if r['link']==24),None),
                         stopped5_vehicle_sec=sum(r['speed']<5 for t,r in rows if t>2400),
                         final=rows[-1][1])
        paired[vid]=own
    # Compare equal merge-count intervals instead of confusing event timing
    # with the accumulated number of admitted vehicles.
    intervals=[]
    for end in (2420,2430,2440,2460):
        intervals.append(dict(start=2400,end=end,counts={a:sum(r['time_s']<=end for r in rs) for a,rs in events.items()},
                              initial_id_sequence={a:[r['vehicle'] for r in rs if r['time_s']<=end and r['initial_cohort']] for a,rs in events.items()}))
    n=frames['none'];r=frames['rm_ramp']
    assert all(n[t][17532][2:7]==r[t][17532][2:7] for t in range(2400,2418))
    assert float(n[2418][17532][6])==97.57 and float(r[2418][17532][6])==109.92
    assert paired[18665]['none']['merge_time']==2417 and paired[18665]['rm_ramp']['merge_time']==2419
    assert intervals[1]['counts']=={'none':5,'rm_ramp':5}
    saved_first=d.e.load(d.HERE/'counterfactual_first_difference_v1/result.json')
    assert saved_first['first_by_initial_road']['FW_E']['time_s']==2418
    with (out/'lane_response_1s.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(lane_stats[0]));writer.writeheader();writer.writerows(lane_stats)
    pins=[Path(__file__),Path(first.__file__),geom_path,d.HERE/'counterfactual_first_difference_v1/result.json']
    result=dict(status='FIRST_NATIVE_MERGE_RESPONSE_IDENTIFIED_NOT_QUALIFIED',
                exact_original9_rows=exact,initial_equal_rows=len(initial),
                timeline=timeline,merge_events=events,paired_initial_vehicles=paired,intervals=intervals,
                source_receipts=receipts,
                pins={str(p.relative_to(d.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pins},
                interpretation='The first changed mainline vehicle follows a ramp vehicle in NC but precedes it in RM. A2s delayed merge changes order even when30s merge counts coincide.',
                limitations=['Retrospective60s audit, not450s causal gain attribution.',
                    'NC native interaction record describes a simulation step; geometric neighbor is separately calculated, never substituted for missing RM interaction.',
                    'Only initial IDs are paired. Event counts and lane statistics include unpaired later entrants.',
                    'An individual benefit does not establish aggregate benefit, monotonic RM benefit, or a qualified macro closure.',
                    'Earlier actual1s merge-pulse replay already failed full gain prediction; do not repeat it as a solution.'],
                native_runs=0,core_changes=False,future_inputs_to_plant=False,qualified=False)
    d.e.save(out/'result.json',result)
    print(dict(exact_rows=exact,paired=paired,intervals=intervals),flush=True)


if __name__=='__main__':main()
