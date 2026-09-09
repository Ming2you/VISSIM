"""Source geometry, observed connector queues, and actual model ramp placement."""
from __future__ import annotations
import argparse
import bisect
import csv
import hashlib
import inspect
import json
from pathlib import Path
from statistics import mean
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "diagnostics"), str(ROOT / "vendor/NumSim-mine")]


def geometry_and_observations(mapping_path, network_path, snapshots):
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    network = ET.parse(network_path).getroot()
    chain = mapping["freeway_model_links"]["FW_E"]
    offset = dict(zip(chain["chain_links"], chain["chain_offsets_m"]))
    topology = mapping["model_topology_overrides"]
    positions = []
    for connector, role, group in (("10643", "diverge", "OR_F_E"), ("10639", "merge", "R_F_E"),
                                    ("10682", "diverge", "OR_F_E"), ("10681", "merge", "R_F_E")):
        node = network.find(f'./links/link[@no="{connector}"]')
        endpoint = node.find("fromLinkEndPt" if role == "diverge" else "toLinkEndPt")
        physical_link, first_lane = [int(x) for x in endpoint.get("lane").split()]
        position = offset[physical_link] + float(endpoint.get("pos"))
        idx = bisect.bisect_right(chain["segment_bounds_m"], position) - 1
        modeled = topology["off_ramp_segment_index" if role == "diverge" else "ramp_merge_segment_index"][group]
        positions.append({"connector": connector, "role": role, "model_group": group,
                          "physical_chain_pos_m": position, "physical_cell": idx, "modeled_cell": modeled,
                          "physical_mainline_link": physical_link, "first_lane": first_lane,
                          "connector_lane_count": len(node.findall("./lanes/lane"))})
    lengths = {}
    for connector in ("10682", "10643", "121"):
        node = network.find(f'./links/link[@no="{connector}"]')
        points = [(float(p.get("x")), float(p.get("y")), float(p.get("zOffset", 0)))
                  for p in node.findall("./geometry/linkPolyPts/linkPolyPoint")]
        import math
        lengths[connector] = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
    observations = []
    for path in snapshots:
        raw = json.loads(path.read_text(encoding="utf-8"))
        sec = int(path.stem.split("_")[-1])
        if sec < 900:
            continue
        for connector in ("10682", "10643", "121"):
            vehicles = [r for r in raw["vehicle_records"]["records"] if str(r["link_no"]) == connector]
            stopped = [r for r in vehicles if r["stopped"]]
            tail = min((float(r["position_m"]) for r in stopped), default=None)
            observations.append({"sim_sec": sec, "connector": connector, "count": len(vehicles),
                                 "stopped_count": len(stopped), "stopped_threshold_kph": raw["vehicle_records"]["stopped_threshold_kph"],
                                 "mean_speed_kph": mean(float(r["speed_kph"]) for r in vehicles) if vehicles else None,
                                 "upstreammost_stopped_position_m": tail,
                                 "downstreammost_stopped_position_m": max((float(r["position_m"]) for r in stopped), default=None),
                                 "length_m": lengths[connector],
                                 "tail_extent_fraction_reference_only": max(0., 1 - tail / lengths[connector]) if tail is not None else 0.})
    return {"positions": positions, "weaving_distance_10639_to_10682_m": positions[2]["physical_chain_pos_m"] - positions[1]["physical_chain_pos_m"],
            "physical_cell_boundaries_m": chain["segment_bounds_m"][8:11],
            "model_scalar_cell_boundaries_m": [i * topology["freeway_segment_length_km"] * 1000 for i in (8, 9, 10)],
            "ramp_group": mapping["ramp_meter_groups"]["R_F_E"], "observations": observations,
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (mapping_path, network_path)}}


def trace_inputs(config_path, state_path, previous_path, action_path):
    traces = []
    from probe_model_area_integration import adapter, build_projected
    from evaluation.controllers import area_freeway_accounting as accounted, area_runtime
    from src.models.demand import DemandStep
    from src.models.state import ControlAction
    source, first_line = inspect.getsourcelines(accounted._freeway_substep_events)
    capture_line = first_line + next(i for i, line in enumerate(source) if "vehicle_new = max(0.0, vehicle_raw)" in line)
    for time in (int(json.loads(state_path.read_text(encoding='utf-8'))['sim_sec']),):
        cfg, state, detectors, tuning, raw, _, _ = build_projected(config_path, state_path, previous_path, fixture_inputs=False)
        from src.controllers.rollout_endpoint import evaluate_price_point, ObjectiveSpec
        action = adapter.control_from_json(action_path, cfg, ControlAction)
        cal = adapter.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
        cal = adapter.deep_update(dict(cal), tuning.get("calibration_override", {}))
        forecast = adapter.demand_from_state(raw, cfg, DemandStep, 1, cal, detectors)
        rows = []
        def observe(frame, event, arg):
            if frame.f_code is not accounted._freeway_substep_events.__code__:
                return None
            if event == "line" and frame.f_lineno == capture_line:
                v = frame.f_locals
                if v["link"] == "FW_E" and v["i"] in (8, 9):
                    i = v["i"]
                    rows.append({"elapsed_sec": (len(rows) // 2 + 1) * cfg.simulation.T_f_sec,
                                 "cell": i, "R_F_E_actual_release_vph": v["ramp_release"]["R_F_E"],
                                 "cell_ramp_in_vph": v["ramp_in_by_link"]["FW_E"][i],
                                 "cell_off_groups": v["offramps_by_segment"].get(i, []),
                                 "cell_normal_off_vph": v["normal_off_total"], "cell_accepted_off_vph": v["effective_off_total"],
                                 "q_in_vph": v["q_in"], "q_out_vph": v["q_out"]})
            return observe
        previous = sys.gettrace()
        try:
            sys.settrace(observe)
            result = evaluate_price_point(state, action, forecast, [], ObjectiveSpec(cfg, depth_override=1, box_walk=False, score_mode="raw"))
        finally:
            sys.settrace(previous)
        result.states[-1]._control_area_ledger.assert_stocks(area_runtime.model_inventory(result.states[-1], cfg))
        assert len(rows) == 30
        assert all(r["cell_ramp_in_vph"] == (0. if r["cell"] == 8 else r["R_F_E_actual_release_vph"]) for r in rows)
        assignments = state.local_observation_summary["projection_diagnostics"]["physical_stock_assignment_by_link"]
        traces.append({"start_sec": time, "mass_closure": True,
                       "implementation": "installed production runtime and endpoint",
                       "previous_action": str(previous_path), "replay_action": str(action_path),
                       "source_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                           (config_path, state_path, previous_path, action_path, Path(accounted.__file__), Path(adapter.__file__))},
                       "initial_branch_assignment": {c: assignments.get(c, {}) for c in ("10639", "10681", "10682", "10643", "121")},
                       "ramp_queue_group_veh": state.ramp_queue.get("R_F_E"),
                       "ramp_feed_movement_specs": {m: cfg.network.urban_movements[m] for m in cfg.network.on_ramp_to_movement.get("R_F_E", [])},
                       "boundary_out_split": getattr(cfg.network, "boundary_out_ramp_split", {}).get("SC1004_W_out", {}),
                       "rows": rows})
    return traces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('config', 'snapshot', 'previous', 'action', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.with_suffix('.csv').exists():
        raise FileExistsError('Choose new production JSON/CSV paths; historical evidence is preserved')
    tuning = json.loads(args.config.read_text(encoding='utf-8'))
    area = json.loads((ROOT/tuning['control_area_objective']['membership_path']).read_text(encoding='utf-8'))
    result = geometry_and_observations(ROOT/tuning['mapping_json'], ROOT/area['network']['path'], [args.snapshot.resolve()])
    result['model_input_traces'] = trace_inputs(args.config.resolve(), args.snapshot.resolve(), args.previous.resolve(), args.action.resolve())
    result['limitations'] = ['Physical order is observed; causal friction is not isolated.',
        'Stopped tail extent is not a verified contiguous queue or calibrated capacity.',
        'No production equation or parameter is replaced; sys.settrace records installed local values.']
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    with output.with_suffix('.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result['observations'][0]))
        writer.writeheader(); writer.writerows(result['observations'])
    print(json.dumps({'output': str(output), 'positions': result['positions'], 'traces': len(result['model_input_traces'])}))


if __name__ == '__main__':
    main()
