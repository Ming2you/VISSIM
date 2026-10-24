"""Compare one150-second installed-production replay with recorded outcomes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'diagnostics'), str(ROOT/'vendor/NumSim-mine')]


def run(config_path, state_path, previous_path, action_path, segment_path, baseline_path=None):
    from probe_model_area_integration import adapter, build_projected, replay_provenance, route_information
    from evaluation.controllers import urban_flow_accounting, area_runtime
    cfg, state, detectors, tuning, raw, _, _ = build_projected(
        config_path, state_path, previous_path, fixture_inputs=False)
    initial_routes = route_information(state, cfg)
    from src.models.demand import DemandStep
    from src.models.state import ControlAction
    from src.controllers.rollout_endpoint import evaluate_price_point, ObjectiveSpec
    if not getattr(cfg.network, 'control_area_enabled', False):
        raise ValueError('Use the explicit final area configuration for this diagnostic')
    control = adapter.control_from_json(action_path, cfg, ControlAction)
    calibration = adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration = adapter.deep_update(calibration, tuning.get('calibration_override', {}))
    demand = adapter.demand_from_state(raw, cfg, DemandStep, 1, calibration, detectors)
    result = evaluate_price_point(state, control, demand, [], ObjectiveSpec(cfg, depth_override=1, box_walk=False, score_mode='raw'))
    final = result.states[-1]
    final._control_area_ledger.assert_stocks(area_runtime.model_inventory(final, cfg))
    start = int(raw['sim_sec'])
    horizon = int(raw['control_interval_sec'])
    assert not result.aborted and len(result.states) == 1 and final.time_sec == start+horizon
    # Future observations are read only after prediction, for validation only.
    with segment_path.open(encoding='utf-8-sig', newline='') as stream:
        observed = {(int(row['sim_sec']), row['model_link'], int(row['segment_index'])): row for row in csv.DictReader(stream)}
    baseline = {}
    if baseline_path:
        with baseline_path.open(encoding='utf-8-sig', newline='') as stream:
            baseline = {(int(row['start_sec']), row['model_link'], int(row['cell'])): row
                for row in csv.DictReader(stream) if int(row['horizon_sec']) == horizon}
    records = []
    for link in cfg.network.freeway_links:
        for cell in range(cfg.network.freeway_segments_per_link):
            actual = observed[(start+horizon, link, cell)]
            old = baseline.get((start, link, cell))
            records.append({'start_sec': start, 'horizon_sec': horizon, 'model_link': link, 'cell': cell,
                'actual_speed_kph': float(actual['mean_speed_kph']),
                'historical_prediction_speed_kph': float(old['predicted_speed_kph']) if old else None,
                'production_prediction_speed_kph': final.freeway_speed[link][cell],
                'actual_density_veh_km_lane': float(actual['density_veh_km_lane']),
                'historical_prediction_density': float(old['predicted_density']) if old else None,
                'production_prediction_density': final.freeway_density[link][cell]})
    sources = [config_path, state_path, previous_path, action_path, segment_path,
        Path(adapter.__file__), Path(urban_flow_accounting.__file__)]
    if baseline_path:
        sources.append(baseline_path)
    return {'implementation': 'installed configure_runtime and endpoint',
        'method': 'Explicit initial snapshot, actual previous-action initialization, declared replay action, and same-snapshot demand forecast; no search.',
        'previous_action': str(previous_path), 'replay_action': str(action_path),
        'source_sha256': replay_provenance(tuning, *sources, Path(__file__)),
        'initial_route_information': initial_routes, 'final_route_information': route_information(final, cfg),
        'limitations': ['Historical comparison rows retain their original model/source meaning.',
            'NC13 route priors are exploratory; holdout evaluation is separate.',
            'Model predictions are not VISSIM counterfactual control outcomes.'] +
            (['Unknown already-chosen routes are held for diagnosis; this is not a complete live-route prediction.']
             if initial_routes['route_choice_information_complete'] is False else []),
        'all_stock_closures_pass': True, 'area': result.control_area, 'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('config', 'snapshot', 'previous', 'action', 'segments', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--historical-baseline', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Choose a new production output; historical evidence is preserved')
    output = run(args.config.resolve(), args.snapshot.resolve(), args.previous.resolve(),
        args.action.resolve(), args.segments.resolve(), args.historical_baseline.resolve() if args.historical_baseline else None)
    args.output.write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'records': len(output['records']), 'all_stock_closures_pass': True, 'output': str(args.output)}))


if __name__ == '__main__':
    main()
