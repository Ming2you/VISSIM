"""Deferred search plus exact selected-domain audit; synthetic contract checks."""
import copy
import unittest
from unittest.mock import patch

from diagnostics import test_fixed_shared_game as fixed_fixtures
from diagnostics import test_runtime_joint_leader as leader_fixtures
from evaluation.controllers import area_follower_objective as subject
from evaluation.controllers import area_leader_objective as pricing
from evaluation.controllers import joint_owner_game as game


class SelectedAuditIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixed_fixtures.FixedSharedGameTests(); self.f.setUp()
        f = self.f
        def neighbors(owner, base, context):
            address = next(a for a in f.addresses if a.owner == owner)
            candidates = [copy.deepcopy(base)]
            for value in (2., 3., 4.):
                trial = copy.deepcopy(base)
                getattr(trial, address.field)[address.key] = value
                candidates.extend((trial, copy.deepcopy(trial)))
            return game.Neighborhood(tuple(candidates), True, 'complete four-value finite domain')
        f.callbacks['neighbors'] = neighbors

    def run_fixed(self, incumbent, **overrides):
        f = self.f
        kwargs = dict(callbacks=f.callbacks, context=f.context, context_fingerprint=fixed_fixtures.digest,
            horizon_steps=3, lambda_p=0., lambda_uf=0., target_np_veh=3., target_nuf_veh_h=5.,
            price_context={'np_mode': 'cap', 'nuf_mode': 'equality'}, max_sweeps=1,
            max_evaluations=1000, time_budget_sec=None, improvement_tolerance=1e-9,
            shared_tolerance=1e-7, scope_label='Selected-only finite audit fixture',
            np_tolerance_veh=1e-7, nuf_tolerance_veh_h=1e-7,
            traversal='sequential_balanced', search_owner_candidate_limit=2)
        kwargs.update(overrides)
        with patch.object(subject, '_evaluate_shared_owner_batch_owned', f.batch), \
             patch.object(pricing, 'fixed_joint_price_terms', f.prices), \
             patch.object(pricing, 'shared_quantity_constraints', return_value={'feasible': True}):
            return subject.solve_fixed_shared_game(f.follower, f.state, f.action,
                f.forecast, incumbent, **kwargs)

    def test_independent_full_audit_reproduces_all_gaps_without_changing_search(self):
        baseline = self.run_fixed(self.f.action)
        search = self.run_fixed(self.f.action, defer_final_audit=True)
        self.assertTrue(search['game']['final_audit_deferred'])
        self.assertFalse(search['game']['final_check_complete'])
        self.assertEqual(search['game']['accepted_updates'], baseline['game']['accepted_updates'])
        self.assertEqual(search['final_action_token'], baseline['final_action_token'])
        audited = self.run_fixed(search['game']['control'], audit_only=True, max_evaluations=1)
        # A placeholder caller limit cannot truncate the exact inventoried audit.
        self.assertTrue(audited['game']['final_check_complete'])
        self.assertEqual(audited['game']['evaluations'], audited['final_audit_domain_inventory']['evaluation_budget'])
        self.assertEqual(audited['game']['evaluations'], 19*3)
        self.assertEqual(audited['game']['per_owner'], baseline['game']['per_owner'])
        combined = subject.attach_selected_final_audit(search, audited)
        self.assertEqual(combined['final_action_token'], baseline['final_action_token'])
        self.assertEqual(combined['final_score'], baseline['final_score'])
        self.assertEqual(combined['game']['accepted_updates'], baseline['game']['accepted_updates'])
        self.assertEqual(combined['game']['evaluations'], baseline['game']['evaluations'])
        self.assertEqual(combined['queries']['requests'], baseline['queries']['requests'])
        self.assertEqual(combined['queries']['endpoint_calls'],
                         search['queries']['endpoint_calls']+audited['queries']['endpoint_calls'])
        self.assertEqual(combined['queries']['search'], search['queries'])
        self.assertEqual(combined['queries']['selected_final_audit'], audited['queries'])
        self.assertEqual(combined['game']['maximum_finite_candidate_gap'], 1.)
        self.assertFalse(combined['game']['certified'])  # Full coverage is not zero gap.

    def test_selected_audit_batches_keep_same_full_gap_and_scored_action(self):
        f = self.f
        f.follower.cfg.network.control_area_response_scheduling = {'lookahead': 4, 'final_check_reserve_sec': 0.}
        query, sizes, _ = f.full_sweep_query()
        search = self.run_fixed(f.action, defer_final_audit=True, response_query=query)
        audited = self.run_fixed(search['game']['control'], audit_only=True, response_query=query)
        result = subject.attach_selected_final_audit(search, audited)
        self.assertTrue(result['game']['final_check_complete'])
        self.assertEqual(result['game']['maximum_finite_candidate_gap'], 1.)
        self.assertLessEqual(max(sizes), 4)
        self.assertEqual(audited['queries']['bounded_response_schedule']['unconsumed_prefetched_actions'], 0)

    def test_changed_selected_context_or_score_is_rejected_before_attachment(self):
        search = self.run_fixed(self.f.action, defer_final_audit=True)
        audited = self.run_fixed(search['game']['control'], audit_only=True)
        for key in ('fixed_inputs_token', 'final_action_token', 'final_score', 'command_evidence'):
            wrong = copy.deepcopy(audited); wrong[key] = 'changed'
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'changed the scored action/context'):
                subject.attach_selected_final_audit(search, wrong)


class LeaderSelectedAuditTests(unittest.TestCase):
    def solve(self, harness, calls, bad=False):
        def solve(*args, **kwargs):
            if 'audit_response' not in kwargs:
                return harness.solve(*args, **kwargs)
            calls.append(args[4]['target_np_veh'])
            response = copy.deepcopy(kwargs['audit_response'])
            final = response['game']
            for row in final['per_owner'].values():
                row.update(complete=True, gap=.25, status='complete')
            final.update(search_skipped=True, accepted_updates=[], evaluations=57,
                sweeps_started=0, sweeps_completed=0, final_check_complete=True,
                certified=False, maximum_finite_candidate_gap=.25, error=None)
            final['limits']['max_evaluations'] = 57
            response['final_audit_domain_inventory'] = {'evaluation_budget': 57}
            response['queries'] = {'endpoint_calls': 30}
            if bad:
                response['final_score']['response_token'] = 'different response'
            return {'response': response, 'source_fingerprint': fixed_fixtures.digest(harness.sources)}
        return solve

    def test_only_rank_winner_gets_full_audit_and_ranked_score_stays_identical(self):
        h = leader_fixtures.RuntimeJointLeaderTests(); h.setUp()
        baseline = h.run_selection()
        h.setUp(); h.options['defer_candidate_final_audit'] = True
        calls = []
        result = h.run_selection(solve=self.solve(h, calls))
        self.assertEqual(calls, [340.])
        self.assertEqual(h.calls, [(500., 7200.), (340., 7200.)])
        self.assertEqual(result['metadata']['ranking_indices'], baseline['metadata']['ranking_indices'])
        self.assertEqual(result['selected']['response']['final_action_token'], baseline['selected']['response']['final_action_token'])
        self.assertEqual(result['selected']['validated_nash']['objective_value'], 10.)
        self.assertTrue(result['metadata']['selected_final_audit']['complete'])
        self.assertTrue(result['selected']['validated_nash']['diagnostics']['joint_shared_response']['final_check_complete'])
        self.assertEqual(result['selected']['validated_nash']['diagnostics']['joint_shared_response']['maximum_finite_candidate_gap'], .25)

    def test_audit_changed_response_aborts_instead_of_publishing_audit_claim(self):
        h = leader_fixtures.RuntimeJointLeaderTests(); h.setUp()
        h.options['defer_candidate_final_audit'] = True
        result = h.run_selection(solve=self.solve(h, [], bad=True))
        self.assertIsNone(result['selected'])
        self.assertEqual(result['metadata']['stop_reason'], 'selected_final_audit_failure')
        self.assertIsNotNone(result['metadata']['failure'])

    def test_skip_keeps_selected_response_and_never_invokes_neighbor_audit(self):
        h = leader_fixtures.RuntimeJointLeaderTests(); h.setUp()
        h.options.update(defer_candidate_final_audit=True, skip_selected_final_audit=True)
        def solve(*args, **kwargs):
            self.assertNotIn('audit_response', kwargs)
            self.assertTrue(kwargs['options']['defer_candidate_final_audit'])
            return h.solve(*args, **kwargs)
        result = h.run_selection(solve=solve)
        self.assertEqual(result['selected']['validated_nash']['objective_value'], 10.)
        self.assertEqual(result['metadata']['selected_final_audit'], {
            'complete': False, 'status': 'skipped_by_config', 'audit_evaluations': 0,
            'action_and_response_unchanged': True})
        self.assertEqual(h.calls, [(500., 7200.), (340., 7200.)])

    def test_skip_flag_requires_boolean_and_deferred_search(self):
        for value, deferred in ((1, True), ('true', True), (True, False)):
            h = leader_fixtures.RuntimeJointLeaderTests(); h.setUp()
            h.options.update(defer_candidate_final_audit=deferred, skip_selected_final_audit=value)
            with self.subTest(value=value, deferred=deferred), self.assertRaises(ValueError):
                h.run_selection()


if __name__ == '__main__':
    unittest.main()
