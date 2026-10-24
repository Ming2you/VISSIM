"""Vehicle-ID passage counts and queues on physical interchange connectors.

Report observed connector departures separately from source-to-target jumps
that skip a short connector between samples. No snapshot density*speed is
called capacity, and disappearance from an interior link is not a departure.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / ".review-deps"))
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CONNECTORS = (10682, 10643, 10646, 10639, 10681, 10644, 10772, 10773,
              10483, 10481, 10484, 10490, 10480, 10482, 10479, 10491, 10638, 10645)


def scan(fzp, network, period=150):
    tree = ET.parse(network)
    triples = {}
    for link in tree.findall(".//links/link"):
        number = int(link.attrib["no"])
        if number in CONNECTORS:
            source = int(link.find("fromLinkEndPt").attrib["lane"].split()[0])
            target = int(link.find("toLinkEndPt").attrib["lane"].split()[0])
            triples[number] = (source, target)
    # A skipped connector is only inferred when the physical pair is unambiguous.
    all_pairs = defaultdict(list)
    for link in tree.findall(".//links/link"):
        source, target = link.find("fromLinkEndPt"), link.find("toLinkEndPt")
        if source is not None and target is not None:
            pair = tuple(int(node.attrib["lane"].split()[0]) for node in (source, target))
            all_pairs[pair].append(int(link.attrib["no"]))
    pair_to_connector = {pair: conn for conn, pair in triples.items() if len(all_pairs[pair]) == 1}
    departures = Counter()
    arrivals = Counter()
    speed_sums = Counter()
    samples = Counter()
    stopped = Counter()
    times = defaultdict(set)
    previous = {}
    current = {}
    current_t = None
    record_times = []

    def flush(t):
        nonlocal previous
        block = int(t // period) * period
        times[block].add(t)
        record_times.append(t)
        for veh, (link, speed) in current.items():
            if link in triples:
                samples[block, link] += 1
                speed_sums[block, link] += speed
                stopped[block, link] += int(speed < 5)
            prev = previous.get(veh)
            if prev is None or prev[0] == link:
                continue
            old = prev[0]
            # The vehicle can also traverse the short target road before the
            # next snapshot. Presence on a different link still proves that it
            # left this connector; demanding immediate target identity misses it.
            if old in triples:
                departures[block, old, "observed_connector_departure"] += 1
            if link in triples:
                arrivals[block, link, "observed_connector_arrival"] += 1
            conn = pair_to_connector.get((old, link))
            if conn is not None:
                departures[block, conn, "inferred_short_connector_jump"] += 1
                arrivals[block, conn, "inferred_short_connector_jump"] += 1
        previous = current.copy()

    with fzp.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if line.startswith("$VEHICLE:"):
                header = line.strip().split(":", 1)[1].split(";")
                indices = {name: header.index(name) for name in ("SIMSEC", "NO", "LANE\\LINK\\NO", "SPEED")}
                break
        else:
            raise ValueError("FZP schema missing")
        for row in csv.reader(stream, delimiter=";"):
            if len(row) != len(header):
                raise ValueError("FZP row does not match schema")
            t = float(row[indices["SIMSEC"]])
            if current_t is not None and t != current_t:
                flush(current_t)
                current = {}
            current_t = t
            current[int(row[indices["NO"]])] = (int(row[indices["LANE\\LINK\\NO"]]), float(row[indices["SPEED"]]))
        if current_t is not None:
            flush(current_t)
    output = []
    for block in sorted(times):
        for conn, (source, target) in triples.items():
            sample_count = samples[block, conn]
            observed = departures[block, conn, "observed_connector_departure"]
            inferred = departures[block, conn, "inferred_short_connector_jump"]
            output.append(dict(start_sec=block, end_sec=block + period, connector=conn,
                source_link=source, target_link=target, departures_observed=observed,
                departures_inferred=inferred, departures_total=observed + inferred,
                discharge_vph=(observed + inferred) * 3600 / period,
                arrival_events=sum(value for key, value in arrivals.items() if key[:2] == (block, conn)),
                mean_vehicles=sample_count / len(times[block]),
                mean_stopped=stopped[block, conn] / len(times[block]),
                mean_speed_kph=speed_sums[block, conn] / sample_count if sample_count else None))
    return pd.DataFrame(output), dict(first_time=record_times[0], last_time=record_times[-1],
        observation_step_sec=min(b - a for a, b in zip(record_times, record_times[1:])),
        definition="Vehicle-ID source/connector/target transitions; short connector skips separately tagged",
        limitation="5-second snapshots may miss multi-link passages; no interior disappearances counted; first/final blocks censored")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("--network", type=Path, default=ROOT / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx")
    a = p.parse_args()
    files = list((a.run / "vissim_eval").glob("*.fzp"))
    if len(files) != 1:
        raise ValueError("Expected exactly one FZP")
    out = a.run / "analysis"
    out.mkdir(exist_ok=True)
    frame, metadata = scan(files[0], a.network)
    frame.to_csv(out / "physical_connector_passages.csv", index=False)
    (out / "physical_connector_passages_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    fig, axes = plt.subplots(3, 1, figsize=(13, 9), constrained_layout=True, sharex=True)
    for conn in (10682, 10643, 10646, 10772):
        rows = frame.loc[frame.connector == conn]
        for ax, column in zip(axes, ("discharge_vph", "mean_vehicles", "mean_speed_kph")):
            ax.plot((rows.start_sec + rows.end_sec) / 120, rows[column], label=str(conn))
    for ax, label in zip(axes, ("Passage flow (veh/h)", "Mean vehicles on connector", "Mean speed (km/h)")):
        ax.set(ylabel=label)
        ax.grid(alpha=.2)
        ax.legend(ncol=4)
    axes[-1].set_xlabel("Simulation minute")
    fig.suptitle("FW_E → F interchange: measured passage, occupancy and speed")
    fig.savefig(out / "F_interchange_passages.png", dpi=160)
    plt.close(fig)
    print(frame.loc[(frame.start_sec >= 900) & (frame.start_sec < 5400)].groupby("connector")[[
        "discharge_vph", "mean_vehicles", "mean_stopped", "mean_speed_kph"]].mean().round(2).to_string())


if __name__ == "__main__":
    main()
