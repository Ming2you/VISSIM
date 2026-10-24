"""Installed-production price endpoint replays with explicit recorded inputs."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import pickle
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics'), str(ROOT / 'vendor/NumSim-mine')]
BETAS = (0, 60, 150, 300)


def fingerprint(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def one(path, config_path, previous_path, *, depth=3, candidate_names=None, betas=BETAS):
    from probe_model_area_integration import adapter, build_projected, replay_provenance, route_information
    from evaluation.controllers import urban_flow_accounting, area_runtime
    cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(
        config_path, path, previous_path, fixture_inputs=False)
    initial_routes = route_information(state, cfg)
    from src.models.demand import DemandStep
    from src.models.state import ControlAction
    from src.controllers.rollout_endpoint import ObjectiveSpec, LeverMove, evaluate_price_point
    if not getattr(cfg.network, 'control_area_enabled', False):
        raise ValueError('Strict area replay requires an explicitly enabled final area config')
    control = adapter.control_from_json(previous_path, cfg, ControlAction)
    source_hash = hashlib.sha256(Path(urban_flow_accounting.__file__).read_bytes()).hexdigest()
    from evaluation.controllers.control_area_objective import physical_membership_from_ledger
    physical = physical_membership_from_ledger(json.loads((ROOT / tuning['control_area_objective']['membership_path']).read_text(encoding='utf-8')))
    fw_links = {str(link) for row in mapping['freeway_model_links'].values() for link in row['chain_links']}
    raw_counts = raw['vehicle_records']['full_network_link_counts']
    assigned = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    gaps = {link: count-sum(assigned.get(link, {}).values()) for link, count in raw_counts.items()
            if physical[link] and link not in fw_links and abs(count-sum(assigned.get(link, {}).values())) > 1e-7}
    if gaps:
        raise AssertionError('Initial physical urban observations are unrepresented: ' + str(gaps))
    raw_initial = sum(count for link, count in raw_counts.items() if physical[link])
    modeled_initial = sum(row['inside'] for row in state._control_area_ledger.stocks.values())
    if abs(raw_initial-modeled_initial) > 1e-7:
        raise AssertionError('Initial physical Omega count differs from model inventory')
    calibration = adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
    calibration = adapter.deep_update(calibration, tuning.get('calibration_override', {}))
    forecast = adapter.demand_from_state(raw, cfg, DemandStep, depth, calibration, detectors)
    meter = float(control.ramp_metering['R_F_W'])
    cap = float(cfg.network.ramp_capacity_veh_h['R_F_W'])
    meter_target = min(cap, meter + .1*cap) if meter < .95*cap else max(.2*cap, meter - .1*cap)
    vsl_values = sorted(float(x) for x in cfg.freeway_follower.vsl_set)
    target_vsl = min(vsl_values, key=lambda value: abs(value - 80))
    vsl_keys = [key for key in control.vsl if key.startswith('FW_E__seg') and int(key.split('__seg')[1]) < 6]
    if not vsl_keys:
        vsl_keys = ['FW_E']
    if all(control.vsl[key] == target_vsl for key in vsl_keys):
        target_vsl = max(vsl_values)
    green_now = control.green_times['SC1004_p1']
    green_target = min(cfg.network.signal_green_max('SC1004'), green_now + 10)
    if green_target == green_now:
        green_target = max(cfg.network.green_min, green_now - 10)
    candidates = {'previous': [], 'green_SC1004_primary': [LeverMove('green', 'SC1004', green_target)],
                  'meter_R_F_W': [LeverMove('meter', 'R_F_W', meter_target)],
                  'vsl_FW_E_upstream': [LeverMove('vsl', key, target_vsl) for key in vsl_keys],
                  'offset_SC1004': [LeverMove('offset', 'SC1004', float(control.offsets.get('SC1004', 0)) + 10)]}
    if candidate_names:
        candidates = {name: candidates[name] for name in candidate_names}
    before_state, before_control = fingerprint(state), fingerprint(control)
    scored = {}
    for name, schedule in candidates.items():
        rows = {}
        physics = None
        for beta in betas:
            cfg.network.control_area_beta_seconds = beta
            spec = ObjectiveSpec(cfg, depth_override=depth, score_mode='price', far_enabled=True,
                                 abort_above=0, box_walk=False)
            result = evaluate_price_point(state, control, forecast, schedule, spec)
            last = result.states[-1]
            ledger = last._control_area_ledger
            ledger.assert_stocks(area_runtime.model_inventory(last, cfg))
            if result.aborted or len(result.states) != depth or result.far != 0:
                raise AssertionError(f'Endpoint horizon/pruning mismatch: aborted={result.aborted}, states={len(result.states)}, far={result.far}, times={[s.time_sec for s in result.states]}')
            metrics = result.control_area
            expected = metrics['ttt_veh_h'] - beta/3600 * metrics['ttd_veh'] + metrics['additional_cost_veh_h']
            if not math.isclose(result.objective, expected, abs_tol=1e-8):
                raise AssertionError('Actual price endpoint does not use TTT minus beta times exits')
            observed = (metrics['ttt_veh_h'], metrics['ttd_veh'], fingerprint(ledger.stocks))
            if physics is None:
                physics = observed
            elif observed != physics:
                raise AssertionError('Changing objective coefficient mutated physical rollout or candidate stock')
            if fingerprint(state) != before_state or fingerprint(control) != before_control:
                raise AssertionError('Candidate evaluation changed its shared observation/action')
            if ledger is state._control_area_ledger:
                raise AssertionError('Candidate reused the observation ledger instance')
            rows[str(beta)] = result.objective
        scored[name] = {'ttt_veh_h': physics[0], 'ttd_veh': physics[1], 'objectives_veh_h': rows,
                        'schedule': [vars(move) for move in schedule], 'event_count': metrics['event_count'],
                        'final_route_information': route_information(last, cfg)}
    # Rerun the opening candidate after every other candidate, then mutate only
    # that result ledger to prove independent copy ownership, not just equality.
    opening = next(iter(candidates))
    cfg.network.control_area_beta_seconds = betas[0]
    repeated = evaluate_price_point(state, control, forecast, candidates[opening], ObjectiveSpec(cfg, depth_override=depth, score_mode='price', box_walk=False))
    if repeated.objective != scored[opening]['objectives_veh_h'][str(betas[0])]:
        raise AssertionError('Candidate order changed the opening candidate score')
    stock = next(iter(repeated.states[-1]._control_area_ledger.stocks.values()))
    stock['inside'] += 1
    if fingerprint(state) != before_state:
        raise AssertionError('Mutating a returned candidate changed the observation ledger')
    rankings = {str(beta): sorted(scored, key=lambda key: scored[key]['objectives_veh_h'][str(beta)]) for beta in betas}
    return {'snapshot_sec': state.time_sec, 'horizon_sec': depth*float(raw['control_interval_sec']), 'source_snapshot': str(path.relative_to(ROOT)),
            'physical_stock_coverage_validated': True, 'all_stock_closures_pass': True,
            'initial_route_information': initial_routes,
            'limitations': ['Physical stock coverage and conservation do not establish routing or predictive fidelity.'] +
                (['Unknown already-chosen routes are held for diagnosis; this is not a complete live-route prediction.']
                 if initial_routes['route_choice_information_complete'] is False else []),
            'candidate_copy_independence': True, 'coefficient_does_not_change_physics': True,
            'actual_price_endpoint_coefficients_verified': True, 'far_and_invalid_pruning_disabled': True,
            'fixed_controls': 'box_walk=False; final physical phase and meter realization still apply',
            'implementation': 'installed configure_runtime and price endpoint',
            'canonical_urban_source_sha256': source_hash,
            'source_sha256': replay_provenance(tuning, config_path, path, previous_path, Path(__file__)),
            'previous_action': str(previous_path),
            'initial_urban_physical_coverage': True, 'raw_initial_omega_veh': raw_initial,
            'model_initial_omega_veh': modeled_initial, 'initial_FW_geometry_delta_veh': raw_initial-modeled_initial,
            'projection_support_path': tuning.get('observation', {}).get('physical_support_repair'),
            'scores': scored, 'rankings': rankings,
            'calibration_scope': 'NC seed13 offline route priors; pure n7 seed13 is exploratory, seed14 holdout pending.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--snapshot', type=Path)
    group.add_argument('--decisions', type=Path)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--depth', type=int, choices=(1, 3), default=3)
    parser.add_argument('--candidate', action='append')
    parser.add_argument('--beta', action='append', type=float)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--timeout-sec', type=float, default=90)
    args = parser.parse_args()
    if args.output and args.output.exists():
        raise FileExistsError('Choose a new production output; historical evidence is preserved')
    if args.snapshot:
        if args.previous is None:
            parser.error('--snapshot requires its actual --previous action')
        result = one(args.snapshot.resolve(), args.config.resolve(), args.previous.resolve(),
            depth=args.depth, candidate_names=args.candidate, betas=tuple(args.beta or BETAS))
        if args.output:
            args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
        print('AREA_SNAPSHOT='+json.dumps(result, sort_keys=True))
        return
    if args.output is None:
        parser.error('--decisions requires a new --output path')
    paths = sorted(p for p in args.decisions.glob('state_*.json') if 900 <= int(p.stem.split('_')[-1]) <= 5400)
    if not paths:
        raise FileNotFoundError('No snapshots in the explicit decisions directory')
    expected_times = list(range(900, 5401, 150))
    output = {'implementation': 'installed production', 'snapshots': [], 'failures': [],
        'expected_times': expected_times,
        'all_expected_snapshots_present': [int(p.stem.split('_')[-1]) for p in paths] == expected_times}
    for path in paths:
        raw = json.loads(path.read_text(encoding='utf-8'))
        previous = path.with_name(f"action_{int(raw['sim_sec']-raw['control_interval_sec']):06d}.json")
        command = [sys.executable, '-X', 'utf8', str(Path(__file__)), '--config', str(args.config.resolve()),
            '--snapshot', str(path.resolve()), '--previous', str(previous.resolve()), '--depth', str(args.depth)]
        for name in args.candidate or []:
            command += ['--candidate', name]
        for beta in args.beta or []:
            command += ['--beta', str(beta)]
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=args.timeout_sec)
            line = next((line for line in result.stdout.splitlines() if line.startswith('AREA_SNAPSHOT=')), None)
            if result.returncode or line is None:
                raise RuntimeError(result.stderr[-5000:]+result.stdout[-1000:])
            output['snapshots'].append(json.loads(line.split('=', 1)[1]))
        except Exception as exc:
            output['failures'].append({'snapshot': str(path), 'error': str(exc)})
        args.output.write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    output['complete'] = output['all_expected_snapshots_present'] and not output['failures'] and len(output['snapshots']) == len(paths)
    args.output.write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
