"""Actual historical schedules held at a new state; no model or COM runs."""
from copy import deepcopy
import pickle
import unittest
from unittest.mock import patch

from diagnostics import test_historical_meter_anchor as fixture
from evaluation.controllers import area_meter_finalization as meters


class HeldActualMeterReferenceTests(unittest.TestCase):
    def setUp(self):
        source = fixture.RecordedHistoricalMeterContextTests()
        source.setUp()
        self.cfg = source.current
        self.historical = source.prepare()['previous']
        self.rows = deepcopy(self.historical.diagnostics[meters.HISTORICAL_REFERENCE]['written_meter_rows'])

    def test_current_demand_and_spill_do_not_change_eight_actual_commands(self):
        before = pickle.dumps((self.cfg, self.historical))
        with patch.object(fixture.adapter, 'apply_ramp_spillback_guard', side_effect=AssertionError('No new allocation')), \
             patch.object(fixture.adapter, 'real_world_ramp_meter_write_back', side_effect=AssertionError('No new allocation')):
            held = meters.prepare_held_actual_reference(self.historical, self.cfg)
            meters.finalize(held, self.cfg)
            prepared = meters.prepare_canonical_candidate(held, self.cfg,
                owned_ramps=tuple(held.ramp_metering), total_budget=None,
                directional_budgets={}, budget_tolerance_veh_h=1e-9)
        self.assertEqual(before, pickle.dumps((self.cfg, self.historical)))
        self.assertEqual(held.ramp_metering, self.historical.ramp_metering)
        self.assertEqual(held.ramp_metering['R_D_W'], 511.2)
        self.assertEqual(held.diagnostics['rw_meter_green_R_D_W_1'], 2.)
        self.assertNotIn(meters.HISTORICAL_REFERENCE, held.diagnostics)
        proof = held.diagnostics[meters.HELD_ACTUAL_REFERENCE]
        self.assertEqual(proof['verified_written_meter_rows'], self.rows)
        self.assertEqual(proof['historical_proof'], self.historical.diagnostics[meters.HISTORICAL_REFERENCE])
        self.assertTrue(proof['reference_only'])
        self.assertFalse(proof['new_command_applied'])
        self.assertEqual(vars(prepared), vars(held))
        self.assertEqual(meters.assert_writer(held, self.cfg, require_scored=True)
                         ['control_area_meter_new_command_applied'], 0.)
        with self.assertRaisesRegex(ValueError, 'Historical meter reference'):
            meters.finalize(self.historical, self.cfg)

    def test_changed_candidate_uses_current_allocation_and_invalidates_held_proof(self):
        held = meters.prepare_held_actual_reference(self.historical, self.cfg)
        frozen = pickle.dumps(held)
        candidate = deepcopy(held)
        candidate.ramp_metering['R_D_W'] += 20.
        with self.assertRaisesRegex(ValueError, 'changed or unfinalized'):
            meters.assert_writer(candidate, self.cfg, require_scored=True)
        ordinary = deepcopy(candidate)
        ordinary.diagnostics = {k: v for k, v in ordinary.diagnostics.items()
            if not k.startswith('rw_meter_') and k not in (meters.MARKER, meters.HELD_ACTUAL_REFERENCE)}
        meters.finalize(ordinary, self.cfg)
        original = fixture.adapter.real_world_ramp_meter_write_back
        with patch.object(fixture.adapter, 'real_world_ramp_meter_write_back', wraps=original) as allocation:
            meters.finalize(candidate, self.cfg)
        allocation.assert_called_once()
        self.assertNotIn(meters.HELD_ACTUAL_REFERENCE, candidate.diagnostics)
        self.assertEqual(candidate.ramp_metering, ordinary.ramp_metering)
        self.assertEqual(candidate.diagnostics[meters.MARKER], ordinary.diagnostics[meters.MARKER])
        self.assertEqual(candidate.diagnostics['rw_meter_green_R_D_W_1'], 10.)
        self.assertEqual(frozen, pickle.dumps(held))

    def test_physical_definition_changes_fail_without_mutation(self):
        for kind in ('mapping', 'capacity', 'actuation', 'future'):
            cfg = deepcopy(self.cfg)
            context = cfg.network.control_area_meter_context
            if kind == 'mapping': context['mapping']['ramp_meters'][0]['sc_no'] += 1
            elif kind == 'capacity': cfg.network.ramp_capacity_veh_h['R_D_W'] += 1.
            elif kind == 'actuation': context['actuation']['real_world_ramp_metering']['cycle_sec'] += 1.
            else: context['sim_sec'] = 749.
            before = pickle.dumps((cfg, self.historical))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                meters.prepare_held_actual_reference(self.historical, cfg)
            self.assertEqual(before, pickle.dumps((cfg, self.historical)))

    def test_writer_schedule_mismatch_is_rejected_even_if_source_proof_is_rehashed(self):
        bad = deepcopy(self.historical)
        proof = bad.diagnostics[meters.HISTORICAL_REFERENCE]
        bad.diagnostics['rw_meter_green_R_D_W_1'] = 3.
        proof['commands']['rw_meter_green_R_D_W_1'] = 3.
        proof['proof_sha256'] = meters._hash({k: v for k, v in proof.items() if k != 'proof_sha256'})
        meters.historical_meter_anchor_rates(bad)
        with self.assertRaisesRegex(ValueError, 'eight historical commands'):
            meters.prepare_held_actual_reference(bad, self.cfg)

    def test_held_marker_proof_tampering_and_later_context_invalidate(self):
        held = meters.prepare_held_actual_reference(self.historical, self.cfg)
        for kind in ('proof', 'marker', 'commands'):
            bad = deepcopy(held)
            if kind == 'proof': bad.diagnostics[meters.HELD_ACTUAL_REFERENCE]['new_command_applied'] = True
            elif kind == 'marker': bad.diagnostics[meters.MARKER].pop('held_actual_reference_sha256')
            else: bad.diagnostics['rw_meter_green_R_D_W_1'] = 3.
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'changed or unfinalized'):
                meters.assert_writer(bad, self.cfg, require_scored=True)
        cfg = deepcopy(self.cfg)
        cfg.network.control_area_meter_context['sim_sec'] += 150.
        with self.assertRaisesRegex(ValueError, 'changed or unfinalized'):
            meters.assert_writer(held, cfg, require_scored=True)
        changed = deepcopy(held)
        meters.finalize(changed, cfg)
        self.assertNotIn(meters.HELD_ACTUAL_REFERENCE, changed.diagnostics)
        meters.assert_writer(changed, cfg, require_scored=True)


if __name__ == '__main__':
    unittest.main()
