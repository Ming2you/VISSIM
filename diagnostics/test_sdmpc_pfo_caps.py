"""Upper budgets allow undersupply and never introduce a lower-flow price."""
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import unittest
import copy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_central as central
from diagnostics.test_sdmpc_central import OPTIONS
from diagnostics.test_shared_joint_price_quantity import fixture, quantities, api
from evaluation.controllers import sdmpc_budget, sdmpc_pfo
from evaluation.controllers.sdmpc_tangent_surrogate import Query, token, MODEL
from diagnostics.test_sdmpc_surrogate_reuse import receipt


def warm_fixture(start=900.,rate=150.):
    f,a,r,_=fixture();n=f.cfg.network
    del n.signal_cycle_length  # The fixture's local lambda is not picklable.
    n.ramps=tuple('RM'+str(i) for i in range(8))
    n.ramp_to_freeway={m:('FW_E' if i<4 else 'FW_W') for i,m in enumerate(n.ramps)}
    n.physical_ramp_branches={'ramps':{m:{'to_model_link':o} for m,o in n.ramp_to_freeway.items()}}
    n.sdmpc_options=dict(budget_caps=True,pfo_each_interval=True,surrogate_reuse=True)
    f.cfg.mpc=NS(horizon_steps=1)
    for owner,model in f._local_freeway_models.items():
        model.owned_ramps=[m for m in n.ramps if n.ramp_to_freeway[m]==owner]
    a.ramp_metering={m:2000. for m in n.ramps};a.diagnostics={}
    r['freeway_frames']=[dict(start_sec=900.,end_sec=902.,actual_ramp_release_veh_h={m:rate for m in n.ramps})]
    q=quantities(f,r)
    for key in ('provenance','predicted_ramp_merge'):
        q[key]['start_sec']+=start-900.;q[key]['end_sec']+=start-900.
    state=NS(time_sec=start,lane_freeway_runtime=NS())
    def run(request):
        out=receipt(request);item=out['surrogate_prediction'];item.pop('response_token')
        item.update(quantities=copy.deepcopy(q),conditional_model_feasibility_witness=True,
            model_constraint_coverage=dict(complete=True,conditional_model_feasibility_witness=True),
            resource_summary=dict(max_exceedance_veh=0.))
        item['response_token']=token(item)
        return out
    query=Query(dict(owned=(f,state,a,None),runtime={},bootstrap={},horizon=1,axes=[{}]),
        lambda *a:None,lambda *a,**k:None,runner=run)
    return query,f,state,a


class WarmBudgetTests(unittest.TestCase):
    def test_each_interval_uses_its_achieved_quantities(self):
        for start,rate in ((900.,150.),(1050.,200.)):
            q,f,s,a=warm_fixture(start,rate)
            item=q.evaluate([a],derivatives=True)[0]
            b,proof=sdmpc_budget.initialize(f,s,a,item,dict(shared_tolerance=1e-7))
            self.assertEqual((b.N_P_star,b.N_UF_star),(-68.,rate*8))
            self.assertEqual(proof['start_sec'],start)
            self.assertFalse(proof['previous_budget_reused'])
            self.assertEqual(b.ramp_metering,a.ramp_metering)
            self.assertEqual(a.N_P_star,123.)

    def test_selected_pfo_ad_reused_without_new_rollout(self):
        q,f,s,a=warm_fixture();item=q.evaluate([a],derivatives=True)[0]
        b,_=sdmpc_budget.initialize(f,s,a,item,dict(shared_tolerance=1e-7))
        q.bind_warm_budget(a,b,dict(shared_tolerance=1e-7))
        bound=q.evaluate([b],derivatives=True)[0];ad=q.derivative(b)
        self.assertEqual(q.stats()['total_rollouts'],1)
        self.assertEqual(bound['objective_veh_h'],item['objective_veh_h'])
        self.assertIn('warm_budget_binding',ad['candidate_prediction_reused'])
        c=copy.deepcopy(b);c.N_UF_star+=1.;q.evaluate([c])
        self.assertEqual(q.stats()['total_rollouts'],2)

    def test_arbitrary_budget_or_control_and_repeat_binding_rejected(self):
        for field in ('N_P_star','N_UF_star','physical'):
            q,f,s,a=warm_fixture();item=q.evaluate([a],derivatives=True)[0]
            b,_=sdmpc_budget.initialize(f,s,a,item,dict(shared_tolerance=1e-7))
            if field=='physical':b.green_times['SC1_p1']+=1.
            else:setattr(b,field,getattr(b,field)+1.)
            with self.assertRaises(ValueError):q.bind_warm_budget(a,b,dict(shared_tolerance=1e-7))
        q,f,s,a=warm_fixture();item=q.evaluate([a],derivatives=True)[0]
        b,_=sdmpc_budget.initialize(f,s,a,item,dict(shared_tolerance=1e-7))
        q.bind_warm_budget(a,b,dict(shared_tolerance=1e-7))
        with self.assertRaises(ValueError):q.bind_warm_budget(a,b,dict(shared_tolerance=1e-7))

    def test_invalid_physical_witness_cannot_initialize(self):
        q,f,s,a=warm_fixture();item=q.evaluate([a],derivatives=True)[0]
        item['model_constraint_coverage']['complete']=False
        with self.assertRaises(ValueError):sdmpc_budget.initialize(f,s,a,item,dict(shared_tolerance=1e-7))

    def test_signed_achieved_np_is_not_clipped_to_old_grid(self):
        self.assertEqual(sdmpc_budget.search_limits([-68.,1200.],[100.,2400.],16000.),([-68.,0.],[2400.,16000.]))


class OwnPfoTests(unittest.TestCase):
    def run_quadratic(self, passive=0., initial=1.):
        from src.models.state import ControlAction
        class Coord:
            owners=('A','B');axes=[dict(owner='A'),dict(owner='B')]
            lower=np.zeros(2);upper=np.ones(2)*2.;G=np.zeros((0,2));glo=np.zeros(0);ghi=np.zeros(0)
            def encode(self,a):return np.array([a.green_times['A'],a.green_times['B']])
            def decode(self,z,a):
                b=a.copy();b.green_times=dict(A=float(z[0]),B=float(z[1]));return b
            def validate(self,a):assert np.all(self.encode(a)>=0.)
        coord=Coord();seen=[]
        def evaluate(actions,**kw):
            rows=[]
            for a in actions:
                x,y=coord.encode(a);p=passive*(x+y)
                rows.append(dict(sdmpc_omega_partition=dict(costs=dict(A=x*x,B=y*y,PASSIVE_OMEGA=p)),
                    objective_veh_h=x*x+y*y+p,conditional_model_feasibility_witness=True,
                    model_constraint_coverage=dict(complete=True,conditional_model_feasibility_witness=True),
                    resource_summary=dict(max_exceedance_veh=0.)))
            return rows
        def derivative(a):
            x,y=coord.encode(a);seen.append((x,y));cost=list(evaluate([a])[0]['sdmpc_omega_partition']['costs'].values())
            return dict(costs=cost,resources=[0.,0.],cost_jacobian=[[2*x,0.],[0.,2*y],[passive,passive]],
                resource_jacobian=np.zeros((2,2)),fallback_reasons={},surrogate_evaluation='ad',
                primal_audit_performed=False,complete_primal_state_match=False,max_primal_state_error=None,
                surrogate_prediction=dict(prediction_model=MODEL))
        policy=dict(pfo_cap_options=dict(max_iterations=2),proximal=10.,qp_iterations=100,
            qp_tolerance=1e-10,tangent_primal_abs_tolerance=1e-8,line_search_steps=3,objective_tolerance=1e-7)
        a=ControlAction(green_times=dict(A=initial,B=initial),N_P_star=-999.,N_UF_star=0.)
        result=sdmpc_pfo.solve(a,coord,policy,dict(shared_tolerance=1e-7),evaluate,derivative,
            lambda *a:np.zeros(2),lambda *a:None,lambda *a,**kw:None)
        return result,seen

    def test_own_derivatives_refresh_and_passive_cost_does_not_steer_pfo(self):
        a,seen=self.run_quadratic();b,_=self.run_quadratic(passive=-1e6)
        self.assertEqual(a[0].green_times,b[0].green_times)
        self.assertNotEqual(seen[0],seen[1])
        self.assertEqual(a[2]['accepted_iterations'],2)
        self.assertFalse(a[2]['converged'])
        self.assertFalse(a[2]['prices_used'])

    def test_next_call_restarts_from_current_applied_control(self):
        first,_=self.run_quadratic(initial=1.);second,seen=self.run_quadratic(initial=1.5)
        self.assertEqual(seen[0],(1.5,1.5))
        self.assertNotEqual(first[0].green_times,second[0].green_times)


class CapsTests(unittest.TestCase):
    def test_slack_merge_has_no_lower_price(self):
        updated=central.update_duals(np.zeros(2),[-1.,-3.],[0.,0.],1.,caps=True)
        np.testing.assert_array_equal(updated,[0.,0.])
        np.testing.assert_array_equal(central.signed_prices(updated),updated)

    def test_excess_updates_both_nonnegative_prices(self):
        np.testing.assert_array_equal(central.update_duals([0.,0.],[1.,2.],[0.,0.],1.,caps=True),[1.,2.])
        np.testing.assert_array_equal(central.update_duals([1.,2.],[-2.,-3.],[0.,0.],1.,caps=True),[0.,0.])

    def test_projection_has_no_merge_lower_bound(self):
        lo,hi=central.qp_bounds([-2.,-3.],[0.,0.],caps=True)
        self.assertTrue(np.isneginf(lo).all())
        np.testing.assert_array_equal(hi,[2.,3.])
        self.assertEqual(central.qp_bounds([-2.,-3.],[0.,.04])[0][1],2.96)

    def test_central_cap_gradient_and_absence_of_lower_row(self):
        physical=dict(names=[],jacobian=np.zeros((0,1)),scope='test')
        coord=NS(lower=np.array([-10.]),upper=np.array([10.]),G=np.zeros((0,1)),glo=[],ghi=[])
        result=central.recover((np.array([0.]),np.array([[-2.]]),np.array([[0.],[1.]]),physical,dict(names=[],values=[])),
            np.array([0.]),[-1.,100.],np.array([0.,100.]),np.ones(2),np.zeros(2),coord,OPTIONS,True,caps=True)
        self.assertEqual(result['constraints'],4)
        self.assertEqual(result['active_rows'][0]['name'],'budget/NUF/upper')
        np.testing.assert_array_equal(result['gradient_estimate'],[0.,-2.])

    def test_actual_merge_caps_not_command_sum(self):
        f,a,r,_=fixture();n=f.cfg.network
        n.ramps=tuple('RM'+str(i) for i in range(8))
        n.ramp_to_freeway={m:('FW_E' if i<4 else 'FW_W') for i,m in enumerate(n.ramps)}
        n.physical_ramp_branches={'ramps':{m:{'to_model_link':o} for m,o in n.ramp_to_freeway.items()}}
        for owner,model in f._local_freeway_models.items():
            model.owned_ramps=[m for m in n.ramps if n.ramp_to_freeway[m]==owner]
        a.ramp_metering={m:2000. for m in n.ramps}
        r['freeway_frames']=[dict(start_sec=900.,end_sec=902.,actual_ramp_release_veh_h={m:150. for m in n.ramps})]
        q=quantities(f,r)
        def check(target,mode='cap'):
            return api.shared_quantity_constraints(f,a,q,start_sec=900.,horizon_steps=1,np_mode='cap',
                target_np_veh=0.,np_tolerance_veh=0.,nuf_mode=mode,target_nuf_veh_h=target,nuf_tolerance_veh_h=1e-7)
        self.assertTrue(check(5000.)['feasible'])
        self.assertTrue(check(1200.)['feasible'])
        self.assertFalse(check(1100.)['feasible'])
        self.assertFalse(check(5000.,'equality')['feasible'])
        self.assertEqual(check(5000.)['nuf']['actual'],1200.)
        self.assertEqual(check(5000.)['nuf']['violation'],0.)


if __name__=='__main__':unittest.main()
