"""Query transport/cache isolation tests; the endpoint here is synthetic."""
import copy
import gc
import hashlib
import pickle
import json
import zipfile
from time import perf_counter
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import area_follower_objective as subject
from evaluation.controllers import area_leader_objective, vissim_stackelberg_adapter as adapter
from src.controllers import rollout_endpoint


BASELINE = ROOT / 'diagnostics/shared_owner_copy_optimization_v1/baseline_functions.zip'
BASELINE_SHA = 'b42db8fbea63bd08181fe9f2867b01a58d6df7800b85da0e1c997d0974f3080d'


def baseline_functions():
    if hashlib.sha256(BASELINE.read_bytes()).hexdigest() != BASELINE_SHA:
        raise AssertionError('Frozen pre-change function fixture changed')
    env = dict(vars(subject))
    with zipfile.ZipFile(BASELINE) as z:
        for name in ('evaluate_shared_owner_batch', 'solve_fixed_shared_game'):
            exec(compile(z.read(name+'.py'), str(BASELINE)+'/'+name, 'exec'), env)
    return env


def without_timing(value):
    """Only elapsed timers differ; full data/tokens/counts/scope remain exact."""
    timers = {'endpoint_sec', 'score_sec', 'solve_wall_sec', 'local_score_sec',
              'price_sec', 'query_sec', 'elapsed_sec'}
    if isinstance(value, dict):
        return {k: without_timing(v) for k, v in value.items() if k not in timers}
    if isinstance(value, (tuple, list)):
        return type(value)(without_timing(v) for v in value)
    return value


class CountedContext:
    copies = 0
    def __init__(self):
        self.values = [{str(i): [float(i), float(i+1)]} for i in range(1500)]

    def __deepcopy__(self, memo):
        type(self).copies += 1
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        result.values = copy.deepcopy(self.values, memo)
        return result


class SharedOwnerBatchTests(unittest.TestCase):
    def test_joint_fingerprint_keeps_exact_guard_and_original_failure_bytes(self):
        runtime = {'_CACHE': {'values': [1, 2]}, 'ordinary': {'ignored': 1}}
        source = NS(**runtime)
        context = {'queue': [4.], 'alias': source._CACHE['values']}
        fingerprint = subject.joint_context_fingerprint(source)
        before = pickle.dumps((context, {'_CACHE': source._CACHE}), protocol=5)
        self.assertEqual(fingerprint(context), hashlib.sha256(before).hexdigest())
        self.assertEqual(fingerprint(context), hashlib.sha256(before).hexdigest())
        # Value equality does not license losing a context/runtime shared ref.
        with self.assertRaises(subject.FrozenJointContextError) as caught:
            fingerprint(copy.deepcopy(context))
        error = caught.exception
        self.assertEqual(error.before, before)
        self.assertNotEqual(error.before, error.after)
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'action.joint.json'
            evidence = error.write_evidence(report)
            for name, payload in (('before', error.before), ('after', error.after)):
                item = evidence[name]
                self.assertEqual(Path(item['path']).read_bytes(), payload)
                self.assertEqual(item['sha256'], hashlib.sha256(payload).hexdigest())
                self.assertEqual(item['bytes'], len(payload))
            with self.assertRaises(FileExistsError):
                error.write_evidence(report)
        self.assertEqual(context['queue'], [4.])
        self.assertIs(context['alias'], source._CACHE['values'])

    def test_joint_fingerprint_detects_runtime_and_physical_changes_without_extra_pickle(self):
        source = NS(_CACHE={'nested': {'value': 2}})
        context = {'queue': [4.]}
        original_dumps = pickle.dumps
        fingerprint = subject.joint_context_fingerprint(source)
        with patch.object(pickle, 'dumps', wraps=original_dumps) as dumps:
            token = fingerprint(context)
            self.assertEqual(fingerprint(copy.deepcopy(context)), token)
            self.assertEqual(dumps.call_count, 2)
        source._CACHE['nested']['value'] = 3
        with self.assertRaisesRegex(subject.FrozenJointContextError, 'Frozen joint query context changed'):
            fingerprint(context)
        source._CACHE['nested']['value'] = 2
        self.assertEqual(fingerprint(context), token)
        context['queue'].append(5.)
        with self.assertRaises(subject.FrozenJointContextError):
            fingerprint(context)

    def test_failed_joint_receipt_keeps_guard_failure_even_if_evidence_write_fails(self):
        for evidence_failure in (False, True):
            with self.subTest(evidence_failure=evidence_failure), tempfile.TemporaryDirectory() as directory:
                report_path = Path(directory) / 'action.joint.json'
                error = subject.FrozenJointContextError(b'original bytes', b'changed bytes')
                write = error.write_evidence
                if evidence_failure:
                    write = lambda _: (_ for _ in ()).throw(OSError('evidence unavailable'))
                with patch.object(adapter, 'load_joint_historical_reference', return_value=({'previous': self.reference}, {})), \
                     patch.object(adapter, 'joint_runtime_source_pins', return_value={}), \
                     patch.object(subject, 'expand_shared_vsl_action', return_value=(self.reference, {})), \
                     patch.object(subject, 'solve_runtime_joint_leader', side_effect=error), \
                     patch.object(error, 'write_evidence', side_effect=write):
                    with self.assertRaises(subject.FrozenJointContextError) as caught:
                        adapter.run_joint_owner_decision(NS(), self.state, self.forecast, self.reference,
                            NS(simulation=NS(T_c_sec=150.)), {}, {}, {'run_id': 'synthetic'},
                            Path(directory) / 'previous.json', {}, report_path, segment_vsl_func=None)
                self.assertIs(caught.exception, error)
                report = json.loads(report_path.read_text(encoding='utf-8'))
                self.assertFalse(report['completed'])
                self.assertEqual(report['error']['message'], 'Frozen joint query context changed')
                if evidence_failure:
                    self.assertEqual(report['frozen_context_evidence_error']['type'], 'OSError')
                else:
                    self.assertEqual(Path(report['frozen_context_evidence']['before']['path']).read_bytes(), error.before)

    def setUp(self):
        self.follower = NS(cfg=NS(network=NS(control_area_enabled=True)))
        self.state = NS(time_sec=900., stock=[3.])
        self.reference = NS(value=120., diagnostics={})
        self.forecast = [NS(demand=7.)]
        self.calls = []
        self.old = copy.deepcopy(adapter._LEGSPLIT_LAST)
        self.identity = adapter._LEGSPLIT_LAST
        def endpoint(state, action, demand, schedule, spec, *, capture_response):
            self.calls.append(action.value)
            adapter._LEGSPLIT_LAST['batch_test_probe'] = action.value
            return NS(aborted=False, states=[NS()] * spec.depth_override,
                objective=action.value + state.stock[0] + demand[0].demand,
                control_area={'ttt_veh_h': action.value},
                control_area_response={'resource_allocations': [], 'value': action.value})
        self.endpoint = endpoint
        self.addCleanup(self.restore)

    def restore(self):
        adapter._LEGSPLIT_LAST.clear()
        adapter._LEGSPLIT_LAST.update(self.old)

    def run_batch(self, actions, *, endpoint=None, scorer=None):
        def score(follower, point, state, candidate, reference, *, horizon_steps):
            return {'owner': {'cost': point.objective + reference.value}}
        with patch.object(rollout_endpoint, 'evaluate_price_point', endpoint or self.endpoint), \
             patch.object(subject, 'score_shared_owner_point', scorer or score), \
             patch.object(area_leader_objective, 'shared_urban_quantities', return_value={'owners': {}}):
            return subject.evaluate_shared_owner_batch(self.follower, self.state, self.reference,
                self.forecast, actions, horizon_steps=3)

    def test_exact_repeats_reuse_only_within_this_batch_and_output_is_independent(self):
        trial = NS(value=100., diagnostics={})
        result = self.run_batch([self.reference, self.reference, trial, trial])
        self.assertEqual(self.calls, [120., 100.])
        self.assertEqual((result['endpoint_calls'], result['cache_hits']), (2, 2))
        self.assertEqual(result['results'][0], result['results'][1])
        result['results'][0]['local_costs']['owner']['cost'] = -999.
        self.assertGreater(result['results'][1]['local_costs']['owner']['cost'], 0.)
        self.run_batch([self.reference])
        self.assertEqual(self.calls, [120., 100., 120.])
        self.assertIs(adapter._LEGSPLIT_LAST, self.identity)
        self.assertEqual(adapter._LEGSPLIT_LAST, self.old)

    def test_response_gc_scope_restores_state_after_failure_and_nested_scope(self):
        was_enabled = gc.isenabled()
        self.addCleanup(gc.enable if was_enabled else gc.disable)
        gc.enable()
        with self.assertRaisesRegex(RuntimeError, 'failed response'):
            with subject.shared_response_gc_scope(True) as outer:
                self.assertFalse(gc.isenabled())
                with subject.shared_response_gc_scope(True) as inner:
                    self.assertFalse(gc.isenabled())
                self.assertEqual(inner['cyclic_gc_deferred_queries'], 0)
                self.assertFalse(gc.isenabled())
                raise RuntimeError('failed response')
        self.assertTrue(gc.isenabled())
        self.assertEqual(outer['cyclic_gc_deferred_queries'], 1)
        self.assertGreaterEqual(outer['cyclic_gc_cleanup_wall_sec'], 0.)
        gc.disable()
        with subject.shared_response_gc_scope(True) as already_off:
            self.assertFalse(gc.isenabled())
        self.assertFalse(gc.isenabled())
        self.assertEqual(already_off['cyclic_gc_deferred_queries'], 0)

    def test_noop_runtime_scope_preserves_keyword_set_encoding_and_root(self):
        for count in range(3, 40):
            keywords = {'runtime_keyword_' + str(i) for i in range(count)}
            with patch.object(adapter, '_TEST_RUNTIME_KEYWORDS', keywords, create=True):
                before = pickle.dumps(keywords, protocol=5)
                for _ in range(3):
                    with subject.shared_query_runtime_scope():
                        pass
                    self.assertIs(adapter._TEST_RUNTIME_KEYWORDS, keywords)
                    self.assertEqual(pickle.dumps(keywords, protocol=5), before)
                with subject.shared_query_runtime_scope():
                    keywords.add('temporary query flag')
                self.assertNotIn('temporary query flag', keywords)

    def test_response_gc_off_never_collects_or_toggles_and_invalid_flag_fails(self):
        with patch.object(gc, 'collect') as collect, patch.object(gc, 'disable') as disable:
            with subject.shared_response_gc_scope():
                pass
        collect.assert_not_called()
        disable.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'must be boolean'):
            with subject.shared_response_gc_scope(1):
                pass

    def test_opt_in_defers_only_endpoint_and_keeps_response_values(self):
        self.follower.cfg.network.control_area_defer_response_gc = True
        was_enabled = gc.isenabled()
        self.addCleanup(gc.enable if was_enabled else gc.disable)
        gc.enable()
        def endpoint(*args, **kwargs):
            self.assertFalse(gc.isenabled())
            return self.endpoint(*args, **kwargs)
        def score(follower, point, state, candidate, reference, **kwargs):
            self.assertTrue(gc.isenabled())
            return {'owner': {'cost': point.objective + reference.value}}
        result = self.run_batch([self.reference], endpoint=endpoint, scorer=score)
        self.assertTrue(gc.isenabled())
        self.assertEqual(result['results'][0]['objective_veh_h'], 130.)
        self.assertEqual(result['results'][0]['local_base_costs']['owner'], 250.)

    def test_other_action_payload_cannot_alias_and_context_changes_are_not_reused(self):
        other = NS(value=120., diagnostics={'different': True})
        before = self.run_batch([self.reference, other])
        self.assertEqual(before['endpoint_calls'], 2)
        self.state.stock[0] += 5.
        after = self.run_batch([self.reference])
        self.assertEqual(after['results'][0]['objective_veh_h'] - before['results'][0]['objective_veh_h'], 5.)
        self.assertNotEqual(after['results'][0]['frozen_context_token'], before['results'][0]['frozen_context_token'])

    def test_failed_query_restores_diagnostics_and_does_not_mutate_caller(self):
        before = copy.deepcopy((self.state, self.reference, self.forecast, self.follower))
        def fail(state, action, demand, schedule, spec, **kwargs):
            state.stock[0] = 999.
            action.value = 0.
            demand[0].demand = -1.
            spec.cfg.network.changed = True
            adapter._LEGSPLIT_LAST['new'] = 5.
            raise RuntimeError('synthetic endpoint failure')
        with self.assertRaisesRegex(RuntimeError, 'synthetic endpoint failure'):
            self.run_batch([self.reference], endpoint=fail)
        self.assertEqual(before, (self.state, self.reference, self.forecast, self.follower))
        self.assertIs(adapter._LEGSPLIT_LAST, self.identity)
        self.assertEqual(adapter._LEGSPLIT_LAST, self.old)

    def test_successful_but_mutating_endpoint_fails_before_cache_insert(self):
        def mutate(state, *args, **kwargs):
            point = self.endpoint(state, *args, **kwargs)
            state.stock.append(88.)
            return point
        with self.assertRaisesRegex(ValueError, 'mutated its frozen operands'):
            self.run_batch([self.reference, self.reference], endpoint=mutate)
        self.assertEqual(self.state.stock, [3.])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(adapter._LEGSPLIT_LAST, self.old)

    def test_truncated_endpoint_cannot_be_cached(self):
        def incomplete(*args, **kwargs):
            point = self.endpoint(*args, **kwargs)
            point.states.pop()
            return point
        with self.assertRaisesRegex(ValueError, 'Incomplete shared endpoint'):
            self.run_batch([self.reference], endpoint=incomplete)
        self.assertEqual(adapter._LEGSPLIT_LAST, self.old)

    def test_operational_runtime_data_restored_after_nested_success_and_failure(self):
        original = {'profile': {'lanes': [2, 3]}, 'armed': False}
        saved = copy.deepcopy(original)
        with patch.object(adapter, '_FW_SEG_CTX_STATE', original):
            with self.assertRaisesRegex(RuntimeError, 'query failed'):
                with subject.shared_query_runtime_scope():
                    original['profile']['lanes'].append(4)
                    with subject.shared_query_runtime_scope():
                        adapter._FW_SEG_CTX_STATE = {'profile': 'replacement'}
                        adapter._TEST_QUERY_NEW_STATE = [123]
                    self.assertIs(adapter._FW_SEG_CTX_STATE, original)
                    self.assertEqual(original['profile']['lanes'], [2, 3, 4])
                    self.assertFalse(hasattr(adapter, '_TEST_QUERY_NEW_STATE'))
                    raise RuntimeError('query failed')
            self.assertIs(adapter._FW_SEG_CTX_STATE, original)
            self.assertEqual(original, saved)

    def test_installed_follower_binding_is_restored_by_identity(self):
        follower = NS(prices={'SC1': 4.})
        binding = {'ref': follower, 'stats': {'calls': 2}}
        with patch.object(adapter, '_PHASE_VECTOR_FOLLOWER', binding):
            with subject.shared_query_runtime_scope():
                binding['stats']['calls'] = 99
                binding['ref'] = NS(prices={})
            self.assertIs(adapter._PHASE_VECTOR_FOLLOWER, binding)
            self.assertIs(binding['ref'], follower)
            self.assertEqual(binding['stats'], {'calls': 2})

    def test_frozen_public_batch_before_after_exact_including_context_tokens(self):
        def score(follower, point, state, candidate, reference, *, horizon_steps):
            return {'owner': {'cost': point.objective + reference.value}}
        actions = (self.reference, NS(value=100., diagnostics={'kept': [1, 2]}), self.reference)
        with patch.object(rollout_endpoint, 'evaluate_price_point', self.endpoint), \
             patch.object(subject, 'score_shared_owner_point', score), \
             patch.object(area_leader_objective, 'shared_urban_quantities', return_value={'owners': {}}):
            old = baseline_functions()['evaluate_shared_owner_batch'](
                self.follower, self.state, self.reference, self.forecast, actions, horizon_steps=3)
            new = subject.evaluate_shared_owner_batch(
                self.follower, self.state, self.reference, self.forecast, actions, horizon_steps=3)
        self.assertEqual(without_timing(old), without_timing(new))

    def test_43_unique_owned_queries_copy_fixed_graph_once_and_match_original(self):
        self.follower.cfg.network.large_frozen_definition = CountedContext()
        before = pickle.dumps((self.follower, self.state, self.reference, self.forecast), protocol=5)
        actions = [NS(value=float(i), diagnostics={'index': i}) for i in range(43)]
        def score(follower, point, state, candidate, reference, *, horizon_steps):
            return {'owner': {'cost': point.objective + reference.value}}
        with patch.object(rollout_endpoint, 'evaluate_price_point', self.endpoint), \
             patch.object(subject, 'score_shared_owner_point', score), \
             patch.object(area_leader_objective, 'shared_urban_quantities', return_value={'owners': {}}):
            old_call = baseline_functions()['evaluate_shared_owner_batch']
            CountedContext.copies = 0
            started = perf_counter()
            old = [old_call(self.follower, self.state, self.reference, self.forecast,
                            (action,), horizon_steps=3) for action in actions]
            old_sec, old_copies = perf_counter()-started, CountedContext.copies
            CountedContext.copies = 0
            started = perf_counter()
            owned = copy.deepcopy((self.follower, self.state, self.reference, self.forecast))
            new = [subject._evaluate_shared_owner_batch_owned(*owned,
                (copy.deepcopy(action),), horizon_steps=3) for action in actions]
            new_sec, new_copies = perf_counter()-started, CountedContext.copies
        self.assertEqual((old_copies, new_copies), (43, 1))
        self.assertEqual(without_timing(old), without_timing(new))
        self.assertEqual(before, pickle.dumps((self.follower, self.state, self.reference, self.forecast), protocol=5))
        # Timing is observational only: CI scheduling cannot invalidate semantic
        # correctness. This fixture is not an estimate of actual model wall time.
        type(self).copy_measurement = {'unique_candidates': 43,
            'old_context_deepcopies': old_copies, 'owned_context_deepcopies': new_copies,
            'old_sec': old_sec, 'owned_sec': new_sec, 'data_exact': True,
            'scope': 'Synthetic endpoint + 1500-entry copied context fixture only'}


class SharedGameOwnedCopyTests(unittest.TestCase):
    def setUp(self):
        from diagnostics.test_fixed_shared_game import FixedSharedGameTests
        fixture = FixedSharedGameTests(); fixture.setUp()
        self.fixture = fixture
        fixture.follower.cfg.network.large_frozen_definition = CountedContext()
        self.endpoint_calls = []

    def run_game(self, *, baseline=False, corrupt=None):
        fixture = self.fixture
        def endpoint(state, action, demand, schedule, spec, *, capture_response):
            self.endpoint_calls.append(pickle.dumps(action, protocol=5))
            if corrupt is not None:
                corrupt(state, action, demand, spec)
            values = fixture.values(action)
            return NS(aborted=False, states=[NS()] * spec.depth_override,
                objective=sum(v*v for v in values.values()),
                control_area={'ttt_veh_h': sum(values.values())},
                control_area_response={'resource_allocations': [],
                    'conditional_model_feasibility_witness': True,
                    'model_constraint_coverage': {'complete': True}})
        def score(follower, point, state, candidate, reference, *, horizon_steps):
            return {owner: {'cost': 10.*value} for owner, value in fixture.values(candidate).items()}
        kwargs = dict(callbacks=fixture.callbacks, context=fixture.context,
            context_fingerprint=lambda value: hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest(),
            horizon_steps=3, lambda_p=0., lambda_uf=0., target_np_veh=3., target_nuf_veh_h=5.,
            price_context={'np_mode': 'cap', 'nuf_mode': 'equality'}, max_sweeps=1,
            max_evaluations=1000, time_budget_sec=120., improvement_tolerance=1e-9,
            shared_tolerance=1e-7, scope_label='Synthetic fixed game transport only',
            np_tolerance_veh=1e-7, nuf_tolerance_veh_h=1e-7)
        with patch.object(rollout_endpoint, 'evaluate_price_point', endpoint), \
             patch.object(subject, 'score_shared_owner_point', score), \
             patch.object(area_leader_objective, 'shared_urban_quantities', return_value={'owners': {}}), \
             patch.object(area_leader_objective, 'fixed_joint_price_terms', fixture.prices), \
             patch.object(area_leader_objective, 'shared_quantity_constraints', return_value={'feasible': True}):
            call = baseline_functions()['solve_fixed_shared_game'] if baseline else subject.solve_fixed_shared_game
            return call(fixture.follower, fixture.state, fixture.action, fixture.forecast,
                        fixture.action, **kwargs)

    def test_actual_game_path_fixed_copy_once_full_selection_and_tokens_exact(self):
        before = pickle.dumps((self.fixture.follower, self.fixture.state, self.fixture.forecast,
                               self.fixture.action, self.fixture.context), protocol=5)
        CountedContext.copies = 0
        old = self.run_game(baseline=True)
        old_copies, old_calls = CountedContext.copies, list(self.endpoint_calls)
        CountedContext.copies = 0; self.endpoint_calls.clear()
        new = self.run_game()
        self.assertEqual((old_copies, CountedContext.copies), (21, 1))
        self.assertEqual(old_calls, self.endpoint_calls)
        self.assertEqual(without_timing(old), without_timing(new))
        self.assertTrue(new['game']['certified'])
        self.assertEqual(new['queries']['endpoint_calls'], 20)
        self.assertEqual(before, pickle.dumps((self.fixture.follower, self.fixture.state, self.fixture.forecast,
                               self.fixture.action, self.fixture.context), protocol=5))

    def test_mutation_then_exception_restores_private_context_before_core_finalizes(self):
        def fail(state, action, demand, spec):
            state.nested_dirty = [999.]
            action.N_P_star = 99.
            demand[0].demand = -999.
            spec.cfg.network.large_frozen_definition.values[0]['0'].append(999.)
            adapter._LEGSPLIT_LAST['contamination'] = [999.]
            raise RuntimeError('synthetic private graph mutation')
        before = pickle.dumps((self.fixture.follower, self.fixture.state, self.fixture.forecast,
                               self.fixture.action), protocol=5)
        old = self.run_game(baseline=True, corrupt=fail)
        new = self.run_game(corrupt=fail)
        self.assertEqual(without_timing(old), without_timing(new))
        self.assertFalse(new['game']['certified'])
        self.assertEqual(before, pickle.dumps((self.fixture.follower, self.fixture.state, self.fixture.forecast,
                               self.fixture.action), protocol=5))
        self.assertNotIn('contamination', adapter._LEGSPLIT_LAST)
        # A new solve is clean; no poisoned process-wide/private context reuse.
        self.assertTrue(self.run_game()['game']['certified'])

    def test_successful_but_mutating_query_is_rejected_and_restored(self):
        def mutate(state, action, demand, spec):
            spec.cfg.network.large_frozen_definition.values[0]['0'].append(999.)
        old = self.run_game(baseline=True, corrupt=mutate)
        new = self.run_game(corrupt=mutate)
        self.assertEqual(without_timing(old), without_timing(new))
        self.assertIn('mutated its frozen operands', new['game']['error']['message'])
        self.assertFalse(new['game']['certified'])

    def test_later_failed_candidate_preserves_prior_score_and_final_command(self):
        def fail_changed(state, action, demand, spec):
            if any(value != 1. for value in self.fixture.values(action).values()):
                state.changed_after_first_success = True
                demand[0].demand = -1.
                spec.cfg.network.large_frozen_definition.values.clear()
                raise RuntimeError('later candidate failed')
        old = self.run_game(baseline=True, corrupt=fail_changed)
        new = self.run_game(corrupt=fail_changed)
        self.assertEqual(without_timing(old), without_timing(new))
        self.assertIsNotNone(new['final_score'])
        self.assertEqual(new['queries']['endpoint_calls'], 1)
        self.assertEqual(new['game']['accepted_updates'], [])
        self.assertEqual(new['final_score']['objective_veh_h'], 19.)


if __name__ == '__main__':
    unittest.main()
