"""Route mass and ledger invariants at an actual ending lane."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919 import test_lane_groups as base
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
import copy
import unittest


class DestinationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):base.LaneGroupTests.setUpClass()

    def fixture(self):return base.LaneGroupTests().fixture()

    def test_priority_preserves_destination_demand(self):
        spec,state,cfg=self.fixture()
        plant=PhysicalLaneGroups(spec,state,cfg,base.ch.accounting,destination_policy='prefer_exit')
        arrivals=[[0.]*len(row) for row in plant.n];arrivals[12]=[2.,8.,10.]
        ratios={o:0. for o in plant.off};ratios['10481']=.1
        plant._label(arrivals,ratios)
        self.assertEqual(plant.off['10481'],[2.,0.,0.])
        self.assertEqual(sum(map(sum,plant.off.values())),2.)

    def test_ending_lane_transfer_keeps_closed_exits_and_source_ledger_conservative(self):
        spec,state,cfg=self.fixture()
        plant=PhysicalLaneGroups(spec,state,cfg,base.ch.accounting,destination_policy='clear_ending_lane')
        fixture=base.LaneGroupTests()
        w=base.e.window(fixture.data,fixture.model,2400,'history_forecast',fixture.profile,lambda _: ({},{}))
        cfg.network.off_ramp_split_ratio=w['boundary_steps'][0]['off_split_ratio']
        control=base.ch.ControlAction.uncontrolled(cfg);demand=base.ch.DemandStep({'FW_E':3000.},{},{})
        before=sum(map(sum,plant.n));exited=entered=0.
        for j in range(6):
            trace=base.ch.ModelAreaLedger({'freeway:FW_E':{'inside':sum(map(sum,plant.n))},
                'origin:FW_E':{'outside':state.mainline_origin_queue['FW_E']}},capture_response=True)
            trace.begin_response_step('freeway',state.time_sec,state.time_sec+10)
            trace.expect_constraint_coverage('freeway_allocator')
            state._control_area_ledger=trace
            plant.advance(state,control,demand,cfg,offramp_capacity_veh_h={o:0. for o in plant.off},
                ramp_release_veh_h={r:0. for r in cfg.network.ramps})
            for row in trace._response['resource_allocations']:
                if row['kind']=='freeway_entry_request':entered+=row['accepted_total_veh']
                if row['kind']=='freeway_terminal_sending':exited+=row['accepted_total_veh']
                if row['kind']=='freeway_offramp_sending':self.assertEqual(row['accepted_total_veh'],0.)
            for off,stock in plant.off.items():
                self.assertTrue(all(0<=x<=n+1e-7 for x,n in zip(stock,plant.n[spec['off_access'][off]['cell']])))
            state.time_sec+=10
        self.assertAlmostEqual(sum(map(sum,plant.n)),before+entered-exited,places=7)


if __name__=='__main__':unittest.main()
