"""Canonical owner addresses and ordered finite joint-owner callback solve.

Catalog creation validates the current 17 urban and two freeway owners.
Callbacks provide realized neighbors, physical fingerprints, shared feasibility
and fixed-context costs; this module supplies no model, allocator or runtime
solver dispatch. Its certificate covers only the caller's declared finite game.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import math
from time import monotonic

__all__ = (
    'PHASES', 'LEVER_FIELDS', 'Address', 'Ownership', 'build_ownership',
    'validate_action_addresses', 'assert_owner_transition',
    'Neighborhood', 'Evaluation', 'solve', 'validate_nuf_semantics',
    'RestorationEvaluation', 'restore_feasibility', 'prepare_final_audit_domains',
)


PHASES = ('p1', 'p2', 'p3', 'p4')
LEVER_FIELDS = ('green_times', 'offsets', 'vsl', 'ramp_metering')


@dataclass(frozen=True)
class Address:
    field: str
    key: str
    owner: str
    role: str  # strategy, derived, fixed_dead, fixed_recovery


@dataclass(frozen=True)
class Ownership:
    owners: tuple[str, ...]
    addresses: tuple[Address, ...]
    # (native address namespace, identity, owner, effective action key)
    writes: tuple[tuple[str, str, str, str], ...]


def traversal_owner_order(ownership, traversal):
    """Explicit optional search ordering; ownership and neighborhoods stay fixed."""
    owners = tuple(ownership.owners)
    if traversal in ('sequential', 'round_robin'):
        return owners
    if traversal not in ('round_robin_balanced', 'sequential_balanced'):
        raise ValueError('Unsupported owner traversal')
    urban, freeway = [], []
    for owner in owners:
        fields = {a.field for a in ownership.addresses if a.owner == owner and a.role == 'strategy'}
        if fields and fields <= {'green_times', 'offsets'}:
            urban.append(owner)
        elif fields and fields <= {'vsl', 'ramp_metering'}:
            freeway.append(owner)
        else:
            raise ValueError('Balanced traversal requires urban or freeway lever owners')
    from itertools import zip_longest
    return tuple(owner for pair in zip_longest(freeway, urban) for owner in pair if owner is not None)


def _integer(value, label):
    if type(value) is int and value > 0:
        return value
    if type(value) is str and value.isascii() and value.isdecimal() and int(value) > 0:
        return int(value)
    raise ValueError(f'{label}: expected positive integer identity')


def _address_number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'{label}: expected finite builtin number')
    return value


def build_ownership(cfg, mapping, selected_plan, *, segment_dsd_controls):
    """Derive the current 17 urban + 2 FW owner addresses without mutation.

    The callback must be the actual writer's `_segment_dsd_controls`; this
    module does not copy its by-lane/extra-DSD merge or fallback behavior.
    Current scope requires explicit segment coordinates and zoned 21-cell FW.
    Native object binding is an independent INPX/COM provenance obligation.
    """
    net = cfg.network
    signals = tuple(net.signals)
    freeway = tuple(net.freeway_links)
    if len(signals) != 17 or len(set(signals)) != 17 or set(freeway) != {'FW_E', 'FW_W'} or len(freeway) != 2:
        raise ValueError('Expected 17 distinct urban owners and FW_E/FW_W')
    if any(type(s) is not str or not s.startswith('SC') or str(_integer(s[2:], s)) != s[2:] for s in signals):
        raise ValueError('Urban owner must be canonical SC<number>')
    rows = mapping['signals']
    if len(rows) != 17 or {r['id'] for r in rows} != set(signals):
        raise ValueError('Model and mapped urban owners differ or duplicate')
    addresses, writes, native_seen = [], [], {}

    def claim(kind, identity, owner, key):
        native = (kind, identity)
        if native in native_seen:
            raise ValueError(f'Duplicate native write address {native}: {native_seen[native]} / {owner}')
        native_seen[native] = owner
        writes.append((kind, identity, owner, key))

    urban_scs = set()
    for row in rows:
        signal = row['id']
        sc = _integer(row['sc_no'], signal)
        if signal != f'SC{sc}' or sc in urban_scs:
            raise ValueError('Signal/model controller identity mismatch')
        urban_scs.add(sc)
        plan = selected_plan['controllers'][str(sc)]
        if plan.get('node_id') != signal or _integer(plan.get('sc_no'), signal) != sc or plan.get('major_maps_to') != row.get('major_maps_to'):
            raise ValueError(f'{signal}: selected plan identity/order mismatch')
        groups, greens = plan['phase_signal_groups'], plan['axis_green_sec']
        if set(groups) != set(PHASES) or set(greens) != set(PHASES):
            raise ValueError(f'{signal}: incomplete phase vector')
        live = tuple(p for p in PHASES if groups[p] and _address_number(greens[p], signal) > 0)
        if live != tuple(net.signal_live_phases(signal)):
            raise ValueError(f'{signal}: model/selected plan live phases differ')
        contract = getattr(net, 'signal_actuation_contract', None)
        if not contract or signal not in contract['nodes']:
            raise ValueError(f'{signal}: configured physical signal contract required')
        if any(contract['nodes'][signal].get(k) != plan.get(k) for k in ('major_maps_to', 'phase_segments', 'phase_signal_groups', 'axis_green_sec')):
            raise ValueError(f'{signal}: configured/written selected plans differ')
        for phase in PHASES:
            _address_number(greens[phase], f'{signal}/{phase}')
            addresses.append(Address('green_times', f'{signal}_{phase}', signal, 'strategy' if phase in live else 'fixed_dead'))
        addresses.append(Address('offsets', signal, signal, 'strategy'))
        claim('signal_sc', str(sc), signal, signal)
        # An SG may have several phase windows, all derived from one owner.
        # plan_windows emits live phase_segments only. red_only metadata is
        # not a derived CSV window (and contains native SG9+ in this network).
        sgs = {_integer(window['sg_no'], signal) for p in live for window in plan['phase_segments'][p]}
        if any(not plan['phase_segments'][p] or not
               {_integer(w['sg_no'], signal) for w in plan['phase_segments'][p]}.issubset(
                   {_integer(sg, signal) for sg in groups[p]}) for p in live):
            raise ValueError(f'{signal}: phase-window write identity is outside its phase group')
        if any(sg > 8 for sg in sgs):
            raise ValueError(f'{signal}: selected plan contains a native-only SG')
        for sg in sorted(sgs):
            claim('signal_sg', f'{sc}:{sg}', signal, signal)

    heads_by_link = net.freeway_vsl_zone_heads
    cells_by_link = net.freeway_vsl_zone_head_of_cell
    if tuple(net.freeway_vsl_zone_free) != (0, 1, 2):
        raise ValueError('Expected the three existing free zone indices')
    for link in freeway:
        if tuple(heads_by_link[link]) != (0, 5, 10, 15):
            raise ValueError(f'{link}: unsupported VSL zone heads')
        expected = tuple(5 * min(i // 5, 3) for i in range(21))
        if tuple(cells_by_link[link]) != expected:
            raise ValueError(f'{link}: invalid zone expansion')
        addresses.append(Address('vsl', link, link, 'derived'))
        for i, head in enumerate(expected):
            role = 'fixed_recovery' if head == 15 else ('strategy' if i == head else 'derived')
            addresses.append(Address('vsl', f'{link}__seg{i}', link, role))
    cells, free_sites = set(), set()
    for segment in mapping['segments']:
        link, index = segment.get('model_link'), segment.get('model_segment_index')
        if link not in freeway or type(index) is not int or not 0 <= index < 21 or (link, index) in cells:
            raise ValueError('Unknown/duplicate explicit mapped model segment')
        cells.add((link, index))
        head = cells_by_link[link][index]
        for dsd in segment_dsd_controls(segment):
            no = _integer(dsd['dsd_no'], 'DSD')
            claim('dsd', str(no), link, f'{link}__seg{head}')
            if head != 15:
                free_sites.add((link, head))
    if cells != {(link, i) for link in freeway for i in range(21)}:
        raise ValueError('Mapped segment coverage must be exactly 42 cells')
    if free_sites != {(link, i) for link in freeway for i in (0, 5, 10)}:
        raise ValueError('A free VSL strategy has no mapped native write')

    ramps = dict(net.ramp_to_freeway)
    physical_branches = getattr(net, 'physical_ramp_branches', None)
    per_owner = 4 if physical_branches is not None else 2
    if (physical_branches is not None and
            (physical_branches.get('schema') != 'physical-ramp-branches/v1'
             or set(physical_branches.get('ramps', {})) != set(ramps))):
        raise ValueError('Physical meter owner catalog differs from configured branch model')
    if len(ramps) != 2*per_owner or any(list(ramps.values()).count(link) != per_owner for link in freeway):
        raise ValueError('Expected two model meters per FW owner')
    for ramp, link in ramps.items():
        if type(ramp) is not str or link not in freeway:
            raise ValueError('Unknown model meter owner')
        addresses.append(Address('ramp_metering', ramp, link, 'strategy'))
    meters, connectors, meter_ids, meter_counts = mapping['ramp_meters'], set(), set(), {r: 0 for r in ramps}
    meter_scs = set()
    if len(meters) != 8:
        raise ValueError('Expected eight physical meters')
    for meter in meters:
        ramp = meter['id'] if physical_branches is not None else meter['model_ramp_key']
        if ramp not in ramps or meter['to_model_link'] != ramps[ramp]:
            raise ValueError('Physical meter has unknown/inconsistent FW owner')
        sc, sg = _integer(meter['sc_no'], 'meter SC'), _integer(meter['sg_no'], 'meter SG')
        # ApplyRampMeterSignal addresses SG1, with rampGreen keyed by SC.
        # Distinct declared SGs on one SC are not independent native meters.
        if sg != 1:
            raise ValueError('Meter writer requires sg_no == 1')
        if sc in meter_scs:
            raise ValueError('Meter controller must be unique')
        meter_scs.add(sc)
        connector = _integer(meter['connector'], 'meter connector')
        if sc in urban_scs or connector in connectors or meter['id'] in meter_ids:
            raise ValueError('Urban/meter controller overlap or duplicate physical meter')
        connectors.add(connector); meter_ids.add(meter['id']); meter_counts[ramp] += 1
        claim('signal_sg', f'{sc}:{sg}', ramps[ramp], ramp)
    if set(meter_counts.values()) != ({1} if physical_branches is not None else {2}):
        raise ValueError('Expected two physical meters per model rate')
    return Ownership(signals + freeway, tuple(addresses), tuple(writes))


def _address_field(control, name):
    value = control[name] if isinstance(control, Mapping) else getattr(control, name)
    if not isinstance(value, Mapping):
        raise ValueError(f'{name}: expected mapping')
    return value


def validate_action_addresses(ownership, control):
    """Require an explicit full action, including all 42 expanded VSL cells.

    Callers must realize through canonical routines first. This function does
    not fill missing keys, repair values, or certify physical realizability.
    """
    for field in LEVER_FIELDS:
        values = _address_field(control, field)
        wanted = {a.key for a in ownership.addresses if a.field == field}
        if set(values) != wanted:
            raise ValueError(f'{field}: missing/unknown action addresses: missing={sorted(wanted-set(values))}, unknown={sorted(set(values)-wanted, key=str)}')
        for key, value in values.items():
            _address_number(value, f'{field}/{key}')
    for address in ownership.addresses:
        if address.role == 'fixed_dead' and _address_field(control, address.field)[address.key] != 0:
            raise ValueError(f'{address.key}: dead phase must remain zero')


def assert_owner_transition(ownership, owner, before, after):
    """Check non-owner lever values/key presence and fixed coordinates exactly.

    Owned derived aliases may change along with their owner, but consistency
    with their head/writer is a separate canonical realization obligation.
    Non-lever payload (including diagnostics and leader quantities) is outside
    this address-only API; its frozen-context guard belongs to the game layer.
    """
    if owner not in ownership.owners:
        raise ValueError(f'Unknown owner {owner}')
    validate_action_addresses(ownership, before)
    validate_action_addresses(ownership, after)
    changed = []
    for address in ownership.addresses:
        old, new = _address_field(before, address.field)[address.key], _address_field(after, address.field)[address.key]
        same = type(old) is type(new) and old == new
        if not same:
            if address.owner != owner or address.role.startswith('fixed_'):
                raise ValueError(f'Non-owned/fixed action address changed: {address.field}/{address.key}')
            changed.append((address.field, address.key))
    return tuple(changed)


@dataclass(frozen=True)
class Neighborhood:
    candidates: tuple
    complete: bool
    domain_label: str
    incomplete_reason: str | None = None


@dataclass(frozen=True)
class Evaluation:
    feasible: bool
    cost: float | None
    shared_violation: float
    witness_complete: bool
    reason: str | None = None


@dataclass(frozen=True)
class RestorationEvaluation:
    """Caller-normalized fixed constraint merit, never a mixed-unit raw sum."""
    feasible: bool
    violation: float
    witness_complete: bool
    reason: str | None = None


class _Stop(Exception):
    def __init__(self, kind, message):
        self.kind = kind
        super().__init__(message)


def _number(value, name, *, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (nonnegative and value < 0):
        raise ValueError(name + ' must be a finite builtin number' + (' >= 0' if nonnegative else ''))
    return value


def _field(control, field):
    return control[field] if isinstance(control, Mapping) else getattr(control, field)


def _action_key(ownership, control):
    # Lever values, including derived aliases; physical schedules are separate.
    return tuple((address.field, address.key, type(value).__name__,
                  value.hex() if type(value) is float else value)
                 for address in ownership.addresses
                 for value in (_field(control, address.field)[address.key],))


def validate_nuf_semantics(control, nuf_semantics):
    """Check the explicit action quantity contract without changing its value.

    fixed_target preserves the prepared core's frozen nonlever payload. In
    realized_sum, N_UF_star is the exact final full-vector meter sum; the leader
    target and its budget remain separate immutable caller context values.
    Requested, not-yet-realized meter points need not satisfy this check.
    """
    if nuf_semantics not in ('fixed_target', 'realized_sum'):
        raise ValueError('nuf_semantics must be fixed_target or realized_sum')
    if nuf_semantics == 'fixed_target':
        return
    rates = _field(control, 'ramp_metering')
    if not isinstance(rates, Mapping) or any(type(key) is not str for key in rates):
        raise ValueError('Realized N_UF requires a complete string-keyed meter map')
    total = math.fsum(_number(rates[key], 'realized meter rate', nonnegative=True)
                      for key in sorted(rates))
    _number(total, 'realized meter sum', nonnegative=True)
    actual = _number(_field(control, 'N_UF_star'), 'realized N_UF_star', nonnegative=True)
    if actual != total:
        raise ValueError('N_UF_star differs from the exact realized full meter sum')


def _extra(control, *, nuf_semantics='fixed_target'):
    # Accepted flows are evaluator outputs. Leader targets and other nonlever
    # payload may not be changed by a neighbor; realizer diagnostics may differ.
    fields = control if isinstance(control, Mapping) else vars(control)
    validate_nuf_semantics(control, nuf_semantics)
    return deepcopy({key: value for key, value in fields.items()
                     if key not in LEVER_FIELDS and key != 'diagnostics'
                     and not (nuf_semantics == 'realized_sum' and key == 'N_UF_star')})


def restore_feasibility(ownership, incumbent, context, *, neighbors, evaluate,
                        context_fingerprint, physical_fingerprint,
                        max_sweeps, max_evaluations, time_budget_sec,
                        improvement_tolerance, scope_label, clock=monotonic,
                        nuf_semantics='fixed_target', deadline_check=None, initial_seeds=()):
    """Bounded constraint-merit descent over the same realized owner domains.

    The caller supplies a dimensionless nonnegative merit with fixed scales
    and tolerances in the frozen context. A fully witnessed feasible action
    has merit zero. This helper does not relax targets, change move boxes, or
    use objective costs. Exhaustion establishes no domain-infeasibility claim.
    Only a completely checked feasible action is returned as ``control``.
    """
    owners = tuple(ownership.owners)
    if not owners or len(set(owners)) != len(owners):
        raise ValueError('A complete unique ordered owner catalog is required')
    if type(max_sweeps) is not int or max_sweeps < 1 or type(max_evaluations) is not int or max_evaluations < 0:
        raise ValueError('Explicit max_sweeps >= 1 and max_evaluations >= 0 are required')
    if time_budget_sec is not None:
        _number(time_budget_sec, 'time_budget_sec', nonnegative=True)
    _number(improvement_tolerance, 'improvement_tolerance', nonnegative=True)
    if type(scope_label) is not str or not scope_label.strip():
        raise ValueError('Caller must label the declared restoration scope')
    if deadline_check is not None and not callable(deadline_check):
        raise ValueError('Decision deadline_check must be callable')
    validate_action_addresses(ownership, incumbent)
    validate_nuf_semantics(incumbent, nuf_semantics)
    current = deepcopy(incumbent)
    start = _number(clock(), 'clock')
    token = context_fingerprint(context)
    if type(token) not in (str, bytes) or not token:
        raise ValueError('Context fingerprint must be a nonempty full-value string/bytes')
    count = neighbor_calls = sweeps_started = sweeps_completed = 0
    per_owner = {owner: 0 for owner in owners}
    accepted, cache = [], {}
    current_eval = None
    control = None
    status, error = 'not_started', None

    def checkpoint():
        now = _number(clock(), 'clock')
        if now < start:
            raise _Stop('clock_failure', 'Clock moved before restoration start')
        if context_fingerprint(context) != token:
            raise _Stop('context_changed', 'Frozen restoration context changed')
        if time_budget_sec is not None and now - start >= time_budget_sec:
            raise _Stop('time_budget', 'Restoration time budget reached')
        if deadline_check is not None:
            try:
                deadline_check('feasibility_restoration')
            except TimeoutError as exc:
                raise _Stop('decision_deadline', str(exc)) from exc

    def call(callback, *args):
        checkpoint()
        try:
            value = callback(*args)
        except TimeoutError as exc:
            raise _Stop('decision_deadline', str(exc)) from exc
        except Exception as exc:
            raise _Stop('callback_failure', type(exc).__name__ + ': ' + str(exc)) from exc
        checkpoint()
        return value

    def commands(action):
        trial = deepcopy(action)
        before = (_action_key(ownership, trial), _extra(trial))
        values = call(physical_fingerprint, trial, context)
        validate_action_addresses(ownership, trial)
        if before != (_action_key(ownership, trial), _extra(trial)):
            raise _Stop('callback_mutation', 'Physical fingerprint changed its supplied action')
        if (not isinstance(values, Mapping) or set(values) != set(owners)
                or any(type(values[o]) not in (str, bytes) or not values[o] for o in owners)):
            raise _Stop('callback_contract_failure', 'Physical fingerprints must cover exactly all owners')
        return tuple((o, values[o]) for o in owners)

    def checked(action, owner=None):
        nonlocal count
        validate_action_addresses(ownership, action)
        validate_nuf_semantics(action, nuf_semantics)
        trial = deepcopy(action)
        before = (_action_key(ownership, trial), _extra(trial))
        physical = commands(trial)
        key = (before[0], physical)
        if key in cache:
            checkpoint()
            return cache[key]
        if count >= max_evaluations:
            raise _Stop('evaluation_budget', 'Restoration evaluation budget reached')
        count += 1
        if owner is not None:
            per_owner[owner] += 1
        value = call(evaluate, trial, context)
        validate_action_addresses(ownership, trial)
        validate_nuf_semantics(trial, nuf_semantics)
        if before != (_action_key(ownership, trial), _extra(trial)) or commands(trial) != physical:
            raise _Stop('callback_mutation', 'Restoration evaluator changed its supplied action')
        if (not isinstance(value, RestorationEvaluation) or type(value.feasible) is not bool
                or type(value.witness_complete) is not bool):
            raise _Stop('callback_contract_failure', 'Expected explicit restoration feasibility and witness')
        violation = _number(value.violation, 'normalized restoration violation', nonnegative=True)
        if not value.witness_complete:
            raise _Stop('incomplete_witness', value.reason or 'Restoration witness incomplete')
        if value.feasible != (violation == 0):
            raise _Stop('inconsistent_feasibility', 'Feasibility must agree with zero normalized violation')
        if not value.feasible and (type(value.reason) is not str or not value.reason):
            raise _Stop('callback_contract_failure', 'Infeasible restoration candidates require a reason')
        cache[key] = value
        return value

    try:
        current_eval = checked(current)
        if type(initial_seeds) is not tuple:
            raise ValueError('Explicit finite initializer tuple required')
        for seed in initial_seeds if not current_eval.feasible else ():
            if _extra(seed, nuf_semantics=nuf_semantics) != _extra(incumbent, nuf_semantics=nuf_semantics):
                raise ValueError('Initializer changed fixed targets or nonlever payload')
            value = checked(seed)
            if value.feasible or value.violation < current_eval.violation - improvement_tolerance:
                current, current_eval = deepcopy(seed), value
            if current_eval.feasible:
                break
        if current_eval.feasible:
            control, status = deepcopy(current), 'feasible'
        else:
            for sweep in range(1, max_sweeps + 1):
                sweeps_started = sweep
                changed = False
                for owner in owners:
                    query = deepcopy(current)
                    before = (_action_key(ownership, query), _extra(query))
                    old_physical = commands(query)
                    neighbor_calls += 1
                    domain = call(neighbors, owner, query, context)
                    validate_action_addresses(ownership, query)
                    validate_nuf_semantics(query, nuf_semantics)
                    if before != (_action_key(ownership, query), _extra(query)) or commands(query) != old_physical:
                        raise _Stop('callback_mutation', 'Restoration producer changed its supplied incumbent')
                    if (not isinstance(domain, Neighborhood) or type(domain.candidates) is not tuple
                            or type(domain.complete) is not bool or not domain.domain_label):
                        raise _Stop('callback_contract_failure', 'Expected a materialized restoration neighborhood')
                    if not domain.complete:
                        raise _Stop('incomplete_domain', domain.incomplete_reason or 'Restoration neighborhood incomplete')
                    best, best_eval = current, current_eval
                    for candidate in deepcopy(domain.candidates):
                        checkpoint()
                        validate_action_addresses(ownership, candidate)
                        validate_nuf_semantics(candidate, nuf_semantics)
                        assert_owner_transition(ownership, owner, current, candidate)
                        if _extra(candidate, nuf_semantics=nuf_semantics) != _extra(current, nuf_semantics=nuf_semantics):
                            raise _Stop('callback_mutation', 'Restoration neighbor changed a fixed target or payload')
                        physical = commands(candidate)
                        if any(new != old for new, old in zip(physical, old_physical) if new[0] != owner):
                            raise _Stop('callback_mutation', 'Restoration changed another owner physical command')
                        value = checked(candidate, owner)
                        if value.feasible:
                            control, current, current_eval = deepcopy(candidate), deepcopy(candidate), value
                            status = 'feasible'
                            break
                        if value.violation < best_eval.violation - improvement_tolerance:
                            best, best_eval = deepcopy(candidate), value
                    if control is not None:
                        break
                    if best_eval.violation < current_eval.violation - improvement_tolerance:
                        accepted.append({'sweep': sweep, 'owner': owner,
                            'from_violation': current_eval.violation, 'to_violation': best_eval.violation,
                            'lever_values': _action_key(ownership, best)})
                        current, current_eval, changed = deepcopy(best), best_eval, True
                if control is not None:
                    break
                sweeps_completed = sweep
                if not changed:
                    status = 'restoration_exhausted'
                    break
            else:
                status = 'iteration_limit'
    except _Stop as exc:
        status = exc.kind
        error = {'kind': exc.kind, 'message': str(exc)}
    except Exception as exc:
        status = 'callback_contract_failure'
        error = {'kind': status, 'message': type(exc).__name__ + ': ' + str(exc)}
    return {'control': control, 'feasible': control is not None,
            'best_infeasible': deepcopy(current) if current_eval is not None and not current_eval.feasible else None,
            'final_violation': current_eval.violation if current_eval is not None else None,
            'status': status, 'error': error, 'domain_infeasible': False,
            'scope_label': scope_label, 'context_fingerprint': token.hex() if isinstance(token, bytes) else token,
            'evaluations': count, 'per_owner_evaluations': per_owner,
            'neighbor_calls': neighbor_calls, 'sweeps_started': sweeps_started,
            'sweeps_completed': sweeps_completed, 'accepted_updates': accepted,
            'elapsed_sec': _number(clock(), 'clock') - start,
            'limits': {'max_sweeps': max_sweeps, 'max_evaluations': max_evaluations,
                       'time_budget_sec': time_budget_sec, 'improvement_tolerance': improvement_tolerance},
            'certificate_scope': 'Bounded feasibility search only; no domain-infeasibility or equilibrium certificate'}


def prepare_final_audit_domains(ownership, incumbent, context, *, neighbors,
                               context_fingerprint, physical_fingerprint,
                               nuf_semantics='fixed_target', traversal='sequential',
                               deadline_check=None, reuse_physical_proofs=False,
                               physical_proof_guard=None):
    """Freeze the final finite domains and count the exact score-call budget.

    No payoff/model evaluation occurs here. Every complete realized domain is
    validated using the same action-plus-physical dedupe as solve(). The
    returned callback rejects any other incumbent/context and never regenerates
    a candidate. The full audit must still evaluate every baseline and unique
    neighbor; this inventory alone is not a gap or feasibility certificate.

    Opt-in physical proof reuse stores the exact full serialized candidate,
    never a lever-only/identity key. The caller supplies the same complete
    physical binding guard used by its writer callback. Every reuse checks
    that guard and the full context; unknown actions fail closed.
    """
    import pickle
    if type(reuse_physical_proofs) is not bool:
        raise ValueError('Physical proof reuse requires an explicit boolean')
    if reuse_physical_proofs and not callable(physical_proof_guard):
        raise ValueError('Physical proof reuse requires its original physical binding guard')
    physical_proofs = {}
    packed = lambda action: pickle.dumps(action, protocol=5)
    owners = traversal_owner_order(ownership, traversal)
    validate_action_addresses(ownership, incumbent)
    validate_nuf_semantics(incumbent, nuf_semantics)
    original_key, original_extra = _action_key(ownership, incumbent), _extra(incumbent)
    token = context_fingerprint(context)
    if type(token) not in (str, bytes) or not token:
        raise ValueError('Context fingerprint must be a nonempty full-value string/bytes')

    def checkpoint(query_context):
        if deadline_check is not None:
            deadline_check('joint_final_domain_inventory')
        if context_fingerprint(query_context) != token:
            raise ValueError('Final audit frozen context changed')

    def commands(action, query_context):
        checkpoint(query_context)
        trial = deepcopy(action)
        before = (_action_key(ownership, trial), _extra(trial))
        full_before = packed(trial) if reuse_physical_proofs else None
        values = physical_fingerprint(trial, query_context)
        checkpoint(query_context)
        if (before != (_action_key(ownership, trial), _extra(trial))
                or (reuse_physical_proofs and packed(trial) != full_before)):
            raise ValueError('Final audit physical callback mutated its action')
        if (not isinstance(values, Mapping) or set(values) != set(owners)
                or any(type(values[o]) not in (str, bytes) or not values[o] for o in owners)):
            raise ValueError('Final audit physical fingerprints must cover exactly all owners')
        if reuse_physical_proofs:
            key = packed(action)
            # Traversal order governs evaluation, not the scored mapping's
            # serialization. Preserve the original callback's key order too.
            values_tuple = tuple(values.items())
            if key in physical_proofs and physical_proofs[key] != values_tuple:
                raise ValueError('One full final audit action produced inconsistent physical proofs')
            physical_proofs[key] = values_tuple
        return tuple((o, type(values[o]).__name__, values[o].hex() if type(values[o]) is bytes else values[o])
                     for o in owners)

    fixed_physical = commands(incumbent, context)
    frozen, counts = {}, {}
    for owner in owners:
        checkpoint(context)
        query = deepcopy(incumbent)
        domain = neighbors(owner, query, context)
        checkpoint(context)
        validate_action_addresses(ownership, query)
        validate_nuf_semantics(query, nuf_semantics)
        if ((_action_key(ownership, query), _extra(query)) != (original_key, original_extra)
                or commands(query, context) != fixed_physical):
            raise ValueError('Final audit neighbor callback mutated its incumbent')
        if (not isinstance(domain, Neighborhood) or type(domain.candidates) is not tuple
                or type(domain.complete) is not bool or not domain.complete
                or type(domain.domain_label) is not str or not domain.domain_label):
            raise ValueError('Final audit requires a complete materialized finite domain')
        domain = deepcopy(domain)
        seen = {(original_key, fixed_physical)}
        duplicates = unique = 0
        for candidate in domain.candidates:
            checkpoint(context)
            validate_action_addresses(ownership, candidate)
            validate_nuf_semantics(candidate, nuf_semantics)
            assert_owner_transition(ownership, owner, incumbent, candidate)
            if _extra(candidate, nuf_semantics=nuf_semantics) != _extra(incumbent, nuf_semantics=nuf_semantics):
                raise ValueError('Final audit candidate changed frozen nonlever context')
            physical = commands(candidate, context)
            if any(new != old for new, old in zip(physical, fixed_physical) if new[0] != owner):
                raise ValueError('Final audit candidate changed another owner physical command')
            key = (_action_key(ownership, candidate), physical)
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)
                unique += 1
        frozen[owner] = domain
        counts[owner] = {'announced_candidates': len(domain.candidates),
                         'unique_neighbors': unique, 'duplicate_count': duplicates,
                         'evaluation_budget': 1+unique, 'domain_label': domain.domain_label}
    checkpoint(context)

    def frozen_physical(action, query_context):
        checkpoint(query_context)
        before = packed(action)
        physical_proof_guard(query_context)
        checkpoint(query_context)
        validate_action_addresses(ownership, action)
        validate_nuf_semantics(action, nuf_semantics)
        if packed(action) != before:
            raise ValueError('Final audit physical proof guard mutated its action')
        if before not in physical_proofs:
            raise ValueError('Final audit physical proof is bound to the exact inventoried full action')
        # Values have only immutable str/bytes leaves; this fresh mapping cannot
        # change another read or the retained final command proof.
        return dict(physical_proofs[before])

    def frozen_command_key(action, query_context):
        values = frozen_physical(action, query_context)
        return tuple((o, type(values[o]).__name__, values[o].hex() if type(values[o]) is bytes else values[o])
                     for o in owners)

    def frozen_neighbors(owner, query, query_context):
        checkpoint(query_context)
        validate_action_addresses(ownership, query)
        validate_nuf_semantics(query, nuf_semantics)
        if (owner not in frozen or (_action_key(ownership, query), _extra(query)) != (original_key, original_extra)
                or (frozen_command_key(query, query_context) if reuse_physical_proofs
                    else commands(query, query_context)) != fixed_physical):
            raise ValueError('Prepared final audit is bound to one unchanged final action/context')
        return deepcopy(frozen[owner])

    budget = sum(row['evaluation_budget'] for row in counts.values())
    result = {'neighbors': frozen_neighbors, 'evaluation_budget': budget,
            'proof': {'schema': 'frozen-final-finite-domain-inventory/v1',
                      'owners': owners, 'owner_count': len(owners), 'per_owner': counts,
                      'evaluation_budget': budget,
                      'context_fingerprint': token.hex() if type(token) is bytes else token,
                      'same_incumbent_for_all_owners': True,
                      'dedupe': 'Exact lever addresses plus complete physical command tokens',
                      'payoff_evaluations': 0, 'gap_certified': False}}
    if reuse_physical_proofs:
        result['physical_fingerprint'] = frozen_physical
        result['proof']['physical_proof_reuse'] = {
            'enabled': True, 'exact_full_action_count': len(physical_proofs),
            'retained_key_bytes': sum(map(len, physical_proofs)),
            'original_physical_binding_guard_preserved': True,
            'final_written_command_verification_required': True}
    return result


def solve(ownership, incumbent, context, *, neighbors, evaluate,
          context_fingerprint, physical_fingerprint,
          max_sweeps, max_evaluations, time_budget_sec,
          improvement_tolerance, shared_tolerance, scope_label, clock=monotonic,
          nuf_semantics='fixed_target', traversal='sequential', deadline_check=None,
          before_evaluate=None, final_check_reserve_sec=0., decision_time_remaining_sec=None,
          search_owner_candidate_limit=None, defer_final_audit=False, audit_only=False):
    """Ordered whole-owner best improvements plus a separate final gap audit.

    All work limits and tolerances are explicit caller inputs. `neighbors`
    returns a materialized finite Neighborhood of already realized complete
    actions. `evaluate(owner, action, context)` recomputes candidate-dependent
    accepted traffic and returns the declared local+price+quantity cost, not JΩ.

    nuf_semantics='fixed_target' retains the original frozen action N_UF_star.
    Explicit 'realized_sum' permits only its checked derived full-meter sum to
    change between candidates. N_P_star and every other nonlever payload stay
    fixed; the leader target/budget must remain in the frozen context. Evaluator
    and producer mutation checks still include the supplied action N_UF_star.

    `physical_fingerprint(action, context)` returns exactly the catalog owners
    mapped to nonempty string/bytes tokens of their complete written commands.
    The caller uses canonical rows/schedules and source/plan/mapping context;
    four group rates alone cannot identify eight physical meter schedules.
    Other owners' command tokens must stay fixed. Dedupe uses command tokens
    AND lever values, avoiding an unproven equivalence of price representations.

    Context includes state/forecast/operational state, prices/references/weights,
    trust, dual/quantity mode and physical allocation rule. The caller's full
    value fingerprint must cover all of these, including installed globals.
    The callback must restore query-scoped mutations even when it raises. This
    core detects visible changes and stops; it cannot restore external globals.

    A clock deadline is cooperative: checked before/after callbacks. A callback
    that blocks cannot be preempted here. A late result is not accepted/certified.
    Opt-in round_robin freezes the incumbent throughout each sweep, evaluates
    one unique candidate per owner in turn, then commits the greatest observed
    own-payoff improvement (stable traversal order breaks ties). At a time or
    evaluation stop, only an already completely checked feasible improvement
    may be committed; no late callback result is used. This is a different
    selection algorithm, not simultaneous owner moves or a global optimum.
    Unfinished domains and the final audit remain unknown.
    An exhausted search sweep budget may still have a complete final finite
    certificate if its separately evaluated final gaps meet the declared bound.

    Opt-in sequential_balanced visits each owner at the latest checked
    incumbent. A positive search_owner_candidate_limit bounds only that
    owner's search prefix; an observed feasible improvement may be committed
    before visiting the next owner at the newly realized full action. No
    candidates evaluated at an older incumbent are merged or reused. A capped
    owner domain has an unknown gap; the independent final audit remains full.

    defer_final_audit explicitly leaves all final gaps unknown so a caller can
    rank checked search responses before auditing only the selected action.
    audit_only skips all search and never adopts deviations. The caller can
    supply prepare_final_audit_domains()'s exact budget and frozen callback;
    bounded deadlines still apply and may leave the audit incomplete.
    """
    requested_traversal = traversal
    if type(defer_final_audit) is not bool or type(audit_only) is not bool or (defer_final_audit and audit_only):
        raise ValueError('Boolean defer_final_audit and audit_only are mutually exclusive')
    owners = traversal_owner_order(ownership, traversal)
    if traversal == 'round_robin_balanced':
        traversal = 'round_robin'
    if not owners or len(set(owners)) != len(owners):
        raise ValueError('A complete unique ordered owner catalog is required')
    if any(address.owner not in owners for address in ownership.addresses):
        raise ValueError('Address owner missing from the catalog')
    if len({(a.field, a.key) for a in ownership.addresses}) != len(ownership.addresses):
        raise ValueError('Duplicate action address in owner catalog')
    if any(not any(a.owner == owner and a.role == 'strategy' for a in ownership.addresses) for owner in owners):
        raise ValueError('Every owner requires a strategic address')
    if type(max_sweeps) is not int or max_sweeps < 1 or type(max_evaluations) is not int or max_evaluations < 0:
        raise ValueError('Explicit max_sweeps >= 1 and max_evaluations >= 0 are required')
    if time_budget_sec is not None:
        _number(time_budget_sec, 'time_budget_sec', nonnegative=True)
    _number(improvement_tolerance, 'improvement_tolerance', nonnegative=True)
    _number(shared_tolerance, 'shared_tolerance', nonnegative=True)
    if type(scope_label) is not str or not scope_label.strip():
        raise ValueError('Caller must label the declared finite domain/payoff scope')
    if deadline_check is not None and not callable(deadline_check):
        raise ValueError('Decision deadline_check must be callable')
    if before_evaluate is not None and not callable(before_evaluate):
        raise ValueError('Response preparation must be callable')
    if search_owner_candidate_limit is not None:
        if (type(search_owner_candidate_limit) is not int or search_owner_candidate_limit < 1
                or traversal != 'sequential_balanced'):
            raise ValueError('Positive search_owner_candidate_limit requires sequential_balanced traversal')
    _number(final_check_reserve_sec, 'final_check_reserve_sec', nonnegative=True)
    reserve_envelope = time_budget_sec
    if decision_time_remaining_sec is not None:
        _number(decision_time_remaining_sec, 'decision_time_remaining_sec', nonnegative=True)
        if deadline_check is None:
            raise ValueError('Remaining decision time requires its unchanged absolute deadline check')
        reserve_envelope = (min(reserve_envelope, decision_time_remaining_sec)
                            if reserve_envelope is not None else decision_time_remaining_sec)
    # Preparation/common prices may leave less time than the candidate limit.
    # Only the search cutoff changes; the absolute decision guard still owns
    # its timeout/error and the local candidate deadline remains unchanged.
    search_time = (max(0., reserve_envelope-final_check_reserve_sec)
                   if reserve_envelope is not None and final_check_reserve_sec else None)
    validate_action_addresses(ownership, incumbent)
    validate_nuf_semantics(incumbent, nuf_semantics)
    current = deepcopy(incumbent)
    start = _number(clock(), 'clock')
    token = context_fingerprint(context)
    if type(token) not in (str, bytes) or not token:
        raise ValueError('Context fingerprint must be a nonempty full-value string/bytes')
    evaluation_count = 0
    neighbor_calls = 0
    max_shared_seen = 0.0
    sweeps_started = sweeps_completed = 0
    accepted = []
    error = None
    search_stop = None
    search_status = 'not_started'
    phase = 'search'
    round_robin_best = None
    search_sweeps = []
    final = {owner: {'complete': False, 'gap': None, 'status': 'unvisited', 'evaluations': 0}
             for owner in owners}

    def checkpoint():
        now = _number(clock(), 'clock')
        if now < start:
            raise _Stop('clock_failure', 'Clock moved before solve start')
        if time_budget_sec is not None and now - start >= time_budget_sec:
            raise _Stop('time_budget', 'Deadline reached; remaining gap checks are incomplete')
        if phase == 'search' and search_time is not None and now-start >= search_time:
            raise _Stop('search_time_budget', 'Search reserve boundary reached; final audit remains')
        if context_fingerprint(context) != token:
            raise _Stop('context_changed', 'Frozen game/context fingerprint changed')
        if deadline_check is not None:
            try:
                deadline_check('joint_game')
            except TimeoutError as exc:
                raise _Stop('decision_deadline', str(exc)) from exc

    def call(callback, *args):
        checkpoint()
        try:
            result = callback(*args)
        except TimeoutError as exc:
            raise _Stop('decision_deadline', str(exc)) from exc
        except Exception as exc:
            raise _Stop('callback_failure', type(exc).__name__ + ': ' + str(exc)) from exc
        checkpoint()
        return result

    def command_key(action):
        value = call(physical_fingerprint, deepcopy(action), context)
        if not isinstance(value, Mapping) or set(value) != set(owners):
            raise _Stop('callback_contract_failure', 'Physical fingerprint must cover exactly all owners')
        if any(type(value[owner]) not in (str, bytes) or not value[owner] for owner in owners):
            raise _Stop('callback_contract_failure', 'Every owner needs a nonempty physical command token')
        return tuple((owner, type(value[owner]).__name__,
                      value[owner].hex() if type(value[owner]) is bytes else value[owner])
                     for owner in owners)

    def checked_eval(owner, action, record, base):
        nonlocal evaluation_count, max_shared_seen
        if evaluation_count >= max_evaluations:
            raise _Stop('evaluation_budget', 'Evaluation cap reached; remaining gap checks are incomplete')
        trial = deepcopy(action)
        validate_nuf_semantics(trial, nuf_semantics)
        key, extra = _action_key(ownership, trial), _extra(trial)
        physical = command_key(trial)
        if before_evaluate is not None:
            checkpoint()
            try:
                before_evaluate(owner, deepcopy(base), deepcopy(trial), context, phase,
                                max_evaluations-evaluation_count, checkpoint)
            except _Stop:
                raise
            except TimeoutError as exc:
                raise _Stop('decision_deadline', str(exc)) from exc
            except Exception as exc:
                raise _Stop('callback_failure', type(exc).__name__ + ': ' + str(exc)) from exc
            checkpoint()
        def dispatch():
            nonlocal evaluation_count
            evaluation_count += 1
            record['evaluations'] += 1
            return evaluate(owner, trial, context)
        value = call(dispatch)
        validate_action_addresses(ownership, trial)
        validate_nuf_semantics(trial, nuf_semantics)
        if (_action_key(ownership, trial) != key or _extra(trial) != extra
                or command_key(trial) != physical):
            raise _Stop('callback_mutation', 'Fixed-candidate evaluator changed its supplied action')
        if not isinstance(value, Evaluation) or type(value.feasible) is not bool or type(value.witness_complete) is not bool:
            raise _Stop('callback_failure', 'Evaluation must provide explicit feasibility and witness completion')
        violation = _number(value.shared_violation, 'shared_violation', nonnegative=True)
        max_shared_seen = max(max_shared_seen, violation)
        record['max_shared_violation_seen'] = max(record['max_shared_violation_seen'], violation)
        if not value.witness_complete:
            raise _Stop('incomplete_witness', value.reason or 'Candidate physical/local witness is incomplete')
        if value.feasible:
            _number(value.cost, 'feasible local fixed-price cost')
            if violation > shared_tolerance:
                raise _Stop('inconsistent_feasibility', 'Feasible result exceeds the declared shared tolerance')
        elif type(value.reason) is not str or not value.reason:
            raise _Stop('callback_failure', 'Known infeasible candidates require a reason')
        return value

    def inspect_steps(owner, base, record, candidate_limit=None):
        nonlocal neighbor_calls
        record.update(status='evaluating', gap=None, complete=False, evaluations=0,
                      duplicate_count=0, announced_candidates=None, unique_neighbors=0,
                      feasible_neighbors=0, infeasible_neighbors=0, rejected=[],
                      max_shared_violation_seen=0.0, observed_gap_lower_bound=None)
        if traversal == 'sequential_balanced':
            record.update(search_candidate_limit=candidate_limit,
                          evaluated_lever_families={}, feasible_lever_families={})
        base_eval = checked_eval(owner, base, record, base)
        if not base_eval.feasible:
            raise _Stop('infeasible_incumbent', base_eval.reason or 'Incumbent is infeasible')
        record['incumbent_cost'] = base_eval.cost
        record['incumbent_shared_violation'] = base_eval.shared_violation
        best, best_cost = base, base_eval.cost
        query_base = deepcopy(base)
        before_key, before_extra = _action_key(ownership, query_base), _extra(query_base)
        before_physical = command_key(query_base)
        best_physical = before_physical
        def dispatch():
            nonlocal neighbor_calls
            neighbor_calls += 1
            return neighbors(owner, query_base, context)
        domain = call(dispatch)
        validate_action_addresses(ownership, query_base)
        validate_nuf_semantics(query_base, nuf_semantics)
        if (_action_key(ownership, query_base) != before_key or _extra(query_base) != before_extra
                or command_key(query_base) != before_physical):
            raise _Stop('callback_mutation', 'Neighbor producer changed its supplied incumbent')
        if (not isinstance(domain, Neighborhood) or type(domain.candidates) is not tuple
                or type(domain.complete) is not bool or type(domain.domain_label) is not str or not domain.domain_label):
            raise _Stop('callback_failure', 'Expected a materialized finite Neighborhood with domain label')
        record['domain_label'] = domain.domain_label
        record['announced_candidates'] = len(domain.candidates)
        if not domain.complete:
            raise _Stop('incomplete_domain', domain.incomplete_reason or 'Declared neighbor enumeration incomplete')
        seen = {(before_key, before_physical)}
        for index, candidate in enumerate(deepcopy(domain.candidates)):
            checkpoint()
            validate_action_addresses(ownership, candidate)
            validate_nuf_semantics(candidate, nuf_semantics)
            changed_addresses = assert_owner_transition(ownership, owner, base, candidate)
            if (_extra(candidate, nuf_semantics=nuf_semantics)
                    != _extra(base, nuf_semantics=nuf_semantics)):
                raise _Stop('callback_mutation', 'Neighbor changed a leader target or other nonlever payload')
            physical = command_key(candidate)
            if any(new != old for new, old in zip(physical, before_physical) if new[0] != owner):
                raise _Stop('callback_mutation', 'Neighbor changed another owner physical command')
            key = (_action_key(ownership, candidate), physical)
            if key in seen:
                record['duplicate_count'] += 1
                continue
            if candidate_limit is not None and record['unique_neighbors'] >= candidate_limit:
                record.update(status='owner_candidate_limit', complete=False, gap=None,
                              minimum_observed_feasible_cost=best_cost,
                              minimum_observed_feasible_command_key=best_physical,
                              observed_gap_lower_bound=max(0.0, base_eval.cost-best_cost),
                              first_unvisited_candidate_index=index,
                              remaining_announced_candidates=len(domain.candidates)-index)
                return best
            seen.add(key)
            record['unique_neighbors'] += 1
            result = checked_eval(owner, candidate, record, base)
            if traversal == 'sequential_balanced':
                family = '+'.join(sorted({field for field, _ in changed_addresses}))
                for name in ('evaluated_lever_families',) + (('feasible_lever_families',) if result.feasible else ()):
                    record[name][family] = record[name].get(family, 0) + 1
            if not result.feasible:
                record['infeasible_neighbors'] += 1
                record['rejected'].append({'candidate_index': index, 'reason': result.reason,
                                            'shared_violation': result.shared_violation})
                yield best, best_cost, best_physical
                continue
            record['feasible_neighbors'] += 1
            # Strict minimum; equal costs retain the first candidate. The base
            # is first, so a tie never moves an incumbent.
            if result.cost < best_cost:
                best, best_cost = deepcopy(candidate), result.cost
                best_physical = physical
            record['observed_gap_lower_bound'] = max(0.0, base_eval.cost - best_cost)
            yield best, best_cost, best_physical
        checkpoint()
        record.update(complete=True, status='complete', minimum_feasible_cost=best_cost,
                      minimum_feasible_command_key=best_physical,
                      gap=max(0.0, base_eval.cost - best_cost),
                      observed_gap_lower_bound=max(0.0, base_eval.cost - best_cost),
                      vacuous_no_feasible_nontrivial_neighbor=record['feasible_neighbors'] == 0)
        return best

    def inspect(owner, base, record, candidate_limit=None):
        # Exhaustion preserves the original sequential callback/check order.
        steps = inspect_steps(owner, base, record, candidate_limit)
        while True:
            try:
                next(steps)
            except StopIteration as finished:
                return finished.value

    def commit_round_robin(*, partial):
        nonlocal current
        if round_robin_best is None:
            return False
        chosen = round_robin_best
        current = deepcopy(chosen['control'])
        accepted.append({'sweep': sweeps_started, 'owner': chosen['owner'],
                         'from_cost': chosen['from_cost'], 'to_cost': chosen['to_cost'],
                         'gap': chosen['gap'], 'lever_values': _action_key(ownership, current),
                         'physical_command_key': chosen['physical'],
                         'partial_sweep': partial,
                         'selection_policy': 'Largest completely checked own-payoff improvement at the fixed sweep incumbent'})
        return True

    def audit_final():
        nonlocal phase
        # Every owner uses the same final control; audit never commits a move.
        phase = 'final_check'
        for owner in owners:
            inspect(owner, current, final[owner])
        checkpoint()

    try:
        for sweep in (() if audit_only else range(1, max_sweeps + 1)):
            sweeps_started = sweep
            changed = False
            if traversal == 'round_robin':
                round_robin_best = None
                base = deepcopy(current)
                records = {owner: {'complete': False, 'gap': None, 'status': 'unvisited', 'evaluations': 0}
                           for owner in owners}
                search_sweeps.append({'sweep': sweep, 'owners': records})
                pending = {owner: inspect_steps(owner, base, records[owner]) for owner in owners}
                while pending:
                    for owner in owners:
                        if owner not in pending:
                            continue
                        try:
                            best, best_cost, physical = next(pending[owner])
                        except StopIteration:
                            del pending[owner]
                            continue
                        improvement = records[owner]['incumbent_cost'] - best_cost
                        if (improvement > improvement_tolerance and
                                (round_robin_best is None or improvement > round_robin_best['gap'])):
                            round_robin_best = {'owner': owner, 'control': deepcopy(best),
                                'from_cost': records[owner]['incumbent_cost'], 'to_cost': best_cost,
                                'gap': improvement, 'physical': physical}
                changed = commit_round_robin(partial=False)
            elif traversal == 'sequential_balanced':
                records = {owner: {'complete': False, 'gap': None, 'status': 'unvisited', 'evaluations': 0}
                           for owner in owners}
                search_sweeps.append({'sweep': sweep, 'owners': records,
                    'incumbent_policy': 'Regenerate and check each owner at the latest accepted complete action'})
                for owner in owners:
                    record = records[owner]
                    best = inspect(owner, current, record, search_owner_candidate_limit)
                    improvement = record['observed_gap_lower_bound']
                    if improvement > improvement_tolerance:
                        # inspect() checked this whole action's physical token,
                        # foreign-owner invariance and shared witness. The next
                        # owner must regenerate from this action, never splice
                        # a previously evaluated unilateral move into it.
                        current = deepcopy(best)
                        changed = True
                        accepted.append({'sweep': sweep, 'owner': owner,
                            'from_cost': record['incumbent_cost'],
                            'to_cost': record.get('minimum_feasible_cost', record.get('minimum_observed_feasible_cost')),
                            'gap': improvement, 'lever_values': _action_key(ownership, current),
                            'physical_command_key': record.get('minimum_feasible_command_key', record.get('minimum_observed_feasible_command_key')),
                            'owner_domain_complete': record['complete'],
                            'selection_policy': 'Best checked own-payoff improvement at the latest incumbent'})
            else:
                for owner in owners:
                    record = {}
                    best = inspect(owner, current, record)
                    if record['gap'] > improvement_tolerance:
                        current = deepcopy(best)
                        changed = True
                        accepted.append({'sweep': sweep, 'owner': owner,
                                         'from_cost': record['incumbent_cost'], 'to_cost': record['minimum_feasible_cost'],
                                         'gap': record['gap'], 'lever_values': _action_key(ownership, current),
                                         'physical_command_key': record['minimum_feasible_command_key']})
            sweeps_completed = sweep
            if not changed:
                search_status = ('no_strict_improvement_in_checked_prefixes'
                    if traversal == 'sequential_balanced' and not all(r['complete'] for r in records.values())
                    else 'no_strict_improvement_in_complete_sweep')
                break
        else:
            search_status = 'audit_only' if audit_only else 'iteration_limit'
        # A single unchanged final control/context is used for ALL owners.
        # No final improvement is committed here; positive gaps remain visible.
        if not defer_final_audit:
            audit_final()
    except _Stop as exc:
        error = {'kind': exc.kind, 'phase': phase, 'message': str(exc)}
        if (traversal == 'round_robin' and phase == 'search'
                and exc.kind in ('time_budget', 'evaluation_budget', 'decision_deadline', 'search_time_budget') and round_robin_best is not None):
            # Deadline checks precede context checks. A simultaneous mutation
            # must invalidate earlier improvements too; this guard never scores.
            try:
                if context_fingerprint(context) != token:
                    raise ValueError('Frozen context changed at the work-limit boundary')
                commit_round_robin(partial=True)
            except Exception as guard:
                error = {'kind': 'context_changed', 'phase': phase,
                          'message': type(guard).__name__ + ': ' + str(guard)}
        if exc.kind == 'search_time_budget' and error['kind'] == 'search_time_budget':
            search_stop = error
            search_status = 'interrupted_search_time_budget'
            error = None
            try:
                if not defer_final_audit:
                    audit_final()
            except _Stop as final_exc:
                error = {'kind': final_exc.kind, 'phase': phase, 'message': str(final_exc)}
            except Exception as final_exc:
                error = {'kind': 'callback_contract_failure', 'phase': phase,
                         'message': type(final_exc).__name__ + ': ' + str(final_exc)}
    except Exception as exc:
        # Invalid callback shapes/numbers/ownership are failures, never gap zero.
        error = {'kind': 'callback_contract_failure', 'phase': phase, 'message': type(exc).__name__ + ': ' + str(exc)}
    if error:
        if phase == 'search':
            search_status = 'interrupted_' + error['kind']
            if traversal == 'sequential_balanced' and search_sweeps:
                for record in search_sweeps[-1]['owners'].values():
                    if record['status'] == 'evaluating':
                        record.update(status=error['kind'], gap=None, complete=False)
        for record in final.values():
            if not record['complete']:
                record['gap'] = None
                if record['status'] == 'evaluating':
                    record['status'] = error['kind']
    if defer_final_audit:
        for record in final.values():
            record.update(status='deferred', complete=False, gap=None)
    complete = not defer_final_audit and error is None and all(record['complete'] for record in final.values())
    max_gap = max(record['gap'] for record in final.values()) if complete else None
    elapsed = _number(clock(), 'clock') - start
    result = {'control': deepcopy(current), 'certified': complete and max_gap <= improvement_tolerance,
            'certificate_scope': 'Declared finite realized unilateral joint neighborhoods at one fixed game context; not continuous/global/coalition or price-fixed-point GNE',
            'scope_label': scope_label, 'owners': owners, 'owner_count': len(owners),
            'context_fingerprint': token.hex() if type(token) is bytes else token,
            'final_check_complete': complete, 'per_owner': final, 'maximum_finite_candidate_gap': max_gap,
            'evaluations': evaluation_count, 'neighbor_calls': neighbor_calls,
            'sweeps_started': sweeps_started, 'sweeps_completed': sweeps_completed,
            'search_status': search_status, 'iteration_limit_reached': search_status == 'iteration_limit',
            'time_budget_reached': error is not None and error['kind'] == 'time_budget',
            'evaluation_budget_reached': error is not None and error['kind'] == 'evaluation_budget',
            'decision_deadline_reached': error is not None and error['kind'] == 'decision_deadline',
            'elapsed_sec': elapsed, 'error': error, 'accepted_updates': accepted,
            'max_shared_violation_seen_including_rejected': max_shared_seen,
            'limits': {'max_sweeps': max_sweeps, 'max_evaluations': max_evaluations, 'time_budget_sec': time_budget_sec,
                       'improvement_tolerance': improvement_tolerance, 'shared_tolerance': shared_tolerance},
            'coupling_scalar_residual_is_not_this_certificate': True}
    if traversal == 'round_robin':
        result.update(traversal=requested_traversal, search_sweeps=search_sweeps,
                      partial_domain_gaps_are_unknown=True)
    if traversal == 'sequential_balanced':
        result.update(traversal=requested_traversal, search_sweeps=search_sweeps,
                      partial_domain_gaps_are_unknown=True,
                      search_owner_candidate_limit=search_owner_candidate_limit,
                      sequential_revalidation=True)
    if defer_final_audit:
        result['final_audit_deferred'] = True
    if audit_only:
        result.update(audit_only=True, search_skipped=True,
                      finite_domain_coverage={
                          'complete_owner_count': sum(r['complete'] for r in final.values()),
                          'owner_count': len(owners),
                          'unvisited_neighbors': 0 if complete else None,
                          'full_final_audit_complete': complete})
    if final_check_reserve_sec:
        result['final_check_reserve'] = {'seconds': final_check_reserve_sec,
            'search_time_budget_sec': search_time, 'search_stop': search_stop,
            'same_total_time_budget': True}
        if decision_time_remaining_sec is not None:
            result['final_check_reserve'].update(decision_time_remaining_sec=decision_time_remaining_sec,
                effective_time_budget_sec=reserve_envelope)
    return result
