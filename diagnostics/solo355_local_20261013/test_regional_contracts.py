"""Failure-closed regional Registry and accepted-resource contracts."""
import copy
import unittest
from types import SimpleNamespace as NS
from evaluation.controllers.sdmpc_tangent_constraints import Registry
from evaluation.controllers.sdmpc_regional_contracts import quantity_constraints


def fixture(mode):
    cfg=NS(network=NS(sdmpc_options={'regional_prediction_prototype':mode},
        signals=('S',),ramps=('R',),freeway_links=('F',),ramp_to_freeway={'R':'F'},
        urban_movements={'M':{}},urban_link_storage_veh={'U':20.}),
        simulation=NS(T_c_sec=150.))
    fw=mode=='freeway_only'
    q=dict(schema='regional-accepted-quantities/v1',region=mode,start_sec=900.,end_sec=1350.,
        active_resource='NUF' if fw else 'NP',np_actual=0. if fw else -2.,
        nuf_actual=80. if fw else 0.,
        coverage=dict(region=mode,complete=True,sample_sec=5. if fw else 10.,
            samples=90 if fw else 45,configured_movement_count=0 if fw else 1),
        owners={} if fw else {'S':dict(net_inflow_veh=-2.,accepted_event_count=1,
            by_kind_veh=dict(boundary_in=0.,off_ramp=0.,boundary_out=2.,on_ramp=0.,internal=0.))},
        predicted_ramp_merge=dict(active=fw,remote_prediction=False,boundary='ramp_to_mainline',
            rate_veh_h_by_ramp={'R':80.} if fw else {},accepted_vehicles_by_ramp={'R':10.} if fw else {}))
    return cfg,q


class QuantityContracts(unittest.TestCase):
    def validate(self,mode,q,**changes):
        cfg,_=fixture(mode)
        args=dict(start_sec=900.,horizon_steps=3,np_mode='cap',target_np_veh=0.,
            np_tolerance_veh=0.,nuf_mode='cap',target_nuf_veh_h=100. if mode=='freeway_only' else 0.,
            nuf_tolerance_veh_h=0.)
        args.update(changes)
        return quantity_constraints(NS(cfg=cfg),None,q,**args)

    def test_only_own_resource_is_checked(self):
        for mode in ('freeway_only','urban_only'):
            _,q=fixture(mode);result=self.validate(mode,q)
            self.assertTrue(result['feasible'])
            absent=result['np' if mode=='freeway_only' else 'nuf']
            self.assertEqual(absent['mode'],'inactive')
            self.assertFalse(absent['constraint_checked'])
            self.assertIsNone(absent['satisfied'])

    def test_no_fabricated_absent_target(self):
        for mode,target in (('freeway_only','target_np_veh'),('urban_only','target_nuf_veh_h')):
            _,q=fixture(mode)
            with self.assertRaisesRegex(ValueError,'Absent'):
                self.validate(mode,q,**{target:1.})

    def test_merge_count_and_rate_must_agree(self):
        _,q=fixture('freeway_only');q['predicted_ramp_merge']['accepted_vehicles_by_ramp']['R']=11.
        with self.assertRaisesRegex(ValueError,'count/rate'):self.validate('freeway_only',q)

    def test_signed_service_cannot_be_replaced_by_entry_count(self):
        _,q=fixture('urban_only');q['owners']['S']['net_inflow_veh']=2.
        with self.assertRaisesRegex(ValueError,'signed owner'):self.validate('urban_only',q)

    def test_nonfinite_and_remote_catalog_fail(self):
        for mode in ('freeway_only','urban_only'):
            _,q=fixture(mode)
            q['np_actual']=float('nan')
            with self.assertRaises(ValueError):self.validate(mode,q)
            _,q=fixture(mode);q['owners']['REMOTE']={}
            with self.assertRaisesRegex(ValueError,'owner catalog'):self.validate(mode,q)


class RegistryContracts(unittest.TestCase):
    def fixture(self,mode):
        cfg,_=fixture(mode)
        state=NS(time_sec=150.,regional_boundary={'mode':mode},
            ramp_queue={'R':2.},mainline_origin_queue={'F':3.},freeway_density={'F':[4.]},
            freeway_buffer_up_density={},freeway_buffer_down_density={},
            urban_movement_queue={'M':6.},urban_link_storage={'U':8.},lane_freeway_runtime=None)
        coverage=dict(schema='regional-model-constraint-coverage/v1',region=mode,
            complete=True,conditional_model_feasibility_witness=True,expected_visits=2,
            completed_visits=2,missing_constraints=[])
        return cfg,state,coverage

    def test_freeway_registry_has_no_urban_shell_rows(self):
        cfg,state,coverage=self.fixture('freeway_only')
        registry=Registry([150.],region='freeway_only')
        names,_=registry.finish([state],cfg,coverage=coverage)
        self.assertTrue(names)
        self.assertFalse(any('urban' in name or '/storage/' in name for name in names))
        state.urban_movement_queue={'REMOTE':float('nan')}
        self.assertEqual(names,Registry([150.],region='freeway_only').finish([state],cfg,coverage=coverage)[0])

    def test_freeway_requires_own_allocator_witness(self):
        cfg,state,coverage=self.fixture('freeway_only')
        for key,value in (('complete',False),('completed_visits',1),('region','urban_only')):
            bad=dict(coverage,**{key:value})
            with self.assertRaises(ValueError):Registry([150.],region='freeway_only').finish([state],cfg,coverage=bad)

    def test_urban_requires_recorded_endpoint_upper_bounds(self):
        cfg,state,coverage=self.fixture('urban_only')
        registry=Registry([150.],region='urban_only')
        with self.assertRaisesRegex(ValueError,'coverage'):registry.finish([state],cfg,coverage=coverage)
        registry.bound(NS(_response_stamp=lambda:dict(end_sec=150.)),'lane_urban_cell','M',6.,10.)
        names,_=registry.finish([state],cfg,coverage=coverage)
        self.assertFalse(any('/ramp_queue/' in name or 'freeway' in name for name in names))
        self.assertTrue(any('/upper' in name for name in names))

    def test_freeway_rejects_unexpected_urban_bound(self):
        registry=Registry([150.],region='freeway_only')
        with self.assertRaisesRegex(ValueError,'Urban state bound'):
            registry.bound(None,'lane_urban_cell','M',1.,2.)



class ActiveResourceContracts(unittest.TestCase):
    def test_absent_resource_has_no_dual_or_qp_bound(self):
        import numpy as np
        from evaluation.controllers import sdmpc_central as c
        for mask in ([False,True],[True,False]):
            inactive=0 if not mask[0] else 1
            initial=c.initialize_duals([7.,11.],caps=True,active_resources=mask)
            self.assertEqual(initial[inactive],0.)
            updated=c.update_duals([7.,11.],[100.,100.],[0.,0.],1.,caps=True,active_resources=mask)
            self.assertEqual(updated[inactive],0.)
            lo,hi=c.qp_bounds([100.,100.],[0.,0.],caps=True,active_resources=mask)
            self.assertEqual((lo[inactive],hi[inactive]),(-np.inf,np.inf))

    def test_leader_never_moves_absent_coordinate(self):
        from evaluation.controllers import sdmpc_central as c
        from diagnostics.test_sdmpc_central import OPTIONS
        for mask in ([False,True],[True,False]):
            center=[0.,50.] if not mask[0] else [50.,0.]
            inactive=0 if not mask[0] else 1
            attempted=[center]
            for _ in range(4):
                trial=c.next_budget(center,dict(accepted_for_leader_direction=True,
                    gradient_estimate=[-100.,-100.]),attempted,([-100.,0.],[200.,2000.]),OPTIONS,
                    active_resources=mask)
                if trial is None:break
                self.assertEqual(trial[inactive],center[inactive])
                self.assertNotIn(trial,[tuple(v) for v in attempted])
                attempted.append(trial)
            self.assertGreater(len(attempted),1)

    def test_recovery_omits_absent_budget_row(self):
        import numpy as np
        from evaluation.controllers import sdmpc_central as c
        from diagnostics.test_sdmpc_central import OPTIONS
        coord=NS(lower=np.array([-10.]),upper=np.array([10.]),
            G=np.zeros((0,1)),glo=np.zeros(0),ghi=np.zeros(0))
        physical=dict(names=[],values=[],jacobian=np.zeros((0,1)),scope='fixture')
        for mask in ([False,True],[True,False]):
            receipt=c.recover((np.array([0.]),np.array([[-2.]]),np.array([[1.],[1.]]),
                physical,physical),np.array([0.]),[0.,0.],np.array([0.,0.]),
                np.array([1.,1.]),np.zeros(2),coord,OPTIONS,True,caps=True,active_resources=mask)
            absent='budget/NP/upper' if not mask[0] else 'budget/NUF/upper'
            self.assertNotIn(absent,[row['name'] for row in receipt['active_rows']])
            self.assertEqual(receipt['gradient_estimate'][0 if not mask[0] else 1],0.)
            self.assertEqual(receipt['constraints'],3)  # own resource + two control bounds
            self.assertEqual(receipt['active_resources'],mask)

    def test_invalid_masks_fail(self):
        from evaluation.controllers import sdmpc_central as c
        for mask in ([False,False],[1,0],[True],['urban']):
            with self.assertRaises(ValueError):c.initialize_duals([0.,0.],caps=True,active_resources=mask)


class RegionalCostContracts(unittest.TestCase):
    def test_own_passive_stock_is_retained_without_remote_owner_rows(self):
        from evaluation.controllers.sdmpc import omega_costs
        cfg,_=fixture('urban_only')
        cfg.network.sdmpc_cost_ownership={'storage:local':'F'}
        point=NS(control_area_response={'residence':[dict(dt_h=1.,inside_veh={
            'movement:M':2.,'storage:local':3.,'freeway:F':0.})]},
            control_area={'ttt_veh_h':5.})
        local,partition=omega_costs(point,cfg)
        self.assertEqual(set(local),{'S'})
        self.assertEqual(set(partition['costs']),{'S','PASSIVE_OMEGA'})
        self.assertEqual(partition['costs']['PASSIVE_OMEGA'],5.)
        self.assertEqual(partition['total_veh_h'],5.)

    def test_positive_remote_stock_cannot_enter_local_merit(self):
        from evaluation.controllers.sdmpc import omega_costs
        cfg,_=fixture('urban_only');cfg.network.sdmpc_cost_ownership={}
        point=NS(control_area_response={'residence':[dict(dt_h=1.,inside_veh={'freeway:F':1.})]},
            control_area={'ttt_veh_h':1.})
        with self.assertRaisesRegex(ValueError,'Remote stock'):omega_costs(point,cfg)



class PersistedPriceContracts(unittest.TestCase):
    def test_only_active_saved_price_is_loaded(self):
        import json
        import tempfile
        from pathlib import Path
        from evaluation.controllers import sdmpc
        from evaluation.controllers.sdmpc_regional_contracts import active_resources
        for mode in ('freeway_only','urban_only'):
            policy={'regional_prediction_prototype':mode,'budget_caps':True}
            mask=active_resources(mode)
            with tempfile.TemporaryDirectory(prefix='regional-price-') as directory:
                previous=Path(directory)/'previous.json';csv=previous.with_suffix('.csv')
                csv.write_text('offline fixture only',encoding='utf-8')
                Path(str(previous)+'.applied').write_text(
                    '750\n'+str(csv)+'\n'+str(csv.stat().st_size)+'\n',encoding='utf-16')
                saved=dict(schema=sdmpc.SCHEMA,sim_sec=750.,policy_sha256=sdmpc.policy_token(policy),
                    regional_mode=mode,active_resources=mask,next_prices_scaled=[7.,11.])
                def load():
                    previous.write_text(json.dumps({'metadata':{'sdmpc_state':saved}}),encoding='utf-8')
                    return sdmpc.load_prices(previous,NS(time_sec=900.,_sdmpc_interval_sec=150.),policy)[0]
                expected=load()
                inactive=0 if mode=='freeway_only' else 1
                saved['next_prices_scaled'][inactive]={'opposite_history':[1e99]}
                self.assertEqual(load().tolist(),expected.tolist())
                saved['next_prices_scaled'][1-inactive]+=3.
                self.assertNotEqual(load().tolist(),expected.tolist())
                saved['regional_mode']='urban_only' if mode=='freeway_only' else 'freeway_only'
                with self.assertRaisesRegex(ValueError,'information scope'):load()


if __name__=='__main__':unittest.main()
