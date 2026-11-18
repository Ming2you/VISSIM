import os
import unittest
from unittest.mock import patch
import numpy as np
from evaluation.controllers import sdmpc, qp_experimental


class OfficialDefaultsTests(unittest.TestCase):
    def test_fixed_reduction_default_and_explicit_off(self):
        args=(np.zeros(2),np.array([-1.,0.]),1.,np.array([-1.,.5]),np.array([1.,.5]),
              np.empty((0,2)),np.array([]),np.array([]),{'qp_iterations':100,'qp_tolerance':1e-10})
        with patch.dict(os.environ,{},clear=True), patch.object(qp_experimental,'fixed_reduce',wraps=qp_experimental.fixed_reduce) as run:
            x, info=sdmpc.solve_qp(*args)
            self.assertTrue(info['success']); self.assertEqual(info['reduced_fixed'],1); self.assertEqual(run.call_count,1)
        with patch.dict(os.environ,{'SDMPC_QP_REDUCE':'0'},clear=True), patch.object(qp_experimental,'fixed_reduce',wraps=qp_experimental.fixed_reduce) as run:
            x, info=sdmpc.solve_qp(*args)
            self.assertTrue(info['success']); self.assertEqual(run.call_count,0)

    def test_bounded_fallback_default_rejects_nonconverged(self):
        from types import SimpleNamespace
        args=(np.zeros(1),np.zeros(1),1.,np.array([-1.]),np.array([1.]),
              np.array([[1.]]),np.array([-.5]),np.array([.5]),{'qp_iterations':10,'qp_tolerance':1e-10})
        failure=SimpleNamespace(x=np.zeros(1),success=False,message='forced',nit=1)
        with patch.dict(os.environ,{},clear=True), patch('scipy.optimize.minimize',return_value=failure), \
                patch.object(sdmpc,'_dykstra_projection',return_value=(np.zeros(1),3,False)):
            _,info=sdmpc.solve_qp(*args)
            self.assertFalse(info['success'])
            self.assertFalse(info['fallback_converged'])

if __name__=='__main__': unittest.main()
