"""Reuse pinned MER chunks for a bounded head-service diagnosis; no native run.

The local replays condition on FUTURE measured connector arrivals and a fixed
uncongested receiving envelope. They isolate the ramp closure, not autonomous
forecast or control gain. No parameter is fitted and no runtime is modified.
"""
from pathlib import Path
import collections
import csv
import hashlib
import json
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary

HERE = Path(__file__).resolve().parent
I = HERE.parent
RAMP = 'RM_C10490'
START, END, HEAD_DCP, ENTRY_DCP = 2700, 3150, 960219, 960272


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arrival_sources():
    """Attribute observed entries to saved initial IDs; validation only."""
    target=HERE/'analysis/head10490_arrival_sources.json'
    assert not target.exists(), 'Preserve completed source audit'
    timing=load(HERE/'analysis/head10490_arrival_timing.json')
    protocol=load(HERE/'protocol.json')
    gate_path=I/'closedloop_recorded2700_init_rm_pair_s47_cell23_sourceaudit_v1/audit.json'
    gate=load(gate_path)
    report=dict(scope='Observed source attribution, not autonomous destination inference',
        arms={},source_sha256={str(Path(__file__)):digest(Path(__file__)),str(gate_path):digest(gate_path)},
        new_native_runs=0,new_forecasts=0,fitted_parameters=0,fzp_scans=0)
    for arm in ('hold','selected'):
        run=(Path(protocol['reuse_native_baseline']['run']) if arm=='hold' else
             Path('D:/VISSIM_runs/20260928_sd31_selected2700_s47/selected'))
        folder=run/f'decisions_sdmpc31_g_2700_{arm}_s47'
        initial_path=folder/'state_002700.json'; initial=load(initial_path)
        initial_by_id={r['veh_no']:r for r in initial['vehicle_records']['records']}
        initial_seen32={i for i,r in initial_by_id.items() if r['link_no']==32}
        report['source_sha256'][str(initial_path)]=digest(initial_path)
        off_times={}; arrivals=[]
        for sec in range(2400,END+1,150):
            path=folder/f'state_{sec:06d}.json'
            raw=load(path);bundle=oc.load_bundle(raw)
            assignment=oc.assign_window(bundle.obs,bundle.mer_rows)
            for dcp in (960225,ENTRY_DCP):assert assignment.tails[dcp]==0
            for event in assignment.entries[960225]:
                off_times.setdefault(event.veh,[]).append(event.t_entry)
            if sec<=START:continue
            window_events=assignment.entries[ENTRY_DCP]
            seen=set()
            for event in window_events:
                assert event.veh not in seen;seen.add(event.veh)
                record=initial_by_id.get(event.veh)
                from_off=any(t<event.t_entry for t in off_times.get(event.veh,()))
                arrivals.append(dict(vehicle=event.veh,entry_sec=event.t_entry,
                    initial_link=record['link_no'] if record else None,
                    initial_position_m=record['position_m'] if record else None,
                    initial_speed_kph=record['speed_kph'] if record else None,
                    off10491_seen_since2250=from_off,
                    seen_on_link32_at_or_after_initial=event.veh in initial_seen32))
            for record in raw['vehicle_records']['records']:
                if record['link_no']==32:initial_seen32.add(record['veh_no'])
            report['source_sha256'][str(path)]=digest(path)
        assert len(arrivals)==timing['arms'][arm]['actual']['arrival']
        windows=[]
        for start in range(START,END,150):
            events=[r for r in arrivals if start<=r['entry_sec']<start+150]
            profiles=timing['arms'][arm]['arrival_profiles_1s']
            windows.append(dict(start_sec=start,actual=len(events),
                predicted=sum(profiles['predicted'][start-START:start-START+150]),
                initial_links=dict(collections.Counter(str(r['initial_link']) for r in events)),
                off10491_recorded=sum(r['off10491_seen_since2250'] for r in events),
                initial_link32_count=sum(r['initial_link']==32 for r in events),
                absent_initial_network=sum(r['initial_link'] is None for r in events)))
        report['arms'][arm]=dict(current_route_capture_present=initial.get('vehicle_routes') is not None,
            current_gate_counts=dict(collections.Counter(str(r['link_no']) for r in initial_by_id.values()
                if r['link_no'] in (32,10778,129,10777,127,10491))),windows=windows,arrivals=arrivals)
    source='in_SC1001_W'
    report['autonomous_gate']=dict(
        parent_release_schedule=gate['storage_release_buffer'][source],
        future_rate_vph=[d[source] for d in gate['forecast_urban_boundary']],
        ramp_shares={m:s['beta'] for m,s in gate['source_specs'].items() if s.get('ramp')},
        current_routes_captured=gate['current_routes'] is not None)
    report['limitations']=[
        'Future IDs and MER crossings classify validation targets only; no route assignment is fed to a model.',
        'Absent from initial complete network means a newly generated vehicle, not a proven source input.',
        'Recorded off10491 passage proves that path; lack of such passage after2250 does not exclude earlier passage.',
        'The source-lane snapshots are150s apart; they do not recover a full trajectory.',
        'Current route observations are absent; exact committed destinations cannot be inferred from future movements for prediction.']
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({arm:row['windows'] for arm,row in report['arms'].items()}))


def arrival_timing(*, timescale=False):
    """Four local input decompositions, same frozen predicted receiving path."""
    import gzip
    from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary
    target = HERE/('analysis/head10490_arrival_timescale.json' if timescale else
                   'analysis/head10490_arrival_timing.json')
    assert not target.exists(), 'Preserve completed decomposition'
    trace_dir = I/'closedloop_recorded2700_select_check_trace10490_rm_pair_s47_cell23_v2'
    original_dir = I/'closedloop_recorded2700_select_check_rm_pair_s47_cell23_v2'
    audit = load(HERE/'analysis/ramp_response_audit.json')
    native = load(HERE/'analysis/head10490_diagnosis.json')
    protocol = load(HERE/'protocol.json')
    report = dict(scope='Conditional cause isolation with frozen model receiving, not autonomous validation',
                  new_native_runs=0,new_full_coupled_forecasts=0,local_replays=8,
                  model_changes=0,fitted_parameters=0,arms={},source_sha256={})
    if timescale:
        report['local_replays'] = 6
    report['source_sha256'][str(Path(__file__))] = digest(Path(__file__))
    for arm, case in (('hold','held_actual'),('selected','selected')):
        path = trace_dir/(case+'_RM_C10490_trace.json.gz')
        with gzip.open(path,'rt',encoding='utf-8') as stream: trace = json.load(stream)
        report['source_sha256'][str(path)] = digest(path)
        previous, repeated = load(original_dir/(case+'.json')), load(trace_dir/(case+'.json'))
        for key in ('ttt_omega_veh_h','tracked_outside_residence_veh_h','ramps','commands'):
            assert previous[key] == repeated[key], (case,key)
        predicted, observed = [0.]*450, [0.]*450
        for row in trace['transfers']:
            if row['target']=='ramp:'+RAMP:
                predicted[int(row['start_sec'])-START] += row['vehicles']
        run = (Path(protocol['reuse_native_baseline']['run']) if arm=='hold' else
               Path('D:/VISSIM_runs/20260928_sd31_selected2700_s47/selected'))
        for sec in range(START+150,END+1,150):
            raw_path = run/f'decisions_sdmpc31_g_2700_{arm}_s47'/f'state_{sec:06d}.json'
            bundle = oc.load_bundle(load(raw_path))
            assignment = oc.assign_window(bundle.obs,bundle.mer_rows)
            assert assignment.tails[ENTRY_DCP]==0
            for event in assignment.entries[ENTRY_DCP]:
                observed[math.floor(event.t_entry)-START] += 1.
            report['source_sha256'][str(raw_path)] = digest(raw_path)
        assert sum(observed)==audit['arms'][arm][RAMP]['actual']['arrival']
        assert abs(sum(predicted)-previous['ramps'][RAMP]['arrival'])<1e-8
        receive={int(r['start_sec']):r['available_veh'] for r in trace['resources']
                 if r['kind']=='physical_ramp_merge_physical_receiving'}
        assert set(receive)==set(range(START,END))
        profiles=dict(predicted=predicted,observed=observed,
            observed_timing_predicted_total=[v*sum(predicted)/sum(observed) for v in observed],
            predicted_timing_observed_total=[v*sum(observed)/sum(predicted) for v in predicted])
        if timescale:
            smooth=[]; within=[]
            for first in range(0,450,150):
                p=predicted[first:first+150]; o=observed[first:first+150]
                assert sum(o)>0
                smooth.extend([sum(o)/150]*150)
                within.extend([v*sum(p)/sum(o) for v in o])
            profiles=dict(predicted=predicted,observed_window_totals_smooth=smooth,
                          predicted_window_totals_observed_within_window=within)
        initial = trace['initial_buffer']
        spec = {k:initial[k] for k in ('connector_id','length_m','head_position_m','lanes',
                'spacing_m','travel_speed_kmh','initial_cohorts','lane_arrival_shares')}
        results = {}
        for label, amounts in profiles.items():
            buf = LaneResolvedRampBoundary(**spec,time_sec=START)
            for t in range(START,END):
                green=int(previous['commands'][(t-START)//150]['meters'][RAMP])
                buf.advance_local_interval(start_sec=t,duration_sec=1,cycle_sec=10,
                    receiving_budget_veh=receive[t],receiving_budget_by_lane_veh=[receive[t]],
                    service_veh=trace['head_service_by_green'][str(green)]*10/3600,
                    mode='GREEN',green_sec=green,request_arrivals_veh=0,allow_partial_cycle=True)
                buf.admit_current(amounts[t-START])
            s=buf.snapshot()
            assert abs(s['conservation_residual_veh'])<1e-8 and not s['outside_component_backlog_veh']
            results[label]=dict(arrival=sum(amounts),head=s['cumulative_head_service_veh'],
                merge=s['cumulative_merge_veh'],final_stock=s['connector_veh'])
        assert abs(results['predicted']['merge']-previous['ramps'][RAMP]['merge'])<1e-8
        assert abs(results['predicted']['final_stock']-previous['ramps'][RAMP]['final_stock'])<1e-8
        expected_head=sum(r['accepted_total_veh'] for r in trace['resources'] if r['kind']=='physical_ramp_head_service')
        assert abs(results['predicted']['head']-expected_head)<1e-8
        report['arms'][arm]=dict(unchanged_autonomous_forecast_verified=True,
            original_local_reproduced=True,actual=native['arms'][arm]['actual'],replays=results,
            arrival_profiles_1s=profiles,receiving_envelope_1s=receive,
            arrival_source='movement:SC1001_W_to_onE')
    report['limitations']=[
        'Native arrival timing is future data used only for diagnosis. No inferred autonomous gain.',
        'Predicted receiving is frozen per arm. Replacing arrivals does not feed back into mainline dynamics.',
        'Scaling arrival profiles separates amount from timing diagnostically; it is not a native demand scenario.',
        'Actual connector entry station is1m downstream; times are assigned to1s steps. All window totals match the boundary audit.',
        'No head-service curve or travel/receiving parameter was changed.']
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v['replays'] for k,v in report['arms'].items()}))


def main():
    target = HERE/'analysis/head10490_diagnosis.json'
    assert not target.exists(), 'Preserve completed diagnosis'
    protocol = load(HERE/'protocol.json')
    audit = load(HERE/'analysis/ramp_response_audit.json')
    summary = load(HERE/'analysis/summary.json')
    assert summary['counterfactual_valid'] and summary['common_start_vehicle_records_exact']
    cfg_path = I/'closedloop9000_d4e2_analysis/local_merge_cell23/candidate_full_config.json'
    cfg = load(cfg_path)
    manifest_path = ROOT/cfg['freeway']['lane_plant']
    manifest = load(manifest_path)
    reference_path = ROOT/manifest['sources']['reference_config']['path']
    profile_path = ROOT/manifest['sources']['port_profile']['path']
    ref, profile = load(reference_path), load(profile_path)
    assert digest(reference_path) == manifest['sources']['reference_config']['sha256']
    assert digest(profile_path) == manifest['sources']['port_profile']['sha256']
    frozen = Path(load(Path('D:/VISSIM_runs/20260928_sd31_selected2700_s47/launch_receipt.json'))['frozen'])
    for filename in ('lane_plant_runtime.py', 'lane_ramp_runtime.py', 'physical_ramp_boundary.py'):
        relative = Path('evaluation/controllers')/filename
        assert digest(ROOT/relative) == digest(frozen/relative), filename
    curve = ref['freeway']['physical_ramp_head_service_veh_per_cycle'][RAMP]
    spacing = load(ROOT/'evaluation/parameters.json')['network']['urban_avg_vehicle_length_m']
    report = dict(scope=__doc__, source_sha256={}, arms={},
                  actual_component_service_veh_per_cycle=curve,
                  top_level_legacy_service_veh_per_cycle=cfg['freeway']['physical_ramp_head_service_veh_per_cycle'][RAMP],
                  model_changes=0, calibration_evaluations=0, new_native_runs=0,
                  full_coupled_forecasts=0, local_conditional_replays=4,
                  fzp_scans=0, runtime_travel_speed_kmh=profile['travel_speed_kmh']['10490'],
                  declared_component_split_travel=ref['freeway']['physical_ramp_travel_speeds'][RAMP])
    for path in (cfg_path, manifest_path, reference_path, profile_path,
                 ROOT/'evaluation/parameters.json', Path(__file__),
                 ROOT/'evaluation/controllers/lane_plant_runtime.py',
                 ROOT/'evaluation/controllers/lane_ramp_runtime.py',
                 ROOT/'evaluation/controllers/physical_ramp_boundary.py'):
        report['source_sha256'][str(path)] = digest(path)
    for arm in ('hold', 'selected'):
        run = (Path(protocol['reuse_native_baseline']['run']) if arm == 'hold' else
               Path('D:/VISSIM_runs/20260928_sd31_selected2700_s47/selected'))
        decisions = run/f'decisions_sdmpc31_g_2700_{arm}_s47'
        initial_path = decisions/f'state_{START:06d}.json'
        initial = load(initial_path)
        report['source_sha256'][str(initial_path)] = digest(initial_path)
        head_events, arrival_events, cycles, frames, greens = [], [], {}, [], {}
        for sec in range(START+150, END+1, 150):
            raw_path = decisions/f'state_{sec:06d}.json'
            raw = load(raw_path)
            bundle = oc.load_bundle(raw)
            assigned = oc.assign_window(bundle.obs, bundle.mer_rows)
            assert not assigned.tails[HEAD_DCP] and not assigned.tails[ENTRY_DCP]
            report['source_sha256'][str(raw_path)] = digest(raw_path)
            for dcp, events in ((HEAD_DCP, head_events), (ENTRY_DCP, arrival_events)):
                events.extend(dict(t=r.t_entry, vehicle=r.veh, speed_kmh=r.v_kmh,
                                   length_m=r.length_m) for r in assigned.entries[dcp])
            action_path = decisions/f'action_{sec-150:06d}.csv'
            report['source_sha256'][str(action_path)] = digest(action_path)
            meter, = (r for r in csv.DictReader(action_path.read_text(encoding='utf-8-sig').splitlines())
                      if r['kind'] == 'ramp_meter' and r['id'] == RAMP)
            green = int(float(meter['green_sec']))
            greens[sec-150] = green
            for t in range(sec-150, sec, 10):
                cycles[t] = dict(start_sec=t, green_sec=green, events=[])
        assert len(head_events) == audit['arms'][arm][RAMP]['actual']['head']
        assert len(arrival_events) == audit['arms'][arm][RAMP]['actual']['arrival']
        for ev in head_events:
            # An event exactly on a cycle boundary needs native step-order
            # classification; fail instead of silently assigning its phase.
            assert abs(ev['t']/10-round(ev['t']/10))*10 > oc.BOUNDARY_EPS_S
            t = math.floor(ev['t']/10)*10
            assert t in cycles
            cycles[t]['events'].append({**ev, 'phase_sec': ev['t']-t})
        detectors, _ = oc.read_detector_csv(initial['obs150']['detector_config']['path'],
                                            initial['obs150']['detector_config']['sha256'])
        detector, = (d for d in detectors if d.dcp_no == HEAD_DCP)
        head = detector.pos
        geometry = json.loads(detector.geometry_assert) if isinstance(detector.geometry_assert, str) else detector.geometry_assert
        length = geometry['link_length_m']
        cohorts = [[v['position_m'], v['speed_kph'], v['lane_no']]
                   for v in initial['vehicle_records']['records'] if int(v['link_no']) == 10490]
        for sec in range(START, END+1, 150):
            raw = load(decisions/f'state_{sec:06d}.json')
            vehicles = [v for v in raw['vehicle_records']['records'] if int(v['link_no']) == 10490]
            frames.append(dict(sec=sec, prehead=sum(v['position_m'] < head for v in vehicles),
                stopped_prehead=sum(v['position_m'] < head and v['speed_kph'] < 5 for v in vehicles),
                posthead=sum(v['position_m'] >= head for v in vehicles)))
        rows = []
        for t, cycle in cycles.items():
            events = cycle['events']
            rows.append({**cycle, 'head_count': len(events),
                'first_passage_phase_sec': events[0]['phase_sec'] if events else None,
                'entry_after_red_count': sum(e['phase_sec'] > cycle['green_sec'] for e in events)})
        windows = []
        for t, green in greens.items():
            part = [r for r in rows if t <= r['start_sec'] < t+150]
            first = [r['first_passage_phase_sec'] for r in part if r['head_count']]
            windows.append(dict(start_sec=t,green_sec=green, head=sum(r['head_count'] for r in part),
                counts_per_cycle=dict(sorted(collections.Counter(r['head_count'] for r in part).items())),
                first_passage_median_sec=statistics.median(first) if first else None,
                entry_after_red=sum(r['entry_after_red_count'] for r in part),
                nominal_cycle_service=curve[str(green)]))
        arrivals = collections.Counter(math.floor(e['t']) for e in arrival_events)
        local = {}
        for mode in ('current_runtime', 'declared_split_travel'):
            spec = dict(connector_id='10490', length_m=length, head_position_m=head, lanes=1,
                spacing_m=spacing, travel_speed_kmh=profile['travel_speed_kmh']['10490'],
                time_sec=START, initial_cohorts=cohorts)
            if mode == 'declared_split_travel':
                speed = ref['freeway']['physical_ramp_travel_speeds'][RAMP]
                spec.update(travel_speed_kmh=speed['upstream_kmh'],posthead_travel_speed_kmh=speed['posthead_kmh'])
            buf = PhysicalRampBoundary(**spec)
            unused = head_total = post_blocked_steps = 0
            for t in range(START, END):
                green = greens[START+(t-START)//150*150]
                receipt = buf.advance_local_interval(start_sec=t,duration_sec=1,cycle_sec=10,
                    receiving_budget_veh=ref['freeway']['physical_ramp_capacity_vph'][RAMP]/3600,
                    service_veh=curve[str(green)], mode='GREEN',green_sec=green,
                    request_arrivals_veh=arrivals[t],allow_partial_cycle=True)
                unused += receipt['head_service_limit_veh']-receipt['head_service_veh']
                head_total += receipt['head_service_veh']
                post_blocked_steps += sum(r.get('posthead_free_before_service_veh',1) <= 1e-8
                                          for r in receipt['local_receipts'])
            snapshot = buf.snapshot()
            assert abs(snapshot['conservation_residual_veh']) < 1e-8
            assert snapshot['outside_component_backlog_veh'] == 0
            local[mode] = dict(head=head_total,merge=snapshot['cumulative_merge_veh'],
                final_stock=snapshot['connector_veh'],unused_head_budget=unused,
                posthead_full_steps=post_blocked_steps,conservation_residual=snapshot['conservation_residual_veh'])
        report['arms'][arm] = dict(windows=windows,cycles=rows,observed_boundary_stocks=frames,
            actual=audit['arms'][arm][RAMP]['actual'],conditional_local=local)
    report['limitations'] = [
        'First passage delay includes approach and waiting; it is not identified startup lost time without green-start queue observations.',
        'Entry after RED is observed detector timing, not a signal-writer failure or proof that a driver violated RED.',
        'The conditional replay uses measured future arrivals; never use it as autonomous validation or gain qualification.',
        'Receiving is fixed at nominal1800veh/h, not reconstructed future freeway supply.',
        'Boundary stocks every150s do not prove within-cycle queue saturation.',
        'Split-travel comparison only checks a declared but uncoupled setting; no adoption or new calibration.',
        'No independent-seed head-service calibration is performed.']
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({arm: {k:v for k,v in data.items() if k not in ('cycles','actual')}
                      for arm,data in report['arms'].items()},ensure_ascii=False))


if __name__ == '__main__':
    if sys.argv[1:] == ['--arrival-timing']:
        arrival_timing()
    elif sys.argv[1:] == ['--arrival-timescale']:
        arrival_timing(timescale=True)
    elif sys.argv[1:] == ['--arrival-sources']:
        arrival_sources()
    else:
        assert not sys.argv[1:]
        main()
