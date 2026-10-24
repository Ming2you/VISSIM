"""Regression probes using the actual n7 link-local follower, without VISSIM."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]

from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import freeway_local_state as fix
from src.controllers import local_freeway_plant as plant
from src.controllers import wu_faithful_follower as follower_module
from src.models.demand import DemandStep
from src.models.state import ControlAction, TrafficState


class LocalStateRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tuning = adapter.load_optional_json(str(ROOT / "evaluation/configs/n21_n7_20260908.json"))
        cal = adapter.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
        cal = adapter.deep_update(dict(cal), tuning.get("calibration_override", {}))
        adapter.install_config_switches(tuning)
        cls.cfg = adapter.build_config(ROOT / "vendor/NumSim-mine", 150, 5400, "wu-link",
                                       cal, tuning, local_observation=True, flagship=True)
        mapping = json.loads((ROOT / tuning["mapping_json"]).read_text(encoding="utf-8"))
        adapter.install_landing_storage(cls.cfg, tuning)
        adapter.install_landing_storage_runtime(cls.cfg)
        adapter.install_freeway_segment_lanes(cls.cfg, tuning, mapping)
        adapter.install_freeway_lane_drop(cls.cfg, tuning)
        adapter.install_freeway_vsl_zones(cls.cfg, tuning)
        adapter.install_freeway_segment_runtime(cls.cfg)
        adapter.install_freeway_vsl_sequence_kbest(cls.cfg, tuning)
        cls.follower = adapter.build_priced_wu_link_controller(cls.cfg, tuning).nash_solver
        cls.control = ControlAction.uncontrolled(cls.cfg)
        cls.demand = DemandStep({link: 3000.0 for link in cls.cfg.network.freeway_links}, {}, {})
        cls.old_drain = follower_module.WuFaithfulFollower._local_offramp_drain
        cls.old_profile = plant._local_lane_profile
        fix.configure(cls.cfg, {"freeway": {"local_lane_context": True,
                                             "conservative_offramp_drain": True}})
        fix.install(cls.cfg, adapter._FW_SEG_CTX_STATE)

    def setUp(self):
        self.cfg.network.local_lane_context = True
        self.cfg.network.conservative_offramp_drain = True

    def test_zero_stock_and_stock_limited_intake(self):
        for occupied in (0.0, 0.01, 2.0, 20.0):
            flow, intake = self.follower._local_offramp_drain(
                "OR_F_E", occupied, {}, self.control, self.cfg.simulation.T_f_h)
            self.assertLessEqual(flow * self.cfg.simulation.T_f_h, occupied + 1e-12)
            self.assertAlmostEqual(flow, sum(intake.values()), places=10)
        self.assertEqual(self.follower._local_offramp_drain(
            "OR_F_E", 0.0, {}, self.control, self.cfg.simulation.T_f_h), (0.0, {}))

    def test_shared_receiving_space_is_not_allocated_twice(self):
        fake = SimpleNamespace(cfg=SimpleNamespace(network=SimpleNamespace(
            conservative_offramp_drain=True, urban_link_storage_veh={"receiver": 10.0})),
            _wu=SimpleNamespace(_offramp_drain_flow={"off": [("s", "a"), ("s", "b")]},
                _specs={"a": {"receiving_link": "receiver", "beta": .5},
                        "b": {"receiving_link": "receiver", "beta": .5}},
                _signal_leaving_rate=lambda *args: 1000.0))
        dt = 10.0 / 3600.0
        total, intake = follower_module.WuFaithfulFollower._local_offramp_drain(
            fake, "off", 20.0, {"receiver": 9.0}, self.control, dt)
        self.assertAlmostEqual(total * dt, 1.0)
        self.assertAlmostEqual(intake["receiver"] * dt, 1.0)

    def test_blocked_major_turn_cannot_escape_through_minor_turn(self):
        fake = SimpleNamespace(cfg=SimpleNamespace(network=SimpleNamespace(
            conservative_offramp_drain=True, urban_link_storage_veh={"blocked": 20.0, "open": 20.0})),
            _wu=SimpleNamespace(_offramp_drain_flow={"off": [("s", "a"), ("s", "b")]},
                _specs={"a": {"receiving_link": "blocked", "beta": .9},
                        "b": {"receiving_link": "open", "beta": .1}},
                _signal_leaving_rate=lambda *args: 10000.0))
        dt = 10.0 / 3600.0
        total, intake = follower_module.WuFaithfulFollower._local_offramp_drain(
            fake, "off", 10.0, {"blocked": 20.0}, self.control, dt)
        self.assertAlmostEqual(total * dt, 1.0)
        self.assertAlmostEqual(intake["open"] * dt, 1.0)
        self.assertEqual(intake["blocked"], 0.0)

    def test_profile_is_current_for_each_substep_and_link(self):
        for link, occupied in (("FW_E", 25.0), ("FW_W", 12.0), ("FW_E", 0.0)):
            model = self.follower._local_freeway_models[link]
            occ = {off: occupied for off in model.owned_offramps}
            lanes = plant._local_lane_profile(model, occ, self.demand)
            self.assertEqual(adapter._FW_SEG_CTX_STATE["profile"], {link: lanes})

    def test_live_candidate_updates_context_as_occupancy_changes(self):
        state = TrafficState.initial(self.cfg)
        n = self.cfg.network.freeway_segments_per_link
        state.freeway_density = {link: [10.0] * n for link in self.cfg.network.freeway_links}
        state.freeway_speed = {link: [100.0] * n for link in self.cfg.network.freeway_links}
        state.freeway_effective_lanes = copy.deepcopy(self.cfg.network.freeway_segment_lanes)
        off = "OR_F_E"
        storage = self.cfg.network.off_ramp_storage_link[off]
        state.urban_link_storage[storage] = self.cfg.network.urban_link_storage_veh[storage] - 20.0
        original = plant._local_lane_profile
        traces = []

        def observe(model, occupancy, demand):
            lanes = original(model, occupancy, demand)
            self.assertEqual(adapter._FW_SEG_CTX_STATE["profile"][model.link], lanes)
            traces.append(float(occupancy.get(off, 0.0)))
            return lanes

        plant._local_lane_profile = observe
        try:
            self.follower._solve_freeway_agent_local(
                "FW_E", state, {}, self.demand, self.control,
                vsl_override=[80.0] * 10 + [120.0] * (n - 10))
        finally:
            plant._local_lane_profile = original
        self.assertGreater(len(traces), 1)
        self.assertGreater(max(traces) - min(traces), 1e-6)

    def test_disabled_flags_preserve_original_calls(self):
        self.cfg.network.conservative_offramp_drain = False
        self.cfg.network.local_lane_context = False
        args = (self.follower, "OR_F_E", 0.0, {}, self.control, self.cfg.simulation.T_f_h)
        self.assertEqual(follower_module.WuFaithfulFollower._local_offramp_drain(*args),
                         type(self).old_drain(*args))
        model = self.follower._local_freeway_models["FW_E"]
        occupancy = {off: 5.0 for off in model.owned_offramps}
        sentinel = {"sentinel": [999.0]}
        adapter._FW_SEG_CTX_STATE["profile"] = sentinel
        self.assertEqual(plant._local_lane_profile(model, occupancy, self.demand),
                         type(self).old_profile(model, occupancy, self.demand))
        self.assertIs(adapter._FW_SEG_CTX_STATE["profile"], sentinel)


if __name__ == "__main__":
    unittest.main(verbosity=2)
