#!/usr/bin/env python3
# 물리 stock 캘리브레이션이 v3 N6 합격 기준을 만족하는지 판정하는 검증기
"""Judge a physical-stock calibration artifact against the N6 acceptance bar.

계획(N6)의 PASS 는 일곱 항목이다.

    split 중복 0 · 포화 독립 lane-group >=30 · 표본 >=200 ·
    jam CI 반폭 <= 추정값의 10% · geometry prior 차이 <=15% ·
    training 시드별 적합 차이 <=15% · fallback 분율 사용 <=10%

여기에 숫자가 아닌 요건이 하나 더 있다 — **적합은 training 시드에서만.** holdout 은 적합·
임계선택·후보교체에 쓰지 않는다. 값만 봐서는 확인할 수 없으므로 아티팩트가 자기 split 과
`fit_source` 를 신고하게 하고, holdout 이면 거부한다.

## 왜 검증기가 데이터보다 먼저인가

지금 있는 자료(`outputs/urban_storage_capacity_20260805.json`)는 jam 표본이 **177 개**로
기준 200 에 미달이고 신뢰구간이 아예 없다. 검증기가 없으면 "무엇이 부족한가" 를 체계적으로
말할 수 없다. 없는 CI 를 반폭 0 으로 통과시키는 것은 정밀도를 날조하는 것이므로
`ci_missing` 을 별도 사유로 둔다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "physical-stock-calibration-v3"

MIN_JAM_SAMPLES = 200
MIN_SATURATED_LANE_GROUPS = 30
MAX_CI_HALF_WIDTH_FRACTION = 0.10
MAX_GEOMETRY_PRIOR_GAP = 0.15
MAX_SEED_FIT_GAP = 0.15
MAX_FALLBACK_FRACTION = 0.10

# jam density 표본 선별 임계. 계획이 못박은 값이라 다르면 다른 모집단을 잰 것이다.
REQUIRED_SPEED_MAX_KPH = 3.0
REQUIRED_STOPPED_FRACTION_MIN = 0.5

REQUIRED_SECTIONS = (
    "split",
    "jam_density",
    "geometry_prior",
    "per_training_seed_fit",
)


def _relative_gap(values: Sequence[float]) -> float:
    """최대/최소 상대 격차. 분모는 최소값이라 격차를 과소평가하지 않는다."""
    items = [float(v) for v in values]
    low, high = min(items), max(items)
    if low <= 0:
        return float("inf")
    return (high - low) / low


def validate(payload: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    measured: dict[str, Any] = {}

    for section in REQUIRED_SECTIONS:
        if section not in payload:
            reasons.append(f"{section}.missing")

    split = payload.get("split") or {}
    training = list(split.get("training_run_ids") or [])
    holdout = list(split.get("holdout_run_ids") or [])
    if not training:
        reasons.append("split.training_empty")
    overlap = sorted(set(training) & set(holdout))
    if overlap:
        reasons.append("split.overlap")
    measured["split_overlap"] = overlap
    # 적합 출처는 값이 아니라 절차 요건이다. 신고를 강제한다.
    if str(split.get("fit_source", "")) != "training":
        reasons.append("split.fit_source")

    jam = payload.get("jam_density") or {}
    if jam:
        samples = int(jam.get("sample_count", 0))
        groups = int(jam.get("saturated_lane_groups", 0))
        measured["jam_sample_count"] = samples
        measured["saturated_lane_groups"] = groups
        if samples < MIN_JAM_SAMPLES:
            reasons.append("jam_density.sample_count")
        if groups < MIN_SATURATED_LANE_GROUPS:
            reasons.append("jam_density.saturated_lane_groups")

        low, high = jam.get("ci95_low"), jam.get("ci95_high")
        value = float(jam.get("value_veh_km_lane", 0.0) or 0.0)
        if low is None or high is None:
            # 없는 CI 를 반폭 0 으로 통과시키면 정밀도를 날조하는 것이다.
            reasons.append("jam_density.ci_missing")
        elif value > 0:
            half_width = (float(high) - float(low)) / 2.0
            measured["ci_half_width_fraction"] = half_width / value
            if half_width / value > MAX_CI_HALF_WIDTH_FRACTION:
                reasons.append("jam_density.ci_half_width")

        selection = jam.get("selection") or {}
        if (
            float(selection.get("speed_max_kph", -1)) != REQUIRED_SPEED_MAX_KPH
            or float(selection.get("stopped_fraction_min", -1))
            != REQUIRED_STOPPED_FRACTION_MIN
        ):
            reasons.append("jam_density.selection")

    prior = payload.get("geometry_prior") or {}
    if prior:
        declared = float(prior.get("jam_spacing_m", 0.0) or 0.0)
        fitted = float(prior.get("fitted_jam_spacing_m", 0.0) or 0.0)
        if declared > 0 and fitted > 0:
            gap = abs(fitted - declared) / declared
            measured["geometry_prior_gap"] = gap
            if gap > MAX_GEOMETRY_PRIOR_GAP:
                reasons.append("geometry_prior.gap")
        else:
            reasons.append("geometry_prior.missing_values")

    seed_fit = payload.get("per_training_seed_fit") or {}
    if seed_fit:
        if len(seed_fit) < 2:
            # 시드 하나로는 시드간 차이를 잴 수 없다. 통과로 세면 검사가 무의미하다.
            reasons.append("per_training_seed_fit.insufficient")
        else:
            gap = _relative_gap(list(seed_fit.values()))
            measured["seed_fit_gap"] = gap
            if gap > MAX_SEED_FIT_GAP:
                reasons.append("per_training_seed_fit.gap")

    fallback = payload.get("fallback_fraction_used")
    if fallback is None:
        reasons.append("fallback_fraction_used.missing")
    else:
        measured["fallback_fraction_used"] = float(fallback)
        if float(fallback) > MAX_FALLBACK_FRACTION:
            reasons.append("fallback_fraction_used")

    # 계획 - 큐꼬리 관측이 있으면 고정 분율(0.35/0.50) 대신 관측 분해를 쓴다.
    if str(payload.get("queue_tail_source", "")) != "observed":
        reasons.append("queue_tail_source")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL" if reasons else "PASS",
        "reasons": sorted(set(reasons)),
        "measured": measured,
        "thresholds": {
            "min_jam_samples": MIN_JAM_SAMPLES,
            "min_saturated_lane_groups": MIN_SATURATED_LANE_GROUPS,
            "max_ci_half_width_fraction": MAX_CI_HALF_WIDTH_FRACTION,
            "max_geometry_prior_gap": MAX_GEOMETRY_PRIOR_GAP,
            "max_seed_fit_gap": MAX_SEED_FIT_GAP,
            "max_fallback_fraction": MAX_FALLBACK_FRACTION,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a physical-stock calibration")
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.calibration.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1

    report = validate(payload)
    report["calibration"] = str(args.calibration)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print("status=%s reasons=%d" % (report["status"], len(report["reasons"])))
    for reason in report["reasons"]:
        print("  -", reason)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
