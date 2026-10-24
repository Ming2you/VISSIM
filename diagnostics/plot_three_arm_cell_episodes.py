"""Completed no-control three-arm CSV congestion episodes and static heatmaps.

Reuses the existing pure episodes() definition. No FZP, model, scipy or COM.
--inspect-schema only reads three old timestamp groups, without plotting.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.audit_observed_nc_trajectory import episodes

EPISODE_SOURCE = ROOT / "diagnostics/audit_observed_nc_trajectory.py"
ARMS = ("baseline", "lcd10635_2000", "upstream1135")
SEGMENT_FIELDS = {"sim_sec", "model_link", "direction", "segment_index", "segment_id",
                  "count", "stopped_count", "mean_speed_kph", "length_km", "lanes"}
STATE_FIELDS = {"sim_sec", "freeway_vehicles", "controller_mode", "controller_status"}
CONTRACT = {"count_minimum_veh": 5, "speed_strictly_below_kph": 30,
            "sample_cadence_sec": 30, "minimum_elapsed_between_samples_sec": 90,
            "minimum_consecutive_samples": 4, "analysis_start_sec": 30,
            "startup_sec1": "retained for schema/stock checks, excluded from the 30-second episode/plot grid",
            "index_orientation": "Both E and W: index0 is upstream; increasing index follows travel toward downstream20.",
            "physical_link_column": "Representative model-link alias, not the physical location of every cell; use chain offsets/bounds.",
            "duration": "last_slow_sec minus start_sec; do not add an extra sample period",
            "interpretation": "Sampled persistence, not proof of uninterrupted slow traffic between observations.",
            "mask": "Every count<5 sample is masked, including zero-count zero-speed cells; no speed imputation.",
            "figure": "Two standard matplotlib figures, E/W separately; three arms vertically; common0..120km/h blue scale; gray insufficient-count cells."}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def one(run, pattern):
    paths = list(run.glob(pattern))
    if len(paths) != 1:
        raise ValueError(f"Expected exactly one {pattern}: {run}")
    return paths[0]


def finite(value, label, integer=False):
    number = float(value)
    if not math.isfinite(number) or number < 0 or (integer and not number.is_integer()):
        raise ValueError(f"Invalid {label}: {value!r}")
    return int(number) if integer else number


def parse_segments(rows):
    seen = set()
    grouped = defaultdict(list)
    for raw in rows:
        if not SEGMENT_FIELDS <= raw.keys():
            raise ValueError("Missing segment CSV columns")
        t = finite(raw["sim_sec"], "time", True)
        model, direction = raw["model_link"], raw["direction"]
        index = finite(raw["segment_index"], "cell", True)
        key = (t, model, index)
        if model not in ("FW_E", "FW_W") or direction != model[-1] or not 0 <= index <= 20:
            raise ValueError("Unknown physical model/cell address")
        if key in seen or raw["segment_id"] != f"RW_{model}_S{index}":
            raise ValueError("Duplicate or mismatched cell ID")
        seen.add(key)
        row = dict(raw)
        for name in ("count", "stopped_count", "lanes"):
            row[name] = finite(raw[name], name, True)
        for name in ("mean_speed_kph", "length_km"):
            row[name] = finite(raw[name], name)
        if row["stopped_count"] > row["count"] or not row["length_km"] or not row["lanes"]:
            raise ValueError("Invalid stopped count or cell geometry")
        row["sim_sec"], row["segment_index"] = t, index
        grouped[t].append(row)
    expected = {(model, index) for model in ("FW_E", "FW_W") for index in range(21)}
    for t, group in grouped.items():
        if {(r["model_link"], r["segment_index"]) for r in group} != expected:
            raise ValueError(f"Incomplete42-cell timestamp {t}")
    return grouped


def parse_state(rows):
    result = {}
    for row in rows:
        if not STATE_FIELDS <= row.keys():
            raise ValueError("Missing state CSV columns")
        t = finite(row["sim_sec"], "state time", True)
        if t in result:
            raise ValueError("Duplicate state timestamp")
        result[t] = {**row, "freeway_vehicles": finite(row["freeway_vehicles"], "freeway stock", True)}
    return result


def stock_check(groups, state):
    if set(groups) != set(state):
        raise ValueError("State and cell timestamp grids differ")
    for t, group in groups.items():
        if sum(row["count"] for row in group) != state[t]["freeway_vehicles"]:
            raise ValueError(f"Cell stocks do not sum to state freeway stock at {t}")


def read_prefix(path, count):
    with path.open("rb") as stream:
        raw = b"".join(stream.readline() for _ in range(count + 1))
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))), {
        "path": str(path.relative_to(ROOT)), "prefix_bytes": len(raw), "prefix_sha256": hashlib.sha256(raw).hexdigest(),
        "full_file_bytes_observed": path.stat().st_size, "scope": "header and first requested data rows only; not a full-file hash"}


def inspect_schema(run, out):
    segments, seg_proof = read_prefix(one(run, "bottleneck_segments_*.csv"), 126)
    state_rows, state_proof = read_prefix(one(run, "state_*.csv"), 3)
    groups, state = parse_segments(segments), parse_state(state_rows)
    stock_check(groups, state)
    if sorted(groups) != [1, 30, 60]:
        raise ValueError("Unexpected old NC startup/30-second prefix")
    save(out / "schema_validation.json", {"status": "prefix_schema_pass_only", "run": str(run.relative_to(ROOT)),
        "contract": CONTRACT, "prefix_sources": [seg_proof, state_proof], "observed_times_sec": sorted(groups),
        "cells_per_time": {t: len(v) for t, v in groups.items()}, "stock_sum_matches_state": True,
        "count_below5_mask_candidates": sum(row["count"] < 5 for group in groups.values() for row in group),
        "episode_function_sha256": digest(EPISODE_SOURCE), "producer_sha256": digest(Path(__file__)),
        "full_analysis_executed": False, "figures_rendered": False, "model_COM_or_FZP_access": False})


def geometry(run_manifest):
    item = run_manifest["files"]["generated_vbs_config"]
    path = Path(item["path"])
    if digest(path) != item["sha256"]:
        raise ValueError("Recorded cell configuration bytes changed")
    source = path.read_text(encoding="utf-8-sig")
    result = {}
    for direction in ("E", "W"):
        def quoted(name):
            matches = re.findall(rf'^RW_FW_{direction}_{name}\s*=\s*"([^"]+)"\s*$', source, re.M)
            if len(matches) != 1:
                raise ValueError("Missing cell geometry constant " + name)
            return matches[0].split(",")
        bounds = [float(x) for x in quoted("SEG_BOUNDS")]
        links = quoted("CHAIN_LINKS")
        offsets = [float(x) for x in quoted("CHAIN_OFFSETS_M")]
        if len(bounds) != 22 or bounds[0] != 0 or any(a >= b for a, b in zip(bounds, bounds[1:])) or len(links) != len(offsets):
            raise ValueError("Invalid21-cell chain geometry")
        result[direction] = {"bounds_m": bounds, "chain_links": links, "chain_offsets_m": offsets}
    return result, {"path": str(path), "sha256": item["sha256"]}


def completed_run(run, arm, end):
    paths = {"segments": one(run, "bottleneck_segments_*.csv"), "state": one(run, "state_*.csv"),
             "log": one(run, "runlog_*.txt"), "manifest": one(run, "run_provenance_*.json")}
    pins = {str(p.relative_to(ROOT)): digest(p) for p in paths.values()}
    manifest = load(paths["manifest"])
    if manifest.get("controller") != "no-control" or int(manifest.get("sim_period_sec", 0)) != end or manifest.get("seed") != 13:
        raise ValueError("Expected completed no-control5400 seed13 experiment")
    log = paths["log"].read_text(encoding="utf-8-sig", errors="replace")
    if "STAGE=SIM_DONE" not in log or any(line.lstrip().startswith("ERROR=") for line in log.splitlines()):
        raise ValueError("Run did not complete without reported runner error")
    with paths["segments"].open(encoding="utf-8-sig", newline="") as stream:
        groups = parse_segments(csv.DictReader(stream))
    with paths["state"].open(encoding="utf-8-sig", newline="") as stream:
        state = parse_state(csv.DictReader(stream))
    stock_check(groups, state)
    if set(groups) != {1, *range(30, end + 1, 30)}:
        raise ValueError("Expected startup1 plus complete30-second grid to5400; gaps cannot be imputed")
    if any("fallback" in row["controller_status"].lower() for row in state.values()):
        raise ValueError("Controller fallback in state CSV")
    geo, geo_source = geometry(manifest)
    by_cell = defaultdict(list)
    for t in sorted(groups):
        if t == 1:
            continue
        for row in groups[t]:
            by_cell[(row["direction"], row["segment_index"])].append(row)
    events, summaries, samples = [], [], []
    for (direction, index), series in sorted(by_cell.items()):
        found = episodes(series)
        lookup = {row["sim_sec"]: row for row in series}
        for event in found:
            first, last = int(event["start_sec"]), int(event["last_slow_sec"])
            selected = [row for row in series if first <= row["sim_sec"] <= last]
            after = lookup.get(last + 30)
            reason = "right_censored_at_end" if after is None else ("below_min_count" if after["count"] < 5 else "speed_not_below30")
            events.append({"arm": arm, "direction": direction, "cell_index": index, **event,
                           "sample_count": len(selected), "minimum_speed_kph": min(row["mean_speed_kph"] for row in selected),
                           "peak_stock_veh": max(row["count"] for row in selected),
                           "peak_stopped_veh": max(row["stopped_count"] for row in selected),
                           "termination_evidence": reason, "first_nonqualifying_sample_sec": after["sim_sec"] if after else None})
        summaries.append({"arm": arm, "direction": direction, "cell_index": index, "episodes": len(found),
                          "first_onset_sec": found[0]["start_sec"] if found else None,
                          "minimum_eligible_speed_kph": min((row["mean_speed_kph"] for row in series if row["count"] >= 5), default=None),
                          "masked_samples_count_lt5": sum(row["count"] < 5 for row in series),
                          "start_chain_m": geo[direction]["bounds_m"][index], "end_chain_m": geo[direction]["bounds_m"][index+1]})
        samples += [{"arm": arm, "direction": direction, "cell_index": index, "sim_sec": row["sim_sec"],
                     "count": row["count"], "stopped_count": row["stopped_count"], "mean_speed_kph": row["mean_speed_kph"],
                     "masked_count_lt5": row["count"] < 5} for row in series]
    if any(digest(ROOT / path) != expected for path, expected in pins.items()):
        raise ValueError("CSV/run metadata changed during analysis")
    return {"arm": arm, "run": str(run.relative_to(ROOT)), "source_sha256": pins, "geometry_source": geo_source,
            "geometry": geo, "rows": sum(map(len, groups.values())), "analysis_samples_per_cell": len(by_cell[("E", 0)]),
            "events": events, "cell_summary": summaries, "samples": samples}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plots(results, out, end):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    import numpy as np
    colors = LinearSegmentedColormap.from_list("sample_speed_blue", ["#17324d", "#4384ae", "#edf4f8"])
    colors.set_bad("#dddddd")
    for direction in ("E", "W"):
        fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True, sharey=True, constrained_layout=True)
        for ax, result in zip(axes, results):
            values = np.full((21, end // 30), np.nan)
            for row in result["samples"]:
                if row["direction"] == direction and not row["masked_count_lt5"]:
                    values[row["cell_index"], row["sim_sec"] // 30 - 1] = row["mean_speed_kph"]
            mesh = ax.imshow(values, origin="lower", interpolation="nearest", aspect="auto",
                             extent=[.25, end / 60 + .25, -.5, 20.5], cmap=colors, vmin=0, vmax=120)
            for event in result["events"]:
                if event["direction"] == direction:
                    ax.plot([event["start_sec"] / 60, event["last_slow_sec"] / 60],
                            [event["cell_index"]] * 2, color="#111111", lw=1.2)
            ax.set(title=result["arm"], ylabel=f"FW_{direction} cell index", xlim=(0, end / 60),
                   yticks=[0, 4, 8, 12, 16, 20], xticks=list(range(0, end // 60 + 1, 15)))
        axes[-1].set_xlabel("Simulation minute;30-second sample-centered pixels")
        fig.colorbar(mesh, ax=axes, label="Sample mean speed(km/h); gray=count<5", shrink=.85, pad=.015)
        fig.suptitle(f"FW_{direction}: native no-control cell speed\n"
                     "0 upstream →20 downstream; black segments: count≥5 and speed<30 for≥90s between samples", fontsize=12)
        fig.savefig(out / f"FW_{direction}_three_arm_speed.png", dpi=160)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--lcd", type=Path)
    parser.add_argument("--upstream", type=Path)
    parser.add_argument("--inspect-schema", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT / "diagnostics"):
        raise ValueError("Output must be a new diagnostics directory")
    out.mkdir()
    if args.inspect_schema:
        if any((args.baseline, args.lcd, args.upstream)):
            raise ValueError("Schema mode cannot also analyze arms")
        inspect_schema(args.inspect_schema.resolve(), out)
        print("prefix_schema_pass_only; no figures/full analysis")
        return 0
    if not all((args.baseline, args.lcd, args.upstream)):
        raise ValueError("All three completed arm directories are required")
    before = {str(p.relative_to(ROOT)): digest(p) for p in (Path(__file__), EPISODE_SOURCE)}
    results = [completed_run(run.resolve(), arm, 5400) for arm, run in zip(ARMS, (args.baseline, args.lcd, args.upstream))]
    if any(result["geometry"] != results[0]["geometry"] for result in results[1:]):
        raise ValueError("Arms use different cell geometry")
    events = [row for result in results for row in result["events"]]
    summaries = [row for result in results for row in result["cell_summary"]]
    samples = [row for result in results for row in result["samples"]]
    write_csv(out / "episodes.csv", events, ["arm", "direction", "cell_index", "start_sec", "last_slow_sec", "duration_between_samples_sec", "sample_count", "minimum_speed_kph", "peak_stock_veh", "peak_stopped_veh", "termination_evidence", "first_nonqualifying_sample_sec"])
    write_csv(out / "cell_summary.csv", summaries, list(summaries[0]))
    write_csv(out / "cell_samples.csv", samples, list(samples[0]))
    plots(results, out, 5400)
    if any(digest(ROOT / path) != expected for path, expected in before.items()):
        raise ValueError("Diagnostic source changed")
    save(out / "manifest.json", {"status": "complete_rendered_pending_visual_review", "contract": CONTRACT,
         "source_sha256": before, "arms": [{k: v for k, v in row.items() if k not in ("samples", "events", "cell_summary")} for row in results],
         "episode_count_by_arm": dict(Counter(row["arm"] for row in events)),
         "outputs": {p.name: digest(p) for p in out.iterdir() if p.is_file()}, "source_changes": [],
         "comparison_scope": "CSV observation evidence only; actual command/network comparability belongs to the parent run receipts."})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
