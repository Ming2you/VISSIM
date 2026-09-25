"""sdmpc.solve_qp fallback after an SLSQP failure (2026-09-25).

SDMPC v3b s31 stopped at the 1350 s decision: the PFO own-cost QP (21 moves, 14 rows) returned
'Inequality constraints incompatible' although the zero move is feasible; the same inputs solve in
another process. data/qp_v3b_s31_1350_pfo_fail.npz holds those inputs (dumped from the replay; SLSQP
fails on them again with one BLAS thread). data/qp_v3b_s31_1350_pfo_ok.npz is the QP solved just before it.
Only a failed SLSQP result takes the fallback; a successful one is returned unchanged.
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

DATA = Path(__file__).resolve().parent / 'data' / 'qp_v3b_s31_1350_pfo_fail.npz'
DATA_OK = Path(__file__).resolve().parent / 'data' / 'qp_v3b_s31_1350_pfo_ok.npz'
OPTIONS = {'qp_iterations': 100, 'qp_tolerance': 1e-10}


def load(path=DATA):
    q = np.load(path)
    return (q['center'], q['gradient'], float(q['proximal']), q['lower'], q['upper'], q['G'], q['glo'], q['ghi'])


def failing_first(real):
    calls = []
    def fake(*args, **kwargs):
        result = real(*args, **kwargs)
        calls.append(result)
        if len(calls) == 1:
            return SimpleNamespace(x=result.x, success=False, message='Inequality constraints incompatible', nit=6)
        return result
    return fake, calls


class SolveQpFallbackTests(unittest.TestCase):
    def test_success_is_unchanged(self):
        d, info = sdmpc.solve_qp(*load(DATA_OK), OPTIONS)
        self.assertTrue(info['success'])
        self.assertEqual(list(info), ['success', 'message', 'constraint_violation', 'iterations'])
        np.testing.assert_array_equal(d, np.load(DATA_OK)['d'])

    def test_the_1350_qp_now_solves(self):
        center, gradient, proximal, lower, upper, G, glo, ghi = load()
        d, info = sdmpc.solve_qp(center, gradient, proximal, lower, upper, G, glo, ghi, OPTIONS)
        self.assertTrue(info['success'])
        self.assertLessEqual(info['constraint_violation'], 1e-7)
        np.testing.assert_allclose(d, np.clip(center-gradient/proximal, lower, upper), atol=1e-9)

    def test_failed_slsqp_takes_the_exact_box_projection(self):
        center, gradient, proximal, lower, upper, G, glo, ghi = load()
        fake, calls = failing_first(scipy.optimize.minimize)
        with mock.patch.object(scipy.optimize, 'minimize', fake):
            d, info = sdmpc.solve_qp(center, gradient, proximal, lower, upper, G, glo, ghi, OPTIONS)
        self.assertEqual(len(calls), 1)
        self.assertTrue(info['success'])
        self.assertEqual(info['fallback'], 'box_projection')
        np.testing.assert_array_equal(d, np.clip(center-gradient/proximal, lower, upper))
        self.assertLessEqual(info['constraint_violation'], 1e-7)

    def test_binding_rows_restart_from_zero(self):
        center, gradient, proximal, lower, upper, G, glo, ghi = load()
        box = np.clip(center-gradient/proximal, lower, upper)
        row = int(np.argmax(np.abs(G@box)))
        ghi, glo = ghi.copy(), glo.copy()
        ghi[row] = glo[row] = 0.   # an equality row the box point violates
        ghi[row] = 0.5*abs(G[row]@box) if G[row]@box > 0 else ghi[row]
        glo[row] = -0.5*abs(G[row]@box) if G[row]@box < 0 else -1.
        fake, calls = failing_first(scipy.optimize.minimize)
        with mock.patch.object(scipy.optimize, 'minimize', fake):
            d, info = sdmpc.solve_qp(center, gradient, proximal, lower, upper, G, glo, ghi, OPTIONS)
        self.assertEqual(len(calls), 2)
        self.assertTrue(info['success'])
        self.assertEqual(info['fallback'], 'slsqp_restart_from_zero')
        self.assertLessEqual(info['constraint_violation'], 1e-7)

    def test_infeasible_still_fails(self):
        center, gradient, proximal, lower, upper, G, glo, ghi = load()
        glo = glo.copy(); glo[0] = ghi[0] = 1e6   # no move reaches it
        d, info = sdmpc.solve_qp(center, gradient, proximal, lower, upper, G, glo, ghi.copy(), OPTIONS)
        self.assertFalse(info['success'])


if __name__ == '__main__':
    unittest.main()
