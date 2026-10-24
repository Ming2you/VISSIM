"""Compare the short read-only witnesses with existing native snapshots."""
import ast
import bisect
import gzip
import hashlib
import json
import statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}
def read(p):
    b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def save(name,v):(HERE/name).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')

def main():
    assert not (HERE/'assessment.json').exists()
    summary=read(HERE/'summary.json');stats=read(HERE/'coupling_stats.json')
    assert summary['formula_error']==summary['speed_error']==0.
    assert stats['commits']==300 and stats['ramp_supply_queries']==1200
    for result in summary['results'].values():assert all(result['parity'].values())
    g=read(I/'selected/port_gain/geometry.json')
    chain={int(x['link']):x for x in g['chains']['FW_E']}
    cells=sorted((x for x in g['cells'] if x['road']=='FW_E'),key=lambda x:x['cell'])
    ends=[c['end_m'] for c in cells]
    analysis={};native_rows=[];binding_checks=0
    for arm in ('release','release_vsl90'):
        trace=read(HERE/(arm+'_actual.json.gz'))
        groups={}
        for row in trace['terms']:
            groups.setdefault((row['cell'],row['lane'],row['part']),[]).append(row)
            if row['cell']==19:continue
            final=max(5.,min(row['speed_after_equation']-row['merge_speed_loss'],
                      row['shared_flux_speed_cap'] if row['shared_flux_speed_cap'] is not None else float('inf')))
            assert abs(final-row['speed_final'])<1e-8
            binding_checks+=1
        grouped=[]
        for (cell,lane,part),rows in sorted(groups.items()):
            assert len(rows)==150
            keys=('initial_n','target','relaxation','convection','anticipation','lane_drop',
                  'speed_after_equation','merge_speed_loss','extra_speed_loss_by_flux_cap','speed_final')
            grouped.append(dict(cell=cell,lane=lane,part=part,
                means={k:statistics.fmean(r[k] for r in rows) for k in keys if k in rows[0]},
                flux_cap_binding_seconds=sum(r.get('extra_speed_loss_by_flux_cap',0)>1e-6 for r in rows)))
        junction=trace['junction'];assert len(junction)==150
        assert max(abs(r['off_before_veh']-r['off_request_veh']) for r in junction)<1e-9
        receivers={r['time_s']:r for r in trace['receiving'] if r['lane']==1}
        merges={r['time_s']-1:r['merge_veh'] for r in trace['lanes'] if r['cell']==21 and r['lane']==1}
        for r in junction:assert abs(receivers[r['time_s']]['accepted_budget_veh']-merges[r['time_s']]-r['through_receiving_veh'])<1e-9
        example=next(r for r in trace['terms'] if r['time_sec']==2701 and r['cell']==20 and r['lane']==1)
        analysis[arm]=dict(grouped=grouped,example2701=example,
            junction_totals={k:sum(r[k] for r in junction) for k in ('through_request_veh','through_receiving_veh','off_request_veh','off_before_veh','off_accepted_veh')},
            zero_remaining_mainline_room_seconds=sum(r['through_receiving_veh']<1e-8 for r in junction))
        raw=read(Path('D:/VISSIM_runs/20261003_s73_vsl_replication95')/arm/f'decisions_sdmpc31_g_2700_{arm}_s73/state_002850.json')
        assert raw['sim_sec']==2850 and raw['vehicle_records']['complete']
        buckets={}
        for v in raw['vehicle_records']['records']:
            link=int(v['link_no'])
            if link not in chain:continue
            x=chain[link]['offset_m']+v['position_m'];c=min(bisect.bisect_right(ends,x),30)
            if c not in range(19,26):continue
            buckets.setdefault((c,int(v['lane_no'])),[]).append(dict(
                position_in_cell_m=x-cells[c]['start_m'],speed_kmh=v['speed_kph']))
        for (c,lane),vehicles in sorted(buckets.items()):
            model=next(r for r in trace['lanes'] if r['time_s']==2850 and r['cell']==c and r['lane']==lane)
            native_rows.append(dict(arm=arm,time_sec=2850,cell=c,lane=lane,native_n=len(vehicles),
                native_speed_kmh=statistics.fmean(v['speed_kmh'] for v in vehicles),
                native_stopped_below5=sum(v['speed_kmh']<5 for v in vehicles),
                native_stop_positions_m=[v['position_in_cell_m'] for v in vehicles if v['speed_kmh']<5],
                model_n=model['n_veh'],model_speed_kmh=model['v_kmh']))
    # The canonical diagnostic differs only by an optional prepared callback.
    old=ast.parse((HERE.parent/'coupled_lane200/probe_before202.py.txt').read_text(encoding='utf-8'))
    current=ast.parse((I/'probe_selected_arrival_path.py').read_text(encoding='utf-8'))
    fn=next(x for x in current.body if isinstance(x,ast.FunctionDef) and x.name=='probe_levers')
    j=next(i for i,x in enumerate(fn.args.kwonlyargs) if x.arg=='prepared_probe_callback')
    fn.args.kwonlyargs.pop(j);fn.args.kw_defaults.pop(j)
    selected=[x for x in fn.body if isinstance(x,ast.If) and isinstance(x.test,ast.Compare) and isinstance(x.test.left,ast.Name) and x.test.left.id=='prepared_probe_callback']
    assert len(selected)==1;fn.body.remove(selected[0]);assert ast.dump(current)==ast.dump(old)
    protocol=read(HERE/'protocol.json')
    for name,value in protocol['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest()=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    save('native2850.json',native_rows)
    save('assessment.json',dict(status='COMPLETE_SPEED_AND_RECEIVING_ATTRIBUTION',arms=analysis,
        binding_formula_checks=binding_checks,scalar_formula_checks=7200,
        default_diagnostic_AST_preserved=True,core_files_unchanged=len(protocol['source_sha256']),
        same150_results_exact200=True,old_STOP_preserved=True,
        predictions150=2,prediction_seconds=sum(x['wall_sec'] for x in summary['results'].values()),
        optimizer_iterations=0,fits=0,new_native=0,FZP_reads=0,production_adopted=False,
        initialization_failures=1,goal='ACTIVE_NOT_QUALIFIED',input_sha256=pins,
        limitations=['Scalar term changes and the flux cap are accounting on the SAME autonomous state, not a new no-cap trajectory.',
            'Native2850 lane data are endpoint snapshots, not150s average speeds or complete stoppage duration.',
            'The prior135 no-cap and189 fixed-priority failures remain; this audit alone does not justify removing caps or assigning a capacity bonus.']))
    print(json.dumps(dict(status='PASS',binding_formula_checks=binding_checks,goal='ACTIVE_NOT_QUALIFIED')))

def cohort204():
    """Current route labels and paired native progress, no FZP or rollout."""
    import csv
    import time
    from collections import Counter,defaultdict
    work=HERE.parent/'cohort204';assert not (work/'summary.json').exists()
    began=time.perf_counter()
    def output(name,v):(work/name).write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf8')
    output('protocol.json',dict(previous_goal_turn='PROGRESS203 joint calibration executed and rejected',
        question='Do the missed19-lane queues consist solely of exit-bound vehicles? Are route/lane changes or missing vehicles required to explain the paired endpoint displacement?',
        inputs='Eight150s COM frames, existing post2700 MER chunks, four176 cached5s vehicle windows. No FZP/9000 result scan.',
        scope='73 two matched RMrelease/VSL arms;67 four existing RM/VSL arms. Common initial IDs only for paired travel.',
        budget=dict(native=0,FZP_reads=0,forecasts=0,fits=0),
        cautions=['Post-treatment stopped cohort is descriptive, not an unbiased network treatment effect.',
                  '150s frames do not reveal exact stop onset, duration or every lane change.',
                  'Point detector travel is not an Omega exit metric and matched completed trips are censored.',
                  'NEXTLINK indicates a current planned branch, not a cause of stopping.']))
    geometry=read(I/'selected/port_gain/geometry.json')
    chain={int(x['link']):x for x in geometry['chains']['FW_E']}
    cells=sorted((x for x in geometry['cells'] if x['road']=='FW_E'),key=lambda x:x['cell'])
    ends=[x['end_m'] for x in cells]
    def vehicle(z):
        x=chain[z[1]]['offset_m']+z[3] if z[1] in chain else None
        return dict(id=int(z[0]),link=int(z[1]),lane=int(z[2]),pos=z[3],v=z[4],
            x=x,cell=min(bisect.bisect_right(ends,x),30) if x is not None else None,
            rd=z[6],route=z[7],nextlink=z[9])
    frames={};summaries=[];native_root=Path('D:/VISSIM_runs/20261003_s73_vsl_replication95')
    arms=('release','release_vsl90')
    for arm in arms:
        folder=native_root/arm/f'decisions_sdmpc31_g_2700_{arm}_s73'
        frames[arm]={}
        for t in (2700,2850,3000,3150):
            d=read(folder/f'lane_observations/frame_{t:06d}.json')
            assert d['complete'] and d['time_s']==t
            fr={int(z[0]):vehicle(z) for z in d['vehicles']};assert len(fr)==len(d['vehicles'])
            frames[arm][t]=fr
            for cell in range(19,26):
                for lane in (1,2,3):
                    vs=[z for z in fr.values() if z['cell']==cell and z['lane']==lane]
                    stopped=[z for z in vs if z['v']<5]
                    summaries.append(dict(arm=arm,t=t,cell=cell,lane=lane,n=len(vs),
                        mean_v=statistics.fmean(z['v'] for z in vs) if vs else None,
                        stopped=len(stopped),stop_exit=sum(z['nextlink']==10483 for z in stopped),
                        stop_through=sum(z['nextlink']==10702 for z in stopped),
                        stop_other_unknown=sum(z['nextlink'] not in (10483,10702) for z in stopped)))
    assert frames['release'][2700]==frames['release_vsl90'][2700]
    initial=frames['release'][2700]
    cohort=[]
    for vid,z in frames['release'][2850].items():
        if z['cell']!=19 or z['v']>=5:continue
        other=frames['release_vsl90'][2850].get(vid)
        assert vid in initial and other is not None and other['x'] is not None
        cohort.append(dict(id=vid,initial=initial[vid],end110=z,end90=other,
            progress_delta_m=other['x']-z['x'],same_route=(z['rd'],z['route'])==(other['rd'],other['route']),
            same_endpoint_lane=z['lane']==other['lane']))
    assert len(cohort)==12
    # Read only existing detector-entry rows. Exit-only rows are not extra vehicles.
    detector_path=I/'selected/obs150/obs150_detectors_v2.csv'
    pins[str(detector_path)]=hashlib.sha256(detector_path.read_bytes()).hexdigest()
    refs=('through:10481','through:10483','off_entry:10483')
    points={int(z['dcp_no']):z for z in csv.DictReader(detector_path.open(encoding='utf-8-sig',newline='')) if z['boundary_ref'] in refs}
    events={};event_counts={};duplicate_entries=[];read_bytes=0
    for arm in arms:
        folder=native_root/arm/f'decisions_sdmpc31_g_2700_{arm}_s73/obs150'
        install=read(folder/'obs150_install.json')
        assert install['detector_config']['sha256']==pins[str(detector_path)]
        for z in install['points']:
            if z['dcp_no'] in points:
                p=points[z['dcp_no']]
                assert z['readback']['link']==int(p['link']) and z['readback']['lane']==int(p['lane']) and abs(z['readback']['pos']-float(p['pos']))<1e-6
        by=defaultdict(dict);counts=Counter()
        for t in (2850,3000,3150):
            path=folder/f'mer_{t:06d}.jsonl';raw=path.read_bytes();read_bytes+=len(raw)
            pins[str(path)]=hashlib.sha256(raw).hexdigest()
            for line in raw.splitlines():
                seq,dcp,entry,exit_t,vid,vtype,v,length,ordinal=json.loads(line)
                if dcp not in points or entry is None or entry<2700 or entry>3150:continue
                label=points[dcp]['boundary_ref'];counts[label]+=1
                value=dict(t=entry,lane=int(points[dcp]['lane']),v=v,dcp=dcp)
                if label in by[vid]:
                    duplicate_entries.append(dict(arm=arm,id=vid,ref=label,previous=by[vid][label],new=value))
                    if entry>=by[vid][label]['t']:continue
                by[vid][label]=value  # First station entry, not an inferred second trip.
        events[arm]=dict(by);event_counts[arm]=dict(counts)
    journeys=[];excluded=Counter()
    common_entry=set(events[arms[0]])&set(events[arms[1]])&set(initial)
    for vid in sorted(common_entry):
        a,b=[events[arm][vid] for arm in arms];start_ref=refs[0]
        if start_ref not in a or start_ref not in b:excluded['missing_entry']+=1;continue
        endpoint_a=[ref for ref in refs[1:] if ref in a];endpoint_b=[ref for ref in refs[1:] if ref in b]
        if len(endpoint_a)!=1 or len(endpoint_b)!=1:excluded['missing_or_multiple_endpoint']+=1;continue
        if endpoint_a!=endpoint_b:excluded['changed_endpoint_branch']+=1;continue
        dest=endpoint_a[0];ta=a[dest]['t']-a[start_ref]['t'];tb=b[dest]['t']-b[start_ref]['t']
        assert ta>=0 and tb>=0
        journeys.append(dict(id=vid,branch=dest,entry110=a[start_ref],entry90=b[start_ref],exit110=a[dest],exit90=b[dest],
            travel110=ta,travel90=tb,delta_sec=tb-ta))
    # Freeze groups by the reference arm entry time, never by observed saving.
    travel=[]
    for branch in refs[1:]:
        for lo,hi in ((2700,2850),(2850,3000),(3000,3150)):
            rows=[z for z in journeys if z['branch']==branch and lo<=z['entry110']['t']<hi]
            travel.append(dict(branch=branch,start=lo,end=hi,count=len(rows),
                mean_delta_sec=statistics.fmean(z['delta_sec'] for z in rows) if rows else None,
                mean_entry_delta_sec=statistics.fmean(z['entry90']['t']-z['entry110']['t'] for z in rows) if rows else None,
                mean110=statistics.fmean(z['travel110'] for z in rows) if rows else None,
                mean90=statistics.fmean(z['travel90'] for z in rows) if rows else None))
    # Independent67 corroboration uses cached5s rows, not the live simulation.
    context67=[]
    for arm in ('hold','hold_vsl90','release','release_vsl90'):
        d=read(HERE.parent/'blocking176'/f'{arm}_frames.json.gz');ix={k:i for i,k in enumerate(d['fields'])}
        post=sorted((float(t),fr) for t,fr in d['frames'].items() if 2700<float(t)<3120.1-1e-6)
        assert len(post)==84 and all(abs(post[j+1][0]-post[j][0]-5)<1e-6 for j in range(83))
        for cell in range(19,26):
            for lane in (1,2,3):
                counts=Counter();timeline=[]
                for t,fr in post:
                    stops=[z for z in fr.values() if z[ix['cell']]==cell and z[ix['lane']]==lane and z[ix['speed']]<5]
                    timeline.append((t,len(stops)))
                    for z in stops:counts[str(z[ix['nextlink']])]+=1
                persistent=[timeline[j][0] for j in range(len(timeline)-2) if timeline[j][0]>=2730.1-1e-6 and all(n>=2 for _,n in timeline[j:j+3])]
                context67.append(dict(arm=arm,cell=cell,lane=lane,vehicle_samples=sum(counts.values()),by_current_nextlink=dict(counts),
                    first_three_frames_with_two_stops=persistent[0] if persistent else None))
    prior=read(HERE.parent/'regional_audit202/protocol.json')
    for p,digest in prior['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest()=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    output('snapshot_routes73.json',summaries);output('stopped_cohort73.json',cohort)
    output('paired_detector_journeys73.json',dict(rows=journeys,groups=travel,event_counts=event_counts,duplicate_station_entries=duplicate_entries,excluded=dict(excluded)))
    output('stop_context67.json',context67)
    output('summary.json',dict(status='COMPLETE_ROUTE_AND_TRAVEL_DIAGNOSTIC',cohort_size=len(cohort),
        same_route=sum(z['same_route'] for z in cohort),same_endpoint_lane=sum(z['same_endpoint_lane'] for z in cohort),
        progress_mean_m=statistics.fmean(z['progress_delta_m'] for z in cohort),
        progress_range_m=[min(z['progress_delta_m'] for z in cohort),max(z['progress_delta_m'] for z in cohort)],
        still_stopped90=sum(z['end90']['v']<5 for z in cohort),
        stopped110_destination=dict(Counter(str(z['end110']['nextlink']) for z in cohort)),
        journeys=len(journeys),detector_travel_groups=travel,core_files_unchanged=len(prior['source_sha256']),old_STOP_preserved=True,
        seconds=time.perf_counter()-began,MER_bytes=read_bytes,input_sha256=pins,
        forecasts=0,fits=0,native=0,FZP_reads=0,goal='ACTIVE_NOT_QUALIFIED'))
    print('COMPLETE204',len(cohort),len(journeys),round(time.perf_counter()-began,3))


def interaction205():
    """Classify native targets and observed slow chains; never a causal label or model input."""
    from collections import Counter, defaultdict
    import math
    import time
    began=time.perf_counter(); work=HERE.parent/'interaction205'
    assert not (work/'protocol.json').exists(), 'Preserve completed/failed diagnostic'
    def output(name, value):
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False,
                       indent=None if name.endswith('.gz') else 2).encode('utf-8')
        (work/name).write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
    output('protocol.json',dict(previous_goal_turn='PROGRESS204 common-ID route and passage evidence',
        question='Are braking/stopping samples linked directly or via an observed slow platoon to cross-lane targets?',
        scope='Four cached seed67 matched RM/VSL arms, 2670.1<=t<3120.1, cells19--25, all lanes. First30s common pre-intervention.',
        thresholds=dict(stopped_kmh=5,braking_mps2=-.5,chain_max_edges=64),
        populations='All current samples; braking a<-.5 with v>=5; stopped v<5; same-ID next5s stop and restart.',
        interaction_states=['Brake AX','Brake BX','Follow','Close up'],
        chain='Follow only current native Vehicle targets while both are observed, current node is active/slow, target is ahead, no repeats. Other-link edges are separate from same-link other-lane edges.',
        cautions=['Native selected target is not a complete causal list of forces or prior lane changes.',
                  'No future data in a controller. Five-second endpoints miss short changes and disappearing vehicles.',
                  'Rare direct events can initiate long platoons; small count does not rule out lane-change friction.',
                  'Deceleration samples are not vehicle-hours or a control reward.'],
        budget=dict(fits=0,forecasts=0,native=0,FZP_reads=0,production_edits=0)))
    active={'Brake AX','Brake BX','Follow','Close up'}
    fields=None; records=[]; chains=[]; source_stats={}; summary=[]
    for arm in ('hold','hold_vsl90','release','release_vsl90'):
        d=read(HERE.parent/'blocking176'/f'{arm}_frames.json.gz')
        if fields is None: fields=d['fields']
        assert fields==d['fields']
        ix={key:j for j,key in enumerate(fields)}
        frames={round(float(t),6):fr for t,fr in d['frames'].items()}
        times=sorted(frames); assert len(times)==91
        assert abs(times[0]-2670.1)<1e-6 and abs(times[-1]-3120.1)<1e-6
        assert all(abs(b-a-5)<1e-6 for a,b in zip(times,times[1:]))
        def relation(vid, fr):
            z=fr[vid]; tid=str(z[ix['target']]); target=fr.get(tid)
            if z[ix['target_type']]!='Vehicle': return 'not_vehicle'
            if tid==vid: return 'self'
            if target is None: return 'unobserved_vehicle'
            if target[ix['link']]!=z[ix['link']]: return 'other_link'
            if target[ix['lane']]!=z[ix['lane']]: return 'other_lane_same_link'
            return 'same_lane_ahead' if target[ix['x']]>z[ix['x']] else 'same_lane_not_ahead'
        for t in times[:-1]:
            fr=frames[t]; future=frames[round(t+5,6)]
            for vid,z in fr.items():
                cell=int(z[ix['cell']])
                if not 19<=cell<=25: continue
                target=fr.get(str(z[ix['target']])); n=future.get(vid)
                v=float(z[ix['speed']]); a=float(z[ix['accel']]); state=z[ix['interaction']]
                record=dict(arm=arm,t=t,block=int(round((t-2670.1)/5))//30,id=vid,
                    cell=cell,lane=z[ix['lane']],link=z[ix['link']],x=z[ix['x']],v=v,a=a,
                    nextlink=z[ix['nextlink']],lnchg=z[ix['lnchg']],state=state,active=state in active,
                    target=str(z[ix['target']]),relation=relation(vid,fr),
                    target_lnchg=target[ix['lnchg']] if target else None,
                    target_v=target[ix['speed']] if target else None,
                    target_dx=target[ix['x']]-z[ix['x']] if target else None,
                    future_v=n[ix['speed']] if n else None,
                    future_cell=n[ix['cell']] if n else None,
                    future_lane=n[ix['lane']] if n else None)
                records.append(record)
                if v>=5: continue
                seen={vid}; path=[vid]; current=vid; edges=[]; reason=None
                for depth in range(64):
                    cur=fr[current]; tid=str(cur[ix['target']]); trg=fr.get(tid)
                    if cur[ix['interaction']] not in active: reason='inactive_native_state'; break
                    if cur[ix['target_type']]!='Vehicle': reason='nonvehicle_target'; break
                    if tid in seen: reason='cycle_or_self'; break
                    if trg is None: reason='unobserved_target'; break
                    if trg[ix['x']]<=cur[ix['x']]: reason='target_not_ahead'; break
                    edges.append(relation(current,fr));path.append(tid);seen.add(tid);current=tid
                    if trg[ix['speed']]>=5: reason='moving_target'; break
                else: reason='edge_budget'
                end=fr[current]
                chains.append(dict(arm=arm,t=t,id=vid,cell=cell,lane=z[ix['lane']],block=record['block'],
                    path=path,edges=edges,reason=reason,root=current,root_cell=end[ix['cell']],
                    root_lane=end[ix['lane']],root_v=end[ix['speed']],root_a=end[ix['accel']],
                    root_state=end[ix['interaction']],root_lnchg=end[ix['lnchg']],
                    root_nextlink=end[ix['nextlink']],span_m=end[ix['x']]-z[ix['x']],
                    any_observed_lane_change=any(fr[k][ix['lnchg']] not in ('','None') for k in path),
                    crosses_lane='other_lane_same_link' in edges,other_link='other_link' in edges))
        source_stats[arm]=dict(frames=len(times),source_rows=sum(map(len,frames.values())),
                              relevant_rows=sum(z['arm']==arm for z in records))
    predicates={'all':lambda z:True,'braking':lambda z:z['v']>=5 and z['a']<-.5,
        'stopped':lambda z:z['v']<5,'stop_onset':lambda z:z['v']>=5 and z['future_v'] is not None and z['future_v']<5,
        'restart':lambda z:z['v']<5 and z['future_v'] is not None and z['future_v']>=5}
    for arm in source_stats:
        rr=[z for z in records if z['arm']==arm]
        for cell in (None,*range(19,26)):
            for block in (None,0,1,2):
                group=[z for z in rr if (cell is None or z['cell']==cell) and (block is None or z['block']==block)]
                for population,predicate in predicates.items():
                    rows=[z for z in group if predicate(z)]; active_rows=[z for z in rows if z['active']]
                    summary.append(dict(arm=arm,cell=cell,block=block,population=population,n=len(rows),
                        relations=dict(Counter(z['relation'] for z in rows)),
                        active_n=len(active_rows),active_relations=dict(Counter(z['relation'] for z in active_rows)),
                        source_lc=sum(z['lnchg'] not in ('','None') for z in rows),
                        target_lc=sum(z['target_lnchg'] not in (None,'','None') for z in rows),
                        missing_future=sum(z['future_v'] is None for z in rows),
                        negative_acceleration_sum_mps2=math.fsum(max(0,-z['a']) for z in rows)))
    chain_summary=[]
    for arm in source_stats:
        for block in (None,0,1,2):
            cc=[z for z in chains if z['arm']==arm and (block is None or z['block']==block)]
            chain_summary.append(dict(arm=arm,block=block,n=len(cc),
                reasons=dict(Counter(z['reason'] for z in cc)),cross_lane=sum(z['crosses_lane'] for z in cc),
                any_lc=sum(z['any_observed_lane_change'] for z in cc),
                other_link=sum(z['other_link'] for z in cc),
                mean_edges=statistics.fmean(len(z['edges']) for z in cc) if cc else None,
                moving_root_a_mean=statistics.fmean(z['root_a'] for z in cc if z['reason']=='moving_target')
                    if any(z['reason']=='moving_target' for z in cc) else None))
    prior=read(HERE/'protocol.json')
    for p,digest in prior['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest()=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    for p,digest in pins.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest
    output('rows.json.gz',records);output('slow_chains.json.gz',chains)
    output('summary.json',dict(status='COMPLETE_OBSERVED_INTERACTION_DIAGNOSTIC',rows=len(records),chains=len(chains),
        source_stats=source_stats,populations=summary,chain_summary=chain_summary,input_sha256=pins,
        seconds=time.perf_counter()-began,core_files_unchanged=len(prior['source_sha256']),old_STOP_preserved=True,
        fits=0,forecasts=0,native=0,FZP_reads=0,goal='ACTIVE_NOT_QUALIFIED'))
    print('COMPLETE205',len(records),len(chains),round(time.perf_counter()-began,3))


def episodes208():
    """Observed slow episodes, separating recurrence from prolonged stopping."""
    import time
    from collections import Counter,defaultdict
    began=time.perf_counter();work=HERE.parent/'stop_episodes208'
    assert not (work/'summary.json').exists()
    def output(name,data):
        raw=json.dumps(data,indent=None if name.endswith('.gz') else 2,allow_nan=False).encode()
        (work/name).write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
    output('protocol.json',dict(previous_goal_turn='PROGRESS207 native postprocess compatibility repair',
        question='Does the VSL/RM reduction in slow residence arise from fewer involved vehicles, fewer repeat episodes, or shorter observed episodes?',
        cases=['hold','hold_vsl90','release','release_vsl90'],seed=67,
        time=[2700.1,3120.1],dt=5,cells=list(range(19,26)),thresholds_kmh=[5,20],
        method='Contiguous same-ID slow samples inside19--25. Changes of cell or lane within region do not break an episode. Track temporal/spatial censoring explicitly.',
        exposure='Left-sampled veh*s, 84 intervals; not exact stop duration, delay or OmegaTTT.',
        decomposition='Total sampled exposure = involved vehicles * episodes/vehicle * sampled seconds/episode. Symmetric Shapley allocation of this accounting identity, not causal mediation.',
        prior_review=['Claude worklog/P_PLANT','134 composition/acceleration','176/177 threshold ledger',
                      '178/183 two-state failure','205 target chains','206 same-leader past-dv failure'],
        budget=dict(fits=0,forecasts=0,native=0,FZP_reads=0,production_edits=0),
        caution='Five-second samples miss shorter stop/restart events. Different realized populations and censoring prevent causal duration claims; no coefficient is adopted.'))
    episodes=[];totals=[];group_rows=[];hazards=[];input_sources={}
    for arm in ('hold','hold_vsl90','release','release_vsl90'):
        source=HERE.parent/'blocking176'/f'{arm}_frames.json.gz'
        d=read(source);input_sources[str(source)]=pins[str(source)]
        ix={k:i for i,k in enumerate(d['fields'])}
        frames={round(float(t),6):fr for t,fr in d['frames'].items()}
        times=[t for t in sorted(frames) if 2700.1<=t<3120.1]
        assert len(times)==84 and frames.get(round(times[-1]+5,6)) is not None
        for threshold in (5,20):
            active={};history=Counter();group=defaultdict(lambda:Counter())
            def slow(z):return z is not None and 19<=z[ix['cell']]<=25 and z[ix['speed']]<threshold
            for t in times:
                fr=frames[t];past=frames[round(t-5,6)];future=frames[round(t+5,6)]
                current={vid:z for vid,z in fr.items() if slow(z)}
                assert not (set(active)-set(current)),(arm,t,'lost active episode')
                for vid,z in current.items():
                    old=past.get(vid);new=future.get(vid)
                    if vid not in active:
                        if t==times[0]:start_kind='window_left'
                        elif old is None:start_kind='missing_previous'
                        elif not 19<=old[ix['cell']]<=25:start_kind='spatial_entry'
                        else:
                            assert old[ix['speed']]>=threshold
                            start_kind='observed_onset'
                        history[vid]+=1
                        active[vid]=dict(arm=arm,threshold=threshold,id=vid,ordinal=history[vid],
                            start=t,start_kind=start_kind,start_cell=z[ix['cell']],start_lane=z[ix['lane']],
                            start_x=z[ix['x']],samples=[])
                    e=active[vid]
                    e['samples'].append([t,int(z[ix['cell']]),int(z[ix['lane']]),float(z[ix['speed']])])
                    known=new is not None and 19<=new[ix['cell']]<=25
                    age=5*(len(e['samples'])-1)
                    age_bin=0 if age==0 else (1 if age<15 else (2 if age<30 else 3))
                    g=group[(age_bin,e['start_kind']=='observed_onset')]
                    g['samples']+=1;g['known_next']+=int(known)
                    g['restart_next']+=int(known and new[ix['speed']]>=threshold)
                    if not slow(new) or t==times[-1]:
                        if t==times[-1]:end_kind='window_right'
                        elif new is None:end_kind='missing_next'
                        elif not 19<=new[ix['cell']]<=25:end_kind='spatial_exit'
                        else:end_kind='observed_restart'
                        e.update(end_sample=t,end_kind=end_kind,end_cell=int(z[ix['cell']]),
                            sampled_seconds=len(e['samples'])*5,
                            full_observed=e['start_kind']=='observed_onset' and end_kind=='observed_restart')
                        episodes.append(e);del active[vid]
            assert not active
            es=[e for e in episodes if e['arm']==arm and e['threshold']==threshold]
            seconds=sum(e['sampled_seconds'] for e in es)
            per_id=Counter(e['id'] for e in es)
            expected=sum(slow(z) for t in times for z in frames[t].values())*5
            assert seconds==expected
            full=[e for e in es if e['full_observed']]
            totals.append(dict(arm=arm,threshold=threshold,vehicles=len(per_id),episodes=len(es),
                repeated_vehicles=sum(n>1 for n in per_id.values()),repeat_episodes=sum(n-1 for n in per_id.values()),
                sampled_seconds=seconds,episodes_per_vehicle=len(es)/len(per_id) if per_id else None,
                seconds_per_episode=seconds/len(es) if es else None,
                start_censoring=dict(Counter(e['start_kind'] for e in es)),
                end_censoring=dict(Counter(e['end_kind'] for e in es)),full_observed_episodes=len(full),
                full_observed_mean_seconds=statistics.fmean(e['sampled_seconds'] for e in full) if full else None,
                full_observed_median_seconds=statistics.median(e['sampled_seconds'] for e in full) if full else None,
                one_sample_episodes=sum(len(e['samples'])==1 for e in es)))
            for (age_bin,known_onset),g in group.items():
                hazards.append(dict(arm=arm,threshold=threshold,age_bin=age_bin,known_onset=known_onset,**g))
            for cell in range(19,26):
                for lane in (1,2,3):
                    ss=[s for e in es for s in e['samples'] if s[1:3]==[cell,lane]]
                    group_rows.append(dict(arm=arm,threshold=threshold,cell=cell,lane=lane,
                        samples=len(ss),sampled_seconds=5*len(ss)))
    import itertools,math
    decompositions=[]
    for left,right in [('release','release_vsl90'),('hold','hold_vsl90'),('release','hold'),('release_vsl90','hold_vsl90')]:
        for threshold in (5,20):
            pair=[next(z for z in totals if z['arm']==arm and z['threshold']==threshold) for arm in (left,right)]
            fields=['vehicles','episodes_per_vehicle','seconds_per_episode']
            x,y=[[z[k] for k in fields] for z in pair];parts=[0.,0.,0.]
            for order in itertools.permutations(range(3)):
                v=list(x)
                for j in order:
                    before=math.prod(v);v[j]=y[j];parts[j]+=(math.prod(v)-before)/6
            delta=pair[1]['sampled_seconds']-pair[0]['sampled_seconds']
            assert abs(sum(parts)-delta)<1e-8
            decompositions.append(dict(left=left,right=right,threshold=threshold,delta_sampled_seconds=delta,
                accounting_parts_seconds=dict(zip(fields,parts))))
    prior=read(HERE/'protocol.json')
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in prior['source_sha256'].items())
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest()=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    output('episodes.json.gz',episodes);output('age_context.json',hazards);output('cell_lane_exposure.json',group_rows)
    output('summary.json',dict(status='COMPLETE_OBSERVED_EPISODE_ACCOUNTING',totals=totals,
        accounting_decomposition=decompositions,input_sha256=input_sources,
        seconds=time.perf_counter()-began,core_files_unchanged=len(prior['source_sha256']),
        fits=0,forecasts=0,native=0,FZP_reads=0,goal='ACTIVE_NOT_QUALIFIED'))
    print(json.dumps(dict(totals=totals,accounting_decomposition=decompositions,seconds=time.perf_counter()-began)))


if __name__=='__main__':
    import sys
    if '--episodes208' in sys.argv:episodes208()
    elif '--interaction205' in sys.argv:interaction205()
    elif '--cohort204' in sys.argv:cohort204()
    else:main()
