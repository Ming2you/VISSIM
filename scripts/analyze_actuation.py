"""Audit requested levers against COM readback and native signal-state changes.

Signal CSV 'stored' means a delivered plan, not observed green. COM transitions
and periodic persistence samples take precedence over native .lsa program logs,
which do not reflect COM overrides in the measured VISSIM 2020 runs.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def signal_intervals(path, end):
    previous = {}
    result = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            fields = [v.strip() for v in line.split(";")]
            if len(fields) < 7:
                continue
            try:
                time, sc, sg = float(fields[0]), int(fields[2]), int(fields[3])
            except ValueError:
                continue
            key = sc, sg
            if key in previous:
                start, aspect = previous[key]
                if time < start:
                    raise ValueError(f"signal events out of order: {key}")
                if time > start:
                    result.append((sc, sg, start, min(time, end), aspect))
            previous[key] = (time, fields[4].lower())
    for (sc, sg), (start, aspect) in previous.items():
        if start < end:
            result.append((sc, sg, start, end, aspect))
    return result


def readback_intervals(path, end):
    previous, intervals, first = {}, [], {}
    samples = Counter()
    mismatches = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = int(row["sc_no"]), int(row["sg_no"])
            time, aspect = float(row["sim_sec"]), row["readback_state"].lower()
            first.setdefault(key, time)
            samples[row["stage"], aspect] += 1
            if row["ok"] != "1":
                mismatches.append(row)
            if key in previous:
                begin, old = previous[key]
                if time < begin:
                    raise ValueError(f"COM readback out of order: {key}")
                if time > begin:
                    intervals.append((*key, begin, min(time, end), old))
            previous[key] = time, aspect
    for key, (begin, aspect) in previous.items():
        if begin < end:
            intervals.append((*key, begin, end, aspect))
    return intervals, first, {f"{stage}:{aspect}": count for (stage, aspect), count in samples.items()}, mismatches


def audit(run, start=900.0, end=5400.0, period=150):
    out = run / "analysis"
    out.mkdir(exist_ok=True)
    native = signal_intervals(next((run / "vissim_eval").glob("*.lsa")), end)
    com, com_first, com_samples, com_mismatches = readback_intervals(
        next(run.glob("decisions_*")) / "signal_readback.csv", end)
    intervals = list(com)
    for sc, sg, begin, finish, aspect in native:
        finish = min(finish, com_first.get((sc, sg), end))
        if finish > begin:
            intervals.append((sc, sg, begin, finish, aspect))
    durations = Counter()
    for sc, sg, begin, finish, aspect in intervals:
        left, finish = max(start, begin), min(end, finish)
        while left < finish:
            block = int(left // period) * period
            right = min(finish, block + period)
            durations[sc, sg, block, aspect] += right - left
            left = right
    inventory = sorted({(sc, sg, block) for sc, sg, block, _ in durations})
    aspects = sorted({aspect for *_, aspect in durations})
    with (out / "signal_seconds_from_readback.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sc", "sg", "start_sec", "known_sec"] + aspects)
        writer.writeheader()
        for sc, sg, block in inventory:
            values = {aspect: durations[sc, sg, block, aspect] for aspect in aspects}
            writer.writerow(dict(sc=sc, sg=sg, start_sec=block, known_sec=sum(values.values()), **values))
    with next(run.glob("action_*.csv")).open(encoding="utf-8-sig", newline="") as handle:
        commands = [r for r in csv.DictReader(handle) if start <= float(r["sim_sec"]) < end]
    vsl = [r for r in commands if r["kind"] == "vsl"]
    vsl_mismatch = []
    for row in vsl:
        try:
            values = [float(x) for x in row["readback"].split("|")]
            if not values or any(abs(x - float(row["speed_kph"])) > 1e-6 for x in values):
                vsl_mismatch.append(row)
        except ValueError:
            vsl_mismatch.append(row)
    decisions = []
    for path in sorted(next(run.glob("decisions_*")).glob("action_*.json")):
        time = int(path.stem.split("_")[-1])
        if not start <= time < end:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        diag, meta = data.get("diagnostics", {}), data.get("metadata", {})
        on, off = diag.get("wu_faithful_offset_ttt_on"), diag.get("wu_faithful_offset_ttt_off")
        decisions.append({"sim_sec": time, "writer": meta.get("offset_writer"),
                          "searched_nonzero": diag.get("wu_faithful_offsets_searched_off_zero"),
                          "kept_nonzero": sum(abs(v) > 1e-9 for v in data.get("offsets", {}).values()),
                          "model_ttt_with_offsets": on, "model_ttt_zero_offsets": off,
                          "model_gain_fraction": (off - on) / off if on is not None and off else None})
    mapping = json.loads((ROOT / "evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json").read_text())
    ramp_summary = []
    for ramp in mapping["ramp_meters"]:
        sc, sg = ramp["sc_no"], ramp["sg_no"]
        values = Counter()
        for (c, g, block, aspect), seconds in durations.items():
            if (c, g) == (sc, sg):
                values[aspect] += seconds
        known = sum(values.values())
        ramp_summary.append({"connector": ramp["connector"], "model_ramp": ramp["model_ramp_key"],
                             "sc": sc, "known_sec": known, "aspects_sec": dict(values),
                             "green_fraction": values["green"] / known if known else None,
                             "off_fraction": values["off"] / known if known else None,
                             "red_fraction": values["red"] / known if known else None})
    signal_commands = [r for r in commands if r["kind"] == "signal"]
    summary = {"run": run.name, "window_sec": [start, end],
               "vsl_command_rows": len(vsl), "vsl_immediate_readback_mismatch_rows": len(vsl_mismatch),
               "vsl_readback_caveat": "Immediate DSD distribution IDs, not subsequent vehicle speeds or persistent state.",
               "signal_plan_rows": len(signal_commands),
               "nonzero_written_offset_rows": sum(abs(float(r["offset"])) > 1e-9 for r in signal_commands),
               "offset_decisions": decisions, "physical_ramps": ramp_summary,
               "com_readback_samples": com_samples, "com_readback_mismatches": len(com_mismatches),
               "signal_caveat": "COM write readbacks plus periodic post_step persistence checks take precedence. Durations hold the last checked state between records; unobserved intervening changes cannot be excluded. Native .lsa is used only before COM takes over or for native SGs. NC ramp .lsa OFF disagrees with COM GREEN and is not treated as the actual override state."}
    (out / "actuation_audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.path.append(str(ROOT / ".review-deps"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    keys = sorted({(sc, sg) for sc, sg, *_ in intervals if sc in (1001, 1004) or 9101 <= sc <= 9108})
    fig, ax = plt.subplots(figsize=(15, max(6, len(keys) * 0.22)))
    lookup = {key: i for i, key in enumerate(keys)}
    for sc, sg, begin, finish, aspect in intervals:
        if (sc, sg) in lookup and aspect in ("green", "off") and finish > start and begin < end:
            begin, finish = max(start, begin), min(end, finish)
            ax.broken_barh([(begin / 60, (finish - begin) / 60)], (lookup[sc, sg] - .35, .7),
                          facecolors="#18865b" if aspect == "green" else "#93b9d4")
    ax.set(yticks=range(len(keys)), yticklabels=[f"SC{sc} / SG{sg}" for sc, sg in keys],
           xlabel="Simulation time (min)", xlim=(start / 60, end / 60),
           title=f"{run.name}: COM-checked transitions / native SGs (green=GREEN, blue=OFF)")
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    fig.savefig(out / "actual_signal_green.png", dpi=160)
    plt.close(fig)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("offset_decisions", "signal_caveat")}, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--start", type=float, default=900)
    parser.add_argument("--end", type=float, default=5400)
    args = parser.parse_args()
    audit(args.run.resolve(), args.start, args.end)
