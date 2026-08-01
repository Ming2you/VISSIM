"""Unit-safe compatibility boundary between the legacy and strict plants.

The strict kernel owns simulation time.  This module is the only migration
boundary allowed to mutate a legacy ``TrafficState``, and it does so once,
after a complete strict interval succeeds.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import math
from typing import Any, Callable, Mapping

from .schema import (
    SCHEMA_VERSION,
    ControlAction,
    DemandEntry,
    DemandSchedule,
    LaneLoss,
    LegacyIntent,
    PlantState,
    SchemaError,
    SignalPlan,
    StepResult,
    StepStatus,
)


VEH_PER_HOUR_TO_VEH_PER_SEC = 1.0 / 3600.0
KM_PER_HOUR_TO_M_PER_SEC = 1.0 / 3.6
_TIME_TOLERANCE_SEC = 1.0e-9
_DEMAND_KINDS = {"freeway_mainline", "urban_boundary", "ramp_arrival"}


class BridgeError(RuntimeError):
    """Raised when compatibility execution would violate the G0 contract."""


def _finite(name: str, value: Any, *, positive: bool = False) -> float:
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        qualifier = "positive and " if positive else ""
        raise SchemaError(f"{name} must be {qualifier}finite")
    return result


def _control_interval_sec(cfg: Any) -> float:
    return _finite("cfg.simulation.control_interval", cfg.simulation.control_interval, positive=True)


def _cycle_length_sec(cfg: Any) -> float:
    return _finite("cfg.network.cycle_length", cfg.network.cycle_length, positive=True)


def _n_uf_unit(cfg: Any) -> str:
    unit = str(cfg.leader.N_UF_star_unit)
    if unit not in {"veh_per_hour", "veh_per_control_interval"}:
        raise SchemaError("cfg.leader.N_UF_star_unit has an unsupported value")
    return unit


def _controller_from_legacy_key(key: str) -> str:
    head, separator, suffix = str(key).rpartition("_")
    if separator and (suffix.lower().startswith("p") or suffix.lower().startswith("phase")):
        return head
    return str(key)


def _signal_targets(
    legacy_key: str,
    signal_mapping: Mapping[str, Any] | None,
) -> tuple[tuple[str, str], ...]:
    target = None if signal_mapping is None else signal_mapping.get(legacy_key)
    if target is None:
        return ((_controller_from_legacy_key(legacy_key), legacy_key),)
    if isinstance(target, str):
        return ((_controller_from_legacy_key(legacy_key), target),)
    if isinstance(target, Mapping):
        controller_id = str(target.get("controller_id", ""))
        command_ids = tuple(str(value) for value in target.get("command_ids", ()))
        if not controller_id or not command_ids or len(set(command_ids)) != len(command_ids):
            raise SchemaError(
                f"signal_mapping[{legacy_key!r}] requires controller_id and unique command_ids"
            )
        return tuple((controller_id, command_id) for command_id in command_ids)
    if len(target) != 2:
        raise SchemaError(f"signal_mapping[{legacy_key!r}] must be command_id or (controller_id, command_id)")
    return ((str(target[0]), str(target[1])),)


def _demand_kind(boundary_id: str, cfg: Any, explicit: Mapping[str, str] | None) -> str:
    if explicit is not None and boundary_id in explicit:
        kind = str(explicit[boundary_id])
        if kind not in _DEMAND_KINDS:
            raise SchemaError(f"invalid demand kind for {boundary_id}: {kind}")
        return kind
    network = cfg.network
    if boundary_id in set(map(str, getattr(network, "freeway_links", ()))):
        return "freeway_mainline"
    if boundary_id in set(map(str, getattr(network, "ramps", ()))):
        return "ramp_arrival"
    return "urban_boundary"


def _legacy_action_to_strict(
    value: Any,
    *,
    cfg: Any,
    topology_hash: str,
    based_on_state_hash: str,
    start_time_sec: float,
    end_time_sec: float,
    action_id: str | None,
    signal_mapping: Mapping[str, Any] | None,
    signal_cycle_sec_by_controller: Mapping[str, float] | None,
    authority_ids: tuple[str, ...] | list[str] | set[str],
) -> ControlAction:
    start = _finite("start_time_sec", start_time_sec)
    end = _finite("end_time_sec", end_time_sec)
    if start < 0.0 or end <= start:
        raise SchemaError("legacy action interval must be non-empty and nonnegative")
    cycle = _cycle_length_sec(cfg)

    plans: dict[str, dict[str, Any]] = {}
    original_green = {str(key): float(amount) for key, amount in value.green_times.items()}
    original_offsets = {str(key): float(amount) for key, amount in value.offsets.items()}
    command_ids: set[str] = set()
    for legacy_key, green_sec in original_green.items():
        if not math.isfinite(green_sec) or green_sec < 0.0:
            raise SchemaError(f"green time for {legacy_key} must be finite and nonnegative")
        for controller_id, command_id in _signal_targets(legacy_key, signal_mapping):
            controller_cycle = _finite(
                f"signal cycle for {controller_id}",
                cycle if signal_cycle_sec_by_controller is None else signal_cycle_sec_by_controller.get(controller_id, cycle),
                positive=True,
            )
            if green_sec > controller_cycle:
                raise SchemaError(f"green time for {legacy_key} exceeds cycle for {controller_id}")
            plan = plans.setdefault(
                controller_id,
                {"green": {}, "legacy_green": {}, "offsets": {}, "cycle": controller_cycle},
            )
            if abs(float(plan["cycle"]) - controller_cycle) > _TIME_TOLERANCE_SEC:
                raise SchemaError(f"conflicting signal cycles for {controller_id}")
            if command_id in command_ids:
                raise SchemaError(f"duplicate strict signal command ID: {command_id}")
            plan["green"][command_id] = green_sec / controller_cycle
            plan["legacy_green"][legacy_key] = green_sec
            command_ids.add(command_id)
    for legacy_key, offset_sec in original_offsets.items():
        if not math.isfinite(offset_sec):
            raise SchemaError(f"offset for {legacy_key} must be finite")
        offset_target = None if signal_mapping is None else signal_mapping.get(legacy_key)
        controller_id = (
            str(offset_target.get("controller_id"))
            if isinstance(offset_target, Mapping) and offset_target.get("controller_id")
            else str(legacy_key)
        )
        controller_cycle = _finite(
            f"signal cycle for {controller_id}",
            cycle if signal_cycle_sec_by_controller is None else signal_cycle_sec_by_controller.get(controller_id, cycle),
            positive=True,
        )
        plan = plans.setdefault(
            controller_id,
            {"green": {}, "legacy_green": {}, "offsets": {}, "cycle": controller_cycle},
        )
        plan["offsets"][legacy_key] = offset_sec

    signal_plans = {
        controller_id: SignalPlan(
            schedule_id=f"legacy-signal:{controller_id}:{start:.9f}",
            controller_id=controller_id,
            activation_boundary_sec=start,
            gate_green_fraction=payload["green"],
            metadata={
                "cycle_length_sec": payload["cycle"],
                "legacy_green_times_sec": payload["legacy_green"],
                "legacy_offsets_sec": payload["offsets"],
                "offset_actuation": "intent_only",
            },
        )
        for controller_id, payload in sorted(plans.items())
    }
    extra_fields = {
        "legacy_diagnostics": deepcopy(value.diagnostics),
        "legacy_infeasibility": deepcopy(value.infeasibility),
        "legacy_green_times_sec": original_green,
        "legacy_offsets_sec": original_offsets,
    }
    authority = set(map(str, authority_ids))
    authority.update(command_ids)
    authority.update(map(str, value.ramp_metering))
    authority.update(map(str, value.vsl))
    authority.update(map(str, value.inflow_outflow_allocation))
    return ControlAction(
        schema_version=SCHEMA_VERSION,
        action_id=action_id or f"legacy-action:{based_on_state_hash[:16]}:{start:.9f}",
        topology_hash=str(topology_hash),
        based_on_state_hash=str(based_on_state_hash),
        decision_time_sec=start,
        valid_from_sec=start,
        activation_boundary_sec=start,
        valid_until_sec=end,
        signal_plans=signal_plans,
        ramp_metering_vehps={key: float(amount) * VEH_PER_HOUR_TO_VEH_PER_SEC for key, amount in value.ramp_metering.items()},
        vsl_mps={key: float(amount) * KM_PER_HOUR_TO_M_PER_SEC for key, amount in value.vsl.items()},
        allocations={
            key: float(amount) * VEH_PER_HOUR_TO_VEH_PER_SEC
            for key, amount in value.inflow_outflow_allocation.items()
        },
        legacy_intent=LegacyIntent(
            n_p_star_value=float(value.N_P_star),
            n_p_star_unit="veh",
            n_uf_star_value=float(value.N_UF_star),
            n_uf_star_unit=_n_uf_unit(cfg),
            extra_fields=extra_fields,
        ),
        authority_ids=tuple(sorted(authority)),
    )


def _legacy_demand_to_strict(
    value: Any,
    *,
    cfg: Any,
    topology_hash: str,
    start_time_sec: float,
    end_time_sec: float,
    schedule_id: str | None,
) -> DemandSchedule:
    start = _finite("start_time_sec", start_time_sec)
    end = _finite("end_time_sec", end_time_sec)
    if start < 0.0 or end <= start:
        raise SchemaError("legacy demand interval must be non-empty and nonnegative")
    categories = {
        "freeway_mainline": value.freeway_mainline,
        "urban_boundary": value.urban_boundary,
        "ramp_arrival": value.ramp_arrival,
    }
    seen: dict[str, str] = {}
    rates: dict[str, dict[str, float]] = {}
    for kind, entries in categories.items():
        for raw_id, amount in entries.items():
            boundary_id = str(raw_id)
            if boundary_id in seen:
                raise SchemaError(f"legacy demand ID {boundary_id!r} appears in both {seen[boundary_id]} and {kind}")
            seen[boundary_id] = kind
            rates[boundary_id] = {"default": float(amount) * VEH_PER_HOUR_TO_VEH_PER_SEC}
    lane_losses = tuple(
        LaneLoss(
            segment_id=f"{link_id}__seg{int(segment_index)}",
            lanes_closed=float(lanes_closed),
            start_time_sec=start,
            end_time_sec=end,
        )
        for link_id, segments in sorted(value.freeway_lane_loss.items())
        for segment_index, lanes_closed in sorted(segments.items())
    )
    return DemandSchedule(
        schedule_id=schedule_id or f"legacy-demand:{start:.9f}:{end:.9f}",
        topology_hash=str(topology_hash),
        start_time_sec=start,
        end_time_sec=end,
        interval_sec=end - start,
        entries=(DemandEntry(start, end, rates, freeway_lane_loss=lane_losses),),
        global_incident_capacity_factor=float(value.incident_capacity_factor),
    )


def legacy_to_strict(
    value: Any,
    *,
    cfg: Any,
    topology_hash: str,
    start_time_sec: float,
    end_time_sec: float,
    based_on_state_hash: str | None = None,
    action_id: str | None = None,
    schedule_id: str | None = None,
    signal_mapping: Mapping[str, Any] | None = None,
    signal_cycle_sec_by_controller: Mapping[str, float] | None = None,
    authority_ids: tuple[str, ...] | list[str] | set[str] = (),
) -> ControlAction | DemandSchedule:
    """Normalize one legacy action or demand step into strict SI schemas."""

    action_fields = (
        "N_P_star", "N_UF_star", "ramp_metering", "vsl", "green_times",
        "offsets", "inflow_outflow_allocation", "infeasibility", "diagnostics",
    )
    demand_fields = (
        "freeway_mainline", "urban_boundary", "ramp_arrival",
        "incident_capacity_factor", "freeway_lane_loss",
    )
    if all(hasattr(value, field) for field in action_fields):
        if not based_on_state_hash:
            raise SchemaError("based_on_state_hash is required for a legacy ControlAction")
        return _legacy_action_to_strict(
            value,
            cfg=cfg,
            topology_hash=topology_hash,
            based_on_state_hash=based_on_state_hash,
            start_time_sec=start_time_sec,
            end_time_sec=end_time_sec,
            action_id=action_id,
            signal_mapping=signal_mapping,
            signal_cycle_sec_by_controller=signal_cycle_sec_by_controller,
            authority_ids=authority_ids,
        )
    if all(hasattr(value, field) for field in demand_fields):
        return _legacy_demand_to_strict(
            value,
            cfg=cfg,
            topology_hash=topology_hash,
            start_time_sec=start_time_sec,
            end_time_sec=end_time_sec,
            schedule_id=schedule_id,
        )
    raise TypeError(f"unsupported legacy type: {type(value).__name__}")


def _strict_action_to_legacy(
    value: ControlAction,
    *,
    cfg: Any,
    factory: Callable[..., Any] | None,
) -> Any:
    intent = value.legacy_intent
    if intent.n_p_star_value is None or intent.n_uf_star_value is None:
        raise SchemaError("strict legacy intent cannot be represented by legacy ControlAction when intent values are None")
    if intent.n_p_star_unit != "veh" or intent.n_uf_star_unit != _n_uf_unit(cfg):
        raise SchemaError("legacy intent unit does not match cfg.leader.N_UF_star_unit")
    extra = dict(intent.extra_fields)
    green = deepcopy(extra.get("legacy_green_times_sec", {}))
    offsets = deepcopy(extra.get("legacy_offsets_sec", {}))
    if not green:
        for _, plan in value.signal_plans:
            metadata = dict(plan.metadata)
            cycle = float(metadata.get("cycle_length_sec", _cycle_length_sec(cfg)))
            legacy_green = metadata.get("legacy_green_times_sec")
            if legacy_green:
                green.update(deepcopy(legacy_green))
            else:
                green.update({key: fraction * cycle for key, fraction in plan.gate_green_fraction})
            offsets.update(deepcopy(metadata.get("legacy_offsets_sec", {})))
    if factory is None:
        raise BridgeError("strict action conversion requires control_action_factory")
    return factory(
        N_P_star=float(intent.n_p_star_value),
        N_UF_star=float(intent.n_uf_star_value),
        ramp_metering={key: value_vehps / VEH_PER_HOUR_TO_VEH_PER_SEC for key, value_vehps in value.ramp_metering_vehps},
        vsl={key: value_mps / KM_PER_HOUR_TO_M_PER_SEC for key, value_mps in value.vsl_mps},
        green_times={str(key): float(amount) for key, amount in green.items()},
        offsets={str(key): float(amount) for key, amount in offsets.items()},
        inflow_outflow_allocation={
            key: value_vehps / VEH_PER_HOUR_TO_VEH_PER_SEC for key, value_vehps in value.allocations
        },
        infeasibility=deepcopy(extra.get("legacy_infeasibility", {})),
        diagnostics=deepcopy(extra.get("legacy_diagnostics", {})),
    )


def _strict_demand_to_legacy(
    value: DemandSchedule,
    *,
    cfg: Any,
    demand_kind_by_id: Mapping[str, str] | None,
    factory: Callable[..., Any] | None,
) -> Any:
    if value.initial_source_queues_veh:
        raise SchemaError("legacy DemandStep cannot represent initial_source_queues_veh")
    if any(entry.incidents for entry in value.entries):
        raise SchemaError("legacy DemandStep cannot represent local strict incidents")
    duration = value.end_time_sec - value.start_time_sec
    totals: dict[str, float] = {}
    for entry in value.entries:
        overlap = entry.end_time_sec - entry.start_time_sec
        for boundary_id, class_rates in entry.boundary_demand_vehps:
            totals[boundary_id] = totals.get(boundary_id, 0.0) + sum(rate for _, rate in class_rates) * overlap
    categories: dict[str, dict[str, float]] = {kind: {} for kind in _DEMAND_KINDS}
    for boundary_id, total in totals.items():
        kind = _demand_kind(boundary_id, cfg, demand_kind_by_id)
        categories[kind][boundary_id] = total / duration / VEH_PER_HOUR_TO_VEH_PER_SEC

    lane_loss: dict[str, dict[int, float]] = {}
    observed: dict[str, float] = {}
    for entry in value.entries:
        for loss in entry.freeway_lane_loss:
            if (
                abs(loss.start_time_sec - value.start_time_sec) > _TIME_TOLERANCE_SEC
                or abs(loss.end_time_sec - value.end_time_sec) > _TIME_TOLERANCE_SEC
            ):
                raise SchemaError("legacy DemandStep cannot represent time-varying freeway lane loss")
            previous = observed.setdefault(loss.segment_id, loss.lanes_closed)
            if abs(previous - loss.lanes_closed) > _TIME_TOLERANCE_SEC:
                raise SchemaError("conflicting lane-loss values for one segment")
    for segment_id, lanes_closed in observed.items():
        link_id, marker, raw_index = segment_id.rpartition("__seg")
        if not marker or not raw_index.isdigit():
            raise SchemaError(f"cannot decode strict segment ID {segment_id!r} into legacy lane loss")
        lane_loss.setdefault(link_id, {})[int(raw_index)] = lanes_closed
    if factory is None:
        raise BridgeError("strict demand conversion requires demand_step_factory")
    return factory(
        freeway_mainline=categories["freeway_mainline"],
        urban_boundary=categories["urban_boundary"],
        ramp_arrival=categories["ramp_arrival"],
        incident_capacity_factor=value.global_incident_capacity_factor,
        freeway_lane_loss=lane_loss,
    )


def strict_to_legacy(
    value: ControlAction | DemandSchedule,
    *,
    cfg: Any,
    demand_kind_by_id: Mapping[str, str] | None = None,
    control_action_factory: Callable[..., Any] | None = None,
    demand_step_factory: Callable[..., Any] | None = None,
) -> Any:
    """Convert strict SI schemas back to legacy units without silent loss."""

    if isinstance(value, ControlAction):
        return _strict_action_to_legacy(value, cfg=cfg, factory=control_action_factory)
    if isinstance(value, DemandSchedule):
        return _strict_demand_to_legacy(
            value,
            cfg=cfg,
            demand_kind_by_id=demand_kind_by_id,
            factory=demand_step_factory,
        )
    raise TypeError(f"unsupported strict type: {type(value).__name__}")


@dataclass(frozen=True)
class BridgeResult:
    path: str
    time_owner: str
    strict_state: PlantState | None
    step_results: tuple[StepResult, ...]
    legacy_result: Any = None


class StrictCouplingBridge:
    """Explicit strict/legacy switch for one coupled control interval.

    ``projector`` must return a strict state without mutating the legacy input.
    ``copy_back`` is invoked exactly once after the whole interval succeeds.
    Strict failures never fall back to the legacy path implicitly.
    """

    def __init__(
        self,
        *,
        mode: str,
        plant: Any | None = None,
        projector: Callable[[Any, PlantState | None], PlantState] | None = None,
        copy_back: Callable[[Any, PlantState], None] | None = None,
        legacy_fallback: Callable[[Any, Any, Any, Any, float], Any] | None = None,
    ) -> None:
        if mode not in {"strict", "legacy"}:
            raise ValueError("mode must be explicitly 'strict' or 'legacy'")
        if mode == "strict" and (plant is None or copy_back is None):
            raise ValueError("strict mode requires plant and copy_back")
        if mode == "legacy" and legacy_fallback is None:
            raise ValueError("legacy mode requires legacy_fallback")
        self.mode = mode
        self.plant = plant
        self.projector = projector
        self.copy_back = copy_back
        self.legacy_fallback = legacy_fallback
        self._strict_state_by_legacy_id: dict[int, PlantState] = {}

    def __call__(
        self,
        legacy_state: Any,
        legacy_action: Any,
        legacy_demand: Any,
        cfg: Any,
        *,
        end_time_sec: float,
        strict_state: PlantState | None = None,
        strict_action: ControlAction | None = None,
        strict_demand: DemandSchedule | None = None,
        signal_mapping: Mapping[str, Any] | None = None,
        signal_cycle_sec_by_controller: Mapping[str, float] | None = None,
        authority_ids: tuple[str, ...] | list[str] | set[str] = (),
    ) -> BridgeResult:
        end = _finite("end_time_sec", end_time_sec)
        if self.mode == "legacy":
            legacy_result = self.legacy_fallback(legacy_state, legacy_action, legacy_demand, cfg, end)
            return BridgeResult("legacy", "legacy_kernel", None, (), legacy_result)

        start = _finite("legacy_state.time_sec", legacy_state.time_sec)
        if end <= start + _TIME_TOLERANCE_SEC:
            raise BridgeError("double-step or non-advancing interval rejected")
        cached = self._strict_state_by_legacy_id.get(id(legacy_state))
        if strict_state is None:
            if cached is not None and abs(cached.sim_time_sec - start) <= _TIME_TOLERANCE_SEC:
                strict_state = cached
            elif self.projector is not None:
                strict_state = self.projector(legacy_state, cached)
            else:
                raise BridgeError("strict_state or projector is required")
        if abs(strict_state.sim_time_sec - start) > _TIME_TOLERANCE_SEC:
            raise BridgeError("legacy and strict clocks disagree before stepping")
        if strict_state.topology_hash != self.plant.topology_hash:
            raise BridgeError("strict state topology hash does not match plant")

        action = strict_action or legacy_to_strict(
            legacy_action,
            cfg=cfg,
            topology_hash=self.plant.topology_hash,
            based_on_state_hash=strict_state.state_hash,
            start_time_sec=start,
            end_time_sec=end,
            signal_mapping=signal_mapping,
            signal_cycle_sec_by_controller=signal_cycle_sec_by_controller,
            authority_ids=authority_ids,
        )
        demand = strict_demand or legacy_to_strict(
            legacy_demand,
            cfg=cfg,
            topology_hash=self.plant.topology_hash,
            start_time_sec=start,
            end_time_sec=end,
        )
        if action.topology_hash != self.plant.topology_hash or demand.topology_hash != self.plant.topology_hash:
            raise BridgeError("action/demand topology hash does not match plant")
        if action.based_on_state_hash != strict_state.state_hash:
            raise BridgeError("stale action state hash rejected before strict execution")

        results: list[StepResult] = []
        advance_interval = getattr(self.plant, "advance_interval", None)
        if callable(advance_interval):
            result = advance_interval(strict_state, action, demand, end)
            results.append(result)
            next_state = self._require_success(result)
        else:
            dt = _finite("plant.parameters.urban_dt_sec", self.plant.parameters.urban_dt_sec, positive=True)
            count_float = (end - start) / dt
            count = int(round(count_float))
            if count <= 0 or abs(count_float - count) > _TIME_TOLERANCE_SEC:
                raise BridgeError("control interval must be an integer multiple of strict kernel dt")
            next_state = strict_state
            for _ in range(count):
                step_action = replace(action, based_on_state_hash=next_state.state_hash, action_hash="")
                result = self.plant.step(next_state, step_action, demand, dt)
                results.append(result)
                next_state = self._require_success(result)

        if abs(next_state.sim_time_sec - end) > _TIME_TOLERANCE_SEC:
            raise BridgeError("strict kernel time freeze or overstep detected")
        self.copy_back(legacy_state, next_state)
        if abs(float(legacy_state.time_sec) - end) > _TIME_TOLERANCE_SEC:
            raise BridgeError("copy_back did not transfer strict-owned time")
        self._strict_state_by_legacy_id[id(legacy_state)] = next_state
        return BridgeResult("strict", "strict_kernel", next_state, tuple(results))

    @staticmethod
    def _require_success(result: StepResult) -> PlantState:
        if result.status is not StepStatus.OK or not result.is_feasible or result.next_state is None:
            raise BridgeError(f"strict step failed: {result.reason_code or result.status.value}")
        return result.next_state
