#!/usr/bin/env python
"""Summarize VISSIM real-world bottleneck logs and recommend active levers."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def rows_through(rows: Iterable[dict[str, str]], end_sec: float) -> list[dict[str, str]]:
    out = [
        row
        for row in rows
        if (sim_sec := fnum(row.get("sim_sec"), math.nan)) == sim_sec and sim_sec <= end_sec
    ]
    return out


def integrate_points(points: list[tuple[float, float]], end_sec: float) -> float:
    pts = sorted((t, y) for t, y in points if t <= end_sec)
    if not pts:
        return 0.0
    if pts[0][0] > 0.0:
        pts.insert(0, (0.0, 0.0))
    if pts[-1][0] < end_sec:
        pts.append((end_sec, pts[-1][1]))
    area = 0.0
    for (t0, y0), (t1, y1) in zip(pts, pts[1:]):
        area += (t1 - t0) * (y0 + y1) / 2.0
    return area / 3600.0


def group_rows(rows: Iterable[dict[str, str]], key_fields: tuple[str, ...]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row.get(field, "")) for field in key_fields)].append(row)
    return groups


def weighted_speed(rows: Iterable[dict[str, str]]) -> float:
    total = 0.0
    weighted = 0.0
    for row in rows:
        count = max(0.0, fnum(row.get("count")))
        speed = max(0.0, fnum(row.get("mean_speed_kph")))
        total += count
        weighted += count * speed
    return weighted / total if total > 0 else 0.0


def delay_proxy_points(rows: Iterable[dict[str, str]], free_flow_kph: float) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for row in rows:
        sim_sec = fnum(row.get("sim_sec"), math.nan)
        if sim_sec != sim_sec:
            continue
        count = max(0.0, fnum(row.get("count")))
        speed = max(0.0, fnum(row.get("mean_speed_kph")))
        speed_gap = max(0.0, free_flow_kph - speed) / max(free_flow_kph, 1.0e-9)
        out.append((sim_sec, count * speed_gap))
    return out


def summarize_segment_rows(rows: list[dict[str, str]], end_sec: float, free_flow_kph: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, group in group_rows(rows, ("model_link", "segment_index")).items():
        model_link, segment_index = key
        first = group[0]
        count_pts = [(fnum(row.get("sim_sec")), max(0.0, fnum(row.get("count")))) for row in group]
        stopped_pts = [
            (fnum(row.get("sim_sec")), max(0.0, fnum(row.get("stopped_count"))))
            for row in group
        ]
        out.append({
            "segment_id": first.get("segment_id", f"RW_{model_link}_S{segment_index}"),
            "model_link": model_link,
            "segment_index": int(fnum(segment_index)),
            "physical_link": int(fnum(first.get("physical_link"))),
            "veh_h": integrate_points(count_pts, end_sec),
            "stopped_h": integrate_points(stopped_pts, end_sec),
            "delay_proxy_h": integrate_points(delay_proxy_points(group, free_flow_kph), end_sec),
            "max_count": max(max(0.0, fnum(row.get("count"))) for row in group),
            "final_count": max(0.0, fnum(sorted(group, key=lambda row: fnum(row.get("sim_sec")))[-1].get("count"))),
            "max_density": max(max(0.0, fnum(row.get("density_veh_km_lane"))) for row in group),
            "avg_speed": weighted_speed(group),
        })
    out.sort(key=lambda row: (row["delay_proxy_h"], row["veh_h"], row["max_density"]), reverse=True)
    return out


def summarize_link_rows(rows: list[dict[str, str]], end_sec: float, free_flow_kph: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for (link,), group in group_rows(rows, ("link",)).items():
        first = group[0]
        count_pts = [(fnum(row.get("sim_sec")), max(0.0, fnum(row.get("count")))) for row in group]
        stopped_pts = [
            (fnum(row.get("sim_sec")), max(0.0, fnum(row.get("stopped_count"))))
            for row in group
        ]
        out.append({
            "link": int(fnum(link)),
            "category": first.get("category", ""),
            "veh_h": integrate_points(count_pts, end_sec),
            "stopped_h": integrate_points(stopped_pts, end_sec),
            "delay_proxy_h": integrate_points(delay_proxy_points(group, free_flow_kph), end_sec),
            "max_count": max(max(0.0, fnum(row.get("count"))) for row in group),
            "final_count": max(0.0, fnum(sorted(group, key=lambda row: fnum(row.get("sim_sec")))[-1].get("count"))),
            "avg_speed": weighted_speed(group),
        })
    out.sort(key=lambda row: (row["delay_proxy_h"], row["veh_h"], row["stopped_h"]), reverse=True)
    return out


def segment_controls(control_mapping: Mapping[str, Any], detector_mapping: Mapping[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    controls: dict[tuple[str, int], dict[str, Any]] = {}
    for segment in control_mapping.get("segments", []) or []:
        if not isinstance(segment, Mapping):
            continue
        key = (str(segment.get("model_link", "")), int(fnum(segment.get("model_segment_index"))))
        controls.setdefault(key, {
            "vsl_segment": str(segment.get("segment_id", "")),
            "ramps": [],
            "off_ramps": [],
            "signals": [],
        })
    for meter in control_mapping.get("ramp_meters", []) or []:
        if not isinstance(meter, Mapping):
            continue
        key = (str(meter.get("to_model_link", "")), int(fnum(meter.get("to_model_segment_index"))))
        rec = controls.setdefault(key, {"vsl_segment": "", "ramps": [], "off_ramps": [], "signals": []})
        ramp_key = str(meter.get("model_ramp_key", ""))
        if ramp_key and ramp_key not in rec["ramps"]:
            rec["ramps"].append(ramp_key)
    for origin, connectors in (detector_mapping.get("off_ramp_connectors", {}) or {}).items():
        if not isinstance(connectors, list):
            continue
        for conn in connectors:
            if not isinstance(conn, Mapping):
                continue
            model_link = "FW_E" if int(fnum(conn.get("from_link"))) == 2 else "FW_W" if int(fnum(conn.get("from_link"))) == 26 else ""
            if not model_link:
                continue
            seg_idx = position_to_segment(control_mapping, model_link, fnum(conn.get("from_pos_m")))
            rec = controls.setdefault((model_link, seg_idx), {"vsl_segment": "", "ramps": [], "off_ramps": [], "signals": []})
            if str(origin) not in rec["off_ramps"]:
                rec["off_ramps"].append(str(origin))
            signal = str(origin).split("_")[1] if "_" in str(origin) else ""
            if signal and signal not in rec["signals"]:
                rec["signals"].append(signal)
    return controls


def position_to_segment(control_mapping: Mapping[str, Any], model_link: str, pos_m: float) -> int:
    model = (control_mapping.get("freeway_model_links", {}) or {}).get(model_link, {})
    bounds = model.get("segment_bounds_m", []) if isinstance(model, Mapping) else []
    if not isinstance(bounds, list) or len(bounds) < 2:
        return 0
    for idx, upper in enumerate(bounds[1:]):
        if pos_m < fnum(upper):
            return idx
    return max(0, len(bounds) - 2)


def link_annotations(control_mapping: Mapping[str, Any], detector_mapping: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for meter in control_mapping.get("ramp_meters", []) or []:
        if not isinstance(meter, Mapping):
            continue
        for key in ("connector", "from_link", "to_link"):
            link = int(fnum(meter.get(key)))
            if link <= 0:
                continue
            rec = out.setdefault(link, {"roles": set(), "ramps": set(), "off_ramps": set(), "signals": set()})
            rec["roles"].add("ramp_meter_" + key)
            rec["ramps"].add(str(meter.get("model_ramp_key", "")))
    for origin, connectors in (detector_mapping.get("off_ramp_connectors", {}) or {}).items():
        if not isinstance(connectors, list):
            continue
        for conn in connectors:
            if not isinstance(conn, Mapping):
                continue
            for key in ("connector", "from_link", "to_link"):
                link = int(fnum(conn.get(key)))
                if link <= 0:
                    continue
                rec = out.setdefault(link, {"roles": set(), "ramps": set(), "off_ramps": set(), "signals": set()})
                rec["roles"].add("off_ramp_" + key)
                rec["off_ramps"].add(str(origin))
                signal = str(origin).split("_")[1] if "_" in str(origin) else ""
                if signal:
                    rec["signals"].add(signal)
    for link, movements in (detector_mapping.get("link_to_movements", {}) or {}).items():
        rec = out.setdefault(int(fnum(link)), {"roles": set(), "ramps": set(), "off_ramps": set(), "signals": set()})
        rec["roles"].add("local_movement")
        if isinstance(movements, list):
            for movement in movements:
                if isinstance(movement, Mapping):
                    signal = str(movement.get("signal", ""))
                    if signal:
                        rec["signals"].add(signal)
    normalized: dict[int, dict[str, Any]] = {}
    for link, rec in out.items():
        normalized[link] = {key: sorted(value) for key, value in rec.items()}
    return normalized


def recommend_mask(
    segments: list[dict[str, Any]],
    links: list[dict[str, Any]],
    controls: Mapping[tuple[str, int], Mapping[str, Any]],
    link_notes: Mapping[int, Mapping[str, Any]],
    top_segments: int,
) -> dict[str, Any]:
    selected = segments[:top_segments]
    allowed_segments: set[str] = set()
    allowed_ramps: set[str] = set()
    allowed_signals: set[str] = set()
    for row in selected:
        model_link = str(row["model_link"])
        idx = int(row["segment_index"])
        for neighbor in (idx - 1, idx, idx + 1):
            if neighbor < 0:
                continue
            rec = controls.get((model_link, neighbor), {})
            vsl_segment = str(rec.get("vsl_segment", ""))
            if vsl_segment:
                allowed_segments.add(vsl_segment)
            allowed_ramps.update(str(value) for value in rec.get("ramps", []) or [])
            allowed_signals.update(str(value) for value in rec.get("signals", []) or [])
    for row in links[:10]:
        notes = link_notes.get(int(row["link"]), {})
        if row["delay_proxy_h"] <= 0.0 and row["stopped_h"] <= 0.0:
            continue
        allowed_ramps.update(str(value) for value in notes.get("ramps", []) or [] if value)
        allowed_signals.update(str(value) for value in notes.get("signals", []) or [] if value)
    return {
        "enabled": True,
        "allowed_vsl_segments": sorted(allowed_segments),
        "allowed_ramps": sorted(allowed_ramps),
        "allowed_signals": sorted(allowed_signals),
        "selection_rule": f"top {top_segments} segment bottlenecks plus immediate neighbors and local connector controls",
    }


def write_config(path: Path, base_tuning: str, name: str, mask: Mapping[str, Any], summary: Mapping[str, Any]) -> None:
    data = {
        "extends": base_tuning,
        "name": name,
        "description": "P-Stack tuning with active controls masked to observed scale-1.35 bottleneck neighborhoods.",
        "actuation": {
            "active_lever_mask": dict(mask),
        },
        "bottleneck_audit": summary,
        "notes": [
            "Inactive VSL segments are forced to free-flow speed in the adapter before prediction/action export.",
            "Inactive ramp meters are forced to their model capacity/open state.",
            "This is a bottleneck-aligned authority test config, not a final calibrated controller.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--end-sec", type=float, default=300.0)
    parser.add_argument("--free-flow-kph", type=float, default=100.0)
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--top-segments-for-mask", type=int, default=4)
    parser.add_argument("--control-mapping", type=Path, default=Path("evaluation/real_world_modi_control/control_mapping.json"))
    parser.add_argument("--detector-mapping", type=Path, default=Path("evaluation/real_world_modi_control/detector_local_mapping.json"))
    parser.add_argument("--write-config", type=Path)
    parser.add_argument("--base-tuning", default="real_world_modi_pstack_adapter_v1_response_calibrated_20260721.json")
    parser.add_argument("--config-name", default="real_world_modi_pstack_bottleneck_mask_scale135_20260722")
    args = parser.parse_args()

    seg_path = args.base / f"bottleneck_segments_{args.run}.csv"
    link_path = args.base / f"bottleneck_links_{args.run}.csv"
    if not seg_path.exists() or not link_path.exists():
        raise SystemExit(f"Missing bottleneck CSVs: {seg_path} / {link_path}")

    control_mapping = read_json(args.control_mapping)
    detector_mapping = read_json(args.detector_mapping)
    seg_rows = rows_through(read_csv(seg_path), args.end_sec)
    link_rows = rows_through(read_csv(link_path), args.end_sec)
    segments = summarize_segment_rows(seg_rows, args.end_sec, args.free_flow_kph)
    links = summarize_link_rows(link_rows, args.end_sec, args.free_flow_kph)
    controls = segment_controls(control_mapping, detector_mapping)
    notes = link_annotations(control_mapping, detector_mapping)
    mask = recommend_mask(segments, links, controls, notes, args.top_segments_for_mask)

    print("SEGMENT_RANK")
    print("rank,segment_id,model_link,idx,veh_h,delay_proxy_h,stopped_h,max_count,max_density,avg_speed,nearby_vsl,nearby_ramps,nearby_offramps,nearby_signals")
    for rank, row in enumerate(segments[: args.top_n], start=1):
        rec = controls.get((str(row["model_link"]), int(row["segment_index"])), {})
        print(",".join([
            str(rank),
            str(row["segment_id"]),
            str(row["model_link"]),
            str(row["segment_index"]),
            fmt(row["veh_h"]),
            fmt(row["delay_proxy_h"]),
            fmt(row["stopped_h"]),
            fmt(row["max_count"], 0),
            fmt(row["max_density"]),
            fmt(row["avg_speed"], 2),
            str(rec.get("vsl_segment", "")),
            "|".join(rec.get("ramps", []) or []),
            "|".join(rec.get("off_ramps", []) or []),
            "|".join(rec.get("signals", []) or []),
        ]))

    print("\nLINK_RANK")
    print("rank,link,category,veh_h,delay_proxy_h,stopped_h,max_count,avg_speed,roles,ramps,offramps,signals")
    for rank, row in enumerate(links[: args.top_n], start=1):
        rec = notes.get(int(row["link"]), {})
        print(",".join([
            str(rank),
            str(row["link"]),
            str(row["category"]),
            fmt(row["veh_h"]),
            fmt(row["delay_proxy_h"]),
            fmt(row["stopped_h"]),
            fmt(row["max_count"], 0),
            fmt(row["avg_speed"], 2),
            "|".join(rec.get("roles", []) or []),
            "|".join(rec.get("ramps", []) or []),
            "|".join(rec.get("off_ramps", []) or []),
            "|".join(rec.get("signals", []) or []),
        ]))

    print("\nRECOMMENDED_ACTIVE_LEVER_MASK")
    print(json.dumps(mask, indent=2, ensure_ascii=False))

    audit = {
        "source_run": args.run,
        "source_base": str(args.base),
        "end_sec": args.end_sec,
        "top_segment_ids": [row["segment_id"] for row in segments[: args.top_segments_for_mask]],
        "top_links": [row["link"] for row in links[: args.top_n]],
    }
    if args.write_config:
        write_config(args.write_config, args.base_tuning, args.config_name, mask, audit)
        print(f"\nWROTE_CONFIG {args.write_config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
