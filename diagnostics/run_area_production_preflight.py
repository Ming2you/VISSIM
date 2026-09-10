"""Run the canonical adapter in a fresh process; no proposal installers or AST.

Default mode prints the exact command. --execute runs only an offline decision.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def process_snapshot():
    command = "$ErrorActionPreference='Stop'; Get-CimInstance Win32_Process | Where-Object { $null -ne $_.CreationDate } | ForEach-Object { [PSCustomObject]@{ pid=[int]$_.ProcessId; parent=[int]$_.ParentProcessId; created=$_.CreationDate.ToUniversalTime().ToString('o') } } | ConvertTo-Json -Compress"
    result = subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True,
                            text=True, encoding='utf-8', timeout=15, check=True)
    return {row['pid']: row for row in json.loads(result.stdout)}


def owned_descendants(snapshot, parent_record, owned):
    parent_pid = parent_record['pid'] if parent_record is not None else None
    parents = {pid for pid, row in owned.items()
               if pid in snapshot and snapshot[pid]['created'] == row['created']}
    if parent_record is not None and snapshot.get(parent_pid, {}).get('created') == parent_record['created']:
        parents.add(parent_pid)
    while True:
        found = {pid for pid, row in snapshot.items() if row['parent'] in parents}
        if found <= parents:
            break
        parents |= found
    for pid in parents - {parent_pid}:
        if pid in snapshot:
            owned[pid] = snapshot[pid]


def stop_exact_process(row):
    # Only terminate a PID if its creation timestamp still identifies our child.
    command = ("$p = Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(int(row['pid'])) + "'; "
               "if ($p -and $p.CreationDate.ToUniversalTime().ToString('o') -eq '" + row['created'] +
               "') { Stop-Process -Id " + str(int(row['pid'])) + " -Force -ErrorAction Stop }")
    subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True,
                   text=True, encoding='utf-8', timeout=15, check=True)


def hashes():
    files = sorted((ROOT / 'evaluation/controllers').glob('*.py'))
    files += [ROOT / 'scripts/run_real_world_stackelberg_controller.vbs',
              ROOT / 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def checked_config(path, beta):
    cfg = json.loads(path.read_text(encoding='utf-8'))
    if 'extends' in cfg:
        raise ValueError('Live/preflight input must be flattened')
    for section, key in [('urban', 'physical_signal_contract'), ('urban', 'conservative_initial_transit'),
                         ('freeway', 'physical_vehicle_counts'), ('freeway', 'local_landing_state')]:
        if cfg[section].get(key) is not True:
            raise ValueError('Missing required flag ' + section + '.' + key)
    signal = cfg['actuation']['real_world_signal_control']
    if signal.get('enabled') is not True or signal.get('offset_writer') != 'experiment':
        raise ValueError('Explicit signal/optimizer offset experiment config required')
    area = cfg['control_area_objective']
    if area.get('enabled') is not True or area.get('beta_seconds') != beta:
        raise ValueError('Explicit area coefficient differs from this run')
    return cfg


def validate_result(payload, beta, controller='wu-link'):
    metadata = payload['metadata']
    required = {'controller_status': 'ok', 'physical_signal_contract_enabled': 1.,
                'offset_writer': 'experiment', 'offset_experiment': 1.,
                'offset_production_writes': 0., 'control_area_endpoint_enabled': 1.,
                'control_area_near_only': 1., 'freeway_physical_vehicle_counts': 1.,
                'control_area_beta_seconds': float(beta),
                'control_area_follower_objective_installed': 1.,
                'control_area_fallback_uses_objective': 1.,
                'control_area_meter_finalization_enabled': 1.,
                'control_area_meter_writer_matches_scored': 1.}
    if controller == 'wu-link':
        required['control_area_leader_objective_only_installed'] = 1.
        required['meta_wu_price_parallel_serial_rerun_count'] = 0.
        required['meta_leader_fallback_guard_metric_ttt'] = 0.
    for key, value in required.items():
        if metadata.get(key) != value:
            raise AssertionError(f'{key}: expected {value!r}, got {metadata.get(key)!r}')
    if not isinstance(metadata.get('offset_written_sec'), dict):
        raise AssertionError('Actual normalized per-signal offset table missing')
    follower = {}
    if controller == 'wu-link':
        diagnostics = payload['diagnostics']
        from evaluation.controllers.area_leader_objective import APPLIED_LEGACY_COSTS
        if diagnostics.get('leader_control_area_objective_only') != 1.:
            raise AssertionError('Leader did not select the pure area endpoint objective')
        for key in APPLIED_LEGACY_COSTS:
            if diagnostics.get(key, 0.) != 0.:
                raise AssertionError('Applied cost outside the area objective: ' + key)
        for key in ('leader_objective_base', 'leader_total_objective'):
            if not math.isclose(diagnostics[key], metadata['leader_objective'], rel_tol=1e-10, abs_tol=1e-8):
                raise AssertionError('Selected leader score differs from endpoint base: ' + key)
        if diagnostics.get('control_area_phase_outer_matches_scored') != 1.:
            raise AssertionError('Outer follower phases did not match the scored phase vector')
        if diagnostics.get('control_area_meter_finalized_before_score') != 1.:
            raise AssertionError('Selected follower meter command was not finalized before scoring')
        marker = diagnostics.get('_control_area_meter_finalized', {})
        if marker.get('realized_rates') != payload.get('ramp_metering'):
            raise AssertionError('Written meter rates differ from the finalized score marker')
        if marker.get('context_sha256') != metadata.get('control_area_meter_context_sha256'):
            raise AssertionError('Writer and score used different meter calibration contexts')
        if marker.get('commands') != {k:v for k,v in diagnostics.items() if k.startswith('rw_meter_')}:
            raise AssertionError('Physical meter greens/hints differ from the finalized score marker')
        follower = {key: value for key, value in diagnostics.items() if key.startswith('control_area_follower_')
                    or key.startswith('control_area_offset_') or key in ('wu_faithful_offsets_off_zero',
                        'wu_faithful_offsets_searched_off_zero', 'wu_faithful_offset_ttt_on', 'wu_faithful_offset_ttt_off')}
        if follower.get('control_area_follower_objective_active') != 1.:
            raise AssertionError('Selected follower did not use the area objective')
        if follower['control_area_follower_additional_cost_veh_h'] != 0.:
            raise AssertionError('Selected follower retained an extra cost outside the area objective')
        actual_j = follower['control_area_follower_objective_veh_h']
        expected_j = (follower['control_area_follower_ttt_veh_h'] - beta / 3600. * follower['control_area_follower_ttd_veh']
                      + follower['control_area_follower_additional_cost_veh_h'])
        if not math.isclose(actual_j, expected_j, rel_tol=1e-10, abs_tol=1e-8):
            raise AssertionError('Selected follower applies an inconsistent area reward')
        if not math.isclose(metadata['nash_objective'], actual_j, rel_tol=1e-10, abs_tol=1e-8):
            raise AssertionError('Nash objective does not carry the selected area score')
    return {key: metadata[key] for key in required} | {
        'decision_wall_sec': metadata['decision_wall_sec'],
        'offset_written_sec': metadata['offset_written_sec'], 'follower_score': follower}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--time', type=int, required=True)
    parser.add_argument('--run', default='codex_n7_pure_s13_20260910',
                        help='Recorded run whose actual state and preceding action are replayed.')
    parser.add_argument('--beta', type=int, choices=(0, 60, 150, 300), required=True)
    parser.add_argument('--controller', choices=('wu-link', 'no-control'), default='wu-link')
    parser.add_argument('--config-directory', default='area_candidate_configs')
    parser.add_argument('--phase-trace', action='store_true', help='Read-only profile of base/outer follower phase vectors; diagnostic overhead applies.')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--timeout-sec', type=float, default=600.)
    args = parser.parse_args()
    if not math.isfinite(args.timeout_sec) or args.timeout_sec <= 0:
        parser.error('--timeout-sec must be finite and positive')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.config_directory):
        parser.error('--config-directory must name a direct diagnostics child')
    cfg_dir = ROOT / 'diagnostics' / args.config_directory
    cfg_path = cfg_dir / f'n7_area_beta{args.beta}.json'
    cfg = checked_config(cfg_path, args.beta)
    run = args.run
    runs_root = (ROOT / 'evaluation/runs').resolve()
    run_path = (runs_root / run).resolve()
    if run_path.parent != runs_root or run_path.name != run or not run_path.is_dir():
        parser.error('--run must name an existing direct child of evaluation/runs')
    decisions = run_path / ('decisions_' + run)
    state = decisions / f'state_{args.time:06d}.json'
    if not state.is_file():
        # No-control runs have no repeated decisions. Their explicitly paused
        # audit anchors use the same complete production state serializer.
        state = decisions / f'anchor_{args.time:06d}.json'
    if not state.is_file():
        parser.error('Requested recorded state does not exist: ' + str(state))
    previous = max((p for p in decisions.glob('action_*.json') if int(p.stem.split('_')[-1]) < args.time),
                   key=lambda p: int(p.stem.split('_')[-1]), default=None)
    tag = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / f'diagnostics/area_production_preflight/{args.controller}_t{args.time}_beta{args.beta}_{tag}'
    command = [sys.executable, '-X', 'utf8', str(ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py'),
               '--state-json', str(state),
               '--out-action-json', str(out / 'action.json'), '--out-action-csv', str(out / 'action.csv'),
               '--mapping-json', str(ROOT / cfg['mapping_json']),
               '--detector-mapping-json', str(ROOT / cfg['detector_mapping_json']),
               '--calibration-json', str(ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
               '--tuning-json', str(cfg_path), '--controller', args.controller]
    if previous is not None:
        command += ['--previous-action-json', str(previous)]
    env = dict(os.environ, RW_OFFSET_WRITER='experiment', PYTHONIOENCODING='utf-8',
               NUMSIM_REPO_ROOT=str(ROOT / 'vendor/NumSim-mine'),
               RW_MAINLINE_SG_ONLY='1' if cfg['urban']['plan']['mainline_only'] else '0')
    env.pop('RW_ADAPTER_MODE', None)  # Match VBS's unset/default fast-smoke mode.
    if args.phase_trace:
        env['PYTHONPATH'] = os.pathsep.join([str(ROOT), str(ROOT / 'diagnostics/phase_trace_bootstrap'),
                                            *([env['PYTHONPATH']] if env.get('PYTHONPATH') else [])])
        env['RW_PHASE_COMMIT_TRACE_DIR'] = str(out / 'phase_trace')
    candidate_manifest = json.loads((cfg_dir / 'manifest.json').read_text(encoding='utf-8'))
    selected = candidate_manifest['outputs'][str(args.beta)]
    if (ROOT / selected['path']).resolve() != cfg_path.resolve() or hashlib.sha256(cfg_path.read_bytes()).hexdigest() != selected['sha256']:
        raise ValueError('Selected config differs from its manifest')
    inputs = {state, cfg_path, ROOT / cfg['mapping_json'], ROOT / cfg['detector_mapping_json'],
              ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'}
    if previous is not None:
        inputs.add(previous)
    for relative, expected in candidate_manifest['source_sha256'].items():
        path = ROOT / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Candidate input changed since manifest generation: ' + relative)
        inputs.add(path)
    input_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(inputs)}
    manifest = {'recorded_run': run, 'recorded_sim_sec': args.time,
                'recorded_snapshot': str(state.relative_to(ROOT)), 'input_sha256': input_hashes,
                'command': command, 'environment': {k: env[k] for k in ('RW_OFFSET_WRITER', 'NUMSIM_REPO_ROOT', 'RW_MAINLINE_SG_ONLY')},
                'config_sha256': hashlib.sha256(cfg_path.read_bytes()).hexdigest(),
                'source_sha256': hashes(), 'execute': args.execute}
    if args.phase_trace:
        manifest['read_only_phase_trace'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / 'diagnostics/phase_commit_trace.py', ROOT / 'diagnostics/phase_trace_bootstrap/sitecustomize.py')}
        manifest['environment'].update({k: env[k] for k in ('PYTHONPATH', 'RW_PHASE_COMMIT_TRACE_DIR')})
    if not args.execute:
        print(json.dumps(manifest, indent=2))
        return
    process_snapshot()  # Verify monitoring permission before starting any child.
    out.mkdir(parents=True, exist_ok=False)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    owned = {}
    started = time.monotonic()
    with (out / 'stdout.log').open('w', encoding='utf-8') as stdout, (out / 'stderr.log').open('w', encoding='utf-8') as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        parent_record = process_snapshot().get(process.pid)
        next_inventory = 0.
        while process.poll() is None:
            if time.monotonic() >= next_inventory:
                owned_descendants(process_snapshot(), parent_record, owned)
                next_inventory = time.monotonic() + 3.
            if time.monotonic() - started > args.timeout_sec:
                for child in reversed(list(owned.values())):
                    stop_exact_process(child)
                if parent_record is not None:
                    stop_exact_process(parent_record)
                else:
                    process.kill()  # Popen retains the exact process handle.
                process.wait()
                manifest['timed_out'] = True
                break
            time.sleep(.2)
    snapshot = process_snapshot()
    survivors = [row for pid, row in owned.items() if pid in snapshot and row['created'] == snapshot[pid]['created']]
    manifest.update(exit_code=process.returncode, elapsed_sec=time.monotonic() - started,
                    observed_worker_processes=list(owned.values()), surviving_worker_pids=[p['pid'] for p in survivors],
                    source_unchanged=hashes() == manifest['source_sha256'],
                    inputs_unchanged=all(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
                                         for relative, expected in input_hashes.items()))
    # Never let a diagnostic timeout leave the process tree it created behind.
    for child in survivors:
        stop_exact_process(child)
    error = None
    try:
        if process.returncode != 0 or survivors or not manifest['source_unchanged'] or not manifest['inputs_unchanged']:
            raise AssertionError('Failed adapter/process cleanup or runtime source/input changed; inspect logs')
        manifest['validated_metadata'] = validate_result(json.loads((out / 'action.json').read_text(encoding='utf-8')), args.beta, args.controller)
        manifest['valid'] = True
    except Exception as exc:
        error = exc
        manifest.update(valid=False, error=str(exc))
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('PRODUCTION_PREFLIGHT=' + str(out / 'manifest.json'), flush=True)
    if error is not None:
        raise error


if __name__ == '__main__':
    main()
