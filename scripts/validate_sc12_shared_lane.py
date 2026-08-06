from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "sc12-shared-lane-v2.1"
REFERENCE_SCHEMA_VERSION = "signal-reference-v2.1"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NOT_EVALUATED = "NOT_EVALUATED"

EXPECTED_HEADS = {
    "50201": {"link_no": "1220012103", "lane_no": 2, "sg_no": 5},
    "50202": {"link_no": "1220012103", "lane_no": 1, "sg_no": 2},
    "50601": {"link_no": "1220013600", "lane_no": 2, "sg_no": 1},
    "50602": {"link_no": "1220013600", "lane_no": 1, "sg_no": 6},
}

EXPECTED_CONNECTORS = {
    "10241": {
        "lane_count": 2,
        "from_endpoint": {
            "link_no": "1220012103",
            "lane_no": 1,
            "lane_id": "lane:1220012103:1",
        },
        "to_endpoint": {
            "link_no": "1220013700",
            "lane_no": 1,
            "lane_id": "lane:1220013700:1",
        },
        "connector_lane_ids": ["lane:10241:1", "lane:10241:2"],
        "lane_mapping": [
            {
                "from_lane_id": "lane:1220012103:1",
                "connector_lane_id": "lane:10241:1",
                "to_lane_id": "lane:1220013700:1",
            },
            {
                "from_lane_id": "lane:1220012103:2",
                "connector_lane_id": "lane:10241:2",
                "to_lane_id": "lane:1220013700:2",
            },
        ],
    },
    "10242": {
        "lane_count": 1,
        "from_endpoint": {
            "link_no": "1220012103",
            "lane_no": 2,
            "lane_id": "lane:1220012103:2",
        },
        "to_endpoint": {
            "link_no": "1220015100",
            "lane_no": 3,
            "lane_id": "lane:1220015100:3",
        },
        "connector_lane_ids": ["lane:10242:1"],
        "lane_mapping": [
            {
                "from_lane_id": "lane:1220012103:2",
                "connector_lane_id": "lane:10242:1",
                "to_lane_id": "lane:1220015100:3",
            }
        ],
    },
    "10238": {
        "lane_count": 2,
        "from_endpoint": {
            "link_no": "1220013600",
            "lane_no": 1,
            "lane_id": "lane:1220013600:1",
        },
        "to_endpoint": {
            "link_no": "1220012003",
            "lane_no": 1,
            "lane_id": "lane:1220012003:1",
        },
        "connector_lane_ids": ["lane:10238:1", "lane:10238:2"],
        "lane_mapping": [
            {
                "from_lane_id": "lane:1220013600:1",
                "connector_lane_id": "lane:10238:1",
                "to_lane_id": "lane:1220012003:1",
            },
            {
                "from_lane_id": "lane:1220013600:2",
                "connector_lane_id": "lane:10238:2",
                "to_lane_id": "lane:1220012003:2",
            },
        ],
    },
    "10240": {
        "lane_count": 1,
        "from_endpoint": {
            "link_no": "1220013600",
            "lane_no": 2,
            "lane_id": "lane:1220013600:2",
        },
        "to_endpoint": {
            "link_no": "1220012600",
            "lane_no": 3,
            "lane_id": "lane:1220012600:3",
        },
        "connector_lane_ids": ["lane:10240:1"],
        "lane_mapping": [
            {
                "from_lane_id": "lane:1220013600:2",
                "connector_lane_id": "lane:10240:1",
                "to_lane_id": "lane:1220012600:3",
            }
        ],
    },
}

EXPECTED_STOCKS = {
    "lane:1220012103:1": {
        "direction": "EB",
        "head_no": "50202",
        "sg_no": 2,
        "movements": ["movement:10241"],
    },
    "lane:1220012103:2": {
        "direction": "EB",
        "head_no": "50201",
        "sg_no": 5,
        "movements": ["movement:10241", "movement:10242"],
    },
    "lane:1220013600:1": {
        "direction": "WB",
        "head_no": "50602",
        "sg_no": 6,
        "movements": ["movement:10238"],
    },
    "lane:1220013600:2": {
        "direction": "WB",
        "head_no": "50601",
        "sg_no": 1,
        "movements": ["movement:10238", "movement:10240"],
    },
}


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _gate(status: str, summary: str, **evidence: Any) -> dict[str, Any]:
    return {"status": status, "summary": summary, "evidence": evidence}


def _index_by_number(items: Any) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    if not isinstance(items, list):
        return {}, ["expected a list"]
    result: dict[str, Mapping[str, Any]] = {}
    reasons: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            reasons.append("encountered a non-object record")
            continue
        number = str(item.get("vissim_no", "")).strip()
        if not number:
            reasons.append("encountered a record without vissim_no")
        elif number in result:
            reasons.append(f"duplicate vissim_no {number}")
        else:
            result[number] = item
    return result, reasons


def _load_reference(path: Path) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    if not path.is_file():
        return None, _gate(
            STATUS_NOT_EVALUATED,
            "compiler reference is missing",
            path=str(path.resolve(strict=False)),
            reasons=["reference file does not exist"],
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, _gate(
            STATUS_FAIL,
            "compiler reference is not readable JSON",
            path=str(path.resolve(strict=False)),
            reasons=[f"{type(exc).__name__}: {exc}"],
        )
    if not isinstance(payload, Mapping):
        return None, _gate(
            STATUS_FAIL,
            "compiler reference root is not an object",
            path=str(path.resolve(strict=False)),
            reasons=[f"root type is {type(payload).__name__}"],
        )
    reference = payload.get("signal_reference")
    actual_schema = reference.get("schema_version") if isinstance(reference, Mapping) else None
    reasons = [] if actual_schema == REFERENCE_SCHEMA_VERSION else [
        f"signal_reference.schema_version must be {REFERENCE_SCHEMA_VERSION}"
    ]
    return payload, _gate(
        STATUS_FAIL if reasons else STATUS_PASS,
        "compiler reference schema is invalid" if reasons else "full compiler signal reference loaded",
        path=str(path.resolve(strict=False)),
        expected_schema_version=REFERENCE_SCHEMA_VERSION,
        actual_schema_version=actual_schema,
        reasons=reasons,
    )


def _find_sc12_schedule(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    schedules_root = payload.get("schedules")
    schedules = schedules_root.get("fixed") if isinstance(schedules_root, Mapping) else None
    if not isinstance(schedules, list):
        return None, _gate(
            STATUS_NOT_EVALUATED,
            "fixed signal schedules are absent",
            reasons=["schedules.fixed is not a list"],
        )
    matches = [
        item
        for item in schedules
        if isinstance(item, Mapping) and str(item.get("controller_no", "")) == "12"
    ]
    if len(matches) != 1:
        return None, _gate(
            STATUS_NOT_EVALUATED if not matches else STATUS_FAIL,
            "SC12 fixed schedule is not uniquely available",
            count=len(matches),
            reasons=[f"expected one SC12 schedule, found {len(matches)}"],
        )
    schedule = matches[0]
    return schedule, _gate(
        STATUS_PASS,
        "one SC12 fixed schedule is available",
        schedule_id=schedule.get("id"),
        source_path=schedule.get("source_path"),
        source_sha256=schedule.get("source_sha256"),
        reasons=[],
    )


def _validate_heads(schedule: Mapping[str, Any] | None) -> dict[str, Any]:
    if schedule is None:
        return _gate(
            STATUS_NOT_EVALUATED,
            "SC12 head assignments cannot be checked without its schedule",
            reasons=["SC12 schedule unavailable"],
        )
    heads, index_reasons = _index_by_number(schedule.get("signal_heads"))
    reasons = list(index_reasons)
    evidence: dict[str, Any] = {}
    for head_no, expected in EXPECTED_HEADS.items():
        head = heads.get(head_no)
        actual = (
            {
                "link_no": str(head.get("link_no")),
                "lane_no": head.get("lane_no"),
                "sg_no": head.get("sg_no"),
            }
            if head is not None
            else None
        )
        evidence[head_no] = {"expected": expected, "actual": actual}
        if actual != expected:
            reasons.append(f"head {head_no} assignment mismatch")
    return _gate(
        STATUS_FAIL if reasons else STATUS_PASS,
        "SC12 target head assignments differ" if reasons else "SC12 target heads match their lane and SG assignments",
        heads=evidence,
        reasons=reasons,
    )


def _connector_mapping(connector: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    raw_mappings = connector.get("lane_mapping")
    if not isinstance(raw_mappings, list):
        return [], ["lane_mapping is not a list"]
    mappings: list[dict[str, Any]] = []
    reasons: list[str] = []
    for raw in raw_mappings:
        if not isinstance(raw, Mapping):
            reasons.append("lane_mapping contains a non-object")
            continue
        from_lane_id = str(raw.get("from_lane_id", ""))
        connector_lane_id = str(raw.get("connector_lane_id", ""))
        if not from_lane_id or not connector_lane_id:
            reasons.append("lane_mapping lacks from_lane_id or connector_lane_id")
        mappings.append(
            {
                "from_lane_id": from_lane_id,
                "connector_lane_id": connector_lane_id,
                "to_lane_id": raw.get("to_lane_id"),
            }
        )
    mappings.sort(key=lambda item: item["connector_lane_id"])
    return mappings, reasons


def _endpoint_view(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    return {
        "link_no": str(value.get("link_no")),
        "lane_no": value.get("lane_no"),
        "lane_id": value.get("lane_id"),
    }


def _connector_lane_ids(connector: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    lanes = connector.get("lanes")
    if not isinstance(lanes, list):
        return [], ["lanes is not a list"]
    lane_ids: list[str] = []
    reasons: list[str] = []
    for lane in lanes:
        if not isinstance(lane, Mapping) or not str(lane.get("id", "")):
            reasons.append("lanes contains a record without an id")
            continue
        lane_ids.append(str(lane["id"]))
    lane_ids.sort()
    return lane_ids, reasons


def _validate_connectors(payload: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, list[str]]]:
    if payload is None:
        return (
            _gate(
                STATUS_NOT_EVALUATED,
                "connector lane mappings cannot be checked",
                reasons=["compiler reference unavailable"],
            ),
            {},
        )
    connectors, index_reasons = _index_by_number(payload.get("connectors"))
    reasons = list(index_reasons)
    source_maps: dict[str, list[str]] = {}
    evidence: dict[str, Any] = {}
    unavailable: list[str] = []
    for connector_no, expected in EXPECTED_CONNECTORS.items():
        connector = connectors.get(connector_no)
        if connector is None:
            unavailable.append(connector_no)
            evidence[connector_no] = {"expected": expected, "actual": None}
            continue
        mappings, mapping_reasons = _connector_mapping(connector)
        actual_sources = [item["from_lane_id"] for item in mappings]
        source_maps[connector_no] = actual_sources
        connector_lane_ids, lane_reasons = _connector_lane_ids(connector)
        actual = {
            "lane_count": connector.get("lane_count"),
            "from_endpoint": _endpoint_view(connector.get("from_endpoint")),
            "to_endpoint": _endpoint_view(connector.get("to_endpoint")),
            "connector_lane_ids": connector_lane_ids,
            "lane_mapping": mappings,
        }
        evidence[connector_no] = {
            "expected": expected,
            "actual": actual,
        }
        reasons.extend(f"connector {connector_no}: {reason}" for reason in mapping_reasons)
        reasons.extend(f"connector {connector_no}: {reason}" for reason in lane_reasons)
        if actual != expected:
            reasons.append(f"connector {connector_no} exact topology contract mismatch")
    status = STATUS_FAIL if reasons else STATUS_NOT_EVALUATED if unavailable else STATUS_PASS
    return (
        _gate(
            status,
            "SC12 connector mappings are invalid"
            if status == STATUS_FAIL
            else "SC12 connector mappings are incomplete"
            if status == STATUS_NOT_EVALUATED
            else "SC12 through and left movements resolve to the expected source lanes",
            connectors=evidence,
            missing_connectors=unavailable,
            reasons=reasons,
        ),
        source_maps,
    )


def _validate_physical_stock_contract(source_maps: Mapping[str, list[str]]) -> dict[str, Any]:
    if set(source_maps) != set(EXPECTED_CONNECTORS):
        return _gate(
            STATUS_NOT_EVALUATED,
            "physical stock sharing cannot be proved from incomplete connector evidence",
            reasons=["one or more required connector mappings are unavailable"],
        )
    actual_movements: dict[str, list[str]] = {stock_id: [] for stock_id in EXPECTED_STOCKS}
    for connector_no, source_ids in source_maps.items():
        for stock_id in source_ids:
            actual_movements.setdefault(stock_id, []).append(f"movement:{connector_no}")
    for movements in actual_movements.values():
        movements.sort(key=lambda value: int(value.split(":", 1)[1]))

    reasons: list[str] = []
    stock_evidence: dict[str, Any] = {}
    for stock_id, expected in EXPECTED_STOCKS.items():
        actual = actual_movements.get(stock_id, [])
        stock_evidence[stock_id] = {
            **expected,
            "actual_movements": actual,
            "physical_stock_instances": 1,
        }
        if actual != expected["movements"]:
            reasons.append(f"{stock_id} movement membership mismatch")
    unexpected_stocks = sorted(set(actual_movements) - set(EXPECTED_STOCKS))
    if unexpected_stocks:
        reasons.append("unexpected source stocks in SC12 target movements")
    return _gate(
        STATUS_FAIL if reasons else STATUS_PASS,
        "shared-lane stock contract is contradicted" if reasons else "each upstream lane is one physical stock shared by its permitted movements",
        stock_identity="upstream VISSIM lane_id",
        movement_queue_duplication_allowed=False,
        unique_physical_stock_count=len(EXPECTED_STOCKS),
        movement_membership_reference_count=sum(len(item["movements"]) for item in EXPECTED_STOCKS.values()),
        stocks=stock_evidence,
        unexpected_stocks=unexpected_stocks,
        reasons=reasons,
    )


def _raw_ms_timeline(timeline: Any) -> Mapping[str, Any] | None:
    if not isinstance(timeline, Mapping):
        return None
    commands = timeline.get("commands")
    fixed_states = timeline.get("fixed_states")
    intervals = timeline.get("intervals")
    if not all(isinstance(value, list) for value in (commands, fixed_states, intervals)):
        return None
    return {
        "cycle_length_ms": timeline.get("cycle_length_ms"),
        "permanent_red": timeline.get("permanent_red"),
        "commands": [
            {"display_id": item.get("display_id"), "begin_ms": item.get("begin_ms")}
            for item in commands
            if isinstance(item, Mapping)
        ],
        "fixed_states": [
            {"display_id": item.get("display_id"), "duration_ms": item.get("duration_ms")}
            for item in fixed_states
            if isinstance(item, Mapping)
        ],
        "intervals": [
            {
                "start_ms": item.get("start_ms"),
                "end_ms": item.get("end_ms"),
                "state": item.get("state"),
                "display_id": item.get("display_id"),
                "source_kind": item.get("source_kind"),
            }
            for item in intervals
            if isinstance(item, Mapping)
        ],
    }


def _validate_profile_timeline_policy(schedule: Mapping[str, Any] | None) -> dict[str, Any]:
    if schedule is None or not isinstance(schedule.get("programs"), list):
        return _gate(
            STATUS_NOT_EVALUATED,
            "SC12 profile timeline policy cannot be checked",
            policy_scope="current_profile_bundle_policy",
            physical_invariant=False,
            reasons=["SC12 programs are unavailable"],
        )
    programs = schedule["programs"]
    by_number: dict[int, Mapping[str, Any]] = {}
    reasons: list[str] = []
    for program in programs:
        if not isinstance(program, Mapping) or isinstance(program.get("active_prog_no"), bool):
            reasons.append("SC12 contains a malformed program record")
            continue
        try:
            number = int(program.get("active_prog_no"))
        except (TypeError, ValueError):
            reasons.append("SC12 program number is not an integer")
            continue
        if number in by_number:
            reasons.append(f"duplicate SC12 program {number}")
        else:
            by_number[number] = program

    unavailable = sorted({1, 2, 3} - set(by_number))
    comparisons: list[dict[str, Any]] = []
    for program_no in (1, 2, 3):
        program = by_number.get(program_no)
        if program is None:
            continue
        timelines = program.get("sg_timelines")
        if not isinstance(timelines, Mapping):
            reasons.append(f"program {program_no} sg_timelines is unavailable")
            continue
        for left, right in (("2", "5"), ("1", "6")):
            left_raw = _raw_ms_timeline(timelines.get(left))
            right_raw = _raw_ms_timeline(timelines.get(right))
            equal = left_raw is not None and left_raw == right_raw
            comparisons.append(
                {
                    "program_no": program_no,
                    "left_sg": int(left),
                    "right_sg": int(right),
                    "raw_ms_timeline_equal": equal,
                    "left_raw_ms_timeline": left_raw,
                    "right_raw_ms_timeline": right_raw,
                }
            )
            if not equal:
                reasons.append(f"program {program_no} SG{left} and SG{right} raw-ms timelines differ")
    status = STATUS_FAIL if reasons else STATUS_NOT_EVALUATED if unavailable else STATUS_PASS
    return _gate(
        status,
        "SC12 paired SG timeline policy is violated"
        if status == STATUS_FAIL
        else "SC12 programs 1/2/3 are incomplete"
        if status == STATUS_NOT_EVALUATED
        else "SC12 programs 1/2/3 preserve both paired raw-ms timelines",
        policy_scope="current_profile_bundle_policy",
        physical_invariant=False,
        policy_statement="SG2==SG5 and SG1==SG6 only for the current SC12 profile bundle",
        expected_program_nos=[1, 2, 3],
        missing_program_nos=unavailable,
        comparisons=comparisons,
        reasons=reasons,
    )


def validate_reference(reference_path: Path) -> dict[str, Any]:
    reference_path = reference_path.resolve(strict=False)
    payload, load_gate = _load_reference(reference_path)
    schedule, schedule_gate = _find_sc12_schedule(payload) if payload is not None else (
        None,
        _gate(
            STATUS_NOT_EVALUATED,
            "SC12 schedule cannot be located",
            reasons=["compiler reference unavailable"],
        ),
    )
    connector_gate, source_maps = _validate_connectors(payload)
    checks = {
        "reference_schema": load_gate,
        "sc12_schedule": schedule_gate,
        "head_assignments": _validate_heads(schedule),
        "connector_lane_mapping": connector_gate,
        "physical_stock_contract": _validate_physical_stock_contract(source_maps),
        "profile_timeline_policy": _validate_profile_timeline_policy(schedule),
    }
    counts = {
        status: sum(check["status"] == status for check in checks.values())
        for status in (STATUS_PASS, STATUS_FAIL, STATUS_NOT_EVALUATED)
    }
    status = (
        STATUS_FAIL
        if counts[STATUS_FAIL]
        else STATUS_NOT_EVALUATED
        if counts[STATUS_NOT_EVALUATED]
        else STATUS_PASS
    )
    reasons = [name for name, check in checks.items() if check["status"] != STATUS_PASS]
    command_path = Path(__file__).resolve()
    return {
        "schema_version": SCHEMA_VERSION,
        "input_hashes": {"reference_sha256": _sha256_file(reference_path)},
        "command_version": {
            "command": "scripts/validate_sc12_shared_lane.py",
            "version": SCHEMA_VERSION,
            "sha256": _sha256_file(command_path),
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "reasons": reasons,
        "complete": status == STATUS_PASS,
        "sample_dimensions": {
            "signal_controller": 1 if schedule is not None else 0,
            "target_signal_heads": len(EXPECTED_HEADS),
            "target_connectors": len(EXPECTED_CONNECTORS),
            "resolved_target_connectors": len(source_maps),
            "physical_lane_stocks": len(EXPECTED_STOCKS),
            "signal_programs": len(
                schedule.get("programs", [])
                if schedule is not None and isinstance(schedule.get("programs"), list)
                else []
            ),
            "timeline_pair_comparisons": len(
                checks["profile_timeline_policy"]["evidence"].get("comparisons", [])
            ),
        },
        "units": {
            "lane_stock": "one upstream VISSIM lane_id",
            "movement": "one VISSIM connector",
            "timeline": "integer millisecond",
            "sha256": "SHA-256 hex digest of raw bytes",
        },
        "downstream_consumers": [
            "A physical stock topology",
            "B mass-conserving state projection",
            "C N-phase signal action model",
            "K plant fidelity audit",
        ],
        "physical_stock_contract": {
            "stock_identity": "upstream VISSIM lane_id",
            "movement_queue_duplication_allowed": False,
            "shared_lane_rule": "one physical lane stock may feed multiple connector movements without cloning its vehicle count",
            "stocks": EXPECTED_STOCKS,
        },
        "profile_bundle_policy": {
            "scope": "current_profile_bundle_policy",
            "physical_invariant": False,
            "equal_raw_ms_timeline_pairs": [[2, 5], [1, 6]],
            "program_nos": [1, 2, 3],
        },
        "summary": {
            "pass": counts[STATUS_PASS],
            "fail": counts[STATUS_FAIL],
            "not_evaluated": counts[STATUS_NOT_EVALUATED],
        },
        "checks": checks,
    }


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path = path.resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
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
    parser = argparse.ArgumentParser(
        description="Validate the SC12 shared through-and-left lane contract from a full compiler reference.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--reference", required=True, help="full signal-reference-v2.1 compiler JSON")
    parser.add_argument("--out", required=True, help="atomic sc12-shared-lane-v2.1 JSON output path")
    parser.add_argument("--strict", action="store_true", help="exit 2 when any check is FAIL")
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="exit 3 when any required check is NOT_EVALUATED; requires --strict",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if args.require_complete and not args.strict:
        parser.error("--require-complete requires --strict")
    artifact = validate_reference(Path(args.reference))
    try:
        atomic_write_json(Path(args.out), artifact)
    except OSError as exc:
        print(f"failed to write SC12 validator artifact: {exc}", file=sys.stderr)
        return 4
    summary = artifact["summary"]
    print(
        f"SC12 shared lane: status={artifact['status']} PASS={summary['pass']} "
        f"FAIL={summary['fail']} NOT_EVALUATED={summary['not_evaluated']}"
    )
    print(f"JSON: {Path(args.out).resolve(strict=False)}")
    if args.strict and summary["fail"]:
        return 2
    if args.require_complete and summary["not_evaluated"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
