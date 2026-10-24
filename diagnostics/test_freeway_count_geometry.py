"""Test installed physical freeway counts against observations and continuity."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import area_freeway_accounting as accounting
from evaluation.controllers.control_area_objective import ModelAreaLedger
from diagnostics.probe_model_area_integration import build_projected
from src.models.demand import DemandStep
from src.models.state import ControlAction, ExperimentConfig, TrafficState


class FreewayCountGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = vars(adapter)
        from diagnostics.fixed_source_reference import function
        cls.legacy_counts = staticmethod(function('evaluation/controllers/vissim_stackelberg_adapter.py',
                                                 '_freeway_vehicle_count_by_link', vars(adapter)))
        run = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry"
        if not (run / "state_000900.json").exists():
            raise unittest.SkipTest("read-only n7 reference observation missing")
        cls.cfg, cls.state, _, _, cls.raw, _, _ = build_projected(
            ROOT / "evaluation/configs/n21_n7_20260908.json", run / "state_000900.json", run / "action_000001.json")

    def test_n7_counts_use_the_observed_lane_field(self):
        cfg = copy.deepcopy(self.cfg)
        cfg.network.physical_vehicle_counts = True
        fixed = self.runtime["_freeway_vehicle_count_by_link"](self.state, cfg)
        expected = accounting.continuity_vehicle_counts(self.state, cfg)
        self.assertEqual(fixed, expected)
        # The earlier helper's nonexistent freeway_lanes field triggered 4 lanes.
        self.assertFalse(hasattr(self.state, "freeway_lanes"))
        for link, gap in (("FW_W", 73.67872065638534), ("FW_E", 31.994765590769646)):
            phantom = sum(max(0.0, rho) * self.cfg.network.freeway_segment_length_km * self.cfg.network.freeway_lanes
                          for rho in self.state.freeway_density[link])
            self.assertAlmostEqual(phantom - sum(fixed[link]), gap)
            raw_rows = self.raw["freeway_segments"][link]
            exact_observed = sum(rho * row["length_km"] * lane for rho, row, lane in zip(
                self.state.freeway_density[link], raw_rows, self.state.freeway_effective_lanes[link]))
            self.assertAlmostEqual(exact_observed, sum(row["count"] for row in raw_rows))
            # This smaller projection/continuity length discrepancy remains explicit.
            self.assertLess(abs(exact_observed - sum(fixed[link])), 0.1)

    def test_selected_actual_flows_conserve_fixed_n7_counts(self):
        cfg, state = copy.deepcopy(self.cfg), self.state.copy()
        cfg.network.physical_vehicle_counts = True
        counts = self.runtime["_freeway_vehicle_count_by_link"](state, cfg)
        stocks = {f"freeway:{key}": {"inside": sum(value)} for key, value in counts.items()}
        stocks.update({f"origin:{key}": {"outside": value} for key, value in state.mainline_origin_queue.items()})
        state._control_area_ledger = ModelAreaLedger(stocks)
        cfg.network.control_area_enabled = True
        demand = adapter.demand_from_state(self.raw, cfg, DemandStep, 1)[0]
        control = ControlAction.uncontrolled(cfg)
        # Repeated Tf transitions include evolving density/speed and off-ramp flow.
        for _ in range(6):
            _, diag = accounting._freeway_substep_events(
                state, control, demand, cfg, update_ramp_queues=False, ramp_release_veh_h={})
            for off in cfg.network.off_ramps:
                state._control_area_ledger.transfer(
                    f"freeway:{cfg.network.off_ramp_from_freeway[off]}", f"storage:{off}",
                    diag[f"offramp_flow_{off}"] * cfg.simulation.T_f_h,
                    inside_to_inside=1.0, outside_to_inside=1.0)
            counts = self.runtime["_freeway_vehicle_count_by_link"](state, cfg)
            for link, row in counts.items():
                self.assertAlmostEqual(sum(row), sum(state._control_area_ledger.stocks[f"freeway:{link}"].values()))

    def test_fractional_effective_lanes_are_not_clamped_to_one(self):
        cfg = ExperimentConfig()
        cfg.network.physical_vehicle_counts = True
        state = TrafficState.initial(cfg)
        state.freeway_effective_lanes["FW_E"] = [0.25] * cfg.network.freeway_segments_per_link
        actual = self.runtime["_freeway_vehicle_count_by_link"](state, cfg)
        self.assertEqual(actual, accounting.continuity_vehicle_counts(state, cfg))
        self.assertEqual(actual["FW_E"], [18 * 0.5 * 0.25] * 4)

    def test_calibrated_state_getter_uses_same_dynamic_lanes(self):
        cfg = ExperimentConfig()
        cfg.network.physical_vehicle_counts = True
        state = TrafficState.initial(cfg)
        state.freeway_effective_lanes["FW_E"] = [0.25, 1.0, 2.0, 1.5]
        lengths = {link: [0.5] * 4 for link in cfg.network.freeway_links}
        calibration = {"physical_inventory": {"freeway_segment_length_profile_km": lengths}}
        with mock.patch.object(TrafficState, "freeway_vehicle_count_by_link", TrafficState.freeway_vehicle_count_by_link), \
                mock.patch.object(TrafficState, "total_freeway_vehicles", TrafficState.total_freeway_vehicles):
            metadata = self.runtime["install_vissim_calibration_runtime_patches"](cfg, calibration)
            self.assertEqual(metadata["calibration_state_vehicle_count_patch_installed"], 1)
            self.assertEqual(state.freeway_vehicle_count_by_link(cfg.network), accounting.continuity_vehicle_counts(state, cfg))
            self.assertEqual(state.total_freeway_vehicles(cfg.network), sum(sum(v) for v in accounting.continuity_vehicle_counts(state, cfg).values()))
            cfg.network.physical_vehicle_counts = False
            self.assertEqual(state.freeway_vehicle_count_by_link(cfg.network)["FW_E"], [18.0] * 4)
            cfg.network.physical_vehicle_counts = True
            self.assertEqual(state.freeway_vehicle_count_by_link(cfg.network), accounting.continuity_vehicle_counts(state, cfg))

    def test_flag_absent_and_false_preserve_the_old_getter(self):
        cfg = copy.deepcopy(self.cfg)
        for explicit_false in (False, True):
            if explicit_false:
                cfg.network.physical_vehicle_counts = False
            expected = self.legacy_counts(self.state, cfg)
            self.assertEqual(self.runtime["_freeway_vehicle_count_by_link"](self.state, cfg), expected)


if __name__ == "__main__":
    unittest.main()
