import copy
import types
import unittest
import numpy as np
from evaluation.controllers.vsl_schedule_neighbors import schedules, audit


class Coordinates:
    def __init__(self, previous=110., limit=40.):
        self.axes = [dict(kind='green', key='signal', owner='urban', block=0,
                          reference_value=20., scale=10., allowed=[])]
        for owner in ('FW_E', 'FW_W'):
            for head in (2, 5, 10, 13):
                for block in range(3):
                    self.axes.append(dict(kind='vsl', key=f'{owner}__seg{head}', owner=owner,
                        block=block, reference_value=previous, scale=10., allowed=list(range(50,111,10))))
        self.previous, self.limit = previous, limit
    def encode(self, action): return action.z.copy()
    def decode(self, z, anchor):
        result = copy.deepcopy(anchor)
        result.z = z.copy()
        return result
    def valid(self, z):
        for start in range(1, len(self.axes), 3):
            values = [self.previous, *(self.previous + 10*z[start:start+3])]
            if any(abs(b-a) > self.limit+1e-9 for a,b in zip(values, values[1:])):
                return False
        return True
    def validate(self, action):
        if not self.valid(action.z): raise ValueError('Invalid move')


class Tests(unittest.TestCase):
    def setUp(self):
        self.coord = Coordinates()
        self.anchor = types.SimpleNamespace(z=np.zeros(len(self.coord.axes)), N_P_star=100., N_UF_star=400.)
    def run_audit(self, objective, valid=lambda a,i:True):
        calls = []
        def evaluate(actions):
            calls.extend(actions)
            return [dict(objective_veh_h=objective(a)) for a in actions]
        best, receipt = audit(self.coord, (self.anchor, dict(objective_veh_h=100.), 'old'),
                              1e-8, evaluate, valid)
        return best, receipt, calls
    def test_bounded_schedules_and_non_vsl_unchanged(self):
        values, skipped = schedules(self.coord, self.anchor)
        self.assertEqual(len(values), 25)
        self.assertFalse(skipped)
        for _, action in values:
            self.assertEqual(action.z[0], 0.)
            self.assertEqual((action.N_P_star, action.N_UF_star), (100.,400.))
            self.assertTrue(set(action.z).issubset({0.,-2.}))
    def test_temporal_synergy_is_found_without_single_block_gain(self):
        def objective(a):
            values = a.z[10:13]  # east seg13, all three blocks
            return 98. if np.all(values == -2.) else 101.
        best, receipt, _ = self.run_audit(objective)
        self.assertLess(best[1]['objective_veh_h'], 100.)
        self.assertIn(':90x3', receipt['selected'])
    def test_spatial_synergy_does_not_require_beneficial_components(self):
        def objective(a):
            return 97. if np.all(a.z[7:13] == -2.) else 102.
        best, receipt, _ = self.run_audit(objective)
        self.assertEqual(best[1]['objective_veh_h'],97.)
        self.assertIn('adjacent',receipt['selected'])
    def test_lower_cost_infeasible_is_rejected(self):
        best, receipt, _ = self.run_audit(lambda a:90., lambda a,i:False)
        self.assertIs(best[0],self.anchor)
        self.assertIsNone(receipt['selected'])
    def test_no_benefit_never_forces_vsl(self):
        best, receipt, _ = self.run_audit(lambda a:101.)
        self.assertIs(best[0],self.anchor)
        self.assertIsNone(receipt['selected'])
    def test_successive_block_change_is_checked(self):
        self.coord.limit = 10.
        values, skipped = schedules(self.coord,self.anchor)
        self.assertFalse(values)
        self.assertEqual(len(skipped),25)
    def test_fixed_vsl_has_no_candidates_or_evaluation(self):
        self.coord.axes = self.coord.axes[:1]
        self.anchor.z = self.anchor.z[:1]
        _, receipt, calls = self.run_audit(lambda a:0.)
        self.assertFalse(calls)
        self.assertEqual(receipt['additional_predictions'],0)
    def test_missing_block_fails_closed(self):
        self.coord.axes = self.coord.axes[:-1]
        self.anchor.z = self.anchor.z[:-1]
        with self.assertRaisesRegex(ValueError,'three complete'):
            schedules(self.coord,self.anchor)
    def test_incomplete_evaluation_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            audit(self.coord,(self.anchor,dict(objective_veh_h=100.),None),1e-8,
                  lambda a:[],lambda a,i:True)


if __name__ == '__main__': unittest.main()
