from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


AMBER_SEC = 3.0
ALL_RED_SEC = 2.0


def f(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load_case(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_rows(batch_dir: Path) -> list[dict[str, str]]:
    rows = read_csv(batch_dir / "batch_manifest.csv")
    if rows:
        return rows
    out: list[dict[str, str]] = []
    for case_dir in sorted(p for p in batch_dir.iterdir() if p.is_dir()):
        out.append({
            "case_id": case_dir.name,
            "returncode": "0",
            "signal_csv": str(case_dir / "signal_discharge.csv"),
        })
    return out


def link_group_map(signal_manifest: Path) -> dict[int, dict[str, Any]]:
    mapping: dict[int, dict[str, Any]] = {}
    for row in read_csv(signal_manifest):
        if row.get("object_type") != "signalHead":
            continue
        category = row.get("category", "")
        if category not in ("intersection_major", "intersection_minor"):
            continue
        link_no = int(f(row.get("link")))
        if link_no <= 0:
            continue
        mapping[link_no] = {
            "phase": "major" if category == "intersection_major" else "minor",
            "sc_no": int(f(row.get("sc_no"))),
            "sg_no": int(f(row.get("sg_no"))),
        }
    return mapping


def linear_fit(xs: list[float], ys: list[float]) -> dict[str, float]:
    n = len(xs)
    if n < 2:
        return {"slope": 0.0, "intercept": 0.0, "r2": 0.0}
    xbar = sum(xs) / n
    ybar = sum(ys) / n
    ssx = sum((x - xbar) ** 2 for x in xs)
    if ssx <= 0:
        return {"slope": 0.0, "intercept": ybar, "r2": 0.0}
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / ssx
    intercept = ybar - slope * xbar
    sst = sum((y - ybar) ** 2 for y in ys)
    sse = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - sse / sst if sst > 0 else 0.0
    return {"slope": slope, "intercept": intercept, "r2": r2}


def analyze(batch_dir: Path, signal_manifest: Path, warmup_sec: float) -> dict[str, Any]:
    group_by_link = link_group_map(signal_manifest)
    obs_by_approach: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in manifest_rows(batch_dir):
        if str(item.get("returncode", "")) not in ("0", "0.0"):
            continue
        signal_csv = Path(item.get("signal_csv") or (Path(item["state_csv"]).parent / "signal_discharge.csv"))
        case_dir = signal_csv.parent
        case = load_case(case_dir)
        major_green = f(case.get("major_green_sec"), 56.0)
        minor_green = f(case.get("minor_green_sec"), 56.0)
        cycle = major_green + minor_green + 2.0 * (AMBER_SEC + ALL_RED_SEC)

        totals: dict[str, dict[str, Any]] = {}
        for row in read_csv(signal_csv):
            sim_sec = f(row.get("sim_sec"))
            if sim_sec < warmup_sec:
                continue
            link = int(f(row.get("link")))
            meta = group_by_link.get(link)
            if not meta:
                continue
            label = row.get("approach_label") or f"L{link}"
            bucket = totals.setdefault(label, {
                "count": 0.0,
                "duration_sec": 0.0,
                "phase": meta["phase"],
                "link": link,
                "node": row.get("node", ""),
            })
            bucket["count"] += f(row.get("discharge_count"))
            bucket["duration_sec"] += f(row.get("interval_sec"))

        for label, bucket in totals.items():
            duration = bucket["duration_sec"]
            if duration <= 0:
                continue
            phase = bucket["phase"]
            green = major_green if phase == "major" else minor_green
            q_vph = bucket["count"] / duration * 3600.0
            obs_by_approach[label].append({
                "case_id": item.get("case_id", case_dir.name),
                "node": bucket["node"],
                "link": bucket["link"],
                "phase": phase,
                "green_sec": green,
                "cycle_sec": cycle,
                "duration_sec": duration,
                "discharge_count": bucket["count"],
                "avg_flow_vph": q_vph,
                "green_exposure_sec": duration * green / cycle if cycle > 0 else 0.0,
                "sat_flow_direct_vph": bucket["count"] / (duration * green / cycle) * 3600.0 if duration > 0 and green > 0 and cycle > 0 else 0.0,
                "fit_y_q_times_cycle": q_vph * cycle,
            })

    by_approach: dict[str, Any] = {}
    sat_values: list[float] = []
    lost_values: list[float] = []
    for label, obs in sorted(obs_by_approach.items()):
        xs = [o["green_sec"] for o in obs]
        ys = [o["fit_y_q_times_cycle"] for o in obs]
        fit = linear_fit(xs, ys)
        sat = fit["slope"]
        lost = -fit["intercept"] / sat if sat > 0 else 0.0
        direct_values = [o["sat_flow_direct_vph"] for o in obs if o["sat_flow_direct_vph"] > 0]
        if sat > 0:
            sat_values.append(sat)
        if 0 <= lost <= 20:
            lost_values.append(lost)
        by_approach[label] = {
            "node": obs[0]["node"] if obs else "",
            "link": obs[0]["link"] if obs else "",
            "phase": obs[0]["phase"] if obs else "",
            "samples": len(obs),
            "fit_saturation_flow_vph_approach": sat,
            "fit_lost_time_sec": lost,
            "fit_r2": fit["r2"],
            "direct_sat_flow_median_vph_approach": median(direct_values) if direct_values else 0.0,
            "avg_flow_max_vph": max((o["avg_flow_vph"] for o in obs), default=0.0),
        }

    return {
        "batch_dir": str(batch_dir),
        "signal_manifest": str(signal_manifest),
        "warmup_sec": warmup_sec,
        "model": "q_vph * cycle_sec = saturation_flow_vph * (green_sec - lost_time_sec)",
        "network_cycle_overhead_sec": 2.0 * (AMBER_SEC + ALL_RED_SEC),
        "approach_count": len(by_approach),
        "summary": {
            "median_fit_saturation_flow_vph_approach": median(sat_values) if sat_values else 0.0,
            "median_fit_lost_time_sec": median(lost_values) if lost_values else 0.0,
            "note": "Approach values are total for the two-lane approach; divide by observed active lanes if a per-lane value is needed.",
        },
        "by_approach": by_approach,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-dir", required=True)
    parser.add_argument("--signal-manifest", default="evaluation/signal_install/signal_manifest.csv")
    parser.add_argument("--warmup-sec", type=float, default=300.0)
    parser.add_argument("--out-json", required=True)
    args = parser.parse_args()
    result = analyze(Path(args.batch_dir), Path(args.signal_manifest), args.warmup_sec)
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "out_json": str(out),
        "approach_count": result["approach_count"],
        "summary": result["summary"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
