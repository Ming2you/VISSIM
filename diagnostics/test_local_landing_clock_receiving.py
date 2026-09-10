"""Peer check: corrected local receiving due is service_step + canonical delay."""
import copy
from types import SimpleNamespace
import unittest
from diagnostics.test_link_predictor import tiny, fix
from src.models.urban_queue_model import _link_delay_steps


class ReceivingClockTests(unittest.TestCase):
    def test_receiving_transfer_uses_current_service_boundary(self):
        _, follower, model, state = tiny(stock={'sig_a': 3.})
        follower._wu._offramp_drain_flow = {'a': [('SC', 'movement')]}
        follower._wu._specs = {'movement': {'receiving_link': 'recv'}}
        initial = copy.deepcopy(vars(state))
        # Explicit one-vehicle accepted service fixture; the clock, storage and
        # receiving-delay implementations themselves remain canonical.
        def accepted_service(off, eligible, receiving, control, dt):
            n = min(1., eligible) if off == 'a' else 0.
            return n / dt, {'recv': n / dt} if n else {}
        follower._local_offramp_drain = accepted_service
        landing = fix.LocalLandingState(follower, model, state)
        service_step = landing.step
        landing.advance(SimpleNamespace(), {}, 5 / 3600)
        view = SimpleNamespace(urban_link_storage={k: landing.capacity[k] - v for k, v in landing.stock.items()},
                               urban_link_speed_kph=landing.speeds)
        delay = _link_delay_steps(view, landing.cfg, 'recv')
        self.assertEqual(delay, 3)
        self.assertEqual(landing.pending['recv'], {service_step + delay: 1.})
        self.assertEqual(landing.step, service_step + 1)
        self.assertEqual(landing.stock['sig_a'], 2.)
        self.assertEqual(landing.stock['recv'], 1.)
        self.assertEqual(landing.ledger['max_abs_residual_veh'], 0.)
        self.assertEqual(vars(state), initial)


if __name__ == '__main__':
    unittest.main()
