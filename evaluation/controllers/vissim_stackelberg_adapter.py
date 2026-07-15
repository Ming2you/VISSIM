from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Mapping


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
# Re-pointed to the tracked git clone at GitHub HEAD 0e07c1c (2026-06-29 audit follow-up).
# The former path "C:/Users/TRLAB/Desktop/찐찐막/Numerical-Sim" is a stale, non-git snapshot
# (default.yaml nu_cong=65/capacity_drop=false) and is kept only as the A/B baseline for the
# nu_cong isolation replay; pass --repo-root explicitly to use it.
DEFAULT_REPO_ROOT = Path("C:/Users/TRLAB/Desktop/찐찐막/Numerical-Sim-git")
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
    return data if isinstance(data, dict) else {}


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
        agents[str(agent_id)] = {
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


def build_config(
    repo_root: Path,
    control_interval: float,
    sim_period: float,
    mode: str,
    calibration: Mapping[str, Any],
    tuning: Mapping[str, Any],
    local_observation: bool = False,
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

    return freeway_mainline, urban_boundary, ramp_arrival, profile


def demand_from_state(
    state_json: dict[str, Any],
    cfg,
    DemandStep,
    horizon_steps: int,
    calibration: Mapping[str, Any] | None = None,
):
    freeway_mainline, urban_boundary, ramp_arrival, _profile = profiled_demand_rates(
        state_json,
        cfg,
        calibration,
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

    if "urban_queue_plus_link_occupancy_total_veh" in summary:
        calibrated["urban_queue_plus_link_occupancy_total_veh"] = float(
            _as_float(summary.get("urban_queue_plus_link_occupancy_total_veh"), 0.0)
            * urban_mass_scale
        )

    return calibrated, {
        "prediction_audit_calibration_applied": 1.0,
        "prediction_audit_freeway_total_scale": float(freeway_scale),
        "prediction_audit_urban_queue_plus_storage_scale": float(urban_mass_scale),
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


def diagnostic_vsl_rm_control(cfg, ControlAction):
    """Forced actuator diagnostic: lower VSL and meter both D/F ramps together.

    This is intentionally not an optimizer policy. It verifies that the Vissim
    bridge can apply VSL and ramp-metering actuation simultaneously before we
    attribute non-movement to the controller objective/calibration.
    """
    control = ControlAction.fixed(cfg)
    control.vsl = {link: 80.0 for link in cfg.network.freeway_links}
    control.ramp_metering = {
        "R_D_W": min(1253.0, float(cfg.network.ramp_capacity_veh_h.get("R_D_W", 1253.0))),
        "R_D_E": min(1253.0, float(cfg.network.ramp_capacity_veh_h.get("R_D_E", 1253.0))),
        "R_F_W": min(284.0, float(cfg.network.ramp_capacity_veh_h.get("R_F_W", 284.0))),
        "R_F_E": min(284.0, float(cfg.network.ramp_capacity_veh_h.get("R_F_E", 284.0))),
    }
    control.diagnostics["diagnostic_forced_vsl_rm_active"] = 1.0
    control.diagnostics["diagnostic_forced_vsl_kph"] = 80.0
    control.diagnostics["diagnostic_forced_ramp_green_target_sec"] = 4.0
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
            model_link, idx = SEGMENT_TO_MODEL[segment_id]
            value = nearest(segment_vsl_func(control, model_link, idx, cfg), vsl_set)
            for lane, dsd in sorted(seg["dsd_by_lane"].items(), key=lambda item: int(item[0])):
                writer.writerow({
                    "kind": "vsl",
                    "id": segment_id,
                    "dsd_no": dsd["dsd_no"],
                    "link": seg["link"],
                    "lane": lane,
                    "speed_kph": value,
                    "metadata": metadata.get("controller_status", ""),
                })
        signal_to_sc = {"A": 1, "B": 2, "C": 3, "D": 4, "F": 5}
        for signal, sc_no in signal_to_sc.items():
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
        choices=["stackelberg", "stackelberg-wu-metered", "pfo", "wu", "wu-leader", "no-control", "diagnostic-vsl-rm"],
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
    )
    runtime_patch_metadata = install_vissim_calibration_runtime_patches(cfg, calibration)
    state = traffic_state_from_vissim(state_json, cfg, TrafficState, detector_mapping, calibration)
    if local_observation:
        install_local_observation_runtime_guards()
    forecast = demand_from_state(state_json, cfg, DemandStep, cfg.mpc.horizon_steps, calibration)
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
            else "DistributedCoordinator"
            if args.controller == "pfo"
            else "NoControl"
            if args.controller == "no-control"
            else "DiagnosticVslRampMetering"
            if args.controller == "diagnostic-vsl-rm"
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
    metadata.update(runtime_patch_metadata)
    if hasattr(state, "local_observation_summary"):
        summary = state.local_observation_summary
        metadata["local_observation_agent_count"] = float(len(summary.get("agents", {})))
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
        elif args.controller == "stackelberg":
            controller = StackelbergMPCController(cfg)
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

    metadata.update(apply_actuation_guards_to_control(control, cfg, actuation))
    prediction = build_one_step_prediction(state, control, forecast, cfg, calibration)
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
