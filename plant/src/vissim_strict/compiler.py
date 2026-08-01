"""Canonical Phase 0 compiler for an INPX network and its VISSIG programs."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from pathlib import Path
from typing import Any

from .contraction import contract_topology
from .signal_program import ControllerProgram, parse_sig
from .topology import canonical_json_sha256, canonical_json_text, compile_inpx, validate_topology


COMPILER_VERSION = "vissim-strict-phase0/1.0.0"


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
        "cycle_length_sec": program.cycle_length_sec,
        "switchpoint_sec": program.switchpoint_sec,
        "program_offset_sec": program.program_offset_sec,
        "display_states": dict(program.display_states),
        "sequences": {key: asdict(value) for key, value in sorted(program.sequences.items())},
        "sg_timelines": {key: asdict(value) for key, value in sorted(program.sg_timelines.items())},
        "source_path": _portable_source_path(source, network_dir),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }


def compile_network(inpx: str | Path) -> dict[str, Any]:
    """Compile topology plus each controller's active fixed-time program."""

    inpx_path = Path(inpx).resolve()
    manifest = compile_inpx(inpx_path)
    errors: list[dict[str, str]] = []
    schedules: list[dict[str, Any]] = []

    for controller in manifest["signal_controllers"]:
        controller_id = str(controller["id"])
        source = _resolve_supply_file(inpx_path, controller["supply_file_2"])
        if not source.is_file():
            errors.append({"code": "missing_signal_program", "entity_id": controller_id, "detail": str(source)})
            continue
        try:
            program = parse_sig(source, int(controller["active_program_no"]))
        except Exception as exc:
            errors.append({"code": "invalid_signal_program", "entity_id": controller_id, "detail": str(exc)})
            continue

        inpx_sgs = {
            str(item["sg_no"])
            for item in manifest["signal_groups"]
            if str(item["controller_no"]) == str(controller["vissim_no"])
        }
        sig_sgs = set(program.sg_timelines)
        for missing in sorted(inpx_sgs - sig_sgs, key=int):
            errors.append(
                {
                    "code": "missing_signal_group_timeline",
                    "entity_id": f"sg:{controller['vissim_no']}:{missing}",
                    "detail": str(source),
                }
            )
        schedules.append(
            {
                "id": f"schedule:fixed:{controller['vissim_no']}",
                "controller_id": controller_id,
                "controller_no": str(controller["vissim_no"]),
                "controller_offset_sec": float(controller["controller_offset_sec"]),
                "phase_formula": "mod(sim_time_sec + start_time_of_day_sec - cycle_epoch_sec - program_offset_sec - controller_offset_sec, cycle_length_sec)",
                "program": _program_dict(program, source, inpx_path.parent),
                "extra_program_sg_nos": sorted(sig_sgs - inpx_sgs, key=int),
            }
        )

    manifest["compiler_version"] = COMPILER_VERSION
    manifest["schedules"]["fixed"] = schedules
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
