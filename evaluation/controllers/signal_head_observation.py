"""Validated per-head discharge lower bounds; no saturation/EWMA claim."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]

def number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a measured number")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Nonfinite or negative head observation")
    return value


def serialized_head_position(value):
    """Match VBS JsonDoubleInvariant's CStr(CDbl) 15-digit transport.

    The collector pads trailing zeros; it cannot retain the INPX double's
    additional binary precision. Canonicalize only the expected coordinate,
    then compare exactly. This is not a geometric distance tolerance.
    """
    return float(format(number(value), ".15g"))


def settings(section, *, v2=False):
    """Configuration is the only switch; ON has explicit quality thresholds."""
    if not isinstance(section, dict) or type(section.get("enabled")) is not bool:
        raise ValueError("head_observation requires an object with boolean enabled")
    if set(section) - {"enabled", "min_green_sec", "min_crossings", "sample_interval_sec"}:
        raise ValueError("Unknown head observation option")
    if v2 and "sample_interval_sec" in section:
        raise ValueError("obs150 v2 reads one 150 s window; head_observation.sample_interval_sec is rejected")
    if not section["enabled"]:
        return {"enabled": False}
    if any(isinstance(section.get(k), (str, bool)) for k in ("min_green_sec", "min_crossings")):
        raise ValueError("Head observation thresholds must be numeric")
    green, count = number(section["min_green_sec"]), number(section["min_crossings"])
    if green <= 0 or green != int(green) or count <= 0 or count != int(count):
        raise ValueError("Positive integer minimum green seconds/crossings required")
    result = {"enabled": True, "min_green_sec": green, "min_crossings": count}
    if 'sample_interval_sec' in section:
        interval = section['sample_interval_sec']
        if type(interval) is not int or interval not in (1, 5):
            raise ValueError('Vehicle observation sample_interval_sec must be1 or5')
        result['sample_interval_sec'] = interval
    return result


def validate_provenance(raw, window, options):
    """Reject independent environment activation or changed source bytes."""
    reference = raw["run_provenance"]
    manifest = json.loads(Path(reference["manifest_path"]).read_text(encoding="utf-8-sig"))
    if manifest["run_id"] != reference["run_id"]:
        raise ValueError("Head observation run identity mismatch")
    evidence = manifest["signal_observation"]
    if evidence["config_key"] != "urban.capacity.head_observation" or evidence["options"] != options:
        raise ValueError("Head observation effective configuration mismatch")
    v2 = observation_mode(raw, manifest) == "v2"
    if v2:
        observation = validate_provenance_v2(raw, window, options, manifest)
    elif manifest["env"].get("RW_SIGNAL_OBSERVATION") != "1" or manifest["env"].get("RW_QUEUE_WINDOW") != "1":
        raise ValueError("Head collector transport was not configured by runner")
    if options.get('sample_interval_sec',1)!=1 and manifest['env'].get('RW_VEHICLE_OBSERVATION_INTERVAL_SEC')!=str(options['sample_interval_sec']):
        raise ValueError('Vehicle sampling transport differs from configured cadence')
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
    if v2:
        identity["obs150"] = observation
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
    v2 = observation_mode(state_json) == "v2"
    options = settings(options, v2=v2)
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
    if window is not None and v2:
        # physical-head-window/v2 was fully validated in validate_provenance_v2.
        start, end = number(window["start_sec"]), number(window["end_sec"])
        valid = window["clock_complete"] is True
        metadata["head_observation_invalid_window"] = float(not valid)
        metadata["head_observation_window_v2"] = 1.0
        observed = {str(row["head_id"]): row for row in window["heads"]}
        # B5 builds the heads from the detector sidecar's pinned plan, this consumer from the
        # adapter's actuation plan. A head in one and not the other would otherwise only count as
        # short exposure below and drop its group silently (plan B7).
        expected = {str(head["head_id"]) for heads in geometry.values() for head in heads}
        if set(observed) != expected:
            raise ValueError("obs150 head window heads differ from the INPX physical groups: missing "
                             f"{sorted(expected - set(observed))}, extra {sorted(set(observed) - expected)}")
    elif window is not None:
        if window.get("schema") != "physical-head-window/v1":
            raise ValueError("Unsupported physical head observation schema")
        start, end = number(window["start_sec"]), number(window["end_sec"])
        steps = number(window["transition_count"])
        if (end != number(state_json["sim_sec"]) or end < start
                or steps != end - start or window.get("cadence_sec") != 1
                or window.get('vehicle_cadence_sec',1) != options.get('sample_interval_sec',1)
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
            if (any(row.get(k) != v for k, v in head.items() if k != "position_m")
                    or number(row.get("position_m")) != serialized_head_position(head["position_m"])):
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
    if getattr(cfg.network, "head_free_service", None) is not None:
        metadata.update(_install_head_free_service(cfg, state_json, previous_path, options, context))
    return metadata


def configure_head_free_service(cfg, tuning, raw):
    """Opt in to a uniquely attributable subset of the existing bypass counter.

    The sibling option leaves the head collector's options/provenance unchanged.
    No observed rate is stored in the physical contract.
    """
    section = (tuning or {}).get("urban", {}).get("capacity", {})
    path = section.get("head_free_service")
    if path is None:
        if hasattr(cfg.network, "head_free_service"):
            delattr(cfg.network, "head_free_service")
        return {}
    if not isinstance(path, str) or not path or section.get("head_observation", {}).get("enabled") is not True:
        raise ValueError("Head-free service requires a contract path and enabled head observation")
    data = (ROOT / path).read_bytes()
    document = json.loads(data)
    if document.get("schema") != "head-free-connector-service/v1" or not document.get("resources"):
        raise ValueError("Unsupported head-free service contract")

    def pinned(pin):
        content = (ROOT / pin["path"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != pin["sha256"]:
            raise ValueError("Head-free service pinned evidence changed")
        return content

    network = pinned(document["network"])
    if tuning.get("execution", {}).get("native_signal_record") is True:
        from evaluation.controllers.network_provenance import snapshot_physical_file_sha256
        physical_sha = snapshot_physical_file_sha256(raw)
    else:
        physical_sha = hashlib.sha256(Path(raw["network_path"]).read_bytes()).hexdigest()
    if physical_sha != document["network"]["sha256"]:
        raise ValueError("Head-free service and snapshot physical networks differ")
    join = json.loads(pinned(document["movement_join"]))["by_movement"]
    tree = ET.fromstring(network)
    links = {n.get("no"): n for n in tree.findall("./links/link")}
    heads = defaultdict(list)
    for head in tree.findall("./signalHeads/signalHead"):
        link, lane = head.get("lane").split()
        heads[link, int(lane)].append(head)
    owned_movements, owned_sources = set(), set()
    for connector, row in document["resources"].items():
        source, movement = row["source_link"], row["movement"]
        if source in owned_sources or movement in owned_movements:
            raise ValueError("Head-free counters or movements cannot be allocated twice")
        owned_sources.add(source); owned_movements.add(movement)
        node = links[connector]; start = node.find("fromLinkEndPt"); end = node.find("toLinkEndPt")
        first = int(start.get("lane").split()[1])
        lanes = list(range(first, first + len(node.findall("./lanes/lane"))))
        if (start.get("lane").split()[0] != source or end.get("lane").split()[0] != row["target_link"]
                or lanes != row["source_lanes"] or float(start.get("pos")) != row["source_position_m"]):
            raise ValueError("Head-free connector geometry changed")
        # Reproduce the collector's bypass predicate for EVERY exit, including
        # pre-head branches. Aggregated counters cannot split two free exits.
        free_exits = set()
        for other in links.values():
            edge = other.find("fromLinkEndPt")
            if edge is None or edge.get("lane").split()[0] != source:
                continue
            lo = int(edge.get("lane").split()[1])
            for lane in range(lo, lo + len(other.findall("./lanes/lane"))):
                lane_heads = heads[source, lane]
                if len(lane_heads) > 1 or any(h.get("allVehTypes") != "true" for h in lane_heads):
                    raise ValueError("Ambiguous head-free source-lane authority")
                if not lane_heads or float(edge.get("pos")) < float(lane_heads[0].get("pos")):
                    free_exits.add(other.get("no"))
        if free_exits != {connector} or any(heads[source, lane] for lane in lanes):
            raise ValueError("Source bypass counter lacks exactly one genuinely head-free exit")
        source_heads = [h for (link, _), values in heads.items() if link == source for h in values]
        if not source_heads:
            raise ValueError("Head-free source is outside the existing head-road collector")
        evidence = join[movement]
        turns = evidence["physical_turns"]
        if (evidence["status"] != "unique" or len(turns) != 1
                or any(turns[0].get(k) != v for k, v in {"from_link": source, "connector": connector,
                                                         "to_link": row["target_link"]}.items())
                or sorted(evidence["merged_from"]) != sorted(row["merged_from"])):
            raise ValueError("Head-free movement is not the unique merged physical turn")
        actual = cfg.network.urban_movements.get(movement, {})
        if (any(actual.get(k) != v for k, v in row["expected_movement"].items())
                or actual.get("unsignalized") is not True
                or sorted(actual.get("merged_from", [])) != sorted(row["merged_from"])
                or any(alias != movement and alias in cfg.network.urban_movements for alias in row["merged_from"])):
            raise ValueError("Head-free service requires its one unsignalized merged movement")
        if actual.get("receiving_link") not in cfg.network.urban_link_storage_veh:
            raise ValueError("Head-free service requires finite receiving storage")
        proof = row["native_route"]
        decision = next(n for n in tree.findall("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic")
                        if n.get("no") == proof["decision"])
        route = next(n for n in decision.findall("./vehRoutSta/vehicleRouteStatic") if n.get("no") == proof["route"])
        physical_path = [decision.get("link"), *[n.get("key") for n in route.findall("./linkSeq/intObjectRef")], route.get("destLink")]
        if physical_path != proof["path"] or [source, connector, row["target_link"]] != physical_path[-3:]:
            raise ValueError("Head-free native route changed")
        row["collector_heads"] = [{"head_id": h.get("no"), "link": source,
            "lane": int(h.get("lane").split()[1]), "position_m": serialized_head_position(h.get("pos")),
            "sc": h.get("sg").split()[0], "sg": h.get("sg").split()[1]} for h in source_heads]
    cfg.network.head_free_service = {**document, "contract_sha256": hashlib.sha256(data).hexdigest(), "observations": {}}
    return {"head_free_service_enabled": 1.0}


def _install_head_free_service(cfg, raw, previous_path, options, context):
    """Two adjacent achieved-flow lower bounds; unknown events are never assigned.

    Confirmed source→connector transitions are a safe subset even when OTHER
    events on that road are unknown. Full elapsed time is the denominator;
    road-wide queues cannot establish saturation of the head-free lane.
    """
    contract = cfg.network.head_free_service
    now = number(raw["sim_sec"])
    window = raw.get("local_observation", {}).get("signal_observation_window")
    start = number(window["start_sec"]) if window is not None else now
    end = number(window["end_sec"]) if window is not None else now
    # install() has already validated schema, config/network provenance, actual
    # cadence, exposure method and window endpoint before this consumer runs.
    valid = (window is not None and window.get("clock_complete") is True and end > start
             and raw["local_observation"].get("scan_ok") is True)
    try:
        previous = json.loads(Path(previous_path).read_text(encoding="utf-8-sig"))
        prior = {**previous.get("diagnostics", {}), **previous.get("metadata", {})}
        previous_time = number(previous["metadata"]["sim_sec"])
        prior_ok = (previous["run_provenance"]["run_id"] == raw["run_provenance"]["run_id"]
            and prior.get("head_provenance_" + context) == 1.0
            and number(prior["head_observation_snapshot_sec"]) == previous_time < now
            and previous_time <= start
            and all(number(v) == previous_time for k, v in prior.items() if k.startswith("head_free_candidate_end_")))
    except (OSError, KeyError, TypeError, ValueError):
        prior, prior_ok = {}, False
    result = {"head_free_service_enabled": 1.0}
    caps = dict(cfg.network.movement_capacity_by_movement_veh_h)
    for connector, row in contract["resources"].items():
        identity = hashlib.sha256((context + contract["contract_sha256"] + connector).encode()).hexdigest()[:16]
        suffix = connector + "_" + identity
        floor_key = "head_free_observed_floor_" + suffix
        candidate_key = "head_free_candidate_rate_" + suffix
        end_key = "head_free_candidate_end_" + suffix
        carried = number(prior.get(floor_key, 0.0)) if prior_ok else 0.0
        support, candidate, unknown = 0.0, 0.0, 0.0
        if valid:
            source = row["source_link"]
            observed_heads = {str(h["head_id"]): h for h in window["heads"]}
            for expected in row["collector_heads"]:
                observed = observed_heads.get(expected["head_id"], {})
                if any(observed.get(k) != v for k, v in expected.items()):
                    raise ValueError("Head-free source-road collector coverage changed")
            count = number(window.get("bypass_link_exits", {}).get(source, 0.0))
            unknown = number(window.get("unknown_links", {}).get(source, 0.0))
            departures = number(raw["local_observation"]["link_departures_window"].get(source, 0.0))
            if any(v != int(v) for v in (count, unknown, departures)) or count > departures:
                raise ValueError("Impossible head-free confirmed crossing count")
            result["head_free_confirmed_crossings_" + connector] = count
            result["head_free_exposure_sec_" + connector] = end - start
            if end - start >= options["min_green_sec"] and count >= options["min_crossings"]:
                candidate = 3600.0 * count / (end - start)
                result[candidate_key], result[end_key] = candidate, end
                if prior_ok and prior.get(end_key) == start and candidate_key in prior:
                    support = min(candidate, number(prior[candidate_key]))
        observed = max(carried, support)
        movement = row["movement"]
        base = number(caps[movement])
        selected = max(base, observed)
        caps[movement] = selected
        result.update({floor_key: observed, "head_free_final_rate_" + connector: selected,
            "head_free_unknown_source_events_" + connector: unknown,
            "head_free_saturation_unidentified_" + connector: 1.0,
            "head_free_waiting_second_window_" + connector: float(candidate > 0 and support == 0),
            "head_free_prior_discarded_" + connector: float(bool(prior) and not prior_ok)})
        contract["observations"][connector] = {"observed_only_floor_veh_h": observed,
            "current_pair_support_veh_h": support, "carried_observed_support_veh_h": carried,
            "current_candidate_veh_h": candidate, "unknown_source_events": unknown,
            "saturation_identified": False, "snapshot_sec": now}
    cfg.network.movement_capacity_by_movement_veh_h = caps
    return result


def observation_mode(raw, manifest=None):
    """'v2' when the state carries the obs150 raw bundle (150 s runner), else 'v1'.

    With the run provenance manifest the two must agree: the 'observation' block
    exists exactly for a v2 plant manifest (PS1 A8). Mixing never runs silently.
    """
    from evaluation.controllers import obs150_contract
    v2 = obs150_contract.RAW_STATE_KEY in raw
    if manifest is not None and ("observation" in manifest) != v2:
        raise ValueError("Head observation state and run provenance disagree on the obs150 mode")
    return "v2" if v2 else "v1"


def validate_provenance_v2(raw, window, options, manifest):
    """obs150 v2 provenance: runner env, plant manifest and detector-table pins (plan B7).

    Returns the identity fragment added to the head provenance context.
    """
    from evaluation.controllers import obs150_contract as oc
    if "sample_interval_sec" in options:
        raise ValueError("obs150 v2 rejects head_observation.sample_interval_sec")
    block = manifest["observation"]
    # A decision state exists only for a launch, and a launch runs from a frozen tree
    # (CONTRACT 1.4; PS1 lets freeze be null in PreflightOnly, which makes no decision).
    oc.validate_provenance_observation(block, require_freeze=True)
    plant = Path(block["plant_manifest"]["path"]).read_bytes()
    if hashlib.sha256(plant).hexdigest() != block["plant_manifest"]["sha256"]:
        raise ValueError("obs150 plant manifest changed after launch")
    lane_plant = manifest["signal_observation"].get("lane_plant")
    if lane_plant is not None and lane_plant.get("sha256") != block["plant_manifest"]["sha256"]:
        raise ValueError("obs150 plant manifest differs from the signal_observation lane_plant pin")
    document = json.loads(plant.decode("utf-8-sig"))
    oc.validate_plant_manifest_v2(document)
    detectors = block["detectors"]
    if detectors["sha256"] != document["observation"]["detectors"]["sha256"]:
        raise ValueError("obs150 detector table differs from the plant manifest pin")
    if hashlib.sha256(Path(detectors["path"]).read_bytes()).hexdigest() != detectors["sha256"]:
        raise ValueError("obs150 detector table changed after launch")
    env = manifest["env"]
    expected = oc.expected_runner_env(document, detectors["path"])
    wrong = sorted(key for key, value in expected.items() if env.get(key) != value)
    if wrong:
        raise ValueError("obs150 runner env differs from the plant manifest: " + ", ".join(wrong))
    windows = block["ground_truth_windows"]
    if windows:
        if env.get("RW_OBS150_GT") != oc.format_gt_windows(windows) or not str(manifest.get("name", "")).startswith(oc.GT_RUN_NAME_PREFIX):
            raise ValueError("obs150 ground-truth windows need RW_OBS150_GT on a dev run")
    elif env.get("RW_OBS150_GT", "") != "":
        raise ValueError("RW_OBS150_GT is set without provenance ground-truth windows")
    obs = raw[oc.RAW_STATE_KEY]
    if (obs["detector_config"]["sha256"] != detectors["sha256"] or obs["detector_config"]["rows"] != detectors["rows"]
            or obs["ground_truth_windows"] != windows or obs["simres_steps_per_sec"] != block["expected_simres"]
            or obs["sim_sec"] != raw["sim_sec"] or obs["run_id"] != raw["run_provenance"]["run_id"]):
        raise ValueError("obs150 bundle identity differs from the run provenance")
    local = raw.get("local_observation", {})
    if "signal_observation_window" not in local:
        raise ValueError("obs150 v2 state lacks the merged signal_observation_window (merge_into_state)")
    if obs["sim_sec"] == oc.FIRST_DECISION_SEC:
        if window is not None:
            raise ValueError("t=1 has no head window")
    elif window is None:
        raise ValueError("obs150 v2 decision lacks its head window")
    else:
        oc.validate_head_window_v2(window, end_sec=obs["sim_sec"], detector_config_sha256=detectors["sha256"])
    return {"cadence": block["cadence"], "plant_manifest_sha256": block["plant_manifest"]["sha256"],
            "detectors_sha256": detectors["sha256"]}
