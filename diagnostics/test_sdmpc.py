"""SDMPC 이식의 물리 제약·회계·실행 승인 경계를 검사한다."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np

from evaluation.controllers import sdmpc


class SDMPCTests(unittest.TestCase):
    def test_discrete_stencil_uses_an_executable_vsl_step(self):
        coord = sdmpc.Coordinates.__new__(sdmpc.Coordinates)
        coord.axes = [{'kind':'vsl','scale':120.,'fd':10./120.,
                       'allowed':[80.,100.,120.],'reference_value':120.}]
        coord.lower, coord.upper = np.array([-40./120.]), np.array([0.])
        coord.G = np.empty((0,1)); coord.glo = coord.ghi = np.array([])
        np.testing.assert_allclose(coord.stencil(np.array([0.]),0), [-20./120.,0.])
        np.testing.assert_allclose(coord.stencil(np.array([-20./120.]),0), [-20./120.,20./120.])
        coord.axes = [{'kind':'meter','scale':10.,'fd':.2,
                       'allowed':[8.,9.,10.],'reference_value':10.}]
        coord.lower = np.array([-.2])
        np.testing.assert_allclose(coord.stencil(np.array([0.]),0), [-.2,0.])

    def test_gradient_cache_ignores_only_np_with_exact_anchor_response(self):
        cache = sdmpc.GradientCache()
        z, costs, resources = np.array([1.]), np.array([2.]), np.array([3., 4.])
        action = NS(N_P_star=100., N_UF_star=4., green_times={'SC1_p1': 20.})
        key = cache.key(z, action, costs, resources)
        cache.put(key, 100., np.array([[5.]]), np.array([[6.], [7.]]))
        action.N_P_star = 200.
        self.assertEqual(cache.key(z, action, costs, resources), key)
        grad, _ = cache.get(key, 200.)
        grad[0, 0] = 999.
        self.assertEqual(cache.get(key, 200.)[0][0, 0], 5.)
        for c, r in ((costs+1e-10, resources), (costs, resources+1e-10)):
            self.assertIsNone(cache.get(cache.key(z, action, c, r), 200.))
        action.N_UF_star += 1.
        self.assertNotEqual(cache.key(z, action, costs, resources), key)
        action.N_UF_star -= 1.
        action.green_times['SC1_p1'] += 1.
        self.assertNotEqual(cache.key(z, action, costs, resources), key)

    def test_omega_partition_excludes_outside_and_keeps_passive(self):
        cfg = NS(network=NS(signals=('SC1',), freeway_links=('FW_E',),
            sdmpc_cost_ownership={'movement:m': 'SC1', 'freeway:FW_E': 'FW_E'}))
        point = NS(control_area={'ttt_veh_h': 3.}, control_area_response={'residence': [
            {'dt_h': .1, 'inside_veh': {'movement:m': 10., 'freeway:FW_E': 15., 'storage:unowned': 5.},
             'model_stock_veh': {'movement:m': 1000., 'freeway:FW_E': 1500., 'storage:unowned': 500.}}]})
        local, receipt = sdmpc.omega_costs(point, cfg)
        self.assertEqual(local['SC1']['cost'], 1.)
        self.assertEqual(local['FW_E']['cost'], 1.5)
        self.assertEqual(receipt['costs'][sdmpc.PASSIVE], .5)
        point.control_area['ttt_veh_h'] = 4.
        with self.assertRaises(ValueError): sdmpc.omega_costs(point, cfg)

    def test_resource_projection_preserves_coupled_green_and_merge(self):
        opts = {'qp_iterations': 100, 'qp_tolerance': 1e-12}
        # 도시 두 현시의 보존 및 8개 미터 중 두 미터의 합류 교환을 모사.
        G = np.array([[1., 1., 0., 0.], [0., 0., 2., 1.]])
        center = np.array([.3, -.1, -.2, .1])
        step, proof = sdmpc.solve_qp(center, np.zeros(4), 1., -np.ones(4), np.ones(4),
            G, np.zeros(2), np.zeros(2), opts)
        self.assertTrue(proof['success'])
        np.testing.assert_allclose(G@step, 0., atol=1e-9)
        self.assertLess(step[2], 0.)
        self.assertGreater(step[3], 0.)

    def test_boundary_price_requires_applied_previous_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'action_000900.json'
            policy = {'key': 'value'}
            saved = {'schema': sdmpc.SCHEMA, 'sim_sec': 900.,
                     'policy_sha256': sdmpc.token(policy), 'next_prices_scaled': [2., -3.]}
            path.write_text(json.dumps({'metadata': {'sdmpc_state': saved}}), encoding='utf-8')
            csv = path.with_suffix('.csv'); csv.write_text('command', encoding='utf-8')
            state = NS(time_sec=1050., _sdmpc_interval_sec=150.)
            with self.assertRaisesRegex(ValueError, 'application receipt'):
                sdmpc.load_prices(path, state, policy)
            ack = Path(str(path)+'.applied')
            ack.write_text('900\n'+str(csv)+'\n'+str(csv.stat().st_size)+'\n', encoding='utf-16')
            prices, receipt = sdmpc.load_prices(path, state, policy)
            np.testing.assert_array_equal(prices, [2., -3.])
            self.assertTrue(receipt['committed'])
            csv.write_text('different command', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'context mismatch'):
                sdmpc.load_prices(path, state, policy)

    def test_absent_switch_does_not_modify_cfg(self):
        cfg = NS()
        self.assertIsNone(sdmpc.configure({}, cfg))
        self.assertEqual(vars(cfg), {})

    def test_no_control_and_warmup_keep_sdmpc_disabled(self):
        cfg = NS()
        self.assertIsNone(sdmpc.configure({'adapter': {'sdmpc': 'proxlinear-v1'}}, cfg, 'no-control'))
        self.assertEqual(vars(cfg), {})


if __name__ == '__main__':
    unittest.main()
