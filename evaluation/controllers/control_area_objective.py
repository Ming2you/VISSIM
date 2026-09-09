"""Strict accounting for Omega = controlled freeway union protected urban area.

This module does not install patches or change the current controller objective.
Callers supply validated physical membership and actual transition events. Vehicle
departures are never inferred from terminal stock. Mixed model reservoirs need
physical decomposition; their geometric inside fraction is not an occupancy share.

Integration points after mapping validation:
* urban_substep: emit actual movement transitions when queues enter receiving
  storage, not the later boundary_out_sink diagnostic;
* freeway_substep: emit actual per-off-ramp and controlled-chain terminal flows;
* coupling: integrate urban stocks at T_u and freeway stocks at T_f, once each.
  The existing aggregate diagnostics cannot reconstruct every movement crossing.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import copy
import math
from typing import Any, Iterable, Mapping, Sequence


class MembershipError(ValueError):
    """A physical location or mixed model reservoir lacks an exact assignment."""


def _nonnegative(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative: {value!r}")
    return result


def _validate_membership(membership: Mapping[str, bool]) -> dict[str, bool]:
    result = {}
    for key, value in membership.items():
        if not isinstance(key, str) or not key or type(value) is not bool:
            raise MembershipError(f"membership requires nonempty string -> bool: {key!r}: {value!r}")
        result[key] = value
    return result


def physical_membership_from_ledger(document: Mapping[str, Any]) -> dict[str, bool]:
    """Read the physical ledger; unresolved or conflicting assignments fail closed."""
    if document.get("schema") != "control-area-membership/v1":
        raise MembershipError("expected schema control-area-membership/v1")
    if document.get("unresolved"):
        raise MembershipError(f"physical ledger has unresolved items: {document['unresolved']!r}")
    inside = {str(key) for key in document.get("inside_links", ())}
    outside = {str(key) for key in document.get("outside_links", ())}
    if not inside or inside & outside:
        raise MembershipError(f"empty inside set or conflicting physical links: {sorted(inside & outside)}")
    return {**dict.fromkeys(inside, True), **dict.fromkeys(outside, False)}


def projection_stock_cohorts(
    physical_assignments: Mapping[str, Mapping[str, float]],
    physical_membership: Mapping[str, bool],
) -> dict[str, dict[str, float]]:
    """Use actual projection contributions, never static support-size fractions.

    These are exact inside/outside counts *of the projected model stock*. Any
    pre-existing physical-to-model approximation remains visible in the source
    assignments. Future motion across the boundary needs explicit flow events.
    """
    membership = _validate_membership(physical_membership)
    result: dict[str, dict[str, float]] = {}
    for physical_link, by_stock in physical_assignments.items():
        if physical_link not in membership:
            raise MembershipError(f"unknown assignment physical link: {physical_link}")
        side = "inside" if membership[physical_link] else "outside"
        for stock, value in by_stock.items():
            row = result.setdefault(stock, {"inside": 0.0, "outside": 0.0})
            row[side] += _nonnegative(value, f"assignment {physical_link} -> {stock}")
    return result


def resolve_model_membership(
    physical_membership: Mapping[str, bool],
    stock_supports: Mapping[str, Iterable[str]],
    required_stock_keys: Iterable[str],
) -> dict[str, bool]:
    """Join model stock to physical support without guessing an inside fraction.

    Every required stock must have nonempty physical support with one membership.
    A movement aggregating inside and outside links must be split upstream using
    observed vehicle counts or represented with separate model reservoirs.
    """
    physical = _validate_membership(physical_membership)
    result, errors = {}, []
    for key in sorted(set(required_stock_keys)):
        support = {str(link) for link in stock_supports.get(key, ())}
        missing = sorted(support - physical.keys())
        if not support or missing:
            errors.append(f"{key}: no support" if not support else f"{key}: unknown {missing}")
            continue
        values = {physical[link] for link in support}
        if len(values) != 1:
            errors.append(f"{key}: mixed inside/outside support {sorted(support)}")
            continue
        result[key] = values.pop()
    if errors:
        raise MembershipError("unresolved model membership; " + "; ".join(errors))
    return result


def detector_stock_supports(
    detector_mapping: Mapping[str, Any],
    *,
    off_ramp_storage_links: Mapping[str, str],
    freeway_chains: Mapping[str, Sequence[str]],
) -> dict[str, set[str]]:
    """Invert documented detector joins; missing/ambiguous stocks remain unresolved.

    Does not assign mainline origin queues or inflow transit to a physical road:
    their reservoir name alone does not establish which side of Omega they occupy.
    Detector support is necessary evidence, not a certificate that projected
    movement queues and ramp queues contain disjoint observed vehicles.
    """
    supports: dict[str, set[str]] = {}
    dedicated = detector_mapping.get("physical_storage_projection", {}).get("link_to_storage", {})
    dedicated_targets = set(dedicated.values())

    def add(key: str, link: Any) -> None:
        supports.setdefault(key, set()).add(str(link))

    for link, origins in detector_mapping.get("link_to_origins", {}).items():
        for origin in origins:
            add(f"storage:{off_ramp_storage_links.get(origin, origin)}", link)
    for link, rows in detector_mapping.get("link_to_movements", {}).items():
        for row in rows:
            # Zero-weight declarations supply no observed stock to this movement.
            if _nonnegative(row.get("weight", 1.0), f"movement weight on {link}") > 0.0:
                add(f"movement:{row['movement']}", link)
    for link, ramps in detector_mapping.get("ramp_link_to_queues", {}).items():
        for ramp in ramps:
            add(f"ramp:{ramp}", link)
    for off_ramp, storage in off_ramp_storage_links.items():
        # The installed direct/signal projection is more specific than the raw
        # group containing both physical branches; do not re-merge it here.
        if storage in dedicated_targets:
            continue
        for row in detector_mapping.get("off_ramp_connectors", {}).get(off_ramp, ()):
            add(f"storage:{storage}", row["connector"])
    for link, chain in freeway_chains.items():
        for physical_link in chain:
            add(f"freeway:{link}", physical_link)
    return supports


def model_stock_values(
    state: Any,
    network: Any,
    *,
    freeway_vehicle_counts: Mapping[str, Sequence[float]],
) -> dict[str, float]:
    """Expose distinct model stock fields for membership resolution and residence.

    Pass counts from the installed adapter's per-cell geometry-aware helper.
    Arrival/release schedules are not stocks. Inflow transit is a stock. This
    function does not repair pre-existing observation projection double counting.
    Buffer chains require explicit separate mapping and are rejected here.
    """
    for attribute in ("freeway_buffer_up_density", "freeway_buffer_down_density"):
        if any(getattr(state, attribute, {}).values()):
            raise MembershipError(f"{attribute} needs explicit stock and physical support")
    if set(freeway_vehicle_counts) != set(network.freeway_links):
        raise MembershipError("freeway counts must cover every configured model link")
    for name, actual, expected in (
        ("movement", state.urban_movement_queue, network.urban_movements),
        ("ramp", state.ramp_queue, network.ramps),
        ("origin", state.mainline_origin_queue, network.freeway_links),
    ):
        if set(actual) != set(expected):
            raise MembershipError(f"{name} state inventory differs from network")
    result: dict[str, float] = {}
    for prefix, values in (
        ("movement", state.urban_movement_queue),
        ("ramp", state.ramp_queue),
        ("origin", state.mainline_origin_queue),
    ):
        result.update({f"{prefix}:{key}": _nonnegative(value, f"{prefix}:{key}") for key, value in values.items()})
    for key, capacity in network.urban_link_storage_veh.items():
        if key not in state.urban_link_storage:
            raise MembershipError(f"missing storage state: {key}")
        cap = _nonnegative(capacity, f"storage capacity {key}")
        available = _nonnegative(state.urban_link_storage[key], f"available storage {key}")
        if available > cap + 1.0e-9:
            raise ValueError(f"available storage exceeds capacity: {key}")
        result[f"storage:{key}"] = max(0.0, cap - available)
    for link, values in freeway_vehicle_counts.items():
        result[f"freeway:{link}"] = sum(_nonnegative(value, f"freeway:{link}") for value in values)
    for source, by_step in state.urban_inflow_transit_buffer.items():
        result[f"transit:{source}"] = sum(_nonnegative(value, f"transit:{source}") for value in by_step.values())
    return result


@dataclass(frozen=True)
class AreaMetrics:
    ttt_veh_h: float = 0.0
    ttd_veh: float = 0.0
    entered_veh: float = 0.0


class ModelAreaLedger:
    """Candidate-private, explicitly routed inside/outside model cohorts.

    Drawing from a mixed model reservoir uses proportional mixing, an explicit
    prediction approximation. Initial cohort amounts come from physical vehicle
    projection provenance. Every crossing is generated by an accepted transfer,
    never by subtracting terminal stock. Native TrafficState.copy deep-copies it.
    """
    def __init__(self, stocks: Mapping[str, Mapping[str, float]]):
        self.stocks = {str(k): {side: _nonnegative(v.get(side, 0), f"{k}:{side}")
                               for side in ("inside", "outside")} for k, v in stocks.items()}
        self.ttt_veh_h = self.ttd_veh = self.entered_veh = 0.0
        self.flow_counts = Counter()
        self.explicit_events = {}
        self.event_count = 0

    @property
    def metrics(self):
        return AreaMetrics(self.ttt_veh_h, self.ttd_veh, self.entered_veh)

    def clone(self):
        return copy.deepcopy(self)

    def _duplicate(self, event_id, payload):
        if event_id is None:
            return False
        if event_id in self.explicit_events:
            if self.explicit_events[event_id] != payload:
                raise MembershipError(f"conflicting area event {event_id}")
            return True
        self.explicit_events[event_id] = payload
        return False

    @staticmethod
    def _external(key):
        return key is None or str(key).startswith("external:")

    def transfer(self, source, target, vehicles, *, inside_to_inside=None,
                 outside_to_inside=None, source_inside=None, route_key=None, event_id=None,
                 physical_source_inside=None, outward_crossings=None, inward_crossings=None):
        count = _nonnegative(vehicles, "accepted transfer")
        if count == 0:
            return
        payload = (source, target, count, inside_to_inside, outside_to_inside, source_inside, route_key,
                   physical_source_inside, outward_crossings, inward_crossings)
        if event_id is not None and event_id in self.explicit_events and self._duplicate(event_id, payload):
            return
        if self._external(source):
            if type(source_inside) is not bool:
                raise MembershipError(f"external input {source} requires explicit source_inside")
            draw_in = count if source_inside else 0.0
        else:
            row = self.stocks.get(source, {"inside": 0.0, "outside": 0.0})
            total = row["inside"] + row["outside"]
            if count > total + 1e-7:
                raise MembershipError(f"area transfer overdraws {source}: {count} > {total}")
            draw_in = count * row["inside"] / total if total else 0.0
        draw_out = count - draw_in
        probabilities = (inside_to_inside, outside_to_inside)
        for amount, value in zip((draw_in, draw_out), probabilities):
            if amount > 1e-9 and (value is None or not math.isfinite(float(value)) or not 0 <= float(value) <= 1):
                raise MembershipError(f"unresolved destination of {route_key or source}: {probabilities}")
        stay_in = draw_in * float(inside_to_inside or 0)
        enter_in = draw_out * float(outside_to_inside or 0)
        target_in = stay_in + enter_in
        if physical_source_inside is not None:
            if type(physical_source_inside) is not bool or outward_crossings is None or inward_crossings is None:
                raise MembershipError("physical path requires source side and both directed crossing counts")
            outward_crossings = _nonnegative(outward_crossings, "physical outward crossings")
            inward_crossings = _nonnegative(inward_crossings, "physical inward crossings")
        if event_id is not None:
            self.explicit_events[event_id] = payload
        if not self._external(source):
            self.stocks[source] = {"inside": max(0.0, row["inside"] - draw_in),
                                   "outside": max(0.0, row["outside"] - draw_out)}
        if not self._external(target):
            target_row = self.stocks.setdefault(target, {"inside": 0.0, "outside": 0.0})
            target_row["inside"] += target_in
            target_row["outside"] += count - target_in
        if physical_source_inside is not None:
            # A grouped storage's current cohort reaches the canonical stopline
            # before following its physical turn. Timing within the lumped link
            # is a prediction approximation, explicitly counted separately.
            remap_exit = draw_in if not physical_source_inside else 0.0
            remap_entry = draw_out if physical_source_inside else 0.0
            self.flow_counts["spatial_remap_exit_veh"] += remap_exit
            self.flow_counts["spatial_remap_entry_veh"] += remap_entry
            self.ttd_veh += remap_exit + count * _nonnegative(outward_crossings, "physical outward crossings")
            self.entered_veh += remap_entry + count * _nonnegative(inward_crossings, "physical inward crossings")
        else:
            self.ttd_veh += draw_in - stay_in
            self.entered_veh += enter_in
        self.event_count += 1
        self.flow_counts[str(route_key or f"{source}->{target}")] += count

    def residence(self, keys, dt_h, *, event_id=None):
        duration = _nonnegative(dt_h, "residence duration hours")
        keys = tuple(keys)
        if len(keys) != len(set(keys)):
            raise MembershipError("duplicate residence stock key")
        if self._duplicate(event_id, ("residence", keys, duration)):
            return
        self.ttt_veh_h += duration * sum(self.stocks.get(k, {}).get("inside", 0.0) for k in keys)

    def assert_stocks(self, model_stocks, *, tolerance=1e-6):
        differences = {}
        for key in self.stocks.keys() | model_stocks.keys():
            tracked = sum(self.stocks.get(key, {}).values())
            actual = float(model_stocks.get(key, 0.0))
            if abs(tracked - actual) > tolerance:
                differences[key] = {"tracked": tracked, "model": actual}
        if differences:
            raise MembershipError(f"area cohort/model stock mismatch: {differences}")


def get_ledger(state):
    return getattr(state, "_control_area_ledger", None)


def emit_transfer(state, cfg, source_stock, target_stock, vehicles, *, route_key=None,
                  target_inside=None, source_inside=None, preserve_area=False, event_id=None):
    """Single API called at accepted model-stock transfers. Disabled is a no-op."""
    ledger = get_ledger(state)
    if ledger is None:
        return
    if preserve_area:
        p_in, p_out = 1.0, 0.0
        route = {}
    elif target_inside is not None:
        if type(target_inside) is not bool:
            raise MembershipError("target_inside must be boolean")
        p_in = p_out = float(target_inside)
        route = {}
    else:
        route = (getattr(cfg.network, "control_area_routes", {}) or {}).get(route_key, {})
        p_in, p_out = route.get("inside_to_inside"), route.get("outside_to_inside")
        if p_in is None and p_out is None and type(route.get("target_inside")) is bool:
            p_in = p_out = float(route["target_inside"])
    ledger.transfer(source_stock, target_stock, vehicles, inside_to_inside=p_in,
                    outside_to_inside=p_out, source_inside=source_inside,
                    route_key=route_key, event_id=event_id,
                    physical_source_inside=route.get("source_inside") if "outward_crossings_per_vehicle" in route else None,
                    outward_crossings=route.get("outward_crossings_per_vehicle"),
                    inward_crossings=route.get("inward_crossings_per_vehicle"))
    if route.get('status') == 'DIAGNOSTIC_UNRESOLVED_PRESERVE':
        ledger.flow_counts['unresolved_route:' + str(route_key)] += float(vehicles)


def emit_input(state, cfg, target_stock, vehicles, *, route_key):
    if get_ledger(state) is None or float(vehicles) == 0:
        return
    route = (getattr(cfg.network, "control_area_routes", {}) or {}).get(route_key, {})
    side = route.get("target_inside")
    if type(side) is not bool:
        raise MembershipError(f"input physical membership missing: {route_key}")
    emit_transfer(state, cfg, None, target_stock, vehicles, source_inside=side,
                  target_inside=side, route_key=route_key)


def integrate_residence(state, cfg, stock_keys, dt_h, *, event_id=None):
    ledger = get_ledger(state)
    if ledger is not None:
        ledger.residence(stock_keys, dt_h, event_id=event_id)


class ControlAreaLedger:
    """Integrate supplied stock residence and count explicit directed crossings.

    One ledger belongs to one rollout or measurement window. Event IDs must be
    stable on retries and unique for different real events, including re-entry.
    Residence windows for the same stock may not overlap; disjoint urban/freeway
    stock groups can use their respective substep clocks.
    """

    def __init__(self, membership: Mapping[str, bool]):
        self.membership = _validate_membership(membership)
        self._events: dict[str, tuple] = {}
        self._stock_end: dict[str, float] = {}
        self._ttt = self._ttd = self._entered = 0.0

    def _inside(self, key: str) -> bool:
        if key not in self.membership:
            raise MembershipError(f"unmapped location/stock: {key}")
        return self.membership[key]

    def _is_duplicate(self, event_id: str, payload: tuple) -> bool:
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("event_id must be a nonempty string")
        if event_id not in self._events:
            return False
        if self._events[event_id] != payload:
            raise ValueError(f"conflicting duplicate event: {event_id}")
        return True

    def inside_stock(self, stocks: Mapping[str, float]) -> float:
        total = 0.0
        for key, value in stocks.items():
            count = _nonnegative(value, key)
            if self._inside(key):
                total += count
        return total

    def record_residence(
        self, event_id: str, *, start_sec: float, end_sec: float, stocks: Mapping[str, float]
    ) -> bool:
        """Record a piecewise-constant count over [start,end), in veh*h.

        Caller chooses an observed residence interval or the model's documented
        substep quadrature. Endpoint snapshots alone are not exact trajectories.
        """
        start = _nonnegative(start_sec, "start_sec")
        end = _nonnegative(end_sec, "end_sec")
        if end <= start:
            raise ValueError("residence end_sec must exceed start_sec")
        inside = self.inside_stock(stocks)
        payload = ("residence", start, end, tuple(sorted((k, float(v)) for k, v in stocks.items())))
        if self._is_duplicate(event_id, payload):
            return False
        for key in stocks:
            if start < self._stock_end.get(key, start) - 1.0e-9:
                raise ValueError(f"overlapping or reversed residence for {key}")
        self._events[event_id] = payload
        self._stock_end.update(dict.fromkeys(stocks, end))
        self._ttt += inside * (end - start) / 3600.0
        return True

    def record_crossing(
        self, event_id: str, *, source: str, target: str, vehicles: float
    ) -> bool:
        """Count actual Omega->outside events; internal transfers add zero TTD.

        A natural exit needs an explicitly mapped outside endpoint. Missing
        observations, unknown targets and disappearance are not exit evidence.
        """
        amount = _nonnegative(vehicles, "vehicles")
        source_inside, target_inside = self._inside(source), self._inside(target)
        payload = ("crossing", source, target, amount)
        if self._is_duplicate(event_id, payload):
            return False
        self._events[event_id] = payload
        if source_inside and not target_inside:
            self._ttd += amount
        elif target_inside and not source_inside:
            self._entered += amount
        return True

    @property
    def metrics(self) -> AreaMetrics:
        return AreaMetrics(self._ttt, self._ttd, self._entered)

    def mass_residual(
        self, opening: Mapping[str, float], closing: Mapping[str, float],
        *, generated_inside_veh: float = 0.0, removed_inside_veh: float = 0.0,
    ) -> float:
        """Validate recorded flux against stock; never use this to generate TTD."""
        if set(opening) != set(closing):
            raise MembershipError("opening and closing stock inventories differ")
        change = self.inside_stock(closing) - self.inside_stock(opening)
        expected = (self._entered - self._ttd
                    + _nonnegative(generated_inside_veh, "generated_inside_veh")
                    - _nonnegative(removed_inside_veh, "removed_inside_veh"))
        return change - expected


@dataclass(frozen=True)
class ControlAreaObjective:
    """J[veh*h] = TTT[veh*h] - beta_hours[h] * TTD[veh]. No implicit beta."""

    beta_hours: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "beta_hours", _nonnegative(self.beta_hours, "beta_hours"))

    def score(self, metrics: AreaMetrics, *, nonnegative_cost_veh_h: float = 0.0) -> float:
        return (_nonnegative(metrics.ttt_veh_h, "ttt_veh_h")
                - self.beta_hours * _nonnegative(metrics.ttd_veh, "ttd_veh")
                + _nonnegative(nonnegative_cost_veh_h, "nonnegative_cost_veh_h"))

    def lower_bound(
        self, partial: AreaMetrics, *, max_future_exits_veh: float | None,
        accrued_nonnegative_cost_veh_h: float = 0.0,
    ) -> float:
        """Admissible only if the caller certifies the remaining exit upper bound.

        Future TTT and additional costs must be nonnegative. Without a certified
        exit bound, a positive departure reward disables this pruning bound.
        """
        value = self.score(partial, nonnegative_cost_veh_h=accrued_nonnegative_cost_veh_h)
        if max_future_exits_veh is None:
            return value if self.beta_hours == 0.0 else -math.inf
        return value - self.beta_hours * _nonnegative(max_future_exits_veh, "max_future_exits_veh")

    def can_prune(
        self, partial: AreaMetrics, *, incumbent_veh_h: float,
        max_future_exits_veh: float | None,
    ) -> bool:
        incumbent = float(incumbent_veh_h)
        if math.isnan(incumbent):
            raise ValueError("incumbent cannot be NaN")
        return self.lower_bound(partial, max_future_exits_veh=max_future_exits_veh) > incumbent
