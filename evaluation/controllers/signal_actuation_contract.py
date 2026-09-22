"""Opt-in physical signal contract shared by candidate generation and rollout.

Supports the selected mainline plan, whose active SGs share full phase windows.
The ordinary native/monitor path remains owned by the existing adapter wrapper.
"""
from __future__ import annotations

import copy
import importlib
import json
import math
import struct
from functools import lru_cache
from collections import OrderedDict

from evaluation.controllers import offset_promotion, plant_cycle, signal_group_plan

PHASES = signal_group_plan.MODEL_PHASES


def enabled(net):
    return bool(getattr(net, "signal_actuation_contract", None))


def native_clock_basis(net, signal):
    return ((getattr(net, 'signal_actuation_contract', None) or {}).get('nodes', {})
            .get(signal, {}).get('native_clock_basis'))


def _native_payload(raw):
    if raw.get('native_clock_basis') is None:
        return None
    return json.dumps({k: raw[k] for k in ('native_cycle_sec', 'axis_green_sec', 'native_clock_basis')},
                      sort_keys=True, separators=(',', ':'), allow_nan=False)


@lru_cache(maxsize=1024)
def _native_plan(payload, segments=()):
    data = json.loads(payload)
    return signal_group_plan.NodePlan('clock', float(data['native_cycle_sec']), dict(segments), {},
        data['axis_green_sec'], {}, (), (), data['native_clock_basis'])


def _native_phase_bounds(net, signal, raw):
    plan = _native_plan(_native_payload(raw))
    basis = plan.native_clock_basis
    live = tuple(net.signal_live_phases(signal))
    source_live = tuple(p for p in PHASES if plan.axis_green_sec.get(p, 0.) > 0.)
    if live != source_live:
        raise ValueError(f'{signal}: native live phases differ from configured phases')
    policy = getattr(net, 'native_signal_minimum_policy', None)
    if policy not in (None, '', 'strict', 'include_source_reference'):
        raise ValueError(f'{signal}: unsupported native signal minimum policy')
    physical_low, physical_high = plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC
    minimum = float(net.green_min)
    if not math.isfinite(minimum):
        raise ValueError(f'{signal}: nonfinite configured green minimum')
    lows = {p: max(physical_low, min(minimum, plan.axis_green_sec[p])
                  if policy == 'include_source_reference' else minimum) for p in live}
    total = float(net.signal_effective_green_total(signal))
    clearance = float(basis['amber_sec']) + float(basis['all_red_sec'])
    concurrent = basis['kind'] == 'concurrent_p1_p2'
    expected = float(basis['cycle_sec']) - 2 * clearance if concurrent else sum(plan.axis_green_sec.values())
    if (not all(math.isfinite(v) for v in (*lows.values(), physical_high, total))
            or abs(total - expected) > 1e-8
            or abs(float(net.signal_cycle_length(signal)) - float(basis['cycle_sec'])) > 1e-8):
        raise ValueError(f'{signal}: configured native cycle/green budget differs from source')
    if concurrent:
        lo2 = max(lows['p2'], total-physical_high, lows['p1'] + float(basis['amber_sec']))
        hi2 = min(physical_high, total-lows['p4'])
        result = {'p1': (lows['p1'], min(physical_high, hi2-float(basis['amber_sec']))),
                  'p2': (lo2, hi2), 'p4': (total-hi2, total-lo2)}
    else:
        result = {p: (lows[p], min(physical_high, total-sum(v for q, v in lows.items() if q != p)))
                  for p in live}
        if sum(lows.values()) > total or total > len(live) * physical_high:
            raise ValueError(f'{signal}: green box cannot contain native budget {total}')
    if any(lo > hi for lo, hi in result.values()):
        raise ValueError(f'{signal}: infeasible native phase bounds')
    return result


def phase_bounds(net, signal):
    """Per-phase bounds; source minima are included only by explicit policy."""
    if native_clock_basis(net, signal) is not None:
        return _native_phase_bounds(net, signal, net.signal_actuation_contract['nodes'][signal])
    low, high, _ = bounds(net, signal)
    return {p: (low, high) for p in net.signal_live_phases(signal)}


def bounds(net, signal):
    if native_clock_basis(net, signal) is not None:
        box = phase_bounds(net, signal)
        return min(v[0] for v in box.values()), max(v[1] for v in box.values()), float(net.signal_effective_green_total(signal))
    low = max(float(net.green_min), plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC[0])
    total = float(net.signal_effective_green_total(signal))
    count = len(net.signal_live_phases(signal))
    high = min(plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC[1], total - (count - 1) * low)
    if not count or not all(math.isfinite(v) for v in (low, high, total)):
        raise ValueError(f"{signal}: invalid signal budget")
    if not count * low <= total <= count * high:
        raise ValueError(f"{signal}: green box cannot contain budget {total}")
    return low, high, total


def project_vector(net, signal, values):
    """Project before scoring, preserving the budget and CSV millisecond grid."""
    if not enabled(net):
        return values
    if native_clock_basis(net, signal) is not None:
        return _project_native_vector(net, signal, values)
    from src.models.state import _project_to_budget
    live = tuple(net.signal_live_phases(signal))
    low, high, total = bounds(net, signal)
    raw = [float(values.get(p, 0.0)) for p in live]
    if not all(math.isfinite(v) for v in raw):
        raise ValueError(f"{signal}: nonfinite candidate green")
    projected = _project_to_budget(raw, total, low, high)
    # Round once at candidate creation, then repair only the <=N millisecond
    # residual. The writer may serialize but must not project this vector again.
    units = [round(v * 1000) for v in projected]
    lo, hi, target = math.ceil(low * 1000), math.floor(high * 1000), round(total * 1000)
    if abs(target / 1000 - total) > 1e-9 or not len(live) * lo <= target <= len(live) * hi:
        raise ValueError(f"{signal}: budget is infeasible on the CSV millisecond grid")
    residual = target - sum(units)
    for i in range(len(units)):
        delta = min(residual, hi - units[i]) if residual > 0 else max(residual, lo - units[i])
        units[i] += delta
        residual -= delta
    if residual:
        raise ValueError(f"{signal}: unable to conserve rounded budget")
    result = {p: 0.0 for p in PHASES}
    result.update({p: v / 1000 for p, v in zip(live, units)})
    return result


def _project_native_vector(net, signal, values):
    box = phase_bounds(net, signal)
    raw = {p: float(values.get(p, 0.)) for p in PHASES}
    if not all(math.isfinite(v) for v in raw.values()):
        raise ValueError(f'{signal}: nonfinite candidate green')
    total = float(net.signal_effective_green_total(signal))
    basis = native_clock_basis(net, signal)
    clip = lambda value, pair: min(max(value, pair[0]), pair[1])
    if basis['kind'] == 'concurrent_p1_p2':
        amber = float(basis['amber_sec'])
        x = clip(raw['p1'], box['p1'])
        y = clip((raw['p2'] + total - raw['p4']) / 2, box['p2'])
        if x + amber > y:
            y = clip((raw['p1'] + amber + raw['p2'] + total - raw['p4']) / 3,
                     (max(box['p2'][0], box['p1'][0]+amber), min(box['p2'][1], box['p1'][1]+amber)))
            x = y - amber
        target = round(total * 1000)
        if abs(target/1000-total) > 1e-9:
            raise ValueError(f'{signal}: native budget is not on CSV millisecond grid')
        yu = min(max(round(y*1000), math.ceil(box['p2'][0]*1000)), math.floor(box['p2'][1]*1000))
        xu = min(max(round(x*1000), math.ceil(box['p1'][0]*1000)),
                 math.floor(min(box['p1'][1], yu/1000-amber)*1000 + 1e-9))
        result = {'p1': xu/1000, 'p2': yu/1000, 'p3': 0., 'p4': (target-yu)/1000}
    else:
        phases = tuple(box)
        projected = {p: clip(raw[p], box[p]) for p in phases}
        for _ in range(len(phases)+1):
            residual = total - sum(projected.values())
            if abs(residual) <= 1e-12: break
            free = [p for p in phases if projected[p] < box[p][1]-1e-12] if residual > 0 else [p for p in phases if projected[p] > box[p][0]+1e-12]
            if not free: break
            for p in free: projected[p] = clip(projected[p]+residual/len(free), box[p])
        units = {p: round(projected[p]*1000) for p in phases}
        target = round(total*1000)
        if abs(target/1000-total) > 1e-9:
            raise ValueError(f'{signal}: native budget is not on CSV millisecond grid')
        residual = target-sum(units.values())
        for p in phases:
            lo, hi = math.ceil(box[p][0]*1000), math.floor(box[p][1]*1000)
            delta = min(residual, hi-units[p]) if residual > 0 else max(residual, lo-units[p])
            units[p] += delta; residual -= delta
        if residual: raise ValueError(f'{signal}: unable to conserve rounded native budget')
        result = {p: units[p]/1000 if p in units else 0. for p in PHASES}
    validate_vector(net, signal, result)
    return result


def validate_vector(net, signal, values):
    if not enabled(net):
        return
    if native_clock_basis(net, signal) is not None:
        raw = net.signal_actuation_contract['nodes'][signal]
        return _validate_native_vector(net, signal, raw, values)
    live = tuple(net.signal_live_phases(signal))
    low, high, total = bounds(net, signal)
    vals = {p: float(values.get(p, 0.0)) for p in PHASES}
    if any(not math.isfinite(v) or abs(v - round(v, 3)) > 1e-9 for v in vals.values()):
        raise ValueError(f"{signal}: candidate must already be finite CSV-precision greens")
    if any(not low - 1e-9 <= vals[p] <= high + 1e-9 for p in live):
        raise ValueError(f"{signal}: candidate exceeds model/physical green bounds")
    if any(vals[p] != 0.0 for p in PHASES if p not in live):
        raise ValueError(f"{signal}: dead phase has nonzero green")
    if abs(sum(vals.values()) - total) > 1e-8:
        raise ValueError(f"{signal}: candidate does not conserve cycle budget")


def _validate_native_vector(net, signal, raw, values):
    box = _native_phase_bounds(net, signal, raw)
    vals = {p: float(values.get(p, 0.)) for p in PHASES}
    if any(not math.isfinite(v) or abs(v-round(v, 3)) > 1e-9 for v in vals.values()):
        raise ValueError(f'{signal}: candidate must already be finite CSV-precision greens')
    if any(not lo-1e-9 <= vals[p] <= hi+1e-9 for p, (lo, hi) in box.items()):
        raise ValueError(f'{signal}: candidate exceeds native model/physical green bounds')
    plan = _native_plan(_native_payload(raw))
    try:
        signal_group_plan.native_phase_windows(plan, vals, plan.native_clock_basis['amber_sec'], plan.native_clock_basis['all_red_sec'])
    except signal_group_plan.SignalGroupPlanError as exc:
        raise ValueError(f'{signal}: {exc}') from exc


def prepare_control(control, cfg):
    """Explicit migration of a previous action; caller keeps the returned copy."""
    if not enabled(cfg.network):
        return control
    out = control.copy()
    largest = 0.0
    for signal in cfg.network.signals:
        before = {p: float(control.green_times.get(f"{signal}_{p}", 0.0)) for p in PHASES}
        after = project_vector(cfg.network, signal, before)
        largest = max(largest, *(abs(before[p] - after[p]) for p in PHASES))
        out.green_times.update({f"{signal}_{p}": v for p, v in after.items()})
    out.diagnostics["signal_actuation_seed_projection_max_sec"] = largest
    return out


def validate_control(control, cfg):
    if enabled(cfg.network):
        for signal in cfg.network.signals:
            validate_vector(cfg.network, signal, {p: control.green_times.get(f"{signal}_{p}", 0.0) for p in PHASES})


def validate_writer(control, cfg, plan_table, offset_writer):
    if not enabled(cfg.network):
        return
    validate_control(control, cfg)
    contract = cfg.network.signal_actuation_contract
    if offset_writer != contract["offset_writer"]:
        raise ValueError("signal model and writer offset authority differ")
    if not plan_table:
        raise ValueError("physical signal contract requires the selected SG plan")
    for signal, expected in contract["nodes"].items():
        written_offset_sec(control, cfg, signal)
        actual = plan_table["controllers"][signal[2:]]
        if any(actual.get(k) != expected.get(k) for k in ("major_maps_to", "phase_segments", "phase_signal_groups", "axis_green_sec")):
            raise ValueError(f"{signal}: model and writer selected plans differ")
        if (actual.get('native_clock_basis') is not None or expected.get('native_clock_basis') is not None) and any(
                actual.get(k) != expected.get(k) for k in ('native_clock_basis', 'native_cycle_sec')):
            raise ValueError(f'{signal}: model and writer native clock bases differ')


def configure(cfg, tuning, plan_table):
    flag = (tuning.get("urban") or {}).get("physical_signal_contract", False)
    if not isinstance(flag, bool):
        raise ValueError("urban.physical_signal_contract must be boolean")
    offset_promotion.validate_experiment_declaration(tuning.get("actuation"), flag)
    if not flag:
        return {}
    if ((tuning.get("actuation") or {}).get("signal_green_freeze") or {}).get("enabled"):
        raise ValueError("legacy two-axis signal_green_freeze is outside the feasible candidate contract")
    net = cfg.network
    amber, all_red = plant_cycle.runner_clearance_sec()
    if (float(plan_table.get("amber_sec", amber)), float(plan_table.get("all_red_sec", all_red))) != (amber, all_red):
        raise ValueError("selected signal plan clearance differs from the actual writer")
    nodes = {}
    for signal in net.signals:
        raw = plan_table["controllers"][str(int(signal[2:]))]
        plan = signal_group_plan.node_plan_from_json(raw)
        live = tuple(p for p in PHASES if plan.phase_signal_groups[p] and plan.axis_green_sec[p] > 0)
        if live != tuple(net.signal_live_phases(signal)):
            raise ValueError(f"{signal}: model and selected writer plan disagree on live phases")
        # The current follower caches green fractions by phase, not movement/SG.
        # Reject partial SG windows instead of claiming that cache is general.
        for phase in live:
            if not plan.phase_segments[phase] or any((row[2], row[3]) != (0.0, 1.0) for row in plan.phase_segments[phase]):
                raise ValueError(f"{signal}: partial SG windows require a movement-level local cache")
        if plan.native_clock_basis is not None:
            # Verify the explicit basis once during setup against its active
            # source program. Candidate/clock calls then use the captured plan.
            from vissim_strict.signal_program import parse_sig
            basis = plan.native_clock_basis
            program = parse_sig(basis['source_path'], int(basis['active_prog_no']))
            proved = signal_group_plan.build_native_clock_basis(plan, program, amber_sec=amber,
                all_red_sec=all_red, controller_offset_sec=float(basis['controller_offset_sec']))
            if proved != basis:
                raise ValueError(f'{signal}: declared native clock differs from active source program')
            _validate_native_vector(net, signal, raw, plan.axis_green_sec)
            cycle = signal_group_plan.node_cycle_sec(plan, plan.axis_green_sec, amber, all_red)
        else:
            _, _, total = bounds(net, signal)
            cycle = total + len(live) * (amber + all_red)
        if abs(cycle - net.signal_cycle_length(signal)) > 1e-8 or abs(cycle - round(cycle, 3)) > 1e-8:
            raise ValueError(f"{signal}: model/writer cycle must match at CSV precision")
        nodes[signal] = copy.deepcopy(raw)
        nodes[signal]["_segments"] = tuple((p, plan.phase_segments[p]) for p in PHASES)
        nodes[signal]["_order"] = signal_group_plan.phase_layout_order(raw.get("major_maps_to", "p2"))
    net.signal_actuation_contract = {"nodes": nodes, "amber": amber, "all_red": all_red,
                                    "offset_writer": offset_promotion.resolve_writer(tuning.get("actuation"), physical_signal_contract=flag)}
    install_candidates(cfg)
    return {"physical_signal_contract_enabled": 1.0, "physical_signal_contract_nodes": len(nodes)}


@lru_cache(maxsize=16384)
def _phase_windows(segments, order, greens, clearance, native_payload=None, amber_sec=None):
    """The existing plan writer is the only phase-layout implementation."""
    # These are the actual selected plan's segments, not another phase clock.
    plan = signal_group_plan.NodePlan("clock", 0.0, dict(segments), {}, {}, {}, (), ()) if native_payload is None else _native_plan(native_payload, segments)
    amber = clearance if native_payload is None else float(amber_sec)
    rows = signal_group_plan.plan_windows(plan, dict(zip(PHASES, greens)), order, amber, clearance-amber)
    by_sg = {row.sg_no: row for row in rows}
    windows = {}
    for phase, spans in segments:
        if spans:
            row = by_sg.get(spans[0][0])
            if row is not None:
                windows[phase] = (round(row.start_sec, 6), round(row.end_sec, 6))
    return windows


def written_offset_sec(control, cfg, signal):
    """One representation for the integer-event model and both CSV row kinds."""
    net = cfg.network
    contract = net.signal_actuation_contract
    values = {p: float(control.green_times.get(f"{signal}_{p}", 0.0)) for p in PHASES}
    validate_vector(net, signal, values)
    cycle = _written_cycle(net, signal, values, contract)
    return round(offset_promotion.written_offset_sec(signal, control, contract["offset_writer"], cycle_sec=cycle), 3)


def _written_cycle(net, signal, values, contract):
    payload = _native_payload(contract['nodes'][signal])
    if payload is not None:
        return round(signal_group_plan.node_cycle_sec(_native_plan(payload), values, contract['amber'], contract['all_red']), 6)
    return round(sum(values.values()) + len(net.signal_live_phases(signal)) * (contract['amber'] + contract['all_red']), 6)


MAX_CLOCKS = 16384


MAX_INTERVALS = 131072


MAX_PLAN_TREES = 1024


_PLAN_TREES = OrderedDict()


_CLOCKS = OrderedDict()


_STATS = {'clock_hits': 0, 'clock_misses': 0, 'clock_bypasses': 0}


def clear_clock_cache():
    _CLOCKS.clear()
    _PLAN_TREES.clear()
    _finite_fraction.cache_clear()
    for key in _STATS:
        _STATS[key] = 0


def clock_cache_info():
    return {**_STATS, 'clocks': len(_CLOCKS),
            'max_clocks': MAX_CLOCKS, 'plan_trees': len(_PLAN_TREES),
            'max_plan_trees': MAX_PLAN_TREES, 'finite': _finite_fraction.cache_info()._asdict()}


def _uncached_clock(control, cfg, signal, values, raw, contract):
    # Preserve original validation/rounding order, including duplicate writer
    # validation. A miss computes exactly the existing clock, not a new clock.
    validate_vector(cfg.network, signal, values)
    offset = written_offset_sec(control, cfg, signal)
    cycle = _written_cycle(cfg.network, signal, values, contract)
    if not math.isfinite(offset) or not 0.0 <= offset <= cycle:
        raise ValueError(f'{signal}: written offset outside CSV range')
    payload = _native_payload(raw)
    args = (raw['_segments'], raw['_order'], tuple(values[p] for p in PHASES), contract['amber'] + contract['all_red'])
    table = _phase_windows(*args) if payload is None else _phase_windows(*args, payload, contract['amber'])
    return cycle, offset, tuple(table.items())


def _immutable(value):
    """Inspect exact built-in types before hashing; custom equality is not proof."""
    pending = [value]
    while pending:
        item = pending.pop()
        kind = type(item)
        if kind is tuple:
            pending.extend(item)
        elif kind is float:
            if not math.isfinite(item):
                return False
        elif item is not None and kind not in (bool, int, str):
            return False
    return True


def _immutable_plan(value):
    """Reuse a proved built-in tuple tree, holding its exact object strongly.

    Every leaf was checked before registration. Such a tuple tree cannot mutate;
    changed cfg plan fields supply another tuple and require another proof. No
    cfg, control or mutable container identity is accepted by this guard.
    """
    if type(value) is not tuple:
        return False
    ident = id(value)
    if _PLAN_TREES.get(ident) is value:
        return True
    if not _immutable(value):
        return False
    _PLAN_TREES[ident] = value
    if len(_PLAN_TREES) > MAX_PLAN_TREES:
        _PLAN_TREES.popitem(last=False)
    return True


_PHASE_SET = frozenset(PHASES)


_NATIVE_BASIS_KEYS = frozenset((
    'schema_version', 'kind', 'cycle_sec', 'amber_sec', 'all_red_sec',
    'phase_order', 'idle_after_phase_sec', 'native_green_sec',
    'program_offset_sec', 'controller_offset_sec', 'reference_offset_sec',
    'source_path', 'active_prog_no'))


def _compact_native_signature(raw):
    """Snapshot every native-payload operand, never a mutable object's identity.

    This narrow fast path accepts only the captured native-clock-v1 shape and
    exact JSON builtin types. Extra/missing fields, custom objects and unusual
    representations fall back to the original JSON key and original guards.
    Numeric bytes preserve signed zero as well as every finite float bit. The
    source path/program/offset fields are included even when they do not change
    the windows, so a source-basis mutation cannot reuse an earlier proof.
    """
    if type(raw) is not dict:
        return None
    basis = raw.get('native_clock_basis')
    axis = raw.get('axis_green_sec')
    if type(basis) is not dict or type(axis) is not dict:
        return None
    # Check key types before equality: subclasses may spoof builtin equality.
    if (tuple(map(type, basis)) != (str,) * len(basis)
            or basis.keys() != _NATIVE_BASIS_KEYS
            or tuple(map(type, axis)) != (str,) * len(axis)
            or axis.keys() != _PHASE_SET):
        return None
    order, idle, source = (basis['phase_order'], basis['idle_after_phase_sec'],
                           basis['native_green_sec'])
    if type(order) not in (list, tuple) or type(idle) is not dict or type(source) is not dict:
        return None
    order, idle_keys = tuple(order), tuple(idle)
    if (tuple(map(type, order)) != (str,) * len(order)
            or tuple(map(type, idle_keys)) != (str,) * len(idle_keys)
            or tuple(map(type, source)) != (str,) * len(source)
            or source.keys() != _PHASE_SET):
        return None
    strings = (basis['schema_version'], basis['kind'], basis['source_path'])
    if tuple(map(type, strings)) != (str, str, str) or type(basis['active_prog_no']) is not int:
        return None
    numbers = (raw.get('native_cycle_sec'), *(axis[p] for p in PHASES),
               basis['cycle_sec'], basis['amber_sec'], basis['all_red_sec'],
               *(source[p] for p in PHASES), basis['program_offset_sec'],
               basis['controller_offset_sec'], basis['reference_offset_sec'],
               *idle.values())
    if tuple(map(type, numbers)) != (float,) * len(numbers) or not all(map(math.isfinite, numbers)):
        return None
    return (strings, basis['active_prog_no'], order, idle_keys,
            struct.pack('!' + str(len(numbers)) + 'd', *numbers))


def _clock_key(control, cfg, signal, values, raw, contract, *, native_signature=None):
    net = cfg.network
    # Missing effective-total overrides can trigger the original cycle getter's
    # fallback diagnostics. Do not silently suppress those observable calls.
    if net.effective_green_total_by_signal.get(signal) is None:
        return None
    # Use current value operands, not cfg/control/spec identity or a stale mark.
    # Read these in the validation's original ordering.
    live = tuple(net.signal_live_phases(signal))
    minimum = float(net.green_min)
    total = net.signal_effective_green_total(signal)
    writer = contract['offset_writer']
    if writer in (offset_promotion.WRITER_EXPERIMENT, offset_promotion.WRITER_PRODUCTION):
        offset_operand = (getattr(control, 'offsets', None) or {}).get(signal, 0.0)
    elif writer == offset_promotion.WRITER_TEST_ONLY:
        diag = getattr(control, 'diagnostics', None) or {}
        offset_operand = (diag.get(offset_promotion.FORCED_ARM_TABLE_KEY),
                          *((k in diag, diag.get(k)) for k in offset_promotion.FORCED_ARM_DIAGNOSTIC_KEYS))
    else:
        offset_operand = None
    key = (signal, tuple(values[p] for p in PHASES), live, minimum, total,
           tuple(plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC), raw['_segments'], raw['_order'],
           contract['amber'], contract['all_red'], writer, offset_operand)
    payload = _native_payload(raw) if native_signature is None else native_signature
    if payload is not None:
        key += (payload, getattr(net, 'native_signal_minimum_policy', None), float(net.signal_cycle_length(signal)))
    return key


def _validated_clock(control, cfg, signal, values, raw, contract, *, reusable_plans=True):
    signature = None
    if reusable_plans and getattr(cfg.network, 'control_area_compact_signal_clock_cache', False):
        signature = _compact_native_signature(raw)
    key = _clock_key(control, cfg, signal, values, raw, contract, native_signature=signature)
    # Check every operand before dictionary equality. A custom numeric object
    # can hash/compare equal to a builtin while converting to a different value.
    cacheable = key is not None
    if cacheable:
        # The compact native signature has already proved every leaf's exact
        # type and snapshotted its value. Retain all original dynamic guards.
        dynamic = key[:6] + key[8:] if signature is None else key[:6] + key[8:12] + key[13:]
        cacheable = (_immutable(dynamic) and
                     _immutable_plan(key[6]) and _immutable_plan(key[7])) if reusable_plans else _immutable(key)
    if not cacheable:
        _STATS['clock_bypasses'] += 1
        return _uncached_clock(control, cfg, signal, values, raw, contract)
    hit = _CLOCKS.get(key)
    if hit is not None:
        _STATS['clock_hits'] += 1
        _CLOCKS.move_to_end(key)
        return hit
    _STATS['clock_misses'] += 1
    result = _uncached_clock(control, cfg, signal, values, raw, contract)
    _CLOCKS[key] = result
    if len(_CLOCKS) > MAX_CLOCKS:
        _CLOCKS.popitem(last=False)
    return result


@lru_cache(maxsize=MAX_INTERVALS)
def _finite_fraction(cycle, offset, lo, hi, duration, start, end):
    total = 0.0
    for sec in range(math.floor(start), math.ceil(end)):
        x = sec + offset
        pos = x - math.floor(x / cycle) * cycle
        if lo <= pos < hi:
            total += max(0.0, min(end, sec + 1) - max(start, sec))
    return total / duration



def phase_fraction(control, cfg, spec, urban_step_index=None):
    """Return None only when the existing native/monitor implementation owns it."""
    net = cfg.network
    if not enabled(net) or not spec.get("phase"):
        return None
    if spec.get("unsignalized"):
        return 1.0
    signal, _, phase = str(spec["phase"]).rpartition("_")
    contract = net.signal_actuation_contract
    raw = contract["nodes"].get(signal)
    if raw is None:
        return None
    values = {p: float(control.green_times.get(f"{signal}_{p}", 0.0)) for p in PHASES}
    cycle, offset, table = _validated_clock(control, cfg, signal, values, raw, contract)
    window = next((window for name, window in table if name == phase), None)
    if window is None:
        return 0.0
    lo, hi = window
    if urban_step_index is None:
        # Mean over the integer event grid's rational superperiod. Finite
        # rollouts below use actual absolute time, including VBS float FMod.
        units = round(cycle * 1000)
        stride = math.gcd(units, 1000)
        residue = round(offset * 1000) % stride
        active = math.ceil((round(hi * 1000) - residue) / stride) - math.ceil((round(lo * 1000) - residue) / stride)
        return active / (units // stride)
    duration = float(cfg.simulation.T_u_sec)
    start, end = float(urban_step_index) * duration, (float(urban_step_index) + 1) * duration
    if duration <= 0 or not math.isfinite(start + end):
        raise ValueError("invalid urban step interval")
    return _finite_fraction(cycle, offset, lo, hi, duration, start, end)


def wrap_clock(previous):
    def wrapped(control, cfg, spec, urban_step_index=None):
        value = phase_fraction(control, cfg, spec, urban_step_index)
        return previous(control, cfg, spec, urban_step_index) if value is None else value
    wrapped._rw_greenfrac_hotpath = getattr(previous, "_rw_greenfrac_hotpath", False)
    return wrapped


def install_candidates(cfg):
    """Reinstall in spawned workers too; every wrapper dispatches on call cfg."""
    if not enabled(cfg.network):
        return {}
    from src.models import state
    if not getattr(state.NetworkConfig.signal_green_max, "_physical_signal_contract", False):
        original_max = state.NetworkConfig.signal_green_max
        def signal_max(net, signal=None):
            if signal is not None and enabled(net):
                return bounds(net, signal)[1]
            return original_max(net, signal)
        signal_max._physical_signal_contract = True
        state.NetworkConfig.signal_green_max = signal_max
    for name in ("src.models.state", "src.controllers.wu_faithful_follower",
                 "src.controllers.priced_wu_link_controller", "src.controllers.local_signal_plant"):
        module = importlib.import_module(name)
        if not hasattr(module, "distribute_phase_green"):
            continue
        current = module.distribute_phase_green
        if getattr(current, "_physical_signal_contract", False):
            continue
        def distribution(net, primary, reference=None, signal=None, _original=current, **kw):
            basis = native_clock_basis(net, signal)
            if basis is not None and basis['kind'] == 'concurrent_p1_p2':
                head = net.signal_primary_phase(signal)
                out = dict(reference or basis['native_green_sec'])
                out[head] = float(primary)
                if head in ('p2', 'p4'):
                    out['p4' if head == 'p2' else 'p2'] = float(net.signal_effective_green_total(signal)) - float(primary)
                return project_vector(net, signal, out)
            out = _original(net, primary, reference, signal=signal, **kw)
            return project_vector(net, signal, out) if signal is not None else out
        distribution._physical_signal_contract = True
        module.distribute_phase_green = distribution
    from src.controllers import wu_faithful_follower as follower_module
    cls = follower_module.WuFaithfulFollower
    original_fractions = cls._offset_green_fractions_vec
    if not getattr(original_fractions, "_physical_signal_contract", False):
        def local_fractions(self, signal, greens, offset, substeps, start_idx):
            if not enabled(self.cfg.network):
                return original_fractions(self, signal, greens, offset, substeps, start_idx)
            model = self._local_models[signal]
            probe = state.ControlAction.uncontrolled(self.cfg)
            probe.green_times = {f"{signal}_{p}": float(v) for p, v in greens.items()}
            probe.offsets = {signal: float(offset)}
            probe.inflow_outflow_allocation = {}
            cache, out = {}, {}
            for movement in model.movements:
                spec = model.specs[movement]
                # The local cache may share full SG windows within a phase,
                # but an unsignalized peel-off is a different physical lever.
                key = (model.phase_of[movement], bool(spec.get("unsignalized")))
                if key not in cache:
                    cache[key] = [follower_module._phase_green_fraction(probe, self.cfg, spec, urban_step_index=start_idx + sub)
                                  for sub in range(substeps)]
                out[movement] = cache[key]
            return out
        local_fractions._physical_signal_contract = True
        cls._offset_green_fractions_vec = local_fractions
    return {"physical_signal_candidate_contract_installed": 1.0}


def install_controller(controller):
    """Call last in the canonical builder, after its existing green-box patch."""
    if not enabled(controller.cfg.network):
        return
    cls = type(controller)
    original = cls._phase_direction
    if not getattr(original, "_physical_signal_contract", False):
        def direction(self, signal, base, target, delta):
            basis = native_clock_basis(self.cfg.network, signal)
            if basis is not None and basis['kind'] == 'concurrent_p1_p2':
                return _native_direction(self.cfg.network, signal, base, target, delta)
            out = original(self, signal, base, target, delta)
            return project_vector(self.cfg.network, signal, out) if out is not None else None
        direction._physical_signal_contract = True
        cls._phase_direction = direction
    # The ordinary scalar expansion is projected before both local scoring and
    # commit; pair-exchange starts at that feasible seed and preserves its sum.
    follower_cls = type(controller.nash_solver)
    scalar_original = follower_cls._urban_green_candidates
    if not getattr(scalar_original, "_physical_signal_contract", False):
        def scalar_candidates(self, signal, state_arg, coupling, snapshot):
            out = scalar_original(self, signal, state_arg, coupling, snapshot)
            if not enabled(self.cfg.network):
                return out
            basis = native_clock_basis(self.cfg.network, signal)
            if basis is not None and basis['kind'] == 'concurrent_p1_p2':
                lo, hi = phase_bounds(self.cfg.network, signal)[self.cfg.network.signal_primary_phase(signal)]
                return list(dict.fromkeys(round(min(max(float(v), lo), hi), 3) for v in out))
            from src.models.state import clamp_primary_green
            return list(dict.fromkeys(round(clamp_primary_green(self.cfg.network, v, signal), 3) for v in out))
        scalar_candidates._physical_signal_contract = True
        follower_cls._urban_green_candidates = scalar_candidates
    current = follower_cls._phase_exchange_candidates
    if not getattr(current, "_physical_signal_contract", False):
        def exchange(self, signal, base, step):
            validate_vector(self.cfg.network, signal, base)
            basis = native_clock_basis(self.cfg.network, signal)
            if basis is not None and basis['kind'] == 'concurrent_p1_p2':
                return [v for target in ('p1', 'p2') for delta in (-float(step), float(step))
                        if (v := _native_direction(self.cfg.network, signal, base, target, delta)) is not None]
            if basis is not None:
                out = []
                for first in self.cfg.network.signal_live_phases(signal):
                    for second in self.cfg.network.signal_live_phases(signal):
                        if first == second: continue
                        v = dict(base)
                        v[first] = round(float(v[first])-float(step), 3)
                        v[second] = round(float(v[second])+float(step), 3)
                        try:
                            validate_vector(self.cfg.network, signal, v)
                        except ValueError:
                            continue
                        out.append(v)
                return out
            return [project_vector(self.cfg.network, signal, v) for v in current(self, signal, base, step)]
        exchange._physical_signal_contract = True
        follower_cls._phase_exchange_candidates = exchange


def _native_direction(net, signal, base, target, delta):
    if target not in ('p1', 'p2', 'p4') or not math.isfinite(float(delta)):
        return None
    out = dict(base)
    out[target] = round(float(out[target]) + float(delta), 3)
    if target in ('p2', 'p4'):
        other = 'p4' if target == 'p2' else 'p2'
        out[other] = round(float(out[other]) - float(delta), 3)
    try:
        validate_vector(net, signal, out)
    except ValueError:
        return None
    return out
