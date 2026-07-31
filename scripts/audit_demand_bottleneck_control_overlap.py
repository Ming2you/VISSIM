#!/usr/bin/env python
"""Audit overlap between demand inputs, bottleneck links, and active controls."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def inum(value: Any, default: int = 0) -> int:
    return int(round(fnum(value, float(default))))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def parse_link_list(value: str) -> set[int]:
    out: set[int] = set()
    for token in (value or "").replace(";", ",").split(","):
        token = token.strip().strip('"')
        if token:
            out.add(inum(token))
    return out


def markdown_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def integrate_toplog(rows: list[dict[str, str]], key_field: str, end_sec: float) -> list[dict[str, Any]]:
    rows = [row for row in rows if fnum(row.get("sim_sec"), end_sec + 1.0) <= end_sec]
    secs = sorted({fnum(row.get("sim_sec")) for row in rows})
    if not secs:
        return []
    dt_by_sec: dict[float, float] = {}
    for idx, sec in enumerate(secs):
        next_sec = secs[idx + 1] if idx + 1 < len(secs) else end_sec
        dt_by_sec[sec] = max(0.0, next_sec - sec)

    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "veh_h": 0.0,
            "stopped_h": 0.0,
            "speed_weight": 0.0,
            "count_time": 0.0,
            "max_count": 0.0,
            "max_stopped": 0.0,
            "max_density": 0.0,
            "samples": 0,
            "categories": Counter(),
            "freeway": False,
            "ramp_meter_connector": False,
            "local_observable": False,
            "first": {},
        }
    )
    for row in rows:
        key = str(row.get(key_field, ""))
        if not key:
            continue
        sec = fnum(row.get("sim_sec"))
        dt = dt_by_sec.get(sec, 0.0)
        count = max(0.0, fnum(row.get("count")))
        stopped = max(0.0, fnum(row.get("stopped_count")))
        speed = max(0.0, fnum(row.get("mean_speed_kph")))
        rec = stats[key]
        if not rec["first"]:
            rec["first"] = row
        rec["veh_h"] += count * dt / 3600.0
        rec["stopped_h"] += stopped * dt / 3600.0
        rec["speed_weight"] += speed * count * dt
        rec["count_time"] += count * dt
        rec["max_count"] = max(rec["max_count"], count)
        rec["max_stopped"] = max(rec["max_stopped"], stopped)
        rec["max_density"] = max(rec["max_density"], max(0.0, fnum(row.get("density_veh_km_lane"))))
        rec["samples"] += 1
        rec["categories"][str(row.get("category", ""))] += 1
        rec["freeway"] = rec["freeway"] or bool(inum(row.get("is_freeway")))
        rec["ramp_meter_connector"] = rec["ramp_meter_connector"] or bool(inum(row.get("is_ramp_meter_connector")))
        rec["local_observable"] = rec["local_observable"] or bool(inum(row.get("is_local_observable")))

    out: list[dict[str, Any]] = []
    for key, rec in stats.items():
        first = rec["first"]
        category = rec["categories"].most_common(1)[0][0] if rec["categories"] else ""
        avg_speed = rec["speed_weight"] / rec["count_time"] if rec["count_time"] > 0 else 0.0
        row = {
            "key": key,
            "category": category,
            "veh_h": rec["veh_h"],
            "stopped_h": rec["stopped_h"],
            "avg_speed": avg_speed,
            "max_count": rec["max_count"],
            "max_stopped": rec["max_stopped"],
            "max_density": rec["max_density"],
            "samples": rec["samples"],
            "freeway": rec["freeway"],
            "ramp_meter_connector": rec["ramp_meter_connector"],
            "local_observable": rec["local_observable"],
        }
        row.update({name: first.get(name, "") for name in ("model_link", "segment_index", "segment_id", "physical_link")})
        out.append(row)
    out.sort(key=lambda row: (row["stopped_h"], row["veh_h"], row["max_stopped"]), reverse=True)
    return out


def demand_inputs(path: Path, demand_scale: float) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in read_csv(path):
        link = inum(row.get("link"))
        if link <= 0:
            continue
        peak = fnum(row.get("peak_volume_vph"))
        rec = out.setdefault(link, {"roles": set(), "names": set(), "base_peak_vph": 0.0, "run_peak_vph": 0.0})
        rec["roles"].add(str(row.get("role", "")))
        name = str(row.get("name", "")).strip()
        if name:
            rec["names"].add(name)
        rec["base_peak_vph"] += peak
        rec["run_peak_vph"] += peak * demand_scale
    return out


def control_link_roles(control_mapping: Mapping[str, Any], signal_roles_path: Path) -> tuple[dict[int, set[str]], dict[int, set[str]]]:
    active_roles: dict[int, set[str]] = defaultdict(set)
    inventory_signals: dict[int, set[str]] = defaultdict(set)

    for model in (control_mapping.get("freeway_model_links", {}) or {}).values():
        if isinstance(model, Mapping):
            link = inum(model.get("physical_link"))
            if link:
                active_roles[link].add("vsl_freeway")
    for segment in control_mapping.get("segments", []) or []:
        if isinstance(segment, Mapping):
            link = inum(segment.get("link") or segment.get("physical_link"))
            if link:
                active_roles[link].add("vsl_segment")

    for meter in control_mapping.get("ramp_meters", []) or []:
        if not isinstance(meter, Mapping):
            continue
        for field, role in (
            ("connector", "ramp_meter_connector"),
            ("from_link", "ramp_meter_approach"),
            ("to_link", "ramp_meter_merge"),
        ):
            link = inum(meter.get(field))
            if link:
                active_roles[link].add(role)

    active_scs = {inum(row.get("sc_no")) for row in control_mapping.get("signals", []) or [] if isinstance(row, Mapping)}
    if signal_roles_path.exists():
        for row in read_csv(signal_roles_path):
            sc_no = inum(row.get("no"))
            for link in parse_link_list(row.get("unique_head_links", "")):
                inventory_signals[link].add(f"SC{sc_no}")
                if sc_no in active_scs:
                    active_roles[link].add(f"active_signal_SC{sc_no}")
    return active_roles, inventory_signals


def pct(part: float, total: float) -> str:
    return f"{100.0 * part / total:.1f}%" if total > 0 else "0.0%"


def coverage(
    rows: list[dict[str, Any]],
    active_roles: Mapping[int, set[str]],
    demand: Mapping[int, Any],
    inventory_signals: Mapping[int, set[str]],
    n: int,
) -> dict[str, Any]:
    top = rows[:n]
    total = sum(row["stopped_h"] for row in top)
    controlled = sum(row["stopped_h"] for row in top if active_roles.get(inum(row["key"])))
    demanded = sum(row["stopped_h"] for row in top if inum(row["key"]) in demand)
    local = sum(row["stopped_h"] for row in top if row["local_observable"])
    signal_inventory = sum(row["stopped_h"] for row in top if inventory_signals.get(inum(row["key"])))
    urban = sum(row["stopped_h"] for row in top if row["category"] == "urban_or_other")
    freeway = sum(row["stopped_h"] for row in top if row["category"] in {"freeway", "freeway_input"})
    return {
        "n": n,
        "total_stopped_h": total,
        "controlled_h": controlled,
        "demand_h": demanded,
        "local_h": local,
        "signal_inventory_h": signal_inventory,
        "urban_h": urban,
        "freeway_h": freeway,
    }


def signal_candidate_totals(rows: list[dict[str, Any]], inventory_signals: Mapping[int, set[str]], n: int) -> list[tuple[str, float]]:
    totals: Counter[str] = Counter()
    for row in rows[:n]:
        link = inum(row["key"])
        for signal in inventory_signals.get(link, set()):
            totals[signal] += row["stopped_h"]
    return [(signal, float(total)) for signal, total in totals.most_common()]


def join(values: Iterable[Any]) -> str:
    text = ",".join(str(value) for value in values if str(value))
    return text if text else "-"


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--links", type=Path, required=True)
    parser.add_argument("--segments", type=Path, required=True)
    parser.add_argument("--vehicle-inputs", type=Path, default=Path("evaluation/real_world_modi_inventory/vehicle_input_roles.csv"))
    parser.add_argument("--control-mapping", type=Path, default=Path("evaluation/real_world_modi_control/control_mapping.json"))
    parser.add_argument("--signal-roles", type=Path, default=Path("evaluation/real_world_modi_inventory/signal_controller_roles.csv"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--end-sec", type=float, default=7200.0)
    parser.add_argument("--demand-scale", type=float, default=1.0)
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args()

    demand = demand_inputs(args.vehicle_inputs, args.demand_scale)
    control_mapping = read_json(args.control_mapping)
    active_roles, inventory_signals = control_link_roles(control_mapping, args.signal_roles)
    link_rank = integrate_toplog(read_csv(args.links), "link", args.end_sec)
    segment_rank = integrate_toplog(read_csv(args.segments), "segment_id", args.end_sec)

    cov10 = coverage(link_rank, active_roles, demand, inventory_signals, min(10, len(link_rank)))
    cov20 = coverage(link_rank, active_roles, demand, inventory_signals, min(20, len(link_rank)))
    signal_totals = signal_candidate_totals(link_rank, inventory_signals, min(args.top_n, len(link_rank)))

    top_links = []
    for rank, row in enumerate(link_rank[: args.top_n], start=1):
        link = inum(row["key"])
        dinfo = demand.get(link, {})
        top_links.append([
            rank,
            link,
            row["category"],
            fmt(row["stopped_h"]),
            fmt(row["veh_h"]),
            fmt(row["max_count"], 0),
            fmt(row["max_stopped"], 0),
            fmt(row["avg_speed"]),
            fmt(dinfo.get("run_peak_vph", 0.0), 0) if dinfo else "-",
            join(dinfo.get("roles", [])) if dinfo else "-",
            join(sorted(active_roles.get(link, []))),
            "Y" if row["local_observable"] else "-",
            join(sorted(inventory_signals.get(link, []))),
        ])

    top_demands = []
    ranked_lookup = {inum(row["key"]): (idx, row) for idx, row in enumerate(link_rank, start=1)}
    for rank, (link, dinfo) in enumerate(
        sorted(demand.items(), key=lambda item: item[1]["run_peak_vph"], reverse=True)[: args.top_n],
        start=1,
    ):
        bottleneck_rank, brow = ranked_lookup.get(link, ("-", {}))
        top_demands.append([
            rank,
            link,
            fmt(dinfo["run_peak_vph"], 0),
            join(sorted(dinfo["roles"])),
            join(sorted(dinfo["names"]))[:40],
            bottleneck_rank,
            fmt(brow.get("stopped_h", 0.0)) if brow else "-",
            brow.get("category", "-") if brow else "-",
            join(sorted(active_roles.get(link, []))),
            join(sorted(inventory_signals.get(link, []))),
        ])

    top_segments = []
    for rank, row in enumerate(segment_rank[: min(16, len(segment_rank))], start=1):
        top_segments.append([
            rank,
            row["segment_id"],
            row["model_link"],
            row["segment_index"],
            row["physical_link"],
            fmt(row["stopped_h"]),
            fmt(row["veh_h"]),
            fmt(row["max_density"]),
            fmt(row["avg_speed"]),
        ])

    lines = [
        "# Demand/Bottleneck/Control Overlap Audit",
        "",
        f"- link_log: `{args.links}`",
        f"- segment_log: `{args.segments}`",
        f"- end_sec: {args.end_sec:.0f}",
        f"- demand_scale: {args.demand_scale:.2f}",
        "- note: bottleneck link logs contain sampled top links, so shares below are top-log shares, not full-network accounting.",
        "",
        "## Coverage",
        "",
        markdown_table(
            [
                "top",
                "stopped_h",
                "current_control",
                "demand_input",
                "local_obs",
                "signal_inventory",
                "urban_or_other",
                "freeway/freeway_input",
            ],
            [
                [
                    f"top {cov10['n']}",
                    fmt(cov10["total_stopped_h"]),
                    pct(cov10["controlled_h"], cov10["total_stopped_h"]),
                    pct(cov10["demand_h"], cov10["total_stopped_h"]),
                    pct(cov10["local_h"], cov10["total_stopped_h"]),
                    pct(cov10["signal_inventory_h"], cov10["total_stopped_h"]),
                    pct(cov10["urban_h"], cov10["total_stopped_h"]),
                    pct(cov10["freeway_h"], cov10["total_stopped_h"]),
                ],
                [
                    f"top {cov20['n']}",
                    fmt(cov20["total_stopped_h"]),
                    pct(cov20["controlled_h"], cov20["total_stopped_h"]),
                    pct(cov20["demand_h"], cov20["total_stopped_h"]),
                    pct(cov20["local_h"], cov20["total_stopped_h"]),
                    pct(cov20["signal_inventory_h"], cov20["total_stopped_h"]),
                    pct(cov20["urban_h"], cov20["total_stopped_h"]),
                    pct(cov20["freeway_h"], cov20["total_stopped_h"]),
                ],
            ],
        ),
        "",
        "## Signal Expansion Candidates",
        "",
        markdown_table(
            ["rank", "signal", "top_link_stopped_h"],
            [[rank, signal, fmt(total)] for rank, (signal, total) in enumerate(signal_totals[:12], start=1)],
        ),
        "",
        "## Top Bottleneck Links By Stopped-Hours",
        "",
        markdown_table(
            [
                "rank",
                "link",
                "category",
                "stopped_h",
                "veh_h",
                "max_count",
                "max_stop",
                "avg_kph",
                "run_peak_vph",
                "demand_role",
                "current_control",
                "local_obs",
                "signal_candidates",
            ],
            top_links,
        ),
        "",
        "## Top Demand Inputs",
        "",
        markdown_table(
            [
                "rank",
                "link",
                "run_peak_vph",
                "role",
                "name",
                "bneck_rank",
                "stopped_h",
                "category",
                "current_control",
                "signal_candidates",
            ],
            top_demands,
        ),
        "",
        "## Freeway Segment Bottlenecks",
        "",
        markdown_table(
            ["rank", "segment", "model", "idx", "physical_link", "stopped_h", "veh_h", "max_density", "avg_kph"],
            top_segments,
        ),
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
