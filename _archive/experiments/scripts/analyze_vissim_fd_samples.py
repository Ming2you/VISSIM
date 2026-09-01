from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Any


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    if math.isfinite(out):
        return out
    return default


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * max(0.0, min(1.0, q))
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    weight = pos - lo
    return xs[lo] * (1.0 - weight) + xs[hi] * weight


def iter_state_files(input_dir: Path) -> list[Path]:
    return sorted(input_dir.glob("state_*.json"))


def sample_rows(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    sim_sec = as_float(raw.get("sim_sec"))
    out: list[dict[str, Any]] = []
    for model_link, segments in dict(raw.get("freeway_segments", {})).items():
        if not isinstance(segments, list):
            continue
        for idx, seg in enumerate(segments):
            if not isinstance(seg, dict):
                continue
            count = max(0.0, as_float(seg.get("count")))
            speed_sum = max(0.0, as_float(seg.get("speed_sum")))
            length_km = max(1.0e-9, as_float(seg.get("length_km")))
            lanes = max(1.0e-9, as_float(seg.get("lanes"), 2.0))
            mean_speed = speed_sum / count if count > 1.0e-9 else 0.0
            density = count / (length_km * lanes)
            flow = density * mean_speed * lanes
            out.append({
                "source_file": path.name,
                "sim_sec": sim_sec,
                "model_link": str(model_link),
                "segment_index": idx,
                "count": count,
                "length_km": length_km,
                "lanes": lanes,
                "mean_speed_kph": mean_speed,
                "density_veh_km_lane": density,
                "flow_proxy_veh_h": flow,
            })
    return out


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    moving_rows = [r for r in rows if r["count"] > 0 and r["mean_speed_kph"] > 0]
    low_density_speeds = [
        r["mean_speed_kph"]
        for r in moving_rows
        if r["density_veh_km_lane"] <= 10.0
    ]
    if not low_density_speeds:
        low_density_speeds = [r["mean_speed_kph"] for r in moving_rows]
    max_flow_row = max(moving_rows, key=lambda r: r["flow_proxy_veh_h"], default=None)
    by_link: dict[str, list[dict[str, Any]]] = {}
    for row in moving_rows:
        by_link.setdefault(row["model_link"], []).append(row)

    link_summary: dict[str, Any] = {}
    for link, link_rows in sorted(by_link.items()):
        link_max = max(link_rows, key=lambda r: r["flow_proxy_veh_h"])
        link_summary[link] = {
            "samples": len(link_rows),
            "free_speed_p85_kph": percentile(
                [
                    r["mean_speed_kph"]
                    for r in link_rows
                    if r["density_veh_km_lane"] <= 10.0
                ]
                or [r["mean_speed_kph"] for r in link_rows],
                0.85,
            ),
            "max_flow_proxy_veh_h": link_max["flow_proxy_veh_h"],
            "rho_at_max_flow_veh_km_lane": link_max["density_veh_km_lane"],
            "speed_at_max_flow_kph": link_max["mean_speed_kph"],
        }

    return {
        "sample_count": len(rows),
        "moving_sample_count": len(moving_rows),
        "source_state_file_count": len({r["source_file"] for r in rows}),
        "free_speed_p85_kph": percentile(low_density_speeds, 0.85),
        "free_speed_p50_kph": median(low_density_speeds) if low_density_speeds else 0.0,
        "max_flow_proxy_veh_h": max_flow_row["flow_proxy_veh_h"] if max_flow_row else 0.0,
        "rho_at_max_flow_veh_km_lane": max_flow_row["density_veh_km_lane"] if max_flow_row else 0.0,
        "speed_at_max_flow_kph": max_flow_row["mean_speed_kph"] if max_flow_row else 0.0,
        "by_link": link_summary,
        "warnings": [
            "These are instantaneous vehicle-count samples, not detector interval counts.",
            "Use demand-sweep calibration runs before updating MPC FD parameters.",
        ],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_file",
        "sim_sec",
        "model_link",
        "segment_index",
        "count",
        "length_km",
        "lanes",
        "mean_speed_kph",
        "density_veh_km_lane",
        "flow_proxy_veh_h",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir",
        default="evaluation/runs/stackelberg_vissim_smoke/decisions",
        help="Directory containing state_*.json files emitted by the Vissim controller runner.",
    )
    parser.add_argument(
        "--out-json",
        default="evaluation/calibration/fd_sample_summary.json",
    )
    parser.add_argument(
        "--out-csv",
        default="evaluation/calibration/fd_samples.csv",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    rows: list[dict[str, Any]] = []
    for path in iter_state_files(input_dir):
        rows.extend(sample_rows(path))

    summary = summarize(rows)
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(Path(args.out_csv), rows)
    print(json.dumps({
        "input_dir": str(input_dir),
        "state_files": summary["source_state_file_count"],
        "samples": summary["sample_count"],
        "out_json": str(out_json),
        "out_csv": args.out_csv,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
