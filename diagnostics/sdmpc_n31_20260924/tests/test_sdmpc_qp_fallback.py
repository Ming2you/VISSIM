"""sdmpc.solve_qp fallback after an SLSQP failure (2026-09-25).

SDMPC v3b s31 stopped twice on SLSQP reports for feasible QPs:
- 1350 s (sdmpc31_v3b_s31): 'Inequality constraints incompatible', 21 moves / 14 rows, zero move feasible;
  data/qp_v3b_s31_1350_pfo_fail.npz (SLSQP fails on it again with one BLAS thread);
- 1500 s (sdmpc31_v3b_s31b): 'Positive directional derivative for linesearch', 12 moves / 22 rows, the box
  point violates G by 18; data/qp_v3b_s31b_1500_pfo_fail.npz.
data/qp_v3b_s31_1350_pfo_ok.npz is the QP solved just before the first one; data/qp_v3b_s31b_1500_ok_binding.npz
is a QP SLSQP solved at 1500 s with binding rows, on which a Dykstra that stopped on a repeated iterate alone
returned a point violating G by 4.1.
Only a failed SLSQP result takes the fallback (Dykstra projection); a successful one is returned unchanged.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import scipy.optimize

import n31_fixtures  # noqa: F401  (puts the worktree root on sys.path)
from evaluation.controllers import sdmpc

HERE = Path(__file__).resolve().parent / 'data'
FAIL_1350 = HERE / 'qp_v3b_s31_1350_pfo_fail.npz'
FAIL_1500 = HERE / 'qp_v3b_s31b_1500_pfo_fail.npz'
OK_1350 = HERE / 'qp_v3b_s31_1350_pfo_ok.npz'
OK_BINDING = HERE / 'qp_v3b_s31b_1500_ok_binding.npz'
OPTIONS = {'qp_iterations': 100, 'qp_tolerance': 1e-10}


def load(path):
    q = np.load(path)
    return (q['center'], q['gradient'], float(q['proximal']), q['lower'], q['upper'], q['G'], q['glo'], q['ghi'])


def objective(args, d):
    center, gradient, proximal = args[:3]
    return float(gradient@d + .5*proximal*np.sum((d-center)**2))


def reference(args):
    """trust-constr optimum, independent of SLSQP and of the fallback."""
    center, gradient, proximal, lower, upper, G, glo, ghi = args
    r = scipy.optimize.minimize(lambda d: objective(args, d), np.clip(center, lower, upper),
        jac=lambda d: gradient+proximal*(d-center), hess=lambda d: proximal*np.eye(len(d)),
        bounds=scipy.optimize.Bounds(lower, upper), constraints=[scipy.optimize.LinearConstraint(G, glo, ghi)],
        method='trust-constr', options={'gtol': 1e-12, 'xtol': 1e-14, 'maxiter': 5000})
    return r.x


def failing_slsqp(real):
    def fake(*args, **kwargs):
        result = real(*args, **kwargs)
        return SimpleNamespace(x=result.x, success=False, message='forced failure', nit=result.nit)
    return fake


class SolveQpFallbackTests(unittest.TestCase):
    def test_success_is_unchanged(self):
        d, info = sdmpc.solve_qp(*load(OK_1350), OPTIONS)
        self.assertTrue(info['success'])
        self.assertEqual(list(info), ['success', 'message', 'constraint_violation', 'iterations'])
        np.testing.assert_array_equal(d, np.load(OK_1350)['d'])

    def test_recorded_failures_now_solve_to_the_optimum(self):
        for path in (FAIL_1350, FAIL_1500):
            with self.subTest(path.name):
                args = load(path)
                d, info = sdmpc.solve_qp(*args, OPTIONS)
                self.assertTrue(info['success'])
                self.assertLessEqual(info['constraint_violation'], 1e-7)
                self.assertLessEqual(objective(args, d), objective(args, reference(args))+1e-8)

    def test_box_point_is_returned_when_it_satisfies_G(self):
        args = load(FAIL_1350)
        center, gradient, proximal, lower, upper = args[:5]
        with mock.patch.object(scipy.optimize, 'minimize', failing_slsqp(scipy.optimize.minimize)):
            d, info = sdmpc.solve_qp(*args, OPTIONS)
        self.assertEqual(info['fallback'], 'dykstra_projection')
        self.assertTrue(info['dykstra_converged'])
        self.assertLessEqual(info['dykstra_sweeps'], 2)
        np.testing.assert_allclose(d, np.clip(center-gradient/proximal, lower, upper), rtol=0, atol=1e-15)

    def test_binding_rows_are_projected_exactly(self):
        args = load(FAIL_1500)
        with mock.patch.object(scipy.optimize, 'minimize', failing_slsqp(scipy.optimize.minimize)):
            d, info = sdmpc.solve_qp(*args, OPTIONS)
        self.assertEqual(info['fallback'], 'dykstra_projection')
        self.assertTrue(info['dykstra_converged'])
        self.assertLessEqual(info['constraint_violation'], 1e-7)
        np.testing.assert_allclose(d, reference(args), rtol=0, atol=1e-6)

    def test_dykstra_does_not_stop_on_a_repeated_iterate(self):
        args = load(OK_BINDING)
        with mock.patch.object(scipy.optimize, 'minimize', failing_slsqp(scipy.optimize.minimize)):
            d, info = sdmpc.solve_qp(*args, OPTIONS)
        self.assertEqual(info['fallback'], 'dykstra_projection')
        self.assertLessEqual(info['constraint_violation'], 1e-7)
        self.assertGreater(info['dykstra_sweeps'], 5)
        np.testing.assert_allclose(d, np.load(OK_BINDING)['d'], rtol=0, atol=1e-5)
        self.assertLessEqual(objective(args, d), objective(args, np.load(OK_BINDING)['d'])+1e-10)

    def test_infeasible_still_fails(self):
        center, gradient, proximal, lower, upper, G, glo, ghi = load(FAIL_1350)
        glo, ghi = glo.copy(), ghi.copy()
        glo[0] = ghi[0] = 1e6   # no move reaches it
        d, info = sdmpc.solve_qp(center, gradient, proximal, lower, upper, G, glo, ghi, OPTIONS)
        self.assertFalse(info['success'])


if __name__ == '__main__':
    unittest.main()
