"""Deterministic Phase 4 shadow-mode recording and G6/G7 validation."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping, Sequence

from .topology import CONTROLLED_UF_TO_SC, canonical_json_sha256, canonical_json_text


REPORT_SCHEMA_VERSION = "vissim-strict-shadow-report/v3"
RECORD_SCHEMA_VERSION = "vissim-strict-shadow-record/v2"
COM_READBACK_REPORT_SCHEMA_VERSION = "vissim-strict-com-readback-report/v2"
PASS = "PASS"
FAIL = "FAIL"
NOT_EVALUATED = "NOT_EVALUATED"
EXPECTED_AUTHORITY_CONTROLLER_COUNT = len(CONTROLLED_UF_TO_SC)

DEFAULT_THRESHOLDS = {
    "spearman_rho_min": 0.70,
    "top_action_pairwise_agreement_min": 0.80,
    "spillback_f1_initial_min": 0.80,
    "spillback_f1_release_min": 0.90,
    "decision_runtime_p95_sec_max": 30.0,
    "decision_runtime_hard_sec_max": 45.0,
    "fallback_rate_max_exclusive": 0.05,
    "silent_fallback_rate_max": 0.0,
    "stale_action_failures_max": 0,
    "readback_failures_max": 0,
}

_REQUIRED_FIELDS = (
    "schema_version",
    "decision_id",
    "candidate_id",
    "strict_predicted_objective",
    "strict_status",
    "strict_runtime_sec",
    "action_hash",
    "policy_hash",
    "build_hash",
    "action_schema_hash",
    "shadow_mode",
    "actuation_attempted",
    "stale_fault_injection_observed",
    "fallback_fault_injection_observed",
    "readback_fault_injection_observed",
)


class ShadowValidationError(ValueError):
    """Raised when a shadow record violates the input contract."""


def _finite_number(value: Any, field: str, *, nullable: bool = False) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ShadowValidationError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ShadowValidationError(f"{field} must be a finite number")
    return result


def _validate_hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ShadowValidationError(f"{field} must be a 64-character SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ShadowValidationError(f"{field} must be a 64-character SHA-256 hex digest") from exc
    return value.lower()


def validate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one candidate JSONL record."""

    missing = [field for field in _REQUIRED_FIELDS if field not in record]
    if missing:
        raise ShadowValidationError(f"missing required fields: {', '.join(missing)}")
    normalized = dict(record)
    if normalized["schema_version"] != RECORD_SCHEMA_VERSION:
        raise ShadowValidationError("unsupported shadow record schema_version")
    for field in ("decision_id", "candidate_id", "strict_status"):
        if not isinstance(normalized[field], str) or not normalized[field]:
            raise ShadowValidationError(f"{field} must be a non-empty string")
    normalized["strict_predicted_objective"] = _finite_number(
        normalized["strict_predicted_objective"],
        "strict_predicted_objective",
        nullable=normalized["strict_status"] != "OK",
    )
    normalized["strict_runtime_sec"] = _finite_number(normalized["strict_runtime_sec"], "strict_runtime_sec")
    if normalized["strict_runtime_sec"] < 0.0:
        raise ShadowValidationError("strict_runtime_sec must be non-negative")
    normalized["action_hash"] = _validate_hash(normalized["action_hash"], "action_hash")

    for field in (
        "topology_hash",
        "program_hash",
        "policy_hash",
        "build_hash",
        "action_schema_hash",
        "state_hash",
        "based_on_state_hash",
        "readback_action_hash",
    ):
        if field in normalized and normalized[field] is not None:
            normalized[field] = _validate_hash(normalized[field], field)
    for field in ("vissim_observed_objective", "decision_runtime_sec"):
        if field in normalized and normalized[field] is not None:
            normalized[field] = _finite_number(normalized[field], field)
            if field == "decision_runtime_sec" and normalized[field] < 0.0:
                raise ShadowValidationError("decision_runtime_sec must be non-negative")
    for field in (
        "strict_predicted_spillback",
        "vissim_observed_spillback",
        "fallback_required",
        "fallback_event_logged",
        "silent_fallback",
        "stale_action_failure",
        "stale_action_detected",
        "stale_action_rejected",
        "readback_ok",
        "actuation_attempted",
        "shadow_mode",
        "stale_fault_injection_observed",
        "fallback_fault_injection_observed",
        "readback_fault_injection_observed",
    ):
        if field in normalized and normalized[field] is not None and not isinstance(normalized[field], bool):
            raise ShadowValidationError(f"{field} must be boolean when provided")
    if normalized["shadow_mode"] is not True:
        raise ShadowValidationError("shadow records must declare shadow_mode=true")
    if normalized["actuation_attempted"] is not False:
        raise ShadowValidationError("shadow records must declare actuation_attempted=false")

    if normalized["stale_fault_injection_observed"]:
        for field in ("stale_action_detected", "stale_action_rejected", "stale_action_failure"):
            if not isinstance(normalized.get(field), bool):
                raise ShadowValidationError(
                    f"stale fault-injection evidence requires boolean {field}"
                )
        if normalized["stale_action_detected"] is not True:
            raise ShadowValidationError("stale fault injection must be detected")
        if normalized.get("state_hash") is None or normalized.get("based_on_state_hash") is None:
            raise ShadowValidationError("stale fault-injection evidence requires both state hashes")
        if normalized["state_hash"] == normalized["based_on_state_hash"]:
            raise ShadowValidationError("stale fault-injection evidence requires a stale hash mismatch")
    if normalized["fallback_fault_injection_observed"]:
        if normalized.get("fallback_required") is not True:
            raise ShadowValidationError("fallback fault-injection evidence requires fallback_required=true")
        if not isinstance(normalized.get("fallback_event_logged"), bool):
            raise ShadowValidationError(
                "fallback fault-injection evidence requires boolean fallback_event_logged"
            )
    if normalized["readback_fault_injection_observed"] and not isinstance(
        normalized.get("readback_ok"), bool
    ):
        raise ShadowValidationError(
            "readback fault-injection evidence requires boolean readback_ok"
        )
    return normalized


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load validated candidate records from JSON Lines."""

    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ShadowValidationError(f"line {line_no}: invalid JSON: {exc.msg}") from exc
            if not isinstance(raw, dict):
                raise ShadowValidationError(f"line {line_no}: record must be a JSON object")
            try:
                record = validate_record(raw)
            except ShadowValidationError as exc:
                raise ShadowValidationError(f"line {line_no}: {exc}") from exc
            key = (record["decision_id"], record["candidate_id"])
            if key in seen:
                raise ShadowValidationError(f"line {line_no}: duplicate decision/candidate key {key!r}")
            seen.add(key)
            records.append(record)
    return records


def _average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        average_rank = ((cursor + 1) + end) / 2.0
        for position in range(cursor, end):
            ranks[order[position]] = average_rank
        cursor = end
    return ranks


def spearman_rank_correlation(left: Sequence[float], right: Sequence[float]) -> float | None:
    """Calculate Spearman rho using average ranks for ties."""

    if len(left) != len(right):
        raise ShadowValidationError("Spearman inputs must have equal length")
    if len(left) < 2:
        return None
    x_rank = _average_ranks(left)
    y_rank = _average_ranks(right)
    x_mean = statistics.fmean(x_rank)
    y_mean = statistics.fmean(y_rank)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_rank, y_rank))
    x_scale = sum((x - x_mean) ** 2 for x in x_rank)
    y_scale = sum((y - y_mean) ** 2 for y in y_rank)
    if x_scale == 0.0 or y_scale == 0.0:
        return None
    return numerator / math.sqrt(x_scale * y_scale)


def _sign(value: float) -> int:
    return (value > 0.0) - (value < 0.0)


def _quantile(values: Sequence[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _confusion_metrics(tp: int, fp: int, fn: int, tn: int) -> dict[str, Any]:
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    if precision is None or recall is None or precision + recall == 0.0:
        f1 = 0.0 if (tp + fp + fn) > 0 else None
    else:
        f1 = 2.0 * precision * recall / (precision + recall)
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "observation_count": tp + fp + fn + tn,
    }


def _criterion(name: str, value: Any, operator: str, threshold: Any, *, evaluated: bool = True) -> dict[str, Any]:
    if not evaluated or value is None:
        verdict = NOT_EVALUATED
    elif operator == ">=":
        verdict = PASS if value >= threshold else FAIL
    elif operator == "<=":
        verdict = PASS if value <= threshold else FAIL
    elif operator == "<":
        verdict = PASS if value < threshold else FAIL
    else:
        raise AssertionError(f"unsupported criterion operator: {operator}")
    return {"name": name, "value": value, "operator": operator, "threshold": threshold, "verdict": verdict}


def _gate(criteria: Sequence[Mapping[str, Any]]) -> str:
    verdicts = {criterion["verdict"] for criterion in criteria}
    if FAIL in verdicts:
        return FAIL
    if NOT_EVALUATED in verdicts:
        return NOT_EVALUATED
    return PASS


def _digest_payload(payload: Mapping[str, Any]) -> str:
    return canonical_json_sha256(dict(payload))


def _with_report_digest(report: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(report)
    output.pop("report_digest_sha256", None)
    output["report_digest_sha256"] = _digest_payload(output)
    return output


def verify_report_digest(report: Mapping[str, Any]) -> bool:
    expected = report.get("report_digest_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        return False
    payload = dict(report)
    payload.pop("report_digest_sha256", None)
    return _digest_payload(payload) == expected.lower()


def evaluate_shadow_records(
    records: Iterable[Mapping[str, Any]],
    *,
    thresholds: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Compute deterministic G6/G7 metrics and gate verdicts."""

    limits = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        unknown = sorted(set(thresholds) - set(limits))
        if unknown:
            raise ShadowValidationError(f"unknown thresholds: {', '.join(unknown)}")
        limits.update(thresholds)

    normalized = [validate_record(record) for record in records]
    topology_hashes = sorted({str(record.get("topology_hash", "")) for record in normalized if record.get("topology_hash")})
    program_hashes = sorted({str(record.get("program_hash", "")) for record in normalized if record.get("program_hash")})
    action_hashes = sorted({str(record["action_hash"]) for record in normalized})
    policy_hashes = sorted({str(record["policy_hash"]) for record in normalized})
    build_hashes = sorted({str(record["build_hash"]) for record in normalized})
    action_schema_hashes = sorted({str(record["action_schema_hash"]) for record in normalized})
    provenance_complete = (
        bool(normalized)
        and len(topology_hashes) == 1
        and len(policy_hashes) == 1
        and len(build_hashes) == 1
        and len(action_schema_hashes) == 1
        and all(record.get("topology_hash") and record.get("program_hash") for record in normalized)
    )
    seen: set[tuple[str, str]] = set()
    by_decision: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in normalized:
        key = (record["decision_id"], record["candidate_id"])
        if key in seen:
            raise ShadowValidationError(f"duplicate decision/candidate key {key!r}")
        seen.add(key)
        by_decision[record["decision_id"]].append(record)

    decision_reports: list[dict[str, Any]] = []
    rhos: list[float] = []
    pairwise_agree = 0
    pairwise_total = 0
    spillback_counts = [0, 0, 0, 0]  # TP, FP, FN, TN
    ranking_oracle_complete = bool(by_decision)
    spillback_oracle_complete = bool(by_decision)
    decision_runtimes: list[float] = []
    fallback_decisions = 0
    silent_fallback_decisions = 0
    stale_failures = 0
    stale_observations = 0
    readback_failures = 0
    readback_observations = 0
    fallback_fault_observations = 0

    for decision_id in sorted(by_decision):
        candidates = sorted(by_decision[decision_id], key=lambda item: item["candidate_id"])
        eligible = [item for item in candidates if item["strict_predicted_objective"] is not None]
        complete_ranking = len(eligible) == len(candidates) and len(eligible) >= 2 and all(
            item.get("vissim_observed_objective") is not None for item in eligible
        )
        if not complete_ranking:
            ranking_oracle_complete = False
            rho = None
            local_agree = 0
            local_total = 0
            ranking_status = NOT_EVALUATED
        else:
            predicted = [float(item["strict_predicted_objective"]) for item in eligible]
            observed = [float(item["vissim_observed_objective"]) for item in eligible]
            rho = spearman_rank_correlation(predicted, observed)
            if rho is not None:
                rhos.append(rho)
            else:
                ranking_oracle_complete = False
            top = min(eligible, key=lambda item: (item["strict_predicted_objective"], item["candidate_id"]))
            local_agree = 0
            local_total = 0
            for item in eligible:
                if item is top:
                    continue
                predicted_order = _sign(top["strict_predicted_objective"] - item["strict_predicted_objective"])
                observed_order = _sign(top["vissim_observed_objective"] - item["vissim_observed_objective"])
                local_agree += int(predicted_order == observed_order)
                local_total += 1
            pairwise_agree += local_agree
            pairwise_total += local_total
            local_pairwise = _ratio(local_agree, local_total)
            ranking_status = (
                PASS
                if rho is not None
                and rho >= limits["spearman_rho_min"]
                and local_pairwise is not None
                and local_pairwise >= limits["top_action_pairwise_agreement_min"]
                else FAIL
            )

        local_spillback = [0, 0, 0, 0]
        labelled = [item for item in candidates if "strict_predicted_spillback" in item]
        if not labelled or any(item.get("vissim_observed_spillback") is None for item in labelled):
            spillback_oracle_complete = False
        else:
            for item in labelled:
                predicted_spillback = item["strict_predicted_spillback"]
                observed_spillback = item["vissim_observed_spillback"]
                index = 0 if predicted_spillback and observed_spillback else 1 if predicted_spillback else 2 if observed_spillback else 3
                local_spillback[index] += 1
                spillback_counts[index] += 1

        runtime_values = {
            float(item["decision_runtime_sec"])
            for item in candidates
            if item.get("decision_runtime_sec") is not None
        }
        if len(runtime_values) > 1:
            raise ShadowValidationError(f"decision {decision_id!r} has inconsistent decision_runtime_sec values")
        decision_runtime = next(iter(runtime_values)) if runtime_values else max(
            float(item["strict_runtime_sec"]) for item in candidates
        )
        decision_runtimes.append(decision_runtime)

        fallback = any(bool(item.get("fallback_required", False)) for item in candidates)
        silent = any(bool(item.get("silent_fallback", False)) for item in candidates) or (
            fallback and not any(bool(item.get("fallback_event_logged", False)) for item in candidates)
        )
        fallback_decisions += int(fallback)
        silent_fallback_decisions += int(silent)

        local_stale_failures = 0
        local_readback_failures = 0
        local_stale_observations = 0
        local_fallback_fault_observations = 0
        local_readback_observations = 0
        for item in candidates:
            if item["stale_fault_injection_observed"]:
                stale_observations += 1
                local_stale_observations += 1
                hash_mismatch = (
                    item.get("based_on_state_hash") is not None
                    and item.get("state_hash") is not None
                    and item["based_on_state_hash"] != item["state_hash"]
                )
                stale_detected = bool(item.get("stale_action_detected", False)) or hash_mismatch
                failed = bool(item.get("stale_action_failure", False))
                failed = failed or (stale_detected and not bool(item.get("stale_action_rejected", False)))
                local_stale_failures += int(failed)
            if item["fallback_fault_injection_observed"]:
                fallback_fault_observations += 1
                local_fallback_fault_observations += 1
            if item["readback_fault_injection_observed"]:
                readback_observations += 1
                local_readback_observations += 1
                failed = item.get("readback_ok") is False
                if item.get("readback_action_hash") is not None:
                    failed = failed or item["readback_action_hash"] != item["action_hash"]
                local_readback_failures += int(failed)
        stale_failures += local_stale_failures
        readback_failures += local_readback_failures

        decision_reports.append(
            {
                "decision_id": decision_id,
                "candidate_count": len(candidates),
                "ranking_status": ranking_status,
                "spearman_rho": rho,
                "top_action_pairwise": {
                    "agreement_count": local_agree,
                    "comparison_count": local_total,
                    "agreement": _ratio(local_agree, local_total),
                },
                "spillback": _confusion_metrics(*local_spillback),
                "runtime_sec": decision_runtime,
                "runtime_source": "decision_runtime_sec" if runtime_values else "max_candidate_runtime_sec",
                "fallback_required": fallback,
                "silent_fallback": silent,
                "stale_fault_injection_observations": local_stale_observations,
                "fallback_fault_injection_observations": local_fallback_fault_observations,
                "readback_fault_injection_observations": local_readback_observations,
                "stale_action_failures": local_stale_failures,
                "readback_failures": local_readback_failures,
            }
        )

    spillback = _confusion_metrics(*spillback_counts)
    aggregate_rho = statistics.fmean(rhos) if rhos else None
    pairwise = _ratio(pairwise_agree, pairwise_total)
    fallback_rate = _ratio(fallback_decisions, len(by_decision))
    silent_fallback_rate = _ratio(silent_fallback_decisions, len(by_decision))
    runtime = {
        "decision_count": len(decision_runtimes),
        "p50_sec": _quantile(decision_runtimes, 0.50),
        "p95_sec": _quantile(decision_runtimes, 0.95),
        "max_sec": max(decision_runtimes) if decision_runtimes else None,
    }

    g6_common = [
        _criterion("provenance_complete", int(provenance_complete), ">=", 1),
        _criterion(
            "spearman_rho",
            aggregate_rho,
            ">=",
            limits["spearman_rho_min"],
            evaluated=ranking_oracle_complete,
        ),
        _criterion(
            "top_action_pairwise_agreement",
            pairwise,
            ">=",
            limits["top_action_pairwise_agreement_min"],
            evaluated=ranking_oracle_complete,
        ),
    ]
    g6_initial = g6_common + [
        _criterion(
            "spillback_f1",
            spillback["f1"],
            ">=",
            limits["spillback_f1_initial_min"],
            evaluated=spillback_oracle_complete,
        )
    ]
    g6_release = g6_common + [
        _criterion(
            "spillback_f1",
            spillback["f1"],
            ">=",
            limits["spillback_f1_release_min"],
            evaluated=spillback_oracle_complete,
        )
    ]
    has_runtime = bool(decision_runtimes)
    shadow_record_count = sum(record["shadow_mode"] is True for record in normalized)
    actuation_attempt_count = sum(record["actuation_attempted"] is True for record in normalized)
    g7_criteria = [
        _criterion("shadow_mode_record_count", shadow_record_count, ">=", len(normalized), evaluated=bool(normalized)),
        _criterion("actuation_attempt_count", actuation_attempt_count, "<=", 0, evaluated=bool(normalized)),
        _criterion("decision_runtime_p95_sec", runtime["p95_sec"], "<=", limits["decision_runtime_p95_sec_max"], evaluated=has_runtime),
        _criterion("decision_runtime_max_sec", runtime["max_sec"], "<=", limits["decision_runtime_hard_sec_max"], evaluated=has_runtime),
        _criterion("fallback_rate", fallback_rate, "<", limits["fallback_rate_max_exclusive"], evaluated=has_runtime),
        _criterion("silent_fallback_rate", silent_fallback_rate, "<=", limits["silent_fallback_rate_max"], evaluated=has_runtime),
        _criterion("stale_fault_injection_observations", stale_observations, ">=", 1, evaluated=stale_observations > 0),
        _criterion("fallback_fault_injection_observations", fallback_fault_observations, ">=", 1, evaluated=fallback_fault_observations > 0),
        _criterion("readback_fault_injection_observations", readback_observations, ">=", 1, evaluated=readback_observations > 0),
        _criterion("stale_action_failures", stale_failures, "<=", limits["stale_action_failures_max"], evaluated=stale_observations > 0),
        _criterion("readback_failures", readback_failures, "<=", limits["readback_failures_max"], evaluated=readback_observations > 0),
    ]

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "record_count": len(normalized),
        "decision_count": len(by_decision),
        "aggregation_policy": {
            "spearman": "macro_mean_of_complete_decisions",
            "top_action_pairwise": "micro_agreement_for_deterministic_predicted_top",
            "spillback": "micro_confusion_matrix",
            "decision_runtime_fallback": "max_candidate_runtime_when_decision_runtime_missing",
        },
        "thresholds": limits,
        "provenance": {
            "complete": provenance_complete,
            "topology_hash": topology_hashes[0] if len(topology_hashes) == 1 else "",
            "program_hashes": program_hashes,
            "action_hashes": action_hashes,
            "action_set_sha256": _digest_payload({"action_hashes": action_hashes}),
            "policy_hash": policy_hashes[0] if len(policy_hashes) == 1 else "",
            "build_hash": build_hashes[0] if len(build_hashes) == 1 else "",
            "action_schema_hash": action_schema_hashes[0] if len(action_schema_hashes) == 1 else "",
        },
        "per_decision": decision_reports,
        "aggregate": {
            "spearman_rho": aggregate_rho,
            "spearman_decision_count": len(rhos),
            "ranking_oracle_complete": ranking_oracle_complete,
            "top_action_pairwise": {
                "agreement_count": pairwise_agree,
                "comparison_count": pairwise_total,
                "agreement": pairwise,
            },
            "spillback": spillback,
            "spillback_oracle_complete": spillback_oracle_complete,
            "runtime": runtime,
            "fallback_decisions": fallback_decisions,
            "fallback_rate": fallback_rate,
            "silent_fallback_decisions": silent_fallback_decisions,
            "silent_fallback_rate": silent_fallback_rate,
            "shadow_contract": {
                "shadow_mode_record_count": shadow_record_count,
                "actuation_attempt_count": actuation_attempt_count,
            },
            "fault_injection": {
                "stale_observation_count": stale_observations,
                "fallback_observation_count": fallback_fault_observations,
                "readback_observation_count": readback_observations,
            },
            "stale_action": {"observation_count": stale_observations, "failure_count": stale_failures},
            "readback": {"observation_count": readback_observations, "failure_count": readback_failures},
        },
        "gates": {
            "g6_initial": {"verdict": _gate(g6_initial), "criteria": g6_initial},
            "g6_release": {"verdict": _gate(g6_release), "criteria": g6_release},
            "g7_shadow_runtime": {"verdict": _gate(g7_criteria), "criteria": g7_criteria},
        },
    }
    return _with_report_digest(report)


def evaluate_com_readback_records(
    records: Iterable[Mapping[str, Any]],
    *,
    expected_authority: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    """Aggregate G8 evidence with exact SC/SG coverage for every promoted interval."""

    authority = {
        str(sc_no): sorted({int(sg_no) for sg_no in sg_nos})
        for sc_no, sg_nos in sorted(expected_authority.items(), key=lambda item: int(item[0]))
    }
    if len(authority) != EXPECTED_AUTHORITY_CONTROLLER_COUNT or any(not sg_nos for sg_nos in authority.values()):
        raise ShadowValidationError(
            "G8 expected_authority must contain exactly "
            f"{EXPECTED_AUTHORITY_CONTROLLER_COUNT} non-empty controllers"
        )
    expected_pairs = {(sc_no, sg_no) for sc_no, sg_nos in authority.items() for sg_no in sg_nos}

    normalized: list[dict[str, Any]] = []
    coverage: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)
    evidence_intervals: set[tuple[str, str]] = set()
    release_coverage: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)
    action_parent_intervals: set[tuple[str, str]] = set()
    for index, raw in enumerate(records):
        record = dict(raw)
        for field in (
            "topology_hash", "program_hash", "action_hash", "action_set_sha256",
            "runtime_action_hash", "policy_hash", "build_hash", "action_schema_hash",
            "runtime_action_hmac_sha256",
            "csv_payload_sha256", "envelope_hmac_sha256",
            "row_contract_sha256",
        ):
            if field not in record:
                raise ShadowValidationError(f"COM record {index} missing {field}")
            record[field] = _validate_hash(record[field], field)
        for field in (
            "sc_no", "sg_no", "requested_state", "state_readback", "interval_id",
            "evidence_kind", "run_id", "build_id", "network_id", "seed", "demand_identity",
        ):
            if str(record.get(field, "")).strip() == "":
                raise ShadowValidationError(f"COM record {index} missing {field}")
        record["sc_no"] = str(record["sc_no"])
        record["sg_no"] = int(record["sg_no"])
        record["interval_id"] = str(record["interval_id"])
        record["evidence_kind"] = str(record["evidence_kind"]).lower()
        if record["evidence_kind"] not in {"sigstate", "contr_by_com", "native_release"}:
            raise ShadowValidationError(f"COM record {index} has invalid evidence_kind")
        singleton_set_hash = _digest_payload({"action_hashes": [record["action_hash"]]})
        if record["action_set_sha256"] != singleton_set_hash:
            raise ShadowValidationError(f"COM record {index} action_set_sha256 mismatch")
        if not isinstance(record.get("contr_by_com_readback"), bool):
            raise ShadowValidationError(f"COM record {index} contr_by_com_readback must be boolean")
        if not isinstance(record.get("contr_by_com_requested"), bool):
            raise ShadowValidationError(f"COM record {index} contr_by_com_requested must be boolean")
        if not isinstance(record.get("envelope_hmac_valid"), bool):
            raise ShadowValidationError(f"COM record {index} envelope_hmac_valid must be boolean")
        requested = str(record["requested_state"]).strip().upper()
        readback = str(record["state_readback"]).strip().upper()
        record["readback_ok"] = bool(record.get("readback_ok")) and requested == readback
        interval_key = (record["runtime_action_hash"], record["interval_id"])
        if record["evidence_kind"] == "native_release":
            parent_runtime = str(record.get("parent_runtime_action_hash", "")).strip()
            parent_interval = str(record.get("parent_action_interval_id", "")).strip()
            if parent_runtime != record["runtime_action_hash"] or not parent_interval:
                raise ShadowValidationError(f"COM record {index} native release parent mismatch")
            release_coverage[(parent_runtime, parent_interval)].append((record["sc_no"], record["sg_no"]))
        else:
            evidence_intervals.add(interval_key)
            action_parent_intervals.add((record["runtime_action_hash"], record["interval_id"].split(":tick=", 1)[0]))
        if record["evidence_kind"] == "sigstate":
            record["readback_ok"] = (
                record["readback_ok"]
                and record["contr_by_com_requested"] is True
                and record["contr_by_com_readback"] is True
            )
            coverage[interval_key].append(
                (record["sc_no"], record["sg_no"])
            )
        normalized.append(record)

    missing_count = 0
    duplicate_count = 0
    extra_count = 0
    interval_reports: list[dict[str, Any]] = []
    for runtime_action_hash, interval_id in sorted(evidence_intervals):
        observed = coverage.get((runtime_action_hash, interval_id), [])
        observed_set = set(observed)
        missing = sorted(expected_pairs - observed_set, key=lambda item: (int(item[0]), item[1]))
        extra = sorted(observed_set - expected_pairs, key=lambda item: (int(item[0]), item[1]))
        duplicate = len(observed) - len(observed_set)
        missing_count += len(missing)
        extra_count += len(extra)
        duplicate_count += duplicate
        interval_reports.append({
            "runtime_action_hash": runtime_action_hash,
            "interval_id": interval_id,
            "expected_pair_count": len(expected_pairs),
            "observed_pair_count": len(observed),
            "missing_pairs": [f"{sc}:{sg}" for sc, sg in missing],
            "extra_pairs": [f"{sc}:{sg}" for sc, sg in extra],
            "duplicate_count": duplicate,
            "complete": not missing and not extra and duplicate == 0,
        })

    release_missing_count = 0
    release_extra_count = 0
    release_duplicate_count = 0
    release_interval_reports: list[dict[str, Any]] = []
    for runtime_action_hash, interval_id in sorted(release_coverage):
        observed = release_coverage[(runtime_action_hash, interval_id)]
        observed_set = set(observed)
        missing = sorted(expected_pairs - observed_set, key=lambda item: (int(item[0]), item[1]))
        extra = sorted(observed_set - expected_pairs, key=lambda item: (int(item[0]), item[1]))
        release_missing_count += len(missing)
        release_extra_count += len(extra)
        duplicate = len(observed) - len(observed_set)
        release_duplicate_count += duplicate
        release_interval_reports.append({
            "runtime_action_hash": runtime_action_hash,
            "interval_id": interval_id,
            "missing_pairs": [f"{sc}:{sg}" for sc, sg in missing],
            "extra_pairs": [f"{sc}:{sg}" for sc, sg in extra],
            "duplicate_count": duplicate,
            "complete": not missing and not extra and duplicate == 0,
        })

    release_parent_mismatch_count = len(action_parent_intervals.symmetric_difference(set(release_coverage)))

    topology_hashes = sorted({record["topology_hash"] for record in normalized})
    program_hashes = sorted({record["program_hash"] for record in normalized})
    action_hashes = sorted({record["action_hash"] for record in normalized})
    runtime_action_hashes = sorted({record["runtime_action_hash"] for record in normalized})
    runtime_action_hmacs = sorted({record["runtime_action_hmac_sha256"] for record in normalized})
    policy_hashes = sorted({record["policy_hash"] for record in normalized})
    build_hashes = sorted({record["build_hash"] for record in normalized})
    action_schema_hashes = sorted({record["action_schema_hash"] for record in normalized})
    row_contract_hashes = sorted({record["row_contract_sha256"] for record in normalized})
    payload_hashes = sorted({record["csv_payload_sha256"] for record in normalized})
    envelope_hmacs = sorted({record["envelope_hmac_sha256"] for record in normalized})
    run_identities = {
        tuple(str(record[field]) for field in ("run_id", "build_id", "network_id", "seed", "demand_identity"))
        for record in normalized
    }
    action_records = [record for record in normalized if record["evidence_kind"] != "native_release"]
    release_records = [record for record in normalized if record["evidence_kind"] == "native_release"]
    success_count = sum(bool(record["readback_ok"]) for record in action_records)
    failure_count = len(action_records) - success_count
    envelope_hmac_failure_count = sum(not record["envelope_hmac_valid"] for record in normalized)
    success_rate = success_count / len(action_records) if action_records else 0.0
    release_success_count = sum(bool(record["readback_ok"]) for record in release_records)
    release_failure_count = len(release_records) - release_success_count
    release_success_rate = release_success_count / len(release_records) if release_records else 0.0
    coverage_complete = bool(evidence_intervals) and missing_count == 0 and duplicate_count == 0 and extra_count == 0
    provenance_complete = (
        bool(normalized)
        and len(topology_hashes) == 1
        and len(run_identities) == 1
        and len(policy_hashes) == 1
        and len(build_hashes) == 1
        and len(action_schema_hashes) == 1
    )
    criteria = [
        _criterion(
            "authority_controller_count",
            len(authority),
            ">=",
            EXPECTED_AUTHORITY_CONTROLLER_COUNT,
        ),
        _criterion("coverage_interval_count", len(evidence_intervals), ">=", 1),
        _criterion("missing_authority_pairs", missing_count, "<=", 0),
        _criterion("duplicate_authority_pairs", duplicate_count, "<=", 0),
        _criterion("extra_authority_pairs", extra_count, "<=", 0),
        _criterion("coverage_complete", int(coverage_complete), ">=", 1),
        _criterion("provenance_complete", int(provenance_complete), ">=", 1),
        _criterion("readback_success_rate", success_rate, ">=", 1.0),
        _criterion("readback_failure_count", failure_count, "<=", 0),
        _criterion("envelope_hmac_failure_count", envelope_hmac_failure_count, "<=", 0),
    ]
    release_criteria = [
        _criterion("native_release_interval_count", len(release_coverage), ">=", 1),
        _criterion("native_release_missing_authority_pairs", release_missing_count, "<=", 0),
        _criterion("native_release_extra_authority_pairs", release_extra_count, "<=", 0),
        _criterion("native_release_duplicate_authority_pairs", release_duplicate_count, "<=", 0),
        _criterion("native_release_parent_mismatch_count", release_parent_mismatch_count, "<=", 0),
        _criterion("native_release_success_rate", release_success_rate, ">=", 1.0),
        _criterion("native_release_failure_count", release_failure_count, "<=", 0),
    ]
    run_identity = list(next(iter(run_identities))) if len(run_identities) == 1 else ["", "", "", "", ""]
    report = {
        "schema_version": COM_READBACK_REPORT_SCHEMA_VERSION,
        "record_count": len(normalized),
        "thresholds": {
            "authority_controller_count": EXPECTED_AUTHORITY_CONTROLLER_COUNT,
            "coverage_interval_count_min": 1,
            "missing_authority_pairs_max": 0,
            "duplicate_authority_pairs_max": 0,
            "extra_authority_pairs_max": 0,
            "readback_success_rate_min": 1.0,
            "readback_failure_count_max": 0,
            "envelope_hmac_failure_count_max": 0,
            "native_release_interval_count_min": 1,
            "native_release_success_rate_min": 1.0,
            "native_release_failure_count_max": 0,
            "native_release_parent_mismatch_count_max": 0,
        },
        "aggregate": {
            "success_count": success_count,
            "action_record_count": len(action_records),
            "failure_count": failure_count,
            "success_rate": success_rate,
            "coverage_interval_count": len(evidence_intervals),
            "missing_authority_pair_count": missing_count,
            "duplicate_authority_pair_count": duplicate_count,
            "extra_authority_pair_count": extra_count,
            "coverage_complete": coverage_complete,
            "envelope_hmac_failure_count": envelope_hmac_failure_count,
            "native_release_record_count": len(release_records),
            "native_release_success_count": release_success_count,
            "native_release_failure_count": release_failure_count,
            "native_release_success_rate": release_success_rate,
            "native_release_interval_count": len(release_coverage),
            "native_release_missing_authority_pair_count": release_missing_count,
            "native_release_extra_authority_pair_count": release_extra_count,
            "native_release_duplicate_authority_pair_count": release_duplicate_count,
            "native_release_parent_mismatch_count": release_parent_mismatch_count,
        },
        "coverage_by_interval": interval_reports,
        "native_release_by_interval": release_interval_reports,
        "provenance": {
            "complete": provenance_complete,
            "topology_hash": topology_hashes[0] if len(topology_hashes) == 1 else "",
            "program_hashes": program_hashes,
            "action_hashes": action_hashes,
            "action_set_sha256": _digest_payload({"action_hashes": action_hashes}),
            "runtime_action_hashes": runtime_action_hashes,
            "runtime_action_set_sha256": _digest_payload({"runtime_action_hashes": runtime_action_hashes}),
            "runtime_action_hmacs": runtime_action_hmacs,
            "runtime_action_hmac_set_sha256": _digest_payload({"runtime_action_hmacs": runtime_action_hmacs}),
            "csv_payload_hashes": payload_hashes,
            "csv_payload_set_sha256": _digest_payload({"csv_payload_hashes": payload_hashes}),
            "envelope_hmacs": envelope_hmacs,
            "envelope_hmac_set_sha256": _digest_payload({"envelope_hmacs": envelope_hmacs}),
            "policy_hash": policy_hashes[0] if len(policy_hashes) == 1 else "",
            "build_hash": build_hashes[0] if len(build_hashes) == 1 else "",
            "action_schema_hash": action_schema_hashes[0] if len(action_schema_hashes) == 1 else "",
            "row_contract_hashes": row_contract_hashes,
            "row_contract_set_sha256": _digest_payload({"row_contract_hashes": row_contract_hashes}),
            "expected_authority": authority,
            "expected_authority_sha256": _digest_payload({"expected_authority": authority}),
            "run_identity": {
                "run_id": run_identity[0], "build_id": run_identity[1], "network_id": run_identity[2],
                "seed": run_identity[3], "demand_identity": run_identity[4],
            },
        },
        "gates": {
            "g8_readback": {"verdict": _gate(criteria), "criteria": criteria},
            "g8_native_release": {"verdict": _gate(release_criteria), "criteria": release_criteria},
        },
    }
    return _with_report_digest(report)


class ShadowRecorder:
    """Append validated candidate decisions without issuing actuation."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(record)
        if payload.get("actuation_attempted") is True:
            raise ShadowValidationError("shadow records must not attempt actuation")
        payload.setdefault("schema_version", RECORD_SCHEMA_VERSION)
        payload["shadow_mode"] = True
        payload["actuation_attempted"] = False
        normalized = validate_record(payload)
        for field in ("topology_hash", "state_hash", "action_hash"):
            if field not in normalized:
                raise ShadowValidationError(f"recorder requires {field}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json_text(normalized) + "\n")
        return normalized

    def record_decision(
        self,
        *,
        decision_id: str,
        topology_hash: str,
        state_hash: str,
        candidates: Iterable[Mapping[str, Any]],
        shared: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Record each candidate under a shared, non-actuating decision envelope."""

        common = dict(shared or {})
        common.update({"decision_id": decision_id, "topology_hash": topology_hash, "state_hash": state_hash})
        output: list[dict[str, Any]] = []
        for candidate in candidates:
            payload = dict(candidate)
            for field, value in common.items():
                if field in payload and payload[field] != value:
                    raise ShadowValidationError(f"candidate cannot override shared field {field}")
                payload[field] = value
            output.append(self.record(payload))
        return output


def write_report(path: str | Path, report: Mapping[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(canonical_json_text(report) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_jsonl", type=Path, help="shadow candidate records in JSON Lines format")
    parser.add_argument("--output", required=True, type=Path, help="canonical JSON validation report")
    args = parser.parse_args(argv)
    try:
        report = evaluate_shadow_records(load_jsonl(args.input_jsonl))
        write_report(args.output, report)
    except ShadowValidationError as exc:
        parser.error(str(exc))
    print(
        f"decisions={report['decision_count']} "
        f"g6_initial={report['gates']['g6_initial']['verdict']} "
        f"g6_release={report['gates']['g6_release']['verdict']} "
        f"g7={report['gates']['g7_shadow_runtime']['verdict']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
