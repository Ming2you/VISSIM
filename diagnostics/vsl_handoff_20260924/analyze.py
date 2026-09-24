"""Analyze one completed 9000-second native NC/VSL pair, one FZP pass per arm."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def netperf(path):
    """VISSIM writes TravTmTot and DelayLatent in vehicle-seconds."""
    required = {'TravTmTot', 'DelayLatent', 'DemandLatent', 'VehAct', 'VehArr'}
    values = {}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['sim_sec', 'attribute', 'value']:
            raise ValueError('Unexpected native_netperf.csv header')
        for row in reader:
            name = row['attribute']
            value = float(row['value'])
            if (float(row['sim_sec']) != 9000 or name not in required or name in values
                    or not math.isfinite(value) or value < 0):
                raise ValueError('Invalid or duplicate final native network-performance measurement')
            values[name] = value
    if set(values) != required:
        raise ValueError('Final native network-performance measurement is incomplete')
    return {'whole_network_TTT_veh_h': values['TravTmTot'] / 3600,
            'external_wait_veh_h': values['DelayLatent'] / 3600,
            'whole_network_TTS_including_external_veh_h': (values['TravTmTot'] + values['DelayLatent']) / 3600,
            'native_network_performance': values}


def validate_pair(folder):
    from diagnostics.vsl_handoff_20260924 import native

    preflight = load(folder / 'preflight.json')
    if not preflight['passed'] or preflight['control_start_sec'] != 900 or preflight['terminal_sec'] != 9000:
        raise ValueError('Analysis requires the prepared 900/9000 native pair')
    seed = preflight['seed']
    if type(seed) is not int or not 1 <= seed <= 2147483647:
        raise ValueError('Invalid paired seed')
    assets = load(HERE / 'assets.json')
    frozen = assets['network']
    original = native.checked_asset(HERE, frozen['file'], frozen['sha256']).read_bytes()
    expected_network = native.network_for_seed(original, seed)
    expected_sha = hashlib.sha256(expected_network).hexdigest()
    if preflight['prepared_source_network_sha256'] != expected_sha:
        raise ValueError('Preflight network differs from the frozen network beyond the seed')
    runs, metrics, validations = {}, {}, {}
    for arm in ('none', 'vsl'):
        prepared_folder = folder / f'prepared_{arm}'
        prepared = load(prepared_folder / 'prepared.json')
        run = folder / arm / 'run'
        receipt = load(run / 'run.json')
        if (not receipt.get('finished') or receipt.get('completed') is not True
                or receipt.get('owned_native_alive') is not False
                or receipt.get('exit_code') != 0 or receipt.get('error') is not None
                or receipt.get('seed') != seed or receipt.get('terminal_sec') != 9000
                or receipt.get('fixed_profile_validation_exit_code') != 0):
            raise ValueError(f'{arm}: native run must be finished, closed, and successfully validated')
        if Path(receipt['prepared']).resolve() != prepared_folder.resolve():
            raise ValueError(f'{arm}: receipt references a different prepared directory')
        validation = load(run / 'fixed_validation.json')
        if validation.get('passed') is not True or validation.get('unrecorded_signal_groups') != {}:
            raise ValueError(f'{arm}: fixed-profile validation failed or omitted native signals')
        network = Path(prepared['network']).resolve()
        source = Path(prepared['source_network']).resolve()
        if (Path(receipt['network']).resolve() != network or prepared['seed'] != seed
                or prepared['terminal_sec'] != 9000 or network.read_bytes() != expected_network
                or source.read_bytes() != expected_network):
            raise ValueError(f'{arm}: source/prepared network or seed does not match the frozen pair')
        profile = load(prepared_folder / 'fixed_profile.json')
        expected_profile = {'schema': 'native-fixed-profile/v1', 'network_sha256': expected_sha,
                            'seed': seed, 'control_start_sec': 900, 'terminal_sec': 9000,
                            'vehicle_record_interval_sec': 5, 'native_resolution_probe': 10,
                            'vsl_commands': [{'time_s': 900, 'dsd_no': n, 'speed_id': 90}
                                             for n in range(63, 67)] if arm == 'vsl' else [],
                            'meter_commands': [], 'collect_native_network_performance': True}
        if profile != expected_profile or load(folder / f'{arm}.json') != expected_profile:
            raise ValueError(f'{arm}: native commands differ from the frozen 9000-second experiment')
        # Validate NC as well: the shared analyzer only checks this explicitly for VSL.
        validations[arm] = {'finished': receipt['finished'], 'fixed_profile_passed': True,
                            'network_sha256': expected_sha}
        runs[arm] = run
        metrics[arm] = netperf(run / 'native_netperf.csv')
    return seed, runs, metrics, validations


def analyze(folder, output):
    if output.exists():
        raise FileExistsError(f'Output already exists; choose a new directory: {output}')
    seed, runs, metrics, validations = validate_pair(folder)
    geometry = load(HERE / 'geometry.json')
    from diagnostics.control_comparison_20260922 import compare

    output.mkdir(parents=True, exist_ok=False)
    compare.HERE, compare.END, compare.RUNS = output, 9000, runs
    compare.LABEL = {'none': 'No control', 'vsl': 'Bottleneck VSL90'}
    performance = []
    for arm, run in runs.items():
        row = compare.analyze(arm, run, geometry, seed=seed)
        performance.append({**row, **metrics[arm], 'Omega_TTT_veh_h': row['TTT_veh_h'],
                            'east_mainline_TTT_veh_h': row['TTT_FW_E']})
    prefixes = {arm: load(output / arm / 'fzp_evidence.json')['prefix_before900_sha256']
                for arm in runs}
    if len(set(prefixes.values())) != 1:
        raise ValueError('Pre900 raw FZP prefixes differ; the pair is not a common-initial-condition comparison')
    nc, vsl = performance
    fields = ('Omega_TTT_veh_h', 'east_mainline_TTT_veh_h', 'whole_network_TTT_veh_h',
              'external_wait_veh_h', 'whole_network_TTS_including_external_veh_h',
              'Omega_TTD_events', 'Omega_end_n', 'native_removed', 'uninserted_at_end',
              'unresolved_Omega_disappearances', 'unresolved_network_disappearances')
    deltas = {key: vsl[key] - nc[key] for key in fields}
    percentages = {key: 100 * deltas[key] / nc[key] if nc[key] else None
                   for key in ('Omega_TTT_veh_h', 'east_mainline_TTT_veh_h',
                               'whole_network_TTS_including_external_veh_h')}
    summary = {'passed': True, 'seed': seed, 'control_start_sec': 900, 'terminal_sec': 9000,
               'native_validation': validations, 'pre900_raw_prefixes': prefixes,
               'pre900_raw_prefixes_equal': True, 'performance': performance,
               'delta_vsl_minus_none': deltas, 'percent_change_vsl_minus_none': percentages,
               'scope': {'Omega_TTT': 'Canonical freeway plus protected urban area; excludes demand waiting outside the network.',
                         'east_mainline_TTT': 'East mainline links only; excludes on/off-ramp connector residence. This is not the reported east-local 6.15% measure.',
                         'whole_network_TTS': 'Native TravTmTot + DelayLatent, converted from vehicle-seconds to vehicle-hours.'},
               'interpretation': 'Negative TTT/TTS delta means lower cost. Review removals, uninserted demand, remaining stock, and unresolved disappearances alongside costs; one seed does not establish general benefit.',
               'sampling': 'One closed-file FZP pass per arm; 5-second observations with final tail stock held by the existing Omega accounting.'}
    compare.table(output / 'performance.csv', performance)
    compare.figures(geometry, seed=seed)
    compare.save(output / 'summary.json', summary)
    print(f"COMPLETE: whole-network TTS delta {deltas['whole_network_TTS_including_external_veh_h']:+.6f} veh h; "
          f"Omega TTT delta {deltas['Omega_TTT_veh_h']:+.6f} veh h. {output / 'summary.json'}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-root', type=Path, required=True, help='Completed pair folder created by native.py')
    parser.add_argument('--output', type=Path, required=True, help='New analysis directory; existing outputs are refused')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    try:
        analyze(args.native_root.resolve(), args.output.resolve())
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        parser.exit(1, f'Analysis failed: {exc}\n')


if __name__ == '__main__':
    main()
