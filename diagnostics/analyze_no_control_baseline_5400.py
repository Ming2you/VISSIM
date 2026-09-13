"""Completed r01 baseline only: reuse cell and canonical area measurements."""
from __future__ import annotations
import copy
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics import measure_no_control_5400_three_arm_area as area
from diagnostics import plot_three_arm_cell_episodes as cells

OUT = ROOT / "diagnostics/no_control_5400_baseline_diagnosis_v1"


def cell_plot(result, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    import numpy as np
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#d8d8d8")
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True, constrained_layout=True)
    for direction, ax in zip(("E", "W"), axes):
        values = np.full((21, 180), np.nan)
        for row in result["samples"]:
            if row["direction"] == direction and not row["masked_count_lt5"]:
                values[row["cell_index"], row["sim_sec"] // 30 - 1] = row["mean_speed_kph"]
        mesh = ax.imshow(values, origin="lower", interpolation="nearest", aspect="auto", extent=[.25, 90.25, -.5, 20.5], cmap=cmap, vmin=0, vmax=120)
        for event in result["events"]:
            if event["direction"] == direction:
                x = [event["start_sec"] / 60, event["last_slow_sec"] / 60]
                ax.plot(x, [event["cell_index"]] * 2, color="black", lw=3)
                ax.plot(x, [event["cell_index"]] * 2, color="white", lw=1.2)
        ax.set(title=f"FW_{direction}: 0 upstream → 20 downstream in travel direction", ylabel="Cell index", xlim=(0, 90), yticks=list(range(0, 21, 2)), xticks=list(range(0, 91, 15)))
    axes[-1].set_xlabel("Simulation minute; 30-second sample-centered pixels")
    fig.colorbar(mesh, ax=axes, label="Sample mean speed (km/h)", shrink=.88, pad=.015)
    axes[0].legend(handles=[Patch(facecolor="#d8d8d8", label="Masked: fewer than 5 vehicles"), Line2D([], [], color="black", lw=3, label="Persistent sampled episode: count ≥ 5, speed < 30, span ≥ 90 s")], loc="upper left", fontsize=8)
    fig.suptitle("Native no-control baseline · seed 13 · complete 5400 s\nEvery regular frame shown; empty cells are not congestion", fontsize=14)
    fig.savefig(out / "baseline_EW_speed_5400.png", dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume-prepared-cells", action="store_true")
    parser.add_argument("--skip-plot", action="store_true")
    args = parser.parse_args()
    require, sha, save = area.require, area.sha, area.save
    if args.resume_prepared_cells:
        require(OUT.is_dir() and not (OUT / "area").exists() and (OUT / "attempt1_plot_dependency_failure.json").is_file(), "Resume only the preserved pre-measurement plot dependency failure")
    else:
        require(not OUT.exists(), "Preserve prior result; output must not exist")
    manifest = area.load(area.MANIFEST)
    rows = [r for r in manifest["arms"] if r["arm"] == "baseline"]
    require(len(rows) == 1, "Exactly one baseline receipt required")
    receipt = rows[0]
    require(receipt["valid"] is True and receipt["completed"] is True and receipt["exit_code"] == 0 and receipt["natural_exit"]["valid"] is True
            and receipt["validation"]["valid"] is True and receipt["trajectory"]["valid"] is True and manifest["source_changes"] == [], "Completed baseline gates failed")
    run = area.workspace_path(receipt["run"])
    provenance_path = area.single(run, "run_provenance_*.json")
    require(sha(provenance_path) == receipt["validation"]["provenance_sha256"], "Provenance differs from completed receipt")
    ledger = area.load(area.MEMBERSHIP)
    inside, outside, terminals = set(ledger["inside_links"]), set(ledger["outside_links"]), set(ledger["terminal_inside_links"])
    require(len(inside) == 635 and len(outside) == 601 and not inside & outside and terminals == {"24", "120"}, "Original physical partition differs")
    network = area.FLAT / "baseline.inpx"
    flat = area.load(area.FLAT / "manifest.json")
    network_sha = sha(network)
    require(network_sha == flat["outputs"]["baseline.inpx"]["destination_sha256"] == area.load(provenance_path)["files"]["network"]["sha256"], "Actual baseline physical network differs")
    require(area.physical_links(network, "baseline") == area.physical_links(area.workspace_path(ledger["network"]["path"]), "baseline"), "Original/baseline physical elements differ")
    require(set(area.physical_links(network, "baseline")) == inside | outside, "Membership does not cover all physical links")
    sources = [*area.SOURCES, Path(__file__), Path(cells.__file__), cells.EPISODE_SOURCE, area.MANIFEST, provenance_path, network,
               *[area.workspace_path(r["path"]) for r in [ledger["network"], *ledger["sources"]]]]
    pins = {area.relative(p): sha(p) for p in sources}
    for row in [ledger["network"], *ledger["sources"]]:
        require(sha(area.workspace_path(row["path"])) == row["sha256"], "Original membership source changed")
    if not args.resume_prepared_cells:
        OUT.mkdir()
    result = cells.completed_run(run, "baseline", 5400)
    pins.update(result["source_sha256"])
    if args.resume_prepared_cells:
        require(area.load(OUT / "cells.json") == {**result, "contract": cells.CONTRACT}, "Prepared cell evidence differs")
        failure = area.load(OUT / "attempt1_plot_dependency_failure.json")
        require(all(sha(OUT / p) == h for p, h in failure["preserved_cell_files"].items()), "Preserved cell files changed")
    else:
        area.write_rows(OUT / "cell_episodes.csv", result["events"], ["arm", "direction", "cell_index", "start_sec", "last_slow_sec", "duration_between_samples_sec", "sample_count", "minimum_speed_kph", "peak_stock_veh", "peak_stopped_veh", "termination_evidence", "first_nonqualifying_sample_sec"])
        area.write_rows(OUT / "cell_summary.csv", result["cell_summary"], list(result["cell_summary"][0]))
        area.write_rows(OUT / "cell_samples.csv", result["samples"], list(result["samples"][0]))
        save(OUT / "cells.json", {**result, "contract": cells.CONTRACT})
    if not args.skip_plot:
        cell_plot(result, OUT)
    print("42 cells complete. Starting the canonical FZP measurement once.", flush=True)
    directory = OUT / "area"
    directory.mkdir()
    bound = copy.deepcopy(ledger)
    bound["network"] = {"path": area.relative(network), "sha256": network_sha}
    bound["analysis_only_variant_binding"] = {"original_membership_sha256": sha(area.MEMBERSHIP), "inside_outside_terminal_lists_unchanged": True,
        "all_physical_link_elements_exact": True, "scope": "Native original-byte baseline in the flat asset directory"}
    membership_path = directory / "membership_analysis_only.json"
    save(membership_path, bound)
    command = [sys.executable, "-B", "-X", "utf8", str(area.SCRIPT), "--run", str(run), "--fzp-only", "--membership", str(membership_path), "--end-sec", "5400", "--out", str(directory)]
    fzp = area.single(run / "vissim_eval", "*.fzp")
    before = fzp.stat()
    save(directory / "command.json", {"argv": command, "cwd": str(ROOT), "source_sha256": pins, "FZP_parses": 1, "canonical_byte_hash_read_additional": True})
    started = time.perf_counter()
    with (directory / "stdout.txt").open("wb") as stdout, (directory / "stderr.txt").open("wb") as stderr:
        child = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
    require(child.returncode == 0, "Canonical area measurement failed")
    elapsed = time.perf_counter() - started
    after = fzp.stat()
    require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "FZP changed")
    metrics = area.load(directory / "area_metrics.json")
    require(metrics["provenance"]["fzp"]["sha256"] == receipt["trajectory"]["actual"]["file_sha256"], "FZP differs from completed native identity proof")
    with (directory / "area_timeseries.csv").open(encoding="utf-8", newline="") as stream:
        timeseries = list(csv.DictReader(stream))
    windows = area.interval_windows(timeseries, metrics)
    pairs = area.spatial_checks(metrics, inside, outside, terminals)
    area.write_rows(OUT / "area_windows.csv", windows, list(windows[0]))
    area.write_rows(directory / "observed_outside_exit_pairs.csv", pairs, ["source_link", "target_link", "events"])
    native = area.native_errors(run, directory, inside, outside, terminals, pins)
    changes = [p for p, h in pins.items() if sha(ROOT / p) != h]
    require(not changes, "Measurement source/evidence changed")
    save(OUT / "validation.json", {"status": "measured_pending_visual_and_interpretation_review", "source_sha256": pins, "source_changes": changes,
        "baseline_only": True, "batch_status_preserved": manifest["status"], "other_arms_not_analyzed": True,
        "canonical_measurement_exit_code": 0, "elapsed_sec_not_benchmark": elapsed, "FZP_sha_matches_recorded_full_payload_proof": True,
        "native_ordered_trajectory_exact_to_old_NC": receipt["trajectory"], "membership": {"inside": 635, "outside": 601, "terminals": sorted(terminals), "network_sha256": network_sha},
        "windows": windows, "native_error_summary": native, "figure_visual_review_complete": False,
        "source/model/COM_mutations": False})
    print(json.dumps({"status": "measured", "full_area": windows[0], "cell_episodes": len(result["events"]), "native": native}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
