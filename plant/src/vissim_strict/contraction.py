"""Topology-preserving contraction from raw VISSIM cells to hydraulic CTM cells.

The raw topology remains the traceability authority.  This module adds a second,
deterministic view in which serial lane cells can share one vehicle stock while
short, stockless connector segments are represented as conserved delay edges.
"""

from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import json
import math
from typing import Any, Iterable


CONTRACTION_VERSION = "vissim-strict-contraction/1.0.0"
_EPS = 1.0e-9


def _canonical_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stable_id(prefix: str, raw_ids: Iterable[str]) -> str:
    ordered = sorted(raw_ids)
    digest = hashlib.sha256("\n".join(ordered).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


class _UnionFind:
    def __init__(self, ids: Iterable[str]) -> None:
        self.parent = {item: item for item in ids}

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            item, self.parent[item] = self.parent[item], root
        return root

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def _point_cells(
    cells: list[dict[str, Any]],
    *,
    lane_group_id: str | None = None,
    link_no: str | None = None,
    lane_no: int | None = None,
    position_m: float | None = None,
) -> list[str]:
    matches: list[tuple[float, str]] = []
    for cell in cells:
        if lane_group_id is not None and cell.get("lane_group_id") != lane_group_id:
            continue
        source = cell.get("source", {})
        if link_no is not None and str(source.get("vissim_no")) != str(link_no):
            continue
        if lane_no is not None and int(source.get("lane_no", -1)) != int(lane_no):
            continue
        start = float(cell.get("start_position_m", 0.0))
        end = float(cell.get("end_position_m", start))
        if position_m is None:
            distance = 0.0
        elif start - _EPS <= position_m <= end + _EPS:
            distance = 0.0
        else:
            distance = min(abs(position_m - start), abs(position_m - end))
        matches.append((distance, cell["id"]))
    if not matches:
        return []
    minimum = min(distance for distance, _ in matches)
    return sorted(item for distance, item in matches if abs(distance - minimum) <= _EPS)


def _collect_anchors(
    manifest: dict[str, Any],
    cells: list[dict[str, Any]],
    predecessors: dict[str, set[str]],
    successors: dict[str, set[str]],
) -> tuple[dict[str, set[str]], set[tuple[str, str]]]:
    reasons: dict[str, set[str]] = defaultdict(set)
    cut_edges: set[tuple[str, str]] = set()
    by_id = {cell["id"]: cell for cell in cells}

    for cell_id in sorted(by_id):
        if len(predecessors[cell_id]) != 1:
            reasons[cell_id].add("merge_or_source")
            cut_edges.update((upstream, cell_id) for upstream in predecessors[cell_id])
        if len(successors[cell_id]) != 1:
            reasons[cell_id].add("diverge_or_sink")
            cut_edges.update((cell_id, downstream) for downstream in successors[cell_id])

    def anchor_point(
        reason: str,
        *,
        lane_group_id: str | None = None,
        link_no: str | None = None,
        lane_no: int | None = None,
        position_m: float | None = None,
        isolate: bool = True,
    ) -> None:
        for cell_id in _point_cells(
            cells,
            lane_group_id=lane_group_id,
            link_no=link_no,
            lane_no=lane_no,
            position_m=position_m,
        ):
            reasons[cell_id].add(reason)
            cell = by_id[cell_id]
            start = float(cell.get("start_position_m", 0.0))
            end = float(cell.get("end_position_m", start))
            if isolate or position_m is None or position_m > start + _EPS:
                cut_edges.update((cell_id, target) for target in successors[cell_id])
            if isolate or (position_m is not None and position_m < end - _EPS):
                cut_edges.update((source, cell_id) for source in predecessors[cell_id])

    for gate in manifest.get("signal_gates", []):
        anchor_point(
            "signal_gate",
            lane_group_id=gate.get("lane_group_id"),
            position_m=float(gate.get("position_m", 0.0)),
            isolate=False,
        )

    for decision in manifest.get("routing_decisions", []):
        anchor_point(
            "route_decision",
            link_no=str(decision.get("link_no")),
            position_m=float(decision.get("position_m", 0.0)),
        )
    for route in manifest.get("routes", []):
        anchor_point(
            "route_destination",
            link_no=str(route.get("destination_link_no")),
            position_m=float(route.get("destination_position_m", 0.0)),
        )

    for boundary in manifest.get("boundaries", []):
        link_id = boundary.get("link_id")
        for cell in cells:
            lane_group = str(cell.get("lane_group_id", ""))
            if link_id and f"lg:{link_id}:lane:" in lane_group:
                cell_id = cell["id"]
                reasons[cell_id].add(f"boundary_{boundary.get('type', 'unknown')}")

    for operator in manifest.get("observation_operators", []):
        kind = operator.get("kind")
        if kind == "data_collection_point":
            ref = operator.get("lane_ref", {})
            anchor_point(
                "detector",
                lane_group_id=ref.get("lane_group_id"),
                position_m=float(operator.get("position_m", 0.0)),
            )
        elif kind == "queue_counter":
            anchor_point(
                "queue_counter",
                link_no=str(operator.get("link_no")),
                position_m=float(operator.get("position_m", 0.0)),
            )
        elif kind == "travel_time_measurement":
            for endpoint in (operator.get("start", {}), operator.get("end", {})):
                anchor_point(
                    "travel_time_endpoint",
                    link_no=str(endpoint.get("link_no")),
                    position_m=float(endpoint.get("position_m", 0.0)),
                )

    for subgraph in manifest.get("influence_subgraphs", []):
        for item in subgraph.get("boundary_trajectory_contract", []):
            owned = item.get("owned_cell_id")
            external = item.get("external_cell_id")
            if owned in by_id:
                reasons[owned].add("influence_subgraph_cut")
            if external in by_id:
                reasons[external].add("influence_subgraph_cut")
            if owned in by_id and external in by_id:
                cut_edges.add((external, owned))
                cut_edges.add((owned, external))

    connector_groups: dict[str, set[str]] = defaultdict(set)
    for cell in cells:
        if str(cell.get("lane_group_id", "")).startswith("lg:link:") and str(
            cell.get("source", {}).get("kind", "")
        ).endswith("cell"):
            connector_groups[str(cell.get("source", {}).get("vissim_no"))].add(cell["id"])
    for candidate in manifest.get("freeway_interface_candidates", []):
        for connector_id in candidate.get("connector_ids", []):
            connector_no = str(connector_id).split(":")[-1]
            for cell_id in connector_groups.get(connector_no, set()):
                reasons[cell_id].add("freeway_interface_candidate")

    return reasons, cut_edges


def _movement_ownership(manifest: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    ownership: dict[str, set[str]] = defaultdict(set)
    for movement in manifest.get("movements", []):
        movement_id = movement["id"]
        groups = (
            movement.get("source_lane_group_ids", [])
            + movement.get("connector_lane_group_ids", [])
            + movement.get("target_lane_group_ids", [])
        )
        for group_id in groups:
            ownership[group_id].add(movement_id)
    return {key: tuple(sorted(value)) for key, value in ownership.items()}


def _reference_index(
    manifest: dict[str, Any],
    cells: list[dict[str, Any]],
    movement_owner: dict[str, tuple[str, ...]],
) -> dict[str, dict[str, set[str]]]:
    gates: dict[str, set[str]] = defaultdict(set)
    for gate in manifest.get("signal_gates", []):
        for raw_id in _point_cells(
            cells,
            lane_group_id=gate.get("lane_group_id"),
            position_m=float(gate.get("position_m", 0.0)),
        ):
            gates[raw_id].add(gate["id"])
    movements = {
        cell["id"]: set(movement_owner.get(cell.get("lane_group_id"), ()))
        for cell in cells
    }
    candidates_by_no: dict[str, set[str]] = defaultdict(set)
    for candidate in manifest.get("freeway_interface_candidates", []):
        for connector_id in candidate.get("connector_ids", []):
            candidates_by_no[str(connector_id).split(":")[-1]].add(candidate["id"])
    candidates = {
        cell["id"]: set(candidates_by_no.get(str(cell.get("source", {}).get("vissim_no")), set()))
        for cell in cells
    }
    observations: dict[str, set[str]] = defaultdict(set)
    for operator in manifest.get("observation_operators", []):
        points: list[str] = []
        if operator.get("kind") == "data_collection_point":
            ref = operator.get("lane_ref", {})
            points = _point_cells(
                cells,
                lane_group_id=ref.get("lane_group_id"),
                position_m=float(operator.get("position_m", 0.0)),
            )
        elif operator.get("kind") == "queue_counter":
            points = _point_cells(
                cells,
                link_no=str(operator.get("link_no")),
                position_m=float(operator.get("position_m", 0.0)),
            )
        elif operator.get("kind") == "travel_time_measurement":
            for endpoint in (operator.get("start", {}), operator.get("end", {})):
                points.extend(
                    _point_cells(
                        cells,
                        link_no=str(endpoint.get("link_no")),
                        position_m=float(endpoint.get("position_m", 0.0)),
                    )
                )
        for raw_id in points:
            observations[raw_id].add(operator["id"])

    route_points: dict[str, set[str]] = defaultdict(set)
    for decision in manifest.get("routing_decisions", []):
        for raw_id in _point_cells(
            cells,
            link_no=str(decision.get("link_no")),
            position_m=float(decision.get("position_m", 0.0)),
        ):
            route_points[raw_id].add(decision["id"])
    for route in manifest.get("routes", []):
        for raw_id in _point_cells(
            cells,
            link_no=str(route.get("destination_link_no")),
            position_m=float(route.get("destination_position_m", 0.0)),
        ):
            route_points[raw_id].add(route["id"])

    boundaries: dict[str, set[str]] = defaultdict(set)
    for boundary in manifest.get("boundaries", []):
        link_id = boundary.get("link_id")
        for item in cells:
            if link_id and f"lg:{link_id}:lane:" in str(item.get("lane_group_id", "")):
                boundaries[item["id"]].add(boundary["id"])

    subgraphs: dict[str, set[str]] = defaultdict(set)
    for subgraph in manifest.get("influence_subgraphs", []):
        for raw_id in (
            subgraph.get("seed_cell_ids", [])
            + subgraph.get("member_cell_ids", [])
            + subgraph.get("owned_cell_ids", [])
        ):
            subgraphs[raw_id].add(subgraph["id"])
        for item in subgraph.get("boundary_trajectory_contract", []):
            for raw_id in (item.get("owned_cell_id"), item.get("external_cell_id")):
                if raw_id:
                    subgraphs[raw_id].add(subgraph["id"])

    return {
        "gates": gates,
        "movements": movements,
        "candidates": candidates,
        "observations": observations,
        "routes": route_points,
        "boundaries": boundaries,
        "subgraphs": subgraphs,
    }


def _anchor_refs(
    raw_ids: list[str], reference_index: dict[str, dict[str, set[str]]]
) -> dict[str, list[str]]:
    gate_ids = {item for raw_id in raw_ids for item in reference_index["gates"].get(raw_id, set())}
    movement_ids = {
        item for raw_id in raw_ids for item in reference_index["movements"].get(raw_id, set())
    }
    candidate_ids = {
        item for raw_id in raw_ids for item in reference_index["candidates"].get(raw_id, set())
    }
    observation_ids = {
        item for raw_id in raw_ids for item in reference_index["observations"].get(raw_id, set())
    }
    route_anchor_ids = {
        item for raw_id in raw_ids for item in reference_index["routes"].get(raw_id, set())
    }
    boundary_ids = {
        item for raw_id in raw_ids for item in reference_index["boundaries"].get(raw_id, set())
    }
    influence_subgraph_ids = {
        item for raw_id in raw_ids for item in reference_index["subgraphs"].get(raw_id, set())
    }
    return {
        "gate_ids": sorted(gate_ids),
        "movement_ids": sorted(movement_ids),
        "freeway_interface_candidate_ids": sorted(candidate_ids),
        "observation_ids": sorted(observation_ids),
        "route_anchor_ids": sorted(route_anchor_ids),
        "boundary_ids": sorted(boundary_ids),
        "influence_subgraph_ids": sorted(influence_subgraph_ids),
    }


def contract_topology(
    manifest: dict[str, Any], *, urban_dt_sec: float = 1.0
) -> dict[str, Any]:
    """Return deterministic hydraulic fields for a raw Phase 0 manifest."""

    if urban_dt_sec <= 0.0:
        raise ValueError("urban_dt_sec must be positive")
    cells = sorted((dict(cell) for cell in manifest.get("cells", [])), key=lambda item: item["id"])
    by_id = {cell["id"]: cell for cell in cells}
    predecessors = {cell_id: set() for cell_id in by_id}
    successors = {cell_id: set() for cell_id in by_id}
    for cell in cells:
        cell_id = cell["id"]
        for downstream in cell.get("downstream_cell_ids", []):
            if downstream in by_id:
                successors[cell_id].add(downstream)
                predecessors[downstream].add(cell_id)
        for upstream in cell.get("upstream_cell_ids", []):
            if upstream in by_id:
                predecessors[cell_id].add(upstream)
                successors[upstream].add(cell_id)

    anchor_reasons, cut_edges = _collect_anchors(manifest, cells, predecessors, successors)
    movement_owner = _movement_ownership(manifest)
    reference_index = _reference_index(manifest, cells, movement_owner)
    union = _UnionFind(by_id)
    for source in sorted(by_id):
        for target in sorted(successors[source]):
            left, right = by_id[source], by_id[target]
            left_group, right_group = left.get("lane_group_id"), right.get("lane_group_id")
            compatible = (
                len(successors[source]) == 1
                and len(predecessors[target]) == 1
                and left_group == right_group
                and movement_owner.get(left_group, ()) == movement_owner.get(right_group, ())
                and (source, target) not in cut_edges
            )
            if compatible:
                union.union(source, target)

    components: dict[str, list[str]] = defaultdict(list)
    for cell_id in sorted(by_id):
        components[union.find(cell_id)].append(cell_id)
    component_ids = {
        root: _stable_id("hydraulic-component", raw_ids)
        for root, raw_ids in sorted(components.items())
    }
    raw_component = {
        raw_id: component_ids[root]
        for root, raw_ids in components.items()
        for raw_id in raw_ids
    }
    component_raw = {component_ids[root]: raw_ids for root, raw_ids in components.items()}
    component_up: dict[str, set[str]] = defaultdict(set)
    component_down: dict[str, set[str]] = defaultdict(set)
    for source in sorted(by_id):
        for target in successors[source]:
            a, b = raw_component[source], raw_component[target]
            if a != b:
                component_down[a].add(b)
                component_up[b].add(a)

    def total(component_id: str, field: str) -> float:
        return sum(float(by_id[item].get(field, 0.0)) for item in component_raw[component_id])

    def speed_threshold(component_id: str) -> float:
        speeds = [
            float(by_id[item].get("parameter_placeholders", {}).get("v_free_mps", 0.0))
            for item in component_raw[component_id]
        ]
        return max(speeds, default=0.0) * urban_dt_sec

    transfer_candidates: set[str] = set()
    for component_id, raw_ids in sorted(component_raw.items()):
        is_short = total(component_id, "length_m") + _EPS < speed_threshold(component_id)
        if is_short:
            transfer_candidates.add(component_id)

    def resolve_endpoints(component_id: str, upstream: bool) -> set[str]:
        queue = deque([component_id])
        seen = {component_id}
        endpoints: set[str] = set()
        while queue:
            current = queue.popleft()
            neighbors = component_up[current] if upstream else component_down[current]
            for neighbor in sorted(neighbors):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                if neighbor in transfer_candidates:
                    queue.append(neighbor)
                else:
                    endpoints.add(neighbor)
        return endpoints

    hydraulic_components = sorted(set(component_raw) - transfer_candidates)
    component_to_hydraulic = {
        component_id: _stable_id("hcell", component_raw[component_id])
        for component_id in hydraulic_components
    }
    component_to_transfer = {
        component_id: _stable_id("transfer", component_raw[component_id])
        for component_id in sorted(transfer_candidates)
    }

    hydraulic_cells: list[dict[str, Any]] = []
    for component_id in hydraulic_components:
        raw_ids = sorted(component_raw[component_id])
        length_m = total(component_id, "length_m")
        storage_veh = total(component_id, "storage_veh")
        v_free = max(
            (
                float(by_id[item].get("parameter_placeholders", {}).get("v_free_mps", 0.0))
                for item in raw_ids
            ),
            default=0.0,
        )
        max_dt = math.inf if v_free <= 0.0 else length_m / v_free
        direct_up = {item for item in component_up[component_id] if item not in transfer_candidates}
        direct_down = {item for item in component_down[component_id] if item not in transfer_candidates}
        through_up = {
            endpoint
            for item in component_up[component_id]
            if item in transfer_candidates
            for endpoint in resolve_endpoints(item, True)
        }
        through_down = {
            endpoint
            for item in component_down[component_id]
            if item in transfer_candidates
            for endpoint in resolve_endpoints(item, False)
        }
        all_up = direct_up | through_up
        all_down = direct_down | through_down
        refs = _anchor_refs(raw_ids, reference_index)
        hydraulic_cells.append(
            {
                "id": component_to_hydraulic[component_id],
                "ownership_kind": "hydraulic_stock",
                "raw_cell_ids": raw_ids,
                "lane_group_ids": sorted({by_id[item].get("lane_group_id") for item in raw_ids}),
                "lane_ids": sorted({lane for item in raw_ids for lane in by_id[item].get("lanes", [])}),
                "length_m": length_m,
                "storage_veh": storage_veh,
                "minimum_travel_time_sec": sum(
                    float(by_id[item].get("minimum_travel_time_sec", 0.0)) for item in raw_ids
                ),
                "v_free_mps": v_free,
                "cfl": {
                    "reference_dt_sec": urban_dt_sec,
                    "maximum_dt_sec_from_free_flow": None if math.isinf(max_dt) else max_dt,
                    "reference_dt_satisfies_free_flow_cfl": max_dt + _EPS >= urban_dt_sec,
                },
                "upstream_hydraulic_ids": sorted(component_to_hydraulic[item] for item in all_up),
                "downstream_hydraulic_ids": sorted(component_to_hydraulic[item] for item in all_down),
                "upstream_element_ids": sorted(
                    component_to_transfer[item] if item in transfer_candidates else component_to_hydraulic[item]
                    for item in component_up[component_id]
                ),
                "downstream_element_ids": sorted(
                    component_to_transfer[item] if item in transfer_candidates else component_to_hydraulic[item]
                    for item in component_down[component_id]
                ),
                "incoming_transfer_edge_ids": sorted(
                    component_to_transfer[item]
                    for item in component_up[component_id]
                    if item in transfer_candidates
                ),
                "outgoing_transfer_edge_ids": sorted(
                    component_to_transfer[item]
                    for item in component_down[component_id]
                    if item in transfer_candidates
                ),
                "anchor_reasons": sorted(
                    set().union(*(anchor_reasons.get(item, set()) for item in raw_ids))
                ),
                **refs,
                "provenance": [
                    {"raw_cell_id": item, "source": by_id[item].get("source", {})}
                    for item in raw_ids
                ],
            }
        )

    transfer_edges: list[dict[str, Any]] = []
    for component_id in sorted(transfer_candidates):
        raw_ids = sorted(component_raw[component_id])
        upstream = resolve_endpoints(component_id, True)
        downstream = resolve_endpoints(component_id, False)
        refs = _anchor_refs(raw_ids, reference_index)
        travel_time = sum(
            float(by_id[item].get("minimum_travel_time_sec", 0.0)) for item in raw_ids
        )
        transfer_edges.append(
            {
                "id": component_to_transfer[component_id],
                "ownership_kind": "stockless_conserved_transfer",
                "owns_vehicles": False,
                "owns_road_storage": False,
                "transit_ledger_owner": True,
                "raw_cell_ids": raw_ids,
                "upstream_hydraulic_ids": sorted(component_to_hydraulic[item] for item in upstream),
                "downstream_hydraulic_ids": sorted(component_to_hydraulic[item] for item in downstream),
                "upstream_element_ids": sorted(
                    component_to_transfer[item] if item in transfer_candidates else component_to_hydraulic[item]
                    for item in component_up[component_id]
                ),
                "downstream_element_ids": sorted(
                    component_to_transfer[item] if item in transfer_candidates else component_to_hydraulic[item]
                    for item in component_down[component_id]
                ),
                "topology_kind": (
                    "serial_edge"
                    if len(component_up[component_id]) <= 1 and len(component_down[component_id]) <= 1
                    else "conserved_node_delay"
                ),
                "length_m": total(component_id, "length_m"),
                "travel_time_sec": travel_time,
                "delay_steps": max(1, int(math.ceil(travel_time / urban_dt_sec - _EPS))),
                "raw_storage_veh_accounting": total(component_id, "storage_veh"),
                "conservation_contract": "move_once from source stock to transit ledger, then once to target stock after delay",
                **refs,
                "provenance": [
                    {"raw_cell_id": item, "source": by_id[item].get("source", {})}
                    for item in raw_ids
                ],
            }
        )

    raw_to_hydraulic: dict[str, dict[str, str]] = {}
    for component_id, raw_ids in sorted(component_raw.items()):
        if component_id in transfer_candidates:
            mapped = {"kind": "transfer_edge", "id": component_to_transfer[component_id]}
        else:
            mapped = {"kind": "hydraulic_cell", "id": component_to_hydraulic[component_id]}
        for raw_id in sorted(raw_ids):
            raw_to_hydraulic[raw_id] = dict(mapped)

    raw_length = sum(float(cell.get("length_m", 0.0)) for cell in cells)
    raw_storage = sum(float(cell.get("storage_veh", 0.0)) for cell in cells)
    hydraulic_length = sum(item["length_m"] for item in hydraulic_cells)
    transfer_length = sum(item["length_m"] for item in transfer_edges)
    hydraulic_storage = sum(item["storage_veh"] for item in hydraulic_cells)
    transfer_storage = sum(item["raw_storage_veh_accounting"] for item in transfer_edges)
    errors: list[dict[str, str]] = []
    if set(raw_to_hydraulic) != set(by_id):
        errors.append({"code": "dangling_raw_to_hydraulic_map", "entity_id": "manifest", "detail": "map coverage differs from raw cells"})
    if abs(raw_length - hydraulic_length - transfer_length) > 1.0e-6:
        errors.append({"code": "hydraulic_length_accounting", "entity_id": "manifest", "detail": "raw length is not conserved"})
    if abs(raw_storage - hydraulic_storage - transfer_storage) > 1.0e-6:
        errors.append({"code": "hydraulic_storage_accounting", "entity_id": "manifest", "detail": "raw reference storage is not conserved"})
    hydraulic_ids = {item["id"] for item in hydraulic_cells}
    element_by_id = {
        item["id"]: item for item in hydraulic_cells + transfer_edges
    }
    for edge in transfer_edges:
        for endpoint in edge["upstream_hydraulic_ids"] + edge["downstream_hydraulic_ids"]:
            if endpoint not in hydraulic_ids:
                errors.append({"code": "dangling_transfer_endpoint", "entity_id": edge["id"], "detail": endpoint})

    ownership_count: dict[str, int] = defaultdict(int)
    for element in hydraulic_cells + transfer_edges:
        for raw_id in element["raw_cell_ids"]:
            ownership_count[raw_id] += 1
    duplicate_or_missing = sorted(
        raw_id for raw_id in by_id if ownership_count.get(raw_id, 0) != 1
    )
    if duplicate_or_missing:
        errors.append(
            {
                "code": "duplicate_or_missing_vehicle_ownership",
                "entity_id": "manifest",
                "detail": ",".join(duplicate_or_missing[:20]),
            }
        )

    quotient_edge_errors: list[str] = []
    for source in sorted(by_id):
        source_element = raw_to_hydraulic[source]["id"]
        for target in sorted(successors[source]):
            target_element = raw_to_hydraulic[target]["id"]
            if source_element == target_element:
                continue
            if target_element not in element_by_id[source_element].get("downstream_element_ids", []):
                quotient_edge_errors.append(f"{source}->{target}")
    if quotient_edge_errors:
        errors.append(
            {
                "code": "anchor_reachability_edge_loss",
                "entity_id": "manifest",
                "detail": ",".join(quotient_edge_errors[:20]),
            }
        )

    remaining_cfl = [
        item["id"]
        for item in hydraulic_cells
        if not item["cfl"]["reference_dt_satisfies_free_flow_cfl"]
    ]
    if remaining_cfl:
        errors.append(
            {
                "code": "hydraulic_free_flow_cfl_violation",
                "entity_id": "manifest",
                "detail": ",".join(remaining_cfl[:20]),
            }
        )
    view_for_hash = {
        "contraction_version": CONTRACTION_VERSION,
        "urban_dt_sec": urban_dt_sec,
        "hydraulic_cells": hydraulic_cells,
        "transfer_edges": transfer_edges,
        "raw_to_hydraulic": raw_to_hydraulic,
    }
    hydraulic_hash = hashlib.sha256(_canonical_text(view_for_hash).encode("utf-8")).hexdigest()
    report = {
        "valid": not errors,
        "error_count": len(errors),
        "errors": sorted(errors, key=lambda item: (item["code"], item["entity_id"], item["detail"])),
        "contraction_version": CONTRACTION_VERSION,
        "urban_dt_sec": urban_dt_sec,
        "raw_cell_count": len(cells),
        "hydraulic_cell_count": len(hydraulic_cells),
        "transfer_edge_count": len(transfer_edges),
        "contracted_raw_cell_count": sum(max(0, len(item["raw_cell_ids"]) - 1) for item in hydraulic_cells),
        "anchor_cell_count": len(anchor_reasons),
        "raw_length_m": raw_length,
        "hydraulic_length_m": hydraulic_length,
        "transfer_edge_length_m": transfer_length,
        "length_residual_m": raw_length - hydraulic_length - transfer_length,
        "raw_storage_veh": raw_storage,
        "hydraulic_storage_veh": hydraulic_storage,
        "transfer_edge_reference_storage_veh": transfer_storage,
        "storage_residual_veh": raw_storage - hydraulic_storage - transfer_storage,
        "remaining_free_flow_cfl_violation_count": len(remaining_cfl),
        "remaining_free_flow_cfl_violation_ids": remaining_cfl,
        "anchor_reachability_preserved": not quotient_edge_errors,
        "reachability_validation": "all raw edges preserved in the deterministic quotient graph",
        "no_duplicate_vehicle_ownership": not duplicate_or_missing,
        "hydraulic_hash": hydraulic_hash,
    }
    return {
        "hydraulic_cells": hydraulic_cells,
        "transfer_edges": transfer_edges,
        "raw_to_hydraulic": raw_to_hydraulic,
        "contraction_report": report,
    }


__all__ = ["CONTRACTION_VERSION", "contract_topology"]
