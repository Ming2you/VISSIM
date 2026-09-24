"""Reproduce the frozen seed29 VSL component forecast with the existing model."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARRAYS = ('cells', 'flows', 'ports', 'ramps')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def array_hash(value):
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def verify_manifest():
    path = HERE / 'manifest.json'
    if not path.exists():
        return {'verified': False, 'reason': 'manifest.json is absent'}
    manifest = load(path)
    files = manifest['files']
    normalized = set(manifest.get('lf_normalized_files', []))
    if not files:
        raise ValueError('The bundle manifest contains no file hashes')
    for relative, expected in files.items():
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT):
            raise ValueError(f'Manifest path is outside this checkout: {relative}')
        content = source.read_bytes()
        if relative in normalized:
            content = content.replace(b'\r\n', b'\n')
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected:
            raise ValueError(f'Manifest SHA256 mismatch: {relative}')
    required = {str((HERE / name).relative_to(ROOT)).replace('\\', '/')
                for name in ('candidate.json', 'parameters.json', 'geometry.json',
                             'case_29.json.gz')}
    if not required.issubset({name.replace('\\', '/') for name in files}):
        raise ValueError('Manifest does not cover all four reproduction inputs')
    return {'verified': True, 'files_checked': len(files)}


def integrate(times, stocks):
    return sum((stocks[a] + stocks[b]) * (b - a) / 7200
               for a, b in zip(times, times[1:]))


def measure(rollout, observed, cutoff, horizon):
    times = [round(cutoff + delta, 6) for delta in range(0, horizon + 1, 30)]
    actual = {round(row['time_s'], 6): row['n_veh'] for row in observed}
    if len(observed) != len(times) or set(actual) != set(times):
        raise ValueError('Observed component stocks must cover every 30-second point')
    predicted = {times[0]: actual[times[0]]}
    for stamp in times[1:]:
        cells = [row for row in rollout['cells'] if abs(row['time_s'] - stamp) < 1e-6]
        ports = [row for row in rollout['ports'] if abs(row['time_s'] - stamp) < 1e-6]
        ramps = [row for row in rollout['ramps'] if abs(row['end_sec'] - stamp) < 1e-6]
        if not cells or not ports or not ramps:
            raise ValueError(f'Missing component stock at {stamp}')
        predicted[stamp] = (sum(row['n_veh'] for row in cells)
                            + sum(row['n_veh'] for row in ports)
                            + sum(row['end']['connector_veh'] for row in ramps))
    if any(not math.isfinite(n) or n < 0 for n in [*actual.values(), *predicted.values()]):
        raise ValueError('Component stocks must be finite and nonnegative')
    residuals = [abs(row['conservation_residual_veh'])
                 for key in ('ports', 'ramps') for row in rollout[key]]
    residuals += [abs(row['continuity_residual_max_veh'])
                  for row in rollout['diagnostics']['roads']]
    if any(not math.isfinite(value) or value >= 1e-7 for value in residuals):
        raise ValueError('Model conservation residual exceeds 1e-7 vehicles')
    return {'predicted_veh_h': integrate(times, predicted),
            'actual_veh_h': integrate(times, actual),
            'conservation_max_veh': max(residuals),
            'stocks': [{'time_s': t, 'actual_n_veh': actual[t],
                        'predicted_n_veh': predicted[t]} for t in times]}


def offline(output):
    if output.exists():
        raise FileExistsError(f'Output already exists; choose a new directory: {output}')
    manifest = verify_manifest()
    parameters = load(HERE / 'parameters.json')
    geometry = load(HERE / 'geometry.json')
    with gzip.open(HERE / 'case_29.json.gz', 'rt', encoding='utf-8') as stream:
        case = json.load(stream)
    if set(case['arms']) != {'none', 'vsl'} or case['cutoff'] != 2220.1 or case['horizon'] != 450:
        raise ValueError('This replay requires the frozen seed29 NC/VSL 450-second case')
    sys.path.insert(0, str(ROOT))
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import load_base_model

    output.mkdir(parents=True, exist_ok=False)
    results = {}
    for arm in ('none', 'vsl'):
        frozen = case['arms'][arm]
        if frozen['args'][2] != parameters:
            raise ValueError(f'{arm}: captured parameters differ from parameters.json')
        model = load_base_model(geometry, HERE / 'candidate.json')
        rollout = model.rollout(*frozen['args'], **frozen['kwargs'])
        measured = measure(rollout, frozen['observed_n'], case['cutoff'], case['horizon'])
        expected = frozen['expected']
        hashes = {key: array_hash(rollout[key]) for key in ARRAYS}
        if hashes != expected['rollout_sha256']:
            changed = [key for key in ARRAYS if hashes[key] != expected['rollout_sha256'].get(key)]
            raise ValueError(f'{arm}: frozen rollout array mismatch: {", ".join(changed)}')
        if abs(measured['predicted_veh_h'] - expected['predicted_veh_h']) > 1e-8:
            raise ValueError(f'{arm}: predicted TTT differs from the frozen result')
        results[arm] = {**measured, 'rollout_sha256': hashes, 'frozen_result_matches': True}
        print(f"{arm}: predicted {measured['predicted_veh_h']:.12f} veh h; arrays match", flush=True)
    result = {'passed': True, 'manifest': manifest, 'seed': 29,
              'cutoff_s': case['cutoff'], 'horizon_s': case['horizon'], 'arms': results,
              'predicted_delta_veh_h': results['vsl']['predicted_veh_h'] - results['none']['predicted_veh_h'],
              'actual_delta_veh_h': results['vsl']['actual_veh_h'] - results['none']['actual_veh_h'],
              'scope': 'East 31 mainline cells plus four on-ramp and four off-ramp connectors; 30-second stock integration.',
              'qualification': 'Training-data reproduction only; no independent gain validation or whole-network benefit claim.'}
    (output / 'result.json').write_text(json.dumps(result, indent=2, ensure_ascii=False,
                                                  allow_nan=False), encoding='utf-8')
    print(f"PASS: VSL delta {result['predicted_delta_veh_h']:+.12f} veh h "
          f"(observed {result['actual_delta_veh_h']:+.12f}); {output / 'result.json'}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    replay = commands.add_parser('offline', help='Reproduce the frozen NC/VSL forecasts without VISSIM')
    replay.add_argument('--output', type=Path, required=True, help='New directory for result.json')
    args = parser.parse_args()
    try:
        offline(args.output.resolve())
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        parser.exit(1, f'Reproduction failed: {exc}\n')


if __name__ == '__main__':
    main()
