"""Branch projection contracts and actual n7 installation/state replay.

The active implementation is imported from production. A fixed historical
function is retained only to verify behavior when projection repair is disabled.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "diagnostics")]
from evaluation.controllers import observation_projection as projection
from diagnostics.review_fixtures import fixture_path
from diagnostics.fixed_source_reference import source_at


class ProjectionContracts(unittest.TestCase):
    def setUp(self):
        self.cfg = SimpleNamespace(network=SimpleNamespace(
            urban_link_storage_veh={"signal": 12.0, "external": 10.0},
            off_ramp_storage_link={"OR": "signal"},
            offramp_direct_share_by_offramp={"OR": 0.4},
        ))
        self.detectors = {"link_to_origins": {"a": ["old"], "b": ["old"]},
                          "link_to_movements": {"a": [{"movement": "old_queue"}], "b": [{"movement": "old_queue"}]}}
        self.tuning = {"observation": {"physical_branch_projection": {
            "enabled": True, "link_to_storage": {"a": "signal", "b": "external"}}}}

    def test_disabled_is_same_object_and_does_not_change_config(self):
        before = deepcopy(self.cfg)
        result, meta = projection.install_physical_branch_projection(self.cfg, {}, self.detectors, link_counts={"a": 20})
        self.assertIs(result, self.detectors)
        self.assertEqual(self.cfg, before)
        self.assertEqual(meta["physical_branch_projection_enabled"], 0)

    def test_twenty_vehicles_partition_signal_and_external_without_copying(self):
        result, meta = projection.install_physical_branch_projection(self.cfg, self.tuning, self.detectors, link_counts={"a": 12, "b": 8})
        self.assertEqual(meta["physical_branch_projection_observed_veh"], 20)
        self.assertEqual(result["link_to_origins"], {"a": ["signal"], "b": ["external"]})
        self.assertEqual(result["link_to_movements"], {})
        self.assertEqual(self.detectors["link_to_origins"]["a"], ["old"])
        audit = projection.audit_physical_branch_projection(result, {"a": 12, "b": 8}, {"signal": 12, "external": 8})
        self.assertEqual(audit["physical_branch_projection_residual_veh"], 0)

    def test_capacity_floor_preserves_observed_stock_and_is_reported(self):
        self.tuning["observation"]["physical_branch_projection"]["capacity_policy"] = "observed_lower_bound"
        _, meta = projection.install_physical_branch_projection(self.cfg, self.tuning, self.detectors, link_counts={"a": 20})
        self.assertEqual(self.cfg.network.urban_link_storage_veh["signal"], 20)
        self.assertEqual(meta["physical_branch_projection_capacity"]["signal"]["observed_floor_added_veh"], 8)

    def test_strict_capacity_failure_does_not_partially_mutate(self):
        before = deepcopy(self.cfg)
        with self.assertRaises(projection.ProjectionError):
            projection.install_physical_branch_projection(self.cfg, self.tuning, self.detectors, link_counts={"a": 20})
        self.assertEqual(self.cfg, before)

    def test_reject_shared_physical_channels_and_unlisted_target_source(self):
        self.detectors["ramp_link_to_queues"] = {"a": ["ramp"]}
        with self.assertRaises(projection.ProjectionError):
            projection.install_physical_branch_projection(self.cfg, self.tuning, self.detectors, link_counts={"a": 1})
        self.detectors.pop("ramp_link_to_queues")
        self.detectors["link_to_origins"]["c"] = ["signal"]
        with self.assertRaises(projection.ProjectionError):
            projection.install_physical_branch_projection(self.cfg, self.tuning, self.detectors, link_counts={"c": 1})

    def test_audit_detects_clipping_and_double_assignment(self):
        result, _ = projection.install_physical_branch_projection(self.cfg, self.tuning, self.detectors, link_counts={"a": 12})
        for actual in (11, 13):
            with self.assertRaises(projection.ProjectionError):
                projection.audit_physical_branch_projection(result, {"a": 12}, {"signal": actual, "external": 0})


class ActualInstalledProjection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from probe_model_area_integration import adapter, build_projected
        cls.adapter, cls.build_projected = adapter, staticmethod(build_projected)
        cls.overlay = json.loads((ROOT / "diagnostics/observation_projection_config.json").read_text(encoding="utf-8"))
        fixed_source = source_at('6056c94', 'evaluation/controllers/vissim_stackelberg_adapter.py')
        cls.patched_summary = staticmethod(adapter.build_local_observation_summary)
        cls.summary_globals = vars(adapter)
        fixed_node = next(node for node in ast.parse(fixed_source).body if isinstance(node, ast.FunctionDef) and node.name == "build_local_observation_summary")
        fixed_namespace = dict(vars(adapter))
        exec(compile(ast.Module(body=[fixed_node], type_ignores=[]), "<6056c94 fixed observation summary>", "exec"), fixed_namespace)
        cls.fixed_summary = staticmethod(fixed_namespace["build_local_observation_summary"])
        cls.calibration = adapter.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
        cls.config_path = ROOT / "evaluation/configs/n21_n7_20260908.json"

    def test_actual_900_and_all_available_n7_states_preserve_total_stock(self):
        from evaluation.controllers.control_area_objective import model_stock_values, projection_stock_cohorts, physical_membership_from_ledger
        from src.models.state import TrafficState
        adapter = self.adapter
        membership = physical_membership_from_ledger(json.loads((ROOT / "diagnostics/control_area_membership.json").read_text(encoding="utf-8")))
        nc = fixture_path(ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry")
        states = [nc / "state_000900.json"]
        states += sorted(fixture_path(ROOT / "evaluation/runs/codex_n7_s13_6056c94_20260909").rglob("state_*.json"))
        rows = []
        for path in states:
            with self.subTest(state=str(path)):
                cfg, state, detectors, tuning, raw, _, _ = self.build_projected(self.config_path, path, nc / "action_000001.json")
                before = model_stock_values(state, cfg.network, freeway_vehicle_counts=adapter._freeway_vehicle_count_by_link(state, cfg))
                counts = adapter._link_counts_from_local_observation(raw)
                calibration = adapter.deep_update(dict(self.calibration), tuning.get("calibration_override", {}))
                self.assertEqual(self.patched_summary(raw, cfg, detectors, calibration), self.fixed_summary(raw, cfg, detectors, calibration))
                updated, meta = projection.install_physical_branch_projection(cfg, self.overlay, detectors, link_counts=counts)
                with patch.object(adapter, "build_local_observation_summary", self.patched_summary):
                    candidate = adapter.traffic_state_from_vissim(raw, cfg, TrafficState, updated, calibration, physical_projection_input=None)
                after = model_stock_values(candidate, cfg.network, freeway_vehicle_counts=adapter._freeway_vehicle_count_by_link(candidate, cfg))
                duplicate_avoided = float(candidate.local_observation_summary["projection_diagnostics"]["ramp_spillback_duplicate_avoided_veh"])
                self.assertAlmostEqual(sum(before.values()) - duplicate_avoided, sum(after.values()), places=8)
                for key, count in meta["physical_branch_projection_target_veh"].items():
                    self.assertAlmostEqual(after["storage:" + key], count, places=8)
                cohorts = projection_stock_cohorts(candidate.local_observation_summary["projection_diagnostics"]["physical_stock_assignment_by_link"], membership)
                for key, value in after.items():
                    if key.startswith(("storage:", "movement:", "ramp:")):
                        self.assertAlmostEqual(sum(cohorts.get(key, {}).values()), value, places=8)
                rows.append({"state": str(path.relative_to(ROOT)), "before_stock": sum(before.values()), "after_stock": sum(after.values()), "spillback_duplicate_removed_veh": duplicate_avoided, "branch_vehicles": meta["physical_branch_projection_target_veh"], "capacity": meta["physical_branch_projection_capacity"]})
        (ROOT / "diagnostics/observation_projection_replay.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    def test_stopped_signal_branch_stays_single_storage_with_origin_binding_on(self):
        adapter = self.adapter
        nc = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry"
        cfg, _, detectors, _, raw, _, _ = self.build_projected(self.config_path, nc / "state_000900.json", nc / "action_000001.json")
        synthetic = deepcopy(raw)
        synthetic["local_observation"]["link_counts"] = {"10491": 12, "10479": 8}
        synthetic["local_observation"]["link_stopped_counts"] = {"10491": 12, "10479": 8}
        synthetic["vehicle_records"]["records"] = []
        cfg.network.ramp_spillback_obs = False
        updated, _ = projection.install_physical_branch_projection(cfg, self.overlay, detectors, link_counts=synthetic["local_observation"]["link_counts"])
        with patch.dict(self.summary_globals, {"_queue_origin_binding_enabled": lambda: True}):
            summary = self.patched_summary(synthetic, cfg, updated, self.calibration)
        self.assertEqual(sum(summary["urban_movement_queue"].values()), 0)
        self.assertEqual(sum(summary["ramp_queue"].values()), 0)
        self.assertEqual(sum(summary["urban_link_storage_occupancy"].values()), 20)
        self.assertEqual(summary["urban_link_storage_occupancy"]["OR_D_W_storage"], 12)
        self.assertEqual(summary["urban_link_storage_occupancy"]["SC1001_W_tail"], 8)

    def test_approach_spillback_twenty_vehicles_remain_twenty_not_forty(self):
        adapter = self.adapter
        nc = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry"
        cfg, _, detectors, _, raw, _, _ = self.build_projected(self.config_path, nc / "state_000900.json", nc / "action_000001.json")
        synthetic = deepcopy(raw)
        synthetic["local_observation"]["link_counts"] = {"32": 20}
        synthetic["local_observation"]["link_stopped_counts"] = {"32": 20}
        synthetic["vehicle_records"]["records"] = []
        cfg.network.ramp_spillback_obs = True
        detectors["ramp_spillback_links"] = {"R_D_W": [{"link": "32", "lanes": 1, "queue_lanes": [1]}]}
        original = self.fixed_summary(synthetic, cfg, detectors, self.calibration)
        disabled = self.patched_summary(synthetic, cfg, detectors, self.calibration)
        self.assertEqual(disabled, original)
        updated, _ = projection.install_physical_branch_projection(cfg, self.overlay, detectors, link_counts=synthetic["local_observation"]["link_counts"])
        corrected = self.patched_summary(synthetic, cfg, updated, self.calibration)
        def stock(summary):
            return sum(summary["urban_movement_queue"].values()) + sum(summary["urban_link_storage_occupancy"].values()) + sum(summary["ramp_queue"].values())
        self.assertAlmostEqual(stock(original), 40)
        self.assertAlmostEqual(stock(disabled), 40)
        self.assertAlmostEqual(stock(corrected), 20)
        self.assertEqual(original["ramp_spillback"], corrected["ramp_spillback"])
        self.assertEqual(corrected["ramp_spillback"]["R_D_W"], 20)
        self.assertEqual(corrected["projection_diagnostics"]["ramp_spillback_duplicate_avoided_veh"], 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
