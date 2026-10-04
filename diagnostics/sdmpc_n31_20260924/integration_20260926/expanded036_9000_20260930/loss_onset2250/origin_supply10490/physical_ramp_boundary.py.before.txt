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

from math import exp, expm1, fsum, isfinite
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


def gap_acceptance_supply_vph(conflicting_vph: float, critical_sec: float,
                              followup_sec: float) -> float:
    """Per-lane gap opportunity bound; not a demand or a promised release.

    Poisson conflicting arrivals and fixed critical/follow-up times are a closure
    approximation. Always intersect this with the existing mainline receiving
    budget. Actual release remains limited by eligible ramp stock and the meter.
    """
    q = _number(conflicting_vph, 'conflicting_vph')
    tc = _number(critical_sec, 'critical_sec', positive=True)
    tf = _number(followup_sec, 'followup_sec', positive=True)
    if tc < tf:
        raise ValueError('Critical gap must be at least the follow-up time')
    if q == 0:
        return 3600. / tf
    return q * exp(-q * tc / 3600.) / -expm1(-q * tf / 3600.)


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
        posthead_travel_speed_kmh: float | None = None,
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
        self.posthead_travel_speed_kmh = (self.travel_speed_kmh if posthead_travel_speed_kmh is None
            else _number(posthead_travel_speed_kmh, 'posthead_travel_speed_kmh', positive=True))
        self._posthead_speed_mps = self.posthead_travel_speed_kmh / 3.6
        self._split_travel = posthead_travel_speed_kmh is not None
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
                self._downstream.append((self._arrival(self.time_sec, self.length_m-pos, posthead=True), 1.0))
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

    def _arrival(self, departure: float, distance_m: float, *, posthead: bool = False) -> float:
        speed = self._posthead_speed_mps if posthead else self._speed_mps
        return _number(departure + distance_m / speed, "cohort arrival time")

    def _require_phase(self, expected: str) -> None:
        if self._phase != expected:
            raise ValueError(f"Expected phase {expected}, got {self._phase}")

    def _stocks(self) -> dict[str, float]:
        from evaluation.controllers.sdmpc_prediction_cache import ramp_stock_entry
        cache,key,saved=ramp_stock_entry(self)
        if saved is not None:
            return dict(saved)
        stocks = {
            "upstream_travelling_veh": _sum((n for _, n in self._upstream), "upstream stock"),
            "head_ready_veh": self._head_ready,
            "downstream_travelling_veh": _sum((n for _, n in self._downstream), "downstream stock"),
            "merge_ready_veh": self._merge_ready,
        }
        stocks["connector_veh"] = _sum(stocks.values(), "connector stock")
        if cache is not None:
            cache.ramp_stocks[key]=dict(stocks)
        return stocks

    def _check_conservation(self, *, stock=None) -> float:
        if stock is None:
            stock = self._stocks()["connector_veh"]
        if stock > self.capacity_veh + _MASS_TOLERANCE:
            raise ValueError("Connector stock exceeds storage")
        expected = _sum((self._initial_total, self.cumulative_requested_veh), "mass source")
        actual = _sum((stock, self.backlog_veh, self.cumulative_merge_veh), "mass destination")
        if hasattr(self, '_lane_transfer_in'):
            expected = _sum((expected, self._lane_transfer_in), 'mass with lateral entry')
            actual = _sum((actual, self._lane_transfer_out), 'mass with lateral exit')
        residual = expected - actual
        if abs(residual) > _MASS_TOLERANCE:
            raise ValueError(f"Ramp mass conservation failed: {residual} vehicles")
        connector_residual = (self._initial_connector + self.cumulative_admitted_veh
                              - self.cumulative_merge_veh - stock)
        if hasattr(self, '_lane_transfer_in'):
            connector_residual += self._lane_transfer_in-self._lane_transfer_out
        backlog_residual = (self._initial_backlog + self.cumulative_requested_veh
                            - self.cumulative_admitted_veh - self.backlog_veh)
        if max(abs(connector_residual), abs(backlog_residual)) > _MASS_TOLERANCE:
            raise ValueError("Connector/backlog transfer accounting failed")
        return residual

    def snapshot(self) -> dict:
        """Return counts without exposing mutable cohort buffers."""
        from evaluation.controllers.sdmpc_prediction_cache import active
        stocks = self._stocks()
        result = {
            "connector_id": self.connector_id, "time_sec": self.time_sec,
            "phase": self._phase, **stocks, "capacity_veh": self.capacity_veh,
            "outside_component_backlog_veh": self.backlog_veh,
            "cumulative_requested_veh": self.cumulative_requested_veh,
            "cumulative_admitted_veh": self.cumulative_admitted_veh,
            "cumulative_head_service_veh": self.cumulative_head_service_veh,
            "cumulative_merge_veh": self.cumulative_merge_veh,
            "connector_ttt_veh_h": self.connector_ttt_veh_h,
            "conservation_residual_veh": (self._check_conservation(stock=stocks['connector_veh'])
                if active() is not None else self._check_conservation()),
        }
        if hasattr(self, '_lane_transfer_in'):
            result.update(cumulative_lane_entry_veh=self._lane_transfer_in,
                          cumulative_lane_exit_veh=self._lane_transfer_out)
        return result

    def metadata(self) -> dict:
        result = {
            "schema": "physical-ramp-boundary/v1", "connector_id": self.connector_id,
            "length_m": self.length_m, "head_position_m": self.head_position_m,
            "lanes": self.lanes, "spacing_m": self.spacing_m,
            "travel_speed_kmh": self.travel_speed_kmh,
            "post_head_travel_sec": (self.length_m-self.head_position_m)/self._posthead_speed_mps,
            "capacity_veh": self.capacity_veh,
            "travel_model": "Deterministic supplied mean speed; initial speeds retained but not extrapolated",
            "time_rule": "Existing cohorts advance to interval end; new head departures and admissions occur at end",
            "service_model": "Explicit caller amount; cycle-mean service, not individual signal pulses",
            "ttt_rule": "Interval-start connector stock times duration; outside-component backlog excluded",
            "initial_cohorts": self.initial_cohorts,
        }
        if self._split_travel:
            result['posthead_travel_speed_kmh'] = self.posthead_travel_speed_kmh
            result['travel_model'] = 'Separate supplied approach/post-head speeds; receiving queue adds delay explicitly'
        return result

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
        from evaluation.controllers.sdmpc_prediction_cache import invalidate_ramp
        invalidate_ramp(self)
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
        from evaluation.controllers.sdmpc_prediction_cache import invalidate_ramp
        invalidate_ramp(self)
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
        arrival = self._arrival(self._receipt["end_sec"], self.length_m-self.head_position_m, posthead=True)
        if arrival <= self._receipt["end_sec"]:
            raise ValueError("Post-head travel is below clock precision")
        total = _sum((self.cumulative_head_service_veh, served), "cumulative head service")
        from evaluation.controllers.sdmpc_prediction_cache import invalidate_ramp
        invalidate_ramp(self)
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
            from evaluation.controllers.sdmpc_prediction_cache import invalidate_ramp
            invalidate_ramp(self)
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

    def current_admission_space(self) -> float:
        """Space for accepted coupled arrivals at this interval's completed end."""
        self._require_phase('idle')
        if self.backlog_veh:
            raise ValueError('Coupled admission cannot own an upstream backlog')
        return max(0., self.capacity_veh-self._stocks()['connector_veh'])

    def admit_current(self, vehicles: float) -> None:
        """Commit an already accepted urban transfer without advancing time.

        This is the admission part of finish_interval. Coupled urban receivers
        decide their accepted amount after the ramp's merge/head step. Rejected
        traffic remains in that receiver's upstream stock, never a second queue.
        """
        amount = _number(vehicles, 'accepted coupled arrivals')
        if amount > self.current_admission_space()+_MASS_TOLERANCE:
            raise ValueError('Accepted coupled arrivals exceed finite ramp space')
        if amount:
            from evaluation.controllers.sdmpc_prediction_cache import invalidate_ramp
            invalidate_ramp(self)
            if self.head_position_m == 0:
                self._head_ready += amount
            else:
                self._upstream.append((self._arrival(self.time_sec, self.head_position_m), amount))
            self.cumulative_requested_veh += amount
            self.cumulative_admitted_veh += amount
        self._check_conservation()

    def advance_local_interval(self, *, start_sec: float, duration_sec: float,
                               cycle_sec: float, receiving_budget_veh: float,
                               service_veh: float, mode: str,
                               green_sec: float | None,
                               request_arrivals_veh: float,
                               request_arrivals_by_second: Sequence[float] | None = None,
                               allow_partial_cycle: bool = False) -> dict:
        steps = self._local_interval_steps(start_sec=start_sec,duration_sec=duration_sec,
            cycle_sec=cycle_sec,receiving_budget_veh=receiving_budget_veh,service_veh=service_veh,
            mode=mode,green_sec=green_sec,request_arrivals_veh=request_arrivals_veh,
            request_arrivals_by_second=request_arrivals_by_second,allow_partial_cycle=allow_partial_cycle)
        while True:
            try:next(steps)
            except StopIteration as finished:return finished.value

    def _local_interval_steps(self, *, start_sec: float, duration_sec: float,
                              cycle_sec: float, receiving_budget_veh: float,
                              service_veh: float, mode: str, green_sec: float | None,
                              request_arrivals_veh: float,
                              request_arrivals_by_second: Sequence[float] | None = None,
                              allow_partial_cycle: bool = False):
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
        if type(allow_partial_cycle) is not bool:raise ValueError('Partial cycle option must be boolean')
        fractional_one_second = allow_partial_cycle and duration == 1. and not start.is_integer()
        aligned=(cycle%duration==0 and (fractional_one_second or
                 (start%duration==0 and start%cycle+duration<=cycle))
                 if allow_partial_cycle else duration==cycle and start%cycle==0)
        if (start != self.time_sec or (not start.is_integer() and not fractional_one_second)
                or not duration.is_integer() or not aligned):
            raise ValueError("Local interval must be one aligned integral-second meter cycle")
        if mode not in {"OFF", "GREEN", "RED"}:
            raise ValueError("Unknown meter mode")
        if mode == "OFF" and green is not None:
            raise ValueError("OFF must not be relabeled as a green duration")
        if mode == "GREEN" and (green is None or not green.is_integer() or not 0 < green <= cycle):
            raise ValueError("Active meter requires an integral green within its cycle")
        if mode == "RED" and (service != 0 or green not in (None, 0.0)):
            raise ValueError("RED cannot provide service")
        arrival_profile = None
        if request_arrivals_by_second is not None:
            if len(request_arrivals_by_second) != int(duration):
                raise ValueError('Arrival profile must contain every local second')
            arrival_profile = tuple(_number(x,'arrival profile') for x in request_arrivals_by_second)
            if abs(fsum(arrival_profile)-requests) > _MASS_TOLERANCE:
                raise ValueError('Arrival profile must preserve the requested total')
        capacity = (self.length_m-self.head_position_m)*self.lanes/self.spacing_m
        before = self.snapshot()
        local_rows = []
        used = 0.0
        interval_service=0.0
        for second in range(int(duration)):
            # Pause at an idle common clock, before any lane advances. The
            # ordinary single-lane interface consumes these pauses immediately.
            yield start+second
            ready = self.begin_interval(start+second, 1.0)["eligible_merge_veh"]
            accepted = min(ready, budget/duration, max(0.0, budget-used))
            self.commit_merge(accepted)
            used = _sum((used, accepted), "local receiving consumption")
            phase=(start+second)%cycle if allow_partial_cycle else second
            active = mode == "OFF" or (mode == "GREEN" and phase < green)
            local_mode = "OFF" if mode == "OFF" else "GREEN" if active else "RED"
            amount = service/((cycle if allow_partial_cycle else duration) if mode == "OFF" else green) if active else 0.0
            if fractional_one_second and mode == 'GREEN':
                # Preserve native .1s timestamps. Integrate the overlap with
                # [cycle start, cycle start+green), including a cycle wrap.
                # Integer-clock callers retain their exact previous arithmetic.
                overlap = max(0., min(1., green-phase))
                overlap += min(green, max(0., phase+1.-cycle))
                amount = service/green*overlap
                active = overlap > 0.
                local_mode = 'GREEN' if active else 'RED'
            interval_service+=amount
            self.apply_head_service(amount, mode=local_mode,
                green_sec=None if mode == "OFF" else green if active else 0.0,
                posthead_capacity_veh=capacity)
            local_rows.append(self.finish_interval(requests/duration if arrival_profile is None else arrival_profile[second]))
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
            "meter_mode": mode, "green_sec": green, "head_service_limit_veh": interval_service if allow_partial_cycle else service,
            "conservation_residual_veh": after['conservation_residual_veh'],
            "local_step_sec": 1.0, "local_receipts": local_rows,
            "receiving_budget_veh": budget, "unused_receiving_budget_veh": max(0.0,budget-used),
            "receiving_rate_envelope_veh_s": budget/duration,
            "nominal_posthead_storage_veh": capacity, "max_posthead_veh": max(posthead),
            "initial_posthead_excess_veh": max(0.0,posthead[0]-capacity)}


class LaneResolvedRampBoundary(PhysicalRampBoundary):
    """Opt-in independent lane buffers for a physical ramp connector.

    A vacant lane cannot lend head service or storage to a queued lane. This
    assumes no in-connector lane exchange during the forecast; the caller must
    supply causal arrival shares. Merge supply is divided equally by physical
    lane count, not fitted from observed departures. The caller separately bounds
    supply by its explicitly configured receiving-node model.
    Only the existing local one-second interface is supported.
    """

    def __init__(self, *, lane_arrival_shares, lane_exchange_rates_per_sec=None, **kwargs):
        kwargs = dict(kwargs)
        kwargs['initial_cohorts'] = tuple(kwargs.get('initial_cohorts', ()))
        super().__init__(**kwargs)
        if (not isinstance(lane_arrival_shares, (list, tuple))
                or len(lane_arrival_shares) != self.lanes):
            raise ValueError('One explicit arrival share per physical ramp lane is required')
        shares = tuple(_number(x, 'lane arrival share') for x in lane_arrival_shares)
        if abs(fsum(shares)-1.) > _MASS_TOLERANCE:
            raise ValueError('Physical ramp lane arrival shares must sum to one')
        if kwargs.get('initial_backlog_veh', 0.) != 0:
            raise ValueError('Unclassified initial lane backlog is unsupported')
        self.lane_arrival_shares = shares
        self.lane_exchange_rates = None
        if lane_exchange_rates_per_sec is not None:
            rates=lane_exchange_rates_per_sec
            if not isinstance(rates,dict) or set(rates)!={'prehead','posthead'}:
                raise ValueError('Lane exchange requires separate prehead and posthead rates')
            checked={}
            for stage,matrix in rates.items():
                if (not isinstance(matrix,(list,tuple)) or len(matrix)!=self.lanes or
                        any(not isinstance(row,(list,tuple)) or len(row)!=self.lanes for row in matrix)):
                    raise ValueError('Lane exchange matrix must match physical lanes')
                checked[stage]=[[_number(x,'lane exchange rate') for x in row] for row in matrix]
                if any(x and abs(i-j)!=1 for i,row in enumerate(checked[stage]) for j,x in enumerate(row)):
                    raise ValueError('Lane exchange is limited to adjacent physical lanes')
            self.lane_exchange_rates=checked
        self._lane_buffers = []
        for lane in range(1, self.lanes+1):
            spec = dict(kwargs, lanes=1)
            spec['initial_cohorts'] = [(pos, speed, 1) for pos, speed, index
                                       in self.initial_cohorts if index == lane]
            self._lane_buffers.append(PhysicalRampBoundary(**spec))
        if self.lane_exchange_rates is not None:
            for b in self._lane_buffers:b._lane_transfer_in=b._lane_transfer_out=0.

    @staticmethod
    def _aggregate_snapshots(snapshots, connector_id):
        # All nonidentifying snapshot fields are additive inventories/counters.
        first = snapshots[0]
        if any((s['time_sec'], s['phase']) != (first['time_sec'], first['phase'])
               for s in snapshots):
            raise ValueError('Lane buffer clocks/phases differ')
        identity = {'connector_id', 'time_sec', 'phase'}
        return {**{k: first[k] for k in identity}, 'connector_id': connector_id,
                **{k: fsum(s[k] for s in snapshots) for k in first if k not in identity}}

    def snapshot(self):
        if not hasattr(self, '_lane_buffers'):
            return super().snapshot()
        return self._aggregate_snapshots([b.snapshot() for b in self._lane_buffers], self.connector_id)

    def metadata(self):
        result = {**super().metadata(), 'lane_resolution': True,
                'lane_arrival_shares': self.lane_arrival_shares,
                'lane_exchange': 'None; independent lane FIFO inventories',
                'lane_supply': 'Equal shares of canonical aggregate receiving budget'}
        if self.lane_exchange_rates is not None:
            result.update(lane_exchange='Stage-preserving adjacent-lane transfer; remaining cohort ETA unchanged',
                          lane_exchange_rates_per_sec=self.lane_exchange_rates)
        return result

    def _exchange_lanes(self):
        """Apply one second of lateral requests without crossing the head.

        Requests use pre-transfer donor stocks. Each receiving stage uses only
        its pre-transfer room, never room expected from an outgoing transfer.
        Moving cohorts keep their ETA, so a lane change grants no travel time.
        """
        buffers=self._lane_buffers
        if any(b._phase!='idle' or b.time_sec!=buffers[0].time_sec for b in buffers):
            raise ValueError('Lane exchange requires common idle clocks')
        snapshots=[b.snapshot() for b in buffers]
        stages={'prehead':('_upstream','_head_ready',self.head_position_m/self.spacing_m),
                'posthead':('_downstream','_merge_ready',(self.length_m-self.head_position_m)/self.spacing_m)}
        transfers={}
        for stage,(travel,ready,capacity) in stages.items():
            ns=[fsum(n for eta,n in getattr(b,travel))+getattr(b,ready) for b in buffers]
            requests=[]
            for i,row in enumerate(self.lane_exchange_rates[stage]):
                rate=fsum(row);fraction=-expm1(-rate)
                requests.append([ns[i]*fraction*x/rate if rate else 0. for x in row])
            factors=[]
            for j,b in enumerate(buffers):
                incoming=fsum(row[j] for row in requests)
                room=min(max(0.,capacity-ns[j]),max(0.,b.capacity_veh-snapshots[j]['connector_veh']))
                # The other stage cannot consume this stage's room, and total
                # requests across stages share the whole-lane room below.
                factors.append(min(1.,room/incoming) if incoming else 1.)
            transfers[stage]=[[x*factors[j] for j,x in enumerate(row)] for row in requests]
        # Reserve shared whole-lane room once across both stages.
        for j,b in enumerate(buffers):
            incoming=fsum(matrix[i][j] for matrix in transfers.values() for i in range(self.lanes))
            room=max(0.,b.capacity_veh-snapshots[j]['connector_veh'])
            factor=min(1.,room/incoming) if incoming else 1.
            for matrix in transfers.values():
                for row in matrix:row[j]*=factor
        for stage,(travel,ready,capacity) in stages.items():
            cohorts=[list(getattr(b,travel)) for b in buffers];queued=[getattr(b,ready) for b in buffers]
            ns=[fsum(n for eta,n in rows)+q for rows,q in zip(cohorts,queued)]
            matrix=transfers[stage]
            for i,b in enumerate(buffers):
                from evaluation.controllers.sdmpc_prediction_cache import invalidate_ramp
                invalidate_ramp(b)
                outgoing=fsum(matrix[i]);fraction=outgoing/ns[i] if ns[i] else 0.
                setattr(b,travel,[(eta,n*(1.-fraction)) for eta,n in cohorts[i]])
                setattr(b,ready,queued[i]*(1.-fraction))
            for i,b in enumerate(buffers):
                for j,amount in enumerate(matrix[i]):
                    if not amount:continue
                    other=buffers[j];fraction=amount/ns[i]
                    getattr(other,travel).extend((eta,n*fraction) for eta,n in cohorts[i])
                    setattr(other,ready,getattr(other,ready)+queued[i]*fraction)
                    b._lane_transfer_out+=amount;other._lane_transfer_in+=amount
            # Preserve finite cohorts without exponential list growth: equal
            # ETA cohorts share one bin. No time quantization is introduced.
            for b in buffers:
                merged={}
                for eta,n in getattr(b,travel):merged[eta]=merged.get(eta,0.)+n
                setattr(b,travel,[(eta,n) for eta,n in sorted(merged.items()) if n])
        for b in buffers:b._check_conservation()
        return transfers

    def current_admission_space(self):
        # A zero-share lane cannot lend storage to the declared arrival mixture.
        return min((buffer.current_admission_space()/share
                    for buffer, share in zip(self._lane_buffers, self.lane_arrival_shares)
                    if share > 0), default=0.)

    def admit_current(self, vehicles):
        amount = _number(vehicles, 'accepted coupled arrivals')
        if amount > self.current_admission_space()+_MASS_TOLERANCE:
            raise ValueError('Accepted coupled arrivals exceed lane receiving')
        for buffer, share in zip(self._lane_buffers, self.lane_arrival_shares):
            buffer.admit_current(amount*share)
        self.snapshot()

    def begin_interval(self, *args, **kwargs):
        raise ValueError('Lane-resolved ramps require advance_local_interval')

    commit_merge = begin_interval
    apply_head_service = begin_interval
    finish_interval = begin_interval

    def advance_local_interval(self, *, receiving_budget_by_lane_veh=None, request_arrivals_by_lane_second=None, **kwargs):
        if receiving_budget_by_lane_veh is not None:
            if (not isinstance(receiving_budget_by_lane_veh,(list,tuple))
                    or len(receiving_budget_by_lane_veh)!=self.lanes):
                raise ValueError('One receiving budget per physical ramp lane is required')
            budgets=[_number(x,'lane receiving budget') for x in receiving_budget_by_lane_veh]
            if abs(fsum(budgets)-_number(kwargs['receiving_budget_veh'],'receiving budget'))>_MASS_TOLERANCE:
                raise ValueError('Lane receiving budgets must preserve the aggregate budget')
        lane_profiles=None
        if request_arrivals_by_lane_second is not None:
            profile=request_arrivals_by_lane_second
            if (not isinstance(profile,(list,tuple)) or len(profile)!=self.lanes or
                    any(not isinstance(row,(list,tuple)) or len(row)!=kwargs['duration_sec'] for row in profile)):
                raise ValueError('Explicit arrival profile must contain every lane and second')
            lane_profiles=[[_number(x,'lane arrival profile') for x in row] for row in profile]
            if abs(fsum(x for row in lane_profiles for x in row)-_number(kwargs['request_arrivals_veh'],'arrival requests'))>_MASS_TOLERANCE:
                raise ValueError('Lane arrival profiles must preserve total requested arrivals')
            if kwargs.get('request_arrivals_by_second') is not None:
                aggregate=kwargs['request_arrivals_by_second']
                if len(aggregate)!=kwargs['duration_sec'] or any(abs(fsum(row[t] for row in lane_profiles)-_number(x,'arrival profile'))>_MASS_TOLERANCE
                    for t,x in enumerate(aggregate)):
                    raise ValueError('Lane arrival profiles disagree with the total second profile')
        receipts = []
        workers=[]
        for lane, (share, buffer) in enumerate(zip(self.lane_arrival_shares, self._lane_buffers)):
            lane_args = dict(kwargs)
            for key in ('receiving_budget_veh', 'service_veh'):
                lane_args[key] = _number(kwargs[key], key)/self.lanes
            if receiving_budget_by_lane_veh is not None:
                lane_args['receiving_budget_veh']=budgets[lane]
            lane_args['request_arrivals_veh'] = _number(kwargs['request_arrivals_veh'], 'request_arrivals_veh')*share
            if kwargs.get('request_arrivals_by_second') is not None:
                lane_args['request_arrivals_by_second'] = [x*share for x in kwargs['request_arrivals_by_second']]
            if lane_profiles is not None:
                lane_args['request_arrivals_by_second']=lane_profiles[lane]
                lane_args['request_arrivals_veh']=fsum(lane_profiles[lane])
            if self.lane_exchange_rates is None:
                receipts.append(buffer.advance_local_interval(**lane_args))
            else:
                worker=buffer._local_interval_steps(**lane_args)
                workers.append(worker)
        transfers=None
        if workers:
            clock=kwargs['start_sec']
            for worker in workers:
                if next(worker)!=clock:raise ArithmeticError('Lane worker start clocks differ')
            transfers={s:[[0.]*self.lanes for _ in range(self.lanes)] for s in self.lane_exchange_rates}
            for second in range(int(kwargs['duration_sec'])):
                moved=self._exchange_lanes()
                for stage,matrix in moved.items():
                    for i,row in enumerate(matrix):
                        for j,x in enumerate(row):transfers[stage][i][j]+=x
                for worker in workers:
                    try:
                        if next(worker)!=clock+second+1:raise ArithmeticError('Lane worker clocks diverged')
                    except StopIteration as finished:
                        if second!=int(kwargs['duration_sec'])-1:raise ArithmeticError('Lane worker ended early')
                        receipts.append(finished.value)
        def combine(rs):
            first = rs[0]
            same = {'start_sec', 'end_sec', 'duration_sec', 'meter_mode', 'green_sec',
                    'local_step_sec', 'eligible_merge_scope'}
            result = {k:v for k,v in first.items() if k in same}
            for k,v in first.items():
                if k in same or k in ('start','end','local_receipts'):
                    continue
                if not isinstance(v, (int,float)):
                    raise ValueError('Unexpected lane receipt field: '+k)
                result[k] = fsum(r[k] for r in rs)
            for key in ('start','end'):
                result[key] = self._aggregate_snapshots([r[key] for r in rs], self.connector_id)
            return result
        result = combine(receipts)
        result['local_receipts'] = [combine([r['local_receipts'][i] for r in receipts])
                                    for i in range(len(receipts[0]['local_receipts']))]
        result['lane_receipts'] = [{k:v for k,v in r.items() if k!='local_receipts'} for r in receipts]
        result['lane_arrival_shares'] = self.lane_arrival_shares
        if transfers is not None:result['lane_exchange_transfers_veh']=transfers
        self.time_sec = result['end_sec']
        # Public counters are consumed by the rollout residence ledger, not only
        # snapshots. Keep them identical to the sum of the physical lanes.
        for key in ('backlog_veh', 'cumulative_requested_veh', 'cumulative_admitted_veh',
                    'cumulative_head_service_veh', 'cumulative_merge_veh', 'connector_ttt_veh_h'):
            setattr(self, key, fsum(getattr(b, key) for b in self._lane_buffers))
        return result
