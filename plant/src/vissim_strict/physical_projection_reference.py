"""Bounded, fail-closed B1a projection sidecar/reference validation and publication."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

from .physical_projection import (
    BoundedJsonSnapshot,
    PROJECTION_SCHEMA_VERSION,
    SHA256_PATTERN,
    ValidatedPhysicalTopology,
    _project_vehicle_records_kernel,
    canonical_json_bytes,
    freeze_json,
    json_type_strict_equal,
    load_bounded_json_snapshot,
    normalize_vehicle_records,
    projection_semantic_payload,
    thaw_json,
    validate_physical_stock_topology,
    workspace_relative_path,
)
from .run_evidence import (
    MAX_APPROVAL_BYTES,
    MAX_RUN_MANIFEST_BYTES,
    MAX_TOPOLOGY_BYTES,
    ValidatedRunManifest,
    resolve_canonical_workspace_destination,
    resolve_canonical_workspace_file,
    validate_run_manifest,
)
from .topology import canonical_json_sha256


PHYSICAL_PROJECTION_REFERENCE_SCHEMA_VERSION = "physical-projection-reference-v2.1"
MAX_STATE_BYTES = 8 * 1024 * 1024
MAX_PROJECTION_SIDECAR_BYTES = 16 * 1024 * 1024
MAX_PROJECTION_REFERENCE_BYTES = 32 * 1024
REFERENCE_FIELDS = (
    "schema_version", "status", "reasons", "qualification", "run_id", "sim_sec",
    "run_manifest_sha256", "state_path", "state_file_sha256", "topology_file_sha256",
    "topology_semantic_sha256", "projection_sidecar_path",
    "projection_sidecar_file_sha256", "projection_sidecar_semantic_sha256",
    "normalized_projection_sha256", "record_count", "assigned_count", "stock_total",
    "global_residual", "semantic_sha256",
)
_SIDECAR_FIELDS = {
    "schema_version", "input_hashes", "command_version", "status", "reasons",
    "sample_dimensions", "units", "downstream_consumers", "run_id", "sim_sec",
    "vehicle_assignments", "stock_counts", "view_summaries", "projection_diagnostics",
    "normalized_projection_sha256", "semantic_sha256",
}


class ProjectionReferenceValidationError(ValueError):
    """Raised whenever a B1a reference or its raw companions are not exact."""

    def __init__(self, issues: Sequence[str]) -> None:
        self.issues = tuple(sorted(set(str(issue) for issue in issues)))
        super().__init__("; ".join(self.issues))


@dataclass(frozen=True)
class ValidatedApprovedTopology:
    approval_snapshot: BoundedJsonSnapshot
    lane_graph_snapshot: BoundedJsonSnapshot
    topology_snapshot: BoundedJsonSnapshot
    topology: ValidatedPhysicalTopology

    def __iter__(self):
        # Preserve the initial slice's tuple-unpacking API.
        yield self.topology_snapshot.path
        yield self.topology


@dataclass(frozen=True)
class ValidatedProjectionReference:
    artifact: Mapping[str, Any]
    reference_path: Path
    reference_file_sha256: str
    reference_snapshot: BoundedJsonSnapshot
    run_manifest: ValidatedRunManifest
    run_manifest_snapshot: BoundedJsonSnapshot
    state_path: Path
    state: Mapping[str, Any]
    state_snapshot: BoundedJsonSnapshot
    approved_topology: ValidatedApprovedTopology
    topology_path: Path
    topology: ValidatedPhysicalTopology
    sidecar_path: Path
    sidecar: Mapping[str, Any]
    sidecar_snapshot: BoundedJsonSnapshot


def physical_projection_reference_semantic_payload(reference: Mapping[str, Any]) -> dict[str, Any]:
    return {key: reference[key] for key in REFERENCE_FIELDS if key != "semantic_sha256"}


def physical_projection_reference_semantic_sha256(reference: Mapping[str, Any]) -> str:
    return canonical_json_sha256(physical_projection_reference_semantic_payload(reference))


def _finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, TypeError, ValueError):
        return False


def _exact_fields(
    value: Any,
    expected: set[str] | tuple[str, ...],
    label: str,
    issues: list[str],
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        issues.append(f"{label} must be an object")
        return {}
    if set(value) != set(expected):
        issues.append(f"{label} fields mismatch")
    return value


def _snapshot_with_path(snapshot: BoundedJsonSnapshot, path: Path) -> BoundedJsonSnapshot:
    return replace(snapshot, path=path.resolve(strict=True))


def load_validated_approved_topology(
    run_manifest: ValidatedRunManifest,
    *,
    workspace_root: str | Path,
) -> ValidatedApprovedTopology:
    """Load, hash, parse, and validate exact approval/A1/A2 byte snapshots."""

    root = Path(workspace_root).resolve(strict=True)
    approval_path = run_manifest.resolved_paths["approved_topology.approving_manifest_path"]
    topology_path = run_manifest.resolved_paths["approved_topology.topology_path"]
    approved = run_manifest.artifact["approved_topology"]
    try:
        approval_snapshot = load_bounded_json_snapshot(
            approval_path, max_bytes=MAX_APPROVAL_BYTES
        )
        if approval_snapshot.file_sha256 != approved["approving_manifest_sha256"]:
            raise ValueError("approved topology approval file hash mismatch")
        approval = approval_snapshot.value
        source_inputs = approval.get("source_inputs") if isinstance(approval, Mapping) else None
        lane_graph_binding = source_inputs.get("lane_graph") if isinstance(source_inputs, Mapping) else None
        if not isinstance(lane_graph_binding, Mapping) or set(lane_graph_binding) != {
            "path", "file_sha256", "semantic_sha256"
        }:
            raise ValueError("approved topology lane graph binding is invalid")
        lane_graph_path = resolve_canonical_workspace_file(root, lane_graph_binding["path"])
        lane_graph_snapshot = load_bounded_json_snapshot(
            lane_graph_path, max_bytes=MAX_TOPOLOGY_BYTES
        )
        if lane_graph_snapshot.file_sha256 != lane_graph_binding["file_sha256"]:
            raise ValueError("approved topology lane graph file hash mismatch")
        topology_snapshot = load_bounded_json_snapshot(
            topology_path, max_bytes=MAX_TOPOLOGY_BYTES
        )
        if topology_snapshot.file_sha256 != approved["topology_file_sha256"]:
            raise ValueError("approved topology file hash mismatch")
        topology = validate_physical_stock_topology(
            topology_snapshot.value, lane_graph_snapshot.value
        )
    except (MemoryError, OSError, OverflowError, TypeError, ValueError) as exc:
        raise ProjectionReferenceValidationError(
            [f"approved topology validation failed: {exc}"]
        ) from exc
    if topology.semantic_sha256 != approved["topology_semantic_sha256"]:
        raise ProjectionReferenceValidationError(
            ["approved topology semantic binding mismatch"]
        )
    return ValidatedApprovedTopology(
        approval_snapshot=approval_snapshot,
        lane_graph_snapshot=lane_graph_snapshot,
        topology_snapshot=topology_snapshot,
        topology=topology,
    )


def validate_projection_sidecar(
    sidecar: Any,
    *,
    topology: ValidatedPhysicalTopology,
    state: Mapping[str, Any],
    hash_context: Mapping[str, str],
    run_id: str,
    sim_sec: float,
) -> Mapping[str, Any]:
    """Validate an exact projection-v2.1 ledger through the shared kernel."""

    issues: list[str] = []
    ledger = _exact_fields(sidecar, _SIDECAR_FIELDS, "projection sidecar", issues)
    if ledger.get("schema_version") != PROJECTION_SCHEMA_VERSION:
        issues.append("projection sidecar schema mismatch")
    if ledger.get("status") != "PASS" or ledger.get("reasons") != []:
        issues.append("projection sidecar must be PASS with empty reasons")
    try:
        if ledger.get("semantic_sha256") != canonical_json_sha256(
            projection_semantic_payload(ledger)
        ):
            issues.append("projection sidecar semantic hash mismatch")
        authored_normalized = canonical_json_sha256({
            "topology_semantic_sha256": hash_context["topology_semantic_sha256"],
            "vehicle_assignments": ledger["vehicle_assignments"],
            "stock_counts": ledger["stock_counts"],
        })
        if ledger.get("normalized_projection_sha256") != authored_normalized:
            issues.append("projection sidecar authored normalized hash mismatch")
    except (KeyError, OverflowError, TypeError, ValueError) as exc:
        issues.append(f"projection sidecar hash payload invalid: {exc}")
    if issues:
        raise ProjectionReferenceValidationError(issues)
    try:
        expected = thaw_json(
            _project_vehicle_records_kernel(topology, state, hash_context).ledger
        )
    except (MemoryError, OSError, OverflowError, TypeError, ValueError) as exc:
        raise ProjectionReferenceValidationError(
            [f"projection kernel validation failed: {exc}"]
        ) from exc
    if not json_type_strict_equal(ledger, expected):
        raise ProjectionReferenceValidationError(
            ["projection sidecar differs from shared-kernel reconstruction"]
        )
    if not isinstance(sim_sec, float) or not _finite_number(sim_sec):
        raise ProjectionReferenceValidationError(["expected sim_sec must be a JSON double"])
    if ledger["run_id"] != run_id or type(ledger["sim_sec"]) is not float or ledger["sim_sec"] != sim_sec:
        raise ProjectionReferenceValidationError(
            ["projection sidecar run/time binding mismatch"]
        )
    return freeze_json(ledger)


def build_physical_projection_reference(
    *,
    workspace_root: str | Path,
    run_manifest: ValidatedRunManifest,
    run_manifest_snapshot: BoundedJsonSnapshot,
    state_snapshot: BoundedJsonSnapshot,
    approved_topology: ValidatedApprovedTopology,
    sidecar_path: str | Path,
    sidecar_snapshot: BoundedJsonSnapshot,
) -> dict[str, Any]:
    """Build a reference solely from already byte-bound validated snapshots."""

    root = Path(workspace_root).resolve(strict=True)
    sidecar = sidecar_snapshot.value
    reference = {
        "schema_version": PHYSICAL_PROJECTION_REFERENCE_SCHEMA_VERSION,
        "status": "PASS",
        "reasons": [],
        "qualification": thaw_json(run_manifest.artifact["qualification"]),
        "run_id": sidecar["run_id"],
        "sim_sec": sidecar["sim_sec"],
        "run_manifest_sha256": run_manifest_snapshot.file_sha256,
        "state_path": workspace_relative_path(root, state_snapshot.path),
        "state_file_sha256": state_snapshot.file_sha256,
        "topology_file_sha256": approved_topology.topology_snapshot.file_sha256,
        "topology_semantic_sha256": approved_topology.topology.semantic_sha256,
        "projection_sidecar_path": workspace_relative_path(root, sidecar_path),
        "projection_sidecar_file_sha256": sidecar_snapshot.file_sha256,
        "projection_sidecar_semantic_sha256": sidecar["semantic_sha256"],
        "normalized_projection_sha256": sidecar["normalized_projection_sha256"],
        "record_count": sidecar["sample_dimensions"]["records"],
        "assigned_count": sidecar["sample_dimensions"]["assignments"],
        "stock_total": sidecar["projection_diagnostics"]["stock_total"],
        "global_residual": sidecar["projection_diagnostics"]["global_residual"],
    }
    reference["semantic_sha256"] = physical_projection_reference_semantic_sha256(
        reference
    )
    return reference


def _validate_reference_root(value: Any) -> Mapping[str, Any]:
    issues: list[str] = []
    reference = _exact_fields(value, REFERENCE_FIELDS, "projection reference", issues)
    if reference.get("schema_version") != PHYSICAL_PROJECTION_REFERENCE_SCHEMA_VERSION:
        issues.append("projection reference schema mismatch")
    if reference.get("status") != "PASS" or reference.get("reasons") != []:
        issues.append("projection reference must be PASS with empty reasons")
    if not isinstance(reference.get("run_id"), str) or not reference.get("run_id"):
        issues.append("projection reference run_id is invalid")
    if type(reference.get("sim_sec")) is not float or not _finite_number(reference.get("sim_sec")) or reference.get("sim_sec", -1.0) < 0.0:
        issues.append("projection reference sim_sec must be a finite nonnegative JSON double")
    for field in (
        "record_count", "assigned_count", "stock_total", "global_residual"
    ):
        number = reference.get(field)
        if not isinstance(number, int) or isinstance(number, bool):
            issues.append(f"projection reference {field} must be a JSON integer")
        elif field != "global_residual" and number < 0:
            issues.append(f"projection reference {field} is negative")
    for field in (
        "run_manifest_sha256", "state_file_sha256", "topology_file_sha256",
        "topology_semantic_sha256", "projection_sidecar_file_sha256",
        "projection_sidecar_semantic_sha256", "normalized_projection_sha256",
        "semantic_sha256",
    ):
        if not isinstance(reference.get(field), str) or SHA256_PATTERN.fullmatch(reference[field]) is None:
            issues.append(f"projection reference {field} is invalid")
    try:
        if reference.get("semantic_sha256") != physical_projection_reference_semantic_sha256(reference):
            issues.append("projection reference semantic hash mismatch")
    except (KeyError, OverflowError, TypeError, ValueError) as exc:
        issues.append(f"projection reference semantic payload invalid: {exc}")
    if issues:
        raise ProjectionReferenceValidationError(issues)
    return reference


def validate_physical_projection_reference(
    reference_path: str | Path,
    *,
    workspace_root: str | Path,
    run_manifest_path: str | Path,
    expected_reference_file_sha256: str | None = None,
) -> ValidatedProjectionReference:
    """Validate a reference chain using one bounded snapshot per JSON artifact."""

    root = Path(workspace_root).resolve(strict=True)
    try:
        reference_file = resolve_canonical_workspace_file(root, str(reference_path))
        manifest_file = resolve_canonical_workspace_file(root, str(run_manifest_path))
        reference_snapshot = load_bounded_json_snapshot(
            reference_file, max_bytes=MAX_PROJECTION_REFERENCE_BYTES
        )
        manifest_snapshot = load_bounded_json_snapshot(
            manifest_file, max_bytes=MAX_RUN_MANIFEST_BYTES
        )
        if (
            expected_reference_file_sha256 is not None
            and reference_snapshot.file_sha256 != expected_reference_file_sha256
        ):
            raise ValueError("caller projection reference SHA-256 mismatch")
        reference = _validate_reference_root(reference_snapshot.value)
        manifest = validate_run_manifest(
            manifest_snapshot.value,
            workspace_root=root,
            expected_run_id=reference["run_id"],
            capture_time=reference["sim_sec"],
        )
        approved = load_validated_approved_topology(
            manifest, workspace_root=root
        )
        state_file = resolve_canonical_workspace_file(root, reference["state_path"])
        sidecar_file = resolve_canonical_workspace_file(
            root, reference["projection_sidecar_path"]
        )
        state_snapshot = load_bounded_json_snapshot(
            state_file, max_bytes=MAX_STATE_BYTES
        )
        sidecar_snapshot = load_bounded_json_snapshot(
            sidecar_file, max_bytes=MAX_PROJECTION_SIDECAR_BYTES
        )
    except (MemoryError, OSError, OverflowError, TypeError, ValueError) as exc:
        if isinstance(exc, ProjectionReferenceValidationError):
            raise
        raise ProjectionReferenceValidationError(
            [f"bounded projection reference validation failed: {exc}"]
        ) from exc

    state = state_snapshot.value
    provenance = state.get("run_provenance") if isinstance(state, Mapping) else None
    manifest_relative = workspace_relative_path(root, manifest_snapshot.path)
    if not isinstance(provenance, Mapping) or not json_type_strict_equal(
        provenance,
        {
            "run_id": reference["run_id"],
            "manifest_path": manifest_relative,
            "manifest_sha256": manifest_snapshot.file_sha256,
        },
    ):
        raise ProjectionReferenceValidationError(
            ["state/run manifest provenance mismatch"]
        )
    if not isinstance(state, Mapping) or type(state.get("sim_sec")) is not float or state["sim_sec"] != reference["sim_sec"]:
        raise ProjectionReferenceValidationError(
            ["state/reference sim_sec mismatch"]
        )
    try:
        _, _, records_hash = normalize_vehicle_records(
            state, approved.topology.tolerance_m
        )
        context = {
            "topology_file_sha256": approved.topology_snapshot.file_sha256,
            "topology_semantic_sha256": approved.topology.semantic_sha256,
            "approving_manifest_sha256": approved.approval_snapshot.file_sha256,
            "state_file_sha256": state_snapshot.file_sha256,
            "vehicle_records_semantic_sha256": records_hash,
        }
        sidecar = validate_projection_sidecar(
            sidecar_snapshot.value,
            topology=approved.topology,
            state=state,
            hash_context=context,
            run_id=reference["run_id"],
            sim_sec=reference["sim_sec"],
        )
        expected_reference = build_physical_projection_reference(
            workspace_root=root,
            run_manifest=manifest,
            run_manifest_snapshot=manifest_snapshot,
            state_snapshot=state_snapshot,
            approved_topology=approved,
            sidecar_path=sidecar_file,
            sidecar_snapshot=sidecar_snapshot,
        )
    except (MemoryError, OSError, OverflowError, TypeError, ValueError) as exc:
        if isinstance(exc, ProjectionReferenceValidationError):
            raise
        raise ProjectionReferenceValidationError(
            [f"projection companion validation failed: {exc}"]
        ) from exc
    if not json_type_strict_equal(reference, expected_reference):
        raise ProjectionReferenceValidationError(
            ["projection reference differs from exact companion reconstruction"]
        )
    return ValidatedProjectionReference(
        artifact=freeze_json(reference),
        reference_path=reference_file,
        reference_file_sha256=reference_snapshot.file_sha256,
        reference_snapshot=reference_snapshot,
        run_manifest=manifest,
        run_manifest_snapshot=manifest_snapshot,
        state_path=state_file,
        state=freeze_json(state),
        state_snapshot=state_snapshot,
        approved_topology=approved,
        topology_path=approved.topology_snapshot.path,
        topology=approved.topology,
        sidecar_path=sidecar_file,
        sidecar=sidecar,
        sidecar_snapshot=sidecar_snapshot,
    )


def validate_projection_output_paths(
    sidecar_path: str | Path | None,
    reference_path: str | Path,
    *,
    immutable_paths: Mapping[str, str | Path],
) -> None:
    """Reject any output/output or output/immutable role identity."""

    outputs = {"projection_reference": Path(reference_path).resolve(strict=False)}
    if sidecar_path is not None:
        outputs["projection_sidecar"] = Path(sidecar_path).resolve(strict=False)
    def identities(path: str | Path) -> set[tuple[Any, ...]]:
        candidate = Path(path)
        resolved = candidate.resolve(strict=False)
        result: set[tuple[Any, ...]] = {
            ("path", os.path.normcase(str(resolved)))
        }
        try:
            stat = resolved.stat()
        except OSError:
            return result
        result.add(("file", stat.st_dev, stat.st_ino))
        return result

    output_identities: dict[str, set[tuple[Any, ...]]] = {
        role: identities(path) for role, path in outputs.items()
    }
    output_roles = tuple(output_identities)
    if len(output_roles) == 2 and (
        output_identities[output_roles[0]] & output_identities[output_roles[1]]
    ):
        raise ProjectionReferenceValidationError(
            [f"projection path role collision: {output_roles[0]} == {output_roles[1]}"]
        )
    for immutable_role, immutable_path in immutable_paths.items():
        immutable_identities = identities(immutable_path)
        for output_role, output_keys in output_identities.items():
            if immutable_identities & output_keys:
                raise ProjectionReferenceValidationError(
                    [
                        "projection path role collision: "
                        f"{immutable_role} == {output_role}"
                    ]
                )


def _write_temporary_bytes(destination: Path, data: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def publish_projection_outputs(
    *,
    workspace_root: str | Path,
    sidecar_path: str | Path,
    reference_path: str | Path,
    immutable_paths: Mapping[str, str | Path],
    projection_ledger: Mapping[str, Any],
    run_manifest: ValidatedRunManifest,
    run_manifest_snapshot: BoundedJsonSnapshot,
    state_snapshot: BoundedJsonSnapshot,
    approved_topology: ValidatedApprovedTopology,
) -> ValidatedProjectionReference:
    """Validate temporary complete bytes and publish PASS reference last."""

    root = Path(workspace_root).resolve(strict=True)
    def canonical_destination(path: str | Path) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            try:
                declared = candidate.relative_to(root).as_posix()
            except ValueError as exc:
                raise ProjectionReferenceValidationError(
                    ["projection output escapes canonical workspace"]
                ) from exc
        else:
            declared = candidate.as_posix()
        try:
            return resolve_canonical_workspace_destination(root, declared)
        except (OSError, TypeError, ValueError) as exc:
            raise ProjectionReferenceValidationError(
                [f"projection output path is invalid: {exc}"]
            ) from exc

    reference_final = canonical_destination(reference_path)
    try:
        sidecar_final = canonical_destination(sidecar_path)
    except BaseException:
        validate_projection_output_paths(
            None, reference_final, immutable_paths=immutable_paths
        )
        reference_final.unlink(missing_ok=True)
        raise
    try:
        validate_projection_output_paths(
            sidecar_final,
            reference_final,
            immutable_paths=immutable_paths,
        )
    except BaseException:
        validate_projection_output_paths(
            None, reference_final, immutable_paths=immutable_paths
        )
        reference_final.unlink(missing_ok=True)
        raise
    sidecar_temp: Path | None = None
    reference_temp: Path | None = None
    try:
        # Invalidate an older PASS before any fallible serialization or write.
        validate_projection_output_paths(
            sidecar_final,
            reference_final,
            immutable_paths=immutable_paths,
        )
        reference_final.unlink(missing_ok=True)
        sidecar_bytes = canonical_json_bytes(projection_ledger)
        if len(sidecar_bytes) > MAX_PROJECTION_SIDECAR_BYTES:
            raise ProjectionReferenceValidationError(
                ["projection sidecar exceeds byte limit"]
            )
        validate_projection_output_paths(
            sidecar_final,
            reference_final,
            immutable_paths=immutable_paths,
        )
        sidecar_final.parent.mkdir(parents=True, exist_ok=True)
        sidecar_temp = _write_temporary_bytes(sidecar_final, sidecar_bytes)
        sidecar_temp_snapshot = load_bounded_json_snapshot(
            sidecar_temp, max_bytes=MAX_PROJECTION_SIDECAR_BYTES
        )
        if sidecar_temp_snapshot.data != sidecar_bytes:
            raise ProjectionReferenceValidationError(
                ["projection sidecar temporary byte mismatch"]
            )
        _, _, records_hash = normalize_vehicle_records(
            state_snapshot.value, approved_topology.topology.tolerance_m
        )
        context = {
            "topology_file_sha256": approved_topology.topology_snapshot.file_sha256,
            "topology_semantic_sha256": approved_topology.topology.semantic_sha256,
            "approving_manifest_sha256": approved_topology.approval_snapshot.file_sha256,
            "state_file_sha256": state_snapshot.file_sha256,
            "vehicle_records_semantic_sha256": records_hash,
        }
        validate_projection_sidecar(
            sidecar_temp_snapshot.value,
            topology=approved_topology.topology,
            state=state_snapshot.value,
            hash_context=context,
            run_id=run_manifest.artifact["run_id"],
            sim_sec=state_snapshot.value["sim_sec"],
        )
        validate_projection_output_paths(
            sidecar_final,
            reference_final,
            immutable_paths=immutable_paths,
        )
        os.replace(sidecar_temp, sidecar_final)
        sidecar_temp = None
        sidecar_snapshot = _snapshot_with_path(
            sidecar_temp_snapshot, sidecar_final
        )
        reference = build_physical_projection_reference(
            workspace_root=root,
            run_manifest=run_manifest,
            run_manifest_snapshot=run_manifest_snapshot,
            state_snapshot=state_snapshot,
            approved_topology=approved_topology,
            sidecar_path=sidecar_final,
            sidecar_snapshot=sidecar_snapshot,
        )
        reference_bytes = canonical_json_bytes(reference)
        if len(reference_bytes) > MAX_PROJECTION_REFERENCE_BYTES:
            raise ProjectionReferenceValidationError(
                ["projection reference exceeds byte limit"]
            )
        validate_projection_output_paths(
            sidecar_final,
            reference_final,
            immutable_paths=immutable_paths,
        )
        reference_final.parent.mkdir(parents=True, exist_ok=True)
        reference_temp = _write_temporary_bytes(
            reference_final, reference_bytes
        )
        reference_temp_snapshot = load_bounded_json_snapshot(
            reference_temp, max_bytes=MAX_PROJECTION_REFERENCE_BYTES
        )
        if reference_temp_snapshot.data != reference_bytes:
            raise ProjectionReferenceValidationError(
                ["projection reference temporary byte mismatch"]
            )
        validated = validate_physical_projection_reference(
            workspace_relative_path(root, reference_temp),
            workspace_root=root,
            run_manifest_path=workspace_relative_path(
                root, run_manifest_snapshot.path
            ),
            expected_reference_file_sha256=reference_temp_snapshot.file_sha256,
        )
        validate_projection_output_paths(
            sidecar_final,
            reference_final,
            immutable_paths=immutable_paths,
        )
        os.replace(reference_temp, reference_final)
        reference_temp = None
        return replace(
            validated,
            reference_path=reference_final,
            reference_snapshot=_snapshot_with_path(
                reference_temp_snapshot, reference_final
            ),
        )
    except BaseException:
        validate_projection_output_paths(
            sidecar_final,
            reference_final,
            immutable_paths=immutable_paths,
        )
        reference_final.unlink(missing_ok=True)
        raise
    finally:
        if sidecar_temp is not None:
            sidecar_temp.unlink(missing_ok=True)
        if reference_temp is not None:
            reference_temp.unlink(missing_ok=True)


__all__ = [
    "MAX_PROJECTION_REFERENCE_BYTES", "MAX_PROJECTION_SIDECAR_BYTES",
    "MAX_STATE_BYTES", "PHYSICAL_PROJECTION_REFERENCE_SCHEMA_VERSION",
    "ProjectionReferenceValidationError", "ValidatedApprovedTopology",
    "ValidatedProjectionReference", "build_physical_projection_reference",
    "load_validated_approved_topology", "physical_projection_reference_semantic_payload",
    "physical_projection_reference_semantic_sha256", "publish_projection_outputs",
    "validate_physical_projection_reference", "validate_projection_output_paths",
    "validate_projection_sidecar",
]
