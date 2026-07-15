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
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


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
    if ssx <= 1.0e-12:
        return {"slope": 0.0, "intercept": ybar, "r2": 0.0}
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / ssx
    intercept = ybar - slope * xbar
    sst = sum((y - ybar) ** 2 for y in ys)
    sse = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - sse / sst if sst > 1.0e-12 else 0.0
    return {"slope": slope, "intercept": intercept, "r2": r2}


def collect_observations(batch_dir: Path, signal_manifest: Path, warmup_sec: float) -> dict[str, list[dict[str, Any]]]:
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
            if duration <= 0.0 or cycle <= 0.0:
                continue
            phase = bucket["phase"]
            green = major_green if phase == "major" else minor_green
            q_vph = bucket["count"] / duration * 3600.0
            green_exposure = duration * green / cycle if green > 0.0 else 0.0
            direct_sat = bucket["count"] / green_exposure * 3600.0 if green_exposure > 0.0 else 0.0
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
                "green_exposure_sec": green_exposure,
                "sat_flow_direct_vph": direct_sat,
                "fit_y_q_times_cycle": q_vph * cycle,
            })
    return obs_by_approach


def classify_approach(obs: list[dict[str, Any]], min_count: float) -> dict[str, Any]:
    usable = [
        item for item in obs
        if f(item.get("discharge_count")) >= min_count
        and f(item.get("green_exposure_sec")) > 0.0
        and f(item.get("sat_flow_direct_vph")) > 0.0
    ]
    direct = [f(item.get("sat_flow_direct_vph")) for item in usable]
    xs = [f(item.get("green_sec")) for item in usable]
    ys = [f(item.get("fit_y_q_times_cycle")) for item in usable]
    fit = linear_fit(xs, ys) if len(usable) >= 2 else {"slope": 0.0, "intercept": 0.0, "r2": 0.0}
    sat_fit = fit["slope"]
    lost_fit = -fit["intercept"] / sat_fit if sat_fit > 0.0 else 0.0
    distinct_green = len({round(x, 6) for x in xs})
    p85 = percentile(direct, 0.85)
    p90 = percentile(direct, 0.90)
    med = median(direct) if direct else 0.0

    valid_regression = (
        len(usable) >= 6
        and distinct_green >= 3
        and 800.0 <= sat_fit <= 3600.0
        and 0.0 <= lost_fit <= 15.0
        and fit["r2"] >= 0.35
    )
    plausible_envelope = (
        len(usable) >= 4
        and 500.0 <= p85 <= 4200.0
        and p90 <= 5000.0
    )
    if valid_regression:
        status = "valid_regression"
        recommended = sat_fit
        lost = lost_fit
    elif plausible_envelope:
        status = "upper_envelope_only"
        recommended = p85
        lost = 6.0
    elif usable:
        status = "underfed_or_unstable"
        recommended = p85 if p85 > 0 else med
        lost = 6.0
    else:
        status = "insufficient_observations"
        recommended = 0.0
        lost = 6.0

    return {
        "node": obs[0].get("node", "") if obs else "",
        "link": int(f(obs[0].get("link"))) if obs else 0,
        "phase": obs[0].get("phase", "") if obs else "",
        "samples_total": len(obs),
        "samples_usable": len(usable),
        "distinct_green_sec": distinct_green,
        "status": status,
        "recommended_saturation_flow_vph_approach": round(float(recommended), 3),
        "recommended_lost_time_sec": round(float(lost), 3),
        "direct_sat_flow_median_vph_approach": round(float(med), 3),
        "direct_sat_flow_p85_vph_approach": round(float(p85), 3),
        "direct_sat_flow_p90_vph_approach": round(float(p90), 3),
        "fit_saturation_flow_vph_approach": round(float(sat_fit), 3),
        "fit_lost_time_sec": round(float(lost_fit), 3),
        "fit_r2": round(float(fit["r2"]), 6),
        "avg_flow_max_vph": round(max((f(item.get("avg_flow_vph")) for item in obs), default=0.0), 3),
        "observations": usable,
    }


def analyze(batch_dir: Path, signal_manifest: Path, warmup_sec: float, min_count: float) -> dict[str, Any]:
    obs_by_approach = collect_observations(batch_dir, signal_manifest, warmup_sec)
    by_approach = {
        label: classify_approach(obs, min_count=min_count)
        for label, obs in sorted(obs_by_approach.items())
    }
    valid = [v for v in by_approach.values() if v["status"] == "valid_regression"]
    envelope = [v for v in by_approach.values() if v["status"] in ("valid_regression", "upper_envelope_only")]
    recommended_values = [
        f(v.get("recommended_saturation_flow_vph_approach"))
        for v in envelope
        if f(v.get("recommended_saturation_flow_vph_approach")) > 0.0
    ]
    lost_values = [
        f(v.get("recommended_lost_time_sec"))
        for v in valid
        if 0.0 <= f(v.get("recommended_lost_time_sec")) <= 15.0
    ]
    promote_per_approach = len(valid) >= 8
    return {
        "schema_version": 1,
        "batch_dir": str(batch_dir),
        "signal_manifest": str(signal_manifest),
        "warmup_sec": warmup_sec,
        "min_discharge_count_per_case": min_count,
        "model": "upper-envelope direct green-exposure service curve plus optional q*cycle = s*(g-lost) regression",
        "summary": {
            "approach_count": len(by_approach),
            "valid_regression_count": len(valid),
            "upper_envelope_or_better_count": len(envelope),
            "median_recommended_saturation_flow_vph_approach": round(median(recommended_values), 3) if recommended_values else 0.0,
            "median_recommended_lost_time_sec": round(median(lost_values), 3) if lost_values else 6.0,
            "promote_per_approach_service_curve": promote_per_approach,
            "recommended_controller_policy": (
                "per_approach_candidate"
                if promote_per_approach
                else "keep_scalar_1800_veh_h_approach_and_6s_lost_time"
            ),
            "reason": (
                "Enough approaches have stable positive regression fits."
                if promote_per_approach
                else "Signal discharge logs do not identify enough saturated approaches; store per-approach values as diagnostics only."
            ),
        },
        "by_approach": by_approach,
    }


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    rows = sorted(result["by_approach"].items())
    lines = [
        "# Vissim signal service-curve fit",
        "",
        f"- Batch: `{result['batch_dir']}`",
        f"- Warmup: `{result['warmup_sec']}` sec",
        f"- Min discharge count per aggregated case: `{result['min_discharge_count_per_case']}`",
        f"- Policy: `{summary['recommended_controller_policy']}`",
        f"- Reason: {summary['reason']}",
        "",
        "| approach | status | usable / total | green levels | q_sat rec | lost rec | p85 direct | fit q_sat | fit lost | R² |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, item in rows:
        lines.append(
            f"| `{label}` | `{item['status']}` | {item['samples_usable']} / {item['samples_total']} | "
            f"{item['distinct_green_sec']} | {item['recommended_saturation_flow_vph_approach']:.1f} | "
            f"{item['recommended_lost_time_sec']:.1f} | {item['direct_sat_flow_p85_vph_approach']:.1f} | "
            f"{item['fit_saturation_flow_vph_approach']:.1f} | {item['fit_lost_time_sec']:.1f} | {item['fit_r2']:.3f} |"
        )
    lines += [
        "",
        "## Validation caveat",
        "",
        "This fit uses stopline discharge only. It does not directly observe an approach queue/presence state during the green, so under-fed approaches can still pass through the upper-envelope calculation. Per-approach values should not be promoted into controller service curves unless future saturated approach runs confirm queue persistence and monotone green-to-discharge behavior.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-dir", required=True)
    parser.add_argument("--signal-manifest", default="evaluation/signal_install/signal_manifest.csv")
    parser.add_argument("--warmup-sec", type=float, default=300.0)
    parser.add_argument("--min-discharge-count", type=float, default=10.0)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", default="")
    args = parser.parse_args()
    result = analyze(
        Path(args.batch_dir),
        Path(args.signal_manifest),
        warmup_sec=float(args.warmup_sec),
        min_count=float(args.min_discharge_count),
    )
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.out_md:
        write_markdown(Path(args.out_md), result)
    print(json.dumps({
        "status": "ok",
        "out_json": str(out_json),
        "out_md": args.out_md,
        "summary": result["summary"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
