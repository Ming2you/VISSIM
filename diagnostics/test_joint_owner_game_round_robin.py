"""Opt-in traversal only: synthetic callbacks, no traffic/model/COM imports."""
from copy import deepcopy
import unittest

from diagnostics.test_joint_owner_game_candidate import (Clock, action, catalog, feasible, run, toggles)
from evaluation.controllers.joint_owner_game import Evaluation, Neighborhood, Address, Ownership, traversal_owner_order


def domain(counts):
    def neighbors(owner, base, context):
        candidates=[deepcopy(base)]
        for value in range(1,counts.get(owner,1)+1):
            candidate=deepcopy(base);candidate['offsets'][owner]=float(value)
            candidates.extend((candidate,deepcopy(candidate)))
        return Neighborhood(tuple(candidates),True,'unchanged full finite synthetic domain')
    return neighbors


class RoundRobinTests(unittest.TestCase):
    def test_unlimited_clock_still_finishes_all_owners_and_checks_final_gap(self):
        own=catalog();initial=action(own);clock=Clock()
        def score(owner,u,ctx):
            clock.value+=1000.
            a,b=u['offsets']['A'],u['offsets']['B']
            return feasible((a-b)**2 if owner=='A' else (1-b)**2)
        result=run(own,initial,score,traversal='round_robin',clock=clock,time_budget_sec=None)
        self.assertTrue(result['certified'],result['error'])
        self.assertTrue(result['final_check_complete'])
        self.assertEqual(result['maximum_finite_candidate_gap'],0.)
        self.assertIsNone(result['limits']['time_budget_sec'])
        limited=run(own,initial,score,traversal='round_robin',clock=clock,time_budget_sec=None,max_evaluations=1)
        self.assertEqual(limited['error']['kind'],'evaluation_budget')
        self.assertFalse(limited['certified'])
    def test_balanced_order_reaches_both_lever_families_without_changing_catalog(self):
        own=Ownership(('A','C','B','D'),(
            Address('offsets','A','A','strategy'), Address('green_times','C','C','strategy'),
            Address('vsl','B','B','strategy'), Address('ramp_metering','D','D','strategy')),())
        self.assertEqual(traversal_owner_order(own,'round_robin'),own.owners)
        self.assertEqual(traversal_owner_order(own,'round_robin_balanced'),('B','A','D','C'))
        seen=[]
        def neighbors(owner,base,context):
            seen.append(owner)
            return Neighborhood((deepcopy(base),),True,'unchanged singleton')
        result=run(own,action(own),lambda *args:feasible(0),neighbors=neighbors,
                   traversal='round_robin_balanced',max_sweeps=1)
        self.assertEqual(tuple(seen[:4]),('B','A','D','C'))
        self.assertEqual(result['traversal'],'round_robin_balanced')
        self.assertEqual(result['control'],action(own))
        self.assertEqual(own.owners,('A','C','B','D'))

    def test_default_and_explicit_sequential_match_every_callback_and_result(self):
        own=catalog();initial=action(own);traces=[];results=[]
        for kwargs in ({},{'traversal':'sequential'}):
            trace=[]
            def score(owner,u,ctx):
                trace.append((owner,deepcopy(u)))
                return feasible((u['offsets']['A']-u['offsets']['B'])**2 if owner=='A' else (1-u['offsets']['B'])**2)
            results.append(run(own,initial,score,**kwargs));traces.append(trace)
        self.assertEqual(results[0],results[1]);self.assertEqual(traces[0],traces[1])
        self.assertNotIn('traversal',results[0])

    def test_all19_visit_before_long_first_owner_gets_second_unique_candidate(self):
        names=tuple('O'+str(i) for i in range(19));own=catalog(names);initial=action(own);nonbase=[]
        def score(owner,u,ctx):
            value=u['offsets'][owner]
            if value:nonbase.append((owner,value))
            return feasible(100-value)
        result=run(own,initial,score,neighbors=domain({names[0]:100}),traversal='round_robin',max_evaluations=38)
        self.assertEqual(nonbase,[(owner,1.) for owner in names])
        self.assertEqual(result['evaluations'],38);self.assertEqual(result['neighbor_calls'],19)
        self.assertEqual(result['control']['offsets'][names[0]],1.)
        self.assertEqual(len(result['accepted_updates']),1)
        self.assertTrue(result['accepted_updates'][0]['partial_sweep'])
        self.assertFalse(result['certified']);self.assertFalse(result['final_check_complete'])
        self.assertTrue(all(record['gap'] is None for record in result['per_owner'].values()))
        self.assertTrue(all(record['gap'] is None for record in result['search_sweeps'][0]['owners'].values()))
        self.assertEqual(initial,action(own))

    def test_fixed_sweep_and_largest_local_improvement_only_not_combined(self):
        own=catalog(('A','B','C'));initial=action(own);seen=[]
        def score(owner,u,ctx):
            seen.append((owner,dict(u['offsets'])))
            return feasible(20-(1+own.owners.index(owner))*u['offsets'][owner])
        result=run(own,initial,score,neighbors=domain({'A':2,'B':2,'C':2}),traversal='round_robin',max_sweeps=1)
        probes=[(owner,values[owner]) for owner,values in seen[:9] if values[owner]]
        self.assertEqual(probes,[('A',1.),('B',1.),('C',1.),('A',2.),('B',2.),('C',2.)])
        self.assertTrue(all(all(value==0 for other,value in values.items() if other!=owner) for owner,values in seen[:9]))
        self.assertEqual(result['control']['offsets'],{'A':0.,'B':0.,'C':2.})
        self.assertEqual([r['owner'] for r in result['accepted_updates']],['C'])
        self.assertEqual(result['accepted_updates'][0]['gap'],6.)
        self.assertTrue(result['final_check_complete']);self.assertFalse(result['certified'])
        self.assertEqual(result['per_owner']['B']['gap'],4.)
        self.assertEqual(result['per_owner']['C']['gap'],0.)

    def test_late_result_ignored_but_earlier_checked_best_committed(self):
        own=catalog();initial=action(own);clock=Clock()
        def score(owner,u,ctx):
            clock.value+=2 if owner=='B' and u['offsets']['B'] else 1
            return feasible(20-(10 if owner=='B' else 1)*u['offsets'][owner])
        result=run(own,initial,score,traversal='round_robin',clock=clock,time_budget_sec=4.)
        self.assertEqual(result['error']['kind'],'time_budget')
        self.assertEqual(result['control']['offsets'],{'A':1.,'B':0.})
        self.assertTrue(result['accepted_updates'][0]['partial_sweep'])
        self.assertIsNone(result['maximum_finite_candidate_gap'])

    def test_context_change_at_same_deadline_cancels_pending_best(self):
        own=catalog();initial=action(own);clock=Clock();context={'price':1}
        def score(owner,u,ctx):
            clock.value+=1
            if owner=='B' and u['offsets']['B']:
                ctx['price']=2;clock.value=10
            return feasible(10-u['offsets'][owner])
        result=run(own,initial,score,traversal='round_robin',clock=clock,time_budget_sec=5,context=context)
        self.assertEqual(result['error']['kind'],'context_changed')
        self.assertEqual(result['control'],initial);self.assertEqual(result['accepted_updates'],[])

    def test_callback_failure_does_not_commit_pending_best(self):
        own=catalog();initial=action(own)
        def score(owner,u,ctx):
            if owner=='B':raise ValueError('failed witness')
            return feasible(10-u['offsets'][owner])
        result=run(own,initial,score,traversal='round_robin')
        self.assertEqual(result['error']['kind'],'callback_failure')
        self.assertEqual(result['control'],initial);self.assertEqual(result['accepted_updates'],[])

    def test_complete_final_audit_of_new_incumbent_and_revisit(self):
        own=catalog();initial=action(own)
        def score(owner,u,ctx):
            a,b=u['offsets']['A'],u['offsets']['B']
            return feasible((a-b)**2 if owner=='A' else (1-b)**2)
        result=run(own,initial,score,traversal='round_robin')
        self.assertTrue(result['certified'],result['error'])
        self.assertEqual([(r['sweep'],r['owner']) for r in result['accepted_updates']],[(1,'B'),(2,'A')])
        self.assertEqual(result['control']['offsets'],{'A':1.,'B':1.})
        self.assertEqual(result['maximum_finite_candidate_gap'],0.)

    def test_infeasible_lower_cost_not_selected(self):
        own=catalog();initial=action(own)
        def score(owner,u,ctx):
            if owner=='A' and u['offsets']['A']:return Evaluation(False,-100.,0.,True,'shared cap')
            return feasible(2-u['offsets'][owner])
        result=run(own,initial,score,traversal='round_robin',max_sweeps=1)
        self.assertEqual(result['control']['offsets'],{'A':0.,'B':1.})
        self.assertEqual(result['search_sweeps'][0]['owners']['A']['infeasible_neighbors'],1)

    def test_foreign_command_or_nonlever_mutation_rejected(self):
        own=catalog();initial=action(own)
        for mutate in (lambda u:u['offsets'].update(B=2.),lambda u:u.update(N_P_star=9.)):
            def bad(owner,u,ctx):
                v=deepcopy(u);mutate(v)
                return Neighborhood((v,),True,'malformed foreign/frozen candidate')
            result=run(own,initial,lambda *args:feasible(0),neighbors=bad,traversal='round_robin')
            self.assertFalse(result['certified']);self.assertEqual(result['control'],initial)
            self.assertEqual(result['accepted_updates'],[])

    def test_unfinished_no_improvement_is_not_gap_zero(self):
        own=catalog();initial=action(own)
        result=run(own,initial,lambda *args:feasible(0),traversal='round_robin',max_evaluations=2)
        self.assertEqual(result['control'],initial);self.assertFalse(result['certified'])
        self.assertIsNone(result['maximum_finite_candidate_gap'])
        self.assertEqual(result['search_sweeps'][0]['owners']['B']['status'],'evaluating')
        with self.assertRaisesRegex(ValueError,'traversal'):run(own,initial,lambda *args:feasible(0),traversal='random')


if __name__=='__main__':unittest.main()
