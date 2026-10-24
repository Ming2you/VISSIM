"""Reverse derivatives must match forward physics, event choices and seeds."""
from pathlib import Path
import copy
import math
import pickle
import sys
import unittest
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_dual as fwd, sdmpc_tangent_reverse as rev
from evaluation.controllers.sdmpc_tangent_state import state_error


class ReverseTests(unittest.TestCase):
    def compare(self, fun, numbers):
        results = []
        for ad in (fwd, rev):
            trace = ad.Trace([.01]*len(numbers), track_stencils=False)
            x = [ad.Dual(v, {j: 1.}, trace) for j, v in enumerate(numbers)]
            outputs = fun(ad, x)
            jac = (trace.jacobian(outputs, 8) if ad is rev else
                   np.array([[ad.derivative(v).get(j, 0.) for j in range(len(numbers))] for v in outputs]))
            results.append(([ad.primal(v) for v in outputs], jac))
        np.testing.assert_allclose(results[0][0], results[1][0], rtol=0, atol=1e-13)
        np.testing.assert_allclose(results[0][1], results[1][1], rtol=1e-11, atol=1e-11)

    def test_chain_all_arithmetic_and_multiple_outputs(self):
        def run(ad, x):
            a, b = x
            q, speed, cost = 8., 35., 0.
            for k in range(80):
                speed += .07*(100.*ad.MathProxy.exp(-q/24.)-speed)+.02*a
                q += .12-.001*q*speed
                cost += (q**1.3+b/(k+1))/3600.
            return [cost, q, speed, a**b, 4./a, ad.MathProxy.log(a), ad.MathProxy.expm1(b),
                    ad.MathProxy.sqrt(a), ad.NumpyProxy.std([a, b]), a*b+b*a-a/a]
        self.compare(run, [20., .7])

    def test_selected_branches_capacity_cancellation_and_clocks(self):
        def run(ad, x):
            a, b = x
            x = ad.minimum(ad.maximum(a, b), 4.)
            return [x, abs(a-b), a % 3., a*0.+1., (a+2.)-a, ad.minimum(a,a), ad.maximum(4.,a)]
        for values in ([2.,3.], [3.,3.], [5.,1.], [0.,0.]):
            self.compare(run, values)

    def test_fsum_cancellation_retains_small_derivative(self):
        self.compare(lambda ad,x: [ad.MathProxy.fsum([x[0]*1e16, x[0], x[0]*-1e16])], [1.])

    def test_shared_seeds_and_zero_outputs(self):
        trace = rev.Trace([.1,.1], track_stencils=False)
        a = rev.Dual(4., {0: 2., 1: -3.}, trace)
        b = rev.Dual(1., {0: -2.}, trace)
        jac = trace.jacobian([a+b, a*b, 3.], 8)
        np.testing.assert_array_equal(jac, [[0.,-3.],[-6.,-3.],[0.,0.]])
        with self.assertRaises(ValueError):
            a*b

    def test_audit_pickle_and_copies_retain_tape_identity(self):
        trace = rev.Trace([.01], track_stencils=False)
        a = rev.Dual(4., {0:1.}, trace)
        y = a*a
        self.assertIs(copy.deepcopy(y), y)
        restored = pickle.loads(pickle.dumps({'x':y}))['x']
        self.assertIs(restored.trace, trace)
        self.assertEqual(state_error([16.], [restored]), 0.)
        np.testing.assert_array_equal(trace.jacobian([restored], 1), [[8.]])
        with self.assertRaises(ValueError):
            rev._restore_scalar('absent', 1, 1., 1, None)

    def test_mixed_tapes_and_implicit_float_rejected(self):
        a = rev.Dual(1., {0:1.}, rev.Trace([.1], track_stencils=False))
        b = rev.Dual(2., {0:1.}, rev.Trace([.1], track_stencils=False))
        with self.assertRaises(ValueError):
            a+b
        with self.assertRaises(TypeError):
            float(a)
        with self.assertRaises(ValueError):
            a.trace.jacobian([b])

    def test_backend_is_explicit_and_requires_tangent(self):
        from evaluation.controllers import sdmpc
        cfg = pickle.loads((ROOT/'diagnostics/sdmpc_sequence_20260921/three_blocks_h3/request.pickle').read_bytes())['owned'][0].cfg
        base = {'adapter': {'sdmpc':'proxlinear-v1', 'sdmpc_derivatives':'tangent-v1'}}
        self.assertNotIn('tangent_backend', sdmpc.configure(base, copy.deepcopy(cfg)))
        base['adapter']['sdmpc_tangent_backend'] = 'reverse-v1'
        self.assertEqual(sdmpc.configure(base,copy.deepcopy(cfg))['tangent_backend'], 'reverse-v1')
        base['adapter']['sdmpc_tangent_backend'] = 'bad'
        with self.assertRaises(ValueError):
            sdmpc.configure(base,copy.deepcopy(cfg))


if __name__ == '__main__':
    unittest.main()
