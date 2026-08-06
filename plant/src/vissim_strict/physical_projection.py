"""Verified physical-stock topology indexing and per-vehicle state projection."""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .topology import canonical_json_sha256, canonical_json_text


TOPOLOGY_SCHEMA_VERSION = "physical-stock-topology-v2.1"
CANONICAL_JSON_VERSION = "canonical-json/v1"
VEHICLE_RECORDS_SCHEMA_VERSION = "vissim-vehicle-records-v2.1"
PROJECTION_SCHEMA_VERSION = "projection-v2.1"
POSITION_TOLERANCE_M = 1.0e-6
WEIGHT_TOLERANCE = 1.0e-9
MAX_VISSIM_ID = 2_147_483_647
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

TOPOLOGY_UNITS = {
    "position": "m",
    "interval": "half-open [start_m,end_m), with the final endpoint equal to lane length",
    "length": "m",
    "capacity": "veh",
    "jam_density": "veh/km/lane",
    "owner_weight": "fraction",
    "objective_weight": "binary dimensionless weight",
}
TOPOLOGY_DOWNSTREAM_CONSUMERS = [
    "rollout plant state projection",
    "rollout plant physical flow trace",
    "controller visibility masks",
    "named objective views",
]
OBJECTIVE_MODES = (
    "physical_total",
    "controller_default",
    "controller_with_boundary",
    "boundary_only",
)
OBJECTIVE_POLICIES = {
    "physical_total": "include every in-network physical stock",
    "controller_default": "exclude exactly stocks carrying the boundary_out role",
    "controller_with_boundary": "include every in-network physical stock",
    "boundary_only": "include exactly stocks carrying the boundary_out role",
}
ALLOWED_STOCK_ROLES = {
    "boundary_out",
    "connector",
    "freeway",
    "interface",
    "ramp",
    "urban",
}
PROJECTION_HASH_NAMES = (
    "topology_file_sha256",
    "topology_semantic_sha256",
    "approving_manifest_sha256",
    "state_file_sha256",
    "vehicle_records_semantic_sha256",
)
PROJECTION_COMMAND_VERSION = {
    "command": "vissim_strict.physical_projection.project_vehicle_records",
    "version": "projection-v2.1",
}
PROJECTION_UNITS = {
    "position": "m",
    "speed": "km/h",
    "sim_sec": "s",
    "vehicle_count": "veh",
}
PROJECTION_DOWNSTREAM_CONSUMERS = [
    "online adapter physical_stock_projection reference",
    "validate_state_projection_v2_1",
]

_GLOBAL_ARTIFACT_FIELDS = {
    "schema_version",
    "input_hashes",
    "command_version",
    "status",
    "reasons",
    "sample_dimensions",
    "units",
    "downstream_consumers",
}
_TOPOLOGY_FIELDS = {
    "schema_version",
    "canonical_json_version",
    "input_hashes",
    "command_version",
    "source_artifacts",
    "command",
    "status",
    "reasons",
    "units",
    "downstream_consumers",
    "policies",
    "legacy_partition",
    "capacity_evidence",
    "sample_dimensions",
    "production_gates",
    "stocks",
    "stock_edges",
    "semantic_sha256",
}
_TOPOLOGY_SEMANTIC_INPUT_HASHES = {
    "lane_graph_semantic_sha256",
    "lane_route_proofs_semantic_sha256",
    "ownership_evidence_semantic_sha256",
    "adjacency_evidence_semantic_sha256",
    "capacity_evidence_semantic_sha256",
    "legacy_partition_identity_sha256",
}
_TOPOLOGY_RAW_INPUT_HASHES = {
    "lane_graph_sha256",
    "lane_route_proofs_sha256",
    "link_assignment_sha256",
    "adjacency_sha256",
    "storage_capacity_sha256",
}
_TOPOLOGY_COMMAND_FIELDS = {
    "version",
    "source_sha256",
    "command_hash",
    "semantic_hash_scope",
}
_TOPOLOGY_COMMAND_VERSION_FIELDS = {"command", "version", "sha256"}
_ROUTE_MEMBERSHIP_FIELDS = {
    "proof_id",
    "route_id",
    "decision_no",
    "route_no",
    "path_index",
    "segment_index",
    "overlap_start_m",
    "overlap_end_m",
    "flow_path_shares",
}
_VEHICLE_ENVELOPE_FIELDS = {
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
}
_VEHICLE_RECORD_FIELDS = {
    "veh_no",
    "link_no",
    "lane_no",
    "position_m",
    "speed_kph",
    "stopped",
}
_SOURCE_ATTRIBUTES = {
    "vehicle_number": "No",
    "lane": "Lane",
    "position": "Pos",
    "speed": "Speed",
}


def _reason(code: str, detail: Any) -> dict[str, Any]:
    return {"code": code, "detail": detail}


class StrictJsonError(ValueError):
    """Raised when JSON is nonstandard or contains duplicate object keys."""


class TopologyValidationError(ValueError):
    """Raised when an A2 topology fails trust or independent structure checks."""

    def __init__(self, reasons: Sequence[Mapping[str, Any]]) -> None:
        self.reasons = tuple(dict(item) for item in reasons)
        super().__init__("; ".join(str(item.get("code", "")) for item in self.reasons))


class ProjectionError(ValueError):
    """Typed fail-closed projection error carrying closed reason evidence."""

    def __init__(
        self,
        reasons: Sequence[Mapping[str, Any]],
        diagnostics: Mapping[str, Any] | None = None,
    ) -> None:
        self.reasons = tuple(dict(item) for item in reasons)
        self.diagnostics = dict(diagnostics or {})
        super().__init__("; ".join(str(item.get("code", "")) for item in self.reasons))


@dataclass(frozen=True)
class StockInterval:
    stock_id: str
    link_no: int
    lane_no: int
    start_m: float
    end_m: float


@dataclass(frozen=True)
class LaneIntervals:
    link_no: int
    lane_no: int
    lane_end_m: float
    starts_m: tuple[float, ...]
    intervals: tuple[StockInterval, ...]

    def locate(self, position_m: float, tolerance_m: float) -> tuple[StockInterval, float, str, str]:
        if not math.isfinite(position_m):
            raise ProjectionError([_reason("invalid_numeric_value", "nonfinite position_m")])
        if position_m < -tolerance_m or position_m > self.lane_end_m + tolerance_m:
            raise ProjectionError(
                [_reason("position_out_of_range", {
                    "link_no": self.link_no,
                    "lane_no": self.lane_no,
                    "position_m": position_m,
                    "lane_end_m": self.lane_end_m,
                })]
            )
        lookup_position = position_m
        assignment_status = "exact_interval"
        detail = "position used without tolerance snapping"
        if position_m < 0.0:
            lookup_position = 0.0
            assignment_status = "outer_endpoint_tolerance_snap"
            detail = "position snapped to lane start"
        elif position_m > self.lane_end_m:
            lookup_position = self.lane_end_m
            assignment_status = "outer_endpoint_tolerance_snap"
            detail = "position snapped to final lane endpoint"

        if lookup_position == self.lane_end_m:
            interval = self.intervals[-1]
        else:
            index = bisect_right(self.starts_m, lookup_position) - 1
            if index < 0:
                raise ProjectionError([_reason("position_out_of_range", position_m)])
            interval = self.intervals[index]
            if not (interval.start_m <= lookup_position < interval.end_m):
                raise ProjectionError([_reason("position_out_of_range", position_m)])
        return interval, lookup_position, assignment_status, detail


@dataclass(frozen=True)
class ValidatedPhysicalTopology:
    """Immutable A2 artifact plus an independently constructed numeric index."""

    artifact: Mapping[str, Any]
    semantic_sha256: str
    tolerance_m: float
    lanes: Mapping[tuple[int, int], LaneIntervals]
    stocks: Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True)
class ProjectionResult:
    ledger: Mapping[str, Any]

    @property
    def status(self) -> str:
        return str(self.ledger["status"])


@dataclass(frozen=True)
class BoundedJsonSnapshot:
    """One bounded file read whose parsed value and digest bind the same bytes."""

    path: Path
    data: bytes
    file_sha256: str
    value: Any


def _reject_constant(token: str) -> None:
    raise StrictJsonError(f"nonstandard JSON numeric token {token}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def strict_json_loads(text: str) -> Any:
    try:
        return json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except StrictJsonError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise StrictJsonError(str(exc)) from exc


def read_bounded_bytes(path: str | Path, max_bytes: int) -> bytes:
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    source = Path(path)
    try:
        if source.stat().st_size > max_bytes:
            raise StrictJsonError(f"JSON artifact exceeds {max_bytes} byte limit")
        with source.open("rb") as stream:
            data = stream.read(max_bytes + 1)
    except MemoryError as exc:
        raise StrictJsonError("JSON artifact read exhausted memory") from exc
    if len(data) > max_bytes:
        raise StrictJsonError(f"JSON artifact exceeds {max_bytes} byte limit")
    return data


def strict_load_json(path: str | Path, *, max_bytes: int | None = None) -> Any:
    try:
        if max_bytes is None:
            text = Path(path).read_text(encoding="utf-8-sig")
        else:
            text = read_bounded_bytes(path, max_bytes).decode("utf-8-sig")
        return strict_json_loads(text)
    except UnicodeDecodeError as exc:
        raise StrictJsonError(f"invalid UTF-8: {exc}") from exc


def load_bounded_json_snapshot(
    path: str | Path, *, max_bytes: int
) -> BoundedJsonSnapshot:
    source = Path(path).resolve(strict=True)
    data = read_bounded_bytes(source, max_bytes)
    try:
        value = strict_json_loads(data.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise StrictJsonError(f"invalid UTF-8: {exc}") from exc
    return BoundedJsonSnapshot(
        path=source,
        data=data,
        file_sha256=hashlib.sha256(data).hexdigest(),
        value=value,
    )


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (canonical_json_text(_thaw(value)) + "\n").encode("utf-8")


def freeze_json(value: Any) -> Any:
    return _freeze(value)


def thaw_json(value: Any) -> Any:
    return _thaw(value)


def json_type_strict_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int or int/float coercions."""

    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(
            isinstance(key, str)
            and json_type_strict_equal(left[key], right[key])
            for key in left
        )
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(
            json_type_strict_equal(a, b) for a, b in zip(left, right)
        )
    return type(left) is type(right) and left == right


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: str | Path, value: Mapping[str, Any]) -> None:
    target = Path(path).resolve(strict=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_json_text(_thaw(value)))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def resolve_contained_path(
    workspace_root: str | Path,
    declared_path: str | Path,
    *,
    must_exist: bool = True,
    allow_absolute: bool = False,
) -> Path:
    root = Path(workspace_root).resolve(strict=True)
    declared = Path(declared_path)
    if declared.is_absolute() and not allow_absolute:
        raise ValueError("absolute child paths are forbidden")
    candidate = declared if declared.is_absolute() else root / declared
    resolved = candidate.resolve(strict=must_exist)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes canonical workspace root") from exc
    return resolved


def workspace_relative_path(workspace_root: str | Path, path: str | Path) -> str:
    root = Path(workspace_root).resolve(strict=True)
    resolved = Path(path).resolve(strict=False)
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("path escapes canonical workspace root") from exc


def projection_sidecar_path(state_path: str | Path) -> Path:
    path = Path(state_path)
    return path.with_name(f"{path.stem}.physical_projection_v2_1.json")


def topology_semantic_payload(artifact: Mapping[str, Any]) -> dict[str, Any]:
    source = artifact["source_artifacts"]
    return {
        "schema_version": artifact["schema_version"],
        "source_artifacts": {
            key: source[key]
            for key in (
                "lane_graph_semantic_sha256",
                "lane_route_proofs_semantic_sha256",
                "ownership_evidence_semantic_sha256",
                "adjacency_evidence_semantic_sha256",
                "capacity_evidence_semantic_sha256",
                "legacy_partition_identity_sha256",
            )
        },
        "policies": artifact["policies"],
        "legacy_partition": artifact["legacy_partition"],
        "capacity_evidence": artifact["capacity_evidence"],
        "stocks": artifact["stocks"],
        "stock_edges": artifact["stock_edges"],
    }


def _finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _positive_int(value: Any) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    return value if 0 < value <= MAX_VISSIM_ID else None


def _canonical_positive_key(value: Any) -> int | None:
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        return None
    if value.startswith("0"):
        return None
    number = int(value)
    return number if number <= MAX_VISSIM_ID else None


def _position_text(value: float) -> str:
    value = 0.0 if abs(float(value)) <= POSITION_TOLERANCE_M else float(value)
    text = format(value, ".15f").rstrip("0").rstrip(".")
    return text or "0"


def _expected_stock_id(link_no: int, lane_no: int, start_m: float, end_m: float) -> str:
    return f"stock:{link_no}:{lane_no}:{_position_text(start_m)}:{_position_text(end_m)}"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


def _global_field_issues(artifact: Mapping[str, Any]) -> list[str]:
    missing = sorted(_GLOBAL_ARTIFACT_FIELDS - set(artifact))
    issues = [f"missing global fields: {missing}"] if missing else []
    for field in ("input_hashes", "command_version", "sample_dimensions", "units"):
        if field in artifact and not isinstance(artifact[field], dict):
            issues.append(f"{field} must be an object")
    if "downstream_consumers" in artifact and not isinstance(
        artifact["downstream_consumers"], list
    ):
        issues.append("downstream_consumers must be an array")
    return issues


def validate_physical_stock_topology(
    topology: Mapping[str, Any],
    lane_graph: Mapping[str, Any] | None = None,
) -> ValidatedPhysicalTopology:
    """Validate A2 independently and build an immutable interval index."""

    if not isinstance(topology, Mapping):
        raise TopologyValidationError([_reason("topology_structure_invalid", "topology is not an object")])
    trust_issues: list[str] = []
    structure_issues = _global_field_issues(topology)
    if set(topology) != _TOPOLOGY_FIELDS:
        structure_issues.append("topology artifact shape mismatch")
    if topology.get("schema_version") != TOPOLOGY_SCHEMA_VERSION:
        trust_issues.append("schema_version")
    if topology.get("canonical_json_version") != CANONICAL_JSON_VERSION:
        trust_issues.append("canonical_json_version")
    if topology.get("status") != "PASS" or topology.get("reasons") != []:
        trust_issues.append("status/reasons")
    try:
        semantic = canonical_json_sha256(topology_semantic_payload(topology))
    except (KeyError, TypeError, ValueError) as exc:
        semantic = ""
        structure_issues.append(f"invalid semantic payload: {exc}")
    if topology.get("semantic_sha256") != semantic or not SHA256_PATTERN.fullmatch(semantic):
        trust_issues.append("semantic_sha256")
    if topology.get("units") != TOPOLOGY_UNITS:
        structure_issues.append("units do not match physical-stock-topology-v2.1")
    if topology.get("downstream_consumers") != TOPOLOGY_DOWNSTREAM_CONSUMERS:
        structure_issues.append("downstream consumer metadata mismatch")
    source_artifacts = topology.get("source_artifacts")
    if not isinstance(source_artifacts, dict) or not _TOPOLOGY_SEMANTIC_INPUT_HASHES.issubset(
        source_artifacts
    ) or any(
        SHA256_PATTERN.fullmatch(str(source_artifacts.get(key, ""))) is None
        for key in _TOPOLOGY_SEMANTIC_INPUT_HASHES
    ):
        structure_issues.append("source artifact semantic hashes are incomplete or invalid")
        source_artifacts = source_artifacts if isinstance(source_artifacts, dict) else {}

    input_hashes = topology.get("input_hashes")
    allowed_input_hash_sets = (
        _TOPOLOGY_SEMANTIC_INPUT_HASHES,
        _TOPOLOGY_SEMANTIC_INPUT_HASHES | _TOPOLOGY_RAW_INPUT_HASHES,
    )
    if not isinstance(input_hashes, dict) or set(input_hashes) not in allowed_input_hash_sets:
        structure_issues.append("topology input_hashes names mismatch")
        input_hashes = input_hashes if isinstance(input_hashes, dict) else {}
    else:
        if any(SHA256_PATTERN.fullmatch(str(value)) is None for value in input_hashes.values()):
            structure_issues.append("topology input_hashes contain invalid SHA-256")
        for key in _TOPOLOGY_SEMANTIC_INPUT_HASHES:
            if input_hashes.get(key) != source_artifacts.get(key):
                structure_issues.append(f"topology input_hashes.{key} binding mismatch")
        source_files = source_artifacts.get("source_file_sha256")
        if set(input_hashes) == _TOPOLOGY_SEMANTIC_INPUT_HASHES | _TOPOLOGY_RAW_INPUT_HASHES:
            expected_raw = {
                "lane_graph_sha256": "lane_graph",
                "lane_route_proofs_sha256": "lane_route_proofs",
                "link_assignment_sha256": "ownership_evidence",
                "adjacency_sha256": "adjacency_evidence",
                "storage_capacity_sha256": "capacity_evidence",
            }
            if not isinstance(source_files, dict) or any(
                input_hashes.get(contract) != source_files.get(source)
                for contract, source in expected_raw.items()
            ):
                structure_issues.append("topology raw input/source-file binding mismatch")

    command_version = topology.get("command_version")
    command = topology.get("command")
    if not isinstance(command_version, dict) or set(command_version) != _TOPOLOGY_COMMAND_VERSION_FIELDS:
        structure_issues.append("topology command_version shape mismatch")
        command_version = {}
    if not isinstance(command, dict) or set(command) != _TOPOLOGY_COMMAND_FIELDS:
        structure_issues.append("topology command shape mismatch")
        command = {}
    source_hashes = command.get("source_sha256")
    valid_source_hashes = (
        isinstance(source_hashes, dict)
        and bool(source_hashes)
        and all(
            isinstance(path, str)
            and bool(path)
            and SHA256_PATTERN.fullmatch(str(digest)) is not None
            for path, digest in source_hashes.items()
        )
    )
    if not valid_source_hashes:
        structure_issues.append("topology command source hashes invalid")
        source_hashes = {}
    if (
        command_version.get("command") != "scripts/compile_physical_stock_topology.py"
        or command_version.get("version") != command.get("version")
        or command_version.get("sha256") != source_hashes.get(
            "scripts/compile_physical_stock_topology.py"
        )
        or command.get("command_hash") != canonical_json_sha256(source_hashes)
        or command.get("semantic_hash_scope")
        != "schema, semantic input hashes, policies, partition, capacity evidence, stocks, stock edges"
    ):
        structure_issues.append("topology command provenance mismatch")

    policies = topology.get("policies")
    if not isinstance(policies, dict):
        structure_issues.append("policies must be an object")
        policies = {}
    tolerance = policies.get("position_tolerance_m")
    if not _finite_number(tolerance) or float(tolerance) != POSITION_TOLERANCE_M:
        structure_issues.append("position_tolerance_m mismatch")
        tolerance = POSITION_TOLERANCE_M
    if policies.get("objective_weights") != OBJECTIVE_POLICIES:
        structure_issues.append("objective weight policy metadata mismatch")

    expected_lanes: dict[tuple[int, int], tuple[str, float, str]] = {}
    if lane_graph is not None:
        nodes = lane_graph.get("nodes") if isinstance(lane_graph, Mapping) else None
        if not isinstance(nodes, list):
            structure_issues.append("lane graph nodes must be an array")
        else:
            for node in nodes:
                if not isinstance(node, dict):
                    structure_issues.append("lane graph node must be an object")
                    continue
                link_no = _canonical_positive_key(node.get("link_no"))
                lane_no = _positive_int(node.get("lane_no"))
                length = node.get("length_m")
                if link_no is None or lane_no is None or not _finite_number(length) or float(length) <= 0.0:
                    structure_issues.append(f"invalid lane graph node {node.get('id')!r}")
                    continue
                key = (link_no, lane_no)
                if key in expected_lanes:
                    structure_issues.append(f"normalized lane key collision {key}")
                expected_lanes[key] = (str(node.get("id")), float(length), str(node.get("object_kind")))

    stocks_value = topology.get("stocks")
    if not isinstance(stocks_value, list):
        structure_issues.append("stocks must be an array")
        stocks_value = []
    intervals_by_lane: dict[tuple[int, int], list[StockInterval]] = defaultdict(list)
    stock_records: dict[str, dict[str, Any]] = {}
    normalized_lane_sources: dict[tuple[int, int], set[tuple[Any, Any]]] = defaultdict(set)
    role_counts: Counter[str] = Counter()
    parent_kind_counts: Counter[str] = Counter()
    objective_one_counts: Counter[str] = Counter()
    route_membership_count = 0
    owner_errors: list[float] = []
    visibility_uncovered = 0
    uncontrolled_count = 0

    for index, stock in enumerate(stocks_value):
        if not isinstance(stock, dict):
            structure_issues.append(f"stock[{index}] must be an object")
            continue
        stock_id = stock.get("id")
        link_no = _canonical_positive_key(stock.get("link_no"))
        lane_no = _positive_int(stock.get("lane_no"))
        start = stock.get("start_m")
        end = stock.get("end_m")
        length = stock.get("length_m")
        if not isinstance(stock_id, str) or not stock_id:
            structure_issues.append(f"stock[{index}] invalid id")
            continue
        if stock_id in stock_records:
            structure_issues.append(f"duplicate stock id {stock_id}")
            continue
        if link_no is None or lane_no is None:
            structure_issues.append(f"{stock_id}: invalid positive integral link/lane key")
            continue
        key = (link_no, lane_no)
        normalized_lane_sources[key].add((stock.get("link_no"), stock.get("lane_no")))
        if len(normalized_lane_sources[key]) != 1:
            structure_issues.append(f"normalized lane key collision {key}")
        if not all(_finite_number(value) for value in (start, end, length)):
            structure_issues.append(f"{stock_id}: nonfinite interval")
            continue
        start_m, end_m, length_m = float(start), float(end), float(length)
        if start_m < 0.0 or end_m <= start_m or length_m != end_m - start_m:
            structure_issues.append(f"{stock_id}: invalid ordered interval")
        if stock_id != _expected_stock_id(link_no, lane_no, start_m, end_m):
            structure_issues.append(f"{stock_id}: noncanonical stock id")
        expected_lane_id = f"lane:{link_no}:{lane_no}"
        if stock.get("lane_id") != expected_lane_id:
            structure_issues.append(f"{stock_id}: lane_id mismatch")
        if expected_lanes:
            expected = expected_lanes.get(key)
            if expected is None:
                structure_issues.append(f"{stock_id}: lane absent from A1 graph")
            elif stock.get("lane_id") != expected[0] or stock.get("parent_kind") != expected[2]:
                structure_issues.append(f"{stock_id}: A1 lane/parent mismatch")

        roles = stock.get("roles")
        if (
            not isinstance(roles, list)
            or any(not isinstance(role, str) or not role for role in roles)
            or roles != sorted(set(roles))
            or not set(roles).issubset(ALLOWED_STOCK_ROLES)
        ):
            structure_issues.append(f"{stock_id}: invalid roles")
            roles = []
        for role in roles:
            role_counts[role] += 1
        boundary = "boundary_out" in roles
        parent_kind = stock.get("parent_kind")
        if parent_kind not in {"link", "connector"}:
            structure_issues.append(f"{stock_id}: invalid parent_kind")
        else:
            parent_kind_counts[parent_kind] += 1
        if (parent_kind == "connector") != ("connector" in roles):
            structure_issues.append(f"{stock_id}: connector role mismatch")

        owner_state = stock.get("control_owner_state")
        owner_weights = stock.get("control_owner_weights")
        visible_to = stock.get("visible_to")
        if not isinstance(owner_state, dict) or owner_state.get("kind") not in {
            "controlled", "external", "uncontrolled"
        }:
            structure_issues.append(f"{stock_id}: invalid control_owner_state")
            owner_state = {"kind": "invalid"}
        elif owner_state["kind"] == "controlled" and (
            not isinstance(owner_state.get("basis"), str) or not owner_state.get("basis")
        ):
            structure_issues.append(f"{stock_id}: controlled owner state lacks basis")
        elif owner_state["kind"] in {"external", "uncontrolled"} and (
            not isinstance(owner_state.get("reason"), str) or not owner_state.get("reason")
        ):
            structure_issues.append(f"{stock_id}: noncontrolled owner state lacks reason")
        if not isinstance(owner_weights, dict):
            structure_issues.append(f"{stock_id}: control_owner_weights must be an object")
            owner_weights = {}
        valid_weights = all(
            isinstance(owner, str)
            and bool(owner)
            and _finite_number(weight)
            and float(weight) >= 0.0
            for owner, weight in owner_weights.items()
        )
        if not valid_weights:
            structure_issues.append(f"{stock_id}: invalid owner weight")
        owner_sum = math.fsum(float(value) for value in owner_weights.values()) if valid_weights else 0.0
        if owner_state.get("kind") == "controlled":
            error = abs(owner_sum - 1.0)
            owner_errors.append(error)
            if not owner_weights or error > WEIGHT_TOLERANCE:
                structure_issues.append(f"{stock_id}: controlled owner weights do not sum to one")
        elif owner_weights:
            structure_issues.append(f"{stock_id}: noncontrolled stock has owner weights")
        if (owner_state.get("kind") == "external") != boundary:
            structure_issues.append(f"{stock_id}: boundary/external owner state mismatch")
        if owner_state.get("kind") == "uncontrolled":
            uncontrolled_count += 1
        if (
            not isinstance(visible_to, list)
            or any(not isinstance(viewer, str) or not viewer for viewer in visible_to)
            or visible_to != sorted(set(visible_to))
        ):
            structure_issues.append(f"{stock_id}: invalid visibility")
            visible_to = []
        if not visible_to:
            visibility_uncovered += 1
        if owner_state.get("kind") == "controlled" and not set(owner_weights).issubset(visible_to):
            structure_issues.append(f"{stock_id}: owners absent from visibility")
        if owner_state.get("kind") == "external" and "external:boundary-out" not in visible_to:
            structure_issues.append(f"{stock_id}: missing explicit external visibility bucket")
        if owner_state.get("kind") == "uncontrolled" and not any(
            viewer.startswith("uncontrolled:") for viewer in visible_to
        ):
            structure_issues.append(f"{stock_id}: missing explicit uncontrolled visibility bucket")

        objective = stock.get("objective_weights")
        expected_objective = {
            "physical_total": 1,
            "controller_default": 0 if boundary else 1,
            "controller_with_boundary": 1,
            "boundary_only": 1 if boundary else 0,
        }
        valid_objective = (
            isinstance(objective, dict)
            and objective == expected_objective
            and not any(isinstance(value, bool) for value in objective.values())
        )
        if not valid_objective:
            structure_issues.append(f"{stock_id}: invalid binary objective weights")
        else:
            for mode, value in objective.items():
                objective_one_counts[mode] += int(value == 1)
        memberships = stock.get("route_memberships")
        if not isinstance(memberships, list):
            structure_issues.append(f"{stock_id}: route_memberships must be an array")
        else:
            route_membership_count += len(memberships)
            for membership in memberships:
                if not isinstance(membership, dict) or set(membership) != _ROUTE_MEMBERSHIP_FIELDS:
                    structure_issues.append(f"{stock_id}: malformed route membership")
                    continue
                overlap_start = membership.get("overlap_start_m")
                overlap_end = membership.get("overlap_end_m")
                if (
                    not _finite_number(overlap_start)
                    or not _finite_number(overlap_end)
                    or float(overlap_start) < start_m
                    or float(overlap_end) > end_m
                    or float(overlap_end) <= float(overlap_start)
                    or _positive_int(membership.get("path_index")) is None
                    or not isinstance(membership.get("segment_index"), int)
                    or isinstance(membership.get("segment_index"), bool)
                    or membership.get("segment_index", -1) < 0
                    or not isinstance(membership.get("flow_path_shares"), list)
                    or not membership.get("flow_path_shares")
                ):
                    structure_issues.append(f"{stock_id}: invalid route membership evidence")

        interval = StockInterval(stock_id, link_no, lane_no, start_m, end_m)
        intervals_by_lane[key].append(interval)
        stock_records[stock_id] = stock

    lane_indexes: dict[tuple[int, int], LaneIntervals] = {}
    if expected_lanes and set(intervals_by_lane) != set(expected_lanes):
        structure_issues.append("stock lane universe does not equal A1 lane universe")
    for key, intervals in intervals_by_lane.items():
        intervals.sort(key=lambda item: (item.start_m, item.end_m, item.stock_id))
        expected_start = 0.0
        for interval in intervals:
            if interval.start_m != expected_start:
                structure_issues.append(f"lane {key}: non-exact interval cover at {expected_start}")
            expected_start = interval.end_m
        lane_end = expected_start
        if expected_lanes and key in expected_lanes and lane_end != expected_lanes[key][1]:
            structure_issues.append(f"lane {key}: final endpoint does not equal A1 lane length")
        lane_indexes[key] = LaneIntervals(
            link_no=key[0],
            lane_no=key[1],
            lane_end_m=lane_end,
            starts_m=tuple(item.start_m for item in intervals),
            intervals=tuple(intervals),
        )

    edges = topology.get("stock_edges")
    if not isinstance(edges, list):
        structure_issues.append("stock_edges must be an array")
        edges = []
    edge_ids: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict) or not isinstance(edge.get("id"), str):
            structure_issues.append("invalid stock edge")
            continue
        if edge["id"] in edge_ids:
            structure_issues.append(f"duplicate stock edge id {edge['id']}")
        edge_ids.add(edge["id"])
        source = stock_records.get(str(edge.get("from_stock_id")))
        target = stock_records.get(str(edge.get("to_stock_id")))
        if source is None or target is None:
            structure_issues.append(f"{edge['id']}: unknown stock endpoint")
            continue
        expected_fields = {
            "from_link_no": source["link_no"],
            "from_lane_no": source["lane_no"],
            "to_link_no": target["link_no"],
            "to_lane_no": target["lane_no"],
        }
        if any(edge.get(field) != value for field, value in expected_fields.items()):
            structure_issues.append(f"{edge['id']}: stock endpoint identity mismatch")
        for field in ("from_position_m", "to_position_m"):
            if not _finite_number(edge.get(field)):
                structure_issues.append(f"{edge['id']}: invalid {field}")
        if (
            _finite_number(edge.get("from_position_m"))
            and float(edge["from_position_m"]) != float(source["end_m"])
        ) or (
            _finite_number(edge.get("to_position_m"))
            and float(edge["to_position_m"]) != float(target["start_m"])
        ):
            structure_issues.append(f"{edge['id']}: stock edge position mismatch")

    dimensions = topology.get("sample_dimensions")
    if not isinstance(dimensions, dict):
        structure_issues.append("sample_dimensions must be an object")
    else:
        expected_dimensions: dict[str, Any] = {
            "stocks": len(stock_records),
            "stock_edges": len(edges),
            "route_memberships": route_membership_count,
            "stocks_by_parent_kind": dict(sorted(parent_kind_counts.items())),
            "stocks_by_role": dict(sorted(role_counts.items())),
            "objective_weight_one_counts": {
                mode: objective_one_counts[mode] for mode in OBJECTIVE_MODES
            },
        }
        if lane_graph is not None:
            expected_dimensions.update({
                "a1_lane_nodes": len(lane_graph.get("nodes", [])),
                "a1_road_links": len(lane_graph.get("links", [])),
                "a1_connector_links": len(lane_graph.get("connectors", [])),
            })
        if dimensions != expected_dimensions:
            structure_issues.append("sample_dimensions mismatch")

    gates = topology.get("production_gates")
    if not isinstance(gates, dict):
        structure_issues.append("production_gates must be an object")
    else:
        for field in (
            "lane_interval_gaps",
            "lane_interval_overlaps",
            "lane_interval_missing_lanes",
            "lane_interval_nonpositive",
            "duplicate_stock_ids",
            "legacy_partition_duplicate",
            "legacy_partition_missing_from_a1",
            "legacy_partition_identity_mismatch",
            "objective_policy_violations",
        ):
            if gates.get(field) != 0:
                structure_issues.append(f"production_gates.{field} must be zero")
        if gates.get("unexplained_owner_stocks") != uncontrolled_count:
            structure_issues.append("production_gates.unexplained_owner_stocks mismatch")
        if gates.get("visibility_uncovered_stocks") != visibility_uncovered:
            structure_issues.append("production_gates.visibility_uncovered_stocks mismatch")
        maximum_owner_error = max(owner_errors, default=0.0)
        if not _finite_number(gates.get("maximum_owner_weight_sum_error")) or abs(
            float(gates.get("maximum_owner_weight_sum_error", math.inf)) - maximum_owner_error
        ) > WEIGHT_TOLERANCE:
            structure_issues.append("production_gates.maximum_owner_weight_sum_error mismatch")

    reasons: list[dict[str, Any]] = []
    if trust_issues:
        reasons.append(_reason("topology_trust_mismatch", sorted(set(trust_issues))))
    if structure_issues:
        reasons.append(_reason("topology_structure_invalid", sorted(set(structure_issues))))
    if reasons:
        raise TopologyValidationError(reasons)
    return ValidatedPhysicalTopology(
        artifact=_freeze(topology),
        semantic_sha256=semantic,
        tolerance_m=float(tolerance),
        lanes=MappingProxyType(dict(sorted(lane_indexes.items()))),
        stocks=MappingProxyType({key: _freeze(stock_records[key]) for key in sorted(stock_records)}),
    )


def _normalized_count_map(value: Any, field: str, issues: list[dict[str, Any]]) -> dict[str, int]:
    if not isinstance(value, dict):
        issues.append(_reason("aggregate_mismatch", f"{field} must be an object"))
        return {}
    result: dict[str, int] = {}
    for key, count in value.items():
        normalized = _canonical_positive_key(key)
        valid_count = isinstance(count, int) and not isinstance(count, bool) and count >= 0
        if normalized is None or not valid_count:
            issues.append(_reason("aggregate_mismatch", f"invalid {field} entry {key!r}"))
            continue
        canonical = str(normalized)
        if canonical in result:
            issues.append(_reason("aggregate_mismatch", f"normalized {field} key collision {key!r}"))
        result[canonical] = int(count)
    return dict(sorted(result.items(), key=lambda item: int(item[0])))


def normalize_vehicle_records(
    state: Mapping[str, Any],
    tolerance_m: float,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], str]:
    """Validate and normalize the complete vehicle-record observation universe."""

    issues: list[dict[str, Any]] = []
    if not isinstance(state, Mapping):
        raise ProjectionError([_reason("invalid_numeric_value", "state must be an object")])
    run_provenance = state.get("run_provenance")
    run_id = run_provenance.get("run_id") if isinstance(run_provenance, dict) else None
    if not isinstance(run_id, str) or RUN_ID_PATTERN.fullmatch(run_id) is None:
        issues.append(_reason("invalid_numeric_value", "invalid run_id"))
    sim_sec = state.get("sim_sec")
    if not _finite_number(sim_sec) or float(sim_sec) < 0.0:
        issues.append(_reason("invalid_numeric_value", "invalid root sim_sec"))
        normalized_sim_sec = 0.0
    else:
        normalized_sim_sec = float(sim_sec)

    envelope = state.get("vehicle_records")
    if not isinstance(envelope, dict):
        raise ProjectionError([_reason("aggregate_mismatch", "missing vehicle_records envelope")])
    if set(envelope) != _VEHICLE_ENVELOPE_FIELDS:
        issues.append(_reason("aggregate_mismatch", {
            "vehicle_records_fields": sorted(envelope),
            "expected": sorted(_VEHICLE_ENVELOPE_FIELDS),
        }))
    if envelope.get("schema_version") != VEHICLE_RECORDS_SCHEMA_VERSION:
        issues.append(_reason("aggregate_mismatch", "vehicle record schema mismatch"))
    if envelope.get("complete") is not True:
        issues.append(_reason("aggregate_mismatch", "vehicle record envelope is incomplete"))
    if envelope.get("source_attributes") != _SOURCE_ATTRIBUTES:
        issues.append(_reason("aggregate_mismatch", "source_attributes mismatch"))
    threshold = envelope.get("stopped_threshold_kph")
    if not _finite_number(threshold) or float(threshold) != 1.0:
        issues.append(_reason("aggregate_mismatch", "stopped_threshold_kph must equal 1.0"))
    times: dict[str, float] = {}
    for field in ("paused_at_sim_sec", "capture_sim_sec_before", "capture_sim_sec_after"):
        value = envelope.get(field)
        if not _finite_number(value) or float(value) < 0.0:
            issues.append(_reason("invalid_numeric_value", f"invalid {field}"))
        else:
            times[field] = float(value)
    if len(times) == 3 and any(value != normalized_sim_sec for value in times.values()):
        issues.append(_reason("com_count_changed", "capture/root time mismatch"))

    scalar_counts: dict[str, int] = {}
    for field in (
        "collection_count_before",
        "collection_count_after",
        "record_count",
        "unobservable_count",
        "external_source_count",
    ):
        value = envelope.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            issues.append(_reason("invalid_numeric_value", f"invalid {field}"))
        else:
            scalar_counts[field] = value
    if scalar_counts.get("collection_count_before") != scalar_counts.get("collection_count_after"):
        issues.append(_reason("com_count_changed", "collection scalar counts differ"))
    if scalar_counts.get("unobservable_count") != 0 or scalar_counts.get("external_source_count") != 0:
        issues.append(_reason("aggregate_mismatch", "full-network zero-count identity failed"))

    records_value = envelope.get("records")
    if not isinstance(records_value, list):
        issues.append(_reason("invalid_table_shape", "records must be an array"))
        records_value = []
    normalized_records: list[dict[str, Any]] = []
    vehicle_numbers: list[int] = []
    reconstructed_counts: Counter[str] = Counter()
    reconstructed_stopped: Counter[str] = Counter()
    for index, record in enumerate(records_value):
        if not isinstance(record, dict) or set(record) != _VEHICLE_RECORD_FIELDS:
            issues.append(_reason("invalid_table_shape", f"record[{index}] shape mismatch"))
            continue
        veh_no = _positive_int(record.get("veh_no"))
        link_no = _positive_int(record.get("link_no"))
        lane_no = _positive_int(record.get("lane_no"))
        position = record.get("position_m")
        speed = record.get("speed_kph")
        stopped = record.get("stopped")
        if veh_no is None or link_no is None or lane_no is None:
            issues.append(_reason("invalid_numeric_value", f"record[{index}] invalid identifier"))
            continue
        if not _finite_number(position) or not _finite_number(speed) or float(speed) < 0.0:
            issues.append(_reason("invalid_numeric_value", f"record[{index}] invalid position/speed"))
            continue
        position_m, speed_kph = float(position), float(speed)
        if position_m < -tolerance_m:
            issues.append(_reason("position_out_of_range", f"record[{index}] below outer tolerance"))
            continue
        if not isinstance(stopped, bool) or stopped != (speed_kph < 1.0):
            issues.append(_reason("aggregate_mismatch", f"record[{index}] stopped derivation mismatch"))
            continue
        normalized = {
            "veh_no": veh_no,
            "link_no": link_no,
            "lane_no": lane_no,
            "position_m": position_m,
            "speed_kph": speed_kph,
            "stopped": stopped,
        }
        normalized_records.append(normalized)
        vehicle_numbers.append(veh_no)
        reconstructed_counts[str(link_no)] += 1
        if stopped:
            reconstructed_stopped[str(link_no)] += 1
    duplicate_count = len(vehicle_numbers) - len(set(vehicle_numbers))
    if duplicate_count:
        issues.append(_reason("duplicate_vehicle_in_snapshot", duplicate_count))
    normalized_records.sort(key=lambda item: item["veh_no"])

    declared_counts = _normalized_count_map(
        envelope.get("full_network_link_counts"), "full_network_link_counts", issues
    )
    declared_stopped = _normalized_count_map(
        envelope.get("full_network_link_stopped_counts"),
        "full_network_link_stopped_counts",
        issues,
    )
    expected_counts = dict(sorted(reconstructed_counts.items(), key=lambda item: int(item[0])))
    expected_stopped = {
        key: reconstructed_stopped.get(key, 0)
        for key in sorted(reconstructed_counts, key=int)
    }
    if declared_counts != expected_counts or declared_stopped != expected_stopped:
        issues.append(_reason("aggregate_mismatch", {
            "declared_counts": declared_counts,
            "reconstructed_counts": expected_counts,
            "declared_stopped": declared_stopped,
            "reconstructed_stopped": expected_stopped,
        }))

    raw_count = len(records_value)
    unique_count = len(set(vehicle_numbers))
    if any(
        scalar_counts.get(field) != raw_count
        for field in ("collection_count_before", "collection_count_after", "record_count")
    ):
        issues.append(_reason("aggregate_mismatch", "collection/record count identity failed"))
    if unique_count != raw_count:
        # The closed duplicate reason above is authoritative; retain the identity detail here.
        pass
    total = state.get("total_vehicles")
    if not isinstance(total, int) or isinstance(total, bool) or total != raw_count:
        issues.append(_reason("state_total_mismatch", {"state_total": total, "record_count": raw_count}))
    if issues:
        diagnostics = {
            "raw_record_count": raw_count,
            "unique_snapshot_identity_count": unique_count,
            "same_snapshot_duplicate_count": duplicate_count,
            "malformed_record_count": max(0, raw_count - len(normalized_records)),
            "aggregate_map_mismatch_count": sum(
                item["code"] == "aggregate_mismatch" for item in issues
            ),
        }
        raise ProjectionError(issues, diagnostics)

    normalized_envelope = {
        "schema_version": VEHICLE_RECORDS_SCHEMA_VERSION,
        "complete": True,
        "paused_at_sim_sec": times["paused_at_sim_sec"],
        "capture_sim_sec_before": times["capture_sim_sec_before"],
        "capture_sim_sec_after": times["capture_sim_sec_after"],
        "source_attributes": dict(_SOURCE_ATTRIBUTES),
        "stopped_threshold_kph": 1.0,
        "collection_count_before": scalar_counts["collection_count_before"],
        "collection_count_after": scalar_counts["collection_count_after"],
        "record_count": scalar_counts["record_count"],
        "unobservable_count": scalar_counts["unobservable_count"],
        "external_source_count": scalar_counts["external_source_count"],
        "full_network_link_counts": declared_counts,
        "full_network_link_stopped_counts": declared_stopped,
        "records": normalized_records,
    }
    return normalized_envelope, tuple(normalized_records), canonical_json_sha256(normalized_envelope)


def projection_semantic_payload(ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: ledger[key]
        for key in (
            "schema_version",
            "input_hashes",
            "command_version",
            "status",
            "reasons",
            "sample_dimensions",
            "units",
            "downstream_consumers",
            "run_id",
            "sim_sec",
            "vehicle_assignments",
            "stock_counts",
            "view_summaries",
            "projection_diagnostics",
            "normalized_projection_sha256",
        )
    }


def _projection_diagnostics_template() -> dict[str, Any]:
    return {
        "collection_count_before": 0,
        "collection_count_after": 0,
        "raw_record_count": 0,
        "unique_snapshot_identity_count": 0,
        "unique_assigned_count": 0,
        "unobservable_count": 0,
        "external_source_count": 0,
        "same_snapshot_duplicate_count": 0,
        "malformed_record_count": 0,
        "unknown_lane_count": 0,
        "position_out_of_range_count": 0,
        "aggregate_map_mismatch_count": 0,
        "state_total_mismatch_count": 0,
        "per_link_residuals": {},
        "stock_total": 0,
        "global_residual": 0,
        "owner_partition_residual": 0.0,
        "objective_partition_residual": 0,
    }


def _validate_hash_context(hash_context: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(hash_context, Mapping) or set(hash_context) != set(PROJECTION_HASH_NAMES):
        raise ProjectionError([_reason("topology_trust_mismatch", "projection hash context shape mismatch")])
    result = {key: str(hash_context[key]) for key in PROJECTION_HASH_NAMES}
    invalid = [key for key, value in result.items() if SHA256_PATTERN.fullmatch(value) is None]
    if invalid:
        raise ProjectionError([_reason("topology_trust_mismatch", {"invalid_hashes": invalid})])
    return result


def _project_vehicle_records_kernel(
    topology: ValidatedPhysicalTopology,
    state: Mapping[str, Any],
    hash_context: Mapping[str, Any],
) -> ProjectionResult:
    """Shared deterministic projection calculation for producer and validator."""

    if not isinstance(topology, ValidatedPhysicalTopology):
        raise ProjectionError([_reason("topology_structure_invalid", "validated topology required")])
    hashes = _validate_hash_context(hash_context)
    if hashes["topology_semantic_sha256"] != topology.semantic_sha256:
        raise ProjectionError([_reason("topology_trust_mismatch", "topology semantic hash context mismatch")])
    envelope, records, records_hash = normalize_vehicle_records(state, topology.tolerance_m)
    if hashes["vehicle_records_semantic_sha256"] != records_hash:
        raise ProjectionError([_reason("topology_trust_mismatch", "vehicle record semantic hash mismatch")])

    run_id = str(state["run_provenance"]["run_id"])
    sim_sec = float(state["sim_sec"])
    assignments: list[dict[str, Any]] = []
    stock_counts = {stock_id: 0 for stock_id in topology.stocks}
    link_assigned: Counter[str] = Counter()
    failures: list[dict[str, Any]] = []
    unknown_lane_count = 0
    out_of_range_count = 0
    for record in records:
        key = (record["link_no"], record["lane_no"])
        lane = topology.lanes.get(key)
        if lane is None:
            unknown_lane_count += 1
            failures.append(_reason("unknown_lane", {"veh_no": record["veh_no"], "lane": key}))
            continue
        try:
            interval, lookup_position, status, detail = lane.locate(
                record["position_m"], topology.tolerance_m
            )
        except ProjectionError as exc:
            out_of_range_count += 1
            failures.extend(
                _reason(item["code"], {"veh_no": record["veh_no"], "detail": item.get("detail")})
                for item in exc.reasons
            )
            continue
        stock_counts[interval.stock_id] += 1
        link_assigned[str(record["link_no"])] += 1
        assignments.append({
            "run_id": run_id,
            "sim_sec": sim_sec,
            "veh_no": record["veh_no"],
            "stock_id": interval.stock_id,
            "source_link_no": record["link_no"],
            "source_lane_no": record["lane_no"],
            "source_position_m": record["position_m"],
            "projected_position_m": lookup_position,
            "assignment_status": status,
            "assignment_detail": detail,
        })
    assignments.sort(key=lambda item: (item["run_id"], item["sim_sec"], item["veh_no"]))

    raw_count = envelope["record_count"]
    assigned_count = len(assignments)
    stock_total = sum(stock_counts.values())
    per_link_residuals = {
        link_no: envelope["full_network_link_counts"].get(link_no, 0) - link_assigned.get(link_no, 0)
        for link_no in sorted(
            set(envelope["full_network_link_counts"]) | set(link_assigned), key=int
        )
    }
    diagnostics = _projection_diagnostics_template()
    diagnostics.update({
        "collection_count_before": envelope["collection_count_before"],
        "collection_count_after": envelope["collection_count_after"],
        "raw_record_count": raw_count,
        "unique_snapshot_identity_count": len({item["veh_no"] for item in records}),
        "unique_assigned_count": assigned_count,
        "unobservable_count": envelope["unobservable_count"],
        "external_source_count": envelope["external_source_count"],
        "unknown_lane_count": unknown_lane_count,
        "position_out_of_range_count": out_of_range_count,
        "per_link_residuals": per_link_residuals,
        "stock_total": stock_total,
        "global_residual": raw_count - stock_total,
    })
    if failures or assigned_count != raw_count or stock_total != assigned_count or any(per_link_residuals.values()):
        if assigned_count != raw_count or stock_total != assigned_count:
            failures.append(_reason("projection_mass_residual", diagnostics["global_residual"]))
        raise ProjectionError(failures, diagnostics)

    objective_views = {mode: 0 for mode in OBJECTIVE_MODES}
    owner_buckets: defaultdict[str, float] = defaultdict(float)
    role_views: defaultdict[str, int] = defaultdict(int)
    visibility_views: defaultdict[str, int] = defaultdict(int)
    owner_total = 0.0
    for stock_id, count in stock_counts.items():
        stock = topology.stocks[stock_id]
        for mode in OBJECTIVE_MODES:
            objective_views[mode] += count * int(stock["objective_weights"][mode])
        for role in stock["roles"]:
            role_views[str(role)] += count
        for viewer in stock["visible_to"]:
            visibility_views[str(viewer)] += count
        owner_state = stock["control_owner_state"]["kind"]
        if owner_state == "controlled":
            for owner, weight in stock["control_owner_weights"].items():
                contribution = count * float(weight)
                owner_buckets[str(owner)] += contribution
                owner_total += contribution
        elif owner_state == "external":
            owner_buckets["external:boundary-out"] += count
            owner_total += count
        else:
            owner_buckets["uncontrolled:no-owner-evidence"] += count
            owner_total += count
    owner_residual = float(assigned_count) - owner_total
    objective_residual = (
        objective_views["controller_default"]
        + objective_views["boundary_only"]
        - assigned_count
    )
    diagnostics["owner_partition_residual"] = owner_residual
    diagnostics["objective_partition_residual"] = objective_residual
    if (
        objective_views["physical_total"] != assigned_count
        or objective_views["controller_with_boundary"] != assigned_count
        or objective_residual != 0
        or abs(owner_residual) > WEIGHT_TOLERANCE
    ):
        raise ProjectionError([_reason("projection_mass_residual", {
            "objective_residual": objective_residual,
            "owner_residual": owner_residual,
        })], diagnostics)

    view_summaries = {
        "objective_views": objective_views,
        "owner_partition": dict(sorted(owner_buckets.items())),
        "roles_nonpartitioning": dict(sorted(role_views.items())),
        "visibility_nonpartitioning": dict(sorted(visibility_views.items())),
    }
    normalized_projection_sha256 = canonical_json_sha256({
        "topology_semantic_sha256": topology.semantic_sha256,
        "vehicle_assignments": assignments,
        "stock_counts": stock_counts,
    })
    ledger: dict[str, Any] = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "input_hashes": hashes,
        "command_version": dict(PROJECTION_COMMAND_VERSION),
        "status": "PASS",
        "reasons": [],
        "sample_dimensions": {
            "records": raw_count,
            "assignments": assigned_count,
            "stocks": len(stock_counts),
            "nonzero_stocks": sum(count > 0 for count in stock_counts.values()),
            "lanes": len(topology.lanes),
        },
        "units": dict(PROJECTION_UNITS),
        "downstream_consumers": list(PROJECTION_DOWNSTREAM_CONSUMERS),
        "run_id": run_id,
        "sim_sec": sim_sec,
        "vehicle_assignments": assignments,
        "stock_counts": stock_counts,
        "view_summaries": view_summaries,
        "projection_diagnostics": diagnostics,
        "normalized_projection_sha256": normalized_projection_sha256,
    }
    ledger["semantic_sha256"] = canonical_json_sha256(projection_semantic_payload(ledger))
    return ProjectionResult(_freeze(ledger))


def project_vehicle_records(
    topology: ValidatedPhysicalTopology,
    state: Mapping[str, Any],
    hash_context: Mapping[str, Any],
) -> ProjectionResult:
    """Sole public projector from one complete snapshot to A2 stocks."""

    return _project_vehicle_records_kernel(topology, state, hash_context)


def failure_projection_ledger(
    *,
    status: str,
    reasons: Sequence[Mapping[str, Any]],
    hash_context: Mapping[str, Any] | None = None,
    run_id: str = "",
    sim_sec: float | None = None,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in {"FAIL", "NOT_EVALUATED"}:
        raise ValueError("failure ledger status must be FAIL or NOT_EVALUATED")
    hashes = {
        key: str((hash_context or {}).get(key, "")) for key in PROJECTION_HASH_NAMES
    }
    merged_diagnostics = _projection_diagnostics_template()
    merged_diagnostics.update(dict(diagnostics or {}))
    ledger: dict[str, Any] = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "input_hashes": hashes,
        "command_version": dict(PROJECTION_COMMAND_VERSION),
        "status": status,
        "reasons": [dict(item) for item in reasons],
        "sample_dimensions": {
            "records": int(merged_diagnostics.get("raw_record_count", 0)),
            "assignments": int(merged_diagnostics.get("unique_assigned_count", 0)),
            "stocks": 0,
            "nonzero_stocks": 0,
            "lanes": 0,
        },
        "units": dict(PROJECTION_UNITS),
        "downstream_consumers": list(PROJECTION_DOWNSTREAM_CONSUMERS),
        "run_id": run_id,
        "sim_sec": sim_sec,
        "vehicle_assignments": [],
        "stock_counts": {},
        "view_summaries": {
            "objective_views": {},
            "owner_partition": {},
            "roles_nonpartitioning": {},
            "visibility_nonpartitioning": {},
        },
        "projection_diagnostics": merged_diagnostics,
        "normalized_projection_sha256": "",
    }
    ledger["semantic_sha256"] = canonical_json_sha256(projection_semantic_payload(ledger))
    return ledger


def write_projection_sidecar(path: str | Path, result: ProjectionResult | Mapping[str, Any]) -> None:
    ledger = result.ledger if isinstance(result, ProjectionResult) else result
    atomic_write_json(path, ledger)


__all__ = [
    "BoundedJsonSnapshot",
    "MAX_VISSIM_ID",
    "POSITION_TOLERANCE_M",
    "PROJECTION_HASH_NAMES",
    "PROJECTION_SCHEMA_VERSION",
    "ProjectionError",
    "ProjectionResult",
    "RUN_ID_PATTERN",
    "SHA256_PATTERN",
    "StrictJsonError",
    "TOPOLOGY_SCHEMA_VERSION",
    "TopologyValidationError",
    "ValidatedPhysicalTopology",
    "VEHICLE_RECORDS_SCHEMA_VERSION",
    "atomic_write_json",
    "canonical_json_bytes",
    "failure_projection_ledger",
    "file_sha256",
    "freeze_json",
    "json_type_strict_equal",
    "load_bounded_json_snapshot",
    "normalize_vehicle_records",
    "project_vehicle_records",
    "projection_semantic_payload",
    "projection_sidecar_path",
    "resolve_contained_path",
    "strict_load_json",
    "strict_json_loads",
    "thaw_json",
    "topology_semantic_payload",
    "validate_physical_stock_topology",
    "workspace_relative_path",
    "write_projection_sidecar",
]
