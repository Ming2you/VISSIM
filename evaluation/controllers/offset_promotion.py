# v3 N4-7 - offset production writer 의 삼중 잠금(D-offset-enable)을 증거에서 판정하는 단일 권위
"""offset 을 플랜트에 쓸 수 있는가. 그 질문에 답하는 곳은 여기 하나다.

## 왜 별도 모듈인가

계획(IMPLEMENTATION_PLAN_V3_LEAN.md N4-7)이 요구하는 것은 삼중 잠금이다.

    D-offset-enable = D-core(같은 신호 profile + 같은 topology SHA-256)
                    ∧ N9 offset 효과·순위 게이트
                    ∧ N8-4 런타임 게이트

이 판정이 어댑터 안에 상수로 흩어져 있으면 "언젠가 그냥 풀린다". 그래서 판정은
**증거 산출물에서만** 나온다. 상수를 고쳐서 여는 길은 없다 - 세 산출물이 모두 있고,
모두 `status=PASS` 이고, 셋이 **같은** 신호 profile / topology 를 가리켜야 열린다.

## 세 writer 의 뜻

    intent_only  의도만 기록하고 COM 에 쓰지 않는다. 승격 전 production 경로의 상태다.
                 의도는 action JSON 의 `offsets` 에 그대로 남는다 - 버리는 것이 아니다.
    test_only    격리된 시험 harness 만 선언할 수 있다. **강제 offset arm** 만 낸다.
                 최적화기가 고른 offset 은 여기서도 나가지 않는다(N9 단일레버 대조가
                 흐려지기 때문이다).
    production   삼중 잠금이 전부 PASS 일 때만. 설정 파일로는 선언할 수 없다.

## 잠금은 두 겹이다

여기(어댑터 쪽)가 권위이고, 러너의 `RW_OFFSET_WRITER` 는 두 번째 자물쇠다. 러너는
증거를 읽을 수 없으므로 "선언하지 않은 런은 offset 을 액추에이션하지 못한다"만
보장한다. 손으로 고친 action CSV 도 러너에서 전량 거부된다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from evaluation.controllers.signal_timing_oracle import (
    BLOCKED,
    FAIL,
    NOT_EVALUATED,
    PASS,
)


SCHEMA_VERSION = "offset-promotion-v3"

WRITER_INTENT_ONLY = "intent_only"
WRITER_TEST_ONLY = "test_only"
WRITER_PRODUCTION = "production"

# 순서가 곧 계획의 곱 순서다. 이름을 바꾸면 증거 산출물 파일명도 함께 바뀌어야 한다.
LOCK_NAMES = ("d_core", "n9_offset_effect", "n8_4_runtime")

REPO = Path(__file__).resolve().parents[2]

# 증거 산출물. 없으면 그 자물쇠는 PASS 가 아니라 NOT_EVALUATED 다.
DEFAULT_EVIDENCE_PATHS: dict[str, Path] = {
    "d_core": REPO / "outputs" / "offset_promotion_d_core.json",
    "n9_offset_effect": REPO / "outputs" / "offset_promotion_n9_offset_effect.json",
    "n8_4_runtime": REPO / "outputs" / "offset_promotion_n8_4_runtime.json",
}

_LOCK_NEEDS = {
    "d_core": (
        "outputs/offset_promotion_d_core.json with status=PASS from "
        "scripts/verify_signal_timing_oracle.py, bound to signal_profile_id + topology_sha256"
    ),
    "n9_offset_effect": (
        "outputs/offset_promotion_n9_offset_effect.json with status=PASS from the N9 "
        "offset effect/ranking gate, bound to the same signal_profile_id + topology_sha256"
    ),
    "n8_4_runtime": (
        "outputs/offset_promotion_n8_4_runtime.json with status=PASS from the N8-4 runtime "
        "gate, bound to the same signal_profile_id + topology_sha256"
    ),
}

_KNOWN_STATUSES = (PASS, FAIL, BLOCKED, NOT_EVALUATED)

# 설정 파일이 선언할 수 있는 값. production 은 여기에 없다 - 증거로만 열린다.
DECLARABLE_WRITERS = ("", WRITER_INTENT_ONLY, WRITER_TEST_ONLY)

# 강제 offset arm 을 싣고 있다고 control 이 스스로 밝히는 키.
FORCED_ARM_DIAGNOSTIC_KEYS = (
    "diagnostic_forced_signal_offset_sec",
    "signal_green_freeze_offset_sec",
)

# 신호별 강제 offset 표. `{signal: offset_sec}` 를 담은 JSON 문자열이다.
#
# 왜 필요한가. 위 두 키는 **스칼라 하나**를 전 신호에 똑같이 쓴다. 공통 주기 망에서
# 균일 이동은 상대 위상을 하나도 안 바꾸므로 연동을 시험할 수 없다. 그런데 이 모듈이
# `test_only` 를 둔 목적이 바로 "**강제 offset arm**" 이다 — 최적화기가 고른 offset 이
# 아니라 harness 가 지정한 값. `.sig` 의 신호별 native offset 을 그대로 재생하는 것이
# 정확히 그 경우다(17개 전부 정수라 1초 격자에 오차 0 으로 들어간다).
#
# **production 은 이 키로 열리지 않는다.** 여기서 넓히는 것은 test_only 가 표현할 수
# 있는 강제 arm 의 모양뿐이고, 삼중 잠금과 optimizer-chosen offset 의 경로는 그대로다.
FORCED_ARM_TABLE_KEY = "forced_signal_offsets_json"


def forced_arm_offset_table(control: Any) -> dict[str, float]:
    """control 이 실은 신호별 강제 offset 표. 없으면 빈 dict."""
    diagnostics = getattr(control, "diagnostics", None) or {}
    raw = diagnostics.get(FORCED_ARM_TABLE_KEY)
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        blob = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(blob, Mapping):
        return {}
    out: dict[str, float] = {}
    for key, value in blob.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


class OffsetPromotionError(RuntimeError):
    """승격 잠금을 우회하려는 설정. 조용히 무시하지 않고 런을 세운다."""


def _lock(name: str, status: str, detail: str, needs: str = "") -> dict[str, Any]:
    return {"name": name, "status": status, "detail": detail, "needs": needs}


def load_evidence(
    paths: Mapping[str, Path] | None = None,
) -> dict[str, Mapping[str, Any] | None]:
    """증거 산출물을 읽는다. 없거나 못 읽으면 `None` - 그 자물쇠는 잠긴 채로 남는다."""
    source = dict(DEFAULT_EVIDENCE_PATHS if paths is None else paths)
    evidence: dict[str, Mapping[str, Any] | None] = {}
    for name in LOCK_NAMES:
        path = source.get(name)
        if path is None or not Path(path).is_file():
            evidence[name] = None
            continue
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            evidence[name] = None
            continue
        evidence[name] = value if isinstance(value, Mapping) else None
    return evidence


def _binding(report: Mapping[str, Any]) -> tuple[str, str]:
    return (
        str(report.get("signal_profile_id", "")).strip(),
        str(report.get("topology_sha256", "")).strip(),
    )


def lock_status(
    name: str,
    report: Mapping[str, Any] | None,
    *,
    signal_profile_id: str | None = None,
    topology_sha256: str | None = None,
) -> dict[str, Any]:
    """자물쇠 하나의 판정. 측정 불가는 PASS 가 아니다."""
    needs = _LOCK_NEEDS.get(name, f"a {name} gate report with status=PASS")
    if report is None:
        return _lock(name, NOT_EVALUATED, "no evidence artifact", needs)
    status = str(report.get("status", "")).strip().upper()
    if status not in _KNOWN_STATUSES:
        return _lock(name, FAIL, f"unknown gate status {status!r}", needs)
    if status != PASS:
        return _lock(name, status, f"gate reports {status}", needs)
    profile, topology = _binding(report)
    if not profile or not topology:
        return _lock(
            name,
            NOT_EVALUATED,
            "gate passes but does not say which signal profile / topology it certifies",
            needs,
        )
    if signal_profile_id is not None and profile != str(signal_profile_id):
        return _lock(
            name,
            BLOCKED,
            f"certifies signal_profile_id={profile!r}, not {str(signal_profile_id)!r}",
            needs,
        )
    if topology_sha256 is not None and topology != str(topology_sha256):
        return _lock(
            name,
            BLOCKED,
            f"certifies topology_sha256={topology!r}, not {str(topology_sha256)!r}",
            needs,
        )
    return _lock(name, PASS, f"PASS for signal_profile_id={profile} topology={topology[:12]}")


def evaluate(
    evidence: Mapping[str, Mapping[str, Any] | None] | None = None,
    *,
    signal_profile_id: str | None = None,
    topology_sha256: str | None = None,
) -> dict[str, Any]:
    """D-offset-enable 판정. `evidence` 를 주지 않으면 기본 산출물 경로에서 읽는다."""
    reports = dict(load_evidence() if evidence is None else evidence)
    locks = [
        lock_status(
            name,
            reports.get(name),
            signal_profile_id=signal_profile_id,
            topology_sha256=topology_sha256,
        )
        for name in LOCK_NAMES
    ]

    # 세 증거가 **같은** profile / topology 를 가리켜야 곱이 성립한다. 서로 다른
    # 프로필에서 하나씩 받아온 PASS 는 같은 대상에 대한 증거가 아니다.
    bindings = {
        _binding(reports[name])
        for name, lock in zip(LOCK_NAMES, locks)
        if lock["status"] == PASS and reports.get(name) is not None
    }
    if len(bindings) > 1:
        locks = [
            lock
            if lock["status"] != PASS
            else _lock(
                lock["name"],
                BLOCKED,
                "the three gates certify different signal profiles / topologies: "
                + "; ".join(sorted(f"{profile}@{sha[:12]}" for profile, sha in bindings)),
                _LOCK_NEEDS.get(lock["name"], ""),
            )
            for lock in locks
        ]

    statuses = [lock["status"] for lock in locks]
    if FAIL in statuses:
        status = FAIL
    elif BLOCKED in statuses:
        status = BLOCKED
    elif NOT_EVALUATED in statuses:
        status = NOT_EVALUATED
    else:
        status = PASS
    promoted = status == PASS
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "promoted": promoted,
        "writer": WRITER_PRODUCTION if promoted else WRITER_INTENT_ONLY,
        "locks": locks,
        "reasons": [
            f"{lock['name']}={lock['status']} ({lock['detail']})"
            for lock in locks
            if lock["status"] != PASS
        ],
    }


def _declared_writer(actuation: Mapping[str, Any] | None) -> str:
    settings = (actuation or {}).get("real_world_signal_control")
    if not isinstance(settings, Mapping):
        return ""
    return str(settings.get("offset_writer", "")).strip().lower()


def resolve_writer(
    actuation: Mapping[str, Any] | None,
    *,
    verdict: Mapping[str, Any] | None = None,
) -> str:
    """이 런의 offset writer. 승격이 없으면 선언으로 test_only 까지만 올라간다."""
    declared = _declared_writer(actuation)
    if declared not in DECLARABLE_WRITERS:
        if declared == WRITER_PRODUCTION:
            raise OffsetPromotionError(
                "offset_writer=production is not declarable from a config; the production "
                "writer opens only from D-offset-enable evidence (N4-7 triple lock)"
            )
        raise OffsetPromotionError(
            f"unknown offset_writer={declared!r}; declarable values are {DECLARABLE_WRITERS!r}"
        )
    decision = evaluate() if verdict is None else verdict
    if bool(decision.get("promoted", False)):
        return WRITER_PRODUCTION
    if declared == WRITER_TEST_ONLY:
        return WRITER_TEST_ONLY
    return WRITER_INTENT_ONLY


def forced_arm_offset_sec(control: Any) -> float | None:
    """control 이 스스로 밝힌 강제 offset arm. 없으면 `None` 이다."""
    diagnostics = getattr(control, "diagnostics", None) or {}
    for key in FORCED_ARM_DIAGNOSTIC_KEYS:
        if key in diagnostics:
            try:
                return float(diagnostics[key])
            except (TypeError, ValueError):
                return None
    return None


def guard_forced_arm(control: Any, writer: str) -> None:
    """강제 offset arm 을 실은 control 이 선언 없는 런에 오면 세운다.

    조용히 0 으로 뭉개면 "돌긴 돌았는데 레버가 없는" 자료가 나온다. 그 자료는 나중에
    offset 효과 없음으로 읽히고, 그것이 잠금보다 위험하다.
    """
    forced = forced_arm_offset_sec(control)
    table = forced_arm_offset_table(control)
    table_max = max((abs(v) for v in table.values()), default=0.0)
    if (forced is None or abs(float(forced)) <= 1.0e-9) and table_max <= 1.0e-9:
        return
    if forced is None:
        forced = table_max
    if writer == WRITER_INTENT_ONLY:
        raise OffsetPromotionError(
            f"control carries a forced offset arm ({forced} s) but this run declares "
            f"offset_writer={WRITER_INTENT_ONLY}; a forced arm needs an isolated test "
            f"harness declaring real_world_signal_control.offset_writer={WRITER_TEST_ONLY!r} "
            "(N4-7). Refusing to silently write a zero-offset arm."
        )


def written_offset_sec(signal: str, control: Any, writer: str) -> float:
    """이 signal 행의 offset 열에 실제로 실을 값."""
    if writer == WRITER_PRODUCTION:
        return float((getattr(control, "offsets", None) or {}).get(signal, 0.0))
    if writer == WRITER_TEST_ONLY:
        # 신호별 표가 있으면 그것이 우선이다(연동 시험용). 없으면 종전대로 스칼라.
        table = forced_arm_offset_table(control)
        if table:
            return float(table.get(str(signal), 0.0))
        forced = forced_arm_offset_sec(control)
        return 0.0 if forced is None else float(forced)
    return 0.0


def action_metadata(
    control: Any, writer: str, verdict: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """런 메타데이터에 남길 값. 억눌린 의도를 숨기지 않는다."""
    intents = {
        str(key): float(value)
        for key, value in (getattr(control, "offsets", None) or {}).items()
    }
    nonzero = [value for value in intents.values() if abs(value) > 1.0e-9]
    suppressed = 0.0 if writer == WRITER_PRODUCTION else float(len(nonzero))
    decision = verdict or {}
    return {
        "offset_writer": writer,
        "offset_promotion_status": str(decision.get("status", NOT_EVALUATED)),
        "offset_promotion_reasons": "; ".join(decision.get("reasons", []) or []),
        "offset_production_writes": float(len(nonzero)) if writer == WRITER_PRODUCTION else 0.0,
        "offset_intent_suppressed_signals": suppressed,
        "offset_intent_max_abs_sec": max((abs(value) for value in intents.values()), default=0.0),
    }


def matrix_lever_status(verdict: Mapping[str, Any] | None = None) -> str:
    """N9 행렬의 offset 레버 상태. 승격 전에는 셀을 돌리지 않는다."""
    decision = evaluate() if verdict is None else verdict
    return "PLANNED" if bool(decision.get("promoted", False)) else BLOCKED


def matrix_lever_writer(verdict: Mapping[str, Any] | None = None) -> str:
    """N9 행렬의 offset 레버 writer."""
    decision = evaluate() if verdict is None else verdict
    return WRITER_PRODUCTION if bool(decision.get("promoted", False)) else WRITER_TEST_ONLY


__all__ = [
    "BLOCKED",
    "DECLARABLE_WRITERS",
    "DEFAULT_EVIDENCE_PATHS",
    "FAIL",
    "LOCK_NAMES",
    "NOT_EVALUATED",
    "OffsetPromotionError",
    "PASS",
    "SCHEMA_VERSION",
    "WRITER_INTENT_ONLY",
    "WRITER_PRODUCTION",
    "WRITER_TEST_ONLY",
    "FORCED_ARM_TABLE_KEY",
    "forced_arm_offset_table",
    "action_metadata",
    "evaluate",
    "forced_arm_offset_sec",
    "guard_forced_arm",
    "load_evidence",
    "lock_status",
    "matrix_lever_status",
    "matrix_lever_writer",
    "resolve_writer",
    "written_offset_sec",
]
