"""Compile VISSIG ``.sig`` programs into deterministic periodic SG timelines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence
import math
import xml.etree.ElementTree as ET


_VALID_STATES = frozenset({"GREEN", "AMBER", "RED"})
_EPSILON = 1e-9


class SignalProgramError(ValueError):
    """Raised when a VISSIG program cannot be compiled unambiguously."""


@dataclass(frozen=True)
class SignalSequenceState:
    display_id: str
    state: str
    fixed_duration: bool
    default_duration_sec: float


@dataclass(frozen=True)
class SignalSequence:
    sequence_id: str
    name: str
    states: tuple[SignalSequenceState, ...]

    @property
    def display_order(self) -> tuple[str, ...]:
        return tuple(item.display_id for item in self.states)


@dataclass(frozen=True)
class SignalInterval:
    start_sec: float
    end_sec: float
    state: str
    display_id: str
    source_kind: str


@dataclass(frozen=True)
class SignalGroupTimeline:
    sg_id: str
    name: str
    sequence_id: str
    cycle_length_sec: float
    permanent_red: bool
    intervals: tuple[SignalInterval, ...]

    def state_at_phase(self, phase_sec: float) -> str:
        phase = _phase_mod(phase_sec, self.cycle_length_sec)
        for interval in self.intervals:
            if interval.start_sec <= phase < interval.end_sec:
                return interval.state
        raise SignalProgramError(f"SG {self.sg_id} timeline does not cover phase {phase}")

    def green_overlap_phase(self, phase_sec: float, duration_sec: float) -> float:
        if not math.isfinite(phase_sec) or not math.isfinite(duration_sec):
            raise SignalProgramError("overlap inputs must be finite")
        if duration_sec < 0:
            raise SignalProgramError("overlap duration must be non-negative")
        if duration_sec == 0:
            return 0.0

        cycle = self.cycle_length_sec
        green_per_cycle = sum(
            interval.end_sec - interval.start_sec
            for interval in self.intervals
            if interval.state == "GREEN"
        )
        complete_cycles = math.floor(duration_sec / cycle)
        overlap = complete_cycles * green_per_cycle
        remainder = duration_sec - complete_cycles * cycle
        phase = _phase_mod(phase_sec, cycle)

        first_span = min(remainder, cycle - phase)
        overlap += _green_overlap_linear(self.intervals, phase, phase + first_span)
        if remainder > first_span:
            overlap += _green_overlap_linear(
                self.intervals, 0.0, remainder - first_span
            )
        return overlap


@dataclass(frozen=True)
class ControllerProgram:
    controller_id: str
    controller_name: str
    active_prog_no: int
    program_name: str
    cycle_length_sec: float
    switchpoint_sec: float
    program_offset_sec: float
    display_states: Mapping[str, str]
    sequences: Mapping[str, SignalSequence]
    sg_timelines: Mapping[str, SignalGroupTimeline]
    source_path: str

    def state_at(
        self,
        time_sec: float,
        sg_id: str | int | None = None,
        *,
        start_time_of_day_sec: float = 0.0,
        cycle_epoch_sec: float = 0.0,
        controller_offset_sec: float = 0.0,
    ) -> str | dict[str, str]:
        return state_at(
            time_sec,
            self,
            sg_id,
            start_time_of_day_sec=start_time_of_day_sec,
            cycle_epoch_sec=cycle_epoch_sec,
            controller_offset_sec=controller_offset_sec,
        )

    def green_overlap(
        self,
        t0_sec: float,
        t1_sec: float,
        sg_id: str | int,
        *,
        start_time_of_day_sec: float = 0.0,
        cycle_epoch_sec: float = 0.0,
        controller_offset_sec: float = 0.0,
    ) -> float:
        return green_overlap(
            t0_sec,
            t1_sec,
            self,
            sg_id,
            start_time_of_day_sec=start_time_of_day_sec,
            cycle_epoch_sec=cycle_epoch_sec,
            controller_offset_sec=controller_offset_sec,
        )


@dataclass(frozen=True)
class _Command:
    display_id: str
    begin_sec: float


@dataclass(frozen=True)
class _Event:
    time_sec: float
    display_id: str
    source_kind: str


def parse_sig(path: str | Path, active_prog_no: int) -> ControllerProgram:
    """Parse one active VISSIG program and compile every SG into a timeline."""

    source = Path(path)
    try:
        root = ET.parse(source).getroot()
    except (OSError, ET.ParseError) as exc:
        raise SignalProgramError(f"cannot parse {source}: {exc}") from exc
    if root.tag != "sc":
        raise SignalProgramError(f"expected <sc> root, found <{root.tag}>")

    displays = _parse_displays(root)
    sequences = _parse_sequences(root, displays)
    sg_definitions = _parse_sg_definitions(root, sequences)

    matching = [
        element
        for element in root.findall("./progs/prog")
        if _required_int(element, "id", "program") == active_prog_no
    ]
    if len(matching) != 1:
        raise SignalProgramError(
            f"active program {active_prog_no} must match exactly once, found {len(matching)}"
        )
    program_element = matching[0]
    cycle_sec = _required_ms(program_element, "cycletime", "program")
    if cycle_sec <= 0:
        raise SignalProgramError("program cycletime must be positive")
    switchpoint_sec = _required_ms(program_element, "switchpoint", "program")
    program_offset_sec = _required_ms(program_element, "offset", "program")

    timelines: dict[str, SignalGroupTimeline] = {}
    program_sgs = program_element.findall("./sgs/sg")
    if not program_sgs:
        raise SignalProgramError(f"program {active_prog_no} contains no SGs")
    for program_sg in sorted(program_sgs, key=lambda item: _id_sort_key(item.get("sg_id"))):
        sg_id = _required_text(program_sg, "sg_id", "program SG")
        if sg_id in timelines:
            raise SignalProgramError(f"program {active_prog_no} repeats SG {sg_id}")
        if sg_id not in sg_definitions:
            raise SignalProgramError(f"program references undefined SG {sg_id}")
        name, default_sequence_id = sg_definitions[sg_id]
        sequence_id = program_sg.get("signal_sequence", default_sequence_id)
        if sequence_id not in sequences:
            raise SignalProgramError(
                f"SG {sg_id} references undefined signal sequence {sequence_id}"
            )
        timeline = _compile_timeline(
            program_sg,
            sg_id=sg_id,
            sg_name=name,
            sequence=sequences[sequence_id],
            display_states=displays,
            cycle_sec=cycle_sec,
        )
        timelines[sg_id] = timeline

    return ControllerProgram(
        controller_id=_required_text(root, "id", "controller"),
        controller_name=root.get("name", ""),
        active_prog_no=active_prog_no,
        program_name=program_element.get("name", ""),
        cycle_length_sec=cycle_sec,
        switchpoint_sec=switchpoint_sec,
        program_offset_sec=program_offset_sec,
        display_states=MappingProxyType(dict(displays)),
        sequences=MappingProxyType(dict(sequences)),
        sg_timelines=MappingProxyType(timelines),
        source_path=str(source.resolve()),
    )


def state_at(
    time_sec: float,
    program: ControllerProgram,
    sg_id: str | int | None = None,
    *,
    start_time_of_day_sec: float = 0.0,
    cycle_epoch_sec: float = 0.0,
    controller_offset_sec: float = 0.0,
) -> str | dict[str, str]:
    """Return SG state(s) using the G0 source-phase normalization contract."""

    phase = _source_phase(
        time_sec,
        program,
        start_time_of_day_sec,
        cycle_epoch_sec,
        controller_offset_sec,
    )
    if sg_id is not None:
        key = str(sg_id)
        try:
            return program.sg_timelines[key].state_at_phase(phase)
        except KeyError as exc:
            raise SignalProgramError(f"unknown SG {key}") from exc
    return {
        key: timeline.state_at_phase(phase)
        for key, timeline in program.sg_timelines.items()
    }


def green_overlap(
    t0_sec: float,
    t1_sec: float,
    program: ControllerProgram,
    sg_id: str | int,
    *,
    start_time_of_day_sec: float = 0.0,
    cycle_epoch_sec: float = 0.0,
    controller_offset_sec: float = 0.0,
) -> float:
    """Measure effective green over ``[t0_sec, t1_sec)`` in seconds."""

    if not math.isfinite(t0_sec) or not math.isfinite(t1_sec):
        raise SignalProgramError("green_overlap bounds must be finite")
    if t1_sec < t0_sec:
        raise SignalProgramError("green_overlap requires t1_sec >= t0_sec")
    key = str(sg_id)
    try:
        timeline = program.sg_timelines[key]
    except KeyError as exc:
        raise SignalProgramError(f"unknown SG {key}") from exc
    phase = _source_phase(
        t0_sec,
        program,
        start_time_of_day_sec,
        cycle_epoch_sec,
        controller_offset_sec,
    )
    return timeline.green_overlap_phase(phase, t1_sec - t0_sec)


def _parse_displays(root: ET.Element) -> dict[str, str]:
    displays: dict[str, str] = {}
    for element in root.findall("./signaldisplays/display"):
        display_id = _required_text(element, "id", "display")
        state = _required_text(element, "state", f"display {display_id}").upper()
        if state not in _VALID_STATES:
            raise SignalProgramError(
                f"display {display_id} has unsupported state {state!r}"
            )
        if display_id in displays:
            raise SignalProgramError(f"duplicate display {display_id}")
        displays[display_id] = state
    if not displays:
        raise SignalProgramError("controller contains no signal displays")
    return displays


def _parse_sequences(
    root: ET.Element, display_states: Mapping[str, str]
) -> dict[str, SignalSequence]:
    sequences: dict[str, SignalSequence] = {}
    for element in root.findall("./signalsequences/signalsequence"):
        sequence_id = _required_text(element, "id", "signal sequence")
        if sequence_id in sequences:
            raise SignalProgramError(f"duplicate signal sequence {sequence_id}")
        states: list[SignalSequenceState] = []
        seen: set[str] = set()
        for state_element in element.findall("./state"):
            display_id = _required_text(
                state_element, "display", f"signal sequence {sequence_id}"
            )
            if display_id not in display_states:
                raise SignalProgramError(
                    f"signal sequence {sequence_id} references undefined display {display_id}"
                )
            if display_id in seen:
                raise SignalProgramError(
                    f"signal sequence {sequence_id} repeats display {display_id}"
                )
            seen.add(display_id)
            states.append(
                SignalSequenceState(
                    display_id=display_id,
                    state=display_states[display_id],
                    fixed_duration=_required_bool(
                        state_element,
                        "isFixedDuration",
                        f"signal sequence {sequence_id}",
                    ),
                    default_duration_sec=_required_ms(
                        state_element,
                        "defaultDuration",
                        f"signal sequence {sequence_id}",
                    ),
                )
            )
        if not states:
            raise SignalProgramError(f"signal sequence {sequence_id} is empty")
        sequences[sequence_id] = SignalSequence(
            sequence_id=sequence_id,
            name=element.get("name", ""),
            states=tuple(states),
        )
    if not sequences:
        raise SignalProgramError("controller contains no signal sequences")
    return sequences


def _parse_sg_definitions(
    root: ET.Element, sequences: Mapping[str, SignalSequence]
) -> dict[str, tuple[str, str]]:
    definitions: dict[str, tuple[str, str]] = {}
    for element in root.findall("./sgs/sg"):
        sg_id = _required_text(element, "id", "SG")
        sequence_id = _required_text(element, "defaultSignalSequence", f"SG {sg_id}")
        if sequence_id not in sequences:
            raise SignalProgramError(
                f"SG {sg_id} references undefined default sequence {sequence_id}"
            )
        if sg_id in definitions:
            raise SignalProgramError(f"duplicate SG {sg_id}")
        definitions[sg_id] = (element.get("name", ""), sequence_id)
    return definitions


def _compile_timeline(
    program_sg: ET.Element,
    *,
    sg_id: str,
    sg_name: str,
    sequence: SignalSequence,
    display_states: Mapping[str, str],
    cycle_sec: float,
) -> SignalGroupTimeline:
    commands = [
        _Command(
            display_id=_required_text(element, "display", f"SG {sg_id} command"),
            begin_sec=_required_ms(element, "begin", f"SG {sg_id} command"),
        )
        for element in program_sg.findall("./cmds/cmd")
    ]
    if not commands:
        raise SignalProgramError(f"SG {sg_id} contains no commands")
    commands.sort(key=lambda item: (item.begin_sec, _id_sort_key(item.display_id)))
    seen_times: set[float] = set()
    sequence_displays = set(sequence.display_order)
    for command in commands:
        if command.display_id not in display_states:
            raise SignalProgramError(
                f"SG {sg_id} command references undefined display {command.display_id}"
            )
        if command.display_id not in sequence_displays:
            raise SignalProgramError(
                f"SG {sg_id} command display {command.display_id} is not in sequence {sequence.sequence_id}"
            )
        if not 0 <= command.begin_sec < cycle_sec:
            raise SignalProgramError(
                f"SG {sg_id} command at {command.begin_sec}s is outside cycle [0,{cycle_sec})"
            )
        if command.begin_sec in seen_times:
            raise SignalProgramError(
                f"SG {sg_id} has multiple commands at {command.begin_sec}s"
            )
        seen_times.add(command.begin_sec)

    fixed_durations: dict[str, float] = {}
    for element in program_sg.findall("./fixedstates/fixedstate"):
        display_id = _required_text(element, "display", f"SG {sg_id} fixedstate")
        duration = _required_ms(element, "duration", f"SG {sg_id} fixedstate")
        if display_id in fixed_durations:
            raise SignalProgramError(f"SG {sg_id} repeats fixedstate {display_id}")
        if duration <= 0:
            raise SignalProgramError(
                f"SG {sg_id} fixedstate {display_id} duration must be positive"
            )
        fixed_durations[display_id] = duration

    sequence_by_display = {item.display_id: item for item in sequence.states}
    expected_fixed = {
        item.display_id for item in sequence.states if item.fixed_duration
    }
    unexpected = set(fixed_durations) - expected_fixed
    if unexpected:
        raise SignalProgramError(
            f"SG {sg_id} fixedstates are not fixed in sequence {sequence.sequence_id}: "
            + ", ".join(sorted(unexpected, key=_id_sort_key))
        )

    if len(commands) == 1:
        command = commands[0]
        state = display_states[command.display_id]
        intervals = (
            SignalInterval(0.0, cycle_sec, state, command.display_id, "command"),
        )
        return SignalGroupTimeline(
            sg_id=sg_id,
            name=sg_name,
            sequence_id=sequence.sequence_id,
            cycle_length_sec=cycle_sec,
            permanent_red=state == "RED",
            intervals=intervals,
        )

    events: list[_Event] = [
        _Event(command.begin_sec, command.display_id, "command")
        for command in commands
    ]
    for index, target in enumerate(commands):
        current = commands[index - 1]
        path = _sequence_path(sequence.display_order, current.display_id, target.display_id)
        transition_states = [
            display_id
            for display_id in path[:-1]
            if sequence_by_display[display_id].fixed_duration
        ]
        missing = [item for item in transition_states if item not in fixed_durations]
        if missing:
            raise SignalProgramError(
                f"SG {sg_id} transition {current.display_id}->{target.display_id} "
                f"has no duration for fixed display {missing[0]}"
            )
        available = (target.begin_sec - current.begin_sec) % cycle_sec
        required = sum(fixed_durations[item] for item in transition_states)
        if required > available + _EPSILON:
            raise SignalProgramError(
                f"SG {sg_id} transition {current.display_id}->{target.display_id} "
                f"has {available}s but requires {required}s of fixed states"
            )
        cursor = target.begin_sec
        for display_id in reversed(transition_states):
            cursor -= fixed_durations[display_id]
            events.append(_Event(cursor % cycle_sec, display_id, "fixedstate"))

    intervals = _events_to_intervals(events, display_states, cycle_sec, sg_id)
    _validate_coverage(intervals, cycle_sec, sg_id)
    return SignalGroupTimeline(
        sg_id=sg_id,
        name=sg_name,
        sequence_id=sequence.sequence_id,
        cycle_length_sec=cycle_sec,
        permanent_red=all(item.state == "RED" for item in intervals),
        intervals=intervals,
    )


def _sequence_path(order: Sequence[str], current: str, target: str) -> tuple[str, ...]:
    if current == target:
        return (target,)
    current_index = order.index(current)
    result: list[str] = []
    for step in range(1, len(order) + 1):
        display_id = order[(current_index + step) % len(order)]
        result.append(display_id)
        if display_id == target:
            return tuple(result)
    raise SignalProgramError(f"no sequence path from display {current} to {target}")


def _events_to_intervals(
    events: Sequence[_Event],
    display_states: Mapping[str, str],
    cycle_sec: float,
    sg_id: str,
) -> tuple[SignalInterval, ...]:
    ordered = sorted(events, key=lambda item: (item.time_sec, item.source_kind, _id_sort_key(item.display_id)))
    deduplicated: list[_Event] = []
    for event in ordered:
        if deduplicated and abs(event.time_sec - deduplicated[-1].time_sec) <= _EPSILON:
            previous = deduplicated[-1]
            if previous.display_id == event.display_id:
                if event.source_kind == "fixedstate":
                    deduplicated[-1] = event
                continue
            # A fixed transition consumes the entire command-to-command span;
            # the zero-duration source command is intentionally omitted.
            if {previous.source_kind, event.source_kind} == {"command", "fixedstate"}:
                deduplicated[-1] = (
                    event if event.source_kind == "fixedstate" else previous
                )
                continue
            raise SignalProgramError(
                f"SG {sg_id} has conflicting events at {event.time_sec}s"
            )
        deduplicated.append(event)

    if not deduplicated:
        raise SignalProgramError(f"SG {sg_id} produced no timeline events")
    pieces: list[SignalInterval] = []
    for index, event in enumerate(deduplicated):
        next_time = (
            deduplicated[index + 1].time_sec
            if index + 1 < len(deduplicated)
            else cycle_sec + deduplicated[0].time_sec
        )
        if next_time <= event.time_sec + _EPSILON:
            continue
        state = display_states[event.display_id]
        if next_time <= cycle_sec + _EPSILON:
            pieces.append(
                SignalInterval(
                    event.time_sec,
                    min(next_time, cycle_sec),
                    state,
                    event.display_id,
                    event.source_kind,
                )
            )
        else:
            pieces.append(
                SignalInterval(
                    event.time_sec,
                    cycle_sec,
                    state,
                    event.display_id,
                    event.source_kind,
                )
            )
            pieces.append(
                SignalInterval(
                    0.0,
                    next_time - cycle_sec,
                    state,
                    event.display_id,
                    event.source_kind,
                )
            )
    pieces.sort(key=lambda item: item.start_sec)
    return tuple(pieces)


def _validate_coverage(
    intervals: Sequence[SignalInterval], cycle_sec: float, sg_id: str
) -> None:
    cursor = 0.0
    for interval in intervals:
        if interval.state not in _VALID_STATES:
            raise SignalProgramError(f"SG {sg_id} has invalid state {interval.state}")
        if abs(interval.start_sec - cursor) > _EPSILON:
            relation = "overlap" if interval.start_sec < cursor else "gap"
            raise SignalProgramError(
                f"SG {sg_id} timeline has {relation} at {cursor}s"
            )
        if interval.end_sec <= interval.start_sec:
            raise SignalProgramError(f"SG {sg_id} has a non-positive interval")
        cursor = interval.end_sec
    if abs(cursor - cycle_sec) > _EPSILON:
        raise SignalProgramError(
            f"SG {sg_id} timeline ends at {cursor}s, expected {cycle_sec}s"
        )


def _source_phase(
    time_sec: float,
    program: ControllerProgram,
    start_time_of_day_sec: float,
    cycle_epoch_sec: float,
    controller_offset_sec: float,
) -> float:
    values = (
        time_sec,
        start_time_of_day_sec,
        cycle_epoch_sec,
        controller_offset_sec,
    )
    if not all(math.isfinite(value) for value in values):
        raise SignalProgramError("source phase inputs must be finite")
    return _phase_mod(
        time_sec
        + start_time_of_day_sec
        - cycle_epoch_sec
        - program.program_offset_sec
        - controller_offset_sec,
        program.cycle_length_sec,
    )


def _phase_mod(value: float, cycle_sec: float) -> float:
    phase = value % cycle_sec
    if abs(phase - cycle_sec) <= _EPSILON or abs(phase) <= _EPSILON:
        return 0.0
    return phase


def _green_overlap_linear(
    intervals: Sequence[SignalInterval], start_sec: float, end_sec: float
) -> float:
    return sum(
        max(0.0, min(end_sec, item.end_sec) - max(start_sec, item.start_sec))
        for item in intervals
        if item.state == "GREEN"
    )


def _required_text(element: ET.Element, attribute: str, context: str) -> str:
    value = element.get(attribute)
    if value is None or value == "":
        raise SignalProgramError(f"{context} is missing {attribute}")
    return value


def _required_int(element: ET.Element, attribute: str, context: str) -> int:
    value = _required_text(element, attribute, context)
    try:
        return int(value)
    except ValueError as exc:
        raise SignalProgramError(f"{context} {attribute} is not an integer: {value!r}") from exc


def _required_ms(element: ET.Element, attribute: str, context: str) -> float:
    milliseconds = _required_int(element, attribute, context)
    if milliseconds < 0:
        raise SignalProgramError(f"{context} {attribute} must be non-negative")
    return milliseconds / 1000.0


def _required_bool(element: ET.Element, attribute: str, context: str) -> bool:
    value = _required_text(element, attribute, context).lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise SignalProgramError(f"{context} {attribute} is not boolean: {value!r}")


def _id_sort_key(value: str | None) -> tuple[int, int | str]:
    if value is None:
        return (2, "")
    try:
        return (0, int(value))
    except ValueError:
        return (1, value)


__all__ = [
    "ControllerProgram",
    "SignalGroupTimeline",
    "SignalInterval",
    "SignalProgramError",
    "SignalSequence",
    "SignalSequenceState",
    "green_overlap",
    "parse_sig",
    "state_at",
]
