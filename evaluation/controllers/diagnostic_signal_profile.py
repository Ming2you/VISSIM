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
    replay_targets = spec.get("replay_recorded_targets", False)
    if type(replay_targets) is not bool:
        raise ValueError("recorded leader target replay requires a boolean flag")
    if replay_targets:
        for key in ("N_P_star", "N_UF_star"):
            value = recorded.get(key)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or (key == "N_UF_star" and value < 0)):
                raise ValueError(f"invalid recorded leader target: {key}")
            setattr(control, key, float(value))
    control.vsl = {str(link): 120.0 for link in cfg.network.freeway_links}
    replay_vsl = spec.get("replay_recorded_vsl", False)
    if type(replay_vsl) is not bool:
        raise ValueError("recorded VSL replay requires a boolean flag")
    if replay_vsl:
        values = recorded.get("vsl")
        links = tuple(map(str, cfg.network.freeway_links))
        head_of = getattr(cfg.network, "freeway_vsl_zone_head_of_cell", None) or {}
        if any(not head_of.get(link) for link in links):
            raise ValueError("recorded VSL replay requires configured zones")
        required = set(links) | {f"{link}__seg{i}" for link in links
                                 for i in range(len(head_of[link]))}
        if not isinstance(values, Mapping) or set(values) != required:
            raise ValueError("recorded VSL map must cover exactly every link and cell")
        allowed = set(cfg.freeway_follower.vsl_set)
        for key, value in values.items():
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value not in allowed):
                raise ValueError(f"unsupported recorded VSL speed: {key}")
        for link in links:
            for cell, head in enumerate(head_of[link]):
                if values[f"{link}__seg{cell}"] != values[f"{link}__seg{int(head)}"]:
                    raise ValueError(f"recorded VSL cells disagree within a zone: {link}")
        control.vsl = {key: float(value) for key, value in values.items()}
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
        plan = signal_group_plan.node_plan_from_json(node)
        cycle = signal_group_plan.node_cycle_sec(plan, greens, *plant_cycle.runner_clearance_sec())
        original_cycle = signal_group_plan.node_cycle_sec(plan, original_greens, *plant_cycle.runner_clearance_sec())
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
    from evaluation.controllers import physical_ramp_branches
    if getattr(cfg.network, 'physical_ramp_branches', None):
        # Eight-branch replay needs the original eight physical green commands;
        # ControlAction.uncontrolled() has no per-SG execution evidence.
        csv_source = Path(workspace_root) / spec['source_action_csv']
        if csv_source.resolve() != source.with_suffix('.csv').resolve():
            raise ValueError('Physical8 replay needs the recorded action sibling CSV')
        if hashlib.sha256(csv_source.read_bytes()).hexdigest() != spec['source_action_csv_sha256']:
            raise ValueError('Physical8 replay command CSV SHA-256 mismatch')
        control = physical_ramp_branches.read_recorded_control(control, cfg, source)
    return control


def fixed_actuation(actuation, tuning=None):
    result = diagnostic_profile.fixed_actuation(actuation, tuning)
    result["real_world_signal_control"].update(enabled=True, offset_writer="test_only")
    return result
