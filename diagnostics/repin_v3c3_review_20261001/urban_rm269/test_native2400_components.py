"""Measurement identities, including lateral movement and native deletion."""
import unittest
from audit_native2400_components import ramp_balance, grouped_model_stock, ramp_stock


class MeasurementTests(unittest.TestCase):
    def test_each_lane_uses_its_own_head_position(self):
        frame = {'vehicles': [(1,10482,1,374.15), (2,10482,2,374.15)]}
        self.assertEqual(ramp_stock(frame,10482,{1:374.119678,2:374.217333}),
                         {'pre':[0,1], 'post':[1,0]})

    def test_future_gate_transit_is_physical_stock_not_an_arrival_rate(self):
        groups = {'approach66': {'initial_model_stock_keys': ['storage:in_SC1004_S', 'movement:left']}}
        values = {'storage:in_SC1004_S': 23., 'movement:left': 104., 'transit:gate:in_SC1004_S': 56.}
        self.assertEqual(grouped_model_stock(values, groups)['approach66'], 183.)

    def test_head_is_not_merge_when_post_head_stock_accumulates(self):
        row = ramp_balance(dict(pre=[10, 10], post=[0, 0]),
            dict(pre=[6, 8], post=[3, 1]), arrival=0, head_by_lane=[4, 2], removed=0)
        self.assertEqual((row['head'], row['merge']), (6, 2))

    def test_lane_change_cannot_be_counted_as_lane_merge(self):
        row = ramp_balance(dict(pre=[2, 2], post=[3, 0]),
            dict(pre=[2, 2], post=[1, 2]), arrival=0, head_by_lane=[0, 0], removed=0)
        self.assertEqual(row['merge'], 0)
        self.assertEqual(row['merge_plus_net_posthead_lateral_outflow_by_lane'], [2, -2])

    def test_deletion_is_not_merge_or_assigned_to_unknown_lane(self):
        row = ramp_balance(dict(pre=[2, 2], post=[3, 0]),
            dict(pre=[2, 2], post=[2, 0]), arrival=0, head_by_lane=[0, 0], removed=1)
        self.assertEqual(row['merge'], 0)
        self.assertIsNone(row['merge_plus_net_posthead_lateral_outflow_by_lane'])

    def test_inconsistent_head_boundary_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'balances disagree'):
            ramp_balance(dict(pre=[2, 2], post=[0, 0]),
                dict(pre=[1, 2], post=[0, 0]), arrival=0, head_by_lane=[0, 0], removed=0)


if __name__ == '__main__':
    unittest.main()
