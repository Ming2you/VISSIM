# v3 N4-5 - 지시된 축 녹색을 SG 단위 녹색창으로 쪼개는 계획(모델 native share 와 같은 정의)
"""Split a commanded axis green into per-signal-group green windows.

## 왜 필요한가

러너는 SG 상태를 이름 부분문자열로 정한다(`run_real_world_stackelberg_controller.vbs`
`SignalStateForGroup`). 한 축의 모든 SG 가 축 녹색 **전체**를 받는다. 모델은 N4-3 이후
그렇게 예측하지 않는다 — `native_phase_green` 이 축 녹색에 native 배분을 곱한다.

    model:  movement m 의 녹색 = 축 녹색 x union_green(m 의 SG) / union_green(축의 SG)

플랜트가 이 식을 재현하려면 축 녹색창을 SG 별로 같은 비율로 쪼개야 한다. 이 모듈이
그 분할을 만든다.

    plant:  SG g 의 녹색 = 축 녹색 x union_green(g) / union_green(축의 SG)

## 어떻게 쪼개는가 — 축 녹색 시간의 단조 재매개화

축의 native 녹색 합집합 U 를 시간축으로 삼는다. `cum(t) = |U ∩ [0,t)|` 로 두고
native 시각 t 를 `cum(t)/|U|` 로 정규화한 뒤, 지시된 축 녹색창에 선형으로 편다.

이 사상이 갖는 성질 셋이 이 설계의 근거다.

1. **배분이 정확히 보존된다.** SG g 의 녹색 길이는 지시 축 녹색 x |g 의 녹색| / |U| 다.
   모델의 share 와 같은 분수다(`ModelSymmetryTests` 가 고정한다).
2. **동시녹색을 새로 만들지 않는다.** cum 은 단조라, native 에서 떨어져 있던 두 SG 는
   편 뒤에도 떨어져 있다. native 에서 겹치던 쌍만 겹친 채로 남는다.
3. **축 녹색 예산이 새지 않는다.** 축 SG 들의 realize 된 녹색 합집합이 지시된 축 녹색창을
   빈틈없이 채운다.

## N4-0 이후 - "축" 은 "현시" 가 됐다

아래 설명의 "축"을 전부 **현시**로 읽어라. v3 은 현시가 둘(major/minor 축)이라 두 말이
같았지만, 모델이 dual-ring 4현시로 옮기면서 한 축 안에 직진 현시와 좌회전 현시가 따로
생겼다. 이 모듈의 분할 방식(native 녹색 합집합의 단조 재매개화)은 그대로이고, 그것이
적용되는 단위가 축에서 현시로 내려갔을 뿐이다.

주기 식만 바뀌었다 - clearance 를 상수 2회가 아니라 **녹색 있는 현시 수**만큼 문다
(`plan_cycle_sec`). 현시가 둘인 계획에서는 v3 과 값이 같다.

## 무엇을 하지 않는가

- 현시의 위치·길이·주기 공식은 건드리지 않는다. 이 모듈은 **현시 안의 분배만** 바꾼다.
- SG -> 모델 phase 귀속은 여기서 만들지 않는다. `outputs/movement_signal_group_map_v3.json`
  의 `phase_signal_groups` 가 정본이고 여기서는 받아서 쓴다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


# 겹침 판정 허용오차[초]. 경계가 맞닿는 것은 겹침이 아니다.
TOUCH_EPS_SEC = 1.0e-9

# 상류 모델(`NumSim-mine/src/models/state.py:MODEL_PHASES`)과 같은 어휘여야 한다.
# 상류는 N4-0 에서 dual-ring 4현시로 옮겼다(commit 3286f47).
MODEL_PHASES = ("p1", "p2", "p3", "p4")


class SignalGroupPlanError(RuntimeError):
    """계획을 만들 수 없다. 조용한 폴백 대신 예외로 올린다."""


@dataclass(frozen=True)
class PlanWindow:
    """한 SG 의 녹색창 하나. 시각은 플랜 주기 좌표계[0, cycle) 안이다."""

    sg_no: str
    window_index: int
    start_sec: float
    end_sec: float


@dataclass(frozen=True)
class NodePlan:
    """한 SC 의 정적 계획. 지시 녹색과 무관한 부분만 담는다."""

    node_id: str
    native_cycle_sec: float
    # phase -> ((sg_no, window_index, start_fraction, end_fraction), ...)
    phase_segments: Mapping[str, tuple[tuple[str, int, float, float], ...]]
    phase_signal_groups: Mapping[str, tuple[str, ...]]
    axis_green_sec: Mapping[str, float]
    window_counts: Mapping[str, int]
    red_only_signal_groups: tuple[str, ...]
    conflict_pairs: tuple[tuple[str, str], ...]


def _sort_key(value: str) -> tuple[int, str]:
    text = str(value)
    return (int(text), text) if text.isdigit() else (2**31 - 1, text)


def _green_windows(program, sg_no: str) -> tuple[tuple[float, float], ...]:
    timeline = program.sg_timelines.get(str(sg_no))
    if timeline is None:
        return ()
    return tuple(
        (float(interval.start_sec), float(interval.end_sec))
        for interval in timeline.intervals
        if interval.state == "GREEN"
    )


def _merge(spans: Iterable[tuple[float, float]]) -> tuple[tuple[float, float], ...]:
    merged: list[tuple[float, float]] = []
    for start, end in sorted(spans):
        if end <= start:
            continue
        if merged and start <= merged[-1][1] + TOUCH_EPS_SEC:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def _cumulative(union: Sequence[tuple[float, float]], t: float) -> float:
    """`|union ∩ [0, t)|`. t 가 union 밖이면 그 앞까지의 길이다."""
    total = 0.0
    for start, end in union:
        if t <= start:
            break
        total += min(t, end) - start
    return total


def build_node_plan(
    node_id: str,
    program,
    phase_signal_groups: Mapping[str, Sequence[str]],
    signal_group_ids: Sequence[str],
) -> NodePlan:
    """한 SC 의 정적 계획을 만든다.

    `program` 은 실제로 VISSIM 이 읽는 `.sig`(inpx `supplyFile2`)에서 파싱된 것이어야 한다.
    파일명 번호로 고른 표를 쓰면 4/15 SC 에서 다른 프로그램을 기술한다
    (`movement_signal_group_map_v3.json` 의 `timing_cross_check`).
    """
    cycle = float(program.cycle_length_sec)
    if cycle <= 0.0:
        raise SignalGroupPlanError(f"{node_id}: non-positive cycle {cycle}")

    all_ids = tuple(str(value) for value in signal_group_ids)
    phased: dict[str, tuple[str, ...]] = {}
    for phase in MODEL_PHASES:
        ids = tuple(str(value) for value in (phase_signal_groups.get(phase) or ()))
        for sg_no in ids:
            if sg_no not in program.sg_timelines:
                raise SignalGroupPlanError(
                    f"{node_id}: phase {phase} lists sg {sg_no} which the active program has no timeline for"
                )
            if sg_no not in all_ids:
                raise SignalGroupPlanError(
                    f"{node_id}: phase {phase} lists sg {sg_no} which the controller does not declare"
                )
        phased[phase] = ids

    for first_index, first_phase in enumerate(MODEL_PHASES):
        for second_phase in MODEL_PHASES[first_index + 1 :]:
            overlap = set(phased[first_phase]) & set(phased[second_phase])
            if overlap:
                raise SignalGroupPlanError(
                    f"{node_id}: signal groups {sorted(overlap, key=_sort_key)} belong to both "
                    f"model phases {first_phase} and {second_phase}"
                )

    segments: dict[str, tuple[tuple[str, int, float, float], ...]] = {}
    axis_green: dict[str, float] = {}
    window_counts: dict[str, int] = {sg_no: 0 for sg_no in all_ids}
    for phase in MODEL_PHASES:
        ids = phased[phase]
        if not ids:
            segments[phase] = ()
            axis_green[phase] = 0.0
            continue
        union = _merge(
            span for sg_no in ids for span in _green_windows(program, sg_no)
        )
        total = sum(end - start for start, end in union)
        if total <= 0.0:
            raise SignalGroupPlanError(
                f"{node_id}: model phase {phase} has signal groups {list(ids)} but no native green"
            )
        axis_green[phase] = total
        rows: list[tuple[str, int, float, float]] = []
        for sg_no in sorted(ids, key=_sort_key):
            for index, (start, end) in enumerate(_green_windows(program, sg_no)):
                low = _cumulative(union, start) / total
                high = _cumulative(union, end) / total
                if not (0.0 <= low < high <= 1.0 + TOUCH_EPS_SEC):
                    raise SignalGroupPlanError(
                        f"{node_id}: sg {sg_no} window {index} ({start},{end}) is not inside the "
                        f"{phase} green union"
                    )
                rows.append((sg_no, index, low, min(high, 1.0)))
                window_counts[sg_no] = window_counts.get(sg_no, 0) + 1
        segments[phase] = tuple(rows)

    phased_ids = set().union(*(set(phased[phase]) for phase in MODEL_PHASES))
    red_only = tuple(sg_no for sg_no in all_ids if sg_no not in phased_ids)

    conflicts: list[tuple[str, str]] = []
    active = sorted(
        (sg_no for sg_no in all_ids if window_counts.get(sg_no, 0) > 0), key=_sort_key
    )
    for index, first in enumerate(active):
        first_windows = _green_windows(program, first)
        for second in active[index + 1 :]:
            second_windows = _green_windows(program, second)
            overlaps = any(
                min(a1, b1) - max(a0, b0) > TOUCH_EPS_SEC
                for a0, a1 in first_windows
                for b0, b1 in second_windows
            )
            if not overlaps:
                conflicts.append((first, second))

    return NodePlan(
        node_id=str(node_id),
        native_cycle_sec=cycle,
        phase_segments=segments,
        phase_signal_groups={phase: phased[phase] for phase in MODEL_PHASES},
        axis_green_sec=axis_green,
        window_counts=window_counts,
        red_only_signal_groups=red_only,
        conflict_pairs=tuple(conflicts),
    )


def live_phases(phase_greens: Mapping[str, float]) -> tuple[str, ...]:
    """녹색을 실제로 받는 현시. 주기에 clearance 를 몇 번 무는지가 이 개수로 정해진다.

    녹색 0 인 현시는 전이도 없다. 2현시 계획에서 p3/p4 가 0 이면 clearance 는 2회이고
    v3 의 주기 식과 정확히 같은 값이 나온다.
    """
    return tuple(
        phase for phase in MODEL_PHASES if float(phase_greens.get(phase, 0.0)) > 0.0
    )


def plan_cycle_sec(
    phase_greens: Mapping[str, float], amber_sec: float, all_red_sec: float
) -> float:
    """러너의 주기 공식 그대로 - 녹색 합 + (녹색 있는 현시 수) x clearance.

    v3 는 축이 둘이라 clearance 를 항상 두 번 물었다. 4현시가 되면 축 **안의** 경계도
    전이가 되므로 계수가 현시 수를 따라간다. 2현시 데이터에서는 값이 v3 과 같다.
    """
    clearance = float(amber_sec) + float(all_red_sec)
    used = live_phases(phase_greens)
    return sum(float(phase_greens[phase]) for phase in used) + len(used) * clearance


def phase_layout_order(major_maps_to: str) -> tuple[str, ...]:
    """녹색창을 주기 안에 놓는 순서.

    major 축 현시가 맨 앞이다 - v3 의 `axis_window` 배치(major 를 [0, major) 에 두고
    minor 를 그 뒤에 두는 것)와 2현시에서 **비트 동일**하게 만드는 조건이다.

    나머지 셋의 상대 순서는 모델 phase 순서로 둔다. 목표 스펙의 현시 순서
    (major 직진 -> major 좌 -> minor 직진 -> minor 좌)는 phase -> 이동류 귀속이 정해져야
    쓸 수 있고, 그 귀속은 `.sig` 재작성(작업 1)이 막혀 아직 없다. 4현시 계획이 실제로
    생기면 이 함수가 그 순서를 받아야 한다.
    """
    major_phase = str(major_maps_to).strip().lower()
    if major_phase not in MODEL_PHASES:
        raise SignalGroupPlanError(
            f"major_maps_to must be one of {MODEL_PHASES}, got {major_maps_to!r}"
        )
    return (major_phase,) + tuple(
        phase for phase in MODEL_PHASES if phase != major_phase
    )


def plan_windows(
    plan: NodePlan,
    phase_greens: Mapping[str, float],
    phase_order: Sequence[str],
    amber_sec: float,
    all_red_sec: float,
) -> tuple[PlanWindow, ...]:
    """지시된 현시 녹색을 SG 녹색창으로 편다.

    `phase_order` 는 주기 안의 배치 순서다. 녹색 0 인 현시는 자리를 차지하지 않는다.
    """
    order = tuple(str(phase).strip().lower() for phase in phase_order)
    if sorted(order) != sorted(MODEL_PHASES):
        raise SignalGroupPlanError(
            f"{plan.node_id}: phase_order must be a permutation of {MODEL_PHASES}, got {order}"
        )
    clearance = float(amber_sec) + float(all_red_sec)
    rows: list[PlanWindow] = []
    cursor = 0.0
    for phase in order:
        span = float(phase_greens.get(phase, 0.0))
        if span <= 0.0:
            continue
        for sg_no, index, low, high in plan.phase_segments.get(phase, ()):
            rows.append(
                PlanWindow(
                    sg_no=sg_no,
                    window_index=index,
                    start_sec=cursor + low * span,
                    end_sec=cursor + high * span,
                )
            )
        cursor += span + clearance
    rows.sort(key=lambda row: (_sort_key(row.sg_no), row.window_index))
    return tuple(rows)


def conflict_violations(
    windows: Iterable[PlanWindow], conflict_pairs: Iterable[tuple[str, str]]
) -> tuple[str, ...]:
    """충돌 쌍이 동시에 녹색인 구간을 전부 사유 문자열로 돌려준다."""
    by_group: dict[str, list[tuple[float, float]]] = {}
    for window in windows:
        by_group.setdefault(str(window.sg_no), []).append(
            (float(window.start_sec), float(window.end_sec))
        )
    violations: list[str] = []
    for first, second in conflict_pairs:
        for a0, a1 in by_group.get(str(first), ()):
            for b0, b1 in by_group.get(str(second), ()):
                low = max(a0, b0)
                high = min(a1, b1)
                if high - low > TOUCH_EPS_SEC:
                    violations.append(
                        f"sg {first} and sg {second} are both green on [{low}, {high})"
                    )
    return tuple(violations)


def node_plan_to_json(plan: NodePlan) -> dict[str, Any]:
    return {
        "node_id": plan.node_id,
        "native_cycle_sec": plan.native_cycle_sec,
        "phase_signal_groups": {
            phase: list(plan.phase_signal_groups.get(phase, ()))
            for phase in MODEL_PHASES
        },
        "axis_green_sec": {phase: plan.axis_green_sec.get(phase, 0.0) for phase in MODEL_PHASES},
        "phase_segments": {
            phase: [
                {
                    "sg_no": sg_no,
                    "window_index": index,
                    "start_fraction": low,
                    "end_fraction": high,
                }
                for sg_no, index, low, high in plan.phase_segments.get(phase, ())
            ]
            for phase in MODEL_PHASES
        },
        "window_counts": {key: int(value) for key, value in sorted(
            plan.window_counts.items(), key=lambda item: _sort_key(item[0])
        )},
        "red_only_signal_groups": list(plan.red_only_signal_groups),
        "conflict_pairs": [list(pair) for pair in plan.conflict_pairs],
    }


def node_plan_from_json(payload: Mapping[str, Any]) -> NodePlan:
    segments: dict[str, tuple[tuple[str, int, float, float], ...]] = {}
    raw_segments = payload.get("phase_segments") or {}
    for phase in MODEL_PHASES:
        segments[phase] = tuple(
            (
                str(item["sg_no"]),
                int(item["window_index"]),
                float(item["start_fraction"]),
                float(item["end_fraction"]),
            )
            for item in raw_segments.get(phase, ())
        )
    raw_phase_groups = payload.get("phase_signal_groups") or {}
    raw_axis_green = payload.get("axis_green_sec") or {}
    return NodePlan(
        node_id=str(payload.get("node_id", "")),
        native_cycle_sec=float(payload.get("native_cycle_sec", 0.0)),
        phase_segments=segments,
        phase_signal_groups={
            phase: tuple(str(value) for value in raw_phase_groups.get(phase, ()))
            for phase in MODEL_PHASES
        },
        axis_green_sec={
            phase: float(raw_axis_green.get(phase, 0.0)) for phase in MODEL_PHASES
        },
        window_counts={
            str(key): int(value)
            for key, value in (payload.get("window_counts") or {}).items()
        },
        red_only_signal_groups=tuple(
            str(value) for value in payload.get("red_only_signal_groups", ())
        ),
        conflict_pairs=tuple(
            (str(pair[0]), str(pair[1])) for pair in payload.get("conflict_pairs", ())
        ),
    )


__all__ = [
    "MODEL_PHASES",
    "NodePlan",
    "PlanWindow",
    "SignalGroupPlanError",
    "build_node_plan",
    "conflict_violations",
    "live_phases",
    "node_plan_from_json",
    "node_plan_to_json",
    "phase_layout_order",
    "plan_cycle_sec",
    "plan_windows",
]
