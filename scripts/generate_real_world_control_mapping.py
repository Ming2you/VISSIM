from __future__ import annotations

import argparse
import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]

FREEWAY_MODEL_LINKS = {
    "FW_E": 2,
    "FW_W": 26,
}

RAMP_METER_ORDER = [
    "RM_C10480",
    "RM_C10482",
    "RM_C10646",
    "RM_C10644",
    "RM_C10639",
    "RM_C10681",
    "RM_C10490",
    "RM_C10484",
]

OFF_RAMP_GROUPS = {
    "OR_D_W": [10479, 10491],
    "OR_F_W": [10638, 10645],
    "OR_F_E": [10643, 10682],
    "OR_D_E": [10481, 10483],
}

OFF_RAMP_MOVEMENTS = {
    "OR_D_W": ["D_offW_to_N", "D_offW_to_E", "D_offW_to_W"],
    "OR_D_E": ["D_offE_to_N", "D_offE_to_E", "D_offE_to_W"],
    "OR_F_W": ["F_offW_to_N", "F_offW_to_E", "F_offW_to_W"],
    "OR_F_E": ["F_offE_to_N", "F_offE_to_E", "F_offE_to_W"],
}

MODEL_RAMP_TO_URBAN_SIGNAL = {
    "R_D_W": "D",
    "R_D_E": "D",
    "R_F_W": "F",
    "R_F_E": "F",
}

REAL_WORLD_INTERFACE_SIGNALS = [
    {
        "id": "D",
        "sc_no": 1,
        "coverage": ["D", "F"],
        "role": "freeway_interface_signal_controller",
        "phase_map": {
            "major_axis": "east_west",
            "minor_axis": "north_south",
            "major_sg_name_prefixes": ["EB", "WB"],
            "minor_sg_name_prefixes": ["NB", "SB"],
        },
        "source": "evaluation/real_world_modi_inventory/signal_controller_roles.csv",
        "note": "SC 1 is the only controller inventoried with freeway-interface signal heads; real-world runner applies major/minor timing to all SGs by EB/WB vs NB/SB SG names.",
    }
]


def freeway_agent_id(model_link: str, segment_index: int) -> str:
    suffix = model_link.split("_")[-1] if "_" in model_link else model_link
    return f"F_{suffix}{int(segment_index)}"


def urban_agent_id(signal: str) -> str:
    return f"U_{signal}"


def clean_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = "".join(ch for ch in str(value) if ch.isdigit() or ch == "-")
    return int(text) if text else None


def clean_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return float(default)


def first_int(value: str | None) -> int | None:
    match = re.search(r"-?\d+", str(value or ""))
    return int(match.group(0)) if match else None


def lane_no_from_ref(value: str | None) -> int | None:
    parts = re.findall(r"-?\d+", str(value or ""))
    if len(parts) >= 2:
        return int(parts[1])
    return None


def link_points(link: ET.Element) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for pt in link.findall("./geometry/linkPolyPts/linkPolyPoint"):
        x = clean_float(pt.get("x"), math.nan)
        y = clean_float(pt.get("y"), math.nan)
        if not math.isnan(x) and not math.isnan(y):
            points.append((x, y))
    return points


def polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(x2 - x1, y2 - y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:])
    )


def parse_network(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    links: dict[int, dict[str, Any]] = {}
    connectors: dict[int, dict[str, Any]] = {}
    dsds: list[dict[str, Any]] = []

    for link in root.iter("link"):
        no = clean_int(link.get("no"))
        if no is None:
            continue
        points = link_points(link)
        from_ep = link.find("./fromLinkEndPt")
        to_ep = link.find("./toLinkEndPt")
        row = {
            "no": no,
            "name": link.get("name", ""),
            "length_m": float(polyline_length(points)),
            "lane_count": len(link.findall("./lanes/lane")),
            "is_connector": from_ep is not None or to_ep is not None,
        }
        if row["is_connector"]:
            row.update(
                {
                    "from_link": first_int(from_ep.get("lane") if from_ep is not None else None),
                    "from_pos": clean_float(from_ep.get("pos") if from_ep is not None else None),
                    "to_link": first_int(to_ep.get("lane") if to_ep is not None else None),
                    "to_pos": clean_float(to_ep.get("pos") if to_ep is not None else None),
                }
            )
            connectors[no] = row
        links[no] = row

    for dsd in root.iter("desSpeedDecision"):
        lane_ref = dsd.get("lane", "")
        dsds.append(
            {
                "no": clean_int(dsd.get("no")),
                "name": dsd.get("name", ""),
                "link": first_int(lane_ref),
                "lane": lane_no_from_ref(lane_ref),
                "pos_m": clean_float(dsd.get("pos")),
            }
        )

    return {"links": links, "connectors": connectors, "dsds": dsds}


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def segment_index(pos_m: float, bounds: list[float]) -> int:
    if len(bounds) < 2:
        return 0
    for idx, upper in enumerate(bounds[1:]):
        if float(pos_m) < float(upper):
            return idx
    return len(bounds) - 2


def round3(value: float) -> float:
    return round(float(value), 3)


def build_segments(
    manifest_rows: list[dict[str, str]],
    network: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[float]], dict[str, list[float]]]:
    links = network["links"]
    rows = [r for r in manifest_rows if r.get("category") == "segment_start_vsl"]
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("segment_id", ""))].append(row)

    segments: list[dict[str, Any]] = []
    bounds_by_model: dict[str, list[float]] = {}
    lengths_km_by_model: dict[str, list[float]] = {}
    installed_dsd_nos: set[int] = set()

    def segment_sort_key(item: tuple[str, list[dict[str, str]]]) -> tuple[str, int]:
        first = item[1][0]
        return str(first.get("model_link", "")), int(clean_float(first.get("model_segment_index"), 0.0))

    for segment_id, seg_rows in sorted(grouped.items(), key=segment_sort_key):
        first = seg_rows[0]
        model_link = str(first.get("model_link", ""))
        model_idx = int(clean_float(first.get("model_segment_index"), 0.0))
        physical_link = int(clean_float(first.get("link"), 0.0))
        start_m = clean_float(first.get("segment_start_m"))
        end_m = clean_float(first.get("segment_end_m"))
        bounds = bounds_by_model.setdefault(model_link, [])
        if not bounds:
            bounds.append(start_m)
        bounds.append(end_m)
        lengths_km_by_model.setdefault(model_link, []).append(max(1.0e-6, (end_m - start_m) / 1000.0))
        dsd_by_lane: dict[str, dict[str, Any]] = {}
        dsds: list[dict[str, Any]] = []
        for row in sorted(seg_rows, key=lambda r: int(clean_float(r.get("lane"), 0.0))):
            dsd_no = int(clean_float(row.get("no"), 0.0))
            lane = int(clean_float(row.get("lane"), 0.0))
            installed_dsd_nos.add(dsd_no)
            dsd = {
                "dsd_no": dsd_no,
                "lane": lane,
                "pos_m": clean_float(row.get("pos")),
                "source": "installed_real_world_segment_start",
                "name": row.get("name", ""),
            }
            dsd_by_lane[str(lane)] = dsd
            dsds.append(dict(dsd))
        link_info = links.get(physical_link, {})
        segments.append(
            {
                "segment_id": segment_id,
                "model_link": model_link,
                "model_segment_index": model_idx,
                "link": physical_link,
                "direction": first.get("direction", ""),
                "segment_start_m": round3(start_m),
                "segment_end_m": round3(end_m),
                "length_km": round((end_m - start_m) / 1000.0, 6),
                "lanes": int(link_info.get("lane_count", 4) or 4),
                "dsd_by_lane": dsd_by_lane,
                "extra_dsd_controls": [],
                "dsds": dsds,
                "default_speed_kph": clean_float(first.get("default_speed_kph"), 120.0),
            }
        )

    segment_lookup = {(s["model_link"], s["model_segment_index"]): s for s in segments}
    link_to_model = {physical: model for model, physical in FREEWAY_MODEL_LINKS.items()}
    for dsd in network["dsds"]:
        dsd_no = dsd.get("no")
        physical_link = dsd.get("link")
        if not isinstance(dsd_no, int) or dsd_no in installed_dsd_nos:
            continue
        if physical_link not in link_to_model:
            continue
        model_link = link_to_model[physical_link]
        idx = segment_index(float(dsd.get("pos_m", 0.0)), bounds_by_model.get(model_link, []))
        segment = segment_lookup.get((model_link, idx))
        if not segment:
            continue
        extra = {
            "dsd_no": dsd_no,
            "lane": dsd.get("lane"),
            "pos_m": round3(float(dsd.get("pos_m", 0.0))),
            "source": "existing_freeway_mainline_dsd",
            "name": dsd.get("name", ""),
        }
        segment["extra_dsd_controls"].append(extra)
        segment["dsds"].append(dict(extra))

    return segments, bounds_by_model, lengths_km_by_model


def build_ramp_meters(
    manifest_rows: list[dict[str, str]],
    network: dict[str, Any],
    bounds_by_model: dict[str, list[float]],
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int]]:
    connectors = network["connectors"]
    rows_by_id = {
        str(row.get("control_id")): row
        for row in manifest_rows
        if row.get("object_type") == "rampMeter"
    }
    meters: list[dict[str, Any]] = []
    for meter_id in RAMP_METER_ORDER:
        row = rows_by_id[meter_id]
        connector_no = int(clean_float(row.get("connector"), 0.0))
        connector = connectors.get(connector_no, {})
        to_link = int(clean_float(row.get("to_link"), connector.get("to_link", 0)))
        model_link = "FW_E" if to_link == FREEWAY_MODEL_LINKS["FW_E"] else "FW_W"
        to_pos = clean_float(row.get("to_pos"), connector.get("to_pos", 0.0))
        model_key = str(row.get("model_ramp_key", ""))
        meters.append(
            {
                "id": meter_id,
                "connector": connector_no,
                "from_link": int(clean_float(row.get("from_link"), connector.get("from_link", 0))),
                "from_pos_m": round3(clean_float(row.get("from_pos"), connector.get("from_pos", 0.0))),
                "to_link": to_link,
                "to_pos_m": round3(to_pos),
                "to_model_link": model_link,
                "to_model_segment_index": segment_index(to_pos, bounds_by_model.get(model_link, [])),
                "sc_no": int(clean_float(row.get("sc_no"), 0.0)),
                "sg_no": int(clean_float(row.get("sg_no"), 1.0)),
                "default_green_sec": clean_float(row.get("default_green_sec"), 10.0),
                "cycle_sec": 10.0,
                "capacity_vph": clean_float(row.get("capacity_vph"), 900.0),
                "model_ramp_key": model_key,
                "purpose": row.get("purpose", ""),
            }
        )

    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for meter in meters:
        by_key[str(meter["model_ramp_key"])].append(meter)

    ramp_merge: dict[str, int] = {}
    for key, group in by_key.items():
        model_link = str(group[0]["to_model_link"])
        avg_pos = sum(float(m["to_pos_m"]) for m in group) / len(group)
        ramp_merge[key] = segment_index(avg_pos, bounds_by_model.get(model_link, []))

    off_ramp_index: dict[str, int] = {}
    for key, connector_nos in OFF_RAMP_GROUPS.items():
        positions: list[float] = []
        model_link = ""
        for connector_no in connector_nos:
            connector = connectors.get(connector_no)
            if not connector:
                continue
            from_link = int(connector.get("from_link", 0) or 0)
            if from_link in FREEWAY_MODEL_LINKS.values():
                model_link = "FW_E" if from_link == FREEWAY_MODEL_LINKS["FW_E"] else "FW_W"
                positions.append(float(connector.get("from_pos", 0.0)))
        if positions and model_link:
            off_ramp_index[key] = segment_index(sum(positions) / len(positions), bounds_by_model.get(model_link, []))

    return meters, ramp_merge, off_ramp_index


def build_detector_mapping(
    network: dict[str, Any],
    meters: list[dict[str, Any]],
    ramp_merge_index: dict[str, int],
    off_ramp_index: dict[str, int],
) -> dict[str, Any]:
    connectors = network["connectors"]
    link_to_origins: dict[str, list[str]] = {}
    link_to_movements: dict[str, list[dict[str, Any]]] = {}
    ramp_link_to_queues: dict[str, list[str]] = {}
    off_ramp_details: dict[str, list[dict[str, Any]]] = {}

    for off_ramp, connector_nos in OFF_RAMP_GROUPS.items():
        entries: list[dict[str, Any]] = []
        signal = off_ramp.split("_")[1] if "_" in off_ramp else ""
        movements = OFF_RAMP_MOVEMENTS.get(off_ramp, [])
        for connector_no in connector_nos:
            connector = connectors.get(connector_no)
            if not connector:
                continue
            link_key = str(connector_no)
            link_to_origins[link_key] = [off_ramp]
            link_to_movements[link_key] = [
                {
                    "movement": movement,
                    "weight": 1.0,
                    "signal": signal,
                    "phase": f"{signal}_p1" if signal else "",
                    "kind": "off_ramp",
                    "origin": off_ramp,
                }
                for movement in movements
            ]
            entries.append(
                {
                    "connector": connector_no,
                    "from_link": int(connector.get("from_link", 0) or 0),
                    "from_pos_m": round3(float(connector.get("from_pos", 0.0) or 0.0)),
                    "to_link": int(connector.get("to_link", 0) or 0),
                    "to_pos_m": round3(float(connector.get("to_pos", 0.0) or 0.0)),
                    "lanes": int(connector.get("lane_count", 0) or 0),
                }
            )
        off_ramp_details[off_ramp] = entries

    for meter in meters:
        ramp_link_to_queues[str(meter["connector"])] = [str(meter["model_ramp_key"])]

    agents: dict[str, dict[str, Any]] = {}
    for signal in ["A", "B", "C", "D", "F"]:
        off_ramps = sorted(
            off_ramp
            for off_ramp in OFF_RAMP_GROUPS
            if off_ramp.startswith(f"OR_{signal}_")
        )
        ramps = sorted(
            ramp
            for ramp, ramp_signal in MODEL_RAMP_TO_URBAN_SIGNAL.items()
            if ramp_signal == signal
        )
        visible_links = sorted(
            {
                str(connector)
                for off_ramp in off_ramps
                for connector in OFF_RAMP_GROUPS.get(off_ramp, [])
            }
            | {
                str(meter["connector"])
                for meter in meters
                if str(meter["model_ramp_key"]) in ramps
            },
            key=lambda value: int(value),
        )
        visible_movements = sorted(
            movement
            for off_ramp in off_ramps
            for movement in OFF_RAMP_MOVEMENTS.get(off_ramp, [])
        )
        agents[urban_agent_id(signal)] = {
            "kind": "urban",
            "signal": signal,
            "visible_links": visible_links,
            "visible_movements": visible_movements,
            "visible_ramps": ramps,
            "visible_off_ramps": off_ramps,
        }

    off_ramp_model_link = {
        off_ramp: (
            "FW_E"
            if any(
                int(connectors.get(connector_no, {}).get("from_link", 0) or 0) == FREEWAY_MODEL_LINKS["FW_E"]
                for connector_no in connector_nos
            )
            else "FW_W"
        )
        for off_ramp, connector_nos in OFF_RAMP_GROUPS.items()
    }
    for model_link, physical_link in FREEWAY_MODEL_LINKS.items():
        for segment_index in range(8):
            visible_ramps = sorted(
                ramp
                for ramp, idx in ramp_merge_index.items()
                if int(idx) == segment_index
                and any(
                    str(meter["model_ramp_key"]) == ramp
                    and str(meter["to_model_link"]) == model_link
                    for meter in meters
                )
            )
            visible_off_ramps = sorted(
                off_ramp
                for off_ramp, idx in off_ramp_index.items()
                if int(idx) == segment_index
                and off_ramp_model_link.get(off_ramp) == model_link
            )
            agents[freeway_agent_id(model_link, segment_index)] = {
                "kind": "freeway",
                "model_link": model_link,
                "segment_index": segment_index,
                "visible_links": [str(physical_link)],
                "visible_movements": [],
                "visible_ramps": visible_ramps,
                "visible_off_ramps": visible_off_ramps,
            }

    observable_links = sorted(
        {
            *(int(link) for link in link_to_origins),
            *(int(link) for link in ramp_link_to_queues),
            *FREEWAY_MODEL_LINKS.values(),
        }
    )
    return {
        "schema_version": 1,
        "mapping_version": "real_world_modi_connector_local_v1_20260720",
        "description": (
            "Real-world Gaepo modi connector-local observation mapping. "
            "Off-ramp connector counts feed OR_* storage/movement queues; "
            "ramp-meter connector counts feed R_* queues."
        ),
        "observable_links": observable_links,
        "link_to_origins": link_to_origins,
        "link_to_movements": link_to_movements,
        "ramp_link_to_queues": ramp_link_to_queues,
        "boundary_link_to_queue": {},
        "freeway_link_to_model_link": {
            str(physical): model for model, physical in FREEWAY_MODEL_LINKS.items()
        },
        "off_ramp_connectors": off_ramp_details,
        "agents": agents,
        "guardrails": {
            "leader_visibility": "global_state_allowed",
            "follower_visibility": "real_world_connector_local_links_only",
            "adapter_global_fallback_allowed_only_when_local_observation_absent": True,
            "vissim_internal_scan_is_masked_before_controller": True,
            "urban_signal_actuation": "freeway_interface_sc1_enabled",
        },
    }


def write_vbs_config(
    path: Path,
    segments: list[dict[str, Any]],
    bounds_by_model: dict[str, list[float]],
    meters: list[dict[str, Any]],
    detector_mapping_path: Path,
) -> None:
    links_by_model = {model: physical for model, physical in FREEWAY_MODEL_LINKS.items()}
    lanes_by_model = {
        str(segment["model_link"]): int(segment.get("lanes", 4))
        for segment in segments
    }
    path.parent.mkdir(parents=True, exist_ok=True)

    def csv_nums(values: list[float]) -> str:
        return ",".join(f"{float(v):.6f}" for v in values)

    lines = [
        "' Generated by scripts/generate_real_world_control_mapping.py",
        "RW_SCHEMA_VERSION = 1",
        'RW_FREEWAY_LINKS = "2,26"',
        'RW_FREEWAY_INPUT_LINKS = "26,74"',
        "RW_CLASSIFY_UNMATCHED_AS_URBAN = True",
    ]
    for model in ("FW_E", "FW_W"):
        bounds = bounds_by_model[model]
        lengths = [max(1.0e-6, (bounds[i + 1] - bounds[i]) / 1000.0) for i in range(len(bounds) - 1)]
        lines.extend(
            [
                f"RW_{model}_LINK = {links_by_model[model]}",
                f"RW_{model}_LENGTH_M = {bounds[-1]:.6f}",
                f"RW_{model}_LANES = {int(lanes_by_model.get(model, 4))}",
                f'RW_{model}_SEG_BOUNDS = "{csv_nums(bounds)}"',
                f'RW_{model}_SEG_LENGTHS_KM = "{csv_nums(lengths)}"',
            ]
        )
    lines.extend(
        [
            'RW_RAMP_METER_IDS = "' + ",".join(m["id"] for m in meters) + '"',
            'RW_RAMP_METER_SCS = "' + ",".join(str(m["sc_no"]) for m in meters) + '"',
            'RW_RAMP_METER_CONNECTORS = "' + ",".join(str(m["connector"]) for m in meters) + '"',
            'RW_RAMP_METER_MODEL_KEYS = "' + ",".join(str(m["model_ramp_key"]) for m in meters) + '"',
            'RW_SIGNAL_SCS = "'
            + ",".join(str(row["sc_no"]) for row in REAL_WORLD_INTERFACE_SIGNALS)
            + '"',
            'RW_LOCAL_OBSERVABLE_LINKS = "'
            + ",".join(
                str(v)
                for v in sorted(
                    {
                        *FREEWAY_MODEL_LINKS.values(),
                        *(int(m["connector"]) for m in meters),
                        *(
                            int(connector)
                            for connectors in OFF_RAMP_GROUPS.values()
                            for connector in connectors
                        ),
                    }
                )
            )
            + '"',
            'RW_DETECTOR_MAPPING_PATH = "' + str(detector_mapping_path).replace('"', '""') + '"',
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_payloads(
    network_path: Path,
    manifest_path: Path,
    mapping_path: Path,
    calibration_path: Path,
    tuning_path: Path,
    player_config_path: Path,
    vbs_config_path: Path,
    detector_mapping_path: Path,
) -> None:
    manifest_rows = read_manifest(manifest_path)
    network = parse_network(network_path)
    segments, bounds_by_model, lengths_km_by_model = build_segments(manifest_rows, network)
    meters, ramp_merge_index, off_ramp_index = build_ramp_meters(manifest_rows, network, bounds_by_model)
    detector_mapping_payload = build_detector_mapping(network, meters, ramp_merge_index, off_ramp_index)

    meters_by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for meter in meters:
        meters_by_model[str(meter["model_ramp_key"])].append(meter)
    ramp_capacity = {
        key: round(sum(float(m["capacity_vph"]) for m in group), 3)
        for key, group in meters_by_model.items()
    }
    for key in ("R_D_W", "R_D_E", "R_F_W", "R_F_E"):
        ramp_capacity.setdefault(key, 1800.0)

    avg_segment_km = sum(sum(v) for v in lengths_km_by_model.values()) / max(
        1,
        sum(len(v) for v in lengths_km_by_model.values()),
    )

    mapping_payload = {
        "schema_version": 1,
        "created_at": "2026-07-19",
        "network": str(network_path),
        "manifest": str(manifest_path),
        "description": "Real-world Gaepo modi freeway control mapping: VSL on freeway links 2/26 and physical ramp meters on eight on-ramp connectors.",
        "freeway_model_links": {
            model: {
                "physical_link": physical,
                "length_m": round3(network["links"][physical]["length_m"]),
                "lanes": int(network["links"][physical]["lane_count"]),
                "segment_bounds_m": [round3(v) for v in bounds_by_model[model]],
                "segment_length_profile_km": [round(v, 6) for v in lengths_km_by_model[model]],
            }
            for model, physical in FREEWAY_MODEL_LINKS.items()
        },
        "segments": segments,
        "signals": [dict(row) for row in REAL_WORLD_INTERFACE_SIGNALS],
        "ramp_meters": meters,
        "ramp_meter_groups": {
            key: {
                "model_ramp_key": key,
                "physical_meter_ids": [m["id"] for m in group],
                "physical_connectors": [m["connector"] for m in group],
                "total_capacity_vph": round(sum(float(m["capacity_vph"]) for m in group), 3),
            }
            for key, group in sorted(meters_by_model.items())
        },
        "model_topology_overrides": {
            "ramp_merge_segment_index": ramp_merge_index,
            "off_ramp_segment_index": off_ramp_index,
            "ramp_capacity_veh_h": ramp_capacity,
            "freeway_lanes": 4,
            "freeway_segment_length_km": round(avg_segment_km, 6),
        },
        "excluded_freeway_touching_connectors": [
            {
                "connector": 10699,
                "from_link": 74,
                "to_link": 2,
                "reason": "Treated as freeway feeder/mainline entry, not isolated ramp metering authority.",
            }
        ],
    }

    calibration_payload = {
        "schema_version": 1,
        "created_at": "2026-07-19",
        "calibration_version": "real_world_modi_control_v0_20260719",
        "status": "geometry_and_control_authority_defined_uncalibrated_response",
        "source_network": str(network_path),
        "source_mapping": str(mapping_path),
        "physical_inventory": {
            "notes": [
                "Initial real-world geometry/control-authority profile for Gaepo modi.",
                "Response curves are engineering defaults; run dedicated VISSIM response calibration before treating them as fitted.",
                "Connector 10699 is excluded from ramp metering because it is a freeway feeder/mainline entry.",
            ],
            "freeway_segment_length_profile_km": {
                model: [round(v, 6) for v in values]
                for model, values in lengths_km_by_model.items()
            },
            "freeway_segment_bounds_m": {
                model: [round3(v) for v in values]
                for model, values in bounds_by_model.items()
            },
            "ramp_meter_connectors": meters,
        },
        "operational": {
            "network": {
                "v_free_kph": 100.0,
                "rho_crit_veh_km_lane": 24.0,
                "freeway_capacity_veh_h": 7600.0,
            },
            "ramp_metering": {
                "D_green_to_release_vph_initial_mpc": {"0": 0.0, "10": 1800.0},
                "F_green_to_release_vph_raw": {"0": 0.0, "10": 1800.0},
                "F_status": "real_world_metering_available",
            },
            "signal": {
                "recommended_initial_lost_time_sec": 6.0,
                "recommended_initial_saturation_flow_vph_approach": 1800.0,
            },
            "urban_mfd": {
                "N_P_crit_veh_initial": 600.0,
            },
        },
    }

    tuning_payload = {
        "name": "real_world_modi_pstack_adapter_v0_20260719",
        "description": "Initial real-world Gaepo modi P-Stack adapter config. It keeps original VISSIM demand, maps P-Stack FW_E/FW_W controls to physical links 2/26, and distributes each model ramp-meter rate across two physical on-ramp meters.",
        "mapping_json": str(mapping_path),
        "calibration_json": str(calibration_path),
        "detector_mapping_json": str(detector_mapping_path),
        "config_overrides": {
            "network": {
                "freeway_links": ["FW_W", "FW_E"],
                "freeway_segments_per_link": 8,
                "freeway_lanes": 4,
                "freeway_segment_length_km": round(avg_segment_km, 6),
                "ramp_merge_segment_index": ramp_merge_index,
                "off_ramp_segment_index": off_ramp_index,
                "ramp_capacity_veh_h": ramp_capacity,
            }
        },
        "actuation": {
            "allow_invalid_F_metering": True,
            "F_ramp_mode": "metered",
            "real_world_ramp_metering": {
                "enabled": True,
                "cycle_sec": 10.0,
                "min_green_sec": 0.0,
                "max_green_sec": 10.0,
                "per_meter_capacity_vph": 900.0,
                "distribute_model_rate_across_meters": True,
            },
        },
    }

    player_config_payload = {
        "schema_version": 1,
        "created_at": "2026-07-19",
        "network": str(network_path),
        "players": [
            {
                "id": "leader_network_manager",
                "kind": "leader",
                "state_scope": "whole network split into freeway links 2/26 and urban remainder",
                "controlled_followers": ["freeway_follower_real_world", "urban_follower_monitor"],
            },
            {
                "id": "freeway_follower_real_world",
                "kind": "freeway_follower",
                "model_links": ["FW_W", "FW_E"],
                "physical_links": [26, 2],
                "vsl_segments": [s["segment_id"] for s in segments],
                "ramp_meters": [m["id"] for m in meters],
                "excluded_connector_controls": [10699],
            },
            {
                "id": "urban_follower_monitor",
                "kind": "urban_follower",
                "state_scope": "all non-freeway links",
                "controlled_signal_controllers": [
                    int(row["sc_no"]) for row in REAL_WORLD_INTERFACE_SIGNALS
                ],
                "local_observation": str(detector_mapping_path),
                "note": "SC 1 is exposed as the D/F freeway-interface signal lever; D/F off-ramp and ramp connector counts are exposed through detector-local observation.",
            },
        ],
    }

    write_json(mapping_path, mapping_payload)
    write_json(detector_mapping_path, detector_mapping_payload)
    write_json(calibration_path, calibration_payload)
    write_json(tuning_path, tuning_payload)
    write_json(player_config_path, player_config_payload)
    write_vbs_config(vbs_config_path, segments, bounds_by_model, meters, detector_mapping_path)

    print(f"MAPPING={mapping_path}")
    print(f"DETECTOR_MAPPING={detector_mapping_path}")
    print(f"CALIBRATION={calibration_path}")
    print(f"TUNING={tuning_path}")
    print(f"PLAYER_CONFIG={player_config_path}")
    print(f"VBS_CONFIG={vbs_config_path}")
    print(f"SEGMENTS={len(segments)} RAMP_METERS={len(meters)}")


def workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--network",
        default="network/real_world_gaepo_modi/modi_eval_rw_control.inpx",
    )
    parser.add_argument(
        "--manifest",
        default="evaluation/real_world_modi_control/freeway_control_manifest.csv",
    )
    parser.add_argument(
        "--mapping-json",
        default="evaluation/real_world_modi_control/control_mapping.json",
    )
    parser.add_argument(
        "--calibration-json",
        default="evaluation/calibration/real_world_modi_control_v0_20260719.json",
    )
    parser.add_argument(
        "--tuning-json",
        default="evaluation/configs/real_world_modi_pstack_adapter_v0_20260719.json",
    )
    parser.add_argument(
        "--player-config-json",
        default="evaluation/real_world_modi_control/player_config.json",
    )
    parser.add_argument(
        "--detector-mapping-json",
        default="evaluation/real_world_modi_control/detector_local_mapping.json",
    )
    parser.add_argument(
        "--vbs-config",
        default="evaluation/generated/real_world_modi_control_config.vbs",
    )
    args = parser.parse_args()

    network = workspace_path(args.network)
    manifest = workspace_path(args.manifest)
    if not network.exists():
        raise FileNotFoundError(network)
    if not manifest.exists():
        raise FileNotFoundError(manifest)

    build_payloads(
        network,
        manifest,
        workspace_path(args.mapping_json),
        workspace_path(args.calibration_json),
        workspace_path(args.tuning_json),
        workspace_path(args.player_config_json),
        workspace_path(args.vbs_config),
        workspace_path(args.detector_mapping_json),
    )


if __name__ == "__main__":
    main()
