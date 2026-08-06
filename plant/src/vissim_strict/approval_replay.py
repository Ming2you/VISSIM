"""Package-stable client for the canonical topology approval replay."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping

from .physical_projection import file_sha256, strict_json_loads, strict_load_json
from .topology import canonical_json_text


VALIDATION_RESULT_SCHEMA_VERSION = "topology-approval-validation-v2.1"
VALIDATION_RESULT_FIELDS = {
    "schema_version",
    "status",
    "reasons",
    "workspace_root",
    "approval_path",
    "approval_file_sha256",
    "preflight_path",
    "preflight_file_sha256",
    "topology_path",
    "topology_file_sha256",
    "topology_semantic_sha256",
}
MAX_VALIDATION_RESULT_BYTES = 65_536
UTF8_BOM = b"\xef\xbb\xbf"


class ApprovalReplayError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedApprovalReplay:
    workspace_root: Path
    approval_path: Path
    approval_file_sha256: str
    preflight_path: Path
    topology_path: Path
    topology_semantic_sha256: str
    preflight: Mapping[str, Any]


def validation_result_wire_bytes(result: Mapping[str, Any]) -> bytes:
    """Encode the exact strict UTF-8/no-BOM/canonical-JSON/LF worker wire."""

    encoded = (canonical_json_text(result) + "\n").encode("utf-8")
    if encoded.startswith(UTF8_BOM):
        raise ApprovalReplayError("approval replay worker wire contains a UTF-8 BOM")
    return encoded


def decode_validation_result_wire(data: bytes) -> Mapping[str, Any]:
    if len(data) > MAX_VALIDATION_RESULT_BYTES:
        raise ApprovalReplayError("approval replay worker output exceeds byte limit")
    if data.startswith(UTF8_BOM):
        raise ApprovalReplayError("approval replay worker result contains a UTF-8 BOM")
    try:
        text = data.decode("utf-8")
        result = strict_json_loads(text)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ApprovalReplayError(f"approval replay worker result is invalid: {exc}") from exc
    if not isinstance(result, dict) or set(result) != VALIDATION_RESULT_FIELDS:
        raise ApprovalReplayError("approval replay worker result shape mismatch")
    if data != validation_result_wire_bytes(result):
        raise ApprovalReplayError("approval replay worker result is not canonical")
    return result


def _contained_result_path(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ApprovalReplayError(f"approval replay {label} is invalid")
    path = Path(value)
    if not path.is_absolute() or str(path) != value:
        raise ApprovalReplayError(f"approval replay {label} spelling is invalid")
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ApprovalReplayError(f"approval replay {label} is unavailable: {exc}") from exc
    if resolved != path or not resolved.is_file():
        raise ApprovalReplayError(f"approval replay {label} is not a canonical file")
    return resolved


def _run_validation_worker(
    validator_path: Path,
    workspace_root: Path,
    approval_path: Path,
    topology_path: Path,
) -> tuple[int, bytes, bytes]:
    command = [
        sys.executable,
        "-B",
        str(validator_path),
        "--workspace-root",
        str(workspace_root),
        "--validate-existing",
        str(approval_path),
        "--supplied-topology",
        str(topology_path),
    ]
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            completed = subprocess.run(
                command,
                cwd=workspace_root,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ApprovalReplayError(f"approval replay worker failed: {exc}") from exc
        stdout_size = stdout.tell()
        stderr_size = stderr.tell()
        if stdout_size > MAX_VALIDATION_RESULT_BYTES or stderr_size > MAX_VALIDATION_RESULT_BYTES:
            raise ApprovalReplayError("approval replay worker output exceeds byte limit")
        stdout.seek(0)
        stderr.seek(0)
        return completed.returncode, stdout.read(), stderr.read()


def validate_approval_replay(
    approval_path: str | Path,
    *,
    workspace_root: str | Path,
    supplied_topology_path: str | Path,
    validator_path: str | Path,
    max_preflight_bytes: int,
) -> ValidatedApprovalReplay:
    """Run the sole canonical approval replay without importing workspace scripts."""

    root = Path(workspace_root).resolve(strict=True)
    approval = Path(approval_path).resolve(strict=True)
    topology = Path(supplied_topology_path).resolve(strict=True)
    validator = Path(validator_path).resolve(strict=True)
    for label, path in (
        ("approval", approval),
        ("topology", topology),
        ("validator", validator),
    ):
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ApprovalReplayError(f"{label} path escapes workspace") from exc
        if not path.is_file():
            raise ApprovalReplayError(f"{label} path is not a file")

    returncode, stdout, stderr = _run_validation_worker(
        validator, root, approval, topology
    )
    if stderr != b"":
        raise ApprovalReplayError("approval replay worker wrote stderr")
    result = decode_validation_result_wire(stdout)
    reasons = result.get("reasons")
    if returncode != 0 or result.get("status") != "PASS" or reasons != []:
        raise ApprovalReplayError(f"approval replay rejected artifact: {reasons}")
    if result.get("schema_version") != VALIDATION_RESULT_SCHEMA_VERSION:
        raise ApprovalReplayError("approval replay worker schema mismatch")
    if result.get("workspace_root") != str(root):
        raise ApprovalReplayError("approval replay workspace mismatch")

    replayed_approval = _contained_result_path(root, result.get("approval_path"), "approval_path")
    replayed_preflight = _contained_result_path(root, result.get("preflight_path"), "preflight_path")
    replayed_topology = _contained_result_path(root, result.get("topology_path"), "topology_path")
    if replayed_approval != approval or replayed_topology != topology:
        raise ApprovalReplayError("approval replay input path mismatch")
    expected_hashes = {
        "approval_file_sha256": file_sha256(approval),
        "preflight_file_sha256": file_sha256(replayed_preflight),
        "topology_file_sha256": file_sha256(topology),
    }
    for field, expected in expected_hashes.items():
        if result.get(field) != expected:
            raise ApprovalReplayError(f"approval replay {field} mismatch")
    topology_semantic = result.get("topology_semantic_sha256")
    if not isinstance(topology_semantic, str) or len(topology_semantic) != 64:
        raise ApprovalReplayError("approval replay topology semantic hash is invalid")
    preflight = strict_load_json(
        replayed_preflight, max_bytes=max_preflight_bytes
    )
    if not isinstance(preflight, Mapping):
        raise ApprovalReplayError("approval replay preflight root is not an object")
    return ValidatedApprovalReplay(
        workspace_root=root,
        approval_path=approval,
        approval_file_sha256=expected_hashes["approval_file_sha256"],
        preflight_path=replayed_preflight,
        topology_path=topology,
        topology_semantic_sha256=topology_semantic,
        preflight=preflight,
    )
