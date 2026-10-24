"""Decision-local response reuse contracts; synthetic endpoint, no native run."""
import copy
import pickle
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from diagnostics import test_shared_owner_batch as fixtures
from evaluation.controllers import area_leader_objective
subject, adapter, rollout_endpoint = fixtures.subject, fixtures.adapter, fixtures.rollout_endpoint


class DecisionSharedResponseCacheTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.SharedOwnerBatchTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.patchers = [
            patch.object(rollout_endpoint, 'evaluate_price_point', self.fixture.endpoint),
            patch.object(subject, 'score_shared_owner_point', self.score),
            patch.object(area_leader_objective, 'shared_urban_quantities', return_value={'owners': {}})]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def score(follower, point, state, candidate, reference, *, horizon_steps):
        return {'owner': {'cost': point.objective+reference.value}}

    def query(self, **changes):
        args = dict(horizon_steps=3, source_fingerprint='fixed-runtime-sources', cache_enabled=True)
        args.update(changes)
        f = self.fixture
        return subject.make_decision_shared_query(f.follower, f.state, f.reference, f.forecast, **args)

    def test_same_action_reused_between_price_and_follower_queries_with_exact_results(self):
        q = self.query()
        ref = self.fixture.reference
        first = q((ref,))
        second = q((ref, ref))
        self.assertEqual(self.fixture.calls, [120.])
        self.assertEqual(pickle.dumps(first['results'][0]), pickle.dumps(second['results'][0]))
        second['results'][0]['local_costs']['owner']['cost'] = -99.
        self.assertGreater(second['results'][1]['local_costs']['owner']['cost'], 0.)
        self.assertEqual(q.stats()['endpoint_calls'], 1)
        self.assertEqual(q.stats()['cache_hits'], 2)
        self.assertEqual(q.stats()['hit_rate'], 2/3)
        self.assertGreater(q.stats()['retained_result_bytes'], 0)

    def test_cache_off_keeps_identical_physics_and_local_scores(self):
        on, off = self.query(), self.query(cache_enabled=False)
        actions = (self.fixture.reference, NS(value=100., diagnostics={}))
        for _ in range(2):
            a, b = on(actions), off(actions)
            self.assertEqual(pickle.dumps(a['results']), pickle.dumps(b['results']))
        self.assertEqual(on.stats()['endpoint_calls'], 2)
        self.assertEqual(off.stats()['endpoint_calls'], 4)
        self.assertEqual(on.stats()['context_token'], off.stats()['context_token'])
        self.assertEqual(off.stats()['retained_result_bytes'], 0)

    def test_exact_full_action_keys_do_not_drop_target_or_diagnostic_payload(self):
        q = self.query()
        values = [NS(value=100., N_P_star=np, N_UF_star=nuf, diagnostics=diag)
                  for np, nuf, diag in [(0., 100., {}), (1., 100., {}), (0., 200., {}),
                                       (0., 100., {'different': True})]]
        q(values)
        self.assertEqual(q.stats()['endpoint_calls'], 4)

    def test_price_holder_changes_do_not_change_owned_physical_context(self):
        f = self.fixture
        f.follower.prices = {'owner': 1.}
        q = self.query()
        first = q((f.reference,))
        f.follower.prices['owner'] = 999.
        second = q((f.reference,))
        self.assertEqual(first['results'], second['results'])
        # New price/dual scoring can use the same physical base without a query.
        base = first['results'][0]['local_base_costs']['owner']
        self.assertNotEqual(base+1., base+999.)
        self.assertEqual(q.stats()['endpoint_calls'], 1)

    def test_new_state_horizon_source_and_runtime_form_distinct_cache_namespaces(self):
        f = self.fixture
        first = self.query()
        a = first((f.reference,))
        second = self.query(horizon_steps=2)
        second((f.reference,))
        third = self.query(source_fingerprint='other-source')
        third((f.reference,))
        f.state.stock[0] += 5.
        fourth = self.query()
        d = fourth((f.reference,))
        with patch.object(adapter, '_FW_SEG_CTX_STATE', {'profile': {'lanes': [3]}}):
            fifth = self.query()
            fifth((f.reference,))
        self.assertEqual(len({q.stats()['context_token'] for q in (first, second, third, fourth, fifth)}), 5)
        self.assertEqual(d['results'][0]['objective_veh_h']-a['results'][0]['objective_veh_h'], 5.)

    def test_failed_mutating_query_is_not_cached_and_private_context_is_restored(self):
        q = self.query()
        def fail(state, *args, **kwargs):
            state.stock[0] = 999.
            raise RuntimeError('failed physical query')
        with patch.object(rollout_endpoint, 'evaluate_price_point', fail):
            with self.assertRaisesRegex(RuntimeError, 'failed physical query'):
                q((self.fixture.reference,))
        value = q((self.fixture.reference,))
        self.assertEqual(value['results'][0]['objective_veh_h'], 130.)
        self.assertEqual(q.stats()['endpoint_attempts'], 2)
        self.assertEqual(q.stats()['endpoint_calls'], 1)
        self.assertEqual(q.stats()['failures'], 1)

    def test_shared_deadline_checked_before_each_response_preserves_completed_prefix(self):
        def check(stage):
            if stage == 'physical_response' and len(self.fixture.calls) >= 1:
                raise TimeoutError('decision deadline')
        q = self.query(check_budget=check)
        with self.assertRaisesRegex(TimeoutError, 'decision deadline'):
            q((self.fixture.reference, NS(value=100., diagnostics={})))
        self.assertEqual(self.fixture.calls, [120.])
        self.assertEqual(q.stats()['endpoint_calls'], 1)
        self.assertEqual(q.stats()['failures'], 1)

    def test_operational_runtime_and_caller_binding_are_restored_after_queries(self):
        bound = NS(caller_prices={'owner': 50.})
        binding = {'ref': bound, 'stats': {'hits': 2}}
        runtime = {'profile': {'lanes': [4]}, 'armed': False}
        with patch.object(adapter, '_PHASE_VECTOR_FOLLOWER', binding), \
             patch.object(adapter, '_FW_SEG_CTX_STATE', runtime):
            q = self.query()
            before = copy.deepcopy(runtime)
            q((self.fixture.reference,))
            self.assertIs(adapter._PHASE_VECTOR_FOLLOWER, binding)
            self.assertIs(adapter._PHASE_VECTOR_FOLLOWER['ref'], bound)
            self.assertEqual(adapter._PHASE_VECTOR_FOLLOWER['stats'], {'hits': 2})
            self.assertIs(adapter._FW_SEG_CTX_STATE, runtime)
            self.assertEqual(runtime, before)


if __name__ == '__main__':
    unittest.main()
