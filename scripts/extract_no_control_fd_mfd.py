"""Extract freeway FD and urban MFD points from the real-world no-control run."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean


def fnum(value: object, default: float = 0.0) -> float:
    try:
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


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def extract_fd(segment_csv: Path, start_sec: float, end_sec: float) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    points: list[dict[str, object]] = []
    for row in read_csv(segment_csv):
        sim_sec = fnum(row.get("sim_sec"))
        if sim_sec < start_sec or sim_sec > end_sec:
            continue
        density = fnum(row.get("density_veh_km_lane"))
        speed = fnum(row.get("mean_speed_kph"))
        lanes = fnum(row.get("lanes"), 1.0)
        flow = density * speed * lanes
        points.append({
            "sim_sec": sim_sec,
            "model_link": row.get("model_link", ""),
            "direction": row.get("direction", ""),
            "segment_index": int(fnum(row.get("segment_index"))),
            "segment_id": row.get("segment_id", ""),
            "physical_link": int(fnum(row.get("physical_link"))),
            "count": fnum(row.get("count")),
            "stopped_count": fnum(row.get("stopped_count")),
            "mean_speed_kph": speed,
            "length_km": fnum(row.get("length_km")),
            "lanes": lanes,
            "density_veh_km_lane": density,
            "flow_vph": flow,
        })

    bin_width = 2.0
    bins: dict[tuple[str, float], list[dict[str, object]]] = defaultdict(list)
    for row in points:
        density = float(row["density_veh_km_lane"])
        center = (int(density / bin_width) + 0.5) * bin_width
        bins[(str(row["model_link"]), center)].append(row)

    binned: list[dict[str, object]] = []
    for (model_link, center), rows in sorted(bins.items(), key=lambda item: (item[0][0], item[0][1])):
        flows = [float(r["flow_vph"]) for r in rows]
        speeds = [float(r["mean_speed_kph"]) for r in rows]
        counts = [float(r["count"]) for r in rows]
        binned.append({
            "model_link": model_link,
            "density_bin_center_veh_km_lane": center,
            "n": len(rows),
            "flow_mean_vph": mean(flows),
            "flow_p85_vph": percentile(flows, 0.85),
            "speed_mean_kph": mean(speeds),
            "count_mean_veh": mean(counts),
        })

    positive = [row for row in points if float(row["density_veh_km_lane"]) > 0.0]
    if not points:
        return points, binned, {"point_count": 0, "positive_point_count": 0, "links": {}}

    by_link: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in positive:
        by_link[str(row["model_link"])].append(row)
    link_summary = {}
    for link, rows in by_link.items():
        max_flow_row = max(rows, key=lambda r: float(r["flow_vph"]))
        link_bins = [row for row in binned if row["model_link"] == link]
        max_bin = max(link_bins, key=lambda r: float(r["flow_mean_vph"])) if link_bins else {}
        link_summary[link] = {
            "points": len(rows),
            "density_min": min(float(r["density_veh_km_lane"]) for r in rows),
            "density_max": max(float(r["density_veh_km_lane"]) for r in rows),
            "speed_mean": mean(float(r["mean_speed_kph"]) for r in rows),
            "observed_flow_max_vph": float(max_flow_row["flow_vph"]),
            "observed_flow_max_density": float(max_flow_row["density_veh_km_lane"]),
            "binned_capacity_mean_vph": float(max_bin.get("flow_mean_vph", 0.0)),
            "binned_critical_density": float(max_bin.get("density_bin_center_veh_km_lane", 0.0)),
        }

    summary = {
        "point_count": len(points),
        "positive_point_count": len(positive),
        "links": link_summary,
    }
    return points, binned, summary


def extract_mfd(link_csv: Path, state_csv: Path, start_sec: float, end_sec: float) -> tuple[list[dict[str, object]], dict[str, object]]:
    state_by_sec = {}
    for row in read_csv(state_csv):
        sim_sec = fnum(row.get("sim_sec"))
        if start_sec <= sim_sec <= end_sec:
            state_by_sec[sim_sec] = row

    buckets: dict[float, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in read_csv(link_csv):
        sim_sec = fnum(row.get("sim_sec"))
        if sim_sec < start_sec or sim_sec > end_sec:
            continue
        category = str(row.get("category", ""))
        count = fnum(row.get("count"))
        speed = fnum(row.get("mean_speed_kph"))
        production = count * speed
        if category in {"urban_or_other", "local_observable_connector", "freeway_input"}:
            buckets[sim_sec]["state_aligned_accumulation"] += count
            buckets[sim_sec]["state_aligned_production"] += production
        if category in {"urban_or_other", "local_observable_connector"}:
            buckets[sim_sec]["core_accumulation"] += count
            buckets[sim_sec]["core_production"] += production
        buckets[sim_sec][f"category_{category}_accumulation"] += count
        buckets[sim_sec][f"category_{category}_production"] += production

    points: list[dict[str, object]] = []
    for sim_sec in sorted(buckets):
        row = buckets[sim_sec]
        state = state_by_sec.get(sim_sec, {})
        state_acc = row["state_aligned_accumulation"]
        core_acc = row["core_accumulation"]
        points.append({
            "sim_sec": sim_sec,
            "urban_state_vehicles": fnum(state.get("urban_vehicles")),
            "urban_state_aligned_accumulation_veh": state_acc,
            "urban_state_aligned_production_veh_km_h": row["state_aligned_production"],
            "urban_state_aligned_mean_speed_kph": row["state_aligned_production"] / state_acc if state_acc > 0 else 0.0,
            "urban_core_accumulation_veh": core_acc,
            "urban_core_production_veh_km_h": row["core_production"],
            "urban_core_mean_speed_kph": row["core_production"] / core_acc if core_acc > 0 else 0.0,
            "total_vehicles": fnum(state.get("total_vehicles")),
            "stopped_vehicles": fnum(state.get("stopped_vehicles")),
        })

    if not points:
        return points, {
            "point_count": 0,
            "state_aligned_peak_production_veh_km_h": 0.0,
            "state_aligned_peak_accumulation_veh": 0.0,
            "state_aligned_peak_time_sec": 0.0,
            "core_peak_production_veh_km_h": 0.0,
            "core_peak_accumulation_veh": 0.0,
            "core_peak_time_sec": 0.0,
            "state_aligned_accumulation_min": 0.0,
            "state_aligned_accumulation_max": 0.0,
            "core_accumulation_min": 0.0,
            "core_accumulation_max": 0.0,
        }

    max_prod = max(points, key=lambda r: float(r["urban_state_aligned_production_veh_km_h"]))
    max_core_prod = max(points, key=lambda r: float(r["urban_core_production_veh_km_h"]))
    summary = {
        "point_count": len(points),
        "state_aligned_peak_production_veh_km_h": float(max_prod["urban_state_aligned_production_veh_km_h"]),
        "state_aligned_peak_accumulation_veh": float(max_prod["urban_state_aligned_accumulation_veh"]),
        "state_aligned_peak_time_sec": float(max_prod["sim_sec"]),
        "core_peak_production_veh_km_h": float(max_core_prod["urban_core_production_veh_km_h"]),
        "core_peak_accumulation_veh": float(max_core_prod["urban_core_accumulation_veh"]),
        "core_peak_time_sec": float(max_core_prod["sim_sec"]),
        "state_aligned_accumulation_min": min(float(r["urban_state_aligned_accumulation_veh"]) for r in points),
        "state_aligned_accumulation_max": max(float(r["urban_state_aligned_accumulation_veh"]) for r in points),
        "core_accumulation_min": min(float(r["urban_core_accumulation_veh"]) for r in points),
        "core_accumulation_max": max(float(r["urban_core_accumulation_veh"]) for r in points),
    }
    return points, summary


def plot_outputs(fd_points: list[dict[str, object]], mfd_points: list[dict[str, object]], out_prefix: Path) -> dict[str, str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    links = sorted({str(row["model_link"]) for row in fd_points})
    colors = {"FW_E": "#1f77b4", "FW_W": "#d62728"}

    fd_png = out_prefix.with_name(out_prefix.name + "_freeway_fd.png")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=140, constrained_layout=True)
    for link in links:
        rows = [row for row in fd_points if str(row["model_link"]) == link]
        density = [float(row["density_veh_km_lane"]) for row in rows]
        flow = [float(row["flow_vph"]) for row in rows]
        speed = [float(row["mean_speed_kph"]) for row in rows]
        axes[0].scatter(density, flow, s=14, alpha=0.55, label=link, color=colors.get(link))
        axes[1].scatter(density, speed, s=14, alpha=0.55, label=link, color=colors.get(link))
    axes[0].set_xlabel("Density (veh/km/lane)")
    axes[0].set_ylabel("Flow proxy (veh/h)")
    axes[0].set_title("Freeway Fundamental Diagram")
    axes[1].set_xlabel("Density (veh/km/lane)")
    axes[1].set_ylabel("Speed (km/h)")
    axes[1].set_title("Freeway Speed-Density")
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend()
    fig.savefig(fd_png)
    plt.close(fig)

    mfd_png = out_prefix.with_name(out_prefix.name + "_urban_mfd.png")
    times = [float(row["sim_sec"]) for row in mfd_points]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=140, constrained_layout=True)
    acc = [float(row["urban_state_aligned_accumulation_veh"]) for row in mfd_points]
    prod = [float(row["urban_state_aligned_production_veh_km_h"]) for row in mfd_points]
    core_acc = [float(row["urban_core_accumulation_veh"]) for row in mfd_points]
    core_prod = [float(row["urban_core_production_veh_km_h"]) for row in mfd_points]
    speed = [float(row["urban_state_aligned_mean_speed_kph"]) for row in mfd_points]
    axes[0].plot(acc, prod, color="#2ca02c", linewidth=1.2, alpha=0.7, label="state-aligned")
    sc = axes[0].scatter(acc, prod, c=times, cmap="viridis", s=30, alpha=0.8)
    axes[0].plot(core_acc, core_prod, color="#9467bd", linewidth=1.0, alpha=0.45, label="core")
    axes[0].set_xlabel("Urban accumulation (veh)")
    axes[0].set_ylabel("Production proxy (veh-km/h)")
    axes[0].set_title("Urban MFD")
    axes[0].legend()
    axes[1].plot(acc, speed, color="#2ca02c", linewidth=1.2)
    axes[1].scatter(acc, speed, c=times, cmap="viridis", s=30, alpha=0.8)
    axes[1].set_xlabel("Urban accumulation (veh)")
    axes[1].set_ylabel("Mean speed proxy (km/h)")
    axes[1].set_title("Urban Speed-Accumulation")
    for ax in axes:
        ax.grid(True, alpha=0.25)
    fig.colorbar(sc, ax=list(axes), label="sim_sec", fraction=0.04, pad=0.03)
    fig.savefig(mfd_png)
    plt.close(fig)

    return {"freeway_fd_png": str(fd_png), "urban_mfd_png": str(mfd_png)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("evaluation/runs/real_world_modi_lever_authority_warm900_eval3600_20260722"),
    )
    parser.add_argument("--run-name", default="no_control_scale135_warm900_eval3600_seed13")
    parser.add_argument("--start-sec", type=float, default=900.0)
    parser.add_argument("--end-sec", type=float, default=4500.0)
    parser.add_argument("--out-prefix", type=Path, default=Path("outputs/no_control_fd_mfd_20260724"))
    args = parser.parse_args()

    segment_csv = args.run_dir / f"bottleneck_segments_{args.run_name}.csv"
    link_csv = args.run_dir / f"bottleneck_links_{args.run_name}.csv"
    state_csv = args.run_dir / f"state_{args.run_name}.csv"

    fd_points, fd_bins, fd_summary = extract_fd(segment_csv, args.start_sec, args.end_sec)
    mfd_points, mfd_summary = extract_mfd(link_csv, state_csv, args.start_sec, args.end_sec)

    fd_csv = args.out_prefix.with_name(args.out_prefix.name + "_freeway_fd_points.csv")
    fd_bin_csv = args.out_prefix.with_name(args.out_prefix.name + "_freeway_fd_binned.csv")
    mfd_csv = args.out_prefix.with_name(args.out_prefix.name + "_urban_mfd_points.csv")
    summary_json = args.out_prefix.with_name(args.out_prefix.name + "_summary.json")
    summary_md = args.out_prefix.with_name(args.out_prefix.name + "_summary.md")

    fd_fields = list(fd_points[0].keys()) if fd_points else [
        "sim_sec", "model_link", "direction", "segment_index", "segment_id", "physical_link",
        "count", "stopped_count", "mean_speed_kph", "length_km", "lanes",
        "density_veh_km_lane", "flow_vph",
    ]
    fd_bin_fields = list(fd_bins[0].keys()) if fd_bins else [
        "model_link", "density_bin_center_veh_km_lane", "n", "flow_mean_vph",
        "flow_p85_vph", "speed_mean_kph", "count_mean_veh",
    ]
    mfd_fields = list(mfd_points[0].keys()) if mfd_points else [
        "sim_sec", "urban_state_vehicles", "urban_state_aligned_accumulation_veh",
        "urban_state_aligned_production_veh_km_h", "urban_state_aligned_mean_speed_kph",
        "urban_core_accumulation_veh", "urban_core_production_veh_km_h",
        "urban_core_mean_speed_kph", "total_vehicles", "stopped_vehicles",
    ]
    write_csv(fd_csv, fd_points, fd_fields)
    write_csv(fd_bin_csv, fd_bins, fd_bin_fields)
    write_csv(mfd_csv, mfd_points, mfd_fields)
    plot_paths = plot_outputs(fd_points, mfd_points, args.out_prefix) if fd_points and mfd_points else {}

    summary = {
        "run_dir": str(args.run_dir),
        "run_name": args.run_name,
        "window_sec": [args.start_sec, args.end_sec],
        "method": {
            "freeway_fd_flow_vph": "density_veh_km_lane * mean_speed_kph * lanes",
            "urban_state_aligned": "urban_or_other + local_observable_connector + freeway_input",
            "urban_core": "urban_or_other + local_observable_connector",
            "urban_production": "sum(link_count * link_mean_speed_kph), veh-km/h proxy",
        },
        "freeway_fd": fd_summary,
        "urban_mfd": mfd_summary,
        "outputs": {
            "freeway_fd_points_csv": str(fd_csv),
            "freeway_fd_binned_csv": str(fd_bin_csv),
            "urban_mfd_points_csv": str(mfd_csv),
            "summary_json": str(summary_json),
            **plot_paths,
        },
    }
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# No-Control Freeway FD / Urban MFD",
        "",
        f"- run: `{args.run_name}`",
        f"- window: `{args.start_sec:.0f}-{args.end_sec:.0f}s`",
        f"- freeway FD points: `{fd_summary['point_count']}`",
        f"- urban MFD points: `{mfd_summary['point_count']}`",
        "",
        "## Freeway FD",
    ]
    for link, item in fd_summary["links"].items():
        lines.append(
            f"- {link}: max observed flow `{item['observed_flow_max_vph']:.1f}` veh/h "
            f"at density `{item['observed_flow_max_density']:.2f}` veh/km/lane; "
            f"binned capacity `{item['binned_capacity_mean_vph']:.1f}` veh/h "
            f"near `{item['binned_critical_density']:.1f}` veh/km/lane"
        )
    lines.extend([
        "",
        "## Urban MFD",
        f"- state-aligned peak production: `{mfd_summary['state_aligned_peak_production_veh_km_h']:.1f}` veh-km/h "
        f"at accumulation `{mfd_summary['state_aligned_peak_accumulation_veh']:.1f}` veh "
        f"(t=`{mfd_summary['state_aligned_peak_time_sec']:.0f}s`)",
        f"- core peak production: `{mfd_summary['core_peak_production_veh_km_h']:.1f}` veh-km/h "
        f"at accumulation `{mfd_summary['core_peak_accumulation_veh']:.1f}` veh "
        f"(t=`{mfd_summary['core_peak_time_sec']:.0f}s`)",
        "",
        "## Files",
    ])
    for key, value in summary["outputs"].items():
        lines.append(f"- {key}: `{value}`")
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
