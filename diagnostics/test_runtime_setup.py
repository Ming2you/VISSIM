"""Compare the shared setup with main()'s AST in isolated offline processes.

AST execution is restricted to this diagnostic reference. Production setup uses
explicit function calls. Requires the local read-only no-control snapshot.
"""
from __future__ import annotations

import ast
import copy
import dataclasses
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/NumSim-mine")]
DEFAULT_RUN = ROOT / "evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry"


def canonical(value):
    if isinstance(value, dict):
        return {str(k): canonical(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [canonical(v) for v in value]
    if isinstance(value, set):
        return sorted(canonical(v) for v in value)
    if dataclasses.is_dataclass(value):
        return canonical(vars(value))
    return value


def observe(adapter, cfg, state, raw, tuning):
    from src.models import metanet, state as state_module
    from src.models.demand import DemandStep
    forecast = adapter.demand_from_state(raw, cfg, DemandStep, 3)
    action = state_module.ControlAction.uncontrolled(cfg)
    action.vsl.update({"FW_E": 100.0, "FW_W": 80.0})
    projected = canonical(vars(state))
    roll = state.copy()
    for _ in range(4):
        metanet.freeway_substep(roll, action, forecast[0], cfg)
    controller = adapter.build_priced_wu_link_controller(cfg, tuning)
    local = controller.nash_solver._solve_freeway_agent_local(
        "FW_E", state, {}, forecast[0], action, vsl_override=[100.0] * 21)
    network = canonical(vars(cfg.network))
    # Newly declared false flags are deliberately absent from the old initializer.
    for key in ("local_lane_context", "conservative_offramp_drain", "local_landing_state"):
        network.pop(key, None)
    return {"network": network, "simulation": canonical(vars(cfg.simulation)),
            "projected": projected,
            "rollout": {k: canonical(getattr(roll, k)) for k in (
                "freeway_density", "freeway_speed", "freeway_effective_lanes",
                "ramp_queue", "mainline_origin_queue")},
            "local_action": canonical(local[0]), "local_cost": local[1],
            "local_evaluations": local[2]}


def run_probe(route, arm):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import freeway_local_state
    from evaluation.controllers.freeway_fd import install_freeway_fd_runtime
    from evaluation.controllers.runtime_setup import configure_runtime, install_worker_runtime
    from src.controllers import wu_faithful_follower

    filename = "n21_n7_20260908.json" if arm == "n7" else "n21i_i1_20260909.json"
    tuning = adapter.load_optional_json(str(ROOT / "evaluation/configs" / filename))
    if arm == "i1_fixed":
        tuning["freeway"].update(local_lane_context=True, conservative_offramp_drain=True)
    adapter.install_config_switches(tuning)
    calibration = adapter.load_optional_json(str(ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    calibration = adapter.deep_update(dict(calibration), tuning.get("calibration_override", {}))
    run = Path(os.environ.get("VISSIM_RUNTIME_TEST_RUN", str(DEFAULT_RUN)))
    raw = adapter.load_optional_json(str(run / "state_000900.json"))
    mapping = adapter.load_optional_json(str(ROOT / tuning["mapping_json"]))
    detectors = adapter.load_optional_json(str(ROOT / tuning["detector_mapping_json"]))
    detectors, _ = adapter.filter_midblock_links_from_detector_mapping(detectors, tuning)
    _, _, _, _, TrafficState, _ = adapter.repo_imports(ROOT / "vendor/NumSim-mine")
    local_observation = bool(adapter._link_counts_from_local_observation(raw) and detectors)
    cfg = adapter.build_config(ROOT / "vendor/NumSim-mine", raw["control_interval_sec"],
                               raw["sim_period_sec"], "fast-smoke", calibration, tuning,
                               local_observation=local_observation, flagship=True)
    adapter.install_adapter_calibration_fingerprints(cfg, tuning)
    previous = str(run / "action_000001.json")
    if route == "reference":
        # Keep the reference fixed after the integration patch replaces main's
        # block with a helper call; otherwise this would only test itself.
        original_source = subprocess.check_output(
            ["git", "show", "6056c94:evaluation/controllers/vissim_stackelberg_adapter.py"],
            cwd=ROOT).decode("utf-8")
        body = next(node.body for node in ast.parse(original_source).body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")

        def assigns(node, name):
            return isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in node.targets)

        start = next(i for i, node in enumerate(body) if assigns(node, "runtime_patch_metadata"))
        end = next(i for i, node in enumerate(body[start:], start) if assigns(node, "forecast_horizon_steps"))
        namespace = dict(vars(adapter))
        namespace.update(cfg=cfg, tuning=tuning, mapping=mapping, calibration=calibration,
                         state_json=raw, detector_mapping=detectors, TrafficState=TrafficState,
                         local_observation=local_observation, physical_projection_input=None,
                         args=SimpleNamespace(previous_action_json=previous))
        exec(compile(ast.Module(body=body[start:end], type_ignores=[]), adapter.__file__, "exec"), namespace)
        state, detectors, metadata = namespace["state"], namespace["detector_mapping"], namespace["runtime_patch_metadata"]
        if arm == "i1_fixed":
            # The intended bug fixes are independent of extracting main's order.
            # Apply them to the original reference too, after its unchanged setup.
            freeway_local_state.configure(cfg, tuning)
            freeway_local_state.install(cfg, adapter._FW_SEG_CTX_STATE)
            install_freeway_fd_runtime(adapter, wu_faithful_follower, cfg, tuning)
    else:
        state, detectors, metadata = configure_runtime(
            adapter, cfg, tuning, mapping, raw, previous, detectors, calibration, TrafficState)
    result = observe(adapter, cfg, state, raw, tuning)
    result["detectors"] = detectors
    result["metadata"] = {k: v for k, v in metadata.items()
                          if k not in ("local_lane_context", "conservative_offramp_drain", "local_landing_state")
                          and not k.startswith("freeway_fd_consistent_")}
    if route == "worker_repeat":
        frozen = canonical(vars(state))
        for _ in range(2):
            install_worker_runtime(adapter, cfg, {"network_path": raw["network_path"]}, detectors)
        result["worker_state_unchanged"] = frozen == canonical(vars(state))
        result["worker_after"] = observe(adapter, cfg, state, raw, tuning)
    print("RUNTIME_PROBE=" + json.dumps(result, ensure_ascii=True, sort_keys=True, allow_nan=False))


class RuntimeSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = Path(os.environ.get("VISSIM_RUNTIME_TEST_RUN", str(DEFAULT_RUN)))
        if not (run / "state_000900.json").is_file():
            raise unittest.SkipTest("local no-control snapshot missing; set VISSIM_RUNTIME_TEST_RUN")

    def probe(self, route, arm):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        process = subprocess.run([sys.executable, str(Path(__file__)), "--probe", route, arm],
                                 cwd=ROOT, env=env, text=True, encoding="utf-8",
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=55)
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout[-1000:])
        line = next(line for line in process.stdout.splitlines() if line.startswith("RUNTIME_PROBE="))
        return json.loads(line.split("=", 1)[1])

    def test_n7_matches_original_main_numerically(self):
        reference = self.probe("reference", "n7")
        actual = self.probe("helper", "n7")
        self.assertEqual(actual, reference)

    def test_enabled_fd_local_fixes_match_original_plus_fixes(self):
        reference = self.probe("reference", "i1_fixed")
        actual = self.probe("helper", "i1_fixed")
        self.assertEqual(actual, reference)

    def test_worker_reinstall_preserves_state_and_behavior(self):
        for arm in ("n7", "i1_fixed"):
            with self.subTest(arm=arm):
                result = self.probe("worker_repeat", arm)
                self.assertTrue(result.pop("worker_state_unchanged"))
                after = result.pop("worker_after")
                result.pop("detectors")
                result.pop("metadata")
                self.assertEqual(after, result)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--probe":
        run_probe(sys.argv[2], sys.argv[3])
    else:
        unittest.main(verbosity=2)
