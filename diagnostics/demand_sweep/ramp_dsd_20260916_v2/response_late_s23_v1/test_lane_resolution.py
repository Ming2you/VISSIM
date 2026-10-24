import unittest
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.response_late_s23_v1.lane_boundary_candidate import LaneResolvedRampBoundary


def spec(cohorts):
    return dict(connector_id='test',length_m=120.,head_position_m=60.,lanes=2,
                spacing_m=6.,travel_speed_kmh=36.,time_sec=0.,initial_cohorts=cohorts)


def cycle(**overrides):
    return dict(start_sec=0.,duration_sec=10.,cycle_sec=10.,receiving_budget_veh=10.,
                service_veh=10.,mode='OFF',green_sec=None,request_arrivals_veh=0.,**overrides)


class LaneResolutionTests(unittest.TestCase):
    def test_empty_lane_cannot_lend_merge_supply(self):
        s=spec([(120.,0.,2)]*10)
        pooled=PhysicalRampBoundary(**s).advance_local_interval(**cycle())
        resolved=LaneResolvedRampBoundary(**s,lane_arrival_shares=[0.,1.]).advance_local_interval(**cycle())
        self.assertEqual(pooled['accepted_merge_veh'],10.)  # Reproduces old pooling.
        self.assertEqual(resolved['accepted_merge_veh'],5.)
        self.assertEqual(resolved['end']['connector_veh'],5.)

    def test_empty_lane_cannot_lend_head_service(self):
        r=LaneResolvedRampBoundary(**spec([(60.,0.,2)]*10),lane_arrival_shares=[0.,1.]).advance_local_interval(**cycle())
        self.assertEqual(r['head_service_veh'],5.)

    def test_empty_lane_cannot_lend_storage(self):
        b=LaneResolvedRampBoundary(**spec([(120.,0.,2)]*20),lane_arrival_shares=[0.,1.])
        c=cycle();c.update(receiving_budget_veh=0.,request_arrivals_veh=5.)
        r=b.advance_local_interval(**c)
        self.assertEqual(r['end']['connector_veh'],20.)
        self.assertAlmostEqual(r['end']['outside_component_backlog_veh'],5.)
        self.assertAlmostEqual(r['conservation_residual_veh'],0.)

    def test_red_and_conservation_across_cycles(self):
        b=LaneResolvedRampBoundary(**spec([(60.,0.,2)]*6),lane_arrival_shares=[.1,.9])
        for start in range(0,40,10):
            c=cycle();c.update(start_sec=start,service_veh=0.,mode='RED',green_sec=0.,request_arrivals_veh=3.)
            r=b.advance_local_interval(**c)
            self.assertEqual(r['head_service_veh'],0.)
            self.assertAlmostEqual(r['conservation_residual_veh'],0.)
        self.assertAlmostEqual(b.snapshot()['connector_veh'],18.)

    def test_reject_invalid_shares(self):
        for shares in [[.2,.2],[-.1,1.1],[1.],[True,0.]]:
            with self.assertRaises(ValueError):
                LaneResolvedRampBoundary(**spec([]),lane_arrival_shares=shares)


if __name__=='__main__':unittest.main()
