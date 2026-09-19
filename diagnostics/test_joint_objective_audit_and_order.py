"""Objective retention and optional NP ordering using existing response fixtures."""
import copy
import json
import pickle
import unittest

from diagnostics.test_joint_leader_result import fixture, digest
from diagnostics.test_runtime_joint_leader import RuntimeJointLeaderTests
from evaluation.controllers import area_follower_objective as subject


class ObjectiveAuditTests(unittest.TestCase):
    def summary(self, item=None):
        return subject.objective_response_summary(item or fixture()['final_score'],
                                                  start_sec=900., end_sec=1350.)

    def test_summary_copies_only_existing_values_without_mutating_response(self):
        score = fixture()['final_score']
        before = pickle.dumps(score, protocol=5)
        result = self.summary(score)
        for key in ('objective_veh_h', 'action_token', 'response_token', 'frozen_context_token'):
            self.assertEqual(result[key], score[key])
        for key in ('ttt_veh_h', 'ttd_veh', 'beta_seconds'):
            self.assertEqual(result[key], score['control_area'][key])
        self.assertEqual(result['additional_endpoint_calls'], 0)
        self.assertEqual(pickle.dumps(score, protocol=5), before)
        json.dumps(result, allow_nan=False)

    def test_comparison_keeps_ttt_ttd_and_weighted_objective_separate(self):
        held = self.summary()
        selected = {**held, 'ttt_veh_h': 7., 'ttd_veh': 200., 'objective_veh_h': -9.}
        result = subject.compare_objective_responses(held, selected)
        self.assertTrue(result['comparable'])
        self.assertEqual(result['ttt_reduction_veh_h'], 1.)
        self.assertEqual(result['ttd_increase_veh'], -40.)
        self.assertEqual(result['objective_reduction_veh_h'], -3.)
        self.assertEqual(result['additional_endpoint_calls'], 0)

    def test_mismatched_window_context_beta_and_missing_evidence_are_not_compared(self):
        held = self.summary()
        for key, value in (('start_sec', 1050.), ('end_sec', 1500.),
                           ('beta_seconds', 0.), ('frozen_context_token', 'other')):
            with self.subTest(key=key):
                result = subject.compare_objective_responses(held, {**held, key: value})
                self.assertFalse(result['comparable'])
                self.assertIn(key, result['mismatched_or_missing_fields'])
                self.assertIsNone(result['objective_reduction_veh_h'])
        self.assertFalse(subject.compare_objective_responses(None, held)['comparable'])

    def test_audit_is_opt_in_and_does_not_change_selection_or_endpoint_requests(self):
        h = RuntimeJointLeaderTests(); h.setUp()
        baseline = h.run_selection()
        original_calls = list(h.calls)
        h.setUp()
        h.options['retain_objective_comparison'] = True
        held = self.summary()
        def common(*args, **kwargs):
            kwargs['budget'].hold_validation = {'objective_summary': copy.deepcopy(held)}
            return h.prepare_common(*args, **kwargs)
        observed = h.run_selection(common=common)
        self.assertEqual(h.calls, original_calls)
        self.assertEqual(len(h.common_calls), 1)
        self.assertEqual(digest(baseline['selected']['response']), digest(observed['selected']['response']))
        self.assertEqual(baseline['metadata']['ranking_indices'], observed['metadata']['ranking_indices'])
        self.assertNotIn('objective_comparison', baseline['metadata'])
        comparison = observed['metadata']['objective_comparison']
        self.assertTrue(comparison['comparable'])
        self.assertEqual(comparison['selected']['action_token'], observed['selected']['response']['final_action_token'])
        self.assertEqual(comparison['selected']['objective_veh_h'], observed['selected']['validated_nash']['objective_value'])
        json.dumps(observed['metadata'], allow_nan=False)


class HoldNPOrderTests(unittest.TestCase):
    def test_existing_caps_near_hold_promoted_without_changing_domain_or_nuf(self):
        h = RuntimeJointLeaderTests(); h.setUp()
        h.domain = h.make_domain((-250., 0., 200., 300., 1075., 2400.))
        h.costs = {row['target_np_veh']: 10. for row in h.domain['candidates']}
        h.options['leader_candidate_order'] = 'hold_np_nearby'
        before = digest(h.domain)
        def common(*args, **kwargs):
            kwargs['budget'].hold_validation = {'quantity_constraints': {'np': {'actual': 255.}}}
            return h.prepare_common(*args, **kwargs)
        result = h.run_selection(common=common)
        self.assertEqual(h.calls, [(2400., 7200.), (300., 7200.), (200., 7200.)])
        self.assertEqual(digest(h.domain), before)
        self.assertEqual(set(result['metadata']['evaluation_order']), set(range(6)))
        self.assertEqual(result['metadata']['hold_np_order']['promoted_indices'], [5, 3, 2])
        self.assertFalse(result['metadata']['hold_np_order']['domain_changed'])
        self.assertFalse(result['metadata']['leader_domain_infeasible'])

    def test_nearby_caps_prefer_actual_first_seed_and_keep_remaining_diverse_order(self):
        h = RuntimeJointLeaderTests(); h.setUp()
        proposals = h.make_domain((2400., 300., 300., 200., -250.))['candidates']
        key = next(iter(proposals[1]['control'].ramp_metering))
        proposals[1]['control'].ramp_metering[key] -= 300.
        order, proof = subject.prioritize_hold_np_candidates([0, 4, 1, 3, 2], proposals,
            {'quantity_constraints': {'np': {'actual': 255.}}})
        self.assertEqual(order, [0, 2, 3, 4, 1])
        self.assertEqual(proof['promoted_np_caps_veh'], [2400., 300., 200.])

    def test_no_actual_witness_is_not_silently_replaced_by_nominal_np(self):
        h = RuntimeJointLeaderTests(); h.setUp()
        h.options['leader_candidate_order'] = 'hold_np_nearby'
        with self.assertRaisesRegex(ValueError, 'actual decision hold'):
            h.run_selection()
        self.assertEqual(h.calls, [])


if __name__ == '__main__':
    unittest.main()
