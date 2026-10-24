"""One wall deadline including preparation; nested CPU accounting is explicit."""
import unittest
from unittest.mock import patch
from evaluation.controllers.area_follower_objective import DecisionBudget, DecisionDeadline


class DecisionBudgetTests(unittest.TestCase):
    def test_explicit_unlimited_keeps_clock_measurement_without_deadlines(self):
        import json
        budget=DecisionBudget(120.,started=0.,cpu_started=0.,unlimited_time=True)
        with patch('time.perf_counter',return_value=100000.),patch('time.process_time',return_value=123.):
            budget.check('search');budget.check('output',final=True)
            self.assertEqual(budget.remaining(),float('inf'))
            row=budget.report()
        self.assertEqual(row['wall_sec'],100000.)
        self.assertIsNone(row['budget_sec']);self.assertIsNone(row['overrun_sec'])
        self.assertIsNone(row['expired_stage']);self.assertEqual(row['cpu_sec'],123.)
        json.dumps(row,allow_nan=False)

    def test_preparation_consumes_search_budget_and_reserves_output(self):
        with patch('time.perf_counter', return_value=100.), patch('time.process_time', return_value=40.):
            budget = DecisionBudget(120., reserve_sec=10., started=0., cpu_started=5.)
            self.assertEqual(budget.remaining(), 10.)
            self.assertEqual(budget.remaining(final=True), 20.)
            budget.check('prices')
        with patch('time.perf_counter', return_value=111.):
            with self.assertRaises(DecisionDeadline): budget.check('next_endpoint')
            self.assertEqual(budget.remaining(final=True), 9.)

    def test_overrun_is_measured_and_never_reported_as_hard_realtime(self):
        budget = DecisionBudget(120., reserve_sec=10., started=0., cpu_started=0.)
        with patch('time.perf_counter', return_value=126.), patch('time.process_time', return_value=119.):
            row = budget.report()
        self.assertEqual(row['overrun_sec'], 6.)
        self.assertEqual(row['cpu_sec'], 119.)
        self.assertIn('in-flight', row['scope_rule'])

    def test_search_expiry_leaves_final_reserve_until_exact_whole_deadline(self):
        budget = DecisionBudget(120., reserve_sec=10., started=0., cpu_started=0.)
        with patch('time.perf_counter', return_value=110.):
            with self.assertRaises(DecisionDeadline):
                budget.check('search')
            budget.check('output', final=True)
        with patch('time.perf_counter', return_value=119.999):
            budget.check('last_output', final=True)
        with patch('time.perf_counter', return_value=120.):
            with self.assertRaisesRegex(DecisionDeadline, 'finalization deadline at output_done'):
                budget.check('output_done', final=True)
        self.assertEqual(budget.expired_stage, 'output_done')

    def test_invalid_reserve_rejected(self):
        for reserve in (-1., 120., 150.):
            with self.assertRaises(ValueError): DecisionBudget(120., reserve_sec=reserve)


if __name__ == '__main__': unittest.main()
