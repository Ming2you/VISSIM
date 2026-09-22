"""Local signal/merge timing checks; no native simulation or parameter fitting."""
from pathlib import Path
import math
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary


def make(rows=()):
    return PhysicalRampBoundary(connector_id='10490', length_m=279.03213017760226,
        head_position_m=272.6035592816065, lanes=1, spacing_m=6.,
        travel_speed_kmh=32.403731246431235, time_sec=0., initial_cohorts=rows)


def local(model, *, budget=5., service=4.2, mode='OFF', green=None, arrivals=0.):
    return model.advance_local_interval(start_sec=model.time_sec, duration_sec=10.,
        cycle_sec=10., receiving_budget_veh=budget, service_veh=service,
        mode=mode, green_sec=green, request_arrivals_veh=arrivals)


def post(snapshot):
    return snapshot['downstream_travelling_veh'] + snapshot['merge_ready_veh']


class RampLocalTests(unittest.TestCase):
    def test_free_flow_retains_service_throughput_after_pipeline_warmup(self):
        m=make([[272.6035592816065, 0., 1]]*40)
        rows=[local(m) for _ in range(5)]
        for row in rows[1:]:
            self.assertAlmostEqual(row['accepted_merge_veh'], 4.2, places=12)
            self.assertAlmostEqual(row['head_service_veh'], 4.2, places=12)
        self.assertGreater(sum(r['accepted_merge_veh'] for r in rows), 19.)
        self.assertLessEqual(max(post(r['end']) for a in rows for r in a['local_receipts']),
                             (m.length_m-m.head_position_m)/m.spacing_m+1e-12)

    def test_zero_receiving_stops_head_at_finite_posthead_space(self):
        m=make([[272.6035592816065, 0., 1]]*20)
        a=local(m,budget=0.);b=local(m,budget=0.)
        cap=(m.length_m-m.head_position_m)/m.spacing_m
        self.assertAlmostEqual(a['head_service_veh'],cap,places=12)
        self.assertEqual(b['head_service_veh'],0.)
        self.assertEqual(b['accepted_merge_veh'],0.)
        self.assertAlmostEqual(post(b['end']),cap,places=12)
        self.assertAlmostEqual(b['end']['connector_veh'],20.,places=12)

    def test_red_clears_only_previous_posthead_vehicles(self):
        m=make([[272.6035592816065,0.,1]]*3+[[279.,20.,1]])
        a=local(m,service=0.,mode='RED',green=0.)
        self.assertEqual(a['head_service_veh'],0.)
        self.assertAlmostEqual(a['accepted_merge_veh'],1.)
        self.assertAlmostEqual(a['end']['head_ready_veh'],3.)

    def test_local_green_pulses_preserve_cycle_budget_and_timing(self):
        m=make([[272.6035592816065,0.,1]]*20)
        a=local(m,service=3.24,mode='GREEN',green=8.)
        self.assertAlmostEqual(a['head_service_veh'],3.24,places=12)
        self.assertEqual([r['meter_mode'] for r in a['local_receipts']],['GREEN']*8+['RED']*2)
        self.assertEqual(a['local_receipts'][0]['accepted_merge_veh'],0.)
        self.assertGreater(a['local_receipts'][1]['accepted_merge_veh'],0.)
        self.assertEqual(a['local_receipts'][-1]['head_service_veh'],0.)

    def test_initial_native_oversubscription_is_retained_and_clears(self):
        m=make([[279.,20.,1]]*2+[[272.6035592816065,0.,1]]*5)
        a=local(m,budget=0.)
        self.assertEqual(a['head_service_veh'],0.)
        self.assertEqual(post(a['end']),2.)
        b=local(m,budget=5.)
        self.assertLessEqual(post(b['end']),b['nominal_posthead_storage_veh']+1e-12)
        self.assertGreater(b['head_service_veh'],0.)

    def test_budget_conservation_and_actual_one_second_cost(self):
        m=make([[272.6035592816065,0.,1]]*12)
        total_ttt=0.
        for _ in range(10):
            a=local(m,budget=.7,arrivals=2.,service=2.34,mode='GREEN',green=6.)
            self.assertLessEqual(a['accepted_merge_veh'],.7+1e-12)
            self.assertEqual(len(a['local_receipts']),10)
            for r in a['local_receipts']:
                self.assertLessEqual(r['accepted_merge_veh'],.07+1e-12)
                self.assertAlmostEqual(r['conservation_residual_veh'],0.,places=10)
                total_ttt+=r['start']['connector_veh']/3600.
            self.assertAlmostEqual(a['end']['connector_ttt_veh_h'],total_ttt,places=12)
            self.assertAlmostEqual(a['accepted_merge_veh'],sum(r['accepted_merge_veh'] for r in a['local_receipts']))

    def test_invalid_subcycle_request_does_not_mutate_state(self):
        for field,value in [('duration_sec',9.),('cycle_sec',11.),('receiving_budget_veh',math.nan),
                            ('service_veh',math.inf),('green_sec',2.5)]:
            m=make();before=m.snapshot()
            args=dict(start_sec=0.,duration_sec=10.,cycle_sec=10.,receiving_budget_veh=5.,
                      service_veh=1.,mode='GREEN',green_sec=2.,request_arrivals_veh=1.)
            args[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):m.advance_local_interval(**args)
            self.assertEqual(m.snapshot(),before)

    def test_fractional_native_phase_keeps_green_overlap_and_cycle_budget(self):
        m=PhysicalRampBoundary(connector_id='10490', length_m=300.,
            head_position_m=200., lanes=1, spacing_m=6., travel_speed_kmh=36.,
            time_sec=2700.1, initial_cohorts=[[200.,0.,1]]*30)
        receipts=[]
        for _ in range(10):
            receipts.append(m.advance_local_interval(start_sec=m.time_sec,duration_sec=1.,
                cycle_sec=10.,receiving_budget_veh=.5,service_veh=3.24,mode='GREEN',
                green_sec=8.,request_arrivals_veh=0.,allow_partial_cycle=True))
        self.assertAlmostEqual(sum(r['head_service_veh'] for r in receipts),3.24,places=10)
        self.assertAlmostEqual(receipts[7]['head_service_veh'],3.24/8*.9,places=10)
        self.assertEqual(receipts[8]['head_service_veh'],0.)
        self.assertAlmostEqual(receipts[9]['head_service_veh'],3.24/8*.1,places=10)
        self.assertEqual(m.time_sec,2710.1)
        self.assertTrue(all(abs(r['conservation_residual_veh'])<1e-9 for r in receipts))

    def test_fractional_native_off_retains_time_and_service(self):
        m=PhysicalRampBoundary(connector_id='10490',length_m=300.,head_position_m=200.,
            lanes=1,spacing_m=6.,travel_speed_kmh=36.,time_sec=2709.1,
            initial_cohorts=[[200.,0.,1]]*30)
        row=m.advance_local_interval(start_sec=2709.1,duration_sec=1.,cycle_sec=10.,
            receiving_budget_veh=.5,service_veh=4.2,mode='OFF',green_sec=None,
            request_arrivals_veh=0.,allow_partial_cycle=True)
        self.assertAlmostEqual(row['head_service_veh'],.42)
        self.assertEqual(row['end_sec'],2710.1)


if __name__=='__main__':unittest.main(verbosity=2)
