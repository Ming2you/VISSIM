"""Conserved off-ramp storage and stock-only ablation; no native processes."""
import copy
import gzip
import json
from pathlib import Path
import unittest

from canonical_harness import load_base_model, DelayedPort
from boundary_factory import ObservationData, build_window

HERE=Path(__file__).parent
ROOT=HERE.parents[3]
B=HERE/'res10_20260922'
OUT=ROOT/'diagnostics/offramp_dynamic_20260922'


class DynamicOfframps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=ObservationData(B/'fw080_urban090_observations')
        cls.config=B/'boundary_literature_v1/boundary_config.json'
        cls.model=load_base_model(cls.data.geometry,cls.config)
        cls.params=json.loads((B/'boundary_literature_v1/family_parameters.json').read_text())['boundary']
        ns={'__file__':str(HERE/'canonical_harness.py'),'__name__':'before_dynamic_offramps'}
        exec(compile((OUT/'canonical_harness.py.before.txt').read_text(encoding='utf8'),ns['__file__'],'exec'),ns)
        cls.before=ns['load_base_model'](cls.data.geometry,cls.config)

    def window(self,horizon=30):
        w=build_window(self.data,2700.1,'history_forecast',model_step_sec=1,horizon_sec=horizon)
        w['port_dynamics']=dict(schema='physical-off-storage/v1',occupancy_lane_loss=True,
            travel_speed_kmh={c:60. for c in self.model.offramps},
            initial_cohorts={c:[] for c in self.model.offramps})
        for step in w['boundary_steps']:
            step['off_capacity_vph']={c:0. for c in self.model.offramps}
            step['off_drain_vph']={c:0. for c in self.model.offramps}
        return w

    def rollout(self,w,model=None):
        return (model or self.model).rollout(w['initial_cells'],w['boundary_steps'],self.params,
            w['initial_origin_queue'],roads=('FW_E',),port_dynamics=w.get('port_dynamics'),horizon_sec=w['meta']['horizon_s'])

    def test_entry_cap_ablation_was_missing_and_is_now_explicit(self):
        w=self.window();w['port_dynamics']['entry_capacity_mode']='storage_and_proxy'
        old=self.rollout(w,self.before)
        new=self.rollout(w)
        self.assertGreater(sum(p['admitted_veh'] for p in old['ports']),0.)
        self.assertEqual(sum(p['admitted_veh'] for p in new['ports']),0.)
        w['port_dynamics']['entry_capacity_mode']='typo'
        with self.assertRaises(ValueError):self.rollout(w)

    def test_existing_dynamic_default_exact(self):
        w=self.window()
        self.assertEqual(self.rollout(w,self.before),self.rollout(w))
        w['port_dynamics']['entry_capacity_mode']='storage'
        self.assertEqual(self.rollout(w,self.before),self.rollout(w))

    def test_original_static_450s_forecasts_exact(self):
        w=build_window(self.data,2700.1,'history_forecast',model_step_sec=1)
        for road in self.model.roads:
            p=B/f'boundary_literature_v1/fresh_boundary_history_forecast_{road}_2700.1.json.gz'
            with gzip.open(p,'rt',encoding='utf8') as f:old=json.load(f)
            new=self.model.rollout(w['initial_cells'],w['boundary_steps'],self.params,w['initial_origin_queue'],roads=(road,))
            self.assertEqual(new,old)

    def test_queue_drain_restores_effective_lanes_and_conserves_stock(self):
        w=self.window(150);c='10643';geom=self.model.offramps[c]
        w['port_dynamics']['initial_cohorts'][c]=[[geom['length_m'],0.,1] for _ in range(80)]
        for index,step in enumerate(w['boundary_steps']):
            step['off_split_ratio']={o:0. for o in self.model.offramps}
            if index>=60:step['off_drain_vph'][c]=7200.
        result=self.rollout(w)
        rows=[p for p in result['ports'] if p['connector']==c]
        self.assertEqual(rows[59]['n_veh'],80.)
        self.assertAlmostEqual(rows[-1]['n_veh'],0.)
        self.assertAlmostEqual(rows[-1]['departed_veh'],80.)
        self.assertTrue(all(abs(p['conservation_residual_veh'])<1e-8 for p in rows))
        cells=[p for p in result['cells'] if p['cell']==geom['from_cell']]
        self.assertLess(cells[0]['effective_lanes'],cells[-1]['effective_lanes'])
        self.assertAlmostEqual(cells[-1]['effective_lanes'],self.model.base.network.freeway_segment_lanes['FW_E'][geom['from_cell']])

    def test_no_drain_before_travel_arrival_or_banked_service(self):
        p=DelayedPort(10.,100.,36.,[],0.,interval_service=True)
        p.release(0.,1.,3600.);p.accept(1.,1.)
        self.assertEqual(p.release(1.,9.,3600.),0.)
        self.assertAlmostEqual(p.release(10.,2.,3600.),1.)
        self.assertAlmostEqual(p.stock,0.)
        self.assertEqual(p.admitted,p.departed)


if __name__=='__main__':unittest.main()
