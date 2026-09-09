"""Actual projected NC/n7 coupled rollout through the installed area endpoint."""
from pathlib import Path
import json
import argparse
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics')]
from test_observation_projection import ActualInstalledProjection as Harness
from diagnostics.review_fixtures import fixture_path


def fixture(state_path=None, *, dynamic_routes=False):
    Harness.setUpClass()
    adapter = Harness.adapter
    from src.models.state import TrafficState, ControlAction
    from evaluation.controllers import area_runtime, observation_projection, physical_movement_routes, shared_approach, projection_support
    nc = ROOT / 'evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry'
    path = state_path or nc / 'state_000900.json'
    if not path.is_absolute():
        path = ROOT / path
    path = fixture_path(path)
    snapshot_time = int(json.loads(path.read_text(encoding='utf-8'))['sim_sec'])
    previous_candidates = [p for p in path.parent.glob('action_*.json') if int(p.stem.split('_')[-1]) < snapshot_time]
    previous = max(previous_candidates, key=lambda p: int(p.stem.split('_')[-1]))
    cfg, _, detectors, tuning, raw, mapping, _ = Harness.build_projected(Harness.config_path, path, previous)
    import copy
    cfg = copy.deepcopy(cfg)
    tuning.setdefault('urban', {}).setdefault('movements', {})['physical_route_topology'] = 'diagnostics/physical_movement_routes_ver2.json'
    detectors, _ = physical_movement_routes.configure_topology_repair(cfg, detectors, tuning, state_json=raw)
    if dynamic_routes:
        from evaluation.controllers.area_dynamic_routes import configure as configure_dynamic_routes
        tuning['urban']['movements']['dynamic_physical_route_topology'] = 'diagnostics/dynamic_area_routes_ver2.json'
        detectors, dynamic_metadata = configure_dynamic_routes(cfg, detectors, tuning, state_json=raw)
    tuning['urban']['shared_approach'] = 'diagnostics/shared_approach_ver2.json'
    tuning.setdefault('observation', {})['physical_support_repair'] = 'diagnostics/physical_projection_support_ver2.json'
    shared_approach.configure(cfg, tuning, raw)
    detectors, raw, _ = projection_support.configure(cfg, tuning, detectors, raw)
    detectors, _ = observation_projection.install_physical_branch_projection(cfg, Harness.overlay, detectors, link_counts=adapter._link_counts_from_local_observation(raw))
    calibration = adapter.deep_update(dict(Harness.calibration), tuning.get('calibration_override', {}))
    with patch.object(adapter, 'build_local_observation_summary', Harness.patched_summary):
        state = adapter.traffic_state_from_vissim(raw, cfg, TrafficState, detectors, calibration)
    tuning.setdefault('urban', {})['conservative_initial_transit'] = True
    initial_metadata = area_runtime.configure_initial_transit(cfg, tuning, state)
    initial_metadata.update(shared_approach.initialize(state, cfg, raw, detectors))
    initial_metadata.update(shared_approach.install(adapter, cfg))
    cfg.network.local_landing_state = True
    observation_projection.install_direct_branch_capacity_runtime(cfg)
    area_tuning = {'control_area_objective': {'enabled': True, 'beta_seconds': 0,
                    'membership_path': 'diagnostics/control_area_membership.json',
                    'route_contract_path': 'diagnostics/control_area_route_contract_physical_routes.json'}}
    state.control_area_initialization_diagnostics = area_runtime.configure(adapter, cfg, area_tuning, state, detectors)
    if dynamic_routes:
        from evaluation.controllers.area_dynamic_routes import extend_routes
        membership = json.loads((ROOT / 'diagnostics/control_area_membership.json').read_text(encoding='utf-8'))
        cfg.network.control_area_routes, path_metadata = extend_routes(
            cfg, cfg.network.control_area_routes, detectors, membership, 'diagnostics/dynamic_area_routes_ver2.json')
        state.control_area_initialization_diagnostics.update(dynamic_metadata)
        state.control_area_initialization_diagnostics.update(path_metadata)
    state.control_area_initialization_diagnostics.update(initial_metadata)
    state.control_area_initialization_diagnostics['previous_action_path'] = str(previous.relative_to(ROOT))
    return cfg, state, adapter.control_from_json(previous, cfg, ControlAction), raw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('state', nargs='?', type=Path)
    parser.add_argument('--structural-only', action='store_true')
    parser.add_argument('--observed-demand', action='store_true')
    parser.add_argument('--depth', type=int, default=1)
    parser.add_argument('--dynamic-routes', action='store_true')
    args = parser.parse_args()
    cfg, state, control, raw = fixture(args.state, dynamic_routes=args.dynamic_routes)
    unresolved_routes = set()
    if args.structural_only:
        # This mode validates event/model mass closure, NOT the Omega score.
        # Missing physical routes retain cohorts solely to expose later bugs.
        for movement in cfg.network.urban_movements:
            for prefix in ('movement:', 'arrival:'):
                key = prefix + movement
                row = cfg.network.control_area_routes.get(key, {})
                if type(row.get('target_inside')) is not bool:
                    unresolved_routes.add(key)
                    cfg.network.control_area_routes[key] = {'inside_to_inside': 1.0, 'outside_to_inside': 0.0,
                                                            'status': 'DIAGNOSTIC_UNRESOLVED_PRESERVE'}
        for origin in cfg.network.boundary_in_links:
            cfg.network.control_area_routes['input:gate:' + origin] = {'target_inside': False}
        for ramp in cfg.network.ramps:
            cfg.network.control_area_routes['input:ramp:' + ramp] = {'target_inside': False}
    from src.models.demand import DemandStep
    from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point
    forecast = Harness.adapter.demand_from_state(raw, cfg, DemandStep, args.depth) if args.observed_demand else [DemandStep({}, {}, {}) for _ in range(args.depth)]
    result = evaluate_price_point(state, control, forecast, [],
                                  ObjectiveSpec(cfg, depth_override=args.depth, score_mode='raw'))
    output = result.control_area
    if args.structural_only:
        output = {'all_model_stocks_conserved': True, 'event_count': output['event_count'],
                  'unresolved_accepted_events': {key.removeprefix('unresolved_route:'): value for key, value in output['flow_counts'].items()
                                                 if key.startswith('unresolved_route:') and value > 1e-9},
                  'score_withheld': 'physical route coverage incomplete; this probe only validates mass closure'}
    output['physical_route_coverage_validated'] = not args.structural_only
    output['demand'] = 'observed forecast' if args.observed_demand else 'zero'
    output['depth'] = args.depth
    output['initialization'] = state.control_area_initialization_diagnostics
    output['initialization'] = {k: v for k, v in output['initialization'].items() if k != 'resolved_gate_aliases'}
    output.pop('flow_counts', None)
    suffix = '_dynamic' if args.dynamic_routes else ''
    output_path = ROOT / 'diagnostics' / f'area_endpoint_{int(state.time_sec):06d}_d{args.depth}_{"structure" if args.structural_only else "strict"}{suffix}.json'
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(output, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
