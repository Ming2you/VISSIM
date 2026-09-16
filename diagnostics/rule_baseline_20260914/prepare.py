"""Freeze the requested four arms; only policy and detector recording differ."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1/joint_config_fidelity_v3_portable.json'


def main():
    base = json.loads(BASE.read_text(encoding='utf-8'))
    detector = HERE / 'detector_mapping.json'
    mapping_sha = hashlib.sha256(detector.read_bytes()).hexdigest()
    settings = base['actuation']['real_world_ramp_metering']
    native_mapping = json.loads((ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json').read_text(encoding='utf-8'))
    meters = [row['id'] for row in native_mapping['ramp_meters']]
    lanes = {mid: settings['meter_lanes'].get(mid, 1) for mid in meters}
    rule = {
        'enabled': True, 'reference_speed_kph': 100, 'control_start_sec': 900,
        'detector_mapping_json': detector.relative_to(ROOT).as_posix(),
        'detector_mapping_sha256': mapping_sha,
        'vsl_rule': {'flow_threshold_vph_per_lane': 1600, 'occupancy_threshold_pct': 15,
                     'speed_thresholds_kph': [60, 80], 'speed_commands_kph': [60, 80, 100]},
        'alinea': {
            'gain_vph_per_pct': {mid: 70*lanes[mid] for mid in meters},
            'target_occupancy_pct': 15,
            'min_rate_vph': {mid: settings['per_lane_veh_per_cycle']['2']*360*lanes[mid] for mid in meters},
            'max_rate_vph': {mid: settings['per_lane_veh_per_cycle']['10']*360*lanes[mid] for mid in meters},
        },
        'parameter_status': 'Exploratory ALINEA target15pct and gain70veh/h/pct/lane; not calibrated critical occupancy or a validated physical capacity.',
    }
    files = {}
    for arm in ('none', 'vsl', 'rm', 'both'):
        cfg = deepcopy(base)
        cfg['name'] = 'rule_baseline100_' + arm
        cfg['diagnostic']['rule_profile'] = {**deepcopy(rule), 'arm': arm}
        # The rule requests60; the inherited MPC candidate set omitted it.
        # The same set also encodes CSV commands, so never bypass its validator.
        follower = cfg['config_overrides']['freeway_follower']
        follower['vsl_set'] = sorted(set(follower['vsl_set']) | set(rule['vsl_rule']['speed_commands_kph']))
        path = HERE / ('config_' + arm + '_v2.json')
        data = (json.dumps(cfg, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Existing case differs; keep it and prepare a new experiment directory')
        files[path] = data
    for path, data in files.items():
        if not path.exists(): path.write_bytes(data)
    print(json.dumps({'source': str(BASE), 'source_sha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
                      'cases': {p.name: hashlib.sha256(data).hexdigest() for p, data in files.items()},
                      'seed': 13, 'demand': 'freeway80 urban50', 'planned_end_sec': 3000}, indent=2))


if __name__ == '__main__':
    main()
