"""Bounded asynchronous final-audit transport and scheduling, synthetic only."""
import copy
import pickle
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from diagnostics import test_parallel_shared_response as parallel_fixtures
from diagnostics import test_selected_final_audit_runtime as audit_fixtures
from evaluation.controllers import area_follower_objective as subject


class AsyncTransportTests(unittest.TestCase):
    def setUp(self):
        self.f = parallel_fixtures.ParallelSharedResponseTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def query(self, **kwargs):
        return self.f.parallel(workers=4, unlimited_time=True, deadline_monotonic=None, **kwargs)

    def test_transport_accepts_in_original_order_only_after_finish(self):
        q = self.query()
        reference = self.f.fixture.reference
        actions = (reference, NS(value=100., diagnostics={}), reference)
        parallel_fixtures.ImmediateExecutor.reverse_pair = True
        finish = q.submit_prefetch(actions)
        self.assertEqual(q.stats()['parallel_submitted'], 2)
        self.assertEqual(q.stats()['parallel_accepted'], 0)
        batch = finish()
        self.assertEqual([r['objective_veh_h'] for r in batch['results']], [130., 110., 130.])
        self.assertEqual((batch['endpoint_calls'], batch['cache_hits']), (2, 1))
        self.assertEqual(q((reference,))['results'][0], batch['results'][0])
        self.assertEqual(q.stats()['parallel_prefetch_max_pending_batches'], 1)
        with self.assertRaisesRegex(ValueError, 'already consumed'):
            finish()
        self.assertEqual(q.stats()['owned_workers_alive'], [])

    def test_pending_future_cleanup_and_bad_transport_fail_closed(self):
        q = self.query()
        parallel_fixtures.ImmediateExecutor.pending = True
        finish = q.submit_prefetch((self.f.fixture.reference,))
        q.close()
        self.assertEqual(q.stats()['parallel_prefetch_cancelled_batches'], 1)
        self.assertEqual(q.stats()['owned_workers_alive'], [])
        with self.assertRaises(ValueError):
            finish()

    def test_deadline_callback_still_runs_when_finishing_unlimited_transport(self):
        stages, stop = [], {'enabled': False}
        def check(stage):
            stages.append(stage)
            if stop['enabled']:
                raise TimeoutError('explicit cooperative stop')
        q = self.query(check_budget=check)
        finish = q.submit_prefetch((self.f.fixture.reference,))
        stop['enabled'] = True
        with self.assertRaisesRegex(TimeoutError, 'cooperative stop'):
            finish()
        self.assertIn('async_audit_finish', stages)
        self.assertEqual(q.stats()['owned_workers_alive'], [])

    def test_bad_action_proof_is_never_inserted_as_accepted_response(self):
        q = self.query()
        parallel_fixtures.ImmediateExecutor.alter = lambda envelope: envelope.update(action_token='bad')
        finish = q.submit_prefetch((self.f.fixture.reference,))
        with self.assertRaisesRegex(ValueError, 'proof'):
            finish()
        self.assertEqual(q.stats()['parallel_accepted'], 0)
        self.assertEqual(q.stats()['owned_workers_alive'], [])

    def test_at_most_one_worker_sized_batch_and_no_hidden_duplicate_miss(self):
        for kind in ('too_many', 'second_batch', 'uncached_read'):
            with self.subTest(kind=kind):
                q = self.query()
                if kind == 'too_many':
                    with self.assertRaisesRegex(ValueError, 'worker-sized'):
                        q.submit_prefetch((self.f.fixture.reference,)*5)
                else:
                    q.submit_prefetch((self.f.fixture.reference,))
                    with self.assertRaises(ValueError):
                        if kind == 'second_batch':
                            q.submit_prefetch((NS(value=80., diagnostics={}),))
                        else:
                            q((self.f.fixture.reference,))
                self.assertEqual(q.stats()['owned_workers_alive'], [])


class AuditPipelineTests(unittest.TestCase):
    def setUp(self):
        self.f = audit_fixtures.SelectedAuditIntegrationTests()
        self.f.setUp()
        inner = self.f.f
        inner.follower.cfg.network.control_area_response_scheduling = {'lookahead': 4, 'final_check_reserve_sec': 0.}
        inner.follower.cfg.network.control_area_reuse_final_audit_physical_proofs = True
        inner.follower.cfg.network.control_area_audit_response_pipeline = True
        inner.callbacks['guard_physical_proofs'] = lambda c: None

    def query(self, events, bad=False):
        query, sizes, cache = self.f.f.full_sweep_query()
        def submit(probes):
            frozen = tuple(pickle.dumps(p, protocol=5) for p in probes)
            events.append(('submit', frozen))
            def finish():
                events.append(('finish', frozen))
                result = query(probes)
                if bad:
                    result['results'][0]['action_token'] = 'bad'
                return result
            return finish
        query.submit_prefetch = submit
        return query, sizes, cache

    def test_full_pipeline_keeps_exact_work_order_scores_gaps_and_zero_pending_reads(self):
        old_events, new_events = [], []
        q, _, old_cache = self.query(old_events)
        original = subject._make_bounded_response_schedule
        def synchronous(*a, **k):
            return original(*a, **{**k, 'audit_response_pipeline': False})
        old_progress, new_progress = [], []
        with patch.object(subject, '_make_bounded_response_schedule', synchronous):
            before = self.f.run_fixed(self.f.f.action, audit_only=True, response_query=q,
                                      progress=old_progress.append)
        q, sizes, new_cache = self.query(new_events)
        def progress(event):
            new_progress.append(event)
            if event['stage'] == 'joint_candidate_evaluated':
                new_events.append(('evaluate', event['requests']))
        after = self.f.run_fixed(self.f.f.action, audit_only=True, response_query=q, progress=progress)
        self.assertEqual(set(new_cache), set(old_cache))
        for key in ('final_score', 'final_action_token', 'command_evidence'):
            self.assertEqual(after[key], before[key])
        for key in ('per_owner', 'evaluations', 'maximum_finite_candidate_gap', 'accepted_updates', 'final_check_complete'):
            self.assertEqual(after['game'][key], before['game'][key])
        semantic = lambda events: [(r['owner'], r['requests'], r['feasible']) for r in events
                                   if r['stage'] == 'joint_candidate_evaluated']
        self.assertEqual(semantic(new_progress), semantic(old_progress))
        proof = after['queries']['bounded_response_schedule']
        self.assertLessEqual(proof['pipeline_max_buffered_logical_reads'], 8)
        self.assertEqual(proof['pipeline_pending_logical_reads'], 0)
        self.assertEqual(proof['unconsumed_prefetched_actions'], 0)
        self.assertEqual(proof['requested_responses'], after['game']['evaluations'])
        self.assertLessEqual(max(sizes), 4)
        self.assertEqual([name for name, _ in new_events[:4]], ['submit', 'finish', 'submit', 'evaluate'])

    def test_bad_pipeline_response_cannot_claim_complete_final_audit(self):
        q, _, _ = self.query([], bad=True)
        result = self.f.run_fixed(self.f.f.action, audit_only=True, response_query=q)
        self.assertFalse(result['game']['final_check_complete'])
        self.assertIsNone(result['game']['maximum_finite_candidate_gap'])
        self.assertFalse(result['game']['certified'])

    def test_search_never_uses_async_submission_and_bounded_audit_is_rejected(self):
        events = []
        q, _, _ = self.query(events)
        self.f.run_fixed(self.f.f.action, defer_final_audit=True, response_query=q)
        self.assertEqual(events, [])
        with self.assertRaisesRegex(ValueError, 'unlimited fixed inventory'):
            self.f.run_fixed(self.f.f.action, audit_only=True, response_query=q, time_budget_sec=10.)


if __name__ == '__main__':
    unittest.main()
