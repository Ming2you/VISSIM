from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def run_label(run_dir: Path, *, include_parent_label: bool = False) -> str:
    if include_parent_label:
        return f"{run_dir.parent.name}/{run_dir.name}"
    return run_dir.name


def iter_action_jsons(run_dir: Path) -> list[Path]:
    decision_dir = run_dir / "decisions"
    return sorted(decision_dir.glob("action_*.json"))


def read_case_json(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "case.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        case = raw.get("case", raw)
        return case if isinstance(case, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def summarize_run(run_dir: Path, *, include_parent_label: bool = False) -> list[dict[str, Any]]:
    case = read_case_json(run_dir)
    rows_by_metric: dict[str, list[dict[str, float]]] = defaultdict(list)
    meta_rows: list[dict[str, float]] = []
    for path in iter_action_jsons(run_dir):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        meta = raw.get("metadata", {})
        if isinstance(meta, dict):
            meta_rows.append({
                "decision_wall_sec": to_float(meta.get("decision_wall_sec")),
                "prediction_wall_sec": to_float(meta.get("prediction_wall_sec")),
                "prediction_total_abs_error": to_float(meta.get("prediction_total_model_vehicles_abs_error")),
                "prediction_np_abs_error": to_float(meta.get("prediction_protected_accumulation_abs_error")),
                "prediction_freeway_abs_error": to_float(meta.get("prediction_freeway_total_abs_error")),
                "density_excess_veh": to_float(meta.get("meta_distributed_response_density_excess_veh")),
                "spillback_violation_veh": to_float(meta.get("meta_distributed_response_total_spillback_violation_veh")),
                "spillback_penalty": to_float(meta.get("meta_distributed_response_spillback_penalty")),
            })
        pred_err = raw.get("prediction_error", {})
        if not isinstance(pred_err, dict) or pred_err.get("status") != "ok":
            continue
        scalar = pred_err.get("scalar_errors", {})
        if not isinstance(scalar, dict):
            continue
        for metric, err in scalar.items():
            if not isinstance(err, dict):
                continue
            rows_by_metric[str(metric)].append({
                "predicted": to_float(err.get("predicted")),
                "observed": to_float(err.get("observed")),
                "error": to_float(err.get("error")),
                "abs_error": to_float(err.get("abs_error")),
                "relative_error": to_float(err.get("relative_error")),
            })

    def avg(items: list[dict[str, float]], key: str) -> float:
        vals = [row[key] for row in items]
        return float(mean(vals)) if vals else 0.0

    out: list[dict[str, Any]] = []
    for metric, items in sorted(rows_by_metric.items()):
        out.append({
            "run_dir": str(run_dir),
            "run_label": run_label(run_dir, include_parent_label=include_parent_label),
            "controller": case.get("controller", ""),
            "scenario_id": (case.get("scenario") or {}).get("scenario_id", case.get("scenario_id", "")),
            "demand_profile": (case.get("scenario") or {}).get("demand_profile", ""),
            "metric": metric,
            "decision_count": len(items),
            "mean_predicted": avg(items, "predicted"),
            "mean_observed": avg(items, "observed"),
            "mean_error_observed_minus_predicted": avg(items, "error"),
            "mean_abs_error": avg(items, "abs_error"),
            "mean_relative_error": avg(items, "relative_error"),
            "mean_decision_wall_sec": avg(meta_rows, "decision_wall_sec"),
            "mean_prediction_total_abs_error": avg(meta_rows, "prediction_total_abs_error"),
            "mean_prediction_np_abs_error": avg(meta_rows, "prediction_np_abs_error"),
            "mean_prediction_freeway_abs_error": avg(meta_rows, "prediction_freeway_abs_error"),
            "mean_density_excess_veh": avg(meta_rows, "density_excess_veh"),
            "mean_spillback_violation_veh": avg(meta_rows, "spillback_violation_veh"),
            "mean_spillback_penalty": avg(meta_rows, "spillback_penalty"),
        })
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    key_metrics = {
        "total_model_vehicles",
        "protected_accumulation_veh",
        "urban_queue_plus_link_occupancy_total_veh",
        "urban_movement_queue_total_veh",
        "urban_link_occupancy_total_veh",
        "freeway_total_veh",
        "freeway_segment_total_veh",
        "ramp_queue_total_veh",
        "freeway_mean_speed_kph",
    }
    lines = [
        "# Prediction error component diagnostics",
        "",
        "`error` is observed minus predicted. Positive means the model under-predicted the observed value.",
        "",
        "| run | controller | scenario | metric | mean observed | mean predicted | mean error | mean abs error | rel error | density excess | spillback |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    filtered = [row for row in rows if row.get("metric") in key_metrics]
    for row in sorted(filtered, key=lambda r: (str(r.get("run_label")), str(r.get("metric")))):
        lines.append(
            "| "
            f"{row.get('run_label')} | "
            f"{row.get('controller')} | "
            f"{row.get('scenario_id')} | "
            f"`{row.get('metric')}` | "
            f"{to_float(row.get('mean_observed')):.3f} | "
            f"{to_float(row.get('mean_predicted')):.3f} | "
            f"{to_float(row.get('mean_error_observed_minus_predicted')):.3f} | "
            f"{to_float(row.get('mean_abs_error')):.3f} | "
            f"{to_float(row.get('mean_relative_error')):.3f} | "
            f"{to_float(row.get('mean_density_excess_veh')):.3f} | "
            f"{to_float(row.get('mean_spillback_violation_veh')):.3f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dirs", nargs="+")
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument(
        "--include-parent-label",
        action="store_true",
        help="Prefix each run label with its parent directory name to make cross-batch comparisons unambiguous.",
    )
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    for item in args.run_dirs:
        rows.extend(summarize_run(Path(item), include_parent_label=args.include_parent_label))
    out_csv = Path(args.out_csv)
    out_md = Path(args.out_md)
    write_csv(out_csv, rows)
    write_markdown(out_md, rows)
    print(json.dumps({
        "status": "ok",
        "rows": len(rows),
        "out_csv": str(out_csv),
        "out_md": str(out_md),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
