"""Deterministic lane-cell CTM and conservative node solver.

This module owns urban physical state transitions only. Freeway METANET state is
intentionally outside Phase 1; a non-empty ``freeway_interfaces`` manifest is
rejected until the Phase 3 bridge supplies explicit boundary transactions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math
from typing import Any, Iterable, Mapping

from .schema import (
    ActionSchedule,
    ControlAction,
    DemandSchedule,
    MASS_TOLERANCE_VEH,
    PlantParameters,
    PlantState,
    SchemaError,
    StepAction,
    StepDiagnostics,
    StepResult,
    StepStatus,
    VehicleStock,
)
from .topology import canonical_json_text


_EPS = 1.0e-12


@dataclass(frozen=True)
class _Cell:
    cell_id: str
    lane_group_id: str
    link_id: str
    length_m: float
    flow_length_m: float
    lane_count: int
    storage_veh: float
    delay_buffer_ids: tuple[str, ...]


@dataclass(frozen=True)
class _Edge:
    edge_id: str
    source_id: str
    target_cell_id: str | None
    kind: str
    movement_id: str | None
    boundary_id: str | None
    turn_ratios: tuple[tuple[str, float], ...]
    priority: float


@dataclass(frozen=True)
class CandidateRolloutResult:
    candidate_index: int
    action_hash: str
    status: StepStatus
    is_feasible: bool
    total_cost: float | None
    terminal_state_hash: str | None
    diagnostics: tuple[tuple[str, Any], ...]
    error: tuple[tuple[str, str], ...] | None


@dataclass(frozen=True)
class BatchRolloutResult:
    schema_version: str
    batch_status: StepStatus
    selected_candidate_index: int | None
    fallback_required: bool
    candidate_results: tuple[CandidateRolloutResult, ...]


def _sum_maps(*values: Mapping[str, float]) -> dict[str, float]:
    result: dict[str, float] = {}
    for value in values:
        for key, amount in value.items():
            result[key] = result.get(key, 0.0) + amount
    return result


def _scale(value: Mapping[str, float], factor: float) -> dict[str, float]:
    return {key: amount * factor for key, amount in value.items()}


def _periodic_green_overlap(
    intervals: Iterable[Mapping[str, Any]],
    phase_sec: float,
    duration_sec: float,
    cycle_sec: float,
    startup_loss_sec: float = 0.0,
) -> float:
    if duration_sec <= 0.0:
        return 0.0
    green_per_cycle = sum(
        max(0.0, float(item["end_sec"]) - (float(item["start_sec"]) + startup_loss_sec))
        for item in intervals
        if str(item["state"]).upper() == "GREEN"
    )
    complete = math.floor(duration_sec / cycle_sec)
    overlap = complete * green_per_cycle
    remainder = duration_sec - complete * cycle_sec
    phase = phase_sec % cycle_sec

    def linear(start: float, end: float) -> float:
        return sum(
            max(
                0.0,
                min(end, float(item["end_sec"]))
                - max(start, float(item["start_sec"]) + startup_loss_sec),
            )
            for item in intervals
            if str(item["state"]).upper() == "GREEN"
        )

    first = min(remainder, cycle_sec - phase)
    overlap += linear(phase, phase + first)
    if remainder > first:
        overlap += linear(0.0, remainder - first)
    return overlap


def _priority_allocate(demands: Mapping[str, float], priorities: Mapping[str, float], supply: float) -> dict[str, float]:
    """Weighted max-min allocation of one downstream supply."""

    result = {key: 0.0 for key in demands}
    active = {key for key, demand in demands.items() if demand > _EPS}
    remaining = max(0.0, supply)
    while active and remaining > _EPS:
        total_weight = sum(max(priorities.get(key, 1.0), _EPS) for key in active)
        shares = {
            key: remaining * max(priorities.get(key, 1.0), _EPS) / total_weight for key in active
        }
        satisfied = [key for key in active if demands[key] - result[key] <= shares[key] + _EPS]
        if not satisfied:
            for key in active:
                result[key] += shares[key]
            remaining = 0.0
            break
        for key in sorted(satisfied):
            amount = demands[key] - result[key]
            result[key] += amount
            remaining -= amount
            active.remove(key)
    return result


class StrictPlant:
    """Immutable topology/parameter binding with a pure one-step CTM kernel."""

    supports_freeway_interfaces = False

    def __init__(self, topology: Mapping[str, Any], parameters: PlantParameters):
        # A canonical JSON round-trip breaks all mutable references held by the caller.
        self._topology = json.loads(canonical_json_text(dict(topology)))
        self.parameters = parameters
        self.topology_hash = str(self._topology.get("topology_hash", ""))
        if not self.topology_hash:
            raise SchemaError("topology_hash is required")
        if parameters.topology_hash != self.topology_hash:
            raise SchemaError("PlantParameters topology_hash does not match topology")
        if self._topology.get("freeway_interfaces"):
            raise SchemaError(
                "Phase 1 urban kernel cannot own freeway interface stocks; use explicit source/sink boundary transactions"
            )

        hydraulic_view = self._topology.get("hydraulic_view")
        if hydraulic_view is None and self._topology.get("hydraulic_cells") is not None:
            hydraulic_view = {
                "hydraulic_cells": self._topology.get("hydraulic_cells", []),
                "transfer_edges": self._topology.get("transfer_edges", []),
                "raw_to_hydraulic": self._topology.get(
                    "raw_to_hydraulic",
                    self._topology.get("raw_cell_to_hydraulic_cell", {}),
                ),
                "validation_report": self._topology.get(
                    "contraction_report",
                    self._topology.get("hydraulic_validation_report", {}),
                ),
            }
        self.uses_hydraulic_view = hydraulic_view is not None
        self._hydraulic_view = hydraulic_view or {}
        if self.uses_hydraulic_view and self._hydraulic_view.get("validation_report", {}).get("valid") is False:
            raise SchemaError("compiler-provided hydraulic_view is invalid")
        self.preserved_anchor_ids = tuple(
            sorted(set(map(str, self._hydraulic_view.get("preserved_anchor_ids", []))))
        )
        required_anchors = set(map(str, self._hydraulic_view.get("required_anchor_ids", [])))
        if not required_anchors.issubset(set(self.preserved_anchor_ids)):
            raise SchemaError("hydraulic_view does not preserve every required anchor")
        raw_mapping = self._hydraulic_view.get(
            "raw_to_hydraulic",
            self._hydraulic_view.get("raw_cell_to_hydraulic_cell", {}),
        )
        self._raw_to_hydraulic = {}
        self._raw_to_transfer = {}
        for key, value in raw_mapping.items():
            if isinstance(value, Mapping):
                if str(value.get("kind")) == "transfer_edge":
                    self._raw_to_transfer[str(key)] = str(value.get("id"))
                else:
                    self._raw_to_hydraulic[str(key)] = str(value.get("id"))
            else:
                self._raw_to_hydraulic[str(key)] = str(value)
        selected_cells = (
            self._hydraulic_view.get("hydraulic_cells", [])
            if self.uses_hydraulic_view
            else self._topology.get("cells", [])
        )

        parameter_cells = dict(parameters.cells)
        self._cells: dict[str, _Cell] = {}
        self._cell_parameters = parameter_cells
        for raw in selected_cells:
            cell_id = str(raw["id"])
            if cell_id in self._cells:
                raise SchemaError(f"duplicate cell {cell_id}")
            if cell_id not in parameter_cells:
                raise SchemaError(f"missing calibrated parameters for cell {cell_id}")
            length = float(raw["length_m"])
            lanes = int(raw.get("lane_count", len(raw.get("lanes", raw.get("lane_ids", []))) or 1))
            configured_storage = float(raw.get("storage_veh", math.inf))
            parameter_storage = parameter_cells[cell_id].rho_jam_veh_per_m_lane * length * lanes
            storage = min(configured_storage, parameter_storage)
            if length <= 0.0 or lanes <= 0 or storage <= 0.0:
                raise SchemaError(f"invalid geometry/storage for cell {cell_id}")
            if self.uses_hydraulic_view:
                minimum_time = float(raw.get("minimum_travel_time_sec", 0.0))
                delay_steps = int(
                    raw.get(
                        "delay_buffer_steps",
                        max(1, math.ceil(minimum_time / parameters.urban_dt_sec - _EPS)),
                    )
                )
            else:
                minimum_time = 0.0
                delay_steps = 1
            flow_length = float(raw.get("flow_length_m", length / delay_steps))
            if flow_length <= 0.0:
                raise SchemaError(f"invalid hydraulic flow_length_m for {cell_id}")
            cfl_limit = min(
                flow_length / parameter_cells[cell_id].v_free_mps,
                flow_length / parameter_cells[cell_id].w_mps,
            )
            if parameters.urban_dt_sec > cfl_limit + _EPS:
                raise SchemaError(
                    f"CFL violation for {cell_id}: urban_dt_sec={parameters.urban_dt_sec} > {cfl_limit}"
                )
            if delay_steps <= 0:
                raise SchemaError(f"invalid delay_buffer_steps for {cell_id}")
            if minimum_time > 0.0 and delay_steps < math.ceil(minimum_time / parameters.urban_dt_sec - _EPS):
                raise SchemaError(f"hydraulic cell {cell_id} understates its minimum travel time")
            buffer_ids = tuple(f"buffer:{cell_id}:stage:{index}" for index in range(delay_steps - 1))
            self._cells[cell_id] = _Cell(
                cell_id=cell_id,
                lane_group_id=str(
                    raw.get(
                        "lane_group_id",
                        (raw.get("lane_group_ids") or [f"hydraulic:{cell_id}"])[0],
                    )
                ),
                link_id=str(raw.get("link_id", raw.get("source", {}).get("vissim_no", ""))),
                length_m=length,
                flow_length_m=flow_length,
                lane_count=lanes,
                storage_veh=storage,
                delay_buffer_ids=buffer_ids,
            )
        if set(parameter_cells) != set(self._cells):
            raise SchemaError("PlantParameters contains cells outside the topology")

        self._lane_group_cells: dict[str, list[str]] = {}
        raw_cells = {str(item["id"]): item for item in selected_cells}
        for cell_id, cell in self._cells.items():
            self._lane_group_cells.setdefault(cell.lane_group_id, []).append(cell_id)
        for group_id, cell_ids in self._lane_group_cells.items():
            cell_ids.sort(key=lambda cell_id: int(raw_cells[cell_id].get("ordered_index", 0)))

        self._priorities = dict(parameters.node_priorities)
        self._saturation = dict(parameters.saturation_flow_vehps)
        self._startup_loss = dict(parameters.startup_loss_sec)
        self._parameter_ratios = {key: dict(value) for key, value in parameters.movement_turn_ratios}
        self._edges: list[_Edge] = []
        self._movement_edges: dict[str, _Edge] = {}
        self._source_boundaries: dict[str, list[_Edge]] = {}
        self._sink_edges: list[_Edge] = []
        self._build_edges(raw_cells)
        self._validate_turn_ratios()

        self._gates_by_movement: dict[str, list[dict[str, Any]]] = {}
        for gate in self._topology.get("signal_gates", []):
            for movement_id in gate.get("controlled_movement_ids", []):
                self._gates_by_movement.setdefault(str(movement_id), []).append(gate)
        unknown_gated = set(self._gates_by_movement) - set(self._movement_edges)
        if unknown_gated:
            raise SchemaError(f"hydraulic graph dropped signal-controlled movements: {sorted(unknown_gated)}")
        self._groups = {str(item["id"]): item for item in self._topology.get("signal_groups", [])}
        self._fixed_schedules = {
            str(item["controller_id"]): item for item in self._topology.get("schedules", {}).get("fixed", [])
        }
        self._known_authority_ids = set(map(str, self._topology.get("control_authority_ids", [])))

    @property
    def required_travel_time_buffer_ids(self) -> tuple[str, ...]:
        return tuple(sorted(buffer_id for cell in self._cells.values() for buffer_id in cell.delay_buffer_ids))

    def _endpoint_cell(self, movement: Mapping[str, Any], source: bool) -> str:
        direct = movement.get("source_cell_id" if source else "target_cell_id")
        if direct is not None:
            cell_id = self._raw_to_hydraulic.get(str(direct), str(direct))
            if cell_id not in self._cells:
                raise SchemaError(f"movement references unknown cell {cell_id}")
            return cell_id
        group_id = str(movement["source_lane_group_id" if source else "target_lane_group_id"])
        try:
            cells = self._lane_group_cells[group_id]
        except KeyError as exc:
            raise SchemaError(f"movement references unresolved lane group {group_id}") from exc
        return cells[-1] if source else cells[0]

    def _movement_ratios(self, movement: Mapping[str, Any]) -> tuple[tuple[str, float], ...]:
        movement_id = str(movement["id"])
        configured = self._parameter_ratios.get(movement_id)
        raw = movement.get("turn_ratio")
        if configured is None and raw is not None:
            configured = {"*": float(raw)}
        if configured is None:
            raise SchemaError(
                f"movement {movement_id} has unresolved turn_ratio; supply PlantParameters.movement_turn_ratios"
            )
        return tuple(sorted((str(key), float(value)) for key, value in configured.items()))

    def _hydraulic_movement_endpoint(self, movement: Mapping[str, Any], source: bool) -> str:
        group_field = "source_lane_group_id" if source else "target_lane_group_id"
        groups_field = "source_lane_group_ids" if source else "target_lane_group_ids"
        groups = list(movement.get(groups_field, []))
        if movement.get(group_field) is not None:
            groups.append(movement[group_field])
        raw_cells = [
            item
            for item in self._topology.get("cells", [])
            if str(item.get("lane_group_id")) in set(map(str, groups))
            and str(item.get("id")) in self._raw_to_hydraulic
        ]
        raw_cells.sort(key=lambda item: (int(item.get("ordered_index", 0)), str(item["id"])))
        if not raw_cells:
            raise SchemaError(f"movement {movement.get('id')} has no hydraulic endpoint")
        raw_id = str(raw_cells[-1 if source else 0]["id"])
        return self._raw_to_hydraulic[raw_id]

    def _build_edges(self, raw_cells: Mapping[str, Mapping[str, Any]]) -> None:
        transfer_edges = self._hydraulic_view.get("transfer_edges") if self.uses_hydraulic_view else None
        if transfer_edges is not None:
            transfer_pairs: set[tuple[str, str]] = set()
            movement_pairs: set[tuple[str, str]] = set()
            for raw in sorted(transfer_edges, key=lambda item: str(item["id"])):
                edge_id = str(raw["id"])
                source_value = raw.get(
                    "source_hydraulic_cell_id",
                    raw.get("source_cell_id", (raw.get("upstream_hydraulic_ids") or [None])[0]),
                )
                target_value = raw.get(
                    "target_hydraulic_cell_id",
                    raw.get("target_cell_id", (raw.get("downstream_hydraulic_ids") or [None])[0]),
                )
                source_id = self._raw_to_hydraulic.get(str(source_value), str(source_value))
                target_id = self._raw_to_hydraulic.get(str(target_value), str(target_value))
                if source_id not in self._cells or target_id not in self._cells:
                    raise SchemaError(f"hydraulic transfer edge {edge_id} has unresolved endpoints")
                delay_steps = int(raw.get("delay_steps", 1))
                if delay_steps > 1:
                    raise SchemaError(
                        f"multi-step transfer edge {edge_id} must be an explicit hydraulic travel-time-buffer cell"
                    )
                movement_ids = list(raw.get("movement_ids", []))
                movement_id = raw.get("movement_id", movement_ids[0] if len(movement_ids) == 1 else None)
                if movement_id is not None:
                    movement_id = str(movement_id)
                    ratio_source = {
                        "id": movement_id,
                        "turn_ratio": raw.get("turn_ratio"),
                    }
                    ratios = self._movement_ratios(ratio_source)
                    kind = "movement"
                else:
                    ratio_values = raw.get("turn_ratios", {"*": raw.get("turn_ratio", 1.0)})
                    ratios = tuple(sorted((str(key), float(value)) for key, value in ratio_values.items()))
                    kind = str(raw.get("kind", "zero_storage_transfer"))
                edge = _Edge(
                    edge_id,
                    source_id,
                    target_id,
                    kind,
                    movement_id,
                    None,
                    ratios,
                    self._priorities.get(
                        movement_id or edge_id,
                        float(raw.get("priority", 1.0)),
                    ),
                )
                self._edges.append(edge)
                transfer_pairs.add((source_id, target_id))
                if movement_id is not None:
                    if movement_id in self._movement_edges:
                        raise SchemaError(f"duplicate hydraulic movement {movement_id}")
                    self._movement_edges[movement_id] = edge
                    movement_pairs.add((source_id, target_id))

            for movement in sorted(self._topology.get("movements", []), key=lambda item: str(item["id"])):
                movement_id = str(movement["id"])
                if movement_id in self._movement_edges:
                    continue
                source_id = self._hydraulic_movement_endpoint(movement, True)
                target_id = self._hydraulic_movement_endpoint(movement, False)
                if source_id == target_id:
                    continue
                edge = _Edge(
                    movement_id,
                    source_id,
                    target_id,
                    "movement",
                    movement_id,
                    None,
                    self._movement_ratios(movement),
                    self._priorities.get(movement_id, float(movement.get("priority", 1.0))),
                )
                self._edges.append(edge)
                self._movement_edges[movement_id] = edge
                movement_pairs.add((source_id, target_id))

            for raw in sorted(self._hydraulic_view.get("hydraulic_cells", []), key=lambda item: str(item["id"])):
                source_id = str(raw["id"])
                for target_id in sorted(map(str, raw.get("downstream_hydraulic_ids", []))):
                    pair = (source_id, target_id)
                    if pair in transfer_pairs or pair in movement_pairs:
                        continue
                    edge_id = f"hydraulic-transfer:{source_id}->{target_id}"
                    self._edges.append(
                        _Edge(
                            edge_id,
                            source_id,
                            target_id,
                            "zero_storage_transfer",
                            None,
                            None,
                            (("*", 1.0),),
                            self._priorities.get(edge_id, 1.0),
                        )
                    )
        else:
            for group_id, cell_ids in sorted(self._lane_group_cells.items()):
                for left, right in zip(cell_ids, cell_ids[1:]):
                    edge_id = f"internal:{left}->{right}"
                    self._edges.append(
                        _Edge(edge_id, left, right, "internal", None, None, (("*", 1.0),), self._priorities.get(edge_id, 1.0))
                    )

            for movement in sorted(self._topology.get("movements", []), key=lambda item: str(item["id"])):
                movement_id = str(movement["id"])
                edge = _Edge(
                    movement_id,
                    self._endpoint_cell(movement, True),
                    self._endpoint_cell(movement, False),
                    "movement",
                    movement_id,
                    None,
                    self._movement_ratios(movement),
                    self._priorities.get(movement_id, float(movement.get("priority", 1.0))),
                )
                self._edges.append(edge)
                self._movement_edges[movement_id] = edge

        for boundary in sorted(self._topology.get("boundaries", []), key=lambda item: str(item["id"])):
            if str(boundary.get("type")) != "source":
                continue
            boundary_id = str(boundary["id"])
            targets = self._resolve_boundary_cells(boundary, source=True)
            shares = boundary.get("target_shares", {})
            if shares:
                beta = {str(key): float(value) for key, value in shares.items()}
            else:
                beta = {target: 1.0 / len(targets) for target in targets}
            if set(beta) != set(targets) or any(value < 0.0 for value in beta.values()):
                raise SchemaError(f"boundary {boundary_id} target_shares do not match target cells")
            if abs(sum(beta.values()) - 1.0) > MASS_TOLERANCE_VEH:
                raise SchemaError(f"boundary {boundary_id} target_shares must sum to 1")
            edges = []
            for target in targets:
                edge_id = f"source:{boundary_id}->{target}"
                edge = _Edge(
                    edge_id,
                    boundary_id,
                    target,
                    "source",
                    None,
                    boundary_id,
                    (("*", beta[target]),),
                    self._priorities.get(edge_id, self._priorities.get(boundary_id, 1.0)),
                )
                edges.append(edge)
                self._edges.append(edge)
            self._source_boundaries[boundary_id] = edges

        existing_out = {edge.source_id for edge in self._edges if edge.kind != "source"}
        explicit_sinks = [item for item in self._topology.get("boundaries", []) if str(item.get("type")) == "sink"]
        sink_cells: list[tuple[str, str]] = []
        for boundary in explicit_sinks:
            boundary_id = str(boundary["id"])
            sink_cells.extend((boundary_id, cell_id) for cell_id in self._resolve_boundary_cells(boundary, source=False))
        explicit_cells = {cell_id for _, cell_id in sink_cells}
        for cell_id in sorted(set(self._cells) - existing_out - explicit_cells):
            sink_cells.append((f"boundary:sink:{cell_id}", cell_id))
        for boundary_id, cell_id in sorted(sink_cells):
            edge_id = f"sink:{cell_id}->{boundary_id}"
            edge = _Edge(edge_id, cell_id, None, "sink", None, boundary_id, (("*", 1.0),), 1.0)
            self._edges.append(edge)
            self._sink_edges.append(edge)

    def _resolve_boundary_cells(self, boundary: Mapping[str, Any], *, source: bool) -> list[str]:
        key = "target_cell_ids" if source else "source_cell_ids"
        singular = "target_cell_id" if source else "source_cell_id"
        if boundary.get(key):
            result = [self._raw_to_hydraulic.get(str(value), str(value)) for value in boundary[key]]
        elif boundary.get(singular):
            raw_id = str(boundary[singular])
            result = [self._raw_to_hydraulic.get(raw_id, raw_id)]
        elif boundary.get("lane_group_id"):
            cells = self._lane_group_cells.get(str(boundary["lane_group_id"]), [])
            result = [cells[0] if source else cells[-1]] if cells else []
        elif boundary.get("link_id"):
            link_id = str(boundary["link_id"])
            groups = sorted({cell.lane_group_id for cell in self._cells.values() if cell.link_id == link_id})
            result = [self._lane_group_cells[group][0 if source else -1] for group in groups]
        else:
            result = []
        if not result or any(cell_id not in self._cells for cell_id in result):
            raise SchemaError(f"boundary {boundary.get('id')} has unresolved cell ownership")
        return sorted(set(result))

    def _validate_turn_ratios(self) -> None:
        outgoing: dict[str, list[_Edge]] = {}
        for edge in self._edges:
            if edge.kind != "source":
                outgoing.setdefault(edge.source_id, []).append(edge)
        for source_id, edges in outgoing.items():
            classes = {key for edge in edges for key, _ in edge.turn_ratios if key != "*"} or {"*"}
            for class_id in classes:
                total = 0.0
                for edge in edges:
                    ratios = dict(edge.turn_ratios)
                    if class_id in ratios:
                        total += ratios[class_id]
                    elif "*" in ratios:
                        total += ratios["*"]
                    else:
                        raise SchemaError(f"missing turn ratio for {source_id}/{class_id}/{edge.edge_id}")
                if abs(total - 1.0) > MASS_TOLERANCE_VEH:
                    raise SchemaError(f"turn ratios for {source_id}/{class_id} sum to {total}, not 1")

    def _invalid(
        self,
        state: PlantState,
        action: ControlAction | StepAction | None,
        demand: DemandSchedule | None,
        reason: str,
        message: str,
    ) -> StepResult:
        return StepResult(
            status=StepStatus.INVALID_INPUT,
            next_state=None,
            diagnostics=None,
            reason_code=reason,
            message=message,
            topology_hash=self.topology_hash,
            state_hash=state.state_hash,
            action_hash=None if action is None else action.action_hash,
            parameter_hash=self.parameters.parameter_hash,
            demand_hash=None if demand is None else demand.demand_hash,
            is_feasible=False,
            is_complete=False,
            completed_horizon_sec=0.0,
        )

    def _validate_step_inputs(
        self, state: PlantState, action: StepAction | None, demand: DemandSchedule, dt_sec: float
    ) -> str | None:
        if state.topology_hash != self.topology_hash:
            return "state_topology_hash_mismatch"
        if demand.topology_hash != self.topology_hash:
            return "demand_topology_hash_mismatch"
        if abs(dt_sec - self.parameters.urban_dt_sec) > _EPS:
            return "unsupported_dt_sec"
        cell_refs = dict(state.urban_cell_stock_id)
        source_refs = dict(state.source_queue_stock_id)
        buffer_refs = dict(state.travel_time_buffer_stock_id)
        if set(cell_refs) != set(self._cells):
            return "cell_stock_ownership_mismatch"
        if set(source_refs) != set(self._source_boundaries):
            return "source_stock_ownership_mismatch"
        if set(buffer_refs) != set(self.required_travel_time_buffer_ids):
            return "travel_time_buffer_stock_ownership_mismatch"
        stock_by_id = state.stock_by_id()
        for cell_id, stock_id in cell_refs.items():
            occupied = stock_by_id[stock_id].vehicle_count_veh + sum(
                stock_by_id[buffer_refs[buffer_id]].vehicle_count_veh
                for buffer_id in self._cells[cell_id].delay_buffer_ids
            )
            if occupied > self._cells[cell_id].storage_veh + MASS_TOLERANCE_VEH:
                return "cell_storage_exceeded"
        if action is not None:
            if action.topology_hash != self.topology_hash:
                return "action_topology_hash_mismatch"
            if action.based_on_state_hash != state.state_hash:
                return "stale_action_state_hash"
            if action.decision_time_sec > state.sim_time_sec + _EPS:
                return "action_from_future"
            if not (action.valid_from_sec - _EPS <= state.sim_time_sec < action.valid_until_sec - _EPS):
                return "action_outside_validity"
            commands = set(dict(action.signal_green_fraction)) | set(dict(action.movement_capacity_vehps))
            known = set(self._movement_edges) | {str(gate["id"]) for gates in self._gates_by_movement.values() for gate in gates}
            if not commands.issubset(known):
                return "unknown_action_command_id"
            if self._known_authority_ids and not commands.issubset(self._known_authority_ids):
                return "action_authority_violation"
        try:
            rates = demand.rates_for_interval(state.sim_time_sec, state.sim_time_sec + dt_sec)
        except SchemaError:
            return "demand_interval_uncovered"
        if not set(rates).issubset(set(self._source_boundaries)):
            return "unknown_demand_boundary"
        stock_by_id = state.stock_by_id()
        cell_refs = dict(state.urban_cell_stock_id)
        edges_by_source: dict[str, list[_Edge]] = {}
        for edge in self._edges:
            if edge.source_id in self._cells:
                edges_by_source.setdefault(edge.source_id, []).append(edge)
        for source_id, edges in edges_by_source.items():
            counts = dict(stock_by_id[cell_refs[source_id]].class_counts_veh)
            for class_id, count in counts.items():
                if count <= _EPS:
                    continue
                total = 0.0
                for edge in edges:
                    ratios = dict(edge.turn_ratios)
                    ratio = ratios.get(class_id, ratios.get("*"))
                    if ratio is None:
                        return "missing_class_turn_ratio"
                    total += ratio
                if abs(total - 1.0) > MASS_TOLERANCE_VEH:
                    return "invalid_runtime_turn_ratio_sum"
        action_green = {} if action is None else dict(action.signal_green_fraction)
        try:
            for movement_id, gates in self._gates_by_movement.items():
                for gate in gates:
                    if str(gate["id"]) not in action_green and movement_id not in action_green:
                        self._fixed_gate_fraction(gate, state.sim_time_sec, state.sim_time_sec + dt_sec)
        except SchemaError:
            return "signal_schedule_unresolved"
        return None

    def _capacity_factors(self, demand: DemandSchedule, t0: float, t1: float) -> tuple[dict[str, float], dict[str, float]]:
        capacity = {cell_id: demand.global_incident_capacity_factor for cell_id in self._cells}
        speed = {cell_id: 1.0 for cell_id in self._cells}
        duration = t1 - t0
        for entry in demand.entries:
            if min(t1, entry.end_time_sec) <= max(t0, entry.start_time_sec):
                continue
            for incident in entry.incidents:
                overlap = max(0.0, min(t1, incident.end_time_sec) - max(t0, incident.start_time_sec))
                if overlap <= 0.0:
                    continue
                weight = overlap / duration
                for entity_id in incident.affected_entity_ids:
                    affected = [entity_id] if entity_id in self._cells else [
                        cell_id for cell_id, cell in self._cells.items() if entity_id in {cell.lane_group_id, cell.link_id}
                    ]
                    for cell_id in affected:
                        capacity[cell_id] *= 1.0 - weight * (1.0 - incident.capacity_factor)
                        speed[cell_id] *= 1.0 - weight * (1.0 - incident.speed_factor)
        return capacity, speed

    def _fixed_gate_fraction(self, gate: Mapping[str, Any], t0: float, t1: float) -> float:
        if "fixed_green_fraction" in gate:
            return float(gate["fixed_green_fraction"])
        group = self._groups.get(str(gate.get("signal_group_id")))
        if group is None:
            raise SchemaError(f"gate {gate.get('id')} has no resolvable signal group")
        controller_id = str(group.get("controller_id", f"sc:{group.get('controller_no')}"))
        schedule = self._fixed_schedules.get(controller_id)
        if schedule is None:
            raise SchemaError(f"gate {gate.get('id')} has no fixed schedule")
        program = schedule["program"]
        sg_no = str(group.get("sg_no"))
        timeline = program["sg_timelines"].get(sg_no)
        if timeline is None:
            raise SchemaError(f"fixed schedule has no SG {sg_no}")
        cycle = float(program["cycle_length_sec"])
        phase = (
            t0
            + float(self._topology.get("simulation", {}).get("start_time_sec", 0.0))
            - float(schedule.get("cycle_epoch_sec", 0.0))
            - float(program.get("program_offset_sec", 0.0))
            - float(schedule.get("controller_offset_sec", 0.0))
        ) % cycle
        return _periodic_green_overlap(
            timeline["intervals"],
            phase,
            t1 - t0,
            cycle,
            self._startup_loss.get(str(gate["id"]), 0.0),
        ) / (t1 - t0)

    def _movement_capacity(
        self,
        edge: _Edge,
        action: StepAction | None,
        t0: float,
        t1: float,
        incident_factor: float,
    ) -> float:
        assert edge.movement_id is not None
        action_capacity = {} if action is None else dict(action.movement_capacity_vehps)
        if edge.movement_id in action_capacity:
            base = action_capacity[edge.movement_id]
        else:
            base = self._saturation.get(edge.movement_id, self._cell_parameters[edge.source_id].q_max_vehps)
        gates = self._gates_by_movement.get(edge.movement_id, [])
        if not gates:
            return base * incident_factor
        action_green = {} if action is None else dict(action.signal_green_fraction)
        factors = []
        for gate in gates:
            gate_id = str(gate["id"])
            if gate_id in action_green:
                factors.append(action_green[gate_id])
            elif edge.movement_id in action_green:
                factors.append(action_green[edge.movement_id])
            else:
                factors.append(self._fixed_gate_fraction(gate, t0, t1))
            base = min(base, self._saturation.get(gate_id, base))
        return base * min(factors) * incident_factor

    def step(
        self,
        state: PlantState,
        action: ControlAction | StepAction | None,
        demand: DemandSchedule,
        dt_sec: float,
        subgraph_view: Any = None,
    ) -> StepResult:
        """Advance exactly one urban CTM interval without mutating inputs."""

        if subgraph_view is not None:
            return self._invalid(state, action, demand, "subgraph_not_implemented", "Phase 1 supports the full urban graph only")
        try:
            normalized = action.to_step_action() if isinstance(action, ControlAction) else action
        except SchemaError as exc:
            return self._invalid(state, action, demand, "action_normalization_failed", str(exc))
        dt = float(dt_sec)
        reason = self._validate_step_inputs(state, normalized, demand, dt)
        if reason:
            return self._invalid(state, action, demand, reason, reason.replace("_", " "))

        t0 = state.sim_time_sec
        t1 = t0 + dt
        stock_by_id = state.stock_by_id()
        cell_refs = dict(state.urban_cell_stock_id)
        source_refs = dict(state.source_queue_stock_id)
        buffer_refs = dict(state.travel_time_buffer_stock_id)
        cell_counts = {
            cell_id: dict(stock_by_id[stock_id].class_counts_veh) for cell_id, stock_id in cell_refs.items()
        }
        buffer_counts = {
            buffer_id: dict(stock_by_id[stock_id].class_counts_veh)
            for buffer_id, stock_id in buffer_refs.items()
        }
        queue_counts = {
            boundary_id: dict(stock_by_id[stock_id].class_counts_veh)
            for boundary_id, stock_id in source_refs.items()
        }
        demand_rates = demand.rates_for_interval(t0, t1)
        arrivals_by_class: dict[str, float] = {}
        for boundary_id in self._source_boundaries:
            rates = demand_rates.get(boundary_id, {})
            arrivals = {class_id: rate * dt for class_id, rate in rates.items()}
            queue_counts[boundary_id] = _sum_maps(queue_counts[boundary_id], arrivals)
            arrivals_by_class = _sum_maps(arrivals_by_class, arrivals)

        capacity_factor, speed_factor = self._capacity_factors(demand, t0, t1)
        sending: dict[str, float] = {}
        receiving: dict[str, float] = {}
        for cell_id, cell in self._cells.items():
            params = self._cell_parameters[cell_id]
            count = sum(cell_counts[cell_id].values())
            occupied = count + sum(
                sum(buffer_counts[buffer_id].values()) for buffer_id in cell.delay_buffer_ids
            )
            qmax = params.q_max_vehps * capacity_factor[cell_id]
            sending[cell_id] = min(
                params.v_free_mps * speed_factor[cell_id] * count / cell.flow_length_m,
                qmax,
                count / dt,
            )
            receiving[cell_id] = min(
                qmax,
                params.w_mps * max(0.0, cell.storage_veh - occupied) / cell.flow_length_m,
                max(0.0, cell.storage_veh - occupied) / dt,
            )

        edges_by_source: dict[str, list[_Edge]] = {}
        for edge in self._edges:
            edges_by_source.setdefault(edge.source_id, []).append(edge)
        original: dict[str, dict[str, float]] = {}
        for source_id, edges in sorted(edges_by_source.items()):
            if source_id in self._cells:
                counts = cell_counts[source_id]
                total = sum(counts.values())
                source_rate = sending[source_id]
            else:
                counts = queue_counts[source_id]
                total = sum(counts.values())
                source_rate = total / dt
            for edge in edges:
                ratios = dict(edge.turn_ratios)
                flows: dict[str, float] = {}
                for class_id, count in counts.items():
                    ratio = ratios.get(class_id, ratios.get("*"))
                    if ratio is None:
                        raise SchemaError(f"missing runtime turn ratio for {source_id}/{class_id}")
                    flows[class_id] = source_rate * (count / total if total > _EPS else 0.0) * ratio
                original[edge.edge_id] = flows

        capped: dict[str, dict[str, float]] = {}
        for edge in self._edges:
            flow = original[edge.edge_id]
            total = sum(flow.values())
            if edge.kind == "movement":
                cap = self._movement_capacity(edge, normalized, t0, t1, capacity_factor[edge.source_id])
            else:
                cap = math.inf
            capped[edge.edge_id] = _scale(flow, min(1.0, cap / total) if total > _EPS else 0.0)

        preliminary_total = {edge.edge_id: sum(capped[edge.edge_id].values()) for edge in self._edges}
        incoming_by_target: dict[str, list[_Edge]] = {}
        for edge in self._edges:
            if edge.target_cell_id is not None:
                incoming_by_target.setdefault(edge.target_cell_id, []).append(edge)
        allocated_total = dict(preliminary_total)
        for target_id, edges in sorted(incoming_by_target.items()):
            demands = {edge.edge_id: preliminary_total[edge.edge_id] for edge in edges}
            priorities = {edge.edge_id: edge.priority for edge in edges}
            allocated = _priority_allocate(demands, priorities, receiving[target_id])
            allocated_total.update(allocated)

        edge_scale = {
            edge.edge_id: (
                min(1.0, allocated_total[edge.edge_id] / sum(original[edge.edge_id].values()))
                if sum(original[edge.edge_id].values()) > _EPS
                else 0.0
            )
            for edge in self._edges
        }
        class_alpha: dict[tuple[str, str], float] = {}
        for source_id, edges in edges_by_source.items():
            classes = {class_id for edge in edges for class_id, value in original[edge.edge_id].items() if value > _EPS}
            for class_id in classes:
                relevant = [edge_scale[edge.edge_id] for edge in edges if original[edge.edge_id].get(class_id, 0.0) > _EPS]
                class_alpha[(source_id, class_id)] = min(relevant) if relevant else 0.0
        actual = {
            edge.edge_id: {
                class_id: value * class_alpha.get((edge.source_id, class_id), 0.0)
                for class_id, value in original[edge.edge_id].items()
            }
            for edge in self._edges
        }

        outgoing: dict[str, dict[str, float]] = {}
        incoming: dict[str, dict[str, float]] = {}
        sink_step: dict[str, dict[str, float]] = {}
        movement_step: dict[str, float] = {}
        boundary_admitted: dict[str, float] = {}
        for edge in self._edges:
            vehicles = _scale(actual[edge.edge_id], dt)
            outgoing[edge.source_id] = _sum_maps(outgoing.get(edge.source_id, {}), vehicles)
            if edge.target_cell_id is not None:
                incoming[edge.target_cell_id] = _sum_maps(incoming.get(edge.target_cell_id, {}), vehicles)
            if edge.kind == "sink" and edge.boundary_id is not None:
                sink_step[edge.boundary_id] = _sum_maps(sink_step.get(edge.boundary_id, {}), vehicles)
            if edge.kind == "movement" and edge.movement_id is not None:
                movement_step[edge.movement_id] = movement_step.get(edge.movement_id, 0.0) + sum(vehicles.values())
            if edge.kind == "source" and edge.boundary_id is not None:
                boundary_admitted[edge.boundary_id] = boundary_admitted.get(edge.boundary_id, 0.0) + sum(vehicles.values())

        next_cell: dict[str, dict[str, float]] = {}
        next_queue: dict[str, dict[str, float]] = {}
        all_classes = set(arrivals_by_class)
        for counts in cell_counts.values():
            all_classes.update(counts)
        for counts in buffer_counts.values():
            all_classes.update(counts)
        for counts in queue_counts.values():
            all_classes.update(counts)
        buffer_shift: dict[str, dict[str, float]] = {}
        for cell_id, cell in self._cells.items():
            qmax_veh = self._cell_parameters[cell_id].q_max_vehps * capacity_factor[cell_id] * dt
            for buffer_id in cell.delay_buffer_ids:
                counts = buffer_counts[buffer_id]
                total = sum(counts.values())
                buffer_shift[buffer_id] = _scale(counts, min(1.0, qmax_veh / total) if total > _EPS else 0.0)
        for cell_id, counts in cell_counts.items():
            cell = self._cells[cell_id]
            if cell.delay_buffer_ids:
                hydraulic_incoming = buffer_shift[cell.delay_buffer_ids[-1]]
            else:
                hydraulic_incoming = incoming.get(cell_id, {})
            result = {
                class_id: counts.get(class_id, 0.0)
                + hydraulic_incoming.get(class_id, 0.0)
                - outgoing.get(cell_id, {}).get(class_id, 0.0)
                for class_id in all_classes
            }
            next_cell[cell_id] = result
        next_buffer: dict[str, dict[str, float]] = {}
        for cell_id, cell in self._cells.items():
            for index, buffer_id in enumerate(cell.delay_buffer_ids):
                upstream = incoming.get(cell_id, {}) if index == 0 else buffer_shift[cell.delay_buffer_ids[index - 1]]
                next_buffer[buffer_id] = {
                    class_id: buffer_counts[buffer_id].get(class_id, 0.0)
                    + upstream.get(class_id, 0.0)
                    - buffer_shift[buffer_id].get(class_id, 0.0)
                    for class_id in all_classes
                }
        for boundary_id, counts in queue_counts.items():
            next_queue[boundary_id] = {
                class_id: counts.get(class_id, 0.0) - outgoing.get(boundary_id, {}).get(class_id, 0.0)
                for class_id in all_classes
            }
        if any(
            value < 0.0
            for counts in list(next_cell.values()) + list(next_queue.values()) + list(next_buffer.values())
            for value in counts.values()
        ):
            return StepResult(
                StepStatus.NUMERICAL_ERROR, None, None, "negative_stock", "node solver produced negative stock",
                self.topology_hash, state.state_hash, None if action is None else action.action_hash,
                self.parameters.parameter_hash, demand.demand_hash, False, False, 0.0,
            )
        if any(
            sum(next_cell[cell_id].values())
            + sum(sum(next_buffer[buffer_id].values()) for buffer_id in self._cells[cell_id].delay_buffer_ids)
            > self._cells[cell_id].storage_veh + MASS_TOLERANCE_VEH
            for cell_id in self._cells
        ):
            return StepResult(
                StepStatus.NUMERICAL_ERROR, None, None, "storage_overflow", "node solver exceeded cell storage",
                self.topology_hash, state.state_hash, None if action is None else action.action_hash,
                self.parameters.parameter_hash, demand.demand_hash, False, False, 0.0,
            )

        next_stocks = []
        for cell_id, stock_id in sorted(cell_refs.items()):
            counts = next_cell[cell_id]
            next_stocks.append(VehicleStock(stock_id, "urban_cell", cell_id, sum(counts.values()), counts))
        for boundary_id, stock_id in sorted(source_refs.items()):
            counts = next_queue[boundary_id]
            next_stocks.append(VehicleStock(stock_id, "boundary_source_queue", boundary_id, sum(counts.values()), counts))
        for buffer_id, stock_id in sorted(buffer_refs.items()):
            counts = next_buffer[buffer_id]
            next_stocks.append(VehicleStock(stock_id, "travel_time_buffer", buffer_id, sum(counts.values()), counts))

        cumulative_movement = dict(state.cumulative_movement_flow_veh)
        for key, value in movement_step.items():
            cumulative_movement[key] = cumulative_movement.get(key, 0.0) + value
        cumulative_admitted = dict(state.cumulative_admitted_veh)
        for key, value in boundary_admitted.items():
            cumulative_admitted[key] = cumulative_admitted.get(key, 0.0) + value
        cumulative_sink = {key: dict(value) for key, value in state.cumulative_sink_outflow_veh}
        for key, counts in sink_step.items():
            cumulative_sink[key] = _sum_maps(cumulative_sink.get(key, {}), counts)
        next_state = PlantState(
            topology_hash=self.topology_hash,
            sim_time_sec=t1,
            stocks=tuple(next_stocks),
            urban_cell_stock_id=state.urban_cell_stock_id,
            source_queue_stock_id=state.source_queue_stock_id,
            travel_time_buffer_stock_id=state.travel_time_buffer_stock_id,
            cumulative_movement_flow_veh=cumulative_movement,
            cumulative_admitted_veh=cumulative_admitted,
            cumulative_sink_outflow_veh=cumulative_sink,
        )

        previous_by_class = state.inventory_by_class()
        next_by_class = next_state.inventory_by_class()
        exited_by_class: dict[str, float] = {}
        for counts in sink_step.values():
            exited_by_class = _sum_maps(exited_by_class, counts)
        residual_by_class = {
            class_id: next_by_class.get(class_id, 0.0)
            - previous_by_class.get(class_id, 0.0)
            - arrivals_by_class.get(class_id, 0.0)
            + exited_by_class.get(class_id, 0.0)
            for class_id in sorted(all_classes | set(exited_by_class))
        }
        residual = sum(residual_by_class.values())
        if abs(residual) > MASS_TOLERANCE_VEH or any(abs(value) > MASS_TOLERANCE_VEH for value in residual_by_class.values()):
            return StepResult(
                StepStatus.NUMERICAL_ERROR, None, None, "mass_conservation_violation", str(residual_by_class),
                self.topology_hash, state.state_hash, None if action is None else action.action_hash,
                self.parameters.parameter_hash, demand.demand_hash, False, False, 0.0,
            )
        spillback = tuple(
            sorted(
                cell_id
                for cell_id, cell in self._cells.items()
                if sum(next_cell[cell_id].values())
                + sum(sum(next_buffer[buffer_id].values()) for buffer_id in cell.delay_buffer_ids)
                >= cell.storage_veh - MASS_TOLERANCE_VEH
                or (
                    receiving[cell_id] <= _EPS
                    and sum(cell_counts[cell_id].values())
                    + sum(sum(buffer_counts[buffer_id].values()) for buffer_id in cell.delay_buffer_ids)
                    >= cell.storage_veh - MASS_TOLERANCE_VEH
                )
            )
        )
        interface_ids = {
            str(item["id"]) for item in self._topology.get("boundaries", []) if bool(item.get("is_interface", False))
        }
        interface_flow = {
            key: boundary_admitted.get(key, 0.0) + sum(sink_step.get(key, {}).values()) for key in interface_ids
        }
        diagnostics = StepDiagnostics(
            mass_residual_veh=residual,
            mass_residual_by_class_veh=tuple(sorted(residual_by_class.items())),
            external_admitted_in_veh=sum(arrivals_by_class.values()),
            external_demand_arrivals_veh=sum(arrivals_by_class.values()),
            external_demand_arrivals_by_class_veh=tuple(sorted(arrivals_by_class.items())),
            boundary_admitted_veh=tuple(sorted(boundary_admitted.items())),
            sink_outflow_veh=tuple(sorted((key, sum(value.values())) for key, value in sink_step.items())),
            sink_outflow_by_class_veh=tuple(sorted((key, tuple(sorted(value.items()))) for key, value in sink_step.items())),
            movement_flow_veh=tuple(sorted(movement_step.items())),
            interface_flow_veh=tuple(sorted(interface_flow.items())),
            cell_sending_vehps=tuple(sorted(sending.items())),
            cell_receiving_vehps=tuple(sorted(receiving.items())),
            spillback_cell_ids=spillback,
            no_clamp_delete=True,
        )
        return StepResult(
            status=StepStatus.OK,
            next_state=next_state,
            diagnostics=diagnostics,
            reason_code=None,
            message=None,
            topology_hash=self.topology_hash,
            state_hash=state.state_hash,
            action_hash=None if action is None else action.action_hash,
            parameter_hash=self.parameters.parameter_hash,
            demand_hash=demand.demand_hash,
            is_feasible=True,
            is_complete=True,
            completed_horizon_sec=dt,
        )

    @staticmethod
    def _committed_hash(action: ActionSchedule | ControlAction | StepAction | None) -> str:
        if isinstance(action, ActionSchedule):
            return action.schedule_hash
        if action is None:
            return "fixed"
        return action.action_hash

    @staticmethod
    def _committed_actions(
        action: ActionSchedule | ControlAction | StepAction | None,
    ) -> tuple[ControlAction | StepAction, ...]:
        if isinstance(action, ActionSchedule):
            return tuple(entry.action for entry in action.entries)
        return () if action is None else (action,)

    def _validate_committed_basis(
        self,
        action: ActionSchedule | ControlAction | StepAction | None,
        state: PlantState,
    ) -> str | None:
        for item in self._committed_actions(action):
            if item.topology_hash != self.topology_hash:
                return "action_topology_hash_mismatch"
            if item.based_on_state_hash != state.state_hash:
                return "stale_action_state_hash"
        return None

    @staticmethod
    def _action_at(
        action: ActionSchedule | ControlAction | StepAction | None,
        time_sec: float,
    ) -> ControlAction | StepAction | None:
        if not isinstance(action, ActionSchedule):
            return action
        for entry in action.entries:
            if entry.start_time_sec - _EPS <= time_sec < entry.end_time_sec - _EPS:
                return entry.action
        raise SchemaError(f"action schedule does not cover time {time_sec}")

    @staticmethod
    def _rebase_action(action: ControlAction | StepAction | None, state: PlantState) -> StepAction | None:
        if action is None:
            return None
        normalized = action.to_step_action() if isinstance(action, ControlAction) else action
        return StepAction(
            action_id=normalized.action_id,
            topology_hash=normalized.topology_hash,
            based_on_state_hash=state.state_hash,
            decision_time_sec=normalized.decision_time_sec,
            valid_from_sec=normalized.valid_from_sec,
            valid_until_sec=normalized.valid_until_sec,
            signal_green_fraction=normalized.signal_green_fraction,
            movement_capacity_vehps=normalized.movement_capacity_vehps,
            ramp_metering_vehps=normalized.ramp_metering_vehps,
            vsl_mps=normalized.vsl_mps,
            authority_ids=normalized.authority_ids,
        )

    @staticmethod
    def _aggregate_diagnostics(values: Iterable[StepDiagnostics]) -> StepDiagnostics:
        items = tuple(values)

        def sum_pairs(name: str) -> tuple[tuple[str, float], ...]:
            result: dict[str, float] = {}
            for item in items:
                for key, value in getattr(item, name):
                    result[key] = result.get(key, 0.0) + value
            return tuple(sorted(result.items()))

        sink_classes: dict[str, dict[str, float]] = {}
        interface_classes: dict[str, dict[str, float]] = {}
        for item in items:
            for sink_id, counts in item.sink_outflow_by_class_veh:
                sink_classes[sink_id] = _sum_maps(sink_classes.get(sink_id, {}), dict(counts))
            for interface_id, counts in item.interface_transfer_by_class_veh:
                interface_classes[interface_id] = _sum_maps(
                    interface_classes.get(interface_id, {}), dict(counts)
                )
        last = items[-1] if items else None
        return StepDiagnostics(
            mass_residual_veh=sum(item.mass_residual_veh for item in items),
            mass_residual_by_class_veh=sum_pairs("mass_residual_by_class_veh"),
            external_admitted_in_veh=sum(item.external_admitted_in_veh for item in items),
            external_demand_arrivals_veh=sum(item.external_demand_arrivals_veh for item in items),
            external_demand_arrivals_by_class_veh=sum_pairs("external_demand_arrivals_by_class_veh"),
            boundary_admitted_veh=sum_pairs("boundary_admitted_veh"),
            sink_outflow_veh=sum_pairs("sink_outflow_veh"),
            sink_outflow_by_class_veh=tuple(
                sorted((key, tuple(sorted(counts.items()))) for key, counts in sink_classes.items())
            ),
            movement_flow_veh=sum_pairs("movement_flow_veh"),
            interface_flow_veh=sum_pairs("interface_flow_veh"),
            cell_sending_vehps=() if last is None else last.cell_sending_vehps,
            cell_receiving_vehps=() if last is None else last.cell_receiving_vehps,
            spillback_cell_ids=tuple(sorted({cell_id for item in items for cell_id in item.spillback_cell_ids})),
            no_clamp_delete=all(item.no_clamp_delete for item in items),
            interface_transfer_by_class_veh=tuple(
                sorted((key, tuple(sorted(counts.items()))) for key, counts in interface_classes.items())
            ),
        )

    def advance_interval(
        self,
        state: PlantState,
        committed_action: ActionSchedule | ControlAction | StepAction | None,
        demand_schedule: DemandSchedule,
        end_time_sec: float,
        subgraph_view: Any = None,
    ) -> StepResult:
        """Purely advance a committed candidate to an exact CTM grid time."""

        end = float(end_time_sec)
        duration = end - state.sim_time_sec
        step_count = round(duration / self.parameters.urban_dt_sec) if duration >= 0.0 else -1
        if step_count < 0 or abs(duration - step_count * self.parameters.urban_dt_sec) > _EPS:
            invalid = self._invalid(
                state,
                None,
                demand_schedule,
                "end_time_off_ctm_grid",
                "end_time_sec must be on the urban CTM grid",
            )
            return replace(invalid, action_hash=self._committed_hash(committed_action))
        basis_error = self._validate_committed_basis(committed_action, state)
        if basis_error:
            invalid = self._invalid(state, None, demand_schedule, basis_error, basis_error.replace("_", " "))
            return replace(invalid, action_hash=self._committed_hash(committed_action))

        current = state
        diagnostics: list[StepDiagnostics] = []
        for index in range(step_count):
            try:
                public_action = self._action_at(committed_action, current.sim_time_sec)
                step_action = self._rebase_action(public_action, current)
            except SchemaError as exc:
                invalid = self._invalid(current, None, demand_schedule, "action_schedule_gap", str(exc))
                return replace(
                    invalid,
                    action_hash=self._committed_hash(committed_action),
                    completed_horizon_sec=index * self.parameters.urban_dt_sec,
                )
            result = self.step(
                current,
                step_action,
                demand_schedule,
                self.parameters.urban_dt_sec,
                subgraph_view=subgraph_view,
            )
            if result.status != StepStatus.OK or result.next_state is None or result.diagnostics is None:
                return replace(
                    result,
                    action_hash=self._committed_hash(committed_action),
                    completed_horizon_sec=index * self.parameters.urban_dt_sec,
                )
            diagnostics.append(result.diagnostics)
            current = result.next_state
        if abs(current.sim_time_sec - end) > _EPS:
            raise AssertionError("strict kernel lost exact time ownership")
        return StepResult(
            status=StepStatus.OK,
            next_state=current,
            diagnostics=self._aggregate_diagnostics(diagnostics),
            reason_code=None,
            message=None,
            topology_hash=self.topology_hash,
            state_hash=state.state_hash,
            action_hash=self._committed_hash(committed_action),
            parameter_hash=self.parameters.parameter_hash,
            demand_hash=demand_schedule.demand_hash,
            is_feasible=True,
            is_complete=True,
            completed_horizon_sec=duration,
        )

    def rollout_batch(
        self,
        initial_state: PlantState,
        action_schedules: Iterable[ActionSchedule | ControlAction | StepAction | None],
        demand_schedule: DemandSchedule,
        start_time_sec: float,
        horizon_sec: float,
        abort_above: float | None = None,
        subgraph_view: Any = None,
    ) -> BatchRolloutResult:
        """Evaluate candidates in input order and select complete minimum-cost output."""

        candidates = tuple(action_schedules)
        dt = self.parameters.urban_dt_sec
        horizon = float(horizon_sec)
        global_error = None
        if abs(initial_state.sim_time_sec - float(start_time_sec)) > _EPS:
            global_error = "start_time_state_mismatch"
        elif horizon < 0.0 or abs(horizon - round(horizon / dt) * dt) > _EPS:
            global_error = "horizon_off_ctm_grid"
        elif abort_above is not None and (not math.isfinite(float(abort_above)) or float(abort_above) < 0.0):
            global_error = "invalid_abort_threshold"
        elif subgraph_view is not None:
            global_error = "subgraph_not_implemented"

        results: list[CandidateRolloutResult] = []
        for index, committed in enumerate(candidates):
            action_hash = self._committed_hash(committed)
            basis_error = global_error or self._validate_committed_basis(committed, initial_state)
            if basis_error:
                results.append(
                    CandidateRolloutResult(
                        index,
                        action_hash,
                        StepStatus.INVALID_INPUT,
                        False,
                        None,
                        None,
                        (("completed_horizon_sec", 0.0),),
                        (("message", basis_error.replace("_", " ")), ("reason_code", basis_error)),
                    )
                )
                continue

            current = initial_state
            elapsed = 0.0
            total_cost = 0.0
            diagnostics: list[StepDiagnostics] = []
            status = StepStatus.OK
            error: tuple[tuple[str, str], ...] | None = None
            for _ in range(round(horizon / dt)):
                total_cost += current.total_vehicle_inventory() * dt
                try:
                    public_action = self._action_at(committed, current.sim_time_sec)
                    step_action = self._rebase_action(public_action, current)
                except SchemaError as exc:
                    status = StepStatus.INVALID_INPUT
                    error = (("message", str(exc)), ("reason_code", "action_schedule_gap"))
                    break
                result = self.step(current, step_action, demand_schedule, dt)
                if result.status != StepStatus.OK or result.next_state is None or result.diagnostics is None:
                    status = result.status
                    error = (
                        ("message", result.message or result.status.value),
                        ("reason_code", result.reason_code or result.status.value.lower()),
                    )
                    break
                diagnostics.append(result.diagnostics)
                current = result.next_state
                elapsed += dt
                if abort_above is not None and total_cost > float(abort_above):
                    status = StepStatus.EARLY_ABORTED
                    error = (("message", "candidate cost exceeded abort_above"), ("reason_code", "abort_above"))
                    break
            complete = status == StepStatus.OK and abs(elapsed - horizon) <= _EPS
            aggregate = self._aggregate_diagnostics(diagnostics)
            results.append(
                CandidateRolloutResult(
                    candidate_index=index,
                    action_hash=action_hash,
                    status=status,
                    is_feasible=complete,
                    total_cost=total_cost if status not in {StepStatus.INVALID_INPUT, StepStatus.NUMERICAL_ERROR} else None,
                    terminal_state_hash=current.state_hash if complete else None,
                    diagnostics=(
                        ("completed_horizon_sec", elapsed),
                        ("mass_residual_veh", aggregate.mass_residual_veh),
                        ("total_vehicle_time_veh_sec", total_cost),
                    ),
                    error=error,
                )
            )

        selectable = [item for item in results if item.is_feasible and item.total_cost is not None]
        selected = min(selectable, key=lambda item: (item.total_cost, item.candidate_index)) if selectable else None
        if results and all(item.status == StepStatus.OK for item in results):
            batch_status = StepStatus.OK
        elif results and all(item.status == StepStatus.INVALID_INPUT for item in results):
            batch_status = StepStatus.INVALID_INPUT
        else:
            batch_status = StepStatus.PARTIAL
        return BatchRolloutResult(
            schema_version="vissim-strict-batch-rollout/v1",
            batch_status=batch_status,
            selected_candidate_index=None if selected is None else selected.candidate_index,
            fallback_required=selected is None,
            candidate_results=tuple(results),
        )

    def project_observation(
        self,
        observation: Mapping[str, Any],
        previous_state: Mapping[str, Any] | None = None,
        mode: str = "vissim_oracle",
        config: Mapping[str, Any] | None = None,
    ) -> PlantState:
        """Pure wrapper around Phase 2 projectors, normalized to the Phase 1 schema."""

        from .observation import ObservationProjectionError, project_observation

        manifest = self._topology
        if self.uses_hydraulic_view:
            manifest = dict(self._topology)
            manifest["cells"] = list(self._hydraulic_view.get("hydraulic_cells", []))
        try:
            projected = project_observation(
                manifest,
                observation,
                previous_state=previous_state,
                mode=mode,
                config=config,
            )
            raw_stocks = projected.get("stocks", {})
            stocks: list[VehicleStock] = []
            for stock_id, raw in sorted(raw_stocks.items()):
                count = float(raw["vehicle_count_veh"])
                stocks.append(
                    VehicleStock(
                        str(stock_id),
                        str(raw["owner_kind"]),
                        str(raw["owner_id"]),
                        count,
                        {"default": count},
                    )
                )
            urban_refs = {
                str(key): str(value) for key, value in projected.get("urban", {}).get("cell_stock_id", {}).items()
            }
            source_refs = {
                str(key): str(value)
                for key, value in projected.get("boundaries", {}).get("source_queue_stock_id", {}).items()
            }
            for boundary_id in sorted(set(self._source_boundaries) - set(source_refs)):
                stock_id = f"stock:boundary-source-queue:{boundary_id}"
                stocks.append(VehicleStock(stock_id, "boundary_source_queue", boundary_id, 0.0, {"default": 0.0}))
                source_refs[boundary_id] = stock_id
            buffer_refs: dict[str, str] = {}
            for buffer_id in self.required_travel_time_buffer_ids:
                stock_id = f"stock:travel-time-buffer:{buffer_id}"
                stocks.append(VehicleStock(stock_id, "travel_time_buffer", buffer_id, 0.0, {"default": 0.0}))
                buffer_refs[buffer_id] = stock_id
            if set(urban_refs) != set(self._cells):
                raise ObservationProjectionError(
                    "projected cell ownership does not match the selected hydraulic/raw plant view"
                )
            return PlantState(
                topology_hash=self.topology_hash,
                sim_time_sec=float(projected["sim_time_sec"]),
                stocks=tuple(stocks),
                urban_cell_stock_id=urban_refs,
                source_queue_stock_id=source_refs,
                travel_time_buffer_stock_id=buffer_refs,
                cumulative_movement_flow_veh=projected.get("connectors", {}).get("cumulative_flow_veh", {}),
                cumulative_admitted_veh=projected.get("boundaries", {}).get("cumulative_admitted_veh", {}),
            )
        except (ObservationProjectionError, SchemaError, KeyError, TypeError, ValueError) as exc:
            raise SchemaError(f"INVALID_INPUT observation projection: {exc}") from exc
