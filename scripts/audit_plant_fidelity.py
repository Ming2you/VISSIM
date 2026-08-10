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
import importlib.util
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


SCHEMA_VERSION = 3
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NE = "NOT_EVALUATED"
# 측정이 구조적으로 막힌 상태. NOT_EVALUATED 보다 나쁘다 - 아직 안 잰 것이 아니라 잴 수 없다.
STATUS_BLOCKED = "BLOCKED"
GATE_STATUS_VALUES = (STATUS_PASS, STATUS_FAIL, STATUS_BLOCKED, STATUS_NE)

# 나쁠수록 작다. 여러 판정을 합칠 때 가장 나쁜 것을 남긴다.
_STATUS_SEVERITY = {STATUS_FAIL: 0, STATUS_BLOCKED: 1, STATUS_NE: 2, STATUS_PASS: 3}


def worst_status(statuses: Iterable[str]) -> str:
    """여러 판정을 합칠 때 가장 나쁜 것을 남긴다. 아무것도 없으면 NOT_EVALUATED 다."""
    known = [status for status in statuses if status in _STATUS_SEVERITY]
    if not known:
        return STATUS_NE
    return min(known, key=lambda status: _STATUS_SEVERITY[status])


# N10 이 요구하는 범주. 게이트를 추가하면서 범주를 안 적으면 테스트가 잡는다.
GATE_CATEGORIES: dict[str, str] = {
    "input_provenance": "runtime",
    "network_xml": "topology",
    "signal_controller_scope": "signal",
    "link_partition": "topology",
    "assignment_ties": "topology",
    "adjacency": "topology",
    "storage_capacity": "topology",
    "canonical_topology": "topology",
    "vendor_snapshot": "runtime",
    "numsim_source_match": "runtime",
    "state_observation_contract": "projection",
    "action_inventory": "runtime",
    "runtime": "runtime",
    "projection_diagnostics": "projection",
    "mass_conservation": "mass",
    "runtime_provenance": "runtime",
    "preflight_provenance": "runtime",
    "signal_com_readback": "signal",
    "signal_event_timing": "signal",
    "signal_timing_canon": "signal",
    "signal_actuation_plan": "signal",
    "movement_signal_group_map": "signal",
    "stock_calibration": "calibration",
    "paired_dynamics": "paired_dynamics",
    "spillback_detection": "paired_dynamics",
    "gradient_ranking": "ranking",
    "promotion_readiness": "promotion",
    "vissim_error_log": "runtime",
}

CANONICAL_TOPOLOGY_SCHEMA = "vissim-strict-topology/v1"

# movement-SG 매핑에서 허용되는 미해결 사유. 이 밖의 사유는 매핑 결함이다.
ACCEPTED_UNRESOLVED_MOVEMENT_REASONS = frozenset({"synthetic_boundary_leg"})

# N9-4 spillback 임계. 표본 하한은 paired_validation_metrics 가 갖고 있다.
SPILLBACK_F1_MIN = 0.80
SPILLBACK_ONSET_MEDIAN_MAX_SEC = 60.0
SPILLBACK_ONSET_P90_MAX_SEC = 120.0

# N9-4 기울기 순위 임계. 점추정과 부트스트랩 95% 하한을 **둘 다** 넘어야 한다.
RANKING_THRESHOLDS = {"spearman": 0.70, "top_pairwise": 0.80}

# 승격 판정이 holdout 셀마다 요구하는 게이트.
PROMOTION_REQUIRED_GATES = (
    "paired_dynamics",
    "spillback_detection",
    "gradient_ranking",
    "mass_conservation",
    "runtime",
)
# 저수요 셀에서만, spillback 만 미측정을 면제한다. 다른 지표에는 면제가 없다.
PROMOTION_LOW_DEMAND_EXEMPT_GATES = frozenset({"spillback_detection"})

# state 의 형제로 놓이는 sidecar 는 `state_` 접두사를 그대로 물려받아 state 발견 glob 에 걸린다.
# 그러면 link count 가 없는 sidecar 가 state 로 집계돼 state_observation_contract 게이트가
# 엉뚱한 이유("missing counts")로 FAIL 한다. 생산자는 두 곳이다 -
#   plant/src/vissim_strict/physical_projection.py:452  (projection sidecar)
#   scripts/build_state_manifest_v2_1.py:301            (capture evidence sidecar)
# 이 모듈은 표준 라이브러리만 쓰므로 import 대신 접미사를 복제하고,
# scripts/tests/test_audit_plant_fidelity.py 가 두 생산자와의 일치를 강제한다.
STATE_SIDECAR_SUFFIXES = (
    ".physical_projection_v2_1.json",
    ".vehicle_capture_v2_1.json",
)

AUDIT_REPLAY_PATH_FIELDS = (
    "repo",
    "network",
    "signal_dir",
    "signal_roles",
    "assignment",
    "adjacency",
    "storage",
    "tuning",
    "calibration",
    "control_mapping",
    "detector_mapping",
    "vbs_config",
    "adapter",
    "vendor_root",
    "numsim_root",
    "action_dir",
    "vissim_err",
    "vissim_err_copy_target",
    "canonical_topology",
    "signal_timing",
    "movement_map",
    "actuation_plan",
    "parent_runs",
    "stock_calibration",
    "paired_metrics",
    "ranking_evidence",
    "promotion_evidence",
)
AUDIT_REPLAY_LIST_FIELDS = ("state_json", "extra_input", "required_gate")


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


_SIBLING_MODULES: dict[str, Any] = {}


def sibling_module(name: str) -> Any:
    """같은 scripts/ 안의 판정 모듈을 경로로 읽는다.

    N6 캘리브레이션 판정과 N9-4 지표·게이트 표는 이미 있다. 임계를 여기서 다시 적으면
    두 벌이 갈라진다 - 이 감사는 그 모듈을 **불러서** 쓴다. sys.path 에 scripts/ 가 없어도
    되도록 파일 경로로 적재한다.
    """
    if name in _SIBLING_MODULES:
        return _SIBLING_MODULES[name]
    module: Any = None
    path = Path(__file__).resolve().with_name(f"{name}.py")
    if path.is_file():
        spec = importlib.util.spec_from_file_location(f"_audit_sibling_{name}", path)
        if spec is not None and spec.loader is not None:
            candidate = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(candidate)
            except Exception:  # 판정 모듈이 깨져 있으면 게이트가 FAIL 로 드러나야 한다
                candidate = None
            module = candidate
    _SIBLING_MODULES[name] = module
    return module


def json_artifact(path: Path | None) -> tuple[dict[str, Any], Mapping[str, Any] | None]:
    """설정 안 함 / 파일 없음 / 깨짐 을 구분해 남긴다.

    셋을 뭉뚱그리면 "안 줬으니 통과" 와 "줬는데 못 읽었다" 가 같아진다. payload 는 매니페스트에
    싣지 않는다 - 정본 토폴로지 하나가 수천 셀이라 감사 산출물을 삼킨다.
    """
    record: dict[str, Any] = {
        "path": None,
        "configured": False,
        "exists": False,
        "available": False,
        "sha256": None,
        "error": None,
    }
    if path is None or not str(path).strip():
        record["error"] = "path not configured"
        return record, None
    record["configured"] = True
    record["path"] = str(path.resolve(strict=False))
    if not path.is_file():
        record["error"] = "file not found"
        return record, None
    record["exists"] = True
    record["sha256"] = sha256_file(path)
    payload, error = load_json(path)
    if error is not None:
        record["error"] = error
        return record, None
    if not isinstance(payload, Mapping):
        record["error"] = "artifact root is not a JSON object"
        return record, None
    record["available"] = True
    return record, payload


def artifact_absence_gate(record: Mapping[str, Any], label: str) -> dict[str, Any] | None:
    """산출물 자체를 못 읽는 경우만 판정하고, 나머지는 게이트 본문에 넘긴다."""
    if not record.get("configured"):
        return gate(STATUS_NE, f"no {label} artifact was supplied")
    if not record.get("exists"):
        return gate(STATUS_NE, f"{label} artifact was not found", path=record.get("path"))
    if not record.get("available"):
        return gate(STATUS_FAIL, f"{label} artifact could not be read: {record.get('error')}")
    return None


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


def preflight_provenance_evidence(path: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "record_count": 0,
        "pass_count": 0,
        "fail_count": 0,
        "distinct_manifest_sha256_count": 0,
        "distinct_fingerprint_count": 0,
        "records": [],
    }
    if path is None or not path.is_dir():
        return result
    hashes: set[str] = set()
    fingerprints: set[str] = set()
    for provenance_path in sorted(path.rglob("run_provenance_*.json")):
        payload, error = load_json(provenance_path)
        reasons: list[str] = []
        if error or not isinstance(payload, Mapping):
            reasons.append(error or "run provenance JSON root is not an object")
            payload = {}
        reference = payload.get("preflight_manifest")
        reference = reference if isinstance(reference, Mapping) else {}
        stored_path = str(reference.get("path", "")).strip()
        stored_hash = str(reference.get("sha256", "")).lower().strip()
        stored_fingerprint = str(payload.get("preflight_fingerprint_sha256", "")).lower().strip()
        manifest_path = Path(stored_path) if stored_path else None
        if manifest_path is None or not manifest_path.is_file():
            reasons.append("preflight manifest path is missing or not a file")
        else:
            actual_hash = sha256_file(manifest_path)
            if not stored_hash or stored_hash != actual_hash:
                reasons.append("preflight manifest SHA-256 mismatch")
            loaded, load_error = load_json(manifest_path)
            if load_error or not isinstance(loaded, Mapping):
                reasons.append(load_error or "preflight manifest JSON root is not an object")
            else:
                if loaded.get("schema_version") != "preflight-v3":
                    reasons.append("preflight schema_version is not preflight-v3")
                if loaded.get("status") != STATUS_PASS:
                    reasons.append("preflight status is not PASS")
                if loaded.get("reasons") != []:
                    reasons.append("preflight reasons are not empty")
                actual_fingerprint = str(loaded.get("fingerprint_sha256", "")).lower().strip()
                if not actual_fingerprint and isinstance(loaded.get("fingerprint"), Mapping):
                    actual_fingerprint = str(loaded["fingerprint"].get("sha256", "")).lower().strip()
                if not stored_fingerprint or stored_fingerprint != actual_fingerprint:
                    reasons.append("preflight fingerprint mismatch")
                runtime_identity = loaded.get("runtime_source_identity")
                runtime_identity = runtime_identity if isinstance(runtime_identity, Mapping) else {}
                if runtime_identity.get("status") != STATUS_PASS or runtime_identity.get("strict") is not True:
                    reasons.append("preflight runtime-source identity is not strict PASS")
                expected_python = runtime_identity.get("python")
                expected_python = expected_python if isinstance(expected_python, Mapping) else {}
                actual_python = payload.get("python_executable")
                actual_python = actual_python if isinstance(actual_python, Mapping) else {}
                expected_python_path = str(expected_python.get("path", "")).strip()
                actual_python_path = str(actual_python.get("path", "")).strip()
                if not expected_python_path or not actual_python_path or Path(expected_python_path).resolve() != Path(actual_python_path).resolve():
                    reasons.append("run Python path differs from preflight")
                if str(expected_python.get("sha256", "")).lower() != str(actual_python.get("sha256", "")).lower():
                    reasons.append("run Python SHA-256 differs from preflight")
                expected_version = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)", str(expected_python.get("version", "")))
                actual_triplet = actual_python.get("version_triplet")
                try:
                    actual_version = tuple(int(value) for value in actual_triplet[:3]) if isinstance(actual_triplet, list) and len(actual_triplet) >= 3 else None
                except (TypeError, ValueError):
                    actual_version = None
                expected_triplet = tuple(int(value) for value in expected_version.groups()) if expected_version else None
                if expected_triplet is None or actual_version != expected_triplet:
                    reasons.append("run Python version triplet differs from preflight")
        if stored_hash:
            hashes.add(stored_hash)
        if stored_fingerprint:
            fingerprints.add(stored_fingerprint)
        result["records"].append(
            {
                "path": str(provenance_path.resolve(strict=False)),
                "run_id": payload.get("run_id"),
                "preflight_path": stored_path,
                "preflight_sha256": stored_hash,
                "preflight_fingerprint_sha256": stored_fingerprint,
                "python_executable": payload.get("python_executable"),
                "status": STATUS_FAIL if reasons else STATUS_PASS,
                "reasons": reasons,
            }
        )
    result["record_count"] = len(result["records"])
    result["pass_count"] = sum(item["status"] == STATUS_PASS for item in result["records"])
    result["fail_count"] = sum(item["status"] == STATUS_FAIL for item in result["records"])
    result["distinct_manifest_sha256_count"] = len(hashes)
    result["distinct_fingerprint_count"] = len(fingerprints)
    return result


def action_directory_evidence(path: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path.resolve(strict=False)) if path else None,
        "exists": path.is_dir() if path else False,
        "artifact_file_count": 0,
        "artifact_files": [],
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
        "preflight_contract": preflight_provenance_evidence(path),
        "signal_readback": signal_readback_evidence(path),
        "errors": [],
    }
    if path is None or not path.is_dir():
        return result
    artifact_paths = sorted(
        (item for item in path.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(path).as_posix(),
    )
    result["artifact_file_count"] = len(artifact_paths)
    result["artifact_files"] = [
        {
            **file_evidence(item),
            "relative_path": item.relative_to(path).as_posix(),
        }
        for item in artifact_paths
    ]
    state_files = sorted(
        item
        for item in (*path.rglob("state_*.json"), *path.rglob("anchor_*.json"))
        if not item.name.endswith(STATE_SIDECAR_SUFFIXES)
    )
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


def vissim_error_directory_evidence(root: Path | None) -> dict[str, Any]:
    root_exists = root is not None and root.is_dir()
    provenance_by_name: dict[str, tuple[str, Path, Mapping[str, Any]]] = {}
    if root_exists:
        for provenance_path in sorted(root.glob("run_provenance_*.json")):
            payload, error = load_json(provenance_path)
            if error or not isinstance(payload, Mapping):
                continue
            name = str(payload.get("name", "")).strip()
            if name:
                provenance_by_name[name] = (str(payload.get("run_id", "")).strip(), provenance_path, payload)

    marker_paths = sorted(root.glob("vissim_error_evidence_*.json")) if root_exists else []
    files: list[dict[str, Any]] = []
    markers: list[dict[str, Any]] = []
    marker_errors: list[str] = []
    referenced_artifacts: set[str] = set()
    seen_names: set[str] = set()
    clean_absence_count = 0

    for marker_path in marker_paths:
        payload, error = load_json(marker_path)
        reasons: list[str] = []
        if error or not isinstance(payload, Mapping):
            reasons.append(error or "marker JSON root is not an object")
            payload = {}
        name = str(payload.get("run_name", "")).strip()
        run_id = str(payload.get("run_id", "")).strip()
        suffix_name = marker_path.stem.removeprefix("vissim_error_evidence_")
        if payload.get("schema_version") != "vissim-error-evidence-v2.1":
            reasons.append("schema_version must be vissim-error-evidence-v2.1")
        if not name or name != suffix_name:
            reasons.append("run_name does not match marker filename")
        if name in seen_names:
            reasons.append("duplicate marker for run_name")
        seen_names.add(name)
        provenance_record = provenance_by_name.get(name)
        if provenance_record is None:
            reasons.append("marker has no matching run provenance")
            provenance_payload: Mapping[str, Any] = {}
        else:
            expected_run_id, provenance_path, provenance_payload = provenance_record
            if not run_id or run_id != expected_run_id:
                reasons.append("marker run_id differs from run provenance")
        attempt = payload.get("attempt")
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            reasons.append("attempt must be a positive integer")
        if payload.get("process_exit_code") != 0:
            reasons.append("process_exit_code must be 0")
        if payload.get("source_checked_after_process_exit") is not True:
            reasons.append("source_checked_after_process_exit must be true")
        wall_path = root / f"wall_time_profile_{name}.json" if root else Path("__missing__")
        wall_payload, wall_error = load_json(wall_path)
        if wall_error or not isinstance(wall_payload, Mapping):
            reasons.append("matching wall-time profile is missing or malformed")
        elif (
            wall_payload.get("schema_version") != "wall-time-profile-v2.1"
            or wall_payload.get("status") != STATUS_PASS
            or wall_payload.get("run_id") != run_id
            or wall_payload.get("run_name") != name
            or wall_payload.get("attempt") != attempt
            or wall_payload.get("process_exit_code") != 0
        ):
            reasons.append("marker does not match the successful wall-time profile")
        checked_at = str(payload.get("post_exit_checked_at_utc", "")).strip()
        try:
            datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        except ValueError:
            reasons.append("post_exit_checked_at_utc is invalid")
        binding_text = str(payload.get("binding_text", ""))
        binding_hash = str(payload.get("binding_sha256", "")).lower()
        actual_binding_hash = hashlib.sha256(binding_text.encode("utf-8")).hexdigest()
        if not binding_text or binding_hash != actual_binding_hash:
            reasons.append("binding_sha256 is invalid")
        expected_binding = (
            f"run_id={run_id}\nrun_name={name}\nattempt={attempt}\n"
            f"present={str(payload.get('present')).lower()}\n"
            f"source_path={payload.get('source_path', '')}\n"
            f"post_exit_checked_at_utc={checked_at}"
        )
        if binding_text != expected_binding:
            reasons.append("binding_text does not match marker fields")

        files_record = provenance_payload.get("files")
        files_record = files_record if isinstance(files_record, Mapping) else {}
        network_record = files_record.get("network")
        network_record = network_record if isinstance(network_record, Mapping) else {}
        network_text = str(network_record.get("path", "")).strip()
        expected_source = str(Path(network_text).with_suffix(".err").resolve(strict=False)) if network_text else ""
        source_text = str(payload.get("source_path", "")).strip()
        if not expected_source or not source_text or os.path.normcase(source_text) != os.path.normcase(expected_source):
            reasons.append("source_path is not the run network .err path")

        stale_records = payload.get("stale_pre_run")
        if not isinstance(stale_records, list):
            reasons.append("stale_pre_run must be an explicit list")
            stale_records = []
        expected_archive_root = Path(str(root.resolve(strict=False)) + ".pre_run_err_archive") if root else Path("__missing__")
        for stale_index, raw_stale in enumerate(stale_records, 1):
            stale = raw_stale if isinstance(raw_stale, Mapping) else {}
            stale_attempt = stale.get("attempt")
            archived_text = str(stale.get("archived_path", "")).strip()
            archived_path = Path(archived_text).resolve(strict=False) if archived_text else Path("__missing__")
            expected_archive = (
                expected_archive_root / f"attempt_{int(stale_attempt):02d}_{name}.err"
                if isinstance(stale_attempt, int) and not isinstance(stale_attempt, bool)
                else Path("__missing__")
            )
            if (
                not isinstance(raw_stale, Mapping)
                or not isinstance(stale_attempt, int)
                or isinstance(stale_attempt, bool)
                or stale_attempt < 1
                or not isinstance(attempt, int)
                or stale_attempt > attempt
            ):
                reasons.append(f"stale_pre_run[{stale_index}] attempt is invalid or mixed")
            if str(stale.get("source_path", "")).strip() != source_text:
                reasons.append(f"stale_pre_run[{stale_index}] source_path differs from the current run")
            if archived_path != expected_archive.resolve(strict=False) or archived_path == Path(source_text).resolve(strict=False):
                reasons.append(f"stale_pre_run[{stale_index}] archive path does not prove run separation")
            archived_hash = sha256_file(archived_path) if archived_path.is_file() else ""
            if not archived_hash or archived_hash != str(stale.get("sha256", "")).lower():
                reasons.append(f"stale_pre_run[{stale_index}] archive SHA-256 mismatch")
            archived_at = str(stale.get("archived_at_utc", "")).strip()
            try:
                datetime.fromisoformat(archived_at.replace("Z", "+00:00"))
            except ValueError:
                reasons.append(f"stale_pre_run[{stale_index}] archived_at_utc is invalid")
            if archived_path.is_file():
                stale_text = archived_path.read_text(encoding="utf-8-sig", errors="replace")
                if re.search(r"\b(error|fatal)\b", stale_text, re.IGNORECASE):
                    reasons.append(f"stale_pre_run[{stale_index}] archive contains error/fatal text")
        if stale_records:
            reasons.append("stale_pre_run is non-empty; strict baseline certification requires a clean pre-run source")

        present = payload.get("present")
        artifact = payload.get("artifact")
        if present is False:
            expected_artifact = root / f"vissim_network_{name}.err" if root else Path("__missing__")
            if artifact not in (None, {}):
                reasons.append("absence marker must not contain an artifact")
            if expected_artifact.is_file():
                reasons.append("absence marker conflicts with a preserved .err artifact")
            if source_text and Path(source_text).is_file():
                reasons.append("absence marker is stale because source .err currently exists")
            if not reasons:
                clean_absence_count += 1
        elif present is True:
            if not isinstance(artifact, Mapping):
                reasons.append("present marker has no artifact record")
            else:
                artifact_path_text = str(artifact.get("path", "")).strip()
                artifact_path = Path(artifact_path_text).resolve(strict=False) if artifact_path_text else Path("__missing__")
                expected_artifact = (root / f"vissim_network_{name}.err").resolve(strict=False) if root else Path("__missing__")
                if artifact_path != expected_artifact:
                    reasons.append("artifact path is not the run-bound .err path")
                actual_hash = sha256_file(artifact_path) if artifact_path.is_file() else ""
                if not actual_hash or actual_hash != str(artifact.get("sha256", "")).lower():
                    reasons.append("artifact SHA-256 mismatch")
                source_path = Path(source_text) if source_text else Path("__missing__")
                source_hash = sha256_file(source_path) if source_path.is_file() else ""
                if not source_hash or source_hash != actual_hash:
                    reasons.append("present marker source .err is missing or differs from the preserved artifact")
                if artifact_path.is_file():
                    referenced_artifacts.add(os.path.normcase(str(artifact_path)))
                    files.append(vissim_error_evidence(artifact_path, None))
        else:
            reasons.append("present must be boolean")

        if reasons:
            marker_errors.extend(f"{marker_path.name}: {reason}" for reason in reasons)
        markers.append(
            {
                "path": str(marker_path.resolve(strict=False)),
                "run_name": name,
                "run_id": run_id,
                "present": present,
                "status": STATUS_FAIL if reasons else STATUS_PASS,
                "reasons": reasons,
            }
        )

    missing_markers = sorted(set(provenance_by_name) - seen_names)
    marker_errors.extend(f"missing marker for run {name}" for name in missing_markers)
    active_err_paths = sorted(root.glob("vissim_network_*.err")) if root_exists else []
    orphan_artifacts = [
        str(path.resolve(strict=False))
        for path in active_err_paths
        if os.path.normcase(str(path.resolve(strict=False))) not in referenced_artifacts
    ]
    marker_errors.extend(f"orphan or mixed-run .err artifact: {path}" for path in orphan_artifacts)
    notable: list[str] = []
    for item in files:
        notable.extend(str(line) for line in item.get("notable_lines", []))
    return {
        "source": str(root.resolve(strict=False)) if root else None,
        "exists": bool(markers),
        "evidence_complete": bool(provenance_by_name) and not marker_errors,
        "provenance_count": len(provenance_by_name),
        "marker_count": len(markers),
        "markers": markers,
        "marker_error_count": len(marker_errors),
        "marker_errors": marker_errors,
        "clean_absence_count": clean_absence_count,
        "orphan_artifacts": orphan_artifacts,
        "file_count": len(files),
        "files": files,
        "line_count": sum(int(item.get("line_count") or 0) for item in files),
        "nonempty_line_count": sum(int(item.get("nonempty_line_count") or 0) for item in files),
        "error_line_count": sum(int(item.get("error_line_count") or 0) for item in files),
        "warning_line_count": sum(int(item.get("warning_line_count") or 0) for item in files),
        "notable_lines": notable[:50],
        "error": next((str(item["error"]) for item in files if item.get("error")), None),
        "copy_requested": False,
        "copy_target": None,
        "copied_to": None,
    }


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


def preflight_provenance_gate(actions: Mapping[str, Any]) -> dict[str, Any]:
    contract = actions.get("preflight_contract", {})
    count = int(contract.get("record_count", 0) or 0)
    if not count:
        return gate(STATUS_NE, "no run provenance manifest references a preflight-v3 artifact")
    if contract.get("fail_count"):
        return gate(
            STATUS_FAIL,
            "one or more run provenance manifests have missing, stale, or invalid preflight evidence",
            record_count=count,
            fail_count=contract.get("fail_count"),
        )
    if contract.get("distinct_manifest_sha256_count") != 1 or contract.get("distinct_fingerprint_count") != 1:
        return gate(
            STATUS_FAIL,
            "run provenance manifests do not share one preflight hash and fingerprint",
            record_count=count,
            manifest_hash_count=contract.get("distinct_manifest_sha256_count"),
            fingerprint_count=contract.get("distinct_fingerprint_count"),
        )
    return gate(
        STATUS_PASS,
        "every run provenance manifest references the same verified preflight-v3 artifact",
        record_count=count,
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


def vissim_error_gate(err: Mapping[str, Any]) -> dict[str, Any]:
    if err.get("marker_error_count"):
        return gate(
            STATUS_FAIL,
            "VISSIM .err run-binding evidence is malformed, stale, missing, or mixed",
            count=err["marker_error_count"],
        )
    if err.get("evidence_complete") and not err.get("error_line_count"):
        return gate(
            STATUS_PASS,
            "run-bound VISSIM .err evidence is complete and contains no error/fatal lines",
            present_file_count=err.get("file_count", 0),
            clean_absence_count=err.get("clean_absence_count", 0),
        )
    if not err.get("exists"):
        return gate(STATUS_NE, "VISSIM .err file was not available")
    if err.get("error"):
        return gate(STATUS_FAIL, str(err["error"]))
    if err.get("error_line_count"):
        return gate(STATUS_FAIL, "VISSIM error log contains error/fatal lines", count=err["error_line_count"])
    return gate(STATUS_PASS, "VISSIM error log contains no error/fatal lines")


# ── N10 게이트 ────────────────────────────────────────────────────────────────
# 실 런이 없어 판정할 수 없는 게이트는 NOT_EVALUATED 다. PASS 로 두면 측정을 덜 할수록
# 유리해진다. 대조 산출물이 없어 교차검증이 못 돌면 그 게이트도 PASS 가 아니다.


def canonical_topology_evidence(path: Path | None) -> dict[str, Any]:
    record, payload = json_artifact(path)
    if payload is None:
        return record
    source = payload.get("source") if isinstance(payload.get("source"), Mapping) else {}
    report = payload.get("validation_report") if isinstance(payload.get("validation_report"), Mapping) else {}
    record.update(
        {
            "topology_schema_version": payload.get("schema_version"),
            "topology_hash": payload.get("topology_hash"),
            "inpx_sha256": (str(source.get("inpx_sha256") or "").strip().lower() or None),
            "validation_valid": report.get("valid"),
            "validation_error_count": report.get("error_count"),
            "counts": {
                key: len(payload.get(key) or [])
                for key in ("links", "cells", "signal_controllers", "signal_groups")
            },
        }
    )
    return record


def canonical_topology_gate(topology: Mapping[str, Any], network_input: Mapping[str, Any]) -> dict[str, Any]:
    absent = artifact_absence_gate(topology, "canonical topology")
    if absent is not None:
        return absent
    network_sha = str((network_input or {}).get("sha256") or "").strip().lower()
    if not network_sha:
        return gate(STATUS_NE, "the audited network could not be hashed, so topology identity cannot be checked")
    reasons: list[str] = []
    if topology.get("topology_schema_version") != CANONICAL_TOPOLOGY_SCHEMA:
        reasons.append(f"schema_version is not {CANONICAL_TOPOLOGY_SCHEMA}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(topology.get("topology_hash") or "").lower() or ""):
        reasons.append("topology_hash is missing or malformed")
    if topology.get("validation_valid") is not True or topology.get("validation_error_count"):
        reasons.append("compiler validation_report is not clean")
    if not topology.get("counts", {}).get("cells"):
        reasons.append("topology declares no cells")
    if topology.get("inpx_sha256") != network_sha:
        reasons.append("canonical topology was compiled from a different .inpx than the audited network")
    if reasons:
        return gate(STATUS_FAIL, "; ".join(reasons), inpx_sha256=topology.get("inpx_sha256"), network_sha256=network_sha)
    return gate(
        STATUS_PASS,
        "canonical topology matches the audited network and its compiler report is clean",
        topology_hash=topology.get("topology_hash"),
        counts=topology.get("counts"),
    )


def signal_timing_evidence(path: Path | None) -> dict[str, Any]:
    record, payload = json_artifact(path)
    if payload is None:
        return record
    controllers = [item for item in (payload.get("controllers") or []) if isinstance(item, Mapping)]
    record.update(
        {
            "declared_status": payload.get("status"),
            "controller_nos": sorted({str(item.get("sc_no")) for item in controllers}),
            "controller_count": len(controllers),
            "signal_group_count": sum(len(item.get("groups") or []) for item in controllers),
            "unresolved_count": len(payload.get("unresolved") or []),
            "conflicting_pair_count": len(payload.get("conflicting_pairs") or []),
            "overlapping_conflict_count": sum(
                1
                for item in (payload.get("conflicting_pairs") or [])
                if isinstance(item, Mapping) and item.get("actually_overlaps") is True
            ),
        }
    )
    return record


def actuation_plan_evidence(path: Path | None) -> dict[str, Any]:
    record, payload = json_artifact(path)
    if payload is None:
        return record
    controllers = payload.get("controllers") if isinstance(payload.get("controllers"), Mapping) else {}
    source = payload.get("source") if isinstance(payload.get("source"), Mapping) else {}
    counts = payload.get("counts") if isinstance(payload.get("counts"), Mapping) else {}
    record.update(
        {
            "declared_status": payload.get("status"),
            "controller_nos": sorted(str(key) for key in controllers),
            "node_ids": sorted(
                str(item.get("node_id"))
                for item in controllers.values()
                if isinstance(item, Mapping) and item.get("node_id")
            ),
            "network_sha256": (str(source.get("network_sha256") or "").strip().lower() or None),
            "timing_table_disagreements": sorted(str(item) for item in (payload.get("timing_table_disagreements") or [])),
            "counts": dict(counts),
        }
    )
    return record


def movement_map_evidence(path: Path | None) -> dict[str, Any]:
    record, payload = json_artifact(path)
    if payload is None:
        return record
    controllers = payload.get("controllers") if isinstance(payload.get("controllers"), Mapping) else {}
    unresolved = payload.get("unresolved_movements") if isinstance(payload.get("unresolved_movements"), Mapping) else {}
    counts = payload.get("counts") if isinstance(payload.get("counts"), Mapping) else {}
    record.update(
        {
            "declared_status": payload.get("status"),
            "controller_ids": sorted(str(key) for key in controllers),
            "unresolved_reason_counts": dict(sorted(Counter(str(value) for value in unresolved.values()).items())),
            "resolved_movements": counts.get("resolved_movements"),
            "counts": dict(counts),
        }
    )
    return record


def signal_timing_canon_gate(timing: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    absent = artifact_absence_gate(timing, "signal group timing")
    if absent is not None:
        return absent
    reasons: list[str] = []
    if timing.get("declared_status") != STATUS_PASS:
        reasons.append(f"timing artifact declares status {timing.get('declared_status')}")
    if not timing.get("controller_count"):
        reasons.append("timing table lists no controllers")
    if timing.get("unresolved_count"):
        reasons.append(f"{timing['unresolved_count']} signal groups are unresolved")
    if timing.get("overlapping_conflict_count"):
        reasons.append(f"{timing['overlapping_conflict_count']} conflicting pairs actually overlap")
    disagreements = list(plan.get("timing_table_disagreements") or [])
    if not plan.get("available"):
        if reasons:
            return gate(STATUS_FAIL, "; ".join(reasons))
        return gate(
            STATUS_NE,
            "the inpx-derived actuation plan is unavailable, so the canonical timing table cannot be cross-checked",
        )
    if disagreements:
        reasons.append(
            "the canonical timing table disagrees with the inpx supply file VISSIM actually runs for "
            + ", ".join(disagreements)
        )
    if reasons:
        return gate(STATUS_FAIL, "; ".join(reasons), timing_table_disagreements=disagreements)
    return gate(
        STATUS_PASS,
        "canonical timing table is resolved, conflict-free, and agrees with the inpx supply file",
        controller_count=timing.get("controller_count"),
        signal_group_count=timing.get("signal_group_count"),
    )


def signal_actuation_plan_gate(
    plan: Mapping[str, Any],
    timing: Mapping[str, Any],
    network_input: Mapping[str, Any],
) -> dict[str, Any]:
    absent = artifact_absence_gate(plan, "signal group actuation plan")
    if absent is not None:
        return absent
    counts = plan.get("counts") or {}
    reasons: list[str] = []
    if plan.get("declared_status") != STATUS_PASS:
        reasons.append(f"plan declares status {plan.get('declared_status')}")
    if not counts.get("controllers"):
        reasons.append("plan covers no controllers")
    if counts.get("conflict_violations"):
        reasons.append(f"{counts['conflict_violations']} planned conflict violations")
    if counts.get("uncovered_signal_groups"):
        reasons.append(f"{counts['uncovered_signal_groups']} signal groups are uncovered")
    network_sha = str((network_input or {}).get("sha256") or "").strip().lower()
    if not network_sha:
        reasons.append("the audited network could not be hashed")
    elif plan.get("network_sha256") != network_sha:
        reasons.append("the plan was derived from a different .inpx than the audited network")
    if timing.get("available") and plan.get("controller_nos") != timing.get("controller_nos"):
        reasons.append("plan and canonical timing table cover different signal controllers")
    if reasons:
        return gate(STATUS_FAIL, "; ".join(reasons), counts=dict(counts))
    return gate(STATUS_PASS, "actuation plan covers every signal group without conflict violations", counts=dict(counts))


def movement_signal_group_map_gate(mapping: Mapping[str, Any], timing: Mapping[str, Any]) -> dict[str, Any]:
    absent = artifact_absence_gate(mapping, "movement signal-group map")
    if absent is not None:
        return absent
    reasons: list[str] = []
    if mapping.get("declared_status") != STATUS_PASS:
        reasons.append(f"map declares status {mapping.get('declared_status')}")
    if not mapping.get("resolved_movements"):
        reasons.append("no movement was resolved to a signal group")
    unexpected = sorted(set(mapping.get("unresolved_reason_counts") or {}) - ACCEPTED_UNRESOLVED_MOVEMENT_REASONS)
    if unexpected:
        reasons.append("unresolved movements carry unaccepted reasons: " + ", ".join(unexpected))
    if timing.get("available"):
        expected = [f"SC{no}" for no in (timing.get("controller_nos") or [])]
        if sorted(mapping.get("controller_ids") or []) != sorted(expected):
            reasons.append("map and canonical timing table cover different signal controllers")
    if reasons:
        return gate(STATUS_FAIL, "; ".join(reasons), unresolved_reason_counts=mapping.get("unresolved_reason_counts"))
    return gate(
        STATUS_PASS,
        "every unresolved movement is an accepted synthetic boundary leg and the controller set matches",
        resolved_movements=mapping.get("resolved_movements"),
    )


MASS_IDENTITY_FIELDS = (
    "input_mass_balance_error_veh",
    "total_mass_balance_error_veh",
    "residual_consistency_error_veh",
)


def mass_conservation_gate(actions: Mapping[str, Any]) -> dict[str, Any]:
    """질량 항등식을 투영 진단에서 분리해 따로 세운다.

    투영 게이트 하나에 묶여 있으면 잔차 임계나 clipping 설명 때문에 FAIL 한 것인지
    질량이 깨진 것인지 표에서 구분되지 않는다.
    """
    contract = actions.get("projection_contract") if isinstance(actions.get("projection_contract"), Mapping) else {}
    records = [item for item in (contract.get("records") or []) if isinstance(item, Mapping)]
    if not records:
        return gate(STATUS_NE, "no projection_diagnostics record was available for a mass identity check")
    evaluable = [item for item in records if not item.get("missing_required_fields")]
    blind_count = len(records) - len(evaluable)
    if not evaluable:
        return gate(
            STATUS_NE,
            "no projection record carries the mass fields required for an identity check",
            record_count=len(records),
        )
    violating = []
    worst = 0.0
    for item in evaluable:
        errors = []
        for field in MASS_IDENTITY_FIELDS:
            try:
                value = abs(float(item.get(field)))
            except (TypeError, ValueError):
                errors.append(field)
                continue
            worst = max(worst, value)
            if not _count_close(value, 0.0):
                errors.append(field)
        if errors:
            violating.append({"source": item.get("source"), "fields": errors})
    if violating:
        return gate(
            STATUS_FAIL,
            "one or more decisions violate a mass identity",
            violating_record_count=len(violating),
            violations=violating[:10],
            worst_absolute_error_veh=worst,
        )
    if blind_count:
        return gate(
            STATUS_FAIL,
            "some decision records carry no mass evidence at all",
            record_count=len(records),
            records_without_mass_fields=blind_count,
        )
    return gate(
        STATUS_PASS,
        "every decision satisfies the input, total, and residual mass identities",
        record_count=len(records),
        worst_absolute_error_veh=worst,
    )


def stock_calibration_evidence(path: Path | None) -> dict[str, Any]:
    record, payload = json_artifact(path)
    if payload is None:
        return record
    module = sibling_module("validate_physical_stock_calibration")
    if module is None:
        record["validator_error"] = "validate_physical_stock_calibration is unavailable"
        return record
    try:
        record["verdict"] = module.validate(payload)
    except Exception as exc:  # 판정기가 못 돌면 통과가 아니라 실패다
        record["validator_error"] = f"{type(exc).__name__}: {exc}"
    return record


def stock_calibration_gate(calibration: Mapping[str, Any]) -> dict[str, Any]:
    absent = artifact_absence_gate(calibration, "physical stock calibration")
    if absent is not None:
        return absent
    if calibration.get("validator_error"):
        return gate(STATUS_FAIL, f"calibration could not be judged: {calibration['validator_error']}")
    verdict = calibration.get("verdict") if isinstance(calibration.get("verdict"), Mapping) else {}
    if not verdict:
        return gate(STATUS_FAIL, "the N6 calibration validator returned no verdict")
    if verdict.get("status") != STATUS_PASS:
        return gate(STATUS_FAIL, "physical stock calibration does not satisfy N6", reasons=verdict.get("reasons"))
    return gate(STATUS_PASS, "physical stock calibration satisfies every N6 threshold", measured=verdict.get("measured"))


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def paired_validation_evidence(path: Path | None) -> dict[str, Any]:
    record, payload = json_artifact(path)
    if payload is None:
        return record
    module = sibling_module("paired_validation_metrics")
    if module is None:
        record["metrics_module_error"] = "paired_validation_metrics is unavailable"
    horizons = payload.get("horizons") if isinstance(payload.get("horizons"), Mapping) else {}
    results: dict[int, Mapping[str, Any]] = {}
    for key, value in horizons.items():
        try:
            horizon = int(key)
        except (TypeError, ValueError):
            record.setdefault("horizon_errors", []).append(str(key))
            continue
        if isinstance(value, Mapping):
            results[horizon] = value
    record["horizon_count"] = len(results)
    if module is not None:
        try:
            record["verdict"] = module.evaluate(results)
        except Exception as exc:
            record["metrics_module_error"] = f"{type(exc).__name__}: {exc}"

    spillback = payload.get("spillback") if isinstance(payload.get("spillback"), Mapping) else {}
    cells: list[dict[str, Any]] = []
    for raw in spillback.get("cells") or []:
        if not isinstance(raw, Mapping):
            continue
        congested = bool(raw.get("congested"))
        positives = int(_finite(raw.get("positives")) or 0)
        sample_status = module.spillback_status(positives, congested) if module is not None else None
        cell = {
            "cell_id": raw.get("cell_id"),
            "congested": congested,
            "positives": positives,
            "sample_status": sample_status,
            "f1": _finite(raw.get("f1")),
            "onset_median_error_sec": _finite(raw.get("onset_median_error_sec")),
            "onset_p90_error_sec": _finite(raw.get("onset_p90_error_sec")),
        }
        failures: list[str] = []
        if sample_status == "EVALUATED":
            if cell["f1"] is None or cell["f1"] < SPILLBACK_F1_MIN:
                failures.append("f1")
            if cell["onset_median_error_sec"] is None or cell["onset_median_error_sec"] > SPILLBACK_ONSET_MEDIAN_MAX_SEC:
                failures.append("onset_median_error_sec")
            if cell["onset_p90_error_sec"] is None or cell["onset_p90_error_sec"] > SPILLBACK_ONSET_P90_MAX_SEC:
                failures.append("onset_p90_error_sec")
        cell["failures"] = failures
        cells.append(cell)
    record["spillback"] = {
        "cell_count": len(cells),
        "blocked_count": sum(1 for cell in cells if cell["sample_status"] == "BLOCKED"),
        "evaluated_count": sum(1 for cell in cells if cell["sample_status"] == "EVALUATED"),
        "exempt_count": sum(1 for cell in cells if cell["sample_status"] == STATUS_NE),
        "failing_count": sum(1 for cell in cells if cell["failures"]),
        "cells": cells,
    }
    return record


def paired_dynamics_gate(paired: Mapping[str, Any]) -> dict[str, Any]:
    absent = artifact_absence_gate(paired, "paired validation metrics")
    if absent is not None:
        return absent
    if paired.get("metrics_module_error"):
        return gate(STATUS_FAIL, f"paired metrics could not be judged: {paired['metrics_module_error']}")
    verdict = paired.get("verdict") if isinstance(paired.get("verdict"), Mapping) else {}
    status = str(verdict.get("status") or STATUS_NE)
    if status == STATUS_NE:
        return gate(STATUS_NE, "the paired validation artifact carries no measured H-gate metric")
    if status != STATUS_PASS:
        return gate(
            STATUS_FAIL,
            "measured H gates fail the N9-4 table",
            failed_horizons=verdict.get("failed_horizons"),
            reasons=verdict.get("reasons"),
        )
    return gate(
        STATUS_PASS,
        "every measured H gate satisfies the N9-4 table",
        measured_metrics=verdict.get("measured_metrics"),
    )


def spillback_gate(paired: Mapping[str, Any]) -> dict[str, Any]:
    absent = artifact_absence_gate(paired, "paired validation metrics")
    if absent is not None:
        return absent
    if paired.get("metrics_module_error"):
        return gate(STATUS_FAIL, f"spillback samples could not be judged: {paired['metrics_module_error']}")
    spillback = paired.get("spillback") if isinstance(paired.get("spillback"), Mapping) else {}
    if not spillback.get("cell_count"):
        return gate(STATUS_NE, "the paired validation artifact carries no spillback cell")
    evidence = {key: spillback.get(key) for key in ("cell_count", "blocked_count", "evaluated_count", "exempt_count", "failing_count")}
    if spillback.get("failing_count"):
        return gate(STATUS_FAIL, "one or more evaluated spillback cells miss F1 or onset error limits", **evidence)
    if spillback.get("blocked_count"):
        return gate(STATUS_BLOCKED, "congested spillback cells have fewer than the required positives", **evidence)
    if not spillback.get("evaluated_count"):
        return gate(STATUS_NE, "every spillback cell is a low-demand cell below the sample floor", **evidence)
    return gate(STATUS_PASS, "every evaluated spillback cell meets F1 and onset error limits", **evidence)


def ranking_evidence(path: Path | None) -> dict[str, Any]:
    record, payload = json_artifact(path)
    if payload is None:
        return record
    metrics: dict[str, dict[str, float | None]] = {}
    for name in RANKING_THRESHOLDS:
        item = payload.get(name) if isinstance(payload.get(name), Mapping) else {}
        metrics[name] = {
            "point": _finite(item.get("point")),
            "ci95_low": _finite(item.get("ci95_low")),
        }
    record["metrics"] = metrics
    return record


def gradient_ranking_gate(ranking: Mapping[str, Any]) -> dict[str, Any]:
    absent = artifact_absence_gate(ranking, "gradient ranking")
    if absent is not None:
        return absent
    metrics = ranking.get("metrics") if isinstance(ranking.get("metrics"), Mapping) else {}
    statuses: list[str] = []
    reasons: list[str] = []
    for name, threshold in RANKING_THRESHOLDS.items():
        measured = metrics.get(name) or {}
        point = measured.get("point")
        lower = measured.get("ci95_low")
        if point is None or lower is None:
            statuses.append(STATUS_NE)
            reasons.append(f"{name} is missing a point estimate or a bootstrap ci95_low")
            continue
        failing = [
            f"{name}.{label}={value:g} < {threshold:g}"
            for label, value in (("point", point), ("ci95_low", lower))
            if value < threshold
        ]
        statuses.append(STATUS_FAIL if failing else STATUS_PASS)
        reasons.extend(failing)
    status = worst_status(statuses)
    if status == STATUS_PASS:
        return gate(STATUS_PASS, "Spearman and top pairwise clear their thresholds on both estimates", metrics=metrics)
    return gate(status, "; ".join(reasons) or "no ranking measurement was supplied", metrics=metrics)


def parent_runs_evidence(path: Path | None) -> dict[str, Any]:
    record, payload = json_artifact(path)
    if payload is None:
        return record
    spec = payload.get("spec") if isinstance(payload.get("spec"), Mapping) else {}
    holdout = spec.get("holdout") if isinstance(spec.get("holdout"), Mapping) else {}
    congested = spec.get("congested") if isinstance(spec.get("congested"), Mapping) else {}
    record.update(
        {
            "holdout_demands": sorted({value for value in (_finite(item) for item in holdout.get("demand") or []) if value is not None}),
            "holdout_seeds": sorted({int(item) for item in holdout.get("seeds") or [] if _finite(item) is not None}),
            "congested_demands": sorted({value for value in (_finite(item) for item in congested.get("demand") or []) if value is not None}),
        }
    )
    return record


def promotion_evidence(path: Path | None) -> dict[str, Any]:
    record, payload = json_artifact(path)
    if payload is None:
        return record
    cells: list[dict[str, Any]] = []
    for raw in payload.get("cells") or []:
        if not isinstance(raw, Mapping):
            continue
        gates = raw.get("gates") if isinstance(raw.get("gates"), Mapping) else {}
        cells.append(
            {
                "demand": _finite(raw.get("demand")),
                "seed": int(_finite(raw.get("seed")) or -1),
                "gates": {str(key): str(value) for key, value in gates.items()},
            }
        )
    record["cell_count"] = len(cells)
    record["cells"] = cells
    return record


def promotion_gate(
    promotion: Mapping[str, Any],
    parents: Mapping[str, Any],
    gates: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """승격은 세 demand 의 holdout 시드에서 필수 게이트가 PASS 일 때만 가능하다.

    저수요라고 spillback 외 지표를 면제하지 않는다. 이 감사 자신의 게이트가 PASS 가 아니면
    holdout 증거가 아무리 좋아도 승격은 열리지 않는다.
    """
    static_statuses = [
        str(item.get("status"))
        for name, item in (gates or {}).items()
        if isinstance(item, Mapping) and name != "promotion_readiness"
    ]
    static_worst = worst_status(static_statuses)

    def blocked_by(status: str, reason: str) -> dict[str, Any]:
        """감사 자신의 상태를 항상 앞에 적는다. 증거가 없다는 말만 남으면 오해를 부른다."""
        if static_worst != STATUS_PASS:
            reason = f"the audit's own gates are {static_worst}; {reason}"
        return gate(worst_status([static_worst, status]), reason, static_gate_status=static_worst)

    if not parents.get("available"):
        return blocked_by(STATUS_NE, "the N5 parent-run spec is unavailable, so the required holdout coverage is unknown")
    required_demands = list(parents.get("holdout_demands") or [])
    required_seeds = list(parents.get("holdout_seeds") or [])
    if not required_demands or not required_seeds:
        return blocked_by(STATUS_NE, "the parent-run spec declares no holdout demand or seed")
    congested = set(parents.get("congested_demands") or [])

    absent = artifact_absence_gate(promotion, "holdout promotion evidence")
    if absent is not None:
        return blocked_by(str(absent["status"]), absent["reason"])

    by_key = {(cell.get("demand"), cell.get("seed")): cell for cell in promotion.get("cells") or []}
    statuses = [static_worst]
    reasons: list[str] = []
    if static_worst != STATUS_PASS:
        reasons.append(f"the audit's own gates are {static_worst}")
    for demand in required_demands:
        for seed in required_seeds:
            cell = by_key.get((demand, seed))
            if cell is None:
                statuses.append(STATUS_NE)
                reasons.append(f"no holdout evidence for demand={demand:g} seed={seed}")
                continue
            cell_gates = cell.get("gates") or {}
            for name in PROMOTION_REQUIRED_GATES:
                status = str(cell_gates.get(name) or STATUS_NE)
                exempt = (
                    status == STATUS_NE
                    and name in PROMOTION_LOW_DEMAND_EXEMPT_GATES
                    and demand not in congested
                )
                if exempt:
                    continue
                statuses.append(status if status in _STATUS_SEVERITY else STATUS_NE)
                if status != STATUS_PASS:
                    reasons.append(f"demand={demand:g} seed={seed} {name}={status}")
    status = worst_status(statuses)
    evidence = {
        "static_gate_status": static_worst,
        "required_demands": required_demands,
        "required_seeds": required_seeds,
        "congested_demands": sorted(congested),
        "evaluated_cell_count": len(by_key),
    }
    if status == STATUS_PASS:
        return gate(STATUS_PASS, "every holdout demand clears every promotion gate", **evidence)
    return gate(status, "; ".join(reasons[:12]) or "promotion evidence is incomplete", **evidence)


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

    network_input = (manifest.get("inputs", {}).get("primary", {}) or {}).get("network", {})
    timing = manifest.get("signal_timing", {})
    plan = manifest.get("actuation_plan", {})
    gates["canonical_topology"] = canonical_topology_gate(manifest.get("canonical_topology", {}), network_input)

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
    gates["mass_conservation"] = mass_conservation_gate(actions)
    gates["runtime_provenance"] = runtime_provenance_gate(actions)
    gates["preflight_provenance"] = preflight_provenance_gate(actions)
    gates["signal_com_readback"] = signal_com_readback_gate(actions)
    gates["signal_event_timing"] = gate(
        STATUS_NE,
        "no expected signal-transition oracle is available; readback rows alone cannot establish event timing error",
    )
    gates["signal_timing_canon"] = signal_timing_canon_gate(timing, plan)
    gates["signal_actuation_plan"] = signal_actuation_plan_gate(plan, timing, network_input)
    gates["movement_signal_group_map"] = movement_signal_group_map_gate(manifest.get("movement_map", {}), timing)

    paired = manifest.get("paired_validation", {})
    gates["stock_calibration"] = stock_calibration_gate(manifest.get("stock_calibration", {}))
    gates["paired_dynamics"] = paired_dynamics_gate(paired)
    gates["spillback_detection"] = spillback_gate(paired)
    gates["gradient_ranking"] = gradient_ranking_gate(manifest.get("ranking", {}))

    gates["vissim_error_log"] = vissim_error_gate(manifest["vissim_error"])
    gates["promotion_readiness"] = promotion_gate(
        manifest.get("promotion", {}),
        manifest.get("parent_runs", {}),
        gates,
    )
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


def _optional_path(value: Any) -> Path | None:
    text = str(value or "").strip()
    return Path(text) if text else None


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
    primary_evidence = {name: file_evidence(path) for name, path in primary_paths.items()}
    signal_evidence = [file_evidence(path) for path in signal_paths]
    input_hashes: dict[str, str | None] = {
        f"primary.{name}": record.get("sha256")
        for name, record in sorted(primary_evidence.items())
    }
    input_hashes.update(
        {
            f"signal_program.{Path(str(record.get('path', ''))).name}": record.get("sha256")
            for record in signal_evidence
        }
    )
    input_hashes.update(
        {
            f"action_artifact.{record.get('relative_path', '')}": record.get("sha256")
            for record in action_evidence.get("artifact_files", [])
            if isinstance(record, Mapping)
        }
    )
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "input_hashes": dict(sorted(input_hashes.items())),
        "command_version": {
            "command": "scripts/audit_plant_fidelity.py",
            "version": SCHEMA_VERSION,
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "reasons": [],
        "sample_dimensions": {
            "primary_inputs": len(primary_evidence),
            "signal_programs": len(signal_evidence),
            "action_artifacts": action_evidence.get("artifact_file_count", 0),
            "state_json_files": action_evidence.get("state_file_count", 0),
            "action_json_files": action_evidence.get("action_file_count", 0),
            "run_provenance_records": action_evidence.get("preflight_contract", {}).get("record_count", 0),
        },
        "units": {
            "file_count": "file",
            "sha256": "SHA-256 hex digest of raw bytes",
            "decision_wall_sec": "s",
            "vehicle_count": "vehicle",
        },
        "downstream_consumers": [
            "S0R-3 baseline snapshot",
            "scripts/run_plant_fidelity_matrix.ps1",
            "plant fidelity certification release",
        ],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "purpose": "static evidence for the current core15n41 VISSIM rollout plant",
            "historical_outputs_are_current_evidence": False,
            "missing_paths": STATUS_NE,
            "status_values": list(GATE_STATUS_VALUES),
            "gate_categories": dict(sorted(GATE_CATEGORIES.items())),
            "promotion_required_gates": list(PROMOTION_REQUIRED_GATES),
            "promotion_low_demand_exempt_gates": sorted(PROMOTION_LOW_DEMAND_EXEMPT_GATES),
        },
        "workspace_git": git_evidence(repo),
        "inputs": {
            "primary": primary_evidence,
            "signal_program_directory": str(signal_dir.resolve(strict=False)),
            "signal_program_count": len(signal_paths),
            "signal_programs": signal_evidence,
        },
        "canonical_topology": canonical_topology_evidence(_optional_path(args.canonical_topology)),
        "signal_timing": signal_timing_evidence(_optional_path(args.signal_timing)),
        "movement_map": movement_map_evidence(_optional_path(args.movement_map)),
        "actuation_plan": actuation_plan_evidence(_optional_path(args.actuation_plan)),
        "parent_runs": parent_runs_evidence(_optional_path(args.parent_runs)),
        "stock_calibration": stock_calibration_evidence(_optional_path(args.stock_calibration)),
        "paired_validation": paired_validation_evidence(_optional_path(args.paired_metrics)),
        "ranking": ranking_evidence(_optional_path(args.ranking_evidence)),
        "promotion": promotion_evidence(_optional_path(args.promotion_evidence)),
        "network": network_evidence(network_path, primary_paths["signal_roles"]),
        "link_assignment": assignment_evidence(primary_paths["link_assignment"], network_path, primary_paths["signal_roles"]),
        "adjacency": adjacency_evidence(primary_paths["adjacency"]),
        "storage_capacity": storage_evidence(primary_paths["storage_capacity"]),
        "vendor_snapshot": vendor_snapshot_evidence(Path(args.vendor_root)),
        "actual_numsim": numsim_evidence(Path(args.vendor_root), actual_root, numsim_source),
        "state_observations": states,
        "action_directory": action_evidence,
        "vissim_error": (
            vissim_error_evidence(err_source, err_target)
            if args.vissim_err or action_dir_path is None
            else vissim_error_directory_evidence(action_dir_path)
        ),
        "artifact_evidence": {
            "primary_inputs": primary_evidence,
            "signal_programs": signal_evidence,
            "action_directory": {
                "path": action_evidence.get("path"),
                "file_count": action_evidence.get("artifact_file_count", 0),
                "files": action_evidence.get("artifact_files", []),
            },
        },
    }
    manifest["gates"] = build_gates(manifest)
    counts = Counter(item["status"] for item in manifest["gates"].values())
    manifest["gate_summary"] = {
        "pass": counts[STATUS_PASS],
        "fail": counts[STATUS_FAIL],
        "blocked": counts[STATUS_BLOCKED],
        "not_evaluated": counts[STATUS_NE],
        "overall": worst_status(item["status"] for item in manifest["gates"].values()),
        "by_category": {
            category: dict(sorted(Counter(
                item["status"]
                for name, item in manifest["gates"].items()
                if GATE_CATEGORIES.get(name) == category
            ).items()))
            for category in sorted(set(GATE_CATEGORIES.values()))
        },
    }
    return manifest


def _resolved_argument_path(value: Any) -> str:
    text = str(value or "").strip()
    return str(Path(text).resolve(strict=False)) if text else ""


def audit_invocation(args: argparse.Namespace) -> dict[str, Any]:
    """Capture every build-affecting argument in a deterministic, replayable form."""
    invocation: dict[str, Any] = {
        field: _resolved_argument_path(getattr(args, field, ""))
        for field in AUDIT_REPLAY_PATH_FIELDS
    }
    state_json = getattr(args, "state_json", []) or []
    invocation["state_json"] = [_resolved_argument_path(path) for path in state_json]
    normalized_extra: list[str] = []
    for raw in getattr(args, "extra_input", []) or []:
        name, separator, value = str(raw).partition("=")
        if not separator or not name.strip() or not value.strip():
            raise ValueError(f"--extra-input must be NAME=PATH, got: {raw!r}")
        normalized_extra.append(f"{name.strip()}={_resolved_argument_path(value.strip())}")
    invocation["extra_input"] = normalized_extra
    invocation["required_gate"] = list(getattr(args, "required_gate", []) or [])
    invocation["strict"] = bool(getattr(args, "strict", False))
    invocation["require_complete"] = bool(getattr(args, "require_complete", False))
    return invocation


def canonical_semantic_projection(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return deterministic audit semantics; exclude timestamps and workspace dirtiness."""
    fields = (
        "schema_version",
        "input_hashes",
        "command_version",
        "reasons",
        "sample_dimensions",
        "units",
        "downstream_consumers",
        "policy",
        "inputs",
        "network",
        "link_assignment",
        "adjacency",
        "storage_capacity",
        "canonical_topology",
        "signal_timing",
        "movement_map",
        "actuation_plan",
        "parent_runs",
        "stock_calibration",
        "paired_validation",
        "ranking",
        "promotion",
        "vendor_snapshot",
        "actual_numsim",
        "state_observations",
        "action_directory",
        "vissim_error",
        "artifact_evidence",
        "gates",
        "gate_summary",
        "completion_policy",
        "strict",
        "require_complete",
        "status",
        "invocation",
    )
    return {field: manifest.get(field) for field in fields}


def semantic_projection_sha256(manifest: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        canonical_semantic_projection(manifest),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def finalize_manifest(manifest: dict[str, Any], args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    manifest["completion_policy"] = completion_policy(manifest["gates"], args.required_gate)
    exit_code = audit_exit_code(
        manifest["gate_summary"],
        manifest["completion_policy"],
        strict=args.strict,
        require_complete=args.require_complete,
    )
    manifest["strict"] = bool(args.strict)
    manifest["require_complete"] = bool(args.require_complete)
    manifest["status"] = STATUS_PASS if exit_code == 0 else STATUS_FAIL
    manifest["reasons"] = list(manifest["completion_policy"]["non_pass_gates"])
    manifest["gate_summary"]["strict_complete_status"] = manifest["status"]
    manifest["invocation"] = audit_invocation(args)
    manifest["semantic_projection_sha256"] = semantic_projection_sha256(manifest)
    return manifest, exit_code


def build_complete_manifest(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    return finalize_manifest(build_manifest(args), args)


def build_complete_manifest_from_invocation(invocation: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    expected = {
        *AUDIT_REPLAY_PATH_FIELDS,
        *AUDIT_REPLAY_LIST_FIELDS,
        "strict",
        "require_complete",
    }
    if set(invocation) != expected:
        raise ValueError("audit invocation fields are incomplete or unexpected")
    if any(not isinstance(invocation.get(field), str) for field in AUDIT_REPLAY_PATH_FIELDS):
        raise ValueError("audit invocation path fields must be strings")
    if any(not isinstance(invocation.get(field), list) for field in AUDIT_REPLAY_LIST_FIELDS):
        raise ValueError("audit invocation list fields must be lists")
    if any(not isinstance(item, str) for field in AUDIT_REPLAY_LIST_FIELDS for item in invocation[field]):
        raise ValueError("audit invocation list values must be strings")
    if not isinstance(invocation.get("strict"), bool) or not isinstance(invocation.get("require_complete"), bool):
        raise ValueError("audit invocation policy fields must be booleans")
    if str(invocation.get("vissim_err_copy_target", "")).strip():
        raise ValueError("audit replay forbids --vissim-err-copy-target side effects")
    args = argparse.Namespace(**dict(invocation), json_out="", markdown_out="")
    return build_complete_manifest(args)


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
        "| Gate | Category | Status | Reason |",
        "|---|---|---|---|",
    ]
    for name, item in gates.items():
        category = GATE_CATEGORIES.get(name, "unclassified")
        lines.append(
            f"| `{_md(name)}` | {_md(category)} | **{_md(item['status'])}** | {_md(item['reason'])} |"
        )
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
            f"| Canonical topology cells / links | {_fmt(manifest.get('canonical_topology', {}).get('counts', {}).get('cells'), 0)} / {_fmt(manifest.get('canonical_topology', {}).get('counts', {}).get('links'), 0)} |",
            f"| Timing canon controllers / signal groups | {_fmt(manifest.get('signal_timing', {}).get('controller_count'), 0)} / {_fmt(manifest.get('signal_timing', {}).get('signal_group_count'), 0)} |",
            f"| Timing table disagreements | {_md(manifest.get('actuation_plan', {}).get('timing_table_disagreements'))} |",
            f"| Paired H gates measured | {_fmt((manifest.get('paired_validation', {}).get('verdict') or {}).get('measured_metrics'), 0)} |",
            f"| Spillback cells evaluated / blocked / exempt | {_fmt(manifest.get('paired_validation', {}).get('spillback', {}).get('evaluated_count'), 0)} / {_fmt(manifest.get('paired_validation', {}).get('spillback', {}).get('blocked_count'), 0)} / {_fmt(manifest.get('paired_validation', {}).get('spillback', {}).get('exempt_count'), 0)} |",
            f"| Holdout promotion cells supplied | {_fmt(manifest.get('promotion', {}).get('cell_count'), 0)} |",
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
            "- `BLOCKED` means the measurement is structurally impossible with the evidence at hand; it is worse than `NOT_EVALUATED`.",
            "- Promotion needs every holdout demand to clear every promotion gate; low demand exempts spillback only.",
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


def completion_policy(
    gates: Mapping[str, Mapping[str, Any]],
    required_gate_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Evaluate completeness without confusing missing evidence with a pass."""
    requested = list(dict.fromkeys(required_gate_names or ()))
    unknown = sorted(set(requested) - set(gates))
    if unknown:
        raise ValueError(f"unknown required gate(s): {', '.join(unknown)}")
    selected = requested or list(gates)
    non_pass = [name for name in selected if gates[name]["status"] != STATUS_PASS]
    return {
        "required_gates": selected,
        "required_gate_count": len(selected),
        "non_pass_gates": non_pass,
        "complete": not non_pass,
    }


def audit_exit_code(
    summary: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    strict: bool,
    require_complete: bool,
) -> int:
    # BLOCKED 는 "아직 안 쟀다" 가 아니라 "잴 수 없다" 다. strict 에서 FAIL 과 같이 다룬다.
    if strict and (int(summary.get("fail", 0) or 0) > 0 or int(summary.get("blocked", 0) or 0) > 0):
        return 2
    if require_complete and not bool(policy.get("complete")):
        return 3
    return 0


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
    # N10 증거. 기본값은 비워 둔다 - 감사는 호출자가 명시한 살아 있는 산출물만 현재 증거로 본다.
    parser.add_argument("--canonical-topology", default="", help="canonical topology v3 JSON (N2)")
    parser.add_argument("--signal-timing", default="", help="canonical signal-group timing v3 JSON (N1)")
    parser.add_argument("--movement-map", default="", help="movement signal-group map v3 JSON (N1)")
    parser.add_argument("--actuation-plan", default="", help="signal-group actuation plan v3 JSON (N4-5)")
    parser.add_argument("--parent-runs", default="", help="parent run spec v3 JSON (N5); supplies the holdout coverage")
    parser.add_argument("--stock-calibration", default="", help="physical stock calibration JSON judged by N6")
    parser.add_argument("--paired-metrics", default="", help="paired validation metrics JSON judged by the N9-4 table")
    parser.add_argument("--ranking-evidence", default="", help="Spearman / top-pairwise point and bootstrap ci95_low JSON (N9-4)")
    parser.add_argument("--promotion-evidence", default="", help="per-holdout-cell gate outcomes JSON (N10)")
    parser.add_argument("--vissim-err", default="", help="VISSIM error log; defaults to the network path with .err suffix")
    parser.add_argument("--vissim-err-copy-target", default="", help="optional destination file or existing directory for a preserved .err copy")
    parser.add_argument("--extra-input", action="append", default=[], metavar="NAME=PATH", help="additional live input to hash; repeatable")
    parser.add_argument("--json-out", default=str(repo / "reports" / "plant_fidelity_evidence_manifest.json"))
    parser.add_argument("--markdown-out", default=str(repo / "reports" / "plant_fidelity_audit_summary.md"))
    parser.add_argument("--strict", action="store_true", help="exit 2 when any gate is FAIL")
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="exit 3 when any required gate is not PASS (including NOT_EVALUATED)",
    )
    parser.add_argument(
        "--required-gate",
        action="append",
        default=[],
        metavar="NAME",
        help="gate required by this run profile; repeatable (defaults to every gate)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    initial_repo = Path(__file__).resolve().parents[1]
    parser = make_parser(initial_repo)
    args = parser.parse_args(argv)
    try:
        manifest, exit_code = build_complete_manifest(args)
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
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
