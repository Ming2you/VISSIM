"""Reject invalid completed command sequences before reporting native gains."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200.analyze_pair import decision_summary


class ClosedLoopDecisionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.write_csv(750, 10)
        for sec, green in ((900, 8), (1050, 6)):
            self.write_csv(sec, green)
            selected = dict(feasible=True, held_objective=100, warm_start_objective=99,
                            selected_objective=98, prediction_ttt_reduction=2,
                            pfo_warm_start={k: 0 for k in ('max_iterations', 'executed_iterations',
                                'accepted_iterations', 'converged', 'status', 'seconds')},
                            candidates=[], converged=False, sdmpc_after_pfo_seconds=1,
                            final_constraints={})
            self.write_json(sec, '.joint.json', dict(completed=True, selection=selected))
            self.write_json(sec, '.json', {'command': sec})
            self.bind(sec)

    def path(self, sec, suffix):
        return self.folder / f'action_{sec:06d}{suffix}'

    def write_json(self, sec, suffix, data):
        self.path(sec, suffix).write_text(json.dumps(data), encoding='utf-8')

    def write_csv(self, sec, green, speed=90, entry_speed=110):
        with self.path(sec, '.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['kind', 'id', 'speed_kph', 'green_sec'])
            writer.writeheader()
            for key in ('RW_FW_E_S0', 'RW_FW_W_S0'):
                writer.writerow(dict(kind='vsl', id=key, speed_kph=entry_speed))
            writer.writerow(dict(kind='vsl', id='RW_FW_E_S13', speed_kph=speed))
            for k in range(8):
                writer.writerow(dict(kind='ramp_meter', id=f'RM_{k}', green_sec=green))

    def bind(self, sec):
        binding = dict(prewrite_binding_passed=True, written_command_binding_passed=True)
        for key, suffix in (('action_csv', '.csv'), ('action_json', '.json')):
            path = self.path(sec, suffix)
            binding[key] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.write_json(sec, '.joint_written.json', binding)

    def audit(self):
        return decision_summary(self.folder, 900, 1200)

    def test_valid_nonconverged_feasible_sequence(self):
        self.assertEqual(len(self.audit()['decisions']), 2)

    def test_rejects_infeasible_completed_decision(self):
        path = self.path(900, '.joint.json')
        report = json.loads(path.read_text())
        report['selection']['feasible'] = False
        path.write_text(json.dumps(report))
        with self.assertRaises(AssertionError):
            self.audit()

    def test_rejects_tampered_written_csv(self):
        self.write_csv(900, 8, speed=80)
        with self.assertRaises(AssertionError):
            self.audit()

    def test_rejects_vsl_outside_discrete_grid(self):
        for speed in (55, 120):
            with self.subTest(speed=speed):
                self.write_csv(900, 8, speed=speed)
                self.bind(900)
                with self.assertRaises(AssertionError):
                    self.audit()

    def test_rejects_entry_speed_change(self):
        self.write_csv(900, 8, entry_speed=100)
        self.bind(900)
        with self.assertRaises(AssertionError):
            self.audit()

    def test_rejects_first_step_slew_against_warmup(self):
        self.write_csv(900, 7)
        self.bind(900)
        with self.assertRaises(AssertionError):
            self.audit()

    def test_rejects_later_step_slew(self):
        self.write_csv(1050, 5)
        self.bind(1050)
        with self.assertRaises(AssertionError):
            self.audit()

    def test_rejects_duplicate_meter(self):
        with self.path(900, '.csv').open('a', encoding='utf-8') as f:
            f.write('ramp_meter,RM_0,,8\n')
        self.bind(900)
        with self.assertRaises(AssertionError):
            self.audit()


if __name__ == '__main__':
    unittest.main()
