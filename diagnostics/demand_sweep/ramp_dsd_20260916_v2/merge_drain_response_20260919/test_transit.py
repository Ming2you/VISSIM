import unittest
from types import SimpleNamespace
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response
from canonical_harness import DelayedPort

class EntrySpeedTests(unittest.TestCase):
    def port(self, cohorts=(), accel=1.):
        return DelayedPort(20.,100.,36.,cohorts,0.,interval_service=True,entry_accel_mps2=accel)

    def test_initial_stationary_cohort_requires_acceleration(self):
        p=self.port([[0.,0.,1]])
        self.assertAlmostEqual(p.pending[0][0],15.)
        self.assertEqual(p.release(0.,10.,3600.),0.)

    def test_new_slow_cohort_uses_supplied_entry_speed(self):
        p=self.port();p.accept(0.,1.,entry_speed_kmh=0.)
        self.assertAlmostEqual(p.pending[0][0],15.)
        self.assertEqual(p.release(0.,10.,3600.),0.)

    def test_missing_speed_fails_before_admission(self):
        p=self.port()
        with self.assertRaises(ValueError):p.accept(0.,1.)
        self.assertEqual(p.stock,0.)

    def test_single_lane_fifo_prevents_fast_cohort_passing(self):
        p=self.port();p.accept(0.,1.,entry_speed_kmh=0.)
        p.accept(1.,1.,entry_speed_kmh=36.)
        self.assertGreaterEqual(p.pending[1][0],p.pending[0][0])

    def test_event_residence_includes_travel_and_partial_drain(self):
        p=DelayedPort(20.,100.,36.,[[50.,36.,1]],0.,interval_service=True)
        self.assertAlmostEqual(p.release(0.,10.,360.),.5)
        self.assertAlmostEqual(p.residence_veh_h,8.75/3600)

    def test_residence_is_partition_independent(self):
        p=self.port([[50.,0.,1]]);q=self.port([[50.,0.,1]])
        p.release(0.,20.,360.)
        q.release(0.,7.,360.);q.release(7.,13.,360.)
        self.assertAlmostEqual(p.residence_veh_h,q.residence_veh_h)
        self.assertAlmostEqual(p.stock,q.stock)
        self.assertAlmostEqual(p.stock-p.initial-p.admitted+p.departed,0.)

    def test_invalid_acceleration_rejected(self):
        for a in [True,0.,-1.,float('nan')]:
            with self.assertRaises(ValueError):self.port(accel=a)

    def test_component_cost_uses_integrals_without_sampling_cells(self):
        model=SimpleNamespace(component_residence=True,roads=['FW_E'])
        end={'cumulative_merge_veh':1.,'cumulative_head_service_veh':2.,'outside_component_backlog_veh':0.}
        pred={'ramps':[{'end_sec':450,'ramp':'RM_C1','end':end}],
            'diagnostics':{'roads':[{'road':'FW_E','model_residence_10s_veh_h':10.,
                'ramp_connector_residence_local_1s_veh_h':3.,'off_connector_residence_event_veh_h':2.}]}}
        result=evaluate_response.component(None,model,0,pred)
        self.assertEqual(result['component_ttt_veh_h'],15.)
        self.assertEqual(result['merges']['RM_C1'],1.)

    def test_native_coarse_stock_cannot_silently_supply_exact_cost(self):
        model=SimpleNamespace(component_residence=True)
        with self.assertRaises(ValueError):evaluate_response.component(None,model,0)

if __name__=='__main__':unittest.main()
