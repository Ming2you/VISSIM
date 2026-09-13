"""Historical meter proof tests using the actual allocator/writer, no rollout."""
import copy
import math
import pickle
import unittest
from unittest.mock import patch

from diagnostics.test_area_meter_finalization import CanonicalMeterCandidateTests, adapter
from evaluation.controllers import area_meter_finalization as module


class HistoricalMeterAnchorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = CanonicalMeterCandidateTests()
        self.cfg, self.original = self.fixture.fixture()
        context = self.cfg.network.control_area_meter_context
        context['sim_sec'] = 750.
        for meter in context['mapping']['ramp_meters'][:2]:
            context['raw']['local_observation']['far_measurement']['link_volume_veh_h'][str(meter['connector'])] = 1200.
        self.original.ramp_metering['R_D_W'] = 131.39246994163818
        module.finalize(self.original, self.cfg)
        self.rows = [{'kind': 'ramp_meter', 'id': mid, 'sc_no': str(int(row['sc_no'])),
                     'rate_vph': str(round(row['rate_vph'], 3)), 'green_sec': str(round(row['green_sec'], 3))}
                    for mid, row in self.fixture.rows(self.original, self.cfg).items()]
        self.provenance = {'fixture': 'synthetic recorded action and actual canonical meter rows',
                           'action': 'previous750', 'historical_context': 'explicit cfg750'}

    def prepare(self, **overrides):
        args = dict(written_meter_rows=self.rows, source_provenance=self.provenance)
        args.update(overrides)
        return module.prepare_historical_meter_reference(self.original, self.cfg, **args)

    def test_no_reallocation_partial_anchor_and_every_other_lever_exact(self):
        before = pickle.dumps((self.original, self.cfg, self.rows, self.provenance))
        with patch.object(module, 'finalize', side_effect=AssertionError('No historical reallocation')):
            result = self.prepare()
        previous = result['previous']
        self.assertEqual(previous.ramp_metering['R_D_W'], 511.2)
        self.assertEqual(previous.ramp_metering['R_F_W'], 1800.)
        self.assertEqual(module.historical_meter_anchor_rates(previous), self.original.ramp_metering)
        self.assertEqual(module.historical_meter_anchor_rates(previous, result['meter_anchor']), self.original.ramp_metering)
        for key, value in vars(self.original).items():
            if key not in ('ramp_metering', 'N_UF_star', 'diagnostics'):
                self.assertEqual(getattr(previous, key), value)
        restored_diag = copy.deepcopy(previous.diagnostics); restored_diag.pop(module.HISTORICAL_REFERENCE)
        self.assertEqual(restored_diag, self.original.diagnostics)
        self.assertEqual(before, pickle.dumps((self.original, self.cfg, self.rows, self.provenance)))

    def test_current_context_old_failure_and_reference_cannot_be_refinalized(self):
        current = copy.deepcopy(self.cfg)
        context = current.network.control_area_meter_context
        context['sim_sec'] = 900.
        context['raw']['local_observation']['far_measurement']['link_volume_veh_h'] = {
            key: 200. for key in context['raw']['local_observation']['far_measurement']['link_volume_veh_h']}
        wrong = module.prepare_canonical_candidate(self.original, current,
            owned_ramps=tuple(self.original.ramp_metering), total_budget=None,
            directional_budgets={}, budget_tolerance_veh_h=1e-9)
        self.assertEqual(wrong.ramp_metering['R_D_W'], 1800.)
        self.assertEqual(wrong.diagnostics['rw_meter_green_R_D_W_1'], 10.)
        self.assertEqual(self.original.diagnostics['rw_meter_green_R_D_W_1'], 2.)
        result = self.prepare(); before = pickle.dumps(result)
        for cfg in (self.cfg, current):
            with self.assertRaisesRegex(ValueError, 'Historical meter reference cannot be reallocated'):
                module.finalize(result['previous'], cfg)
        self.assertEqual(before, pickle.dumps(result))
        with self.assertRaisesRegex(ValueError, 'historical meter context'):
            module.prepare_historical_meter_reference(self.original, current,
                written_meter_rows=self.rows, source_provenance=self.provenance)

    def test_actual_warmup_zero_nuf_is_preserved_as_source_only(self):
        self.original.N_UF_star = 0.
        result = self.prepare()
        self.assertEqual(result['meter_anchor']['original_nuf_star'], 0.)
        self.assertEqual(result['previous'].N_UF_star,
            math.fsum(result['previous'].ramp_metering[r] for r in sorted(self.original.ramp_metering)))
        self.assertEqual(self.original.N_UF_star, 0.)

    def test_written_rows_missing_duplicate_reordered_or_changed_reject(self):
        for kind in ('missing', 'duplicate', 'order', 'green', 'rate', 'address', 'nan'):
            rows = copy.deepcopy(self.rows)
            if kind == 'missing': rows.pop()
            elif kind == 'duplicate': rows[-1] = copy.deepcopy(rows[0])
            elif kind == 'order': rows.reverse()
            elif kind == 'green': rows[0]['green_sec'] = '10'
            elif kind == 'rate': rows[0]['rate_vph'] = '900'
            elif kind == 'address': rows[0]['sc_no'] = '9101.5'
            else: rows[0]['rate_vph'] = 'nan'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.prepare(written_meter_rows=rows)

    def test_source_proof_marker_and_reference_mutation_reject(self):
        with self.assertRaisesRegex(ValueError, 'provenance required'):
            self.prepare(source_provenance={})
        for kind in ('rates', 'green', 'proof'):
            result = self.prepare(); previous = result['previous']
            if kind == 'rates': previous.ramp_metering['R_D_W'] += 1.
            elif kind == 'green': previous.diagnostics['rw_meter_green_R_D_W_1'] = 10.
            else: previous.diagnostics[module.HISTORICAL_REFERENCE]['final_writeback_rates']['R_D_W'] = 131.39246994163818
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'proof changed'):
                module.historical_meter_anchor_rates(previous)
        self.original.diagnostics['rw_meter_green_R_D_W_1'] = 10.
        with self.assertRaisesRegex(ValueError, 'historical meter context'):
            self.prepare()

    def test_serialized_reference_and_proof_retain_exact_anchor(self):
        result = pickle.loads(pickle.dumps(self.prepare()))
        self.assertEqual(module.historical_meter_anchor_rates(result['previous'], result['meter_anchor']),
                         self.original.ramp_metering)


class RecordedHistoricalMeterContextTests(unittest.TestCase):
    def setUp(self):
        fixture = HistoricalMeterAnchorTests()
        fixture.setUp()
        self.previous, self.rows = fixture.original, fixture.rows
        self.previous.diagnostics[module.WRITTEN_CONTEXT] = copy.deepcopy(
            fixture.cfg.network.control_area_meter_context)
        self.current = copy.deepcopy(fixture.cfg)
        context = self.current.network.control_area_meter_context
        context['sim_sec'] = 900.
        context['raw']['local_observation']['far_measurement']['link_volume_veh_h'] = {
            key: 200. for key in context['raw']['local_observation']['far_measurement']['link_volume_veh_h']}
        context['spillback']['R_D_W'] = 20.
        self.provenance = {
            'action_json': {'path': 'fixture/action_000750.json', 'sha256': 'a' * 64},
            'action_csv': {'path': 'fixture/action_000750.csv', 'sha256': 'b' * 64},
            'scope': 'Synthetic source receipt, actual physical writer rows'}

    def prepare(self, **overrides):
        args = dict(previous_sim_sec=750., written_meter_rows=self.rows,
                    source_provenance=self.provenance)
        args.update(overrides)
        return module.prepare_recorded_historical_meter_reference(self.previous, self.current, **args)

    def test_recorded_context_preserves_partial_without_reallocation(self):
        before = pickle.dumps((self.previous, self.current, self.rows, self.provenance))
        with patch.object(module, 'finalize', side_effect=AssertionError('No allocation')), \
             patch.object(adapter, 'apply_ramp_spillback_guard', side_effect=AssertionError('No spill guard')), \
             patch.object(adapter, 'real_world_ramp_meter_write_back', side_effect=AssertionError('No writeback')):
            result = self.prepare()
        self.assertEqual(result['previous'].ramp_metering['R_D_W'], 511.2)
        self.assertEqual(result['previous'].diagnostics['rw_meter_green_R_D_W_1'], 2.)
        self.assertEqual(result['previous'].ramp_metering['R_F_W'], 1800.)
        self.assertEqual(result['meter_anchor']['historical_context_sec'], 750.)
        self.assertEqual(module.historical_meter_anchor_rates(result['previous']), self.previous.ramp_metering)
        self.assertEqual(result['previous'].N_P_star, self.previous.N_P_star)
        self.assertEqual(result['previous'].N_UF_star, math.fsum(
            result['previous'].ramp_metering[r] for r in sorted(result['previous'].ramp_metering)))
        self.assertEqual(before, pickle.dumps((self.previous, self.current, self.rows, self.provenance)))

    def test_missing_changed_context_and_capacity_fail_without_mutation(self):
        for kind in ('missing', 'recorded_demand', 'current_actuation', 'current_mapping', 'capacity'):
            previous, current = copy.deepcopy(self.previous), copy.deepcopy(self.current)
            if kind == 'missing': del previous.diagnostics[module.WRITTEN_CONTEXT]
            elif kind == 'recorded_demand':
                previous.diagnostics[module.WRITTEN_CONTEXT]['raw']['local_observation']['far_measurement']['link_volume_veh_h']['1'] = 201.
            elif kind == 'current_actuation':
                current.network.control_area_meter_context['actuation']['real_world_ramp_metering']['cycle_sec'] = 11.
            elif kind == 'current_mapping':
                current.network.control_area_meter_context['mapping']['ramp_meters'][0]['sc_no'] = 9200
            else: current.network.ramp_capacity_veh_h['R_D_W'] = 1900.
            before = pickle.dumps((previous, current))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                module.prepare_recorded_historical_meter_reference(previous, current,
                    previous_sim_sec=750., written_meter_rows=self.rows, source_provenance=self.provenance)
            self.assertEqual(before, pickle.dumps((previous, current)))

    def test_previous_timestamp_and_strict_temporal_order(self):
        for sec in (749., 900., True, float('nan'), -1.):
            with self.subTest(previous=sec), self.assertRaises(ValueError):
                self.prepare(previous_sim_sec=sec)
        for sec in (750., 600., float('inf')):
            self.current.network.control_area_meter_context['sim_sec'] = sec
            with self.subTest(current=sec), self.assertRaises(ValueError):
                self.prepare()

    def test_exact_csv_and_provenance_are_still_required(self):
        rows = copy.deepcopy(self.rows); rows[0]['green_sec'] = '10'
        with self.assertRaisesRegex(ValueError, 'Actual written meter rows differ'):
            self.prepare(written_meter_rows=rows)
        for item in ({}, {'action_json': self.provenance['action_json']},
                     {**self.provenance, 'action_csv': {'path': 'old.csv', 'sha256': 'bad'}}):
            with self.subTest(provenance=item), self.assertRaisesRegex(ValueError, 'provenance required'):
                self.prepare(source_provenance=item)

    def test_historical_warmup_zero_nuf_is_not_a_replacement_leader_target(self):
        self.previous.N_UF_star = 0.
        result = self.prepare()
        self.assertEqual(result['meter_anchor']['original_nuf_star'], 0.)
        self.assertEqual(self.previous.N_UF_star, 0.)
        self.assertEqual(result['previous'].N_P_star, self.previous.N_P_star)

    def test_explicit_helper_off_rejects_while_legacy_off_remains_noop(self):
        self.current.network.control_area_enabled = False
        before = pickle.dumps((self.previous, self.current))
        with self.assertRaisesRegex(ValueError, 'enabled current context'):
            self.prepare()
        self.assertIs(module.finalize(self.previous, self.current), self.previous)
        self.assertEqual(before, pickle.dumps((self.previous, self.current)))


if __name__ == '__main__':
    unittest.main()
