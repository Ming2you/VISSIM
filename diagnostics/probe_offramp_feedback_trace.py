"""Read-only 10-second accepted-flow trace; no altered equation or parameter."""
import argparse
import csv
import hashlib
import inspect
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics'), str(ROOT / 'vendor/NumSim-mine')]


def geometry():
    root = ET.parse(ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx').getroot()
    spacing = json.loads((ROOT / 'evaluation/parameters.json').read_text(encoding='utf-8'))['network']['urban_avg_vehicle_length_m']
    result = {}
    for key in ('10682', '10643', '121'):
        node = root.find(f'./links/link[@no="{key}"]')
        points = [(float(p.get('x')), float(p.get('y')), float(p.get('zOffset', 0)))
                  for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
        length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
        lanes = len(node.findall('./lanes/lane'))
        result[key] = {'length_m': length, 'lanes': lanes,
                       'existing_spacing_m': spacing, 'reference_geometry_capacity_veh': length * lanes / spacing}
    return result


def run(config_path, state_path, previous_path, action_path, physical_path):
    with physical_path.open(encoding='utf-8-sig', newline='') as stream:
        physical = {(int(row['sim_sec']), row['link']): row for row in csv.DictReader(stream)
                    if row['link'] in ('10682', '10643', '121')}
    output = {'physical_geometry_reference_only': geometry(), 'traces': [],
        'method': 'Installed canonical initialization with explicit previous action, replay action, and same-snapshot forecast. sys.settrace observes selected local values at the existing vehicle conservation statement; does not change execution.',
        'limitations': ['Model SC1004_W_out is a shared receiver, not a separately simulated10682 branch.',
                       'Physical observations are emitted only at exact logged times; missing samples remain null.',
                       'Reference geometric capacity uses existing vehicle spacing and is not a calibrated or newly installed model capacity.']}
    from probe_model_area_integration import adapter, build_projected
    from evaluation.controllers import area_freeway_accounting as accounted, area_runtime
    from src.models import metanet
    from src.models.demand import DemandStep
    from src.models.state import ControlAction
    from src.simulation import coupling
    for time in (int(json.loads(state_path.read_text(encoding='utf-8'))['sim_sec']),):
        cfg, state, detectors, tuning, raw, _, _ = build_projected(config_path, state_path, previous_path, fixture_inputs=False)
        control = adapter.control_from_json(action_path, cfg, ControlAction)
        calibration = adapter.load_optional_json(str(ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
        calibration = adapter.deep_update(dict(calibration), tuning.get('calibration_override', {}))
        demand = adapter.demand_from_state(raw, cfg, DemandStep, 1, calibration, detectors)
        net = cfg.network
        signal = net.off_ramp_storage_link['OR_F_E']
        direct = net.offramp_direct_tail_by_offramp['OR_F_E']
        specs = getattr(net, 'landing_storage_spec', {})
        trace = {'start_sec': time, 'signal_storage': signal, 'direct_shared_receiver': direct,
            'direct_share': net.offramp_direct_share_by_offramp['OR_F_E'],
            'off_ramp_segment': net.off_ramp_segment_index['OR_F_E'],
            'landing_storage_spec': specs,
            'capacity_drop': vars(cfg.freeway_offramp_capacity_drop),
            'initial_physical_projection': {link: {'count': raw['vehicle_records']['full_network_link_counts'].get(link, 0),
                'model_assignment': state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'].get(link, {})}
                for link in ('10682', '10643', '121')}, 'steps': []}
        original_fw, original_lanes = coupling.freeway_substep, metanet.effective_lane_profile
        active = {}
        source, first_line = inspect.getsourcelines(accounted._freeway_substep_events)
        capture_line = first_line + next(i for i, line in enumerate(source) if 'vehicle_new = max(0.0, vehicle_raw)' in line)

        def observe_frame(frame, event, arg):
            if frame.f_code is not accounted._freeway_substep_events.__code__:
                return None
            if event == 'line' and frame.f_lineno == capture_line:
                v = frame.f_locals
                if v['link'] == 'FW_E' and v['i'] == 8:
                    active['selected_E8'] = {key: float(v[key]) for key in
                        ('rho', 'q_in', 'q_out', 'normal_off_total', 'effective_off_total', 'vehicle_raw')}
                    active['selected_E8'].update({'q_sending_veh_h': v['q_values'][8],
                        'mainline_sending_veh_h': v['mainline_sending'][8],
                        'actual_mainline_outflow_veh_h': v['q_inter'][8],
                        'next_cell_receiving_for_mainline_veh_h': v['receiving_for_mainline'][9],
                        'effective_lanes': v['lanes_now'][8],
                        'boundary_speed_cap': v['boundary_speed_cap']})
            return observe_frame

        def lane_trace(*args, **kwargs):
            profile, diag = original_lanes(*args, **kwargs)
            if active:
                active['effective_lane_diagnostics'] = dict(diag)
            return profile, diag

        def storage_snapshot(s):
            return {key: {'capacity_veh': net.urban_link_storage_veh[key],
                          'available_veh': s.urban_link_storage[key],
                          'occupancy_veh': net.urban_link_storage_veh[key] - s.urban_link_storage[key]}
                    for key in (signal, direct)}

        def traced_fw(*args, **kwargs):
            active.clear()
            elapsed = (len(trace['steps']) + 1) * cfg.simulation.T_f_sec
            active.update({'elapsed_sec': elapsed, 'before_freeway_after_urban': storage_snapshot(args[0]),
                'receiving_cap_veh_h': kwargs['offramp_capacity_veh_h']['OR_F_E'],
                'actual_R_F_E_release_veh_h': kwargs['ramp_release_veh_h'].get('R_F_E', 0),
                'physical_observation_at_interval_end': {key: physical.get((int(time + elapsed), key)) for key in ('10682', '10643', '121')}})
            previous_trace = sys.gettrace()
            try:
                sys.settrace(observe_frame)
                result = original_fw(*args, **kwargs)
            finally:
                sys.settrace(previous_trace)
            diag = result[1]
            active['actual_offflow_veh_h'] = diag['offramp_flow_OR_F_E']
            active['blocked_offflow_veh_h'] = diag['offramp_blocked_flow_OR_F_E']
            active['speed_E8_end_kph'] = args[0].freeway_speed['FW_E'][8]
            active['density_E8_end'] = args[0].freeway_density['FW_E'][8]
            trace['steps'].append(dict(active))
            active.clear()
            return result

        from src.controllers.rollout_endpoint import evaluate_price_point, ObjectiveSpec
        with patch.object(coupling, 'freeway_substep', traced_fw), \
             patch.object(metanet, 'effective_lane_profile', lane_trace):
            result = evaluate_price_point(state, control, demand, [], ObjectiveSpec(cfg, depth_override=1, box_walk=False, score_mode='raw'))
        assert len(trace['steps']) == 15
        assert all('selected_E8' in step for step in trace['steps'])
        result.states[-1]._control_area_ledger.assert_stocks(area_runtime.model_inventory(result.states[-1], cfg))
        trace['final_storage'] = storage_snapshot(result.states[-1])
        output['traces'].append(trace)
        print(json.dumps({'start_sec': time, 'signal': signal, 'direct': direct,
            'initial_physical': trace['initial_physical_projection'], 'first': trace['steps'][0], 'last': trace['steps'][-1]}), flush=True)
    output['source_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (config_path, state_path, previous_path, action_path, physical_path, Path(accounted.__file__), Path(adapter.__file__))}
    output['previous_action'] = str(previous_path)
    output['replay_action'] = str(action_path)
    output['implementation'] = 'installed configure_runtime and endpoint; observation wrappers call originals unchanged'
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('config', 'snapshot', 'previous', 'action', 'physical', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Choose a new production output; historical evidence is preserved')
    output = run(args.config.resolve(), args.snapshot.resolve(), args.previous.resolve(),
        args.action.resolve(), args.physical.resolve())
    args.output.write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
