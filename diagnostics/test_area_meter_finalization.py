"""Actual production calibrated allocation and canonical box-walk tests."""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path
import pickle
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import area_meter_finalization as module
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from src.models.state import ControlAction


class MeterFinalizationTests(unittest.TestCase):
    def fixture(self, *, spill=0., demand=1200.):
        cfg = SimpleNamespace(network=SimpleNamespace(control_area_enabled=True,
            ramp_capacity_veh_h={'R': 1800.}))
        settings = {'allocation': 'measured_table', 'write_back_realized': True,
                    'min_green_sec': 2, 'max_green_sec': 10, 'close_penalty_mode': 'demand',
                    'meter_lanes': {'B': 2}, 'spillback_guard': {'enabled': True, 'spill_threshold_veh': 8, 'floor_vph': 1800}}
        tuning = {'actuation': {'real_world_ramp_metering': settings}}
        mapping = {'ramp_meters': [{'id': 'A', 'model_ramp_key': 'R', 'connector': 1},
                                   {'id': 'B', 'model_ramp_key': 'R', 'connector': 2}]}
        raw = {'sim_sec': 900, 'local_observation': {'far_measurement': {'link_volume_veh_h': {'1': demand, '2': demand}}}}
        state = SimpleNamespace(local_observation_summary={'ramp_spillback': {'R': spill}})
        module.configure(adapter, cfg, tuning, mapping, raw, None, state)
        return cfg, tuning, mapping, raw, state

    def test_minimum_two_seconds_and_writer_exact_same_schedule(self):
        cfg, _, mapping, _, _ = self.fixture()
        control = ControlAction(ramp_metering={'R': 131.39246994163818})
        module.finalize(control, cfg)
        self.assertAlmostEqual(control.ramp_metering['R'], 766.8)
        self.assertEqual({control.diagnostics['rw_meter_green_'+m] for m in ('A', 'B')}, {2.})
        prior = copy.deepcopy(control)
        module.finalize(control, cfg)
        self.assertEqual(vars(control), vars(prior))
        self.assertEqual(module.assert_writer(control, cfg, require_scored=True)['control_area_meter_writer_matches_scored'], 1.)
        rows = adapter.real_world_ramp_meter_actions(control, cfg, cfg.network.control_area_meter_context['actuation'], mapping)
        self.assertEqual([rows[m]['green_sec'] for m in ('A','B')], [2.,2.])
        self.assertEqual(control.ramp_metering, prior.ramp_metering)

    def test_copied_action_changed_rate_invalidates_old_schedule(self):
        cfg, *_ = self.fixture()
        original = ControlAction(ramp_metering={'R': 1000.})
        module.finalize(original, cfg)
        frozen = copy.deepcopy(original)
        changed = original.copy()
        changed.ramp_metering['R'] = 1800.
        module.finalize(changed, cfg)
        fresh = ControlAction(ramp_metering={'R': 1800.})
        module.finalize(fresh, cfg)
        self.assertEqual(changed.ramp_metering, fresh.ramp_metering)
        self.assertEqual(changed.diagnostics[module.MARKER], fresh.diagnostics[module.MARKER])
        self.assertEqual(vars(original), vars(frozen))

    def test_state_demand_table_mapping_and_marker_tamper_invalidate(self):
        cfg, tuning, mapping, raw, state = self.fixture()
        original = ControlAction(ramp_metering={'R': 1000.})
        module.finalize(original, cfg)
        old = original.diagnostics[module.MARKER]['context_sha256']
        for field in ('demand', 'state', 'table', 'mapping'):
            child_cfg = copy.deepcopy(cfg)
            context = child_cfg.network.control_area_meter_context
            if field == 'demand': context['raw']['local_observation']['far_measurement']['link_volume_veh_h']['1'] = 150.
            if field == 'state': context['spillback']['R'] = 20.
            if field == 'table': context['actuation']['real_world_ramp_metering']['per_lane_veh_per_cycle'] = {'2': .71, '10': 4.3}
            if field == 'mapping': context['mapping']['ramp_meters'][0]['connector'] = 3
            changed = original.copy()
            module.finalize(changed, child_cfg)
            self.assertNotEqual(changed.diagnostics[module.MARKER]['context_sha256'], old, field)
            module.assert_writer(changed, child_cfg, require_scored=True)
        changed = original.copy()
        changed.diagnostics['rw_meter_green_A'] = 9.
        with self.assertRaises(ValueError): module.assert_writer(changed, cfg, require_scored=True)
        module.finalize(changed, cfg)
        self.assertNotEqual(changed.diagnostics['rw_meter_green_A'], 9.)

    def test_severe_spill_guard_precedes_allocation_and_late_mutation_fails(self):
        cfg, *_ = self.fixture(spill=20)
        control = ControlAction(ramp_metering={'R': 100.})
        module.finalize(control, cfg)
        marker = control.diagnostics[module.MARKER]
        self.assertEqual(marker['requested_rates']['R'], 100.)
        self.assertEqual(control.diagnostics['rw_meter_requested_R'], 1800.)
        self.assertEqual(marker['guard_metadata']['rw_spill_guard_R_from_vph'], 100.)
        self.assertEqual(marker['guard_metadata']['rw_spill_guard_forced_count'], 1.)
        control.ramp_metering['R'] += 1
        with self.assertRaises(ValueError): module.assert_writer(control, cfg, require_scored=True)

    def test_off_is_exact_noop_and_enabled_missing_context_fails(self):
        cfg, *_ = self.fixture()
        cfg.network.control_area_enabled = False
        control = ControlAction(ramp_metering={'R': 1}, diagnostics={'rw_meter_realized_R': 300.})
        frozen = copy.deepcopy(control)
        self.assertIs(module.finalize(control,cfg), control)
        self.assertEqual(vars(control), vars(frozen))
        self.assertEqual(module.assert_writer(control,cfg,require_scored=True), {})
        cfg.network.control_area_enabled = True
        del cfg.network.control_area_meter_context
        with self.assertRaises(ValueError): module.finalize(control,cfg)

    def test_unscored_nonfollower_baseline_is_rejected_except_explicit_warmup(self):
        cfg, tuning, mapping, raw, state = self.fixture()
        control = ControlAction(ramp_metering={'R': 1800.})
        with self.assertRaises(ValueError): module.assert_writer(control,cfg,require_scored=True)
        module.assert_writer(control,cfg,require_scored=False)
        tuning['adapter'] = {'post_guard_safety': {'enabled': True}}
        with self.assertRaisesRegex(ValueError, 'baseline selector'):
            module.configure(adapter,cfg,tuning,mapping,raw,None,state)

    def test_endpoint_base_and_meter_probes_are_private_and_quantization_is_visible(self):
        from src.controllers.rollout_endpoint import ObjectiveSpec, LeverMove
        cfg, *_ = self.fixture()
        control = ControlAction(ramp_metering={'R': 131.39246994163818})
        before = copy.deepcopy(control)
        spec = ObjectiveSpec(cfg)
        base = module.for_endpoint(control, [], spec)
        hi = module.for_endpoint(control, [LeverMove('meter','R',191.39246994163818)], spec)
        lo = module.for_endpoint(control, [LeverMove('meter','R',71.39246994163818)], spec)
        self.assertEqual(vars(control), vars(before))
        self.assertEqual(base.ramp_metering['R'], hi.ramp_metering['R'])
        self.assertNotEqual(base.ramp_metering['R'], lo.ramp_metering['R'])
        self.assertNotIn(module.MARKER, control.diagnostics)

    def test_actual_box_walk_refinalizes_each_interval_without_initial_candidate_mutation(self):
        from diagnostics.probe_signal_feasibility import setup
        from src.controllers import rollout_endpoint
        cfg, state, _, tuning, _, _, _ = setup()
        cfg.network.control_area_enabled = True
        mapping = json.loads((ROOT/tuning['mapping_json']).read_text(encoding='utf-8'))
        raw = {'sim_sec': 900, 'local_observation': {'far_measurement': {'link_volume_veh_h': {str(m['connector']): 1200 for m in mapping['ramp_meters']}}}}
        module.configure(adapter,cfg,tuning,mapping,raw,None,state)
        control = ControlAction.uncontrolled(cfg)
        control.ramp_metering = {r: 1000. for r in cfg.network.ramp_capacity_veh_h}
        control.N_UF_star = 7200.
        module.finalize(control,cfg)
        before = copy.deepcopy(control)
        observed = []
        def coupled(s, c, demand, config):
            raw_rates = dict(c.ramp_metering)
            module.finalize(c,config)
            observed.append({'requested': raw_rates, 'finalized': dict(c.ramp_metering)})
            return SimpleNamespace(freeway_ttt=0.,urban_ttt=0.)
        with patch('src.simulation.coupling.run_coupled_interval', side_effect=coupled):
            rollout_endpoint._rollout(state,control,[object()]*3,rollout_endpoint.ObjectiveSpec(cfg,depth_override=3,box_walk=True))
        self.assertEqual(len(observed),3)
        self.assertNotEqual(observed[0]['finalized'],observed[1]['requested'])
        self.assertNotEqual(observed[1]['requested'],observed[1]['finalized'])
        self.assertEqual(vars(control),vars(before))


class CanonicalMeterCandidateTests(unittest.TestCase):
    """Pure physical allocation tests: no TrafficState, rollout, or COM calls."""

    def fixture(self):
        cfg, tuning, _, _, _ = MeterFinalizationTests().fixture(demand=200.)
        ramps = ('R_D_W', 'R_F_W', 'R_D_E', 'R_F_E')
        cfg.network.ramp_capacity_veh_h = dict.fromkeys(ramps, 1800.)
        cfg.network.ramp_to_freeway = {r: 'FW_'+r[-1] for r in ramps}
        tuning['actuation']['real_world_ramp_metering']['cycle_sec'] = 10.
        mapping = {'ramp_meters': [
            {'id': f'{r}_{i}', 'model_ramp_key': r, 'connector': j*2+i,
             'sc_no': 9100+j*2+i, 'sg_no': 1}
            for j, r in enumerate(ramps) for i in (1, 2)]}
        raw = {'sim_sec': 900, 'local_observation': {'far_measurement': {
            'link_volume_veh_h': {str(m['connector']): 200. for m in mapping['ramp_meters']}}}}
        state = SimpleNamespace(local_observation_summary={'ramp_spillback': dict.fromkeys(ramps, 0.)})
        module.configure(adapter, cfg, tuning, mapping, raw, None, state)
        rates = dict(zip(ramps, (1169.0634529178417, 1484.531726458921, 1800., 962.6324439585037)))
        control = ControlAction(N_P_star=4000., N_UF_star=math.fsum(rates.values()), ramp_metering=rates,
                                vsl={'FW_W__seg0': 80., 'FW_W__seg5': 100.},
                                green_times={'SC1004__p3': 50.}, offsets={'SC1004': 5.},
                                diagnostics={'nested': {'preserved': [1, 2]}})
        return cfg, control

    def prepare(self, control, cfg, **overrides):
        args = {'owned_ramps': tuple(control.ramp_metering),
                'total_budget': {'mode': 'equality', 'veh_h': 7200.},
                'directional_budgets': {d: {'mode': 'equality', 'veh_h': 3600.} for d in ('FW_E', 'FW_W')},
                'budget_tolerance_veh_h': 1.e-9}
        args.update(overrides)
        return module.prepare_canonical_candidate(control, cfg, **args)

    def rows(self, control, cfg):
        context = cfg.network.control_area_meter_context
        rows = adapter.real_world_ramp_meter_actions(copy.deepcopy(control), cfg,
                                                     context['actuation'], context['mapping'])
        return {m: {k: v for k, v in row.items() if k != 'group_rate_vph'} for m, row in rows.items()}

    def test_all_open_canonical_private_idempotent_and_serializable(self):
        cfg, control = self.fixture()
        before = pickle.dumps((cfg, control))
        allocated = module.finalize(copy.deepcopy(control), cfg)
        canonical = self.prepare(control, cfg)
        self.assertEqual(canonical.ramp_metering, dict.fromkeys(control.ramp_metering, 1800.))
        self.assertEqual(canonical.N_UF_star, 7200.)
        self.assertEqual(self.rows(allocated, cfg), self.rows(canonical, cfg))
        self.assertEqual(before, pickle.dumps((cfg, control)))
        self.assertEqual(vars(canonical), vars(self.prepare(canonical, cfg)))
        for restored in (pickle.loads(pickle.dumps(canonical)), ControlAction(**json.loads(json.dumps(vars(canonical))))):
            module.assert_writer(restored, cfg, require_scored=True)
            self.assertEqual(vars(restored), vars(canonical))
            self.assertEqual(vars(restored), vars(self.prepare(restored, cfg)))
        canonical.diagnostics['nested']['preserved'].append(3)
        self.assertEqual(control.diagnostics['nested']['preserved'], [1, 2])

    def test_budget_failure_never_retargets_input_or_enlarges_budget(self):
        cfg, control = self.fixture()
        before = pickle.dumps((cfg, control))
        for mode in ('equality', 'cap'):
            budget = {'mode': mode, 'veh_h': control.N_UF_star}
            with self.assertRaisesRegex(module.MeterCandidateInfeasible, 'total .*realized 7200'):
                self.prepare(control, cfg, total_budget=budget)
            self.assertEqual(budget['veh_h'], control.N_UF_star)
        with self.assertRaisesRegex(module.MeterCandidateInfeasible, 'FW_W'):
            self.prepare(control, cfg, directional_budgets={'FW_W': {'mode': 'cap', 'veh_h': 3000.}})
        self.assertEqual(before, pickle.dumps((cfg, control)))
        self.assertEqual(self.prepare(control, cfg, total_budget=None, directional_budgets={}).N_UF_star, 7200.)

    def test_partial_closed_and_max_green_below_cycle_are_not_open(self):
        cfg, control = self.fixture()
        context = cfg.network.control_area_meter_context
        for meter in context['mapping']['ramp_meters'][:2]:
            context['raw']['local_observation']['far_measurement']['link_volume_veh_h'][str(meter['connector'])] = 1200.
        control.ramp_metering['R_D_W'] = 131.39246994163818
        control.ramp_metering['R_F_W'] = 0.
        allocated = module.finalize(copy.deepcopy(control), cfg)
        canonical = self.prepare(control, cfg, total_budget=None, directional_budgets={})
        self.assertEqual(canonical.ramp_metering['R_D_W'], allocated.ramp_metering['R_D_W'])
        self.assertEqual(canonical.ramp_metering['R_F_W'], 0.)
        self.assertEqual(self.rows(canonical, cfg), self.rows(allocated, cfg))
        cfg, control = self.fixture()
        cfg.network.control_area_meter_context['actuation']['real_world_ramp_metering']['max_green_sec'] = 9.
        allocated = module.finalize(copy.deepcopy(control), cfg)
        canonical = self.prepare(control, cfg, total_budget=None, directional_budgets={})
        self.assertEqual(canonical.ramp_metering, allocated.ramp_metering)
        self.assertEqual({row['green_sec'] for row in self.rows(canonical, cfg).values()}, {9.})

    def test_foreign_owner_and_fixed_levers_preserved_for_edited_owned_request(self):
        cfg, control = self.fixture()
        module.finalize(control, cfg)
        # A normal local candidate edits owned rates while retaining the base marker.
        control.ramp_metering['R_F_W'] = 1400.
        before = pickle.dumps((cfg, control))
        foreign_rows = self.rows(control, cfg)
        canonical = self.prepare(control, cfg, owned_ramps=('R_D_W', 'R_F_W'), total_budget=None,
                                 directional_budgets={'FW_W': {'mode': 'equality', 'veh_h': 3600.}})
        for ramp in ('R_D_E', 'R_F_E'):
            self.assertEqual(canonical.ramp_metering[ramp], control.ramp_metering[ramp])
            for mid, row in self.rows(canonical, cfg).items():
                if row['model_ramp_key'] == ramp:
                    self.assertEqual(row, foreign_rows[mid])
        for field in ('N_P_star', 'vsl', 'green_times', 'offsets', 'inflow_outflow_allocation', 'infeasibility'):
            self.assertEqual(getattr(canonical, field), getattr(control, field))
        self.assertEqual(before, pickle.dumps((cfg, control)))
        control.diagnostics['rw_meter_green_R_F_E_1'] = 5.
        with self.assertRaisesRegex(ValueError, 'Foreign meter'):
            self.prepare(control, cfg, owned_ramps=('R_D_W', 'R_F_W'))

    def test_near_cap_that_changes_schedule_is_infeasible(self):
        cfg, control = self.fixture()
        control.ramp_metering['R_D_W'] = 3000.
        for mid in (1, 2):
            cfg.network.control_area_meter_context['raw']['local_observation']['far_measurement']['link_volume_veh_h'][str(mid)] = 1200.
        before = pickle.dumps((cfg, control))
        with self.assertRaises(module.MeterCandidateInfeasible):
            self.prepare(control, cfg, total_budget=None, directional_budgets={})
        self.assertEqual(before, pickle.dumps((cfg, control)))

    def test_invalid_domains_missing_context_and_changed_frozen_context_fail(self):
        cfg, control = self.fixture()
        for overrides in ({'owned_ramps': ()}, {'owned_ramps': ('R_D_W', 'R_D_W')},
                          {'total_budget': {'mode': 'intent', 'veh_h': 7200.}},
                          {'total_budget': {'mode': 'cap', 'veh_h': float('nan')}},
                          {'directional_budgets': {'UNKNOWN': None}}, {'budget_tolerance_veh_h': -1.}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.prepare(control, cfg, **overrides)
        with self.assertRaisesRegex(ValueError, 'Foreign meter'):
            self.prepare(control, cfg, owned_ramps=('R_D_W', 'R_F_W'))
        changed = copy.deepcopy(cfg)
        changed.network.control_area_enabled = False
        with self.assertRaises(ValueError): self.prepare(control, changed)
        del changed.network.control_area_meter_context
        changed.network.control_area_enabled = True
        with self.assertRaises(ValueError): self.prepare(control, changed)
        original_finalize = module.finalize
        def mutate_context(candidate, config):
            result = original_finalize(candidate, config)
            config.network.control_area_meter_context['sim_sec'] += 1.
            return result
        with patch.object(module, 'finalize', side_effect=mutate_context), self.assertRaisesRegex(ValueError, 'frozen context'):
            self.prepare(control, cfg)


if __name__ == '__main__': unittest.main()
