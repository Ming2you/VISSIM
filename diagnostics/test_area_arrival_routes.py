"""Physical gate-to-stopline paths; no fabricated route around a junction."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics')]
from probe_area_endpoint import fixture


class ArrivalRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.state, _, _ = fixture()

    def test_sc1_entry_reaches_real_signal_before_turn(self):
        routes = self.cfg.network.control_area_routes
        arrival = routes['arrival:SC1_S_to_N_SC101']
        departure = routes['movement:SC1_S_to_N_SC101']
        self.assertFalse(arrival['source_inside'])
        self.assertTrue(arrival['target_inside'])
        self.assertEqual(arrival['inward_crossings_per_vehicle'], 1)
        self.assertTrue(departure['source_inside'])
        for path in arrival['physical_paths']:
            self.assertEqual(path[0], '1220042300')
            self.assertEqual(path[-1], '1220006903')
            self.assertIn('10595', path)
        self.assertEqual(departure['shared_turn_movements'], ['SC1_S_SC107_to_N_SC101'])

    def test_midblock_signal_does_not_become_a_different_modeled_junction(self):
        arrival = self.cfg.network.control_area_routes['arrival:SC6_S_to_N_SC103']
        self.assertTrue(arrival['target_inside'])
        self.assertEqual(arrival['outward_crossings_per_vehicle'], 0)
        self.assertEqual(arrival['physical_paths'][0][0], '138')
        self.assertEqual(arrival['physical_paths'][0][-1], '1210018302')

    def test_loop_through_freeway_cannot_prove_impossible_same_leg_turn(self):
        route = self.cfg.network.control_area_routes['movement:SC1004_E_SC107_to_E_SC1005']
        self.assertIsNone(route['target_inside'])
        self.assertEqual(route['status'], 'no_match')

    def test_arrival_can_be_known_while_departure_stays_unresolved(self):
        routes = self.cfg.network.control_area_routes
        self.assertIsInstance(routes['arrival:SC2001_N_to_S']['target_inside'], bool)
        self.assertIsNone(routes['movement:SC2001_N_to_S']['target_inside'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
