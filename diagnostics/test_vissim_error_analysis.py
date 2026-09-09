from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.analyze_vissim_errors import parse


class ErrorAnalysisTests(unittest.TestCase):
    def test_removals_and_skipped_decisions_are_distinct(self):
        lines = [
            'Warning\tSimulation second 467.0: After 45.0 seconds of waiting for lane change the vehicle 590 (on Static Vehicle Route 1159 - 1) was removed from link 310 at position 93.3.\tNetwork object type: Vehicle',
            'Warning\tSimulation second 178.0: Vehicle 1013 ignores the desired speed decision 33 because it has left link 10274 at position 8.46 in the same time step.',
            'Warning\tSimulation second 225.0: Vehicle 1350 ignores the static routing decision 1102 because it has left link 201 at position 17.18 in the same time step.',
            'Warning\tStatic Vehicle Routing Decision 1102 is located only 5.431 m upstream of the first connector.',
        ]
        rows, result = parse(lines, {'310': True, '10274': False, '201': False})
        self.assertEqual(len(rows), 3)
        self.assertEqual(result['lane_change_removal_inside'], 1)
        self.assertEqual(result['event_counts'], {'lane_change_removal': 1, 'skipped_desired_speed': 1, 'skipped_route': 1})
        self.assertEqual(result['skipped_desired_speed_by_decision'], {'33': 1})
        self.assertEqual(result['skipped_route_by_decision'], {'1102': 1})
        with self.assertRaises(ValueError):
            parse(lines, {})


if __name__ == '__main__':
    unittest.main()
