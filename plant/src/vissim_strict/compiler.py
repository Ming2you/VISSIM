"""Canonical Phase 0 compiler for an INPX network and its VISSIG programs."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from .contraction import contract_topology
from .signal_program import (
    ControllerProgram,
    DailyProgramList,
    SignalDefinition,
    parse_sig_definition,
)
from .topology import canonical_json_sha256, canonical_json_text, compile_inpx, validate_topology


COMPILER_VERSION = "vissim-strict-phase0/1.1.1"
SIGNAL_REFERENCE_SCHEMA_VERSION = "signal-reference-v2.1"
_AUXILIARY_RAMP_SC_NOS = frozenset(str(value) for value in range(9101, 9109))
_EXPLICIT_MODEL_EXCLUSIONS = {
    "9004": "explicit_sc9004_exclusion_no_signal_head_references",
}
_DAY_MS = 86_400_000


def _resolve_supply_file(inpx_path: Path, raw: str) -> Path:
    value = raw.strip()
    if value.lower().startswith("#data#"):
        value = value[6:]
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = inpx_path.parent / candidate
    return candidate.resolve()


def _portable_source_path(source: Path, network_dir: Path) -> str:
    try:
        return source.relative_to(network_dir).as_posix()
    except ValueError:
        return source.name


def _program_dict(program: ControllerProgram, source: Path, network_dir: Path) -> dict[str, Any]:
    return {
        "controller_id": program.controller_id,
        "controller_name": program.controller_name,
        "active_prog_no": program.active_prog_no,
        "program_name": program.program_name,
        "cycle_length_ms": program.cycle_length_ms,
        "cycle_length_sec": program.cycle_length_sec,
        "switchpoint_ms": program.switchpoint_ms,
        "switchpoint_sec": program.switchpoint_sec,
        "program_offset_ms": program.program_offset_ms,
        "program_offset_sec": program.program_offset_sec,
        "display_states": dict(program.display_states),
        "sequences": {key: asdict(value) for key, value in sorted(program.sequences.items())},
        "sg_timelines": {key: asdict(value) for key, value in sorted(program.sg_timelines.items())},
        "source_path": _portable_source_path(source, network_dir),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }


def _compiler_source_hashes() -> dict[str, str]:
    paths = (Path(__file__).resolve(), Path(__file__).with_name("signal_program.py").resolve())
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths, key=lambda item: item.name)
    }


def _id_sort_key(value: str | int) -> tuple[int, int | str]:
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, str(value))


def _controller_heads(manifest: dict[str, Any], controller_no: str) -> list[dict[str, Any]]:
    heads = [
        head
        for head in manifest["signal_heads"]
        if str(head["signal_group_ref"].get("controller_no")) == controller_no
    ]
    return sorted(heads, key=lambda item: _id_sort_key(item["vissim_no"]))


def _head_evidence(head: dict[str, Any]) -> dict[str, Any]:
    lane_ref = head["lane_ref"]
    sg_ref = head["signal_group_ref"]
    return {
        "id": head["id"],
        "vissim_no": str(head["vissim_no"]),
        "name": head["name"],
        "link_no": lane_ref["link_no"],
        "lane_no": lane_ref["lane_no"],
        "lane_raw": lane_ref["raw"],
        "position_m": head["position_m"],
        "controller_no": sg_ref["controller_no"],
        "sg_no": sg_ref["sg_no"],
        "sg_raw": sg_ref["raw"],
    }


def _controller_classification(
    controller: dict[str, Any], heads: list[dict[str, Any]]
) -> tuple[str, str]:
    controller_no = str(controller["vissim_no"])
    supply_file = str(controller["supply_file_2"]).strip()
    if not supply_file and controller_no in _AUXILIARY_RAMP_SC_NOS:
        return ("auxiliary", "artificial_ramp_controller_without_supplyFile2")
    if supply_file and not heads:
        if controller_no in _EXPLICIT_MODEL_EXCLUSIONS:
            return ("model_excluded", _EXPLICIT_MODEL_EXCLUSIONS[controller_no])
        return ("invalid", "missing_signal_head_provenance")
    if supply_file and heads:
        return ("model_selected", "supplyFile2_and_signal_head_references")
    return ("invalid", "missing_supplyFile2_outside_auxiliary_ramp_set")


def _signal_group_evidence(
    manifest: dict[str, Any], controller_no: str, heads: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for group in sorted(
        (
            item
            for item in manifest["signal_groups"]
            if str(item["controller_no"]) == controller_no
        ),
        key=lambda item: _id_sort_key(item["sg_no"]),
    ):
        sg_no = int(group["sg_no"])
        result.append(
            {
                "id": group["id"],
                "sg_no": sg_no,
                "name": group["name"],
                "head_ids": [
                    head["id"]
                    for head in heads
                    if head["signal_group_ref"].get("sg_no") == sg_no
                ],
            }
        )
    return result


def _inpx_daily_program_schedule_status(inpx_path: Path) -> str:
    root = ET.parse(inpx_path).getroot()
    present = any("dailyprog" in element.tag.lower() for element in root.iter())
    return "present_in_inpx" if present else "absent_in_inpx"


def _daily_list_dict(value: DailyProgramList) -> dict[str, Any]:
    return {
        "list_no": value.list_no,
        "name": value.name,
        "items": [asdict(item) for item in value.items],
    }


def _expand_daily_program_list(value: DailyProgramList) -> list[dict[str, Any]]:
    intervals: list[dict[str, Any]] = []
    if value.items[0].time_ms > 0:
        intervals.append(
            {
                "start_time_of_day_ms": 0,
                "end_time_of_day_ms": value.items[0].time_ms,
                "start_time_of_day_sec": 0.0,
                "end_time_of_day_sec": value.items[0].time_sec,
                "program_no": None,
                "status": "no_program_defined",
            }
        )
    for index, item in enumerate(value.items):
        end_ms = (
            value.items[index + 1].time_ms
            if index + 1 < len(value.items)
            else _DAY_MS
        )
        intervals.append(
            {
                "start_time_of_day_ms": item.time_ms,
                "end_time_of_day_ms": end_ms,
                "start_time_of_day_sec": item.time_sec,
                "end_time_of_day_sec": end_ms / 1000.0,
                "program_no": item.program_no,
                "status": "program_defined",
            }
        )
    return intervals


def _effective_program_at(
    intervals: list[dict[str, Any]], time_of_day_ms: int
) -> int | None:
    for interval in intervals:
        if (
            interval["start_time_of_day_ms"]
            <= time_of_day_ms
            < interval["end_time_of_day_ms"]
        ):
            value = interval["program_no"]
            return int(value) if value is not None else None
    return None


def _active_program_evidence(
    *,
    controller: dict[str, Any],
    definition: SignalDefinition,
    inpx_daily_status: str,
    simulation_start_sec: float,
) -> tuple[dict[str, Any], int | None, dict[str, str] | None]:
    configured_no = int(controller["active_program_no"])
    program_match = configured_no in definition.programs
    daily_match = configured_no in definition.daily_program_lists
    start_ms = round(simulation_start_sec * 1000.0) % _DAY_MS
    sig_daily_status = (
        "present_in_sig"
        if definition.daily_program_lists
        else (
            "empty_in_sig"
            if definition.daily_program_lists_element_present
            else "absent_in_sig"
        )
    )
    evidence: dict[str, Any] = {
        "configured_prog_no": configured_no,
        "source_attribute": "inpx.signalController.progNo",
        "inpx_daily_program_schedule_status": inpx_daily_status,
        "daily_program_schedule_status": inpx_daily_status,
        "sig_daily_program_list_status": sig_daily_status,
        "daily_program_lists": [
            _daily_list_dict(value)
            for value in definition.daily_program_lists.values()
        ],
        "simulation_start": {
            "time_of_day_ms": start_ms,
            "time_of_day_sec": start_ms / 1000.0,
            "source_attribute": "inpx.simulation.startTm",
        },
        "runtime_readback": {
            "status": "NOT_EVALUATED",
            "source": "VISSIM_COM.ISignalController.ProgNo",
            "reason": "compile_time_artifact_has_no_runtime_COM_readback",
        },
        "fallback_used": False,
    }

    if program_match and daily_match:
        evidence.update(
            {
                "mode": "ambiguous_progNo",
                "program_no": None,
                "effective_program_at_start": None,
                "provenance": "NOT_EVALUATED",
                "compile_time_status": "NOT_EVALUATED",
                "time_indexed_schedule": [],
            }
        )
        return (
            evidence,
            None,
            {
                "code": "ambiguous_active_program_reference",
                "detail": f"progNo={configured_no} matches a program and daily program list",
            },
        )
    if program_match:
        evidence.update(
            {
                "mode": "static_program",
                "program_no": configured_no,
                "effective_program_at_start": configured_no,
                "provenance": "static_inpx_progNo",
                "compile_time_status": "PASS",
                "time_indexed_schedule": [
                    {
                        "start_time_of_day_ms": 0,
                        "end_time_of_day_ms": _DAY_MS,
                        "start_time_of_day_sec": 0.0,
                        "end_time_of_day_sec": _DAY_MS / 1000.0,
                        "program_no": configured_no,
                        "status": "program_defined",
                    }
                ],
            }
        )
        return evidence, configured_no, None
    if daily_match:
        daily_list = definition.daily_program_lists[configured_no]
        intervals = _expand_daily_program_list(daily_list)
        effective_no = _effective_program_at(intervals, start_ms)
        evidence.update(
            {
                "mode": "daily_program_list",
                "program_no": effective_no,
                "daily_program_list_no": configured_no,
                "effective_program_at_start": effective_no,
                "provenance": "inpx_progNo_selects_sig_dailyProgList",
                "compile_time_status": (
                    "PASS" if effective_no is not None else "NOT_EVALUATED"
                ),
                "time_indexed_schedule": intervals,
            }
        )
        if effective_no is None:
            return (
                evidence,
                None,
                {
                    "code": "no_active_program_at_simulation_start",
                    "detail": (
                        f"dailyProgList={configured_no}; start_time_of_day_ms={start_ms}"
                    ),
                },
            )
        return evidence, effective_no, None

    evidence.update(
        {
            "mode": "unresolved_progNo",
            "program_no": None,
            "effective_program_at_start": None,
            "provenance": "NOT_EVALUATED",
            "compile_time_status": "NOT_EVALUATED",
            "time_indexed_schedule": [],
        }
    )
    return (
        evidence,
        None,
        {
            "code": "missing_active_signal_program",
            "detail": (
                f"INPX progNo={configured_no}; programs={list(definition.programs)}; "
                f"daily_lists={list(definition.daily_program_lists)}"
            ),
        },
    )


def compile_network(inpx: str | Path) -> dict[str, Any]:
    """Compile topology plus canonical all-program signal references."""

    inpx_path = Path(inpx).resolve()
    manifest = compile_inpx(inpx_path)
    errors: list[dict[str, str]] = []
    schedules: list[dict[str, Any]] = []
    classifications: list[dict[str, Any]] = []
    inpx_daily_status = _inpx_daily_program_schedule_status(inpx_path)
    simulation_start_sec = float(manifest["simulation"]["start_time_sec"])

    for controller in manifest["signal_controllers"]:
        controller_id = str(controller["id"])
        controller_no = str(controller["vissim_no"])
        heads = _controller_heads(manifest, controller_no)
        classification, reason = _controller_classification(controller, heads)
        classifications.append(
            {
                "controller_id": controller_id,
                "controller_no": controller_no,
                "classification": classification,
                "reason": reason,
                "supply_file_2": controller["supply_file_2"],
                "signal_head_count": len(heads),
                "signal_head_ids": [head["id"] for head in heads],
            }
        )
        if classification == "auxiliary" or classification == "model_excluded":
            continue
        if classification == "invalid":
            error_code = (
                "missing_signal_head_provenance"
                if reason == "missing_signal_head_provenance"
                else "missing_signal_program"
            )
            errors.append(
                {
                    "code": error_code,
                    "entity_id": controller_id,
                    "detail": reason,
                }
            )
            continue
        source = _resolve_supply_file(inpx_path, controller["supply_file_2"])
        if not source.is_file():
            errors.append({"code": "missing_signal_program", "entity_id": controller_id, "detail": str(source)})
            continue
        try:
            definition = parse_sig_definition(source)
            programs = definition.programs
        except Exception as exc:
            errors.append({"code": "invalid_signal_program", "entity_id": controller_id, "detail": str(exc)})
            continue

        active_program, effective_program_no, schedule_error = _active_program_evidence(
            controller=controller,
            definition=definition,
            inpx_daily_status=inpx_daily_status,
            simulation_start_sec=simulation_start_sec,
        )
        if schedule_error is not None:
            errors.append(
                {
                    "code": schedule_error["code"],
                    "entity_id": controller_id,
                    "detail": schedule_error["detail"],
                }
            )
        inpx_groups = {
            str(item["sg_no"]): item
            for item in manifest["signal_groups"]
            if str(item["controller_no"]) == controller_no
        }
        program_records: list[dict[str, Any]] = []
        extra_by_program: dict[str, list[str]] = {}
        for program_no, program in programs.items():
            sig_sgs = set(program.sg_timelines)
            for missing in sorted(set(inpx_groups) - sig_sgs, key=_id_sort_key):
                errors.append(
                    {
                        "code": "missing_signal_group_timeline",
                        "entity_id": f"sg:{controller_no}:{missing}",
                        "detail": f"program={program_no}; source={source}",
                    }
                )
            for sg_no in sorted(set(inpx_groups) & sig_sgs, key=_id_sort_key):
                inpx_name = str(inpx_groups[sg_no]["name"])
                sig_name = str(program.sg_timelines[sg_no].name)
                if inpx_name != sig_name:
                    errors.append(
                        {
                            "code": "signal_group_name_mismatch",
                            "entity_id": f"sg:{controller_no}:{sg_no}",
                            "detail": f"program={program_no}; inpx={inpx_name!r}; sig={sig_name!r}",
                        }
                    )
            extra_by_program[str(program_no)] = sorted(
                sig_sgs - set(inpx_groups), key=_id_sort_key
            )
            program_records.append(_program_dict(program, source, inpx_path.parent))
        schedules.append(
            {
                "id": f"schedule:fixed:{controller_no}",
                "controller_id": controller_id,
                "controller_no": controller_no,
                "controller_offset_sec": float(controller["controller_offset_sec"]),
                "phase_formula": "mod(sim_time_sec + start_time_of_day_sec - cycle_epoch_sec - program_offset_sec - controller_offset_sec, cycle_length_sec)",
                "active_program": active_program,
                "program": (
                    _program_dict(programs[effective_program_no], source, inpx_path.parent)
                    if effective_program_no in programs
                    else None
                ),
                "programs": program_records,
                "program_nos": list(programs),
                "source_path": _portable_source_path(source, inpx_path.parent),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "signal_groups": _signal_group_evidence(manifest, controller_no, heads),
                "signal_heads": [_head_evidence(head) for head in heads],
                "extra_program_sg_nos": extra_by_program,
            }
        )

    manifest["compiler_version"] = COMPILER_VERSION
    manifest["schedules"]["fixed"] = schedules
    compiler_sources = _compiler_source_hashes()
    manifest["signal_reference"] = {
        "schema_version": SIGNAL_REFERENCE_SCHEMA_VERSION,
        "compiler_version": COMPILER_VERSION,
        "compiler_source_sha256": compiler_sources,
        "compiler_hash": canonical_json_sha256(compiler_sources),
        "inpx_sha256": manifest["source"]["inpx_sha256"],
        "active_program_schedule_status": inpx_daily_status,
        "active_program_schedule_provenance": "per_controller",
        "active_program_runtime_readback_status": "NOT_EVALUATED",
        "active_program_runtime_readback_reason": (
            "compile_time_artifact_has_no_runtime_COM_readback"
        ),
        "fallback_used": False,
        "controller_classifications": classifications,
        "selected_controller_nos": [
            item["controller_no"]
            for item in classifications
            if item["classification"] == "model_selected"
        ],
        "auxiliary_controller_nos": [
            item["controller_no"]
            for item in classifications
            if item["classification"] == "auxiliary"
        ],
        "excluded_controllers": [
            item
            for item in classifications
            if item["classification"] == "model_excluded"
        ],
        "source_sig_sha256": [
            {
                "controller_no": schedule["controller_no"],
                "source_path": schedule["source_path"],
                "sha256": schedule["source_sha256"],
            }
            for schedule in schedules
        ],
    }
    hydraulic_view = contract_topology(
        manifest,
        urban_dt_sec=float(manifest.get("defaults", {}).get("urban_dt_sec", 1.0)),
    )
    manifest.update(hydraulic_view)
    errors.extend(hydraulic_view["contraction_report"]["errors"])
    manifest["topology_hash"] = canonical_json_sha256(
        {key: value for key, value in manifest.items() if key not in {"topology_hash", "validation_report"}}
    )
    base_report = validate_topology(manifest)
    errors.extend(base_report["errors"])
    errors.sort(key=lambda item: (item["code"], item["entity_id"], item["detail"]))
    manifest["validation_report"] = {
        **base_report,
        "valid": not errors,
        "error_count": len(errors),
        "errors": errors,
        "compiled_signal_programs": len(schedules),
        "compiled_all_programs": sum(len(item["programs"]) for item in schedules),
        "selected_model_controllers": sum(
            item["classification"] == "model_selected" for item in classifications
        ),
        "auxiliary_signal_controllers": sum(
            item["classification"] == "auxiliary" for item in classifications
        ),
        "excluded_signal_controllers": sum(
            item["classification"] == "model_excluded" for item in classifications
        ),
        "contraction": hydraulic_view["contraction_report"],
    }
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inpx", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    manifest = compile_network(args.inpx)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json_text(manifest) + "\n", encoding="utf-8")
    report = manifest["validation_report"]
    print(
        f"valid={report['valid']} errors={report['error_count']} "
        f"controllers={report['compiled_signal_programs']} hash={manifest['topology_hash']}"
    )
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
