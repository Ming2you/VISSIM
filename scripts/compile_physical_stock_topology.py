"""Compile the canonical one-stock physical topology for the VISSIM rollout plant."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable


SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from build_vissim_lane_graph import (  # noqa: E402
    atomic_write_json,
    behavioral_source_hashes,
    load_graph,
    validate_lane_graph_artifact,
)
from resolve_lane_routes import (  # noqa: E402
    SCHEMA_VERSION as ROUTE_SCHEMA_VERSION,
    semantic_payload as route_semantic_payload,
)

REPO_ROOT = SCRIPT_ROOT.parent
PLANT_ROOT = REPO_ROOT / "plant"
if str(PLANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PLANT_ROOT))

from src.vissim_strict.topology import (  # noqa: E402
    CANONICAL_JSON_VERSION,
    canonical_json_sha256,
)


SCHEMA_VERSION = "physical-stock-topology-v2.1"
COMMAND_VERSION = "compile-physical-stock-topology/2.1.1"
POSITION_TOLERANCE_M = 1.0e-6
WEIGHT_TOLERANCE = 1.0e-9
# 생산 격자를 못 박는 세 상수. 격자를 바꾸면 여기도 같이 바꿔야 하고, 바꾸는 순간
# 옛 격자로는 컴파일이 안 된다. 그래서 새 격자로 실런이 도는 것을 본 뒤에 갱신한다.
#
# 2026-08-14 갱신 — pedovrx 격자. 이전 값은 2026-08-05 판이었다.
#   보행자 노드 7개(SC2 SC3 SC8 SC17 SC18 SC19 SC9002)를 midblock 으로 접고,
#   tie 38건을 분수 귀속으로 해소하고, 유입 게이트 30개를 vehicleInput 근거로 추가하고,
#   저류 강제 지정 46링크(941 veh)를 얹은 결과다. 검증 런: 결정 31건 전부 exit=0,
#   실패·COM오류·관측실패 0, SIGNAL_SG_PLAN_ROWS 3,658, 표현률 92.0%, 저류 클리핑 0.
PRODUCTION_PARTITION_COUNTS = {
    "urban_owned": 952,
    "freeway_bound": 10,
    "boundary_out": 242,
    "total": 1204,
}
TRUSTED_PRODUCTION_FILE_HASHES = {
    "ownership_evidence": "c2a03de32ab29eef2a0a20eb2ddbad32a44ecf91a963ab0f58554b79363b5bff",
    "adjacency_evidence": "b200ebe9a40b7943b883c4b6f5a47b5ff9937d03f89842a17550ce03c4c55d2d",
    "capacity_evidence": "87e3858a44797094037516d0f4e533223bcefeaf62cc4d3c92cb2994b730c918",
}
TRUSTED_PRODUCTION_EVIDENCE_HASHES = {
    "ownership_evidence_semantic_sha256": "4988054c98d657ecbff287286eb281b8ead95fab0ad29467b8e0ba3282f038f1",
    "adjacency_evidence_semantic_sha256": "1f9311c5841c683f894ed937ccf1703e4848df9ed32c13f24e3cd57901b39d48",
    "capacity_evidence_semantic_sha256": "0277a749acfc8a23f1babe0bce85a6607703890e6811de9d8d36093c72b658b0",
    "legacy_partition_identity_sha256": "827537702b11cb2a011ca265583796782fb62d842b56996ca041e4400f41d395",
}
OBJECTIVE_POLICIES = {
    "physical_total": "include every in-network physical stock",
    "controller_default": "exclude exactly stocks carrying the boundary_out role",
    "controller_with_boundary": "include every in-network physical stock",
    "boundary_only": "include exactly stocks carrying the boundary_out role",
}
UNITS = {
    "position": "m",
    "interval": "half-open [start_m,end_m), with the final endpoint equal to lane length",
    "length": "m",
    "capacity": "veh",
    "jam_density": "veh/km/lane",
    "owner_weight": "fraction",
    "objective_weight": "binary dimensionless weight",
}
DOWNSTREAM_CONSUMERS = [
    "rollout plant state projection",
    "rollout plant physical flow trace",
    "controller visibility masks",
    "named objective views",
]


def _numeric_key(value: Any) -> tuple[int, int | str]:
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


def _position_text(value: float) -> str:
    value = 0.0 if abs(float(value)) <= POSITION_TOLERANCE_M else float(value)
    text = format(value, ".15f").rstrip("0").rstrip(".")
    return text or "0"


def stock_id(link_no: str, lane_no: int, start_m: float, end_m: float) -> str:
    return (
        f"stock:{link_no}:{lane_no}:"
        f"{_position_text(start_m)}:{_position_text(end_m)}"
    )


def _stock_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _numeric_key(item.get("link_no")),
        int(item.get("lane_no", -1)),
        float(item.get("start_m", -1.0)),
        float(item.get("end_m", -1.0)),
    )


def _edge_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        _stock_sort_key({
            "link_no": item.get("from_link_no"),
            "lane_no": item.get("from_lane_no"),
            "start_m": item.get("from_position_m"),
            "end_m": item.get("from_position_m"),
        }),
        str(item.get("kind", "")),
        str(item.get("id", "")),
    )


def _route_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (_numeric_key(item.get("decision_no")), _numeric_key(item.get("route_no")))


def _proof_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (*_route_sort_key(item), int(item.get("path_index", -1)))


def _normalized_mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a JSON object")
    return {str(key): value[key] for key in sorted(value, key=_numeric_key)}


def normalize_ownership_evidence(value: dict[str, Any]) -> dict[str, Any]:
    owner = _normalized_mapping(value.get("link_owner"), field="link_owner")
    freeway = _normalized_mapping(
        value.get("freeway_bound_links"), field="freeway_bound_links"
    )
    exits = value.get("monitor_only_exit_links")
    if not isinstance(exits, list):
        raise ValueError("monitor_only_exit_links must be a JSON array")
    exit_ids = sorted({str(item) for item in exits}, key=_numeric_key)
    return {
        "rule": str(value.get("rule", "")),
        "link_owner": {key: str(owner[key]) for key in owner},
        "freeway_bound_links": {key: str(freeway[key]) for key in freeway},
        "monitor_only_exit_links": exit_ids,
        "monitor_only_exit_duplicate_count": len(exits) - len(exit_ids),
        "urban_link_count": value.get("urban_link_count"),
    }


def normalize_adjacency_evidence(value: dict[str, Any]) -> dict[str, Any]:
    raw = _normalized_mapping(value.get("adjacency"), field="adjacency")
    adjacency: dict[str, list[str]] = {}
    for key, neighbors in raw.items():
        if not isinstance(neighbors, list):
            raise ValueError(f"adjacency[{key}] must be a JSON array")
        adjacency[key] = sorted({str(item) for item in neighbors}, key=_numeric_key)
    internal = value.get("internal_link_members", {})
    if not isinstance(internal, dict):
        raise ValueError("internal_link_members must be a JSON object")
    normalized_internal = {}
    for key in sorted(internal):
        members = internal[key] if isinstance(internal[key], list) else [internal[key]]
        normalized_internal[str(key)] = sorted({str(item) for item in members}, key=_numeric_key)
    return {
        "adjacency": adjacency,
        "internal_link_members": normalized_internal,
    }


def normalize_capacity_evidence(value: dict[str, Any]) -> dict[str, Any]:
    jam = value.get("jam_density_veh_km_lane")
    if not _finite(jam) or float(jam) <= 0.0:
        raise ValueError("jam_density_veh_km_lane must be finite and positive")
    ramps = _normalized_mapping(
        value.get("ramp_queue_max_veh_by_ramp"),
        field="ramp_queue_max_veh_by_ramp",
    )
    if not ramps:
        raise ValueError("named per-ramp capacity evidence is required")
    normalized_ramps: dict[str, float] = {}
    for key, capacity in ramps.items():
        if not _finite(capacity) or float(capacity) <= 0.0:
            raise ValueError(f"invalid named ramp capacity for {key}")
        normalized_ramps[key] = float(capacity)
    return {
        "jam_density_veh_km_lane": float(jam),
        "jam_sample_count": value.get("jam_sample_count"),
        "source": str(value.get("source", "")),
        "ramp_queue_source": str(value.get("ramp_queue_source", "")),
        "ramp_queue_max_veh_by_ramp": normalized_ramps,
    }


def legacy_partition_identity_payload(ownership: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "urban_owned": sorted(ownership["link_owner"], key=_numeric_key),
        "freeway_bound": sorted(ownership["freeway_bound_links"], key=_numeric_key),
        "boundary_out": sorted(ownership["monitor_only_exit_links"], key=_numeric_key),
    }


def evidence_identity_hashes(
    ownership_evidence: dict[str, Any],
    adjacency_evidence: dict[str, Any],
    capacity_evidence: dict[str, Any],
) -> dict[str, str]:
    ownership = normalize_ownership_evidence(ownership_evidence)
    adjacency = normalize_adjacency_evidence(adjacency_evidence)
    capacity = normalize_capacity_evidence(capacity_evidence)
    return {
        "ownership_evidence_semantic_sha256": canonical_json_sha256(ownership),
        "adjacency_evidence_semantic_sha256": canonical_json_sha256(adjacency),
        "capacity_evidence_semantic_sha256": canonical_json_sha256(capacity),
        "legacy_partition_identity_sha256": canonical_json_sha256(
            legacy_partition_identity_payload(ownership)
        ),
    }


def _command_records(source_hashes: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    script_key = "scripts/compile_physical_stock_topology.py"
    command_version = {
        "command": script_key,
        "version": COMMAND_VERSION,
        "sha256": source_hashes[script_key],
    }
    command = {
        "version": COMMAND_VERSION,
        "source_sha256": source_hashes,
        "command_hash": canonical_json_sha256(source_hashes),
        "semantic_hash_scope": "schema, semantic input hashes, policies, partition, capacity evidence, stocks, stock edges",
    }
    return command_version, command


def validate_route_proofs_artifact(
    routes: dict[str, Any], graph: dict[str, Any]
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def fail(code: str, detail: Any) -> None:
        failures.append({"code": code, "entity_id": "lane-route-proofs", "detail": detail})

    if routes.get("schema_version") != ROUTE_SCHEMA_VERSION:
        fail("invalid_route_proof_schema", routes.get("schema_version"))
    if routes.get("canonical_json_version") != CANONICAL_JSON_VERSION:
        fail("invalid_route_canonical_json_version", routes.get("canonical_json_version"))
    if routes.get("status") != "PASS":
        fail("route_proof_status_not_pass", routes.get("status"))
    if routes.get("reasons") != []:
        fail("route_proof_reasons_not_empty", routes.get("reasons"))
    if routes.get("source", {}).get("graph_semantic_sha256") != graph.get("semantic_sha256"):
        fail(
            "route_graph_semantic_hash_mismatch",
            {
                "route": routes.get("source", {}).get("graph_semantic_sha256"),
                "graph": graph.get("semantic_sha256"),
            },
        )
    try:
        actual_hash = canonical_json_sha256(route_semantic_payload(routes))
    except (KeyError, TypeError, ValueError) as exc:
        fail("invalid_route_semantic_payload", str(exc))
        actual_hash = None
    if actual_hash is not None and routes.get("semantic_sha256") != actual_hash:
        fail(
            "route_semantic_hash_mismatch",
            {"stored": routes.get("semantic_sha256"), "actual": actual_hash},
        )

    decisions = routes.get("routing_decisions")
    route_records = routes.get("routes")
    proofs = routes.get("proofs")
    if not isinstance(decisions, list) or decisions != sorted(
        decisions if isinstance(decisions, list) else [],
        key=lambda item: _numeric_key(item.get("decision_no")),
    ):
        fail("noncanonical_route_proof_order", "routing_decisions")
    if not isinstance(route_records, list) or route_records != sorted(
        route_records if isinstance(route_records, list) else [], key=_route_sort_key
    ):
        fail("noncanonical_route_proof_order", "routes")
    if not isinstance(proofs, list) or proofs != sorted(
        proofs if isinstance(proofs, list) else [], key=_proof_sort_key
    ):
        fail("noncanonical_route_proof_order", "proofs")
    route_records = route_records if isinstance(route_records, list) else []
    proofs = proofs if isinstance(proofs, list) else []
    lane_ids = {node["id"] for node in graph.get("nodes", [])}
    edge_ids = {edge["id"] for edge in graph.get("edges", [])}
    route_ids = {item.get("id") for item in route_records}
    proof_route_ids = {item.get("route_id") for item in proofs}
    if len(route_ids) != len(route_records) or route_ids != proof_route_ids:
        fail(
            "invalid_route_proof_universe",
            {"routes_without_proofs": sorted(route_ids - proof_route_ids)},
        )
    for route in route_records:
        if route.get("resolution_status") != "PASS" or not route.get(
            "normalized_flow_supports"
        ):
            fail("invalid_route_record", route.get("id"))
    for proof in proofs:
        segments = proof.get("lane_segments")
        if not isinstance(segments, list) or not segments:
            fail("invalid_route_lane_segment", proof.get("id"))
            continue
        for segment in segments:
            if (
                segment.get("lane_id") not in lane_ids
                or not _finite(segment.get("start_position_m"))
                or not _finite(segment.get("end_position_m"))
                or float(segment.get("end_position_m"))
                <= float(segment.get("start_position_m")) + POSITION_TOLERANCE_M
            ):
                fail("invalid_route_lane_segment", {"proof": proof.get("id"), "segment": segment})
        unknown_edges = sorted(set(proof.get("traversed_edge_ids", [])) - edge_ids)
        if unknown_edges:
            fail("route_proof_unknown_edge", {"proof": proof.get("id"), "edges": unknown_edges})
        supports = proof.get("flow_path_shares")
        if not isinstance(supports, list) or not supports:
            fail("invalid_route_flow_share", proof.get("id"))
        elif any(
            not _finite(item.get("normalized_flow_path_share"))
            or float(item["normalized_flow_path_share"]) < 0.0
            for item in supports
        ):
            fail("invalid_route_flow_share", proof.get("id"))
    gates = routes.get("production_gates", {})
    required_gates = {
        "unresolved_routes": 0,
        "reverse_synthetic_edges": 0,
        "executable_connector_path_coverage": 1.0,
    }
    for name, expected in required_gates.items():
        value = gates.get(name)
        if not _finite(value) or abs(float(value) - expected) > WEIGHT_TOLERANCE:
            fail("invalid_route_production_gate", {"name": name, "value": value})
    share_error = gates.get("maximum_normalized_flow_share_error")
    if not _finite(share_error) or float(share_error) > WEIGHT_TOLERANCE:
        fail("invalid_route_production_gate", {"name": "maximum_normalized_flow_share_error", "value": share_error})
    return failures


def _coalesced_points(
    length_m: float, evidence: list[tuple[float, str, str]]
) -> list[dict[str, Any]]:
    candidates: list[tuple[float, str, str]] = [(0.0, "lane_boundary", "start"), (length_m, "lane_boundary", "end")]
    for position, kind, identifier in evidence:
        position = float(position)
        if position < -POSITION_TOLERANCE_M or position > length_m + POSITION_TOLERANCE_M:
            raise ValueError(f"split point {position} outside [0,{length_m}]")
        if abs(position) <= POSITION_TOLERANCE_M:
            position = 0.0
        elif abs(position - length_m) <= POSITION_TOLERANCE_M:
            position = length_m
        candidates.append((position, kind, identifier))
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    clusters: list[list[tuple[float, str, str]]] = []
    for candidate in candidates:
        if clusters and candidate[0] - clusters[-1][0][0] <= POSITION_TOLERANCE_M:
            clusters[-1].append(candidate)
        else:
            clusters.append([candidate])
    result = []
    for cluster in clusters:
        positions = {item[0] for item in cluster}
        if 0.0 in positions:
            position = 0.0
        elif length_m in positions:
            position = length_m
        else:
            position = min(positions)
        reasons = [
            {"kind": kind, "id": identifier}
            for _, kind, identifier in sorted(cluster, key=lambda item: (item[1], item[2], item[0]))
        ]
        result.append({"position_m": position, "evidence": reasons})
    return result


def _partition_and_roles(
    graph: dict[str, Any], ownership: dict[str, Any]
) -> tuple[dict[str, str], dict[str, list[str]], dict[str, str], list[dict[str, Any]]]:
    reasons: list[dict[str, Any]] = []
    urban = set(ownership["link_owner"])
    freeway_bound = set(ownership["freeway_bound_links"])
    boundary = set(ownership["monitor_only_exit_links"])
    overlaps = (urban & freeway_bound) | (urban & boundary) | (freeway_bound & boundary)
    if overlaps:
        reasons.append({"code": "legacy_partition_overlap", "entity_id": "ownership", "detail": sorted(overlaps, key=_numeric_key)})
    parent_kind = {
        **{item["link_no"]: "link" for item in graph["links"]},
        **{item["connector_no"]: "connector" for item in graph["connectors"]},
    }
    partition: dict[str, str] = {}
    for identifier in urban:
        partition[identifier] = "urban_owned"
    for identifier in freeway_bound:
        partition[identifier] = "freeway_bound"
    for identifier in boundary:
        partition[identifier] = "boundary_out"
    unknown = sorted(set(partition) - set(parent_kind), key=_numeric_key)
    if unknown:
        reasons.append({"code": "legacy_partition_unknown_parent", "entity_id": "ownership", "detail": unknown})

    connector_by_no = {item["connector_no"]: item for item in graph["connectors"]}
    unpartitioned_roads = {
        item["link_no"] for item in graph["links"] if item["link_no"] not in partition
    }
    road_neighbors: dict[str, set[str]] = defaultdict(set)
    for connector in connector_by_no.values():
        source = connector["from_link_no"]
        target = connector["to_link_no"]
        if (
            connector["connector_no"] not in partition
            and source in unpartitioned_roads
            and target in unpartitioned_roads
        ):
            road_neighbors[source].add(target)
            road_neighbors[target].add(source)
    freeway_anchor_ids = set(ownership["freeway_bound_links"].values())
    inferred_road_owner: dict[str, str] = {}
    unseen = set(unpartitioned_roads)
    while unseen:
        root = min(unseen, key=_numeric_key)
        component: set[str] = set()
        queue = deque([root])
        while queue:
            current = queue.popleft()
            if current in component:
                continue
            component.add(current)
            queue.extend(sorted(road_neighbors[current] - component, key=_numeric_key))
        unseen -= component
        owner_ids = component & freeway_anchor_ids
        if len(owner_ids) == 1:
            owner = next(iter(owner_ids))
            for item in component:
                inferred_road_owner[item] = owner
        else:
            reasons.append({
                "code": "ambiguous_unpartitioned_road_role",
                "entity_id": ",".join(sorted(component, key=_numeric_key)),
                "detail": sorted(owner_ids, key=_numeric_key),
            })

    roles: dict[str, list[str]] = {}
    for identifier, kind in parent_kind.items():
        item_roles: set[str] = {"connector"} if kind == "connector" else set()
        legacy = partition.get(identifier)
        if legacy == "urban_owned":
            item_roles.add("urban")
        elif legacy == "freeway_bound":
            item_roles.add("interface")
        elif legacy == "boundary_out":
            item_roles.add("boundary_out")
        elif kind == "link" and identifier in inferred_road_owner:
            item_roles.add("freeway")
        roles[identifier] = sorted(item_roles)
    for identifier, connector in connector_by_no.items():
        if identifier in partition:
            continue
        source = connector["from_link_no"]
        target = connector["to_link_no"]
        endpoint_roles = {role for endpoint in (source, target) for role in roles.get(endpoint, [])}
        if target in inferred_road_owner and source not in inferred_road_owner:
            roles[identifier] = ["connector", "ramp"]
        elif source in inferred_road_owner and target in inferred_road_owner:
            owners = {inferred_road_owner[source], inferred_road_owner[target]}
            if len(owners) == 1:
                roles[identifier] = ["connector", "freeway"]
            else:
                reasons.append({"code": "ambiguous_connector_role", "entity_id": identifier, "detail": sorted(owners, key=_numeric_key)})
        else:
            reasons.append({"code": "ambiguous_connector_role", "entity_id": identifier, "detail": sorted(endpoint_roles)})
    return partition, roles, inferred_road_owner, reasons


def _split_evidence(
    graph: dict[str, Any], routes: dict[str, Any]
) -> dict[str, list[tuple[float, str, str]]]:
    evidence: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
    lanes_by_object_no: dict[str, list[str]] = defaultdict(list)
    for node in graph["nodes"]:
        lanes_by_object_no[str(node["link_no"])].append(node["id"])
    for edge in graph["edges"]:
        evidence[edge["from_lane_id"]].append((float(edge["from_position_m"]), "graph_edge", edge["id"]))
        evidence[edge["to_lane_id"]].append((float(edge["to_position_m"]), "graph_edge", edge["id"]))
    for head in graph["signal_heads"]:
        evidence[head["lane_id"]].append((float(head["position_m"]), "signal_head", head["id"]))
    for decision in routes["routing_decisions"]:
        for lane_id in lanes_by_object_no[str(decision["link_no"])]:
            evidence[lane_id].append((float(decision["position_m"]), "routing_decision", decision["id"]))
    for route in routes["routes"]:
        for lane_id in lanes_by_object_no[str(route["destination_link_no"])]:
            evidence[lane_id].append((float(route["destination_position_m"]), "route_destination", route["id"]))
    for proof in routes["proofs"]:
        for index, segment in enumerate(proof["lane_segments"]):
            identifier = f"{proof['id']}:segment:{index}"
            evidence[segment["lane_id"]].append((float(segment["start_position_m"]), "route_segment_start", identifier))
            evidence[segment["lane_id"]].append((float(segment["end_position_m"]), "route_segment_end", identifier))
        for index, event in enumerate(proof.get("lane_change_events", [])):
            identifier = f"{proof['id']}:lane-change:{index}"
            evidence[event["from_lane_id"]].append((float(event["start_position_m"]), "lane_change_start", identifier))
            evidence[event["to_lane_id"]].append((float(event["connector_position_m"]), "lane_change_end", identifier))
    return evidence


def _membership_records(
    stock: dict[str, Any], proof_segments: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    memberships = []
    for item in proof_segments.get(stock["lane_id"], []):
        overlap = min(stock["end_m"], item["end_m"]) - max(stock["start_m"], item["start_m"])
        if overlap <= POSITION_TOLERANCE_M:
            continue
        memberships.append({
            "proof_id": item["proof_id"],
            "route_id": item["route_id"],
            "decision_no": item["decision_no"],
            "route_no": item["route_no"],
            "path_index": item["path_index"],
            "segment_index": item["segment_index"],
            "overlap_start_m": max(stock["start_m"], item["start_m"]),
            "overlap_end_m": min(stock["end_m"], item["end_m"]),
            "flow_path_shares": item["flow_path_shares"],
        })
    memberships.sort(key=lambda item: (*_proof_sort_key(item), item["segment_index"]))
    return memberships


def _same_owner_distribution(
    left: dict[str, float], right: dict[str, float]
) -> bool:
    return set(left) == set(right) and all(
        abs(left[owner] - right[owner]) <= WEIGHT_TOLERANCE for owner in left
    )


def _local_decision_owner_distribution(
    item: dict[str, Any],
    proof_by_id: dict[str, dict[str, Any]],
    decision_by_no: dict[str, dict[str, Any]],
    node_by_id: dict[str, dict[str, Any]],
    parent_direct_owner: dict[str, tuple[str, str]],
) -> tuple[dict[str, float] | None, dict[str, Any] | None, dict[str, Any] | None]:
    eligible: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for membership in item["route_memberships"]:
        decision_no = str(membership["decision_no"])
        decision = decision_by_no.get(decision_no)
        if (
            decision is None
            or str(decision.get("link_no")) != item["link_no"]
            or float(decision.get("position_m", math.inf))
            > item["start_m"] + POSITION_TOLERANCE_M
        ):
            continue
        eligible[decision_no].append(membership)
    if not eligible:
        return None, None, None

    nearest_position = max(
        float(decision_by_no[decision_no]["position_m"])
        for decision_no in eligible
    )
    nearest_decisions = sorted(
        (
            decision_no
            for decision_no in eligible
            if abs(
                float(decision_by_no[decision_no]["position_m"])
                - nearest_position
            )
            <= POSITION_TOLERANCE_M
        ),
        key=_numeric_key,
    )
    distributions: dict[str, dict[str, float]] = {}
    support_times: dict[str, float] = {}
    for decision_no in nearest_decisions:
        owner_shares: dict[str, list[float]] = defaultdict(list)
        times: list[float] = []
        for membership in eligible[decision_no]:
            proof = proof_by_id[membership["proof_id"]]
            downstream_owner = None
            for segment in proof["lane_segments"][membership["segment_index"] :]:
                segment_parent = str(node_by_id[segment["lane_id"]]["link_no"])
                if segment_parent == item["link_no"]:
                    continue
                if segment_parent in parent_direct_owner:
                    downstream_owner = parent_direct_owner[segment_parent][0]
                    break
            if downstream_owner is None:
                continue
            supports = membership["flow_path_shares"]
            earliest = min(supports, key=lambda support: float(support["time_ms"]))
            support_time = float(earliest["time_ms"])
            times.append(support_time)
            owner_shares[downstream_owner].append(
                float(earliest["normalized_flow_path_share"])
            )
        totals = {owner: math.fsum(values) for owner, values in owner_shares.items()}
        total = math.fsum(totals.values())
        if total > 0.0:
            distributions[decision_no] = {
                owner: totals[owner] / total for owner in sorted(totals)
            }
            support_times[decision_no] = min(times)
    if not distributions:
        return None, None, None

    selected_decisions = sorted(distributions, key=_numeric_key)
    selected = distributions[selected_decisions[0]]
    conflicting = {
        decision_no: distributions[decision_no]
        for decision_no in selected_decisions[1:]
        if not _same_owner_distribution(selected, distributions[decision_no])
    }
    if conflicting:
        return None, None, {
            "nearest_decision_position_m": nearest_position,
            "decision_distributions": {
                decision_no: distributions[decision_no]
                for decision_no in selected_decisions
            },
            "reason": "no decision-inflow evidence for distinct conditional denominators",
        }
    return selected, {
        "decision_nos": selected_decisions,
        "decision_position_m": nearest_position,
        "flow_support_time_ms": min(
            support_times[decision_no] for decision_no in selected_decisions
        ),
    }, None


def semantic_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": artifact["schema_version"],
        "source_artifacts": {
            key: artifact["source_artifacts"][key]
            for key in (
                "lane_graph_semantic_sha256",
                "lane_route_proofs_semantic_sha256",
                "ownership_evidence_semantic_sha256",
                "adjacency_evidence_semantic_sha256",
                "capacity_evidence_semantic_sha256",
                "legacy_partition_identity_sha256",
            )
        },
        "policies": artifact["policies"],
        "legacy_partition": artifact["legacy_partition"],
        "capacity_evidence": artifact["capacity_evidence"],
        "stocks": artifact["stocks"],
        "stock_edges": artifact["stock_edges"],
    }


def _failed_artifact(
    graph: dict[str, Any],
    routes: dict[str, Any],
    source_artifacts: dict[str, Any],
    input_hashes: dict[str, str],
    reasons: list[dict[str, Any]],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    command_version, command = _command_records(source_hashes)
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "canonical_json_version": CANONICAL_JSON_VERSION,
        "input_hashes": input_hashes,
        "command_version": command_version,
        "source_artifacts": source_artifacts,
        "command": command,
        "status": "FAIL",
        "reasons": sorted(reasons, key=lambda item: (item["code"], item["entity_id"])),
        "units": UNITS,
        "downstream_consumers": DOWNSTREAM_CONSUMERS,
        "policies": {
            "stock_identity": "exact A1 lane interval",
            "position_tolerance_m": POSITION_TOLERANCE_M,
            "owner_weight_support": "nearest local A1 routing decision at its earliest flow support; distinct same-position decision denominators require decision-inflow evidence",
            "objective_weights": OBJECTIVE_POLICIES,
        },
        "legacy_partition": {},
        "capacity_evidence": {},
        "sample_dimensions": {"stocks": 0, "stock_edges": 0},
        "production_gates": {},
        "stocks": [],
        "stock_edges": [],
    }
    artifact["semantic_sha256"] = canonical_json_sha256(semantic_payload(artifact))
    return artifact


def compile_physical_stock_topology(
    graph: dict[str, Any],
    routes: dict[str, Any],
    ownership_evidence: dict[str, Any],
    adjacency_evidence: dict[str, Any],
    capacity_evidence: dict[str, Any],
    *,
    source_file_sha256: dict[str, str] | None = None,
    expected_evidence_hashes: dict[str, str] | None = None,
    require_production_partition: bool = False,
) -> dict[str, Any]:
    source_hashes = behavioral_source_hashes(
        [Path(__file__).resolve(), SCRIPT_ROOT / "resolve_lane_routes.py"]
    )
    reasons = list(validate_lane_graph_artifact(graph))
    reasons.extend(validate_route_proofs_artifact(routes, graph))
    try:
        ownership = normalize_ownership_evidence(ownership_evidence)
        adjacency = normalize_adjacency_evidence(adjacency_evidence)
        capacity = normalize_capacity_evidence(capacity_evidence)
    except (TypeError, ValueError) as exc:
        reasons.append({"code": "invalid_topology_evidence", "entity_id": "evidence", "detail": str(exc)})
        ownership, adjacency, capacity = {}, {}, {}
    actual_evidence_hashes = (
        evidence_identity_hashes(
            ownership_evidence, adjacency_evidence, capacity_evidence
        )
        if ownership and adjacency and capacity
        else {}
    )
    source_files = dict(sorted((source_file_sha256 or {}).items()))
    source_artifacts = {
        "lane_graph_schema_version": graph.get("schema_version"),
        "lane_graph_semantic_sha256": graph.get("semantic_sha256"),
        "lane_route_proofs_schema_version": routes.get("schema_version"),
        "lane_route_proofs_semantic_sha256": routes.get("semantic_sha256"),
        "ownership_evidence_semantic_sha256": actual_evidence_hashes.get(
            "ownership_evidence_semantic_sha256"
        ),
        "adjacency_evidence_semantic_sha256": actual_evidence_hashes.get(
            "adjacency_evidence_semantic_sha256"
        ),
        "capacity_evidence_semantic_sha256": actual_evidence_hashes.get(
            "capacity_evidence_semantic_sha256"
        ),
        "legacy_partition_identity_sha256": actual_evidence_hashes.get(
            "legacy_partition_identity_sha256"
        ),
        "source_file_sha256": source_files,
    }
    input_hashes = {
        "lane_graph_semantic_sha256": str(graph.get("semantic_sha256", "")),
        "lane_route_proofs_semantic_sha256": str(routes.get("semantic_sha256", "")),
        **actual_evidence_hashes,
    }
    raw_contract_names = {
        "lane_graph": "lane_graph_sha256",
        "lane_route_proofs": "lane_route_proofs_sha256",
        "ownership_evidence": "link_assignment_sha256",
        "adjacency_evidence": "adjacency_sha256",
        "capacity_evidence": "storage_capacity_sha256",
    }
    input_hashes.update(
        {
            contract_name: str(source_files[source_name])
            for source_name, contract_name in raw_contract_names.items()
            if source_name in source_files
        }
    )
    input_hashes = dict(sorted(input_hashes.items()))

    if ownership and ownership["monitor_only_exit_duplicate_count"]:
        reasons.append({
            "code": "legacy_partition_duplicate",
            "entity_id": "ownership",
            "detail": ownership["monitor_only_exit_duplicate_count"],
        })

    trusted_hashes = (
        TRUSTED_PRODUCTION_EVIDENCE_HASHES
        if require_production_partition
        else expected_evidence_hashes
    )
    if not isinstance(trusted_hashes, dict):
        reasons.append({
            "code": "missing_trusted_evidence_hashes",
            "entity_id": "evidence",
            "detail": sorted(TRUSTED_PRODUCTION_EVIDENCE_HASHES),
        })
    else:
        for name in sorted(TRUSTED_PRODUCTION_EVIDENCE_HASHES):
            expected = trusted_hashes.get(name)
            actual = actual_evidence_hashes.get(name)
            if expected != actual:
                reasons.append({
                    "code": (
                        "legacy_partition_identity_hash_mismatch"
                        if name == "legacy_partition_identity_sha256"
                        else "trusted_evidence_hash_mismatch"
                    ),
                    "entity_id": name,
                    "detail": {"expected": expected, "actual": actual},
                })
    if require_production_partition:
        for name, expected in TRUSTED_PRODUCTION_FILE_HASHES.items():
            actual = source_files.get(name)
            if actual != expected:
                reasons.append({
                    "code": "trusted_evidence_file_hash_mismatch",
                    "entity_id": name,
                    "detail": {"expected": expected, "actual": actual},
                })
    if reasons:
        return _failed_artifact(
            graph,
            routes,
            source_artifacts,
            input_hashes,
            reasons,
            source_hashes,
        )

    partition, roles, inferred_road_owner, role_reasons = _partition_and_roles(graph, ownership)
    reasons.extend(role_reasons)
    partition_sets = {
        "urban_owned": set(ownership["link_owner"]),
        "freeway_bound": set(ownership["freeway_bound_links"]),
        "boundary_out": set(ownership["monitor_only_exit_links"]),
    }
    partition_union = set().union(*partition_sets.values())
    partition_duplicates = (
        sum(map(len, partition_sets.values()))
        - len(partition_union)
        + int(ownership["monitor_only_exit_duplicate_count"])
    )
    if ownership["monitor_only_exit_duplicate_count"]:
        reasons.append({
            "code": "legacy_partition_duplicate",
            "entity_id": "ownership",
            "detail": ownership["monitor_only_exit_duplicate_count"],
        })
    if ownership.get("urban_link_count") != len(partition_union):
        reasons.append({
            "code": "legacy_partition_declared_total_mismatch",
            "entity_id": "ownership",
            "detail": {"declared": ownership.get("urban_link_count"), "actual": len(partition_union)},
        })
    if require_production_partition:
        actual = {key: len(value) for key, value in partition_sets.items()}
        actual["total"] = len(partition_union)
        if actual != PRODUCTION_PARTITION_COUNTS:
            reasons.append({"code": "production_partition_count_mismatch", "entity_id": "ownership", "detail": {"expected": PRODUCTION_PARTITION_COUNTS, "actual": actual}})

    urban_owner_ids = {str(value) for value in ownership["link_owner"].values()}
    missing_adjacency = sorted(urban_owner_ids - set(adjacency["adjacency"]), key=_numeric_key)
    if missing_adjacency:
        reasons.append({"code": "missing_owner_adjacency", "entity_id": "adjacency", "detail": missing_adjacency})

    node_by_id = {node["id"]: node for node in graph["nodes"]}
    parent_by_no = {
        **{item["link_no"]: item for item in graph["links"]},
        **{item["connector_no"]: item for item in graph["connectors"]},
    }
    connector_by_no = {item["connector_no"]: item for item in graph["connectors"]}
    direct_owner: dict[str, tuple[str, str]] = {}
    for identifier, owner in ownership["link_owner"].items():
        direct_owner[identifier] = (f"urban:{owner}", "legacy_link_owner")
    for identifier, owner in ownership["freeway_bound_links"].items():
        direct_owner[identifier] = (f"freeway:{owner}", "legacy_freeway_bound")
    for identifier, owner in inferred_road_owner.items():
        direct_owner[identifier] = (f"freeway:{owner}", "a1_connectivity_inference")
    for identifier, connector in connector_by_no.items():
        if identifier in direct_owner or identifier in partition_sets["boundary_out"]:
            continue
        target_owner = inferred_road_owner.get(connector["to_link_no"])
        source_owner = inferred_road_owner.get(connector["from_link_no"])
        if target_owner is not None:
            direct_owner[identifier] = (f"freeway:{target_owner}", "a1_connectivity_inference")
        elif source_owner is not None:
            owner = source_owner
            direct_owner[identifier] = (f"freeway:{owner}", "a1_connectivity_inference")

    split_evidence = _split_evidence(graph, routes)
    stocks: list[dict[str, Any]] = []
    split_points_by_lane: dict[str, list[dict[str, Any]]] = {}
    stocks_by_lane: dict[str, list[dict[str, Any]]] = defaultdict(list)
    interval_failures = {"gaps": 0, "overlaps": 0, "missing_lanes": 0, "nonpositive": 0}
    capacity_hash = source_artifacts["capacity_evidence_semantic_sha256"]
    jam = capacity["jam_density_veh_km_lane"]
    for node in graph["nodes"]:
        lane_id = node["id"]
        length_m = float(node["length_m"])
        if length_m <= POSITION_TOLERANCE_M:
            reasons.append({"code": "nonpositive_lane_length", "entity_id": lane_id, "detail": length_m})
            interval_failures["nonpositive"] += 1
            continue
        try:
            points = _coalesced_points(length_m, split_evidence.get(lane_id, []))
        except ValueError as exc:
            reasons.append({"code": "invalid_split_point", "entity_id": lane_id, "detail": str(exc)})
            interval_failures["missing_lanes"] += 1
            continue
        split_points_by_lane[lane_id] = points
        for left, right in zip(points, points[1:]):
            start_m = float(left["position_m"])
            end_m = float(right["position_m"])
            if end_m - start_m <= POSITION_TOLERANCE_M:
                interval_failures["nonpositive"] += 1
                reasons.append({"code": "nonpositive_stock_interval", "entity_id": lane_id, "detail": [start_m, end_m]})
                continue
            parent_no = str(node["link_no"])
            item_roles = roles.get(parent_no, [])
            boundary_out = "boundary_out" in item_roles
            item = {
                "id": stock_id(parent_no, int(node["lane_no"]), start_m, end_m),
                "lane_id": lane_id,
                "link_no": parent_no,
                "lane_no": int(node["lane_no"]),
                "parent_id": node["object_id"],
                "parent_kind": node["object_kind"],
                "parent_name": str(node.get("name", "")),
                "start_m": start_m,
                "end_m": end_m,
                "length_m": end_m - start_m,
                "members": [{"kind": "a1_lane", "id": lane_id}],
                "roles": item_roles,
                "legacy_partition": partition.get(parent_no, "outside_legacy_partition"),
                "split_start_evidence": left["evidence"],
                "split_end_evidence": right["evidence"],
                "upstream_stock_ids": [],
                "downstream_stock_ids": [],
                "upstream_edge_ids": [],
                "downstream_edge_ids": [],
                "control_owner_state": {},
                "control_owner_weights": {},
                "visible_to": [],
                "objective_weights": {
                    "physical_total": 1,
                    "controller_default": 0 if boundary_out else 1,
                    "controller_with_boundary": 1,
                    "boundary_only": 1 if boundary_out else 0,
                },
                "route_memberships": [],
                "capacity_prior": {
                    "value": (end_m - start_m) / 1000.0 * jam,
                    "unit": "veh",
                    "formula": "length_km * jam_density_veh_km_lane for one lane",
                    "jam_density_veh_km_lane": jam,
                    "capacity_evidence_semantic_sha256": capacity_hash,
                },
            }
            stocks.append(item)
            stocks_by_lane[lane_id].append(item)

    proof_segments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    proof_by_id = {proof["id"]: proof for proof in routes["proofs"]}
    for proof in routes["proofs"]:
        for index, segment in enumerate(proof["lane_segments"]):
            proof_segments[segment["lane_id"]].append({
                "proof_id": proof["id"],
                "route_id": proof["route_id"],
                "decision_no": proof["decision_no"],
                "route_no": proof["route_no"],
                "path_index": proof["path_index"],
                "segment_index": index,
                "start_m": float(segment["start_position_m"]),
                "end_m": float(segment["end_position_m"]),
                "flow_path_shares": proof["flow_path_shares"],
            })
    for values in proof_segments.values():
        values.sort(key=lambda item: (*_proof_sort_key(item), item["segment_index"]))
    for item in stocks:
        item["route_memberships"] = _membership_records(item, proof_segments)

    stock_edges: list[dict[str, Any]] = []
    for lane_id, lane_stocks in stocks_by_lane.items():
        lane_stocks.sort(key=lambda item: item["start_m"])
        for left, right in zip(lane_stocks, lane_stocks[1:]):
            edge_id = f"stock-edge:continuation:{lane_id}:{_position_text(left['end_m'])}"
            stock_edges.append({
                "id": edge_id,
                "kind": "lane_continuation",
                "from_stock_id": left["id"],
                "to_stock_id": right["id"],
                "from_link_no": left["link_no"],
                "from_lane_no": left["lane_no"],
                "from_position_m": left["end_m"],
                "to_link_no": right["link_no"],
                "to_lane_no": right["lane_no"],
                "to_position_m": right["start_m"],
                "source_graph_edge_id": None,
            })
    for graph_edge in graph["edges"]:
        source_candidates = [
            item for item in stocks_by_lane[graph_edge["from_lane_id"]]
            if abs(item["end_m"] - float(graph_edge["from_position_m"])) <= POSITION_TOLERANCE_M
        ]
        target_candidates = [
            item for item in stocks_by_lane[graph_edge["to_lane_id"]]
            if abs(item["start_m"] - float(graph_edge["to_position_m"])) <= POSITION_TOLERANCE_M
        ]
        if len(source_candidates) != 1 or len(target_candidates) != 1:
            reasons.append({"code": "unresolved_stock_edge_endpoint", "entity_id": graph_edge["id"], "detail": {"source_count": len(source_candidates), "target_count": len(target_candidates)}})
            continue
        source = source_candidates[0]
        target = target_candidates[0]
        stock_edges.append({
            "id": f"stock-edge:{graph_edge['id']}",
            "kind": graph_edge["kind"],
            "from_stock_id": source["id"],
            "to_stock_id": target["id"],
            "from_link_no": source["link_no"],
            "from_lane_no": source["lane_no"],
            # 엣지가 떠나고 닿는 stock 의 **경계값**을 쓴다. 위 :1010/:1014 가 허용오차로
            # 후보를 찾으므로 graph edge 의 원시값은 경계와 미세하게 다를 수 있다
            # (VISSIM 이 커넥터 Pos 를 6자리로 저장하고 차로 길이는 좌표에서 전정밀도로
            # 계산되기 때문이다). validate_physical_stock_topology 는 정확 일치를 요구하므로
            # 원시값을 그대로 기록하면 구조 오류가 된다. lane_continuation(:1001)이 이미
            # 같은 방식으로 경계값을 쓴다. 원시값은 source_graph_edge_id 로 추적 가능하다.
            "from_position_m": source["end_m"],
            "to_link_no": target["link_no"],
            "to_lane_no": target["lane_no"],
            "to_position_m": target["start_m"],
            "source_graph_edge_id": graph_edge["id"],
        })
    stock_edges.sort(key=_edge_sort_key)
    stock_by_id = {item["id"]: item for item in stocks}
    for edge in stock_edges:
        source = stock_by_id[edge["from_stock_id"]]
        target = stock_by_id[edge["to_stock_id"]]
        source["downstream_stock_ids"].append(target["id"])
        source["downstream_edge_ids"].append(edge["id"])
        target["upstream_stock_ids"].append(source["id"])
        target["upstream_edge_ids"].append(edge["id"])

    parent_direct_owner = direct_owner
    decision_by_no = {
        str(decision["decision_no"]): decision
        for decision in routes["routing_decisions"]
    }
    unexplained_owner = 0
    max_owner_error = 0.0
    for item in stocks:
        parent_no = item["link_no"]
        route_distribution, route_basis, route_conflict = (
            _local_decision_owner_distribution(
                item,
                proof_by_id,
                decision_by_no,
                node_by_id,
                parent_direct_owner,
            )
        )
        if route_conflict is not None:
            reasons.append({
                "code": "unsupported_multi_decision_owner_weights",
                "entity_id": item["id"],
                "detail": route_conflict,
            })
        use_route_weights = route_distribution is not None and (
            len(route_distribution) > 1 or parent_no not in parent_direct_owner
        )
        if parent_no in partition_sets["boundary_out"]:
            item["control_owner_state"] = {"kind": "external", "reason": "legacy_boundary_out"}
        elif use_route_weights:
            item["control_owner_weights"] = route_distribution
            item["control_owner_state"] = {
                "kind": "controlled",
                "basis": "a1_local_decision_route_flow_shares",
                **route_basis,
            }
        elif parent_no in parent_direct_owner:
            owner, basis = parent_direct_owner[parent_no]
            item["control_owner_weights"] = {owner: 1.0}
            item["control_owner_state"] = {"kind": "controlled", "basis": basis}
        else:
            item["control_owner_state"] = {"kind": "uncontrolled", "reason": "no_owner_or_local_decision_route_evidence"}
            unexplained_owner += 1
            reasons.append({"code": "unexplained_stock_owner", "entity_id": item["id"], "detail": parent_no})
        weights = item["control_owner_weights"]
        if weights:
            error = abs(math.fsum(weights.values()) - 1.0)
            max_owner_error = max(max_owner_error, error)
            if error > WEIGHT_TOLERANCE:
                reasons.append({"code": "owner_weight_sum_error", "entity_id": item["id"], "detail": error})
        principals: set[str] = set(weights)
        for owner in weights:
            if owner.startswith("urban:"):
                sc = owner.split(":", 1)[1]
                principals.update(f"urban:{neighbor}" for neighbor in adjacency["adjacency"].get(sc, []))
        if item["control_owner_state"]["kind"] == "external":
            principals.add("external:boundary-out")
        elif item["control_owner_state"]["kind"] == "uncontrolled":
            principals.add("uncontrolled:no-owner-evidence")
        item["visible_to"] = sorted(principals)
        for field in ("upstream_stock_ids", "downstream_stock_ids", "upstream_edge_ids", "downstream_edge_ids"):
            item[field] = sorted(set(item[field]))

    stocks.sort(key=_stock_sort_key)
    stock_ids = [item["id"] for item in stocks]
    duplicate_stock_ids = len(stock_ids) - len(set(stock_ids))
    for node in graph["nodes"]:
        lane_stocks = stocks_by_lane.get(node["id"], [])
        if not lane_stocks:
            interval_failures["missing_lanes"] += 1
            continue
        expected = 0.0
        for item in lane_stocks:
            if item["start_m"] > expected + POSITION_TOLERANCE_M:
                interval_failures["gaps"] += 1
            if item["start_m"] < expected - POSITION_TOLERANCE_M:
                interval_failures["overlaps"] += 1
            expected = item["end_m"]
        if abs(expected - float(node["length_m"])) > POSITION_TOLERANCE_M:
            interval_failures["gaps"] += 1

    objective_violations = 0
    for item in stocks:
        weights = item["objective_weights"]
        boundary_out = "boundary_out" in item["roles"]
        valid = (
            set(weights) == set(OBJECTIVE_POLICIES)
            and all(value in (0, 1) and not isinstance(value, bool) for value in weights.values())
            and weights["physical_total"] == 1
            and weights["controller_with_boundary"] == 1
            and weights["controller_default"] == (0 if boundary_out else 1)
            and weights["boundary_only"] == (1 if boundary_out else 0)
        )
        objective_violations += not valid
    if any(interval_failures.values()) or duplicate_stock_ids:
        reasons.append({"code": "lane_interval_partition_failure", "entity_id": "stocks", "detail": {**interval_failures, "duplicate_stock_ids": duplicate_stock_ids}})
    if objective_violations:
        reasons.append({"code": "objective_policy_violation", "entity_id": "stocks", "detail": objective_violations})

    role_counts = defaultdict(int)
    partition_stock_counts = defaultdict(int)
    parent_kind_stock_counts = defaultdict(int)
    for item in stocks:
        for role in item["roles"]:
            role_counts[role] += 1
        partition_stock_counts[item["legacy_partition"]] += 1
        parent_kind_stock_counts[item["parent_kind"]] += 1
    legacy_summary = {
        "identity_sha256": actual_evidence_hashes[
            "legacy_partition_identity_sha256"
        ],
        "counts": {
            "urban_owned": len(partition_sets["urban_owned"]),
            "freeway_bound": len(partition_sets["freeway_bound"]),
            "boundary_out": len(partition_sets["boundary_out"]),
            "total": len(partition_union),
            "duplicate": partition_duplicates,
            "missing_from_a1": len(partition_union - set(parent_by_no)),
        },
        "remaining_a1_road_links": sum(item["link_no"] not in partition_union for item in graph["links"]),
        "a1_connector_links": len(graph["connectors"]),
        "stock_counts": dict(sorted(partition_stock_counts.items())),
    }
    topology_capacity_evidence = {
        "jam_density_veh_km_lane": jam,
        "jam_density_unit": "veh/km/lane",
        "semantic_sha256": capacity_hash,
        "named_ramp_capacity_veh": capacity["ramp_queue_max_veh_by_ramp"],
        "named_ramp_membership_policy": "preserved as named evidence; source artifact contains no lane-membership mapping",
    }
    command_version, command = _command_records(source_hashes)
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "canonical_json_version": CANONICAL_JSON_VERSION,
        "input_hashes": input_hashes,
        "command_version": command_version,
        "source_artifacts": source_artifacts,
        "command": command,
        "status": "FAIL" if reasons else "PASS",
        "reasons": sorted(reasons, key=lambda item: (item["code"], item["entity_id"])),
        "units": UNITS,
        "downstream_consumers": DOWNSTREAM_CONSUMERS,
        "policies": {
            "stock_identity": "exact (link_no,lane_no,[start_m,end_m)) A1 lane interval",
            "position_tolerance_m": POSITION_TOLERANCE_M,
            "owner_weight_support": "nearest local A1 routing decision at its earliest flow support; distinct same-position decision denominators require decision-inflow evidence",
            "visibility": "control owners plus current urban adjacency; external stocks retain an explicit external principal",
            "objective_weights": OBJECTIVE_POLICIES,
        },
        "legacy_partition": legacy_summary,
        "capacity_evidence": topology_capacity_evidence,
        "sample_dimensions": {
            "a1_lane_nodes": len(graph["nodes"]),
            "a1_road_links": len(graph["links"]),
            "a1_connector_links": len(graph["connectors"]),
            "stocks": len(stocks),
            "stock_edges": len(stock_edges),
            "route_memberships": sum(len(item["route_memberships"]) for item in stocks),
            "stocks_by_parent_kind": dict(sorted(parent_kind_stock_counts.items())),
            "stocks_by_role": dict(sorted(role_counts.items())),
            "objective_weight_one_counts": {
                mode: sum(item["objective_weights"][mode] for item in stocks)
                for mode in OBJECTIVE_POLICIES
            },
        },
        "production_gates": {
            "lane_interval_gaps": interval_failures["gaps"],
            "lane_interval_overlaps": interval_failures["overlaps"],
            "lane_interval_missing_lanes": interval_failures["missing_lanes"],
            "lane_interval_nonpositive": interval_failures["nonpositive"],
            "duplicate_stock_ids": duplicate_stock_ids,
            "legacy_partition_duplicate": partition_duplicates,
            "legacy_partition_missing_from_a1": len(partition_union - set(parent_by_no)),
            "legacy_partition_identity_mismatch": 0,
            "maximum_owner_weight_sum_error": max_owner_error,
            "unexplained_owner_stocks": unexplained_owner,
            "objective_policy_violations": objective_violations,
            "visibility_uncovered_stocks": sum(not item["visible_to"] for item in stocks),
            "named_ramp_capacity_count": len(capacity["ramp_queue_max_veh_by_ramp"]),
        },
        "stocks": stocks,
        "stock_edges": stock_edges,
    }
    artifact["semantic_sha256"] = canonical_json_sha256(semantic_payload(artifact))
    return artifact


def iter_visible_stock_ids(
    topology: dict[str, Any], viewers: Iterable[str]
) -> Iterable[str]:
    visible = defaultdict(list)
    for item in topology["stocks"]:
        for viewer in item["visible_to"]:
            visible[viewer].append(item["id"])
    seen: set[str] = set()
    for viewer in viewers:
        for identifier in visible.get(str(viewer), []):
            if identifier not in seen:
                seen.add(identifier)
                yield identifier


def deduplicated_visible_mass(
    topology: dict[str, Any], stock_values: dict[str, float], viewers: Iterable[str] | None = None
) -> float:
    if viewers is None:
        viewers = sorted({viewer for item in topology["stocks"] for viewer in item["visible_to"]})
    return math.fsum(float(stock_values[identifier]) for identifier in iter_visible_stock_ids(topology, viewers))


def weighted_objective(
    topology: dict[str, Any], stock_values: dict[str, float], mode: str
) -> float:
    if mode not in OBJECTIVE_POLICIES:
        raise ValueError(f"unknown objective mode {mode!r}")
    return math.fsum(
        float(stock_values[item["id"]]) * item["objective_weights"][mode]
        for item in topology["stocks"]
    )


def objective_evaluation(
    topology: dict[str, Any],
    stock_values: dict[str, float],
    edge_flows: dict[str, float],
    mode: str,
) -> dict[str, Any]:
    return {
        "mode": mode,
        "weighted_objective": weighted_objective(topology, stock_values, mode),
        "physical_trace": {
            "stock_values": [
                {"stock_id": item["id"], "value": float(stock_values[item["id"]])}
                for item in topology["stocks"]
            ],
            "edge_flows": [
                {"edge_id": edge["id"], "value": float(edge_flows[edge["id"]])}
                for edge in topology["stock_edges"]
            ],
        },
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--routes", required=True, type=Path)
    parser.add_argument("--ownership", required=True, type=Path)
    parser.add_argument("--adjacency", required=True, type=Path)
    parser.add_argument("--capacity", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    paths = {
        "lane_graph": args.graph,
        "lane_route_proofs": args.routes,
        "ownership_evidence": args.ownership,
        "adjacency_evidence": args.adjacency,
        "capacity_evidence": args.capacity,
    }
    graph = load_graph(args.graph)
    with args.routes.open(encoding="utf-8") as handle:
        routes = json.load(handle)
    with args.ownership.open(encoding="utf-8") as handle:
        ownership = json.load(handle)
    with args.adjacency.open(encoding="utf-8") as handle:
        adjacency = json.load(handle)
    with args.capacity.open(encoding="utf-8") as handle:
        capacity = json.load(handle)
    artifact = compile_physical_stock_topology(
        graph,
        routes,
        ownership,
        adjacency,
        capacity,
        source_file_sha256={key: _file_sha256(path) for key, path in paths.items()},
        require_production_partition=True,
    )
    atomic_write_json(args.output, artifact)
    gates = artifact.get("production_gates", {})
    print(
        f"status={artifact['status']} stocks={len(artifact['stocks'])} "
        f"edges={len(artifact['stock_edges'])} gaps={gates.get('lane_interval_gaps')} "
        f"owners={gates.get('unexplained_owner_stocks')} hash={artifact['semantic_sha256']}"
    )
    return 0 if artifact["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
