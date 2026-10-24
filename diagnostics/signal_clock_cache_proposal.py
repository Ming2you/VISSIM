"""Unapplied value-key caches for the existing selected physical signal clock.

Only pure clock values are retained. No candidate/state/cfg object is retained,
no receiving/service/ready operation is cached, and no model formula changes.
"""
from collections import OrderedDict
from functools import lru_cache
import math

from evaluation.controllers import signal_actuation_contract as original
from evaluation.controllers import offset_promotion, plant_cycle

PHASES = original.PHASES
MAX_CLOCKS = 16384
MAX_INTERVALS = 131072
MAX_PLAN_TREES = 1024
_PLAN_TREES = OrderedDict()
_CLOCKS = OrderedDict()
_STATS = {'clock_hits': 0, 'clock_misses': 0, 'clock_bypasses': 0}


def clear():
    _CLOCKS.clear()
    _PLAN_TREES.clear()
    _finite_fraction.cache_clear()
    for key in _STATS:
        _STATS[key] = 0


def stats():
    return {**_STATS, 'clocks': len(_CLOCKS),
            'max_clocks': MAX_CLOCKS, 'plan_trees': len(_PLAN_TREES),
            'max_plan_trees': MAX_PLAN_TREES, 'finite': _finite_fraction.cache_info()._asdict()}


def _uncached_clock(control, cfg, signal, values, raw, contract):
    # Preserve original validation/rounding order, including duplicate writer
    # validation. A miss computes exactly the existing clock, not a new clock.
    original.validate_vector(cfg.network, signal, values)
    offset = original.written_offset_sec(control, cfg, signal)
    cycle = round(sum(values.values()) + len(cfg.network.signal_live_phases(signal)) *
                  (contract['amber'] + contract['all_red']), 6)
    if not math.isfinite(offset) or not 0.0 <= offset <= cycle:
        raise ValueError(f'{signal}: written offset outside CSV range')
    table = original._phase_windows(raw['_segments'], raw['_order'],
        tuple(values[p] for p in PHASES), contract['amber'] + contract['all_red'])
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


def _clock_key(control, cfg, signal, values, raw, contract):
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
    return key


def _validated_clock(control, cfg, signal, values, raw, contract, *, reusable_plans=True):
    key = _clock_key(control, cfg, signal, values, raw, contract)
    # Check every operand before dictionary equality. A custom numeric object
    # can hash/compare equal to a builtin while converting to a different value.
    cacheable = key is not None
    if cacheable:
        cacheable = (_immutable(key[:6] + key[8:]) and
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


def _fraction(control, cfg, spec, urban_step_index, *, clock_cache, reusable_plans=True):
    net = cfg.network
    if not original.enabled(net) or not spec.get('phase'):
        return None
    if spec.get('unsignalized'):
        return 1.0
    signal, _, phase = str(spec['phase']).rpartition('_')
    contract = net.signal_actuation_contract
    raw = contract['nodes'].get(signal)
    if raw is None:
        return None
    values = {p: float(control.green_times.get(f'{signal}_{p}', 0.0)) for p in PHASES}
    if clock_cache:
        cycle, offset, table = _validated_clock(control, cfg, signal, values, raw, contract, reusable_plans=reusable_plans)
    else:
        cycle, offset, table = _uncached_clock(control, cfg, signal, values, raw, contract)
    window = next((window for name, window in table if name == phase), None)
    if window is None:
        return 0.0
    lo, hi = window
    if urban_step_index is None:
        units = round(cycle * 1000)
        stride = math.gcd(units, 1000)
        residue = round(offset * 1000) % stride
        active = math.ceil((round(hi * 1000) - residue) / stride) - math.ceil((round(lo * 1000) - residue) / stride)
        return active / (units // stride)
    duration = float(cfg.simulation.T_u_sec)
    start, end = float(urban_step_index) * duration, (float(urban_step_index) + 1) * duration
    if duration <= 0 or not math.isfinite(start + end):
        raise ValueError('invalid urban step interval')
    return _finite_fraction(cycle, offset, lo, hi, duration, start, end)


def finite_only(control, cfg, spec, urban_step_index=None):
    return _fraction(control, cfg, spec, urban_step_index, clock_cache=False)


def validated_clock(control, cfg, spec, urban_step_index=None):
    return _fraction(control, cfg, spec, urban_step_index, clock_cache=True)


def validated_clock_full_check(control, cfg, spec, urban_step_index=None):
    return _fraction(control, cfg, spec, urban_step_index, clock_cache=True, reusable_plans=False)


def wrap(previous, candidate=validated_clock):
    def wrapped(control, cfg, spec, urban_step_index=None):
        value = candidate(control, cfg, spec, urban_step_index)
        return previous(control, cfg, spec, urban_step_index) if value is None else value
    return wrapped
