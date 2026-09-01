#!/usr/bin/env python
"""Summarize no-control real-world demand ladder runs into congestion regimes."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


URBAN_CATEGORIES = {"urban_or_other", "local_observable_connector", "freeway_input"}


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def rows_in_window(rows: list[dict[str, str]], start_sec: float, end_sec: float) -> list[dict[str, str]]:
    return [
        row for row in rows
        if start_sec <= fnum(row.get("sim_sec"), -1.0) <= end_sec
    ]


def summarize_freeway(segment_rows: list[dict[str, str]]) -> dict[str, float]:
    speeds = [fnum(row.get("mean_speed_kph")) for row in segment_rows]
    densities = [fnum(row.get("density_veh_km_lane")) for row in segment_rows]
    stopped = [fnum(row.get("stopped_count")) for row in segment_rows]
    n = max(1, len(segment_rows))
    return {
        "freeway_points": float(len(segment_rows)),
        "freeway_speed_p10_kph": percentile(speeds, 0.10),
        "freeway_speed_p50_kph": median(speeds) if speeds else 0.0,
        "freeway_density_p90_veh_km_lane": percentile(densities, 0.90),
        "freeway_density_max_veh_km_lane": max(densities) if densities else 0.0,
        "freeway_speed_lt40_share": sum(1 for value in speeds if value < 40.0) / n,
        "freeway_speed_lt30_share": sum(1 for value in speeds if value < 30.0) / n,
        "freeway_density_gt30_share": sum(1 for value in densities if value > 30.0) / n,
        "freeway_stopped_max": max(stopped) if stopped else 0.0,
    }


def summarize_urban(link_rows: list[dict[str, str]]) -> dict[str, float]:
    by_time: dict[float, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    for row in link_rows:
        if row.get("category") not in URBAN_CATEGORIES:
            continue
        sim_sec = fnum(row.get("sim_sec"))
        count = max(0.0, fnum(row.get("count")))
        stopped = max(0.0, fnum(row.get("stopped_count")))
        speed = max(0.0, fnum(row.get("mean_speed_kph")))
        by_time[sim_sec][0] += count
        by_time[sim_sec][1] += stopped
        by_time[sim_sec][2] += count * speed

    acc = []
    stopped = []
    speeds = []
    production = []
    for sim_sec, values in sorted(by_time.items()):
        count, stop_count, speed_sum = values
        mean_speed = speed_sum / count if count > 0 else 0.0
        acc.append(count)
        stopped.append(stop_count)
        speeds.append(mean_speed)
        production.append((sim_sec, speed_sum))

    peak_time = 0.0
    peak_prod = 0.0
    later_min_prod = 0.0
    if production:
        peak_time, peak_prod = max(production, key=lambda item: item[1])
        later_values = [value for sim_sec, value in production if sim_sec >= peak_time]
        later_min_prod = min(later_values) if later_values else peak_prod
    prod_drop = (peak_prod - later_min_prod) / peak_prod if peak_prod > 0 else 0.0

    n = max(1, len(speeds))
    return {
        "urban_points": float(len(by_time)),
        "urban_acc_p50_veh": median(acc) if acc else 0.0,
        "urban_acc_max_veh": max(acc) if acc else 0.0,
        "urban_speed_p10_kph": percentile(speeds, 0.10),
        "urban_speed_p50_kph": median(speeds) if speeds else 0.0,
        "urban_speed_lt20_share": sum(1 for value in speeds if value < 20.0) / n,
        "urban_speed_lt15_share": sum(1 for value in speeds if value < 15.0) / n,
        "urban_stopped_p50": median(stopped) if stopped else 0.0,
        "urban_stopped_max": max(stopped) if stopped else 0.0,
        "urban_peak_production_veh_km_h": peak_prod,
        "urban_peak_time_sec": peak_time,
        "urban_production_drop_after_peak_pct": 100.0 * prod_drop,
    }


def summarize_state_fallback(state_rows: list[dict[str, str]], summary: dict[str, Any]) -> None:
    if not state_rows:
        return
    speeds = [fnum(row.get("mean_speed_kph")) for row in state_rows]
    freeway_speeds = [fnum(row.get("freeway_mean_speed_kph")) for row in state_rows]
    urban_acc = [fnum(row.get("urban_vehicles")) for row in state_rows]
    stopped = [fnum(row.get("stopped_vehicles")) for row in state_rows]

    if summary.get("freeway_points", 0.0) <= 0.0:
        n = max(1, len(freeway_speeds))
        summary.update({
            "freeway_points": float(len(freeway_speeds)),
            "freeway_speed_p10_kph": percentile(freeway_speeds, 0.10),
            "freeway_speed_p50_kph": median(freeway_speeds) if freeway_speeds else 0.0,
            "freeway_speed_lt40_share": sum(1 for value in freeway_speeds if value < 40.0) / n,
            "freeway_speed_lt30_share": sum(1 for value in freeway_speeds if value < 30.0) / n,
        })
    if summary.get("urban_points", 0.0) <= 0.0:
        n = max(1, len(speeds))
        summary.update({
            "urban_points": float(len(state_rows)),
            "urban_acc_p50_veh": median(urban_acc) if urban_acc else 0.0,
            "urban_acc_max_veh": max(urban_acc) if urban_acc else 0.0,
            "urban_speed_p10_kph": percentile(speeds, 0.10),
            "urban_speed_p50_kph": median(speeds) if speeds else 0.0,
            "urban_speed_lt20_share": sum(1 for value in speeds if value < 20.0) / n,
            "urban_speed_lt15_share": sum(1 for value in speeds if value < 15.0) / n,
            "urban_stopped_p50": median(stopped) if stopped else 0.0,
            "urban_stopped_max": max(stopped) if stopped else 0.0,
        })


def classify(row: dict[str, float]) -> str:
    freeway_clear = (
        row["freeway_speed_lt40_share"] >= 0.15
        and row["freeway_density_gt30_share"] >= 0.15
    )
    urban_clear = (
        row["urban_speed_p50_kph"] < 20.0
        and row["urban_stopped_max"] >= 1200.0
    ) or row["urban_production_drop_after_peak_pct"] >= 15.0 or (
        row["urban_speed_p50_kph"] < 40.0
        and row["urban_stopped_max"] >= 800.0
    )
    severe = (
        row["freeway_speed_lt30_share"] >= 0.10
        or row["urban_speed_lt15_share"] >= 0.25
    )
    if freeway_clear and urban_clear:
        return "mixed_clear_congestion"
    if freeway_clear:
        return "freeway_breakdown_candidate"
    if urban_clear:
        return "urban_storage_congestion"
    if severe:
        return "localized_severe_but_not_global"
    return "marginal_or_ambiguous"


def summarize_case(run_dir: Path, state_csv: Path, start_sec: float, end_sec: float) -> dict[str, Any]:
    name = state_csv.stem.removeprefix("state_")
    state_rows = rows_in_window(read_csv(state_csv), start_sec, end_sec)
    segments = rows_in_window(read_csv(run_dir / f"bottleneck_segments_{name}.csv"), start_sec, end_sec)
    links = rows_in_window(read_csv(run_dir / f"bottleneck_links_{name}.csv"), start_sec, end_sec)
    summary: dict[str, Any] = {
        "case": name,
        "window_start_sec": start_sec,
        "window_end_sec": end_sec,
    }
    summary.update(summarize_freeway(segments))
    summary.update(summarize_urban(links))
    summarize_state_fallback(state_rows, summary)
    summary["regime"] = classify(summary)  # type: ignore[arg-type]
    return summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Real-World No-Control Congestion Ladder",
        "",
        "| case | regime | fw sp<40 | fw den>30 | fw p10 speed | urban p50 speed | urban stopped max | prod drop |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['case']}` | `{row['regime']}` | "
            f"{100.0 * row['freeway_speed_lt40_share']:.1f}% | "
            f"{100.0 * row['freeway_density_gt30_share']:.1f}% | "
            f"{row['freeway_speed_p10_kph']:.1f} | "
            f"{row['urban_speed_p50_kph']:.1f} | "
            f"{row['urban_stopped_max']:.0f} | "
            f"{row['urban_production_drop_after_peak_pct']:.1f}% |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=Path("evaluation/runs/real_world_modi_congestion_ladder_20260724"))
    parser.add_argument("--start-sec", type=float, default=900.0)
    parser.add_argument("--end-sec", type=float, default=2100.0)
    parser.add_argument("--out-prefix", type=Path, default=Path("outputs/real_world_congestion_ladder_20260724"))
    args = parser.parse_args()

    rows = [
        summarize_case(args.run_dir, state_csv, args.start_sec, args.end_sec)
        for state_csv in sorted(args.run_dir.glob("state_no_control_*.csv"))
    ]
    rows.sort(key=lambda row: (row["regime"], -row["urban_stopped_max"], -row["freeway_speed_lt40_share"]))

    csv_path = args.out_prefix.with_suffix(".csv")
    json_path = args.out_prefix.with_suffix(".json")
    md_path = args.out_prefix.with_suffix(".md")
    write_csv(csv_path, rows)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")
    write_md(md_path, rows)
    print(json.dumps({"rows": rows, "outputs": {"csv": str(csv_path), "json": str(json_path), "md": str(md_path)}}, indent=2))


if __name__ == "__main__":
    main()
