"""T4 (plan C5, D-C (b)): the 10643 lane split of the aggregate off flow.

Held observed shares, exact sum (land(), lane_offramp_runtime.py:133-136) and
each lane inside its receiving room (capacities(), :112-120).
"""
from __future__ import annotations

import math
import types
import unittest

import n31_fixtures  # noqa: F401  (paths)
from evaluation.controllers.lane_coupling import lane_amounts_10643, split_10643

SPLIT = {'mode': 'observed_lane_shares_held', 'shares': [0.4, 0.6], 'information_cutoff_s': 900}


def rooms(a, b):
    """group_capacity['10643'] as capacities() returns it: two lanes [veh/h] + the inaccessible group."""
    return [a * 3600.0, b * 3600.0, 0.0]


class SplitTests(unittest.TestCase):

    def test_held_shares_when_rooms_allow(self):
        first, second = split_10643(1.0, rooms(5.0, 5.0), SPLIT)
        self.assertAlmostEqual(first, 0.4, places=15)
        self.assertAlmostEqual(second, 0.6, places=15)
        self.assertEqual(first + second, 1.0)

    def test_exact_sum_and_rooms(self):
        for amount in (0.0, 1e-9, 0.37, 1.2, 2.0):
            for a, b in ((0.1, 1.9), (1.9, 0.1), (1.0, 1.0), (0.0, 2.0), (2.0, 0.0)):
                for share in (0.0, 0.25, 0.5, 0.9, 1.0):
                    split = {**SPLIT, 'shares': [share, 1 - share]}
                    if amount > a + b:
                        continue
                    first, second = split_10643(amount, rooms(a, b), split)
                    self.assertLessEqual(abs(math.fsum([first, second]) - amount), 1e-12)
                    self.assertGreaterEqual(first, 0.0)
                    self.assertGreaterEqual(second, -1e-12)
                    self.assertLessEqual(first, a + 1e-12)
                    self.assertLessEqual(second, b + 1e-12)

    def test_water_fill_into_the_other_lane(self):
        first, second = split_10643(1.0, rooms(0.1, 5.0), SPLIT)
        self.assertAlmostEqual(first, 0.1, places=15)
        self.assertAlmostEqual(second, 0.9, places=15)
        first, second = split_10643(1.0, rooms(5.0, 0.2), SPLIT)
        self.assertAlmostEqual(first, 0.8, places=15)
        self.assertAlmostEqual(second, 0.2, places=15)

    def test_zero_room_lane(self):
        self.assertEqual(split_10643(0.5, rooms(0.0, 1.0), SPLIT), [0.0, 0.5])
        self.assertEqual(split_10643(0.0, rooms(0.0, 0.0), SPLIT), [0.0, 0.0])

    def test_rejections(self):
        with self.assertRaises(ArithmeticError):
            split_10643(3.0, rooms(1.0, 1.0), SPLIT)
        with self.assertRaises(ArithmeticError):
            split_10643(0.5, [3600.0, 3600.0, 1.0], SPLIT)
        with self.assertRaises(ValueError):
            split_10643(0.5, rooms(1.0, 1.0), {'mode': 'capacity_ratio', 'shares': [0.5, 0.5]})
        with self.assertRaises(ValueError):
            split_10643(0.5, rooms(1.0, 1.0), None)

    def test_forward_duals(self):
        """The split runs inside instrumented rollouts: Dual amounts keep the sum's tangent."""
        from evaluation.controllers import sdmpc_dual as ad
        trace = ad.Trace([1.0], track_stencils=False)
        amount = ad.Dual(1.0, {0: 1.0}, trace)
        first, second = split_10643(amount, rooms(5.0, 5.0), SPLIT)
        total = first + second
        self.assertEqual(ad.primal(total), 1.0)
        self.assertAlmostEqual(ad.derivative(total).get(0, 0.0), 1.0, places=15)


class SourceSelectionTests(unittest.TestCase):
    """run_interval takes the 10643 lane amounts from exactly one declared source."""

    def test_v1_lane_groups(self):
        local = types.SimpleNamespace(last_off_sent={'10643': [0.2, 0.3, 0.0]})
        freeway = types.SimpleNamespace(lanes={'FW_E': local})
        self.assertEqual(lane_amounts_10643(freeway, {'10643': 1800.0}, {'10643': rooms(5, 5)},
                                            types.SimpleNamespace()), [0.2, 0.3])
        local.last_off_sent['10643'][2] = 1e-6
        with self.assertRaises(ArithmeticError):
            lane_amounts_10643(freeway, {'10643': 1800.0}, {'10643': rooms(5, 5)}, types.SimpleNamespace())

    def test_v2_declared_split(self):
        freeway = types.SimpleNamespace(lanes={})
        network = types.SimpleNamespace(lane_plant_10643_lane_split=SPLIT)
        self.assertEqual(lane_amounts_10643(freeway, {'10643': 3600.0}, {'10643': rooms(5, 5)}, network),
                         split_10643(1.0, rooms(5, 5), SPLIT))

    def test_neither_or_both_refused(self):
        local = types.SimpleNamespace(last_off_sent={'10643': [0.2, 0.3, 0.0]})
        with self.assertRaisesRegex(ValueError, 'exactly one source'):
            lane_amounts_10643(types.SimpleNamespace(lanes={}), {'10643': 0.0}, {'10643': rooms(1, 1)},
                               types.SimpleNamespace())
        with self.assertRaisesRegex(ValueError, 'exactly one source'):
            lane_amounts_10643(types.SimpleNamespace(lanes={'FW_E': local}), {'10643': 0.0}, {'10643': rooms(1, 1)},
                               types.SimpleNamespace(lane_plant_10643_lane_split=SPLIT))


if __name__ == '__main__':
    unittest.main()
