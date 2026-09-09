"""Reproducible congestion chronology and actuator evidence from a VISSIM run.

Space-time panels use measured vehicle snapshots, not model predictions. Empty
cells are masked. Congestion events are operational thresholds, not causal proof.
The optional FZP lane analysis resolves the single-lane diverge bottleneck that
cell averages can hide. Files are written only under a new analysis directory.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / ".review-deps"))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MAPPING = ROOT / "evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json"


def unique_file(directory, pattern):
    paths = list(directory.glob(pattern))
    if len(paths) != 1:
        raise ValueError(f"Expected one {pattern} in {directory}, found {len(paths)}")
    return paths[0]


def execution_status(log_text, last_sim_sec, expected_end_sec):
    """Completion alone does not establish that the requested control ran."""
    errors = [line.strip() for line in log_text.splitlines()
              if line.lstrip().startswith("ERROR=")]
    failed_counters = {}
    for line in log_text.splitlines():
        match = re.fullmatch(r"([A-Z_]*(?:FAIL|MISMATCH)[A-Z_]*)=(\d+)", line.strip())
        if match and int(match[2]):
            failed_counters[match[1]] = int(match[2])
    reasons = []
    if "STAGE=SIM_DONE" not in log_text:
        reasons.append("simulation completion marker is missing")
    if abs(last_sim_sec - expected_end_sec) > 1e-6:
        reasons.append("state observations do not reach the requested end time")
    if errors:
        reasons.append("runner reported errors, including possible unapplied controls")
    if failed_counters:
        reasons.append("nonzero failure or mismatch counters")
    return {"completed_without_reported_errors": not reasons,
            "reasons": reasons, "runner_error_count": len(errors),
            "runner_errors": errors[:20], "failed_counters": failed_counters,
            "scope": "Necessary execution check; command readback and experimental comparability require separate review."}


def persistent_events(frame, speed_threshold=30.0, min_count=5, duration_sec=90.0):
    events = []
    for (direction, cell), group in frame.groupby(["model_link", "segment_index"]):
        group = group.sort_values("sim_sec")
        start = last = None
        lowest_speed = float("inf")
        peak_stopped = 0
        for row in group.itertuples():
            active = row.sim_sec >= 900 and row.mean_speed_kph < speed_threshold and row.count >= min_count
            if active and (last is None or row.sim_sec - last <= 31):
                start = row.sim_sec if start is None else start
                last = row.sim_sec
                lowest_speed = min(lowest_speed, row.mean_speed_kph)
                peak_stopped = max(peak_stopped, row.stopped_count)
            else:
                if start is not None and last - start >= duration_sec:
                    events.append(dict(model_link=direction, cell=int(cell), start_sec=float(start),
                        end_sec=float(last), min_speed_kph=float(lowest_speed), peak_stopped=int(peak_stopped)))
                start = row.sim_sec if active else None
                last = row.sim_sec if active else None
                lowest_speed = row.mean_speed_kph if active else float("inf")
                peak_stopped = row.stopped_count if active else 0
        if start is not None and last - start >= duration_sec:
            events.append(dict(model_link=direction, cell=int(cell), start_sec=float(start),
                end_sec=float(last), min_speed_kph=float(lowest_speed), peak_stopped=int(peak_stopped)))
    return sorted(events, key=lambda event: (event["start_sec"], event["model_link"], event["cell"]))


def cell_panels(frame, mapping, out):
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    for i, link in enumerate(("FW_E", "FW_W")):
        group = frame.loc[frame.model_link == link].copy()
        group.loc[group["count"] == 0, "mean_speed_kph"] = np.nan
        for j, (column, title, cmap, limits) in enumerate((
                ("mean_speed_kph", "Speed (km/h); empty cells masked", "RdYlGn", (0, 120)),
                ("density_veh_km_lane", "Density (veh/km/lane)", "magma_r", (0, 120)),
                ("stopped_count", "Stopped vehicles", "magma_r", (0, None)))):
            pivot = group.pivot(index="segment_index", columns="sim_sec", values=column).sort_index()
            ax = axes[i, j]
            extent = [float(pivot.columns.min()) / 60, float(pivot.columns.max()) / 60,
                      -.5, float(pivot.index.max()) + .5]
            image = ax.imshow(pivot.to_numpy(), origin="lower", aspect="auto", extent=extent,
                              cmap=cmap, vmin=limits[0], vmax=limits[1], interpolation="nearest")
            ax.set(title=f"{link}: {title}", xlabel="Simulation minute", ylabel="Cell (travel direction → increasing)")
            ax.axvline(15, color="black", lw=.6, ls="--")
            for ramp, spec in mapping["ramp_meter_groups"].items():
                if ramp.endswith(link[-1]):
                    for cell in spec["physical_segment_indices"]:
                        ax.axhline(cell, color="white", lw=.4, alpha=.5)
            fig.colorbar(image, ax=ax, shrink=.85)
    fig.savefig(out / "freeway_space_time.png", dpi=160)
    plt.close(fig)


def actuator_panels(actions, out):
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), constrained_layout=True)
    for group_id, group in actions.loc[actions.kind == "ramp_meter"].groupby("id"):
        group = group.drop_duplicates(["sim_sec", "rate_vph"]).sort_values("sim_sec")
        axes[0].step(group.sim_sec / 60, group.rate_vph, where="post", label=str(group_id))
    for group_id, group in actions.loc[actions.kind == "vsl"].groupby("id"):
        group = group.drop_duplicates(["sim_sec", "speed_kph"]).sort_values("sim_sec")
        if group.speed_kph.nunique() > 1 or str(group_id).endswith(("S0", "S5", "S10", "S15")):
            axes[1].step(group.sim_sec / 60, group.speed_kph, where="post", label=str(group_id))
    signals = actions.loc[actions.kind == "signal"]
    for signal in (1001, 1004, 1005):
        group = signals.loc[pd.to_numeric(signals.sc_no, errors="coerce") == signal].sort_values("sim_sec")
        for phase in ("p1_green", "p2_green", "p3_green", "p4_green"):
            if len(group):
                axes[2].step(group.sim_sec / 60, group[phase], where="post", label=f"SC{signal} {phase}")
    for ax, label in zip(axes, ("Requested meter rate (veh/h)", "Requested VSL (km/h)", "Requested green (s)")):
        ax.set(xlabel="Simulation minute", ylabel=label)
        ax.grid(alpha=.2)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(fontsize=7, ncol=4)
        else:
            ax.text(.5, .5, "No commands in this category", ha="center", transform=ax.transAxes)
    fig.suptitle("Requested commands; COM-controlled signal switching requires actual COM readback")
    fig.savefig(out / "control_commands.png", dpi=160)
    plt.close(fig)


def lane_observations(fzp, mapping, out):
    with fzp.open(encoding="utf-8", errors="replace") as stream:
        header_row = None
        for row, line in enumerate(stream):
            if line.startswith("$VEHICLE:"):
                names = line.strip().split(":", 1)[1].split(";")
                header_row = row
                break
    if header_row is None:
        raise ValueError("FZP has no $VEHICLE schema header")
    columns = ["SIMSEC", "NO", "LANE\\LINK\\NO", "LANE\\INDEX", "POS", "SPEED"]
    if not set(columns).issubset(names):
        raise ValueError(f"FZP lacks required columns: {set(columns) - set(names)}")
    chain_lookup = {}
    for model_link, spec in mapping["freeway_model_links"].items():
        for link, offset in zip(spec["chain_links"], spec["chain_offsets_m"]):
            chain_lookup[int(link)] = (model_link, offset)
    parts = []
    # Streaming reduces memory use on multi-million-row trajectories.
    for frame in pd.read_csv(fzp, sep=";", names=names, skiprows=header_row + 1,
                             usecols=columns, chunksize=300000, encoding="utf-8", encoding_errors="replace"):
        frame = frame.loc[frame["LANE\\LINK\\NO"].isin(chain_lookup)].copy()
        frame["model_link"] = frame["LANE\\LINK\\NO"].map(lambda link: chain_lookup[link][0])
        frame["chain_pos"] = frame.POS + frame["LANE\\LINK\\NO"].map(lambda link: chain_lookup[link][1])
        frame["time_bin_sec"] = (frame.SIMSEC // 30 * 30).astype(int)
        frame["space_bin_m"] = (frame.chain_pos.clip(lower=0) // 100 * 100).astype(int)
        frame["stopped"] = frame.SPEED < 5
        group = frame.groupby(["model_link", "LANE\\INDEX", "time_bin_sec", "space_bin_m"])
        parts.append(group.agg(samples=("NO", "size"), speed_sum=("SPEED", "sum"),
                               stopped_samples=("stopped", "sum")))
    if not parts:
        raise ValueError("No freeway observations in FZP")
    grouped = pd.concat(parts).groupby(level=[0, 1, 2, 3]).sum().reset_index()
    grouped["mean_speed_kph"] = grouped.speed_sum / grouped.samples
    grouped["stopped_fraction"] = grouped.stopped_samples / grouped.samples
    grouped.to_csv(out / "freeway_lane_space_time.csv", index=False)
    for link in ("FW_E", "FW_W"):
        fig, axes = plt.subplots(4, 1, figsize=(15, 12), constrained_layout=True, sharex=True)
        for lane, ax in enumerate(axes, 1):
            subset = grouped.loc[(grouped.model_link == link) & (grouped["LANE\\INDEX"] == lane)]
            pivot = subset.pivot(index="space_bin_m", columns="time_bin_sec", values="mean_speed_kph")
            pivot = pivot.reindex(index=np.arange(0, 10800, 100),
                                  columns=np.arange(0, grouped.time_bin_sec.max() + 30, 30))
            im = ax.imshow(pivot.to_numpy(), origin="lower", aspect="auto", interpolation="nearest",
                extent=[0, (float(pivot.columns.max()) + 30) / 60, 0, 10.8], vmin=0, vmax=120, cmap="RdYlGn")
            ax.set(ylabel=f"Lane {lane}\nChain km", title=f"{link} lane {lane}: 100 m / 30 s mean speed; missing cells masked")
            fig.colorbar(im, ax=ax, label="km/h", shrink=.85)
        axes[-1].set_xlabel("Simulation minute")
        fig.savefig(out / f"{link}_lane_speed.png", dpi=150)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--mapping", type=Path, default=MAPPING)
    parser.add_argument("--lanes", action="store_true")
    args = parser.parse_args()
    run = args.run.resolve()
    out = run / "analysis"
    out.mkdir(exist_ok=True)
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    segments = pd.read_csv(unique_file(run, "bottleneck_segments_*.csv"))
    actions = pd.read_csv(unique_file(run, "action_*.csv"))
    state = pd.read_csv(unique_file(run, "state_*.csv"))
    manifest = json.loads(unique_file(run, "run_provenance_*.json").read_text(encoding="utf-8"))
    log = unique_file(run, "runlog_*.txt").read_text(encoding="utf-8", errors="replace")
    events = persistent_events(segments)
    summary = {"run": run.name, "last_sim_sec": float(state.sim_sec.max()),
        "execution": execution_status(log, float(state.sim_sec.max()), float(manifest["sim_period_sec"])),
        "metric_scope": "Global TTT is a secondary legacy metric, not the requested control-area objective",
        "global_ttt_veh_h": float(np.trapezoid(state.total_vehicles, state.sim_sec) / 3600),
        "congestion_definition": "speed<30 km/h, >=5 vehicles, after900s, >=90s persistence; 30s samples",
        "persistent_congestion_events": events,
        "causal_limit": "Chronology alone cannot separate queue cause from consequence; pair with lane trajectories, discharge and paired runs"}
    (out / "congestion_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(events).to_csv(out / "congestion_events.csv", index=False)
    cell_panels(segments, mapping, out)
    actuator_panels(actions, out)
    if args.lanes:
        lane_observations(unique_file(run / "vissim_eval", "*.fzp"), mapping, out)
    print(json.dumps({"analysis": str(out), "global_ttt_veh_h": summary["global_ttt_veh_h"],
                      "persistent_events": len(events)}, indent=2))


if __name__ == "__main__":
    main()
