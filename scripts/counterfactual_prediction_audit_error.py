from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping


KEY_METRICS = [
    "total_model_vehicles",
    "freeway_total_veh",
    "freeway_segment_total_veh",
    "freeway_mean_density_veh_km_lane",
    "freeway_mean_speed_kph",
    "urban_queue_plus_link_occupancy_total_veh",
    "protected_accumulation_veh",
    "urban_movement_queue_total_veh",
    "urban_link_occupancy_total_veh",
    "urban_total_veh",
    "boundary_queue_total_veh",
    "off_ramp_storage_veh",
    "ramp_queue_total_veh",
    "mainline_origin_queue_total_veh",
]

SCALE_MIN = 0.05
SCALE_MAX = 5.0


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
        out = float(value)
        return out if math.isfinite(out) else float(default)
    except (TypeError, ValueError):
        return float(default)


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def collect_decision_paths(inputs: list[Path]) -> list[Path]:
    out: list[Path] = []
    for path in inputs:
        if path.is_file() and path.suffix.lower() == ".json":
            out.append(path)
        elif path.is_dir():
            out.extend(sorted(path.glob("action_*.json")))
            out.extend(sorted(path.glob("**/action_*.json")))
            out.extend(sorted(path.glob("**/decisions/action_*.json")))
    return sorted(set(path.resolve() for path in out))


def valid_scale(value: Any, default: float = 1.0) -> float:
    scale = as_float(value, default)
    return scale if SCALE_MIN <= scale <= SCALE_MAX else default


def calibration_audit(calibration: Mapping[str, Any]) -> Mapping[str, Any]:
    prediction = mapping(calibration.get("prediction"))
    return mapping(prediction.get("audit_calibration"))


def apply_audit(summary: Mapping[str, Any], calibration: Mapping[str, Any]) -> dict[str, float]:
    out = {str(k): as_float(v) for k, v in summary.items() if isinstance(v, (int, float))}
    audit = calibration_audit(calibration)
    if not audit or not bool(audit.get("enabled", True)):
        return out

    freeway_scale = valid_scale(
        audit.get("freeway_total_scale", audit.get("freeway_total_observed_over_predicted_mean")),
        1.0,
    )
    urban_scale = valid_scale(
        audit.get(
            "urban_queue_plus_storage_scale",
            audit.get("urban_queue_plus_storage_observed_over_predicted_mean"),
        ),
        1.0,
    )

    raw_freeway = as_float(summary.get("freeway_total_veh"))
    raw_segment = as_float(summary.get("freeway_segment_total_veh"), raw_freeway)
    scaled_freeway = raw_freeway * freeway_scale
    scaled_segment = raw_segment * freeway_scale
    out["freeway_total_veh"] = scaled_freeway
    out["freeway_segment_total_veh"] = scaled_segment
    out["freeway_mean_density_veh_km_lane"] = (
        as_float(summary.get("freeway_mean_density_veh_km_lane")) * freeway_scale
    )
    out["total_model_vehicles"] = as_float(summary.get("total_model_vehicles")) + (scaled_freeway - raw_freeway)

    component_scales = mapping(audit.get("component_scales"))
    scale_aliases = {
        "total_model_vehicles": "total_model_vehicles_scale",
        "urban_total_veh": "urban_total_scale",
        "protected_accumulation_veh": "protected_accumulation_scale",
        "urban_movement_queue_total_veh": "urban_movement_queue_scale",
        "urban_link_occupancy_total_veh": "urban_link_occupancy_scale",
        "boundary_queue_total_veh": "boundary_queue_scale",
        "off_ramp_storage_veh": "off_ramp_storage_scale",
        "ramp_queue_total_veh": "ramp_queue_scale",
        "mainline_origin_queue_total_veh": "mainline_origin_queue_scale",
        "freeway_mean_speed_kph": "freeway_mean_speed_scale",
    }
    already_scaled = {
        "freeway_total_veh",
        "freeway_segment_total_veh",
        "freeway_mean_density_veh_km_lane",
        "urban_queue_plus_link_occupancy_total_veh",
    }
    scaled_metrics: set[str] = set()
    for metric, alias in scale_aliases.items():
        if metric in already_scaled or metric not in summary:
            continue
        raw_scale = component_scales.get(metric, audit.get(alias))
        if raw_scale is None:
            continue
        scale = valid_scale(raw_scale, 1.0)
        out[metric] = as_float(summary.get(metric)) * scale
        scaled_metrics.add(metric)

    if "urban_queue_plus_link_occupancy_total_veh" in summary:
        recompute_queue_storage = bool(
            audit.get(
                "recompute_urban_queue_plus_storage_from_components",
                audit.get("preserve_component_consistency", False),
            )
        )
        if recompute_queue_storage and {
            "urban_movement_queue_total_veh",
            "urban_link_occupancy_total_veh",
        } & scaled_metrics:
            out["urban_queue_plus_link_occupancy_total_veh"] = (
                as_float(out.get("urban_movement_queue_total_veh"))
                + as_float(out.get("urban_link_occupancy_total_veh"))
            )
        else:
            out["urban_queue_plus_link_occupancy_total_veh"] = (
                as_float(summary.get("urban_queue_plus_link_occupancy_total_veh")) * urban_scale
            )

    if bool(
        audit.get(
            "recompute_urban_total_from_components",
            audit.get("preserve_component_consistency", False),
        )
    ) and {
        "urban_movement_queue_total_veh",
        "urban_link_occupancy_total_veh",
        "off_ramp_storage_veh",
    } & scaled_metrics:
        movement = as_float(out.get("urban_movement_queue_total_veh"))
        link_occupancy = as_float(out.get("urban_link_occupancy_total_veh"))
        off_ramp_storage = as_float(out.get("off_ramp_storage_veh"))
        out["urban_total_veh"] = movement + max(0.0, link_occupancy - off_ramp_storage)

    if bool(
        audit.get(
            "recompute_total_model_vehicles_from_components",
            audit.get("preserve_component_consistency", False),
        )
    ) and {
        "urban_total_veh",
        "off_ramp_storage_veh",
        "urban_movement_queue_total_veh",
        "urban_link_occupancy_total_veh",
    } & scaled_metrics:
        out["total_model_vehicles"] = (
            as_float(out.get("urban_total_veh"))
            + as_float(out.get("freeway_total_veh"))
            + as_float(out.get("off_ramp_storage_veh"))
        )
    return out


def case_label(path: Path) -> tuple[str, str, str]:
    case_dir = path.parents[1]
    case = read_json(case_dir / "case.json")
    if "case" in case and isinstance(case["case"], dict):
        case = case["case"]
    scenario = mapping(case.get("scenario"))
    return (
        str(case.get("controller", "all") or "all"),
        str(scenario.get("scenario_id", case.get("scenario_id", "")) or ""),
        str(case.get("rand_seed", "") or ""),
    )


def analyze(
    paths: list[Path],
    calibration: Mapping[str, Any],
    warmup_sec: float,
    end_sec: float | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        current = read_json(path)
        err = mapping(current.get("prediction_error"))
        if err.get("status") != "ok":
            continue
        observed_sec = as_float(err.get("observed_sim_sec"))
        if observed_sec < warmup_sec:
            continue
        if end_sec is not None and observed_sec > end_sec:
            continue
        source = read_json(Path(str(err.get("source_action_json", ""))))
        pred = mapping(source.get("prediction"))
        raw_summary = mapping(pred.get("state_summary"))
        active_summary = mapping(pred.get("calibrated_state_summary"))
        v3_summary = apply_audit(raw_summary, calibration)
        scalar = mapping(err.get("scalar_errors"))
        controller, scenario, seed = case_label(path)
        for metric in KEY_METRICS:
            item = mapping(scalar.get(metric))
            if not item:
                continue
            observed = as_float(item.get("observed"))
            raw_pred = as_float(raw_summary.get(metric))
            active_pred = as_float(active_summary.get(metric), as_float(item.get("predicted")))
            v3_pred = as_float(v3_summary.get(metric), raw_pred)
            rows.append({
                "decision_json": str(path),
                "controller": controller,
                "scenario_id": scenario,
                "rand_seed": seed,
                "observed_sim_sec": observed_sec,
                "metric": metric,
                "observed": observed,
                "raw_predicted": raw_pred,
                "active_predicted": active_pred,
                "counterfactual_predicted": v3_pred,
                "raw_abs_error": abs(observed - raw_pred),
                "active_abs_error": abs(observed - active_pred),
                "counterfactual_abs_error": abs(observed - v3_pred),
            })
    return rows


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("controller")), str(row.get("metric")))].append(row)
    out: list[dict[str, Any]] = []
    for (controller, metric), items in sorted(groups.items()):
        observed = [as_float(row.get("observed")) for row in items]
        raw_predicted = [as_float(row.get("raw_predicted")) for row in items]
        active_predicted = [as_float(row.get("active_predicted")) for row in items]
        cf_predicted = [as_float(row.get("counterfactual_predicted")) for row in items]
        raw = [as_float(row.get("raw_abs_error")) for row in items]
        active = [as_float(row.get("active_abs_error")) for row in items]
        cf = [as_float(row.get("counterfactual_abs_error")) for row in items]
        active_mean = mean(active) if active else 0.0
        cf_mean = mean(cf) if cf else 0.0
        out.append({
            "controller": controller,
            "metric": metric,
            "n": len(items),
            "mean_observed": mean(observed) if observed else 0.0,
            "mean_raw_predicted": mean(raw_predicted) if raw_predicted else 0.0,
            "mean_active_predicted": mean(active_predicted) if active_predicted else 0.0,
            "mean_counterfactual_predicted": mean(cf_predicted) if cf_predicted else 0.0,
            "raw_abs_error_mean": mean(raw) if raw else 0.0,
            "active_abs_error_mean": active_mean,
            "counterfactual_abs_error_mean": cf_mean,
            "counterfactual_vs_active_pct": 100.0 * (cf_mean - active_mean) / max(1.0e-9, active_mean),
            "counterfactual_abs_error_median": median(cf) if cf else 0.0,
        })
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, summary_rows: list[dict[str, Any]], calibration_json: Path) -> None:
    lines = [
        "# Counterfactual prediction audit error",
        "",
        f"- Counterfactual calibration: `{calibration_json}`",
        "- Active means the prediction summary already stored in existing action JSONs.",
        "- Counterfactual reapplies the candidate audit scales to the raw source prediction summary.",
        "",
        "| controller | metric | n | observed | active pred | cf pred | active abs | cf abs | cf vs active |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    order = {metric: idx for idx, metric in enumerate(KEY_METRICS)}
    filtered = [row for row in summary_rows if row["metric"] in order]
    filtered.sort(key=lambda row: order[str(row["metric"])])
    for row in filtered:
        lines.append(
            "| "
            f"`{row['controller']}` | `{row['metric']}` | {row['n']} | "
            f"{as_float(row['mean_observed']):.3f} | "
            f"{as_float(row['mean_active_predicted']):.3f} | "
            f"{as_float(row['mean_counterfactual_predicted']):.3f} | "
            f"{as_float(row['active_abs_error_mean']):.3f} | "
            f"{as_float(row['counterfactual_abs_error_mean']):.3f} | "
            f"{as_float(row['counterfactual_vs_active_pct']):.1f}% |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--calibration-json", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--warmup-sec", type=float, default=0.0)
    parser.add_argument("--end-sec", type=float, default=None)
    args = parser.parse_args()

    calibration_json = Path(args.calibration_json)
    calibration = read_json(calibration_json)
    paths = collect_decision_paths([Path(value) for value in args.input])
    rows = analyze(paths, calibration, args.warmup_sec, args.end_sec)
    summary_rows = summarize(rows)
    out_dir = Path(args.out_dir)
    write_csv(out_dir / "counterfactual_prediction_error_rows.csv", rows)
    write_csv(out_dir / "counterfactual_prediction_error_summary.csv", summary_rows)
    (out_dir / "counterfactual_prediction_error_summary.json").write_text(
        json.dumps({"summary": summary_rows}, indent=2),
        encoding="utf-8",
    )
    write_md(out_dir / "counterfactual_prediction_error.md", summary_rows, calibration_json)
    print(json.dumps({
        "status": "ok",
        "decision_count": len(paths),
        "row_count": len(rows),
        "summary_md": str(out_dir / "counterfactual_prediction_error.md"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
