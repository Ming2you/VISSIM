"""Composition checks against the actual saved configuration, no rollout."""
from copy import deepcopy
from pathlib import Path
import pickle
import unittest
from candidate import prepare, install, hook, west, east

HERE = Path(__file__).resolve().parent


class Composition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg, _, _ = pickle.loads((HERE.parent/'citysplit287/forecast2400/initial.pickle').read_bytes())

    def test_independent_physical_budgets_and_no_other_changes(self):
        cfg = deepcopy(self.cfg)
        before = pickle.dumps(cfg, protocol=5)
        caps, groups, metadata = prepare(cfg, 2400)
        self.assertEqual(pickle.dumps(cfg, protocol=5), before)
        self.assertEqual(set(groups)-set(cfg.network.regular_alias_pool['groups']), {west.GROUP, east.GROUP})
        self.assertEqual({k for k,v in caps.items() if v != cfg.network.movement_capacity_by_movement_veh_h[k]}, set(west.MEMBERS)|set(east.MEMBERS))
        self.assertEqual(groups[west.GROUP]['service_veh_h'], 960)
        self.assertAlmostEqual(groups[east.GROUP]['service_veh_h'], 1677.2727272727273)
        self.assertEqual(metadata['SC12W']['cutoff_sec'], 2400)
        self.assertEqual(metadata['SC16E']['cutoff_sec'], 2400)

    def test_failed_composition_is_transactional(self):
        cfg = deepcopy(self.cfg)
        cfg.network.urban_movements['SC16_E_to_N_SC12']['receiving_link'] = 'wrong'
        before = pickle.dumps(cfg, protocol=5)
        with self.assertRaises(ValueError):
            install(cfg, 2400)
        self.assertEqual(pickle.dumps(cfg, protocol=5), before)

    def test_hook_restored_after_failure(self):
        from evaluation.controllers import regular_alias_service
        old = regular_alias_service.configure
        with self.assertRaises(RuntimeError):
            with hook():
                self.assertIsNot(regular_alias_service.configure, old)
                raise RuntimeError('diagnostic')
        self.assertIs(regular_alias_service.configure, old)


if __name__ == '__main__':
    unittest.main()
