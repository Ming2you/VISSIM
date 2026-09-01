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

## N4-2 이후 - 매핑 산출물이 먼저다

`scripts/derive_movement_signal_group_map.py` 가 만드는
`outputs/movement_signal_group_map_v3.json` 을 `signal_group_map` 으로 넘기면 분자(movement 의
SG)와 분모(모델 phase 의 SG)를 둘 다 그 산출물에서 읽는다. 산출물에 없는 노드만 아래의
이름/leg 규칙으로 떨어지고, 그 건수는 `native_phase_share_name_fallback_count` 와
`native_phase_share_axis_name_fallback_count` 로 나간다. 실런 산출물 기준 둘 다 0 이다.

`signal_group_map=None` 이면 직전 판과 **완전히 같은 경로**다(되돌림용).
"""

from __future__ import annotations

import os

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


# (intersection, phase, origin, approach) - `movement_signal_groups` 가 보는 필드 전부다.
ShareKey = tuple[str, str, str, str]


# 본선 SG 상한. 이보다 큰 SG 는 미드블록이라 본선 신호가 통제하지 않는다.
MAINLINE_SG_MAX = 8


def _mainline_share_enabled() -> bool:
    """share 계산에서 미드블록 SG(9+)를 뺄지. 기본 꺼짐 = 비트 동일.

    **왜 필요한가.** `share = union_green(movement SG) / union_green(축 SG)` 인데,
    미드블록 SG 는 현시 전체를 덮는다. 실측(SC5 액추에이션 계획의 창 분율):

        p3:  SG2 0.4653 · SG6 0.4653 · **SG10 1.0 · SG14 1.0**
        p1:  SG4 0.4433 · SG8 0.4433 · **SG20 1.0 · SG24 1.0**

    그래서 분모가 현시 전체가 되고, movement 의 SG 집합에 미드블록이 하나라도 들어가면
    분자도 전체가 되어 **share = 1.0** 으로 뭉개진다. `RW_NARROW_AXIS_SG=1` 로 좁히기를
    켠 실런(narrowaxis)에서 movement 263개 중 **170개가 share=1.0**, 실제로 깎인 것은
    **4개**뿐이었다 — 보정이 98% 무력화된 것이다.

    그런데 플랜트는 본선 SG 창만큼만 배달한다. 실측(conv, 1초 되읽기, 12주기):

        SC5 p1  주문 54.5s x 0.4433 = 24.2s  =  **실측 24.2 s/cycle**
        SC5 p3  주문 22.7s x 0.4653 = 10.6s  =  **실측 11.0 s/cycle**

    미드블록 SG 는 러너가 COM 으로 건드리지 않아 native 프로그램대로 돌고
    (`RW_MAINLINE_SG_ONLY` 는 러너에만 있고 여기엔 적용되지 않았다), 본선 movement 의
    서비스와 무관하다. 그것을 분모·분자에 넣는 것 자체가 틀렸다.

    켜면 SG 1-8 만으로 비율을 낸다 — 그러면 SC5 p3 가 0.4653 을 받는다.
    """
    return str(os.environ.get("RW_MAINLINE_SHARE_SG", "")).strip().lower() in {"1", "true", "on"}


def _mainline_only(group_ids):
    """SG 1-8 만 남긴다. 남는 게 없으면 원본을 그대로 돌려준다(정보 없음 = 안 건드림)."""
    kept = tuple(g for g in group_ids if str(g).isdigit() and int(g) <= MAINLINE_SG_MAX)
    return kept if kept else tuple(group_ids)


def _narrow_axis_enabled() -> bool:
    """movement SG 를 자기 현시 SG 로 교집합해 살릴지. 기본 꺼짐.

    이 경로는 **생산** 컨트롤러가 쓴다. 실런 검증 전에 거동을 바꾸지 않는다.
    """
    return str(os.environ.get("RW_NARROW_AXIS_SG", "")).strip().lower() in {"1", "true", "on"}

_UNRESOLVED_REASONS = (
    "no_schedule",
    "no_signal_group_mapping",
    "axis_mismatch",
    "no_axis_green",
    # 아래 넷은 N4-2 매핑 산출물 경로의 사유다. `origin_not_in_map` 은 산출물이 만들어진
    # 뒤 config 가 바뀐 경우(=산출물 낡음)로, 다른 사유와 후속 조치가 다르다.
    "synthetic_boundary_leg",
    "origin_link_unknown",
    "no_signal_head_downstream",
    "origin_not_in_map",
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


def _mapped_node(signal_group_map: Mapping[str, Any] | None, node: str):
    """매핑 산출물에서 이 노드의 항목. 없으면 `None` 이고 호출부가 이름 규칙으로 떨어진다."""
    if signal_group_map is None:
        return None
    controllers = signal_group_map.get("controllers") or {}
    return controllers.get(node)


@dataclass(frozen=True)
class NativePhaseShareTable:
    """제어 movement 의 native 녹색배분표. 배분이 1.0 인 항목은 담지 않는다."""

    shares: Mapping[ShareKey, float]
    unresolved: Mapping[str, str]
    unit_share_movements: tuple[str, ...]
    scaled_movements: tuple[str, ...]
    missing_schedule_nodes: tuple[str, ...]
    map_enabled: bool = False
    name_fallback_movements: tuple[str, ...] = ()
    axis_name_fallback_movements: tuple[str, ...] = ()

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
            "native_phase_share_map_enabled": 1.0 if self.map_enabled else 0.0,
            "native_phase_share_name_fallback_count": float(
                len(self.name_fallback_movements)
            ),
            "native_phase_share_axis_name_fallback_count": float(
                len(self.axis_name_fallback_movements)
            ),
        }


def build_native_phase_share_table(
    urban_movements: Mapping[str, Mapping[str, Any]],
    schedules: Mapping[str, Any],
    signal_group_map: Mapping[str, Any] | None = None,
) -> NativePhaseShareTable:
    """phase 를 가진 movement 마다 native 배분을 계산한다.

    phase 가 빈 movement(=monitor 노드)는 여기 대상이 아니다. 그쪽은
    `FixedControllerSchedule` 이 통째로 native 타임라인을 돌려준다.

    `signal_group_map` 은 `derive_movement_signal_group_map.derive()` 산출물이다. 넘기면
    분자·분모를 그 산출물에서 읽고, 산출물에 없는 노드만 이름/leg 규칙으로 떨어진다.
    """
    shares: dict[ShareKey, float] = {}
    unresolved: dict[str, str] = {}
    unit_movements: list[str] = []
    scaled_movements: list[str] = []
    missing_nodes: set[str] = set()
    name_fallback: list[str] = []
    axis_name_fallback: list[str] = []
    # 자기 현시 SG 로 좁혀서 살린 movement (RW_NARROW_AXIS_SG).
    narrowed_movements: list[str] = []
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

        mapped = _mapped_node(signal_group_map, node)
        if mapped is None:
            name_fallback.append(str(name))
            group_ids = _exact_signal_groups(schedule, spec)
            if not group_ids:
                unresolved[str(name)] = "no_signal_group_mapping"
                continue
        else:
            origin = str(spec.get("origin", ""))
            entry = (mapped.get("origin_signal_groups") or {}).get(origin)
            if entry is None:
                # 산출물이 이 origin 을 이미 사유와 함께 미해결로 계상했다. 덮지 않는다.
                unresolved[str(name)] = str(
                    (mapped.get("unresolved_origins") or {}).get(origin)
                    or "origin_not_in_map"
                )
                continue
            group_ids = tuple(str(value) for value in entry.get("signal_groups", ()))
            if not group_ids:
                unresolved[str(name)] = "no_signal_group_mapping"
                continue

        axis = phase.rpartition("_")[2]
        if mapped is None:
            axis_name_fallback.append(str(name))
            axis_group_ids = tuple(schedule.phase_signal_groups.get(axis, ()))
        else:
            axis_group_ids = tuple(
                str(value)
                for value in (mapped.get("phase_signal_groups") or {}).get(axis, ())
            )
        if not set(group_ids) <= set(axis_group_ids):
            # 축이 어긋나는 이유는 거의 항상 하나다 - `group_ids` 가 origin **링크**의
            # 신호두에서 오므로 한 접근로의 직진과 보호좌회전이 한 덩어리로 섞인다.
            # 그래서 자기 현시(axis)의 부분집합이 될 수 없다.
            #
            # 2026-08-16 실측: 이 교집합이 옳다. 검증 rollout 에서 movement 를 자기 현시
            # SG 로 좁히니 스텝1 보존단위 오차가 44.9% -> 36.4%, G5 32.4% -> 38.8% 였다.
            # 좁히지 않으면 union 녹색이 단일 SG 의 중앙값 1.39배(최대 2.96배)라 방출이
            # 과대해지고, 직진이 보호좌회전 현시에까지 흐른다.
            #
            # 기본은 종전대로 남긴다(RW_NARROW_AXIS_SG 로 켠다) - 이 경로는 **생산**
            # 컨트롤러가 쓰므로 실런 검증 전에 거동을 바꾸지 않는다.
            narrowed = tuple(g for g in group_ids if g in set(axis_group_ids))
            if _narrow_axis_enabled() and narrowed:
                group_ids = narrowed
                narrowed_movements.append(str(name))
            else:
                unresolved[str(name)] = "axis_mismatch"
                continue

        cache_key = (node, axis)
        axis_green = axis_green_cache.get(cache_key)
        if axis_green is None:
            axis_ids = _mainline_only(axis_group_ids) if _mainline_share_enabled() else axis_group_ids
            axis_green = union_green_seconds(schedule.program, axis_ids)
            axis_green_cache[cache_key] = axis_green
        if axis_green <= 0.0:
            unresolved[str(name)] = "no_axis_green"
            continue

        mv_ids = _mainline_only(group_ids) if _mainline_share_enabled() else group_ids
        share = union_green_seconds(schedule.program, mv_ids) / axis_green
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
        map_enabled=signal_group_map is not None,
        name_fallback_movements=tuple(name_fallback),
        axis_name_fallback_movements=tuple(axis_name_fallback),
    )


__all__ = [
    "NativePhaseShareTable",
    "ShareKey",
    "build_native_phase_share_table",
    "signal_group_green_fractions",
    "union_green_seconds",
]
