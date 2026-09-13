"""Read-only return-frame trace of base score vector versus Link follower commit."""
from __future__ import annotations
import atexit
import hashlib
import json
import os
from pathlib import Path
import sys


def install(directory):
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    stream_path = destination / f"phase_commit_{pid}.jsonl"
    summary_path = destination / f"phase_commit_{pid}.json"
    pending, records = {}, []
    previous = sys.getprofile()

    def capture(control):
        greens = {str(k): float(v) for k, v in control.green_times.items()}
        offsets = {str(k): float(v) for k, v in control.offsets.items()}
        blob = json.dumps(greens, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return {"greens": greens, "green_sha256": hashlib.sha256(blob.encode()).hexdigest(), "offsets": offsets}

    def profile(frame, event, arg):
        if previous is not None:
            previous(frame, event, arg)
        if event != "return" or frame.f_code.co_name != "solve" or arg is None:
            return
        path = frame.f_code.co_filename.replace("\\", "/")
        base = path.endswith("/controllers/wu_faithful_follower.py")
        outer = path.endswith("/controllers/priced_wu_link_controller.py")
        if not (base or outer) or not hasattr(arg, "control"):
            return
        if base:
            follower = frame.f_locals.get("self")
            pending[id(arg)] = {**capture(arg.control), "objective": float(arg.objective_value),
                                "phase_price_in_gne": bool(getattr(follower, "phase_price_in_gne", False)),
                                "stored_phase_overrides": len(getattr(follower, "_gne_phase_override", {}) or {})}
            return
        before = pending.pop(id(arg), None)
        after = capture(arg.control)
        differences = {} if before is None else {
            key: {"before": before["greens"].get(key), "after": after["greens"].get(key)}
            for key in before["greens"].keys() | after["greens"].keys()
            if before["greens"].get(key) != after["greens"].get(key)}
        row = {"index": len(records), "pid": pid, "parent_pid": os.getppid(),
               "base_found": before is not None, "before": before, "after": after,
               "objective_after": float(arg.objective_value),
               "changed_phase_values": len(differences), "changes": differences,
               "max_abs_green_delta_sec": max((abs(v["after"] - v["before"]) for v in differences.values()
                                                 if v["before"] is not None and v["after"] is not None), default=0.)}
        records.append(row)
        with stream_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")

    def finish():
        sys.setprofile(previous)
        if not records and not pending:
            return
        report = {"scope": "actual base/outer solve return frames; no function replacement or model mutation",
                  "pid": pid, "parent_pid": os.getppid(), "paired_returns": len(records),
                  "missing_base_returns": sum(not row["base_found"] for row in records),
                  "unmatched_base_returns": len(pending),
                  "changed_returns": sum(row["changed_phase_values"] > 0 for row in records),
                  "max_abs_green_delta_sec": max((row["max_abs_green_delta_sec"] for row in records), default=0.),
                  "rows_file": str(stream_path), "records": records}
        summary_path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")

    sys.setprofile(profile)
    atexit.register(finish)
    return finish
