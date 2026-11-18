import os,sys,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np

from evaluation.controllers import sdmpc,qp_experimental
OPT={'qp_iterations':100,'qp_tolerance':1e-10}

class QPTests(unittest.TestCase):
 def solve(self,args,**env):
  keys=('SDMPC_QP_REDUCE','SDMPC_QP_FALLBACK_LIMIT','SDMPC_QP_SOLVER')
  with patch.dict(os.environ,{**{k:'' for k in keys},**env}):return sdmpc.solve_qp(*args)
 def test_fixed_nonzero_and_rows(self):
  args=(np.zeros(3),np.array([-1.,0.,-2.]),2.,np.array([-2.,.5,-2.]),np.array([2.,.5,2.]),
        np.array([[1.,2.,1.],[0.,1.,0.],[0.,0.,0.]]),np.array([2.,.5,-1.]),np.array([2.,.5,1.]),OPT)
  a,ai=self.solve(args);b,bi=self.solve(args,SDMPC_QP_REDUCE='1')
  self.assertTrue(ai['success']);self.assertTrue(bi['success']);np.testing.assert_allclose(a,b,atol=1e-6);self.assertEqual(bi['reduced_fixed'],1)
 def test_all_fixed_and_empty(self):
  for low,high,expected in [(1.,1.,True),(2.,3.,False)]:
   args=(np.zeros(2),np.zeros(2),1.,np.array([.5,.5]),np.array([.5,.5]),np.array([[1.,1.]]),np.array([low]),np.array([high]),OPT)
   _,r=self.solve(args,SDMPC_QP_REDUCE='1');self.assertEqual(r['success'],expected)
  args=(np.zeros(2),np.zeros(2),1.,np.zeros(2),np.zeros(2),np.empty((0,2)),np.array([]),np.array([]),OPT)
  _,r=self.solve(args,SDMPC_QP_REDUCE='1');self.assertTrue(r['success'])
 def test_fixed_infeasible_row(self):
  args=(np.zeros(2),np.zeros(2),1.,np.array([1.,-1.]),np.array([1.,1.]),np.array([[1.,0.]]),np.array([2.]),np.array([3.]),OPT)
  _,r=self.solve(args,SDMPC_QP_REDUCE='1');self.assertFalse(r['success'])
 def test_random_feasible_highs(self):
  rng=np.random.default_rng(7)
  for _ in range(20):
   n=8;G=rng.normal(size=(5,n));lower=np.full(n,-1.);upper=np.full(n,1.);lower[0]=upper[0]=.2
   witness=np.zeros(n);witness[0]=.2;gw=G@witness;lo=gw-.3;hi=gw+.3
   args=(np.zeros(n),rng.normal(size=n),2.,lower,upper,G,lo,hi,OPT)
   a,ai=self.solve(args,SDMPC_QP_REDUCE='1');b,bi=self.solve(args,SDMPC_QP_REDUCE='1',SDMPC_QP_SOLVER='highs')
   self.assertTrue(ai['success']);self.assertTrue(bi['success'])
   f=lambda x:args[1]@x+np.sum((x-args[0])**2)
   self.assertLess(abs(f(a)-f(b)),1e-6);self.assertLessEqual(qp_experimental.violation(b,lower,upper,G,lo,hi),1e-7)
 def test_highs_after_scipy_linprog_scheduler(self):
  from scipy.optimize import linprog
  self.assertTrue(linprog([1.],bounds=[(-1.,1.)]).success)
  args=(np.zeros(1),np.array([-1.]),1.,np.array([-1.]),np.array([1.]),np.empty((0,1)),np.array([]),np.array([]),OPT)
  _,r=self.solve(args,SDMPC_QP_SOLVER='highs');self.assertTrue(r['success'])
 def test_highs_failure_uses_original(self):
  args=(np.zeros(1),np.array([-1.]),1.,np.array([-1.]),np.array([1.]),np.empty((0,1)),np.array([]),np.array([]),OPT)
  with patch.object(qp_experimental,'highs_qp',return_value=(np.zeros(1),{'success':False,'message':'time limit'})):
   _,r=self.solve(args,SDMPC_QP_SOLVER='highs')
  self.assertTrue(r['success']);self.assertEqual(r['experimental_solver_fallback'],'original_slsqp_dykstra')
 def test_limited_nonconvergence_is_not_accepted(self):
  args=(np.zeros(1),np.array([-.1]),1.,np.array([-1.]),np.array([1.]),np.array([[1.]]),np.array([-.5]),np.array([.5]),OPT)
  fail=SimpleNamespace(x=np.zeros(1),success=False,message='forced failure',nit=1)
  with patch('scipy.optimize.minimize',return_value=fail),patch.object(sdmpc,'_dykstra_projection',return_value=(np.zeros(1),3,False)):
   _,r=self.solve(args,SDMPC_QP_FALLBACK_LIMIT='1')
  self.assertFalse(r['success'])
 def test_stagnation_is_failure_not_convergence(self):
  with patch.dict(os.environ,{'SDMPC_QP_FALLBACK_LIMIT':'1','SDMPC_QP_FALLBACK_STAGNATION':'1',
                              'SDMPC_QP_FALLBACK_SWEEPS':'5000','SDMPC_QP_FALLBACK_SECONDS':'30'}):
   _,sweeps,converged=sdmpc._dykstra_projection(np.zeros(1),np.ones(1),-np.ones(1),np.ones(1),
                                                np.zeros((1,1)),np.ones(1),np.array([np.inf]))
  self.assertFalse(converged);self.assertEqual(sweeps,1000)

if __name__=='__main__':unittest.main()

