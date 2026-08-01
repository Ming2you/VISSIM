"""VISSIM INPX를 strict rollout plant의 canonical topology로 변환한다."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable
import xml.etree.ElementTree as ET


SCHEMA_VERSION = "vissim-strict-topology/v1"
COMPILER_VERSION = "phase0/1.0.0"
CANONICAL_JSON_VERSION = "canonical-json/v1"
DEFAULT_URBAN_DT_SEC = 1.0
DEFAULT_V_FREE_MPS = 50.0 / 3.6
DEFAULT_JAM_SPACING_M = 7.5
_POSITION_EPS = 1.0e-7
CONTROLLED_UF_TO_SC = (
    (1, "1004"),
    (2, "1005"),
    (3, "107"),
    (4, "108"),
    (5, "109"),
    (6, "1003"),
    (7, "105"),
    (8, "1"),
    (9, "11"),
    (10, "12"),
    (12, "1001"),
    (13, "1002"),
    (14, "101"),
    (15, "5"),
    (16, "6"),
)
CONTROLLED_MAIN_SG_NOS = frozenset(range(1, 9))
DEFAULT_INFLUENCE_HOPS = 1


def _float_text(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("canonical-json/v1 rejects NaN and Infinity")
    if value == 0.0:
        return "0.0"
    text = repr(value).lower()
    if "e" not in text:
        return text
    mantissa, exponent = text.split("e", 1)
    sign = ""
    if exponent.startswith(("+", "-")):
        sign = "-" if exponent[0] == "-" else ""
        exponent = exponent[1:]
    exponent = exponent.lstrip("0") or "0"
    return f"{mantissa}e{sign}{exponent}"


def canonical_json_text(value: Any) -> str:
    """`canonical-json/v1` 규칙으로 JSON 문자열을 만든다."""

    def encode(item: Any) -> str:
        if item is None:
            return "null"
        if item is True:
            return "true"
        if item is False:
            return "false"
        if isinstance(item, int):
            return str(item)
        if isinstance(item, float):
            return _float_text(item)
        if isinstance(item, str):
            return json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        if isinstance(item, (list, tuple)):
            return "[" + ",".join(encode(child) for child in item) + "]"
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise TypeError("canonical JSON object keys must be strings")
            return "{" + ",".join(
                f"{encode(key)}:{encode(item[key])}" for key in sorted(item)
            ) + "}"
        raise TypeError(f"unsupported canonical JSON type: {type(item).__name__}")

    return encode(value)


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_text(value).encode("utf-8")).hexdigest()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _iter_tag(root: ET.Element, tag: str) -> Iterable[ET.Element]:
    return (element for element in root.iter() if _local_name(element.tag) == tag)


def _first_tag(root: ET.Element, tag: str) -> ET.Element | None:
    return next(_iter_tag(root, tag), None)


def _as_float(raw: str | None, default: float = 0.0) -> float:
    if raw is None or raw == "":
        return default
    return float(raw)


def _as_int(raw: str | None, default: int = 0) -> int:
    if raw is None or raw == "":
        return default
    return int(raw)


def _as_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes"}


def _id_sort(entity: dict[str, Any]) -> str:
    return str(entity.get("id", ""))


def _source(kind: str, vissim_no: str | int, **extra: Any) -> dict[str, Any]:
    result = {"kind": kind, "vissim_no": str(vissim_no)}
    result.update(extra)
    return result


def _lane_ref(raw: str | None) -> dict[str, Any]:
    tokens = (raw or "").split()
    result: dict[str, Any] = {"raw": raw or "", "link_no": None, "lane_no": None}
    if len(tokens) >= 2:
        result["link_no"] = tokens[0]
        try:
            result["lane_no"] = int(tokens[1])
        except ValueError:
            pass
    if result["link_no"] is not None and result["lane_no"] is not None:
        result["lane_id"] = f"lane:{result['link_no']}:{result['lane_no']}"
        result["lane_group_id"] = f"lg:link:{result['link_no']}:lane:{result['lane_no']}"
    else:
        result["lane_id"] = None
        result["lane_group_id"] = None
    return result


def _sg_ref(raw: str | None) -> dict[str, Any]:
    tokens = (raw or "").split()
    result: dict[str, Any] = {"raw": raw or "", "controller_no": None, "sg_no": None}
    if len(tokens) >= 2:
        result["controller_no"] = tokens[0]
        try:
            result["sg_no"] = int(tokens[1])
        except ValueError:
            pass
    if result["controller_no"] is not None and result["sg_no"] is not None:
        result["signal_group_id"] = f"sg:{result['controller_no']}:{result['sg_no']}"
    else:
        result["signal_group_id"] = None
    return result


def _geometry(element: ET.Element) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    for point in _iter_tag(element, "linkPolyPoint"):
        points.append(
            {
                "x_m": _as_float(point.get("x")),
                "y_m": _as_float(point.get("y")),
                "z_m": _as_float(point.get("zOffset")),
            }
        )
    return points


def _polyline_length(points: list[dict[str, float]]) -> float:
    return sum(
        math.sqrt(
            (right["x_m"] - left["x_m"]) ** 2
            + (right["y_m"] - left["y_m"]) ** 2
            + (right["z_m"] - left["z_m"]) ** 2
        )
        for left, right in zip(points, points[1:])
    )


def _raw_attributes(element: ET.Element, excluded: set[str] | None = None) -> dict[str, str]:
    excluded = excluded or set()
    return {key: element.attrib[key] for key in sorted(element.attrib) if key not in excluded}


def _parse_links(root: ET.Element) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    roads: list[dict[str, Any]] = []
    connectors: list[dict[str, Any]] = []
    for element in _iter_tag(root, "link"):
        no = element.get("no")
        if no is None:
            continue
        from_endpoint = _first_tag(element, "fromLinkEndPt")
        to_endpoint = _first_tag(element, "toLinkEndPt")
        points = _geometry(element)
        lanes_parent = next(
            (child for child in element if _local_name(child.tag) == "lanes"), None
        )
        lane_elements = [] if lanes_parent is None else [
            child for child in lanes_parent if _local_name(child.tag) == "lane"
        ]
        if from_endpoint is not None or to_endpoint is not None:
            from_ref = _lane_ref(None if from_endpoint is None else from_endpoint.get("lane"))
            to_ref = _lane_ref(None if to_endpoint is None else to_endpoint.get("lane"))
            connector_lanes = [
                {
                    "id": f"lane:{no}:{index}",
                    "lane_no": index,
                    "width_m": _as_float(lane.get("width"), 0.0),
                    "closed": _as_bool(lane.get("closed") or lane.get("isClosed")),
                    "source": _source("inpx.link.connectorLane", no, lane_no=index),
                    "source_attributes": _raw_attributes(lane),
                }
                for index, lane in enumerate(lane_elements, 1)
            ]
            lane_mapping = []
            for index in range(1, len(connector_lanes) + 1):
                from_lane_no = None if from_ref["lane_no"] is None else from_ref["lane_no"] + index - 1
                to_lane_no = None if to_ref["lane_no"] is None else to_ref["lane_no"] + index - 1
                lane_mapping.append(
                    {
                        "connector_lane_id": f"lane:{no}:{index}",
                        "connector_lane_group_id": f"lg:link:{no}:lane:{index}",
                        "from_lane_id": None if from_ref["link_no"] is None or from_lane_no is None else f"lane:{from_ref['link_no']}:{from_lane_no}",
                        "from_lane_group_id": None if from_ref["link_no"] is None or from_lane_no is None else f"lg:link:{from_ref['link_no']}:lane:{from_lane_no}",
                        "to_lane_id": None if to_ref["link_no"] is None or to_lane_no is None else f"lane:{to_ref['link_no']}:{to_lane_no}",
                        "to_lane_group_id": None if to_ref["link_no"] is None or to_lane_no is None else f"lg:link:{to_ref['link_no']}:lane:{to_lane_no}",
                    }
                )
            connectors.append(
                {
                    "id": f"connector:{no}",
                    "vissim_no": str(no),
                    "name": element.get("name", ""),
                    "kind": "connector",
                    "geometry": points,
                    "length_m": _polyline_length(points),
                    "lane_count": len(connector_lanes),
                    "lanes": connector_lanes,
                    "from_endpoint": {
                        **from_ref,
                        "position_m": None if from_endpoint is None else _as_float(from_endpoint.get("pos")),
                    },
                    "to_endpoint": {
                        **to_ref,
                        "position_m": None if to_endpoint is None else _as_float(to_endpoint.get("pos")),
                    },
                    "upstream_lane_group_ids": sorted(
                        mapping["from_lane_group_id"] for mapping in lane_mapping if mapping["from_lane_group_id"] is not None
                    ),
                    "connector_lane_group_ids": sorted(mapping["connector_lane_group_id"] for mapping in lane_mapping),
                    "downstream_lane_group_ids": sorted(
                        mapping["to_lane_group_id"] for mapping in lane_mapping if mapping["to_lane_group_id"] is not None
                    ),
                    "lane_mapping": lane_mapping,
                    "level": element.get("level"),
                    "link_behavior_type": element.get("linkBehavType"),
                    "gradient_percent": _as_float(element.get("gradient")),
                    "speed_prior_mps": DEFAULT_V_FREE_MPS,
                    "speed_prior_source": "phase0.default_50_kph",
                    "source": _source("inpx.link.connector", no),
                    "source_attributes": _raw_attributes(element),
                }
            )
            continue

        road_lanes = [
            {
                "id": f"lane:{no}:{index}",
                "lane_no": index,
                "width_m": _as_float(lane.get("width"), 0.0),
                "closed": _as_bool(lane.get("closed") or lane.get("isClosed")),
                "source": _source("inpx.link.lane", no, lane_no=index),
                "source_attributes": _raw_attributes(lane),
            }
            for index, lane in enumerate(lane_elements, 1)
        ]
        roads.append(
            {
                "id": f"link:{no}",
                "vissim_no": str(no),
                "name": element.get("name", ""),
                "kind": "road",
                "geometry": points,
                "length_m": _polyline_length(points),
                "lane_count": len(road_lanes),
                "lanes": road_lanes,
                "level": element.get("level"),
                "link_behavior_type": element.get("linkBehavType"),
                "gradient_percent": _as_float(element.get("gradient")),
                "speed_prior_mps": DEFAULT_V_FREE_MPS,
                "speed_prior_source": "phase0.default_50_kph",
                "source": _source("inpx.link.road", no),
                "source_attributes": _raw_attributes(element),
            }
        )
    return sorted(roads, key=_id_sort), sorted(connectors, key=_id_sort)


def _parse_signals(root: ET.Element) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    controllers: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    heads: list[dict[str, Any]] = []
    for controller in _iter_tag(root, "signalController"):
        no = controller.get("no")
        if no is None:
            continue
        controller_id = f"sc:{no}"
        group_ids: list[str] = []
        for group in _iter_tag(controller, "signalGroup"):
            sg_no = group.get("no")
            if sg_no is None:
                continue
            group_id = f"sg:{no}:{sg_no}"
            group_ids.append(group_id)
            groups.append(
                {
                    "id": group_id,
                    "controller_id": controller_id,
                    "controller_no": str(no),
                    "sg_no": _as_int(sg_no),
                    "name": group.get("name", ""),
                    "amber_sec": _as_float(group.get("amber")),
                    "red_amber_sec": _as_float(group.get("redAmber")),
                    "minimum_green_sec": _as_float(group.get("minGreen")),
                    "minimum_red_sec": _as_float(group.get("minRed")),
                    "source": _source("inpx.signalGroup", sg_no, controller_no=str(no)),
                    "source_attributes": _raw_attributes(group),
                }
            )
        controllers.append(
            {
                "id": controller_id,
                "vissim_no": str(no),
                "name": controller.get("name", ""),
                "active": _as_bool(controller.get("active"), True),
                "type": controller.get("type"),
                "supply_file_2": controller.get("supplyFile2", ""),
                "active_program_no": _as_int(controller.get("progNo"), 1),
                "controller_offset_sec": _as_float(controller.get("offset")),
                "signal_group_ids": sorted(group_ids),
                "source": _source("inpx.signalController", no),
                "source_attributes": _raw_attributes(controller),
            }
        )
    for head in _iter_tag(root, "signalHead"):
        no = head.get("no")
        if no is None:
            continue
        lane = _lane_ref(head.get("lane"))
        sg = _sg_ref(head.get("sg"))
        heads.append(
            {
                "id": f"signal-head:{no}",
                "vissim_no": str(no),
                "name": head.get("name", ""),
                "lane_ref": lane,
                "position_m": _as_float(head.get("pos")),
                "signal_group_ref": sg,
                "source": _source("inpx.signalHead", no),
                "source_attributes": _raw_attributes(head),
            }
        )
    return (
        sorted(controllers, key=_id_sort),
        sorted(groups, key=_id_sort),
        sorted(heads, key=_id_sort),
    )


def _parse_vehicle_inputs(root: ET.Element) -> list[dict[str, Any]]:
    inputs: list[dict[str, Any]] = []
    for element in _iter_tag(root, "vehicleInput"):
        no = element.get("no")
        if no is None:
            continue
        profiles = [
            {"attributes": _raw_attributes(interval)}
            for interval in _iter_tag(element, "timeIntervalVehVolume")
        ]
        inputs.append(
            {
                "id": f"vehicle-input:{no}",
                "vissim_no": str(no),
                "name": element.get("name", ""),
                "link_id": f"link:{element.get('link')}",
                "link_no": element.get("link"),
                "volume_profiles": profiles,
                "source": _source("inpx.vehicleInput", no),
                "source_attributes": _raw_attributes(element),
            }
        )
    return sorted(inputs, key=_id_sort)


def _network_link_id(link_no: str | None, connector_nos: set[str]) -> str:
    prefix = "connector" if str(link_no) in connector_nos else "link"
    return f"{prefix}:{link_no}"


def _parse_routes(
    root: ET.Element, connector_nos: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    for decision in _iter_tag(root, "vehicleRoutingDecisionStatic"):
        decision_no = decision.get("no")
        if decision_no is None:
            continue
        decision_id = f"routing-decision:{decision_no}"
        route_ids: list[str] = []
        for route in _iter_tag(decision, "vehicleRouteStatic"):
            route_no = route.get("no")
            if route_no is None:
                continue
            route_id = f"route:{decision_no}:{route_no}"
            route_ids.append(route_id)
            link_sequence = [reference.get("key", "") for reference in _iter_tag(route, "intObjectRef")]
            rel_flow_raw = route.get("relFlow", "")
            rel_flow_value: float | None = None
            try:
                rel_flow_value = float(rel_flow_raw)
            except ValueError:
                pass
            routes.append(
                {
                    "id": route_id,
                    "decision_id": decision_id,
                    "vissim_no": str(route_no),
                    "name": route.get("name", ""),
                    "destination_link_no": route.get("destLink"),
                    "destination_link_id": _network_link_id(route.get("destLink"), connector_nos),
                    "destination_position_m": _as_float(route.get("destPos")),
                    "relative_flow_raw": rel_flow_raw,
                    "relative_flow": rel_flow_value,
                    "link_sequence_vissim_nos": link_sequence,
                    "link_sequence_ids": [_network_link_id(link_no, connector_nos) for link_no in link_sequence],
                    "source": _source("inpx.vehicleRouteStatic", route_no, decision_no=str(decision_no)),
                    "source_attributes": _raw_attributes(route),
                }
            )
        decisions.append(
            {
                "id": decision_id,
                "vissim_no": str(decision_no),
                "name": decision.get("name", ""),
                "link_no": decision.get("link"),
                "link_id": _network_link_id(decision.get("link"), connector_nos),
                "position_m": _as_float(decision.get("pos")),
                "route_ids": sorted(route_ids),
                "source": _source("inpx.vehicleRoutingDecisionStatic", decision_no),
                "source_attributes": _raw_attributes(decision),
            }
        )
    return sorted(decisions, key=_id_sort), sorted(routes, key=_id_sort)


def _parse_observations(
    root: ET.Element, connector_nos: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    data_points: list[dict[str, Any]] = []
    queue_counters: list[dict[str, Any]] = []
    travel_times: list[dict[str, Any]] = []
    for element in _iter_tag(root, "dataCollectionPoint"):
        no = element.get("no")
        if no is None:
            continue
        data_points.append(
            {
                "id": f"observation:data-collection:{no}",
                "vissim_no": str(no),
                "name": element.get("name", ""),
                "kind": "data_collection_point",
                "lane_ref": _lane_ref(element.get("lane")),
                "position_m": _as_float(element.get("pos")),
                "source": _source("inpx.dataCollectionPoint", no),
            }
        )
    for element in _iter_tag(root, "queueCounter"):
        no = element.get("no")
        if no is None:
            continue
        queue_counters.append(
            {
                "id": f"observation:queue-counter:{no}",
                "vissim_no": str(no),
                "name": element.get("name", ""),
                "kind": "queue_counter",
                "link_no": element.get("link"),
                "link_id": _network_link_id(element.get("link"), connector_nos),
                "position_m": _as_float(element.get("pos")),
                "source": _source("inpx.queueCounter", no),
            }
        )
    for element in _iter_tag(root, "vehicleTravelTimeMeasurement"):
        no = element.get("no")
        if no is None:
            continue
        start = _first_tag(element, "start")
        end = _first_tag(element, "end")
        travel_times.append(
            {
                "id": f"observation:travel-time:{no}",
                "vissim_no": str(no),
                "name": element.get("name", ""),
                "kind": "travel_time_measurement",
                "start": None if start is None else {
                    "link_no": start.get("link"),
                    "link_id": _network_link_id(start.get("link"), connector_nos),
                    "position_m": _as_float(start.get("pos")),
                },
                "end": None if end is None else {
                    "link_no": end.get("link"),
                    "link_id": _network_link_id(end.get("link"), connector_nos),
                    "position_m": _as_float(end.get("pos")),
                },
                "source": _source("inpx.vehicleTravelTimeMeasurement", no),
            }
        )
    return (
        sorted(data_points, key=_id_sort),
        sorted(queue_counters, key=_id_sort),
        sorted(travel_times, key=_id_sort),
    )


def _split_positions(
    network_link: dict[str, Any],
    lane_no: int,
    connectors: list[dict[str, Any]],
    heads: list[dict[str, Any]],
) -> list[tuple[float, list[str]]]:
    link_no = network_link["vissim_no"]
    length = network_link["length_m"]
    lane_id = f"lane:{link_no}:{lane_no}"
    candidates: list[tuple[float, str]] = [(0.0, f"link:{link_no}:start"), (length, f"link:{link_no}:end")]
    for connector in connectors:
        for mapping in connector.get("lane_mapping", []):
            for endpoint_name, mapping_key in (
                ("from_endpoint", "from_lane_id"),
                ("to_endpoint", "to_lane_id"),
            ):
                endpoint = connector[endpoint_name]
                if mapping.get(mapping_key) == lane_id and endpoint["position_m"] is not None:
                    candidates.append((float(endpoint["position_m"]), f"{connector['id']}:{endpoint_name}"))
    for head in heads:
        lane = head["lane_ref"]
        if lane["link_no"] == link_no and lane["lane_no"] == lane_no:
            candidates.append((float(head["position_m"]), head["id"]))
    valid = [(min(length, max(0.0, position)), source) for position, source in candidates if -_POSITION_EPS <= position <= length + _POSITION_EPS]
    valid.sort(key=lambda item: (item[0], item[1]))
    merged: list[tuple[float, list[str]]] = []
    for position, source in valid:
        if merged and abs(position - merged[-1][0]) <= _POSITION_EPS:
            merged[-1][1].append(source)
        else:
            merged.append((position, [source]))
    return [(position, sorted(set(sources))) for position, sources in merged]


def _build_lane_groups(
    roads: list[dict[str, Any]],
    connectors: list[dict[str, Any]],
    heads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    downstream: dict[str, list[str]] = {}
    for connector in connectors:
        lane_id = connector["from_endpoint"].get("lane_id")
        if lane_id:
            downstream.setdefault(lane_id, []).append(connector["id"])
    gates_by_lane: dict[str, list[str]] = {}
    for head in heads:
        lane_id = head["lane_ref"].get("lane_id")
        if lane_id:
            gates_by_lane.setdefault(lane_id, []).append(f"gate:head:{head['vissim_no']}")
    result: list[dict[str, Any]] = []
    for road in roads:
        for lane in road["lanes"]:
            lane_id = lane["id"]
            connector_ids = sorted(set(downstream.get(lane_id, [])))
            gate_ids = sorted(set(gates_by_lane.get(lane_id, [])))
            merge_key = "|".join(
                [
                    f"link={road['vissim_no']}",
                    f"downstream={','.join(connector_ids)}",
                    f"gates={','.join(gate_ids)}",
                ]
            )
            result.append(
                {
                    "id": f"lg:link:{road['vissim_no']}:lane:{lane['lane_no']}",
                    "link_id": road["id"],
                    "link_no": road["vissim_no"],
                    "member_lane_ids": [lane_id],
                    "longitudinal_start_m": 0.0,
                    "longitudinal_end_m": road["length_m"],
                    "downstream_connector_ids": connector_ids,
                    "signal_gate_ids": gate_ids,
                    "model_type": "lane_group_ctm",
                    "merge_compatibility_key": merge_key,
                    "merge_hook": {"phase0_grouping": "individual_lane", "same_link_only": True, "key": merge_key},
                    "source": _source("derived.laneGroup", road["vissim_no"], lane_no=lane["lane_no"]),
                }
            )
    for connector in connectors:
        for lane in connector["lanes"]:
            lane_id = lane["id"]
            gate_ids = sorted(set(gates_by_lane.get(lane_id, [])))
            merge_key = "|".join(
                [
                    f"connector={connector['vissim_no']}",
                    f"lane={lane['lane_no']}",
                    f"gates={','.join(gate_ids)}",
                ]
            )
            result.append(
                {
                    "id": f"lg:link:{connector['vissim_no']}:lane:{lane['lane_no']}",
                    "link_id": connector["id"],
                    "link_no": connector["vissim_no"],
                    "member_lane_ids": [lane_id],
                    "longitudinal_start_m": 0.0,
                    "longitudinal_end_m": connector["length_m"],
                    "downstream_connector_ids": [],
                    "signal_gate_ids": gate_ids,
                    "model_type": "lane_group_ctm",
                    "merge_compatibility_key": merge_key,
                    "merge_hook": {
                        "phase0_grouping": "individual_lane",
                        "same_link_only": True,
                        "key": merge_key,
                    },
                    "source": _source(
                        "derived.connectorLaneGroup",
                        connector["vissim_no"],
                        lane_no=lane["lane_no"],
                    ),
                }
            )
    return sorted(result, key=_id_sort)


def _build_signal_gates(
    heads: list[dict[str, Any]], connectors: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    connector_nos = {connector["vissim_no"] for connector in connectors}
    for head in heads:
        lane = head["lane_ref"]
        downstream = [
            connector
            for connector in connectors
            if connector["from_endpoint"].get("lane_id") == lane.get("lane_id")
            and connector["from_endpoint"].get("position_m") is not None
            and connector["from_endpoint"]["position_m"] + _POSITION_EPS >= head["position_m"]
        ]
        controlled: list[str] = []
        if lane.get("link_no") in connector_nos:
            controlled = [f"movement:{lane['link_no']}"]
        elif downstream:
            nearest = min(connector["from_endpoint"]["position_m"] for connector in downstream)
            controlled = sorted(
                f"movement:{connector['vissim_no']}"
                for connector in downstream
                if abs(connector["from_endpoint"]["position_m"] - nearest) <= _POSITION_EPS
            )
        gates.append(
            {
                "id": f"gate:head:{head['vissim_no']}",
                "signal_head_id": head["id"],
                "signal_group_id": head["signal_group_ref"].get("signal_group_id"),
                "lane_id": lane.get("lane_id"),
                "lane_group_id": lane.get("lane_group_id"),
                "position_m": head["position_m"],
                "controlled_movement_ids": controlled,
                "source_signal_head_ids": [head["id"]],
                "source": _source("derived.signalGate", head["vissim_no"]),
            }
        )
    return sorted(gates, key=_id_sort)


def _build_cells(
    roads: list[dict[str, Any]],
    connectors: list[dict[str, Any]],
    heads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    lane_cells: dict[str, list[dict[str, Any]]] = {}
    for network_link in roads + connectors:
        if network_link["length_m"] <= 0.0:
            continue
        for lane in network_link["lanes"]:
            lane_no = lane["lane_no"]
            lane_id = lane["id"]
            positions = _split_positions(network_link, lane_no, connectors, heads)
            current: list[dict[str, Any]] = []
            for index, ((start, start_sources), (end, end_sources)) in enumerate(zip(positions, positions[1:])):
                length = end - start
                if length <= _POSITION_EPS:
                    continue
                minimum_time = length / DEFAULT_V_FREE_MPS
                cell = {
                    "id": f"cell:link:{network_link['vissim_no']}:lane:{lane_no}:seg:{index:04d}",
                    "lane_group_id": f"lg:link:{network_link['vissim_no']}:lane:{lane_no}",
                    "ordered_index": len(current),
                    "start_position_m": start,
                    "end_position_m": end,
                    "length_m": length,
                    "lanes": [lane_id],
                    "lane_count": 1,
                    "model_type": "ctm",
                    "upstream_cell_ids": [],
                    "downstream_cell_ids": [],
                    "storage_veh": length / DEFAULT_JAM_SPACING_M,
                    "minimum_travel_time_sec": minimum_time,
                    "delay_buffer_steps": max(1, math.ceil(minimum_time / DEFAULT_URBAN_DT_SEC)),
                    "cfl": {
                        "reference_dt_sec": DEFAULT_URBAN_DT_SEC,
                        "maximum_dt_sec_from_free_flow": minimum_time,
                        "reference_dt_satisfies_free_flow_cfl": DEFAULT_URBAN_DT_SEC <= minimum_time + _POSITION_EPS,
                        "backward_wave_limit_sec": None,
                        "backward_wave_status": "calibration_required",
                    },
                    "parameter_placeholders": {
                        "v_free_mps": DEFAULT_V_FREE_MPS,
                        "v_free_source": "phase0.default_50_kph",
                        "jam_spacing_m_per_veh": DEFAULT_JAM_SPACING_M,
                        "jam_spacing_source": "phase0.default",
                    },
                    "source_object_ids": sorted(set(start_sources + end_sources + [network_link["id"], lane_id])),
                    "source": _source("derived.cell", network_link["vissim_no"], lane_no=lane_no),
                }
                current.append(cell)
                cells.append(cell)
            for left, right in zip(current, current[1:]):
                left["downstream_cell_ids"].append(right["id"])
                right["upstream_cell_ids"].append(left["id"])
            lane_cells[lane_id] = current

    def source_cell_at(candidates: list[dict[str, Any]], position: float) -> dict[str, Any] | None:
        exact = next(
            (cell for cell in candidates if abs(cell["end_position_m"] - position) <= _POSITION_EPS),
            None,
        )
        if exact is not None:
            return exact
        return next(
            (
                cell
                for cell in candidates
                if cell["start_position_m"] - _POSITION_EPS
                <= position
                <= cell["end_position_m"] + _POSITION_EPS
            ),
            None,
        )

    def target_cell_at(candidates: list[dict[str, Any]], position: float) -> dict[str, Any] | None:
        exact = next(
            (cell for cell in candidates if abs(cell["start_position_m"] - position) <= _POSITION_EPS),
            None,
        )
        if exact is not None:
            return exact
        return next(
            (
                cell
                for cell in candidates
                if cell["start_position_m"] - _POSITION_EPS
                <= position
                <= cell["end_position_m"] + _POSITION_EPS
            ),
            None,
        )

    for connector in connectors:
        source_pos = connector["from_endpoint"].get("position_m")
        target_pos = connector["to_endpoint"].get("position_m")
        if source_pos is None or target_pos is None:
            continue
        for mapping in connector.get("lane_mapping", []):
            source_cell = source_cell_at(lane_cells.get(mapping.get("from_lane_id"), []), source_pos)
            connector_cells = lane_cells.get(mapping.get("connector_lane_id"), [])
            target_cell = target_cell_at(lane_cells.get(mapping.get("to_lane_id"), []), target_pos)
            if source_cell is not None and connector_cells:
                connector_first = connector_cells[0]
                source_cell["downstream_cell_ids"].append(connector_first["id"])
                connector_first["upstream_cell_ids"].append(source_cell["id"])
            if connector_cells and target_cell is not None:
                connector_last = connector_cells[-1]
                connector_last["downstream_cell_ids"].append(target_cell["id"])
                target_cell["upstream_cell_ids"].append(connector_last["id"])

    for cell in cells:
        cell["upstream_cell_ids"] = sorted(set(cell["upstream_cell_ids"]))
        cell["downstream_cell_ids"] = sorted(set(cell["downstream_cell_ids"]))
    return sorted(cells, key=_id_sort)


def _build_movements(connectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "id": f"movement:{connector['vissim_no']}",
                "connector_ids": [connector["id"]],
                "source_lane_group_id": connector["from_endpoint"].get("lane_group_id"),
                "target_lane_group_id": connector["to_endpoint"].get("lane_group_id"),
                "source_lane_group_ids": connector.get("upstream_lane_group_ids", []),
                "connector_lane_group_ids": connector.get("connector_lane_group_ids", []),
                "target_lane_group_ids": connector.get("downstream_lane_group_ids", []),
                "turn_ratio": None,
                "capacity_vehps": None,
                "priority": None,
                "parameter_gaps": [
                    {"parameter": "turn_ratio", "status": "calibration_required"},
                    {"parameter": "capacity_vehps", "status": "calibration_required"},
                    {"parameter": "priority", "status": "calibration_required"},
                ],
                "source": _source("derived.movement", connector["vissim_no"]),
            }
            for connector in connectors
        ],
        key=_id_sort,
    )


def _build_freeway_interface_candidates(
    movements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose transfer edges without guessing urban/freeway ownership from INPX."""

    return sorted(
        [
            {
                "id": f"freeway-interface-candidate:{movement['id']}",
                "status": "classification_required",
                "movement_id": movement["id"],
                "connector_ids": list(movement["connector_ids"]),
                "source_lane_group_ids": list(movement["source_lane_group_ids"]),
                "connector_lane_group_ids": list(movement["connector_lane_group_ids"]),
                "target_lane_group_ids": list(movement["target_lane_group_ids"]),
                "urban_owner_id": None,
                "freeway_owner_id": None,
                "sending_rule": None,
                "receiving_rule": None,
                "parameter_gaps": [
                    {"parameter": "domain_ownership", "status": "calibration_required"},
                    {"parameter": "sending_rule", "status": "calibration_required"},
                    {"parameter": "receiving_rule", "status": "calibration_required"},
                ],
                "source": _source(
                    "derived.freewayInterfaceCandidate",
                    movement["source"]["vissim_no"],
                ),
            }
            for movement in movements
        ],
        key=_id_sort,
    )


def _build_influence_subgraphs(
    cells: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    controlled_uf_to_sc: tuple[tuple[int, str], ...] = CONTROLLED_UF_TO_SC,
) -> list[dict[str, Any]]:
    """Build deterministic controller neighborhoods with exclusive cell ownership."""

    cell_by_id = {cell["id"]: cell for cell in cells}
    cells_by_group: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        cells_by_group.setdefault(cell["lane_group_id"], []).append(cell)
    for group_cells in cells_by_group.values():
        group_cells.sort(key=lambda item: (item["ordered_index"], item["id"]))

    candidates: dict[int, dict[str, Any]] = {}
    for uf_id, sc_no in controlled_uf_to_sc:
        controller_gates = sorted(
            [gate for gate in gates if str(gate.get("signal_group_id", "")).startswith(f"sg:{sc_no}:")],
            key=_id_sort,
        )
        if not controller_gates:
            continue
        seed_ids: set[str] = set()
        for gate in controller_gates:
            position = float(gate["position_m"])
            for cell in cells_by_group.get(str(gate.get("lane_group_id")), []):
                if (
                    abs(float(cell["start_position_m"]) - position) <= _POSITION_EPS
                    or abs(float(cell["end_position_m"]) - position) <= _POSITION_EPS
                ):
                    seed_ids.add(cell["id"])

        distance = {cell_id: 0 for cell_id in sorted(seed_ids)}
        frontier = sorted(seed_ids)
        for hop in range(1, DEFAULT_INFLUENCE_HOPS + 1):
            next_frontier: set[str] = set()
            for cell_id in frontier:
                cell = cell_by_id[cell_id]
                for neighbor in cell["upstream_cell_ids"] + cell["downstream_cell_ids"]:
                    if neighbor not in distance:
                        distance[neighbor] = hop
                        next_frontier.add(neighbor)
            frontier = sorted(next_frontier)
        candidates[uf_id] = {
            "sc_no": sc_no,
            "gates": controller_gates,
            "seed_ids": sorted(seed_ids),
            "distance": distance,
        }

    ownership_claims: dict[str, list[tuple[int, int]]] = {}
    for uf_id, candidate in candidates.items():
        for cell_id, distance in candidate["distance"].items():
            ownership_claims.setdefault(cell_id, []).append((distance, uf_id))
    owner_by_cell = {
        cell_id: min(claims)[1] for cell_id, claims in ownership_claims.items()
    }

    mapping_snapshot = [
        {"urban_follower_id": uf_id, "signal_controller_no": sc_no}
        for uf_id, sc_no in controlled_uf_to_sc
    ]
    mapping_hash = canonical_json_sha256(mapping_snapshot)
    result: list[dict[str, Any]] = []
    for uf_id in sorted(candidates):
        candidate = candidates[uf_id]
        sc_no = candidate["sc_no"]
        member_ids = sorted(candidate["distance"])
        owned_ids = sorted(
            cell_id for cell_id in member_ids if owner_by_cell.get(cell_id) == uf_id
        )
        owned_set = set(owned_ids)
        boundary_ownership: list[dict[str, Any]] = []
        seen_boundaries: set[tuple[str, str, str]] = set()
        for owned_id in owned_ids:
            cell = cell_by_id[owned_id]
            for direction, neighbors in (
                ("inbound", cell["upstream_cell_ids"]),
                ("outbound", cell["downstream_cell_ids"]),
            ):
                for external_id in neighbors:
                    if external_id in owned_set:
                        continue
                    key = (owned_id, external_id, direction)
                    if key in seen_boundaries:
                        continue
                    seen_boundaries.add(key)
                    boundary_ownership.append(
                        {
                            "owned_cell_id": owned_id,
                            "external_cell_id": external_id,
                            "direction": direction,
                            "external_vehicle_owner_kind": "frozen_boundary_trajectory",
                            "flow_contract": "subtract_from_source_and_add_to_target_once",
                        }
                    )
        controller_gates = candidate["gates"]
        action_gate_ids = sorted(
            gate["id"]
            for gate in controller_gates
            if int(str(gate["signal_group_id"]).rsplit(":", 1)[-1]) in CONTROLLED_MAIN_SG_NOS
        )
        fixed_gate_ids = sorted(
            gate["id"] for gate in controller_gates if gate["id"] not in set(action_gate_ids)
        )
        result.append(
            {
                "id": f"influence-subgraph:UF{uf_id}",
                "urban_follower_id": uf_id,
                "controller_id": f"sc:{sc_no}",
                "controller_no": sc_no,
                "construction_status": "deterministic_controller_centered_default",
                "graph_radius_hops": DEFAULT_INFLUENCE_HOPS,
                "seed_cell_ids": candidate["seed_ids"],
                "member_cell_ids": member_ids,
                "owned_cell_ids": owned_ids,
                "owned_gate_ids": sorted(gate["id"] for gate in controller_gates),
                "action_enabled_gate_ids": action_gate_ids,
                "fixed_context_gate_ids": fixed_gate_ids,
                "vehicle_ownership": {
                    "owner_kind": "influence_subgraph",
                    "owner_id": f"influence-subgraph:UF{uf_id}",
                    "owned_cell_ids": owned_ids,
                    "boundary": sorted(
                        boundary_ownership,
                        key=lambda item: (
                            item["owned_cell_id"],
                            item["external_cell_id"],
                            item["direction"],
                        ),
                    ),
                },
                "source": {
                    "kind": "derived.controllerCenteredInfluenceSubgraph",
                    "authority": "G0 controlled UF selection plus Urban-Follower adapter SC mapping snapshot",
                    "mapping_snapshot_sha256": mapping_hash,
                    "algorithm": "signal-head boundary cells plus undirected one-hop adjacency; exclusive ownership by distance then UF id",
                },
            }
        )
    return sorted(result, key=_id_sort)


def _topology_hash_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key not in {"topology_hash", "validation_report"}}


def compile_inpx(path: str | Path) -> dict[str, Any]:
    """INPX 파일을 deterministic canonical topology manifest로 compile한다."""
    inpx_path = Path(path).resolve()
    raw = inpx_path.read_bytes()
    root = ET.fromstring(raw)
    simulation = _first_tag(root, "simulation")
    roads, connectors = _parse_links(root)
    connector_nos = {connector["vissim_no"] for connector in connectors}
    controllers, groups, heads = _parse_signals(root)
    inputs = _parse_vehicle_inputs(root)
    decisions, routes = _parse_routes(root, connector_nos)
    data_points, queue_counters, travel_times = _parse_observations(root, connector_nos)
    gates = _build_signal_gates(heads, connectors)
    lane_groups = _build_lane_groups(roads, connectors, heads)
    cells = _build_cells(roads, connectors, heads)
    movements = _build_movements(connectors)
    freeway_interface_candidates = _build_freeway_interface_candidates(movements)
    influence_subgraphs = _build_influence_subgraphs(cells, gates)
    control_mapping_snapshot = [
        {"urban_follower_id": uf_id, "signal_controller_no": sc_no}
        for uf_id, sc_no in CONTROLLED_UF_TO_SC
    ]
    boundaries = [
        {
            "id": f"boundary:source:{item['vissim_no']}",
            "type": "source",
            "vehicle_input_id": item["id"],
            "link_id": item["link_id"],
            "external_queue_owner": True,
            "source": _source("derived.boundary", item["vissim_no"]),
        }
        for item in inputs
    ]
    observations = sorted(data_points + queue_counters + travel_times, key=_id_sort)
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "compiler_version": COMPILER_VERSION,
        "canonical_json_version": CANONICAL_JSON_VERSION,
        "source": {
            "inpx_path": inpx_path.name,
            "inpx_sha256": hashlib.sha256(raw).hexdigest(),
            "vissim_network_version": root.get("version"),
            "vissim_version": root.get("vissimVersion"),
            "provenance": "modi.inpx",
            "hash_scope": "manifest excluding topology_hash and validation_report",
        },
        "simulation": {
            "start_time_sec": 0.0 if simulation is None else _as_float(simulation.get("startTm")),
            "source_attribute": "simulation.startTm",
        },
        "coordinate_system": None,
        "control_authority": {
            "controlled_uf_to_signal_controller": control_mapping_snapshot,
            "action_enabled_signal_group_nos": sorted(CONTROLLED_MAIN_SG_NOS),
            "status": "embedded_approved_mapping_snapshot",
            "source": "G0 controlled UF selection plus Urban-Follower adapter SC mapping",
            "mapping_snapshot_sha256": canonical_json_sha256(control_mapping_snapshot),
        },
        "defaults": {
            "urban_dt_sec": DEFAULT_URBAN_DT_SEC,
            "v_free_mps": DEFAULT_V_FREE_MPS,
            "jam_spacing_m_per_veh": DEFAULT_JAM_SPACING_M,
            "status": "phase0_placeholders_require_calibration",
            "modeling_resolution": {
                "lane_grouping": "individual_vissim_lane",
                "true_lane_grouping_inferred": False,
                "connector_representation": "first_class_lane_groups_and_cells",
                "reason": "INPX topology alone does not establish shared-choice lane groups",
            },
        },
        "links": roads,
        "connector_links": connectors,
        "connectors": connectors,
        "lane_groups": lane_groups,
        "cells": cells,
        "movements": movements,
        "signal_controllers": controllers,
        "signal_groups": groups,
        "signal_heads": heads,
        "signal_gates": gates,
        "schedules": {"fixed": [], "controlled": [], "derived": []},
        "vehicle_inputs": inputs,
        "routing_decisions": decisions,
        "routes": routes,
        "boundaries": sorted(boundaries, key=_id_sort),
        "data_collection_points": data_points,
        "queue_counters": queue_counters,
        "travel_time_measurements": travel_times,
        "observation_operators": observations,
        "freeway_interfaces": [],
        "freeway_interface_candidates": freeway_interface_candidates,
        "parameter_gaps": [
            {
                "parameter": "movement.turn_ratio",
                "status": "calibration_required",
                "affected_entity_ids": [movement["id"] for movement in movements],
            },
            {
                "parameter": "movement.capacity_vehps",
                "status": "calibration_required",
                "affected_entity_ids": [movement["id"] for movement in movements],
            },
            {
                "parameter": "movement.priority",
                "status": "calibration_required",
                "affected_entity_ids": [movement["id"] for movement in movements],
            },
            {
                "parameter": "cell.backward_wave_speed_mps",
                "status": "calibration_required",
                "affected_entity_ids": [cell["id"] for cell in cells],
            },
            {
                "parameter": "freeway_interface.domain_ownership_and_coupling",
                "status": "calibration_required",
                "affected_entity_ids": [candidate["id"] for candidate in freeway_interface_candidates],
            },
        ],
        "influence_subgraphs": influence_subgraphs,
    }
    manifest["topology_hash"] = canonical_json_sha256(_topology_hash_payload(manifest))
    manifest["validation_report"] = validate_topology(manifest)
    return manifest


def validate_topology(manifest: dict[str, Any]) -> dict[str, Any]:
    """참조 무결성, cell ordering, 양의 길이를 검사한다."""
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def issue(target: list[dict[str, Any]], code: str, entity_id: str, detail: str) -> None:
        target.append({"code": code, "entity_id": entity_id, "detail": detail})

    def ids(key: str) -> set[str]:
        values = [str(entity.get("id")) for entity in manifest.get(key, [])]
        seen: set[str] = set()
        for value in values:
            if value in seen:
                issue(errors, "duplicate_id", value, f"duplicate id in {key}")
            seen.add(value)
        return seen

    link_ids = ids("links")
    connector_ids = ids("connectors")
    lane_group_ids = ids("lane_groups")
    cell_ids = ids("cells")
    group_ids = ids("signal_groups")
    movement_ids = ids("movements")
    route_ids = ids("routes")
    controller_ids = ids("signal_controllers")
    ids("signal_heads")
    gate_ids = ids("signal_gates")
    ids("vehicle_inputs")
    ids("routing_decisions")
    ids("observation_operators")
    ids("freeway_interface_candidates")
    ids("influence_subgraphs")

    road_by_no = {str(link.get("vissim_no")): link for link in manifest.get("links", [])}
    connector_by_no = {
        str(link.get("vissim_no")): link for link in manifest.get("connectors", [])
    }
    network_by_no = {**road_by_no, **connector_by_no}
    network_link_nos = set(network_by_no)

    def validate_lane_ref(ref: dict[str, Any], entity_id: str, field: str) -> None:
        link_no = ref.get("link_no")
        lane_no = ref.get("lane_no")
        network_link = network_by_no.get(str(link_no))
        if network_link is None:
            issue(errors, "dangling_link_ref", entity_id, f"{field} references network link {link_no}")
            return
        if not isinstance(lane_no, int) or not 1 <= lane_no <= int(network_link.get("lane_count", 0)):
            issue(errors, "dangling_lane_ref", entity_id, f"{field} references lane {link_no} {lane_no}")
        position = ref.get("position_m")
        if position is not None and not (
            -_POSITION_EPS
            <= float(position)
            <= float(network_link["length_m"]) + _POSITION_EPS
        ):
            issue(
                errors,
                "position_out_of_range",
                entity_id,
                f"{field} position {position} outside [0,{network_link['length_m']}]",
            )

    for link in manifest.get("links", []):
        if float(link.get("length_m", 0.0)) <= 0.0:
            issue(errors, "nonpositive_link_length", link["id"], "road link geometry must have positive length")
        if not link.get("lanes"):
            issue(errors, "missing_lanes", link["id"], "road link has no lanes")

    for connector in manifest.get("connectors", []):
        if float(connector.get("length_m", 0.0)) <= 0.0:
            issue(errors, "nonpositive_connector_length", connector["id"], str(connector.get("length_m")))
        if not connector.get("lanes"):
            issue(errors, "missing_lanes", connector["id"], "connector has no lanes")
        validate_lane_ref(connector.get("from_endpoint", {}), connector["id"], "from_endpoint")
        validate_lane_ref(connector.get("to_endpoint", {}), connector["id"], "to_endpoint")
        for mapping in connector.get("lane_mapping", []):
            for field in (
                "from_lane_group_id",
                "connector_lane_group_id",
                "to_lane_group_id",
            ):
                if mapping.get(field) not in lane_group_ids:
                    issue(errors, "dangling_lane_group_ref", connector["id"], str(mapping.get(field)))
        for group_id in (
            connector.get("upstream_lane_group_ids", [])
            + connector.get("connector_lane_group_ids", [])
            + connector.get("downstream_lane_group_ids", [])
        ):
            if group_id not in lane_group_ids:
                issue(errors, "dangling_lane_group_ref", connector["id"], group_id)

    for head in manifest.get("signal_heads", []):
        ref = dict(head.get("lane_ref", {}))
        ref["position_m"] = head.get("position_m")
        validate_lane_ref(ref, head["id"], "lane_ref")
        group_id = head.get("signal_group_ref", {}).get("signal_group_id")
        if group_id not in group_ids:
            issue(errors, "dangling_signal_group_ref", head["id"], str(group_id))

    for cell in manifest.get("cells", []):
        if float(cell.get("length_m", 0.0)) <= 0.0:
            issue(errors, "nonpositive_cell_length", cell["id"], str(cell.get("length_m")))
        if float(cell.get("minimum_travel_time_sec", 0.0)) <= 0.0:
            issue(errors, "nonpositive_minimum_travel_time", cell["id"], str(cell.get("minimum_travel_time_sec")))
        if float(cell.get("storage_veh", 0.0)) <= 0.0:
            issue(errors, "nonpositive_storage", cell["id"], str(cell.get("storage_veh")))
        if cell.get("lane_group_id") not in lane_group_ids:
            issue(errors, "dangling_lane_group_ref", cell["id"], str(cell.get("lane_group_id")))
        for neighbor in cell.get("upstream_cell_ids", []) + cell.get("downstream_cell_ids", []):
            if neighbor not in cell_ids:
                issue(errors, "dangling_cell_ref", cell["id"], str(neighbor))
        reference_dt = float(manifest.get("defaults", {}).get("urban_dt_sec", DEFAULT_URBAN_DT_SEC))
        if reference_dt > float(cell.get("minimum_travel_time_sec", 0.0)) + _POSITION_EPS:
            issue(
                warnings,
                "cfl_reference_dt_exceeds_cell_travel_time",
                cell["id"],
                f"dt={reference_dt} minimum_travel_time_sec={cell.get('minimum_travel_time_sec')}",
            )

    cells_by_group: dict[str, list[dict[str, Any]]] = {}
    for cell in manifest.get("cells", []):
        cells_by_group.setdefault(str(cell.get("lane_group_id")), []).append(cell)
    for group_id, group_cells in cells_by_group.items():
        ordered = sorted(group_cells, key=lambda cell: int(cell.get("ordered_index", -1)))
        if [cell.get("ordered_index") for cell in ordered] != list(range(len(ordered))):
            issue(errors, "noncontiguous_cell_order", group_id, "ordered_index must start at zero and be contiguous")
        for left, right in zip(ordered, ordered[1:]):
            if abs(float(left["end_position_m"]) - float(right["start_position_m"])) > _POSITION_EPS:
                issue(errors, "cell_gap_or_overlap", group_id, f"{left['id']} -> {right['id']}")

    for connector in manifest.get("connectors", []):
        source_position = connector.get("from_endpoint", {}).get("position_m")
        target_position = connector.get("to_endpoint", {}).get("position_m")
        if source_position is None or target_position is None:
            continue
        for mapping in connector.get("lane_mapping", []):
            source_cells = cells_by_group.get(str(mapping.get("from_lane_group_id")), [])
            connector_cells = sorted(
                cells_by_group.get(str(mapping.get("connector_lane_group_id")), []),
                key=lambda cell: int(cell.get("ordered_index", -1)),
            )
            target_cells = cells_by_group.get(str(mapping.get("to_lane_group_id")), [])
            source_cell = next(
                (
                    cell
                    for cell in source_cells
                    if abs(float(cell["end_position_m"]) - float(source_position)) <= _POSITION_EPS
                ),
                None,
            )
            target_cell = next(
                (
                    cell
                    for cell in target_cells
                    if abs(float(cell["start_position_m"]) - float(target_position)) <= _POSITION_EPS
                ),
                None,
            )
            if not connector_cells or source_cell is None or target_cell is None:
                issue(
                    errors,
                    "unresolved_connector_endpoint_adjacency",
                    connector["id"],
                    str(mapping.get("connector_lane_id")),
                )
                continue
            first_connector_cell = connector_cells[0]
            last_connector_cell = connector_cells[-1]
            if first_connector_cell["id"] not in source_cell.get("downstream_cell_ids", []):
                issue(errors, "missing_connector_upstream_adjacency", connector["id"], first_connector_cell["id"])
            if source_cell["id"] not in first_connector_cell.get("upstream_cell_ids", []):
                issue(errors, "missing_connector_upstream_adjacency", connector["id"], source_cell["id"])
            if target_cell["id"] not in last_connector_cell.get("downstream_cell_ids", []):
                issue(errors, "missing_connector_downstream_adjacency", connector["id"], target_cell["id"])
            if last_connector_cell["id"] not in target_cell.get("upstream_cell_ids", []):
                issue(errors, "missing_connector_downstream_adjacency", connector["id"], last_connector_cell["id"])

    for movement in manifest.get("movements", []):
        if movement.get("connector_ids", [None])[0] not in connector_ids:
            issue(errors, "dangling_connector_ref", movement["id"], str(movement.get("connector_ids")))
        for field in ("source_lane_group_id", "target_lane_group_id"):
            if movement.get(field) not in lane_group_ids:
                issue(errors, "dangling_lane_group_ref", movement["id"], str(movement.get(field)))
        declared_gaps = {
            gap.get("parameter")
            for gap in movement.get("parameter_gaps", [])
            if gap.get("status") == "calibration_required"
        }
        unresolved = [
            parameter
            for parameter in ("turn_ratio", "capacity_vehps", "priority")
            if movement.get(parameter) is None
        ]
        missing_gap_declarations = sorted(set(unresolved) - declared_gaps)
        if missing_gap_declarations:
            issue(
                errors,
                "undeclared_movement_parameter_gap",
                movement["id"],
                ",".join(missing_gap_declarations),
            )

    unresolved_movement_parameters = sorted(
        {
            parameter
            for movement in manifest.get("movements", [])
            for parameter in ("turn_ratio", "capacity_vehps", "priority")
            if movement.get(parameter) is None
        }
    )
    if unresolved_movement_parameters:
        issue(
            warnings,
            "movement_calibration_required",
            "manifest",
            ",".join(unresolved_movement_parameters),
        )

    for candidate in manifest.get("freeway_interface_candidates", []):
        if candidate.get("movement_id") not in movement_ids:
            issue(errors, "dangling_movement_ref", candidate["id"], str(candidate.get("movement_id")))
        for connector_id in candidate.get("connector_ids", []):
            if connector_id not in connector_ids:
                issue(errors, "dangling_connector_ref", candidate["id"], connector_id)
        for group_id in (
            candidate.get("source_lane_group_ids", [])
            + candidate.get("connector_lane_group_ids", [])
            + candidate.get("target_lane_group_ids", [])
        ):
            if group_id not in lane_group_ids:
                issue(errors, "dangling_lane_group_ref", candidate["id"], group_id)

    expected_sc_nos = {sc_no for _, sc_no in CONTROLLED_UF_TO_SC}
    network_sc_nos = {
        str(controller.get("vissim_no"))
        for controller in manifest.get("signal_controllers", [])
    }
    present_controlled_sc_nos = expected_sc_nos & network_sc_nos
    subgraphs = manifest.get("influence_subgraphs", [])
    if present_controlled_sc_nos and present_controlled_sc_nos != expected_sc_nos:
        issue(
            errors,
            "incomplete_control_authority_mapping",
            "manifest",
            f"present={sorted(present_controlled_sc_nos)} expected={sorted(expected_sc_nos)}",
        )
    if present_controlled_sc_nos == expected_sc_nos:
        subgraph_sc_nos = {str(subgraph.get("controller_no")) for subgraph in subgraphs}
        if subgraph_sc_nos != expected_sc_nos or len(subgraphs) != len(CONTROLLED_UF_TO_SC):
            issue(
                errors,
                "missing_controlled_influence_subgraphs",
                "manifest",
                f"compiled={sorted(subgraph_sc_nos)} expected={sorted(expected_sc_nos)}",
            )

    physical_owner: dict[str, str] = {}
    for subgraph in subgraphs:
        subgraph_id = subgraph["id"]
        if subgraph.get("controller_id") not in controller_ids:
            issue(errors, "dangling_controller_ref", subgraph_id, str(subgraph.get("controller_id")))
        for field in ("seed_cell_ids", "member_cell_ids", "owned_cell_ids"):
            values = subgraph.get(field, [])
            if not values:
                issue(errors, "empty_influence_subgraph_cells", subgraph_id, field)
            for cell_id in values:
                if cell_id not in cell_ids:
                    issue(errors, "dangling_cell_ref", subgraph_id, cell_id)
        for gate_id in subgraph.get("owned_gate_ids", []):
            if gate_id not in gate_ids:
                issue(errors, "dangling_signal_gate_ref", subgraph_id, gate_id)
        for cell_id in subgraph.get("owned_cell_ids", []):
            previous_owner = physical_owner.get(cell_id)
            if previous_owner is not None:
                issue(
                    errors,
                    "duplicate_cell_vehicle_owner",
                    cell_id,
                    f"{previous_owner},{subgraph_id}",
                )
            physical_owner[cell_id] = subgraph_id
        ownership = subgraph.get("vehicle_ownership", {})
        if ownership.get("owner_id") != subgraph_id or ownership.get("owned_cell_ids") != subgraph.get("owned_cell_ids"):
            issue(errors, "invalid_vehicle_ownership", subgraph_id, "owned cell registry mismatch")
        boundary_keys = {
            (
                item.get("owned_cell_id"),
                item.get("external_cell_id"),
                item.get("direction"),
            )
            for item in ownership.get("boundary", [])
            if item.get("external_vehicle_owner_kind") == "frozen_boundary_trajectory"
        }
        owned_set = set(subgraph.get("owned_cell_ids", []))
        for owned_id in owned_set:
            cell = next((item for item in manifest.get("cells", []) if item["id"] == owned_id), None)
            if cell is None:
                continue
            for direction, neighbors in (
                ("inbound", cell.get("upstream_cell_ids", [])),
                ("outbound", cell.get("downstream_cell_ids", [])),
            ):
                for external_id in neighbors:
                    if external_id not in owned_set and (owned_id, external_id, direction) not in boundary_keys:
                        issue(
                            errors,
                            "missing_boundary_vehicle_ownership",
                            subgraph_id,
                            f"{owned_id}->{external_id}:{direction}",
                        )

    for item in manifest.get("vehicle_inputs", []):
        if item.get("link_id") not in link_ids:
            issue(errors, "dangling_vehicle_input_link", item["id"], str(item.get("link_id")))
    for item in manifest.get("routing_decisions", []):
        if item.get("link_no") not in network_link_nos:
            issue(errors, "dangling_routing_decision_link", item["id"], str(item.get("link_id")))
        elif not (
            -_POSITION_EPS
            <= float(item.get("position_m", 0.0))
            <= float(network_by_no[str(item["link_no"])]["length_m"]) + _POSITION_EPS
        ):
            issue(errors, "position_out_of_range", item["id"], str(item.get("position_m")))
        for route_id in item.get("route_ids", []):
            if route_id not in route_ids:
                issue(errors, "dangling_route_ref", item["id"], route_id)
    for route in manifest.get("routes", []):
        destination = route.get("destination_link_no")
        if destination not in network_link_nos:
            issue(errors, "dangling_route_destination", route["id"], str(destination))
        for link_no in route.get("link_sequence_vissim_nos", []):
            if link_no not in network_link_nos:
                issue(errors, "dangling_route_link", route["id"], str(link_no))

    for operator in manifest.get("observation_operators", []):
        kind = operator.get("kind")
        if kind == "data_collection_point":
            ref = dict(operator.get("lane_ref", {}))
            ref["position_m"] = operator.get("position_m")
            validate_lane_ref(ref, operator["id"], "lane_ref")
        elif kind == "queue_counter":
            if operator.get("link_no") not in network_link_nos:
                issue(errors, "dangling_observation_link", operator["id"], str(operator.get("link_no")))
            else:
                link = network_by_no[str(operator["link_no"])]
                if not (-_POSITION_EPS <= float(operator.get("position_m", 0.0)) <= float(link["length_m"]) + _POSITION_EPS):
                    issue(errors, "position_out_of_range", operator["id"], str(operator.get("position_m")))
        elif kind == "travel_time_measurement":
            for endpoint in (operator.get("start"), operator.get("end")):
                if endpoint is None or endpoint.get("link_no") not in network_link_nos:
                    issue(errors, "dangling_observation_link", operator["id"], str(endpoint))
                else:
                    link = network_by_no[str(endpoint["link_no"])]
                    if not (-_POSITION_EPS <= float(endpoint.get("position_m", 0.0)) <= float(link["length_m"]) + _POSITION_EPS):
                        issue(errors, "position_out_of_range", operator["id"], str(endpoint))

    expected_hash = canonical_json_sha256(_topology_hash_payload(manifest))
    if manifest.get("topology_hash") not in {None, expected_hash}:
        issue(errors, "topology_hash_mismatch", "manifest", f"expected {expected_hash}")
    errors.sort(key=lambda item: (item["code"], item["entity_id"], item["detail"]))
    warnings.sort(key=lambda item: (item["code"], item["entity_id"], item["detail"]))
    return {
        "valid": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "road_links": len(manifest.get("links", [])),
            "connector_links": len(manifest.get("connectors", [])),
            "lane_groups": len(manifest.get("lane_groups", [])),
            "cells": len(manifest.get("cells", [])),
            "signal_controllers": len(manifest.get("signal_controllers", [])),
            "signal_groups": len(manifest.get("signal_groups", [])),
            "signal_heads": len(manifest.get("signal_heads", [])),
            "vehicle_inputs": len(manifest.get("vehicle_inputs", [])),
            "routes": len(manifest.get("routes", [])),
            "observation_operators": len(manifest.get("observation_operators", [])),
            "freeway_interface_candidates": len(manifest.get("freeway_interface_candidates", [])),
            "influence_subgraphs": len(manifest.get("influence_subgraphs", [])),
        },
    }
