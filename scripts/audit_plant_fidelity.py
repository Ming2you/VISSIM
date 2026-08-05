#!/usr/bin/env python3
"""Build static evidence for the current VISSIM -> NumSim rollout plant.

Only the Python standard library is used. Historical reports under outputs/ are
never read as current evidence; callers must provide live artifacts explicitly
or use the repository defaults below.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = 2
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NE = "NOT_EVALUATED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_evidence(path: Path | None) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "path": str(path.resolve(strict=False)) if path else None,
        "exists": False,
        "is_file": False,
        "size_bytes": None,
        "sha256": None,
        "error": None,
    }
    if path is None:
        evidence["error"] = "path not configured"
        return evidence
    try:
        evidence["exists"] = path.exists()
        evidence["is_file"] = path.is_file()
        if path.is_file():
            evidence["size_bytes"] = path.stat().st_size
            evidence["sha256"] = sha256_file(path)
        elif path.exists():
            evidence["error"] = "path exists but is not a file"
        else:
            evidence["error"] = "file not found"
    except OSError as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
    return evidence


def load_json(path: Path | None) -> tuple[Any | None, str | None]:
    if path is None or not path.is_file():
        return None, "file not found"
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def gate(status: str, reason: str, **evidence: Any) -> dict[str, Any]:
    result = {"status": status, "reason": reason}
    if evidence:
        result["evidence"] = evidence
    return result


def run_git(root: Path, *arguments: str) -> tuple[str | None, str | None]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if proc.returncode:
        message = proc.stderr.strip() or proc.stdout.strip() or f"git exited {proc.returncode}"
        return None, message
    return proc.stdout.strip(), None


def git_evidence(root: Path, require_exact_root: bool = False) -> dict[str, Any]:
    top, top_error = run_git(root, "rev-parse", "--show-toplevel")
    result: dict[str, Any] = {
        "path": str(root.resolve(strict=False)),
        "is_git_root": False,
        "top_level": top,
        "branch": None,
        "commit": None,
        "dirty": None,
        "dirty_path_count": None,
        "dirty_paths": [],
        "error": top_error,
    }
    if top_error or top is None:
        return result
    try:
        exact = Path(top).resolve() == root.resolve()
    except OSError:
        exact = False
    result["is_git_root"] = exact
    if require_exact_root and not exact:
        result["error"] = "path is inside a Git worktree but is not its repository root"
        return result
    branch, branch_error = run_git(root, "branch", "--show-current")
    commit, commit_error = run_git(root, "rev-parse", "HEAD")
    status, status_error = run_git(root, "status", "--porcelain", "--untracked-files=all")
    dirty_paths = status.splitlines() if status is not None else []
    result.update(
        {
            "branch": branch or None,
            "commit": commit,
            "dirty": bool(dirty_paths) if status is not None else None,
            "dirty_path_count": len(dirty_paths) if status is not None else None,
            "dirty_paths": dirty_paths,
            "error": branch_error or commit_error or status_error,
        }
    )
    return result


def network_evidence(path: Path | None, roles_path: Path | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path) if path else None, "available": False, "error": None}
    if path is None or not path.is_file():
        result["error"] = "network XML not found"
        return result
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    links = [element for element in root.iter("link") if element.get("no") is not None]
    connectors = [
        element
        for element in links
        if element.find("./fromLinkEndPt") is not None and element.find("./toLinkEndPt") is not None
    ]
    controllers = [element for element in root.iter("signalController") if element.get("no") is not None]
    active = [element for element in controllers if str(element.get("active", "")).lower() == "true"]
    raw_active_ids = {str(element.get("no")) for element in active}
    heads = list(root.iter("signalHead"))
    head_refs: Counter[str] = Counter()
    malformed_refs = 0
    for head in heads:
        parts = str(head.get("sg", "")).split()
        if parts:
            head_refs[parts[0]] += 1
        else:
            malformed_refs += 1
    role_scope, role_scope_error = read_signal_controller_scope(roles_path)
    urban_eligible_ids = set(role_scope.get("urban_eligible_ids", []))
    model_ids = {sc for sc in urban_eligible_ids if head_refs.get(sc, 0) > 0}
    excluded_ids = urban_eligible_ids - model_ids
    auxiliary_active_ids = raw_active_ids - urban_eligible_ids
    eligible_not_raw_active = urban_eligible_ids - raw_active_ids
    artificial_ramp_ids = auxiliary_active_ids & {str(number) for number in range(9101, 9109)}
    sc9004 = next((element for element in controllers if element.get("no") == "9004"), None)
    result.update(
        {
            "available": True,
            "link_count": len(links),
            "connector_count": len(connectors),
            "regular_link_count": len(links) - len(connectors),
            "signal_controller_count": len(controllers),
            "raw_active_signal_controller_count": len(raw_active_ids),
            "raw_active_signal_controller_ids": sorted(raw_active_ids, key=int),
            "urban_eligible_signal_controller_count": len(urban_eligible_ids) if role_scope_error is None else None,
            "urban_eligible_signal_controller_ids": sorted(urban_eligible_ids, key=int),
            "urban_eligible_source": str(roles_path.resolve(strict=False)) if roles_path else None,
            "urban_eligible_error": role_scope_error,
            "model_signal_controller_count": len(model_ids) if role_scope_error is None else None,
            "model_signal_controller_ids": sorted(model_ids, key=int),
            "model_excluded_signal_controller_count": len(excluded_ids) if role_scope_error is None else None,
            "model_excluded_signal_controllers": [
                {
                    "no": int(sc),
                    "reason": "no signal-head reference in network XML",
                    "head_reference_count": head_refs.get(sc, 0),
                }
                for sc in sorted(excluded_ids, key=int)
            ],
            "auxiliary_active_signal_controller_count": len(auxiliary_active_ids) if role_scope_error is None else None,
            "auxiliary_active_signal_controller_ids": sorted(auxiliary_active_ids, key=int),
            "artificial_ramp_meter_active_signal_controller_count": len(artificial_ramp_ids)
            if role_scope_error is None
            else None,
            "artificial_ramp_meter_active_signal_controller_ids": sorted(artificial_ramp_ids, key=int),
            "urban_eligible_not_raw_active_count": len(eligible_not_raw_active)
            if role_scope_error is None
            else None,
            "urban_eligible_not_raw_active_ids": sorted(eligible_not_raw_active, key=int),
            "signal_head_count": len(heads),
            "signal_head_controller_reference_count": len(head_refs),
            "signal_head_reference_count_by_controller": dict(sorted(head_refs.items(), key=lambda item: int(item[0]))),
            "malformed_signal_head_reference_count": malformed_refs,
            "signal_program_files": sorted(
                {
                    str(element.get("supplyFile2"))
                    for element in controllers
                    if str(element.get("supplyFile2", "")).strip()
                }
            ),
            "sc9004": {
                "controller_present": sc9004 is not None,
                "active": str(sc9004.get("active", "")).lower() == "true" if sc9004 is not None else None,
                "head_reference_count": head_refs.get("9004", 0),
            },
        }
    )
    return result


def _csv_ids(value: Any) -> list[str]:
    ids: list[str] = []
    for part in str(value or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(str(int(float(part))))
        except ValueError:
            continue
    return ids


def read_signal_controller_scope(path: Path | None) -> tuple[dict[str, Any], str | None]:
    if path is None or not path.is_file():
        return {}, "signal-controller roles CSV not found"
    eligible: list[str] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                if str(row.get("active", "")).lower() != "true":
                    continue
                try:
                    eligible.append(str(int(float(str(row.get("no", ""))))))
                except ValueError:
                    continue
    except (OSError, UnicodeError, csv.Error) as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    return {"urban_eligible_ids": sorted(set(eligible), key=int)}, None


def read_stop_owners(path: Path | None) -> tuple[dict[str, str], str | None]:
    if path is None or not path.is_file():
        return {}, "signal-controller roles CSV not found"
    owners: dict[str, str] = {}
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                if str(row.get("active", "")).lower() != "true":
                    continue
                try:
                    sc = str(int(float(str(row.get("no", "")))))
                except ValueError:
                    continue
                for link in _csv_ids(row.get("unique_head_links")):
                    owners.setdefault(link, sc)
    except (OSError, UnicodeError, csv.Error) as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    return owners, None


def _network_downstream(path: Path | None) -> tuple[dict[str, set[str]], str | None]:
    if path is None or not path.is_file():
        return {}, "network XML not found"
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    downstream: dict[str, set[str]] = defaultdict(set)
    for link in root.iter("link"):
        number = link.get("no")
        source = link.find("./fromLinkEndPt")
        target = link.find("./toLinkEndPt")
        if number is None or source is None or target is None:
            continue
        source_lane = str(source.get("lane", "")).split()
        target_lane = str(target.get("lane", "")).split()
        if source_lane and target_lane:
            downstream[source_lane[0]].add(str(number))
            downstream[str(number)].add(target_lane[0])
    return downstream, None


def derive_assignment_ties(
    network_path: Path | None,
    roles_path: Path | None,
    universe: Iterable[str],
    freeway_terminals: Iterable[str],
    max_hops: int = 60,
) -> dict[str, Any]:
    downstream, graph_error = _network_downstream(network_path)
    stop_owners, roles_error = read_stop_owners(roles_path)
    if graph_error or roles_error:
        return {
            "status": STATUS_NE,
            "reason": graph_error or roles_error,
            "tie_count": None,
            "ties": [],
        }
    freeway = {str(value) for value in freeway_terminals}
    ties: list[dict[str, Any]] = []
    unresolved = 0
    for start in sorted({str(value) for value in universe}, key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value)):
        if start in stop_owners:
            continue
        first_nodes = sorted(downstream.get(start, ()))
        queue = deque((node, 1) for node in first_nodes)
        seen = {start, *first_nodes}
        first_terminal_depth: int | None = None
        terminals: set[str] = set()
        while queue:
            node, depth = queue.popleft()
            if depth > max_hops or (first_terminal_depth is not None and depth > first_terminal_depth):
                continue
            terminal = None
            if node in stop_owners:
                terminal = f"SC:{stop_owners[node]}@{node}"
            elif node in freeway:
                terminal = f"FW:{node}"
            if terminal is not None:
                first_terminal_depth = depth if first_terminal_depth is None else first_terminal_depth
                if depth == first_terminal_depth:
                    terminals.add(terminal)
                continue
            for neighbor in sorted(downstream.get(node, ())):
                # A terminal identity is node-based. BFS discovers each node at
                # its shortest depth, so additional paths cannot add a new tie.
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append((neighbor, depth + 1))
        if len(terminals) > 1:
            ties.append({"link": start, "hops": first_terminal_depth, "terminals": sorted(terminals)})
        elif not terminals:
            unresolved += 1
    return {
        "status": STATUS_PASS,
        "reason": "independent breadth-first search completed",
        "tie_count": len(ties),
        "unresolved_count": unresolved,
        "ties": ties,
    }


def assignment_evidence(
    path: Path | None, network_path: Path | None, roles_path: Path | None
) -> dict[str, Any]:
    data, error = load_json(path)
    result: dict[str, Any] = {"path": str(path) if path else None, "available": False, "error": error}
    if not isinstance(data, Mapping):
        if data is not None and error is None:
            result["error"] = "assignment JSON root is not an object"
        return result
    owner = data.get("link_owner") if isinstance(data.get("link_owner"), Mapping) else {}
    freeway_map = data.get("freeway_bound_links") if isinstance(data.get("freeway_bound_links"), Mapping) else {}
    exits_raw = data.get("monitor_only_exit_links")
    exits = [str(value) for value in exits_raw] if isinstance(exits_raw, list) else []
    owner_links = {str(value) for value in owner}
    freeway_links = {str(value) for value in freeway_map}
    exit_links = set(exits)
    cross_duplicates = sorted(
        (owner_links & freeway_links) | (owner_links & exit_links) | (freeway_links & exit_links)
    )
    repeated_exits = sorted(value for value, count in Counter(exits).items() if count > 1)
    universe = owner_links | freeway_links | exit_links
    declared = data.get("urban_link_count")
    try:
        declared_count = int(declared)
    except (TypeError, ValueError):
        declared_count = None
    missing_count = max(0, declared_count - len(universe)) if declared_count is not None else None
    over_count = max(0, len(universe) - declared_count) if declared_count is not None else None
    tie_info = derive_assignment_ties(
        network_path,
        roles_path,
        universe,
        {str(value) for value in freeway_map.values()},
    )
    result.update(
        {
            "available": True,
            "owned_count": len(owner_links),
            "freeway_count": len(freeway_links),
            "exit_count": len(exits),
            "exit_unique_count": len(exit_links),
            "coverage_count": len(universe),
            "declared_urban_link_count": declared_count,
            "coverage_ratio": len(universe) / declared_count if declared_count else None,
            "missing_count": missing_count,
            "over_count": over_count,
            "cross_category_duplicate_count": len(cross_duplicates),
            "cross_category_duplicate_links": cross_duplicates,
            "repeated_exit_count": len(repeated_exits),
            "repeated_exit_links": repeated_exits,
            "tie_analysis": tie_info,
            "error": None,
        }
    )
    return result


def adjacency_evidence(path: Path | None) -> dict[str, Any]:
    data, error = load_json(path)
    result: dict[str, Any] = {"path": str(path) if path else None, "available": False, "error": error}
    if not isinstance(data, Mapping):
        if data is not None and error is None:
            result["error"] = "adjacency JSON root is not an object"
        return result
    adjacency = data.get("adjacency") if isinstance(data.get("adjacency"), Mapping) else {}
    internal = data.get("internal_link_members") if isinstance(data.get("internal_link_members"), Mapping) else {}
    pair_calculated = sum(len(value) for value in adjacency.values() if isinstance(value, list))
    leg_count = sum(len(value) for value in data.get("legs", {}).values() if isinstance(value, Mapping)) if isinstance(data.get("legs"), Mapping) else 0
    memberships: list[str] = []
    empty_pairs: list[str] = []
    for pair, members in internal.items():
        if not isinstance(members, list) or not members:
            empty_pairs.append(str(pair))
            continue
        memberships.extend(str(value) for value in members)
    repeated = {value: count for value, count in Counter(memberships).items() if count > 1}
    result.update(
        {
            "available": True,
            "node_count": len(adjacency),
            "declared_pair_count": data.get("pair_count"),
            "calculated_pair_count": pair_calculated,
            "declared_leg_count": data.get("leg_count"),
            "calculated_leg_count": leg_count,
            "internal_pair_count": len(internal),
            "internal_member_reference_count": len(memberships),
            "internal_member_unique_count": len(set(memberships)),
            "internal_member_reused_link_count": len(repeated),
            "internal_member_reused_links": repeated,
            "empty_internal_pair_count": len(empty_pairs),
            "empty_internal_pairs": empty_pairs,
            "direction_conflict_count": len(data.get("would_be_dropped_if_single_neighbor_per_direction", []))
            if isinstance(data.get("would_be_dropped_if_single_neighbor_per_direction"), list)
            else None,
            "error": None,
        }
    )
    return result


def _numeric_values(mapping: Any) -> list[float]:
    if not isinstance(mapping, Mapping):
        return []
    values: list[float] = []
    for value in mapping.values():
        if isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            values.append(number)
    return values


def storage_evidence(path: Path | None) -> dict[str, Any]:
    data, error = load_json(path)
    result: dict[str, Any] = {"path": str(path) if path else None, "available": False, "error": error}
    if not isinstance(data, Mapping):
        if data is not None and error is None:
            result["error"] = "storage JSON root is not an object"
        return result
    capacities = _numeric_values(data.get("urban_link_storage_veh"))
    lengths = _numeric_values(data.get("urban_link_length_km"))
    try:
        jam_density = float(data.get("jam_density_veh_km_lane"))
    except (TypeError, ValueError):
        jam_density = None
    result.update(
        {
            "available": True,
            "jam_density_veh_km_lane": jam_density,
            "jam_sample_count": data.get("jam_sample_count"),
            "storage_count": len(capacities),
            "storage_total_veh": sum(capacities),
            "storage_min_veh": min(capacities) if capacities else None,
            "storage_max_veh": max(capacities) if capacities else None,
            "nonpositive_storage_count": sum(value <= 0.0 for value in capacities),
            "length_entry_count": len(lengths),
            "length_total_km": sum(lengths),
            "ramp_capacity_count": len(_numeric_values(data.get("ramp_queue_max_veh_by_ramp"))),
            "error": None,
        }
    )
    return result


def vendor_snapshot_evidence(vendor_root: Path) -> dict[str, Any]:
    snapshot_path = vendor_root / "SNAPSHOT.md"
    result = {"root": str(vendor_root.resolve(strict=False)), "snapshot_file": file_evidence(snapshot_path), "commit": None}
    if snapshot_path.is_file():
        try:
            text = snapshot_path.read_text(encoding="utf-8-sig")
            match = re.search(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])", text, re.IGNORECASE)
            result["commit"] = match.group(0) if match else None
        except (OSError, UnicodeError) as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _source_files(root: Path) -> dict[str, Path]:
    source = root / "src"
    if not source.is_dir():
        return {}
    result: dict[str, Path] = {}
    for path in source.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        result[path.relative_to(source).as_posix()] = path
    return result


def numsim_evidence(vendor_root: Path, actual_root: Path | None, source: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "configured_source": source,
        "actual_root": str(actual_root.resolve(strict=False)) if actual_root else None,
        "exists": actual_root.is_dir() if actual_root else False,
        "git": None,
        "vendor_file_count": None,
        "actual_file_count": None,
        "matching_file_count": None,
        "mismatch_count": None,
        "mismatched_files": [],
        "missing_from_actual": [],
        "extra_in_actual": [],
        "error": None,
    }
    if actual_root is None:
        result["error"] = "NUMSIM_REPO_ROOT was not provided by argument or environment"
        return result
    if not actual_root.is_dir():
        result["error"] = "configured NUMSIM_REPO_ROOT does not exist"
        return result
    result["git"] = git_evidence(actual_root, require_exact_root=True)
    vendor_files = _source_files(vendor_root)
    actual_files = _source_files(actual_root)
    if not vendor_files or not actual_files:
        result["error"] = "vendor/src or actual/src is missing or empty"
        return result
    shared = sorted(set(vendor_files) & set(actual_files))
    mismatched: list[dict[str, Any]] = []
    for relative in shared:
        try:
            vendor_hash = sha256_file(vendor_files[relative])
            actual_hash = sha256_file(actual_files[relative])
        except OSError as exc:
            mismatched.append({"path": relative, "error": f"{type(exc).__name__}: {exc}"})
            continue
        if vendor_hash != actual_hash:
            mismatched.append({"path": relative, "vendor_sha256": vendor_hash, "actual_sha256": actual_hash})
    missing = sorted(set(vendor_files) - set(actual_files))
    extra = sorted(set(actual_files) - set(vendor_files))
    result.update(
        {
            "vendor_file_count": len(vendor_files),
            "actual_file_count": len(actual_files),
            "matching_file_count": len(shared) - len(mismatched),
            "mismatch_count": len(mismatched) + len(missing) + len(extra),
            "mismatched_files": mismatched,
            "missing_from_actual": missing,
            "extra_in_actual": extra,
        }
    )
    return result


def _find_mapping(payload: Mapping[str, Any], names: Sequence[str]) -> Mapping[str, Any] | None:
    local = payload.get("local_observation")
    sources = [local, payload] if isinstance(local, Mapping) else [payload]
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for name in names:
            value = source.get(name)
            if isinstance(value, Mapping):
                return value
    return None


def _count_close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1.0e-9, abs_tol=1.0e-6)


def _nonnegative_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0.0 else None


def inspect_state_payload(payload: Any, label: str) -> dict[str, Any]:
    result: dict[str, Any] = {"path": label, "valid_object": isinstance(payload, Mapping), "error": None}
    if not isinstance(payload, Mapping):
        result["error"] = "state JSON root is not an object"
        return result
    counts = _find_mapping(payload, ("link_counts", "link_vehicle_counts"))
    speeds = _find_mapping(payload, ("link_speeds_kph", "link_speeds"))
    stopped = _find_mapping(payload, ("link_stopped_counts", "link_stopped", "link_queue_counts"))
    count_values = _numeric_values(counts)
    speed_values = _numeric_values(speeds)
    stopped_values = _numeric_values(stopped)
    weighted_speed = None
    if isinstance(counts, Mapping) and isinstance(speeds, Mapping):
        weighted_sum = 0.0
        weight = 0.0
        for key, raw_speed in speeds.items():
            try:
                speed = float(raw_speed)
                count = float(counts.get(key, 0.0))
            except (TypeError, ValueError):
                continue
            if math.isfinite(speed) and math.isfinite(count) and count > 0.0:
                weighted_sum += speed * count
                weight += count
        if weight > 0.0:
            weighted_speed = weighted_sum / weight
    root_totals: dict[str, float] = {}
    for key in ("total_vehicles", "urban_vehicles", "boundary_vehicles", "stopped_vehicles"):
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            root_totals[key] = number
    local = payload.get("local_observation")
    schema_errors: list[str] = []
    missing_fields: list[str] = []
    if _nonnegative_number(payload.get("sim_sec")) is None:
        missing_fields.append("sim_sec")
    if not isinstance(payload.get("network_path"), str) or not str(payload.get("network_path")).strip():
        missing_fields.append("network_path")
    total_vehicles = _nonnegative_number(payload.get("total_vehicles"))
    if total_vehicles is None:
        missing_fields.append("total_vehicles")
    if not isinstance(local, Mapping):
        missing_fields.append("local_observation")
        local = {}

    schema_version = _nonnegative_number(local.get("schema_version"))
    if schema_version is None or schema_version < 2:
        missing_fields.append("local_observation.schema_version>=2")
    observation_mode = local.get("mode")
    if observation_mode != "real_world_connector_local_v2":
        missing_fields.append("local_observation.mode=real_world_connector_local_v2")
    if local.get("scan_ok") is not True:
        missing_fields.append("local_observation.scan_ok=true")
    observed_vehicle_count = _nonnegative_number(local.get("observed_vehicle_count"))
    if observed_vehicle_count is None:
        missing_fields.append("local_observation.observed_vehicle_count")
    unobservable_vehicle_count = _nonnegative_number(local.get("unobservable_vehicle_count"))
    if unobservable_vehicle_count is None:
        missing_fields.append("local_observation.unobservable_vehicle_count")
    for name, mapping in (
        ("local_observation.link_counts", counts),
        ("local_observation.link_speeds_kph", speeds),
        ("local_observation.link_stopped_counts", stopped),
    ):
        if not isinstance(mapping, Mapping):
            missing_fields.append(name)
        elif any(_nonnegative_number(value) is None for value in mapping.values()):
            schema_errors.append(f"{name} contains a non-numeric or negative value")

    link_vehicle_total = sum(count_values)
    if observed_vehicle_count is not None and not _count_close(observed_vehicle_count, link_vehicle_total):
        schema_errors.append(
            "state observed-count identity failed: observed_vehicle_count != sum(link_counts)"
        )
    if (
        total_vehicles is not None
        and observed_vehicle_count is not None
        and unobservable_vehicle_count is not None
        and not _count_close(total_vehicles, observed_vehicle_count + unobservable_vehicle_count)
    ):
        schema_errors.append(
            "state total identity failed: total_vehicles != observed_vehicle_count + unobservable_vehicle_count"
        )
    if missing_fields:
        schema_errors.insert(0, "missing or invalid latest-state fields: " + ", ".join(missing_fields))

    result.update(
        {
            "sim_sec": payload.get("sim_sec"),
            "has_link_counts": counts is not None,
            "link_count_entries": len(count_values),
            "link_vehicle_total": link_vehicle_total,
            "has_link_speeds": speeds is not None,
            "link_speed_entries": len(speed_values),
            "link_speed_mean_kph": statistics.fmean(speed_values) if speed_values else None,
            "link_speed_count_weighted_mean_kph": weighted_speed,
            "has_link_stopped": stopped is not None,
            "link_stopped_entries": len(stopped_values),
            "link_stopped_total": sum(stopped_values),
            "root_vehicle_totals": root_totals,
            "network_path": payload.get("network_path"),
            "schema_version": schema_version,
            "observation_mode": observation_mode,
            "observed_vehicle_count": observed_vehicle_count,
            "unobservable_vehicle_count": unobservable_vehicle_count,
            "missing_latest_schema_fields": missing_fields,
            "schema_errors": schema_errors,
            "schema_status": STATUS_FAIL if schema_errors else STATUS_PASS,
        }
    )
    return result


def state_evidence(paths: Sequence[Path]) -> dict[str, Any]:
    result: dict[str, Any] = {"configured_count": len(paths), "files": [], "error_count": 0}
    for path in paths:
        payload, error = load_json(path)
        if error:
            record = {"path": str(path.resolve(strict=False)), "valid_object": False, "error": error}
        else:
            record = inspect_state_payload(payload, str(path.resolve(strict=False)))
        result["files"].append(record)
        if record.get("error"):
            result["error_count"] += 1
    valid = [record for record in result["files"] if record.get("valid_object")]
    result.update(
        {
            "valid_count": len(valid),
            "link_vehicle_total_sum": sum(float(record.get("link_vehicle_total", 0.0)) for record in valid),
            "link_stopped_total_sum": sum(float(record.get("link_stopped_total", 0.0)) for record in valid),
            "missing_link_counts_count": sum(not record.get("has_link_counts", False) for record in valid),
            "missing_link_speeds_count": sum(not record.get("has_link_speeds", False) for record in valid),
            "missing_link_stopped_count": sum(not record.get("has_link_stopped", False) for record in valid),
            "latest_schema_fail_count": sum(record.get("schema_status") != STATUS_PASS for record in valid),
        }
    )
    return result


def _flatten_numeric(mapping: Mapping[str, Any], prefix: str = "") -> dict[str, float]:
    result: dict[str, float] = {}
    for key, value in mapping.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            result.update(_flatten_numeric(value, full_key))
        elif not isinstance(value, bool):
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(number):
                result[full_key] = number
    return result


def numeric_stats(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "mean": None, "median": None, "p95": None, "max": None, "sum": 0.0}
    ordered = sorted(values)
    p95 = ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]
    return {
        "count": len(ordered),
        "min": min(ordered),
        "mean": statistics.fmean(ordered),
        "median": statistics.median(ordered),
        "p95": p95,
        "max": max(ordered),
        "sum": sum(ordered),
    }


PROJECTION_REQUIRED_FIELDS = (
    "total_vehicle_count_veh",
    "input_link_vehicle_count_veh",
    "represented_vehicle_count_veh",
    "exit_excluded_vehicle_count_veh",
    "unobservable_vehicle_count_veh",
    "unrepresented_vehicle_count_veh",
    "mass_balance_error_veh",
    "storage_capacity_clipped_veh",
)


def projection_contract_record(
    projection: Mapping[str, Any],
    source: str,
    state_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    values: dict[str, float] = {}
    missing: list[str] = []
    for field in PROJECTION_REQUIRED_FIELDS:
        raw = projection.get(field)
        if isinstance(raw, bool):
            missing.append(field)
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            missing.append(field)
            continue
        if not math.isfinite(value) or value < 0.0:
            missing.append(field)
            continue
        values[field] = value

    explanation = projection.get("storage_capacity_clipping_explanation")
    if not isinstance(explanation, str) or not explanation.strip():
        explanation = projection.get("clipping_explanation")
    explicitly_explained = bool(
        isinstance(explanation, str) and explanation.strip()
    ) or projection.get("storage_capacity_clipping_explained") is True

    threshold = None
    residual_pass = False
    clipping_pass = False
    reasons: list[str] = []
    if missing:
        reasons.append("missing or invalid required fields: " + ", ".join(missing))
    else:
        represented = values["represented_vehicle_count_veh"]
        exit_excluded = values["exit_excluded_vehicle_count_veh"]
        unobservable = values["unobservable_vehicle_count_veh"]
        unrepresented = values["unrepresented_vehicle_count_veh"]
        mass_error = values["mass_balance_error_veh"]
        input_expected = represented + exit_excluded + unrepresented
        total_expected = represented + exit_excluded + unobservable + mass_error
        input_balance_error = values["input_link_vehicle_count_veh"] - input_expected
        total_balance_error = values["total_vehicle_count_veh"] - total_expected
        residual_consistency_error = mass_error - unrepresented
        if not _count_close(input_balance_error, 0.0):
            reasons.append(
                "input mass identity failed: input != represented + exit + unrepresented"
            )
        if not _count_close(total_balance_error, 0.0):
            reasons.append(
                "total mass identity failed: total != represented + exit + unobservable + residual"
            )
        if not _count_close(residual_consistency_error, 0.0):
            reasons.append("residual identity failed: mass_balance_error != unrepresented")

        explicit_residual = projection.get("residual_vehicle_count_veh")
        if explicit_residual is not None:
            residual_value = _nonnegative_number(explicit_residual)
            if residual_value is None or not _count_close(residual_value, mass_error):
                reasons.append("explicit residual_vehicle_count_veh does not match mass_balance_error_veh")

        if state_record is not None:
            state_total = _nonnegative_number(
                (state_record.get("root_vehicle_totals") or {}).get("total_vehicles")
            )
            state_input = _nonnegative_number(state_record.get("link_vehicle_total"))
            state_unobservable = _nonnegative_number(state_record.get("unobservable_vehicle_count"))
            if state_record.get("schema_status") != STATUS_PASS:
                reasons.append("paired state does not satisfy the latest state schema")
            if state_total is None or not _count_close(values["total_vehicle_count_veh"], state_total):
                reasons.append("projection total does not match paired state total_vehicles")
            if state_input is None or not _count_close(values["input_link_vehicle_count_veh"], state_input):
                reasons.append("projection input does not match paired state sum(link_counts)")
            if state_unobservable is None or not _count_close(unobservable, state_unobservable):
                reasons.append("projection unobservable count does not match paired state")

        threshold = max(5.0, 0.03 * values["input_link_vehicle_count_veh"])
        residual_pass = values["unrepresented_vehicle_count_veh"] <= threshold
        clipping = values["storage_capacity_clipped_veh"]
        clipping_pass = clipping == 0.0 or explicitly_explained
        if not residual_pass:
            reasons.append(
                f"unrepresented vehicles {values['unrepresented_vehicle_count_veh']:.6g} "
                f"exceed threshold {threshold:.6g}"
            )
        if not clipping_pass:
            reasons.append(f"storage clipping {clipping:.6g} veh is not explicitly explained")
    input_balance_error = None
    total_balance_error = None
    residual_consistency_error = None
    if not missing:
        input_balance_error = values["input_link_vehicle_count_veh"] - (
            values["represented_vehicle_count_veh"]
            + values["exit_excluded_vehicle_count_veh"]
            + values["unrepresented_vehicle_count_veh"]
        )
        total_balance_error = values["total_vehicle_count_veh"] - (
            values["represented_vehicle_count_veh"]
            + values["exit_excluded_vehicle_count_veh"]
            + values["unobservable_vehicle_count_veh"]
            + values["mass_balance_error_veh"]
        )
        residual_consistency_error = (
            values["mass_balance_error_veh"] - values["unrepresented_vehicle_count_veh"]
        )
    return {
        "source": source,
        "required_fields": values,
        "missing_required_fields": missing,
        "unrepresented_threshold_veh": threshold,
        "unrepresented_pass": residual_pass,
        "storage_clipping_explained": explicitly_explained,
        "storage_clipping_pass": clipping_pass,
        "input_mass_balance_error_veh": input_balance_error,
        "total_mass_balance_error_veh": total_balance_error,
        "residual_consistency_error_veh": residual_consistency_error,
        "status": STATUS_PASS if not reasons else STATUS_FAIL,
        "reasons": reasons,
    }


CORE_RUNTIME_MODULES = (
    "src.controllers.stackelberg_mpc",
    "src.models.demand",
    "src.models.state",
    "src.models.urban_queue_model",
)


def _numsim_python_tree_sha256(repo_root: Path) -> str:
    source_root = repo_root / "src"
    if not source_root.is_dir():
        return ""
    digest = hashlib.sha256()
    for source in sorted(
        source_root.rglob("*.py"),
        key=lambda item: item.relative_to(source_root).as_posix(),
    ):
        digest.update(source.relative_to(source_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _resolved_provenance_path(value: Any, provenance: Mapping[str, Any], source: Path) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if not path.is_absolute():
        workspace = provenance.get("workspace_root")
        base = Path(workspace) if isinstance(workspace, str) and workspace.strip() else source.parent
        path = base / path
    return path.resolve(strict=False)


def _runtime_provenance_fingerprint(provenance: Mapping[str, Any]) -> str:
    inputs = provenance.get("inputs") if isinstance(provenance.get("inputs"), Mapping) else {}
    stable_inputs = {
        str(name): value
        for name, value in inputs.items()
        if str(name) != "state_json"
    }
    stable = {
        key: provenance.get(key)
        for key in (
            "workspace_root",
            "workspace_git_commit",
            "numsim_repo_root",
            "numsim_git_commit",
            "numsim_snapshot_commit",
            "numsim_src_sha256",
            "imported_modules",
            "signal_program_sha256",
        )
    }
    stable["inputs"] = stable_inputs
    encoded = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def runtime_provenance_contract_record(
    provenance: Any,
    source: Path,
    state_path: Path | None,
    state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(provenance, Mapping):
        return {
            "source": str(source.resolve(strict=False)),
            "status": STATUS_FAIL,
            "reasons": ["missing action run_provenance"],
            "provenance_fingerprint": None,
        }

    numsim_root = _resolved_provenance_path(provenance.get("numsim_repo_root"), provenance, source)
    expected_tree_hash = provenance.get("numsim_src_sha256")
    actual_tree_hash = _numsim_python_tree_sha256(numsim_root) if numsim_root else ""
    if numsim_root is None or not numsim_root.is_dir():
        reasons.append("NUMSIM_REPO_ROOT is missing or is not a directory")
    if not isinstance(expected_tree_hash, str) or len(expected_tree_hash) != 64:
        reasons.append("missing or invalid numsim_src_sha256")
    elif actual_tree_hash != expected_tree_hash.lower():
        reasons.append("NumSim source tree hash mismatch")

    imported = provenance.get("imported_modules")
    if not isinstance(imported, Mapping):
        imported = {}
    for module_name in CORE_RUNTIME_MODULES:
        module = imported.get(module_name)
        if not isinstance(module, Mapping):
            reasons.append(f"missing imported module evidence: {module_name}")
            continue
        module_path = _resolved_provenance_path(module.get("path"), provenance, source)
        stored_hash = module.get("sha256")
        if module_path is None or not module_path.is_file():
            reasons.append(f"imported module path is unavailable: {module_name}")
            continue
        if numsim_root is None or not module_path.is_relative_to(numsim_root):
            reasons.append(f"imported module is outside NUMSIM_REPO_ROOT: {module_name}")
        if not isinstance(stored_hash, str) or sha256_file(module_path) != stored_hash.lower():
            reasons.append(f"imported module hash mismatch: {module_name}")

    inputs = provenance.get("inputs")
    if not isinstance(inputs, Mapping):
        inputs = {}
    for required_input in ("state_json", "network_inpx"):
        if not isinstance(inputs.get(required_input), Mapping):
            reasons.append(f"missing provenance input: {required_input}")
    resolved_inputs: dict[str, Path] = {}
    for name, item in inputs.items():
        if not isinstance(item, Mapping):
            reasons.append(f"invalid provenance input evidence: {name}")
            continue
        input_path = _resolved_provenance_path(item.get("path"), provenance, source)
        stored_hash = item.get("sha256")
        if input_path is None or not input_path.is_file():
            reasons.append(f"provenance input path is unavailable: {name}")
            continue
        resolved_inputs[str(name)] = input_path
        if not isinstance(stored_hash, str) or sha256_file(input_path) != stored_hash.lower():
            reasons.append(f"provenance input hash mismatch: {name}")

    recorded_state = resolved_inputs.get("state_json")
    if state_path is None:
        reasons.append("action has no paired state JSON")
    elif recorded_state is not None and recorded_state != state_path.resolve(strict=False):
        state_evidence = inputs.get("state_json") if isinstance(inputs.get("state_json"), Mapping) else {}
        recorded_hash = str(state_evidence.get("sha256", "")).lower()
        if not recorded_hash or sha256_file(state_path) != recorded_hash:
            reasons.append("provenance state_json path differs and paired state hash does not match")

    network_path = resolved_inputs.get("network_inpx")
    if network_path is not None and state_payload is not None:
        state_network = _resolved_provenance_path(state_payload.get("network_path"), provenance, state_path or source)
        if state_network != network_path:
            reasons.append("paired state network_path does not match provenance network_inpx")

    stored_signals = provenance.get("signal_program_sha256")
    if not isinstance(stored_signals, Mapping) or not stored_signals:
        reasons.append("missing signal_program_sha256 evidence")
        stored_signals = {}
    actual_signals = (
        {
            signal.name: sha256_file(signal)
            for signal in sorted(network_path.parent.glob("*.sig"), key=lambda item: item.name)
        }
        if network_path is not None
        else {}
    )
    normalized_stored_signals = {
        str(name): str(value).lower() for name, value in stored_signals.items()
    }
    if normalized_stored_signals != actual_signals:
        reasons.append("signal program hashes do not match the network directory")

    return {
        "source": str(source.resolve(strict=False)),
        "run_id": provenance.get("run_id"),
        "numsim_repo_root": str(numsim_root) if numsim_root else None,
        "numsim_src_sha256": expected_tree_hash,
        "actual_numsim_src_sha256": actual_tree_hash,
        "imported_module_count": len(imported),
        "signal_program_count": len(normalized_stored_signals),
        "provenance_fingerprint": _runtime_provenance_fingerprint(provenance),
        "status": STATUS_FAIL if reasons else STATUS_PASS,
        "reasons": reasons,
    }


def _payload_run_id(payload: Mapping[str, Any], file_path: Path, root: Path) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    provenance = payload.get("run_provenance") if isinstance(payload.get("run_provenance"), Mapping) else {}
    for source in (payload, metadata, provenance):
        value = source.get("run_id")
        if isinstance(value, str) and value.strip():
            return value.strip()
    try:
        relative_parent = file_path.resolve().parent.relative_to(root.resolve()).as_posix()
    except ValueError:
        relative_parent = str(file_path.resolve().parent)
    return relative_parent or "."


def _paired_state_path(action_path: Path) -> Path | None:
    suffix = action_path.name.removeprefix("action_")
    for prefix in ("state_", "anchor_"):
        candidate = action_path.with_name(prefix + suffix)
        if candidate.is_file():
            return candidate
    return None


def action_directory_evidence(path: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path.resolve(strict=False)) if path else None,
        "exists": path.is_dir() if path else False,
        "state_file_count": 0,
        "action_file_count": 0,
        "state_files": [],
        "action_files": [],
        "invalid_state_json_count": 0,
        "invalid_action_json_count": 0,
        "decision_wall_sec": numeric_stats([]),
        "projection_diagnostics_record_count": 0,
        "projection_diagnostics": {},
        "projection_contract": {
            "record_count": 0,
            "pass_count": 0,
            "fail_count": 0,
            "missing_required_field_record_count": 0,
            "records": [],
        },
        "runtime_provenance_contract": {
            "record_count": 0,
            "pass_count": 0,
            "fail_count": 0,
            "records": [],
        },
        "run_contract": {
            "run_count": 0,
            "pass_count": 0,
            "fail_count": 0,
            "mixed_provenance_run_count": 0,
            "runs": [],
        },
        "signal_readback": signal_readback_evidence(path),
        "errors": [],
    }
    if path is None or not path.is_dir():
        return result
    state_files = sorted((*path.rglob("state_*.json"), *path.rglob("anchor_*.json")))
    action_files = sorted(path.rglob("action_*.json"))
    result["state_file_count"] = len(state_files)
    result["action_file_count"] = len(action_files)
    result["state_files"] = [str(item.resolve(strict=False)) for item in state_files]
    result["action_files"] = [str(item.resolve(strict=False)) for item in action_files]
    state_payloads: dict[Path, Mapping[str, Any]] = {}
    state_records: dict[Path, dict[str, Any]] = {}
    runs: dict[str, dict[str, Any]] = {}
    for state_path in state_files:
        payload, error = load_json(state_path)
        if error:
            result["invalid_state_json_count"] += 1
            result["errors"].append({"path": str(state_path), "error": error})
            continue
        if not isinstance(payload, Mapping):
            result["invalid_state_json_count"] += 1
            result["errors"].append({"path": str(state_path), "error": "JSON root is not an object"})
            continue
        resolved_state = state_path.resolve(strict=False)
        state_payloads[resolved_state] = payload
        state_record = inspect_state_payload(payload, str(resolved_state))
        state_records[resolved_state] = state_record
        run_id = _payload_run_id(payload, state_path, path)
        run = runs.setdefault(
            run_id,
            {
                "run_id": run_id,
                "state_files": [],
                "action_files": [],
                "projection_records": [],
                "provenance_records": [],
                "reasons": [],
            },
        )
        run["state_files"].append(str(resolved_state))
        if state_record.get("schema_status") != STATUS_PASS:
            run["reasons"].append(f"latest state schema failed: {state_path.name}")
    wall_times: list[float] = []
    diagnostics: dict[str, list[float]] = defaultdict(list)
    projection_records: list[dict[str, Any]] = []
    provenance_records: list[dict[str, Any]] = []
    for action_path in action_files:
        payload, error = load_json(action_path)
        if error or not isinstance(payload, Mapping):
            result["invalid_action_json_count"] += 1
            result["errors"].append({"path": str(action_path), "error": error or "JSON root is not an object"})
            continue
        run_id = _payload_run_id(payload, action_path, path)
        run = runs.setdefault(
            run_id,
            {
                "run_id": run_id,
                "state_files": [],
                "action_files": [],
                "projection_records": [],
                "provenance_records": [],
                "reasons": [],
            },
        )
        run["action_files"].append(str(action_path.resolve(strict=False)))
        paired_state_path = _paired_state_path(action_path)
        paired_state_resolved = paired_state_path.resolve(strict=False) if paired_state_path else None
        paired_state_payload = state_payloads.get(paired_state_resolved) if paired_state_resolved else None
        paired_state_record = state_records.get(paired_state_resolved) if paired_state_resolved else None
        if paired_state_path is None:
            run["reasons"].append(f"missing paired state for {action_path.name}")
        elif paired_state_payload is not None:
            state_run_id = _payload_run_id(paired_state_payload, paired_state_path, path)
            if state_run_id != run_id:
                run["reasons"].append(
                    f"run_id mismatch for {action_path.name}: action={run_id} state={state_run_id}"
                )
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
        raw_wall = metadata.get("decision_wall_sec", payload.get("decision_wall_sec"))
        try:
            wall = float(raw_wall)
        except (TypeError, ValueError):
            wall = None
        if wall is not None and math.isfinite(wall) and wall >= 0.0:
            wall_times.append(wall)
        projection = payload.get("projection_diagnostics")
        if not isinstance(projection, Mapping):
            projection = metadata.get("projection_diagnostics")
        if isinstance(projection, Mapping):
            result["projection_diagnostics_record_count"] += 1
            projection_record = projection_contract_record(
                projection,
                str(action_path.resolve(strict=False)),
                paired_state_record,
            )
            for key, value in _flatten_numeric(projection).items():
                diagnostics[key].append(value)
        else:
            projection_record = projection_contract_record({}, str(action_path.resolve(strict=False)), paired_state_record)
        projection_records.append(projection_record)
        run["projection_records"].append(projection_record)

        provenance = payload.get("run_provenance")
        if not isinstance(provenance, Mapping):
            provenance = metadata.get("run_provenance")
        provenance_record = runtime_provenance_contract_record(
            provenance,
            action_path,
            paired_state_path,
            paired_state_payload,
        )
        provenance_records.append(provenance_record)
        run["provenance_records"].append(provenance_record)
    result["decision_wall_sec"] = numeric_stats(wall_times)
    result["projection_diagnostics"] = {key: numeric_stats(values) for key, values in sorted(diagnostics.items())}
    result["projection_contract"] = {
        "record_count": len(projection_records),
        "pass_count": sum(record["status"] == STATUS_PASS for record in projection_records),
        "fail_count": sum(record["status"] == STATUS_FAIL for record in projection_records),
        "missing_required_field_record_count": sum(bool(record["missing_required_fields"]) for record in projection_records),
        "records": projection_records,
    }
    result["runtime_provenance_contract"] = {
        "record_count": len(provenance_records),
        "pass_count": sum(record["status"] == STATUS_PASS for record in provenance_records),
        "fail_count": sum(record["status"] == STATUS_FAIL for record in provenance_records),
        "records": provenance_records,
    }
    run_records: list[dict[str, Any]] = []
    for run_id in sorted(runs):
        run = runs[run_id]
        fingerprints = {
            record.get("provenance_fingerprint")
            for record in run["provenance_records"]
            if record.get("provenance_fingerprint")
        }
        mixed = len(fingerprints) > 1
        reasons = list(run["reasons"])
        if mixed:
            reasons.append("multiple runtime provenance fingerprints were mixed under one run_id")
        if any(record["status"] == STATUS_FAIL for record in run["projection_records"]):
            reasons.append("one or more projection contracts failed")
        if any(record["status"] == STATUS_FAIL for record in run["provenance_records"]):
            reasons.append("one or more runtime provenance contracts failed")
        run_records.append(
            {
                "run_id": run_id,
                "state_file_count": len(run["state_files"]),
                "action_file_count": len(run["action_files"]),
                "provenance_fingerprint_count": len(fingerprints),
                "mixed_provenance": mixed,
                "status": STATUS_FAIL if reasons else STATUS_PASS,
                "reasons": reasons,
                "state_files": run["state_files"],
                "action_files": run["action_files"],
            }
        )
    result["run_contract"] = {
        "run_count": len(run_records),
        "pass_count": sum(record["status"] == STATUS_PASS for record in run_records),
        "fail_count": sum(record["status"] == STATUS_FAIL for record in run_records),
        "mixed_provenance_run_count": sum(record["mixed_provenance"] for record in run_records),
        "runs": run_records,
    }
    return result


SIGNAL_READBACK_COLUMNS = (
    "sim_sec",
    "sc_no",
    "sg_no",
    "requested_state",
    "readback_state",
    "ok",
    "stage",
)


def signal_readback_evidence(path: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "file_count": 0,
        "row_count": 0,
        "ok_count": 0,
        "mismatch_count": 0,
        "ok_not_one_count": 0,
        "malformed_row_count": 0,
        "malformed_file_count": 0,
        "empty_file_count": 0,
        "immediate_count": 0,
        "post_step_count": 0,
        "unpaired_post_step_count": 0,
        "files": [],
        "problem_rows": [],
    }
    if path is None or not path.is_dir():
        return result

    readback_paths = sorted(path.rglob("signal_readback.csv"))
    result["file_count"] = len(readback_paths)
    for readback_path in readback_paths:
        file_result: dict[str, Any] = {
            "path": str(readback_path.resolve(strict=False)),
            "row_count": 0,
            "ok_count": 0,
            "mismatch_count": 0,
            "ok_not_one_count": 0,
            "malformed_row_count": 0,
            "malformed": False,
            "error": None,
            "immediate_count": 0,
            "post_step_count": 0,
            "unpaired_post_step_count": 0,
        }
        try:
            with readback_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, strict=True)
                fieldnames = reader.fieldnames or []
                missing_columns = [column for column in SIGNAL_READBACK_COLUMNS if column not in fieldnames]
                if missing_columns:
                    file_result["malformed"] = True
                    file_result["error"] = "missing required columns: " + ", ".join(missing_columns)
                else:
                    immediate_pairs: set[tuple[str, str]] = set()
                    for row in reader:
                        file_result["row_count"] += 1
                        result["row_count"] += 1
                        row_number = reader.line_num
                        values = {column: (row.get(column) or "").strip() for column in SIGNAL_READBACK_COLUMNS}
                        errors = [f"empty {column}" for column, value in values.items() if not value]
                        if None in row:
                            errors.append("unexpected extra columns")
                        if values["sim_sec"]:
                            try:
                                sim_sec = float(values["sim_sec"])
                                if not math.isfinite(sim_sec) or sim_sec < 0.0:
                                    raise ValueError
                            except ValueError:
                                errors.append("sim_sec is not a non-negative finite number")
                        for column in ("sc_no", "sg_no"):
                            if values[column]:
                                try:
                                    if int(values[column]) <= 0:
                                        raise ValueError
                                except ValueError:
                                    errors.append(f"{column} is not a positive integer")
                        ok_value: int | None = None
                        if values["ok"]:
                            try:
                                ok_value = int(values["ok"])
                            except ValueError:
                                errors.append("ok is not an integer")
                            else:
                                if ok_value not in (0, 1):
                                    errors.append("ok is not 0 or 1")
                        stage = values["stage"]
                        pair = (values["sc_no"], values["sg_no"])
                        if stage == "immediate":
                            file_result["immediate_count"] += 1
                            result["immediate_count"] += 1
                            immediate_pairs.add(pair)
                        elif stage == "post_step":
                            file_result["post_step_count"] += 1
                            result["post_step_count"] += 1
                            if pair not in immediate_pairs:
                                file_result["unpaired_post_step_count"] += 1
                                result["unpaired_post_step_count"] += 1
                        else:
                            errors.append("stage is not immediate or post_step")

                        mismatch = bool(
                            values["requested_state"]
                            and values["readback_state"]
                            and values["requested_state"] != values["readback_state"]
                        )
                        if errors:
                            file_result["malformed_row_count"] += 1
                            result["malformed_row_count"] += 1
                        else:
                            if ok_value == 1:
                                file_result["ok_count"] += 1
                                result["ok_count"] += 1
                            else:
                                file_result["ok_not_one_count"] += 1
                                result["ok_not_one_count"] += 1
                            if mismatch:
                                file_result["mismatch_count"] += 1
                                result["mismatch_count"] += 1

                        if errors or mismatch or ok_value != 1:
                            result["problem_rows"].append(
                                {
                                    "path": file_result["path"],
                                    "row_number": row_number,
                                    "sim_sec": values["sim_sec"],
                                    "sc_no": values["sc_no"],
                                    "sg_no": values["sg_no"],
                                    "requested_state": values["requested_state"],
                                    "readback_state": values["readback_state"],
                                    "ok": values["ok"],
                                    "mismatch": mismatch,
                                    "errors": errors,
                                }
                            )
        except (OSError, UnicodeError, csv.Error) as exc:
            file_result["malformed"] = True
            file_result["error"] = f"{type(exc).__name__}: {exc}"

        if file_result["malformed"]:
            result["malformed_file_count"] += 1
        if not file_result["malformed"] and file_result["row_count"] == 0:
            result["empty_file_count"] += 1
        result["files"].append(file_result)
    return result


def vissim_error_evidence(source: Path | None, copy_target: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source": str(source.resolve(strict=False)) if source else None,
        "exists": source.is_file() if source else False,
        "copy_requested": copy_target is not None,
        "copy_target": str(copy_target.resolve(strict=False)) if copy_target else None,
        "copied_to": None,
        "line_count": None,
        "nonempty_line_count": None,
        "error_line_count": None,
        "warning_line_count": None,
        "notable_lines": [],
        "error": None,
    }
    if source is None or not source.is_file():
        return result
    try:
        text = source.read_text(encoding="utf-8-sig", errors="replace")
        lines = text.splitlines()
        error_lines = [line.strip() for line in lines if re.search(r"\b(error|fatal)\b|오류|fehler", line, re.IGNORECASE)]
        warning_lines = [line.strip() for line in lines if re.search(r"\bwarn(?:ing)?\b|경고|warnung", line, re.IGNORECASE)]
        result.update(
            {
                "line_count": len(lines),
                "nonempty_line_count": sum(bool(line.strip()) for line in lines),
                "error_line_count": len(error_lines),
                "warning_line_count": len(warning_lines),
                "notable_lines": (error_lines + warning_lines)[:50],
            }
        )
        if copy_target is not None:
            destination = copy_target / source.name if copy_target.exists() and copy_target.is_dir() else copy_target
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            result["copied_to"] = str(destination.resolve())
    except (OSError, UnicodeError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def signal_controller_scope_gate(network: Mapping[str, Any]) -> dict[str, Any]:
    if not network.get("available"):
        return gate(STATUS_NE, "network XML is unavailable")
    if network.get("urban_eligible_error"):
        return gate(STATUS_NE, str(network["urban_eligible_error"]))
    raw_count = network.get("raw_active_signal_controller_count")
    urban_count = network.get("urban_eligible_signal_controller_count")
    model_count = network.get("model_signal_controller_count")
    excluded_count = network.get("model_excluded_signal_controller_count")
    auxiliary_count = network.get("auxiliary_active_signal_controller_count")
    eligible_not_active = network.get("urban_eligible_not_raw_active_count")
    if not all(isinstance(value, int) for value in (raw_count, urban_count, model_count, excluded_count, auxiliary_count)):
        return gate(STATUS_FAIL, "signal-controller scope counts are incomplete")
    if eligible_not_active:
        return gate(
            STATUS_FAIL,
            "roles CSV marks controllers eligible that are not raw active in XML",
            controller_ids=network.get("urban_eligible_not_raw_active_ids"),
        )
    if raw_count != urban_count + auxiliary_count or urban_count != model_count + excluded_count:
        return gate(STATUS_FAIL, "raw, urban-eligible, and model controller scopes do not form consistent partitions")
    excluded = network.get("model_excluded_signal_controllers", [])
    return gate(
        STATUS_PASS,
        f"raw XML active {raw_count} / urban eligible {urban_count} / model {model_count}; "
        f"auxiliary active {auxiliary_count}, model excluded {excluded_count}",
        raw_active=raw_count,
        urban_eligible=urban_count,
        model=model_count,
        auxiliary_active=auxiliary_count,
        artificial_ramp_meter_active=network.get("artificial_ramp_meter_active_signal_controller_count"),
        model_excluded=excluded,
    )


def state_observation_contract_gate(states: Mapping[str, Any]) -> dict[str, Any]:
    if not states.get("configured_count"):
        return gate(STATUS_NE, "no state JSON was supplied or discovered under --action-dir")
    if states.get("error_count") or not states.get("valid_count"):
        return gate(STATUS_FAIL, "one or more supplied or discovered state JSON files could not be read")
    if states.get("missing_link_counts_count") or states.get("missing_link_speeds_count") or states.get("missing_link_stopped_count"):
        return gate(
            STATUS_FAIL,
            "state observation is missing counts, speeds, or stopped counts",
            missing_counts=states.get("missing_link_counts_count"),
            missing_speeds=states.get("missing_link_speeds_count"),
            missing_stopped=states.get("missing_link_stopped_count"),
        )
    if states.get("latest_schema_fail_count"):
        return gate(
            STATUS_FAIL,
            "one or more states violate the latest state schema or state-level mass identity",
            fail_count=states.get("latest_schema_fail_count"),
        )
    return gate(
        STATUS_PASS,
        "all supplied and action-dir-discovered states contain link counts, speeds, and stopped counts",
        explicit_count=states.get("explicit_configured_count", 0),
        action_dir_discovered_count=states.get("action_dir_discovered_count", 0),
    )


def projection_diagnostics_gate(actions: Mapping[str, Any]) -> dict[str, Any]:
    contract = actions.get("projection_contract", {})
    record_count = contract.get("record_count", 0)
    if not record_count:
        return gate(STATUS_NE, "no projection_diagnostics records were found")
    if contract.get("missing_required_field_record_count"):
        return gate(
            STATUS_FAIL,
            "projection diagnostics are missing required count or clipping fields",
            record_count=record_count,
            missing_required_field_record_count=contract.get("missing_required_field_record_count"),
        )
    if contract.get("fail_count"):
        return gate(
            STATUS_FAIL,
            "one or more projection records violate mass identities, residual limits, or clipping rules",
            record_count=record_count,
            fail_count=contract.get("fail_count"),
        )
    return gate(
        STATUS_PASS,
        "every projection record satisfies both mass identities, residual consistency, the unrepresented limit, and clipping rules",
        record_count=record_count,
        pass_count=contract.get("pass_count"),
    )


def runtime_provenance_gate(actions: Mapping[str, Any]) -> dict[str, Any]:
    contract = actions.get("runtime_provenance_contract", {})
    run_contract = actions.get("run_contract", {})
    action_count = int(actions.get("action_file_count", 0) or 0)
    record_count = int(contract.get("record_count", 0) or 0)
    if not action_count:
        return gate(STATUS_NE, "no action JSON was available for runtime provenance validation")
    if record_count != action_count:
        return gate(
            STATUS_FAIL,
            "not every action has a runtime provenance contract record",
            action_count=action_count,
            record_count=record_count,
        )
    if contract.get("fail_count"):
        return gate(
            STATUS_FAIL,
            "one or more actions have missing, stale, external, or hash-mismatched runtime provenance",
            record_count=record_count,
            fail_count=contract.get("fail_count"),
        )
    if run_contract.get("mixed_provenance_run_count"):
        return gate(
            STATUS_FAIL,
            "multiple provenance fingerprints were mixed under the same run_id",
            run_count=run_contract.get("run_count"),
            mixed_run_count=run_contract.get("mixed_provenance_run_count"),
        )
    return gate(
        STATUS_PASS,
        "every action is paired to a state and each run_id has one verified runtime provenance fingerprint",
        action_count=action_count,
        run_count=run_contract.get("run_count"),
    )


def signal_com_readback_gate(actions: Mapping[str, Any]) -> dict[str, Any]:
    trace = actions.get("signal_readback", {})
    file_count = int(trace.get("file_count", 0) or 0)
    row_count = int(trace.get("row_count", 0) or 0)
    evidence = {
        "file_count": file_count,
        "row_count": row_count,
        "ok_count": int(trace.get("ok_count", 0) or 0),
        "mismatch_count": int(trace.get("mismatch_count", 0) or 0),
        "ok_not_one_count": int(trace.get("ok_not_one_count", 0) or 0),
        "malformed_row_count": int(trace.get("malformed_row_count", 0) or 0),
        "malformed_file_count": int(trace.get("malformed_file_count", 0) or 0),
        "empty_file_count": int(trace.get("empty_file_count", 0) or 0),
        "immediate_count": int(trace.get("immediate_count", 0) or 0),
        "post_step_count": int(trace.get("post_step_count", 0) or 0),
        "unpaired_post_step_count": int(trace.get("unpaired_post_step_count", 0) or 0),
    }
    if not file_count:
        return gate(STATUS_NE, "no signal_readback.csv files were found under --action-dir", **evidence)
    if evidence["malformed_file_count"] or evidence["malformed_row_count"]:
        return gate(STATUS_FAIL, "signal readback trace contains malformed or empty evidence", **evidence)
    if not row_count:
        return gate(STATUS_NE, "all signal readback files are empty", **evidence)
    if not evidence["immediate_count"] or not evidence["post_step_count"]:
        return gate(STATUS_FAIL, "signal readback lacks either immediate or post-step persistence evidence", **evidence)
    if evidence["unpaired_post_step_count"]:
        return gate(STATUS_FAIL, "post-step signal readback has no preceding immediate write for one or more SGs", **evidence)
    if evidence["mismatch_count"] or evidence["ok_not_one_count"]:
        return gate(STATUS_FAIL, "signal readback trace contains a state mismatch or ok != 1", **evidence)
    if evidence["ok_count"] != row_count:
        return gate(STATUS_FAIL, "not every signal readback row is confirmed ok", **evidence)
    return gate(STATUS_PASS, "every signal readback row has matching requested/readback states and ok=1", **evidence)


def build_gates(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    gates: dict[str, dict[str, Any]] = {}
    inputs = manifest["inputs"]
    missing = [name for name, item in inputs["primary"].items() if not item.get("is_file")]
    if missing:
        gates["input_provenance"] = gate(STATUS_NE, "one or more configured input files are unavailable", missing=missing)
    else:
        gates["input_provenance"] = gate(STATUS_PASS, "all configured primary inputs were hashed")

    network = manifest["network"]
    if not network.get("available"):
        status = STATUS_NE if "not found" in str(network.get("error", "")) else STATUS_FAIL
        gates["network_xml"] = gate(status, str(network.get("error") or "network evidence unavailable"))
    elif network.get("malformed_signal_head_reference_count", 0):
        gates["network_xml"] = gate(STATUS_FAIL, "malformed signal-head controller references found")
    else:
        gates["network_xml"] = gate(STATUS_PASS, "network XML parsed and signal-head references are well formed")
    gates["signal_controller_scope"] = signal_controller_scope_gate(network)

    assignment = manifest["link_assignment"]
    if not assignment.get("available"):
        status = STATUS_NE if assignment.get("error") == "file not found" else STATUS_FAIL
        gates["link_partition"] = gate(status, str(assignment.get("error") or "assignment evidence unavailable"))
    else:
        duplicate_count = assignment.get("cross_category_duplicate_count", 0) + assignment.get("repeated_exit_count", 0)
        complete = assignment.get("missing_count") == 0 and assignment.get("over_count") == 0
        if duplicate_count or not complete:
            gates["link_partition"] = gate(
                STATUS_FAIL,
                "link assignment is not a complete disjoint partition",
                duplicate_count=duplicate_count,
                missing_count=assignment.get("missing_count"),
                over_count=assignment.get("over_count"),
            )
        else:
            gates["link_partition"] = gate(STATUS_PASS, "owned/freeway/exit categories form a complete disjoint partition")
        tie_info = assignment.get("tie_analysis", {})
        if tie_info.get("status") == STATUS_NE:
            gates["assignment_ties"] = gate(STATUS_NE, str(tie_info.get("reason")))
        elif tie_info.get("tie_count", 0):
            gates["assignment_ties"] = gate(STATUS_FAIL, "equal-hop downstream terminal ties were found", tie_count=tie_info["tie_count"])
        else:
            gates["assignment_ties"] = gate(STATUS_PASS, "no equal-hop downstream terminal ties were found")

    adjacency = manifest["adjacency"]
    if not adjacency.get("available"):
        status = STATUS_NE if adjacency.get("error") == "file not found" else STATUS_FAIL
        gates["adjacency"] = gate(status, str(adjacency.get("error") or "adjacency evidence unavailable"))
    elif (
        adjacency.get("declared_pair_count") != adjacency.get("calculated_pair_count")
        or adjacency.get("declared_leg_count") != adjacency.get("calculated_leg_count")
        or adjacency.get("empty_internal_pair_count")
    ):
        gates["adjacency"] = gate(STATUS_FAIL, "adjacency declarations or internal members are inconsistent")
    else:
        gates["adjacency"] = gate(STATUS_PASS, "adjacency declarations match their calculated sizes")

    storage = manifest["storage_capacity"]
    if not storage.get("available"):
        status = STATUS_NE if storage.get("error") == "file not found" else STATUS_FAIL
        gates["storage_capacity"] = gate(status, str(storage.get("error") or "storage evidence unavailable"))
    elif not storage.get("jam_density_veh_km_lane") or storage.get("nonpositive_storage_count"):
        gates["storage_capacity"] = gate(STATUS_FAIL, "jam density or storage capacities are non-positive")
    else:
        gates["storage_capacity"] = gate(STATUS_PASS, "jam density and all reported storage capacities are positive")

    vendor = manifest["vendor_snapshot"]
    if not vendor.get("snapshot_file", {}).get("is_file"):
        gates["vendor_snapshot"] = gate(STATUS_NE, "vendor snapshot metadata is unavailable")
    elif not vendor.get("commit"):
        gates["vendor_snapshot"] = gate(STATUS_FAIL, "vendor snapshot commit could not be parsed")
    else:
        gates["vendor_snapshot"] = gate(STATUS_PASS, "vendor snapshot commit was recorded", commit=vendor["commit"])

    numsim = manifest["actual_numsim"]
    if not numsim.get("exists"):
        gates["numsim_source_match"] = gate(STATUS_NE, str(numsim.get("error") or "actual NumSim root unavailable"))
    elif numsim.get("error"):
        gates["numsim_source_match"] = gate(STATUS_FAIL, str(numsim["error"]))
    elif numsim.get("mismatch_count"):
        gates["numsim_source_match"] = gate(STATUS_FAIL, "actual NumSim src differs from the vendor snapshot", mismatch_count=numsim["mismatch_count"])
    else:
        gates["numsim_source_match"] = gate(STATUS_PASS, "actual NumSim src matches the vendor snapshot file-for-file")

    states = manifest["state_observations"]
    gates["state_observation_contract"] = state_observation_contract_gate(states)

    actions = manifest["action_directory"]
    if not actions.get("exists"):
        gates["action_inventory"] = gate(STATUS_NE, "no action directory was supplied or it does not exist")
    elif actions.get("invalid_action_json_count") or actions.get("invalid_state_json_count"):
        gates["action_inventory"] = gate(STATUS_FAIL, "the action directory contains unreadable JSON")
    elif not actions.get("action_file_count") and not actions.get("state_file_count"):
        gates["action_inventory"] = gate(STATUS_NE, "the action directory contains no state/action JSON")
    else:
        gates["action_inventory"] = gate(STATUS_PASS, "state/action JSON inventory completed")
    wall = actions.get("decision_wall_sec", {})
    if not wall.get("count"):
        gates["runtime"] = gate(STATUS_NE, "no actual metadata.decision_wall_sec samples were found")
    elif wall.get("p95", float("inf")) <= 30.0 and wall.get("max", float("inf")) <= 45.0:
        gates["runtime"] = gate(STATUS_PASS, "actual decision wall time meets p95 and hard-limit gates", p95=wall["p95"], max=wall["max"])
    else:
        gates["runtime"] = gate(STATUS_FAIL, "actual decision wall time exceeds p95=30s or max=45s", p95=wall["p95"], max=wall["max"])
    gates["projection_diagnostics"] = projection_diagnostics_gate(actions)
    gates["runtime_provenance"] = runtime_provenance_gate(actions)
    gates["signal_com_readback"] = signal_com_readback_gate(actions)
    gates["signal_event_timing"] = gate(
        STATUS_NE,
        "no expected signal-transition oracle is available; readback rows alone cannot establish event timing error",
    )

    err = manifest["vissim_error"]
    if not err.get("exists"):
        gates["vissim_error_log"] = gate(STATUS_NE, "VISSIM .err file was not available")
    elif err.get("error"):
        gates["vissim_error_log"] = gate(STATUS_FAIL, str(err["error"]))
    elif err.get("error_line_count"):
        gates["vissim_error_log"] = gate(STATUS_FAIL, "VISSIM error log contains error/fatal lines", count=err["error_line_count"])
    else:
        gates["vissim_error_log"] = gate(STATUS_PASS, "VISSIM error log contains no error/fatal lines")
    return gates


def _artifact_paths(args: argparse.Namespace, repo: Path) -> dict[str, Path]:
    return {
        "network": Path(args.network),
        "signal_roles": Path(args.signal_roles),
        "link_assignment": Path(args.assignment),
        "adjacency": Path(args.adjacency),
        "storage_capacity": Path(args.storage),
        "tuning": Path(args.tuning),
        "calibration": Path(args.calibration),
        "control_mapping": Path(args.control_mapping),
        "detector_mapping": Path(args.detector_mapping),
        "generated_vbs_config": Path(args.vbs_config),
        "adapter": Path(args.adapter),
        "vendor_snapshot": Path(args.vendor_root) / "SNAPSHOT.md",
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    repo = Path(args.repo).resolve()
    primary_paths = _artifact_paths(args, repo)
    for raw in args.extra_input:
        name, separator, value = raw.partition("=")
        if not separator or not name.strip() or not value.strip():
            raise ValueError(f"--extra-input must be NAME=PATH, got: {raw!r}")
        primary_paths[f"extra:{name.strip()}"] = Path(value.strip())
    signal_dir = Path(args.signal_dir)
    signal_paths = sorted(signal_dir.glob("*.sig")) if signal_dir.is_dir() else []

    env_numsim = os.environ.get("NUMSIM_REPO_ROOT", "").strip()
    if args.numsim_root:
        actual_root = Path(args.numsim_root)
        numsim_source = "argument"
    elif env_numsim:
        actual_root = Path(env_numsim)
        numsim_source = "environment"
    else:
        actual_root = None
        numsim_source = "unset"

    network_path = primary_paths["network"]
    err_source = Path(args.vissim_err) if args.vissim_err else network_path.with_suffix(".err")
    err_target = Path(args.vissim_err_copy_target) if args.vissim_err_copy_target else None
    action_dir_path = Path(args.action_dir) if args.action_dir else None
    action_evidence = action_directory_evidence(action_dir_path)
    explicit_state_paths = [Path(path) for path in args.state_json]
    discovered_state_paths = [Path(path) for path in action_evidence.get("state_files", [])]
    state_paths: list[Path] = []
    seen_state_paths: set[str] = set()
    for path in [*explicit_state_paths, *discovered_state_paths]:
        key = str(path.resolve(strict=False)).casefold()
        if key not in seen_state_paths:
            seen_state_paths.add(key)
            state_paths.append(path)
    states = state_evidence(state_paths)
    states["explicit_configured_count"] = len(explicit_state_paths)
    states["action_dir_discovered_count"] = len(discovered_state_paths)
    states["deduplicated_count"] = len(state_paths)
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "purpose": "static evidence for the current core15n41 VISSIM rollout plant",
            "historical_outputs_are_current_evidence": False,
            "missing_paths": STATUS_NE,
            "status_values": [STATUS_PASS, STATUS_FAIL, STATUS_NE],
        },
        "workspace_git": git_evidence(repo),
        "inputs": {
            "primary": {name: file_evidence(path) for name, path in primary_paths.items()},
            "signal_program_directory": str(signal_dir.resolve(strict=False)),
            "signal_program_count": len(signal_paths),
            "signal_programs": [file_evidence(path) for path in signal_paths],
        },
        "network": network_evidence(network_path, primary_paths["signal_roles"]),
        "link_assignment": assignment_evidence(primary_paths["link_assignment"], network_path, primary_paths["signal_roles"]),
        "adjacency": adjacency_evidence(primary_paths["adjacency"]),
        "storage_capacity": storage_evidence(primary_paths["storage_capacity"]),
        "vendor_snapshot": vendor_snapshot_evidence(Path(args.vendor_root)),
        "actual_numsim": numsim_evidence(Path(args.vendor_root), actual_root, numsim_source),
        "state_observations": states,
        "action_directory": action_evidence,
        "vissim_error": vissim_error_evidence(err_source, err_target),
    }
    manifest["gates"] = build_gates(manifest)
    counts = Counter(item["status"] for item in manifest["gates"].values())
    manifest["gate_summary"] = {
        "pass": counts[STATUS_PASS],
        "fail": counts[STATUS_FAIL],
        "not_evaluated": counts[STATUS_NE],
        "overall": STATUS_FAIL if counts[STATUS_FAIL] else (STATUS_NE if counts[STATUS_NE] else STATUS_PASS),
    }
    return manifest


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _md(value: Any) -> str:
    return str(value if value is not None else "-").replace("|", "\\|").replace("\n", " ")


def render_markdown(manifest: Mapping[str, Any]) -> str:
    gates = manifest["gates"]
    network = manifest["network"]
    assignment = manifest["link_assignment"]
    adjacency = manifest["adjacency"]
    storage = manifest["storage_capacity"]
    actions = manifest["action_directory"]
    signal_readback = actions.get("signal_readback", {})
    states = manifest.get("state_observations", {})
    lines = [
        "# Plant Fidelity Static Audit Summary",
        "",
        f"Generated: `{manifest['generated_at_utc']}`",
        "",
        "> This report uses live files supplied to the CLI. Historical `outputs/gates_*` measurements are not treated as current evidence.",
        "",
        "## Gate Summary",
        "",
        "| Gate | Status | Reason |",
        "|---|---|---|",
    ]
    for name, item in gates.items():
        lines.append(f"| `{_md(name)}` | **{_md(item['status'])}** | {_md(item['reason'])} |")
    lines.extend(
        [
            "",
            "## Static Scale",
            "",
            "| Evidence | Value |",
            "|---|---:|",
            f"| Network links | {_fmt(network.get('link_count'), 0)} |",
            f"| Connectors | {_fmt(network.get('connector_count'), 0)} |",
            f"| Raw XML active signal controllers | {_fmt(network.get('raw_active_signal_controller_count'), 0)} |",
            f"| Urban eligible controllers (roles `active=true`) | {_fmt(network.get('urban_eligible_signal_controller_count'), 0)} |",
            f"| Model signal controllers | {_fmt(network.get('model_signal_controller_count'), 0)} |",
            f"| Auxiliary active / artificial ramp-meter SCs | {_fmt(network.get('auxiliary_active_signal_controller_count'), 0)} / {_fmt(network.get('artificial_ramp_meter_active_signal_controller_count'), 0)} |",
            f"| Model-excluded controllers | {_md([item.get('no') for item in network.get('model_excluded_signal_controllers', [])])} |",
            f"| SC9004 head references | {_fmt(network.get('sc9004', {}).get('head_reference_count'), 0)} |",
            f"| Assignment owned / freeway / exit | {_fmt(assignment.get('owned_count'), 0)} / {_fmt(assignment.get('freeway_count'), 0)} / {_fmt(assignment.get('exit_count'), 0)} |",
            f"| Assignment coverage / duplicates / ties | {_fmt(assignment.get('coverage_count'), 0)} / {_fmt(assignment.get('cross_category_duplicate_count'), 0)} / {_fmt(assignment.get('tie_analysis', {}).get('tie_count'), 0)} |",
            f"| Adjacency pairs / internal pairs | {_fmt(adjacency.get('calculated_pair_count'), 0)} / {_fmt(adjacency.get('internal_pair_count'), 0)} |",
            f"| Internal member refs / unique | {_fmt(adjacency.get('internal_member_reference_count'), 0)} / {_fmt(adjacency.get('internal_member_unique_count'), 0)} |",
            f"| Jam density (veh/km/lane) | {_fmt(storage.get('jam_density_veh_km_lane'))} |",
            f"| Storage entries / total vehicles | {_fmt(storage.get('storage_count'), 0)} / {_fmt(storage.get('storage_total_veh'))} |",
            f"| Action JSON / state JSON | {_fmt(actions.get('action_file_count'), 0)} / {_fmt(actions.get('state_file_count'), 0)} |",
            f"| State contract explicit / action-dir discovered | {_fmt(states.get('explicit_configured_count'), 0)} / {_fmt(states.get('action_dir_discovered_count'), 0)} |",
            f"| Projection records pass / fail | {_fmt(actions.get('projection_contract', {}).get('pass_count'), 0)} / {_fmt(actions.get('projection_contract', {}).get('fail_count'), 0)} |",
            f"| Runtime provenance records pass / fail | {_fmt(actions.get('runtime_provenance_contract', {}).get('pass_count'), 0)} / {_fmt(actions.get('runtime_provenance_contract', {}).get('fail_count'), 0)} |",
            f"| Run groups pass / fail / mixed | {_fmt(actions.get('run_contract', {}).get('pass_count'), 0)} / {_fmt(actions.get('run_contract', {}).get('fail_count'), 0)} / {_fmt(actions.get('run_contract', {}).get('mixed_provenance_run_count'), 0)} |",
            f"| Signal readback files / rows | {_fmt(signal_readback.get('file_count'), 0)} / {_fmt(signal_readback.get('row_count'), 0)} |",
            f"| Signal readback ok / mismatch / ok!=1 | {_fmt(signal_readback.get('ok_count'), 0)} / {_fmt(signal_readback.get('mismatch_count'), 0)} / {_fmt(signal_readback.get('ok_not_one_count'), 0)} |",
            f"| Signal immediate / post-step / unpaired post-step | {_fmt(signal_readback.get('immediate_count'), 0)} / {_fmt(signal_readback.get('post_step_count'), 0)} / {_fmt(signal_readback.get('unpaired_post_step_count'), 0)} |",
            f"| Signal readback malformed rows / files / empty files | {_fmt(signal_readback.get('malformed_row_count'), 0)} / {_fmt(signal_readback.get('malformed_file_count'), 0)} / {_fmt(signal_readback.get('empty_file_count'), 0)} |",
            f"| Actual decision wall p95 / max (s) | {_fmt(actions.get('decision_wall_sec', {}).get('p95'))} / {_fmt(actions.get('decision_wall_sec', {}).get('max'))} |",
            "",
            "## Provenance",
            "",
            f"- Workspace: branch `{_md(manifest['workspace_git'].get('branch'))}`, commit `{_md(manifest['workspace_git'].get('commit'))}`, dirty `{_md(manifest['workspace_git'].get('dirty'))}`",
            f"- Vendor snapshot commit: `{_md(manifest['vendor_snapshot'].get('commit'))}`",
            f"- Actual NUMSIM_REPO_ROOT: `{_md(manifest['actual_numsim'].get('actual_root'))}`",
            f"- Actual NumSim commit: `{_md((manifest['actual_numsim'].get('git') or {}).get('commit'))}`",
            f"- Vendor/actual src mismatch count: `{_md(manifest['actual_numsim'].get('mismatch_count'))}`",
            "",
            "## Input Hashes",
            "",
            "| Input | Exists | SHA-256 | Path |",
            "|---|---|---|---|",
        ]
    )
    for name, evidence in manifest["inputs"]["primary"].items():
        lines.append(
            f"| `{_md(name)}` | {_md(evidence.get('is_file'))} | `{_md(evidence.get('sha256'))}` | `{_md(evidence.get('path'))}` |"
        )
    lines.extend(
        [
            "",
            f"Signal programs hashed: **{manifest['inputs']['signal_program_count']}**",
            "",
            "## Notes",
            "",
            "- `PASS` means the available static evidence satisfies the implemented invariant.",
            "- `FAIL` means available evidence contradicts an invariant or threshold.",
            "- `NOT_EVALUATED` means the necessary path or measurement was unavailable; it is not a pass.",
            "- Projection diagnostics pass only when state/action pairing, both mass identities, residual consistency, and clipping rules are all verified.",
            "- Runtime provenance is validated per run ID; mixed fingerprints under one run ID fail instead of being averaged together.",
            "",
        ]
    )
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    suffix = 0
    while temporary.exists():
        suffix += 1
        temporary = path.with_name(f".{path.name}.{os.getpid()}.{suffix}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary, path)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        finally:
            raise


def make_parser(repo: Path) -> argparse.ArgumentParser:
    network_dir = repo / "network" / "real_world_gaepo_modi"
    mapping_dir = repo / "evaluation" / "real_world_modi_control_distributed_20260728"
    parser = argparse.ArgumentParser(
        description="Generate a current core15n41 plant-fidelity evidence manifest and Markdown summary.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--repo", default=str(repo), help="VISSIM repository root")
    parser.add_argument("--network", default=str(network_dir / "modi_eval_rw_control.inpx"))
    parser.add_argument("--signal-dir", default=str(network_dir), help="directory containing live .sig programs")
    parser.add_argument("--signal-roles", default=str(repo / "evaluation" / "real_world_modi_inventory" / "signal_controller_roles.csv"))
    parser.add_argument("--assignment", default=str(repo / "outputs" / "link_player_assignment_20260805.json"))
    parser.add_argument("--adjacency", default=str(repo / "outputs" / "intersection_adjacency8_20260805.json"))
    parser.add_argument("--storage", default=str(repo / "outputs" / "urban_storage_capacity_20260805.json"))
    parser.add_argument("--tuning", default=str(repo / "evaluation" / "configs" / "real_world_modi_pstack_distributed_core15n41_20260805.json"))
    parser.add_argument("--calibration", default=str(repo / "evaluation" / "calibration" / "real_world_prediction_calibration_pshb4500fix_20260724.json"))
    parser.add_argument("--control-mapping", default=str(mapping_dir / "control_mapping_distributed_core15n41_20260805.json"))
    parser.add_argument("--detector-mapping", default=str(mapping_dir / "detector_local_mapping_distributed_core15n41_20260805.json"))
    parser.add_argument("--vbs-config", default=str(repo / "evaluation" / "generated" / "real_world_modi_control_config_distributed_core15n41_20260805.vbs"))
    parser.add_argument("--adapter", default=str(repo / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"))
    parser.add_argument("--vendor-root", default=str(repo / "vendor" / "NumSim-mine"))
    parser.add_argument("--numsim-root", default="", help="actual runtime NumSim root; overrides NUMSIM_REPO_ROOT")
    parser.add_argument("--state-json", action="append", default=[], metavar="PATH", help="state JSON to inspect; repeatable")
    parser.add_argument(
        "--action-dir",
        default="",
        help="directory recursively containing state_*.json, anchor_*.json, and action_*.json",
    )
    parser.add_argument("--vissim-err", default="", help="VISSIM error log; defaults to the network path with .err suffix")
    parser.add_argument("--vissim-err-copy-target", default="", help="optional destination file or existing directory for a preserved .err copy")
    parser.add_argument("--extra-input", action="append", default=[], metavar="NAME=PATH", help="additional live input to hash; repeatable")
    parser.add_argument("--json-out", default=str(repo / "reports" / "plant_fidelity_evidence_manifest.json"))
    parser.add_argument("--markdown-out", default=str(repo / "reports" / "plant_fidelity_audit_summary.md"))
    parser.add_argument("--strict", action="store_true", help="exit 2 when any gate is FAIL")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    initial_repo = Path(__file__).resolve().parents[1]
    parser = make_parser(initial_repo)
    args = parser.parse_args(argv)
    try:
        manifest = build_manifest(args)
    except ValueError as exc:
        parser.error(str(exc))
    markdown = render_markdown(manifest)
    json_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.json_out == "-":
        sys.stdout.write(json_text)
    else:
        atomic_write(Path(args.json_out), json_text)
    if args.markdown_out == "-":
        sys.stdout.write(markdown)
    else:
        atomic_write(Path(args.markdown_out), markdown)
    summary = manifest["gate_summary"]
    print(
        f"plant audit gates: overall={summary['overall']} "
        f"PASS={summary['pass']} FAIL={summary['fail']} NOT_EVALUATED={summary['not_evaluated']}",
        file=sys.stderr if args.json_out == "-" else sys.stdout,
    )
    if args.json_out != "-":
        print(f"JSON: {Path(args.json_out).resolve()}")
    if args.markdown_out != "-":
        print(f"Markdown: {Path(args.markdown_out).resolve()}")
    return 2 if args.strict and summary["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
