"""Offline regression tests; never opens VISSIM or edits the running adapter."""
from __future__ import annotations

import copy
import importlib.util
import json
import math
import multiprocessing
from pathlib import Path
import pickle
import sys
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]

from evaluation.controllers.freeway_fd import (  # noqa: E402
    FDParameters, SegmentVSL, cell_parameters, install_freeway_fd_runtime,
)


def _spawn_fd_probe(cfg, connection):
    """Replicate price-worker hook order in a fresh Windows spawn process."""
    try:
        spec = importlib.util.spec_from_file_location(
            "fd_worker_adapter", ROOT / "evaluation/controllers/vissim_stackelberg_adapter.py")
        adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(adapter)
        from src.controllers import wu_faithful_follower as w
        from src.models import metanet as mn, state as st
        adapter.install_freeway_vsl_zones(cfg, None)
        adapter.install_freeway_segment_runtime(cfg)
        install_freeway_fd_runtime(adapter, w, cfg, None)
        action = st.ControlAction.uncontrolled(cfg)
        action.vsl["FW_E__seg5"] = 100.0
        value = st.segment_vsl(action, "FW_E", 9, cfg)
        net = cfg.network
        speed = mn.effective_desired_speed_kmh(
            5.0, net.v_free, net.rho_crit, value, net.alpha_vsl, True,
            net.metanet_a_m, True, net.rho_max, net.rho_crit_two_branch)
        connection.send((speed, mn.effective_rho_crit(net, value)))
    except BaseException as error:
        connection.send(repr(error))
    finally:
        connection.close()


class FreewayFDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "fd_test_adapter", ROOT / "evaluation/controllers/vissim_stackelberg_adapter.py")
        cls.adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.adapter)
        a = cls.adapter
        cls.tuning = a.load_optional_json(str(ROOT / "evaluation/configs/n21i_i1_20260909.json"))
        calibration = a.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
        calibration = a.deep_update(dict(calibration), cls.tuning.get("calibration_override") or {})
        a.install_config_switches(cls.tuning)
        cls.cfg = a.build_config(ROOT / "vendor/NumSim-mine", 150, 5400, "wu-link",
                                calibration, cls.tuning, local_observation=True, flagship=True)
        a.install_freeway_segment_lanes(cls.cfg, cls.tuning, a.load_optional_json(str(ROOT / cls.tuning["mapping_json"])))
        a.install_freeway_lane_drop(cls.cfg, cls.tuning)
        a.install_freeway_two_branch_fd(cls.cfg, cls.tuning)
        a.install_freeway_vsl_zones(cls.cfg, cls.tuning)
        a.install_freeway_segment_runtime(cls.cfg)
        from src.models import metanet, state
        from src.models.demand import DemandStep
        from src.controllers import wu_faithful_follower as w, local_freeway_plant
        cls.mn, cls.st, cls.w, cls.local = metanet, state, w, local_freeway_plant
        cls.DemandStep = DemandStep
        cls.controller = a.build_priced_wu_link_controller(cls.cfg, cls.tuning)
        cls.off_cfg = copy.deepcopy(cls.cfg)
        cls.off_cfg.network.vsl_fd_two_branch = False
        cls.off_baseline = cls._global_rollout(cls.off_cfg)
        before = (state.segment_vsl, metanet.effective_desired_speed_kmh,
                  metanet.effective_rho_crit, metanet.select_anticipation_nu,
                  w.WuFaithfulFollower._local_ramp_release)
        cls.off_install = install_freeway_fd_runtime(a, w, cls.off_cfg, {})
        cls.off_identity_unchanged = before == (
            state.segment_vsl, metanet.effective_desired_speed_kmh,
            metanet.effective_rho_crit, metanet.select_anticipation_nu,
            w.WuFaithfulFollower._local_ramp_release)
        cls.metadata = install_freeway_fd_runtime(a, w, cls.cfg, cls.tuning)

    @classmethod
    def _global_rollout(cls, cfg):
        state = cls.st.TrafficState.initial(cfg)
        action = cls.st.ControlAction.uncontrolled(cfg)
        action.vsl.update({"FW_E": 100.0, "FW_W": 80.0})
        for link in cfg.network.freeway_links:
            state.freeway_density[link] = [10.0 + i for i in range(21)]
            state.freeway_speed[link] = [70.0] * 21
        state.ramp_queue = {r: 40.0 for r in cfg.network.ramps}
        demand = cls.DemandStep({"FW_E": 3000.0, "FW_W": 3000.0}, {}, {})
        for _ in range(4):
            cls.mn.freeway_substep(state, action, demand, cfg)
        return (state.freeway_density, state.freeway_speed, state.ramp_queue,
                state.mainline_origin_queue, state.freeway_effective_lanes)

    def _token(self, index, cap, cfg=None):
        cfg = cfg or self.cfg
        action = self.st.ControlAction.uncontrolled(cfg)
        # E8/E9 share head5; E14 belongs to head10 in the real i1 mapping.
        heads = cfg.network.freeway_vsl_zone_head_of_cell["FW_E"]
        action.vsl[f"FW_E__seg{heads[index]}"] = cap
        return self.st.segment_vsl(action, "FW_E", index, cfg)

    def _desired(self, rho, token, cfg=None):
        cfg = cfg or self.cfg
        net = cfg.network
        return self.mn.effective_desired_speed_kmh(
            rho, net.v_free, net.rho_crit, token, net.alpha_vsl,
            float(token) < max(cfg.freeway_follower.vsl_set) - 0.5,
            net.metanet_a_m, True, net.rho_max, net.rho_crit_two_branch)

    def test_disabled_identity_and_exact_rollout(self):
        self.assertTrue(self.off_identity_unchanged)
        self.assertEqual(self.off_install["freeway_fd_consistent_enabled"], 0.0)
        self.assertEqual(self.off_baseline, self._global_rollout(self.off_cfg))

    def test_actual_link_follower_route(self):
        follower = self.controller.nash_solver
        self.assertTrue(follower.segment_agents)
        self.assertTrue(follower.metering_in_gne)
        self.assertEqual(type(follower)._solve_freeway_segment_agents.__module__,
                         "src.controllers.priced_wu_link_controller")

    def test_cell_speed_monotone_and_branch_continuous(self):
        for index in (8, 9, 14):
            previous_speed = math.inf
            previous_critical = 0.0
            for cap in (120.0, 100.0, 80.0):
                token = self._token(index, cap)
                self.assertIsInstance(token, SegmentVSL)
                critical = self.mn.effective_rho_crit(self.cfg.network, token)
                speed = self._desired(5.0, token)
                self.assertLessEqual(speed, previous_speed)
                self.assertGreaterEqual(critical + 1e-12, previous_critical)
                self.assertLessEqual(speed, token.fd.v_free)
                self.assertAlmostEqual(self._desired(critical, token), speed)
                self.assertAlmostEqual(self._desired(critical + 1e-8, token), speed, places=5)
                previous_speed, previous_critical = speed, critical
        self.assertEqual(self._desired(5.0, self._token(9, 100.0)), 91.31)
        self.assertEqual(self._desired(5.0, self._token(14, 80.0)), 78.1)

    def test_interleaved_cells_do_not_use_global_context(self):
        e9 = self._token(9, 100.0)
        self._token(8, 80.0)  # Arms legacy context for another cell/candidate.
        self.assertEqual(self._desired(5.0, e9), 91.31)
        self.assertAlmostEqual(self.mn.effective_rho_crit(self.cfg.network, e9), 15.164)
        self.adapter._FW_SEG_CTX["p"] = {"v_free": 1.0, "rho_crit": 1000.0}
        self.adapter._FW_SEG_CTX["armed"] = True
        self.assertEqual(self._desired(5.0, e9), 91.31)
        self.assertAlmostEqual(self.mn.effective_rho_crit(self.cfg.network, e9), 15.164)

    def test_extreme_densities(self):
        for rho in (-1.0, 0.0, 1e-12, 15.164, 100.0, 180.0, 200.0, 1e9):
            token = self._token(9, 80.0)
            speed = self._desired(rho, token)
            self.assertTrue(math.isfinite(speed))
            self.assertGreaterEqual(speed, 0.0)
            self.assertLessEqual(speed, 80.0)
            if rho >= 180.0:
                self.assertEqual(speed, 0.0)

    def test_anticipation_uses_same_cell_critical(self):
        cfg = copy.deepcopy(self.cfg)
        cfg.network.capacity_drop_anticipation = True
        cfg.network.metanet_nu_cong_km2_h = 90.0
        for index in (8, 9, 14):
            for cap in (120.0, 100.0, 80.0):
                token = self._token(index, cap, cfg)
                critical = self.mn.effective_rho_crit(cfg.network, token)
                self.assertEqual(self.mn.select_anticipation_nu(critical, cfg.network, token), 30.0)
                self.assertEqual(self.mn.select_anticipation_nu(critical + 1e-6, cfg.network, token), 90.0)

    def test_global_local_ramp_release_match(self):
        follower = self.controller.nash_solver
        demand = self.DemandStep({}, {}, {})
        for rho in (0.0, 16.0, 30.0, 160.0, 179.9, 180.0, 200.0):
            for cap in (120.0, 100.0, 80.0):
                state = self.st.TrafficState.initial(self.cfg)
                action = self.st.ControlAction.uncontrolled(self.cfg)
                action.vsl.update({"FW_E": cap, "FW_W": cap})
                for link in self.cfg.network.freeway_links:
                    state.freeway_density[link] = [rho] * 21
                state.ramp_queue = {r: 100.0 for r in self.cfg.network.ramps}
                global_release, _ = self.mn.compute_ramp_release_flows(
                    state, action, demand, self.cfg, include_current_arrivals=False)
                for link in self.cfg.network.freeway_links:
                    local_release = follower._local_ramp_release(
                        link, state.freeway_density[link], state.ramp_queue, action, demand)
                    for ramp, value in local_release.items():
                        self.assertEqual(value, global_release[ramp])

    def test_global_local_substeps_match_with_same_fd(self):
        cfg = copy.deepcopy(self.cfg)
        # Isolate FD from the independently diagnosed legacy phi context bug.
        cfg.network.freeway_lane_drop_phi = 0.0
        cfg.network.freeway_buffer_segments = 0
        cfg.network.capacity_drop_anticipation = True
        cfg.network.capacity_drop_discharge_phi = 0.85
        demand = self.DemandStep({"FW_E": 3000.0, "FW_W": 3000.0}, {}, {})
        for cap in (120.0, 100.0, 80.0):
            state = self.st.TrafficState.initial(cfg)
            action = self.st.ControlAction.uncontrolled(cfg)
            action.vsl.update({"FW_E": cap, "FW_W": cap})
            for link in cfg.network.freeway_links:
                state.freeway_density[link] = [10.0 + i for i in range(21)]
                state.freeway_speed[link] = [60.0] * 21
            release = {r: 0.0 for r in cfg.network.ramps}
            offcap = {r: 0.0 for r in cfg.network.off_ramps}
            for _ in range(4):
                original = state.copy()
                self.mn.freeway_substep(state, action, demand, cfg,
                                        offramp_capacity_veh_h=offcap,
                                        ramp_release_veh_h=release)
                for link in cfg.network.freeway_links:
                    model = self.local.build_local_freeway_model(cfg, link)
                    result = self.local.freeway_substep_local(
                        model, original.freeway_density[link], original.freeway_speed[link],
                        original.freeway_effective_lanes[link], {},
                        original.mainline_origin_queue.get(link, 0.0),
                        release, offcap, action, demand)
                    self.assertEqual(result[0], state.freeway_density[link])
                    self.assertEqual(result[1], state.freeway_speed[link])
                    self.assertEqual(result[2], state.freeway_effective_lanes[link])

    def test_spawn_worker_matches_parent(self):
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=False)
        process = context.Process(target=_spawn_fd_probe, args=(self.cfg, child))
        process.start()
        child.close()
        try:
            self.assertTrue(parent.poll(20.0), "spawn FD worker timed out")
            result = parent.recv()
            token = self._token(9, 100.0)
            self.assertEqual(result, (self._desired(5.0, token),
                                     self.mn.effective_rho_crit(self.cfg.network, token)))
        finally:
            process.join(5.0)
            if process.is_alive():
                process.terminate()
                process.join(5.0)
            parent.close()

    def test_repeated_adapter_installers_and_pickle(self):
        self.adapter.install_freeway_vsl_zones(self.cfg, None)
        self.adapter.install_freeway_segment_runtime(self.cfg)
        again = install_freeway_fd_runtime(self.adapter, self.w, self.cfg, None)
        self.assertEqual(again["freeway_fd_consistent_installed"], 0.0)
        token = pickle.loads(pickle.dumps(self._token(9, 100.0)))
        self.assertEqual(self._desired(5.0, token), 91.31)
        self.assertEqual(json.loads(json.dumps({"vsl": token})), {"vsl": 100.0})

    def test_reject_invalid_enabled_parameters(self):
        for nominal in (0.0, -1.0, 180.0, 181.0, math.nan, math.inf):
            cfg = copy.deepcopy(self.cfg)
            cfg.network.rho_crit_two_branch = nominal
            with self.assertRaises(ValueError):
                install_freeway_fd_runtime(self.adapter, self.w, cfg, None)
        with self.assertRaises(ValueError):
            install_freeway_fd_runtime(self.adapter, self.w, self.cfg,
                                      {"freeway": {"two_branch": {"enabled": True}}})
        for jam in (0.0, 15.164, math.nan, math.inf):
            with self.assertRaises(ValueError):
                FDParameters(90.0, 15.164, jam).validate()


class DirectionalFDParameterTests(unittest.TestCase):
    """Configuration and arithmetic only; no controller, endpoint or native run."""

    @classmethod
    def setUpClass(cls):
        from evaluation.controllers import vissim_stackelberg_adapter
        cls.adapter = vissim_stackelberg_adapter

    def cfg(self):
        return SimpleNamespace(network=SimpleNamespace(
            v_free=120.0, rho_crit_two_branch=15.0, rho_max=180.0,
            freeway_segment_params={'FW_E': [{'v_free': 100.0, 'rho_max': 160.0}],
                                    'FW_W': [{'v_free': 110.0, 'rho_max': 170.0}]}))

    def install(self, cfg, values):
        return self.adapter.install_freeway_two_branch_fd(cfg, {'freeway': {'two_branch': values}})

    def test_absent_configuration_is_byte_identical(self):
        cfg = self.cfg()
        before = pickle.dumps(cfg)
        self.assertEqual(self.adapter.install_freeway_two_branch_fd(cfg, {}),
                         {'two_branch_fd_enabled': 0.0})
        self.assertEqual(pickle.dumps(cfg), before)

    def test_disabled_directional_setting_does_not_change_configuration_or_values(self):
        plain, directional = self.cfg(), self.cfg()
        self.install(plain, {'enabled': False})
        self.install(directional, {'enabled': False,
            'rho_crit_two_branch_by_direction': {'FW_E': 12.0, 'FW_W': 18.0}})
        self.assertEqual(pickle.dumps(plain), pickle.dumps(directional))
        # A disabled runtime ignores an old mapping held on a reused config.
        directional.network.rho_crit_two_branch_by_direction = {'FW_E': 12.0, 'FW_W': 18.0}
        self.assertEqual(cell_parameters(plain.network, 'FW_E', 0),
                         cell_parameters(directional.network, 'FW_E', 0))

    def test_absent_mapping_preserves_global_critical_density(self):
        cfg = self.cfg()
        self.install(cfg, {'enabled': True, 'rho_crit_two_branch': 15.0})
        self.assertEqual(cell_parameters(cfg.network, 'FW_E', 0), FDParameters(100.0, 15.0, 160.0))
        self.assertEqual(cell_parameters(cfg.network, 'FW_W', 0), FDParameters(110.0, 15.0, 170.0))
        self.assertFalse(hasattr(cfg.network, 'rho_crit_two_branch_by_direction'))

    def test_asymmetric_values_use_direction_and_keep_cell_speed_and_jam(self):
        cfg = self.cfg()
        values = {'FW_E': 12.0, 'FW_W': 18.0}
        metadata = self.install(cfg, {'enabled': True, 'rho_crit_two_branch': 15.0,
                                     'rho_crit_two_branch_by_direction': values})
        east, west = cell_parameters(cfg.network, 'FW_E', 0), cell_parameters(cfg.network, 'FW_W', 0)
        self.assertEqual(east, FDParameters(100.0, 12.0, 160.0))
        self.assertEqual(west, FDParameters(110.0, 18.0, 170.0))
        self.assertAlmostEqual(east.critical(120.0, False), 12.0)
        self.assertAlmostEqual(west.critical(120.0, False), 18.0)
        self.assertEqual(cell_parameters(cfg.network), FDParameters(120.0, 15.0, 180.0))
        self.assertEqual(metadata['two_branch_rho_crit_FW_E'], 12.0)
        self.assertEqual(metadata['two_branch_rho_crit_FW_W'], 18.0)
        values['FW_E'] = 99.0
        self.assertEqual(cell_parameters(cfg.network, 'FW_E', 0).rho_crit, 12.0)
        restored = pickle.loads(pickle.dumps(cfg))
        self.assertEqual(cell_parameters(restored.network, 'FW_W', 0), west)

    def test_invalid_mapping_fails_before_configuration_mutation(self):
        for values in ({'FW_E': 12.0}, {'FW_E': 12.0, 'FW_W': 18.0, 'other': 1.0},
                       None, [], {'FW_E': True, 'FW_W': 18.0},
                       {'FW_E': '12', 'FW_W': 18.0}):
            cfg = self.cfg()
            before = pickle.dumps(cfg)
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    self.install(cfg, {'enabled': True, 'rho_crit_two_branch_by_direction': values})
                self.assertEqual(pickle.dumps(cfg), before)
        for value in (0.0, -1.0, 160.0, 180.0, math.nan, math.inf):
            cfg = self.cfg()
            before = pickle.dumps(cfg)
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.install(cfg, {'enabled': True,
                        'rho_crit_two_branch_by_direction': {'FW_E': value, 'FW_W': 18.0}})
                self.assertEqual(pickle.dumps(cfg), before)

    def test_omitted_mapping_removes_stale_direction_override(self):
        cfg = self.cfg()
        self.install(cfg, {'enabled': True,
            'rho_crit_two_branch_by_direction': {'FW_E': 12.0, 'FW_W': 18.0}})
        self.install(cfg, {'enabled': True, 'rho_crit_two_branch': 15.0})
        self.assertFalse(hasattr(cfg.network, 'rho_crit_two_branch_by_direction'))
        self.assertEqual(cell_parameters(cfg.network, 'FW_E', 0).rho_crit, 15.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
