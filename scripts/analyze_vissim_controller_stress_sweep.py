from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from summarize_vissim_controller_run import summarize, summarize_files, to_float


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_manifest(out_dir: Path) -> list[dict[str, Any]]:
    path = out_dir / "batch_manifest.json"
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        return raw if isinstance(raw, list) else []
    csv_path = out_dir / "batch_manifest.csv"
    if csv_path.exists():
        return [dict(row) for row in read_csv(csv_path)]
    return [dict(row) for row in read_csv(out_dir / "batch_manifest_partial.csv")]


def pct_delta(value: float, base: float) -> float:
    if abs(base) <= 1.0e-9:
        return 0.0
    return 100.0 * (value - base) / abs(base)


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


def fmt(value: Any, ndigits: int = 3) -> str:
    return f"{to_float(value):.{ndigits}f}"


def build_case_rows(manifest: list[dict[str, Any]], warmup_sec: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in manifest:
        state_csv_text = str(item.get("state_csv", "")).strip()
        action_csv_text = str(item.get("action_csv", "")).strip()
        decision_dir_text = str(item.get("decision_dir", "")).strip()
        if state_csv_text and action_csv_text and decision_dir_text:
            metrics = summarize_files(
                Path(state_csv_text),
                Path(action_csv_text),
                Path(decision_dir_text),
                warmup_sec=warmup_sec,
            )
        else:
            run_dir = Path(state_csv_text).parent
            metrics = summarize(run_dir, warmup_sec=warmup_sec)
        returncode = int(to_float(item.get("returncode"), 999.0))
        if returncode != 0 or not bool(metrics.get("ok", False)):
            continue
        row = {
            "case_id": item.get("case_id", ""),
            "controller": item.get("controller", metrics.get("controller_variants", "")),
            "scenario_id": item.get("scenario_id", ""),
            "category": item.get("category", ""),
            "demand_profile": item.get("demand_profile", ""),
            "urban_volume_vph": to_float(item.get("urban_volume_vph")),
            "freeway_volume_vph": to_float(item.get("freeway_volume_vph")),
            "rand_seed": int(to_float(item.get("rand_seed"), -1.0)),
            "returncode": returncode,
            "elapsed_sec": to_float(item.get("elapsed_sec")),
            **metrics,
        }
        rows.append(row)
    return rows


def add_baseline_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_scenario_seed: dict[tuple[str, int], dict[str, Any]] = {}
    by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if str(row.get("controller")) == "no-control":
            scenario_id = str(row.get("scenario_id"))
            seed = int(to_float(row.get("rand_seed"), -1.0))
            by_scenario_seed[(scenario_id, seed)] = row
            by_scenario[scenario_id].append(row)
    out: list[dict[str, Any]] = []
    for row in rows:
        scenario_id = str(row.get("scenario_id"))
        seed = int(to_float(row.get("rand_seed"), -1.0))
        base = by_scenario_seed.get((scenario_id, seed))
        if base is None:
            candidates = by_scenario.get(scenario_id, [])
            base = candidates[0] if candidates else None
        item = dict(row)
        if base:
            for key in (
                "vehicle_hours_total",
                "stopped_vehicle_hours",
                "mean_speed_kph",
                "mean_total_vehicles",
                "final_total_vehicles",
                "prediction_total_abs_error_mean_veh",
            ):
                item[f"{key}_delta_vs_no_control"] = to_float(item.get(key)) - to_float(base.get(key))
                item[f"{key}_pct_vs_no_control"] = pct_delta(to_float(item.get(key)), to_float(base.get(key)))
        out.append(item)
    return out


def build_controller_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("controller")), str(row.get("category")))].append(row)
    out: list[dict[str, Any]] = []
    keys = [
        "vehicle_hours_total_pct_vs_no_control",
        "stopped_vehicle_hours_pct_vs_no_control",
        "mean_speed_kph_pct_vs_no_control",
        "prediction_total_abs_error_mean_veh_pct_vs_no_control",
        "mean_decision_wall_sec",
        "mean_signal_split_abs_sec",
        "mean_signal_offset_abs_sec",
        "vsl_mean_abs_step_kph",
        "ramp_green_abs_step_sec",
        "controller_error_count",
        "fallback_state_rows",
    ]
    for (controller, category), items in sorted(groups.items()):
        row: dict[str, Any] = {
            "controller": controller,
            "category": category,
            "case_count": len(items),
            "scenarios": ",".join(str(item.get("scenario_id")) for item in items),
        }
        for key in keys:
            vals = [to_float(item.get(key)) for item in items]
            row[f"mean_{key}"] = mean(vals) if vals else 0.0
            row[f"max_{key}"] = max(vals) if vals else 0.0
        out.append(row)
    return out


def write_markdown(path: Path, rows: list[dict[str, Any]], controller_summary: list[dict[str, Any]]) -> None:
    lines = [
        "# Vissim controller stress sweep",
        "",
        "Negative `% vs no-control` for vehicle-hours/stopped-hours means improvement.",
        "",
        "## Scenario-level comparison",
        "",
        "| category | scenario | controller | total veh-h | total % | stopped veh-h | stopped % | speed | speed % | pred abs err | wall s | action movement |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in sorted(rows, key=lambda r: (str(r.get("category")), str(r.get("scenario_id")), str(r.get("controller")))):
        action_bits = (
            f"split={fmt(row.get('mean_signal_split_abs_sec'))}s, "
            f"offset={fmt(row.get('mean_signal_offset_abs_sec'))}s, "
            f"vsl-step={fmt(row.get('vsl_mean_abs_step_kph'))}, "
            f"ramp-step={fmt(row.get('ramp_green_abs_step_sec'))}"
        )
        lines.append(
            "| "
            f"{row.get('category')} | `{row.get('scenario_id')}` | `{row.get('controller')}` | "
            f"{fmt(row.get('vehicle_hours_total'))} | {fmt(row.get('vehicle_hours_total_pct_vs_no_control'))}% | "
            f"{fmt(row.get('stopped_vehicle_hours'))} | {fmt(row.get('stopped_vehicle_hours_pct_vs_no_control'))}% | "
            f"{fmt(row.get('mean_speed_kph'))} | {fmt(row.get('mean_speed_kph_pct_vs_no_control'))}% | "
            f"{fmt(row.get('prediction_total_abs_error_mean_veh'))} | {fmt(row.get('mean_decision_wall_sec'))} | "
            f"{action_bits} |"
        )
    lines.extend([
        "",
        "## Controller/category aggregate",
        "",
        "| category | controller | cases | mean total % | mean stopped % | mean speed % | mean pred err % | wall s |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in sorted(controller_summary, key=lambda r: (str(r.get("category")), str(r.get("controller")))):
        lines.append(
            "| "
            f"{row.get('category')} | `{row.get('controller')}` | {row.get('case_count')} | "
            f"{fmt(row.get('mean_vehicle_hours_total_pct_vs_no_control'))}% | "
            f"{fmt(row.get('mean_stopped_vehicle_hours_pct_vs_no_control'))}% | "
            f"{fmt(row.get('mean_mean_speed_kph_pct_vs_no_control'))}% | "
            f"{fmt(row.get('mean_prediction_total_abs_error_mean_veh_pct_vs_no_control'))}% | "
            f"{fmt(row.get('mean_mean_decision_wall_sec'))} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--warmup-sec", type=float, default=120.0)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    manifest = read_manifest(out_dir)
    rows = add_baseline_deltas(build_case_rows(manifest, warmup_sec=float(args.warmup_sec)))
    controller_summary = build_controller_summary(rows)
    write_csv(out_dir / "stress_case_summary.csv", rows)
    write_csv(out_dir / "stress_controller_summary.csv", controller_summary)
    payload = {
        "status": "ok",
        "warmup_sec": float(args.warmup_sec),
        "cases": rows,
        "controller_summary": controller_summary,
    }
    (out_dir / "stress_summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(out_dir / "stress_summary.md", rows, controller_summary)
    print(json.dumps({
        "status": "ok",
        "case_count": len(rows),
        "summary_md": str(out_dir / "stress_summary.md"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
