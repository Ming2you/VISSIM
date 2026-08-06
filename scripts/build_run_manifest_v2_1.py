"""Build and create-once publish one exact B1a run-manifest-v2.1."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import sys
from typing import Any, Mapping, Sequence


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
PLANT_ROOT = REPO_ROOT / "plant"
for search_root in (SCRIPT_ROOT, PLANT_ROOT):
    if str(search_root) not in sys.path:
        sys.path.insert(0, str(search_root))

from approve_physical_stock_topology import (  # noqa: E402
    FAIL_CLOSED_INPUT_EXCEPTIONS,
    validate_approval_artifact,
    validate_preflight_artifact,
)
from build_state_manifest_v2_1 import expected_approved_topology_binding  # noqa: E402
from src.vissim_strict.physical_projection import (  # noqa: E402
    atomic_write_json,
    file_sha256,
    strict_json_loads,
    strict_load_json,
)
from src.vissim_strict.run_evidence import (  # noqa: E402
    CONFIGURATION_INPUT_ROLES,
    MAX_POLICY_BYTES,
    MAX_PREFLIGHT_BYTES,
    PRODUCER_SOURCE_ROLES,
    RUN_MANIFEST_SCHEMA_VERSION,
    SIMULATION_FIELDS,
    build_run_manifest_creation_result,
    publish_run_manifest_create_once,
    resolve_canonical_workspace_destination,
    resolve_canonical_workspace_absolute_file,
    resolve_canonical_workspace_file,
    run_manifest_semantic_sha256,
    validate_run_manifest,
    write_run_manifest_creation_result,
)
from src.vissim_strict.topology import canonical_json_sha256  # noqa: E402


REQUEST_SCHEMA_VERSION = "run-manifest-request-v2.1"
MAX_REQUEST_BYTES = 1_048_576
REQUEST_FIELDS = (
    "schema_version",
    "workspace_root",
    "run_directory",
    "run_id",
    "campaign_id",
    "attempt",
    "qualification",
    "topology_approval",
    "preflight",
    "producer_sources",
    "configuration",
    "allowed_capture_times",
    "output_manifest",
    "creation_result_output",
    "validate_only",
    "semantic_sha256",
)
REQUEST_QUALIFICATION_FIELDS = ("mode",)
REQUEST_CONFIGURATION_FIELDS = ("inputs", "simulation")
REQUEST_TEMPLATE_FIELDS = REQUEST_FIELDS[:-1]


class RunManifestRequestError(ValueError):
    pass


def request_semantic_payload(request: Mapping[str, Any]) -> dict[str, Any]:
    return {field: request[field] for field in REQUEST_FIELDS[:-1]}


def build_request_from_template(template: Any, *, workspace_root: Path) -> dict[str, Any]:
    """Complete a watchdog-owned request template with the sole canonical hash.

    The watchdog deliberately does not duplicate canonical JSON/hash logic.  It owns
    paths and run identity; this pinned producer turns that exact structured payload
    into the closed request consumed by the normal create/validate-only entrypoint.
    """

    value = _exact_object(template, REQUEST_TEMPLATE_FIELDS, "request template")
    request = dict(value)
    request["semantic_sha256"] = canonical_json_sha256(request_semantic_payload(request))
    validate_request(request, workspace_root=workspace_root)
    return request


def write_request_from_template(
    template_path: Path, output_path: Path, *, workspace_root: Path
) -> None:
    """Strict-read one template and atomically publish the exact request."""

    template = _read_request(template_path.resolve(strict=True))
    request = build_request_from_template(template, workspace_root=workspace_root)
    atomic_write_json(output_path, request)


def validate_request_template_no_write(template: Any, *, workspace_root: Path) -> None:
    """Exercise the exact request-to-manifest validation kernel without publishing."""

    request = build_request_from_template(template, workspace_root=workspace_root)
    manifest = _manifest_from_request(request, workspace_root)
    validate_run_manifest(
        manifest,
        workspace_root=workspace_root,
        expected_run_id=str(request["run_id"]),
        expected_campaign_id=str(request["campaign_id"]),
        expected_attempt=int(request["attempt"]),
    )


def _exact_object(value: Any, fields: Sequence[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(fields):
        raise RunManifestRequestError(f"{label} fields mismatch")
    return value


def _read_request(path: Path) -> Mapping[str, Any]:
    try:
        if path.stat().st_size > MAX_REQUEST_BYTES:
            raise RunManifestRequestError("request exceeds byte limit")
        with path.open("rb") as stream:
            raw = stream.read(MAX_REQUEST_BYTES + 1)
    except MemoryError as exc:
        raise RunManifestRequestError("request read exhausted memory") from exc
    except OSError as exc:
        raise RunManifestRequestError(f"request is unreadable: {exc}") from exc
    if len(raw) > MAX_REQUEST_BYTES:
        raise RunManifestRequestError("request exceeds byte limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RunManifestRequestError(f"request is not UTF-8: {exc}") from exc
    if text.startswith("\ufeff"):
        raise RunManifestRequestError("request UTF-8 BOM is forbidden")
    try:
        value = strict_json_loads(text)
    except (RecursionError, TypeError, ValueError) as exc:
        raise RunManifestRequestError(f"request JSON is invalid: {exc}") from exc
    if not isinstance(value, Mapping):
        raise RunManifestRequestError("request root must be an object")
    return value


def _request_context(
    request: Mapping[str, Any],
    request_path: Path,
    ownership: dict[str, bool],
) -> tuple[Path, Path, Path, Path]:
    root_value = request.get("workspace_root")
    if not isinstance(root_value, str) or not root_value or len(root_value) > 4096:
        raise RunManifestRequestError("workspace_root is invalid")
    root = Path(root_value)
    if not root.is_absolute():
        raise RunManifestRequestError("workspace_root must be absolute")
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise RunManifestRequestError(f"workspace_root is unavailable: {exc}") from exc
    if str(root) != root_value:
        raise RunManifestRequestError("workspace_root spelling is not canonical")
    try:
        request_path.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise RunManifestRequestError("request path is outside workspace") from exc

    run_declared = request.get("run_directory")
    if not isinstance(run_declared, str):
        raise RunManifestRequestError("run_directory is invalid")
    run_dir = resolve_canonical_workspace_destination(root, run_declared)
    validate_only = request.get("validate_only")
    if not isinstance(validate_only, bool):
        raise RunManifestRequestError("validate_only must be a JSON boolean")
    if run_dir.exists():
        if not run_dir.is_dir():
            raise RunManifestRequestError("run_directory is not a directory")
        if validate_only:
            ownership["owns_result"] = True
        else:
            raise RunManifestRequestError("run_directory already exists outside validate-only mode")
    else:
        if validate_only:
            raise RunManifestRequestError("validate-only run_directory does not exist")
        try:
            run_dir.mkdir()
            ownership["owns_result"] = True
        except OSError as exc:
            raise RunManifestRequestError(f"exclusive run_directory create failed: {exc}") from exc

    output_value = request.get("output_manifest")
    result_value = request.get("creation_result_output")
    if not isinstance(output_value, str) or not isinstance(result_value, str):
        raise RunManifestRequestError("output paths must be strings")
    output = resolve_canonical_workspace_destination(root, output_value)
    result = resolve_canonical_workspace_destination(root, result_value)
    if output.parent != run_dir or result.parent != run_dir or output == result:
        raise RunManifestRequestError("manifest and creation result must be distinct direct run-directory children")
    return root, run_dir, output, result


def _prepare_cli_result_context(
    args: argparse.Namespace,
    ownership: dict[str, bool],
) -> Path | None:
    supplied = (args.workspace_root, args.run_directory, args.creation_result_output)
    if not any(supplied):
        return None
    if not all(supplied):
        raise RunManifestRequestError(
            "workspace-root, run-directory, and creation-result-output must be supplied together"
        )
    root = Path(args.workspace_root)
    if not root.is_absolute() or str(root.resolve(strict=True)) != args.workspace_root:
        raise RunManifestRequestError("CLI workspace-root is not canonical")
    root = root.resolve(strict=True)
    run_dir = resolve_canonical_workspace_destination(root, args.run_directory)
    if args.validate_only:
        if not run_dir.is_dir():
            raise RunManifestRequestError("CLI validate-only run directory is unavailable")
        ownership["owns_result"] = True
    else:
        if run_dir.exists():
            raise RunManifestRequestError(
                "CLI run directory already exists outside validate-only mode"
            )
    result_declared = args.creation_result_output
    if (
        not isinstance(result_declared, str)
        or not result_declared
        or "\\" in result_declared
        or result_declared.startswith("/")
        or "//" in result_declared
    ):
        raise RunManifestRequestError("CLI creation result path is invalid")
    result_pure = PurePosixPath(result_declared)
    if result_pure.is_absolute() or any(part in {"", ".", ".."} for part in result_pure.parts):
        raise RunManifestRequestError("CLI creation result path is not canonical")
    result_path = root.joinpath(*result_pure.parts).resolve(strict=False)
    if result_path.parent != run_dir:
        raise RunManifestRequestError(
            "CLI creation result must be a direct run-directory child"
        )
    return result_path


def _validate_cli_context_matches_request(
    args: argparse.Namespace, request: Mapping[str, Any]
) -> None:
    expected = {
        "workspace_root": args.workspace_root,
        "run_directory": args.run_directory,
        "creation_result_output": args.creation_result_output,
    }
    for field, supplied in expected.items():
        if supplied and request.get(field) != supplied:
            raise RunManifestRequestError(f"CLI/request {field} mismatch")
    if args.validate_only and request.get("validate_only") is not True:
        raise RunManifestRequestError("CLI/request validate_only mismatch")


def validate_request(request: Any, *, workspace_root: Path) -> Mapping[str, Any]:
    value = _exact_object(request, REQUEST_FIELDS, "request")
    if value.get("schema_version") != REQUEST_SCHEMA_VERSION:
        raise RunManifestRequestError("request schema mismatch")
    _exact_object(value.get("qualification"), REQUEST_QUALIFICATION_FIELDS, "request.qualification")
    if value["qualification"].get("mode") not in {"live_required", "synthetic_fixture"}:
        raise RunManifestRequestError("request qualification mode is invalid")
    sources = _exact_object(value.get("producer_sources"), PRODUCER_SOURCE_ROLES, "request.producer_sources")
    if any(not isinstance(sources.get(role), str) for role in PRODUCER_SOURCE_ROLES):
        raise RunManifestRequestError("request producer source paths must be strings")
    configuration = _exact_object(value.get("configuration"), REQUEST_CONFIGURATION_FIELDS, "request.configuration")
    inputs = _exact_object(configuration.get("inputs"), CONFIGURATION_INPUT_ROLES, "request.configuration.inputs")
    for role in CONFIGURATION_INPUT_ROLES:
        item = inputs.get(role)
        if role == "demand_profile":
            if item is not None and not isinstance(item, str):
                raise RunManifestRequestError("request demand_profile must be a string or null")
        elif not isinstance(item, str):
            raise RunManifestRequestError(f"request configuration input {role} must be a string")
    _exact_object(configuration.get("simulation"), SIMULATION_FIELDS, "request.configuration.simulation")
    if not isinstance(value.get("allowed_capture_times"), list):
        raise RunManifestRequestError("request allowed_capture_times must be an array")
    expected_semantic = canonical_json_sha256(request_semantic_payload(value))
    if value.get("semantic_sha256") != expected_semantic:
        raise RunManifestRequestError("request semantic hash mismatch")
    for field in ("topology_approval", "preflight"):
        if not isinstance(value.get(field), str):
            raise RunManifestRequestError(f"request {field} must be a string")
        resolve_canonical_workspace_file(workspace_root, value[field])
    return value


def _binding(
    root: Path, declared_path: str, *, max_bytes: int | None = None
) -> dict[str, str]:
    path = resolve_canonical_workspace_file(root, declared_path)
    if max_bytes is not None and path.stat().st_size > max_bytes:
        raise RunManifestRequestError(
            f"bound artifact {declared_path} exceeds {max_bytes} byte limit"
        )
    return {"path": declared_path, "file_sha256": file_sha256(path)}


def _preflight_binding(root: Path, preflight_path: Path, preflight: Mapping[str, Any]) -> dict[str, str]:
    return {
        "schema_version": "preflight-v3",
        "path": preflight_path.relative_to(root).as_posix(),
        "file_sha256": file_sha256(preflight_path),
        "fingerprint_sha256": str(preflight["fingerprint_sha256"]),
    }


def _manifest_from_request(request: Mapping[str, Any], root: Path) -> dict[str, Any]:
    approval_path = resolve_canonical_workspace_file(root, request["topology_approval"])
    preflight_path = resolve_canonical_workspace_file(root, request["preflight"])
    bundle = validate_approval_artifact(
        approval_path,
        workspace_root=root,
        supplied_topology_path=None,
    )
    if bundle.preflight_path != preflight_path:
        raise RunManifestRequestError("approval and request bind different preflight artifacts")
    preflight = strict_load_json(preflight_path, max_bytes=MAX_PREFLIGHT_BYTES)
    if not isinstance(preflight, Mapping):
        raise RunManifestRequestError("preflight root is not an object")
    preflight_reasons = validate_preflight_artifact(preflight, root)
    if preflight_reasons:
        raise RunManifestRequestError(f"preflight validation failed: {preflight_reasons}")

    request_sources = request["producer_sources"]
    producer_sources = {
        role: _binding(
            root,
            request_sources[role],
            max_bytes=MAX_POLICY_BYTES if role == "supported_version_policy" else None,
        )
        for role in PRODUCER_SOURCE_ROLES
    }
    artifacts = preflight.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise RunManifestRequestError("preflight artifacts map is unavailable")
    for role, binding in producer_sources.items():
        evidence = artifacts.get(role)
        if not isinstance(evidence, Mapping):
            raise RunManifestRequestError(f"preflight omits producer source {role}")
        try:
            evidence_path = resolve_canonical_workspace_absolute_file(
                root, evidence.get("path")
            )
            expected = {
                "path": evidence_path.relative_to(root).as_posix(),
                "file_sha256": str(evidence.get("sha256", "")),
            }
        except (OSError, ValueError) as exc:
            raise RunManifestRequestError(f"preflight producer source {role} is invalid: {exc}") from exc
        if binding != expected:
            raise RunManifestRequestError(f"producer source {role} disagrees with preflight")

    request_inputs = request["configuration"]["inputs"]
    inputs: dict[str, Any] = {}
    for role in CONFIGURATION_INPUT_ROLES:
        declared = request_inputs[role]
        inputs[role] = (
            {"path": None, "file_sha256": None}
            if declared is None
            else _binding(root, declared)
        )
        if declared is not None:
            evidence = artifacts.get(role)
            if not isinstance(evidence, Mapping):
                raise RunManifestRequestError(f"preflight omits configuration input {role}")
            try:
                evidence_path = resolve_canonical_workspace_absolute_file(
                    root, evidence.get("path")
                )
                expected = {
                    "path": evidence_path.relative_to(root).as_posix(),
                    "file_sha256": str(evidence.get("sha256", "")),
                }
            except (OSError, ValueError) as exc:
                raise RunManifestRequestError(f"preflight configuration input {role} is invalid: {exc}") from exc
            if inputs[role] != expected:
                raise RunManifestRequestError(f"configuration input {role} disagrees with preflight")

    policy_source = producer_sources["supported_version_policy"]
    policy = strict_load_json(
        resolve_canonical_workspace_file(root, policy_source["path"]),
        max_bytes=MAX_POLICY_BYTES,
    )
    if not isinstance(policy, Mapping):
        raise RunManifestRequestError("supported version policy root is not an object")
    manifest: dict[str, Any] = {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": request["run_id"],
        "campaign_id": request["campaign_id"],
        "attempt": request["attempt"],
        "qualification": dict(request["qualification"]),
        "approved_topology": expected_approved_topology_binding(bundle),
        "preflight": _preflight_binding(root, preflight_path, preflight),
        "producer_sources": producer_sources,
        "configuration": {
            "inputs": inputs,
            "simulation": dict(request["configuration"]["simulation"]),
        },
        "allowed_capture_times": list(request["allowed_capture_times"]),
        "supported_version_policy": {
            "schema_version": policy.get("schema_version"),
            "path": policy_source["path"],
            "file_sha256": policy_source["file_sha256"],
            "semantic_sha256": policy.get("semantic_sha256"),
        },
    }
    manifest["semantic_sha256"] = run_manifest_semantic_sha256(manifest)
    return manifest


def _failure_context(request: Mapping[str, Any]) -> tuple[str, str, int | None, str, str]:
    qualification = request.get("qualification")
    mode = qualification.get("mode", "") if isinstance(qualification, Mapping) else ""
    return (
        str(request.get("run_id", "")),
        str(request.get("campaign_id", "")),
        request.get("attempt") if isinstance(request.get("attempt"), int) and not isinstance(request.get("attempt"), bool) else None,
        str(mode),
        str(request.get("output_manifest", "")),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--request-template", type=Path)
    parser.add_argument("--write-request")
    parser.add_argument("--workspace-root", default="")
    parser.add_argument("--run-directory", default="")
    parser.add_argument("--creation-result-output", default="")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--validate-template-stdin", action="store_true")
    args = parser.parse_args(argv)

    if args.validate_template_stdin:
        if any(
            (
                args.request is not None,
                args.request_template is not None,
                args.write_request is not None,
                bool(args.run_directory),
                bool(args.creation_result_output),
                args.validate_only,
            )
        ) or not args.workspace_root:
            parser.error(
                "--validate-template-stdin requires only --workspace-root"
            )
        try:
            root = Path(args.workspace_root)
            if not root.is_absolute() or str(root.resolve(strict=True)) != args.workspace_root:
                raise RunManifestRequestError("workspace-root is not canonical")
            raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
            if len(raw) > MAX_REQUEST_BYTES:
                raise RunManifestRequestError("request template exceeds byte limit")
            if raw.startswith(b"\xef\xbb\xbf"):
                raise RunManifestRequestError("request template UTF-8 BOM is forbidden")
            template = strict_json_loads(raw.decode("utf-8"))
            validate_request_template_no_write(
                template,
                workspace_root=root.resolve(strict=True),
            )
            return 0
        except (RecursionError, *FAIL_CLOSED_INPUT_EXCEPTIONS, RunManifestRequestError):
            return 1

    if args.request_template is not None or args.write_request is not None:
        if args.request is not None or args.request_template is None or args.write_request is None:
            parser.error("--request-template and --write-request must be supplied together and exclude --request")
        if not args.workspace_root:
            parser.error("--workspace-root is required with --request-template")
        root = Path(args.workspace_root)
        try:
            if not root.is_absolute() or str(root.resolve(strict=True)) != args.workspace_root:
                raise RunManifestRequestError("workspace-root is not canonical")
            root = root.resolve(strict=True)
            template_path = args.request_template.resolve(strict=True)
            output_path = resolve_canonical_workspace_destination(root, str(args.write_request))
            if output_path.exists():
                raise RunManifestRequestError("request output already exists")
            if output_path.parent != template_path.parent:
                raise RunManifestRequestError("request output must share the template directory")
            write_request_from_template(template_path, output_path, workspace_root=root)
            return 0
        except (RecursionError, *FAIL_CLOSED_INPUT_EXCEPTIONS, RunManifestRequestError):
            return 1

    if args.request is None:
        parser.error("--request is required unless building a request from a template")

    request: Mapping[str, Any] = {}
    result_path: Path | None = None
    ownership = {"owns_result": False}
    try:
        result_path = _prepare_cli_result_context(args, ownership)
        request = _read_request(args.request.resolve(strict=True))
        _validate_cli_context_matches_request(args, request)
        root, _, output_path, request_result_path = _request_context(
            request, args.request, ownership
        )
        if result_path is not None and result_path != request_result_path:
            raise RunManifestRequestError("CLI/request creation result path mismatch")
        result_path = request_result_path
        request = validate_request(request, workspace_root=root)
        manifest = _manifest_from_request(request, root)
        publication = publish_run_manifest_create_once(
            output_path,
            manifest,
            workspace_root=root,
            validate_only=bool(request["validate_only"]),
        )
        result = build_run_manifest_creation_result(
            status="PASS",
            reasons=[],
            outcome=publication.outcome,
            run_id=str(request["run_id"]),
            campaign_id=str(request["campaign_id"]),
            attempt=int(request["attempt"]),
            qualification=str(request["qualification"]["mode"]),
            manifest_path=str(request["output_manifest"]),
            file_sha256_value=publication.file_sha256,
            semantic_sha256_value=publication.validated.semantic_sha256,
        )
        write_run_manifest_creation_result(result_path, result)
        return 0
    except (RecursionError, *FAIL_CLOSED_INPUT_EXCEPTIONS) as exc:
        if result_path is None and request and ownership.get("owns_result", False):
            try:
                root_value = request.get("workspace_root")
                result_value = request.get("creation_result_output")
                if isinstance(root_value, str) and isinstance(result_value, str):
                    root = Path(root_value).resolve(strict=True)
                    result_path = resolve_canonical_workspace_destination(root, result_value)
            except FAIL_CLOSED_INPUT_EXCEPTIONS:
                result_path = None
        if result_path is not None and ownership.get("owns_result", False):
            run_id, campaign_id, attempt, qualification, manifest_path = _failure_context(request)
            result = build_run_manifest_creation_result(
                status="FAIL",
                reasons=[f"{type(exc).__name__}: {exc}"],
                outcome="failed",
                run_id=run_id,
                campaign_id=campaign_id,
                attempt=attempt,
                qualification=qualification,
                manifest_path=manifest_path,
                file_sha256_value="",
                semantic_sha256_value="",
            )
            try:
                write_run_manifest_creation_result(result_path, result)
            except FAIL_CLOSED_INPUT_EXCEPTIONS:
                pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
