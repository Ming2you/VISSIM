"""Bounded native interaction evidence; no COM, forecasts or parameter changes."""
from pathlib import Path
from collections import Counter
from bisect import bisect_right
import ctypes
import ctypes.wintypes
import gzip
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from diagnostics.probe_e8_lane_receiving import IndexedFzp


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    assert not (OUT / "frames.json.gz").exists(), "Reuse the cache; do not reread native files."
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    geometry = json.loads((ROOT / "diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json").read_text(encoding="utf-8"))
    cells = [c for c in geometry["cells"] if c["road"] == "FW_E"]
    offsets = {}
    for c in cells:
        x = c["start_m"]
        for p in c["physical_pieces"]:
            offsets.setdefault(p["link"], x)
            x += p["length_m"]
    bounds = [c["start_m"] for c in cells] + [cells[-1]["end_m"]]
    extras = ["ACCELERATION", "POSLAT", "LNCHG", "DESTLANE", "INTERACTSTATE", "INTERACTTARGTYPE", "INTERACTTARGNO", "NEXTLINK\\NO", "ROUTDECNO", "ROUTENO", "LENGTH"]
    times = [round(2700.1 + 5*i, 1) for i in range(90)]
    write("protocol.json", {
        "question": "Are stationary mainline queues associated with mandatory lane-change blockers, or with other downstream interaction targets?",
        "population": "All vehicles in east physical cells16..25; buffer15..26, four adjacent ramps, recursive current interaction targets retained. No outcome-selected exit cohort.",
        "times": times, "cases": ["release", "release_vsl90"], "extras": extras,
        "read_budget_bytes_per_arm": 170 * 1024**2,
        "rules": ["Native 5s samples only, not all lane-change events.", "LNCHG denotes current change direction, not unfulfilled intention.", "Interaction chains and prior changes are associations, not causal attribution.", "Stop thresholds 5km/h and1km/h, same-link changes only, no lane-number remapping treated as lane change.", "No new fit, forecast, VISSIM, production edit, push or active-process intervention."]})
    started = time.monotonic()
    result = {"offsets_m": offsets, "bounds_m": bounds, "cases": {}}
    summaries = {}
    for arm in ("release", "release_vsl90"):
        path = Path("D:/VISSIM_runs/20261003_s67_vsl_observation2700") / arm / "vissim_eval" / ("sdmpc31_g_2700_" + arm + "_s67_001.fzp")
        before = path.stat()
        reader = IndexedFzp(path, max_bytes=170*1024**2)
        frames, states, targets, lc = [], Counter(), Counter(), Counter()
        for t in times:
            snapshot = reader.snapshot(t, extra_columns=extras)
            keep = set()
            mapped = {}
            for vid, row in snapshot.items():
                link, lane, pos, speed, extra = row
                x = offsets[link] + pos if link in offsets else None
                cell = bisect_right(bounds, x)-1 if x is not None else None
                mapped[vid] = cell
                if (cell is not None and 15 <= cell <= 26) or link in (10481, 10483, 10490, 10484):
                    keep.add(vid)
            todo = list(keep)
            while todo:
                extra = snapshot[todo.pop()][4]
                if extra["INTERACTTARGTYPE"] != "Vehicle":
                    continue
                target = int(extra["INTERACTTARGNO"]) if extra["INTERACTTARGNO"] else None
                if target in snapshot and target not in keep:
                    keep.add(target)
                    todo.append(target)
            rows = {}
            for vid in sorted(keep):
                link, lane, pos, speed, extra = snapshot[vid]
                c = mapped[vid]
                rows[vid] = {"link": link, "lane": lane, "pos": pos, "speed": speed, "cell": c, **extra}
                if c is not None and 16 <= c <= 25 and speed < 5:
                    states[extra["INTERACTSTATE"]] += 1
                    targets[extra["INTERACTTARGTYPE"]] += 1
                    lc[extra["LNCHG"]] += 1
            frames.append({"t": t, "rows": rows})
        reader.handle.close()
        after = path.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "Source changed during read"
        result["cases"][arm] = {"frames": frames, "source": str(path), "size": before.st_size, "mtime_ns": before.st_mtime_ns, "bytes_read": reader.bytes_read, "selected": reader.selected}
        summaries[arm] = {"bytes_read": reader.bytes_read, "retained_rows": sum(len(f["rows"]) for f in frames), "stopped_sample_states": dict(states), "stopped_sample_targets": dict(targets), "stopped_sample_lane_change": dict(lc)}
        print(arm, json.dumps(summaries[arm]), flush=True)
    with gzip.open(OUT / "frames.json.gz", "wt", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
    summaries["elapsed_sec"] = time.monotonic()-started
    write("extract_summary.json", summaries)
    print("complete", summaries["elapsed_sec"], flush=True)


if __name__ == "__main__":
    main()
