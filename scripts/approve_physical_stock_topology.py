"""Approve one exact preflight/A1/A2 physical-stock topology bundle."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
PLANT_ROOT = REPO_ROOT / "plant"
for search_root in (SCRIPT_ROOT, PLANT_ROOT):
    if str(search_root) not in sys.path:
        sys.path.insert(0, str(search_root))

from build_preflight_manifest import DEFAULT_PATHS  # noqa: E402
from build_vissim_lane_graph import (  # noqa: E402
    COMMAND_VERSION as GRAPH_COMMAND_VERSION,
    behavioral_source_hashes,
    validate_lane_graph_artifact,
)
from compile_physical_stock_topology import (  # noqa: E402
    compile_physical_stock_topology,
    evidence_identity_hashes,
    validate_route_proofs_artifact,
)
from resolve_lane_routes import COMMAND_VERSION as ROUTES_COMMAND_VERSION  # noqa: E402
from src.vissim_strict.physical_projection import (  # noqa: E402
    SHA256_PATTERN,
    TopologyValidationError,
    ValidatedPhysicalTopology,
    atomic_write_json,
    file_sha256,
    resolve_contained_path,
    strict_load_json,
    validate_physical_stock_topology,
    workspace_relative_path,
)
from src.vissim_strict.run_evidence import (  # noqa: E402
    CONFIGURATION_INPUT_ROLES,
    MAX_APPROVAL_BYTES,
    MAX_POLICY_BYTES,
    MAX_PREFLIGHT_BYTES,
    MAX_TOPOLOGY_BYTES,
    PRODUCER_SOURCE_ROLES,
    resolve_canonical_workspace_absolute_file,
)
from src.vissim_strict.approval_replay import (  # noqa: E402
    MAX_VALIDATION_RESULT_BYTES,
    VALIDATION_RESULT_SCHEMA_VERSION,
    validation_result_wire_bytes,
)
from src.vissim_strict.topology import (  # noqa: E402
    canonical_json_sha256,
)


SCHEMA_VERSION = "topology-approval-v2.1"
UNITS = {"position": "m", "capacity": "veh"}
DOWNSTREAM_CONSUMERS = ["state-manifest-v2.1", "projection-v2.1"]
PREFLIGHT_UNITS = {
    "controller_count": "signal controller",
    "signal_program_count": "resolved .sig file",
    "signal_head_count": "signal head reference",
    "size_bytes": "byte",
    "sha256": "SHA-256 hex digest of raw bytes unless explicitly named normalised",
    "normalised_tree_sha256": "SHA-256 over relative Python paths and LF-normalised file hashes",
}
PREFLIGHT_DOWNSTREAM_CONSUMERS = [
    "S0R-3 baseline snapshot",
    "scripts/run_plant_fidelity_matrix.ps1",
    "scripts/audit_plant_fidelity.py",
    "paired VISSIM future campaign",
    "plant fidelity certification release",
]
INPUT_HASH_NAMES = {
    "preflight_file_sha256",
    "lane_graph_file_sha256",
    "lane_graph_semantic_sha256",
    "lane_route_proofs_file_sha256",
    "lane_route_proofs_semantic_sha256",
    "topology_file_sha256",
    "topology_semantic_sha256",
}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "input_hashes",
    "command_version",
    "status",
    "reasons",
    "sample_dimensions",
    "units",
    "downstream_consumers",
    "workspace_root_relative_to_artifact",
    "source_inputs",
    "approved_topology",
    "semantic_sha256",
}
PREFLIGHT_TOP_LEVEL_FIELDS = {
    "schema_version",
    "input_hashes",
    "command_version",
    "status",
    "reasons",
    "sample_dimensions",
    "units",
    "downstream_consumers",
    "repo",
    "artifacts",
    "network",
    "runtime_source_identity",
    "checks",
    "fingerprint",
    "fingerprint_sha256",
}
REQUIRED_A2_PREFLIGHT_ARTIFACTS = {
    "network",
    "link_assignment",
    "adjacency",
    "storage_capacity",
}
REQUIRED_B1A_PREFLIGHT_ARTIFACTS = set(PRODUCER_SOURCE_ROLES) | (
    set(CONFIGURATION_INPUT_ROLES) - {"demand_profile"}
)
FAIL_CLOSED_INPUT_EXCEPTIONS = (
    AttributeError,
    IndexError,
    KeyError,
    MemoryError,
    OSError,
    OverflowError,
    TypeError,
    ValueError,
)


@dataclass(frozen=True)
class ValidatedApprovalBundle:
    workspace_root: Path
    approval_path: Path
    approval: Mapping[str, Any]
    approval_file_sha256: str
    preflight_path: Path
    graph_path: Path
    routes_path: Path
    topology_path: Path
    preflight: Mapping[str, Any]
    graph: Mapping[str, Any]
    routes: Mapping[str, Any]
    topology: Mapping[str, Any]
    validated_topology: ValidatedPhysicalTopology


class ApprovalValidationError(ValueError):
    def __init__(self, reasons: Sequence[Mapping[str, Any]]) -> None:
        self.reasons = tuple(dict(item) for item in reasons)
        super().__init__("; ".join(str(item.get("code", "")) for item in self.reasons))


def _reason(code: str, detail: Any) -> dict[str, Any]:
    return {"code": code, "detail": detail}


def _safe_file_hash(path: Path, *, max_bytes: int) -> str:
    try:
        if not path.is_file() or path.stat().st_size > max_bytes:
            return ""
        return file_sha256(path)
    except (MemoryError, OSError):
        return ""


def semantic_payload(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: artifact[key]
        for key in (
            "schema_version",
            "input_hashes",
            "command_version",
            "sample_dimensions",
            "units",
            "downstream_consumers",
            "workspace_root_relative_to_artifact",
            "source_inputs",
            "approved_topology",
        )
    }


def _preflight_fingerprint_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    network = manifest["network"]
    runtime = manifest["runtime_source_identity"]
    return {
        "schema_version": manifest["schema_version"],
        "input_hashes": manifest["input_hashes"],
        "command_version": manifest["command_version"],
        "network": {
            "network_version": network.get("network_version", ""),
            "vissim_version": network.get("vissim_version", ""),
            "model_controllers": [
                {
                    "controller_no": item["controller_no"],
                    "supply_file_2": item["supply_file_2"],
                    "signal_head_reference_count": item["signal_head_reference_count"],
                    "sig_sha256": item["signal_program"]["sha256"],
                }
                for item in network.get("model_controllers", [])
            ],
            "excluded_controller": network.get("excluded_controller"),
            "auxiliary_controllers": network.get("auxiliary_controllers", []),
        },
        "runtime_source": {
            "schema_version": runtime.get("schema_version", ""),
            "expected_snapshot_commit": runtime.get("expected_snapshot_commit", ""),
            "selected_is_canonical": runtime.get("selected_is_canonical", False),
            "selected": runtime.get("selected", {}),
            "python_sha256": runtime.get("python", {}).get("sha256", ""),
        },
    }


def _preflight_fingerprint_sha256(manifest: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _preflight_fingerprint_payload(manifest),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_preflight_artifact(
    preflight: Mapping[str, Any], workspace_root: Path
) -> list[dict[str, Any]]:
    issues: list[str] = []
    if set(preflight) != PREFLIGHT_TOP_LEVEL_FIELDS:
        issues.append("preflight shape mismatch")
    if preflight.get("schema_version") != "preflight-v3":
        issues.append("schema_version mismatch")
    if preflight.get("status") != "PASS" or preflight.get("reasons") != []:
        issues.append("status/reasons mismatch")
    if preflight.get("units") != PREFLIGHT_UNITS:
        issues.append("preflight units mismatch")
    if preflight.get("downstream_consumers") != PREFLIGHT_DOWNSTREAM_CONSUMERS:
        issues.append("preflight downstream_consumers mismatch")
    if not isinstance(preflight.get("input_hashes"), dict):
        issues.append("input_hashes must be an object")
    if not isinstance(preflight.get("command_version"), dict):
        issues.append("command_version must be an object")
    checks = preflight.get("checks")
    if not isinstance(checks, list) or not checks:
        issues.append("checks must be a nonempty array")
        checks = []
    check_ids = [item.get("id") for item in checks if isinstance(item, dict)]
    if len(check_ids) != len(checks) or len(check_ids) != len(set(check_ids)):
        issues.append("checks contain malformed or duplicate identities")
    if any(
        set(item) != {"id", "status", "expected", "actual"}
        or item.get("status") != "PASS"
        for item in checks
        if isinstance(item, dict)
    ):
        issues.append("preflight check is not PASS")
    checks_by_id = {
        str(item["id"]): item for item in checks if isinstance(item, dict) and "id" in item
    }

    network_value = preflight.get("network")
    runtime_value = preflight.get("runtime_source_identity")
    if isinstance(network_value, dict):
        for field in (
            "model_controllers",
            "auxiliary_controllers",
            "resolved_signal_programs",
        ):
            records = network_value.get(field, [])
            if not isinstance(records, list):
                issues.append(f"preflight network.{field} must be an array")
            elif any(not isinstance(item, dict) for item in records):
                issues.append(f"preflight network.{field} contains a non-object record")
        controllers = network_value.get("model_controllers", [])
        if isinstance(controllers, list) and any(
            isinstance(item, dict) and not isinstance(item.get("signal_program"), dict)
            for item in controllers
        ):
            issues.append("preflight model controller signal_program must be an object")
    if isinstance(runtime_value, dict):
        for field in ("selected", "python"):
            if not isinstance(runtime_value.get(field), dict):
                issues.append(f"preflight runtime_source_identity.{field} must be an object")

    try:
        fingerprint_hash = _preflight_fingerprint_sha256(preflight)
    except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
        issues.append(f"invalid fingerprint payload: {exc}")
        fingerprint_hash = ""
    fingerprint = preflight.get("fingerprint")
    if (
        not isinstance(fingerprint, dict)
        or fingerprint.get("algorithm") != "sha256"
        or fingerprint.get("canonicalisation")
        != "UTF-8 JSON, sorted keys, compact separators, ensure_ascii"
        or fingerprint.get("sha256") != fingerprint_hash
        or preflight.get("fingerprint_sha256") != fingerprint_hash
    ):
        issues.append("preflight fingerprint mismatch")

    try:
        if preflight.get("repo") != str(workspace_root):
            issues.append("preflight repo does not equal workspace root")
    except OSError as exc:
        issues.append(f"invalid preflight repo: {exc}")

    input_hashes = preflight.get("input_hashes")
    input_hashes = input_hashes if isinstance(input_hashes, dict) else {}
    artifacts = preflight.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        issues.append("preflight artifacts must be a nonempty object")
        artifacts = {}
    if not REQUIRED_A2_PREFLIGHT_ARTIFACTS.issubset(artifacts):
        issues.append("preflight omits required A2 source artifacts")
    if not REQUIRED_B1A_PREFLIGHT_ARTIFACTS.issubset(artifacts):
        issues.append("preflight omits required B1a producer/configuration artifacts")
    for name, evidence in sorted(artifacts.items()):
        if not isinstance(evidence, dict) or set(evidence) != {
            "path", "exists", "size_bytes", "sha256"
        }:
            issues.append(f"artifact {name} evidence is malformed")
            continue
        try:
            authored_path = evidence.get("path")
            if name == "python_executable":
                if not isinstance(authored_path, str) or str(Path(authored_path)) != authored_path:
                    raise ValueError("python_executable path spelling is not canonical")
                path = Path(authored_path).resolve(strict=True)
                if path != Path(sys.executable).resolve(strict=True):
                    raise ValueError("python_executable is not the current interpreter")
            else:
                path = resolve_canonical_workspace_absolute_file(
                    workspace_root, authored_path
                )
            if (
                name == "supported_version_policy"
                and path.stat().st_size > MAX_POLICY_BYTES
            ):
                raise ValueError("supported version policy exceeds byte limit")
            actual_hash = file_sha256(path)
            actual_size = path.stat().st_size
        except (OSError, ValueError) as exc:
            issues.append(f"artifact {name} is unavailable: {exc}")
            continue
        if (
            evidence.get("exists") is not True
            or evidence.get("sha256") != actual_hash
            or input_hashes.get(name) != actual_hash
            or evidence.get("size_bytes") != actual_size
        ):
            issues.append(f"artifact {name} byte evidence mismatch")
        expected_checks = {
            f"artifact.{name}.exists": {
                "id": f"artifact.{name}.exists",
                "status": "PASS",
                "expected": True,
                "actual": True,
            },
            f"artifact.{name}.sha256": {
                "id": f"artifact.{name}.sha256",
                "status": "PASS",
                "expected": "non-empty SHA-256",
                "actual": actual_hash,
            },
        }
        for check_id, expected_check in expected_checks.items():
            check = checks_by_id.get(check_id)
            if check_id.endswith(".sha256"):
                if not isinstance(check, dict) or (
                    check.get("id") != expected_check["id"]
                    or check.get("status") != "PASS"
                    or check.get("expected") != "non-empty SHA-256"
                    or check.get("actual") != actual_hash
                ):
                    issues.append(f"preflight check {check_id} mismatch")
            elif check != expected_check:
                issues.append(f"preflight check {check_id} mismatch")

    command = preflight.get("command_version")
    if isinstance(command, dict):
        producer_path = workspace_root / "scripts/build_preflight_manifest.py"
        try:
            producer_hash = file_sha256(producer_path)
        except OSError as exc:
            issues.append(f"preflight producer unavailable: {exc}")
            producer_hash = ""
        if command != {
            "command": "scripts/build_preflight_manifest.py",
            "version": "preflight-v3",
            "sha256": producer_hash,
        }:
            issues.append("preflight command_version mismatch")

    network = preflight.get("network")
    runtime = preflight.get("runtime_source_identity")
    dimensions = preflight.get("sample_dimensions")
    if not isinstance(network, dict) or not isinstance(runtime, dict) or not isinstance(dimensions, dict):
        issues.append("preflight network/runtime/dimensions malformed")
    else:
        raw_resolved_programs = network.get("resolved_signal_programs", [])
        if not isinstance(raw_resolved_programs, list):
            issues.append("resolved_signal_programs must be an array")
            raw_resolved_programs = []
        resolved_programs: list[dict[str, Any]] = []
        for index, record in enumerate(raw_resolved_programs):
            if not isinstance(record, dict):
                issues.append(f"resolved_signal_programs[{index}] must be an object")
                continue
            resolved_programs.append(record)
            try:
                path = resolve_canonical_workspace_absolute_file(
                    workspace_root, record.get("path")
                )
                actual_hash = file_sha256(path)
            except (OSError, ValueError) as exc:
                issues.append(f"signal program unavailable: {exc}")
                continue
            hash_key = f"signal_program.SC{record.get('controller_no')}"
            if record.get("exists") is not True or record.get("sha256") != actual_hash or input_hashes.get(hash_key) != actual_hash:
                issues.append(f"signal program {hash_key} byte evidence mismatch")
        expected_input_hash_names = set(artifacts) | {
            f"signal_program.SC{record.get('controller_no')}"
            for record in resolved_programs
            if isinstance(record, dict)
        }
        if set(input_hashes) != expected_input_hash_names:
            issues.append("preflight input hash universe mismatch")
        model_controllers = network.get("model_controllers", [])
        auxiliary_controllers = network.get("auxiliary_controllers", [])
        selected_runtime = runtime.get("selected", {})
        model_controllers = model_controllers if isinstance(model_controllers, list) else []
        auxiliary_controllers = auxiliary_controllers if isinstance(auxiliary_controllers, list) else []
        selected_runtime = selected_runtime if isinstance(selected_runtime, dict) else {}
        expected_dimensions = {
            "model_signal_controllers": len(model_controllers),
            "resolved_signal_programs": sum(
                bool(item.get("exists") and item.get("sha256"))
                for item in resolved_programs if isinstance(item, dict)
            ),
            "unique_resolved_signal_programs": len({
                os.path.normcase(str(item.get("path", "")))
                for item in resolved_programs
                if isinstance(item, dict) and item.get("exists")
            }),
            "excluded_signal_controllers": 1 if network.get("excluded_controller") else 0,
            "auxiliary_signal_controllers": len(auxiliary_controllers),
            "signal_heads": (
                network.get("signal_head_count", 0)
                if isinstance(network.get("signal_head_count", 0), int)
                and not isinstance(network.get("signal_head_count", 0), bool)
                else -1
            ),
            "hashed_artifacts": sum(bool(value) for value in input_hashes.values()),
            "runtime_python_files": selected_runtime.get("actual_python_file_count", 0),
        }
        for field, expected in expected_dimensions.items():
            if dimensions.get(field) != expected:
                issues.append(f"sample_dimensions.{field} mismatch")
    return [_reason("topology_trust_mismatch", sorted(set(issues)))] if issues else []


def _validate_a1_provenance(
    preflight: Mapping[str, Any],
    graph: Mapping[str, Any],
    routes: Mapping[str, Any],
) -> list[str]:
    issues: list[str] = []
    artifacts = preflight.get("artifacts", {})
    artifacts = artifacts if isinstance(artifacts, dict) else {}
    network_evidence = artifacts.get("network", {})
    network_evidence = network_evidence if isinstance(network_evidence, dict) else {}
    network_hash = str(network_evidence.get("sha256", ""))
    graph_hashes = behavioral_source_hashes()
    expected_graph_command = {
        "version": GRAPH_COMMAND_VERSION,
        "source_sha256": graph_hashes,
        "command_hash": canonical_json_sha256(graph_hashes),
        "semantic_hash_scope": "schema_version, links, nodes, edges, connectors, signal_heads",
    }
    if graph.get("command") != expected_graph_command:
        issues.append("lane graph producer provenance mismatch")
    graph_source = graph.get("source", {})
    graph_source = graph_source if isinstance(graph_source, dict) else {}
    if graph_source.get("input_sha256") != network_hash:
        issues.append("lane graph/preflight network binding mismatch")

    routes_hashes = behavioral_source_hashes([SCRIPT_ROOT / "resolve_lane_routes.py"])
    expected_routes_command = {
        "version": ROUTES_COMMAND_VERSION,
        "source_sha256": routes_hashes,
        "command_hash": canonical_json_sha256(routes_hashes),
        "semantic_hash_scope": "schema_version, graph semantic hash, decisions, routes, proofs",
    }
    if routes.get("command") != expected_routes_command:
        issues.append("lane route producer provenance mismatch")
    expected_route_source = {
        "inpx_path": Path(str(network_evidence.get("path", ""))).name,
        "input_sha256": network_hash,
        "graph_schema_version": graph.get("schema_version"),
        "graph_semantic_sha256": graph.get("semantic_sha256"),
        "graph_input_sha256": network_hash,
    }
    if routes.get("source") != expected_route_source:
        issues.append("lane route/preflight/graph binding mismatch")
    return issues


def _replay_topology(
    workspace_root: Path,
    preflight: Mapping[str, Any],
    graph: Mapping[str, Any],
    routes: Mapping[str, Any],
    topology: Mapping[str, Any],
    graph_path: Path,
    routes_path: Path,
) -> list[dict[str, Any]]:
    issues: list[str] = []
    artifacts = preflight.get("artifacts", {})
    paths: dict[str, Path] = {}
    for name in REQUIRED_A2_PREFLIGHT_ARTIFACTS:
        try:
            raw_path = artifacts[name]["path"]
            path = Path(str(raw_path)).resolve(strict=True)
            path.relative_to(workspace_root)
            paths[name] = path
        except (KeyError, OSError, TypeError, ValueError) as exc:
            issues.append(f"preflight {name} path unavailable: {exc}")
    if issues:
        return [_reason("topology_trust_mismatch", sorted(set(issues)))]
    try:
        ownership = strict_load_json(
            paths["link_assignment"], max_bytes=MAX_TOPOLOGY_BYTES
        )
        adjacency = strict_load_json(
            paths["adjacency"], max_bytes=MAX_TOPOLOGY_BYTES
        )
        capacity = strict_load_json(
            paths["storage_capacity"], max_bytes=MAX_TOPOLOGY_BYTES
        )
        if not all(isinstance(value, dict) for value in (ownership, adjacency, capacity)):
            raise ValueError("A2 evidence roots must be objects")
        source_hashes = {
            "lane_graph": file_sha256(graph_path),
            "lane_route_proofs": file_sha256(routes_path),
            "ownership_evidence": file_sha256(paths["link_assignment"]),
            "adjacency_evidence": file_sha256(paths["adjacency"]),
            "capacity_evidence": file_sha256(paths["storage_capacity"]),
        }
        production_paths = {
            name: DEFAULT_PATHS[name]
            for name in REQUIRED_A2_PREFLIGHT_ARTIFACTS
        }
        is_production = all(
            workspace_relative_path(workspace_root, paths[name]) == expected
            for name, expected in production_paths.items()
        )
        replayed = compile_physical_stock_topology(
            dict(graph),
            dict(routes),
            ownership,
            adjacency,
            capacity,
            source_file_sha256=source_hashes,
            expected_evidence_hashes=(
                None if is_production else evidence_identity_hashes(ownership, adjacency, capacity)
            ),
            require_production_partition=is_production,
        )
    except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
        return [_reason("topology_trust_mismatch", f"A2 replay failed: {exc}")]
    if replayed.get("status") != "PASS":
        issues.append(f"A2 replay status is {replayed.get('status')}: {replayed.get('reasons')}")
    if replayed != topology:
        issues.append("topology differs from independent A2 replay")
    return [_reason("topology_trust_mismatch", sorted(set(issues)))] if issues else []


def _a1_nested_record_issues(
    graph: Mapping[str, Any], routes: Mapping[str, Any]
) -> tuple[list[str], list[str]]:
    graph_issues: list[str] = []
    route_issues: list[str] = []
    for field in ("links", "nodes", "edges", "connectors", "signal_heads"):
        records = graph.get(field)
        if not isinstance(records, list):
            graph_issues.append(f"lane graph {field} must be an array")
            continue
        bad = [index for index, item in enumerate(records) if not isinstance(item, dict)]
        if bad:
            graph_issues.append(f"lane graph {field} non-object records {bad}")
    for field in ("links", "connectors"):
        parents = graph.get(field)
        for index, parent in enumerate(parents if isinstance(parents, list) else []):
            if not isinstance(parent, dict):
                continue
            lanes = parent.get("lanes")
            if not isinstance(lanes, list) or any(
                not isinstance(item, dict) for item in lanes
            ):
                graph_issues.append(f"lane graph {field}[{index}].lanes malformed")
            if field == "connectors":
                mappings = parent.get("lane_mapping")
                if not isinstance(mappings, list) or any(
                    not isinstance(item, dict) for item in mappings
                ):
                    graph_issues.append(
                        f"lane graph connectors[{index}].lane_mapping malformed"
                    )
    for field in ("routing_decisions", "routes", "proofs"):
        records = routes.get(field)
        if not isinstance(records, list):
            route_issues.append(f"lane routes {field} must be an array")
            continue
        bad = [index for index, item in enumerate(records) if not isinstance(item, dict)]
        if bad:
            route_issues.append(f"lane routes {field} non-object records {bad}")
    return graph_issues, route_issues


def validate_source_bundle(
    workspace_root: Path,
    preflight_path: Path,
    graph_path: Path,
    routes_path: Path,
    topology_path: Path,
) -> tuple[
    Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any],
    ValidatedPhysicalTopology | None, dict[str, str], list[dict[str, Any]],
]:
    reasons: list[dict[str, Any]] = []
    loaded: list[Mapping[str, Any]] = []
    for label, path in (
        ("preflight", preflight_path),
        ("lane_graph", graph_path),
        ("lane_route_proofs", routes_path),
        ("physical_stock_topology", topology_path),
    ):
        try:
            limit = MAX_PREFLIGHT_BYTES if label == "preflight" else MAX_TOPOLOGY_BYTES
            value = strict_load_json(path, max_bytes=limit)
            if not isinstance(value, dict):
                raise ValueError("root must be an object")
            loaded.append(value)
        except (OSError, ValueError) as exc:
            reasons.append(_reason("topology_trust_mismatch", f"{label}: {exc}"))
            loaded.append({})
    preflight, graph, routes, topology = loaded
    if preflight:
        try:
            reasons.extend(validate_preflight_artifact(preflight, workspace_root))
        except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
            reasons.append(_reason(
                "topology_trust_mismatch",
                f"preflight nested contract malformed: {type(exc).__name__}: {exc}",
            ))
    graph_record_issues, route_record_issues = _a1_nested_record_issues(graph, routes)
    if graph_record_issues:
        reasons.append(_reason("topology_trust_mismatch", sorted(graph_record_issues)))
    if graph:
        if not graph_record_issues:
            try:
                graph_reasons = validate_lane_graph_artifact(dict(graph))
                if graph_reasons:
                    reasons.append(_reason(
                        "topology_trust_mismatch", {"lane_graph": graph_reasons}
                    ))
            except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
                reasons.append(_reason(
                    "topology_trust_mismatch",
                    f"lane graph nested contract malformed: {type(exc).__name__}: {exc}",
                ))
    if route_record_issues:
        reasons.append(_reason("topology_trust_mismatch", sorted(route_record_issues)))
    if routes and graph and not graph_record_issues and not route_record_issues:
        try:
            route_reasons = validate_route_proofs_artifact(dict(routes), dict(graph))
            if route_reasons:
                reasons.append(_reason(
                    "topology_trust_mismatch", {"lane_route_proofs": route_reasons}
                ))
        except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
            reasons.append(_reason(
                "topology_trust_mismatch",
                f"lane routes nested contract malformed: {type(exc).__name__}: {exc}",
            ))
    validated_topology: ValidatedPhysicalTopology | None = None
    if topology:
        try:
            validated_topology = validate_physical_stock_topology(topology, graph or None)
        except TopologyValidationError as exc:
            reasons.extend(dict(item) for item in exc.reasons)
        except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
            reasons.append(_reason(
                "topology_structure_invalid",
                f"topology nested contract malformed: {type(exc).__name__}: {exc}",
            ))
    topology_sources = topology.get("source_artifacts", {}) if topology else {}
    topology_sources = topology_sources if isinstance(topology_sources, dict) else {}
    if topology and graph and topology_sources.get(
        "lane_graph_semantic_sha256"
    ) != graph.get("semantic_sha256"):
        reasons.append(_reason("topology_trust_mismatch", "topology/graph semantic binding mismatch"))
    if topology and routes and topology_sources.get(
        "lane_route_proofs_semantic_sha256"
    ) != routes.get("semantic_sha256"):
        reasons.append(_reason("topology_trust_mismatch", "topology/routes semantic binding mismatch"))
    if preflight and graph and routes and not graph_record_issues and not route_record_issues:
        try:
            a1_issues = _validate_a1_provenance(preflight, graph, routes)
            if a1_issues:
                reasons.append(_reason("topology_trust_mismatch", sorted(set(a1_issues))))
        except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
            reasons.append(_reason(
                "topology_trust_mismatch",
                f"A1 provenance malformed: {type(exc).__name__}: {exc}",
            ))
    if (
        preflight
        and graph
        and routes
        and topology
        and not graph_record_issues
        and not route_record_issues
    ):
        reasons.extend(
            _replay_topology(
                workspace_root,
                preflight,
                graph,
                routes,
                topology,
                graph_path,
                routes_path,
            )
        )

    hashes = {
        "preflight_file_sha256": _safe_file_hash(
            preflight_path, max_bytes=MAX_PREFLIGHT_BYTES
        ),
        "lane_graph_file_sha256": _safe_file_hash(
            graph_path, max_bytes=MAX_TOPOLOGY_BYTES
        ),
        "lane_graph_semantic_sha256": str(graph.get("semantic_sha256", "")),
        "lane_route_proofs_file_sha256": _safe_file_hash(
            routes_path, max_bytes=MAX_TOPOLOGY_BYTES
        ),
        "lane_route_proofs_semantic_sha256": str(routes.get("semantic_sha256", "")),
        "topology_file_sha256": _safe_file_hash(
            topology_path, max_bytes=MAX_TOPOLOGY_BYTES
        ),
        "topology_semantic_sha256": str(topology.get("semantic_sha256", "")),
    }
    if any(SHA256_PATTERN.fullmatch(value) is None for value in hashes.values()):
        reasons.append(_reason("topology_trust_mismatch", "missing or invalid source hash"))
    return preflight, graph, routes, topology, validated_topology, hashes, reasons


def build_approval_artifact(
    *,
    workspace_root: Path,
    artifact_path: Path,
    preflight_path: Path,
    graph_path: Path,
    routes_path: Path,
    topology_path: Path,
) -> dict[str, Any]:
    preflight, graph, routes, topology, _, hashes, reasons = validate_source_bundle(
        workspace_root, preflight_path, graph_path, routes_path, topology_path
    )
    source_inputs = {
        "preflight": {
            "path": workspace_relative_path(workspace_root, preflight_path),
            "file_sha256": hashes["preflight_file_sha256"],
        },
        "lane_graph": {
            "path": workspace_relative_path(workspace_root, graph_path),
            "file_sha256": hashes["lane_graph_file_sha256"],
            "semantic_sha256": hashes["lane_graph_semantic_sha256"],
        },
        "lane_route_proofs": {
            "path": workspace_relative_path(workspace_root, routes_path),
            "file_sha256": hashes["lane_route_proofs_file_sha256"],
            "semantic_sha256": hashes["lane_route_proofs_semantic_sha256"],
        },
        "physical_stock_topology": {
            "path": workspace_relative_path(workspace_root, topology_path),
            "file_sha256": hashes["topology_file_sha256"],
            "semantic_sha256": hashes["topology_semantic_sha256"],
        },
    }
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "input_hashes": hashes,
        "command_version": {},
        "status": "FAIL" if reasons else "PASS",
        "reasons": sorted(reasons, key=lambda item: (item["code"], repr(item.get("detail")))),
        "sample_dimensions": {
            "stocks": len(topology.get("stocks", [])) if isinstance(topology, dict) else 0,
            "lanes": len(graph.get("nodes", [])) if isinstance(graph, dict) else 0,
        },
        "units": dict(UNITS),
        "downstream_consumers": list(DOWNSTREAM_CONSUMERS),
        "workspace_root_relative_to_artifact": "..",
        "source_inputs": source_inputs,
        "approved_topology": {
            "topology_path": source_inputs["physical_stock_topology"]["path"],
            "topology_file_sha256": hashes["topology_file_sha256"],
            "topology_semantic_sha256": hashes["topology_semantic_sha256"],
        },
    }
    artifact["semantic_sha256"] = canonical_json_sha256(semantic_payload(artifact))
    return artifact


def validate_approval_artifact(
    approval_path: str | Path,
    *,
    workspace_root: str | Path | None = None,
    supplied_topology_path: str | Path | None = None,
) -> ValidatedApprovalBundle:
    path = Path(approval_path).resolve(strict=True)
    approval = strict_load_json(path, max_bytes=MAX_APPROVAL_BYTES)
    reasons: list[dict[str, Any]] = []
    if not isinstance(approval, dict):
        raise ApprovalValidationError([_reason("topology_trust_mismatch", "approval root is not an object")])
    if set(approval) != TOP_LEVEL_FIELDS:
        reasons.append(_reason("topology_trust_mismatch", "approval shape mismatch"))
    if approval.get("schema_version") != SCHEMA_VERSION:
        reasons.append(_reason("topology_trust_mismatch", "approval schema mismatch"))
    if approval.get("status") != "PASS" or approval.get("reasons") != []:
        reasons.append(_reason("topology_trust_mismatch", "approval status/reasons mismatch"))
    if approval.get("command_version") != {}:
        reasons.append(_reason("topology_trust_mismatch", "approval command_version mismatch"))
    if approval.get("units") != UNITS or approval.get("downstream_consumers") != DOWNSTREAM_CONSUMERS:
        reasons.append(_reason("topology_trust_mismatch", "approval global metadata mismatch"))
    try:
        semantic = canonical_json_sha256(semantic_payload(approval))
    except (KeyError, TypeError, ValueError) as exc:
        reasons.append(_reason("topology_trust_mismatch", f"invalid approval semantic payload: {exc}"))
        semantic = ""
    if approval.get("semantic_sha256") != semantic:
        reasons.append(_reason("topology_trust_mismatch", "approval semantic hash mismatch"))

    root_declaration = approval.get("workspace_root_relative_to_artifact")
    if root_declaration != "..":
        reasons.append(_reason("topology_trust_mismatch", "invalid approval workspace root declaration"))
        root = path.parent
    else:
        try:
            root = (path.parent / root_declaration).resolve(strict=True)
        except OSError as exc:
            reasons.append(_reason("topology_trust_mismatch", f"unavailable workspace root: {exc}"))
            root = path.parent
    if workspace_root is not None:
        expected_root = Path(workspace_root).resolve(strict=True)
        if root != expected_root:
            reasons.append(_reason("topology_trust_mismatch", "approval workspace root mismatch"))

    source_inputs = approval.get("source_inputs")
    expected_source_keys = {
        "preflight", "lane_graph", "lane_route_proofs", "physical_stock_topology"
    }
    paths: dict[str, Path] = {}
    if not isinstance(source_inputs, dict) or set(source_inputs) != expected_source_keys:
        reasons.append(_reason("topology_trust_mismatch", "approval source_inputs shape mismatch"))
        source_inputs = {}
    for key in sorted(expected_source_keys):
        record = source_inputs.get(key)
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            reasons.append(_reason("topology_trust_mismatch", f"invalid source input {key}"))
            continue
        try:
            paths[key] = resolve_contained_path(root, record["path"])
        except (OSError, ValueError) as exc:
            reasons.append(_reason("topology_trust_mismatch", f"{key} path: {exc}"))
    if len(paths) != len(expected_source_keys):
        raise ApprovalValidationError(reasons)

    preflight, graph, routes, topology, validated, hashes, source_reasons = validate_source_bundle(
        root,
        paths["preflight"],
        paths["lane_graph"],
        paths["lane_route_proofs"],
        paths["physical_stock_topology"],
    )
    reasons.extend(source_reasons)
    if approval.get("input_hashes") != hashes or set(approval.get("input_hashes", {})) != INPUT_HASH_NAMES:
        reasons.append(_reason("topology_trust_mismatch", "approval input_hashes mismatch"))
    expected_sources = {
        "preflight": {"path": workspace_relative_path(root, paths["preflight"]), "file_sha256": hashes["preflight_file_sha256"]},
        "lane_graph": {"path": workspace_relative_path(root, paths["lane_graph"]), "file_sha256": hashes["lane_graph_file_sha256"], "semantic_sha256": hashes["lane_graph_semantic_sha256"]},
        "lane_route_proofs": {"path": workspace_relative_path(root, paths["lane_route_proofs"]), "file_sha256": hashes["lane_route_proofs_file_sha256"], "semantic_sha256": hashes["lane_route_proofs_semantic_sha256"]},
        "physical_stock_topology": {"path": workspace_relative_path(root, paths["physical_stock_topology"]), "file_sha256": hashes["topology_file_sha256"], "semantic_sha256": hashes["topology_semantic_sha256"]},
    }
    if approval.get("source_inputs") != expected_sources:
        reasons.append(_reason("topology_trust_mismatch", "approval source binding mismatch"))
    expected_binding = {
        "topology_path": expected_sources["physical_stock_topology"]["path"],
        "topology_file_sha256": hashes["topology_file_sha256"],
        "topology_semantic_sha256": hashes["topology_semantic_sha256"],
    }
    if approval.get("approved_topology") != expected_binding:
        reasons.append(_reason("topology_trust_mismatch", "approved_topology binding mismatch"))
    expected_dimensions = {"stocks": len(topology.get("stocks", [])), "lanes": len(graph.get("nodes", []))}
    if approval.get("sample_dimensions") != expected_dimensions:
        reasons.append(_reason("topology_trust_mismatch", "approval sample_dimensions mismatch"))
    if supplied_topology_path is not None:
        try:
            supplied = Path(supplied_topology_path).resolve(strict=True)
            supplied.relative_to(root)
            if supplied != paths["physical_stock_topology"]:
                reasons.append(_reason("topology_trust_mismatch", "separately supplied topology path mismatch"))
        except (OSError, ValueError) as exc:
            reasons.append(_reason("topology_trust_mismatch", f"invalid separately supplied topology: {exc}"))
    if validated is None and not reasons:
        reasons.append(_reason("topology_structure_invalid", "validated topology unavailable"))
    if reasons:
        raise ApprovalValidationError(reasons)
    return ValidatedApprovalBundle(
        workspace_root=root,
        approval_path=path,
        approval=approval,
        approval_file_sha256=file_sha256(path),
        preflight_path=paths["preflight"],
        graph_path=paths["lane_graph"],
        routes_path=paths["lane_route_proofs"],
        topology_path=paths["physical_stock_topology"],
        preflight=preflight,
        graph=graph,
        routes=routes,
        topology=topology,
        validated_topology=validated,
    )


def _resolve_cli_input(root: Path, value: Path) -> Path:
    candidate = value if value.is_absolute() else root / value
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    return resolved


def _validation_result(
    *,
    workspace_root: Path,
    bundle: ValidatedApprovalBundle | None,
    reasons: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    passed = bundle is not None and not reasons
    return {
        "schema_version": VALIDATION_RESULT_SCHEMA_VERSION,
        "status": "PASS" if passed else "FAIL",
        "reasons": [] if passed else [dict(item) for item in reasons],
        "workspace_root": str(workspace_root),
        "approval_path": str(bundle.approval_path) if bundle is not None else "",
        "approval_file_sha256": (
            bundle.approval_file_sha256 if bundle is not None else ""
        ),
        "preflight_path": str(bundle.preflight_path) if bundle is not None else "",
        "preflight_file_sha256": (
            file_sha256(bundle.preflight_path) if bundle is not None else ""
        ),
        "topology_path": str(bundle.topology_path) if bundle is not None else "",
        "topology_file_sha256": (
            file_sha256(bundle.topology_path) if bundle is not None else ""
        ),
        "topology_semantic_sha256": (
            bundle.validated_topology.semantic_sha256 if bundle is not None else ""
        ),
    }


def _validate_existing_cli(args: argparse.Namespace) -> int:
    try:
        root = args.workspace_root.resolve(strict=True)
        if any(
            value is not None
            for value in (
                args.preflight,
                args.graph,
                args.routes,
                args.topology,
                args.out,
            )
        ):
            raise ValueError("build arguments are forbidden in validate-existing mode")
        if args.supplied_topology is None:
            raise ValueError("supplied-topology is required in validate-existing mode")
        bundle = validate_approval_artifact(
            args.validate_existing,
            workspace_root=root,
            supplied_topology_path=args.supplied_topology,
        )
        result = _validation_result(
            workspace_root=root, bundle=bundle, reasons=[]
        )
    except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
        try:
            root = args.workspace_root.resolve(strict=True)
        except FAIL_CLOSED_INPUT_EXCEPTIONS:
            root = args.workspace_root
        reasons = (
            exc.reasons
            if isinstance(exc, ApprovalValidationError)
            else (_reason("topology_trust_mismatch", f"{type(exc).__name__}: {exc}"),)
        )
        result = _validation_result(
            workspace_root=root, bundle=None, reasons=reasons
        )
    wire = validation_result_wire_bytes(result)
    if len(wire) > MAX_VALIDATION_RESULT_BYTES:
        result = _validation_result(
            workspace_root=root,
            bundle=None,
            reasons=(
                _reason(
                    "topology_trust_mismatch",
                    "validation result exceeds worker wire byte limit",
                ),
            ),
        )
        wire = validation_result_wire_bytes(result)
    sys.stdout.buffer.write(wire)
    return 0 if result["status"] == "PASS" else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--graph", type=Path)
    parser.add_argument("--routes", type=Path)
    parser.add_argument("--topology", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--validate-existing", type=Path)
    parser.add_argument("--supplied-topology", type=Path)
    args = parser.parse_args(argv)

    if args.validate_existing is not None:
        return _validate_existing_cli(args)
    if args.supplied_topology is not None:
        parser.error("supplied-topology requires validate-existing mode")
    missing = [
        name
        for name in ("preflight", "graph", "routes", "topology", "out")
        if getattr(args, name) is None
    ]
    if missing:
        parser.error("missing build arguments: " + ", ".join(missing))

    try:
        root = args.workspace_root.resolve(strict=True)
        output = args.out if args.out.is_absolute() else root / args.out
        output = output.resolve(strict=False)
        output.relative_to(root)
        if output.parent != root / "outputs" or output.name != "topology_approval_v2_1.json":
            raise ValueError("approval output must be outputs/topology_approval_v2_1.json")
        preflight_path = _resolve_cli_input(root, args.preflight)
        graph_path = _resolve_cli_input(root, args.graph)
        routes_path = _resolve_cli_input(root, args.routes)
        topology_path = _resolve_cli_input(root, args.topology)
        artifact = build_approval_artifact(
            workspace_root=root,
            artifact_path=output,
            preflight_path=preflight_path,
            graph_path=graph_path,
            routes_path=routes_path,
            topology_path=topology_path,
        )
    except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
        try:
            root = args.workspace_root.resolve(strict=True)
            output = args.out if args.out.is_absolute() else root / args.out
            output = output.resolve(strict=False)
            output.relative_to(root)
            blank = {key: "" for key in INPUT_HASH_NAMES}
            artifact = {
                "schema_version": SCHEMA_VERSION,
                "input_hashes": blank,
                "command_version": {},
                "status": "FAIL",
                "reasons": [_reason("topology_trust_mismatch", str(exc))],
                "sample_dimensions": {"stocks": 0, "lanes": 0},
                "units": dict(UNITS),
                "downstream_consumers": list(DOWNSTREAM_CONSUMERS),
                "workspace_root_relative_to_artifact": "..",
                "source_inputs": {
                    "preflight": {"path": "", "file_sha256": ""},
                    "lane_graph": {"path": "", "file_sha256": "", "semantic_sha256": ""},
                    "lane_route_proofs": {"path": "", "file_sha256": "", "semantic_sha256": ""},
                    "physical_stock_topology": {"path": "", "file_sha256": "", "semantic_sha256": ""},
                },
                "approved_topology": {
                    "topology_path": "",
                    "topology_file_sha256": "",
                    "topology_semantic_sha256": "",
                },
            }
            artifact["semantic_sha256"] = canonical_json_sha256(semantic_payload(artifact))
        except FAIL_CLOSED_INPUT_EXCEPTIONS:
            return 1
    try:
        atomic_write_json(output, artifact)
    except OSError:
        return 1
    print(f"status={artifact['status']} hash={artifact['semantic_sha256']}")
    return 0 if artifact["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
