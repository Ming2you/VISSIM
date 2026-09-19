"""Runtime work-budget propagation with synthetic fixed candidate responses."""
import copy
from contextlib import nullcontext
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from diagnostics.test_joint_leader_result import fixture
from evaluation.controllers import area_follower_objective as subject
from evaluation.controllers import area_leader_objective as pricing
from evaluation.controllers import physical_ramp_branches as ramps


class UnlimitedCandidateTests(unittest.TestCase):
    def run_candidate(self, unlimited):
        response = fixture()
        action = response['game']['control']
        owners = tuple(response['game']['owners'])
        fast = {'candidate_time_budget_sec': 120., 'restoration_time_budget_sec': 45.,
                'restoration_max_evaluations': 8}
        cfg = NS(network=NS(signals=owners[:-2], freeway_links=owners[-2:],
                            control_area_fast_np_initialization=fast),
                 mpc=NS(horizon_steps=3, max_nash_iter=3), simulation=NS(T_c_sec=150.))
        controller = NS(nash_solver=NS(cfg=cfg, _lambda_P=0., _lambda_UF=0.))
        common = {'reference': action, 'measured': {'field': {}, 'probe_selection': {}},
                  'expected_context': {}, 'response_query': object(),
                  'fast_np': {'seeds': (), 'evidence': {}}}
        proposal = {'control': action, 'target_np_veh': action.N_P_star,
                    'target_nuf_veh_h': action.N_UF_star, 'directional_budgets': {}}
        options = dict(max_evaluations=512, time_budget_sec=240., improvement_tolerance=1e-7,
                       shared_tolerance=1e-7, np_tolerance_veh=1e-7, nuf_tolerance_veh_h=40.,
                       traversal='round_robin_balanced')
        captured = {}
        def solve(*args, **kwargs):
            captured.update(kwargs)
            return {**copy.deepcopy(response), 'initializer_seed_checks': []}
        budget = subject.DecisionBudget(120., unlimited_time=unlimited)
        with patch.object(subject, 'shared_query_runtime_scope', return_value=nullcontext()), \
             patch.object(subject, '_joint_runtime_callbacks', return_value=(
                 {'ownership': NS(owners=owners)}, {}, lambda value: 'same-context')), \
             patch.object(subject, 'solve_fixed_shared_game', side_effect=solve), \
             patch.object(subject, '_runtime_joint_candidate_validation', return_value=(
                 'feasible_final_response', {}, None)), \
             patch.object(pricing, 'install_joint_price_field', return_value={}), \
             patch.object(ramps, 'enabled', return_value=True), \
             patch.object(ramps, 'prepare_control', side_effect=lambda value, cfg: value):
            result = subject.solve_runtime_joint_candidate(controller, NS(time_sec=900.), [], action,
                proposal, {}, runtime_sources={'source': 'pinned'}, options=options, common=common, budget=budget)
        return captured, result, fast

    def test_unlimited_disables_both_hidden_wall_caps_and_keeps_finite_work_bounds(self):
        work, result, original = self.run_candidate(True)
        self.assertIsNone(work['time_budget_sec'])
        self.assertIsNone(work['restoration_policy']['restoration_time_budget_sec'])
        self.assertEqual(work['max_evaluations'], 512)
        self.assertEqual(work['max_sweeps'], 3)
        self.assertEqual(work['restoration_policy']['restoration_max_evaluations'], 8)
        self.assertTrue(work['restore_initializer'])
        self.assertNotIn('decision_deadline_monotonic', work)
        proof = result['response']['fast_np']
        self.assertTrue(proof['wall_limits_disabled'])
        self.assertIsNone(proof['candidate_time_budget_sec'])
        self.assertIsNone(proof['candidate_time_overrun_sec'])
        self.assertEqual(proof['configured_inactive_candidate_time_budget_sec'], 120.)
        self.assertEqual(original['restoration_time_budget_sec'], 45.)

    def test_bounded_retains_candidate_and_restoration_caps(self):
        work, result, _ = self.run_candidate(False)
        self.assertGreater(work['time_budget_sec'], 0.)
        self.assertLessEqual(work['time_budget_sec'], 120.)
        self.assertEqual(work['restoration_policy']['restoration_time_budget_sec'], 45.)
        self.assertIn('decision_deadline_monotonic', work)
        self.assertNotIn('wall_limits_disabled', result['response']['fast_np'])


if __name__ == '__main__':
    unittest.main()
