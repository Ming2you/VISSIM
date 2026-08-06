from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
PLANT_ROOT = REPO_ROOT / "plant"
for search_root in (SCRIPT_ROOT, PLANT_ROOT):
    if str(search_root) not in sys.path:
        sys.path.insert(0, str(search_root))

from build_preflight_manifest import DEFAULT_PATHS as PREFLIGHT_DEFAULT_PATHS  # noqa: E402


SCHEMA_VERSION = "baseline-snapshot-v2.1"
RUNTIME_SOURCE_SCHEMA = "runtime-source-v2.1"
PREFLIGHT_SCHEMA = "preflight-v3"
AUDIT_SCHEMA = 2
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NOT_EVALUATED = "NOT_EVALUATED"
FILESYSTEM_MTIME_TOLERANCE_SEC = 2.0

EXPECTED_NUMSIM_COMMIT = "0240ba89b97bf43438e1a0f519f7b0c978288913"
EXPECTED_ROOT_TREE = "ce7ec4e66d936a53f77e7586977775b8b4eef186"
EXPECTED_SRC_TREE = "f90966498b75bfd29639e0649491d68b2e8a6424"
EXPECTED_ANCHOR_SEMANTIC_SHA256 = "46f09f3ca71f2b9388e86864fe49c1781b35180a1db859d8bea583a3b3bd6cf9"
EXPECTED_PYTHON_FILE_COUNT = 96
EXPECTED_RUNTIME_IMPORTS = (
    "src",
    "src.controllers",
    "src.controllers.distributed_coordinator",
    "src.controllers.freeway_follower",
    "src.controllers.grid_parallel",
    "src.controllers.inflow_outflow_allocation",
    "src.controllers.leader",
    "src.controllers.nash_solver",
    "src.controllers.relaxed_quantization",
    "src.controllers.simplified_inflow_outflow_allocation",
    "src.controllers.spillback_constraints",
    "src.controllers.stackelberg_mpc",
    "src.controllers.structured_grid",
    "src.controllers.urban_follower",
    "src.models",
    "src.models.demand",
    "src.models.metanet",
    "src.models.state",
    "src.models.urban_queue_model",
)
RUNTIME_REQUIRED_CHECK_IDS = (
    "python.rw_python_exe_present",
    "python.rw_python_exe_exists",
    "python.executable_matches",
    "canonical.root_exists",
    "trust_anchor.exists",
    "trust_anchor.json",
    "trust_anchor.semantic_sha256",
    "trust_anchor.schema",
    "trust_anchor.repository",
    "trust_anchor.commit",
    "trust_anchor.root_tree",
    "trust_anchor.src_tree",
    "trust_anchor.object_format",
    "trust_anchor.python_file_count",
    "trust_anchor.paths_sorted",
    "trust_anchor.blob_oids",
    "canonical.anchor_python_file_set",
    "canonical.anchor_python_blobs",
    "canonical.snapshot_commit",
    "canonical.python_tree_nonempty",
    "canonical.tracked_python_complete",
    "canonical.tracked_source_clean",
    "canonical.eol_declared",
    "selected.root_exists",
    "selected.adapter_default_root",
    "selected.snapshot_commit",
    "selected.commit",
    "selected.anchor_python_file_set",
    "selected.anchor_python_blobs",
    "selected.python_file_set",
    "selected.python_tree",
    "selected.tracked_python_complete",
    "selected.tracked_source_clean",
    "canonical.import_probe",
    "selected.import_probe",
    "canonical.external_imports",
    "selected.external_imports",
    "selected.import_module_set",
    "selected.import_module_path_hash",
)
PREFLIGHT_ARTIFACT_KEYS = tuple(PREFLIGHT_DEFAULT_PATHS) + (
    "runtime_source",
    "python_executable",
)
PREFLIGHT_STATIC_CHECK_IDS = (
    "network.exists",
    "network.xml",
    "network.signal_controller_ids_unique",
    "network.signal_head_references_well_formed",
    "network.signal_head_controller_references_resolve",
    "network.model_sc_count",
    "network.resolved_sig_count",
    "network.unique_resolved_sig_count",
    "network.auxiliary_sc_count",
    "network.unclassified_controllers",
    "network.excluded_sc_present",
    "network.excluded_sc_head_reference_count",
    "network.unexpected_excluded_controllers",
    "signal_roles.readable",
    "signal_roles.active_scope",
    "signal_roles.network_alignment",
    "tuning.json",
    "tuning.mapping_json",
    "tuning.detector_mapping_json",
    "generated_vbs.detector_mapping",
    "runtime_source.exists",
    "runtime_source.json",
    "runtime_source.schema",
    "runtime_source.status",
    "runtime_source.reasons",
    "runtime_source.strict",
    "runtime_source.expected_commit",
    "runtime_source.selected_root",
    "runtime_source.selected_tree_hash",
    "runtime_source.selected_python_file_count",
    "runtime_source.adapter_hash",
    "runtime_source.python_executable_hash",
    "runtime_source.snapshot_hash",
    "runtime_source.verifier_hash",
    "runtime_source.anchor_hash",
    "runtime_source.python_executable_path",
    "python.current_executable",
    "runtime_source.selected_import_root",
    "runtime_source.imported_adapter_path",
    "runtime_source.external_imports",
)
PREFLIGHT_RUNTIME_TRUST_CHECK_IDS = (
    "trust_anchor.exists",
    "trust_anchor.json",
    "trust_anchor.semantic_sha256",
    "trust_anchor.schema",
    "trust_anchor.repository",
    "trust_anchor.commit",
    "trust_anchor.root_tree",
    "trust_anchor.src_tree",
    "trust_anchor.object_format",
    "trust_anchor.python_file_count",
    "trust_anchor.paths_sorted",
    "trust_anchor.blob_oids",
    "canonical.anchor_python_file_set",
    "canonical.anchor_python_blobs",
    "selected.anchor_python_file_set",
    "selected.anchor_python_blobs",
    "canonical.snapshot_commit",
    "selected.snapshot_commit",
    "selected.commit",
)
AUDIT_REQUIRED_GATES = (
    "input_provenance",
    "network_xml",
    "signal_controller_scope",
    "link_partition",
    "assignment_ties",
    "adjacency",
    "storage_capacity",
    "vendor_snapshot",
    "numsim_source_match",
    "state_observation_contract",
    "action_inventory",
    "projection_diagnostics",
    "runtime_provenance",
    "preflight_provenance",
    "vissim_error_log",
)
STATE_CSV_HEADER = (
    "sim_sec",
    "total_vehicles",
    "urban_vehicles",
    "freeway_vehicles",
    "ramp_vehicles",
    "boundary_vehicles",
    "other_vehicles",
    "mean_speed_kph",
    "freeway_mean_speed_kph",
    "stopped_vehicles",
    "controller_mode",
    "controller_status",
    "decision_wall_sec",
)

EXPECTED_NAME = "fixed_nocontrol_nominal_d1p00_seed13"
EXPECTED_ANCHORS = (900, 1500, 2100, 2700)
EXPECTED_DECISIONS = (1, 900)
EXPECTED_STATE_TIMES = (1, *range(5, 3601, 5))
EXPECTED_PROFILE = {
    "demand_scale": 1.0,
    "seed": 13,
    "sim_period_sec": 3600,
    "control_start_sec": 900,
    "warmup_sec": 900,
    "controller": "no-control",
    "warmup_controller": "no-control",
    "control_interval_sec": 60,
    "audit_anchors_sec": list(EXPECTED_ANCHORS),
}

PREFLIGHT_FILE_KEYS = {
    "network": "network",
    "tuning": "tuning",
    "calibration": "calibration",
    "control_mapping": "control_mapping",
    "adapter": "adapter",
    "runner": "main_vbs_runner",
    "watchdog": "watchdog_wrapper",
    "generated_vbs": "generated_vbs_config",
}


def _gate(status: str, summary: str, **evidence: Any) -> dict[str, Any]:
    return {"status": status, "summary": summary, "evidence": evidence}


def _read_json(path: Path) -> tuple[Mapping[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(payload, Mapping):
        return None, "JSON root is not an object"
    return payload, None


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _same_number(value: Any, expected: float, tolerance: float = 1e-6) -> bool:
    result = _number(value)
    return result is not None and abs(result - expected) <= tolerance


def _normal_controller(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _normal_path(value: Any, base: Path | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    path = Path(text)
    if not path.is_absolute() and base is not None:
        path = base / path
    return os.path.normcase(str(path.resolve(strict=False)))


def _version_triplet(value: Any) -> tuple[int, int, int] | None:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            return tuple(int(item) for item in value[:3])  # type: ignore[return-value]
        except (TypeError, ValueError):
            return None
    match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)", str(value or ""))
    return tuple(int(item) for item in match.groups()) if match else None


def _recorded_mtime_matches(record: Mapping[str, Any], path: Path) -> bool:
    text = str(record.get("last_write_time_utc", "")).strip()
    if not text or not path.is_file():
        return False
    try:
        recorded = datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return False
    return abs(recorded - path.stat().st_mtime) <= 0.01


def _parse_utc_datetime(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _mtime_within(path: Path, lower: datetime, upper: datetime, tolerance_sec: float) -> bool:
    if not path.is_file():
        return False
    current = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    tolerance = abs(float(tolerance_sec))
    return lower.timestamp() - tolerance <= current.timestamp() <= upper.timestamp() + tolerance


_AUDITOR_MODULE: Any | None = None


def _current_auditor() -> Any:
    global _AUDITOR_MODULE
    if _AUDITOR_MODULE is None:
        path = Path(__file__).resolve().with_name("audit_plant_fidelity.py")
        spec = importlib.util.spec_from_file_location("baseline_current_audit_plant_fidelity", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load current audit_plant_fidelity.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _AUDITOR_MODULE = module
    return _AUDITOR_MODULE


def _parse_csv_ints(value: Any) -> list[int] | None:
    if not isinstance(value, str):
        return None
    try:
        return [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError:
        return None


def _payload_run_id(payload: Mapping[str, Any]) -> str:
    provenance = payload.get("run_provenance")
    if isinstance(provenance, Mapping):
        return str(provenance.get("run_id", "")).strip()
    metadata = payload.get("metadata")
    if isinstance(metadata, Mapping) and isinstance(metadata.get("run_provenance"), Mapping):
        return str(metadata["run_provenance"].get("run_id", "")).strip()
    return str(payload.get("run_id", "")).strip()


def _payload_sim_sec(payload: Mapping[str, Any]) -> float | None:
    value = _number(payload.get("sim_sec"))
    if value is not None:
        return value
    metadata = payload.get("metadata")
    return _number(metadata.get("sim_sec")) if isinstance(metadata, Mapping) else None


def _manifest_artifact(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve(strict=False)), "sha256": _sha256_file(path), "exists": path.is_file()}


def _semantic_json_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalised_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _git_blob_oid(data: bytes) -> str:
    framed = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(framed).hexdigest()


def _tree_digest(files: Mapping[str, Mapping[str, Any]], field: str) -> str:
    digest = hashlib.sha256()
    for relative, record in sorted(files.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record.get(field, "")).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest() if files else ""


def _check_status_map(payload: Mapping[str, Any], label: str, reasons: list[str]) -> dict[str, str]:
    raw = payload.get("checks")
    if not isinstance(raw, list):
        reasons.append(f"{label} checks must be a complete list")
        return {}
    result: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            reasons.append(f"{label} contains a malformed check record")
            continue
        identifier = str(item.get("id", "")).strip()
        if not identifier or identifier in result:
            reasons.append(f"{label} contains a missing or duplicate check id")
            continue
        result[identifier] = str(item.get("status", ""))
    return result


def _validate_runtime_source_artifact(
    runtime: Mapping[str, Any], runtime_source_path: Path, reasons: list[str]
) -> None:
    verifier_path = Path(__file__).resolve().with_name("verify_runtime_source.py")
    command = runtime.get("command_version")
    command = command if isinstance(command, Mapping) else {}
    if (
        command.get("command") != "scripts/verify_runtime_source.py"
        or command.get("version") != RUNTIME_SOURCE_SCHEMA
        or str(command.get("sha256", "")).lower() != str(_sha256_file(verifier_path) or "")
    ):
        reasons.append("runtime-source command_version is not the exact current verifier")

    if runtime.get("expected_snapshot_commit") != EXPECTED_NUMSIM_COMMIT:
        reasons.append("runtime-source expected snapshot commit mismatch")
    checks = _check_status_map(runtime, "runtime-source", reasons)
    if set(checks) != set(RUNTIME_REQUIRED_CHECK_IDS):
        reasons.append("runtime-source check inventory is incomplete or unexpected")
    if any(checks.get(identifier) != STATUS_PASS for identifier in RUNTIME_REQUIRED_CHECK_IDS):
        reasons.append("runtime-source does not PASS every required check")

    trust = runtime.get("trust_anchor")
    trust = trust if isinstance(trust, Mapping) else {}
    expected_trust = {
        "schema_version": "numsim-upstream-tree-v1",
        "upstream_repository": "https://github.com/Ming2you/Numerical-Sim.git",
        "commit": EXPECTED_NUMSIM_COMMIT,
        "root_tree": EXPECTED_ROOT_TREE,
        "src_tree": EXPECTED_SRC_TREE,
        "object_format": "sha1",
        "python_file_count": EXPECTED_PYTHON_FILE_COUNT,
        "semantic_sha256": EXPECTED_ANCHOR_SEMANTIC_SHA256,
    }
    if any(trust.get(key) != value for key, value in expected_trust.items()):
        reasons.append("runtime-source trust-anchor semantic identity mismatch")
    anchor_path_text = str(trust.get("path", "")).strip()
    anchor_path = Path(anchor_path_text) if anchor_path_text else Path("__missing_anchor__")
    anchor, anchor_error = _read_json(anchor_path)
    if anchor_error or anchor is None:
        reasons.append("runtime-source trust-anchor file is unavailable")
        anchor_blobs: Mapping[str, Any] = {}
    else:
        if _semantic_json_sha256(anchor) != EXPECTED_ANCHOR_SEMANTIC_SHA256:
            reasons.append("runtime-source trust-anchor file semantic hash mismatch")
        if str(trust.get("checkout_sha256", "")).lower() != str(_sha256_file(anchor_path) or ""):
            reasons.append("runtime-source trust-anchor checkout hash mismatch")
        anchor_blobs = anchor.get("python_blobs") if isinstance(anchor.get("python_blobs"), Mapping) else {}
        if (
            anchor.get("commit") != EXPECTED_NUMSIM_COMMIT
            or anchor.get("root_tree") != EXPECTED_ROOT_TREE
            or anchor.get("src_tree") != EXPECTED_SRC_TREE
            or anchor.get("python_file_count") != EXPECTED_PYTHON_FILE_COUNT
            or len(anchor_blobs) != EXPECTED_PYTHON_FILE_COUNT
        ):
            reasons.append("runtime-source trust-anchor file constants mismatch")

    canonical = runtime.get("canonical")
    selected = runtime.get("selected")
    canonical = canonical if isinstance(canonical, Mapping) else {}
    selected = selected if isinstance(selected, Mapping) else {}
    canonical_root_text = str(canonical.get("root", "")).strip()
    selected_root_text = str(selected.get("root", "")).strip()
    canonical_root = Path(canonical_root_text) if canonical_root_text else Path("__missing_canonical__")
    selected_root = Path(selected_root_text) if selected_root_text else Path("__missing_selected__")
    if runtime.get("selected_is_canonical") is not True or _normal_path(canonical_root) != _normal_path(selected_root):
        reasons.append("runtime-source selected root is not the canonical root")

    source_root = canonical_root / "src"
    source_paths = sorted(
        source_root.rglob("*.py") if source_root.is_dir() else [],
        key=lambda path: path.relative_to(source_root).as_posix(),
    )
    local_files: dict[str, dict[str, str]] = {}
    for source_path in source_paths:
        relative = source_path.relative_to(source_root).as_posix()
        data = _normalised_bytes(source_path)
        local_files[relative] = {
            "normalised_sha256": hashlib.sha256(data).hexdigest(),
            "normalised_git_blob_oid": _git_blob_oid(data),
        }
    canonical_files = canonical.get("files") if isinstance(canonical.get("files"), Mapping) else {}
    selected_files = selected.get("files") if isinstance(selected.get("files"), Mapping) else {}
    if (
        len(local_files) != EXPECTED_PYTHON_FILE_COUNT
        or set(canonical_files) != set(local_files)
        or set(selected_files) != set(local_files)
        or set(f"src/{path}" for path in local_files) != set(anchor_blobs)
    ):
        reasons.append("runtime-source canonical/selected/anchor path identity mismatch")
    else:
        for relative, local in local_files.items():
            canonical_record = canonical_files.get(relative)
            selected_record = selected_files.get(relative)
            canonical_record = canonical_record if isinstance(canonical_record, Mapping) else {}
            selected_record = selected_record if isinstance(selected_record, Mapping) else {}
            expected_blob = str(anchor_blobs.get(f"src/{relative}", ""))
            if (
                canonical_record.get("normalised_sha256") != local["normalised_sha256"]
                or selected_record.get("normalised_sha256") != local["normalised_sha256"]
                or canonical_record.get("normalised_git_blob_oid") != local["normalised_git_blob_oid"]
                or selected_record.get("normalised_git_blob_oid") != local["normalised_git_blob_oid"]
                or local["normalised_git_blob_oid"] != expected_blob
            ):
                reasons.append(f"runtime-source canonical/selected blob mismatch: {relative}")
                break
    for label, record in (("canonical", canonical), ("selected", selected)):
        files = record.get("files") if isinstance(record.get("files"), Mapping) else {}
        if (
            record.get("snapshot_commit") != EXPECTED_NUMSIM_COMMIT
            or record.get("python_file_count") != EXPECTED_PYTHON_FILE_COUNT
            or record.get("normalised_tree_sha256") != _tree_digest(files, "normalised_sha256")
        ):
            reasons.append(f"runtime-source {label} source-tree summary mismatch")

    imports = runtime.get("imports")
    imports = imports if isinstance(imports, Mapping) else {}
    canonical_imports = imports.get("canonical") if isinstance(imports.get("canonical"), Mapping) else {}
    selected_imports = imports.get("selected") if isinstance(imports.get("selected"), Mapping) else {}
    for label, probe, root in (
        ("canonical", canonical_imports, canonical_root),
        ("selected", selected_imports, selected_root),
    ):
        modules = probe.get("modules") if isinstance(probe.get("modules"), Mapping) else {}
        if (
            probe.get("ok") is not True
            or probe.get("returncode") != 0
            or probe.get("external_modules") != []
            or _normal_path(probe.get("adapter_default_root")) != _normal_path(root)
            or set(modules) != set(EXPECTED_RUNTIME_IMPORTS)
        ):
            reasons.append(f"runtime-source {label} import evidence is incomplete")
            continue
        for module_name, raw_record in modules.items():
            record = raw_record if isinstance(raw_record, Mapping) else {}
            module_path_text = str(record.get("path", "")).strip()
            module_path = Path(module_path_text) if module_path_text else Path("__missing_module__")
            try:
                expected_relative = module_path.resolve().relative_to(root.resolve()).as_posix()
            except (OSError, ValueError):
                expected_relative = ""
            if (
                not module_path.is_file()
                or record.get("relative_path") != expected_relative
                or record.get("checkout_sha256") != _sha256_file(module_path)
                or record.get("normalised_sha256") != hashlib.sha256(_normalised_bytes(module_path)).hexdigest()
            ):
                reasons.append(f"runtime-source {label} import identity mismatch: {module_name}")
                break
    canonical_modules = canonical_imports.get("modules") if isinstance(canonical_imports.get("modules"), Mapping) else {}
    selected_modules = selected_imports.get("modules") if isinstance(selected_imports.get("modules"), Mapping) else {}
    if canonical_modules != selected_modules:
        reasons.append("runtime-source canonical and selected import identities differ")

    input_hashes = runtime.get("input_hashes")
    input_hashes = input_hashes if isinstance(input_hashes, Mapping) else {}
    if str(input_hashes.get("upstream_tree_anchor_semantic_sha256", "")).lower() != EXPECTED_ANCHOR_SEMANTIC_SHA256:
        reasons.append("runtime-source input hash does not bind the anchor semantics")
    if str(input_hashes.get("upstream_tree_anchor_sha256", "")).lower() != str(_sha256_file(anchor_path) or ""):
        reasons.append("runtime-source input hash does not bind the anchor file")


def _expected_preflight_check_ids(preflight: Mapping[str, Any]) -> set[str]:
    identifiers = set(PREFLIGHT_STATIC_CHECK_IDS)
    for key in PREFLIGHT_ARTIFACT_KEYS:
        identifiers.update((f"artifact.{key}.exists", f"artifact.{key}.sha256"))
    identifiers.update(
        f"runtime_source.required_check.{identifier}"
        for identifier in PREFLIGHT_RUNTIME_TRUST_CHECK_IDS
    )
    network = preflight.get("network")
    network = network if isinstance(network, Mapping) else {}
    for record in network.get("model_controllers", []):
        if isinstance(record, Mapping):
            number = str(record.get("controller_no", "")).strip()
            identifiers.update((f"signal_program.SC{number}.resolved", f"signal_program.SC{number}.sha256"))
    return identifiers


def _validate_preflight_artifact(
    preflight: Mapping[str, Any], runtime: Mapping[str, Any] | None, runtime_source_path: Path, reasons: list[str]
) -> None:
    builder_path = Path(__file__).resolve().with_name("build_preflight_manifest.py")
    command = preflight.get("command_version")
    command = command if isinstance(command, Mapping) else {}
    if (
        command.get("command") != "scripts/build_preflight_manifest.py"
        or command.get("version") != PREFLIGHT_SCHEMA
        or str(command.get("sha256", "")).lower() != str(_sha256_file(builder_path) or "")
    ):
        reasons.append("preflight command_version is not the exact current builder")
    checks = _check_status_map(preflight, "preflight", reasons)
    expected_checks = _expected_preflight_check_ids(preflight)
    if set(checks) != expected_checks:
        reasons.append("preflight check inventory is incomplete or unexpected")
    if any(checks.get(identifier) != STATUS_PASS for identifier in expected_checks):
        reasons.append("preflight does not PASS every required check")

    artifacts = preflight.get("artifacts")
    artifacts = artifacts if isinstance(artifacts, Mapping) else {}
    input_hashes = preflight.get("input_hashes")
    input_hashes = input_hashes if isinstance(input_hashes, Mapping) else {}
    if set(artifacts) != set(PREFLIGHT_ARTIFACT_KEYS):
        reasons.append("preflight artifact inventory is incomplete or unexpected")
    for key in PREFLIGHT_ARTIFACT_KEYS:
        record = artifacts.get(key)
        record = record if isinstance(record, Mapping) else {}
        path_text = str(record.get("path", "")).strip()
        path = Path(path_text) if path_text else Path("__missing_preflight_artifact__")
        actual_hash = _sha256_file(path)
        if (
            record.get("exists") is not True
            or not actual_hash
            or str(record.get("sha256", "")).lower() != actual_hash
            or str(input_hashes.get(key, "")).lower() != actual_hash
        ):
            reasons.append(f"preflight artifact identity mismatch: {key}")
    runtime_identity = preflight.get("runtime_source_identity")
    runtime_identity = runtime_identity if isinstance(runtime_identity, Mapping) else {}
    runtime_artifact = runtime_identity.get("manifest")
    runtime_artifact = runtime_artifact if isinstance(runtime_artifact, Mapping) else {}
    if (
        _normal_path(runtime_artifact.get("path")) != _normal_path(runtime_source_path)
        or str(runtime_artifact.get("sha256", "")).lower() != str(_sha256_file(runtime_source_path) or "")
        or runtime_identity.get("schema_version") != RUNTIME_SOURCE_SCHEMA
        or runtime_identity.get("status") != STATUS_PASS
        or runtime_identity.get("strict") is not True
        or runtime_identity.get("expected_snapshot_commit") != EXPECTED_NUMSIM_COMMIT
        or runtime_identity.get("selected_is_canonical") is not True
    ):
        reasons.append("preflight runtime-source manifest linkage or strict identity mismatch")
    if runtime is not None:
        for key in ("trust_anchor", "selected_is_canonical", "expected_snapshot_commit"):
            if runtime_identity.get(key) != runtime.get(key):
                reasons.append(f"preflight runtime-source identity differs for {key}")
        selected = runtime.get("selected") if isinstance(runtime.get("selected"), Mapping) else {}
        preflight_selected = runtime_identity.get("selected") if isinstance(runtime_identity.get("selected"), Mapping) else {}
        if (
            _normal_path(preflight_selected.get("root")) != _normal_path(selected.get("root"))
            or preflight_selected.get("snapshot_commit") != selected.get("snapshot_commit")
            or preflight_selected.get("reported_python_file_count") != selected.get("python_file_count")
            or preflight_selected.get("reported_normalised_tree_sha256") != selected.get("normalised_tree_sha256")
        ):
            reasons.append("preflight selected source identity differs from runtime-source")
    network = preflight.get("network")
    network = network if isinstance(network, Mapping) else {}
    model = [item for item in network.get("model_controllers", []) if isinstance(item, Mapping)]
    resolved = [item for item in network.get("resolved_signal_programs", []) if isinstance(item, Mapping)]
    if len(model) != 41 or len(resolved) != 41:
        reasons.append("preflight does not contain the complete 41-controller network evidence")
    for record in resolved:
        path_text = str(record.get("path", "")).strip()
        path = Path(path_text) if path_text else Path("__missing_signal_program__")
        actual_hash = _sha256_file(path)
        key = f"signal_program.SC{record.get('controller_no')}"
        if not actual_hash or str(record.get("sha256", "")).lower() != actual_hash or str(input_hashes.get(key, "")).lower() != actual_hash:
            reasons.append(f"preflight signal-program identity mismatch: {key}")


def _validate_audit_artifact(
    audit: Mapping[str, Any], baseline_dir: Path, preflight: Mapping[str, Any] | None, reasons: list[str]
) -> None:
    command_path = Path(__file__).resolve().with_name("audit_plant_fidelity.py")
    command = audit.get("command_version")
    command = command if isinstance(command, Mapping) else {}
    if (
        command.get("command") != "scripts/audit_plant_fidelity.py"
        or command.get("version") != AUDIT_SCHEMA
        or str(command.get("sha256", "")).lower() != str(_sha256_file(command_path) or "")
    ):
        reasons.append("audit command_version is not the exact current auditor")

    invocation = audit.get("invocation")
    if not isinstance(invocation, Mapping):
        reasons.append("audit is missing a replayable deterministic invocation")
    else:
        if _normal_path(invocation.get("repo")) != _normal_path(command_path.parents[1]):
            reasons.append("audit invocation repo differs from the current auditor repository")
        if _normal_path(invocation.get("action_dir")) != _normal_path(baseline_dir):
            reasons.append("audit invocation action_dir differs from the baseline directory")
        if invocation.get("strict") is not True or invocation.get("require_complete") is not True:
            reasons.append("audit invocation is not strict complete")
        if invocation.get("required_gate") != list(AUDIT_REQUIRED_GATES):
            reasons.append("audit invocation does not name the exact baseline required gates")
        try:
            auditor = _current_auditor()
            rebuilt, rebuilt_exit = auditor.build_complete_manifest_from_invocation(invocation)
            supplied_projection = auditor.canonical_semantic_projection(audit)
            rebuilt_projection = auditor.canonical_semantic_projection(rebuilt)
            supplied_hash = auditor.semantic_projection_sha256(audit)
            rebuilt_hash = auditor.semantic_projection_sha256(rebuilt)
            if str(audit.get("semantic_projection_sha256", "")).lower() != supplied_hash:
                reasons.append("audit semantic projection hash does not match the supplied evidence")
            if rebuilt_exit != 0 or rebuilt.get("status") != STATUS_PASS:
                reasons.append("current auditor replay is not strict complete PASS")
            if supplied_projection != rebuilt_projection or supplied_hash != rebuilt_hash:
                reasons.append("audit semantic evidence differs from a current auditor replay")
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            reasons.append(f"audit current-code replay failed: {type(exc).__name__}: {exc}")
    for key in ("input_hashes", "command_version", "reasons", "sample_dimensions", "units", "downstream_consumers", "artifact_evidence"):
        if key not in audit:
            reasons.append(f"audit is missing global evidence key: {key}")

    gates = audit.get("gates")
    gates = gates if isinstance(gates, Mapping) else {}
    policy = audit.get("completion_policy")
    policy = policy if isinstance(policy, Mapping) else {}
    required = policy.get("required_gates")
    if not isinstance(required, list) or required != list(AUDIT_REQUIRED_GATES):
        reasons.append("audit completion policy does not name the exact baseline required gates")
    if policy.get("required_gate_count") != len(AUDIT_REQUIRED_GATES):
        reasons.append("audit completion policy required gate count mismatch")
    if any(not isinstance(gates.get(name), Mapping) or gates[name].get("status") != STATUS_PASS for name in AUDIT_REQUIRED_GATES):
        reasons.append("audit does not PASS every required baseline gate")
    summary = audit.get("gate_summary")
    summary = summary if isinstance(summary, Mapping) else {}
    counts = {
        STATUS_PASS: sum(isinstance(item, Mapping) and item.get("status") == STATUS_PASS for item in gates.values()),
        STATUS_FAIL: sum(isinstance(item, Mapping) and item.get("status") == STATUS_FAIL for item in gates.values()),
        STATUS_NOT_EVALUATED: sum(isinstance(item, Mapping) and item.get("status") == STATUS_NOT_EVALUATED for item in gates.values()),
    }
    expected_overall = STATUS_FAIL if counts[STATUS_FAIL] else (STATUS_NOT_EVALUATED if counts[STATUS_NOT_EVALUATED] else STATUS_PASS)
    if (
        summary.get("pass") != counts[STATUS_PASS]
        or summary.get("fail") != counts[STATUS_FAIL]
        or summary.get("not_evaluated") != counts[STATUS_NOT_EVALUATED]
        or summary.get("overall") != expected_overall
        or summary.get("strict_complete_status") != STATUS_PASS
    ):
        reasons.append("audit gate_summary does not match the complete gate inventory")

    action_directory = audit.get("action_directory")
    action_directory = action_directory if isinstance(action_directory, Mapping) else {}
    artifact_records = action_directory.get("artifact_files")
    artifact_records = artifact_records if isinstance(artifact_records, list) else []
    recorded: dict[str, Mapping[str, Any]] = {}
    for raw in artifact_records:
        record = raw if isinstance(raw, Mapping) else {}
        relative = str(record.get("relative_path", "")).replace("\\", "/").strip()
        if not relative or relative in recorded:
            reasons.append("audit action artifact inventory contains malformed or duplicate paths")
            continue
        recorded[relative] = record
    current_paths = sorted(
        (path for path in baseline_dir.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(baseline_dir).as_posix(),
    )
    current = {path.relative_to(baseline_dir).as_posix(): path for path in current_paths}
    if set(recorded) != set(current) or action_directory.get("artifact_file_count") != len(current):
        reasons.append("audit action-directory current file set/count differs from baseline")
    for relative, path in current.items():
        record = recorded.get(relative, {})
        if (
            _normal_path(record.get("path")) != _normal_path(path)
            or record.get("exists") is not True
            or record.get("is_file") is not True
            or record.get("size_bytes") != path.stat().st_size
            or str(record.get("sha256", "")).lower() != str(_sha256_file(path) or "")
        ):
            reasons.append(f"audit action artifact identity mismatch: {relative}")
            break
    expected_state_files = sorted(
        str(path.resolve(strict=False))
        for path in (*baseline_dir.rglob("state_*.json"), *baseline_dir.rglob("anchor_*.json"))
    )
    expected_action_files = sorted(str(path.resolve(strict=False)) for path in baseline_dir.rglob("action_*.json"))
    if (
        action_directory.get("state_file_count") != len(expected_state_files)
        or sorted(action_directory.get("state_files", [])) != expected_state_files
        or action_directory.get("action_file_count") != len(expected_action_files)
        or sorted(action_directory.get("action_files", [])) != expected_action_files
        or action_directory.get("invalid_state_json_count") != 0
        or action_directory.get("invalid_action_json_count") != 0
        or action_directory.get("errors") != []
    ):
        reasons.append("audit action JSON inventory/count/status differs from baseline")

    inputs = audit.get("inputs")
    inputs = inputs if isinstance(inputs, Mapping) else {}
    primary = inputs.get("primary") if isinstance(inputs.get("primary"), Mapping) else {}
    signals = inputs.get("signal_programs") if isinstance(inputs.get("signal_programs"), list) else []
    audit_hashes = audit.get("input_hashes")
    audit_hashes = audit_hashes if isinstance(audit_hashes, Mapping) else {}
    expected_hashes: dict[str, str | None] = {}
    for name, raw in primary.items():
        record = raw if isinstance(raw, Mapping) else {}
        path_text = str(record.get("path", "")).strip()
        path = Path(path_text) if path_text else Path("__missing_audit_input__")
        actual_hash = _sha256_file(path)
        expected_hashes[f"primary.{name}"] = actual_hash
        if record.get("exists") is not True or record.get("is_file") is not True or str(record.get("sha256", "")).lower() != str(actual_hash or ""):
            reasons.append(f"audit primary input identity mismatch: {name}")
    for raw in signals:
        record = raw if isinstance(raw, Mapping) else {}
        path_text = str(record.get("path", "")).strip()
        path = Path(path_text) if path_text else Path("__missing_audit_signal__")
        actual_hash = _sha256_file(path)
        expected_hashes[f"signal_program.{path.name}"] = actual_hash
        if record.get("exists") is not True or record.get("is_file") is not True or str(record.get("sha256", "")).lower() != str(actual_hash or ""):
            reasons.append(f"audit signal-program identity mismatch: {path.name}")
    expected_hashes.update({f"action_artifact.{relative}": _sha256_file(path) for relative, path in current.items()})
    if dict(sorted(audit_hashes.items())) != dict(sorted(expected_hashes.items())):
        reasons.append("audit global input_hashes do not match its current input/artifact evidence")

    if preflight is not None:
        preflight_artifacts = preflight.get("artifacts")
        preflight_artifacts = preflight_artifacts if isinstance(preflight_artifacts, Mapping) else {}
        audit_to_preflight = {
            "network": "network",
            "tuning": "tuning",
            "calibration": "calibration",
            "control_mapping": "control_mapping",
            "detector_mapping": "detector_mapping",
            "generated_vbs_config": "generated_vbs",
            "adapter": "adapter",
        }
        for audit_key, preflight_key in audit_to_preflight.items():
            audit_record = primary.get(audit_key) if isinstance(primary.get(audit_key), Mapping) else {}
            preflight_record = preflight_artifacts.get(preflight_key) if isinstance(preflight_artifacts.get(preflight_key), Mapping) else {}
            if (
                _normal_path(audit_record.get("path")) != _normal_path(preflight_record.get("path"))
                or str(audit_record.get("sha256", "")).lower() != str(preflight_record.get("sha256", "")).lower()
            ):
                reasons.append(f"audit primary input differs from preflight: {audit_key}")
        preflight_network = preflight.get("network")
        preflight_network = preflight_network if isinstance(preflight_network, Mapping) else {}
        preflight_signal_hashes = {
            _normal_path(record.get("path")): str(record.get("sha256", "")).lower()
            for record in preflight_network.get("resolved_signal_programs", [])
            if isinstance(record, Mapping)
        }
        audit_signal_hashes = {
            _normal_path(record.get("path")): str(record.get("sha256", "")).lower()
            for record in signals
            if isinstance(record, Mapping) and _normal_path(record.get("path")) in preflight_signal_hashes
        }
        if audit_signal_hashes != preflight_signal_hashes:
            reasons.append("audit signal-program evidence differs from preflight")
        runtime_identity = preflight.get("runtime_source_identity")
        runtime_identity = runtime_identity if isinstance(runtime_identity, Mapping) else {}
        selected = runtime_identity.get("selected")
        selected = selected if isinstance(selected, Mapping) else {}
        selected_root = selected.get("root")
        actual_numsim = audit.get("actual_numsim")
        actual_numsim = actual_numsim if isinstance(actual_numsim, Mapping) else {}
        if (
            not isinstance(invocation, Mapping)
            or not str(invocation.get("numsim_root", "")).strip()
            or _normal_path(invocation.get("numsim_root")) != _normal_path(selected_root)
            or _normal_path(actual_numsim.get("actual_root")) != _normal_path(selected_root)
        ):
            reasons.append("audit NumSim invocation/source differs from the preflight selected runtime root")


def _preflight_fingerprint_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    network = manifest.get("network") if isinstance(manifest.get("network"), Mapping) else {}
    runtime = manifest.get("runtime_source_identity") if isinstance(manifest.get("runtime_source_identity"), Mapping) else {}
    return {
        "schema_version": manifest.get("schema_version"),
        "input_hashes": manifest.get("input_hashes"),
        "command_version": manifest.get("command_version"),
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
                if isinstance(item, Mapping) and isinstance(item.get("signal_program"), Mapping)
            ],
            "excluded_controller": network.get("excluded_controller"),
            "auxiliary_controllers": network.get("auxiliary_controllers", []),
        },
        "runtime_source": {
            "schema_version": runtime.get("schema_version", ""),
            "expected_snapshot_commit": runtime.get("expected_snapshot_commit", ""),
            "selected_is_canonical": runtime.get("selected_is_canonical", False),
            "selected": runtime.get("selected", {}),
            "python_sha256": (runtime.get("python") or {}).get("sha256", "") if isinstance(runtime.get("python"), Mapping) else "",
        },
    }


def _validate_manifest_chain(
    baseline_dir: Path,
    runtime_source_path: Path,
    preflight_path: Path,
    audit_path: Path,
) -> tuple[dict[str, Any], Mapping[str, Any] | None, Mapping[str, Any] | None, Mapping[str, Any] | None]:
    reasons: list[str] = []
    runtime, runtime_error = _read_json(runtime_source_path)
    preflight, preflight_error = _read_json(preflight_path)
    audit, audit_error = _read_json(audit_path)
    if runtime_error:
        reasons.append(f"runtime-source: {runtime_error}")
    if preflight_error:
        reasons.append(f"preflight: {preflight_error}")
    if audit_error:
        reasons.append(f"audit: {audit_error}")
    if runtime is not None:
        if runtime.get("schema_version") != RUNTIME_SOURCE_SCHEMA:
            reasons.append("runtime-source schema_version mismatch")
        if runtime.get("status") != STATUS_PASS or runtime.get("strict") is not True or runtime.get("reasons") != []:
            reasons.append("runtime-source must be strict PASS with no reasons")
        _validate_runtime_source_artifact(runtime, runtime_source_path, reasons)
    if preflight is not None:
        if preflight.get("schema_version") != PREFLIGHT_SCHEMA:
            reasons.append("preflight schema_version mismatch")
        if preflight.get("status") != STATUS_PASS or preflight.get("reasons") != []:
            reasons.append("preflight must be PASS with no reasons")
        fingerprint = str(preflight.get("fingerprint_sha256", "")).lower()
        fingerprint_record = preflight.get("fingerprint")
        recorded = str(fingerprint_record.get("sha256", "")).lower() if isinstance(fingerprint_record, Mapping) else ""
        try:
            calculated = hashlib.sha256(
                json.dumps(_preflight_fingerprint_payload(preflight), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        except (KeyError, TypeError, ValueError):
            calculated = ""
            reasons.append("preflight fingerprint payload is malformed")
        if not fingerprint or fingerprint != recorded or fingerprint != calculated:
            reasons.append("preflight fingerprint is missing or invalid")
        runtime_identity = preflight.get("runtime_source_identity")
        runtime_identity = runtime_identity if isinstance(runtime_identity, Mapping) else {}
        runtime_artifact = runtime_identity.get("manifest")
        runtime_artifact = runtime_artifact if isinstance(runtime_artifact, Mapping) else {}
        if _normal_path(runtime_artifact.get("path")) != _normal_path(runtime_source_path):
            reasons.append("preflight runtime-source path mismatch")
        if str(runtime_artifact.get("sha256", "")).lower() != str(_sha256_file(runtime_source_path) or ""):
            reasons.append("preflight runtime-source SHA-256 mismatch")
        if runtime is not None and runtime_identity.get("schema_version") != runtime.get("schema_version"):
            reasons.append("preflight runtime-source schema linkage mismatch")
        _validate_preflight_artifact(preflight, runtime, runtime_source_path, reasons)
    if audit is not None:
        if audit.get("schema_version") != AUDIT_SCHEMA:
            reasons.append("audit schema_version mismatch")
        if audit.get("status") != STATUS_PASS or audit.get("strict") is not True or audit.get("require_complete") is not True:
            reasons.append("audit must be strict complete PASS")
        if audit.get("reasons") != []:
            reasons.append("audit reasons must be empty")
        action_directory = audit.get("action_directory") if isinstance(audit.get("action_directory"), Mapping) else {}
        if _normal_path(action_directory.get("path")) != _normal_path(baseline_dir):
            reasons.append("audit action_directory.path differs from baseline directory")
        summary = audit.get("gate_summary") if isinstance(audit.get("gate_summary"), Mapping) else {}
        policy = audit.get("completion_policy") if isinstance(audit.get("completion_policy"), Mapping) else {}
        if summary.get("fail") != 0 or summary.get("strict_complete_status") != STATUS_PASS:
            reasons.append("audit gate_summary is not strict PASS")
        if policy.get("complete") is not True or policy.get("non_pass_gates") != []:
            reasons.append("audit completion_policy is not complete")
        gates = audit.get("gates") if isinstance(audit.get("gates"), Mapping) else {}
        if (gates.get("preflight_provenance") or {}).get("status") != STATUS_PASS:
            reasons.append("audit preflight_provenance gate is not PASS")
        contract = action_directory.get("preflight_contract", {})
        records = contract.get("records", []) if isinstance(contract, Mapping) else []
        expected_fingerprint = str(preflight.get("fingerprint_sha256", "")).lower() if preflight else ""
        expected_hash = str(_sha256_file(preflight_path) or "")
        if not isinstance(records, list) or len(records) != 1:
            reasons.append("audit must contain exactly one preflight provenance record")
        else:
            record = records[0] if isinstance(records[0], Mapping) else {}
            if (
                record.get("status") != STATUS_PASS
                or _normal_path(record.get("preflight_path")) != _normal_path(preflight_path)
                or str(record.get("preflight_sha256", "")).lower() != expected_hash
                or str(record.get("preflight_fingerprint_sha256", "")).lower() != expected_fingerprint
            ):
                reasons.append("audit preflight provenance differs from supplied preflight")
        _validate_audit_artifact(audit, baseline_dir, preflight, reasons)
    status = STATUS_NOT_EVALUATED if (runtime is None or preflight is None or audit is None) and not reasons else (STATUS_FAIL if reasons else STATUS_PASS)
    return (
        _gate(
            status,
            "runtime-source, preflight, and audit are not one strict evidence chain" if reasons else "runtime-source, preflight, and audit form one strict evidence chain",
            runtime_source=_manifest_artifact(runtime_source_path),
            preflight=_manifest_artifact(preflight_path),
            audit=_manifest_artifact(audit_path),
            preflight_fingerprint=preflight.get("fingerprint_sha256") if preflight else None,
            reasons=reasons,
        ),
        runtime,
        preflight,
        audit,
    )


def _find_provenance(baseline_dir: Path) -> tuple[Mapping[str, Any] | None, Path | None, list[str], bool]:
    paths = sorted(baseline_dir.glob("run_provenance_*.json")) if baseline_dir.is_dir() else []
    if len(paths) != 1:
        return None, None, [f"expected exactly one run provenance JSON, found {len(paths)}"], not paths
    payload, error = _read_json(paths[0])
    return payload, paths[0], ([error] if error else []), False


def _validate_provenance(
    baseline_dir: Path,
    preflight_path: Path,
    preflight: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], Mapping[str, Any] | None, Path | None]:
    payload, path, reasons, missing = _find_provenance(baseline_dir)
    if payload is None or path is None:
        return _gate(STATUS_NOT_EVALUATED if missing else STATUS_FAIL, "canonical run provenance is unavailable", reasons=reasons), None, path
    name = str(payload.get("name", "")).strip()
    run_id = str(payload.get("run_id", "")).strip()
    expected = {
        "schema_version": 1,
        "name": EXPECTED_NAME,
        "seed": 13,
        "sim_period_sec": 3600,
        "control_interval_sec": 60,
        "control_start_sec": 900,
        "state_log_interval_sec": 5,
        "demand_scale": 1.0,
    }
    for key, value in expected.items():
        actual = payload.get(key)
        if isinstance(value, (int, float)) and key not in {"schema_version", "seed"}:
            if not _same_number(actual, float(value)):
                reasons.append(f"{key} must be {value}")
        elif actual != value:
            reasons.append(f"{key} must be {value}")
    if path.name != f"run_provenance_{name}.json":
        reasons.append("provenance filename does not match name")
    decision_dirs = sorted(item.name for item in baseline_dir.glob("decisions_*") if item.is_dir())
    if decision_dirs != [f"decisions_{EXPECTED_NAME}"]:
        reasons.append("baseline directory must contain exactly one canonical decision directory")
    for pattern, expected_name in (
        ("state_*.csv", f"state_{EXPECTED_NAME}.csv"),
        ("action_*.csv", f"action_{EXPECTED_NAME}.csv"),
        ("runlog_*.txt", f"runlog_{EXPECTED_NAME}.txt"),
    ):
        names = sorted(item.name for item in baseline_dir.glob(pattern) if item.is_file())
        if names != [expected_name]:
            reasons.append(f"baseline directory must contain exactly one {pattern} artifact")
    if not run_id:
        reasons.append("run_id is empty")
    if str(payload.get("demand_profile", "")).strip():
        reasons.append("demand_profile must be empty")
    if _normal_controller(payload.get("controller")) != "no-control":
        reasons.append("controller must be no-control")
    if _normal_controller(payload.get("warmup_controller")) != "no-control":
        reasons.append("warmup_controller must be no-control")
    if _parse_csv_ints(payload.get("audit_anchors_sec")) != list(EXPECTED_ANCHORS):
        reasons.append("audit_anchors_sec must be 900,1500,2100,2700")

    if preflight is None:
        reasons.append("preflight is unavailable")
    else:
        reference = payload.get("preflight_manifest")
        reference = reference if isinstance(reference, Mapping) else {}
        if _normal_path(reference.get("path")) != _normal_path(preflight_path):
            reasons.append("run preflight path mismatch")
        if str(reference.get("sha256", "")).lower() != str(_sha256_file(preflight_path) or ""):
            reasons.append("run preflight SHA-256 mismatch")
        if str(payload.get("preflight_fingerprint_sha256", "")).lower() != str(preflight.get("fingerprint_sha256", "")).lower():
            reasons.append("run preflight fingerprint mismatch")
        artifacts = preflight.get("artifacts") if isinstance(preflight.get("artifacts"), Mapping) else {}
        files = payload.get("files") if isinstance(payload.get("files"), Mapping) else {}
        for preflight_key, run_key in PREFLIGHT_FILE_KEYS.items():
            expected_record = artifacts.get(preflight_key)
            actual_record = files.get(run_key)
            expected_record = expected_record if isinstance(expected_record, Mapping) else {}
            actual_record = actual_record if isinstance(actual_record, Mapping) else {}
            expected_path = Path(str(expected_record.get("path", ""))) if expected_record.get("path") else None
            live_hash = _sha256_file(expected_path) if expected_path else None
            if (
                _normal_path(actual_record.get("path")) != _normal_path(expected_record.get("path"))
                or str(actual_record.get("sha256", "")).lower() != str(expected_record.get("sha256", "")).lower()
                or not live_hash
                or live_hash != str(expected_record.get("sha256", "")).lower()
            ):
                reasons.append(f"run {run_key} differs from preflight {preflight_key}")
        preserved = files.get("preserved_generated_vbs_config")
        generated = artifacts.get("generated_vbs")
        preserved = preserved if isinstance(preserved, Mapping) else {}
        generated = generated if isinstance(generated, Mapping) else {}
        preserved_path = Path(str(preserved.get("path", ""))) if preserved.get("path") else Path("__missing__")
        if (
            not preserved_path.is_file()
            or str(preserved.get("sha256", "")).lower() != str(generated.get("sha256", "")).lower()
            or _sha256_file(preserved_path) != str(generated.get("sha256", "")).lower()
        ):
            reasons.append("preserved generated VBS config is missing or hash-mismatched")
        preflight_network = preflight.get("network") if isinstance(preflight.get("network"), Mapping) else {}
        expected_signals = {
            (_normal_path(record.get("path")), str(record.get("sha256", "")).lower())
            for record in preflight_network.get("resolved_signal_programs", [])
            if isinstance(record, Mapping)
        }
        actual_signals = {
            (_normal_path(record.get("path")), str(record.get("sha256", "")).lower())
            for record in payload.get("signal_programs", [])
            if isinstance(record, Mapping)
        }
        if not expected_signals or not expected_signals.issubset(actual_signals):
            reasons.append("run signal-program hashes do not cover the preflight set")
    return _gate(STATUS_FAIL if reasons else STATUS_PASS, "run provenance is not canonical or preflight-bound" if reasons else "one canonical preflight-bound run provenance was found", path=str(path), run_id=run_id, reasons=reasons), payload, path


def _summary_value(text: str, key: str) -> tuple[str | None, str | None]:
    values = re.findall(rf"(?m)^{re.escape(key)}=([^\r\n]+)\s*$", text)
    if len(values) != 1:
        return None, f"expected one {key} line, found {len(values)}"
    return values[0].strip(), None


def _read_runlog(path: Path) -> tuple[str, str | None]:
    if not path.is_file():
        return "", "run log is missing"
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace"), None
    except OSError as exc:
        return "", str(exc)


def _validate_runlog(path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    text, error = _read_runlog(path)
    if error:
        return _gate(STATUS_NOT_EVALUATED, "run log is unavailable", path=str(path), error=error), {}
    reasons: list[str] = []
    parsed: dict[str, str] = {}
    expected = {
        "DECISIONS_OK": 2,
        "DECISIONS_FAILED": 0,
        "OBSERVATION_FAILURES": 0,
        "SIGNAL_FAILURES": 0,
        "ACTION_FORMAT_FAILURES": 0,
        "COM_FAILURES": 0,
        "SIM_SEC": 3600,
    }
    for key, value in expected.items():
        raw, issue = _summary_value(text, key)
        if issue:
            reasons.append(issue)
        elif not _same_number(raw, value):
            reasons.append(f"{key} must be {value}")
        else:
            parsed[key] = raw or ""
    stage_values = re.findall(r"(?m)^STAGE=SIM_DONE\s*$", text)
    if len(stage_values) != 1:
        reasons.append(f"expected one STAGE=SIM_DONE line, found {len(stage_values)}")
    decisions = [int(value) for value in re.findall(r"CONTROLLER_DECISION sim_sec=(\d+)", text)]
    if decisions != list(EXPECTED_DECISIONS):
        reasons.append(f"controller decision times must be {list(EXPECTED_DECISIONS)}")
    warmup = re.findall(r"WARMUP_CONTROLLER sim_sec=(\d+) controller=([^\s]+)", text)
    if warmup != [("1", "no-control")]:
        reasons.append("warmup controller line must be sim_sec=1 controller=no-control")
    if "DEMAND=ORIGINAL_INPX_UNCHANGED" not in text:
        reasons.append("nominal demand marker is missing")
    if "INCIDENT=DISABLED" not in text:
        reasons.append("incident-disabled marker is missing")
    error_lines = [line for line in text.splitlines() if line.startswith("ERROR=")]
    if error_lines:
        reasons.append("run log contains ERROR lines")
    for key in ("PYTHON", "PYTHON_VERSION", "VERSION"):
        value, issue = _summary_value(text, key)
        if issue:
            reasons.append(issue)
        elif value is not None:
            parsed[key] = value
    return _gate(STATUS_FAIL if reasons else STATUS_PASS, "run did not complete with zero failures" if reasons else "run completed at 3600s with all failure counters at zero", path=str(path), reasons=reasons, error_lines=error_lines), parsed


def _validate_python_identity(
    provenance: Mapping[str, Any] | None,
    runtime: Mapping[str, Any] | None,
    preflight: Mapping[str, Any] | None,
    runlog_values: Mapping[str, str],
) -> dict[str, Any]:
    reasons: list[str] = []
    run_python = provenance.get("python_executable") if provenance else {}
    run_python = run_python if isinstance(run_python, Mapping) else {}
    runtime_python = runtime.get("python") if runtime else {}
    runtime_python = runtime_python if isinstance(runtime_python, Mapping) else {}
    preflight_runtime = preflight.get("runtime_source_identity") if preflight else {}
    preflight_runtime = preflight_runtime if isinstance(preflight_runtime, Mapping) else {}
    preflight_python = preflight_runtime.get("python")
    preflight_python = preflight_python if isinstance(preflight_python, Mapping) else {}
    paths = [run_python.get("path"), runtime_python.get("executable"), runtime_python.get("rw_python_exe"), preflight_python.get("path"), preflight_python.get("reported_path"), runlog_values.get("PYTHON")]
    normal_paths = {_normal_path(value) for value in paths if str(value or "").strip()}
    if len(normal_paths) != 1 or len([value for value in paths if str(value or "").strip()]) != len(paths):
        reasons.append("recorded Python executable paths do not all match")
    hashes = [
        str(run_python.get("sha256", "")).lower(),
        str(runtime_python.get("executable_sha256", "")).lower(),
        str((runtime.get("input_hashes") or {}).get("python_executable_sha256", "")).lower() if runtime else "",
        str(preflight_python.get("sha256", "")).lower(),
    ]
    if not all(re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes) or len(set(hashes)) != 1:
        reasons.append("recorded Python executable SHA-256 values do not all match")
    triplets = [
        _version_triplet(run_python.get("version_triplet")),
        _version_triplet(run_python.get("version")),
        _version_triplet(runtime_python.get("version")),
        _version_triplet(preflight_python.get("version")),
        _version_triplet(runlog_values.get("PYTHON_VERSION")),
    ]
    if any(value is None for value in triplets) or len(set(triplets)) != 1:
        reasons.append("recorded Python normalized version triplets do not all match")
    recorded_path = Path(str(run_python.get("path", ""))) if run_python.get("path") else None
    live_hash = _sha256_file(recorded_path) if recorded_path else None
    recorded_hash = hashes[0] if hashes else ""
    live_status = "MATCH" if live_hash == recorded_hash else "DRIFTED_OR_UNAVAILABLE"
    return _gate(STATUS_FAIL if reasons else STATUS_PASS, "run-time Python records disagree" if reasons else "run-time Python path, hash, and version records agree", recorded_path=str(recorded_path) if recorded_path else None, recorded_sha256=recorded_hash, recorded_version_triplet=list(triplets[0]) if triplets and triplets[0] else None, live_sha256=live_hash, live_status=live_status, live_drift_invalidates_historical_run=False, reasons=reasons)


def _validate_json_contract(decision_dir: Path, provenance_path: Path | None, run_id: str) -> dict[str, Any]:
    missing: list[str] = []
    invalid: list[str] = []
    mismatches: list[str] = []
    manifest_mismatches: list[str] = []
    paths: list[tuple[str, Path, int]] = []
    expected_files: set[Path] = set()
    for sec in EXPECTED_DECISIONS:
        paths.extend((("state", decision_dir / f"state_{sec:06d}.json", sec), ("action", decision_dir / f"action_{sec:06d}.json", sec)))
        action_csv = decision_dir / f"action_{sec:06d}.csv"
        expected_files.update({decision_dir / f"state_{sec:06d}.json", decision_dir / f"action_{sec:06d}.json", action_csv})
        if not action_csv.is_file():
            missing.append(str(action_csv))
    for sec in EXPECTED_ANCHORS:
        paths.append(("anchor", decision_dir / f"anchor_{sec:06d}.json", sec))
        expected_files.add(decision_dir / f"anchor_{sec:06d}.json")
    discovered = set(decision_dir.glob("state_*.json")) | set(decision_dir.glob("action_*.json")) | set(decision_dir.glob("action_*.csv")) | set(decision_dir.glob("anchor_*.json"))
    unexpected = sorted(str(path) for path in discovered - expected_files)
    for kind, path, sec in paths:
        if not path.is_file():
            missing.append(str(path))
            continue
        payload, error = _read_json(path)
        if error or payload is None:
            invalid.append(f"{path}: {error}")
            continue
        if _payload_run_id(payload) != run_id:
            mismatches.append(str(path))
        if not _same_number(_payload_sim_sec(payload), sec):
            invalid.append(f"{path}: sim_sec mismatch")
        if kind in {"state", "anchor"}:
            reference = payload.get("run_provenance")
            reference = reference if isinstance(reference, Mapping) else {}
            if provenance_path is None or _normal_path(reference.get("manifest_path")) != _normal_path(provenance_path):
                manifest_mismatches.append(str(path))
        if kind == "action":
            action_provenance = payload.get("run_provenance")
            action_provenance = action_provenance if isinstance(action_provenance, Mapping) else {}
            inputs = action_provenance.get("inputs")
            inputs = inputs if isinstance(inputs, Mapping) else {}
            run_manifest = inputs.get("run_manifest_json")
            run_manifest = run_manifest if isinstance(run_manifest, Mapping) else {}
            if provenance_path is None or _normal_path(run_manifest.get("path")) != _normal_path(provenance_path) or str(run_manifest.get("sha256", "")).lower() != str(_sha256_file(provenance_path) or ""):
                manifest_mismatches.append(str(path))
    status = STATUS_NOT_EVALUATED if missing else (STATUS_FAIL if invalid or mismatches or manifest_mismatches or unexpected else STATUS_PASS)
    return _gate(status, "state/action/anchor JSON contract is incomplete or inconsistent" if status != STATUS_PASS else "two state/action pairs and four anchors share one run and manifest", missing=missing, unexpected=unexpected, invalid=invalid, run_id_mismatches=mismatches, manifest_mismatches=manifest_mismatches, state_json_count=2, action_json_count=2, action_csv_count=2, anchor_json_count=4)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]], str | None]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                return [], [], "CSV header is missing"
            return list(reader.fieldnames), [dict(row) for row in reader], None
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], [], f"{type(exc).__name__}: {exc}"


def _validate_state_csv(path: Path) -> dict[str, Any]:
    header, rows, error = _read_csv(path)
    if error:
        return _gate(STATUS_NOT_EVALUATED if not path.is_file() else STATUS_FAIL, "state CSV is unavailable or malformed", path=str(path), error=error)
    reasons: list[str] = []
    times: list[int] = []
    if tuple(header) != STATE_CSV_HEADER:
        reasons.append("state CSV header is not the exact 13-column VBS schema")
    count_fields = (
        "total_vehicles",
        "urban_vehicles",
        "freeway_vehicles",
        "ramp_vehicles",
        "boundary_vehicles",
        "other_vehicles",
        "stopped_vehicles",
    )
    speed_fields = ("mean_speed_kph", "freeway_mean_speed_kph")
    row_errors: list[str] = []
    for index, row in enumerate(rows, 2):
        sim_sec = _number(row.get("sim_sec"))
        if sim_sec is None or sim_sec < 0 or not sim_sec.is_integer():
            row_errors.append(f"row {index}: sim_sec must be a nonnegative integer")
        else:
            times.append(int(sim_sec))
        counts: dict[str, int] = {}
        for field in count_fields:
            value = _number(row.get(field))
            if value is None or value < 0 or not value.is_integer():
                row_errors.append(f"row {index}: {field} must be a finite nonnegative integer")
            else:
                counts[field] = int(value)
        for field in speed_fields:
            value = _number(row.get(field))
            if value is None or not 0.0 <= value <= 300.0:
                row_errors.append(f"row {index}: {field} must be finite and within 0..300 km/h")
        wall = _number(row.get("decision_wall_sec"))
        if wall is None or not 0.0 <= wall <= 45.0:
            row_errors.append(f"row {index}: decision_wall_sec must be finite and within 0..45 s")
        if row.get("controller_mode", "").strip().upper() != "VISSIM_REAL_WORLD_NO-CONTROL":
            row_errors.append(f"row {index}: controller_mode is not the no-control VBS mode")
        if row.get("controller_status", "").strip().lower() != "ok":
            row_errors.append(f"row {index}: controller_status is not ok")
        if len(counts) == len(count_fields):
            represented = sum(
                counts[field]
                for field in ("urban_vehicles", "freeway_vehicles", "ramp_vehicles", "boundary_vehicles", "other_vehicles")
            )
            if counts["total_vehicles"] != represented:
                row_errors.append(f"row {index}: vehicle category counts do not sum to total_vehicles")
            if counts["stopped_vehicles"] > counts["total_vehicles"]:
                row_errors.append(f"row {index}: stopped_vehicles exceeds total_vehicles")
    if row_errors:
        reasons.extend(row_errors[:25])
        if len(row_errors) > 25:
            reasons.append(f"state CSV has {len(row_errors) - 25} additional row validation errors")
    if tuple(times) != EXPECTED_STATE_TIMES:
        reasons.append("state CSV timing is not canonical 1,5,...,3600")
    return _gate(STATUS_FAIL if reasons else STATUS_PASS, "state CSV schema, values, or timing are not canonical" if reasons else "state CSV has 721 typed 13-column observations through 3600s", path=str(path), header=header, row_count=len(rows), first_sim_sec=times[0] if times else None, final_sim_sec=times[-1] if times else None, reasons=reasons)


def _yaml_mapping_block(text: str, key: str) -> dict[str, float]:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(rf"^  {re.escape(key)}:\s*$", line)), -1)
    result: dict[str, float] = {}
    if start < 0:
        return result
    for line in lines[start + 1 :]:
        if line.strip() and not line.startswith("    "):
            break
        match = re.match(r"^    ([A-Za-z0-9_]+):\s*([-+0-9.eE]+)\s*$", line)
        if match:
            result[match.group(1)] = float(match.group(2))
    return result


def _yaml_list_block(text: str, key: str, section_indent: int) -> list[str]:
    prefix = " " * section_indent
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(rf"^{prefix}{re.escape(key)}:\s*$", line)), -1)
    result: list[str] = []
    if start < 0:
        return result
    item_prefix = " " * section_indent
    for line in lines[start + 1 :]:
        match = re.match(rf"^{re.escape(item_prefix)}-\s*(\S+)\s*$", line)
        if match:
            result.append(match.group(1))
            continue
        if line.strip() and not line.startswith(" " * (section_indent + 2)):
            break
    return result


def _deep_update(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_update(result[key], value)  # type: ignore[arg-type]
        else:
            result[key] = value
    return result


def _load_json_extends(path: Path, seen: set[str] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
    seen = set() if seen is None else seen
    key = _normal_path(path)
    if key in seen:
        return {}, [], f"cyclic JSON extends at {path}"
    seen.add(key)
    payload, error = _read_json(path)
    if error or payload is None:
        return {}, [], error or "invalid JSON"
    evidence = [_manifest_artifact(path)]
    extends = str(payload.get("extends", "")).strip()
    child = dict(payload)
    child.pop("extends", None)
    if not extends:
        return child, evidence, None
    parent_path = Path(extends)
    if not parent_path.is_absolute():
        parent_path = path.parent / parent_path
    parent, parent_evidence, parent_error = _load_json_extends(parent_path.resolve(strict=False), seen)
    if parent_error:
        return {}, [*parent_evidence, *evidence], parent_error
    return _deep_update(parent, child), [*parent_evidence, *evidence], None


def _derive_no_control_contract(
    provenance: Mapping[str, Any],
    preflight: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    reasons: list[str] = []
    artifacts = preflight.get("artifacts") if isinstance(preflight.get("artifacts"), Mapping) else {}
    mapping_path = Path(str((artifacts.get("control_mapping") or {}).get("path", "")))
    tuning_path = Path(str((artifacts.get("tuning") or {}).get("path", "")))
    generated_path = Path(str((artifacts.get("generated_vbs") or {}).get("path", "")))
    files = provenance.get("files") if isinstance(provenance.get("files"), Mapping) else {}
    default_record = files.get("numsim_default_yaml")
    default_record = default_record if isinstance(default_record, Mapping) else {}
    default_path = Path(str(default_record.get("path", "")))
    mapping, mapping_error = _read_json(mapping_path)
    tuning, tuning_dependencies, tuning_error = _load_json_extends(tuning_path)
    if mapping_error or mapping is None:
        reasons.append(f"control mapping unavailable: {mapping_error}")
        mapping = {}
    if tuning_error:
        reasons.append(f"tuning unavailable: {tuning_error}")
        tuning = {}
    if not generated_path.is_file():
        reasons.append("generated VBS config unavailable")
        generated_text = ""
    else:
        generated_text = generated_path.read_text(encoding="utf-8-sig", errors="replace")
    if not default_path.is_file() or _sha256_file(default_path) != str(default_record.get("sha256", "")).lower():
        reasons.append("NumSim default.yaml is unavailable or differs from run provenance")
        default_text = ""
    else:
        default_text = default_path.read_text(encoding="utf-8-sig", errors="replace")
    freeway_links = _yaml_list_block(default_text, "freeway_links", 2)
    vsl_values = [float(value) for value in _yaml_list_block(default_text, "vsl_set", 2)]
    ramp_capacities = _yaml_mapping_block(default_text, "ramp_capacity_veh_h")
    scalar = {key: float(value) for key, value in re.findall(r"^  (cycle_length|lost_time):\s*([-+0-9.eE]+)\s*$", default_text, re.MULTILINE)}
    overrides = tuning.get("config_overrides") if isinstance(tuning.get("config_overrides"), Mapping) else {}
    for section in ("network", "mpc", "leader", "freeway_follower", "urban_follower"):
        if isinstance(tuning.get(section), Mapping):
            overrides = _deep_update(overrides, {section: tuning[section]})
    network_overrides = overrides.get("network") if isinstance(overrides.get("network"), Mapping) else {}
    follower_overrides = overrides.get("freeway_follower") if isinstance(overrides.get("freeway_follower"), Mapping) else {}
    signals = network_overrides.get("signals", [])
    if isinstance(network_overrides.get("ramp_capacity_veh_h"), Mapping):
        ramp_capacities.update({str(key): float(value) for key, value in network_overrides["ramp_capacity_veh_h"].items()})
    if isinstance(follower_overrides.get("vsl_set"), list):
        vsl_values = [float(value) for value in follower_overrides["vsl_set"]]
    for key in ("cycle_length", "lost_time"):
        if key in network_overrides:
            scalar[key] = float(network_overrides[key])
    apply_signal = (((tuning.get("actuation") or {}).get("real_world_signal_control") or {}).get("apply_to_no_control")) if isinstance(tuning, Mapping) else None
    ramp_settings = (((tuning.get("actuation") or {}).get("real_world_ramp_metering") or {})) if isinstance(tuning, Mapping) else {}
    allowed_match = re.search(r'^RW_ALLOWED_VSL_SPEEDS\s*=\s*"([^"]+)"', generated_text, re.MULTILINE)
    expected_rows_match = re.search(r"^RW_EXPECTED_VSL_ACTION_ROWS\s*=\s*(\d+)", generated_text, re.MULTILINE)
    generated_allowed = [float(value) for value in allowed_match.group(1).split(",")] if allowed_match else []
    if not freeway_links or not vsl_values or not ramp_capacities or not signals:
        reasons.append("NumSim/tuning no-control model values could not be derived")
    max_vsl = max(vsl_values) if vsl_values else None
    if max_vsl is None or max_vsl not in generated_allowed:
        reasons.append("no-control VSL is not allowed by generated VBS config")
    if apply_signal is not False:
        reasons.append("tuning does not suppress signal rows for no-control")
    vsl_rows: dict[int, dict[str, Any]] = {}
    for segment in mapping.get("segments", []) if isinstance(mapping, Mapping) else []:
        if not isinstance(segment, Mapping):
            continue
        controls: list[Mapping[str, Any]] = []
        by_lane = segment.get("dsd_by_lane")
        if isinstance(by_lane, Mapping):
            controls.extend(value for value in by_lane.values() if isinstance(value, Mapping))
        extras = segment.get("extra_dsd_controls")
        if isinstance(extras, list):
            controls.extend(value for value in extras if isinstance(value, Mapping))
        for control in controls:
            dsd_no = int(float(control.get("dsd_no", 0)))
            vsl_rows[dsd_no] = {
                "id": str(segment.get("segment_id", "")),
                "dsd_no": dsd_no,
                "link": int(float(control.get("link", segment.get("link", 0)))),
                "lane": int(float(control.get("lane", 0))),
                "speed_kph": max_vsl,
            }
    expected_vsl_rows = int(expected_rows_match.group(1)) if expected_rows_match else 0
    if len(vsl_rows) != expected_vsl_rows:
        reasons.append("mapping VSL row count differs from generated VBS config")
    ramp_rows: dict[str, dict[str, Any]] = {}
    meters = mapping.get("ramp_meters", []) if isinstance(mapping, Mapping) else []
    group_counts: dict[str, int] = {}
    for meter in meters if isinstance(meters, list) else []:
        if isinstance(meter, Mapping):
            key = str(meter.get("model_ramp_key", ""))
            group_counts[key] = group_counts.get(key, 0) + 1
    for meter in meters if isinstance(meters, list) else []:
        if not isinstance(meter, Mapping):
            continue
        key = str(meter.get("model_ramp_key", ""))
        group_rate = ramp_capacities.get(key)
        count = group_counts.get(key, 0)
        default_capacity = float(ramp_settings.get("per_meter_capacity_vph", 900.0))
        capacity = float(meter.get("capacity_vph", default_capacity))
        if group_rate is None or count < 1:
            reasons.append(f"ramp {key} has no derived no-control capacity")
            continue
        distribute = bool(ramp_settings.get("distribute_model_rate_across_meters", True))
        per_rate = group_rate / count if distribute else group_rate
        cycle = float(ramp_settings.get("cycle_sec", meter.get("cycle_sec", 10.0)))
        min_green = max(0.0, min(cycle, float(ramp_settings.get("min_green_sec", 0.0))))
        max_green = max(min_green, min(cycle, float(ramp_settings.get("max_green_sec", cycle))))
        green = max(min_green, min(max_green, float(round(cycle * per_rate / capacity))))
        ramp_rows[str(meter.get("id", ""))] = {
            "sc_no": int(float(meter.get("sc_no", 0))),
            "rate_vph": per_rate,
            "green_sec": green,
            "model_ramp_key": key,
        }
    phase_green = (scalar.get("cycle_length", 0.0) - scalar.get("lost_time", 0.0)) / 2.0
    return {
        "sources": {
            "numsim_default_yaml": {"path": str(default_path), "sha256": default_record.get("sha256")},
            "control_mapping": _manifest_artifact(mapping_path),
            "tuning": _manifest_artifact(tuning_path),
            "tuning_dependencies": tuning_dependencies,
            "generated_vbs": _manifest_artifact(generated_path),
        },
        "model": {
            "freeway_links": freeway_links,
            "vsl_kph": max_vsl,
            "ramp_capacity_vph": ramp_capacities,
            "signals": [str(value) for value in signals],
            "phase_green_sec": phase_green,
            "offset_sec": 0.0,
        },
        "physical_vsl_rows": vsl_rows,
        "physical_ramp_rows": ramp_rows,
        "signal_rows": 0,
        "derivation": "ControlAction.uncontrolled(default.yaml) plus adapter mapping and generated VBS constraints",
    }, reasons


def _row_number(row: Mapping[str, str], key: str) -> float | None:
    return _number(row.get(key, ""))


def _validate_action_rows(rows: list[dict[str, str]], contract: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    vsl_rows = [row for row in rows if row.get("kind", "").strip().lower() == "vsl"]
    ramp_rows = [row for row in rows if row.get("kind", "").strip().lower() == "ramp_meter"]
    signal_rows = [row for row in rows if row.get("kind", "").strip().lower() == "signal"]
    unknown_rows = [row for row in rows if row.get("kind", "").strip().lower() not in {"vsl", "ramp_meter", "signal"}]
    expected_vsl = contract.get("physical_vsl_rows", {})
    expected_ramps = contract.get("physical_ramp_rows", {})
    if len(vsl_rows) != len(expected_vsl) or len(ramp_rows) != len(expected_ramps) or signal_rows or unknown_rows:
        reasons.append("action kind counts are not canonical no-control counts")
    seen_dsd: set[int] = set()
    for row in vsl_rows:
        try:
            dsd_no = int(float(row.get("dsd_no", "")))
        except ValueError:
            reasons.append("VSL row has invalid dsd_no")
            continue
        expected = expected_vsl.get(dsd_no) if isinstance(expected_vsl, Mapping) else None
        if not isinstance(expected, Mapping) or dsd_no in seen_dsd:
            reasons.append(f"unexpected or duplicate VSL DSD {dsd_no}")
            continue
        seen_dsd.add(dsd_no)
        for key in ("link", "lane"):
            if not _same_number(row.get(key), float(expected[key])):
                reasons.append(f"VSL DSD {dsd_no} {key} mismatch")
        if row.get("id") != expected["id"] or not _same_number(row.get("speed_kph"), float(expected["speed_kph"])):
            reasons.append(f"VSL DSD {dsd_no} is not the no-control setting")
    seen_ramps: set[str] = set()
    for row in ramp_rows:
        ramp_id = str(row.get("id", ""))
        expected = expected_ramps.get(ramp_id) if isinstance(expected_ramps, Mapping) else None
        if not isinstance(expected, Mapping) or ramp_id in seen_ramps:
            reasons.append(f"unexpected or duplicate ramp meter {ramp_id}")
            continue
        seen_ramps.add(ramp_id)
        for key in ("sc_no", "rate_vph", "green_sec"):
            if not _same_number(row.get(key), float(expected[key])):
                reasons.append(f"ramp {ramp_id} {key} is not the no-control setting")
    return reasons


def _validate_no_control_actions(
    baseline_dir: Path,
    decision_dir: Path,
    provenance: Mapping[str, Any] | None,
    preflight: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if provenance is None or preflight is None:
        return _gate(STATUS_NOT_EVALUATED, "no-control sources are unavailable")
    contract, reasons = _derive_no_control_contract(provenance, preflight)
    per_decision_rows: dict[int, list[dict[str, str]]] = {}
    expected_model = contract.get("model", {})
    for sec in EXPECTED_DECISIONS:
        json_path = decision_dir / f"action_{sec:06d}.json"
        csv_path = decision_dir / f"action_{sec:06d}.csv"
        payload, error = _read_json(json_path)
        if error or payload is None:
            reasons.append(f"{json_path.name}: {error or 'missing'}")
            continue
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
        diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), Mapping) else {}
        if metadata.get("controller") != "NoControl" or _normal_controller(metadata.get("controller_variant")) != "no-control" or metadata.get("controller_status") != "ok":
            reasons.append(f"{json_path.name}: controller labels/status are not canonical no-control")
        if not _same_number(diagnostics.get("no_control_active"), 1.0):
            reasons.append(f"{json_path.name}: no_control_active must be 1")
        for key in ("N_P_star", "N_UF_star"):
            if not _same_number(payload.get(key), 0.0):
                reasons.append(f"{json_path.name}: {key} must be 0")
        if payload.get("inflow_outflow_allocation") not in ({}, None):
            reasons.append(f"{json_path.name}: inflow_outflow_allocation must be empty")
        vsl = payload.get("vsl") if isinstance(payload.get("vsl"), Mapping) else {}
        if set(vsl) != set(expected_model.get("freeway_links", [])) or any(not _same_number(value, float(expected_model.get("vsl_kph"))) for value in vsl.values()):
            reasons.append(f"{json_path.name}: model VSL payload is not uncontrolled")
        ramps = payload.get("ramp_metering") if isinstance(payload.get("ramp_metering"), Mapping) else {}
        expected_ramps = expected_model.get("ramp_capacity_vph", {})
        if set(ramps) != set(expected_ramps) or any(not _same_number(ramps.get(key), float(value)) for key, value in expected_ramps.items()):
            reasons.append(f"{json_path.name}: model ramp payload is not full-release no-control")
        signals = expected_model.get("signals", [])
        expected_green = {f"{signal}_{phase}": float(expected_model.get("phase_green_sec")) for signal in signals for phase in ("p1", "p2")}
        green = payload.get("green_times") if isinstance(payload.get("green_times"), Mapping) else {}
        if set(green) != set(expected_green) or any(not _same_number(green.get(key), value) for key, value in expected_green.items()):
            reasons.append(f"{json_path.name}: model green payload is not the uncontrolled default")
        offsets = payload.get("offsets") if isinstance(payload.get("offsets"), Mapping) else {}
        if set(offsets) != set(signals) or any(not _same_number(value, 0.0) for value in offsets.values()):
            reasons.append(f"{json_path.name}: offsets are not the uncontrolled default")
        header, rows, csv_error = _read_csv(csv_path)
        expected_header = ["kind", "id", "dsd_no", "sc_no", "link", "lane", "speed_kph", "major_green", "minor_green", "offset", "rate_vph", "green_sec", "metadata"]
        if csv_error or header != expected_header:
            reasons.append(f"{csv_path.name}: invalid action CSV header/content ({csv_error or 'header mismatch'})")
        else:
            reasons.extend(f"{csv_path.name}: {reason}" for reason in _validate_action_rows(rows, contract))
            per_decision_rows[sec] = rows

    cumulative_path = baseline_dir / f"action_{EXPECTED_NAME}.csv"
    cumulative_header, cumulative_rows, cumulative_error = _read_csv(cumulative_path)
    expected_cumulative_header = ["sim_sec", "kind", "id", "dsd_no", "sc_no", "link", "lane", "speed_kph", "major_green", "minor_green", "offset", "rate_vph", "green_sec", "metadata", "readback"]
    if cumulative_error or cumulative_header != expected_cumulative_header:
        reasons.append(f"cumulative action CSV is invalid ({cumulative_error or 'header mismatch'})")
    else:
        expected_rows: list[dict[str, str]] = []
        for sec in EXPECTED_DECISIONS:
            for row in per_decision_rows.get(sec, []):
                expected_rows.append({"sim_sec": str(sec), **row})
        if len(cumulative_rows) != len(expected_rows):
            reasons.append("cumulative action CSV row count does not match per-decision CSVs")
        compare_keys = expected_cumulative_header[:-1]
        for index, (actual, expected) in enumerate(zip(cumulative_rows, expected_rows), 1):
            if any(str(actual.get(key, "")) != str(expected.get(key, "")) for key in compare_keys):
                reasons.append(f"cumulative action row {index} differs from its per-decision row")
                break
            readback = str(actual.get("readback", "")).strip()
            kind = str(actual.get("kind", "")).strip().lower()
            if kind == "vsl" and (not readback or "ERR" in readback.upper()):
                reasons.append(f"cumulative action row {index} has missing/failed VSL readback")
                break
            if kind == "ramp_meter" and readback.upper() not in {"GREEN", "AMBER", "RED"}:
                reasons.append(f"cumulative action row {index} has unsuccessful ramp readback")
                break
            if kind == "signal":
                reasons.append(f"cumulative action row {index} contains forbidden no-control signal actuation")
                break
    readback_path = decision_dir / "signal_readback.csv"
    readback_header, readback_rows, readback_error = _read_csv(readback_path)
    expected_readback_header = ["sim_sec", "sc_no", "sg_no", "requested_state", "readback_state", "ok", "stage"]
    if readback_error or readback_header != expected_readback_header or readback_rows:
        reasons.append("signal_readback must be a valid header-only CSV for no-control")
    return _gate(STATUS_FAIL if reasons else STATUS_PASS, "one or more action payloads are not canonical no-control" if reasons else "both decisions are canonical no-control and match cumulative physical actions", reasons=reasons, contract=contract, decision_count=len(per_decision_rows), cumulative_row_count=len(cumulative_rows), signal_readback_row_count=len(readback_rows))


def _validate_vissim_error_evidence(
    baseline_dir: Path,
    name: str,
    run_id: str,
    provenance: Mapping[str, Any] | None,
    audit: Mapping[str, Any] | None,
) -> dict[str, Any]:
    path = baseline_dir / f"vissim_error_evidence_{name}.json"
    payload, error = _read_json(path)
    if error or payload is None:
        return _gate(STATUS_NOT_EVALUATED if not path.is_file() else STATUS_FAIL, "run-bound VISSIM error evidence is unavailable", path=str(path), error=error)
    reasons: list[str] = []
    if payload.get("schema_version") != "vissim-error-evidence-v2.1" or payload.get("run_name") != name or payload.get("run_id") != run_id:
        reasons.append("error evidence schema/run linkage mismatch")
    if payload.get("source_checked_after_process_exit") is not True or payload.get("process_exit_code") != 0:
        reasons.append("error evidence was not captured after a successful process exit")
    attempt = payload.get("attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
        reasons.append("error evidence attempt must be a positive integer")
    wall, wall_error = _read_json(baseline_dir / f"wall_time_profile_{name}.json")
    if wall_error or wall is None or wall.get("run_id") != run_id or wall.get("run_name") != name or wall.get("attempt") != payload.get("attempt") or wall.get("status") != STATUS_PASS or wall.get("process_exit_code") != 0:
        reasons.append("error evidence does not match the successful wall-time profile")
    binding_text = str(payload.get("binding_text", ""))
    if hashlib.sha256(binding_text.encode("utf-8")).hexdigest() != str(payload.get("binding_sha256", "")).lower():
        reasons.append("error evidence binding SHA-256 mismatch")
    checked_at = str(payload.get("post_exit_checked_at_utc", "")).strip()
    try:
        datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
    except ValueError:
        reasons.append("error evidence post-exit timestamp is invalid")
    expected_binding = (
        f"run_id={run_id}\nrun_name={name}\nattempt={attempt}\n"
        f"present={str(payload.get('present')).lower()}\n"
        f"source_path={payload.get('source_path', '')}\n"
        f"post_exit_checked_at_utc={checked_at}"
    )
    if binding_text != expected_binding:
        reasons.append("error evidence binding text differs from marker fields")

    files = provenance.get("files") if provenance and isinstance(provenance.get("files"), Mapping) else {}
    network = files.get("network") if isinstance(files.get("network"), Mapping) else {}
    network_path_text = str(network.get("path", "")).strip()
    expected_source = str(Path(network_path_text).with_suffix(".err").resolve(strict=False)) if network_path_text else ""
    source_text = str(payload.get("source_path", "")).strip()
    if not expected_source or _normal_path(source_text) != _normal_path(expected_source):
        reasons.append("error evidence source_path is not the run network .err path")

    stale_records = payload.get("stale_pre_run")
    if not isinstance(stale_records, list):
        reasons.append("stale_pre_run must be an explicit list")
        stale_records = []
    expected_archive_root = Path(str(baseline_dir.resolve(strict=False)) + ".pre_run_err_archive")
    for index, raw_stale in enumerate(stale_records, 1):
        stale = raw_stale if isinstance(raw_stale, Mapping) else {}
        stale_attempt = stale.get("attempt")
        archive_text = str(stale.get("archived_path", "")).strip()
        archive_path = Path(archive_text).resolve(strict=False) if archive_text else Path("__missing__")
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
            reasons.append(f"stale_pre_run[{index}] attempt is invalid or mixed")
        if _normal_path(stale.get("source_path")) != _normal_path(source_text):
            reasons.append(f"stale_pre_run[{index}] source path differs from the run")
        if archive_path != expected_archive.resolve(strict=False) or archive_path == Path(source_text).resolve(strict=False):
            reasons.append(f"stale_pre_run[{index}] archive path does not prove run separation")
        archive_hash = _sha256_file(archive_path)
        if not archive_hash or archive_hash != str(stale.get("sha256", "")).lower():
            reasons.append(f"stale_pre_run[{index}] archive SHA-256 mismatch")
        archived_at = str(stale.get("archived_at_utc", "")).strip()
        try:
            datetime.fromisoformat(archived_at.replace("Z", "+00:00"))
        except ValueError:
            reasons.append(f"stale_pre_run[{index}] archived_at_utc is invalid")
        if archive_path.is_file() and re.search(r"\b(error|fatal)\b", archive_path.read_text(encoding="utf-8-sig", errors="replace"), re.IGNORECASE):
            reasons.append(f"stale_pre_run[{index}] archive contains error/fatal text")
    if stale_records:
        reasons.append("stale_pre_run is non-empty; strict baseline certification requires zero stale source files")
    present = payload.get("present")
    artifact = payload.get("artifact")
    if present is True:
        artifact = artifact if isinstance(artifact, Mapping) else {}
        artifact_path = Path(str(artifact.get("path", ""))) if artifact.get("path") else Path("__missing__")
        expected_artifact_path = baseline_dir / f"vissim_network_{name}.err"
        artifact_hash = _sha256_file(artifact_path)
        source_hash = _sha256_file(Path(source_text)) if source_text else None
        if _normal_path(artifact_path) != _normal_path(expected_artifact_path):
            reasons.append("preserved .err artifact path is not run-bound")
        if artifact_hash != str(artifact.get("sha256", "")).lower():
            reasons.append("preserved .err artifact hash mismatch")
        elif not source_hash or source_hash != artifact_hash:
            reasons.append("present source .err is missing or differs from preserved artifact")
        elif re.search(r"\b(error|fatal)\b", artifact_path.read_text(encoding="utf-8-sig", errors="replace"), re.IGNORECASE):
            reasons.append("preserved .err contains error/fatal text")
    elif present is False:
        if artifact not in (None, {}):
            reasons.append("absence marker unexpectedly contains an artifact")
        if source_text and Path(source_text).is_file():
            reasons.append("absence marker is stale because source .err currently exists")
    else:
        reasons.append("error evidence present field is not boolean")
    audit_gate = (((audit.get("gates") or {}).get("vissim_error_log") or {}).get("status")) if audit else None
    if audit_gate != STATUS_PASS:
        reasons.append("generic audit VISSIM error gate is not PASS")
    audit_error = audit.get("vissim_error") if audit and isinstance(audit.get("vissim_error"), Mapping) else {}
    markers = audit_error.get("markers") if isinstance(audit_error.get("markers"), list) else []
    matching_markers = [
        item
        for item in markers
        if isinstance(item, Mapping)
        and _normal_path(item.get("path")) == _normal_path(path)
        and item.get("run_name") == name
        and item.get("run_id") == run_id
    ]
    if (
        len(matching_markers) != 1
        or matching_markers[0].get("status") != STATUS_PASS
        or matching_markers[0].get("present") is not present
        or audit_error.get("marker_error_count") != 0
        or audit_error.get("evidence_complete") is not True
    ):
        reasons.append("generic audit error evidence does not match the current run marker")
    return _gate(STATUS_FAIL if reasons else STATUS_PASS, "VISSIM error evidence is invalid or non-clean" if reasons else "run-bound VISSIM error evidence is clean", path=str(path), present=present, reasons=reasons)


def _validate_run_artifact_manifest(
    baseline_dir: Path, name: str, run_id: str, provenance_path: Path | None
) -> dict[str, Any]:
    path = baseline_dir / f"run_artifact_manifest_{name}.json"
    payload, error = _read_json(path)
    if error or payload is None:
        return _gate(
            STATUS_NOT_EVALUATED if not path.is_file() else STATUS_FAIL,
            "run-bound artifact manifest is unavailable",
            path=str(path),
            error=error,
        )
    reasons: list[str] = []
    if (
        payload.get("schema_version") != "run-artifact-manifest-v2.1"
        or payload.get("status") != STATUS_PASS
        or payload.get("run_name") != name
        or payload.get("run_id") != run_id
        or not isinstance(payload.get("attempt"), int)
        or isinstance(payload.get("attempt"), bool)
        or int(payload.get("attempt", 0)) < 1
        or payload.get("process_exit_code") != 0
    ):
        reasons.append("run artifact manifest schema/status/run linkage is invalid")
    finalized = _parse_utc_datetime(payload.get("finalized_at_utc"))
    if finalized is None:
        reasons.append("run artifact manifest finalized_at_utc is invalid")

    provenance_record = payload.get("run_provenance")
    provenance_record = provenance_record if isinstance(provenance_record, Mapping) else {}
    if (
        provenance_path is None
        or _normal_path(provenance_record.get("path")) != _normal_path(provenance_path)
        or str(provenance_record.get("sha256", "")).lower() != str(_sha256_file(provenance_path) or "")
    ):
        reasons.append("run artifact manifest does not bind the immutable run provenance")

    decision_dir = baseline_dir / f"decisions_{name}"
    expected_outputs = {
        "state_csv": baseline_dir / f"state_{name}.csv",
        "cumulative_action_csv": baseline_dir / f"action_{name}.csv",
        "stdout_runlog": baseline_dir / f"runlog_{name}.txt",
        "stderr_runlog": baseline_dir / f"runlog_{name}.txt.err",
        "signal_readback_csv": decision_dir / "signal_readback.csv",
        "generated_vbs_config_copy": baseline_dir / f"generated_vbs_config_{name}.vbs",
        "vissim_error_evidence": baseline_dir / f"vissim_error_evidence_{name}.json",
        "wall_time_profile": baseline_dir / f"wall_time_profile_{name}.json",
    }
    simulation_output_keys = (
        "state_csv",
        "cumulative_action_csv",
        "stdout_runlog",
        "stderr_runlog",
        "signal_readback_csv",
    )
    post_exit_evidence_keys = ("vissim_error_evidence", "wall_time_profile")
    pre_run_input_keys = ("generated_vbs_config_copy",)
    roles = payload.get("artifact_roles")
    roles = roles if isinstance(roles, Mapping) else {}
    if (
        roles.get("simulation_output_keys") != list(simulation_output_keys)
        or roles.get("post_exit_evidence_keys") != list(post_exit_evidence_keys)
        or roles.get("pre_run_input_keys") != list(pre_run_input_keys)
        or roles.get("decision_artifacts") != "simulation_output"
    ):
        reasons.append("run artifact manifest output role classification is invalid")

    wall, wall_error = _read_json(expected_outputs["wall_time_profile"])
    started = _parse_utc_datetime(wall.get("started_at_utc")) if wall is not None else None
    finished = _parse_utc_datetime(wall.get("finished_at_utc")) if wall is not None else None
    if wall_error or wall is None or started is None or finished is None:
        reasons.append("run artifact manifest wall-time linkage is unavailable or invalid")
    else:
        if wall.get("run_id") != run_id or wall.get("run_name") != name or wall.get("attempt") != payload.get("attempt"):
            reasons.append("run artifact manifest attempt differs from wall-time profile")
        if finished < started:
            reasons.append("wall-time profile finishes before it starts")
        if finalized is not None and finalized < finished:
            reasons.append("run artifact manifest was finalized before process completion evidence")

    run_window = payload.get("run_window")
    run_window = run_window if isinstance(run_window, Mapping) else {}
    window_started = _parse_utc_datetime(run_window.get("started_at_utc"))
    window_finished = _parse_utc_datetime(run_window.get("finished_at_utc"))
    tolerance_raw = run_window.get("filesystem_mtime_tolerance_sec")
    try:
        tolerance = float(tolerance_raw)
    except (TypeError, ValueError):
        tolerance = -1.0
    if (
        window_started is None
        or window_finished is None
        or started is None
        or finished is None
        or window_started != started
        or window_finished != finished
        or tolerance != FILESYSTEM_MTIME_TOLERANCE_SEC
    ):
        reasons.append("run artifact manifest run_window does not exactly bind the wall-time profile")
    outputs = payload.get("output_artifacts")
    outputs = outputs if isinstance(outputs, Mapping) else {}
    if set(outputs) != set(expected_outputs):
        reasons.append("run artifact manifest output inventory is incomplete or unexpected")
    for key, expected_path in expected_outputs.items():
        record = outputs.get(key)
        record = record if isinstance(record, Mapping) else {}
        if (
            _normal_path(record.get("path")) != _normal_path(expected_path)
            or record.get("exists") is not True
            or str(record.get("sha256", "")).lower() != str(_sha256_file(expected_path) or "")
            or record.get("size_bytes") != (expected_path.stat().st_size if expected_path.is_file() else None)
            or not _recorded_mtime_matches(record, expected_path)
        ):
            reasons.append(f"run artifact manifest hash/link mismatch: {key}")
        if started is not None and finished is not None and finalized is not None:
            if key in simulation_output_keys and not _mtime_within(expected_path, started, finished, tolerance):
                reasons.append(f"run artifact predates or postdates the simulation window: {key}")
            elif key in post_exit_evidence_keys and not _mtime_within(expected_path, finished, finalized, tolerance):
                reasons.append(f"post-exit artifact falls outside completion/finalization: {key}")

    expected_decisions = {
        *(decision_dir / f"state_{sec:06d}.json" for sec in EXPECTED_DECISIONS),
        *(decision_dir / f"action_{sec:06d}.json" for sec in EXPECTED_DECISIONS),
        *(decision_dir / f"action_{sec:06d}.csv" for sec in EXPECTED_DECISIONS),
        *(decision_dir / f"anchor_{sec:06d}.json" for sec in EXPECTED_ANCHORS),
    }
    decision_records = payload.get("decision_artifacts")
    decision_records = decision_records if isinstance(decision_records, list) else []
    recorded_paths: dict[str, Mapping[str, Any]] = {}
    for raw in decision_records:
        record = raw if isinstance(raw, Mapping) else {}
        key = _normal_path(record.get("path"))
        if not key or key in recorded_paths:
            reasons.append("run artifact manifest has malformed/duplicate decision artifacts")
            continue
        recorded_paths[key] = record
    expected_by_key = {_normal_path(item): item for item in expected_decisions}
    if set(recorded_paths) != set(expected_by_key):
        reasons.append("run artifact manifest decision inventory is incomplete or unexpected")
    for key, expected_path in expected_by_key.items():
        record = recorded_paths.get(key, {})
        if (
            record.get("exists") is not True
            or str(record.get("sha256", "")).lower() != str(_sha256_file(expected_path) or "")
            or record.get("size_bytes") != (expected_path.stat().st_size if expected_path.is_file() else None)
            or not _recorded_mtime_matches(record, expected_path)
        ):
            reasons.append(f"run artifact manifest decision hash mismatch: {expected_path.name}")
            break
        if started is not None and finished is not None and not _mtime_within(
            expected_path, started, finished, tolerance
        ):
            reasons.append(f"decision artifact predates or postdates the simulation window: {expected_path.name}")
            break
    return _gate(
        STATUS_FAIL if reasons else STATUS_PASS,
        "run-bound artifact manifest is invalid" if reasons else "successful run artifacts are atomically hash-bound to one run/attempt",
        path=str(path),
        output_artifact_count=len(outputs),
        decision_artifact_count=len(decision_records),
        reasons=reasons,
    )


def _validate_preserved_artifacts(baseline_dir: Path, name: str, run_id: str) -> dict[str, Any]:
    decision_dir = baseline_dir / f"decisions_{name}"
    required = {
        "state_csv": baseline_dir / f"state_{name}.csv",
        "cumulative_action_csv": baseline_dir / f"action_{name}.csv",
        "stdout_runlog": baseline_dir / f"runlog_{name}.txt",
        "stderr_runlog": baseline_dir / f"runlog_{name}.txt.err",
        "signal_readback_csv": decision_dir / "signal_readback.csv",
        "generated_vbs_config_copy": baseline_dir / f"generated_vbs_config_{name}.vbs",
        "wall_time_profile": baseline_dir / f"wall_time_profile_{name}.json",
        "vissim_error_evidence": baseline_dir / f"vissim_error_evidence_{name}.json",
        "run_artifact_manifest": baseline_dir / f"run_artifact_manifest_{name}.json",
    }
    missing = [key for key, path in required.items() if not path.is_file()]
    reasons: list[str] = []
    wall, wall_error = _read_json(required["wall_time_profile"])
    if wall_error is None and wall is not None:
        if wall.get("schema_version") != "wall-time-profile-v2.1" or wall.get("status") != STATUS_PASS or wall.get("run_id") != run_id or wall.get("run_name") != name or wall.get("process_exit_code") != 0 or (_number(wall.get("elapsed_wall_sec")) or -1) < 0:
            reasons.append("wall-time profile is malformed or not linked to the successful run")
    elif not missing:
        reasons.append(f"wall-time profile is invalid: {wall_error}")
    stderr_path = required["stderr_runlog"]
    if stderr_path.is_file() and stderr_path.read_text(encoding="utf-8-sig", errors="replace").strip():
        reasons.append("stderr runlog is not empty")
    status = STATUS_NOT_EVALUATED if missing else (STATUS_FAIL if reasons else STATUS_PASS)
    return _gate(status, "required deep run artifacts are missing or invalid" if status != STATUS_PASS else "all required deep run artifacts are preserved and linked", artifacts={key: _manifest_artifact(path) for key, path in required.items()}, missing=missing, reasons=reasons)


def _input_hashes(
    baseline_dir: Path,
    name: str,
    runtime_source_path: Path,
    preflight_path: Path,
    audit_path: Path,
    provenance: Mapping[str, Any] | None,
) -> dict[str, str | None]:
    paths = [runtime_source_path, preflight_path, audit_path]
    paths.extend(path for path in baseline_dir.rglob("*") if path.is_file())
    hashes = {str(path.resolve(strict=False)): _sha256_file(path) for path in sorted(set(paths), key=lambda item: str(item).casefold())}
    python_record = provenance.get("python_executable") if provenance else {}
    python_record = python_record if isinstance(python_record, Mapping) else {}
    hashes["RW_PYTHON_EXE.recorded"] = str(python_record.get("sha256", "")) or None
    python_path = Path(str(python_record.get("path", ""))) if python_record.get("path") else None
    hashes["RW_PYTHON_EXE.live_observation"] = _sha256_file(python_path) if python_path else None
    return hashes


def validate_snapshot(
    baseline_dir: Path,
    runtime_source_path: Path,
    preflight_path: Path,
    audit_path: Path,
) -> dict[str, Any]:
    baseline_dir = baseline_dir.resolve(strict=False)
    runtime_source_path = runtime_source_path.resolve(strict=False)
    preflight_path = preflight_path.resolve(strict=False)
    audit_path = audit_path.resolve(strict=False)
    chain_gate, runtime, preflight, audit = _validate_manifest_chain(baseline_dir, runtime_source_path, preflight_path, audit_path)
    provenance_gate, provenance, provenance_path = _validate_provenance(baseline_dir, preflight_path, preflight)
    name = str(provenance.get("name", EXPECTED_NAME)).strip() if provenance else EXPECTED_NAME
    run_id = str(provenance.get("run_id", "")).strip() if provenance else ""
    runlog_path = baseline_dir / f"runlog_{name}.txt"
    decision_dir = baseline_dir / f"decisions_{name}"
    runlog_gate, runlog_values = _validate_runlog(runlog_path)
    preflight_network = preflight.get("network") if preflight is not None and isinstance(preflight.get("network"), Mapping) else {}
    if preflight is not None and runlog_values.get("VERSION") != str(preflight_network.get("vissim_version", "")):
        runlog_gate["status"] = STATUS_FAIL
        runlog_gate["evidence"]["reasons"].append("runlog VERSION differs from preflight VISSIM version")
    checks = {
        "source_preflight_audit_contract": chain_gate,
        "run_provenance": provenance_gate,
        "run_completion_and_failures": runlog_gate,
        "python_runtime_identity": _validate_python_identity(provenance, runtime, preflight, runlog_values),
        "state_action_anchor_contract": _validate_json_contract(decision_dir, provenance_path, run_id),
        "state_csv_contract": _validate_state_csv(baseline_dir / f"state_{name}.csv"),
        "no_control_action_contract": _validate_no_control_actions(baseline_dir, decision_dir, provenance, preflight),
        "vissim_error_evidence": _validate_vissim_error_evidence(baseline_dir, name, run_id, provenance, audit),
        "run_artifact_manifest": _validate_run_artifact_manifest(baseline_dir, name, run_id, provenance_path),
        "preserved_artifacts": _validate_preserved_artifacts(baseline_dir, name, run_id),
    }
    counts = {status: sum(check["status"] == status for check in checks.values()) for status in (STATUS_PASS, STATUS_FAIL, STATUS_NOT_EVALUATED)}
    overall = STATUS_FAIL if counts[STATUS_FAIL] else (STATUS_NOT_EVALUATED if counts[STATUS_NOT_EVALUATED] else STATUS_PASS)
    reasons = [key for key, check in checks.items() if check["status"] != STATUS_PASS]
    return {
        "schema_version": SCHEMA_VERSION,
        "input_hashes": _input_hashes(baseline_dir, name, runtime_source_path, preflight_path, audit_path, provenance),
        "command_version": {"command": "scripts/validate_baseline_snapshot.py", "version": SCHEMA_VERSION, "sha256": _sha256_file(Path(__file__).resolve())},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_output_directory": str(baseline_dir),
        "expected_profile": EXPECTED_PROFILE,
        "run_id": run_id or None,
        "status": overall,
        "reasons": reasons,
        "complete": overall == STATUS_PASS,
        "sample_dimensions": {
            "run_provenance": 1 if provenance is not None else 0,
            "decision_state_json": 2,
            "decision_action_json": 2,
            "decision_action_csv": 2,
            "anchor_state_json": 4,
            "state_csv_observations": checks["state_csv_contract"]["evidence"].get("row_count", 0),
            "cumulative_action_rows": checks["no_control_action_contract"]["evidence"].get("cumulative_row_count", 0),
        },
        "units": {"time": "s", "demand_scale": "dimensionless", "failure_count": "count", "artifact_count": "file", "input_hashes": "SHA-256 hex digest of raw bytes"},
        "downstream_consumers": ["S1 canonical signal reference", "A physical stock topology", "DEV-DATA development campaign", "CERT-PREP certification campaign", "K plant fidelity audit"],
        "summary": {"pass": counts[STATUS_PASS], "fail": counts[STATUS_FAIL], "not_evaluated": counts[STATUS_NOT_EVALUATED]},
        "checks": checks,
    }


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path = path.resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    suffix = 0
    while temporary.exists():
        suffix += 1
        temporary = path.with_name(f".{path.name}.{os.getpid()}.{suffix}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate one canonical fixed/no-control VISSIM baseline output directory.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("baseline_output_directory", help="directory produced by -BaselineOnly")
    parser.add_argument("--runtime-source", required=True, help="strict runtime-source-v2.1 JSON")
    parser.add_argument("--preflight", required=True, help="strict preflight-v3 JSON")
    parser.add_argument("--audit", required=True, help="generic strict complete audit JSON")
    parser.add_argument("--out", required=True, help="atomic baseline-snapshot-v2.1 JSON output path")
    parser.add_argument("--strict", action="store_true", help="exit 2 when any check is FAIL")
    parser.add_argument("--require-complete", action="store_true", help="exit 3 when any required check is NOT_EVALUATED; requires --strict")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if args.require_complete and not args.strict:
        parser.error("--require-complete requires --strict")
    manifest = validate_snapshot(Path(args.baseline_output_directory), Path(args.runtime_source), Path(args.preflight), Path(args.audit))
    try:
        atomic_write_json(Path(args.out), manifest)
    except OSError as exc:
        print(f"failed to write baseline snapshot: {exc}", file=sys.stderr)
        return 4
    summary = manifest["summary"]
    print(f"baseline snapshot: status={manifest['status']} PASS={summary['pass']} FAIL={summary['fail']} NOT_EVALUATED={summary['not_evaluated']}")
    print(f"JSON: {Path(args.out).resolve(strict=False)}")
    if args.strict and summary["fail"]:
        return 2
    if args.require_complete and summary["not_evaluated"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
