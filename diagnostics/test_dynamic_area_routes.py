"""Physical native positions, calibration cohorts, and conserved re-projection."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics')]
from evaluation.controllers import area_dynamic_routes as dynamic_routes
from calibrate_dynamic_area_routes import scan_rows
from probe_area_endpoint import fixture


class CalibrationTests(unittest.TestCase):
    def test_same_vehicle_sources_and_outcomes_count_once(self):
        complete, censored = scan_rows([(0, 'a', '61'), (5, 'a', '61'), (10, 'a', '387'),
            (15, 'a', '10023'), (20, 'a', '1220000402'), (1, 'b', '10621'), (6, 'b', '10616')])
        self.assertEqual([(row['origin'], row['outcome']) for row in complete],
                         [('SC1005_to_SC107', 'through'), ('SC1004_to_SC107', 'right')])
        self.assertEqual(censored, [])

    def test_lost_cohort_is_not_redistributed_to_completed_turn(self):
        complete, censored = scan_rows([(0, 'a', '58'), (5, 'a', '52'), (0, 'b', '10501'), (5, 'b', '999')])
        self.assertEqual(complete, [])
        self.assertEqual(len(censored), 2)
        self.assertEqual({row['reason'] for row in censored},
                         {'end_or_interior_disappearance', 'unobserved_turn_or_left_reviewed_path'})

    def test_native_decision_behind_merge_is_not_applicable(self):
        data = json.loads((ROOT / 'diagnostics/dynamic_area_nc13_calibration.json').read_text())
        for origin in ('SC1004_to_SC107', 'SC1005_to_SC107'):
            row = data['native_decision_positions'][origin]
            self.assertGreater(row['entry_position_m'], row['decision_position_m'])
            self.assertFalse(row['decision_ahead_of_entry'])
        for origin in ('SC1005_to_SC1004', 'SC107_to_SC1004'):
            self.assertTrue(data['native_decision_positions'][origin]['decision_ahead_of_entry'])


class ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.state, _, cls.raw = fixture(dynamic_routes=True)

    def test_four_phantoms_removed_with_observed_prior_counts(self):
        document = json.loads((ROOT / 'diagnostics/dynamic_area_routes_ver2.json').read_text())
        calibration = json.loads((ROOT / document['calibration']['path']).read_text())
        for row in document['topology_repairs']:
            self.assertNotIn(row['remove_movement'], self.cfg.network.urban_movements)
            betas = []
            for name in row['keep_movements']:
                spec = self.cfg.network.urban_movements[name]
                expected = calibration['priors'][spec['origin']]['shares'][spec['turn']]
                self.assertAlmostEqual(spec['beta'], expected)
                betas.append(spec['beta'])
            self.assertAlmostEqual(sum(betas), 1)

    def test_initial_physical_stock_and_actual_source_379_are_preserved(self):
        initial = sum(row['inside'] for row in self.state._control_area_ledger.stocks.values())
        self.assertAlmostEqual(initial, 1763.0155647050337)
        assignments = self.state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        self.assertEqual(assignments['379'], {'storage:in_SC107_S': 3.0})
        self.assertNotIn('storage:in_SC108_W', assignments['379'])

    def test_four_bypass_routes_have_native_edges_and_model_receivers(self):
        document, _, _, _ = dynamic_routes.checked_evidence('diagnostics/dynamic_area_routes_ver2.json')
        for name, row in document['by_movement'].items():
            route = self.cfg.network.control_area_routes['movement:' + name]
            self.assertEqual(route['path'], row['path'])
            self.assertEqual(route['path'][-1], '10621')
            self.assertIsInstance(route['target_inside'], bool)

    def test_flag_absent_is_identity_and_bad_network_fails_before_mutation(self):
        cfg = deepcopy(self.cfg)
        before = deepcopy(vars(cfg.network))
        detectors = {'sentinel': []}
        self.assertIs(dynamic_routes.configure(cfg, detectors, {}, state_json={})[0], detectors)
        self.assertEqual(vars(cfg.network), before)
        with patch.object(dynamic_routes, 'snapshot_network_sha256', return_value='wrong'):
            with self.assertRaisesRegex(ValueError, 'hashes differ'):
                dynamic_routes.configure(cfg, detectors, {'urban': {'movements': {
                    'dynamic_physical_route_topology': 'diagnostics/dynamic_area_routes_ver2.json'}}}, state_json=self.raw)
        self.assertEqual(vars(cfg.network), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
