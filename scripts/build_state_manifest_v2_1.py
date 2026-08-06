"""Build the closed, hash-bound state manifest for B1a projection replay."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping, Sequence


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
PLANT_ROOT = REPO_ROOT / "plant"
for search_root in (SCRIPT_ROOT, PLANT_ROOT):
    if str(search_root) not in sys.path:
        sys.path.insert(0, str(search_root))

from approve_physical_stock_topology import (  # noqa: E402
    ValidatedApprovalBundle,
    validate_approval_artifact,
)
from src.vissim_strict.physical_projection import (  # noqa: E402
    POSITION_TOLERANCE_M,
    RUN_ID_PATTERN,
    SHA256_PATTERN,
    StrictJsonError,
    atomic_write_json,
    file_sha256,
    projection_sidecar_path,
    read_bounded_bytes,
    resolve_contained_path,
    strict_load_json,
    strict_json_loads,
    workspace_relative_path,
)
from src.vissim_strict.physical_projection_reference import MAX_STATE_BYTES  # noqa: E402
from src.vissim_strict.run_evidence import (  # noqa: E402
    MAX_RUN_MANIFEST_BYTES,
    MONOTONIC_CLOCK,
    RunManifestValidationError,
    parse_monotonic_clock_line,
    validate_run_manifest,
)
from src.vissim_strict.topology import canonical_json_sha256  # noqa: E402


SELECTION_SCHEMA_VERSION = "state-selection-v2.1"
SCHEMA_VERSION = "state-manifest-v2.1"
SELECTION_UNITS = {"sim_sec": "s"}
SELECTION_DOWNSTREAM_CONSUMERS = ["build_state_manifest_v2_1"]
UNITS = {"sim_sec": "s"}
DOWNSTREAM_CONSUMERS = ["validate_state_projection_v2_1"]
FAIL_CLOSED_INPUT_EXCEPTIONS = (
    AttributeError,
    IndexError,
    KeyError,
    OSError,
    OverflowError,
    TypeError,
    ValueError,
)
SELECTION_ENTRY_FIELDS = {
    "run_manifest_path",
    "state_path",
    "run_id",
    "sim_sec",
    "required_vehicle_records",
}
SELECTION_FIELDS = {
    "schema_version",
    "input_hashes",
    "command_version",
    "status",
    "reasons",
    "sample_dimensions",
    "units",
    "downstream_consumers",
    "campaign_id",
    "expected_entry_count",
    "entries",
    "semantic_sha256",
}
STATE_ENTRY_FIELDS = {
    "state_path",
    "state_file_sha256",
    "run_id",
    "sim_sec",
    "run_manifest_path",
    "run_manifest_sha256",
    "required_vehicle_records",
    "projection_sidecar_path",
}
MANIFEST_FIELDS = {
    "schema_version",
    "input_hashes",
    "command_version",
    "status",
    "reasons",
    "sample_dimensions",
    "units",
    "downstream_consumers",
    "base_dir",
    "state_selection",
    "approved_topology",
    "states",
    "semantic_sha256",
}
MANIFEST_INPUT_HASH_NAMES = {
    "approving_manifest_sha256",
    "state_selection_file_sha256",
    "state_selection_semantic_sha256",
    "topology_file_sha256",
    "topology_semantic_sha256",
    "state_set_semantic_sha256",
}
CAPTURE_SCHEMA_VERSION = "vehicle-capture-evidence-v2.1"
MAX_CAPTURE_EVIDENCE_BYTES = 256 * 1024
MAX_CAPTURE_REQUEST_BYTES = 8 * 1024 * 1024
MAX_RAW_SAMPLE_ROWS = 20_000
MAX_CAPTURE_SAMPLES = 64
MAX_POSITIVE_INT32 = 2_147_483_647
MAX_POSITIVE_INT64 = 9_223_372_036_854_775_807
CAPTURE_FIELDS = (
    "schema_version",
    "run_id",
    "sim_sec",
    "qualification",
    "run_manifest_path",
    "run_manifest_sha256",
    "state_path",
    "vissim_version_raw",
    "counts",
    "capture_timer",
    "raw_attribute_samples",
    "semantic_sha256",
)
CAPTURE_COUNTS_FIELDS = (
    "collection_count_before",
    "collection_count_after",
    "record_count",
)
CAPTURE_TIMER_FIELDS = ("clock", "start_ns", "end_ns", "elapsed_sec")
RAW_SAMPLE_FIELDS = (
    "com_key",
    "no_value",
    "lane_raw",
    "parsed_link_no",
    "parsed_lane_no",
    "position_value",
    "speed_value",
)
STATE_RECORD_FIELDS = (
    "veh_no",
    "link_no",
    "lane_no",
    "position_m",
    "speed_kph",
    "stopped",
)
VEHICLE_RECORDS_FIELDS = (
    "schema_version",
    "complete",
    "paused_at_sim_sec",
    "capture_sim_sec_before",
    "capture_sim_sec_after",
    "source_attributes",
    "stopped_threshold_kph",
    "collection_count_before",
    "collection_count_after",
    "record_count",
    "unobservable_count",
    "external_source_count",
    "full_network_link_counts",
    "full_network_link_stopped_counts",
    "records",
)
VEHICLE_RECORDS_SOURCE_ATTRIBUTES_FIELDS = (
    "vehicle_number",
    "lane",
    "position",
    "speed",
)
VEHICLE_RECORDS_SOURCE_ATTRIBUTES = {
    "vehicle_number": "No",
    "lane": "Lane",
    "position": "Pos",
    "speed": "Speed",
}


class StateManifestValidationError(ValueError):
    def __init__(self, reasons: Sequence[Mapping[str, Any]]) -> None:
        self.reasons = tuple(dict(item) for item in reasons)
        super().__init__("; ".join(str(item.get("code", "")) for item in self.reasons))


class VehicleCaptureEvidenceError(ValueError):
    def __init__(self, reasons: Sequence[Mapping[str, Any]]) -> None:
        self.reasons = tuple(dict(item) for item in reasons)
        super().__init__("; ".join(str(item.get("code", "")) for item in self.reasons))


def _reason(code: str, detail: Any) -> dict[str, Any]:
    return {"code": code, "detail": detail}


def _exception_detail(exc: BaseException) -> Any:
    reasons = getattr(exc, "reasons", None)
    if isinstance(reasons, (list, tuple)) and reasons and all(
        isinstance(item, Mapping) for item in reasons
    ):
        return [dict(item) for item in reasons]
    return f"{type(exc).__name__}: {exc}"


def _finite_nonnegative(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return False
    return math.isfinite(number) and number >= 0.0


def _json_double(value: Any) -> float:
    if not isinstance(value, float) or not math.isfinite(value):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "expected JSON double")])
    return float(value)


def _json_double_equal(value: Any, expected: float, *, label: str) -> float:
    result = _json_double(value)
    if result != expected:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"{label} mismatch")])
    return result


def _json_int(value: Any, *, positive: bool = False) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "expected JSON integer")])
    if value < (1 if positive else 0):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "integer out of range")])
    return int(value)


def _bounded_json_int(
    value: Any,
    *,
    positive: bool = False,
    max_value: int | None = None,
    reason_code: str = "aggregate_mismatch",
) -> int:
    result = _json_int(value, positive=positive)
    if max_value is not None and result > max_value:
        raise VehicleCaptureEvidenceError([_reason(reason_code, "integer out of range")])
    return result


def _strict_load_json_no_bom(path: str | Path, *, max_bytes: int | None = None) -> Any:
    if max_bytes is None:
        try:
            data = Path(path).read_bytes()
        except MemoryError as exc:
            raise StrictJsonError("JSON artifact read exhausted memory") from exc
    else:
        data = read_bounded_bytes(path, max_bytes)
    if data.startswith(b"\xef\xbb\xbf"):
        raise StrictJsonError("UTF-8 BOM is not allowed for required capture evidence")
    try:
        return strict_json_loads(data.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise StrictJsonError(f"invalid UTF-8: {exc}") from exc


def _parse_vbs_lane_raw(lane_raw: str, *, row_label: str) -> tuple[int, int]:
    trimmed = lane_raw.strip(" \t")
    if trimmed.count("-") != 1:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"{row_label} malformed lane_raw")])
    left, right = trimmed.split("-", 1)
    for component in (left, right):
        if (
            not component
            or component[0] == "0"
            or any(char < "0" or char > "9" for char in component)
        ):
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"{row_label} malformed lane_raw")])
    link_no = int(left)
    lane_no = int(right)
    if link_no > MAX_POSITIVE_INT32 or lane_no > MAX_POSITIVE_INT32:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"{row_label} lane_raw out of range")])
    return link_no, lane_no


def vehicle_capture_sidecar_path(state_path: str | Path) -> Path:
    path = Path(state_path)
    return path.with_name(f"{path.stem}.vehicle_capture_v2_1.json")


def capture_evidence_semantic_payload(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {field: evidence[field] for field in CAPTURE_FIELDS[:-1]}


def capture_evidence_json_bytes(evidence: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _exact_capture_fields(value: Any, fields: Sequence[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or tuple(value.keys()) != tuple(fields):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"{label} exact-key order mismatch")])
    return value


def _exact_field_set(value: Any, fields: Sequence[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value.keys()) != set(fields):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"{label} exact-key mismatch")])
    return value


def _canonical_positive_stock_link_no(value: Any) -> int:
    if isinstance(value, bool):
        raise VehicleCaptureEvidenceError([_reason("topology_trust_mismatch", "invalid stock link_no")])
    if isinstance(value, int):
        if value <= 0 or value > MAX_POSITIVE_INT32:
            raise VehicleCaptureEvidenceError([_reason("topology_trust_mismatch", "invalid stock link_no")])
        return int(value)
    if isinstance(value, str):
        if not value or value[0] == "0" or not value.isdecimal():
            raise VehicleCaptureEvidenceError([_reason("topology_trust_mismatch", "invalid stock link_no")])
        link_no = int(value)
        if link_no > MAX_POSITIVE_INT32:
            raise VehicleCaptureEvidenceError([_reason("topology_trust_mismatch", "invalid stock link_no")])
        return link_no
    raise VehicleCaptureEvidenceError([_reason("topology_trust_mismatch", "invalid stock link_no")])


def _canonical_positive_stock_lane_no(value: Any) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
        or value > MAX_POSITIVE_INT32
    ):
        raise VehicleCaptureEvidenceError([_reason("topology_trust_mismatch", "invalid stock lane_no")])
    return int(value)


def _topology_lane_sets(topology: Mapping[str, Any]) -> tuple[set[tuple[int, int]], set[tuple[int, int]], set[tuple[int, int]]]:
    known: set[tuple[int, int]] = set()
    connector: set[tuple[int, int]] = set()
    road_lanes: dict[int, set[int]] = {}
    stocks = topology.get("stocks")
    if not isinstance(stocks, list):
        raise VehicleCaptureEvidenceError([_reason("topology_trust_mismatch", "topology stocks are unavailable")])
    for stock in stocks:
        if not isinstance(stock, Mapping):
            raise VehicleCaptureEvidenceError([_reason("topology_trust_mismatch", "malformed topology stock")])
        link_no = _canonical_positive_stock_link_no(stock.get("link_no"))
        lane_no = _canonical_positive_stock_lane_no(stock.get("lane_no"))
        key = (link_no, lane_no)
        known.add(key)
        parent_kind = stock.get("parent_kind")
        roles = stock.get("roles")
        role_set = set(roles) if isinstance(roles, list) and all(isinstance(item, str) for item in roles) else set()
        if parent_kind == "connector" or "connector" in role_set:
            connector.add(key)
        elif parent_kind == "link":
            road_lanes.setdefault(link_no, set()).add(lane_no)
    multilane = {
        (link_no, lane_no)
        for link_no, lane_nos in road_lanes.items()
        if len(lane_nos) >= 2
        for lane_no in lane_nos
    }
    return known, connector, multilane


def _normalize_raw_rows(raw_rows: Any, records_by_no: Mapping[int, Mapping[str, Any]], known_lanes: set[tuple[int, int]]) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, list) or len(raw_rows) > MAX_RAW_SAMPLE_ROWS:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "raw capture rows must be a bounded array")])
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index, row in enumerate(raw_rows):
        sample = _exact_capture_fields(row, RAW_SAMPLE_FIELDS, f"raw row[{index}]")
        com_key = _bounded_json_int(sample.get("com_key"), positive=True, max_value=MAX_POSITIVE_INT32)
        no_value = _bounded_json_int(sample.get("no_value"), positive=True, max_value=MAX_POSITIVE_INT32)
        link_no = _bounded_json_int(sample.get("parsed_link_no"), positive=True, max_value=MAX_POSITIVE_INT32)
        lane_no = _bounded_json_int(sample.get("parsed_lane_no"), positive=True, max_value=MAX_POSITIVE_INT32)
        position = _json_double(sample.get("position_value"))
        speed = _json_double(sample.get("speed_value"))
        lane_raw = sample.get("lane_raw")
        if not isinstance(lane_raw, str) or not lane_raw or len(lane_raw) > 256:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"raw row[{index}] invalid lane_raw")])
        raw_link_no, raw_lane_no = _parse_vbs_lane_raw(lane_raw, row_label=f"raw row[{index}]")
        if raw_link_no != link_no or raw_lane_no != lane_no:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"raw row[{index}] lane_raw/parser disagreement")])
        if com_key != no_value:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"raw row[{index}] COM key mismatch")])
        if no_value in seen:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"duplicate raw vehicle {no_value}")])
        seen.add(no_value)
        if (link_no, lane_no) not in known_lanes:
            raise VehicleCaptureEvidenceError([_reason("topology_trust_mismatch", f"unknown lane {link_no}-{lane_no}")])
        state_record = records_by_no.get(no_value)
        if state_record is None:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"raw vehicle {no_value} absent from state")])
        if (
            state_record.get("veh_no") != no_value
            or state_record.get("link_no") != link_no
            or state_record.get("lane_no") != lane_no
            or state_record.get("position_m") != position
            or state_record.get("speed_kph") != speed
        ):
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"raw/state disagreement for vehicle {no_value}")])
        rows.append({
            "com_key": com_key,
            "no_value": no_value,
            "lane_raw": lane_raw,
            "parsed_link_no": link_no,
            "parsed_lane_no": lane_no,
            "position_value": position,
            "speed_value": speed,
        })
    return sorted(rows, key=lambda item: item["no_value"])


def _select_capture_samples(
    rows: Sequence[Mapping[str, Any]],
    connector_lanes: set[tuple[int, int]],
    multilane_road_lanes: set[tuple[int, int]],
) -> list[dict[str, Any]]:
    selected: list[Mapping[str, Any]] = []
    used: set[int] = set()

    def add_first(predicate: Any) -> None:
        for row in rows:
            no_value = int(row["no_value"])
            if no_value not in used and predicate(row):
                selected.append(row)
                used.add(no_value)
                return

    add_first(lambda row: (int(row["parsed_link_no"]), int(row["parsed_lane_no"])) in connector_lanes)
    add_first(lambda row: (int(row["parsed_link_no"]), int(row["parsed_lane_no"])) in multilane_road_lanes)
    for row in rows:
        if len(selected) >= MAX_CAPTURE_SAMPLES:
            break
        no_value = int(row["no_value"])
        if no_value not in used:
            selected.append(row)
            used.add(no_value)
    return [dict(item) for item in sorted(selected, key=lambda item: int(item["no_value"]))]


def _canonical_count_map(value: Any, *, label: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"{label} missing")])
    result: dict[str, int] = {}
    for raw_key, raw_value in value.items():
        if (
            not isinstance(raw_key, str)
            or not raw_key
            or raw_key[0] == "0"
            or any(char < "0" or char > "9" for char in raw_key)
        ):
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"{label} invalid key")])
        key_int = int(raw_key)
        if key_int <= 0 or key_int > MAX_POSITIVE_INT32:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"{label} key out of range")])
        result[raw_key] = _bounded_json_int(raw_value, max_value=MAX_RAW_SAMPLE_ROWS)
    return result


def _state_records_by_no(
    state: Mapping[str, Any],
    *,
    expected_sim_sec: float | None = None,
) -> tuple[Mapping[str, Any], dict[int, Mapping[str, Any]], dict[str, int], dict[str, int], int]:
    envelope = state.get("vehicle_records")
    envelope = _exact_field_set(envelope, VEHICLE_RECORDS_FIELDS, "state vehicle_records")
    if envelope.get("schema_version") != "vissim-vehicle-records-v2.1" or envelope.get("complete") is not True:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "state vehicle_records header invalid")])
    if expected_sim_sec is not None:
        _json_double_equal(
            envelope.get("paused_at_sim_sec"),
            expected_sim_sec,
            label="state vehicle_records.paused_at_sim_sec",
        )
        _json_double_equal(
            envelope.get("capture_sim_sec_before"),
            expected_sim_sec,
            label="state vehicle_records.capture_sim_sec_before",
        )
        _json_double_equal(
            envelope.get("capture_sim_sec_after"),
            expected_sim_sec,
            label="state vehicle_records.capture_sim_sec_after",
        )
    source_attributes = _exact_field_set(
        envelope.get("source_attributes"),
        VEHICLE_RECORDS_SOURCE_ATTRIBUTES_FIELDS,
        "state vehicle_records.source_attributes",
    )
    if dict(source_attributes) != VEHICLE_RECORDS_SOURCE_ATTRIBUTES:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "state vehicle_records source attributes invalid")])
    _json_double_equal(
        envelope.get("stopped_threshold_kph"),
        1.0,
        label="state vehicle_records stopped threshold",
    )
    count_before = _bounded_json_int(envelope.get("collection_count_before"), max_value=MAX_RAW_SAMPLE_ROWS)
    count_after = _bounded_json_int(envelope.get("collection_count_after"), max_value=MAX_RAW_SAMPLE_ROWS)
    record_count = _bounded_json_int(envelope.get("record_count"), max_value=MAX_RAW_SAMPLE_ROWS)
    unobservable_count = _bounded_json_int(envelope.get("unobservable_count"), max_value=MAX_RAW_SAMPLE_ROWS)
    external_source_count = _bounded_json_int(envelope.get("external_source_count"), max_value=MAX_RAW_SAMPLE_ROWS)
    if (
        count_before != count_after
        or count_before != record_count
        or unobservable_count != 0
        or external_source_count != 0
    ):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "state vehicle_records scalar counts invalid")])
    declared_link_counts = _canonical_count_map(
        envelope.get("full_network_link_counts"),
        label="state vehicle_records.full_network_link_counts",
    )
    declared_stopped_counts = _canonical_count_map(
        envelope.get("full_network_link_stopped_counts"),
        label="state vehicle_records.full_network_link_stopped_counts",
    )
    records = envelope.get("records")
    if not isinstance(records, list):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "state records missing")])
    by_no: dict[int, Mapping[str, Any]] = {}
    derived_link_counts: dict[str, int] = {}
    derived_stopped_counts: dict[str, int] = {}
    stopped_total = 0
    for index, record in enumerate(records):
        if not isinstance(record, Mapping) or set(record.keys()) != set(STATE_RECORD_FIELDS):
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"state record[{index}] malformed")])
        try:
            veh_no = _bounded_json_int(record.get("veh_no"), positive=True, max_value=MAX_POSITIVE_INT32)
            link_no = _bounded_json_int(record.get("link_no"), positive=True, max_value=MAX_POSITIVE_INT32)
            lane_no = _bounded_json_int(record.get("lane_no"), positive=True, max_value=MAX_POSITIVE_INT32)
            position_m = _json_double(record.get("position_m"))
            speed_kph = _json_double(record.get("speed_kph"))
        except VehicleCaptureEvidenceError as exc:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"state record[{index}] invalid typed value")]) from exc
        if veh_no in by_no:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"state record[{index}] invalid veh_no")])
        if record.get("link_no") != link_no or record.get("lane_no") != lane_no:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"state record[{index}] invalid lane identity")])
        if position_m < -POSITION_TOLERANCE_M:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"state record[{index}] invalid position_m")])
        if speed_kph < 0.0:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"state record[{index}] invalid speed_kph")])
        is_stopped = speed_kph < 1.0
        if not isinstance(record.get("stopped"), bool) or record.get("stopped") != is_stopped:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"state record[{index}] stopped derivation mismatch")])
        by_no[veh_no] = record
        link_key = str(link_no)
        derived_link_counts[link_key] = derived_link_counts.get(link_key, 0) + 1
        derived_stopped_counts.setdefault(link_key, 0)
        if is_stopped:
            stopped_total += 1
            derived_stopped_counts[link_key] += 1
    derived_link_counts = {
        key: derived_link_counts[key]
        for key in sorted(derived_link_counts, key=lambda item: int(item))
    }
    derived_stopped_counts = {
        key: derived_stopped_counts[key]
        for key in sorted(derived_stopped_counts, key=lambda item: int(item))
    }
    if record_count != len(records) or record_count != len(by_no):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "state vehicle_records record count invalid")])
    if declared_link_counts != derived_link_counts:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "state full_network_link_counts disagree with records")])
    if declared_stopped_counts != derived_stopped_counts:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "state full_network_link_stopped_counts disagree with records")])
    if _bounded_json_int(state.get("total_vehicles"), max_value=MAX_RAW_SAMPLE_ROWS) != record_count:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "state root total_vehicles disagrees with records")])
    if _bounded_json_int(state.get("stopped_vehicles"), max_value=MAX_RAW_SAMPLE_ROWS) != stopped_total:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "state root stopped_vehicles disagrees with records")])
    return envelope, by_no, derived_link_counts, derived_stopped_counts, stopped_total


def build_vehicle_capture_evidence(
    *,
    workspace_root: Path,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    root = workspace_root.resolve(strict=True)
    manifest_rel = request.get("run_manifest_path")
    state_rel = request.get("state_path")
    if not isinstance(manifest_rel, str) or not isinstance(state_rel, str):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "request path fields are invalid")])
    manifest_path = resolve_contained_path(root, manifest_rel)
    state_path = resolve_contained_path(root, state_rel)
    manifest = strict_load_json(manifest_path, max_bytes=MAX_RUN_MANIFEST_BYTES)
    manifest_hash = file_sha256(manifest_path)
    run_id = request.get("run_id")
    sim_sec = _json_double(request.get("sim_sec"))
    if not isinstance(run_id, str):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "request run_id invalid")])
    if request.get("run_manifest_sha256") != manifest_hash:
        raise VehicleCaptureEvidenceError([_reason("run_attempt_mismatch", "run manifest hash mismatch")])
    try:
        validated = validate_run_manifest(
            manifest,
            workspace_root=root,
            expected_run_id=run_id,
            capture_time=sim_sec,
        )
    except RunManifestValidationError as exc:
        raise VehicleCaptureEvidenceError([_reason("run_attempt_mismatch", list(exc.issues))]) from exc
    if request.get("qualification") != validated.artifact["qualification"]:
        raise VehicleCaptureEvidenceError([_reason("qualification_mismatch", "qualification does not copy manifest")])
    state = _strict_load_json_no_bom(state_path, max_bytes=MAX_STATE_BYTES)
    state_issues = validate_state_run_binding(
        state,
        workspace_root=root,
        state_path=state_path,
        run_manifest_path=manifest_path,
        run_manifest_sha256=manifest_hash,
        run_id=run_id,
        sim_sec=sim_sec,
        require_vehicle_records=True,
    )
    if state_issues:
        raise VehicleCaptureEvidenceError([_reason("run_attempt_mismatch", state_issues)])
    envelope, records_by_no, _, _, _ = _state_records_by_no(state, expected_sim_sec=sim_sec)
    counts = _exact_capture_fields(request.get("counts"), CAPTURE_COUNTS_FIELDS, "counts")
    count_before = _bounded_json_int(counts.get("collection_count_before"), max_value=MAX_RAW_SAMPLE_ROWS)
    count_after = _bounded_json_int(counts.get("collection_count_after"), max_value=MAX_RAW_SAMPLE_ROWS)
    record_count = _bounded_json_int(counts.get("record_count"), max_value=MAX_RAW_SAMPLE_ROWS)
    if count_before != count_after or count_before != record_count or record_count != len(records_by_no):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "capture counts disagree")])
    for field in CAPTURE_COUNTS_FIELDS:
        if envelope.get(field) != counts.get(field):
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", f"state/counts mismatch for {field}")])

    timer = _exact_capture_fields(request.get("capture_timer"), CAPTURE_TIMER_FIELDS, "capture_timer")
    if timer.get("clock") != MONOTONIC_CLOCK:
        raise VehicleCaptureEvidenceError([_reason("timing_receipt_invalid", "clock mismatch")])
    start_ns = _bounded_json_int(
        timer.get("start_ns"),
        positive=True,
        max_value=MAX_POSITIVE_INT64,
        reason_code="timing_receipt_invalid",
    )
    end_ns = _bounded_json_int(
        timer.get("end_ns"),
        positive=True,
        max_value=MAX_POSITIVE_INT64,
        reason_code="timing_receipt_invalid",
    )
    if end_ns <= start_ns:
        raise VehicleCaptureEvidenceError([_reason("timing_receipt_invalid", "non-increasing endpoints")])
    elapsed = (end_ns - start_ns) / 1_000_000_000.0

    version_raw = request.get("vissim_version_raw")
    if not isinstance(version_raw, str) or not version_raw or len(version_raw) > 256:
        raise VehicleCaptureEvidenceError([_reason("unsupported_vissim_version", "raw version string is invalid")])
    topology_path = resolve_contained_path(root, validated.artifact["approved_topology"]["topology_path"])
    topology = strict_load_json(topology_path)
    known_lanes, connector_lanes, multilane_lanes = _topology_lane_sets(topology)
    rows = _normalize_raw_rows(request.get("raw_attribute_rows"), records_by_no, known_lanes)
    samples = _select_capture_samples(rows, connector_lanes, multilane_lanes)
    evidence: dict[str, Any] = {
        "schema_version": CAPTURE_SCHEMA_VERSION,
        "run_id": run_id,
        "sim_sec": sim_sec,
        "qualification": dict(validated.artifact["qualification"]),
        "run_manifest_path": workspace_relative_path(root, manifest_path),
        "run_manifest_sha256": manifest_hash,
        "state_path": workspace_relative_path(root, state_path),
        "vissim_version_raw": version_raw,
        "counts": {
            "collection_count_before": count_before,
            "collection_count_after": count_after,
            "record_count": record_count,
        },
        "capture_timer": {
            "clock": MONOTONIC_CLOCK,
            "start_ns": start_ns,
            "end_ns": end_ns,
            "elapsed_sec": elapsed,
        },
        "raw_attribute_samples": samples,
    }
    evidence["semantic_sha256"] = canonical_json_sha256(capture_evidence_semantic_payload(evidence))
    return evidence


def validate_vehicle_capture_evidence(
    evidence: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    root = workspace_root.resolve(strict=True)
    record = _exact_capture_fields(evidence, CAPTURE_FIELDS, "vehicle capture evidence")
    if record.get("schema_version") != CAPTURE_SCHEMA_VERSION:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "capture schema mismatch")])
    manifest_path = resolve_contained_path(root, record.get("run_manifest_path", ""))
    state_path = resolve_contained_path(root, record.get("state_path", ""))
    manifest_hash = file_sha256(manifest_path)
    if record.get("run_manifest_sha256") != manifest_hash:
        raise VehicleCaptureEvidenceError([_reason("run_attempt_mismatch", "run manifest hash mismatch")])
    sim_sec = _json_double(record.get("sim_sec"))
    run_id = record.get("run_id")
    if not isinstance(run_id, str):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "run_id invalid")])
    manifest = strict_load_json(manifest_path, max_bytes=MAX_RUN_MANIFEST_BYTES)
    try:
        validated = validate_run_manifest(
            manifest,
            workspace_root=root,
            expected_run_id=run_id,
            capture_time=sim_sec,
        )
    except RunManifestValidationError as exc:
        raise VehicleCaptureEvidenceError([_reason("run_attempt_mismatch", list(exc.issues))]) from exc
    if record.get("qualification") != validated.artifact["qualification"]:
        raise VehicleCaptureEvidenceError([_reason("qualification_mismatch", "qualification mismatch")])
    state = _strict_load_json_no_bom(state_path, max_bytes=MAX_STATE_BYTES)
    state_issues = validate_state_run_binding(
        state,
        workspace_root=root,
        state_path=state_path,
        run_manifest_path=manifest_path,
        run_manifest_sha256=manifest_hash,
        run_id=run_id,
        sim_sec=sim_sec,
        require_vehicle_records=True,
    )
    if state_issues:
        raise VehicleCaptureEvidenceError([_reason("run_attempt_mismatch", state_issues)])
    envelope, records_by_no, _, _, _ = _state_records_by_no(state, expected_sim_sec=sim_sec)
    counts = _exact_capture_fields(record.get("counts"), CAPTURE_COUNTS_FIELDS, "counts")
    count_before = _bounded_json_int(counts.get("collection_count_before"), max_value=MAX_RAW_SAMPLE_ROWS)
    count_after = _bounded_json_int(counts.get("collection_count_after"), max_value=MAX_RAW_SAMPLE_ROWS)
    record_count = _bounded_json_int(counts.get("record_count"), max_value=MAX_RAW_SAMPLE_ROWS)
    if any(envelope.get(field) != counts.get(field) for field in CAPTURE_COUNTS_FIELDS):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "state/counts mismatch")])
    if count_before != count_after or count_before != record_count or len(records_by_no) != record_count:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "record count mismatch")])
    timer = _exact_capture_fields(record.get("capture_timer"), CAPTURE_TIMER_FIELDS, "capture_timer")
    if timer.get("clock") != MONOTONIC_CLOCK:
        raise VehicleCaptureEvidenceError([_reason("timing_receipt_invalid", "clock mismatch")])
    start_ns = _bounded_json_int(
        timer.get("start_ns"),
        positive=True,
        max_value=MAX_POSITIVE_INT64,
        reason_code="timing_receipt_invalid",
    )
    end_ns = _bounded_json_int(
        timer.get("end_ns"),
        positive=True,
        max_value=MAX_POSITIVE_INT64,
        reason_code="timing_receipt_invalid",
    )
    if end_ns <= start_ns or timer.get("elapsed_sec") != (end_ns - start_ns) / 1_000_000_000.0:
        raise VehicleCaptureEvidenceError([_reason("timing_receipt_invalid", "timer arithmetic mismatch")])
    if not isinstance(record.get("vissim_version_raw"), str) or not record.get("vissim_version_raw"):
        raise VehicleCaptureEvidenceError([_reason("unsupported_vissim_version", "raw version missing")])
    topology = strict_load_json(resolve_contained_path(root, validated.artifact["approved_topology"]["topology_path"]))
    known_lanes, _, _ = _topology_lane_sets(topology)
    samples = _normalize_raw_rows(record.get("raw_attribute_samples"), records_by_no, known_lanes)
    if samples != list(record.get("raw_attribute_samples", [])):
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "sample rows are not canonical")])
    semantic = canonical_json_sha256(capture_evidence_semantic_payload(record))
    if record.get("semantic_sha256") != semantic:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "semantic hash mismatch")])
    return dict(record)


def publish_vehicle_capture_evidence_create_once(
    *,
    workspace_root: Path,
    request: Mapping[str, Any],
    output_path: Path,
    validate_only: bool = False,
) -> dict[str, Any]:
    root = workspace_root.resolve(strict=True)
    target = output_path if output_path.is_absolute() else root / output_path
    target = target.resolve(strict=False)
    target.relative_to(root)
    evidence = build_vehicle_capture_evidence(workspace_root=root, request=request)
    payload = capture_evidence_json_bytes(evidence)
    if len(payload) > MAX_CAPTURE_EVIDENCE_BYTES:
        raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "capture evidence exceeds size limit")])
    if validate_only:
        if read_bounded_bytes(target, MAX_CAPTURE_EVIDENCE_BYTES) != payload:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "existing capture evidence bytes differ")])
        validate_vehicle_capture_evidence(
            _strict_load_json_no_bom(target, max_bytes=MAX_CAPTURE_EVIDENCE_BYTES),
            workspace_root=root,
        )
        return evidence
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary_name, target)
        except FileExistsError as exc:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "capture evidence already exists")]) from exc
        final = read_bounded_bytes(target, MAX_CAPTURE_EVIDENCE_BYTES)
        if final != payload:
            raise VehicleCaptureEvidenceError([_reason("aggregate_mismatch", "published capture evidence bytes differ")])
        validate_vehicle_capture_evidence(
            _strict_load_json_no_bom(target, max_bytes=MAX_CAPTURE_EVIDENCE_BYTES),
            workspace_root=root,
        )
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return evidence


def _entry_sort_key(entry: Mapping[str, Any]) -> tuple[str, tuple[int, Any], str]:
    sim_sec = entry.get("sim_sec", -1.0)
    numeric = isinstance(sim_sec, (int, float)) and not isinstance(sim_sec, bool)
    return (
        str(entry.get("run_id", "")),
        (0, sim_sec) if numeric else (1, str(sim_sec)),
        str(entry.get("state_path", "")),
    )


def selection_semantic_payload(selection: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: selection[key]
        for key in (
            "schema_version",
            "input_hashes",
            "command_version",
            "sample_dimensions",
            "units",
            "downstream_consumers",
            "campaign_id",
            "expected_entry_count",
            "entries",
        )
    }


def state_set_semantic_payload(states: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "state_path",
        "state_file_sha256",
        "run_id",
        "sim_sec",
        "run_manifest_path",
        "run_manifest_sha256",
        "required_vehicle_records",
        "projection_sidecar_path",
    )
    return [
        {field: entry[field] for field in fields}
        for entry in sorted(states, key=_entry_sort_key)
    ]


def manifest_semantic_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: manifest[key]
        for key in (
            "schema_version",
            "input_hashes",
            "command_version",
            "sample_dimensions",
            "units",
            "downstream_consumers",
            "base_dir",
            "state_selection",
            "approved_topology",
            "states",
        )
    }


def validate_state_selection(
    selection: Mapping[str, Any],
    *,
    workspace_root: Path | None = None,
) -> tuple[dict[str, Any], ...]:
    issues: list[str] = []
    if not isinstance(selection, Mapping):
        raise StateManifestValidationError([_reason("aggregate_mismatch", "selection is not an object")])
    if set(selection) != SELECTION_FIELDS:
        issues.append("selection shape mismatch")
    if selection.get("schema_version") != SELECTION_SCHEMA_VERSION:
        issues.append("selection schema mismatch")
    if selection.get("status") != "PASS" or selection.get("reasons") != []:
        issues.append("selection status/reasons mismatch")
    if not isinstance(selection.get("input_hashes"), dict) or any(
        SHA256_PATTERN.fullmatch(str(value)) is None
        for value in selection.get("input_hashes", {}).values()
    ):
        issues.append("selection input_hashes malformed")
    if not isinstance(selection.get("command_version"), dict):
        issues.append("selection command_version malformed")
    if selection.get("units") != SELECTION_UNITS:
        issues.append("selection units mismatch")
    if selection.get("downstream_consumers") != SELECTION_DOWNSTREAM_CONSUMERS:
        issues.append("selection downstream_consumers mismatch")
    campaign_id = selection.get("campaign_id")
    if not isinstance(campaign_id, str) or not campaign_id.strip() or len(campaign_id) > 128:
        issues.append("invalid campaign_id")
    expected_count = selection.get("expected_entry_count")
    if not isinstance(expected_count, int) or isinstance(expected_count, bool) or expected_count < 0:
        issues.append("invalid expected_entry_count")
        expected_count = -1
    entries = selection.get("entries")
    if not isinstance(entries, list):
        issues.append("entries must be an array")
        entries = []
    normalized: list[dict[str, Any]] = []
    resolved_states: set[Path] = set()
    identities: set[tuple[str, float]] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != SELECTION_ENTRY_FIELDS:
            issues.append(f"entry[{index}] shape mismatch")
            continue
        run_id = entry.get("run_id")
        sim_sec = entry.get("sim_sec")
        if not isinstance(run_id, str) or RUN_ID_PATTERN.fullmatch(run_id) is None:
            issues.append(f"entry[{index}] invalid run_id")
            continue
        if not _finite_nonnegative(sim_sec):
            issues.append(f"entry[{index}] invalid sim_sec")
            continue
        if not isinstance(entry.get("required_vehicle_records"), bool):
            issues.append(f"entry[{index}] invalid required_vehicle_records")
            continue
        for field in ("state_path", "run_manifest_path"):
            value = entry.get(field)
            if not isinstance(value, str) or not value:
                issues.append(f"entry[{index}] invalid {field}")
        normalized_entry = {
            "run_manifest_path": str(entry.get("run_manifest_path", "")),
            "state_path": str(entry.get("state_path", "")),
            "run_id": run_id,
            "sim_sec": float(sim_sec),
            "required_vehicle_records": entry["required_vehicle_records"],
        }
        identity = (run_id, float(sim_sec))
        if identity in identities:
            issues.append(f"duplicate run/time identity {identity}")
        identities.add(identity)
        if workspace_root is not None:
            for field in ("state_path", "run_manifest_path"):
                try:
                    resolved = resolve_contained_path(workspace_root, normalized_entry[field])
                except (OSError, ValueError) as exc:
                    issues.append(f"entry[{index}] {field}: {exc}")
                    continue
                if field == "state_path":
                    if resolved in resolved_states:
                        issues.append(f"duplicate resolved state path {resolved}")
                    resolved_states.add(resolved)
        normalized.append(normalized_entry)
    if len(entries) != expected_count:
        issues.append("selection length does not equal expected_entry_count")
    if selection.get("sample_dimensions") != {"entries": len(entries)}:
        issues.append("selection sample_dimensions mismatch")
    if normalized != sorted(normalized, key=_entry_sort_key) or entries != normalized:
        issues.append("selection entries are not canonical")
    try:
        semantic = canonical_json_sha256(selection_semantic_payload(selection))
    except (KeyError, TypeError, ValueError) as exc:
        issues.append(f"invalid selection semantic payload: {exc}")
        semantic = ""
    if selection.get("semantic_sha256") != semantic:
        issues.append("selection semantic hash mismatch")
    if issues:
        raise StateManifestValidationError([_reason("aggregate_mismatch", sorted(set(issues)))])
    return tuple(normalized)


def expected_approved_topology_binding(
    bundle: ValidatedApprovalBundle,
) -> dict[str, str]:
    return {
        "approving_manifest_path": workspace_relative_path(
            bundle.workspace_root, bundle.approval_path
        ),
        "approving_manifest_sha256": bundle.approval_file_sha256,
        "topology_path": workspace_relative_path(
            bundle.workspace_root, bundle.topology_path
        ),
        "topology_file_sha256": file_sha256(bundle.topology_path),
        "topology_semantic_sha256": bundle.validated_topology.semantic_sha256,
    }


def validate_state_run_binding(
    state: Mapping[str, Any],
    *,
    workspace_root: Path,
    state_path: Path,
    run_manifest_path: Path,
    run_manifest_sha256: str,
    run_id: str,
    sim_sec: float,
    require_vehicle_records: bool = False,
) -> list[str]:
    issues: list[str] = []
    if not isinstance(state, Mapping):
        return ["state root is not an object"]
    try:
        _json_double_equal(state.get("sim_sec"), sim_sec, label="state root sim_sec")
    except VehicleCaptureEvidenceError:
        issues.append("state root sim_sec mismatch")
    provenance = state.get("run_provenance")
    if not isinstance(provenance, dict):
        return [*issues, "missing state run_provenance"]
    if provenance.get("run_id") != run_id:
        issues.append("state run_provenance.run_id mismatch")
    if provenance.get("manifest_sha256") != run_manifest_sha256:
        issues.append("state run_provenance.manifest_sha256 mismatch")
    declared_manifest = provenance.get("manifest_path")
    if not isinstance(declared_manifest, str) or not declared_manifest:
        issues.append("missing state run_provenance.manifest_path")
    else:
        try:
            resolved = resolve_contained_path(
                workspace_root, declared_manifest, allow_absolute=True
            )
            if resolved != run_manifest_path:
                issues.append("state run_provenance.manifest_path mismatch")
        except (OSError, ValueError) as exc:
            issues.append(f"state run_provenance.manifest_path: {exc}")
    if require_vehicle_records:
        try:
            _state_records_by_no(state, expected_sim_sec=sim_sec)
        except VehicleCaptureEvidenceError as exc:
            detail = _exception_detail(exc)
            issues.append(f"state vehicle_records invalid: {detail}")
    return issues


def build_manifest_artifact(
    *,
    workspace_root: Path,
    output_path: Path,
    bundle: ValidatedApprovalBundle,
    selection_path: Path,
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    if output_path.parent.parent.resolve(strict=True) != workspace_root:
        raise StateManifestValidationError([
            _reason("topology_trust_mismatch", "base_dir '..' does not resolve to workspace root")
        ])
    selected_entries = validate_state_selection(selection, workspace_root=workspace_root)
    approved_topology = expected_approved_topology_binding(bundle)
    states: list[dict[str, Any]] = []
    issues: list[str] = []
    immutable_runs: dict[str, tuple[Path, str]] = {}
    for entry in selected_entries:
        try:
            state_path = resolve_contained_path(workspace_root, entry["state_path"])
            run_manifest_path = resolve_contained_path(
                workspace_root, entry["run_manifest_path"]
            )
            state = strict_load_json(state_path)
            run_manifest = strict_load_json(
                run_manifest_path, max_bytes=MAX_RUN_MANIFEST_BYTES
            )
            state_hash = file_sha256(state_path)
            run_manifest_hash = file_sha256(run_manifest_path)
        except (OSError, ValueError) as exc:
            issues.append(f"{entry['state_path']}: {exc}")
            continue
        prior_run = immutable_runs.get(entry["run_id"])
        current_run = (run_manifest_path, run_manifest_hash)
        if prior_run is not None and prior_run != current_run:
            issues.append(
                f"{entry['state_path']}: run_id binds more than one immutable run manifest"
            )
        immutable_runs[entry["run_id"]] = current_run
        try:
            validate_run_manifest(
                run_manifest,
                workspace_root=workspace_root,
                expected_run_id=entry["run_id"],
                capture_time=entry["sim_sec"],
                expected_approved_topology=approved_topology,
            )
        except RunManifestValidationError as exc:
            issues.extend(
                f"{entry['state_path']}: {issue}" for issue in exc.issues
            )
        issues.extend(
            f"{entry['state_path']}: {issue}"
            for issue in validate_state_run_binding(
                state,
                workspace_root=workspace_root,
                state_path=state_path,
                run_manifest_path=run_manifest_path,
                run_manifest_sha256=run_manifest_hash,
                run_id=entry["run_id"],
                sim_sec=entry["sim_sec"],
                require_vehicle_records=entry["required_vehicle_records"],
            )
        )
        states.append({
            "state_path": workspace_relative_path(workspace_root, state_path),
            "state_file_sha256": state_hash,
            "run_id": entry["run_id"],
            "sim_sec": entry["sim_sec"],
            "run_manifest_path": workspace_relative_path(workspace_root, run_manifest_path),
            "run_manifest_sha256": run_manifest_hash,
            "required_vehicle_records": entry["required_vehicle_records"],
            "projection_sidecar_path": workspace_relative_path(
                workspace_root, projection_sidecar_path(state_path)
            ),
        })
    if len(states) != len(selected_entries):
        issues.append("one or more selected entries could not be materialized")
    states.sort(key=_entry_sort_key)
    if issues:
        raise StateManifestValidationError([_reason("aggregate_mismatch", sorted(set(issues)))])

    state_set_hash = canonical_json_sha256(state_set_semantic_payload(states))
    selection_file_hash = file_sha256(selection_path)
    input_hashes = {
        "approving_manifest_sha256": bundle.approval_file_sha256,
        "state_selection_file_sha256": selection_file_hash,
        "state_selection_semantic_sha256": str(selection["semantic_sha256"]),
        "topology_file_sha256": file_sha256(bundle.topology_path),
        "topology_semantic_sha256": bundle.validated_topology.semantic_sha256,
        "state_set_semantic_sha256": state_set_hash,
    }
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "input_hashes": input_hashes,
        "command_version": {},
        "status": "PASS",
        "reasons": [],
        "sample_dimensions": {"states": len(states)},
        "units": dict(UNITS),
        "downstream_consumers": list(DOWNSTREAM_CONSUMERS),
        "base_dir": "..",
        "state_selection": {
            "path": workspace_relative_path(workspace_root, selection_path),
            "file_sha256": selection_file_hash,
            "semantic_sha256": selection["semantic_sha256"],
            "campaign_id": selection["campaign_id"],
            "expected_entry_count": selection["expected_entry_count"],
        },
        "approved_topology": approved_topology,
        "states": states,
    }
    manifest["semantic_sha256"] = canonical_json_sha256(manifest_semantic_payload(manifest))
    return manifest


def failed_manifest(reason: Mapping[str, Any]) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "input_hashes": {key: "" for key in sorted(MANIFEST_INPUT_HASH_NAMES)},
        "command_version": {},
        "status": "FAIL",
        "reasons": [dict(reason)],
        "sample_dimensions": {"states": 0},
        "units": dict(UNITS),
        "downstream_consumers": list(DOWNSTREAM_CONSUMERS),
        "base_dir": "..",
        "state_selection": {
            "path": "",
            "file_sha256": "",
            "semantic_sha256": "",
            "campaign_id": "",
            "expected_entry_count": 0,
        },
        "approved_topology": {
            "approving_manifest_path": "",
            "approving_manifest_sha256": "",
            "topology_path": "",
            "topology_file_sha256": "",
            "topology_semantic_sha256": "",
        },
        "states": [],
    }
    manifest["semantic_sha256"] = canonical_json_sha256(manifest_semantic_payload(manifest))
    return manifest


def _resolve_cli_input(root: Path, value: Path) -> Path:
    candidate = value if value.is_absolute() else root / value
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    return resolved


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--topology", type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--validate-run-binding", action="store_true")
    parser.add_argument("--validate-state-run-binding", action="store_true")
    parser.add_argument("--run-manifest", type=Path)
    parser.add_argument("--run-manifest-sha256")
    parser.add_argument("--run-id")
    parser.add_argument("--qualification-mode")
    parser.add_argument("--capture-time", type=float)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--produce-vehicle-capture", action="store_true")
    parser.add_argument("--validate-vehicle-capture", action="store_true")
    parser.add_argument("--vehicle-capture-request", type=Path)
    parser.add_argument("--vehicle-capture", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.workspace_root.resolve(strict=True)
        if args.validate_run_binding:
            if args.run_manifest is None or not args.run_manifest_sha256 or not args.run_id:
                raise ValueError("missing run binding arguments")
            manifest_path = args.run_manifest if args.run_manifest.is_absolute() else root / args.run_manifest
            manifest_path = manifest_path.resolve(strict=True)
            manifest_path.relative_to(root)
            manifest_hash = file_sha256(manifest_path)
            if manifest_hash != args.run_manifest_sha256:
                raise ValueError("run manifest hash mismatch")
            manifest = strict_load_json(manifest_path, max_bytes=MAX_RUN_MANIFEST_BYTES)
            validated = validate_run_manifest(
                manifest,
                workspace_root=root,
                expected_run_id=args.run_id,
                capture_time=args.capture_time,
            )
            if args.qualification_mode is not None and validated.qualification_mode != args.qualification_mode:
                raise ValueError("qualification mode mismatch")
            print(
                "status=PASS run_id="
                + args.run_id
                + " manifest_path="
                + workspace_relative_path(root, manifest_path)
            )
            return 0
        if args.validate_state_run_binding:
            if (
                args.run_manifest is None
                or args.state is None
                or not args.run_manifest_sha256
                or not args.run_id
                or args.capture_time is None
            ):
                raise ValueError("missing state run binding arguments")
            manifest_path = args.run_manifest if args.run_manifest.is_absolute() else root / args.run_manifest
            manifest_path = manifest_path.resolve(strict=True)
            manifest_path.relative_to(root)
            state_path = args.state if args.state.is_absolute() else root / args.state
            state_path = state_path.resolve(strict=True)
            state_path.relative_to(root)
            manifest_hash = file_sha256(manifest_path)
            if manifest_hash != args.run_manifest_sha256:
                raise ValueError("run manifest hash mismatch")
            manifest = strict_load_json(manifest_path, max_bytes=MAX_RUN_MANIFEST_BYTES)
            validated = validate_run_manifest(
                manifest,
                workspace_root=root,
                expected_run_id=args.run_id,
                capture_time=args.capture_time,
            )
            if args.qualification_mode is not None and validated.qualification_mode != args.qualification_mode:
                raise ValueError("qualification mode mismatch")
            state = _strict_load_json_no_bom(state_path, max_bytes=MAX_STATE_BYTES)
            issues = validate_state_run_binding(
                state,
                workspace_root=root,
                state_path=state_path,
                run_manifest_path=manifest_path,
                run_manifest_sha256=manifest_hash,
                run_id=args.run_id,
                sim_sec=float(args.capture_time),
                require_vehicle_records=True,
            )
            if issues:
                raise ValueError("state run binding mismatch: " + "; ".join(issues))
            print(
                "status=PASS state="
                + workspace_relative_path(root, state_path)
                + " sha256="
                + file_sha256(state_path)
            )
            return 0
        if args.produce_vehicle_capture or args.validate_vehicle_capture:
            if args.vehicle_capture is None:
                raise ValueError("missing vehicle capture output")
            output = args.vehicle_capture if args.vehicle_capture.is_absolute() else root / args.vehicle_capture
            output = output.resolve(strict=False)
            output.relative_to(root)
            if args.validate_vehicle_capture:
                validate_vehicle_capture_evidence(
                    _strict_load_json_no_bom(output, max_bytes=MAX_CAPTURE_EVIDENCE_BYTES),
                    workspace_root=root,
                )
                print("status=PASS vehicle_capture=" + workspace_relative_path(root, output))
                return 0
            if args.vehicle_capture_request is None:
                raise ValueError("missing vehicle capture request")
            request_path = args.vehicle_capture_request if args.vehicle_capture_request.is_absolute() else root / args.vehicle_capture_request
            request_path = request_path.resolve(strict=True)
            request_path.relative_to(root)
            request = _strict_load_json_no_bom(request_path, max_bytes=MAX_CAPTURE_REQUEST_BYTES)
            if not isinstance(request, Mapping):
                raise ValueError("vehicle capture request must be an object")
            publish_vehicle_capture_evidence_create_once(
                workspace_root=root,
                request=request,
                output_path=output,
                validate_only=args.validate_only,
            )
            print("status=PASS vehicle_capture=" + workspace_relative_path(root, output))
            return 0
        if args.approval is None or args.topology is None or args.selection is None or args.out is None:
            raise ValueError("missing state manifest arguments")
        output = args.out if args.out.is_absolute() else root / args.out
        output = output.resolve(strict=False)
        output.relative_to(root)
        if output.parent.parent.resolve(strict=True) != root:
            raise ValueError("manifest output must be in an immediate child of workspace root")
    except FAIL_CLOSED_INPUT_EXCEPTIONS:
        return 1

    try:
        approval_path = _resolve_cli_input(root, args.approval)
        topology_path = _resolve_cli_input(root, args.topology)
        selection_path = _resolve_cli_input(root, args.selection)
        bundle = validate_approval_artifact(
            approval_path,
            workspace_root=root,
            supplied_topology_path=topology_path,
        )
        selection = strict_load_json(selection_path)
        artifact = build_manifest_artifact(
            workspace_root=root,
            output_path=output,
            bundle=bundle,
            selection_path=selection_path,
            selection=selection,
        )
    except FAIL_CLOSED_INPUT_EXCEPTIONS as exc:
        artifact = failed_manifest(_reason("aggregate_mismatch", _exception_detail(exc)))
    try:
        atomic_write_json(output, artifact)
    except OSError:
        return 1
    print(f"status={artifact['status']} states={artifact['sample_dimensions']['states']}")
    return 0 if artifact["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
