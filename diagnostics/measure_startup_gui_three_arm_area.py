"""Measure completed native runs with the existing area CLI, then difference windows.

No controller evaluation, COM, simulator, source edits or repository writes.
Only a fresh diagnostics output directory is created.
"""
from __future__ import annotations
import argparse
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/measure_control_area.py"
MEMBERSHIP = ROOT / "diagnostics/control_area_membership.json"
FLAT = ROOT / "diagnostics/fixed_beta300v3_network_arms_flat_v1"
ARMS = ("baseline", "lcd10635_2000", "upstream1135")
EVENTS = ("observed_entry_events", "appeared_inside_events", "observed_exit_events",
          "terminal_exit_inferred_events", "unresolved_inside_disappearances", "reappeared_inside_events")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def physical_links(path, arm):
    tree = ET.parse(path)
    rows = tree.getroot().findall("./links/link")
    result = {}
    for row in rows:
        no = row.attrib["no"]
        if no in result:
            raise ValueError("Duplicate physical link " + no)
        if no == "10635":
            expected = "2000" if arm == "lcd10635_2000" else "1000"
            if row.attrib["lnChgDist"] != expected:
                raise ValueError("Unexpected 10635 lane-change distance")
            row.attrib["lnChgDist"] = "1000"
        result[no] = ET.tostring(row, encoding="unicode")
    if not result:
        raise ValueError("No physical network links")
    return result


def windows(rows, metrics):
    by_time = {float(row["sim_sec"]): row for row in rows}
    if len(by_time) != len(rows):
        raise ValueError("Duplicate area timeseries timestamp")
    answer = []
    for start, end in ((0, 1050), (750, 900), (900, 1050)):
        if (start and start not in by_time) or end not in by_time:
            raise ValueError("Missing exact requested window endpoint")
        begin = by_time[start] if start else {"inside_vehicles": "0", "ttt_veh_h_cumulative": "0", "ttd_observed_plus_terminal_cumulative": "0", "source": "assumed_initial_empty"}
        finish = by_time[end]
        selected = [row for row in rows if start < float(row["sim_sec"]) <= end]
        counts = {key: sum(int(row[key]) for row in selected) for key in EVENTS}
        n0, n1 = int(begin["inside_vehicles"]), int(finish["inside_vehicles"])
        ttt = float(finish["ttt_veh_h_cumulative"]) - float(begin["ttt_veh_h_cumulative"])
        td = float(finish["ttd_observed_plus_terminal_cumulative"]) - float(begin["ttd_observed_plus_terminal_cumulative"])
        left = right = 0.0
        previous_time, previous_n = start, n0
        for row in selected:
            current_time, current_n = float(row["sim_sec"]), int(row["inside_vehicles"])
            dt = current_time - previous_time
            if dt != 1 or float(row["interval_sec"]) != dt:
                raise ValueError("Requested window does not have exact 1-second cadence")
            left += previous_n * dt / 3600
            right += current_n * dt / 3600
            previous_time, previous_n = current_time, current_n
        if previous_time != end or not math.isclose(ttt, (left + right) / 2, rel_tol=1e-11, abs_tol=1e-9):
            raise ValueError("Window trapezoid does not reproduce cumulative difference")
        if td != counts["observed_exit_events"] + counts["terminal_exit_inferred_events"]:
            raise ValueError("Window exit totals do not reproduce cumulative difference")
        closure = n1 - n0 - counts["observed_entry_events"] - counts["appeared_inside_events"] + td + counts["unresolved_inside_disappearances"]
        if closure or any(int(row["stock_closure_residual_veh"]) for row in selected):
            raise ValueError("Window stock ledger does not close")
        answer.append({"start_sec": start, "end_sec": end, "duration_sec": end-start,
                       "event_assignment": "start < observed upper timestamp <= end",
                       "ttt_veh_h": ttt, "ttt_left_veh_h": left, "ttt_right_veh_h": right,
                       "ttd_events": int(td), **counts, "initial_inside_vehicles": n0,
                       "final_inside_vehicles": n1, "stock_closure_residual_veh": int(closure),
                       "start_source": begin["source"], "end_source": finish["source"],
                       "censored_hold_rows": sum(row["source"] == "censored_hold_extrapolation" for row in selected),
                       "reappeared_inside_scope": "uses complete prior run history, not window-local ID reset"})
    if not math.isclose(answer[0]["ttt_veh_h"], metrics["ttt_veh_h"], abs_tol=1e-9):
        raise ValueError("Full-window TTT differs from original CLI")
    return answer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "diagnostics/startup_gui_three_arm_comparison_v1/manifest.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / "diagnostics") or out.exists():
        raise ValueError("Output must be a new directory within diagnostics")
    assembly = load(args.manifest)
    if not assembly.get("completed") or not assembly.get("valid") or assembly.get("source_changes"):
        raise ValueError("Completed experiment receipt is not valid")
    arms = {row["arm"]: row for row in assembly["arms"]}
    if set(arms) != set(ARMS):
        raise ValueError("Unexpected experiment arms")
    ledger = load(MEMBERSHIP)
    inside, outside = set(ledger["inside_links"]), set(ledger["outside_links"])
    if len(inside) != len(ledger["inside_links"]) or len(outside) != len(ledger["outside_links"]) or inside & outside:
        raise ValueError("Membership duplicate or overlap")
    flat = load(FLAT / "manifest.json")
    baseline_links = physical_links(FLAT / "baseline.inpx", "baseline")
    if set(baseline_links) != inside | outside:
        raise ValueError("Membership does not cover the complete physical network")
    sources = [Path(__file__), SCRIPT, MEMBERSHIP, args.manifest.resolve(), FLAT / "manifest.json",
               ROOT / "evaluation/controllers/control_area_objective.py"]
    sources += [ROOT / x["path"] for x in [ledger["network"]] + ledger["sources"]]
    for arm in ARMS:
        sources.append(FLAT / (arm + ".inpx"))
        run = ROOT / arms[arm]["run"]
        provenance = list(run.glob("run_provenance_*.json"))
        if len(provenance) != 1:
            raise ValueError("Expected one native provenance per arm")
        sources += provenance
    pins = {p.relative_to(ROOT).as_posix(): sha(p) for p in sources}
    for item in [ledger["network"]] + ledger["sources"]:
        if pins[item["path"]] != item["sha256"]:
            raise ValueError("Frozen membership source changed")
    out.mkdir()
    report = {"schema": "startup-three-arm-control-area/v1", "status": "running", "source_sha256": pins,
              "scope": "Native sampled area measurement; not a model or timing benchmark",
              "membership": {"inside_links": len(inside), "outside_links": len(outside), "definition": ledger["definition"],
                             "terminal_inside_links": ledger["terminal_inside_links"], "counts": ledger["counts"],
                             "protected_union_ramp_checks": ledger["ramp_checks"], "verified_all_inside_paths": ledger["verified_all_inside_paths"]},
              "arms": []}
    save(out / "comparison.json", report)
    for arm in ARMS:
        row = arms[arm]
        network = FLAT / (arm + ".inpx")
        expected = row["network_sha256"]
        if pins[network.relative_to(ROOT).as_posix()] != expected or flat["outputs"][network.name]["destination_sha256"] != expected:
            raise ValueError("Network receipt/hash mismatch")
        if physical_links(network, arm) != baseline_links:
            raise ValueError("Physical link geometry/topology changed beyond allowed lane-change distance")
        directory = out / arm
        directory.mkdir()
        analysis_ledger = copy.deepcopy(ledger)
        analysis_ledger["network"] = {"path": network.relative_to(ROOT).as_posix(), "sha256": expected}
        analysis_ledger["analysis_only_variant_binding"] = {"original_membership_sha256": pins[MEMBERSHIP.relative_to(ROOT).as_posix()],
            "only_network_binding_changed": True, "inside_outside_terminal_lists_unchanged": True,
            "all_physical_link_elements_exact_after_normalizing_only_10635_lnChgDist": True}
        membership_path = directory / "membership_analysis_only.json"
        save(membership_path, analysis_ledger)
        run = ROOT / row["run"]
        fzps = list((run / "vissim_eval").glob("*.fzp"))
        if len(fzps) != 1:
            raise ValueError("Expected exactly one FZP")
        fzp = fzps[0]
        stat_before = (fzp.stat().st_size, fzp.stat().st_mtime_ns)
        command = [sys.executable, "-B", "-X", "utf8", str(SCRIPT), "--run", str(run), "--fzp-only",
                   "--membership", str(membership_path), "--end-sec", "1050", "--out", str(directory)]
        save(directory / "command.json", {"argv": command, "cwd": str(ROOT), "measurement_script_sha256": pins[SCRIPT.relative_to(ROOT).as_posix()]})
        started = time.perf_counter()
        with (directory / "stdout.txt").open("wb") as stdout, (directory / "stderr.txt").open("wb") as stderr:
            process = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        elapsed = time.perf_counter() - started
        if process.returncode:
            raise RuntimeError("Existing measurement CLI failed for " + arm)
        if stat_before != (fzp.stat().st_size, fzp.stat().st_mtime_ns):
            raise ValueError("FZP changed during measurement")
        metrics = load(directory / "area_metrics.json")
        with (directory / "area_timeseries.csv").open(encoding="utf8", newline="") as stream:
            timeseries = list(csv.DictReader(stream))
        arm_result = {"arm": arm, "run": row["run"], "network_sha256": expected, "measurement_exit_code": process.returncode,
                      "measurement_elapsed_sec_not_benchmark": elapsed, "fzp_stat_unchanged": True,
                      "original_metrics_path": (directory / "area_metrics.json").relative_to(ROOT).as_posix(),
                      "provenance": metrics["provenance"], "boundaries": metrics["boundaries"], "sampling": metrics["sampling"],
                      "full_closure": metrics["closure"], "terminal_inferred_by_link": metrics["terminal_inferred_by_link"],
                      "unresolved_inside_disappearances_by_link": metrics["unresolved_inside_disappearances_by_link"],
                      "exit_events_by_observed_link_pair": metrics["exit_events_by_observed_link_pair"],
                      "windows": windows(timeseries, metrics)}
        report["arms"].append(arm_result)
        save(out / "comparison.json", report)
        print(json.dumps({"arm": arm, "windows": arm_result["windows"]}, ensure_ascii=False), flush=True)
    changes = [p for p, expected in pins.items() if sha(ROOT / p) != expected]
    report["source_changes"] = changes
    if changes:
        raise ValueError("Measurement source changed")
    report["status"] = "complete"
    report["limitations"] = ["TTD counts boundary exit events, including alive outside movements and repeat exits; not a unique-ID blacklist.",
        "Inside-to-inside urban/freeway transfers contribute no entry or exit event.",
        "First appearances inside are distinct from observed boundary entries and cannot all be identified as internal generation.",
        "Terminal departures are inferred; unknown inside disappearances are losses, never TTD.",
        "Last-frame vehicles remain censored; any short unobserved tail is explicitly held without exit inference.",
        "One-second sampling can miss an outside excursion completed between frames; closure verifies sampled bookkeeping.",
        "A single seed with changed route/lane behavior supports matched outcomes, not a separated causal mechanism."]
    save(out / "comparison.json", report)
    flat_rows = [{"arm": arm["arm"], **window} for arm in report["arms"] for window in arm["windows"]]
    with (out / "windows.csv").open("w", encoding="utf8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
