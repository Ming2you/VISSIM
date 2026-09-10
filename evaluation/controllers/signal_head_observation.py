"""Validated per-head discharge lower bounds; no saturation/EWMA claim."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

def number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a measured number")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Nonfinite or negative head observation")
    return value


def settings(section):
    """Configuration is the only switch; ON has explicit quality thresholds."""
    if not isinstance(section, dict) or type(section.get("enabled")) is not bool:
        raise ValueError("head_observation requires an object with boolean enabled")
    if set(section) - {"enabled", "min_green_sec", "min_crossings"}:
        raise ValueError("Unknown head observation option")
    if not section["enabled"]:
        return {"enabled": False}
    if any(isinstance(section.get(k), (str, bool)) for k in ("min_green_sec", "min_crossings")):
        raise ValueError("Head observation thresholds must be numeric")
    green, count = number(section["min_green_sec"]), number(section["min_crossings"])
    if green <= 0 or green != int(green) or count <= 0 or count != int(count):
        raise ValueError("Positive integer minimum green seconds/crossings required")
    return {"enabled": True, "min_green_sec": green, "min_crossings": count}


def validate_provenance(raw, window, options):
    """Reject independent environment activation or changed source bytes."""
    reference = raw["run_provenance"]
    manifest = json.loads(Path(reference["manifest_path"]).read_text(encoding="utf-8-sig"))
    if manifest["run_id"] != reference["run_id"]:
        raise ValueError("Head observation run identity mismatch")
    evidence = manifest["signal_observation"]
    if evidence["config_key"] != "urban.capacity.head_observation" or evidence["options"] != options:
        raise ValueError("Head observation effective configuration mismatch")
    if manifest["env"].get("RW_SIGNAL_OBSERVATION") != "1" or manifest["env"].get("RW_QUEUE_WINDOW") != "1":
        raise ValueError("Head collector transport was not configured by runner")
    chain = evidence["config_chain"]
    if not chain or chain[0]["sha256"] != manifest["files"]["tuning"]["sha256"]:
        raise ValueError("Head observation tuning provenance mismatch")
    for source in [*chain, manifest["files"]["network"]]:
        if hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Head observation pinned source changed")
    if window is not None and window.get("config_sha256") != chain[0]["sha256"]:
        raise ValueError("Head observation collector/consumer source mismatch")
    if Path(raw["network_path"]).resolve() != Path(manifest["files"]["network"]["path"]).resolve():
        raise ValueError("Head observation physical network mismatch")
    identity = {"run_id": reference["run_id"], "config_chain_sha256": [s["sha256"] for s in chain],
                "network_sha256": manifest["files"]["network"]["sha256"], "quality": options}
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def physical_groups(network_path, plan):
    """Only unique physical lane/head and unique selected phase are eligible."""
    tree = ET.parse(network_path).getroot()
    lanes = defaultdict(list)
    for head in tree.findall("./signalHeads/signalHead"):
        link, lane = head.get("lane").split()
        lanes[link, lane].append(head)
    result = defaultdict(list)
    for (link, lane), heads in lanes.items():
        if len(heads) != 1:
            continue
        head = heads[0]
        if head.get("allVehTypes") != "true":
            continue
        sc, sg = head.get("sg").split()
        controller = (plan or {}).get("controllers", {}).get(sc, {})
        phases = [p for p, groups in controller.get("phase_signal_groups", {}).items() if sg in map(str, groups)]
        if len(phases) != 1 or sg in map(str, controller.get("midblock_native_signal_groups", [])):
            continue
        result[link, phases[0]].append({
            "head_id": head.get("no"), "link": link, "lane": int(lane),
            "position_m": float(head.get("pos")), "sc": sc, "sg": sg})
    return dict(result)


def install(cfg, state_json, previous_path, caps, plan, distribute, options):
    """Carry a verified prior; accept min of two contiguous independent windows."""
    options = settings(options)
    if not options["enabled"]:
        raise ValueError("Head observation consumer requires enabled configuration")
    window = state_json.get("local_observation", {}).get("signal_observation_window")
    context = validate_provenance(state_json, window, options)
    context_key = "head_provenance_" + context
    now = number(state_json["sim_sec"])
    geometry = physical_groups(state_json["network_path"], plan)
    try:
        previous = json.loads(Path(previous_path).read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        previous = {}
    prior = {**previous.get("diagnostics", {}), **previous.get("metadata", {})}
    has_prior = any(k.startswith(("head_discharge_floor_", "head_candidate_")) for k in prior)
    prior_valid = False
    if has_prior:
        try:
            previous_time = number(previous["metadata"]["sim_sec"])
            prior_valid = (previous["run_provenance"]["run_id"] == state_json["run_provenance"]["run_id"]
                           and prior.get(context_key) == 1.0
                           and number(prior["head_observation_snapshot_sec"]) == previous_time
                           and previous_time < now
                           and (window is None or previous_time <= number(window["start_sec"]))
                           and all(number(v) == previous_time for k, v in prior.items()
                                   if k.startswith("head_candidate_end_")))
        except (KeyError, TypeError, ValueError):
            prior_valid = False
    if not prior_valid:
        prior = {}
    metadata = {"measured_capacity_enabled": 1.0, "head_observation_enabled": 1.0,
                context_key: 1.0, "head_observation_snapshot_sec": now,
                "head_observation_prior_discarded": float(has_prior and not prior_valid),
                "head_observation_groups_updated": 0.0, "head_observation_groups_carried": 0.0,
                "head_observation_missing_window": float(window is None),
                "head_observation_invalid_window": 0.0, "head_observation_short_exposure": 0.0,
                "head_observation_missing_crossings": 0.0, "head_observation_unknown_link": 0.0,
                "head_observation_no_model_members": 0.0, "head_observation_waiting_second_window": 0.0}
    valid = False
    observed = {}
    start = end = 0.0
    if window is not None:
        if window.get("schema") != "physical-head-window/v1":
            raise ValueError("Unsupported physical head observation schema")
        start, end = number(window["start_sec"]), number(window["end_sec"])
        steps = number(window["transition_count"])
        if (end != number(state_json["sim_sec"]) or end < start
                or steps != end - start or window.get("cadence_sec") != 1
                or window.get("exposure_method") != "actual_left_step_hold"):
            raise ValueError("Head observation time/exposure contract mismatch")
        valid = window.get("clock_complete") is True and steps > 0
        metadata["head_observation_invalid_window"] = float(not valid)
        for row in window.get("heads", []):
            head_id = str(row["head_id"])
            if head_id in observed:
                raise ValueError("Duplicate physical head observation")
            observed[head_id] = row
    groups = [{"stopline_link": link, "signal": "SC" + heads[0]["sc"]}
              for (link, _), heads in geometry.items()]
    estimates = {}
    for (link, phase), heads in sorted(geometry.items()):
        identity = hashlib.sha256(json.dumps({"heads": heads, "context": context}, sort_keys=True).encode()).hexdigest()[:16]
        suffix = f"{link}_{phase}_{identity}"
        estimate_key = "head_discharge_floor_" + suffix
        candidate_key = "head_candidate_rate_" + suffix
        end_key = "head_candidate_end_" + suffix
        weights = {}
        distribute(cfg, groups, {(link, phase): 1.0}, weights)
        if not weights:
            metadata["head_observation_no_model_members"] += 1
            continue
        base = sum(number(caps.get(m, cfg.network.movement_capacity_veh_h)) for m in weights)
        carried = number(prior[estimate_key]) if estimate_key in prior else base
        if estimate_key in prior:
            estimates[link, phase] = max(base, carried)
            metadata["head_observation_groups_carried"] += 1
            metadata[estimate_key] = max(base, carried)
        if not valid:
            continue
        if number(window.get("unknown_links", {}).get(link, 0)) > 0:
            metadata["head_observation_unknown_link"] += 1
            continue
        rates, count, enough = [], 0.0, True
        for head in heads:
            row = observed.get(head["head_id"])
            if row is None:
                enough = False
                break
            if any(row.get(k) != v for k, v in head.items()):
                raise ValueError("Physical head identity/geometry does not match INPX")
            green = number(row["green_sec"])
            qualified = number(row["qualified_crossings"])
            crossings = number(row["crossings"])
            if qualified != int(qualified) or crossings != int(crossings) or qualified > crossings:
                raise ValueError("Impossible physical head count")
            if green > end - start or green != int(green):
                raise ValueError("Head green exceeds elapsed window or one-second cadence")
            if number(row["native_sec"]) + number(row["controlled_sec"]) != end - start:
                raise ValueError("Native/controlled exposure does not cover the window")
            if green < options["min_green_sec"]:
                enough = False
            rates.append(3600 * qualified / green if green > 0 else 0.0)
            count += qualified
        if not enough:
            metadata["head_observation_short_exposure"] += 1
            continue
        rate = sum(rates)
        if count < options["min_crossings"] or rate <= 0:
            metadata["head_observation_missing_crossings"] += 1
            continue
        metadata[candidate_key] = rate
        metadata[end_key] = end
        if candidate_key not in prior or number(prior.get(end_key, -1)) != start:
            metadata["head_observation_waiting_second_window"] += 1
            continue
        supported = min(rate, number(prior[candidate_key]))
        # This is an achieved-discharge lower bound, not an estimate of saturation.
        estimates[link, phase] = max(base, carried, supported)
        metadata[estimate_key] = estimates[link, phase]
        metadata["head_observation_groups_updated"] += 1
    if estimates:
        changed = dict(caps)
        distribute(cfg, groups, estimates, changed)
        cfg.network.movement_capacity_by_movement_veh_h = changed
    return metadata
