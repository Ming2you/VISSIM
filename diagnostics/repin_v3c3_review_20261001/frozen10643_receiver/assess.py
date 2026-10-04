"""Bounded component diagnosis with frozen downstream space; not a plant forecast."""
import ast
import gzip
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path

from evaluation.controllers.physical_urban_transport import CumulativeLane

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REVIEW = HERE.parent
I = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def replay(trace, initial, speed, events, mode):
    off = trace['offramp_network_diagnostics']
    local = trace['local_receiver_diagnostics']
    start, end = int(trace['start_sec']), int(trace['end_sec'])
    row = off['descriptions']['10643']
    ports = [CumulativeLane(row['storage_capacity_veh']/2, row['length_m'], speed,
             [(v[3], v[4], v[5]) for v in initial if v[1] == 10643 and v[2] == lane],
             start, local['states'][0]['geometry']['wave']) for lane in (1, 2)]
    receiving, recorded, arrivals = {}, {}, defaultdict(lambda: [0., 0.])
    for r in local['resources']:
        if r['kind'] != 'lane_urban_receiving':
            continue
        key = ast.literal_eval(r['resource'])
        if key[0] != 126 or key[2] != len(local['states'][0]['geometry']['edges']['126'])-2:
            continue
        g = key[1]-1
        t = int(r['start_sec'])
        own = r['accepted_by_source_veh'].get(str(('external', 'off:'+str(g))), 0.)
        other = r['accepted_total_veh']-own
        receiving[t, g] = max(0., r['available_veh']-(0. if mode == 'native_all_frozen_space' else other))
        recorded[t, g] = own
    assert len(receiving) == 2*(end-start)
    if mode == 'baseline':
        for r in off['resources']:
            if r['kind'] == 'physical_offramp_lane_receiving' and r['resource'].startswith('10643:'):
                arrivals[int(r['start_sec'])][int(r['resource'].split(':')[1])] += r['accepted_total_veh']
    else:
        assert mode in ('native_residual_space', 'native_all_frozen_space')
        for event in events:
            t = math.floor(event['time_sec'])
            assert start <= t < end
            arrivals[t][event['lane']-1] += 1.
    backlog, peak, snapshots = [0., 0.], [p.stock for p in ports], []
    max_baseline_error = 0.
    for t in range(start, end):
        for g, port in enumerate(ports):
            served = port.release(t, 1, receiving[t, g]*3600.)
            if mode == 'baseline':
                max_baseline_error = max(max_baseline_error, abs(served-recorded[t, g]))
            backlog[g] += arrivals[t][g]
            accepted = min(backlog[g], port.receiving(1.))
            port.accept(t+1, accepted)
            backlog[g] -= accepted
            peak[g] = max(peak[g], port.stock)
        if (t+1-start) % 150 == 0:
            snapshots.append(dict(time_sec=t+1, stock=[p.stock for p in ports],
                admitted=[p.admitted for p in ports], departed=[p.departed for p in ports],
                external_backlog=list(backlog)))
    requested = [math.fsum(a[g] for a in arrivals.values()) for g in (0, 1)]
    residual = math.fsum(p.initial+requested[g]-p.departed-p.stock-backlog[g]
                         for g, p in enumerate(ports))
    assert abs(residual) < 1e-8
    if mode == 'baseline':
        assert max_baseline_error < 1e-8, max_baseline_error
        assert max(backlog) < 1e-8
        for actual, saved in zip(snapshots, local['states'][1:]):
            for g, p in enumerate(saved['off_lanes']):
                for key in ('stock', 'admitted', 'departed'):
                    assert abs(actual[key][g]-p[key]) < 1e-8, (key, g, actual, p)
    return dict(mode=mode, requested_by_lane=requested, snapshots=snapshots,
        drain_total=sum(p.departed for p in ports), final_stock=sum(p.stock for p in ports),
        final_external_backlog=backlog, peak_stock_by_lane=peak,
        frozen_space_by_lane=[sum(receiving[t,g] for t in range(start,end)) for g in (0,1)],
        balance_residual=residual, max_baseline_per_step_error=max_baseline_error,
        conditional_only=True, native_future_entries=mode!='baseline',
        downstream_feedback_frozen=True, full_network_TTT_computed=False)


def main():
    assert not (HERE/'assessment.json').exists()
    protocol = read(HERE/'protocol.json')
    for p, h in protocol['production_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h, p
    metadata = read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    cohorts = read(REVIEW/'entry10643/native_cohorts.json')
    manifest = read(REVIEW/'retained10638/candidate_manifest.json')
    profile = read(ROOT/manifest['sources']['port_profile']['path'])
    assert PINS[str(ROOT/manifest['sources']['port_profile']['path'])] == manifest['sources']['port_profile']['sha256']
    cases = {}
    start = time.perf_counter()
    for arm, key in [('hold','held_actual'), ('selected','selected')]:
        trace = read(I/'closedloop_recorded2700_select_check_trace10681_entry10643'/(key+'_RM_C10681_trace.json.gz'))
        samples = {}
        for text, pin in metadata['input_sha256'].items():
            path = Path(text)
            if arm not in path.parts:
                continue
            raw = read(path)
            assert PINS[str(path)] == pin
            t = int(raw['sim_sec'])
            frame = read(Path(raw['lane_plant_observation']['directory'])/f'frame_{t:06d}.json')
            samples[t] = frame['vehicles']
        assert sorted(samples) == [2700,2850,3000,3150]
        events = cohorts['cases'][arm]['witnesses']
        initial = samples[2700]
        native_stocks = {t:[sum(v[1]==10643 and v[2]==g for v in frame) for g in (1,2)]
                         for t,frame in samples.items()}
        native_entry = [sum(e['lane']==g for e in events) for g in (1,2)]
        net_lane_out = [native_stocks[2700][g]+native_entry[g]-native_stocks[3150][g] for g in (0,1)]
        outcomes = {mode:replay(trace,initial,profile['travel_speed_kmh']['10643'],events,mode)
                    for mode in protocol['modes']}
        cases[arm] = dict(native_entry_by_lane=native_entry,native_stock_by_lane=native_stocks,
            native_drain_total=sum(net_lane_out),
            native_drain_plus_net_lateral_outflow_by_lane=net_lane_out,
            cases=outcomes)
    cache = read(REVIEW/'lane10643_native/rows.json.gz')
    previous, changes, departures = {}, [], []
    for row in cache['rows']:
        if not 2700 <= row[0] <= 3150.1:
            continue
        old = previous.get(row[1])
        if old and row[0]-old[0] < 5.0001 and old[2]==10643:
            if row[2]==10643 and old[3]!=row[3]:
                changes.append(dict(vehicle=row[1],from_sec=old[0],to_sec=row[0],from_lane=old[3],to_lane=row[3]))
            elif row[2]!=10643:
                departures.append(dict(vehicle=row[1],from_sec=old[0],to_sec=row[0],last_off_lane=old[3],next_link=row[2],next_lane=row[3]))
        previous[row[1]]=row
    assert len(cases)*len(protocol['modes']) == protocol['max_component_replays'] == 6
    for p, h in protocol['production_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h
    result = dict(status='completed_frozen_receiver_diagnosis_not_gain_qualified',
        previous_goal_turn='progress',cases=cases,component_replays=6,wall_sec=time.perf_counter()-start,
        cached_hold_lane_changes=changes,cached_hold_departure_pairs=departures,
        full_forecasts=0,new_native=0,new_fzp_scan=0,fit=0,production_changed=False,source_pins=PINS,
        limitations=[
            'Actual1m entry events binned to1s are future truth used only in this component diagnosis.',
            'Fluid receiving can postpone point-vehicle arrivals; all unaccepted demand remains in explicit external backlog.',
            'Per-lane native balance includes net lateral transfers; it is not a direct outlet count.',
            'Native5s cached lane transitions omit unobserved intermediate changes and are not exact crossing planes.',
            'The all-space variant withholds original background vehicles and freezes original receiving history; it is neither feasible full-network control nor a global capacity bound.',
            'No autonomous ranking, TTT gain or coefficient qualification follows from these conditional replays.'])
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for arm,row in cases.items():
        print(arm,'native',row['native_drain_total'],row['native_stock_by_lane']['3150'] if '3150' in row['native_stock_by_lane'] else row['native_stock_by_lane'][3150])
        for mode,case in row['cases'].items():
            print(mode,case['drain_total'],case['final_stock'],case['final_external_backlog'],case['frozen_space_by_lane'])
    print('COMPLETE',result['wall_sec'], 'cached_lane_changes',len(changes),'departure_pairs',len(departures))


if __name__ == '__main__':
    main()
