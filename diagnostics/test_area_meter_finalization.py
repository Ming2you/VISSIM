"""Actual production calibrated allocation and canonical box-walk tests."""
from __future__ import annotations
import copy
import json
from pathlib import Path
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


if __name__ == '__main__': unittest.main()
