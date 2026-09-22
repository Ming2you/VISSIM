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


_COPY_MISSING = object()
_COPY_ATOMIC_TYPES = frozenset((type(None), bool, int, float, complex, str, bytes))


def _copy_response_tree(value, memo=None):
    """Copy owned builtin records with the same memo as surrounding deepcopy.

    Exact dict/list records avoid deepcopy's repeated generic dispatch. Every
    mutable container remains independent, including shared/cyclic references.
    Unrecognized objects retain their normal deepcopy hooks and failure modes.
    This helper can be replaced with copy.deepcopy for an unchanged-data A/B.
    """
    if memo is None:
        memo = {}
    identity = id(value)
    prior = memo.get(identity, _COPY_MISSING)
    if prior is not _COPY_MISSING:
        return prior
    kind = type(value)
    if kind in _COPY_ATOMIC_TYPES:
        return value
    if kind is dict:
        result = {}
        memo[identity] = result
        for key, item in value.items():
            # Copy value before key, as deepcopy's dict path. Atomic record
            # fields need the memo lookup but no recursive Python function call.
            copied_item = (memo.get(id(item), item) if type(item) in _COPY_ATOMIC_TYPES
                           else _copy_response_tree(item, memo))
            copied_key = (memo.get(id(key), key) if type(key) in _COPY_ATOMIC_TYPES
                          else _copy_response_tree(key, memo))
            result[copied_key] = copied_item
    elif kind is list:
        result = []
        memo[identity] = result
        for item in value:
            result.append(memo.get(id(item), item) if type(item) in _COPY_ATOMIC_TYPES
                          else _copy_response_tree(item, memo))
    else:
        return copy.deepcopy(value, memo)
    # Match deepcopy's keep-alive rule if a custom child hook mutates its source.
    memo.setdefault(id(memo), []).append(value)
    return result


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
    def __init__(self, stocks: Mapping[str, Mapping[str, float]], *, capture_response=False,
                 indexed_coverage=False, immutable_audit=False, primal_audit=False):
        self.stocks = {str(k): {side: _nonnegative(v.get(side, 0), f"{k}:{side}")
                               for side in ("inside", "outside")} for k, v in stocks.items()}
        self.ttt_veh_h = self.ttd_veh = self.entered_veh = 0.0
        self.flow_counts = Counter()
        self.explicit_events = {}
        self.event_count = 0
        if capture_response:
            self._response = {'transfers': [], 'residence': [], 'freeway_frames': [], 'resource_allocations': []}
            self._response['constraint_coverage'] = []
            self._response['state_bounds'] = []
            self._response['constraint_intervals'] = []
            self._response_clock = None
            if indexed_coverage:
                self._coverage_index = {}
            if immutable_audit:
                self._immutable_audit = True
            if primal_audit:
                self._primal_audit = True

    def __deepcopy__(self, memo):
        if type(self) is not ModelAreaLedger:
            # Subclasses may use slots or custom reconstruction. Preserve the
            # ordinary deepcopy reduction path instead of guessing their state.
            reduced = self.__reduce_ex__(4)
            if isinstance(reduced, str):
                return self
            return copy._reconstruct(self, memo, *reduced)
        result = object.__new__(ModelAreaLedger)
        memo[id(self)] = result
        result.__dict__.update(_copy_response_tree(self.__dict__, memo))
        return result

    @property
    def captures_response(self):
        return hasattr(self, '_response')

    def pack_completed_response_records(self, *, compact=False):
        """Freeze owned append-only audit records after one coupled interval.

        These three lists never feed traffic dynamics or later coverage checks.
        Snapshot copies can share immutable bytes; response() reconstructs all
        original records in order. Active stocks, clocks, coverage, residence
        and freeway operands retain their existing representation and copies.
        Only bytes produced by this ledger are loaded, never external pickle.
        """
        if not self.captures_response:
            return
        import pickle
        keys = ('transfers', 'resource_allocations', 'state_bounds')
        records = {key: self._response[key] for key in keys}
        if not any(records.values()):
            return
        if compact:
            if not getattr(self, '_primal_audit', False):
                raise ValueError('Compact audit requires explicit primal-only validation records')
            from evaluation.controllers.sdmpc_tangent_audit import pack
            payload = pack(records)
        elif getattr(self, '_immutable_audit', False):
            from evaluation.controllers.sdmpc_tangent_records import freeze
            payload = freeze(records)
        else:
            payload = pickle.dumps(records, protocol=5)
        if not hasattr(self, '_packed_response_records'):
            self._packed_response_records = []
        self._packed_response_records.append(payload)
        for key in keys:
            self._response[key] = []

    def record_resource_allocation(self, kind, resource, available_veh, accepted_by_source_veh):
        """Verify the existing allocation against its actual pre-service limit.

        Callers provide accepted amounts at the original allocation site. A
        partial list of these records is not complete network certification.
        """
        if not self.captures_response:
            return
        if not isinstance(kind, str) or not kind or not isinstance(resource, str) or not resource:
            raise ValueError('Resource allocation needs its kind and physical/model identity')
        if not isinstance(accepted_by_source_veh, Mapping) or any(not isinstance(k, str) or not k for k in accepted_by_source_veh):
            raise ValueError('Resource allocation needs named accepted sources')
        # These records certify the realized allocation, never feed the model
        # or its cost/resource Jacobians. Retain every primal check and record.
        if getattr(self, '_primal_audit', False):
            available_veh = getattr(available_veh, '_validation_primal', available_veh)
            accepted_by_source_veh = {k: getattr(v, '_validation_primal', v)
                                     for k, v in accepted_by_source_veh.items()}
        available = _nonnegative(available_veh, 'resource availability')
        accepted = {k: _nonnegative(v, 'accepted resource source ' + k) for k, v in accepted_by_source_veh.items()}
        total = sum(accepted.values())
        record = {**self._response_stamp(), 'kind': kind,
            'resource': resource, 'available_veh': available, 'accepted_by_source_veh': accepted,
            'accepted_total_veh': total, 'exceedance_veh': max(0., total - available)}
        if total > available and not math.isclose(total, available, rel_tol=1e-9, abs_tol=1e-7):
            failure = ValueError('Accepted allocation exceeds shared resource availability: ' + resource)
            failure.resource_allocation = record
            raise failure
        self._response['resource_allocations'].append(record)

    def expect_constraint_coverage(self, scope):
        """Declare an expected allocator visit at the existing nested clock.

        A completed model step or a nonempty resource list cannot substitute
        for a missing visit. This evidence never certifies native plant fidelity.
        """
        if not self.captures_response:
            return
        if not isinstance(scope, str) or not scope:
            raise ValueError('Constraint coverage requires a named allocator')
        stamp = self._response_stamp()
        rows = self._response['constraint_coverage']
        if hasattr(self, '_coverage_index'):
            key = (scope, stamp['stage'], stamp['start_sec'], stamp['end_sec'])
            if key in self._coverage_index:
                raise ValueError('Duplicate constraint coverage expectation: ' + scope)
            row = {**stamp, 'scope': scope, 'expected': True, 'completed': False,
                   'missing_constraints': []}
            rows.append(row)
            self._coverage_index[key] = row
            return
        if any(row['scope'] == scope and all(row[k] == v for k, v in stamp.items()) for row in rows):
            raise ValueError('Duplicate constraint coverage expectation: ' + scope)
        rows.append({**stamp, 'scope': scope, 'expected': True, 'completed': False,
                     'missing_constraints': []})

    def plan_constraint_interval(self, start_sec, tu_sec, tf_sec, k_fu, k_cf, urban_scopes, *, off_ramps=(), physical_ramps=False):
        """Declare the whole nested interval before executing any of its gates."""
        if not self.captures_response:
            return
        start = _nonnegative(start_sec, 'constraint interval start')
        tu, tf = _nonnegative(tu_sec, 'urban duration'), _nonnegative(tf_sec, 'freeway duration')
        if tu <= 0 or tf <= 0 or int(k_fu) != k_fu or int(k_cf) != k_cf or k_fu < 1 or k_cf < 1 or not math.isclose(tu*k_fu, tf, abs_tol=1e-9):
            raise ValueError('Constraint schedule requires the canonical nested clock')
        scopes = list(urban_scopes)
        ramps = list(off_ramps)
        if len(set(ramps)) != len(ramps) or any(not isinstance(r, str) or not r for r in ramps):
            raise ValueError('Landing coverage requires unique configured off-ramp identities')
        if (len(set(scopes)) != len(scopes) or 'urban_allocator' not in scopes or
                set(scopes) - {'urban_allocator', 'shared_approach', 'sc2001_corridor', 'legsplit_allocator',
                    'route_choice_allocator', 'native_route_queue', 'native_prehead_queue',
                    'native_input_generation', 'native_prehead_residual', 'lane_urban_allocator', 'physical_offramp_drain'}):
            raise ValueError('Unknown or incomplete urban constraint scopes')
        intervals = self._response['constraint_intervals']
        if intervals and not math.isclose(start, intervals[-1]['end_sec'], abs_tol=1e-9):
            raise ValueError('Constraint intervals must be contiguous')
        previous_clock = self._response_clock
        try:
            for f in range(int(k_cf)):
                t = start + f*tf
                self.begin_response_step('freeway', t, t+tf)
                for scope in (('physical_ramp_release' if physical_ramps else 'ramp_release_query'), 'freeway_allocator'):
                    self.expect_constraint_coverage(scope)
                self.begin_response_step('landing', t, t+tf)
                self.expect_constraint_coverage('offramp_landing')
                for ramp in ramps:
                    self.expect_constraint_coverage('offramp_landing:' + ramp)
                for u in range(int(k_fu)):
                    self.begin_response_step('urban', t+u*tu, t+(u+1)*tu)
                    for scope in scopes:
                        self.expect_constraint_coverage(scope)
        finally:
            self._response_clock = previous_clock
        intervals.append({'start_sec': start, 'end_sec': start+k_cf*tf,
                          'T_u_sec': tu, 'T_f_sec': tf, 'K_fu': k_fu, 'K_cf': k_cf,
                          'urban_scopes': scopes, 'off_ramps': ramps})

    def record_state_upper_bound(self, kind, resource, value_veh, upper_veh):
        """Record an existing post-projection bound, separately from flows."""
        if not self.captures_response:
            return
        if getattr(self, '_primal_audit', False):
            value_veh = getattr(value_veh, '_validation_primal', value_veh)
            upper_veh = getattr(upper_veh, '_validation_primal', upper_veh)
        value = _nonnegative(value_veh, 'bounded state vehicles')
        upper = _nonnegative(upper_veh, 'existing state upper bound')
        if value > upper and not math.isclose(value, upper, rel_tol=1e-9, abs_tol=1e-7):
            raise ValueError('Existing model state upper bound exceeded: ' + resource)
        self._response['state_bounds'].append({**self._response_stamp(), 'kind': kind,
            'resource': resource, 'value_veh': value, 'upper_veh': upper})

    def complete_constraint_coverage(self, scope, *, missing_constraints=()):
        """Close only the specified visit; omissions remain explicit and false."""
        if not self.captures_response:
            return
        missing = list(missing_constraints)
        if any(not isinstance(x, str) or not x for x in missing) or len(set(missing)) != len(missing):
            raise ValueError('Missing constraints require unique explicit names')
        stamp = self._response_stamp()
        if hasattr(self, '_coverage_index'):
            key = (scope, stamp['stage'], stamp['start_sec'], stamp['end_sec'])
            indexed = self._coverage_index.get(key)
            matches = [] if indexed is None else [indexed]
        else:
            matches = [row for row in self._response['constraint_coverage']
                       if row['scope'] == scope and all(row[k] == v for k, v in stamp.items())]
        if not matches:
            # An isolated unit call is useful evidence, but cannot assert that
            # the complete coupled schedule was declared and covered.
            row = {**stamp, 'scope': scope, 'expected': False, 'completed': False}
            self._response['constraint_coverage'].append(row)
            if hasattr(self, '_coverage_index'):
                self._coverage_index[key] = row
        else:
            row = matches[0]
        if row['completed']:
            raise ValueError('Duplicate constraint coverage completion: ' + scope)
        row.update(completed=True, missing_constraints=missing)

    def record_freeway_operands(self, state, control, actual_ramp_release=None, *, initial=False):
        """Capture existing coupled operands without introducing a model step.

        Initial operands precede the rollout. Frames must follow the existing
        post-T_f landing residence sample. Raw destination bins are preserved;
        the consumer decides their local-cost attribution explicitly.
        """
        if not hasattr(self, '_response'):
            return
        fields = ('N_P_star', 'N_UF_star', 'ramp_metering', 'vsl', 'green_times',
                  'offsets', 'inflow_outflow_allocation')
        row = {'applied_control': {key: copy.deepcopy(getattr(control, key)) for key in fields},
               'model_stock_veh': {key: value['inside'] + value['outside']
                                   for key, value in self.stocks.items()},
               'freeway_density': copy.deepcopy(state.freeway_density),
               'urban_movement_queue': copy.deepcopy(state.urban_movement_queue),
               'shared_approach_state': copy.deepcopy(getattr(state, 'shared_approach_state', None))}
        if hasattr(state, 'offramp_route_inventory_state'):
            row['offramp_route_inventory_state'] = copy.deepcopy(state.offramp_route_inventory_state)
        if initial:
            if 'initial_freeway_operands' in self._response or self._response['freeway_frames']:
                raise ValueError('Initial joint operands must be captured once before frames')
            row['start_sec'] = float(state.time_sec)
            row['stock_cohorts'] = copy.deepcopy(self.stocks)
            self._response['initial_freeway_operands'] = row
            return
        stamp = self._response_stamp()
        if stamp['stage'] != 'landing' or not self._response['residence']:
            raise ValueError('Freeway operands require post-landing residence')
        sample = self._response['residence'][-1]
        if any(sample[key] != stamp[key] for key in ('stage', 'start_sec', 'end_sec')):
            raise ValueError('Freeway operand and residence clocks differ')
        if row['model_stock_veh'] != sample['model_stock_veh']:
            raise ValueError('Freeway stock changed after its residence sample')
        if actual_ramp_release is None:
            raise ValueError('Freeway operands require actual accepted ramp release')
        row.update(stamp)
        row['actual_ramp_release_veh_h'] = copy.deepcopy(actual_ramp_release)
        self._response['freeway_frames'].append(row)

    def begin_response_step(self, stage, start_sec, end_sec):
        """Stamp the existing nested clock; never advance or resample traffic."""
        if not hasattr(self, '_response'):
            return
        start = _nonnegative(start_sec, 'response start seconds')
        end = _nonnegative(end_sec, 'response end seconds')
        if stage not in ('urban', 'freeway', 'landing') or end <= start:
            raise ValueError('invalid response stage/window')
        self._response_clock = {'stage': stage, 'start_sec': start, 'end_sec': end}

    def _response_stamp(self):
        if not hasattr(self, '_response'):
            return None
        if self._response_clock is None:
            raise ValueError('captured model response requires the nested step clock')
        return dict(self._response_clock)

    def response(self):
        """Accepted flows, residence and explicitly scoped model-limit evidence.

        Checked scalar allocations are not a full shared physical certificate.
        Missing allocator visits/operands keep the conditional model witness
        false even when stock closure and the endpoint cost both succeed.
        """
        if not hasattr(self, '_response'):
            raise ValueError('model response capture is not enabled')
        if hasattr(self, '_coverage_index'):
            rows = self._response['constraint_coverage']
            if (len(rows) != len(self._coverage_index) or any(
                    self._coverage_index.get((r['scope'], r['stage'], r['start_sec'], r['end_sec'])) is not r
                    for r in rows)):
                raise ValueError('Constraint coverage index does not match all owned records')
        exported = _copy_response_tree(self._response)
        if getattr(self, '_packed_response_records', None):
            import pickle
            accumulated = {key: [] for key in ('transfers', 'resource_allocations', 'state_bounds')}
            for payload in self._packed_response_records:
                if isinstance(payload, bytes):
                    records = pickle.loads(payload)
                else:
                    from evaluation.controllers.sdmpc_tangent_records import unpack
                    records = unpack(payload)
                for key, rows in records.items():
                    accumulated[key].extend(rows)
            for key, rows in accumulated.items():
                rows.extend(exported[key])
                exported[key] = rows
        coverage = self._response['constraint_coverage']
        missing = sorted({name for row in coverage for name in row['missing_constraints']})
        visits_complete = bool(self._response['constraint_intervals']) and all(row['expected'] and row['completed'] for row in coverage)
        planned_landings = [(row['start_sec'], row['end_sec']) for row in coverage if row['expected'] and row['scope'] == 'offramp_landing']
        actual_landings = [(row['start_sec'], row['end_sec']) for row in self._response['freeway_frames']]
        initial = self._response.get('initial_freeway_operands')
        frames_complete = bool(initial and planned_landings and initial['start_sec'] == planned_landings[0][0] and actual_landings == planned_landings)
        complete = visits_complete and frames_complete
        return {'schema': 'control-area-fixed-response/v1',
                'shared_capacity_certificate': False,
                'conditional_model_feasibility_witness': complete and not missing,
                'physical_native_fidelity_certificate': False,
                'model_constraint_coverage': {
                    'schema': 'implemented-model-constraint-coverage/v1',
                    'claim_scope': 'implemented traffic-transition allocation and post-projection limits; control-domain feasibility is a caller obligation',
                    'expected_visits': sum(row['expected'] for row in coverage),
                    'completed_visits': sum(row['completed'] for row in coverage),
                    'schedule_complete': complete,
                    'complete': complete and not missing,
                    'allocator_visits_complete': visits_complete,
                    'captured_frames_complete': frames_complete,
                    'missing_constraints': missing,
                    'checked_allocation_count': len(exported['resource_allocations']),
                    'checked_state_bound_count': len(exported['state_bounds']),
                    'conditional_model_feasibility_witness': complete and not missing},
                **exported}

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
        stamp = self._response_stamp()
        before_td, before_entered = self.ttd_veh, self.entered_veh
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
        if stamp is not None:
            self._response['transfers'].append({**stamp, 'source': source, 'target': target,
                'route_key': str(route_key or f'{source}->{target}'), 'vehicles': count,
                'ttd_veh': self.ttd_veh - before_td,
                'entered_veh': self.entered_veh - before_entered})

    def residence(self, keys, dt_h, *, event_id=None):
        duration = _nonnegative(dt_h, "residence duration hours")
        keys = tuple(keys)
        if len(keys) != len(set(keys)):
            raise MembershipError("duplicate residence stock key")
        stamp = self._response_stamp()
        if self._duplicate(event_id, ("residence", keys, duration)):
            return
        self.ttt_veh_h += duration * sum(self.stocks.get(k, {}).get("inside", 0.0) for k in keys)
        if stamp is not None:
            self._response['residence'].append({**stamp, 'dt_h': duration,
                'inside_veh': {k: self.stocks.get(k, {}).get('inside', 0.0) for k in keys},
                # Existing local costs use physical queue/storage counts. Keep
                # these separate from the Omega-only residence operands above.
                'model_stock_veh': {k: v['inside'] + v['outside'] for k, v in self.stocks.items()}})

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
    """TTT - beta*exits - gamma*distance, all in veh*h.

    TTD still denotes outward vehicle events, not travel distance (TVD).
    Distance is opt-in: the caller must supply measured/model-accounted TVD
    over its explicitly declared reward domain. The stock ledger alone cannot
    reconstruct it. This scoring option does not enable runtime collection.
    """

    beta_hours: float
    distance_hours_per_km: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "beta_hours", _nonnegative(self.beta_hours, "beta_hours"))
        object.__setattr__(self, "distance_hours_per_km",
                           _nonnegative(self.distance_hours_per_km, "distance_hours_per_km"))

    def score(self, metrics: AreaMetrics, *, nonnegative_cost_veh_h: float = 0.0,
              tvd_veh_km: float | None = None) -> float:
        value = (_nonnegative(metrics.ttt_veh_h, "ttt_veh_h")
                - self.beta_hours * _nonnegative(metrics.ttd_veh, "ttd_veh")
                + _nonnegative(nonnegative_cost_veh_h, "nonnegative_cost_veh_h"))
        if tvd_veh_km is None:
            if self.distance_hours_per_km:
                raise ValueError("Positive distance reward requires explicitly accounted tvd_veh_km")
            return value
        distance = _nonnegative(tvd_veh_km, "tvd_veh_km")
        return value if not self.distance_hours_per_km else value - self.distance_hours_per_km * distance

    def lower_bound(
        self, partial: AreaMetrics, *, max_future_exits_veh: float | None,
        accrued_nonnegative_cost_veh_h: float = 0.0,
        tvd_veh_km: float | None = None, max_future_tvd_veh_km: float | None = None,
    ) -> float:
        """Admissible only if the caller certifies the remaining exit upper bound.

        Future TTT and additional costs must be nonnegative. Without a certified
        exit/distance bound, the corresponding positive reward disables pruning.
        Future-distance bounds must cover the complete remaining control domain.
        """
        value = self.score(partial, nonnegative_cost_veh_h=accrued_nonnegative_cost_veh_h,
                           tvd_veh_km=tvd_veh_km)
        if max_future_exits_veh is None:
            if self.beta_hours:
                return -math.inf
        else:
            value -= self.beta_hours * _nonnegative(max_future_exits_veh, "max_future_exits_veh")
        if max_future_tvd_veh_km is None:
            return -math.inf if self.distance_hours_per_km else value
        return value - self.distance_hours_per_km * _nonnegative(max_future_tvd_veh_km, "max_future_tvd_veh_km")

    def can_prune(
        self, partial: AreaMetrics, *, incumbent_veh_h: float,
        max_future_exits_veh: float | None,
        tvd_veh_km: float | None = None, max_future_tvd_veh_km: float | None = None,
    ) -> bool:
        incumbent = float(incumbent_veh_h)
        if math.isnan(incumbent):
            raise ValueError("incumbent cannot be NaN")
        return self.lower_bound(partial, max_future_exits_veh=max_future_exits_veh,
                                tvd_veh_km=tvd_veh_km, max_future_tvd_veh_km=max_future_tvd_veh_km) > incumbent
