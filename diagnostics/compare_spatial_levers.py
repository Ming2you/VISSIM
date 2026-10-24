"""Read-only comparison of three completed seed-13 runs on common windows."""
from __future__ import annotations
from collections import defaultdict
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNS = {"NC": "codex_nc_s13_6056c94_20260909_retry",
        "n7": "codex_n7_pure_s13_20260910",
        "VSL80": "codex_vsl80_upstream_s13_20260910"}
LINKS = [10481, 127, 10682, 68, 121, 10646, 10639, 70, 71, 420, 40, 32, 10491]


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def onset(series, predicate, minimum_sec):
    start = None
    previous = None
    for sec, row in series:
        if predicate(row):
            if start is None or previous != sec - 30:
                start = sec
            if sec - start >= minimum_sec:
                return start
        else:
            start = None
        previous = sec
    return None


def compare(runs=None, output_prefix="spatial_lever"):
    runs = RUNS if runs is None else runs
    result = {"method": {"stock_window_sec": [900, 5400], "stock_cadence_sec": 30,
                         "passage_window_sec": [900, 5250],
                         "note": "Passages exclude final censored 150-second block; link stock metrics use trapezoids and zero-fill absent vehicle rows."},
              "runs": {}}
    curves = []
    for label, run in runs.items():
        directory = ROOT / "evaluation/runs" / run
        links = defaultdict(dict)
        for row in rows(directory / f"bottleneck_links_{run}.csv"):
            sec, link = int(row["sim_sec"]), int(row["link"])
            if 900 <= sec <= 5400 and sec % 30 == 0 and link in LINKS:
                links[link][sec] = {key: float(row[key]) for key in ("count", "stopped_count", "mean_speed_kph")}
        stats = {}
        for link in LINKS:
            series = [(sec, links[link].get(sec, dict(count=0, stopped_count=0, mean_speed_kph=0)))
                      for sec in range(900, 5401, 30)]
            measures = {}
            for key in ("count", "stopped_count"):
                integral = sum((left[1][key] + right[1][key]) * (right[0] - left[0]) / 7200
                               for left, right in zip(series, series[1:]))
                measures[key + "_veh_h"] = integral
                measures["mean_" + key] = integral / 1.25
                measures["peak_" + key] = max(x[key] for _, x in series)
            measures["slow90_onset_sec"] = onset(series, lambda x: x["count"] >= 5 and x["mean_speed_kph"] < 30, 90)
            measures["stopped10_300_onset_sec"] = onset(series, lambda x: x["stopped_count"] >= 10, 300)
            stats[str(link)] = measures
            for sec, values in series:
                curves.append(dict(run=label, link=link, sim_sec=sec, **values))
        passages = defaultdict(list)
        for row in rows(directory / "analysis/physical_connector_passages.csv"):
            if 900 <= float(row["start_sec"]) and float(row["end_sec"]) <= 5250:
                passages[row["connector"]].append(row)
        passage_stats = {}
        for connector, data in passages.items():
            passage_stats[connector] = dict(source=data[0]["source_link"], target=data[0]["target_link"],
                observed=sum(float(x["departures_observed"]) for x in data),
                inferred=sum(float(x["departures_inferred"]) for x in data),
                discharge_vph=sum(float(x["departures_total"]) for x in data) * 3600 / 4350,
                mean_stopped=sum(float(x["mean_stopped"]) for x in data) / len(data),
                mean_vehicles=sum(float(x["mean_vehicles"]) for x in data) / len(data))
        area = json.loads((directory / "analysis/area_metrics.json").read_text(encoding="utf-8"))
        actuation = json.loads((directory / "analysis/actuation_audit.json").read_text(encoding="utf-8"))
        green_seconds = defaultdict(float)
        for row in rows(directory / "analysis/signal_seconds_from_readback.csv"):
            if int(row["sc"]) in (1001, 1004, 105):
                green_seconds[row["sc"] + "/" + row["sg"]] += float(row.get("green", 0))
        source_paths = [directory / f"bottleneck_links_{run}.csv"] + [directory / "analysis" / name for name in
                       ("area_metrics.json", "actuation_audit.json", "physical_connector_passages.csv",
                        "congestion_events.csv", "signal_seconds_from_readback.csv")]
        result["runs"][label] = dict(run=run, links=stats, passages=passage_stats,
                area={k: v for k, v in area.items() if not isinstance(v, (dict, list))},
                physical_link_residence={str(link): area["physical_link_residence"].get(str(link)) for link in LINKS},
                green_seconds=dict(green_seconds),
                source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths},
                actuation={k: v for k, v in actuation.items() if k != "offset_decisions"},
                congestion=rows(directory / "analysis/congestion_events.csv"))
    output = ROOT / "diagnostics" / f"{output_prefix}_comparison.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    with (ROOT / "diagnostics" / f"{output_prefix}_curves.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(curves[0]))
        writer.writeheader()
        writer.writerows(curves)
    sys.path.append(str(ROOT / ".review-deps"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 2, figsize=(13, 9), sharex=True)
    for ax, link in zip(axes.flat, (127, 40, 420, 10682, 10646, 10639)):
        for label, color in zip(runs, ("#777777", "#b74830", "#2474b0", "#5c8c32", "#9565a3")):
            data = [row for row in curves if row["run"] == label and row["link"] == link]
            smoothed = [sum(row["stopped_count"] for row in data[max(0, i-4):i+1]) / min(5, i+1)
                        for i in range(len(data))]
            ax.plot([row["sim_sec"] / 60 for row in data], smoothed, label=label, color=color)
        ax.set_title(f"Physical link {link}")
        ax.set_ylabel("Stopped vehicles")
        ax.grid(alpha=.2)
    for ax in axes[-1]:
        ax.set_xlabel("Simulation time (min)")
    axes[0, 0].legend()
    fig.suptitle("Seed 13: spatial queue changes (trailing five 30-second samples)")
    fig.tight_layout()
    fig.savefig(ROOT / "diagnostics" / f"{output_prefix}_queues.png", dpi=160)
    plt.close(fig)
    for link in LINKS:
        print(link, {label: {k: round(v, 2) if isinstance(v, float) else v for k, v in run["links"][str(link)].items()
                            if k in {"mean_stopped_count", "peak_stopped_count", "slow90_onset_sec", "stopped10_300_onset_sec"}}
                     for label, run in result["runs"].items()})
    for connector in ("10481", "10682", "10646", "10639", "10644", "10681"):
        print("passage", connector, {label: run["passages"].get(connector) for label, run in result["runs"].items()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", metavar="LABEL=RUN_DIRECTORY")
    parser.add_argument("--output-prefix", default="spatial_lever")
    args = parser.parse_args()
    selected = dict(item.split("=", 1) for item in args.run) if args.run else None
    if selected is not None and not 1 <= len(selected) <= 5:
        parser.error("Use one to five distinct run labels")
    if Path(args.output_prefix).name != args.output_prefix:
        parser.error("output-prefix must be a filename prefix")
    compare(selected, args.output_prefix)
