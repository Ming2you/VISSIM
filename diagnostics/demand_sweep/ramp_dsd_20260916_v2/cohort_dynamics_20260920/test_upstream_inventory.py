"""Accepted-flow transport and physical conservation of first-exit intent."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919 import test_lane_groups as base
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
import copy
import unittest


class UpstreamInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.LaneGroupTests.setUpClass()
        cls.model=base.e.load_base_model(base.LaneGroupTests.data.geometry,
            Path(__file__).resolve().with_name('port_origin_split_v1')/'config.json')

    def fixture(self, stocks=None, speeds=360.):
        fixture=base.LaneGroupTests(); spec=copy.deepcopy(fixture.spec)
        for i,rows in enumerate(spec['initial_groups']):
            for g,row in enumerate(rows):row.update(n_veh=(stocks or {}).get((i,g),0.),v_kmh=speeds)
        for matrix in spec['exchange_rates_per_sec']:
            for row in matrix:
                for k in range(len(row)):row[k]=0.
        spec['initial_ramp_origin']={r:[0.]*len(spec['widths'][p['cell']]) for r,p in spec['ramp_access'].items()}
        spec['initial_off_eligible']={o:[x['n_veh'] for x in spec['initial_groups'][p['cell']]]
                                    for o,p in spec['off_access'].items()}
        spec,state,cfg=fixture.fixture(spec)
        cfg.network.off_ramp_split_ratio={o:0. for o in cfg.network.off_ramps}
        return spec,state,cfg

    def plant(self, fixture, fraction=.5):
        spec,state,cfg=fixture
        return PhysicalLaneGroups(spec,state,cfg,base.ch.accounting,
            port_travel=self.model.lane_port_travel['FW_E'],position_aware_initial=True,
            upstream_exit_inventory={'10643':fraction})

    def advance(self, p, state, cfg, demand=0., cap=0., releases=None):
        releases=releases or {r:0. for r in cfg.network.ramps}
        ledger=base.ch.ModelAreaLedger({'freeway:FW_E':{'inside':sum(map(sum,p.n))},
            'origin:FW_E':{'outside':state.mainline_origin_queue['FW_E']},
            **{'merge_pending:'+r:{'outside':q*p.dt} for r,q in releases.items()}},capture_response=True)
        ledger.begin_response_step('freeway',state.time_sec,state.time_sec+p.sec)
        ledger.expect_constraint_coverage('freeway_allocator');state._control_area_ledger=ledger
        p.advance(state,base.ch.ControlAction.uncontrolled(cfg),base.ch.DemandStep({'FW_E':demand},{},{}),cfg,
            offramp_capacity_veh_h={o:cap for o in p.off},ramp_release_veh_h=releases)
        state.time_sec+=p.sec
        self.assertLess(p.max_intent_residual,1e-7)
        return ledger

    def test_accepted_transfer_retains_intent_and_cannot_relabel_or_pass_exit(self):
        f=self.fixture({(7,0):20.});p=self.plant(f);_,state,cfg=f
        self.advance(p,state,cfg)
        self.assertAlmostEqual(sum(map(sum,p.upstream_off['10643'])),0.)
        self.assertAlmostEqual(sum(p.off['10643']),10.)
        self.assertAlmostEqual(sum(p.n[8]),20.)
        self.advance(p,state,cfg)
        self.assertAlmostEqual(sum(p.off['10643']),10.)
        self.assertAlmostEqual(sum(p.n[9]),0.)
        self.advance(p,state,cfg,cap=99999.)
        self.assertGreater(sum(p.last_off_sent['10643']),0.)
        self.assertAlmostEqual(sum(p.off['10643'])+p.intent_exited['10643'],10.)

    def test_blocked_receiving_keeps_intent_with_donor(self):
        f=self.fixture({(7,0):20.});spec,state,cfg=f
        length=base.ch.accounting.cell_lengths_km(cfg,'FW_E',21)[8]
        spec['initial_groups'][8][0]['n_veh']=cfg.network.rho_max*length
        f=base.LaneGroupTests().fixture(spec);p=self.plant(f);_,state,cfg=f
        self.advance(p,state,cfg)
        self.assertAlmostEqual(p.upstream_off['10643'][7][0],10.)

    def test_transfer_does_not_cross_two_cells_in_one_step(self):
        f=self.fixture({(6,0):20.});p=self.plant(f);_,state,cfg=f
        self.advance(p,state,cfg)
        self.assertAlmostEqual(p.upstream_off['10643'][7][0],10.)
        self.assertEqual(sum(p.off['10643']),0.)

    def test_only_admitted_source_vehicles_receive_tags(self):
        f=self.fixture();p=self.plant(f,.25);_,state,cfg=f
        self.advance(p,state,cfg,demand=3600.)
        self.assertAlmostEqual(p.intent_entered['10643'],2.5)
        self.assertAlmostEqual(p.upstream_off['10643'][0][0],2.5)
        f=self.fixture();spec,state,cfg=f
        length=base.ch.accounting.cell_lengths_km(cfg,'FW_E',21)[0]
        spec['initial_groups'][0][0]['n_veh']=cfg.network.rho_max*length*sum(spec['widths'][0])
        f=base.LaneGroupTests().fixture(spec);p=self.plant(f,.25);_,state,cfg=f
        self.advance(p,state,cfg,demand=3600.)
        self.assertEqual(p.intent_entered['10643'],0.)
        self.assertAlmostEqual(state.mainline_origin_queue['FW_E'],10.)

    def test_downstream_merge_and_already_passed_stock_get_no_exit_tags(self):
        f=self.fixture({(8,0):20.});spec,state,cfg=f
        spec['initial_off_eligible']['10643']=[0.,0.,0.]
        p=self.plant(f);releases={r:0. for r in cfg.network.ramps};releases['RM_C10639']=360.
        self.advance(p,state,cfg,releases=releases)
        self.assertEqual(p.intent_initial['10643'],0.)
        self.assertEqual(sum(p.off['10643']),0.)

    def test_lateral_exchange_conserves_tags_and_stays_with_carriers(self):
        f=self.fixture({(7,0):10.,(7,1):10.,(7,2):20.},speeds=0.);spec,state,cfg=f
        spec['exchange_rates_per_sec'][7]=[[0.,.03,0.],[.03,0.,.03],[0.,.03,0.]]
        p=self.plant(f)
        self.advance(p,state,cfg)
        self.assertAlmostEqual(sum(p.upstream_off['10643'][7]),20.)
        for n,x in zip(p.n[7],p.upstream_off['10643'][7]):self.assertTrue(-1e-8<=x<=n+1e-8)
        self.assertEqual(p.upstream_off['10643'][7][2],0.)

    def test_invalid_fraction_and_later_branch_are_rejected(self):
        for fraction in (-.1,1.1,float('nan'),True):
            with self.assertRaises(ValueError):self.plant(self.fixture(),fraction)
        spec,state,cfg=self.fixture()
        with self.assertRaisesRegex(ValueError,'first'):
            PhysicalLaneGroups(spec,state,cfg,base.ch.accounting,
                port_travel=self.model.lane_port_travel['FW_E'],position_aware_initial=True,
                upstream_exit_inventory={'10682':.2})


if __name__=='__main__':unittest.main()
