"""Fixed, physically realizable VSL zones for a native-signal causal experiment.

The runner supplies its effective allowed speed-distribution IDs. This module
does not fit an FD, optimize controls, or install any global runtime hooks.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import math


CONTROLLER = "diagnostic-vsl-profile"
UNCONTROLLED_KPH = 120.0


def build_control(cfg, ControlAction, tuning, mapping, allowed_vsl_speeds):
    """Build the complete zone profile; reject unsupported heads or speeds."""
    profile = tuning.get("diagnostic", {}).get("vsl_profile")
    if not isinstance(profile, Mapping):
        raise ValueError("diagnostic.vsl_profile must be a mapping ({} is the baseline)")
    if isinstance(allowed_vsl_speeds, str):
        allowed_vsl_speeds = allowed_vsl_speeds.split(",")
    try:
        physical_speeds = {float(value) for value in allowed_vsl_speeds}
        model_speeds = {float(value) for value in cfg.freeway_follower.vsl_set}
    except (TypeError, ValueError) as exc:
        raise ValueError("runner allowed VSL speeds must be supplied") from exc
    if not physical_speeds or not all(math.isfinite(v) and v > 0 for v in physical_speeds):
        raise ValueError("runner allowed VSL speeds must be finite and positive")
    allowed = physical_speeds & model_speeds
    if UNCONTROLLED_KPH not in allowed:
        raise ValueError("the native-signal VSL baseline requires validated 120 km/h")

    heads = getattr(cfg.network, "freeway_vsl_zone_heads", None) or {}
    head_of = getattr(cfg.network, "freeway_vsl_zone_head_of_cell", None) or {}
    physical_heads = {
        f"{seg['model_link']}__seg{int(seg['model_segment_index'])}"
        for seg in mapping.get("segments", [])
        if seg.get("dsds") and all(int(dsd.get("dsd_no", 0)) > 0 for dsd in seg["dsds"])
    }
    zone_values = {}
    for link in cfg.network.freeway_links:
        hs, cells = heads.get(str(link)), head_of.get(str(link))
        if not hs or not cells:
            raise ValueError(f"configured VSL zones required for {link}")
        for head in hs:
            key = f"{link}__seg{int(head)}"
            if key not in physical_heads:
                raise ValueError(f"VSL zone head has no physical DSD: {key}")
            zone_values[key] = UNCONTROLLED_KPH
    for key, value in profile.items():
        if key not in zone_values:
            raise ValueError(f"profile key is not a configured VSL zone head: {key}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"VSL speed must be numeric: {key}")
        if not math.isfinite(value) or value not in allowed:
            raise ValueError(f"unsupported VSL speed {value!r} for {key}; allowed={sorted(allowed)}")
        zone_values[key] = float(value)

    control = ControlAction.uncontrolled(cfg)
    control.vsl = {str(link): UNCONTROLLED_KPH for link in cfg.network.freeway_links}
    # Expand once so the CSV writer is correct even with a pre-install function
    # reference. The installed zone-aware reader obtains exactly the same values.
    for link in cfg.network.freeway_links:
        for cell, head in enumerate(head_of[str(link)]):
            control.vsl[f"{link}__seg{cell}"] = zone_values[f"{link}__seg{int(head)}"]
    control.ramp_metering = {
        str(ramp): float(cfg.network.ramp_capacity_veh_h[ramp])
        for ramp in cfg.network.ramps
    }
    if any(not math.isfinite(rate) or rate <= 0 for rate in control.ramp_metering.values()):
        raise ValueError("open-ramp profile requires positive finite ramp capacities")
    control.diagnostics.update({
        "diagnostic_vsl_profile_active": 1.0,
        "diagnostic_signal_original_vissim": 1.0,
        "diagnostic_ramps_forced_open": 1.0,
        "diagnostic_vsl_zone_profile": zone_values,
    })
    return control


def fixed_actuation(actuation):
    """Make the existing physical meter writer emit full-cycle green on all meters."""
    result = deepcopy(actuation)
    meters = result.setdefault("real_world_ramp_metering", {})
    cycle = float(meters.get("cycle_sec", 10.0))
    if cycle != 10.0:
        raise ValueError("diagnostic profile requires the runner's 10-second ramp cycle")
    # Setting both bounds to the cycle also works for unequal group capacities.
    # Proportional allocation avoids a measured-table optimizer or cached greens.
    meters.update(allocation="proportional", enabled=True, cycle_sec=cycle,
                  min_green_sec=cycle, max_green_sec=cycle)
    result.setdefault("real_world_signal_control", {})["enabled"] = False
    return result
