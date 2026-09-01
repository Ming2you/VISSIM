from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping


TARGETS = {
    "freeway_total_veh": "freeway_total_scale",
    "urban_queue_plus_link_occupancy_total_veh": "urban_queue_plus_storage_scale",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def nested_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def collect_decision_paths(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".json":
            out.append(path)
        elif path.is_dir():
            out.extend(sorted(path.glob("**/decisions/action_*.json")))
            out.extend(sorted(path.glob("**/action_*.json")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in sorted(out):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def robust_log_ratio_update(
    ratios: list[float],
    prior_scale: float,
    prior_sigma_log: float,
    obs_sigma_log: float,
    min_samples: int,
) -> dict[str, Any]:
    valid = [
        float(v)
        for v in ratios
        if math.isfinite(float(v)) and 0.05 <= float(v) <= 20.0
    ]
    if len(valid) < min_samples:
        return {
            "status": "insufficient_samples",
            "sample_count": len(valid),
            "prior_scale": float(prior_scale),
            "posterior_scale": float(prior_scale),
        }

    logs = [math.log(v) for v in valid]
    obs_mean = mean(logs)
    prior_mean = math.log(max(1.0e-6, prior_scale))
    prior_precision = 1.0 / max(1.0e-6, prior_sigma_log * prior_sigma_log)
    obs_precision = len(logs) / max(1.0e-6, obs_sigma_log * obs_sigma_log)
    posterior_mean = (
        prior_precision * prior_mean + obs_precision * obs_mean
    ) / (prior_precision + obs_precision)
    posterior_sigma = math.sqrt(1.0 / (prior_precision + obs_precision))
    posterior_scale = math.exp(posterior_mean)
    return {
        "status": "ok",
        "sample_count": len(valid),
        "prior_scale": float(prior_scale),
        "posterior_scale": float(posterior_scale),
        "posterior_sigma_log": float(posterior_sigma),
        "ratio_mean": float(mean(valid)),
        "ratio_median": float(median(valid)),
        "ratio_min": float(min(valid)),
        "ratio_max": float(max(valid)),
        "ratio_p10": float(sorted(valid)[max(0, int(0.10 * (len(valid) - 1)))]),
        "ratio_p90": float(sorted(valid)[min(len(valid) - 1, int(0.90 * (len(valid) - 1)))]),
    }


def current_prior_scales(calibration: Mapping[str, Any]) -> dict[str, float]:
    prediction = nested_mapping(calibration.get("prediction"))
    audit = nested_mapping(prediction.get("audit_calibration"))
    return {
        "freeway_total_scale": as_float(
            audit.get("freeway_total_scale", audit.get("freeway_total_observed_over_predicted_mean")),
            1.0,
        ),
        "urban_queue_plus_storage_scale": as_float(
            audit.get(
                "urban_queue_plus_storage_scale",
                audit.get("urban_queue_plus_storage_observed_over_predicted_mean"),
            ),
            1.0,
        ),
    }


def extract_ratios(paths: list[Path]) -> dict[str, dict[str, list[float]]]:
    ratios = {
        key: {
            "raw_observed_over_predicted": [],
            "calibrated_observed_over_predicted": [],
            "active_calibrated_abs_error": [],
            "raw_abs_error": [],
            "raw_predicted": [],
            "observed": [],
        }
        for key in TARGETS
    }
    for path in paths:
        current = read_json(path)
        err = nested_mapping(current.get("prediction_error"))
        if err.get("status") != "ok":
            continue
        scalar_errors = nested_mapping(err.get("scalar_errors"))
        source_path = Path(str(err.get("source_action_json", "")))
        source = read_json(source_path)
        prediction = nested_mapping(source.get("prediction"))
        raw_summary = nested_mapping(prediction.get("state_summary"))
        calibrated_summary = nested_mapping(prediction.get("calibrated_state_summary"))
        for key in TARGETS:
            item = nested_mapping(scalar_errors.get(key))
            observed = as_float(item.get("observed"))
            active_predicted = as_float(item.get("predicted"))
            raw_predicted = as_float(raw_summary.get(key))
            calibrated_predicted = as_float(calibrated_summary.get(key), active_predicted)
            if raw_predicted > 1.0 and observed >= 0.0:
                ratios[key]["raw_observed_over_predicted"].append(observed / raw_predicted)
                ratios[key]["raw_abs_error"].append(abs(observed - raw_predicted))
                ratios[key]["raw_predicted"].append(raw_predicted)
                ratios[key]["observed"].append(observed)
            if calibrated_predicted > 1.0 and observed >= 0.0:
                ratios[key]["calibrated_observed_over_predicted"].append(observed / calibrated_predicted)
                ratios[key]["active_calibrated_abs_error"].append(abs(observed - calibrated_predicted))
    return ratios


def summary_stats(values: list[float]) -> dict[str, float]:
    valid = [float(v) for v in values if math.isfinite(float(v))]
    if not valid:
        return {"count": 0.0, "mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
    ordered = sorted(valid)
    return {
        "count": float(len(valid)),
        "mean": float(mean(valid)),
        "median": float(median(valid)),
        "min": float(min(valid)),
        "max": float(max(valid)),
        "p10": float(ordered[max(0, int(0.10 * (len(ordered) - 1)))]),
        "p90": float(ordered[min(len(ordered) - 1, int(0.90 * (len(ordered) - 1)))]),
    }


def scaled_abs_error_stats(raw_predicted: list[float], observed: list[float], scale: float) -> dict[str, float]:
    values = [
        abs(float(obs) - float(pred) * float(scale))
        for pred, obs in zip(raw_predicted, observed)
        if math.isfinite(float(pred)) and math.isfinite(float(obs))
    ]
    return summary_stats(values)


def markdown_report(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Prediction audit Bayesian calibration update",
        "",
        f"- Source decisions: `{payload.get('decision_count', 0)}`",
        f"- Prior calibration: `{payload.get('calibration_json', '')}`",
        f"- Ratio basis: `{payload.get('ratio_basis', '')}`",
        f"- Policy: patch artifact only; active calibration is not overwritten.",
        "",
        "| target | status | samples | prior | posterior | raw median ratio | calibrated median ratio | raw abs err | active abs err | posterior abs err | posterior vs active |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    updates = nested_mapping(payload.get("updates"))
    for target, update in updates.items():
        item = nested_mapping(update)
        lines.append(
            "| "
            f"`{target}` | `{item.get('status', '')}` | {int(as_float(item.get('sample_count')))} | "
            f"{as_float(item.get('prior_scale'), 1.0):.4f} | {as_float(item.get('posterior_scale'), 1.0):.4f} | "
            f"{as_float(item.get('ratio_median'), 0.0):.4f} | "
            f"{as_float(item.get('active_calibrated_ratio_median'), 0.0):.4f} | "
            f"{as_float(item.get('raw_abs_error_mean'), 0.0):.3f} | "
            f"{as_float(item.get('active_calibrated_abs_error_mean'), 0.0):.3f} | "
            f"{as_float(item.get('posterior_abs_error_mean'), 0.0):.3f} | "
            f"{as_float(item.get('posterior_vs_active_abs_error_pct'), 0.0):.1f}% |"
        )
    lines.extend([
        "",
        "## Caveat",
        "",
        "This is a one-step audit correction fitted from completed controller decisions. The posterior is an absolute scale against the raw source prediction, not a multiplier on the already calibrated prediction. Promote only after held-out validation.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True, help="Run directory or decision JSON. May be repeated.")
    parser.add_argument("--calibration-json", default="evaluation/calibration/vissim_network_calibration_v2_20260628.json")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--prior-sigma-log", type=float, default=0.35)
    parser.add_argument("--obs-sigma-log", type=float, default=0.35)
    parser.add_argument("--min-samples", type=int, default=3)
    args = parser.parse_args()

    calibration_path = Path(args.calibration_json)
    calibration = read_json(calibration_path)
    priors = current_prior_scales(calibration)
    paths = collect_decision_paths([Path(value) for value in args.input])
    ratios = extract_ratios(paths)
    updates: dict[str, Any] = {}
    audit_patch: dict[str, Any] = {
        "enabled": True,
        "mode": "bayesian_summary_scale_patch_not_controller_dynamics",
    }
    for target, scale_key in TARGETS.items():
        target_ratios = ratios.get(target, {})
        update = robust_log_ratio_update(
            target_ratios.get("raw_observed_over_predicted", []),
            prior_scale=priors.get(scale_key, 1.0),
            prior_sigma_log=float(args.prior_sigma_log),
            obs_sigma_log=float(args.obs_sigma_log),
            min_samples=int(args.min_samples),
        )
        calibrated_ratio = summary_stats(target_ratios.get("calibrated_observed_over_predicted", []))
        raw_abs = summary_stats(target_ratios.get("raw_abs_error", []))
        calibrated_abs = summary_stats(target_ratios.get("active_calibrated_abs_error", []))
        posterior_abs = scaled_abs_error_stats(
            target_ratios.get("raw_predicted", []),
            target_ratios.get("observed", []),
            float(update.get("posterior_scale", priors.get(scale_key, 1.0))),
        )
        update["active_calibrated_ratio_median"] = calibrated_ratio.get("median", 0.0)
        update["active_calibrated_ratio_mean"] = calibrated_ratio.get("mean", 0.0)
        update["raw_abs_error_mean"] = raw_abs.get("mean", 0.0)
        update["active_calibrated_abs_error_mean"] = calibrated_abs.get("mean", 0.0)
        update["posterior_abs_error_mean"] = posterior_abs.get("mean", 0.0)
        update["posterior_abs_error_median"] = posterior_abs.get("median", 0.0)
        update["posterior_vs_active_abs_error_pct"] = (
            100.0
            * (float(posterior_abs.get("mean", 0.0)) - float(calibrated_abs.get("mean", 0.0)))
            / max(1.0e-9, float(calibrated_abs.get("mean", 0.0)))
            if calibrated_abs.get("count", 0.0)
            else 0.0
        )
        update["active_calibration_improved_abs_error"] = (
            float(calibrated_abs.get("mean", 0.0)) < float(raw_abs.get("mean", 0.0))
            if raw_abs.get("count", 0.0) and calibrated_abs.get("count", 0.0)
            else None
        )
        updates[target] = update
        audit_patch[scale_key] = float(update.get("posterior_scale", priors.get(scale_key, 1.0)))
    payload = {
        "schema_version": 2,
        "calibration_json": str(calibration_path),
        "decision_count": len(paths),
        "ratio_basis": "observed / source prediction.state_summary raw value",
        "ratio_targets": TARGETS,
        "updates": updates,
        "calibration_patch": {
            "prediction": {
                "audit_calibration": audit_patch,
            },
        },
    }
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(markdown_report(payload), encoding="utf-8")
    print(json.dumps({"status": "ok", "decision_count": len(paths), "out_json": str(out_json), "out_md": str(out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
