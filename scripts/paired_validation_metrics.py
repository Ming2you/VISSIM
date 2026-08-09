#!/usr/bin/env python3
# 짝지은 VISSIM 검증의 지표 정의와 합격 게이트 (v3 N9-4)
"""Metric definitions with the denominators pinned in code.

The plan says why:

    지표 정의 (v2.1 J-4 에서 유지 — 분모를 명시하지 않으면 두 사람이 다르게 계산한다)

A gate whose metric two people compute differently decides nothing. So every denominator
here is explicit, floored, and tested — including the floors that exist only to keep a
zero observation from producing an infinite ratio.

The other rule this module enforces: every absolute metric is gated together with the
signed bias computed over **the same denominator**. Different denominators let a run pass
the absolute check while the bias check fails on arithmetic rather than on physics.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence


SCHEMA_VERSION = "paired-validation-metrics-v3"

# 분모 바닥. 관측이 0 인 셀에서 비율이 발산하는 것을 막는다.
NMAE_FLOOR_VEH = 1.0
SPEED_FLOOR_KPH = 5.0
TTT_FLOOR_VEH_H = 1.0
ZERO_OBSERVATION_MAE_LIMIT_VEH = 1.0

# spillback 표본 하한. 저수요는 면제하고 혼잡은 막는다.
SPILLBACK_MIN_LOW_DEMAND = 5
SPILLBACK_MIN_CONGESTED = 10


class MetricError(ValueError):
    """Raised when a metric is asked for something it cannot mean."""


def _pairs(pred: Sequence[float], obs: Sequence[float]) -> list[tuple[float, float]]:
    if len(pred) != len(obs):
        raise MetricError(f"length mismatch: pred={len(pred)} obs={len(obs)}")
    if not pred:
        raise MetricError("empty series")
    return [(float(p), float(o)) for p, o in zip(pred, obs)]


def nmae(pred: Sequence[float], obs: Sequence[float]) -> float:
    """Σ|pred − obs| / max(Σ obs, 1 veh).

    분모는 셀별이 아니라 **합계**다. 셀별로 나누면 작은 관측 하나가 전체를 지배한다.
    """
    items = _pairs(pred, obs)
    numerator = sum(abs(p - o) for p, o in items)
    denominator = max(sum(o for _, o in items), NMAE_FLOOR_VEH)
    return numerator / denominator


def signed_bias(pred: Sequence[float], obs: Sequence[float]) -> float:
    """Σ(pred − obs) / max(Σ obs, 1 veh) — nmae 와 **같은 분모**를 쓴다."""
    items = _pairs(pred, obs)
    numerator = sum(p - o for p, o in items)
    denominator = max(sum(o for _, o in items), NMAE_FLOOR_VEH)
    return numerator / denominator


def zero_observation_cell_passes(pred: float, obs: float) -> bool:
    """관측 0인 셀은 비율이 정의되지 않으므로 MAE <= 1 veh 로 판정한다."""
    if float(obs) != 0.0:
        raise MetricError("this rule only applies to cells whose observation is zero")
    return abs(float(pred)) <= ZERO_OBSERVATION_MAE_LIMIT_VEH


def speed_mape(
    pred: Sequence[float],
    obs: Sequence[float],
    weights: Sequence[float],
) -> float:
    """차량가중 MAPE, 분모 max(obs_speed, 5 kph).

    바닥이 없으면 정지 구간(관측 0 kph)이 값을 발산시킨다. 가중은 차량 대수다 —
    한 대가 지나간 구간과 백 대가 지나간 구간을 같게 세면 지표가 물리를 반영하지 않는다.
    """
    items = _pairs(pred, obs)
    if len(weights) != len(items):
        raise MetricError(f"weight length mismatch: {len(weights)} vs {len(items)}")
    total_weight = sum(float(w) for w in weights)
    if total_weight <= 0.0:
        raise MetricError("total vehicle weight is zero")
    weighted = sum(
        float(w) * abs(p - o) / max(o, SPEED_FLOOR_KPH)
        for (p, o), w in zip(items, weights)
    )
    return weighted / total_weight


def ttt_ape(pred: float, obs: float) -> float:
    """|pred − obs| / max(obs, 1 veh·h)."""
    return abs(float(pred) - float(obs)) / max(float(obs), TTT_FLOOR_VEH_H)


def geh(pred: float, obs: float) -> float:
    """GEH = sqrt(2(m−c)² / (m+c)).

    m+c 가 0 이면 0/0 이다. NaN 을 흘리면 통과율 집계가 통째로 오염되므로 0 으로 정의한다 —
    관측도 예측도 0 이면 불일치가 없다.
    """
    m, c = float(pred), float(obs)
    total = m + c
    if total <= 0.0:
        return 0.0
    return math.sqrt(2.0 * (m - c) ** 2 / total)


def geh_pass_fraction(
    pred: Sequence[float], obs: Sequence[float], threshold: float = 5.0
) -> float:
    items = _pairs(pred, obs)
    passing = sum(1 for p, o in items if geh(p, o) <= threshold)
    return passing / len(items)


# 합격 게이트. 각 항목은 상한이다(작을수록 좋다). geh_pass_fraction 만 하한이다.
GATES: dict[int, dict[str, float]] = {
    1: {
        "urban_queue_storage_nmae": 0.15,
        "travel_time_median_sec": 5.0,
        "travel_time_p95_sec": 15.0,
        "queue_tail_mae_m": 20.0,
        "speed_mape": 0.10,
        "count_mae_veh": 5.0,
        "count_mae_fraction": 0.10,
        "geh_pass_fraction": 0.85,
        "flow_signed_bias": 0.10,
        "ttt_ape": 0.10,
    },
    3: {
        "ttt_ape": 0.12,
        "terminal_nmae": 0.20,
        "speed_mape": 0.15,
        "count_mae_veh": 7.5,
        "count_mae_fraction": 0.15,
        "geh_pass_fraction": 0.85,
        "flow_signed_bias": 0.10,
    },
    5: {
        "ttt_ape": 0.15,
        "terminal_nmae": 0.20,
        "speed_mape": 0.15,
        "count_mae_veh": 7.5,
        "count_mae_fraction": 0.15,
        "geh_pass_fraction": 0.85,
        "flow_signed_bias": 0.10,
    },
    10: {
        "ttt_ape": 0.18,
        "terminal_nmae": 0.35,
        "speed_mape": 0.20,
        "count_mae_veh": 10.0,
        "count_mae_fraction": 0.20,
        "flow_signed_bias": 0.10,
        "nonfinite_failures": 0.0,
        "negative_failures": 0.0,
        "clipping_failures": 0.0,
        "mass_failures": 0.0,
    },
    15: {
        "ttt_ape": 0.20,
        "terminal_nmae": 0.35,
        "speed_mape": 0.20,
        "count_mae_veh": 10.0,
        "count_mae_fraction": 0.20,
        "flow_signed_bias": 0.10,
        "nonfinite_failures": 0.0,
        "negative_failures": 0.0,
        "clipping_failures": 0.0,
        "mass_failures": 0.0,
    },
}

# 하한 게이트(클수록 좋다). 나머지는 전부 상한이다.
LOWER_BOUND_METRICS = frozenset({"geh_pass_fraction"})

# 절대지표와 그 부호편향의 짝. 계획 - "모든 absolute metric 은 같은 분모의 signed bias 를
# 함께 게이트한다. |signed_bias| 가 해당 H 의 absolute metric 한계를 넘으면 실패다."
SIGNED_BIAS_PARTNERS = {
    "urban_queue_storage_nmae": "urban_queue_storage_signed_bias",
    "terminal_nmae": "terminal_signed_bias",
    "speed_mape": "speed_signed_bias",
    "ttt_ape": "ttt_signed_bias",
}


def count_mae_limit(horizon: int, observed_total: float) -> float:
    """max(절대 veh, 비율 x 관측총합). 계획 표기 max(5 veh, 10%) 그대로다."""
    gate = GATES.get(int(horizon))
    if gate is None:
        raise MetricError(f"unknown horizon: {horizon}")
    return max(gate["count_mae_veh"], gate["count_mae_fraction"] * float(observed_total))


def evaluate(results: Mapping[int, Mapping[str, float]]) -> dict[str, object]:
    """Judge measured metrics against the gate table.

    **H=1 은 독립 게이트다.** 다른 H 로 구제하지 않으므로 horizon 별로 따로 판정하고
    하나라도 실패하면 전체가 실패다.

    측정되지 않은 지표는 통과가 아니라 NOT_EVALUATED 다 — 통과로 세면 측정을 덜 할수록
    유리해진다.
    """
    unknown = sorted(set(results) - set(GATES))
    if unknown:
        raise MetricError(f"unknown horizons: {unknown}")

    reasons: list[str] = []
    failed: list[int] = []
    measured = 0

    for horizon in sorted(results):
        gate = GATES[horizon]
        values = results[horizon]
        for name, limit in gate.items():
            if name not in values:
                continue
            measured += 1
            value = float(values[name])
            if name in LOWER_BOUND_METRICS:
                if value < limit:
                    reasons.append(f"H={horizon} {name}={value:g} < {limit:g}")
                    failed.append(horizon)
            elif value > limit:
                reasons.append(f"H={horizon} {name}={value:g} > {limit:g}")
                failed.append(horizon)

            partner = SIGNED_BIAS_PARTNERS.get(name)
            if partner and partner in values:
                measured += 1
                bias = abs(float(values[partner]))
                if bias > limit:
                    reasons.append(
                        f"H={horizon} {partner}={bias:g} > {name} limit {limit:g}"
                    )
                    failed.append(horizon)

        if "flow_signed_bias" in values:
            measured += 1
            bias = abs(float(values["flow_signed_bias"]))
            if bias > gate["flow_signed_bias"]:
                reasons.append(
                    f"H={horizon} flow_signed_bias={bias:g} > {gate['flow_signed_bias']:g}"
                )
                failed.append(horizon)

    if measured == 0:
        status = "NOT_EVALUATED"
    elif reasons:
        status = "FAIL"
    else:
        status = "PASS"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reasons": reasons,
        "failed_horizons": sorted(set(failed)),
        "measured_metrics": measured,
    }


def spillback_status(positives: int, congested: bool) -> str:
    """표본이 모자랄 때 면제인지 차단인지 가른다.

    v3 초판은 "저수요" 한정을 빠뜨렸다. 그러면 탐지를 덜 할수록 게이트를 피하는
    역인센티브가 생긴다 — 혼잡 셀에서 positive 를 못 찾으면 그것 자체가 결함이므로 BLOCKED 다.
    """
    if congested:
        return "EVALUATED" if positives >= SPILLBACK_MIN_CONGESTED else "BLOCKED"
    return "EVALUATED" if positives >= SPILLBACK_MIN_LOW_DEMAND else "NOT_EVALUATED"
