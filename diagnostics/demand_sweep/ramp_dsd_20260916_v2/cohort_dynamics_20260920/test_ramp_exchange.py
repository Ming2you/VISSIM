"""Physical constraints for ramp-internal lane transfer, independent of gains."""
import unittest,math,copy
from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.plant_completion_20260919.test_receiving_node import spec,cycle


def rates(a=0.,b=0.):
    return {'prehead':[[0.,a],[b,0.]],'posthead':[[0.,a],[b,0.]]}


class RampExchangeTests(unittest.TestCase):
    def buffer(self,cohorts,exchange=None):
        return LaneResolvedRampBoundary(**spec(cohorts),lane_arrival_shares=[.5,.5],lane_exchange_rates_per_sec=exchange)

    def test_disabled_generator_replays_zero_rate_physics(self):
        cohorts=[(10.,20.,1),(50.,0.,2),(61.,10.,1),(120.,0.,2)]
        old=self.buffer(cohorts);new=self.buffer(cohorts,rates())
        def clean(x):
            if isinstance(x,dict):return {k:clean(v) for k,v in x.items() if k not in
                {'cumulative_lane_entry_veh','cumulative_lane_exit_veh','lane_exchange_transfers_veh'}}
            if isinstance(x,list):return [clean(v) for v in x]
            return x
        for t in range(0,40,10):
            c=cycle();c.update(start_sec=t,request_arrivals_veh=3.)
            self.assertEqual(old.advance_local_interval(**c),clean(new.advance_local_interval(**c)))

    def test_transfer_preserves_eta_stage_mass_and_does_not_count_as_admission(self):
        p=self.buffer([(20.,10.,1),(80.,10.,1)],rates(math.log(2)))
        before=[copy.deepcopy(b._upstream+b._downstream) for b in p._lane_buffers]
        moved=p._exchange_lanes();a,b=p._lane_buffers
        self.assertAlmostEqual(moved['prehead'][0][1],.5)
        self.assertAlmostEqual(moved['posthead'][0][1],.5)
        self.assertEqual([eta for eta,n in b._upstream+b._downstream],[eta for eta,n in before[0]])
        self.assertAlmostEqual(a.snapshot()['connector_veh'],1.)
        self.assertAlmostEqual(b.snapshot()['connector_veh'],1.)
        self.assertEqual(a.cumulative_admitted_veh+b.cumulative_admitted_veh,0.)
        self.assertAlmostEqual(a._lane_transfer_out,b._lane_transfer_in)

    def test_full_posthead_lane_cannot_borrow_empty_prehead_space(self):
        p=self.buffer([(120.,0.,2)]*10+[(120.,0.,1)]*2+[(20.,10.,1)]*2,rates(100.))
        r=p._exchange_lanes()
        self.assertEqual(r['posthead'][0][1],0.)
        self.assertGreater(r['prehead'][0][1],0.)
        self.assertAlmostEqual(p._lane_buffers[1]._merge_ready,10.)

    def test_two_donors_share_one_receiver_space(self):
        s=spec([(60.,0.,1)]*10+[(60.,0.,2)]*9+[(60.,0.,3)]*10);s['lanes']=3
        matrix=[[0.,100.,0.],[0.,0.,0.],[0.,100.,0.]]
        p=LaneResolvedRampBoundary(**s,lane_arrival_shares=[1/3]*3,
            lane_exchange_rates_per_sec={'prehead':matrix,'posthead':matrix})
        r=p._exchange_lanes()
        self.assertAlmostEqual(r['prehead'][0][1]+r['prehead'][2][1],1.)
        self.assertAlmostEqual(p._lane_buffers[1]._head_ready,10.)

    def test_red_still_prevents_head_crossing_after_lane_change(self):
        p=self.buffer([(60.,0.,1)]*4,rates(1.,.1));c=cycle()
        c.update(mode='RED',green_sec=0.,service_veh=0.)
        r=p.advance_local_interval(**c)
        self.assertGreater(r['lane_exchange_transfers_veh']['prehead'][0][1],0.)
        self.assertEqual(r['head_service_veh'],0.)
        self.assertEqual(r['accepted_merge_veh'],0.)
        self.assertAlmostEqual(r['connector_ttt_veh_h'],4*10/3600)

    def test_posthead_transfer_does_not_skip_travel_or_need_a_new_green(self):
        p=self.buffer([(61.,0.,1)],rates(1.));c=cycle()
        c.update(mode='RED',green_sec=0.,service_veh=0.)
        r=p.advance_local_interval(**c)
        self.assertTrue(all(x['accepted_merge_veh']==0 for x in r['local_receipts'][:5]))
        self.assertGreater(r['accepted_merge_veh'],.99)
        self.assertEqual(r['head_service_veh'],0.)

    def test_multicycle_lane_ledger_and_ttt(self):
        p=self.buffer([(60.,0.,2)]*10+[(120.,0.,1)]*5,rates(.08,.015));ttt=0.
        for t in range(0,100,10):
            c=cycle();c.update(start_sec=t,request_arrivals_veh=2.,receiving_budget_veh=1.)
            r=p.advance_local_interval(**c,receiving_budget_by_lane_veh=[.2,.8])
            ttt+=sum(x['start']['connector_veh']/3600 for x in r['local_receipts'])
            self.assertAlmostEqual(p.connector_ttt_veh_h,ttt)
            self.assertAlmostEqual(r['end']['cumulative_lane_entry_veh'],r['end']['cumulative_lane_exit_veh'])
            for lane in r['lane_receipts']:
                a,z=lane['start'],lane['end']
                self.assertAlmostEqual(z['connector_veh']-a['connector_veh'],lane['admitted_arrivals_veh']-lane['accepted_merge_veh']+
                    z['cumulative_lane_entry_veh']-a['cumulative_lane_entry_veh']-z['cumulative_lane_exit_veh']+a['cumulative_lane_exit_veh'])

    def test_invalid_rates_fail(self):
        bad=[{}, {'prehead':[[0,1],[0,0]]},rates(-1),rates(float('nan')),rates(True),
             {'prehead':[[1,0],[0,0]],'posthead':[[0,0],[0,0]]}]
        for r in bad:
            with self.assertRaises(ValueError):self.buffer([],r)

    def test_explicit_lane_arrivals_preserve_time_and_not_only_shares(self):
        p=self.buffer([],rates());c=cycle();c.update(request_arrivals_veh=2.)
        profile=[[1.]+[0.]*9,[0.]*9+[1.]]
        r=p.advance_local_interval(**c,request_arrivals_by_lane_second=profile)
        self.assertEqual([x['admitted_arrivals_veh'] for x in r['lane_receipts']],[1.,1.])
        self.assertEqual([x['admitted_arrivals_veh'] for x in r['local_receipts']],[1.]+[0.]*8+[1.])
        self.assertEqual(p._lane_buffers[0]._downstream[0][0],13.)
        self.assertEqual(p._lane_buffers[1]._upstream[0][0],16.)

    def test_inconsistent_lane_arrivals_rejected_before_clock_advances(self):
        for profile in [[[1.]*10],[[1.]*10,[0.]*10],[[True]*10,[0.]*10]]:
            p=self.buffer([]);c=cycle()
            with self.assertRaises(ValueError):p.advance_local_interval(**c,request_arrivals_by_lane_second=profile)
            self.assertEqual(p.time_sec,0.)
        p=self.buffer([]);c=cycle();c.update(request_arrivals_veh=1.,request_arrivals_by_second=[1.]+[0.]*9)
        with self.assertRaises(ValueError):
            p.advance_local_interval(**c,request_arrivals_by_lane_second=[[0.]*9+[1.],[0.]*10])


if __name__=='__main__':unittest.main()
