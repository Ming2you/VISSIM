"""Replay the first actual full-MPC receiving race, with conserved rejected stock."""
import copy
import json
from pathlib import Path
import pickle
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'diagnostics'), str(ROOT / 'vendor/NumSim-mine')]


class LegsplitReceivingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from evaluation.controllers import runtime_setup, vissim_stackelberg_adapter as adapter
        path = ROOT / 'diagnostics/area_main_preflight/first_ramp_clip_50548.pkl'
        if not path.is_file():
            raise unittest.SkipTest('Actual first clipping fixture missing')
        cls.payload = pickle.loads(path.read_bytes())
        cfg = cls.payload['cfg']
        runtime_setup.install_worker_runtime(adapter, cfg, {'network_path': str(ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx')}, {})
        from evaluation.controllers import urban_flow_accounting as urban
        cls.urban = urban
        from diagnostics.fixed_source_reference import function
        # This is the immutable pre-receipt *wrapper*, with the current body's
        # unchanged default (no deferred sinks). It is not an old whole model.
        cls.old = staticmethod(function('evaluation/controllers/urban_flow_accounting.py',
                                        'legsplit_substep_accounted', vars(urban)))
        cls.fixed = staticmethod(urban.legsplit_substep_accounted)

    def run_step(self, function, *, mutate=None):
        p = copy.deepcopy(self.payload)
        if mutate:
            mutate(p)
        initial = p['state'].copy()
        function(p['state'], p['control'], p['demand'], p['cfg'], *p['args'], **p['kwargs'])
        return initial, p['state'], p['cfg']

    def test_actual_failed_candidate_reproduces_exact_clip(self):
        _, final, _ = self.run_step(self.old)
        tracked = sum(final._control_area_ledger.stocks['ramp:R_D_W'].values())
        self.assertAlmostEqual(tracked - final.ramp_queue['R_D_W'], 0.22302305524194777)
        self.assertEqual(final.ramp_queue['R_D_W'], 153.2)

    def test_rejected_vehicle_stays_in_original_source_and_only_accepted_is_emitted(self):
        _, old, cfg = self.run_step(self.old)
        _, fixed, _ = self.run_step(self.fixed)
        key = 'SC1001_W_out'
        self.assertAlmostEqual(old.urban_link_storage[key] - fixed.urban_link_storage[key], .22302305524194777)
        self.assertAlmostEqual(sum(fixed._control_area_ledger.stocks['ramp:R_D_W'].values()), fixed.ramp_queue['R_D_W'])
        from evaluation.controllers.area_runtime import model_inventory
        inventory = model_inventory(fixed, cfg)
        # During a Tu step an already released vehicle legitimately waits for
        # the next Tf merge. All other physical stocks must already agree.
        for key, row in fixed._control_area_ledger.stocks.items():
            if not key.startswith('merge_pending:'):
                self.assertAlmostEqual(sum(row.values()), inventory.get(key, 0), places=6, msg=key)

    def test_same_step_does_not_mutate_input_candidate_and_repeats_exactly(self):
        before = pickle.dumps(self.payload, protocol=5)
        _, a, _ = self.run_step(self.fixed)
        _, b, _ = self.run_step(self.fixed)
        self.assertEqual({k:v for k,v in vars(a).items() if k != '_control_area_ledger'},
                         {k:v for k,v in vars(b).items() if k != '_control_area_ledger'})
        self.assertEqual(vars(a._control_area_ledger), vars(b._control_area_ledger))
        self.assertEqual(pickle.dumps(self.payload, protocol=5), before)

    def test_no_competition_preserves_every_state_field_and_flow(self):
        def more_space(p):
            p['cfg'].network.ramp_queue_max_veh_by_ramp['R_D_W'] += 100
        _, old, _ = self.run_step(self.old, mutate=more_space)
        _, fixed, _ = self.run_step(self.fixed, mutate=more_space)
        # The new receipt counter is adapter metadata, not a model state change.
        self.assertEqual({k:v for k,v in vars(old).items() if k != '_control_area_ledger'},
                         {k:v for k,v in vars(fixed).items() if k != '_control_area_ledger'})
        self.assertEqual(vars(old._control_area_ledger), vars(fixed._control_area_ledger))


if __name__ == '__main__':
    unittest.main(verbosity=2)
