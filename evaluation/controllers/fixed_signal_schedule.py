"""Compile VISSIM fixed-time programs for monitoring-only rollout nodes."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Iterable, Mapping
import xml.etree.ElementTree as ET

from plant.src.vissim_strict.signal_program import ControllerProgram, parse_sig


NS_AXIS = frozenset({"N", "S", "NW", "SE"})
_DIRECTION_DEGREES = {
    "N": 0.0,
    "NE": 45.0,
    "E": 90.0,
    "SE": 135.0,
    "S": 180.0,
    "SW": 225.0,
    "W": 270.0,
    "NW": 315.0,
}


def _sort_id(value: str) -> tuple[int, str]:
    try:
        return int(value), value
    except ValueError:
        return 2**31 - 1, value


def _axis_for_signal_group(group_no: str, group_name: str) -> str:
    name = group_name.upper()
    if "EB" in name or "WB" in name:
        return "p2"
    if "NB" in name or "SB" in name:
        return "p1"
    if group_no == "1":
        return "p2"
    if group_no == "2":
        return "p1"
    return ""


def movement_phase(spec: Mapping[str, object], available_phases: Iterable[str]) -> str:
    phases = set(available_phases)
    approach = str(spec.get("approach", ""))
    direction = approach.split("_", 1)[0]
    inferred = "p1" if direction in NS_AXIS else "p2"
    if inferred in phases:
        return inferred
    if len(phases) == 1:
        return next(iter(phases))
    return ""


@dataclass(frozen=True)
class FixedControllerSchedule:
    node_id: str
    program: ControllerProgram
    controller_offset_sec: float
    phase_signal_groups: Mapping[str, tuple[str, ...]]
    origin_signal_groups: Mapping[str, tuple[str, ...]]
    approach_signal_groups: Mapping[str, tuple[str, ...]]

    def movement_signal_groups(self, spec: Mapping[str, object]) -> tuple[str, ...]:
        origin = str(spec.get("origin", ""))
        if origin in self.origin_signal_groups:
            return self.origin_signal_groups[origin]
        approach = str(spec.get("approach", "")).split("_", 1)[0]
        if approach in self.approach_signal_groups:
            return self.approach_signal_groups[approach]
        target = _DIRECTION_DEGREES.get(approach)
        candidates = [
            (leg, groups, _angular_distance(target, angle))
            for leg, groups in self.approach_signal_groups.items()
            if groups and target is not None and (angle := _DIRECTION_DEGREES.get(leg)) is not None
        ]
        if candidates:
            best = min(item[2] for item in candidates)
            return tuple(
                sorted(
                    {group for _, groups, distance in candidates if distance == best for group in groups},
                    key=_sort_id,
                )
            )
        phase = movement_phase(spec, self.phase_signal_groups)
        return self.phase_signal_groups.get(phase, ())

    def green_fraction(
        self,
        phase: str,
        start_sec: float | None = None,
        duration_sec: float | None = None,
    ) -> float:
        group_ids = self.phase_signal_groups.get(phase, ())
        return self._green_fraction(group_ids, start_sec, duration_sec)

    def movement_green_fraction(
        self,
        spec: Mapping[str, object],
        start_sec: float | None = None,
        duration_sec: float | None = None,
        group_ids: tuple[str, ...] | None = None,
    ) -> float:
        """`group_ids` 를 주면 그 신호그룹만 적분한다.

        기본 해석(`movement_signal_groups`)은 신호두의 `lane` 이 링크 단위라
        **한 접근로의 직진과 보호좌회전을 같은 SG 집합으로 묶는다.** 그러면 movement 가
        자기 현시가 아닌 녹색까지 받아 방출이 과대해진다 - 542개 중 339개(62.5%)가 서로
        떨어진 녹색창 2~4개에 걸치고, union 녹색이 올바른 단일 SG 녹색의 중앙값 1.39배
        (p90 1.81, 최대 2.96)다. 호출부가 movement 자기 현시의 SG 로 좁혀 넣을 수 있게
        통로를 낸다.
        """
        groups = group_ids if group_ids is not None else self.movement_signal_groups(spec)
        return self._green_fraction(tuple(groups), start_sec, duration_sec)

    def _green_fraction(
        self,
        group_ids: tuple[str, ...],
        start_sec: float | None,
        duration_sec: float | None,
    ) -> float:
        if not group_ids:
            return 0.0
        cycle = self.program.cycle_length_sec
        if start_sec is None or duration_sec is None:
            return _union_green_overlap(
                self.program, group_ids, 0.0, cycle, self.controller_offset_sec
            ) / cycle
        if duration_sec <= 0.0:
            return 0.0
        return _union_green_overlap(
            self.program,
            group_ids,
            start_sec,
            start_sec + duration_sec,
            self.controller_offset_sec,
        ) / duration_sec


def _angular_distance(left: float | None, right: float) -> float:
    if left is None:
        return math.inf
    distance = abs(left - right) % 360.0
    return min(distance, 360.0 - distance)


# 녹색 합집합 적분 캐시.
#
# 왜. 이 함수가 어댑터 호출 시간의 단독 1위다 - 생산 config 에서 13.2%(279초 중 36.9초),
# 램프 결합을 켜면 24.3%(7,730초 중 1,877초)다. 그런데 `.sig` 에서 온 **고정시간** 계획을
# 적분하는 것이라 컨트롤러가 정하는 녹색과 무관하다. leader 가 코너 2^15 개를 열거할 때
# 같은 (movement, 창) 이 완전히 동일한 입력으로 수만 번 재계산된다.
#
# 안전한 이유. `ControllerProgram` 은 frozen dataclass 이고(signal_program.py:113),
# 이 함수는 cycle_length_sec / program_offset_sec / sg_timelines 만 읽는다. 저장소 전체에서
# sg_timelines 를 변형하는 곳이 없다(전부 조회). 즉 출력이 인자만의 함수다 - 캐시는
# 비트 동일해야 하고, 실제로 그렇게 검증한다.
#
# id(program) 을 키에 쓰므로 그 program 에 강한 참조를 함께 들고 있어야 한다. 안 그러면
# GC 후 id 가 재사용돼 다른 계획의 값을 돌려줄 수 있다.
_GREEN_OVERLAP_CACHE: dict[tuple, float] = {}
_GREEN_OVERLAP_PROGRAMS: dict[int, "ControllerProgram"] = {}
_GREEN_OVERLAP_STATS = {"hit": 0, "miss": 0}


def green_overlap_cache_stats() -> dict[str, int]:
    """캐시 적중 통계. 진단에 실어 적중률이 실제로 높은지 보이게 한다."""
    return dict(_GREEN_OVERLAP_STATS)


def _union_green_overlap(
    program: ControllerProgram,
    group_ids: Iterable[str],
    start_sec: float,
    end_sec: float,
    controller_offset_sec: float,
) -> float:
    if end_sec <= start_sec:
        return 0.0
    groups = tuple(group_ids)
    key = (id(program), groups, start_sec, end_sec, controller_offset_sec)
    cached = _GREEN_OVERLAP_CACHE.get(key)
    if cached is not None:
        _GREEN_OVERLAP_STATS["hit"] += 1
        return cached
    _GREEN_OVERLAP_PROGRAMS.setdefault(id(program), program)
    value = _union_green_overlap_uncached(program, groups, start_sec, end_sec, controller_offset_sec)
    _GREEN_OVERLAP_CACHE[key] = value
    _GREEN_OVERLAP_STATS["miss"] += 1
    return value


def _union_green_overlap_uncached(
    program: ControllerProgram,
    group_ids: Iterable[str],
    start_sec: float,
    end_sec: float,
    controller_offset_sec: float,
) -> float:
    if end_sec <= start_sec:
        return 0.0
    cycle = program.cycle_length_sec
    shift = program.program_offset_sec + controller_offset_sec
    spans: list[tuple[float, float]] = []
    first_cycle = math.floor((start_sec - shift) / cycle) - 1
    last_cycle = math.ceil((end_sec - shift) / cycle) + 1
    for group_id in group_ids:
        timeline = program.sg_timelines.get(str(group_id))
        if timeline is None:
            continue
        for interval in timeline.intervals:
            if interval.state != "GREEN":
                continue
            for cycle_index in range(first_cycle, last_cycle + 1):
                left = max(start_sec, shift + cycle_index * cycle + interval.start_sec)
                right = min(end_sec, shift + cycle_index * cycle + interval.end_sec)
                if right > left:
                    spans.append((left, right))
    total = 0.0
    right_edge = -math.inf
    for left, right in sorted(spans):
        if left > right_edge:
            total += right - left
            right_edge = right
        elif right > right_edge:
            total += right - right_edge
            right_edge = right
    return total


def _signal_program_path(network_path: Path, supply_file: str) -> Path:
    value = supply_file.strip()
    if value.lower().startswith("#data#"):
        value = value[6:]
    path = Path(value)
    if not path.is_absolute():
        path = network_path.parent / path
    return path


def compile_fixed_signal_schedules(
    network_path: str | Path,
    node_ids: Iterable[str] | None = None,
    detector_mapping: Mapping[str, Any] | None = None,
) -> tuple[dict[str, FixedControllerSchedule], dict[str, str]]:
    source = Path(network_path)
    root = ET.parse(source).getroot()
    selected = {str(value) for value in node_ids} if node_ids is not None else None
    detector = detector_mapping or {}
    link_to_origins = detector.get("link_to_origins", {})
    link_legs = (detector.get("link_partition", {}) or {}).get("owned_link_legs", {})
    head_groups_by_node_link: dict[str, dict[str, set[str]]] = {}
    for head in root.findall(".//signalHeads/signalHead"):
        sg_ref = str(head.get("sg", "")).split()
        lane_ref = str(head.get("lane", "")).split()
        if len(sg_ref) >= 2 and lane_ref:
            head_groups_by_node_link.setdefault(f"SC{sg_ref[0]}", {}).setdefault(lane_ref[0], set()).add(sg_ref[1])
    schedules: dict[str, FixedControllerSchedule] = {}
    errors: dict[str, str] = {}
    for controller in root.findall(".//signalControllers/signalController"):
        node_id = f"SC{controller.get('no', '')}"
        if selected is not None and node_id not in selected:
            continue
        if str(controller.get("active", "true")).lower() != "true":
            continue
        try:
            program_path = _signal_program_path(source, controller.get("supplyFile2", ""))
            program = parse_sig(program_path, int(controller.get("progNo", "1")))
            phase_groups: dict[str, list[str]] = {"p1": [], "p2": []}
            for group in controller.findall("./sgs/signalGroup"):
                group_no = str(group.get("no", ""))
                axis = _axis_for_signal_group(group_no, str(group.get("name", "")))
                if axis and group_no in program.sg_timelines:
                    phase_groups[axis].append(group_no)
            compact = {
                phase: tuple(sorted(group_ids, key=_sort_id))
                for phase, group_ids in phase_groups.items()
                if group_ids
            }
            if not compact:
                raise ValueError("no vehicle signal group maps to p1/p2")
            origin_groups: dict[str, set[str]] = {}
            approach_groups: dict[str, set[str]] = {}
            for link, groups in head_groups_by_node_link.get(node_id, {}).items():
                valid_groups = {group for group in groups if group in program.sg_timelines}
                for origin in link_to_origins.get(str(link), []):
                    origin_groups.setdefault(str(origin), set()).update(valid_groups)
                leg = str(link_legs.get(str(link), ""))
                if leg:
                    approach_groups.setdefault(leg, set()).update(valid_groups)
            schedules[node_id] = FixedControllerSchedule(
                node_id=node_id,
                program=program,
                controller_offset_sec=float(controller.get("offset", "0") or 0.0),
                phase_signal_groups=compact,
                origin_signal_groups={
                    key: tuple(sorted(groups, key=_sort_id)) for key, groups in origin_groups.items()
                },
                approach_signal_groups={
                    key: tuple(sorted(groups, key=_sort_id)) for key, groups in approach_groups.items()
                },
            )
        except Exception as exc:
            errors[node_id] = f"{type(exc).__name__}: {exc}"
    return schedules, errors
