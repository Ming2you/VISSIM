"""Serial native NC5400 arms. Plan only by default; root owns actual execution.

Current runtime pins and historical NC command/trajectory evidence are separate.
Failure preserves outputs/lock and stops the sequence; this driver never kills.
"""
import argparse
from collections import Counter
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from diagnostics import run_fixed_beta300v3_route_experiment as d
from diagnostics.signal_readback_cadence import vsl_readback_matches
from diagnostics import prepare_native_nc5400_config as nc_config

FAMILY = ROOT / 'diagnostics/performance_initial_startup_clock_v1/manifest.json'
FAMILY_SHA = '7317fe4fb2021721e1c60e55249105b06dd40e8d1df06dd4d58454e00eb8b91b'
NATIVE = ROOT / 'diagnostics/flat_network_native_readback_v3/native_gate.json'
NATIVE_SHA = '56b3f9ff9e608e680482392ceb75f2109984194d7423ab5eac00cc265af09dbd'
TUNING = ROOT / 'diagnostics/native_nc5400_config_v1/config.json'
TUNING_SHA = '851d8e3e3384a0af1d5fe93833c4ff451e1ccea99b9a2cb3272d24377125138a'
OLD = ROOT / 'evaluation/runs/codex_contract_nc_headoff_continuous_s13_5400_v3_20260910'
OLD_SHA = '65312d19a5e69ad51dbe619e6085ca8eac30acd7c88e81d41c7b6845ac597760'
TRAJECTORY = ROOT / 'diagnostics/current_nc_v3_vs_original_full5400_trajectory.json'
TRAJECTORY_SHA = '4aa81ac080c2e8c9b2b76b4c9145714d3b27b1673e6399fe87a58542f3599c4c'
ANCHORS = '900,1500,1800,2100,2700,3600,4500,5400'
EXPECTED = dict(seed=13, sim_period_sec=5400, control_interval_sec=150, state_log_interval_sec=30,
                demand_scale=1, controller='no-control')


def environment(python):
    env = d.child_environment(python)
    env.pop('RW_FORCE_STEPWISE', None)
    env.update(RW_OFFSET_WRITER='experiment', RW_SIGNAL_OBSERVATION='0')
    return env


def arm_command(name, arm, run):
    out = d.arm_command(name, arm, run)
    for key, value in {'-Controller': 'no-control', '-Tuning': str(TUNING),
                       '-SimPeriod': '5400', '-AuditAnchorsSec': ANCHORS}.items():
        out[out.index(key) + 1] = value
    out.remove('-ForceStepwise')
    return out


def gates():
    pins = {}
    for path, digest in ((FAMILY, FAMILY_SHA), (NATIVE, NATIVE_SHA), (TUNING, TUNING_SHA), (TRAJECTORY, TRAJECTORY_SHA)):
        d.pin(pins, path, digest)
    runtime, native, tuning = d.load(FAMILY), d.load(NATIVE), d.load(TUNING)
    d.pin(pins, nc_config.BASE, nc_config.BASE_SHA)
    d.pin(pins, Path(nc_config.__file__))
    config_manifest = TUNING.parent / 'manifest.json'
    report = d.load(config_manifest)
    d.require(report['json_diff'] == nc_config.validate(d.load(nc_config.BASE), tuning)
              and report['output'] == {'path': d.relative(TUNING), 'sha256': TUNING_SHA}
              and report['producer_sha256'] == d.sha(Path(nc_config.__file__)), 'NC model-only diff certificate differs')
    for p in (config_manifest, ROOT / 'diagnostics/audit_nc5400_native_signals.py', ROOT / 'diagnostics/review_nc5400_baseline.py'):
        d.pin(pins, p)
    smoke_path = TUNING.parent / 'lcd_t1_smoke/validation.json'; smoke = d.load(smoke_path)
    d.require(smoke['valid'] is True and smoke['physical74_exact'] is True and smoke['source_changes'] == []
              and smoke['input_changes'] == [] and smoke['source_sha256'] == runtime['source_sha256'], 'Native NC physical smoke missing/stale')
    d.pin(pins, smoke_path)
    d.pin(pins, smoke_path.parent / 'action.csv', d.WARM_SHA)
    for p, h in smoke['input_sha256'].items(): d.pin(pins, p, h)
    d.require(len(runtime['source_sha256']) == 137, 'Expected current137 runtime family')
    d.require(tuning['urban']['capacity']['head_observation']['enabled'] is False and
              tuning['actuation']['real_world_signal_control']['apply_to_no_control'] is False, 'NC ownership/continuous settings differ')
    for path, digest in runtime['source_sha256'].items():
        d.pin(pins, path, digest)
    d.require(native['schema'] == 'flat-network-native-gate/v1' and native['native_load_readback_passed'] is True
              and native['source_changes'] == [] and native['errors'] == [] and native['native_vehicle_eligibility_verified'] is False, 'Native gate failed')
    d.require(d.workspace_path(native['flat_manifest_path']) == d.FLAT / 'manifest.json', 'Wrong native asset family')
    pre = NATIVE.parent / 'preflight.json'
    d.pin(pins, pre, native['preflight_sha256'])
    for path, digest in d.load(pre)['pinned_files'].items():
        d.pin(pins, path, digest)
    d.pin(pins, d.FLAT / 'manifest.json', native['flat_manifest_sha256'])
    flat = d.load(d.FLAT / 'manifest.json')
    d.require(flat['source_changes'] == [] and flat['data_reference_filesystem_validation'] is True, 'Flat assets invalid')
    d.require(set(native['arms']) == set(d.ARMS), 'Native arms differ')
    for arm in d.ARMS:
        row = native['arms'][arm]
        d.require(all(row[k] is True for k in ('native_readback_exact', 'loadnet_passed', 'owned_processes_gone'))
                  and row['network_sha256'] == flat['outputs'][arm + '.inpx']['destination_sha256'], 'Native arm proof differs')
    for row in flat['outputs'].values():
        d.pin(pins, d.FLAT / row['destination'], row['destination_sha256'])
    old_prov = OLD / ('run_provenance_' + OLD.name + '.json')
    d.pin(pins, old_prov, OLD_SHA)
    old = d.load(old_prov)
    d.require(all(old[k] == v for k, v in EXPECTED.items()), 'Wrong old NC reference')
    refs = {s: OLD / ('decisions_' + OLD.name) / f'action_{s:06d}.csv' for s in (1, 900)}
    for path in refs.values():
        d.pin(pins, path, d.WARM_SHA)
        nc_rows(d.csv_rows(path))
    for path in [*d.FILES.values(), d.RUNNER, Path(d.__file__), Path(__file__),
                 ROOT / 'diagnostics/signal_readback_cadence.py', ROOT / 'diagnostics/live_beta0_first_interval_audit.py',
                 ROOT / 'diagnostics/audit_observed_nc_trajectory.py']:
        if path != d.FILES['Tuning']:
            d.pin(pins, path)
    return pins, runtime, flat, refs, old


def nc_rows(rows):
    d.physical_rows(rows)
    d.require(Counter(r['kind'] for r in rows) == {'vsl': 66, 'ramp_meter': 8}, 'NC must have66 VSL/8 meters/no city rows')
    d.require(all(Decimal(r['speed_kph']) == 120 if r['kind'] == 'vsl' else
                  Decimal(r['green_sec']) == 10 and Decimal(r['rate_vph']) == 900 for r in rows), 'NC physical command differs')


def demand_writes(log):
    pending, rows = None, []
    for line in log.splitlines():
        if line.startswith('DEMAND_WRITE_BEGIN '):
            match = re.fullmatch(r'DEMAND_WRITE_BEGIN no=(\d+) time_int=([\d-]+) before=([\d.]+) target=([\d.]+) timer_sec=([\d.]+)', line)
            d.require(match is not None and pending is None, 'Malformed/nonserial demand BEGIN')
            pending = list(match.groups()[:4])
        elif line.startswith('DEMAND_WRITE_DONE '):
            match = re.fullmatch(r'DEMAND_WRITE_DONE no=(\d+) time_int=([\d-]+) timer_sec=([\d.]+)', line)
            d.require(match is not None and pending is not None and list(match.groups()[:2]) == pending[:2], 'Demand DONE mismatch')
            rows.append(pending); pending = None
    d.require(pending is None and len(rows) == 204 and len({tuple(r[:2]) for r in rows}) == 204, 'Expected204 distinct completed writes')
    return rows


def ascii_control_log(raw):
    prefixes = (b'RUN_MODE=', b'STAGE=', b'DECISIONS_', b'DEMAND_WRITE_')
    return '\n'.join(line.decode('ascii') for line in raw.splitlines()
                     if line.startswith(prefixes) or b'ERROR=' in line or b'FAILED=' in line)


def validate_run(run, arm, network_sha, refs, old, runtime):
    name = run.name; folder = run / ('decisions_' + name)
    p = run / ('run_provenance_' + name + '.json'); prov = d.load(p)
    d.require(prov['name'] == name and prov['run_id'] and all(prov.get(k) == v for k, v in EXPECTED.items()), 'NC provenance differs')
    d.require(prov['startup_stall_sec'] == 300 and prov['files']['network']['sha256'] == network_sha
              and prov['files']['tuning']['sha256'] == TUNING_SHA, 'Wrong run input/startup bound')
    for key in ('calibration', 'control_mapping', 'vehicle_input_roles', 'demand_profile', 'urban_input_gate_map', 'generated_vbs_config'):
        d.require(prov['files'][key]['sha256'] == old['files'][key]['sha256'], 'Changed historical NC physical input: ' + key)
    current = {d.relative(d.workspace_path(k)): v for k, v in runtime['source_sha256'].items()}
    recorded = [d.relative(d.workspace_path(r['path'])) for r in prov['controller_sources']]
    d.require(len(recorded) == len(set(recorded)) and set(recorded) == {k for k in current if k.startswith('evaluation/controllers/') and k.endswith('.py')}, 'Runtime controller source coverage differs')
    for row in prov['controller_sources']:
        key = d.relative(d.workspace_path(row['path']))
        d.require(row['sha256'] == current.get(key), 'Runtime provenance differs from current family: ' + key)
    for key, value in environment(d.DEFAULT_PYTHON).items():
        if key.startswith('RW_'):
            d.require(str(prov['env'].get(key)) == value, 'Unexpected runtime environment: ' + key)
    log = ascii_control_log((run / ('runlog_' + name + '.txt')).read_bytes())
    d.require('RUN_MODE=CONTINUOUS_STATIC controller=no-control' in log and 'STAGE=SIM_DONE' in log
              and re.findall(r'^DECISIONS_OK=(\d+)\s*$', log, re.M) == ['2']
              and re.findall(r'^DECISIONS_FAILED=(\d+)\s*$', log, re.M) == ['0']
              and 'ERROR=' not in log and not re.search(r'FAILED=[1-9]', log), 'NC completion/failure/mode gate failed')
    states = d.csv_rows(run / ('state_' + name + '.csv'))
    d.require([Decimal(r['sim_sec']) for r in states] == [Decimal(1), *map(Decimal, range(30, 5401, 30))], 'Incomplete/duplicate NC state cadence')
    d.require({p.name for p in folder.glob('action_*.csv')} == {'action_000001.csv', 'action_000900.csv'}, 'Unexpected decision cadence')
    applied = d.csv_rows(run / ('action_' + name + '.csv'))
    d.require(Counter(Decimal(r['sim_sec']) for r in applied) == {Decimal(1): 74, Decimal(900): 74}, 'Applied action cadence differs')
    commands = []
    for sec in (1, 900):
        path = folder / f'action_{sec:06d}.csv'; rows = d.csv_rows(path); nc_rows(rows)
        d.require(d.physical_rows(rows) == d.physical_rows(d.csv_rows(refs[sec])), 'Historical74 command differs')
        actual = [r for r in applied if Decimal(r['sim_sec']) == sec]
        d.require(d.physical_rows(actual) == d.physical_rows(rows) and all(vsl_readback_matches(r) if r['kind'] == 'vsl'
                  else r['readback'] == 'GREEN' for r in actual), 'Actual command/readback mismatch')
        meta = d.load(path.with_suffix('.json'))['metadata']
        d.require(meta['controller_variant'] == 'no-control' and meta['controller_status'] == 'ok' and not meta.get('controller_error'), 'Decision metadata failed')
        commands.append({'time': sec, 'sha256': d.sha(path), 'rows': 74, 'physical_reference_exact': True})
    trace = d.csv_rows(folder / 'signal_readback.csv')
    expected = Counter((str(sc), '1', str(sec), stage) for sc in range(9101, 9109)
                       for stage, times in (('immediate', (1, 900)), ('post_step', range(30, 5401, 30))) for sec in times)
    d.require(Counter((r['sc_no'], r['sg_no'], r['sim_sec'], r['stage']) for r in trace) == expected
              and all(r['requested_state'] == r['readback_state'] == 'GREEN' and r['ok'] == '1' for r in trace), 'Continuous sampled ramp persistence failed')
    native = {ext: [{'path': d.relative(p), 'bytes': p.stat().st_size} for p in sorted(run.rglob('*' + ext))] for ext in ('.fzp', '.lsa', '.err')}
    d.require(all(len(native[e]) == 1 and native[e][0]['bytes'] > 0 for e in ('.fzp', '.lsa')), 'Missing/ambiguous native outputs')
    return {'valid': True, 'commands': commands, 'sampled_ramp_readbacks': len(trace), 'city_command_rows': 0,
            'demand_writes': demand_writes(log), 'native_outputs': native, 'provenance_sha256': d.sha(p),
            'scope': 'Native urban ownership; sampled30s meter persistence. Native LSA is checked separately. Rate900 is a command, not measured flow. Adapter predictions are excluded from outcomes.'}


def native_signal_reference(run):
    from diagnostics.audit_nc5400_native_signals import events, used_signal_programs
    records, programs = [], []
    for folder in (run, OLD):
        paths = list(folder.rglob('*.lsa')); d.require(len(paths) == 1, 'One completed native LSA required')
        records.append(events(paths[0]))
        prov = d.load(folder / ('run_provenance_' + folder.name + '.json'))
        programs.append(used_signal_programs(prov))
    keys = ('preamble_sha256', 'preamble_bytes', 'event_sha256', 'rows', 'group_event_counts', 'states', 'modes', 'first_sec', 'last_sec')
    d.require(all(records[0][k] == records[1][k] for k in keys)
              and programs[0]['selected_by_sc'] == programs[1]['selected_by_sc']
              and programs[0]['without_program'] == programs[1]['without_program'], 'Native signals differ from old NC')
    return {'valid': True, 'records': records, 'used_programs_by_sc_exact': True,
            'programs': programs, 'compared_fields': list(keys)}


def baseline_trajectory(run):
    from diagnostics.audit_observed_nc_trajectory import payload
    expected = d.load(TRAJECTORY)['trajectory']['payloads'][0]
    records = []
    for folder in (run, OLD):
        path = d.single_fzp(folder); before = path.stat(); record = payload(path); after = path.stat()
        d.require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'FZP changed during complete payload/hash read')
        records.append(record)
    fields = ('header', 'payload_sha256', 'payload_bytes', 'rows', 'first_sec', 'last_sec')
    valid = all(record[k] == expected[k] for record in records for k in fields) and records[0]['rows'] == 26693633 and records[0]['last_sec'] == 5400
    return {'valid': valid, 'actual': records[0], 'historical': records[1], 'compared_fields': fields,
            'excluded': 'Only pre-$VEHICLE date/run preamble; historical runtime source is not claimed current.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--name', default='r03'); parser.add_argument('--execute', action='store_true')
    parser.add_argument('--reuse-baseline-review'); parser.add_argument('--reuse-baseline-review-sha256')
    args = parser.parse_args(); d.require(re.fullmatch(r'[a-z0-9]{1,8}', args.name), 'Use a new short batch name')
    d.require(bool(args.reuse_baseline_review) == bool(args.reuse_baseline_review_sha256), 'Baseline reuse requires an exact review SHA')
    batch = ROOT / 'diagnostics/no_control_network_arms' / args.name
    rows = [{'arm': a, 'name': f'codex_nc5400_{args.name}_{a}_s13', 'status': 'pending', 'valid': False} for a in d.ARMS]
    for row in rows:
        run = ROOT / 'evaluation/runs' / row['name']; row.update(run=d.relative(run), command=arm_command(row['name'], row['arm'], run))
    if not args.execute:
        print(json.dumps({'executed': False, 'validated': False, 'batch': d.relative(batch), 'arms': rows,
                          'requested_baseline_review': args.reuse_baseline_review}, indent=2)); return 0
    d.require(os.name == 'nt' and d.DEFAULT_PYTHON.is_file(), 'Windows/canonical Python required')
    d.require(not batch.exists() and all(not (ROOT / r['run']).exists() for r in rows), 'Existing outputs: refuse overwrite')
    pins, runtime, flat, refs, old = gates(); env = environment(d.DEFAULT_PYTHON)
    if args.reuse_baseline_review:
        from diagnostics.review_nc5400_baseline import validated_receipt
        rows[0] = validated_receipt(d.workspace_path(args.reuse_baseline_review), args.reuse_baseline_review_sha256, pins, runtime)
    d.require(not d.process_inventory(), 'Existing VISSIM/WSH process; do not launch')
    lock = ROOT / f'diagnostics/no_control_network_arms_{args.name}.lock'; token = json.dumps({'pid': os.getpid(), 'batch': d.relative(batch)}).encode()
    with lock.open('xb') as f: f.write(token)
    batch.mkdir(parents=True, exist_ok=False)
    result = {'schema': 'no-control-network-arms5400/v1', 'valid': False, 'completed': False, 'status': 'running', 'arms': rows,
              'source_sha256': pins, 'current_runtime_family': {'path': d.relative(FAMILY), 'sha256': FAMILY_SHA, 'count': 137},
              'historical_nc_provenance': {'path': d.relative(OLD), 'sha256': OLD_SHA}, 'environment': {k: v for k, v in env.items() if k.startswith('RW_')},
              'nc_config': {'path': d.relative(TUNING), 'sha256': TUNING_SHA, 'base_sha256': nc_config.BASE_SHA, 'model_predictions_used': False},
              'driver_process_termination': False, 'source_changes': []}
    try:
        for row in rows:
            if row.get('reused_from'): continue
            d.assert_pins(pins); d.require(not d.process_inventory(), 'Process survivor: stop before next arm')
            run = ROOT / row['run']; run.mkdir(parents=True, exist_ok=False)
            d.save(run / 'no_control_source_manifest.json', {'source_sha256': pins, 'runtime_family': d.relative(FAMILY), 'tuning_sha256': TUNING_SHA})
            row.update(status='running', started_utc=d.utc()); d.save(batch / 'manifest.json', result); started = time.monotonic()
            with (run / 'watchdog_stdout.txt').open('xb') as out, (run / 'watchdog_stderr.txt').open('xb') as err:
                proc = subprocess.Popen(row['command'], cwd=ROOT, env=env, stdout=out, stderr=err, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                row['watchdog_pid'] = proc.pid; d.save(batch / 'manifest.json', result); row['exit_code'] = proc.wait()
            row.update(elapsed_sec=time.monotonic() - started, completed=True, finished_utc=d.utc())
            row['natural_exit'] = d.post_watchdog_process_gate(row['exit_code']); d.require(row['natural_exit']['valid'], 'Natural-exit gate failed')
            d.assert_pins(pins)
            row['validation'] = validate_run(run, row['arm'], flat['outputs'][row['arm'] + '.inpx']['destination_sha256'], refs, old, runtime)
            row['native_signal_reference'] = native_signal_reference(run)
            for record in row['native_signal_reference']['records']:
                pins[record['path']] = record['file_sha256']
            for proof in row['native_signal_reference']['programs']: pins.update(proof['source_sha256'])
            if row['arm'] == 'baseline':
                row['trajectory'] = baseline_trajectory(run); d.save(batch / 'manifest.json', result); d.require(row['trajectory']['valid'], 'NC baseline full trajectory mismatch')
            else:
                d.require(row['validation']['demand_writes'] == rows[0]['validation']['demand_writes'], '204 demand values/order differ')
            row.update(status='passed', valid=True); d.save(batch / 'manifest.json', result)
        d.assert_pins(pins); result.update(valid=True, completed=True, status='all_three_passed'); d.save(batch / 'manifest.json', result)
        d.require(lock.read_bytes() == token, 'Lock identity changed'); lock.unlink(); return 0
    except BaseException as exc:
        result.update(status='failed_preserved_stop', error=f'{type(exc).__name__}: {exc}', source_changes=[p for p, h in pins.items() if not (ROOT / p).is_file() or d.sha(ROOT / p) != h])
        d.save(batch / 'manifest.json', result); print(result['error'], file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
