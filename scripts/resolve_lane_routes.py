"""Compile deterministic executable lane-path proofs for VISSIM static routes."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import math
from pathlib import Path
import sys
from typing import Any
import xml.etree.ElementTree as ET


SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from build_vissim_lane_graph import (  # noqa: E402
    atomic_write_json,
    behavioral_source_hashes,
    load_graph,
    validate_lane_graph_artifact,
)


REPO_ROOT = SCRIPT_ROOT.parent
PLANT_ROOT = REPO_ROOT / "plant"
if str(PLANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PLANT_ROOT))

from src.vissim_strict.topology import (  # noqa: E402
    CANONICAL_JSON_VERSION,
    canonical_json_sha256,
)


SCHEMA_VERSION = "lane-route-proofs-v2.1"
COMMAND_VERSION = "resolve-lane-routes/2.1.3"
POSITION_TOLERANCE_M = 1.0e-6
FLOW_TOLERANCE = 1.0e-9
UNITS = {
    "length": "m",
    "position": "m",
    "flow_support_time": "ms",
    "relative_flow": "dimensionless weight",
    "normalized_share": "fraction",
}
DOWNSTREAM_CONSUMERS = [
    "rollout plant stock compiler",
    "projection and movement gates",
    "controller action gates",
]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _iter_tag(root: ET.Element, tag: str):
    return (item for item in root.iter() if _local_name(item.tag) == tag)


def _numeric_key(value: str | int | None) -> tuple[int, int | str]:
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, "" if value is None else str(value))


def _bool_attribute(raw: str | None, default: bool = True) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes"}


def _attributes(element: ET.Element) -> dict[str, str]:
    return {key: element.attrib[key] for key in sorted(element.attrib)}


def parse_relative_flow(raw_value: str | None) -> dict[str, Any]:
    if raw_value is None:
        raise ValueError("missing relFlow attribute")
    raw = raw_value.strip()
    if not raw:
        return {
            "raw": raw_value,
            "attribute_present": True,
            "tokens": [],
            "encoding_prefix_tokens": [],
            "defaulted": True,
            "default_reason": "empty_relFlow_means_1.0",
            "supports": [{"time_ms": 0.0, "time_raw": None, "value": 1.0, "value_raw": None}],
        }
    tokens = raw.split()
    if len(tokens) == 1 and ":" not in tokens[0]:
        value = float(tokens[0])
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"invalid relFlow value {tokens[0]!r}")
        return {
            "raw": raw_value,
            "attribute_present": True,
            "tokens": tokens,
            "encoding_prefix_tokens": [],
            "defaulted": False,
            "supports": [
                {"time_ms": 0.0, "time_raw": None, "value": value, "value_raw": tokens[0]}
            ],
        }

    first_support = next((index for index, token in enumerate(tokens) if ":" in token), None)
    if first_support is None:
        raise ValueError(f"invalid relFlow representation {raw_value!r}")
    prefix = tokens[:first_support]
    if prefix != ["2"]:
        raise ValueError(f"unsupported VISSIM relFlow encoding prefix {prefix!r}")
    supports: list[dict[str, Any]] = []
    seen_times: set[float] = set()
    for token in tokens[first_support:]:
        if token.count(":") != 1:
            raise ValueError(f"invalid relFlow support token {token!r}")
        time_raw, value_raw = token.split(":", 1)
        time_ms = float(time_raw)
        value = float(value_raw)
        if not math.isfinite(time_ms) or time_ms < 0.0:
            raise ValueError(f"invalid relFlow support time {time_raw!r}")
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"invalid relFlow value {value_raw!r}")
        if time_ms in seen_times:
            raise ValueError(f"duplicate relFlow support time {time_raw!r}")
        seen_times.add(time_ms)
        supports.append(
            {
                "time_ms": time_ms,
                "time_raw": time_raw,
                "value": value,
                "value_raw": value_raw,
            }
        )
    supports.sort(key=lambda item: item["time_ms"])
    if not supports:
        raise ValueError(f"relFlow has no supports {raw_value!r}")
    return {
        "raw": raw_value,
        "attribute_present": True,
        "tokens": tokens,
        "encoding_prefix_tokens": prefix,
        "defaulted": False,
        "supports": supports,
    }


def parse_static_routes(inpx: str | Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = ET.parse(inpx).getroot()
    decisions: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    for decision in _iter_tag(root, "vehicleRoutingDecisionStatic"):
        decision_no = decision.get("no")
        if decision_no is None or not _bool_attribute(decision.get("active"), True):
            continue
        route_choice_method = decision.get("routeChoiceMeth", "STATIC")
        if route_choice_method.upper() != "STATIC":
            continue
        decision_id = f"routing-decision:{decision_no}"
        decision_routes: list[str] = []
        route_elements = sorted(
            list(_iter_tag(decision, "vehicleRouteStatic")),
            key=lambda item: _numeric_key(item.get("no")),
        )
        for route in route_elements:
            route_no = route.get("no")
            if route_no is None or not _bool_attribute(route.get("active"), True):
                continue
            route_id = f"route:{decision_no}:{route_no}"
            sequence = [
                {"key": reference.get("key", ""), "attributes": _attributes(reference)}
                for reference in _iter_tag(route, "intObjectRef")
            ]
            relative_flow_present = "relFlow" in route.attrib
            raw_flow = route.get("relFlow") if relative_flow_present else None
            record = {
                "id": route_id,
                "decision_id": decision_id,
                "decision_no": str(decision_no),
                "route_no": str(route_no),
                "name": route.get("name", ""),
                "decision_link_no": decision.get("link"),
                "decision_position_m": float(decision.get("pos", "0")),
                "destination_link_no": route.get("destLink"),
                "destination_position_m": float(route.get("destPos", "0")),
                "link_sequence_vissim_nos": [item["key"] for item in sequence],
                "relative_flow_raw": raw_flow,
                "relative_flow_attribute_present": relative_flow_present,
                "raw_route_evidence": {
                    "decision_attributes": _attributes(decision),
                    "route_attributes": _attributes(route),
                    "link_sequence": sequence,
                },
            }
            routes.append(record)
            decision_routes.append(route_id)
        decisions.append(
            {
                "id": decision_id,
                "decision_no": str(decision_no),
                "name": decision.get("name", ""),
                "link_no": decision.get("link"),
                "position_m": float(decision.get("pos", "0")),
                "route_ids": sorted(
                    decision_routes,
                    key=lambda value: _numeric_key(value.rsplit(":", 1)[1]),
                ),
                "source_attributes": _attributes(decision),
            }
        )
    decisions.sort(key=lambda item: _numeric_key(item["decision_no"]))
    routes.sort(key=lambda item: (_numeric_key(item["decision_no"]), _numeric_key(item["route_no"])))
    return decisions, routes


def _graph_index(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = {node["id"]: node for node in graph["nodes"]}
    object_lengths = {
        parent["id"]: float(parent["length_m"])
        for parent in [*graph["links"], *graph["connectors"]]
    }
    object_lanes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    object_by_no: dict[str, str] = {}
    for node in graph["nodes"]:
        object_lanes[node["object_id"]].append(node)
        previous = object_by_no.setdefault(str(node["link_no"]), node["object_id"])
        if previous != node["object_id"]:
            raise ValueError(f"ambiguous network object number {node['link_no']}")
    for lanes in object_lanes.values():
        lanes.sort(key=lambda item: item["lane_no"])
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    entries_by_target_object: dict[str, list[dict[str, Any]]] = defaultdict(list)
    entries_by_source_object: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in graph["edges"]:
        outgoing[edge["from_lane_id"]].append(edge)
        if edge["kind"] == "connector_entry":
            target_object_id = nodes[edge["to_lane_id"]]["object_id"]
            entries_by_target_object[target_object_id].append(edge)
            source_object_id = nodes[edge["from_lane_id"]]["object_id"]
            entries_by_source_object[source_object_id].append(edge)
    for edges in outgoing.values():
        edges.sort(
            key=lambda item: (
                _numeric_key(item["connector_no"]),
                item["connector_lane_no"],
                0 if item["kind"] == "connector_entry" else 1,
            )
        )
    for edges in entries_by_target_object.values():
        edges.sort(
            key=lambda item: (
                _numeric_key(item["connector_no"]), item["connector_lane_no"]
            )
        )
    for edges in entries_by_source_object.values():
        edges.sort(
            key=lambda item: (
                _numeric_key(item["connector_no"]), item["connector_lane_no"]
            )
        )
    heads: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for head in graph["signal_heads"]:
        heads[head["lane_id"]].append(head)
    for lane_heads in heads.values():
        lane_heads.sort(key=lambda item: (item["position_m"], _numeric_key(item["head_no"])))
    return {
        "nodes": nodes,
        "object_lanes": object_lanes,
        "object_by_no": object_by_no,
        "object_lengths": object_lengths,
        "outgoing": outgoing,
        "entries_by_target_object": entries_by_target_object,
        "entries_by_source_object": entries_by_source_object,
        "heads": heads,
    }


def _append_segment(state: dict[str, Any], end_position_m: float) -> dict[str, Any]:
    start = float(state["position_m"])
    end = float(end_position_m)
    if end < start - POSITION_TOLERANCE_M:
        raise ValueError("attempted reverse lane traversal")
    end = max(start, end)
    segment = {
        "lane_id": state["lane_id"],
        "start_position_m": start,
        "end_position_m": end,
        "length_m": end - start,
        "path_distance_start_m": float(state["physical_path_length_m"]),
    }
    return {
        **state,
        "position_m": end,
        "physical_path_length_m": float(state["physical_path_length_m"]) + end - start,
        "lane_segments": [*state["lane_segments"], segment],
    }


def _state_support_key(state: dict[str, Any], index: dict[str, Any]) -> tuple[Any, ...]:
    reached_stoplines = []
    for segment in state["lane_segments"]:
        for head in index["heads"].get(segment["lane_id"], []):
            if (
                head["position_m"] >= segment["start_position_m"] - POSITION_TOLERANCE_M
                and head["position_m"]
                <= segment["end_position_m"] + POSITION_TOLERANCE_M
            ):
                reached_stoplines.append(
                    (
                        segment["path_distance_start_m"]
                        + max(0.0, head["position_m"] - segment["start_position_m"]),
                        str(head["id"]),
                    )
                )
    first_stopline = min(reached_stoplines) if reached_stoplines else (math.inf, "")
    return (
        state["lane_ids"][0],
        state["lane_id"],
        state["position_m"],
        state["physical_path_length_m"],
        first_stopline,
    )


def _stable_state_dedupe(
    states: list[dict[str, Any]], index: dict[str, Any]
) -> list[dict[str, Any]]:
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for state in states:
        unique.setdefault(_state_support_key(state, index), state)
    return [unique[key] for key in sorted(unique)]


def _transition_to_object(
    states: list[dict[str, Any]], target_object_id: str, index: dict[str, Any]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    nodes = index["nodes"]
    for state in states:
        current_node = nodes[state["lane_id"]]
        if current_node.get("closed", False):
            continue
        if current_node["object_id"] == target_object_id:
            result.append(state)
            continue
        state_result: list[dict[str, Any]] = []
        for edge in index["outgoing"].get(state["lane_id"], []):
            target_node = nodes[edge["to_lane_id"]]
            if target_node["object_id"] != target_object_id:
                continue
            if target_node.get("closed", False):
                continue
            if edge["from_position_m"] < state["position_m"] - POSITION_TOLERANCE_M:
                continue
            advanced = _append_segment(state, float(edge["from_position_m"]))
            state_result.append(
                {
                    **advanced,
                    "lane_id": edge["to_lane_id"],
                    "position_m": float(edge["to_position_m"]),
                    "lane_ids": [*advanced["lane_ids"], edge["to_lane_id"]],
                    "edge_ids": [*advanced["edge_ids"], edge["id"]],
                }
            )
        if current_node["object_kind"] == "link":
            for edge in index["entries_by_target_object"].get(target_object_id, []):
                source_lane = nodes[edge["from_lane_id"]]
                target_lane = nodes[edge["to_lane_id"]]
                available_distance = float(edge["from_position_m"]) - float(
                    state["position_m"]
                )
                if (
                    source_lane["object_id"] != current_node["object_id"]
                    or source_lane.get("closed", False)
                    or target_lane.get("closed", False)
                    or source_lane["id"] == state["lane_id"]
                    or available_distance <= POSITION_TOLERANCE_M
                ):
                    continue
                changed = {
                    **state,
                    "lane_id": source_lane["id"],
                    "lane_ids": [*state["lane_ids"], source_lane["id"]],
                    "lane_change_events": [
                        *state["lane_change_events"],
                        {
                            "object_id": current_node["object_id"],
                            "from_lane_id": state["lane_id"],
                            "to_lane_id": source_lane["id"],
                            "start_position_m": state["position_m"],
                            "connector_position_m": edge["from_position_m"],
                            "available_distance_m": available_distance,
                            "basis": "forced_by_static_route_connector_lane_range",
                            "canonical_evidence": {
                                "entry_edge_id": edge["id"],
                                "source_lane_id": source_lane["id"],
                                "source_position_m": edge["from_position_m"],
                            },
                        },
                    ],
                }
                advanced = _append_segment(changed, float(edge["from_position_m"]))
                state_result.append(
                    {
                        **advanced,
                        "lane_id": edge["to_lane_id"],
                        "position_m": float(edge["to_position_m"]),
                        "lane_ids": [*advanced["lane_ids"], edge["to_lane_id"]],
                        "edge_ids": [*advanced["edge_ids"], edge["id"]],
                    }
                )
        result.extend(state_result)

    return _stable_state_dedupe(result, index)


def _take_search_edge(
    state: dict[str, Any], edge: dict[str, Any], index: dict[str, Any]
) -> dict[str, Any] | None:
    nodes = index["nodes"]
    source_lane = nodes[edge["from_lane_id"]]
    current_node = nodes[state["lane_id"]]
    target_lane = nodes[edge["to_lane_id"]]
    if (
        current_node.get("closed", False)
        or source_lane.get("closed", False)
        or target_lane.get("closed", False)
        or source_lane["object_id"] != current_node["object_id"]
    ):
        return None
    available_distance = float(edge["from_position_m"]) - float(state["position_m"])
    if available_distance < -POSITION_TOLERANCE_M:
        return None
    working = state
    if source_lane["id"] != state["lane_id"]:
        if (
            current_node["object_kind"] != "link"
            or available_distance <= POSITION_TOLERANCE_M
        ):
            return None
        working = {
            **state,
            "lane_id": source_lane["id"],
            "lane_ids": [*state["lane_ids"], source_lane["id"]],
            "lane_change_events": [
                *state["lane_change_events"],
                {
                    "object_id": current_node["object_id"],
                    "from_lane_id": state["lane_id"],
                    "to_lane_id": source_lane["id"],
                    "start_position_m": state["position_m"],
                    "connector_position_m": edge["from_position_m"],
                    "available_distance_m": available_distance,
                    "basis": "directed_waypoint_reachability",
                    "canonical_evidence": {
                        "entry_edge_id": edge["id"],
                        "source_lane_id": source_lane["id"],
                        "source_position_m": edge["from_position_m"],
                    },
                },
            ],
        }
    advanced = _append_segment(working, float(edge["from_position_m"]))
    return {
        **advanced,
        "lane_id": edge["to_lane_id"],
        "position_m": float(edge["to_position_m"]),
        "lane_ids": [*advanced["lane_ids"], edge["to_lane_id"]],
        "edge_ids": [*advanced["edge_ids"], edge["id"]],
    }


def _advance_to_waypoint(
    states: list[dict[str, Any]],
    target_object_id: str,
    index: dict[str, Any],
    *,
    dedupe_support_states: bool,
) -> list[dict[str, Any]]:
    completed: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for state in states:
        adjacent = _transition_to_object([state], target_object_id, index)
        if adjacent:
            completed.extend(adjacent)
        else:
            unresolved.append(state)
    stack: list[tuple[dict[str, Any], frozenset[tuple[str, float]]]] = [
        (state, frozenset({(state["lane_id"], round(float(state["position_m"]), 9))}))
        for state in reversed(unresolved)
    ]
    nodes = index["nodes"]
    while stack:
        state, visited = stack.pop()
        current_node = nodes[state["lane_id"]]
        if current_node["object_kind"] == "link":
            candidate_edges = index["entries_by_source_object"].get(
                current_node["object_id"], []
            )
        else:
            candidate_edges = index["outgoing"].get(state["lane_id"], [])
        for edge in candidate_edges:
            advanced = _take_search_edge(state, edge, index)
            if advanced is None:
                continue
            target_node = nodes[advanced["lane_id"]]
            if target_node["object_id"] == target_object_id:
                completed.append(advanced)
                continue
            signature = (
                advanced["lane_id"], round(float(advanced["position_m"]), 9)
            )
            if signature in visited:
                continue
            stack.append((advanced, visited | {signature}))

    if dedupe_support_states:
        return _stable_state_dedupe(completed, index)
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for state in completed:
        key = (tuple(state["lane_ids"]), tuple(state["edge_ids"]))
        unique[key] = state
    return [unique[key] for key in sorted(unique)]


def _first_downstream(
    state: dict[str, Any], index: dict[str, Any], route: dict[str, Any]
) -> dict[str, Any]:
    candidates: list[tuple[float, tuple[int, int | str], dict[str, Any]]] = []
    for segment in state["lane_segments"]:
        for head in index["heads"].get(segment["lane_id"], []):
            position = float(head["position_m"])
            if (
                position >= segment["start_position_m"] - POSITION_TOLERANCE_M
                and position <= segment["end_position_m"] + POSITION_TOLERANCE_M
            ):
                distance = segment["path_distance_start_m"] + max(
                    0.0, position - segment["start_position_m"]
                )
                candidates.append((distance, _numeric_key(head["head_no"]), head))
    if candidates:
        distance, _, head = min(candidates, key=lambda item: (item[0], item[1]))
        return {
            "kind": "signal_head_stopline",
            "distance_from_decision_m": distance,
            "signal_head_id": head["id"],
            "signal_controller_no": head["signal_controller_no"],
            "signal_group_no": head["signal_group_no"],
            "head_no": head["head_no"],
            "lane_id": head["lane_id"],
            "position_m": head["position_m"],
        }
    return {
        "kind": "terminal",
        "distance_from_decision_m": state["physical_path_length_m"],
        "lane_id": state["lane_id"],
        "link_no": route["destination_link_no"],
        "position_m": route["destination_position_m"],
    }


def resolve_route_paths(route: dict[str, Any], graph: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    index = _graph_index(graph)
    object_by_no = index["object_by_no"]
    decision_object = object_by_no.get(str(route["decision_link_no"]))
    destination_object = object_by_no.get(str(route["destination_link_no"]))
    if decision_object is None:
        return [], f"unknown decision link {route['decision_link_no']}"
    if destination_object is None:
        return [], f"unknown destination link {route['destination_link_no']}"
    sequence_nos = [
        str(route["decision_link_no"]),
        *[str(value) for value in route["link_sequence_vissim_nos"]],
        str(route["destination_link_no"]),
    ]
    unknown = [value for value in sequence_nos if value not in object_by_no]
    if unknown:
        return [], f"unknown explicit route objects {unknown}"

    start_position = float(route["decision_position_m"])
    decision_length = index["object_lengths"][decision_object]
    start_lanes = [
        lane for lane in index["object_lanes"][decision_object] if not lane.get("closed", False)
    ]
    states: list[dict[str, Any]] = []
    for lane in start_lanes:
        if (
            start_position < -POSITION_TOLERANCE_M
            or start_position > decision_length + POSITION_TOLERANCE_M
        ):
            continue
        states.append(
            {
                "lane_id": lane["id"],
                "position_m": min(decision_length, max(0.0, start_position)),
                "lane_ids": [lane["id"]],
                "edge_ids": [],
                "lane_segments": [],
                "lane_change_events": [],
                "physical_path_length_m": 0.0,
            }
        )
    if not states:
        return [], "no open start lane contains the decision position"

    remaining_sequence = sequence_nos[1:]
    for sequence_index, sequence_no in enumerate(remaining_sequence):
        target_object = object_by_no[sequence_no]
        states = _advance_to_waypoint(
            states,
            target_object,
            index,
            dedupe_support_states=sequence_index < len(remaining_sequence) - 1,
        )
        if not states:
            return [], f"no forward exact-lane transition to explicit object {sequence_no}"

    terminal_position = float(route["destination_position_m"])
    destination_length = index["object_lengths"][destination_object]
    completed: list[dict[str, Any]] = []
    for state in states:
        terminal_node = index["nodes"][state["lane_id"]]
        if (
            terminal_node["object_id"] != destination_object
            or terminal_node.get("closed", False)
        ):
            continue
        if terminal_position < state["position_m"] - POSITION_TOLERANCE_M:
            continue
        if terminal_position > destination_length + POSITION_TOLERANCE_M:
            continue
        advanced = _append_segment(
            state, min(destination_length, max(0.0, terminal_position))
        )
        completed.append(
            {
                "start_lane_id": advanced["lane_ids"][0],
                "terminal_lane_id": advanced["lane_id"],
                "terminal_position_m": terminal_position,
                "lane_ids": advanced["lane_ids"],
                "traversed_edge_ids": advanced["edge_ids"],
                "lane_segments": advanced["lane_segments"],
                "lane_change_events": advanced["lane_change_events"],
                "physical_path_length_m": advanced["physical_path_length_m"],
                "first_downstream_stopline_or_terminal": _first_downstream(advanced, index, route),
            }
        )
    completed.sort(
        key=lambda item: (
            _numeric_key(item["terminal_lane_id"].split(":")[1]),
            int(item["terminal_lane_id"].split(":")[2]),
            tuple(item["lane_ids"]),
            tuple(item["traversed_edge_ids"]),
        )
    )
    if not completed:
        return [], "destination position is upstream or outside all executable terminal lanes"
    return completed, None


def _flow_at(flow: dict[str, Any], time_ms: float) -> float:
    supports = flow["supports"]
    eligible = [item for item in supports if item["time_ms"] <= time_ms]
    if eligible:
        return float(eligible[-1]["value"])
    return float(supports[0]["value"])


def _command_hashes() -> dict[str, str]:
    return behavioral_source_hashes([Path(__file__).resolve()])


def semantic_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": artifact["schema_version"],
        "graph_semantic_sha256": artifact["source"]["graph_semantic_sha256"],
        "routing_decisions": artifact["routing_decisions"],
        "routes": artifact["routes"],
        "proofs": artifact["proofs"],
    }


def compile_route_proofs(
    inpx: str | Path, graph: dict[str, Any]
) -> dict[str, Any]:
    inpx_path = Path(inpx).resolve()
    input_sha256 = hashlib.sha256(inpx_path.read_bytes()).hexdigest()
    decisions, routes = parse_static_routes(inpx_path)
    graph_failures = validate_lane_graph_artifact(graph)
    reasons: list[dict[str, Any]] = list(graph_failures)
    if graph.get("source", {}).get("input_sha256") != input_sha256:
        reasons.append(
            {
                "code": "lane_graph_input_hash_mismatch",
                "entity_id": "lane-graph",
                "detail": {
                    "graph_input_sha256": graph.get("source", {}).get("input_sha256"),
                    "route_input_sha256": input_sha256,
                },
            }
        )
    graph_usable = not reasons
    flows: dict[str, dict[str, Any]] = {}
    paths_by_route: dict[str, list[dict[str, Any]]] = {}
    for route in routes:
        try:
            flows[route["id"]] = parse_relative_flow(route["relative_flow_raw"])
        except (ValueError, OverflowError) as exc:
            reasons.append(
                {"code": "invalid_relative_flow", "entity_id": route["id"], "detail": str(exc)}
            )
            continue
        if not graph_usable:
            paths_by_route[route["id"]] = []
            continue
        paths, error = resolve_route_paths(route, graph)
        paths_by_route[route["id"]] = paths
        if error is not None:
            reasons.append(
                {"code": "unresolved_route", "entity_id": route["id"], "detail": error}
            )

    normalized: dict[str, list[dict[str, Any]]] = defaultdict(list)
    max_share_error = 0.0
    for decision in decisions:
        valid_route_ids = [route_id for route_id in decision["route_ids"] if route_id in flows]
        support_times = sorted(
            {
                support["time_ms"]
                for route_id in valid_route_ids
                for support in flows[route_id]["supports"]
            }
        )
        for time_ms in support_times:
            values = {route_id: _flow_at(flows[route_id], time_ms) for route_id in valid_route_ids}
            total = math.fsum(values.values())
            if not math.isfinite(total) or total <= 0.0:
                reasons.append(
                    {
                        "code": "invalid_decision_flow_total",
                        "entity_id": decision["id"],
                        "detail": {"time_ms": time_ms, "total": total},
                    }
                )
                continue
            shares = {route_id: value / total for route_id, value in values.items()}
            share_error = abs(math.fsum(shares.values()) - 1.0)
            max_share_error = max(max_share_error, share_error)
            if share_error > FLOW_TOLERANCE:
                reasons.append(
                    {
                        "code": "normalized_flow_share_error",
                        "entity_id": decision["id"],
                        "detail": {"time_ms": time_ms, "error": share_error},
                    }
                )
            for route_id in valid_route_ids:
                normalized[route_id].append(
                    {
                        "time_ms": time_ms,
                        "relative_flow": values[route_id],
                        "decision_relative_flow_total": total,
                        "normalized_route_share": shares[route_id],
                    }
                )

    proofs: list[dict[str, Any]] = []
    route_records: list[dict[str, Any]] = []
    for route in routes:
        route_paths = paths_by_route.get(route["id"], [])
        flow = flows.get(route["id"])
        route_records.append(
            {
                **route,
                "relative_flow": flow,
                "normalized_flow_supports": normalized.get(route["id"], []),
                "executable_lane_path_count": len(route_paths),
                "resolution_status": "PASS" if route_paths else "FAIL",
            }
        )
        if not route_paths:
            continue
        path_share = 1.0 / len(route_paths)
        for path_index, path in enumerate(route_paths, 1):
            proof_supports = [
                {
                    **support,
                    "normalized_path_share_within_route": path_share,
                    "normalized_flow_path_share": support["normalized_route_share"] * path_share,
                }
                for support in normalized.get(route["id"], [])
            ]
            proofs.append(
                {
                    "id": f"proof:{route['decision_no']}:{route['route_no']}:{path_index}",
                    "route_id": route["id"],
                    "decision_no": route["decision_no"],
                    "route_no": route["route_no"],
                    "path_index": path_index,
                    "path_share_basis": "equal_share_without_lane_demand_evidence",
                    "flow_path_shares": proof_supports,
                    **path,
                }
            )

    proofs.sort(
        key=lambda item: (
            _numeric_key(item["decision_no"]),
            _numeric_key(item["route_no"]),
            item["path_index"],
        )
    )
    proof_share_totals: dict[tuple[str, float], list[float]] = defaultdict(list)
    for proof in proofs:
        for support in proof["flow_path_shares"]:
            proof_share_totals[(proof["decision_no"], support["time_ms"])].append(
                support["normalized_flow_path_share"]
            )
    max_path_share_error = max(
        (
            abs(math.fsum(shares) - 1.0)
            for shares in proof_share_totals.values()
        ),
        default=0.0,
    )
    if max_path_share_error > FLOW_TOLERANCE:
        reasons.append(
            {
                "code": "normalized_path_share_error",
                "entity_id": "route-proofs",
                "detail": max_path_share_error,
            }
        )
    max_share_error = max(max_share_error, max_path_share_error)
    unresolved_routes = sum(not paths_by_route.get(route["id"]) for route in routes)
    required_edge_ids = {
        edge_id
        for paths in paths_by_route.values()
        for path in paths
        for edge_id in path["traversed_edge_ids"]
    }
    required_connector_lanes = {
        edge_id.rsplit(":", 1)[0]
        for edge_id in required_edge_ids
        if edge_id.endswith(":entry")
    }
    graph_coverage = float(
        graph.get("production_gates", {}).get("executable_connector_path_coverage", 0.0)
    )
    if graph_coverage < 1.0 - FLOW_TOLERANCE:
        reasons.append(
            {
                "code": "incomplete_executable_connector_path_coverage",
                "entity_id": "lane-graph",
                "detail": graph_coverage,
            }
        )

    source_hashes = _command_hashes()
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "canonical_json_version": CANONICAL_JSON_VERSION,
        "source": {
            "inpx_path": inpx_path.name,
            "input_sha256": input_sha256,
            "graph_schema_version": graph.get("schema_version"),
            "graph_semantic_sha256": graph.get("semantic_sha256"),
            "graph_input_sha256": graph.get("source", {}).get("input_sha256"),
        },
        "command": {
            "version": COMMAND_VERSION,
            "source_sha256": source_hashes,
            "command_hash": canonical_json_sha256(source_hashes),
            "semantic_hash_scope": "schema_version, graph semantic hash, decisions, routes, proofs",
        },
        "status": "FAIL" if reasons else "PASS",
        "reasons": sorted(reasons, key=lambda item: (item["code"], item["entity_id"])),
        "sample_dimensions": {
            "active_static_routing_decisions": len(decisions),
            "active_static_routes": len(routes),
            "executable_lane_path_proofs": len(proofs),
            "required_connector_lanes": len(required_connector_lanes),
        },
        "units": UNITS,
        "downstream_consumers": DOWNSTREAM_CONSUMERS,
        "production_gates": {
            "unresolved_routes": unresolved_routes,
            "reverse_synthetic_edges": graph.get("production_gates", {}).get(
                "reverse_synthetic_edges"
            ),
            "executable_connector_path_coverage": graph_coverage,
            "maximum_normalized_flow_share_error": max_share_error,
        },
        "routing_decisions": decisions,
        "routes": route_records,
        "proofs": proofs,
    }
    artifact["semantic_sha256"] = canonical_json_sha256(semantic_payload(artifact))
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inpx", required=True, type=Path)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    artifact = compile_route_proofs(args.inpx, load_graph(args.graph))
    atomic_write_json(args.output, artifact)
    gates = artifact["production_gates"]
    print(
        f"status={artifact['status']} routes={len(artifact['routes'])} "
        f"proofs={len(artifact['proofs'])} unresolved={gates['unresolved_routes']} "
        f"flow_error={gates['maximum_normalized_flow_share_error']:.3g} "
        f"hash={artifact['semantic_sha256']}"
    )
    return 0 if artifact["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
