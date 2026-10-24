"""450s conditional component smoke and opt-in-disabled numerical regression."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CAL = HERE.parent/'metanet_calibration_v1'
sys.path[:0] = [str(ROOT), str(CAL), str(ROOT/'diagnostics/rule_baseline_20260914/.plot-deps')]
from canonical_harness import DEFAULT_CONFIG, load_base_model, accounting
from boundary_factory import ObservationData, build_window
from evaluate_native_response import actuated_window, model_component, observed_sampled_component, native_baseline_vsl, posthead_audit


class RampHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = ObservationData(HERE/'seed13_observations')
        cls.model = load_base_model(cls.data.geometry)
        cls.profile = json.loads((HERE/'port_profile.json').read_text(encoding='utf-8'))
        cls.parameters = json.loads((HERE/'fit_dynamic_v1/parameters.json').read_text(encoding='utf-8'))['parameters']
        cls.window = build_window(cls.data, 1350, 'conditioned_diagnostic', cls.profile)
        cls.old = json.loads((HERE/'ramp_harness_legacy_before.json').read_text(encoding='utf-8'))
        cls.target = 'RM_C10490'
        cls.spec = dict(connector_id='10490', length_m=279.03213017760226,
            head_position_m=272.60355928160652, lanes=1, spacing_m=6.,
            travel_speed_kmh=cls.profile['travel_speed_kmh']['10490'], time_sec=1350.,
            initial_cohorts=cls.data.port_cohorts['1350']['10490'])
        cls.dynamics = {'schema': 'physical-ramp-boundary/v1', 'ramps': {cls.target: cls.spec}}

    def rollout(self, steps=None, dynamics=None):
        w = self.window
        return self.model.rollout(w['initial_cells'], steps or w['boundary_steps'],
            self.parameters, w['initial_origin_queue'], port_dynamics=w['port_dynamics'],
            ramp_dynamics=dynamics)

    def test_01_disabled_result_matches_pre_edit_values_and_structure(self):
        result = self.rollout()
        self.assertEqual(result, self.old)
        body = json.dumps(result, sort_keys=True, separators=(',', ':'))
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),
                         '42eb40a94bbfa79511df4e171c4ef92f82959e5eb21e6aafd04fe8973ea6c6c6')
        self.assertNotIn('ramps', result)

    def test_02_real_initial_cohorts_canonical_receiving_and_no_duplicate_meter(self):
        steps = copy.deepcopy(self.window['boundary_steps'])
        tuning = json.loads(DEFAULT_CONFIG.read_text(encoding='utf-8-sig'))
        service_table = tuning['actuation']['real_world_ramp_metering']['per_lane_veh_per_cycle']
        for item in steps:
            start = int(item['window_start_s'])
            green = 8-2*((start-1350)//150)
            # Explicit future realized arrivals are a conditional smoke input,
            # not an autonomous demand forecast or within-horizon state reset.
            row = self.data.ports[(start//30+1)*30, '10490']
            item['ramp_arrival_vph'] = {self.target: float(row['arrivals_veh'])*120.}
            item['ramp_head_service'] = {self.target: {
                'service_veh': service_table[str(green)], 'mode': 'GREEN', 'green_sec': green}}
            del item['ramp_release_vph'][self.target]
        original = accounting._mn.compute_ramp_release_flows
        calls = []

        def checked(state, control, demand, cfg, include_current_arrivals=True):
            self.assertFalse(include_current_arrivals)
            self.assertEqual(control.ramp_metering[self.target], cfg.network.ramp_capacity_veh_h[self.target])
            self.assertEqual(demand.ramp_arrival, {})
            calls.append(state.time_sec)
            return original(state, control, demand, cfg, include_current_arrivals=False)

        with patch.object(accounting._mn, 'compute_ramp_release_flows', checked):
            result = self.rollout(steps, self.dynamics)
        self.assertEqual(calls, list(range(1350, 1800, 10)))
        receipts = result['ramps']
        self.assertEqual(len(receipts), 45)
        for r in receipts:
            self.assertAlmostEqual(r['conservation_residual_veh'], 0., places=10)
            self.assertLessEqual(r['accepted_merge_veh'], r['eligible_merge_veh'])
            self.assertLessEqual(r['end']['connector_veh'], r['end']['capacity_veh']+1e-10)
            self.assertGreaterEqual(r['end']['outside_component_backlog_veh'], 0.)
        for key in ('cells', 'flows'):
            self.assertEqual([r for r in result[key] if r['road']=='FW_W'],
                             [r for r in self.old[key] if r['road']=='FW_W'])
        target_cell = self.model.ramps[self.target]['to_cell']
        target_merge = sum(r['ramp_merges'] for r in result['flows']
                           if r['road']=='FW_E' and r['cell']==target_cell)
        self.assertAlmostEqual(target_merge, sum(r['accepted_merge_veh'] for r in receipts), places=10)
        east = next(r for r in result['diagnostics']['roads'] if r['road']=='FW_E')
        self.assertAlmostEqual(east['ramp_connector_residence_10s_veh_h'],
                               sum(r['connector_ttt_veh_h'] for r in receipts), places=12)
        self.assertLess(east['continuity_residual_max_veh'], 1e-9)
        self.assertEqual(result['diagnostics']['future_state_resets'], 0)
        component = model_component(result, {**self.window, 'ramp_dynamics': self.dynamics})
        self.assertAlmostEqual(component['ramp_merges_veh'], target_merge, places=10)
        self.assertEqual(component['ramp_final_n_veh'], receipts[-1]['end']['connector_veh'])

    def test_03_wrong_geometry_or_missing_action_fails(self):
        bad = copy.deepcopy(self.dynamics)
        bad['ramps'][self.target]['length_m'] += 1.
        with self.assertRaisesRegex(ValueError, 'geometry/time'):
            self.rollout(dynamics=bad)
        with self.assertRaises(KeyError):
            self.rollout(dynamics=self.dynamics)
        with self.assertRaisesRegex(ValueError, 'contract'):
            self.rollout(dynamics={})

    def test_04_explicit_physical_vsl_zone_is_local_and_optional(self):
        from src.models.state import segment_vsl
        steps = copy.deepcopy(self.window['boundary_steps'])
        for row in steps:
            row['vsl_commands'] = {'FW_E__seg10': 80.}
        calls = []
        original = accounting._freeway_substep_events

        def capture(state, control, demand, cfg, **kwargs):
            road = cfg.network.freeway_links[0]
            if road == 'FW_E':
                values = [segment_vsl(control, road, i, cfg) for i in range(21)]
                self.assertEqual([i for i,v in enumerate(values) if v == 80.], [10,11,12])
                calls.append(values)
            return original(state, control, demand, cfg, **kwargs)

        before = copy.deepcopy(self.model.base.network.freeway_vsl_zone_heads)
        with patch.object(accounting, '_freeway_substep_events', capture):
            result = self.model.rollout(self.window['initial_cells'], steps, self.parameters,
                self.window['initial_origin_queue'], port_dynamics=self.window['port_dynamics'],
                vsl_zone_heads={'FW_E': [0,5,10,13,15]})
        self.assertEqual(len(calls), 45)
        self.assertEqual(self.model.base.network.freeway_vsl_zone_heads, before)
        self.assertEqual(self.rollout(), self.old)
        for key in ('cells','flows'):
            self.assertEqual([r for r in result[key] if r['road']=='FW_W'],
                             [r for r in self.old[key] if r['road']=='FW_W'])
        with self.assertRaisesRegex(ValueError, 'VSL'):
            self.model.rollout(self.window['initial_cells'], steps, vsl_zone_heads={'FW_E': [-1,10]})

    def test_05_native_command_contract_and_sampled_scope(self):
        experiment = HERE.parent/'native_fixed_profile_v3'
        commands = json.loads((experiment/'both.json').read_text(encoding='utf-8'))
        meter = json.loads(DEFAULT_CONFIG.read_text(encoding='utf-8-sig'))['actuation']['real_world_ramp_metering']
        baseline = native_baseline_vsl(experiment/'run_none/fixed_readback.csv')
        w = actuated_window(self.data, self.model, 1350, 'history_forecast', self.profile, commands, meter, baseline)
        self.assertEqual(w['vsl_zone_heads'], {'FW_E': [0,5,10,13,15]})
        self.assertEqual([w['boundary_steps'][i]['ramp_head_service'][self.target]['green_sec'] for i in (0,15,30)], [8.,6.,4.])
        self.assertEqual(set(w['boundary_steps'][0]['vsl_commands']),
                         {'FW_E','FW_E__seg10','FW_E__seg11','FW_E__seg12','FW_E__seg13'})
        self.assertEqual(w['boundary_steps'][0]['vsl_commands']['FW_E__seg13'], baseline)
        invalid = copy.deepcopy(commands)
        invalid['vsl_commands'][0]['speed_id'] -= 20
        with self.assertRaisesRegex(ValueError, 'four target DSDs'):
            actuated_window(self.data,self.model,1350,'history_forecast',self.profile,invalid,meter,baseline)
        sampled = observed_sampled_component(self.data,1350,self.model.offramps)
        self.assertEqual(sampled['component_ttt_veh_h'], sum(v for k,v in sampled.items() if k!='component_ttt_veh_h'))
        self.assertGreater(sampled['target_ramp_ttt_veh_h'], 0.)

    def test_06_red_immune_point_queue_is_flagged_without_changing_flow(self):
        zero={'downstream_travelling_veh':0.,'merge_ready_veh':0.}
        crowded={'downstream_travelling_veh':2.,'merge_ready_veh':3.}
        receipt={'ramp':self.target,'start_sec':1350.,'end_sec':1360.,'duration_sec':10.,'start':zero,'end':crowded}
        prediction={'ramps':[receipt]}
        before=copy.deepcopy(prediction)
        observed=[{'time_s':t,'downstream_n':1.} for t in range(1350,1361)]
        audit=posthead_audit(prediction,{'ramp_dynamics':self.dynamics},observed)
        self.assertFalse(audit['actuator_geometry_valid'])
        self.assertEqual(audit['model_max_posthead_veh'],5.)
        self.assertEqual(audit['model_end_snapshot_exceedance_times_s'],[1360.])
        self.assertEqual(audit['native_max_posthead_veh'],1.)
        self.assertEqual(prediction,before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
