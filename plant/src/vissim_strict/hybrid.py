"""Strict SI freeway kernel and conservative urban/freeway wrapper.

The wrapper owns every interface transaction.  Interface vehicles are removed
from one physical stock and added to exactly one other physical stock in the
same immutable state transition.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping

from .plant import StrictPlant
from .schema import (
    ControlAction,
    DemandSchedule,
    MASS_TOLERANCE_VEH,
    PlantState,
    SchemaError,
    StepAction,
    StepDiagnostics,
    StepResult,
    StepStatus,
    VehicleStock,
)
from .topology import canonical_json_sha256


_EPS = 1.0e-12


def kph_to_mps(value: float) -> float:
    return float(value) / 3.6


def mps_to_kph(value: float) -> float:
    return float(value) * 3.6


def veh_per_hour_to_vehps(value: float) -> float:
    return float(value) / 3600.0


def vehps_to_veh_per_hour(value: float) -> float:
    return float(value) * 3600.0


def veh_per_km_lane_to_veh_per_m_lane(value: float) -> float:
    return float(value) / 1000.0


def veh_per_m_lane_to_veh_per_km_lane(value: float) -> float:
    return float(value) * 1000.0


def _finite(name: str, value: float, *, positive: bool = False, nonnegative: bool = False) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise SchemaError(f"{name} must be finite")
    if positive and result <= 0.0:
        raise SchemaError(f"{name} must be positive")
    if nonnegative and result < 0.0:
        raise SchemaError(f"{name} must be non-negative")
    return result


def _sorted_pairs(value: Mapping[str, Any] | Iterable[tuple[str, Any]]) -> tuple[tuple[str, Any], ...]:
    items = value.items() if isinstance(value, Mapping) else value
    result = tuple(sorted(((str(key), item) for key, item in items), key=lambda item: item[0]))
    if len({key for key, _ in result}) != len(result):
        raise SchemaError("duplicate freeway parameter key")
    return result


def _sum_maps(left: Mapping[str, float], right: Mapping[str, float]) -> dict[str, float]:
    result = dict(left)
    for key, value in right.items():
        result[key] = result.get(key, 0.0) + value
    return result


def _scale_classes(counts: Mapping[str, float], amount: float) -> dict[str, float]:
    total = sum(counts.values())
    if amount <= _EPS or total <= _EPS:
        return {key: 0.0 for key in counts}
    if amount > total + MASS_TOLERANCE_VEH:
        raise SchemaError(f"requested {amount} veh from stock containing {total} veh")
    return {key: amount * value / total for key, value in counts.items()}


def _priority_allocate(
    demands: Mapping[str, float], priorities: Mapping[str, float], supply: float
) -> dict[str, float]:
    result = {key: 0.0 for key in demands}
    active = {key for key, value in demands.items() if value > _EPS}
    remaining = max(0.0, supply)
    while active and remaining > _EPS:
        total_priority = sum(priorities[key] for key in active)
        shares = {key: remaining * priorities[key] / total_priority for key in active}
        satisfied = {key for key in active if demands[key] - result[key] <= shares[key] + _EPS}
        if not satisfied:
            for key in active:
                result[key] += shares[key]
            break
        for key in sorted(satisfied):
            amount = demands[key] - result[key]
            result[key] += amount
            remaining -= amount
            active.remove(key)
    return result


@dataclass(frozen=True)
class FreewaySegmentParameters:
    length_m: float
    lane_count: float
    v_free_mps: float
    w_mps: float
    rho_critical_veh_per_m_lane: float
    rho_jam_veh_per_m_lane: float
    q_max_vehps_per_lane: float
    tau_sec: float
    anticipation_m2ps: float = 0.0
    kappa_veh_per_m_lane: float = 0.001
    desired_speed_shape: float = 1.867

    def __post_init__(self) -> None:
        for name in (
            "length_m",
            "lane_count",
            "v_free_mps",
            "w_mps",
            "rho_critical_veh_per_m_lane",
            "rho_jam_veh_per_m_lane",
            "q_max_vehps_per_lane",
            "tau_sec",
            "kappa_veh_per_m_lane",
            "desired_speed_shape",
        ):
            object.__setattr__(self, name, _finite(name, getattr(self, name), positive=True))
        object.__setattr__(
            self, "anticipation_m2ps", _finite("anticipation_m2ps", self.anticipation_m2ps, nonnegative=True)
        )
        if self.rho_critical_veh_per_m_lane >= self.rho_jam_veh_per_m_lane:
            raise SchemaError("freeway critical density must be below jam density")

    def payload(self) -> dict[str, float]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True)
class MainlineConnection:
    connection_id: str
    source_segment_id: str
    target_segment_id: str
    split_fraction: float = 1.0
    priority: float = 1.0

    def __post_init__(self) -> None:
        if not self.connection_id or not self.source_segment_id or not self.target_segment_id:
            raise SchemaError("mainline connection identity is required")
        split = _finite("mainline split_fraction", self.split_fraction, nonnegative=True)
        if split > 1.0:
            raise SchemaError("mainline split_fraction must be in [0, 1]")
        object.__setattr__(self, "split_fraction", split)
        object.__setattr__(self, "priority", _finite("mainline priority", self.priority, positive=True))


@dataclass(frozen=True)
class OnRampInterface:
    interface_id: str
    source_stock_id: str
    target_segment_id: str
    max_rate_vehps: float
    priority: float = 1.0

    def __post_init__(self) -> None:
        if not self.interface_id or not self.source_stock_id or not self.target_segment_id:
            raise SchemaError("on-ramp identity is required")
        object.__setattr__(self, "max_rate_vehps", _finite("on-ramp rate", self.max_rate_vehps, nonnegative=True))
        object.__setattr__(self, "priority", _finite("on-ramp priority", self.priority, positive=True))


@dataclass(frozen=True)
class OffRampInterface:
    interface_id: str
    source_segment_id: str
    target_stock_id: str
    split_fraction: float
    max_rate_vehps: float
    target_storage_capacity_veh: float = 1.0e30

    def __post_init__(self) -> None:
        if not self.interface_id or not self.source_segment_id or not self.target_stock_id:
            raise SchemaError("off-ramp identity is required")
        split = _finite("off-ramp split_fraction", self.split_fraction, nonnegative=True)
        if split > 1.0:
            raise SchemaError("off-ramp split_fraction must be in [0, 1]")
        object.__setattr__(self, "split_fraction", split)
        object.__setattr__(self, "max_rate_vehps", _finite("off-ramp rate", self.max_rate_vehps, nonnegative=True))
        capacity = _finite(
            "off-ramp target storage capacity",
            self.target_storage_capacity_veh,
            positive=True,
        )
        if capacity <= 0.0:
            raise SchemaError("off-ramp target storage capacity must be positive")
        object.__setattr__(self, "target_storage_capacity_veh", capacity)


@dataclass(frozen=True)
class FreewayNetworkParameters:
    topology_hash: str
    dt_sec: float
    segments: tuple[tuple[str, FreewaySegmentParameters], ...] | Mapping[str, FreewaySegmentParameters]
    mainline_connections: tuple[MainlineConnection, ...] = ()
    on_ramps: tuple[OnRampInterface, ...] = ()
    off_ramps: tuple[OffRampInterface, ...] = ()
    parameter_hash: str = ""

    def __post_init__(self) -> None:
        if not self.topology_hash:
            raise SchemaError("freeway topology_hash is required")
        dt = _finite("freeway dt_sec", self.dt_sec, positive=True)
        segments = _sorted_pairs(self.segments)
        if not segments or any(not isinstance(value, FreewaySegmentParameters) for _, value in segments):
            raise SchemaError("segments must contain FreewaySegmentParameters")
        ids = {key for key, _ in segments}
        for segment_id, item in segments:
            cfl = min(item.length_m / item.v_free_mps, item.length_m / item.w_mps, item.tau_sec)
            if dt > cfl + _EPS:
                raise SchemaError(f"freeway stability/CFL violation for {segment_id}: {dt} > {cfl}")
        connections = tuple(sorted(self.mainline_connections, key=lambda item: item.connection_id))
        on_ramps = tuple(sorted(self.on_ramps, key=lambda item: item.interface_id))
        off_ramps = tuple(sorted(self.off_ramps, key=lambda item: item.interface_id))
        if any(item.source_segment_id not in ids or item.target_segment_id not in ids for item in connections):
            raise SchemaError("mainline connection references unknown segment")
        if any(item.target_segment_id not in ids for item in on_ramps):
            raise SchemaError("on-ramp references unknown target segment")
        if any(item.source_segment_id not in ids for item in off_ramps):
            raise SchemaError("off-ramp references unknown source segment")
        interface_ids = [item.interface_id for item in on_ramps + off_ramps]
        if len(set(interface_ids)) != len(interface_ids):
            raise SchemaError("interface_id must be globally unique")
        for segment_id in ids:
            split = sum(item.split_fraction for item in connections if item.source_segment_id == segment_id)
            split += sum(item.split_fraction for item in off_ramps if item.source_segment_id == segment_id)
            if split > 1.0 + MASS_TOLERANCE_VEH:
                raise SchemaError(f"outgoing split fractions exceed one for {segment_id}")
        object.__setattr__(self, "dt_sec", dt)
        object.__setattr__(self, "segments", segments)
        object.__setattr__(self, "mainline_connections", connections)
        object.__setattr__(self, "on_ramps", on_ramps)
        object.__setattr__(self, "off_ramps", off_ramps)
        expected = canonical_json_sha256(self.hash_payload())
        if self.parameter_hash and self.parameter_hash != expected:
            raise SchemaError(f"freeway parameter_hash mismatch: expected {expected}")
        object.__setattr__(self, "parameter_hash", expected)

    def hash_payload(self) -> dict[str, Any]:
        return {
            "dt_sec": self.dt_sec,
            "mainline_connections": [item.__dict__ for item in self.mainline_connections],
            "off_ramps": [item.__dict__ for item in self.off_ramps],
            "on_ramps": [item.__dict__ for item in self.on_ramps],
            "segments": {key: value.payload() for key, value in self.segments},
            "topology_hash": self.topology_hash,
        }


class StrictHybridPlant:
    """Pure strict freeway kernel with optional conservative urban coupling."""

    supports_freeway_interfaces = True

    def __init__(self, freeway: FreewayNetworkParameters, urban_plant: StrictPlant | None = None):
        self.freeway = freeway
        self.urban_plant = urban_plant
        self.topology_hash = freeway.topology_hash
        self.parameters = freeway
        if urban_plant is not None and urban_plant.topology_hash != self.topology_hash:
            raise SchemaError("urban and freeway topology hashes differ")
        self._segments = dict(freeway.segments)

    def _invalid(
        self,
        state: PlantState,
        action: ControlAction | StepAction | None,
        demand: DemandSchedule | None,
        reason: str,
        message: str,
        status: StepStatus = StepStatus.INVALID_INPUT,
    ) -> StepResult:
        return StepResult(
            status, None, None, reason, message, self.topology_hash, state.state_hash,
            None if action is None else action.action_hash, self.freeway.parameter_hash,
            None if demand is None else demand.demand_hash, False, False, 0.0,
        )

    def _active_factors(
        self, demand: DemandSchedule, start: float, end: float
    ) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
        duration = end - start
        capacity = {key: demand.global_incident_capacity_factor for key in self._segments}
        speed = {key: 1.0 for key in self._segments}
        lanes = {key: item.lane_count for key, item in self._segments.items()}
        for entry in demand.entries:
            if min(end, entry.end_time_sec) <= max(start, entry.start_time_sec):
                continue
            for loss in entry.freeway_lane_loss:
                if loss.segment_id not in lanes:
                    continue
                overlap = max(0.0, min(end, loss.end_time_sec) - max(start, loss.start_time_sec))
                lanes[loss.segment_id] -= loss.lanes_closed * overlap / duration
            for incident in entry.incidents:
                overlap = max(0.0, min(end, incident.end_time_sec) - max(start, incident.start_time_sec))
                weight = overlap / duration
                for segment_id in set(incident.affected_entity_ids) & set(self._segments):
                    capacity[segment_id] *= 1.0 - weight * (1.0 - incident.capacity_factor)
                    speed[segment_id] *= 1.0 - weight * (1.0 - incident.speed_factor)
        return capacity, speed, {key: max(0.0, value) for key, value in lanes.items()}

    def _urban_substate(self, state: PlantState, counts: Mapping[str, Mapping[str, float]]) -> PlantState:
        selected_ids = {
            stock_id
            for _, stock_id in (
                state.urban_cell_stock_id + state.source_queue_stock_id + state.travel_time_buffer_stock_id
            )
        }
        original = state.stock_by_id()
        stocks = tuple(
            VehicleStock(
                stock_id,
                original[stock_id].owner_kind,
                original[stock_id].owner_id,
                sum(counts[stock_id].values()),
                counts[stock_id],
            )
            for stock_id in sorted(selected_ids)
        )
        return PlantState(
            topology_hash=state.topology_hash,
            sim_time_sec=state.sim_time_sec,
            stocks=stocks,
            urban_cell_stock_id=state.urban_cell_stock_id,
            source_queue_stock_id=state.source_queue_stock_id,
            travel_time_buffer_stock_id=state.travel_time_buffer_stock_id,
            cumulative_movement_flow_veh=state.cumulative_movement_flow_veh,
            cumulative_admitted_veh=state.cumulative_admitted_veh,
            cumulative_sink_outflow_veh=state.cumulative_sink_outflow_veh,
        )

    @staticmethod
    def _urban_action(action: StepAction | None, urban_state: PlantState) -> StepAction | None:
        if action is None:
            return None
        signal_ids = {key for key, _ in action.signal_green_fraction}
        movement_ids = {key for key, _ in action.movement_capacity_vehps}
        return StepAction(
            action_id=action.action_id,
            topology_hash=action.topology_hash,
            based_on_state_hash=urban_state.state_hash,
            decision_time_sec=action.decision_time_sec,
            valid_from_sec=action.valid_from_sec,
            valid_until_sec=action.valid_until_sec,
            signal_green_fraction=action.signal_green_fraction,
            movement_capacity_vehps=action.movement_capacity_vehps,
            authority_ids=tuple(sorted(signal_ids | movement_ids)),
        )

    def step(
        self,
        state: PlantState,
        action: ControlAction | StepAction | None,
        demand: DemandSchedule,
        dt_sec: float,
        subgraph_view: Any = None,
    ) -> StepResult:
        if subgraph_view is not None:
            return self._invalid(state, action, demand, "subgraph_not_implemented", "hybrid subgraphs are not implemented")
        try:
            normalized = action.to_step_action() if isinstance(action, ControlAction) else action
        except SchemaError as exc:
            return self._invalid(state, action, demand, "action_normalization_failed", str(exc))
        dt = float(dt_sec)
        if state.topology_hash != self.topology_hash or demand.topology_hash != self.topology_hash:
            return self._invalid(state, action, demand, "topology_hash_mismatch", "state/demand topology mismatch")
        if abs(dt - self.freeway.dt_sec) > _EPS:
            return self._invalid(state, action, demand, "unsupported_dt_sec", "dt must equal freeway dt_sec")
        if normalized is not None:
            if normalized.topology_hash != self.topology_hash or normalized.based_on_state_hash != state.state_hash:
                return self._invalid(state, action, demand, "stale_action_state_hash", "action is not based on current state")
            if not (normalized.valid_from_sec - _EPS <= state.sim_time_sec < normalized.valid_until_sec - _EPS):
                return self._invalid(state, action, demand, "action_outside_validity", "action validity excludes step")
        segment_refs = dict(state.freeway_segment_stock_id)
        if set(segment_refs) != set(self._segments) or set(dict(state.freeway_speed_mps)) != set(self._segments):
            return self._invalid(state, action, demand, "freeway_state_coverage", "freeway stocks/speeds are incomplete")
        stock_by_id = state.stock_by_id()
        interface_stock_ids = {item.source_stock_id for item in self.freeway.on_ramps}
        interface_stock_ids |= {item.target_stock_id for item in self.freeway.off_ramps}
        if not interface_stock_ids.issubset(stock_by_id):
            return self._invalid(state, action, demand, "interface_stock_missing", "interface references unknown stock")

        t0, t1 = state.sim_time_sec, state.sim_time_sec + dt
        try:
            demand.rates_for_interval(t0, t1)
        except SchemaError as exc:
            return self._invalid(state, action, demand, "demand_interval_uncovered", str(exc))
        counts = {stock_id: dict(stock.class_counts_veh) for stock_id, stock in stock_by_id.items()}
        previous_by_class = state.inventory_by_class()
        speeds = dict(state.freeway_speed_mps)
        capacity_factor, speed_factor, active_lanes = self._active_factors(demand, t0, t1)
        vsl = {} if normalized is None else dict(normalized.vsl_mps)
        meters = {} if normalized is None else dict(normalized.ramp_metering_vehps)
        known_vsl = set(self._segments)
        known_meters = {item.interface_id for item in self.freeway.on_ramps}
        if not set(vsl).issubset(known_vsl) or not set(meters).issubset(known_meters):
            return self._invalid(state, action, demand, "unknown_freeway_command", "unknown VSL or ramp meter command")

        density: dict[str, float] = {}
        sending: dict[str, float] = {}
        receiving: dict[str, float] = {}
        desired_speed: dict[str, float] = {}
        for segment_id, params in self._segments.items():
            count = sum(counts[segment_refs[segment_id]].values())
            lanes = active_lanes[segment_id]
            nominal_density = count / (params.length_m * params.lane_count)
            operational_density = count / (params.length_m * lanes) if lanes > _EPS else params.rho_jam_veh_per_m_lane
            density[segment_id] = operational_density
            limit = min(params.v_free_mps * speed_factor[segment_id], vsl.get(segment_id, math.inf))
            desired = limit * math.exp(
                -(operational_density / params.rho_critical_veh_per_m_lane) ** params.desired_speed_shape
                / params.desired_speed_shape
            )
            desired_speed[segment_id] = desired
            qmax = params.q_max_vehps_per_lane * lanes * capacity_factor[segment_id]
            sending[segment_id] = min(
                count / dt,
                qmax,
                operational_density * min(speeds[segment_id], limit) * lanes,
            )
            free_storage = max(
                0.0,
                params.rho_jam_veh_per_m_lane * params.length_m * params.lane_count - count,
            )
            receiving[segment_id] = min(
                qmax,
                params.w_mps * max(0.0, params.rho_jam_veh_per_m_lane - nominal_density) * params.lane_count,
                free_storage / dt,
            )

        mainline_demands = {
            item.connection_id: sending[item.source_segment_id] * item.split_fraction
            for item in self.freeway.mainline_connections
        }
        onramp_demands = {
            item.interface_id: min(
                sum(counts[item.source_stock_id].values()) / dt,
                item.max_rate_vehps,
                meters.get(item.interface_id, math.inf),
            )
            for item in self.freeway.on_ramps
        }
        incoming_by_target: dict[str, dict[str, float]] = {key: {} for key in self._segments}
        priority_by_target: dict[str, dict[str, float]] = {key: {} for key in self._segments}
        for item in self.freeway.mainline_connections:
            incoming_by_target[item.target_segment_id][item.connection_id] = mainline_demands[item.connection_id]
            priority_by_target[item.target_segment_id][item.connection_id] = item.priority
        for item in self.freeway.on_ramps:
            incoming_by_target[item.target_segment_id][item.interface_id] = onramp_demands[item.interface_id]
            priority_by_target[item.target_segment_id][item.interface_id] = item.priority
        allocated: dict[str, float] = {}
        for target in self._segments:
            allocated.update(
                _priority_allocate(incoming_by_target[target], priority_by_target[target], receiving[target])
            )

        interface_classes: dict[str, dict[str, float]] = {}
        for item in self.freeway.on_ramps:
            amount = allocated.get(item.interface_id, 0.0) * dt
            flow = _scale_classes(counts[item.source_stock_id], amount)
            counts[item.source_stock_id] = {
                key: counts[item.source_stock_id].get(key, 0.0) - value for key, value in flow.items()
            }
            if any(value < 0.0 for value in counts[item.source_stock_id].values()):
                return self._invalid(
                    state,
                    action,
                    demand,
                    "negative_interface_source_stock",
                    item.interface_id,
                    StepStatus.NUMERICAL_ERROR,
                )
            interface_classes[item.interface_id] = flow

        urban_diagnostics: StepDiagnostics | None = None
        cumulative_movement = state.cumulative_movement_flow_veh
        cumulative_admitted = state.cumulative_admitted_veh
        cumulative_sink = state.cumulative_sink_outflow_veh
        if self.urban_plant is not None:
            urban_state = self._urban_substate(state, counts)
            urban_result = self.urban_plant.step(
                urban_state, self._urban_action(normalized, urban_state), demand, dt
            )
            if urban_result.status is not StepStatus.OK or urban_result.next_state is None:
                return self._invalid(
                    state, action, demand, "urban_step_failed", urban_result.message or str(urban_result.reason_code),
                    urban_result.status,
                )
            for stock in urban_result.next_state.stocks:
                counts[stock.stock_id] = dict(stock.class_counts_veh)
            urban_diagnostics = urban_result.diagnostics
            cumulative_movement = urban_result.next_state.cumulative_movement_flow_veh
            cumulative_admitted = urban_result.next_state.cumulative_admitted_veh
            cumulative_sink = urban_result.next_state.cumulative_sink_outflow_veh
        elif state.urban_cell_stock_id or state.source_queue_stock_id or state.travel_time_buffer_stock_id:
            return self._invalid(state, action, demand, "urban_plant_missing", "urban stocks require an urban plant")

        off_demand: dict[str, float] = {}
        off_cap: dict[str, float] = {}
        for item in self.freeway.off_ramps:
            off_demand[item.interface_id] = sending[item.source_segment_id] * item.split_fraction
            target_count = sum(counts[item.target_stock_id].values())
            storage_rate = (item.target_storage_capacity_veh - target_count) / dt
            off_cap[item.interface_id] = min(item.max_rate_vehps, max(0.0, storage_rate))

        source_alpha = {key: 1.0 for key in self._segments}
        for segment_id in self._segments:
            branch_limits: list[float] = []
            for item in self.freeway.mainline_connections:
                if item.source_segment_id == segment_id and mainline_demands[item.connection_id] > _EPS:
                    branch_limits.append(allocated.get(item.connection_id, 0.0) / mainline_demands[item.connection_id])
            for item in self.freeway.off_ramps:
                if item.source_segment_id == segment_id and off_demand[item.interface_id] > _EPS:
                    branch_limits.append(off_cap[item.interface_id] / off_demand[item.interface_id])
            if branch_limits:
                source_alpha[segment_id] = min(1.0, min(branch_limits))

        actual_mainline = {
            item.connection_id: mainline_demands[item.connection_id] * source_alpha[item.source_segment_id] * dt
            for item in self.freeway.mainline_connections
        }
        actual_offramp = {
            item.interface_id: off_demand[item.interface_id] * source_alpha[item.source_segment_id] * dt
            for item in self.freeway.off_ramps
        }
        segment_in: dict[str, dict[str, float]] = {key: {} for key in self._segments}
        segment_out: dict[str, dict[str, float]] = {key: {} for key in self._segments}
        for item in self.freeway.mainline_connections:
            source_counts = counts[segment_refs[item.source_segment_id]]
            flow = _scale_classes(source_counts, actual_mainline[item.connection_id])
            segment_out[item.source_segment_id] = _sum_maps(segment_out[item.source_segment_id], flow)
            segment_in[item.target_segment_id] = _sum_maps(segment_in[item.target_segment_id], flow)
        for item in self.freeway.off_ramps:
            source_counts = counts[segment_refs[item.source_segment_id]]
            flow = _scale_classes(source_counts, actual_offramp[item.interface_id])
            segment_out[item.source_segment_id] = _sum_maps(segment_out[item.source_segment_id], flow)
            counts[item.target_stock_id] = _sum_maps(counts[item.target_stock_id], flow)
            interface_classes[item.interface_id] = flow
        for item in self.freeway.on_ramps:
            segment_in[item.target_segment_id] = _sum_maps(
                segment_in[item.target_segment_id], interface_classes[item.interface_id]
            )

        for segment_id, stock_id in segment_refs.items():
            classes = set(counts[stock_id]) | set(segment_in[segment_id]) | set(segment_out[segment_id])
            updated = {
                key: counts[stock_id].get(key, 0.0)
                + segment_in[segment_id].get(key, 0.0)
                - segment_out[segment_id].get(key, 0.0)
                for key in classes
            }
            if any(value < -MASS_TOLERANCE_VEH for value in updated.values()):
                return self._invalid(
                    state, action, demand, "negative_freeway_stock", str(updated), StepStatus.NUMERICAL_ERROR
                )
            counts[stock_id] = updated

        upstream: dict[str, list[MainlineConnection]] = {key: [] for key in self._segments}
        downstream: dict[str, list[MainlineConnection]] = {key: [] for key in self._segments}
        for connection in self.freeway.mainline_connections:
            upstream[connection.target_segment_id].append(connection)
            downstream[connection.source_segment_id].append(connection)
        next_speeds: dict[str, float] = {}
        for segment_id, params in self._segments.items():
            v = speeds[segment_id]
            incoming_connections = upstream[segment_id]
            incoming_weight = sum(actual_mainline[item.connection_id] for item in incoming_connections)
            up_speed = (
                sum(
                    speeds[item.source_segment_id] * actual_mainline[item.connection_id]
                    for item in incoming_connections
                )
                / incoming_weight
                if incoming_weight > _EPS
                else v
            )
            outgoing_connections = downstream[segment_id]
            outgoing_weight = sum(item.split_fraction for item in outgoing_connections)
            down_density = (
                sum(density[item.target_segment_id] * item.split_fraction for item in outgoing_connections)
                / outgoing_weight
                if outgoing_weight > _EPS
                else density[segment_id]
            )
            relaxation = dt / params.tau_sec * (desired_speed[segment_id] - v)
            convection = dt / params.length_m * v * (up_speed - v)
            anticipation = (
                -dt
                * params.anticipation_m2ps
                / (params.tau_sec * params.length_m)
                * (down_density - density[segment_id])
                / (density[segment_id] + params.kappa_veh_per_m_lane)
            )
            raw_speed = v + relaxation + convection + anticipation
            if not math.isfinite(raw_speed):
                return self._invalid(
                    state, action, demand, "nonfinite_freeway_speed", segment_id, StepStatus.NUMERICAL_ERROR
                )
            speed_ceiling = min(params.v_free_mps * speed_factor[segment_id], vsl.get(segment_id, math.inf))
            next_speeds[segment_id] = min(speed_ceiling, max(0.0, raw_speed))

        original = state.stock_by_id()
        next_stocks = tuple(
            VehicleStock(
                stock_id,
                original[stock_id].owner_kind,
                original[stock_id].owner_id,
                sum(counts[stock_id].values()),
                counts[stock_id],
            )
            for stock_id in sorted(counts)
        )
        next_state = PlantState(
            topology_hash=self.topology_hash,
            sim_time_sec=t1,
            stocks=next_stocks,
            urban_cell_stock_id=state.urban_cell_stock_id,
            source_queue_stock_id=state.source_queue_stock_id,
            travel_time_buffer_stock_id=state.travel_time_buffer_stock_id,
            freeway_segment_stock_id=state.freeway_segment_stock_id,
            ramp_queue_stock_id=state.ramp_queue_stock_id,
            off_ramp_storage_stock_id=state.off_ramp_storage_stock_id,
            freeway_speed_mps=next_speeds,
            cumulative_movement_flow_veh=cumulative_movement,
            cumulative_admitted_veh=cumulative_admitted,
            cumulative_sink_outflow_veh=cumulative_sink,
        )
        urban_arrivals = {} if urban_diagnostics is None else dict(urban_diagnostics.external_demand_arrivals_by_class_veh)
        urban_exits: dict[str, float] = {}
        if urban_diagnostics is not None:
            for _, values in urban_diagnostics.sink_outflow_by_class_veh:
                urban_exits = _sum_maps(urban_exits, dict(values))
        next_by_class = next_state.inventory_by_class()
        classes = set(previous_by_class) | set(next_by_class) | set(urban_arrivals) | set(urban_exits)
        residual_by_class = {
            key: next_by_class.get(key, 0.0)
            - previous_by_class.get(key, 0.0)
            - urban_arrivals.get(key, 0.0)
            + urban_exits.get(key, 0.0)
            for key in sorted(classes)
        }
        residual = sum(residual_by_class.values())
        if abs(residual) > MASS_TOLERANCE_VEH or any(
            abs(value) > MASS_TOLERANCE_VEH for value in residual_by_class.values()
        ):
            return self._invalid(
                state, action, demand, "mass_conservation_violation", str(residual_by_class), StepStatus.NUMERICAL_ERROR
            )
        interface_totals = tuple(
            sorted((key, sum(values.values())) for key, values in interface_classes.items())
        )
        diagnostics = StepDiagnostics(
            mass_residual_veh=residual,
            mass_residual_by_class_veh=tuple(residual_by_class.items()),
            external_admitted_in_veh=0.0 if urban_diagnostics is None else urban_diagnostics.external_admitted_in_veh,
            external_demand_arrivals_veh=0.0 if urban_diagnostics is None else urban_diagnostics.external_demand_arrivals_veh,
            external_demand_arrivals_by_class_veh=tuple(sorted(urban_arrivals.items())),
            boundary_admitted_veh=() if urban_diagnostics is None else urban_diagnostics.boundary_admitted_veh,
            sink_outflow_veh=() if urban_diagnostics is None else urban_diagnostics.sink_outflow_veh,
            sink_outflow_by_class_veh=() if urban_diagnostics is None else urban_diagnostics.sink_outflow_by_class_veh,
            movement_flow_veh=() if urban_diagnostics is None else urban_diagnostics.movement_flow_veh,
            interface_flow_veh=interface_totals,
            cell_sending_vehps=tuple(sorted(sending.items())),
            cell_receiving_vehps=tuple(sorted(receiving.items())),
            spillback_cell_ids=tuple(
                sorted(
                    segment_id
                    for segment_id, params in self._segments.items()
                    if sum(counts[segment_refs[segment_id]].values())
                    >= params.rho_jam_veh_per_m_lane * params.length_m * params.lane_count
                    - MASS_TOLERANCE_VEH
                )
            ),
            no_clamp_delete=True,
            interface_transfer_by_class_veh=tuple(
                sorted((key, tuple(sorted(value.items()))) for key, value in interface_classes.items())
            ),
        )
        return StepResult(
            StepStatus.OK, next_state, diagnostics, None, None, self.topology_hash, state.state_hash,
            None if action is None else action.action_hash, self.freeway.parameter_hash, demand.demand_hash,
            True, True, dt,
        )

    def advance_interval(
        self,
        state: PlantState,
        committed_action: ControlAction | StepAction | None,
        demand_schedule: DemandSchedule,
        end_time_sec: float,
        subgraph_view: Any = None,
    ) -> StepResult:
        duration = float(end_time_sec) - state.sim_time_sec
        steps = round(duration / self.freeway.dt_sec) if duration >= 0.0 else -1
        if steps < 0 or abs(duration - steps * self.freeway.dt_sec) > _EPS:
            return self._invalid(state, committed_action, demand_schedule, "end_time_off_grid", "end time is off-grid")
        current = state
        diagnostics: list[StepDiagnostics] = []
        for _ in range(steps):
            action = committed_action
            if action is not None:
                normalized = action.to_step_action() if isinstance(action, ControlAction) else action
                action = StepAction(
                    action_id=normalized.action_id,
                    topology_hash=normalized.topology_hash,
                    based_on_state_hash=current.state_hash,
                    decision_time_sec=normalized.decision_time_sec,
                    valid_from_sec=normalized.valid_from_sec,
                    valid_until_sec=normalized.valid_until_sec,
                    signal_green_fraction=normalized.signal_green_fraction,
                    movement_capacity_vehps=normalized.movement_capacity_vehps,
                    ramp_metering_vehps=normalized.ramp_metering_vehps,
                    vsl_mps=normalized.vsl_mps,
                    authority_ids=normalized.authority_ids,
                )
            result = self.step(current, action, demand_schedule, self.freeway.dt_sec, subgraph_view)
            if result.status is not StepStatus.OK or result.next_state is None:
                return result
            current = result.next_state
            if result.diagnostics is not None:
                diagnostics.append(result.diagnostics)
        if not diagnostics:
            return self._invalid(state, committed_action, demand_schedule, "empty_interval", "no step requested")
        final = diagnostics[-1]
        return StepResult(
            StepStatus.OK, current, final, None, None, self.topology_hash, state.state_hash,
            None if committed_action is None else committed_action.action_hash, self.freeway.parameter_hash,
            demand_schedule.demand_hash, True, True, duration,
        )

    def rollout(
        self,
        state: PlantState,
        actions: Iterable[ControlAction | StepAction | None],
        demand_schedule: DemandSchedule,
    ) -> tuple[StepResult, ...]:
        results: list[StepResult] = []
        current = state
        for action in actions:
            normalized = action
            if action is not None:
                raw = action.to_step_action() if isinstance(action, ControlAction) else action
                normalized = StepAction(
                    action_id=raw.action_id,
                    topology_hash=raw.topology_hash,
                    based_on_state_hash=current.state_hash,
                    decision_time_sec=raw.decision_time_sec,
                    valid_from_sec=raw.valid_from_sec,
                    valid_until_sec=raw.valid_until_sec,
                    signal_green_fraction=raw.signal_green_fraction,
                    movement_capacity_vehps=raw.movement_capacity_vehps,
                    ramp_metering_vehps=raw.ramp_metering_vehps,
                    vsl_mps=raw.vsl_mps,
                    authority_ids=raw.authority_ids,
                )
            result = self.step(current, normalized, demand_schedule, self.freeway.dt_sec)
            results.append(result)
            if result.status is not StepStatus.OK or result.next_state is None:
                break
            current = result.next_state
        return tuple(results)


__all__ = [
    "FreewayNetworkParameters",
    "FreewaySegmentParameters",
    "MainlineConnection",
    "OffRampInterface",
    "OnRampInterface",
    "StrictHybridPlant",
    "kph_to_mps",
    "mps_to_kph",
    "veh_per_hour_to_vehps",
    "veh_per_km_lane_to_veh_per_m_lane",
    "veh_per_m_lane_to_veh_per_km_lane",
    "vehps_to_veh_per_hour",
]
