"""Within-cell origin ordering, physical travel and conserved label tests."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919 import test_lane_groups as base
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
import unittest
import copy


class PortTravelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.LaneGroupTests.setUpClass()
        cls.model=base.e.load_base_model(base.LaneGroupTests.data.geometry,Path(__file__).with_name('port_travel_candidate_v1')/'config.json')

    def fixture(self):
        fixture=base.LaneGroupTests();spec=copy.deepcopy(fixture.spec)
        for rows in spec['initial_groups']:
            for row in rows:row.update(n_veh=0.,v_kmh=60.)
        spec['initial_groups'][13][0]['n_veh']=20.
        for matrix in spec['exchange_rates_per_sec']:
            for row in matrix:
                for j in range(len(row)):row[j]=0.
        spec['initial_ramp_origin']={r:[0.]*len(spec['widths'][p['cell']]) for r,p in spec['ramp_access'].items()}
        spec['initial_ramp_origin']['RM_C10490'][0]=20.
        spec,state,cfg=fixture.fixture(spec)
        cfg.network.off_ramp_split_ratio={o:.5 for o in cfg.network.off_ramps}
        return spec,state,cfg

    def test_late_merge_cannot_take_upstream_exit_and_uses_remaining_distance(self):
        spec,state,cfg=self.fixture();travel=self.model.lane_port_travel['FW_E']
        self.assertAlmostEqual(travel['ramp_remaining_km']['RM_C10490'],.09144219816623626)
        plant=PhysicalLaneGroups(spec,state,cfg,base.ch.accounting,port_travel=travel)
        releases={r:0. for r in cfg.network.ramps};releases['RM_C10490']=360.
        stocks={'freeway:FW_E':{'inside':20.},'origin:FW_E':{'outside':0.},
            **{'merge_pending:'+r:{'outside':q/360} for r,q in releases.items()}}
        trace=base.ch.ModelAreaLedger(stocks,capture_response=True)
        trace.begin_response_step('freeway',2400,2410);trace.expect_constraint_coverage('freeway_allocator')
        state._control_area_ledger=trace
        plant.advance(state,base.ch.ControlAction.uncontrolled(cfg),base.ch.DemandStep({'FW_E':0.},{},{}),cfg,
            offramp_capacity_veh_h={o:99999. for o in plant.off},ramp_release_veh_h=releases)
        self.assertEqual(sum(plant.off['10483']),0.)
        self.assertEqual(sum(plant.last_off_sent['10483']),0.)
        self.assertAlmostEqual(sum(plant.n[14]),20.)
        self.assertAlmostEqual(sum(plant.ramp_origin['RM_C10490']),1.)
        self.assertAlmostEqual(sum(map(sum,plant.n)),21.)

    def test_origin_tags_must_be_supported_by_current_observed_stock(self):
        spec,state,cfg=self.fixture();spec['initial_ramp_origin']['RM_C10490'][0]=21.
        with self.assertRaises(ValueError):PhysicalLaneGroups(spec,state,cfg,base.ch.accounting,
            port_travel=self.model.lane_port_travel['FW_E'])

    def test_passed_exit_vehicles_cannot_be_initialized_as_exit_destinations(self):
        spec,state,cfg=self.fixture()
        spec['initial_ramp_origin']['RM_C10490'][0]=0.
        spec['initial_off_eligible']={o:[0.]*len(spec['widths'][p['cell']]) for o,p in spec['off_access'].items()}
        spec['initial_off_eligible']['10483'][0]=1.
        plant=PhysicalLaneGroups(spec,state,cfg,base.ch.accounting,
            port_travel=self.model.lane_port_travel['FW_E'],position_aware_initial=True)
        releases={r:0. for r in cfg.network.ramps}
        trace=base.ch.ModelAreaLedger({'freeway:FW_E':{'inside':20.},'origin:FW_E':{'outside':0.},
            **{'merge_pending:'+r:{'outside':0.} for r in releases}},capture_response=True)
        trace.begin_response_step('freeway',2400,2410);trace.expect_constraint_coverage('freeway_allocator')
        state._control_area_ledger=trace
        plant.advance(state,base.ch.ControlAction.uncontrolled(cfg),base.ch.DemandStep({'FW_E':0.},{},{}),cfg,
            offramp_capacity_veh_h={o:99999. for o in plant.off},ramp_release_veh_h=releases)
        self.assertLessEqual(sum(plant.last_off_sent['10483'])+sum(plant.off['10483']),.5+1e-9)
        self.assertAlmostEqual(sum(map(sum,plant.n))+sum(map(sum,plant.last_off_sent.values())),20.)

    def test_pre_exit_stock_cannot_overlap_downstream_ramp_origins(self):
        spec,state,cfg=self.fixture()
        spec['initial_off_eligible']={o:[0.]*len(spec['widths'][p['cell']]) for o,p in spec['off_access'].items()}
        spec['initial_off_eligible']['10483'][0]=1.
        with self.assertRaises(ValueError):
            PhysicalLaneGroups(spec,state,cfg,base.ch.accounting,
                port_travel=self.model.lane_port_travel['FW_E'],position_aware_initial=True)

    def test_split_excludes_only_ramp_origins_that_left_the_cell(self):
        ratio,bypass=base.e.upstream_origin_split(20.,80.,30.,5.,15.)
        self.assertEqual(bypass,20.)
        self.assertEqual(ratio,.25)

    def test_split_rejects_unexplained_ramp_origin_loss(self):
        with self.assertRaises(ValueError):base.e.upstream_origin_split(20.,10.,30.,5.,0.)


if __name__=='__main__':unittest.main()
