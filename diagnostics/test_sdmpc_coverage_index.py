"""Coverage indexing must preserve missing visits and copied ledger ownership."""
from pathlib import Path
import copy
import pickle
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.control_area_objective import ModelAreaLedger


class CoverageIndexTests(unittest.TestCase):
    def ledgers(self):
        return [ModelAreaLedger({}, capture_response=True, indexed_coverage=mode)
                for mode in (False, True)]

    def test_all_clocks_scopes_missing_constraints_and_order_match(self):
        old, new = self.ledgers()
        for ledger in (old, new):
            for start in (0., 10., 20.):
                ledger.plan_constraint_interval(start, 1., 5., 5, 2,
                    ['urban_allocator', 'shared_approach'], off_ramps=['A', 'B'], physical_ramps=True)
                pending = [row for row in ledger._response['constraint_coverage'] if not row['completed']]
                for i, row in enumerate(reversed(pending)):
                    if i == 7:
                        continue
                    ledger.begin_response_step(row['stage'], row['start_sec'], row['end_sec'])
                    ledger.complete_constraint_coverage(row['scope'], missing_constraints=['missing'] if i == 8 else [])
        self.assertEqual(old.response(), new.response())
        self.assertFalse(new.response()['model_constraint_coverage']['allocator_visits_complete'])
        self.assertEqual(new.response()['model_constraint_coverage']['missing_constraints'], ['missing'])

    def test_duplicate_expectations_completions_and_unplanned_visits_reject(self):
        for ledger in self.ledgers():
            ledger.begin_response_step('urban', 0., 1.)
            ledger.expect_constraint_coverage('urban_allocator')
            with self.assertRaises(ValueError):
                ledger.expect_constraint_coverage('urban_allocator')
            ledger.complete_constraint_coverage('urban_allocator')
            with self.assertRaises(ValueError):
                ledger.complete_constraint_coverage('urban_allocator')
            ledger.complete_constraint_coverage('isolated')
            self.assertFalse(ledger.response()['model_constraint_coverage']['allocator_visits_complete'])
            with self.assertRaises(ValueError):
                ledger.expect_constraint_coverage('isolated')

    def test_clone_and_pickle_index_points_to_owned_rows(self):
        ledger = self.ledgers()[1]
        ledger.plan_constraint_interval(0., 1., 1., 1, 2, ['urban_allocator'])
        for clone in (copy.deepcopy(ledger), pickle.loads(pickle.dumps(ledger))):
            row = clone._response['constraint_coverage'][0]
            clone.begin_response_step(row['stage'], row['start_sec'], row['end_sec'])
            clone.complete_constraint_coverage(row['scope'])
            self.assertTrue(clone.response()['constraint_coverage'][0]['completed'])
            self.assertFalse(ledger.response()['constraint_coverage'][0]['completed'])
            self.assertIs(next(iter(clone._coverage_index.values())), row)

    def test_index_corruption_cannot_hide_an_unchecked_row(self):
        for mutation in ('append', 'remove', 'replace', 'key'):
            ledger = self.ledgers()[1]
            ledger.plan_constraint_interval(0., 1., 1., 1, 1, ['urban_allocator'])
            rows = ledger._response['constraint_coverage']
            if mutation == 'append': rows.append(dict(rows[0]))
            elif mutation == 'remove': rows.pop()
            elif mutation == 'replace': rows[0] = dict(rows[0])
            else: rows[0]['start_sec'] += .1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                ledger.response()

    def test_disabled_has_no_index_state(self):
        self.assertFalse(hasattr(ModelAreaLedger({}, capture_response=True), '_coverage_index'))
        self.assertFalse(hasattr(ModelAreaLedger({}, indexed_coverage=True), '_coverage_index'))


if __name__ == '__main__':
    unittest.main()
