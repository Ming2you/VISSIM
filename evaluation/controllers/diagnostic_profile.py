"""Fixed, physically realizable VSL zones for a native-signal causal experiment.

The runner supplies its effective allowed speed-distribution IDs. This module
does not fit an FD, optimize controls, or install any global runtime hooks.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import math


CONTROLLER = "diagnostic-vsl-profile"
RAMP_CONTROLLER = "diagnostic-ramp-profile"
CONTROLLERS = (CONTROLLER, RAMP_CONTROLLER)
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
    overrides = tuning.get("diagnostic", {}).get("physical_meter_green_sec")
    if overrides is not None:
        rows = _physical_meter_rows(cfg, mapping, overrides)
        control.ramp_metering = {
            key: sum(float(row["rate_vph"]) for row in rows.values() if row["model_ramp_key"] == key)
            for key in cfg.network.ramps
        }
        control.diagnostics.update({
            "diagnostic_physical_meter_green_sec": {key: row["green_sec"] for key, row in rows.items()},
            "diagnostic_ramps_forced_open": float(all(row["green_sec"] == 10 for row in rows.values())),
            "diagnostic_meter_rate_semantics": "CSV command encoding: green * physical capacity / 10; not measured throughput",
        })
    return control



def fixed_actuation(actuation, tuning=None):
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
    diagnostic = (tuning or {}).get("diagnostic", {})
    if "physical_meter_green_sec" in diagnostic:
        # This is a separate physical-command contract, not an optimizer cache.
        meters.update(allocation="diagnostic_profile", min_green_sec=0.0,
                      diagnostic_green_sec=deepcopy(diagnostic["physical_meter_green_sec"]))
    result.setdefault("real_world_signal_control", {})["enabled"] = False
    return result



def validate_controller(controller, tuning):
    """A nonconstant meter requires the runner's event mode, not static VSL mode."""
    overrides = tuning.get("diagnostic", {}).get("physical_meter_green_sec")
    if controller == RAMP_CONTROLLER and not isinstance(overrides, Mapping):
        raise ValueError("diagnostic-ramp-profile requires physical_meter_green_sec ({} means all open)")
    if controller == CONTROLLER and overrides is not None:
        if not isinstance(overrides, Mapping) or any(value != 10 for value in overrides.values()):
            raise ValueError("nonconstant physical meters require --controller diagnostic-ramp-profile")


def _physical_meter_rows(cfg, mapping, overrides):
    if not isinstance(overrides, Mapping):
        raise ValueError("physical_meter_green_sec must map physical meter IDs to integer seconds")
    meters = mapping.get("ramp_meters", [])
    if not isinstance(meters, list) or not meters:
        raise ValueError("physical ramp-meter mapping is required")
    out, addresses = {}, set()
    for meter in meters:
        mid, key = str(meter.get("id", "")), str(meter.get("model_ramp_key", ""))
        if not mid or mid in out or key not in cfg.network.ramps:
            raise ValueError("missing, duplicate or unknown physical meter/model ramp identity")
        sc, sg = int(meter.get("sc_no", 0)), int(meter.get("sg_no", 0))
        if sc <= 0 or sg <= 0 or (sc, sg) in addresses:
            raise ValueError(f"invalid or duplicated physical meter SC/SG: {mid}")
        addresses.add((sc, sg))
        capacity = float(meter.get("capacity_vph", 0))
        if not math.isfinite(capacity) or capacity <= 0 or float(meter.get("cycle_sec", 10)) != 10:
            raise ValueError(f"invalid physical capacity or ramp cycle: {mid}")
        green = overrides.get(mid, 10.0)
        if isinstance(green, bool) or not isinstance(green, (int, float)) or not math.isfinite(green) or not 0 <= green <= 10 or green != round(green):
            raise ValueError(f"physical meter green must be an integer in [0,10]: {mid}")
        out[mid] = {"sc_no": float(sc), "sg_no": float(sg), "model_ramp_key": key,
                    "green_sec": float(green), "rate_vph": float(green) * capacity / 10.0}
    if set(overrides) - set(out):
        raise ValueError("physical_meter_green_sec references an unknown physical meter")
    for row in out.values():
        row["group_rate_vph"] = sum(float(other["rate_vph"]) for other in out.values()
                                    if other["model_ramp_key"] == row["model_ramp_key"])
    return out


def physical_meter_actions(control, cfg, actuation, mapping):
    """Return explicit physical commands, or None for the unchanged normal writer."""
    settings = actuation.get("real_world_ramp_metering", {})
    if settings.get("allocation") != "diagnostic_profile":
        return None
    if float(settings.get("cycle_sec", 0)) != 10:
        raise ValueError("diagnostic physical meter commands require a 10-second cycle")
    return _physical_meter_rows(cfg, mapping, settings.get("diagnostic_green_sec"))
