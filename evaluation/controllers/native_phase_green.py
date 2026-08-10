# v3 N4-3 - 제어 SC 의 movement 별 native 녹색배분(share)을 실 .sig 타임라인에서 뽑는다
"""Derive per-movement native green shares for controlled signal controllers.

## 왜 필요한가

러너는 SG 상태를 이름 부분문자열로만 정한다(`run_real_world_stackelberg_controller.vbs`
`SignalStateForGroup`). EB/WB 는 major, NB/SB 는 minor 다. 그래서 모델은 제어 15 SC 를
전부 2현시로 본다. 실 `.sig` 는 그렇지 않다 - SC1001 은 주기 150 s 에 SG 8개이고
녹색분율이 0.120~0.340 으로 갈린다. 2현시 근사는 이를 축별 한 값으로 뭉개
좌회전 녹색을 최대 5.00배 과대평가한다(`outputs/signal_group_timing_v3.json`).

## 무엇을 하는가

축(=모델 phase)이 받는 native 녹색 **합집합**을 분모로, movement 가 잡는 SG 들의
native 녹색 합집합을 분자로 삼아 배분(share) ∈ (0, 1] 을 만든다.

    share(m) = union_green(m 의 SG 들) / union_green(축의 SG 들)

이 정규화를 고른 이유는 셋이다.

1. 분자의 SG 집합이 분모의 부분집합이므로 share <= 1 이 구조적으로 보장된다.
   clamp 로 덮는 fail-open 이 생기지 않는다.
2. 축의 녹색 예산을 보존한다 - 서로 겹치지 않는 movement 들의 share 합이 1 이다.
3. **N=2 에서 share 가 정확히 1.0 이다.** 2현시 프로그램은 한 축의 SG 들이 같은
   녹색창을 쓰므로 분자와 분모가 같은 값이 되고, 호출부는 배분을 곱하지 않고
   원본 경로로 그대로 내려간다(비트동일).

## 무엇을 하지 않는가

movement -> SG 매핑의 정밀도는 여기서 올리지 않는다. 신호두의 `lane` 은 링크 단위라
한 접근로의 직진과 좌회전이 같은 SG 집합으로 묶인다(N4-2 가 커넥터 추적으로 풀 몫이다).
매핑이 없는 movement 는 **조용히 통과시키지 않는다** - 사유와 함께 미해결로 계상하고
진단으로 내보낸다. 값은 기존 2현시 경로 그대로 두되, 몇 개가 그렇게 남았는지는 숨기지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


# (intersection, phase, origin, approach) - `movement_signal_groups` 가 보는 필드 전부다.
ShareKey = tuple[str, str, str, str]

_UNRESOLVED_REASONS = (
    "no_schedule",
    "no_signal_group_mapping",
    "axis_mismatch",
    "no_axis_green",
)


def union_green_seconds(program, group_ids: Iterable[str]) -> float:
    """SG 집합이 한 주기 안에서 녹색인 시간의 합집합[s]."""
    spans: list[tuple[float, float]] = []
    for group_id in group_ids:
        timeline = program.sg_timelines.get(str(group_id))
        if timeline is None:
            continue
        for interval in timeline.intervals:
            if interval.state == "GREEN":
                spans.append((interval.start_sec, interval.end_sec))
    total = 0.0
    right_edge = float("-inf")
    for left, right in sorted(spans):
        if left > right_edge:
            total += right - left
            right_edge = right
        elif right > right_edge:
            total += right - right_edge
            right_edge = right
    return total


def signal_group_green_fractions(program) -> dict[str, float]:
    """SG id -> native 녹색분율(녹색 합 / 주기). `.sig` 가 유일한 근거다."""
    cycle = float(program.cycle_length_sec)
    if cycle <= 0.0:
        raise ValueError(f"program {program.controller_id} has a non-positive cycle")
    return {
        sg_id: union_green_seconds(program, (sg_id,)) / cycle
        for sg_id in program.sg_timelines
    }


def _share_key(spec: Mapping[str, Any]) -> ShareKey:
    return (
        str(spec.get("intersection", "")),
        str(spec.get("phase", "")),
        str(spec.get("origin", "")),
        str(spec.get("approach", "")),
    )


def _exact_signal_groups(schedule, spec: Mapping[str, Any]) -> tuple[str, ...]:
    """origin/approach 로 **정확히** 잡히는 SG 만 돌려준다.

    `FixedControllerSchedule.movement_signal_groups` 의 각도 근접 fallback 은 쓰지 않는다.
    그것은 어떤 movement 에도 빈 값을 돌려주지 않으므로 미해결을 미해결로 셀 수 없다.
    """
    origin = str(spec.get("origin", ""))
    if origin in schedule.origin_signal_groups:
        return tuple(schedule.origin_signal_groups[origin])
    leg = str(spec.get("approach", "")).split("_", 1)[0]
    if leg in schedule.approach_signal_groups:
        return tuple(schedule.approach_signal_groups[leg])
    return ()


@dataclass(frozen=True)
class NativePhaseShareTable:
    """제어 movement 의 native 녹색배분표. 배분이 1.0 인 항목은 담지 않는다."""

    shares: Mapping[ShareKey, float]
    unresolved: Mapping[str, str]
    unit_share_movements: tuple[str, ...]
    scaled_movements: tuple[str, ...]
    missing_schedule_nodes: tuple[str, ...]

    def share_for(self, spec: Mapping[str, Any]) -> float | None:
        """곱해야 할 배분. `None` 이면 원본 2현시 경로를 그대로 쓴다."""
        return self.shares.get(_share_key(spec))

    @property
    def diagnostics(self) -> dict[str, Any]:
        reasons: dict[str, float] = {name: 0.0 for name in _UNRESOLVED_REASONS}
        for reason in self.unresolved.values():
            reasons[reason] = reasons.get(reason, 0.0) + 1.0
        values = list(self.shares.values())
        return {
            "native_phase_share_movement_count": float(
                len(self.scaled_movements)
                + len(self.unit_share_movements)
                + len(self.unresolved)
            ),
            "native_phase_share_scaled_count": float(len(self.scaled_movements)),
            "native_phase_share_unit_count": float(len(self.unit_share_movements)),
            "native_phase_share_unresolved_count": float(len(self.unresolved)),
            "native_phase_share_unresolved_reasons": reasons,
            "native_phase_share_min": min(values) if values else 1.0,
            "native_phase_share_missing_signal_nodes": ",".join(
                self.missing_schedule_nodes
            ),
        }


def build_native_phase_share_table(
    urban_movements: Mapping[str, Mapping[str, Any]],
    schedules: Mapping[str, Any],
) -> NativePhaseShareTable:
    """phase 를 가진 movement 마다 native 배분을 계산한다.

    phase 가 빈 movement(=monitor 노드)는 여기 대상이 아니다. 그쪽은
    `FixedControllerSchedule` 이 통째로 native 타임라인을 돌려준다.
    """
    shares: dict[ShareKey, float] = {}
    unresolved: dict[str, str] = {}
    unit_movements: list[str] = []
    scaled_movements: list[str] = []
    missing_nodes: set[str] = set()
    axis_green_cache: dict[tuple[str, str], float] = {}

    for name, spec in urban_movements.items():
        phase = str(spec.get("phase", ""))
        if not phase:
            continue
        node = str(spec.get("intersection", ""))
        schedule = schedules.get(node)
        if schedule is None:
            unresolved[str(name)] = "no_schedule"
            missing_nodes.add(node)
            continue

        group_ids = _exact_signal_groups(schedule, spec)
        if not group_ids:
            unresolved[str(name)] = "no_signal_group_mapping"
            continue

        axis = phase.rpartition("_")[2]
        axis_group_ids = tuple(schedule.phase_signal_groups.get(axis, ()))
        if not set(group_ids) <= set(axis_group_ids):
            # 축이 어긋나면 분자와 분모가 다른 현시를 재는 셈이다. 섞지 않고 남긴다.
            unresolved[str(name)] = "axis_mismatch"
            continue

        cache_key = (node, axis)
        axis_green = axis_green_cache.get(cache_key)
        if axis_green is None:
            axis_green = union_green_seconds(schedule.program, axis_group_ids)
            axis_green_cache[cache_key] = axis_green
        if axis_green <= 0.0:
            unresolved[str(name)] = "no_axis_green"
            continue

        share = union_green_seconds(schedule.program, group_ids) / axis_green
        if share == 1.0:
            unit_movements.append(str(name))
            continue
        shares[_share_key(spec)] = share
        scaled_movements.append(str(name))

    return NativePhaseShareTable(
        shares=shares,
        unresolved=unresolved,
        unit_share_movements=tuple(unit_movements),
        scaled_movements=tuple(scaled_movements),
        missing_schedule_nodes=tuple(sorted(missing_nodes)),
    )


__all__ = [
    "NativePhaseShareTable",
    "ShareKey",
    "build_native_phase_share_table",
    "signal_group_green_fractions",
    "union_green_seconds",
]
