"""Service uses the current urban boundary; FW landing uses its end boundary."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from diagnostics.test_link_predictor import tiny, fix
from src.models.urban_queue_model import _inflow_delay_steps


class LandingClockTests(unittest.TestCase):
    def fixture(self, due):
        _, follower, model, state = tiny(stock={'sig_a': 3})
        state.offramp_transit_buffer = {'sig_a': {due: 3}}
        unchanged = copy.deepcopy(vars(state))
        landing = fix.LocalLandingState(follower, model, state)
        calls = []
        def drain(off, ready, receivers, control, dt):
            calls.append((landing.step, off, ready))
            return min(1., ready)/dt, {}
        follower._local_offramp_drain = drain
        return landing, state, unchanged, calls

    def test_due_next_waits_one_service_and_retains_physical_stock(self):
        landing, state, unchanged, calls = self.fixture(1)
        landing.advance(SimpleNamespace(), {}, 5/3600)
        self.assertEqual(calls[0], (0, 'a', 0.))
        self.assertEqual(landing.stock['sig_a'], 3.)
        self.assertEqual(landing.step, 1)
        landing.advance(SimpleNamespace(), {}, 5/3600)
        self.assertEqual([row for row in calls if row[1] == 'a'], [(0, 'a', 0.), (1, 'a', 3.)])
        self.assertEqual(landing.stock['sig_a'], 2.)
        self.assertEqual(landing.ledger['max_abs_residual_veh'], 0.)
        self.assertEqual(vars(state), unchanged)

    def test_due_now_and_past_are_ready_at_current_boundary(self):
        for due in (-1, 0):
            with self.subTest(due=due):
                landing, state, unchanged, calls = self.fixture(due)
                landing.advance(SimpleNamespace(), {}, 5/3600)
                self.assertEqual(calls[0], (0, 'a', 3.))
                self.assertEqual(landing.stock['sig_a'], 2.)
                self.assertEqual(vars(state), unchanged)

    def test_two_urban_services_preserve_the_fw_admission_boundary(self):
        landing, _, _, state = tiny()
        before = copy.deepcopy(vars(state))
        landing.advance(SimpleNamespace(), {}, 10/3600)
        self.assertEqual(landing.step, 2)
        landing.land({'a': 360.}, 10/3600)
        self.assertEqual(landing.stock['sig_a'], .5)
        self.assertEqual(landing.stock['tail'], .5)
        self.assertEqual(landing.pending['sig_a'], {2+_inflow_delay_steps(landing.cfg): .5})
        self.assertEqual(landing.ledger['arrivals_veh'], 1.)
        self.assertEqual(landing.ledger['max_abs_residual_veh'], 0.)
        self.assertEqual(vars(state), before)

    def test_actual_900_pending_boundary_and_first_fw_landing(self):
        from diagnostics.test_shared_service_pool import inputs
        from src.controllers.priced_wu_link_controller import LinkAgentWuFollower
        cfg, state, action, *_ = inputs()
        storage = cfg.network.off_ramp_storage_link['OR_F_W']
        stock = cfg.network.urban_link_storage_veh[storage]-state.urban_link_storage[storage]
        start = round(state.time_sec/cfg.simulation.T_u_sec)
        private = state.copy()
        private.offramp_transit_buffer[storage] = {start+1: stock}
        agent = LinkAgentWuFollower(cfg)
        model = agent._local_freeway_models[cfg.network.off_ramp_from_freeway['OR_F_W']]
        landing = fix.LocalLandingState(agent, model, private)
        original = fix.LocalLandingState.arrived
        observed = []
        def query(owner, key):
            value = original(owner, key)
            if key == storage:
                observed.append((owner.step, value))
            return value
        with patch.object(fix.LocalLandingState, 'arrived', query):
            landing.advance(action, dict(state.ramp_queue), cfg.simulation.T_f_h)
        self.assertEqual(observed[0], (180, 0.))
        self.assertTrue(any(step == 181 and value == stock for step, value in observed))
        self.assertEqual(landing.step, 182)
        prior = sum(landing.stock.values())
        landing.land({'OR_F_W': 360.}, cfg.simulation.T_f_h)
        self.assertAlmostEqual(sum(landing.stock.values())-prior, 1.)
        self.assertIn(189, landing.pending[storage])
        self.assertLess(landing.ledger['max_abs_residual_veh'], 1e-8)


if __name__ == '__main__':
    unittest.main()
