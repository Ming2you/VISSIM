"""Serial 1050s physical fixed-command experiment; use only after native gates.

Preparation status: small stdlib fixture checks only; live gates remain required.
No adapter copy. Only the canonical PowerShell watchdog launches VISSIM.
Without --execute this prints a plan, performs no validation, and launches nothing.
On any failure preserve all files and the batch lock; never start the next arm.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ARMS = ('baseline', 'lcd10635_2000', 'upstream1135')
FLAT = ROOT / 'diagnostics/fixed_beta300v3_network_arms_flat_v1'
PROFILE = ROOT / 'diagnostics/fixed_beta300v3_900_signal_profile'
WRITER = ROOT / 'diagnostics/fixed_beta300v3_profile_invocation_v2'
WRITER_SHA = '5130a95a36b1ccb2f0e1fc02c042979b7f0e17fa0b1d18f3cb0eae0bd295a7c3'
CONFIG_SHA = '304bba9e24d936e76b9c2a1c49ae977f49aeb60e408c4f27581fc9a774812970'
CSV900_SHA = 'becee44cef1cfd96fc0dc7be4be70b3a424210a362f52d87aa9ee70388e9940a'
WARM_SHA = '76fb1f0a6a47fe87bbeaff0f7082e2433fa357242052ea25e609211f9297871d'
RUNNER = ROOT / 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
DEFAULT_PYTHON = Path(r'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
FILES = {
    'Tuning': PROFILE / 'config.json',
    'Calibration': ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json',
    'Mapping': ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json',
    'VbsConfig': ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs',
    'UrbanInputGateMap': ROOT / 'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv',
    'VehicleInputRoles': ROOT / 'evaluation/real_world_modi_inventory/vehicle_input_roles.csv',
    'DemandProfile': ROOT / 'evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv',
}
ENVIRONMENT = {
    'PYTHONUTF8': '1', 'RW_OFFSET_WRITER': 'test_only',
    'RW_SIGNAL_READBACK_SEC': '1', 'RW_SIGNAL_WRITE_ON_CHANGE': '0',
    'RW_VEHREC_RESOLUTION': '1', 'RW_VEHICLE_ROUTES': '1',
    'RW_FORCE_STEPWISE': '1', 'RW_QUEUE_COUNTER': '1', 'RW_QUEUE_WINDOW': '1',
}
ADDRESS = ('kind', 'id', 'dsd_no', 'sc_no', 'link', 'lane')
NUMERIC = set(('dsd_no', 'sc_no', 'link', 'lane', 'speed_kph', 'p1_green',
               'p2_green', 'p3_green', 'p4_green', 'offset', 'rate_vph', 'green_sec'))
PHYSICAL_COLUMNS = NUMERIC | {'kind', 'id'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def workspace_path(value):
    path = Path(value)
    path = (path if path.is_absolute() else ROOT / path).resolve()
    require(path.is_relative_to(ROOT), 'Input outside this workspace: ' + str(path))
    return path


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, obj):
    # Only this new batch's own status is replaced; original evidence is copied.
    data = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    temp = path.with_suffix('.json.tmp')
    with temp.open('xb') as stream:
        stream.write(data)
    os.replace(temp, path)


def pin(pins, path, expected=None):
    path = workspace_path(path)
    actual = sha(path)
    require(expected is None or actual == str(expected).lower(), 'Source SHA mismatch: ' + relative(path))
    key = relative(path)
    require(key not in pins or pins[key] == actual, 'Conflicting source pins: ' + key)
    pins[key] = actual
    return actual


def assert_pins(pins):
    changed = [key for key, value in pins.items() if not (ROOT / key).is_file() or sha(ROOT / key) != value]
    require(not changed, 'Pinned inputs changed: ' + repr(changed))


def csv_rows(path):
    return list(csv.DictReader(io.StringIO(Path(path).read_text(encoding='utf-8-sig'))))


def physical_rows(rows):
    """All nonmetadata physical columns, unique physical address, exact decimals."""
    out = {}
    for row in rows:
        require(None not in row, 'Malformed CSV row')
        require(PHYSICAL_COLUMNS <= row.keys(), 'Missing physical CSV column')
        require(all(row[key] is not None for key in PHYSICAL_COLUMNS), 'Truncated physical CSV row')
        normalized = {}
        for key, value in row.items():
            if key in ('metadata', 'sim_sec', 'readback'):
                continue
            value = '' if value is None else str(value)
            if key in NUMERIC and value != '':
                value = Decimal(value)
                require(value.is_finite(), 'Nonfinite command value')
            normalized[key] = value
        address = tuple(normalized.get(key, '') for key in ADDRESS)
        require(address not in out, 'Duplicate physical CSV address: ' + repr(address))
        out[address] = normalized
    return out


def powershell():
    return Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'


def process_inventory(*, timeout_sec=30):
    """Read-only single-license gate. Never terminate unrelated or owned processes."""
    code = ("$ErrorActionPreference='Stop'; @([System.Diagnostics.Process]::GetProcesses() | "
            "Where-Object { $_.ProcessName -match '^(VISSIM.*|cscript|wscript)$' } | "
            "ForEach-Object { [ordered]@{pid=$_.Id;name=$_.ProcessName;"
            "start_utc=$_.StartTime.ToUniversalTime().ToString('o')} }) | ConvertTo-Json -Compress")
    result = subprocess.run([str(powershell()), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', code],
                            check=True, capture_output=True, text=True, timeout=timeout_sec,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    value = json.loads(result.stdout.strip() or '[]')
    return value if isinstance(value, list) else [value]


def post_watchdog_process_gate(exit_code, *, timeout_sec=30.0, poll_sec=0.5):
    """Wait only for initial observed identities to exit naturally; never kill.

    The first inventory query is inside the deadline. Subsequent query timeout
    and sleep are capped by its remaining budget. Only an empty observation
    after watchdog exit0 permits the next arm; new PID/start identities fail.
    This is sampled evidence, not a lock against unrelated process creation.
    """
    require(0 < timeout_sec <= 30 and 0 < poll_sec <= timeout_sec, 'Invalid natural-exit wait bound')
    report = {'schema': 'fixed-watchdog-natural-exit/v1', 'watchdog_exit_code': exit_code,
              'valid': False, 'status': 'watchdog_failed_no_wait', 'wait_limit_sec': timeout_sec,
              'wait_elapsed_sec': 0.0, 'initial_processes': None, 'final_processes': None,
              'observations': [], 'new_identities': [], 'process_termination_performed': False}
    if type(exit_code) is not int or exit_code != 0:
        return report
    started = time.monotonic()
    report['started_utc'] = utc()
    initial = None
    while True:
        remaining = timeout_sec - (time.monotonic() - started)
        if remaining <= 0:
            report['status'] = 'initial_processes_did_not_exit_before_deadline'
            break
        try:
            inventory = process_inventory(timeout_sec=remaining)
            require(isinstance(inventory, list), 'Invalid process inventory container')
            snapshot = [dict(row) for row in inventory]
            report['observations'].append({'elapsed_sec': time.monotonic() - started,
                                           'observed_utc': utc(), 'processes': snapshot})
            report['final_processes'] = snapshot
            identities = set()
            for row in snapshot:
                require(type(row.get('pid')) is int and row['pid'] > 0,
                        'Invalid process PID identity')
                require(type(row.get('start_utc')) is str and row['start_utc'],
                        'Missing process creation-time identity')
                parsed = datetime.fromisoformat(row['start_utc'].replace('Z', '+00:00'))
                require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0,
                        'Process creation time is not UTC')
                require(type(row.get('name')) is str and re.fullmatch(r'(VISSIM.*|cscript|wscript)', row['name'], re.I),
                        'Unexpected process inventory name')
                identity = (row['pid'], row['start_utc'])
                require(identity not in identities, 'Duplicate process identity in inventory')
                identities.add(identity)
            if initial is None:
                initial = identities
                report['initial_processes'] = snapshot
            unexpected = identities - initial
            if unexpected:
                report['new_identities'] = [row for row in snapshot if (row['pid'], row['start_utc']) in unexpected]
                report['status'] = 'new_process_identity_observed'
                break
            if not snapshot:
                report.update(valid=True, status='empty_process_inventory')
                break
        except Exception as exc:
            report.update(status='process_inventory_failed', error=f'{type(exc).__name__}: {exc}')
            break
        remaining = timeout_sec - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(min(poll_sec, remaining))
    report['wait_elapsed_sec'] = time.monotonic() - started
    return report


def child_environment(python):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('RW_')
           and k.upper() not in ('PYTHONPATH', 'PYTHONSTARTUP', 'PYTHONPROFILEIMPORTTIME', 'NUMSIM_REPO_ROOT', 'PSMODULEPATH')}
    env.update(ENVIRONMENT)
    env['RW_PYTHON'] = str(python)
    env['NUMSIM_REPO_ROOT'] = str(ROOT / 'vendor/NumSim-mine')
    # Python-launched Windows PowerShell can inherit incompatible Core modules.
    # Use its own built-in modules, including the Get-FileHash provenance cmdlet.
    env['PSMODULEPATH'] = str(powershell().parent / 'Modules')
    return env


def validate_powershell_runtime(env):
    literal = str(FILES['Tuning']).replace("'", "''")
    code = ("$ErrorActionPreference='Stop'; [ordered]@{"
            "version=$PSVersionTable.PSVersion.ToString();"
            "module_path=$env:PSModulePath;sha256=(Get-FileHash -LiteralPath '"
            + literal + "' -Algorithm SHA256).Hash.ToLowerInvariant()} | ConvertTo-Json -Compress")
    result = subprocess.run([str(powershell()), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', code],
                            env=env, capture_output=True, timeout=30,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    require(result.returncode == 0 and not result.stderr.strip(), 'Windows PowerShell hash preflight failed')
    proof = json.loads(result.stdout.decode('ascii'))
    require(proof.get('sha256') == CONFIG_SHA, 'Windows PowerShell returned an invalid provenance hash')
    return proof


def arm_command(name, arm, run):
    command = [str(powershell()), '-NoLogo', '-NoProfile', '-NonInteractive',
               '-ExecutionPolicy', 'Bypass', '-File', str(RUNNER),
               '-Name', name, '-Controller', 'diagnostic-signal-profile',
               '-Network', str(FLAT / (arm + '.inpx')), '-OutDir', str(run)]
    for key, path in FILES.items():
        command.extend(['-' + key, str(path)])
    command += ['-DemandScale', '1', '-SimPeriod', '1050', '-Seed', '13',
                '-ControlIntervalSec', '150', '-ControlStartSec', '900',
                '-WarmupController', 'no-control', '-StateLogIntervalSec', '30',
                '-StartupStallSec', '300', '-StallSec', '300', '-MaxAttempts', '1',
                '-NoGlobalKill', '-ForceStepwise', '-AuditAnchorsSec', '900,1050']
    return command


def single_fzp(run):
    files = list(run.rglob('*.fzp'))
    require(len(files) == 1, 'Expected exactly one complete FZP per run: ' + str(run))
    path = files[0].resolve()
    require(path.is_relative_to(run.resolve()) and path.stat().st_size > 0,
            'Empty or out-of-run FZP')
    return path


def compare_trajectory_files(actual, reference, *, expected_reference_sha256):
    """Stream existing ordered FZP payload helper only at execution time.

    Whole-file hashes identify immutable files; equality excludes the pre-data
    run/date preamble but includes the exact $VEHICLE header and every data byte.
    The outer stat check also covers the helper's final whole-file hash pass.
    """
    from diagnostics.audit_observed_nc_trajectory import payload

    records = []
    for path in (actual, reference):
        before = path.stat()
        result = payload(path)
        after = path.stat()
        require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'FZP changed during full payload/hash read')
        records.append(result)
    require(records[1]['file_sha256'] == expected_reference_sha256, 'Original FZP changed since preflight pin')
    fields = ('header', 'payload_sha256', 'payload_bytes', 'rows', 'first_sec', 'last_sec')
    differences = [key for key in fields if records[0][key] != records[1][key]]
    endpoint_valid = all(record['rows'] > 0 and record['payload_bytes'] > 0
                         and Decimal(str(record['first_sec'])).is_finite()
                         and 0 <= record['first_sec'] < 1050 and record['last_sec'] == 1050 for record in records)
    return {'schema': 'fixed-beta300v3-baseline-trajectory/v1',
            'valid': not differences and endpoint_valid, 'actual': records[0], 'reference': records[1],
            'compared_fields': list(fields), 'different_fields': differences, 'terminal1050_valid': endpoint_valid,
            'ordered_payload_exact': not differences, 'whole_file_identity_required': False,
            'excluded': 'Only bytes before the $VEHICLE header (run/date/preamble)',
            'reference_unchanged_since_preflight': True,
            'meaning': 'Every ordered recorded physical FZP data byte and its column header must match before a treatment may start.'}


def validate_baseline_trajectory(run, name, reference):
    """Require the profile baseline to reproduce the pinned original beta run."""
    reference_run = workspace_path(reference['run'])
    source_provenance = reference_run / ('run_provenance_' + reference['source_run'] + '.json')
    require(sha(source_provenance) == reference['provenance_sha256'], 'Original provenance changed')
    actual_provenance = run / ('run_provenance_' + name + '.json')
    a, b = load(actual_provenance), load(source_provenance)
    expected = {'seed': 13, 'sim_period_sec': 1050, 'control_interval_sec': 150,
                'state_log_interval_sec': 30, 'demand_scale': 1}
    for provenance in (a, b):
        require(all(provenance.get(key) == value for key, value in expected.items()), 'Trajectory provenance/time configuration mismatch')
        require(str(provenance['env'].get('RW_VEHREC_RESOLUTION')) == '1', 'Trajectory must be recorded at native1s cadence')
    require(a['controller'] == 'diagnostic-signal-profile' and b['controller'] == 'wu-link',
            'Wrong baseline/reference controller provenance')
    same_inputs = ('network', 'control_mapping', 'vehicle_input_roles', 'demand_profile', 'urban_input_gate_map')
    require(all(a['files'][key]['sha256'] == b['files'][key]['sha256'] for key in same_inputs),
            'Baseline/reference physical input source SHA mismatch')
    original_fzp = single_fzp(reference_run)
    require(relative(original_fzp) == reference['fzp'], 'Original FZP path changed')
    result = compare_trajectory_files(single_fzp(run), original_fzp,
                                      expected_reference_sha256=reference['fzp_sha256'])
    result['source_run'] = reference['source_run']
    result['provenance_sha256'] = {relative(actual_provenance): sha(actual_provenance),
                                    relative(source_provenance): reference['provenance_sha256']}
    result['matched_physical_input_sha256'] = {key: b['files'][key]['sha256'] for key in same_inputs}
    return result


def validate_gates(args):
    """Gate before any batch/run mkdir, process launch, or simulator ownership."""
    pins = {}
    require(args.native_gate and args.native_gate_sha256, 'Completed native gate and its exact SHA are required')
    require(args.source_manifest and args.source_manifest_sha256, 'Reviewed runtime source manifest and SHA are required')
    native_path = workspace_path(args.native_gate)
    pin(pins, native_path, args.native_gate_sha256)
    native = load(native_path)
    require(native.get('schema') == 'flat-network-native-gate/v1', 'Wrong native gate schema')
    require(native.get('native_load_readback_passed') is True and native.get('source_changes') == [],
            'Native LoadNet/readback gate incomplete or invalid')
    require(native.get('native_vehicle_eligibility_verified') is False,
            'LoadNet-only gate must not claim realized vehicle eligibility')
    require(workspace_path(native['flat_manifest_path']) == FLAT / 'manifest.json', 'Native gate covered a different flat directory')
    preflight_path = native_path.parent / 'preflight.json'
    pin(pins, preflight_path, native['preflight_sha256'])
    for path, expected in load(preflight_path)['pinned_files'].items():
        pin(pins, path, expected)
    flat_path = FLAT / 'manifest.json'
    pin(pins, flat_path, native['flat_manifest_sha256'])
    flat = load(flat_path)
    require(flat.get('schema') == 'fixed-command-flat-network-assets/v1'
            and flat.get('source_changes') == [] and flat.get('data_reference_filesystem_validation') is True,
            'Flat asset manifest invalid')
    require(set(native['arms']) == set(ARMS), 'Native gate must cover all three arms')
    for arm in ARMS:
        row = native['arms'][arm]
        require(all(row.get(k) is True for k in ('native_readback_exact', 'loadnet_passed', 'owned_processes_gone')),
                arm + ': native gate incomplete')
        require(row['network_sha256'] == flat['outputs'][arm + '.inpx']['destination_sha256'],
                arm + ': native gate covers different network')
        readback = workspace_path(row['readback_csv_path'])
        require(readback.parent == native_path.parent / arm, 'Native readback is outside its arm evidence directory')
        pin(pins, readback, row['readback_csv_sha256'])
        pin(pins, native_path.parent / arm / 'process.json', row['process_manifest_sha256'])
    expected_assets = {arm + '.inpx' for arm in ARMS} | {k for k in flat['outputs'] if k.lower().endswith('.sig')} | {'개포동 Test-bed.jpg'}
    require(set(flat['outputs']) == expected_assets and len(expected_assets) == 46, 'Unexpected flat asset set')
    for name, row in flat['outputs'].items():
        path = (FLAT / name).resolve()
        require(path.parent == FLAT.resolve(), 'Flat filename escaped directory')
        pin(pins, path, row['destination_sha256'])
    source_path = workspace_path(args.source_manifest)
    pin(pins, source_path, args.source_manifest_sha256)
    source = load(source_path)
    require(isinstance(source.get('source_sha256'), dict) and source['source_sha256'], 'Runtime source manifest is empty')
    for path, expected in source['source_sha256'].items():
        pin(pins, path, expected)
    pin(pins, WRITER / 'validation.json', WRITER_SHA)
    writer = load(WRITER / 'validation.json')
    require(writer.get('passed') is True and writer.get('exit_code') == 0
            and writer.get('source_unchanged') is True and writer.get('fake_readback_exact') is True,
            'Canonical writer/invocation gate incomplete')
    for path, expected in writer['source_sha256'].items():
        pin(pins, path, expected)
    profile = load(PROFILE / 'manifest.json')
    pin(pins, PROFILE / 'manifest.json')
    require(profile['schema'] == 'fixed-beta300v3-900-signal-profile/v1', 'Wrong fixed profile schema')
    for path, expected in profile['source_sha256'].items():
        pin(pins, path, expected)
    for row in profile['outputs'].values():
        pin(pins, row['path'], row['sha256'])
    pin(pins, FILES['Tuning'], CONFIG_SHA)
    for path in FILES.values():
        pin(pins, path)
    for path in (RUNNER, Path(__file__), ROOT / 'diagnostics/signal_readback_cadence.py',
                 ROOT / 'diagnostics/live_beta0_first_interval_audit.py',
                 ROOT / 'diagnostics/run_area_production_preflight.py',
                 ROOT / 'diagnostics/audit_observed_nc_trajectory.py',
                 ROOT / 'evaluation/controllers/signal_timing_oracle.py'):
        pin(pins, path)
    require(re.fullmatch(r'[A-Za-z0-9_-]+', profile['source_run']), 'Unsafe original source run')
    original_run = ROOT / 'evaluation/runs' / profile['source_run']
    original_dir = original_run / ('decisions_' + profile['source_run'])
    refs = {1: original_dir / 'action_000001.csv', 900: original_dir / 'action_000900.csv'}
    for sec, expected_sha, count in ((1, WARM_SHA, 74), (900, CSV900_SHA, 213)):
        pin(pins, refs[sec], expected_sha)
        actual = WRITER / f'action_{sec:06d}.csv'
        result = next(row for row in writer['commands'] if row['time'] == sec)
        require(result['source_sha256'] == expected_sha and result['rows'] == count
                and result['nonmetadata_column_differences'] == [], 'Writer command report mismatch')
        pin(pins, actual, result['actual_sha256'])
        require(physical_rows(csv_rows(actual)) == physical_rows(csv_rows(refs[sec])), 'Writer physical CSV mismatch')
    provenance = original_run / ('run_provenance_' + profile['source_run'] + '.json')
    require(relative(provenance) in profile['source_sha256'], 'Original provenance missing from profile source proof')
    original_fzp = single_fzp(original_run)
    reference = {'source_run': profile['source_run'], 'run': relative(original_run),
                 'provenance_sha256': pin(pins, provenance, profile['source_sha256'][relative(provenance)]),
                 'fzp': relative(original_fzp), 'fzp_sha256': pin(pins, original_fzp)}
    # The large reference is first read here, never in preparation or plan mode.
    # It joins the source pins checked before/after every arm and on failure.
    return pins, native, flat, refs, reference


def validate_run(run, name, arm, expected_network, refs):
    # Import only existing pure readback/oracle helpers, never an adapter or solver.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from diagnostics.signal_readback_cadence import strict_signal_trace, vsl_readback_matches
    from evaluation.controllers.signal_timing_oracle import decisions_from_action_rows

    decision_dir = run / ('decisions_' + name)
    provenance_path = run / ('run_provenance_' + name + '.json')
    provenance = load(provenance_path)
    for key, value in {'seed': 13, 'sim_period_sec': 1050, 'control_interval_sec': 150,
                       'state_log_interval_sec': 30, 'startup_stall_sec': 300,
                       'demand_scale': 1, 'controller': 'diagnostic-signal-profile'}.items():
        require(provenance.get(key) == value, 'Run provenance mismatch: ' + key)
    require(provenance['files']['network']['sha256'] == expected_network, 'Run used wrong network SHA')
    require(provenance['files']['tuning']['sha256'] == CONFIG_SHA, 'Run used wrong profile')
    for key, value in ENVIRONMENT.items():
        if key.startswith('RW_') and key != 'RW_FORCE_STEPWISE':
            require(str(provenance['env'].get(key)) == value, 'Run environment mismatch: ' + key)
    log = (run / ('runlog_' + name + '.txt')).read_text(encoding='utf-8-sig', errors='replace')
    require('STAGE=SIM_DONE' in log, 'Missing SIM_DONE')
    require(not any(token in log for token in ('ERROR=', 'DIAGNOSTIC_DECISION_FAILED', 'STRICT_DECISION_FAILED')),
            'Runner reported an error; preserve and inspect')
    states = csv_rows(run / ('state_' + name + '.csv'))
    require(states and max(Decimal(row['sim_sec']) for row in states) == Decimal(1050), 'Run did not finish at exactly1050')
    require(not any('fallback' in row.get('controller_status', '').lower() for row in states), 'Fallback status in run')
    commands = []
    for sec in (1, 150, 300, 450, 600, 750, 900, 1050):
        path = decision_dir / f'action_{sec:06d}.csv'
        reference = refs[1 if sec < 900 else 900]
        rows = csv_rows(path)
        require(physical_rows(rows) == physical_rows(csv_rows(reference)), 'Fixed command mismatch at ' + str(sec))
        action = load(path.with_suffix('.json'))
        meta = {**action.get('diagnostics', {}), **action.get('metadata', {})}
        require(meta.get('controller_status') == 'ok' and not meta.get('controller_error'), 'Decision failed at ' + str(sec))
        if sec >= 900:
            require(meta.get('diagnostic_signal_profile_active') == 1, 'Wrong controller mode')
        commands.append({'sim_sec': sec, 'path': relative(path), 'sha256': sha(path), 'rows': len(rows), 'physical_exact': True})
    rows900 = csv_rows(decision_dir / 'action_000900.csv')
    parsed = decisions_from_action_rows([{**row, 'sim_sec': 900} for row in rows900])
    require(len(parsed) == 1 and len(parsed[0]['controllers']) == 17, 'Expected seventeen signal controllers')
    ramps = {str(int(row['sc_no'])): float(row['green_sec']) for row in rows900 if row['kind'] == 'ramp_meter'}
    signal_path = decision_dir / 'signal_readback.csv'
    readback = strict_signal_trace(csv_rows(signal_path), parsed[0]['controllers'], ramps, start=900, end=1050)
    require(readback['valid'], 'Strict900–1050 signal/ramp readback failed')
    action_log = run / ('action_' + name + '.csv')
    log900 = [row for row in csv_rows(action_log) if Decimal(row['sim_sec']) == Decimal(900)]
    require(physical_rows(log900) == physical_rows(rows900), 'Actual applied213 rows differ from action CSV')
    vsl = [row for row in log900 if row['kind'] == 'vsl']
    require(len(vsl) == 66 and all(vsl_readback_matches(row) for row in vsl), 'VSL applied readback failed')
    raw_paths = [decision_dir / f'state_{sec:06d}.json' for sec in (900, 1050)]
    for sec, path in zip((900, 1050), raw_paths):
        raw = load(path)
        require(raw.get('sim_sec') == sec, 'Raw snapshot time mismatch')
        envelope = raw.get('vehicle_routes')
        require(isinstance(envelope, dict) and envelope.get('complete') is True, 'Missing completed vehicle route collection')
    native_outputs = {suffix: [{'path': relative(path), 'bytes': path.stat().st_size}
                             for path in sorted(run.rglob('*' + suffix))] for suffix in ('.fzp', '.lsa', '.err')}
    require(all(native_outputs[suffix] and all(row['bytes'] > 0 for row in native_outputs[suffix])
                for suffix in ('.fzp', '.lsa')), 'Native FZP/LSA outputs absent or empty')
    return {'status': 'execution_and_command_readback_passed', 'commands': commands,
            'signal_ramp_readback': readback, 'vsl_apply_readback_rows': len(vsl),
            'raw_states': [{'path': relative(p), 'sha256': sha(p)} for p in raw_paths],
            'readback_sources': {relative(p): sha(p) for p in (signal_path, action_log, provenance_path)},
            'native_outputs': native_outputs, 'native_large_files_hashed_or_scanned': False,
            'window': {'start': 900, 'end': 1050, 'include_post_step1050': True, 'include_immediate1050': False},
            'trajectory_equivalence_or_performance_claim': False,
            'native_vehicle_eligibility_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True, help='New batch identifier; no run/diagnostic directory may already exist')
    parser.add_argument('--native-gate', default='diagnostics/flat_network_native_readback_v3/native_gate.json')
    parser.add_argument('--native-gate-sha256')
    parser.add_argument('--source-manifest')
    parser.add_argument('--source-manifest-sha256')
    parser.add_argument('--reuse-baseline-manifest', help='Reuse only a previously passed baseline after full revalidation')
    parser.add_argument('--reuse-baseline-manifest-sha256')
    parser.add_argument('--python', type=Path, default=DEFAULT_PYTHON)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,48}', args.name), 'Unsafe/new batch name required')
    batch = ROOT / 'diagnostics/fixed_beta300v3_experiments' / args.name
    rows = []
    for arm in ARMS:
        name = f'codex_fixed_beta300v3_{args.name}_{arm}_s13'
        run = ROOT / 'evaluation/runs' / name
        rows.append({'arm': arm, 'name': name, 'run': relative(run),
                     'command': arm_command(name, arm, run), 'status': 'pending', 'completed': False, 'valid': False})
    if not args.execute:
        print(json.dumps({'schema': 'fixed-beta300v3-three-arm-plan/v1', 'validated': False,
                          'executed': False, 'arms': rows, 'batch': relative(batch)}, ensure_ascii=False, indent=2))
        return 0
    require(os.name == 'nt' and args.python.is_file(), 'Windows and existing canonical Python are required')
    for row in rows:
        longest = ROOT / row['run'] / ('decisions_' + row['name']) / 'action_001050.json'
        require(len(str(longest)) < 240, 'Batch name exceeds conservative legacy VBS path limit; choose a shorter name')
    require(not batch.exists() and all(not (ROOT / row['run']).exists() for row in rows), 'Existing outputs; choose a new batch')
    require(bool(args.reuse_baseline_manifest) == bool(args.reuse_baseline_manifest_sha256), 'Baseline reuse requires its exact manifest SHA')
    env = child_environment(args.python.resolve())
    powershell_proof = validate_powershell_runtime(env)
    pins, native, flat, refs, reference = validate_gates(args)
    if args.reuse_baseline_manifest:
        old_path = workspace_path(args.reuse_baseline_manifest)
        pin(pins, old_path, args.reuse_baseline_manifest_sha256)
        old = load(old_path)
        require(old.get('schema') == 'fixed-beta300v3-three-arm-experiment/v1'
                and old.get('source_changes') == [] and old.get('baseline_trajectory_reference') == reference
                and old.get('native_gate_sha256') == args.native_gate_sha256,
                'Baseline source batch/reference differs')
        prior = old['arms'][0]
        require(prior.get('arm') == 'baseline' and prior.get('status') == 'passed'
                and prior.get('valid') is True and prior.get('completed') is True
                and prior.get('exit_code') == 0 and prior.get('post_run_processes') == [],
                'Only an already passed baseline may be reused')
        runtime = load(workspace_path(args.source_manifest))['source_sha256']
        historical = {relative(workspace_path(p)): h for p, h in old['source_sha256'].items()}
        require(all(historical.get(relative(workspace_path(p))) == h for p, h in runtime.items()),
                'Baseline used different runtime sources')
        old_run = workspace_path(prior['run'])
        require(old_run.parent == ROOT / 'evaluation/runs' and old_run.name == prior['name'],
                'Reused baseline run identity differs')
        checked = validate_run(old_run, prior['name'], 'baseline',
                               flat['outputs']['baseline.inpx']['destination_sha256'], refs)
        trajectory = validate_baseline_trajectory(old_run, prior['name'], reference)
        require(trajectory['valid'] and trajectory == prior.get('baseline_trajectory_comparison'),
                'Reused baseline full trajectory certificate changed')
        rows[0] = {**prior, 'validation': checked, 'reused_from': relative(old_path),
                   'reused_manifest_sha256': args.reuse_baseline_manifest_sha256,
                   'revalidated_utc': utc()}
        for item in checked['commands'] + checked['raw_states']:
            pin(pins, item['path'], item['sha256'])
        for path, expected in checked['readback_sources'].items():
            pin(pins, path, expected)
        pin(pins, trajectory['actual']['path'], trajectory['actual']['file_sha256'])
    require(not process_inventory(), 'Existing VISSIM/cscript/wscript process: single-license execution blocked')
    lock = ROOT / 'diagnostics/fixed_beta300v3_experiment.lock'
    lock_bytes = json.dumps({'pid': os.getpid(), 'created_utc': utc(), 'batch': relative(batch)}).encode('utf-8')
    with lock.open('xb') as stream:
        stream.write(lock_bytes)
    batch.mkdir(parents=True, exist_ok=False)
    manifest = {'schema': 'fixed-beta300v3-three-arm-experiment/v1', 'started_utc': utc(),
                'status': 'running', 'completed': False, 'valid': False, 'arms': rows, 'source_sha256': pins,
                'native_gate': relative(workspace_path(args.native_gate)),
                'native_gate_sha256': args.native_gate_sha256, 'native_vehicle_eligibility_verified': False,
                'environment': {k: v for k, v in env.items() if k.startswith('RW_') or k in ('PYTHONUTF8', 'PYTHONHASHSEED', 'NUMSIM_REPO_ROOT', 'PSMODULEPATH')},
                'powershell_provenance_hash_preflight': powershell_proof,
                'python_executable': {'path': str(args.python.resolve()), 'sha256': sha(args.python)},
                'inherited_RW_environment_cleared': True, 'serial_single_license': True,
                'source_changes': [], 'driver_performs_process_termination': False,
                'baseline_trajectory_reference': reference,
                'scope': 'Fixed physical command experiment; optional model contracts OFF; adapter prediction is not evidence.'}
    save(batch / 'manifest.json', manifest)
    try:
        for path in (workspace_path(args.native_gate), workspace_path(args.source_manifest),
                     PROFILE / 'manifest.json', WRITER / 'validation.json'):
            destination = batch / (('native_' if path == workspace_path(args.native_gate) else
                                    'runtime_' if path == workspace_path(args.source_manifest) else
                                    'profile_' if path.parent == PROFILE else 'writer_') + path.name)
            with destination.open('xb') as stream:
                stream.write(path.read_bytes())
        for row in rows:
            if row.get('reused_from'):
                assert_pins(pins)
                continue
            if row['arm'] != 'baseline':
                require(rows[0].get('baseline_trajectory_comparison', {}).get('valid') is True,
                        'Original full-payload baseline equivalence has not passed; no treatment')
            assert_pins(pins)
            require(not process_inventory(), 'License/process survivor before next arm; stop')
            run = ROOT / row['run']
            require(not run.exists(), 'Run directory appeared; refuse overwrite')
            run.mkdir(parents=True, exist_ok=False)
            save(run / 'fixed_command_source_manifest.json', {'batch': relative(batch), 'source_sha256': pins})
            row.update(status='running', started_utc=utc())
            save(batch / 'manifest.json', manifest)
            started = time.monotonic()
            with (run / 'watchdog_stdout.txt').open('xb') as stdout, (run / 'watchdog_stderr.txt').open('xb') as stderr:
                proc = subprocess.Popen(row['command'], cwd=ROOT, env=env, stdout=stdout, stderr=stderr,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                row['watchdog_pid'] = proc.pid
                save(batch / 'manifest.json', manifest)
                # Canonical watchdog owns startup300/stall300 and PID+StartTime cleanup.
                # This driver does not kill Python/VISSIM or retry a failed arm.
                row['exit_code'] = proc.wait()
            row.update(elapsed_sec=time.monotonic() - started, finished_utc=utc(), completed=True)
            row['post_run_natural_exit'] = post_watchdog_process_gate(row['exit_code'])
            row['post_run_processes'] = row['post_run_natural_exit']['final_processes']
            require(row['post_run_natural_exit']['valid'],
                    'Watchdog failed or process exit gate failed; stop all subsequent arms')
            assert_pins(pins)
            row['validation'] = validate_run(run, row['name'], row['arm'],
                                             flat['outputs'][row['arm'] + '.inpx']['destination_sha256'], refs)
            if row['arm'] == 'baseline':
                row['baseline_trajectory_comparison'] = validate_baseline_trajectory(run, row['name'], reference)
                # Save both payload hashes/counts/header/terminal comparison even
                # on mismatch, before the failure stops every treatment arm.
                save(batch / 'manifest.json', manifest)
                require(row['baseline_trajectory_comparison']['valid'],
                        'Baseline differs from original beta300v3 full FZP payload; stop before treatments')
            row['network_sha256'] = flat['outputs'][row['arm'] + '.inpx']['destination_sha256']
            row.update(status='passed', valid=True)
            save(batch / 'manifest.json', manifest)
        assert_pins(pins)
        manifest.update(status='all_three_execution_and_readback_passed', completed=True, valid=True, finished_utc=utc())
        save(batch / 'manifest.json', manifest)
        require(lock.read_bytes() == lock_bytes, 'Lock identity changed; preserve it')
        lock.unlink()  # This exact driver's own lock, only after all arms succeeded.
        return 0
    except BaseException as exc:
        manifest.update(status='failed_preserved_stop', valid=False, finished_utc=utc(), error=f'{type(exc).__name__}: {exc}')
        manifest['source_changes'] = [key for key, value in pins.items() if not (ROOT / key).is_file() or sha(ROOT / key) != value]
        save(batch / 'manifest.json', manifest)
        print(f'FAILED_PRESERVED: {batch / "manifest.json"}; no next arm and no cleanup by driver', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
