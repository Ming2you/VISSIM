import copy
import unittest
from types import SimpleNamespace

from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305 import candidate as original
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.validation338.install import apply_service_floor


def fixture(rate):
    group = dict(members=original.west.MEMBERS, signal='SC12', phase='SC12_p4',
                 receiver='SC12_to_SC6', service_veh_h=rate)
    return SimpleNamespace(network=SimpleNamespace(
        regular_alias_pool={'groups':{original.west.GROUP:group}},
        movement_capacity_by_movement_veh_h={k:rate for k in original.west.MEMBERS}))


class ServiceFloorTransfer(unittest.TestCase):
    def test_training_state_keeps_original_capacity(self):
        old = fixture(960.)
        new = copy.deepcopy(old)
        evidence = original.evidence()
        original.install(old,2400,evidence)
        apply_service_floor(new,2700,evidence)
        self.assertEqual(old.network.regular_alias_pool,new.network.regular_alias_pool)
        self.assertEqual(old.network.movement_capacity_by_movement_veh_h,
                         new.network.movement_capacity_by_movement_veh_h)

    def test_higher_current_shared_support_is_preserved(self):
        cfg = fixture(2006.530612244898)
        before = copy.deepcopy(cfg)
        record = apply_service_floor(cfg,2700,original.evidence())
        self.assertTrue(record['retained_higher_current_floor'])
        self.assertEqual(before.network.regular_alias_pool,cfg.network.regular_alias_pool)
        self.assertEqual(before.network.movement_capacity_by_movement_veh_h,
                         cfg.network.movement_capacity_by_movement_veh_h)

    def test_inconsistent_alias_rates_are_rejected(self):
        cfg = fixture(2006.530612244898)
        cfg.network.movement_capacity_by_movement_veh_h[original.west.MEMBERS[0]] = 3000.
        with self.assertRaises(ValueError):
            apply_service_floor(cfg,2700,original.evidence())


if __name__ == '__main__':
    unittest.main()
