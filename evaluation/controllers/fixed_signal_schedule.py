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
    ) -> float:
        return self._green_fraction(self.movement_signal_groups(spec), start_sec, duration_sec)

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


def _union_green_overlap(
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
