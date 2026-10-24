"""Actual canonical row/writer binding on retained 213-row inputs; no rollout."""
import copy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import pickle
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from diagnostics.test_action_row_iterator import geometry, OUT
from evaluation.controllers import area_leader_objective as subject
from evaluation.controllers import action_csv_schema, vissim_stackelberg_adapter as adapter


def digest(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


class JointWrittenActionTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'RW_OFFSET_WRITER': 'experiment'})
        env.start(); self.addCleanup(env.stop)
        data_path = OUT / 'fixtures/writer_inputs.json'
        manifest = json.loads((OUT / 'fixtures/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(data_path.read_bytes()).hexdigest(), manifest['files_sha256']['writer_inputs.json'])
        data = json.loads(data_path.read_text(encoding='utf-8'))
        self.cfg = geometry(data)
        self.mapping, self.plan, self.actuation = copy.deepcopy((data['mapping'], data['plan'], data['actuation']))
        self.control = SimpleNamespace(**copy.deepcopy(data['actions']['000900']['control']))
        self.control.N_P_star = 340.
        self.control.N_UF_star = math.fsum(self.control.ramp_metering.values())
        self.control.inflow_outflow_allocation = {'synthetic_movement': 5.}
        self.control.vsl = {key: 80. for key in self.control.vsl}
        self.values = [80.] * len(self.mapping['segments'])
        self.meters = adapter.real_world_ramp_meter_actions(copy.deepcopy(self.control), self.cfg, self.actuation, self.mapping)
        self.metadata = copy.deepcopy(data['actions']['000900']['metadata'])
        self.metadata['controller_status'] = 'joint-selected'
        frozen = copy.deepcopy(self.control)
        owners = (*self.cfg.network.signals, 'FW_E', 'FW_W')
        tokens = {owner: digest(('synthetic scored physical token', owner)) for owner in owners}
        self.response = {'game': {'control': frozen}, 'final_action_token': digest(frozen),
            'final_score': {'action_token': digest(frozen), 'physical_owner_tokens': tokens},
            'command_evidence': {'ordered_rows': self.rows(metadata={}), 'owner_physical_sha256': tokens}}
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.json_path, self.csv_path = (Path(self.temp.name) / name for name in ('action.json', 'action.csv'))

    def rows(self, metadata=None):
        return tuple(adapter.iter_action_csv_rows(copy.deepcopy(self.control), self.cfg, self.mapping,
            self.values, self.meters, self.metadata if metadata is None else metadata,
            self.actuation, self.plan, 'experiment'))

    def test_validated_hold_uses_same_real_writer_binding_without_nash(self):
        self.response['schema'] = 'validated-decision-hold/v1'
        self.response['control'] = self.response.pop('game')['control']
        self.response.update(feasible=True, finite_neighborhood_certified=False,
            maximum_finite_candidate_gap=None, shared_tolerance=1e-7,
            directional_constraints={k:{'actual':3600.,'target':3600.,'tolerance':1e-7}
                for k in ('FW_W','FW_E')})
        self.response['final_score'].update(conditional_model_feasibility_witness=True,
            model_constraint_coverage={'complete':True,'conditional_model_feasibility_witness':True},
            resource_summary={'max_exceedance_veh':0.},quantity_constraints={'feasible':True})
        self.write()
        receipt = self.verify(post=True)
        self.assertTrue(receipt['written_command_binding_passed'])
        self.assertFalse(receipt['nash_result'])
        self.assertEqual(receipt['response_kind'],'validated_actual_hold')
        self.control.green_times[next(iter(self.control.green_times))] += 1.
        with self.assertRaisesRegex(ValueError,'seven action fields'):
            self.verify()

    def test_hold_cannot_hide_quantity_or_resource_failure(self):
        self.response['schema'] = 'validated-decision-hold/v1'
        self.response['control'] = self.response.pop('game')['control']
        self.response.update(feasible=True, finite_neighborhood_certified=False,
            maximum_finite_candidate_gap=None, shared_tolerance=1e-7,
            directional_constraints={k:{'actual':3600.,'target':3600.,'tolerance':1e-7}
                for k in ('FW_W','FW_E')})
        self.response['final_score'].update(conditional_model_feasibility_witness=True,
            model_constraint_coverage={'complete':True,'conditional_model_feasibility_witness':True},
            resource_summary={'max_exceedance_veh':0.},quantity_constraints={'feasible':False})
        with self.assertRaisesRegex(ValueError,'feasible model evidence'):
            self.verify()
        self.response['final_score']['quantity_constraints']['feasible']=True
        self.response['final_score']['resource_summary']['max_exceedance_veh']=1.
        with self.assertRaisesRegex(ValueError,'feasible model evidence'):
            self.verify()

    def test_physical_hold_has_total_only_gate_and_legacy_still_needs_directions(self):
        self.response['schema']='validated-decision-hold/v1'
        self.response['control']=self.response.pop('game')['control']
        self.response.update(feasible=True,finite_neighborhood_certified=False,
            maximum_finite_candidate_gap=None,shared_tolerance=1e-7,directional_constraints={})
        self.response['final_score'].update(conditional_model_feasibility_witness=True,
            model_constraint_coverage={'complete':True,'conditional_model_feasibility_witness':True},
            resource_summary={'max_exceedance_veh':0.},quantity_constraints={'feasible':True})
        with self.assertRaisesRegex(ValueError,'directional NUF'):
            self.verify()
        self.cfg.network.physical_ramp_branches={'test':'only hold gate; use retained physical CSV rows'}
        # This test isolates the final evidence gate. Actual eight-row writer is
        # checked by the physical writer suite and native command comparison.
        with patch.object(adapter,'iter_action_csv_rows',return_value=self.response['command_evidence']['ordered_rows']):
            result=self.verify()
        self.assertTrue(result['prewrite_binding_passed'])
        self.assertFalse(result['nash_result'])

    def verify(self, *, post=False, **kwargs):
        args = dict(signal_group_plan_table=self.plan, offset_writer='experiment')
        if post:
            args.update(action_json_path=self.json_path, action_csv_path=self.csv_path)
        args.update(kwargs)
        return subject.verify_joint_written_action(self.response, self.control, self.cfg, self.mapping,
            self.values, self.meters, self.metadata, self.actuation, **args)

    def write(self):
        self.json_path.write_text(json.dumps(adapter.control_to_json_dict(self.control, self.metadata)), encoding='utf-8')
        adapter.write_action_csv(self.csv_path, self.control, self.cfg, self.mapping,
            lambda *args: 80., self.metadata, self.actuation, self.plan, 'experiment')

    def change_csv(self, edit):
        with self.csv_path.open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream); rows = list(reader); fields = reader.fieldnames
        fields, rows = edit(fields, rows)
        with self.csv_path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

    def test_pre_and_actual_post_exact_213_rows_with_diagnostic_context_additions(self):
        before = pickle.dumps(self.response)
        self.control.diagnostics['_control_area_written_meter_context'] = {'sim_sec': 900., 'new': [1, 2]}
        control_before = pickle.dumps(self.control)
        pre = self.verify()
        self.assertEqual(pre['ordered_row_count'], 213)
        self.assertFalse(pre['written_command_binding_passed'])
        self.assertIsNone(pre['native_execution_passed'])
        self.write(); post = self.verify(post=True)
        self.assertTrue(post['written_command_binding_passed'])
        self.assertEqual(post['expected_csv_sha256'], post['action_csv']['sha256'])
        self.assertEqual(pre['ordered_physical_rows_sha256'], post['ordered_physical_rows_sha256'])
        self.assertEqual(post['native_execution_status'], 'pending')
        self.assertEqual(pickle.dumps(self.response), before)
        self.assertEqual(pickle.dumps(self.control), control_before)

    def test_no_second_VSL_callback_or_meter_allocation(self):
        with patch.object(adapter, 'real_world_ramp_meter_actions', side_effect=AssertionError('No allocation')), \
             patch.object(adapter, '_measured_meter_allocation', side_effect=AssertionError('No allocation')):
            self.verify()

    def test_each_scored_seven_field_is_fixed_before_write(self):
        original = copy.deepcopy(self.control)
        for field in ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation'):
            self.control = copy.deepcopy(original)
            value = getattr(self.control, field)
            if isinstance(value, dict): value[next(iter(value))] += 1.
            else: setattr(self.control, field, value + 1.)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'seven action fields'):
                self.verify()

    def test_changed_scored_token_or_physical_token_fails(self):
        self.response['game']['control'].diagnostics['after_score'] = 1
        with self.assertRaisesRegex(ValueError, 'token differs'): self.verify()
        self.response['game']['control'].diagnostics.pop('after_score')
        self.response['command_evidence']['owner_physical_sha256'] = dict.fromkeys(self.cfg.network.signals, 'wrong')
        with self.assertRaisesRegex(ValueError, 'physical owner tokens'): self.verify()

    def test_resolved_VSL_meter_and_evidence_physical_changes_reject(self):
        self.values[0] = 100.
        with self.assertRaisesRegex(ValueError, 'physical CSV'): self.verify()
        self.values[0] = 80.
        meter = next(iter(self.meters)); self.meters[meter]['green_sec'] -= 1.
        with self.assertRaisesRegex(ValueError, 'physical CSV'): self.verify()
        self.meters[meter]['green_sec'] += 1.
        rows = list(self.response['command_evidence']['ordered_rows']); rows.reverse()
        self.response['command_evidence']['ordered_rows'] = rows
        with self.assertRaisesRegex(ValueError, 'physical CSV'): self.verify()

    def test_every_JSON_field_is_checked_after_write_and_failure_preserves_files(self):
        self.write(); original = self.json_path.read_bytes(); csv_before = self.csv_path.read_bytes()
        for field in ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation'):
            payload = json.loads(original)
            if isinstance(payload[field], dict): payload[field][next(iter(payload[field]))] += 1.
            else: payload[field] += 1.
            self.json_path.write_text(json.dumps(payload), encoding='utf-8')
            bad = self.json_path.read_bytes()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Written JSON'):
                self.verify(post=True)
            self.assertEqual(self.json_path.read_bytes(), bad)
            self.assertEqual(self.csv_path.read_bytes(), csv_before)

    def test_header_order_missing_duplicate_nonfinite_unused_column_and_metadata(self):
        self.write(); original = self.csv_path.read_bytes()
        def cell(rows, kind, field, value):
            next(r for r in rows if r['kind'] == kind)[field] = value
            return rows
        cases = {
            'header': lambda f, r: (list(reversed(f)), r),
            'order': lambda f, r: (f, list(reversed(r))),
            'missing': lambda f, r: (f, r[:-1]),
            'duplicate': lambda f, r: (f, r + [r[-1]]),
            'nonfinite': lambda f, r: (f, cell(r, 'vsl', 'speed_kph', 'nan')),
            'unused': lambda f, r: (f, cell(r, 'signal_sg', 'p3_green', '1')),
            'metadata': lambda f, r: (f, cell(r, 'ramp_meter', 'metadata', 'tampered'))}
        for name, edit in cases.items():
            self.csv_path.write_bytes(original); self.change_csv(edit)
            before = self.csv_path.read_bytes()
            with self.subTest(case=name), self.assertRaises(ValueError): self.verify(post=True)
            self.assertEqual(self.csv_path.read_bytes(), before)

    def test_binary_serialization_and_incomplete_path_pair_reject(self):
        self.write(); self.csv_path.write_bytes(self.csv_path.read_bytes().replace(b'\r\n', b'\n'))
        with self.assertRaisesRegex(ValueError, 'binary serialization'): self.verify(post=True)
        with self.assertRaisesRegex(ValueError, 'both written'): self.verify(action_csv_path=self.csv_path)


if __name__ == '__main__':
    unittest.main()
