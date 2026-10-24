"""Replay physical path joins and topology repair on two actual snapshots."""
from __future__ import annotations
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from diagnostics.probe_model_area_integration import build_projected, adapter
from diagnostics.probe_control_area_movement_join import accepted_movements
from evaluation.controllers.control_area_join import build_movement_join, route_contract
from evaluation.controllers.control_area_objective import model_stock_values
from evaluation.controllers.physical_movement_routes import configure_topology_repair, extend_join, build_input_contract
from src.models.state import TrafficState, ControlAction
from src.models.demand import DemandStep

EVIDENCE = 'diagnostics/physical_movement_routes_ver2.json'


def case(run, time):
    base = ROOT / 'evaluation/runs' / run / ('decisions_' + run)
    previous = base / ('action_000001.json' if time == 900 else 'action_003150.json')
    cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(
        ROOT / 'evaluation/configs/n21_n7_20260908.json', base / f'state_{time:06d}.json', previous)
    membership = json.loads((ROOT / 'diagnostics/control_area_membership.json').read_text(encoding='utf-8'))
    turns = json.loads((ROOT / 'outputs/pn_boundary_turns_v2_20260907.json').read_text(encoding='utf-8'))
    tree = ET.parse(ROOT / membership['network']['path']).getroot()
    successors = defaultdict(list)
    for link in tree.findall('./links/link'):
        a, b = link.find('fromLinkEndPt'), link.find('toLinkEndPt')
        if a is not None:
            successors[a.get('lane').split()[0]].append((link.get('no'), b.get('lane').split()[0]))
    before = build_movement_join(cfg, detectors, turns, membership, physical_successors=successors)
    joined_only = extend_join(before, cfg, detectors, membership, EVIDENCE)
    candidate_cfg, candidate_tuning = copy.deepcopy(cfg), copy.deepcopy(tuning)
    candidate_tuning.setdefault('urban', {}).setdefault('movements', {})['physical_route_topology'] = EVIDENCE
    candidate_detectors, repair_metadata = configure_topology_repair(
        candidate_cfg, detectors, candidate_tuning, state_json=raw)
    calibration = adapter.load_optional_json(str(ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration = adapter.deep_update(dict(calibration), tuning.get('calibration_override', {}))
    candidate_state = adapter.traffic_state_from_vissim(
        raw, candidate_cfg, TrafficState, candidate_detectors, calibration, physical_projection_input=None)
    final = extend_join(build_movement_join(candidate_cfg, candidate_detectors, turns, membership,
        physical_successors=successors), candidate_cfg, candidate_detectors, membership, EVIDENCE)
    control = adapter.control_from_json(previous, cfg, ControlAction)
    demand = adapter.demand_from_state(raw, cfg, DemandStep, 1)[0]
    old_flow = accepted_movements(state, cfg, control, demand)
    new_demand = adapter.demand_from_state(raw, candidate_cfg, DemandStep, 1)[0]
    new_flow = accepted_movements(candidate_state, candidate_cfg, control, new_demand)
    def unresolved(flow, join):
        return {key: value for key, value in flow.items()
                if join['by_movement'][key]['status'] not in ('unique', 'same_transition')}
    old_stocks = model_stock_values(state, cfg.network,
        freeway_vehicle_counts=adapter._freeway_vehicle_count_by_link(state, cfg))
    new_stocks = model_stock_values(candidate_state, candidate_cfg.network,
        freeway_vehicle_counts=adapter._freeway_vehicle_count_by_link(candidate_state, candidate_cfg))
    changes = {key: {'before': old_stocks.get(key, 0), 'after': new_stocks.get(key, 0)}
               for key in old_stocks.keys() | new_stocks.keys()
               if old_stocks.get(key, 0) != new_stocks.get(key, 0)}
    report = {'run': run, 'time_sec': time, 'urban_step_sec': cfg.simulation.T_u_sec,
        'unresolved_before': unresolved(old_flow, before),
        'unresolved_after_path_join_only': unresolved(old_flow, joined_only),
        'unresolved_after_topology_repair': unresolved(new_flow, final),
        'accepted_before_veh': sum(old_flow.values()), 'accepted_after_veh': sum(new_flow.values()),
        'model_stock_before': sum(old_stocks.values()), 'model_stock_after': sum(new_stocks.values()),
        'model_stock_delta': sum(new_stocks.values()) - sum(old_stocks.values()),
        'projection_changes': changes, 'repair_metadata': repair_metadata, 'join_counts': final['counts'],
        'limits': 'One 5sec model step under the actual prior action, not a closed-loop performance result. Unmatched inactive movements remain coverage errors if later positive.'}
    input_contract = build_input_contract(candidate_cfg, candidate_detectors, membership,
        'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv')
    return report, final, input_contract, (cfg, state, detectors, tuning, raw, candidate_cfg, candidate_state, candidate_detectors)


def main():
    reports = []
    for run, time in [('codex_nc_s13_6056c94_20260909_retry', 900), ('codex_n7_s13_6056c94_20260909', 3300)]:
        report, join, inputs, _ = case(run, time)
        reports.append(report)
    (ROOT / 'diagnostics/physical_movement_route_replay.json').write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding='utf-8')
    (ROOT / 'diagnostics/control_area_movement_join_physical_routes.json').write_text(json.dumps(join, indent=2, ensure_ascii=False), encoding='utf-8')
    contract = route_contract(join)
    contract.update(inputs['routes'])
    (ROOT / 'diagnostics/control_area_route_contract_physical_routes.json').write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding='utf-8')
    (ROOT / 'diagnostics/control_area_input_contract.json').write_text(json.dumps(inputs, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps([{key: row[key] for key in ['time_sec', 'unresolved_before', 'unresolved_after_path_join_only',
        'unresolved_after_topology_repair', 'model_stock_delta', 'join_counts']} for row in reports], indent=2))


if __name__ == '__main__':
    main()
