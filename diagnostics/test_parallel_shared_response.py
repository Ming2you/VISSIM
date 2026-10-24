"""Pure transport/lifecycle tests; mock executor, no spawn/model/native run."""
from concurrent.futures import Future
import copy
import hashlib
import os
import pickle
import tempfile
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from diagnostics import test_decision_shared_response_cache as cache_fixtures
from evaluation.controllers import area_follower_objective as subject, runtime_setup


class OwnedProcess:
    def __init__(self):
        self.pid = os.getpid()
        self.alive = True
        self.terminated = self.killed = 0
    def is_alive(self):
        return self.alive
    def terminate(self):
        self.terminated += 1
        self.alive = False
    def kill(self):
        self.killed += 1
        self.alive = False
    def join(self, timeout=None):
        pass


class ImmediateExecutor:
    instances = []
    alter = None
    pending = False
    reverse_pair = False
    def __init__(self, *, max_workers, mp_context, initializer, initargs):
        self.max_workers = max_workers
        self.context = mp_context.get_start_method()
        self.process = OwnedProcess()
        self._processes = {self.process.pid: self.process}
        self.shutdowns = []
        self.queued = []
        self.error = None
        type(self).instances.append(self)
        try:
            initializer(*initargs)
        except BaseException as exc:
            self.error = exc

    def finish(self, fn, task, future):
        try:
            if self.error:
                raise self.error
            value = fn(task)
            if type(self).alter:
                type(self).alter(value)
            future.set_result(value)
        except BaseException as exc:
            future.set_exception(exc)

    def submit(self, fn, task):
        future = Future()
        if self.pending:
            return future
        if self.reverse_pair:
            self.queued.append((fn, task, future))
            if len(self.queued) == 2:
                for args in reversed(self.queued):
                    self.finish(*args)
                self.queued.clear()
        else:
            self.finish(fn, task, future)
        return future

    def shutdown(self, wait=True, *, cancel_futures=False):
        self.shutdowns.append((wait, cancel_futures))


class ParallelSharedResponseTests(unittest.TestCase):
    def setUp(self):
        original = cache_fixtures.DecisionSharedResponseCacheTests()
        original.setUp()
        self.addCleanup(original.doCleanups)
        self.fixture = original.fixture
        self.query = original.query
        ImmediateExecutor.instances = []
        ImmediateExecutor.alter = None
        ImmediateExecutor.pending = ImmediateExecutor.reverse_pair = False
        for patcher in (patch('concurrent.futures.ProcessPoolExecutor', ImmediateExecutor),
                        patch.object(runtime_setup, 'install_worker_runtime', return_value={'test': 1.})):
            patcher.start()
            self.addCleanup(patcher.stop)
        old_context = dict(subject._SHARED_RESPONSE_WORKER)
        self.addCleanup(lambda: (subject._SHARED_RESPONSE_WORKER.clear(), subject._SHARED_RESPONSE_WORKER.update(old_context)))

    def parallel(self, *, workers=1, **changes):
        path = Path(subject.__file__).resolve()
        options = dict(parallel_workers=workers, deadline_monotonic=perf_counter()+5.,
            worker_bootstrap={'state_json': {'network_path': str(path)}, 'detector_mapping': {},
                              'runtime_sources': {str(path): hashlib.sha256(path.read_bytes()).hexdigest()}})
        options.update(changes)
        q = self.query(**options)
        self.addCleanup(q.close)
        return q

    def test_worker1_exact_compact_result_and_cross_query_cache(self):
        serial, parallel = self.query(), self.parallel()
        actions = (self.fixture.reference, NS(value=100., diagnostics={}), self.fixture.reference)
        expected = serial(actions)
        actual = parallel(actions)
        self.assertEqual(pickle.dumps(actual['results'], protocol=5), pickle.dumps(expected['results'], protocol=5))
        self.assertEqual((actual['endpoint_calls'], actual['cache_hits']), (2, 1))
        self.assertEqual(parallel((actions[1],))['results'], [actual['results'][1]])
        self.assertEqual(parallel.stats()['endpoint_calls'], 2)
        self.assertEqual(parallel.stats()['cache_hits'], 2)
        self.assertEqual(parallel.stats()['context_token'], serial.stats()['context_token'])
        self.assertEqual(len(ImmediateExecutor.instances), 1)
        self.assertEqual(ImmediateExecutor.instances[0].context, 'spawn')
        actual['results'][0]['local_costs']['owner']['cost'] = -1.
        self.assertGreater(parallel((actions[0],))['results'][0]['local_costs']['owner']['cost'], 0.)
        parallel.close()
        self.assertEqual(parallel.stats()['owned_workers_alive'], [])
        self.assertEqual(ImmediateExecutor.instances[0].shutdowns, [(False, True)])

    def test_explicit_unlimited_workers_keep_exact_results_and_cleanup(self):
        finite=self.parallel()
        unbounded=self.parallel(unlimited_time=True,deadline_monotonic=None)
        actions=(self.fixture.reference,NS(value=100.,diagnostics={}))
        expected=finite(actions)['results'];finite.close()
        self.assertEqual(pickle.dumps(expected,protocol=5),pickle.dumps(unbounded(actions)['results'],protocol=5))
        self.assertIsNone(subject._SHARED_RESPONSE_WORKER['deadline'])
        unbounded.close();self.assertEqual(unbounded.stats()['owned_workers_alive'],[])
        with self.assertRaisesRegex(ValueError,'future whole-decision'):
            self.parallel(deadline_monotonic=None)
        with self.assertRaisesRegex(ValueError,'requires no deadline'):
            self.parallel(unlimited_time=True)

    def test_optional_full_response_audit_preserves_token_bytes_and_repeats(self):
        from diagnostics.check_fixed_candidate_response import _compare_full_response_audits
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            action = self.fixture.reference
            token = hashlib.sha256(pickle.dumps(action, protocol=5)).hexdigest()
            results = {}
            for arm in ('serial', 'spawn1'):
                directory = root / arm
                directory.mkdir()
                audit = {'directory': str(directory), 'action_tokens': (token,)}
                q = self.query(response_audit=audit) if arm == 'serial' else self.parallel(response_audit=audit)
                results[arm] = q((action,))['results']
                self.assertEqual(q((action,))['results'], results[arm])
                q.close()
                raw = (directory / (token + '.pickle')).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), results[arm][0]['response_token'])
                self.assertEqual(len(list(directory.iterdir())), 2)
            audit = _compare_full_response_audits(root, 'spawn1', results['serial'], results['spawn1'])
            self.assertTrue(audit[0]['full_response_value_comparison']['all_typed_values_exact'])
            with self.assertRaises(FileExistsError):
                subject._save_shared_response_audit(raw, token, 'context',
                    {'directory': str(root / 'serial'), 'action_tokens': (token,)})

    def test_response_audit_rejects_unbounded_or_undeclared_action(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'audit requires'):
                self.query(response_audit={'directory': temporary, 'action_tokens': ('a'*64,)*3})
            q = self.parallel(response_audit={'directory': temporary, 'action_tokens': ('a'*64,)})
            with self.assertRaisesRegex(ValueError, 'undeclared action'):
                q((self.fixture.reference,))
            self.assertEqual(list(Path(temporary).iterdir()), [])
            self.assertEqual(q.stats()['owned_workers_alive'], [])

    def test_full_response_diff_distinguishes_values_order_alias_and_bits(self):
        from diagnostics.check_fixed_candidate_response import _full_response_value_diff as compare
        import numpy as np
        common = [1., 2.]
        left = {'a': common, 'b': common, 'array': np.array([1., 2.], dtype='float64')}
        right = {'array': np.array([1., 2.], dtype='float64'), 'b': list(common), 'a': list(common)}
        result = compare(left, right)
        self.assertTrue(result['all_typed_values_exact'])
        self.assertEqual(result['counts']['dict_order_differences'], 1)
        self.assertNotEqual(*result['mutable_alias_graph_sha256'])
        self.assertTrue(compare({184: {('bin', 2.): [1., 2.]}},
                                {184: {('bin', 2.): [1., 2.]}})['all_typed_values_exact'])
        self.assertFalse(compare({1: 'x'}, {True: 'x'})['all_typed_values_exact'])
        for x, y in ((0., -0.), ([1., 2.], [2., 1.]), (1, True),
                     (np.array([1.], dtype='float32'), np.array([1.], dtype='float64')),
                     (object(), object())):
            self.assertFalse(compare(x, y)['all_typed_values_exact'])
        x = []; x.append(x)
        self.assertFalse(compare(x, x)['all_typed_values_exact'])

    def test_compact_qualification_requires_exact_bits_and_tokens_not_immutable_memo(self):
        from diagnostics.check_fixed_candidate_response import _parallel_compact_comparison as compare
        shared = ''.join(['same ', 'immutable value'])
        a = [{'response_token': 'r', 'action_token': 'a', 'frozen_context_token': 'c',
              'values': [shared, shared], 'cost': 0.}]
        b = copy.deepcopy(a)
        b[0]['values'][1] = (shared+'x')[:-1]
        self.assertEqual(a, b)
        self.assertNotEqual(pickle.dumps(a), pickle.dumps(b))
        self.assertTrue(compare(a, b)['qualified'])
        for field in ('response_token', 'action_token', 'frozen_context_token'):
            changed = copy.deepcopy(b); changed[0][field] = 'changed'
            self.assertFalse(compare(a, changed)['qualified'])
        b[0]['cost'] = -0.
        self.assertFalse(compare(a, b)['qualified'])

    def test_four_worker_action_bank_has_four_actual_vsl_variants_and_fixed_other_fields(self):
        from diagnostics.check_fixed_candidate_response import _parallel_qualification_actions
        from src.models.state import ControlAction
        vsl = {f'{direction}__seg{i}': 120. for direction in ('FW_E', 'FW_W') for i in range(21)}
        vsl.update(FW_E=120., FW_W=120.)
        control = ControlAction(vsl=vsl, ramp_metering={'R_D_W': 1800.}, N_P_star=450., N_UF_star=7200.,
                                diagnostics={'nested': [1, 2]})
        frozen = pickle.dumps(control)
        labels, actions = _parallel_qualification_actions(control, 4)
        self.assertEqual(labels, ('base', 'E100', 'W100', 'both100'))
        self.assertEqual(len({tuple(sorted(a.vsl.items())) for a in actions}), 4)
        self.assertEqual([(a.vsl['FW_E__seg10'], a.vsl['FW_W__seg10']) for a in actions],
                         [(120., 120.), (100., 120.), (120., 100.), (100., 100.)])
        for action in actions:
            self.assertEqual({k: v for k, v in vars(action).items() if k != 'vsl'},
                             {k: v for k, v in vars(control).items() if k != 'vsl'})
            self.assertEqual(action.vsl['FW_W__seg0'], 120.)
        actions[0].diagnostics['nested'].append(3)
        self.assertEqual(actions[1].diagnostics['nested'], [1, 2])
        self.assertEqual(pickle.dumps(control), frozen)

    def test_reverse_completion_preserves_request_order(self):
        ImmediateExecutor.reverse_pair = True
        q = self.parallel(workers=4)
        result = q((self.fixture.reference, NS(value=100., diagnostics={})))
        self.assertEqual(self.fixture.calls, [100., 120.])
        self.assertEqual([r['objective_veh_h'] for r in result['results']], [130., 110.])
        self.assertEqual(q.stats()['parallel_accepted'], 2)
        self.assertEqual(ImmediateExecutor.instances[0].max_workers, 4)

    def test_tampered_transport_context_or_action_fails_and_closes(self):
        for field in ('transport_token', 'local_context_after', 'action_token'):
            with self.subTest(field=field):
                ImmediateExecutor.alter = lambda row, field=field: row.__setitem__(field, 'tampered')
                q = self.parallel()
                with self.assertRaisesRegex(ValueError, 'proof'):
                    q((self.fixture.reference,))
                self.assertTrue(q.stats()['closed'])
                self.assertEqual(q.stats()['owned_workers_alive'], [])
                self.assertEqual(q.stats()['parallel_accepted'], 0)

    def test_child_local_identity_requires_all_proofs_before_parent_binding(self):
        def alternate_local_identity(row):
            value = 'a'*64
            row['local_context_before'] = row['local_context_after'] = value
            row['result']['frozen_context_token'] = value
        ImmediateExecutor.alter = alternate_local_identity
        serial, q = self.query(), self.parallel()
        expected = serial((self.fixture.reference,))['results']
        self.assertEqual(q((self.fixture.reference,))['results'], expected)
        proof = next(iter(q.stats()['worker_proofs'].values()))
        self.assertEqual(proof['local_context_token'], 'a'*64)
        self.assertNotEqual(proof['local_context_token'], proof['parent_context_token'])
        self.assertEqual(proof['transport_token'], q.stats()['parallel_transport_token'])

    def test_bootstrap_operand_mutation_fails_without_serial_retry(self):
        def change(adapter, cfg, *args):
            cfg.network.unrequested = True
            return {}
        with patch.object(runtime_setup, 'install_worker_runtime', change):
            q = self.parallel()
            with self.assertRaisesRegex(ValueError, 'bootstrap changed'):
                q((self.fixture.reference,))
        self.assertEqual(self.fixture.calls, [])
        self.assertEqual(q.stats()['parallel_failed_tasks_with_unknown_endpoint_count'], 1)
        self.assertEqual(q.stats()['owned_workers_alive'], [])

    def test_wrong_source_pin_fails_before_physics(self):
        path = str(Path(subject.__file__).resolve())
        q = self.parallel(worker_bootstrap={'state_json': {'network_path': path},
            'detector_mapping': {}, 'runtime_sources': {path: '0'*64}})
        with self.assertRaisesRegex(ValueError, 'source changed'):
            q((self.fixture.reference,))
        self.assertEqual(self.fixture.calls, [])
        self.assertTrue(q.stats()['closed'])

    def test_deadline_cancels_owned_worker_without_unbounded_wait(self):
        ImmediateExecutor.pending = True
        q = self.parallel(deadline_monotonic=perf_counter()+.05)
        start = perf_counter()
        with self.assertRaisesRegex(TimeoutError, 'parallel_response_wait'):
            q((self.fixture.reference,))
        self.assertLess(perf_counter()-start, .5)
        self.assertEqual(q.stats()['owned_workers_alive'], [])
        self.assertEqual(self.fixture.calls, [])
        self.assertEqual(ImmediateExecutor.instances[0].shutdowns, [(False, True)])
        with self.assertRaisesRegex(RuntimeError, 'closed'):
            q((self.fixture.reference,))

    def test_parallel_cache_off_keeps_full_values_and_repeats_work(self):
        serial, q = self.query(cache_enabled=False), self.parallel(cache_enabled=False)
        action = self.fixture.reference
        for _ in range(2):
            expected, actual = serial((action, action)), q((action, action))
            self.assertEqual(expected['results'], actual['results'])
            self.assertEqual(actual['cache_hits'], 1)
        self.assertEqual(q.stats()['endpoint_calls'], 2)
        self.assertEqual(q.stats()['retained_result_bytes'], 0)

    def test_parallel_off_remains_lazy_and_does_not_require_bootstrap(self):
        q = self.query(parallel_workers=0)
        q((self.fixture.reference,))
        q.close()
        self.assertEqual(ImmediateExecutor.instances, [])
        self.assertEqual(q.stats()['owned_worker_pids'], [])

    def test_parallel_options_fail_before_any_worker(self):
        for changes in ({'parallel_workers': True}, {'parallel_workers': 5},
                        {'parallel_workers': 1}, {'parallel_workers': 1, 'deadline_monotonic': -1.}):
            with self.assertRaises(ValueError):
                self.query(**changes)
        self.assertEqual(ImmediateExecutor.instances, [])


if __name__ == '__main__':
    unittest.main()
