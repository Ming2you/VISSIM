"""Scheduling/clock contracts on synthetic responses; no physical model runs."""
import copy
import unittest
from unittest.mock import patch

from diagnostics import test_fixed_shared_game as fixtures
from diagnostics import test_runtime_joint_leader as leader_fixtures
from diagnostics.test_joint_owner_game_candidate import Clock, action, catalog, feasible, run
from evaluation.controllers import joint_owner_game as game
from evaluation.controllers.area_follower_objective import _make_bounded_response_schedule
from evaluation.controllers.area_follower_objective import DecisionBudget
from evaluation.controllers.area_runtime import response_scheduling_options


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.FixedSharedGameTests()
        self.fixture.setUp()

    def enabled(self, lookahead=4, reserve=0.):
        self.fixture.follower.cfg.network.control_area_response_scheduling = {
            'lookahead': lookahead, 'final_check_reserve_sec': reserve}

    def query(self):
        return self.fixture.full_sweep_query()

    def test_option_validation_and_off(self):
        self.assertIsNone(response_scheduling_options(None))
        self.assertIsNone(response_scheduling_options(False))
        for bad in (True, {}, {'lookahead': 9, 'final_check_reserve_sec': 0.},
                    {'lookahead': True, 'final_check_reserve_sec': 0.},
                    {'lookahead': 8, 'final_check_reserve_sec': float('nan')},
                    {'lookahead': 8, 'final_check_reserve_sec': -1.}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                response_scheduling_options(bad)
        source = {'lookahead': 8, 'final_check_reserve_sec': 30.}
        self.assertEqual(response_scheduling_options(source), source)
        self.assertIsNot(response_scheduling_options(source), source)

    def test_runtime_candidate_receipt_keeps_schedule_and_reserve_counts(self):
        leader = leader_fixtures.RuntimeJointLeaderTests()
        leader.setUp()
        scheduling = {'endpoint_calls': 8, 'logical_reads': 5, 'unconsumed_prefetched_actions': 3}
        reserve = {'seconds': 30., 'same_total_time_budget': True}
        def solve(*args, **kwargs):
            result = leader.solve(*args, **kwargs)
            result['response']['queries'] = {'bounded_response_schedule': scheduling}
            result['response']['game']['final_check_reserve'] = reserve
            return result
        result = leader.run_selection(solve=solve)
        for row in result['metadata']['candidates']:
            self.assertEqual(row['response_scheduling'], scheduling)
            self.assertEqual(row['final_check_reserve'], reserve)
        self.assertIsNot(result['metadata']['candidates'][0]['response_scheduling'], scheduling)

    def test_absent_false_have_same_evaluations_actions_and_gaps(self):
        f = self.fixture
        first = f.solve(traversal='round_robin')
        f.follower.cfg.network.control_area_response_scheduling = False
        second = f.solve(traversal='round_robin')
        for key in ('control', 'evaluations', 'accepted_updates', 'per_owner', 'search_sweeps'):
            self.assertEqual(first['game'][key], second['game'][key])
        self.assertNotIn('bounded_response_schedule', second['queries'])
        self.assertNotIn('final_check_reserve', second['game'])

    def test_absolute_deadline_envelope_does_not_change_scheduler_off_results(self):
        f = self.fixture
        budget = DecisionBudget(120., reserve_sec=10., started=0., cpu_started=0.)
        with patch('time.perf_counter', return_value=60.):
            first = f.solve(traversal='round_robin', deadline_check=budget.check)
            second = f.solve(traversal='round_robin', deadline_check=budget.check,
                decision_deadline_monotonic=110.)
        for key in ('final_score', 'command_evidence', 'final_action_token'):
            self.assertEqual(first[key], second[key])
        self.assertEqual({k: v for k, v in first['game'].items() if k != 'elapsed_sec'},
                         {k: v for k, v in second['game'].items() if k != 'elapsed_sec'})

    def test_batches_preserve_all_logical_reads_actions_updates_and_final_gaps(self):
        f = self.fixture
        def neighbors(owner, base, context):
            address = next(a for a in f.addresses if a.owner == owner)
            candidates = [copy.deepcopy(base)]
            for value in (2., 3., 4.):
                trial = copy.deepcopy(base)
                getattr(trial, address.field)[address.key] = value
                candidates.extend((trial, copy.deepcopy(trial)))
            return game.Neighborhood(tuple(candidates), True, 'same explicit finite list')
        f.callbacks['neighbors'] = neighbors
        before_q, _, before_cache = self.query()
        before_events = []
        before = f.solve(response_query=before_q, traversal='round_robin',
                         time_budget_sec=None, progress=before_events.append)
        self.enabled()
        after_q, sizes, after_cache = self.query()
        after_events = []
        after = f.solve(response_query=after_q, traversal='round_robin',
                        time_budget_sec=None, progress=after_events.append)
        self.assertIn(4, sizes)
        self.assertLessEqual(max(sizes), 4)
        self.assertEqual(set(before_cache), set(after_cache))
        self.assertEqual([(r['owner'], r['requests'], r['feasible']) for r in before_events],
                         [(r['owner'], r['requests'], r['feasible']) for r in after_events])
        for key in ('control', 'accepted_updates', 'per_owner', 'search_sweeps', 'evaluations',
                    'certified', 'final_check_complete', 'maximum_finite_candidate_gap', 'error'):
            self.assertEqual(before['game'][key], after['game'][key], key)
        for key in ('owner_costs', 'objective_veh_h', 'quantity_constraints', 'physical_owner_tokens'):
            self.assertEqual(before['final_score'][key], after['final_score'][key], key)
        proof = after['queries']['bounded_response_schedule']
        self.assertEqual(proof['logical_reads'], after['game']['evaluations'])
        self.assertEqual(proof['unconsumed_prefetched_actions'], 0)
        self.assertEqual(proof['scopes'], 2)  # Search base and new final incumbent.
        self.assertFalse(proof['full_domain_precomputed'])

    def test_small_budget_never_prefetches_more_than_remaining_logical_reads(self):
        f = self.fixture
        self.enabled()
        q, sizes, cache = self.query()
        result = f.solve(response_query=q, traversal='round_robin', max_evaluations=2)
        self.assertEqual(result['game']['evaluations'], 2)
        self.assertEqual(len(cache), 2)
        self.assertLessEqual(max(sizes), 2)
        proof = result['queries']['bounded_response_schedule']
        self.assertEqual(proof['physical_checks'], 2)
        self.assertEqual(result['game']['error']['kind'], 'evaluation_budget')

    def test_large_domain_only_checks_next_batch_before_work_cap(self):
        f = self.fixture
        def neighbors(owner, base, context):
            address = next(a for a in f.addresses if a.owner == owner)
            candidates = []
            for value in range(2, 1002):
                trial = copy.deepcopy(base)
                getattr(trial, address.field)[address.key] = float(value)
                candidates.append(trial)
            return game.Neighborhood(tuple(candidates), True, 'large unchanged domain')
        f.callbacks['neighbors'] = neighbors
        self.enabled()
        q, sizes, cache = self.query()
        result = f.solve(response_query=q, traversal='round_robin', max_evaluations=4)
        proof = result['queries']['bounded_response_schedule']
        self.assertEqual(proof['physical_checks'], 3)  # One base + first two owners.
        self.assertEqual(len(cache), 3)
        self.assertLessEqual(max(sizes), 4)

    def test_invalid_future_proposal_aborts_before_submitting_batch(self):
        f = self.fixture
        original = f.callbacks['neighbors']
        def invalid(owner, base, context):
            value = original(owner, base, context)
            value.candidates[0].N_P_star += 1
            return value
        f.callbacks['neighbors'] = invalid
        self.enabled()
        q, sizes, cache = self.query()
        result = f.solve(response_query=q, traversal='round_robin')
        self.assertEqual(sizes, [])
        self.assertEqual(cache, {})
        self.assertEqual(result['game']['error']['kind'], 'callback_failure')
        self.assertEqual(result['game']['accepted_updates'], [])
        self.assertFalse(result['game']['certified'])

    def test_response_mutation_wrong_token_and_mixed_context_fail_closed(self):
        f = self.fixture
        self.enabled()
        for mode in ('mutation', 'action', 'context'):
            original, _, _ = self.query()
            def query(actions):
                value = original(actions)
                if mode == 'mutation':
                    actions[0].diagnostics['injected'] = 1.
                elif mode == 'action':
                    value['results'][0]['action_token'] = 'wrong'
                else:
                    value['results'][0]['frozen_context_token'] = 'wrong'
                return value
            query.stats = original.stats
            with self.subTest(mode=mode):
                result = f.solve(response_query=query, traversal='round_robin')
                self.assertEqual(result['game']['error']['kind'], 'callback_failure')
                self.assertEqual(result['game']['accepted_updates'], [])
                self.assertIsNone(result['game']['maximum_finite_candidate_gap'])

    def test_expired_batch_is_counted_but_not_consumed_and_new_batch_cannot_start(self):
        f = self.fixture
        original, sizes, cache = self.query()
        expired = False
        def query(actions):
            nonlocal expired
            result = original(actions)
            expired = True
            return result
        def checkpoint():
            if expired:
                raise TimeoutError('budget crossed while responses were in flight')
        schedule = _make_bounded_response_schedule(f.ownership,
            neighbors=f.callbacks['neighbors'], physical_fingerprint=f.callbacks['physical_fingerprint'],
            response_query=query, fingerprint=fixtures.digest, traversal='round_robin',
            nuf_semantics='fixed_target', lookahead=4)
        with self.assertRaises(TimeoutError):
            schedule(f.owners[0], f.action, f.action, f.context, 'search', 4, checkpoint)
        proof = schedule.report(0)
        self.assertEqual(proof['endpoint_calls'], 3)
        self.assertEqual(proof['completed_batches_past_work_limit'], 1)
        self.assertEqual(proof['logical_reads'], 0)
        self.assertEqual(proof['unconsumed_prefetched_actions'], 3)
        self.assertEqual(len(sizes), 1)
        with self.assertRaises(TimeoutError):
            schedule(f.owners[0], f.action, f.action, f.context, 'search', 4, checkpoint)
        self.assertEqual(len(sizes), 1)


class FinalReserveTests(unittest.TestCase):
    def test_shorter_candidate_limit_still_controls_search_reserve(self):
        own = catalog()
        def solve(remaining):
            clock = Clock()
            def score(owner, value, context):
                clock.value += 1.
                return feasible(20.-value['offsets'][owner])
            return run(own, action(own), score, traversal='round_robin', clock=clock,
                time_budget_sec=12., final_check_reserve_sec=8.,
                deadline_check=lambda stage: None, decision_time_remaining_sec=remaining)
        before, after = solve(None), solve(50.)
        self.assertEqual(after['final_check_reserve']['effective_time_budget_sec'], 12.)
        self.assertEqual(after['final_check_reserve']['search_time_budget_sec'], 4.)
        self.assertEqual({k: v for k, v in before.items() if k != 'final_check_reserve'},
                         {k: v for k, v in after.items() if k != 'final_check_reserve'})

    def test_common_price_time_leaves_reserve_inside_absolute_decision_deadline(self):
        for elapsed_before_game in (60., 95.):
            with self.subTest(elapsed_before_game=elapsed_before_game):
                fixture = fixtures.FixedSharedGameTests()
                fixture.setUp()
                fixture.follower.cfg.network.control_area_response_scheduling = {
                    'lookahead': 4, 'final_check_reserve_sec': 30.}
                clock, phases = Clock(), []
                clock.value = elapsed_before_game
                budget = DecisionBudget(120., reserve_sec=10., started=0., cpu_started=0.)
                query, _, _ = fixture.full_sweep_query()
                original = game.solve
                def observed_solve(*args, **kwargs):
                    evaluate, prepare = kwargs['evaluate'], kwargs['before_evaluate']
                    def timed_evaluate(*args):
                        result = evaluate(*args)
                        clock.value += 2.
                        return result
                    def observed_prepare(owner, base, trial, context, phase, remaining, check):
                        phases.append((phase, clock.value))
                        return prepare(owner, base, trial, context, phase, remaining, check)
                    kwargs.update(evaluate=timed_evaluate, before_evaluate=observed_prepare, clock=clock)
                    return original(*args, **kwargs)
                with patch('time.perf_counter', side_effect=clock), patch.object(game, 'solve', observed_solve):
                    result = fixture.solve(response_query=query, traversal='round_robin',
                        deadline_check=budget.check, decision_deadline_monotonic=110.)
                solved = result['game']
                reserve = solved['final_check_reserve']
                self.assertEqual(reserve['search_time_budget_sec'], max(0., 110.-elapsed_before_game-30.))
                self.assertEqual(next(t for phase, t in phases if phase == 'final_check'), max(80., elapsed_before_game))
                self.assertEqual(solved['error']['kind'], 'decision_deadline')
                self.assertEqual(solved['error']['phase'], 'final_check')
                self.assertIsNone(solved['maximum_finite_candidate_gap'])
                self.assertFalse(solved['certified'])
                self.assertEqual(budget.seconds, 120.)
                self.assertEqual(budget.reserve_sec, 10.)
                self.assertLessEqual(clock.value, 111.)

    def test_search_cutoff_commits_only_earlier_checked_best_then_audits_same_final(self):
        own, clock, seen = catalog(), Clock(), []
        initial = action(own)
        def score(owner, value, context):
            seen.append((owner, dict(value['offsets'])))
            clock.value += 1.
            return feasible(20.-(10. if owner == 'B' else 1.)*value['offsets'][owner])
        result = run(own, initial, score, traversal='round_robin', clock=clock,
                     time_budget_sec=12., final_check_reserve_sec=8.)
        self.assertEqual(result['control']['offsets'], {'A': 1., 'B': 0.})
        self.assertEqual([r['owner'] for r in result['accepted_updates']], ['A'])
        self.assertTrue(result['accepted_updates'][0]['partial_sweep'])
        self.assertTrue(result['final_check_complete'], result['error'])
        self.assertFalse(result['certified'])  # Positive final gap for B remains.
        self.assertEqual(result['final_check_reserve']['search_stop']['kind'], 'search_time_budget')
        self.assertEqual(seen[4][1], {'A': 1., 'B': 0.})
        self.assertLessEqual(result['elapsed_sec'], 12.)

    def test_partial_audit_preserves_unknown_at_same_overall_deadline(self):
        own, clock = catalog(), Clock()
        def score(owner, value, context):
            clock.value += 1.
            return feasible(20.-value['offsets'][owner])
        result = run(own, action(own), score, traversal='round_robin', clock=clock,
                     time_budget_sec=7., final_check_reserve_sec=3.)
        self.assertEqual(result['error']['phase'], 'final_check')
        self.assertEqual(result['error']['kind'], 'time_budget')
        self.assertTrue(result['per_owner']['A']['complete'])
        self.assertFalse(result['per_owner']['B']['complete'])
        self.assertIsNone(result['per_owner']['B']['gap'])
        self.assertIsNone(result['maximum_finite_candidate_gap'])
        self.assertFalse(result['certified'])

    def test_model_failure_and_external_deadline_do_not_resume_into_audit(self):
        own = catalog()
        for failure in (ValueError('model failure'), TimeoutError('whole decision deadline')):
            def score(owner, value, context):
                if owner == 'B':
                    raise failure
                return feasible(10.-value['offsets'][owner])
            result = run(own, action(own), score, traversal='round_robin',
                         time_budget_sec=12., final_check_reserve_sec=8.)
            self.assertIsNone(result['final_check_reserve']['search_stop'])
            self.assertTrue(all(r['status'] == 'unvisited' for r in result['per_owner'].values()))
            self.assertFalse(result['certified'])
            if isinstance(failure, ValueError):
                self.assertEqual(result['accepted_updates'], [])

    def test_context_mutation_at_reserve_boundary_cancels_pending_best(self):
        own, clock, context = catalog(), Clock(), {'price': 1}
        def score(owner, value, supplied):
            clock.value += 1.
            if owner == 'B' and value['offsets']['B']:
                supplied['price'] = 2
            return feasible(10.-value['offsets'][owner])
        result = run(own, action(own), score, traversal='round_robin', clock=clock,
                     context=context, time_budget_sec=12., final_check_reserve_sec=8.)
        self.assertEqual(result['error']['kind'], 'context_changed')
        self.assertEqual(result['control'], action(own))
        self.assertEqual(result['accepted_updates'], [])


if __name__ == '__main__':
    unittest.main()
