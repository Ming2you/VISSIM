"""Freeze a recorded plan and apply explicit, cycle-preserving authority tests."""
from __future__ import annotations
from collections.abc import Mapping
import hashlib
import json
import math
from pathlib import Path

from evaluation.controllers import diagnostic_profile, offset_promotion, plant_cycle, signal_group_plan

CONTROLLER = "diagnostic-signal-profile"


def build_control(cfg, ControlAction, tuning, plan_table, workspace_root):
    spec = tuning.get("diagnostic", {}).get("signal_profile", {})
    source = Path(workspace_root) / spec["green_action_json"]
    payload = source.read_bytes()
    if hashlib.sha256(payload).hexdigest() != spec.get("green_action_sha256"):
        raise ValueError("frozen green action SHA-256 mismatch")
    recorded = json.loads(payload)
    plan_hash = hashlib.sha256(json.dumps(plan_table, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False).encode("utf-8")).hexdigest()
    if plan_hash != spec.get("plan_content_sha256"):
        raise ValueError("frozen SG plan content SHA-256 mismatch")
    control = ControlAction.uncontrolled(cfg)
    control.vsl = {str(link): 120.0 for link in cfg.network.freeway_links}
    shifts = spec.get("relative_offset_sec", {})
    if not isinstance(shifts, Mapping):
        raise ValueError("relative_offset_sec must be a signal-to-seconds mapping")
    signals = {str(node["node_id"]): node for node in plan_table["controllers"].values()}
    if set(shifts) - set(signals):
        raise ValueError("relative offset references an unknown signal")
    base = spec.get("base_writer_offsets_sec", {})
    if not isinstance(base, Mapping) or set(base) - set(signals):
        raise ValueError("base_writer_offsets_sec references an unknown signal")
    green_changes = spec.get("green_delta_sec", {})
    known_green_keys = {f"{signal}_{phase}" for signal in signals for phase in signal_group_plan.MODEL_PHASES}
    if not isinstance(green_changes, Mapping) or set(green_changes) - known_green_keys:
        raise ValueError("green_delta_sec references an unknown signal phase")
    offsets = {}
    for signal, node in signals.items():
        greens = {}
        original_greens = {}
        for phase in signal_group_plan.MODEL_PHASES:
            key = f"{signal}_{phase}"
            raw = float(recorded["green_times"][key])
            if not math.isfinite(raw) or raw < 0:
                raise ValueError(f"invalid frozen green: {key}")
            original_greens[phase] = plant_cycle.written_axis_green_sec(raw) if raw > 0 else 0.0
            change = green_changes.get(key, 0.0)
            if isinstance(change, bool) or not isinstance(change, (int, float)) or not math.isfinite(change):
                raise ValueError(f"invalid green delta: {key}")
            target = original_greens[phase] + change
            if change and (original_greens[phase] == 0 or not 5.0 <= target <= 90.0):
                raise ValueError(f"green delta changes a dead phase or exceeds writer bounds: {key}")
            greens[phase] = target
            control.green_times[key] = greens[phase]
        expected = tuple(phase for phase in signal_group_plan.MODEL_PHASES
                         if node["phase_signal_groups"].get(phase) and node["axis_green_sec"].get(phase, 0) > 0)
        if signal_group_plan.live_phases(greens) != expected:
            raise ValueError(f"frozen green phases differ from current SG plan: {signal}")
        cycle = signal_group_plan.plan_cycle_sec(greens, *plant_cycle.runner_clearance_sec())
        original_cycle = signal_group_plan.plan_cycle_sec(original_greens, *plant_cycle.runner_clearance_sec())
        if not math.isclose(cycle, original_cycle, rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"green deltas must preserve the written cycle: {signal}")
        value, change = float(base.get(signal, 0)), float(shifts.get(signal, 0))
        if not math.isfinite(value) or not math.isfinite(change):
            raise ValueError(f"non-finite forced offset: {signal}")
        offsets[signal] = (value + change) % cycle
    control.offsets = offsets
    control.diagnostics.update({
        "diagnostic_signal_profile_active": 1.0,
        "diagnostic_green_action_sha256": spec["green_action_sha256"],
        "diagnostic_offset_sign": "positive writer offset advances the frozen cycle",
        "diagnostic_green_delta_sec": dict(green_changes),
        offset_promotion.FORCED_ARM_TABLE_KEY: json.dumps(offsets, sort_keys=True),
    })
    return control


def fixed_actuation(actuation):
    result = diagnostic_profile.fixed_actuation(actuation)
    result["real_world_signal_control"].update(enabled=True, offset_writer="test_only")
    return result
