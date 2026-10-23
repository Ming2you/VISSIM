"""Read-only verification of the published S-DMPC source and static inputs.

Does not start VISSIM, freeze a tree, optimize controls, or read native results.
"""
import hashlib
import json
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    manifest_path = root / 'docs/sdmpc_plant_20261013/source_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    failures = []
    # Keep the original delivery receipt immutable and verify a pinned increment.
    increment_path = root / 'docs/sdmpc_vsl_20261023/source_manifest.json'
    if increment_path.is_file():
        increment = json.loads(increment_path.read_text(encoding='utf-8'))
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != increment['base_manifest_sha256']:
            failures.append('BASE MANIFEST HASH')
        manifest['files'].update(increment['files'])
    for relative, expected in manifest['files'].items():
        path = root / relative
        if not path.is_file():
            failures.append(f'MISSING {relative}')
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            failures.append(f'HASH {relative}')
    configs = [
        'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/' + mode + '_config.json'
        for mode in ('window', 'optimized', 'off')
    ] + ['diagnostics/solo355_local_20261013/' + mode + '_config.json' for mode in ('freeway_only', 'urban_only')]
    if increment_path.is_file():
        configs.append('diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json')
    for relative in configs:
        config = json.loads((root / relative).read_text(encoding='utf-8-sig'))
        for key in ('mapping_json', 'detector_mapping_json'):
            if not (root / config[key]).is_file():
                failures.append(f'CONFIG INPUT {relative}: {key}')
        if config['urban']['single_lane_causal_receiving'] != {
            'ramps': ['RM_C10639', 'RM_C10484'], 'wave_m_s': 3.2557309454394003
        }:
            failures.append(f'ADOPTED RECEIVING {relative}')
    print(json.dumps({'passed':not failures, 'files_checked':len(manifest['files']),
                      'configs_checked':len(configs), 'failures':failures}, indent=2))
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
