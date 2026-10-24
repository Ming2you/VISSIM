"""Pure copy-contract regressions; no model endpoint or native VISSIM run."""
from __future__ import annotations

from collections import Counter, defaultdict
import copy
import pickle
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation.controllers import control_area_objective as area


class DictSubclass(dict):
    pass


class SlotLedger(area.ModelAreaLedger):
    __slots__ = ('extra_slot',)


class HookValue:
    def __init__(self, payload, calls):
        self.payload, self.calls = payload, calls

    def __deepcopy__(self, memo):
        self.calls.append('hook')
        result = type(self)(copy.deepcopy(self.payload, memo), self.calls)
        memo[id(self)] = result
        return result


class BrokenCopy:
    def __deepcopy__(self, memo):
        raise ValueError('fixture copy failure')


def fixture():
    ledger = area.ModelAreaLedger({'storage:x': {'inside': 8., 'outside': 2.}}, capture_response=True)
    ledger.begin_response_step('urban', 900., 905.)
    ledger.record_resource_allocation('receiving', 'x', 5., {'a': 2., 'b': 3.})
    ledger.record_state_upper_bound('queue', 'a', 2., 5.)
    ledger.complete_constraint_coverage('isolated', missing_constraints=['unobserved_gate'])
    ledger.residence(('storage:x',), 5./3600.)
    ledger.explicit_events['e'] = ('storage:x', 'outside', 2.)
    ledger.flow_counts['e'] = 2.
    return ledger


class ModelAreaLedgerCopyTests(unittest.TestCase):
    def test_packed_records_preserve_order_counts_values_and_snapshot_isolation(self):
        original = fixture()
        packed = copy.deepcopy(original)
        packed.pack_completed_response_records()
        snapshot = copy.deepcopy(packed)
        self.assertEqual(packed.response(), original.response())
        self.assertEqual(packed._response['resource_allocations'], [])
        for ledger in (original, packed):
            ledger.begin_response_step('urban', 905., 910.)
            ledger.record_resource_allocation('receiving', 'y', 2., {'c': 1.})
            ledger.record_state_upper_bound('queue', 'c', 1., 2.)
            ledger.transfer('storage:x', None, .5, inside_to_inside=0., outside_to_inside=0., event_id='later')
        packed.pack_completed_response_records()
        self.assertEqual(packed.response(), original.response())
        self.assertEqual(len(snapshot.response()['resource_allocations']), 1)
        self.assertEqual(packed.response()['model_constraint_coverage']['checked_allocation_count'], 2)
        exported = packed.response()
        exported['resource_allocations'][0]['accepted_by_source_veh']['a'] = 99.
        self.assertEqual(packed.response(), original.response())
        self.assertEqual(snapshot.response()['resource_allocations'][0]['accepted_by_source_veh']['a'], 2.)

    def test_full_ledger_matches_generic_deepcopy_bytes(self):
        original = fixture()
        with patch.object(area.ModelAreaLedger, '__deepcopy__', None):
            expected = copy.deepcopy(original)
        actual = copy.deepcopy(original)
        self.assertEqual(pickle.dumps(actual, protocol=5), pickle.dumps(expected, protocol=5))
        self.assertEqual(actual.response(), expected.response())
        self.assertIs(type(actual.flow_counts), Counter)
        self.assertIsNot(actual.stocks, original.stocks)
        self.assertIsNot(actual._response['resource_allocations'][0], original._response['resource_allocations'][0])
        actual._response['resource_allocations'][0]['accepted_by_source_veh']['a'] = 99.
        actual.stocks['storage:x']['inside'] = 99.
        self.assertEqual(original.stocks['storage:x']['inside'], 8.)
        self.assertEqual(original._response['resource_allocations'][0]['accepted_by_source_veh']['a'], 2.)

    def test_helper_opt_out_is_byte_identical(self):
        original = fixture()
        actual = copy.deepcopy(original)
        response = original.response()
        with patch.object(area, '_copy_response_tree', copy.deepcopy):
            expected = copy.deepcopy(original)
            legacy_response = original.response()
        self.assertEqual(pickle.dumps(actual, protocol=5), pickle.dumps(expected, protocol=5))
        self.assertEqual(pickle.dumps(response, protocol=5), pickle.dumps(legacy_response, protocol=5))

    def test_aliases_with_sibling_state_fields_in_both_traversal_orders(self):
        for ledger_first in (False, True):
            ledger = fixture()
            shared = {'nested': [1., 2.]}
            ledger._response['custom_shared'] = shared
            ledger.shared = shared
            envelope = {'ledger': ledger, 'sibling': shared} if ledger_first else {'sibling': shared, 'ledger': ledger}
            with patch.object(area.ModelAreaLedger, '__deepcopy__', None):
                expected = copy.deepcopy(envelope)
            result = copy.deepcopy(envelope)
            self.assertEqual(pickle.dumps(result, protocol=5), pickle.dumps(expected, protocol=5))
            self.assertIs(result['ledger'].shared, result['sibling'])
            self.assertIs(result['ledger']._response['custom_shared'], result['sibling'])
            self.assertIsNot(result['sibling'], shared)
            result['sibling']['nested'].append(3.)
            self.assertEqual(shared['nested'], [1., 2.])

    def test_cycles_through_ledger_list_dict_and_tuple_preserved(self):
        ledger = fixture()
        repeated = []
        wrapped = (repeated,)
        repeated.append(wrapped)
        ledger._response['cycle'] = {'self': ledger, 'list': repeated, 'alias': repeated}
        with patch.object(area.ModelAreaLedger, '__deepcopy__', None):
            expected = copy.deepcopy(ledger)
        result = copy.deepcopy(ledger)
        self.assertEqual(pickle.dumps(result, protocol=5), pickle.dumps(expected, protocol=5))
        row = result._response['cycle']
        self.assertIs(row['self'], result)
        self.assertIs(row['list'], row['alias'])
        self.assertIs(row['list'][0][0], row['list'])

    def test_response_rows_independent_between_calls_and_original(self):
        ledger = fixture()
        first, second = ledger.response(), ledger.response()
        first['residence'][0]['model_stock_veh']['storage:x'] = 999.
        first['constraint_coverage'][0]['missing_constraints'].append('new')
        self.assertEqual(second['residence'][0]['model_stock_veh']['storage:x'], 10.)
        self.assertEqual(ledger.response(), second)
        self.assertEqual(second['model_constraint_coverage']['missing_constraints'], ['unobserved_gate'])
        self.assertFalse(first['conditional_model_feasibility_witness'])

    def test_custom_values_and_container_subclasses_use_normal_hooks(self):
        calls = []
        shared = [1.]
        hooked = HookValue(shared, calls)
        value = {'hook': hooked, 'again': hooked, 'shared': shared,
                 'subclass': DictSubclass(x=[2.]), 'default': defaultdict(list, x=[3.])}
        result = area._copy_response_tree(value)
        self.assertEqual(calls, ['hook'])
        self.assertIs(result['hook'], result['again'])
        self.assertIs(result['hook'].payload, result['shared'])
        self.assertIs(type(result['subclass']), DictSubclass)
        self.assertIs(type(result['default']), defaultdict)
        self.assertIs(result['default'].default_factory, list)
        result['subclass']['x'].append(4.)
        self.assertEqual(value['subclass']['x'], [2.])

    def test_provided_memo_is_respected_including_atomic_substitutions(self):
        value = {'stock': [1.], 'number': 12345.67}
        substitute, number = [8.], 765.43
        memo = {id(value['stock']): substitute, id(value['number']): number}
        result = area._copy_response_tree(value, memo)
        self.assertIs(result['stock'], substitute)
        self.assertIs(result['number'], number)
        self.assertIs(memo[id(value)], result)

    def test_subclass_slots_use_generic_reconstruction(self):
        ledger = SlotLedger({'x': {'inside': 1.}}, capture_response=True)
        shared = [2.]
        ledger.extra_slot = shared
        ledger.other = shared
        result = copy.deepcopy(ledger)
        self.assertIs(type(result), SlotLedger)
        self.assertIs(result.extra_slot, result.other)
        self.assertIsNot(result.extra_slot, shared)
        result.extra_slot.append(3.)
        self.assertEqual(shared, [2.])

    def test_custom_copy_failures_propagate_without_changing_source(self):
        ledger = fixture()
        ledger._response['custom'] = BrokenCopy()
        original_row = ledger._response['resource_allocations'][0]
        for operation in (ledger.response, ledger.clone):
            with self.assertRaisesRegex(ValueError, 'fixture copy failure'):
                operation()
            self.assertIs(ledger._response['resource_allocations'][0], original_row)
            self.assertEqual(original_row['accepted_total_veh'], 5.)

    def test_capture_disabled_and_failure_checks_unchanged(self):
        ledger = area.ModelAreaLedger({'x': {'inside': 1.}})
        cloned = ledger.clone()
        self.assertFalse(cloned.captures_response)
        with self.assertRaisesRegex(ValueError, 'not enabled'):
            cloned.response()
        active = fixture()
        before = pickle.dumps(active, protocol=5)
        with self.assertRaisesRegex(ValueError, 'exceeds shared'):
            active.record_resource_allocation('receiving', 'x', 1., {'a': 2.})
        self.assertEqual(pickle.dumps(active, protocol=5), before)


if __name__ == '__main__':
    unittest.main()
