"""Derive a native-only NC input; never rebind historical model evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'diagnostics/contract_observer_off_configs_v3/n7_area_beta0.json'
BASE_SHA = '201b7b6d5c759736201dd9a08b036dd3cd4891501a9d2de922b59651d3fd910d'
OUT = ROOT / 'diagnostics/native_nc5400_config_v1'
REMOVED_URBAN = ('route_choice_corridor', 'native_internal_inputs', 'shared_approach',
                 'sc2001_corridor', 'preserve_known_wout_routes')
REMOVED_MOVEMENTS = ('physical_route_topology', 'dynamic_physical_route_topology',
                     'physical_phase_authority', 'native_input_signal_authority')


def derive(base):
    result = deepcopy(base)
    result['control_area_objective']['enabled'] = False
    result['observation'] = {}
    result['prediction'] = {'native_input_schedule': False}
    urban = result['urban']
    urban['conservative_initial_transit'] = False
    urban['shared_local_service_pool'] = False
    for key in REMOVED_URBAN:
        urban.pop(key, None)
    for key in REMOVED_MOVEMENTS:
        urban['movements'].pop(key, None)
    urban['capacity'].pop('head_resource_contract', None)
    return result


def differences(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        result = []
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                result.append({'path': list(path + (key,)), 'before_present': key in a,
                               'after_present': key in b, 'before': a.get(key), 'after': b.get(key)})
            else:
                result.extend(differences(a[key], b[key], path + (key,)))
        return result
    return [] if type(a) is type(b) and a == b else [{'path': list(path), 'before': a, 'after': b}]


def validate(base, candidate):
    if candidate != derive(base):
        raise ValueError('NC input differs from the explicit model-hook-only transformation')
    for key in ('actuation', 'freeway', 'mapping_json', 'detector_mapping_json'):
        if candidate.get(key) != base.get(key):
            raise ValueError('Physical command/mapping settings changed: ' + key)
    if (candidate['urban']['capacity']['head_observation']['enabled'] is not False
            or candidate['actuation']['real_world_signal_control']['apply_to_no_control'] is not False
            or candidate['actuation']['real_world_signal_control']['offset_writer'] != 'experiment'):
        raise ValueError('Wrong native ownership/head observer/offset mode')
    return differences(base, candidate)


def main():
    raw = BASE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA or OUT.exists():
        raise ValueError('Wrong base or existing output')
    base = json.loads(raw.decode('utf-8-sig')); candidate = derive(base)
    diff = validate(base, candidate)
    encoded = (json.dumps(candidate, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    OUT.mkdir()
    (OUT / 'config.json').write_bytes(encoded)
    report = {'schema': 'native-nc5400-model-hooks-off/v1', 'base': {'path': BASE.relative_to(ROOT).as_posix(), 'sha256': BASE_SHA},
              'output': {'path': (OUT / 'config.json').relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(encoded).hexdigest()},
              'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'json_diff': diff,
              'preserved': ['complete actuation settings', 'complete freeway settings', 'mapping and detector mapping',
                            'native urban ownership', 'head observation OFF', 'runtime source bytes', 'all original evidence bytes'],
              'scope': 'Pure native traffic experiment. Any remaining adapter prediction is incidental and must not be used as model or objective evidence. Omega outcomes are measured externally from actual trajectories.',
              'historical_evidence_rebound': False, 'physical_command_smoke_pending': True}
    (OUT / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'output': report['output'], 'json_diff_count': len(diff)}))


if __name__ == '__main__':
    main()
