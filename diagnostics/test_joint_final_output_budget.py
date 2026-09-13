"""Execute the canonical CLI's final output block with small files and a fake clock.

The AST slice uses the installed block unchanged, without initializing models or COM.
"""
import ast
from contextlib import nullcontext
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from evaluation.controllers.area_follower_objective import DecisionBudget, DecisionDeadline


SOURCE = Path(__file__).resolve().parents[1] / 'evaluation/controllers/vissim_stackelberg_adapter.py'


def final_output_code():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    candidates = [(index, node) for index, node in enumerate(main.body)
                  if isinstance(node, ast.Try) and any(
                      isinstance(item, ast.Constant) and item.value == 'final_action_validation_and_output'
                      for item in ast.walk(node))]
    if len(candidates) != 1:
        raise AssertionError('Expected one canonical final action output block')
    index, block = candidates[0]
    return compile(ast.Module(body=[main.body[index - 1], block], type_ignores=[]), str(SOURCE), 'exec')


class JointFinalOutputBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_code = final_output_code()

    def execute_output(self, folder, clock, *, json_delay=0., csv_delay=0., csv_error=None, budget=True,
                       validation_failure=None, validation_delay=0.):
        path = Path(folder) / 'action.json'
        events = []
        decision_budget = DecisionBudget(120., reserve_sec=10., started=0., cpu_started=0.) if budget else None
        def validate(stage):
            if validation_failure == stage:
                raise ValueError(stage + ' execution evidence mismatch')
            if stage == 'signal':
                clock[0] += validation_delay
            return {}
        def serialize(*args, **kwargs):
            events.append('json')
            clock[0] += json_delay
            return {'action': 'validated fixture'}
        def write_csv(out_csv, *args, **kwargs):
            events.append('csv')
            if csv_error:
                raise csv_error
            out_csv.write_text('kind,id\nsignal,SC7\n', encoding='utf-8')
            clock[0] += csv_delay
            return {'written': True}
        namespace = {'decision_budget': decision_budget, 'nullcontext': nullcontext, 'json': json,
            'out_json': path, 'out_csv': path.with_suffix('.csv'),
            'control_to_json_dict': serialize, 'write_action_csv': write_csv,
            'load_signal_group_actuation_plan': lambda: {}, 'control': SimpleNamespace(diagnostics={}), 'metadata': {},
            'prediction': {}, 'prediction_error': None,
            'cfg': SimpleNamespace(network=SimpleNamespace(control_area_enabled=True,
                control_area_meter_context={'sim_sec': 1050})), 'mapping': {},
            'segment_vsl_func': object(), 'actuation': {}, 'offset_writer': 'fixture',
            'joint_response': object(), 'joint_options': {}, 'args': SimpleNamespace(controller='wu-link'),
            'diagnostic_profile': SimpleNamespace(CONTROLLERS=()),
            'diagnostic_signal_profile': SimpleNamespace(CONTROLLER='diagnostic-fixture'),
            'offset_promotion': SimpleNamespace(evaluate=lambda: validate('offset'),
                resolve_writer=lambda *args, **kwargs: 'fixture',
                action_metadata=lambda *args: {}, WRITER_EXPERIMENT='experiment'),
            'signal_actuation_contract': SimpleNamespace(enabled=lambda net: True,
                validate_writer=lambda *args: validate('signal'))}
        failure = None
        with patch('time.perf_counter', side_effect=lambda: clock[0]), patch('time.process_time', return_value=0.), \
                patch('evaluation.controllers.area_meter_finalization.assert_writer',
                      side_effect=lambda *args, **kwargs: validate('meter')):
            try:
                exec(self.output_code, namespace)
            except Exception as exc:
                failure = exc
        receipt_path = path.with_suffix('.decision_budget.json')
        receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else None
        return path, events, failure, receipt

    def test_final_reserve_writes_action_and_success_receipt_after_search_expiry(self):
        with tempfile.TemporaryDirectory() as folder:
            path, events, failure, receipt = self.execute_output(folder, [115.], json_delay=1., csv_delay=2.)
            self.assertIsNone(failure)
            self.assertEqual(events, ['json', 'csv'])
            self.assertTrue(path.with_suffix('.csv').exists())
            self.assertTrue(path.with_suffix('.joint_written.json').exists())
            self.assertTrue(receipt['output_completed'])
            self.assertIsNone(receipt['output_error'])
            self.assertEqual(receipt['wall_sec'], 118.)
            scope = receipt['inclusive_scopes']['final_action_validation_and_output']
            self.assertEqual(scope['wall_sec'], 3.)
            self.assertEqual(scope['calls'], 1)

    def test_expired_final_budget_rejects_action_before_output_but_keeps_failure_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            path, events, failure, receipt = self.execute_output(folder, [120.])
            self.assertIsInstance(failure, DecisionDeadline)
            self.assertEqual(events, [])
            self.assertFalse(path.exists())
            self.assertFalse(path.with_suffix('.csv').exists())
            self.assertFalse(receipt['output_completed'])
            self.assertEqual(receipt['expired_stage'], 'final_action_validation')

    def test_offset_meter_and_signal_validation_failure_prevents_output_and_keeps_receipt(self):
        for stage in ('offset', 'meter', 'signal'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as folder:
                path, events, failure, receipt = self.execute_output(folder, [115.], validation_failure=stage)
                self.assertIsInstance(failure, ValueError)
                self.assertEqual(events, [])
                self.assertFalse(path.exists())
                self.assertFalse(path.with_suffix('.csv').exists())
                self.assertFalse(receipt['output_completed'])
                self.assertEqual(receipt['output_error'],
                    {'type': 'ValueError', 'message': stage + ' execution evidence mismatch'})
                self.assertEqual(receipt['inclusive_scopes']['final_action_validation_and_output']['calls'], 1)

    def test_validation_overrun_rejects_output_and_accounts_for_validation_time(self):
        with tempfile.TemporaryDirectory() as folder:
            path, events, failure, receipt = self.execute_output(folder, [119.], validation_delay=2.)
            self.assertIsInstance(failure, DecisionDeadline)
            self.assertEqual(events, [])
            self.assertFalse(path.exists())
            self.assertFalse(path.with_suffix('.csv').exists())
            self.assertFalse(receipt['output_completed'])
            self.assertEqual(receipt['expired_stage'], 'action_json_output')
            self.assertEqual(receipt['inclusive_scopes']['final_action_validation_and_output']['wall_sec'], 2.)

    def test_serialization_overrun_rejects_csv_and_preserves_partial_json_as_failed_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path, events, failure, receipt = self.execute_output(folder, [119.], json_delay=2.)
            self.assertIsInstance(failure, DecisionDeadline)
            self.assertEqual(events, ['json'])
            self.assertTrue(path.exists())
            self.assertFalse(path.with_suffix('.csv').exists())
            self.assertFalse(receipt['output_completed'])
            self.assertEqual(receipt['expired_stage'], 'action_csv_validation_and_output')
            self.assertEqual(receipt['overrun_sec'], 1.)

    def test_csv_overrun_propagates_failure_even_when_action_files_exist(self):
        with tempfile.TemporaryDirectory() as folder:
            path, events, failure, receipt = self.execute_output(folder, [119.], csv_delay=2.)
            self.assertIsInstance(failure, DecisionDeadline)
            self.assertEqual(events, ['json', 'csv'])
            self.assertTrue(path.exists())
            self.assertTrue(path.with_suffix('.csv').exists())
            self.assertFalse(receipt['output_completed'])
            self.assertEqual(receipt['expired_stage'], 'completed_action_output')
            self.assertTrue(receipt['application_requires_successful_process_exit'])
            self.assertEqual(receipt['output_error']['type'], 'DecisionDeadline')

    def test_writer_validation_error_propagates_and_is_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            error = ValueError('physical writer evidence mismatch')
            path, events, failure, receipt = self.execute_output(folder, [115.], csv_error=error)
            self.assertIs(failure, error)
            self.assertFalse(path.with_suffix('.csv').exists())
            self.assertEqual(events, ['json', 'csv'])
            self.assertFalse(receipt['output_completed'])
            self.assertEqual(receipt['output_error'],
                {'type': 'ValueError', 'message': 'physical writer evidence mismatch'})
            self.assertEqual(receipt['inclusive_scopes']['final_action_validation_and_output']['calls'], 1)

    def test_legacy_output_without_budget_is_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            path, events, failure, receipt = self.execute_output(folder, [999.], budget=False)
            self.assertIsNone(failure)
            self.assertEqual(events, ['json', 'csv'])
            self.assertTrue(path.with_suffix('.csv').exists())
            self.assertIsNone(receipt)


if __name__ == '__main__':
    unittest.main()
