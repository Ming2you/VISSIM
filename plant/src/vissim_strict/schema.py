"""Immutable schemas for the deterministic VISSIM strict plant.

The schemas deliberately keep physical vehicle counts in one stock registry.
All other maps are references or cumulative accounting views.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Iterable, Mapping

from .topology import canonical_json_sha256


SCHEMA_VERSION = "vissim-strict-plant/v1"
MASS_TOLERANCE_VEH = 1.0e-6


class SchemaError(ValueError):
    """Raised when a strict-plant schema violates its contract."""


class StepStatus(str, Enum):
    OK = "OK"
    INFEASIBLE = "INFEASIBLE"
    INVALID_INPUT = "INVALID_INPUT"
    EARLY_ABORTED = "EARLY_ABORTED"
    TIMEOUT = "TIMEOUT"
    PARTIAL = "PARTIAL"
    NUMERICAL_ERROR = "NUMERICAL_ERROR"


def _finite(name: str, value: float, *, nonnegative: bool = False, positive: bool = False) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise SchemaError(f"{name} must be finite")
    if positive and result <= 0.0:
        raise SchemaError(f"{name} must be positive")
    if nonnegative and result < 0.0:
        raise SchemaError(f"{name} must be non-negative")
    return result


def _pairs(value: Mapping[str, Any] | Iterable[tuple[str, Any]]) -> tuple[tuple[str, Any], ...]:
    items = value.items() if isinstance(value, Mapping) else value
    result = tuple(sorted(((str(key), item) for key, item in items), key=lambda pair: pair[0]))
    if len({key for key, _ in result}) != len(result):
        raise SchemaError("mapping contains duplicate keys")
    return result


def _float_pairs(
    value: Mapping[str, float] | Iterable[tuple[str, float]],
    *,
    name: str,
    nonnegative: bool = True,
) -> tuple[tuple[str, float], ...]:
    return tuple((key, _finite(f"{name}[{key}]", item, nonnegative=nonnegative)) for key, item in _pairs(value))


def as_dict(items: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    return dict(items)


def class_counts(
    value: Mapping[str, float] | Iterable[tuple[str, float]], *, name: str = "class_counts"
) -> tuple[tuple[str, float], ...]:
    result = _float_pairs(value, name=name)
    if not result:
        return (("default", 0.0),)
    return result


@dataclass(frozen=True)
class CellParameters:
    v_free_mps: float
    w_mps: float
    rho_jam_veh_per_m_lane: float
    q_max_vehps: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "v_free_mps", _finite("v_free_mps", self.v_free_mps, positive=True))
        object.__setattr__(self, "w_mps", _finite("w_mps", self.w_mps, positive=True))
        object.__setattr__(
            self,
            "rho_jam_veh_per_m_lane",
            _finite("rho_jam_veh_per_m_lane", self.rho_jam_veh_per_m_lane, positive=True),
        )
        object.__setattr__(self, "q_max_vehps", _finite("q_max_vehps", self.q_max_vehps, nonnegative=True))

    def payload(self) -> dict[str, float]:
        return {
            "q_max_vehps": self.q_max_vehps,
            "rho_jam_veh_per_m_lane": self.rho_jam_veh_per_m_lane,
            "v_free_mps": self.v_free_mps,
            "w_mps": self.w_mps,
        }


@dataclass(frozen=True)
class HydraulicCellSpec:
    """Compiler-provided macro cell; raw member cells remain provenance only."""

    cell_id: str
    lane_group_id: str
    length_m: float
    lane_count: int
    storage_veh: float
    delay_buffer_steps: int = 1
    flow_length_m: float | None = None
    member_cell_ids: tuple[str, ...] = ()
    preserved_anchor_ids: tuple[str, ...] = ()
    model_type: str = "hydraulic_ctm"

    def __post_init__(self) -> None:
        if not self.cell_id or not self.lane_group_id:
            raise SchemaError("hydraulic cell identity is required")
        object.__setattr__(self, "length_m", _finite("hydraulic length_m", self.length_m, positive=True))
        object.__setattr__(self, "storage_veh", _finite("hydraulic storage_veh", self.storage_veh, positive=True))
        if self.lane_count <= 0 or self.delay_buffer_steps <= 0:
            raise SchemaError("hydraulic lane_count and delay_buffer_steps must be positive")
        flow_length = self.length_m / self.delay_buffer_steps if self.flow_length_m is None else self.flow_length_m
        object.__setattr__(self, "flow_length_m", _finite("hydraulic flow_length_m", flow_length, positive=True))
        object.__setattr__(self, "member_cell_ids", tuple(sorted(set(map(str, self.member_cell_ids)))))
        object.__setattr__(self, "preserved_anchor_ids", tuple(sorted(set(map(str, self.preserved_anchor_ids)))))


@dataclass(frozen=True)
class TransferEdgeSpec:
    """A zero-storage conservative transfer between hydraulic cells."""

    edge_id: str
    source_cell_id: str
    target_cell_id: str
    kind: str = "zero_storage_transfer"
    movement_id: str | None = None
    turn_ratios: tuple[tuple[str, float], ...] | Mapping[str, float] = (("*", 1.0),)
    minimum_travel_time_sec: float = 0.0
    delay_steps: int = 1
    preserved_anchor_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.edge_id or not self.source_cell_id or not self.target_cell_id:
            raise SchemaError("transfer edge identity and endpoints are required")
        ratios = _float_pairs(self.turn_ratios, name=f"transfer[{self.edge_id}].turn_ratios")
        if any(value > 1.0 for _, value in ratios):
            raise SchemaError("transfer-edge turn ratios must be in [0, 1]")
        object.__setattr__(self, "turn_ratios", ratios)
        travel_time = _finite("minimum_travel_time_sec", self.minimum_travel_time_sec, nonnegative=True)
        if self.delay_steps <= 0:
            raise SchemaError("transfer-edge delay_steps must be positive")
        if self.delay_steps > 1:
            raise SchemaError(
                "multi-step transfer edges must be compiled as an explicit hydraulic travel-time-buffer cell"
            )
        object.__setattr__(self, "minimum_travel_time_sec", travel_time)
        object.__setattr__(self, "preserved_anchor_ids", tuple(sorted(set(map(str, self.preserved_anchor_ids)))))


@dataclass(frozen=True)
class PlantParameters:
    topology_hash: str
    cells: tuple[tuple[str, CellParameters], ...] | Mapping[str, CellParameters]
    urban_dt_sec: float = 1.0
    movement_turn_ratios: tuple[tuple[str, tuple[tuple[str, float], ...]], ...] | Mapping[str, Any] = ()
    node_priorities: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    saturation_flow_vehps: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    startup_loss_sec: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    provenance: tuple[tuple[str, str], ...] | Mapping[str, str] = ()
    uncertainty: tuple[tuple[str, Any], ...] | Mapping[str, Any] = ()
    calibration_version: str = "unversioned"
    schema_version: str = SCHEMA_VERSION
    parameter_hash: str = ""

    def __post_init__(self) -> None:
        if not self.topology_hash:
            raise SchemaError("PlantParameters.topology_hash is required")
        cells = _pairs(self.cells)
        if not cells or any(not isinstance(value, CellParameters) for _, value in cells):
            raise SchemaError("PlantParameters.cells must contain CellParameters")
        object.__setattr__(self, "cells", cells)
        object.__setattr__(self, "urban_dt_sec", _finite("urban_dt_sec", self.urban_dt_sec, positive=True))
        ratios = []
        for movement_id, values in _pairs(self.movement_turn_ratios):
            parsed = _float_pairs(values, name=f"movement_turn_ratios[{movement_id}]")
            if any(value > 1.0 for _, value in parsed):
                raise SchemaError("movement turn ratios must be in [0, 1]")
            ratios.append((movement_id, parsed))
        object.__setattr__(self, "movement_turn_ratios", tuple(ratios))
        object.__setattr__(self, "node_priorities", _float_pairs(self.node_priorities, name="node_priorities"))
        if any(value <= 0.0 for _, value in self.node_priorities):
            raise SchemaError("node priorities must be positive")
        object.__setattr__(
            self,
            "saturation_flow_vehps",
            _float_pairs(self.saturation_flow_vehps, name="saturation_flow_vehps"),
        )
        object.__setattr__(self, "startup_loss_sec", _float_pairs(self.startup_loss_sec, name="startup_loss_sec"))
        object.__setattr__(self, "provenance", tuple((key, str(value)) for key, value in _pairs(self.provenance)))
        object.__setattr__(self, "uncertainty", _pairs(self.uncertainty))
        payload = self.hash_payload()
        expected = canonical_json_sha256(payload)
        if self.parameter_hash and self.parameter_hash != expected:
            raise SchemaError(f"parameter_hash mismatch: expected {expected}")
        object.__setattr__(self, "parameter_hash", expected)

    def hash_payload(self) -> dict[str, Any]:
        return {
            "calibration_version": self.calibration_version,
            "cells": {key: value.payload() for key, value in self.cells},
            "movement_turn_ratios": {key: dict(value) for key, value in self.movement_turn_ratios},
            "node_priorities": dict(self.node_priorities),
            "provenance": dict(self.provenance),
            "saturation_flow_vehps": dict(self.saturation_flow_vehps),
            "schema_version": self.schema_version,
            "startup_loss_sec": dict(self.startup_loss_sec),
            "topology_hash": self.topology_hash,
            "uncertainty": dict(self.uncertainty),
            "urban_dt_sec": self.urban_dt_sec,
        }


@dataclass(frozen=True)
class VehicleStock:
    stock_id: str
    owner_kind: str
    owner_id: str
    vehicle_count_veh: float
    class_counts_veh: tuple[tuple[str, float], ...] | Mapping[str, float] = field(
        default_factory=lambda: (("default", 0.0),)
    )

    def __post_init__(self) -> None:
        if not self.stock_id or not self.owner_kind or not self.owner_id:
            raise SchemaError("stock_id, owner_kind, and owner_id are required")
        total = _finite("vehicle_count_veh", self.vehicle_count_veh, nonnegative=True)
        counts = class_counts(self.class_counts_veh, name=f"stock[{self.stock_id}].class_counts_veh")
        if abs(sum(value for _, value in counts) - total) > MASS_TOLERANCE_VEH:
            raise SchemaError(f"stock {self.stock_id} class counts do not sum to vehicle_count_veh")
        object.__setattr__(self, "vehicle_count_veh", total)
        object.__setattr__(self, "class_counts_veh", counts)

    def payload(self) -> dict[str, Any]:
        return {
            "class_counts_veh": dict(self.class_counts_veh),
            "owner_id": self.owner_id,
            "owner_kind": self.owner_kind,
            "stock_id": self.stock_id,
            "vehicle_count_veh": self.vehicle_count_veh,
        }


@dataclass(frozen=True)
class PlantState:
    topology_hash: str
    sim_time_sec: float
    stocks: tuple[VehicleStock, ...]
    urban_cell_stock_id: tuple[tuple[str, str], ...] | Mapping[str, str]
    source_queue_stock_id: tuple[tuple[str, str], ...] | Mapping[str, str] = ()
    travel_time_buffer_stock_id: tuple[tuple[str, str], ...] | Mapping[str, str] = ()
    cumulative_movement_flow_veh: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    cumulative_admitted_veh: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    cumulative_sink_outflow_veh: tuple[tuple[str, tuple[tuple[str, float], ...]], ...] | Mapping[str, Any] = ()
    schema_version: str = SCHEMA_VERSION
    state_hash: str = ""
    freeway_segment_stock_id: tuple[tuple[str, str], ...] | Mapping[str, str] = ()
    ramp_queue_stock_id: tuple[tuple[str, str], ...] | Mapping[str, str] = ()
    off_ramp_storage_stock_id: tuple[tuple[str, str], ...] | Mapping[str, str] = ()
    freeway_speed_mps: tuple[tuple[str, float], ...] | Mapping[str, float] = ()

    def __post_init__(self) -> None:
        if not self.topology_hash:
            raise SchemaError("PlantState.topology_hash is required")
        object.__setattr__(self, "sim_time_sec", _finite("sim_time_sec", self.sim_time_sec, nonnegative=True))
        stocks = tuple(sorted(self.stocks, key=lambda stock: stock.stock_id))
        stock_ids = [stock.stock_id for stock in stocks]
        owners = [(stock.owner_kind, stock.owner_id) for stock in stocks]
        if len(set(stock_ids)) != len(stock_ids):
            raise SchemaError("stock_id must be globally unique")
        if len(set(owners)) != len(owners):
            raise SchemaError("(owner_kind, owner_id) must be globally unique")
        object.__setattr__(self, "stocks", stocks)
        cell_refs = tuple((key, str(value)) for key, value in _pairs(self.urban_cell_stock_id))
        source_refs = tuple((key, str(value)) for key, value in _pairs(self.source_queue_stock_id))
        buffer_refs = tuple((key, str(value)) for key, value in _pairs(self.travel_time_buffer_stock_id))
        freeway_refs = tuple((key, str(value)) for key, value in _pairs(self.freeway_segment_stock_id))
        ramp_refs = tuple((key, str(value)) for key, value in _pairs(self.ramp_queue_stock_id))
        off_ramp_refs = tuple((key, str(value)) for key, value in _pairs(self.off_ramp_storage_stock_id))
        referenced = [
            stock_id
            for _, stock_id in cell_refs + source_refs + buffer_refs + freeway_refs + ramp_refs + off_ramp_refs
        ]
        if len(set(referenced)) != len(referenced):
            raise SchemaError("a physical stock may be referenced by only one owner view")
        stock_by_id = {stock.stock_id: stock for stock in stocks}
        for cell_id, stock_id in cell_refs:
            stock = stock_by_id.get(stock_id)
            if stock is None or stock.owner_kind != "urban_cell" or stock.owner_id != cell_id:
                raise SchemaError(f"invalid urban cell stock reference {cell_id} -> {stock_id}")
        for boundary_id, stock_id in source_refs:
            stock = stock_by_id.get(stock_id)
            if stock is None or stock.owner_kind != "boundary_source_queue" or stock.owner_id != boundary_id:
                raise SchemaError(f"invalid source queue stock reference {boundary_id} -> {stock_id}")
        for buffer_id, stock_id in buffer_refs:
            stock = stock_by_id.get(stock_id)
            if stock is None or stock.owner_kind != "travel_time_buffer" or stock.owner_id != buffer_id:
                raise SchemaError(f"invalid travel-time buffer stock reference {buffer_id} -> {stock_id}")
        for segment_id, stock_id in freeway_refs:
            stock = stock_by_id.get(stock_id)
            if stock is None or stock.owner_kind != "freeway_segment" or stock.owner_id != segment_id:
                raise SchemaError(f"invalid freeway segment stock reference {segment_id} -> {stock_id}")
        for ramp_id, stock_id in ramp_refs:
            stock = stock_by_id.get(stock_id)
            if stock is None or stock.owner_kind != "ramp_queue" or stock.owner_id != ramp_id:
                raise SchemaError(f"invalid ramp queue stock reference {ramp_id} -> {stock_id}")
        for storage_id, stock_id in off_ramp_refs:
            stock = stock_by_id.get(stock_id)
            if stock is None or stock.owner_kind != "off_ramp_storage" or stock.owner_id != storage_id:
                raise SchemaError(f"invalid off-ramp storage stock reference {storage_id} -> {stock_id}")
        if set(referenced) != set(stock_ids):
            raise SchemaError("every physical stock must be referenced exactly once")
        object.__setattr__(self, "urban_cell_stock_id", cell_refs)
        object.__setattr__(self, "source_queue_stock_id", source_refs)
        object.__setattr__(self, "travel_time_buffer_stock_id", buffer_refs)
        object.__setattr__(self, "freeway_segment_stock_id", freeway_refs)
        object.__setattr__(self, "ramp_queue_stock_id", ramp_refs)
        object.__setattr__(self, "off_ramp_storage_stock_id", off_ramp_refs)
        speeds = _float_pairs(self.freeway_speed_mps, name="freeway_speed_mps")
        if set(dict(speeds)) != set(dict(freeway_refs)):
            if speeds or freeway_refs:
                raise SchemaError("freeway_speed_mps must cover every freeway segment exactly once")
        object.__setattr__(self, "freeway_speed_mps", speeds)
        object.__setattr__(
            self,
            "cumulative_movement_flow_veh",
            _float_pairs(self.cumulative_movement_flow_veh, name="cumulative_movement_flow_veh"),
        )
        object.__setattr__(
            self,
            "cumulative_admitted_veh",
            _float_pairs(self.cumulative_admitted_veh, name="cumulative_admitted_veh"),
        )
        sink_items = []
        for boundary_id, counts in _pairs(self.cumulative_sink_outflow_veh):
            sink_items.append((boundary_id, class_counts(counts, name=f"sink[{boundary_id}]")))
        object.__setattr__(self, "cumulative_sink_outflow_veh", tuple(sink_items))
        expected = canonical_json_sha256(self.hash_payload())
        if self.state_hash and self.state_hash != expected:
            raise SchemaError(f"state_hash mismatch: expected {expected}")
        object.__setattr__(self, "state_hash", expected)

    def total_vehicle_inventory(self) -> float:
        return sum(stock.vehicle_count_veh for stock in self.stocks)

    def inventory_by_class(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for stock in self.stocks:
            for class_id, value in stock.class_counts_veh:
                result[class_id] = result.get(class_id, 0.0) + value
        return dict(sorted(result.items()))

    def stock_by_id(self) -> dict[str, VehicleStock]:
        return {stock.stock_id: stock for stock in self.stocks}

    def hash_payload(self) -> dict[str, Any]:
        return {
            "cumulative_admitted_veh": dict(self.cumulative_admitted_veh),
            "cumulative_movement_flow_veh": dict(self.cumulative_movement_flow_veh),
            "cumulative_sink_outflow_veh": {
                key: dict(value) for key, value in self.cumulative_sink_outflow_veh
            },
            "schema_version": self.schema_version,
            "sim_time_sec": self.sim_time_sec,
            "source_queue_stock_id": dict(self.source_queue_stock_id),
            "freeway_segment_stock_id": dict(self.freeway_segment_stock_id),
            "freeway_speed_mps": dict(self.freeway_speed_mps),
            "off_ramp_storage_stock_id": dict(self.off_ramp_storage_stock_id),
            "ramp_queue_stock_id": dict(self.ramp_queue_stock_id),
            "stocks": [stock.payload() for stock in self.stocks],
            "topology_hash": self.topology_hash,
            "travel_time_buffer_stock_id": dict(self.travel_time_buffer_stock_id),
            "urban_cell_stock_id": dict(self.urban_cell_stock_id),
        }


@dataclass(frozen=True)
class StepAction:
    """Normalized one-step kernel command; not the public control envelope."""

    action_id: str
    topology_hash: str
    based_on_state_hash: str
    decision_time_sec: float
    valid_from_sec: float
    valid_until_sec: float
    signal_green_fraction: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    movement_capacity_vehps: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    authority_ids: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION
    action_hash: str = ""
    ramp_metering_vehps: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    vsl_mps: tuple[tuple[str, float], ...] | Mapping[str, float] = ()

    def __post_init__(self) -> None:
        if not self.action_id or not self.topology_hash or not self.based_on_state_hash:
            raise SchemaError("action identity and stale-check hashes are required")
        for field_name in ("decision_time_sec", "valid_from_sec", "valid_until_sec"):
            object.__setattr__(self, field_name, _finite(field_name, getattr(self, field_name), nonnegative=True))
        if self.valid_until_sec <= self.valid_from_sec:
            raise SchemaError("action validity interval must be non-empty")
        if self.decision_time_sec > self.valid_from_sec:
            raise SchemaError("decision_time_sec must not follow valid_from_sec")
        green = _float_pairs(self.signal_green_fraction, name="signal_green_fraction")
        if any(value > 1.0 for _, value in green):
            raise SchemaError("signal green fractions must be in [0, 1]")
        capacity = _float_pairs(self.movement_capacity_vehps, name="movement_capacity_vehps")
        ramp_metering = _float_pairs(self.ramp_metering_vehps, name="ramp_metering_vehps")
        vsl = _float_pairs(self.vsl_mps, name="vsl_mps")
        authority = tuple(sorted(set(str(value) for value in self.authority_ids)))
        command_ids = {key for key, _ in green + capacity + ramp_metering + vsl}
        if not command_ids.issubset(set(authority)):
            raise SchemaError("all action command IDs must be present in authority_ids")
        object.__setattr__(self, "signal_green_fraction", green)
        object.__setattr__(self, "movement_capacity_vehps", capacity)
        object.__setattr__(self, "ramp_metering_vehps", ramp_metering)
        object.__setattr__(self, "vsl_mps", vsl)
        object.__setattr__(self, "authority_ids", authority)
        expected = canonical_json_sha256(self.hash_payload())
        if self.action_hash and self.action_hash != expected:
            raise SchemaError(f"action_hash mismatch: expected {expected}")
        object.__setattr__(self, "action_hash", expected)

    def hash_payload(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "authority_ids": list(self.authority_ids),
            "based_on_state_hash": self.based_on_state_hash,
            "decision_time_sec": self.decision_time_sec,
            "movement_capacity_vehps": dict(self.movement_capacity_vehps),
            "ramp_metering_vehps": dict(self.ramp_metering_vehps),
            "schema_version": self.schema_version,
            "signal_green_fraction": dict(self.signal_green_fraction),
            "topology_hash": self.topology_hash,
            "valid_from_sec": self.valid_from_sec,
            "valid_until_sec": self.valid_until_sec,
            "vsl_mps": dict(self.vsl_mps),
        }


@dataclass(frozen=True)
class LegacyIntent:
    n_p_star_value: float | None = None
    n_p_star_unit: str = "veh"
    n_uf_star_value: float | None = None
    n_uf_star_unit: str = "veh_per_hour"
    extra_fields: tuple[tuple[str, Any], ...] | Mapping[str, Any] = ()

    def __post_init__(self) -> None:
        if self.n_p_star_unit != "veh":
            raise SchemaError("N_P_star unit must be veh")
        if self.n_uf_star_unit not in {"veh_per_hour", "veh_per_control_interval"}:
            raise SchemaError("invalid N_UF_star unit")
        if self.n_p_star_value is not None:
            object.__setattr__(self, "n_p_star_value", _finite("N_P_star", self.n_p_star_value, nonnegative=True))
        if self.n_uf_star_value is not None:
            object.__setattr__(self, "n_uf_star_value", _finite("N_UF_star", self.n_uf_star_value, nonnegative=True))
        object.__setattr__(self, "extra_fields", _pairs(self.extra_fields))

    def payload(self) -> dict[str, Any]:
        return {
            "N_P_star": {"unit": self.n_p_star_unit, "value": self.n_p_star_value},
            "N_UF_star": {"unit": self.n_uf_star_unit, "value": self.n_uf_star_value},
            "extra_fields": dict(self.extra_fields),
        }


@dataclass(frozen=True)
class SignalPlan:
    schedule_id: str
    controller_id: str
    activation_boundary_sec: float
    gate_green_fraction: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    movement_capacity_vehps: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    metadata: tuple[tuple[str, Any], ...] | Mapping[str, Any] = ()

    def __post_init__(self) -> None:
        if not self.schedule_id or not self.controller_id:
            raise SchemaError("signal plan identity is required")
        object.__setattr__(
            self,
            "activation_boundary_sec",
            _finite("signal activation_boundary_sec", self.activation_boundary_sec, nonnegative=True),
        )
        green = _float_pairs(self.gate_green_fraction, name="gate_green_fraction")
        if any(value > 1.0 for _, value in green):
            raise SchemaError("gate green fractions must be in [0, 1]")
        object.__setattr__(self, "gate_green_fraction", green)
        object.__setattr__(
            self,
            "movement_capacity_vehps",
            _float_pairs(self.movement_capacity_vehps, name="movement_capacity_vehps"),
        )
        object.__setattr__(self, "metadata", _pairs(self.metadata))

    def payload(self) -> dict[str, Any]:
        return {
            "activation_boundary_sec": self.activation_boundary_sec,
            "controller_id": self.controller_id,
            "gate_green_fraction": dict(self.gate_green_fraction),
            "metadata": dict(self.metadata),
            "movement_capacity_vehps": dict(self.movement_capacity_vehps),
            "schedule_id": self.schedule_id,
        }


@dataclass(frozen=True)
class ControlAction:
    schema_version: str
    action_id: str
    topology_hash: str
    based_on_state_hash: str
    decision_time_sec: float
    valid_from_sec: float
    activation_boundary_sec: float
    valid_until_sec: float
    signal_plans: tuple[tuple[str, SignalPlan], ...] | Mapping[str, SignalPlan] = ()
    ramp_metering_vehps: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    vsl_mps: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    allocations: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    legacy_intent: LegacyIntent = field(default_factory=LegacyIntent)
    authority_ids: tuple[str, ...] = ()
    action_hash: str = ""

    def __post_init__(self) -> None:
        if not self.action_id or not self.topology_hash or not self.based_on_state_hash:
            raise SchemaError("control action identity and stale-check hashes are required")
        for name in ("decision_time_sec", "valid_from_sec", "activation_boundary_sec", "valid_until_sec"):
            object.__setattr__(self, name, _finite(name, getattr(self, name), nonnegative=True))
        if self.valid_until_sec <= self.valid_from_sec:
            raise SchemaError("control action validity interval must be non-empty")
        if self.decision_time_sec > self.valid_from_sec or self.activation_boundary_sec < self.valid_from_sec:
            raise SchemaError("invalid decision/activation ordering")
        plans = _pairs(self.signal_plans)
        if any(not isinstance(plan, SignalPlan) or key != plan.controller_id for key, plan in plans):
            raise SchemaError("signal_plans must be keyed by controller_id")
        if any(abs(plan.activation_boundary_sec - self.activation_boundary_sec) > MASS_TOLERANCE_VEH for _, plan in plans):
            raise SchemaError("all signal plans must share the action activation boundary")
        object.__setattr__(self, "signal_plans", plans)
        object.__setattr__(self, "ramp_metering_vehps", _float_pairs(self.ramp_metering_vehps, name="ramp_metering_vehps"))
        object.__setattr__(self, "vsl_mps", _float_pairs(self.vsl_mps, name="vsl_mps"))
        object.__setattr__(self, "allocations", _float_pairs(self.allocations, name="allocations"))
        object.__setattr__(self, "authority_ids", tuple(sorted(set(str(value) for value in self.authority_ids))))
        expected = canonical_json_sha256(self.hash_payload())
        if self.action_hash and self.action_hash != expected:
            raise SchemaError(f"action_hash mismatch: expected {expected}")
        object.__setattr__(self, "action_hash", expected)

    def hash_payload(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "activation_boundary_sec": self.activation_boundary_sec,
            "allocations": dict(self.allocations),
            "authority_ids": list(self.authority_ids),
            "based_on_state_hash": self.based_on_state_hash,
            "decision_time_sec": self.decision_time_sec,
            "legacy_intent": self.legacy_intent.payload(),
            "ramp_metering_vehps": dict(self.ramp_metering_vehps),
            "schema_version": self.schema_version,
            "signal_plans": {key: value.payload() for key, value in self.signal_plans},
            "topology_hash": self.topology_hash,
            "valid_from_sec": self.valid_from_sec,
            "valid_until_sec": self.valid_until_sec,
            "vsl_mps": dict(self.vsl_mps),
        }

    def to_step_action(self) -> StepAction:
        green: dict[str, float] = {}
        capacities: dict[str, float] = {}
        for _, plan in self.signal_plans:
            green.update(plan.gate_green_fraction)
            capacities.update(plan.movement_capacity_vehps)
        command_ids = set(green) | set(capacities)
        if not command_ids.issubset(set(self.authority_ids)):
            raise SchemaError("signal plan commands exceed control authority")
        return StepAction(
            action_id=self.action_id,
            topology_hash=self.topology_hash,
            based_on_state_hash=self.based_on_state_hash,
            decision_time_sec=self.decision_time_sec,
            valid_from_sec=self.activation_boundary_sec,
            valid_until_sec=self.valid_until_sec,
            signal_green_fraction=green,
            movement_capacity_vehps=capacities,
            ramp_metering_vehps=self.ramp_metering_vehps,
            vsl_mps=self.vsl_mps,
            authority_ids=self.authority_ids,
        )


# Compatibility name for callers that imported the early Phase 1 schema.
PlantAction = ControlAction


@dataclass(frozen=True)
class ActionScheduleEntry:
    start_time_sec: float
    end_time_sec: float
    action: ControlAction

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_time_sec", _finite("entry start_time_sec", self.start_time_sec, nonnegative=True))
        object.__setattr__(self, "end_time_sec", _finite("entry end_time_sec", self.end_time_sec, nonnegative=True))
        if self.end_time_sec <= self.start_time_sec:
            raise SchemaError("action schedule entry must be non-empty")


@dataclass(frozen=True)
class ActionSchedule:
    schedule_id: str
    control_interval_sec: float
    prediction_horizon_steps: int
    control_horizon_steps: int
    move_blocking: bool
    activation_boundary_sec: float
    entries: tuple[ActionScheduleEntry, ...]
    schema_version: str = SCHEMA_VERSION
    schedule_hash: str = ""

    def __post_init__(self) -> None:
        if not self.schedule_id:
            raise SchemaError("schedule_id is required")
        object.__setattr__(self, "control_interval_sec", _finite("control_interval_sec", self.control_interval_sec, positive=True))
        object.__setattr__(self, "activation_boundary_sec", _finite("activation_boundary_sec", self.activation_boundary_sec, nonnegative=True))
        if self.prediction_horizon_steps <= 0 or self.control_horizon_steps <= 0:
            raise SchemaError("action horizons must be positive")
        if self.control_horizon_steps > self.prediction_horizon_steps:
            raise SchemaError("control horizon cannot exceed prediction horizon")
        entries = tuple(sorted(self.entries, key=lambda entry: entry.start_time_sec))
        if not entries:
            raise SchemaError("action schedule must contain entries")
        if any(right.start_time_sec < left.end_time_sec - MASS_TOLERANCE_VEH for left, right in zip(entries, entries[1:])):
            raise SchemaError("action schedule entries overlap")
        if any(abs(entry.action.activation_boundary_sec - self.activation_boundary_sec) > MASS_TOLERANCE_VEH for entry in entries):
            raise SchemaError("entry action activation boundary mismatch")
        object.__setattr__(self, "entries", entries)
        payload = {
            "activation_boundary_sec": self.activation_boundary_sec,
            "control_horizon_steps": self.control_horizon_steps,
            "control_interval_sec": self.control_interval_sec,
            "entries": [
                {"action_hash": entry.action.action_hash, "end_time_sec": entry.end_time_sec, "start_time_sec": entry.start_time_sec}
                for entry in entries
            ],
            "move_blocking": self.move_blocking,
            "prediction_horizon_steps": self.prediction_horizon_steps,
            "schedule_id": self.schedule_id,
            "schema_version": self.schema_version,
        }
        expected = canonical_json_sha256(payload)
        if self.schedule_hash and self.schedule_hash != expected:
            raise SchemaError(f"schedule_hash mismatch: expected {expected}")
        object.__setattr__(self, "schedule_hash", expected)


@dataclass(frozen=True)
class LaneLoss:
    segment_id: str
    lanes_closed: float
    start_time_sec: float
    end_time_sec: float

    def __post_init__(self) -> None:
        if not self.segment_id:
            raise SchemaError("lane-loss segment_id is required")
        object.__setattr__(self, "lanes_closed", _finite("lanes_closed", self.lanes_closed, nonnegative=True))
        object.__setattr__(self, "start_time_sec", _finite("lane-loss start", self.start_time_sec, nonnegative=True))
        object.__setattr__(self, "end_time_sec", _finite("lane-loss end", self.end_time_sec, nonnegative=True))
        if self.end_time_sec <= self.start_time_sec:
            raise SchemaError("lane-loss interval must be non-empty")


@dataclass(frozen=True)
class Incident:
    incident_id: str
    affected_entity_ids: tuple[str, ...]
    capacity_factor: float
    speed_factor: float
    start_time_sec: float
    end_time_sec: float

    def __post_init__(self) -> None:
        if not self.incident_id or not self.affected_entity_ids:
            raise SchemaError("incident identity and affected entities are required")
        object.__setattr__(self, "affected_entity_ids", tuple(sorted(set(map(str, self.affected_entity_ids)))))
        for name in ("capacity_factor", "speed_factor"):
            value = _finite(name, getattr(self, name), nonnegative=True)
            if value > 1.0:
                raise SchemaError(f"{name} must be in [0, 1]")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "start_time_sec", _finite("incident start", self.start_time_sec, nonnegative=True))
        object.__setattr__(self, "end_time_sec", _finite("incident end", self.end_time_sec, nonnegative=True))
        if self.end_time_sec <= self.start_time_sec:
            raise SchemaError("incident interval must be non-empty")


@dataclass(frozen=True)
class DemandEntry:
    start_time_sec: float
    end_time_sec: float
    boundary_demand_vehps: tuple[tuple[str, tuple[tuple[str, float], ...]], ...] | Mapping[str, Any]
    freeway_lane_loss: tuple[LaneLoss, ...] = ()
    incidents: tuple[Incident, ...] = ()

    def __post_init__(self) -> None:
        start = _finite("start_time_sec", self.start_time_sec, nonnegative=True)
        end = _finite("end_time_sec", self.end_time_sec, nonnegative=True)
        if end <= start:
            raise SchemaError("demand entry interval must be non-empty")
        entries = tuple(
            (boundary_id, class_counts(rates, name=f"demand[{boundary_id}]"))
            for boundary_id, rates in _pairs(self.boundary_demand_vehps)
        )
        object.__setattr__(self, "start_time_sec", start)
        object.__setattr__(self, "end_time_sec", end)
        object.__setattr__(self, "boundary_demand_vehps", entries)
        object.__setattr__(self, "freeway_lane_loss", tuple(sorted(self.freeway_lane_loss, key=lambda item: (item.start_time_sec, item.segment_id))))
        object.__setattr__(self, "incidents", tuple(sorted(self.incidents, key=lambda item: (item.start_time_sec, item.incident_id))))


@dataclass(frozen=True)
class DemandSchedule:
    schedule_id: str
    topology_hash: str
    start_time_sec: float
    end_time_sec: float
    interval_sec: float
    entries: tuple[DemandEntry, ...]
    initial_source_queues_veh: tuple[tuple[str, float], ...] | Mapping[str, float] = ()
    global_incident_capacity_factor: float = 1.0
    schema_version: str = SCHEMA_VERSION
    demand_hash: str = ""

    def __post_init__(self) -> None:
        if not self.schedule_id or not self.topology_hash:
            raise SchemaError("demand schedule identity is required")
        start = _finite("start_time_sec", self.start_time_sec, nonnegative=True)
        end = _finite("end_time_sec", self.end_time_sec, nonnegative=True)
        interval = _finite("interval_sec", self.interval_sec, positive=True)
        factor = _finite("global_incident_capacity_factor", self.global_incident_capacity_factor, nonnegative=True)
        if end <= start or factor > 1.0:
            raise SchemaError("invalid demand schedule range or incident factor")
        entries = tuple(sorted(self.entries, key=lambda item: item.start_time_sec))
        cursor = start
        for entry in entries:
            if abs(entry.start_time_sec - cursor) > MASS_TOLERANCE_VEH:
                raise SchemaError("demand entries must cover the schedule without gaps or overlap")
            cursor = entry.end_time_sec
        if not entries or abs(cursor - end) > MASS_TOLERANCE_VEH:
            raise SchemaError("demand entries must cover the complete schedule")
        object.__setattr__(self, "start_time_sec", start)
        object.__setattr__(self, "end_time_sec", end)
        object.__setattr__(self, "interval_sec", interval)
        object.__setattr__(self, "global_incident_capacity_factor", factor)
        object.__setattr__(self, "entries", entries)
        object.__setattr__(
            self,
            "initial_source_queues_veh",
            _float_pairs(self.initial_source_queues_veh, name="initial_source_queues_veh"),
        )
        expected = canonical_json_sha256(self.hash_payload())
        if self.demand_hash and self.demand_hash != expected:
            raise SchemaError(f"demand_hash mismatch: expected {expected}")
        object.__setattr__(self, "demand_hash", expected)

    def rates_for_interval(self, start_sec: float, end_sec: float) -> dict[str, dict[str, float]]:
        start = _finite("demand interval start", start_sec, nonnegative=True)
        end = _finite("demand interval end", end_sec, nonnegative=True)
        if end <= start or start < self.start_time_sec - MASS_TOLERANCE_VEH or end > self.end_time_sec + MASS_TOLERANCE_VEH:
            raise SchemaError("step interval is outside demand schedule")
        totals: dict[str, dict[str, float]] = {}
        for entry in self.entries:
            overlap = max(0.0, min(end, entry.end_time_sec) - max(start, entry.start_time_sec))
            if overlap <= 0.0:
                continue
            for boundary_id, rates in entry.boundary_demand_vehps:
                destination = totals.setdefault(boundary_id, {})
                for class_id, rate in rates:
                    destination[class_id] = destination.get(class_id, 0.0) + rate * overlap
        duration = end - start
        return {
            boundary_id: {class_id: value / duration for class_id, value in sorted(rates.items())}
            for boundary_id, rates in sorted(totals.items())
        }

    def hash_payload(self) -> dict[str, Any]:
        return {
            "end_time_sec": self.end_time_sec,
            "entries": [
                {
                    "boundary_demand_vehps": {
                        boundary_id: dict(rates) for boundary_id, rates in entry.boundary_demand_vehps
                    },
                    "end_time_sec": entry.end_time_sec,
                    "freeway_lane_loss": [
                        {
                            "end_time_sec": loss.end_time_sec,
                            "lanes_closed": loss.lanes_closed,
                            "segment_id": loss.segment_id,
                            "start_time_sec": loss.start_time_sec,
                        }
                        for loss in entry.freeway_lane_loss
                    ],
                    "incidents": [
                        {
                            "affected_entity_ids": list(incident.affected_entity_ids),
                            "capacity_factor": incident.capacity_factor,
                            "end_time_sec": incident.end_time_sec,
                            "incident_id": incident.incident_id,
                            "speed_factor": incident.speed_factor,
                            "start_time_sec": incident.start_time_sec,
                        }
                        for incident in entry.incidents
                    ],
                    "start_time_sec": entry.start_time_sec,
                }
                for entry in self.entries
            ],
            "global_incident_capacity_factor": self.global_incident_capacity_factor,
            "initial_source_queues_veh": dict(self.initial_source_queues_veh),
            "interval_sec": self.interval_sec,
            "schedule_id": self.schedule_id,
            "schema_version": self.schema_version,
            "start_time_sec": self.start_time_sec,
            "topology_hash": self.topology_hash,
        }


@dataclass(frozen=True)
class StepDiagnostics:
    mass_residual_veh: float
    mass_residual_by_class_veh: tuple[tuple[str, float], ...]
    external_admitted_in_veh: float
    external_demand_arrivals_veh: float
    external_demand_arrivals_by_class_veh: tuple[tuple[str, float], ...]
    boundary_admitted_veh: tuple[tuple[str, float], ...]
    sink_outflow_veh: tuple[tuple[str, float], ...]
    sink_outflow_by_class_veh: tuple[tuple[str, tuple[tuple[str, float], ...]], ...]
    movement_flow_veh: tuple[tuple[str, float], ...]
    interface_flow_veh: tuple[tuple[str, float], ...]
    cell_sending_vehps: tuple[tuple[str, float], ...]
    cell_receiving_vehps: tuple[tuple[str, float], ...]
    spillback_cell_ids: tuple[str, ...]
    no_clamp_delete: bool = True
    interface_transfer_by_class_veh: tuple[
        tuple[str, tuple[tuple[str, float], ...]], ...
    ] = ()


@dataclass(frozen=True)
class StepResult:
    status: StepStatus
    next_state: PlantState | None
    diagnostics: StepDiagnostics | None
    reason_code: str | None
    message: str | None
    topology_hash: str
    state_hash: str
    action_hash: str | None
    parameter_hash: str
    demand_hash: str | None
    is_feasible: bool
    is_complete: bool
    completed_horizon_sec: float
