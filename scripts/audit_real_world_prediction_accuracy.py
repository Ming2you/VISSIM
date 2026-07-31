#!/usr/bin/env python
"""Audit one-step MPC prediction accuracy from real-world VISSIM action JSONs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


METRIC_GROUPS = {
    "total_model_vehicles": "overall",
    "freeway_total_veh": "metanet_freeway",
    "freeway_segment_total_veh": "metanet_freeway",
    "freeway_mean_density_veh_km_lane": "metanet_freeway",
    "freeway_mean_speed_kph": "metanet_freeway",
    "protected_accumulation_veh": "kashani_urban",
    "urban_queue_plus_link_occupancy_total_veh": "kashani_urban",
    "urban_movement_queue_total_veh": "kashani_urban",
    "urban_link_occupancy_total_veh": "kashani_urban",
    "urban_total_veh": "kashani_urban",
    "boundary_queue_total_veh": "interface_queue",
    "off_ramp_storage_veh": "interface_queue",
    "ramp_queue_total_veh": "interface_queue",
    "mainline_origin_queue_total_veh": "interface_queue",
}


KEY_METRICS = [
    "total_model_vehicles",
    "freeway_total_veh",
    "freeway_mean_density_veh_km_lane",
    "freeway_mean_speed_kph",
    "protected_accumulation_veh",
    "urban_queue_plus_link_occupancy_total_veh",
    "urban_movement_queue_total_veh",
    "urban_link_occupancy_total_veh",
    "ramp_queue_total_veh",
    "off_ramp_storage_veh",
]


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        out = float(value)
        return out if math.isfinite(out) else float(default)
    except (TypeError, ValueError):
        return float(default)


def read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def iter_error_rows(decision_dir: Path, warmup_sec: float, end_sec: float | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(decision_dir.glob("action_*.json")):
        raw = read_json(path)
        pred_err = raw.get("prediction_error")
        if not isinstance(pred_err, dict) or pred_err.get("status") != "ok":
            continue
        observed_sec = fnum(pred_err.get("observed_sim_sec"))
        if observed_sec < warmup_sec:
            continue
        if end_sec is not None and observed_sec > float(end_sec):
            continue
        scalar = pred_err.get("scalar_errors")
        if not isinstance(scalar, dict):
            continue
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        for metric, item in scalar.items():
            if not isinstance(item, dict):
                continue
            predicted = fnum(item.get("predicted"))
            observed = fnum(item.get("observed"))
            error = fnum(item.get("error"), observed - predicted)
            abs_error = abs(error)
            rows.append({
                "action_json": path.name,
                "predicted_from_sim_sec": fnum(pred_err.get("predicted_from_sim_sec")),
                "predicted_for_sim_sec": fnum(pred_err.get("predicted_for_sim_sec")),
                "observed_sim_sec": observed_sec,
                "target_lag_sec": fnum(pred_err.get("target_lag_sec")),
                "metric_group": METRIC_GROUPS.get(str(metric), "other"),
                "metric": str(metric),
                "predicted": predicted,
                "observed": observed,
                "error_observed_minus_predicted": error,
                "abs_error": abs_error,
                "relative_error_vs_predicted": fnum(item.get("relative_error")),
                "controller_status": str(metadata.get("controller_status", "")),
                "controller_variant": str(metadata.get("controller_variant", "")),
                "decision_wall_sec": fnum(metadata.get("decision_wall_sec")),
                "prediction_wall_sec": fnum(metadata.get("prediction_wall_sec")),
            })
    return rows


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_metric: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_metric[str(row["metric"])].append(row)

    out: list[dict[str, Any]] = []
    for metric, items in sorted(by_metric.items(), key=lambda pair: (METRIC_GROUPS.get(pair[0], "z"), pair[0])):
        predicted = [fnum(row["predicted"]) for row in items]
        observed = [fnum(row["observed"]) for row in items]
        errors = [fnum(row["error_observed_minus_predicted"]) for row in items]
        abs_errors = [abs(value) for value in errors]
        rel_errors = [fnum(row["relative_error_vs_predicted"]) for row in items]
        mean_observed_abs = mean(abs(value) for value in observed) if observed else 0.0
        rmse = math.sqrt(mean(value * value for value in errors)) if errors else 0.0
        out.append({
            "metric_group": METRIC_GROUPS.get(metric, "other"),
            "metric": metric,
            "n": len(items),
            "mean_observed": mean(observed) if observed else 0.0,
            "mean_predicted": mean(predicted) if predicted else 0.0,
            "bias_observed_minus_predicted": mean(errors) if errors else 0.0,
            "mae": mean(abs_errors) if abs_errors else 0.0,
            "rmse": rmse,
            "mae_pct_of_mean_observed": 100.0 * mean(abs_errors) / mean_observed_abs if mean_observed_abs > 1.0e-9 else 0.0,
            "mean_relative_error_vs_predicted": mean(rel_errors) if rel_errors else 0.0,
            "max_abs_error": max(abs_errors) if abs_errors else 0.0,
        })
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, summary_rows: list[dict[str, Any]], source: dict[str, Any]) -> None:
    lines = [
        "# Real-World MPC One-Step Prediction Accuracy",
        "",
        f"- decision_dir: `{source['decision_dir']}`",
        f"- warmup_sec: `{source['warmup_sec']}`",
        f"- end_sec: `{source['end_sec']}`",
        "",
        "| group | metric | n | observed | predicted | bias obs-pred | MAE | MAE % obs | RMSE | max AE |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    wanted = [row for row in summary_rows if row["metric"] in KEY_METRICS]
    for row in wanted:
        lines.append(
            f"| `{row['metric_group']}` | `{row['metric']}` | {row['n']} | "
            f"{row['mean_observed']:.3f} | {row['mean_predicted']:.3f} | "
            f"{row['bias_observed_minus_predicted']:.3f} | {row['mae']:.3f} | "
            f"{row['mae_pct_of_mean_observed']:.1f}% | {row['rmse']:.3f} | {row['max_abs_error']:.3f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision-dir", type=Path, required=True)
    parser.add_argument("--warmup-sec", type=float, default=900.0)
    parser.add_argument("--end-sec", type=float, default=None)
    parser.add_argument("--out-prefix", type=Path, default=Path("outputs/real_world_prediction_accuracy"))
    args = parser.parse_args()

    rows = iter_error_rows(args.decision_dir, args.warmup_sec, args.end_sec)
    summary_rows = summarize(rows)
    raw_csv = args.out_prefix.with_name(args.out_prefix.name + "_rows.csv")
    summary_csv = args.out_prefix.with_name(args.out_prefix.name + "_summary.csv")
    summary_json = args.out_prefix.with_name(args.out_prefix.name + "_summary.json")
    summary_md = args.out_prefix.with_name(args.out_prefix.name + "_summary.md")
    write_csv(raw_csv, rows)
    write_csv(summary_csv, summary_rows)
    source = {
        "decision_dir": str(args.decision_dir),
        "warmup_sec": args.warmup_sec,
        "end_sec": args.end_sec,
        "row_count": len(rows),
        "metric_count": len(summary_rows),
        "raw_csv": str(raw_csv),
        "summary_csv": str(summary_csv),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps({"source": source, "summary": summary_rows}, indent=2), encoding="utf-8")
    write_md(summary_md, summary_rows, source)
    print(json.dumps({"source": source, "summary": summary_rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
