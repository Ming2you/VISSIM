"""WP-0: time rules (plan 1.2, B3 assignment, B5 file-order rule)."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_fixtures as fx  # noqa: E402
from contract_fixtures import c  # noqa: E402


def rows_at(*times):
    """Entry rows of one point in file order; seq = position."""
    return [c.MerRow(i, 960001, t, None, 100 + i, 100, 50.0, 4.5, i + 1) for i, t in enumerate(times)]


class Windows(unittest.TestCase):
    def test_stops_and_windows(self):
        self.assertTrue(c.is_decision_stop(1) and c.is_decision_stop(150) and c.is_decision_stop(9000))
        self.assertFalse(c.is_decision_stop(0) or c.is_decision_stop(149) or c.is_decision_stop(150.0))
        self.assertEqual(c.window_bounds(6), (750, 900))
        self.assertEqual(c.window_index(900), 6)
        self.assertEqual(c.bundle_interval(1), (0, 1, None))
        self.assertEqual(c.bundle_interval(900), (750, 900, 6))
        for bad in (0, 1, 899, 900.0):
            with self.assertRaises(c.ObsContractError):
                c.window_index(bad)

    def test_window_membership_is_left_open(self):
        self.assertEqual(c.window_of_time(150), 1)
        self.assertEqual(c.window_of_time(150.01), 2)
        self.assertEqual(c.window_of_time(0.01), 1)
        with self.assertRaises(c.ObsContractError):
            c.window_of_time(0)


class GreenIntervals(unittest.TestCase):
    def test_half_open_on_the_left(self):
        green = [(750, 780), (820, 850)]
        self.assertFalse(c.in_green(750, green))
        self.assertTrue(c.in_green(750.05, green))
        self.assertTrue(c.in_green(780, green))
        self.assertFalse(c.in_green(780.05, green))

    def test_tail_uses_the_last_second_state(self):
        self.assertTrue(c.tail_in_green(900, [(890, 900)]))
        self.assertFalse(c.tail_in_green(900, [(850, 899)]))
        self.assertTrue(c.tail_in_green(900, [(899, 900)]))


class FileOrderRule(unittest.TestCase):
    def test_after_before_ambiguous(self):
        self.assertEqual(c.boundary_side(rows_at(780.01, 780.0), 1, 780), 'after')
        self.assertEqual(c.boundary_side(rows_at(780.0, 779.99), 0, 780), 'before')
        self.assertEqual(c.boundary_side(rows_at(779.98, 780.0, 780.02), 1, 780), 'ambiguous')

    def test_contradiction_breaks_the_premise(self):
        with self.assertRaises(c.ObsContractError):
            c.boundary_side(rows_at(780.01, 780.0, 779.99), 1, 780)

    def test_scan_stops_two_steps_away(self):
        # 779.7 < 780 - 0.2 ends the backward scan before the (disordered) 780.5.
        self.assertEqual(c.boundary_side(rows_at(780.5, 779.7, 780.0), 2, 780), 'ambiguous')

    def test_classify_passage(self):
        green = [(750, 780)]
        self.assertEqual(c.classify_passage(rows_at(780.0, 779.99), 0, green), 'green')
        self.assertEqual(c.classify_passage(rows_at(780.01, 780.0), 1, green), 'not_green')
        self.assertEqual(c.classify_passage(rows_at(750.01, 750.0), 1, green), 'green')
        self.assertEqual(c.classify_passage(rows_at(750.0, 749.99), 0, green), 'not_green')
        self.assertEqual(c.classify_passage(rows_at(765.43), 0, green), 'green')
        self.assertEqual(c.classify_passage(rows_at(779.98, 780.0, 780.02), 1, green), 'ambiguous')
        # An integer second that is not a green boundary needs no file-order rule.
        self.assertEqual(c.classify_passage(rows_at(779.98, 770.0, 780.02), 1, green), 'green')


class LagRule(unittest.TestCase):
    def test_lag(self):
        self.assertTrue(c.lag_ok(None, 900, 0))
        self.assertTrue(c.lag_ok(899.01, 900, 3))
        self.assertFalse(c.lag_ok(899.0, 900, 3))
        self.assertFalse(c.lag_ok(None, 900, 1))


def assignment_case():
    obs = fx.raw_obs(900)
    rows = fx.detector_rows()
    a, b = str(rows[0].dcm_no), str(rows[1].dcm_no)
    for key in obs['detectors']:
        obs['detectors'][key], obs['detectors_cum'][key], obs['mer']['records_cum_by_dcp'][key] = 0, 4, 4
    obs['detectors'][a], obs['detectors_cum'][a], obs['mer']['records_cum_by_dcp'][a] = 3, 10, 9
    obs['mer']['max_t_any'] = 899.5
    chunk = [c.MerRow(0, int(a), 749.8, None, 1, 100, 50.0, 4.5, 6),     # previous window's tail
             c.MerRow(1, int(a), None, 750.1, 1, 100, 50.0, 4.5, None),
             c.MerRow(2, int(a), 750.0, None, 2, 100, 50.0, 4.5, 7),       # previous tail at the boundary
             c.MerRow(3, int(a), 800.2, None, 3, 100, 50.0, 4.5, 8),
             c.MerRow(4, int(b), None, 812.0, 9, 100, 50.0, 4.5, None),
             c.MerRow(5, int(a), 899.3, None, 4, 100, 50.0, 4.5, 9)]
    return obs, chunk, int(a)


class Assignment(unittest.TestCase):
    def test_ordinals_tails_and_lag(self):
        obs, chunk, a = assignment_case()
        result = c.assign_window(obs, chunk)
        self.assertEqual([r.ordinal for r in result.entries[a]], [8, 9])
        self.assertEqual(result.tails[a], 1)
        self.assertEqual(result.sum_tail, 1)
        self.assertTrue(result.lag_ok)
        self.assertEqual((result.start_s, result.end_s, result.k), (750, 900, 6))

    def test_lag_failure_is_obs_lag_error(self):
        obs, chunk, _ = assignment_case()
        obs['mer']['max_t_any'] = 898.9
        with self.assertRaises(c.ObsLagError):
            c.assign_window(obs, chunk)

    def test_count_contradictions(self):
        obs, chunk, a = assignment_case()
        broken = [r._replace(ordinal=10) if r.seq == 5 else r for r in chunk]
        with self.assertRaises(c.ObsContractError):
            c.assign_window(obs, broken)
        obs2 = copy.deepcopy(obs)
        obs2['mer']['records_cum_by_dcp'][str(a)] = 11
        with self.assertRaises(c.ObsContractError):
            c.assign_window(obs2, chunk)
        early = [r._replace(t_entry=700.0) if r.seq == 3 else r for r in chunk]
        with self.assertRaises(c.ObsContractError):
            c.assign_window(obs, early)
        # Rows of this interval that are not in the chunk (records_prev > C_prev).
        with self.assertRaises(c.ObsContractError):
            c.assign_window(obs, [r for r in chunk if r.seq not in (0, 2, 3)])

    def test_open_interval_at_t1(self):
        obs = fx.raw_obs(1)
        key = next(iter(obs['detectors']))
        obs['mer']['records_cum_by_dcp'][key] = 1
        obs['mer']['max_t_any'] = 0.73
        result = c.assign_window(obs, [c.MerRow(0, int(key), 0.73, None, 5, 100, 50.0, 4.5, 1)])
        self.assertEqual((result.start_s, result.end_s, result.k), (0, 1, None))
        self.assertEqual(len(result.entries[int(key)]), 1)
        self.assertEqual(result.sum_tail, len(obs['detectors']) - 1)


if __name__ == '__main__':
    unittest.main()
