from __future__ import annotations

import argparse
import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def clean_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = "".join(ch for ch in value if ch.isdigit() or ch == "-")
    return int(text) if text else None


def clean_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return float(text)


def lane_ref(value: str | None) -> dict[str, int | None]:
    if not value:
        return {"link": None, "lane": None}
    parts = value.split()
    return {
        "link": int(parts[0]) if len(parts) >= 1 and parts[0].lstrip("-").isdigit() else None,
        "lane": int(parts[1]) if len(parts) >= 2 and parts[1].lstrip("-").isdigit() else None,
    }


def link_points(link: ET.Element) -> list[tuple[float, float, float]]:
    pts: list[tuple[float, float, float]] = []
    for pt in link.findall("./geometry/linkPolyPts/linkPolyPoint"):
        x = clean_float(pt.get("x"))
        y = clean_float(pt.get("y"))
        z = clean_float(pt.get("zOffset")) or 0.0
        if x is not None and y is not None:
            pts.append((x, y, z))
    return pts


def polyline_length(points: list[tuple[float, float, float]]) -> float:
    total = 0.0
    for (x1, y1, z1), (x2, y2, z2) in zip(points, points[1:]):
        total += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
    return total


def classify_link(name: str, no: int, is_connector: bool) -> str:
    n = name.lower()
    if is_connector:
        if "ramp" in n or "merge" in n or "diverge" in n:
            return "ramp_connector"
        return "turn_connector"
    if name.startswith("FW_") or "freeway" in n or "mainline" in n:
        return "freeway_mainline"
    if "ramp" in n or "trumpet" in n or "_loop" in n:
        return "ramp"
    if "boundary" in n:
        return "boundary"
    if "arterial" in n:
        return "urban_internal"
    return "other_link"


def expected_urban_pair_name(a: str, b: str) -> str:
    return f"{a}-{b} arterial {a} to {b}"


def expected_urban_name(edge_a: str, edge_b: str, from_node: str, to_node: str) -> str:
    return f"{edge_a}-{edge_b} arterial {from_node} to {to_node}"


def parse_links(root: ET.Element) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    links: list[dict[str, Any]] = []
    connectors: list[dict[str, Any]] = []

    for link in root.iter("link"):
        no = clean_int(link.get("no"))
        if no is None:
            continue
        name = link.get("name", "")
        from_ep = link.find("./fromLinkEndPt")
        to_ep = link.find("./toLinkEndPt")
        is_connector = from_ep is not None or to_ep is not None
        lanes = link.findall("./lanes/lane")
        pts = link_points(link)
        length = polyline_length(pts)
        lane_widths = [clean_float(lane.get("width")) for lane in lanes]

        item = {
            "no": no,
            "name": name,
            "type": classify_link(name, no, is_connector),
            "is_connector": is_connector,
            "lane_count": len(lanes),
            "lane_widths": lane_widths,
            "length_m": round(length, 3),
            "start_xy": [round(pts[0][0], 3), round(pts[0][1], 3)] if pts else None,
            "end_xy": [round(pts[-1][0], 3), round(pts[-1][1], 3)] if pts else None,
        }
        if is_connector:
            item["from"] = {
                **lane_ref(from_ep.get("lane") if from_ep is not None else None),
                "pos": clean_float(from_ep.get("pos")) if from_ep is not None else None,
            }
            item["to"] = {
                **lane_ref(to_ep.get("lane") if to_ep is not None else None),
                "pos": clean_float(to_ep.get("pos")) if to_ep is not None else None,
            }
            connectors.append(item)
        else:
            links.append(item)
    return links, connectors


def parse_by_tag(root: ET.Element, tag: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for el in root.iter(tag):
        rows.append(dict(el.attrib))
    return rows


def parse_nodes(root: ET.Element) -> list[dict[str, Any]]:
    return [
        {"no": clean_int(el.get("no")), "name": el.get("name", ""), **dict(el.attrib)}
        for el in root.iter("node")
    ]


def group_links(links: list[dict[str, Any]], connectors: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {item["name"]: item["no"] for item in links + connectors if item["name"]}
    link_type_by_no = {item["no"]: item["type"] for item in links}

    urban_edges = [
        ("A", "B"), ("B", "C"), ("A", "D"), ("B", "E"),
        ("C", "F"), ("D", "E"), ("E", "F"),
    ]
    boundary_pairs = [
        ("AW", "A"), ("AN", "A"), ("BN", "B"), ("CN", "C"),
        ("CE", "C"), ("DW", "D"), ("FE", "F"),
    ]

    mapping: dict[str, Any] = {
        "schema_version": 1,
        "notes": [
            "Draft mapping generated from current user-edited Vissim network.",
            "Geometry is treated as frozen; downstream scripts should not rewrite link shapes.",
            "Controller phase 1 uses global vehicle state, so detector lists are optional.",
        ],
        "freeway": {
            "EB": [],
            "WB": [],
        },
        "urban_internal": {},
        "boundary_inputs": {},
        "trumpet_ramps": {
            "D": [],
            "F": [],
        },
        "connectors": {
            "intersection_turns": [],
            "ramp_merge_diverge": [],
        },
        "nodes": {
            "controlled_intersections": ["A", "B", "C", "D", "F"],
            "uncontrolled_intersections": ["E"],
            "trumpet_interchanges": ["D", "F"],
        },
        "global_state_groups": {
            "urban_links": [],
            "freeway_links": [],
            "ramp_links": [],
            "boundary_links": [],
        },
    }

    for item in links:
        no = item["no"]
        name = item["name"]
        typ = item["type"]
        if typ == "freeway_mainline":
            if "FW_E" in name:
                mapping["freeway"]["EB"].append(no)
            elif "FW_W" in name:
                mapping["freeway"]["WB"].append(no)
            mapping["global_state_groups"]["freeway_links"].append(no)
        elif typ == "urban_internal":
            mapping["global_state_groups"]["urban_links"].append(no)
        elif typ == "boundary":
            mapping["global_state_groups"]["boundary_links"].append(no)
        elif typ == "ramp":
            mapping["global_state_groups"]["ramp_links"].append(no)
            if name.startswith("D ") or name.startswith("D_") or " D " in name:
                mapping["trumpet_ramps"]["D"].append(no)
            elif name.startswith("F ") or name.startswith("F_") or " F " in name:
                mapping["trumpet_ramps"]["F"].append(no)

    for a, b in urban_edges:
        fwd = by_name.get(expected_urban_name(a, b, a, b))
        rev = by_name.get(expected_urban_name(a, b, b, a))
        mapping["urban_internal"][f"{a}_{b}"] = {
            f"{a}_to_{b}": fwd,
            f"{b}_to_{a}": rev,
        }

    for a, b in boundary_pairs:
        inbound = by_name.get(f"{b if a in ['CE', 'FE'] else b} boundary {a} to {b}")
        outbound = by_name.get(f"{b if a in ['CE', 'FE'] else b} boundary {b} to {a}")
        # Fall back to substring search because generated names are human-readable.
        if inbound is None:
            inbound = next((item["no"] for item in links if f"{a} to {b}" in item["name"]), None)
        if outbound is None:
            outbound = next((item["no"] for item in links if f"{b} to {a}" in item["name"]), None)
        mapping["boundary_inputs"][f"{a}_to_{b}"] = {
            "entry_link": inbound,
            "exit_link": outbound,
        }

    ramp_related_link_types = {"freeway_mainline", "ramp"}
    for c in connectors:
        from_type = link_type_by_no.get(c.get("from", {}).get("link"))
        to_type = link_type_by_no.get(c.get("to", {}).get("link"))
        is_ramp_related = from_type in ramp_related_link_types or to_type in ramp_related_link_types
        bucket = "ramp_merge_diverge" if is_ramp_related else "intersection_turns"
        mapping["connectors"][bucket].append(c["no"])

    return mapping


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inpx", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    inpx = Path(args.inpx)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    root = ET.parse(inpx).getroot()
    links, connectors = parse_links(root)
    all_links = links + connectors
    counter = Counter(item["type"] for item in all_links)

    vehicle_inputs = parse_by_tag(root, "vehicleInput")
    data_points = parse_by_tag(root, "dataCollectionPoint")
    queue_counters = parse_by_tag(root, "queueCounter")
    route_decisions = parse_by_tag(root, "vehicleRoutingDecisionStatic")
    routes = parse_by_tag(root, "vehicleRouteStatic")
    signal_controllers = parse_by_tag(root, "signalController")
    signal_groups = parse_by_tag(root, "signalGroup")
    signal_heads = parse_by_tag(root, "signalHead")
    detectors = parse_by_tag(root, "detector")
    desired_speed_decisions = parse_by_tag(root, "desSpeedDecision")
    nodes = parse_nodes(root)

    inventory = {
        "source": str(inpx),
        "summary": {
            "road_links": len(links),
            "connectors": len(connectors),
            "all_link_objects": len(all_links),
            "by_type": dict(counter),
            "vehicle_inputs": len(vehicle_inputs),
            "data_collection_points": len(data_points),
            "queue_counters": len(queue_counters),
            "route_decisions_static": len(route_decisions),
            "vehicle_routes_static": len(routes),
            "signal_controllers": len(signal_controllers),
            "signal_groups": len(signal_groups),
            "signal_heads": len(signal_heads),
            "detectors": len(detectors),
            "desired_speed_decisions": len(desired_speed_decisions),
            "nodes": len(nodes),
        },
        "links": links,
        "connectors": connectors,
        "vehicle_inputs": vehicle_inputs,
        "data_collection_points": data_points,
        "queue_counters": queue_counters,
        "route_decisions_static": route_decisions,
        "vehicle_routes_static": routes,
        "signal_controllers": signal_controllers,
        "signal_groups": signal_groups,
        "signal_heads": signal_heads,
        "detectors": detectors,
        "desired_speed_decisions": desired_speed_decisions,
        "nodes": nodes,
    }

    mapping = group_links(links, connectors)
    gaps = {
        "route_objects": {
            "status": "missing_or_not_configured" if not route_decisions else "present",
            "route_decisions_static": len(route_decisions),
            "vehicle_routes_static": len(routes),
            "needed_for_smoke_test": [
                "boundary input to plausible exits",
                "freeway through EB/WB routes",
                "urban cross-network routes",
                "ramp on/off routes at D/F trumpets",
            ],
        },
        "signal_objects": {
            "status": "missing_or_not_configured" if not signal_controllers or not signal_heads else "present",
            "signal_controllers": len(signal_controllers),
            "signal_heads": len(signal_heads),
            "needed_for_baseline": [
                "fixed-time signal controllers at A/B/C/D/F or COM-only virtual signal control",
                "signal heads on controlled approaches",
                "fallback all-green/no-signal smoke mode if route connectivity is the first target",
            ],
        },
        "detector_objects": {
            "status": "optional_for_phase_1_global_state" if not detectors else "present_for_detector_phase",
            "data_collection_points": len(data_points),
            "queue_counters": len(queue_counters),
            "detectors": len(detectors),
            "phase_1": "not required; use global vehicle/link state",
            "phase_2_needed": [
                "approach queue/detection near A/B/C/D/F",
                "ramp queues and merge detectors at D/F",
                "freeway mainline density/flow detectors",
            ],
        },
        "global_state_controller": {
            "recommended_first": True,
            "control_interval_sec": 5,
            "state_groups": mapping["global_state_groups"],
        },
    }

    (out_dir / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "network_mapping.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "missing_objects.json").write_text(
        json.dumps(gaps, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    write_csv(
        out_dir / "links.csv",
        links,
        ["no", "name", "type", "lane_count", "lane_widths", "length_m", "start_xy", "end_xy"],
    )
    write_csv(
        out_dir / "connectors.csv",
        connectors,
        ["no", "name", "type", "lane_count", "length_m", "from", "to", "start_xy", "end_xy"],
    )

    print(json.dumps(inventory["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
