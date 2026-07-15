from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping


KEY_METRICS = [
    "total_model_vehicles",
    "freeway_total_veh",
    "freeway_segment_total_veh",
    "urban_queue_plus_link_occupancy_total_veh",
    "protected_accumulation_veh",
    "urban_total_veh",
    "off_ramp_storage_veh",
    "ramp_queue_total_veh",
]


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


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def collect_decision_paths(inputs: list[Path]) -> list[Path]:
    out: list[Path] = []
    for path in inputs:
        if path.is_file() and path.suffix.lower() == ".json":
            out.append(path)
        elif path.is_dir():
            out.extend(sorted(path.glob("**/decisions/action_*.json")))
    return sorted(set(path.resolve() for path in out))


def calibration_scales(calibration: Mapping[str, Any]) -> tuple[float, float]:
    prediction = mapping(calibration.get("prediction"))
    audit = mapping(prediction.get("audit_calibration"))
    freeway = as_float(audit.get("freeway_total_scale", audit.get("freeway_total_observed_over_predicted_mean")), 1.0)
    urban = as_float(
        audit.get("urban_queue_plus_storage_scale", audit.get("urban_queue_plus_storage_observed_over_predicted_mean")),
        1.0,
    )
    return freeway, urban


def apply_audit(summary: Mapping[str, Any], freeway_scale: float, urban_scale: float) -> dict[str, float]:
    out = {str(k): as_float(v) for k, v in summary.items() if isinstance(v, (int, float))}
    raw_freeway = as_float(summary.get("freeway_total_veh"))
    raw_segment = as_float(summary.get("freeway_segment_total_veh"), raw_freeway)
    scaled_freeway = raw_freeway * freeway_scale
    scaled_segment = raw_segment * freeway_scale
    out["freeway_total_veh"] = scaled_freeway
    out["freeway_segment_total_veh"] = scaled_segment
    out["total_model_vehicles"] = as_float(summary.get("total_model_vehicles")) + (scaled_freeway - raw_freeway)
    if "urban_queue_plus_link_occupancy_total_veh" in summary:
        out["urban_queue_plus_link_occupancy_total_veh"] = (
            as_float(summary.get("urban_queue_plus_link_occupancy_total_veh")) * urban_scale
        )
    return out


def case_label(path: Path) -> tuple[str, str, str]:
    case_dir = path.parents[1]
    case = read_json(case_dir / "case.json")
    if "case" in case and isinstance(case["case"], dict):
        case = case["case"]
    scenario = mapping(case.get("scenario"))
    return (
        str(case.get("controller", "")),
        str(scenario.get("scenario_id", case.get("scenario_id", ""))),
        str(case.get("rand_seed", "")),
    )


def analyze(paths: list[Path], calibration: Mapping[str, Any]) -> list[dict[str, Any]]:
    freeway_scale, urban_scale = calibration_scales(calibration)
    rows: list[dict[str, Any]] = []
    for path in paths:
        current = read_json(path)
        err = mapping(current.get("prediction_error"))
        if err.get("status") != "ok":
            continue
        source = read_json(Path(str(err.get("source_action_json", ""))))
        pred = mapping(source.get("prediction"))
        raw_summary = mapping(pred.get("state_summary"))
        active_summary = mapping(pred.get("calibrated_state_summary"))
        v3_summary = apply_audit(raw_summary, freeway_scale, urban_scale)
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
        raw = [as_float(row.get("raw_abs_error")) for row in items]
        active = [as_float(row.get("active_abs_error")) for row in items]
        cf = [as_float(row.get("counterfactual_abs_error")) for row in items]
        active_mean = mean(active) if active else 0.0
        cf_mean = mean(cf) if cf else 0.0
        out.append({
            "controller": controller,
            "metric": metric,
            "n": len(items),
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
        "| controller | metric | n | raw abs | active abs | counterfactual abs | cf vs active |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    preferred = set(KEY_METRICS[:4])
    filtered = [row for row in summary_rows if row["metric"] in preferred]
    for row in filtered:
        lines.append(
            "| "
            f"`{row['controller']}` | `{row['metric']}` | {row['n']} | "
            f"{as_float(row['raw_abs_error_mean']):.3f} | "
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
    args = parser.parse_args()

    calibration_json = Path(args.calibration_json)
    calibration = read_json(calibration_json)
    paths = collect_decision_paths([Path(value) for value in args.input])
    rows = analyze(paths, calibration)
    summary_rows = summarize(rows)
    out_dir = Path(args.out_dir)
    write_csv(out_dir / "counterfactual_prediction_error_rows.csv", rows)
    write_csv(out_dir / "counterfactual_prediction_error_summary.csv", summary_rows)
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
