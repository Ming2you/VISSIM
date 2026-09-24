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
RULE_CONTROLLER = "diagnostic-rule-profile"
CONTROLLERS = (CONTROLLER, RAMP_CONTROLLER, RULE_CONTROLLER)
UNCONTROLLED_KPH = 120.0


def build_control(cfg, ControlAction, tuning, mapping, allowed_vsl_speeds, *,
                  rule_observation=None, rule_history=None):
    """Build the complete zone profile; reject unsupported heads or speeds."""
    if tuning.get("diagnostic", {}).get("rule_profile", {}).get("enabled") is True:
        return _build_rule_control(cfg, ControlAction, tuning, mapping, allowed_vsl_speeds,
                                   rule_observation, rule_history)
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
    if (tuning or {}).get("diagnostic", {}).get("rule_profile", {}).get("enabled") is True:
        if meters.get("amber_sec") != 0:
            raise ValueError("rule profile requires RED/GREEN-only meters")
        meters.update(allocation="diagnostic_rule_profile", enabled=True)
        result.setdefault("real_world_signal_control", {})["enabled"] = False
        return result
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
    rule = tuning.get("diagnostic", {}).get("rule_profile", {})
    if controller == RULE_CONTROLLER:
        if rule.get("enabled") is not True or rule.get("arm") not in ("none", "vsl", "rm", "both"):
            raise ValueError("diagnostic-rule-profile requires an enabled, explicit rule arm")
        if overrides is not None:
            raise ValueError("rule commands cannot also use fixed physical meter overrides")
    elif rule.get("enabled") is True:
        raise ValueError("enabled rule_profile requires --controller diagnostic-rule-profile")
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
    if settings.get("allocation") == "diagnostic_rule_profile":
        from evaluation.controllers import physical_ramp_branches
        if not physical_ramp_branches.enabled(cfg):
            raise ValueError("rule profile requires eight physical ramp branches")
        return physical_ramp_branches.physical_commands(control, cfg, actuation=actuation, mapping=mapping)
    if settings.get("allocation") != "diagnostic_profile":
        return None
    if float(settings.get("cycle_sec", 0)) != 10:
        raise ValueError("diagnostic physical meter commands require a 10-second cycle")
    return _physical_meter_rows(cfg, mapping, settings.get("diagnostic_green_sec"))


def _number(value, label, minimum=0.0, maximum=math.inf):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not minimum <= value <= maximum):
        raise ValueError(f"invalid {label}: {value!r}")
    return float(value)


def _observation(row):
    if not isinstance(row, Mapping):
        raise ValueError("rule detector observation must be a mapping")
    return (_number(row.get("flow_vph_per_lane"), "detector flow_vph_per_lane"),
            _number(row.get("occupancy_pct"), "detector occupancy_pct", maximum=100),
            _number(row.get("speed_kph"), "detector speed_kph"))


def rule_vsl_speed(observation, spec):
    """Photo decision tree; q and occupancy equality use the low-demand arm."""
    flow, occupancy, speed = _observation(observation)
    q_limit = _number(spec.get("flow_threshold_vph_per_lane"), "VSL flow threshold")
    o_limit = _number(spec.get("occupancy_threshold_pct"), "VSL occupancy threshold", maximum=100)
    thresholds = spec.get("speed_thresholds_kph")
    commands = spec.get("speed_commands_kph")
    if not isinstance(thresholds, (list, tuple)) or len(thresholds) != 2 or not isinstance(commands, (list, tuple)) or len(commands) != 3:
        raise ValueError("rule VSL requires two speed thresholds and three commands")
    low, high = [_number(value, "VSL speed threshold") for value in thresholds]
    slow, medium, fast = [_number(value, "VSL speed command") for value in commands]
    if not low < high or not 0 < slow < medium < fast:
        raise ValueError("rule VSL thresholds and commands must be strictly increasing")
    if flow <= q_limit and occupancy <= o_limit:
        return fast
    return fast if speed > high else medium if speed > low else slow


def mtfc_vsl_step(bottleneck, controlled_flow, spec, previous=None):
    """Carlson cascade equations, with explicit native measurement and actuator limits.

    qhat = qhat_prev + Kp*(e-e_prev) + Ki*e; b = b_prev + Kflow*(qhat-q).
    Density is an occupancy proxy using an offline-estimated effective vehicle length.
    Gains are supplied for the actual control interval; no implicit rescaling here.
    """
    _, occupancy, _ = _observation(bottleneck)
    flow, _, _ = _observation(controlled_flow)
    keys = ('effective_length_m', 'target_density', 'kp', 'ki', 'flow_ki',
            'flow_min', 'flow_max', 'reference_speed', 'max_speed_change')
    p = {k: _number(spec[k], 'MTFC ' + k) for k in keys}
    if not (p['effective_length_m'] > 0 and p['target_density'] > 0
            and p['flow_min'] < p['flow_max'] and p['flow_ki'] > 0):
        raise ValueError('Invalid MTFC density, length or flow parameters')
    allowed = [_number(x, 'MTFC allowed speed') for x in spec['allowed_speeds']]
    if not allowed or allowed != sorted(set(allowed)) or min(allowed) <= 0 or max(allowed) != p['reference_speed']:
        raise ValueError('MTFC speed support must be distinct and end at reference')
    density = occupancy * 10 / p['effective_length_m']
    error = p['target_density'] - density
    state = previous or {'error': error, 'target_flow': p['flow_max'], 'b': 1.0,
                         'speed': p['reference_speed']}
    last = _number(state['speed'], 'MTFC preceding actual command')
    if last not in allowed:
        raise ValueError('MTFC previous command outside actual support')
    old_error = float(state['error'])
    if not math.isfinite(old_error): raise ValueError('Nonfinite MTFC history')
    target_raw = (_number(state['target_flow'], 'MTFC preceding flow')
                  + p['kp'] * (error-old_error) + p['ki'] * error)
    target = min(p['flow_max'], max(p['flow_min'], target_raw))
    b_raw = _number(state['b'], 'MTFC preceding b', maximum=1) + p['flow_ki'] * (target-flow)
    feasible = [v for v in allowed if abs(v-last) <= p['max_speed_change']]
    if not feasible: raise ValueError('Empty MTFC actual-command trust region')
    # Saturate the integral state at the available temporal actuator limits.
    # Preserve sub-quantization increments within them, avoiding an artificial deadband.
    b = min(max(feasible)/p['reference_speed'], max(min(feasible)/p['reference_speed'], b_raw))
    speed = min(feasible, key=lambda v: (abs(v-b*p['reference_speed']), abs(v-last), -v))
    next_state = {'error': error, 'target_flow': target, 'b': b, 'speed': speed}
    audit = {'density_proxy': density, 'density_error': error, 'measured_flow': flow,
             'target_raw': target_raw, 'target_flow': target, 'b_raw': b_raw, 'b_applied_state': b,
             'previous_speed': last, 'speed': speed, 'feasible_speeds': feasible}
    return speed, next_state, audit


def alinea_meter_step(table, previous_green, previous_request, params, occupancy,
                      minimum_green, max_green_change):
    """Shared rule arithmetic, independent of plant initialization and COM."""
    previous_green = _number(previous_green, "previous actual green", maximum=10)
    previous_request = _number(previous_request, "previous ALINEA request")
    if previous_green != int(previous_green) or str(int(previous_green)) not in table:
        raise ValueError("previous actual green is not representable")
    raw = request = float(table["10"])
    if params is not None:
        params = {k: _number(params[k], "ALINEA " + k) for k in
                  ("gain_vph_per_pct", "target_occupancy_pct", "min_rate_vph", "max_rate_vph")}
        occupancy = _number(occupancy, "occupancy percent", maximum=100)
        if not 0 < params["target_occupancy_pct"] <= 100 or params["gain_vph_per_pct"] <= 0:
            raise ValueError("ALINEA needs positive gain and target occupancy")
        if not 0 <= params["min_rate_vph"] < params["max_rate_vph"] <= max(table.values()):
            raise ValueError("ALINEA request bounds exceed service range")
        raw = previous_request + params["gain_vph_per_pct"] * (params["target_occupancy_pct"] - occupancy)
        request = min(params["max_rate_vph"], max(params["min_rate_vph"], raw))
    choices = [int(g) for g in table if (int(g) == 0 or int(g) >= minimum_green)
               and abs(int(g) - previous_green) <= max_green_change]
    if not choices:
        raise ValueError("no physical green in trust region")
    green = min(choices, key=lambda g: (abs(table[str(g)] - request), abs(g - previous_green), -g))
    next_request = min(max(table[str(g)] for g in choices), max(min(table[str(g)] for g in choices), request))
    return green, next_request, raw, request


def _build_rule_control(cfg, ControlAction, tuning, mapping, allowed, observation, history):
    from evaluation.controllers import physical_ramp_branches
    validate_controller(RULE_CONTROLLER, tuning)
    spec = tuning["diagnostic"]["rule_profile"]
    if not physical_ramp_branches.enabled(cfg):
        raise ValueError("rule profile requires the installed eight-ramp physical plant")
    ramps = cfg.network.physical_ramp_branches
    if len(ramps["ramps"]) != 8 or ramps["cycle_sec"] != 10 or ramps["max_green_change_sec"] != 2:
        raise ValueError("rule profile must retain eight meters, 10-second cycle and actual-green +/-2")
    reference_speed = _number(spec.get("reference_speed_kph"), "rule reference speed")
    vsl_spec = spec.get("vsl_rule", {})
    # Validate the configured decision tree even in its fixed-reference arm.
    if rule_vsl_speed({"flow_vph_per_lane": 0, "occupancy_pct": 0, "speed_kph": 0}, vsl_spec) != reference_speed:
        raise ValueError("rule reference speed must equal the highest VSL rule command")
    physical_speeds = {float(value) for value in (allowed.split(",") if isinstance(allowed, str) else allowed)}
    command_speeds = {float(value) for value in cfg.freeway_follower.vsl_set}
    missing = set(vsl_spec["speed_commands_kph"]) - (physical_speeds & command_speeds)
    if missing:
        raise ValueError(f"rule commands missing from physical/model VSL sets: {sorted(missing)}")
    heads = {f"{link}__seg{head}" for link, values in cfg.network.freeway_vsl_zone_heads.items() for head in values}
    zone_values = dict.fromkeys(heads, reference_speed)
    arm = spec["arm"]
    if arm != "none":
        if not isinstance(observation, Mapping) or any(observation.get(key) != value for key, value in (
                ("occupancy_unit", "percent"), ("flow_unit", "veh/h/lane"), ("speed_unit", "km/h"))):
            raise ValueError("explicit detector units percent, veh/h/lane and km/h are required")
    if arm in ("vsl", "both"):
        observed = observation.get("vsl_zones", {})
        if not isinstance(observed, Mapping) or set(observed) != heads:
            raise ValueError("rule VSL observation must cover exactly all configured zone heads")
        zone_values = {key: rule_vsl_speed(observed[key], vsl_spec) for key in sorted(heads)}
    fixed = deepcopy(tuning)
    fixed["diagnostic"].pop("rule_profile")
    fixed["diagnostic"]["vsl_profile"] = zone_values
    control = build_control(cfg, ControlAction, fixed, mapping, allowed)
    # Urban SG rows stay native, but the plant replay must describe their real
    # phase lengths and clock, not ControlAction.uncontrolled's nominal plan.
    from evaluation.controllers.vissim_stackelberg_adapter import represent_native_no_control_signals
    control = represent_native_no_control_signals(control, cfg)
    native_reference = control.diagnostics.get("no_control_native_signal_reference")
    if native_reference is not None:
        control.diagnostics["diagnostic_rule_native_signal_reference"] = deepcopy(native_reference)
    control.vsl.update({str(link): reference_speed for link in cfg.network.freeway_links})
    history = history if history is not None else {
        "actual_green_sec": dict.fromkeys(ramps["ramps"], 10.0),
        "requested_rate_vph": {mid: row["service_by_green_veh_h"]["10"] for mid, row in ramps["ramps"].items()}}
    if not isinstance(history, Mapping):
        raise ValueError("rule history must include actual greens and bounded continuous rate requests")
    for key in ("actual_green_sec", "requested_rate_vph"):
        if not isinstance(history.get(key), Mapping) or set(history[key]) != set(ramps["ramps"]):
            raise ValueError(f"rule history requires all eight meters: {key}")
    reference = control.copy()
    for mid, row in ramps["ramps"].items():
        green = _number(history["actual_green_sec"][mid], "previous actual green", maximum=10)
        if green != int(green) or str(int(green)) not in row["service_by_green_veh_h"]:
            raise ValueError("previous actual green is not representable by the service table")
        reference.diagnostics["rw_meter_green_"+mid] = green
        reference.ramp_metering[mid] = row["service_by_green_veh_h"][str(int(green))]
    reference = physical_ramp_branches.prepare_control(reference, cfg)
    greens, requests, audit = {}, {}, {}
    if arm in ("rm", "both"):
        observed = observation.get("ramps", {})
        if not isinstance(observed, Mapping) or set(observed) != set(ramps["ramps"]):
            raise ValueError("ALINEA requires downstream observations for all eight ramps")
        alinea = spec.get("alinea", {})
    for mid, row in ramps["ramps"].items():
        previous_green = reference.diagnostics["rw_meter_green_"+mid]
        table = row["service_by_green_veh_h"]
        previous_request = _number(history["requested_rate_vph"][mid], "previous ALINEA request")
        params, occupancy = None, None
        if arm in ("rm", "both"):
            _, occupancy, _ = _observation(observed[mid])
            params = {}
            for key in ("gain_vph_per_pct", "target_occupancy_pct", "min_rate_vph", "max_rate_vph"):
                value = alinea.get(key)
                if isinstance(value, Mapping):
                    if set(value) != set(ramps["ramps"]):
                        raise ValueError(f"ALINEA {key} must cover all eight meters")
                    value = value[mid]
                params[key] = _number(value, "ALINEA "+key)
            if not 0 < params["target_occupancy_pct"] <= 100 or params["gain_vph_per_pct"] <= 0:
                raise ValueError("ALINEA needs positive gain and a target occupancy in percent")
            if not params["min_rate_vph"] < params["max_rate_vph"] <= max(table.values()):
                raise ValueError("ALINEA request bounds must lie within physical service range")
        green, next_request, raw, request = alinea_meter_step(
            table, previous_green, previous_request, params, occupancy,
            ramps["minimum_green_sec"], ramps["max_green_change_sec"])
        greens[mid], requests[mid] = float(green), next_request
        audit[mid] = {"previous_actual_green_sec": previous_green, "previous_request_vph": previous_request,
                      "raw_requested_rate_vph": raw, "bounded_requested_rate_vph": request,
                      "next_integrator_rate_vph": next_request,
                      "applied_green_sec": float(green), "applied_service_ceiling_vph": table[str(green)],
                      "csv_command_rate_vph": float(green)*row["capacity_vph"]/ramps["cycle_sec"]}
    control = physical_ramp_branches.candidate_from_greens(reference, reference, cfg, greens)
    control.diagnostics.update({"diagnostic_rule_profile_active": 1.0, "diagnostic_rule_arm": arm,
        "diagnostic_physical_meter_green_sec": greens,
        "diagnostic_ramps_forced_open": float(all(g == 10 for g in greens.values())),
        "diagnostic_rule_meter_audit": audit,
        "diagnostic_rule_observation": deepcopy(observation),
        "diagnostic_rule_next_history": {"actual_green_sec": greens, "requested_rate_vph": requests},
        "diagnostic_rule_rate_semantics": "bounded ALINEA request; discrete model service ceiling; CSV encoding; none is measured flow"})
    return control
