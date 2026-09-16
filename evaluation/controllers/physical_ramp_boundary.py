"""Finite ramp connector with a signal head upstream of the merge boundary.

This is a fluid cohort buffer, not a second freeway or signal model. The caller
supplies the existing meter's service amount and the freeway's accepted merge
amount. A new red can restrict head service, never vehicles past the head.

Each interval advances existing travelling cohorts to its end, exposes merge
eligibility, commits accepted merges, applies head service, then admits approach
requests. New head departures and admissions occur at the interval end. Travel
uses the supplied mean speed, including for initial stopped vehicles: snapshot
speeds are validated and retained, not extrapolated as permanent speeds. Positive
post-head travel therefore prevents a newly served vehicle merging in that same
interval. No within-horizon observations are read here.

Connector TTT uses start-of-interval stock * duration. Outside-component backlog
is conserved separately and is not claimed to be Omega stock or included in TTT.
The caller must account for that backlog's actual upstream area and waiting cost.
"""
from __future__ import annotations

from math import fsum, isfinite
from typing import Iterable, Sequence


_MASS_TOLERANCE = 1.0e-8  # Roundoff check only; not an admission/merge allowance.


def _number(value: float, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return result


def _sum(values: Iterable[float], name: str) -> float:
    try:
        result = fsum(values)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name} overflow") from exc
    return _number(result, name)


class PhysicalRampBoundary:
    """One connector; use separate instances for the eight physical ramps.

    ``initial_cohorts`` has one ``[position_m, speed_kmh, lane]`` row per vehicle.
    All model quantities, including storage spacing and travel speed, are explicit
    constructor inputs. Subsequent requests and service may be fractional vehicles.
    No service capacity is inferred from the mode or green label in this class.
    """

    def __init__(
        self, *, connector_id: str, length_m: float, head_position_m: float,
        lanes: int, spacing_m: float, travel_speed_kmh: float, time_sec: float,
        initial_cohorts: Iterable[Sequence[float]] = (),
        initial_backlog_veh: float = 0.0,
    ):
        self.connector_id = str(connector_id)
        self.length_m = _number(length_m, "length_m", positive=True)
        self.head_position_m = _number(head_position_m, "head_position_m")
        if self.head_position_m >= self.length_m:
            raise ValueError("head_position_m must be strictly before the connector end")
        lane_value = _number(lanes, "lanes", positive=True)
        if not lane_value.is_integer():
            raise ValueError("lanes must be an integer")
        self.lanes = int(lane_value)
        self.spacing_m = _number(spacing_m, "spacing_m", positive=True)
        self.travel_speed_kmh = _number(travel_speed_kmh, "travel_speed_kmh", positive=True)
        self._speed_mps = _number(self.travel_speed_kmh / 3.6, "travel_speed_mps", positive=True)
        self.time_sec = _number(time_sec, "time_sec")
        self.capacity_veh = _number(self.length_m * self.lanes / self.spacing_m,
                                    "capacity_veh", positive=True)
        self.backlog_veh = _number(initial_backlog_veh, "initial_backlog_veh")
        self._upstream: list[tuple[float, float]] = []
        self._downstream: list[tuple[float, float]] = []
        self._head_ready = 0.0
        self._merge_ready = 0.0
        rows = []
        for row in initial_cohorts:
            if len(row) != 3:
                raise ValueError("initial cohort must be [position_m, speed_kmh, lane]")
            pos = _number(row[0], "initial position_m")
            speed = _number(row[1], "initial speed_kmh")
            lane = _number(row[2], "initial lane", positive=True)
            if pos > self.length_m or not lane.is_integer() or lane > self.lanes:
                raise ValueError("initial cohort is outside connector geometry")
            rows.append((pos, speed, int(lane)))
            if pos < self.head_position_m:
                self._upstream.append((self._arrival(self.time_sec, self.head_position_m-pos), 1.0))
            elif pos == self.head_position_m:
                self._head_ready += 1.0
            elif pos < self.length_m:
                self._downstream.append((self._arrival(self.time_sec, self.length_m-pos), 1.0))
            else:
                self._merge_ready += 1.0
        self.initial_cohorts = tuple(rows)
        self._initial_connector = float(len(rows))
        self._initial_backlog = self.backlog_veh
        self._initial_total = _sum((self._initial_connector, self.backlog_veh), "initial total")
        if self._initial_connector > self.capacity_veh:
            raise ValueError("initial connector stock exceeds finite storage")
        self.cumulative_requested_veh = 0.0
        self.cumulative_admitted_veh = 0.0
        self.cumulative_head_service_veh = 0.0
        self.cumulative_merge_veh = 0.0
        self.connector_ttt_veh_h = 0.0
        self._phase = "idle"
        self._receipt: dict = {}
        self._check_conservation()

    def _arrival(self, departure: float, distance_m: float) -> float:
        return _number(departure + distance_m / self._speed_mps, "cohort arrival time")

    def _require_phase(self, expected: str) -> None:
        if self._phase != expected:
            raise ValueError(f"Expected phase {expected}, got {self._phase}")

    def _stocks(self) -> dict[str, float]:
        stocks = {
            "upstream_travelling_veh": _sum((n for _, n in self._upstream), "upstream stock"),
            "head_ready_veh": self._head_ready,
            "downstream_travelling_veh": _sum((n for _, n in self._downstream), "downstream stock"),
            "merge_ready_veh": self._merge_ready,
        }
        stocks["connector_veh"] = _sum(stocks.values(), "connector stock")
        return stocks

    def _check_conservation(self) -> float:
        stock = self._stocks()["connector_veh"]
        if stock > self.capacity_veh + _MASS_TOLERANCE:
            raise ValueError("Connector stock exceeds storage")
        expected = _sum((self._initial_total, self.cumulative_requested_veh), "mass source")
        actual = _sum((stock, self.backlog_veh, self.cumulative_merge_veh), "mass destination")
        residual = expected - actual
        if abs(residual) > _MASS_TOLERANCE:
            raise ValueError(f"Ramp mass conservation failed: {residual} vehicles")
        connector_residual = (self._initial_connector + self.cumulative_admitted_veh
                              - self.cumulative_merge_veh - stock)
        backlog_residual = (self._initial_backlog + self.cumulative_requested_veh
                            - self.cumulative_admitted_veh - self.backlog_veh)
        if max(abs(connector_residual), abs(backlog_residual)) > _MASS_TOLERANCE:
            raise ValueError("Connector/backlog transfer accounting failed")
        return residual

    def snapshot(self) -> dict:
        """Return counts without exposing mutable cohort buffers."""
        return {
            "connector_id": self.connector_id, "time_sec": self.time_sec,
            "phase": self._phase, **self._stocks(), "capacity_veh": self.capacity_veh,
            "outside_component_backlog_veh": self.backlog_veh,
            "cumulative_requested_veh": self.cumulative_requested_veh,
            "cumulative_admitted_veh": self.cumulative_admitted_veh,
            "cumulative_head_service_veh": self.cumulative_head_service_veh,
            "cumulative_merge_veh": self.cumulative_merge_veh,
            "connector_ttt_veh_h": self.connector_ttt_veh_h,
            "conservation_residual_veh": self._check_conservation(),
        }

    def metadata(self) -> dict:
        return {
            "schema": "physical-ramp-boundary/v1", "connector_id": self.connector_id,
            "length_m": self.length_m, "head_position_m": self.head_position_m,
            "lanes": self.lanes, "spacing_m": self.spacing_m,
            "travel_speed_kmh": self.travel_speed_kmh,
            "post_head_travel_sec": (self.length_m-self.head_position_m)/self._speed_mps,
            "capacity_veh": self.capacity_veh,
            "travel_model": "Deterministic supplied mean speed; initial speeds retained but not extrapolated",
            "time_rule": "Existing cohorts advance to interval end; new head departures and admissions occur at end",
            "service_model": "Explicit caller amount; cycle-mean service, not individual signal pulses",
            "ttt_rule": "Interval-start connector stock times duration; outside-component backlog excluded",
            "initial_cohorts": self.initial_cohorts,
        }

    def begin_interval(self, start_sec: float, duration_sec: float = 10.0) -> dict:
        self._require_phase("idle")
        start = _number(start_sec, "start_sec")
        duration = _number(duration_sec, "duration_sec", positive=True)
        if start != self.time_sec:
            raise ValueError(f"Noncontiguous interval: {start} != {self.time_sec}")
        end = _number(start + duration, "end_sec", positive=True)
        if end <= start:
            raise ValueError("Interval duration is below clock precision")
        before = self.snapshot()
        # Compute first, so invalid arithmetic cannot partially advance a buffer.
        upstream = [(eta, n) for eta, n in self._upstream if eta > end]
        downstream = [(eta, n) for eta, n in self._downstream if eta > end]
        head_arrived = _sum((n for eta, n in self._upstream if eta <= end), "head arrivals")
        merge_arrived = _sum((n for eta, n in self._downstream if eta <= end), "merge arrivals")
        head_ready = _sum((self._head_ready, head_arrived), "head-ready stock")
        merge_ready = _sum((self._merge_ready, merge_arrived), "merge-ready stock")
        ttt = _number(before["connector_veh"] * duration / 3600.0, "interval TTT")
        total_ttt = _sum((self.connector_ttt_veh_h, ttt), "cumulative TTT")
        self._upstream, self._downstream = upstream, downstream
        self._head_ready, self._merge_ready = head_ready, merge_ready
        self._receipt = {
            "start_sec": start, "end_sec": end, "duration_sec": duration,
            "start": before, "arrived_at_head_veh": head_arrived,
            "arrived_at_merge_veh": merge_arrived,
            "eligible_merge_veh": merge_ready, "connector_ttt_veh_h": ttt,
        }
        self.connector_ttt_veh_h = total_ttt
        self._phase = "merge"
        self._check_conservation()
        return {"eligible_merge_veh": merge_ready, "start_sec": start, "end_sec": end,
                "head_ready_veh": head_ready}

    def commit_merge(self, accepted_veh: float) -> None:
        self._require_phase("merge")
        accepted = _number(accepted_veh, "accepted_veh")
        if accepted > self._merge_ready:
            raise ValueError("Accepted merge exceeds eligible stock")
        total = _sum((self.cumulative_merge_veh, accepted), "cumulative merge")
        self._merge_ready -= accepted
        self.cumulative_merge_veh = total
        self._receipt["accepted_merge_veh"] = accepted
        self._phase = "head"
        self._check_conservation()

    def apply_head_service(self, service_veh: float, *, mode: str,
                           green_sec: float | None = None,
                           posthead_capacity_veh: float | None = None) -> float:
        self._require_phase("head")
        service = _number(service_veh, "service_veh")
        if mode not in {"OFF", "GREEN", "RED"}:
            raise ValueError("Meter mode must be OFF, GREEN or RED")
        green = None if green_sec is None else _number(green_sec, "green_sec")
        if mode == "OFF" and green is not None:
            raise ValueError("Native OFF is distinct from a green duration")
        if mode == "RED" and (service != 0 or green not in (None, 0.0)):
            raise ValueError("RED cannot provide head service")
        if mode == "GREEN" and green == 0 and service > 0:
            raise ValueError("Zero green cannot provide positive head service")
        posthead_free = None
        if posthead_capacity_veh is not None:
            capacity = _number(posthead_capacity_veh, "posthead_capacity_veh", positive=True)
            posthead = _sum((self._merge_ready, *(n for _, n in self._downstream)),
                            "posthead stock")
            # Observed fronts may initially exceed the nominal spacing-based
            # bound. Keep them, but admit no new head departure until space opens.
            posthead_free = max(0.0, capacity-posthead)
        served = min(service, self._head_ready)
        if posthead_free is not None:
            served = min(served, posthead_free)
        arrival = self._arrival(self._receipt["end_sec"], self.length_m-self.head_position_m)
        if arrival <= self._receipt["end_sec"]:
            raise ValueError("Post-head travel is below clock precision")
        total = _sum((self.cumulative_head_service_veh, served), "cumulative head service")
        if served:
            self._downstream.append((arrival, served))
        self._head_ready -= served
        self.cumulative_head_service_veh = total
        self._receipt.update({"meter_mode": mode, "green_sec": green,
                              "head_service_limit_veh": service,
                              "head_service_veh": served})
        if posthead_free is not None:
            self._receipt.update(posthead_free_before_service_veh=posthead_free,
                                 nominal_posthead_storage_veh=capacity)
        self._phase = "admit"
        self._check_conservation()
        return served

    def finish_interval(self, request_arrivals_veh: float) -> dict:
        self._require_phase("admit")
        requested = _number(request_arrivals_veh, "request_arrivals_veh")
        available = _sum((self.backlog_veh, requested), "approach available")
        free = max(0.0, self.capacity_veh-self._stocks()["connector_veh"])
        admitted = min(available, free)
        backlog = available-admitted
        total_requested = _sum((self.cumulative_requested_veh, requested), "cumulative requests")
        total_admitted = _sum((self.cumulative_admitted_veh, admitted), "cumulative admissions")
        end = self._receipt["end_sec"]
        arrival = self._arrival(end, self.head_position_m)
        if admitted:
            if self.head_position_m == 0:
                self._head_ready = _sum((self._head_ready, admitted), "head-ready stock")
            else:
                self._upstream.append((arrival, admitted))
        self.backlog_veh = backlog
        self.cumulative_requested_veh = total_requested
        self.cumulative_admitted_veh = total_admitted
        self.time_sec = end
        self._phase = "idle"
        after = self.snapshot()
        self._receipt.update({
            "requested_arrivals_veh": requested, "admitted_arrivals_veh": admitted,
            "end": after, "conservation_residual_veh": after["conservation_residual_veh"],
        })
        # The receipt's nested snapshots contain only scalars, so callers may keep
        # them without aliasing any subsequent buffer state.
        return dict(self._receipt)

    def advance_local_interval(self, *, start_sec: float, duration_sec: float,
                               cycle_sec: float, receiving_budget_veh: float,
                               service_veh: float, mode: str,
                               green_sec: float | None,
                               request_arrivals_veh: float) -> dict:
        """One complete meter cycle in local 1 s steps, with frozen FW supply.

        The caller queries the canonical freeway receiving budget once. Its
        uniform per-second envelope prevents spending all supply at the start.
        Head service keeps the supplied cycle budget and native first-g-seconds
        RG phase (the interval ending at t+1 is the native t+1 sample).
        Existing direct begin/merge/head/admit calls are unchanged.
        """
        self._require_phase("idle")
        start = _number(start_sec, "start_sec")
        duration = _number(duration_sec, "duration_sec", positive=True)
        cycle = _number(cycle_sec, "cycle_sec", positive=True)
        budget = _number(receiving_budget_veh, "receiving_budget_veh")
        service = _number(service_veh, "service_veh")
        requests = _number(request_arrivals_veh, "request_arrivals_veh")
        green = None if green_sec is None else _number(green_sec, "green_sec")
        if (start != self.time_sec or not start.is_integer() or not duration.is_integer()
                or duration != cycle or start % cycle != 0):
            raise ValueError("Local interval must be one aligned integral-second meter cycle")
        if mode not in {"OFF", "GREEN", "RED"}:
            raise ValueError("Unknown meter mode")
        if mode == "OFF" and green is not None:
            raise ValueError("OFF must not be relabeled as a green duration")
        if mode == "GREEN" and (green is None or not green.is_integer() or not 0 < green <= cycle):
            raise ValueError("Active meter requires an integral green within its cycle")
        if mode == "RED" and (service != 0 or green not in (None, 0.0)):
            raise ValueError("RED cannot provide service")
        capacity = (self.length_m-self.head_position_m)*self.lanes/self.spacing_m
        before = self.snapshot()
        local_rows = []
        used = 0.0
        for second in range(int(duration)):
            ready = self.begin_interval(start+second, 1.0)["eligible_merge_veh"]
            accepted = min(ready, budget/duration, max(0.0, budget-used))
            self.commit_merge(accepted)
            used = _sum((used, accepted), "local receiving consumption")
            active = mode == "OFF" or (mode == "GREEN" and second < green)
            local_mode = "OFF" if mode == "OFF" else "GREEN" if active else "RED"
            amount = service/(duration if mode == "OFF" else green) if active else 0.0
            self.apply_head_service(amount, mode=local_mode,
                green_sec=None if mode == "OFF" else green if active else 0.0,
                posthead_capacity_veh=capacity)
            local_rows.append(self.finish_interval(requests/duration))
        after = self.snapshot()
        counts = {key: _sum((r[key] for r in local_rows), key) for key in (
            "arrived_at_head_veh", "arrived_at_merge_veh", "accepted_merge_veh",
            "head_service_veh", "requested_arrivals_veh", "admitted_arrivals_veh",
            "connector_ttt_veh_h")}
        snapshots = [before]+[r['end'] for r in local_rows]
        posthead = [s['downstream_travelling_veh']+s['merge_ready_veh'] for s in snapshots]
        return {"start_sec": start, "end_sec": start+duration, "duration_sec": duration,
            "start": before, "end": after, **counts,
            "eligible_merge_veh": local_rows[0]['eligible_merge_veh'],
            "eligible_merge_scope": "First local1s eligibility only; later substeps may receive newly head-served vehicles",
            "meter_mode": mode, "green_sec": green, "head_service_limit_veh": service,
            "conservation_residual_veh": after['conservation_residual_veh'],
            "local_step_sec": 1.0, "local_receipts": local_rows,
            "receiving_budget_veh": budget, "unused_receiving_budget_veh": max(0.0,budget-used),
            "receiving_rate_envelope_veh_s": budget/duration,
            "nominal_posthead_storage_veh": capacity, "max_posthead_veh": max(posthead),
            "initial_posthead_excess_veh": max(0.0,posthead[0]-capacity)}
