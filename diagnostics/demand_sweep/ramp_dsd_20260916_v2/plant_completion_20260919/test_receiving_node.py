import unittest
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary
from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary, gap_acceptance_supply_vph


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


class ReceivingNodeTests(unittest.TestCase):
    def test_gap_limits_and_monotonicity(self):
        self.assertEqual(gap_acceptance_supply_vph(0.,3.,2.),1800.)
        values=[gap_acceptance_supply_vph(q,3.,2.) for q in [0.,1.,500.,1000.,2000.,4000.]]
        self.assertEqual(values,sorted(values,reverse=True))
        self.assertAlmostEqual(gap_acceptance_supply_vph(1.e-8,3.,2.),1800.,places=7)

    def test_invalid_physical_parameters(self):
        for args in [(-1,3,2),(1000,1,2),(1000,3,0),(True,3,2),(1000,float('nan'),2)]:
            with self.assertRaises(ValueError):gap_acceptance_supply_vph(*args)

    def test_aggregate_residence_and_counters(self):
        b=LaneResolvedRampBoundary(**spec([(120.,0.,2)]*10),lane_arrival_shares=[.1,.9])
        integral=0.
        for start in range(0,100,10):
            c=cycle();c.update(start_sec=start,request_arrivals_veh=3.)
            r=b.advance_local_interval(**c)
            integral+=sum(x['start']['connector_veh']/3600 for x in r['local_receipts'])
            self.assertAlmostEqual(b.connector_ttt_veh_h,integral)
            self.assertAlmostEqual(b.cumulative_merge_veh,r['end']['cumulative_merge_veh'])
            self.assertAlmostEqual(b.backlog_veh,r['end']['outside_component_backlog_veh'])
            self.assertAlmostEqual(10+b.cumulative_requested_veh,b.cumulative_merge_veh+b.backlog_veh+r['end']['connector_veh'])

    def test_downstream_vehicles_clear_during_red(self):
        b=LaneResolvedRampBoundary(**spec([(120.,0.,2)]*3+[(60.,0.,1)]*3),lane_arrival_shares=[.5,.5])
        c=cycle();c.update(service_veh=0.,mode='RED',green_sec=0.)
        r=b.advance_local_interval(**c)
        self.assertEqual(r['accepted_merge_veh'],3.)
        self.assertEqual(r['head_service_veh'],0.)
        self.assertEqual(r['end']['connector_veh'],3.)

class CausalLaneHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import copy
        from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
        cls.e=e;cls.copy=copy
        cls.data=e.ObservationData(e.HERE/'controller_response_s23_v1/none')
        folder=e.HERE/'controller_response_4500_v1/model_v5_node'
        cls.model=e.load_base_model(cls.data.geometry,folder/'config.json')
        cls.profile=e.load(folder/'port_profile.json')
        cls.events=e.rows(cls.data.folder/'port_events.csv')

    def make(self,events):
        data=self.copy.copy(self.data)
        data.port_events=events
        data.folder=self.e.HERE/'this_directory_does_not_exist'
        return self.e.window(data,self.model,2400,'history_forecast',self.profile,lambda t: ({},{}))

    def test_live_event_rows_do_not_require_an_offline_csv(self):
        history=[r for r in self.events if 2250<float(r['time_s'])<=2400]
        self.assertEqual(self.make(history),self.make(self.events))

    def test_future_lane_events_cannot_change_forecast(self):
        future={'time_s':2401,'connector':10681,'kind':'arrival','lane':99}
        self.assertEqual(self.make(self.events),self.make(self.events+[future]*1000))

    def test_missing_lane_events_cannot_silently_assign_positive_demand(self):
        events=[r for r in self.events if str(r['connector'])!='10681']
        with self.assertRaisesRegex(ValueError,'without lane arrival history'):
            self.make(events)

if __name__=='__main__':unittest.main()
