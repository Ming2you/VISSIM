"""Canonical finite urban and held-action freeway owner neighborhoods.

Callers supply the existing domains, installed urban exchange function and
canonical realization/command callbacks. This module supplies no costs,
allocator, rollout or runtime solver dispatch. Incumbents are already realized.
"""
import copy
import hashlib
import json
import math
import pickle
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from contextlib import contextmanager
from functools import lru_cache

from evaluation.controllers import joint_owner_game as addresses
from evaluation.controllers.joint_owner_game import (
    LEVER_FIELDS, assert_owner_transition, validate_action_addresses,
    validate_nuf_semantics,
)
from evaluation.controllers import signal_actuation_contract as signals
from evaluation.controllers import offset_promotion, plant_cycle, action_csv_schema

__all__ = (
    'generate_urban_requests', 'realize_urban_requests',
    'Domain', 'generate', 'owner_physical_fingerprints', 'build_current_freeway_domain',
    'make_joint_neighbor_callbacks',
    'interleave_realized_neighbors',
    'FixedMoveBox', 'build_fixed_move_box',
)


@dataclass(frozen=True)
class FixedMoveBox:
    """One decision's actual-action references; never an incumbent-centered box."""
    entries: tuple  # (field, key, reference, limit, circular period or None)
    anchor_token: str

    def violations(self, action):
        result = []
        for field, key, reference, limit, cycle in self.entries:
            value = float(_number(_field(action, field)[key]))
            delta = value-reference if cycle is None else _circular_delta(value, reference, cycle)
            if abs(delta) > limit + 1e-9:
                result.append({'field': field, 'key': key, 'anchor': reference,
                    'value': value, 'delta': delta, 'limit': limit})
        return tuple(result)

    def validate(self, action):
        violations = self.violations(action)
        if violations:
            raise ValueError('Outside fixed actual-action movement box: ' + repr(violations))
        return {'checked': True, 'anchor_token': self.anchor_token,
                'address_count': len(self.entries), 'violations': ()}


def build_fixed_move_box(ownership, anchor, cfg, limits):
    """Caller supplies existing total-step limits, separately from search steps."""
    from evaluation.controllers import physical_ramp_branches as physical_meters
    physical=physical_meters.enabled(cfg)
    meter_limit='meter_green_sec' if physical else 'meter_veh_h'
    required = {'green_sec', 'offset_sec', 'vsl_kmh', meter_limit}
    if not isinstance(limits, Mapping) or set(limits) != required:
        raise ValueError('Explicit complete decision movement limits required')
    validate_action_addresses(ownership, anchor)
    if physical:
        physical_meters.prepare_control(anchor.copy(),cfg)
        if limits[meter_limit] != cfg.network.physical_ramp_branches['max_green_change_sec']:
            raise ValueError('Physical meter move limit differs from configured green bound')
    for name in required - {'offset_sec'}:
        if _number(limits[name]) < 0:
            raise ValueError('Negative decision movement limit')
    offsets = limits['offset_sec']
    if isinstance(offsets, Mapping):
        if set(offsets) != set(cfg.network.signals):
            raise ValueError('Offset limits must cover every urban owner')
        for value in offsets.values():
            if _number(value) < 0: raise ValueError('Negative offset movement limit')
    elif _number(offsets) < 0:
        raise ValueError('Negative offset movement limit')
    entries = []
    keys = {'green_times': 'green_sec', 'vsl': 'vsl_kmh', 'ramp_metering': 'meter_veh_h'}
    for address in ownership.addresses:
        if physical and address.field=='ramp_metering':
            key='rw_meter_green_'+address.key
            entries.append(('diagnostics',key,float(anchor.diagnostics[key]),float(limits[meter_limit]),None))
            continue
        value = float(_number(_field(anchor, address.field)[address.key]))
        if address.field == 'offsets':
            cycle = float(_number(cfg.network.signal_cycle_length(address.owner)))
            if cycle <= 0: raise ValueError('Positive physical offset cycle required')
            limit = offsets[address.owner] if isinstance(offsets, Mapping) else offsets
        else:
            cycle, limit = None, limits[keys[address.field]]
        if address.role.startswith('fixed_'):
            limit = 0.
        entries.append((address.field, address.key, value, float(limit), cycle))
    anchor_values={f:dict(_field(anchor,f)) for f in LEVER_FIELDS}
    if physical:
        anchor_values['physical_meter_green_sec']={r:anchor.diagnostics['rw_meter_green_'+r] for r in cfg.network.ramps}
    box = FixedMoveBox(tuple(entries), _key(anchor_values))
    box.validate(anchor)
    return box


def interleave_realized_neighbors(ownership, owner, incumbent, neighborhood):
    """Reorder the same realized game candidates, keeping the incumbent first.

    Coupled changes lead, followed by one candidate from each pure lever
    family. A short owner visit can therefore inspect a coupled action without
    first exhausting every green/VSL-only point. Stable source order remains
    inside each family; no candidate, payload, filter or bound changes.
    This is a search policy, not an output-equivalent speed optimization. Price
    basis selection must use the original neighborhood order instead.
    """
    candidates = neighborhood.candidates
    if not candidates or assert_owner_transition(ownership, owner, incumbent, candidates[0]):
        raise ValueError('Expected realized incumbent first')
    pure = ('vsl', 'ramp_metering') if owner in ('FW_E', 'FW_W') else ('green_times', 'offsets')
    families = (frozenset(pure), frozenset(pure[:1]), frozenset(pure[1:]))
    buckets = {family: [] for family in families}
    for candidate in candidates[1:]:
        changed = frozenset(field for field, _ in
                            assert_owner_transition(ownership, owner, incumbent, candidate))
        if changed not in buckets:
            raise ValueError('Realized neighbor is duplicate or outside its owner lever families')
        buckets[changed].append(candidate)
    ordered = [candidates[0]]
    for index in range(max((len(bucket) for bucket in buckets.values()), default=0)):
        for family in families:
            if index < len(buckets[family]):
                ordered.append(buckets[family][index])
    return addresses.Neighborhood(tuple(ordered), neighborhood.complete,
        neighborhood.domain_label + ';search_order=coupled-family-interleave/v1',
        neighborhood.incomplete_reason)


def _urban_number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'{label}: expected finite builtin number')
    return float(value)


def _vector(control, owner):
    return {p: control.green_times[f'{owner}_{p}'] for p in signals.PHASES}


def _scope(cfg, ownership, owner):
    net = cfg.network
    if owner not in ownership.owners or owner not in net.signals:
        raise ValueError(f'{owner}: not an urban owner')
    if not signals.enabled(net):
        raise ValueError('Urban neighbors require the physical signal contract')
    contract = net.signal_actuation_contract
    if contract['offset_writer'] != offset_promotion.WRITER_EXPERIMENT:
        raise ValueError('Current urban neighbor scope requires experiment offset authority')
    live = tuple(net.signal_live_phases(owner))
    node = contract['nodes'][owner]
    planned = tuple(p for p in signals.PHASES if node['phase_signal_groups'][p]
                    and node['axis_green_sec'][p] > 0)
    if planned != live or any(not node['phase_segments'][p] or any(
            (row['start_fraction'], row['end_fraction']) != (0.0, 1.0)
            for row in node['phase_segments'][p]) for p in live):
        raise ValueError('Current neighborhood requires the verified full-phase selected plan')
    owned = {a.key: a.role for a in ownership.addresses
             if a.owner == owner and a.field == 'green_times'}
    wanted = {f'{owner}_{p}': ('strategy' if p in live else 'fixed_dead')
              for p in signals.PHASES}
    if owned != wanted or not any(a.owner == owner and a.field == 'offsets'
                                  and a.key == owner and a.role == 'strategy'
                                  for a in ownership.addresses):
        raise ValueError('Owner catalog and configured phase/offset addresses differ')
    cycle = _urban_number(net.cycle_length, 'offset lattice cycle')
    actual_cycle = _urban_number(net.signal_cycle_length(owner), 'signal cycle')
    lo, hi, total = signals.bounds(net, owner)
    physical_cycle = total + len(live) * (contract['amber'] + contract['all_red'])
    if node.get('native_clock_basis') is not None:
        native = signals.signal_group_plan.node_plan_from_json(node)
        physical_cycle = signals.signal_group_plan.node_cycle_sec(native, native.axis_green_sec,
            contract['amber'], contract['all_red'])
        cycle = actual_cycle
    if cycle <= 0 or abs(cycle - actual_cycle) > 1e-8 or abs(cycle - physical_cycle) > 1e-8:
        raise ValueError('Per-signal cycle differs from current follower offset lattice')
    if abs(cycle - round(cycle, 3)) > 1e-8:
        raise ValueError('Cycle is not on the writer millisecond grid')
    # Value snapshot, never a mutable-object identity cache.
    scope = {'cycle_sec': cycle, 'live': live, 'bounds': (lo, hi, total),
             'refine_bounds': (net.green_min, net.signal_green_max(owner)),
             'node': contract['nodes'][owner],
             'amber': contract['amber'], 'all_red': contract['all_red'],
             'writer': contract['offset_writer']}
    if node.get('native_clock_basis') is not None:
        # The source-compatible minimum may differ by phase (SC16 p2=17s).
        # Preserve those exact bounds in the stale-request/context check.
        scope['phase_bounds'] = signals.phase_bounds(net, owner)
    return copy.deepcopy(scope)


def _circular_delta(value, reference, cycle):
    # Exact current Wu offset candidate/trust convention; half-cycle is -C/2.
    return ((value - reference + cycle / 2.0) % cycle) - cycle / 2.0


def _adds_price_rank(rows, row):
    import numpy as np
    matrix = np.asarray(rows + [row], dtype=float)
    scales = np.linalg.norm(matrix, axis=0)
    return int(np.linalg.matrix_rank(matrix / np.where(scales == 0., 1., scales))) > len(rows)


def generate_urban_requests(follower, owner, incumbent, *, ownership, decision_anchor=None,
                            price_probe=False):
    """Return incumbent + exchange-only + offset-only + their ordered product.

    Uses the INSTALLED pure _phase_exchange_candidates method and its configured
    steps. Offset fractions/reference/trust are the current frozen follower's
    values, not new tuning. No local best-response or price refresh is called.
    Each recall starts from the supplied incumbent; there is no inner descent.
    """
    cfg = follower.cfg
    scope = _scope(cfg, ownership, owner)
    addresses.validate_action_addresses(ownership, incumbent)
    if getattr(follower, 'phase_price_in_gne', False):
        raise ValueError('Anchored in-GNE phase trust is outside this post-refinement domain')
    if not getattr(follower, 'ramp_offset_enabled', False):
        raise ValueError('All urban owners require the existing ramp offset domain')
    if getattr(follower, 'offset_directive', None) is not None:
        raise ValueError('Leader offset directives are outside this owner-local domain')
    exchange = follower._phase_exchange_candidates
    if not getattr(exchange, '_physical_signal_contract', False):
        raise ValueError('Installed physical phase exchange generator is required')
    steps = tuple(_urban_number(x, 'phase exchange step')
                  for x in cfg.mpc.phase_price_exchange_steps_sec)
    fractions = tuple(_urban_number(x, 'offset fraction') for x in follower.offset_fractions)
    if not steps or any(x <= 0 for x in steps) or not fractions:
        raise ValueError('Existing exchange steps and offset fractions must be nonempty')
    base = _vector(incumbent, owner)
    signals.validate_vector(cfg.network, owner, base)
    base_offset = _urban_number(incumbent.offsets[owner], 'incumbent offset')
    if base_offset != signals.written_offset_sec(incumbent, cfg, owner):
        raise ValueError('Incumbent offset must already equal its canonical written value')
    cycle = scope['cycle_sec']
    price = follower.offset_marginal_price
    if price is not None and not isinstance(price, Mapping):
        raise ValueError('Offset price context must be a mapping or None')
    price_active = price is not None and owner in price and not price_probe
    reference = base_offset if decision_anchor is None else float(decision_anchor.offsets[owner]) % cycle
    trust = None
    if price_active:
        _urban_number(price[owner], 'offset price')
        reference = _urban_number(follower.offset_marginal_price_ref.get(owner, 0.0), 'offset price reference') % cycle
        raw_trust = follower.offset_marginal_price_trust_sec
        trust = None if raw_trust is None else _urban_number(raw_trust, 'offset trust')
        if trust is not None and trust < 0:
            raise ValueError('Offset trust must be nonnegative')
    greens, offsets, rejected = [], [], []
    for step_index, step in enumerate(steps):
        for exchange_index, vector in enumerate(exchange(owner, dict(base), step)):
            if set(vector) != set(signals.PHASES):
                raise ValueError('Phase exchange must return an explicit four-phase vector')
            vector = {p: _urban_number(vector[p], p) for p in signals.PHASES}
            signals.validate_vector(cfg.network, owner, vector)
            greens.append((vector, {'step_index': step_index, 'step_sec': step,
                                    'exchange_index': exchange_index}))
    for index, fraction in enumerate(fractions):
        raw = fraction * cycle
        if not math.isfinite(raw):
            raise ValueError('Nonfinite offset lattice point')
        offset = raw % cycle
        item = {'fraction_index': index, 'fraction': fraction, 'grid_raw_sec': raw,
                'trust_delta_sec': _circular_delta(offset, reference, cycle)}
        if trust is not None and abs(item['trust_delta_sec']) > trust + 1e-9:
            rejected.append({'stage': 'requested_offset_trust', **item})
            continue
        # Preserve this explicit source-derived chart, including the -C/2 tie.
        item['signed_lift_sec'] = base_offset + _circular_delta(offset, base_offset, cycle)
        offsets.append((offset, item))

    def request(kind, green, offset, green_origin=None, offset_origin=None):
        return {'kind': kind, 'green': dict(green), 'offset': offset,
                'green_origin': copy.deepcopy(green_origin),
                'offset_origin': copy.deepcopy(offset_origin)}

    requests = [request('incumbent', base, base_offset)]
    requests.extend(request('green', g, base_offset, origin) for g, origin in greens)
    requests.extend(request('offset', base, o, offset_origin=origin) for o, origin in offsets)
    requests.extend(request('joint', g, o, g_origin, o_origin)
                    for g, g_origin in greens for o, o_origin in offsets)
    if price_probe:
        # Put a full requested basis first; retain every other source point as
        # fallback if physical rounding/box checks collapse a selected edge.
        rows, chosen = [], []
        for index, item in enumerate(requests[1:], 1):
            row = [item['green'][p]-base[p] for p in signals.PHASES] + [
                _circular_delta(round(item['offset'], 3), base_offset, cycle)]
            if _adds_price_rank(rows, row):
                rows.append(row); chosen.append(index)
        requests = [requests[0]] + [requests[i] for i in chosen] + [
            item for i, item in enumerate(requests[1:], 1) if i not in chosen]
    return {'schema': 'joint-urban-requests/v1', 'owner': owner, 'scope': scope,
            'base_green': dict(base), 'base_offset': base_offset,
            'offset_reference': reference, 'offset_trust_sec': trust,
            'steps_sec': steps, 'offset_fractions': fractions,
            'requests': tuple(requests), 'rejected': tuple(rejected)}


def _command_key(control, cfg, ownership, owner, plan, sg_rows):
    """Own signal row plus its actual writer-derived SG rows, metadata excluded.

    All other levers/payload stay byte-value unchanged on a private copy. Caller
    must use the same pinned cfg/actuation/plan for scoring and final full CSV.
    This is command identity, not a finite-horizon GREEN-profile equivalence.
    """
    values = _vector(control, owner)
    for p, value in values.items():
        written = plant_cycle.written_axis_green_sec(value) if value > 0 else 0.0
        if value != round(written, 3):
            raise ValueError(f'{owner}/{p}: writer would change candidate green')
    offset = signals.written_offset_sec(control, cfg, owner)
    if offset != control.offsets[owner]:
        raise ValueError('Writer would change realized offset')
    rows = sg_rows(plan, sc_no=int(owner[2:]), phase_greens=dict(values), offset=offset, metadata='')
    expected = {identity for kind, identity, who, _ in ownership.writes
                if kind == 'signal_sg' and who == owner}
    expected_windows = {(str(item['sg_no']), int(item['window_index']))
                        for p in cfg.network.signal_live_phases(owner)
                        for item in plan['controllers'][owner[2:]]['phase_segments'][p]}
    found, result = set(), []
    fields = tuple(f for f in action_csv_schema.ACTION_CSV_FIELDS if f != 'metadata')
    for row in rows:
        sc, sg = row.get('sc_no'), row.get('dsd_no')
        if (type(sc) is not int or type(sg) is not str or not sg.isascii()
                or not sg.isdecimal() or str(int(sg)) != sg or sc != int(owner[2:])
                or row.get('kind') != 'signal_sg'):
            raise ValueError('Derived SG row has an invalid native identity')
        identity = f'{sc}:{sg}'
        if identity in found or (sg, row.get('link')) not in expected_windows:
            raise ValueError('Current full-phase plan requires one window per physical SG')
        found.add(identity)
        physical = tuple(row.get(field, '') for field in fields)
        if any(type(x) not in (str, int, float) or (type(x) in (int, float) and not math.isfinite(x)) for x in physical):
            raise ValueError('Nonfinite/custom value in a physical SG command')
        if row.get('offset') != offset or row.get('green_sec') != round(cfg.network.signal_cycle_length(owner), 6):
            raise ValueError('Derived SG offset/cycle differs from the candidate')
        result.append(physical)
    if found != expected:
        raise ValueError('Derived SG coverage differs from the physical owner catalog')
    return (int(owner[2:]), tuple(values[p] for p in signals.PHASES), offset, tuple(result))


def realize_urban_requests(bundle, incumbent, cfg, *, ownership, selected_plan,
                           actuation, metadata, signal_group_rows, move_box=None, deadline_check=None,
                           price_basis_only=False):
    """Copy/project/write-normalize requests and dedupe actual urban commands.

    signal_group_rows is the canonical adapter.signal_group_action_rows (pure).
    It is passed explicitly to avoid a new adapter import/dispatch layer. This
    helper does not finalize any meter, VSL or shared physical allocation.
    A caller's incumbent must already carry those finalized unchanged values.
    """
    if bundle.get('schema') != 'joint-urban-requests/v1':
        raise ValueError('Unsupported urban request bundle')
    owner = bundle['owner']
    scope = _scope(cfg, ownership, owner)
    if scope != bundle['scope'] or _vector(incumbent, owner) != bundle['base_green'] or incumbent.offsets[owner] != bundle['base_offset']:
        raise ValueError('Stale owner requests: regenerate after a control or domain change')
    settings = actuation.get('real_world_signal_control') or {}
    if settings.get('enabled', True) is not True or metadata.get('suppress_signal_rows', False):
        raise ValueError('Urban command rows are disabled in this writer context')
    if metadata.get('controller_variant') == 'no-control' and settings.get('apply_to_no_control', False) is not True:
        raise ValueError('Native no-control context does not write these urban candidates')
    if settings.get('offset_writer') != scope['writer']:
        raise ValueError('Current scope requires explicit experiment offset writer config')
    if offset_promotion.resolve_writer(actuation, physical_signal_contract=True) != scope['writer']:
        raise ValueError('Actuation and model offset writer authority differ')
    signals.validate_writer(incumbent, cfg, selected_plan, scope['writer'])
    offset_promotion.guard_forced_arm(incumbent, scope['writer'])
    candidates, keys, aliases, key_index = [], [], [], {}
    rejected = list(copy.deepcopy(bundle['rejected']))
    cycle, base_offset = scope['cycle_sec'], bundle['base_offset']
    basis_rows = []
    basis_dimension = len(cfg.network.signal_live_phases(owner))
    for index, request in enumerate(bundle['requests']):
        if deadline_check is not None: deadline_check('urban_candidate_realization')
        candidate = copy.deepcopy(incumbent)
        if set(request['green']) != set(signals.PHASES):
            raise ValueError('Requested green vector is incomplete')
        raw_vector = {p: _urban_number(request['green'][p], p) for p in signals.PHASES}
        vector = signals.project_vector(cfg.network, owner, raw_vector)
        signals.validate_vector(cfg.network, owner, vector)
        candidate.green_times.update({f'{owner}_{p}': vector[p] for p in signals.PHASES})
        candidate.offsets[owner] = _urban_number(request['offset'], 'requested offset')
        candidate.offsets[owner] = signals.written_offset_sec(candidate, cfg, owner)
        if move_box is not None and move_box.violations(candidate):
            rejected.append({'stage': 'written_fixed_decision_box', 'request_index': index,
                             'violations': move_box.violations(candidate)})
            continue
        offset_origin = request['offset_origin']
        alias = copy.deepcopy(request)
        alias['request_index'] = index
        alias['green_displacement_sec'] = {p: vector[p] - bundle['base_green'][p] for p in signals.PHASES}
        if offset_origin is not None:
            trust = bundle['offset_trust_sec']
            written_delta = _circular_delta(candidate.offsets[owner], bundle['offset_reference'], cycle)
            if trust is not None and abs(written_delta) > trust + 1e-9:
                rejected.append({'stage': 'written_offset_trust', 'request_index': index, 'written_delta_sec': written_delta})
                continue
            lift = offset_origin['signed_lift_sec']
            written_lift = candidate.offsets[owner] + cycle * math.floor((lift - candidate.offsets[owner]) / cycle + 0.5)
            if abs(written_lift - lift) > 0.000500001:
                raise ValueError('Offset realization changed more than writer rounding')
            alias['written_lift_sec'] = written_lift
            alias['offset_displacement_sec'] = written_lift - base_offset
        else:
            alias['written_lift_sec'] = base_offset
            alias['offset_displacement_sec'] = 0.0
        addresses.assert_owner_transition(ownership, owner, incumbent, candidate)
        if index == 0 and (vector != bundle['base_green'] or candidate.offsets[owner] != base_offset):
            raise ValueError('Incumbent must not be silently projected')
        price_row = [vector[p]-bundle['base_green'][p] for p in signals.PHASES] + [
            _circular_delta(candidate.offsets[owner], base_offset, cycle)]
        if price_basis_only and index and not _adds_price_rank(basis_rows, price_row):
            continue
        key = _command_key(candidate, cfg, ownership, owner, selected_plan, signal_group_rows)
        if price_basis_only and index and key[-1] == keys[0][-1]:
            continue
        if key in key_index:
            aliases[key_index[key]].append(alias)
        else:
            key_index[key] = len(keys)
            candidates.append(candidate); keys.append(key); aliases.append([alias])
            if price_basis_only and index:
                basis_rows.append(price_row)
                if len(basis_rows) == basis_dimension:
                    break
    if not candidates or not bundle['requests'] or bundle['requests'][0]['kind'] != 'incumbent':
        raise ValueError('Neighborhood requires an explicit first incumbent')
    return {'complete': True, 'domain_label': 'post-refinement-exchanges+x-current-offset-lattice/v1' +
                ('/realized-price-basis' if price_basis_only else ''),
            'incomplete_reason': None, 'owner': owner, 'candidates': tuple(candidates),
            'command_keys': tuple(keys), 'aliases': tuple(tuple(x) for x in aliases),
            'rejected': tuple(rejected), 'requested_count': len(bundle['requests']),
            'physical_candidate_count': len(candidates)}


@dataclass(frozen=True)
class Domain:
    # Values must already have the current branch's step/trust/certification
    # filters. These inputs are rebuilt from one frozen decision context.
    head_values: Mapping[int, tuple[float, ...]]
    meter_points: tuple[tuple[str, Mapping[str, float]], ...]
    # Explicit (head, value, meter-point label) joint probes, in caller order.
    joint_pairs: tuple[tuple[int, float, str], ...]
    held_horizon_sec: float
    budget_mode: str  # none, cap, equality; realized-rate contract, not intent box
    budget_veh_h: float | None
    budget_tolerance_veh_h: float
    provenance: Mapping
    nuf_semantics: str = 'fixed_target'


def _field(action, field):
    return action[field] if isinstance(action, Mapping) else getattr(action, field)


def _number(value):
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError('Expected finite builtin number')
    return value


@lru_cache(maxsize=2048)
def _primitive_mapping_key_json(tagged_value):
    # The type tag prevents Python's True == 1 cache-key alias.
    return json.dumps(tagged_value[1], sort_keys=True)


def _mapping_key_json(value):
    """Reuse only bounded immutable typed keys; preserve default JSON ordering."""
    kind = type(value)
    if (value is None or kind is bool
            or (kind is int and value.bit_length() <= 128)
            or (kind is str and len(value) <= 256)):
        return _primitive_mapping_key_json((kind, value))
    # Float/tuple keys have composite _typed representations. They and large
    # keys retain the original encoder; all key/value validation still runs.
    return json.dumps(value, sort_keys=True)


def _typed(value):
    if value is None or type(value) in (str,bool,int):return value
    if type(value) is float:
        _number(value);return {'float_hex':value.hex()}
    if isinstance(value,Mapping):
        pairs=[[_typed(k),_typed(v)] for k,v in value.items()]
        return {'mapping':sorted(pairs,key=lambda x:_mapping_key_json(x[0]))}
    if isinstance(value,(tuple,list)):return {type(value).__name__:[_typed(v) for v in value]}
    raise ValueError('Unsupported command evidence value')


def _key(value):
    return hashlib.sha256(json.dumps(_typed(value),sort_keys=True,separators=(',',':'),
                          ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def _snapshot_builtin_tree(value):
    """Private immutable value proof, or None for any non-builtin subtree."""
    kind = type(value)
    if value is None or kind is bool or kind is int or kind is str:
        return kind, value
    if kind is float:
        return (kind, value.hex()) if math.isfinite(value) else None
    if kind is dict:
        children = []
        for key, item in value.items():
            left, right = _snapshot_builtin_tree(key), _snapshot_builtin_tree(item)
            if left is None or right is None:
                return None
            children.append((left, right))
        return kind, tuple(children)
    if kind is list or kind is tuple:
        children = tuple(_snapshot_builtin_tree(item) for item in value)
        return None if any(item is None for item in children) else (kind, children)
    return None


def _matches_builtin_snapshot(value, snapshot):
    if snapshot is None or type(value) is not snapshot[0]:
        return False
    kind, saved = snapshot
    if kind is float:
        return value.hex() == saved
    if kind is dict:
        return len(value) == len(saved) and all(
            _matches_builtin_snapshot(key, old_key) and _matches_builtin_snapshot(item, old_item)
            for (key, item), (old_key, old_item) in zip(value.items(), saved))
    if kind is list or kind is tuple:
        return len(value) == len(saved) and all(
            _matches_builtin_snapshot(item, old) for item, old in zip(value, saved))
    return value == saved


def _matches_builtin_serialization(value, serialized):
    """A C-pickle byte match proves a previously checked builtin tree unchanged.

    Protocol opcodes retain exact scalar/container types and float bits.
    Reordering or alias changes may miss and use the existing canonical hash;
    custom reductions cannot silently replace the original builtin encoding.
    Unpickleable values also fall back to that original validation path. No
    deserialization or changed external fingerprint is introduced here.
    """
    if serialized is None:
        return False
    try:
        return pickle.dumps(value, protocol=5) == serialized
    except Exception as exc:
        if isinstance(exc, MemoryError):
            raise
        return False


def owner_physical_fingerprints(ownership, physical_rows):
    """Pure adapter for the joint core's owner -> full command string tokens.

    Caller obtains complete semantic rows from the canonical writer and pins
    horizon/source/plan/mapping in its separate full-value context fingerprint.
    Model lever values are checked separately; two group rates cannot replace
    the eight physical meter schedules in these rows.
    """
    catalog={(kind,identity):owner for kind,identity,owner,key in ownership.writes}
    if len(catalog)!=len(ownership.writes) or not isinstance(physical_rows,Mapping) or set(physical_rows)!=set(catalog):
        raise ValueError('Physical row catalog differs')
    groups={owner:{} for owner in ownership.owners}
    for key,owner in catalog.items():
        if owner not in groups:raise ValueError('Unknown physical owner')
        groups[owner][key]=physical_rows[key]
    if any(not group for group in groups.values()):raise ValueError('Owner lacks physical commands')
    return {owner:_key(group) for owner,group in groups.items()}


def _admitted(callback, control):
    private=deepcopy(control)
    before=_key({field:_field(private,field) for field in LEVER_FIELDS})
    result=callback(private)
    if before!=_key({field:_field(private,field) for field in LEVER_FIELDS}):
        raise ValueError('Admissibility callback mutated control')
    if not isinstance(result,Mapping) or type(result.get('feasible')) is not bool:
        raise ValueError('Admissibility callback must return explicit feasible bool and evidence')
    if not result['feasible'] and not result.get('reason'):
        raise ValueError('Rejected candidate needs an explicit reason')
    return deepcopy(dict(result))


def generate(ownership, cfg, owner, incumbent, domain, *, requested_admissible,
             realize, realized_admissible, physical_rows, deadline_check=None,
             price_basis_dimension=None, meter_actual_reference=None,
             defer_physical_commands=False):
    """Return full actions, request aliases, rejections and an explicit status.

    Every call starts from its already-realized incumbent; no cross-round
    visited set. Re-realizing that first request must preserve every lever and
    native command exactly, or generation fails instead of replacing the base.
    `realize` may mutate only its private copy and must use the frozen canonical
    meter/DSD context. `physical_rows` returns all catalog native identities as
    {(namespace, identity): complete written semantic payload}. It must run the
    canonical row projection, not approximate rate-to-green conversion here.
    Both admissibility callbacks must preserve state/cfg and include the actual
    branch's bounds, trust and certification policy. Realization may change only
    the four lever fields and derived diagnostics; all other action fields are
    preserved exactly. Explicit Domain.nuf_semantics='realized_sum' additionally
    permits N_UF_star to equal the exact final full-meter sum, without changing
    the frozen leader target or domain budget. Closure-owned state/cfg needs a
    caller-side guard. No
    endpoint is called.
    """
    from evaluation.controllers import physical_ramp_branches as physical_meters
    physical = physical_meters.enabled(cfg)
    if type(defer_physical_commands) is not bool or (defer_physical_commands and
            (not physical or price_basis_dimension is not None)):
        raise ValueError('Deferred commands require the exact physical-meter search domain')
    if physical:
        if meter_actual_reference is None:
            raise ValueError('Physical neighbors require the fixed actual meter reference')
        if domain.nuf_semantics != 'fixed_target' or domain.budget_mode != 'none' or domain.budget_veh_h is not None:
            raise ValueError('Physical NUF is predicted merge; service-sum candidate budgets are invalid')
        physical_meters.candidate_from_services(incumbent,meter_actual_reference,cfg,incumbent.ramp_metering)
    if owner not in ('FW_E','FW_W') or owner not in ownership.owners:raise ValueError('Unknown FW owner')
    validate_action_addresses(ownership,incumbent)
    validate_nuf_semantics(incumbent,domain.nuf_semantics)
    heads=tuple(cfg.network.freeway_vsl_zone_heads[owner])
    head_of=tuple(cfg.network.freeway_vsl_zone_head_of_cell[owner])
    if heads!=(0,5,10,15) or head_of!=tuple(5*min(i//5,3) for i in range(21)):
        raise ValueError('Expected canonical21-cell four-zone expansion')
    if any(type(h) is not int for h in domain.head_values) or set(domain.head_values)!={0,5,10}:
        raise ValueError('Only free heads0/5/10 are independent')
    if _number(domain.held_horizon_sec)<=0 or _number(domain.budget_tolerance_veh_h)<0:
        raise ValueError('Invalid caller horizon/tolerance')
    if domain.budget_mode not in ('none','cap','equality'):raise ValueError('Unsupported realized budget mode')
    if domain.budget_mode=='none':
        if domain.budget_veh_h is not None:raise ValueError('Unconstrained mode cannot hide a budget')
    elif domain.budget_veh_h is None or _number(domain.budget_veh_h)<0:raise ValueError('Explicit realized budget required')
    if not domain.provenance:raise ValueError('Effective domain provenance required')
    allowed=tuple(_number(v) for v in cfg.freeway_follower.vsl_set)
    if not allowed:raise ValueError('Empty configured VSL set')
    ramps=tuple(a.key for a in ownership.addresses if a.owner==owner and a.field=='ramp_metering' and a.role=='strategy')
    if len(ramps)!=(4 if physical else 2) or set(ramps)!={r for r,d in cfg.network.ramp_to_freeway.items() if d==owner}:
        raise ValueError('Owner meter catalog differs from configured physical branch count')
    for head,values in domain.head_values.items():
        if not isinstance(values,(tuple,list)) or any(_number(v) not in allowed for v in values):
            raise ValueError('Unconfigured or nonfinite VSL domain')
    meter_points={}
    for label,values in domain.meter_points:
        if type(label) is not str or not label or label in meter_points or set(values)!=set(ramps):
            raise ValueError('Invalid/duplicate full two-meter point')
        if any(_number(v)<0 for v in values.values()):raise ValueError('Negative meter request')
        meter_points[label]=dict(values)
    for head,value,label in domain.joint_pairs:
        if type(head) is not int or head not in domain.head_values or _number(value) not in domain.head_values[head] or label not in meter_points:
            raise ValueError('Joint probe is outside supplied effective domains')
    native={ (kind,identity):who for kind,identity,who,key in ownership.writes }
    fixed={a.key for a in ownership.addresses if a.owner==owner and a.field=='vsl' and a.role=='fixed_recovery'}
    frozen_rows={(kind,identity) for kind,identity,who,key in ownership.writes
                 if who!=owner or (kind=='dsd' and key in fixed)}
    if len(native)!=len(ownership.writes):raise ValueError('Duplicate physical identity')
    def rows(control):
        result=physical_rows(deepcopy(control))
        if not isinstance(result,Mapping) or set(result)!=set(native):raise ValueError('Physical row catalog differs')
        _typed(result)
        return deepcopy(dict(result))
    baseline_rows=rows(incumbent)
    baseline_semantics=_key({field:_field(incumbent,field) for field in LEVER_FIELDS})
    def check_aliases(control):
        vsl=_field(control,'vsl')
        if any(vsl[f'{owner}__seg{i}'] not in allowed for i in range(21)):
            raise ValueError('Realized VSL outside configured set')
        if any(vsl[f'{owner}__seg{i}']!=vsl[f'{owner}__seg{head_of[i]}'] for i in range(21)):
            raise ValueError('Expanded VSL aliases differ from their head')
        if vsl[owner]!=min(vsl[f'{owner}__seg{i}'] for i in range(21)):
            raise ValueError('Direction VSL fallback differs from full vector minimum')
    check_aliases(incumbent)
    requested=[('incumbent',None,None)]
    requested += [(f'vsl:{head}:{i}',(head,value),None) for head in (0,5,10)
                  for i,value in enumerate(domain.head_values[head])]
    requested += [('meter:'+label,None,label) for label in meter_points]
    requested += [(f'joint:{i}',(head,value),label) for i,(head,value,label) in enumerate(domain.joint_pairs)]
    accepted=[];rejected=[];seen={};incumbent_feasible=False
    basis_rows=[]
    for alias,head_point,meter_label in requested:
        if deadline_check is not None: deadline_check('freeway_candidate_realization')
        trial=deepcopy(incumbent)
        if head_point is not None:
            head,value=head_point;vsl=_field(trial,'vsl')
            for i,source in enumerate(head_of):
                if source==head:vsl[f'{owner}__seg{i}']=float(value)
            vsl[owner]=min(vsl[f'{owner}__seg{i}'] for i in range(21))
        if meter_label is not None:
            if physical:
                services={**trial.ramp_metering,**meter_points[meter_label]}
                trial=physical_meters.candidate_from_services(trial,meter_actual_reference,cfg,services)
            else:
                _field(trial,'ramp_metering').update(meter_points[meter_label])
        assert_owner_transition(ownership,owner,incumbent,trial)
        request=deepcopy({field:dict(_field(trial,field)) for field in LEVER_FIELDS})
        requested_evidence=_admitted(requested_admissible,trial)
        if not requested_evidence['feasible']:
            rejected.append({'alias':alias,'stage':'requested','request':request,'evidence':requested_evidence});continue
        action_fields=dict(trial) if isinstance(trial,Mapping) else vars(trial)
        derived_fields=('N_UF_star',) if domain.nuf_semantics=='realized_sum' else ()
        frozen_other=deepcopy({k:v for k,v in action_fields.items() if k not in (*LEVER_FIELDS,'diagnostics',*derived_fields)})
        # A known canonical allocation/budget rejection is an infeasible point,
        # not an incomplete enumeration. Unexpected callback failures propagate.
        from evaluation.controllers.area_meter_finalization import MeterCandidateInfeasible
        try:
            realized=realize(trial)
        except MeterCandidateInfeasible as exc:
            if alias == 'incumbent':
                raise
            rejected.append({'alias':alias,'stage':'canonical_realization',
                             'request':request,'reason':str(exc)})
            continue
        validate_nuf_semantics(realized,domain.nuf_semantics)
        if physical:
            physical_meters.candidate_from_services(realized,meter_actual_reference,cfg,realized.ramp_metering)
        realized_fields=dict(realized) if isinstance(realized,Mapping) else vars(realized)
        if _typed(frozen_other)!=_typed({k:v for k,v in realized_fields.items() if k not in (*LEVER_FIELDS,'diagnostics',*derived_fields)}):
            raise ValueError('Realizer changed non-lever action context')
        assert_owner_transition(ownership,owner,incumbent,realized);check_aliases(realized)
        if any(_field(realized,'ramp_metering')[r]<0 for r in ramps):raise ValueError('Negative realized meter rate')
        semantics=_key({field:_field(realized,field) for field in LEVER_FIELDS})
        command=rows(realized) if alias=='incumbent' else None
        if alias=='incumbent' and (semantics!=baseline_semantics or _typed(command)!=_typed(baseline_rows)):
            raise ValueError('Realizer changed the already-realized incumbent action or physical commands')
        evidence=_admitted(realized_admissible,realized)
        total=sum(_field(realized,'ramp_metering')[r] for r in ramps)
        residual=None if domain.budget_veh_h is None else total-domain.budget_veh_h
        budget_ok=(domain.budget_mode=='none' or
                   (abs(residual)<=domain.budget_tolerance_veh_h if domain.budget_mode=='equality'
                    else residual<=domain.budget_tolerance_veh_h))
        if not evidence['feasible'] or not budget_ok:
            rejected.append({'alias':alias,'stage':'realized','request':request,'evidence':evidence,
                'budget_mode':domain.budget_mode,'budget_residual_veh_h':residual});continue
        price_row = [_field(realized, 'vsl')[f'{owner}__seg{h}']-_field(incumbent, 'vsl')[f'{owner}__seg{h}']
                     for h in (0, 5, 10)] + [_field(realized, 'ramp_metering')[r]-_field(incumbent, 'ramp_metering')[r] for r in ramps]
        if price_basis_dimension is not None and alias != 'incumbent' and not _adds_price_rank(basis_rows, price_row):
            continue
        if command is None and not defer_physical_commands:command=rows(realized)
        if command is not None and any(_typed(command[key])!=_typed(baseline_rows[key]) for key in frozen_rows):
            raise ValueError('Realizer changed a foreign/fixed physical command')
        fingerprint=(_key({'held_horizon_sec':domain.held_horizon_sec,'physical_rows':command})
                     if command is not None else None)
        # Physical-meter services have a checked one-to-one integer-green
        # encoding; VSLs are already exact allowed values with expanded aliases.
        # Equal full modeled vectors therefore deduplicate identically here.
        # Full native rows/foreign-owner checks remain mandatory before any
        # visited candidate is scored. No native proof is fabricated below.
        deduplication_key=semantics if defer_physical_commands else fingerprint
        alias_record={'alias':alias,'request':request,'request_evidence':requested_evidence,
                      'realized_evidence':evidence,
                      'budget_residual_veh_h':residual}
        if deduplication_key in seen:
            previous=accepted[seen[deduplication_key]]
            if previous['modeled_control_sha256']!=semantics:
                raise ValueError('Same physical command has different modeled control; unsafe deduplication')
            previous['aliases'].append(alias_record)
        else:
            seen[deduplication_key]=len(accepted)
            accepted.append({'control':deepcopy(realized),'physical_rows':command,'physical_sha256':fingerprint,
                'owner_physical_sha256':owner_physical_fingerprints(ownership,command) if command is not None else None,
                'modeled_control_sha256':semantics,'aliases':[alias_record],
                'owner_vector':{'vsl_heads':{h:_field(realized,'vsl')[f'{owner}__seg{h}'] for h in heads},
                    'meter_veh_h':{r:_field(realized,'ramp_metering')[r] for r in ramps}}})
            if price_basis_dimension is not None and alias != 'incumbent':
                basis_rows.append(price_row)
                if len(basis_rows) == price_basis_dimension:
                    break
        if alias=='incumbent':incumbent_feasible=True
    return {'status':'feasible_neighbors' if accepted else 'empty_infeasible','owner':owner,
        'held_horizon_sec':domain.held_horizon_sec,'scope':'one full action held throughout horizon; not temporal VSL sequences',
        'incumbent_requested':True,'incumbent_feasible':incumbent_feasible,
        'requested_count':len(requested),'candidates':accepted,'rejected':rejected,
        'domain_provenance':deepcopy(dict(domain.provenance))}



def _current_meter_points(follower, owner, incumbent, leader, previous):
    """Extract existing branch values at one fixed seed, never run _solve_with."""
    import numpy as np

    net, mpc = follower.cfg.network, follower.cfg.mpc
    ramps = [r for r in net.ramps if net.ramp_to_freeway.get(r) == owner]
    if len(ramps) != 2:
        raise ValueError('Current linked freeway domain requires two owned ramps')
    caps = {r: float(_number(net.ramp_capacity_veh_h[r])) for r in ramps}
    if any(cap <= 0 for cap in caps.values()):
        raise ValueError('Positive explicit ramp capacities required')
    fractions = tuple(float(_number(f)) for f in follower.ramp_metering_fractions)
    if not fractions or any(not 0 <= f <= 1 for f in fractions):
        raise ValueError('Explicit current metering fractions required')
    mode = str(mpc.wu_faithful_nuf_coordination_mode)
    if mode not in ('dual', 'cap', 'equality'):
        raise ValueError('Unsupported current N_UF coordination mode')
    nuf = 0.0 if leader is None else float(_number(leader.N_UF_star))
    if nuf < 0:
        raise ValueError('Negative frozen leader N_UF target')
    omega = float(_number(follower._wu._omega_f[owner]))
    if not 0 <= omega <= 1:
        raise ValueError('Invalid frozen directional allocation')
    budget = float(np.clip(omega * nuf, 0.0, sum(caps.values())))
    prices = deepcopy(follower.metering_marginal_price)
    refs = deepcopy(follower.metering_marginal_price_ref)
    trust = follower.metering_marginal_price_trust_frac
    certified = deepcopy(follower.metering_release_certified)
    if prices is not None and not isinstance(prices, Mapping):
        raise ValueError('Explicit current meter price mapping or None required')
    if not isinstance(refs, Mapping):
        raise ValueError('Explicit current meter price reference mapping required')
    if trust is not None and _number(trust) < 0:
        raise ValueError('Negative current meter trust')
    if certified is not None and not isinstance(certified, Mapping):
        raise ValueError('Explicit current release certificate mapping or None required')
    for value in (prices or {}).values():
        _number(value)
    for value in refs.values():
        _number(value)
    lam = float(_number(follower._lambda_UF))
    dual_standing = mode == 'dual' and abs(lam) > 1.0e-12
    split = bool(follower.metering_price_split and prices is not None
                 and leader is not None and nuf > 0.0)
    priced = prices is not None and not split and (
        (leader is not None and nuf > 0.0) or dual_standing)
    budget_off = bool(mpc.leader_budget_off)
    box_on = bool(mpc.baseline_move_box and previous is not None)
    box, box_points = {}, {}
    if box_on:
        for ramp in ramps:
            anchor = min(max(float(_number(_field(previous, 'ramp_metering').get(ramp, caps[ramp]))), 0.0), caps[ramp])
            box[ramp] = (max(0.0, anchor - 300.0), min(caps[ramp], anchor + 300.0))
            box_points[ramp] = sorted({round(min(max(anchor + off, 0.0), caps[ramp]), 6)
                                      for off in (-300.0, -150.0, 0.0, 150.0, 300.0)}, reverse=True)
    def box_ok(ramp, value):
        return not box_on or box[ramp][0] - 1.0e-9 <= value <= box[ramp][1] + 1.0e-9
    def clipped(values):
        return {r: float(np.clip(values[r], 0.0, caps[r])) for r in ramps}
    raw = {r: float(_number(_field(incumbent, 'ramp_metering')[r])) for r in ramps}
    if any(value < 0 for value in raw.values()):
        raise ValueError('Negative incumbent meter')
    def box_seed(seed):
        return {r: min(max(seed[r], box[r][0]), box[r][1]) for r in ramps} if box_on else seed
    points, rejected = [], []
    budget_mode, budget_value = 'none', None
    if priced:
        branch = 'priced_' + mode
        seed = box_seed(clipped(raw))
    elif not budget_off and ((leader is not None and nuf > 0.0) or dual_standing):
        branch = 'leader_' + mode
        if mode == 'dual':
            seed = box_seed(clipped(raw))
        elif mode == 'cap':
            def project(values):
                out = clipped(values)
                total = sum(out.values())
                if total > budget + 1.0e-9 and total > 0.0:
                    out = {r: v * (budget / total) for r, v in out.items()}
                return out
            seed = project(raw)
            budget_mode, budget_value = 'cap', budget
        else:
            r1, r2 = ramps
            lo, hi = max(0.0, budget - caps[r2]), min(caps[r1], budget)
            splits = [lo] if hi - lo <= 1.0e-9 else [float(v) for v in np.linspace(lo, hi, 7)]
            for index, value in enumerate(splits):
                first = float(np.clip(value, 0.0, caps[r1]))
                points.append((f'equality:{index}', {r1: first, r2: float(np.clip(budget - first, 0.0, caps[r2]))}))
            seed = None
            budget_mode, budget_value = 'equality', budget
    else:
        branch = 'pfo_autonomous'
        seed = box_seed(raw)
    if seed is not None:
        points.append(('seed', dict(seed)))
        for ramp in ramps:
            current = seed[ramp]
            if priced:
                values = {0.0, current, min(caps[ramp], budget)}
                values.update(f * caps[ramp] for f in fractions)
                if box_on:
                    values = ({v for v in values if box_ok(ramp, v)} | set(box_points[ramp]) | {current})
                cert_ok = True
                if certified is not None and ramp in (prices or {}):
                    cert_ok = bool(certified.get(ramp, False))
                    if not cert_ok:
                        ref = float(refs.get(ramp, current))
                        kept = {v for v in values if float(np.clip(v, 0.0, caps[ramp])) <= ref + 1.0e-9}
                        if kept:
                            values = kept
                if trust is not None and ramp in (prices or {}):
                    ref = float(refs.get(ramp, current))
                    clipped_vals = sorted({float(np.clip(v, 0.0, caps[ramp])) for v in values})
                    trusted = {v for v in clipped_vals if abs(v - ref) <= float(trust) * caps[ramp] + 1.0e-9}
                    below = [v for v in clipped_vals if v < ref - 1.0e-9]
                    above = [v for v in clipped_vals if v > ref + 1.0e-9]
                    if below:
                        trusted.add(below[-1])
                    if above and cert_ok:
                        trusted.add(above[0])
                    if trusted:
                        values = trusted
                values = sorted(float(np.clip(v, 0.0, caps[ramp])) for v in values)
            else:
                values = box_points[ramp] if box_on else [f * caps[ramp] for f in fractions]
            for index, value in enumerate(values):
                if branch != 'leader_cap' and abs(value - current) <= 1.0e-9:
                    continue
                if branch == 'pfo_autonomous':
                    if (prices is not None and certified is not None and ramp in prices
                            and not certified.get(ramp, False)
                            and value > float(refs.get(ramp, value)) + 1.0e-9):
                        rejected.append((ramp, value, 'release_certificate'))
                        continue
                    if prices is not None and trust is not None and ramp in prices:
                        ref = float(refs.get(ramp, value))
                        if abs(value - ref) > float(trust) * caps[ramp] + 1.0e-9:
                            lattice = sorted(f * caps[ramp] for f in fractions)
                            below = [v for v in lattice if v < ref - 1.0e-9]
                            above = [v for v in lattice if v > ref + 1.0e-9]
                            nearest = set()
                            if below:
                                nearest.add(round(below[-1], 9))
                            if above:
                                nearest.add(round(above[0], 9))
                            if round(value, 9) not in nearest:
                                rejected.append((ramp, value, 'price_trust'))
                                continue
                trial = dict(seed)
                trial[ramp] = value
                if branch == 'leader_cap':
                    trial = project(trial)
                    if all(abs(trial[r] - seed[r]) <= 1.0e-9 for r in ramps):
                        continue
                    if box_on and any(not box_ok(r, trial[r]) for r in ramps):
                        rejected.append((ramp, value, 'projected_baseline_box'))
                        continue
                points.append((f'coordinate:{ramp}:{index}', trial))
    return tuple(points), budget_mode, budget_value, {
        'source': 'WuFaithfulFollower._solve_freeway_agent_metered',
        'branch': branch, 'ramp_order': tuple(ramps), 'capacities_veh_h': caps,
        'fractions': fractions, 'previous_box': box, 'box_points': box_points,
        'leader_present': leader is not None, 'leader_target_nuf_veh_h': nuf,
        'omega_f': omega, 'direction_budget_veh_h': budget, 'lambda_UF': lam,
        'nuf_mode': mode, 'leader_budget_off': budget_off, 'price_split': split,
        'prices': prices, 'references': refs, 'trust_fraction': trust,
        'release_certified': certified, 'seed': seed, 'rejected': tuple(rejected),
        'coordinate_basis': 'fixed branch seed from this incumbent; no prior-coordinate optimum',
        'physical_quantization': 'not performed; caller canonical realizer remains required',
    }


def fixed_meter_coordinate_proofs(cfg, reference, move_box):
    """Prove all-open normalization throughout an actual request box.

    Fresh canonical allocation supplies the exact frozen demand hints. The
    allocator's open branch applies for every r >= open_total-1e-9; its spill
    guard can only increase r. This is an interval proof, not sampled rank.
    """
    import inspect
    from evaluation.controllers import area_meter_finalization as meters
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    context, identity = meters._context(cfg)
    if move_box is None or move_box.anchor_token != _key({f: dict(_field(reference, f)) for f in LEVER_FIELDS}):
        raise ValueError('Fixed meter proof needs the complete actual anchor box')
    move_box.validate(reference)
    if meters.HISTORICAL_REFERENCE in (getattr(reference, 'diagnostics', {}) or {}):
        # The immutable box belongs to the actual prior action. Verify its
        # eight written commands in today's context without reallocating it.
        reference = meters.prepare_held_actual_reference(reference, cfg)
        if move_box.anchor_token != _key({f: dict(_field(reference, f)) for f in LEVER_FIELDS}):
            raise ValueError('Held meter proof reference changed the actual anchor')
        move_box.validate(reference)
    meters.assert_writer(reference, cfg, require_scored=True)
    settings = context['actuation']['real_world_ramp_metering']
    cycle = float(settings['cycle_sec'])
    # The bounded proof deliberately fails to identify unusual configuration
    # variants. Those coordinates must still provide ordinary physical probes.
    max_green = int(round(adapter.clamp(adapter._as_float(settings.get('max_green_sec'), cycle),
        float(int(round(adapter.clamp(adapter._as_float(settings.get('min_green_sec'), 2.), 0., cycle)))), cycle)))
    table = {str(k): float(v) for k, v in (settings.get('per_lane_veh_per_cycle') or adapter.METER_PER_LANE_VEH_PER_CYCLE_DEFAULT).items()}
    lanes = {str(k): float(v) for k, v in (settings.get('meter_lanes') or adapter.METER_LANES_DEFAULT).items()}
    source = {name: hashlib.sha256(inspect.getsource(getattr(adapter, name)).encode()).hexdigest()
              for name in ('_meter_flow_vph', '_measured_meter_allocation',
                           'apply_ramp_spillback_guard', 'real_world_ramp_meter_write_back')}
    bounds = {key: (max(0., value-limit), min(float(cfg.network.ramp_capacity_veh_h[key]), value+limit))
              for field, key, value, limit, _ in move_box.entries if field == 'ramp_metering'}
    trial = deepcopy(reference)
    trial.ramp_metering = {r: bound[0] for r, bound in bounds.items()}
    trial.diagnostics = {k: v for k, v in trial.diagnostics.items()
        if not k.startswith('rw_meter_') and k not in (meters.MARKER, meters.HISTORICAL_REFERENCE, meters.HELD_ACTUAL_REFERENCE)}
    meters.finalize(trial, cfg)
    physical = adapter.real_world_ramp_meter_actions(deepcopy(reference), cfg, context['actuation'], context['mapping'])
    proofs = {}
    for ramp, (lower, upper) in bounds.items():
        group = [m for m in context['mapping']['ramp_meters'] if m['model_ramp_key'] == ramp]
        operands = [{'id': m['id'], 'demand_veh_h': float(trial.diagnostics['rw_meter_demand_'+m['id']]),
                     'open_table_veh_h': adapter._meter_flow_vph(lanes.get(m['id'], 1.), max_green, table, cycle)} for m in group]
        open_total = sum(min(row['demand_veh_h'], row['open_table_veh_h']) for row in operands)
        cap = float(cfg.network.ramp_capacity_veh_h[ramp])
        if (max_green == cycle and group and lower <= upper and lower >= open_total-1e-9
                and _field(reference, 'ramp_metering')[ramp] == cap
                and all(physical[m['id']]['green_sec'] == cycle for m in group)):
            proofs[ramp] = {'request_interval_veh_h': [lower, upper], 'open_total_veh_h': open_total,
                'open_branch_tolerance_veh_h': 1e-9, 'fixed_rate_veh_h': cap, 'operands': operands,
                'physical_green_sec': {m['id']: physical[m['id']]['green_sec'] for m in group},
                'proof': 'Every request in the fixed box takes the measured-table all-open branch; canonical normalization equals configured cap',
                'price_convention': 'zero representative on a fixed coordinate, not an identified derivative'}
    return {'schema': 'fixed-meter-open-box/v1', 'context_sha256': identity,
            'allocator_sources_sha256': source, 'anchor_token': move_box.anchor_token,
            'move_box_entries': [list(entry) for entry in move_box.entries], 'meters': proofs}


def validate_fixed_meter_coordinate_proofs(cfg, reference, proof, *, move_box=None):
    if not isinstance(proof, dict) or proof.get('schema') != 'fixed-meter-open-box/v1':
        raise ValueError('Explicit fixed meter interval proof required')
    declared = FixedMoveBox(tuple(tuple(row) for row in proof['move_box_entries']), proof['anchor_token'])
    if move_box is not None and declared != move_box:
        raise ValueError('Fixed meter proof and active decision box differ')
    if fixed_meter_coordinate_proofs(cfg, reference, declared) != proof:
        raise ValueError('Fixed meter interval proof differs from current source/context/anchor')
    return {r: row['fixed_rate_veh_h'] for r, row in proof['meters'].items()}


def _physical_meter_points(follower, owner, incumbent, actual_reference):
    """Each SG's realizable green lattice in the same fixed actual +/-2s box.

    Model coordinates are service ceilings. Only the coupled response can
    constrain predicted accepted merge flow against the frozen N_UF target.
    """
    from evaluation.controllers import physical_ramp_branches as physical_meters
    cfg=follower.cfg
    checked=physical_meters.candidate_from_services(incumbent,actual_reference,cfg,incumbent.ramp_metering)
    spec=cfg.network.physical_ramp_branches
    ramps=tuple(r for r in cfg.network.ramps if cfg.network.ramp_to_freeway[r]==owner)
    if owner not in ('FW_E','FW_W') or len(ramps)!=4:
        raise ValueError('Physical meter domain requires four owned branches')
    raw={r:checked.ramp_metering[r] for r in ramps}
    points=[('physical_seed',dict(raw))]
    actual={r:actual_reference.diagnostics['rw_meter_green_'+r] for r in spec['ramps']}
    for mid in ramps:
        table=spec['ramps'][mid]['service_by_green_veh_h']
        for green in sorted((int(g) for g in table),reverse=True):
            if abs(green-actual[mid])<=spec['max_green_change_sec'] and table[str(green)]!=raw[mid]:
                points.append((f'physical:{mid}:g{green}',{**raw,mid:table[str(green)]}))
    return tuple(points),'none',None,{
        'source':'physical eight-SG green lattice at the fixed actual-action anchor',
        'actual_green_sec':actual,'max_green_change_sec':spec['max_green_change_sec'],
        'candidate_nuf_constraint_applied':False,'nuf_evaluation':'coupled predicted accepted merge',
        'meter_coordinate_unit':'service ceiling veh/h; uniquely decoded to green seconds'}


def _independent_meter_points(follower, owner, incumbent, anchor, move_box, fixed_rates=None):
    """Price probes have physical bounds, not a candidate leader's equality."""
    ramps = tuple(r for r in follower.cfg.network.ramps
                  if follower.cfg.network.ramp_to_freeway[r] == owner)
    raw = {r: float(_number(_field(incumbent, 'ramp_metering')[r])) for r in ramps}
    entries = {key: (reference, limit) for field, key, reference, limit, _ in move_box.entries
               if field == 'ramp_metering'}
    points = [('independent_seed', dict(raw))]
    for ramp in ramps:
        if ramp in (fixed_rates or {}):
            continue
        reference, limit = entries[ramp]
        cap = float(_number(follower.cfg.network.ramp_capacity_veh_h[ramp]))
        lo, hi = max(0., reference-limit), min(cap, reference+limit)
        values = {lo, hi, reference, max(lo, reference-limit/2), min(hi, reference+limit/2)}
        values.update(float(f)*cap for f in follower.ramp_metering_fractions if lo <= float(f)*cap <= hi)
        for index, value in enumerate(sorted(values, reverse=True)):
            if value != raw[ramp]:
                pair = dict(raw); pair[ramp] = value
                points.append((f'independent:{ramp}:{index}', pair))
    return tuple(points), 'none', None, {
        'source': 'independent canonical meter probes within fixed actual-action box',
        'candidate_nuf_constraint_applied': False, 'physical_quantization': 'caller canonical realizer',
        'anchor_token': move_box.anchor_token}


def build_current_freeway_domain(follower, owner, state, coupling, demand, incumbent,
                                 leader, previous, *, ownership, held_horizon_sec,
                                 budget_tolerance_veh_h, joint_pairs, nuf_semantics,
                                 context_provenance, decision_anchor=None, move_box=None,
                                 price_probe=False, fixed_meter_rates=None):
    """Connect installed candidate values to a finite held-action Domain.

    No objective, price refresh, _solve_with, rollout or flow-cache commit runs.
    Current scope is the installed zoned21-cell relaxed + k-best VSL branch.
    Existing temporal sequences supply ordered first-value evidence only; this
    finite owner-coordinate neighborhood is NOT the old temporal search domain.
    VSL uses the current incumbent snapshot, as legacy _solve_with does. The
    previous committed action anchors only the existing meter movement box.
    Meter coordinates retain one fixed branch seed instead of cost-dependent
    earlier coordinate optima. Callers explicitly choose joint_pairs, horizon,
    tolerances, frozen-context provenance and N_UF semantics. The canonical
    realizer and both admissibility callbacks are still required by generate.

    The installed effective_lane_profile reads runtime context. Its isolation
    and the full state/forecast/price/leader source fingerprint belong to the
    caller's query scope. The source repair accumulator and its state/previous/
    coupling/demand inputs are privately copied: effective_lane_profile may
    initialize the supplied state's lane fields. No caller input is rewritten.
    """
    cfg, net, ff = follower.cfg, follower.cfg.network, follower.cfg.freeway_follower
    if owner not in ('FW_E', 'FW_W') or owner not in ownership.owners:
        raise ValueError('Unknown freeway owner')
    validate_action_addresses(ownership, incumbent)
    validate_nuf_semantics(incumbent, nuf_semantics)
    if previous is None:
        raise ValueError('Explicit previous action required for decision-anchored domain')
    if _number(held_horizon_sec) <= 0 or _number(budget_tolerance_veh_h) < 0:
        raise ValueError('Positive held horizon and nonnegative tolerance required')
    if not isinstance(context_provenance, Mapping) or not context_provenance:
        raise ValueError('Explicit frozen query context provenance required')
    if type(joint_pairs) is not tuple:
        raise ValueError('Caller must supply explicit ordered joint_pairs')
    heads = tuple(net.freeway_vsl_zone_heads[owner])
    head_of = tuple(net.freeway_vsl_zone_head_of_cell[owner])
    zones = tuple(net.freeway_vsl_zone_of_cell[owner])
    if (heads != (0, 5, 10, 15) or head_of != tuple(5 * min(i // 5, 3) for i in range(21))
            or zones != tuple(min(i // 5, 3) for i in range(21))
            or tuple(net.freeway_vsl_zone_free) != (0, 1, 2)):
        raise ValueError('Current domain requires three free heads and fixed recovery zone')
    if not cfg.mpc.relaxed_quantized_controls or not ff.vsl_sequence_search:
        raise ValueError('Current extraction supports installed relaxed temporal VSL source only')
    sequence_method = follower._freeway_vsl_sequence_candidates
    if not getattr(sequence_method, '_rw_vsl_kbest', False):
        raise ValueError('Current domain requires the installed k-best sequence source')
    if len(state.freeway_density[owner]) != 21:
        raise ValueError('Current domain requires all21 observed freeway density cells')
    source_horizon = max(1, ff.freeway_prediction_horizon_steps or cfg.mpc.horizon_steps)
    private = copy.copy(follower)
    private._wu = copy.copy(follower._wu)
    private._wu._repair_diagnostics = deepcopy(follower._wu._repair_diagnostics)
    source_state = deepcopy(state)
    source_snapshot = deepcopy(incumbent if decision_anchor is None else decision_anchor)
    base = private._wu._relaxed_freeway_segment_candidates(
        owner, 21, source_state, deepcopy(coupling), source_snapshot, deepcopy(demand))
    sequences = private._freeway_vsl_sequence_candidates(
        owner, 21, source_snapshot, base, source_horizon)
    if not sequences or any(not seq or len(seq[0]) != 21 for seq in sequences):
        raise ValueError('Installed source returned no complete first VSL vector')
    allowed = tuple(float(_number(v)) for v in ff.vsl_set)
    max_step = max(0.0, float(_number(ff.max_vsl_step)))
    first = [tuple(float(_number(v)) for v in seq[0]) for seq in sequences]
    refs = deepcopy(follower.vsl_marginal_price_ref)
    prices = deepcopy(follower.vsl_marginal_price)
    trust = follower.vsl_marginal_price_trust_kmh
    if not isinstance(refs, Mapping) or (prices is not None and not isinstance(prices, Mapping)):
        raise ValueError('Explicit current VSL price/reference maps required')
    for value in refs.values():
        _number(value)
    for value in (prices or {}).values():
        _number(value)
    if trust is not None and _number(trust) < 0:
        raise ValueError('Negative VSL price trust')
    active_trust = bool(prices) and trust is not None and not price_probe
    def trusted(vector):
        return all(refs.get(f'{owner}__seg{i}') is None
                   or abs(value - float(refs[f'{owner}__seg{i}'])) <= float(trust) + 1.0e-9
                   for i, value in enumerate(vector))
    kept = [vec for vec in first if trusted(vec)] if active_trust else first
    trust_fallback = bool(active_trust and not kept)
    selected = (kept or first) if move_box is None else kept
    current = tuple(float(_field(incumbent, 'vsl')[f'{owner}__seg{i}']) for i in range(21))
    snapshot_heads = {h: float(_number(_field(source_snapshot, 'vsl')[f'{owner}__seg{h}'])) for h in heads}
    values = {h: [] for h in (0, 5, 10)}
    projected_rejected = []
    for vector in selected:
        if any(vector[i] != vector[head_of[i]] for i in range(21)) or any(vector[i] != current[i] for i in range(15, 21)):
            raise ValueError('Installed first-vector source changed zone aliases or fixed recovery')
        for head in values:
            value = vector[head]
            if value not in allowed or abs(value - snapshot_heads[head]) > max_step + 1.0e-9:
                raise ValueError('Installed first value violates configured set/snapshot step')
            projected = tuple(value if head_of[i] == head else current[i] for i in range(21))
            if active_trust and not trust_fallback and not trusted(projected):
                projected_rejected.append((head, value, 'fixed_incumbent_full_vector_trust'))
                continue
            if value not in values[head]:
                values[head].append(value)
    from evaluation.controllers import physical_ramp_branches as physical_meters
    if physical_meters.enabled(cfg):
        if nuf_semantics != 'fixed_target' or decision_anchor is None:
            raise ValueError('Physical domain requires fixed NUF target and actual decision anchor')
        points,budget_mode,budget,meter_provenance=_physical_meter_points(follower,owner,incumbent,decision_anchor)
    elif price_probe:
        if move_box is None or decision_anchor is None:
            raise ValueError('Independent price probes require a fixed actual-action box')
        points, budget_mode, budget, meter_provenance = _independent_meter_points(
            follower, owner, incumbent, decision_anchor, move_box, fixed_meter_rates)
    else:
        points, budget_mode, budget, meter_provenance = _current_meter_points(
            follower, owner, incumbent, leader, previous)
    for head, value, label in joint_pairs:
        if head not in values or value not in values[head] or label not in {name for name, _ in points}:
            raise ValueError('Explicit joint pair is outside current extracted values')
    provenance = {
        'schema': 'current-linked-freeway-domain/v1', 'owner': owner,
        'query_context': deepcopy(dict(context_provenance)), 'state_time_sec': _number(state.time_sec),
        'held_horizon_sec': held_horizon_sec, 'nuf_semantics': nuf_semantics,
        'source_horizon_steps': source_horizon, 'source_first_vectors': tuple(first),
        'vsl_source': {'relaxed': private._wu._relaxed_freeway_segment_candidates.__func__.__qualname__,
                       'sequence': sequence_method.__func__.__qualname__},
        'vsl_snapshot_heads': snapshot_heads,
        'vsl_anchor': 'actual decision anchor' if decision_anchor is not None else 'current incumbent snapshot',
        'meter_box_anchor': 'previous committed action', 'vsl_set': allowed, 'max_vsl_step': max_step,
        'vsl_prices': prices, 'vsl_references': refs, 'vsl_trust_kmh': trust,
        'vsl_empty_trust_fallback': trust_fallback, 'projection_rejected': tuple(projected_rejected),
        'meter': meter_provenance, 'joint_pairs_policy': 'explicit caller ordered pairs',
        'candidate_scope': 'finite owner-coordinate held-action neighborhood; not temporal-sequence search',
        'legacy_sequential_search_equivalent': False, 'shared_feasibility_certified': False,
        'runtime_lane_context_isolation_required': True,
    }
    return Domain({h: tuple(v) for h, v in values.items()}, points, joint_pairs,
                  held_horizon_sec, budget_mode, budget, budget_tolerance_veh_h,
                  provenance, nuf_semantics)


def make_joint_neighbor_callbacks(
        follower, state, coupling, demand, leader, previous, mapping,
        selected_plan, actuation, metadata, *, segment_vsl_func, context,
        context_fingerprint, query_scope, held_horizon_sec,
        budget_tolerance_veh_h, total_budget, directional_budgets,
        freeway_joint_pairs, previous_meter_anchor=None, decision_anchor=None,
        move_limits=None, deadline_check=None, price_probe=False, defer_unvisited_command_checks=False):
    """Bind the current 19-owner finite domains to canonical physical commands.

    No cost, rollout, price refresh or shared receiving allocator is called.
    ``neighbors(owner, incumbent, context)`` returns the pure game's Neighborhood.
    ``neighbor_evidence`` additionally returns request/rejection provenance.
    ``physical_fingerprint(action, context)`` returns owner command tokens;
    ``physical_rows(action)`` returns the complete catalog payload, and
    ``command_evidence(action)`` retains ordered CSV rows and owner model vectors.

    Root supplies a fresh query_scope context manager for EVERY call. It must
    restore runtime globals even on exceptions; cfg/follower/state/forecast are
    caller-owned private query inputs. context_fingerprint must cover their full
    source values, prices, duals, leader and runtime-hook state. Explicit physical
    bindings below are also checked by value, never cached by object identity.

    Both current incumbent and historical reference use canonical all-open
    near-capacity rates. Historical previous must come from the meter helper's
    verified original-action/context/CSV reference. Its separate final-writeback
    rates anchor the meter box, before all-open normalization. It is never
    reallocated under this decision or tested against the NEW leader budget. Current
    candidates use explicit total/directional hard budgets; the frozen leader
    target is never copied into derived action.N_UF_star.

    Source request filters are preserved before canonical quantization. Their
    realized rates may differ: this is recorded, not treated as a new post-write
    trust policy. Admissibility here certifies only this finite command domain,
    caps and declared budgets. Shared physical feasibility remains an evaluator
    obligation. Headless/red-only plan metadata is pinned, not invented as rows.
    """
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import area_meter_finalization as meters

    from evaluation.controllers import physical_ramp_branches as physical_meters
    if any(not callable(fn) for fn in (segment_vsl_func, context_fingerprint,
                                      query_scope, freeway_joint_pairs)):
        raise ValueError('Explicit command, context, query-scope and joint-pair callbacks required')
    if _number(held_horizon_sec) <= 0 or _number(budget_tolerance_veh_h) < 0:
        raise ValueError('Explicit positive held horizon and nonnegative tolerance required')
    cfg, net = follower.cfg, follower.cfg.network
    physical=physical_meters.enabled(cfg)
    nuf_semantics='fixed_target' if physical else 'realized_sum'
    if physical and (decision_anchor is None or total_budget is not None or directional_budgets):
        raise ValueError('Physical joint neighbors require an actual anchor; NUF budgets belong to predicted merges')
    if type(defer_unvisited_command_checks) is not bool:
        raise ValueError('Deferred unvisited command checks must be boolean')
    if previous is None or leader is None:
        raise ValueError('Explicit historical previous action and frozen leader required')
    if deadline_check is not None and not callable(deadline_check):
        raise ValueError('Decision deadline_check must be callable')
    if (decision_anchor is None) != (move_limits is None):
        raise ValueError('Decision anchor and explicit movement limits must be supplied together')
    if price_probe and (decision_anchor is None or total_budget is not None or directional_budgets):
        raise ValueError('Common price probes need actual anchor/box and no candidate quantity budgets')
    ownership = addresses.build_ownership(cfg, mapping, selected_plan,
                                          segment_dsd_controls=adapter._segment_dsd_controls)
    if len(ownership.owners) != 19:
        raise ValueError('Current integration requires all 17 urban and two freeway owners')
    decision_anchor = deepcopy(decision_anchor)
    move_box = None if decision_anchor is None else build_fixed_move_box(ownership, decision_anchor, cfg, move_limits)
    validate_action_addresses(ownership, previous)
    validate_nuf_semantics(previous, nuf_semantics)
    meter_context, meter_identity = meters._context(cfg)
    if (_typed(meter_context['mapping']['ramp_meters']) != _typed(mapping['ramp_meters'])
            or _typed(meter_context['actuation']) != _typed(actuation)):
        raise ValueError('Writer and canonical meter context must use identical physical definitions')
    if physical:
        anchor_proof=previous.diagnostics.get('physical_ramp_recorded_csv')
        if not isinstance(anchor_proof,dict):
            raise ValueError('Physical historical reference requires its recorded CSV')
        checked=physical_meters.read_recorded_control(previous.copy(),cfg,anchor_proof['path'])
        if checked.diagnostics['physical_ramp_recorded_csv'] != anchor_proof:
            raise ValueError('Recorded physical anchor CSV changed')
        if (decision_anchor.ramp_metering != previous.ramp_metering or
                any(decision_anchor.diagnostics['rw_meter_green_'+r] != previous.diagnostics['rw_meter_green_'+r] for r in net.ramps)):
            raise ValueError('Physical decision anchor differs from recorded actual greens')
        anchor_rates=dict(previous.ramp_metering)
    else:
        anchor_rates = meters.historical_meter_anchor_rates(previous, previous_meter_anchor)
        anchor_proof = previous.diagnostics[meters.HISTORICAL_REFERENCE]
        if anchor_proof['physical_definition_sha256'] != meters._hash({
                'actuation': meter_context['actuation'], 'mapping': meter_context['mapping'],
                'capacities': dict(net.ramp_capacity_veh_h)}):
            raise ValueError('Historical and current physical meter definitions differ')
    meter_previous = {'ramp_metering': anchor_rates}
    writer = offset_promotion.resolve_writer(actuation, physical_signal_contract=True)
    if writer != offset_promotion.WRITER_EXPERIMENT:
        raise ValueError('Joint physical commands require current experiment offset authority')
    cycle = _number(actuation['real_world_ramp_metering']['cycle_sec'])
    if cycle <= 0:
        raise ValueError('Positive physical meter cycle required')
    groups = {r: [] for r in net.ramp_capacity_veh_h}
    meter_by_id = {}
    for meter in mapping['ramp_meters']:
        mid = str(meter.get('id', meter.get('control_id', '')))
        groups[mid if physical else meter['model_ramp_key']].append(mid)
        meter_by_id[mid] = meter

    def canonical_open_rates(action):
        if physical:
            physical_meters.prepare_control(action.copy(),cfg)
            return
        # No write/reallocation here, in particular for historical previous.
        diag = action.diagnostics
        for ramp, mids in groups.items():
            greens = [_number(diag['rw_meter_green_' + mid]) for mid in mids]
            if any(g < 0 or g > cycle for g in greens):
                raise ValueError('Physical meter green outside the configured cycle')
            if all(g == cycle for g in greens) and action.ramp_metering[ramp] != net.ramp_capacity_veh_h[ramp]:
                raise ValueError('All-open physical command has a noncanonical modeled rate alias')

    canonical_open_rates(previous)
    fixed_proofs = fixed_meter_coordinate_proofs(cfg, decision_anchor, move_box) if price_probe and not physical else None
    installed_proofs = getattr(follower, '_joint_fixed_meter_proofs', None)
    if installed_proofs is not None:
        if physical:
            raise ValueError('Legacy fixed-rate proof cannot freeze a physical green coordinate')
        validate_fixed_meter_coordinate_proofs(cfg, decision_anchor, installed_proofs, move_box=move_box)
    fixed_rates = {} if fixed_proofs is None else {r: p['fixed_rate_veh_h'] for r, p in fixed_proofs['meters'].items()}
    token = context_fingerprint(context)
    if type(token) not in (str, bytes) or not token:
        raise ValueError('Frozen context fingerprint must be a nonempty string/bytes token')

    def binding():
        def fields(obj, names):
            return {name: getattr(obj, name) for name in names}
        return {
            'mapping': mapping, 'selected_plan': selected_plan, 'actuation': actuation,
            'metadata': metadata, 'meter_context': meters._context(cfg),
            'previous': vars(previous), 'leader': vars(leader),
            'decision_move_box': None if move_box is None else move_box.entries,
            'decision_anchor': None if decision_anchor is None else vars(decision_anchor),
            'price_probe': price_probe,
            'fixed_meter_proofs': fixed_proofs,
            'installed_fixed_meter_proofs': getattr(follower, '_joint_fixed_meter_proofs', None),
            'total_budget': total_budget, 'directional_budgets': directional_budgets,
            'held_horizon_sec': held_horizon_sec, 'tolerance': budget_tolerance_veh_h,
            'network': fields(net, ('signal_actuation_contract', 'cycle_length', 'green_min',
                'ramp_capacity_veh_h', 'ramp_to_freeway', 'ramps', 'freeway_vsl_zone_heads',
                'freeway_vsl_zone_head_of_cell', 'freeway_vsl_zone_of_cell', 'freeway_vsl_zone_free')),
            'mpc': fields(cfg.mpc, ('phase_price_exchange_steps_sec', 'wu_faithful_nuf_coordination_mode',
                'baseline_move_box', 'leader_budget_off', 'relaxed_quantized_controls', 'horizon_steps')),
            'freeway': fields(cfg.freeway_follower, ('vsl_set', 'max_vsl_step',
                'vsl_sequence_search', 'freeway_prediction_horizon_steps')),
            'follower': fields(follower, ('phase_price_in_gne', 'ramp_offset_enabled', 'offset_directive',
                'offset_fractions', 'offset_marginal_price', 'offset_marginal_price_ref',
                'offset_marginal_price_trust_sec', 'ramp_metering_fractions', 'metering_marginal_price',
                'metering_marginal_price_ref', 'metering_marginal_price_trust_frac',
                'metering_release_certified', 'metering_price_split', '_lambda_UF',
                'vsl_marginal_price', 'vsl_marginal_price_ref', 'vsl_marginal_price_trust_kmh')),
            'omega_f': follower._wu._omega_f,
        }
    initial_binding = binding()
    binding_sha = _key(initial_binding)
    binding_snapshot = _snapshot_builtin_tree(initial_binding)
    binding_serialized = pickle.dumps(initial_binding, protocol=5) if binding_snapshot is not None else None
    del initial_binding

    def guard(query_context):
        if (context_fingerprint(query_context) != token
                or (query_context is not context and context_fingerprint(context) != token)):
            raise ValueError('Frozen joint query context changed')
        current_binding = binding()
        # Exact builtin equality proves the original hash is unchanged. Order
        # changes/custom structures retain the original order-insensitive check.
        if (not _matches_builtin_serialization(current_binding, binding_serialized)
                and _key(current_binding) != binding_sha):
            raise ValueError('Frozen physical/domain binding changed')

    @contextmanager
    def scoped(query_context):
        guard(query_context)
        try:
            with query_scope():
                yield
        finally:
            guard(query_context)

    provenance = {'schema': 'canonical-joint-neighbor-bindings/v1',
        'binding_sha256': binding_sha, 'meter_context_sha256': meter_identity,
        'context_fingerprint': token, 'held_horizon_sec': held_horizon_sec,
        'nuf_semantics': nuf_semantics, 'leader_target_nuf_veh_h': _number(leader.N_UF_star),
        'hard_total_budget': deepcopy(total_budget), 'hard_directional_budgets': deepcopy(directional_budgets),
        'previous_meter_anchor': deepcopy(anchor_proof),
        'shared_feasibility_certified': False, 'legacy_temporal_search_equivalent': False,
        'scope': 'finite full-action held neighborhood; no price, cost or receiving allocation',
        'meter_filter_scope': 'source requests before canonical quantization; no new realized trust policy'}
    if move_box is not None:
        provenance.update(fixed_actual_action_box={'anchor_token': move_box.anchor_token,
            'entries': move_box.entries, 'post_realization_checked': True}, price_probe=price_probe)
    physical_fields = tuple(f for f in action_csv_schema.ACTION_CSV_FIELDS if f != 'metadata')
    catalog = {(kind, identity): who for kind, identity, who, _ in ownership.writes}

    def uncached_command_evidence(action, query_context=context):
        before = _key(vars(action))
        with scoped(query_context):
            private = deepcopy(action)
            validate_action_addresses(ownership, private)
            validate_nuf_semantics(private, nuf_semantics)
            if move_box is not None: move_box.validate(private)
            canonical_open_rates(private)
            meters.assert_writer(private, cfg, require_scored=True)
            for owner in net.signals:
                values = _vector(private, owner)
                signals.validate_vector(net, owner, values)
                if any(v != (round(plant_cycle.written_axis_green_sec(v), 3) if v > 0 else 0.)
                       for v in values.values()):
                    raise ValueError('Writer would change a modeled phase green')
                if private.offsets[owner] != signals.written_offset_sec(private, cfg, owner):
                    raise ValueError('Writer would change a modeled offset')
            allowed = tuple(cfg.freeway_follower.vsl_set)
            for owner in ('FW_E', 'FW_W'):
                head_of = net.freeway_vsl_zone_head_of_cell[owner]
                vector = [private.vsl[f'{owner}__seg{i}'] for i in range(len(head_of))]
                if (any(_number(v) not in allowed for v in vector)
                        or any(v != vector[head_of[i]] for i, v in enumerate(vector))
                        or private.vsl[owner] != min(vector)):
                    raise ValueError('Modeled VSL set, zone aliases or direction fallback differ')
            segment_values = []
            for segment in mapping['segments']:
                link, index = adapter._segment_model_coordinates(str(segment['segment_id']), segment)
                value = _number(segment_vsl_func(private, link, index, cfg))
                if value != private.vsl[f'{link}__seg{index}']:
                    raise ValueError('Runtime VSL command differs from the full modeled vector')
                segment_values.append(value)
            ramp_actions = adapter.real_world_ramp_meter_actions(private, cfg, actuation, mapping)
            rows = tuple(adapter.iter_action_csv_rows(private, cfg, mapping, segment_values,
                ramp_actions, metadata, actuation, selected_plan, writer))
            grouped, windows = {}, set()
            for row in rows:
                kind = row['kind']
                if kind == 'vsl':
                    key = ('dsd', str(row['dsd_no']))
                elif kind == 'signal':
                    key = ('signal_sc', str(row['sc_no']))
                elif kind == 'signal_sg':
                    key = ('signal_sg', f"{row['sc_no']}:{row['dsd_no']}")
                    window = (key, row['link'])
                    if window in windows:
                        raise ValueError('Duplicate physical SG window')
                    windows.add(window)
                elif kind == 'ramp_meter':
                    meter = meter_by_id[row['id']]
                    if int(row['sc_no']) != int(meter['sc_no']):
                        raise ValueError('Physical meter controller address changed')
                    key = ('signal_sg', f"{row['sc_no']}:1")
                else:
                    raise ValueError('Unknown physical CSV row kind')
                if key not in catalog or (key in grouped and kind != 'signal_sg'):
                    raise ValueError('Unexpected or duplicate physical row address')
                payload = tuple(row.get(field, '') for field in physical_fields)
                _typed(payload)
                grouped.setdefault(key, []).append(payload)
            grouped = {key: tuple(value) for key, value in grouped.items()}
            fingerprints = owner_physical_fingerprints(ownership, grouped)
            vectors = {owner: {field: {a.key: _field(private, field)[a.key]
                for a in ownership.addresses if a.owner == owner and a.field == field}
                for field in LEVER_FIELDS} for owner in ownership.owners}
            if _key(vars(action)) != before:
                raise ValueError('Command query mutated caller action')
            # The canonical writer may add diagnostic bookkeeping to its private
            # copy, but cannot alter the evaluated full model vector.
            if any(_typed(_field(private, f)) != _typed(_field(action, f)) for f in LEVER_FIELDS):
                raise ValueError('Command callbacks changed modeled controls')
            return {'ordered_rows': deepcopy(rows), 'physical_rows': grouped,
                'owner_physical_sha256': fingerprints, 'owner_model_vectors': deepcopy(vectors),
                'owner_model_sha256': {owner: _key(v) for owner, v in vectors.items()},
                'provenance': deepcopy(provenance)}

    # One frozen binding only. The existing opt-in command optimization also
    # avoids re-running the writer for identical, already checked full actions.
    # Context guards still run on every hit; serialized results prevent callers
    # from mutating a later proof. This cache cannot cross decisions/bindings.
    command_cache = {}
    command_cache_counts = {'requests': 0, 'hits': 0, 'writer_checks': 0,
                            'retained_bytes': 0, 'entry_limit': 256}
    def command_evidence(action, query_context=context):
        command_cache_counts['requests'] += 1
        if not defer_unvisited_command_checks:
            command_cache_counts['writer_checks'] += 1
            return uncached_command_evidence(action, query_context)
        guard(query_context)
        key = (type(action), pickle.dumps(vars(action), protocol=5))
        if key in command_cache:
            command_cache_counts['hits'] += 1
            result = pickle.loads(command_cache[key])
        else:
            command_cache_counts['writer_checks'] += 1
            result = uncached_command_evidence(action, query_context)
            if pickle.dumps(vars(action), protocol=5) != key[1]:
                raise ValueError('Command query mutated caller action')
            payload = pickle.dumps(result, protocol=5)
            if len(command_cache) >= command_cache_counts['entry_limit']:
                old = next(iter(command_cache))
                command_cache_counts['retained_bytes'] -= len(old[1]) + len(command_cache.pop(old))
            command_cache[key] = payload
            command_cache_counts['retained_bytes'] += len(key[1]) + len(payload)
        guard(query_context)
        return result

    def physical_rows(action, query_context=context):
        return command_evidence(action, query_context)['physical_rows']

    def physical_fingerprint(action, query_context):
        guard(query_context)
        return command_evidence(action, query_context)['owner_physical_sha256']

    def prepare(action, owned):
        with scoped(context):
            if physical:
                return physical_meters.prepare_control(action.copy(),cfg)
            return meters.prepare_canonical_candidate(action, cfg, owned_ramps=owned,
                total_budget=total_budget, directional_budgets=directional_budgets,
                budget_tolerance_veh_h=budget_tolerance_veh_h)

    def neighbor_evidence(owner, incumbent, query_context, *, _all_command_evidence=True):
        if deadline_check is not None: deadline_check('joint_neighbor_generation')
        with scoped(query_context):
            if owner not in ownership.owners:
                raise ValueError('Unknown owner')
            base = command_evidence(incumbent)
            # Do not silently repair an incumbent or relax a new hard budget.
            checked = prepare(incumbent, tuple(groups))
            if any(_typed(_field(checked, f)) != _typed(_field(incumbent, f)) for f in LEVER_FIELDS):
                raise ValueError('Incumbent is not the prepared canonical representation')
            if owner in net.signals:
                # Restore source-query globals before any later command guard
                # fingerprints the LIVE runtime context, including nested calls.
                with scoped(query_context):
                    bundle = generate_urban_requests(follower, owner, deepcopy(incumbent), ownership=ownership,
                        decision_anchor=decision_anchor, price_probe=price_probe)
                with scoped(query_context):
                    result = realize_urban_requests(bundle, incumbent, cfg, ownership=ownership,
                        selected_plan=selected_plan, actuation=actuation, metadata=metadata,
                        signal_group_rows=adapter.signal_group_action_rows, move_box=move_box,
                        deadline_check=deadline_check, price_basis_only=price_probe)
                candidates = result['candidates']
            else:
                with scoped(query_context):
                    domain = build_current_freeway_domain(follower, owner, state, coupling, demand,
                        incumbent, leader, meter_previous, ownership=ownership, held_horizon_sec=held_horizon_sec,
                        budget_tolerance_veh_h=budget_tolerance_veh_h, joint_pairs=(),
                        nuf_semantics=nuf_semantics, context_provenance=provenance,
                        decision_anchor=decision_anchor, move_box=move_box, price_probe=price_probe)
                if price_probe:
                    # Fixed coordinates stay in the catalog/proof; they do not
                    # require redundant requests or an invented zero gradient.
                    domain = replace(domain, meter_points=tuple((label, pair) for label, pair in domain.meter_points
                        if all(pair[r] == incumbent.ramp_metering[r] for r in fixed_rates if r in pair)), joint_pairs=())
                with scoped(query_context):
                    pairs = freeway_joint_pairs(owner, deepcopy(domain))
                if type(pairs) is not tuple:
                    raise ValueError('Joint selector must return an explicit ordered tuple')
                domain = replace(domain, joint_pairs=pairs)
                ramps = tuple(a.key for a in ownership.addresses if a.owner == owner and a.field == 'ramp_metering')
                valid_pairs = [dict(p) for _, p in domain.meter_points]
                valid_pairs.append({r: incumbent.ramp_metering[r] for r in ramps})

                def requested_admissible(action):
                    pair = {r: action.ramp_metering[r] for r in ramps}
                    ok = pair in valid_pairs
                    for head, values in domain.head_values.items():
                        value = action.vsl[f'{owner}__seg{head}']
                        ok = ok and value in (*values, incumbent.vsl[f'{owner}__seg{head}'])
                    ok = ok and (move_box is None or not move_box.violations(action))
                    return {'feasible': bool(ok), 'reason': None if ok else 'Outside extracted source request domain',
                            'source_filters_applied': True, 'shared_feasibility_certified': False}

                def realized_admissible(action):
                    # Trust/box/certification have already filtered requests.
                    # Recheck actual capacities, aliases and the explicit
                    # canonical allocator result, not a fabricated raw lattice.
                    ok = all(0 <= action.ramp_metering[r] <= net.ramp_capacity_veh_h[r] for r in ramps)
                    ok = ok and (move_box is None or not move_box.violations(action))
                    return {'feasible': bool(ok), 'reason': None if ok else 'Realized rate outside configured near capacity',
                            'source_request_filters_retained': True, 'shared_feasibility_certified': False}

                result = generate(ownership, cfg, owner, incumbent, domain,
                    requested_admissible=requested_admissible,
                    realize=lambda action: prepare(action, ramps),
                    realized_admissible=realized_admissible, physical_rows=physical_rows,
                    deadline_check=deadline_check,
                    price_basis_dimension=(3 + sum(r not in fixed_rates for r in ramps)) if price_probe else None,
                    meter_actual_reference=decision_anchor if physical else None,
                    defer_physical_commands=physical and not _all_command_evidence and not price_probe)
                if not result['incumbent_feasible']:
                    raise meters.MeterCandidateInfeasible('Incumbent violates current source/realized budget')
                candidates = tuple(c['control'] for c in result['candidates'])
            evidence = []
            for candidate in candidates:
                if deadline_check is not None: deadline_check('joint_candidate_command_check')
                assert_owner_transition(ownership, owner, incumbent, candidate)
                if not _all_command_evidence:
                    continue
                item = command_evidence(candidate)
                if any(item['owner_physical_sha256'][other] != base['owner_physical_sha256'][other]
                       for other in ownership.owners if other != owner):
                    raise ValueError('Candidate changed another owner physical command')
                evidence.append(item)
            return {'complete': True, 'incomplete_reason': None,
                'domain_label': 'canonical-current-19owner-held-finite/v1' + ('/realized-price-basis' if price_probe else ''),
                'candidates': tuple(candidates), 'command_evidence': tuple(evidence),
                'source_bundle': result, 'provenance': deepcopy(provenance)}

    def neighbors(owner, incumbent, query_context):
        # Enumeration/quantization/owner checks still cover the entire domain.
        # The game and restoration paths both check full native commands and
        # unchanged foreign-owner rows before evaluating each visited action.
        # Price preparation retains eager evidence because it batches responses.
        result = neighbor_evidence(owner, incumbent, query_context,
            _all_command_evidence=not defer_unvisited_command_checks or price_probe)
        return addresses.Neighborhood(result['candidates'], result['complete'],
                                      result['domain_label'], result['incomplete_reason'])

    return {'ownership': ownership, 'neighbors': neighbors, 'neighbor_evidence': neighbor_evidence,
            'physical_fingerprint': physical_fingerprint, 'physical_rows': physical_rows,
            'command_evidence': command_evidence, 'provenance': deepcopy(provenance),
            'move_box': move_box,
            'fixed_meter_proofs': deepcopy(fixed_proofs),
            'command_cache_stats': lambda: dict(command_cache_counts),
            'validate_move_box': None if move_box is None else move_box.validate}
