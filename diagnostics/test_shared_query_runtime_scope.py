"""Exact runtime restoration regressions; no physical endpoint or native calls."""
from contextlib import contextmanager
import pickle
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import area_follower_objective as subject
from evaluation.controllers import vissim_stackelberg_adapter as adapter


def selected_runtime():
    return {key: value for key, value in vars(adapter).items()
            if key.startswith('_') and key.isupper() and isinstance(value, (dict, list, set))}


@contextmanager
def installed(runtime):
    original = selected_runtime()
    for key in original:
        delattr(adapter, key)
    for key, value in runtime.items():
        setattr(adapter, key, value)
    try:
        yield
    finally:
        for key in tuple(selected_runtime()):
            delattr(adapter, key)
        for key, value in original.items():
            setattr(adapter, key, value)


class NonSerializableFollower:
    def __reduce_ex__(self, protocol):
        raise AssertionError('Scope must not serialize or copy the installed follower')


class SharedQueryRuntimeScopeTests(unittest.TestCase):
    def assert_frozen(self, context, before):
        self.assertEqual(pickle.dumps((context, selected_runtime()), protocol=5), before)

    def test_noop_nested_keyword_set_keeps_original_object_and_encoding(self):
        keywords = {'runtime_keyword_' + str(i) for i in range(31)}
        temporary = {'temporary_' + str(i) for i in range(4096)}
        keywords.update(temporary)
        for value in temporary:
            keywords.remove(value)
        cache = {'d': keywords, 'source': 'fixture'}
        with installed({'_MIDBLOCK_CACHE': cache}):
            before = pickle.dumps(({}, selected_runtime()), protocol=5)
            for _ in range(3):
                with subject.shared_query_runtime_scope():
                    pass
                self.assertIs(adapter._MIDBLOCK_CACHE, cache)
                self.assertIs(cache['d'], keywords)
                self.assert_frozen({}, before)

    def test_noop_preserves_context_aliases_through_dict_and_list_roots(self):
        row = {'v_free': 120., 'rho_crit': 27.}
        context = {'cfg': {'row': row}}
        segment, rows = {'p': row, 'armed': False}, [row, 'tail']
        with installed({'_FW_SEG_CTX': segment, '_ROWS': rows}):
            before = pickle.dumps((context, selected_runtime()), protocol=5)
            with subject.shared_query_runtime_scope():
                pass
            self.assertIs(segment['p'], row)
            self.assertIs(rows[0], row)
            self.assertIs(adapter._FW_SEG_CTX, segment)
            self.assertIs(adapter._ROWS, rows)
            self.assert_frozen(context, before)

    def test_replaced_equal_child_restores_original_alias_and_root_order(self):
        row = {'v_free': 120., 'rho_crit': 27.}
        context = {'cfg': row}
        segment = {'p': row, 'armed': False, 'phi': .75}
        with installed({'_FW_SEG_CTX': segment}):
            before = pickle.dumps((context, selected_runtime()), protocol=5)
            with subject.shared_query_runtime_scope():
                # Root serialization alone cannot detect this lost external alias.
                original_root_bytes = pickle.dumps(segment, protocol=5)
                segment['p'] = dict(row)
                self.assertEqual(pickle.dumps(segment, protocol=5), original_root_bytes)
                segment['armed'] = True
                segment.pop('phi')
                segment['temporary'] = 7
            self.assertIs(segment['p'], row)
            self.assertEqual(list(segment), ['p', 'armed', 'phi'])
            self.assert_frozen(context, before)

    def test_changed_list_and_rebound_root_restore_original_children(self):
        row = {'v_free': 120.}
        rows = [row, 'tail']
        context = {'cfg': row}
        with installed({'_ROWS': rows}):
            before = pickle.dumps((context, selected_runtime()), protocol=5)
            with subject.shared_query_runtime_scope():
                rows[:] = ['temporary', dict(row), 3]
                adapter._ROWS = [999]
                adapter._CREATED_DURING_QUERY = {'value': 1}
            self.assertIs(adapter._ROWS, rows)
            self.assertIs(rows[0], row)
            self.assertNotIn('_CREATED_DURING_QUERY', selected_runtime())
            self.assert_frozen(context, before)

    def test_physical_child_mutation_is_not_rolled_back_or_hidden_from_guard(self):
        for use_list in (False, True):
            with self.subTest(use_list=use_list):
                row = {'v_free': 120.}
                context = {'cfg': row}
                root = [row] if use_list else {'p': row}
                with installed({'_PROBE': root}):
                    fingerprint = subject.joint_context_fingerprint(adapter)
                    fingerprint(context)
                    with subject.shared_query_runtime_scope():
                        row['v_free'] = 80.
                    restored = root[0] if use_list else root['p']
                    self.assertIs(context['cfg'], row)
                    self.assertEqual(row, {'v_free': 80.})
                    self.assertEqual(restored, {'v_free': 120.})
                    self.assertIsNot(restored, row)
                    with self.assertRaises(subject.FrozenJointContextError):
                        fingerprint(context)

    def test_changed_runtime_child_restores_snapshot_and_shared_children(self):
        child = {'values': [1, 2]}
        root = {'left': child, 'right': child}
        with installed({'_PROBE': root}):
            before = pickle.dumps(({}, selected_runtime()), protocol=5)
            with subject.shared_query_runtime_scope():
                child['values'].append(3)
            self.assertEqual(child['values'], [1, 2, 3])
            self.assertEqual(root['left'], {'values': [1, 2]})
            self.assertIs(root['left'], root['right'])
            self.assert_frozen({}, before)

    def test_bound_follower_and_scalar_children_require_no_pickle_or_copy(self):
        follower = NonSerializableFollower()
        binding = {'ref': follower}
        scalars = {'none': None, 'bool': True, 'int': 2, 'float': 3.5,
                   'complex': 1+2j, 'str': 'value', 'bytes': b'value'}
        with installed({'_PHASE_VECTOR_FOLLOWER': binding, '_SCALARS': scalars}), \
             patch.object(pickle, 'dumps', side_effect=AssertionError('Unexpected child pickle')):
            with subject.shared_query_runtime_scope():
                binding['ref'] = NS(cfg='temporary')
                scalars['temporary'] = 99
            self.assertIs(binding['ref'], follower)
            self.assertNotIn('temporary', scalars)

    def test_bound_follower_physical_mutation_remains_visible_to_guard(self):
        follower = NS(cfg={'v_free': 120.})
        with installed({'_PHASE_VECTOR_FOLLOWER': {'ref': follower}}):
            context = {'follower': follower}
            fingerprint = subject.joint_context_fingerprint(adapter)
            fingerprint(context)
            with subject.shared_query_runtime_scope():
                follower.cfg['v_free'] = 80.
            self.assertIs(adapter._PHASE_VECTOR_FOLLOWER['ref'], follower)
            self.assertEqual(follower.cfg['v_free'], 80.)
            with self.assertRaises(subject.FrozenJointContextError):
                fingerprint(context)

    def test_exception_cleanup_preserves_alias_and_original_error(self):
        row = {'v_free': 120.}
        segment = {'p': row, 'armed': False}
        context = {'cfg': row}
        with installed({'_FW_SEG_CTX': segment}):
            before = pickle.dumps((context, selected_runtime()), protocol=5)
            with self.assertRaisesRegex(RuntimeError, 'synthetic command failed'):
                with subject.shared_query_runtime_scope():
                    segment['armed'] = True
                    raise RuntimeError('synthetic command failed')
            self.assertIs(segment['p'], row)
            self.assert_frozen(context, before)

    def test_top_level_keyword_set_policy_is_unchanged(self):
        keywords = {'keyword_' + str(i) for i in range(31)}
        with installed({'_KEYWORDS': keywords}):
            before = pickle.dumps(keywords, protocol=5)
            with subject.shared_query_runtime_scope():
                pass
            self.assertIs(adapter._KEYWORDS, keywords)
            self.assertEqual(pickle.dumps(keywords, protocol=5), before)
            with subject.shared_query_runtime_scope():
                keywords.add('temporary')
            self.assertNotIn('temporary', keywords)


if __name__ == '__main__':
    unittest.main()
