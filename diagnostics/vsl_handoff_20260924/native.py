"""Prepare the frozen native NC/VSL90 pair; never launch VISSIM automatically."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def checked_asset(root, relative, expected):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Asset path is outside its declared root: {relative}')
    if sha(path) != expected:
        raise ValueError(f'Asset SHA256 mismatch: {relative}')
    return path


def network_for_seed(original, seed):
    pattern = rb'(<simulation\b[^>]*\brandSeed=")([0-9]+)(")'
    matches = list(re.finditer(pattern, original))
    if len(matches) != 1 or matches[0][2] != b'29':
        raise ValueError('Expected exactly one saved seed29 simulation')
    changed = re.sub(pattern, lambda m: m[1] + str(seed).encode('ascii') + m[3], original)
    restored = re.sub(pattern, lambda m: m[1] + b'29' + m[3], changed)
    if restored != original:
        raise ValueError('Changing the seed modified other network bytes')
    return changed


def powershell_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def prepare(output, seed, start, end):
    if output.exists():
        raise FileExistsError(f'Output already exists; choose a new directory: {output}')
    if seed < 1 or seed > 2147483647:
        raise ValueError('Seed must be an integer between 1 and 2147483647')
    if (start, end) not in ((900, 3000), (900, 9000), (2250, 3000)):
        raise ValueError('Supported start/end pairs are 900/3000, 900/9000, and 2250/3000')
    assets = json.loads((HERE / 'assets.json').read_text(encoding='utf-8-sig'))
    native = assets['network']
    source = checked_asset(HERE, native['file'], native['sha256'])
    originals = {name: checked_asset(HERE, spec['file'], spec['sha256'])
                 for name, spec in assets['sidecars'].items()}
    background = assets['background']
    originals[background['name']] = checked_asset(ROOT, background['repository_path'], background['sha256'])
    original = source.read_bytes()
    referenced = {value[6:] for node in ET.fromstring(original).iter()
                  for value in node.attrib.values() if value.startswith('#data#')}
    if referenced != set(originals) or any(Path(name).name != name for name in originals):
        raise ValueError('The asset manifest must exactly cover native sibling references')
    changed = network_for_seed(original, seed)
    sys.path.insert(0, str(ROOT))
    from diagnostics.fast_fixed_profile import prepare as prepare_fixed

    output.mkdir(parents=True, exist_ok=False)
    source_folder = output / 'source'
    source_folder.mkdir()
    for name, asset in originals.items():
        shutil.copy2(asset, source_folder / name)
    plans = {}
    pins = {}
    for arm in ('none', 'vsl'):
        network = source_folder / f'vsl_seed{seed}_{arm}.inpx'
        network.write_bytes(changed)
        profile = {'schema': 'native-fixed-profile/v1', 'network_sha256': sha(network),
                   'seed': seed, 'control_start_sec': start, 'terminal_sec': end,
                   'vehicle_record_interval_sec': 5, 'native_resolution_probe': 10,
                   'vsl_commands': [{'time_s': start, 'dsd_no': dsd, 'speed_id': 90}
                                    for dsd in range(63, 67)] if arm == 'vsl' else [],
                   'meter_commands': []}
        if start == 2250:
            profile['native_off_service_anchor_green_sec'] = 10
        if end == 9000:
            profile['collect_native_network_performance'] = True
        profile_path = output / f'{arm}.json'
        save(profile_path, profile)
        prepared = output / f'prepared_{arm}'
        meta = prepare_fixed(network, profile_path, prepared)
        pins.update(meta['snapshot_sha256'])
        pins[str(prepared / 'prepared.json')] = sha(prepared / 'prepared.json')
        plans[arm] = {'prepared': str(prepared), 'profile': profile,
                      'event_rows': meta['fixed_profile_proof']['event_rows']}
    save(output / 'preflight.json', {
        'passed': True, 'seed': seed, 'control_start_sec': start, 'terminal_sec': end,
        'original_seed29_network_sha256': native['sha256'],
        'prepared_source_network_sha256': hashlib.sha256(changed).hexdigest(),
        'only_permitted_network_change': {'saved_seed_from': 29, 'saved_seed_to': seed,
                                         'byte_restoration_passed': True},
        'arms': plans, 'pins': pins,
        'scope': 'NC versus fixed distribution90 on DSD63..66; native urban signals and RM OFF retained.',
        'execution': 'Prepared only. Run run_commands.ps1 explicitly to launch the existing runner sequentially.'})
    commands = f"""# Run from this computer after installing/licensing VISSIM2020 with COM support.
param([string]$Python = {powershell_literal(sys.executable)})
$ErrorActionPreference = 'Stop'
$runner = {powershell_literal(ROOT / 'diagnostics/fast_nc_run.ps1')}
foreach ($arm in @('none', 'vsl')) {{
    $prepared = Join-Path $PSScriptRoot ('prepared_' + $arm)
    $output = Join-Path $PSScriptRoot ($arm + '/run')
    & $runner -Prepared $prepared -Output $output -Seed {seed} -Execute -MinimumFreeGiB 15 -Python $Python
    $receipt = Get-Content -LiteralPath (Join-Path $output 'run.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if (!$receipt.completed -or !$receipt.finished -or $receipt.owned_native_alive) {{
        throw ('Native run did not complete cleanly: ' + $arm)
    }}
}}
"""
    (output / 'run_commands.ps1').write_text(commands, encoding='utf-8-sig')
    print(f'PREPARED: seed{seed}, VSL90 from {start}s, terminal {end}s; no native run started.', flush=True)
    print(f'Run explicitly: {output / "run_commands.ps1"}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('prepare', help='Prepare a fresh NC/VSL pair and explicit run commands')
    command.add_argument('--output', type=Path, required=True, help='New output directory on this computer')
    command.add_argument('--seed', type=int, default=29)
    command.add_argument('--start', type=int, default=900, choices=(900, 2250))
    command.add_argument('--end', type=int, default=9000, choices=(3000, 9000))
    args = parser.parse_args()
    try:
        prepare(args.output.resolve(), args.seed, args.start, args.end)
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        parser.exit(1, f'Preparation failed: {exc}\n')


if __name__ == '__main__':
    main()
