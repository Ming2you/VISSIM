# v3 N4-4 - 고정신호 패치가 조용히 항상녹색으로 되돌아가는 폴백 3곳을 fail-closed 로 못박는다
from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
NETWORK = WORKSPACE_ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
VENDOR_NUMSIM = WORKSPACE_ROOT / "vendor" / "NumSim-mine"
TUNING = (
    WORKSPACE_ROOT
    / "evaluation"
    / "configs"
    / "real_world_modi_pstack_distributed_core15n41_20260805.json"
)
DETECTOR_MAPPING = (
    WORKSPACE_ROOT
    / "evaluation"
    / "real_world_modi_control_distributed_20260728"
    / "detector_local_mapping_distributed_core15n41_20260805.json"
)

# 패치 대상 모델 모듈은 상류 저장소에 있다. 실런은 `repo_imports` 가 넣어주지만
# 테스트는 스냅샷을 직접 올린다.
if str(VENDOR_NUMSIM) not in sys.path:
    sys.path.insert(0, str(VENDOR_NUMSIM))


def _cfg(uncontrolled, signals=(), movements=None):
    return SimpleNamespace(
        network=SimpleNamespace(
            uncontrolled_nodes=list(uncontrolled),
            signals=list(signals),
            urban_movements=dict(movements or {}),
        )
    )


class MonitorFixedSignalFailClosedTests(unittest.TestCase):
    def setUp(self) -> None:
        from evaluation.controllers import vissim_stackelberg_adapter as adapter

        self.adapter = adapter
        self.model_module = importlib.import_module("src.models.urban_queue_model")
        self.patch_targets = [
            importlib.import_module(name)
            for name in (
                "src.models.urban_queue_model",
                "src.controllers.distributed_coordinator",
                "src.controllers.local_signal_plant",
                "src.controllers.wu_distributed",
                "src.controllers.wu_faithful_follower",
            )
        ]
        self.saved = [
            (module, getattr(module, "_phase_green_fraction", None))
            for module in self.patch_targets
        ]
        self.saved_original = getattr(
            self.model_module, "_vissim_original_phase_green_fraction", None
        )

    def tearDown(self) -> None:
        for module, value in self.saved:
            if value is not None:
                setattr(module, "_phase_green_fraction", value)
        if self.saved_original is None:
            if hasattr(self.model_module, "_vissim_original_phase_green_fraction"):
                delattr(self.model_module, "_vissim_original_phase_green_fraction")
        else:
            self.model_module._vissim_original_phase_green_fraction = self.saved_original

    def test_missing_network_file_raises_instead_of_returning_silently(self) -> None:
        state_json = {"network_path": str(WORKSPACE_ROOT / "__no_such_network__.inpx")}
        with self.assertRaises(self.adapter.MonitorFixedSignalPatchError) as ctx:
            self.adapter.install_monitor_fixed_signal_runtime_patch(
                _cfg(["SC2"]), state_json, {}
            )
        self.assertIn("__no_such_network__", str(ctx.exception))

    def test_compile_failure_raises_instead_of_returning_silently(self) -> None:
        from evaluation.controllers import fixed_signal_schedule

        def boom(*_args, **_kwargs):
            raise ValueError("forced compile failure")

        saved = fixed_signal_schedule.compile_fixed_signal_schedules
        fixed_signal_schedule.compile_fixed_signal_schedules = boom
        try:
            with self.assertRaises(self.adapter.MonitorFixedSignalPatchError) as ctx:
                self.adapter.install_monitor_fixed_signal_runtime_patch(
                    _cfg(["SC2"]), {"network_path": str(NETWORK)}, {}
                )
            self.assertIn("forced compile failure", str(ctx.exception))
        finally:
            fixed_signal_schedule.compile_fixed_signal_schedules = saved

    def test_monitor_node_without_schedule_raises(self) -> None:
        with self.assertRaises(self.adapter.MonitorFixedSignalPatchError) as ctx:
            self.adapter.install_monitor_fixed_signal_runtime_patch(
                _cfg(["SC2", "__ghost_node__"]), {"network_path": str(NETWORK)}, {}
            )
        self.assertIn("__ghost_node__", str(ctx.exception))

    def test_empty_target_set_is_a_legitimate_skip(self) -> None:
        diagnostics = self.adapter.install_monitor_fixed_signal_runtime_patch(
            _cfg([], []), {"network_path": str(NETWORK)}, {}
        )
        self.assertEqual(diagnostics["monitor_fixed_signal_patch_enabled"], 0.0)
        self.assertEqual(
            diagnostics["monitor_fixed_signal_patch_skip_reason"], "no_target_nodes"
        )

    def test_blank_phase_movement_without_schedule_raises_at_runtime(self) -> None:
        from evaluation.controllers.native_phase_green import (
            build_native_phase_share_table,
        )

        table = build_native_phase_share_table({}, {})
        patched = self.adapter.build_patched_phase_green_fraction(
            lambda *_args, **_kwargs: 1.0, {}, table
        )
        spec = {"intersection": "__ghost_node__", "phase": ""}
        with self.assertRaises(self.adapter.MonitorFixedSignalPatchError) as ctx:
            patched(SimpleNamespace(green_times={}, offsets={}), None, spec, 0)
        self.assertIn("__ghost_node__", str(ctx.exception))

    def test_real_core15n41_target_set_installs_and_reports_counts(self) -> None:
        tuning = json.loads(TUNING.read_text(encoding="utf-8"))
        detector_mapping = json.loads(DETECTOR_MAPPING.read_text(encoding="utf-8"))
        network_cfg = tuning["config_overrides"]["network"]
        cfg = _cfg(
            network_cfg["uncontrolled_nodes"],
            network_cfg["signals"],
            network_cfg["urban_movements"],
        )
        diagnostics = self.adapter.install_monitor_fixed_signal_runtime_patch(
            cfg, {"network_path": str(NETWORK)}, detector_mapping
        )

        self.assertEqual(diagnostics["monitor_fixed_signal_patch_enabled"], 1.0)
        self.assertEqual(diagnostics["monitor_fixed_signal_schedule_count"], 41.0)
        self.assertGreater(diagnostics["monitor_fixed_signal_patched_module_count"], 0.0)
        self.assertGreater(diagnostics["native_phase_share_scaled_count"], 0.0)
        self.assertGreater(diagnostics["native_phase_share_unresolved_count"], 0.0)
        self.assertEqual(
            diagnostics["native_phase_share_movement_count"],
            diagnostics["native_phase_share_scaled_count"]
            + diagnostics["native_phase_share_unit_count"]
            + diagnostics["native_phase_share_unresolved_count"],
        )


if __name__ == "__main__":
    unittest.main()
