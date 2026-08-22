from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
PLANT_PACKAGE_ROOT = WORKSPACE_ROOT / "plant" / "src"
if str(PLANT_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PLANT_PACKAGE_ROOT))
from vissim_strict import (
    ProjectionReferenceValidationError,
    load_validated_approved_topology,
    load_bounded_json_snapshot,
    project_vehicle_records,
    publish_projection_outputs,
    validate_physical_projection_reference,
    validate_projection_output_paths,
    validate_run_manifest,
)
from vissim_strict.physical_projection import (
    file_sha256 as strict_file_sha256,
    freeze_json,
    json_type_strict_equal,
    normalize_vehicle_records,
    thaw_json,
)
from vissim_strict.physical_projection_reference import MAX_STATE_BYTES
# N4-5: SG 단위 액추에이션 계획. 순수 함수만 들어 있어 import 부작용이 없다.
from evaluation.controllers import action_csv_schema
from evaluation.controllers import offset_promotion
from evaluation.controllers import plant_cycle
from evaluation.controllers import signal_group_plan
from vissim_strict.run_evidence import (
    MAX_APPROVAL_BYTES,
    MAX_RUN_MANIFEST_BYTES,
    MAX_TOPOLOGY_BYTES,
    resolve_canonical_workspace_destination,
    resolve_canonical_workspace_file,
)
# 2026-07-31: 기본 모델 저장소를 NUMSIM_REPO_ROOT env → NumSim-mine(flagship-ms-adapt-clean,
# HEAD 7f10393) 순서로 결정한다. 과거 경로 이력(재현용):
#   - "C:/Users/TRLAB/Desktop/찐찐막/Numerical-Sim": 비-git 스냅샷(default.yaml nu_cong=65/
#     capacity_drop=false). nu_cong 격리 재현의 A/B 기준으로만 --repo-root로 명시 지정.
#   - "C:/Users/TRLAB/Desktop/찐찐막/Numerical-Sim-git": GitHub HEAD 0e07c1c 추적 클론
#     (2026-06-29 audit follow-up). 이 머신에는 없음.
_BUNDLED_NUMSIM_ROOT = WORKSPACE_ROOT / "vendor" / "NumSim-mine"
DEFAULT_REPO_ROOT = Path(
    os.environ.get("NUMSIM_REPO_ROOT")
    or (_BUNDLED_NUMSIM_ROOT if _BUNDLED_NUMSIM_ROOT.is_dir() else WORKSPACE_ROOT.parent / "NumSim-mine")
)
DEFAULT_MAPPING = WORKSPACE_ROOT / "evaluation/vsl_install/vsl_segment_mapping_8seg.json"
DEFAULT_CALIBRATION = WORKSPACE_ROOT / "evaluation/calibration/vissim_network_calibration_v2_8seg_20260714.json"
DEFAULT_DETECTOR_MAPPING = WORKSPACE_ROOT / "evaluation/detector_install/detector_local_mapping.json"
LOCAL_OBSERVATION_INTERNAL_STORAGE_FRACTION = 0.35
LOCAL_OBSERVATION_OFFRAMP_STORAGE_FRACTION = 0.50
# 2026-08-15: 결정마다 상태를 다시 지을 때 release 스케줄을 plant 가 짓게 하는 warm-up 길이.
# 0 이면 꺼진다(`RW_WARMSTART_SEC` 로 덮어쓴다). 자세한 근거는 warm_start_release_buffers.
#
# 실런 A/B 3쌍(시드 13, 1800 s, 제어창 [900,1800])에서 전부 개선이라 기본으로 켠다.
#   demand 0.75  ΔJ -7.934 veh·h (-1.37%)
#   demand 1.00  ΔJ -7.468 veh·h (-0.94%)
#   demand 1.25  ΔJ -4.684 veh·h (-0.45%)
# eps_J_vissim 이 1e-6 veh·h 라 가장 작은 -4.684 도 재료성이 460만 배 여유로 확정된다.
# 혼잡할수록 효과가 주는 것은 저류가 차 있을수록 빈 버퍼 왜곡이 작아지기 때문이다.
DEFAULT_WARMSTART_SEC = 900.0

# 생산 저류 용량 측정 근거(jam 168.18). 두 곳이 쓴다.
#   1) execution_fingerprint_sha256 의 증거 목록 - 여기가 낡으면 런이 자기가 쓰지도 않은
#      격자를 썼다고 기록한다(2026-08-16 에 _ovr_20260814 에서 옮겼다).
#   2) `_storage_effective_lanes` 의 차로수 유도.
# 런타임 용량 자체는 tuning config 인라인에서 온다 - 이 파일은 그 값의 출처 증거다.
STORAGE_CAPACITY_EVIDENCE_JSON = WORKSPACE_ROOT / "outputs" / "urban_storage_capacity_jam168_20260815.json"


def _b1a_existing_path(path_text: str) -> Path:
    """Resolve one canonical B1a CLI file below the checked-out workspace."""

    candidate = Path(path_text)
    if candidate.is_absolute():
        candidate = candidate.resolve(strict=True)
        relative = candidate.relative_to(WORKSPACE_ROOT.resolve(strict=True)).as_posix()
    else:
        relative = path_text
    return resolve_canonical_workspace_file(WORKSPACE_ROOT, relative)


def _b1a_destination_path(path_text: str) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        candidate = candidate.resolve(strict=False)
        relative = candidate.relative_to(WORKSPACE_ROOT.resolve(strict=True)).as_posix()
    else:
        relative = path_text
    return resolve_canonical_workspace_destination(WORKSPACE_ROOT, relative)


def _validate_b1a_adapter_source(manifest) -> None:
    expected = manifest.resolved_paths["producer_sources.adapter"]
    actual = Path(__file__).resolve(strict=True)
    if expected != actual or strict_file_sha256(actual) != manifest.artifact["producer_sources"]["adapter"]["file_sha256"]:
        raise ProjectionReferenceValidationError(["adapter executed-source binding mismatch"])


def _validate_b1a_projection_inputs(
    *,
    run_manifest_path: Path,
    topology_path: Path,
    state_path: Path,
):
    manifest_snapshot = load_bounded_json_snapshot(
        run_manifest_path, max_bytes=MAX_RUN_MANIFEST_BYTES
    )
    manifest = validate_run_manifest(
        manifest_snapshot.value, workspace_root=WORKSPACE_ROOT
    )
    _validate_b1a_adapter_source(manifest)
    approved = manifest.artifact["approved_topology"]
    expected_topology = manifest.resolved_paths["approved_topology.topology_path"]
    approved_topology = load_validated_approved_topology(
        manifest, workspace_root=WORKSPACE_ROOT
    )
    if (
        topology_path != expected_topology
        or topology_path != approved_topology.topology_snapshot.path
        or approved_topology.topology_snapshot.file_sha256
        != approved["topology_file_sha256"]
    ):
        raise ProjectionReferenceValidationError(["caller topology differs from immutable approved topology"])
    state_snapshot = load_bounded_json_snapshot(
        state_path, max_bytes=MAX_STATE_BYTES
    )
    state = state_snapshot.value
    run_id = manifest.artifact["run_id"]
    sim_sec = state.get("sim_sec") if isinstance(state, Mapping) else None
    if type(sim_sec) is not float or not math.isfinite(sim_sec) or sim_sec < 0.0:
        raise ProjectionReferenceValidationError(
            ["state sim_sec must be a finite nonnegative JSON double"]
        )
    manifest = validate_run_manifest(
        manifest_snapshot.value,
        workspace_root=WORKSPACE_ROOT,
        expected_run_id=run_id,
        capture_time=sim_sec,
    )
    provenance = state.get("run_provenance") if isinstance(state, Mapping) else None
    expected_provenance = {
        "run_id": run_id,
        "manifest_path": run_manifest_path.relative_to(WORKSPACE_ROOT).as_posix(),
        "manifest_sha256": manifest_snapshot.file_sha256,
    }
    if not isinstance(provenance, Mapping) or not json_type_strict_equal(
        provenance, expected_provenance
    ):
        raise ProjectionReferenceValidationError(["state/run manifest provenance mismatch"])
    return manifest_snapshot, manifest, approved_topology, state_snapshot


_PROJECTION_VALUE_OPTIONS = (
    "--state-json",
    "--run-manifest",
    "--approved-topology",
    "--out-projection-sidecar",
    "--out-projection-reference",
)
_PROJECTION_OPTIONS = ("--projection-only", *_PROJECTION_VALUE_OPTIONS)


def _parser_accepts_split_value(
    parser: argparse.ArgumentParser, token: str
) -> bool:
    """Use argparse's own option classifier for required split values."""

    return token != "--" and parser._parse_optional(token) is None


def _preparse_projection_roles(
    argv: Sequence[str], parser: argparse.ArgumentParser
) -> dict[str, Any]:
    """Collect projection roles without enforcing unrelated argparse choices."""

    values: dict[str, list[str | None]] = {
        option: [] for option in _PROJECTION_VALUE_OPTIONS
    }
    rejected_role_values: list[str] = []
    projection_only = False
    index = 0
    while index < len(argv):
        token = str(argv[index])
        if token == "--":
            break
        if token == "--projection-only":
            projection_only = True
        matched = False
        for option in _PROJECTION_VALUE_OPTIONS:
            if token == option:
                next_index = index + 1
                value = None
                if next_index < len(argv) and _parser_accepts_split_value(
                    parser, str(argv[next_index])
                ):
                    value = str(argv[next_index])
                    index = next_index
                values[option].append(value)
                matched = True
                break
            prefix = option + "="
            if token.startswith(prefix):
                value = token[len(prefix):]
                values[option].append(value or None)
                matched = True
                break
        if not matched and token.startswith("--"):
            option_text, separator, inline_value = token.partition("=")
            if option_text not in _PROJECTION_OPTIONS and any(
                option.startswith(option_text) for option in _PROJECTION_OPTIONS
            ):
                value = inline_value if separator else None
                next_index = index + 1
                if (
                    value is None
                    and next_index < len(argv)
                    and _parser_accepts_split_value(
                        parser, str(argv[next_index])
                    )
                ):
                    value = str(argv[next_index])
                    index = next_index
                if value:
                    rejected_role_values.append(value)
                matched = True
        index += 1
        if matched:
            continue
    return {
        "projection_only": projection_only,
        "values": values,
        "rejected_role_values": rejected_role_values,
    }


def _last_projection_role(
    preparse: Mapping[str, Any], option: str
) -> str:
    values = preparse.get("values", {}).get(option, [])
    if not isinstance(values, list) or not values:
        return ""
    value = values[-1]
    return value if isinstance(value, str) else ""


def _lexical_workspace_role(path_text: str) -> Path:
    """Preserve authored spelling while retaining existing-file identity."""

    if not isinstance(path_text, str) or not path_text:
        raise ValueError("declared projection role path is empty")
    candidate = Path(path_text)
    return candidate if candidate.is_absolute() else WORKSPACE_ROOT / candidate


def _declared_manifest_role_values(manifest_value: Any) -> dict[str, str]:
    """Collect authored role strings before exact path resolution can reject one."""

    if not isinstance(manifest_value, Mapping):
        return {}
    declared: dict[str, Any] = {}
    approved = manifest_value.get("approved_topology")
    if isinstance(approved, Mapping):
        declared["approval"] = approved.get("approving_manifest_path")
        declared["topology_manifest"] = approved.get("topology_path")
    preflight = manifest_value.get("preflight")
    if isinstance(preflight, Mapping):
        declared["preflight"] = preflight.get("path")
    for container_name in ("producer_sources",):
        container = manifest_value.get(container_name)
        if isinstance(container, Mapping):
            for role, binding in container.items():
                if isinstance(binding, Mapping):
                    declared[f"{container_name}.{role}"] = binding.get("path")
    configuration = manifest_value.get("configuration")
    inputs = configuration.get("inputs") if isinstance(configuration, Mapping) else None
    if isinstance(inputs, Mapping):
        for role, binding in inputs.items():
            if isinstance(binding, Mapping) and binding.get("path") is not None:
                declared[f"configuration.inputs.{role}"] = binding.get("path")
    policy = manifest_value.get("supported_version_policy")
    if isinstance(policy, Mapping):
        declared["supported_version_policy"] = policy.get("path")
    collected: dict[str, str] = {}
    for role, value in declared.items():
        if isinstance(value, str) and value:
            collected[role] = value
    return collected


def _prepare_projection_output_roles(
    args,
    preparse: Mapping[str, Any],
):
    """Authorize the complete immutable universe, then invalidate the reference."""

    if not args.out_projection_reference:
        return None, None, {}, False
    reference_path = _b1a_destination_path(args.out_projection_reference)
    immutable_paths: dict[str, Path] = {
        "adapter_source": Path(__file__).resolve(strict=True),
    }
    effective_roles = (
        ("--state-json", "state_json", "state_effective", True),
        ("--run-manifest", "run_manifest", "run_manifest_effective", True),
        (
            "--approved-topology",
            "approved_topology",
            "topology_effective",
            True,
        ),
        (
            "--out-projection-sidecar",
            "out_projection_sidecar",
            "sidecar_effective",
            False,
        ),
        (
            "--out-projection-reference",
            "out_projection_reference",
            "reference_effective",
            False,
        ),
    )
    for option, attribute, role, is_input in effective_roles:
        value = getattr(args, attribute, "")
        if value and is_input:
            immutable_paths[role] = _lexical_workspace_role(value)
        if value != _last_projection_role(preparse, option):
            raise ProjectionReferenceValidationError(
                [f"projection parser/preparse role mismatch: {option}"]
            )
    if bool(getattr(args, "projection_only", True)) != bool(
        preparse.get("projection_only")
    ):
        raise ProjectionReferenceValidationError(
            ["projection parser/preparse role mismatch: --projection-only"]
        )
    raw_values = preparse.get("values", {})
    rejected_role_values = preparse.get("rejected_role_values", [])
    if not isinstance(rejected_role_values, list):
        raise ProjectionReferenceValidationError(
            ["projection preparse rejected-role set is invalid"]
        )
    for index, value in enumerate(rejected_role_values):
        if isinstance(value, str) and value:
            immutable_paths[f"rejected_role[{index}]"] = (
                _lexical_workspace_role(value)
            )
    for option, role in (
        ("--state-json", "state_cli"),
        ("--run-manifest", "run_manifest_cli"),
        ("--approved-topology", "topology_cli"),
    ):
        values = raw_values.get(option, []) if isinstance(raw_values, Mapping) else []
        if not isinstance(values, list):
            raise ProjectionReferenceValidationError(
                [f"projection preparse role is invalid: {option}"]
            )
        for index, value in enumerate(values):
            if isinstance(value, str) and value:
                immutable_paths[f"{role}[{index}]"] = _lexical_workspace_role(value)

    sidecar_values = (
        raw_values.get("--out-projection-sidecar", [])
        if isinstance(raw_values, Mapping)
        else []
    )
    if not isinstance(sidecar_values, list):
        raise ProjectionReferenceValidationError(
            ["projection sidecar preparse role is invalid"]
        )
    for index, value in enumerate(sidecar_values[:-1]):
        if isinstance(value, str) and value:
            immutable_paths[f"superseded_sidecar[{index}]"] = (
                _lexical_workspace_role(value)
            )
    sidecar_candidate = (
        _lexical_workspace_role(args.out_projection_sidecar)
        if args.out_projection_sidecar
        else None
    )

    reference_values = (
        raw_values.get("--out-projection-reference", [])
        if isinstance(raw_values, Mapping)
        else []
    )
    if not isinstance(reference_values, list):
        raise ProjectionReferenceValidationError(
            ["projection reference preparse role is invalid"]
        )
    for index, value in enumerate(reference_values[:-1]):
        if isinstance(value, str) and value != args.out_projection_reference:
            immutable_paths[f"superseded_reference[{index}]"] = (
                _lexical_workspace_role(value)
            )

    manifest_text = args.run_manifest or _last_projection_role(
        preparse, "--run-manifest"
    )
    if not manifest_text:
        raise ProjectionReferenceValidationError(
            ["run manifest is required to authorize projection outputs"]
        )
    manifest_candidate = _lexical_workspace_role(manifest_text)
    manifest_snapshot = load_bounded_json_snapshot(
        manifest_candidate, max_bytes=MAX_RUN_MANIFEST_BYTES
    )
    immutable_paths["run_manifest_snapshot"] = manifest_snapshot.path
    declared_manifest_roles = _declared_manifest_role_values(
        manifest_snapshot.value
    )
    for role, value in declared_manifest_roles.items():
        immutable_paths[f"manifest.{role}"] = _lexical_workspace_role(value)

    manifest_approved = (
        manifest_snapshot.value.get("approved_topology")
        if isinstance(manifest_snapshot.value, Mapping)
        else None
    )
    if not isinstance(manifest_approved, Mapping):
        raise ProjectionReferenceValidationError(
            ["run manifest approval binding is unavailable"]
        )
    approval_text = manifest_approved.get("approving_manifest_path")
    approval_hash = manifest_approved.get("approving_manifest_sha256")
    if not isinstance(approval_text, str) or not approval_text:
        raise ProjectionReferenceValidationError(
            ["run manifest approval path is invalid"]
        )
    approval_candidate = _lexical_workspace_role(approval_text)
    immutable_paths["approval_declared"] = approval_candidate
    approval_snapshot = load_bounded_json_snapshot(
        approval_candidate, max_bytes=MAX_APPROVAL_BYTES
    )
    if approval_snapshot.file_sha256 != approval_hash:
        raise ProjectionReferenceValidationError(
            ["run manifest approval snapshot hash mismatch"]
        )
    immutable_paths["approval_snapshot"] = approval_snapshot.path

    source_inputs = (
        approval_snapshot.value.get("source_inputs")
        if isinstance(approval_snapshot.value, Mapping)
        else None
    )
    lane_graph_binding = (
        source_inputs.get("lane_graph")
        if isinstance(source_inputs, Mapping)
        else None
    )
    if not isinstance(lane_graph_binding, Mapping) or set(lane_graph_binding) != {
        "path", "file_sha256", "semantic_sha256"
    }:
        raise ProjectionReferenceValidationError(
            ["approval lane graph binding is invalid"]
        )
    lane_graph_text = lane_graph_binding.get("path")
    if not isinstance(lane_graph_text, str) or not lane_graph_text:
        raise ProjectionReferenceValidationError(
            ["approval lane graph path is invalid"]
        )
    lane_graph_candidate = _lexical_workspace_role(lane_graph_text)
    immutable_paths["lane_graph_declared"] = lane_graph_candidate
    lane_graph_snapshot = load_bounded_json_snapshot(
        lane_graph_candidate, max_bytes=MAX_TOPOLOGY_BYTES
    )
    if lane_graph_snapshot.file_sha256 != lane_graph_binding.get("file_sha256"):
        raise ProjectionReferenceValidationError(
            ["approval lane graph snapshot hash mismatch"]
        )
    immutable_paths["lane_graph_snapshot"] = lane_graph_snapshot.path

    manifest = validate_run_manifest(
        manifest_snapshot.value, workspace_root=WORKSPACE_ROOT
    )
    approved_topology = load_validated_approved_topology(
        manifest, workspace_root=WORKSPACE_ROOT
    )
    if (
        approval_snapshot.data != approved_topology.approval_snapshot.data
        or approval_snapshot.file_sha256
        != approved_topology.approval_snapshot.file_sha256
        or lane_graph_snapshot.data != approved_topology.lane_graph_snapshot.data
        or lane_graph_snapshot.file_sha256
        != approved_topology.lane_graph_snapshot.file_sha256
    ):
        raise ProjectionReferenceValidationError(
            ["projection authorization companions changed during validation"]
        )
    immutable_paths.update({
        str(role): path for role, path in manifest.resolved_paths.items()
    })
    immutable_paths.update({
        "approval": approved_topology.approval_snapshot.path,
        "lane_graph": approved_topology.lane_graph_snapshot.path,
        "topology": approved_topology.topology_snapshot.path,
    })
    output_authorization_error = None
    try:
        validate_projection_output_paths(
            sidecar_candidate,
            reference_path,
            immutable_paths=immutable_paths,
        )
    except ProjectionReferenceValidationError as exc:
        output_authorization_error = exc
    validate_projection_output_paths(
        None,
        reference_path,
        immutable_paths=immutable_paths,
    )
    reference_path.unlink(missing_ok=True)
    if output_authorization_error is not None:
        raise output_authorization_error
    sidecar_path = (
        _b1a_destination_path(args.out_projection_sidecar)
        if args.out_projection_sidecar
        else None
    )
    return sidecar_path, reference_path, immutable_paths, True


def _invalidate_projection_reference_after_parser_failure(
    preparse: Mapping[str, Any],
) -> None:
    if not bool(preparse.get("projection_only")):
        return
    reference_text = _last_projection_role(
        preparse, "--out-projection-reference"
    )
    if not reference_text:
        return

    try:
        args = argparse.Namespace(
            projection_only=True,
            state_json=_last_projection_role(preparse, "--state-json"),
            run_manifest=_last_projection_role(preparse, "--run-manifest"),
            approved_topology=_last_projection_role(
                preparse, "--approved-topology"
            ),
            out_projection_sidecar=_last_projection_role(
                preparse, "--out-projection-sidecar"
            ),
            out_projection_reference=reference_text,
        )
        _prepare_projection_output_roles(args, preparse)
    except BaseException:
        # Parser failure remains authoritative; unsafe or incomplete role
        # authorization deliberately leaves every file untouched.
        return


def _projection_provenance(validated) -> dict[str, Any]:
    reference = validated.artifact
    return {
        "schema_version": "physical-projection-action-provenance-v2.1",
        "qualification": thaw_json(reference["qualification"]),
        "run_id": reference["run_id"],
        "sim_sec": reference["sim_sec"],
        "run_manifest_path": validated.run_manifest_snapshot.path.relative_to(WORKSPACE_ROOT).as_posix(),
        "run_manifest_sha256": reference["run_manifest_sha256"],
        "state_path": reference["state_path"],
        "state_file_sha256": reference["state_file_sha256"],
        "topology_path": validated.topology_path.relative_to(WORKSPACE_ROOT).as_posix(),
        "topology_file_sha256": reference["topology_file_sha256"],
        "topology_semantic_sha256": reference["topology_semantic_sha256"],
        "projection_sidecar_path": reference["projection_sidecar_path"],
        "projection_sidecar_file_sha256": reference["projection_sidecar_file_sha256"],
        "projection_sidecar_semantic_sha256": reference["projection_sidecar_semantic_sha256"],
        "projection_reference_path": validated.reference_path.relative_to(WORKSPACE_ROOT).as_posix(),
        "projection_reference_file_sha256": validated.reference_file_sha256,
        "projection_reference_semantic_sha256": reference["semantic_sha256"],
        "normalized_projection_sha256": reference["normalized_projection_sha256"],
        "record_count": reference["record_count"],
        "assigned_count": reference["assigned_count"],
        "stock_total": reference["stock_total"],
        "global_residual": reference["global_residual"],
    }


def _b1a_state_construction_input(validated) -> Mapping[str, Any]:
    """Create the required B1a observation boundary without B1b dynamics."""

    state = thaw_json(validated.state)
    ledger = thaw_json(validated.sidecar)
    records = {
        record["veh_no"]: record
        for record in state["vehicle_records"]["records"]
    }
    link_counts: dict[str, int] = {}
    link_speed_totals: dict[str, float] = {}
    link_stopped: dict[str, int] = {}
    queue_tails: dict[str, float] = {}
    for assignment in ledger["vehicle_assignments"]:
        record = records[assignment["veh_no"]]
        link = str(assignment["source_link_no"])
        link_counts[link] = link_counts.get(link, 0) + 1
        link_speed_totals[link] = link_speed_totals.get(link, 0.0) + record["speed_kph"]
        link_stopped[link] = link_stopped.get(link, 0) + int(record["stopped"])
        queue_tails[link] = min(
            queue_tails.get(link, record["position_m"]), record["position_m"]
        )
    link_speeds = {
        link: link_speed_totals[link] / count
        for link, count in link_counts.items()
    }
    return freeze_json({
        "provenance": _projection_provenance(validated),
        "ledger": ledger,
        "local_observation": {
            "link_counts": link_counts,
            "link_speeds_kph": link_speeds,
            "link_stopped_counts": link_stopped,
            "link_queue_tail_pos_m": queue_tails,
        },
    })


def _state_json_from_b1a_projection(validated) -> tuple[dict[str, Any], Mapping[str, Any]]:
    projection_input = _b1a_state_construction_input(validated)
    state_json = thaw_json(validated.state)
    state_json["local_observation"] = thaw_json(
        projection_input["local_observation"]
    )
    state_json["physical_projection"] = thaw_json(projection_input["ledger"])
    return state_json, projection_input


# 8-seg plant (2026-07-14): one ramp junction per segment, indices in travel
# direction. Matches the Numerical-Sim feature/segment-agents-13p default.yaml
# geometry (segments 8, off 2/4, merge 3/5); see the index-override comment in
# build_config for the westbound swap.
SEGMENT_TO_MODEL = {
    "EB_S0_W_EXT_ENTRY": ("FW_E", 0),
    "EB_S1_W_APPROACH": ("FW_E", 1),
    "EB_S2_D_DIVERGE": ("FW_E", 2),
    "EB_S3_D_MERGE": ("FW_E", 3),
    "EB_S4_F_DIVERGE": ("FW_E", 4),
    "EB_S5_F_MERGE": ("FW_E", 5),
    "EB_S6_POST_F": ("FW_E", 6),
    "EB_S7_E_EXIT": ("FW_E", 7),
    "WB_S0_E_EXT_ENTRY": ("FW_W", 0),
    "WB_S1_E_APPROACH": ("FW_W", 1),
    "WB_S2_F_DIVERGE": ("FW_W", 2),
    "WB_S3_F_MERGE": ("FW_W", 3),
    "WB_S4_D_DIVERGE": ("FW_W", 4),
    "WB_S5_D_MERGE": ("FW_W", 5),
    "WB_S6_POST_D": ("FW_W", 6),
    "WB_S7_W_EXIT": ("FW_W", 7),
}


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def nearest(value: float, candidates: list[float]) -> float:
    return float(min(candidates, key=lambda x: abs(float(x) - float(value))))


def deep_update(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = deep_update(dict(out[key]), value)
        else:
            out[key] = value
    return out


def load_optional_json(path_text: str) -> dict[str, Any]:
    if not path_text:
        return {}
    path = Path(path_text)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    extends = data.get("extends", "")
    if not extends:
        return data
    parent_path = Path(str(extends))
    if not parent_path.is_absolute():
        parent_path = path.parent / parent_path
    parent = load_optional_json(str(parent_path))
    child = dict(data)
    child.pop("extends", None)
    return deep_update(parent, child)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _calibration_child(calibration: Mapping[str, Any], section: str, child: str) -> Mapping[str, Any]:
    parent = _mapping(calibration.get(section))
    nested = _mapping(parent.get(child))
    if nested:
        return nested
    return _mapping(calibration.get(child))


def _segment_length_profile_km(calibration: Mapping[str, Any]) -> dict[str, list[float]]:
    physical = _mapping(calibration.get("physical_inventory"))
    raw = _mapping(physical.get("freeway_segment_length_profile_km"))
    profile: dict[str, list[float]] = {}
    for link, values in raw.items():
        lengths: list[float] = []
        if isinstance(values, list):
            lengths = [max(1.0e-6, _as_float(value)) for value in values]
        elif isinstance(values, Mapping):
            for key in sorted(values, key=lambda item: int(item) if str(item).isdigit() else str(item)):
                lengths.append(max(1.0e-6, _as_float(values[key])))
        if lengths:
            profile[str(link)] = lengths
    return profile


def _freeway_segment_lengths_km(cfg, link: str, count: int) -> list[float]:
    net = cfg.network
    profile = getattr(net, "freeway_segment_length_profile_km", {})
    values: list[float] = []
    if isinstance(profile, Mapping):
        raw = profile.get(str(link), profile.get(link, []))
        if isinstance(raw, list):
            values = [max(1.0e-6, _as_float(value)) for value in raw]
    if len(values) >= count:
        return values[:count]
    base = max(1.0e-6, float(getattr(net, "freeway_segment_length_km", 0.58)))
    if values:
        values = values + [base] * max(0, count - len(values))
        return values[:count]
    return [base] * max(0, count)


def _freeway_vehicle_count_by_link(state, cfg) -> dict[str, list[float]]:
    """Return segment vehicle counts using Vissim-specific length profiles when available."""
    net = cfg.network
    state.ensure_freeway_lane_profile(net)
    counts: dict[str, list[float]] = {}
    lane_profile = getattr(state, "freeway_lanes", {})
    for link in net.freeway_links:
        key = str(link)
        densities = [float(value) for value in state.freeway_density.get(key, [])]
        lengths = _freeway_segment_lengths_km(cfg, key, len(densities))
        raw_lanes = lane_profile.get(key, []) if isinstance(lane_profile, Mapping) else []
        lanes = [
            max(1.0, _as_float(raw_lanes[i], getattr(net, "freeway_lanes", 2)))
            if i < len(raw_lanes)
            else max(1.0, float(getattr(net, "freeway_lanes", 2)))
            for i in range(len(densities))
        ]
        counts[key] = [
            max(0.0, rho) * lengths[i] * lanes[i]
            for i, rho in enumerate(densities)
        ]
    return counts


def _vsl_rollout_tuning(tuning: Mapping[str, Any]) -> Mapping[str, Any]:
    adapter = _mapping(tuning.get("adapter"))
    return _mapping(adapter.get("vsl_metanet_rollout"))


def _is_enabled(settings: Mapping[str, Any]) -> bool:
    return str(settings.get("enabled", False)).lower() in {"1", "true", "yes", "on"}


def _off_ramp_ratio_by_segment(cfg, link: str, count: int) -> list[float]:
    net = cfg.network
    out = [0.0 for _ in range(count)]
    for off_ramp in getattr(net, "off_ramps", []):
        if str(net.off_ramp_from_freeway.get(off_ramp, "")) != str(link):
            continue
        raw_idx = getattr(net, "off_ramp_segment_index", {}).get(off_ramp, count - 1)
        idx = int(clamp(_as_float(raw_idx), 0.0, float(max(0, count - 1))))
        out[idx] = clamp(out[idx] + _as_float(net.off_ramp_split_ratio.get(off_ramp), 0.0), 0.0, 1.0)
    return out


def _vsl_aware_link_rollout_terms(
    context: Mapping[str, Any],
    vsl_kph: float,
    cfg,
    metanet_module,
) -> tuple[float, float, float, float, float] | None:
    """Small Vissim-only link rollout used to rank VSL candidates.

    The stock local follower computes candidate freeway TTS before the VSL loop,
    so all VSL candidates inherit the same freeway/density terms. This helper
    gives the adapter a candidate-specific METANET/CTM approximation without
    editing the external Numerical-Sim checkout.
    """
    agent = context.get("agent")
    state = context.get("state")
    forecast = list(context.get("forecast") or [])
    lane_profile = _mapping(context.get("lane_profile"))
    ramp_metering = _mapping(context.get("ramp_metering"))
    upper = _mapping(context.get("upper"))
    if agent is None or state is None or not forecast:
        return None

    net = cfg.network
    link = str(agent.link)
    rhos = [max(0.0, _as_float(value)) for value in state.freeway_density.get(link, [])]
    if not rhos:
        return None
    speeds_raw = state.freeway_speed.get(link, [])
    speeds = [
        max(float(getattr(net, "v_min", 5.0)), _as_float(speeds_raw[i], getattr(net, "v_free", 120.0)))
        if i < len(speeds_raw)
        else float(getattr(net, "v_free", 120.0))
        for i in range(len(rhos))
    ]
    raw_lanes = lane_profile.get(link, []) if isinstance(lane_profile, Mapping) else []
    lanes = [
        max(1.0e-9, _as_float(raw_lanes[i], getattr(net, "freeway_lanes", 4)))
        if i < len(raw_lanes)
        else max(1.0e-9, float(getattr(net, "freeway_lanes", 4)))
        for i in range(len(rhos))
    ]
    lengths = _freeway_segment_lengths_km(cfg, link, len(rhos))
    off_ratios = _off_ramp_ratio_by_segment(cfg, link, len(rhos))
    dt_h = float(cfg.simulation.T_c_h)
    horizon_steps = forecast[: max(1, int(getattr(cfg.mpc, "horizon_steps", 1)))]
    max_vsl = max(float(value) for value in cfg.freeway_follower.vsl_set)
    vsl_active = float(vsl_kph) < max_vsl - 0.5
    merge_idx = int(clamp(
        getattr(agent, "segment_index", len(rhos) // 2),
        0.0,
        float(max(0, len(rhos) - 1)),
    ))
    release = sum(
        min(
            max(0.0, _as_float(ramp_metering.get(ramp))),
            max(0.0, _as_float(upper.get(ramp), ramp_metering.get(ramp, 0.0))),
        )
        for ramp in getattr(agent, "ramps", [])
    )

    vehicle_tts = 0.0
    density_excess_tts = 0.0
    peak_density = max(rhos)
    capacity = max(0.0, float(getattr(net, "freeway_capacity_veh_h", 0.0)))
    for step in horizon_steps:
        q_values = [
            metanet_module.segment_flow_veh_h(rho, speed, lane)
            for rho, speed, lane in zip(rhos, speeds, lanes)
        ]
        if capacity > 0.0:
            q_values = [min(q, capacity) for q in q_values]
        receiving = [
            max(0.0, (float(net.rho_max) - rhos[i]) * lengths[i] * lanes[i] / max(dt_h, 1.0e-9))
            for i in range(len(rhos))
        ]
        sending = [
            (1.0 - off_ratios[i]) * q_values[i]
            for i in range(len(rhos))
        ]
        q_inter = [
            min(sending[i], receiving[i + 1])
            for i in range(len(rhos) - 1)
        ]
        mainline_demand = max(0.0, _as_float(step.freeway_mainline.get(link, 0.0)))
        entry_flow = min(mainline_demand, capacity if capacity > 0.0 else mainline_demand, receiving[0])
        next_rhos: list[float] = []
        next_speeds: list[float] = []
        for i, rho in enumerate(rhos):
            q_in = entry_flow if i == 0 else q_inter[i - 1]
            if i == merge_idx:
                q_in += release
            q_out = sending[i] if i == len(rhos) - 1 else q_inter[i]
            veh_per_density = max(1.0e-9, lengths[i] * lanes[i])
            rho_next = clamp(
                rho + (q_in - q_out) * dt_h / veh_per_density,
                0.0,
                float(net.rho_max),
            )
            vehicle_tts += 0.5 * (rho + rho_next) * veh_per_density * dt_h
            density_excess_tts += 0.5 * (
                max(0.0, rho - float(net.rho_crit)) + max(0.0, rho_next - float(net.rho_crit))
            ) * dt_h
            upstream_speed = float(net.v_free) if i == 0 else speeds[i - 1]
            downstream_rho = rhos[i + 1] if i + 1 < len(rhos) else rhos[i]
            v_eff = metanet_module.effective_desired_speed_kmh(
                rho,
                float(net.v_free),
                float(net.rho_crit),
                float(vsl_kph),
                float(getattr(net, "alpha_vsl", 0.0)),
                bool(vsl_active),
                float(getattr(net, "metanet_a_m", 1.867)),
            )
            v_next = metanet_module.metanet_speed_update_kmh(
                speeds[i],
                upstream_speed,
                rho,
                downstream_rho,
                v_eff,
                dt_h,
                lengths[i],
                float(net.metanet_tau_h),
                metanet_module.select_anticipation_nu(rho, net),
                float(net.metanet_kappa_veh_km_lane),
                float(net.v_min),
            )
            next_rhos.append(float(rho_next))
            next_speeds.append(float(v_next))
        rhos = next_rhos
        speeds = next_speeds
        peak_density = max(peak_density, max(rhos) if rhos else 0.0)
    return (
        float(vehicle_tts),
        float(density_excess_tts),
        float(rhos[merge_idx] if rhos else 0.0),
        float(peak_density),
        float(release),
    )


def install_vsl_metanet_rollout_runtime_patch(cfg, tuning: Mapping[str, Any]) -> dict[str, float]:
    settings = _vsl_rollout_tuning(tuning)
    if not _is_enabled(settings):
        setattr(cfg, "_vissim_vsl_rollout_enabled", False)
        return {"vsl_metanet_rollout_patch_enabled": 0.0}
    try:
        from src.controllers import distributed_coordinator as dc
        from src.models import metanet as metanet_module
    except Exception:
        return {"vsl_metanet_rollout_patch_enabled": 0.0, "vsl_metanet_rollout_patch_failed": 1.0}

    cls = dc.DistributedCoordinator
    if not hasattr(cls, "_vissim_original_candidate_freeway_tts_terms"):
        cls._vissim_original_candidate_freeway_tts_terms = cls._candidate_freeway_tts_terms
    if not hasattr(cls, "_vissim_original_freeway_agent_objective"):
        cls._vissim_original_freeway_agent_objective = cls._freeway_agent_objective
    if not hasattr(cls, "_vissim_original_solve_for_vsl_consensus"):
        cls._vissim_original_solve_for_vsl_consensus = cls.solve
    original_terms = cls._vissim_original_candidate_freeway_tts_terms
    original_objective = cls._vissim_original_freeway_agent_objective
    original_solve = cls._vissim_original_solve_for_vsl_consensus
    finalize_agent_consensus = str(settings.get("finalize_agent_consensus", False)).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    def patched_candidate_freeway_tts_terms(self, agent, state, ramp_metering, upper, forecast, lane_profile):
        result = original_terms(self, agent, state, ramp_metering, upper, forecast, lane_profile)
        if getattr(self.cfg, "_vissim_vsl_rollout_enabled", False):
            self._vissim_vsl_rollout_context = {
                "agent": agent,
                "state": state,
                "ramp_metering": dict(ramp_metering),
                "upper": dict(upper),
                "forecast": list(forecast),
                "lane_profile": lane_profile,
            }
        return result

    def patched_freeway_agent_objective(
        self,
        rhos,
        density_excess,
        metering_error,
        ramp_metering,
        vsl,
        previous_vsl,
        offramp_forecast_veh,
        offramp_storage_veh,
        offramp_capacity_veh=0.0,
        ramp_queue_tts=0.0,
        onramp_urban_queue_tts=0.0,
        horizon_h=1.0,
        freeway_vehicle_tts=None,
        density_excess_tts=None,
    ):
        if getattr(self.cfg, "_vissim_vsl_rollout_enabled", False):
            context = getattr(self, "_vissim_vsl_rollout_context", None)
            terms = _vsl_aware_link_rollout_terms(context or {}, float(vsl), self.cfg, metanet_module)
            if terms is not None:
                freeway_vehicle_tts = terms[0]
                density_excess_tts = terms[1]
                self._vissim_vsl_rollout_eval_count = (
                    int(getattr(self, "_vissim_vsl_rollout_eval_count", 0)) + 1
                )
        return original_objective(
            self,
            rhos,
            density_excess,
            metering_error,
            ramp_metering,
            vsl,
            previous_vsl,
            offramp_forecast_veh,
            offramp_storage_veh,
            offramp_capacity_veh,
            ramp_queue_tts=ramp_queue_tts,
            onramp_urban_queue_tts=onramp_urban_queue_tts,
            horizon_h=horizon_h,
            freeway_vehicle_tts=freeway_vehicle_tts,
            density_excess_tts=density_excess_tts,
        )

    def patched_solve(self, *args, **kwargs):
        result = original_solve(self, *args, **kwargs)
        if not getattr(self.cfg, "_vissim_vsl_rollout_consensus_enabled", False):
            return result
        control = getattr(result, "control", None)
        if control is None:
            return result
        diagnostics: dict[str, Any] = {}
        raw_result_diag = getattr(result, "diagnostics", None)
        if isinstance(raw_result_diag, Mapping):
            diagnostics.update(raw_result_diag)
        raw_control_diag = getattr(control, "diagnostics", None)
        if isinstance(raw_control_diag, Mapping):
            diagnostics.update(raw_control_diag)
        by_link: dict[str, list[float]] = {str(link): [] for link in self.cfg.network.freeway_links}
        for agent in getattr(self, "freeway_agents", []):
            key = f"agent_{agent.id}_vsl_selected"
            if key not in diagnostics:
                continue
            try:
                by_link.setdefault(str(agent.link), []).append(float(diagnostics[key]))
            except (TypeError, ValueError):
                continue
        selected = {link: float(min(values)) for link, values in by_link.items() if values}
        if not selected:
            return result
        for key in list(getattr(control, "vsl", {}).keys()):
            if "__seg" in str(key):
                control.vsl.pop(key, None)
        control.vsl.update(selected)
        consensus_diag = {
            "vsl_agent_consensus_finalize_active": 1.0,
            "vsl_agent_consensus_finalize_link_count": float(len(selected)),
            "vsl_agent_consensus_finalize_min_kph": float(min(selected.values())),
        }
        for link, value in selected.items():
            consensus_diag[f"vsl_agent_consensus_{link}_kph"] = float(value)
        control.diagnostics.update(consensus_diag)
        if isinstance(raw_result_diag, Mapping):
            raw_result_diag.update(consensus_diag)
        return result

    cls._candidate_freeway_tts_terms = patched_candidate_freeway_tts_terms
    cls._freeway_agent_objective = patched_freeway_agent_objective
    cls.solve = patched_solve
    setattr(cfg, "_vissim_vsl_rollout_enabled", True)
    setattr(cfg, "_vissim_vsl_rollout_consensus_enabled", finalize_agent_consensus)
    return {
        "vsl_metanet_rollout_patch_enabled": 1.0,
        "vsl_agent_consensus_finalize_enabled": float(finalize_agent_consensus),
    }


def _observation_split_parameters(calibration: Mapping[str, Any] | None = None) -> dict[str, float]:
    observation = _mapping((calibration or {}).get("observation"))
    return {
        "internal_storage_fraction": clamp(
            _as_float(
                observation.get("internal_storage_fraction"),
                LOCAL_OBSERVATION_INTERNAL_STORAGE_FRACTION,
            ),
            0.0,
            1.0,
        ),
        "offramp_storage_fraction": clamp(
            _as_float(
                observation.get("offramp_storage_fraction"),
                LOCAL_OBSERVATION_OFFRAMP_STORAGE_FRACTION,
            ),
            0.0,
            1.0,
        ),
    }


def _link_counts_from_local_observation(state_json: Mapping[str, Any]) -> dict[str, float]:
    """링크별 점유 대수. `RW_QUEUE_WINDOW_STAT` 이 켜져 있으면 직전 구간 창 집계를 쓴다.

    **큐 배정이 이 값에서 나온다** — `queue_count = link_counts x (1 - storage_fraction)`.
    `link_stopped_counts` 는 저류 몫의 정지 비율에만 쓰인다. 2026-08-22 에 창 집계를
    정지차에만 걸었다가 결정이 하나도 안 바뀌는 걸 뒤늦게 발견했다(leave-one-out
    리플레이에서 `no_window` 가 `all` 과 현시 0개 차이).

    창을 쓰는 이유는 위상 잠금이다 — 제어주기 150s 가 신호주기 150s 와 같아 관측이 늘
    같은 신호 위상에 떨어진다(SC1 동서: 결정시점 0.1 vs 창평균 3.3 vs 창최대 12.8).
    필드가 없으면 순간값으로 폴백해 **비트 동일**이다."""
    local = state_json.get("local_observation", {})
    if not isinstance(local, Mapping):
        return {}
    raw = local.get("link_counts", {})
    mode = str(os.environ.get("RW_QUEUE_WINDOW_STAT", "")).strip().lower()
    if mode in {"mean", "max"}:
        windowed = local.get("link_counts_window_mean")
        samples = _as_float(local.get("queue_window_samples"), 0.0)
        if isinstance(windowed, Mapping) and windowed and samples >= 1.0:
            raw = windowed
    if not isinstance(raw, Mapping):
        return {}
    return {str(k): max(0.0, _as_float(v)) for k, v in raw.items()}


def _link_metric_from_local_observation(
    state_json: Mapping[str, Any],
    key: str,
) -> dict[str, float]:
    local = state_json.get("local_observation", {})
    if not isinstance(local, Mapping):
        return {}
    raw = local.get(key, {})
    if not isinstance(raw, Mapping):
        return {}
    return {str(k): max(0.0, _as_float(v)) for k, v in raw.items()}


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit(path: Path) -> str:
    # `text=True` 만 주면 파이썬이 **로케일 기본 인코딩**으로 디코딩한다. 이 워크스페이스는
    # 한글 경로(학술/찐찐막)이고 git 은 그 경로를 UTF-8 로 출력하므로, cp949 로케일에서는
    # subprocess 의 reader 스레드가 UnicodeDecodeError 로 죽는다. 그러면 `stdout` 이 None 이
    # 되고 `.stdout.strip()` 이 AttributeError 를 던지는데, 이 예외는 아래 except 에 없어
    # 그대로 전파되어 **어댑터 프로세스 전체가 종료**된다.
    # 2026-08-07 실 런에서 매 decision 마다 이것으로 죽었다(DECISION_EXIT_NONZERO).
    # 인코딩을 명시해 로케일 의존을 제거한다.
    try:
        top_level = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        ).stdout.strip()
        if Path(top_level).resolve() != path.resolve():
            return ""
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()


def _snapshot_commit(path: Path) -> str:
    snapshot = path / "SNAPSHOT.md"
    if not snapshot.is_file():
        return ""
    match = re.search(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])", snapshot.read_text(encoding="utf-8-sig"), re.I)
    return match.group(0) if match else ""


def _source_tree_sha256(path: Path) -> str:
    source_root = path / "src"
    if not source_root.is_dir():
        return ""
    digest = hashlib.sha256()
    for source in sorted(source_root.rglob("*.py"), key=lambda item: item.relative_to(source_root).as_posix()):
        digest.update(source.relative_to(source_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_run_provenance(
    repo_root: Path,
    state_json: Mapping[str, Any],
    state_path: Path,
    mapping_path: Path,
    detector_mapping_path: Path,
    calibration_path: Path,
    tuning_path: Path,
    network_path: Path | None = None,
) -> dict[str, Any]:
    network_path = network_path or (
        WORKSPACE_ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
    )
    state_run_provenance = _mapping(state_json.get("run_provenance"))
    run_manifest_text = str(state_run_provenance.get("manifest_path", "")).strip()
    run_manifest_path = Path(run_manifest_text) if run_manifest_text else Path("__missing_run_manifest.json")
    inputs = {
        "state_json": state_path,
        "control_mapping_json": mapping_path,
        "detector_mapping_json": detector_mapping_path,
        "calibration_json": calibration_path,
        "tuning_json": tuning_path,
        "adapter_py": Path(__file__).resolve(),
        "fixed_signal_schedule_py": WORKSPACE_ROOT / "evaluation" / "controllers" / "fixed_signal_schedule.py",
        "strict_signal_program_py": WORKSPACE_ROOT / "plant" / "src" / "vissim_strict" / "signal_program.py",
        "network_inpx": network_path,
        "main_vbs_runner": WORKSPACE_ROOT / "scripts" / "run_real_world_stackelberg_controller.vbs",
        # 2026-08-14: 생산 격자가 pedovrx 로 옮겨 갔다. 이 넷은 모형 입력이 아니라
        # execution_fingerprint_sha256 에 들어가는 **증거**다 - 낡은 채로 두면 모든 런이
        # 자기가 쓰지도 않은 2026-08-05 격자를 썼다고 기록한다.
        "watchdog_wrapper": WORKSPACE_ROOT / "scripts" / "run_real_world_single_watchdog_distributed_pedovrx.ps1",
        "numsim_default_yaml": repo_root / "src" / "config" / "default.yaml",
        "link_assignment_json": WORKSPACE_ROOT / "outputs" / "link_player_assignment_pedfold_20260814.json",
        "intersection_adjacency_json": WORKSPACE_ROOT / "outputs" / "intersection_adjacency_pedfold_20260814.json",
        "storage_capacity_json": STORAGE_CAPACITY_EVIDENCE_JSON,
        "run_manifest_json": run_manifest_path,
    }
    imported_modules = {}
    expected_root = repo_root.resolve()
    for module_name, module in sorted(sys.modules.items()):
        if module_name != "src" and not module_name.startswith("src."):
            continue
        module_text = str(getattr(module, "__file__", "") or "").strip()
        if not module_text:
            continue
        module_path = Path(module_text).resolve()
        if not module_path.is_relative_to(expected_root):
            raise RuntimeError(f"imported {module_name} from {module_path}, expected under {expected_root}")
        imported_modules[module_name] = {
            "path": str(module_path),
            "sha256": _file_sha256(module_path),
        }
    signal_programs = {
        path.name: _file_sha256(path)
        for path in sorted(network_path.parent.glob("*.sig"), key=lambda item: item.name)
    }
    provenance = {
        "schema_version": 2,
        "run_id": str(state_run_provenance.get("run_id", "")),
        "workspace_root": str(WORKSPACE_ROOT.resolve()),
        "workspace_git_commit": _git_commit(WORKSPACE_ROOT),
        "numsim_repo_root": str(repo_root.resolve()),
        "numsim_git_commit": _git_commit(repo_root),
        "numsim_snapshot_commit": _snapshot_commit(repo_root),
        "numsim_src_sha256": _source_tree_sha256(repo_root),
        "imported_modules": imported_modules,
        "signal_program_sha256": signal_programs,
        "inputs": {
            name: {
                "path": str(path.resolve()) if str(path) else "",
                "sha256": _file_sha256(path),
                "exists": path.is_file(),
            }
            for name, path in inputs.items()
        },
    }
    stable_evidence = {
        "numsim_repo_root": provenance["numsim_repo_root"],
        "numsim_git_commit": provenance["numsim_git_commit"],
        "numsim_snapshot_commit": provenance["numsim_snapshot_commit"],
        "numsim_src_sha256": provenance["numsim_src_sha256"],
        "imported_modules": provenance["imported_modules"],
        "signal_program_sha256": provenance["signal_program_sha256"],
        "inputs": {name: value for name, value in provenance["inputs"].items() if name != "state_json"},
    }
    provenance["execution_fingerprint_sha256"] = hashlib.sha256(
        json.dumps(stable_evidence, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return provenance


def _network_path_from_state(state_json: Mapping[str, Any]) -> Path:
    provenance = state_json.get("run_provenance", {})
    if isinstance(provenance, Mapping):
        value = provenance.get("network_path", "")
        if value:
            return Path(str(value))
    value = state_json.get("network_path", "")
    if value:
        return Path(str(value))
    return WORKSPACE_ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"


MOVEMENT_SIGNAL_GROUP_MAP_PATH = (
    WORKSPACE_ROOT / "outputs" / "movement_signal_group_map_v3.json"
)


def load_movement_signal_group_map(path: Path | None = None) -> dict[str, Any] | None:
    """N4-2 매핑 산출물을 읽는다. 없으면 `None` 이고 호출부가 이름 규칙으로 떨어진다.

    없다고 예외를 던지지 않는 이유는 제어 SC 의 폴백이 항상녹색이 아니라 기존 2현시
    경로이기 때문이다(N4-4 의 fail-closed 대상은 monitor 노드다). 대신 폴백 건수를
    `native_phase_share_*_fallback_count` 로 내보내 조용히 지나가지 못하게 한다.
    """
    source = Path(path) if path is not None else MOVEMENT_SIGNAL_GROUP_MAP_PATH
    if not source.is_file():
        return None
    return json.loads(source.read_text(encoding="utf-8"))


SIGNAL_GROUP_ACTUATION_PLAN_PATH = (
    WORKSPACE_ROOT / "outputs" / "signal_group_actuation_plan_v3.json"
)
# 러너 원문에서 한 번만 읽는다. 결정마다 읽으면 15 SC x 60 결정 = 900 번 러너를 다시
# 파싱하게 된다. 상수는 런 도중 바뀌지 않는다.
RUNNER_CLEARANCE_SEC = plant_cycle.runner_clearance_sec()


def load_signal_group_actuation_plan(path: Path | None = None) -> dict[str, Any] | None:
    """N4-5 액추에이션 계획을 읽는다. 없으면 `None` 이고 action CSV 는 예전 모양이다.

    여기서 예외를 던지지 않는 이유는 러너 쪽에 짝이 되는 게이트가 있기 때문이다.
    러너의 generated config 에 `RW_SIGNAL_SG_PLAN_SCHEMA` 가 있으면 `signal_sg` 행이
    **반드시** 와야 하고, 없으면 action CSV 전체를 거부한다. 즉 "계획 없이 조용히
    이름 규칙으로 도는" 조합은 러너에서 막힌다.
    """
    source = Path(path) if path is not None else SIGNAL_GROUP_ACTUATION_PLAN_PATH
    if not source.is_file():
        return None
    return json.loads(source.read_text(encoding="utf-8"))


def plan_live_phases(plan_table: Mapping[str, Any], sc_no: int) -> tuple[str, ...]:
    """계획이 그 SC 에서 **실제로 켤 수 있는** 현시. 액션의 현시 집합과 같아야 한다.

    SG 가 붙어 있는 것만으로는 부족하다. SC107·108·109 는 한 현시의 SG 가 `.sig` 에서
    영구적색이라 네이티브 녹색이 0 이고, 아무리 녹색을 명령해도 0 초가 실현된다. 그
    현시를 살아 있다고 세면 러너가 clearance 를 한 번 더 물고(주기가 3 s 밀린다) 모델은
    켜지지 않을 현시에 예산을 붓는다(실측 SC107 p1 지시 97.5 s, 실현 0.0 s).
    """
    node = (plan_table.get("controllers") or {}).get(str(int(sc_no)))
    if node is None:
        raise signal_group_plan.SignalGroupPlanError(
            f"actuation plan has no controller {sc_no}"
        )
    groups = node.get("phase_signal_groups") or {}
    native = node.get("axis_green_sec") or {}
    return tuple(
        phase
        for phase in signal_group_plan.MODEL_PHASES
        if tuple(groups.get(phase) or ()) and float(native.get(phase, 0.0)) > 0.0
    )


def signal_group_action_rows(
    plan_table: Mapping[str, Any],
    sc_no: int,
    phase_greens: Mapping[str, float],
    offset: float,
    metadata: str,
) -> list[dict[str, Any]]:
    """한 SC 의 `signal_sg` 행. 열 재사용 규칙은 `action_csv_schema` 가 정본이다.

        dsd_no    -> sg 번호
        link      -> 녹색창 인덱스
        p1_green  -> 녹색창 시작[s] (플랜 주기 좌표)
        p2_green  -> 녹색창 끝[s]
        p3_green  -> 빈 칸       p4_green -> 빈 칸
        offset    -> 그 SC 의 offset (같은 SC 의 `signal` 행과 같아야 한다)
        green_sec -> 플랜 주기[s]

    이 행은 **파생**이다. 정본은 같은 SC 의 `signal` 행이 싣는 현시 4값이고, 러너가
    `green_sec` 을 그 4값으로 다시 계산해 대조한다(어긋나면 CSV 전량 거부).
    """
    node = (plan_table.get("controllers") or {}).get(str(int(sc_no)))
    if node is None:
        raise signal_group_plan.SignalGroupPlanError(
            f"actuation plan has no controller {sc_no}"
        )
    plan = signal_group_plan.node_plan_from_json(node)
    # 액션이 녹색을 준 현시와 계획이 SG 를 붙여 둔 현시가 다르면 창을 만들지 않는다.
    # 여기서 조용히 넘어가면 러너는 주기가 맞는 CSV 를 받고, 녹색을 받기로 한 이동류는
    # 아무 창도 없이 통째로 적색이 된다 - 런 중에도 안 보인다.
    commanded = signal_group_plan.live_phases(phase_greens)
    planned = plan_live_phases(plan_table, sc_no)
    if commanded != planned:
        raise signal_group_plan.SignalGroupPlanError(
            f"sc {sc_no}: action commands green on phases {commanded} but the actuation plan "
            f"has signal groups on {planned}"
        )
    # 계획 표에 없으면 리터럴이 아니라 **러너 원문** 으로 떨어진다. 여기서 나온 주기는
    # 러너가 자기 현시 주기와 대조하는 값이라(:1453), 4 s 만 달라도 그 SC 의 창이 통째로
    # 거부된다. 리터럴을 두면 러너가 clearance 를 바꾼 순간 조용히 그 상태가 된다.
    amber, all_red = RUNNER_CLEARANCE_SEC
    amber = float(plan_table.get("amber_sec", amber))
    all_red = float(plan_table.get("all_red_sec", all_red))
    cycle = signal_group_plan.plan_cycle_sec(phase_greens, amber, all_red)
    windows = signal_group_plan.plan_windows(
        plan,
        phase_greens=phase_greens,
        phase_order=signal_group_plan.phase_layout_order(
            str(node.get("major_maps_to", "p2"))
        ),
        amber_sec=amber,
        all_red_sec=all_red,
    )
    rows: list[dict[str, Any]] = []
    for window in windows:
        row = {
            "kind": "signal_sg",
            "id": f"SC{int(sc_no)}_SG{window.sg_no}_W{int(window.window_index)}",
            "dsd_no": window.sg_no,
            "sc_no": int(sc_no),
            "link": int(window.window_index),
            "lane": 0,
            "speed_kph": 0,
            action_csv_schema.WINDOW_START_FIELD: round(window.start_sec, 6),
            action_csv_schema.WINDOW_END_FIELD: round(window.end_sec, 6),
            "offset": round(float(offset), 3),
            "rate_vph": 0,
            "green_sec": round(cycle, 6),
            "metadata": metadata,
        }
        for field in action_csv_schema.WINDOW_BLANK_FIELDS:
            row[field] = ""
        rows.append(row)
    return rows


class MonitorFixedSignalPatchError(RuntimeError):
    """고정신호 패치를 설치하지 못했다 (v3 N4-4).

    원본 `_phase_green_fraction` 은 phase 가 빈 movement 에 1.0(항상녹색)을 돌려준다.
    패치가 조용히 빠지면 monitor 26개 SC 가 통째로 항상녹색이 되는데 아무도 모른다.
    그래서 실패는 예외다. 정당한 "대상 없음"(uncontrolled·signals 공집합)만 건너뛴다.
    """


_NARROW_SG_CACHE: dict[str, Any] = {}


def _narrowed_signal_groups(spec: Mapping[str, Any], schedule) -> tuple[str, ...] | None:
    """movement 를 **자기 현시의 SG** 로 좁힌다. 못 좁히면 None(기존 해석 유지).

    기본 해석은 origin 링크에 달린 신호두의 SG 를 전부 합집합으로 준다. 신호두의 `lane`
    이 링크 단위라 직진과 보호좌회전이 한 덩어리가 되기 때문이다. movement 의 `phase`
    (예: "SC1_p3")로 `movement_signal_group_map_v3.json` 의 `phase_signal_groups` 를
    찾아 교집합하면 자기 현시만 남는다.

    교집합이 비면 **좁히지 않는다** - 맵이 낡아 SG 이름이 안 맞는 경우가 있고(실측 38건),
    그때 0 을 돌려주면 그 movement 가 영영 방출 못 한다. 과대가 낫지 무방출은 안 된다.
    """
    phase = str(spec.get("phase", ""))
    node = str(spec.get("intersection", ""))
    if not phase or not node:
        return None
    if "map" not in _NARROW_SG_CACHE:
        payload = load_movement_signal_group_map()
        _NARROW_SG_CACHE["map"] = _mapping((payload or {}).get("controllers"))
    controllers = _NARROW_SG_CACHE["map"]
    entry = _mapping(controllers.get(node))
    table = _mapping(entry.get("phase_signal_groups"))
    if not table:
        return None
    key = phase.split("_", 1)[1] if "_" in phase else phase
    own = {str(g) for g in (table.get(key) or [])}
    if not own:
        return None
    current = {str(g) for g in schedule.movement_signal_groups(spec)}
    narrowed = tuple(sorted(current & own)) if current else tuple(sorted(own))
    return narrowed or None


def _validation_fixed_signal_enabled() -> bool:
    """검증 rollout 에서 제어 SC 도 고정시간 신호를 쓸지. **생산에서는 켜지 마라.**

    실제 컨트롤러는 후보의 녹색 배분으로 굴려야 하고 그것이 MPC 다. 이 스위치는
    무제어 rollout 으로 동역학 충실도를 잴 때만 쓴다 - VISSIM 이 실제로 돌린 신호를
    재현해야 모델 오차와 신호 불일치가 갈린다.
    """
    return str(os.environ.get("RW_VALIDATION_FIXED_SIGNAL", "")).strip().lower() in {"1", "true", "on"}


def build_patched_phase_green_fraction(original, schedules, share_table):
    """`_phase_green_fraction` 대체본을 만든다.

    - phase 가 있는 movement(=제어 SC): native 배분이 있으면 원본 값에 곱한다.
      배분이 없거나 정확히 1.0 이면 **원본을 그대로 돌려준다** - N=2 비트동일 경로다.
    - phase 가 빈 movement(=monitor SC): 고정 스케줄로 native 타임라인을 적분한다.
      스케줄이 없으면 항상녹색으로 되돌아가는 대신 예외를 던진다.
    """

    def patched_phase_green_fraction(control, cfg_arg, spec, urban_step_index=None):
        if str(spec.get("phase", "")):
            # **검증 전용 경로.** 제어 SC 도 VISSIM 이 실제로 돌린 고정시간 신호를 쓴다.
            #
            # 왜 필요한가: 무제어 rollout 으로 동역학을 검증할 때, 제어 SC 는
            # ControlAction.uncontrolled 의 **주기 균등분할** 녹색을 받는다. 그러면 모델은
            # 모든 movement 를 동시에 평균 녹색률로 방출하는데 VISSIM 은 현시를 순차로 돌려
            # 한 번에 한 무리만 전 속도로 뺀다. 한 주기 적분하면 총량은 같지만 60초 창 안의
            # 공간 분포가 달라서, 그 차이가 모델 오차로 잘못 계상된다.
            #
            # 실측 근거(2026-08-16): 창 정확 녹색을 쓰는 비제어 노드 스텝1 39.4%(G5 42.7%) 대
            # 평균 녹색을 쓰는 제어 노드 48.3%(G5 27.1%). 그리고 포화유율을 낮출수록 적합이
            # 좋아지는 것(400 veh/h 에서 최적)이 "과다 동시 방출" 의 서명이다.
            #
            # **생산에서는 켜면 안 된다.** 실제 컨트롤러는 후보의 녹색 배분으로 굴려야 하고
            # 그것이 MPC 다. 이 경로는 동역학 충실도를 재는 동안만 쓴다.
            if _validation_fixed_signal_enabled():
                node = str(spec.get("intersection", ""))
                schedule = schedules.get(node)
                if schedule is not None:
                    # movement 자기 현시의 SG 로 좁힌다. 좁히지 않으면 신호두 lane 이 링크
                    # 단위라 직진이 보호좌회전 녹색까지 받는다(실측: 542개 중 339개가
                    # 녹색창 2~4개에 걸치고 union 이 단일 SG 의 중앙값 1.39배).
                    groups = _narrowed_signal_groups(spec, schedule)
                    if urban_step_index is None:
                        return float(clamp(schedule.movement_green_fraction(spec, group_ids=groups), 0.0, 1.0))
                    duration_sec = float(cfg_arg.simulation.T_u_sec)
                    start_sec = _absolute_urban_step_start_sec(urban_step_index, duration_sec)
                    return float(
                        clamp(
                            schedule.movement_green_fraction(spec, start_sec, duration_sec, group_ids=groups),
                            0.0,
                            1.0,
                        )
                    )
            share = share_table.share_for(spec)
            if share is None:
                return original(control, cfg_arg, spec, urban_step_index)
            return original(control, cfg_arg, spec, urban_step_index) * share
        node = str(spec.get("intersection", ""))
        schedule = schedules.get(node)
        if schedule is None:
            raise MonitorFixedSignalPatchError(
                f"uncontrolled movement at node {node!r} has no fixed signal schedule; "
                "falling back to the original path would make it always-green"
            )
        if urban_step_index is None:
            return float(clamp(schedule.movement_green_fraction(spec), 0.0, 1.0))
        duration_sec = float(cfg_arg.simulation.T_u_sec)
        start_sec = _absolute_urban_step_start_sec(urban_step_index, duration_sec)
        return float(
            clamp(
                schedule.movement_green_fraction(spec, start_sec, duration_sec),
                0.0,
                1.0,
            )
        )

    return patched_phase_green_fraction


def install_monitor_fixed_signal_runtime_patch(
    cfg,
    state_json: Mapping[str, Any],
    detector_mapping: Mapping[str, Any],
) -> dict[str, Any]:
    """Use native VISSIG timing for monitor nodes and native green shares for controlled ones."""

    from evaluation.controllers import fixed_signal_schedule
    from evaluation.controllers.native_phase_green import (
        build_native_phase_share_table,
    )

    uncontrolled = {str(node) for node in getattr(cfg.network, "uncontrolled_nodes", [])}
    controlled = {str(node) for node in getattr(cfg.network, "signals", [])}
    targets = uncontrolled | controlled
    network_path = _network_path_from_state(state_json)
    if not targets:
        return {
            "monitor_fixed_signal_patch_enabled": 0.0,
            "monitor_fixed_signal_patch_skip_reason": "no_target_nodes",
            "monitor_fixed_signal_network_path": str(network_path),
            "monitor_fixed_signal_schedule_count": 0.0,
            "monitor_fixed_signal_expected_count": 0.0,
        }
    if not network_path.is_file():
        raise MonitorFixedSignalPatchError(
            f"fixed signal patch needs the run network but it is not a file: {network_path}"
        )
    try:
        schedules, errors = fixed_signal_schedule.compile_fixed_signal_schedules(
            network_path, targets, detector_mapping
        )
    except Exception as exc:
        raise MonitorFixedSignalPatchError(
            f"fixed signal compile failed for {network_path}: {type(exc).__name__}: {exc}"
        ) from exc

    # monitor 노드만 fail-closed 다. 제어 SC 는 스케줄이 없어도 기존 2현시 경로로
    # 떨어질 뿐이라 항상녹색이 되지 않는다 - 그쪽은 진단으로 계상한다.
    missing_monitor = sorted(uncontrolled - set(schedules))
    monitor_errors = {node: text for node, text in sorted(errors.items()) if node in uncontrolled}
    if missing_monitor or monitor_errors:
        raise MonitorFixedSignalPatchError(
            "uncontrolled nodes without a fixed schedule would become always-green: "
            f"missing={missing_monitor} errors={monitor_errors}"
        )

    signal_group_map = load_movement_signal_group_map()
    share_table = build_native_phase_share_table(
        getattr(cfg.network, "urban_movements", {}) or {}, schedules, signal_group_map
    )

    model_module = importlib.import_module("src.models.urban_queue_model")
    original = getattr(
        model_module,
        "_vissim_original_phase_green_fraction",
        model_module._phase_green_fraction,
    )
    setattr(model_module, "_vissim_original_phase_green_fraction", original)
    patched_phase_green_fraction = build_patched_phase_green_fraction(
        original, schedules, share_table
    )

    patched_modules = 0
    for module_name in (
        "src.models.urban_queue_model",
        "src.controllers.distributed_coordinator",
        "src.controllers.local_signal_plant",
        "src.controllers.wu_distributed",
        "src.controllers.wu_faithful_follower",
    ):
        module = importlib.import_module(module_name)
        if hasattr(module, "_phase_green_fraction"):
            setattr(module, "_phase_green_fraction", patched_phase_green_fraction)
            patched_modules += 1
    if patched_modules == 0:
        raise MonitorFixedSignalPatchError(
            "no model module exposes _phase_green_fraction; the patch would be a no-op"
        )

    diagnostics: dict[str, Any] = {
        "monitor_fixed_signal_patch_enabled": 1.0,
        "monitor_fixed_signal_network_path": str(network_path.resolve()),
        "monitor_fixed_signal_schedule_count": float(len(schedules)),
        "monitor_fixed_signal_expected_count": float(len(targets)),
        "monitor_fixed_signal_missing_nodes": ",".join(sorted(targets - set(schedules))),
        "monitor_fixed_signal_compile_errors": dict(errors),
        "monitor_fixed_signal_patched_module_count": float(patched_modules),
        "native_phase_share_map_path": str(MOVEMENT_SIGNAL_GROUP_MAP_PATH),
    }
    diagnostics.update(share_table.diagnostics)
    return diagnostics


PERIMETER_MOVEMENT_KINDS_ADAPTER = {"boundary_in", "boundary_out", "on_ramp", "off_ramp"}


def install_movement_capacity_by_lanes(cfg, tuning: Mapping[str, Any]) -> dict[str, float]:
    """movement 방류 용량을 **차로수 비례**로 배분한다. `urban.capacity.per_lane` 없으면 no-op.

    왜. `_movement_capacity_flow` 가 내부 movement 184개 전부에 전역 스칼라 하나를 준다.
    spec 에 차로 수도 포화유율도 없어서 1차로 보호좌회전과 3차로 직진이 같은 값을 받는다.
    3시점 검정에서 전역 600 이 집계는 잘 맞췄지만(잔차 -6.3/+7.5/-10.0%) **상대 용량은
    여전히 틀려 있다** — 신호제어가 쓰는 게 정확히 그 상대값이다.

    유도. 산출물의 길이·jam 으로 링크 차로수를 역산하고, 그 링크에서 출발하는 movement
    들에 회전 분율 `beta` 로 나눈다(실제 차로 배정이 수요 비례인 것과 맞는다).

        lanes(L)  = storage(L) / (length_km(L) x jam_density)
        lanes(m)  = lanes(origin(m)) x beta(m) / sum(beta over same origin)
        cap(m)    = per_lane x lanes(m)

    정규화. `equivalent_uniform_veh_h`(기본 600)를 주면 내부 movement 총 용량이
    N x 그 값과 같아지도록 per_lane 을 정한다. 3시점 검정으로 확보한 집계 적합을 유지한
    채 **배분만** 바꾼다.
    """
    section = _mapping(_mapping(tuning.get("urban")).get("capacity"))
    # `_is_enabled` 는 문자열 집합 비교라 float 1.0 을 "1.0" 으로 만들어 **꺼진 것으로**
    # 읽는다(실측: per_lane:1.0 이 조용히 무시돼 base 와 소수점까지 같은 결과가 나왔다).
    # 설정이 true / 1 / 1.0 / "on" 중 무엇이어도 켜지도록 여기서는 직접 본다.
    _flag = section.get("per_lane", False)
    _on = bool(_flag) if isinstance(_flag, (bool, int, float)) else         str(_flag).strip().lower() in {"1", "true", "yes", "on"}
    if not _on:
        return {"movement_capacity_by_lanes_enabled": 0.0}
    # movement 별 **실측 차로수**. VISSIM 커넥터 기하에서 뽑는다.
    #
    # 이전 판은 `storage/(length x jam)` 로 링크 차로수를 역산해 beta 로 나눴는데 그게
    # 틀렸다. 산출물 정의가 `sum(link_length_km * lanes) * jam` 이라 그 역산은 **권역
    # 구간의 길이가중 평균 차로수**(중앙 2.77, 정수 근처가 11%뿐)지 정지선에서 그 회전을
    # 담당하는 차로수가 아니다. 방류 용량을 정하는 건 후자다.
    #
    # 지금은 leg 권역의 정지선 유출 커넥터를 목적 SC 로 매칭해 커넥터 `lanes` 수를 쓴다.
    # 실측: internal 184개 중 171개(93%) 해결, 직진 중앙 2.0 / 좌·우 중앙 1.0 차로.
    src = WORKSPACE_ROOT / "outputs/movement_lanes_core17legs4b_20260821.json"
    if not src.is_file():
        return {"movement_capacity_by_lanes_enabled": 0.0, "movement_capacity_by_lanes_source_missing": 1.0}
    lanes_by_movement = _mapping(json.loads(src.read_text(encoding="utf-8")).get("movement_lanes"))
    movements = cfg.network.urban_movements or {}
    internal = {m: sp for m, sp in movements.items()
                if str(sp.get("kind", "")) not in PERIMETER_MOVEMENT_KINDS_ADAPTER}
    # 미해결 movement 는 같은 회전 종류의 중앙값으로 채운다(빠뜨리면 전역 스칼라로 떨어져
    # 구조가 반쪽이 된다).
    by_turn: dict[str, list[float]] = {}
    for m, sp in internal.items():
        v = _as_float(lanes_by_movement.get(m), 0.0)
        if v > 0.0:
            by_turn.setdefault(str(sp.get("turn", "")), []).append(v)
    median_by_turn = {t: sorted(v)[len(v) // 2] for t, v in by_turn.items() if v}
    share: dict[str, float] = {}
    for m, sp in internal.items():
        v = _as_float(lanes_by_movement.get(m), 0.0)
        if v <= 0.0:
            v = median_by_turn.get(str(sp.get("turn", "")), 1.0)
        share[m] = float(v)
    if not share:
        return {"movement_capacity_by_lanes_enabled": 0.0, "movement_capacity_by_lanes_empty": 1.0}

    equiv = _as_float(section.get("equivalent_uniform_veh_h"), 600.0)
    total_target = equiv * float(len(share))
    total_share = sum(share.values())
    per_lane = total_target / total_share if total_share > 1.0e-9 else 0.0
    caps = {m: per_lane * v for m, v in share.items()}
    setattr(cfg.network, "movement_capacity_by_movement_veh_h", caps)
    vals = sorted(caps.values())
    return {
        "movement_capacity_by_lanes_enabled": 1.0,
        "movement_capacity_by_lanes_count": float(len(caps)),
        "movement_capacity_by_lanes_per_lane_veh_h": float(per_lane),
        "movement_capacity_by_lanes_equivalent_uniform": float(equiv),
        "movement_capacity_by_lanes_min_veh_h": float(vals[0]),
        "movement_capacity_by_lanes_median_veh_h": float(vals[len(vals) // 2]),
        "movement_capacity_by_lanes_max_veh_h": float(vals[-1]),
    }


def filter_midblock_links_from_detector_mapping(detector_mapping, tuning: Mapping[str, Any]):
    """미드블록 정지선 링크를 **관측에서** 뺀다. `urban.midblock.exclude_links` 없으면 no-op.

    왜. 권역 정의가 "leg 정지선 접근로 + 상류로 앞 교차로까지" 라, 중간에 미드블록 신호가
    있으면 **그 미드블록의 정지선과 대기 구간까지 본선 leg 가 소유**한다. 그러면 미드블록
    적색에 서 있는 차가 본선 leg 의 큐로 집계되고, 컨트롤러는 "본선 접근로에 큐가 길다"로
    읽어 녹색을 배분한다 — 그 차들은 본선 정지선까지 도달하지도 못한 상태인데.

    실측(2026-08-22): 미드블록 정지선을 품은 leg 이 24개(11개 교차로)이고 SC5 가 5개로
    가장 많다. SC5 본선 배분이 직진 47->10.1초(21%), 좌회전 23->61.7초(268%)로 뒤집혀
    있는 것이 이 오염과 맞는다.

    권역 정본(urban_player_territory_v1)은 **건드리지 않는다** — "재유도하지 않는다,
    읽어서 쓴다" 가 그 파일의 규칙이고 오늘 자동 규칙이 틀린 전례가 있다. 대신 관측
    단계에서 뺀다. 되돌리기 쉽고 정본이 그대로 남는다.

    주의: 31개 중 2개(1220013600, 1220013700)는 본선 신호두도 함께 있어 빼면 본선 관측도
    잃는다. `keep_mixed` 로 남길 수 있다(기본은 규칙대로 전부 뺀다).
    """
    section = _mapping(_mapping(tuning.get("urban")).get("midblock"))
    _flag = section.get("exclude_links", False)
    _on = bool(_flag) if isinstance(_flag, (bool, int, float)) else         str(_flag).strip().lower() in {"1", "true", "yes", "on"}
    if not _on or not detector_mapping:
        return detector_mapping, {"midblock_link_exclusion_enabled": 0.0}
    src = WORKSPACE_ROOT / "outputs/midblock_stopline_links_20260822.json"
    if not src.is_file():
        return detector_mapping, {"midblock_link_exclusion_enabled": 0.0,
                                  "midblock_link_source_missing": 1.0}
    doc = json.loads(src.read_text(encoding="utf-8"))
    drop = {str(k) for k in (_mapping(doc.get("links")) or {})}
    keep_mixed = str(section.get("keep_mixed", "")).strip().lower() in {"1", "true", "yes", "on"}
    if keep_mixed:
        drop -= {str(x) for x in (doc.get("mixed_with_mainline") or [])}
    out = dict(detector_mapping)
    meta = {"midblock_link_exclusion_enabled": 1.0,
            "midblock_link_candidates": float(len(drop)),
            "midblock_keep_mixed": 1.0 if keep_mixed else 0.0}
    for key in ("link_to_origins", "link_to_movements"):
        table = _mapping(detector_mapping.get(key))
        if not table:
            continue
        kept = {k: v for k, v in table.items() if str(k) not in drop}
        meta[f"midblock_dropped_{key}"] = float(len(table) - len(kept))
        out[key] = kept
    obs = detector_mapping.get("observable_links")
    if isinstance(obs, list):
        kept = [x for x in obs if str(x) not in drop]
        meta["midblock_dropped_observable_links"] = float(len(obs) - len(kept))
        out["observable_links"] = kept
    return out, meta


def _native_live_phases_by_signal(cfg) -> dict[str, list[str]]:
    """실측 SG 타이밍에서 SC 별 **녹색 0 이 아닌 현시**를 뽑는다.

    NEMA 이름으로 현시를 정한다(진행방향 기준이라 접근로는 반대다):
    NBT/SBT -> p1(주축 직진) · NBL/SBL -> p2(주축 좌) · EBT/WBT -> p3 · EBL/WBL -> p4.
    미드블록(SG 9+)은 뺀다 — 우리가 구동하지 않는다.
    """
    src = WORKSPACE_ROOT / "outputs/signal_group_timing_core17legs4b_20260819.json"
    if not src.is_file():
        return {}
    nema = {"NBT": "p1", "SBT": "p1", "NBL": "p2", "SBL": "p2",
            "EBT": "p3", "WBT": "p3", "EBL": "p4", "WBL": "p4"}
    controlled = {str(x) for x in _controlled_signal_names(cfg)}
    doc = json.loads(src.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for entry in doc.get("controllers", []) or []:
        sid = f"SC{entry.get('sc_no')}"
        if sid not in controlled:
            continue
        best: dict[str, float] = {}
        for grp in entry.get("groups", []) or []:
            raw_sg = str(grp.get("sg_id", ""))
            if not raw_sg.isdigit() or int(raw_sg) > 8:
                continue
            pid = nema.get(str(grp.get("name", "")).strip().upper())
            if pid is None:
                continue
            best[pid] = max(best.get(pid, 0.0), _as_float(grp.get("green_sec"), 0.0))
        live = [pid for pid in ("p1", "p2", "p3", "p4") if best.get(pid, 0.0) > 0.0]
        # 전부 0 이면 유도 실패다 — 그 SC 는 손대지 않고 전 현시 폴백으로 둔다.
        if live and len(live) < 4:
            out[sid] = live
    return out


def _is_enabled_value(flag: Any) -> bool:
    """단일 값 on/off. bool·수·문자열을 다 받는다.

    `_is_enabled` 는 설정 절 전체를 받고 문자열 집합으로 비교해서 float 1.0 이
    "1.0" 이 되어 조용히 꺼진 적이 있다(2026-08-21 lanes600). 여기서는 수를 먼저 본다.
    """
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, (int, float)):
        return float(flag) != 0.0
    return str(flag).strip().lower() in {"1", "true", "yes", "on"}


MEASURED_SATURATION_EVIDENCE_JSON = WORKSPACE_ROOT / "outputs/movement_saturation_measured_20260822.json"


def install_measured_movement_capacity(cfg, tuning, state_json, previous_path) -> dict[str, float]:
    """**직전 구간 실측 방류율**로 movement 용량을 갱신한다. `urban.capacity.measured` 없으면 no-op.

    왜. 지금 용량은 가정값이다 — 플랜트/GNE 가 `차로수 x 330`, 정련 채점기가
    `len(movements) x 1400`. 실측(무제어 .knr)은 정지선 차로군이 1,100~4,400 veh/h 라
    전자는 3~5배 과소, 후자는 신호 합이 4배 과대다. 리더가 녹색을 나눌 때 쓰는 게
    movement 간 **상대** 용량이라 이 왜곡이 그대로 배분 왜곡이 된다.

    무엇을 재나. 러너가 5초 스캔에서 차량별 (No, Link) 를 이미 읽으므로 연속 스캔을
    비교해 **정지선 링크를 떠난 대수**를 세고 `link_departures_window` 로 실어 보낸다
    (`RW_QUEUE_WINDOW=1`). 그 링크 차로군의 직전 구간 녹색초로 나누면 방류율이다.

        cap_obs[link] = departures[link] / green_sec[link] x 3600

    수요제약을 어떻게 거르나. 한산한 구간의 `departures/green` 은 용량이 아니라 수요다.
    오프라인 분위수로 거르려 했으나 실패했다(중앙값 기준 차로환산 0.52 — 1차로 미만).
    대신 **감쇠 러닝맥스**를 쓴다:

        cap_est = max(cap_obs, decay x cap_est_prev)

    증거가 나오면 즉시 올라가고 없으면 천천히 잊는다. 포화점이 안정 고정점이라
    아래에서 수렴한다 — 녹색이 줄면 큐가 덜 비어 `departures/green` 이 올라간다.
    어댑터는 결정마다 새 프로세스라 직전 추정치를 **직전 action JSON 진단**으로 나른다.

    씨앗. 첫 결정에는 직전값이 없다. 무제어 런에서 유도한
    `movement_saturation_measured_20260822.json` 의 차로군 값을 쓴다.

    차로군 -> movement 배분. 한 접근로의 직진·좌·우는 **같은 차로를 나눠 쓴다**.
    차로군 총량을 movement 마다 복제하면 그 접근로가 용량의 3배를 방류한다.
    모델 자신의 회전 분율 `beta` 로 나눈다 — 총량이 보존된다.
    """
    section = _mapping(_mapping(tuning.get("urban")).get("capacity"))
    if not _is_enabled_value(section.get("measured")):
        return {"measured_capacity_enabled": 0.0}
    decay = _as_float(section.get("decay"), 0.98)
    local = _mapping(state_json.get("local_observation"))
    departures = {str(k): _as_float(v, 0.0) for k, v in _mapping(local.get("link_departures_window")).items()}

    prev_est: dict[str, float] = {}
    try:
        prev_doc = json.loads(Path(previous_path).read_text(encoding="utf-8"))
        for holder in ("metadata", "diagnostics"):
            for key, value in _mapping(prev_doc.get(holder)).items():
                if key.startswith("sat_est_"):
                    prev_est[key[len("sat_est_"):]] = _as_float(value, 0.0)
    except (OSError, ValueError):
        pass

    groups: list[Mapping[str, Any]] = []
    if MEASURED_SATURATION_EVIDENCE_JSON.is_file():
        doc = json.loads(MEASURED_SATURATION_EVIDENCE_JSON.read_text(encoding="utf-8"))
        groups = [g for g in (doc.get("lane_groups") or []) if isinstance(g, Mapping)]
    # 씨앗. 기본은 **플랜트가 지금 믿는 값**(차로수 x equivalent_uniform, 통상 330)이다.
    #
    # 왜 기하값(차로수 x 1800)을 안 쓰나. `max(실측, 씨앗)` 에서 기하 씨앗은 실측보다
    # 3~8배 커서 사실상 늘 이긴다(실측: 60개 중 2개만 채택). 그러면 "직전 실측을 쓴다"가
    # 아니라 "1800/차로를 가정한다"가 되고, 이 망이 실제로 그 근처도 못 가므로 낙관적이다.
    # 플랜트 현재값에서 출발하면 대부분의 접근로에서 실측이 즉시 이겨 데이터가 지배한다
    # (예: SC6 1220021201 실측 7,912 vs 4차로x330 = 1,320).
    #
    # `seed: "geometric"` 으로 옛 거동(차로수 x 1800)을 되살릴 수 있다.
    seed_mode = str(section.get("seed", "plant")).strip().lower()
    base_caps = dict(getattr(cfg.network, "movement_capacity_by_movement_veh_h", {}) or {})
    seed: dict[str, float] = {}
    if seed_mode == "geometric":
        for g in groups:
            link = str(g.get("stopline_link", ""))
            if link:
                seed[link] = seed.get(link, 0.0) + _as_float(g.get("saturation_veh_h"), 0.0)
    else:
        # 접근로 총량 = 그 접근로 movement 들의 현재 용량 합. 이탈 계수(링크 단위)와
        # 같은 단위가 되고, 아래 배분에서 그대로 되돌려 놓으므로 실측이 없으면 무변화다.
        for link, (sig, pids) in _approach_topology(groups).items():
            total = sum(
                float(base_caps.get(m, cfg.network.movement_capacity_veh_h))
                for m, spec in (cfg.network.urban_movements or {}).items()
                if str(spec.get("signal", "")) == sig
                and any(str(spec.get("phase", "")).endswith("_" + pid) for pid in pids)
                and str(spec.get("kind", "")) not in PERIMETER_MOVEMENT_KINDS_ADAPTER
            )
            if total > 0.0:
                seed[link] = total

    # 그 링크 차로군의 직전 구간 녹색초. 커밋한 계획을 쓴다(러너가 그대로 적용한다).
    green_sec = _measured_green_sec_by_link(cfg, groups, previous_path)
    interval = _as_float(state_json.get("control_interval_sec"), 150.0)
    est: dict[str, float] = {}
    observed_used = 0
    for link in set(seed) | set(prev_est) | set(departures):
        g = green_sec.get(link, 0.0)
        obs = 0.0
        if g > 1.0 and link in departures:
            cycles = max(1.0, interval / max(1.0, _as_float(cfg.network.cycle_length, 150.0)))
            obs = departures[link] / (g * cycles) * 3600.0
        carried = decay * prev_est.get(link, seed.get(link, 0.0))
        value = max(obs, carried)
        if value > 0.0:
            est[link] = value
            if obs >= carried and obs > 0.0:
                observed_used += 1

    caps = dict(getattr(cfg.network, "movement_capacity_by_movement_veh_h", {}) or {})
    applied = _distribute_group_capacity_to_movements(cfg, groups, est, caps)
    if applied:
        setattr(cfg.network, "movement_capacity_by_movement_veh_h", caps)
    meta = {
        "measured_capacity_enabled": 1.0,
        "measured_capacity_links": float(len(est)),
        "measured_capacity_observed_links": float(observed_used),
        "measured_capacity_movements": float(applied),
        "measured_capacity_decay": float(decay),
    }
    for link, value in sorted(est.items()):
        meta[f"sat_est_{link}"] = float(value)
    return meta


def _approach_topology(groups) -> dict[str, tuple[str, tuple[str, ...]]]:
    """정지선 링크 -> (신호, 그 접근로가 받는 현시들). 링크 하나 = 접근로 하나다."""
    nema = {"NBT": "p1", "SBT": "p1", "NBL": "p2", "SBL": "p2",
            "EBT": "p3", "WBT": "p3", "EBL": "p4", "WBL": "p4"}
    pids: dict[str, set[str]] = {}
    sigs: dict[str, str] = {}
    for g in groups:
        link = str(g.get("stopline_link", ""))
        pid = nema.get(str(g.get("sg_name", "")).upper())
        sig = str(g.get("signal", ""))
        if link and pid and sig:
            pids.setdefault(link, set()).add(pid)
            sigs[link] = sig
    return {lk: (sigs[lk], tuple(sorted(v))) for lk, v in pids.items()}


def _measured_green_sec_by_link(cfg, groups, previous_path) -> dict[str, float]:
    """정지선 링크별 직전 구간 녹색초. 차로군의 SG 이름 -> 현시 -> 커밋 녹색."""
    nema = {"NBT": "p1", "SBT": "p1", "NBL": "p2", "SBL": "p2",
            "EBT": "p3", "WBT": "p3", "EBL": "p4", "WBL": "p4"}
    try:
        prev = json.loads(Path(previous_path).read_text(encoding="utf-8"))
        greens = {str(k): _as_float(v, 0.0) for k, v in _mapping(prev.get("green_times")).items()}
    except (OSError, ValueError):
        greens = {}
    # **합**이지 최대가 아니다. 이탈 계수는 링크 단위라 그 접근로 전체(좌·직·우)의
    # 방출을 센다. 한 링크에 차로군이 둘 붙으면(WBL+WBT) 두 현시의 녹색을 다 받는다.
    # 최대만 쓰면 분모가 작아 방류율이 과대해진다.
    out: dict[str, float] = {}
    seen: set[tuple[str, str]] = set()
    for g in groups:
        link = str(g.get("stopline_link", ""))
        pid = nema.get(str(g.get("sg_name", "")).upper())
        sig = str(g.get("signal", ""))
        if not link or pid is None or not sig or (link, pid) in seen:
            continue
        seen.add((link, pid))
        value = greens.get(f"{sig}_{pid}")
        if value is None:
            value = _as_float(g.get("green_sec"), 0.0)   # 첫 결정: 고정계획 녹색
        out[link] = out.get(link, 0.0) + float(value)
    return out


def _distribute_group_capacity_to_movements(cfg, groups, est, caps) -> int:
    """접근로 용량을 그 접근로 movement 들에 `beta` 비율로 나눈다(총량 보존)."""
    # 링크 하나 = 접근로 하나다. 그 접근로의 좌·직·우는 **같은 차로를 나눠 쓰므로**
    # 용량 총량을 공유한다. 현시(p1·p2)를 가로질러 배분해야 총량이 보존된다 —
    # 현시별로 각각 총량을 주면 그 접근로가 용량의 2배를 방류한다.
    by_key: dict[tuple[str, tuple[str, ...]], float] = {}
    for link, key in _approach_topology(groups).items():
        if link in est:
            by_key[key] = by_key.get(key, 0.0) + float(est[link])
    applied = 0
    for key, total in by_key.items():
        sig, pids = key
        members = [
            (m, max(0.0, _as_float(spec.get("beta"), 0.0)))
            for m, spec in (cfg.network.urban_movements or {}).items()
            if str(spec.get("signal", "")) == sig
            and any(str(spec.get("phase", "")).endswith("_" + pid) for pid in pids)
            and str(spec.get("kind", "")) not in PERIMETER_MOVEMENT_KINDS_ADAPTER
        ]
        if not members:
            continue
        weight = sum(w for _, w in members) or float(len(members))
        for m, w in members:
            share = (w / weight) if weight > 0 else 1.0 / len(members)
            caps[m] = float(total) * float(share)
            applied += 1
    return applied


def install_native_signal_structure(cfg, tuning: Mapping[str, Any]) -> dict[str, float]:
    """망의 **실제 신호 구조**(주기·녹색 예산)를 모델에 심는다. `urban.native_signal` 없으면 no-op.

    왜. 지금까지 컨트롤러는 모든 신호를 주기 150초 · 녹색 예산 138초(4현시)로 다뤘다.
    망의 실제 계획은 그렇지 않다.

        SC107/108/109   141      이미 일치 (live 3현시 -> 150-9)
        SC16            107      컨트롤러가 141 을 줘 **과잉 공급**
        SC5             246      p1 97 + p3 101 = 198 > 150 -> **동시 현시**
        SC7             205      동시 현시 + 주기 120

    링크 단위 분석에서 정체 최악 12개 중 10개가 SC5·SC6 이었다(SC6 은 SC5 하류).
    SC5 가 고정신호의 56%, SC7 이 69% 만 받고 있었다. 나머지 162개 링크는 무제어보다
    좋아졌는데 이 두 곳이 망 전체를 무너뜨린다.

    세 조각.

    (1) 신호별 주기. `cycle_length_by_signal` 에 `native_cycle_sec` 를 넣는다. SC7 이
        120초가 된다. 기반은 이미 있었고 매핑만 비어 있었다.

    (2) 신호별 녹색 예산. `min(계획 총합, C - N x clearance)`. SC16 이 141 -> 107 로
        내려간다. 상한을 두는 이유는 (3) 이다.

    (3) 동시 현시. `_phase_green_fraction` 이 현시를 **순차로 배치**하고
        `end = min(start + green, cycle)` 로 자르므로, 246초를 150초 주기에 넣으면 뒤쪽
        현시가 통째로 잘린다. 동시성을 제대로 넣으려면 "어느 현시가 겹치는지" 를 모델이
        알아야 하는데 그건 별건이다. 대신 **처리량 등가**로 근사한다 — 두 현시가 겹쳐
        켜지면 그 접근로의 시간당 처리량이 그만큼 는다. 그 신호 movement 들의 용량에
        `계획총합 / 예산` 을 곱한다(SC5 1.78, SC7 1.85). 근사임을 명시해 둔다.

    (3) 은 movement 용량 맵을 쓰므로 `install_movement_capacity_by_lanes` **뒤에** 불러야
    한다. 맵이 비어 있으면 전역 스칼라로 씨를 뿌린 뒤 곱한다.
    """
    section = _mapping(_mapping(tuning.get("urban")).get("native_signal"))
    _flag = section.get("enabled", False)
    _on = bool(_flag) if isinstance(_flag, (bool, int, float)) else         str(_flag).strip().lower() in {"1", "true", "yes", "on"}
    if not _on:
        return {"native_signal_structure_enabled": 0.0}
    # **측정값**을 쓴다. 유도(C - N x clearance)는 손실시간을 3초 x live현시수 로 고정하는데
    # 실측은 신호마다 전혀 다르다 — SC5 는 0초(항상 어딘가 녹색, 최대 6 SG 동시), SC16 은
    # 43초다. 유도를 쓰면 SC5 예산이 138(참값 150)이 되고 동시현시 배율의 분모까지 틀린다.
    src = WORKSPACE_ROOT / "outputs/signal_timeline_measured_20260821.json"
    if not src.is_file():
        return {"native_signal_structure_enabled": 0.0, "native_signal_source_missing": 1.0}
    measured = _mapping(json.loads(src.read_text(encoding="utf-8")).get("signals"))

    net = cfg.network
    cycles: dict[str, float] = {}
    budgets: dict[str, float] = {}
    factors: dict[str, float] = {}
    for signal in _controlled_signal_names(cfg):
        entry = _mapping(measured.get(str(signal)))
        if not entry:
            continue
        cyc = _as_float(entry.get("cycle_sec"), 0.0)
        green = _as_float(entry.get("green_sec"), 0.0)
        fac = _as_float(entry.get("concurrency_factor"), 1.0)
        if cyc > 0.0:
            cycles[str(signal)] = cyc
        if green > 0.0:
            budgets[str(signal)] = green
        if fac > 1.0 + 1.0e-9:
            factors[str(signal)] = fac

    if cycles:
        setattr(net, "cycle_length_by_signal", dict(cycles))
    if budgets:
        setattr(net, "effective_green_total_by_signal", dict(budgets))

    # (4) **죽은 현시**. 실 계획에서 녹색 0 인 현시가 있다 — SC7 p3 · SC16 p4 ·
    #     SC107 p1 · SC108 p2 · SC109 p1. 모델이 4현시로 강제하면 없는 현시에 녹색을
    #     주고, 그만큼이 실제 접근로에서 사라진다. `signal_live_phases` 는 이 경우를
    #     위해 만들어져 있었는데 매핑이 비어 있었다.
    #
    #     상한도 같이 풀린다. green_max 는 total - (live-1) x green_min 의 유도값이라
    #     3현시 141 이면 101 이어야 하는데 스칼라 78 이 걸려 SC108(88) · SC109(90) 의
    #     실계획을 재현조차 못 했다(`NetworkConfig.signal_green_max`).
    live_map = _native_live_phases_by_signal(cfg)
    if live_map:
        setattr(net, "live_phases_by_signal", dict(live_map))

    # 동시 현시 -> 처리량 등가 배율. 순차 배치 모델은 겹침을 담을 수 없으므로
    # 그 신호 movement 들의 용량에 곱한다(배율 = 계획 현시녹색 합 / 실제 녹색초).
    applied_factor = 0
    if factors:
        caps = dict(getattr(net, "movement_capacity_by_movement_veh_h", {}) or {})
        for movement, spec in (net.urban_movements or {}).items():
            if str(spec.get("kind", "")) in PERIMETER_MOVEMENT_KINDS_ADAPTER:
                continue
            caps.setdefault(movement, float(net.movement_capacity_veh_h))
        for movement, spec in (net.urban_movements or {}).items():
            if str(spec.get("kind", "")) in PERIMETER_MOVEMENT_KINDS_ADAPTER:
                continue
            f = factors.get(str(spec.get("signal", "")))
            if f is None:
                continue
            caps[movement] = float(caps[movement]) * float(f)
            applied_factor += 1
        setattr(net, "movement_capacity_by_movement_veh_h", caps)

    meta = {
        "native_signal_structure_enabled": 1.0,
        "native_signal_cycle_count": float(len(cycles)),
        "native_signal_budget_count": float(len(budgets)),
        "native_signal_concurrency_signals": float(len(factors)),
        "native_signal_concurrency_movements": float(applied_factor),
        "native_signal_dead_phase_signals": float(len(live_map)),
    }
    for sig, live in sorted(live_map.items()):
        meta[f"native_signal_live_phases_{sig}"] = float(len(live))
        meta[f"native_signal_green_max_{sig}"] = float(net.signal_green_max(sig))
    for sig, f in sorted(factors.items()):
        meta[f"native_signal_concurrency_factor_{sig}"] = float(f)
    return meta


def install_urban_stopline_storage(cfg, tuning: Mapping[str, Any]) -> dict[str, float]:
    """정지선 규모 저류를 유도해 cfg 에 주입한다. `urban.stopline_bay_m` 이 없으면 no-op.

    왜 필요한가. 기존 막힘 제약은 교차로간 링크(0.5~2.1 km, 링크당 중앙 431대) 저류를
    쓴다. 첨두에도 망 전체 4,500대가 185개 링크에 흩어져 점유율 10% 수준이라 제약이
    **절대 안 물린다** — 혼잡기 진단에 저류/막힘 항목이 하나도 안 뜬다. 그래서 모든 큐가
    녹색마다 완전히 비워지고, 참 큐에서 출발해도 150초에 400~550대를 과다 방류한다.
    부족분이 혼잡과 함께 커진다(t=600 -5 대 t=4800 -556).

    실제 막힘은 정지선 앞 대기공간과 좌회전 포켓에서 일어난다. 그 규모를 넣는다.

    유도. 산출물이 링크 길이와 jam 밀도를 들고 있어 차로수를 역산할 수 있다.

        lanes(L)    = storage(L) / (length_km(L) x jam_density)
        stopline(L) = lanes(L) x bay_km x jam_density
                    = storage(L) x bay_km / length_km(L)

    즉 링크 길이에 비례해 줄인다 — 짧은 링크는 덜 줄고 긴 링크는 많이 준다. 물리적으로
    맞다(정지선 대기공간은 링크 길이와 무관하게 일정하다).

    이건 방류율을 낮추는 대증요법(movement_capacity 1400->600)과 다르다. 그쪽은 모든
    movement 를 균일하게 굶겨 **movement 간 상대 비교를 왜곡**한다 — 신호제어가 쓰는 게
    정확히 그 상대 비교다. 이쪽은 혼잡할 때만, 막힌 곳에서만 물린다.
    """
    section = _mapping(_mapping(tuning.get("urban")).get("stopline"))
    bay_m = _as_float(section.get("bay_m"), 0.0)
    if bay_m <= 0.0:
        return {"urban_stopline_storage_enabled": 0.0}
    src = WORKSPACE_ROOT / "outputs/urban_storage_capacity_core17legs4b_20260819.json"
    if not src.is_file():
        return {"urban_stopline_storage_enabled": 0.0, "urban_stopline_storage_source_missing": 1.0}
    doc = json.loads(src.read_text(encoding="utf-8"))
    lengths = _mapping(doc.get("urban_link_length_km"))
    storages = _mapping(doc.get("urban_link_storage_veh"))
    bay_km = bay_m / 1000.0
    out: dict[str, float] = {}
    for link, cap in (cfg.network.urban_link_storage_veh or {}).items():
        base = _as_float(storages.get(link), _as_float(cap, 0.0))
        length_km = _as_float(lengths.get(link), 0.0)
        if base <= 0.0 or length_km <= 0.0:
            continue
        out[str(link)] = float(base) * bay_km / float(length_km)
    if not out:
        return {"urban_stopline_storage_enabled": 0.0, "urban_stopline_storage_empty": 1.0}
    setattr(cfg.network, "urban_stopline_storage_veh", out)
    vals = sorted(out.values())
    return {
        "urban_stopline_storage_enabled": 1.0,
        "urban_stopline_bay_m": float(bay_m),
        "urban_stopline_link_count": float(len(out)),
        "urban_stopline_storage_median_veh": float(vals[len(vals) // 2]),
        "urban_stopline_storage_min_veh": float(vals[0]),
        "urban_stopline_storage_max_veh": float(vals[-1]),
    }


def install_price_worker_bootstrap(controller, state_json, detector_mapping) -> dict[str, float]:
    """가격 롤아웃 워커가 되살려야 할 런타임 패치를 컨트롤러에 실어 보낸다.

    워커는 spawn 된 **새 인터프리터**라 이 어댑터가 모듈에 심은 몽키패치를 못 물려받는다.
    유실 대상은 `install_monitor_fixed_signal_runtime_patch` 의 `_phase_green_fraction`
    (5개 모듈) 하나다 — 캘리브레이션 v2 와 VSL/METANET 은 `cfg` 속성으로 들어가므로
    컨트롤러와 함께 피클되어 살아남는다.

    2026-08-20 실측(phasepar). 이걸 안 실어 보낸 병렬 런이 같은 입력 t=600 에서 직렬과
    다른 가격을 냈고(SC5 27%, SC6 부호 반전) SC1002·SC12·SC5 의 녹색을 8초씩 반대로
    커밋했다. green 채널에서만 갈린 것이 이 패치가 green->유량 변환 전용이라는 것과 맞는다.

    페이로드는 최소로 싣는다 — 설치 함수는 `state_json` 에서 `_network_path_from_state`
    로 경로 하나만 읽는다. 상태 전체를 실으면 워커마다 차량 기록을 통째로 피클한다.

    되살리기는 `PricedWuLinkStackelbergController.__setstate__` 가 한다. 실패하면 raise 해
    직렬 재실행 + 카운터로 떨어진다(조용한 경로 없음).
    """
    if int(getattr(controller, "price_parallel_workers", 0) or 0) <= 1:
        return {"price_worker_bootstrap_installed": 0.0}
    controller.price_worker_bootstrap = {
        "sys_path": str(WORKSPACE_ROOT),
        "module": "evaluation.controllers.vissim_stackelberg_adapter",
        "func": "install_monitor_fixed_signal_runtime_patch",
        "state_json": {"network_path": str(_network_path_from_state(state_json))},
        "detector_mapping": dict(detector_mapping or {}),
        "verify_module": "src.models.urban_queue_model",
        "verify_attr": "_vissim_original_phase_green_fraction",
    }
    return {"price_worker_bootstrap_installed": 1.0}


def _absolute_urban_step_start_sec(urban_step_index: int, duration_sec: float) -> float:
    """NumSim urban step indices are already based on absolute state.time_sec."""
    return int(urban_step_index) * float(duration_sec)


def _storage_links_for_observed_origin(cfg, origin: str) -> list[str]:
    net = cfg.network
    value = str(origin)
    if value in net.urban_link_storage_veh:
        return [value]
    storage = str(net.off_ramp_storage_link.get(value, ""))
    if storage and storage in net.urban_link_storage_veh:
        return [storage]
    return []


def _link_storage_split_fraction(cfg, origins: list[str], split_parameters: Mapping[str, Any]) -> float:
    storage_links: list[str] = []
    off_ramp_storage_links = {str(v) for v in cfg.network.off_ramp_storage_link.values()}
    for origin in origins:
        storage_links.extend(_storage_links_for_observed_origin(cfg, origin))
    if not storage_links:
        return 0.0
    if any(link in off_ramp_storage_links for link in storage_links):
        return float(split_parameters.get("offramp_storage_fraction", LOCAL_OBSERVATION_OFFRAMP_STORAGE_FRACTION))
    return float(split_parameters.get("internal_storage_fraction", LOCAL_OBSERVATION_INTERNAL_STORAGE_FRACTION))


def _queue_origin_filter_enabled() -> bool:
    """movement 큐를 그 링크의 저류에서 출발하는 것으로 좁힐지. 기본 꺼짐."""
    return str(os.environ.get("RW_QUEUE_ORIGIN_FILTER", "")).strip().lower() in {"1", "true", "on"}


def _lane_delay_correction_enabled() -> bool:
    """저류 통과지연을 차로수로 나눌지. 기본 꺼짐(RW_LANE_DELAY_CORRECTION)."""
    return str(os.environ.get("RW_LANE_DELAY_CORRECTION", "")).strip().lower() in {"1", "true", "on"}


_STORAGE_LANES_CACHE: dict[str, float] | None = None


def _storage_effective_lanes() -> dict[str, float]:
    """저류별 **길이가중 평균 차로수** = 용량 / (길이 × jam).

    용량이 `길이 × 차로 × jam` 으로 지어졌으므로 이 나눗셈은 항등식이고 측정이 아니다.
    저류가 여러 링크를 묶으면 정수로 안 떨어진다(중앙 2.69, 범위 1.00~8.37) - 대수를
    종방향 거리로 되돌리는 데 필요한 제수는 바로 이 길이가중 평균이라 그대로 쓴다.
    길이 근거가 없는 램프 저류 4개는 1.0(보정 없음)으로 남는다.
    """
    global _STORAGE_LANES_CACHE
    if _STORAGE_LANES_CACHE is not None:
        return _STORAGE_LANES_CACHE
    lanes: dict[str, float] = {}
    evidence = load_optional_json(str(STORAGE_CAPACITY_EVIDENCE_JSON))
    jam = _as_float(evidence.get("jam_density_veh_km_lane", 0.0))
    capacity = evidence.get("urban_link_storage_veh") or {}
    length_km = evidence.get("urban_link_length_km") or {}
    if jam > 0.0 and isinstance(capacity, Mapping) and isinstance(length_km, Mapping):
        for link, veh in capacity.items():
            km = _as_float(length_km.get(link, 0.0))
            if km > 0.0:
                lanes[str(link)] = max(1.0, _as_float(veh) / (km * jam))
    _STORAGE_LANES_CACHE = lanes
    return lanes


def _apply_lane_delay_correction(state, cfg, local_summary: dict) -> None:
    """저류 통과지연의 **차원 오류**를 링크별 속도 통로로 정확히 상쇄한다.

    plant 의 `_link_delay_steps` 는 큐 꼬리까지의 거리를
        distance_km = available[veh] × urban_avg_vehicle_length_m / 1000
    로 잡는데, `available` 은 **전 차로 합계 대수**다. 3차로 링크의 여유 300대는 종방향
    600 m 인데 산식은 1,800 m 로 본다. 실측 배수는 정확히 차로수(중앙 2.69, p90 4.04)라
    통과시간이 그만큼 길어지고, 중앙 지연이 MPC 지평(3스텝)을 넘겨 저류가 사실상 얼어붙는다.

    vendor 는 수정 금지라 거리는 못 건드린다. 대신 `urban_link_speed_kph` 가 이 산식
    **한 곳에서만** 쓰이므로(vendor/.../urban_queue_model.py:624) 속도에 차로수를 곱하면
    distance/speed 가 정확히 같은 값이 된다 - 근사가 아니라 항등이다. 그래서 이 필드는
    보정이 켜진 동안 "관측 속도"가 아니라 **유효 속도**를 담는다.

    하한(`OBSERVED_SPEED_DELAY_CAP_RATIO`)이 주입 뒤에 `max()` 로 걸리므로 하한을 여기서
    먼저 적용한 뒤 차로수를 곱한다. 그러면 vendor 의 `max()` 가 무해해지고 의도한 지연
    상한이 차로보정된 거리에 그대로 적용된다.
    """
    if not _lane_delay_correction_enabled():
        # 꺼짐도 **양성으로** 기록한다. 키가 없으면 "꺼져 있었다"와 "환경변수가 어댑터까지
        # 안 왔다"가 구별되지 않고, A/B 에서 ΔJ≈0 이 나왔을 때 그 둘을 사후에 가를 방법이
        # 없다. arm 이 실제로 무엇이었는지는 발사 의도가 아니라 디스크가 말해야 한다.
        local_summary["lane_delay_correction"] = {"enabled": False, "links_corrected": 0}
        return
    from src.models.urban_queue_model import OBSERVED_SPEED_DELAY_CAP_RATIO

    lanes_table = _storage_effective_lanes()
    nominal = max(_as_float(getattr(cfg.network, "urban_avg_speed_km_h", 50.0)), 1.0e-9)
    floor = nominal / max(float(OBSERVED_SPEED_DELAY_CAP_RATIO), 1.0e-9)
    applied = 0
    lane_weighted = 0.0
    for link in cfg.network.urban_link_storage_veh:
        key = str(link)
        lanes = lanes_table.get(key, 1.0)
        if lanes <= 1.0:
            continue
        observed = state.urban_link_speed_kph.get(key)
        base = max(_as_float(observed), floor) if observed is not None else nominal
        state.urban_link_speed_kph[key] = lanes * base
        applied += 1
        lane_weighted += lanes
    local_summary["lane_delay_correction"] = {
        "enabled": True,
        "links_corrected": applied,
        "links_without_length_evidence": sum(
            1 for link in cfg.network.urban_link_storage_veh if str(link) not in lanes_table
        ),
        "mean_lanes_applied": (lane_weighted / applied) if applied else 0.0,
        "evidence": STORAGE_CAPACITY_EVIDENCE_JSON.name,
    }


def _movement_origin(cfg, movement: str) -> str:
    spec = cfg.network.urban_movements.get(movement)
    if isinstance(spec, Mapping):
        return str(spec.get("origin", ""))
    return str(getattr(spec, "origin", "") or "")


def _observed_stopped_counts(state_json: Mapping[str, Any]) -> dict[str, float]:
    """큐 관측을 순간 표본에서 **직전 제어구간 창 집계**로 바꾼다(RW_QUEUE_WINDOW).

    왜. 제어주기 150 s 가 신호주기 150 s 와 같아 결정 시점이 항상 신호 위상의 같은
    지점에 떨어진다 — 무작위 잡음이 아니라 계통 편향이다. 실측(SC1, 무제어 고정계획):

        접근  결정시점  창평균  창최대
        N      15.3     11.0    27.7     (+39%)
        E       0.1      3.3    12.8     (-97%)
        W       0.1      1.4     5.2     (-93%)

    결정 시점이 동서 녹색 직후라 동서가 늘 빈 것으로 읽힌다. 리더가 쓰는 건 현시 간
    **상대** 큐라 이 편향이 그대로 배분 왜곡이 된다(남북:동서 = 99.3:0.7 -> 84:16).

    러너가 5초 스캔을 이미 돌리므로 창 집계에 COM 왕복이 안 붙는다. 필드가 없으면
    (스위치 꺼짐·구 상태 JSON) 순간값으로 폴백해 **비트 동일**하다.
    """
    # 기본은 꺼짐. `link_counts` 쪽과 같은 스위치를 써서 둘이 어긋나지 않게 한다 —
    # 하나만 창값이면 저류/큐 분할 비율이 뒤틀린다.
    mode = str(os.environ.get("RW_QUEUE_WINDOW_STAT", "")).strip().lower()
    if mode in {"mean", "max"}:
        key = f"link_stopped_counts_window_{mode}"
        windowed = _link_metric_from_local_observation(state_json, key)
        if windowed:
            samples = _as_float(
                _mapping(state_json.get("local_observation")).get("queue_window_samples"), 0.0
            )
            if samples >= 1.0:
                return windowed
    return _link_metric_from_local_observation(state_json, "link_stopped_counts")


def build_local_observation_summary(
    state_json: Mapping[str, Any],
    cfg,
    detector_mapping: Mapping[str, Any],
    calibration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert Vissim detector/local-zone counts into model-local queues.

    The Vissim runner may still use a fast whole-vehicle scan internally, but
    once the counts enter this function they are reduced through the detector
    mapping. Follower-visible state is therefore link/movement/agent scoped
    instead of aggregate global counts.
    """
    link_counts = _link_counts_from_local_observation(state_json)
    if not link_counts:
        return {}

    link_speeds_kph = _link_metric_from_local_observation(state_json, "link_speeds_kph")
    link_stopped_counts = _observed_stopped_counts(state_json)
    link_queue_tail_pos_m = _link_metric_from_local_observation(state_json, "link_queue_tail_pos_m")
    split_parameters = _observation_split_parameters(calibration)
    partition = _mapping(detector_mapping.get("link_partition"))
    exit_links = {str(value) for value in partition.get("monitor_only_exit_links", [])}
    freeway_bound_links = {str(value) for value in partition.get("freeway_bound_links", [])}
    freeway_links = {
        str(link) for link in _mapping(detector_mapping.get("freeway_link_to_model_link"))
    }
    ramp_links = {str(link) for link in _mapping(detector_mapping.get("ramp_link_to_queues"))}
    storage_fraction_by_link: dict[str, float] = {}
    queue_count_by_link: dict[str, float] = {}
    storage_count_by_link: dict[str, float] = {}
    storage_assigned_by_link: dict[str, float] = {}
    urban_link_storage_occupancy = {link: 0.0 for link in cfg.network.urban_link_storage_veh}
    # 저류별 **정지 대수**. 투영이 release 버퍼를 복원할 때 "이미 정지선에 도착한 몫" 과
    # "아직 이동 중인 몫" 을 가르는 근거다(traffic_state_from_vissim 의 버퍼 복원 참조).
    # 관측에서 나오므로 추정이 아니다.
    urban_link_storage_stopped = {link: 0.0 for link in cfg.network.urban_link_storage_veh}
    storage_requested_veh = 0.0
    storage_assigned_veh = 0.0
    storage_capacity_clipped_veh = 0.0
    # 관측 링크속도를 모델 storage 링크 키로 접기 위한 대수 가중 누산기(v3 N3-1b).
    speed_weight_by_storage: dict[str, float] = {}
    speed_moment_by_storage: dict[str, float] = {}
    # 링크별 저류 목록. 아래 movement 큐 분배가 "그 링크의 저류에서 출발하는 movement"
    # 로 좁힐 때 쓴다(RW_QUEUE_ORIGIN_FILTER).
    storage_links_by_link: dict[str, list[str]] = {}
    for link, count in link_counts.items():
        if link in freeway_links or link in ramp_links or link in exit_links:
            storage_fraction_by_link[str(link)] = 0.0
            storage_count_by_link[str(link)] = 0.0
            queue_count_by_link[str(link)] = 0.0
            storage_assigned_by_link[str(link)] = 0.0
            continue
        origins = [
            str(value)
            for value in detector_mapping.get("link_to_origins", {}).get(str(link), [])
        ]
        storage_fraction = _link_storage_split_fraction(cfg, origins, split_parameters)
        # movement 매핑이 없는 링크는 queue_count 가 갈 데가 없어 그냥 증발한다.
        # 아래 link_to_movements 루프가 그 링크를 아예 안 도는 탓이다.
        # 실측 2026-08-05: 관측된 배정 링크 952개 중 **882개**가 매핑이 없어
        # 1,415 대의 queue 분이 사라졌다(도시부 포착률이 50.7% 에서 안 올라간 원인).
        # 그 882개는 신호두 링크가 아니라 링크 본체다 — 정지선 대기행렬이 아니라
        # 링크 저류가 물리적으로 맞으므로 전량 저류로 보낸다.
        if not (detector_mapping.get("link_to_movements", {}) or {}).get(str(link)):
            storage_fraction = 1.0
        storage_fraction_by_link[str(link)] = float(storage_fraction)
        storage_count = max(0.0, count * storage_fraction)
        queue_count = max(0.0, count - storage_count)
        storage_count_by_link[str(link)] = float(storage_count)
        queue_count_by_link[str(link)] = float(queue_count)
        storage_links: list[str] = []
        for origin in origins:
            for storage_link in _storage_links_for_observed_origin(cfg, origin):
                if storage_link not in storage_links:
                    storage_links.append(storage_link)
        storage_links_by_link[str(link)] = list(storage_links)
        # 관측 속도는 **표본이 있는 링크만** 기여한다(v3 N3-1b). VBS 의 링크속도는
        # `speed_sum / count` 라 표본이 없으면 0 인데, 그 0 은 "정지" 가 아니라
        # "관측 없음" 이다. count=0 이거나 속도 키 자체가 없으면 건너뛴다.
        if count > 0.0 and str(link) in link_speeds_kph and storage_links:
            observed_kph = float(link_speeds_kph[str(link)])
            for storage_link in storage_links:
                speed_weight_by_storage[storage_link] = (
                    speed_weight_by_storage.get(storage_link, 0.0) + float(count)
                )
                speed_moment_by_storage[storage_link] = (
                    speed_moment_by_storage.get(storage_link, 0.0)
                    + float(count) * observed_kph
                )
        storage_requested_veh += storage_count
        storage_assigned_by_link[str(link)] = 0.0
        if storage_count > 0.0 and storage_links:
            share = storage_count / len(storage_links)
            for storage_link in storage_links:
                capacity = float(cfg.network.urban_link_storage_veh.get(storage_link, 0.0))
                current = urban_link_storage_occupancy.get(storage_link, 0.0)
                assigned = max(0.0, min(share, capacity - current))
                urban_link_storage_occupancy[storage_link] = current + assigned
                storage_assigned_by_link[str(link)] += assigned
                storage_assigned_veh += assigned
                storage_capacity_clipped_veh += max(0.0, share - assigned)
                # 배정된 몫 중 정지 비율만큼을 정지 대수로 같이 옮긴다.
                if count > 0.0 and assigned > 0.0:
                    stopped_share = min(1.0, max(0.0, float(link_stopped_counts.get(str(link), 0.0)) / count))
                    urban_link_storage_stopped[storage_link] = (
                        urban_link_storage_stopped.get(storage_link, 0.0) + assigned * stopped_share
                    )

    movement_queue = {movement: 0.0 for movement in cfg.network.urban_movements}
    movement_assigned_by_link: dict[str, float] = {}
    for link, entries in detector_mapping.get("link_to_movements", {}).items():
        count = queue_count_by_link.get(str(link), link_counts.get(str(link), 0.0))
        if count <= 0.0 or not isinstance(entries, list):
            continue
        movement_assigned_by_link[str(link)] = 0.0
        # 배정 대상만 먼저 추린다. 두 가지를 고친다(둘 다 RW_QUEUE_ORIGIN_FILTER 로 켠다).
        #
        # (a) **링크와 무관한 movement 로 흩뿌리지 않는다.** detector_mapping 의
        #     link_to_movements 는 링크별이 아니라 **교차로별**이다 - SC1 의 네 접근 링크가
        #     전부 SC1 의 movement 전체를 받는다. 그래서 SC15 쪽 접근에 선 차가 SC107 /
        #     SC9001 / SC11 쪽 큐로도 나뉜다. 62개 링크가 이 상태이고 분수 귀속으로
        #     설명되는 것은 2개뿐이다. 접근 링크에 선 차는 **그 링크의 저류에서 출발하는**
        #     movement 의 큐다 - origin 으로 좁힌다.
        #
        # (b) **건너뛴 movement 몫이 증발하지 않게 한다.** 옛 코드는 weight_sum 을 전체
        #     entries 로 잡고 `movement not in movement_queue` 인 것을 건너뛰어서, 배정
        #     총합이 count 에 못 미쳤다. 모델에 없는 off-ramp movement 를 가리키는 링크가
        #     8개 있고(D_offW_to_N 등) 그만큼 질량이 사라진다(관측의 0.57%).
        usable = [
            item
            for item in entries
            if isinstance(item, Mapping) and str(item.get("movement", "")) in movement_queue
        ]
        if _queue_origin_filter_enabled():
            allowed = set(storage_links_by_link.get(str(link)) or [])
            if allowed:
                scoped = [
                    item
                    for item in usable
                    if str(_movement_origin(cfg, str(item.get("movement", "")))) in allowed
                ]
                # origin 이 하나도 안 맞으면 좁히지 않는다 - 질량을 버리는 것보다 낫다.
                if scoped:
                    usable = scoped
        weight_sum = sum(max(0.0, _as_float(item.get("weight", 0.0))) for item in usable)
        if weight_sum <= 1.0e-9:
            weight_sum = float(len(usable)) if usable else 1.0
        for item in usable:
            movement = str(item.get("movement", ""))
            weight = max(0.0, _as_float(item.get("weight", 1.0)))
            assigned = count * weight / weight_sum
            movement_queue[movement] += assigned
            movement_assigned_by_link[str(link)] += assigned

    ramp_queue = {ramp: 0.0 for ramp in cfg.network.ramps}
    for link, ramps in detector_mapping.get("ramp_link_to_queues", {}).items():
        count = link_counts.get(str(link), 0.0)
        if count <= 0.0 or not isinstance(ramps, list) or not ramps:
            continue
        share = count / len(ramps)
        for ramp in ramps:
            ramp_key = str(ramp)
            if ramp_key in ramp_queue:
                ramp_queue[ramp_key] += share

    # Legacy boundary_queue is kept for diagnostics/compatibility. The actual
    # urban signal queues above are the follower-visible queue state.
    boundary_queue: dict[str, float] = {}
    for link, key in detector_mapping.get("boundary_link_to_queue", {}).items():
        qkey = str(key)
        boundary_queue[qkey] = boundary_queue.get(qkey, 0.0) + link_counts.get(str(link), 0.0)

    agents: dict[str, Any] = {}
    for agent_id, spec in detector_mapping.get("agents", {}).items():
        if not isinstance(spec, Mapping):
            continue
        visible_links = [str(v) for v in spec.get("visible_links", [])]
        visible_movements = [str(v) for v in spec.get("visible_movements", [])]
        visible_ramps = [str(v) for v in spec.get("visible_ramps", [])]
        agent_summary = {
            "visible_links": visible_links,
            "visible_movements": visible_movements,
            "visible_ramps": visible_ramps,
            "link_counts": {link: link_counts.get(link, 0.0) for link in visible_links},
            "link_speeds_kph": {link: link_speeds_kph.get(link, 0.0) for link in visible_links},
            "link_stopped_counts": {
                link: link_stopped_counts.get(link, 0.0) for link in visible_links
            },
            "link_queue_tail_pos_m": {
                link: link_queue_tail_pos_m.get(link, 0.0) for link in visible_links
            },
            "movement_queue": {
                movement: movement_queue.get(movement, 0.0)
                for movement in visible_movements
            },
            "ramp_queue": {
                ramp: ramp_queue.get(ramp, 0.0)
                for ramp in visible_ramps
            },
        }
        if "control_enabled" in spec:
            agent_summary["control_enabled"] = bool(spec.get("control_enabled", True))
        if "monitoring_only" in spec:
            agent_summary["monitoring_only"] = bool(spec.get("monitoring_only", False))
        agents[str(agent_id)] = agent_summary

    represented_by_link: dict[str, float] = {}
    unrepresented_by_link: dict[str, float] = {}
    exit_excluded_by_link: dict[str, float] = {}
    for link, count in link_counts.items():
        if link in freeway_links or link in ramp_links:
            represented = count
        elif link in exit_links:
            represented = 0.0
            if count > 1.0e-9:
                exit_excluded_by_link[link] = count
        else:
            represented = min(
                count,
                storage_assigned_by_link.get(link, 0.0)
                + movement_assigned_by_link.get(link, 0.0),
            )
        represented_by_link[link] = represented
        missing = max(0.0, count - represented)
        if missing > 1.0e-9 and link not in exit_links:
            unrepresented_by_link[link] = missing

    # storage 링크별 관측 평균속도[km/h] — `TrafficState.urban_link_speed_kph` 로 간다.
    # 표본이 없는 storage 링크는 **항목 자체를 만들지 않는다**(모델이 전역 상수로 폴백).
    urban_link_speed_kph = {
        storage_link: float(speed_moment_by_storage[storage_link] / weight)
        for storage_link, weight in speed_weight_by_storage.items()
        if weight > 1.0e-9
    }

    positive_speeds = [
        speed
        for link, speed in link_speeds_kph.items()
        if link_counts.get(link, 0.0) > 0.0 and speed > 0.0
    ]
    weighted_speed_count = sum(
        link_counts.get(link, 0.0)
        for link, speed in link_speeds_kph.items()
        if speed > 0.0
    )
    weighted_speed_sum = sum(
        speed * link_counts.get(link, 0.0)
        for link, speed in link_speeds_kph.items()
        if speed > 0.0
    )
    input_vehicle_count = float(sum(link_counts.values()))
    represented_vehicle_count = float(sum(represented_by_link.values()))
    exit_excluded_vehicle_count = float(sum(exit_excluded_by_link.values()))
    total_vehicle_count = max(input_vehicle_count, _as_float(state_json.get("total_vehicles"), input_vehicle_count))
    local_observation = _mapping(state_json.get("local_observation"))
    unobservable_vehicle_count = max(
        0.0,
        _as_float(
            local_observation.get("unobservable_vehicle_count"),
            total_vehicle_count - input_vehicle_count,
        ),
    )
    projection_diagnostics = {
        "total_vehicle_count_veh": total_vehicle_count,
        "input_link_vehicle_count_veh": input_vehicle_count,
        "represented_vehicle_count_veh": represented_vehicle_count,
        "unrepresented_vehicle_count_veh": float(sum(unrepresented_by_link.values())),
        "exit_excluded_vehicle_count_veh": exit_excluded_vehicle_count,
        "unobservable_vehicle_count_veh": unobservable_vehicle_count,
        "mass_balance_error_veh": float(
            total_vehicle_count
            - represented_vehicle_count
            - exit_excluded_vehicle_count
            - unobservable_vehicle_count
        ),
        "freeway_observation_vehicle_count_veh": float(
            sum(link_counts.get(link, 0.0) for link in freeway_links)
        ),
        "ramp_observation_vehicle_count_veh": float(
            sum(link_counts.get(link, 0.0) for link in ramp_links)
        ),
        "freeway_bound_vehicle_count_veh": float(
            sum(link_counts.get(link, 0.0) for link in freeway_bound_links)
        ),
        "storage_requested_veh": float(storage_requested_veh),
        "storage_assigned_veh": float(storage_assigned_veh),
        "storage_capacity_clipped_veh": float(storage_capacity_clipped_veh),
        "movement_queue_assigned_veh": float(sum(movement_assigned_by_link.values())),
        "ramp_queue_assigned_veh": float(sum(ramp_queue.values())),
        "boundary_queue_assigned_veh": float(sum(boundary_queue.values())),
        "input_link_count": len(link_counts),
        "unrepresented_link_count": len(unrepresented_by_link),
        "exit_excluded_link_count": len(exit_excluded_by_link),
        "link_speed_observed_count": len(positive_speeds),
        "urban_link_speed_observed_count": len(urban_link_speed_kph),
        "link_stopped_vehicle_count_veh": float(sum(link_stopped_counts.values())),
        "link_queue_tail_observed_count": sum(
            1 for value in link_queue_tail_pos_m.values() if value > 0.0
        ),
        "observed_mean_link_speed_kph": (
            float(weighted_speed_sum / weighted_speed_count)
            if weighted_speed_count > 1.0e-9
            else 0.0
        ),
    }

    return {
        "mode": "detector_local_v2_storage_split",
        "link_counts": link_counts,
        "link_speeds_kph": link_speeds_kph,
        "link_stopped_counts": link_stopped_counts,
        "link_queue_tail_pos_m": link_queue_tail_pos_m,
        "queue_count_by_link": queue_count_by_link,
        "storage_count_by_link": storage_count_by_link,
        "storage_fraction_by_link": storage_fraction_by_link,
        "urban_movement_queue": movement_queue,
        "urban_link_storage_occupancy": urban_link_storage_occupancy,
        "urban_link_storage_stopped": urban_link_storage_stopped,
        "urban_link_speed_kph": urban_link_speed_kph,
        "ramp_queue": ramp_queue,
        "boundary_queue": boundary_queue,
        "projection_diagnostics": projection_diagnostics,
        "unrepresented_by_link": unrepresented_by_link,
        "exit_excluded_by_link": exit_excluded_by_link,
        "agents": agents,
        "split_parameters": {
            "internal_storage_fraction": float(split_parameters["internal_storage_fraction"]),
            "offramp_storage_fraction": float(split_parameters["offramp_storage_fraction"]),
        },
    }


def _movement_allowed_storage_links(cfg, movements: set[str]) -> set[str]:
    allowed: set[str] = set()
    for movement in movements:
        spec = cfg.network.urban_movements.get(movement, {})
        for field in ("origin", "destination", "receiving_link"):
            value = str(spec.get(field, ""))
            if value:
                allowed.add(value)
        ramp = str(spec.get("ramp", ""))
        if ramp:
            for linked in cfg.network.on_ramp_to_movement.get(ramp, []):
                linked_spec = cfg.network.urban_movements.get(linked, {})
                receiving = str(linked_spec.get("receiving_link", ""))
                if receiving:
                    allowed.add(receiving)
        off_ramp = str(spec.get("off_ramp", ""))
        if off_ramp:
            storage = str(cfg.network.off_ramp_storage_link.get(off_ramp, ""))
            if storage:
                allowed.add(storage)
    return allowed


def mask_state_for_agent(state, cfg, agent):
    """Return an agent-local state view for Vissim local-information runs.

    This is a runtime guard around the existing Numerical-Sim distributed
    coordinator. It keeps the plant state global for the leader, but masks the
    state object seen by each follower solve.
    """
    masked = state.copy()
    net = cfg.network
    kind = str(getattr(agent, "kind", ""))

    allowed_movements = set(str(m) for m in getattr(agent, "movements", ()) or ())
    allowed_ramps = set(str(r) for r in getattr(agent, "ramps", ()) or ())
    allowed_off_ramps = set(str(r) for r in getattr(agent, "off_ramps", ()) or ())
    allowed_storage = _movement_allowed_storage_links(cfg, allowed_movements)
    for off_ramp in allowed_off_ramps:
        storage = str(net.off_ramp_storage_link.get(off_ramp, ""))
        if storage:
            allowed_storage.add(storage)

    if kind == "urban":
        masked.urban_movement_queue = {
            key: (float(value) if key in allowed_movements else 0.0)
            for key, value in masked.urban_movement_queue.items()
        }
        masked.ramp_queue = {
            key: (float(value) if key in allowed_ramps else 0.0)
            for key, value in masked.ramp_queue.items()
        }
        boundary_keys = {
            str(net.urban_movements.get(movement, {}).get(field, ""))
            for movement in allowed_movements
            for field in ("origin", "destination")
        }
        masked.boundary_queue = {
            key: (float(value) if key in boundary_keys else 0.0)
            for key, value in masked.boundary_queue.items()
        }
        masked.urban_link_storage = {
            key: (
                float(value)
                if key in allowed_storage
                else float(net.urban_link_storage_veh.get(key, value))
            )
            for key, value in masked.urban_link_storage.items()
        }
        masked.mainline_origin_queue = {key: 0.0 for key in masked.mainline_origin_queue}
        # Urban followers should not directly inspect global freeway density;
        # freeway influence, if enabled, arrives through the coupling response.
        masked.freeway_density = {
            link: [0.0 for _ in values]
            for link, values in masked.freeway_density.items()
        }
        masked.freeway_speed = {
            link: [float(net.v_free) for _ in values]
            for link, values in masked.freeway_speed.items()
        }
        masked.refresh_freeway_flow(net)
        return masked

    if kind == "freeway":
        link = str(getattr(agent, "link", ""))
        segment_index = int(getattr(agent, "segment_index", -1))
        masked.urban_movement_queue = {key: 0.0 for key in masked.urban_movement_queue}
        masked.boundary_queue = {key: 0.0 for key in masked.boundary_queue}
        masked.ramp_queue = {
            key: (float(value) if key in allowed_ramps else 0.0)
            for key, value in masked.ramp_queue.items()
        }
        masked.urban_link_storage = {
            key: (
                float(value)
                if key in allowed_storage
                else float(net.urban_link_storage_veh.get(key, value))
            )
            for key, value in masked.urban_link_storage.items()
        }
        masked.mainline_origin_queue = {
            key: (float(value) if key == link else 0.0)
            for key, value in masked.mainline_origin_queue.items()
        }
        for model_link, values in list(masked.freeway_density.items()):
            speeds = list(masked.freeway_speed.get(model_link, [float(net.v_free) for _ in values]))
            densities = list(values)
            if model_link != link:
                masked.freeway_density[model_link] = [0.0 for _ in densities]
                masked.freeway_speed[model_link] = [float(net.v_free) for _ in densities]
                continue
            for i in range(len(densities)):
                if i != segment_index:
                    densities[i] = 0.0
                    if i < len(speeds):
                        speeds[i] = float(net.v_free)
            masked.freeway_density[model_link] = densities
            masked.freeway_speed[model_link] = speeds
        masked.refresh_freeway_flow(net)
        return masked

    return masked


def install_local_observation_runtime_guards() -> None:
    """Patch distributed follower solves to receive agent-masked state views."""
    from src.controllers import distributed_coordinator as dc

    cls = dc.DistributedCoordinator
    if getattr(cls, "_vissim_local_observation_guard_installed", False):
        return

    original_urban = cls._solve_urban_agent
    original_freeway = cls._solve_freeway_agent

    def guarded_urban(self, agent, state, leader, forecast, freeway_response, current, allocation_plan, coupling):
        return original_urban(
            self,
            agent,
            mask_state_for_agent(state, self.cfg, agent),
            leader,
            forecast,
            freeway_response,
            current,
            allocation_plan,
            coupling,
        )

    def guarded_freeway(self, agent, state, leader, forecast, current, coupling):
        return original_freeway(
            self,
            agent,
            mask_state_for_agent(state, self.cfg, agent),
            leader,
            forecast,
            current,
            coupling,
        )

    cls._solve_urban_agent = guarded_urban
    cls._solve_freeway_agent = guarded_freeway
    cls._vissim_local_observation_guard_installed = True


def install_vissim_calibration_runtime_patches(cfg, calibration: Mapping[str, Any]) -> dict[str, float]:
    """Install Vissim-specific runtime patches without editing Numerical-Sim sources.

    This adapter owns Vissim-only physical corrections so that the Desktop
    Numerical-Sim source tree can stay untouched. The v2 patches are:

    * non-uniform freeway segment lengths from the VSL/control-segment geometry;
    * off-ramp combined spillback capacity. The stock Numerical-Sim function
      adds all downstream turning-movement storage capacities, which
      double-counts shared Vissim approach space for this hypothetical network.
      Calibration v2 replaces that with explicit per-off-ramp physical capacity.
    """
    metadata: dict[str, float] = {}
    physical = _mapping(calibration.get("physical_inventory"))
    length_profile = _segment_length_profile_km(calibration)
    if length_profile:
        setattr(cfg.network, "freeway_segment_length_profile_km", length_profile)
        lengths = [length for values in length_profile.values() for length in values]
        metadata.update({
            "calibration_freeway_segment_length_profile_applied": 1.0,
            "calibration_freeway_segment_length_count": float(len(lengths)),
            "calibration_freeway_segment_length_min_km": float(min(lengths)),
            "calibration_freeway_segment_length_max_km": float(max(lengths)),
            "calibration_freeway_segment_length_mean_km": float(sum(lengths) / len(lengths)),
        })
        try:
            from src.models import state as state_module

            TrafficState = state_module.TrafficState
            if not hasattr(TrafficState, "_vissim_original_freeway_vehicle_count_by_link"):
                TrafficState._vissim_original_freeway_vehicle_count_by_link = (
                    TrafficState.freeway_vehicle_count_by_link
                )
            if not hasattr(TrafficState, "_vissim_original_total_freeway_vehicles"):
                TrafficState._vissim_original_total_freeway_vehicles = TrafficState.total_freeway_vehicles

            def calibrated_freeway_vehicle_count_by_link(self, net):
                self.ensure_freeway_lane_profile(net)
                out: dict[str, list[float]] = {}
                lane_profile = getattr(self, "freeway_lanes", {})
                profile = getattr(net, "freeway_segment_length_profile_km", {})
                for link in net.freeway_links:
                    key = str(link)
                    densities = [float(value) for value in self.freeway_density.get(key, [])]
                    raw_lengths = profile.get(key, []) if isinstance(profile, Mapping) else []
                    lengths = [
                        max(1.0e-6, _as_float(value))
                        for value in raw_lengths
                    ] if isinstance(raw_lengths, list) else []
                    base = max(1.0e-6, float(getattr(net, "freeway_segment_length_km", 0.58)))
                    if len(lengths) < len(densities):
                        lengths = lengths + [base] * (len(densities) - len(lengths))
                    raw_lanes = lane_profile.get(key, []) if isinstance(lane_profile, Mapping) else []
                    counts = []
                    for i, rho in enumerate(densities):
                        lanes = (
                            max(1.0, _as_float(raw_lanes[i], getattr(net, "freeway_lanes", 2)))
                            if i < len(raw_lanes)
                            else max(1.0, float(getattr(net, "freeway_lanes", 2)))
                        )
                        counts.append(max(0.0, float(rho)) * lengths[i] * lanes)
                    out[key] = counts
                return out

            def calibrated_total_freeway_vehicles(self, net) -> float:
                return float(
                    sum(
                        sum(max(0.0, float(value)) for value in values)
                        for values in calibrated_freeway_vehicle_count_by_link(self, net).values()
                    )
                )

            TrafficState.freeway_vehicle_count_by_link = calibrated_freeway_vehicle_count_by_link
            TrafficState.total_freeway_vehicles = calibrated_total_freeway_vehicles
            metadata["calibration_state_vehicle_count_patch_installed"] = 1.0
        except Exception:
            metadata["calibration_state_vehicle_count_patch_installed"] = 0.0

    capacity_map = _mapping(physical.get("off_ramp_combined_capacity_veh"))
    if not capacity_map:
        return metadata

    calibrated_capacity = {
        str(off_ramp): max(0.0, _as_float(value))
        for off_ramp, value in capacity_map.items()
    }
    if not calibrated_capacity:
        return metadata

    from src.controllers import spillback_constraints

    if not hasattr(spillback_constraints, "_vissim_original_offramp_combined_capacity_veh"):
        spillback_constraints._vissim_original_offramp_combined_capacity_veh = (
            spillback_constraints.offramp_combined_capacity_veh
        )
    original = spillback_constraints._vissim_original_offramp_combined_capacity_veh

    def calibrated_offramp_combined_capacity_veh(cfg_arg, off_ramp: str) -> float:
        key = str(off_ramp)
        if key in calibrated_capacity:
            return float(calibrated_capacity[key])
        return float(original(cfg_arg, off_ramp))

    spillback_constraints.offramp_combined_capacity_veh = calibrated_offramp_combined_capacity_veh

    # Usually unnecessary because imported assess_* functions keep their module
    # globals, but patch a direct attribute too if a future module imports it.
    try:
        import src.controllers.distributed_coordinator as distributed_coordinator

        if hasattr(distributed_coordinator, "offramp_combined_capacity_veh"):
            distributed_coordinator.offramp_combined_capacity_veh = calibrated_offramp_combined_capacity_veh
    except Exception:
        pass

    capacities = []
    for off_ramp in getattr(cfg.network, "off_ramps", []):
        capacities.append(calibrated_offramp_combined_capacity_veh(cfg, str(off_ramp)))
    metadata.update({
        "calibration_offramp_capacity_patch_installed": 1.0,
        "calibration_offramp_capacity_min_veh": float(min(capacities)) if capacities else 0.0,
        "calibration_offramp_capacity_max_veh": float(max(capacities)) if capacities else 0.0,
        "calibration_offramp_capacity_total_veh": float(sum(capacities)),
    })
    return metadata


def repo_imports(repo_root: Path):
    expected_root = repo_root.resolve()
    existing_src = sys.modules.get("src")
    existing_file = Path(str(getattr(existing_src, "__file__", ""))) if existing_src is not None else None
    if existing_file and existing_file.is_file() and not existing_file.resolve().is_relative_to(expected_root):
        raise RuntimeError(
            f"preloaded src package is outside NUMSIM_REPO_ROOT: {existing_file} not under {expected_root}"
        )
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.controllers.stackelberg_mpc import StackelbergMPCController
    from src.models.demand import DemandStep
    from src.models.state import ControlAction, ExperimentConfig, TrafficState, segment_vsl

    for module_name in ("src.controllers.stackelberg_mpc", "src.models.demand", "src.models.state"):
        module_path = Path(str(getattr(sys.modules[module_name], "__file__", ""))).resolve()
        if not module_path.is_relative_to(expected_root):
            raise RuntimeError(
                f"imported {module_name} from {module_path}, expected under {expected_root}"
            )

    return StackelbergMPCController, DemandStep, ControlAction, ExperimentConfig, TrafficState, segment_vsl


def calibration_to_config_overrides(calibration: Mapping[str, Any]) -> dict[str, Any]:
    network = _calibration_child(calibration, "operational", "network")
    ramp = _calibration_child(calibration, "operational", "ramp_metering")
    signal = _calibration_child(calibration, "operational", "signal")
    mfd = _calibration_child(calibration, "operational", "urban_mfd")
    physical = _mapping(calibration.get("physical_inventory"))

    d_map = ramp.get("D_green_to_release_vph_initial_mpc", {})
    f_map = ramp.get("F_green_to_release_vph_raw", {})
    d_cap = max((float(v) for v in d_map.values()), default=1500.0) if isinstance(d_map, Mapping) else 1500.0
    f_cap = max((float(v) for v in f_map.values()), default=1500.0) if isinstance(f_map, Mapping) else 1500.0
    if str(ramp.get("F_status", "")).lower() == "invalid_for_physical_metering_fit":
        # F is not a valid green-to-release metering curve. Use only the
        # full-green observed discharge as a conservative plant cap; do not
        # optimize against the non-monotone raw maximum.
        f_cap = _release_at_largest_green(f_map, f_cap)

    out: dict[str, Any] = {
        "network": {
            "v_free": float(network.get("v_free_kph", 100.0)),
            "rho_crit": float(network.get("rho_crit_veh_km_lane", 33.5)),
            # 지수형 속도-밀도식 V(rho)=v_free*exp(-(1/a)*(rho/rho_crit)^a)의 형상 a.
            # 키가 없는 구 캘리브레이션 파일은 NetworkConfig 기본값 1.867을 그대로 받는다(비트 동일).
            "metanet_a_m": float(network.get("desired_speed_shape_a", 1.867)),
            "freeway_capacity_veh_h": float(network.get("freeway_capacity_veh_h", 4000.0)),
            "lost_time": float(signal.get("recommended_initial_lost_time_sec", 8.0)),
            "movement_capacity_veh_h": float(
                signal.get("recommended_initial_saturation_flow_vph_approach", 1400.0)
            ),
            "ramp_capacity_veh_h": {
                "R_D_W": float(d_cap),
                "R_D_E": float(d_cap),
                "R_F_W": float(f_cap),
                "R_F_E": float(f_cap),
            },
        },
        "leader": {
            "N_P_crit_veh": float(mfd.get("N_P_crit_veh_initial", 509.448830418254)),
        },
    }
    length_profile = _segment_length_profile_km(calibration)
    if length_profile:
        lengths = [length for values in length_profile.values() for length in values]
        if lengths:
            out["network"]["freeway_segment_length_km"] = float(sum(lengths) / len(lengths))

    storage_capacity: dict[str, float] = {}
    for key in (
        "urban_link_storage_capacity_veh",
        "on_ramp_storage_capacity_veh",
        "off_ramp_storage_capacity_veh",
    ):
        for link, value in _mapping(physical.get(key)).items():
            storage_capacity[str(link)] = max(0.0, _as_float(value))
    if storage_capacity:
        out["network"]["urban_link_storage_veh"] = storage_capacity

    for scalar_key in ("boundary_queue_max_veh", "ramp_queue_max_veh"):
        if scalar_key in physical:
            out["network"][scalar_key] = max(0.0, _as_float(physical.get(scalar_key)))
    return out


def tuning_to_config_overrides(tuning: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(tuning.get("config_overrides"), Mapping):
        out = deep_update(out, tuning["config_overrides"])
    for section in ("network", "mpc", "leader", "freeway_follower", "urban_follower"):
        if isinstance(tuning.get(section), Mapping):
            out = deep_update(out, {section: tuning[section]})
    return out


def adapter_actuation_settings(calibration: Mapping[str, Any], tuning: Mapping[str, Any]) -> dict[str, Any]:
    ramp = _calibration_child(calibration, "operational", "ramp_metering")
    actuation = {
        "D_green_to_release_vph": ramp.get("D_green_to_release_vph_initial_mpc", {}),
        "F_green_to_release_vph": ramp.get("F_green_to_release_vph_raw", {}),
        "F_ramp_mode": "always_green",
    }
    if isinstance(tuning.get("actuation"), Mapping):
        actuation = deep_update(actuation, tuning["actuation"])
    f_status = str(ramp.get("F_status", "")).lower()
    allow_invalid = bool(actuation.get("allow_invalid_F_metering", False))
    if f_status == "invalid_for_physical_metering_fit" and not allow_invalid:
        actuation["F_ramp_mode"] = "always_green"
        actuation["F_ramp_invalid_guard_active"] = True
        actuation["F_ramp_guard_reason"] = f_status
    return actuation


# ---------------------------------------------------------------------------
# P-Stack flagship (2026-07-31): NumSim flagship-ms-adapt-clean(HEAD 7f10393)의
# 최종 P-Stack(P-STACK-WU-FAITHFUL-ALLPRICE-JOINT) 운영점을 `pstack-flagship`
# 모드로 이식한 구간. 기준 원문(레시피 문서와 다르면 러너가 정답):
#   NumSim-mine/work/run_claude_style_five_controller.py
#     - make_controller ALLPRICE-JOINT 분기 L244-316 (BIAS_SAMPLE L268-273 포함)
#     - env→cfg 번역 L560-726 (METER_BOX/VSL_BOX/BOX_WALK/NP_PD_ITER/NP_BIAS/FAR_*)
#     - SEG13 L829-844, SUP_PFO L925-959·L1151-1176, FAR_GATE L1001-1099,
#       MS_ADAPT L1018-1026·L1106-1116
#   NumSim-mine/work/run_job.sh (플래그십 env 고정값, NASH_SMAX=10)
# 어댑터는 결정 1회마다 재기동되므로 러너 루프의 스텝 간 상태(직전 링크평균 밀도,
# MS 래치, fargate 래치)는 out-action-json 옆 사이드카 JSON에 영속화한다.
# ---------------------------------------------------------------------------

FLAGSHIP_RUNTIME_FILENAME = "pstack_flagship_runtime.json"
# 플래그십 채택값(2026-07-27 확정 셀): thr10 / hold5 / w0.013.
# 주의 — 러너 코드 기본은 MS_HOLD=3이지만 플래그십 채택 런은 MS_HOLD=5로 실행됐다.
# 여기서는 채택값 5를 하드코딩하고 tuning `adapter.flagship.ms_adapt`로만 조정한다.
FLAGSHIP_MS_ADAPT_DEFAULTS: dict[str, Any] = {"enabled": True, "thr": 10.0, "hold": 5, "w": 0.013}
# FAR_GATE=3(하이브리드). 폐쇄 예보 입력이 VISSIM forecast에 없으므로(아래
# freeway_lane_loss 항상 빈 dict) 실질적으로 mode 2(capdrop 상태 트리거)로 동작한다.
FLAGSHIP_FAR_GATE_DEFAULTS: dict[str, Any] = {"enabled": True, "thr": 0.95}


def flagship_settings(tuning: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(_mapping(tuning.get("adapter")).get("flagship"))


def flagship_config_overrides() -> dict[str, Any]:
    """플래그십 cfg 정식 키(적용 순서 base < flagship < calibration < tuning의 flagship 층).

    러너 build_cfg(L76-99) + run_job.sh env + default.yaml 실효값을 그대로 옮긴다.
    주의: plan.md 레시피는 leader_search_mode='continuous'라고 적었지만 러너 build_cfg
    L81이 "grid"를 강제한다 — 러너 원문이 정답이므로 grid를 쓴다(문서화: context-notes).
    OPT12 2종(leader_skip_local_refinement/leader_rollout_early_stop)은 MPCConfig
    dataclass 필드가 아니라 여기 넣으면 TypeError — build_pstack_flagship_controller의
    setattr로만 주입한다. 플랜트 env(VFREE/RHO_CRIT/TAU_H 등)는 수치실험 플랜트 물리라
    복사 금지(VISSIM 캘리브레이션이 예측모델 기준).
    """
    return {
        "mpc": {
            # 러너 build_cfg L77-84 원문(HORIZON env 미설정 → default.yaml 3 유지).
            "horizon_steps": 3,
            "control_horizon_steps": 3,
            "leader_search_mode": "grid",
            "relaxed_quantized_controls": True,
            "stackelberg_leader_parallel_backend": "serial",
            "grid_parallel_backend": "serial",
            "grid_reuse_process_pool": False,
            # default.yaml 실효값(어댑터 base가 축소해 둔 예산 복원).
            "leader_candidate_count": 49,
            "leader_refinement_candidate_count": 25,
            "max_nash_iter": 10,
            "stackelberg_enable_fallback": True,
            "stackelberg_enable_pfo_incumbent": True,
            "stackelberg_allocation_mode": "direct",
            # make_controller L252-255: LEADER_V_DEPTH env 없고 cfg 0이면 depth 3.
            "leader_value_depth": 3,
            # run_job.sh env → cfg 번역(러너 L679-704, L894-896, L872-874, L602-628).
            "seg13_meter_box_veh_h": 300.0,     # METER_BOX=300
            "seg13_vsl_box_kmh": 20.0,          # VSL_BOX=15의 VISSIM DSD(20 간격) 보정값
            "leader_rollout_box_walk": True,    # BOX_WALK=1
            "leader_rollout_box_walk_vg": True, # BOX_WALK_VG=1
            "baseline_move_box": True,          # BASELINE_BOX=1
            "np_primal_dual_iters": 4,          # NP_PD_ITER=4
            "np_bias_correction": True,         # NP_BIAS=1
            "leader_mfd_far_state_aware": True, # FAR_STATE_AWARE=1
            "leader_mfd_far_real_speed": True,  # FAR_REAL_V=1
            # BIAS_SAMPLE=1 + BIAS_POW=0.4 (make_controller L268-273; 활성화 자체는
            # build_pstack_flagship_controller의 enable_biased_sampling에서).
            "leader_bias_sample_pow": 0.4,
        },
        "freeway_follower": {
            # 러너 실효 기본(default.yaml): VSL smoothness 0.0.
            # segment_metering_smoothness_weight는 여기서 건드리지 않는다 —
            # 러너와 동일하게 MS_ADAPT per-step 주입만 그 값을 결정한다.
            "vsl_smoothness_weight": 0.0,
        },
    }


def build_priced_wu_link_controller(cfg, tuning: Mapping[str, Any]):
    """가격 리더 + Wu 충실 팔로워, player 입도만 링크 단위 (2026-08-20).

    `build_pstack_flagship_controller` 와 **가격 설정이 같고 `segment_agents` 만 다르다.**
    flagship 은 freeway agent 를 세그먼트 16개로 쪼개는데, 그러면 VSL 은 링크당 1개뿐이라
    8 agent 가 하나를 두고 경합한다(실측 vsl_selected 가 100.0/120.0 로 갈리고 병합은
    out.vsl[link] 한 줄이라 사실상 마지막 승자). 링크 단위면 agent 가 VSL 1 + 램프 2 =
    액션 3개를 정확히 소유한다.

    Wu 팔로워는 그대로다 — 순수 Jacobi, 결합변수 z̃ 동결·동시갱신, 오라클 7개, λ_P/λ_UF.
    `PricedWuLinkStackelbergController` 는 `_make_follower_solver` 한 줄만 오버라이드한다.
    """
    from src.controllers.priced_wu_link_controller import (
        PricedWuLinkStackelbergController,
    )

    settings = flagship_settings(tuning)
    os.environ["NASH_SMAX"] = str(int(_as_float(settings.get("nash_smax"), 10.0)))
    if bool(settings.get("opt12", True)):
        cfg.mpc.leader_skip_local_refinement = True
        cfg.mpc.leader_rollout_early_stop = True

    controller = PricedWuLinkStackelbergController(cfg)
    controller.nash_solver.f1_spillback_weight = 0.0
    # 가격 4채널 — flagship 과 동일. wu 팔로워라 offset 오라클도 있으므로 켠다.
    controller.signal_price_enabled = True
    controller.metering_price_enabled = True
    controller.vsl_price_enabled = True
    controller.offset_price_enabled = True
    controller.offset_price_inner_iters = 4
    controller.green_offset_cross_price_enabled = False
    controller.vsl_meter_cross_price_enabled = False
    controller.nash_solver.joint_green_offset_enabled = True
    controller.nash_solver.ramp_offset_enabled = True
    controller.metering_price_delta_veh_h = _as_float(settings.get("metering_price_delta_veh_h"), 300.0)
    controller.metering_price_trust_frac = _as_float(settings.get("metering_price_trust_frac"), 0.20)
    # 녹색 신뢰영역[s]. 기본 6.0 = 기존 거동.
    #
    # 왜 노출하나. 5400초 실런에서 컨트롤러가 무제어보다 나빴는데(TTT +12.4%), SG 단위
    # 녹색이 망의 고정신호 대비 **중앙 65%(최대 129%)** 어긋나 있었다. 총 녹색합은
    # 보존되므로(비 1.000) 용량 손실이 아니라 **재분배 크기**의 문제다. 결정당 ±6초씩
    # 33결정이면 누적 드리프트가 그만큼 커진다. 모델이 큐를 40~73% 과소예측하는 상태에서
    # 그 크기로 재분배하면 손해가 난다는 가설을 이 값으로 검정한다.
    if settings.get("signal_price_trust_sec") is not None:
        controller.signal_price_trust_sec = _as_float(settings.get("signal_price_trust_sec"), 6.0)
    # 가격 롤아웃 병렬화 (tuning 절 `price_parallel`). 기본 10 워커.
    #
    # 가격 FD 는 같은 작동점에서 레버를 하나씩 흔든 **독립 롤아웃**이라 병렬이 자연스럽다.
    # 상류가 green 채널에 이미 기구를 갖고 있고(`_green_price_rollouts`), 독스트링이
    # "병렬이어도 각 롤아웃 인자가 같고 순수 함수이므로 결과가 같다(수집 순서만 다르다)" 를
    # 보증한다. 여기서 현시별 가격(`_phase_price_rollouts`)도 같은 규약으로 병렬화했다.
    #
    # flagship 이 parallel_backend 를 serial 로 두는 것은 "러너 build_cfg 원문" 을 옮긴
    # 것이지 병렬을 배제한 판단이 아니다 — 그 자리에 경고 주석이 없다.
    #
    # 병렬 실패는 조용히 넘어가지 않는다. 직렬로 재실행하되
    # `price_parallel_serial_rerun_count` 와 `price_parallel_last_error` 를 남긴다.
    _par = _mapping((tuning or {}).get("price_parallel"))
    controller.price_parallel_workers = int(_as_float(_par.get("workers"), 10.0))

    # 현시별 교환 가격 (tuning 절 `phase_price`). 기본 꺼짐 — 켜면 리더의 가격 롤아웃이
    # 신호당 2회에서 2 + live현시수 로 늘어 약 3배가 된다. 병렬이 그 비용을 흡수한다.
    section = _mapping((tuning or {}).get("phase_price"))
    if section:
        if "enabled" in section:
            controller.phase_price_enabled = bool(section["enabled"])
        if "delta_sec" in section:
            controller.phase_price_delta_sec = _as_float(section["delta_sec"], 6.0)
        if "weight" in section:
            controller.phase_price_weight = _as_float(section["weight"], 1.0)
        if "local_cost_model" in section:
            # "phased" 면 정련이 GNE 와 같은 국소 물리(rollout_local_tts_phased —
            # 플래툰 도착·하류 S_eff·offset·per-movement 용량)로 후보를 채점한다.
            # 기본 "drain" 은 기존 큐 배수 모형이라 비트 동일.
            controller.phase_price_local_cost_model = str(section["local_cost_model"])
        if "exchange_steps_sec" in section:
            cfg.mpc.phase_price_exchange_steps_sec = tuple(
                float(x) for x in section["exchange_steps_sec"]
            )
    # flagship 이 여기서 segment_agents=True 를 켠다. 이 팔은 켜지 않는다 —
    # LinkAgentWuFollower.__init__ 이 False 로 못박아 두었다.
    #
    # 그래서 **SEG13 전용 설정을 같이 걷어내야 한다.** `flagship_config_overrides()` 가
    # seg13_meter_box_veh_h=300 · seg13_vsl_box_kmh=20 을 넣는데, wu 팔로워가
    # `segment_agents and metering_enabled` 를 요구하며 RuntimeError 로 즉사시킨다
    # (wu_faithful_follower.py:4024-4034). 실측: 2026-08-20 첫 스모크가 전 결정
    # controller_status=fallback_fixed 로 떨어졌고 controller_error 가 정확히 그 메시지였다.
    #
    # 대체 수단은 에러 메시지 자신이 알려준다 — "비-SEG13은 metering_marginal_price_trust_frac
    # 이 이미 묶는다". 위에서 0.20 으로 세워 두었다.
    for _seg13_only in ("seg13_meter_box_veh_h", "seg13_vsl_box_kmh", "freeway_agent_groups"):
        if getattr(cfg.mpc, _seg13_only, None) is not None:
            setattr(cfg.mpc, _seg13_only, None)
    return controller


def build_pstack_flagship_controller(cfg, tuning: Mapping[str, Any]):
    """P-STACK-WU-FAITHFUL-ALLPRICE-JOINT 컨트롤러 구성(러너 make_controller L244-316 이식).

    cfg 정식 키는 flagship_config_overrides()가 build_config 단계에서 이미 주입했다는
    전제. 여기서는 (1) 프로세스 env, (2) cfg.mpc 동적 속성, (3) controller/nash_solver
    인스턴스 속성을 러너와 같은 순서로 채운다.
    """
    settings = flagship_settings(tuning)
    # NASH_SMAX: src 내부에서 env로만 소비(wu_faithful_follower.py:3908-3912) —
    # min(max_nash_iter, 5) 하드캡 해제. 어댑터는 1회 실행 프로세스라 부작용 없음.
    os.environ["NASH_SMAX"] = str(int(_as_float(settings.get("nash_smax"), 10.0)))
    # OPT12(러너 L259-261): dataclass 필드가 아닌 동적 속성(stackelberg_mpc getattr 소비).
    if bool(settings.get("opt12", True)):
        cfg.mpc.leader_skip_local_refinement = True
        cfg.mpc.leader_rollout_early_stop = True

    from src.controllers.f1_wu_faithful_follower import F1StackelbergWuMeteredController

    controller = F1StackelbergWuMeteredController(cfg)
    # BIAS_SAMPLE(러너 L268-273): Halton 상단 warp. leader_bias_sample_pow(0.4)는 cfg
    # override로 주입 완료. 러너 build_cfg가 grid 검색을 강제하므로 continuous 샘플
    # 경로가 호출되지 않아 사실상 불활성이지만, 러너 원문 그대로 이식해 둔다
    # (tuning으로 leader_search_mode를 continuous로 바꾸면 그대로 발화).
    if bool(settings.get("bias_sample", True)):
        from src.controllers.biasedsample_mpc import enable_biased_sampling

        enable_biased_sampling(controller)
    controller.nash_solver.f1_spillback_weight = 0.0
    controller.signal_price_enabled = True
    controller.metering_price_enabled = True
    controller.vsl_price_enabled = True
    # cross 2종 기본 OFF(2026-07-16 동결 + run_job.sh CROSS_OFF=1).
    controller.green_offset_cross_price_enabled = False
    controller.vsl_meter_cross_price_enabled = False
    controller.nash_solver.joint_green_offset_enabled = True
    # OFFSET_PRICE 기본 ON + SQP식 inner-walk 4회(러너 L298-300).
    controller.offset_price_enabled = True
    controller.offset_price_inner_iters = 4
    # RAMP_OFFSET 기본 ON(러너 L303-304): D/F ramp-aware offset 탐색.
    controller.nash_solver.ramp_offset_enabled = True
    # metering δ=300 + trust_frac=0.20 — 반드시 짝(러너 L305-315).
    controller.metering_price_delta_veh_h = 300.0
    controller.metering_price_trust_frac = 0.20
    # SEG13(러너 L829-834): freeway를 segment agent로 분해 + 예산 simplex 사영.
    if hasattr(controller.nash_solver, "segment_agents"):
        controller.nash_solver.segment_agents = True
    # PRICE_FAR / PRICE_HINGE (2026-08-04, 튜닝 노출). 기본 OFF = 기존과 비트 동일.
    #
    # 왜 노출하는가. 리더는 후보를 `TTT + far` 로 채점하는데(stackelberg_mpc.py:2371-2377,
    # leader_value_depth=3>0 이라 게이트가 열려 있다) 한계가격은 `TTT` 의 기울기다.
    # **최소화하는 함수와 미분하는 함수가 다르다.**
    #
    # 실측(2026-08-04, g6_v6 앵커 t0, 깊이 6=360 s, 수요 정합 튜닝):
    #   미터가 구속하지 않는 운영점(1800/1440)에서는 두 가격이 모두 음수이고 far 배율 ~4 배.
    #   **구속하는 운영점(1080/720)에서 far 를 넣으면 부호가 양수로 뒤집힌다**
    #   (1080: -1.7e-4 -> +8.1e-3, 48.9 배). 순수 TTT 는 "미터를 열수록 좋다"만 말하므로
    #   조일 이유가 기울기에 존재하지 않았다. far 의 램프 항 q^2/(2*merge_rate) 가
    #   본선 혼잡 시 배수 지연을 담아 처음으로 metering 에 값을 만든다.
    #   크기도 |g|*Δm ~ 10 veh*h 로 기준 TTT(90~150)의 7~11 % 가 된다.
    #
    # 반대 증거도 남아 있다. stackelberg_wu_metered.py:157-159 가 2026-07-09 ablation 에서
    # "gradient 크기와 노이즈를 함께 증폭 — 실측 악화" 로 기본 OFF 로 되돌렸다고 적고 있다.
    # 그 실험은 수치 시뮬 환경이고 오늘의 수요 정합 이전이라 그대로 적용하기 어렵지만,
    # 44~60 배 증폭은 실재하므로 **기본 ON 으로 두지 않는다.** 폐루프 A/B 로 판정할 것.
    if bool(settings.get("price_far", False)):
        controller.price_far_enabled = True
    if bool(settings.get("price_hinge", False)):
        controller.price_hinge_enabled = True
        controller.price_hinge_weight = _as_float(settings.get("price_hinge_weight"), 1.0)
    return controller


def load_flagship_runtime(path: Path) -> dict[str, Any]:
    """사이드카 읽기. 부재/파손 시 빈 dict → 러너 첫 스텝과 동일(래치 0, prev 없음)."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except Exception:
        pass
    return {}


def save_flagship_runtime(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(data), ensure_ascii=False, indent=2), encoding="utf-8")


def flagship_link_mean_density(state) -> dict[str, float]:
    """러너 L1107-1108: 링크별 세그먼트 평균 밀도."""
    return {
        str(link): float(sum(values)) / len(values)
        for link, values in (getattr(state, "freeway_density", {}) or {}).items()
        if values
    }


def flagship_ms_adapt_update(
    prev_rho: Mapping[str, float],
    rho_now: Mapping[str, float],
    latch: int,
    thr: float,
    hold: int,
    w: float,
) -> tuple[float, int, float]:
    """MS_ADAPT 래치 갱신(러너 L1109-1113과 동일한 순수 함수 — 단위검증 대상).

    첫 스텝(prev 비어 있음)은 dmax=0 → latch max(0,-1)=0 → weight=w (러너와 동일).
    """
    dmax = max(
        (abs(float(v) - float(prev_rho[lk])) for lk, v in rho_now.items() if lk in prev_rho),
        default=0.0,
    )
    new_latch = int(hold) if dmax > float(thr) else max(0, int(latch) - 1)
    weight = 0.0 if new_latch else float(w)
    return float(dmax), new_latch, float(weight)


def flagship_far_gate_update(
    cfg,
    state,
    forecast,
    stress: bool,
    thr: float,
) -> tuple[bool, bool, bool, bool]:
    """FAR_GATE=3 갱신(러너 L1064-1096): capdrop 실측 히스테리시스 + 폐쇄 예보 선제 ON.

    반환: (fg_new, stress_latch, drop_seen, all_sub).
    VISSIM forecast는 freeway_lane_loss가 항상 비어 있어 예보 분기는 발화하지 않는다
    (실질 mode 2). 폐쇄 예보 입력이 생기면 그대로 mode 3으로 동작한다.
    """
    from src.models.metanet import desired_speed_kmh, segment_flow_veh_h

    rc = float(cfg.network.rho_crit)
    vf = float(cfg.network.v_free)
    all_sub = True
    drop_seen = False
    for link in cfg.network.freeway_links:
        dens = state.freeway_density.get(link, [])
        spds = state.freeway_speed.get(link, [])
        lns = getattr(state, "freeway_effective_lanes", {}).get(link, [])
        for i in range(len(dens)):
            rho = float(dens[i])
            if rho <= rc:
                continue
            all_sub = False
            lam = float(lns[i]) if i < len(lns) else float(cfg.network.freeway_lanes)
            v = float(spds[i]) if i < len(spds) else 0.0
            flow = segment_flow_veh_h(rho, v, lam)
            cap = segment_flow_veh_h(rc, desired_speed_kmh(rc, vf, rc), lam)
            if flow < float(thr) * cap:
                drop_seen = True
    if drop_seen:
        stress = True  # drop 발생 → ON 래치
    elif all_sub:
        stress = False  # 전 세그 임계 아래 = 회복 완료 → OFF
    fg_new = bool(stress)
    # mode 3 하이브리드: 예보 지평 내 차선 폐쇄가 있으면 선제 ON(래치는 불변 — 러너 동일).
    try:
        from src.models.demand import merge_freeway_lane_loss

        merged = merge_freeway_lane_loss(list(forecast))
        if any(float(v) > 0.0 for segs in merged.values() for v in segs.values()):
            fg_new = True
    except Exception:
        pass
    return fg_new, bool(stress), drop_seen, all_sub


def flagship_sup_score(control, state, forecast, cfg) -> float:
    """감독자 공통 채점(러너 _sup_score L947-959): h스텝 결합 rollout TTT + far cost-to-go.

    후보 채점이므로 상류 rollout endpoint 를 거친다(N7 "우회 호출 0"). far cost-to-go 는
    endpoint 의 far_enabled 성분이 그대로 수행한다.
    """
    from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point

    point = evaluate_price_point(
        state,
        control,
        list(forecast),
        (),
        ObjectiveSpec(
            cfg=cfg,
            depth_override=max(1, int(cfg.mpc.horizon_steps)),
            box_walk=False,
            score_mode="price",
            far_enabled=True,
        ),
    )
    return float(point.objective)


def run_pstack_flagship_decision(
    cfg,
    state,
    forecast,
    previous,
    tuning: Mapping[str, Any],
    runtime_path: Path,
):
    """pstack-flagship 결정 1회: 사이드카 복원 → FAR_GATE/MS_ADAPT → decide → SUP_PFO.

    러너 run_one 루프(L1034-1176)의 한 스텝과 동일한 순서. 반환:
    (control, controller, metadata).
    """
    import copy as _copy

    metadata: dict[str, Any] = {}
    settings = flagship_settings(tuning)
    runtime = load_flagship_runtime(runtime_path)
    first_step = not bool(runtime)
    metadata["flagship_runtime_first_step"] = float(first_step)

    controller = build_pstack_flagship_controller(cfg, tuning)
    metadata.update(install_vissim_terminal_cost_objective(controller, cfg, tuning))
    metadata["flagship_nash_smax_env"] = _as_float(os.environ.get("NASH_SMAX"), 0.0)

    # SUP_PFO 준비(러너 L931-945): per-step cfg 변형(FAR_GATE/MS_ADAPT) **이전** 사본.
    # seg13 전용 박스는 `is not None` 가드라 반드시 None으로 되돌린다. 링크-PFO 이동
    # 한계는 baseline_move_box로 walk-MVG와 동일화.
    sup_settings = _mapping(settings.get("sup_pfo"))
    sup_enabled = bool(sup_settings.get("enabled", True))
    sup_gate = str(sup_settings.get("gate", "fargate"))
    sup_cfg = None
    if sup_enabled:
        sup_cfg = _copy.deepcopy(cfg)
        sup_cfg.mpc.seg13_meter_box_veh_h = None
        if hasattr(sup_cfg.mpc, "seg13_meter_box_up_veh_h"):
            sup_cfg.mpc.seg13_meter_box_up_veh_h = None
        sup_cfg.mpc.seg13_vsl_box_kmh = None
        # ZONE-4(2026-08-01): 감독자 PFO는 링크 모드(segment_agents=False)라 zone 구조를
        # 쓰지 않는다. 남겨두면 follower 진입부 가드가 "groups인데 SEG13이 꺼져 있다"로
        # 즉사시킨다 — seg13 박스 키와 동일 규약으로 되돌린다.
        if hasattr(sup_cfg.mpc, "freeway_agent_groups"):
            sup_cfg.mpc.freeway_agent_groups = None
        sup_cfg.mpc.baseline_move_box = True

    # FAR_GATE=3 (러너 L1048-1099).
    fg_settings = dict(FLAGSHIP_FAR_GATE_DEFAULTS)
    fg_settings.update(_mapping(settings.get("far_gate")))
    fargate_stress = bool(runtime.get("fargate_stress", False))
    if bool(fg_settings.get("enabled", True)):
        fg_new, fargate_stress, drop_seen, all_sub = flagship_far_gate_update(
            cfg,
            state,
            forecast,
            fargate_stress,
            _as_float(fg_settings.get("thr"), 0.95),
        )
        cfg.mpc.leader_mfd_far_enabled = bool(fg_new)
        metadata.update({
            "flagship_fargate_enabled": 1.0,
            "flagship_fargate_capdrop_seen": float(drop_seen),
            "flagship_fargate_all_subcritical": float(all_sub),
            "flagship_fargate_stress_latch": float(fargate_stress),
        })
    else:
        metadata["flagship_fargate_enabled"] = 0.0
    metadata["flagship_fargate_on"] = float(bool(cfg.mpc.leader_mfd_far_enabled))

    # MS_ADAPT (러너 L1106-1116). 결정 전에 마찰 가중을 주입한다.
    ms_settings = dict(FLAGSHIP_MS_ADAPT_DEFAULTS)
    ms_settings.update(_mapping(settings.get("ms_adapt")))
    ms_prev = {
        str(k): _as_float(v)
        for k, v in _mapping(runtime.get("ms_prev_rho")).items()
    }
    ms_latch = int(_as_float(runtime.get("ms_latch"), 0.0))
    rho_now = flagship_link_mean_density(state)
    if bool(ms_settings.get("enabled", True)):
        ms_dmax, ms_latch, ms_weight = flagship_ms_adapt_update(
            ms_prev,
            rho_now,
            ms_latch,
            _as_float(ms_settings.get("thr"), 10.0),
            int(_as_float(ms_settings.get("hold"), 5.0)),
            _as_float(ms_settings.get("w"), 0.013),
        )
        cfg.freeway_follower.segment_metering_smoothness_weight = float(ms_weight)
        metadata.update({
            "flagship_ms_adapt_enabled": 1.0,
            "flagship_ms_dmax": float(ms_dmax),
            "flagship_ms_latch": float(ms_latch),
        })
    else:
        metadata["flagship_ms_adapt_enabled"] = 0.0
    metadata["flagship_ms_friction"] = float(
        getattr(cfg.freeway_follower, "segment_metering_smoothness_weight", 0.0)
    )

    # 사이드카는 decide 이전에 저장 — 결정이 실패(fallback_fixed)해도 상태 전이
    # 관측치(직전 밀도·래치)는 다음 스텝에 이어진다.
    save_flagship_runtime(runtime_path, {
        "schema_version": 1,
        "sim_sec": float(getattr(state, "time_sec", 0.0)),
        "ms_prev_rho": rho_now,
        "ms_latch": int(ms_latch),
        "fargate_stress": bool(fargate_stress),
    })

    result = controller.decide_with_info(state.copy(), forecast, previous, cfg)
    control = result.control
    metadata["leader_objective"] = float(getattr(result, "leader_objective", 0.0))
    metadata["nash_objective"] = float(getattr(getattr(result, "nash", None), "objective_value", 0.0))
    metadata.update({
        f"meta_{k}": float(v)
        for k, v in getattr(result, "metadata", {}).items()
        if isinstance(v, (int, float, bool))
    })

    # SUP_PFO + SUP_GATE=fargate (러너 L1151-1176): far 게이트 ON 스텝은 감독자 OFF
    # (동일한 물리 조건이 far를 부르고 감독자를 쫓아낸다 — 단일 게이트, 이중 스위치).
    sup_off = sup_gate == "fargate" and bool(cfg.mpc.leader_mfd_far_enabled)
    metadata["flagship_sup_enabled"] = float(sup_enabled)
    metadata["flagship_sup_gated_off"] = float(bool(sup_enabled and sup_off))
    if sup_enabled and not sup_off and sup_cfg is not None:
        from src.controllers.wu_faithful_follower import WuFaithfulFollower

        sup_pfo = WuFaithfulFollower(sup_cfg)
        try:
            pfo_control = sup_pfo.solve(state.copy(), None, forecast, previous).control
        finally:
            if hasattr(sup_pfo, "close"):
                try:
                    sup_pfo.close()
                except Exception:
                    pass
        v_ps = flagship_sup_score(control, state, forecast, cfg)
        v_pfo = flagship_sup_score(pfo_control, state, forecast, cfg)
        if v_pfo < v_ps - 1.0e-9:
            pfo_control.diagnostics["sup_pick_pfo"] = 1.0
            pfo_control.diagnostics["sup_v_pstack"] = v_ps
            pfo_control.diagnostics["sup_v_pfo"] = v_pfo
            control = pfo_control
        else:
            control.diagnostics["sup_pick_pfo"] = 0.0
            control.diagnostics["sup_v_pstack"] = v_ps
            control.diagnostics["sup_v_pfo"] = v_pfo
        metadata["flagship_sup_pick_pfo"] = float(control.diagnostics["sup_pick_pfo"])
        metadata["flagship_sup_v_pstack"] = float(v_ps)
        metadata["flagship_sup_v_pfo"] = float(v_pfo)
    return control, controller, metadata


def build_config(
    repo_root: Path,
    control_interval: float,
    sim_period: float,
    mode: str,
    calibration: Mapping[str, Any],
    tuning: Mapping[str, Any],
    local_observation: bool = False,
    flagship: bool = False,
):
    _, _, _, ExperimentConfig, _, _ = repo_imports(repo_root)
    config_path = repo_root / "src/config/default.yaml"
    # This is intentionally a light Vissim-integration profile. The full offline
    # controller can be much heavier; for COM smoke/control-loop use we keep a
    # short horizon and serial execution.
    overrides: dict[str, Any] = {
        "simulation": {
            "T_total": max(float(sim_period), float(control_interval)),
            "T_f": 10.0,
            "T_u": 5.0,
            "control_interval": float(control_interval),
        },
        "network": {
            "freeway_links": ["FW_W", "FW_E"],
            "freeway_segments_per_link": 8,
            "freeway_segment_length_km": 0.444,
            "freeway_lanes": 2,
            "v_free": 123.825,
            "rho_crit": 20.401,
            "freeway_capacity_veh_h": 4574.818,
            "lost_time": 6.0,
            "movement_capacity_veh_h": 1800.0,
            "ramp_capacity_veh_h": {
                "R_D_W": 1414.0,
                "R_F_W": 316.0,
                "R_D_E": 1414.0,
                "R_F_E": 316.0,
            },
            # 아래 두 인덱스는 **가상 8-seg 네트워크(modi_eval_vsl_8seg)** 기본값이다.
            # 실제 개포 real-world 플랜트(modi_eval_rw_control.inpx)의 값이 아니므로
            # tuning(config_overrides.network)이 없는 합성 스모크/계약 검증 경로에서만
            # 쓰인다. 실 플랜트 값은 generate_real_world_control_mapping.py 가 .inpx
            # 커넥터 기하에서 뽑아 control_mapping.json(model_topology_overrides)과
            # evaluation/configs/real_world_modi_pstack_adapter_v0_20260719.json
            # (config_overrides.network)에 쓰고, 후자가 base보다 나중에 적용된다.
            #
            # 실측 개포 토폴로지(2026-08-02 .inpx 커넥터 전수조사 + Link Segment
            # Results 유량 검증, 세그먼트는 진행방향 인덱스):
            #   FW_E(체인 74-10699-2-10702-24): S3 에 OR_F_E(10643/10682) diverge 와
            #        R_F_E(10639/10681) merge 가 **같은 세그먼트**에 있고,
            #        S5 에 OR_D_E(10481/10483) diverge 와 R_D_E(10490/10484) merge.
            #   FW_W(체인 26): S2 에 OR_D_W(10479/10491)+R_D_W(10480/10482),
            #        S4 에 OR_F_W(10645/10638)+R_F_W(10646) — R_F_W 의 두 번째
            #        물리 미터 10644 는 S5 에 합류한다(ramp_meter_groups 의
            #        segment_straddle 참조).
            # 즉 가상망은 각 인터체인지의 diverge/merge 를 다른 세그먼트로 분리했지만
            # (off 2/4, merge 3/5), 실 플랜트는 1,347 m 세그먼트 하나에 둘 다 들어간다.
            "ramp_merge_segment_index": {
                "R_D_W": 5,
                "R_F_W": 3,
                "R_D_E": 3,
                "R_F_E": 5,
            },
            "off_ramp_segment_index": {
                "OR_D_W": 4,
                "OR_F_W": 2,
                "OR_D_E": 2,
                "OR_F_E": 4,
            },
        },
        "mpc": {
            "horizon_steps": 1,
            "control_horizon_steps": 1,
            "follower_solver_mode": "distributed" if local_observation else "two_block",
            "leader_search_mode": "grid",
            "leader_candidate_count": 1 if local_observation and mode == "fast-smoke" else 3,
            "leader_refinement_candidate_count": 1,
            "max_nash_iter": 1,
            "distributed_coupling_tol": 0.05 if local_observation else 0.001,
            "relaxed_quantized_controls": bool(local_observation),
            "stackelberg_allocation_mode": "simplified" if local_observation else "direct",
            "stackelberg_enable_fallback": False,
            "stackelberg_leader_parallel_backend": "serial",
            "grid_parallel_backend": "serial",
            "grid_reuse_process_pool": False,
            "leader_continuous_parallel_multistart": False,
        },
        "leader": {
            "N_P_crit_veh": 390.0,
            "mfd_penalty_mode": "all_urban_halfcap",
            # N_P_star 는 horizon 순유입[veh] 목표다(누적 수준이 아니다).
            #
            # 2026-08-20 재산정. 옛 값 [0.0, 780.0] 은 `Leader._candidate_bounds` 가 매 결정
            # 유도하는 movement-level 도달가능 범위의 **양끝을 다 잘랐다**:
            #
            #   측정(core17legs4b, 18결정)   movement 하한 -216.3 ~ -0.4
            #                                movement 상한   517.1 ~ 2135.9
            #                                사영 순유입   1068.9 ~ 1105.8 (적재 구간)
            #
            # 결과 두 가지. (1) 상한 780 이 자연 순유입 ~1,100 보다 낮아 리더의 모든 선택이
            # "지금 흐르는 것보다 조여라" 가 됐고, 가장 느슨한 780 을 골라도 318 veh 를 조인다
            # — 완료차량이 폴백 대비 14~17% 줄어 가드가 7/7 기각했다. (2) 하한 0 이 18결정
            # 전부에서 물려 리더가 순유출(배수)을 아예 표현하지 못했다.
            #
            # 앵커까지 무너진다 — `_np_anchor_values` 는 movement 양끝과 직전 N_P_star 를
            # 앵커로 쓰는데 셋 다 [0,780] 으로 클립돼 앵커 집합이 {0, 780} 으로 붕괴했다.
            # linspace 는 n_np = round(sqrt(9)) = 3 개뿐이라 앵커가 사실상 후보 전부다.
            #
            # 새 값은 측정된 도달가능 범위를 여유 두고 덮는다(하한 -216.3 -> -250,
            # 상한 2135.9 -> 2400). 상류 설계 의도와도 맞다 — `test_constraints.py:1799` 가
            # 파생 경계는 base 범위 **안에** 들어간다고 검사한다(상류 기본 [-3500, 3500]).
            "N_P_star_range": [-250.0, 2400.0],
            # N_UF_star 는 램프 미터링 합[veh/h] 목표다.
            #
            # 2026-08-20 재산정. 옛 상한 5000.0 은 이 망의 **물리 램프 용량 7,200 의 69%** 였다
            # (ramp_capacity_veh_h = 1800 x 4, `real_world_modi_pstack_adapter_v0_20260719.json`).
            #
            # `Leader._candidate_bounds` 는 자유류에서
            #     feasible_nuf = max(feasible_nuf, total_ramp_capacity)   # = 7200
            #     nuf_upper    = min(N_UF_star_range[1], nuf_upper_target)
            # 을 계산하는데, 상한 5000 이 항상 이겼다 — 실런 전 결정에서
            # `leader_nuf_bound_upper = 5000` 이고 `leader_nuf_heuristic_target` 마저 5000 으로
            # 잘렸다.
            #
            # 결과가 이것이다. 폴백(무제어)은 `ControlAction.uncontrolled` 로 램프를 용량 그대로
            # 열어 7,200 을 실현하는데, 리더는 `_leader_metering_projection` 이 합을 5,000 에
            # 맞춰 **매 결정 램프 유입을 30.6% 강제 차단**당했다. 완료차량이 폴백 대비
            # 14~17% 적었던 직접 원인이고, 가드가 `completed_severe` 로 7/7 기각한 이유다.
            #
            # N_P 축만 넓힌 대조군(npbox, 2026-08-20)에서 리더 의도가 780 -> 1078.7 로 움직여도
            # 완료차량이 1520.61 로 **소수점까지 동일**했다 — 물리는 축은 N_P 가 아니라 N_UF 다.
            #
            # 새 상한은 물리 용량 그 자체다. 리더가 "미터링 안 함" 을 고를 수 있어야
            # 폴백과 같은 출발선에 선다.
            "N_UF_star_range": [0.0, 7200.0],
        },
        "freeway_follower": {
            "vsl_set": [60.0, 70.0, 80.0, 90.0, 100.0, 110.0, 120.0],
            "vsl_max_km_h": 120.0,
            "horizon_beam_width": 1 if local_observation else 2,
            "horizon_ramp_candidate_limit": 1 if local_observation else 3,
            "horizon_vsl_candidate_limit_per_link": 1 if local_observation else 3,
        },
        "urban_follower": {
            "allocation_pso_particles": 4 if local_observation else 18,
            "allocation_pso_iterations": 4 if local_observation else 24,
        },
    }
    if flagship:
        # 적용 순서: base < flagship < calibration < tuning (plan.md 결정).
        overrides = deep_update(overrides, flagship_config_overrides())
    overrides = deep_update(overrides, calibration_to_config_overrides(calibration))
    overrides = deep_update(overrides, tuning_to_config_overrides(tuning))
    if mode == "fuller-smoke":
        overrides["mpc"].update({
            "leader_candidate_count": 5,
            "max_nash_iter": 2,
        })
    cfg = ExperimentConfig.from_file(config_path, overrides=overrides)
    _plant_phase_counts_into(cfg)
    _plant_phase_shape_into(cfg, tuning)
    _plant_rollout_far_into(cfg, tuning)
    _plant_agent_topology_into(cfg, tuning)
    return cfg


def _plant_agent_topology_into(cfg, tuning) -> None:
    """tuning 의 `agent_topology` 절을 런타임 속성으로 심는다 (2026-08-20).

        freeway_granularity   "segment"(기본) | "link"

    **plant 모델을 바꾸지 않는다.** `freeway_segments_per_link` 도 `ramps` 도 그대로라
    METANET 롤아웃은 여전히 2링크 x 8세그먼트 = 16셀 + 램프 4개를 굴린다. 바뀌는 것은
    `build_agent_specs` 의 **agent 분할**뿐이다 — 누가 어느 레버를 소유하고 어느 셀을 보는가.

      segment  agent 16개. 각자 자기 1셀만 본다. VSL 은 링크당 1개뿐이라 8 agent 가
               하나를 공유하고 합의가 안 된다(실측 vsl_selected 100.0/120.0 로 갈림).
      link     agent 2개. 각자 VSL 1 + 램프 2 = 액션 3개를 정확히 소유하고,
               segment_index<0 이라 해석부가 자기 링크 8셀을 **전부** 본다.

    `phase_shape`/`rollout_far` 와 같은 이유로 dataclass 필드를 안 늘린다 —
    `src/models/state.py` 를 건드리면 앵커 등재가 하나 더 는다.
    """
    section = (tuning or {}).get("agent_topology")
    if not isinstance(section, Mapping):
        return
    if "freeway_granularity" in section:
        setattr(cfg.mpc, "freeway_agent_granularity", str(section["freeway_granularity"]))


def _plant_rollout_far_into(cfg, tuning) -> None:
    """tuning 의 `rollout_far` 절을 런타임 속성으로 심는다 (2026-08-20).

    far(MFD tail) terminal cost 는 `mfd_far_cost_to_go` 로 이미 구현돼 있고
    `cfg.mpc.leader_mfd_far_enabled` 도 상류 기본이 True 다. 그런데 분산 경로
    (`distributed_coordinator._evaluate_grid_candidate`)가 `ObjectiveSpec` 을
    `score_mode="raw"` 로 만들어 far 를 계산조차 하지 않았다 — 실런 진단에 far 키가 0건이다.

        enabled     분산 rollout 채점에 far 를 태운다 (기본 False = 비트동일)
        ncrit       urban reservoir 임계 누적[veh] (상류 기본 1700)
        g_free      임계 미만 배수율, g_cong 임계 초과 배수율
        weight      far 가중치 (1.0 이 물리 정확값)

    `phase_shape` 와 같은 이유로 dataclass 필드를 안 늘린다 —
    `src/models/state.py` 를 건드리면 앵커 등재가 하나 더 는다.
    """
    section = (tuning or {}).get("rollout_far")
    if not isinstance(section, Mapping):
        return
    mpc = cfg.mpc
    if "enabled" in section:
        setattr(mpc, "distributed_rollout_far_enabled", bool(section["enabled"]))
    for key, cast in (("ncrit", float), ("g_free", float), ("g_cong", float),
                      ("g_fw", float), ("weight", float)):
        if key in section:
            setattr(mpc, f"leader_mfd_far_{key}", cast(section[key]))


def _plant_phase_shape_into(cfg, tuning) -> None:
    """tuning 의 `phase_shape` 절을 런타임 속성으로 심는다 (2026-08-20).

    dataclass 필드로 넣지 않는 이유는 `ExperimentConfig.from_dict` 가 strict 라
    `src/models/state.py` 를 건드리게 되고, 그러면 앵커 등재가 하나 늘기 때문이다.
    vendor 쪽은 전부 `getattr(..., 기본값)` 으로만 읽으므로 안 심으면 오늘과 같다.

        mode / weight        압력 shape 주입 (3단계, 아직 vendor 미구현)
        search               쌍교환 탐색 stage 켜기
        steps_sec            교환 스텝 사다리
        signal_top_k         압력 치우침 상위 k 신호만
        candidate_limit      하드캡
    """
    section = (tuning or {}).get("phase_shape")
    if not isinstance(section, Mapping):
        return
    uf = cfg.urban_follower
    if "search" in section:
        setattr(uf, "phase_shape_search", bool(section["search"]))
    if "steps_sec" in section:
        setattr(uf, "phase_shape_steps_sec", tuple(float(x) for x in section["steps_sec"]))
    for key, cast in (("signal_top_k", int), ("candidate_limit", int),
                      ("weight", float), ("mode", str)):
        if key in section:
            setattr(uf, f"phase_shape_{key}", cast(section[key]))


def _plant_phase_counts_into(cfg) -> None:
    """계획이 센 SC별 현시 수를 모델에 심는다.

    이걸 안 심으면 모델은 legacy 스칼라 모드로 떨어져 전 SC 에 같은 예산을 준다. 실 망은
    SC107·108·109 가 3현시라(한 현시의 SG 가 `.sig` 에서 영구적색) 그 셋만 예산이 3 s 더
    커야 한다. 스칼라로 밀면 그 3 s 가 죽은 현시로 흘러가 실현 0 이 된다.

    계획은 config 뒤에 유도되므로 config 생성기가 이 값을 알 수 없다 — 두 산출물을 모두
    쥐고 있는 여기가 유일하게 순환이 없는 자리다. 계획이 없으면 아무것도 안 한다.
    """
    plan = load_signal_group_actuation_plan()
    if not plan:
        return
    live = {
        f"SC{int(sc_no)}": list(plan_live_phases(plan, int(sc_no)))
        for sc_no in (plan.get("controllers") or {})
    }
    if not live:
        return
    cfg.network.live_phases_by_signal = live


def profiled_demand_rates(
    state_json: Mapping[str, Any],
    cfg,
    calibration: Mapping[str, Any] | None = None,
    detector_mapping: Mapping[str, Any] | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, float], str]:
    """Mirror the Vissim runner's demand-profile multipliers in the model forecast.

    `run_stackelberg_vissim_controller.vbs` applies demand profiles at the
    VehicleInput level. Before this adapter-side mirror, the one-step METANET
    prediction treated every freeway direction and every urban boundary input
    as symmetric even when Vissim was running `fw_eb_heavy`, `urban_d_heavy`,
    etc. That creates a biased prediction target before calibration even
    starts.
    """
    demand = state_json.get("demand", {})
    if not isinstance(demand, Mapping):
        demand = {}
    urban_vph = float(demand.get("urban_volume_vph", 60.0))
    freeway_vph = float(demand.get("freeway_volume_vph", 1200.0))
    ramp_vph = float(demand.get("ramp_volume_vph", max(120.0, freeway_vph * 0.12)))
    profile = str(demand.get("demand_profile", "")).lower()
    urban_west_east_ratio = max(1.0e-6, _as_float(demand.get("urban_west_east_ratio"), 1.0))

    freeway_mainline = {str(link): freeway_vph for link in cfg.network.freeway_links}
    gate_keys = [
        str(link)
        for link in list(cfg.network.boundary_in_links) + list(cfg.network.boundary_out_links)
    ]
    # 게이트 앵커링. 러너가 자기 VISSIM vehicle input 을 게이트에 조인해서 게이트별
    # 유량을 넘겨주면 그것을 그대로 쓴다. 없으면(8seg 러너·g6 harness) 예전대로
    # 스칼라 하나를 전 게이트에 복제한다 — evaluation/controllers/demand_contract.md.
    urban_by_gate = demand.get("urban_volume_vph_by_gate")
    gate_anchored = isinstance(urban_by_gate, Mapping) and bool(urban_by_gate)
    if gate_anchored:
        unknown = sorted(str(gate) for gate in urban_by_gate if str(gate) not in set(gate_keys))
        if unknown:
            # 조용히 흘리면 그 유입의 수요가 말없이 사라진다. 대장과 격자가 따로
            # 갱신됐다는 뜻이므로 런을 세운다.
            raise ValueError(
                "state.demand.urban_volume_vph_by_gate has gates the model does not know: "
                + ", ".join(unknown)
            )
        urban_boundary = {key: 0.0 for key in gate_keys}
        for gate, value in urban_by_gate.items():
            urban_boundary[str(gate)] = float(value)
    else:
        urban_boundary = {key: urban_vph for key in gate_keys}
    ramp_arrival = {str(ramp): ramp_vph for ramp in cfg.network.ramps}

    if profile == "fw_eb_heavy":
        freeway_mainline["FW_E"] = freeway_vph * 1.55
        freeway_mainline["FW_W"] = freeway_vph * 0.55
    elif profile == "fw_wb_heavy":
        freeway_mainline["FW_W"] = freeway_vph * 1.55
        freeway_mainline["FW_E"] = freeway_vph * 0.55

    def set_urban_profile(high_links: set[str], high_factor: float, low_factor: float) -> None:
        for link in cfg.network.boundary_in_links:
            urban_boundary[str(link)] = urban_vph * (high_factor if str(link) in high_links else low_factor)
        # boundary_out links are not used as exogenous arrivals by the movement
        # queue model, but keep them populated for diagnostics/compatibility.
        for link in cfg.network.boundary_out_links:
            urban_boundary[str(link)] = urban_vph * low_factor

    # 아래 도시부 공간 프로파일은 스칼라 경로의 heuristic 이다(합성망 게이트 이름 기준).
    # 게이트 앵커링이 켜져 있으면 러너가 이미 vehicle input 단위로 배수를 적용한 값을
    # 주므로, 여기서 다시 흔들면 이중 적용이 된다.
    if not gate_anchored:
        if profile == "urban_west_heavy":
            set_urban_profile({"in_A_left", "in_D_left"}, 1.8, 0.65)
        elif profile == "urban_east_heavy":
            set_urban_profile({"in_C_right", "in_F_right"}, 1.8, 0.65)
        elif profile == "urban_north_heavy":
            set_urban_profile({"in_A_top", "in_B_top", "in_C_top"}, 1.65, 0.6)
        elif profile == "urban_d_heavy":
            set_urban_profile({"in_D_left"}, 2.2, 0.65)
        elif profile == "urban_f_heavy":
            set_urban_profile({"in_F_right"}, 2.2, 0.65)

        if abs(urban_west_east_ratio - 1.0) > 1.0e-9:
            west_factor = 2.0 * urban_west_east_ratio / (1.0 + urban_west_east_ratio)
            east_factor = 2.0 / (1.0 + urban_west_east_ratio)
            for link in cfg.network.boundary_in_links:
                key = str(link)
                if key in {"in_A_left", "in_D_left"}:
                    urban_boundary[key] = urban_boundary.get(key, urban_vph) * west_factor
                elif key in {"in_C_right", "in_F_right"}:
                    urban_boundary[key] = urban_boundary.get(key, urban_vph) * east_factor

    # Route-aware on-ramp forecast (2026-06-30): the hardcoded uniform ramp_vph (250/ramp) under-sizes
    # and mis-directs the on-ramp arrival. The VISSIM static routes send a fixed fraction of each urban
    # origin's demand onto the D on-ramp (link 25 -> FW_WB -> R_D_W) and F on-ramp (link 31 -> FW_EB ->
    # R_F_E); at u1400 this is ~1032 vph per direction (~2x the 1000 vph total forecast). Sizing N_UF to
    # the under-forecast made the leader meter the on-ramps below the real demand -> ramp queues -> harm.
    # ramp_share_of_urban_in[ramp] = (routing fraction onto that ramp) so ramp_arrival = share x total
    # urban boundary-in demand (which already carries the profile multipliers above).
    onramp_fc = _mapping(_mapping(calibration or {}).get("prediction")).get("onramp_route_forecast", {})
    if bool(_mapping(onramp_fc).get("enabled", False)):
        total_urban_in = sum(
            _as_float(urban_boundary.get(str(link), 0.0)) for link in cfg.network.boundary_in_links
        )
        shares = _mapping(_mapping(onramp_fc).get("ramp_share_of_urban_in"))
        for ramp in cfg.network.ramps:
            ramp_arrival[str(ramp)] = max(0.0, _as_float(shares.get(str(ramp), 0.0))) * total_urban_in

    route_bias = _mapping(_mapping(calibration or {}).get("prediction")).get("route_bias_forecast", {})
    route_bias = _mapping(route_bias)
    route_bias_enabled = bool(route_bias.get("enabled", True))
    route_bias_version = int(_as_float(route_bias.get("version"), 1.0))
    target_share = clamp(_as_float(route_bias.get("target_share"), 0.98), 0.5, 1.0)

    # v1 (legacy, demoted candidate): preserve total ramp demand and split the target node's ramp
    # pair by target_share. This is direction-agnostic and ties magnitude to a hardcoded ramp_vph.
    def apply_ramp_route_bias_v1(target_node: str) -> None:
        ramps = [str(ramp) for ramp in cfg.network.ramps]
        if not ramps:
            return
        target_prefix = f"R_{target_node}_"
        target_ramps = [ramp for ramp in ramps if ramp.startswith(target_prefix)]
        other_ramps = [ramp for ramp in ramps if ramp not in target_ramps]
        if not target_ramps or not other_ramps:
            return
        total_arrival_vph = ramp_vph * float(len(ramps))
        target_each = total_arrival_vph * target_share / float(len(target_ramps))
        other_each = total_arrival_vph * (1.0 - target_share) / float(len(other_ramps))
        for ramp in target_ramps:
            ramp_arrival[ramp] = target_each
        for ramp in other_ramps:
            ramp_arrival[ramp] = other_each

    # v2 (direction-aware, 2026-06-29 audit follow-up): VISSIM d/f_ramp_bias funnels biased flow
    # through ONE physical on-ramp toward ONE freeway direction (link 25 -> FW_WB, link 31 -> FW_EB;
    # run_stackelberg_vissim_controller.vbs ApplyRouteBias). v1 wrongly split the boost across both
    # directional ramps of the node and preserved a hardcoded total. v2 loads the direction-feeding
    # ramp with a fittable multiplier on ramp_vph, gives the same-node cross-direction ramp a small
    # share, and starves the other node's ramps. Total ramp demand is intentionally NOT preserved.
    v2 = _mapping(route_bias.get("v2"))
    v2_target_multiplier = max(0.0, _as_float(v2.get("target_multiplier"), 4.0))
    v2_cross_share = max(0.0, _as_float(v2.get("cross_share"), 0.15))
    v2_off_share = max(0.0, _as_float(v2.get("off_share"), 0.02))
    v2_direction_feed = _mapping(v2.get("direction_feed"))

    def apply_ramp_route_bias_v2(target_node: str) -> None:
        ramps = [str(ramp) for ramp in cfg.network.ramps]
        if not ramps:
            return
        target_prefix = f"R_{target_node}_"
        node_ramps = [ramp for ramp in ramps if ramp.startswith(target_prefix)]
        if not node_ramps:
            return
        ramp_to_freeway = getattr(cfg.network, "ramp_to_freeway", {}) or {}
        feed = str(v2_direction_feed.get(profile, ""))
        if feed not in node_ramps:
            wanted_dir = "FW_W" if target_node == "D" else "FW_E"
            feed = next(
                (r for r in node_ramps if str(ramp_to_freeway.get(r, "")) == wanted_dir),
                node_ramps[0],
            )
        for ramp in ramps:
            if ramp == feed:
                ramp_arrival[ramp] = ramp_vph * v2_target_multiplier
            elif ramp in node_ramps:
                ramp_arrival[ramp] = ramp_vph * v2_cross_share
            else:
                ramp_arrival[ramp] = ramp_vph * v2_off_share

    apply_ramp_route_bias = (
        apply_ramp_route_bias_v2 if route_bias_version >= 2 else apply_ramp_route_bias_v1
    )
    if route_bias_enabled:
        if profile in {"d_ramp_bias", "d_ramp_heavy"}:
            apply_ramp_route_bias("D")
        elif profile in {"f_ramp_bias", "f_ramp_heavy"}:
            apply_ramp_route_bias("F")

    local_fc = _mapping(_mapping(calibration or {}).get("prediction")).get(
        "local_ramp_arrival_forecast",
        {},
    )
    local_fc = _mapping(local_fc)
    if bool(local_fc.get("enabled", False)):
        observed_counts = {str(ramp): 0.0 for ramp in cfg.network.ramps}
        direct_counts = _mapping(state_json.get("ramp_counts"))
        has_model_ramp_counts = any(str(ramp) in direct_counts for ramp in observed_counts)
        if has_model_ramp_counts:
            for ramp in observed_counts:
                observed_counts[ramp] = max(0.0, _as_float(direct_counts.get(ramp), 0.0))
        else:
            d_count = max(0.0, _as_float(direct_counts.get("D"), 0.0))
            f_count = max(0.0, _as_float(direct_counts.get("F"), 0.0))
            for ramp in observed_counts:
                if ramp.startswith("R_D_"):
                    observed_counts[ramp] = d_count / 2.0
                elif ramp.startswith("R_F_"):
                    observed_counts[ramp] = f_count / 2.0
        if not any(value > 0.0 for value in observed_counts.values()) and detector_mapping:
            link_counts = _link_counts_from_local_observation(state_json)
            for link, ramps in _mapping(detector_mapping.get("ramp_link_to_queues")).items():
                count = max(0.0, _as_float(link_counts.get(str(link)), 0.0))
                if count <= 0.0 or not isinstance(ramps, list) or not ramps:
                    continue
                share = count / float(len(ramps))
                for ramp in ramps:
                    ramp_key = str(ramp)
                    if ramp_key in observed_counts:
                        observed_counts[ramp_key] += share
        queue_drain_horizon_sec = max(1.0, _as_float(local_fc.get("queue_drain_horizon_sec"), 120.0))
        multiplier = max(0.0, _as_float(local_fc.get("multiplier"), 1.0))
        min_vph = max(0.0, _as_float(local_fc.get("min_vph_if_observed"), 120.0))
        max_default = max(0.0, _as_float(local_fc.get("max_vph_per_ramp"), 900.0))
        max_by_ramp = _mapping(local_fc.get("max_vph_by_ramp"))
        # 램프별 배수 지평(2026-08-04). 스칼라 120 s 고정은 점유에 일률적으로 30 을 곱하는데,
        # 실제 커넥터 통과시간은 길이·속도에 따라 다르다 — 실측 역산값이 R_F_E 25.7 s ~
        # R_F_W 116.6 s 로 4.5배 벌어진다(scripts/measure_ramp_connector_flow.py 기준).
        # 이 때문에 모델 ramp_arrival 이 플랜트의 3.5분의 1로 나왔고, 모델 세계에서만
        # 미터가 수요를 구속하지 않아 dTTT/d(meter) 가 정의상 0 이 됐다(G6 램프 축 붕괴 원인).
        # max_vph_by_ramp 와 동일 규약 — dict 미지정이면 스칼라 폴백이라 비트동일.
        drain_by_ramp = _mapping(local_fc.get("queue_drain_horizon_sec_by_ramp"))
        blend = str(local_fc.get("blend", "max")).lower()
        for ramp, count in observed_counts.items():
            if count <= 0.0:
                continue
            drain_sec = max(1.0, _as_float(drain_by_ramp.get(ramp), queue_drain_horizon_sec))
            observed_vph = count * 3600.0 / drain_sec * multiplier
            if observed_vph > 0.0:
                observed_vph = max(min_vph, observed_vph)
            cap_fallback = float(cfg.network.ramp_capacity_veh_h.get(ramp, max_default))
            cap = max(0.0, _as_float(max_by_ramp.get(ramp), max_default or cap_fallback))
            if cap <= 0.0:
                cap = cap_fallback
            observed_vph = clamp(observed_vph, 0.0, cap)
            if blend == "replace":
                ramp_arrival[ramp] = observed_vph
            elif blend == "add":
                ramp_arrival[ramp] = max(0.0, float(ramp_arrival.get(ramp, 0.0)) + observed_vph)
            else:
                ramp_arrival[ramp] = max(float(ramp_arrival.get(ramp, 0.0)), observed_vph)

    return freeway_mainline, urban_boundary, ramp_arrival, profile


def demand_from_state(
    state_json: dict[str, Any],
    cfg,
    DemandStep,
    horizon_steps: int,
    calibration: Mapping[str, Any] | None = None,
    detector_mapping: Mapping[str, Any] | None = None,
):
    freeway_mainline, urban_boundary, ramp_arrival, _profile = profiled_demand_rates(
        state_json,
        cfg,
        calibration,
        detector_mapping,
    )
    step = DemandStep(
        freeway_mainline=freeway_mainline,
        urban_boundary=urban_boundary,
        ramp_arrival=ramp_arrival,
        incident_capacity_factor=1.0,
        freeway_lane_loss={},
    )
    return [step for _ in range(max(1, int(horizon_steps)))]


def warm_start_release_buffers(state, cfg, state_json: Mapping[str, Any], calibration, detector_mapping):
    """release 스케줄을 **plant 가 스스로 짓게** 한 뒤 관측 점유량으로 되돌린다.

    ## 왜

    투영은 저류 점유량만 싣고 `urban_storage_release_buffer` 를 비워 둔다. plant 의 방출은
    전적으로 그 버퍼에 물려 있어(urban_queue_model.py:962-973, :994) 빈 버퍼로 시작하면
    내부 링크는 동결되고 sink 는 즉시 전량 방출된다. **어댑터는 결정마다 상태를 다시
    짓기 때문에 모든 제어 결정이 그 상태에서 출발한다.**

    버퍼를 손으로 지어 넣는 것은 실패했다(유출만 복원되어 -37.4% 로 무너진다). 대신
    현재 관측에서 W 초를 무제어로 굴려 plant 가 자기 규약대로 스케줄을 만들게 하고,
    점유량은 관측값으로 되돌린다. 스케줄은 **같은 비율로** 줄여 모양을 보존한다.

    ## 실측 (보존 단위, anchor 1500/2100, 3셀, 스텝 1 / G5 통과 / 부호)

        기준선(꺼짐)      51.7%   29.2%   -25.8%
        self warm 300     47.5%   37.1%   -11.8%
        self warm 900     42.9%   38.8%    -6.7%

    남는 ~43% 는 plant 대 VISSIM 의 실재하는 동역학 오차이고 이 함수의 몫이 아니다.

    ## 비용

    모델 한 스텝이 약 0.21 초라 15 스텝이 결정당 ~3 초다. 60 초 제어주기 안에서 감당된다.

    기본은 **꺼짐**이다. `RW_WARMSTART_SEC` 에 초를 넣으면 켜진다(예: 900).
    """
    stats = {"warmstart_sec": 0.0, "steps": 0.0, "rescaled_links": 0.0}
    try:
        warm_sec = float(str(os.environ.get("RW_WARMSTART_SEC", str(DEFAULT_WARMSTART_SEC))).strip() or 0.0)
    except ValueError:
        warm_sec = 0.0
    if warm_sec <= 0.0:
        return stats
    # 바깥 `simulation` 도 가드한다. 실 cfg 는 항상 갖고 있어 거동은 같고, 이 필드가 없는
    # 축약 cfg(테스트 스텁 등)에서 warm-start 기본 켜짐이 통째로 터지던 것을 막는다.
    interval = float(getattr(getattr(cfg, "simulation", None), "control_interval", 60.0) or 60.0)
    steps = max(1, int(round(warm_sec / max(interval, 1.0e-9))))
    try:
        from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point

        repo_root = Path(DEFAULT_REPO_ROOT)
        _c, DemandStep, ControlAction, _e, _t, _v = repo_imports(repo_root)
        actuation = adapter_actuation_settings(calibration or {}, {})
        control = _guarded_no_control_baseline(ControlAction, cfg, state, dict(state_json), actuation)
        forecast = demand_from_state(dict(state_json), cfg, DemandStep, steps, calibration, detector_mapping)
        warmed = evaluate_price_point(
            state, control, list(forecast), (),
            ObjectiveSpec(cfg=cfg, depth_override=steps, box_walk=False),
        ).states[-1]
    except Exception as exc:  # noqa: BLE001 - warm-start 실패가 결정을 막으면 안 된다
        stats["error"] = f"{type(exc).__name__}: {exc}"
        return stats

    # 지은 스케줄을 현재 상태로 옮기고, 점유량은 관측값으로 되돌리며 예약을 같은 비율로 줄인다.
    capacity = cfg.network.urban_link_storage_veh
    observed_remaining = dict(getattr(state, "urban_link_storage", {}) or {})
    warm_buffer = getattr(warmed, "urban_storage_release_buffer", {}) or {}
    target_buffer = getattr(state, "urban_storage_release_buffer", None)
    if not isinstance(target_buffer, dict):
        return stats
    for link, cap in capacity.items():
        cap = float(cap)
        target_occ = max(0.0, cap - float(observed_remaining.get(link, cap)))
        warm_occ = max(0.0, cap - float((getattr(warmed, "urban_link_storage", {}) or {}).get(link, cap)))
        pending = warm_buffer.get(str(link)) or {}
        if not pending:
            continue
        ratio = (target_occ / warm_occ) if warm_occ > 1.0e-9 else 0.0
        if ratio <= 0.0:
            continue
        target_buffer[str(link)] = {int(k): float(v) * ratio for k, v in pending.items()}
        stats["rescaled_links"] += 1.0
    stats["warmstart_sec"] = warm_sec
    stats["steps"] = float(steps)
    return stats


def restore_urban_release_buffers(state, cfg, local_summary: Mapping[str, Any]) -> dict[str, float]:
    """관측에서 저류의 **이동 중 예약**을 복원한다.

    ## 왜 필요한가 (2026-08-15 실측으로 밝힌 결함)

    투영은 저류 **점유량만** 싣고 `urban_storage_release_buffer` 를 비워 둔다. 그런데
    plant 의 방출은 전적으로 그 버퍼에 물려 있다.

        내부 링크   `released = _pop_buffer(...)` 가 >0 일 때만 available 복원
                    (urban_queue_model.py:962-973) -> 버퍼가 비면 **영원히 안 빠진다**
        sink(_out)  `arrived = occupancy - _pending_in_transit(...)` (:994)
                    -> 버퍼가 비면 **점유 전량이 즉시 방출 후보**가 된다

    그래서 첫 스텝에 내부 링크는 동결되어 유입만 쌓이고(+114~208%), sink 는 통째로
    비워진다(정확히 -100%). 저류별 APE 중앙값이 스텝 0 에서 0.0% 인데 스텝 1 에서
    54.8% 로 튀고 그 뒤 평평한 것이 이 재배치다.

    sink 코드의 주석이 그 뺄셈을 넣은 이유를 직접 적어 놨다 - 안 빼면 "진입 substep 에
    곧바로 이탈해 out 링크 통행시간이 0". 버퍼가 비면 그 옛 버그가 그대로 재현된다.

    ## 어떻게 복원하는가

    추정하지 않는다. 관측이 정지/이동을 갈라 준다.

        정지 대수      정지선에 이미 도착한 몫. 예약 없이 둔다(즉시 방출 가능).
        점유 - 정지    아직 이동 중. plant 자신의 `_link_delay_steps` 로 만기 스텝을
                       구해 1..delay 에 **균등 분산**한다. 정상류가 계속 진입해 온
                       링크의 정상상태 분포가 균등이기 때문이다.

    내부 링크는 예약이 없으면 동결되므로 정지 몫도 다음 substep 에 만기로 넣는다.
    sink 는 정지 몫을 예약하지 않아야 출구 게이트가 내보낸다.

    되돌릴 수 있게 기본은 **꺼짐**이다. `RW_RESTORE_RELEASE_BUFFERS=1` 로 켠다.
    """
    stats = {"links": 0.0, "in_transit_veh": 0.0, "arrived_veh": 0.0}
    mode = str(os.environ.get("RW_RESTORE_RELEASE_BUFFERS", "")).strip().lower()
    # off(기본) / sinks(sink 만) / all(전부). 실측상 all 은 더 나쁘다 - 아래 주석 참조.
    if mode in {"", "0", "off", "false"}:
        return stats
    if mode in {"1", "true"}:
        mode = "all"
    if mode not in {"sinks", "all"}:
        return stats
    buffer = getattr(state, "urban_storage_release_buffer", None)
    if not isinstance(buffer, dict):
        return stats
    try:
        from src.models.urban_queue_model import _link_delay_steps, _schedule, sink_storage_links
    except Exception:  # noqa: BLE001 - 상류 스냅샷에 없으면 조용히 건너뛴다(기존 거동 유지)
        return stats

    occupancy_by_link = _mapping(local_summary.get("urban_link_storage_occupancy"))
    stopped_by_link = _mapping(local_summary.get("urban_link_storage_stopped"))
    sinks = set(sink_storage_links(cfg))
    step_sec = max(float(cfg.simulation.T_u_sec), 1.0e-9)
    start_step = int(round(float(getattr(state, "time_sec", 0.0)) / step_sec))

    for link in cfg.network.urban_link_storage_veh:
        if mode == "sinks" and str(link) not in sinks:
            continue
        occupied = max(0.0, _as_float(occupancy_by_link.get(link, 0.0)))
        if occupied <= 0.0:
            continue
        stopped = min(occupied, max(0.0, _as_float(stopped_by_link.get(link, 0.0))))
        moving = max(0.0, occupied - stopped)
        # 지연은 plant 자신의 산식으로 잰다 - 여기서 다른 규칙을 쓰면 첫 스텝에 또 어긋난다.
        delay = max(1, int(_link_delay_steps(state, cfg, str(link))))
        if moving > 0.0:
            per = moving / float(delay)
            for k in range(1, delay + 1):
                _schedule(buffer, str(link), start_step + k, per)
            stats["in_transit_veh"] += moving
        if stopped > 0.0 and str(link) not in sinks:
            # 내부 링크는 예약이 없으면 동결된다. 도착분은 바로 다음 substep 만기.
            _schedule(buffer, str(link), start_step + 1, stopped)
        stats["arrived_veh"] += stopped
        stats["links"] += 1.0
    return stats


def traffic_state_from_vissim(
    state_json: dict[str, Any],
    cfg,
    TrafficState,
    detector_mapping: Mapping[str, Any] | None = None,
    calibration: Mapping[str, Any] | None = None,
    physical_projection_input: Mapping[str, Any] | None = None,
):
    state = TrafficState.initial(cfg)
    state.time_sec = float(state_json.get("sim_sec", 0.0))
    state.ensure_freeway_lane_profile(cfg.network)

    segs = state_json.get("freeway_segments", {})
    for link in cfg.network.freeway_links:
        rows = list(segs.get(link, []))
        densities: list[float] = []
        speeds: list[float] = []
        flows: list[float] = []
        lanes_profile: list[float] = []
        for i in range(cfg.network.freeway_segments_per_link):
            row = rows[i] if i < len(rows) and isinstance(rows[i], dict) else {}
            count = max(0.0, float(row.get("count", 0.0)))
            speed_sum = max(0.0, float(row.get("speed_sum", 0.0)))
            length_km = max(1.0e-6, float(row.get("length_km", cfg.network.freeway_segment_length_km)))
            lanes = max(1.0, float(row.get("lanes", cfg.network.freeway_lanes)))
            speed = speed_sum / count if count > 1.0e-9 else float(cfg.network.v_free)
            density = count / (length_km * lanes)
            densities.append(float(density))
            speeds.append(float(speed))
            flows.append(float(density * speed * lanes))
            lanes_profile.append(float(lanes))
        state.freeway_density[link] = densities
        state.freeway_speed[link] = speeds
        state.freeway_flow[link] = flows
        state.freeway_effective_lanes[link] = lanes_profile

    local_summary = (
        build_local_observation_summary(
            state_json, cfg, detector_mapping or {}, calibration
        )
        if detector_mapping or physical_projection_input is not None
        else {}
    )
    if local_summary:
        for key in state.ramp_queue:
            state.ramp_queue[key] = float(local_summary["ramp_queue"].get(key, 0.0))
        for key in state.boundary_queue:
            state.boundary_queue[key] = float(local_summary["boundary_queue"].get(key, 0.0))
        for key in state.urban_movement_queue:
            state.urban_movement_queue[key] = float(local_summary["urban_movement_queue"].get(key, 0.0))
        storage_occupancy = local_summary.get("urban_link_storage_occupancy", {})
        if isinstance(storage_occupancy, Mapping):
            for link, capacity in cfg.network.urban_link_storage_veh.items():
                occupied = clamp(
                    _as_float(storage_occupancy.get(link, 0.0)),
                    0.0,
                    float(capacity),
                )
                state.urban_link_storage[link] = float(capacity) - occupied
        # 관측 링크속도를 상태에 싣는다(v3 N3-1b). `_link_delay_steps` 가 이걸 보고
        # 전역 `urban_avg_speed_km_h` 대신 링크별 통과시간을 잰다.
        # `hasattr` 가드가 필요한 이유 — 실런 기본 모델 저장소가 `vendor/NumSim-mine`
        # (해시고정 스냅샷, DEFAULT_REPO_ROOT:55-59)이고 그 TrafficState 에는 아직 이 필드가
        # 없다. 상류 재스냅샷 전까지는 조용히 건너뛰고 기존 거동(전역 상수)을 유지한다.
        observed_speeds = local_summary.get("urban_link_speed_kph", {})
        if isinstance(observed_speeds, Mapping) and hasattr(state, "urban_link_speed_kph"):
            for link, speed_kph in observed_speeds.items():
                if str(link) in cfg.network.urban_link_storage_veh:
                    state.urban_link_speed_kph[str(link)] = max(0.0, _as_float(speed_kph))
            _apply_lane_delay_correction(state, cfg, local_summary)
        restore_urban_release_buffers(state, cfg, local_summary)
        # 버퍼를 손으로 짓지 않고 plant 가 짓게 하는 경로. 기본 꺼짐(RW_WARMSTART_SEC).
        state.warmstart_diagnostics = warm_start_release_buffers(
            state, cfg, state_json, calibration, detector_mapping
        )
        state.local_observation_summary = local_summary
    else:
        ramp_counts = state_json.get("ramp_counts", {})
        if isinstance(ramp_counts, Mapping) and any(str(key) in ramp_counts for key in state.ramp_queue):
            for key in state.ramp_queue:
                state.ramp_queue[key] = max(0.0, _as_float(ramp_counts.get(str(key), 0.0)))
        else:
            d_queue = max(0.0, float(ramp_counts.get("D", 0.0)))
            f_queue = max(0.0, float(ramp_counts.get("F", 0.0)))
            state.ramp_queue.update({
                "R_D_W": d_queue / 2.0,
                "R_D_E": d_queue / 2.0,
                "R_F_W": f_queue / 2.0,
                "R_F_E": f_queue / 2.0,
            })

        # Legacy global-state fallback for old state files. Local detector
        # observation must be preferred whenever it is present.
        urban_total = max(0.0, float(state_json.get("urban_vehicles", 0.0)))
        boundary_total = max(0.0, float(state_json.get("boundary_vehicles", 0.0)))
        if state.boundary_queue:
            per = boundary_total / max(1, len(state.boundary_queue))
            for key in state.boundary_queue:
                state.boundary_queue[key] = per
        if state.urban_movement_queue:
            protected_kinds = {"internal", "boundary_out", "off_ramp"}
            protected_movements = [
                movement
                for movement, spec in cfg.network.urban_movements.items()
                if str(spec.get("kind", "")) in protected_kinds
                and movement in state.urban_movement_queue
            ]
            boundary_in_movements = [
                movement
                for movement, spec in cfg.network.urban_movements.items()
                if str(spec.get("kind", "")) == "boundary_in"
                and movement in state.urban_movement_queue
            ]
            for key in state.urban_movement_queue:
                state.urban_movement_queue[key] = 0.0
            if protected_movements:
                per_protected = urban_total / max(1, len(protected_movements))
                for key in protected_movements:
                    state.urban_movement_queue[key] = per_protected
            elif state.urban_movement_queue:
                per = urban_total / max(1, len(state.urban_movement_queue))
                for key in state.urban_movement_queue:
                    state.urban_movement_queue[key] = per
            if boundary_in_movements:
                per_boundary = boundary_total / max(1, len(boundary_in_movements))
                for key in boundary_in_movements:
                    state.urban_movement_queue[key] = per_boundary
    if physical_projection_input is not None:
        # The B1a ledger is a required state-construction input. B1b remains
        # responsible for defining stock-to-dynamics transfer semantics.
        state.physical_projection_input = physical_projection_input
        state.physical_projection_ledger = physical_projection_input["ledger"]
    return state


def control_from_json(path: Path, cfg, ControlAction):
    if not path.exists():
        return ControlAction.fixed(cfg)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ControlAction(
        N_P_star=float(raw.get("N_P_star", 0.0)),
        N_UF_star=float(raw.get("N_UF_star", 0.0)),
        ramp_metering={str(k): float(v) for k, v in raw.get("ramp_metering", {}).items()},
        vsl={str(k): float(v) for k, v in raw.get("vsl", {}).items()},
        green_times={str(k): float(v) for k, v in raw.get("green_times", {}).items()},
        offsets={str(k): float(v) for k, v in raw.get("offsets", {}).items()},
        inflow_outflow_allocation={
            str(k): float(v) for k, v in raw.get("inflow_outflow_allocation", {}).items()
        },
        diagnostics=dict(raw.get("diagnostics", {})),
    )


def control_to_json_dict(
    control,
    metadata: dict[str, Any],
    prediction: dict[str, Any] | None = None,
    prediction_error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "N_P_star": float(control.N_P_star),
        "N_UF_star": float(control.N_UF_star),
        "ramp_metering": {str(k): float(v) for k, v in control.ramp_metering.items()},
        "vsl": {str(k): float(v) for k, v in control.vsl.items()},
        "green_times": {str(k): float(v) for k, v in control.green_times.items()},
        "offsets": {str(k): float(v) for k, v in control.offsets.items()},
        "inflow_outflow_allocation": {
            str(k): float(v) for k, v in control.inflow_outflow_allocation.items()
        },
        "diagnostics": dict(control.diagnostics),
        "metadata": metadata,
    }
    run_provenance = metadata.get("run_provenance")
    if isinstance(run_provenance, Mapping):
        payload["run_provenance"] = dict(run_provenance)
    projection_diagnostics = metadata.get("projection_diagnostics")
    if isinstance(projection_diagnostics, Mapping):
        payload["projection_diagnostics"] = dict(projection_diagnostics)
    projection_provenance = metadata.get("physical_projection_provenance")
    if isinstance(projection_provenance, Mapping):
        payload["physical_projection_provenance"] = dict(projection_provenance)
    if prediction:
        payload["prediction"] = prediction
    if prediction_error:
        payload["prediction_error"] = prediction_error
    return payload


PREDICTION_AUDIT_SCALARS = [
    "total_model_vehicles",
    "urban_total_veh",
    "protected_accumulation_veh",
    "urban_queue_plus_link_occupancy_total_veh",
    "urban_movement_queue_total_veh",
    "urban_link_occupancy_total_veh",
    "boundary_queue_total_veh",
    "freeway_total_veh",
    "freeway_segment_total_veh",
    "off_ramp_storage_veh",
    "ramp_queue_total_veh",
    "mainline_origin_queue_total_veh",
    "freeway_mean_density_veh_km_lane",
    "freeway_mean_speed_kph",
]


def summarize_model_state(state, cfg) -> dict[str, Any]:
    net = cfg.network
    state.ensure_freeway_lane_profile(net)
    freeway_counts = _freeway_vehicle_count_by_link(state, cfg)
    freeway_segment_counts = {
        link: [float(v) for v in freeway_counts.get(link, [])]
        for link in net.freeway_links
    }
    freeway_segment_total = float(sum(sum(values) for values in freeway_segment_counts.values()))
    speed_weight = 0.0
    vehicle_weight = 0.0
    density_sum = 0.0
    density_n = 0
    for link in net.freeway_links:
        speeds = list(state.freeway_speed.get(link, []))
        densities = list(state.freeway_density.get(link, []))
        counts = freeway_counts.get(link, [])
        for i, rho in enumerate(densities):
            density_sum += float(rho)
            density_n += 1
            count = float(counts[i]) if i < len(counts) else 0.0
            speed = float(speeds[i]) if i < len(speeds) else float(net.v_free)
            speed_weight += speed * max(0.0, count)
            vehicle_weight += max(0.0, count)
    urban_link_occupancy = 0.0
    for link, capacity in net.urban_link_storage_veh.items():
        urban_link_occupancy += max(0.0, float(capacity) - float(state.urban_link_storage.get(link, capacity)))
    ramp_queue_total = float(sum(max(0.0, float(v)) for v in state.ramp_queue.values()))
    mainline_origin_queue_total = float(
        sum(max(0.0, float(v)) for v in state.mainline_origin_queue.values())
    )
    urban_total = float(state.total_urban_vehicles(net))
    freeway_total = freeway_segment_total
    off_ramp_storage = float(state.off_ramp_storage_occupancy_veh(net))
    return {
        "time_sec": float(getattr(state, "time_sec", 0.0)),
        "total_model_vehicles": float(urban_total + freeway_total + off_ramp_storage),
        "urban_total_veh": urban_total,
        "protected_accumulation_veh": float(state.protected_accumulation_veh(net)),
        "urban_queue_plus_link_occupancy_total_veh": float(
            sum(max(0.0, float(v)) for v in state.urban_movement_queue.values())
            + urban_link_occupancy
        ),
        "urban_movement_queue_total_veh": float(
            sum(max(0.0, float(v)) for v in state.urban_movement_queue.values())
        ),
        "urban_link_occupancy_total_veh": float(urban_link_occupancy),
        "boundary_queue_total_veh": float(sum(max(0.0, float(v)) for v in state.boundary_queue.values())),
        "freeway_total_veh": freeway_total,
        "freeway_segment_total_veh": freeway_segment_total,
        "off_ramp_storage_veh": off_ramp_storage,
        "ramp_queue_total_veh": ramp_queue_total,
        "mainline_origin_queue_total_veh": mainline_origin_queue_total,
        "freeway_mean_density_veh_km_lane": float(density_sum / density_n) if density_n else 0.0,
        "freeway_mean_speed_kph": float(speed_weight / vehicle_weight) if vehicle_weight > 1.0e-9 else float(net.v_free),
        "ramp_queue": {str(k): float(v) for k, v in sorted(state.ramp_queue.items())},
        "freeway_segment_vehicles": freeway_segment_counts,
    }


def apply_prediction_audit_calibration(
    summary: Mapping[str, Any],
    calibration: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, float]]:
    prediction = _mapping((calibration or {}).get("prediction"))
    audit = _mapping(prediction.get("audit_calibration"))
    if not audit:
        return {}, {}

    enabled = bool(audit.get("enabled", True))
    if not enabled:
        return {}, {}

    freeway_scale = _as_float(
        audit.get("freeway_total_scale", audit.get("freeway_total_observed_over_predicted_mean")),
        1.0,
    )
    urban_mass_scale = _as_float(
        audit.get(
            "urban_queue_plus_storage_scale",
            audit.get("urban_queue_plus_storage_observed_over_predicted_mean"),
        ),
        1.0,
    )
    if not (0.05 <= freeway_scale <= 5.0):
        freeway_scale = 1.0
    if not (0.05 <= urban_mass_scale <= 5.0):
        urban_mass_scale = 1.0

    calibrated = dict(summary)
    metadata: dict[str, float] = {}
    old_freeway = _as_float(summary.get("freeway_total_veh"), 0.0)
    old_freeway_segment = _as_float(summary.get("freeway_segment_total_veh"), old_freeway)
    new_freeway = old_freeway * freeway_scale
    new_freeway_segment = old_freeway_segment * freeway_scale
    calibrated["freeway_total_veh"] = float(new_freeway)
    calibrated["freeway_segment_total_veh"] = float(new_freeway_segment)
    calibrated["freeway_mean_density_veh_km_lane"] = float(
        _as_float(summary.get("freeway_mean_density_veh_km_lane"), 0.0) * freeway_scale
    )
    calibrated["total_model_vehicles"] = float(
        _as_float(summary.get("total_model_vehicles"), 0.0) + (new_freeway - old_freeway)
    )
    segment_vehicles = summary.get("freeway_segment_vehicles", {})
    if isinstance(segment_vehicles, Mapping):
        calibrated["freeway_segment_vehicles"] = {
            str(link): [
                float(_as_float(value) * freeway_scale)
                for value in values
            ]
            for link, values in segment_vehicles.items()
            if isinstance(values, list)
        }

    component_scales = _mapping(audit.get("component_scales"))
    recompute_queue_storage = bool(
        audit.get(
            "recompute_urban_queue_plus_storage_from_components",
            audit.get("preserve_component_consistency", False),
        )
    )
    recompute_urban_total = bool(
        audit.get(
            "recompute_urban_total_from_components",
            audit.get("preserve_component_consistency", False),
        )
    )
    recompute_model_total = bool(
        audit.get(
            "recompute_total_model_vehicles_from_components",
            audit.get("preserve_component_consistency", False),
        )
    )
    scale_aliases = {
        "total_model_vehicles": "total_model_vehicles_scale",
        "urban_total_veh": "urban_total_scale",
        "protected_accumulation_veh": "protected_accumulation_scale",
        "urban_movement_queue_total_veh": "urban_movement_queue_scale",
        "urban_link_occupancy_total_veh": "urban_link_occupancy_scale",
        "boundary_queue_total_veh": "boundary_queue_scale",
        "off_ramp_storage_veh": "off_ramp_storage_scale",
        "ramp_queue_total_veh": "ramp_queue_scale",
        "mainline_origin_queue_total_veh": "mainline_origin_queue_scale",
        "freeway_mean_speed_kph": "freeway_mean_speed_scale",
    }
    already_scaled = {
        "freeway_total_veh",
        "freeway_segment_total_veh",
        "freeway_mean_density_veh_km_lane",
        "urban_queue_plus_link_occupancy_total_veh",
    }
    scaled_metrics: set[str] = set()
    for metric, alias in scale_aliases.items():
        raw_scale = component_scales.get(metric, audit.get(alias))
        if raw_scale is None or metric in already_scaled or metric not in summary:
            continue
        scale = _as_float(raw_scale, 1.0)
        if not (0.05 <= scale <= 5.0):
            continue
        calibrated[metric] = float(_as_float(summary.get(metric), 0.0) * scale)
        metadata[f"prediction_audit_{metric}_scale"] = float(scale)
        scaled_metrics.add(metric)

    if "urban_queue_plus_link_occupancy_total_veh" in summary:
        if recompute_queue_storage and {
            "urban_movement_queue_total_veh",
            "urban_link_occupancy_total_veh",
        } & scaled_metrics:
            calibrated["urban_queue_plus_link_occupancy_total_veh"] = float(
                _as_float(calibrated.get("urban_movement_queue_total_veh"), 0.0)
                + _as_float(calibrated.get("urban_link_occupancy_total_veh"), 0.0)
            )
            metadata["prediction_audit_urban_queue_plus_storage_recomputed"] = 1.0
        else:
            calibrated["urban_queue_plus_link_occupancy_total_veh"] = float(
                _as_float(summary.get("urban_queue_plus_link_occupancy_total_veh"), 0.0)
                * urban_mass_scale
            )

    if recompute_urban_total and {
        "urban_movement_queue_total_veh",
        "urban_link_occupancy_total_veh",
        "off_ramp_storage_veh",
    } & scaled_metrics:
        movement = _as_float(calibrated.get("urban_movement_queue_total_veh"), 0.0)
        link_occupancy = _as_float(calibrated.get("urban_link_occupancy_total_veh"), 0.0)
        off_ramp_storage = _as_float(calibrated.get("off_ramp_storage_veh"), 0.0)
        calibrated["urban_total_veh"] = float(movement + max(0.0, link_occupancy - off_ramp_storage))
        metadata["prediction_audit_urban_total_recomputed"] = 1.0

    if recompute_model_total and {
        "urban_total_veh",
        "freeway_total_veh",
        "off_ramp_storage_veh",
        "urban_movement_queue_total_veh",
        "urban_link_occupancy_total_veh",
    } & (scaled_metrics | {"freeway_total_veh"}):
        calibrated["total_model_vehicles"] = float(
            _as_float(calibrated.get("urban_total_veh"), 0.0)
            + _as_float(calibrated.get("freeway_total_veh"), 0.0)
            + _as_float(calibrated.get("off_ramp_storage_veh"), 0.0)
        )
        metadata["prediction_audit_total_model_vehicles_recomputed"] = 1.0

    metadata.update({
        "prediction_audit_calibration_applied": 1.0,
        "prediction_audit_freeway_total_scale": float(freeway_scale),
        "prediction_audit_urban_queue_plus_storage_scale": float(urban_mass_scale),
    })
    return calibrated, metadata


def _workspace_path(path_text: str, default: Path | None = None) -> Path:
    if not path_text:
        return default if default is not None else WORKSPACE_ROOT
    path = Path(path_text)
    if path.is_absolute():
        return path
    return WORKSPACE_ROOT / path


def install_adapter_calibration_fingerprints(cfg, tuning: Mapping[str, Any]) -> dict[str, float]:
    """Mark canary-protected components as calibrated for the current VISSIM geometry.

    The upstream controller stores component calibration fingerprints as module
    globals. In this workspace we cannot edit the external Numerical-Sim checkout,
    so VISSIM-specific tuning can explicitly declare that those components have
    been revalidated against the current 8-seg merge map.
    """
    settings = _mapping(_mapping(tuning.get("adapter")).get("calibration_fingerprints"))
    if str(settings.get("mode", "")).lower() != "current_vissim_geometry":
        return {}
    components = settings.get("components", ["leader_hinge", "np_deadband", "leader_mfd_far"])
    if not isinstance(components, list):
        components = ["leader_hinge", "np_deadband", "leader_mfd_far"]
    merge_map = {
        str(key): int(value)
        for key, value in dict(getattr(cfg.network, "ramp_merge_segment_index", {}) or {}).items()
    }
    if not merge_map:
        return {}
    try:
        from src.controllers import stackelberg_mpc as stackelberg_module

        for component in components:
            stackelberg_module.CALIBRATION_FINGERPRINTS[str(component)] = {
                "ramp_merge": dict(merge_map),
            }
        if hasattr(stackelberg_module, "_calib_fingerprint_warned"):
            stackelberg_module._calib_fingerprint_warned.clear()
    except Exception:
        return {"adapter_calibration_fingerprint_override_failed": 1.0}
    return {
        "adapter_calibration_fingerprint_override_active": 1.0,
        "adapter_calibration_fingerprint_component_count": float(len(components)),
        "adapter_calibration_fingerprint_merge_R_D_W": float(merge_map.get("R_D_W", -1)),
        "adapter_calibration_fingerprint_merge_R_F_W": float(merge_map.get("R_F_W", -1)),
        "adapter_calibration_fingerprint_merge_R_D_E": float(merge_map.get("R_D_E", -1)),
        "adapter_calibration_fingerprint_merge_R_F_E": float(merge_map.get("R_F_E", -1)),
    }


def _freeway_excess_vehicle_proxy(state, cfg) -> float:
    net = cfg.network
    state.ensure_freeway_lane_profile(net)
    excess = 0.0
    for link, densities in getattr(state, "freeway_density", {}).items():
        lanes = getattr(state, "freeway_effective_lanes", {}).get(link, [])
        for idx, rho in enumerate(densities):
            lane_count = float(lanes[idx]) if idx < len(lanes) else float(net.freeway_lanes)
            excess += (
                max(0.0, _as_float(rho) - float(net.rho_crit))
                * float(net.freeway_segment_length_km)
                * max(1.0e-9, lane_count)
            )
    return float(excess)


def vissim_terminal_feature_vector(state, cfg) -> dict[str, float]:
    """Map a model-predicted state to the aggregate fields used by VISSIM CSV fits."""
    net = cfg.network
    summary = summarize_model_state(state, cfg)
    freeway = max(0.0, _as_float(summary.get("freeway_segment_total_veh")))
    ramp = max(0.0, _as_float(summary.get("ramp_queue_total_veh"))) + max(
        0.0, _as_float(summary.get("off_ramp_storage_veh"))
    )
    boundary = max(0.0, _boundary_in_queue_veh(state, cfg))
    urban_total = max(0.0, _as_float(summary.get("urban_total_veh")))
    urban = max(0.0, urban_total - boundary)
    mainline_origin = max(0.0, _as_float(summary.get("mainline_origin_queue_total_veh")))
    total = freeway + urban + ramp + boundary + mainline_origin
    urban_queue = max(0.0, _as_float(summary.get("urban_movement_queue_total_veh")))
    stopped = min(
        total,
        ramp
        + boundary
        + 0.5 * max(0.0, urban_queue - boundary)
        + _freeway_excess_vehicle_proxy(state, cfg),
    )
    freeway_speed = max(0.0, _as_float(summary.get("freeway_mean_speed_kph"), float(net.v_free)))
    urban_speed = max(0.0, float(getattr(net, "urban_avg_speed_km_h", 50.0)))
    ramp_speed = 15.0
    boundary_speed = 5.0
    mean_speed = (
        freeway * freeway_speed
        + urban * urban_speed
        + ramp * ramp_speed
        + boundary * boundary_speed
    ) / max(total, 1.0e-9)
    return {
        "total_vehicles": float(total),
        "urban_vehicles": float(urban),
        "freeway_vehicles": float(freeway),
        "ramp_vehicles": float(ramp),
        "boundary_vehicles": float(boundary),
        "stopped_vehicles": float(stopped),
        "mean_speed_kph": float(mean_speed),
        "freeway_mean_speed_kph": float(freeway_speed),
    }


def vissim_terminal_feature_vector_from_summary(summary: Mapping[str, Any], cfg) -> dict[str, float]:
    """Best-effort terminal features from a serialized prediction summary."""
    net = cfg.network
    freeway = max(0.0, _as_float(summary.get("freeway_segment_total_veh")))
    ramp = max(0.0, _as_float(summary.get("ramp_queue_total_veh"))) + max(
        0.0, _as_float(summary.get("off_ramp_storage_veh"))
    )
    boundary = max(0.0, _as_float(summary.get("boundary_queue_total_veh")))
    urban_total = max(0.0, _as_float(summary.get("urban_total_veh")))
    urban = max(0.0, urban_total - boundary)
    mainline_origin = max(0.0, _as_float(summary.get("mainline_origin_queue_total_veh")))
    total = freeway + urban + ramp + boundary + mainline_origin
    urban_queue = max(0.0, _as_float(summary.get("urban_movement_queue_total_veh")))
    stopped = _as_float(summary.get("stopped_vehicles"), -1.0)
    if stopped < 0.0:
        stopped = min(total, ramp + boundary + 0.5 * max(0.0, urban_queue - boundary))
    else:
        stopped = max(0.0, stopped)
    freeway_speed = max(0.0, _as_float(summary.get("freeway_mean_speed_kph"), float(net.v_free)))
    urban_speed = max(0.0, float(getattr(net, "urban_avg_speed_km_h", 50.0)))
    ramp_speed = 15.0
    boundary_speed = 5.0
    mean_speed = (
        freeway * freeway_speed
        + urban * urban_speed
        + ramp * ramp_speed
        + boundary * boundary_speed
    ) / max(total, 1.0e-9)
    return {
        "total_vehicles": float(total),
        "urban_vehicles": float(urban),
        "freeway_vehicles": float(freeway),
        "ramp_vehicles": float(ramp),
        "boundary_vehicles": float(boundary),
        "stopped_vehicles": float(stopped),
        "mean_speed_kph": float(mean_speed),
        "freeway_mean_speed_kph": float(freeway_speed),
    }


def install_vissim_terminal_cost_objective(controller, cfg, tuning: Mapping[str, Any]) -> dict[str, float]:
    settings = _mapping(_mapping(tuning.get("adapter")).get("terminal_cost"))
    if not bool(settings.get("enabled", False)):
        return {}
    fit_path = _workspace_path(
        str(settings.get("fit_json", "evaluation/calibration/vissim_terminal_cost_fit_20260715.json"))
    )
    try:
        fit = json.loads(fit_path.read_text(encoding="utf-8"))
    except Exception:
        return {"adapter_vissim_terminal_cost_load_failed": 1.0}
    raw_coefficients = _mapping(fit.get("raw_coefficients"))
    features = settings.get("features", fit.get("features", []))
    if not isinstance(features, list):
        features = list(raw_coefficients)
    coefficient_mode = str(settings.get("coefficient_mode", "positive_only")).lower()
    include_intercept = bool(settings.get("include_intercept", False))
    clamp_nonnegative = bool(settings.get("clamp_nonnegative", True))
    weight = _as_float(settings.get("weight"), 1.0)
    intercept = _as_float(fit.get("raw_intercept"), 0.0) if include_intercept else 0.0
    used: dict[str, float] = {}
    for feature in features:
        name = str(feature)
        coef = _as_float(raw_coefficients.get(name), 0.0)
        if coefficient_mode == "positive_only" and coef <= 0.0:
            continue
        used[name] = float(coef)
    if not used and abs(intercept) <= 1.0e-12:
        return {"adapter_vissim_terminal_cost_empty": 1.0}

    original_objective_terms = controller.leader.objective_terms

    def objective_terms_with_vissim_terminal(
        predicted_states,
        action,
        previous,
        follower_objective,
        nash_converged,
        nash_residual_objective=0.0,
        nash_residual_control=0.0,
    ):
        states = list(predicted_states)
        terms = original_objective_terms(
            states,
            action,
            previous,
            follower_objective,
            nash_converged,
            nash_residual_objective,
            nash_residual_control,
        )
        if not states:
            return terms
        vector = vissim_terminal_feature_vector(states[-1], cfg)
        raw = float(intercept)
        for feature, coef in used.items():
            value = float(vector.get(feature, 0.0))
            raw += coef * value
            terms[f"leader_vissim_terminal_feature_{feature}"] = value
            terms[f"leader_vissim_terminal_coef_{feature}"] = float(coef)
        if clamp_nonnegative:
            raw = max(0.0, raw)
        penalty = weight * raw
        terms["leader_vissim_terminal_cost_active"] = 1.0
        terms["leader_vissim_terminal_cost_raw_veh_h"] = float(raw)
        terms["leader_vissim_terminal_cost_weight"] = float(weight)
        terms["leader_vissim_terminal_cost_penalty"] = float(penalty)
        terms["leader_vissim_terminal_cost_feature_count"] = float(len(used))
        terms["leader_total_objective"] = float(terms.get("leader_total_objective", 0.0)) + penalty
        return terms

    controller.leader.objective_terms = objective_terms_with_vissim_terminal
    return {
        "adapter_vissim_terminal_cost_active": 1.0,
        "adapter_vissim_terminal_cost_weight": float(weight),
        "adapter_vissim_terminal_cost_feature_count": float(len(used)),
        "adapter_vissim_terminal_cost_horizon_sec": _as_float(fit.get("horizon_sec"), 0.0),
        "adapter_vissim_terminal_cost_fit_r2": _as_float(_mapping(fit.get("metrics")).get("r2"), 0.0),
    }


def build_one_step_prediction(state, control, forecast, cfg, calibration: Mapping[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        from src.controllers.rollout_endpoint import ObjectiveSpec, evaluate_price_point

        demand = list(forecast)[0]
        # 한스텝 예측도 상류 rollout endpoint 를 거친다(N7 "우회 호출 0").
        predicted = evaluate_price_point(
            state,
            control,
            [demand],
            (),
            ObjectiveSpec(cfg=cfg, depth_override=1, box_walk=False),
        ).states[-1]
        predicted.time_sec = float(getattr(state, "time_sec", 0.0)) + float(cfg.simulation.control_interval)
        state_summary = summarize_model_state(predicted, cfg)
        try:
            terminal_features = vissim_terminal_feature_vector(predicted, cfg)
        except Exception:
            terminal_features = vissim_terminal_feature_vector_from_summary(state_summary, cfg)
        calibrated_summary, audit_metadata = apply_prediction_audit_calibration(state_summary, calibration)
        payload = {
            "schema_version": 1,
            "status": "ok",
            "mode": "coupled_interval_one_step",
            "from_sim_sec": float(getattr(state, "time_sec", 0.0)),
            "target_sim_sec": float(predicted.time_sec),
            "control_interval_sec": float(cfg.simulation.control_interval),
            "wall_sec": round(time.perf_counter() - started, 6),
            "state_summary": state_summary,
            "terminal_features": terminal_features,
        }
        if calibrated_summary:
            payload["calibrated_state_summary"] = calibrated_summary
            payload["audit_calibration"] = audit_metadata
        return payload
    except Exception as exc:
        return {
            "schema_version": 1,
            "status": "error",
            "mode": "coupled_interval_one_step",
            "from_sim_sec": float(getattr(state, "time_sec", 0.0)),
            "control_interval_sec": float(cfg.simulation.control_interval),
            "wall_sec": round(time.perf_counter() - started, 6),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def prediction_error_from_previous(previous_path: Path, observed_summary: Mapping[str, Any]) -> dict[str, Any]:
    if not previous_path.exists():
        return {}
    try:
        raw = json.loads(previous_path.read_text(encoding="utf-8"))
        prediction = raw.get("prediction", {})
        if not isinstance(prediction, Mapping) or prediction.get("status") != "ok":
            return {}
        predicted_summary = prediction.get("calibrated_state_summary", prediction.get("state_summary", {}))
        if not isinstance(predicted_summary, Mapping):
            return {}
        prediction_summary_kind = (
            "calibrated_state_summary"
            if isinstance(prediction.get("calibrated_state_summary"), Mapping)
            else "state_summary"
        )
        scalar_errors: dict[str, dict[str, float]] = {}
        abs_sum = 0.0
        count = 0
        for key in PREDICTION_AUDIT_SCALARS:
            if key not in predicted_summary or key not in observed_summary:
                continue
            predicted = float(predicted_summary.get(key, 0.0))
            observed = float(observed_summary.get(key, 0.0))
            error = observed - predicted
            scalar_errors[key] = {
                "predicted": predicted,
                "observed": observed,
                "error": error,
                "abs_error": abs(error),
                "relative_error": error / max(1.0, abs(predicted)),
            }
            abs_sum += abs(error)
            count += 1
        return {
            "schema_version": 1,
            "status": "ok",
            "source_action_json": str(previous_path),
            "predicted_from_sim_sec": float(prediction.get("from_sim_sec", 0.0)),
            "predicted_for_sim_sec": float(prediction.get("target_sim_sec", 0.0)),
            "observed_sim_sec": float(observed_summary.get("time_sec", 0.0)),
            "target_lag_sec": float(observed_summary.get("time_sec", 0.0)) - float(prediction.get("target_sim_sec", 0.0)),
            "prediction_summary_kind": prediction_summary_kind,
            "mean_abs_scalar_error": float(abs_sum / count) if count else 0.0,
            "scalar_errors": scalar_errors,
        }
    except Exception as exc:
        return {
            "schema_version": 1,
            "status": "error",
            "source_action_json": str(previous_path),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def green_from_release_map(rate_vph: float, curve: Mapping[str, Any], default_green: float = 10.0) -> float:
    points: list[tuple[float, float]] = []
    for green, release in curve.items():
        try:
            points.append((float(green), float(release)))
        except (TypeError, ValueError):
            continue
    if not points:
        return float(default_green)
    points = sorted(points, key=lambda item: item[0])
    monotone: list[tuple[float, float]] = []
    best_release = -1.0
    for green, release in points:
        best_release = max(best_release, release)
        monotone.append((green, best_release))
    rate = max(0.0, float(rate_vph))
    if rate <= monotone[0][1]:
        return monotone[0][0]
    for (g0, r0), (g1, r1) in zip(monotone, monotone[1:]):
        if rate <= r1:
            if r1 <= r0:
                return g1
            frac = (rate - r0) / (r1 - r0)
            return g0 + frac * (g1 - g0)
    return monotone[-1][0]


def physical_ramp_actions(control, cfg, actuation: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    cap = cfg.network.ramp_capacity_veh_h
    d_rate = (
        float(control.ramp_metering.get("R_D_W", cap.get("R_D_W", 1500.0)))
        + float(control.ramp_metering.get("R_D_E", cap.get("R_D_E", 1500.0)))
    ) / 2.0
    f_rate = (
        float(control.ramp_metering.get("R_F_W", cap.get("R_F_W", 1500.0)))
        + float(control.ramp_metering.get("R_F_E", cap.get("R_F_E", 1500.0)))
    ) / 2.0
    out = {}
    d_curve = actuation.get("D_green_to_release_vph", {})
    f_curve = actuation.get("F_green_to_release_vph", {})
    f_mode = str(actuation.get("F_ramp_mode", "always_green")).lower()
    d_rate = clamp(d_rate, 0.0, max((float(v) for v in d_curve.values()), default=1500.0) if isinstance(d_curve, Mapping) else 1500.0)
    d_green = green_from_release_map(d_rate, d_curve if isinstance(d_curve, Mapping) else {}, default_green=10.0)
    out["D"] = {"rate_vph": float(d_rate), "green_sec": float(clamp(round(d_green), 0.0, 10.0))}
    f_rate = clamp(f_rate, 0.0, max((float(v) for v in f_curve.values()), default=1500.0) if isinstance(f_curve, Mapping) else 1500.0)
    if f_mode in ("always_green", "monitor_only", "disabled"):
        f_green = 10.0
    else:
        f_green = green_from_release_map(f_rate, f_curve if isinstance(f_curve, Mapping) else {}, default_green=10.0)
    out["F"] = {"rate_vph": float(f_rate), "green_sec": float(clamp(round(f_green), 0.0, 10.0))}
    return out


def real_world_ramp_meter_actions(
    control,
    cfg,
    actuation: Mapping[str, Any],
    mapping: Mapping[str, Any],
) -> dict[str, dict[str, float | str]]:
    """Map model ramp releases to physical real-world ramp-meter controllers."""
    meters = mapping.get("ramp_meters", [])
    if not isinstance(meters, list) or not meters:
        return {}

    settings = _mapping(actuation.get("real_world_ramp_metering"))
    cycle = max(1.0e-6, _as_float(settings.get("cycle_sec"), 10.0))
    min_green = clamp(_as_float(settings.get("min_green_sec"), 0.0), 0.0, cycle)
    max_green = clamp(_as_float(settings.get("max_green_sec"), cycle), min_green, cycle)
    default_per_meter_capacity = max(1.0e-6, _as_float(settings.get("per_meter_capacity_vph"), 900.0))
    distribute = bool(settings.get("distribute_model_rate_across_meters", True))

    group_counts: dict[str, int] = {}
    for meter in meters:
        if not isinstance(meter, Mapping):
            continue
        key = str(meter.get("model_ramp_key", ""))
        if key:
            group_counts[key] = group_counts.get(key, 0) + 1

    capacities = getattr(cfg.network, "ramp_capacity_veh_h", {}) or {}
    out: dict[str, dict[str, float | str]] = {}
    for meter in meters:
        if not isinstance(meter, Mapping):
            continue
        meter_id = str(meter.get("id", meter.get("control_id", "")))
        if not meter_id:
            continue
        key = str(meter.get("model_ramp_key", ""))
        group_count = max(1, int(group_counts.get(key, 1)))
        per_meter_capacity = max(
            1.0e-6,
            _as_float(meter.get("capacity_vph"), default_per_meter_capacity),
        )
        default_group_capacity = per_meter_capacity * group_count
        group_capacity = max(
            1.0e-6,
            _as_float(capacities.get(key, default_group_capacity), default_group_capacity),
        )
        group_rate = clamp(
            _as_float(control.ramp_metering.get(key, group_capacity), group_capacity),
            0.0,
            group_capacity,
        )
        per_meter_rate = group_rate / float(group_count) if distribute else group_rate
        green = cycle * per_meter_rate / per_meter_capacity
        green = clamp(round(green), min_green, max_green)
        out[meter_id] = {
            "sc_no": float(_as_float(meter.get("sc_no"), 0.0)),
            "sg_no": float(_as_float(meter.get("sg_no"), 1.0)),
            "rate_vph": float(per_meter_rate),
            "group_rate_vph": float(group_rate),
            "green_sec": float(green),
            "model_ramp_key": key,
        }
    return out


def _segment_model_coordinates(segment_id: str, segment: Mapping[str, Any]) -> tuple[str, int]:
    model_link = segment.get("model_link")
    model_idx = segment.get("model_segment_index")
    if model_link is not None and model_idx is not None:
        return str(model_link), int(_as_float(model_idx))
    return SEGMENT_TO_MODEL[segment_id]


def _segment_dsd_controls(segment: Mapping[str, Any]) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    by_lane = segment.get("dsd_by_lane", {})
    if isinstance(by_lane, Mapping):
        for lane_key, value in by_lane.items():
            if not isinstance(value, Mapping):
                continue
            row = dict(value)
            row.setdefault("lane", lane_key)
            controls.append(row)
    extras = segment.get("extra_dsd_controls", [])
    if isinstance(extras, list):
        for value in extras:
            if isinstance(value, Mapping):
                controls.append(dict(value))

    def sort_key(item: Mapping[str, Any]) -> tuple[int, int]:
        lane = int(_as_float(item.get("lane"), 9999.0))
        dsd_no = int(_as_float(item.get("dsd_no"), 0.0))
        return lane, dsd_no

    return sorted(controls, key=sort_key)


def _signal_rows_for_mapping(mapping: Mapping[str, Any]) -> list[dict[str, Any]]:
    if "signals" not in mapping:
        return [{"id": signal, "sc_no": sc_no} for signal, sc_no in {"A": 1, "B": 2, "C": 3, "D": 4, "F": 5}.items()]
    raw = mapping.get("signals", [])
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, Mapping):
            # major_maps_to — 이 컨트롤러의 VISSIM MAJOR(SG1) 접근이 모델의 어느 phase 인가.
            # 일반 간선 교차로는 MAJOR 가 EW 간선이고 모델도 그것을 p2 로 서비스한다.
            # freeway 인터페이스 교차로는 MAJOR 가 off-ramp 유출이고, 모델은 램프 leg 를
            # NS 축으로 보아 p1 에 둔다(NumSim grid_topology._token_leg_dir: off*/on* -> "S").
            # 이 값이 없으면 간선 규약(p2)으로 본다 - 기존 동작과 같다.
            maps_to = str(item.get("major_maps_to", "p2")).strip().lower()
            if maps_to not in ("p1", "p2"):
                maps_to = "p2"
            rows.append({
                "id": str(item.get("id", "")),
                "sc_no": int(_as_float(item.get("sc_no"), 0.0)),
                "major_maps_to": maps_to,
            })
    return [row for row in rows if row["id"] and row["sc_no"] > 0]


def _release_at_largest_green(curve: Any, fallback: float) -> float:
    if not isinstance(curve, Mapping) or not curve:
        return float(fallback)
    points: list[tuple[float, float]] = []
    for green, release in curve.items():
        try:
            points.append((float(green), float(release)))
        except (TypeError, ValueError):
            continue
    if not points:
        return float(fallback)
    green, release = max(points, key=lambda item: item[0])
    return max(0.0, float(release))


def apply_actuation_guards_to_control(control, cfg, actuation: Mapping[str, Any]) -> dict[str, float]:
    """Force action JSON/prediction to respect calibration-level actuator guards."""
    metadata: dict[str, float] = {}
    active_mask = _mapping(actuation.get("active_lever_mask"))
    active_mask_enabled = bool(active_mask.get("enabled", False))
    vsl_segment_override_policy = str(actuation.get("vsl_segment_override_policy", "")).strip().lower()
    if vsl_segment_override_policy in {"clear_all", "clear_when_mask_disabled"}:
        if vsl_segment_override_policy == "clear_all" or not active_mask_enabled:
            stale_vsl_segments = [key for key in list(getattr(control, "vsl", {}).keys()) if "__seg" in str(key)]
            for key in stale_vsl_segments:
                control.vsl.pop(key, None)
            if stale_vsl_segments:
                control.diagnostics["vsl_segment_overrides_cleared"] = float(len(stale_vsl_segments))
                metadata["vsl_segment_overrides_cleared"] = float(len(stale_vsl_segments))
    if active_mask_enabled:
        allowed_vsl_links = {str(value) for value in active_mask.get("allowed_vsl_links", []) or []}
        allowed_vsl_segments = {str(value) for value in active_mask.get("allowed_vsl_segments", []) or []}
        max_vsl = max(float(value) for value in cfg.freeway_follower.vsl_set)
        disabled_vsl_segments = 0
        for link in cfg.network.freeway_links:
            link_key = str(link)
            for idx in range(int(cfg.network.freeway_segments_per_link)):
                segment_key = f"{link_key}__seg{idx}"
                readable_key = f"RW_{link_key}_S{idx}"
                if link_key in allowed_vsl_links or segment_key in allowed_vsl_segments or readable_key in allowed_vsl_segments:
                    continue
                control.vsl[segment_key] = float(max_vsl)
                disabled_vsl_segments += 1
        allowed_ramps = {str(value) for value in active_mask.get("allowed_ramps", []) or []}
        if "allowed_ramps" in active_mask:
            for ramp, capacity in _ramp_capacities(cfg).items():
                if ramp not in allowed_ramps:
                    control.ramp_metering[ramp] = float(capacity)
        control.diagnostics["active_lever_mask_enabled"] = 1.0
        control.diagnostics["active_lever_mask_disabled_vsl_segments"] = float(disabled_vsl_segments)
        control.diagnostics["active_lever_mask_allowed_ramp_count"] = float(len(allowed_ramps))
        metadata.update({
            "active_lever_mask_enabled": 1.0,
            "active_lever_mask_disabled_vsl_segments": float(disabled_vsl_segments),
            "active_lever_mask_allowed_ramp_count": float(len(allowed_ramps)),
        })
    signal_freeze = _mapping(actuation.get("signal_green_freeze"))
    if bool(signal_freeze.get("enabled", False)):
        green = _as_float(signal_freeze.get("green_sec"), 57.0)
        major = _as_float(signal_freeze.get("major_green_sec"), green)
        minor = _as_float(signal_freeze.get("minor_green_sec"), green)
        offset = _as_float(signal_freeze.get("offset_sec"), 0.0)
        signals = signal_freeze.get("signals")
        if not isinstance(signals, list) or not signals:
            signals = _controlled_signal_names(cfg)
        for signal in signals:
            name = str(signal)
            control.green_times[f"{name}_p1"] = float(minor)
            control.green_times[f"{name}_p2"] = float(major)
            control.offsets[name] = float(offset)
        control.diagnostics["signal_green_freeze_active"] = 1.0
        control.diagnostics["signal_green_freeze_major_sec"] = float(major)
        control.diagnostics["signal_green_freeze_minor_sec"] = float(minor)
        control.diagnostics["signal_green_freeze_offset_sec"] = float(offset)
        metadata.update({
            "signal_green_freeze_active": 1.0,
            "signal_green_freeze_major_sec": float(major),
            "signal_green_freeze_minor_sec": float(minor),
            "signal_green_freeze_offset_sec": float(offset),
        })
    if bool(actuation.get("F_ramp_invalid_guard_active", False)):
        cap = cfg.network.ramp_capacity_veh_h
        fallback = (
            float(cap.get("R_F_W", 0.0))
            + float(cap.get("R_F_E", 0.0))
        ) / 2.0
        release = _release_at_largest_green(actuation.get("F_green_to_release_vph", {}), fallback)
        for ramp in ("R_F_W", "R_F_E"):
            control.ramp_metering[ramp] = float(release)
        control.diagnostics["F_ramp_invalid_guard_active"] = 1.0
        control.diagnostics["F_ramp_guard_release_vph"] = float(release)
        metadata.update({
            "F_ramp_invalid_guard_active": 1.0,
            "F_ramp_guard_release_vph": float(release),
        })
    return metadata


def _total_ramp_queue_veh(state) -> float:
    ramp_queue = getattr(state, "ramp_queue", {})
    if not isinstance(ramp_queue, Mapping):
        return 0.0
    return float(sum(max(0.0, _as_float(value)) for value in ramp_queue.values()))


def _boundary_in_queue_veh(state, cfg) -> float:
    try:
        return float(state.boundary_in_queue_vehicles(cfg.network))
    except Exception:
        return 0.0


def _max_freeway_density_ratio(state, cfg) -> float:
    rho_crit = max(1.0e-9, float(getattr(cfg.network, "rho_crit", 1.0)))
    values: list[float] = []
    freeway_density = getattr(state, "freeway_density", {})
    if isinstance(freeway_density, Mapping):
        for densities in freeway_density.values():
            if isinstance(densities, list):
                values.extend(max(0.0, _as_float(value)) / rho_crit for value in densities)
    return float(max(values)) if values else 0.0


def _ramp_capacities(cfg) -> dict[str, float]:
    raw = getattr(cfg.network, "ramp_capacity_veh_h", {})
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): max(0.0, _as_float(value)) for key, value in raw.items()}


def _release_sum(control, capacities: Mapping[str, float]) -> float:
    return float(sum(
        max(0.0, _as_float(control.ramp_metering.get(ramp, capacities.get(ramp, 0.0))))
        for ramp in capacities
    ))


def _release_floor_ratio(
    guard: Mapping[str, Any],
    ramp_queue_veh: float,
    boundary_queue_veh: float,
    stopped_veh: float,
) -> float:
    ratio = clamp(_as_float(guard.get("min_release_ratio_of_capacity"), 0.0), 0.0, 1.0)
    high_ratio = clamp(
        _as_float(guard.get("queue_high_release_ratio_of_capacity"), ratio),
        0.0,
        1.0,
    )
    if ramp_queue_veh >= _as_float(guard.get("ramp_queue_threshold_veh"), float("inf")):
        ratio = max(ratio, high_ratio)
    if boundary_queue_veh >= _as_float(guard.get("boundary_queue_threshold_veh"), float("inf")):
        ratio = max(ratio, high_ratio)
    if stopped_veh >= _as_float(guard.get("stopped_threshold_veh"), float("inf")):
        ratio = max(ratio, high_ratio)
    return float(ratio)


def _make_no_control(ControlAction, cfg):
    if hasattr(ControlAction, "uncontrolled"):
        return ControlAction.uncontrolled(cfg)
    return ControlAction.fixed(cfg)


def apply_vissim_policy_guards(
    control,
    cfg,
    state,
    state_json: Mapping[str, Any],
    actuation: Mapping[str, Any],
    ControlAction,
) -> tuple[Any, dict[str, float]]:
    """Plant-aware action guards applied before bridge-level actuator guards.

    These guards are intentionally conservative. They do not try to improve the
    Stackelberg objective; they prevent Vissim-facing ramp actions from hiding
    too much queue in ramp/boundary storage when the predicted benefit is small.
    """
    if bool(_mapping(getattr(control, "diagnostics", {})).get("diagnostic_bypass_policy_guards", False)):
        return control, {"ramp_release_guard_bypassed_for_diagnostic": 1.0}

    guard = _mapping(actuation.get("ramp_release_guard"))
    if not bool(guard.get("enabled", False)):
        return control, {}

    capacities = _ramp_capacities(cfg)
    if not capacities:
        return control, {}

    ramp_queue_veh = _total_ramp_queue_veh(state)
    boundary_queue_veh = _boundary_in_queue_veh(state, cfg)
    stopped_veh = max(0.0, _as_float(state_json.get("stopped_vehicles")))
    density_ratio = _max_freeway_density_ratio(state, cfg)
    floor_ratio = _release_floor_ratio(guard, ramp_queue_veh, boundary_queue_veh, stopped_veh)
    before_sum = _release_sum(control, capacities)
    cap_sum = float(sum(capacities.values()))
    no_control_sum = cap_sum
    mean_ratio_before = before_sum / max(no_control_sum, 1.0e-9)

    fallback = _mapping(guard.get("no_control_fallback"))
    fallback_enabled = bool(fallback.get("enabled", False))
    fallback_release_ratio = clamp(
        _as_float(
            fallback.get("min_release_ratio_of_uncontrolled"),
            guard.get("fallback_min_release_ratio_of_uncontrolled", 0.0),
        ),
        0.0,
        1.0,
    )
    density_limit = _as_float(
        fallback.get("max_density_ratio_for_fallback"),
        guard.get("max_density_ratio_for_fallback", float("inf")),
    )
    queue_required = bool(fallback.get("require_queue_or_stopped", False))
    has_queue_risk = (
        ramp_queue_veh >= _as_float(guard.get("ramp_queue_threshold_veh"), float("inf"))
        or boundary_queue_veh >= _as_float(guard.get("boundary_queue_threshold_veh"), float("inf"))
        or stopped_veh >= _as_float(guard.get("stopped_threshold_veh"), float("inf"))
    )
    should_fallback = (
        fallback_enabled
        and mean_ratio_before < fallback_release_ratio
        and density_ratio <= density_limit
        and (has_queue_risk or not queue_required)
    )

    metadata: dict[str, float] = {
        "ramp_release_guard_active": 1.0,
        "ramp_release_guard_floor_ratio": float(floor_ratio),
        "ramp_release_guard_before_sum_vph": float(before_sum),
        "ramp_release_guard_before_ratio": float(mean_ratio_before),
        "ramp_release_guard_ramp_queue_veh": float(ramp_queue_veh),
        "ramp_release_guard_boundary_queue_veh": float(boundary_queue_veh),
        "ramp_release_guard_stopped_veh": float(stopped_veh),
        "ramp_release_guard_density_ratio_max": float(density_ratio),
        "ramp_release_guard_no_control_fallback": float(should_fallback),
    }

    if should_fallback:
        control = _make_no_control(ControlAction, cfg)
        control.diagnostics["ramp_release_guard_no_control_fallback"] = 1.0
        control.diagnostics["ramp_release_guard_before_ratio"] = float(mean_ratio_before)
    else:
        adjusted = 0
        ramp_overrides = _mapping(guard.get("per_ramp_min_release_ratio_of_capacity"))
        for ramp, capacity in capacities.items():
            ratio = clamp(_as_float(ramp_overrides.get(ramp), floor_ratio), 0.0, 1.0)
            floor = float(capacity) * ratio
            current = max(0.0, _as_float(control.ramp_metering.get(ramp), capacity))
            if current < floor:
                control.ramp_metering[ramp] = float(floor)
                adjusted += 1
        control.diagnostics["ramp_release_guard_adjusted_count"] = float(adjusted)
        control.diagnostics["ramp_release_guard_floor_ratio"] = float(floor_ratio)
        metadata["ramp_release_guard_adjusted_count"] = float(adjusted)

    after_sum = _release_sum(control, capacities)
    control.N_UF_star = float(after_sum)
    control.diagnostics["ramp_release_guard_after_sum_vph"] = float(after_sum)
    control.diagnostics["ramp_release_guard_N_UF_resynced"] = 1.0
    metadata.update({
        "ramp_release_guard_after_sum_vph": float(after_sum),
        "ramp_release_guard_after_ratio": float(after_sum / max(no_control_sum, 1.0e-9)),
        "ramp_release_guard_N_UF_resynced": 1.0,
    })
    return control, metadata


def _post_guard_safety_settings(tuning: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(_mapping(tuning.get("adapter")).get("post_guard_safety"))


def _post_guard_terminal_score_settings(
    tuning: Mapping[str, Any],
    safety: Mapping[str, Any],
) -> Mapping[str, Any]:
    base = dict(_mapping(_mapping(tuning.get("adapter")).get("terminal_cost")))
    score = _mapping(safety.get("score"))
    if not score:
        score = _mapping(safety.get("terminal_cost"))
    if score:
        base = deep_update(base, score)
    if "fit_json" not in base:
        base["fit_json"] = "evaluation/calibration/vissim_terminal_cost_fit_20260715.json"
    return base


def _load_terminal_score_spec(settings: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    fit_path = _workspace_path(
        str(settings.get("fit_json", "evaluation/calibration/vissim_terminal_cost_fit_20260715.json"))
    )
    try:
        fit = json.loads(fit_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, {
            "post_guard_safety_status": "terminal_fit_load_failed",
            "post_guard_safety_error_type": type(exc).__name__,
        }

    raw_coefficients = _mapping(fit.get("raw_coefficients"))
    features = settings.get("features", fit.get("features", []))
    if not isinstance(features, list):
        features = list(raw_coefficients)
    coefficient_mode = str(settings.get("coefficient_mode", "positive_only")).lower()
    include_intercept = bool(settings.get("include_intercept", False))
    intercept = _as_float(fit.get("raw_intercept"), 0.0) if include_intercept else 0.0
    used: dict[str, float] = {}
    for feature in features:
        name = str(feature)
        coef = _as_float(raw_coefficients.get(name), 0.0)
        if coefficient_mode == "positive_only" and coef <= 0.0:
            continue
        used[name] = float(coef)
    if not used and abs(intercept) <= 1.0e-12:
        return None, {"post_guard_safety_status": "terminal_fit_empty"}

    return {
        "coefficients": used,
        "intercept": float(intercept),
        "weight": _as_float(settings.get("weight"), 1.0),
        "clamp_nonnegative": bool(settings.get("clamp_nonnegative", True)),
        "use_calibrated_prediction": bool(settings.get("use_calibrated_prediction", True)),
        "component_penalty": _mapping(settings.get("component_penalty")),
        "fit_path": str(fit_path),
        "fit_r2": _as_float(_mapping(fit.get("metrics")).get("r2"), 0.0),
    }, {
        "post_guard_terminal_score_feature_count": float(len(used)),
        "post_guard_terminal_score_fit_r2": _as_float(_mapping(fit.get("metrics")).get("r2"), 0.0),
        "post_guard_terminal_score_weight": _as_float(settings.get("weight"), 1.0),
    }


def _prediction_terminal_features(
    prediction: Mapping[str, Any],
    cfg,
    spec: Mapping[str, Any],
) -> tuple[dict[str, float], str]:
    if bool(spec.get("use_calibrated_prediction", True)):
        calibrated = _mapping(prediction.get("calibrated_state_summary"))
        if calibrated:
            return vissim_terminal_feature_vector_from_summary(calibrated, cfg), "calibrated_state_summary"
    terminal_features = _mapping(prediction.get("terminal_features"))
    if terminal_features:
        return {str(k): _as_float(v) for k, v in terminal_features.items()}, "terminal_features"
    summary = _mapping(prediction.get("state_summary"))
    return vissim_terminal_feature_vector_from_summary(summary, cfg), "state_summary"


def _prediction_component_summary(
    prediction: Mapping[str, Any],
    settings: Mapping[str, Any],
) -> tuple[Mapping[str, Any], str]:
    if bool(settings.get("use_calibrated_prediction", True)):
        calibrated = _mapping(prediction.get("calibrated_state_summary"))
        if calibrated:
            return calibrated, "calibrated_state_summary"
    summary = _mapping(prediction.get("state_summary"))
    return summary, "state_summary"


def _component_penalty_score(
    prediction: Mapping[str, Any],
    settings: Mapping[str, Any],
) -> tuple[float, str, int]:
    component = _mapping(settings.get("component_penalty"))
    if not bool(component.get("enabled", False)):
        return 0.0, "disabled", 0
    terms = component.get("terms", [])
    if not isinstance(terms, list):
        return 0.0, "empty", 0
    summary, summary_kind = _prediction_component_summary(prediction, component)
    total = 0.0
    used = 0
    for raw_term in terms:
        term = _mapping(raw_term)
        metric = str(term.get("metric", ""))
        if not metric:
            continue
        value = _as_float(summary.get(metric), 0.0)
        target = _as_float(term.get("target", term.get("threshold", 0.0)), 0.0)
        mode = str(term.get("mode", "above")).lower()
        if mode in ("above", "excess", "over"):
            amount = max(0.0, value - target)
        elif mode in ("below", "deficit", "under"):
            amount = max(0.0, target - value)
        elif mode in ("absolute", "abs"):
            amount = abs(value - target)
        elif mode in ("value", "raw"):
            amount = max(0.0, value)
        else:
            amount = 0.0
        weight = _as_float(term.get("weight"), 0.0)
        total += weight * amount
        used += 1
    return float(total), summary_kind, used


def _score_prediction_with_terminal_fit(
    prediction: Mapping[str, Any],
    cfg,
    spec: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    if str(prediction.get("status", "")) != "ok":
        return None, "prediction_unavailable"
    features, summary_kind = _prediction_terminal_features(prediction, cfg, spec)
    raw = _as_float(spec.get("intercept"), 0.0)
    for feature, coef in _mapping(spec.get("coefficients")).items():
        raw += float(coef) * float(features.get(str(feature), 0.0))
    if bool(spec.get("clamp_nonnegative", True)):
        raw = max(0.0, raw)
    component_penalty, component_summary_kind, component_term_count = _component_penalty_score(prediction, spec)
    weight = _as_float(spec.get("weight"), 1.0)
    return {
        "score": float(weight * raw + component_penalty),
        "raw_veh_h": float(raw),
        "summary_kind": summary_kind,
        "component_penalty": float(component_penalty),
        "component_summary_kind": component_summary_kind,
        "component_term_count": float(component_term_count),
    }, "ok"


def _add_score_metadata(
    metadata: dict[str, Any],
    prefix: str,
    score: Mapping[str, Any] | None,
    status: str,
) -> None:
    metadata[f"{prefix}_score_status"] = status
    if score is None:
        return
    metadata[f"{prefix}_terminal_score"] = float(score.get("score", 0.0))
    metadata[f"{prefix}_terminal_score_raw_veh_h"] = float(score.get("raw_veh_h", 0.0))
    metadata[f"{prefix}_score_summary_kind"] = str(score.get("summary_kind", ""))
    metadata[f"{prefix}_component_penalty"] = float(score.get("component_penalty", 0.0))
    metadata[f"{prefix}_component_penalty_term_count"] = float(score.get("component_term_count", 0.0))
    metadata[f"{prefix}_component_penalty_summary_kind"] = str(score.get("component_summary_kind", ""))


def _physical_action_metadata(prefix: str, control, cfg, actuation: Mapping[str, Any]) -> dict[str, float]:
    metadata: dict[str, float] = {}
    try:
        actions = physical_ramp_actions(control, cfg, actuation)
    except Exception:
        return metadata
    for ramp, spec in actions.items():
        metadata[f"{prefix}_physical_ramp_{ramp}_rate_vph"] = _as_float(spec.get("rate_vph"))
        metadata[f"{prefix}_physical_ramp_{ramp}_green_sec"] = _as_float(spec.get("green_sec"))
    return metadata


def _guarded_no_control_baseline(ControlAction, cfg, state, state_json, actuation: Mapping[str, Any]):
    control = _make_no_control(ControlAction, cfg)
    control.diagnostics["post_guard_no_control_baseline"] = 1.0
    control, _ = apply_vissim_policy_guards(control, cfg, state, state_json, actuation, ControlAction)
    apply_actuation_guards_to_control(control, cfg, actuation)
    return control


def _guarded_pfo_baseline(cfg, state, forecast, previous, state_json, actuation: Mapping[str, Any], ControlAction):
    started = time.perf_counter()
    metadata: dict[str, Any] = {}
    controller = None
    try:
        from src.controllers.distributed_coordinator import DistributedCoordinator

        controller = DistributedCoordinator(cfg)
        result = controller.solve(state.copy(), None, forecast, previous)
        control = result.control
        control.diagnostics["post_guard_pfo_baseline"] = 1.0
        metadata.update({
            "post_guard_pfo_iterations": float(getattr(result, "iterations", 0)),
            "post_guard_pfo_converged": float(bool(getattr(result, "converged", False))),
            "post_guard_pfo_objective": float(getattr(result, "objective_value", 0.0)),
        })
        control, _ = apply_vissim_policy_guards(control, cfg, state, state_json, actuation, ControlAction)
        apply_actuation_guards_to_control(control, cfg, actuation)
        metadata["post_guard_pfo_baseline_status"] = "ok"
        metadata["post_guard_pfo_wall_sec"] = round(time.perf_counter() - started, 6)
        return control, metadata
    except Exception as exc:
        metadata.update({
            "post_guard_pfo_baseline_status": "error",
            "post_guard_pfo_error_type": type(exc).__name__,
            "post_guard_pfo_wall_sec": round(time.perf_counter() - started, 6),
        })
        return None, metadata
    finally:
        if controller is not None and hasattr(controller, "close"):
            try:
                controller.close()
            except Exception:
                pass


def apply_post_guard_safety_evaluation(
    control,
    cfg,
    state,
    state_json: Mapping[str, Any],
    forecast,
    previous,
    calibration: Mapping[str, Any],
    tuning: Mapping[str, Any],
    actuation: Mapping[str, Any],
    ControlAction,
    prediction: Mapping[str, Any],
) -> tuple[Any, dict[str, Any], Mapping[str, Any]]:
    """Evaluate guarded plant-facing action against explicit safety baselines."""
    if bool(_mapping(getattr(control, "diagnostics", {})).get("diagnostic_bypass_policy_guards", False)):
        return control, {"post_guard_safety_bypassed_for_diagnostic": 1.0}, prediction

    safety = _post_guard_safety_settings(tuning)
    if not bool(safety.get("enabled", False)):
        return control, {}, prediction

    metadata: dict[str, Any] = {
        "post_guard_safety_enabled": 1.0,
        "post_guard_safety_status": "ok",
        "post_guard_safety_fallback_occurred": 0.0,
        "post_guard_no_control_fallback": 0.0,
    }
    metadata.update(_physical_action_metadata("post_guard", control, cfg, actuation))

    spec, spec_metadata = _load_terminal_score_spec(_post_guard_terminal_score_settings(tuning, safety))
    metadata.update(spec_metadata)
    if spec is None:
        return control, metadata, prediction

    post_score, post_status = _score_prediction_with_terminal_fit(prediction, cfg, spec)
    _add_score_metadata(metadata, "post_guard", post_score, post_status)
    if post_score is None:
        metadata["post_guard_safety_status"] = post_status
        return control, metadata, prediction

    no_control_settings = _mapping(safety.get("no_control_baseline"))
    if not no_control_settings:
        no_control_settings = _mapping(safety.get("no_control"))
    no_control_enabled = bool(no_control_settings.get("enabled", True))
    metadata["post_guard_no_control_baseline_enabled"] = float(no_control_enabled)
    no_control_prediction: Mapping[str, Any] | None = None
    no_control_control = None
    if no_control_enabled:
        no_control_control = _guarded_no_control_baseline(ControlAction, cfg, state, state_json, actuation)
        metadata.update(_physical_action_metadata("post_guard_no_control", no_control_control, cfg, actuation))
        no_control_prediction = build_one_step_prediction(state, no_control_control, forecast, cfg, calibration)
        no_score, no_status = _score_prediction_with_terminal_fit(no_control_prediction, cfg, spec)
        _add_score_metadata(metadata, "post_guard_no_control", no_score, no_status)
        if no_score is not None:
            gap = float(post_score["score"] - no_score["score"])
            metadata["post_guard_no_control_score_gap"] = gap
            metadata["post_guard_vs_no_control_score_gap"] = gap
            margin = max(
                0.0,
                _as_float(
                    no_control_settings.get(
                        "fallback_margin_score",
                        safety.get("no_control_fallback_margin_score", 0.0),
                    ),
                ),
            )
            metadata["post_guard_no_control_fallback_margin_score"] = float(margin)
            fallback_enabled = bool(
                no_control_settings.get(
                    "fallback_enabled",
                    safety.get("fallback_to_no_control", False),
                )
            )
            prefer_less_restrictive = bool(
                no_control_settings.get(
                    "prefer_less_restrictive_on_tie",
                    no_control_settings.get("prefer_no_control_on_tie", False),
                )
            )
            tie_margin = max(
                0.0,
                _as_float(
                    no_control_settings.get(
                        "tie_margin_score",
                        no_control_settings.get("prefer_no_control_tie_margin_score", 0.0),
                    ),
                ),
            )
            min_release_gap = max(
                0.0,
                _as_float(
                    no_control_settings.get(
                        "min_release_gap_vph",
                        no_control_settings.get("prefer_no_control_min_release_gap_vph", 0.0),
                    ),
                ),
            )
            post_physical = physical_ramp_actions(control, cfg, actuation)
            no_physical = physical_ramp_actions(no_control_control, cfg, actuation)
            release_gap = 0.0
            for ramp in sorted(set(post_physical) | set(no_physical)):
                release_gap += max(
                    0.0,
                    _as_float(_mapping(no_physical.get(ramp)).get("rate_vph"))
                    - _as_float(_mapping(post_physical.get(ramp)).get("rate_vph")),
                )
            tie_fallback = (
                prefer_less_restrictive
                and gap >= -tie_margin
                and release_gap >= min_release_gap
            )
            metadata["post_guard_no_control_prefer_less_restrictive_on_tie"] = float(prefer_less_restrictive)
            metadata["post_guard_no_control_tie_margin_score"] = float(tie_margin)
            metadata["post_guard_no_control_release_gap_vph"] = float(release_gap)
            metadata["post_guard_no_control_tie_fallback"] = float(tie_fallback)
            should_fallback = fallback_enabled and (gap > margin or tie_fallback)
            metadata["post_guard_no_control_fallback"] = float(should_fallback)
            if should_fallback and no_control_prediction is not None:
                no_control_control.diagnostics["post_guard_safety_no_control_fallback"] = 1.0
                no_control_control.diagnostics["post_guard_no_control_score_gap"] = float(gap)
                no_control_control.diagnostics["post_guard_no_control_tie_fallback"] = float(tie_fallback)
                metadata["post_guard_safety_fallback_occurred"] = 1.0
                metadata["post_guard_safety_fallback_baseline"] = "no_control"
                metadata["post_guard_safety_status"] = "fallback_no_control"
                metadata.update(_physical_action_metadata("post_guard_final", no_control_control, cfg, actuation))
                return no_control_control, metadata, no_control_prediction
    else:
        metadata["post_guard_no_control_score_status"] = "disabled"

    pfo_settings = _mapping(safety.get("pfo_baseline"))
    pfo_enabled = bool(pfo_settings.get("enabled", False))
    metadata["post_guard_pfo_baseline_enabled"] = float(pfo_enabled)
    if pfo_enabled:
        pfo_control, pfo_metadata = _guarded_pfo_baseline(
            cfg,
            state,
            forecast,
            previous,
            state_json,
            actuation,
            ControlAction,
        )
        metadata.update(pfo_metadata)
        if pfo_control is not None:
            metadata.update(_physical_action_metadata("post_guard_pfo", pfo_control, cfg, actuation))
            pfo_prediction = build_one_step_prediction(state, pfo_control, forecast, cfg, calibration)
            pfo_score, pfo_status = _score_prediction_with_terminal_fit(pfo_prediction, cfg, spec)
            _add_score_metadata(metadata, "post_guard_pfo", pfo_score, pfo_status)
            if pfo_score is not None:
                gap = float(post_score["score"] - pfo_score["score"])
                metadata["post_guard_pfo_score_gap"] = gap
                metadata["post_guard_vs_pfo_score_gap"] = gap
    metadata.update(_physical_action_metadata("post_guard_final", control, cfg, actuation))
    return control, metadata, prediction


DIAGNOSTIC_SIGNALS = ("A", "B", "C", "D", "F")


def _controlled_signal_names(cfg) -> list[str]:
    signals = getattr(getattr(cfg, "network", None), "signals", None)
    out = [str(signal) for signal in (signals or []) if str(signal)]
    return out if out else list(DIAGNOSTIC_SIGNALS)


def _diagnostic_fixed_control(
    cfg,
    ControlAction,
    *,
    vsl_kph: float = 120.0,
    d_ramp_rate_vph: float | None = None,
    f_ramp_rate_vph: float | None = None,
    major_green_sec: float = 57.0,
    minor_green_sec: float = 57.0,
    offset_sec: float = 0.0,
):
    control = ControlAction.fixed(cfg)
    cap = cfg.network.ramp_capacity_veh_h
    control.vsl = {link: float(vsl_kph) for link in cfg.network.freeway_links}
    for link in cfg.network.freeway_links:
        for i in range(int(getattr(cfg.network, "freeway_segments_per_link", 0))):
            control.vsl[f"{link}__seg{i}"] = float(vsl_kph)
    d_rate = (
        float(d_ramp_rate_vph)
        if d_ramp_rate_vph is not None
        else (float(cap.get("R_D_W", 0.0)) + float(cap.get("R_D_E", 0.0))) / 2.0
    )
    f_rate = (
        float(f_ramp_rate_vph)
        if f_ramp_rate_vph is not None
        else (float(cap.get("R_F_W", 0.0)) + float(cap.get("R_F_E", 0.0))) / 2.0
    )
    control.ramp_metering = {
        "R_D_W": float(d_rate),
        "R_D_E": float(d_rate),
        "R_F_W": float(f_rate),
        "R_F_E": float(f_rate),
    }
    for signal in _controlled_signal_names(cfg):
        control.green_times[f"{signal}_p1"] = float(minor_green_sec)
        control.green_times[f"{signal}_p2"] = float(major_green_sec)
        control.offsets[signal] = float(offset_sec)
    control.diagnostics.update({
        "diagnostic_fixed_actuation_active": 1.0,
        "diagnostic_forced_vsl_kph": float(vsl_kph),
        "diagnostic_forced_d_ramp_rate_vph": float(d_rate),
        "diagnostic_forced_f_ramp_rate_vph": float(f_rate),
        "diagnostic_forced_signal_major_green_sec": float(major_green_sec),
        "diagnostic_forced_signal_minor_green_sec": float(minor_green_sec),
        "diagnostic_forced_signal_offset_sec": float(offset_sec),
        "diagnostic_bypass_policy_guards": 1.0,
    })
    return control


def _force_all_vsl(control, cfg, vsl_kph: float) -> None:
    control.vsl = {link: float(vsl_kph) for link in cfg.network.freeway_links}
    for link in cfg.network.freeway_links:
        for i in range(int(getattr(cfg.network, "freeway_segments_per_link", 0))):
            control.vsl[f"{link}__seg{i}"] = float(vsl_kph)


def _force_open_ramps(control, cfg) -> None:
    cap = getattr(cfg.network, "ramp_capacity_veh_h", {}) or {}
    ramps = list(getattr(cfg.network, "ramps", ()) or cap.keys())
    control.ramp_metering = {
        str(ramp): float(cap.get(str(ramp), 1800.0))
        for ramp in ramps
    }


def _diagnostic_open_ramp_original_signal_control(cfg, ControlAction):
    control = ControlAction.uncontrolled(cfg)
    _force_all_vsl(control, cfg, 120.0)
    _force_open_ramps(control, cfg)
    control.diagnostics.update({
        "diagnostic_pure_lever_baseline": 1.0,
        "diagnostic_forced_vsl_kph": 120.0,
        "diagnostic_ramps_forced_open": 1.0,
        "diagnostic_signal_original_vissim": 1.0,
    })
    return control


def diagnostic_vsl60_only_control(cfg, ControlAction):
    control = _diagnostic_open_ramp_original_signal_control(cfg, ControlAction)
    _force_all_vsl(control, cfg, 60.0)
    control.diagnostics["diagnostic_vsl60_only_active"] = 1.0
    control.diagnostics["diagnostic_forced_vsl_kph"] = 60.0
    return control


def diagnostic_vsl80_only_control(cfg, ControlAction):
    control = _diagnostic_open_ramp_original_signal_control(cfg, ControlAction)
    _force_all_vsl(control, cfg, 80.0)
    control.diagnostics["diagnostic_vsl80_only_active"] = 1.0
    control.diagnostics["diagnostic_forced_vsl_kph"] = 80.0
    return control


def _diagnostic_signal_only_control(
    cfg,
    ControlAction,
    *,
    major_green_sec: float,
    minor_green_sec: float,
    offset_sec: float = 0.0,
):
    control = _diagnostic_open_ramp_original_signal_control(cfg, ControlAction)
    for signal in _controlled_signal_names(cfg):
        control.green_times[f"{signal}_p1"] = float(minor_green_sec)
        control.green_times[f"{signal}_p2"] = float(major_green_sec)
        control.offsets[signal] = float(offset_sec)
    control.diagnostics.update({
        "diagnostic_signal_only_active": 1.0,
        "diagnostic_forced_signal_major_green_sec": float(major_green_sec),
        "diagnostic_forced_signal_minor_green_sec": float(minor_green_sec),
        "diagnostic_forced_signal_offset_sec": float(offset_sec),
    })
    return control


def diagnostic_signal_major90_only_control(cfg, ControlAction):
    control = _diagnostic_signal_only_control(
        cfg,
        ControlAction,
        major_green_sec=90.0,
        minor_green_sec=5.0,
    )
    control.diagnostics["diagnostic_signal_major90_only_active"] = 1.0
    return control


def diagnostic_signal_minor90_only_control(cfg, ControlAction):
    control = _diagnostic_signal_only_control(
        cfg,
        ControlAction,
        major_green_sec=5.0,
        minor_green_sec=90.0,
    )
    control.diagnostics["diagnostic_signal_minor90_only_active"] = 1.0
    return control


def diagnostic_signal_offset60_only_control(cfg, ControlAction):
    control = _diagnostic_signal_only_control(
        cfg,
        ControlAction,
        major_green_sec=57.0,
        minor_green_sec=57.0,
        offset_sec=60.0,
    )
    control.diagnostics["diagnostic_signal_offset60_only_active"] = 1.0
    return control


def diagnostic_vsl_rm_control(cfg, ControlAction):
    """Forced actuator diagnostic: lower VSL and meter both D/F ramps together.

    This is intentionally not an optimizer policy. It verifies that the Vissim
    bridge can apply VSL and ramp-metering actuation simultaneously before we
    attribute non-movement to the controller objective/calibration.
    """
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        vsl_kph=80.0,
        d_ramp_rate_vph=min(1253.0, float(cfg.network.ramp_capacity_veh_h.get("R_D_W", 1253.0))),
        f_ramp_rate_vph=min(284.0, float(cfg.network.ramp_capacity_veh_h.get("R_F_W", 284.0))),
    )
    control.diagnostics["diagnostic_forced_vsl_rm_active"] = 1.0
    control.diagnostics["diagnostic_forced_ramp_green_target_sec"] = 4.0
    return control


def native_fixed_control(cfg, ControlAction):
    """망의 **실제 고정신호 계획**을 그대로 ControlAction 으로 낸다.

    왜. "모델이 고정신호가 더 낫다는 걸 볼 수 있는가" 를 묻기 위해서다. 답에 따라 진단이
    갈린다 — 모델도 고정신호가 낫다고 하면 리더의 **탐색**이 문제고, 모델이 제어안을 더
    낫게 채점하면 **모델**이 문제다.

    출처는 `outputs/signal_group_actuation_plan_v3.json` 의 `axis_green_sec` 다. 이미
    모델 현시(p1..p4) 단위로 정리돼 있고, .sig 에서 SG 별 union green 을 뽑은 값과
    일치한다(SC1: SG4=54->p1, SG3=21->p2, SG2=32->p3, SG1=31->p4).

    주의: 고정 계획에는 **녹색이 0 인 현시**가 있다(SC7 p3, SC16 p4, SC107 p1, SC108 p2,
    SC109 p1). 그대로 0 을 넣는다 — 컨트롤러도 그 현시에 0 을 준다(실측 확인).
    VSL·metering 은 무제어와 같은 자유 방출로 둬 신호만 비교되게 한다.
    """
    control = ControlAction.uncontrolled(cfg)
    src = WORKSPACE_ROOT / "outputs/signal_group_actuation_plan_v3.json"
    doc = json.loads(src.read_text(encoding="utf-8"))
    plan = {str(v.get("node_id")): v for v in (doc.get("controllers") or {}).values()}
    applied = 0
    for signal in _controlled_signal_names(cfg):
        entry = plan.get(str(signal))
        if entry is None:
            continue
        greens = _mapping(entry.get("axis_green_sec"))
        for pid in ("p1", "p2", "p3", "p4"):
            key = f"{signal}_{pid}"
            if key in control.green_times or greens.get(pid) is not None:
                control.green_times[key] = max(0.0, _as_float(greens.get(pid), 0.0))
        control.offsets[signal] = 0.0
        applied += 1
    control.diagnostics.update({
        "native_fixed_actuation_active": 1.0,
        "native_fixed_signals_applied": float(applied),
    })
    return control


def diagnostic_fixed57_control(cfg, ControlAction):
    return _diagnostic_fixed_control(cfg, ControlAction)


def diagnostic_ramp_hold_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        d_ramp_rate_vph=691.0,
    )
    control.diagnostics["diagnostic_ramp_hold_active"] = 1.0
    control.diagnostics["diagnostic_ramp_hold_target_green_sec"] = 2.0
    return control


def diagnostic_ramp_d1364_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        d_ramp_rate_vph=1364.0,
    )
    control.diagnostics["diagnostic_ramp_d1364_active"] = 1.0
    control.diagnostics["diagnostic_ramp_d1364_target_green_sec"] = 6.0
    return control


def diagnostic_ramp_d1253_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        d_ramp_rate_vph=1253.0,
    )
    control.diagnostics["diagnostic_ramp_d1253_active"] = 1.0
    control.diagnostics["diagnostic_ramp_d1253_target_green_sec"] = 4.0
    return control


def diagnostic_vsl80_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction, vsl_kph=80.0)
    control.diagnostics["diagnostic_vsl80_active"] = 1.0
    return control


# VSL 90/70/60/50 — 실측 속도 분포에 맞춘 선택지. 기존 [80,100,120] 은 상단이 무의미했다
# (속도>120 표본 1.23%, 혼잡 구간 앵커 평균속도 75.3 km/h). 혼잡 하단(v최저 19.0)을 덮으려면
# 50~70 이 필요하고, 그 결과 c01_vsl110 과 c02_vsl100 이 관측상 구분되지 않던 문제도 사라진다.
# 램프 미터링 후보 — 네 그룹(R_D_E/R_D_W/R_F_E/R_F_W)을 **전부** 설정한다.
#
# 기존 diagnostic-ramp-d1364/d1253/hold 는 d_ramp_rate_vph 만 지정해 R_D_W 그룹(물리 미터
# RM_C10480, RM_C10482) 에만 걸렸고(액션 CSV 488 행 중 64 행), 그 미터율마저 실제 램프 수요보다
# 높아 구속하지 않았다. 그래서 관측 목적함수가 후보를 구분하지 못했다.
#
# 2026-08-04 실측 램프 수요(mixed_critical, t>=2700):
#   10646=816  10681=741  10480=668  10490=619  10644=560  10482=492  10639=354  10484=307 veh/h
# 그룹 미터율은 물리 미터 2 개에 절반씩 갈리므로(그룹 1364 -> 미터당 682) 아래 값은
# 미터당 500 / 400 / 300 이 된다. 실무 램프 미터링의 통상 범위 안이다.
#
# 그리고 합류부 검정에서 8 곳 중 4 곳이 이미 용량 초과다(FW_W S2 107 %, S4 102 %, FW_E S3 100 %).
# 붕괴 위험이 실재하므로 이 미터율은 조작이 아니라 정상화다.
def diagnostic_ramp_all500_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction,
                                        d_ramp_rate_vph=1000.0, f_ramp_rate_vph=1000.0)
    control.diagnostics["diagnostic_ramp_all500_active"] = 1.0
    return control


def diagnostic_ramp_all400_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction,
                                        d_ramp_rate_vph=800.0, f_ramp_rate_vph=800.0)
    control.diagnostics["diagnostic_ramp_all400_active"] = 1.0
    return control


def diagnostic_ramp_all300_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction,
                                        d_ramp_rate_vph=600.0, f_ramp_rate_vph=600.0)
    control.diagnostics["diagnostic_ramp_all300_active"] = 1.0
    return control


def diagnostic_vsl90_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction, vsl_kph=90.0)
    control.diagnostics["diagnostic_vsl90_active"] = 1.0
    return control


def diagnostic_vsl70_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction, vsl_kph=70.0)
    control.diagnostics["diagnostic_vsl70_active"] = 1.0
    return control


def diagnostic_vsl60_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction, vsl_kph=60.0)
    control.diagnostics["diagnostic_vsl60_active"] = 1.0
    return control


def diagnostic_vsl50_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction, vsl_kph=50.0)
    control.diagnostics["diagnostic_vsl50_active"] = 1.0
    return control


def diagnostic_vsl80_original_signal_control(cfg, ControlAction):
    control = diagnostic_vsl80_control(cfg, ControlAction)
    control.diagnostics["diagnostic_original_signal_active"] = 1.0
    return control


def diagnostic_ramp_all735_original_signal_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        d_ramp_rate_vph=735.0,
        f_ramp_rate_vph=735.0,
    )
    control.diagnostics["diagnostic_ramp_all735_original_signal_active"] = 1.0
    return control


def diagnostic_ramp_all360_original_signal_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        d_ramp_rate_vph=360.0,
        f_ramp_rate_vph=360.0,
    )
    control.diagnostics["diagnostic_ramp_all360_original_signal_active"] = 1.0
    return control


def diagnostic_vsl110_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction, vsl_kph=110.0)
    control.diagnostics["diagnostic_vsl110_active"] = 1.0
    return control


def diagnostic_vsl100_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(cfg, ControlAction, vsl_kph=100.0)
    control.diagnostics["diagnostic_vsl100_active"] = 1.0
    return control


def diagnostic_signal_major_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        major_green_sec=75.0,
        minor_green_sec=25.0,
    )
    control.diagnostics["diagnostic_signal_major_active"] = 1.0
    return control


def diagnostic_signal_minor_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        major_green_sec=25.0,
        minor_green_sec=75.0,
    )
    control.diagnostics["diagnostic_signal_minor_active"] = 1.0
    return control


def diagnostic_signal_major62_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        major_green_sec=62.0,
        minor_green_sec=52.0,
    )
    control.diagnostics["diagnostic_signal_major62_active"] = 1.0
    return control


def diagnostic_signal_minor62_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        major_green_sec=52.0,
        minor_green_sec=62.0,
    )
    control.diagnostics["diagnostic_signal_minor62_active"] = 1.0
    return control


def diagnostic_signal_offset30_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        major_green_sec=57.0,
        minor_green_sec=57.0,
        offset_sec=30.0,
    )
    control.diagnostics["diagnostic_signal_offset30_active"] = 1.0
    return control


def diagnostic_combined_strong_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        vsl_kph=80.0,
        d_ramp_rate_vph=691.0,
        major_green_sec=75.0,
        minor_green_sec=25.0,
    )
    control.diagnostics["diagnostic_combined_strong_active"] = 1.0
    return control


def diagnostic_combined_extreme_control(cfg, ControlAction):
    control = _diagnostic_fixed_control(
        cfg,
        ControlAction,
        vsl_kph=60.0,
        d_ramp_rate_vph=360.0,
        f_ramp_rate_vph=360.0,
        major_green_sec=90.0,
        minor_green_sec=5.0,
    )
    control.diagnostics["diagnostic_combined_extreme_active"] = 1.0
    return control


def _action_csv_metadata(
    metadata: Mapping[str, Any],
    row_metadata: Mapping[str, Any] | None = None,
) -> str:
    status = str(metadata.get("controller_status", ""))
    provenance = metadata.get("physical_projection_provenance")
    if not isinstance(provenance, Mapping):
        if not row_metadata:
            return status
        suffix = ";".join(f"{key}={value}" for key, value in row_metadata.items())
        return f"{status};{suffix}"
    payload: dict[str, Any] = {
        "controller_status": status,
        "physical_projection_provenance": thaw_json(provenance),
    }
    if row_metadata:
        payload["action_row"] = thaw_json(row_metadata)
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def write_action_csv(
    path: Path,
    control,
    cfg,
    mapping: dict[str, Any],
    segment_vsl_func,
    metadata: dict[str, Any],
    actuation: Mapping[str, Any],
    signal_group_plan_table: Mapping[str, Any] | None = None,
    offset_writer: str = offset_promotion.WRITER_INTENT_ONLY,
) -> None:
    # N4-7. `offset_writer` 의 기본값이 intent_only 인 것이 fail-closed 의 요점이다.
    # 이 함수를 아무 말 없이 부르면 offset 은 절대 플랜트로 나가지 않는다.
    path.parent.mkdir(parents=True, exist_ok=True)
    vsl_set = [float(v) for v in cfg.freeway_follower.vsl_set]
    if 120.0 not in vsl_set:
        # Allow no-control-ish 120 km/h on Vissim when previous/control provides it.
        vsl_set = sorted(set(vsl_set + [120.0]))
    # Action CSV fields are ASCII-compatible. Omitting a BOM lets the VBS
    # consumer validate the complete header token-for-token.
    with path.open("w", newline="", encoding="utf-8") as f:
        csv_metadata = _action_csv_metadata(metadata)
        # 열 목록은 `action_csv_schema` 가 정본이다. 여기에 리터럴로 두면 러너 헤더와
        # 조용히 갈라진다(러너는 헤더를 토큰 단위로 대조해 전량 거부한다).
        fields = list(action_csv_schema.ACTION_CSV_FIELDS)
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for seg in mapping["segments"]:
            segment_id = seg["segment_id"]
            model_link, idx = _segment_model_coordinates(str(segment_id), seg)
            value = nearest(segment_vsl_func(control, model_link, idx, cfg), vsl_set)
            for dsd in _segment_dsd_controls(seg):
                lane = dsd.get("lane", "")
                writer.writerow({
                    "kind": "vsl",
                    "id": segment_id,
                    "dsd_no": dsd["dsd_no"],
                    "link": seg["link"],
                    "lane": lane,
                    "speed_kph": value,
                    "metadata": csv_metadata,
                })
        signal_settings = _mapping(actuation.get("real_world_signal_control"))
        write_signal_rows = bool(signal_settings.get("enabled", True))
        if str(metadata.get("controller_variant", "")) == "no-control" and not bool(
            signal_settings.get("apply_to_no_control", False)
        ):
            write_signal_rows = False
        if bool(metadata.get("suppress_signal_rows", False)):
            write_signal_rows = False
        if write_signal_rows:
            offset_promotion.guard_forced_arm(control, offset_writer)
            for signal_row in _signal_rows_for_mapping(mapping):
                signal = str(signal_row["id"])
                sc_no = int(signal_row["sc_no"])
                # Phase-axis fix (2026-06-30): VISSIM SG1(MAJOR) controls the E-W/arterial approaches,
                # which the model serves in phase p2; SG2(MINOR) controls the N-S/cross approaches = model
                # phase p1. Verified against evaluation/signal_install/signal_manifest.csv (20/20 approach
                # links). The previous mapping (major<-p1, minor<-p2) axis-swapped every signal's green
                # allocation in VISSIM, so the controller's green was applied to the wrong axis.
                # 진단(fixed-action) 컨트롤러는 모델 신호명(cfg.network.signals)으로 green_times 를
                # 채우는데, 매핑의 signal id 는 별개 이름공간이다. 기본 control_mapping.json 은
                # id 가 "D" 라 모델 신호명과 우연히 일치했지만 distributed 매핑은 "SC1"/"SC5"/... 라
                # 전부 기본값으로 떨어져 **앵커와 green 후보의 액션이 완전히 같아졌다**
                # (2026-08-04 실측: 바뀐 셀 0 개, 관측 응답 0.000 km/h).
                # 강제값이 diagnostics 에 있으면 그것을 기본값으로 쓴다.
                _dg = getattr(control, "diagnostics", {}) or {}
                _maj_default = float(_dg.get("diagnostic_forced_signal_major_green_sec", 40.0))
                _min_default = float(_dg.get("diagnostic_forced_signal_minor_green_sec", 40.0))
                # 컨트롤러별 축 대응 (2026-08-04). VISSIM MAJOR(SG1) 가 모델의 어느 phase 인지는
                # 교차로마다 다르다. 일반 간선 교차로는 MAJOR=EW 간선=모델 p2 이지만,
                # freeway 인터페이스 교차로(SC 1001)는 MAJOR 접근이 **off-ramp 유출**이고
                # 모델은 램프 leg 를 NS 축으로 보아 p1 에 둔다.
                #   확인 근거 - SC1001 정지선 신호두는 link 32 위이고, link 32 유입 커넥터는
                #   conn 10481(본선 2에서) / conn 10491(본선 26에서) **뿐**이다.
                #   NumSim grid_topology._token_leg_dir 은 off*/on* 토큰을 "S" 로 보아 p1 에 배정한다.
                # 이전에는 major<-p2 로 일괄 매핑해 인터페이스 교차로에서 부호가 뒤집혔고,
                # G6 에서 major green 증가를 모델은 J 악화(+2084), 플랜트는 개선(-263)으로 냈다.
                #
                # N4-0 이후 이 축 대응은 **여기서 값을 고르는 데 쓰이지 않는다.** 열이 현시
                # 이름이라 어느 열에 무엇이 실리는지가 축 대응과 무관해졌고, 창 배치 순서만
                # 계획 산출물의 `major_maps_to`(같은 매핑 JSON 에서 나온 값)가 정한다.
                # 즉 매핑과 계획이 어긋나도 값이 뒤바뀌는 경로는 사라졌다.
                # 기본값은 **라벨이 아니라 phase 를 따라가야 한다.**
                # _diagnostic_fixed_control 은 모델 신호명 기준으로 p1<-minor, p2<-major 를 넣는데
                # 그 키는 매핑 signal id 와 이름공간이 달라 조회가 항상 빗나간다. 그래서 기본값이
                # 실제로 쓰이는데, 여기서 major<-강제major 로 두면 축을 바꿔도 결과가 같아진다.
                # phase 별 기본값을 모델이 그 phase 에 넣었을 값과 맞춰야 인터페이스 교차로에서
                # freeway 접속 이동류가 모델·플랜트 양쪽에서 같은 녹색을 받는다.
                # N4-0 4현시. 축(major/minor)은 더 이상 CSV 열이 아니다. 축 대응은
                # 여기서 **기본값을 고를 때만** 살아 있고, 실려 나가는 것은 현시 이름이다.
                # 남는 현시(p3/p4)의 기본값이 0.0 인 것은 조용한 폴백이 아니다 - 계획이
                # 그 현시에 SG 를 붙여 두었으면 `signal_group_action_rows` 가 현시 집합
                # 불일치로 죽는다(부분 적용 없음).
                _phase_default = {"p1": _min_default, "p2": _maj_default}
                # 클램프는 plant_cycle 이 단일 출처다. 여기 리터럴로 두면 모델 주기와
                # 플랜트 주기가 같은지 재는 쪽(tests/test_model_plant_cycle_identity)이
                # 실제로 실리는 값이 아니라 사본을 재게 된다.
                phase_green: dict[str, float] = {}
                for _phase in signal_group_plan.MODEL_PHASES:
                    _raw = control.green_times.get(
                        f"{signal}_{_phase}", _phase_default.get(_phase, 0.0)
                    )
                    _value = float(_raw)
                    # 녹색 0 = 그 현시를 쓰지 않는다는 뜻이라 클램프 하한을 물리면 안 된다.
                    phase_green[_phase] = (
                        plant_cycle.written_axis_green_sec(_value) if _value > 0.0 else 0.0
                    )
                # N4-7 offset 승격 잠금. 최적화기가 고른 offset(control.offsets)은
                # 삼중 잠금이 열리기 전에는 이 열에 실리지 않는다. 의도는 버려지지 않고
                # action JSON 의 `offsets` 에 그대로 남는다 - 그것이 intent_only 다.
                offset = offset_promotion.written_offset_sec(signal, control, offset_writer)
                signal_row_out = {
                    "kind": "signal",
                    "id": signal,
                    "sc_no": sc_no,
                    "offset": round(offset, 3),
                    "metadata": csv_metadata,
                }
                for _phase, _field in zip(
                    signal_group_plan.MODEL_PHASES, action_csv_schema.PHASE_GREEN_FIELDS
                ):
                    signal_row_out[_field] = round(phase_green[_phase], 3)
                writer.writerow(signal_row_out)
                # N4-5. 현시 녹색을 SG 단위로 쪼갠 행(파생). 계획이 없으면 행도 없고,
                # 그 조합은 러너의 RW_SIGNAL_SG_PLAN_SCHEMA 게이트가 fail-closed 로 막는다.
                if signal_group_plan_table is not None:
                    for sg_row in signal_group_action_rows(
                        signal_group_plan_table,
                        sc_no=sc_no,
                        phase_greens={
                            _phase: round(phase_green[_phase], 3)
                            for _phase in signal_group_plan.MODEL_PHASES
                        },
                        offset=round(offset, 3),
                        metadata=csv_metadata,
                    ):
                        writer.writerow(sg_row)
        if isinstance(mapping.get("ramp_meters"), list) and mapping.get("ramp_meters"):
            for ramp, spec in real_world_ramp_meter_actions(control, cfg, actuation, mapping).items():
                writer.writerow({
                    "kind": "ramp_meter",
                    "id": ramp,
                    "sc_no": int(_as_float(spec.get("sc_no"), 0.0)),
                    "rate_vph": round(_as_float(spec.get("rate_vph"), 0.0), 3),
                    "green_sec": round(_as_float(spec.get("green_sec"), 10.0), 3),
                    "metadata": _action_csv_metadata(metadata, {
                        "model_ramp_key": spec.get("model_ramp_key", ""),
                        "group_rate_vph": round(
                            _as_float(spec.get("group_rate_vph"), 0.0), 3
                        ),
                    }),
                })
        else:
            ramp_to_sc = {"D": 6, "F": 7}
            for ramp, spec in physical_ramp_actions(control, cfg, actuation).items():
                writer.writerow({
                    "kind": "ramp_meter",
                    "id": ramp,
                    "sc_no": ramp_to_sc[ramp],
                    "rate_vph": round(spec["rate_vph"], 3),
                    "green_sec": round(spec["green_sec"], 3),
                    "metadata": csv_metadata,
                })


def main() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--state-json", default="")
    parser.add_argument("--previous-action-json", default="")
    parser.add_argument("--out-action-json", default="")
    parser.add_argument("--out-action-csv", default="")
    parser.add_argument("--b1a-required", action="store_true")
    parser.add_argument("--projection-only", action="store_true")
    parser.add_argument("--run-manifest", default="")
    parser.add_argument("--approved-topology", default="")
    parser.add_argument("--out-projection-sidecar", default="")
    parser.add_argument("--out-projection-reference", default="")
    parser.add_argument("--projection-reference", default="")
    parser.add_argument("--projection-reference-sha256", default="")
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--mapping-json", default=str(DEFAULT_MAPPING))
    parser.add_argument("--detector-mapping-json", default=str(DEFAULT_DETECTOR_MAPPING))
    parser.add_argument("--mode", choices=["fast-smoke", "fuller-smoke"], default="fast-smoke")
    parser.add_argument(
        "--controller",
        choices=[
            "stackelberg",
            "stackelberg-wu-metered",
            "pstack-flagship",
            "wu-link",
            "pfo",
            "wu",
            "wu-leader",
            "no-control",
            "diagnostic-vsl-rm",
            "native-fixed",
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
        ],
        default="stackelberg",
    )
    parser.add_argument("--calibration-json", default=str(DEFAULT_CALIBRATION))
    parser.add_argument("--tuning-json", default="")
    projection_preparse = _preparse_projection_roles(sys.argv[1:], parser)
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        if exc.code not in (None, 0):
            _invalidate_projection_reference_after_parser_failure(
                projection_preparse
            )
        raise

    if args.projection_only:
        sidecar_path = None
        reference_path = None
        immutable_paths: dict[str, Path] = {}
        reference_invalidatable = False
        try:
            (
                sidecar_path,
                reference_path,
                immutable_paths,
                reference_invalidatable,
            ) = _prepare_projection_output_roles(args, projection_preparse)
            required = {
                "--state-json": args.state_json,
                "--run-manifest": args.run_manifest,
                "--approved-topology": args.approved_topology,
                "--out-projection-sidecar": args.out_projection_sidecar,
                "--out-projection-reference": args.out_projection_reference,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ProjectionReferenceValidationError(
                    ["projection-only requires " + ", ".join(missing)]
                )
            state_path = _b1a_existing_path(args.state_json)
            run_manifest_path = _b1a_existing_path(args.run_manifest)
            topology_path = _b1a_existing_path(args.approved_topology)
            if sidecar_path is None or reference_path is None:
                raise ProjectionReferenceValidationError(
                    ["projection output roles were not established"]
                )
            (
                manifest_snapshot,
                manifest,
                approved_topology,
                state_snapshot,
            ) = _validate_b1a_projection_inputs(
                run_manifest_path=run_manifest_path,
                topology_path=topology_path,
                state_path=state_path,
            )
            immutable_paths.update({
                "state": state_snapshot.path,
                "run_manifest": manifest_snapshot.path,
                "approval": approved_topology.approval_snapshot.path,
                "lane_graph": approved_topology.lane_graph_snapshot.path,
                "topology": approved_topology.topology_snapshot.path,
                "adapter_source": Path(__file__).resolve(strict=True),
            })
            immutable_paths.update({
                str(role): path
                for role, path in manifest.resolved_paths.items()
            })
            validate_projection_output_paths(
                sidecar_path,
                reference_path,
                immutable_paths=immutable_paths,
            )
            _, _, records_hash = normalize_vehicle_records(
                state_snapshot.value, approved_topology.topology.tolerance_m
            )
            hash_context = {
                "topology_file_sha256": approved_topology.topology_snapshot.file_sha256,
                "topology_semantic_sha256": approved_topology.topology.semantic_sha256,
                "approving_manifest_sha256": approved_topology.approval_snapshot.file_sha256,
                "state_file_sha256": state_snapshot.file_sha256,
                "vehicle_records_semantic_sha256": records_hash,
            }
            result = project_vehicle_records(
                approved_topology.topology, state_snapshot.value, hash_context
            )
            publish_projection_outputs(
                workspace_root=WORKSPACE_ROOT,
                sidecar_path=sidecar_path,
                reference_path=reference_path,
                immutable_paths=immutable_paths,
                projection_ledger=result.ledger,
                run_manifest=manifest,
                run_manifest_snapshot=manifest_snapshot,
                state_snapshot=state_snapshot,
                approved_topology=approved_topology,
            )
            print(json.dumps({
                "status": "PASS", "projection_sidecar": str(sidecar_path),
                "projection_reference": str(reference_path),
            }, ensure_ascii=False))
            return
        except BaseException as exc:
            if reference_invalidatable and reference_path is not None:
                validate_projection_output_paths(
                    sidecar_path,
                    reference_path,
                    immutable_paths=immutable_paths,
                )
                reference_path.unlink(missing_ok=True)
            if isinstance(
                exc,
                (MemoryError, OSError, OverflowError, TypeError, ValueError),
            ):
                raise SystemExit(f"B1a projection-only failed: {exc}") from exc
            raise

    if not args.state_json or not args.out_action_json or not args.out_action_csv:
        parser.error("normal action mode requires --out-action-json and --out-action-csv")
    prevalidated_projection = None
    if args.b1a_required:
        required = {
            "--run-manifest": args.run_manifest,
            "--projection-reference": args.projection_reference,
            "--projection-reference-sha256": args.projection_reference_sha256,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            parser.error("B1a required action mode requires " + ", ".join(missing))
        if re.fullmatch(r"[0-9a-f]{64}", args.projection_reference_sha256) is None:
            parser.error("--projection-reference-sha256 must be lowercase SHA-256")
        try:
            run_manifest_path = _b1a_existing_path(args.run_manifest)
            reference_path = _b1a_existing_path(args.projection_reference)
            caller_state_path = _b1a_existing_path(args.state_json)
            manifest_snapshot = load_bounded_json_snapshot(
                run_manifest_path, max_bytes=MAX_RUN_MANIFEST_BYTES
            )
            manifest = validate_run_manifest(
                manifest_snapshot.value, workspace_root=WORKSPACE_ROOT
            )
            _validate_b1a_adapter_source(manifest)
            prevalidated_projection = validate_physical_projection_reference(
                reference_path.relative_to(WORKSPACE_ROOT).as_posix(),
                workspace_root=WORKSPACE_ROOT,
                run_manifest_path=run_manifest_path.relative_to(WORKSPACE_ROOT).as_posix(),
                expected_reference_file_sha256=args.projection_reference_sha256,
            )
            if (
                manifest_snapshot.data
                != prevalidated_projection.run_manifest_snapshot.data
                or manifest_snapshot.file_sha256
                != prevalidated_projection.run_manifest_snapshot.file_sha256
            ):
                raise ProjectionReferenceValidationError(
                    ["run manifest changed during required-mode validation"]
                )
            if caller_state_path != prevalidated_projection.state_path:
                raise ProjectionReferenceValidationError(["caller state path differs from projection reference"])
        except (MemoryError, OSError, OverflowError, TypeError, ValueError) as exc:
            raise SystemExit(f"B1a required action mode failed: {exc}") from exc

    started = time.perf_counter()
    repo_root = Path(args.repo_root)
    mapping_path = Path(args.mapping_json)
    state_path = prevalidated_projection.state_path if prevalidated_projection else Path(args.state_json)
    out_json = Path(args.out_action_json)
    out_csv = Path(args.out_action_csv)
    physical_projection_input = None
    if prevalidated_projection:
        state_json, physical_projection_input = _state_json_from_b1a_projection(
            prevalidated_projection
        )
    else:
        state_json = json.loads(state_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    calibration = load_optional_json(args.calibration_json)
    tuning = load_optional_json(args.tuning_json)
    # **검지 매핑은 tuning 이 이긴다** (2026-08-22).
    #
    # 러너는 생성 VBS 설정의 `RW_DETECTOR_MAPPING_PATH` 를 --detector-mapping-json 으로
    # 넘긴다. 그 값은 망 단위 상수라 팔마다 바뀌지 않는다. 그래서 tuning 에
    # `detector_mapping_json` 을 넣어도 조용히 무시됐다 — 매핑을 바꾼 팔 셋이 전부
    # 옛 매핑으로 돌았고, 상태 JSON 에 옛 경로가 찍혀 있는 걸 나중에야 발견했다.
    # 매핑은 관측 귀속을 정하는 실험 변수이므로 설정으로 갈아끼울 수 있어야 한다.
    _tuned_detector = str(tuning.get("detector_mapping_json", "") or "").strip()
    detector_mapping_path = _tuned_detector or args.detector_mapping_json
    if _tuned_detector and not Path(detector_mapping_path).is_absolute():
        detector_mapping_path = str(WORKSPACE_ROOT / detector_mapping_path)
    detector_mapping = load_optional_json(detector_mapping_path)
    # 미드블록 정지선 링크를 관측에서 뺀다(tuning `urban.midblock.exclude_links`).
    # 투영보다 먼저여야 한다 — traffic_state_from_vissim 이 이 매핑으로 큐를 귀속한다.
    detector_mapping, _midblock_meta = filter_midblock_links_from_detector_mapping(
        detector_mapping, tuning)
    calibration_override = tuning.get("calibration_override", {})
    if isinstance(calibration_override, Mapping):
        calibration = deep_update(dict(calibration), calibration_override)
    actuation = adapter_actuation_settings(calibration, tuning)
    control_interval = float(state_json.get("control_interval_sec", 60.0))
    sim_period = float(state_json.get("sim_period_sec", max(180.0, control_interval)))

    (
        StackelbergMPCController,
        DemandStep,
        ControlAction,
        _ExperimentConfig,
        TrafficState,
        segment_vsl_func,
    ) = repo_imports(repo_root)
    local_observation = bool(
        _link_counts_from_local_observation(state_json)
        and (detector_mapping or physical_projection_input is not None)
    )
    cfg = build_config(
        repo_root,
        control_interval,
        sim_period,
        args.mode,
        calibration,
        tuning,
        local_observation=local_observation,
        flagship=(args.controller in ("pstack-flagship", "wu-link")),
    )
    adapter_runtime_metadata = install_adapter_calibration_fingerprints(cfg, tuning)
    # 실제로 쓴 검지 매핑을 남긴다. 상태 JSON 의 `detector_mapping_json` 은 **러너가**
    # 쓰는 값이라 tuning 이 덮은 경우를 못 잡는다(2026-08-22 에 그걸로 팔 셋을 헛돌렸다).
    adapter_runtime_metadata["detector_mapping_effective"] = Path(detector_mapping_path).name
    adapter_runtime_metadata["detector_mapping_from_tuning"] = 1.0 if _tuned_detector else 0.0
    runtime_patch_metadata = install_vissim_calibration_runtime_patches(cfg, calibration)
    runtime_patch_metadata.update(install_vsl_metanet_rollout_runtime_patch(cfg, tuning))
    # 정지선 규모 저류. tuning `urban.stopline.bay_m` 이 없으면 no-op(비트 동일).
    runtime_patch_metadata.update(install_urban_stopline_storage(cfg, tuning))
    runtime_patch_metadata.update(install_movement_capacity_by_lanes(cfg, tuning))
    # 동시 현시 배율이 movement 용량 맵을 쓰므로 반드시 그 뒤다.
    runtime_patch_metadata.update(install_native_signal_structure(cfg, tuning))
    # 직전 구간 실측 방류율로 용량을 갱신한다. 가정값(차로수 x 330)을 덮는다 —
    # 동시현시 배율은 실측 통과량에 이미 반영돼 있으므로 그 뒤여야 한다.
    runtime_patch_metadata.update(install_measured_movement_capacity(
        cfg, tuning, state_json, args.previous_action_json))
    state = traffic_state_from_vissim(
        state_json, cfg, TrafficState, detector_mapping, calibration,
        physical_projection_input=physical_projection_input,
    )
    runtime_patch_metadata.update(
        install_monitor_fixed_signal_runtime_patch(cfg, state_json, detector_mapping)
    )
    if local_observation:
        install_local_observation_runtime_guards()
    forecast_horizon_steps = int(cfg.mpc.horizon_steps)
    if args.controller in ("pstack-flagship", "wu-link"):
        # 러너 L1044: 리더 value-depth rollout이 horizon 밖 수요를 소비한다 —
        # forecast 길이 = horizon_steps + max(0, leader_value_depth).
        forecast_horizon_steps += max(0, int(getattr(cfg.mpc, "leader_value_depth", 0)))
    forecast = demand_from_state(
        state_json,
        cfg,
        DemandStep,
        forecast_horizon_steps,
        calibration,
        detector_mapping,
    )
    previous_path = Path(args.previous_action_json) if args.previous_action_json else Path("__missing_previous.json")
    previous = control_from_json(previous_path, cfg, ControlAction)
    observed_summary = summarize_model_state(state, cfg)
    prediction_error = prediction_error_from_previous(previous_path, observed_summary)

    metadata: dict[str, Any] = {
        "controller": (
            "StackelbergMPCController"
            if args.controller == "stackelberg"
            else "StackelbergWuMeteredController"
            if args.controller == "stackelberg-wu-metered"
            else "F1StackelbergWuMeteredController"
            if args.controller == "pstack-flagship"
            else "DistributedCoordinator"
            if args.controller == "pfo"
            else "NoControl"
            if args.controller == "no-control"
            else "DiagnosticVslRampMetering"
            if args.controller == "diagnostic-vsl-rm"
            else "DiagnosticFixedActuation"
            if args.controller.startswith("diagnostic-")
            else "WuDistributedController"
        ),
        "controller_variant": args.controller,
        "adapter_mode": args.mode,
        "controller_status": "ok",
        "sim_sec": float(state_json.get("sim_sec", 0.0)),
        "calibration_version": str(calibration.get("calibration_version", "")),
        "tuning_name": str(tuning.get("name", "")),
        "F_ramp_mode": str(actuation.get("F_ramp_mode", "")),
        "F_ramp_invalid_guard_configured": float(bool(actuation.get("F_ramp_invalid_guard_active", False))),
        "observation_mode": "detector_local_v2_storage_split" if local_observation else "global_fallback",
        "follower_solver_mode": str(cfg.mpc.follower_solver_mode),
        "local_observation_runtime_guard": float(local_observation),
        "mpc_horizon_steps": float(cfg.mpc.horizon_steps),
        "mpc_control_horizon_steps": float(cfg.mpc.control_horizon_steps),
        "mpc_max_nash_iter": float(cfg.mpc.max_nash_iter),
        "freeway_horizon_beam_width": float(getattr(cfg.freeway_follower, "horizon_beam_width", 0.0)),
        "freeway_horizon_ramp_candidate_limit": float(
            getattr(cfg.freeway_follower, "horizon_ramp_candidate_limit", 0.0)
        ),
        "freeway_horizon_vsl_candidate_limit_per_link": float(
            getattr(cfg.freeway_follower, "horizon_vsl_candidate_limit_per_link", 0.0)
        ),
    }
    metadata["run_provenance"] = build_run_provenance(
        repo_root=repo_root,
        state_json=state_json,
        state_path=state_path,
        mapping_path=mapping_path,
        detector_mapping_path=Path(args.detector_mapping_json),
        calibration_path=Path(args.calibration_json),
        tuning_path=Path(args.tuning_json) if args.tuning_json else Path("__missing_tuning.json"),
        network_path=_network_path_from_state(state_json),
    )
    if prevalidated_projection:
        metadata["physical_projection_provenance"] = _projection_provenance(
            prevalidated_projection
        )
        metadata["projection_diagnostics"] = thaw_json(
            prevalidated_projection.sidecar["projection_diagnostics"]
        )
    if forecast:
        forecast0 = forecast[0]
        demand_payload = _mapping(state_json.get("demand"))
        forecast_profile = str(demand_payload.get("demand_profile", "")).lower()
        route_bias_forecast = _mapping(_mapping(calibration.get("prediction")).get("route_bias_forecast"))
        route_bias_enabled = bool(route_bias_forecast.get("enabled", True))
        route_bias_applied = route_bias_enabled and forecast_profile in {
            "d_ramp_bias",
            "d_ramp_heavy",
            "f_ramp_bias",
            "f_ramp_heavy",
        }
        metadata.update({
            "demand_profile_forecast_profile_aware": 1.0,
            "demand_profile": forecast_profile,
            "demand_urban_west_east_ratio": float(_as_float(demand_payload.get("urban_west_east_ratio"), 1.0)),
            "demand_profile_route_bias_forecast_applied": float(route_bias_applied),
            "route_bias_forecast_target_share": float(_as_float(route_bias_forecast.get("target_share"), 0.98)),
            "forecast_freeway_FW_E_vph": float(forecast0.freeway_mainline.get("FW_E", 0.0)),
            "forecast_freeway_FW_W_vph": float(forecast0.freeway_mainline.get("FW_W", 0.0)),
            "forecast_urban_boundary_in_total_vph": float(
                sum(
                    float(forecast0.urban_boundary.get(str(link), 0.0))
                    for link in cfg.network.boundary_in_links
                )
            ),
            "forecast_ramp_arrival_total_vph": float(
                sum(float(value) for value in forecast0.ramp_arrival.values())
            ),
            "forecast_ramp_arrival_R_D_W_vph": float(forecast0.ramp_arrival.get("R_D_W", 0.0)),
            "forecast_ramp_arrival_R_D_E_vph": float(forecast0.ramp_arrival.get("R_D_E", 0.0)),
            "forecast_ramp_arrival_R_F_W_vph": float(forecast0.ramp_arrival.get("R_F_W", 0.0)),
            "forecast_ramp_arrival_R_F_E_vph": float(forecast0.ramp_arrival.get("R_F_E", 0.0)),
        })
    storage_values = [
        max(0.0, _as_float(value))
        for value in getattr(cfg.network, "urban_link_storage_veh", {}).values()
    ]
    metadata.update({
        "network_lost_time_sec": float(getattr(cfg.network, "lost_time", 0.0)),
        "network_movement_capacity_veh_h": float(getattr(cfg.network, "movement_capacity_veh_h", 0.0)),
        "network_boundary_queue_max_veh": float(getattr(cfg.network, "boundary_queue_max_veh", 0.0)),
        "network_ramp_queue_max_veh": float(getattr(cfg.network, "ramp_queue_max_veh", 0.0)),
        "network_urban_link_storage_count": float(len(storage_values)),
        "network_urban_link_storage_min_veh": float(min(storage_values)) if storage_values else 0.0,
        "network_urban_link_storage_max_veh": float(max(storage_values)) if storage_values else 0.0,
        "network_urban_link_storage_total_veh": float(sum(storage_values)),
        "network_ramp_capacity_R_D_W_veh_h": float(cfg.network.ramp_capacity_veh_h.get("R_D_W", 0.0)),
        "network_ramp_capacity_R_D_E_veh_h": float(cfg.network.ramp_capacity_veh_h.get("R_D_E", 0.0)),
        "network_ramp_capacity_R_F_W_veh_h": float(cfg.network.ramp_capacity_veh_h.get("R_F_W", 0.0)),
        "network_ramp_capacity_R_F_E_veh_h": float(cfg.network.ramp_capacity_veh_h.get("R_F_E", 0.0)),
    })
    metadata.update(adapter_runtime_metadata)
    metadata.update(runtime_patch_metadata)
    if hasattr(state, "local_observation_summary"):
        summary = state.local_observation_summary
        projection_diagnostics = summary.get("projection_diagnostics", {})
        if isinstance(projection_diagnostics, Mapping):
            metadata["projection_diagnostics"] = dict(projection_diagnostics)
            for key, value in projection_diagnostics.items():
                if isinstance(value, (int, float, bool)):
                    metadata[f"projection_{key}"] = float(value)
        # 차로보정 arm 의 온디스크 증거. `native_phase_share_scaled_count` 가 축좁힘 arm 을
        # 관측 가능하게 만드는 것과 같은 역할이다 - 이게 없으면 A/B 의 한 축이 사후 검증
        # 불가능해진다. 켜짐이면 links_corrected 가 양수, 꺼짐이면 0 이어야 한다.
        lane_correction = summary.get("lane_delay_correction")
        if isinstance(lane_correction, Mapping):
            metadata["lane_delay_correction"] = dict(lane_correction)
            metadata["lane_delay_enabled"] = float(bool(lane_correction.get("enabled", False)))
            metadata["lane_delay_links_corrected"] = float(lane_correction.get("links_corrected", 0))
            metadata["lane_delay_mean_lanes"] = float(lane_correction.get("mean_lanes_applied", 0.0))
        summary_agents = summary.get("agents", {})
        metadata["local_observation_agent_count"] = float(len(summary_agents))
        if isinstance(summary_agents, Mapping):
            flagged_agents = [
                agent
                for agent in summary_agents.values()
                if isinstance(agent, Mapping)
                and ("control_enabled" in agent or "monitoring_only" in agent)
            ]
            if flagged_agents:
                metadata["local_observation_control_agent_count"] = float(
                    sum(1 for agent in flagged_agents if bool(agent.get("control_enabled", True)))
                )
                metadata["local_observation_monitoring_agent_count"] = float(
                    sum(1 for agent in flagged_agents if bool(agent.get("monitoring_only", False)))
                )
        metadata["local_observation_total_movement_queue"] = float(
            sum(max(0.0, _as_float(v)) for v in summary.get("urban_movement_queue", {}).values())
        )
        metadata["local_observation_total_ramp_queue"] = float(
            sum(max(0.0, _as_float(v)) for v in summary.get("ramp_queue", {}).values())
        )
        storage_occupancy = summary.get("urban_link_storage_occupancy", {})
        if isinstance(storage_occupancy, Mapping):
            metadata["local_observation_total_storage_occupancy"] = float(
                sum(max(0.0, _as_float(v)) for v in storage_occupancy.values())
            )
            off_storage_links = {str(v) for v in cfg.network.off_ramp_storage_link.values()}
            metadata["local_observation_offramp_storage_occupancy"] = float(
                sum(
                    max(0.0, _as_float(value))
                    for key, value in storage_occupancy.items()
                    if str(key) in off_storage_links
                )
            )
        split_params = summary.get("split_parameters", {})
        if isinstance(split_params, Mapping):
            metadata["local_observation_internal_storage_fraction"] = float(
                split_params.get("internal_storage_fraction", 0.0)
            )
            metadata["local_observation_offramp_storage_fraction"] = float(
                split_params.get("offramp_storage_fraction", 0.0)
            )
    if prediction_error:
        metadata["prediction_audit_available"] = float(prediction_error.get("status") == "ok")
        scalar_errors = prediction_error.get("scalar_errors", {})
        if isinstance(scalar_errors, Mapping):
            total_error = scalar_errors.get("total_model_vehicles", {})
            protected_error = scalar_errors.get("protected_accumulation_veh", {})
            freeway_error = scalar_errors.get("freeway_total_veh", {})
            if isinstance(total_error, Mapping):
                metadata["prediction_total_model_vehicles_error"] = float(total_error.get("error", 0.0))
                metadata["prediction_total_model_vehicles_abs_error"] = float(total_error.get("abs_error", 0.0))
            if isinstance(protected_error, Mapping):
                metadata["prediction_protected_accumulation_abs_error"] = float(protected_error.get("abs_error", 0.0))
            if isinstance(freeway_error, Mapping):
                metadata["prediction_freeway_total_abs_error"] = float(freeway_error.get("abs_error", 0.0))
    try:
        controller = None
        if args.controller == "no-control":
            control = ControlAction.uncontrolled(cfg)
            control.diagnostics["no_control_active"] = 1.0
        elif args.controller == "diagnostic-vsl-rm":
            control = diagnostic_vsl_rm_control(cfg, ControlAction)
            metadata["diagnostic_forced_vsl_rm_active"] = 1.0
        elif args.controller == "native-fixed":
            control = native_fixed_control(cfg, ControlAction)
            metadata["native_fixed_active"] = 1.0
        elif args.controller == "diagnostic-fixed57":
            control = diagnostic_fixed57_control(cfg, ControlAction)
            metadata["diagnostic_fixed57_active"] = 1.0
        elif args.controller == "diagnostic-ramp-hold":
            control = diagnostic_ramp_hold_control(cfg, ControlAction)
            metadata["diagnostic_ramp_hold_active"] = 1.0
        elif args.controller == "diagnostic-ramp-d1364":
            control = diagnostic_ramp_d1364_control(cfg, ControlAction)
            metadata["diagnostic_ramp_d1364_active"] = 1.0
        elif args.controller == "diagnostic-ramp-d1253":
            control = diagnostic_ramp_d1253_control(cfg, ControlAction)
            metadata["diagnostic_ramp_d1253_active"] = 1.0
        elif args.controller == "diagnostic-ramp-all500":
            control = diagnostic_ramp_all500_control(cfg, ControlAction)
            metadata["diagnostic_ramp_all500_active"] = 1.0
        elif args.controller == "diagnostic-ramp-all400":
            control = diagnostic_ramp_all400_control(cfg, ControlAction)
            metadata["diagnostic_ramp_all400_active"] = 1.0
        elif args.controller == "diagnostic-ramp-all300":
            control = diagnostic_ramp_all300_control(cfg, ControlAction)
            metadata["diagnostic_ramp_all300_active"] = 1.0
        elif args.controller == "diagnostic-vsl60-only":
            control = diagnostic_vsl60_only_control(cfg, ControlAction)
            metadata["diagnostic_vsl60_only_active"] = 1.0
            metadata["suppress_signal_rows"] = 1.0
        elif args.controller == "diagnostic-vsl80-only":
            control = diagnostic_vsl80_only_control(cfg, ControlAction)
            metadata["diagnostic_vsl80_only_active"] = 1.0
            metadata["suppress_signal_rows"] = 1.0
        elif args.controller == "diagnostic-vsl110":
            control = diagnostic_vsl110_control(cfg, ControlAction)
            metadata["diagnostic_vsl110_active"] = 1.0
        elif args.controller == "diagnostic-vsl100":
            control = diagnostic_vsl100_control(cfg, ControlAction)
            metadata["diagnostic_vsl100_active"] = 1.0
        elif args.controller == "diagnostic-vsl90":
            control = diagnostic_vsl90_control(cfg, ControlAction)
            metadata["diagnostic_vsl90_active"] = 1.0
        elif args.controller == "diagnostic-vsl80":
            control = diagnostic_vsl80_control(cfg, ControlAction)
            metadata["diagnostic_vsl80_active"] = 1.0
        elif args.controller == "diagnostic-vsl70":
            control = diagnostic_vsl70_control(cfg, ControlAction)
            metadata["diagnostic_vsl70_active"] = 1.0
        elif args.controller == "diagnostic-vsl60":
            control = diagnostic_vsl60_control(cfg, ControlAction)
            metadata["diagnostic_vsl60_active"] = 1.0
        elif args.controller == "diagnostic-vsl50":
            control = diagnostic_vsl50_control(cfg, ControlAction)
            metadata["diagnostic_vsl50_active"] = 1.0
        elif args.controller == "diagnostic-vsl80-original":
            control = diagnostic_vsl80_original_signal_control(cfg, ControlAction)
            metadata["diagnostic_vsl80_original_signal_active"] = 1.0
            metadata["suppress_signal_rows"] = 1.0
        elif args.controller == "diagnostic-ramp-all735-original":
            control = diagnostic_ramp_all735_original_signal_control(cfg, ControlAction)
            metadata["diagnostic_ramp_all735_original_signal_active"] = 1.0
            metadata["suppress_signal_rows"] = 1.0
        elif args.controller == "diagnostic-ramp-all360-original":
            control = diagnostic_ramp_all360_original_signal_control(cfg, ControlAction)
            metadata["diagnostic_ramp_all360_original_signal_active"] = 1.0
            metadata["suppress_signal_rows"] = 1.0
        elif args.controller == "diagnostic-signal-major90-only":
            control = diagnostic_signal_major90_only_control(cfg, ControlAction)
            metadata["diagnostic_signal_major90_only_active"] = 1.0
        elif args.controller == "diagnostic-signal-minor90-only":
            control = diagnostic_signal_minor90_only_control(cfg, ControlAction)
            metadata["diagnostic_signal_minor90_only_active"] = 1.0
        elif args.controller == "diagnostic-signal-offset60-only":
            control = diagnostic_signal_offset60_only_control(cfg, ControlAction)
            metadata["diagnostic_signal_offset60_only_active"] = 1.0
        elif args.controller == "diagnostic-signal-major62":
            control = diagnostic_signal_major62_control(cfg, ControlAction)
            metadata["diagnostic_signal_major62_active"] = 1.0
        elif args.controller == "diagnostic-signal-minor62":
            control = diagnostic_signal_minor62_control(cfg, ControlAction)
            metadata["diagnostic_signal_minor62_active"] = 1.0
        elif args.controller == "diagnostic-signal-major":
            control = diagnostic_signal_major_control(cfg, ControlAction)
            metadata["diagnostic_signal_major_active"] = 1.0
        elif args.controller == "diagnostic-signal-minor":
            control = diagnostic_signal_minor_control(cfg, ControlAction)
            metadata["diagnostic_signal_minor_active"] = 1.0
        elif args.controller == "diagnostic-signal-offset30":
            control = diagnostic_signal_offset30_control(cfg, ControlAction)
            metadata["diagnostic_signal_offset30_active"] = 1.0
        elif args.controller == "diagnostic-combined-strong":
            control = diagnostic_combined_strong_control(cfg, ControlAction)
            metadata["diagnostic_combined_strong_active"] = 1.0
        elif args.controller == "diagnostic-combined-extreme":
            control = diagnostic_combined_extreme_control(cfg, ControlAction)
            metadata["diagnostic_combined_extreme_active"] = 1.0
        elif args.controller in ("stackelberg", "wu-link"):
            controller = (
                build_priced_wu_link_controller(cfg, tuning)
                if args.controller == "wu-link"
                else StackelbergMPCController(cfg)
            )
            metadata.update(install_vissim_terminal_cost_objective(controller, cfg, tuning))
            metadata.update(
                install_price_worker_bootstrap(controller, state_json, detector_mapping)
            )
            if hasattr(controller, "decide_with_info"):
                result = controller.decide_with_info(state, forecast, previous, cfg)
                control = result.control
                metadata["leader_objective"] = float(getattr(result, "leader_objective", 0.0))
                metadata["nash_objective"] = float(getattr(getattr(result, "nash", None), "objective_value", 0.0))
                metadata.update({
                    f"meta_{k}": float(v)
                    for k, v in getattr(result, "metadata", {}).items()
                    if isinstance(v, (int, float, bool))
                })
            else:
                control = controller.decide(state, forecast, previous, cfg)
        elif args.controller == "stackelberg-wu-metered":
            # Same Stackelberg leader path as "stackelberg" but with the follower replaced by
            # WuFaithfulFollower (the new O(n)-local metering-PFO follower). The subclass only
            # overrides _make_follower_solver/_evaluate_candidate_set, so decide_with_info is
            # inherited and the call is identical. Note: the follower is NOT a DistributedCoordinator,
            # so leader output-closure keeps N_P_star at intent (no realized override) and the
            # local-observation runtime guard (which patches DistributedCoordinator) does not apply
            # because WuFaithfulFollower is natively local.
            from src.controllers.stackelberg_wu_metered import StackelbergWuMeteredController

            controller = StackelbergWuMeteredController(cfg)
            metadata.update(install_vissim_terminal_cost_objective(controller, cfg, tuning))
            if hasattr(controller, "decide_with_info"):
                result = controller.decide_with_info(state, forecast, previous, cfg)
                control = result.control
                metadata["leader_objective"] = float(getattr(result, "leader_objective", 0.0))
                metadata["nash_objective"] = float(getattr(getattr(result, "nash", None), "objective_value", 0.0))
                metadata["wu_metered_follower"] = 1.0
                metadata.update({
                    f"meta_{k}": float(v)
                    for k, v in getattr(result, "metadata", {}).items()
                    if isinstance(v, (int, float, bool))
                })
            else:
                control = controller.decide(state, forecast, previous, cfg)
        elif args.controller == "pstack-flagship":
            # NumSim flagship P-Stack(P-STACK-WU-FAITHFUL-ALLPRICE-JOINT) 이식 모드.
            # 구성·per-step 로직·사이드카는 run_pstack_flagship_decision 참조.
            control, controller, flagship_metadata = run_pstack_flagship_decision(
                cfg,
                state,
                forecast,
                previous,
                tuning,
                out_json.parent / FLAGSHIP_RUNTIME_FILENAME,
            )
            metadata.update(flagship_metadata)
        elif args.controller == "pfo":
            from src.controllers.distributed_coordinator import DistributedCoordinator

            controller = DistributedCoordinator(cfg)
            result = controller.solve(state.copy(), None, forecast, previous)
            control = result.control
            metadata["pfo_iterations"] = float(getattr(result, "iterations", 0))
            metadata["pfo_converged"] = float(bool(getattr(result, "converged", False)))
            metadata["pfo_objective"] = float(getattr(result, "objective_value", 0.0))
            metadata["pfo_residual_objective"] = float(getattr(result, "residual_objective", 0.0))
            metadata["pfo_residual_control"] = float(getattr(result, "residual_control", 0.0))
            metadata.update({
                f"meta_{k}": float(v)
                for k, v in getattr(result, "diagnostics", {}).items()
                if isinstance(v, (int, float, bool))
            })
        else:
            from src.controllers.wu_distributed import WuDistributedController

            controller = WuDistributedController(cfg, leader_enabled=(args.controller == "wu-leader"))
            result = controller.decide_with_info(state, forecast, previous)
            control = result.control
            metadata["wu_leader_enabled"] = float(args.controller == "wu-leader")
            metadata["wu_iterations"] = float(getattr(result, "iterations", 0))
            metadata["wu_converged"] = float(bool(getattr(result, "converged", False)))
            metadata["wu_coupling_residual"] = float(getattr(result, "coupling_residual", 0.0))
            metadata["wu_solver_evaluations"] = float(getattr(result, "solver_evaluations", 0))
            metadata["wu_computation_time_sec"] = float(getattr(result, "computation_time_sec", 0.0))
            metadata["wu_leader_candidates"] = float(getattr(result, "leader_candidates", 0))
            metadata["wu_leader_objective"] = float(getattr(result, "leader_objective", 0.0))
        if controller is not None and hasattr(controller, "close"):
            controller.close()
    except Exception as exc:  # Keep Vissim running; log and fall back safely.
        control = ControlAction.fixed(cfg)
        metadata["controller_status"] = "fallback_fixed"
        metadata["controller_error_type"] = type(exc).__name__
        metadata["controller_error"] = str(exc)

    control, policy_guard_metadata = apply_vissim_policy_guards(
        control,
        cfg,
        state,
        state_json,
        actuation,
        ControlAction,
    )
    metadata.update(policy_guard_metadata)
    metadata.update(apply_actuation_guards_to_control(control, cfg, actuation))
    prediction = build_one_step_prediction(state, control, forecast, cfg, calibration)
    post_guard_tuning: Mapping[str, Any] = tuning
    if args.controller == "pstack-flagship" and not bool(
        flagship_settings(tuning).get("post_guard_pfo_baseline", False)
    ):
        # SUP_PFO가 flagship의 정식 PFO 기권 메커니즘이므로 post_guard의 PFO 기준선
        # 평가(폴백 포함)는 기본 OFF — 이중 개입 방지. tuning
        # adapter.flagship.post_guard_pfo_baseline=true로만 재활성.
        post_guard_tuning = deep_update(
            dict(tuning),
            {"adapter": {"post_guard_safety": {"pfo_baseline": {"enabled": False}}}},
        )
        metadata["flagship_post_guard_pfo_baseline_forced_off"] = 1.0
    control, post_guard_safety_metadata, prediction = apply_post_guard_safety_evaluation(
        control,
        cfg,
        state,
        state_json,
        forecast,
        previous,
        calibration,
        post_guard_tuning,
        actuation,
        ControlAction,
        prediction,
    )
    metadata.update(post_guard_safety_metadata)
    metadata["prediction_status"] = str(prediction.get("status", ""))
    metadata["prediction_wall_sec"] = float(prediction.get("wall_sec", 0.0))
    audit_calibration = prediction.get("audit_calibration", {})
    if isinstance(audit_calibration, Mapping):
        metadata.update({
            str(key): float(value)
            for key, value in audit_calibration.items()
            if isinstance(value, (int, float, bool))
        })
    # N4-7. offset 승격 판정은 action JSON 을 쓰기 **전에** 나와야 한다. 억눌린 의도가
    # 어디로 갔는지 그 JSON 하나로 설명되어야 하기 때문이다(intent_only 의 "기록").
    offset_verdict = offset_promotion.evaluate()
    offset_writer = offset_promotion.resolve_writer(actuation, verdict=offset_verdict)
    metadata.update(offset_promotion.action_metadata(control, offset_writer, offset_verdict))
    metadata["decision_wall_sec"] = round(time.perf_counter() - started, 6)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(
            control_to_json_dict(control, metadata, prediction=prediction, prediction_error=prediction_error),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_action_csv(
        out_csv,
        control,
        cfg,
        mapping,
        segment_vsl_func,
        metadata,
        actuation,
        signal_group_plan_table=load_signal_group_actuation_plan(),
        offset_writer=offset_writer,
    )
    print(json.dumps({
        "status": metadata["controller_status"],
        "out_action_json": str(out_json),
        "out_action_csv": str(out_csv),
        "decision_wall_sec": metadata["decision_wall_sec"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
