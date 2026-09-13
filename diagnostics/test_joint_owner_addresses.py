"""Canonical owner-address tests; no traffic simulation or solver execution.

Uses the real ControlAction and writer DSD helper;
cfg is an explicitly scoped address fixture, not a built model/rollout.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers import joint_owner_game as proposed
from evaluation.controllers.vissim_stackelberg_adapter import _segment_dsd_controls
from src.models.state import ControlAction


class OwnerAddressesTests(unittest.TestCase):
    def test_canonical_catalog_and_core_compatibility_identity(self):
        from diagnostics import joint_owner_addresses_candidate as catalog_alias
        from diagnostics import joint_owner_game_candidate as core_alias
        for name in ('Address', 'Ownership', 'build_ownership',
                     'validate_action_addresses', 'assert_owner_transition'):
            self.assertIs(getattr(catalog_alias, name), getattr(proposed, name))
            self.assertEqual(getattr(proposed, name).__module__, proposed.__name__)
        for name in ('Neighborhood', 'Evaluation', 'solve'):
            self.assertIs(getattr(core_alias, name), getattr(proposed, name))
            self.assertEqual(getattr(proposed, name).__module__, proposed.__name__)

    def setUp(self):
        self.mapping = json.loads((ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json').read_text(encoding='utf-8-sig'))
        self.plan = json.loads((ROOT / 'outputs/signal_group_actuation_plan_mainline_20260825.json').read_text(encoding='utf-8-sig'))
        nodes = {r['id']: self.plan['controllers'][str(r['sc_no'])] for r in self.mapping['signals']}
        live = {s: tuple(p for p in proposed.PHASES if n['phase_signal_groups'][p] and n['axis_green_sec'][p] > 0) for s, n in nodes.items()}
        self.cfg = SimpleNamespace(network=SimpleNamespace(
            signals=tuple(nodes), freeway_links=('FW_E', 'FW_W'),
            signal_live_phases=lambda s: live[s],
            signal_actuation_contract={'nodes': copy.deepcopy(nodes)},
            freeway_vsl_zone_heads={d: [0, 5, 10, 15] for d in ('FW_E', 'FW_W')},
            freeway_vsl_zone_head_of_cell={d: [5 * min(i // 5, 3) for i in range(21)] for d in ('FW_E', 'FW_W')},
            freeway_vsl_zone_free=[0, 1, 2],
            ramp_to_freeway={m['model_ramp_key']: m['to_model_link'] for m in self.mapping['ramp_meters']},
        ))

    def build(self):
        return proposed.build_ownership(self.cfg, self.mapping, self.plan, segment_dsd_controls=_segment_dsd_controls)

    def action(self, catalog):
        values = {f: {} for f in proposed.LEVER_FIELDS}
        for a in catalog.addresses:
            value = 0.0 if a.role == 'fixed_dead' or a.field == 'offsets' else (120.0 if a.field == 'vsl' else 30.0)
            values[a.field][a.key] = value
        return ControlAction(**values)

    def test_actual_mapping_counts_and_no_mutation(self):
        before = copy.deepcopy((self.mapping, self.plan, vars(self.cfg.network)))
        c = self.build()
        self.assertEqual(len(c.owners), 19)
        self.assertEqual(sum(a.field == 'green_times' for a in c.addresses), 68)
        self.assertEqual(sum(a.field == 'vsl' and a.role == 'strategy' for a in c.addresses), 6)
        self.assertEqual(sum(w[0] == 'dsd' for w in c.writes), 66)
        self.assertEqual(sum(w[0] == 'signal_sg' for w in c.writes), 130)
        self.assertEqual(before, (self.mapping, self.plan, vars(self.cfg.network)))

    def test_eight_physical_meters_have_independent_owners_and_writes(self):
        net = self.cfg.network
        net.ramp_to_freeway = {m['id']:m['to_model_link'] for m in self.mapping['ramp_meters']}
        net.physical_ramp_branches = {'schema':'physical-ramp-branches/v1',
            'ramps':{m['id']:copy.deepcopy(m) for m in self.mapping['ramp_meters']}}
        c = self.build()
        self.assertEqual(len(c.owners),19)
        meters = [a for a in c.addresses if a.field == 'ramp_metering']
        self.assertEqual(len(meters),8)
        self.assertEqual(sum(a.owner=='FW_W' for a in meters),4)
        self.assertEqual(sum(a.owner=='FW_E' for a in meters),4)
        old = self.action(c); changed = old.copy()
        changed.ramp_metering['RM_C10644'] -= 1.
        self.assertEqual(proposed.assert_owner_transition(c,'FW_W',old,changed),
                         (('ramp_metering','RM_C10644'),))
        with self.assertRaises(ValueError):proposed.assert_owner_transition(c,'FW_E',old,changed)
        self.assertIn(('signal_sg','9104:1','FW_W','RM_C10644'),c.writes)
        self.assertIn(('signal_sg','9103:1','FW_W','RM_C10646'),c.writes)

    def test_active_headless_phase_retained_with_joint_offset(self):
        c = self.build(); old = self.action(c); new = old.copy()
        new.green_times['SC1_p4'] = 36.0
        new.offsets['SC1'] = 18.75
        self.assertEqual(set(proposed.assert_owner_transition(c, 'SC1', old, new)), {('green_times', 'SC1_p4'), ('offsets', 'SC1')})
        self.assertEqual(old.green_times['SC1_p4'], 30.0)

    def test_fw_joint_group_and_owned_derived_alias(self):
        c = self.build(); old = self.action(c); new = old.copy()
        new.vsl['FW_E__seg0'] = 100.0
        new.vsl['FW_E__seg1'] = 100.0
        new.ramp_metering['R_F_E'] = 40.0
        self.assertEqual(len(proposed.assert_owner_transition(c, 'FW_E', old, new)), 3)

    def test_non_owner_values_and_missing_addresses_rejected(self):
        c = self.build(); old = self.action(c)
        for field, key in (('offsets', 'SC5'), ('vsl', 'FW_W__seg0'), ('ramp_metering', 'R_F_E')):
            new = old.copy(); getattr(new, field)[key] += 1
            with self.subTest(field=field), self.assertRaises(ValueError):
                proposed.assert_owner_transition(c, 'SC1', old, new)
        new = old.copy(); del new.vsl['FW_W__seg20']
        with self.assertRaises(ValueError): proposed.assert_owner_transition(c, 'FW_E', old, new)

    def test_dead_and_recovery_are_fixed_even_for_owner(self):
        c = self.build(); old = self.action(c)
        for owner, field, key in (('SC7', 'green_times', 'SC7_p3'), ('FW_E', 'vsl', 'FW_E__seg15'), ('FW_E', 'vsl', 'FW_E__seg20')):
            new = old.copy(); getattr(new, field)[key] += 1
            with self.subTest(key=key), self.assertRaises(ValueError): proposed.assert_owner_transition(c, owner, old, new)

    def test_duplicate_dsd_and_unmapped_free_zone_rejected(self):
        original = copy.deepcopy(self.mapping)
        first = _segment_dsd_controls(self.mapping['segments'][0])[0]
        self.mapping['segments'][1].setdefault('extra_dsd_controls', []).append(copy.deepcopy(first))
        with self.assertRaises(ValueError): self.build()
        self.mapping = original
        for row in self.mapping['segments']:
            if row['model_link'] == 'FW_E' and row['model_segment_index'] < 5:
                row['dsd_by_lane'] = {}; row['extra_dsd_controls'] = []
        with self.assertRaises(ValueError): self.build()

    def test_urban_meter_overlap_and_unknown_ramp_rejected(self):
        self.mapping['ramp_meters'][0]['sc_no'] = 1
        with self.assertRaises(ValueError): self.build()
        self.mapping['ramp_meters'][0]['sc_no'] = 9101
        self.mapping['ramp_meters'][0]['model_ramp_key'] = 'invented'
        with self.assertRaises(ValueError): self.build()

    def test_plan_live_and_zone_tampering_rejected(self):
        self.plan['controllers']['1']['axis_green_sec']['p4'] = 0.0
        with self.assertRaises(ValueError): self.build()
        self.plan['controllers']['1']['axis_green_sec']['p4'] = 1.0
        # A changed nonzero plan still differs from the configured plan proof.
        with self.assertRaises(ValueError): self.build()
        self.plan['controllers']['1'] = copy.deepcopy(self.cfg.network.signal_actuation_contract['nodes']['SC1'])
        self.cfg.network.freeway_vsl_zone_head_of_cell['FW_E'][1] = 5
        with self.assertRaises(ValueError): self.build()

    def test_meter_writer_sg1_and_unique_sc_required(self):
        self.mapping['ramp_meters'][0]['sg_no'] = 2
        with self.assertRaisesRegex(ValueError, 'sg_no == 1'): self.build()
        self.mapping['ramp_meters'][0]['sg_no'] = 1
        self.mapping['ramp_meters'][1]['sc_no'] = self.mapping['ramp_meters'][0]['sc_no']
        with self.assertRaisesRegex(ValueError, 'controller must be unique'): self.build()

    def test_unknown_nonfinite_bool_and_type_changes_rejected(self):
        c = self.build(); old = self.action(c)
        for value in (float('nan'), float('inf'), True):
            new = old.copy(); new.offsets['SC1'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): proposed.assert_owner_transition(c, 'SC1', old, new)
        new = old.copy(); new.vsl['FW_E__seg42'] = 100.0
        with self.assertRaises(ValueError): proposed.assert_owner_transition(c, 'FW_E', old, new)
        new = old.copy(); new.offsets['SC5'] = 0
        with self.assertRaises(ValueError): proposed.assert_owner_transition(c, 'SC1', old, new)


if __name__ == '__main__':
    unittest.main()
