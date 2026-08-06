"""Validate and project the exact state-manifest-v2.1 snapshot universe."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import re
import sys
import time
from typing import Any, Mapping, Sequence


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
PLANT_ROOT = REPO_ROOT / "plant"
for search_root in (SCRIPT_ROOT, PLANT_ROOT):
    if str(search_root) not in sys.path:
        sys.path.insert(0, str(search_root))

from approve_physical_stock_topology import (  # noqa: E402
    ApprovalValidationError,
    ValidatedApprovalBundle,
    validate_approval_artifact,
)
from build_state_manifest_v2_1 import (  # noqa: E402
    DOWNSTREAM_CONSUMERS as MANIFEST_DOWNSTREAM_CONSUMERS,
    MANIFEST_FIELDS,
    MANIFEST_INPUT_HASH_NAMES,
    SCHEMA_VERSION as MANIFEST_SCHEMA_VERSION,
    STATE_ENTRY_FIELDS,
    UNITS as MANIFEST_UNITS,
    StateManifestValidationError,
    expected_approved_topology_binding,
    manifest_semantic_payload,
    state_set_semantic_payload,
    validate_state_run_binding,
    validate_state_selection,
)
from src.vissim_strict.physical_projection import (  # noqa: E402
    ProjectionError,
    atomic_write_json,
    failure_projection_ledger,
    file_sha256,
    normalize_vehicle_records,
    project_vehicle_records,
    projection_sidecar_path,
    resolve_contained_path,
    strict_load_json,
    workspace_relative_path,
    write_projection_sidecar,
)
from src.vissim_strict.run_evidence import (  # noqa: E402
    MAX_RUN_MANIFEST_BYTES,
    RunManifestValidationError,
    validate_run_manifest,
)
from src.vissim_strict.topology import canonical_json_sha256  # noqa: E402


SCHEMA_VERSION = "initial-projection-audit-v2.1"
UNITS = {"sim_sec": "s", "wall_time": "s", "size": "byte"}
DOWNSTREAM_CONSUMERS = ["B1a readiness review"]
FAIL_CLOSED_INPUT_EXCEPTIONS = (
    AttributeError,
    IndexError,
    KeyError,
    OSError,
    OverflowError,
    TypeError,
    ValueError,
)
LIVE_EVIDENCE_SCHEMA_VERSION = "projection-live-evidence-v2.1"
LIVE_EVIDENCE_UNITS = {
    "sim_sec": "s",
    "wall_time": "s",
    "size": "byte",
    "position": "m",
    "speed": "km/h",
}
LIVE_EVIDENCE_DOWNSTREAM_CONSUMERS = ["validate_state_projection_v2_1"]
LIVE_EVIDENCE_FIELDS = {
    "schema_version",
    "input_hashes",
    "command_version",
    "status",
    "reasons",
    "sample_dimensions",
    "units",
    "downstream_consumers",
    "states",
    "performance",
    "semantic_sha256",
}
LIVE_STATE_FIELDS = {
    "state_path",
    "state_file_sha256",
    "run_id",
    "sim_sec",
    "capture_source",
    "vissim_version",
    "supported_vissim_version",
    "collection_count_before",
    "collection_count_after",
    "raw_record_count",
    "assigned_count",
    "stock_total",
    "global_residual",
    "raw_attribute_samples",
    "runner_utf8_without_bom",
    "public_projector_parsed",
}
RAW_ATTRIBUTE_SAMPLE_FIELDS = {
    "com_key",
    "no_value",
    "lane_raw",
    "parsed_link_no",
    "parsed_lane_no",
    "position_value",
    "speed_value",
}
PERFORMANCE_FIELDS = {
    "qualification_record_count",
    "state_envelope_size_bytes",
    "sidecar_size_bytes",
    "action_reference_size_bytes",
    "decision_budget_sec",
    "timing_scope",
    "combined_wall_sec_samples",
    "p95_wall_sec",
}
LIVE_INPUT_HASH_NAMES = {
    "state_manifest_file_sha256",
    "state_manifest_semantic_sha256",
    "state_set_semantic_sha256",
    "approving_manifest_sha256",
    "topology_file_sha256",
    "topology_semantic_sha256",
}
LANE_ATTRIBUTE_PATTERN = re.compile(r"^[ \t]*([1-9][0-9]*)-([1-9][0-9]*)[ \t]*$")
MAX_VISSIM_ID = 2_147_483_647


@dataclass(frozen=True)
class ValidatedStateManifest:
    workspace_root: Path
    manifest_path: Path
    manifest: Mapping[str, Any]
    selection_path: Path
    selection: Mapping[str, Any]
    bundle: ValidatedApprovalBundle
    topology_path: Path


def _reason(code: str, detail: Any) -> dict[str, Any]:
    return {"code": code, "detail": detail}


def _exception_reasons(exc: BaseException) -> list[dict[str, Any]]:
    reasons = getattr(exc, "reasons", None)
    if isinstance(reasons, (list, tuple)) and reasons and all(
        isinstance(item, Mapping) for item in reasons
    ):
        return [dict(item) for item in reasons]
    return [_reason(
        "topology_trust_mismatch",
        f"{type(exc).__name__}: {exc}",
    )]


def audit_semantic_payload(audit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: audit[key]
        for key in (
            "schema_version",
            "input_hashes",
            "command_version",
            "status",
            "reasons",
            "sample_dimensions",
            "units",
            "downstream_consumers",
            "live_gates",
            "states",
        )
    }


def live_evidence_semantic_payload(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: evidence[key]
        for key in (
            "schema_version",
            "input_hashes",
            "command_version",
            "sample_dimensions",
            "units",
            "downstream_consumers",
            "states",
            "performance",
        )
    }


def _finite_nonnegative(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return False
    return math.isfinite(number) and number >= 0.0


def _entry_sort_key(entry: Mapping[str, Any]) -> tuple[str, tuple[int, Any], str]:
    sim_sec = entry.get("sim_sec", -1.0)
    numeric = isinstance(sim_sec, (int, float)) and not isinstance(sim_sec, bool)
    return (
        str(entry.get("run_id", "")),
        (0, sim_sec) if numeric else (1, str(sim_sec)),
        str(entry.get("state_path", "")),
    )


def validate_manifest_contract(
    manifest_path: Path,
    supplied_topology_path: Path,
) -> ValidatedStateManifest:
    reasons: list[dict[str, Any]] = []
    manifest = strict_load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise StateManifestValidationError([_reason("aggregate_mismatch", "manifest root is not an object")])
    if set(manifest) != MANIFEST_FIELDS:
        reasons.append(_reason("aggregate_mismatch", "state manifest shape mismatch"))
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        reasons.append(_reason("aggregate_mismatch", "state manifest schema mismatch"))
    if manifest.get("status") != "PASS" or manifest.get("reasons") != []:
        reasons.append(_reason("aggregate_mismatch", "state manifest status/reasons mismatch"))
    if manifest.get("base_dir") != "..":
        reasons.append(_reason("topology_trust_mismatch", "state manifest base_dir must be '..'"))
    workspace_root = manifest_path.parent.parent.resolve(strict=True)
    try:
        declared_root = (manifest_path.parent / str(manifest.get("base_dir", ""))).resolve(strict=True)
        if declared_root != workspace_root:
            reasons.append(_reason("topology_trust_mismatch", "state manifest base_dir mismatch"))
    except OSError as exc:
        reasons.append(_reason("topology_trust_mismatch", f"invalid base_dir: {exc}"))
    if manifest.get("units") != MANIFEST_UNITS or manifest.get(
        "downstream_consumers"
    ) != MANIFEST_DOWNSTREAM_CONSUMERS:
        reasons.append(_reason("aggregate_mismatch", "state manifest global metadata mismatch"))
    try:
        semantic = canonical_json_sha256(manifest_semantic_payload(manifest))
    except (KeyError, TypeError, ValueError) as exc:
        reasons.append(_reason("aggregate_mismatch", f"invalid manifest semantic payload: {exc}"))
        semantic = ""
    if manifest.get("semantic_sha256") != semantic:
        reasons.append(_reason("aggregate_mismatch", "state manifest semantic hash mismatch"))
    input_hashes = manifest.get("input_hashes")
    if not isinstance(input_hashes, dict) or set(input_hashes) != MANIFEST_INPUT_HASH_NAMES:
        reasons.append(_reason("aggregate_mismatch", "state manifest input_hashes shape mismatch"))
        input_hashes = {}

    states = manifest.get("states")
    if not isinstance(states, list):
        reasons.append(_reason("aggregate_mismatch", "manifest states must be an array"))
        states = []
    state_paths: set[Path] = set()
    identities: set[tuple[str, float]] = set()
    normalized_states: list[dict[str, Any]] = []
    for index, entry in enumerate(states):
        if not isinstance(entry, dict) or set(entry) != STATE_ENTRY_FIELDS:
            reasons.append(_reason("aggregate_mismatch", f"state entry[{index}] shape mismatch"))
            continue
        try:
            state_path = resolve_contained_path(workspace_root, entry["state_path"])
            run_path = resolve_contained_path(workspace_root, entry["run_manifest_path"])
            sidecar_path = resolve_contained_path(
                workspace_root,
                entry["projection_sidecar_path"],
                must_exist=False,
            )
        except (OSError, ValueError, KeyError) as exc:
            reasons.append(_reason("topology_trust_mismatch", f"state entry[{index}] path: {exc}"))
            continue
        if sidecar_path != projection_sidecar_path(state_path).resolve(strict=False):
            reasons.append(_reason("topology_trust_mismatch", f"state entry[{index}] sidecar name mismatch"))
        if state_path in state_paths:
            reasons.append(_reason("aggregate_mismatch", f"duplicate state path {state_path}"))
        state_paths.add(state_path)
        if not _finite_nonnegative(entry.get("sim_sec")):
            reasons.append(_reason("invalid_numeric_value", f"state entry[{index}] invalid sim_sec"))
            continue
        identity = (str(entry.get("run_id", "")), float(entry["sim_sec"]))
        if identity in identities:
            reasons.append(_reason("duplicate_vehicle_in_snapshot", f"duplicate manifest run/time {identity}"))
        identities.add(identity)
        if not isinstance(entry.get("required_vehicle_records"), bool):
            reasons.append(_reason("aggregate_mismatch", f"state entry[{index}] invalid policy flag"))
        normalized_states.append(dict(entry))
    if states != sorted(normalized_states, key=_entry_sort_key):
        reasons.append(_reason("aggregate_mismatch", "manifest states are not canonical"))
    if manifest.get("sample_dimensions") != {"states": len(states)}:
        reasons.append(_reason("aggregate_mismatch", "manifest sample_dimensions mismatch"))
    try:
        state_set_hash = canonical_json_sha256(state_set_semantic_payload(states))
    except (KeyError, TypeError, ValueError) as exc:
        reasons.append(_reason("aggregate_mismatch", f"invalid state-set payload: {exc}"))
        state_set_hash = ""
    if input_hashes.get("state_set_semantic_sha256") != state_set_hash:
        reasons.append(_reason("aggregate_mismatch", "state-set semantic hash mismatch"))

    selection_binding = manifest.get("state_selection")
    if not isinstance(selection_binding, dict) or set(selection_binding) != {
        "path", "file_sha256", "semantic_sha256", "campaign_id", "expected_entry_count"
    }:
        reasons.append(_reason("aggregate_mismatch", "state_selection binding shape mismatch"))
        selection_binding = {}
    try:
        selection_path = resolve_contained_path(workspace_root, selection_binding["path"])
        selection = strict_load_json(selection_path)
        selected_entries = validate_state_selection(selection, workspace_root=workspace_root)
        selection_file_hash = file_sha256(selection_path)
    except (OSError, ValueError, KeyError, StateManifestValidationError) as exc:
        detail = [dict(item) for item in getattr(exc, "reasons", ())] or str(exc)
        reasons.append(_reason("aggregate_mismatch", {"state_selection": detail}))
        selection_path = manifest_path
        selection = {}
        selected_entries = ()
        selection_file_hash = ""
    expected_selection_binding = {
        "path": workspace_relative_path(workspace_root, selection_path),
        "file_sha256": selection_file_hash,
        "semantic_sha256": selection.get("semantic_sha256", ""),
        "campaign_id": selection.get("campaign_id", ""),
        "expected_entry_count": selection.get("expected_entry_count", 0),
    }
    if selection_binding != expected_selection_binding:
        reasons.append(_reason("aggregate_mismatch", "state_selection binding mismatch"))
    if input_hashes.get("state_selection_file_sha256") != selection_file_hash or input_hashes.get(
        "state_selection_semantic_sha256"
    ) != selection.get("semantic_sha256"):
        reasons.append(_reason("aggregate_mismatch", "selection input hash mismatch"))
    expected_selected_from_manifest = [
        {
            "run_manifest_path": entry["run_manifest_path"],
            "state_path": entry["state_path"],
            "run_id": entry["run_id"],
            "sim_sec": entry["sim_sec"],
            "required_vehicle_records": entry["required_vehicle_records"],
        }
        for entry in states
        if isinstance(entry, dict) and STATE_ENTRY_FIELDS.issubset(entry)
    ]
    if list(selected_entries) != expected_selected_from_manifest:
        reasons.append(_reason("aggregate_mismatch", "selection/manifest entry universe mismatch"))

    approved = manifest.get("approved_topology")
    if not isinstance(approved, dict):
        reasons.append(_reason("topology_trust_mismatch", "approved_topology must be an object"))
        approved = {}
    try:
        approval_path = resolve_contained_path(workspace_root, approved["approving_manifest_path"])
        topology_path = resolve_contained_path(workspace_root, approved["topology_path"])
        supplied = supplied_topology_path.resolve(strict=True)
        supplied.relative_to(workspace_root)
        if supplied != topology_path:
            reasons.append(_reason("topology_trust_mismatch", "CLI topology path differs from manifest"))
        bundle = validate_approval_artifact(
            approval_path,
            workspace_root=workspace_root,
            supplied_topology_path=supplied,
        )
    except (OSError, ValueError, KeyError, ApprovalValidationError) as exc:
        detail = [dict(item) for item in getattr(exc, "reasons", ())] or str(exc)
        reasons.append(_reason("topology_trust_mismatch", {"approval": detail}))
        bundle = None
        topology_path = supplied_topology_path
    if bundle is not None:
        expected_approved = expected_approved_topology_binding(bundle)
        if approved != expected_approved:
            reasons.append(_reason("topology_trust_mismatch", "manifest approved_topology binding mismatch"))
        expected_hashes = {
            "approving_manifest_sha256": bundle.approval_file_sha256,
            "topology_file_sha256": file_sha256(bundle.topology_path),
            "topology_semantic_sha256": bundle.validated_topology.semantic_sha256,
        }
        for key, expected in expected_hashes.items():
            if input_hashes.get(key) != expected:
                reasons.append(_reason("topology_trust_mismatch", f"manifest {key} mismatch"))
    if reasons or bundle is None:
        raise StateManifestValidationError(reasons)
    return ValidatedStateManifest(
        workspace_root=workspace_root,
        manifest_path=manifest_path,
        manifest=manifest,
        selection_path=selection_path,
        selection=selection,
        bundle=bundle,
        topology_path=topology_path,
    )


def _process_state(
    validated: ValidatedStateManifest,
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    root = validated.workspace_root
    state_path = resolve_contained_path(root, entry["state_path"])
    run_manifest_path = resolve_contained_path(root, entry["run_manifest_path"])
    sidecar_path = resolve_contained_path(
        root, entry["projection_sidecar_path"], must_exist=False
    )
    started = time.perf_counter()
    state_hash = file_sha256(state_path)
    run_hash = file_sha256(run_manifest_path)
    hash_context = {
        "topology_file_sha256": file_sha256(validated.bundle.topology_path),
        "topology_semantic_sha256": validated.bundle.validated_topology.semantic_sha256,
        "approving_manifest_sha256": validated.bundle.approval_file_sha256,
        "state_file_sha256": state_hash,
        "vehicle_records_semantic_sha256": "",
    }
    reasons: list[dict[str, Any]] = []
    state: Mapping[str, Any] = {}
    try:
        state = strict_load_json(state_path)
        run_manifest = strict_load_json(
            run_manifest_path, max_bytes=MAX_RUN_MANIFEST_BYTES
        )
        if state_hash != entry["state_file_sha256"]:
            reasons.append(_reason("topology_trust_mismatch", "state file hash mismatch"))
        if run_hash != entry["run_manifest_sha256"]:
            reasons.append(_reason("topology_trust_mismatch", "run manifest file hash mismatch"))
        approved = expected_approved_topology_binding(validated.bundle)
        try:
            validate_run_manifest(
                run_manifest,
                workspace_root=root,
                expected_run_id=entry["run_id"],
                capture_time=float(entry["sim_sec"]),
                expected_approved_topology=approved,
            )
        except RunManifestValidationError as exc:
            reasons.extend(
                _reason("topology_trust_mismatch", issue) for issue in exc.issues
            )
        reasons.extend(
            _reason("topology_trust_mismatch", issue)
            for issue in validate_state_run_binding(
                state,
                workspace_root=root,
                state_path=state_path,
                run_manifest_path=run_manifest_path,
                run_manifest_sha256=run_hash,
                run_id=entry["run_id"],
                sim_sec=float(entry["sim_sec"]),
            )
        )
    except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
        reasons.append(_reason("topology_trust_mismatch", str(exc)))

    run_id = str(entry.get("run_id", ""))
    sim_sec = float(entry.get("sim_sec", 0.0))
    if "vehicle_records" not in state:
        status = (
            "FAIL"
            if reasons or entry["required_vehicle_records"]
            else "NOT_EVALUATED"
        )
        code = "aggregate_mismatch" if status == "FAIL" else "live_com_not_evaluated"
        reasons.append(_reason(code, "vehicle_records envelope absent"))
        ledger = failure_projection_ledger(
            status=status,
            reasons=reasons,
            hash_context=hash_context,
            run_id=run_id,
            sim_sec=sim_sec,
        )
    elif reasons:
        status = "FAIL"
        ledger = failure_projection_ledger(
            status="FAIL",
            reasons=reasons,
            hash_context=hash_context,
            run_id=run_id,
            sim_sec=sim_sec,
        )
    else:
        try:
            _, _, record_hash = normalize_vehicle_records(
                state, validated.bundle.validated_topology.tolerance_m
            )
            hash_context["vehicle_records_semantic_sha256"] = record_hash
            result = project_vehicle_records(
                validated.bundle.validated_topology, state, hash_context
            )
            ledger = result.ledger
            status = "PASS"
        except ProjectionError as exc:
            reasons = [dict(item) for item in exc.reasons]
            status = "FAIL"
            ledger = failure_projection_ledger(
                status="FAIL",
                reasons=reasons,
                hash_context=hash_context,
                run_id=run_id,
                sim_sec=sim_sec,
                diagnostics=exc.diagnostics,
            )
        except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
            reasons = [_reason(
                "invalid_table_shape",
                f"state projection nested contract malformed: {type(exc).__name__}: {exc}",
            )]
            status = "FAIL"
            ledger = failure_projection_ledger(
                status="FAIL",
                reasons=reasons,
                hash_context=hash_context,
                run_id=run_id,
                sim_sec=sim_sec,
            )
    write_projection_sidecar(sidecar_path, ledger)
    elapsed = time.perf_counter() - started
    sidecar_value = strict_load_json(sidecar_path)
    return {
        "state_path": entry["state_path"],
        "run_id": run_id,
        "sim_sec": sim_sec,
        "required_vehicle_records": entry["required_vehicle_records"],
        "status": status,
        "reasons": reasons,
        "projection_sidecar_path": entry["projection_sidecar_path"],
        "projection_sidecar_file_sha256": file_sha256(sidecar_path),
        "projection_sidecar_semantic_sha256": sidecar_value["semantic_sha256"],
        "normalized_projection_sha256": sidecar_value["normalized_projection_sha256"],
        "record_count": sidecar_value["projection_diagnostics"]["raw_record_count"],
        "assigned_count": sidecar_value["projection_diagnostics"]["unique_assigned_count"],
        "stock_total": sidecar_value["projection_diagnostics"]["stock_total"],
        "state_size_bytes": state_path.stat().st_size,
        "sidecar_size_bytes": sidecar_path.stat().st_size,
        "parse_project_write_wall_sec": elapsed,
    }


def _expected_live_input_hashes(validated: ValidatedStateManifest) -> dict[str, str]:
    return {
        "state_manifest_file_sha256": file_sha256(validated.manifest_path),
        "state_manifest_semantic_sha256": str(validated.manifest["semantic_sha256"]),
        "state_set_semantic_sha256": str(
            validated.manifest["input_hashes"]["state_set_semantic_sha256"]
        ),
        "approving_manifest_sha256": validated.bundle.approval_file_sha256,
        "topology_file_sha256": file_sha256(validated.topology_path),
        "topology_semantic_sha256": validated.bundle.validated_topology.semantic_sha256,
    }


def _nearest_rank_p95(samples: Sequence[float]) -> float:
    ordered = sorted(samples)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def validate_live_evidence(
    validated: ValidatedStateManifest,
    state_results: Sequence[Mapping[str, Any]],
    evidence: Mapping[str, Any],
) -> list[str]:
    issues: list[str] = []
    if not isinstance(evidence, Mapping) or set(evidence) != LIVE_EVIDENCE_FIELDS:
        return ["live evidence shape mismatch"]
    if evidence.get("schema_version") != LIVE_EVIDENCE_SCHEMA_VERSION:
        issues.append("live evidence schema mismatch")
    if evidence.get("status") != "PASS" or evidence.get("reasons") != []:
        issues.append("live evidence status/reasons mismatch")
    if evidence.get("command_version") != {}:
        issues.append("live evidence command_version mismatch")
    if evidence.get("units") != LIVE_EVIDENCE_UNITS:
        issues.append("live evidence units mismatch")
    if evidence.get("downstream_consumers") != LIVE_EVIDENCE_DOWNSTREAM_CONSUMERS:
        issues.append("live evidence downstream_consumers mismatch")
    expected_hashes = _expected_live_input_hashes(validated)
    if (
        not isinstance(evidence.get("input_hashes"), dict)
        or set(evidence["input_hashes"]) != LIVE_INPUT_HASH_NAMES
        or evidence["input_hashes"] != expected_hashes
    ):
        issues.append("live evidence input hash binding mismatch")

    state_evidence = evidence.get("states")
    if not isinstance(state_evidence, list):
        issues.append("live evidence states must be an array")
        state_evidence = []
    if any(not isinstance(item, dict) for item in state_evidence):
        issues.append("live evidence state record is not an object")
    elif state_evidence != sorted(state_evidence, key=_entry_sort_key):
        issues.append("live evidence states are not canonical")
    seen_paths: set[str] = set()
    seen_identities: set[tuple[str, float]] = set()
    for index, item in enumerate(state_evidence):
        if not isinstance(item, dict):
            continue
        state_path = item.get("state_path")
        if not isinstance(state_path, str) or not state_path:
            issues.append(f"live state[{index}] invalid state_path")
        elif state_path in seen_paths:
            issues.append("duplicate live state_path")
        else:
            seen_paths.add(state_path)
        run_id = item.get("run_id")
        sim_sec = item.get("sim_sec")
        if not isinstance(run_id, str) or not run_id or not _finite_nonnegative(sim_sec):
            issues.append(f"live state[{index}] invalid run/time identity")
            continue
        identity = (run_id, float(sim_sec))
        if identity in seen_identities:
            issues.append("duplicate live run/time identity")
        else:
            seen_identities.add(identity)
    dimensions = evidence.get("sample_dimensions")
    expected_dimensions = {
        "states": len(state_evidence),
        "nonzero_live_states": sum(
            isinstance(item, dict)
            and isinstance(item.get("raw_record_count"), int)
            and not isinstance(item.get("raw_record_count"), bool)
            and item["raw_record_count"] > 0
            for item in state_evidence
        ),
        "timing_samples": len(
            evidence.get("performance", {}).get("combined_wall_sec_samples", [])
        )
        if isinstance(evidence.get("performance"), dict)
        and isinstance(evidence["performance"].get("combined_wall_sec_samples"), list)
        else 0,
    }
    if dimensions != expected_dimensions:
        issues.append("live evidence sample_dimensions mismatch")

    result_by_path = {str(item["state_path"]): item for item in state_results}
    if set(result_by_path) != {
        str(item.get("state_path", ""))
        for item in state_evidence
        if isinstance(item, dict)
    }:
        issues.append("live evidence state universe mismatch")
    if not state_results or any(item.get("status") != "PASS" for item in state_results):
        issues.append("live evidence requires a nonempty all-PASS projection universe")

    graph_nodes = validated.bundle.graph.get("nodes", [])
    node_by_lane: dict[tuple[int, int], Mapping[str, Any]] = {}
    lane_counts: dict[tuple[str, int], int] = {}
    for node in graph_nodes if isinstance(graph_nodes, list) else []:
        try:
            key = (int(node["link_no"]), int(node["lane_no"]))
            node_by_lane[key] = node
            parent = (str(node.get("object_kind", "")), int(node["link_no"]))
            lane_counts[parent] = lane_counts.get(parent, 0) + 1
        except (KeyError, TypeError, ValueError):
            continue

    saw_connector = False
    saw_multilane_road = False
    for index, item in enumerate(state_evidence):
        if not isinstance(item, dict) or set(item) != LIVE_STATE_FIELDS:
            issues.append(f"live state[{index}] shape mismatch")
            continue
        path = str(item.get("state_path", ""))
        result = result_by_path.get(path)
        if result is None:
            continue
        try:
            state_path = resolve_contained_path(validated.workspace_root, path)
            state = strict_load_json(state_path)
            raw_bytes = state_path.read_bytes()
        except (OSError, ValueError) as exc:
            issues.append(f"live state[{index}] unavailable: {exc}")
            continue
        envelope = state.get("vehicle_records") if isinstance(state, dict) else None
        records = envelope.get("records") if isinstance(envelope, dict) else None
        if not isinstance(records, list):
            issues.append(f"live state[{index}] vehicle_records missing")
            records = []
        record_by_vehicle = {
            record.get("veh_no"): record
            for record in records
            if isinstance(record, dict)
        }
        expected_values = {
            "state_path": result["state_path"],
            "state_file_sha256": file_sha256(state_path),
            "run_id": result["run_id"],
            "sim_sec": result["sim_sec"],
            "collection_count_before": envelope.get("collection_count_before")
            if isinstance(envelope, dict)
            else None,
            "collection_count_after": envelope.get("collection_count_after")
            if isinstance(envelope, dict)
            else None,
            "raw_record_count": result["record_count"],
            "assigned_count": result["assigned_count"],
            "stock_total": result["stock_total"],
            "global_residual": 0,
        }
        if any(item.get(field) != value for field, value in expected_values.items()):
            issues.append(f"live state[{index}] projection/count binding mismatch")
        if item.get("capture_source") != "live_vissim_com":
            issues.append(f"live state[{index}] capture_source mismatch")
        if (
            not isinstance(item.get("vissim_version"), str)
            or not item["vissim_version"].strip()
            or item.get("supported_vissim_version") is not True
        ):
            issues.append(f"live state[{index}] supported VISSIM version missing")
        if item.get("runner_utf8_without_bom") is not True or raw_bytes.startswith(b"\xef\xbb\xbf"):
            issues.append(f"live state[{index}] UTF-8 without BOM gate failed")
        if item.get("public_projector_parsed") is not True:
            issues.append(f"live state[{index}] public projector parse gate failed")
        if not isinstance(item.get("raw_record_count"), int) or isinstance(
            item.get("raw_record_count"), bool
        ) or item["raw_record_count"] <= 0:
            issues.append(f"live state[{index}] is a zero-vehicle capture")

        samples = item.get("raw_attribute_samples")
        if not isinstance(samples, list) or not samples:
            issues.append(f"live state[{index}] raw attribute samples missing")
            samples = []
        for sample_index, sample in enumerate(samples):
            if not isinstance(sample, dict) or set(sample) != RAW_ATTRIBUTE_SAMPLE_FIELDS:
                issues.append(f"live state[{index}] sample[{sample_index}] shape mismatch")
                continue
            lane_raw = sample.get("lane_raw")
            match = LANE_ATTRIBUTE_PATTERN.fullmatch(lane_raw) if isinstance(lane_raw, str) else None
            if match is None:
                issues.append(f"live state[{index}] sample[{sample_index}] lane grammar mismatch")
                continue
            parsed_link, parsed_lane = int(match.group(1)), int(match.group(2))
            if (
                parsed_link > MAX_VISSIM_ID
                or parsed_lane > MAX_VISSIM_ID
                or sample.get("parsed_link_no") != parsed_link
                or sample.get("parsed_lane_no") != parsed_lane
            ):
                issues.append(f"live state[{index}] sample[{sample_index}] parser output mismatch")
                continue
            com_key = sample.get("com_key")
            no_value = sample.get("no_value")
            if (
                not isinstance(com_key, int)
                or isinstance(com_key, bool)
                or not 0 < com_key <= MAX_VISSIM_ID
                or no_value != com_key
            ):
                issues.append(f"live state[{index}] sample[{sample_index}] COM key mismatch")
                continue
            record = record_by_vehicle.get(com_key)
            if (
                record is None
                or record.get("link_no") != parsed_link
                or record.get("lane_no") != parsed_lane
                or not _finite_nonnegative(sample.get("position_value"))
                or not _finite_nonnegative(sample.get("speed_value"))
                or record.get("position_m") != sample.get("position_value")
                or record.get("speed_kph") != sample.get("speed_value")
            ):
                issues.append(f"live state[{index}] sample[{sample_index}] state record mismatch")
                continue
            node = node_by_lane.get((parsed_link, parsed_lane))
            if node is None:
                issues.append(f"live state[{index}] sample[{sample_index}] unknown A1 lane")
                continue
            parent_kind = str(node.get("object_kind", ""))
            saw_connector = saw_connector or parent_kind == "connector"
            saw_multilane_road = saw_multilane_road or (
                parent_kind == "link"
                and lane_counts.get((parent_kind, parsed_link), 0) >= 2
            )
    if not saw_connector:
        issues.append("live evidence lacks a connector sample")
    if not saw_multilane_road:
        issues.append("live evidence lacks a multi-lane road sample")

    performance = evidence.get("performance")
    if not isinstance(performance, dict) or set(performance) != PERFORMANCE_FIELDS:
        issues.append("live performance evidence shape mismatch")
    else:
        samples = performance.get("combined_wall_sec_samples")
        valid_samples = (
            isinstance(samples, list)
            and len(samples) >= 20
            and all(_finite_nonnegative(value) for value in samples)
        )
        if performance.get("qualification_record_count") != 20_000:
            issues.append("live performance qualification_record_count mismatch")
        size_limits = (
            ("state_envelope_size_bytes", 8 * 1024 * 1024),
            ("sidecar_size_bytes", 16 * 1024 * 1024),
            ("action_reference_size_bytes", 32 * 1024),
        )
        for field, limit in size_limits:
            value = performance.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 < value <= limit:
                issues.append(f"live performance {field} exceeds contract")
        if performance.get("decision_budget_sec") != 30.0:
            issues.append("live performance decision budget mismatch")
        if performance.get("timing_scope") != (
            "live_com_capture+serialize+strict_parse+public_project+atomic_sidecar_write"
        ):
            issues.append("live performance timing scope mismatch")
        if not valid_samples:
            issues.append("live performance timing samples invalid")
        else:
            numeric_samples = [float(value) for value in samples]
            p95 = _nearest_rank_p95(numeric_samples)
            if performance.get("p95_wall_sec") != p95:
                issues.append("live performance p95 mismatch")
            if p95 > 3.0 or p95 > 0.1 * 30.0:
                issues.append("live performance p95 exceeds contract")
    try:
        semantic = canonical_json_sha256(live_evidence_semantic_payload(evidence))
    except (KeyError, OverflowError, TypeError, ValueError) as exc:
        issues.append(f"live evidence semantic payload invalid: {exc}")
        semantic = ""
    if evidence.get("semantic_sha256") != semantic:
        issues.append("live evidence semantic hash mismatch")
    return sorted(set(issues))


def build_audit(
    validated: ValidatedStateManifest,
    state_results: Sequence[Mapping[str, Any]],
    live_evidence: Mapping[str, Any] | None = None,
    live_evidence_path: Path | None = None,
) -> dict[str, Any]:
    failed = any(item["status"] == "FAIL" for item in state_results)
    reasons: list[dict[str, Any]] = []
    if failed:
        for state in state_results:
            if state["status"] != "FAIL":
                continue
            for state_reason in state["reasons"]:
                reasons.append(_reason(
                    str(state_reason.get("code", "aggregate_mismatch")),
                    {
                        "state_path": state["state_path"],
                        "detail": state_reason.get("detail"),
                    },
                ))
    live_issues: list[str] = []
    if live_evidence is None:
        reasons.extend([
            _reason("live_com_not_evaluated", "supported-version live COM evidence was not supplied"),
            _reason("performance_not_evaluated", "live combined capture/serialize/parse/project p95 is unavailable"),
        ])
        live_gates = {
            "supported_vissim_com_capture": "NOT_EVALUATED",
            "live_performance_p95": "NOT_EVALUATED",
        }
    else:
        live_issues = validate_live_evidence(validated, state_results, live_evidence)
        if live_issues:
            reasons.append(_reason("aggregate_mismatch", live_issues))
            live_gates = {
                "supported_vissim_com_capture": "FAIL",
                "live_performance_p95": "FAIL",
            }
        else:
            live_gates = {
                "supported_vissim_com_capture": "PASS",
                "live_performance_p95": "PASS",
            }
    status = (
        "FAIL"
        if failed or live_issues
        else "PASS"
        if live_evidence is not None
        else "NOT_EVALUATED"
    )
    manifest = validated.manifest
    audit: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "input_hashes": {
            "state_manifest_file_sha256": file_sha256(validated.manifest_path),
            "state_manifest_semantic_sha256": manifest["semantic_sha256"],
            "approving_manifest_sha256": validated.bundle.approval_file_sha256,
            "state_selection_file_sha256": file_sha256(validated.selection_path),
            "state_selection_semantic_sha256": validated.selection["semantic_sha256"],
            "topology_file_sha256": file_sha256(validated.topology_path),
            "topology_semantic_sha256": validated.bundle.validated_topology.semantic_sha256,
            "live_evidence_file_sha256": (
                file_sha256(live_evidence_path) if live_evidence_path is not None else ""
            ),
            "live_evidence_semantic_sha256": (
                str(live_evidence.get("semantic_sha256", ""))
                if live_evidence is not None
                else ""
            ),
        },
        "command_version": {},
        "status": status,
        "reasons": reasons,
        "sample_dimensions": {
            "states": len(state_results),
            "projection_pass": sum(item["status"] == "PASS" for item in state_results),
            "projection_fail": sum(item["status"] == "FAIL" for item in state_results),
            "projection_not_evaluated": sum(
                item["status"] == "NOT_EVALUATED" for item in state_results
            ),
        },
        "units": dict(UNITS),
        "downstream_consumers": list(DOWNSTREAM_CONSUMERS),
        "live_gates": live_gates,
        "states": list(state_results),
    }
    audit["semantic_sha256"] = canonical_json_sha256(audit_semantic_payload(audit))
    return audit


def failed_audit(reasons: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    audit: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "input_hashes": {},
        "command_version": {},
        "status": "FAIL",
        "reasons": [dict(item) for item in reasons],
        "sample_dimensions": {
            "states": 0,
            "projection_pass": 0,
            "projection_fail": 0,
            "projection_not_evaluated": 0,
        },
        "units": dict(UNITS),
        "downstream_consumers": list(DOWNSTREAM_CONSUMERS),
        "live_gates": {
            "supported_vissim_com_capture": "NOT_EVALUATED",
            "live_performance_p95": "NOT_EVALUATED",
        },
        "states": [],
    }
    audit["semantic_sha256"] = canonical_json_sha256(audit_semantic_payload(audit))
    return audit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--states", required=True, type=Path)
    parser.add_argument("--topology", required=True, type=Path)
    parser.add_argument("--live-evidence", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    output = args.out.resolve(strict=False)
    try:
        manifest_path = args.states.resolve(strict=True)
        topology_path = args.topology.resolve(strict=True)
        validated = validate_manifest_contract(manifest_path, topology_path)
        results = [_process_state(validated, entry) for entry in validated.manifest["states"]]
        live_evidence_path: Path | None = None
        live_evidence: Mapping[str, Any] | None = None
        if args.live_evidence is not None:
            candidate = (
                args.live_evidence
                if args.live_evidence.is_absolute()
                else validated.workspace_root / args.live_evidence
            )
            live_evidence_path = candidate.resolve(strict=True)
            live_evidence_path.relative_to(validated.workspace_root)
            loaded_evidence = strict_load_json(live_evidence_path)
            if not isinstance(loaded_evidence, dict):
                raise ValueError("live evidence root is not an object")
            live_evidence = loaded_evidence
        audit = build_audit(
            validated,
            results,
            live_evidence=live_evidence,
            live_evidence_path=live_evidence_path,
        )
    except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
        audit = failed_audit(_exception_reasons(exc))
    try:
        atomic_write_json(output, audit)
    except OSError:
        return 1
    print(f"status={audit['status']} states={audit['sample_dimensions']['states']}")
    return {"PASS": 0, "FAIL": 1, "NOT_EVALUATED": 2}[audit["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
