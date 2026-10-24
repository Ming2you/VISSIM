"""One canonical held150s endpoint, with current route/ordering evidence only."""
import argparse
from collections import Counter
import copy
import hashlib
import inspect
import json
from pathlib import Path
import pickle
import sys
import time
from unittest.mock import patch

from diagnostics.probe_model_area_integration import ROOT, adapter, build_projected, replay_provenance
from evaluation.controllers import area_freeway_accounting as freeway, area_runtime, urban_flow_accounting as urban
from evaluation.controllers.projection_support import complete_records
from evaluation.controllers.vehicle_routes import complete_vehicle_routes
from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point
from src.models.demand import DemandStep
from src.models.state import ControlAction
from src.simulation import coupling


def route_key(route):
    return (f"{route['route_decision_no']}:{route['route_no']}"
            if route['route_decision_type'] == 'STATIC' else 'unresolved')


def current_partition(raw, mapping, evidence):
    records = complete_records(raw)
    routes = complete_vehicle_routes(raw, required=True)
    chain = mapping['freeway_model_links']['FW_E']
    offset = dict(zip(chain['chain_links'], chain['chain_offsets_m']))[2]
    low, boundary, high = chain['segment_bounds_m'][8:11]
    gate = evidence['nodes']['10682']['chain_m']
    signal_gate = evidence['nodes']['10643']['chain_m']
    by_zone, ids = {}, []
    for row in records:
        link, pos = row['link_no'], row['position_m']
        if link == 2 and low <= pos + offset < high:
            x = pos + offset
            zone = ('E8_before_10643' if x <= signal_gate else 'E8_after_10643') if x < boundary else (
                    'E9_before_10682' if x <= gate else 'E9_after_10682')
        elif link in (10639, 10681, 10682, 10643):
            zone = str(link)
            x = None
        else:
            continue
        tag = route_key(routes[row['veh_no']])
        by_zone.setdefault(zone, Counter())[tag] += 1
        ids.append({'veh_no': row['veh_no'], 'zone': zone, 'lane': row['lane_no'],
                    'route': tag, 'chain_m': x, 'position_m': pos, 'speed_kph': row['speed_kph']})
    cells = {str(i): Counter() for i in (8, 9)}
    for zone, counts in by_zone.items():
        if zone.startswith('E8_'):
            cells['8'].update(counts)
        elif zone.startswith('E9_'):
            cells['9'].update(counts)
    return {'zone_route_counts': by_zone, 'cell_route_counts': cells, 'records': ids}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--start', type=int, choices=(1200, 3300), required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'diagnostics') or output.exists():
        raise ValueError('Choose a new output file under diagnostics')
    run = (ROOT / 'evaluation/runs' / args.run).resolve()
    if run.parent != (ROOT / 'evaluation/runs').resolve():
        raise ValueError('Run must be a direct child of evaluation/runs')
    dec = run / ('decisions_' + args.run)
    state_path, action_path, previous_path = [dec / f'{kind}_{sec:06d}.json' for kind, sec in (
        ('state', args.start), ('action', args.start), ('action', args.start-150))]
    evidence_path = ROOT / 'diagnostics/e8_ordered_gate_observability.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    for path in ('network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',
                 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'):
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == evidence['source_sha256'][path]
    started = time.perf_counter()
    cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(
        args.config.resolve(), state_path, previous_path, fixture_inputs=False)
    assert raw['sim_sec'] == args.start and cfg.simulation.T_c_sec == 150
    partition = current_partition(raw, mapping, evidence)
    counts = freeway.continuity_vehicle_counts(state, cfg)['FW_E']
    for cell in (8, 9):
        assert abs(counts[cell] - sum(partition['cell_route_counts'][str(cell)].values())) < 1e-7
    action = adapter.control_from_json(action_path, cfg, ControlAction)
    action_json = json.loads(action_path.read_text(encoding='utf-8'))
    control_keys = ('green_times', 'offsets', 'vsl', 'ramp_metering')
    assert all(action_json[k] == getattr(action, k) for k in control_keys)
    calibration = adapter.load_optional_json(str(ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration = adapter.deep_update(dict(calibration), tuning.get('calibration_override', {}))
    forecast = adapter.demand_from_state(raw, cfg, DemandStep, 1, calibration, detectors)
    input_pickle = pickle.dumps((cfg, state, action, forecast))
    before = replay_provenance(tuning, args.config.resolve(), state_path, action_path, previous_path, evidence_path, Path(__file__))
    expected = {k: copy.deepcopy(getattr(action, k)) for k in control_keys}
    rows, schedules, steps = [], [], []
    source, first_line = inspect.getsourcelines(freeway._freeway_substep_events)
    capture_line = first_line + next(i for i, line in enumerate(source) if 'vehicle_new = max(0.0, vehicle_raw)' in line)
    def local_trace(frame, event, arg):
        v = frame.f_locals
        if frame.f_code is freeway._freeway_substep_events.__code__:
            if event == 'line' and frame.f_lineno == capture_line and v['link'] == 'FW_E' and v['i'] in (8, 9):
                i = v['i']
                rows.append({'elapsed_sec': (len(rows)//2+1)*cfg.simulation.T_f_sec, 'cell': i,
                    'initial_veh': v['vehicles'][i], 'raw_next_veh': v['vehicle_raw'],
                    'gross_q_vph': v['q_values'][i], 'speed_kph': v['speeds'][i],
                    'mainline_sending_vph': v['mainline_sending'][i], 'q_inter_out_vph': v['q_inter'][i],
                    'receiving_vph': v['receiving'][i], 'receiving_after_merge_vph': v['receiving_for_mainline'][i],
                    'off_groups': v['offramps_by_segment'].get(i, []),
                    'normal_off_vph': v['normal_off_total'], 'accepted_off_vph': v['effective_off_total'],
                    'merge_R_FE_vph': v['ramp_release']['R_F_E'], 'cell_merge_vph': v['ramp_in_by_link']['FW_E'][i],
                    'q_in_vph': v['q_in'], 'q_out_vph': v['q_out']})
        elif event == 'return' and v['off_ramp'] == 'OR_F_E':
            schedules.append({'urban_step': v['urban_step_index'], 'group_veh': v['vehicles'],
                'direct_share': v['share'], 'direct_receiver': v['target'],
                'direct_accepted_veh': v['direct_accepted'], 'direct_rejected_veh': v['direct_rejected'],
                'signal_accepted_veh': v['accepted'], 'signal_rejected_veh': v['rejected']})
        return local_trace
    def dispatch(frame, event, arg):
        if frame.f_code in (freeway._freeway_substep_events.__code__, urban.schedule_offramp_arrivals_accounted.__code__):
            return local_trace
        return None
    original = coupling.freeway_substep
    def observed_step(*pos, **kw):
        assert all(getattr(pos[1], k) == expected[k] for k in control_keys), 'Held command changed'
        result = original(*pos, **kw)
        steps.append(dict(result[1]))
        return result
    old_trace = sys.gettrace()
    try:
        sys.settrace(dispatch)
        with patch.object(coupling, 'freeway_substep', observed_step):
            endpoint = evaluate_price_point(state, action, forecast, [], ObjectiveSpec(cfg, depth_override=1, box_walk=False, score_mode='raw'))
    finally:
        sys.settrace(old_trace)
    assert not endpoint.aborted and len(steps) == len(schedules) == 15 and len(rows) == 30
    last = endpoint.states[-1]
    last._control_area_ledger.assert_stocks(area_runtime.model_inventory(last, cfg))
    assert input_pickle == pickle.dumps((cfg, state, action, forecast))
    assert all(abs(r['raw_next_veh'] - r['initial_veh'] - cfg.simulation.T_f_h*(r['q_in_vph']-r['q_out_vph'])) < 1e-7 for r in rows)
    assert all(r['cell_merge_vph'] == (0. if r['cell']==8 else r['merge_R_FE_vph']) for r in rows)
    assert all(r['accepted_off_vph']==0. for r in rows if r['cell']==9)
    assert all(abs(s['group_veh']-s['direct_accepted_veh']-s['signal_accepted_veh'])<1e-7 for s in schedules)
    changes = [p for p, sha in before.items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest()!=sha]
    assert not changes
    assignment = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    # This attribution is algebra under the scalar cell's common speed, NOT a
    # tagged trajectory nor an assertion of which real ID the model removes.
    first = rows[0]
    arithmetic = {tag: {'current_veh': n,
        'proportional_first10s_group_off_veh': n/first['initial_veh']*first['accepted_off_vph']*cfg.simulation.T_f_h,
        'proportional_first10s_signal_veh': n/first['initial_veh']*schedules[0]['signal_accepted_veh'],
        'proportional_first10s_direct_veh': n/first['initial_veh']*schedules[0]['direct_accepted_veh']}
        for tag, n in partition['cell_route_counts']['8'].items()}
    history = json.loads((run/'area_candidate_source_manifest.json').read_text(encoding='utf-8'))
    differences = {p: {'executed': h, 'current': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()}
        for p,h in history['source_sha256'].items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest()!=h}
    report = {'schema':'e8-route-flow-assignment/v1', 'start_sec': args.start, 'elapsed_wall_sec': time.perf_counter()-started,
        'scope':'Current production runtime with the recorded source-run tuning/action; one held150s endpoint. Only current raw route/vehicle data read; no future truth, parameter override, MPC or VISSIM.',
        'executed_source_differences': differences, 'source_sha256': before, 'source_changes': changes,
        'initial_cfg_state_action_forecast_unchanged': True, 'held_control_exact_all_15_steps': True,
        'stock_closure': True, 'current_partition': partition,
        'model': {'off_ratio': cfg.network.off_ramp_split_ratio['OR_F_E'],
            'direct_share': cfg.network.offramp_direct_share_by_offramp['OR_F_E'],
            'off_cell': cfg.network.off_ramp_segment_index['OR_F_E'],
            'merge_cell': cfg.network.ramp_merge_segment_index['R_F_E'],
            'signal_receiver': cfg.network.off_ramp_storage_link['OR_F_E'],
            'direct_receiver': cfg.network.offramp_direct_tail_by_offramp['OR_F_E'],
            'initial_R_FE_queue': state.ramp_queue['R_F_E'],
            'physical_assignments': {k:assignment.get(k,{}) for k in ('10639','10681','10682','10643','121')},
            'FW_E8_final_speed': last.freeway_speed['FW_E'][8], 'FW_E9_final_speed':last.freeway_speed['FW_E'][9]},
        'first10s_common_speed_proportional_attribution_only': arithmetic,
        'attribution_limit':'The prediction has no FW route/lane subset state or per-ID receipts. These proportions expose the collapsed scalar operator, not observed or identifiable ID misrouting. No actual double-counted vehicle is asserted.',
        'totals_veh': {'FE_requested':sum((s['offramp_flow_OR_F_E']+s['offramp_blocked_flow_OR_F_E'])*cfg.simulation.T_f_h for s in steps),
            'FE_accepted':sum(s['group_veh'] for s in schedules), 'FE_direct':sum(s['direct_accepted_veh'] for s in schedules),
            'FE_signal':sum(s['signal_accepted_veh'] for s in schedules),
            'R_FE_merged_into_E9':sum(r['cell_merge_vph']*cfg.simulation.T_f_h for r in rows),
            'E8_to_E9':sum(r['q_inter_out_vph']*cfg.simulation.T_f_h for r in rows if r['cell']==8),
            'E9_to_E10':sum(r['q_inter_out_vph']*cfg.simulation.T_f_h for r in rows if r['cell']==9)},
        'freeway_cells':rows, 'offramp_schedule':schedules}
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('start_sec','elapsed_wall_sec','totals_veh','source_changes')},indent=2))


if __name__=='__main__':
    main()
