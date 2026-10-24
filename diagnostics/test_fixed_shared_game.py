"""Transport/selection integration with synthetic trajectories; no plant claim."""
import copy
import hashlib
from pathlib import Path
import pickle
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import area_follower_objective as subject
from evaluation.controllers import area_leader_objective as pricing
from evaluation.controllers import joint_owner_game as game


def digest(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


class ReconstructedContext:
    def __init__(self):
        self.reconstructions = 0

    def __setstate__(self, values):
        self.__dict__.update(values)
        self.reconstructions += 1


class FixedSharedGameTests(unittest.TestCase):
    def setUp(self):
        signals = tuple(f'SC{i}' for i in range(1, 18))
        self.owners = signals + ('FW_E', 'FW_W')
        self.follower = NS(cfg=NS(network=NS(control_area_enabled=True,
            signals=signals, freeway_links=('FW_E', 'FW_W'))))
        self.state, self.forecast = NS(time_sec=900.), [NS(demand=9.)]
        self.action = NS(green_times={s: 1. for s in signals}, offsets={},
                         vsl={'FW_E': 1., 'FW_W': 1.}, ramp_metering={},
                         N_P_star=3., N_UF_star=0., diagnostics={})
        self.addresses = tuple(game.Address('green_times' if s in signals else 'vsl',
                               s, s, 'strategy') for s in self.owners)
        self.ownership = game.Ownership(self.owners, self.addresses, ())
        self.context = {'source_pin': 'synthetic-v1', 'leader_target': 5.}
        self.calls = []
        self.coverage = True
        self.quantity_feasible = lambda action: True
        self.neighbor_calls = []
        def neighbors(owner, action, context):
            self.neighbor_calls.append(owner)
            trial = copy.deepcopy(action)
            address = next(a for a in self.addresses if a.owner == owner)
            getattr(trial, address.field)[address.key] = 2.
            return game.Neighborhood((trial,), True, 'synthetic explicit two values')
        self.callbacks = {'ownership': self.ownership, 'neighbors': neighbors,
            'physical_fingerprint': lambda action, context: {k: digest(v) for k, v in self.values(action).items()},
            'physical_rows': lambda action, context: self.values(action),
            'command_evidence': lambda action, context: {'synthetic_commands': self.values(action)}}

    def values(self, action):
        return {a.owner: getattr(action, a.field)[a.key] for a in self.addresses}

    def batch(self, follower, state, reference, forecast, candidates, *, horizon_steps):
        self.assertEqual(len(candidates), 1)
        action = candidates[0]
        self.calls.append(copy.deepcopy(action))
        values = self.values(action)
        return {'results': [{'objective_veh_h': sum(v*v for v in values.values()),
            'local_base_costs': {s: 10.*v for s, v in values.items()},
            'quantities': {'synthetic': True}, 'action_token': digest(action),
            'frozen_context_token': digest((follower, state, reference, forecast)),
            'model_constraint_coverage': {'complete': self.coverage},
            'conditional_model_feasibility_witness': self.coverage,
            'resource_summary': {'max_exceedance_veh': 0.}}],
            'endpoint_calls': 1, 'endpoint_sec': .01, 'score_sec': .001}

    def prices(self, follower, action, quantities, **kwargs):
        # Deliberately not J: fixed external terms favor value 2 although J rises.
        self.assertEqual(kwargs['target_nuf_veh_h'], 5.)
        return {'owners': {s: {'total': -11.*v} for s, v in self.values(action).items()}}

    def solve(self, **overrides):
        kwargs = dict(callbacks=self.callbacks, context=self.context, context_fingerprint=digest,
            horizon_steps=3, lambda_p=0., lambda_uf=0., target_np_veh=3.,
            target_nuf_veh_h=5., price_context={'np_mode': 'cap', 'nuf_mode': 'equality'}, max_sweeps=1,
            max_evaluations=1000, time_budget_sec=120., improvement_tolerance=1e-9,
            shared_tolerance=1e-7, scope_label='Synthetic fixed game transport only',
            np_tolerance_veh=1e-7, nuf_tolerance_veh_h=1e-7)
        kwargs.update(overrides)
        with patch.object(subject, '_evaluate_shared_owner_batch_owned', self.batch), \
             patch.object(pricing, 'fixed_joint_price_terms', self.prices), \
             patch.object(pricing, 'shared_quantity_constraints',
                side_effect=lambda follower, action, quantities, **kwargs: {'feasible': self.quantity_feasible(action)}):
            return subject.solve_fixed_shared_game(self.follower, self.state, self.action,
                self.forecast, self.action, **kwargs)

    def test_every_owner_selects_fixed_payoff_not_global_objective_and_final_commands_match(self):
        before = digest((self.follower, self.state, self.action, self.forecast, self.context))
        result = self.solve()
        final = result['game']
        self.assertTrue(final['certified'])
        self.assertTrue(final['final_check_complete'])
        self.assertEqual(final['maximum_finite_candidate_gap'], 0.)
        self.assertEqual(len(final['accepted_updates']), 19)
        self.assertEqual(result['final_score']['objective_veh_h'], 76.)
        self.assertEqual(set(result['final_score']['owner_costs'].values()), {-2.})
        self.assertEqual(result['command_evidence']['synthetic_commands'], dict.fromkeys(self.owners, 2.))
        self.assertEqual(len(self.calls), 20)
        self.assertEqual(result['queries']['endpoint_calls'], 20)
        self.assertEqual(result['queries']['cache_hits'], final['evaluations'] - 20)
        self.assertFalse(result['price_refresh_performed'])
        self.assertFalse(result['native_plant_feasibility_certified'])
        self.assertEqual(before, digest((self.follower, self.state, self.action, self.forecast, self.context)))

    def test_incomplete_constraint_coverage_stops_without_any_zero_gap(self):
        self.coverage = False
        result = self.solve()
        self.assertEqual(result['game']['error']['kind'], 'incomplete_witness')
        self.assertFalse(result['game']['certified'])
        self.assertIsNone(result['game']['maximum_finite_candidate_gap'])
        self.assertTrue(all(row['gap'] is None for row in result['game']['per_owner'].values()))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.neighbor_calls, [])

    def test_completed_evaluation_progress_preserves_selection_and_query_counts(self):
        baseline = self.solve()
        events = []
        observed = self.solve(progress=events.append)
        for key in ('final_action_token', 'final_score', 'command_evidence'):
            self.assertEqual(baseline[key], observed[key])
        for key in ('endpoint_calls', 'cache_hits', 'requests'):
            self.assertEqual(baseline['queries'][key], observed['queries'][key])
        self.assertEqual(len(events), observed['queries']['requests'])
        self.assertEqual([row['requests'] for row in events], list(range(1, len(events)+1)))
        self.assertEqual({row['owner'] for row in events}, set(self.owners))
        self.assertTrue(all(row['stage'] == 'joint_candidate_evaluated' for row in events))
        self.assertTrue(all(row['feasible'] and row['witness_complete'] for row in events))
        self.assertTrue(observed['game']['certified'])

    def test_progress_does_not_turn_incomplete_witness_into_success(self):
        self.coverage = False
        events = []
        result = self.solve(progress=events.append)
        self.assertEqual(result['game']['error']['kind'], 'incomplete_witness')
        self.assertFalse(result['game']['certified'])
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0]['witness_complete'])
        self.assertFalse(events[0]['feasible'])

    def test_progress_must_be_a_callable_when_supplied(self):
        with self.assertRaisesRegex(ValueError, 'progress'):
            self.solve(progress=True)
        self.assertEqual(self.calls, [])

    def test_budget_does_not_trigger_post_stop_model_query_or_fabricate_final_check(self):
        result = self.solve(max_evaluations=2)
        self.assertEqual(result['game']['error']['kind'], 'evaluation_budget')
        self.assertFalse(result['game']['certified'])
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(result['game']['accepted_updates']), 1)
        self.assertIsNone(result['game']['maximum_finite_candidate_gap'])

    def test_worker_timeout_keeps_unchanged_local_context_and_checked_incumbent(self):
        self.follower.reconstruction_probe = ReconstructedContext()
        calls = []
        def query(actions):
            calls.append(1)
            if len(calls) > 1:
                raise TimeoutError('owned response worker deadline')
            return self.batch(self.follower, self.state, self.action, self.forecast,
                              actions, horizon_steps=3)
        result = self.solve(response_query=query)
        self.assertEqual(result['game']['error']['kind'], 'decision_deadline')
        self.assertEqual(result['game']['control'], self.action)
        self.assertIsNotNone(result['final_score'])
        self.assertFalse(result['game']['final_check_complete'])
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.follower.reconstruction_probe.reconstructions, 0)

    def test_first_owner_prefetch_batches_same_actions_without_changing_game(self):
        def query_factory():
            cache, sizes = {}, []
            def query(actions):
                sizes.append(len(actions))
                result, misses = [], 0
                for action in actions:
                    key = digest(action)
                    if key not in cache:
                        cache[key] = self.batch(self.follower, self.state, self.action, self.forecast,
                                               (action,), horizon_steps=3)['results'][0]
                        misses += 1
                    result.append(copy.deepcopy(cache[key]))
                return {'results': result, 'endpoint_calls': misses, 'endpoint_sec': .01*misses, 'score_sec': 0.}
            query.stats = lambda: {'parallel_workers': 4}
            return query, sizes, cache
        before_query, _, before_cache = query_factory()
        before = self.solve(response_query=before_query, traversal='round_robin')
        self.follower.cfg.network.control_area_prefetch_first_owner_responses = True
        after_query, sizes, after_cache = query_factory()
        after = self.solve(response_query=after_query, traversal='round_robin')
        self.assertIn(4, sizes)
        self.assertLessEqual(max(sizes), 4)
        self.assertEqual(set(before_cache), set(after_cache))
        self.assertEqual(pickle.dumps(before['game']['control']), pickle.dumps(after['game']['control']))
        self.assertEqual(before['game']['accepted_updates'], after['game']['accepted_updates'])
        self.assertEqual(before['final_score']['owner_costs'], after['final_score']['owner_costs'])
        self.assertEqual(before['final_score']['objective_veh_h'], after['final_score']['objective_veh_h'])
        proof = after['queries']['first_owner_prefetch']
        self.assertTrue(proof['completed'])
        self.assertEqual(proof['owners'], list(self.owners))
        self.assertFalse(proof['selection_or_domain_changed'])

    def test_first_owner_prefetch_does_not_exceed_a_small_evaluation_budget(self):
        self.follower.cfg.network.control_area_prefetch_first_owner_responses = True
        def query(actions):
            self.assertEqual(len(actions), 1)
            return self.batch(self.follower, self.state, self.action, self.forecast,
                              actions, horizon_steps=3)
        query.stats = lambda: {'parallel_workers': 4}
        result = self.solve(response_query=query, traversal='round_robin', max_evaluations=2)
        self.assertNotIn('first_owner_prefetch', result['queries'])
        self.assertEqual(result['game']['error']['kind'], 'evaluation_budget')

    def full_sweep_query(self):
        cache, sizes = {}, []
        def query(actions):
            sizes.append(len(actions)); result, misses = [], 0
            for action in actions:
                key = digest(action)
                if key not in cache:
                    cache[key] = self.batch(self.follower, self.state, self.action, self.forecast,
                        (action,), horizon_steps=3)['results'][0]
                    misses += 1
                result.append(copy.deepcopy(cache[key]))
            return {'results': result, 'endpoint_calls': misses, 'endpoint_sec': .01*misses, 'score_sec': 0.}
        query.stats = lambda: {'parallel_workers': 4, 'cache_enabled': True}
        return query, sizes, cache

    def multiple_neighbors(self, owner, action, context):
        self.neighbor_calls.append(owner)
        address = next(a for a in self.addresses if a.owner == owner)
        candidates = [copy.deepcopy(action)]
        for value in (2., 3., 4., 2.):
            trial = copy.deepcopy(action)
            getattr(trial, address.field)[address.key] = value
            candidates.append(trial)
        return game.Neighborhood(tuple(candidates), True, 'Fixed values with duplicate and incumbent')

    def test_complete_sweep_prefetch_keeps_all_evaluations_updates_and_final_gaps(self):
        self.callbacks['neighbors'] = self.multiple_neighbors
        for cap in (1000, 60):
            with self.subTest(cap=cap):
                self.follower.cfg.network.control_area_prefetch_complete_sweep_responses = False
                q, _, baseline_cache = self.full_sweep_query(); events = []
                before = self.solve(response_query=q, traversal='round_robin', time_budget_sec=None,
                    max_sweeps=2, max_evaluations=cap, progress=events.append)
                self.follower.cfg.network.control_area_prefetch_complete_sweep_responses = True
                q, sizes, cache = self.full_sweep_query(); observed = []
                after = self.solve(response_query=q, traversal='round_robin', time_budget_sec=None,
                    max_sweeps=2, max_evaluations=cap, progress=observed.append)
                for key in ('control', 'accepted_updates', 'per_owner', 'search_sweeps', 'evaluations',
                            'certified', 'final_check_complete', 'maximum_finite_candidate_gap', 'error'):
                    self.assertEqual(before['game'][key], after['game'][key])
                self.assertEqual(set(baseline_cache), set(cache))
                self.assertEqual(before['final_score']['owner_costs'], after['final_score']['owner_costs'])
                self.assertEqual(before['final_score']['objective_veh_h'], after['final_score']['objective_veh_h'])
                self.assertEqual(before['queries']['endpoint_calls'], after['queries']['endpoint_calls'])
                event_key = lambda e:(e['owner'], e['requests'], e['feasible'], e['witness_complete'])
                self.assertEqual(list(map(event_key, events)),
                    [event_key(e) for e in observed if e['stage']=='joint_candidate_evaluated'])
                proof = after['queries']['complete_sweep_prefetch']
                if cap == 1000:
                    self.assertIn(4, sizes)
                    self.assertLessEqual(max(sizes), 4)
                    self.assertEqual(proof['completed_bases'], 3)  # two sweeps and final action audit
                    self.assertFalse(proof['selection_or_domain_changed'])
                else:
                    self.assertEqual(max(sizes), 1)
                    self.assertGreater(proof['skipped_insufficient_evaluation_budget'], 0)

    def test_complete_sweep_prefetch_requires_unlimited_parallel_round_robin(self):
        self.follower.cfg.network.control_area_prefetch_complete_sweep_responses = True
        q, _, _ = self.full_sweep_query()
        for kwargs in ({'time_budget_sec': 120., 'traversal':'round_robin', 'response_query':q},
                       {'time_budget_sec':None, 'traversal':'sequential', 'response_query':q},
                       {'time_budget_sec':None, 'traversal':'round_robin', 'response_query':None}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, 'Complete-sweep prefetch requires'):
                self.solve(**kwargs)
        q.stats = lambda: {'parallel_workers': 4, 'cache_enabled': False}
        with self.assertRaisesRegex(ValueError, 'Complete-sweep prefetch requires'):
            self.solve(response_query=q, traversal='round_robin', time_budget_sec=None)

    def test_complete_sweep_prefetch_rejects_query_mutation_without_a_certificate(self):
        self.follower.cfg.network.control_area_prefetch_complete_sweep_responses = True
        original, _, _ = self.full_sweep_query()
        def query(actions):
            result = original(actions)
            if len(actions)>1:
                actions[0].N_P_star += 1.
            return result
        query.stats = original.stats
        value = self.solve(response_query=query, traversal='round_robin', time_budget_sec=None)
        self.assertFalse(value['game']['certified'])
        self.assertIsNone(value['game']['maximum_finite_candidate_gap'])
        self.assertIn('changed its supplied actions', value['game']['error']['message'])
        self.assertEqual(value['game']['control'], self.action)

    def test_response_bound_to_other_action_is_rejected(self):
        original = self.batch
        def wrong(*args, **kwargs):
            value = original(*args, **kwargs)
            value['results'][0]['action_token'] = 'wrong'
            return value
        self.batch = wrong
        result = self.solve()
        self.assertFalse(result['game']['certified'])
        self.assertIn('another full action', result['game']['error']['message'])
        self.assertIsNone(result['final_score'])

    def test_final_serialization_cannot_change_scored_action_after_certificate(self):
        def corrupt(action, context):
            action.N_P_star += 10.
            return {'synthetic_commands': self.values(action)}
        self.callbacks['command_evidence'] = corrupt
        before = digest(self.action)
        with self.assertRaisesRegex(ValueError, 'serialization changed'):
            self.solve()
        self.assertEqual(digest(self.action), before)

    def test_better_priced_candidate_cannot_escape_shared_quantity_cap(self):
        self.quantity_feasible = lambda action: all(v <= 1. for v in self.values(action).values())
        result = self.solve()
        self.assertTrue(result['game']['certified'])
        self.assertEqual(result['game']['accepted_updates'], [])
        self.assertEqual(result['final_score']['objective_veh_h'], 19.)
        self.assertTrue(all(row['infeasible_neighbors'] == 1 for row in result['game']['per_owner'].values()))


class HistoricalVSLTests(unittest.TestCase):
    def test_missing_segment_values_use_actual_callback_without_other_changes(self):
        action = NS(vsl={'FW_E': 120.}, diagnostics={'recorded': True}, N_P_star=9.)
        cfg = NS(network=NS(freeway_links=('FW_E',), freeway_vsl_zone_head_of_cell={'FW_E': (0, 0)}))
        def actual(action, link, i, cfg):
            return action.vsl.get(f'{link}__seg{i}', action.vsl[link])
        before = digest(action)
        expanded, evidence = subject.expand_shared_vsl_action(action, cfg, segment_vsl_func=actual)
        self.assertEqual(expanded.vsl, {'FW_E': 120., 'FW_E__seg0': 120., 'FW_E__seg1': 120.})
        self.assertEqual(digest(action), before)
        self.assertEqual(expanded.diagnostics, action.diagnostics)
        self.assertEqual(len(evidence['added_segment_keys']), 2)

    def test_inconsistent_explicit_value_is_not_silently_normalized(self):
        action = NS(vsl={'FW_E': 120., 'FW_E__seg1': 100.}, diagnostics={})
        cfg = NS(network=NS(freeway_links=('FW_E',), freeway_vsl_zone_head_of_cell={'FW_E': (0, 0)}))
        with self.assertRaisesRegex(ValueError, 'explicit VSL differs'):
            subject.expand_shared_vsl_action(action, cfg,
                segment_vsl_func=lambda action, link, i, cfg: action.vsl[link])


if __name__ == '__main__':
    unittest.main()
