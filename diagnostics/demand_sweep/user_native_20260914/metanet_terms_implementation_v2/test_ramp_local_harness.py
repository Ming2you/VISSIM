"""Frozen10s regression and local1s/canonical10s merge coupling."""
from pathlib import Path
import copy
import json
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CAL=HERE.parent/'metanet_calibration_v1'
sys.path[:0]=[str(ROOT),str(CAL),str(ROOT/'diagnostics/rule_baseline_20260914/.plot-deps')]
from canonical_harness import load_base_model,accounting


class RampLocalHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.windows=json.loads((HERE/'native_response_v1/windows.json').read_text())
        cls.frozen=json.loads((HERE/'native_response_v1/predictions.json').read_text())
        geometry=json.loads((HERE/'seed13_observations/geometry.json').read_text())
        cls.model=load_base_model(geometry)
        cls.params=json.loads((HERE/'fit_dynamic_v1/parameters.json').read_text())['parameters']

    def rollout(self,w):
        return self.model.rollout(w['initial_cells'],w['boundary_steps'],self.params,
            w['initial_origin_queue'],port_dynamics=w['port_dynamics'],
            ramp_dynamics=w['ramp_dynamics'],vsl_zone_heads=w['vsl_zone_heads'])

    def test_absent_and_explicit10_match_frozen_entire_output(self):
        for key in ('none_1350_history_forecast','both_1350_history_forecast'):
            w=copy.deepcopy(self.windows[key])
            # Persisted JSON represents the helper's immutable cohort tuples as
            # arrays. Compare the entire serialized output without tolerances.
            expected=json.dumps(self.frozen[key],sort_keys=True,separators=(',',':'))
            self.assertEqual(json.dumps(self.rollout(w),sort_keys=True,separators=(',',':')),expected)
            w['ramp_dynamics']['local_step_sec']=10.
            self.assertEqual(json.dumps(self.rollout(w),sort_keys=True,separators=(',',':')),expected)

    def test_local1_keeps_one_canonical_receiving_query_and45_mainline_steps(self):
        w=copy.deepcopy(self.windows['both_1350_history_forecast'])
        w['ramp_dynamics'].update(local_step_sec=1.,meter_cycle_sec=10.)
        original=accounting._mn.compute_ramp_release_flows
        calls=[]
        def supply(state,control,demand,cfg,include_current_arrivals=True):
            self.assertFalse(include_current_arrivals)
            cap=cfg.network.ramp_capacity_veh_h['RM_C10490']
            self.assertGreaterEqual(state.ramp_queue['RM_C10490'],cap*cfg.simulation.T_f_h)
            self.assertEqual(cfg.simulation.T_f_sec,10.)
            calls.append(state.time_sec)
            return original(state,control,demand,cfg,include_current_arrivals=False)
        with patch.object(accounting._mn,'compute_ramp_release_flows',supply):
            result=self.rollout(w)
        self.assertEqual(calls,list(range(1350,1800,10)))
        receipts=result['ramps']
        self.assertEqual(len(receipts),45)
        for r in receipts:
            self.assertEqual(len(r['local_receipts']),10)
            self.assertLessEqual(r['accepted_merge_veh'],r['receiving_budget_veh']+1e-12)
            self.assertAlmostEqual(r['accepted_merge_veh'],sum(x['accepted_merge_veh'] for x in r['local_receipts']),places=12)
            self.assertLess(abs(r['merge_interface_roundoff_veh']),1e-12)
            self.assertAlmostEqual(r['conservation_residual_veh'],0.,places=10)
            previous=r['start']['downstream_travelling_veh']+r['start']['merge_ready_veh']
            for local in r['local_receipts']:
                s=local['end'];post=s['downstream_travelling_veh']+s['merge_ready_veh']
                self.assertLessEqual(post,max(previous,r['nominal_posthead_storage_veh'])+1e-12)
                previous=post
        target_cell=self.model.ramps['RM_C10490']['to_cell']
        merges=sum(r['ramp_merges'] for r in result['flows'] if r['road']=='FW_E' and r['cell']==target_cell)
        self.assertAlmostEqual(merges,sum(r['accepted_merge_veh'] for r in receipts),places=10)
        for key in ('cells','flows'):
            self.assertEqual([r for r in result[key] if r['road']=='FW_W'],
                [r for r in self.frozen['both_1350_history_forecast'][key] if r['road']=='FW_W'])
        diag=next(r for r in result['diagnostics']['roads'] if r['road']=='FW_E')
        self.assertLess(diag['continuity_residual_max_veh'],1e-9)
        self.assertAlmostEqual(diag['ramp_connector_residence_local_1s_veh_h'],
            sum(x['connector_ttt_veh_h'] for r in receipts for x in r['local_receipts']),places=12)

    def test_bad_local_step_or_cycle_rejected(self):
        for step,cycle in ((.5,10.),(2.,10.),(True,10.),(1.,None),(1.,20.)):
            w=copy.deepcopy(self.windows['none_1350_history_forecast'])
            w['ramp_dynamics'].update(local_step_sec=step,meter_cycle_sec=cycle)
            with self.subTest(step=step,cycle=cycle),self.assertRaises(ValueError):self.rollout(w)


if __name__=='__main__':unittest.main(verbosity=2)
