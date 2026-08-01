from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
# 2026-07-31: 기본 모델 저장소를 NUMSIM_REPO_ROOT env → NumSim-mine(flagship-ms-adapt-clean,
# HEAD 7f10393) 순서로 결정한다. 과거 경로 이력(재현용):
#   - "C:/Users/TRLAB/Desktop/찐찐막/Numerical-Sim": 비-git 스냅샷(default.yaml nu_cong=65/
#     capacity_drop=false). nu_cong 격리 재현의 A/B 기준으로만 --repo-root로 명시 지정.
#   - "C:/Users/TRLAB/Desktop/찐찐막/Numerical-Sim-git": GitHub HEAD 0e07c1c 추적 클론
#     (2026-06-29 audit follow-up). 이 머신에는 없음.
DEFAULT_REPO_ROOT = Path(
    os.environ.get(
        "NUMSIM_REPO_ROOT",
        "C:/Users/alsrj/Desktop/학술/찐찐막/Claude/NumSim-mine",
    )
)
DEFAULT_MAPPING = WORKSPACE_ROOT / "evaluation/vsl_install/vsl_segment_mapping_8seg.json"
DEFAULT_CALIBRATION = WORKSPACE_ROOT / "evaluation/calibration/vissim_network_calibration_v2_8seg_20260714.json"
DEFAULT_DETECTOR_MAPPING = WORKSPACE_ROOT / "evaluation/detector_install/detector_local_mapping.json"
LOCAL_OBSERVATION_INTERNAL_STORAGE_FRACTION = 0.35
LOCAL_OBSERVATION_OFFRAMP_STORAGE_FRACTION = 0.50


# 8-seg plant (2026-07-14): one ramp junction per segment, indices in travel
# direction. Matches the Numerical-Sim feature/segment-agents-13p default.yaml
# geometry (segments 8, off 2/4, merge 3/5); see the index-override comment in
# build_config for the westbound swap.
SEGMENT_TO_MODEL = {
    "EB_S0_W_EXT_ENTRY": ("FW_E", 0),
    "EB_S1_W_APPROACH": ("FW_E", 1),
    "EB_S2_D_DIVERGE": ("FW_E", 2),
    "EB_S3_D_MERGE": ("FW_E", 3),
    "EB_S4_F_DIVERGE": ("FW_E", 4),
    "EB_S5_F_MERGE": ("FW_E", 5),
    "EB_S6_POST_F": ("FW_E", 6),
    "EB_S7_E_EXIT": ("FW_E", 7),
    "WB_S0_E_EXT_ENTRY": ("FW_W", 0),
    "WB_S1_E_APPROACH": ("FW_W", 1),
    "WB_S2_F_DIVERGE": ("FW_W", 2),
    "WB_S3_F_MERGE": ("FW_W", 3),
    "WB_S4_D_DIVERGE": ("FW_W", 4),
    "WB_S5_D_MERGE": ("FW_W", 5),
    "WB_S6_POST_D": ("FW_W", 6),
    "WB_S7_W_EXIT": ("FW_W", 7),
}


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def nearest(value: float, candidates: list[float]) -> float:
    return float(min(candidates, key=lambda x: abs(float(x) - float(value))))


def deep_update(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = deep_update(dict(out[key]), value)
        else:
            out[key] = value
    return out


def load_optional_json(path_text: str) -> dict[str, Any]:
    if not path_text:
        return {}
    path = Path(path_text)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    extends = data.get("extends", "")
    if not extends:
        return data
    parent_path = Path(str(extends))
    if not parent_path.is_absolute():
        parent_path = path.parent / parent_path
    parent = load_optional_json(str(parent_path))
    child = dict(data)
    child.pop("extends", None)
    return deep_update(parent, child)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _calibration_child(calibration: Mapping[str, Any], section: str, child: str) -> Mapping[str, Any]:
    parent = _mapping(calibration.get(section))
    nested = _mapping(parent.get(child))
    if nested:
        return nested
    return _mapping(calibration.get(child))


def _segment_length_profile_km(calibration: Mapping[str, Any]) -> dict[str, list[float]]:
    physical = _mapping(calibration.get("physical_inventory"))
    raw = _mapping(physical.get("freeway_segment_length_profile_km"))
    profile: dict[str, list[float]] = {}
    for link, values in raw.items():
        lengths: list[float] = []
        if isinstance(values, list):
            lengths = [max(1.0e-6, _as_float(value)) for value in values]
        elif isinstance(values, Mapping):
            for key in sorted(values, key=lambda item: int(item) if str(item).isdigit() else str(item)):
                lengths.append(max(1.0e-6, _as_float(values[key])))
        if lengths:
            profile[str(link)] = lengths
    return profile


def _freeway_segment_lengths_km(cfg, link: str, count: int) -> list[float]:
    net = cfg.network
    profile = getattr(net, "freeway_segment_length_profile_km", {})
    values: list[float] = []
    if isinstance(profile, Mapping):
        raw = profile.get(str(link), profile.get(link, []))
        if isinstance(raw, list):
            values = [max(1.0e-6, _as_float(value)) for value in raw]
    if len(values) >= count:
        return values[:count]
    base = max(1.0e-6, float(getattr(net, "freeway_segment_length_km", 0.58)))
    if values:
        values = values + [base] * max(0, count - len(values))
        return values[:count]
    return [base] * max(0, count)


def _freeway_vehicle_count_by_link(state, cfg) -> dict[str, list[float]]:
    """Return segment vehicle counts using Vissim-specific length profiles when available."""
    net = cfg.network
    state.ensure_freeway_lane_profile(net)
    counts: dict[str, list[float]] = {}
    lane_profile = getattr(state, "freeway_lanes", {})
    for link in net.freeway_links:
        key = str(link)
        densities = [float(value) for value in state.freeway_density.get(key, [])]
        lengths = _freeway_segment_lengths_km(cfg, key, len(densities))
        raw_lanes = lane_profile.get(key, []) if isinstance(lane_profile, Mapping) else []
        lanes = [
            max(1.0, _as_float(raw_lanes[i], getattr(net, "freeway_lanes", 2)))
            if i < len(raw_lanes)
            else max(1.0, float(getattr(net, "freeway_lanes", 2)))
            for i in range(len(densities))
        ]
        counts[key] = [
            max(0.0, rho) * lengths[i] * lanes[i]
            for i, rho in enumerate(densities)
        ]
    return counts


def _vsl_rollout_tuning(tuning: Mapping[str, Any]) -> Mapping[str, Any]:
    adapter = _mapping(tuning.get("adapter"))
    return _mapping(adapter.get("vsl_metanet_rollout"))


def _is_enabled(settings: Mapping[str, Any]) -> bool:
    return str(settings.get("enabled", False)).lower() in {"1", "true", "yes", "on"}


def _off_ramp_ratio_by_segment(cfg, link: str, count: int) -> list[float]:
    net = cfg.network
    out = [0.0 for _ in range(count)]
    for off_ramp in getattr(net, "off_ramps", []):
        if str(net.off_ramp_from_freeway.get(off_ramp, "")) != str(link):
            continue
        raw_idx = getattr(net, "off_ramp_segment_index", {}).get(off_ramp, count - 1)
        idx = int(clamp(_as_float(raw_idx), 0.0, float(max(0, count - 1))))
        out[idx] = clamp(out[idx] + _as_float(net.off_ramp_split_ratio.get(off_ramp), 0.0), 0.0, 1.0)
    return out


def _vsl_aware_link_rollout_terms(
    context: Mapping[str, Any],
    vsl_kph: float,
    cfg,
    metanet_module,
) -> tuple[float, float, float, float, float] | None:
    """Small Vissim-only link rollout used to rank VSL candidates.

    The stock local follower computes candidate freeway TTS before the VSL loop,
    so all VSL candidates inherit the same freeway/density terms. This helper
    gives the adapter a candidate-specific METANET/CTM approximation without
    editing the external Numerical-Sim checkout.
    """
    agent = context.get("agent")
    state = context.get("state")
    forecast = list(context.get("forecast") or [])
    lane_profile = _mapping(context.get("lane_profile"))
    ramp_metering = _mapping(context.get("ramp_metering"))
    upper = _mapping(context.get("upper"))
    if agent is None or state is None or not forecast:
        return None

    net = cfg.network
    link = str(agent.link)
    rhos = [max(0.0, _as_float(value)) for value in state.freeway_density.get(link, [])]
    if not rhos:
        return None
    speeds_raw = state.freeway_speed.get(link, [])
    speeds = [
        max(float(getattr(net, "v_min", 5.0)), _as_float(speeds_raw[i], getattr(net, "v_free", 120.0)))
        if i < len(speeds_raw)
        else float(getattr(net, "v_free", 120.0))
        for i in range(len(rhos))
    ]
    raw_lanes = lane_profile.get(link, []) if isinstance(lane_profile, Mapping) else []
    lanes = [
        max(1.0e-9, _as_float(raw_lanes[i], getattr(net, "freeway_lanes", 4)))
        if i < len(raw_lanes)
        else max(1.0e-9, float(getattr(net, "freeway_lanes", 4)))
        for i in range(len(rhos))
    ]
    lengths = _freeway_segment_lengths_km(cfg, link, len(rhos))
    off_ratios = _off_ramp_ratio_by_segment(cfg, link, len(rhos))
    dt_h = float(cfg.simulation.T_c_h)
    horizon_steps = forecast[: max(1, int(getattr(cfg.mpc, "horizon_steps", 1)))]
    max_vsl = max(float(value) for value in cfg.freeway_follower.vsl_set)
    vsl_active = float(vsl_kph) < max_vsl - 0.5
    merge_idx = int(clamp(
        getattr(agent, "segment_index", len(rhos) // 2),
        0.0,
        float(max(0, len(rhos) - 1)),
    ))
    release = sum(
        min(
            max(0.0, _as_float(ramp_metering.get(ramp))),
            max(0.0, _as_float(upper.get(ramp), ramp_metering.get(ramp, 0.0))),
        )
        for ramp in getattr(agent, "ramps", [])
    )

    vehicle_tts = 0.0
    density_excess_tts = 0.0
    peak_density = max(rhos)
    capacity = max(0.0, float(getattr(net, "freeway_capacity_veh_h", 0.0)))
    for step in horizon_steps:
        q_values = [
            metanet_module.segment_flow_veh_h(rho, speed, lane)
            for rho, speed, lane in zip(rhos, speeds, lanes)
        ]
        if capacity > 0.0:
            q_values = [min(q, capacity) for q in q_values]
        receiving = [
            max(0.0, (float(net.rho_max) - rhos[i]) * lengths[i] * lanes[i] / max(dt_h, 1.0e-9))
            for i in range(len(rhos))
        ]
        sending = [
            (1.0 - off_ratios[i]) * q_values[i]
            for i in range(len(rhos))
        ]
        q_inter = [
            min(sending[i], receiving[i + 1])
            for i in range(len(rhos) - 1)
        ]
        mainline_demand = max(0.0, _as_float(step.freeway_mainline.get(link, 0.0)))
        entry_flow = min(mainline_demand, capacity if capacity > 0.0 else mainline_demand, receiving[0])
        next_rhos: list[float] = []
        next_speeds: list[float] = []
        for i, rho in enumerate(rhos):
            q_in = entry_flow if i == 0 else q_inter[i - 1]
            if i == merge_idx:
                q_in += release
            q_out = sending[i] if i == len(rhos) - 1 else q_inter[i]
            veh_per_density = max(1.0e-9, lengths[i] * lanes[i])
            rho_next = clamp(
                rho + (q_in - q_out) * dt_h / veh_per_density,
                0.0,
                float(net.rho_max),
            )
            vehicle_tts += 0.5 * (rho + rho_next) * veh_per_density * dt_h
            density_excess_tts += 0.5 * (
                max(0.0, rho - float(net.rho_crit)) + max(0.0, rho_next - float(net.rho_crit))
            ) * dt_h
            upstream_speed = float(net.v_free) if i == 0 else speeds[i - 1]
            downstream_rho = rhos[i + 1] if i + 1 < len(rhos) else rhos[i]
            v_eff = metanet_module.effective_desired_speed_kmh(
                rho,
                float(net.v_free),
                float(net.rho_crit),
                float(vsl_kph),
                float(getattr(net, "alpha_vsl", 0.0)),
                bool(vsl_active),
                float(getattr(net, "metanet_a_m", 1.867)),
            )
            v_next = metanet_module.metanet_speed_update_kmh(
                speeds[i],
                upstream_speed,
                rho,
                downstream_rho,
                v_eff,
                dt_h,
                lengths[i],
                float(net.metanet_tau_h),
                metanet_module.select_anticipation_nu(rho, net),
                float(net.metanet_kappa_veh_km_lane),
                float(net.v_min),
            )
            next_rhos.append(float(rho_next))
            next_speeds.append(float(v_next))
        rhos = next_rhos
        speeds = next_speeds
        peak_density = max(peak_density, max(rhos) if rhos else 0.0)
    return (
        float(vehicle_tts),
        float(density_excess_tts),
        float(rhos[merge_idx] if rhos else 0.0),
        float(peak_density),
        float(release),
    )


def install_vsl_metanet_rollout_runtime_patch(cfg, tuning: Mapping[str, Any]) -> dict[str, float]:
    settings = _vsl_rollout_tuning(tuning)
    if not _is_enabled(settings):
        setattr(cfg, "_vissim_vsl_rollout_enabled", False)
        return {"vsl_metanet_rollout_patch_enabled": 0.0}
    try:
        from src.controllers import distributed_coordinator as dc
        from src.models import metanet as metanet_module
    except Exception:
        return {"vsl_metanet_rollout_patch_enabled": 0.0, "vsl_metanet_rollout_patch_failed": 1.0}

    cls = dc.DistributedCoordinator
    if not hasattr(cls, "_vissim_original_candidate_freeway_tts_terms"):
        cls._vissim_original_candidate_freeway_tts_terms = cls._candidate_freeway_tts_terms
    if not hasattr(cls, "_vissim_original_freeway_agent_objective"):
        cls._vissim_original_freeway_agent_objective = cls._freeway_agent_objective
    if not hasattr(cls, "_vissim_original_solve_for_vsl_consensus"):
        cls._vissim_original_solve_for_vsl_consensus = cls.solve
    original_terms = cls._vissim_original_candidate_freeway_tts_terms
    original_objective = cls._vissim_original_freeway_agent_objective
    original_solve = cls._vissim_original_solve_for_vsl_consensus
    finalize_agent_consensus = str(settings.get("finalize_agent_consensus", False)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    def patched_candidate_freeway_tts_terms(self, agent, state, ramp_metering, upper, forecast, lane_profile):
        result = original_terms(self, agent, state, ramp_metering, upper, forecast, lane_profile)
        if getattr(self.cfg, "_vissim_vsl_rollout_enabled", False):
            self._vissim_vsl_rollout_context = {
                "agent": agent,
                "state": state,
                "ramp_metering": dict(ramp_metering),
                "upper": dict(upper),
                "forecast": list(forecast),
                "lane_profile": lane_profile,
            }
        return result

    def patched_freeway_agent_objective(
        self,
        rhos,
        density_excess,
        metering_error,
        ramp_metering,
        vsl,
        previous_vsl,
        offramp_forecast_veh,
        offramp_storage_veh,
        offramp_capacity_veh=0.0,
        ramp_queue_tts=0.0,
        onramp_urban_queue_tts=0.0,
        horizon_h=1.0,
        freeway_vehicle_tts=None,
        density_excess_tts=None,
    ):
        if getattr(self.cfg, "_vissim_vsl_rollout_enabled", False):
            context = getattr(self, "_vissim_vsl_rollout_context", None)
            terms = _vsl_aware_link_rollout_terms(context or {}, float(vsl), self.cfg, metanet_module)
            if terms is not None:
                freeway_vehicle_tts = terms[0]
                density_excess_tts = terms[1]
                self._vissim_vsl_rollout_eval_count = (
                    int(getattr(self, "_vissim_vsl_rollout_eval_count", 0)) + 1
                )
        return original_objective(
            self,
            rhos,
            density_excess,
            metering_error,
            ramp_metering,
            vsl,
            previous_vsl,
            offramp_forecast_veh,
            offramp_storage_veh,
            offramp_capacity_veh,
            ramp_queue_tts=ramp_queue_tts,
            onramp_urban_queue_tts=onramp_urban_queue_tts,
            horizon_h=horizon_h,
            freeway_vehicle_tts=freeway_vehicle_tts,
            density_excess_tts=density_excess_tts,
        )

    def patched_solve(self, *args, **kwargs):
        result = original_solve(self, *args, **kwargs)
        if not getattr(self.cfg, "_vissim_vsl_rollout_consensus_enabled", False):
            return result
        control = getattr(result, "control", None)
        if control is None:
            return result
        diagnostics: dict[str, Any] = {}
        raw_result_diag = getattr(result, "diagnostics", None)
        if isinstance(raw_result_diag, Mapping):
            diagnostics.update(raw_result_diag)
        raw_control_diag = getattr(control, "diagnostics", None)
        if isinstance(raw_control_diag, Mapping):
            diagnostics.update(raw_control_diag)
        by_link: dict[str, list[float]] = {str(link): [] for link in self.cfg.network.freeway_links}
        for agent in getattr(self, "freeway_agents", []):
            key = f"agent_{agent.id}_vsl_selected"
            if key not in diagnostics:
                continue
            try:
                by_link.setdefault(str(agent.link), []).append(float(diagnostics[key]))
            except (TypeError, ValueError):
                continue
        selected = {link: float(min(values)) for link, values in by_link.items() if values}
        if not selected:
            return result
        for key in list(getattr(control, "vsl", {}).keys()):
            if "__seg" in str(key):
                control.vsl.pop(key, None)
        control.vsl.update(selected)
        consensus_diag = {
            "vsl_agent_consensus_finalize_active": 1.0,
            "vsl_agent_consensus_finalize_link_count": float(len(selected)),
            "vsl_agent_consensus_finalize_min_kph": float(min(selected.values())),
        }
        for link, value in selected.items():
            consensus_diag[f"vsl_agent_consensus_{link}_kph"] = float(value)
        control.diagnostics.update(consensus_diag)
        if isinstance(raw_result_diag, Mapping):
            raw_result_diag.update(consensus_diag)
        return result

    cls._candidate_freeway_tts_terms = patched_candidate_freeway_tts_terms
    cls._freeway_agent_objective = patched_freeway_agent_objective
    cls.solve = patched_solve
    setattr(cfg, "_vissim_vsl_rollout_enabled", True)
    setattr(cfg, "_vissim_vsl_rollout_consensus_enabled", finalize_agent_consensus)
    return {
        "vsl_metanet_rollout_patch_enabled": 1.0,
        "vsl_agent_consensus_finalize_enabled": float(finalize_agent_consensus),
    }


def _observation_split_parameters(calibration: Mapping[str, Any] | None = None) -> dict[str, float]:
    observation = _mapping((calibration or {}).get("observation"))
    return {
        "internal_storage_fraction": clamp(
            _as_float(
                observation.get("internal_storage_fraction"),
                LOCAL_OBSERVATION_INTERNAL_STORAGE_FRACTION,
            ),
            0.0,
            1.0,
        ),
        "offramp_storage_fraction": clamp(
            _as_float(
                observation.get("offramp_storage_fraction"),
                LOCAL_OBSERVATION_OFFRAMP_STORAGE_FRACTION,
            ),
            0.0,
            1.0,
        ),
    }


def _link_counts_from_local_observation(state_json: Mapping[str, Any]) -> dict[str, float]:
    local = state_json.get("local_observation", {})
    if not isinstance(local, Mapping):
        return {}
    raw = local.get("link_counts", {})
    if not isinstance(raw, Mapping):
        return {}
    return {str(k): max(0.0, _as_float(v)) for k, v in raw.items()}


def _storage_links_for_observed_origin(cfg, origin: str) -> list[str]:
    net = cfg.network
    value = str(origin)
    if value in net.urban_link_storage_veh:
        return [value]
    storage = str(net.off_ramp_storage_link.get(value, ""))
    if storage and storage in net.urban_link_storage_veh:
        return [storage]
    return []


def _link_storage_split_fraction(cfg, origins: list[str], split_parameters: Mapping[str, Any]) -> float:
    storage_links: list[str] = []
    off_ramp_storage_links = {str(v) for v in cfg.network.off_ramp_storage_link.values()}
    for origin in origins:
        storage_links.extend(_storage_links_for_observed_origin(cfg, origin))
    if not storage_links:
        return 0.0
    if any(link in off_ramp_storage_links for link in storage_links):
        return float(split_parameters.get("offramp_storage_fraction", LOCAL_OBSERVATION_OFFRAMP_STORAGE_FRACTION))
    return float(split_parameters.get("internal_storage_fraction", LOCAL_OBSERVATION_INTERNAL_STORAGE_FRACTION))


def build_local_observation_summary(
    state_json: Mapping[str, Any],
    cfg,
    detector_mapping: Mapping[str, Any],
    calibration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert Vissim detector/local-zone counts into model-local queues.

    The Vissim runner may still use a fast whole-vehicle scan internally, but
    once the counts enter this function they are reduced through the detector
    mapping. Follower-visible state is therefore link/movement/agent scoped
    instead of aggregate global counts.
    """
    link_counts = _link_counts_from_local_observation(state_json)
    if not link_counts:
        return {}

    split_parameters = _observation_split_parameters(calibration)
    storage_fraction_by_link: dict[str, float] = {}
    queue_count_by_link: dict[str, float] = {}
    storage_count_by_link: dict[str, float] = {}
    urban_link_storage_occupancy = {link: 0.0 for link in cfg.network.urban_link_storage_veh}
    for link, count in link_counts.items():
        origins = [
            str(value)
            for value in detector_mapping.get("link_to_origins", {}).get(str(link), [])
        ]
        storage_fraction = _link_storage_split_fraction(cfg, origins, split_parameters)
        storage_fraction_by_link[str(link)] = float(storage_fraction)
        storage_count = max(0.0, count * storage_fraction)
        queue_count = max(0.0, count - storage_count)
        storage_count_by_link[str(link)] = float(storage_count)
        queue_count_by_link[str(link)] = float(queue_count)
        storage_links: list[str] = []
        for origin in origins:
            for storage_link in _storage_links_for_observed_origin(cfg, origin):
                if storage_link not in storage_links:
                    storage_links.append(storage_link)
        if storage_count > 0.0 and storage_links:
            share = storage_count / len(storage_links)
            for storage_link in storage_links:
                capacity = float(cfg.network.urban_link_storage_veh.get(storage_link, 0.0))
                current = urban_link_storage_occupancy.get(storage_link, 0.0)
                urban_link_storage_occupancy[storage_link] = min(capacity, current + share)

    movement_queue = {movement: 0.0 for movement in cfg.network.urban_movements}
    for link, entries in detector_mapping.get("link_to_movements", {}).items():
        count = queue_count_by_link.get(str(link), link_counts.get(str(link), 0.0))
        if count <= 0.0 or not isinstance(entries, list):
            continue
        weight_sum = sum(
            max(0.0, _as_float(item.get("weight", 0.0)))
            for item in entries
            if isinstance(item, Mapping)
        )
        if weight_sum <= 1.0e-9:
            weight_sum = float(len(entries)) if entries else 1.0
        for item in entries:
            if not isinstance(item, Mapping):
                continue
            movement = str(item.get("movement", ""))
            if movement not in movement_queue:
                continue
            weight = max(0.0, _as_float(item.get("weight", 1.0)))
            movement_queue[movement] += count * weight / weight_sum

    ramp_queue = {ramp: 0.0 for ramp in cfg.network.ramps}
    for link, ramps in detector_mapping.get("ramp_link_to_queues", {}).items():
        count = link_counts.get(str(link), 0.0)
        if count <= 0.0 or not isinstance(ramps, list) or not ramps:
            continue
        share = count / len(ramps)
        for ramp in ramps:
            ramp_key = str(ramp)
            if ramp_key in ramp_queue:
                ramp_queue[ramp_key] += share

    # Legacy boundary_queue is kept for diagnostics/compatibility. The actual
    # urban signal queues above are the follower-visible queue state.
    boundary_queue: dict[str, float] = {}
    for link, key in detector_mapping.get("boundary_link_to_queue", {}).items():
        qkey = str(key)
        boundary_queue[qkey] = boundary_queue.get(qkey, 0.0) + link_counts.get(str(link), 0.0)

    agents: dict[str, Any] = {}
    for agent_id, spec in detector_mapping.get("agents", {}).items():
        if not isinstance(spec, Mapping):
            continue
        visible_links = [str(v) for v in spec.get("visible_links", [])]
        visible_movements = [str(v) for v in spec.get("visible_movements", [])]
        visible_ramps = [str(v) for v in spec.get("visible_ramps", [])]
        agent_summary = {
            "visible_links": visible_links,
            "visible_movements": visible_movements,
            "visible_ramps": visible_ramps,
            "link_counts": {link: link_counts.get(link, 0.0) for link in visible_links},
            "movement_queue": {
                movement: movement_queue.get(movement, 0.0)
                for movement in visible_movements
            },
            "ramp_queue": {
                ramp: ramp_queue.get(ramp, 0.0)
                for ramp in visible_ramps
            },
        }
        if "control_enabled" in spec:
            agent_summary["control_enabled"] = bool(spec.get("control_enabled", True))
        if "monitoring_only" in spec:
            agent_summary["monitoring_only"] = bool(spec.get("monitoring_only", False))
        agents[str(agent_id)] = agent_summary

    return {
        "mode": "detector_local_v2_storage_split",
        "link_counts": link_counts,
        "queue_count_by_link": queue_count_by_link,
        "storage_count_by_link": storage_count_by_link,
        "storage_fraction_by_link": storage_fraction_by_link,
        "urban_movement_queue": movement_queue,
        "urban_link_storage_occupancy": urban_link_storage_occupancy,
        "ramp_queue": ramp_queue,
        "boundary_queue": boundary_queue,
        "agents": agents,
        "split_parameters": {
            "internal_storage_fraction": float(split_parameters["internal_storage_fraction"]),
            "offramp_storage_fraction": float(split_parameters["offramp_storage_fraction"]),
        },
    }


def _movement_allowed_storage_links(cfg, movements: set[str]) -> set[str]:
    allowed: set[str] = set()
    for movement in movements:
        spec = cfg.network.urban_movements.get(movement, {})
        for field in ("origin", "destination", "receiving_link"):
            value = str(spec.get(field, ""))
            if value:
                allowed.add(value)
        ramp = str(spec.get("ramp", ""))
        if ramp:
            for linked in cfg.network.on_ramp_to_movement.get(ramp, []):
                linked_spec = cfg.network.urban_movements.get(linked, {})
                receiving = str(linked_spec.get("receiving_link", ""))
                if receiving:
                    allowed.add(receiving)
        off_ramp = str(spec.get("off_ramp", ""))
        if off_ramp:
            storage = str(cfg.network.off_ramp_storage_link.get(off_ramp, ""))
            if storage:
                allowed.add(storage)
    return allowed


def mask_state_for_agent(state, cfg, agent):
    """Return an agent-local state view for Vissim local-information runs.

    This is a runtime guard around the existing Numerical-Sim distributed
    coordinator. It keeps the plant state global for the leader, but masks the
    state object seen by each follower solve.
    """
    masked = state.copy()
    net = cfg.network
    kind = str(getattr(agent, "kind", ""))

    allowed_movements = set(str(m) for m in getattr(agent, "movements", ()) or ())
    allowed_ramps = set(str(r) for r in getattr(agent, "ramps", ()) or ())
    allowed_off_ramps = set(str(r) for r in getattr(agent, "off_ramps", ()) or ())
    allowed_storage = _movement_allowed_storage_links(cfg, allowed_movements)
    for off_ramp in allowed_off_ramps:
        storage = str(net.off_ramp_storage_link.get(off_ramp, ""))
        if storage:
            allowed_storage.add(storage)

    if kind == "urban":
        masked.urban_movement_queue = {
            key: (float(value) if key in allowed_movements else 0.0)
            for key, value in masked.urban_movement_queue.items()
        }
        masked.ramp_queue = {
            key: (float(value) if key in allowed_ramps else 0.0)
            for key, value in masked.ramp_queue.items()
        }
        boundary_keys = {
            str(net.urban_movements.get(movement, {}).get(field, ""))
            for movement in allowed_movements
            for field in ("origin", "destination")
        }
        masked.boundary_queue = {
            key: (float(value) if key in boundary_keys else 0.0)
            for key, value in masked.boundary_queue.items()
        }
        masked.urban_link_storage = {
            key: (
                float(value)
                if key in allowed_storage
                else float(net.urban_link_storage_veh.get(key, value))
            )
            for key, value in masked.urban_link_storage.items()
        }
        masked.mainline_origin_queue = {key: 0.0 for key in masked.mainline_origin_queue}
        # Urban followers should not directly inspect global freeway density;
        # freeway influence, if enabled, arrives through the coupling response.
        masked.freeway_density = {
            link: [0.0 for _ in values]
            for link, values in masked.freeway_density.items()
        }
        masked.freeway_speed = {
            link: [float(net.v_free) for _ in values]
            for link, values in masked.freeway_speed.items()
        }
        masked.refresh_freeway_flow(net)
        return masked

    if kind == "freeway":
        link = str(getattr(agent, "link", ""))
        segment_index = int(getattr(agent, "segment_index", -1))
        masked.urban_movement_queue = {key: 0.0 for key in masked.urban_movement_queue}
        masked.boundary_queue = {key: 0.0 for key in masked.boundary_queue}
        masked.ramp_queue = {
            key: (float(value) if key in allowed_ramps else 0.0)
            for key, value in masked.ramp_queue.items()
        }
        masked.urban_link_storage = {
            key: (
                float(value)
                if key in allowed_storage
                else float(net.urban_link_storage_veh.get(key, value))
            )
            for key, value in masked.urban_link_storage.items()
        }
        masked.mainline_origin_queue = {
            key: (float(value) if key == link else 0.0)
            for key, value in masked.mainline_origin_queue.items()
        }
        for model_link, values in list(masked.freeway_density.items()):
            speeds = list(masked.freeway_speed.get(model_link, [float(net.v_free) for _ in values]))
            densities = list(values)
            if model_link != link:
                masked.freeway_density[model_link] = [0.0 for _ in densities]
                masked.freeway_speed[model_link] = [float(net.v_free) for _ in densities]
                continue
            for i in range(len(densities)):
                if i != segment_index:
                    densities[i] = 0.0
                    if i < len(speeds):
                        speeds[i] = float(net.v_free)
            masked.freeway_density[model_link] = densities
            masked.freeway_speed[model_link] = speeds
        masked.refresh_freeway_flow(net)
        return masked

    return masked


def install_local_observation_runtime_guards() -> None:
    """Patch distributed follower solves to receive agent-masked state views."""
    from src.controllers import distributed_coordinator as dc

    cls = dc.DistributedCoordinator
    if getattr(cls, "_vissim_local_observation_guard_installed", False):
        return

    original_urban = cls._solve_urban_agent
    original_freeway = cls._solve_freeway_agent

    def guarded_urban(self, agent, state, leader, forecast, freeway_response, current, allocation_plan, coupling):
        return original_urban(
            self,
            agent,
            mask_state_for_agent(state, self.cfg, agent),
            leader,
            forecast,
            freeway_response,
            current,
            allocation_plan,
            coupling,
        )

    def guarded_freeway(self, agent, state, leader, forecast, current, coupling):
        return original_freeway(
            self,
            agent,
            mask_state_for_agent(state, self.cfg, agent),
            leader,
            forecast,
            current,
            coupling,
        )

    cls._solve_urban_agent = guarded_urban
    cls._solve_freeway_agent = guarded_freeway
    cls._vissim_local_observation_guard_installed = True


def install_vissim_calibration_runtime_patches(cfg, calibration: Mapping[str, Any]) -> dict[str, float]:
    """Install Vissim-specific runtime patches without editing Numerical-Sim sources.

    This adapter owns Vissim-only physical corrections so that the Desktop
    Numerical-Sim source tree can stay untouched. The v2 patches are:

    * non-uniform freeway segment lengths from the VSL/control-segment geometry;
    * off-ramp combined spillback capacity. The stock Numerical-Sim function
      adds all downstream turning-movement storage capacities, which
      double-counts shared Vissim approach space for this hypothetical network.
      Calibration v2 replaces that with explicit per-off-ramp physical capacity.
    """
    metadata: dict[str, float] = {}
    physical = _mapping(calibration.get("physical_inventory"))
    length_profile = _segment_length_profile_km(calibration)
    if length_profile:
        setattr(cfg.network, "freeway_segment_length_profile_km", length_profile)
        lengths = [length for values in length_profile.values() for length in values]
        metadata.update({
            "calibration_freeway_segment_length_profile_applied": 1.0,
            "calibration_freeway_segment_length_count": float(len(lengths)),
            "calibration_freeway_segment_length_min_km": float(min(lengths)),
            "calibration_freeway_segment_length_max_km": float(max(lengths)),
            "calibration_freeway_segment_length_mean_km": float(sum(lengths) / len(lengths)),
        })
        try:
            from src.models import state as state_module

            TrafficState = state_module.TrafficState
            if not hasattr(TrafficState, "_vissim_original_freeway_vehicle_count_by_link"):
                TrafficState._vissim_original_freeway_vehicle_count_by_link = (
                    TrafficState.freeway_vehicle_count_by_link
                )
            if not hasattr(TrafficState, "_vissim_original_total_freeway_vehicles"):
                TrafficState._vissim_original_total_freeway_vehicles = TrafficState.total_freeway_vehicles

            def calibrated_freeway_vehicle_count_by_link(self, net):
                self.ensure_freeway_lane_profile(net)
                out: dict[str, list[float]] = {}
                lane_profile = getattr(self, "freeway_lanes", {})
                profile = getattr(net, "freeway_segment_length_profile_km", {})
                for link in net.freeway_links:
                    key = str(link)
                    densities = [float(value) for value in self.freeway_density.get(key, [])]
                    raw_lengths = profile.get(key, []) if isinstance(profile, Mapping) else []
                    lengths = [
                        max(1.0e-6, _as_float(value))
                        for value in raw_lengths
                    ] if isinstance(raw_lengths, list) else []
                    base = max(1.0e-6, float(getattr(net, "freeway_segment_length_km", 0.58)))
                    if len(lengths) < len(densities):
                        lengths = lengths + [base] * (len(densities) - len(lengths))
                    raw_lanes = lane_profile.get(key, []) if isinstance(lane_profile, Mapping) else []
                    counts = []
                    for i, rho in enumerate(densities):
                        lanes = (
                            max(1.0, _as_float(raw_lanes[i], getattr(net, "freeway_lanes", 2)))
                            if i < len(raw_lanes)
                            else max(1.0, float(getattr(net, "freeway_lanes", 2)))
                        )
                        counts.append(max(0.0, float(rho)) * lengths[i] * lanes)
                    out[key] = counts
                return out

            def calibrated_total_freeway_vehicles(self, net) -> float:
                return float(
                    sum(
                        sum(max(0.0, float(value)) for value in values)
                        for values in calibrated_freeway_vehicle_count_by_link(self, net).values()
                    )
                )

            TrafficState.freeway_vehicle_count_by_link = calibrated_freeway_vehicle_count_by_link
            TrafficState.total_freeway_vehicles = calibrated_total_freeway_vehicles
            metadata["calibration_state_vehicle_count_patch_installed"] = 1.0
        except Exception:
            metadata["calibration_state_vehicle_count_patch_installed"] = 0.0

    capacity_map = _mapping(physical.get("off_ramp_combined_capacity_veh"))
    if not capacity_map:
        return metadata

    calibrated_capacity = {
        str(off_ramp): max(0.0, _as_float(value))
        for off_ramp, value in capacity_map.items()
    }
    if not calibrated_capacity:
        return metadata

    from src.controllers import spillback_constraints

    if not hasattr(spillback_constraints, "_vissim_original_offramp_combined_capacity_veh"):
        spillback_constraints._vissim_original_offramp_combined_capacity_veh = (
            spillback_constraints.offramp_combined_capacity_veh
        )
    original = spillback_constraints._vissim_original_offramp_combined_capacity_veh

    def calibrated_offramp_combined_capacity_veh(cfg_arg, off_ramp: str) -> float:
        key = str(off_ramp)
        if key in calibrated_capacity:
            return float(calibrated_capacity[key])
        return float(original(cfg_arg, off_ramp))

    spillback_constraints.offramp_combined_capacity_veh = calibrated_offramp_combined_capacity_veh

    # Usually unnecessary because imported assess_* functions keep their module
    # globals, but patch a direct attribute too if a future module imports it.
    try:
        import src.controllers.distributed_coordinator as distributed_coordinator

        if hasattr(distributed_coordinator, "offramp_combined_capacity_veh"):
            distributed_coordinator.offramp_combined_capacity_veh = calibrated_offramp_combined_capacity_veh
    except Exception:
        pass

    capacities = []
    for off_ramp in getattr(cfg.network, "off_ramps", []):
        capacities.append(calibrated_offramp_combined_capacity_veh(cfg, str(off_ramp)))
    metadata.update({
        "calibration_offramp_capacity_patch_installed": 1.0,
        "calibration_offramp_capacity_min_veh": float(min(capacities)) if capacities else 0.0,
        "calibration_offramp_capacity_max_veh": float(max(capacities)) if capacities else 0.0,
        "calibration_offramp_capacity_total_veh": float(sum(capacities)),
    })
    return metadata


def repo_imports(repo_root: Path):
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.controllers.stackelberg_mpc import StackelbergMPCController
    from src.models.demand import DemandStep
    from src.models.state import ControlAction, ExperimentConfig, TrafficState, segment_vsl

    return StackelbergMPCController, DemandStep, ControlAction, ExperimentConfig, TrafficState, segment_vsl


def calibration_to_config_overrides(calibration: Mapping[str, Any]) -> dict[str, Any]:
    network = _calibration_child(calibration, "operational", "network")
    ramp = _calibration_child(calibration, "operational", "ramp_metering")
    signal = _calibration_child(calibration, "operational", "signal")
    mfd = _calibration_child(calibration, "operational", "urban_mfd")
    physical = _mapping(calibration.get("physical_inventory"))

    d_map = ramp.get("D_green_to_release_vph_initial_mpc", {})
    f_map = ramp.get("F_green_to_release_vph_raw", {})
    d_cap = max((float(v) for v in d_map.values()), default=1500.0) if isinstance(d_map, Mapping) else 1500.0
    f_cap = max((float(v) for v in f_map.values()), default=1500.0) if isinstance(f_map, Mapping) else 1500.0
    if str(ramp.get("F_status", "")).lower() == "invalid_for_physical_metering_fit":
        # F is not a valid green-to-release metering curve. Use only the
        # full-green observed discharge as a conservative plant cap; do not
        # optimize against the non-monotone raw maximum.
        f_cap = _release_at_largest_green(f_map, f_cap)

    out: dict[str, Any] = {
        "network": {
            "v_free": float(network.get("v_free_kph", 100.0)),
            "rho_crit": float(network.get("rho_crit_veh_km_lane", 33.5)),
            # 지수형 속도-밀도식 V(rho)=v_free*exp(-(1/a)*(rho/rho_crit)^a)의 형상 a.
            # 키가 없는 구 캘리브레이션 파일은 NetworkConfig 기본값 1.867을 그대로 받는다(비트 동일).
            "metanet_a_m": float(network.get("desired_speed_shape_a", 1.867)),
            "freeway_capacity_veh_h": float(network.get("freeway_capacity_veh_h", 4000.0)),
            "lost_time": float(signal.get("recommended_initial_lost_time_sec", 8.0)),
            "movement_capacity_veh_h": float(
                signal.get("recommended_initial_saturation_flow_vph_approach", 1400.0)
            ),
            "ramp_capacity_veh_h": {
                "R_D_W": float(d_cap),
                "R_D_E": float(d_cap),
                "R_F_W": float(f_cap),
                "R_F_E": float(f_cap),
            },
        },
        "leader": {
            "N_P_crit_veh": float(mfd.get("N_P_crit_veh_initial", 509.448830418254)),
        },
    }
    length_profile = _segment_length_profile_km(calibration)
    if length_profile:
        lengths = [length for values in length_profile.values() for length in values]
        if lengths:
            out["network"]["freeway_segment_length_km"] = float(sum(lengths) / len(lengths))

    storage_capacity: dict[str, float] = {}
    for key in (
        "urban_link_storage_capacity_veh",
        "on_ramp_storage_capacity_veh",
        "off_ramp_storage_capacity_veh",
    ):
        for link, value in _mapping(physical.get(key)).items():
            storage_capacity[str(link)] = max(0.0, _as_float(value))
    if storage_capacity:
        out["network"]["urban_link_storage_veh"] = storage_capacity

    for scalar_key in ("boundary_queue_max_veh", "ramp_queue_max_veh"):
        if scalar_key in physical:
            out["network"][scalar_key] = max(0.0, _as_float(physical.get(scalar_key)))
    return out


def tuning_to_config_overrides(tuning: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(tuning.get("config_overrides"), Mapping):
        out = deep_update(out, tuning["config_overrides"])
    for section in ("network", "mpc", "leader", "freeway_follower", "urban_follower"):
        if isinstance(tuning.get(section), Mapping):
            out = deep_update(out, {section: tuning[section]})
    return out


def adapter_actuation_settings(calibration: Mapping[str, Any], tuning: Mapping[str, Any]) -> dict[str, Any]:
    ramp = _calibration_child(calibration, "operational", "ramp_metering")
    actuation = {
        "D_green_to_release_vph": ramp.get("D_green_to_release_vph_initial_mpc", {}),
        "F_green_to_release_vph": ramp.get("F_green_to_release_vph_raw", {}),
        "F_ramp_mode": "always_green",
    }
    if isinstance(tuning.get("actuation"), Mapping):
        actuation = deep_update(actuation, tuning["actuation"])
    f_status = str(ramp.get("F_status", "")).lower()
    allow_invalid = bool(actuation.get("allow_invalid_F_metering", False))
    if f_status == "invalid_for_physical_metering_fit" and not allow_invalid:
        actuation["F_ramp_mode"] = "always_green"
        actuation["F_ramp_invalid_guard_active"] = True
        actuation["F_ramp_guard_reason"] = f_status
    return actuation


# ---------------------------------------------------------------------------
# P-Stack flagship (2026-07-31): NumSim flagship-ms-adapt-clean(HEAD 7f10393)의
# 최종 P-Stack(P-STACK-WU-FAITHFUL-ALLPRICE-JOINT) 운영점을 `pstack-flagship`
# 모드로 이식한 구간. 기준 원문(레시피 문서와 다르면 러너가 정답):
#   NumSim-mine/work/run_claude_style_five_controller.py
#     - make_controller ALLPRICE-JOINT 분기 L244-316 (BIAS_SAMPLE L268-273 포함)
#     - env→cfg 번역 L560-726 (METER_BOX/VSL_BOX/BOX_WALK/NP_PD_ITER/NP_BIAS/FAR_*)
#     - SEG13 L829-844, SUP_PFO L925-959·L1151-1176, FAR_GATE L1001-1099,
#       MS_ADAPT L1018-1026·L1106-1116
#   NumSim-mine/work/run_job.sh (플래그십 env 고정값, NASH_SMAX=10)
# 어댑터는 결정 1회마다 재기동되므로 러너 루프의 스텝 간 상태(직전 링크평균 밀도,
# MS 래치, fargate 래치)는 out-action-json 옆 사이드카 JSON에 영속화한다.
# ---------------------------------------------------------------------------

FLAGSHIP_RUNTIME_FILENAME = "pstack_flagship_runtime.json"
# 플래그십 채택값(2026-07-27 확정 셀): thr10 / hold5 / w0.013.
# 주의 — 러너 코드 기본은 MS_HOLD=3이지만 플래그십 채택 런은 MS_HOLD=5로 실행됐다.
# 여기서는 채택값 5를 하드코딩하고 tuning `adapter.flagship.ms_adapt`로만 조정한다.
FLAGSHIP_MS_ADAPT_DEFAULTS: dict[str, Any] = {"enabled": True, "thr": 10.0, "hold": 5, "w": 0.013}
# FAR_GATE=3(하이브리드). 폐쇄 예보 입력이 VISSIM forecast에 없으므로(아래
# freeway_lane_loss 항상 빈 dict) 실질적으로 mode 2(capdrop 상태 트리거)로 동작한다.
FLAGSHIP_FAR_GATE_DEFAULTS: dict[str, Any] = {"enabled": True, "thr": 0.95}


def flagship_settings(tuning: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(_mapping(tuning.get("adapter")).get("flagship"))


def flagship_config_overrides() -> dict[str, Any]:
    """플래그십 cfg 정식 키(적용 순서 base < flagship < calibration < tuning의 flagship 층).

    러너 build_cfg(L76-99) + run_job.sh env + default.yaml 실효값을 그대로 옮긴다.
    주의: plan.md 레시피는 leader_search_mode='continuous'라고 적었지만 러너 build_cfg
    L81이 "grid"를 강제한다 — 러너 원문이 정답이므로 grid를 쓴다(문서화: context-notes).
    OPT12 2종(leader_skip_local_refinement/leader_rollout_early_stop)은 MPCConfig
    dataclass 필드가 아니라 여기 넣으면 TypeError — build_pstack_flagship_controller의
    setattr로만 주입한다. 플랜트 env(VFREE/RHO_CRIT/TAU_H 등)는 수치실험 플랜트 물리라
    복사 금지(VISSIM 캘리브레이션이 예측모델 기준).
    """
    return {
        "mpc": {
            # 러너 build_cfg L77-84 원문(HORIZON env 미설정 → default.yaml 3 유지).
            "horizon_steps": 3,
            "control_horizon_steps": 3,
            "leader_search_mode": "grid",
            "relaxed_quantized_controls": True,
            "stackelberg_leader_parallel_backend": "serial",
            "grid_parallel_backend": "serial",
            "grid_reuse_process_pool": False,
            # default.yaml 실효값(어댑터 base가 축소해 둔 예산 복원).
            "leader_candidate_count": 49,
            "leader_refinement_candidate_count": 25,
            "max_nash_iter": 10,
            "stackelberg_enable_fallback": True,
            "stackelberg_enable_pfo_incumbent": True,
            "stackelberg_allocation_mode": "direct",
            # make_controller L252-255: LEADER_V_DEPTH env 없고 cfg 0이면 depth 3.
            "leader_value_depth": 3,
            # run_job.sh env → cfg 번역(러너 L679-704, L894-896, L872-874, L602-628).
            "seg13_meter_box_veh_h": 300.0,     # METER_BOX=300
            "seg13_vsl_box_kmh": 20.0,          # VSL_BOX=15의 VISSIM DSD(20 간격) 보정값
            "leader_rollout_box_walk": True,    # BOX_WALK=1
            "leader_rollout_box_walk_vg": True, # BOX_WALK_VG=1
            "baseline_move_box": True,          # BASELINE_BOX=1
            "np_primal_dual_iters": 4,          # NP_PD_ITER=4
            "np_bias_correction": True,         # NP_BIAS=1
            "leader_mfd_far_state_aware": True, # FAR_STATE_AWARE=1
            "leader_mfd_far_real_speed": True,  # FAR_REAL_V=1
            # BIAS_SAMPLE=1 + BIAS_POW=0.4 (make_controller L268-273; 활성화 자체는
            # build_pstack_flagship_controller의 enable_biased_sampling에서).
            "leader_bias_sample_pow": 0.4,
        },
        "freeway_follower": {
            # 러너 실효 기본(default.yaml): VSL smoothness 0.0.
            # segment_metering_smoothness_weight는 여기서 건드리지 않는다 —
            # 러너와 동일하게 MS_ADAPT per-step 주입만 그 값을 결정한다.
            "vsl_smoothness_weight": 0.0,
        },
    }


def build_pstack_flagship_controller(cfg, tuning: Mapping[str, Any]):
    """P-STACK-WU-FAITHFUL-ALLPRICE-JOINT 컨트롤러 구성(러너 make_controller L244-316 이식).

    cfg 정식 키는 flagship_config_overrides()가 build_config 단계에서 이미 주입했다는
    전제. 여기서는 (1) 프로세스 env, (2) cfg.mpc 동적 속성, (3) controller/nash_solver
    인스턴스 속성을 러너와 같은 순서로 채운다.
    """
    settings = flagship_settings(tuning)
    # NASH_SMAX: src 내부에서 env로만 소비(wu_faithful_follower.py:3908-3912) —
    # min(max_nash_iter, 5) 하드캡 해제. 어댑터는 1회 실행 프로세스라 부작용 없음.
    os.environ["NASH_SMAX"] = str(int(_as_float(settings.get("nash_smax"), 10.0)))
    # OPT12(러너 L259-261): dataclass 필드가 아닌 동적 속성(stackelberg_mpc getattr 소비).
    if bool(settings.get("opt12", True)):
        cfg.mpc.leader_skip_local_refinement = True
        cfg.mpc.leader_rollout_early_stop = True

    from src.controllers.f1_wu_faithful_follower import F1StackelbergWuMeteredController

    controller = F1StackelbergWuMeteredController(cfg)
    # BIAS_SAMPLE(러너 L268-273): Halton 상단 warp. leader_bias_sample_pow(0.4)는 cfg
    # override로 주입 완료. 러너 build_cfg가 grid 검색을 강제하므로 continuous 샘플
    # 경로가 호출되지 않아 사실상 불활성이지만, 러너 원문 그대로 이식해 둔다
    # (tuning으로 leader_search_mode를 continuous로 바꾸면 그대로 발화).
    if bool(settings.get("bias_sample", True)):
        from src.controllers.biasedsample_mpc import enable_biased_sampling

        enable_biased_sampling(controller)
    controller.nash_solver.f1_spillback_weight = 0.0
    controller.signal_price_enabled = True
    controller.metering_price_enabled = True
    controller.vsl_price_enabled = True
    # cross 2종 기본 OFF(2026-07-16 동결 + run_job.sh CROSS_OFF=1).
    controller.green_offset_cross_price_enabled = False
    controller.vsl_meter_cross_price_enabled = False
    controller.nash_solver.joint_green_offset_enabled = True
    # OFFSET_PRICE 기본 ON + SQP식 inner-walk 4회(러너 L298-300).
    controller.offset_price_enabled = True
    controller.offset_price_inner_iters = 4
    # RAMP_OFFSET 기본 ON(러너 L303-304): D/F ramp-aware offset 탐색.
    controller.nash_solver.ramp_offset_enabled = True
    # metering δ=300 + trust_frac=0.20 — 반드시 짝(러너 L305-315).
    controller.metering_price_delta_veh_h = 300.0
    controller.metering_price_trust_frac = 0.20
    # SEG13(러너 L829-834): freeway를 segment agent로 분해 + 예산 simplex 사영.
    if hasattr(controller.nash_solver, "segment_agents"):
        controller.nash_solver.segment_agents = True
    return controller


def load_flagship_runtime(path: Path) -> dict[str, Any]:
    """사이드카 읽기. 부재/파손 시 빈 dict → 러너 첫 스텝과 동일(래치 0, prev 없음)."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except Exception:
        pass
    return {}


def save_flagship_runtime(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(data), ensure_ascii=False, indent=2), encoding="utf-8")


def flagship_link_mean_density(state) -> dict[str, float]:
    """러너 L1107-1108: 링크별 세그먼트 평균 밀도."""
    return {
        str(link): float(sum(values)) / len(values)
        for link, values in (getattr(state, "freeway_density", {}) or {}).items()
        if values
    }


def flagship_ms_adapt_update(
    prev_rho: Mapping[str, float],
    rho_now: Mapping[str, float],
    latch: int,
    thr: float,
    hold: int,
    w: float,
) -> tuple[float, int, float]:
    """MS_ADAPT 래치 갱신(러너 L1109-1113과 동일한 순수 함수 — 단위검증 대상).

    첫 스텝(prev 비어 있음)은 dmax=0 → latch max(0,-1)=0 → weight=w (러너와 동일).
    """
    dmax = max(
        (abs(float(v) - float(prev_rho[lk])) for lk, v in rho_now.items() if lk in prev_rho),
        default=0.0,
    )
    new_latch = int(hold) if dmax > float(thr) else max(0, int(latch) - 1)
    weight = 0.0 if new_latch else float(w)
    return float(dmax), new_latch, float(weight)


def flagship_far_gate_update(
    cfg,
    state,
    forecast,
    stress: bool,
    thr: float,
) -> tuple[bool, bool, bool, bool]:
    """FAR_GATE=3 갱신(러너 L1064-1096): capdrop 실측 히스테리시스 + 폐쇄 예보 선제 ON.

    반환: (fg_new, stress_latch, drop_seen, all_sub).
    VISSIM forecast는 freeway_lane_loss가 항상 비어 있어 예보 분기는 발화하지 않는다
    (실질 mode 2). 폐쇄 예보 입력이 생기면 그대로 mode 3으로 동작한다.
    """
    from src.models.metanet import desired_speed_kmh, segment_flow_veh_h

    rc = float(cfg.network.rho_crit)
    vf = float(cfg.network.v_free)
    all_sub = True
    drop_seen = False
    for link in cfg.network.freeway_links:
        dens = state.freeway_density.get(link, [])
        spds = state.freeway_speed.get(link, [])
        lns = getattr(state, "freeway_effective_lanes", {}).get(link, [])
        for i in range(len(dens)):
            rho = float(dens[i])
            if rho <= rc:
                continue
            all_sub = False
            lam = float(lns[i]) if i < len(lns) else float(cfg.network.freeway_lanes)
            v = float(spds[i]) if i < len(spds) else 0.0
            flow = segment_flow_veh_h(rho, v, lam)
            cap = segment_flow_veh_h(rc, desired_speed_kmh(rc, vf, rc), lam)
            if flow < float(thr) * cap:
                drop_seen = True
    if drop_seen:
        stress = True  # drop 발생 → ON 래치
    elif all_sub:
        stress = False  # 전 세그 임계 아래 = 회복 완료 → OFF
    fg_new = bool(stress)
    # mode 3 하이브리드: 예보 지평 내 차선 폐쇄가 있으면 선제 ON(래치는 불변 — 러너 동일).
    try:
        from src.models.demand import merge_freeway_lane_loss

        merged = merge_freeway_lane_loss(list(forecast))
        if any(float(v) > 0.0 for segs in merged.values() for v in segs.values()):
            fg_new = True
    except Exception:
        pass
    return fg_new, bool(stress), drop_seen, all_sub


def flagship_sup_score(control, state, forecast, cfg) -> float:
    """감독자 공통 채점(러너 _sup_score L947-959): h스텝 결합 rollout TTT + far cost-to-go."""
    from src.controllers.stackelberg_mpc import mfd_far_cost_to_go
    from src.simulation.coupling import run_coupled_interval

    s = state.copy()
    total = 0.0
    h = max(1, int(cfg.mpc.horizon_steps))
    for k in range(min(h, len(forecast))):
        res = run_coupled_interval(s, control, forecast[k], cfg)
        total += float(res.urban_ttt + res.freeway_ttt)
        s.time_sec += cfg.simulation.control_interval
    total += float(mfd_far_cost_to_go(cfg, s))
    return float(total)


def run_pstack_flagship_decision(
    cfg,
    state,
    forecast,
    previous,
    tuning: Mapping[str, Any],
    runtime_path: Path,
):
    """pstack-flagship 결정 1회: 사이드카 복원 → FAR_GATE/MS_ADAPT → decide → SUP_PFO.

    러너 run_one 루프(L1034-1176)의 한 스텝과 동일한 순서. 반환:
    (control, controller, metadata).
    """
    import copy as _copy

    metadata: dict[str, Any] = {}
    settings = flagship_settings(tuning)
    runtime = load_flagship_runtime(runtime_path)
    first_step = not bool(runtime)
    metadata["flagship_runtime_first_step"] = float(first_step)

    controller = build_pstack_flagship_controller(cfg, tuning)
    metadata.update(install_vissim_terminal_cost_objective(controller, cfg, tuning))
    metadata["flagship_nash_smax_env"] = _as_float(os.environ.get("NASH_SMAX"), 0.0)

    # SUP_PFO 준비(러너 L931-945): per-step cfg 변형(FAR_GATE/MS_ADAPT) **이전** 사본.
    # seg13 전용 박스는 `is not None` 가드라 반드시 None으로 되돌린다. 링크-PFO 이동
    # 한계는 baseline_move_box로 walk-MVG와 동일화.
    sup_settings = _mapping(settings.get("sup_pfo"))
    sup_enabled = bool(sup_settings.get("enabled", True))
    sup_gate = str(sup_settings.get("gate", "fargate"))
    sup_cfg = None
    if sup_enabled:
        sup_cfg = _copy.deepcopy(cfg)
        sup_cfg.mpc.seg13_meter_box_veh_h = None
        if hasattr(sup_cfg.mpc, "seg13_meter_box_up_veh_h"):
            sup_cfg.mpc.seg13_meter_box_up_veh_h = None
        sup_cfg.mpc.seg13_vsl_box_kmh = None
        # ZONE-4(2026-08-01): 감독자 PFO는 링크 모드(segment_agents=False)라 zone 구조를
        # 쓰지 않는다. 남겨두면 follower 진입부 가드가 "groups인데 SEG13이 꺼져 있다"로
        # 즉사시킨다 — seg13 박스 키와 동일 규약으로 되돌린다.
        if hasattr(sup_cfg.mpc, "freeway_agent_groups"):
            sup_cfg.mpc.freeway_agent_groups = None
        sup_cfg.mpc.baseline_move_box = True

    # FAR_GATE=3 (러너 L1048-1099).
    fg_settings = dict(FLAGSHIP_FAR_GATE_DEFAULTS)
    fg_settings.update(_mapping(settings.get("far_gate")))
    fargate_stress = bool(runtime.get("fargate_stress", False))
    if bool(fg_settings.get("enabled", True)):
        fg_new, fargate_stress, drop_seen, all_sub = flagship_far_gate_update(
            cfg,
            state,
            forecast,
            fargate_stress,
            _as_float(fg_settings.get("thr"), 0.95),
        )
        cfg.mpc.leader_mfd_far_enabled = bool(fg_new)
        metadata.update({
            "flagship_fargate_enabled": 1.0,
            "flagship_fargate_capdrop_seen": float(drop_seen),
            "flagship_fargate_all_subcritical": float(all_sub),
            "flagship_fargate_stress_latch": float(fargate_stress),
        })
    else:
        metadata["flagship_fargate_enabled"] = 0.0
    metadata["flagship_fargate_on"] = float(bool(cfg.mpc.leader_mfd_far_enabled))

    # MS_ADAPT (러너 L1106-1116). 결정 전에 마찰 가중을 주입한다.
    ms_settings = dict(FLAGSHIP_MS_ADAPT_DEFAULTS)
    ms_settings.update(_mapping(settings.get("ms_adapt")))
    ms_prev = {
        str(k): _as_float(v)
        for k, v in _mapping(runtime.get("ms_prev_rho")).items()
    }
    ms_latch = int(_as_float(runtime.get("ms_latch"), 0.0))
    rho_now = flagship_link_mean_density(state)
    if bool(ms_settings.get("enabled", True)):
        ms_dmax, ms_latch, ms_weight = flagship_ms_adapt_update(
            ms_prev,
            rho_now,
            ms_latch,
            _as_float(ms_settings.get("thr"), 10.0),
            int(_as_float(ms_settings.get("hold"), 5.0)),
            _as_float(ms_settings.get("w"), 0.013),
        )
        cfg.freeway_follower.segment_metering_smoothness_weight = float(ms_weight)
        metadata.update({
            "flagship_ms_adapt_enabled": 1.0,
            "flagship_ms_dmax": float(ms_dmax),
            "flagship_ms_latch": float(ms_latch),
        })
    else:
        metadata["flagship_ms_adapt_enabled"] = 0.0
    metadata["flagship_ms_friction"] = float(
        getattr(cfg.freeway_follower, "segment_metering_smoothness_weight", 0.0)
    )

    # 사이드카는 decide 이전에 저장 — 결정이 실패(fallback_fixed)해도 상태 전이
    # 관측치(직전 밀도·래치)는 다음 스텝에 이어진다.
    save_flagship_runtime(runtime_path, {
        "schema_version": 1,
        "sim_sec": float(getattr(state, "time_sec", 0.0)),
        "ms_prev_rho": rho_now,
        "ms_latch": int(ms_latch),
        "fargate_stress": bool(fargate_stress),
    })

    result = controller.decide_with_info(state.copy(), forecast, previous, cfg)
    control = result.control
    metadata["leader_objective"] = float(getattr(result, "leader_objective", 0.0))
    metadata["nash_objective"] = float(getattr(getattr(result, "nash", None), "objective_value", 0.0))
    metadata.update({
        f"meta_{k}": float(v)
        for k, v in getattr(result, "metadata", {}).items()
        if isinstance(v, (int, float, bool))
    })

    # SUP_PFO + SUP_GATE=fargate (러너 L1151-1176): far 게이트 ON 스텝은 감독자 OFF
    # (동일한 물리 조건이 far를 부르고 감독자를 쫓아낸다 — 단일 게이트, 이중 스위치).
    sup_off = sup_gate == "fargate" and bool(cfg.mpc.leader_mfd_far_enabled)
    metadata["flagship_sup_enabled"] = float(sup_enabled)
    metadata["flagship_sup_gated_off"] = float(bool(sup_enabled and sup_off))
    if sup_enabled and not sup_off and sup_cfg is not None:
        from src.controllers.wu_faithful_follower import WuFaithfulFollower

        sup_pfo = WuFaithfulFollower(sup_cfg)
        try:
            pfo_control = sup_pfo.solve(state.copy(), None, forecast, previous).control
        finally:
            if hasattr(sup_pfo, "close"):
                try:
                    sup_pfo.close()
                except Exception:
                    pass
        v_ps = flagship_sup_score(control, state, forecast, cfg)
        v_pfo = flagship_sup_score(pfo_control, state, forecast, cfg)
        if v_pfo < v_ps - 1.0e-9:
            pfo_control.diagnostics["sup_pick_pfo"] = 1.0
            pfo_control.diagnostics["sup_v_pstack"] = v_ps
            pfo_control.diagnostics["sup_v_pfo"] = v_pfo
            control = pfo_control
        else:
            control.diagnostics["sup_pick_pfo"] = 0.0
            control.diagnostics["sup_v_pstack"] = v_ps
            control.diagnostics["sup_v_pfo"] = v_pfo
        metadata["flagship_sup_pick_pfo"] = float(control.diagnostics["sup_pick_pfo"])
        metadata["flagship_sup_v_pstack"] = float(v_ps)
        metadata["flagship_sup_v_pfo"] = float(v_pfo)
    return control, controller, metadata


def build_config(
    repo_root: Path,
    control_interval: float,
    sim_period: float,
    mode: str,
    calibration: Mapping[str, Any],
    tuning: Mapping[str, Any],
    local_observation: bool = False,
    flagship: bool = False,
):
    _, _, _, ExperimentConfig, _, _ = repo_imports(repo_root)
    config_path = repo_root / "src/config/default.yaml"
    # This is intentionally a light Vissim-integration profile. The full offline
    # controller can be much heavier; for COM smoke/control-loop use we keep a
    # short horizon and serial execution.
    overrides: dict[str, Any] = {
        "simulation": {
            "T_total": max(float(sim_period), float(control_interval)),
            "T_f": 10.0,
            "T_u": 5.0,
            "control_interval": float(control_interval),
        },
        "network": {
            "freeway_links": ["FW_W", "FW_E"],
            "freeway_segments_per_link": 8,
            "freeway_segment_length_km": 0.444,
            "freeway_lanes": 2,
            "v_free": 123.825,
            "rho_crit": 20.401,
            "freeway_capacity_veh_h": 4574.818,
            "lost_time": 6.0,
            "movement_capacity_veh_h": 1800.0,
            "ramp_capacity_veh_h": {
                "R_D_W": 1414.0,
                "R_F_W": 316.0,
                "R_D_E": 1414.0,
                "R_F_E": 316.0,
            },
            # Vissim 8-seg mainline topology (2026-07-14, one ramp junction per
            # segment, indices in travel direction):
            #   FW_E: S0/S1 entry+approach, S2 OR_D diverge, S3 R_D merge,
            #         S4 OR_F diverge, S5 R_F merge, S6/S7 exit
            #   FW_W: S0/S1 entry+approach, S2 OR_F diverge, S3 R_F merge,
            #         S4 OR_D diverge, S5 R_D merge, S6/S7 exit
            #
            # Matches the 8-seg default.yaml (off 2/4, merge 3/5) except that
            # the yaml's hypothetical network puts D first in BOTH directions;
            # the Vissim plant passes F first westbound, so the _W indices are
            # swapped relative to the yaml (same travel-direction convention as
            # the 5-seg adapter override before it).
            "ramp_merge_segment_index": {
                "R_D_W": 5,
                "R_F_W": 3,
                "R_D_E": 3,
                "R_F_E": 5,
            },
            "off_ramp_segment_index": {
                "OR_D_W": 4,
                "OR_F_W": 2,
                "OR_D_E": 2,
                "OR_F_E": 4,
            },
        },
        "mpc": {
            "horizon_steps": 1,
            "control_horizon_steps": 1,
            "follower_solver_mode": "distributed" if local_observation else "two_block",
            "leader_search_mode": "grid",
            "leader_candidate_count": 1 if local_observation and mode == "fast-smoke" else 3,
            "leader_refinement_candidate_count": 1,
            "max_nash_iter": 1,
            "distributed_coupling_tol": 0.05 if local_observation else 0.001,
            "relaxed_quantized_controls": bool(local_observation),
            "stackelberg_allocation_mode": "simplified" if local_observation else "direct",
            "stackelberg_enable_fallback": False,
            "stackelberg_leader_parallel_backend": "serial",
            "grid_parallel_backend": "serial",
            "grid_reuse_process_pool": False,
            "leader_continuous_parallel_multistart": False,
        },
        "leader": {
            "N_P_crit_veh": 390.0,
            "mfd_penalty_mode": "all_urban_halfcap",
            "N_P_star_range": [0.0, 780.0],
            "N_UF_star_range": [0.0, 5000.0],
        },
        "freeway_follower": {
            "vsl_set": [60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0],
            "vsl_max_km_h": 120.0,
            "horizon_beam_width": 1 if local_observation else 2,
            "horizon_ramp_candidate_limit": 1 if local_observation else 3,
            "horizon_vsl_candidate_limit_per_link": 1 if local_observation else 3,
        },
        "urban_follower": {
            "allocation_pso_particles": 4 if local_observation else 18,
            "allocation_pso_iterations": 4 if local_observation else 24,
        },
    }
    if flagship:
        # 적용 순서: base < flagship < calibration < tuning (plan.md 결정).
        overrides = deep_update(overrides, flagship_config_overrides())
    overrides = deep_update(overrides, calibration_to_config_overrides(calibration))
    overrides = deep_update(overrides, tuning_to_config_overrides(tuning))
    if mode == "fuller-smoke":
        overrides["mpc"].update({
            "leader_candidate_count": 5,
            "max_nash_iter": 2,
        })
    return ExperimentConfig.from_file(config_path, overrides=overrides)


def profiled_demand_rates(
    state_json: Mapping[str, Any],
    cfg,
    calibration: Mapping[str, Any] | None = None,
    detector_mapping: Mapping[str, Any] | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, float], str]:
    """Mirror the Vissim runner's demand-profile multipliers in the model forecast.

    `run_stackelberg_vissim_controller.vbs` applies demand profiles at the
    VehicleInput level. Before this adapter-side mirror, the one-step METANET
    prediction treated every freeway direction and every urban boundary input
    as symmetric even when Vissim was running `fw_eb_heavy`, `urban_d_heavy`,
    etc. That creates a biased prediction target before calibration even
    starts.
    """
    demand = state_json.get("demand", {})
    if not isinstance(demand, Mapping):
        demand = {}
    urban_vph = float(demand.get("urban_volume_vph", 60.0))
    freeway_vph = float(demand.get("freeway_volume_vph", 1200.0))
    ramp_vph = float(demand.get("ramp_volume_vph", max(120.0, freeway_vph * 0.12)))
    profile = str(demand.get("demand_profile", "")).lower()
    urban_west_east_ratio = max(1.0e-6, _as_float(demand.get("urban_west_east_ratio"), 1.0))

    freeway_mainline = {str(link): freeway_vph for link in cfg.network.freeway_links}
    urban_boundary = {
        str(link): urban_vph
        for link in list(cfg.network.boundary_in_links) + list(cfg.network.boundary_out_links)
    }
    ramp_arrival = {str(ramp): ramp_vph for ramp in cfg.network.ramps}

    if profile == "fw_eb_heavy":
        freeway_mainline["FW_E"] = freeway_vph * 1.55
        freeway_mainline["FW_W"] = freeway_vph * 0.55
    elif profile == "fw_wb_heavy":
        freeway_mainline["FW_W"] = freeway_vph * 1.55
        freeway_mainline["FW_E"] = freeway_vph * 0.55

    def set_urban_profile(high_links: set[str], high_factor: float, low_factor: float) -> None:
        for link in cfg.network.boundary_in_links:
            urban_boundary[str(link)] = urban_vph * (high_factor if str(link) in high_links else low_factor)
        # boundary_out links are not used as exogenous arrivals by the movement
        # queue model, but keep them populated for diagnostics/compatibility.
        for link in cfg.network.boundary_out_links:
            urban_boundary[str(link)] = urban_vph * low_factor

    if profile == "urban_west_heavy":
        set_urban_profile({"in_A_left", "in_D_left"}, 1.8, 0.65)
    elif profile == "urban_east_heavy":
        set_urban_profile({"in_C_right", "in_F_right"}, 1.8, 0.65)
    elif profile == "urban_north_heavy":
        set_urban_profile({"in_A_top", "in_B_top", "in_C_top"}, 1.65, 0.6)
    elif profile == "urban_d_heavy":
        set_urban_profile({"in_D_left"}, 2.2, 0.65)
    elif profile == "urban_f_heavy":
        set_urban_profile({"in_F_right"}, 2.2, 0.65)

    if abs(urban_west_east_ratio - 1.0) > 1.0e-9:
        west_factor = 2.0 * urban_west_east_ratio / (1.0 + urban_west_east_ratio)
        east_factor = 2.0 / (1.0 + urban_west_east_ratio)
        for link in cfg.network.boundary_in_links:
            key = str(link)
            if key in {"in_A_left", "in_D_left"}:
                urban_boundary[key] = urban_boundary.get(key, urban_vph) * west_factor
            elif key in {"in_C_right", "in_F_right"}:
                urban_boundary[key] = urban_boundary.get(key, urban_vph) * east_factor

    # Route-aware on-ramp forecast (2026-06-30): the hardcoded uniform ramp_vph (250/ramp) under-sizes
    # and mis-directs the on-ramp arrival. The VISSIM static routes send a fixed fraction of each urban
    # origin's demand onto the D on-ramp (link 25 -> FW_WB -> R_D_W) and F on-ramp (link 31 -> FW_EB ->
    # R_F_E); at u1400 this is ~1032 vph per direction (~2x the 1000 vph total forecast). Sizing N_UF to
    # the under-forecast made the leader meter the on-ramps below the real demand -> ramp queues -> harm.
    # ramp_share_of_urban_in[ramp] = (routing fraction onto that ramp) so ramp_arrival = share x total
    # urban boundary-in demand (which already carries the profile multipliers above).
    onramp_fc = _mapping(_mapping(calibration or {}).get("prediction")).get("onramp_route_forecast", {})
    if bool(_mapping(onramp_fc).get("enabled", False)):
        total_urban_in = sum(
            _as_float(urban_boundary.get(str(link), 0.0)) for link in cfg.network.boundary_in_links
        )
        shares = _mapping(_mapping(onramp_fc).get("ramp_share_of_urban_in"))
        for ramp in cfg.network.ramps:
            ramp_arrival[str(ramp)] = max(0.0, _as_float(shares.get(str(ramp), 0.0))) * total_urban_in

    route_bias = _mapping(_mapping(calibration or {}).get("prediction")).get("route_bias_forecast", {})
    route_bias = _mapping(route_bias)
    route_bias_enabled = bool(route_bias.get("enabled", True))
    route_bias_version = int(_as_float(route_bias.get("version"), 1.0))
    target_share = clamp(_as_float(route_bias.get("target_share"), 0.98), 0.5, 1.0)

    # v1 (legacy, demoted candidate): preserve total ramp demand and split the target node's ramp
    # pair by target_share. This is direction-agnostic and ties magnitude to a hardcoded ramp_vph.
    def apply_ramp_route_bias_v1(target_node: str) -> None:
        ramps = [str(ramp) for ramp in cfg.network.ramps]
        if not ramps:
            return
        target_prefix = f"R_{target_node}_"
        target_ramps = [ramp for ramp in ramps if ramp.startswith(target_prefix)]
        other_ramps = [ramp for ramp in ramps if ramp not in target_ramps]
        if not target_ramps or not other_ramps:
            return
        total_arrival_vph = ramp_vph * float(len(ramps))
        target_each = total_arrival_vph * target_share / float(len(target_ramps))
        other_each = total_arrival_vph * (1.0 - target_share) / float(len(other_ramps))
        for ramp in target_ramps:
            ramp_arrival[ramp] = target_each
        for ramp in other_ramps:
            ramp_arrival[ramp] = other_each

    # v2 (direction-aware, 2026-06-29 audit follow-up): VISSIM d/f_ramp_bias funnels biased flow
    # through ONE physical on-ramp toward ONE freeway direction (link 25 -> FW_WB, link 31 -> FW_EB;
    # run_stackelberg_vissim_controller.vbs ApplyRouteBias). v1 wrongly split the boost across both
    # directional ramps of the node and preserved a hardcoded total. v2 loads the direction-feeding
    # ramp with a fittable multiplier on ramp_vph, gives the same-node cross-direction ramp a small
    # share, and starves the other node's ramps. Total ramp demand is intentionally NOT preserved.
    v2 = _mapping(route_bias.get("v2"))
    v2_target_multiplier = max(0.0, _as_float(v2.get("target_multiplier"), 4.0))
    v2_cross_share = max(0.0, _as_float(v2.get("cross_share"), 0.15))
    v2_off_share = max(0.0, _as_float(v2.get("off_share"), 0.02))
    v2_direction_feed = _mapping(v2.get("direction_feed"))

    def apply_ramp_route_bias_v2(target_node: str) -> None:
        ramps = [str(ramp) for ramp in cfg.network.ramps]
        if not ramps:
            return
        target_prefix = f"R_{target_node}_"
        node_ramps = [ramp for ramp in ramps if ramp.startswith(target_prefix)]
        if not node_ramps:
            return
        ramp_to_freeway = getattr(cfg.network, "ramp_to_freeway", {}) or {}
        feed = str(v2_direction_feed.get(profile, ""))
        if feed not in node_ramps:
            wanted_dir = "FW_W" if target_node == "D" else "FW_E"
            feed = next(
                (r for r in node_ramps if str(ramp_to_freeway.get(r, "")) == wanted_dir),
                node_ramps[0],
            )
        for ramp in ramps:
            if ramp == feed:
                ramp_arrival[ramp] = ramp_vph * v2_target_multiplier
            elif ramp in node_ramps:
                ramp_arrival[ramp] = ramp_vph * v2_cross_share
            else:
                ramp_arrival[ramp] = ramp_vph * v2_off_share

    apply_ramp_route_bias = (
        apply_ramp_route_bias_v2 if route_bias_version >= 2 else apply_ramp_route_bias_v1
    )
    if route_bias_enabled:
        if profile in {"d_ramp_bias", "d_ramp_heavy"}:
            apply_ramp_route_bias("D")
        elif profile in {"f_ramp_bias", "f_ramp_heavy"}:
            apply_ramp_route_bias("F")

    local_fc = _mapping(_mapping(calibration or {}).get("prediction")).get(
        "local_ramp_arrival_forecast",
        {},
    )
    local_fc = _mapping(local_fc)
    if bool(local_fc.get("enabled", False)):
        observed_counts = {str(ramp): 0.0 for ramp in cfg.network.ramps}
        direct_counts = _mapping(state_json.get("ramp_counts"))
        has_model_ramp_counts = any(str(ramp) in direct_counts for ramp in observed_counts)
        if has_model_ramp_counts:
            for ramp in observed_counts:
                observed_counts[ramp] = max(0.0, _as_float(direct_counts.get(ramp), 0.0))
        else:
            d_count = max(0.0, _as_float(direct_counts.get("D"), 0.0))
            f_count = max(0.0, _as_float(direct_counts.get("F"), 0.0))
            for ramp in observed_counts:
                if ramp.startswith("R_D_"):
                    observed_counts[ramp] = d_count / 2.0
                elif ramp.startswith("R_F_"):
                    observed_counts[ramp] = f_count / 2.0
        if not any(value > 0.0 for value in observed_counts.values()) and detector_mapping:
            link_counts = _link_counts_from_local_observation(state_json)
            for link, ramps in _mapping(detector_mapping.get("ramp_link_to_queues")).items():
                count = max(0.0, _as_float(link_counts.get(str(link)), 0.0))
                if count <= 0.0 or not isinstance(ramps, list) or not ramps:
                    continue
                share = count / float(len(ramps))
                for ramp in ramps:
                    ramp_key = str(ramp)
                    if ramp_key in observed_counts:
                        observed_counts[ramp_key] += share
        queue_drain_horizon_sec = max(1.0, _as_float(local_fc.get("queue_drain_horizon_sec"), 120.0))
        multiplier = max(0.0, _as_float(local_fc.get("multiplier"), 1.0))
        min_vph = max(0.0, _as_float(local_fc.get("min_vph_if_observed"), 120.0))
        max_default = max(0.0, _as_float(local_fc.get("max_vph_per_ramp"), 900.0))
        max_by_ramp = _mapping(local_fc.get("max_vph_by_ramp"))
        blend = str(local_fc.get("blend", "max")).lower()
        for ramp, count in observed_counts.items():
            if count <= 0.0:
                continue
            observed_vph = count * 3600.0 / queue_drain_horizon_sec * multiplier
            if observed_vph > 0.0:
                observed_vph = max(min_vph, observed_vph)
            cap_fallback = float(cfg.network.ramp_capacity_veh_h.get(ramp, max_default))
            cap = max(0.0, _as_float(max_by_ramp.get(ramp), max_default or cap_fallback))
            if cap <= 0.0:
                cap = cap_fallback
            observed_vph = clamp(observed_vph, 0.0, cap)
            if blend == "replace":
                ramp_arrival[ramp] = observed_vph
            elif blend == "add":
                ramp_arrival[ramp] = max(0.0, float(ramp_arrival.get(ramp, 0.0)) + observed_vph)
            else:
                ramp_arrival[ramp] = max(float(ramp_arrival.get(ramp, 0.0)), observed_vph)

    return freeway_mainline, urban_boundary, ramp_arrival, profile


def demand_from_state(
    state_json: dict[str, Any],
    cfg,
    DemandStep,
    horizon_steps: int,
    calibration: Mapping[str, Any] | None = None,
    detector_mapping: Mapping[str, Any] | None = None,
):
    freeway_mainline, urban_boundary, ramp_arrival, _profile = profiled_demand_rates(
        state_json,
        cfg,
        calibration,
        detector_mapping,
    )
    step = DemandStep(
        freeway_mainline=freeway_mainline,
        urban_boundary=urban_boundary,
        ramp_arrival=ramp_arrival,
        incident_capacity_factor=1.0,
        freeway_lane_loss={},
    )
    return [step for _ in range(max(1, int(horizon_steps)))]


def traffic_state_from_vissim(
    state_json: dict[str, Any],
    cfg,
    TrafficState,
    detector_mapping: Mapping[str, Any] | None = None,
    calibration: Mapping[str, Any] | None = None,
):
    state = TrafficState.initial(cfg)
    state.time_sec = float(state_json.get("sim_sec", 0.0))
    state.ensure_freeway_lane_profile(cfg.network)

    segs = state_json.get("freeway_segments", {})
    for link in cfg.network.freeway_links:
        rows = list(segs.get(link, []))
        densities: list[float] = []
        speeds: list[float] = []
        flows: list[float] = []
        lanes_profile: list[float] = []
        for i in range(cfg.network.freeway_segments_per_link):
            row = rows[i] if i < len(rows) and isinstance(rows[i], dict) else {}
            count = max(0.0, float(row.get("count", 0.0)))
            speed_sum = max(0.0, float(row.get("speed_sum", 0.0)))
            length_km = max(1.0e-6, float(row.get("length_km", cfg.network.freeway_segment_length_km)))
            lanes = max(1.0, float(row.get("lanes", cfg.network.freeway_lanes)))
            speed = speed_sum / count if count > 1.0e-9 else float(cfg.network.v_free)
            density = count / (length_km * lanes)
            densities.append(float(density))
            speeds.append(float(speed))
            flows.append(float(density * speed * lanes))
            lanes_profile.append(float(lanes))
        state.freeway_density[link] = densities
        state.freeway_speed[link] = speeds
        state.freeway_flow[link] = flows
        state.freeway_effective_lanes[link] = lanes_profile

    local_summary = (
        build_local_observation_summary(state_json, cfg, detector_mapping, calibration)
        if detector_mapping
        else {}
    )
    if local_summary:
        for key in state.ramp_queue:
            state.ramp_queue[key] = float(local_summary["ramp_queue"].get(key, 0.0))
        for key in state.boundary_queue:
            state.boundary_queue[key] = float(local_summary["boundary_queue"].get(key, 0.0))
        for key in state.urban_movement_queue:
            state.urban_movement_queue[key] = float(local_summary["urban_movement_queue"].get(key, 0.0))
        storage_occupancy = local_summary.get("urban_link_storage_occupancy", {})
        if isinstance(storage_occupancy, Mapping):
            for link, capacity in cfg.network.urban_link_storage_veh.items():
                occupied = clamp(
                    _as_float(storage_occupancy.get(link, 0.0)),
                    0.0,
                    float(capacity),
                )
                state.urban_link_storage[link] = float(capacity) - occupied
        state.local_observation_summary = local_summary
    else:
        ramp_counts = state_json.get("ramp_counts", {})
        if isinstance(ramp_counts, Mapping) and any(str(key) in ramp_counts for key in state.ramp_queue):
            for key in state.ramp_queue:
                state.ramp_queue[key] = max(0.0, _as_float(ramp_counts.get(str(key), 0.0)))
        else:
            d_queue = max(0.0, float(ramp_counts.get("D", 0.0)))
            f_queue = max(0.0, float(ramp_counts.get("F", 0.0)))
            state.ramp_queue.update({
                "R_D_W": d_queue / 2.0,
                "R_D_E": d_queue / 2.0,
                "R_F_W": f_queue / 2.0,
                "R_F_E": f_queue / 2.0,
            })

        # Legacy global-state fallback for old state files. Local detector
        # observation must be preferred whenever it is present.
        urban_total = max(0.0, float(state_json.get("urban_vehicles", 0.0)))
        boundary_total = max(0.0, float(state_json.get("boundary_vehicles", 0.0)))
        if state.boundary_queue:
            per = boundary_total / max(1, len(state.boundary_queue))
            for key in state.boundary_queue:
                state.boundary_queue[key] = per
        if state.urban_movement_queue:
            protected_kinds = {"internal", "boundary_out", "off_ramp"}
            protected_movements = [
                movement
                for movement, spec in cfg.network.urban_movements.items()
                if str(spec.get("kind", "")) in protected_kinds
                and movement in state.urban_movement_queue
            ]
            boundary_in_movements = [
                movement
                for movement, spec in cfg.network.urban_movements.items()
                if str(spec.get("kind", "")) == "boundary_in"
                and movement in state.urban_movement_queue
            ]
            for key in state.urban_movement_queue:
                state.urban_movement_queue[key] = 0.0
            if protected_movements:
                per_protected = urban_total / max(1, len(protected_movements))
                for key in protected_movements:
                    state.urban_movement_queue[key] = per_protected
            elif state.urban_movement_queue:
                per = urban_total / max(1, len(state.urban_movement_queue))
                for key in state.urban_movement_queue:
                    state.urban_movement_queue[key] = per
            if boundary_in_movements:
                per_boundary = boundary_total / max(1, len(boundary_in_movements))
                for key in boundary_in_movements:
                    state.urban_movement_queue[key] = per_boundary
    return state


def control_from_json(path: Path, cfg, ControlAction):
    if not path.exists():
        return ControlAction.fixed(cfg)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ControlAction(
        N_P_star=float(raw.get("N_P_star", 0.0)),
        N_UF_star=float(raw.get("N_UF_star", 0.0)),
        ramp_metering={str(k): float(v) for k, v in raw.get("ramp_metering", {}).items()},
        vsl={str(k): float(v) for k, v in raw.get("vsl", {}).items()},
        green_times={str(k): float(v) for k, v in raw.get("green_times", {}).items()},
        offsets={str(k): float(v) for k, v in raw.get("offsets", {}).items()},
        inflow_outflow_allocation={
            str(k): float(v) for k, v in raw.get("inflow_outflow_allocation", {}).items()
        },
        diagnostics=dict(raw.get("diagnostics", {})),
    )


def control_to_json_dict(
    control,
    metadata: dict[str, Any],
    prediction: dict[str, Any] | None = None,
    prediction_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "N_P_star": float(control.N_P_star),
        "N_UF_star": float(control.N_UF_star),
        "ramp_metering": {str(k): float(v) for k, v in control.ramp_metering.items()},
        "vsl": {str(k): float(v) for k, v in control.vsl.items()},
        "green_times": {str(k): float(v) for k, v in control.green_times.items()},
        "offsets": {str(k): float(v) for k, v in control.offsets.items()},
        "inflow_outflow_allocation": {
            str(k): float(v) for k, v in control.inflow_outflow_allocation.items()
        },
        "diagnostics": dict(control.diagnostics),
        "metadata": metadata,
    }
    if prediction:
        payload["prediction"] = prediction
    if prediction_error:
        payload["prediction_error"] = prediction_error
    return payload


PREDICTION_AUDIT_SCALARS = [
    "total_model_vehicles",
    "urban_total_veh",
    "protected_accumulation_veh",
    "urban_queue_plus_link_occupancy_total_veh",
    "urban_movement_queue_total_veh",
    "urban_link_occupancy_total_veh",
    "boundary_queue_total_veh",
    "freeway_total_veh",
    "freeway_segment_total_veh",
    "off_ramp_storage_veh",
    "ramp_queue_total_veh",
    "mainline_origin_queue_total_veh",
    "freeway_mean_density_veh_km_lane",
    "freeway_mean_speed_kph",
]


def summarize_model_state(state, cfg) -> dict[str, Any]:
    net = cfg.network
    state.ensure_freeway_lane_profile(net)
    freeway_counts = _freeway_vehicle_count_by_link(state, cfg)
    freeway_segment_counts = {
        link: [float(v) for v in freeway_counts.get(link, [])]
        for link in net.freeway_links
    }
    freeway_segment_total = float(sum(sum(values) for values in freeway_segment_counts.values()))
    speed_weight = 0.0
    vehicle_weight = 0.0
    density_sum = 0.0
    density_n = 0
    for link in net.freeway_links:
        speeds = list(state.freeway_speed.get(link, []))
        densities = list(state.freeway_density.get(link, []))
        counts = freeway_counts.get(link, [])
        for i, rho in enumerate(densities):
            density_sum += float(rho)
            density_n += 1
            count = float(counts[i]) if i < len(counts) else 0.0
            speed = float(speeds[i]) if i < len(speeds) else float(net.v_free)
            speed_weight += speed * max(0.0, count)
            vehicle_weight += max(0.0, count)
    urban_link_occupancy = 0.0
    for link, capacity in net.urban_link_storage_veh.items():
        urban_link_occupancy += max(0.0, float(capacity) - float(state.urban_link_storage.get(link, capacity)))
    ramp_queue_total = float(sum(max(0.0, float(v)) for v in state.ramp_queue.values()))
    mainline_origin_queue_total = float(
        sum(max(0.0, float(v)) for v in state.mainline_origin_queue.values())
    )
    urban_total = float(state.total_urban_vehicles(net))
    freeway_total = freeway_segment_total
    off_ramp_storage = float(state.off_ramp_storage_occupancy_veh(net))
    return {
        "time_sec": float(getattr(state, "time_sec", 0.0)),
        "total_model_vehicles": float(urban_total + freeway_total + off_ramp_storage),
        "urban_total_veh": urban_total,
        "protected_accumulation_veh": float(state.protected_accumulation_veh(net)),
        "urban_queue_plus_link_occupancy_total_veh": float(
            sum(max(0.0, float(v)) for v in state.urban_movement_queue.values())
            + urban_link_occupancy
        ),
        "urban_movement_queue_total_veh": float(
            sum(max(0.0, float(v)) for v in state.urban_movement_queue.values())
        ),
        "urban_link_occupancy_total_veh": float(urban_link_occupancy),
        "boundary_queue_total_veh": float(sum(max(0.0, float(v)) for v in state.boundary_queue.values())),
        "freeway_total_veh": freeway_total,
        "freeway_segment_total_veh": freeway_segment_total,
        "off_ramp_storage_veh": off_ramp_storage,
        "ramp_queue_total_veh": ramp_queue_total,
        "mainline_origin_queue_total_veh": mainline_origin_queue_total,
        "freeway_mean_density_veh_km_lane": float(density_sum / density_n) if density_n else 0.0,
        "freeway_mean_speed_kph": float(speed_weight / vehicle_weight) if vehicle_weight > 1.0e-9 else float(net.v_free),
        "ramp_queue": {str(k): float(v) for k, v in sorted(state.ramp_queue.items())},
        "freeway_segment_vehicles": freeway_segment_counts,
    }


def apply_prediction_audit_calibration(
    summary: Mapping[str, Any],
    calibration: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, float]]:
    prediction = _mapping((calibration or {}).get("prediction"))
    audit = _mapping(prediction.get("audit_calibration"))
    if not audit:
        return {}, {}

    enabled = bool(audit.get("enabled", True))
    if not enabled:
        return {}, {}

    freeway_scale = _as_float(
        audit.get("freeway_total_scale", audit.get("freeway_total_observed_over_predicted_mean")),
        1.0,
    )
    urban_mass_scale = _as_float(
        audit.get(
            "urban_queue_plus_storage_scale",
            audit.get("urban_queue_plus_storage_observed_over_predicted_mean"),
        ),
        1.0,
    )
    if not (0.05 <= freeway_scale <= 5.0):
        freeway_scale = 1.0
    if not (0.05 <= urban_mass_scale <= 5.0):
        urban_mass_scale = 1.0

    calibrated = dict(summary)
    metadata: dict[str, float] = {}
    old_freeway = _as_float(summary.get("freeway_total_veh"), 0.0)
    old_freeway_segment = _as_float(summary.get("freeway_segment_total_veh"), old_freeway)
    new_freeway = old_freeway * freeway_scale
    new_freeway_segment = old_freeway_segment * freeway_scale
    calibrated["freeway_total_veh"] = float(new_freeway)
    calibrated["freeway_segment_total_veh"] = float(new_freeway_segment)
    calibrated["freeway_mean_density_veh_km_lane"] = float(
        _as_float(summary.get("freeway_mean_density_veh_km_lane"), 0.0) * freeway_scale
    )
    calibrated["total_model_vehicles"] = float(
        _as_float(summary.get("total_model_vehicles"), 0.0) + (new_freeway - old_freeway)
    )
    segment_vehicles = summary.get("freeway_segment_vehicles", {})
    if isinstance(segment_vehicles, Mapping):
        calibrated["freeway_segment_vehicles"] = {
            str(link): [
                float(_as_float(value) * freeway_scale)
                for value in values
            ]
            for link, values in segment_vehicles.items()
            if isinstance(values, list)
        }

    component_scales = _mapping(audit.get("component_scales"))
    recompute_queue_storage = bool(
        audit.get(
            "recompute_urban_queue_plus_storage_from_components",
            audit.get("preserve_component_consistency", False),
        )
    )
    recompute_urban_total = bool(
        audit.get(
            "recompute_urban_total_from_components",
            audit.get("preserve_component_consistency", False),
        )
    )
    recompute_model_total = bool(
        audit.get(
            "recompute_total_model_vehicles_from_components",
            audit.get("preserve_component_consistency", False),
        )
    )
    scale_aliases = {
        "total_model_vehicles": "total_model_vehicles_scale",
        "urban_total_veh": "urban_total_scale",
        "protected_accumulation_veh": "protected_accumulation_scale",
        "urban_movement_queue_total_veh": "urban_movement_queue_scale",
        "urban_link_occupancy_total_veh": "urban_link_occupancy_scale",
        "boundary_queue_total_veh": "boundary_queue_scale",
        "off_ramp_storage_veh": "off_ramp_storage_scale",
        "ramp_queue_total_veh": "ramp_queue_scale",
        "mainline_origin_queue_total_veh": "mainline_origin_queue_scale",
        "freeway_mean_speed_kph": "freeway_mean_speed_scale",
    }
    already_scaled = {
        "freeway_total_veh",
        "freeway_segment_total_veh",
        "freeway_mean_density_veh_km_lane",
        "urban_queue_plus_link_occupancy_total_veh",
    }
    scaled_metrics: set[str] = set()
    for metric, alias in scale_aliases.items():
        raw_scale = component_scales.get(metric, audit.get(alias))
        if raw_scale is None or metric in already_scaled or metric not in summary:
            continue
        scale = _as_float(raw_scale, 1.0)
        if not (0.05 <= scale <= 5.0):
            continue
        calibrated[metric] = float(_as_float(summary.get(metric), 0.0) * scale)
        metadata[f"prediction_audit_{metric}_scale"] = float(scale)
        scaled_metrics.add(metric)

    if "urban_queue_plus_link_occupancy_total_veh" in summary:
        if recompute_queue_storage and {
            "urban_movement_queue_total_veh",
            "urban_link_occupancy_total_veh",
        } & scaled_metrics:
            calibrated["urban_queue_plus_link_occupancy_total_veh"] = float(
                _as_float(calibrated.get("urban_movement_queue_total_veh"), 0.0)
                + _as_float(calibrated.get("urban_link_occupancy_total_veh"), 0.0)
            )
            metadata["prediction_audit_urban_queue_plus_storage_recomputed"] = 1.0
        else:
            calibrated["urban_queue_plus_link_occupancy_total_veh"] = float(
                _as_float(summary.get("urban_queue_plus_link_occupancy_total_veh"), 0.0)
                * urban_mass_scale
            )

    if recompute_urban_total and {
        "urban_movement_queue_total_veh",
        "urban_link_occupancy_total_veh",
        "off_ramp_storage_veh",
    } & scaled_metrics:
        movement = _as_float(calibrated.get("urban_movement_queue_total_veh"), 0.0)
        link_occupancy = _as_float(calibrated.get("urban_link_occupancy_total_veh"), 0.0)
        off_ramp_storage = _as_float(calibrated.get("off_ramp_storage_veh"), 0.0)
        calibrated["urban_total_veh"] = float(movement + max(0.0, link_occupancy - off_ramp_storage))
        metadata["prediction_audit_urban_total_recomputed"] = 1.0

    if recompute_model_total and {
        "urban_total_veh",
        "freeway_total_veh",
        "off_ramp_storage_veh",
        "urban_movement_queue_total_veh",
        "urban_link_occupancy_total_veh",
    } & (scaled_metrics | {"freeway_total_veh"}):
        calibrated["total_model_vehicles"] = float(
            _as_float(calibrated.get("urban_total_veh"), 0.0)
            + _as_float(calibrated.get("freeway_total_veh"), 0.0)
            + _as_float(calibrated.get("off_ramp_storage_veh"), 0.0)
        )
        metadata["prediction_audit_total_model_vehicles_recomputed"] = 1.0

    metadata.update({
        "prediction_audit_calibration_applied": 1.0,
        "prediction_audit_freeway_total_scale": float(freeway_scale),
        "prediction_audit_urban_queue_plus_storage_scale": float(urban_mass_scale),
    })
    return calibrated, metadata


def _workspace_path(path_text: str, default: Path | None = None) -> Path:
    if not path_text:
        return default if default is not None else WORKSPACE_ROOT
    path = Path(path_text)
    if path.is_absolute():
        return path
    return WORKSPACE_ROOT / path


def install_adapter_calibration_fingerprints(cfg, tuning: Mapping[str, Any]) -> dict[str, float]:
    """Mark canary-protected components as calibrated for the current VISSIM geometry.

    The upstream controller stores component calibration fingerprints as module
    globals. In this workspace we cannot edit the external Numerical-Sim checkout,
    so VISSIM-specific tuning can explicitly declare that those components have
    been revalidated against the current 8-seg merge map.
    """
    settings = _mapping(_mapping(tuning.get("adapter")).get("calibration_fingerprints"))
    if str(settings.get("mode", "")).lower() != "current_vissim_geometry":
        return {}
    components = settings.get("components", ["leader_hinge", "np_deadband", "leader_mfd_far"])
    if not isinstance(components, list):
        components = ["leader_hinge", "np_deadband", "leader_mfd_far"]
    merge_map = {
        str(key): int(value)
        for key, value in dict(getattr(cfg.network, "ramp_merge_segment_index", {}) or {}).items()
    }
    if not merge_map:
        return {}
    try:
        from src.controllers import stackelberg_mpc as stackelberg_module

        for component in components:
            stackelberg_module.CALIBRATION_FINGERPRINTS[str(component)] = {
                "ramp_merge": dict(merge_map),
            }
        if hasattr(stackelberg_module, "_calib_fingerprint_warned"):
            stackelberg_module._calib_fingerprint_warned.clear()
    except Exception:
        return {"adapter_calibration_fingerprint_override_failed": 1.0}
    return {
        "adapter_calibration_fingerprint_override_active": 1.0,
        "adapter_calibration_fingerprint_component_count": float(len(components)),
        "adapter_calibration_fingerprint_merge_R_D_W": float(merge_map.get("R_D_W", -1)),
        "adapter_calibration_fingerprint_merge_R_F_W": float(merge_map.get("R_F_W", -1)),
        "adapter_calibration_fingerprint_merge_R_D_E": float(merge_map.get("R_D_E", -1)),
        "adapter_calibration_fingerprint_merge_R_F_E": float(merge_map.get("R_F_E", -1)),
    }


def _freeway_excess_vehicle_proxy(state, cfg) -> float:
    net = cfg.network
    state.ensure_freeway_lane_profile(net)
    excess = 0.0
    for link, densities in getattr(state, "freeway_density", {}).items():
        lanes = getattr(state, "freeway_effective_lanes", {}).get(link, [])
        for idx, rho in enumerate(densities):
            lane_count = float(lanes[idx]) if idx < len(lanes) else float(net.freeway_lanes)
            excess += (
                max(0.0, _as_float(rho) - float(net.rho_crit))
                * float(net.freeway_segment_length_km)
                * max(1.0e-9, lane_count)
            )
    return float(excess)


def vissim_terminal_feature_vector(state, cfg) -> dict[str, float]:
    """Map a model-predicted state to the aggregate fields used by VISSIM CSV fits."""
    net = cfg.network
    summary = summarize_model_state(state, cfg)
    freeway = max(0.0, _as_float(summary.get("freeway_segment_total_veh")))
    ramp = max(0.0, _as_float(summary.get("ramp_queue_total_veh"))) + max(
        0.0, _as_float(summary.get("off_ramp_storage_veh"))
    )
    boundary = max(0.0, _boundary_in_queue_veh(state, cfg))
    urban_total = max(0.0, _as_float(summary.get("urban_total_veh")))
    urban = max(0.0, urban_total - boundary)
    mainline_origin = max(0.0, _as_float(summary.get("mainline_origin_queue_total_veh")))
    total = freeway + urban + ramp + boundary + mainline_origin
    urban_queue = max(0.0, _as_float(summary.get("urban_movement_queue_total_veh")))
    stopped = min(
        total,
        ramp
        + boundary
        + 0.5 * max(0.0, urban_queue - boundary)
        + _freeway_excess_vehicle_proxy(state, cfg),
    )
    freeway_speed = max(0.0, _as_float(summary.get("freeway_mean_speed_kph"), float(net.v_free)))
    urban_speed = max(0.0, float(getattr(net, "urban_avg_speed_km_h", 50.0)))
    ramp_speed = 15.0
    boundary_speed = 5.0
    mean_speed = (
        freeway * freeway_speed
        + urban * urban_speed
        + ramp * ramp_speed
        + boundary * boundary_speed
    ) / max(total, 1.0e-9)
    return {
        "total_vehicles": float(total),
        "urban_vehicles": float(urban),
        "freeway_vehicles": float(freeway),
        "ramp_vehicles": float(ramp),
        "boundary_vehicles": float(boundary),
        "stopped_vehicles": float(stopped),
        "mean_speed_kph": float(mean_speed),
        "freeway_mean_speed_kph": float(freeway_speed),
    }


def vissim_terminal_feature_vector_from_summary(summary: Mapping[str, Any], cfg) -> dict[str, float]:
    """Best-effort terminal features from a serialized prediction summary."""
    net = cfg.network
    freeway = max(0.0, _as_float(summary.get("freeway_segment_total_veh")))
    ramp = max(0.0, _as_float(summary.get("ramp_queue_total_veh"))) + max(
        0.0, _as_float(summary.get("off_ramp_storage_veh"))
    )
    boundary = max(0.0, _as_float(summary.get("boundary_queue_total_veh")))
    urban_total = max(0.0, _as_float(summary.get("urban_total_veh")))
    urban = max(0.0, urban_total - boundary)
    mainline_origin = max(0.0, _as_float(summary.get("mainline_origin_queue_total_veh")))
    total = freeway + urban + ramp + boundary + mainline_origin
    urban_queue = max(0.0, _as_float(summary.get("urban_movement_queue_total_veh")))
    stopped = _as_float(summary.get("stopped_vehicles"), -1.0)
    if stopped < 0.0:
        stopped = min(total, ramp + boundary + 0.5 * max(0.0, urban_queue - boundary))
    else:
        stopped = max(0.0, stopped)
    freeway_speed = max(0.0, _as_float(summary.get("freeway_mean_speed_kph"), float(net.v_free)))
    urban_speed = max(0.0, float(getattr(net, "urban_avg_speed_km_h", 50.0)))
    ramp_speed = 15.0
    boundary_speed = 5.0
    mean_speed = (
        freeway * freeway_speed
        + urban * urban_speed
        + ramp * ramp_speed
        + boundary * boundary_speed
    ) / max(total, 1.0e-9)
    return {
        "total_vehicles": float(total),
        "urban_vehicles": float(urban),
        "freeway_vehicles": float(freeway),
        "ramp_vehicles": float(ramp),
        "boundary_vehicles": float(boundary),
        "stopped_vehicles": float(stopped),
        "mean_speed_kph": float(mean_speed),
        "freeway_mean_speed_kph": float(freeway_speed),
    }


def install_vissim_terminal_cost_objective(controller, cfg, tuning: Mapping[str, Any]) -> dict[str, float]:
    settings = _mapping(_mapping(tuning.get("adapter")).get("terminal_cost"))
    if not bool(settings.get("enabled", False)):
        return {}
    fit_path = _workspace_path(
        str(settings.get("fit_json", "evaluation/calibration/vissim_terminal_cost_fit_20260715.json"))
    )
    try:
        fit = json.loads(fit_path.read_text(encoding="utf-8"))
    except Exception:
        return {"adapter_vissim_terminal_cost_load_failed": 1.0}
    raw_coefficients = _mapping(fit.get("raw_coefficients"))
    features = settings.get("features", fit.get("features", []))
    if not isinstance(features, list):
        features = list(raw_coefficients)
    coefficient_mode = str(settings.get("coefficient_mode", "positive_only")).lower()
    include_intercept = bool(settings.get("include_intercept", False))
    clamp_nonnegative = bool(settings.get("clamp_nonnegative", True))
    weight = _as_float(settings.get("weight"), 1.0)
    intercept = _as_float(fit.get("raw_intercept"), 0.0) if include_intercept else 0.0
    used: dict[str, float] = {}
    for feature in features:
        name = str(feature)
        coef = _as_float(raw_coefficients.get(name), 0.0)
        if coefficient_mode == "positive_only" and coef <= 0.0:
            continue
        used[name] = float(coef)
    if not used and abs(intercept) <= 1.0e-12:
        return {"adapter_vissim_terminal_cost_empty": 1.0}

    original_objective_terms = controller.leader.objective_terms

    def objective_terms_with_vissim_terminal(
        predicted_states,
        action,
        previous,
        follower_objective,
        nash_converged,
        nash_residual_objective=0.0,
        nash_residual_control=0.0,
    ):
        states = list(predicted_states)
        terms = original_objective_terms(
            states,
            action,
            previous,
            follower_objective,
            nash_converged,
            nash_residual_objective,
            nash_residual_control,
        )
        if not states:
            return terms
        vector = vissim_terminal_feature_vector(states[-1], cfg)
        raw = float(intercept)
        for feature, coef in used.items():
            value = float(vector.get(feature, 0.0))
            raw += coef * value
            terms[f"leader_vissim_terminal_feature_{feature}"] = value
            terms[f"leader_vissim_terminal_coef_{feature}"] = float(coef)
        if clamp_nonnegative:
            raw = max(0.0, raw)
        penalty = weight * raw
        terms["leader_vissim_terminal_cost_active"] = 1.0
        terms["leader_vissim_terminal_cost_raw_veh_h"] = float(raw)
        terms["leader_vissim_terminal_cost_weight"] = float(weight)
        terms["leader_vissim_terminal_cost_penalty"] = float(penalty)
        terms["leader_vissim_terminal_cost_feature_count"] = float(len(used))
        terms["leader_total_objective"] = float(terms.get("leader_total_objective", 0.0)) + penalty
        return terms

    controller.leader.objective_terms = objective_terms_with_vissim_terminal
    return {
        "adapter_vissim_terminal_cost_active": 1.0,
        "adapter_vissim_terminal_cost_weight": float(weight),
        "adapter_vissim_terminal_cost_feature_count": float(len(used)),
        "adapter_vissim_terminal_cost_horizon_sec": _as_float(fit.get("horizon_sec"), 0.0),
        "adapter_vissim_terminal_cost_fit_r2": _as_float(_mapping(fit.get("metrics")).get("r2"), 0.0),
    }


def build_one_step_prediction(state, control, forecast, cfg, calibration: Mapping[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        from src.simulation.coupling import run_coupled_interval

        demand = list(forecast)[0]
        predicted = state.copy()
        run_coupled_interval(predicted, control, demand, cfg)
        predicted.time_sec = float(getattr(state, "time_sec", 0.0)) + float(cfg.simulation.control_interval)
        state_summary = summarize_model_state(predicted, cfg)
        try:
            terminal_features = vissim_terminal_feature_vector(predicted, cfg)
        except Exception:
            terminal_features = vissim_terminal_feature_vector_from_summary(state_summary, cfg)
        calibrated_summary, audit_metadata = apply_prediction_audit_calibration(state_summary, calibration)
        payload = {
            "schema_version": 1,
            "status": "ok",
            "mode": "coupled_interval_one_step",
            "from_sim_sec": float(getattr(state, "time_sec", 0.0)),
            "target_sim_sec": float(predicted.time_sec),
            "control_interval_sec": float(cfg.simulation.control_interval),
            "wall_sec": round(time.perf_counter() - started, 6),
            "state_summary": state_summary,
            "terminal_features": terminal_features,
        }
        if calibrated_summary:
            payload["calibrated_state_summary"] = calibrated_summary
            payload["audit_calibration"] = audit_metadata
        return payload
    except Exception as exc:
        return {
            "schema_version": 1,
            "status": "error",
            "mode": "coupled_interval_one_step",
            "from_sim_sec": float(getattr(state, "time_sec", 0.0)),
            "control_interval_sec": float(cfg.simulation.control_interval),
            "wall_sec": round(time.perf_counter() - started, 6),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def prediction_error_from_previous(previous_path: Path, observed_summary: Mapping[str, Any]) -> dict[str, Any]:
    if not previous_path.exists():
        return {}
    try:
        raw = json.loads(previous_path.read_text(encoding="utf-8"))
        prediction = raw.get("prediction", {})
        if not isinstance(prediction, Mapping) or prediction.get("status") != "ok":
            return {}
        predicted_summary = prediction.get("calibrated_state_summary", prediction.get("state_summary", {}))
        if not isinstance(predicted_summary, Mapping):
            return {}
        prediction_summary_kind = (
            "calibrated_state_summary"
            if isinstance(prediction.get("calibrated_state_summary"), Mapping)
            else "state_summary"
        )
        scalar_errors: dict[str, dict[str, float]] = {}
        abs_sum = 0.0
        count = 0
        for key in PREDICTION_AUDIT_SCALARS:
            if key not in predicted_summary or key not in observed_summary:
                continue
            predicted = float(predicted_summary.get(key, 0.0))
            observed = float(observed_summary.get(key, 0.0))
            error = observed - predicted
            scalar_errors[key] = {
                "predicted": predicted,
                "observed": observed,
                "error": error,
                "abs_error": abs(error),
                "relative_error": error / max(1.0, abs(predicted)),
            }
            abs_sum += abs(error)
            count += 1
        return {
            "schema_version": 1,
            "status": "ok",
            "source_action_json": str(previous_path),
            "predicted_from_sim_sec": float(prediction.get("from_sim_sec", 0.0)),
            "predicted_for_sim_sec": float(prediction.get("target_sim_sec", 0.0)),
            "observed_sim_sec": float(observed_summary.get("time_sec", 0.0)),
            "target_lag_sec": float(observed_summary.get("time_sec", 0.0)) - float(prediction.get("target_sim_sec", 0.0)),
            "prediction_summary_kind": prediction_summary_kind,
            "mean_abs_scalar_error": float(abs_sum / count) if count else 0.0,
            "scalar_errors": scalar_errors,
        }
    except Exception as exc:
        return {
            "schema_version": 1,
            "status": "error",
            "source_action_json": str(previous_path),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def green_from_release_map(rate_vph: float, curve: Mapping[str, Any], default_green: float = 10.0) -> float:
    points: list[tuple[float, float]] = []
    for green, release in curve.items():
        try:
            points.append((float(green), float(release)))
        except (TypeError, ValueError):
            continue
    if not points:
        return float(default_green)
    points = sorted(points, key=lambda item: item[0])
    monotone: list[tuple[float, float]] = []
    best_release = -1.0
    for green, release in points:
        best_release = max(best_release, release)
        monotone.append((green, best_release))
    rate = max(0.0, float(rate_vph))
    if rate <= monotone[0][1]:
        return monotone[0][0]
    for (g0, r0), (g1, r1) in zip(monotone, monotone[1:]):
        if rate <= r1:
            if r1 <= r0:
                return g1
            frac = (rate - r0) / (r1 - r0)
            return g0 + frac * (g1 - g0)
    return monotone[-1][0]


def physical_ramp_actions(control, cfg, actuation: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    cap = cfg.network.ramp_capacity_veh_h
    d_rate = (
        float(control.ramp_metering.get("R_D_W", cap.get("R_D_W", 1500.0)))
        + float(control.ramp_metering.get("R_D_E", cap.get("R_D_E", 1500.0)))
    ) / 2.0
    f_rate = (
        float(control.ramp_metering.get("R_F_W", cap.get("R_F_W", 1500.0)))
        + float(control.ramp_metering.get("R_F_E", cap.get("R_F_E", 1500.0)))
    ) / 2.0
    out = {}
    d_curve = actuation.get("D_green_to_release_vph", {})
    f_curve = actuation.get("F_green_to_release_vph", {})
    f_mode = str(actuation.get("F_ramp_mode", "always_green")).lower()
    d_rate = clamp(d_rate, 0.0, max((float(v) for v in d_curve.values()), default=1500.0) if isinstance(d_curve, Mapping) else 1500.0)
    d_green = green_from_release_map(d_rate, d_curve if isinstance(d_curve, Mapping) else {}, default_green=10.0)
    out["D"] = {"rate_vph": float(d_rate), "green_sec": float(clamp(round(d_green), 0.0, 10.0))}
    f_rate = clamp(f_rate, 0.0, max((float(v) for v in f_curve.values()), default=1500.0) if isinstance(f_curve, Mapping) else 1500.0)
    if f_mode in ("always_green", "monitor_only", "disabled"):
        f_green = 10.0
    else:
        f_green = green_from_release_map(f_rate, f_curve if isinstance(f_curve, Mapping) else {}, default_green=10.0)
    out["F"] = {"rate_vph": float(f_rate), "green_sec": float(clamp(round(f_green), 0.0, 10.0))}
    return out


def real_world_ramp_meter_actions(
    control,
    cfg,
    actuation: Mapping[str, Any],
    mapping: Mapping[str, Any],
) -> dict[str, dict[str, float | str]]:
    """Map model ramp releases to physical real-world ramp-meter controllers."""
    meters = mapping.get("ramp_meters", [])
    if not isinstance(meters, list) or not meters:
        return {}

    settings = _mapping(actuation.get("real_world_ramp_metering"))
    cycle = max(1.0e-6, _as_float(settings.get("cycle_sec"), 10.0))
    min_green = clamp(_as_float(settings.get("min_green_sec"), 0.0), 0.0, cycle)
    max_green = clamp(_as_float(settings.get("max_green_sec"), cycle), min_green, cycle)
    default_per_meter_capacity = max(1.0e-6, _as_float(settings.get("per_meter_capacity_vph"), 900.0))
    distribute = bool(settings.get("distribute_model_rate_across_meters", True))

    group_counts: dict[str, int] = {}
    for meter in meters:
        if not isinstance(meter, Mapping):
            continue
        key = str(meter.get("model_ramp_key", ""))
        if key:
            group_counts[key] = group_counts.get(key, 0) + 1

    capacities = getattr(cfg.network, "ramp_capacity_veh_h", {}) or {}
    out: dict[str, dict[str, float | str]] = {}
    for meter in meters:
        if not isinstance(meter, Mapping):
            continue
        meter_id = str(meter.get("id", meter.get("control_id", "")))
        if not meter_id:
            continue
        key = str(meter.get("model_ramp_key", ""))
        group_count = max(1, int(group_counts.get(key, 1)))
        per_meter_capacity = max(
            1.0e-6,
            _as_float(meter.get("capacity_vph"), default_per_meter_capacity),
        )
        default_group_capacity = per_meter_capacity * group_count
        group_capacity = max(
            1.0e-6,
            _as_float(capacities.get(key, default_group_capacity), default_group_capacity),
        )
        group_rate = clamp(
            _as_float(control.ramp_metering.get(key, group_capacity), group_capacity),
            0.0,
            group_capacity,
        )
        per_meter_rate = group_rate / float(group_count) if distribute else group_rate
        green = cycle * per_meter_rate / per_meter_capacity
        green = clamp(round(green), min_green, max_green)
        out[meter_id] = {
            "sc_no": float(_as_float(meter.get("sc_no"), 0.0)),
            "sg_no": float(_as_float(meter.get("sg_no"), 1.0)),
            "rate_vph": float(per_meter_rate),
            "group_rate_vph": float(group_rate),
            "green_sec": float(green),
            "model_ramp_key": key,
        }
    return out


def _segment_model_coordinates(segment_id: str, segment: Mapping[str, Any]) -> tuple[str, int]:
    model_link = segment.get("model_link")
    model_idx = segment.get("model_segment_index")
    if model_link is not None and model_idx is not None:
        return str(model_link), int(_as_float(model_idx))
    return SEGMENT_TO_MODEL[segment_id]


def _segment_dsd_controls(segment: Mapping[str, Any]) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    by_lane = segment.get("dsd_by_lane", {})
    if isinstance(by_lane, Mapping):
        for lane_key, value in by_lane.items():
            if not isinstance(value, Mapping):
                continue
            row = dict(value)
            row.setdefault("lane", lane_key)
            controls.append(row)
    extras = segment.get("extra_dsd_controls", [])
    if isinstance(extras, list):
        for value in extras:
            if isinstance(value, Mapping):
                controls.append(dict(value))

    def sort_key(item: Mapping[str, Any]) -> tuple[int, int]:
        lane = int(_as_float(item.get("lane"), 9999.0))
        dsd_no = int(_as_float(item.get("dsd_no"), 0.0))
        return lane, dsd_no

    return sorted(controls, key=sort_key)


def _signal_rows_for_mapping(mapping: Mapping[str, Any]) -> list[dict[str, Any]]:
    if "signals" not in mapping:
        return [{"id": signal, "sc_no": sc_no} for signal, sc_no in {"A": 1, "B": 2, "C": 3, "D": 4, "F": 5}.items()]
    raw = mapping.get("signals", [])
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, Mapping):
            rows.append({"id": str(item.get("id", "")), "sc_no": int(_as_float(item.get("sc_no"), 0.0))})
    return [row for row in rows if row["id"] and row["sc_no"] > 0]


def _release_at_largest_green(curve: Any, fallback: float) -> float:
    if not isinstance(curve, Mapping) or not curve:
        return float(fallback)
    points: list[tuple[float, float]] = []
    for green, release in curve.items():
        try:
            points.append((float(green), float(release)))
        except (TypeError, ValueError):
            continue
    if not points:
        return float(fallback)
    green, release = max(points, key=lambda item: item[0])
    return max(0.0, float(release))


def apply_actuation_guards_to_control(control, cfg, actuation: Mapping[str, Any]) -> dict[str, float]:
    """Force action JSON/prediction to respect calibration-level actuator guards."""
    metadata: dict[str, float] = {}
    active_mask = _mapping(actuation.get("active_lever_mask"))
    active_mask_enabled = bool(active_mask.get("enabled", False))
    vsl_segment_override_policy = str(actuation.get("vsl_segment_override_policy", "")).strip().lower()
    if vsl_segment_override_policy in {"clear_all", "clear_when_mask_disabled"}:
        if vsl_segment_override_policy == "clear_all" or not active_mask_enabled:
            stale_vsl_segments = [key for key in list(getattr(control, "vsl", {}).keys()) if "__seg" in str(key)]
            for key in stale_vsl_segments:
                control.vsl.pop(key, None)
            if stale_vsl_segments:
                control.diagnostics["vsl_segment_overrides_cleared"] = float(len(stale_vsl_segments))
                metadata["vsl_segment_overrides_cleared"] = float(len(stale_vsl_segments))
    if active_mask_enabled:
        allowed_vsl_links = {str(value) for value in active_mask.get("allowed_vsl_links", []) or []}
        allowed_vsl_segments = {str(value) for value in active_mask.get("allowed_vsl_segments", []) or []}
        max_vsl = max(float(value) for value in cfg.freeway_follower.vsl_set)
        disabled_vsl_segments = 0
        for link in cfg.network.freeway_links:
            link_key = str(link)
            for idx in range(int(cfg.network.freeway_segments_per_link)):
                segment_key = f"{link_key}__seg{idx}"
                readable_key = f"RW_{link_key}_S{idx}"
                if link_key in allowed_vsl_links or segment_key in allowed_vsl_segments or readable_key in allowed_vsl_segments:
                    continue
                control.vsl[segment_key] = float(max_vsl)
                disabled_vsl_segments += 1
        allowed_ramps = {str(value) for value in active_mask.get("allowed_ramps", []) or []}
        if "allowed_ramps" in active_mask:
            for ramp, capacity in _ramp_capacities(cfg).items():
                if ramp not in allowed_ramps:
                    control.ramp_metering[ramp] = float(capacity)
        control.diagnostics["active_lever_mask_enabled"] = 1.0
        control.diagnostics["active_lever_mask_disabled_vsl_segments"] = float(disabled_vsl_segments)
        control.diagnostics["active_lever_mask_allowed_ramp_count"] = float(len(allowed_ramps))
        metadata.update({
            "active_lever_mask_enabled": 1.0,
            "active_lever_mask_disabled_vsl_segments": float(disabled_vsl_segments),
            "active_lever_mask_allowed_ramp_count": float(len(allowed_ramps)),
        })
    signal_freeze = _mapping(actuation.get("signal_green_freeze"))
    if bool(signal_freeze.get("enabled", False)):
        green = _as_float(signal_freeze.get("green_sec"), 57.0)
        major = _as_float(signal_freeze.get("major_green_sec"), green)
        minor = _as_float(signal_freeze.get("minor_green_sec"), green)
        offset = _as_float(signal_freeze.get("offset_sec"), 0.0)
        signals = signal_freeze.get("signals")
        if not isinstance(signals, list) or not signals:
            signals = _controlled_signal_names(cfg)
        for signal in signals:
            name = str(signal)
            control.green_times[f"{name}_p1"] = float(minor)
            control.green_times[f"{name}_p2"] = float(major)
            control.offsets[name] = float(offset)
        control.diagnostics["signal_green_freeze_active"] = 1.0
        control.diagnostics["signal_green_freeze_major_sec"] = float(major)
        control.diagnostics["signal_green_freeze_minor_sec"] = float(minor)
        control.diagnostics["signal_green_freeze_offset_sec"] = float(offset)
        metadata.update({
            "signal_green_freeze_active": 1.0,
            "signal_green_freeze_major_sec": float(major),
            "signal_green_freeze_minor_sec": float(minor),
            "signal_green_freeze_offset_sec": float(offset),
        })
    if bool(actuation.get("F_ramp_invalid_guard_active", False)):
        cap = cfg.network.ramp_capacity_veh_h
        fallback = (
            float(cap.get("R_F_W", 0.0))
            + float(cap.get("R_F_E", 0.0))
        ) / 2.0
        release = _release_at_largest_green(actuation.get("F_green_to_release_vph", {}), fallback)
        for ramp in ("R_F_W", "R_F_E"):
            control.ramp_metering[ramp] = float(release)
        control.diagnostics["F_ramp_invalid_guard_active"] = 1.0
        control.diagnostics["F_ramp_guard_release_vph"] = float(release)
        metadata.update({
            "F_ramp_invalid_guard_active": 1.0,
            "F_ramp_guard_release_vph": float(release),
        })
    return metadata


def _total_ramp_queue_veh(state) -> float:
    ramp_queue = getattr(state, "ramp_queue", {})
    if not isinstance(ramp_queue, Mapping):
        return 0.0
    return float(sum(max(0.0, _as_float(value)) for value in ramp_queue.values()))


def _boundary_in_queue_veh(state, cfg) -> float:
    try:
        return float(state.boundary_in_queue_vehicles(cfg.network))
    except Exception:
        return 0.0


def _max_freeway_density_ratio(state, cfg) -> float:
    rho_crit = max(1.0e-9, float(getattr(cfg.network, "rho_crit", 1.0)))
    values: list[float] = []
    freeway_density = getattr(state, "freeway_density", {})
    if isinstance(freeway_density, Mapping):
        for densities in freeway_density.values():
            if isinstance(densities, list):
                values.extend(max(0.0, _as_float(value)) / rho_crit for value in densities)
    return float(max(values)) if values else 0.0


def _ramp_capacities(cfg) -> dict[str, float]:
    raw = getattr(cfg.network, "ramp_capacity_veh_h", {})
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): max(0.0, _as_float(value)) for key, value in raw.items()}


def _release_sum(control, capacities: Mapping[str, float]) -> float:
    return float(sum(
        max(0.0, _as_float(control.ramp_metering.get(ramp, capacities.get(ramp, 0.0))))
        for ramp in capacities
    ))


def _release_floor_ratio(
    guard: Mapping[str, Any],
    ramp_queue_veh: float,
    boundary_queue_veh: float,
    stopped_veh: float,
) -> float:
    ratio = clamp(_as_float(guard.get("min_release_ratio_of_capacity"), 0.0), 0.0, 1.0)
    high_ratio = clamp(
        _as_float(guard.get("queue_high_release_ratio_of_capacity"), ratio),
        0.0,
        1.0,
    )
    if ramp_queue_veh >= _as_float(guard.get("ramp_queue_threshold_veh"), float("inf")):
        ratio = max(ratio, high_ratio)
    if boundary_queue_veh >= _as_float(guard.get("boundary_queue_threshold_veh"), float("inf")):
        ratio = max(ratio, high_ratio)
    if stopped_veh >= _as_float(guard.get("stopped_threshold_veh"), float("inf")):
        ratio = max(ratio, high_ratio)
    return float(ratio)


def _make_no_control(ControlAction, cfg):
    if hasattr(ControlAction, "uncontrolled"):
        return ControlAction.uncontrolled(cfg)
    return ControlAction.fixed(cfg)


def apply_vissim_policy_guards(
    control,
    cfg,
    state,
    state_json: Mapping[str, Any],
    actuation: Mapping[str, Any],
    ControlAction,
) -> tuple[Any, dict[str, float]]:
    """Plant-aware action guards applied before bridge-level actuator guards.

    These guards are intentionally conservative. They do not try to improve the
    Stackelberg objective; they prevent Vissim-facing ramp actions from hiding
    too much queue in ramp/boundary storage when the predicted benefit is small.
    """
    if bool(_mapping(getattr(control, "diagnostics", {})).get("diagnostic_bypass_policy_guards", False)):
        return control, {"ramp_release_guard_bypassed_for_diagnostic": 1.0}

    guard = _mapping(actuation.get("ramp_release_guard"))
    if not bool(guard.get("enabled", False)):
        return control, {}

    capacities = _ramp_capacities(cfg)
    if not capacities:
        return control, {}

    ramp_queue_veh = _total_ramp_queue_veh(state)
    boundary_queue_veh = _boundary_in_queue_veh(state, cfg)
    stopped_veh = max(0.0, _as_float(state_json.get("stopped_vehicles")))
    density_ratio = _max_freeway_density_ratio(state, cfg)
    floor_ratio = _release_floor_ratio(guard, ramp_queue_veh, boundary_queue_veh, stopped_veh)
    before_sum = _release_sum(control, capacities)
    cap_sum = float(sum(capacities.values()))
    no_control_sum = cap_sum
    mean_ratio_before = before_sum / max(no_control_sum, 1.0e-9)

    fallback = _mapping(guard.get("no_control_fallback"))
    fallback_enabled = bool(fallback.get("enabled", False))
    fallback_release_ratio = clamp(
        _as_float(
            fallback.get("min_release_ratio_of_uncontrolled"),
            guard.get("fallback_min_release_ratio_of_uncontrolled", 0.0),
        ),
        0.0,
        1.0,
    )
    density_limit = _as_float(
        fallback.get("max_density_ratio_for_fallback"),
        guard.get("max_density_ratio_for_fallback", float("inf")),
    )
    queue_required = bool(fallback.get("require_queue_or_stopped", False))
    has_queue_risk = (
        ramp_queue_veh >= _as_float(guard.get("ramp_queue_threshold_veh"), float("inf"))
        or boundary_queue_veh >= _as_float(guard.get("boundary_queue_threshold_veh"), float("inf"))
        or stopped_veh >= _as_float(guard.get("stopped_threshold_veh"), float("inf"))
    )
    should_fallback = (
        fallback_enabled
        and mean_ratio_before < fallback_release_ratio
        and density_ratio <= density_limit
        and (has_queue_risk or not queue_required)
    )

    metadata: dict[str, float] = {
        "ramp_release_guard_active": 1.0,
        "ramp_release_guard_floor_ratio": float(floor_ratio),
        "ramp_release_guard_before_sum_vph": float(before_sum),
        "ramp_release_guard_before_ratio": float(mean_ratio_before),
        "ramp_release_guard_ramp_queue_veh": float(ramp_queue_veh),
        "ramp_release_guard_boundary_queue_veh": float(boundary_queue_veh),
        "ramp_release_guard_stopped_veh": float(stopped_veh),
        "ramp_release_guard_density_ratio_max": float(density_ratio),
        "ramp_release_guard_no_control_fallback": float(should_fallback),
    }

    if should_fallback:
        control = _make_no_control(ControlAction, cfg)
        control.diagnostics["ramp_release_guard_no_control_fallback"] = 1.0
        control.diagnostics["ramp_release_guard_before_ratio"] = float(mean_ratio_before)
    else:
        adjusted = 0
        ramp_overrides = _mapping(guard.get("per_ramp_min_release_ratio_of_capacity"))
        for ramp, capacity in capacities.items():
            ratio = clamp(_as_float(ramp_overrides.get(ramp), floor_ratio), 0.0, 1.0)
            floor = float(capacity) * ratio
            current = max(0.0, _as_float(control.ramp_metering.get(ramp), capacity))
            if current < floor:
                control.ramp_metering[ramp] = float(floor)
                adjusted += 1
        control.diagnostics["ramp_release_guard_adjusted_count"] = float(adjusted)
        control.diagnostics["ramp_release_guard_floor_ratio"] = float(floor_ratio)
        metadata["ramp_release_guard_adjusted_count"] = float(adjusted)

    after_sum = _release_sum(control, capacities)
    control.N_UF_star = float(after_sum)
    control.diagnostics["ramp_release_guard_after_sum_vph"] = float(after_sum)
    control.diagnostics["ramp_release_guard_N_UF_resynced"] = 1.0
    metadata.update({
        "ramp_release_guard_after_sum_vph": float(after_sum),
        "ramp_release_guard_after_ratio": float(after_sum / max(no_control_sum, 1.0e-9)),
        "ramp_release_guard_N_UF_resynced": 1.0,
    })
    return control, metadata


def _post_guard_safety_settings(tuning: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(_mapping(tuning.get("adapter")).get("post_guard_safety"))


def _post_guard_terminal_score_settings(
    tuning: Mapping[str, Any],
    safety: Mapping[str, Any],
) -> Mapping[str, Any]:
    base = dict(_mapping(_mapping(tuning.get("adapter")).get("terminal_cost")))
    score = _mapping(safety.get("score"))
    if not score:
        score = _mapping(safety.get("terminal_cost"))
    if score:
        base = deep_update(base, score)
    if "fit_json" not in base:
        base["fit_json"] = "evaluation/calibration/vissim_terminal_cost_fit_20260715.json"
    return base


def _load_terminal_score_spec(settings: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    fit_path = _workspace_path(
        str(settings.get("fit_json", "evaluation/calibration/vissim_terminal_cost_fit_20260715.json"))
    )
    try:
        fit = json.loads(fit_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, {
            "post_guard_safety_status": "terminal_fit_load_failed",
            "post_guard_safety_error_type": type(exc).__name__,
        }

    raw_coefficients = _mapping(fit.get("raw_coefficients"))
    features = settings.get("features", fit.get("features", []))
    if not isinstance(features, list):
        features = list(raw_coefficients)
    coefficient_mode = str(settings.get("coefficient_mode", "positive_only")).lower()
    include_intercept = bool(settings.get("include_intercept", False))
    intercept = _as_float(fit.get("raw_intercept"), 0.0) if include_intercept else 0.0
    used: dict[str, float] = {}
    for feature in features:
        name = str(feature)
        coef = _as_float(raw_coefficients.get(name), 0.0)
        if coefficient_mode == "positive_only" and coef <= 0.0:
            continue
        used[name] = float(coef)
    if not used and abs(intercept) <= 1.0e-12:
        return None, {"post_guard_safety_status": "terminal_fit_empty"}

    return {
        "coefficients": used,
        "intercept": float(intercept),
        "weight": _as_float(settings.get("weight"), 1.0),
        "clamp_nonnegative": bool(settings.get("clamp_nonnegative", True)),
        "use_calibrated_prediction": bool(settings.get("use_calibrated_prediction", True)),
        "component_penalty": _mapping(settings.get("component_penalty")),
        "fit_path": str(fit_path),
        "fit_r2": _as_float(_mapping(fit.get("metrics")).get("r2"), 0.0),
    }, {
        "post_guard_terminal_score_feature_count": float(len(used)),
        "post_guard_terminal_score_fit_r2": _as_float(_mapping(fit.get("metrics")).get("r2"), 0.0),
        "post_guard_terminal_score_weight": _as_float(settings.get("weight"), 1.0),
    }


def _prediction_terminal_features(
    prediction: Mapping[str, Any],
    cfg,
    spec: Mapping[str, Any],
) -> tuple[dict[str, float], str]:
    if bool(spec.get("use_calibrated_prediction", True)):
        calibrated = _mapping(prediction.get("calibrated_state_summary"))
        if calibrated:
            return vissim_terminal_feature_vector_from_summary(calibrated, cfg), "calibrated_state_summary"
    terminal_features = _mapping(prediction.get("terminal_features"))
    if terminal_features:
        return {str(k): _as_float(v) for k, v in terminal_features.items()}, "terminal_features"
    summary = _mapping(prediction.get("state_summary"))
    return vissim_terminal_feature_vector_from_summary(summary, cfg), "state_summary"


def _prediction_component_summary(
    prediction: Mapping[str, Any],
    settings: Mapping[str, Any],
) -> tuple[Mapping[str, Any], str]:
    if bool(settings.get("use_calibrated_prediction", True)):
        calibrated = _mapping(prediction.get("calibrated_state_summary"))
        if calibrated:
            return calibrated, "calibrated_state_summary"
    summary = _mapping(prediction.get("state_summary"))
    return summary, "state_summary"


def _component_penalty_score(
    prediction: Mapping[str, Any],
    settings: Mapping[str, Any],
) -> tuple[float, str, int]:
    component = _mapping(settings.get("component_penalty"))
    if not bool(component.get("enabled", False)):
        return 0.0, "disabled", 0
    terms = component.get("terms", [])
    if not isinstance(terms, list):
        return 0.0, "empty", 0
    summary, summary_kind = _prediction_component_summary(prediction, component)
    total = 0.0
    used = 0
    for raw_term in terms:
        term = _mapping(raw_term)
        metric = str(term.get("metric", ""))
        if not metric:
            continue
        value = _as_float(summary.get(metric), 0.0)
        target = _as_float(term.get("target", term.get("threshold", 0.0)), 0.0)
        mode = str(term.get("mode", "above")).lower()
        if mode in ("above", "excess", "over"):
            amount = max(0.0, value - target)
        elif mode in ("below", "deficit", "under"):
            amount = max(0.0, target - value)
        elif mode in ("absolute", "abs"):
            amount = abs(value - target)
        elif mode in ("value", "raw"):
            amount = max(0.0, value)
        else:
            amount = 0.0
        weight = _as_float(term.get("weight"), 0.0)
        total += weight * amount
        used += 1
    return float(total), summary_kind, used


def _score_prediction_with_terminal_fit(
    prediction: Mapping[str, Any],
    cfg,
    spec: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    if str(prediction.get("status", "")) != "ok":
        return None, "prediction_unavailable"
    features, summary_kind = _prediction_terminal_features(prediction, cfg, spec)
    raw = _as_float(spec.get("intercept"), 0.0)
    for feature, coef in _mapping(spec.get("coefficients")).items():
        raw += float(coef) * float(features.get(str(feature), 0.0))
    if bool(spec.get("clamp_nonnegative", True)):
        raw = max(0.0, raw)
    component_penalty, component_summary_kind, component_term_count = _component_penalty_score(prediction, spec)
    weight = _as_float(spec.get("weight"), 1.0)
    return {
        "score": float(weight * raw + component_penalty),
        "raw_veh_h": float(raw),
        "summary_kind": summary_kind,
        "component_penalty": float(component_penalty),
        "component_summary_kind": component_summary_kind,
        "component_term_count": float(component_term_count),
    }, "ok"


def _add_score_metadata(
    metadata: dict[str, Any],
    prefix: str,
    score: Mapping[str, Any] | None,
    status: str,
) -> None:
    metadata[f"{prefix}_score_status"] = status
    if score is None:
        return
    metadata[f"{prefix}_terminal_score"] = float(score.get("score", 0.0))
    metadata[f"{prefix}_terminal_score_raw_veh_h"] = float(score.get("raw_veh_h", 0.0))
    metadata[f"{prefix}_score_summary_kind"] = str(score.get("summary_kind", ""))
    metadata[f"{prefix}_component_penalty"] = float(score.get("component_penalty", 0.0))
    metadata[f"{prefix}_component_penalty_term_count"] = float(score.get("component_term_count", 0.0))
    metadata[f"{prefix}_component_penalty_summary_kind"] = str(score.get("component_summary_kind", ""))


def _physical_action_metadata(prefix: str, control, cfg, actuation: Mapping[str, Any]) -> dict[str, float]:
    metadata: dict[str, float] = {}
    try:
        actions = physical_ramp_actions(control, cfg, actuation)
    except Exception:
        return metadata
    for ramp, spec in actions.items():
        metadata[f"{prefix}_physical_ramp_{ramp}_rate_vph"] = _as_float(spec.get("rate_vph"))
        metadata[f"{prefix}_physical_ramp_{ramp}_green_sec"] = _as_float(spec.get("green_sec"))
    return metadata


def _guarded_no_control_baseline(ControlAction, cfg, state, state_json, actuation: Mapping[str, Any]):
    control = _make_no_control(ControlAction, cfg)
    control.diagnostics["post_guard_no_control_baseline"] = 1.0
    control, _ = apply_vissim_policy_guards(control, cfg, state, state_json, actuation, ControlAction)
    apply_actuation_guards_to_control(control, cfg, actuation)
    return control


def _guarded_pfo_baseline(cfg, state, forecast, previous, state_json, actuation: Mapping[str, Any], ControlAction):
    started = time.perf_counter()
    metadata: dict[str, Any] = {}
    controller = None
    try:
        from src.controllers.distributed_coordinator import DistributedCoordinator

        controller = DistributedCoordinator(cfg)
        result = controller.solve(state.copy(), None, forecast, previous)
        control = result.control
        control.diagnostics["post_guard_pfo_baseline"] = 1.0
        metadata.update({
            "post_guard_pfo_iterations": float(getattr(result, "iterations", 0)),
            "post_guard_pfo_converged": float(bool(getattr(result, "converged", False))),
            "post_guard_pfo_objective": float(getattr(result, "objective_value", 0.0)),
        })
        control, _ = apply_vissim_policy_guards(control, cfg, state, state_json, actuation, ControlAction)
        apply_actuation_guards_to_control(control, cfg, actuation)
        metadata["post_guard_pfo_baseline_status"] = "ok"
        metadata["post_guard_pfo_wall_sec"] = round(time.perf_counter() - started, 6)
        return control, metadata
    except Exception as exc:
        metadata.update({
            "post_guard_pfo_baseline_status": "error",
            "post_guard_pfo_error_type": type(exc).__name__,
            "post_guard_pfo_wall_sec": round(time.perf_counter() - started, 6),
        })
        return None, metadata
    finally:
        if controller is not None and hasattr(controller, "close"):
            try:
                controller.close()
            except Exception:
                pass


def apply_post_guard_safety_evaluation(
    control,
    cfg,
    state,
    state_json: Mapping[str, Any],
    forecast,
    previous,
    calibration: Mapping[str, Any],
    tuning: Mapping[str, Any],
    actuation: Mapping[str, Any],
    ControlAction,
    prediction: Mapping[str, Any],
) -> tuple[Any, dict[str, Any], Mapping[str, Any]]:
    """Evaluate guarded plant-facing action against explicit safety baselines."""
    if bool(_mapping(getattr(control, "diagnostics", {})).get("diagnostic_bypass_policy_guards", False)):
        return control, {"post_guard_safety_bypassed_for_diagnostic": 1.0}, prediction

    safety = _post_guard_safety_settings(tuning)
    if not bool(safety.get("enabled", False)):
        return control, {}, prediction

    metadata: dict[str, Any] = {
        "post_guard_safety_enabled": 1.0,
        "post_guard_safety_status": "ok",
        "post_guard_safety_fallback_occurred": 0.0,
        "post_guard_no_control_fallback": 0.0,
    }
    metadata.update(_physical_action_metadata("post_guard", control, cfg, actuation))

    spec, spec_metadata = _load_terminal_score_spec(_post_guard_terminal_score_settings(tuning, safety))
    metadata.update(spec_metadata)
    if spec is None:
        return control, metadata, prediction

    post_score, post_status = _score_prediction_with_terminal_fit(prediction, cfg, spec)
    _add_score_metadata(metadata, "post_guard", post_score, post_status)
    if post_score is None:
        metadata["post_guard_safety_status"] = post_status
        return control, metadata, prediction

    no_control_settings = _mapping(safety.get("no_control_baseline"))
    if not no_control_settings:
        no_control_settings = _mapping(safety.get("no_control"))
    no_control_enabled = bool(no_control_settings.get("enabled", True))
    metadata["post_guard_no_control_baseline_enabled"] = float(no_control_enabled)
    no_control_prediction: Mapping[str, Any] | None = None
    no_control_control = None
    if no_control_enabled:
        no_control_control = _guarded_no_control_baseline(ControlAction, cfg, state, state_json, actuation)
        metadata.update(_physical_action_metadata("post_guard_no_control", no_control_control, cfg, actuation))
        no_control_prediction = build_one_step_prediction(state, no_control_control, forecast, cfg, calibration)
        no_score, no_status = _score_prediction_with_terminal_fit(no_control_prediction, cfg, spec)
        _add_score_metadata(metadata, "post_guard_no_control", no_score, no_status)
        if no_score is not None:
            gap = float(post_score["score"] - no_score["score"])
            metadata["post_guard_no_control_score_gap"] = gap
            metadata["post_guard_vs_no_control_score_gap"] = gap
            margin = max(
                0.0,
                _as_float(
                    no_control_settings.get(
                        "fallback_margin_score",
                        safety.get("no_control_fallback_margin_score", 0.0),
                    ),
                ),
            )
            metadata["post_guard_no_control_fallback_margin_score"] = float(margin)
            fallback_enabled = bool(
                no_control_settings.get(
                    "fallback_enabled",
                    safety.get("fallback_to_no_control", False),
                )
            )
            prefer_less_restrictive = bool(
                no_control_settings.get(
                    "prefer_less_restrictive_on_tie",
                    no_control_settings.get("prefer_no_control_on_tie", False),
                )
            )
            tie_margin = max(
                0.0,
                _as_float(
                    no_control_settings.get(
                        "tie_margin_score",
                        no_control_settings.get("prefer_no_control_tie_margin_score", 0.0),
                    ),
                ),
            )
            min_release_gap = max(
                0.0,
                _as_float(
                    no_control_settings.get(
                        "min_release_gap_vph",
                        no_control_settings.get("prefer_no_control_min_release_gap_vph", 0.0),
                    ),
                ),
            )
            post_physical = physical_ramp_actions(control, cfg, actuation)
            no_physical = physical_ramp_actions(no_control_control, cfg, actuation)
            release_gap = 0.0
            for ramp in sorted(set(post_physical) | set(no_physical)):
                release_gap += max(
                    0.0,
                    _as_float(_mapping(no_physical.get(ramp)).get("rate_vph"))
                    - _as_float(_mapping(post_physical.get(ramp)).get("rate_vph")),
                )
            tie_fallback = (
                prefer_less_restrictive
                and gap >= -tie_margin
                and release_gap >= min_release_gap
            )
            metadata["post_guard_no_control_prefer_less_restrictive_on_tie"] = float(prefer_less_restrictive)
            metadata["post_guard_no_control_tie_margin_score"] = float(tie_margin)
            metadata["post_guard_no_control_release_gap_vph"] = float(release_gap)
            metadata["post_guard_no_control_tie_fallback"] = float(tie_fallback)
            should_fallback = fallback_enabled and (gap > margin or tie_fallback)
            metadata["post_guard_no_control_fallback"] = float(should_fallback)
            if should_fallback and no_control_prediction is not None:
                no_control_control.diagnostics["post_guard_safety_no_control_fallback"] = 1.0
                no_control_control.diagnostics["post_guard_no_control_score_gap"] = float(gap)
                no_control_control.diagnostics["post_guard_no_control_tie_fallback"] = float(tie_fallback)
                metadata["post_guard_safety_fallback_occurred"] = 1.0
                metadata["post_guard_safety_fallback_baseline"] = "no_control"
                metadata["post_guard_safety_status"] = "fallback_no_control"
                metadata.update(_physical_action_metadata("post_guard_final", no_control_control, cfg, actuation))
                return no_control_control, metadata, no_control_prediction
    else:
        metadata["post_guard_no_control_score_status"] = "disabled"

    pfo_settings = _mapping(safety.get("pfo_baseline"))
    pfo_enabled = bool(pfo_settings.get("enabled", False))
    metadata["post_guard_pfo_baseline_enabled"] = float(pfo_enabled)
    if pfo_enabled:
        pfo_control, pfo_metadata = _guarded_pfo_baseline(
            cfg,
            state,
            forecast,
            previous,
            state_json,
            actuation,
            ControlAction,
        )
        metadata.update(pfo_metadata)
        if pfo_control is not None:
            metadata.update(_physical_action_metadata("post_guard_pfo", pfo_control, cfg, actuation))
            pfo_prediction = build_one_step_prediction(state, pfo_control, forecast, cfg, calibration)
            pfo_score, pfo_status = _score_prediction_with_terminal_fit(pfo_prediction, cfg, spec)
            _add_score_metadata(metadata, "post_guard_pfo", pfo_score, pfo_status)
            if pfo_score is not None:
                gap = float(post_score["score"] - pfo_score["score"])
                metadata["post_guard_pfo_score_gap"] = gap
                metadata["post_guard_vs_pfo_score_gap"] = gap
    metadata.update(_physical_action_metadata("post_guard_final", control, cfg, actuation))
    return control, metadata, prediction


DIAGNOSTIC_SIGNALS = ("A", "B", "C", "D", "F")


def _controlled_signal_names(cfg) -> list[str]:
    signals = getattr(getattr(cfg, "network", None), "signals", None)
    out = [str(signal) for signal in (signals or []) if str(signal)]
    return out if out else list(DIAGNOSTIC_SIGNALS)


def _diagnostic_fixed_control(
    cfg,
    ControlAction,
    *,
    vsl_kph: float = 120.0,
    d_ramp_rate_vph: float | None = None,
    f_ramp_rate_vph: float | None = None,
    major_green_sec: float = 57.0,
    minor_green_sec: float = 57.0,
    offset_sec: float = 0.0,
):
    control = ControlAction.fixed(cfg)
    cap = cfg.network.ramp_capacity_veh_h
    control.vsl = {link: float(vsl_kph) for link in cfg.network.freeway_links}
    for link in cfg.network.freeway_links:
        for i in range(int(getattr(cfg.network, "freeway_segments_per_link", 0))):
            control.vsl[f"{link}__seg{i}"] = float(vsl_kph)
    d_rate = (
        float(d_ramp_rate_vph)
        if d_ramp_rate_vph is not None
        else (float(cap.get("R_D_W", 0.0)) + float(cap.get("R_D_E", 0.0))) / 2.0
    )
    f_rate = (
        float(f_ramp_rate_vph)
        if f_ramp_rate_vph is not None
        else (float(cap.get("R_F_W", 0.0)) + float(cap.get("R_F_E", 0.0))) / 2.0
    )
    control.ramp_metering = {
        "R_D_W": float(d_rate),
        "R_D_E": float(d_rate),
        "R_F_W": float(f_rate),
        "R_F_E": float(f_rate),
    }
    for signal in _controlled_signal_names(cfg):
        control.green_times[f"{signal}_p1"] = float(minor_green_sec)
        control.green_times[f"{signal}_p2"] = float(major_green_sec)
        control.offsets[signal] = float(offset_sec)
    control.diagnostics.update({
        "diagnostic_fixed_actuation_active": 1.0,
        "diagnostic_forced_vsl_kph": float(vsl_kph),
        "diagnostic_forced_d_ramp_rate_vph": float(d_rate),
        "diagnostic_forced_f_ramp_rate_vph": float(f_rate),
        "diagnostic_forced_signal_major_green_sec": float(major_green_sec),
        "diagnostic_forced_signal_minor_green_sec": float(minor_green_sec),
        "diagnostic_bypass_policy_guards": 1.0,
    })
    return control


def _force_all_vsl(control, cfg, vsl_kph: float) -> None:
    control.vsl = {link: float(vsl_kph) for link in cfg.network.freeway_links}
    for link in cfg.network.freeway_links:
        for i in range(int(getattr(cfg.network, "freeway_segments_per_link", 0))):
            control.vsl[f"{link}__seg{i}"] = float(vsl_kph)


def _force_open_ramps(control, cfg) -> None:
    cap = getattr(cfg.network, "ramp_capacity_veh_h", {}) or {}
    ramps = list(getattr(cfg.network, "ramps", ()) or cap.keys())
    control.ramp_metering = {
        str(ramp): float(cap.get(str(ramp), 1800.0))
        for ramp in ramps
    }


def _diagnostic_open_ramp_original_signal_control(cfg, ControlAction):
    control = ControlAction.uncontrolled(cfg)
    _force_all_vsl(control, cfg, 120.0)
    _force_open_ramps(control, cfg)
    control.diagnostics.update({
        "diagnostic_pure_lever_baseline": 1.0,
        "diagnostic_forced_vsl_kph": 120.0,
        "diagnostic_ramps_forced_open": 1.0,
        "diagnostic_signal_original_vissim": 1.0,
    })
    return control


def diagnostic_vsl60_only_control(cfg, ControlAction):
    control = _diagnostic_open_ramp_original_signal_control(cfg, ControlAction)
    _force_all_vsl(control, cfg, 60.0)
    control.diagnostics["diagnostic_vsl60_only_active"] = 1.0
    control.diagnostics["diagnostic_forced_vsl_kph"] = 60.0
    return control


def diagnostic_vsl80_only_control(cfg, ControlAction):
    control = _diagnostic_open_ramp_original_signal_control(cfg, ControlAction)
    _force_all_vsl(control, cfg, 80.0)
    control.diagnostics["diagnostic_vsl80_only_active"] = 1.0
    control.diagnostics["diagnostic_forced_vsl_kph"] = 80.0
    return control


def _diagnostic_signal_only_control(
    cfg,
    ControlAction,
    *,
    major_green_sec: float,
    minor_green_sec: float,
    offset_sec: float = 0.0,
):
    control = _diagnostic_open_ramp_original_signal_control(cfg, ControlAction)
    for signal in _controlled_signal_names(cfg):
        control.green_times[f"{signal}_p1"] = float(minor_green_sec)
        control.green_times[f"{signal}_p2"] = float(major_green_sec)
        control.offsets[signal] = float(offset_sec)
    control.diagnostics.update({
        "diagnostic_signal_only_active": 1.0,
        "diagnostic_forced_signal_major_green_sec": float(major_green_sec),
        "diagnostic_forced_signal_minor_green_sec": float(minor_green_sec),
        "diagnostic_forced_signal_offset_sec": float(offset_sec),
    })
    return control


def diagnostic_signal_major90_only_control(cfg, ControlAction):
    control = _diagnostic_signal_only_control(
        cfg,
        ControlAction,
        major_green_sec=90.0,
        minor_green_sec=5.0,
    )
    control.diagnostics["diagnostic_signal_major90_only_active"] = 1.0
    return control


def diagnostic_signal_minor90_only_control(cfg, ControlAction):
    control = _diagnostic_signal_only_control(
        cfg,
        ControlAction,
        major_green_sec=5.0,
        minor_green_sec=90.0,
    )
    control.diagnostics["diagnostic_signal_minor90_only_active"] = 1.0
    return control


def diagnostic_signal_offset60_only_control(cfg, ControlAction):
    control = _diagnostic_signal_only_control(
        cfg,
        ControlAction,
        major_green_sec=57.0,
        minor_green_sec=57.0,
        offset_sec=60.0,
    )
    control.diagnostics["diagnostic_signal_offset60_only_active"] = 1.0
    return control


def diagnostic_vsl_rm_control(cfg, ControlAction):
    """Forced actuator diagnostic: lower VSL and meter both D/F ramps together.

    This is intentionally not an optimizer policy. It verifies that the Vissim
    bridge can apply VSL and ramp-metering actuation simultaneously before we
    attribute non-movement to the controller objective/calibration.
    """
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        vsl_kph=80.0,
        d_ramp_rate_vph=min(1253.0, float(cfg.network.ramp_capacity_veh_h.get("R_D_W", 1253.0))),
        f_ramp_rate_vph=min(284.0, float(cfg.network.ramp_capacity_veh_h.get("R_F_W", 284.0))),
    )
    control.diagnostics["diagnostic_forced_vsl_rm_active"] = 1.0
    control.diagnostics["diagnostic_forced_ramp_green_target_sec"] = 4.0
    return control


def diagnostic_fixed57_control(cfg, ControlAction):
    return _diagnostic_fixed_control(cfg, ControlAction)


def diagnostic_ramp_hold_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        d_ramp_rate_vph=691.0,
    )
    control.diagnostics["diagnostic_ramp_hold_active"] = 1.0
    control.diagnostics["diagnostic_ramp_hold_target_green_sec"] = 2.0
    return control


def diagnostic_ramp_d1364_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        d_ramp_rate_vph=1364.0,
    )
    control.diagnostics["diagnostic_ramp_d1364_active"] = 1.0
    control.diagnostics["diagnostic_ramp_d1364_target_green_sec"] = 6.0
    return control


def diagnostic_ramp_d1253_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        d_ramp_rate_vph=1253.0,
    )
    control.diagnostics["diagnostic_ramp_d1253_active"] = 1.0
    control.diagnostics["diagnostic_ramp_d1253_target_green_sec"] = 4.0
    return control


def diagnostic_vsl80_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction, vsl_kph=80.0)
    control.diagnostics["diagnostic_vsl80_active"] = 1.0
    return control


def diagnostic_vsl80_original_signal_control(cfg, ControlAction):
    control = diagnostic_vsl80_control(cfg, ControlAction)
    control.diagnostics["diagnostic_original_signal_active"] = 1.0
    return control


def diagnostic_ramp_all735_original_signal_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        d_ramp_rate_vph=735.0,
        f_ramp_rate_vph=735.0,
    )
    control.diagnostics["diagnostic_ramp_all735_original_signal_active"] = 1.0
    return control


def diagnostic_ramp_all360_original_signal_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        d_ramp_rate_vph=360.0,
        f_ramp_rate_vph=360.0,
    )
    control.diagnostics["diagnostic_ramp_all360_original_signal_active"] = 1.0
    return control


def diagnostic_vsl110_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction, vsl_kph=110.0)
    control.diagnostics["diagnostic_vsl110_active"] = 1.0
    return control


def diagnostic_vsl100_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction, vsl_kph=100.0)
    control.diagnostics["diagnostic_vsl100_active"] = 1.0
    return control


def diagnostic_signal_major_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        major_green_sec=75.0,
        minor_green_sec=25.0,
    )
    control.diagnostics["diagnostic_signal_major_active"] = 1.0
    return control


def diagnostic_signal_minor_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        major_green_sec=25.0,
        minor_green_sec=75.0,
    )
    control.diagnostics["diagnostic_signal_minor_active"] = 1.0
    return control


def diagnostic_signal_major62_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        major_green_sec=62.0,
        minor_green_sec=52.0,
    )
    control.diagnostics["diagnostic_signal_major62_active"] = 1.0
    return control


def diagnostic_signal_minor62_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        major_green_sec=52.0,
        minor_green_sec=62.0,
    )
    control.diagnostics["diagnostic_signal_minor62_active"] = 1.0
    return control


def diagnostic_signal_offset30_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        major_green_sec=57.0,
        minor_green_sec=57.0,
        offset_sec=30.0,
    )
    control.diagnostics["diagnostic_signal_offset30_active"] = 1.0
    return control


def diagnostic_combined_strong_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        vsl_kph=80.0,
        d_ramp_rate_vph=691.0,
        major_green_sec=75.0,
        minor_green_sec=25.0,
    )
    control.diagnostics["diagnostic_combined_strong_active"] = 1.0
    return control


def diagnostic_combined_extreme_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        vsl_kph=60.0,
        d_ramp_rate_vph=360.0,
        f_ramp_rate_vph=360.0,
        major_green_sec=90.0,
        minor_green_sec=5.0,
    )
    control.diagnostics["diagnostic_combined_extreme_active"] = 1.0
    return control


def write_action_csv(
    path: Path,
    control,
    cfg,
    mapping: dict[str, Any],
    segment_vsl_func,
    metadata: dict[str, Any],
    actuation: Mapping[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    vsl_set = [float(v) for v in cfg.freeway_follower.vsl_set]
    if 120.0 not in vsl_set:
        # Allow no-control-ish 120 km/h on Vissim when previous/control provides it.
        vsl_set = sorted(set(vsl_set + [120.0]))
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        fields = [
            "kind",
            "id",
            "dsd_no",
            "sc_no",
            "link",
            "lane",
            "speed_kph",
            "major_green",
            "minor_green",
            "offset",
            "rate_vph",
            "green_sec",
            "metadata",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for seg in mapping["segments"]:
            segment_id = seg["segment_id"]
            model_link, idx = _segment_model_coordinates(str(segment_id), seg)
            value = nearest(segment_vsl_func(control, model_link, idx, cfg), vsl_set)
            for dsd in _segment_dsd_controls(seg):
                lane = dsd.get("lane", "")
                writer.writerow({
                    "kind": "vsl",
                    "id": segment_id,
                    "dsd_no": dsd["dsd_no"],
                    "link": seg["link"],
                    "lane": lane,
                    "speed_kph": value,
                    "metadata": metadata.get("controller_status", ""),
                })
        signal_settings = _mapping(actuation.get("real_world_signal_control"))
        write_signal_rows = bool(signal_settings.get("enabled", True))
        if str(metadata.get("controller_variant", "")) == "no-control" and not bool(
            signal_settings.get("apply_to_no_control", False)
        ):
            write_signal_rows = False
        if bool(metadata.get("suppress_signal_rows", False)):
            write_signal_rows = False
        if write_signal_rows:
            for signal_row in _signal_rows_for_mapping(mapping):
                signal = str(signal_row["id"])
                sc_no = int(signal_row["sc_no"])
                # Phase-axis fix (2026-06-30): VISSIM SG1(MAJOR) controls the E-W/arterial approaches,
                # which the model serves in phase p2; SG2(MINOR) controls the N-S/cross approaches = model
                # phase p1. Verified against evaluation/signal_install/signal_manifest.csv (20/20 approach
                # links). The previous mapping (major<-p1, minor<-p2) axis-swapped every signal's green
                # allocation in VISSIM, so the controller's green was applied to the wrong axis.
                major = clamp(float(control.green_times.get(f"{signal}_p2", 40.0)), 5.0, 90.0)
                minor = clamp(float(control.green_times.get(f"{signal}_p1", 40.0)), 5.0, 90.0)
                offset = float(control.offsets.get(signal, 0.0))
                writer.writerow({
                    "kind": "signal",
                    "id": signal,
                    "sc_no": sc_no,
                    "major_green": round(major, 3),
                    "minor_green": round(minor, 3),
                    "offset": round(offset, 3),
                    "metadata": metadata.get("controller_status", ""),
                })
        if isinstance(mapping.get("ramp_meters"), list) and mapping.get("ramp_meters"):
            for ramp, spec in real_world_ramp_meter_actions(control, cfg, actuation, mapping).items():
                writer.writerow({
                    "kind": "ramp_meter",
                    "id": ramp,
                    "sc_no": int(_as_float(spec.get("sc_no"), 0.0)),
                    "rate_vph": round(_as_float(spec.get("rate_vph"), 0.0), 3),
                    "green_sec": round(_as_float(spec.get("green_sec"), 10.0), 3),
                    "metadata": (
                        f"{metadata.get('controller_status', '')};"
                        f"model_ramp_key={spec.get('model_ramp_key', '')};"
                        f"group_rate_vph={round(_as_float(spec.get('group_rate_vph'), 0.0), 3)}"
                    ),
                })
        else:
            ramp_to_sc = {"D": 6, "F": 7}
            for ramp, spec in physical_ramp_actions(control, cfg, actuation).items():
                writer.writerow({
                    "kind": "ramp_meter",
                    "id": ramp,
                    "sc_no": ramp_to_sc[ramp],
                    "rate_vph": round(spec["rate_vph"], 3),
                    "green_sec": round(spec["green_sec"], 3),
                    "metadata": metadata.get("controller_status", ""),
                })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-json", required=True)
    parser.add_argument("--previous-action-json", default="")
    parser.add_argument("--out-action-json", required=True)
    parser.add_argument("--out-action-csv", required=True)
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--mapping-json", default=str(DEFAULT_MAPPING))
    parser.add_argument("--detector-mapping-json", default=str(DEFAULT_DETECTOR_MAPPING))
    parser.add_argument("--mode", choices=["fast-smoke", "fuller-smoke"], default="fast-smoke")
    parser.add_argument(
        "--controller",
        choices=[
            "stackelberg",
            "stackelberg-wu-metered",
            "pstack-flagship",
            "pfo",
            "wu",
            "wu-leader",
            "no-control",
            "diagnostic-vsl-rm",
            "diagnostic-fixed57",
            "diagnostic-ramp-hold",
            "diagnostic-ramp-d1364",
            "diagnostic-ramp-d1253",
            "diagnostic-vsl60-only",
            "diagnostic-vsl80-only",
            "diagnostic-vsl110",
            "diagnostic-vsl100",
            "diagnostic-vsl80",
            "diagnostic-vsl80-original",
            "diagnostic-ramp-all735-original",
            "diagnostic-ramp-all360-original",
            "diagnostic-signal-major90-only",
            "diagnostic-signal-minor90-only",
            "diagnostic-signal-offset60-only",
            "diagnostic-signal-major62",
            "diagnostic-signal-minor62",
            "diagnostic-signal-major",
            "diagnostic-signal-minor",
            "diagnostic-signal-offset30",
            "diagnostic-combined-strong",
            "diagnostic-combined-extreme",
        ],
        default="stackelberg",
    )
    parser.add_argument("--calibration-json", default=str(DEFAULT_CALIBRATION))
    parser.add_argument("--tuning-json", default="")
    args = parser.parse_args()

    started = time.perf_counter()
    repo_root = Path(args.repo_root)
    mapping_path = Path(args.mapping_json)
    state_path = Path(args.state_json)
    out_json = Path(args.out_action_json)
    out_csv = Path(args.out_action_csv)
    state_json = json.loads(state_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    detector_mapping = load_optional_json(args.detector_mapping_json)
    calibration = load_optional_json(args.calibration_json)
    tuning = load_optional_json(args.tuning_json)
    calibration_override = tuning.get("calibration_override", {})
    if isinstance(calibration_override, Mapping):
        calibration = deep_update(dict(calibration), calibration_override)
    actuation = adapter_actuation_settings(calibration, tuning)
    control_interval = float(state_json.get("control_interval_sec", 60.0))
    sim_period = float(state_json.get("sim_period_sec", max(180.0, control_interval)))

    (
        StackelbergMPCController,
        DemandStep,
        ControlAction,
        _ExperimentConfig,
        TrafficState,
        segment_vsl_func,
    ) = repo_imports(repo_root)
    local_observation = bool(_link_counts_from_local_observation(state_json) and detector_mapping)
    cfg = build_config(
        repo_root,
        control_interval,
        sim_period,
        args.mode,
        calibration,
        tuning,
        local_observation=local_observation,
        flagship=(args.controller == "pstack-flagship"),
    )
    adapter_runtime_metadata = install_adapter_calibration_fingerprints(cfg, tuning)
    runtime_patch_metadata = install_vissim_calibration_runtime_patches(cfg, calibration)
    runtime_patch_metadata.update(install_vsl_metanet_rollout_runtime_patch(cfg, tuning))
    state = traffic_state_from_vissim(state_json, cfg, TrafficState, detector_mapping, calibration)
    if local_observation:
        install_local_observation_runtime_guards()
    forecast_horizon_steps = int(cfg.mpc.horizon_steps)
    if args.controller == "pstack-flagship":
        # 러너 L1044: 리더 value-depth rollout이 horizon 밖 수요를 소비한다 —
        # forecast 길이 = horizon_steps + max(0, leader_value_depth).
        forecast_horizon_steps += max(0, int(getattr(cfg.mpc, "leader_value_depth", 0)))
    forecast = demand_from_state(
        state_json,
        cfg,
        DemandStep,
        forecast_horizon_steps,
        calibration,
        detector_mapping,
    )
    previous_path = Path(args.previous_action_json) if args.previous_action_json else Path("__missing_previous.json")
    previous = control_from_json(previous_path, cfg, ControlAction)
    observed_summary = summarize_model_state(state, cfg)
    prediction_error = prediction_error_from_previous(previous_path, observed_summary)

    metadata: dict[str, Any] = {
        "controller": (
            "StackelbergMPCController"
            if args.controller == "stackelberg"
            else "StackelbergWuMeteredController"
            if args.controller == "stackelberg-wu-metered"
            else "F1StackelbergWuMeteredController"
            if args.controller == "pstack-flagship"
            else "DistributedCoordinator"
            if args.controller == "pfo"
            else "NoControl"
            if args.controller == "no-control"
            else "DiagnosticVslRampMetering"
            if args.controller == "diagnostic-vsl-rm"
            else "DiagnosticFixedActuation"
            if args.controller.startswith("diagnostic-")
            else "WuDistributedController"
        ),
        "controller_variant": args.controller,
        "adapter_mode": args.mode,
        "controller_status": "ok",
        "sim_sec": float(state_json.get("sim_sec", 0.0)),
        "calibration_version": str(calibration.get("calibration_version", "")),
        "tuning_name": str(tuning.get("name", "")),
        "F_ramp_mode": str(actuation.get("F_ramp_mode", "")),
        "F_ramp_invalid_guard_configured": float(bool(actuation.get("F_ramp_invalid_guard_active", False))),
        "observation_mode": "detector_local_v2_storage_split" if local_observation else "global_fallback",
        "follower_solver_mode": str(cfg.mpc.follower_solver_mode),
        "local_observation_runtime_guard": float(local_observation),
        "mpc_horizon_steps": float(cfg.mpc.horizon_steps),
        "mpc_control_horizon_steps": float(cfg.mpc.control_horizon_steps),
        "mpc_max_nash_iter": float(cfg.mpc.max_nash_iter),
        "freeway_horizon_beam_width": float(getattr(cfg.freeway_follower, "horizon_beam_width", 0.0)),
        "freeway_horizon_ramp_candidate_limit": float(
            getattr(cfg.freeway_follower, "horizon_ramp_candidate_limit", 0.0)
        ),
        "freeway_horizon_vsl_candidate_limit_per_link": float(
            getattr(cfg.freeway_follower, "horizon_vsl_candidate_limit_per_link", 0.0)
        ),
    }
    if forecast:
        forecast0 = forecast[0]
        demand_payload = _mapping(state_json.get("demand"))
        forecast_profile = str(demand_payload.get("demand_profile", "")).lower()
        route_bias_forecast = _mapping(_mapping(calibration.get("prediction")).get("route_bias_forecast"))
        route_bias_enabled = bool(route_bias_forecast.get("enabled", True))
        route_bias_applied = route_bias_enabled and forecast_profile in {
            "d_ramp_bias",
            "d_ramp_heavy",
            "f_ramp_bias",
            "f_ramp_heavy",
        }
        metadata.update({
            "demand_profile_forecast_profile_aware": 1.0,
            "demand_profile": forecast_profile,
            "demand_urban_west_east_ratio": float(_as_float(demand_payload.get("urban_west_east_ratio"), 1.0)),
            "demand_profile_route_bias_forecast_applied": float(route_bias_applied),
            "route_bias_forecast_target_share": float(_as_float(route_bias_forecast.get("target_share"), 0.98)),
            "forecast_freeway_FW_E_vph": float(forecast0.freeway_mainline.get("FW_E", 0.0)),
            "forecast_freeway_FW_W_vph": float(forecast0.freeway_mainline.get("FW_W", 0.0)),
            "forecast_urban_boundary_in_total_vph": float(
                sum(
                    float(forecast0.urban_boundary.get(str(link), 0.0))
                    for link in cfg.network.boundary_in_links
                )
            ),
            "forecast_ramp_arrival_total_vph": float(
                sum(float(value) for value in forecast0.ramp_arrival.values())
            ),
            "forecast_ramp_arrival_R_D_W_vph": float(forecast0.ramp_arrival.get("R_D_W", 0.0)),
            "forecast_ramp_arrival_R_D_E_vph": float(forecast0.ramp_arrival.get("R_D_E", 0.0)),
            "forecast_ramp_arrival_R_F_W_vph": float(forecast0.ramp_arrival.get("R_F_W", 0.0)),
            "forecast_ramp_arrival_R_F_E_vph": float(forecast0.ramp_arrival.get("R_F_E", 0.0)),
        })
    storage_values = [
        max(0.0, _as_float(value))
        for value in getattr(cfg.network, "urban_link_storage_veh", {}).values()
    ]
    metadata.update({
        "network_lost_time_sec": float(getattr(cfg.network, "lost_time", 0.0)),
        "network_movement_capacity_veh_h": float(getattr(cfg.network, "movement_capacity_veh_h", 0.0)),
        "network_boundary_queue_max_veh": float(getattr(cfg.network, "boundary_queue_max_veh", 0.0)),
        "network_ramp_queue_max_veh": float(getattr(cfg.network, "ramp_queue_max_veh", 0.0)),
        "network_urban_link_storage_count": float(len(storage_values)),
        "network_urban_link_storage_min_veh": float(min(storage_values)) if storage_values else 0.0,
        "network_urban_link_storage_max_veh": float(max(storage_values)) if storage_values else 0.0,
        "network_urban_link_storage_total_veh": float(sum(storage_values)),
        "network_ramp_capacity_R_D_W_veh_h": float(cfg.network.ramp_capacity_veh_h.get("R_D_W", 0.0)),
        "network_ramp_capacity_R_D_E_veh_h": float(cfg.network.ramp_capacity_veh_h.get("R_D_E", 0.0)),
        "network_ramp_capacity_R_F_W_veh_h": float(cfg.network.ramp_capacity_veh_h.get("R_F_W", 0.0)),
        "network_ramp_capacity_R_F_E_veh_h": float(cfg.network.ramp_capacity_veh_h.get("R_F_E", 0.0)),
    })
    metadata.update(adapter_runtime_metadata)
    metadata.update(runtime_patch_metadata)
    if hasattr(state, "local_observation_summary"):
        summary = state.local_observation_summary
        summary_agents = summary.get("agents", {})
        metadata["local_observation_agent_count"] = float(len(summary_agents))
        if isinstance(summary_agents, Mapping):
            flagged_agents = [
                agent
                for agent in summary_agents.values()
                if isinstance(agent, Mapping)
                and ("control_enabled" in agent or "monitoring_only" in agent)
            ]
            if flagged_agents:
                metadata["local_observation_control_agent_count"] = float(
                    sum(1 for agent in flagged_agents if bool(agent.get("control_enabled", True)))
                )
                metadata["local_observation_monitoring_agent_count"] = float(
                    sum(1 for agent in flagged_agents if bool(agent.get("monitoring_only", False)))
                )
        metadata["local_observation_total_movement_queue"] = float(
            sum(max(0.0, _as_float(v)) for v in summary.get("urban_movement_queue", {}).values())
        )
        metadata["local_observation_total_ramp_queue"] = float(
            sum(max(0.0, _as_float(v)) for v in summary.get("ramp_queue", {}).values())
        )
        storage_occupancy = summary.get("urban_link_storage_occupancy", {})
        if isinstance(storage_occupancy, Mapping):
            metadata["local_observation_total_storage_occupancy"] = float(
                sum(max(0.0, _as_float(v)) for v in storage_occupancy.values())
            )
            off_storage_links = {str(v) for v in cfg.network.off_ramp_storage_link.values()}
            metadata["local_observation_offramp_storage_occupancy"] = float(
                sum(
                    max(0.0, _as_float(value))
                    for key, value in storage_occupancy.items()
                    if str(key) in off_storage_links
                )
            )
        split_params = summary.get("split_parameters", {})
        if isinstance(split_params, Mapping):
            metadata["local_observation_internal_storage_fraction"] = float(
                split_params.get("internal_storage_fraction", 0.0)
            )
            metadata["local_observation_offramp_storage_fraction"] = float(
                split_params.get("offramp_storage_fraction", 0.0)
            )
    if prediction_error:
        metadata["prediction_audit_available"] = float(prediction_error.get("status") == "ok")
        scalar_errors = prediction_error.get("scalar_errors", {})
        if isinstance(scalar_errors, Mapping):
            total_error = scalar_errors.get("total_model_vehicles", {})
            protected_error = scalar_errors.get("protected_accumulation_veh", {})
            freeway_error = scalar_errors.get("freeway_total_veh", {})
            if isinstance(total_error, Mapping):
                metadata["prediction_total_model_vehicles_error"] = float(total_error.get("error", 0.0))
                metadata["prediction_total_model_vehicles_abs_error"] = float(total_error.get("abs_error", 0.0))
            if isinstance(protected_error, Mapping):
                metadata["prediction_protected_accumulation_abs_error"] = float(protected_error.get("abs_error", 0.0))
            if isinstance(freeway_error, Mapping):
                metadata["prediction_freeway_total_abs_error"] = float(freeway_error.get("abs_error", 0.0))
    try:
        controller = None
        if args.controller == "no-control":
            control = ControlAction.uncontrolled(cfg)
            control.diagnostics["no_control_active"] = 1.0
        elif args.controller == "diagnostic-vsl-rm":
            control = diagnostic_vsl_rm_control(cfg, ControlAction)
            metadata["diagnostic_forced_vsl_rm_active"] = 1.0
        elif args.controller == "diagnostic-fixed57":
            control = diagnostic_fixed57_control(cfg, ControlAction)
            metadata["diagnostic_fixed57_active"] = 1.0
        elif args.controller == "diagnostic-ramp-hold":
            control = diagnostic_ramp_hold_control(cfg, ControlAction)
            metadata["diagnostic_ramp_hold_active"] = 1.0
        elif args.controller == "diagnostic-ramp-d1364":
            control = diagnostic_ramp_d1364_control(cfg, ControlAction)
            metadata["diagnostic_ramp_d1364_active"] = 1.0
        elif args.controller == "diagnostic-ramp-d1253":
            control = diagnostic_ramp_d1253_control(cfg, ControlAction)
            metadata["diagnostic_ramp_d1253_active"] = 1.0
        elif args.controller == "diagnostic-vsl60-only":
            control = diagnostic_vsl60_only_control(cfg, ControlAction)
            metadata["diagnostic_vsl60_only_active"] = 1.0
            metadata["suppress_signal_rows"] = 1.0
        elif args.controller == "diagnostic-vsl80-only":
            control = diagnostic_vsl80_only_control(cfg, ControlAction)
            metadata["diagnostic_vsl80_only_active"] = 1.0
            metadata["suppress_signal_rows"] = 1.0
        elif args.controller == "diagnostic-vsl110":
            control = diagnostic_vsl110_control(cfg, ControlAction)
            metadata["diagnostic_vsl110_active"] = 1.0
        elif args.controller == "diagnostic-vsl100":
            control = diagnostic_vsl100_control(cfg, ControlAction)
            metadata["diagnostic_vsl100_active"] = 1.0
        elif args.controller == "diagnostic-vsl80":
            control = diagnostic_vsl80_control(cfg, ControlAction)
            metadata["diagnostic_vsl80_active"] = 1.0
        elif args.controller == "diagnostic-vsl80-original":
            control = diagnostic_vsl80_original_signal_control(cfg, ControlAction)
            metadata["diagnostic_vsl80_original_signal_active"] = 1.0
            metadata["suppress_signal_rows"] = 1.0
        elif args.controller == "diagnostic-ramp-all735-original":
            control = diagnostic_ramp_all735_original_signal_control(cfg, ControlAction)
            metadata["diagnostic_ramp_all735_original_signal_active"] = 1.0
            metadata["suppress_signal_rows"] = 1.0
        elif args.controller == "diagnostic-ramp-all360-original":
            control = diagnostic_ramp_all360_original_signal_control(cfg, ControlAction)
            metadata["diagnostic_ramp_all360_original_signal_active"] = 1.0
            metadata["suppress_signal_rows"] = 1.0
        elif args.controller == "diagnostic-signal-major90-only":
            control = diagnostic_signal_major90_only_control(cfg, ControlAction)
            metadata["diagnostic_signal_major90_only_active"] = 1.0
        elif args.controller == "diagnostic-signal-minor90-only":
            control = diagnostic_signal_minor90_only_control(cfg, ControlAction)
            metadata["diagnostic_signal_minor90_only_active"] = 1.0
        elif args.controller == "diagnostic-signal-offset60-only":
            control = diagnostic_signal_offset60_only_control(cfg, ControlAction)
            metadata["diagnostic_signal_offset60_only_active"] = 1.0
        elif args.controller == "diagnostic-signal-major62":
            control = diagnostic_signal_major62_control(cfg, ControlAction)
            metadata["diagnostic_signal_major62_active"] = 1.0
        elif args.controller == "diagnostic-signal-minor62":
            control = diagnostic_signal_minor62_control(cfg, ControlAction)
            metadata["diagnostic_signal_minor62_active"] = 1.0
        elif args.controller == "diagnostic-signal-major":
            control = diagnostic_signal_major_control(cfg, ControlAction)
            metadata["diagnostic_signal_major_active"] = 1.0
        elif args.controller == "diagnostic-signal-minor":
            control = diagnostic_signal_minor_control(cfg, ControlAction)
            metadata["diagnostic_signal_minor_active"] = 1.0
        elif args.controller == "diagnostic-signal-offset30":
            control = diagnostic_signal_offset30_control(cfg, ControlAction)
            metadata["diagnostic_signal_offset30_active"] = 1.0
        elif args.controller == "diagnostic-combined-strong":
            control = diagnostic_combined_strong_control(cfg, ControlAction)
            metadata["diagnostic_combined_strong_active"] = 1.0
        elif args.controller == "diagnostic-combined-extreme":
            control = diagnostic_combined_extreme_control(cfg, ControlAction)
            metadata["diagnostic_combined_extreme_active"] = 1.0
        elif args.controller == "stackelberg":
            controller = StackelbergMPCController(cfg)
            metadata.update(install_vissim_terminal_cost_objective(controller, cfg, tuning))
            if hasattr(controller, "decide_with_info"):
                result = controller.decide_with_info(state, forecast, previous, cfg)
                control = result.control
                metadata["leader_objective"] = float(getattr(result, "leader_objective", 0.0))
                metadata["nash_objective"] = float(getattr(getattr(result, "nash", None), "objective_value", 0.0))
                metadata.update({
                    f"meta_{k}": float(v)
                    for k, v in getattr(result, "metadata", {}).items()
                    if isinstance(v, (int, float, bool))
                })
            else:
                control = controller.decide(state, forecast, previous, cfg)
        elif args.controller == "stackelberg-wu-metered":
            # Same Stackelberg leader path as "stackelberg" but with the follower replaced by
            # WuFaithfulFollower (the new O(n)-local metering-PFO follower). The subclass only
            # overrides _make_follower_solver/_evaluate_candidate_set, so decide_with_info is
            # inherited and the call is identical. Note: the follower is NOT a DistributedCoordinator,
            # so leader output-closure keeps N_P_star at intent (no realized override) and the
            # local-observation runtime guard (which patches DistributedCoordinator) does not apply
            # because WuFaithfulFollower is natively local.
            from src.controllers.stackelberg_wu_metered import StackelbergWuMeteredController

            controller = StackelbergWuMeteredController(cfg)
            metadata.update(install_vissim_terminal_cost_objective(controller, cfg, tuning))
            if hasattr(controller, "decide_with_info"):
                result = controller.decide_with_info(state, forecast, previous, cfg)
                control = result.control
                metadata["leader_objective"] = float(getattr(result, "leader_objective", 0.0))
                metadata["nash_objective"] = float(getattr(getattr(result, "nash", None), "objective_value", 0.0))
                metadata["wu_metered_follower"] = 1.0
                metadata.update({
                    f"meta_{k}": float(v)
                    for k, v in getattr(result, "metadata", {}).items()
                    if isinstance(v, (int, float, bool))
                })
            else:
                control = controller.decide(state, forecast, previous, cfg)
        elif args.controller == "pstack-flagship":
            # NumSim flagship P-Stack(P-STACK-WU-FAITHFUL-ALLPRICE-JOINT) 이식 모드.
            # 구성·per-step 로직·사이드카는 run_pstack_flagship_decision 참조.
            control, controller, flagship_metadata = run_pstack_flagship_decision(
                cfg,
                state,
                forecast,
                previous,
                tuning,
                out_json.parent / FLAGSHIP_RUNTIME_FILENAME,
            )
            metadata.update(flagship_metadata)
        elif args.controller == "pfo":
            from src.controllers.distributed_coordinator import DistributedCoordinator

            controller = DistributedCoordinator(cfg)
            result = controller.solve(state.copy(), None, forecast, previous)
            control = result.control
            metadata["pfo_iterations"] = float(getattr(result, "iterations", 0))
            metadata["pfo_converged"] = float(bool(getattr(result, "converged", False)))
            metadata["pfo_objective"] = float(getattr(result, "objective_value", 0.0))
            metadata["pfo_residual_objective"] = float(getattr(result, "residual_objective", 0.0))
            metadata["pfo_residual_control"] = float(getattr(result, "residual_control", 0.0))
            metadata.update({
                f"meta_{k}": float(v)
                for k, v in getattr(result, "diagnostics", {}).items()
                if isinstance(v, (int, float, bool))
            })
        else:
            from src.controllers.wu_distributed import WuDistributedController

            controller = WuDistributedController(cfg, leader_enabled=(args.controller == "wu-leader"))
            result = controller.decide_with_info(state, forecast, previous)
            control = result.control
            metadata["wu_leader_enabled"] = float(args.controller == "wu-leader")
            metadata["wu_iterations"] = float(getattr(result, "iterations", 0))
            metadata["wu_converged"] = float(bool(getattr(result, "converged", False)))
            metadata["wu_coupling_residual"] = float(getattr(result, "coupling_residual", 0.0))
            metadata["wu_solver_evaluations"] = float(getattr(result, "solver_evaluations", 0))
            metadata["wu_computation_time_sec"] = float(getattr(result, "computation_time_sec", 0.0))
            metadata["wu_leader_candidates"] = float(getattr(result, "leader_candidates", 0))
            metadata["wu_leader_objective"] = float(getattr(result, "leader_objective", 0.0))
        if controller is not None and hasattr(controller, "close"):
            controller.close()
    except Exception as exc:  # Keep Vissim running; log and fall back safely.
        control = ControlAction.fixed(cfg)
        metadata["controller_status"] = "fallback_fixed"
        metadata["controller_error_type"] = type(exc).__name__
        metadata["controller_error"] = str(exc)

    control, policy_guard_metadata = apply_vissim_policy_guards(
        control,
        cfg,
        state,
        state_json,
        actuation,
        ControlAction,
    )
    metadata.update(policy_guard_metadata)
    metadata.update(apply_actuation_guards_to_control(control, cfg, actuation))
    prediction = build_one_step_prediction(state, control, forecast, cfg, calibration)
    post_guard_tuning: Mapping[str, Any] = tuning
    if args.controller == "pstack-flagship" and not bool(
        flagship_settings(tuning).get("post_guard_pfo_baseline", False)
    ):
        # SUP_PFO가 flagship의 정식 PFO 기권 메커니즘이므로 post_guard의 PFO 기준선
        # 평가(폴백 포함)는 기본 OFF — 이중 개입 방지. tuning
        # adapter.flagship.post_guard_pfo_baseline=true로만 재활성.
        post_guard_tuning = deep_update(
            dict(tuning),
            {"adapter": {"post_guard_safety": {"pfo_baseline": {"enabled": False}}}},
        )
        metadata["flagship_post_guard_pfo_baseline_forced_off"] = 1.0
    control, post_guard_safety_metadata, prediction = apply_post_guard_safety_evaluation(
        control,
        cfg,
        state,
        state_json,
        forecast,
        previous,
        calibration,
        post_guard_tuning,
        actuation,
        ControlAction,
        prediction,
    )
    metadata.update(post_guard_safety_metadata)
    metadata["prediction_status"] = str(prediction.get("status", ""))
    metadata["prediction_wall_sec"] = float(prediction.get("wall_sec", 0.0))
    audit_calibration = prediction.get("audit_calibration", {})
    if isinstance(audit_calibration, Mapping):
        metadata.update({
            str(key): float(value)
            for key, value in audit_calibration.items()
            if isinstance(value, (int, float, bool))
        })
    metadata["decision_wall_sec"] = round(time.perf_counter() - started, 6)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(
            control_to_json_dict(control, metadata, prediction=prediction, prediction_error=prediction_error),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_action_csv(out_csv, control, cfg, mapping, segment_vsl_func, metadata, actuation)
    print(json.dumps({
        "status": metadata["controller_status"],
        "out_action_json": str(out_json),
        "out_action_csv": str(out_csv),
        "decision_wall_sec": metadata["decision_wall_sec"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
