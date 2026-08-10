# v3 N4-6 - 명령한 신호가 VISSIM 에 그 시각에 들어갔는지 되읽어 판정하는 oracle (D-core)
"""Verify that the commanded signal timing was actually realized in VISSIM.

## 무엇을 판정하는가

여기가 틀리면 아래의 모든 동적 검증이 엉뚱한 것을 측정한다. 그래서 D-core 는
"증거 출처 관리"가 아니라 **액추에이션 충실도**다.

## valid-interval 계약 — 언제부터 언제까지 그 값이 유효한가

러너는 매초 돌지 않는다(`run_real_world_stackelberg_controller.vbs`
`RunEventContinuousMode`). 다음 이벤트 초까지 `RunContinuous` 로 달린 뒤 그 초에서

    1. `ValidateRuntimeSignalPersistence t'`  <- 직전에 쓴 값을 되읽는다 (stage=post_step)
    2. (주기가 되면) `RunControllerDecision t'`
    3. `ApplyRuntimeSignals t'`               <- 새 값을 쓰고 곧바로 되읽는다 (stage=immediate)

따라서 `signal_readback.csv` 의 한 줄이 입증하는 것은 다음과 같다.

    stage=immediate  (sim_sec=t): t 시점에 쓴 값이 **그 자리에서** 되읽혔다.
    stage=post_step  (sim_sec=t'): t 에 쓴 값이 t' 까지 **유지**되었다.

즉 값 `v` 의 유효 구간은 `[t, t')` 이고, 증거는 **양 끝점 두 표본뿐**이다.
구간 내부는 표본이 없다. 이 사실을 숨기면 안 된다 - `interior_sampled=False` 로 보고한다.

## 왜 전이 시각 게이트가 BLOCKED 인가

계획의 녹색창 경계는 실수다(지시 축 녹색 x native 분율). 러너는 정수 초에서만 쓴다.
그래서 실현 전이 시각은 의도 시각의 **올림**이고 오차가 최대 1 s 다. 계획의 D-core
게이트는 `<= 0.5 s` 를 요구한다. readback 해상도(1 s)가 게이트보다 거칠므로 이 게이트는
**측정 불가**이며, 계획 v2.1 J-4 의 분기대로 PASS 가 아니라 `BLOCKED` 다.
`command_quantization_sec` 게이트가 그 양자화 오차를 **실 런 없이** 수치로 낸다.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "signal-timing-oracle-v3"

# 러너가 신호를 쓰는 시각 격자[초]. 이벤트 스케줄러가 정수 초에서만 멈춘다.
READBACK_RESOLUTION_SEC = 1.0
# 계획(IMPLEMENTATION_PLAN_V3_LEAN.md N4-6)이 요구하는 전이 시각 오차 상한[초].
TRANSITION_TIME_GATE_SEC = 0.5

TOUCH_EPS_SEC = 1.0e-9

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
NOT_EVALUATED = "NOT_EVALUATED"


def intended_state(
    windows: Sequence[tuple[float, float]], pos: float, cycle: float, amber_sec: float
) -> str:
    """러너 `SignalGroupStateFromPlan` 과 같은 판정. 창이 없으면 영구 적색이다."""
    if cycle <= 0.0:
        return "RED"
    position = math.fmod(float(pos), float(cycle))
    if position < 0.0:
        position += float(cycle)
    for start, end in windows:
        if start <= position < end:
            return "GREEN"
    for _, end in windows:
        amber_end = end + float(amber_sec)
        if end <= position < amber_end:
            return "AMBER"
        if amber_end > cycle and position < amber_end - cycle:
            return "AMBER"
    return "RED"


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def decisions_from_action_rows(action_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """action 로그의 `signal_sg` 행을 결정 시각별 계획으로 접는다.

    한 결정은 `sim_sec` 하나에 실린 모든 행이다. 그 계획의 유효 구간은
    `[sim_sec, 다음 결정의 sim_sec)` 이다.
    """
    by_time: dict[float, dict[str, Any]] = {}
    for row in action_rows or ():
        kind = str(row.get("kind", "")).strip().lower()
        if kind not in ("signal", "signal_sg"):
            continue
        sim_sec = _as_float(row.get("sim_sec"))
        sc_no = str(int(_as_float(row.get("sc_no"))))
        entry = by_time.setdefault(sim_sec, {"sim_sec": sim_sec, "controllers": {}})
        controller = entry["controllers"].setdefault(
            sc_no, {"cycle_sec": 0.0, "offset_sec": 0.0, "windows": {}}
        )
        if kind == "signal":
            controller["offset_sec"] = _as_float(row.get("offset"))
            controller["axis_cycle_sec"] = (
                _as_float(row.get("major_green")) + _as_float(row.get("minor_green"))
            )
        else:
            sg_no = str(int(_as_float(row.get("dsd_no"))))
            controller["cycle_sec"] = _as_float(row.get("green_sec"))
            controller["offset_sec"] = _as_float(row.get("offset"))
            controller["windows"].setdefault(sg_no, []).append(
                (_as_float(row.get("major_green")), _as_float(row.get("minor_green")))
            )
    decisions = [by_time[key] for key in sorted(by_time)]
    for entry in decisions:
        for controller in entry["controllers"].values():
            for windows in controller["windows"].values():
                windows.sort()
    return decisions


def _decision_at(decisions: Sequence[Mapping[str, Any]], sim_sec: float) -> Mapping[str, Any] | None:
    chosen = None
    for entry in decisions:
        if float(entry["sim_sec"]) <= sim_sec + TOUCH_EPS_SEC:
            chosen = entry
        else:
            break
    return chosen


def _gate(
    name: str,
    status: str,
    detail: str,
    count: int = 0,
    value: float | None = None,
    needs: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "count": int(count),
        "value": value,
        "needs": needs,
    }


def _conflict_pairs(plan_table: Mapping[str, Any]) -> dict[str, tuple[tuple[str, str], ...]]:
    table: dict[str, tuple[tuple[str, str], ...]] = {}
    for sc_no, node in (plan_table.get("controllers") or {}).items():
        table[str(int(sc_no))] = tuple(
            (str(pair[0]), str(pair[1])) for pair in node.get("conflict_pairs", ())
        )
    return table


def _overlap(first: tuple[float, float], second: tuple[float, float]) -> float:
    return min(first[1], second[1]) - max(first[0], second[0])


def _plan_self_conflict_gate(decisions, conflicts) -> dict[str, Any]:
    if not decisions:
        return _gate(
            "plan_self_conflict", NOT_EVALUATED, "no signal_sg rows in the action log",
            needs="an action log that carries kind=signal_sg rows",
        )
    violations = 0
    example = ""
    for entry in decisions:
        for sc_no, controller in entry["controllers"].items():
            for first, second in conflicts.get(sc_no, ()):
                for a in controller["windows"].get(first, ()):
                    for b in controller["windows"].get(second, ()):
                        if _overlap(a, b) > TOUCH_EPS_SEC:
                            violations += 1
                            if not example:
                                example = f"sim_sec={entry['sim_sec']} sc={sc_no} sg {first}&{second}"
    if violations:
        return _gate(
            "plan_self_conflict", FAIL,
            f"the delivered plan co-greens a forbidden pair ({example})", violations,
        )
    return _gate(
        "plan_self_conflict", PASS,
        "no forbidden pair overlaps anywhere in the delivered plan (interval arithmetic, whole cycle)",
    )


def _cycle_wrap_gate(decisions) -> dict[str, Any]:
    if not decisions:
        return _gate(
            "cycle_wrap", NOT_EVALUATED, "no signal_sg rows in the action log",
            needs="an action log that carries kind=signal_sg rows",
        )
    bad = 0
    example = ""
    for entry in decisions:
        for sc_no, controller in entry["controllers"].items():
            cycle = float(controller["cycle_sec"])
            for sg_no, windows in controller["windows"].items():
                for start, end in windows:
                    if not (0.0 - TOUCH_EPS_SEC <= start < end <= cycle + TOUCH_EPS_SEC):
                        bad += 1
                        if not example:
                            example = f"sc={sc_no} sg={sg_no} [{start},{end}) cycle={cycle}"
    if bad:
        return _gate("cycle_wrap", FAIL, f"window outside [0, cycle): {example}", bad)
    return _gate(
        "cycle_wrap", PASS,
        "every green window lies inside [0, cycle); the state function wraps with fmod(t+offset, cycle)",
    )


def _quantization_gate(decisions) -> dict[str, Any]:
    """의도한 경계 시각과 러너가 실제로 쓸 수 있는 초 사이의 거리[초].

    실 런이 필요 없다. 계획의 경계가 실수이고 러너가 정수 초에서만 쓰기 때문에
    이 값은 계획만으로 결정된다.
    """
    if not decisions:
        return _gate(
            "command_quantization_sec", NOT_EVALUATED, "no signal_sg rows in the action log",
            needs="an action log that carries kind=signal_sg rows",
        )
    worst = 0.0
    example = ""
    for entry in decisions:
        for sc_no, controller in entry["controllers"].items():
            offset = float(controller["offset_sec"])
            for sg_no, windows in controller["windows"].items():
                for bound in (value for window in windows for value in window):
                    absolute = bound - offset
                    error = math.ceil(absolute - TOUCH_EPS_SEC) - absolute
                    if error > worst:
                        worst = error
                        example = f"sc={sc_no} sg={sg_no} boundary={bound}"
    status = PASS if worst <= TRANSITION_TIME_GATE_SEC + TOUCH_EPS_SEC else FAIL
    return _gate(
        "command_quantization_sec", status,
        f"worst |intended boundary - first writable second| = {worst:.6f} s "
        f"(gate {TRANSITION_TIME_GATE_SEC} s, worst at {example}); "
        "the runner writes signal states only on integer seconds",
        value=worst,
    )


def _min_green_gate(decisions, min_green_sec: float | None) -> dict[str, Any]:
    if not decisions:
        return _gate(
            "min_green_sec", NOT_EVALUATED, "no signal_sg rows in the action log",
            needs="an action log that carries kind=signal_sg rows",
        )
    shortest = None
    example = ""
    for entry in decisions:
        for sc_no, controller in entry["controllers"].items():
            for sg_no, windows in controller["windows"].items():
                total = sum(end - start for start, end in windows)
                if total <= 0.0:
                    continue
                if shortest is None or total < shortest:
                    shortest = total
                    example = f"sc={sc_no} sg={sg_no}"
    if min_green_sec is None:
        return _gate(
            "min_green_sec", NOT_EVALUATED,
            f"shortest planned green = {shortest} s at {example}; no authority declares a minimum",
            value=shortest,
            needs=(
                "a declared per-signal-group minimum green. The .sig programs carry empty "
                "<intergreenmatrices/>, so VISSIM declares none; pass --min-green-sec to gate on it."
            ),
        )
    status = PASS if shortest is not None and shortest >= float(min_green_sec) else FAIL
    return _gate(
        "min_green_sec", status,
        f"shortest planned green = {shortest} s at {example} (threshold {min_green_sec} s)",
        value=shortest,
    )


def _readback_gates(
    decisions, readback_rows, conflicts, amber_sec: float
) -> list[dict[str, Any]]:
    needs = (
        "decisions/signal_readback.csv from a real VISSIM run "
        "(sim_sec,sc_no,sg_no,requested_state,readback_state,ok,stage)"
    )
    names = (
        "request_readback_mismatch",
        "post_step_persistence",
        "intent_vs_request",
        "command_lag_sign",
        "runtime_cogreen",
    )
    if readback_rows is None:
        return [
            _gate(name, NOT_EVALUATED, "no readback log supplied", needs=needs)
            for name in names
        ]

    rows = list(readback_rows)
    immediate = [row for row in rows if str(row.get("stage", "")).strip() == "immediate"]
    post_step = [row for row in rows if str(row.get("stage", "")).strip() == "post_step"]
    # 표본이 0 이면 "위반 0" 이 아니라 "잰 적이 없음"이다. 이 둘을 섞으면 fail-open 이다.
    empty_needs = "a readback log with at least one sample at this stage"

    mismatch = sum(
        1
        for row in immediate
        if str(row.get("requested_state", "")).strip().upper()
        != str(row.get("readback_state", "")).strip().upper()
    )
    persistence = sum(
        1
        for row in post_step
        if str(row.get("requested_state", "")).strip().upper()
        != str(row.get("readback_state", "")).strip().upper()
    )

    intent_bad = 0
    intent_checked = 0
    intent_example = ""
    series: dict[tuple[str, str], list[tuple[float, str]]] = {}
    for row in immediate:
        sim_sec = _as_float(row.get("sim_sec"))
        sc_no = str(int(_as_float(row.get("sc_no"))))
        sg_no = str(int(_as_float(row.get("sg_no"))))
        requested = str(row.get("requested_state", "")).strip().upper()
        series.setdefault((sc_no, sg_no), []).append((sim_sec, requested))
        entry = _decision_at(decisions, sim_sec)
        if entry is None:
            continue
        controller = entry["controllers"].get(sc_no)
        if controller is None:
            continue
        cycle = float(controller["cycle_sec"])
        windows = tuple(controller["windows"].get(sg_no, ()))
        expected = intended_state(
            windows, sim_sec + float(controller["offset_sec"]), cycle, amber_sec
        )
        intent_checked += 1
        if expected != requested:
            intent_bad += 1
            if not intent_example:
                intent_example = (
                    f"sim_sec={sim_sec} sc={sc_no} sg={sg_no} plan={expected} requested={requested}"
                )

    lag_bad = 0
    lag_checked = 0
    lag_example = ""
    for (sc_no, sg_no), samples in series.items():
        samples.sort()
        for index in range(1, len(samples)):
            previous_sec, previous_state = samples[index - 1]
            current_sec, current_state = samples[index]
            if current_state == previous_state:
                continue
            entry = _decision_at(decisions, current_sec)
            if entry is None:
                continue
            controller = entry["controllers"].get(sc_no)
            if controller is None:
                continue
            cycle = float(controller["cycle_sec"])
            offset = float(controller["offset_sec"])
            windows = tuple(controller["windows"].get(sg_no, ()))
            boundary = _intended_boundary(
                windows, previous_sec, current_sec, cycle, offset, amber_sec
            )
            lag_checked += 1
            if boundary is None or current_sec + TOUCH_EPS_SEC < boundary:
                lag_bad += 1
                if not lag_example:
                    lag_example = (
                        f"sc={sc_no} sg={sg_no} written at {current_sec} but the plan changes "
                        f"at {boundary}"
                    )

    cogreen = 0
    cogreen_checked = 0
    cogreen_example = ""
    green_by_time: dict[tuple[float, str], set[str]] = {}
    for row in immediate:
        if str(row.get("requested_state", "")).strip().upper() != "GREEN":
            continue
        key = (_as_float(row.get("sim_sec")), str(int(_as_float(row.get("sc_no")))))
        green_by_time.setdefault(key, set()).add(str(int(_as_float(row.get("sg_no")))))
    for (sim_sec, sc_no), greens in sorted(green_by_time.items()):
        pairs = conflicts.get(sc_no, ())
        if not pairs:
            continue
        cogreen_checked += 1
        for first, second in pairs:
            if first in greens and second in greens:
                cogreen += 1
                if not cogreen_example:
                    cogreen_example = f"sim_sec={sim_sec} sc={sc_no} sg {first}&{second}"

    return [
        _gate(
            "request_readback_mismatch",
            NOT_EVALUATED if not immediate else (PASS if mismatch == 0 else FAIL),
            f"{mismatch} immediate readbacks disagree with the requested state "
            f"({len(immediate)} samples)",
            mismatch,
            needs="" if immediate else empty_needs,
        ),
        _gate(
            "post_step_persistence",
            NOT_EVALUATED if not post_step else (PASS if persistence == 0 else FAIL),
            f"{persistence} post-step readbacks drifted from the requested state "
            f"({len(post_step)} samples)",
            persistence,
            needs="" if post_step else empty_needs,
        ),
        _gate(
            "intent_vs_request",
            NOT_EVALUATED if intent_checked == 0 else (PASS if intent_bad == 0 else FAIL),
            f"{intent_bad}/{intent_checked} written states disagree with the delivered plan "
            f"({intent_example})",
            intent_bad,
            needs=(
                ""
                if intent_checked
                else (
                    "an action log whose kind=signal_sg rows cover the controllers in the readback "
                    "log; without a delivered plan there is nothing to compare the written state to"
                )
            ),
        ),
        _gate(
            "command_lag_sign",
            NOT_EVALUATED if lag_checked == 0 else (PASS if lag_bad == 0 else FAIL),
            f"{lag_bad}/{lag_checked} transitions were written before the plan called for them "
            f"({lag_example})",
            lag_bad,
            needs=(
                ""
                if lag_checked
                else "a readback log containing at least one state transition under a delivered plan"
            ),
        ),
        _gate(
            "runtime_cogreen",
            NOT_EVALUATED if cogreen_checked == 0 else (PASS if cogreen == 0 else FAIL),
            f"{cogreen}/{cogreen_checked} sampled seconds show a forbidden pair both GREEN "
            f"({cogreen_example})",
            cogreen,
            needs=(
                ""
                if cogreen_checked
                else (
                    "a readback log with GREEN samples for a controller that the actuation plan "
                    "declares conflict pairs for"
                )
            ),
        ),
    ]


def _intended_boundary(
    windows: Sequence[tuple[float, float]],
    previous_sec: float,
    current_sec: float,
    cycle: float,
    offset: float,
    amber_sec: float,
) -> float | None:
    """`(previous_sec, current_sec]` 안에서 계획 상태가 바뀌는 절대 시각.

    계획은 주기 좌표이고 러너는 `pos = fmod(t + offset, cycle)` 로 본다. 경계
    후보는 각 창의 시작·끝·끝+amber 이며, 그것을 절대 시각으로 펼쳐 구간에 드는
    것 가운데 가장 이른 것을 돌려준다.
    """
    if cycle <= 0.0:
        return None
    candidates: list[float] = []
    for start, end in windows:
        candidates.extend((start, end, end + float(amber_sec)))
    if not candidates:
        return None
    first_cycle = math.floor((previous_sec + offset) / cycle) - 1
    last_cycle = math.ceil((current_sec + offset) / cycle) + 1
    best: float | None = None
    for index in range(first_cycle, last_cycle + 1):
        for candidate in candidates:
            absolute = candidate + index * cycle - offset
            if previous_sec + TOUCH_EPS_SEC < absolute <= current_sec + TOUCH_EPS_SEC:
                if best is None or absolute < best:
                    best = absolute
    if best is not None:
        return best
    # 구간 안에 경계가 없으면, 가장 가까운 미래 경계를 돌려준다 - 호출부가 이것을
    # "아직 오지 않은 전이를 미리 썼다"로 읽는다.
    future: float | None = None
    for index in range(first_cycle, last_cycle + 2):
        for candidate in candidates:
            absolute = candidate + index * cycle - offset
            if absolute > current_sec + TOUCH_EPS_SEC:
                if future is None or absolute < future:
                    future = absolute
    return future


VALID_INTERVAL_CONTRACT = {
    "statement": (
        "A state written at event second t is the intent for [t, t'), where t' is the next event "
        "second. Evidence exists only at the two endpoints: stage=immediate at t proves the COM "
        "write took, stage=post_step at t' proves it survived the run-continuous span. The "
        "interior of [t, t') is never sampled."
    ),
    "stages": {
        "immediate": "written and read back at t, inside ApplyRuntimeSignals",
        "post_step": "read back at t' by ValidateRuntimeSignalPersistence, before any new write",
    },
    "interior_sampled": False,
    "write_grid_sec": READBACK_RESOLUTION_SEC,
    "source": "run_real_world_stackelberg_controller.vbs RunEventContinuousMode",
}


def evaluate(
    plan_table: Mapping[str, Any],
    action_rows: Iterable[Mapping[str, Any]] | None,
    readback_rows: Iterable[Mapping[str, Any]] | None,
    min_green_sec: float | None = None,
) -> dict[str, Any]:
    """D-core 판정. 측정 불가는 PASS 가 아니라 BLOCKED / NOT_EVALUATED 다."""
    amber_sec = float((plan_table or {}).get("amber_sec", 3.0))
    conflicts = _conflict_pairs(plan_table or {})
    decisions = decisions_from_action_rows(action_rows or ())

    gates: list[dict[str, Any]] = [
        _plan_self_conflict_gate(decisions, conflicts),
        _cycle_wrap_gate(decisions),
        _quantization_gate(decisions),
        _min_green_gate(decisions, min_green_sec),
    ]
    gates.extend(_readback_gates(decisions, readback_rows, conflicts, amber_sec))
    gates.append(
        _gate(
            "transition_time_error_sec",
            BLOCKED,
            f"the D-core gate is {TRANSITION_TIME_GATE_SEC} s but signal states are written and "
            f"read back only on a {READBACK_RESOLUTION_SEC:g} s grid, so the error cannot be "
            "resolved. Per IMPLEMENTATION_PLAN_V3_LEAN.md N4-6 this is BLOCKED, not PASS, and it "
            "keeps the N4-7 offset promotion locked.",
            needs=(
                "sub-second signal readback (a runner that steps and reads back finer than "
                f"{TRANSITION_TIME_GATE_SEC} s), or an agreed relaxation of the gate"
            ),
        )
    )

    statuses = {gate["status"] for gate in gates}
    if FAIL in statuses:
        status = FAIL
    elif BLOCKED in statuses:
        status = BLOCKED
    elif NOT_EVALUATED in statuses:
        status = NOT_EVALUATED
    else:
        status = PASS

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "valid_interval_contract": VALID_INTERVAL_CONTRACT,
        "gates": gates,
        "counts": {
            "decisions": len(decisions),
            "readback_rows": 0 if readback_rows is None else len(list(readback_rows)),
        },
    }


__all__ = [
    "BLOCKED",
    "FAIL",
    "NOT_EVALUATED",
    "PASS",
    "READBACK_RESOLUTION_SEC",
    "SCHEMA_VERSION",
    "TRANSITION_TIME_GATE_SEC",
    "VALID_INTERVAL_CONTRACT",
    "decisions_from_action_rows",
    "evaluate",
    "intended_state",
]
