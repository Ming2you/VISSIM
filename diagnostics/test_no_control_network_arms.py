"""Small NC driver guards; no simulator, process inventory, model or FZP scan."""
import contextlib
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from diagnostics import run_no_control_network_arms as n


def demands():
    return '\n'.join(f'DEMAND_WRITE_BEGIN no={1000+i} time_int=1 before=0 target=400 timer_sec=1\n'
                     f'DEMAND_WRITE_DONE no={1000+i} time_int=1 timer_sec=2' for i in range(204))


class DriverTests(unittest.TestCase):
    def test_three_command_domains(self):
        for arm in n.d.ARMS:
            cmd = n.arm_command('codex_nc5400_r01_' + arm + '_s13', arm, n.ROOT / 'evaluation/runs/new')
            for k, v in {'-Controller': 'no-control', '-SimPeriod': '5400', '-Seed': '13',
                         '-Tuning': str(n.TUNING), '-StartupStallSec': '300', '-StallSec': '300', '-MaxAttempts': '1'}.items():
                self.assertEqual(cmd[cmd.index(k)+1], v)
            self.assertNotIn('-ForceStepwise', cmd); self.assertIn('-NoGlobalKill', cmd)

    def test_environment_excludes_trace_and_force(self):
        with patch.dict(os.environ, {'RW_FORCE_STEPWISE': '1', 'RW_EVALUATION_TRACE_DIR': 'bad',
                                     'RW_DECISION_PROFILE_DIR': 'bad', 'PYTHONPATH': 'bad'}):
            env = n.environment(n.d.DEFAULT_PYTHON)
        for key in ('RW_FORCE_STEPWISE', 'RW_EVALUATION_TRACE_DIR', 'RW_DECISION_PROFILE_DIR', 'PYTHONPATH'):
            self.assertNotIn(key, env)
        self.assertEqual(env['RW_OFFSET_WRITER'], 'experiment'); self.assertEqual(env['RW_SIGNAL_OBSERVATION'], '0')

    def test_plan_never_launches_or_validates(self):
        with (patch('sys.argv', ['driver']), patch.object(n, 'gates', side_effect=AssertionError('no gate')),
              contextlib.redirect_stdout(io.StringIO()) as stream):
            self.assertEqual(n.main(), 0)
        plan = json.loads(stream.getvalue()); self.assertFalse(plan['executed']); self.assertEqual(len(plan['arms']), 3)

    def test_old74_rows_and_bad_control_rejected(self):
        rows = n.d.csv_rows(n.OLD / ('decisions_' + n.OLD.name) / 'action_000001.csv')
        n.nc_rows(rows)
        for key, value, index in [('speed_kph', '80', 0), ('green_sec', '5', 66), ('rate_vph', 'NaN', 66)]:
            changed = [dict(row) for row in rows]; changed[index][key] = value
            with self.assertRaises(ValueError): n.nc_rows(changed)
        with self.assertRaises(ValueError): n.nc_rows(rows + [rows[0]])

    def test204_serial_unique_demand(self):
        self.assertEqual(len(n.demand_writes(demands())), 204)
        for bad in (demands().replace('no=1203', 'no=1202'), demands().rsplit('\n', 1)[0],
                    demands().replace('target=400', 'target=NaN', 1), demands().replace('DONE no=1000', 'DONE no=1001', 1)):
            with self.assertRaises(ValueError): n.demand_writes(bad)

    def test_cp949_path_lines_ignored_ascii_records_strict(self):
        raw = '원본 경로: 학술'.encode('cp949') + b'\r\nRUN_MODE=CONTINUOUS_STATIC controller=no-control\r\nDECISIONS_FAILED=0\r\n'
        self.assertEqual(n.ascii_control_log(raw), 'RUN_MODE=CONTINUOUS_STATIC controller=no-control\nDECISIONS_FAILED=0')
        with self.assertRaises(UnicodeDecodeError):
            n.ascii_control_log(b'DEMAND_WRITE_BEGIN ' + '변조'.encode('cp949'))
        source = Path(n.__file__).read_text(encoding='utf-8')
        self.assertIn("lock = ROOT / f'diagnostics/no_control_network_arms_{args.name}.lock'", source)
        self.assertNotIn('fixed_beta300v3_experiment.lock', source)

    def test_native_config_only_exact_model_hook_diff(self):
        base = n.d.load(n.nc_config.BASE); candidate = n.d.load(n.TUNING)
        diff = n.nc_config.validate(base, candidate)
        self.assertEqual(len(diff), 14)
        self.assertEqual(candidate['actuation'], base['actuation'])
        self.assertEqual(candidate['freeway'], base['freeway'])
        candidate['actuation']['real_world_signal_control']['apply_to_no_control'] = True
        with self.assertRaises(ValueError): n.nc_config.validate(base, candidate)

    def test_native_lsa_gate_checks_geometry_and_event_order(self):
        from diagnostics import audit_nc5400_native_signals as audit
        from tempfile import TemporaryDirectory
        record = dict.fromkeys(('preamble_sha256', 'event_sha256'), 'exact')
        record.update(preamble_bytes=100, rows=30845, group_event_counts={'1:1': 1}, states={'green': 1},
                      modes={'Fixed Time': 1}, first_sec=1, last_sec=5400)
        with TemporaryDirectory(dir=n.ROOT/'diagnostics') as directory:
            folder=Path(directory); (folder/'native.lsa').write_bytes(b'fixture')
            with patch.object(n, 'OLD', folder), patch.object(n.d, 'load', return_value={}), \
                 patch.object(audit, 'used_signal_programs', return_value={'selected_by_sc':{'1':'s'},'without_program':{}}):
                with patch.object(audit, 'events', return_value=record): self.assertTrue(n.native_signal_reference(folder)['valid'])
                for key in ('preamble_sha256','event_sha256'):
                    with patch.object(audit, 'events', side_effect=[record,{**record,key:'changed'}]):
                        with self.assertRaises(ValueError): n.native_signal_reference(folder)

    def test_native_programs_select_actual42_not_unused_inventory(self):
        from copy import deepcopy
        from diagnostics.audit_nc5400_native_signals import used_signal_programs
        old=n.d.load(n.OLD/('run_provenance_'+n.OLD.name+'.json'))
        actual=used_signal_programs(old)
        self.assertEqual(len(actual['selected_by_sc']),42)
        self.assertEqual(actual['inventory_count'],73)
        self.assertEqual(actual['ignored_unreferenced_files'],31)
        used=set(actual['source_sha256'])
        unused=next(i for i,r in enumerate(old['signal_programs']) if n.d.relative(n.d.workspace_path(r['path'])) not in used)
        altered=deepcopy(old);altered['signal_programs'][unused]['sha256']='unused inventory is not an executed program'
        self.assertEqual(used_signal_programs(altered)['selected_by_sc'],actual['selected_by_sc'])
        selected=next(i for i,r in enumerate(old['signal_programs']) if n.d.relative(n.d.workspace_path(r['path'])) in used)
        altered=deepcopy(old);altered['signal_programs'][selected]['sha256']='0'*64
        with self.assertRaises(ValueError):used_signal_programs(altered)
        altered=deepcopy(old);altered['files']['network']['sha256']='0'*64
        with self.assertRaises(ValueError):used_signal_programs(altered)

    def test_reuse_requires_explicit_sha(self):
        with patch('sys.argv',['driver','--reuse-baseline-review','some.json']):
            with self.assertRaises(ValueError):n.main()

    def test_review_exception_allowlist_is_only_two_checker_revisions(self):
        from diagnostics.review_nc5400_baseline import OLD_CHECKERS,source_review_exceptions
        self.assertEqual(set(OLD_CHECKERS),{'diagnostics/run_no_control_network_arms.py','diagnostics/audit_nc5400_native_signals.py'})
        historical={**OLD_CHECKERS,'evaluation/controllers/runtime.py':'a'*64,'input.json':'b'*64}
        current={**historical,**dict.fromkeys(OLD_CHECKERS,'c'*64)}
        runtime={'evaluation/controllers/runtime.py':'a'*64}
        self.assertEqual(len(source_review_exceptions(historical,current,runtime)),2)
        for key in ('input.json','evaluation/controllers/runtime.py'):
            with self.assertRaises(ValueError):source_review_exceptions(historical,{**current,key:'d'*64},runtime)
        with self.assertRaises(ValueError):source_review_exceptions(historical,historical,runtime)
        wrong=dict(historical);wrong[next(iter(OLD_CHECKERS))]='e'*64
        with self.assertRaises(ValueError):source_review_exceptions(wrong,current,runtime)

    def test_baseline_fullpayload_guard_and_no1050_reuse(self):
        expected = {'header': 'H', 'payload_sha256': 'S', 'payload_bytes': 100, 'rows': 26693633, 'first_sec': 1, 'last_sec': 5400}
        from diagnostics import audit_observed_nc_trajectory as audit
        with (patch.object(n.d, 'load', return_value={'trajectory': {'payloads': [expected]}}),
              patch.object(n.d, 'single_fzp', return_value=Path(__file__)), patch.object(audit, 'payload', return_value=dict(expected))):
            self.assertTrue(n.baseline_trajectory(n.OLD)['valid'])
            with patch.object(audit, 'payload', return_value={**expected, 'last_sec': 1050}):
                self.assertFalse(n.baseline_trajectory(n.OLD)['valid'])
            with patch.object(audit, 'payload', return_value={**expected, 'rows': 26693632}):
                self.assertFalse(n.baseline_trajectory(n.OLD)['valid'])


if __name__ == '__main__':
    unittest.main()
