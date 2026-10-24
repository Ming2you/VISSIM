"""Physical per-lane limits and end-to-end accepted-flow conservation."""
from pathlib import Path
import sys,copy,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.plant_completion_20260919.test_receiving_node import spec,cycle
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919 import test_lane_groups as base
from evaluation.controllers.physical_ramp_boundary import LaneResolvedRampBoundary
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups


class RampLaneBudgetTests(unittest.TestCase):
    def test_blocked_lane_cannot_pass_using_neighbors_budget(self):
        p=LaneResolvedRampBoundary(**spec([(120.,0.,1)]*3+[(120.,0.,2)]*3),lane_arrival_shares=[.5,.5])
        c=cycle();c['receiving_budget_veh']=2.
        r=p.advance_local_interval(**c,receiving_budget_by_lane_veh=[0.,2.])
        self.assertEqual(r['lane_receipts'][0]['accepted_merge_veh'],0.)
        self.assertAlmostEqual(r['lane_receipts'][1]['accepted_merge_veh'],2.)
        self.assertAlmostEqual(r['end']['connector_veh'],4.)
        self.assertAlmostEqual(r['conservation_residual_veh'],0.)

    def test_equal_explicit_budgets_reproduce_old_behavior(self):
        s=spec([(120.,0.,2)]*10)
        a=LaneResolvedRampBoundary(**s,lane_arrival_shares=[.2,.8]).advance_local_interval(**cycle())
        b=LaneResolvedRampBoundary(**s,lane_arrival_shares=[.2,.8]).advance_local_interval(**cycle(),receiving_budget_by_lane_veh=[5.,5.])
        self.assertEqual(a,b)

    def test_invalid_lane_budgets_rejected_before_advancing(self):
        for budgets in [[1.],[-1.,11.],[0.,9.],[True,9.],[float('nan'),1.]]:
            p=LaneResolvedRampBoundary(**spec([]),lane_arrival_shares=[.5,.5])
            with self.assertRaises(ValueError):p.advance_local_interval(**cycle(),receiving_budget_by_lane_veh=budgets)
            self.assertEqual(p.time_sec,0.)


class MainlineLaneCouplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):base.LaneGroupTests.setUpClass()

    def fixture(self):
        f=base.LaneGroupTests();s=copy.deepcopy(f.spec)
        for row in s['initial_groups']:
            for group in row:group.update(n_veh=0.,v_kmh=60.)
        for matrix in s['exchange_rates_per_sec']:
            for row in matrix:
                for j in range(len(row)):row[j]=0.
        s,state,cfg=f.fixture(s);cfg.network.off_ramp_split_ratio={o:0. for o in cfg.network.off_ramps}
        return s,state,cfg

    def advance(self,groups):
        s,state,cfg=self.fixture()
        # Retain the within-cell ramp origin labels through the same interface.
        s['initial_ramp_origin']={r:[0.]*len(s['widths'][p['cell']]) for r,p in s['ramp_access'].items()}
        model=base.e.load_base_model(base.LaneGroupTests.data.geometry,Path(__file__).with_name('port_origin_split_v1')/'config.json')
        plant=PhysicalLaneGroups(s,state,cfg,base.ch.accounting,port_travel=model.lane_port_travel['FW_E'])
        rates={r:0. for r in cfg.network.ramps};rates['RM_C10681']=360.
        ledger=base.ch.ModelAreaLedger({'freeway:FW_E':{'inside':0.},'origin:FW_E':{'outside':0.},
            **{'merge_pending:'+r:{'outside':q/360} for r,q in rates.items()}},capture_response=True)
        ledger.begin_response_step('freeway',2400,2410);ledger.expect_constraint_coverage('freeway_allocator');state._control_area_ledger=ledger
        plant.advance(state,base.ch.ControlAction.uncontrolled(cfg),base.ch.DemandStep({'FW_E':0.},{},{}),cfg,
            offramp_capacity_veh_h={o:99999. for o in plant.off},ramp_release_veh_h=rates,
            ramp_group_release_veh_h={'RM_C10681':groups})
        return plant

    def test_unequal_lane_departures_reach_the_same_mainline_lanes(self):
        p=self.advance([90.,270.,0.])
        self.assertEqual(p.n[9],[.25,.75,0.])
        self.assertEqual(p.ramp_origin['RM_C10681'],[.25,.75,0.])
        self.assertAlmostEqual(sum(map(sum,p.n)),1.)
        self.assertLess(p.max_residual,1e-8)

    def test_mismatched_or_inaccessible_group_release_rejected(self):
        for values in [[0.,350.,0.],[0.,0.,360.],[360.],[-1.,361.,0.]]:
            with self.assertRaises(ValueError):self.advance(values)

    def test_blocked_lane_space_does_not_close_free_lane(self):
        s,state,cfg=self.fixture();f=base.LaneGroupTests()
        length=base.ch.accounting.cell_lengths_km(cfg,'FW_E',21)[9]
        s['initial_groups'][9][0]['n_veh']=cfg.network.rho_max*length
        s,state,cfg=f.fixture(s);p=PhysicalLaneGroups(s,state,cfg,base.ch.accounting)
        lanes=p.ramp_lane_conditions('RM_C10681',[0,1],cfg)
        self.assertAlmostEqual(lanes[0]['space_vph'],0.)
        self.assertGreater(lanes[1]['space_vph'],0.)
        self.assertGreater(lanes[0]['conflicting_vph'],lanes[1]['conflicting_vph'])
        with self.assertRaises(ValueError):p.ramp_lane_conditions('RM_C10681',[0,2],cfg)


class ThroughConflictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):base.LaneGroupTests.setUpClass()

    def fixture(self,enabled=True,travel_edit=None,spec_edit=None):
        s,state,cfg=MainlineLaneCouplingTests().fixture()
        for g in (0,1):s['initial_groups'][9][g].update(n_veh=20.,v_kmh=60.)
        s,state,cfg=base.LaneGroupTests().fixture(s)
        cfg.network.off_ramp_split_ratio={o:0. for o in cfg.network.off_ramps}
        s['initial_ramp_origin']={r:[0.]*len(s['widths'][p['cell']]) for r,p in s['ramp_access'].items()}
        s['initial_ramp_origin']['RM_C10681']=[4.,6.,0.]
        model=base.e.load_base_model(base.LaneGroupTests.data.geometry,Path(__file__).with_name('port_origin_split_v1')/'config.json')
        travel=copy.deepcopy(model.lane_port_travel['FW_E'])
        if travel_edit:travel_edit(travel,s,cfg)
        if spec_edit:spec_edit(s)
        plant=PhysicalLaneGroups(s,state,cfg,base.ch.accounting,port_travel=travel,
            ramp_conflict_through_inventory=['RM_C10681'] if enabled else None)
        return plant,cfg

    def test_prior_exit_and_same_merge_not_counted_as_upstream_conflict(self):
        plant,cfg=self.fixture();plant._initialize_destinations(cfg);plant.off['10682']=[5.,0.,0.]
        old=copy.deepcopy(plant.n);rows=plant.ramp_lane_conditions('RM_C10681',[0,1],cfg)
        self.assertEqual([r['conflicting_stock_veh'] for r in rows],[11.,14.])
        for g,row in enumerate(rows):self.assertAlmostEqual(row['conflicting_vph'],row['conflicting_stock_veh']*60/plant.lengths[9])
        self.assertEqual(plant.n,old)
        self.assertEqual(rows[0]['same_merge_origin_veh'],4.)
        self.assertEqual(rows[0]['prior_exit_stock_veh'],5.)

    def test_merged_stock_still_consumes_receiving_space(self):
        plant,cfg=self.fixture();before=plant.ramp_lane_conditions('RM_C10681',[0,1],cfg)
        plant.n[9][1]+=2.;plant.ramp_origin['RM_C10681'][1]+=2.
        after=plant.ramp_lane_conditions('RM_C10681',[0,1],cfg)
        self.assertEqual(after[1]['conflicting_vph'],before[1]['conflicting_vph'])
        self.assertAlmostEqual(before[1]['space_vph']-after[1]['space_vph'],2/plant.dt)

    def test_initial_label_query_is_idempotent(self):
        plant,cfg=self.fixture();cfg.network.off_ramp_split_ratio['10682']=.1
        a=plant.ramp_lane_conditions('RM_C10681',[0,1],cfg);labels=copy.deepcopy(plant.off)
        b=plant.ramp_lane_conditions('RM_C10681',[0,1],cfg)
        self.assertEqual(a,b);self.assertEqual(plant.off,labels)
        self.assertGreater(sum(labels['10682']),0.)

    def test_unsupported_port_order_and_multiple_merges_rejected(self):
        def after(travel,s,cfg):travel['off_distance_km']['10682']=100.
        with self.assertRaises(ValueError):self.fixture(travel_edit=after)
        def second(s):s['ramp_access']['RM_C10639']['cell']=9
        with self.assertRaises(ValueError):self.fixture(spec_edit=second)


if __name__=='__main__':unittest.main()
