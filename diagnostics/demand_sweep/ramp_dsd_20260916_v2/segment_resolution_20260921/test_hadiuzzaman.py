"""Conservation, shared receiving and the Eq3/Eq8 activation discontinuity."""
import unittest
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.test_lane_groups import LaneGroupTests
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups,hadi_receiving_vph,hadi_desired_speed
import canonical_harness as ch

class Equations(unittest.TestCase):
    def test_capacity_supply_jam_and_recovery(self):
        self.assertEqual(hadi_receiving_vph(10,110,40,1700,30,.15),1700)
        self.assertEqual(hadi_receiving_vph(41,110,40,1700,30,.15),1445)
        self.assertEqual(hadi_receiving_vph(100,110,40,1700,30,.15),300)
        self.assertEqual(hadi_receiving_vph(110,110,40,1700,30,.15),0)
    def test_mode_switch_is_not_physical_gain(self):
        # Same dense state: activating a 1km/h reduction must not be
        # called a 69km/h physical increase of the traffic's desired speed.
        self.assertEqual(hadi_desired_speed(50,120,'paper_switch',False),50)
        self.assertEqual(hadi_desired_speed(50,119,'paper_switch',True),119)
        self.assertEqual(hadi_desired_speed(50,119,'command',True)-hadi_desired_speed(50,120,'command',False),-1)
    def test_bad_receiving_parameters_fail(self):
        for theta in (-.1,1,float('nan')):
            with self.assertRaises(ValueError):hadi_receiving_vph(20,110,40,1700,11.5,theta)
    def test_paper_representative_drop_is_masked_by_supply(self):
        for rho in range(41,111):
            self.assertEqual(hadi_receiving_vph(rho,110,40,1700,11.5,0),hadi_receiving_vph(rho,110,40,1700,11.5,.15))

class ConservedReceiving(LaneGroupTests):
    def test_fixed_equipped_scope_includes_nominal_command(self):
        spec,state,cfg=self.fixture()
        cfg.network.freeway_hadiuzzaman={'FW_E':dict(ctm=True,relaxation='command',relaxation_cells=[1],cells=[
            dict(capacity_vphpl=1700,wave_kmh=11.5,rho_critical=40,theta=0.) for _ in spec['widths']])}
        plant=PhysicalLaneGroups(spec,state,cfg,ch.accounting)
        self.assertEqual(plant._hadi_target(0,50,120,False),50)
        self.assertEqual(plant._hadi_target(1,50,120,False),120)
        self.assertEqual(plant._hadi_target(1,50,100,True),100)

    def test_ramp_and_mainline_share_rate_budget(self):
        spec,state,cfg=self.fixture()
        cfg.network.freeway_hadiuzzaman={'FW_E':dict(ctm=True,relaxation='fd_cap',cells=[
            dict(capacity_vphpl=1700,wave_kmh=11.5,rho_critical=40,theta=0.) for _ in spec['widths']])}
        plant=PhysicalLaneGroups(spec,state,cfg,ch.accounting)
        cfg.network.off_ramp_split_ratio={o:.05 for o in plant.off}
        initial=sum(map(sum,plant.n));admitted=exited=0.
        for _ in range(3):
            rates={r:.5*plant.ramp_supply(r,cfg) for r in cfg.network.ramps}
            stocks={'freeway:FW_E':{'inside':sum(map(sum,plant.n))},'origin:FW_E':{'outside':state.mainline_origin_queue['FW_E']}}
            stocks.update({'merge_pending:'+r:{'inside':q*cfg.simulation.T_f_h} for r,q in rates.items()})
            ledger=ch.ModelAreaLedger(stocks,capture_response=True)
            ledger.begin_response_step('freeway',state.time_sec,state.time_sec+10)
            ledger.expect_constraint_coverage('freeway_allocator');state._control_area_ledger=ledger
            plant.advance(state,ch.ControlAction.uncontrolled(cfg),ch.DemandStep({'FW_E':6000.},{},{}),cfg,
                offramp_capacity_veh_h={o:0. for o in plant.off},ramp_release_veh_h=rates)
            last=[r for r in plant.rows if r['time_s']==state.time_sec+10]
            admitted+=sum(r['merge_in_veh'] for r in last)+sum(r['longitudinal_in_veh'] for r in last if r['cell']==0)
            exited+=sum(r['mainline_out_veh'] for r in last if r['cell']==len(plant.n)-1)
            self.assertAlmostEqual(sum(map(sum,plant.n)),initial+admitted-exited,places=7)
            self.assertLessEqual(plant.hadi_audit['max_budget_violation_veh'],1e-7)
            state.time_sec+=10
        self.assertGreater(plant.hadi_audit['limited_group_steps'],0)
        self.assertEqual(plant.hadi_audit['desired_changed'],0)

if __name__=='__main__':unittest.main()
