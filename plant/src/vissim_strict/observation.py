"""Deterministic observation projectors for the strict VISSIM plant.

The projectors intentionally accept plain mappings.  Phase 1 can therefore wrap
their output in its PlantState type without making observation ingestion depend
on the physical kernel.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence

from .topology import canonical_json_sha256


STATE_SCHEMA_VERSION = "vissim-strict-plant-state/v1"
OBSERVATION_SCHEMA_VERSION = "vissim-strict-raw-observation/v1"
PROJECTOR_VERSION = "vissim-strict-observation-projector/v1"


class ObservationProjectionError(ValueError):
    """Raised when an observation cannot be projected without ambiguity."""


_DEFAULT_CONFIG: dict[str, Any] = {
    "aggregation_window_sec": 60.0,
    "stale_after_sec": 120.0,
    "missing_freshness_sec": 1.0e9,
    "default_v_free_mps": 50.0 / 3.6,
    "minimum_speed_mps": 0.0,
    "jam_spacing_m_per_veh": 7.5,
    "queue_lane_count": 1.0,
    "queue_lane_count_by_operator": {},
    "observed_count_variance_veh2": 4.0,
    "reconstructed_count_variance_veh2": 16.0,
    "fallback_count_variance_veh2": 100.0,
}

_DETECTOR_TOP_LEVEL_KEYS = {
    "schema_version",
    "observation_id",
    "network_hash",
    "sim_time_sec",
    "captured_interval",
    "units",
    "detector_values",
    "signal_readback",
    "boundary_values",
    "metadata",
}
_TRUTH_KEYS = {
    "vehicles",
    "vehicle_rows",
    "cell_truth",
    "per_cell_truth",
    "ground_truth",
    "true_state",
    "oracle_state",
}


def project_observation(
    manifest: Mapping[str, Any],
    observation: Mapping[str, Any],
    previous_state: Mapping[str, Any] | None = None,
    mode: str = "vissim_oracle",
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project a raw observation into the common strict PlantState mapping."""

    if mode == "vissim_oracle":
        return project_vissim_oracle(manifest, observation, config=config)
    if mode == "detector_realistic":
        return project_detector_realistic(
            manifest, observation, previous_state=previous_state, config=config
        )
    raise ObservationProjectionError(f"unsupported observation mode: {mode!r}")


def project_vissim_oracle(
    manifest: Mapping[str, Any],
    observation: Mapping[str, Any],
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project complete per-cell VISSIM truth without duplicating ownership."""

    cfg = _config(config)
    sim_time = _validate_envelope(manifest, observation)
    rows = observation.get("cell_truth", observation.get("per_cell_truth"))
    if rows is None:
        raise ObservationProjectionError("oracle observation requires cell_truth")
    if isinstance(rows, Mapping):
        rows = [dict(value, cell_id=key) for key, value in rows.items()]
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ObservationProjectionError("cell_truth must be a mapping or sequence")

    cells = _cells_by_id(manifest)
    truth_by_cell: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ObservationProjectionError("each cell_truth row must be a mapping")
        cell_id = str(row.get("cell_id", ""))
        if cell_id not in cells:
            raise ObservationProjectionError(f"unknown oracle cell_id: {cell_id!r}")
        if cell_id in truth_by_cell:
            raise ObservationProjectionError(f"duplicate oracle cell_id: {cell_id}")
        truth_by_cell[cell_id] = row
    missing = sorted(set(cells) - set(truth_by_cell))
    if missing:
        raise ObservationProjectionError(
            "oracle cell_truth is incomplete: " + ", ".join(missing[:5])
        )

    estimates: dict[str, dict[str, Any]] = {}
    provenance: dict[str, list[dict[str, Any]]] = {}
    for cell_id in sorted(cells):
        row = truth_by_cell[cell_id]
        count = _oracle_count(row)
        storage = float(cells[cell_id].get("storage_veh", math.inf))
        if count < 0.0 or count > storage + 1.0e-9:
            raise ObservationProjectionError(
                f"oracle count for {cell_id} is outside [0, {storage}]"
            )
        speed = _oracle_speed(row)
        if speed < 0.0:
            raise ObservationProjectionError(f"oracle speed for {cell_id} is negative")
        estimates[cell_id] = {"vehicle_count_veh": count, "speed_mps": speed}
        provenance[cell_id] = [
            {
                "source": "cell_truth",
                "observation_id": str(observation.get("observation_id", "")),
                "observed_at_sec": float(row.get("observed_at_sec", sim_time)),
            }
        ]

    state = _build_state(
        manifest,
        sim_time,
        estimates,
        mode="vissim_oracle",
        signal_readback=observation.get("signal_readback", []),
        boundary_values=observation.get("boundary_values", []),
        estimation={
            "covariance_ref": "estimation.covariance",
            "covariance": _diagonal_covariance(estimates, cells, 0.0),
            "freshness_sec": {},
            "missing_mask": {},
            "stale_mask": {},
            "fallback_flags": [],
            "provenance": provenance,
            "aggregation_window_sec": float(cfg["aggregation_window_sec"]),
        },
    )
    return _finish_state(state)


def project_detector_realistic(
    manifest: Mapping[str, Any],
    observation: Mapping[str, Any],
    previous_state: Mapping[str, Any] | None = None,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Estimate cell state solely from detector-compatible measurements."""

    cfg = _config(config)
    sim_time = _validate_envelope(manifest, observation)
    _guard_detector_input(manifest, observation, previous_state, sim_time)
    cells = _cells_by_id(manifest)
    operators = {
        str(item["id"]): item for item in manifest.get("observation_operators", [])
    }
    records = _validated_detector_records(observation, operators, sim_time)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    freshness: dict[str, float] = {}
    missing_mask: dict[str, bool] = {}
    stale_mask: dict[str, bool] = {}
    window = float(cfg["aggregation_window_sec"])
    stale_after = float(cfg["stale_after_sec"])
    for operator_id in sorted(operators):
        operator_records = sorted(
            (record for record in records if record["operator_id"] == operator_id),
            key=lambda record: (
                float(record["observed_at_sec"]),
                str(record["measurement_kind"]),
                str(record.get("detector_id", "")),
                float(record["value"]),
            ),
        )
        if operator_records:
            age = max(0.0, sim_time - float(operator_records[-1]["observed_at_sec"]))
            freshness[operator_id] = age
            missing_mask[operator_id] = False
            stale_mask[operator_id] = age > stale_after
            if not stale_mask[operator_id]:
                grouped[operator_id] = [
                    record
                    for record in operator_records
                    if float(record["observed_at_sec"]) >= sim_time - window
                ]
                if not grouped[operator_id]:
                    stale_mask[operator_id] = True
        else:
            freshness[operator_id] = float(cfg["missing_freshness_sec"])
            missing_mask[operator_id] = True
            stale_mask[operator_id] = False

    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for operator_id in sorted(grouped):
        if stale_mask[operator_id]:
            continue
        operator = operators[operator_id]
        aggregated = _aggregate_records(grouped[operator_id])
        target_cells = _operator_cells(operator, cells)
        _add_operator_candidates(
            candidates, target_cells, operator, aggregated, manifest, cfg
        )

    previous = _previous_estimates(previous_state, cells)
    estimates: dict[str, dict[str, Any]] = {}
    provenance: dict[str, list[dict[str, Any]]] = {}
    variances: dict[str, float] = {}
    fallback_flags: list[str] = []
    for cell_id in sorted(cells):
        cell = cells[cell_id]
        cell_candidates = candidates.get(cell_id, [])
        estimate, sources, variance, fallback = _combine_candidates(
            cell, cell_candidates, previous.get(cell_id), cfg
        )
        estimates[cell_id] = estimate
        provenance[cell_id] = sources
        variances[cell_id] = variance
        if fallback:
            fallback_flags.append(f"unobserved_cell:{cell_id}:{fallback}")

    if any(missing_mask.values()):
        fallback_flags.append("missing_detector_data")
    if any(stale_mask.values()):
        fallback_flags.append("stale_detector_data")

    state = _build_state(
        manifest,
        sim_time,
        estimates,
        mode="detector_realistic",
        signal_readback=observation.get("signal_readback", []),
        boundary_values=observation.get("boundary_values", []),
        estimation={
            "covariance_ref": "estimation.covariance",
            "covariance": {
                "schema_version": "diagonal-covariance/v1",
                "state_ordering": [
                    _cell_stock_id(cell_id, cells[cell_id]) for cell_id in sorted(cells)
                ],
                "diagonal_vehicle_count_variance_veh2": [
                    variances[cell_id] for cell_id in sorted(cells)
                ],
            },
            "freshness_sec": freshness,
            "missing_mask": missing_mask,
            "stale_mask": stale_mask,
            "fallback_flags": sorted(set(fallback_flags)),
            "provenance": provenance,
            "aggregation_window_sec": window,
        },
    )
    return _finish_state(state)


def _config(config: Mapping[str, Any] | None) -> dict[str, Any]:
    result = dict(_DEFAULT_CONFIG)
    if config:
        result.update(config)
    for key in ("aggregation_window_sec", "stale_after_sec", "jam_spacing_m_per_veh"):
        value = float(result[key])
        if not math.isfinite(value) or value <= 0.0:
            raise ObservationProjectionError(f"{key} must be finite and positive")
        result[key] = value
    return result


def _validate_envelope(
    manifest: Mapping[str, Any], observation: Mapping[str, Any]
) -> float:
    if not isinstance(observation, Mapping):
        raise ObservationProjectionError("observation must be a mapping")
    if str(observation.get("schema_version", "")) != OBSERVATION_SCHEMA_VERSION:
        raise ObservationProjectionError("unsupported raw observation schema_version")
    if not str(observation.get("observation_id", "")):
        raise ObservationProjectionError("observation_id is required")
    if not isinstance(observation.get("units"), Mapping):
        raise ObservationProjectionError("units must be a mapping")
    expected_hash = str(manifest.get("topology_hash", ""))
    if not expected_hash:
        raise ObservationProjectionError("manifest has no topology_hash")
    if str(observation.get("network_hash", "")) != expected_hash:
        raise ObservationProjectionError("observation network_hash mismatch")
    sim_time = _finite(observation.get("sim_time_sec"), "sim_time_sec")
    interval = observation.get("captured_interval")
    if not isinstance(interval, Mapping):
        raise ObservationProjectionError("captured_interval is required")
    start = _finite(interval.get("start_sec"), "captured_interval.start_sec")
    end = _finite(interval.get("end_sec"), "captured_interval.end_sec")
    if start > end or sim_time < end - 1.0e-9:
        raise ObservationProjectionError("invalid or future captured_interval")
    return sim_time


def _guard_detector_input(
    manifest: Mapping[str, Any],
    observation: Mapping[str, Any],
    previous_state: Mapping[str, Any] | None,
    sim_time: float,
) -> None:
    unexpected = sorted(set(observation) - _DETECTOR_TOP_LEVEL_KEYS)
    if unexpected:
        raise ObservationProjectionError(
            "detector_realistic rejects non-detector fields: " + ", ".join(unexpected)
        )

    def walk(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                key_text = str(key).lower()
                if key_text in _TRUTH_KEYS or key_text.endswith("_truth"):
                    raise ObservationProjectionError(
                        f"detector_realistic hidden truth leakage at {path}.{key}"
                    )
                walk(child, f"{path}.{key}")
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(observation, "observation")
    if previous_state is not None:
        _validate_previous_detector_state(manifest, previous_state, sim_time)


def _validate_previous_detector_state(
    manifest: Mapping[str, Any],
    previous_state: Mapping[str, Any],
    current_sim_time: float,
) -> None:
    if not isinstance(previous_state, Mapping):
        raise ObservationProjectionError("previous detector_realistic state must be a mapping")
    if str(previous_state.get("schema_version", "")) != STATE_SCHEMA_VERSION:
        raise ObservationProjectionError("previous detector_realistic state schema_version mismatch")

    topology_hash = str(manifest.get("topology_hash", ""))
    if str(previous_state.get("topology_hash", "")) != topology_hash:
        raise ObservationProjectionError("previous detector_realistic state topology_hash mismatch")
    previous_time = _finite(previous_state.get("sim_time_sec"), "previous_state.sim_time_sec")
    if previous_time > current_sim_time + 1.0e-9:
        raise ObservationProjectionError("previous detector_realistic state is from the future")

    state_hash = previous_state.get("state_hash")
    if not isinstance(state_hash, str) or len(state_hash) != 64:
        raise ObservationProjectionError("previous detector_realistic state_hash is invalid")
    hash_payload = dict(previous_state)
    hash_payload.pop("state_hash", None)
    if canonical_json_sha256(hash_payload) != state_hash.lower():
        raise ObservationProjectionError("previous detector_realistic state_hash mismatch")

    estimation = previous_state.get("estimation")
    if not isinstance(estimation, Mapping):
        raise ObservationProjectionError("previous detector_realistic estimation is required")
    if estimation.get("mode") != "detector_realistic":
        raise ObservationProjectionError(
            "detector_realistic may only use a previous detector_realistic estimate"
        )
    if estimation.get("projector_version") != PROJECTOR_VERSION:
        raise ObservationProjectionError("previous detector_realistic projector_version mismatch")

    provenance = estimation.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ObservationProjectionError("previous detector_realistic provenance is required")
    cell_ids = set(_cells_by_id(manifest))
    if set(map(str, provenance)) != cell_ids:
        raise ObservationProjectionError("previous detector_realistic provenance cell set mismatch")
    operator_ids = {
        str(operator["id"]) for operator in manifest.get("observation_operators", [])
    }
    for cell_id in sorted(cell_ids):
        entries = provenance.get(cell_id)
        if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)) or not entries:
            raise ObservationProjectionError(
                f"previous detector_realistic provenance is invalid for {cell_id}"
            )
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ObservationProjectionError(
                    f"previous detector_realistic provenance is invalid for {cell_id}"
                )
            source = str(entry.get("source", ""))
            operator_id = str(entry.get("operator_id", ""))
            if source:
                if source not in {"previous_estimate", "zero_prior"}:
                    raise ObservationProjectionError(
                        "previous detector_realistic provenance contains oracle-derived data"
                    )
            elif operator_id not in operator_ids:
                raise ObservationProjectionError(
                    f"previous detector_realistic provenance has unknown operator for {cell_id}"
                )


def _validated_detector_records(
    observation: Mapping[str, Any],
    operators: Mapping[str, Mapping[str, Any]],
    sim_time: float,
) -> list[dict[str, Any]]:
    interval = observation["captured_interval"]
    start, end = float(interval["start_sec"]), float(interval["end_sec"])
    result: list[dict[str, Any]] = []
    for raw in observation.get("detector_values", []):
        if not isinstance(raw, Mapping):
            raise ObservationProjectionError("detector_values rows must be mappings")
        record = dict(raw)
        operator_id = str(record.get("operator_id", ""))
        if operator_id not in operators:
            raise ObservationProjectionError(f"unknown observation operator: {operator_id!r}")
        kind = str(record.get("measurement_kind", ""))
        observed = _finite(record.get("observed_at_sec"), "observed_at_sec")
        if observed < start - 1.0e-9 or observed > end + 1.0e-9 or observed > sim_time + 1.0e-9:
            raise ObservationProjectionError("detector timestamp outside captured_interval")
        record["value"] = _canonical_measurement(
            kind, _finite(record.get("value"), "detector value"), str(record.get("unit", ""))
        )
        if kind in {"count", "flow"}:
            record["duration_sec"] = _record_duration(record)
        result.append(record)
    return result


def _canonical_measurement(kind: str, value: float, unit: str) -> float:
    converters = {
        ("count", "veh"): lambda x: x,
        ("flow", "veh_per_sec"): lambda x: x,
        ("flow", "veh_per_hour"): lambda x: x / 3600.0,
        ("speed", "m_per_sec"): lambda x: x,
        ("speed", "km_per_hour"): lambda x: x / 3.6,
        ("occupancy", "fraction"): lambda x: x,
        ("occupancy", "percent"): lambda x: x / 100.0,
        ("queue_length", "m"): lambda x: x,
        ("queue_length", "km"): lambda x: x * 1000.0,
        ("travel_time", "sec"): lambda x: x,
        ("travel_time", "msec"): lambda x: x / 1000.0,
    }
    converter = converters.get((kind, unit))
    if converter is None:
        raise ObservationProjectionError(f"unsupported unit {unit!r} for {kind!r}")
    converted = converter(value)
    if converted < 0.0:
        raise ObservationProjectionError(f"negative {kind} measurement")
    if kind == "occupancy" and converted > 1.0 + 1.0e-9:
        raise ObservationProjectionError("occupancy exceeds 100 percent")
    return converted


def _record_duration(record: Mapping[str, Any]) -> float | None:
    left, right = record.get("interval_start_sec"), record.get("interval_end_sec")
    if left is None or right is None:
        return None
    duration = _finite(right, "interval_end_sec") - _finite(left, "interval_start_sec")
    if duration <= 0.0:
        raise ObservationProjectionError("measurement interval must be positive")
    return duration


def _aggregate_records(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    by_kind: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        by_kind[str(record["measurement_kind"])].append(record)
    result: dict[str, dict[str, Any]] = {}
    for kind in sorted(by_kind):
        rows = by_kind[kind]
        if kind == "count":
            value = sum(float(row["value"]) for row in rows)
            duration = sum(float(row["duration_sec"] or 0.0) for row in rows)
            result[kind] = {"value": value, "duration_sec": duration or None, "records": len(rows)}
        else:
            result[kind] = {
                "value": sum(float(row["value"]) for row in rows) / len(rows),
                "duration_sec": None,
                "records": len(rows),
            }
    return result


def _operator_cells(
    operator: Mapping[str, Any], cells: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    explicit = [str(item) for item in operator.get("cell_ids", [])]
    if explicit:
        unknown = sorted(set(explicit) - set(cells))
        if unknown:
            raise ObservationProjectionError(f"operator references unknown cells: {unknown}")
        return sorted(set(explicit))
    kind = operator.get("kind")
    if kind == "data_collection_point":
        lane_id = operator.get("lane_ref", {}).get("lane_id")
        position = float(operator.get("position_m", 0.0))
        matches = [
            cell_id
            for cell_id, cell in cells.items()
            if lane_id in cell.get("lanes", [])
            and float(cell["start_position_m"]) - 1.0e-9 <= position
            <= float(cell["end_position_m"]) + 1.0e-9
        ]
        return sorted(matches, key=lambda item: (int(cells[item].get("ordered_index", 0)), item))[:1]
    link_no = None
    if kind == "queue_counter":
        link_no = str(operator.get("link_no"))
    elif kind == "travel_time_measurement":
        endpoints = [operator.get("start"), operator.get("end")]
        link_nos = {str(item.get("link_no")) for item in endpoints if isinstance(item, Mapping)}
        return sorted(
            cell_id
            for cell_id, cell in cells.items()
            if _cell_link_no(cell) in link_nos
        )
    if link_no is not None:
        return sorted(
            (cell_id for cell_id, cell in cells.items() if _cell_link_no(cell) == link_no),
            key=lambda item: (str(cells[item].get("lane_group_id")), int(cells[item].get("ordered_index", 0))),
        )
    return []


def _add_operator_candidates(
    candidates: dict[str, list[dict[str, Any]]],
    target_cells: list[str],
    operator: Mapping[str, Any],
    values: Mapping[str, Mapping[str, Any]],
    manifest: Mapping[str, Any],
    cfg: Mapping[str, Any],
) -> None:
    if not target_cells:
        return
    operator_id = str(operator["id"])
    kind = operator.get("kind")
    if kind == "queue_counter" and "queue_length" in values:
        lane_count = float(cfg.get("queue_lane_count_by_operator", {}).get(operator_id, cfg["queue_lane_count"]))
        queued = values["queue_length"]["value"] * lane_count / float(cfg["jam_spacing_m_per_veh"])
        remaining = queued
        for cell_id in reversed(target_cells):
            storage = float(_cells_by_id(manifest)[cell_id].get("storage_veh", 0.0))
            assigned = min(storage, remaining)
            candidates[cell_id].append(_candidate(assigned, 0.0, operator_id, "queue_length", "direct_queue"))
            remaining -= assigned
            if remaining <= 1.0e-12:
                break
        return

    speed = values.get("speed", {}).get("value")
    if speed is None and kind == "travel_time_measurement" and "travel_time" in values:
        distance = sum(float(_cells_by_id(manifest)[cell_id]["length_m"]) for cell_id in target_cells)
        travel_time = float(values["travel_time"]["value"])
        speed = distance / travel_time if travel_time > 0.0 else None
    flow = values.get("flow", {}).get("value")
    if flow is None and "count" in values and values["count"].get("duration_sec"):
        flow = float(values["count"]["value"]) / float(values["count"]["duration_sec"])
    occupancy = values.get("occupancy", {}).get("value")
    for cell_id in target_cells:
        cell = _cells_by_id(manifest)[cell_id]
        lane_count = max(1.0, float(cell.get("lane_count", 1.0)))
        length = float(cell["length_m"])
        storage = float(cell["storage_veh"])
        count = None
        method = None
        if occupancy is not None:
            count = float(occupancy) * storage
            method = "occupancy_to_density"
        elif flow is not None and speed is not None and speed > 1.0e-6:
            count = float(flow) / float(speed) * length
            method = "flow_speed_to_density"
        if count is not None or speed is not None:
            candidates[cell_id].append(
                _candidate(count, speed, operator_id, str(kind), method or "speed_only", lane_count)
            )


def _candidate(
    count: float | None,
    speed: float | None,
    operator_id: str,
    measurement_kind: str,
    method: str,
    lane_count: float = 1.0,
) -> dict[str, Any]:
    return {
        "vehicle_count_veh": count,
        "speed_mps": speed,
        "operator_id": operator_id,
        "measurement_kind": measurement_kind,
        "method": method,
        "lane_count": lane_count,
    }


def _combine_candidates(
    cell: Mapping[str, Any],
    candidates: list[Mapping[str, Any]],
    previous: Mapping[str, float] | None,
    cfg: Mapping[str, Any],
) -> tuple[dict[str, float], list[dict[str, Any]], float, str | None]:
    storage = float(cell["storage_veh"])
    v_free = float(cell.get("parameter_placeholders", {}).get("v_free_mps", cfg["default_v_free_mps"]))
    count_values = [float(item["vehicle_count_veh"]) for item in candidates if item.get("vehicle_count_veh") is not None]
    speed_values = [float(item["speed_mps"]) for item in candidates if item.get("speed_mps") is not None]
    fallback = None
    if count_values:
        count = sum(count_values) / len(count_values)
        variance = float(cfg["observed_count_variance_veh2"] if any(item.get("method") == "direct_queue" for item in candidates) else cfg["reconstructed_count_variance_veh2"])
    elif previous is not None:
        count = float(previous["vehicle_count_veh"])
        variance = float(cfg["fallback_count_variance_veh2"])
        fallback = "previous_estimate"
    else:
        count = 0.0
        variance = float(cfg["fallback_count_variance_veh2"])
        fallback = "zero_prior"
    if speed_values:
        speed = sum(speed_values) / len(speed_values)
    elif previous is not None:
        speed = float(previous["speed_mps"])
    else:
        speed = v_free
    count = min(storage, max(0.0, count))
    speed = min(v_free, max(float(cfg["minimum_speed_mps"]), speed))
    sources = [
        {
            "operator_id": str(item["operator_id"]),
            "measurement_kind": str(item["measurement_kind"]),
            "method": str(item["method"]),
        }
        for item in sorted(candidates, key=lambda item: (str(item["operator_id"]), str(item["measurement_kind"]), str(item["method"])))
    ]
    if fallback:
        sources.append({"source": fallback})
    return {"vehicle_count_veh": count, "speed_mps": speed}, sources, variance, fallback


def _previous_estimates(
    previous_state: Mapping[str, Any] | None,
    cells: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, float]]:
    if previous_state is None:
        return {}
    result: dict[str, dict[str, float]] = {}
    urban = previous_state.get("urban", {})
    freeway = previous_state.get("freeway", {})
    stocks = previous_state.get("stocks", {})
    for cell_id in cells:
        stock_id = urban.get("cell_stock_id", {}).get(cell_id) or freeway.get("cell_stock_id", {}).get(cell_id)
        stock = stocks.get(stock_id, {})
        if "vehicle_count_veh" not in stock:
            continue
        speed = urban.get("speed_mps", {}).get(cell_id, freeway.get("speed_mps", {}).get(cell_id, 0.0))
        result[cell_id] = {
            "vehicle_count_veh": float(stock["vehicle_count_veh"]),
            "speed_mps": float(speed),
        }
    return result


def _build_state(
    manifest: Mapping[str, Any],
    sim_time: float,
    estimates: Mapping[str, Mapping[str, float]],
    mode: str,
    signal_readback: Any,
    boundary_values: Any,
    estimation: dict[str, Any],
) -> dict[str, Any]:
    cells = _cells_by_id(manifest)
    stocks: dict[str, dict[str, Any]] = {}
    urban_ids: dict[str, str] = {}
    freeway_ids: dict[str, str] = {}
    urban_density: dict[str, float] = {}
    urban_speed: dict[str, float] = {}
    freeway_density: dict[str, float] = {}
    freeway_speed: dict[str, float] = {}
    for cell_id in sorted(cells):
        cell = cells[cell_id]
        is_freeway = str(cell.get("model_type", "")).lower() in {"metanet", "freeway", "freeway_metanet"}
        domain = "freeway" if is_freeway else "urban"
        stock_id = _cell_stock_id(cell_id, cell)
        count = float(estimates[cell_id]["vehicle_count_veh"])
        speed = float(estimates[cell_id]["speed_mps"])
        density = count / (float(cell["length_m"]) * max(1.0, float(cell.get("lane_count", 1.0))))
        stocks[stock_id] = {
            "owner_kind": f"{domain}_cell",
            "owner_id": cell_id,
            "vehicle_count_veh": count,
        }
        if is_freeway:
            freeway_ids[cell_id] = stock_id
            freeway_density[cell_id] = density
            freeway_speed[cell_id] = speed
        else:
            urban_ids[cell_id] = stock_id
            urban_density[cell_id] = density
            urban_speed[cell_id] = speed

    estimation = dict(estimation)
    estimation.update({"mode": mode, "projector_version": PROJECTOR_VERSION})
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "topology_hash": str(manifest["topology_hash"]),
        "state_hash": None,
        "sim_time_sec": sim_time,
        "stocks": stocks,
        "freeway": {
            "density_vehpmpl": freeway_density,
            "speed_mps": freeway_speed,
            "cell_stock_id": freeway_ids,
            "origin_queue_stock_id": {},
        },
        "urban": {
            "cell_stock_id": urban_ids,
            "density_vehpmpl": urban_density,
            "speed_mps": urban_speed,
            "commodity_fraction": {},
        },
        "connectors": {"cumulative_flow_veh": {}},
        "ramps": {"queue_stock_id": {}, "storage_stock_id": {}},
        "boundaries": _project_boundaries(manifest, boundary_values),
        "signals": _project_signals(manifest, signal_readback),
        "estimation": estimation,
    }


def _project_signals(manifest: Mapping[str, Any], raw: Any) -> dict[str, Any]:
    groups = {str(item["id"]) for item in manifest.get("signal_groups", [])}
    controllers = {str(item["id"]): item for item in manifest.get("signal_controllers", [])}
    sg_state: dict[str, dict[str, Any]] = {}
    for row in raw or []:
        controller_id, sg_id = str(row.get("controller_id", "")), str(row.get("sg_id", ""))
        if controller_id not in controllers or sg_id not in groups:
            raise ObservationProjectionError("unknown signal readback reference")
        display = str(row.get("display", ""))
        if display not in {"GREEN", "AMBER", "RED"}:
            raise ObservationProjectionError("invalid signal display")
        sg_state[sg_id] = {
            "current_display": display,
            "current_event_id": str(row.get("event_id", "readback")),
            "event_elapsed_sec": float(row.get("event_elapsed_sec", 0.0)),
            "cycle_position_sec": row.get("cycle_position_sec"),
        }
    return {
        "active_schedule_id": {},
        "pending_schedule_id": {controller_id: None for controller_id in sorted(controllers)},
        "sg_state": sg_state,
    }


def _project_boundaries(manifest: Mapping[str, Any], raw: Any) -> dict[str, Any]:
    boundary_ids = {str(item["id"]) for item in manifest.get("boundaries", [])}
    cumulative_admitted = {item: 0.0 for item in sorted(boundary_ids)}
    for row in raw or []:
        boundary_id = str(row.get("boundary_id", ""))
        if boundary_id not in boundary_ids:
            raise ObservationProjectionError(f"unknown boundary: {boundary_id!r}")
        if row.get("measurement_kind") == "admitted_flow":
            value = _canonical_boundary_value(float(row["value"]), str(row.get("unit", "")))
            duration = _record_duration(row)
            if duration is not None:
                cumulative_admitted[boundary_id] += value * duration
    return {
        "source_queue_stock_id": {},
        "cumulative_admitted_veh": cumulative_admitted,
    }


def _canonical_boundary_value(value: float, unit: str) -> float:
    if unit == "veh_per_sec":
        return value
    if unit == "veh_per_hour":
        return value / 3600.0
    raise ObservationProjectionError(f"unsupported boundary flow unit: {unit!r}")


def _finish_state(state: dict[str, Any]) -> dict[str, Any]:
    payload = dict(state)
    payload.pop("state_hash", None)
    state["state_hash"] = canonical_json_sha256(payload)
    return state


def _diagonal_covariance(
    estimates: Mapping[str, Mapping[str, float]],
    cells: Mapping[str, Mapping[str, Any]],
    variance: float,
) -> dict[str, Any]:
    cell_ids = sorted(estimates)
    return {
        "schema_version": "diagonal-covariance/v1",
        "state_ordering": [_cell_stock_id(cell_id, cells[cell_id]) for cell_id in cell_ids],
        "diagonal_vehicle_count_variance_veh2": [variance for _ in cell_ids],
    }


def _cells_by_id(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(cell["id"]): cell for cell in manifest.get("cells", [])}


def _cell_stock_id(cell_id: str, cell: Mapping[str, Any]) -> str:
    is_freeway = str(cell.get("model_type", "")).lower() in {
        "metanet",
        "freeway",
        "freeway_metanet",
    }
    domain = "freeway" if is_freeway else "urban"
    return f"stock:{domain}-cell:{cell_id}"


def _cell_link_no(cell: Mapping[str, Any]) -> str:
    lane_group = str(cell.get("lane_group_id", ""))
    parts = lane_group.split(":")
    return parts[2] if len(parts) >= 3 and parts[:2] == ["lg", "link"] else ""


def _oracle_count(row: Mapping[str, Any]) -> float:
    if "vehicle_count_veh" in row:
        return _finite(row["vehicle_count_veh"], "vehicle_count_veh")
    if row.get("vehicle_count_unit") == "veh" and "vehicle_count" in row:
        return _finite(row["vehicle_count"], "vehicle_count")
    raise ObservationProjectionError("oracle cell row has no explicitly unit-tagged count")


def _oracle_speed(row: Mapping[str, Any]) -> float:
    if "speed_mps" in row:
        return _finite(row["speed_mps"], "speed_mps")
    unit = str(row.get("speed_unit", ""))
    if "speed" in row and unit in {"m_per_sec", "km_per_hour"}:
        value = _finite(row["speed"], "speed")
        return value if unit == "m_per_sec" else value / 3.6
    raise ObservationProjectionError("oracle cell row has no explicitly unit-tagged speed")


def _finite(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ObservationProjectionError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ObservationProjectionError(f"{name} must be finite")
    return result
