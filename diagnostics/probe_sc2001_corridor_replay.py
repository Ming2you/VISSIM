"""Production corridor fixture and replay; archived proposal helper is explicit."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics'), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import sc2001_corridor as corridor
from probe_area_endpoint import fixture as area_fixture
from test_observation_projection import ActualInstalledProjection as Harness
from evaluation.controllers import area_runtime, shared_approach, urban_flow_accounting
from evaluation.controllers.control_area_objective import physical_membership_from_ledger


def fixture(state_path=None, *, return_detectors=False, support_path='diagnostics/physical_projection_support_ver2.json'):
    cfg, original, control, raw = area_fixture(state_path, dynamic_routes=True)
    # Reuse the full diagnostic route/projection configuration, then reproject
    # the original physical records. Never move an already-aggregated stock by
    # guessing which of its vehicles belonged to78.
    # The fixture does not return detectors; repeat only its mapping mutations.
    path = state_path or ROOT / 'evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry/state_000900.json'
    prior_path = ROOT / original.control_area_initialization_diagnostics['previous_action_path']
    _, _, detectors, tuning, _, _, _ = Harness.build_projected(Harness.config_path, path, prior_path)
    from evaluation.controllers import physical_movement_routes, projection_support, observation_projection
    # Apply mappings on separate base cfg to avoid installing topology changes
    # twice on the actual already repaired cfg used by this replay.
    import copy
    map_cfg, _, _, _, _, _, _ = Harness.build_projected(Harness.config_path, path, prior_path)
    map_cfg = copy.deepcopy(map_cfg)
    tuning.setdefault('urban', {}).setdefault('movements', {})['physical_route_topology'] = 'diagnostics/physical_movement_routes_ver2.json'
    detectors, _ = physical_movement_routes.configure_topology_repair(map_cfg, detectors, tuning, state_json=raw)
    from evaluation.controllers.area_dynamic_routes import configure as configure_dynamic
    tuning['urban']['movements']['dynamic_physical_route_topology'] = 'diagnostics/dynamic_area_routes_ver2.json'
    detectors, _ = configure_dynamic(map_cfg, detectors, tuning, state_json=raw)
    tuning.setdefault('observation', {})['physical_support_repair'] = support_path
    detectors, raw, _ = projection_support.configure(cfg, tuning, detectors, raw)
    detectors, _ = observation_projection.install_physical_branch_projection(cfg, Harness.overlay, detectors, link_counts=Harness.adapter._link_counts_from_local_observation(raw))
    metadata = corridor.configure(cfg, {'urban': {'sc2001_corridor': 'diagnostics/sc2001_corridor_nc13.json'}}, raw)
    detectors, raw, projection = corridor.prepare_projection(cfg, detectors, raw)
    from src.models.state import TrafficState
    calibration = Harness.adapter.deep_update(dict(Harness.calibration), tuning.get('calibration_override', {}))
    with patch.object(Harness.adapter, 'build_local_observation_summary', Harness.patched_summary):
        state = Harness.adapter.traffic_state_from_vissim(raw, cfg, TrafficState, detectors, calibration)
    metadata.update(area_runtime.configure_initial_transit(cfg, {'urban': {'conservative_initial_transit': True}}, state))
    metadata.update(shared_approach.initialize(state, cfg, raw, detectors))
    metadata.update(corridor.initialize(state, cfg, raw, detectors))
    physical = physical_membership_from_ledger(json.loads((ROOT / 'diagnostics/control_area_membership.json').read_text(encoding='utf-8')))
    metadata.update(corridor.extend_area_routes(cfg))
    area_runtime.seed_from_projection(state, cfg, physical)
    state.control_area_initialization_diagnostics = metadata
    if return_detectors:
        return cfg, state, control, raw, detectors
    return cfg, state, control, raw


def proposal_module():
    # Historical diagnostic callers explicitly request the pre-integration
    # proposal. Never reapply its patch to the now-integrated production body.
    from fixed_source_reference import source as fixed_source
    from prepare_sc2001_urban_patch import proposed_source
    source = fixed_source('evaluation/controllers/urban_flow_accounting.py')
    module = types.ModuleType('diagnostics.sc2001_isolated_urban')
    code = proposed_source(source)
    exec(compile(code, '<isolated unapplied corridor urban body>', 'exec'), module.__dict__)
    module._adapter = Harness.adapter
    return module, hashlib.sha256(source.encode()).hexdigest(), hashlib.sha256(code.encode()).hexdigest()


def run(time, depth):
    path = None if time == 900 else ROOT / 'evaluation/runs/codex_n7_s13_6056c94_20260909/decisions_codex_n7_s13_6056c94_20260909/state_003300.json'
    cfg, state, control, raw = fixture(path)
    source_hash = hashlib.sha256(Path(urban_flow_accounting.__file__).read_bytes()).hexdigest()
    from src.models.demand import DemandStep
    from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point
    forecast = Harness.adapter.demand_from_state(raw, cfg, DemandStep, depth)
    result = evaluate_price_point(state, control, forecast, [], ObjectiveSpec(cfg, depth_override=depth, score_mode='raw'))
    last = result.states[-1]
    ledger = last._control_area_ledger
    ledger.assert_stocks(area_runtime.model_inventory(last, cfg))
    output = {'snapshot_sec': time, 'horizon_sec': depth*150, 'physical_route_coverage_validated': True,
        'demand': 'same-snapshot observed forecast; no future FZP', 'canonical_urban_source_sha256': source_hash,
        'implementation': 'imported production urban_flow_accounting and sc2001_corridor',
        'initial_veh': state.control_area_initialization_diagnostics['sc2001_initial_veh'],
        'area': result.control_area, 'corridor': last.sc2001_corridor_state,
        'local_area_stock_closure': True, 'calibration': cfg.network.sc2001_corridor['calibration'],
        'limitations': cfg.network.sc2001_corridor['limitations']}
    output['area']['sc2001_flow_counts'] = {key: value for key, value in output['area'].pop('flow_counts').items() if 'SC2001' in key or 'sc2001:' in key}
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--time', type=int, choices=[900, 3300], default=900)
    parser.add_argument('--depth', type=int, choices=[1, 3], default=1)
    args = parser.parse_args()
    output = run(args.time, args.depth)
    path = ROOT / f'diagnostics/sc2001_replay_{args.time}_{args.depth*150}.json'
    path.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps({key: output[key] for key in ['snapshot_sec', 'horizon_sec', 'physical_route_coverage_validated', 'initial_veh', 'area']}, indent=2))
