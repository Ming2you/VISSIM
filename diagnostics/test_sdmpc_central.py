"""Price/band semantics, complete central rows, and existing-tape state AD."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_central as central
from evaluation.controllers import sdmpc_tangent_constraints as states
from evaluation.controllers import sdmpc_tangent_reverse as ad

OPTIONS=dict(active_tolerance=1e-8,stationarity_tolerance=1e-3,
             zero_jacobian_tolerance=1e-12,duplicate_decimals=12,np_step_veh=50.,nuf_step_veh_h=1000.)


class CentralTests(unittest.TestCase):
    def test_signed_initialization(self):
        for p in ([2.,3.],[2.,-3.],[0.,0.]):
            np.testing.assert_array_equal(central.signed_prices(central.initialize_duals(p)),p)

    def test_price_update_both_band_sides(self):
        d=central.update_duals(np.zeros(3),[-1.,.2],[0.,.04],1.)
        np.testing.assert_allclose(d,[0.,.16,0.])
        d=central.update_duals(np.zeros(3),[.1,-.2],[0.,.04],1.)
        np.testing.assert_allclose(d,[.1,0.,.16])

    def test_slack_band_does_not_create_price(self):
        np.testing.assert_array_equal(central.update_duals(np.zeros(3),[-1.,.02],[0.,.04],1.),np.zeros(3))

    def fit(self, physical, final, g=-2.):
        c=NS(lower=np.array([-10.]),upper=np.array([10.]),G=np.zeros((0,1)),glo=np.zeros(0),ghi=np.zeros(0))
        return central.recover((np.array([0.]),np.array([[g]]),np.zeros((2,1)),physical,final),
            np.array([.2]),[-5.,100.],np.array([0.,100.]),np.array([100.,1000.]),
            np.array([0.,40.]),c,OPTIONS,True)

    def test_physical_constraint_needed(self):
        p=dict(names=['physical/storage/upper'],values=[-.2],jacobian=[[1.]],scope='test')
        result=self.fit(p,dict(names=p['names'],values=[0.]))
        self.assertAlmostEqual(result['stationarity_inf'],0.)
        self.assertAlmostEqual(result['active_rows'][0]['multiplier'],2.)
        self.assertFalse(result['reference_matches_selected'])
        self.assertFalse(result['optimality_certified'])

    def test_final_actual_active_set_not_anchor(self):
        p=dict(names=['physical/storage/upper'],values=[0.],jacobian=[[1.]],scope='test')
        result=self.fit(p,dict(names=p['names'],values=[-1.]))
        self.assertAlmostEqual(result['stationarity_inf'],2.)

    def test_missing_physical_registry_fails(self):
        p=dict(names=['physical/storage/upper'],values=[0.],jacobian=[[1.]],scope='test')
        with self.assertRaises(ValueError):self.fit(p,dict(names=[],values=[]))

    def test_nonnegative_multipliers(self):
        p=dict(names=['physical/storage/upper'],values=[0.],jacobian=[[1.]],scope='test')
        result=self.fit(p,dict(names=p['names'],values=[0.]),g=2.)
        self.assertAlmostEqual(result['stationarity_inf'],2.)

    def test_actual_merge_target_can_move_down(self):
        result=central.next_budget([100.,5000.],dict(accepted_for_leader_direction=True,gradient_estimate=[0.,2.]),
            [[100.,5000.]],([0.,0.],[2400.,10000.]),OPTIONS)
        np.testing.assert_array_equal(result,[100.,4000.])

    def test_targets_not_duplicated_or_relabeled(self):
        r=central.next_budget([100.,5000.],dict(accepted_for_leader_direction=False),
            [[100.,5000.],[100.,4000.]],([0.,0.],[2400.,10000.]),OPTIONS)
        np.testing.assert_array_equal(r,[100.,6000.])


class StateDerivativeTests(unittest.TestCase):
    def test_same_tape_forward_matches_reverse(self):
        trace=ad.Trace([.1,.1]);a=ad.Dual(2.,{0:1.},trace);b=ad.Dual(3.,{1:1.},trace)
        values=[a*b,a*a+b,-a,b/2.,4.]
        expected=trace.jacobian(values,2)
        actual,work=states.jacobian(trace,values,2)
        np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-12)
        self.assertEqual(work['additional_traffic_rollouts'],0)
        self.assertEqual(work['method'],'forward_columns_on_existing_reverse_tape')

    def test_duplicate_and_constant_nodes(self):
        trace=ad.Trace([.1,.1]);a=ad.Dual(2.,{0:1.},trace)
        actual,work=states.jacobian(trace,[a,a,0.],2)
        np.testing.assert_array_equal(actual,[[1.,0.],[1.,0.],[0.,0.]])
        self.assertEqual(work['sweeps'],1)

    def test_capture_only_requested_endpoints(self):
        registry=states.Registry([150.]);ledger=NS(_response_stamp=lambda:dict(end_sec=149.))
        registry.bound(ledger,'queue','x',2.,5.)
        self.assertFalse(registry.rows)
        ledger._response_stamp=lambda:dict(end_sec=150.)
        registry.bound(ledger,'queue','x',2.,5.)
        self.assertEqual(sorted(registry.rows.values()),[-3.,-2.])

    def test_duplicate_state_row_fails(self):
        r=states.Registry([150.]);r.add('x',0.)
        with self.assertRaises(ValueError):r.add('x',0.)

    def test_incomplete_horizon_fails(self):
        with self.assertRaises(ValueError):states.Registry([150.]).finish([],None)


if __name__=='__main__':unittest.main()
