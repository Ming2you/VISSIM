import unittest
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary, LaneResolvedRampBoundary

def spec(**extra):
    return dict(connector_id='test',length_m=100.,head_position_m=50.,lanes=1,
        spacing_m=1.,travel_speed_kmh=36.,time_sec=0.,**extra)

def cycle(**extra):
    return dict(start_sec=0.,duration_sec=10.,cycle_sec=10.,receiving_budget_veh=10.,
        service_veh=10.,mode='OFF',green_sec=None,request_arrivals_veh=10.,**extra)

class RampProfilesTests(unittest.TestCase):
    def test_posthead_speed_does_not_change_upstream_time(self):
        p=PhysicalRampBoundary(**spec(initial_cohorts=[(0.,36.,1),(60.,36.,1)],posthead_travel_speed_kmh=72.))
        r=p.begin_interval(0.,2.)
        self.assertEqual(r['head_ready_veh'],0.)
        self.assertEqual(r['eligible_merge_veh'],1.)
        p.commit_merge(1.);p.apply_head_service(0.,mode='OFF');p.finish_interval(0.)
        r=p.begin_interval(2.,3.)
        self.assertEqual(r['head_ready_veh'],1.)

    def test_uniform_profile_exact_default_receipt(self):
        a=PhysicalRampBoundary(**spec()).advance_local_interval(**cycle())
        b=PhysicalRampBoundary(**spec()).advance_local_interval(**cycle(request_arrivals_by_second=[1.]*10))
        self.assertEqual(a,b)

    def test_late_arrivals_not_available_early(self):
        p=PhysicalRampBoundary(**spec()).advance_local_interval(**cycle(request_arrivals_by_second=[0.]*9+[10.]))
        self.assertEqual(p['head_service_veh'],0.)
        self.assertEqual(p['accepted_merge_veh'],0.)
        self.assertEqual(p['end']['connector_veh'],10.)
        self.assertEqual(p['end']['cumulative_requested_veh'],10.)
        self.assertEqual(p['conservation_residual_veh'],0.)

    def test_reject_before_state_change(self):
        for profile in [[1.]*9,[0.]*10,[-1.]+[11.]+[0.]*8,[float('nan')]+[0.]*9]:
            p=PhysicalRampBoundary(**spec());before=p.snapshot()
            with self.assertRaises(ValueError):p.advance_local_interval(**cycle(request_arrivals_by_second=profile))
            self.assertEqual(before,p.snapshot())

    def test_lane_profiles_preserve_independent_mass(self):
        s=spec();s['lanes']=2
        p=LaneResolvedRampBoundary(**s,lane_arrival_shares=[.3,.7])
        r=p.advance_local_interval(**cycle(request_arrivals_by_second=[0.]*9+[10.]))
        self.assertEqual(r['end']['connector_veh'],10.)
        self.assertEqual([x['end']['connector_veh'] for x in r['lane_receipts']],[3.,7.])
        self.assertEqual(r['conservation_residual_veh'],0.)

    def test_invalid_posthead_speed(self):
        for speed in [0.,-1.,True,float('inf'),float('nan')]:
            with self.assertRaises(ValueError):PhysicalRampBoundary(**spec(posthead_travel_speed_kmh=speed))

if __name__=='__main__':unittest.main()
