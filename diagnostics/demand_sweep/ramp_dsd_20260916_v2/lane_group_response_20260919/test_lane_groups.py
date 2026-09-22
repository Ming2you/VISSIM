"""Physical invariants, not only comparisons against this implementation."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, CASES, MODEL
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.run import HERE
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
import canonical_harness as ch
import copy
import unittest


class LaneGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=e.ObservationData(CASES[1][1])
        cls.model=e.load_base_model(cls.data.geometry,MODEL/'config.json')
        cls.params=e.load(MODEL/'selected_parameters.json')['parameters']
        cls.profile=e.load(MODEL/'port_profile.json')
        lane=e.load(HERE/'observations_v1/s23.json')
        cls.spec={**lane['geometry'],**lane['cutoffs']['2400']}

    def fixture(self,spec=None):
        cfg=self.model._config('FW_E',self.params['by_direction']['FW_E'])
        state=ch.TrafficState.initial(cfg);state.time_sec=2400.
        spec=copy.deepcopy(spec or self.spec)
        state.freeway_effective_lanes['FW_E']=list(map(sum,spec['widths']))
        lengths=ch.accounting.cell_lengths_km(cfg,'FW_E',21)
        state.freeway_density['FW_E']=[sum(r['n_veh'] for r in rows)/lengths[i]/sum(spec['widths'][i])
            for i,rows in enumerate(spec['initial_groups'])]
        state.freeway_speed['FW_E']=[sum(r['n_veh']*(r['v_kmh'] or 0.) for r in rows)/sum(r['n_veh'] for r in rows)
            if sum(r['n_veh'] for r in rows) else cfg.network.v_free for rows in spec['initial_groups']]
        state.mainline_origin_queue['FW_E']=0.
        return spec,state,cfg

    def test_initial_aggregate_mismatch_is_rejected(self):
        spec,state,cfg=self.fixture();spec['initial_groups'][8][0]['n_veh']+=1.
        with self.assertRaisesRegex(ValueError,'stock mismatch'):PhysicalLaneGroups(spec,state,cfg,ch.accounting)

    def test_candidate_copy_and_spawn_serialization_preserve_independent_stocks(self):
        import pickle
        spec,state,cfg=self.fixture()
        plant=PhysicalLaneGroups(spec,state,cfg,ch.accounting)
        before=copy.deepcopy(plant.n)
        for candidate in (copy.deepcopy(plant),pickle.loads(pickle.dumps(plant))):
            self.assertIs(candidate.a,ch.accounting)
            self.assertEqual(candidate.n,before)
            self.assertEqual(candidate.spec,plant.spec)
            candidate.n[8][0]+=1.
            candidate.off[next(iter(candidate.off))][0]+=.25
            self.assertEqual(plant.n,before)
            self.assertNotEqual(candidate.off,plant.off)

    def test_future_snapshot_is_rejected(self):
        spec,state,cfg=self.fixture();spec['observation_end_s']+=1
        with self.assertRaisesRegex(ValueError,'cutoff'):PhysicalLaneGroups(spec,state,cfg,ch.accounting)

    def test_no_borrowing_receiving_space_from_unreachable_lanes(self):
        spec,state,cfg=self.fixture();i=13
        length=ch.accounting.cell_lengths_km(cfg,'FW_E',21)[i]
        spec['initial_groups'][i][0]['n_veh']=cfg.network.rho_max*length
        spec,state,cfg=self.fixture(spec)
        plant=PhysicalLaneGroups(spec,state,cfg,ch.accounting)
        self.assertGreater(sum(plant.free_space(cfg)[i][1:]),0.)
        self.assertAlmostEqual(plant.ramp_supply('RM_C10490',cfg),0.,places=7)

    def test_real_lane_drop_connects_old_lanes_two_to_four(self):
        matrix=self.spec['matrices'][12]
        self.assertEqual(matrix,[[0.,0.,0.],[1.,0.,0.],[0.,.5,.5]])

    def test_blocked_branch_destinations_are_retained_and_all_stock_conserved(self):
        spec,state,cfg=self.fixture();plant=PhysicalLaneGroups(spec,state,cfg,ch.accounting)
        w=e.window(self.data,self.model,2400,'history_forecast',self.profile,lambda _: ({},{}))
        cfg.network.off_ramp_split_ratio=w['boundary_steps'][0]['off_split_ratio']
        control=ch.ControlAction.uncontrolled(cfg);demand=ch.DemandStep({'FW_E':0.},{},{})
        before=sum(map(sum,plant.n));initial_branch=None;terminal=0.
        for _ in range(6):
            trace=ch.ModelAreaLedger({'freeway:FW_E':{'inside':sum(map(sum,plant.n))},'origin:FW_E':{'outside':0.}},capture_response=True)
            trace.begin_response_step('freeway',state.time_sec,state.time_sec+10)
            trace.expect_constraint_coverage('freeway_allocator');state._control_area_ledger=trace
            plant.advance(state,control,demand,cfg,offramp_capacity_veh_h={o:0. for o in plant.off},
                          ramp_release_veh_h={r:0. for r in cfg.network.ramps})
            branch=sum(map(sum,plant.off.values()))
            if initial_branch is None:initial_branch=branch
            self.assertGreaterEqual(branch+1e-8,initial_branch)
            for row in trace._response['resource_allocations']:
                if row['kind']=='freeway_offramp_sending':self.assertEqual(row['accepted_total_veh'],0.)
                if row['kind']=='freeway_terminal_sending':terminal+=row['accepted_total_veh']
            state.time_sec+=10
        self.assertGreater(initial_branch,0.)
        self.assertAlmostEqual(sum(map(sum,plant.n))+terminal,before,places=7)
        self.assertLess(plant.max_residual,1e-7)

    def test_disabled_config_rejects_supplied_group_state(self):
        w=e.window(self.data,self.model,2400,'history_forecast',self.profile,lambda _: ({},{}))
        w['lane_group_dynamics']={'FW_E':self.spec}
        with self.assertRaisesRegex(ValueError,'supplied together'):e.simulate(self.model,w,self.params)


if __name__=='__main__':unittest.main()
