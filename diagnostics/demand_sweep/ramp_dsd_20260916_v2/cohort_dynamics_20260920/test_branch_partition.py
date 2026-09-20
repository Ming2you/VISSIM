"""Spatial causality at an interior diverge, plus conserved future transport."""
from pathlib import Path
import sys,unittest,copy
from contextlib import contextmanager
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.test_upstream_inventory import UpstreamInventoryTests,base
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups


@contextmanager
def actual_partition_speed_calls():
    """Observe the original equation after the canonical wrapper resolved overrides."""
    rows=[];previous=sys.getprofile()
    def profile(frame,event,arg):
        if event!='call' or frame.f_code.co_name!='metanet_speed_update_kmh':return
        parent=frame.f_back
        if parent is None or parent.f_code.co_name!='_patched_metanet_speed_update_kmh':return
        caller=parent.f_back
        if caller is None or caller.f_code.co_name!='advance' or caller.f_locals.get('i')!=8:return
        source=caller.f_locals;effective=frame.f_locals
        rows.append(dict(group=source['g'],side=source.get('side'),armed=parent.f_locals.get('_armed'),
            length_km=effective['length_km'],tau_h=effective['tau_h'],nu=effective['nu_km2_h'],
            kappa=effective['kappa_veh_km_lane'],dt_h=effective['dt_h'],desired=effective['v_eff']))
    sys.setprofile(profile)
    try:yield rows
    finally:sys.setprofile(previous)


class BranchPartitionTests(UpstreamInventoryTests):
    def setup_partition(self,pre=5.,post=5.,pre_speed=10.,post_speed=100.,through=0.,exchange=None,speed_context=False):
        f=self.fixture({(8,1):pre+post});spec,state,cfg=f
        spec['initial_groups'][8][1]['v_kmh']=(pre*pre_speed+post*post_speed)/(pre+post)
        spec['initial_off_eligible']['10643']=[0.,pre,0.]
        spec['branch_partition_initial']={'10643':{
            'pre':[dict(n_veh=n,v_kmh=pre_speed) for n in (0.,pre,0.)],
            'post':[dict(n_veh=n,v_kmh=post_speed) for n in (0.,post,0.)]}}
        spec,state,cfg=base.LaneGroupTests().fixture(spec)
        options={}
        if speed_context:options['partition_speed_context']=True
        if exchange is not None:
            spec['branch_partition_initial']['10643']['exchange']={
                'observation_end_s':state.time_sec,'rates_per_sec':exchange}
            options['partition_exchange']=True
        cfg.network.off_ramp_split_ratio={o:0. for o in cfg.network.off_ramps}
        p=PhysicalLaneGroups(spec,state,cfg,base.ch.accounting,
            port_travel=self.model.lane_port_travel['FW_E'],position_aware_initial=True,
            upstream_exit_inventory={'10643':1.},branch_partition=['10643'],**options)
        p.off['10643'][1]-=through;p.intent_initial['10643']-=through
        return p,state,cfg

    def test_blocked_exit_does_not_stop_vehicles_already_downstream(self):
        p,state,cfg=self.setup_partition();self.advance(p,state,cfg,cap=0.)
        self.assertGreater(p.n[9][1],0.)
        self.assertLessEqual(p.n[9][1],5.)
        self.assertAlmostEqual(p.off['10643'][1],5.)
        self.assertAlmostEqual(sum(map(sum,p.n)),10.)

    def test_upstream_through_cannot_bypass_blocked_exit_head(self):
        p,state,cfg=self.setup_partition(pre=10.,post=0.,through=5.)
        self.advance(p,state,cfg,cap=0.)
        self.assertEqual(p.n[9][1],0.)
        self.assertEqual(p.partitions[8]['post_n'][1],0.)
        self.assertAlmostEqual(p.off['10643'][1],5.)

    def test_internal_transfer_persists_without_two_boundary_jumps(self):
        p,state,cfg=self.setup_partition(pre=10.,post=0.,pre_speed=60.,through=5.)
        self.advance(p,state,cfg,cap=99999.)
        self.assertEqual(p.n[9][1],0.)
        self.assertGreater(p.partitions[8]['post_n'][1],0.)
        self.advance(p,state,cfg,cap=99999.)
        self.assertGreater(p.n[9][1],0.)
        self.assertLess(p.max_partition_residual,1e-7)

    def test_downstream_receiving_still_limits_departures(self):
        p,state,cfg=self.setup_partition()
        n=cfg.network.rho_max*p.lengths[9]*p.widths[9][1]
        p.n[9][1]=n
        self.advance(p,state,cfg,cap=0.)
        rows=[r for r in p.rows if r['cell']==8 and r['group']==1]
        self.assertEqual(rows[-1]['mainline_out_veh'],0.)

    def test_lateral_exchange_preserves_both_partition_stocks(self):
        p,state,cfg=self.setup_partition(pre=10.,post=10.,pre_speed=0.,post_speed=0.,through=5.)
        p.rates[8]=[[0.,.02,0.],[.02,0.,.02],[0.,.02,0.]]
        for _ in range(4):
            self.advance(p,state,cfg,cap=0.)
            part=p.partitions[8]
            for g,n in enumerate(p.n[8]):
                self.assertAlmostEqual(part['pre_n'][g]+part['post_n'][g],n)
                self.assertLessEqual(p.off['10643'][g],part['pre_n'][g]+1e-8)
                for side in ('pre','post'):
                    self.assertGreaterEqual(part[side+'_n'][g],-1e-8)
                    self.assertLessEqual(part[side+'_n'][g],cfg.network.rho_max*part[side+'_length']*p.widths[8][g]+1e-8)

    def test_no_upstream_velocity_transport_when_branch_passage_is_zero(self):
        p,state,cfg=self.setup_partition()
        cfg.network.metanet_tau_h=1e12;cfg.network.metanet_nu_km2_h=0.
        self.advance(p,state,cfg,cap=0.)
        self.assertEqual(p.partition_rows[1]['internal_cross_veh'],0.)
        self.assertAlmostEqual(p.partitions[8]['post_v'][1],100.,places=7)

    def test_accepted_crossing_carries_its_velocity_once(self):
        p,state,cfg=self.setup_partition(through=5.)
        cfg.network.metanet_tau_h=1e12;cfg.network.metanet_nu_km2_h=0.
        self.advance(p,state,cfg,cap=99999.)
        row=p.partition_rows[1];cross=row['internal_cross_veh'];left=row['mainline_out_veh']
        expected=((5-left)*100.+cross*10.)/(5-left+cross)
        self.assertGreater(cross,0.)
        self.assertAlmostEqual(p.partitions[8]['post_v'][1],expected,places=7)

    def test_merge_after_exit_enters_post_stock_only(self):
        p,state,cfg=self.setup_partition()
        rates={r:0. for r in cfg.network.ramps};rates['RM_C10639']=360.
        self.advance(p,state,cfg,cap=0.,releases=rates)
        self.assertAlmostEqual(p.partitions[8]['post_n'][0],1.)
        self.assertEqual(p.partitions[8]['pre_n'][0],0.)
        self.assertAlmostEqual(p.ramp_origin['RM_C10639'][0],1.)
        self.assertEqual(p.off['10643'][0],0.)

    def test_full_post_storage_blocks_internal_crossing(self):
        p,state,cfg=self.setup_partition()
        capacity=cfg.network.rho_max*p.partitions[8]['post_length']
        p,state,cfg=self.setup_partition(pre=10.,post=capacity,pre_speed=60.,through=5.)
        self.advance(p,state,cfg,cap=99999.)
        self.assertEqual(p.partition_rows[1]['internal_cross_veh'],0.)
        self.assertLess(p.partitions[8]['post_n'][1],capacity)

    def test_spatial_exchange_keeps_destination_and_origin_on_correct_side(self):
        rates={'pre':[[0.,0.,0.],[0.,0.,.02],[0.,0.,0.]],
               'post':[[0.,0.,0.],[.02,0.,0.],[0.,0.,0.]]}
        p,state,cfg=self.setup_partition(pre=10.,post=10.,pre_speed=0.,post_speed=0.,through=5.,exchange=rates)
        p.ramp_origin['RM_C10639'][1]=4.
        self.advance(p,state,cfg,cap=0.)
        part=p.partitions[8]
        self.assertGreater(part['pre_n'][2],0.)
        self.assertEqual(part['pre_n'][0],0.)
        self.assertGreater(part['post_n'][0],0.)
        self.assertEqual(part['post_n'][2],0.)
        self.assertAlmostEqual(p.off['10643'][1],5.)
        self.assertEqual(p.off['10643'][2],0.)
        self.assertAlmostEqual(p.ramp_origin['RM_C10639'][0],.4*part['post_n'][0])
        self.assertAlmostEqual(sum(p.ramp_origin['RM_C10639']),4.)
        self.assertAlmostEqual(sum(map(sum,p.n)),20.)

    def test_full_pre_receiver_does_not_block_post_exchange(self):
        rates={s:[[0.,0.,0.],[.02,0.,0.],[0.,0.,0.]] for s in ('pre','post')}
        p,state,cfg=self.setup_partition(pre=10.,post=10.,pre_speed=0.,post_speed=0.,exchange=rates)
        part=p.partitions[8];capacity=cfg.network.rho_max*part['pre_length']*p.widths[8][0]
        part['pre_n'][0]=p.n[8][0]=capacity
        self.advance(p,state,cfg,cap=0.)
        self.assertAlmostEqual(part['pre_n'][0],capacity)
        self.assertGreater(part['post_n'][0],0.)
        self.assertAlmostEqual(sum(p.off['10643']),10.)

    def test_partition_exchange_rejects_invalid_rates(self):
        for invalid in (-.1,float('nan'),float('inf')):
            rates={s:[[0.,0.,0.],[invalid,0.,0.],[0.,0.,0.]] for s in ('pre','post')}
            with self.subTest(rate=invalid),self.assertRaises(ValueError):self.setup_partition(exchange=rates)

    def test_partition_exchange_rejects_missing_or_future_observation(self):
        p,state,cfg=self.setup_partition()
        for exchange in (None,{'observation_end_s':state.time_sec+1,'rates_per_sec':{}}):
            spec=copy.deepcopy(p.spec)
            if exchange is not None:spec['branch_partition_initial']['10643']['exchange']=exchange
            with self.subTest(exchange=exchange),self.assertRaises(ValueError):
                PhysicalLaneGroups(spec,state,cfg,base.ch.accounting,
                    port_travel=self.model.lane_port_travel['FW_E'],position_aware_initial=True,
                    upstream_exit_inventory={'10643':1.},branch_partition=['10643'],partition_exchange=True)

    def test_partition_equation_receives_physical_length_and_segment_coefficients_each_call(self):
        p,state,cfg=self.setup_partition(speed_context=True)
        row=cfg.network.freeway_segment_params['FW_E'][8]
        row.update(metanet_tau_h=2./3600,metanet_nu_km2_h=17.,metanet_kappa_veh_km_lane=13.,v_free=117.)
        cfg.network.v_free=90.
        cfg.network.metanet_tau_h=12./3600;cfg.network.metanet_nu_km2_h=35.
        original=copy.deepcopy(row)
        with actual_partition_speed_calls() as calls:self.advance(p,state,cfg,cap=0.)
        self.assertEqual(len(calls),30)
        for call in calls:
            self.assertTrue(call['armed'])
            self.assertAlmostEqual(call['length_km'],p.partitions[8][call['side']+'_length'])
            self.assertEqual(call['tau_h'],2./3600)
            self.assertEqual(call['nu'],17.)
            self.assertEqual(call['kappa'],13.)
            self.assertLessEqual(call['dt_h'],call['tau_h'])
            if call['group']==0:self.assertAlmostEqual(call['desired'],117.)
        self.assertEqual(row,original)


if __name__=='__main__':unittest.main()
