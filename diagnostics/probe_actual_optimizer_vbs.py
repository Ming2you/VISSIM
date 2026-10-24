"""Consume an existing real optimizer CSV with canonical VBS and fake COM.

This does not run an optimizer or VISSIM, and cannot establish live authority.
The original CSV bytes are passed directly to actual ApplyActionCsv.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics import test_profile_runner_invocation as harness


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(action_path, output_dir, sec):
    action_path, output_dir = action_path.resolve(), output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with action_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    axes = {row["sc_no"]: row for row in rows if row["kind"] == "signal"}
    groups = [row for row in rows if row["kind"] == "signal_sg"]
    nonzero = {key: float(row["offset"]) for key, row in axes.items() if float(row["offset"]) != 0}
    assert axes and groups
    assert all("offset_writer=experiment" in row["metadata"] and "physical_signal_contract=1" in row["metadata"] for row in rows)
    script_path = harness.build_harness(output_dir, "wu-link", "signal_profile_config_sc1004_green10.json")
    script = script_path.read_text(encoding="utf-16")
    script = script.replace('RW_OFFSET_WRITER = "test_only"', 'RW_OFFSET_WRITER = "experiment"')
    begin = script.rindex('If UseContinuousStaticMode() Then')
    end_marker = 'WScript.Echo "LAST_ACTION=" & lastActionJson'
    end = script.index(end_marker, begin) + len(end_marker)
    script = script[:begin] + (
        f'If ApplyActionCsv({sec}, {harness.q(action_path)}, "wu-link") Then\n'
        'WScript.Echo "EXPERIMENT_ACCEPTED"\n'
        f'ApplyRuntimeSignals {sec}\n'
        'WScript.Echo "AXIS_COUNT=" & sigPhaseGreen.Count\n'
        'Else\nWScript.Echo "EXPERIMENT_REJECTED"\nEnd If\n'
    ) + script[end:]
    script_path.write_text(script, encoding="utf-16")
    result = subprocess.run(["cscript.exe", "//nologo", str(script_path)], cwd=ROOT,
                            capture_output=True, text=True, errors="replace", timeout=30,
                            env=dict(os.environ, RW_OFFSET_WRITER="experiment", RW_MAINLINE_SG_ONLY="1",
                                     RW_SIGNAL_READBACK_SEC="1", RW_SIGNAL_WRITE_ON_CHANGE="0"))
    (output_dir / "cscript.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    with (output_dir / "signalTraceFile.csv").open(newline="") as stream:
        trace = list(csv.DictReader(stream))
    errors = [row for row in trace if row["ok"] != "1" or row["readback"] != row["requested"]]
    written_sc = sorted({row["sc"] for row in trace if int(row["sc"]) < 9100}, key=int)
    accepted = result.returncode == 0 and "EXPERIMENT_ACCEPTED" in result.stdout and "ERROR=" not in result.stdout
    report = {
        "scope": "Actual optimizer CSV -> canonical VBS ApplyActionCsv -> first ApplyRuntimeSignals; fake COM only",
        "action_csv": str(action_path), "action_csv_sha256": digest(action_path),
        "vbs_source": str(harness.RUNNER), "vbs_source_sha256": digest(harness.RUNNER),
        "harness_sha256": digest(script_path), "sim_sec": sec,
        "environment": {"RW_OFFSET_WRITER": "experiment", "RW_MAINLINE_SG_ONLY": "1", "RW_SIGNAL_WRITE_ON_CHANGE": "0"},
        "axis_rows": len(axes), "sg_rows": len(groups), "nonzero_offset_count": len(nonzero),
        "nonzero_offsets_sec": nonzero, "exit_code": result.returncode, "accepted": accepted,
        "first_event_readback_rows": len(trace), "readback_mismatches": errors,
        "urban_controllers_written": written_sc,
        "all_urban_controllers_written": set(written_sc) == set(axes),
        "passed": accepted and bool(trace) and not errors and set(written_sc) == set(axes),
    }
    sibling = action_path.with_suffix(".json")
    if sibling.exists():
        payload = json.loads(sibling.read_text(encoding="utf-8"))
        report["action_json_sha256"] = digest(sibling)
        report["action_metadata"] = {key: value for key, value in payload.get("metadata", {}).items()
                                     if key.startswith("offset_") or key.startswith("physical_signal_contract")}
    (output_dir / "result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    assert report["passed"], report
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action_csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sec", type=int, required=True)
    args = parser.parse_args()
    run(args.action_csv, args.output, args.sec)
