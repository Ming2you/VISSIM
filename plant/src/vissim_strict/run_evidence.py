"""Strict immutable run identity and timing framing for B1a evidence."""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .physical_projection import (
    RUN_ID_PATTERN,
    SHA256_PATTERN,
    atomic_write_json,
    file_sha256,
    read_bounded_bytes,
    strict_load_json,
)
from .approval_replay import validate_approval_replay
from .topology import canonical_json_sha256, canonical_json_text


RUN_MANIFEST_SCHEMA_VERSION = "run-manifest-v2.1"
RUN_MANIFEST_CREATION_RESULT_SCHEMA_VERSION = "run-manifest-creation-result-v2.1"
SUPPORTED_VERSION_POLICY_SCHEMA_VERSION = "supported-vissim-versions-v2.1"
CANONICAL_JSON_VERSION = "canonical-json/v1"
MONOTONIC_CLOCK = "python_perf_counter_ns"
MAX_VISSIM_ID = 2_147_483_647
MAX_PATH_CHARS = 4096
MAX_STRING_CHARS = 1024
MAX_RUN_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_PREFLIGHT_BYTES = 32 * 1024 * 1024
MAX_APPROVAL_BYTES = 8 * 1024 * 1024
MAX_TOPOLOGY_BYTES = 128 * 1024 * 1024
MAX_POLICY_BYTES = 64 * 1024

RUN_MANIFEST_FIELDS = (
    "schema_version",
    "run_id",
    "campaign_id",
    "attempt",
    "qualification",
    "approved_topology",
    "preflight",
    "producer_sources",
    "configuration",
    "allowed_capture_times",
    "supported_version_policy",
    "semantic_sha256",
)
QUALIFICATION_FIELDS = ("mode",)
APPROVED_TOPOLOGY_FIELDS = (
    "approving_manifest_path",
    "approving_manifest_sha256",
    "topology_path",
    "topology_file_sha256",
    "topology_semantic_sha256",
)
PREFLIGHT_FIELDS = (
    "schema_version",
    "path",
    "file_sha256",
    "fingerprint_sha256",
)
FILE_BINDING_FIELDS = ("path", "file_sha256")
POLICY_BINDING_FIELDS = (
    "schema_version",
    "path",
    "file_sha256",
    "semantic_sha256",
)
CONFIGURATION_FIELDS = ("inputs", "simulation")
CONFIGURATION_INPUT_ROLES = (
    "network",
    "generated_vbs_config",
    "adapter",
    "calibration",
    "tuning",
    "control_mapping",
    "vehicle_input_roles",
    "demand_profile",
)
PRODUCER_SOURCE_ROLES = (
    "watchdog",
    "vbs",
    "adapter",
    "run_manifest_producer",
    "topology_approval_validator",
    "state_manifest_builder",
    "physical_projection_module",
    # v3 N0-1 - post_run_artifact_producer(build_run_artifact_manifest_v2_2.py)와
    # live_replay_builder(build_projection_live_evidence_v2_2.py)를 필수 역할에서 뺐다.
    # v3 는 런 사후 출처 사슬을 만들지 않으므로 두 파일이 영영 존재하지 않고,
    # 남겨 두면 preflight 가 영원히 FAIL 한다. 런 전 매니페스트와 해시 결속은 그대로다.
    "preflight_producer",
    "monotonic_clock_helper",
    "supported_version_policy",
)
PRODUCER_SOURCE_DEFAULT_PATHS = {
    "watchdog": "scripts/run_real_world_single_watchdog_distributed_core15n41.ps1",
    "vbs": "scripts/run_real_world_stackelberg_controller.vbs",
    "adapter": "evaluation/controllers/vissim_stackelberg_adapter.py",
    "run_manifest_producer": "scripts/build_run_manifest_v2_1.py",
    "topology_approval_validator": "scripts/approve_physical_stock_topology.py",
    "state_manifest_builder": "scripts/build_state_manifest_v2_1.py",
    "physical_projection_module": "plant/src/vissim_strict/physical_projection.py",
    "preflight_producer": "scripts/build_preflight_manifest.py",
    "monotonic_clock_helper": "scripts/read_monotonic_clock.py",
    "supported_version_policy": "plant/policies/supported_vissim_versions_v2_1.json",
}
CONFIGURATION_INPUT_DEFAULT_PATHS = {
    "network": "network/real_world_gaepo_modi/modi_eval_rw_control.inpx",
    "generated_vbs_config": "evaluation/generated/real_world_modi_control_config_distributed_core15n41_20260805.vbs",
    "adapter": "evaluation/controllers/vissim_stackelberg_adapter.py",
    "calibration": "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json",
    "tuning": "evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json",
    "control_mapping": "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core15n41_20260805.json",
    "vehicle_input_roles": "evaluation/real_world_modi_inventory/vehicle_input_roles.csv",
    "demand_profile": None,
}
SIMULATION_FIELDS = (
    "sim_period_sec",
    "control_interval_sec",
    "seed",
    "controller",
    "control_start_sec",
    "warmup_controller",
    "state_log_interval_sec",
    "demand_scale",
    "demand_profile",
    "incident_link",
    "incident_lane",
    "incident_pos_m",
    "incident_start_sec",
    "incident_end_sec",
    "incident_name",
)
ADAPTER_CONTROLLERS = frozenset(
    {
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
        "diagnostic-ramp-all500",
        "diagnostic-ramp-all400",
        "diagnostic-ramp-all300",
        "diagnostic-vsl60-only",
        "diagnostic-vsl80-only",
        "diagnostic-vsl110",
        "diagnostic-vsl100",
        "diagnostic-vsl90",
        "diagnostic-vsl80",
        "diagnostic-vsl70",
        "diagnostic-vsl60",
        "diagnostic-vsl50",
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
    }
)
SUPPORTED_VERSION_POLICY_FIELDS = (
    "schema_version",
    "canonical_json_version",
    "accepted_leading_majors",
    "normalized_major",
    "semantic_sha256",
)
CREATION_RESULT_FIELDS = (
    "schema_version",
    "status",
    "reasons",
    "outcome",
    "run_id",
    "campaign_id",
    "attempt",
    "qualification",
    "run_manifest",
    "semantic_sha256",
)
CREATION_RESULT_MANIFEST_FIELDS = ("path", "file_sha256", "semantic_sha256")
MUTABLE_RUN_FIELDS = frozenset(
    {
        "sim_sec",
        "actual_snapshot_time",
        "snapshot_time",
        "paused_at_sim_sec",
        "capture_sim_sec_before",
        "capture_sim_sec_after",
        "status",
        "reasons",
    }
)
_VERSION_RE = re.compile(r"^(20|2020)(?:\.[0-9]+)*(?:[- ][!-~]+)?$")
_MONOTONIC_RE = re.compile(rb"python_perf_counter_ns=([1-9][0-9]*)\n")


class RunManifestValidationError(ValueError):
    """One typed fail-closed error for an invalid immutable run identity."""

    def __init__(self, issues: Sequence[str]) -> None:
        normalized = tuple(sorted(set(str(issue) for issue in issues)))
        self.issues = normalized
        super().__init__("; ".join(normalized))


class RunManifestPublicationError(RunManifestValidationError):
    """Raised when create-once publication cannot preserve immutability."""


class SupportedVersionPolicyError(ValueError):
    """Raised when a policy or raw VISSIM version is invalid."""


class MonotonicClockError(ValueError):
    """Raised when monotonic-helper output violates its exact framing."""


@dataclass(frozen=True)
class ValidatedRunManifest:
    artifact: Mapping[str, Any]
    semantic_sha256: str
    qualification_mode: str
    resolved_paths: Mapping[str, Path]


@dataclass(frozen=True)
class RunManifestPublication:
    outcome: str
    manifest_path: Path
    file_sha256: str
    validated: ValidatedRunManifest


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


def _exact_fields(value: Any, fields: Sequence[str], label: str, issues: list[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        issues.append(f"{label} must be an object")
        return {}
    if set(value) != set(fields):
        issues.append(f"{label} fields mismatch")
    return value


def _is_reparse(path: Path) -> bool:
    try:
        stat_result = path.lstat()
    except OSError:
        return False
    attributes = getattr(stat_result, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & 0x400)


def _canonical_contained_file(root: Path, declared: Any, label: str) -> Path:
    if not isinstance(declared, str) or not declared or len(declared) > MAX_PATH_CHARS:
        raise ValueError(f"{label} must be a bounded nonempty path")
    if "\\" in declared or declared.startswith("/") or "//" in declared:
        raise ValueError(f"{label} must use canonical relative forward slashes")
    pure = PurePosixPath(declared)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"{label} is not a canonical relative path")

    current = root
    actual_parts: list[str] = []
    for part in pure.parts:
        try:
            matches = [child for child in current.iterdir() if child.name.casefold() == part.casefold()]
        except OSError as exc:
            raise ValueError(f"{label} is unavailable: {exc}") from exc
        if len(matches) != 1 or matches[0].name != part:
            raise ValueError(f"{label} path spelling is not canonical")
        current = matches[0]
        actual_parts.append(current.name)
        if _is_reparse(current):
            raise ValueError(f"{label} traverses a reparse point")
    if not current.is_file():
        raise ValueError(f"{label} is not an existing file")
    try:
        current.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{label} escapes the workspace") from exc
    if "/".join(actual_parts) != declared:
        raise ValueError(f"{label} path spelling is not canonical")
    return current.resolve(strict=True)


def resolve_canonical_workspace_file(
    workspace_root: str | Path, declared_path: str
) -> Path:
    """Resolve one existing canonical, non-reparse workspace-relative file."""

    root = Path(workspace_root).resolve(strict=True)
    return _canonical_contained_file(root, declared_path, "workspace path")


def resolve_canonical_workspace_absolute_file(
    workspace_root: str | Path, authored_path: str
) -> Path:
    """Validate an authored absolute Windows path before resolving its target."""

    root = Path(workspace_root).resolve(strict=True)
    if not isinstance(authored_path, str) or not authored_path or len(authored_path) > MAX_PATH_CHARS:
        raise ValueError("authored absolute path must be a bounded nonempty string")
    candidate = Path(authored_path)
    if not candidate.is_absolute() or str(candidate) != authored_path:
        raise ValueError("authored path is not lexically canonical absolute Windows syntax")
    root_text = str(root)
    prefix = root_text + os.sep
    if not authored_path.startswith(prefix):
        raise ValueError("authored absolute path does not use the exact workspace spelling")
    relative_text = authored_path[len(prefix):]
    if not relative_text or "/" in relative_text:
        raise ValueError("authored absolute path uses noncanonical separators")
    return _canonical_contained_file(
        root,
        PurePosixPath(*Path(relative_text).parts).as_posix(),
        "authored absolute path",
    )


def resolve_canonical_workspace_destination(
    workspace_root: str | Path, declared_path: str
) -> Path:
    """Resolve a canonical destination whose existing parent chain is non-reparse."""

    root = Path(workspace_root).resolve(strict=True)
    if not isinstance(declared_path, str) or not declared_path or len(declared_path) > MAX_PATH_CHARS:
        raise ValueError("workspace destination must be a bounded nonempty path")
    if "\\" in declared_path or declared_path.startswith("/") or "//" in declared_path:
        raise ValueError("workspace destination must use canonical relative forward slashes")
    pure = PurePosixPath(declared_path)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("workspace destination is not a canonical relative path")
    current = root
    for index, part in enumerate(pure.parts):
        final = index == len(pure.parts) - 1
        matches = [child for child in current.iterdir() if child.name.casefold() == part.casefold()]
        if not matches:
            if not final:
                raise ValueError("workspace destination parent does not exist")
            current = current / part
            continue
        if len(matches) != 1 or matches[0].name != part:
            raise ValueError("workspace destination spelling is not canonical")
        current = matches[0]
        if _is_reparse(current):
            raise ValueError("workspace destination traverses a reparse point")
        if not final and not current.is_dir():
            raise ValueError("workspace destination parent is not a directory")
    try:
        current.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise ValueError("workspace destination escapes the workspace") from exc
    return current.resolve(strict=False)


def _validate_hash(value: Any, label: str, issues: list[str]) -> None:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        issues.append(f"{label} must be lowercase SHA-256")


def _validate_identity(value: Any, label: str, issues: list[str]) -> None:
    if not isinstance(value, str) or RUN_ID_PATTERN.fullmatch(value) is None:
        issues.append(f"{label} is invalid")


def _validate_file_binding(
    root: Path,
    value: Any,
    label: str,
    issues: list[str],
    resolved: dict[str, Path],
    *,
    nullable: bool = False,
    max_bytes: int | None = None,
) -> Mapping[str, Any]:
    record = _exact_fields(value, FILE_BINDING_FIELDS, label, issues)
    path_value = record.get("path")
    hash_value = record.get("file_sha256")
    if nullable and path_value is None and hash_value is None:
        return record
    if path_value is None or hash_value is None:
        issues.append(f"{label} path/hash nullability mismatch")
        return record
    _validate_hash(hash_value, f"{label}.file_sha256", issues)
    try:
        path = _canonical_contained_file(root, path_value, f"{label}.path")
        if max_bytes is not None and path.stat().st_size > max_bytes:
            raise ValueError(f"{label} exceeds {max_bytes} byte limit")
        resolved[label] = path
        if isinstance(hash_value, str) and file_sha256(path) != hash_value:
            issues.append(f"{label} file hash mismatch")
    except (MemoryError, OSError, ValueError) as exc:
        issues.append(str(exc))
    return record


def run_manifest_semantic_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact canonical JSON v1 payload for run-manifest-v2.1."""

    return {field: _thaw(manifest[field]) for field in RUN_MANIFEST_FIELDS[:-1]}


def run_manifest_semantic_sha256(manifest: Mapping[str, Any]) -> str:
    return canonical_json_sha256(run_manifest_semantic_payload(manifest))


def supported_version_policy_semantic_payload(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {field: _thaw(policy[field]) for field in SUPPORTED_VERSION_POLICY_FIELDS[:-1]}


def validate_supported_version_policy(policy: Any) -> Mapping[str, Any]:
    issues: list[str] = []
    record = _exact_fields(policy, SUPPORTED_VERSION_POLICY_FIELDS, "supported version policy", issues)
    if record.get("schema_version") != SUPPORTED_VERSION_POLICY_SCHEMA_VERSION:
        issues.append("supported version policy schema mismatch")
    if record.get("canonical_json_version") != CANONICAL_JSON_VERSION:
        issues.append("supported version policy canonical JSON mismatch")
    if record.get("accepted_leading_majors") != ["20", "2020"]:
        issues.append("supported version policy accepted majors mismatch")
    if record.get("normalized_major") != 2020 or isinstance(record.get("normalized_major"), bool):
        issues.append("supported version policy normalized major mismatch")
    try:
        semantic = canonical_json_sha256(supported_version_policy_semantic_payload(record))
    except (KeyError, TypeError, ValueError) as exc:
        issues.append(f"supported version policy semantic payload invalid: {exc}")
        semantic = ""
    if record.get("semantic_sha256") != semantic:
        issues.append("supported version policy semantic hash mismatch")
    if issues:
        raise SupportedVersionPolicyError("; ".join(sorted(set(issues))))
    return _freeze(record)


def parse_supported_vissim_version(raw_version: Any, policy: Mapping[str, Any]) -> int:
    """Normalize an exact supported raw COM VERSION string without observing COM."""

    validated = validate_supported_version_policy(policy)
    if (
        not isinstance(raw_version, str)
        or not raw_version
        or len(raw_version) > 256
        or not raw_version.isascii()
        or _VERSION_RE.fullmatch(raw_version) is None
    ):
        raise SupportedVersionPolicyError("malformed or unsupported VISSIM version")
    major = _VERSION_RE.fullmatch(raw_version).group(1)  # type: ignore[union-attr]
    if major not in validated["accepted_leading_majors"]:
        raise SupportedVersionPolicyError("unsupported VISSIM major version")
    return int(validated["normalized_major"])


def parse_monotonic_clock_line(data: bytes | str) -> int:
    """Parse the helper's one-line ASCII framing."""

    if isinstance(data, str):
        try:
            encoded = data.encode("ascii")
        except UnicodeEncodeError as exc:
            raise MonotonicClockError("clock output is not ASCII") from exc
    elif isinstance(data, bytes):
        encoded = data
    else:
        raise MonotonicClockError("clock output must be bytes or text")
    match = _MONOTONIC_RE.fullmatch(encoded)
    if match is None:
        raise MonotonicClockError("clock output framing mismatch")
    try:
        value = int(match.group(1))
    except (ValueError, OverflowError) as exc:
        raise MonotonicClockError("clock value is invalid") from exc
    if value <= 0:
        raise MonotonicClockError("clock value must be positive")
    return value


def _preflight_artifact_binding(root: Path, preflight: Mapping[str, Any], role: str) -> dict[str, str] | None:
    artifacts = preflight.get("artifacts")
    if not isinstance(artifacts, Mapping):
        return None
    evidence = artifacts.get(role)
    if not isinstance(evidence, Mapping):
        return None
    path_value = evidence.get("path")
    hash_value = evidence.get("sha256")
    if not isinstance(path_value, str) or not isinstance(hash_value, str):
        return None
    try:
        path = resolve_canonical_workspace_absolute_file(root, path_value)
        relative = path.relative_to(root).as_posix()
    except (OSError, ValueError):
        return None
    return {"path": relative, "file_sha256": hash_value}


def _finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _validate_simulation(simulation: Any, inputs: Mapping[str, Any], issues: list[str]) -> None:
    value = _exact_fields(simulation, SIMULATION_FIELDS, "configuration.simulation", issues)
    positive_ints = ("sim_period_sec", "control_interval_sec", "seed", "state_log_interval_sec")
    for field in positive_ints:
        item = value.get(field)
        if not isinstance(item, int) or isinstance(item, bool) or not 0 < item <= MAX_VISSIM_ID:
            issues.append(f"configuration.simulation.{field} must be a positive JSON integer")
    sim_period = value.get("sim_period_sec")
    period = sim_period if isinstance(sim_period, int) and not isinstance(sim_period, bool) and sim_period > 0 else None
    for field in ("control_start_sec", "incident_start_sec", "incident_end_sec"):
        item = value.get(field)
        if not isinstance(item, int) or isinstance(item, bool) or (
            item != -1 and (period is None or not 0 <= item <= period)
        ):
            issues.append(f"configuration.simulation.{field} is out of range")
    start = value.get("incident_start_sec")
    end = value.get("incident_end_sec")
    if isinstance(start, int) and isinstance(end, int) and start != -1 and end != -1 and end < start:
        issues.append("configuration.simulation incident interval is reversed")
    for field in ("incident_link", "incident_lane"):
        item = value.get(field)
        if not isinstance(item, int) or isinstance(item, bool) or not 0 <= item <= MAX_VISSIM_ID:
            issues.append(f"configuration.simulation.{field} must be a nonnegative 32-bit integer")
    incident_pos = value.get("incident_pos_m")
    if not _finite_number(incident_pos) or float(incident_pos) < -1.0:
        issues.append("configuration.simulation.incident_pos_m is invalid")
    demand_scale = value.get("demand_scale")
    if not _finite_number(demand_scale) or float(demand_scale) <= 0.0:
        issues.append("configuration.simulation.demand_scale is invalid")
    for field in ("controller", "warmup_controller"):
        item = value.get(field)
        if not isinstance(item, str) or item not in ADAPTER_CONTROLLERS:
            issues.append(f"configuration.simulation.{field} is not accepted by the adapter")
    incident_name = value.get("incident_name")
    if not isinstance(incident_name, str) or len(incident_name) > MAX_STRING_CHARS or "\x00" in incident_name:
        issues.append("configuration.simulation.incident_name is invalid")
    demand_profile = value.get("demand_profile")
    input_profile = inputs.get("demand_profile") if isinstance(inputs, Mapping) else None
    input_path = input_profile.get("path") if isinstance(input_profile, Mapping) else object()
    if demand_profile != input_path or type(demand_profile) is not type(input_path):
        issues.append("configuration demand_profile duplicate binding mismatch")


def validate_run_manifest(
    manifest: Any,
    *,
    workspace_root: str | Path,
    expected_run_id: str | None = None,
    expected_campaign_id: str | None = None,
    expected_attempt: int | None = None,
    expected_approved_topology: Mapping[str, Any] | None = None,
    capture_time: float | None = None,
) -> ValidatedRunManifest:
    """Validate, rehash, and freeze one exact run-manifest-v2.1."""

    issues: list[str] = []
    resolved: dict[str, Path] = {}
    try:
        root = Path(workspace_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("workspace root is not a directory")
    except (OSError, ValueError) as exc:
        raise RunManifestValidationError([f"invalid workspace root: {exc}"]) from exc

    value = _exact_fields(manifest, RUN_MANIFEST_FIELDS, "run manifest", issues)
    if isinstance(value, Mapping) and MUTABLE_RUN_FIELDS & set(value):
        issues.append("run manifest contains mutable or verdict fields")
    if value.get("schema_version") != RUN_MANIFEST_SCHEMA_VERSION:
        issues.append("run manifest schema mismatch")
    _validate_identity(value.get("run_id"), "run_id", issues)
    _validate_identity(value.get("campaign_id"), "campaign_id", issues)
    if expected_run_id is not None and value.get("run_id") != expected_run_id:
        issues.append("run_id binding mismatch")
    if expected_campaign_id is not None and value.get("campaign_id") != expected_campaign_id:
        issues.append("campaign_id binding mismatch")
    attempt = value.get("attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= MAX_VISSIM_ID:
        issues.append("attempt must be a positive JSON integer")
    if expected_attempt is not None and attempt != expected_attempt:
        issues.append("attempt binding mismatch")

    qualification = _exact_fields(value.get("qualification"), QUALIFICATION_FIELDS, "qualification", issues)
    mode = qualification.get("mode")
    if mode not in {"live_required", "synthetic_fixture"}:
        issues.append("qualification mode is invalid")

    approved = _exact_fields(value.get("approved_topology"), APPROVED_TOPOLOGY_FIELDS, "approved_topology", issues)
    for field in ("approving_manifest_sha256", "topology_file_sha256", "topology_semantic_sha256"):
        _validate_hash(approved.get(field), f"approved_topology.{field}", issues)
    for field in ("approving_manifest_path", "topology_path"):
        hash_field = "approving_manifest_sha256" if field == "approving_manifest_path" else "topology_file_sha256"
        _validate_file_binding(
            root,
            {"path": approved.get(field), "file_sha256": approved.get(hash_field)},
            f"approved_topology.{field}",
            issues,
            resolved,
            max_bytes=(
                MAX_APPROVAL_BYTES
                if field == "approving_manifest_path"
                else MAX_TOPOLOGY_BYTES
            ),
        )
    if expected_approved_topology is not None and approved != expected_approved_topology:
        issues.append("approved_topology binding mismatch")

    preflight = _exact_fields(value.get("preflight"), PREFLIGHT_FIELDS, "preflight", issues)
    if preflight.get("schema_version") != "preflight-v3":
        issues.append("preflight schema mismatch")
    _validate_hash(preflight.get("file_sha256"), "preflight.file_sha256", issues)
    _validate_hash(preflight.get("fingerprint_sha256"), "preflight.fingerprint_sha256", issues)
    _validate_file_binding(
        root,
        {"path": preflight.get("path"), "file_sha256": preflight.get("file_sha256")},
        "preflight",
        issues,
        resolved,
        max_bytes=MAX_PREFLIGHT_BYTES,
    )

    producer_sources = _exact_fields(value.get("producer_sources"), PRODUCER_SOURCE_ROLES, "producer_sources", issues)
    producer_paths: dict[str, str] = {}
    for role in PRODUCER_SOURCE_ROLES:
        binding = _validate_file_binding(
            root,
            producer_sources.get(role),
            f"producer_sources.{role}",
            issues,
            resolved,
            max_bytes=MAX_POLICY_BYTES if role == "supported_version_policy" else None,
        )
        path_value = binding.get("path")
        if isinstance(path_value, str):
            prior = producer_paths.get(path_value.casefold())
            if prior is not None:
                issues.append(f"producer source path is duplicated by {prior} and {role}")
            producer_paths[path_value.casefold()] = role

    configuration = _exact_fields(value.get("configuration"), CONFIGURATION_FIELDS, "configuration", issues)
    inputs = _exact_fields(configuration.get("inputs"), CONFIGURATION_INPUT_ROLES, "configuration.inputs", issues)
    for role in CONFIGURATION_INPUT_ROLES:
        _validate_file_binding(
            root,
            inputs.get(role),
            f"configuration.inputs.{role}",
            issues,
            resolved,
            nullable=role == "demand_profile",
        )
    _validate_simulation(configuration.get("simulation"), inputs, issues)
    if producer_sources.get("adapter") != inputs.get("adapter"):
        issues.append("producer_sources.adapter/configuration.inputs.adapter mismatch")

    policy_binding = _exact_fields(value.get("supported_version_policy"), POLICY_BINDING_FIELDS, "supported_version_policy", issues)
    if policy_binding.get("schema_version") != SUPPORTED_VERSION_POLICY_SCHEMA_VERSION:
        issues.append("supported_version_policy schema mismatch")
    _validate_hash(policy_binding.get("file_sha256"), "supported_version_policy.file_sha256", issues)
    _validate_hash(policy_binding.get("semantic_sha256"), "supported_version_policy.semantic_sha256", issues)
    _validate_file_binding(
        root,
        {"path": policy_binding.get("path"), "file_sha256": policy_binding.get("file_sha256")},
        "supported_version_policy",
        issues,
        resolved,
        max_bytes=MAX_POLICY_BYTES,
    )
    source_policy = producer_sources.get("supported_version_policy")
    if isinstance(source_policy, Mapping) and {
        "path": policy_binding.get("path"),
        "file_sha256": policy_binding.get("file_sha256"),
    } != source_policy:
        issues.append("supported version policy duplicate binding mismatch")

    allowed = value.get("allowed_capture_times")
    if not isinstance(allowed, list):
        issues.append("allowed_capture_times must be an array")
        allowed = []
    else:
        if any(not isinstance(item, float) or not math.isfinite(item) or item < 0.0 for item in allowed):
            issues.append("allowed_capture_times must contain finite nonnegative JSON doubles")
        if any(left >= right for left, right in zip(allowed, allowed[1:])):
            issues.append("allowed_capture_times must be strictly increasing and unique")
        period = configuration.get("simulation", {}).get("sim_period_sec") if isinstance(configuration.get("simulation"), Mapping) else None
        if isinstance(period, int) and any(isinstance(item, float) and item > period for item in allowed):
            issues.append("allowed_capture_times exceed sim_period_sec")
    if capture_time is not None:
        if not _finite_number(capture_time) or float(capture_time) not in allowed:
            issues.append("capture time is not allowed by immutable manifest")

    preflight_artifact: Mapping[str, Any] = {}
    preflight_path = resolved.get("preflight")
    approval_path = resolved.get("approved_topology.approving_manifest_path")
    topology_path = resolved.get("approved_topology.topology_path")
    approval_validator_path = resolved.get(
        "producer_sources.topology_approval_validator"
    )
    if (
        approval_path is not None
        and topology_path is not None
        and preflight_path is not None
        and approval_validator_path is not None
    ):
        try:
            replay = validate_approval_replay(
                approval_path,
                workspace_root=root,
                supplied_topology_path=topology_path,
                validator_path=approval_validator_path,
                max_preflight_bytes=MAX_PREFLIGHT_BYTES,
            )
            expected_approved = {
                "approving_manifest_path": approval_path.relative_to(root).as_posix(),
                "approving_manifest_sha256": replay.approval_file_sha256,
                "topology_path": replay.topology_path.relative_to(root).as_posix(),
                "topology_file_sha256": file_sha256(replay.topology_path),
                "topology_semantic_sha256": replay.topology_semantic_sha256,
            }
            if approved != expected_approved:
                issues.append("approved topology disagrees with independent replay")
            if replay.preflight_path != preflight_path:
                issues.append("approval and run manifest bind different preflight artifacts")
            preflight_artifact = replay.preflight
            if preflight_artifact.get("fingerprint_sha256") != preflight.get("fingerprint_sha256"):
                issues.append("preflight fingerprint binding mismatch")
        except (MemoryError, OSError, ValueError) as exc:
            issues.append(f"independent approval/preflight/topology replay failed: {exc}")
    else:
        issues.append("independent approval replay inputs are unavailable")
    for role in PRODUCER_SOURCE_ROLES:
        expected = _preflight_artifact_binding(root, preflight_artifact, role)
        if expected is None or producer_sources.get(role) != expected:
            issues.append(f"producer_sources.{role} disagrees with preflight")
    for role in CONFIGURATION_INPUT_ROLES:
        binding = inputs.get(role)
        if role == "demand_profile" and isinstance(binding, Mapping) and binding.get("path") is None:
            continue
        expected = _preflight_artifact_binding(root, preflight_artifact, role)
        if expected is None or binding != expected:
            issues.append(f"configuration.inputs.{role} disagrees with preflight")

    policy_path = resolved.get("supported_version_policy")
    if policy_path is not None:
        try:
            policy = strict_load_json(policy_path, max_bytes=MAX_POLICY_BYTES)
            validated_policy = validate_supported_version_policy(policy)
            if validated_policy["semantic_sha256"] != policy_binding.get("semantic_sha256"):
                issues.append("supported version policy semantic binding mismatch")
        except (MemoryError, OSError, ValueError) as exc:
            issues.append(f"supported version policy is invalid: {exc}")

    try:
        semantic = run_manifest_semantic_sha256(value)
    except (KeyError, TypeError, ValueError) as exc:
        issues.append(f"run manifest semantic payload invalid: {exc}")
        semantic = ""
    if value.get("semantic_sha256") != semantic:
        issues.append("run manifest semantic hash mismatch")
    if issues:
        raise RunManifestValidationError(issues)
    return ValidatedRunManifest(
        artifact=_freeze(value),
        semantic_sha256=semantic,
        qualification_mode=str(mode),
        resolved_paths=MappingProxyType(dict(resolved)),
    )


def canonical_run_manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    return (canonical_json_text(_thaw(manifest)) + "\n").encode("utf-8")


def publish_run_manifest_create_once(
    path: str | Path,
    manifest: Mapping[str, Any],
    *,
    workspace_root: str | Path,
    validate_only: bool = False,
    **validation_context: Any,
) -> RunManifestPublication:
    """Create once, or validate byte-identical existing bytes without rewriting."""

    validated = validate_run_manifest(
        manifest,
        workspace_root=workspace_root,
        **validation_context,
    )
    root = Path(workspace_root).resolve(strict=True)
    target = Path(path).resolve(strict=False)
    try:
        declared_target = target.relative_to(root).as_posix()
        canonical_target = resolve_canonical_workspace_destination(root, declared_target)
    except (OSError, ValueError) as exc:
        raise RunManifestPublicationError([f"invalid manifest destination: {exc}"]) from exc
    if canonical_target != target:
        raise RunManifestPublicationError(["manifest destination spelling is not canonical"])
    payload = canonical_run_manifest_bytes(validated.artifact)
    if validate_only:
        try:
            existing = read_bounded_bytes(target, MAX_RUN_MANIFEST_BYTES)
        except (OSError, ValueError) as exc:
            raise RunManifestPublicationError([f"validate-only manifest unavailable: {exc}"]) from exc
        if existing != payload:
            raise RunManifestPublicationError(["existing manifest bytes differ"])
        try:
            reloaded = strict_load_json(target, max_bytes=MAX_RUN_MANIFEST_BYTES)
            revalidated = validate_run_manifest(
                reloaded,
                workspace_root=workspace_root,
                **validation_context,
            )
        except (OSError, ValueError) as exc:
            raise RunManifestPublicationError([f"validate-only strict reload failed: {exc}"]) from exc
        return RunManifestPublication("validated_existing", target, file_sha256(target), revalidated)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary_name, target)
        except FileExistsError as exc:
            raise RunManifestPublicationError(
                ["manifest already exists; explicit validate-only mode is required"]
            ) from exc
        except OSError as exc:
            raise RunManifestPublicationError(
                [f"manifest atomic no-clobber publication failed: {exc}"]
            ) from exc
        final_bytes = read_bounded_bytes(target, MAX_RUN_MANIFEST_BYTES)
        if final_bytes != payload:
            raise RunManifestPublicationError(["published manifest bytes differ after reload"])
        try:
            reloaded = strict_load_json(target, max_bytes=MAX_RUN_MANIFEST_BYTES)
            revalidated = validate_run_manifest(
                reloaded,
                workspace_root=workspace_root,
                **validation_context,
            )
        except (OSError, ValueError) as exc:
            raise RunManifestPublicationError(
                [f"published manifest strict reload failed: {exc}"]
            ) from exc
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    try:
        os.unlink(temporary_name)
    except FileNotFoundError:
        pass
    return RunManifestPublication("created", target, file_sha256(target), revalidated)


def creation_result_semantic_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    return {field: _thaw(result[field]) for field in CREATION_RESULT_FIELDS[:-1]}


def build_run_manifest_creation_result(
    *,
    status: str,
    reasons: Sequence[str],
    outcome: str,
    run_id: str,
    campaign_id: str,
    attempt: int | None,
    qualification: str,
    manifest_path: str,
    file_sha256_value: str,
    semantic_sha256_value: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": RUN_MANIFEST_CREATION_RESULT_SCHEMA_VERSION,
        "status": status,
        "reasons": sorted(set(str(reason)[:MAX_STRING_CHARS] for reason in reasons)),
        "outcome": outcome,
        "run_id": run_id[:128] if isinstance(run_id, str) else "",
        "campaign_id": campaign_id[:128] if isinstance(campaign_id, str) else "",
        "attempt": attempt if isinstance(attempt, int) and not isinstance(attempt, bool) else None,
        "qualification": qualification if qualification in {"live_required", "synthetic_fixture"} else "",
        "run_manifest": {
            "path": manifest_path[:MAX_PATH_CHARS] if isinstance(manifest_path, str) else "",
            "file_sha256": file_sha256_value if SHA256_PATTERN.fullmatch(file_sha256_value or "") else "",
            "semantic_sha256": semantic_sha256_value if SHA256_PATTERN.fullmatch(semantic_sha256_value or "") else "",
        },
    }
    result["semantic_sha256"] = canonical_json_sha256(creation_result_semantic_payload(result))
    return result


def write_run_manifest_creation_result(path: str | Path, result: Mapping[str, Any]) -> None:
    issues: list[str] = []
    record = _exact_fields(result, CREATION_RESULT_FIELDS, "creation result", issues)
    manifest_binding = _exact_fields(
        record.get("run_manifest"),
        CREATION_RESULT_MANIFEST_FIELDS,
        "creation result run_manifest",
        issues,
    )
    status = record.get("status")
    outcome = record.get("outcome")
    if status not in {"PASS", "FAIL"}:
        issues.append("creation result status is invalid")
    if outcome not in {"created", "validated_existing", "failed"}:
        issues.append("creation result outcome is invalid")
    if (status == "PASS") != (outcome in {"created", "validated_existing"}):
        issues.append("creation result status/outcome mismatch")
    reasons = record.get("reasons")
    if not isinstance(reasons, list) or any(
        not isinstance(reason, str) or not reason or len(reason) > MAX_STRING_CHARS
        for reason in reasons
    ) or reasons != sorted(set(reasons)):
        issues.append("creation result reasons are not canonical")
    if status == "PASS" and reasons != []:
        issues.append("successful creation result must have empty reasons")
    if status == "FAIL" and not reasons:
        issues.append("failed creation result must have reasons")
    for field in ("run_id", "campaign_id"):
        value = record.get(field)
        if not isinstance(value, str) or len(value) > 128:
            issues.append(f"creation result {field} is invalid")
    attempt = record.get("attempt")
    if attempt is not None and (
        not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= MAX_VISSIM_ID
    ):
        issues.append("creation result attempt is invalid")
    if record.get("qualification") not in {"", "live_required", "synthetic_fixture"}:
        issues.append("creation result qualification is invalid")
    path_value = manifest_binding.get("path")
    if not isinstance(path_value, str) or len(path_value) > MAX_PATH_CHARS:
        issues.append("creation result manifest path is invalid")
    for field in ("file_sha256", "semantic_sha256"):
        hash_value = manifest_binding.get(field)
        if not isinstance(hash_value, str) or (
            hash_value and SHA256_PATTERN.fullmatch(hash_value) is None
        ):
            issues.append(f"creation result run_manifest.{field} is invalid")
    if status == "PASS" and any(not manifest_binding.get(field) for field in ("path", "file_sha256", "semantic_sha256")):
        issues.append("successful creation result has incomplete manifest binding")
    try:
        semantic = canonical_json_sha256(creation_result_semantic_payload(record))
    except (KeyError, TypeError, ValueError) as exc:
        issues.append(f"creation result semantic payload invalid: {exc}")
        semantic = ""
    if record.get("semantic_sha256") != semantic:
        issues.append("creation result semantic hash mismatch")
    if issues:
        raise RunManifestValidationError(issues)
    atomic_write_json(path, record)
