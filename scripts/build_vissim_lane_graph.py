"""Compile the canonical directed VISSIM lane graph artifact."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
PLANT_ROOT = REPO_ROOT / "plant"
if str(PLANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PLANT_ROOT))

from src.vissim_strict.compiler import compile_network  # noqa: E402
from src.vissim_strict.topology import (  # noqa: E402
    CANONICAL_JSON_VERSION,
    canonical_json_sha256,
    canonical_json_text,
)


SCHEMA_VERSION = "vissim-lane-graph-v2.1"
COMMAND_VERSION = "build-vissim-lane-graph/2.1.3"
REQUIRED_PRODUCTION_GATES = (
    "unresolved_connector_lane_mappings",
    "reverse_synthetic_edges",
    "executable_connector_path_count",
    "executable_connector_path_coverage",
)
UNITS = {
    "length": "m",
    "position": "m",
    "coordinate": "m",
    "lane_number": "VISSIM one-based lane number",
}
DOWNSTREAM_CONSUMERS = [
    "resolve_lane_routes.py",
    "rollout plant stock compiler",
    "projection and movement gates",
]


def _numeric_key(value: str | int | None) -> tuple[int, int | str]:
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, "" if value is None else str(value))


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _canonical_positive_integer_identity(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if not isinstance(value, str) or not value or not value.isascii() or not value.isdigit():
        return None
    normalized = int(value)
    if normalized <= 0 or value != str(normalized):
        return None
    return normalized


def _point(point: dict[str, Any] | None) -> dict[str, float] | None:
    if point is None:
        return None
    return {
        "x_m": float(point["x_m"]),
        "y_m": float(point["y_m"]),
        "z_m": float(point["z_m"]),
    }


def behavioral_source_hashes(additional_paths: Iterable[Path] = ()) -> dict[str, str]:
    strict_sources = (PLANT_ROOT / "src" / "vissim_strict").rglob("*.py")
    paths = {
        Path(__file__).resolve(),
        (PLANT_ROOT / "src" / "__init__.py").resolve(),
        *(path.resolve() for path in strict_sources),
        *(Path(path).resolve() for path in additional_paths),
    }
    return {
        path.relative_to(REPO_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths, key=lambda item: item.as_posix())
    }


def _link_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (_numeric_key(item.get("link_no")),)


def _node_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (_numeric_key(item.get("link_no")), int(item.get("lane_no", -1)))


def _connector_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (_numeric_key(item.get("connector_no")),)


def _mapping_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    lane_id = str(item.get("connector_lane_id", ""))
    return (_numeric_key(lane_id.rsplit(":", 1)[-1]), lane_id)


def _edge_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _numeric_key(item.get("connector_no")),
        int(item.get("connector_lane_no", -1)),
        0 if item.get("kind") == "connector_entry" else 1,
        str(item.get("id", "")),
    )


def _head_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _numeric_key(item.get("link_no")),
        -1 if item.get("lane_no") is None else int(item["lane_no"]),
        float("inf") if item.get("position_m") is None else float(item["position_m"]),
        _numeric_key(item.get("signal_controller_no")),
        _numeric_key(item.get("signal_group_no")),
        _numeric_key(item.get("head_no")),
    )


def _network_objects(manifest: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for link in manifest.get("links", []):
        yield "link", link
    for connector in manifest.get("connectors", []):
        yield "connector", connector


def _lane_nodes(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for object_kind, item in _network_objects(manifest):
        geometry = [_point(point) for point in item.get("geometry", [])]
        source_coordinate = geometry[0] if geometry else None
        destination_coordinate = geometry[-1] if geometry else None
        for lane in item.get("lanes", []):
            nodes.append(
                {
                    "id": str(lane["id"]),
                    "object_id": f"{object_kind}:{item['vissim_no']}",
                    "object_kind": object_kind,
                    "link_no": str(item["vissim_no"]),
                    "lane_no": int(lane["lane_no"]),
                    "name": str(item.get("name", "")),
                    "length_m": float(item["length_m"]),
                    "width_m": float(lane.get("width_m", 0.0)),
                    "closed": bool(lane.get("closed", False)),
                    "source_coordinate": source_coordinate,
                    "destination_coordinate": destination_coordinate,
                }
            )
    return sorted(nodes, key=_node_sort_key)


def _parent_lane_records(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(lane["id"]),
            "lane_no": int(lane["lane_no"]),
            "width_m": float(lane.get("width_m", 0.0)),
            "closed": bool(lane.get("closed", False)),
        }
        for lane in sorted(item.get("lanes", []), key=lambda lane: int(lane["lane_no"]))
    ]


def _link_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for link in manifest.get("links", []):
        geometry = [_point(point) for point in link.get("geometry", [])]
        lanes = _parent_lane_records(link)
        records.append(
            {
                "id": f"link:{link['vissim_no']}",
                "object_kind": "link",
                "link_no": str(link["vissim_no"]),
                "name": str(link.get("name", "")),
                "length_m": float(link["length_m"]),
                "lane_count": len(lanes),
                "lane_ids": [lane["id"] for lane in lanes],
                "lanes": lanes,
                "source_coordinate": geometry[0] if geometry else None,
                "destination_coordinate": geometry[-1] if geometry else None,
            }
        )
    return sorted(records, key=_link_sort_key)


def _connector_records(
    manifest: dict[str, Any], node_ids: set[str], reasons: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    connectors: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    expected_lane_ids: set[str] = set()
    invalid_lane_ids: set[str] = set()
    reverse_mapping_ids: list[str] = []
    for connector in sorted(
        manifest.get("connectors", []), key=lambda item: _numeric_key(item.get("vissim_no"))
    ):
        connector_no = str(connector["vissim_no"])
        connector_id = f"connector:{connector_no}"
        lane_count = int(connector.get("lane_count", 0))
        geometry = [_point(point) for point in connector.get("geometry", [])]
        expected_ids = [f"lane:{connector_no}:{lane_no}" for lane_no in range(1, lane_count + 1)]
        expected_lane_ids.update(expected_ids)
        declared_lanes = sorted(
            connector.get("lanes", []), key=lambda lane: int(lane.get("lane_no", -1))
        )
        declared_ids = [str(lane.get("id", "")) for lane in declared_lanes]
        declared_lane_nos = [int(lane.get("lane_no", -1)) for lane in declared_lanes]
        if declared_ids != expected_ids or declared_lane_nos != list(range(1, lane_count + 1)):
            invalid_lane_ids.update(expected_ids)
            reasons.append(
                {
                    "code": "connector_declared_lane_range_mismatch",
                    "entity_id": connector_id,
                    "detail": {
                        "lane_count": lane_count,
                        "expected_lane_ids": expected_ids,
                        "declared_lane_ids": declared_ids,
                        "declared_lane_nos": declared_lane_nos,
                    },
                }
            )

        from_endpoint = connector.get("from_endpoint", {})
        to_endpoint = connector.get("to_endpoint", {})
        endpoint_values = (
            from_endpoint.get("link_no"),
            from_endpoint.get("lane_no"),
            from_endpoint.get("position_m"),
            to_endpoint.get("link_no"),
            to_endpoint.get("lane_no"),
            to_endpoint.get("position_m"),
        )
        endpoints_valid = (
            all(value is not None for value in endpoint_values)
            and _finite(from_endpoint.get("position_m"))
            and _finite(to_endpoint.get("position_m"))
            and _finite(connector.get("length_m"))
        )
        if not endpoints_valid:
            invalid_lane_ids.update(expected_ids)
            reasons.append(
                {
                    "code": "invalid_connector_endpoint_evidence",
                    "entity_id": connector_id,
                    "detail": {
                        "from_endpoint": from_endpoint,
                        "to_endpoint": to_endpoint,
                        "length_m": connector.get("length_m"),
                    },
                }
            )

        raw_mappings = sorted(connector.get("lane_mapping", []), key=_mapping_sort_key)
        mappings: list[dict[str, Any]] = []
        mappings_by_lane: dict[str, list[dict[str, Any]]] = {}
        for mapping in raw_mappings:
            connector_lane_id = str(mapping["connector_lane_id"])
            from_lane_id = mapping.get("from_lane_id")
            to_lane_id = mapping.get("to_lane_id")
            record = {
                "connector_lane_id": connector_lane_id,
                "connector_lane_no": int(connector_lane_id.rsplit(":", 1)[1]),
                "from_lane_id": from_lane_id,
                "to_lane_id": to_lane_id,
            }
            mappings.append(record)
            mappings_by_lane.setdefault(connector_lane_id, []).append(record)

        extra_mapping_ids = sorted(set(mappings_by_lane) - set(expected_ids), key=_numeric_key)
        if extra_mapping_ids:
            reasons.append(
                {
                    "code": "unexpected_connector_lane_mapping",
                    "entity_id": connector_id,
                    "detail": extra_mapping_ids,
                }
            )

        for connector_lane_no, connector_lane_id in enumerate(expected_ids, 1):
            lane_mappings = mappings_by_lane.get(connector_lane_id, [])
            if len(lane_mappings) != 1:
                invalid_lane_ids.add(connector_lane_id)
                reasons.append(
                    {
                        "code": "connector_lane_mapping_not_one_to_one",
                        "entity_id": connector_lane_id,
                        "detail": {"mapping_count": len(lane_mappings)},
                    }
                )
                continue
            mapping = lane_mappings[0]
            from_lane_id = mapping["from_lane_id"]
            to_lane_id = mapping["to_lane_id"]
            if not endpoints_valid:
                continue
            expected_from_lane_id = (
                f"lane:{from_endpoint['link_no']}:"
                f"{int(from_endpoint['lane_no']) + connector_lane_no - 1}"
            )
            expected_to_lane_id = (
                f"lane:{to_endpoint['link_no']}:"
                f"{int(to_endpoint['lane_no']) + connector_lane_no - 1}"
            )
            if from_lane_id != expected_from_lane_id or to_lane_id != expected_to_lane_id:
                invalid_lane_ids.add(connector_lane_id)
                reversed_mapping = (
                    from_lane_id == expected_to_lane_id and to_lane_id == expected_from_lane_id
                )
                if reversed_mapping:
                    reverse_mapping_ids.append(connector_lane_id)
                reasons.append(
                    {
                        "code": (
                            "reversed_connector_lane_mapping"
                            if reversed_mapping
                            else "connector_lane_mapping_endpoint_mismatch"
                        ),
                        "entity_id": connector_lane_id,
                        "detail": {
                            "expected_from_lane_id": expected_from_lane_id,
                            "actual_from_lane_id": from_lane_id,
                            "expected_to_lane_id": expected_to_lane_id,
                            "actual_to_lane_id": to_lane_id,
                            "from_position_m": from_endpoint["position_m"],
                            "to_position_m": to_endpoint["position_m"],
                        },
                    }
                )
            missing = [
                lane_id
                for lane_id in (from_lane_id, connector_lane_id, to_lane_id)
                if lane_id not in node_ids
            ]
            if missing:
                invalid_lane_ids.add(connector_lane_id)
                reasons.append(
                    {
                        "code": "connector_lane_mapping_missing_node",
                        "entity_id": connector_lane_id,
                        "detail": missing,
                    }
                )
                continue
            common = {
                "connector_id": connector_id,
                "connector_no": connector_no,
                "connector_lane_no": connector_lane_no,
            }
            edges.extend(
                [
                    {
                        "id": f"edge:connector:{connector_no}:lane:{connector_lane_no}:entry",
                        "kind": "connector_entry",
                        "from_lane_id": from_lane_id,
                        "to_lane_id": connector_lane_id,
                        "from_position_m": float(connector["from_endpoint"]["position_m"]),
                        "to_position_m": 0.0,
                        **common,
                    },
                    {
                        "id": f"edge:connector:{connector_no}:lane:{connector_lane_no}:exit",
                        "kind": "connector_exit",
                        "from_lane_id": connector_lane_id,
                        "to_lane_id": to_lane_id,
                        "from_position_m": float(connector["length_m"]),
                        "to_position_m": float(connector["to_endpoint"]["position_m"]),
                        **common,
                    },
                ]
            )
        connectors.append(
            {
                "id": connector_id,
                "object_kind": "connector",
                "connector_no": connector_no,
                "name": str(connector.get("name", "")),
                "length_m": float(connector["length_m"]),
                "lane_count": lane_count,
                "lane_ids": [lane["id"] for lane in _parent_lane_records(connector)],
                "lanes": _parent_lane_records(connector),
                "from_link_no": from_endpoint.get("link_no"),
                "from_lane_no": from_endpoint.get("lane_no"),
                "from_position_m": from_endpoint.get("position_m"),
                "to_link_no": to_endpoint.get("link_no"),
                "to_lane_no": to_endpoint.get("lane_no"),
                "to_position_m": to_endpoint.get("position_m"),
                "source_coordinate": geometry[0] if geometry else None,
                "destination_coordinate": geometry[-1] if geometry else None,
                "lane_mapping": mappings,
            }
        )
    edges.sort(key=_edge_sort_key)
    return connectors, edges, {
        "expected_lane_ids": expected_lane_ids,
        "invalid_lane_ids": invalid_lane_ids,
        "reverse_mapping_ids": sorted(reverse_mapping_ids),
    }


def _signal_heads(
    manifest: dict[str, Any], node_ids: set[str], reasons: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for head in manifest.get("signal_heads", []):
        lane = head.get("lane_ref", {})
        group = head.get("signal_group_ref", {})
        record = {
            "id": str(head["id"]),
            "head_no": str(head["vissim_no"]),
            "name": str(head.get("name", "")),
            "signal_controller_no": group.get("controller_no"),
            "signal_group_no": group.get("sg_no"),
            "link_no": lane.get("link_no"),
            "lane_no": lane.get("lane_no"),
            "lane_id": lane.get("lane_id"),
            "position_m": head.get("position_m"),
            "raw_lane_reference": lane.get("raw", ""),
            "raw_signal_group_reference": group.get("raw", ""),
        }
        required = (
            record["signal_controller_no"],
            record["signal_group_no"],
            record["link_no"],
            record["lane_no"],
            record["lane_id"],
            record["position_m"],
        )
        if any(value is None for value in required) or not _finite(record["position_m"]):
            reasons.append(
                {
                    "code": "malformed_signal_head_reference",
                    "entity_id": record["id"],
                    "detail": record,
                }
            )
        elif record["lane_id"] not in node_ids:
            reasons.append(
                {
                    "code": "signal_head_lane_missing_from_graph",
                    "entity_id": record["id"],
                    "detail": record["lane_id"],
                }
            )
        result.append(record)
    return sorted(result, key=_head_sort_key)


def semantic_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": artifact["schema_version"],
        "links": artifact["links"],
        "nodes": artifact["nodes"],
        "edges": artifact["edges"],
        "connectors": artifact["connectors"],
        "signal_heads": artifact["signal_heads"],
    }


def validate_lane_graph_artifact(graph: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def fail(code: str, detail: Any) -> None:
        failures.append({"code": code, "entity_id": "lane-graph", "detail": detail})

    def duplicate_ids(field: str, values: list[dict[str, Any]]) -> None:
        counts: dict[str, int] = defaultdict(int)
        for value in values:
            counts[str(value.get("id"))] += 1
        duplicates = sorted(identifier for identifier, count in counts.items() if count != 1)
        if duplicates:
            fail("duplicate_lane_graph_id", {"field": field, "ids": duplicates})

    def valid_nonnegative(value: Any) -> bool:
        return _finite(value) and float(value) >= 0.0

    if graph.get("schema_version") != SCHEMA_VERSION:
        fail("invalid_lane_graph_schema", graph.get("schema_version"))
    if graph.get("canonical_json_version") != CANONICAL_JSON_VERSION:
        fail("invalid_lane_graph_canonical_json_version", graph.get("canonical_json_version"))
    if graph.get("status") != "PASS":
        fail("lane_graph_status_not_pass", graph.get("status"))
    if graph.get("reasons") != []:
        fail("lane_graph_reasons_not_empty", graph.get("reasons"))

    gates = graph.get("production_gates")
    if not isinstance(gates, dict):
        fail("missing_lane_graph_gate", list(REQUIRED_PRODUCTION_GATES))
        gates = {}
    missing_gates = [name for name in REQUIRED_PRODUCTION_GATES if name not in gates]
    if missing_gates:
        fail("missing_lane_graph_gate", missing_gates)

    collection_fields = ("links", "nodes", "edges", "connectors", "signal_heads")
    collections = {field: graph.get(field) for field in collection_fields}
    safe_collections = {
        field: values if isinstance(values, list) else []
        for field, values in collections.items()
    }
    order_errors: list[str] = []
    ordered_fields = (
        ("links", _link_sort_key),
        ("nodes", _node_sort_key),
        ("edges", _edge_sort_key),
        ("connectors", _connector_sort_key),
        ("signal_heads", _head_sort_key),
    )
    for field, key in ordered_fields:
        values = collections[field]
        if not isinstance(values, list) or values != sorted(values, key=key):
            order_errors.append(field)
    for connector in safe_collections["connectors"]:
        mappings = connector.get("lane_mapping")
        if not isinstance(mappings, list) or mappings != sorted(mappings, key=_mapping_sort_key):
            order_errors.append(f"{connector.get('id')}.lane_mapping")
    for parent in [*safe_collections["links"], *safe_collections["connectors"]]:
        lane_ids = parent.get("lane_ids")
        if not isinstance(lane_ids, list) or lane_ids != sorted(
            lane_ids, key=lambda lane_id: int(str(lane_id).rsplit(":", 1)[1])
        ):
            order_errors.append(f"{parent.get('id')}.lane_ids")
        lanes = parent.get("lanes")
        if not isinstance(lanes, list) or lanes != sorted(
            lanes, key=lambda lane: int(lane.get("lane_no", -1))
        ):
            order_errors.append(f"{parent.get('id')}.lanes")
    if order_errors:
        fail("noncanonical_lane_graph_order", order_errors)

    try:
        actual_hash = canonical_json_sha256(semantic_payload(graph))
    except (KeyError, TypeError, ValueError) as exc:
        fail("invalid_lane_graph_semantic_payload", str(exc))
        actual_hash = None
    if actual_hash is not None and graph.get("semantic_sha256") != actual_hash:
        fail(
            "graph_semantic_hash_mismatch",
            {"stored": graph.get("semantic_sha256"), "actual": actual_hash},
        )

    links = safe_collections["links"]
    nodes = safe_collections["nodes"]
    edges = safe_collections["edges"]
    connectors = safe_collections["connectors"]
    signal_heads = safe_collections["signal_heads"]
    for field, values in (
        ("links", links),
        ("nodes", nodes),
        ("edges", edges),
        ("connectors", connectors),
        ("signal_heads", signal_heads),
    ):
        duplicate_ids(field, values)

    nodes_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    edges_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        nodes_by_id[str(node.get("id"))].append(node)
    for edge in edges:
        edges_by_id[str(edge.get("id"))].append(edge)

    expected_nodes: dict[str, dict[str, Any]] = {}
    road_links_by_no: dict[str, dict[str, Any]] = {}
    expected_connector_lane_count = 0
    for object_kind, parents, number_field in (
        ("link", links, "link_no"),
        ("connector", connectors, "connector_no"),
    ):
        for parent in parents:
            number = str(parent.get(number_field))
            parent_id = f"{object_kind}:{number}"
            if parent.get("id") != parent_id or parent.get("object_kind") != object_kind:
                fail(
                    "invalid_lane_graph_parent",
                    {
                        "expected_id": parent_id,
                        "actual_id": parent.get("id"),
                        "expected_kind": object_kind,
                        "actual_kind": parent.get("object_kind"),
                    },
                )
            if not valid_nonnegative(parent.get("length_m")):
                fail(
                    "invalid_lane_graph_parent",
                    {"id": parent_id, "length_m": parent.get("length_m")},
                )
                continue
            if object_kind == "link":
                if number in road_links_by_no:
                    fail("duplicate_lane_graph_id", {"field": "link_no", "ids": [number]})
                road_links_by_no[number] = parent

            lane_count = parent.get("lane_count")
            if not isinstance(lane_count, int) or isinstance(lane_count, bool):
                fail(
                    "invalid_lane_graph_parent",
                    {"id": parent_id, "lane_count": lane_count},
                )
                continue
            if lane_count < 0:
                fail("invalid_lane_graph_parent", {"id": parent_id, "lane_count": lane_count})
                continue
            if object_kind == "connector":
                expected_connector_lane_count += lane_count
            expected_lane_ids = [
                f"lane:{number}:{lane_no}" for lane_no in range(1, lane_count + 1)
            ]
            parent_lanes = parent.get("lanes")
            if not isinstance(parent_lanes, list):
                parent_lanes = []
            actual_lane_ids = [str(lane.get("id")) for lane in parent_lanes]
            actual_lane_nos = [lane.get("lane_no") for lane in parent_lanes]
            if (
                parent.get("lane_ids") != expected_lane_ids
                or actual_lane_ids != expected_lane_ids
                or actual_lane_nos != list(range(1, lane_count + 1))
            ):
                fail(
                    "invalid_lane_graph_parent_lane_universe",
                    {
                        "id": parent_id,
                        "expected_lane_ids": expected_lane_ids,
                        "lane_ids": parent.get("lane_ids"),
                        "declared_lane_ids": actual_lane_ids,
                        "declared_lane_nos": actual_lane_nos,
                    },
                )
            for lane in parent_lanes:
                lane_id = str(lane.get("id"))
                if (
                    not valid_nonnegative(lane.get("width_m"))
                    or not isinstance(lane.get("closed"), bool)
                ):
                    fail(
                        "invalid_lane_graph_parent_lane_universe",
                        {
                            "id": parent_id,
                            "lane_id": lane_id,
                            "width_m": lane.get("width_m"),
                            "closed": lane.get("closed"),
                        },
                    )
                expected_nodes[lane_id] = {
                    "id": lane_id,
                    "object_id": parent_id,
                    "object_kind": object_kind,
                    "link_no": number,
                    "lane_no": lane.get("lane_no"),
                    "name": parent.get("name"),
                    "length_m": parent.get("length_m"),
                    "width_m": lane.get("width_m"),
                    "closed": lane.get("closed"),
                    "source_coordinate": parent.get("source_coordinate"),
                    "destination_coordinate": parent.get("destination_coordinate"),
                }

    if set(nodes_by_id) != set(expected_nodes) or len(nodes) != len(expected_nodes):
        fail(
            "lane_node_parent_mismatch",
            {
                "missing": sorted(set(expected_nodes) - set(nodes_by_id)),
                "orphan": sorted(set(nodes_by_id) - set(expected_nodes)),
                "expected_count": len(expected_nodes),
                "actual_count": len(nodes),
            },
        )
    for lane_id in sorted(set(nodes_by_id) | set(expected_nodes)):
        matches = nodes_by_id.get(lane_id, [])
        expected = expected_nodes.get(lane_id)
        if len(matches) != 1 or expected is None or any(
            matches[0].get(key) != value
            or key == "closed" and not isinstance(matches[0].get(key), bool)
            for key, value in expected.items()
        ):
            fail(
                "lane_node_parent_mismatch",
                {"lane_id": lane_id, "expected": expected, "actual": matches},
            )

    expected_edges: dict[str, dict[str, Any]] = {}
    for connector in connectors:
        connector_no = str(connector.get("connector_no"))
        connector_id = f"connector:{connector_no}"
        try:
            lane_count = int(connector["lane_count"])
            from_lane_no = int(connector["from_lane_no"])
            to_lane_no = int(connector["to_lane_no"])
            length_m = float(connector["length_m"])
            from_position_m = float(connector["from_position_m"])
            to_position_m = float(connector["to_position_m"])
            from_link_no = str(connector["from_link_no"])
            to_link_no = str(connector["to_link_no"])
        except (KeyError, TypeError, ValueError) as exc:
            fail("invalid_connector_endpoint_evidence", {"id": connector_id, "error": str(exc)})
            continue
        from_parent = road_links_by_no.get(from_link_no)
        to_parent = road_links_by_no.get(to_link_no)
        endpoint_errors: list[str] = []
        if from_parent is None:
            endpoint_errors.append(f"unknown from link {from_link_no}")
        if to_parent is None:
            endpoint_errors.append(f"unknown to link {to_link_no}")
        if not valid_nonnegative(length_m):
            endpoint_errors.append("invalid connector length")
        if (
            not valid_nonnegative(from_position_m)
            or from_parent is not None
            and from_position_m > float(from_parent["length_m"])
        ):
            endpoint_errors.append("invalid from position")
        if (
            not valid_nonnegative(to_position_m)
            or to_parent is not None
            and to_position_m > float(to_parent["length_m"])
        ):
            endpoint_errors.append("invalid to position")
        if endpoint_errors:
            fail(
                "invalid_connector_endpoint_evidence",
                {"id": connector_id, "errors": endpoint_errors},
            )
        mappings_by_lane: dict[str, list[dict[str, Any]]] = defaultdict(list)
        connector_mappings = connector.get("lane_mapping")
        if not isinstance(connector_mappings, list):
            connector_mappings = []
        for mapping in connector_mappings:
            mappings_by_lane[str(mapping.get("connector_lane_id"))].append(mapping)
        expected_lane_ids = {
            f"lane:{connector_no}:{lane_no}" for lane_no in range(1, lane_count + 1)
        }
        if set(mappings_by_lane) != expected_lane_ids:
            fail(
                "invalid_connector_mapping_universe",
                {
                    "id": connector_id,
                    "expected": sorted(expected_lane_ids),
                    "actual": sorted(mappings_by_lane),
                },
            )
        for lane_no in range(1, lane_count + 1):
            lane_id = f"lane:{connector_no}:{lane_no}"
            lane_nodes = nodes_by_id.get(lane_id, [])
            valid_node = (
                len(lane_nodes) == 1
                and lane_nodes[0].get("object_id") == connector_id
                and lane_nodes[0].get("object_kind") == "connector"
                and int(lane_nodes[0].get("lane_no", -1)) == lane_no
            )
            if not valid_node:
                fail("invalid_connector_lane_node", {"lane_id": lane_id, "nodes": lane_nodes})

            lane_mappings = mappings_by_lane.get(lane_id, [])
            expected_from_lane_id = f"lane:{from_link_no}:{from_lane_no + lane_no - 1}"
            expected_to_lane_id = f"lane:{to_link_no}:{to_lane_no + lane_no - 1}"
            valid_mapping = (
                len(lane_mappings) == 1
                and lane_mappings[0].get("connector_lane_no") == lane_no
                and lane_mappings[0].get("from_lane_id") == expected_from_lane_id
                and lane_mappings[0].get("to_lane_id") == expected_to_lane_id
            )
            if not valid_mapping:
                fail(
                    "invalid_connector_lane_mapping",
                    {
                        "lane_id": lane_id,
                        "expected_from_lane_id": expected_from_lane_id,
                        "expected_to_lane_id": expected_to_lane_id,
                        "mappings": lane_mappings,
                    },
                )

            lane_expected_edges = {
                f"edge:connector:{connector_no}:lane:{lane_no}:entry": {
                    "id": f"edge:connector:{connector_no}:lane:{lane_no}:entry",
                    "kind": "connector_entry",
                    "from_lane_id": expected_from_lane_id,
                    "to_lane_id": lane_id,
                    "from_position_m": from_position_m,
                    "to_position_m": 0.0,
                    "connector_id": connector_id,
                    "connector_no": connector_no,
                    "connector_lane_no": lane_no,
                },
                f"edge:connector:{connector_no}:lane:{lane_no}:exit": {
                    "id": f"edge:connector:{connector_no}:lane:{lane_no}:exit",
                    "kind": "connector_exit",
                    "from_lane_id": lane_id,
                    "to_lane_id": expected_to_lane_id,
                    "from_position_m": length_m,
                    "to_position_m": to_position_m,
                    "connector_id": connector_id,
                    "connector_no": connector_no,
                    "connector_lane_no": lane_no,
                },
            }
            for edge_id, expected in lane_expected_edges.items():
                expected_edges[edge_id] = expected
                matches = edges_by_id.get(edge_id, [])
                valid_edge = len(matches) == 1 and all(
                    matches[0].get(key) == value for key, value in expected.items()
                )
                if not valid_edge:
                    fail(
                        "invalid_connector_edge_evidence",
                        {"edge_id": edge_id, "expected": expected, "actual": matches},
                    )
            incoming = [edge for edge in edges if edge.get("to_lane_id") == lane_id]
            outgoing = [edge for edge in edges if edge.get("from_lane_id") == lane_id]
            touching = [
                edge
                for edge in edges
                if edge.get("from_lane_id") == lane_id or edge.get("to_lane_id") == lane_id
            ]
            if len(incoming) != 1 or len(outgoing) != 1 or len(touching) != 2:
                fail(
                    "invalid_connector_node_degree",
                    {
                        "lane_id": lane_id,
                        "incoming": [edge.get("id") for edge in incoming],
                        "outgoing": [edge.get("id") for edge in outgoing],
                        "touching": [edge.get("id") for edge in touching],
                    },
                )

    if set(edges_by_id) != set(expected_edges) or len(edges) != len(expected_edges):
        fail(
            "invalid_connector_edge_evidence",
            {
                "missing": sorted(set(expected_edges) - set(edges_by_id)),
                "unexpected": sorted(set(edges_by_id) - set(expected_edges)),
                "expected_count": len(expected_edges),
                "actual_count": len(edges),
            },
        )
    for edge in edges:
        edge_errors: list[str] = []
        from_lane_id = str(edge.get("from_lane_id"))
        to_lane_id = str(edge.get("to_lane_id"))
        from_node = expected_nodes.get(from_lane_id)
        to_node = expected_nodes.get(to_lane_id)
        if from_node is None:
            edge_errors.append(f"unknown from endpoint {from_lane_id}")
        if to_node is None:
            edge_errors.append(f"unknown to endpoint {to_lane_id}")
        if edge.get("kind") not in {"connector_entry", "connector_exit"}:
            edge_errors.append(f"unsupported kind {edge.get('kind')}")
        for position_field, node in (
            ("from_position_m", from_node),
            ("to_position_m", to_node),
        ):
            position = edge.get(position_field)
            if not valid_nonnegative(position):
                edge_errors.append(f"invalid {position_field}")
            elif node is not None and float(position) > float(node["length_m"]):
                edge_errors.append(f"{position_field} beyond parent length")
        if from_node is not None and to_node is not None:
            orientation = (from_node["object_kind"], to_node["object_kind"])
            expected_orientation = (
                ("link", "connector")
                if edge.get("kind") == "connector_entry"
                else ("connector", "link")
            )
            if orientation != expected_orientation:
                edge_errors.append(f"invalid orientation {orientation}")
        if edge_errors:
            fail(
                "invalid_lane_graph_edge",
                {"id": edge.get("id"), "errors": edge_errors},
            )

    head_numbers: dict[int, list[str]] = defaultdict(list)
    head_identities: dict[tuple[int, int, int], list[str]] = defaultdict(list)
    for head in signal_heads:
        lane_id = str(head.get("lane_id"))
        lane = expected_nodes.get(lane_id)
        position = head.get("position_m")
        controller_no = _canonical_positive_integer_identity(
            head.get("signal_controller_no")
        )
        signal_group_no = _canonical_positive_integer_identity(
            head.get("signal_group_no")
        )
        head_no = _canonical_positive_integer_identity(head.get("head_no"))
        expected_head_id = None if head_no is None else f"signal-head:{head_no}"
        identity_valid = (
            controller_no is not None
            and signal_group_no is not None
            and head_no is not None
            and head.get("id") == expected_head_id
        )
        if not identity_valid:
            fail(
                "invalid_lane_graph_stopline_identity",
                {
                    "id": head.get("id"),
                    "expected_id": expected_head_id,
                    "signal_controller_no": head.get("signal_controller_no"),
                    "signal_group_no": head.get("signal_group_no"),
                    "head_no": head.get("head_no"),
                },
            )
        else:
            head_numbers[head_no].append(str(head["id"]))
            head_identities[(controller_no, signal_group_no, head_no)].append(
                str(head["id"])
            )
        valid = (
            lane is not None
            and str(head.get("link_no")) == lane["link_no"]
            and head.get("lane_no") == lane["lane_no"]
            and valid_nonnegative(position)
            and float(position) <= float(lane["length_m"])
        )
        if not valid:
            fail(
                "invalid_lane_graph_stopline",
                {"id": head.get("id"), "lane_id": lane_id, "position_m": position},
            )

    duplicate_head_numbers = {
        str(head_no): ids
        for head_no, ids in sorted(head_numbers.items())
        if len(ids) != 1
    }
    duplicate_head_identities = {
        f"{controller_no}:{signal_group_no}:{head_no}": ids
        for (controller_no, signal_group_no, head_no), ids in sorted(
            head_identities.items()
        )
        if len(ids) != 1
    }
    if duplicate_head_numbers or duplicate_head_identities:
        fail(
            "invalid_lane_graph_stopline_identity",
            {
                "duplicate_head_numbers": duplicate_head_numbers,
                "duplicate_signal_identities": duplicate_head_identities,
            },
        )

    required_gate_values = {
        "unresolved_connector_lane_mappings": 0,
        "reverse_synthetic_edges": 0,
        "executable_connector_path_count": expected_connector_lane_count,
        "executable_connector_path_coverage": 1.0,
    }
    for name, expected in required_gate_values.items():
        if name in gates and gates[name] != expected:
            fail(
                "invalid_lane_graph_gate",
                {"gate": name, "expected": expected, "actual": gates[name]},
            )
    dimensions = graph.get("sample_dimensions", {})
    expected_dimensions = {
        "road_links": len(links),
        "connector_links": len(connectors),
        "lane_nodes": len(nodes),
        "connector_lanes": expected_connector_lane_count,
        "directed_edges": len(edges),
        "signal_heads": len(signal_heads),
    }
    if dimensions != expected_dimensions:
        fail(
            "invalid_lane_graph_dimension",
            {"expected": expected_dimensions, "actual": dimensions},
        )
    return sorted(failures, key=lambda item: (item["code"], item["entity_id"]))


def build_lane_graph(manifest: dict[str, Any]) -> dict[str, Any]:
    reasons: list[dict[str, Any]] = []
    validation = manifest.get("validation_report")
    if not isinstance(validation, dict) or not validation.get("valid", False):
        reasons.append(
            {
                "code": "canonical_compiler_validation_not_pass",
                "entity_id": "canonical-manifest",
                "detail": None if validation is None else validation.get("errors", []),
            }
        )
    signal_reference = manifest.get("signal_reference", {})
    if signal_reference.get("schema_version") != "signal-reference-v2.1":
        reasons.append(
            {
                "code": "missing_signal_reference_v2_1_evidence",
                "entity_id": "canonical-manifest",
                "detail": signal_reference.get("schema_version"),
            }
        )
    if not manifest.get("source", {}).get("inpx_sha256"):
        reasons.append(
            {
                "code": "missing_input_sha256",
                "entity_id": "canonical-manifest",
                "detail": None,
            }
        )
    nodes = _lane_nodes(manifest)
    links = _link_records(manifest)
    node_ids = {node["id"] for node in nodes}
    connectors, edges, connector_diagnostics = _connector_records(
        manifest, node_ids, reasons
    )
    heads = _signal_heads(manifest, node_ids, reasons)

    expected_connector_lane_ids = connector_diagnostics["expected_lane_ids"]
    invalid_connector_lane_ids = set(connector_diagnostics["invalid_lane_ids"])
    malformed_degrees: list[dict[str, Any]] = []
    for lane_id in sorted(expected_connector_lane_ids):
        incoming = [edge for edge in edges if edge["to_lane_id"] == lane_id]
        outgoing = [edge for edge in edges if edge["from_lane_id"] == lane_id]
        touching = [
            edge
            for edge in edges
            if edge["from_lane_id"] == lane_id or edge["to_lane_id"] == lane_id
        ]
        valid_degree = (
            len(incoming) == 1
            and incoming[0]["kind"] == "connector_entry"
            and len(outgoing) == 1
            and outgoing[0]["kind"] == "connector_exit"
            and len(touching) == 2
        )
        if not valid_degree:
            invalid_connector_lane_ids.add(lane_id)
            malformed_degrees.append(
                {
                    "lane_id": lane_id,
                    "incoming_edge_ids": [edge["id"] for edge in incoming],
                    "outgoing_edge_ids": [edge["id"] for edge in outgoing],
                    "touching_edge_ids": [edge["id"] for edge in touching],
                }
            )
    if malformed_degrees:
        reasons.append(
            {
                "code": "connector_lane_does_not_have_exact_two_directed_edges",
                "entity_id": "lane-graph",
                "detail": malformed_degrees,
            }
        )
    connector_lane_count = len(expected_connector_lane_ids)
    executable_count = connector_lane_count - len(invalid_connector_lane_ids)
    coverage = 1.0 if connector_lane_count == 0 else executable_count / connector_lane_count
    reverse_edges = connector_diagnostics["reverse_mapping_ids"]
    if reverse_edges:
        reasons.append(
            {
                "code": "synthetic_reverse_edge",
                "entity_id": "lane-graph",
                "detail": reverse_edges,
            }
        )

    source_hashes = behavioral_source_hashes()
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "canonical_json_version": CANONICAL_JSON_VERSION,
        "source": {
            "inpx_path": manifest.get("source", {}).get("inpx_path"),
            "input_sha256": manifest.get("source", {}).get("inpx_sha256"),
            "canonical_compiler_version": manifest.get("compiler_version"),
            "canonical_topology_hash": manifest.get("topology_hash"),
            "signal_reference_schema_version": signal_reference.get("schema_version"),
            "signal_reference_compiler_hash": signal_reference.get("compiler_hash"),
        },
        "command": {
            "version": COMMAND_VERSION,
            "source_sha256": source_hashes,
            "command_hash": canonical_json_sha256(source_hashes),
            "semantic_hash_scope": "schema_version, links, nodes, edges, connectors, signal_heads",
        },
        "status": "FAIL" if reasons else "PASS",
        "reasons": sorted(reasons, key=lambda item: (item["code"], item["entity_id"])),
        "sample_dimensions": {
            "road_links": len(manifest.get("links", [])),
            "connector_links": len(connectors),
            "lane_nodes": len(nodes),
            "connector_lanes": connector_lane_count,
            "directed_edges": len(edges),
            "signal_heads": len(heads),
        },
        "units": UNITS,
        "downstream_consumers": DOWNSTREAM_CONSUMERS,
        "production_gates": {
            "unresolved_connector_lane_mappings": len(invalid_connector_lane_ids),
            "reverse_synthetic_edges": len(reverse_edges),
            "executable_connector_path_count": executable_count,
            "executable_connector_path_coverage": coverage,
        },
        "links": links,
        "nodes": nodes,
        "edges": edges,
        "connectors": connectors,
        "signal_heads": heads,
    }
    artifact["semantic_sha256"] = canonical_json_sha256(semantic_payload(artifact))
    return artifact


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_json_text(value))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def load_graph(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inpx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    artifact = build_lane_graph(compile_network(args.inpx))
    atomic_write_json(args.output, artifact)
    gates = artifact["production_gates"]
    print(
        f"status={artifact['status']} nodes={len(artifact['nodes'])} "
        f"edges={len(artifact['edges'])} coverage={gates['executable_connector_path_coverage']:.12f} "
        f"hash={artifact['semantic_sha256']}"
    )
    return 0 if artifact["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
