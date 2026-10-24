"""Exact typed-key encoding checks; no model, candidate rollout or native run."""
import hashlib
import json
import math
import pickle
from collections import UserDict
from collections.abc import Mapping
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import joint_owner_neighbors as subject


def original_typed(value):
    # Previous production expression, including default escaped JSON sort keys.
    if value is None or type(value) in (str, bool, int): return value
    if type(value) is float:
        if not math.isfinite(value): raise ValueError('Expected finite builtin number')
        return {'float_hex': value.hex()}
    if isinstance(value, Mapping):
        pairs = [[original_typed(k), original_typed(v)] for k, v in value.items()]
        return {'mapping': sorted(pairs, key=lambda x: json.dumps(x[0], sort_keys=True))}
    if isinstance(value, (tuple, list)):
        return {type(value).__name__: [original_typed(v) for v in value]}
    raise ValueError('Unsupported command evidence value')


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


class TypedKeyTests(unittest.TestCase):
    def setUp(self):
        subject._primitive_mapping_key_json.cache_clear()

    def assert_original(self, value):
        expected = canonical_bytes(original_typed(value))
        self.assertEqual(canonical_bytes(subject._typed(value)), expected)
        self.assertEqual(subject._key(value), hashlib.sha256(expected).hexdigest())

    def test_nested_types_unicode_and_escaped_sort_order_are_exact(self):
        value = {'z': [True, 1, 1., -0., None, ('p1', 'p2')],
                 '한글': {'\n': 1, '"': 2, '\\': 3, 'é': 4, '😀': 5},
                 2: {'offset': -0., 'meter': 1800.}, None: 'none',
                 ('FW_E', 1, False, -0.): {'phase': 'p1'}, 2.5: 'float'}
        self.assert_original(value)
        self.assert_original(value)  # Warm-cache result remains byte exact.
        keys = ['z', 'é', '한글', '😀', '\n', '"', '\\']
        encoded_order = sorted(keys, key=lambda k: json.dumps(k, sort_keys=True))
        self.assertEqual([p[0] for p in subject._typed(dict.fromkeys(keys, 1))['mapping']], encoded_order)

    def test_primitive_tags_prevent_bool_int_aliases(self):
        values = [True, 1, False, 0, None, '1', 'true', -1, 2**100]
        for value in values * 2:
            self.assertEqual(subject._mapping_key_json(value), json.dumps(value, sort_keys=True))
            self.assert_original({value: 'x'})
        info = subject._primitive_mapping_key_json.cache_info()
        self.assertEqual(info.currsize, len(values))
        self.assertGreater(info.hits, 0)
        self.assertNotEqual(subject._key({True: 1}), subject._key({1: 1}))
        self.assertNotEqual(subject._key({1.: 1}), subject._key({1: 1}))

    def test_composite_and_large_keys_use_original_fallback(self):
        typed_keys = [original_typed(1.5), original_typed(('SC1', 1, True)),
                      'x' * 257, 2**129, -(2**129)]
        for key in typed_keys * 2:
            self.assertEqual(subject._mapping_key_json(key), json.dumps(key, sort_keys=True))
        self.assertEqual(subject._primitive_mapping_key_json.cache_info().currsize, 0)
        self.assert_original({('SC1', 1, True): [1., 1, True], 1.5: 'x', 'x'*257: 2**129})

    def test_insertion_order_and_mutated_values_are_not_cached(self):
        items = [('SC1', {'green': 30.}), ('é', [1, 2]), ('z', None)]
        for order in (items, list(reversed(items)), items[1:] + items[:1]):
            self.assert_original(dict(order))
        value = dict(items); before = subject._key(value)
        value['SC1']['green'] = 36.
        self.assert_original(value)
        self.assertNotEqual(subject._key(value), before)

    def test_invalid_values_and_keys_preserve_exception_class_and_message(self):
        class CustomInt(int): pass
        class CustomString(str): pass
        bad = [float('nan'), float('inf'), -float('inf'), object(), {1, 2},
               {('SC1', float('nan')): 1}, {CustomInt(3): 1},
               {CustomString('SC1'): 1}, {'SC1': object()}]
        self.assert_original({'SC1': 1})  # A cached valid key cannot hide bad values.
        for value in bad:
            with self.subTest(value_type=type(value).__name__):
                errors = []
                for encoder in (original_typed, subject._typed):
                    try: encoder(value)
                    except Exception as exc: errors.append((type(exc), str(exc)))
                    else: self.fail('Unsupported input was accepted')
                self.assertEqual(errors[0], errors[1])

    def test_entry_and_primitive_size_bounds_do_not_change_output(self):
        for index in range(2200):
            value = 'key_' + str(index)
            self.assertEqual(subject._mapping_key_json(value), json.dumps(value, sort_keys=True))
        info = subject._primitive_mapping_key_json.cache_info()
        self.assertEqual((info.maxsize, info.currsize), (2048, 2048))
        for value in ('key_0', '한'*256, '한'*257, 2**127, 2**128):
            self.assertEqual(subject._mapping_key_json(value), json.dumps(value, sort_keys=True))


class BuiltinBindingSnapshotTests(unittest.TestCase):
    def test_serialized_guard_preserves_types_float_bits_and_nested_mutation_checks(self):
        source = {'x': [True, 1, 1., -0., ('a', '한글')]}
        frozen = pickle.dumps(source, protocol=5)
        self.assertTrue(subject._matches_builtin_serialization(source, frozen))
        for index, value in ((0, 1), (1, True), (2, 1), (3, 0.), (4, ['a', '한글'])):
            original = source['x'][index]
            source['x'][index] = value
            self.assertFalse(subject._matches_builtin_serialization(source, frozen))
            source['x'][index] = original
        self.assertFalse(subject._matches_builtin_serialization(source, None))

    def test_serialized_guard_reordering_and_alias_change_use_original_hash(self):
        shared = [2.]
        source = {'a': shared, 'b': shared}
        frozen = pickle.dumps(source, protocol=5)
        for changed in ({'b': shared, 'a': shared}, {'a': [2.], 'b': [2.]}):
            self.assertFalse(subject._matches_builtin_serialization(changed, frozen))
            self.assertEqual(subject._key(changed), subject._key(source))

    def test_custom_reduction_cannot_mimic_builtin_encoding(self):
        class PretendList(list):
            def __reduce_ex__(self, protocol):
                return list, ([1.],)
        class CannotPickle(list):
            def __reduce_ex__(self, protocol):
                raise RuntimeError('custom reducer')
        frozen = pickle.dumps({'a': [1.]}, protocol=5)
        for value in (PretendList([1.]), CannotPickle([1.])):
            self.assertFalse(subject._matches_builtin_serialization({'a': value}, frozen))

    def test_snapshot_is_independent_and_matches_exact_types_and_float_bits(self):
        source = {'x': [None, True, 1, 1., -0., '한글'], ('tuple', 1): {'v': 2.}}
        snapshot = subject._snapshot_builtin_tree(source)
        self.assertIsNotNone(snapshot)
        self.assertTrue(subject._matches_builtin_snapshot(source, snapshot))
        for index, changed in ((1, 1), (2, True), (3, 1), (4, 0.), (5, '다름')):
            original = source['x'][index]
            source['x'][index] = changed
            self.assertFalse(subject._matches_builtin_snapshot(source, snapshot))
            source['x'][index] = original
        source[('tuple', 1)]['v'] = 3.
        self.assertFalse(subject._matches_builtin_snapshot(source, snapshot))
        source[('tuple', 1)]['v'] = 2.
        self.assertTrue(subject._matches_builtin_snapshot(source, snapshot))
        source['x'].append(0)
        self.assertFalse(subject._matches_builtin_snapshot(source, snapshot))
        source['x'].pop()
        source['x'] = tuple(source['x'])
        self.assertFalse(subject._matches_builtin_snapshot(source, snapshot))

    def test_reordered_dict_uses_original_hash_acceptance(self):
        source = {'one': [1., True], 'two': {'a': 1, 'b': 2}}
        snapshot = subject._snapshot_builtin_tree(source)
        original_sha = subject._key(source)
        reordered = {'two': {'b': 2, 'a': 1}, 'one': [1., True]}
        self.assertFalse(subject._matches_builtin_snapshot(reordered, snapshot))
        self.assertEqual(subject._key(reordered), original_sha)
        reordered['two']['a'] = 3
        self.assertFalse(subject._matches_builtin_snapshot(reordered, snapshot))
        self.assertNotEqual(subject._key(reordered), original_sha)

    def test_custom_trees_do_not_call_custom_copy_or_equality(self):
        class CustomMapping(UserDict):
            def __deepcopy__(self, memo): raise AssertionError('custom deepcopy')
            def __eq__(self, other): raise AssertionError('custom equality')
        class CustomList(list):
            def __deepcopy__(self, memo): raise AssertionError('custom deepcopy')
            def __eq__(self, other): raise AssertionError('custom equality')
        class CustomInt(int):
            def __eq__(self, other): raise AssertionError('custom equality')
        class CustomMeta(type):
            def __eq__(self, other): raise AssertionError('custom metaclass equality')
        class CustomObject(metaclass=CustomMeta): pass
        for custom in (CustomMapping({'x': 1}), CustomList([1]), CustomInt(1), CustomObject()):
            self.assertIsNone(subject._snapshot_builtin_tree({'nested': custom}))
            self.assertFalse(subject._matches_builtin_snapshot(custom, subject._snapshot_builtin_tree(1)))
        custom = CustomMapping({'x': 1})
        self.assertEqual(subject._key(custom), subject._key({'x': 1}))
        custom['x'] = 2
        self.assertNotEqual(subject._key(custom), subject._key({'x': 1}))

    def test_nonfinite_and_unsupported_values_still_reach_original_error(self):
        snapshot = subject._snapshot_builtin_tree({'x': 1.})
        for changed in (float('nan'), float('inf'), -float('inf'), object(), {1}):
            value = {'x': changed}
            self.assertIsNone(subject._snapshot_builtin_tree(value))
            self.assertFalse(subject._matches_builtin_snapshot(value, snapshot))
            with self.assertRaises(ValueError): subject._key(value)


if __name__ == '__main__':
    unittest.main()
