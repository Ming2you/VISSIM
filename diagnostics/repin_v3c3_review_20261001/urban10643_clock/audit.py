"""Two bounded conditional clock substitutions; never autonomous forecast input.

Reuse existing held arrival cohorts and held replay results. Read native MER only
to describe each actual policy, not to manufacture its unobserved counterfactual.
"""
import copy
import gzip
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent
ROOT = REVIEW.parents[1]
PINS = {}


def read(path):
    path = Path(path)
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def save(name, value):
    path = HERE / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load_module(path):
    spec = importlib.util.spec_from_file_location('conditional_clock_replay', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    PINS[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return module


def check_production(prior):
    for name, digest in prior['production_exact'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    stop = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest() == prior['stop_sha256']


def native_events(replay, folder, windows, detectors):
    events = {}
    removed = []
    targets = {d.dcp_no: d for d in detectors if
               (d.role == 'head' and d.link == 71) or d.role == 'x10643_exit'}
    for end in (2850, 3000, 3150):
        raw = read(folder / f'state_{end:06d}.json')
        bundle = replay.oc.load_bundle(raw)
        removed.extend(replay.oc.window_removals(bundle.err_rows, 2700., 3150.))
        for e in bundle.mer_rows:
            if e.dcp not in targets or e.t_entry is None or not 2700. < e.t_entry <= 3150.:
                continue
            d = targets[e.dcp]
            key = (e.dcp, e.ordinal)
            event = dict(vehicle=e.veh, time=e.t_entry, lane=d.lane, role=d.role)
            assert key not in events or events[key] == event
            events[key] = event
    events = sorted(events.values(), key=lambda e: (e['time'], e['role'], e['lane']))
    program = replay.NativeProgram(windows)
    green_cycles = []
    for sg, lanes in ((2, (1, 2, 3)), (5, (4, 5))):
        for start, end in program.green[sg]:
            record = dict(sg=sg, green=[start, end], lanes={})
            for lane in lanes:
                ts = [e['time'] for e in events if e['role'] == 'head' and
                      e['lane'] == lane and start <= e['time'] < end]
                gaps = ([ts[0]-start] + [b-a for a, b in zip(ts, ts[1:])] +
                        [end-ts[-1]]) if ts else [end-start]
                record['lanes'][str(lane)] = dict(
                    crossings=len(ts), times=ts, first_lag_s=ts[0]-start if ts else None,
                    last_to_green_end_s=end-ts[-1] if ts else None,
                    max_empty_interval_s=max(gaps),
                    first10=sum(t < start+10 for t in ts),
                    middle=sum(start+10 <= t < end-10 for t in ts),
                    last10=sum(t >= max(start+10, end-10) for t in ts))
            green_cycles.append(record)
    for window in windows:
        for h in window['heads']:
            lane = h['lane']; sg = int(h['sg'])
            es = [e for e in events if e['role'] == 'head' and e['lane'] == lane and
                  window['start_sec'] < e['time'] <= window['end_sec']]
            assert len(es) == h['crossings'], (lane, es, h)
            assert sum(program.green_at(e['time'], sg) for e in es) == h['qualified_crossings']
    return dict(events=events, green_cycles=green_cycles,
                head_count=sum(e['role']=='head' for e in events),
                off10643_drain=sum(e['role']=='x10643_exit' for e in events),
                local_removals=[e for e in removed if e['link'] in replay.LOCAL])


def main():
    assert not (HERE/'assessment.json').exists()
    prior = read(REVIEW/'urban10643_lateral_completion/completion.json')
    check_production(prior)
    replay = load_module(REVIEW/'urban10643_conditional/replay.py')
    old = read(REVIEW/'urban10643_conditional/assessment.json')
    manifest = read(REVIEW/'retained10638/candidate_manifest.json')
    network = ROOT/manifest['sources']['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest() == manifest['sources']['network']['sha256']
    protocol = read(ROOT/manifest['sources']['reference_protocol']['path'])
    cache = read(REVIEW/'lane10643_native/rows.json.gz')
    current = replay.observe(replay.raw_frame([r for r in cache['rows'] if
        r[0] == replay.START and r[2] in replay.LOCAL], replay.START), *replay.geometry(network))
    assert len(current['vehicles']) == old['native']['initial_n'] == 35
    clocks = read(REVIEW/'local10643_receiver/head_audit.json')['cases']
    trace = read(replay.I/'closedloop_recorded2700_select_check_trace10681_entry10643/held_actual_RM_C10681_trace.json.gz')
    exit_room = {}
    for r in trace['local_receiver_diagnostics']['resources']:
        if r['kind'] == 'lane_urban_exit_receiving':
            exit_room.setdefault(int(r['start_sec']), {})[int(r['resource'])] = r['available_veh']
    assert set(exit_room) >= set(range(2700, 3145))
    save('protocol.json', dict(
        status='prepared_two_conditional_clock_substitutions',
        previous_goal_turn='no_progress_explanatory_answer_only',
        period_s=[replay.START, replay.END], max_new_replays=2,
        held_arrivals=204, held_initial_stock=35,
        variations='Held actual arrival brackets early/late; selected verified green clock only.',
        held_reference='Reuse original unchanged early/late frozen_exit conserved results.',
        future_native_input=True, autonomous=False, no_new_fzp=True, no_new_native=True,
        limits=['Selected native arrivals are not held fixed by the real closed-loop experiment.',
                'Native head and model connector discharge are distinct count planes.',
                'Native short sampling brackets cannot reconstruct exact lane-change chronology.',
                'No coefficient or production source change; no full-network gain claim.']))
    detectors, _ = replay.oc.read_detector_csv(replay.I/'selected/obs150/obs150_detectors_v2.csv')
    folders = {
        '47hold': Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47'),
        '47selected': Path('D:/VISSIM_runs/20261002_sc1001_corrected2700_s47/selected/decisions_sdmpc31_g_2700_selected_s47')}
    native = {name: native_events(replay, folder, clocks[name], detectors)
              for name, folder in folders.items()}
    save('native_clock_events.json', native)
    results = {}
    for timing in ('early', 'late'):
        result = replay.run(copy.deepcopy(current), network, protocol, old['events'],
            replay.NativeProgram(clocks['47selected']), exit_room, timing, 'frozen_exit', [])
        results[timing] = dict(held_clock=old['cases'][timing+'_frozen_exit_conserved'],
                               selected_clock=result)
        save(timing+'.json', result)
        print(timing, 'selected clock', result['departures'], 'stock', result['final_n'],
              'off admitted', sum(v for k,v in result['admitted_by_source'].items()
                                  if k.startswith('off10643:')), flush=True)
    check_production(prior)
    save('assessment.json', dict(status='completed_conditional_clock_diagnosis',
        results=results, native=native, source_pins=PINS,
        production_exact=prior['production_exact'], stop_sha256=prior['stop_sha256'],
        new_component_replays=2, new_full_forecasts=0, new_fzp=0, new_native=0,
        coefficient_changes=0, production_changes=0, goal_complete=False))


def extract_selected_cache():
    """One scan of a completed file, using the earlier bounded extractor."""
    target = HERE/'selected_native'
    target.mkdir(exist_ok=True)
    assert not (target/'rows.json.gz').exists(), 'Reuse the cache; never rescan.'
    save('selected_cache_protocol.json',dict(
        reason='Existing selected observations are only150s; no selected5s local cache exists.',
        source='D:/VISSIM_runs/20261002_sc1001_corrected2700_s47/selected/vissim_eval/sdmpc31_g_2700_selected_s47_001.fzp',
        max_fzp_passes=1, retained_period_s=[2550,3150.1],
        future_rows_usage='conditional diagnosis and evaluation only',
        no_active_owned_job_at_preflight=True, no_new_simulation=True))
    extractor = load_module(REVIEW/'lane10643_native/audit.py')
    extractor.SOURCE = Path('D:/VISSIM_runs/20261002_sc1001_corrected2700_s47/selected/vissim_eval/sdmpc31_g_2700_selected_s47_001.fzp')
    extractor.HERE = target
    extractor.extract()


def arrival_events(cache, replay, network):
    routes, exits = replay.geometry(network)
    frames = defaultdict(dict)
    for row in cache['rows']:
        frames[row[0]][row[1]] = row
    last = {}; visits = Counter(); events = []; transitions = []
    for t, rows in sorted(frames.items()):
        for vid, r in rows.items():
            old = last.get(vid)
            if t > replay.START and r[2] in replay.LOCAL and (old is None or old[2] not in replay.LOCAL):
                assert old is not None and abs(t-old[0]-5)<1e-6, (t,vid,old)
                assert old[2] in (70,10776,10643,10640,10700,10638), old
                if old[2]==10638:
                    # A5s sample can skip70/10776. Require observed successor
                    # and static path continuity; do not invent an exact time.
                    path=routes.get((old[6],old[7]))
                    assert old[9]==70 and r[2]==126 and path, (old,r,path)
                    j=path.index(10638)
                    assert tuple(path[j:j+4])==(10638,70,10776,126),path
                obs = replay.observe(replay.raw_frame([r],t),routes,exits)['vehicles'][0]
                source = ('off10643' if old[2]==10643 else 'upstream70' if old[2] in (70,10776,10638)
                          else 'city10640' if old[2]==10640 else 'side10700')
                lane = old[3] if source=='off10643' else old[3]+3 if source=='city10640' else r[3]
                visits[vid] += 1
                events.append(dict(vehicle=vid,visit_label=f'{vid}:visit{visits[vid]}',
                    source=source,entry_lane=lane,bracket=[old[0],t],destination=obs['connector'],
                    unassigned_continuation=replay.unassigned_continuation(obs,routes),
                    order=[-old[4],vid],first_local_link=r[2],first_local_lane=r[3],first_local_position=r[4],
                    last_outside_link=old[2],last_outside_position=old[4],observed_route=r[6:9]))
            if t > replay.START and old is not None and old[2] in replay.LOCAL and r[2] not in replay.LOCAL:
                transitions.append(dict(vehicle=vid,bracket=[old[0],t],target=r[2]))
            last[vid] = r
    initial_ids={v[1] for v in frames[replay.START].values() if v[2] in replay.LOCAL}
    assert max(visits.values())==1 and not (initial_ids & set(visits))
    return events,frames,transitions


def queue_arrival_audit(cache, replay, network, native):
    routes, exits = replay.geometry(network)
    frames=defaultdict(dict)
    for row in cache['rows']:
        frames[row[0]][row[1]]=row

    def intent(row):
        if row[2] == 71 and row[9] in exits:
            return int(row[9])
        route = routes.get((row[6], row[7])) if row[8].lower()=='static' else None
        if route and 71 in route:
            i=route.index(71)
            if i+1 < len(route) and route[i+1] in exits:
                return route[i+1]
        return None

    def lane_state(rows, lane):
        cars = sorted([r for r in rows.values() if r[2]==71 and r[3]==lane and r[4]<=78.8],
                      key=lambda r:-r[4])
        stopped=[r for r in cars if r[5]<5.]
        classes=Counter('unknown' if intent(r) is None else
                        'compatible' if lane in exits[intent(r)]['lanes'] else 'wrong_lane'
                        for r in stopped)
        front = cars[0] if cars else None
        return dict(stock_before_head=len(cars),stopped=len(stopped),moving=len(cars)-len(stopped),
            stopped_destinations=dict(classes),front=(dict(vehicle=front[1],position=front[4],
            speed=front[5],destination=intent(front),compatible=(lane in exits[intent(front)]['lanes'])
            if intent(front) is not None else None) if front else None))

    result=[]
    for cycle in native['green_cycles']:
        start,end=cycle['green']
        before=max(t for t in frames if t<=start)
        after=min(t for t in frames if t>=start)
        for lane_s, cross in cycle['lanes'].items():
            lane=int(lane_s)
            departures=[e for e in native['events'] if e['role']=='head' and e['lane']==lane
                        and start<=e['time']<end]
            cohorts=Counter()
            for event in departures:
                r=frames[before].get(event['vehicle'])
                if r is None or r[2] not in replay.LOCAL:
                    kind='not_yet_in_local_area_at_pre_green_sample'
                elif r[2]!=71:
                    kind='upstream_local_stopped' if r[5]<5 else 'upstream_local_moving'
                elif r[5]>=5:
                    kind='on71_moving'
                elif r[3]!=lane:
                    kind='on71_stopped_other_lane'
                else:
                    kind='on71_stopped_same_lane'
                cohorts[kind]+=1
            tail_begin=max(cross['times']) if cross['times'] else start
            tail=[dict(time=t,**lane_state(frames[t],lane)) for t in sorted(frames)
                  if tail_begin<t<end]
            result.append(dict(sg=cycle['sg'],lane=lane,green=[start,end],
                pre_green_epoch=before,post_green_epoch=after,
                pre_green=lane_state(frames[before],lane),
                post_green=lane_state(frames[after],lane),
                crossings=len(departures),crossing_cohorts=dict(cohorts),
                final_empty_interval_s=end-tail_begin,tail_samples=tail))
    return dict(cycles=result,stopped_threshold_kmh=5.,head_approx_position_m=78.8,
        limits=['Pre-green cohorts refer to the preceding5s sample, not exact green-on state.',
                'Stopped compatible-lane stock is not guaranteed dischargeable; downstream and leader still matter.',
                'Wrong-lane front samples are an association, not proof of every lost crossing.',
                'Missing from local area at pre-green sample means approaching/later arrival, never extra initial queue.'])


def arrival_factorial():
    assert not (HERE/'assessment_arrival_factorial.json').exists()
    prior=read(REVIEW/'urban10643_lateral_completion/completion.json')
    check_production(prior)
    replay=load_module(REVIEW/'urban10643_conditional/replay.py')
    old=read(REVIEW/'urban10643_conditional/assessment.json')
    manifest=read(REVIEW/'retained10638/candidate_manifest.json')
    network=ROOT/manifest['sources']['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest()==manifest['sources']['network']['sha256']
    protocol=read(ROOT/manifest['sources']['reference_protocol']['path'])
    caches={'held':read(REVIEW/'lane10643_native/rows.json.gz'),
            'selected':read(HERE/'selected_native/rows.json.gz')}
    parsed={name:arrival_events(cache,replay,network) for name,cache in caches.items()}
    assert parsed['held'][0]==old['events'], 'Reuse contract differs'
    assert parsed['held'][2]==old['native']['known_exit_pairs']
    starts={name:sorted((r for r in frames[replay.START].values() if r[2] in replay.LOCAL),key=lambda r:r[1])
            for name,(_,frames,_) in parsed.items()}
    assert starts['held']==starts['selected'], 'Not the same initial native state'
    current=replay.observe(replay.raw_frame(starts['held'],replay.START),*replay.geometry(network))
    clocks=read(REVIEW/'local10643_receiver/head_audit.json')['cases']
    native=read(HERE/'native_clock_events.json')
    save('arrival_factorial_protocol.json',dict(
        hypothesis='Distinguish present queue, future arrivals and signal timing before cell calibration.',
        shared_initial_native_exact=True,initial_local_n=35,
        held_arrivals=len(parsed['held'][0]),selected_arrivals=len(parsed['selected'][0]),
        max_new_replays=4,total_replays_including_two_invalid=8,
        reuse='Held-arrival/held-clock and held-arrival/selected-clock early/late already available.',
        receiver='unrestricted exit in all arms; conditional component isolation only',
        preflight_failure='Original held-only extractor did not include5s skip10638->70->10776->126. Static path/successor continuity now required; old failure retained, no forecasts preceded it.',
        future_inputs=True,autonomous=False,new_fit=0,new_native=0,new_fzp_passes_total=1))
    queue_audit={name:queue_arrival_audit(cache,replay,network,native['47'+('hold' if name=='held' else name)])
                 for name,cache in caches.items()}
    save('native_queue_arrival.json',queue_audit)
    source_tables={}
    for name,(events,frames,transitions) in parsed.items():
        removals=[e for e in native['47'+('hold' if name=='held' else name)]['local_removals']
                  if replay.START<e['time_sec']<=replay.END]
        final=sum(r[2] in replay.LOCAL for r in frames[replay.END].values())
        source_tables[name]=dict(arrivals=len(events),
            skipped_upstream_samples=sum(e['last_outside_link']==10638 for e in events),
            by_source=dict(Counter(e['source'] for e in events)),
            by_destination=dict(Counter(str(e['destination']) for e in events)),
            source_lane_destination=[dict(source=k[0],lane=k[1],destination=k[2],n=v)
                for k,v in Counter((e['source'],e['entry_lane'],e['destination']) for e in events).items()],
            final_local_stock=final,abnormal_removals=removals,
            native_normal_departures_mass_balance=35+len(events)-final-len(removals),
            events=events,known_exit_pairs=transitions)
    save('native_arrival_sources.json',source_tables)
    results={}
    for clock in ('held','selected'):
        for timing in ('early','late'):
            result=replay.run(copy.deepcopy(current),network,protocol,parsed['selected'][0],
                replay.NativeProgram(clocks['47'+('hold' if clock=='held' else clock)]),{},
                timing,'unrestricted_exit',[])
            key='selected_arrivals_'+clock+'_clock_'+timing
            save(key+'.json',result);results[key]=result
            print(key,result['departures'],'local_n',result['final_n'],
                  'off admitted',sum(v for k,v in result['admitted_by_source'].items()
                                     if k.startswith('off10643:')),flush=True)
    check_production(prior)
    save('assessment_arrival_factorial.json',dict(status='completed_conditional_arrival_clock_factorial',
        results=results,native_sources=source_tables,source_pins=PINS,
        production_exact=prior['production_exact'],stop_sha256=prior['stop_sha256'],
        initial_native_exact=True,initial_vs_arrivals_disjoint=True,old_cohort_extraction_exact=True,
        new_replays_total=8,invalid_replays=2,new_full_forecasts=0,new_fzp=1,new_native=0,
        coefficient_changes=0,goal_complete=False))


def repair_clock_budget():
    """Remove the held signal embedded in the frozen receiving budget.

    Both arms use the earlier unrestricted-exit component convention. This is
    still a conditional local experiment, never a feasible full-network claim.
    The first two results remain saved and are explicitly disqualified.
    """
    assert not (HERE/'assessment_clock_only.json').exists()
    prior = read(REVIEW/'urban10643_lateral_completion/completion.json')
    check_production(prior)
    replay = load_module(REVIEW/'urban10643_conditional/replay.py')
    old = read(REVIEW/'urban10643_conditional/assessment.json')
    manifest = read(REVIEW/'retained10638/candidate_manifest.json')
    network = ROOT/manifest['sources']['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest() == manifest['sources']['network']['sha256']
    protocol = read(ROOT/manifest['sources']['reference_protocol']['path'])
    cache = read(REVIEW/'lane10643_native/rows.json.gz')
    current = replay.observe(replay.raw_frame([r for r in cache['rows'] if
        r[0] == replay.START and r[2] in replay.LOCAL], replay.START), *replay.geometry(network))
    clocks = read(REVIEW/'local10643_receiver/head_audit.json')['cases']
    trace = read(replay.I/'closedloop_recorded2700_select_check_trace10681_entry10643/held_actual_RM_C10681_trace.json.gz')
    program = replay.NativeProgram(clocks['47selected'])
    bad_budget = [dict(time=r['start_sec'], held_budget=r['available_veh'])
                  for r in trace['local_receiver_diagnostics']['resources']
                  if r['kind']=='lane_urban_exit_receiving' and r['resource']=='10634'
                  and replay.START <= r['start_sec']+.1 < replay.END
                  and program.green_at(r['start_sec']+.1,2) and r['available_veh']==0.]
    assert bad_budget
    save('protocol_amended.json', dict(
        reason='Initial frozen10634 receiving already contains held SG2 clock; incompatible counterfactual, not physical prediction.',
        invalid_artifacts=['early.json','late.json','assessment.json'],
        conflicting_green_steps=len(bad_budget), conflicting_examples=bad_budget[:5],
        replacement='Compare selected clock unrestricted_exit with cached held unrestricted_exit.',
        max_additional_replays=2, total_replays_including_invalid=4,
        no_physical_parameter_change=True, autonomous=False, no_new_native=True,
        limits='Downstream exit room removed in BOTH arms for signal-isolation diagnosis only.'))
    results = {}
    for timing in ('early','late'):
        result = replay.run(copy.deepcopy(current), network, protocol, old['events'],
            program, {}, timing, 'unrestricted_exit', [])
        held = old['cases'][timing+'_unrestricted_exit_conserved']
        results[timing] = dict(held_clock=held, selected_clock=result)
        save(timing+'_clock_only.json',result)
        print(timing,'clock-only departures',held['departures'],result['departures'],
            'off admitted',sum(v for k,v in result['admitted_by_source'].items()
                              if k.startswith('off10643:')),flush=True)
    check_production(prior)
    save('assessment_clock_only.json',dict(status='completed_corrected_conditional_clock_diagnosis',
        results=results, conflicting_green_steps=len(bad_budget), source_pins=PINS,
        production_exact=prior['production_exact'], stop_sha256=prior['stop_sha256'],
        original_two_counterfactuals_invalid=True, new_component_replays=4,
        new_full_forecasts=0,new_fzp=0,new_native=0,goal_complete=False))


def repair_skipped_crossing():
    """MER proves one entire local traversal skipped by the5s FZP samples."""
    assert not (HERE/'assessment_mer_repair.json').exists()
    prior=read(REVIEW/'urban10643_lateral_completion/completion.json');check_production(prior)
    replay=load_module(REVIEW/'urban10643_conditional/replay.py')
    factor=read(HERE/'assessment_arrival_factorial.json')
    native=read(HERE/'native_clock_events.json')['47selected']
    cache=read(HERE/'selected_native/rows.json.gz')
    manifest=read(REVIEW/'retained10638/candidate_manifest.json')
    network=ROOT/manifest['sources']['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest()==manifest['sources']['network']['sha256']
    protocol=read(ROOT/manifest['sources']['reference_protocol']['path'])
    routes,exits=replay.geometry(network)
    selected=factor['native_sources']['selected'];events=copy.deepcopy(selected['events'])
    initial=[r for r in cache['rows'] if r[0]==replay.START and r[2] in replay.LOCAL]
    current=replay.observe(replay.raw_frame(initial,replay.START),routes,exits)
    known={e['vehicle'] for e in events}
    missing=[e for e in native['events'] if e['role']=='x10643_exit' and
             replay.START<e['time']<=replay.END and e['vehicle'] not in known]
    assert len(missing)==1 and missing[0]['vehicle']==25422
    mer=missing[0]
    track=sorted([r for r in cache['rows'] if r[1]==mer['vehicle']])
    before=max((r for r in track if r[0]<mer['time']),key=lambda r:r[0])
    after=min((r for r in track if r[0]>mer['time']),key=lambda r:r[0])
    assert before[2]==10643 and after[2]==10634 and after[0]-before[0]==5.
    path=routes[(before[6],before[7])]
    i=path.index(10643)
    assert tuple(path[i:i+5])==(10643,126,10641,71,10634),path
    head=[e for e in native['events'] if e['role']=='head' and e['vehicle']==mer['vehicle']]
    assert len(head)==1 and before[0]<mer['time']<head[0]['time']<after[0]
    obs=replay.observe(replay.raw_frame([before],before[0]),routes,exits)['vehicles'][0]
    assert obs['connector']==10634
    extra=dict(vehicle=mer['vehicle'],visit_label=f"{mer['vehicle']}:visit1",source='off10643',
        entry_lane=mer['lane'],bracket=[before[0],after[0]],destination=obs['connector'],
        unassigned_continuation=replay.unassigned_continuation(obs,routes),order=[-before[4],mer['vehicle']],
        first_local_link=None,first_local_lane=None,first_local_position=None,
        last_outside_link=10643,last_outside_position=before[4],observed_route=before[6:9],
        provenance='MER exit+head and static path prove traversal; no FZP local sample',
        native_off_exit_time=mer['time'],native_head_time=head[0]['time'])
    events.append(extra)
    assert {r[1] for r in initial}.isdisjoint(e['vehicle'] for e in events)
    save('mer_repair_protocol.json',dict(
        reason='Final event coverage QA found25422 exits10643 at2930.27 and crosses71 head2934.48, wholly between5s samples.',
        new_event=extra,max_additional_replays=2,prior_factorial_scope='sampled cohort, incomplete by1known traversal',
        choice='Repair own-selected early/late only; no new grid or full factorial repetition.',
        future_native_input=True,autonomous=False,new_fzp=0,new_native=0))
    program=replay.NativeProgram(read(REVIEW/'local10643_receiver/head_audit.json')['cases']['47selected'])
    results={}
    for timing in ('early','late'):
        r=replay.run(copy.deepcopy(current),network,protocol,events,program,{},timing,'unrestricted_exit',[])
        results[timing]=r;save('selected_mer_complete_'+timing+'.json',r)
        print(timing,'MER complete selected departures',r['departures'],'stock',r['final_n'],flush=True)
    check_production(prior)
    held=read(HERE/'assessment_clock_only.json')['results']
    save('assessment_mer_repair.json',dict(status='completed_mer_coverage_repair',
        native_selected_cohort=dict(initial_n=35,arrivals=len(events),off10643_arrivals=84,
            final_n=38,abnormal_removals=2,normal_out=35+len(events)-38-2,
            head_missing_from_cohort=[],all_off_exit_mer_covered=True),
        native_held_normal_out=212,normal_out_delta=35+len(events)-38-2-212,
        model_delta={timing:results[timing]['departures']-held[timing]['held_clock']['departures']
                     for timing in ('early','late')},results=results,extra_event=extra,
        source_pins=PINS,production_exact=prior['production_exact'],stop_sha256=prior['stop_sha256'],
        new_replays_total=10,invalid_initial_clock_replays=2,new_fzp_total=1,new_native=0,
        limitations=['Other short traversals not seen at heads can still be missed; native balance is the tracked cohort.',
                    'No future observed removal applied to model; cannot count deletion as normal outflow.',
                    'Actual drainage is a conditional input here, not an independent desired-demand scenario.'],
        goal_complete=False))


def observed_queue_reset():
    """A40s diagnosis: propagation error versus service from the actual queue."""
    assert not (HERE/'observed_queue_reset.json').exists()
    prior=read(REVIEW/'urban10643_lateral_completion/completion.json');check_production(prior)
    replay=load_module(REVIEW/'urban10643_conditional/replay.py')
    replay.START,replay.END=3030.1,3070.1
    cache=read(HERE/'selected_native/rows.json.gz')
    manifest=read(REVIEW/'retained10638/candidate_manifest.json')
    network=ROOT/manifest['sources']['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest()==manifest['sources']['network']['sha256']
    protocol=read(ROOT/manifest['sources']['reference_protocol']['path'])
    current_rows=[r for r in cache['rows'] if r[0]==replay.START and r[2] in replay.LOCAL]
    current=replay.observe(replay.raw_frame(current_rows,replay.START),*replay.geometry(network))
    source=read(HERE/'native_arrival_sources.json')['selected']['events']
    events=[e for e in source if replay.START<e['bracket'][1]<=replay.END]
    assert all(e['bracket'][0]>=replay.START for e in events)
    assert {r[1] for r in current_rows}.isdisjoint(e['vehicle'] for e in events)
    clocks=read(REVIEW/'local10643_receiver/head_audit.json')['cases']['47selected']
    program=replay.NativeProgram(clocks)
    native=read(HERE/'native_clock_events.json')['47selected']
    native_heads=Counter(str(e['lane']) for e in native['events'] if e['role']=='head' and
                         replay.START<e['time']<=replay.END)
    save('queue_reset_protocol.json',dict(
        purpose='Reset observed queue/route/position to distinguish450s propagated queue error from instantaneous discharge error.',
        window=[replay.START,replay.END],max_component_replays=2,initial_vehicles=len(current_rows),
        subsequent_arrivals=len(events),future_observation_diagnosis_only=True,
        other_coefficients_and_service_unchanged=True,full_network_forecast=False,
        native_head=dict(native_heads),limit='Model connector exit is2m after native head.'))
    results={}
    for timing in ('early','late'):
        r=replay.run(copy.deepcopy(current),network,protocol,events,program,{},timing,'unrestricted_exit',[])
        results[timing]=r
        print('observed queue reset',timing,'heads',r['head_connector_discharge'],'native',dict(native_heads),flush=True)
    check_production(prior)
    save('observed_queue_reset.json',dict(status='completed_conditional_actual_queue_reset',
        window=[replay.START,replay.END],results=results,native_head=dict(native_heads),
        source_pins=PINS,production_exact=prior['production_exact'],stop_sha256=prior['stop_sha256'],
        new_native=0,new_fzp=0,coefficient_fit=0,autonomous=False,goal_complete=False))


def propagated_queue_observer():
    """Observe the same40s window in the existing445s result; assert parity."""
    assert not (HERE/'propagated_queue.json').exists()
    prior=read(REVIEW/'urban10643_lateral_completion/completion.json');check_production(prior)
    replay=load_module(REVIEW/'urban10643_conditional/replay.py')
    cache=read(HERE/'selected_native/rows.json.gz')
    manifest=read(REVIEW/'retained10638/candidate_manifest.json')
    network=ROOT/manifest['sources']['network']['path']
    protocol=read(ROOT/manifest['sources']['reference_protocol']['path'])
    expected=read(HERE/'assessment_mer_repair.json')
    source=read(HERE/'native_arrival_sources.json')['selected']['events']
    events=source+[expected['extra_event']]
    current=replay.observe(replay.raw_frame([r for r in cache['rows'] if r[0]==replay.START and
        r[2] in replay.LOCAL],replay.START),*replay.geometry(network))
    program=replay.NativeProgram(read(REVIEW/'local10643_receiver/head_audit.json')['cases']['47selected'])
    heads=Counter();snapshot={}
    original=replay.UrbanTransport.step

    def observed_step(model,external,**kwargs):
        t=model.time
        if abs(t-3030.1)<1e-5:
            snapshot['time']=t;snapshot['lanes']={}
            for lane in range(1,6):
                q=model.cells[71,lane,3]
                packets=[dict(label=list(label),mass=n) for label,n in q.q]
                per_dest=Counter()
                for (road,ln,cell),queue in model.cells.items():
                    if road==71 and ln==lane:
                        for label,n in queue.q:
                            per_dest['unknown' if label[0] is None else str(int(label[0]))]+=n
                snapshot['lanes'][str(lane)]=dict(total_stock=sum(per_dest.values()),
                    destinations=dict(per_dest),last_cell_packets=packets)
        result=original(model,external,**kwargs)
        if 3030.1-1e-5<=t<3070.1-1e-5:
            for src,dst,packets in model.last_transfers:
                if src[0]==71 and src[2]==3 and dst[0]=='exit':
                    heads[str(src[1])]+=sum(n for label,n in packets)
        return result

    replay.UrbanTransport.step=observed_step
    try:
        result=replay.run(current,network,protocol,events,program,{},'early','unrestricted_exit',[])
    finally:
        replay.UrbanTransport.step=original
    assert {k:v for k,v in result.items() if k!='wall_sec'} == {
        k:v for k,v in expected['results']['early'].items() if k!='wall_sec'}
    assert snapshot
    check_production(prior)
    reset=read(HERE/'observed_queue_reset.json')
    save('propagated_queue.json',dict(status='completed_observer_exact_parity',
        window=[3030.1,3070.1],head_connector_discharge=dict(heads),
        native_head=reset['native_head'],snapshot=snapshot,
        exact_prior_result_except_wall=True,wall_sec=result['wall_sec'],
        source_pins=PINS,production_exact=prior['production_exact'],stop_sha256=prior['stop_sha256'],
        source_changes=0,future_native_input=True,autonomous=False,
        limitations=['Snapshot is propagated fractional stock, not an observed stopped-queue count.',
                    'Model exits and native heads are separated by approximately2m.']))
    print('same40s propagated',dict(heads),'reset',reset['results']['early']['head_connector_discharge'],
          'native',reset['native_head'],flush=True)


if __name__ == '__main__':
    if '--propagated-queue-observer' in sys.argv:
        propagated_queue_observer()
    elif '--observed-queue-reset' in sys.argv:
        observed_queue_reset()
    elif '--repair-skipped-crossing' in sys.argv:
        repair_skipped_crossing()
    elif '--arrival-factorial' in sys.argv:
        arrival_factorial()
    elif '--extract-selected-cache' in sys.argv:
        extract_selected_cache()
    elif '--repair-clock-budget' in sys.argv:
        repair_clock_budget()
    else:
        main()
