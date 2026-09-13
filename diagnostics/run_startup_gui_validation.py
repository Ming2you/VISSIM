"""Validate the startup-only VBS change using the canonical fixed-command run."""
from pathlib import Path
import argparse
import json
import subprocess
import time

from diagnostics import run_fixed_beta300v3_route_experiment as d


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=d.ARMS, default='baseline')
    parser.add_argument('--baseline-validation-sha256')
    args = parser.parse_args()
    arm = args.arm
    suffix = '' if arm == 'baseline' else '_' + arm
    name = 'codex_startup_gui' + suffix + '_s13_1050_v1'
    output = d.ROOT / ('diagnostics/startup_gui_actual' + suffix + '_v1')
    run = d.ROOT / 'evaluation/runs' / name
    d.require(not output.exists() and not run.exists(), 'New evidence/run directories required')
    family_path = d.ROOT / 'diagnostics/performance_initial_clock_replay_v1/manifest.json'
    d.require(d.sha(family_path) == 'cca58af11e22fd3301003d61f412cb4c66ce3513262d83e80182ca7ddfde4a00', 'Unexpected original runtime manifest')
    family = d.load(family_path)
    pins = {}
    for path, expected in family['source_sha256'].items():
        if path.replace('\\', '/') == 'scripts/run_real_world_stackelberg_controller.vbs':
            d.require(expected == '71ec5f8d8a36a93f21f8e66da80730e91dae64de1a3eb2321f0361df636b9a81', 'Wrong VBS base')
            expected = '30a279cbcc111a7374af023decf65456ccf6c46e005dc7ab6639bc8b5f69cdb0'
        d.pin(pins, path, expected)
    for path in (Path(__file__), Path(d.__file__), d.ROOT / 'diagnostics/startup_gui_change_v1.json',
                 d.ROOT / 'diagnostics/startup_gui_strict_demand_change_v2.json'):
        d.pin(pins, path)
    flat = d.load(d.FLAT / 'manifest.json')
    native_path = d.ROOT / 'diagnostics/flat_network_native_readback_v3/native_gate.json'
    d.pin(pins, native_path, '56b3f9ff9e608e680482392ceb75f2109984194d7423ab5eac00cc265af09dbd')
    native = d.load(native_path)
    d.require(native.get('native_load_readback_passed') is True and native.get('source_changes') == [],
              'Native network readback gate failed')
    d.pin(pins, d.FLAT / 'manifest.json', native['flat_manifest_sha256'])
    native_arm = native['arms'][arm]
    d.require(all(native_arm.get(key) is True for key in ('native_readback_exact', 'loadnet_passed', 'owned_processes_gone'))
              and native_arm['network_sha256'] == flat['outputs'][arm + '.inpx']['destination_sha256'],
              'Native gate covered a different or invalid arm')
    d.pin(pins, native_arm['readback_csv_path'], native_arm['readback_csv_sha256'])
    d.pin(pins, native_path.parent / arm / 'process.json', native_arm['process_manifest_sha256'])
    for path, row in flat['outputs'].items():
        d.pin(pins, d.FLAT / path, row['destination_sha256'])
    profile = d.load(d.PROFILE / 'manifest.json')
    for row in profile['outputs'].values():
        d.pin(pins, row['path'], row['sha256'])
    for path in d.FILES.values():
        d.pin(pins, path)
    d.pin(pins, d.FILES['Tuning'], d.CONFIG_SHA)
    original = d.load(d.ROOT / 'diagnostics/fixed_beta300v3_experiments/r02/manifest.json')
    reference = original['baseline_trajectory_reference']
    refs_dir = d.ROOT / reference['run'] / ('decisions_' + reference['source_run'])
    refs = {1: refs_dir / 'action_000001.csv', 900: refs_dir / 'action_000900.csv'}
    d.pin(pins, refs[1], d.WARM_SHA)
    d.pin(pins, refs[900], d.CSV900_SHA)
    d.pin(pins, reference['fzp'], reference['fzp_sha256'])
    baseline = None
    if arm != 'baseline':
        baseline_path = d.ROOT / 'diagnostics/startup_gui_actual_v1/result.json'
        d.require(args.baseline_validation_sha256, 'Exact completed baseline certificate SHA required')
        d.pin(pins, baseline_path, args.baseline_validation_sha256)
        baseline = d.load(baseline_path)
        d.require(baseline.get('schema') == 'startup-gui-actual-validation/v1'
                  and baseline.get('valid') is True and baseline.get('exit_code') == 0
                  and baseline.get('source_changes') == [] and baseline.get('reference') == reference
                  and baseline.get('natural_exit', {}).get('valid') is True,
                  'Incomplete startup baseline certificate')
        for path in family['source_sha256']:
            key = d.relative(d.workspace_path(path))
            d.require(baseline['source_sha256'].get(key) == pins[key],
                      'Baseline used different runtime: ' + path)
        baseline_run = d.workspace_path(baseline['run'])
        d.require(baseline_run.name == 'codex_startup_gui_s13_1050_v1', 'Wrong baseline run identity')
        checked = d.validate_run(baseline_run, baseline_run.name, 'baseline',
                                 flat['outputs']['baseline.inpx']['destination_sha256'], refs)
        trajectory = d.validate_baseline_trajectory(baseline_run, baseline_run.name, reference)
        d.require(trajectory.get('valid') is True and trajectory == baseline['trajectory'],
                  'Baseline full native trajectory certificate changed')
        for item in checked['commands'] + checked['raw_states']:
            d.pin(pins, item['path'], item['sha256'])
        for path, expected in checked['readback_sources'].items():
            d.pin(pins, path, expected)
        d.pin(pins, trajectory['actual']['path'], trajectory['actual']['file_sha256'])
    env = d.child_environment(d.DEFAULT_PYTHON)
    shell_proof = d.validate_powershell_runtime(env)
    d.require(not d.process_inventory(), 'Existing simulator/script host')
    output.mkdir()
    run.mkdir()
    report = {'schema': 'startup-gui-actual-validation/v1', 'started_utc': d.utc(),
              'source_sha256': pins, 'source_changes': [], 'valid': False,
              'runtime_change': 'Only reviewed VBS GUI placement, startup observations and strict demand reads',
              'arm': arm, 'run': d.relative(run), 'command': d.arm_command(name, arm, run),
              'baseline_validation_sha256': args.baseline_validation_sha256,
              'powershell_hash_preflight': shell_proof, 'reference': reference}
    d.save(output / 'result.json', report)
    try:
        started = time.monotonic()
        with (run / 'watchdog_stdout.txt').open('xb') as stdout, (run / 'watchdog_stderr.txt').open('xb') as stderr:
            proc = subprocess.Popen(report['command'], cwd=d.ROOT, env=env, stdout=stdout, stderr=stderr,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            report['watchdog_pid'] = proc.pid
            d.save(output / 'result.json', report)
            report['exit_code'] = proc.wait()
        report['wall_sec'] = time.monotonic() - started
        report['natural_exit'] = d.post_watchdog_process_gate(report['exit_code'])
        d.require(report['natural_exit']['valid'], 'Watchdog failed or native process remains')
        d.assert_pins(pins)
        report['validation'] = d.validate_run(run, name, arm, flat['outputs'][arm + '.inpx']['destination_sha256'], refs)
        if arm == 'baseline':
            report['trajectory'] = d.validate_baseline_trajectory(run, name, reference)
            d.require(report['trajectory']['valid'], 'Startup change altered the full native trajectory')
        report['valid'] = True
    except BaseException as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        report['finished_utc'] = d.utc()
        report['source_changes'] = [p for p, h in pins.items() if d.sha(d.ROOT / p) != h]
        report['valid'] = report['valid'] and not report['source_changes']
        d.save(output / 'result.json', report)
    print(json.dumps({k: report.get(k) for k in ('valid', 'exit_code', 'wall_sec', 'error', 'source_changes')}))
    return 0 if report['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
