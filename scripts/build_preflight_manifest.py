from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
PLANT_ROOT = REPO_ROOT / "plant"
if str(PLANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PLANT_ROOT))

from src.vissim_strict.run_evidence import (  # noqa: E402
    CONFIGURATION_INPUT_DEFAULT_PATHS,
    PRODUCER_SOURCE_DEFAULT_PATHS,
)


SCHEMA_VERSION = "preflight-v3"
RUNTIME_SOURCE_SCHEMA = "runtime-source-v2.1"
EXPECTED_NUMSIM_COMMIT = "bd1cf91c3b2cb84e80e279fba78aa5d3f1ea1016"
RUNTIME_SOURCE_TRUST_CHECKS = (
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
EXPECTED_MODEL_SC_COUNT = 41
EXPECTED_RESOLVED_SIG_COUNT = 41
EXPECTED_AUXILIARY_SC_COUNT = 8
DEFAULT_EXCLUDED_SC = "9004"

DEFAULT_PATHS = {
    "network": "network/real_world_gaepo_modi/modi_eval_rw_control.inpx",
    "signal_roles": "evaluation/real_world_modi_inventory/signal_controller_roles.csv",
    "link_assignment": "outputs/link_player_assignment_20260805.json",
    "adjacency": "outputs/intersection_adjacency8_20260805.json",
    "storage_capacity": "outputs/urban_storage_capacity_20260805.json",
    "tuning": "evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json",
    "calibration": "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json",
    "control_mapping": "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core15n41_20260805.json",
    "detector_mapping": "evaluation/real_world_modi_control_distributed_20260728/detector_local_mapping_distributed_core15n41_20260805.json",
    "generated_vbs": "evaluation/generated/real_world_modi_control_config_distributed_core15n41_20260805.vbs",
    "runner": "scripts/run_real_world_stackelberg_controller.vbs",
    "watchdog": "scripts/run_real_world_single_watchdog_distributed_core15n41.ps1",
    "adapter": "evaluation/controllers/vissim_stackelberg_adapter.py",
    "runtime_source_verifier": "scripts/verify_runtime_source.py",
    "runtime_source_anchor": "vendor/NumSim-mine/UPSTREAM_TREE.json",
}
DEFAULT_PATHS.update(PRODUCER_SOURCE_DEFAULT_PATHS)
DEFAULT_PATHS.update({
    role: path
    for role, path in CONFIGURATION_INPUT_DEFAULT_PATHS.items()
    if path is not None
})


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return _sha256(path.read_bytes()) if path.is_file() else ""


def _normalise_eol(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def source_tree_identity(root: Path) -> dict[str, Any]:
    source_root = root / "src"
    sources = sorted(
        source_root.rglob("*.py") if source_root.is_dir() else [],
        key=lambda item: item.relative_to(source_root).as_posix(),
    )
    digest = hashlib.sha256()
    files: dict[str, str] = {}
    for source in sources:
        relative = source.relative_to(source_root).as_posix()
        source_hash = _sha256(_normalise_eol(source.read_bytes()))
        files[relative] = source_hash
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source_hash.encode("ascii"))
        digest.update(b"\0")
    return {
        "root": str(root.resolve()),
        "python_file_count": len(sources),
        "normalised_tree_sha256": digest.hexdigest() if sources else "",
        "files": files,
    }


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.samefile(right)
    except (FileNotFoundError, OSError):
        return left.resolve() == right.resolve()


def artifact_evidence(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=False)
    exists = resolved.is_file()
    return {
        "path": str(resolved),
        "exists": exists,
        "size_bytes": resolved.stat().st_size if exists else 0,
        "sha256": file_sha256(resolved),
    }


class Checks:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, identifier: str, passed: bool, expected: Any, actual: Any) -> None:
        self.items.append(
            {
                "id": identifier,
                "status": "PASS" if passed else "FAIL",
                "expected": expected,
                "actual": actual,
            }
        )

    @property
    def reasons(self) -> list[str]:
        return [item["id"] for item in self.items if item["status"] != "PASS"]


def _controller_sort_key(value: str) -> tuple[int, str]:
    try:
        return int(value), value
    except ValueError:
        return sys.maxsize, value


def _resolve_repo_path(repo: Path, value: str | Path | None, default: str) -> Path:
    raw = Path(value) if value else Path(default)
    return raw.resolve(strict=False) if raw.is_absolute() else (repo / raw).resolve(strict=False)


def _resolve_supply_file(signal_dir: Path, supply_file_2: str) -> Path | None:
    value = supply_file_2.strip()
    if not value:
        return None
    if value.lower().startswith("#data#"):
        value = value[6:]
    elif value.startswith("#"):
        return None
    value = value.replace("\\", os.sep).replace("/", os.sep)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = signal_dir / candidate
    return candidate.resolve(strict=False)


def _sig_metadata(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.is_file():
        return {}, "missing"
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    if root.tag.rsplit("}", 1)[-1].lower() != "sc":
        return {}, f"unexpected root element {root.tag!r}"
    return {
        "root_element": root.tag.rsplit("}", 1)[-1],
        "signal_file_id": root.get("id", ""),
        "signal_file_version": root.get("version", ""),
    }, None


def _read_roles(path: Path) -> tuple[dict[str, dict[str, str]], str | None]:
    if not path.is_file():
        return {}, "missing"
    rows: dict[str, dict[str, str]] = {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                raw_no = str(row.get("no", "")).strip()
                try:
                    number = str(int(float(raw_no)))
                except ValueError:
                    continue
                if number in rows:
                    return {}, f"duplicate controller {number}"
                rows[number] = {str(key): str(value or "") for key, value in row.items()}
    except (OSError, UnicodeError, csv.Error) as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    return rows, None


def _parse_network(
    network: Path,
    signal_dir: Path,
    roles_path: Path,
    checks: Checks,
    *,
    expected_model_count: int,
    expected_resolved_sig_count: int,
    expected_auxiliary_count: int,
    excluded_sc: str,
) -> dict[str, Any]:
    if not network.is_file():
        checks.add("network.exists", False, True, False)
        return {
            "path": str(network),
            "vissim_version": "",
            "model_controllers": [],
            "resolved_signal_programs": [],
            "excluded_controller": None,
            "auxiliary_controllers": [],
            "unclassified_controllers": [],
            "malformed_signal_head_references": [],
        }
    checks.add("network.exists", True, True, True)
    try:
        root = ET.parse(network).getroot()
    except (OSError, ET.ParseError) as exc:
        checks.add("network.xml", False, "well-formed XML", f"{type(exc).__name__}: {exc}")
        return {
            "path": str(network),
            "vissim_version": "",
            "model_controllers": [],
            "resolved_signal_programs": [],
            "excluded_controller": None,
            "auxiliary_controllers": [],
            "unclassified_controllers": [],
            "malformed_signal_head_references": [],
        }
    checks.add("network.xml", True, "well-formed XML", "well-formed XML")

    controllers: dict[str, ET.Element] = {}
    duplicate_controllers: list[str] = []
    for element in root.iter("signalController"):
        number = str(element.get("no", "")).strip()
        if not number:
            continue
        if number in controllers:
            duplicate_controllers.append(number)
        else:
            controllers[number] = element
    checks.add("network.signal_controller_ids_unique", not duplicate_controllers, [], duplicate_controllers)

    head_refs: Counter[str] = Counter()
    malformed_head_refs: list[dict[str, str]] = []
    for head in root.iter("signalHead"):
        parts = str(head.get("sg", "")).split()
        if len(parts) < 2 or not parts[0]:
            malformed_head_refs.append({"head_no": str(head.get("no", "")), "sg": str(head.get("sg", ""))})
            continue
        head_refs[parts[0]] += 1
    checks.add("network.signal_head_references_well_formed", not malformed_head_refs, [], malformed_head_refs)
    unknown_head_refs = sorted(set(head_refs) - set(controllers), key=_controller_sort_key)
    checks.add("network.signal_head_controller_references_resolve", not unknown_head_refs, [], unknown_head_refs)

    model_controllers: list[dict[str, Any]] = []
    signal_programs: list[dict[str, Any]] = []
    excluded_records: list[dict[str, Any]] = []
    auxiliary: list[dict[str, Any]] = []
    unclassified: list[dict[str, Any]] = []

    for number in sorted(controllers, key=_controller_sort_key):
        controller = controllers[number]
        active = str(controller.get("active", "")).strip().lower() == "true"
        controller_type = str(controller.get("type", "")).strip()
        is_fixed = controller_type.upper() == "FIXEDTIME"
        supply = str(controller.get("supplyFile2", "")).strip()
        reference_count = int(head_refs.get(number, 0))
        base = {
            "controller_no": number,
            "name": str(controller.get("name", "")),
            "active": active,
            "type": controller_type,
            "program_no": str(controller.get("progNo", "")),
            "supply_file_2": supply,
            "signal_head_reference_count": reference_count,
        }
        if active and is_fixed and supply and reference_count > 0:
            resolved = _resolve_supply_file(signal_dir, supply)
            sig_artifact = artifact_evidence(resolved) if resolved else {
                "path": "",
                "exists": False,
                "size_bytes": 0,
                "sha256": "",
            }
            metadata, sig_error = _sig_metadata(resolved) if resolved else ({}, "unsupported supplyFile2")
            record = dict(base)
            record["signal_program"] = {**sig_artifact, **metadata}
            model_controllers.append(record)
            signal_programs.append(
                {
                    "controller_no": number,
                    "supply_file_2": supply,
                    **sig_artifact,
                    **metadata,
                }
            )
            checks.add(f"signal_program.SC{number}.resolved", sig_error is None, "existing .sig XML", sig_error or "resolved")
            checks.add(f"signal_program.SC{number}.sha256", bool(sig_artifact["sha256"]), "non-empty SHA-256", sig_artifact["sha256"])
        elif active and is_fixed and supply and reference_count == 0:
            record = dict(base)
            resolved = _resolve_supply_file(signal_dir, supply)
            record["signal_program"] = artifact_evidence(resolved) if resolved else {
                "path": "",
                "exists": False,
                "size_bytes": 0,
                "sha256": "",
            }
            record["reason"] = "no signal-head reference in network XML"
            excluded_records.append(record)
        elif active and is_fixed and not supply and reference_count > 0:
            record = dict(base)
            record["reason"] = "artificial controller with signal heads and no fixed SIG"
            auxiliary.append(record)
        elif reference_count > 0 or supply:
            record = dict(base)
            record["reason"] = "does not satisfy model, exclusion, or auxiliary classification"
            unclassified.append(record)

    resolved_programs = [item for item in signal_programs if item["exists"] and item["sha256"]]
    unique_sig_paths = {os.path.normcase(str(item["path"])) for item in resolved_programs}
    checks.add("network.model_sc_count", len(model_controllers) == expected_model_count, expected_model_count, len(model_controllers))
    checks.add(
        "network.resolved_sig_count",
        len(resolved_programs) == expected_resolved_sig_count,
        expected_resolved_sig_count,
        len(resolved_programs),
    )
    checks.add(
        "network.unique_resolved_sig_count",
        len(unique_sig_paths) == expected_resolved_sig_count,
        expected_resolved_sig_count,
        len(unique_sig_paths),
    )
    checks.add(
        "network.auxiliary_sc_count",
        len(auxiliary) == expected_auxiliary_count,
        expected_auxiliary_count,
        len(auxiliary),
    )
    checks.add("network.unclassified_controllers", not unclassified, [], [item["controller_no"] for item in unclassified])

    excluded_record = next((item for item in excluded_records if item["controller_no"] == excluded_sc), None)
    checks.add("network.excluded_sc_present", excluded_record is not None, excluded_sc, [item["controller_no"] for item in excluded_records])
    checks.add(
        "network.excluded_sc_head_reference_count",
        bool(excluded_record) and excluded_record["signal_head_reference_count"] == 0,
        0,
        excluded_record["signal_head_reference_count"] if excluded_record else None,
    )
    unexpected_excluded = [item["controller_no"] for item in excluded_records if item["controller_no"] != excluded_sc]
    checks.add("network.unexpected_excluded_controllers", not unexpected_excluded, [], unexpected_excluded)

    roles, roles_error = _read_roles(roles_path)
    checks.add("signal_roles.readable", roles_error is None, "readable unique controller rows", roles_error or "readable")
    if roles_error is None:
        role_active = {number for number, row in roles.items() if row.get("active", "").strip().lower() == "true"}
        expected_role_active = {item["controller_no"] for item in model_controllers}
        expected_role_active.add(excluded_sc)
        checks.add(
            "signal_roles.active_scope",
            role_active == expected_role_active,
            sorted(expected_role_active, key=_controller_sort_key),
            sorted(role_active, key=_controller_sort_key),
        )
        role_mismatches: list[str] = []
        for record in model_controllers + ([excluded_record] if excluded_record else []):
            number = record["controller_no"]
            row = roles.get(number, {})
            if row.get("supplyFile2", "").strip() != record["supply_file_2"]:
                role_mismatches.append(f"SC{number}:supplyFile2")
            raw_count = row.get("signal_head_count", "").strip()
            try:
                role_count = int(float(raw_count))
            except ValueError:
                role_count = -1
            if role_count != record["signal_head_reference_count"]:
                role_mismatches.append(f"SC{number}:signal_head_count")
        checks.add("signal_roles.network_alignment", not role_mismatches, [], role_mismatches)

    return {
        "path": str(network.resolve()),
        "network_version": root.get("version", ""),
        "vissim_version": root.get("vissimVersion", ""),
        "signal_controller_count": len(controllers),
        "signal_head_count": sum(head_refs.values()),
        "signal_head_reference_count_by_controller": dict(
            sorted(head_refs.items(), key=lambda item: _controller_sort_key(item[0]))
        ),
        "model_controllers": model_controllers,
        "resolved_signal_programs": signal_programs,
        "excluded_controller": excluded_record,
        "auxiliary_controllers": auxiliary,
        "unclassified_controllers": unclassified,
        "malformed_signal_head_references": malformed_head_refs,
    }


def _runtime_source_identity(
    report_path: Path,
    adapter: Path,
    verifier: Path,
    anchor: Path,
    python_executable: Path,
    checks: Checks,
) -> dict[str, Any]:
    report_artifact = artifact_evidence(report_path)
    if not report_path.is_file():
        checks.add("runtime_source.exists", False, True, False)
        return {"manifest": report_artifact, "selected": {}, "python": {}}
    checks.add("runtime_source.exists", True, True, True)
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        checks.add("runtime_source.json", False, "valid JSON object", f"{type(exc).__name__}: {exc}")
        return {"manifest": report_artifact, "selected": {}, "python": {}}
    if not isinstance(payload, Mapping):
        checks.add("runtime_source.json", False, "JSON object", type(payload).__name__)
        return {"manifest": report_artifact, "selected": {}, "python": {}}
    checks.add("runtime_source.json", True, "JSON object", "JSON object")
    checks.add("runtime_source.schema", payload.get("schema_version") == RUNTIME_SOURCE_SCHEMA, RUNTIME_SOURCE_SCHEMA, payload.get("schema_version"))
    checks.add("runtime_source.status", payload.get("status") == "PASS", "PASS", payload.get("status"))
    checks.add("runtime_source.reasons", payload.get("reasons") == [], [], payload.get("reasons"))
    checks.add("runtime_source.strict", payload.get("strict") is True, True, payload.get("strict"))
    checks.add(
        "runtime_source.expected_commit",
        payload.get("expected_snapshot_commit") == EXPECTED_NUMSIM_COMMIT,
        EXPECTED_NUMSIM_COMMIT,
        payload.get("expected_snapshot_commit"),
    )
    reported_checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
    reported_check_status = {
        str(item.get("id", "")): str(item.get("status", ""))
        for item in reported_checks
        if isinstance(item, Mapping)
    }
    for check_id in RUNTIME_SOURCE_TRUST_CHECKS:
        checks.add(
            f"runtime_source.required_check.{check_id}",
            reported_check_status.get(check_id) == "PASS",
            "PASS",
            reported_check_status.get(check_id, "MISSING"),
        )

    selected = payload.get("selected") if isinstance(payload.get("selected"), Mapping) else {}
    selected_root_text = str(selected.get("root", "")).strip()
    selected_root = Path(selected_root_text).resolve(strict=False) if selected_root_text else Path("__missing_runtime_source__").resolve()
    actual_tree = source_tree_identity(selected_root)
    reported_tree = str(selected.get("normalised_tree_sha256", ""))
    reported_count = selected.get("python_file_count")
    checks.add("runtime_source.selected_root", bool(selected_root_text) and selected_root.is_dir(), "existing selected root", selected_root_text)
    checks.add("runtime_source.selected_tree_hash", bool(reported_tree) and reported_tree == actual_tree["normalised_tree_sha256"], reported_tree, actual_tree["normalised_tree_sha256"])
    checks.add("runtime_source.selected_python_file_count", reported_count == actual_tree["python_file_count"], reported_count, actual_tree["python_file_count"])

    input_hashes = payload.get("input_hashes") if isinstance(payload.get("input_hashes"), Mapping) else {}
    adapter_hash = file_sha256(adapter)
    python_hash = file_sha256(python_executable)
    verifier_hash = file_sha256(verifier)
    anchor_hash = file_sha256(anchor)
    snapshot = selected_root / "SNAPSHOT.md"
    checks.add("runtime_source.adapter_hash", input_hashes.get("adapter_sha256") == adapter_hash and bool(adapter_hash), input_hashes.get("adapter_sha256"), adapter_hash)
    checks.add(
        "runtime_source.python_executable_hash",
        input_hashes.get("python_executable_sha256") == python_hash and bool(python_hash),
        input_hashes.get("python_executable_sha256"),
        python_hash,
    )
    checks.add(
        "runtime_source.snapshot_hash",
        input_hashes.get("selected_snapshot_sha256") == file_sha256(snapshot) and snapshot.is_file(),
        input_hashes.get("selected_snapshot_sha256"),
        file_sha256(snapshot),
    )
    command_version = payload.get("command_version") if isinstance(payload.get("command_version"), Mapping) else {}
    checks.add("runtime_source.verifier_hash", command_version.get("sha256") == verifier_hash and bool(verifier_hash), command_version.get("sha256"), verifier_hash)
    checks.add(
        "runtime_source.anchor_hash",
        input_hashes.get("upstream_tree_anchor_sha256") == anchor_hash and bool(anchor_hash),
        input_hashes.get("upstream_tree_anchor_sha256"),
        anchor_hash,
    )

    python_record = payload.get("python") if isinstance(payload.get("python"), Mapping) else {}
    reported_python = Path(str(python_record.get("executable", ""))).resolve(strict=False) if python_record.get("executable") else Path("__missing_python__").resolve()
    checks.add("runtime_source.python_executable_path", _same_path(reported_python, python_executable), str(python_executable), str(reported_python))
    checks.add("python.current_executable", _same_path(python_executable, Path(sys.executable)), str(Path(sys.executable).resolve()), str(python_executable))

    imports = payload.get("imports") if isinstance(payload.get("imports"), Mapping) else {}
    selected_imports = imports.get("selected") if isinstance(imports.get("selected"), Mapping) else {}
    import_root_text = str(selected_imports.get("adapter_default_root", "")).strip()
    import_root = Path(import_root_text).resolve(strict=False) if import_root_text else Path("__missing_import_root__").resolve()
    import_adapter_text = str(selected_imports.get("adapter_path", "")).strip()
    import_adapter = Path(import_adapter_text).resolve(strict=False) if import_adapter_text else Path("__missing_import_adapter__").resolve()
    checks.add("runtime_source.selected_import_root", _same_path(import_root, selected_root), str(selected_root), str(import_root))
    checks.add("runtime_source.imported_adapter_path", _same_path(import_adapter, adapter), str(adapter), str(import_adapter))
    checks.add("runtime_source.external_imports", selected_imports.get("external_modules") == [], [], selected_imports.get("external_modules"))

    selected_git = selected.get("git") if isinstance(selected.get("git"), Mapping) else {}
    return {
        "manifest": report_artifact,
        "schema_version": payload.get("schema_version"),
        "status": payload.get("status"),
        "strict": payload.get("strict"),
        "expected_snapshot_commit": payload.get("expected_snapshot_commit", ""),
        "selected_is_canonical": bool(payload.get("selected_is_canonical")),
        "trust_anchor": payload.get("trust_anchor") if isinstance(payload.get("trust_anchor"), Mapping) else {},
        "selected": {
            "root": str(selected_root),
            "snapshot_path": str(snapshot.resolve(strict=False)),
            "snapshot_sha256": file_sha256(snapshot),
            "snapshot_commit": selected.get("snapshot_commit", ""),
            "git_commit": selected_git.get("head_commit", ""),
            "reported_python_file_count": reported_count,
            "actual_python_file_count": actual_tree["python_file_count"],
            "reported_normalised_tree_sha256": reported_tree,
            "actual_normalised_tree_sha256": actual_tree["normalised_tree_sha256"],
            "imported_module_count": len(selected_imports.get("modules", {})) if isinstance(selected_imports.get("modules"), Mapping) else 0,
        },
        "python": {
            "path": str(python_executable),
            "sha256": python_hash,
            "version": sys.version,
            "reported_path": str(reported_python),
        },
    }


def _resolve_declared_path(repo: Path, value: str) -> Path:
    candidate = Path(value.replace("\\", os.sep).replace("/", os.sep))
    return candidate.resolve(strict=False) if candidate.is_absolute() else (repo / candidate).resolve(strict=False)


def _check_configuration_links(repo: Path, paths: Mapping[str, Path], checks: Checks) -> None:
    tuning = paths["tuning"]
    if tuning.is_file():
        try:
            payload = json.loads(tuning.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            checks.add("tuning.json", False, "valid JSON object", f"{type(exc).__name__}: {exc}")
        else:
            checks.add("tuning.json", isinstance(payload, Mapping), "JSON object", type(payload).__name__)
            if isinstance(payload, Mapping):
                for field, path_key in (("mapping_json", "control_mapping"), ("detector_mapping_json", "detector_mapping")):
                    declared = str(payload.get(field, "")).strip()
                    actual = paths[path_key]
                    checks.add(
                        f"tuning.{field}",
                        bool(declared) and _same_path(_resolve_declared_path(repo, declared), actual),
                        str(actual),
                        str(_resolve_declared_path(repo, declared)) if declared else "",
                    )

    generated_vbs = paths["generated_vbs"]
    if generated_vbs.is_file():
        try:
            text = generated_vbs.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            checks.add("generated_vbs.readable", False, "readable text", f"{type(exc).__name__}: {exc}")
        else:
            match = re.search(r'^\s*RW_DETECTOR_MAPPING_PATH\s*=\s*"([^"]+)"', text, re.MULTILINE | re.IGNORECASE)
            declared = match.group(1).strip() if match else ""
            checks.add(
                "generated_vbs.detector_mapping",
                bool(declared) and _same_path(_resolve_declared_path(repo, declared), paths["detector_mapping"]),
                str(paths["detector_mapping"]),
                str(_resolve_declared_path(repo, declared)) if declared else "",
            )


def _fingerprint_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
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


def build_manifest(
    repo: Path,
    runtime_source: Path,
    *,
    path_overrides: Mapping[str, str | Path] | None = None,
    signal_dir: str | Path | None = None,
    python_executable: str | Path | None = None,
    expected_model_count: int = EXPECTED_MODEL_SC_COUNT,
    expected_resolved_sig_count: int = EXPECTED_RESOLVED_SIG_COUNT,
    expected_auxiliary_count: int = EXPECTED_AUXILIARY_SC_COUNT,
    excluded_sc: str = DEFAULT_EXCLUDED_SC,
) -> dict[str, Any]:
    repo = repo.resolve()
    overrides = dict(path_overrides or {})
    paths = {
        key: _resolve_repo_path(repo, overrides.get(key), default)
        for key, default in DEFAULT_PATHS.items()
    }
    if overrides.get("demand_profile"):
        paths["demand_profile"] = _resolve_repo_path(
            repo, overrides["demand_profile"], str(overrides["demand_profile"])
        )
    runtime_source = _resolve_repo_path(repo, runtime_source, str(runtime_source))
    python_path = Path(python_executable or sys.executable).resolve(strict=False)
    signal_directory = _resolve_repo_path(repo, signal_dir, str(paths["network"].parent))
    checks = Checks()

    artifacts = {name: artifact_evidence(path) for name, path in paths.items()}
    artifacts["runtime_source"] = artifact_evidence(runtime_source)
    artifacts["python_executable"] = artifact_evidence(python_path)
    for name, record in artifacts.items():
        checks.add(f"artifact.{name}.exists", bool(record["exists"]), True, record["exists"])
        checks.add(f"artifact.{name}.sha256", bool(record["sha256"]), "non-empty SHA-256", record["sha256"])

    network = _parse_network(
        paths["network"],
        signal_directory,
        paths["signal_roles"],
        checks,
        expected_model_count=expected_model_count,
        expected_resolved_sig_count=expected_resolved_sig_count,
        expected_auxiliary_count=expected_auxiliary_count,
        excluded_sc=str(excluded_sc),
    )
    _check_configuration_links(repo, paths, checks)
    runtime_identity = _runtime_source_identity(
        runtime_source,
        paths["adapter"],
        paths["runtime_source_verifier"],
        paths["runtime_source_anchor"],
        python_path,
        checks,
    )

    input_hashes = {name: str(record["sha256"]) for name, record in sorted(artifacts.items())}
    for record in network.get("resolved_signal_programs", []):
        input_hashes[f"signal_program.SC{record['controller_no']}"] = str(record["sha256"])
    input_hashes = dict(sorted(input_hashes.items()))
    command_path = Path(__file__).resolve()
    status = "PASS" if not checks.reasons else "FAIL"
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "input_hashes": input_hashes,
        "command_version": {
            "command": "scripts/build_preflight_manifest.py",
            "version": SCHEMA_VERSION,
            "sha256": file_sha256(command_path),
        },
        "status": status,
        "reasons": checks.reasons,
        "sample_dimensions": {
            "model_signal_controllers": len(network.get("model_controllers", [])),
            "resolved_signal_programs": sum(
                bool(item.get("exists") and item.get("sha256"))
                for item in network.get("resolved_signal_programs", [])
            ),
            "unique_resolved_signal_programs": len(
                {os.path.normcase(str(item.get("path", ""))) for item in network.get("resolved_signal_programs", []) if item.get("exists")}
            ),
            "excluded_signal_controllers": 1 if network.get("excluded_controller") else 0,
            "auxiliary_signal_controllers": len(network.get("auxiliary_controllers", [])),
            "signal_heads": int(network.get("signal_head_count", 0)),
            "hashed_artifacts": sum(bool(value) for value in input_hashes.values()),
            "runtime_python_files": runtime_identity.get("selected", {}).get("actual_python_file_count", 0),
        },
        "units": {
            "controller_count": "signal controller",
            "signal_program_count": "resolved .sig file",
            "signal_head_count": "signal head reference",
            "size_bytes": "byte",
            "sha256": "SHA-256 hex digest of raw bytes unless explicitly named normalised",
            "normalised_tree_sha256": "SHA-256 over relative Python paths and LF-normalised file hashes",
        },
        "downstream_consumers": [
            "S0R-3 baseline snapshot",
            "scripts/run_plant_fidelity_matrix.ps1",
            "scripts/audit_plant_fidelity.py",
            "paired VISSIM future campaign",
            "plant fidelity certification release",
        ],
        "repo": str(repo),
        "artifacts": artifacts,
        "network": network,
        "runtime_source_identity": runtime_identity,
        "checks": checks.items,
    }
    fingerprint_payload = _fingerprint_payload(manifest)
    manifest["fingerprint"] = {
        "algorithm": "sha256",
        "canonicalisation": "UTF-8 JSON, sorted keys, compact separators, ensure_ascii",
        "sha256": _sha256(
            json.dumps(
                fingerprint_payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ),
    }
    manifest["fingerprint_sha256"] = manifest["fingerprint"]["sha256"]
    return manifest


def write_manifest_atomic(path: Path, manifest: Mapping[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the deterministic strict plant preflight manifest.")
    parser.add_argument("--repo", required=True, help="VISSIM repository root")
    parser.add_argument("--runtime-source", required=True, help="runtime-source-v2.1 JSON from S0R-1")
    parser.add_argument("--out", required=True, help="output preflight-v3 JSON")
    parser.add_argument("--strict", action="store_true", help="return nonzero when any preflight check fails")
    parser.add_argument("--signal-dir", default="", help="directory used to resolve #data# SIG references")
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--expected-model-sc-count", type=int, default=EXPECTED_MODEL_SC_COUNT)
    parser.add_argument("--expected-resolved-sig-count", type=int, default=EXPECTED_RESOLVED_SIG_COUNT)
    parser.add_argument("--expected-auxiliary-sc-count", type=int, default=EXPECTED_AUXILIARY_SC_COUNT)
    parser.add_argument("--excluded-sc", default=DEFAULT_EXCLUDED_SC)
    for key, default in DEFAULT_PATHS.items():
        parser.add_argument(
            "--" + key.replace("_", "-"),
            default="",
            help=f"override {key} (default: {default})",
        )
    parser.add_argument(
        "--demand-profile",
        default="",
        help="optional demand_profile configuration input",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    overrides = {
        key: getattr(args, key)
        for key in DEFAULT_PATHS
        if str(getattr(args, key, "")).strip()
    }
    if str(args.demand_profile).strip():
        overrides["demand_profile"] = args.demand_profile
    manifest = build_manifest(
        Path(args.repo),
        Path(args.runtime_source),
        path_overrides=overrides,
        signal_dir=args.signal_dir or None,
        python_executable=args.python_executable,
        expected_model_count=args.expected_model_sc_count,
        expected_resolved_sig_count=args.expected_resolved_sig_count,
        expected_auxiliary_count=args.expected_auxiliary_sc_count,
        excluded_sc=args.excluded_sc,
    )
    out = Path(args.out)
    write_manifest_atomic(out, manifest)
    print(
        json.dumps(
            {
                "fingerprint": manifest["fingerprint"]["sha256"],
                "out": str(out.resolve()),
                "status": manifest["status"],
            },
            sort_keys=True,
        )
    )
    return 2 if args.strict and manifest["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
