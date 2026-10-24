"""Audit actual simulation warnings, especially removals that are not TTD.

The network-load .err does not contain these events. Archive the numbered
simulation .err before another run overwrites it, then pass that archived file.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.control_area_objective import physical_membership_from_ledger

EVENT = re.compile(r"Simulation second ([\d.]+): (.*)", re.I)
REMOVED = re.compile(r"After ([\d.]+) seconds of waiting for lane change the vehicle (\d+).*?"
                     r"was removed from link (\d+) at position (\d+(?:\.\d+)?)", re.I)
SKIPPED = re.compile(r"Vehicle (\d+) ignores the (static routing|desired speed) decision (\d+) "
                     r"because it has left link (\d+) at position ([\d.]+)", re.I)


def parse(lines, membership):
    records = []
    for line in lines:
        match = EVENT.search(line)
        if not match:
            continue
        time, message = float(match[1]), match[2].strip()
        row = dict(sim_sec=time, kind="other", vehicle="", link="", position_m="",
                   inside="", wait_sec="", decision="", message=message)
        removed, skipped = REMOVED.search(message), SKIPPED.search(message)
        if removed:
            wait, vehicle, link, position = removed.groups()
            if link not in membership:
                raise ValueError(f"Removal on unclassified physical link {link}")
            row.update(kind="lane_change_removal", vehicle=vehicle, link=link,
                       position_m=float(position), inside=membership[link], wait_sec=float(wait))
        elif skipped:
            vehicle, kind, decision, link, position = skipped.groups()
            row.update(kind="skipped_route" if kind.lower().startswith("static") else "skipped_desired_speed",
                       vehicle=vehicle, link=link, position_m=float(position),
                       inside=membership.get(link, ""), decision=decision)
        elif "remov" in message.lower():
            row["kind"] = "other_removal_message"
        records.append(row)
    counts = Counter(row["kind"] for row in records)
    removals = [r for r in records if r["kind"] == "lane_change_removal"]
    by_link = Counter(r["link"] for r in removals)
    return records, dict(
        event_counts=dict(counts),
        lane_change_removal_inside=sum(r["inside"] for r in removals),
        lane_change_removal_outside=sum(not r["inside"] for r in removals),
        lane_change_removal_by_link=dict(by_link.most_common()),
        skipped_desired_speed_by_decision=dict(Counter(r["decision"] for r in records if r["kind"] == "skipped_desired_speed")),
        skipped_route_by_decision=dict(Counter(r["decision"] for r in records if r["kind"] == "skipped_route")),
        last_warning_sim_sec=max((r["sim_sec"] for r in records), default=None),
        interpretation="Forced lane-change removals are simulation losses, never completed vehicles or TTD. Absence of a warning does not prove a complete trajectory ledger.",
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--error-file", type=Path)
    a = p.parse_args()
    source = a.error_file or a.run / "vissim_simulation_001.err"
    data = source.read_bytes()
    ledger = json.loads((ROOT / "diagnostics/control_area_membership.json").read_text(encoding="utf-8"))
    rows, summary = parse(data.decode("utf-8", errors="replace").splitlines(), physical_membership_from_ledger(ledger))
    summary["source"] = {"path": str(source.resolve()), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    out = a.run / "analysis"
    out.mkdir(exist_ok=True)
    (out / "simulation_errors_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if rows:
        with (out / "simulation_warning_events.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
