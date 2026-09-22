"""Regression checks for lossless qualification and durable failed gates."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from diagnostics import sdmpc_qualification_report as report


class QualificationReportTests(unittest.TestCase):
    def test_tuple_key_collisions_and_types_survive_json(self):
        value = {'constraints': {'feasible': True}, 'tokens': {
            ('FW_E', 0): b'actual', "('FW_E', 0)": 'different',
            1: {'nested': (1, 2)}, '1': 'string'},
            'reserved': {report.TAG: 'not_an_encoding', 'items': []}}
        self.assertEqual(value, report.restore_evidence(json.loads(json.dumps(report.json_evidence(value)))))

    def test_nonfinite_or_unknown_evidence_is_rejected(self):
        for value in (float('nan'), float('inf'), object()):
            with self.subTest(value=type(value).__name__), self.assertRaises((ValueError, TypeError)):
                report.json_evidence({'value': value})

    def test_real_command_and_saved_response_serialize_without_losing_witness(self):
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        from src.models.state import ControlAction
        lane = ROOT.parent / 'sdmpc-lane-plant-20260921'
        path = lane / 'evaluation/runs/lane_native_nc2850_s13_v2/decisions_lane_native_nc2850_s13_v2/action_000001.json'
        recorded = json.loads(path.read_text(encoding='utf-8'))
        fields = ControlAction.__dataclass_fields__
        control = ControlAction(**{k: v for k, v in recorded.items() if k in fields})
        saved = json.loads((ROOT / 'diagnostics/metanet_compare_20260921/native_response_000450.json').read_text())
        response = {'control': control, 'final_score': saved['results'][0],
                    'tuple_key_regression_fixture': {('FW_E', 0): 42.0}}
        selection = {'price_state': {}, 'final_constraints': {'feasible': True}, 'feasible': True}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            evidence = report.save_solution(target, response, selection, adapter)
            report.atomic_json(target / 'result.json', {'completed': True, **evidence})
            readback = report.restore_evidence(json.loads((target / 'result.json').read_text()))
            self.assertEqual(readback['response'], {**response, 'control': vars(control)})
            self.assertTrue(readback['native_command_json_serializable'])
            self.assertTrue((target / 'solution.pickle').is_file())
            self.assertEqual(readback['native_command_preview']['ramp_metering'], control.ramp_metering)

    def test_raw_checkpoint_survives_native_preview_serialization_failure(self):
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        from src.models.state import ControlAction
        control = ControlAction(diagnostics={'invalid_json_key': {('FW_E', 0): 1}})
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            with self.assertRaises(TypeError):
                report.save_solution(target, {'control': control},
                    {'price_state': {}, 'final_constraints': {}}, adapter)
            self.assertTrue((target / 'solution.pickle').is_file())
            self.assertFalse((target / 'result.json').exists())

    def test_build_failure_has_terminal_failed_report(self):
        with tempfile.TemporaryDirectory() as folder:
            here = Path(folder)
            with patch.object(sys, 'argv', ['test', 'missing-state.json', 'missing-action.json', 'failed']), \
                 patch('scripts.offline_harness_20260904.build', side_effect=RuntimeError('build failure fixture')):
                with self.assertRaisesRegex(RuntimeError, 'build failure fixture'):
                    report.run(here, __file__, lane=False)
            saved = json.loads((here / 'failed/result.json').read_text())
            self.assertIs(saved['completed'], False)
            self.assertIs(saved['native_command_applied'], False)
            self.assertEqual(saved['error']['message'], 'build failure fixture')


if __name__ == '__main__':
    unittest.main()
