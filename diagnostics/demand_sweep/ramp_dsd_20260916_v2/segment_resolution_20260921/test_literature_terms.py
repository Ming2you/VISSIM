"""Formula limits and conserved blocked-exit behavior; never starts VISSIM."""
import math, unittest
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.test_lane_groups import LaneGroupTests
from evaluation.controllers.physical_lane_groups import (PhysicalLaneGroups,junction_mean_speed,
    junction_downstream_density,off_operational_factors)
from evaluation.controllers.freeway_fd import state_response_coefficients
import canonical_harness as ch

class FormulaTests(unittest.TestCase):
    def test_inlet_uses_flow_weights_not_equal_average(self):
        self.assertEqual(junction_mean_speed(30,20*100+10*40,50),80)
        self.assertEqual(junction_mean_speed(0,0,50),50)
    def test_outlet_is_density_weighted_not_arithmetic(self):
        self.assertEqual(junction_downstream_density([10,30]),25)
        self.assertEqual(junction_downstream_density([0,0]),0)
    def test_exact_smooth_lane_loss_at_full_storage_and_recovery(self):
        self.assertEqual(off_operational_factors([1,1,2],[1,1,0],0,100,.5,2),[1,1,1])
        factors=off_operational_factors([1,1,2],[1,1,0],100,100,.5,2)
        self.assertAlmostEqual(sum(w*f for w,f in zip([1,1,2],factors)),3+math.exp(-2))
        self.assertEqual(factors[2],1)
        half=off_operational_factors([1,1,2],[1,1,0],50,100,.5,2)
        self.assertGreater(half[0],factors[0])
    def test_invalid_inputs_fail(self):
        with self.assertRaises(ValueError):off_operational_factors([1],[1],1,0,.5,2)
        with self.assertRaises(ValueError):junction_downstream_density([float('nan')])
    def test_gradient_sign_not_critical_density_selects_nu(self):
        s={'anticipation':{'downstream_ge_local':35,'downstream_lt_local':12}}
        self.assertEqual(state_response_coefficients(s,80,100,5,6,30,12/3600,1)[1],35)
        self.assertEqual(state_response_coefficients(s,80,100,50,49,30,12/3600,1)[1],12)
        self.assertEqual(state_response_coefficients(s,80,100,5,5,30,12/3600,1)[1],35)

class ConservedExitTests(LaneGroupTests):
    def test_width_loss_does_not_also_apply_fifo_speed_clamp(self):
        speeds=[];flows=[]
        for closure in (False,True):
            spec,_,_=self.fixture()
            for rows in spec['initial_groups']:
                for row in rows:row['v_kmh']=80.
            for matrix in spec['exchange_rates_per_sec']:
                for row in matrix:
                    for j in range(len(row)):row[j]=0.
            spec,state,cfg=self.fixture(spec)
            if closure:cfg.network.freeway_port_response={'FW_E':dict(merge_speed=False,diverge_density=False,
                spillback=dict(mode='envelope',gamma=.5,b=2))}
            plant=PhysicalLaneGroups(spec,state,cfg,ch.accounting)
            cfg.network.off_ramp_split_ratio={o:.05 for o in plant.off}
            ledger=ch.ModelAreaLedger({'freeway:FW_E':{'inside':sum(map(sum,plant.n))},'origin:FW_E':{'outside':0.}},capture_response=True)
            ledger.begin_response_step('freeway',2400,2410);ledger.expect_constraint_coverage('freeway_allocator');state._control_area_ledger=ledger
            offstate={o:dict(n_veh=50,capacity_veh=100,density_by_group=[40 if w else 0 for w in p['weights']])
                      for o,p in spec['off_access'].items()}
            plant.advance(state,ch.ControlAction.uncontrolled(cfg),ch.DemandStep({'FW_E':0.},{},{}),cfg,
                offramp_capacity_veh_h={o:1e9 for o in plant.off},ramp_release_veh_h={r:0 for r in cfg.network.ramps},
                offramp_start_state=offstate if closure else None)
            speeds.append([v for row in plant.v for v in row]);flows.append(sum(r['mainline_out_veh'] for r in plant.rows))
        self.assertLess(flows[1],flows[0])
        for a,b in zip(*speeds):self.assertAlmostEqual(a,b,places=8)

    def test_both_lane_modes_keep_queued_exit_vehicles_and_geometry(self):
        for mode in ('replace_fifo','envelope'):
            spec,state,cfg=self.fixture()
            cfg.network.freeway_port_response={'FW_E':dict(merge_speed=True,diverge_density=True,
                spillback=dict(mode=mode,gamma=.5,b=2))}
            plant=PhysicalLaneGroups(spec,state,cfg,ch.accounting)
            cfg.network.off_ramp_split_ratio={o:.05 for o in plant.off}
            before=sum(map(sum,plant.n));terminal=0.;first_labels=None
            lanes=list(state.freeway_effective_lanes['FW_E'])
            for _ in range(3):
                ledger=ch.ModelAreaLedger({'freeway:FW_E':{'inside':sum(map(sum,plant.n))},'origin:FW_E':{'outside':0.}},capture_response=True)
                ledger.begin_response_step('freeway',state.time_sec,state.time_sec+10)
                ledger.expect_constraint_coverage('freeway_allocator');state._control_area_ledger=ledger
                offstate={o:dict(n_veh=100,capacity_veh=100,density_by_group=[80 if w else 0 for w in p['weights']])
                          for o,p in spec['off_access'].items()}
                plant.advance(state,ch.ControlAction.uncontrolled(cfg),ch.DemandStep({'FW_E':0.},{},{}),cfg,
                    offramp_capacity_veh_h={o:0 for o in plant.off},ramp_release_veh_h={r:0 for r in cfg.network.ramps},
                    junction_ramp_speeds={r:40 for r in cfg.network.ramps},offramp_start_state=offstate)
                labels=sum(map(sum,plant.off.values()))
                if first_labels is None:first_labels=labels
                self.assertGreaterEqual(labels+1e-8,first_labels)
                terminal+=sum(r['accepted_total_veh'] for r in ledger._response['resource_allocations'] if r['kind']=='freeway_terminal_sending')
                self.assertEqual(lanes,state.freeway_effective_lanes['FW_E'])
                self.assertAlmostEqual(sum(map(sum,plant.n))+terminal,before,places=7)
                state.time_sec+=10
            self.assertGreater(first_labels,0)
            for r in plant.port_response_rows:
                if r['kind']=='spillback':
                    self.assertLess(r['operational_lanes'],r['physical_lanes'])
                    if mode=='envelope':self.assertTrue(all(a<=b for a,b in zip(r['used_fifo'],r['original_fifo'])))

if __name__=='__main__':unittest.main()
