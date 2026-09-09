"""Build four flattened, review-only area configs without touching live configs."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BETAS = (0, 60, 150, 300)


def deep_merge(base, update):
    result = copy.deepcopy(base)
    for key, value in update.items():
        result[key] = deep_merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else copy.deepcopy(value)
    return result


def build(base, physics, clock=None):
    merged = deep_merge(base, physics)
    merged = deep_merge(merged, {'freeway': {'physical_vehicle_counts': True}})
    if clock is not None:
        merged = deep_merge(merged, clock)
    required = [(['freeway', key], True) for key in ('physical_vehicle_counts', 'local_lane_context',
                'conservative_offramp_drain', 'local_landing_state')]
    required += [(['urban', 'conservative_initial_transit'], True),
                 (['observation', 'physical_branch_projection', 'enabled'], True)]
    for path, expected in required:
        value = merged
        for key in path:
            value = value[key]
        if value is not expected:
            raise ValueError('Required proposed physics flag was overridden: ' + '.'.join(path))
    if 'extends' in merged:
        raise ValueError('Flattened candidates must not retain an unresolved extends directive')
    rows = {}
    for beta in BETAS:
        cfg = deep_merge(merged, {'control_area_objective': {
            'enabled': True, 'beta_seconds': beta,
            'membership_path': 'diagnostics/control_area_membership.json',
            'route_contract_path': 'diagnostics/control_area_route_contract_physical_routes.json'}})
        cfg['name'] = f'n7_area_physics_beta{beta}_review'
        rows[beta] = cfg
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clock-overlay', type=Path, default=Path('diagnostics/control_area_all_lever_overlay.json'),
                        help='Explicit physical signal and optimizer-offset experiment contract.')
    args = parser.parse_args()
    base = ROOT / 'evaluation/configs/n21_n7_20260908.json'
    physics = ROOT / 'diagnostics/control_area_physics_overlay.json'
    paths = [base, physics]
    clock = None
    if args.clock_overlay:
        path = args.clock_overlay if args.clock_overlay.is_absolute() else ROOT / args.clock_overlay
        clock = json.loads(path.read_text(encoding='utf-8'))
        paths.append(path)
    configs = build(json.loads(base.read_text(encoding='utf-8')), json.loads(physics.read_text(encoding='utf-8')), clock)
    for cfg in configs.values():
        if cfg['urban'].get('physical_signal_contract') is not True:
            raise ValueError('All-lever trial requires urban.physical_signal_contract=true')
        signal = cfg['actuation']['real_world_signal_control']
        if signal.get('enabled') is not True or signal.get('offset_writer') != 'experiment':
            raise ValueError('All-lever trial requires enabled real-world signals and explicit experiment writer')
    support = ROOT / configs[0]['observation']['physical_support_repair']
    if json.loads(support.read_text(encoding='utf-8')).get('full_area_coverage_audit', {}).get('require_positive_unresolved_failure') is not True:
        raise ValueError('635 support must retain strict positive unresolved failure')
    # Pin actual runtime code and data. Historical patch builders are not needed
    # to generate configs from a clean integrated checkout.
    paths += list((ROOT / 'evaluation/controllers').glob('*.py'))
    paths += [support, ROOT / 'evaluation/parameters.json', ROOT / 'evaluation/parameters.py',
              ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json',
              ROOT / 'scripts/run_real_world_stackelberg_controller.vbs',
              ROOT / 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1']
    def add_data(value):
        if isinstance(value, dict):
            for item in value.values():
                add_data(item)
        elif isinstance(value, list):
            for item in value:
                add_data(item)
        elif isinstance(value, str) and value.startswith(('diagnostics/', 'evaluation/', 'outputs/', 'network/')):
            path = (ROOT / value).resolve()
            if path.is_relative_to(ROOT.resolve()) and path.is_file():
                paths.append(path)
    add_data(configs[0])
    dynamic_path = ROOT / configs[0]['urban']['movements']['dynamic_physical_route_topology']
    dynamic_document = json.loads(dynamic_path.read_text(encoding='utf-8'))
    paths.append(ROOT / dynamic_document['calibration']['path'])
    paths = sorted(set(paths))
    destination = ROOT / 'diagnostics/area_candidate_configs'
    destination.mkdir(exist_ok=True)
    manifest = {'purpose': 'Review-only flattened MPC candidates; no live config was changed or launched.',
        'beta_units': 'seconds/vehicle; score TTT_veh_h - beta_seconds/3600 * outward_crossings_veh',
        'clock_overlay_supplied': clock is not None,
        'required_process_environment': {'RW_OFFSET_WRITER': 'experiment'},
        'remaining_integration': [] if clock is not None else ['Approved clock-contract overlay pending; rerun recipe with its file.'],
        'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        'outputs': {}}
    for beta, cfg in configs.items():
        path = destination / f'n7_area_beta{beta}.json'
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        manifest['outputs'][str(beta)] = {'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
