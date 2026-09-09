# -*- coding: utf-8 -*-
"""Replay observations through the canonical shared VISSIM runtime setup.

Input loading and config construction remain here. Ordered model configuration,
projection, and hook installation are shared with the real adapter and workers.
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DEFAULT_CAL = "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"


def build(qb, TrafficState, tuning_path, state_path, prev_action_path):
    state_json = json.loads(Path(state_path).read_text(encoding="utf-8"))
    calibration = qb.load_optional_json(str(R / DEFAULT_CAL))
    tuning = qb.load_optional_json(str(tuning_path))
    qb.install_config_switches(tuning)
    dm_path = str(tuning.get("detector_mapping_json", "") or "").strip()
    if dm_path and not Path(dm_path).is_absolute():
        dm_path = str(R / dm_path)
    detector_mapping = qb.load_optional_json(dm_path)
    if not detector_mapping:
        raise SystemExit("detector mapping unreadable: %r" % dm_path)
    detector_mapping, _ = qb.filter_midblock_links_from_detector_mapping(detector_mapping, tuning)
    override = tuning.get("calibration_override", {})
    if isinstance(override, dict):
        calibration = qb.deep_update(dict(calibration), override)
    control_interval = float(state_json.get("control_interval_sec", 150.0))
    sim_period = float(state_json.get("sim_period_sec", 5400.0))
    local_observation = bool(
        qb._link_counts_from_local_observation(state_json) and detector_mapping)
    cfg = qb.build_config(R / "vendor/NumSim-mine", control_interval, sim_period, "fast-smoke",
                          calibration, tuning, local_observation=local_observation, flagship=True)
    from evaluation.controllers.runtime_setup import configure_runtime
    mapping_path = Path(tuning["mapping_json"])
    if not mapping_path.is_absolute():
        mapping_path = R / mapping_path
    mapping = qb.load_optional_json(str(mapping_path))
    if not mapping:
        raise ValueError("control mapping unreadable: %s" % mapping_path)
    m = dict(qb.install_adapter_calibration_fingerprints(cfg, tuning))
    state, detector_mapping, runtime = configure_runtime(
        qb, cfg, tuning, mapping, state_json, prev_action_path,
        detector_mapping, calibration, TrafficState,
    )
    m.update(runtime)
    m["_local_observation"] = float(local_observation)
    return cfg, state, state_json, m, detector_mapping, calibration, tuning
