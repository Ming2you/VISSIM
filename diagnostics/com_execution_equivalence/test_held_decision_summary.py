"""Keep failed calculation reports separate from verified hold commands."""
import csv
from pathlib import Path
import tempfile
import unittest

from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200 import analyze_pair as a
from evaluation.controllers.action_csv_schema import ACTION_CSV_FIELDS


class HeldDecisionSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='held-summary-')
        self.root = Path(self.tmp.name)
        assert self.root.resolve().parent == Path(tempfile.gettempdir()).resolve()
        self.addCleanup(self.tmp.cleanup)
        self.rows = []
        for key, speed in [('RW_FW_E_S0', 110), ('RW_FW_W_S0', 110), ('RW_FW_E_S13', 90)]:
            row = dict.fromkeys(ACTION_CSV_FIELDS, '')
            row.update(kind='vsl', id=key, speed_kph=str(speed))
            self.rows.append(row)
        for i in range(8):
            row = dict.fromkeys(ACTION_CSV_FIELDS, '')
            row.update(kind='ramp_meter', id=f'RM{i}', green_sec='8')
            self.rows.append(row)
        self.write_csv(750)
        self.write_csv(900)
        a.save(self.root/'action_000900.json', {'metadata': {'controller_status': 'hold_previous_error'}})
        # A failed optimizer can leave these artifacts. They are not a prediction.
        (self.root/'action_000900.joint.json').write_text('NOT A COMPLETED REPORT')
        self.repin()

    def write_csv(self, sec):
        with (self.root/f'action_{sec:06d}.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=ACTION_CSV_FIELDS)
            writer.writeheader()
            writer.writerows(self.rows)

    def repin(self):
        self.recovery = {'passed': True, 'holds': {'900': {
            'command_json_sha256': a.sha256(self.root/'action_000900.json'),
            'command_csv_sha256': a.sha256(self.root/'action_000900.csv'),
            'optimizer_success': False}}}

    def summary(self):
        return a.decision_summary(self.root, 900, 1050, recovery=self.recovery)

    def test_hold_does_not_reuse_optimizer_artifact_or_invent_gain(self):
        result = self.summary()
        self.assertEqual(result['held_error_decisions'], 1)
        self.assertEqual(result['optimized_decisions'], 0)
        row, = result['decisions']
        self.assertFalse(row['optimizer_success'])
        self.assertIsNone(row['predicted_ttt_reduction_from_held_veh_h'])
        self.assertIsNone(row['pfo'])
        self.assertFalse(row['native_execution_verified'])
        self.assertEqual(set(row['meter_green_change_sec'].values()), {0})

    def test_missing_or_rejected_recovery_proof_fails(self):
        with self.assertRaises(AssertionError):
            a.decision_summary(self.root, 900, 1050)
        self.recovery['passed'] = False
        with self.assertRaises(AssertionError):
            self.summary()

    def test_changed_csv_after_recovery_verification_fails(self):
        self.rows[-1]['green_sec'] = '9'
        self.write_csv(900)
        with self.assertRaises(AssertionError):
            self.summary()

    def test_trust_region_not_waived(self):
        self.rows[-1]['green_sec'] = '5'
        self.write_csv(900)
        self.repin()
        with self.assertRaises(AssertionError):
            self.summary()

    def test_entry_fixed_speed_not_waived(self):
        self.rows[0]['speed_kph'] = '90'
        self.write_csv(900)
        self.repin()
        with self.assertRaises(AssertionError):
            self.summary()

    def test_recovery_and_command_status_must_agree(self):
        a.save(self.root/'action_000900.json', {'metadata': {'controller_status': 'ok'}})
        self.repin()
        with self.assertRaises(AssertionError):
            self.summary()


if __name__ == '__main__':
    unittest.main()
