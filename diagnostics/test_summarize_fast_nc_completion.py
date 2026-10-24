"""Small receipt fixtures only: no FZP scan, model, native process or run."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics import summarize_fast_nc as m


class CompletionReceipts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='completion_fixture_', dir=m.ROOT / 'diagnostics')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.assertTrue(self.base.is_relative_to(m.ROOT / 'diagnostics'))
        self.run = self.base / 'fixture_control'
        self.run.mkdir()
        self.receipt_path = self.run / 'completion_receipt.json'
        self.provenance_path = self.run / 'run_provenance_fixture_control.json'
        self.log_path = self.run / 'runlog_fixture_control.txt'
        self.state_path = self.run / 'state_fixture_control.csv'
        self.provenance = {'run_id': 'fixture-id', 'name': self.run.name, 'sim_period_sec': 5400,
                           'controller': 'wu-link', 'seed': 13, 'files': {'network': {'path': 'fixture.inpx'}}}
        self.write_json(self.provenance_path, self.provenance)
        self.log = '\n'.join(['STAGE=SIM_DONE', 'SIM_SEC=5400', 'DECISIONS_FAILED=0',
            'OBSERVATION_FAILURES=0', 'SIGNAL_FAILURES=0', 'ACTION_FORMAT_FAILURES=0', 'COM_FAILURES=0']) + '\n'
        self.log_path.write_text(self.log, encoding='utf-8')
        self.states = 'sim_sec,controller_status\n1,ok\n900,ok\n5400,ok\n'
        self.state_path.write_text(self.states, encoding='utf-8')
        errors = []
        for name in ('vissim_network.err', 'vissim_simulation_001.err'):
            path = self.run / name
            path.write_bytes(b'')
            errors.append({'name': name, 'path': str(path), 'bytes': 0, 'sha256': self.sha(path)})
        self.receipt = {'schema': 'selected-control-completion/v1', 'run_id': 'fixture-id',
            'name': self.run.name, 'run_directory': str(self.run), 'exit_code': 0,
            'cscript_exit_code': None, 'completed': True, 'terminal_sec': 5400, 'owned_native_alive': False,
            'provenance_path': str(self.provenance_path), 'provenance_sha256': self.sha(self.provenance_path),
            'runlog_path': str(self.log_path), 'state_csv_path': str(self.state_path), 'error_files': errors}
        self.write_json(self.receipt_path, self.receipt)

    @staticmethod
    def write_json(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def read(self, receipt=None):
        self.write_json(self.receipt_path, self.receipt if receipt is None else receipt)
        return m.completion_inputs(self.run, self.receipt_path)

    def test_valid_canonical_is_read_only_and_retains_identity(self):
        before = {str(p): self.sha(p) for p in self.run.iterdir()}
        path, info, errors, proof = self.read()
        self.assertEqual(path, self.receipt_path)
        self.assertEqual(info, {'network': 'fixture.inpx', 'prepared': None, 'seed': 13})
        self.assertEqual([p.name for p in errors], ['vissim_network.err', 'vissim_simulation_001.err'])
        self.assertEqual(proof['controller'], 'wu-link')
        self.assertEqual(proof['run_id'], 'fixture-id')
        self.assertIsNone(proof['cscript_exit_code'])
        self.assertEqual(before, {str(p): self.sha(p) for p in self.run.iterdir()})

    def test_existing_fast_without_option_keeps_its_contract(self):
        manifest = {'completed': True, 'exit_code': 0, 'terminal_sec': 5400,
            'owned_native_alive': False, 'network': 'old-network', 'prepared': 'old-prepared', 'seed': 13,
            'error_files': [{'name': 'baseline.err'}, {'name': 'baseline_001.err'}]}
        self.write_json(self.run / 'run.json', manifest)
        (self.run / 'stdout.txt').write_text('STAGE=SIM_DONE\nSIM_SEC=5400\n', encoding='utf-8')
        path, actual, errors, proof = m.completion_inputs(self.run)
        self.assertEqual(path, self.run / 'run.json')
        self.assertEqual(actual, manifest)
        self.assertEqual(errors, [self.run / 'baseline.err', self.run / 'baseline_001.err'])
        self.assertIsNone(proof)
        # The explicit canonical option never silently falls back to a valid fast receipt.
        bad = {**self.receipt, 'completed': False}
        with self.assertRaises(ValueError):
            self.read(bad)

    def canonical_horizon(self, end):
        self.write_json(self.provenance_path, {**self.provenance, 'sim_period_sec': end})
        self.log_path.write_text(self.log.replace('5400', str(end)), encoding='utf-8')
        self.state_path.write_text(self.states.replace('5400', str(end)), encoding='utf-8')
        return {**self.receipt, 'terminal_sec': end,
                'provenance_sha256': self.sha(self.provenance_path)}

    def test_extended_canonical_horizon_requires_all_clocks_agree(self):
        for end in (7200, 9000, 9000.0):
            with self.subTest(end=end):
                receipt = self.canonical_horizon(end)
                self.assertEqual(self.read(receipt)[3]['terminal_sec'], end)
                self.log_path.write_text(self.log, encoding='utf-8')
                with self.assertRaises(ValueError):
                    self.read(receipt)
                receipt = self.canonical_horizon(end)
                self.state_path.write_text(self.states, encoding='utf-8')
                with self.assertRaises(ValueError):
                    self.read(receipt)
                receipt = self.canonical_horizon(end)
                self.write_json(self.provenance_path, self.provenance)
                with self.assertRaises(ValueError):
                    self.read({**receipt, 'provenance_sha256': self.sha(self.provenance_path)})
        for end in (5399, 6000, 9001, '9000', True, float('nan'), float('inf')):
            with self.subTest(invalid_end=end), self.assertRaises(ValueError):
                self.read(self.canonical_horizon(end))

    def native_receipt(self, end):
        manifest = {'completed': True, 'exit_code': 0, 'terminal_sec': end,
            'owned_native_alive': False, 'error_files': [{'name': 'baseline_001.err'}]}
        self.write_json(self.run / 'run.json', manifest)
        (self.run / 'baseline_001.err').write_bytes(b'')
        (self.run / 'stdout.txt').write_text(f'STAGE=SIM_DONE\nSIM_SEC={end}\n', encoding='utf-8')
        return manifest

    def test_extended_native_horizon_requires_agreeing_complete_log(self):
        for end in (7200, 9000, 9000.0):
            with self.subTest(end=end):
                manifest = self.native_receipt(end)
                self.assertEqual(m.completion_inputs(self.run)[1], manifest)
        for end in (5399, 6000, 9001, '9000', True, float('nan'), float('inf')):
            with self.subTest(invalid_end=end), self.assertRaises(ValueError):
                self.native_receipt(end)
                m.completion_inputs(self.run)
        for log in ('STAGE=SIM_DONE\nSIM_SEC=5400\n',
                    'STAGE=SIM_DONE\nSIM_SEC=9000\nSIM_SEC=9001\n',
                    'STAGE=RUNNING\nSIM_SEC=9000\n',
                    'STAGE=SIM_DONE\nSIM_SEC=9000\nERROR=failed\n'):
            self.native_receipt(9000)
            (self.run / 'stdout.txt').write_text(log, encoding='utf-8')
            with self.subTest(log=log), self.assertRaises(ValueError):
                m.completion_inputs(self.run)
        for key, value in (('completed', False), ('exit_code', 1), ('exit_code', False),
                           ('owned_native_alive', True)):
            manifest = self.native_receipt(9000)
            self.write_json(self.run / 'run.json', {**manifest, key: value})
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                m.completion_inputs(self.run)

    def test_native_horizon_reaches_measurement_without_5400_truncation(self):
        self.native_receipt(9000)
        (self.run / 'vissim_eval').mkdir()
        (self.run / 'vissim_eval' / 'fixture.fzp').write_bytes(b'fixture')
        ledger = self.base / 'membership.json'
        self.write_json(ledger, {})
        membership = {str(i): i < 635 for i in range(1236)}
        with patch.object(m, 'MEMBERSHIP', ledger), \
             patch.object(m, 'physical_membership_from_ledger', return_value=membership), \
             patch.object(m, 'terminal_lengths', return_value={}), \
             patch.object(m, 'cell_geometry', return_value=({}, {}, {})), \
             patch.object(m, 'parse_bytes', return_value={'partial_tail_bytes': 0,
                 'unparsed_removal_lines': [], 'events': [], 'counts': {}}), \
             patch.object(m, 'native_frames', return_value=[]), \
             patch.object(m, 'summarize_stream', side_effect=RuntimeError('measurement reached')) as measure, \
             patch.object(m.sys, 'argv', ['summarize_fast_nc.py', '--run', str(self.run),
                                        '--out', str(self.base / 'summary')]):
            for canonical in (False, True):
                if canonical:
                    self.write_json(self.receipt_path, self.canonical_horizon(9000))
                    m.sys.argv += ['--completion-receipt', str(self.receipt_path)]
                with self.subTest(canonical=canonical), self.assertRaisesRegex(RuntimeError, 'measurement reached'):
                    m.main()
                self.assertEqual(measure.call_args.kwargs['end'], 9000)

    def test_extended_horizon_does_not_relax_canonical_control_contract(self):
        for end in (7200, 9000):
            with self.subTest(end=end), self.assertRaisesRegex(ValueError, 'provenance identity/end mismatch'):
                self.read({**self.receipt, 'terminal_sec': end})

    def test_extended_stream_covers_last_window_and_rejects_missing_terminal_frame(self):
        # One synthetic vehicle; validates terminal accounting without loading a native FZP.
        def frames(last):
            return ((sec, {1: (2, 1, 0.0, 0.0)}) for sec in range(1, last + 1))
        bounds = {'E': list(range(22)), 'W': list(range(22))}
        result = m.summarize_stream(frames(9000), {'2': True}, {}, bounds, {}, [], end=9000)
        last = [r for r in result['road_windows'] if r['link'] == 2][-1]
        self.assertEqual((last['start_sec'], last['end_sec'], last['end_n']), (8100, 9000, 1))
        self.assertEqual(max(r['end_sec'] for r in result['source_inputs']), 9000)
        self.assertEqual(max(r['sec'] for r in result['cell_samples']), 9000)
        with self.assertRaisesRegex(ValueError, 'Incomplete FZP extent'):
            m.summarize_stream(frames(8999), {'2': True}, {}, bounds, {}, [], end=9000)

    def test_completion_and_closed_native_are_required(self):
        variants = [('completed', False), ('exit_code', 1), ('exit_code', False),
                    ('owned_native_alive', True), ('owned_native_alive', None),
                    ('terminal_sec', 5399), ('terminal_sec', '5400'), ('terminal_sec', float('nan')),
                    ('schema', 'unknown/v1'), ('cscript_exit_code', 0)]
        for key, value in variants:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.read({**self.receipt, key: value})

    def test_run_identity_and_directory_cannot_be_substituted(self):
        for key, value in [('run_id', 'different'), ('run_id', ''), ('name', 'other'),
                           ('name', '../fixture_control'), ('run_directory', str(self.base))]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.read({**self.receipt, key: value})
        elsewhere = self.base / 'completion_receipt.json'
        self.write_json(elsewhere, self.receipt)
        with self.assertRaises(ValueError):
            m.completion_inputs(self.run, elsewhere)

    def test_evidence_paths_must_be_exact_run_local_files(self):
        for key in ('provenance_path', 'runlog_path', 'state_csv_path'):
            original = Path(self.receipt[key])
            other = self.base / original.name
            other.write_bytes(original.read_bytes())
            for value in (str(other), original.name, str(self.run / 'missing')):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.read({**self.receipt, key: value})

    def test_provenance_sha_and_identity_both_verified(self):
        with self.assertRaises(ValueError):
            self.read({**self.receipt, 'provenance_sha256': '0' * 64})
        for key, value in [('run_id', 'old-run'), ('name', 'other'), ('sim_period_sec', 1050), ('controller', '')]:
            self.write_json(self.provenance_path, {**self.provenance, key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.read({**self.receipt, 'provenance_sha256': self.sha(self.provenance_path)})

    def test_log_terminal_and_error_markers(self):
        for text in (self.log.replace('SIM_SEC=5400', 'SIM_SEC=5399'),
                     self.log.replace('SIM_SEC=5400', 'SIM_SEC=nan'),
                     self.log.replace('STAGE=SIM_DONE', 'STAGE=RUNNING'),
                     self.log + 'ERROR=anything\n', self.log + 'STRICT_DECISION_FAILED\n'):
            self.log_path.write_text(text, encoding='utf-8')
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.read()

    def test_each_actual_failure_counter_is_single_zero(self):
        for counter in ('DECISIONS_FAILED', 'OBSERVATION_FAILURES', 'SIGNAL_FAILURES', 'ACTION_FORMAT_FAILURES', 'COM_FAILURES'):
            for text in (self.log.replace(counter + '=0\n', ''),
                         self.log.replace(counter + '=0', counter + '=1'),
                         self.log + counter + '=0\n'):
                self.log_path.write_text(text, encoding='utf-8')
                with self.subTest(counter=counter, text=text), self.assertRaises(ValueError):
                    self.read()

    def test_state_terminal_order_finite_and_fallback(self):
        for text in ('sim_sec,controller_status\n', self.states.replace('5400', '5399'),
                     self.states.replace('900,ok', '900,fallback'), self.states.replace('900,ok', 'nan,ok'),
                     self.states.replace('900,ok', '1,ok'), self.states + '5401,ok\n'):
            self.state_path.write_text(text, encoding='utf-8')
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.read()

    def test_runtime_err_cannot_be_omitted_or_duplicated(self):
        for rows in ([], self.receipt['error_files'][:1], self.receipt['error_files'] * 2):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.read({**self.receipt, 'error_files': rows})
        Path(self.receipt['error_files'][1]['path']).unlink()
        with self.assertRaises(ValueError):
            self.read()

    def test_err_hash_size_name_and_path_are_bound(self):
        for key, value in [('sha256', '0' * 64), ('bytes', 1), ('bytes', False),
                           ('name', '../vissim_simulation_001.err'), ('path', str(self.provenance_path))]:
            bad = deepcopy(self.receipt)
            bad['error_files'][1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.read(bad)
        Path(self.receipt['error_files'][1]['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            self.read()

    def test_measurement_geometry_and_terminal_functions_remain_exact(self):
        source = Path(m.__file__).read_text(encoding='utf-8-sig')
        expected = {
            'summarize_stream': 'd0b62701fddaef4fc0d59f6376fe80eead379cead8d7531455eb6e65cf35f291',
            'cell_geometry': '39f5ef0971cced3198a165a420aea1725f152ee80b8fb375a8eb0d32b92ef4ed',
            'terminal_candidate': '2667405bb7a2af7d218381c28c9a34f4490e573af8ed3d28daaa93c7768da822'}
        actual = {node.name: hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest()
                  for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name in expected}
        self.assertEqual(actual, expected)
        self.assertEqual(self.sha(m.ROOT / 'scripts/measure_control_area.py'),
                         '8f6df1cf9ef9bcd646799c81703a6cdcae4a0f42ae84484136f53889833d7327')


if __name__ == '__main__':
    unittest.main()
