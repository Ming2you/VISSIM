"""Current-frame route/access observations; no forecast or flow restriction.

Unknown intent stays unknown. A mismatched lane is not itself a closed lane.
Future route, deletion and traffic records are never accepted by observe().
"""
from pathlib import Path
from collections import Counter
import sys,hashlib,argparse
import xml.etree.ElementTree as ET
import re

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e

HERE=Path(__file__).resolve().parent


from evaluation.controllers.physical_urban_transport import geometry, observe


def cohort_truth(current,frames):
    """Validation labels only; labels never return to observe/current state."""
    initial=[r for r in current['vehicles'] if r['link']==10643]
    index={t:{v[0]:v for v in f['vehicles']} for t,f in frames.items() if 2400<=t<=2850}
    rows=[];summary={}
    for r in initial:
        vid=r['vehicle'];times=[t for t in range(2400,2850) if vid in index[t] and index[t][vid][1]==10643]
        exits=[t for t in range(2401,2851) if vid in index[t-1] and index[t-1][vid][1]==10643 and (vid not in index[t] or index[t][vid][1]!=10643)]
        assert len(exits)<=1
        if exits:assert vid in index[exits[0]] and index[exits[0]][vid][1] in (126,10641,10700,71)
        group=str(r['connector']) if r['connector'] else 'unknown'
        record=dict(vehicle=vid,initial_lane=r['lane'],observed_current_connector=r['connector'],
            off_residence_sec=len(times),normal_off_exit_s=exits[0] if exits else None,
            reached_71_s=next((t for t in range(2400,2851) if vid in index[t] and index[t][vid][1]==71),None))
        rows.append(record)
        s=summary.setdefault(group,dict(initial_n=0,normal_off_exits=0,off_vehicle_seconds=0))
        s['initial_n']+=1;s['normal_off_exits']+=bool(exits);s['off_vehicle_seconds']+=len(times)
    assert sum(s['initial_n'] for s in summary.values())==sum(r['n'] for r in current['off_lanes'].values())
    return dict(rows=rows,summary=summary,
        scope='Initial10643 cohort only; measured2400-2850 residence and normal connector exits are future truth labels, not forecast inputs or TTD.')


def current_access(state):
    """Optimistic current-body insertion geometry, NOT a capacity/flow gate.

    A negative gap at the current position need not preclude insertion farther
    ahead. Safety distances, moving neighbors and lateral overlap are not
    inferred. Starting a lane change is distinct from completing insertion.
    Missing neighbors are unknown, never infinite clearance.
    """
    local=[v for v in state['vehicles'] if v['link']==71]
    rows=[]
    for v in local:
        required=v['required_lanes']
        if not required or v['lane'] in required:continue
        target=v['lane']+(1 if v['lane']<min(required) else -1)
        p=v['position_m'];size=v['length_m']
        other=[w for w in local if w['lane']==target]
        front=min((w for w in other if w['position_m']>=p),key=lambda w:w['position_m'],default=None)
        back=max((w for w in other if w['position_m']<p),key=lambda w:w['position_m'],default=None)
        leader=min((w for w in local if w['lane']==v['lane'] and w['position_m']>p),
                   key=lambda w:w['position_m'],default=None)
        row=dict(time_s=state['time_s'],vehicle=v['vehicle'],lane=v['lane'],target_lane=target,
                 connector=v['connector'],position_m=p,length_m=size,speed_kmh=v['speed_kmh'],
                 source_head=leader is None,ongoing=v['lane_change'] in ('Left','Right'),
                 current_destination=v['current_lane_change_destination'],
                 front_vehicle=front['vehicle'] if front else None,back_vehicle=back['vehicle'] if back else None,
                 source_leader=leader['vehicle'] if leader else None)
        if front is None or back is None:
            row['geometry']='unobserved_neighbor'
        else:
            lower=back['position_m']+size
            upper=front['position_m']-front['length_m']
            source_upper=leader['position_m']-leader['length_m'] if leader else None
            row.update(front_gap_m=upper-p,back_gap_m=p-lower,
                       pocket_extra_length_m=upper-lower,required_forward_m=max(0.,lower-p),
                       source_forward_room_m=source_upper-p if source_upper is not None else None,
                       front_speed_kmh=front['speed_kmh'],back_speed_kmh=back['speed_kmh'],
                       stationary_neighborhood=max(v['speed_kmh'],front['speed_kmh'],back['speed_kmh'])<5.)
            if upper<max(p,lower)-1e-8:row['geometry']='no_current_forward_pocket'
            elif source_upper is not None and source_upper<max(p,lower)-1e-8:
                row['geometry']='needs_source_progression'
            elif lower>p+1e-8:row['geometry']='pocket_ahead'
            else:row['geometry']='pocket_at_current_position'
        rows.append(row)
    return rows


def access_audit():
    """Validate current geometry against future labels without feeding back."""
    out=HERE/'urban_access_transition_v1';out.mkdir(exist_ok=False)
    summaries={};pins={};initial_states={}
    for case in ('none_s23','vsl_s23'):
        bank=HERE/'route_state_native_v1'/case
        path=bank/'analysis/frames.json';data=e.load(path)
        validation=e.load(bank/'analysis/result.json');assert validation['passed']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==validation['source_pins'][str(path.relative_to(e.ROOT))]
        network=bank/'source/baseline.inpx';routes,exits=geometry(network)
        frames={f['time_s']:f for f in data['frames']}
        states={t:observe(frames[t],routes,exits) for t in range(2400,2851)}
        index={t:{v['vehicle']:v for v in s['vehicles']} for t,s in states.items()}
        initial_states[case]=current_access(states[2400])
        rows=[];groups={};packing=[]
        for t in range(2400,2850):
            for current in current_access(states[t]):
                # Truth is attached only AFTER the current-state observation.
                later=index[t+1].get(current['vehicle'])
                completed=bool(later and later['link']==71 and later['lane']==current['target_lane'])
                started=bool(not current['ongoing'] and later and later['lane_change'] in ('Left','Right'))
                truth=dict(next_second_target_lane=completed,next_second_started_change=started,
                           next_second_in_local_record=later is not None)
                row=dict(current=current,truth=truth);rows.append(row)
                key=(current['geometry'],current['ongoing'],current['source_head'])
                g=groups.setdefault(key,dict(vehicle_seconds=0,vehicles=set(),target_lane_next_s=0,starts_next_s=0))
                g['vehicle_seconds']+=1;g['vehicles'].add(current['vehicle'])
                g['target_lane_next_s']+=completed;g['starts_next_s']+=started
            # Test the old nominal6m assumption; no rows are excluded or resized.
            for lane in range(1,6):
                vs=[v for v in states[t]['vehicles'] if v['link']==71 and v['lane']==lane]
                if len(vs)>max(x['position_m'] for x in exits.values())/6.:
                    packing.append(dict(time_s=t,lane=lane,n=len(vs),body_length_m=sum(v['length_m'] for v in vs),
                        active_changes=sum(v['lane_change'] in ('Left','Right') for v in vs)))
        group_rows=[]
        for (geometry_name,ongoing,head),g in sorted(groups.items()):
            group_rows.append(dict(geometry=geometry_name,ongoing=ongoing,source_head=head,
                                   **{k:len(v) if k=='vehicles' else v for k,v in g.items()}))
        stationary_heads=[r for r in rows if r['current']['source_head'] and not r['current']['ongoing']
                          and r['current']['geometry']=='no_current_forward_pocket'
                          and r['current'].get('stationary_neighborhood')]
        summaries[case]=dict(groups=group_rows,nominal6m_exceeded_snapshots=len(packing),
            stationary_head_no_pocket_vehicle_seconds=len(stationary_heads),
            stationary_head_unique_vehicles=len({r['current']['vehicle'] for r in stationary_heads}),
            stationary_head_next_second_changes=sum(r['truth']['next_second_target_lane'] for r in stationary_heads),
            stationary_head_next_second_starts=sum(r['truth']['next_second_started_change'] for r in stationary_heads))
        e.save(out/f'{case}.json',dict(rows=rows,packing=packing,summary=summaries[case]))
        for p in (path,network,bank/'analysis/result.json',out/f'{case}.json'):
            pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        print(case,summaries[case],flush=True)
    assert initial_states['none_s23']==initial_states['vsl_s23']
    pins[str(Path(__file__).relative_to(e.ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    e.save(out/'result.json',dict(status='GEOMETRY_OBSERVATION_ONLY_NOT_A_FLOW_PREDICTOR',
        summaries=summaries,source_pins=pins,paired_initial_observation_equal=True,
        excluded_rows=0,production_adopted=False,
        caveats=['Body-only insertion is optimistic; no safety gap or width has been invented.',
                 'Source progression can occur during a lane change, so current source clearance is not a hard prohibition.',
                 'A missing next local record is not a normal exit, deletion or TTD classification.',
                 'Future observations are validation labels only; no450s gain qualification.']))


def head_outcomes():
    """Ground truth only: verify actual exits versus native abnormal removal."""
    out=HERE/'urban_access_head_outcomes_v2';out.mkdir(exist_ok=False)
    summaries={};pins={}
    pattern=re.compile(r'Simulation second ([0-9.]+): After ([0-9.]+) seconds of waiting for lane change the vehicle (\d+) .*? was removed from link (\d+) at position (\d+(?:\.\d+)?)')
    for case in ('none_s23','vsl_s23'):
        audit=HERE/'urban_access_transition_v1'/f'{case}.json'
        rows=e.load(audit)['rows'];selected={}
        for row in rows:
            c=row['current']
            if c['source_head'] and not c['ongoing'] and c['geometry']=='no_current_forward_pocket' and c.get('stationary_neighborhood'):
                selected.setdefault(c['vehicle'],[]).append(c)
        bank=HERE/'route_state_native_v1'/case
        frames_path=bank/'analysis/frames.json';meta=e.load(frames_path)
        source=e.ROOT/meta['source_fzp'];before=source.stat();sha=hashlib.sha256()
        proof=e.load(bank/'analysis/result.json');assert proof['passed']
        trails={vid:[] for vid in selected};header=None;count=0
        with source.open('rb') as stream:
            for line in stream:
                sha.update(line)
                if line.startswith(b'$VEHICLE:'):header=line.split(b':',1)[1].strip().rstrip(b';').decode('ascii').split(';')
                if not line[:1].isdigit():continue
                count+=1;prefix=line.split(b';',2);vid=int(prefix[1])
                if vid not in selected:continue
                fields=line.rstrip(b'\r\n').split(b';')
                if len(fields)==21 and fields[-1]==b'':fields.pop()
                assert len(fields)==20
                trails[vid].append([int(float(fields[0])),int(fields[2]),int(fields[3]),float(fields[4]),float(fields[5]),
                    float(fields[6]),fields[16].decode('ascii'),int(fields[15]) if fields[15] else None])
        assert sha.hexdigest()==proof['new_fzp_sha256']
        assert count==proof['all_original_ten_columns_exact_rows']
        after=source.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        err=source.parent.parent/'baseline_001.err'
        warnings=[dict(time_s=float(t),wait_s=float(w),vehicle=int(v),link=int(l),position_m=float(p))
                  for t,w,v,l,p in pattern.findall(err.read_text(encoding='utf-8-sig',errors='replace'))]
        result=[]
        for vid,events in selected.items():
            first=events[0];t0=first['time_s'];trace=trails[vid]
            normal=[dict(time_s=b[0],connector=b[1]) for a,b in zip(trace,trace[1:])
                    if a[1]==71 and b[1] in (10634,10635,10642) and t0<b[0]<=2850]
            removal=[w for w in warnings if w['vehicle']==vid and t0<=w['time_s']<=2850]
            assert len(normal)<=1 and len(removal)<=1 and not (normal and removal)
            end=next((r for r in trace if r[0]==2850),None)
            kind='normal_connector_exit' if normal else 'abnormal_lane_change_removal' if removal else 'present_at2850' if end else 'unresolved'
            result.append(dict(vehicle=vid,first_blocked_s=t0,blocked_vehicle_seconds=len(events),
                initial_source_lane=first['lane'],initial_target_lane=first['target_lane'],
                came_via10643=any(r[1]==10643 and r[0]<=t0 for r in trace),
                outcome=kind,normal_exit=normal,abnormal_removal=removal,record_at2850=end,
                first_change_start=next((r[0] for r in trace if t0<r[0]<=2850 and r[6] in ('Left','Right')),None)))
        summaries[case]=dict(outcomes=dict(Counter(r['outcome'] for r in result)),
            observed_heads=len(result),came_via10643=sum(r['came_via10643'] for r in result),
            all_fzp_data_rows=count,raw_hash_matches_prior=True)
        e.save(out/f'{case}.json',dict(summary=summaries[case],heads=result,
            trace_columns=['time_s','link','lane','front_position_m','lateral_position_lane_fraction','speed_kmh','lane_change','destination_lane'],
            traces=trails,source_fzp=str(source.relative_to(e.ROOT)),source_err=str(err.relative_to(e.ROOT))))
        for p in (audit,frames_path,bank/'analysis/result.json',err,out/f'{case}.json'):
            pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        pins[str(source.relative_to(e.ROOT))]=sha.hexdigest()
        print(case,summaries[case],flush=True)
    pins[str(Path(__file__).relative_to(e.ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    e.save(out/'result.json',dict(status='ABNORMAL_CLEARANCE_SEPARATED_NOT_GAIN_QUALIFIED',summaries=summaries,source_pins=pins,
        native_runs_started=0,production_adopted=False,
        caveat='Head cohort is selected for stationary body-pocket blockage; not all71 demand, removals or off-ramp departures. No outcomes enter the causal observation.'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cohorts',action='store_true')
    ap.add_argument('--access-audit',action='store_true');ap.add_argument('--head-outcomes',action='store_true');args=ap.parse_args()
    if args.head_outcomes:return head_outcomes()
    if args.access_audit:return access_audit()
    contract_checks=check_contract()
    out=HERE/('route_access_observations_v2' if args.cohorts else 'route_access_observations_v1');out.mkdir(exist_ok=False)
    pins={};summaries={}
    for case in ('none_s23','vsl_s23'):
        bank=HERE/'route_state_native_v1'/case
        validation=e.load(bank/'analysis/result.json');assert validation['passed']
        for path,pin in validation['source_pins'].items():assert hashlib.sha256((e.ROOT/path).read_bytes()).hexdigest()==pin
        network=bank/'source/baseline.inpx';routes,exits=geometry(network)
        path=bank/'analysis/frames.json';data=e.load(path)
        frames={f['time_s']:f for f in data['frames']}
        cutoffs=(900,1650,2400,2474,2624,2644,2774)
        states={str(t):observe(frames[t],routes,exits) for t in cutoffs}
        for t in cutoffs:
            past={s:f for s,f in frames.items() if s<=t}
            assert states[str(t)]==observe(past[t],routes,exits)
        e.save(out/f'{case}.json',dict(states=states,exits=exits,
            observation_only=True,future_truncation_checks=len(cutoffs)))
        unknown=sum(r['connector'] is None for s in states.values() for r in s['vehicles'])
        conflicts=sum(r['route_next_link_conflict'] for s in states.values() for r in s['vehicles'])
        summaries[case]=dict(sampled_cutoffs=list(cutoffs),unknown_intents=unknown,route_conflicts=conflicts,
            current2400_off=states['2400']['off_lanes'],head2644=states['2644']['urban_lanes']['3']['head'])
        if args.cohorts:
            truth=cohort_truth(states['2400'],frames)
            e.save(out/f'{case}_initial_cohort_truth.json',truth)
            summaries[case]['future_validation_initial_cohort']=truth['summary']
            print(case,'Initial cohort truth',truth['summary'],flush=True)
            p=out/f'{case}_initial_cohort_truth.json';pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (path,network,bank/'analysis/result.json',out/f'{case}.json'):
            pins[str(p.relative_to(e.ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        print(case,summaries[case],flush=True)
    a=e.load(HERE/'route_state_native_v1/none_s23/analysis/result.json')
    b=e.load(HERE/'route_state_native_v1/vsl_s23/analysis/result.json')
    assert a['prefix_rows']==b['prefix_rows'] and a['full_twenty_column_prefix_through2400_sha256']==b['full_twenty_column_prefix_through2400_sha256']
    pins[str(Path(__file__).relative_to(e.ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    e.save(out/'result.json',dict(status='CURRENT_ROUTE_OBSERVATION_VALIDATED_NOT_A_PREDICTOR',summaries=summaries,
        full20column_paired_prefix_sha256=a['full_twenty_column_prefix_through2400_sha256'],paired_prefix_rows=a['prefix_rows'],
        source_pins=pins,future_truncation_checks=14,contract_checks=contract_checks,
        caveats=['Mismatched required lane or short gap is a state, not a valid zero-capacity rule.',
            'No adjacent vehicle observed on71 means unobserved beyond the link, not an infinite usable gap.',
            'Future sampled cutoffs are independent current observations; do not feed them to the2400s rollout.',
            'On10643 the route may still be unassigned before decision1126; keep unknown mass explicitly.',
            'No400/450s lane-change or route-access transition law is qualified here.'],qualified=False))


def check_contract():
    routes={(1126,1):[10643,126,10641,71,10635,47]}
    exits={10635:dict(lanes=[4,5],position_m=81),10634:dict(lanes=[1,2,3],position_m=81)}
    missing=[1,10643,2,10.,0.,4.,None,None,None,126,None,'None','Free',None,None]
    state=observe(dict(time_s=2400,vehicles=[missing]),routes,exits)
    assert state['off_lanes']['2']['planned_71_exit_counts']=={'unknown':1}
    direct=[2,71,3,73.,0.,5.,None,None,None,10635,None,'None','Free',None,None]
    neighbor=[3,71,4,75.,0.,4.,None,None,None,10635,None,'None','Free',None,None]
    state=observe(dict(time_s=2400,vehicles=[direct,neighbor]),routes,exits)
    head=state['urban_lanes']['3']['head']
    assert head['required_lanes']==[4,5] and head['currently_in_required_lane'] is False
    assert head['adjacent_gaps']['4']['front_net_gap_m']==-2
    conflict=list(direct);conflict[6:10]=[1126,1,'Static',10634]
    state=observe(dict(time_s=2400,vehicles=[conflict]),routes,exits)
    assert state['vehicles'][0]['route_next_link_conflict'] and state['vehicles'][0]['connector'] is None
    return 3


if __name__=='__main__':main()
