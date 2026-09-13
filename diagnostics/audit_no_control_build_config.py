"""Compare only build_config(flagship=False/True); no runtime or rollout calls."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze(value):
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else {"float_repr": repr(value)}
    if isinstance(value, dict):
        return {str(k): freeze(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [freeze(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted((freeze(v) for v in value), key=repr)
    if hasattr(value, "__dict__"):
        return freeze(vars(value))
    raise TypeError((type(value).__name__, repr(value)))


def diff(a, b, prefix=""):
    if isinstance(a, dict) and isinstance(b, dict):
        rows = []
        for key in sorted(set(a) | set(b)):
            name = f"{prefix}.{key}" if prefix else key
            if key not in a or key not in b:
                rows.append({"field": name, "live_nc": a.get(key), "helper": b.get(key),
                             "present_live": key in a, "present_helper": key in b})
            else:
                rows.extend(diff(a[key], b[key], name))
        return rows
    return [] if type(a) is type(b) and a == b else [{"field": prefix, "live_nc": a, "helper": b}]


def main():
    started = time.perf_counter()
    config_path = ROOT / "diagnostics/contract_observer_off_configs_v3/n7_area_beta0.json"
    run = ROOT / "evaluation/runs/codex_nc5400_r01_baseline_s13"
    provenance_path = run / f"run_provenance_{run.name}.json"
    snapshot_path = run / f"decisions_{run.name}/state_000900.json"
    action_path = run / f"decisions_{run.name}/action_000900.json"
    calibration_path = ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"
    core_paths = [Path(__file__), config_path, provenance_path, snapshot_path, action_path,
                  calibration_path, ROOT / "evaluation/controllers/vissim_stackelberg_adapter.py",
                  ROOT / "evaluation/parameters.json", ROOT / "vendor/NumSim-mine/src/config/default.yaml",
                  ROOT / "vendor/NumSim-mine/src/models/state.py"]
    before = {str(p.relative_to(ROOT)): sha(p) for p in core_paths}
    load = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
    provenance, raw, action = map(load, (provenance_path, snapshot_path, action_path))
    for name, value in provenance["env"].items():
        os.environ[name] = str(value)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    tuning = adapter.load_optional_json(str(config_path))
    adapter.install_config_switches(tuning)
    calibration = adapter.deep_update(load(calibration_path), tuning.get("calibration_override", {}))
    detectors = adapter.load_optional_json(str(ROOT / tuning["detector_mapping_json"]))
    detectors, _ = adapter.filter_midblock_links_from_detector_mapping(detectors, tuning)
    local = bool(adapter._link_counts_from_local_observation(raw) and detectors)
    mode = action["metadata"]["adapter_mode"]
    assert mode == "fast-smoke"
    args = (ROOT / "vendor/NumSim-mine", float(raw["control_interval_sec"]),
            float(raw["sim_period_sec"]), mode, calibration, tuning)
    configs = {str(flag): freeze(adapter.build_config(*args, local_observation=local, flagship=flag))
               for flag in (False, True)}
    changes = diff(configs["False"], configs["True"])
    after = {str(p.relative_to(ROOT)): sha(p) for p in core_paths}
    source_changes = [key for key in before if before[key] != after[key]]
    assert not source_changes
    result = {
        "schema_version": "no-control-build-config-comparison/v1",
        "scope": "Real build_config only. No configure_runtime, state projection, forecast, model rollout, controller solve, COM or VISSIM execution.",
        "local_observation": local, "mode": mode, "control_interval_sec": args[1],
        "sim_period_sec": args[2], "flagship_false_role": "live no-control",
        "flagship_true_role": "probe_model_area_integration helper",
        "config_sha256": {key: hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                          for key, value in configs.items()},
        "effective_differences": changes,
        "difference_count": len(changes), "source_sha256_before": before,
        "source_changes": source_changes, "elapsed_sec": time.perf_counter() - started,
        "limitations": ["This compares build_config output before common runtime installers.",
                        "No inference that differing search fields change a held depth=1 rollout.",
                        "No inference that this establishes complete live/replay parity."],
    }
    out = ROOT / "diagnostics/no_control_build_config_comparison.json"
    if out.exists():
        raise FileExistsError(out)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"difference_count": len(changes), "differences": changes,
                      "source_changes": source_changes, "elapsed_sec": result["elapsed_sec"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
