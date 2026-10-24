"""Storage, travel and service invariants for lane-resolved off-ramp candidate."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,CASES,H,MODEL
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import LaneResolvedDelayedPort
import unittest
import copy


class OffLaneTests(unittest.TestCase):
    def test_empty_lane_service_cannot_drain_busy_neighbor(self):
        p=LaneResolvedDelayedPort(4,100,36,[[100,0,2],[100,0,2]],0,[[0,0],[0,0]])
        self.assertEqual(p.release(0,10,[3600,0]),0)
        self.assertEqual(p.stock,2)
        self.assertAlmostEqual(p.residence_veh_h,20/3600)
        with self.assertRaises(ArithmeticError):p.accept(10,1,lane_amounts=[0,1])

    def test_exchange_preserves_cohort_due_and_total_stock(self):
        p=LaneResolvedDelayedPort(8,100,36,[[0,36,1],[50,36,1]],0,[[0,1],[0,0]])
        p._exchange(1)
        self.assertAlmostEqual(p.stock,2)
        self.assertEqual(set(t for t,n in p.lanes[1].pending),{5,10})
        self.assertAlmostEqual(p.admitted,0);self.assertAlmostEqual(p.departed,0)
        self.assertEqual(p.release(0,4,[3600,3600]),0)
        p.accept(4,1,lane_amounts=[.5,.5])
        self.assertAlmostEqual(p.stock,3)
        p.release(4,20,[3600,3600])
        self.assertAlmostEqual(p.departed,3)
        self.assertAlmostEqual(p.stock,0)

    def test_exchange_respects_receiver_storage(self):
        p=LaneResolvedDelayedPort(4,100,36,[[0,36,1],[50,36,1],[0,36,2],[50,36,2]],0,[[0,100],[100,0]])
        p._exchange(1)
        self.assertEqual(p.internal_transferred,0)
        self.assertEqual([x.stock for x in p.lanes],[2,2])

    def test_causal_history_and_aggregate_service_preserved(self):
        here=Path(__file__).resolve().parent
        data=e.ObservationData(CASES[1][1]);model=e.load_base_model(data.geometry,here/'off_lanes_candidate_v1/config.json')
        profile=e.load(MODEL/'port_profile.json')
        w=e.window(data,model,2400,'history_forecast',profile,lambda _: ({},{}))
        data.port_events=[r for r in data.port_events if float(r['time_s'])<=2400]
        data.port_cohorts={k:v for k,v in data.port_cohorts.items() if int(k)<=2400}
        self.assertEqual(w,e.window(data,model,2400,'history_forecast',profile,lambda _: ({},{})))
        for step in w['boundary_steps']:
            for off,qs in step['off_lane_drain_vph'].items():
                self.assertAlmostEqual(sum(qs),step['off_drain_vph'][off])


if __name__=='__main__':unittest.main()
