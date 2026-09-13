"""Fixed decision boxes/restoration/deadline checks with finite stub models."""
from copy import deepcopy
import json
import unittest

from diagnostics.test_joint_owner_game_candidate import (
    Clock, action, catalog, feasible, physical_tokens, run, toggles,
)
from evaluation.controllers import joint_owner_game as game
from evaluation.controllers import joint_owner_neighbors as neighbors


class RestorationTests(unittest.TestCase):
    def restore(self, evaluate, **overrides):
        own = catalog()
        kwargs = dict(neighbors=toggles, context_fingerprint=lambda ctx: json.dumps(ctx, sort_keys=True),
            physical_fingerprint=lambda u, ctx: physical_tokens(own, u, ctx),
            max_sweeps=3, max_evaluations=20, time_budget_sec=10.,
            improvement_tolerance=0., scope_label='synthetic fixed constraints', clock=Clock())
        kwargs.update(overrides)
        return game.restore_feasibility(own, action(own), {'fixed_np_cap': 7.},
            evaluate=evaluate, **kwargs)

    @staticmethod
    def merit(u, ctx):
        value = 2. - sum(u['offsets'].values())
        return game.RestorationEvaluation(value == 0., value, True, None if value == 0. else 'fixed shared cap')

    def test_infeasible_seed_can_reach_checked_feasibility_without_target_change(self):
        result = self.restore(self.merit)
        self.assertTrue(result['feasible'], result['error'])
        self.assertEqual(result['control']['offsets'], {'A': 1., 'B': 1.})
        self.assertEqual(result['control']['N_P_star'], 7.)
        self.assertEqual(result['control']['N_UF_star'], 9.)
        self.assertEqual(result['evaluations'], 3)
        self.assertEqual(result['per_owner_evaluations'], {'A': 1, 'B': 1})
        self.assertFalse(result['domain_infeasible'])

    def test_exhaustion_does_not_claim_domain_infeasible(self):
        result = self.restore(lambda u, ctx: game.RestorationEvaluation(False, 1., True, 'cap'))
        self.assertEqual(result['status'], 'restoration_exhausted')
        self.assertFalse(result['domain_infeasible'])
        self.assertIsNone(result['control'])
        self.assertIsNotNone(result['best_infeasible'])

    def test_budget_retains_checked_infeasible_without_emitting_control(self):
        result = self.restore(self.merit, max_evaluations=2)
        self.assertEqual(result['status'], 'evaluation_budget')
        self.assertIsNone(result['control'])
        self.assertEqual(result['best_infeasible']['offsets'], {'A': 1., 'B': 0.})
        self.assertEqual(result['final_violation'], 1.)

    def test_incomplete_witness_is_not_a_feasible_result(self):
        result = self.restore(lambda *args: game.RestorationEvaluation(True, 0., False, 'missing accepted flows'))
        self.assertEqual(result['status'], 'incomplete_witness')
        self.assertIsNone(result['control'])
        self.assertIsNone(result['best_infeasible'])

    def test_target_and_evaluator_mutations_are_rejected(self):
        def wrong_target(owner, u, ctx):
            changed = deepcopy(u); changed['N_P_star'] += 1.
            return game.Neighborhood((changed,), True, 'bad target')
        def changed_evaluation(u, ctx):
            u['offsets']['A'] = 1.
            return self.merit(u, ctx)
        for result in (self.restore(self.merit, neighbors=wrong_target), self.restore(changed_evaluation)):
            self.assertEqual(result['status'], 'callback_mutation')
            self.assertIsNone(result['control'])

    def test_late_feasible_result_is_not_accepted(self):
        expired = [False]
        def check(stage):
            if expired[0]: raise TimeoutError('fixed decision deadline')
        def evaluate(u, ctx):
            value = self.merit(u, ctx)
            if value.feasible: expired[0] = True
            return value
        result = self.restore(evaluate, deadline_check=check)
        self.assertEqual(result['status'], 'decision_deadline')
        self.assertIsNone(result['control'])
        self.assertEqual(result['best_infeasible']['offsets'], {'A': 1., 'B': 0.})

    def test_game_deadline_keeps_previously_validated_round_robin_improvement(self):
        expired = [False]
        def check(stage):
            if expired[0]: raise TimeoutError('fixed decision deadline')
        def evaluate(owner, u, ctx):
            if owner == 'B' and u['offsets']['B']: expired[0] = True
            return feasible(10. - u['offsets'][owner])
        own = catalog()
        result = run(own, action(own), evaluate, traversal='round_robin', deadline_check=check)
        self.assertTrue(result['decision_deadline_reached'])
        self.assertEqual(result['control']['offsets'], {'A': 1., 'B': 0.})
        self.assertFalse(result['certified'])
        self.assertIsNone(result['maximum_finite_candidate_gap'])


class FixedAnchorCallbackTests(unittest.TestCase):
    def setUp(self):
        from diagnostics.test_joint_neighbor_callbacks import JointNeighborCallbackTests
        self.fixture = JointNeighborCallbackTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.limits = {'green_sec': 6., 'offset_sec': 15., 'vsl_kmh': 40., 'meter_veh_h': 300.}

    def make(self, **kwargs):
        return self.f.make(decision_anchor=self.f.initial, move_limits=self.limits, **kwargs)

    def test_repeated_green_queries_never_walk_box(self):
        cb = self.make()
        owner = 'SC1'
        first = cb['neighbors'](owner, self.f.initial, self.f.context)
        changed = [u for u in first.candidates if u.green_times != self.f.initial.green_times]
        self.assertTrue(changed)
        second = cb['neighbors'](owner, changed[0], self.f.context)
        self.assertTrue(second.candidates)
        for u in (*first.candidates, *second.candidates):
            self.assertFalse(cb['move_box'].violations(u))
        bad = deepcopy(self.f.initial)
        key = next(k for k in bad.green_times if k.startswith(owner + '_') and bad.green_times[k] > 0)
        bad.green_times[key] += 6.001
        with self.assertRaisesRegex(ValueError, 'fixed actual-action movement box'):
            cb['validate_move_box'](bad)

    def test_vsl_reference_stays_actual_anchor_after_incumbent_change(self):
        cb = self.make()
        first = cb['neighbors']('FW_E', self.f.initial, self.f.context)
        changed = [u for u in first.candidates if u.vsl != self.f.initial.vsl]
        self.assertTrue(changed)
        second = cb['neighbors']('FW_E', changed[0], self.f.context)
        for u in second.candidates:
            self.assertFalse(cb['move_box'].violations(u))
            self.assertGreaterEqual(u.vsl['FW_E__seg0'], 80.)

    def test_circular_offset_and_written_values_are_checked(self):
        cb = self.make()
        u = deepcopy(self.f.initial)
        cycle = self.f.cfg.network.signal_cycle_length('SC1')
        u.offsets['SC1'] = cycle - 10.
        self.assertFalse(cb['move_box'].violations(u))
        u.offsets['SC1'] = cycle - 16.
        self.assertTrue(cb['move_box'].violations(u))
        u = deepcopy(self.f.initial)
        ramp = next(iter(u.ramp_metering))
        u.ramp_metering[ramp] -= 300.001
        self.assertTrue(cb['move_box'].violations(u))

    def test_final_command_checks_remain_available_after_search_deadline(self):
        expired = [False]
        def check(stage):
            if expired[0]: raise TimeoutError('search deadline')
        cb = self.make(deadline_check=check)
        before = cb['physical_fingerprint'](self.f.initial, self.f.context)
        expired[0] = True
        self.assertEqual(before, cb['physical_fingerprint'](self.f.initial, self.f.context))
        cb['command_evidence'](self.f.initial)
        with self.assertRaises(TimeoutError):
            cb['neighbors']('SC1', self.f.initial, self.f.context)

    def test_independent_price_probe_has_both_meter_coordinates_after_quantization(self):
        from evaluation.controllers import area_meter_finalization as meters
        volumes = self.f.cfg.network.control_area_meter_context['raw']['local_observation']['far_measurement']['link_volume_veh_h']
        volumes.update({key: 1500. for key in volumes})
        self.f.initial.ramp_metering = {r: 1500. for r in self.f.initial.ramp_metering}
        self.f.initial = meters.prepare_canonical_candidate(self.f.initial, self.f.cfg,
            owned_ramps=tuple(self.f.cfg.network.ramps), total_budget=None,
            directional_budgets={}, budget_tolerance_veh_h=1e-9)
        self.f.previous = self.f.historical_reference(self.f.initial, self.f.cfg)['previous']
        cb = self.make(price_probe=True)
        result = cb['neighbors']('FW_E', self.f.initial, self.f.context)
        ramps = tuple(r for r, owner in self.f.cfg.network.ramp_to_freeway.items() if owner == 'FW_E')
        moved = [{r for r in ramps if u.ramp_metering[r] != self.f.initial.ramp_metering[r]}
                 for u in result.candidates]
        for ramp in ramps:
            self.assertIn({ramp}, moved)
        for u in result.candidates:
            self.assertFalse(cb['move_box'].violations(u))
            self.assertEqual(u.N_UF_star, sum(u.ramp_metering.values()))
        with self.assertRaisesRegex(ValueError, 'Common price probes'):
            self.make(price_probe=True, total_budget=7200.)


if __name__ == '__main__':
    unittest.main()
