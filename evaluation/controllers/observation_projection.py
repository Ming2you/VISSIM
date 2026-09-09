"""Opt-in physical branch observations for existing model reservoirs.

This changes a copied detector projection, never the ownership ledger. Topology
and geometry are explicit scenario data. Each selected physical link contributes
its complete snapshot once, to one existing storage; it cannot also seed a signal
queue. Run before traffic_state_from_vissim and follower model construction.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math
from typing import Any, Mapping
import sys


class ProjectionError(ValueError):
    pass


def record_projection_assignment(provenance, physical_link, stock_key, vehicles):
    """Record the actual assignment at its mutation site, after any clipping."""
    count = _count(vehicles, stock_key)
    if count:
        row = provenance.setdefault(str(physical_link), {})
        row[str(stock_key)] = row.get(str(stock_key), 0.0) + count


def audit_projection_provenance(provenance, storage, movement, ramp):
    """Verify assignment provenance covers every urban/ramp summary stock."""
    expected = {**{"storage:" + k: v for k, v in storage.items()},
                **{"movement:" + k: v for k, v in movement.items()},
                **{"ramp:" + k: v for k, v in ramp.items()}}
    assigned = defaultdict(float)
    for row in provenance.values():
        for key, value in row.items():
            assigned[key] += float(value)
    residual = {key: assigned.get(key, 0.0) - float(expected.get(key, 0.0))
                for key in assigned.keys() | expected.keys()
                if abs(assigned.get(key, 0.0) - float(expected.get(key, 0.0))) > 1e-8}
    if residual:
        raise ProjectionError(f"physical assignment provenance does not cover projected stocks: {residual}")
    return {"physical_stock_assignment_veh": sum(assigned.values()),
            "physical_stock_assignment_by_link": provenance}


def _count(value: Any, label: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ProjectionError(f"{label}: expected finite nonnegative count, got {value!r}")
    return number


def install_physical_branch_projection(
    cfg, tuning: Mapping[str, Any], detector_mapping: Mapping[str, Any],
    *, link_counts: Mapping[str, float],
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    """Install a one-link/one-storage table under one explicit configuration key.

    Absent/disabled leaves both cfg and detector mapping untouched. The optional
    capacity table is derived offline from pinned physical geometry. A scenario
    may explicitly request ``observed_lower_bound``: a measured stock is a lower
    bound on real capacity, so preserve it and report a geometry underestimate
    instead of discarding vehicles at projection time.
    """
    section = tuning.get("observation", {}).get("physical_branch_projection", {})
    if not section or section is False:
        return detector_mapping, {"physical_branch_projection_enabled": 0.0}
    if not isinstance(section, Mapping) or type(section.get("enabled", False)) is not bool:
        raise ProjectionError("physical_branch_projection must be an object with boolean enabled")
    if not section.get("enabled", False):
        return detector_mapping, {"physical_branch_projection_enabled": 0.0}
    table = {str(k): str(v) for k, v in section.get("link_to_storage", {}).items()}
    if not table:
        raise ProjectionError("enabled physical_branch_projection requires link_to_storage")
    net = cfg.network
    if not getattr(net, "offramp_direct_share_by_offramp", None):
        raise ProjectionError("physical branch projection requires the installed direct-landing split")
    if getattr(net, "landing_storage_spec", None):
        raise ProjectionError("physical branch projection and aggregate landing storage cannot both seed stock")
    counts = {str(k): _count(v, str(k)) for k, v in link_counts.items()}
    capacities = dict(net.urban_link_storage_veh)
    unknown = sorted(set(table.values()) - capacities.keys())
    if unknown:
        raise ProjectionError(f"unknown target storage: {unknown}")
    reserved = set(map(str, detector_mapping.get("freeway_link_to_model_link", {})))
    reserved.update(map(str, detector_mapping.get("ramp_link_to_queues", {})))
    reserved.update(map(str, detector_mapping.get("link_partition", {}).get("monitor_only_exit_links", [])))
    if reserved.intersection(table):
        raise ProjectionError(f"branch observation overlaps freeway/ramp/excluded channel: {sorted(reserved.intersection(table))}")
    original_origins = detector_mapping.get("link_to_origins", {})
    if set(table) - set(original_origins):
        raise ProjectionError(f"branch physical links absent from detector mapping: {sorted(set(table) - set(original_origins))}")

    target_counts: dict[str, float] = defaultdict(float)
    for link, storage in table.items():
        target_counts[storage] += counts.get(link, 0.0)
    # An exclusive branch reservoir cannot also accept an unaccounted old source.
    for link, origins in original_origins.items():
        if str(link) in table or counts.get(str(link), 0.0) == 0:
            continue
        resolved = {str(net.off_ramp_storage_link.get(str(o), str(o))) for o in origins}
        if resolved.intersection(target_counts):
            raise ProjectionError(f"positive unlisted physical source {link} shares a dedicated branch target")
    declared_caps = section.get("storage_capacity_veh", {})
    if set(declared_caps) - set(target_counts):
        raise ProjectionError("capacity overrides must belong to the dedicated branch targets")
    policy = section.get("capacity_policy", "strict")
    if policy not in {"strict", "observed_lower_bound"}:
        raise ProjectionError(f"unknown capacity_policy: {policy}")
    capacity_rows = {}
    for storage, observed in target_counts.items():
        prior = float(capacities[storage])
        geometric = _count(declared_caps.get(storage, prior), storage)
        if geometric <= 0:
            raise ProjectionError(f"positive capacity required for {storage}")
        if policy == "strict" and observed > geometric + 1e-8:
            raise ProjectionError(f"{storage}: observed {observed} exceeds capacity {geometric}")
        effective = max(geometric, observed) if policy == "observed_lower_bound" else geometric
        capacities[storage] = effective
        capacity_rows[storage] = {
            "prior_veh": prior, "declared_veh": geometric, "effective_veh": effective,
            "observed_floor_added_veh": max(0.0, observed - geometric),
        }
    copied = deepcopy(detector_mapping)
    previous = {}
    for link, storage in table.items():
        previous[link] = list(copied["link_to_origins"][link])
        copied["link_to_origins"][link] = [storage]
        copied.get("link_to_movements", {}).pop(link, None)
    metadata = {
        "physical_branch_projection_enabled": 1.0,
        "physical_branch_projection_link_count": float(len(table)),
        "physical_branch_projection_observed_veh": sum(target_counts.values()),
        "physical_branch_projection_target_veh": dict(target_counts),
        "physical_branch_projection_capacity": capacity_rows,
        "physical_branch_projection_previous_origins": previous,
        "physical_branch_projection_source": section.get("source", "explicit scenario mapping"),
    }
    copied["physical_storage_projection"] = {"link_to_storage": table, "metadata": metadata}
    # Mutate cfg only after validating the complete proposal.
    net.urban_link_storage_veh = capacities
    return copied, metadata


def audit_physical_branch_projection(
    detector_mapping: Mapping[str, Any], link_counts: Mapping[str, float],
    storage_occupancy: Mapping[str, float],
) -> dict[str, Any]:
    """Assert the measured branch stock reached its target once, without clipping."""
    section = detector_mapping.get("physical_storage_projection", {})
    if not section:
        return {}
    targets: dict[str, float] = defaultdict(float)
    provenance = {}
    for link, storage in section["link_to_storage"].items():
        count = _count(link_counts.get(link, 0.0), link)
        targets[storage] += count
        provenance[link] = {"storage": storage, "observed_veh": count, "assigned_veh": count}
    residual = {storage: float(storage_occupancy.get(storage, 0.0)) - count for storage, count in targets.items()}
    if any(abs(value) > 1e-8 for value in residual.values()):
        raise ProjectionError(f"physical branch projection failed count conservation: {residual}")
    return {
        "physical_branch_projection_assigned_veh": sum(targets.values()),
        "physical_branch_projection_residual_veh": sum(residual.values()),
        "physical_branch_projection_provenance": provenance,
    }


def install_direct_branch_capacity_runtime(cfg) -> dict[str, float]:
    """Limit freeway departure by both destinations before removing vehicles.

    The global scheduler splits accepted group flow after the freeway step. Its
    rejection counter cannot restore a vehicle already removed from freeway
    stock. Use the same fixed-share capacity helper as the local candidate model.
    ``cfg.network.local_landing_state`` is installed by link_predictor.configure;
    call this after configure in main and again in spawned price workers.
    """
    if not bool(getattr(cfg.network, "local_landing_state", False)):
        return {"direct_branch_receiving_enabled": 0.0}
    from src.models import urban_queue_model as queue_model
    from evaluation.controllers.link_predictor import branch_capacity

    original = getattr(queue_model, "_direct_branch_capacity_original", None)
    if original is None:
        original = queue_model.off_ramp_capacity_by_freeway_link
        queue_model._direct_branch_capacity_original = original

    def direct_branch_capacity(state, cfg_arg, interval_h=None):
        result = original(state, cfg_arg, interval_h=interval_h)
        net = cfg_arg.network
        if not bool(getattr(net, "local_landing_state", False)):
            return result
        duration = cfg_arg.simulation.T_c_h if interval_h is None else interval_h
        shares = getattr(net, "offramp_direct_share_by_offramp", {}) or {}
        tails = getattr(net, "offramp_direct_tail_by_offramp", {}) or {}
        by_freeway: dict[str, float] = defaultdict(float)
        for off_ramp in net.off_ramps:
            share = float(shares.get(off_ramp, 0.0))
            if not math.isfinite(share) or not 0.0 <= share <= 1.0:
                raise ProjectionError(f"{off_ramp}: direct share must be finite in [0, 1]")
            if share > 0.0:
                tail = tails.get(off_ramp)
                if tail not in net.urban_link_storage_veh:
                    raise ProjectionError(f"{off_ramp}: direct branch requires existing target storage")
                signal = net.off_ramp_storage_link[off_ramp]
                signal_available = queue_model._effective_available_space(state, cfg_arg, signal)
                direct_available = queue_model._effective_available_space(state, cfg_arg, tail)
                result[off_ramp] = branch_capacity(signal_available, direct_available, share, duration)
        # The scheduler lands groups sequentially, but their simultaneous caps
        # must not each reserve the complete space of a shared direct receiver.
        for target in {tails[o] for o in net.off_ramps if float(shares.get(o, 0.0)) > 0.0}:
            groups = [o for o in net.off_ramps if float(shares.get(o, 0.0)) > 0.0 and tails[o] == target]
            needed = sum(result[o] * float(shares[o]) * duration for o in groups)
            available = queue_model._effective_available_space(state, cfg_arg, target)
            scale = min(1.0, available / needed) if needed > 0.0 else 1.0
            for off_ramp in groups:
                result[off_ramp] *= scale
        for off_ramp in net.off_ramps:
            by_freeway[net.off_ramp_from_freeway[off_ramp]] += result[off_ramp]
        result.update(by_freeway)
        return result

    queue_model.off_ramp_capacity_by_freeway_link = direct_branch_capacity
    rebound = 0
    for module in list(sys.modules.values()):
        if module is None or module is queue_model:
            continue
        current = getattr(module, "off_ramp_capacity_by_freeway_link", None)
        if current is original or getattr(current, "__name__", "") == "direct_branch_capacity":
            setattr(module, "off_ramp_capacity_by_freeway_link", direct_branch_capacity)
            rebound += 1
    return {"direct_branch_receiving_enabled": 1.0, "direct_branch_receiving_aliases": float(rebound)}
