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
    text = "".join(ch for ch in str(value) if ch.isdigit() or ch == "-")
    return int(text) if text else None


def clean_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    return float(text) if text else None


def first_int(value: str | None) -> int | None:
    match = re.search(r"-?\d+", str(value or ""))
    return int(match.group(0)) if match else None


def parse_int_csv(value: str) -> list[int]:
    out: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if part:
            out.append(int(part))
    return out


def link_points(link: ET.Element) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for pt in link.findall("./geometry/linkPolyPts/linkPolyPoint"):
        x = clean_float(pt.get("x"))
        y = clean_float(pt.get("y"))
        if x is not None and y is not None:
            points.append((x, y))
    return points


def polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(x2 - x1, y2 - y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:])
    )


def point_at_pos(points: list[tuple[float, float]], pos: float | None) -> tuple[float, float] | None:
    if not points:
        return None
    if pos is None or len(points) == 1:
        return points[0]
    remaining = max(0.0, float(pos))
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        seg_len = math.hypot(x2 - x1, y2 - y1)
        if seg_len <= 1.0e-9:
            continue
        if remaining <= seg_len:
            frac = remaining / seg_len
            return (x1 + frac * (x2 - x1), y1 + frac * (y2 - y1))
        remaining -= seg_len
    return points[-1]


def direction_label(dx: float, dy: float) -> str:
    adx = abs(dx)
    ady = abs(dy)
    if ady > 1.3 * adx:
        return "NS"
    if adx > 1.3 * ady:
        return "EW"
    return "DIAG"


def as_rounded_xy(point: tuple[float, float] | None) -> list[float] | None:
    if point is None:
        return None
    return [round(point[0], 3), round(point[1], 3)]


def parse_link_rows(root: ET.Element) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_no: dict[int, dict[str, Any]] = {}
    road_links: list[dict[str, Any]] = []
    connectors: list[dict[str, Any]] = []
    for link in root.iter("link"):
        no = clean_int(link.get("no"))
        if no is None:
            continue
        points = link_points(link)
        length = polyline_length(points)
        from_ep = link.find("./fromLinkEndPt")
        to_ep = link.find("./toLinkEndPt")
        is_connector = from_ep is not None or to_ep is not None
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            start = points[0]
            end = points[-1]
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            centroid = (sum(xs) / len(xs), sum(ys) / len(ys))
        else:
            xs = ys = []
            start = end = centroid = None
            dx = dy = 0.0
        row: dict[str, Any] = {
            "no": no,
            "name": link.get("name", ""),
            "is_connector": is_connector,
            "lane_count": len(link.findall("./lanes/lane")),
            "length_m": round(length, 3),
            "start_xy": as_rounded_xy(start),
            "end_xy": as_rounded_xy(end),
            "centroid_xy": as_rounded_xy(centroid),
            "min_x": round(min(xs), 3) if xs else None,
            "max_x": round(max(xs), 3) if xs else None,
            "min_y": round(min(ys), 3) if ys else None,
            "max_y": round(max(ys), 3) if ys else None,
            "dx": round(dx, 3),
            "dy": round(dy, 3),
            "orientation": direction_label(dx, dy),
        }
        if is_connector:
            row["from_link"] = first_int(from_ep.get("lane") if from_ep is not None else None)
            row["from_pos"] = clean_float(from_ep.get("pos") if from_ep is not None else None)
            row["to_link"] = first_int(to_ep.get("lane") if to_ep is not None else None)
            row["to_pos"] = clean_float(to_ep.get("pos") if to_ep is not None else None)
            connectors.append(row)
        else:
            road_links.append(row)
        by_no[no] = row
    return by_no, road_links, connectors


def freeway_candidates(road_links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in road_links
        if row["orientation"] == "NS" and float(row["length_m"]) >= 1000.0
    ]
    return sorted(candidates, key=lambda r: (float(r["min_x"] or 0.0), -float(r["length_m"])))[:10]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def volume_rows(vi: ET.Element) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for child in vi.findall("./timeIntVehVols/timeIntervalVehVolume"):
        rows.append(dict(child.attrib))
    return rows


def max_volume(volumes: list[dict[str, Any]]) -> float:
    vals: list[float] = []
    for row in volumes:
        value = clean_float(row.get("volume"))
        if value is not None:
            vals.append(value)
    return max(vals) if vals else 0.0


def signal_group_rows(sc: ET.Element) -> list[dict[str, Any]]:
    return [dict(sg.attrib) for sg in sc.findall("./sgs/signalGroup")]


def build_real_world_inventory(
    root: ET.Element,
    source: Path,
    freeway_links: set[int],
    freeway_input_min_vph: float,
) -> dict[str, Any]:
    links_by_no, road_links, connectors = parse_link_rows(root)
    all_link_ids = sorted(links_by_no)

    touching_freeway_road_links: set[int] = set()
    touching_freeway_connectors: set[int] = set()
    for connector in connectors:
        from_link = connector.get("from_link")
        to_link = connector.get("to_link")
        if from_link in freeway_links or to_link in freeway_links:
            touching_freeway_connectors.add(int(connector["no"]))
            if isinstance(from_link, int) and from_link not in freeway_links:
                touching_freeway_road_links.add(from_link)
            if isinstance(to_link, int) and to_link not in freeway_links:
                touching_freeway_road_links.add(to_link)

    vehicle_inputs: list[dict[str, Any]] = []
    freeway_input_links: set[int] = set()
    for vi in root.iter("vehicleInput"):
        no = clean_int(vi.get("no"))
        link_no = first_int(vi.get("link"))
        vols = volume_rows(vi)
        peak = max_volume(vols)
        role = "urban_input"
        if link_no in freeway_links:
            role = "freeway_mainline_input"
            if link_no is not None:
                freeway_input_links.add(link_no)
        elif link_no in touching_freeway_road_links and peak >= freeway_input_min_vph:
            role = "freeway_feeder_input_candidate"
            if link_no is not None:
                freeway_input_links.add(link_no)
        vehicle_inputs.append(
            {
                "no": no,
                "name": vi.get("name", ""),
                "link": link_no,
                "role": role,
                "first_volume_vph": clean_float(vols[0].get("volume")) if vols else None,
                "peak_volume_vph": round(peak, 3),
                "time_interval_count": len(vols),
            }
        )

    des_speed_decisions: list[dict[str, Any]] = []
    for dsd in root.iter("desSpeedDecision"):
        link_no = first_int(dsd.get("lane"))
        role = "urban_or_local_speed_decision"
        if link_no in freeway_links:
            role = "freeway_mainline_speed_decision"
        elif link_no in freeway_input_links:
            role = "freeway_feeder_speed_decision"
        elif link_no in touching_freeway_road_links:
            role = "freeway_interface_speed_decision"
        des_speed_decisions.append(
            {
                "no": clean_int(dsd.get("no")),
                "link": link_no,
                "lane_ref": dsd.get("lane", ""),
                "pos": clean_float(dsd.get("pos")),
                "role": role,
            }
        )

    queue_counters: list[dict[str, Any]] = []
    for qc in root.iter("queueCounter"):
        link_no = first_int(qc.get("link"))
        role = "freeway_queue_counter" if link_no in freeway_links else "urban_queue_counter"
        queue_counters.append(
            {
                "no": clean_int(qc.get("no")),
                "name": qc.get("name", ""),
                "link": link_no,
                "pos": clean_float(qc.get("pos")),
                "role": role,
            }
        )

    data_collection_points: list[dict[str, Any]] = []
    for dcp in root.iter("dataCollectionPoint"):
        link_no = first_int(dcp.get("lane"))
        role = "freeway_data_collection_point" if link_no in freeway_links else "urban_data_collection_point"
        data_collection_points.append(
            {
                "no": clean_int(dcp.get("no")),
                "name": dcp.get("name", ""),
                "link": link_no,
                "lane_ref": dcp.get("lane", ""),
                "pos": clean_float(dcp.get("pos")),
                "role": role,
            }
        )

    signal_heads_by_sc: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for sh in root.iter("signalHead"):
        sg_ref = sh.get("sg", "")
        parts = sg_ref.split()
        sc_no = int(parts[0]) if parts and parts[0].lstrip("-").isdigit() else None
        link_no = first_int(sh.get("lane"))
        pos = clean_float(sh.get("pos"))
        point = None
        link_row = links_by_no.get(link_no or -1)
        if link_row:
            raw_points = []
            # Reconstruct only when needed; kept separate to avoid storing all polyline points in JSON.
            link_el = next((el for el in root.iter("link") if clean_int(el.get("no")) == link_no), None)
            raw_points = link_points(link_el) if link_el is not None else []
            point = point_at_pos(raw_points, pos)
        if sc_no is not None:
            signal_heads_by_sc[sc_no].append(
                {
                    "no": clean_int(sh.get("no")),
                    "sg": sh.get("sg", ""),
                    "link": link_no,
                    "lane_ref": sh.get("lane", ""),
                    "pos": pos,
                    "xy": as_rounded_xy(point),
                }
            )

    signal_controllers: list[dict[str, Any]] = []
    for sc in root.iter("signalController"):
        sc_no = clean_int(sc.get("no"))
        heads = signal_heads_by_sc.get(sc_no or -1, [])
        head_links = [int(h["link"]) for h in heads if isinstance(h.get("link"), int)]
        unique_head_links = sorted(set(head_links))
        xy = [h["xy"] for h in heads if h.get("xy")]
        centroid = None
        if xy:
            centroid = [
                round(sum(p[0] for p in xy) / len(xy), 3),
                round(sum(p[1] for p in xy) / len(xy), 3),
            ]
        head_counter = Counter(head_links)
        freeway_head_count = sum(head_counter[link_no] for link_no in freeway_links)
        interface_head_count = sum(head_counter[link_no] for link_no in touching_freeway_road_links)
        if freeway_head_count:
            role = "freeway_direct_signal_controller"
        elif interface_head_count:
            role = "urban_freeway_interface_signal_controller"
        else:
            role = "urban_signal_controller"
        groups = signal_group_rows(sc)
        signal_controllers.append(
            {
                "no": sc_no,
                "name": sc.get("name", ""),
                "active": sc.get("active", ""),
                "type": sc.get("type", ""),
                "supplyFile2": sc.get("supplyFile2", ""),
                "role": role,
                "signal_group_count": len(groups),
                "signal_group_names": ",".join(str(g.get("name", "")) for g in groups),
                "signal_head_count": len(heads),
                "unique_head_links": ",".join(str(v) for v in unique_head_links),
                "freeway_head_count": freeway_head_count,
                "interface_head_count": interface_head_count,
                "centroid_xy": centroid,
            }
        )

    route_decisions = [dict(el.attrib) for el in root.iter("vehicleRoutingDecisionStatic")]
    routes = [dict(el.attrib) for el in root.iter("vehicleRouteStatic")]

    for row in links_by_no.values():
        if row["no"] in freeway_links:
            role = "freeway_mainline"
        elif row["no"] in touching_freeway_connectors:
            role = "urban_freeway_interface_connector"
        elif row["no"] in touching_freeway_road_links:
            role = "urban_freeway_interface_road"
        else:
            role = "urban_road"
        row["role"] = role

    urban_state_links = [link_no for link_no in all_link_ids if link_no not in freeway_links]
    freeway_dsd = [
        int(row["no"])
        for row in des_speed_decisions
        if row["role"] in {"freeway_mainline_speed_decision", "freeway_feeder_speed_decision"}
        and row["no"] is not None
    ]
    freeway_mainline_dsd_by_link: dict[int, list[int]] = defaultdict(list)
    for row in des_speed_decisions:
        if row["role"] == "freeway_mainline_speed_decision" and row["no"] is not None:
            freeway_mainline_dsd_by_link[int(row["link"])].append(int(row["no"]))
    missing_mainline_dsd_links = [
        link_no for link_no in sorted(freeway_links) if not freeway_mainline_dsd_by_link.get(link_no)
    ]

    urban_signal_ids = [
        int(row["no"])
        for row in signal_controllers
        if row["no"] is not None and row["role"].startswith("urban")
    ]
    interface_signal_ids = [
        int(row["no"])
        for row in signal_controllers
        if row["no"] is not None and row["role"] == "urban_freeway_interface_signal_controller"
    ]

    player_definition = {
        "schema_version": 1,
        "source_network": str(source),
        "user_geometry_hint": "The leftmost long north-south corridor is freeway; the remaining network is urban road.",
        "freeway_mainline_links": sorted(freeway_links),
        "urban_state_links": urban_state_links,
        "freeway_input_links": sorted(freeway_input_links),
        "freeway_touching_road_links": sorted(touching_freeway_road_links),
        "freeway_touching_connectors": sorted(touching_freeway_connectors),
        "global_state_groups": {
            "freeway_links": sorted(freeway_links),
            "urban_links": [],
            "ramp_links": [],
            "boundary_links": [],
            "classify_unmatched_as_urban": True,
        },
        "players": [
            {
                "id": "leader_network_manager",
                "kind": "leader",
                "state_scope": "all vehicles split into freeway_mainline versus urban_remainder",
                "objective": "minimize TTT/stopped vehicles while protecting both freeway and urban queues",
                "controlled_objects": [],
            },
            {
                "id": "freeway_follower_left_ns",
                "kind": "freeway_follower",
                "state_links": sorted(freeway_links),
                "demand_input_links": sorted(freeway_input_links),
                "current_des_speed_decisions": sorted(freeway_dsd),
                "current_signal_controllers": [],
                "missing_mainline_des_speed_links": missing_mainline_dsd_links,
                "note": "No signal heads are attached directly to the freeway mainline in the INPX.",
            },
            {
                "id": "urban_follower_all_signals",
                "kind": "urban_follower",
                "state_links": urban_state_links,
                "signal_controllers": sorted(urban_signal_ids),
                "freeway_interface_signal_controllers": sorted(interface_signal_ids),
                "note": "First real-world P-Stack pass should keep this as one urban follower, then split by corridor if authority is too coarse.",
            },
        ],
        "action_authority_risks": [
            "Freeway VSL coverage is asymmetric because existing mainline desired-speed decisions are present on link 26 but not link 2.",
            "All signal controllers are fixed-time VISSIG controllers; COM control must be proven before P-Stack can change phases/offsets.",
            "Real-world demand is already encoded in vehicle inputs, so synthetic uniform volume overrides should not be used.",
        ],
        "recommended_sequence": [
            "Run load/short-step smoke with original demand.",
            "Run no-control baseline with long warm-up and real-world state split.",
            "Audit freeway VSL authority on links 2 and 26; add missing link-2 VSL decisions only after load smoke is stable.",
            "Audit VISSIG signal-group COM control on a small freeway-interface controller subset.",
            "Only then rebuild the P-Stack adapter around these players.",
        ],
    }

    inventory = {
        "source": str(source),
        "network": dict(root.attrib),
        "summary": {
            "road_links": len(road_links),
            "connectors": len(connectors),
            "all_link_objects": len(all_link_ids),
            "vehicle_inputs": len(vehicle_inputs),
            "signal_controllers": len(signal_controllers),
            "signal_groups": sum(int(row["signal_group_count"]) for row in signal_controllers),
            "signal_heads": sum(int(row["signal_head_count"]) for row in signal_controllers),
            "desired_speed_decisions": len(des_speed_decisions),
            "queue_counters": len(queue_counters),
            "data_collection_points": len(data_collection_points),
            "route_decisions_static": len(route_decisions),
            "vehicle_routes_static": len(routes),
        },
        "freeway_candidates_by_geometry": freeway_candidates(road_links),
        "player_definition": player_definition,
        "links": sorted(links_by_no.values(), key=lambda r: int(r["no"])),
        "vehicle_inputs": vehicle_inputs,
        "des_speed_decisions": des_speed_decisions,
        "queue_counters": queue_counters,
        "data_collection_points": data_collection_points,
        "signal_controllers": signal_controllers,
        "route_decisions_static_count": len(route_decisions),
        "vehicle_routes_static_count": len(routes),
    }
    return inventory


def write_vbs_global_config(path: Path, player_definition: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    freeway_links = ",".join(str(v) for v in player_definition["global_state_groups"]["freeway_links"])
    freeway_input_links = ",".join(str(v) for v in player_definition["freeway_input_links"])
    text = "\n".join(
        [
            "' Auto-generated by scripts/inventory_real_world_modi.py.",
            "' Real-world state split: freeway is explicit; all unmatched links are urban.",
            f"FREEWAY_LINKS = \"{freeway_links}\"",
            "URBAN_LINKS = \"\"",
            "RAMP_LINKS = \"\"",
            "BOUNDARY_LINKS = \"\"",
            f"FREEWAY_INPUT_LINKS = \"{freeway_input_links}\"",
            "CLASSIFY_UNMATCHED_AS_URBAN = True",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def write_markdown_report(path: Path, inventory: dict[str, Any]) -> None:
    pd = inventory["player_definition"]
    summary = inventory["summary"]
    freeway_player = next(p for p in pd["players"] if p["id"] == "freeway_follower_left_ns")
    urban_player = next(p for p in pd["players"] if p["id"] == "urban_follower_all_signals")
    candidates = inventory["freeway_candidates_by_geometry"][:5]
    lines = [
        "# Real-world modi player definition",
        "",
        f"Source: `{inventory['source']}`",
        "",
        "## Object inventory",
        "",
        f"- Road links: {summary['road_links']}",
        f"- Connectors: {summary['connectors']}",
        f"- Signal controllers / groups / heads: {summary['signal_controllers']} / {summary['signal_groups']} / {summary['signal_heads']}",
        f"- Vehicle inputs: {summary['vehicle_inputs']}",
        f"- Desired-speed decisions: {summary['desired_speed_decisions']}",
        f"- Queue counters / data collection points: {summary['queue_counters']} / {summary['data_collection_points']}",
        "",
        "## Freeway geometry",
        "",
        f"- Freeway mainline links: `{pd['freeway_mainline_links']}`",
        f"- Freeway demand/input links: `{pd['freeway_input_links']}`",
        f"- Freeway-touching road links: `{pd['freeway_touching_road_links']}`",
        "",
        "Top north-south long-link candidates:",
        "",
    ]
    for row in candidates:
        lines.append(
            f"- link {row['no']}: length {row['length_m']} m, lanes {row['lane_count']}, "
            f"x=[{row['min_x']}, {row['max_x']}], y=[{row['min_y']}, {row['max_y']}]"
        )
    lines.extend(
        [
            "",
            "## Player draft",
            "",
            f"- Leader: whole-network TTT/stopped objective, with freeway/urban split from player definition.",
            f"- Freeway follower: state links `{freeway_player['state_links']}`, demand inputs `{freeway_player['demand_input_links']}`, current DSD actuators `{freeway_player['current_des_speed_decisions']}`.",
            f"- Urban follower: all non-freeway links as urban state; {len(urban_player['signal_controllers'])} signal controllers, interface subset `{urban_player['freeway_interface_signal_controllers']}`.",
            "",
            "## Immediate risks",
            "",
        ]
    )
    for risk in pd["action_authority_risks"]:
        lines.append(f"- {risk}")
    lines.extend(["", "## Recommended sequence", ""])
    for idx, step in enumerate(pd["recommended_sequence"], start=1):
        lines.append(f"{idx}. {step}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inpx", default="network/real_world_gaepo_modi/modi.inpx")
    parser.add_argument("--out-dir", default="evaluation/real_world_modi_inventory")
    parser.add_argument("--report", default="outputs/real_world_modi_player_definition_20260718.md")
    parser.add_argument("--json-report", default="outputs/real_world_modi_player_definition_20260718.json")
    parser.add_argument("--vbs-config", default="evaluation/generated/real_world_modi_global_state_config.vbs")
    parser.add_argument("--freeway-mainline-links", default="2,26")
    parser.add_argument("--freeway-input-min-vph", type=float, default=2500.0)
    args = parser.parse_args()

    source = Path(args.inpx)
    root = ET.parse(source).getroot()
    freeway_links = set(parse_int_csv(args.freeway_mainline_links))
    inventory = build_real_world_inventory(root, source, freeway_links, args.freeway_input_min_vph)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "player_definition.json").write_text(
        json.dumps(inventory["player_definition"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    Path(args.json_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_report).write_text(
        json.dumps(inventory["player_definition"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown_report(Path(args.report), inventory)
    write_vbs_global_config(Path(args.vbs_config), inventory["player_definition"])

    write_csv(
        out_dir / "link_roles.csv",
        inventory["links"],
        [
            "no",
            "role",
            "is_connector",
            "lane_count",
            "length_m",
            "orientation",
            "start_xy",
            "end_xy",
            "centroid_xy",
            "from_link",
            "to_link",
            "name",
        ],
    )
    write_csv(
        out_dir / "signal_controller_roles.csv",
        inventory["signal_controllers"],
        [
            "no",
            "role",
            "active",
            "type",
            "signal_group_count",
            "signal_head_count",
            "freeway_head_count",
            "interface_head_count",
            "unique_head_links",
            "centroid_xy",
            "supplyFile2",
            "signal_group_names",
            "name",
        ],
    )
    write_csv(
        out_dir / "vehicle_input_roles.csv",
        inventory["vehicle_inputs"],
        ["no", "role", "link", "first_volume_vph", "peak_volume_vph", "time_interval_count", "name"],
    )
    write_csv(
        out_dir / "des_speed_decision_roles.csv",
        inventory["des_speed_decisions"],
        ["no", "role", "link", "lane_ref", "pos"],
    )

    print(json.dumps(inventory["summary"], ensure_ascii=False, indent=2))
    print("PLAYER_DEFINITION=" + str(out_dir / "player_definition.json"))
    print("REPORT=" + str(args.report))
    print("VBS_CONFIG=" + str(args.vbs_config))


if __name__ == "__main__":
    main()
