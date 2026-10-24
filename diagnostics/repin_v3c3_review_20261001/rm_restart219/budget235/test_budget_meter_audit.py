"""A tied budget may admit a useful discrete command hidden at the first cap."""
import copy
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from evaluation.controllers import sdmpc


def incumbent(cap, cost=100.):
    action=NS(N_P_star=20.,N_UF_star=cap,green=0.)
    return action,dict(objective_veh_h=cost,nuf=80.,physical=True),None


class BudgetMeterAuditTests(unittest.TestCase):
    def setUp(self):
        self.evaluated=[]
        self.physical=True
        self.cost=90.

    def neighbors(self,coord,action):
        release=copy.deepcopy(action);release.green=2.
        return [('ramp:release',release)]

    def evaluate(self,actions):
        self.evaluated.extend(actions)
        return [dict(objective_veh_h=self.cost,nuf=150.,physical=self.physical) for _ in actions]

    def feasible(self,action,item):
        return item['physical'] and item['nuf']<=action.N_UF_star

    def run_audit(self,best,candidates):
        with patch.object(sdmpc,'meter_neighbors',self.neighbors):
            return sdmpc.audit_meter_budget_candidates(None,best,candidates,1e-7,self.evaluate,self.feasible)

    def test_tied_continuous_solution_does_not_discard_reopen_budget(self):
        low,high=incumbent(100.),incumbent(200.)
        with patch.object(sdmpc,'meter_neighbors',self.neighbors):
            old,_=sdmpc.audit_meter_neighbors(None,low,1e-7,self.evaluate,self.feasible)
        self.assertIs(old,low)
        self.evaluated.clear()
        result,proof=self.run_audit(low,[low,high])
        self.assertEqual((result[0].green,result[0].N_UF_star,result[1]['objective_veh_h']),(2.,200.,90.))
        self.assertEqual([a.N_UF_star for a in self.evaluated],[100.,200.])
        self.assertEqual([r['feasible'] for r in proof['candidates']],[False,True])
        self.assertEqual((low[0].N_UF_star,high[0].N_UF_star),(100.,200.))

    def test_larger_budget_does_not_bypass_physical_failure(self):
        self.physical=False
        low,high=incumbent(100.),incumbent(200.)
        result,proof=self.run_audit(low,[high])
        self.assertIs(result,low)
        self.assertIsNone(proof['selected'])

    def test_identical_incumbent_is_not_predicted_twice(self):
        low=incumbent(100.)
        _,proof=self.run_audit(low,[low,copy.deepcopy(low)])
        self.assertEqual(proof['distinct_budget_incumbents'],1)
        self.assertEqual(proof['additional_predictions'],1)

    def test_local_improvement_must_beat_global_incumbent(self):
        self.cost=105.
        low=incumbent(100.)
        result,_=self.run_audit(low,[incumbent(200.,110.)])
        self.assertIs(result,low)

    def test_unproven_budget_incumbent_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'feasible incumbent'):
            self.run_audit(incumbent(100.),[incumbent(50.)])

    def test_single_budget_action_matches_old_audit(self):
        base=incumbent(200.)
        with patch.object(sdmpc,'meter_neighbors',self.neighbors):
            old,old_proof=sdmpc.audit_meter_neighbors(None,base,1e-7,self.evaluate,self.feasible)
        new,proof=self.run_audit(base,[base])
        self.assertEqual(vars(old[0]),vars(new[0]))
        self.assertEqual(old[1:],new[1:])
        self.assertEqual(proof['additional_predictions'],old_proof['additional_predictions'])


if __name__=='__main__':unittest.main()
