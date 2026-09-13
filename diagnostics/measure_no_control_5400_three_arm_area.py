"""Measure three completed NC5400 arms with the unchanged canonical area CLI.

One canonical FZP parse per arm, followed by small cumulative-CSV window checks.
The canonical CLI also hashes the FZP bytes. No model, COM, simulator or Git calls.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.measure_startup_gui_three_arm_area import ARMS, EVENTS, FLAT, MEMBERSHIP, SCRIPT, load, physical_links, save, sha
from diagnostics.capture_native_runtime_errors import parse_bytes

MANIFEST = ROOT / "diagnostics/no_control_network_arms/r01/manifest.json"
WINDOWS = ((0, 5400), *[(t, t + 900) for t in range(0, 5400, 900)], (750, 900), (900, 1050))
SOURCES = [Path(__file__), ROOT / "diagnostics/measure_startup_gui_three_arm_area.py",
           ROOT / "diagnostics/capture_native_runtime_errors.py", ROOT / "diagnostics/probe_e8_lane_receiving.py",
           SCRIPT, ROOT / "evaluation/controllers/control_area_objective.py", MEMBERSHIP, FLAT / "manifest.json"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def workspace_path(path):
    result = (ROOT / path).resolve()
    require(result.is_relative_to(ROOT), "Input path outside this worktree")
    return result


def single(run, pattern):
    rows = list(run.glob(pattern))
    require(len(rows) == 1, f"Expected one {pattern}: {run}")
    return rows[0]


def write_rows(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def interval_windows(rows, metrics):
    times = [float(r["sim_sec"]) for r in rows]
    require(times == list(range(1, 5401)), "Require exact completed FZP1s grid1..5400")
    require(all(r["source"] == "fzp" for r in rows), "No COM or censored-hold substitution")
    require(all(int(r["stock_closure_residual_veh"]) == 0 for r in rows), "Nonzero subinterval stock closure")
    by_time = dict(zip(times, rows))
    result = []
    for start, end in WINDOWS:
        begin = by_time[start] if start else {"inside_vehicles": "0", "ttt_veh_h_cumulative": "0", "ttd_observed_plus_terminal_cumulative": "0"}
        finish = by_time[end]
        selected = rows[start:end]
        counts = {key: sum(int(r[key]) for r in selected) for key in EVENTS}
        n0, n1 = int(begin["inside_vehicles"]), int(finish["inside_vehicles"])
        ttt = float(finish["ttt_veh_h_cumulative"]) - float(begin["ttt_veh_h_cumulative"])
        td = float(finish["ttd_observed_plus_terminal_cumulative"]) - float(begin["ttd_observed_plus_terminal_cumulative"])
        left = right = 0.0
        previous = n0
        for row in selected:
            require(float(row["interval_sec"]) == 1, "Interval/cadence mismatch")
            n = int(row["inside_vehicles"])
            left += previous / 3600
            right += n / 3600
            previous = n
        require(math.isclose(ttt, (left + right) / 2, rel_tol=1e-11, abs_tol=1e-8), "Cumulative TTT differs from independent trapezoid")
        require(td == counts["observed_exit_events"] + counts["terminal_exit_inferred_events"], "Cumulative TD differs from row events")
        closure = n1 - n0 - counts["observed_entry_events"] - counts["appeared_inside_events"] + td + counts["unresolved_inside_disappearances"]
        require(closure == 0, "Window stock ledger does not close")
        result.append({"start_sec": start, "end_sec": end, "duration_sec": end - start,
                       "event_assignment": "start < observed upper timestamp <= end", "ttt_veh_h": ttt,
                       "ttt_left_veh_h": left, "ttt_right_veh_h": right, "ttd_events": int(td), **counts,
                       "initial_inside_vehicles": n0, "final_inside_vehicles": n1, "stock_closure_residual_veh": 0})
    full = result[0]
    require(math.isclose(full["ttt_veh_h"], metrics["ttt_veh_h"], abs_tol=1e-8), "Whole-run TTT differs from canonical CLI")
    require(full["ttd_events"] == metrics["ttd_observed_plus_terminal_events"], "Whole-run TD differs from canonical CLI")
    for key in ("ttt_veh_h", "ttd_events", *EVENTS):
        require(math.isclose(sum(r[key] for r in result[1:7]), full[key], abs_tol=1e-8), "Six demand windows do not sum: " + key)
    return result


def spatial_checks(metrics, inside, outside, terminals):
    pairs = []
    for pair, count in metrics["exit_events_by_observed_link_pair"].items():
        source, target = pair.split("->")
        require(source in inside and target in outside and count > 0, "Invalid observed outside-boundary event")
        pairs.append({"source_link": source, "target_link": target, "events": count})
    require(sum(r["events"] for r in pairs) == metrics["ttd_observed_exit_events"], "Observed boundary-pair sum mismatch")
    require(set(metrics["terminal_inferred_by_link"]) <= terminals, "Unknown inferred terminal")
    require(sum(metrics["terminal_inferred_by_link"].values()) == metrics["ttd_terminal_exit_inferred_events"], "Terminal sum mismatch")
    require(set(metrics["unresolved_inside_disappearances_by_link"]) <= inside, "Unknown disappearance outside membership")
    require(sum(metrics["unresolved_inside_disappearances_by_link"].values()) == metrics["unresolved_inside_disappearances"], "Unknown-disappearance sum mismatch")
    residence = 0.0
    for link, row in metrics["physical_link_residence"].items():
        require(link in inside | outside and row["inside"] == (link in inside), "Residence membership mismatch")
        require(math.isfinite(row["ttt_veh_h"]) and 0 <= row["slow_veh_h"] <= row["ttt_veh_h"] + 1e-9, "Invalid physical residence")
        if row["inside"]:
            residence += row["ttt_veh_h"]
    require(math.isclose(residence, metrics["ttt_veh_h"], rel_tol=1e-10, abs_tol=1e-8), "Physical residence does not sum to area TTT")
    return pairs


def native_errors(run, directory, inside, outside, terminals, pins):
    """Preserved run-local warnings only; never read overwritten live network ERR."""
    # These are the canonical watchdog's two preserved native files. WSH stderr
    # also ends in .err but is not a VISSIM warning log.
    paths = [run / name for name in ("vissim_network.err", "vissim_simulation_001.err") if (run / name).is_file()]
    files, removals = [], []
    for index, path in enumerate(paths):
        raw = path.read_bytes()
        digest = sha(path)
        require(digest == hashlib.sha256(raw).hexdigest(), "Native ERR changed during read")
        pins[relative(path)] = digest
        captured = directory / f"native_err_{index:02d}.raw"
        captured.write_bytes(raw)
        parsed = parse_bytes(raw)
        files.append({"source": relative(path), "sha256": digest, "bytes": len(raw),
                      "raw_capture": relative(captured), **parsed})
        for row in parsed["events"]:
            if row["kind"] != "lane_change_removal":
                continue
            require(row["link"] in inside | outside and 0 <= row["time_sec"] <= 5400, "Removal outside physical/time contract")
            removals.append({**row, "source": relative(path), "source_sha256": digest,
                             "inside": row["link"] in inside, "terminal": row["link"] in terminals})
    identities = [(r["time_sec"], r["vehicle_id"], r["link"], r["position_m"]) for r in removals]
    duplicates = len(identities) - len(set(identities))
    complete = len(paths) == 2 and not duplicates and all(not f["partial_tail_bytes"] and not f["unparsed_removal_lines"] for f in files)
    # Duplicate raw lines remain visible; do not inflate an aggregate or silently deduplicate them.
    counts = dict(Counter("inside_terminal" if r["terminal"] else "inside_nonterminal" if r["inside"] else "outside" for r in removals)) if complete else None
    report = {"status": "parsed_preserved_run_local_warnings" if complete else "incomplete_or_ambiguous_warning_evidence",
              "files": files, "removals": removals, "duplicate_event_records": duplicates,
              "counts_by_membership": counts, "removals_by_link": dict(Counter(r["link"] for r in removals)) if complete else None,
              "native_warning_windows": [{"start_sec": start, "end_sec": end,
                  "inside_removals": sum(r["inside"] for r in removals if start < r["time_sec"] <= end),
                  "outside_removals": sum(not r["inside"] for r in removals if start < r["time_sec"] <= end),
                  "terminal_removals": sum(r["terminal"] for r in removals if start < r["time_sec"] <= end)}
                  for start, end in WINDOWS] if complete else None,
              "warning_counts": dict(sum((Counter(f["counts"]) for f in files), Counter())),
              "expected_native_files_present": len(paths) == 2,
              "terminal_inference_removal_overlap_requires_review": any(r["terminal"] for r in removals),
              "native_warning_id_time_matched_to_FZP": False,
              "time_assignment": "native warning timestamp; distinct from observed disappearance upper timestamp",
              "scope": "Run-local saved ERR, linked by completed run receipt; native ERR itself has no run_id. No ID blacklist or TD subtraction. Prior genuine outside exits remain valid. Counts are not asserted equal to FZP unknown losses without ID/time matching."}
    save(directory / "native_error_evidence.json", report)
    return {k: v for k, v in report.items() if k not in ("files", "removals")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to(ROOT / "diagnostics") and not out.exists(), "Output must be a new diagnostics directory")
    assembly_path = workspace_path(args.manifest)
    assembly = load(assembly_path)
    require(assembly.get("schema") == "no-control-network-arms5400/v1" and assembly.get("status") == "all_three_passed"
            and assembly.get("completed") is True and assembly.get("valid") is True and assembly.get("source_changes") == [], "All three completed validated NC runs required before analysis")
    require(len(assembly["arms"]) == 3, "Duplicate or extra arms")
    arms = {row["arm"]: row for row in assembly["arms"]}
    require(set(arms) == set(ARMS), "Unexpected arm addresses")
    ledger, flat = load(MEMBERSHIP), load(FLAT / "manifest.json")
    inside, outside, terminals = set(ledger["inside_links"]), set(ledger["outside_links"]), set(ledger["terminal_inside_links"])
    require(len(inside) == len(ledger["inside_links"]) == 635 and len(outside) == len(ledger["outside_links"]) == 601
            and not inside & outside and terminals == {"24", "120"}, "Frozen physical635/601/terminal partition differs")
    baseline_links = physical_links(FLAT / "baseline.inpx", "baseline")
    require(set(baseline_links) == inside | outside, "Membership does not cover physical network")
    sources = [*SOURCES, assembly_path, *[workspace_path(item["path"]) for item in [ledger["network"], *ledger["sources"]]]]
    pins = {relative(path): sha(path) for path in sources}
    for item in [ledger["network"], *ledger["sources"]]:
        require(pins[relative(workspace_path(item["path"]))] == item["sha256"], "Frozen membership source changed")
    contexts = {}
    for arm in ARMS:
        row = arms[arm]
        require(row.get("valid") is True and row.get("completed") is True and row.get("status") == "passed" and row.get("exit_code") == 0
                and row["natural_exit"]["valid"] is True and row["validation"]["valid"] is True, "Arm completion/process/readback gate failed")
        run = workspace_path(row["run"])
        require(run.name == row["name"] and run.parent == ROOT / "evaluation/runs", "Unexpected actual run directory")
        provenance_path = single(run, "run_provenance_*.json")
        provenance = load(provenance_path)
        require(sha(provenance_path) == row["validation"]["provenance_sha256"], "Driver/run provenance mismatch")
        require(provenance.get("controller") == "no-control" and provenance.get("seed") == 13 and provenance.get("sim_period_sec") == 5400
                and provenance.get("name") == run.name and provenance.get("run_id"), "Run identity/NC5400/seed differs")
        network = FLAT / (arm + ".inpx")
        expected = flat["outputs"][network.name]["destination_sha256"]
        require(sha(network) == expected == provenance["files"]["network"]["sha256"], "Actual variant/network SHA differs")
        require(physical_links(network, arm) == baseline_links, "Physical network differs beyond allowed10635 distance")
        log_path = single(run, "runlog_*.txt")
        log = log_path.read_bytes()
        require(b"STAGE=SIM_DONE" in log and b"ERROR=" not in log and b"RUN_MODE=CONTINUOUS_STATIC controller=no-control" in log, "Native completion/mode log gate failed")
        for path in (network, provenance_path, log_path):
            pins[relative(path)] = sha(path)
        contexts[arm] = (run, network, expected, provenance)
    out.mkdir()
    report = {"schema": "no-control-three-arm-area5400/v1", "status": "running", "source_sha256": pins,
              "driver_receipt": relative(assembly_path), "driver_runtime_source_pins_historical": assembly["source_sha256"],
              "scope": "Native observations, not a model or timing benchmark; temporary clock source is not an area-measurement dependency",
              "membership": {"inside_links": 635, "outside_links": 601, "terminal_inside_links": sorted(terminals),
                             "definition": ledger["definition"], "ramp_checks": ledger["ramp_checks"], "verified_all_inside_paths": ledger["verified_all_inside_paths"]}, "arms": []}
    save(out / "comparison.json", report)
    for arm in ARMS:
        run, network, expected, provenance = contexts[arm]
        directory = out / arm
        directory.mkdir()
        bound = copy.deepcopy(ledger)
        bound["network"] = {"path": relative(network), "sha256": expected}
        bound["analysis_only_variant_binding"] = {"original_membership_sha256": pins[relative(MEMBERSHIP)],
            "only_network_binding_changed": True, "inside_outside_terminal_lists_unchanged": True,
            "all_physical_link_elements_exact_after_normalizing_only_10635_lnChgDist": True}
        membership_path = directory / "membership_analysis_only.json"
        save(membership_path, bound)
        fzp = single(run / "vissim_eval", "*.fzp")
        stat = fzp.stat()
        command = [sys.executable, "-B", "-X", "utf8", str(SCRIPT), "--run", str(run), "--fzp-only", "--membership", str(membership_path), "--end-sec", "5400", "--out", str(directory)]
        save(directory / "command.json", {"argv": command, "cwd": str(ROOT), "measurement_script_sha256": pins[relative(SCRIPT)], "fzp_parses": 1, "canonical_additional_FZP_byte_hash_read": True})
        started = time.perf_counter()
        with (directory / "stdout.txt").open("wb") as stdout, (directory / "stderr.txt").open("wb") as stderr:
            child = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        require(child.returncode == 0, "Canonical area CLI failed for " + arm)
        elapsed = time.perf_counter() - started
        after = fzp.stat()
        require((stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "FZP changed during measurement")
        metrics = load(directory / "area_metrics.json")
        with (directory / "area_timeseries.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        require(metrics["sampling"]["fzp_snapshots"] == 5400 and metrics["sampling"]["maximum_step_sec"] == 1
                and metrics["sampling"]["missing_snapshot_gaps"] == 0 and metrics["boundaries"]["unobserved_tail_sec"] == 0
                and metrics["boundaries"]["final_state_used"] is False, "Incomplete/phase-mixed native1s observations")
        pairs = spatial_checks(metrics, inside, outside, terminals)
        write_rows(directory / "observed_outside_exit_pairs.csv", pairs, ["source_link", "target_link", "events"])
        native = native_errors(run, directory, inside, outside, terminals, pins)
        report["arms"].append({"arm": arm, "run": relative(run), "run_id": provenance["run_id"], "network_sha256": expected,
            "measurement_exit_code": 0, "measurement_elapsed_sec_not_benchmark": elapsed, "fzp_stat_unchanged": True,
            "original_metrics_path": relative(directory / "area_metrics.json"), "provenance": metrics["provenance"],
            "boundaries": metrics["boundaries"], "sampling": metrics["sampling"], "closure": metrics["closure"],
            "terminal_inferred_by_link": metrics["terminal_inferred_by_link"], "unresolved_inside_disappearances_by_link": metrics["unresolved_inside_disappearances_by_link"],
            "ttd_counted_unique_vehicle_ids": metrics["ttd_counted_unique_vehicle_ids"], "ttd_repeat_exit_events": metrics["ttd_repeat_exit_events"],
            "native_error_summary": native, "windows": interval_windows(rows, metrics)})
        save(out / "comparison.json", report)
        print(json.dumps({"arm": arm, "status": "measured", "full_window": report["arms"][-1]["windows"][0]}), flush=True)
    report["source_changes"] = [path for path, expected in pins.items() if sha(ROOT / path) != expected]
    require(not report["source_changes"], "Measurement evidence/source changed")
    report.update(status="complete", validation={"all_interval_closures_zero": True, "six_windows_sum_to_whole": True,
        "physical_residence_equals_area_TTT": True, "all_observed_exit_pairs_inside_to_outside": True,
        "native_warnings_require_separate_review": any(a["native_error_summary"]["status"] != "parsed_preserved_run_local_warnings" or a["native_error_summary"]["terminal_inference_removal_overlap_requires_review"] for a in report["arms"])})
    report["limitations"] = ["Alive outside boundary crossings count as TTD, including repeated real exits. Inside-to-inside transfers do not.",
        "First appearances inside are distinct from observed entries and are not all proven internal generation.",
        "Unknown inside disappearances are losses, never TTD; deletions may lower TTT/stock by truncating congestion.",
        "Native removal does not invalidate earlier genuine outside exits by the same ID. No blacklist or metric subtraction.",
        "Terminal24/120 departures are inferred; native removals there require review before interpreting those TD counts.",
        "Final5400-frame vehicles are censored, not exits. Closure certifies sampled bookkeeping, not missed subsecond excursions."]
    flat_rows = [{"arm": arm["arm"], **window} for arm in report["arms"] for window in arm["windows"]]
    write_rows(out / "windows.csv", flat_rows, list(flat_rows[0]))
    report["output_sha256"] = {relative(p): sha(p) for p in out.rglob("*") if p.is_file() and p != out / "comparison.json"}
    save(out / "comparison.json", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
