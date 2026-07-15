from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


def f(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


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
    return xs[lo] * (1.0 - (pos - lo)) + xs[hi] * (pos - lo)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def manifest_rows(batch_dir: Path) -> list[dict[str, str]]:
    manifest = batch_dir / "batch_manifest.csv"
    rows = read_csv(manifest)
    if rows:
        return rows

    discovered: list[dict[str, str]] = []
    for case_dir in sorted(p for p in batch_dir.iterdir() if p.is_dir()):
        state_csv = case_dir / "state.csv"
        segment_csv = case_dir / "segments.csv"
        ramp_csv = case_dir / "ramps.csv"
        if not state_csv.exists() and not segment_csv.exists() and not ramp_csv.exists():
            continue
        ok = state_csv.exists() and segment_csv.exists() and ramp_csv.exists()
        if ok:
            ok = len(read_csv(state_csv)) > 0 and len(read_csv(segment_csv)) > 0 and len(read_csv(ramp_csv)) > 0
        discovered.append({
            "case_id": case_dir.name,
            "returncode": "0" if ok else "999",
            "elapsed_sec": "",
            "state_csv": str(state_csv),
            "segment_csv": str(segment_csv),
            "ramp_csv": str(ramp_csv),
            "signal_csv": str(case_dir / "signal_discharge.csv"),
            "urban_csv": str(case_dir / "urban_production.csv"),
            "stdout": str(case_dir / "stdout.txt"),
            "stderr": str(case_dir / "stderr.txt"),
        })
    return discovered


def load_case(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def collect_segments(batch_dir: Path, warmup_sec: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in manifest_rows(batch_dir):
        if str(item.get("returncode", "")) not in ("0", "0.0"):
            continue
        segment_csv = Path(item["segment_csv"])
        case = load_case(segment_csv.parent)
        for row in read_csv(segment_csv):
            sim_sec = f(row.get("sim_sec"))
            if sim_sec < warmup_sec:
                continue
            out = dict(row)
            out["case_id"] = item.get("case_id", segment_csv.parent.name)
            out["freeway_volume_vph"] = f(case.get("freeway_volume_vph"))
            out["urban_volume_vph"] = f(case.get("urban_volume_vph"))
            out["rand_seed"] = int(f(case.get("rand_seed")))
            out["sim_sec"] = sim_sec
            out["count"] = f(row.get("count"))
            out["mean_speed_kph"] = f(row.get("mean_speed_kph"))
            out["density_veh_km_lane"] = f(row.get("density_veh_km_lane"))
            out["flow_proxy_veh_h"] = f(row.get("flow_proxy_veh_h"))
            rows.append(out)
    return rows


def collect_ramps(batch_dir: Path, warmup_sec: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in manifest_rows(batch_dir):
        if str(item.get("returncode", "")) not in ("0", "0.0"):
            continue
        ramp_csv = Path(item["ramp_csv"])
        case = load_case(ramp_csv.parent)
        for row in read_csv(ramp_csv):
            sim_sec = f(row.get("sim_sec"))
            if sim_sec < warmup_sec:
                continue
            out = dict(row)
            out["case_id"] = item.get("case_id", ramp_csv.parent.name)
            out["freeway_volume_vph"] = f(case.get("freeway_volume_vph"))
            out["urban_volume_vph"] = f(case.get("urban_volume_vph"))
            out["rand_seed"] = int(f(case.get("rand_seed")))
            out["sim_sec"] = sim_sec
            out["green_sec"] = f(row.get("green_sec"))
            out["interval_sec"] = f(row.get("interval_sec"))
            out["passage_count"] = f(row.get("passage_count"))
            out["release_rate_vph"] = f(row.get("release_rate_vph"))
            out["queue_count"] = f(row.get("queue_count"))
            out["presence_count"] = f(row.get("presence_count"))
            out["downstream_count"] = f(row.get("downstream_count"))
            out["mean_speed_kph"] = f(row.get("mean_speed_kph"))
            rows.append(out)
    return rows


def collect_signals(batch_dir: Path, warmup_sec: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in manifest_rows(batch_dir):
        if str(item.get("returncode", "")) not in ("0", "0.0"):
            continue
        signal_csv = Path(item.get("signal_csv") or (Path(item["state_csv"]).parent / "signal_discharge.csv"))
        case = load_case(signal_csv.parent)
        for row in read_csv(signal_csv):
            sim_sec = f(row.get("sim_sec"))
            if sim_sec < warmup_sec:
                continue
            out = dict(row)
            out["case_id"] = item.get("case_id", signal_csv.parent.name)
            out["urban_volume_vph"] = f(case.get("urban_volume_vph"))
            out["freeway_volume_vph"] = f(case.get("freeway_volume_vph"))
            out["rand_seed"] = int(f(case.get("rand_seed")))
            out["sim_sec"] = sim_sec
            out["interval_sec"] = f(row.get("interval_sec"))
            out["discharge_count"] = f(row.get("discharge_count"))
            out["discharge_rate_vph"] = f(row.get("discharge_rate_vph"))
            rows.append(out)
    return rows


def collect_urban(batch_dir: Path, warmup_sec: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in manifest_rows(batch_dir):
        if str(item.get("returncode", "")) not in ("0", "0.0"):
            continue
        urban_csv = Path(item.get("urban_csv") or (Path(item["state_csv"]).parent / "urban_production.csv"))
        case = load_case(urban_csv.parent)
        for row in read_csv(urban_csv):
            sim_sec = f(row.get("sim_sec"))
            if sim_sec < warmup_sec:
                continue
            out = dict(row)
            out["case_id"] = item.get("case_id", urban_csv.parent.name)
            out["urban_volume_vph"] = f(case.get("urban_volume_vph"))
            out["freeway_volume_vph"] = f(case.get("freeway_volume_vph"))
            out["rand_seed"] = int(f(case.get("rand_seed")))
            out["sim_sec"] = sim_sec
            out["interval_sec"] = f(row.get("interval_sec"))
            out["total_signal_discharge"] = f(row.get("total_signal_discharge"))
            out["total_signal_discharge_rate_vph"] = f(row.get("total_signal_discharge_rate_vph"))
            out["urban_vehicles"] = f(row.get("urban_vehicles"))
            out["mean_speed_kph"] = f(row.get("mean_speed_kph"))
            rows.append(out)
    return rows


def fd_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    moving = [
        r for r in rows
        if r["count"] > 0.0 and r["mean_speed_kph"] > 0.0
    ]
    low_density = [
        r["mean_speed_kph"] for r in moving
        if r["density_veh_km_lane"] <= 10.0
    ] or [r["mean_speed_kph"] for r in moving]
    max_flow_row = max(moving, key=lambda r: r["flow_proxy_veh_h"], default=None)

    by_demand: dict[str, dict[str, Any]] = {}
    demand_groups: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for row in moving:
        demand_groups[row["freeway_volume_vph"]].append(row)
    for demand, group in sorted(demand_groups.items()):
        best = max(group, key=lambda r: r["flow_proxy_veh_h"], default=None)
        by_demand[str(int(demand))] = {
            "samples": len(group),
            "median_density_veh_km_lane": median([r["density_veh_km_lane"] for r in group]),
            "median_speed_kph": median([r["mean_speed_kph"] for r in group]),
            "max_flow_proxy_veh_h": best["flow_proxy_veh_h"] if best else 0.0,
            "rho_at_max_flow_veh_km_lane": best["density_veh_km_lane"] if best else 0.0,
        }

    by_link: dict[str, dict[str, Any]] = {}
    link_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in moving:
        link_groups[str(row.get("model_link"))].append(row)
    for link, group in sorted(link_groups.items()):
        best = max(group, key=lambda r: r["flow_proxy_veh_h"], default=None)
        by_link[link] = {
            "samples": len(group),
            "free_speed_p85_kph": percentile(
                [r["mean_speed_kph"] for r in group if r["density_veh_km_lane"] <= 10.0]
                or [r["mean_speed_kph"] for r in group],
                0.85,
            ),
            "max_flow_proxy_veh_h": best["flow_proxy_veh_h"] if best else 0.0,
            "rho_at_max_flow_veh_km_lane": best["density_veh_km_lane"] if best else 0.0,
        }

    return {
        "sample_count": len(rows),
        "moving_sample_count": len(moving),
        "free_speed_p85_kph": percentile(low_density, 0.85),
        "free_speed_p50_kph": median(low_density) if low_density else 0.0,
        "max_flow_proxy_veh_h": max_flow_row["flow_proxy_veh_h"] if max_flow_row else 0.0,
        "rho_at_max_flow_veh_km_lane": max_flow_row["density_veh_km_lane"] if max_flow_row else 0.0,
        "speed_at_max_flow_kph": max_flow_row["mean_speed_kph"] if max_flow_row else 0.0,
        "suggested_initial_overrides": {
            "network.v_free": round(percentile(low_density, 0.85), 3) if low_density else None,
            "network.freeway_capacity_veh_h": round(max_flow_row["flow_proxy_veh_h"], 3) if max_flow_row else None,
            "network.rho_crit": round(max_flow_row["density_veh_km_lane"], 3) if max_flow_row else None,
            "network.rho_max": round(max((r["density_veh_km_lane"] for r in moving), default=0.0), 3),
        },
        "by_demand": by_demand,
        "by_link": by_link,
        "caveat": "flow_proxy_veh_h is density*speed*lanes from instantaneous vehicle states; use detector/passage flow for final FD calibration.",
    }


def ramp_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("site")), row["green_sec"])].append(row)

    by_site_green: dict[str, Any] = {}
    lookup: dict[str, dict[str, float]] = defaultdict(dict)
    for (site, green), group in sorted(groups.items()):
        total_pass = sum(r["passage_count"] for r in group)
        total_interval = sum(r["interval_sec"] for r in group)
        rate = total_pass / total_interval * 3600.0 if total_interval > 0 else 0.0
        queue_values = [r["queue_count"] for r in group]
        key = f"{site}_g{green:g}"
        by_site_green[key] = {
            "site": site,
            "green_sec": green,
            "samples": len(group),
            "total_passage_count": total_pass,
            "total_interval_sec": total_interval,
            "release_rate_vph": rate,
            "median_logged_release_rate_vph": median([r["release_rate_vph"] for r in group]) if group else 0.0,
            "median_queue_count": median(queue_values) if queue_values else 0.0,
            "max_queue_count": max(queue_values) if queue_values else 0.0,
        }
        lookup[site][str(green)] = rate

    return {
        "sample_count": len(rows),
        "by_site_green": by_site_green,
        "suggested_green_to_rate_vph": lookup,
        "caveat": "Short or underfed ramp runs can underestimate capacity; final fit needs sustained queue at the meter.",
    }


def signal_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row.get("node")), str(row.get("approach_label")))].append(row)
    by_approach: dict[str, Any] = {}
    for (node, label), group in sorted(groups.items()):
        total_pass = sum(r["discharge_count"] for r in group)
        total_interval = sum(r["interval_sec"] for r in group)
        by_approach[label] = {
            "node": node,
            "samples": len(group),
            "total_discharge_count": total_pass,
            "total_interval_sec": total_interval,
            "mean_discharge_rate_vph": total_pass / total_interval * 3600.0 if total_interval > 0 else 0.0,
            "max_logged_discharge_rate_vph": max((r["discharge_rate_vph"] for r in group), default=0.0),
        }
    return {
        "sample_count": len(rows),
        "by_approach": by_approach,
        "candidate_movement_capacity_veh_h": max(
            (v["max_logged_discharge_rate_vph"] for v in by_approach.values()),
            default=0.0,
        ),
        "caveat": "Use high-demand saturated approaches before treating this as signal saturation flow.",
    }


def urban_mfd_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_demand: dict[str, Any] = {}
    groups: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["urban_volume_vph"]].append(row)
    best_row = None
    for demand, group in sorted(groups.items()):
        production_values = [r["total_signal_discharge_rate_vph"] for r in group]
        accum_values = [r["urban_vehicles"] for r in group]
        local_best = max(group, key=lambda r: r["total_signal_discharge_rate_vph"], default=None)
        if best_row is None or (local_best and local_best["total_signal_discharge_rate_vph"] > best_row["total_signal_discharge_rate_vph"]):
            best_row = local_best
        by_demand[str(int(demand))] = {
            "samples": len(group),
            "median_urban_accumulation_veh": median(accum_values) if accum_values else 0.0,
            "max_urban_accumulation_veh": max(accum_values) if accum_values else 0.0,
            "median_signal_production_vph": median(production_values) if production_values else 0.0,
            "max_signal_production_vph": max(production_values) if production_values else 0.0,
        }
    return {
        "sample_count": len(rows),
        "by_urban_demand": by_demand,
        "candidate_N_P_crit_veh": best_row["urban_vehicles"] if best_row else 0.0,
        "max_signal_production_vph": best_row["total_signal_discharge_rate_vph"] if best_row else 0.0,
        "caveat": "This uses signal stopline discharge as a production proxy; final MFD should use validated protected-region production counts.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-dir", default="evaluation/runs/calibration_batch_smoke")
    parser.add_argument("--warmup-sec", type=float, default=60.0)
    parser.add_argument("--out-json", default="evaluation/calibration/vissim_calibration_fit_smoke.json")
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir)
    segments = collect_segments(batch_dir, args.warmup_sec)
    ramps = collect_ramps(batch_dir, args.warmup_sec)
    signals = collect_signals(batch_dir, args.warmup_sec)
    urban_rows = collect_urban(batch_dir, args.warmup_sec)
    fd_segments = [row for row in segments if str(row.get("case_id", "")).startswith("fd_")]
    if not fd_segments:
        fd_segments = segments
    ramp_rows = [row for row in ramps if str(row.get("case_id", "")).startswith("ramp_")]
    if not ramp_rows:
        ramp_rows = ramps

    summary = {
        "batch_dir": str(batch_dir),
        "warmup_sec": args.warmup_sec,
        "fd": fd_summary(fd_segments),
        "ramp_metering": ramp_summary(ramp_rows),
        "signal_saturation": signal_summary(signals),
        "urban_mfd": urban_mfd_summary(urban_rows),
        "mpc_weight_tuning": {
            "status": "pending",
            "next": "Tune after FD, ramp, signal, and MFD physical calibration pass acceptance checks.",
        },
    }
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "out_json": str(out),
        "segment_rows": len(segments),
        "fd_segment_rows": len(fd_segments),
        "ramp_rows": len(ramps),
        "ramp_fit_rows": len(ramp_rows),
        "signal_rows": len(signals),
        "urban_rows": len(urban_rows),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
