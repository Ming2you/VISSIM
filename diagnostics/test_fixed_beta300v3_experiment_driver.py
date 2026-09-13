"""Small stdlib driver checks; never validate live gates, load a model or COM.

Real inputs are the already validated 74/213-row CSVs and two v3 raw/provenance
schemas. A synthetic run has oracle-generated signal rows and header-only native
files: passing it proves the validator wiring, not traffic execution/effect.
"""
from __future__ import annotations

import ast
from contextlib import redirect_stdout
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from diagnostics import run_fixed_beta300v3_route_experiment as driver

ROOT = Path(__file__).resolve().parents[1]
RUN_NAME = 'codex_contract_beta300_s13_1050_v3_20260910'
ACTUAL_RUN = ROOT / 'evaluation/runs' / RUN_NAME
ACTUAL_DECISIONS = ACTUAL_RUN / ('decisions_' + RUN_NAME)
WRITER = ROOT / 'diagnostics/fixed_beta300v3_profile_invocation_v2'
PURE_MODULES = {
    'diagnostics.run_fixed_beta300v3_route_experiment',
    'diagnostics.signal_readback_cadence',
    'diagnostics.live_beta0_first_interval_audit',
    'diagnostics.run_area_production_preflight',
    'diagnostics.audit_observed_nc_trajectory',
    'evaluation.controllers.signal_timing_oracle',
    'evaluation.controllers.action_csv_schema',
    'evaluation.controllers.signal_group_plan',
}
EVIDENCE = {}


def small_read(path):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise AssertionError('Fixture exceeded the small-file limit: ' + str(path))
    if path.suffix.lower() in ('.fzp', '.lsa', '.err', '.jpg', '.inpx', '.sig'):
        raise AssertionError('Forbidden traffic/asset fixture: ' + str(path))
    data = path.read_bytes()
    EVIDENCE[path.relative_to(ROOT).as_posix()] = {
        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return data


def dump_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def dump_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


class SmallFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.command_bytes = {sec: small_read(WRITER / f'action_{sec:06d}.csv') for sec in (1, 900)}
        cls.rows = {sec: list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
                    for sec, data in cls.command_bytes.items()}
        cls.original = {sec: list(csv.DictReader(io.StringIO(
            small_read(ACTUAL_DECISIONS / f'action_{sec:06d}.csv').decode('utf-8-sig')))) for sec in (1, 900)}
        cls.actions = {sec: json.loads(small_read(WRITER / f'action_{sec:06d}.json').decode('utf-8-sig'))
                       for sec in (1, 900)}
        cls.provenance = json.loads(small_read(ACTUAL_RUN / ('run_provenance_' + RUN_NAME + '.json')).decode('utf-8-sig'))
        cls.raw = {sec: json.loads(small_read(ACTUAL_DECISIONS / f'state_{sec:06d}.json').decode('utf-8-sig'))
                   for sec in (900, 1050)}

    def test_01_fresh_import_is_pure_and_driver_syntax_compiles(self):
        # Spawn only a new Python import probe. Its audit hook forbids any child,
        # COM/model import, workspace data read, or file write during imports.
        source = r'''
import ast, json, os, pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1]).resolve()
allowed = set(json.loads(sys.argv[2]))
opened = []
class Guard:
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.startswith(('evaluation.', 'diagnostics.')) and
            fullname not in allowed and fullname != 'evaluation.controllers'):
            raise AssertionError('Unexpected project import: ' + fullname)
        if fullname.split('.')[0] in {'src', 'vendor', 'numpy', 'scipy', 'win32com', 'pythoncom', 'comtypes'}:
            raise AssertionError('Model/COM import: ' + fullname)
def audit(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.spawn'}:
        raise AssertionError('Child execution during import')
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        p = pathlib.Path(os.fsdecode(args[0])).resolve()
        mode = args[1] or ''
        if any(c in str(mode) for c in 'wax+') or (isinstance(args[2], int) and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)):
            raise AssertionError('File write during pure import: ' + str(p))
        if p.is_relative_to(root):
            if p.suffix not in {'.py', '.pyc'}:
                raise AssertionError('Workspace data read during import: ' + str(p))
            opened.append(p.relative_to(root).as_posix())
sys.meta_path.insert(0, Guard())
sys.addaudithook(audit)
from diagnostics import run_fixed_beta300v3_route_experiment
from diagnostics.signal_readback_cadence import strict_signal_trace
from diagnostics.audit_observed_nc_trajectory import payload
from evaluation.controllers.signal_timing_oracle import decisions_from_action_rows
source = pathlib.Path(run_fixed_beta300v3_route_experiment.__file__).read_text(encoding='utf-8-sig')
compile(source, '<driver-syntax-only>', 'exec')
ast.parse(source)
loaded = sorted(set(sys.modules) & allowed)
assert set(loaded) == allowed, loaded
print(json.dumps({'loaded_project_modules': loaded, 'opened_project_source_files': sorted(set(opened)),
                  'model_or_COM_imports': [], 'child_processes_during_import': 0, 'workspace_data_reads': 0}))
'''
        env = driver.child_environment(Path(sys.executable))
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', source, str(ROOT), json.dumps(sorted(PURE_MODULES))],
                                cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=20,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(result.returncode, 0, result.stderr)
        EVIDENCE['pure_import_probe'] = json.loads(result.stdout)

    def test_02_plan_does_not_gate_launch_or_create_outputs(self):
        out = io.StringIO()
        with patch.object(sys, 'argv', ['driver', '--name', 'fixture_only']), redirect_stdout(out), \
                patch.object(driver, 'validate_gates', side_effect=AssertionError('live gate called')), \
                patch.object(driver, 'process_inventory', side_effect=AssertionError('process enumeration')), \
                patch.object(driver.subprocess, 'Popen', side_effect=AssertionError('launch')), \
                patch.object(Path, 'mkdir', side_effect=AssertionError('directory mutation')):
            self.assertEqual(driver.main(), 0)
        plan = json.loads(out.getvalue())
        self.assertFalse(plan['validated'])
        self.assertFalse(plan['executed'])
        self.assertEqual([row['arm'] for row in plan['arms']], list(driver.ARMS))
        self.assertTrue(all(not row['completed'] and not row['valid'] for row in plan['arms']))

    def test_03_command_and_environment_parity(self):
        common = []
        for arm in driver.ARMS:
            command = driver.arm_command('name_' + arm, arm, ROOT / 'synthetic' / arm)
            self.assertEqual(command[command.index('-File') + 1], str(driver.RUNNER))
            self.assertNotIn('-Adapter', command)
            for switch in ('-NoGlobalKill', '-ForceStepwise'):
                self.assertIn(switch, command)
            for key, value in {'-Controller': 'diagnostic-signal-profile', '-Seed': '13', '-SimPeriod': '1050',
                               '-ControlIntervalSec': '150', '-ControlStartSec': '900', '-WarmupController': 'no-control',
                               '-StateLogIntervalSec': '30', '-StartupStallSec': '300', '-StallSec': '300',
                               '-MaxAttempts': '1', '-AuditAnchorsSec': '900,1050', '-DemandScale': '1'}.items():
                self.assertEqual(command[command.index(key) + 1], value)
            for key in ('-Name', '-Network', '-OutDir'):
                command[command.index(key) + 1] = '<arm-specific>'
            common.append(command)
        self.assertEqual(common[0], common[1])
        self.assertEqual(common[0], common[2])
        injected = {'RW_UNKNOWN': 'bad', 'rw_offset_writer': 'bad', 'PYTHONPATH': 'bad',
                    'PYTHONSTARTUP': 'bad', 'PYTHONPROFILEIMPORTTIME': '1', 'NUMSIM_REPO_ROOT': 'bad',
                    'PYTHONHASHSEED': '137', 'PSModulePath': 'incompatible-powershell-core-modules'}
        with patch.dict(os.environ, injected):
            before = dict(os.environ)
            a, b = driver.child_environment(Path(sys.executable)), driver.child_environment(Path(sys.executable))
            self.assertEqual(a, b)
            self.assertEqual(dict(os.environ), before)
        for key in ('RW_UNKNOWN', 'rw_offset_writer', 'PYTHONPATH', 'PYTHONSTARTUP', 'PYTHONPROFILEIMPORTTIME'):
            self.assertNotIn(key, a)
        self.assertEqual(a['PYTHONHASHSEED'], '137')
        self.assertEqual(a['RW_OFFSET_WRITER'], 'test_only')
        self.assertEqual(a['RW_PYTHON'], sys.executable)
        self.assertEqual(a['NUMSIM_REPO_ROOT'], str(ROOT / 'vendor/NumSim-mine'))
        self.assertEqual([k for k in a if k.upper() == 'PSMODULEPATH'], ['PSMODULEPATH'])
        self.assertEqual(a['PSMODULEPATH'], str(driver.powershell().parent / 'Modules'))
        proof = {'version': '5.1', 'module_path': a['PSMODULEPATH'], 'sha256': driver.CONFIG_SHA}
        success = subprocess.CompletedProcess([], 0, json.dumps(proof).encode('ascii'), b'')
        with patch.object(driver.subprocess, 'run', return_value=success) as query:
            self.assertEqual(driver.validate_powershell_runtime(a), proof)
            self.assertIs(query.call_args.kwargs['env'], a)
        for failed in (subprocess.CompletedProcess([], 1, b'', b'Get-FileHash unavailable'),
                       subprocess.CompletedProcess([], 0, b'{}', b''),
                       subprocess.CompletedProcess([], 0, json.dumps(proof).encode('ascii'), b'error')):
            with self.subTest(preflight=failed.returncode), patch.object(driver.subprocess, 'run', return_value=failed), \
                    self.assertRaises(ValueError):
                driver.validate_powershell_runtime(a)

    def test_04_real_74_and_213_rows_match_without_metadata(self):
        for sec, count in ((1, 74), (900, 213)):
            self.assertEqual(len(self.rows[sec]), count)
            self.assertEqual(driver.physical_rows(self.rows[sec]), driver.physical_rows(self.original[sec]))
        self.assertEqual({row['speed_kph'] for row in self.rows[900] if row['kind'] == 'vsl'}, {'120.0'})
        self.assertEqual({row['rate_vph'] for row in self.rows[900] if row['kind'] == 'ramp_meter'}, {'900.0'})
        self.assertEqual({row['green_sec'] for row in self.rows[900] if row['kind'] == 'ramp_meter'}, {'10.0'})
        changed = copy.deepcopy(self.rows[900])
        for row in changed:
            row.update(metadata='different harmless provenance', sim_sec='900', readback='ignored here')
            for key in driver.NUMERIC:
                if row[key]:
                    row[key] = str(driver.Decimal(row[key]).quantize(driver.Decimal('.000000')))
        self.assertEqual(driver.physical_rows(changed), driver.physical_rows(self.rows[900]))

    def test_05_missing_or_truncated_column_duplicate_and_nonfinite_rejected(self):
        for column in driver.PHYSICAL_COLUMNS:
            for kind in ('absent', 'truncated'):
                rows = copy.deepcopy(self.rows[900])
                if kind == 'absent':
                    del rows[0][column]
                else:
                    rows[0][column] = None
                with self.subTest(column=column, kind=kind), self.assertRaises(ValueError):
                    driver.physical_rows(rows)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            driver.physical_rows(self.rows[900] + [self.rows[900][0]])
        for value in ('NaN', 'sNaN', 'Infinity', '-Infinity'):
            rows = copy.deepcopy(self.rows[900])
            rows[0]['speed_kph'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                driver.physical_rows(rows)
        malformed = copy.deepcopy(self.rows[900])
        malformed[0][None] = ['overflow']
        with self.assertRaises(ValueError):
            driver.physical_rows(malformed)

    def test_06_every_physical_column_and_missing_row_changes_comparison(self):
        baseline = driver.physical_rows(self.rows[900])
        for column in driver.PHYSICAL_COLUMNS:
            rows = copy.deepcopy(self.rows[900])
            index = next(i for i, row in enumerate(rows) if row[column])
            rows[index][column] = str(driver.Decimal(rows[index][column]) + 1) if column in driver.NUMERIC else rows[index][column] + '_changed'
            with self.subTest(column=column):
                self.assertNotEqual(driver.physical_rows(rows), baseline)
        self.assertNotEqual(driver.physical_rows(self.rows[900][1:]), baseline)

    def test_07_actual_raw_and_provenance_expected_keys_exist(self):
        p = self.provenance
        self.assertTrue({'seed', 'sim_period_sec', 'control_interval_sec', 'state_log_interval_sec',
                         'startup_stall_sec', 'demand_scale', 'controller', 'files', 'env'} <= p.keys())
        self.assertTrue({'network', 'tuning'} <= p['files'].keys())
        self.assertTrue(all('sha256' in p['files'][key] for key in ('network', 'tuning')))
        expected_env = {key for key in driver.ENVIRONMENT if key.startswith('RW_') and key != 'RW_FORCE_STEPWISE'}
        self.assertTrue(expected_env <= p['env'].keys())
        # It is a beta300 source run; do not mislabel its controller/writer as the
        # new diagnostic profile. The writer invocation fixtures cover that mode.
        self.assertEqual(p['controller'], 'wu-link')
        self.assertEqual(p['env']['RW_OFFSET_WRITER'], 'experiment')
        for sec, raw in self.raw.items():
            self.assertEqual(raw['sim_sec'], sec)
            envelope = raw['vehicle_routes']
            self.assertEqual(envelope['schema_version'], 'vissim-vehicle-routes-v1')
            self.assertIs(envelope['complete'], True)
            self.assertEqual(envelope['record_count'], len(envelope['records']))
            self.assertEqual(envelope['record_count'], raw['vehicle_records']['record_count'])
            self.assertEqual(envelope['sim_sec_before'], sec)
            self.assertEqual(envelope['sim_sec_after'], sec)
        meta = {**self.actions[900].get('diagnostics', {}), **self.actions[900].get('metadata', {})}
        self.assertEqual(meta['diagnostic_signal_profile_active'], 1)
        self.assertEqual(meta['controller_status'], 'ok')


class RunValidation(SmallFixtures):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from evaluation.controllers.signal_timing_oracle import decisions_from_action_rows
        from diagnostics.live_beta0_first_interval_audit import expected_signal, expected_ramp
        controllers = decisions_from_action_rows([{**row, 'sim_sec': 900} for row in cls.rows[900]])[0]['controllers']
        definitions = [(str(sc), str(sg), lambda sec, node=node, sg=str(sg): expected_signal(node, sg, sec))
                       for sc, node in controllers.items() for sg in node['windows']]
        definitions += [(str(int(row['sc_no'])), '1', lambda sec, green=float(row['green_sec']): expected_ramp(green, sec))
                        for row in cls.rows[900] if row['kind'] == 'ramp_meter']
        cls.trace_rows = []
        for sec in range(900, 1051):
            for stage in ('post_step', 'immediate'):
                if (stage == 'post_step' and sec == 900) or (stage == 'immediate' and sec == 1050):
                    continue
                for sc, sg, expected in definitions:
                    value = expected(sec - 1 if stage == 'post_step' else sec)
                    cls.trace_rows.append({'sim_sec': str(sec), 'sc_no': sc, 'sg_no': sg,
                                           'requested_state': value, 'readback_state': value, 'ok': '1', 'stage': stage})

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fixed_driver_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.name = 'synthetic_only'
        self.run = self.root / 'run'
        self.dec = self.run / ('decisions_' + self.name)
        self.dec.mkdir(parents=True)
        self.refs = {}
        for sec in (1, 900):
            self.refs[sec] = self.root / f'reference_{sec}.csv'
            self.refs[sec].write_bytes(self.command_bytes[sec])
        for sec in (1, 150, 300, 450, 600, 750, 900, 1050):
            source_sec = 1 if sec < 900 else 900
            path = self.dec / f'action_{sec:06d}.csv'
            path.write_bytes(self.command_bytes[source_sec])
            dump_json(path.with_suffix('.json'), self.actions[source_sec])
        p = copy.deepcopy(self.provenance)
        p['controller'] = 'diagnostic-signal-profile'
        p['files']['network']['sha256'] = 'synthetic-network-sha'
        p['files']['tuning']['sha256'] = driver.CONFIG_SHA
        p['env'].update(driver.ENVIRONMENT)
        self.prov_path = self.run / ('run_provenance_' + self.name + '.json')
        dump_json(self.prov_path, p)
        (self.run / ('runlog_' + self.name + '.txt')).write_text('STAGE=SIM_DONE\n', encoding='utf-8')
        dump_csv(self.run / ('state_' + self.name + '.csv'), [{'sim_sec': '1050', 'controller_status': 'ok'}])
        self.trace_path = self.dec / 'signal_readback.csv'
        dump_csv(self.trace_path, self.trace_rows)
        applied = [{**row, 'sim_sec': '900', 'readback': '120|120' if row['kind'] == 'vsl' else ''} for row in self.rows[900]]
        self.applied_path = self.run / ('action_' + self.name + '.csv')
        dump_csv(self.applied_path, applied)
        for sec in (900, 1050):
            dump_json(self.dec / f'state_{sec:06d}.json', {'sim_sec': sec, 'vehicle_routes': {'complete': True}})
        # Existence/size fixtures only, deliberately not trajectory evidence.
        for suffix in ('.fzp', '.lsa'):
            (self.run / ('synthetic' + suffix)).write_bytes(b'SYNTHETIC HEADER ONLY\n')

    def validate(self):
        original_open = io.open
        def guarded_open(file, *args, **kwargs):
            if isinstance(file, (str, os.PathLike)) and Path(file).suffix.lower() in ('.fzp', '.lsa', '.err', '.jpg', '.inpx', '.sig'):
                raise AssertionError('Native trajectory/asset content read during validation')
            return original_open(file, *args, **kwargs)
        with patch.object(driver, 'ROOT', self.root), patch('io.open', guarded_open), \
                patch.object(driver, 'validate_gates', side_effect=AssertionError('Live gate')), \
                patch.object(driver.subprocess, 'Popen', side_effect=AssertionError('COM/model execution')):
            return driver.validate_run(self.run, self.name, 'baseline', 'synthetic-network-sha', self.refs)

    def test_08_complete_synthetic_readback_and_terminal_boundary(self):
        result = self.validate()
        self.assertEqual(result['status'], 'execution_and_command_readback_passed')
        self.assertEqual(result['signal_ramp_readback']['strict_one_second_cadence']['groups'], 130)
        self.assertEqual(result['vsl_apply_readback_rows'], 66)
        self.assertFalse(result['native_large_files_hashed_or_scanned'])
        self.assertFalse(result['trajectory_equivalence_or_performance_claim'])
        self.assertTrue(result['window']['include_post_step1050'])
        self.assertFalse(result['window']['include_immediate1050'])

    def test_09_missing_terminal_readback_fails(self):
        dump_csv(self.trace_path, [row for row in self.trace_rows if row['sim_sec'] != '1050'])
        with self.assertRaisesRegex(ValueError, 'readback failed'):
            self.validate()

    def test_10_applied_command_mutation_or_vsl_readback_fails(self):
        original = driver.csv_rows(self.applied_path)
        for column, value in (('speed_kph', '119'), ('readback', '120|NaN'), ('readback', '120')):
            rows = copy.deepcopy(original)
            rows[0][column] = value
            dump_csv(self.applied_path, rows)
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                self.validate()

    def test_11_provenance_mismatch_and_missing_key_fail(self):
        original = driver.load(self.prov_path)
        for key, value in (('seed', 14), ('controller', 'wu-link'), ('state_log_interval_sec', 150)):
            p = copy.deepcopy(original)
            p[key] = value
            dump_json(self.prov_path, p)
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate()
        p = copy.deepcopy(original)
        del p['env']['RW_VEHICLE_ROUTES']
        dump_json(self.prov_path, p)
        with self.assertRaisesRegex(ValueError, 'environment mismatch'):
            self.validate()

    def test_12_wrong_raw_time_incomplete_routes_or_empty_native_fails(self):
        path = self.dec / 'state_001050.json'
        for raw in ({'sim_sec': 900, 'vehicle_routes': {'complete': True}},
                    {'sim_sec': 1050, 'vehicle_routes': {'complete': False}}, {'sim_sec': 1050}):
            dump_json(path, raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.validate()
        dump_json(path, {'sim_sec': 1050, 'vehicle_routes': {'complete': True}})
        (self.run / 'synthetic.fzp').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'absent or empty'):
            self.validate()


class TrajectoryGate(unittest.TestCase):
    """Tiny generated FZP only; actual large original FZP is never opened."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fixed_trajectory_test_', dir=ROOT / 'diagnostics')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.actual_run, self.old_run = self.directory / 'new', self.directory / 'old'
        self.actual_run.mkdir(); self.old_run.mkdir()
        self.actual, self.original = self.actual_run / 'new.fzp', self.old_run / 'old.fzp'
        self.body = b'$VEHICLE:SIMSEC;NO;LINK;LANE;POS;SPEED\r\n1.00;1;71;1;3.00;10.00\r\n1050.00;1;56;1;5.00;30.00\r\n'
        self.original.write_bytes(b'ORIGINAL DATE AND RUN\r\n' + self.body)
        self.actual.write_bytes(b'NEW DATE AND RUN, DIFFERENT PREAMBLE SIZE\r\n' + self.body)
        self.original_sha = driver.sha(self.original)

    def compare(self):
        return driver.compare_trajectory_files(self.actual, self.original,
                                               expected_reference_sha256=self.original_sha)

    def test_13_equal_payload_with_different_preamble_and_whole_hash_passes(self):
        result = self.compare()
        self.assertTrue(result['valid'])
        self.assertEqual(result['different_fields'], [])
        self.assertEqual(result['actual']['rows'], 2)
        self.assertEqual(result['actual']['last_sec'], 1050)
        self.assertNotEqual(result['actual']['file_sha256'], result['reference']['file_sha256'])
        self.assertEqual(result['actual']['payload_sha256'], result['reference']['payload_sha256'])
        self.assertEqual(result['reference']['file_sha256'], self.original_sha)

    def test_14_changed_data_order_or_header_fails(self):
        changes = {
            'physical value': self.body.replace(b';30.00', b';29.00'),
            'column header': self.body.replace(b';SPEED', b';DELAY'),
            'row order': b'$VEHICLE:SIMSEC;NO;LINK;LANE;POS;SPEED\r\n1050.00;1;56;1;5.00;30.00\r\n1.00;1;71;1;3.00;10.00\r\n',
        }
        for label, data in changes.items():
            self.actual.write_bytes(data)
            with self.subTest(label=label):
                result = self.compare()
                self.assertFalse(result['valid'])
                self.assertTrue(result['different_fields'])

    def test_15_matching_but_short_terminal_or_reference_change_fails(self):
        short = self.body.replace(b'1050.00', b'1049.00')
        self.actual.write_bytes(short); self.original.write_bytes(short)
        self.original_sha = driver.sha(self.original)
        result = self.compare()
        self.assertTrue(result['ordered_payload_exact'])
        self.assertFalse(result['terminal1050_valid'])
        self.assertFalse(result['valid'])
        self.original.write_bytes(short + b'1050.00;2;56;1;8.00;30.00\r\n')
        with self.assertRaisesRegex(ValueError, 'Original FZP changed'):
            self.compare()

    def test_16_file_mutation_during_helper_final_hash_is_rejected(self):
        from diagnostics import audit_observed_nc_trajectory as helper
        original_payload = helper.payload
        def mutate_after_payload(path):
            result = original_payload(path)
            if path == self.actual:
                with path.open('ab') as stream:
                    stream.write(b'changed after helper hash\n')
            return result
        with patch.object(helper, 'payload', side_effect=mutate_after_payload), \
                self.assertRaisesRegex(ValueError, 'changed during full payload'):
            self.compare()

    def test_17_baseline_provenance_binds_source_run_and_physical_inputs(self):
        # The shape is taken from the real small v3 provenance; only paths/run
        # labels/network values refer to synthetic test files here.
        p = json.loads(small_read(ACTUAL_RUN / ('run_provenance_' + RUN_NAME + '.json')).decode('utf-8-sig'))
        old_prov = self.old_run / 'run_provenance_old.json'
        new_prov = self.actual_run / 'run_provenance_new.json'
        dump_json(old_prov, p)
        a = copy.deepcopy(p); a['controller'] = 'diagnostic-signal-profile'
        dump_json(new_prov, a)
        reference = {'run': driver.relative(self.old_run), 'source_run': 'old',
                     'provenance_sha256': driver.sha(old_prov), 'fzp': driver.relative(self.original),
                     'fzp_sha256': self.original_sha}
        self.assertTrue(driver.validate_baseline_trajectory(self.actual_run, 'new', reference)['valid'])
        for key, value in (('sim_period_sec', 1049), ('seed', 14)):
            modified = copy.deepcopy(a); modified[key] = value
            dump_json(new_prov, modified)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'provenance/time'):
                driver.validate_baseline_trajectory(self.actual_run, 'new', reference)
        modified = copy.deepcopy(a)
        modified['files']['demand_profile']['sha256'] = 'other demand'
        dump_json(new_prov, modified)
        with self.assertRaisesRegex(ValueError, 'physical input source SHA'):
            driver.validate_baseline_trajectory(self.actual_run, 'new', reference)
        dump_json(new_prov, a)
        dump_json(old_prov, {**p, 'sim_period_sec': 1049})
        with self.assertRaisesRegex(ValueError, 'Original provenance changed'):
            driver.validate_baseline_trajectory(self.actual_run, 'new', reference)


class NaturalExitGate(unittest.TestCase):
    def gate(self, inventories, *, exit_code=0):
        now, calls = [0.0], []
        def inventory(*, timeout_sec):
            calls.append(timeout_sec)
            return copy.deepcopy(inventories[min(len(calls)-1, len(inventories)-1)])
        def sleep(seconds):
            self.assertGreater(seconds, 0)
            now[0] += seconds
        with patch.object(driver, 'process_inventory', side_effect=inventory), \
                patch.object(driver.time, 'monotonic', side_effect=lambda: now[0]), \
                patch.object(driver.time, 'sleep', side_effect=sleep), \
                patch.object(driver.subprocess, 'Popen', side_effect=AssertionError('No process launch or termination')):
            report = driver.post_watchdog_process_gate(exit_code)
        return report, calls

    def test_19_delayed_natural_exit_preserves_observations(self):
        process = {'pid': 51256, 'name': 'VISSIM200', 'start_utc': '2026-09-10T06:52:54.8058010Z'}
        report, calls = self.gate([[process], [process], []])
        self.assertTrue(report['valid'])
        self.assertEqual(report['status'], 'empty_process_inventory')
        self.assertEqual(report['initial_processes'], [process])
        self.assertEqual(report['final_processes'], [])
        self.assertEqual([r['processes'] for r in report['observations']], [[process], [process], []])
        self.assertEqual(report['wait_elapsed_sec'], 1.0)
        self.assertEqual(calls, [30.0, 29.5, 29.0])
        self.assertFalse(report['process_termination_performed'])

    def test_20_new_pid_or_reused_pid_creation_time_stops_immediately(self):
        process = {'pid': 51256, 'name': 'VISSIM200', 'start_utc': '2026-09-10T06:52:54.8058010Z'}
        for new in ({**process, 'pid': 999}, {**process, 'start_utc': '2026-09-10T06:52:55.8058010Z'}):
            with self.subTest(new=new):
                report, calls = self.gate([[process], [new], []])
                self.assertFalse(report['valid'])
                self.assertEqual(report['status'], 'new_process_identity_observed')
                self.assertEqual(report['new_identities'], [new])
                self.assertEqual(report['initial_processes'], [process])
                self.assertEqual(len(calls), 2)
                self.assertEqual(report['wait_elapsed_sec'], 0.5)

    def test_21_timeout_preserves_survivor_and_nonzero_exit_never_waits(self):
        process = {'pid': 51256, 'name': 'VISSIM200', 'start_utc': '2026-09-10T06:52:54.8058010Z'}
        report, calls = self.gate([[process]])
        self.assertFalse(report['valid'])
        self.assertEqual(report['status'], 'initial_processes_did_not_exit_before_deadline')
        self.assertEqual(report['wait_elapsed_sec'], 30.0)
        self.assertEqual(report['final_processes'], [process])
        self.assertTrue(all(0 < bound <= 30 for bound in calls))
        self.assertFalse(report['process_termination_performed'])
        failed, no_calls = self.gate([[process]], exit_code=7)
        self.assertFalse(failed['valid'])
        self.assertEqual(failed['status'], 'watchdog_failed_no_wait')
        self.assertEqual(failed['observations'], [])
        self.assertIsNone(failed['final_processes'])
        self.assertEqual(failed['wait_elapsed_sec'], 0.0)
        self.assertEqual(no_calls, [])


class SerialFailureGate(unittest.TestCase):
    def test_18_baseline_mismatch_preserves_both_hashes_and_stops_before_treatment(self):
        # Mock the external watchdog/gates only; execute the actual serial state
        # machine and its filesystem evidence saving in a new temporary root.
        with tempfile.TemporaryDirectory(prefix='serial_gate_') as directory:
            root = Path(directory)
            profile, writer = root / 'profile', root / 'writer'
            profile.mkdir(); writer.mkdir(); (root / 'diagnostics').mkdir()
            for path in (root / 'native.json', root / 'runtime.json', profile / 'manifest.json', writer / 'validation.json'):
                dump_json(path, {})
            flat = {'outputs': {arm + '.inpx': {'destination_sha256': arm + '-sha'} for arm in driver.ARMS}}
            mismatch = {'valid': False, 'actual': {'payload_sha256': 'different'},
                        'reference': {'payload_sha256': 'original'}, 'different_fields': ['payload_sha256']}
            argv = ['driver', '--name', 'unit', '--execute', '--native-gate', 'native.json', '--native-gate-sha256', 'fake',
                    '--source-manifest', 'runtime.json', '--source-manifest-sha256', 'fake', '--python', sys.executable]
            with patch.object(driver, 'ROOT', root), patch.object(driver, 'PROFILE', profile), patch.object(driver, 'WRITER', writer), \
                    patch.object(sys, 'argv', argv), patch.object(driver, 'validate_gates', return_value=({}, {}, flat, {}, {'source_run': 'fixture'})), \
                    patch.object(driver, 'validate_powershell_runtime', return_value={'synthetic': True}), \
                    patch.object(driver, 'process_inventory', return_value=[]), patch.object(driver, 'assert_pins'), \
                    patch.object(driver, 'validate_run', return_value={'synthetic_validation': True}), \
                    patch.object(driver, 'validate_baseline_trajectory', return_value=mismatch), \
                    patch.object(driver.subprocess, 'Popen') as launch, patch.object(sys, 'stderr', io.StringIO()):
                launch.return_value.pid = 12345
                launch.return_value.wait.return_value = 0
                self.assertEqual(driver.main(), 1)
                self.assertEqual(launch.call_count, 1)
            report = driver.load(root / 'diagnostics/fixed_beta300v3_experiments/unit/manifest.json')
            self.assertEqual(report['status'], 'failed_preserved_stop')
            self.assertFalse(report['valid'])
            self.assertEqual(report['arms'][0]['baseline_trajectory_comparison'], mismatch)
            self.assertTrue((root / 'diagnostics/fixed_beta300v3_experiment.lock').is_file())
            for arm in report['arms'][1:]:
                self.assertEqual(arm['status'], 'pending')
                self.assertFalse((root / arm['run']).exists())


def load_tests(loader, tests, pattern):
    # Run shared small-fixture tests once; RunValidation inherits fixture setup.
    suite = unittest.TestSuite(loader.loadTestsFromTestCase(SmallFixtures))
    suite.addTests(RunValidation(name) for name in loader.getTestCaseNames(RunValidation)
                   if name not in loader.getTestCaseNames(SmallFixtures))
    suite.addTests(loader.loadTestsFromTestCase(TrajectoryGate))
    suite.addTests(loader.loadTestsFromTestCase(SerialFailureGate))
    suite.addTests(loader.loadTestsFromTestCase(NaturalExitGate))
    return suite


if __name__ == '__main__':
    unittest.main()
