"""Exact selected function bodies from dd13e08; regression reference only.

No adapter or vendor model is copied. Runtime imports supply unchanged types,
plan writer, offset authority and enabled flag; these bodies are pinned below.
"""
import math
from functools import lru_cache
from evaluation.controllers import plant_cycle, signal_group_plan, offset_promotion
from evaluation.controllers.signal_actuation_contract import enabled, PHASES

def bounds(net, signal):
    low = max(float(net.green_min), plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC[0])
    total = float(net.signal_effective_green_total(signal))
    count = len(net.signal_live_phases(signal))
    high = min(plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC[1], total - (count - 1) * low)
    if not count or not all(math.isfinite(v) for v in (low, high, total)):
        raise ValueError(f"{signal}: invalid signal budget")
    if not count * low <= total <= count * high:
        raise ValueError(f"{signal}: green box cannot contain budget {total}")
    return low, high, total


def validate_vector(net, signal, values):
    if not enabled(net):
        return
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


@lru_cache(maxsize=16384)
def _phase_windows(segments, order, greens, clearance):
    """The existing plan writer is the only phase-layout implementation."""
    # These are the actual selected plan's segments, not another phase clock.
    plan = signal_group_plan.NodePlan("clock", 0.0, dict(segments), {}, {}, {}, (), ())
    rows = signal_group_plan.plan_windows(plan, dict(zip(PHASES, greens)), order, clearance, 0.0)
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
    cycle = round(sum(values.values()) + len(net.signal_live_phases(signal)) * (contract["amber"] + contract["all_red"]), 6)
    return round(offset_promotion.written_offset_sec(signal, control, contract["offset_writer"], cycle_sec=cycle), 3)


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
    validate_vector(net, signal, values)
    offset = written_offset_sec(control, cfg, signal)
    # Writer cycle is recomputed from the serialized vector, not separately
    # rounded to whole seconds. E.g. 150.001 is a legal CSV cycle.
    cycle = round(sum(values.values()) + len(net.signal_live_phases(signal)) * (contract["amber"] + contract["all_red"]), 6)
    if not math.isfinite(offset) or not 0.0 <= offset <= cycle:
        raise ValueError(f"{signal}: written offset outside CSV range")
    table = _phase_windows(raw["_segments"], raw["_order"],
                           tuple(values[p] for p in PHASES), contract["amber"] + contract["all_red"])
    window = table.get(phase)
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
    total = 0.0
    for sec in range(math.floor(start), math.ceil(end)):
        x = sec + offset
        # Match the actual VBS FMod expression; Python % differs at some
        # decimal cycle boundaries because it uses a different remainder path.
        pos = x - math.floor(x / cycle) * cycle
        if lo <= pos < hi:
            total += max(0.0, min(end, sec + 1) - max(start, sec))
    return total / duration

