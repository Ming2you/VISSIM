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
    default_duration_ms: int
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
    start_ms: int
    end_ms: int
    start_sec: float
    end_sec: float
    state: str
    display_id: str
    source_kind: str


@dataclass(frozen=True)
class SignalCommand:
    display_id: str
    begin_ms: int
    begin_sec: float


@dataclass(frozen=True)
class SignalFixedState:
    display_id: str
    duration_ms: int
    duration_sec: float


@dataclass(frozen=True)
class SignalGroupTimeline:
    sg_id: str
    name: str
    sequence_id: str
    cycle_length_ms: int
    cycle_length_sec: float
    permanent_red: bool
    commands: tuple[SignalCommand, ...]
    fixed_states: tuple[SignalFixedState, ...]
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
    cycle_length_ms: int
    cycle_length_sec: float
    switchpoint_ms: int
    switchpoint_sec: float
    program_offset_ms: int
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
class DailyProgramListItem:
    time_ms: int
    time_sec: float
    program_no: int


@dataclass(frozen=True)
class DailyProgramList:
    list_no: int
    name: str
    items: tuple[DailyProgramListItem, ...]


@dataclass(frozen=True)
class SignalDefinition:
    controller_id: str
    controller_name: str
    programs: Mapping[int, ControllerProgram]
    daily_program_lists: Mapping[int, DailyProgramList]
    daily_program_lists_element_present: bool
    source_path: str


@dataclass(frozen=True)
class _Command:
    display_id: str
    begin_ms: int


@dataclass(frozen=True)
class _Event:
    time_ms: int
    display_id: str
    source_kind: str


def parse_sig(path: str | Path, active_prog_no: int) -> ControllerProgram:
    """Parse one active VISSIG program and compile every SG into a timeline."""

    programs = parse_sig_programs(path)
    try:
        return programs[int(active_prog_no)]
    except KeyError as exc:
        raise SignalProgramError(
            f"active program {active_prog_no} must match exactly once, found 0"
        ) from exc


def parse_sig_programs(path: str | Path) -> Mapping[int, ControllerProgram]:
    """Parse every VISSIG program in deterministic numeric program order."""

    return parse_sig_definition(path).programs


def parse_sig_definition(path: str | Path) -> SignalDefinition:
    """Parse programs and optional VISSIG daily-program-list definitions."""

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

    program_elements: dict[int, ET.Element] = {}
    for element in root.findall("./progs/prog"):
        program_no = _required_int(element, "id", "program")
        if program_no in program_elements:
            raise SignalProgramError(f"program {program_no} must match exactly once, found 2")
        program_elements[program_no] = element
    if not program_elements:
        raise SignalProgramError("controller contains no programs")

    programs: dict[int, ControllerProgram] = {}
    for program_no in sorted(program_elements):
        programs[program_no] = _compile_program(
            root=root,
            program_element=program_elements[program_no],
            program_no=program_no,
            source=source,
            displays=displays,
            sequences=sequences,
            sg_definitions=sg_definitions,
        )
    daily_lists_element = root.find("./dailyProgLists")
    daily_program_lists = _parse_daily_program_lists(
        daily_lists_element, available_program_nos=frozenset(programs)
    )
    return SignalDefinition(
        controller_id=_required_text(root, "id", "controller"),
        controller_name=root.get("name", ""),
        programs=MappingProxyType(programs),
        daily_program_lists=MappingProxyType(daily_program_lists),
        daily_program_lists_element_present=daily_lists_element is not None,
        source_path=str(source.resolve()),
    )


def _parse_daily_program_lists(
    container: ET.Element | None, *, available_program_nos: frozenset[int]
) -> dict[int, DailyProgramList]:
    if container is None:
        return {}

    result: dict[int, DailyProgramList] = {}
    for element in container:
        if element.tag != "dailyProgList":
            raise SignalProgramError(
                f"dailyProgLists contains unsupported element <{element.tag}>"
            )
        list_no = _required_int(element, "id", "daily program list")
        if list_no in result:
            raise SignalProgramError(f"duplicate daily program list {list_no}")
        items: list[DailyProgramListItem] = []
        seen_times: set[int] = set()
        for item in element.findall(".//dailyProgListItem"):
            time_ms = _required_ms_int(
                item, "time", f"daily program list {list_no} item"
            )
            if time_ms >= 86_400_000:
                raise SignalProgramError(
                    f"daily program list {list_no} item time must be within one day"
                )
            if time_ms in seen_times:
                raise SignalProgramError(
                    f"daily program list {list_no} repeats time {time_ms}ms"
                )
            seen_times.add(time_ms)
            program_no = _required_int(
                item, "prog_id", f"daily program list {list_no} item"
            )
            if program_no not in available_program_nos:
                raise SignalProgramError(
                    f"daily program list {list_no} references undefined program {program_no}"
                )
            items.append(
                DailyProgramListItem(
                    time_ms=time_ms,
                    time_sec=time_ms / 1000.0,
                    program_no=program_no,
                )
            )
        if not items:
            raise SignalProgramError(f"daily program list {list_no} contains no items")
        items.sort(key=lambda item: item.time_ms)
        result[list_no] = DailyProgramList(
            list_no=list_no,
            name=element.get("name", ""),
            items=tuple(items),
        )
    return {key: result[key] for key in sorted(result)}


def _compile_program(
    *,
    root: ET.Element,
    program_element: ET.Element,
    program_no: int,
    source: Path,
    displays: Mapping[str, str],
    sequences: Mapping[str, SignalSequence],
    sg_definitions: Mapping[str, tuple[str, str]],
) -> ControllerProgram:
    cycle_ms = _required_ms_int(program_element, "cycletime", "program")
    if cycle_ms <= 0:
        raise SignalProgramError("program cycletime must be positive")
    switchpoint_ms = _required_ms_int(program_element, "switchpoint", "program")
    program_offset_ms = _required_ms_int(program_element, "offset", "program")

    timelines: dict[str, SignalGroupTimeline] = {}
    program_sgs = program_element.findall("./sgs/sg")
    if not program_sgs:
        raise SignalProgramError(f"program {program_no} contains no SGs")
    for program_sg in sorted(program_sgs, key=lambda item: _id_sort_key(item.get("sg_id"))):
        sg_id = _required_text(program_sg, "sg_id", "program SG")
        if sg_id in timelines:
            raise SignalProgramError(f"program {program_no} repeats SG {sg_id}")
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
            cycle_ms=cycle_ms,
        )
        timelines[sg_id] = timeline

    return ControllerProgram(
        controller_id=_required_text(root, "id", "controller"),
        controller_name=root.get("name", ""),
        active_prog_no=program_no,
        program_name=program_element.get("name", ""),
        cycle_length_ms=cycle_ms,
        cycle_length_sec=cycle_ms / 1000.0,
        switchpoint_ms=switchpoint_ms,
        switchpoint_sec=switchpoint_ms / 1000.0,
        program_offset_ms=program_offset_ms,
        program_offset_sec=program_offset_ms / 1000.0,
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
            default_duration_ms = _required_ms_int(
                state_element,
                "defaultDuration",
                f"signal sequence {sequence_id}",
            )
            states.append(
                SignalSequenceState(
                    display_id=display_id,
                    state=display_states[display_id],
                    fixed_duration=_required_bool(
                        state_element,
                        "isFixedDuration",
                        f"signal sequence {sequence_id}",
                    ),
                    default_duration_ms=default_duration_ms,
                    default_duration_sec=default_duration_ms / 1000.0,
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
    cycle_ms: int,
) -> SignalGroupTimeline:
    commands = [
        _Command(
            display_id=_required_text(element, "display", f"SG {sg_id} command"),
            begin_ms=_required_ms_int(element, "begin", f"SG {sg_id} command"),
        )
        for element in program_sg.findall("./cmds/cmd")
    ]
    if not commands:
        raise SignalProgramError(f"SG {sg_id} contains no commands")
    commands.sort(key=lambda item: (item.begin_ms, _id_sort_key(item.display_id)))
    seen_times: set[int] = set()
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
        if not 0 <= command.begin_ms < cycle_ms:
            raise SignalProgramError(
                f"SG {sg_id} command at {command.begin_ms / 1000.0}s is outside cycle "
                f"[0,{cycle_ms / 1000.0})"
            )
        if command.begin_ms in seen_times:
            raise SignalProgramError(
                f"SG {sg_id} has multiple commands at {command.begin_ms / 1000.0}s"
            )
        seen_times.add(command.begin_ms)

    fixed_durations: dict[str, int] = {}
    for element in program_sg.findall("./fixedstates/fixedstate"):
        display_id = _required_text(element, "display", f"SG {sg_id} fixedstate")
        duration = _required_ms_int(element, "duration", f"SG {sg_id} fixedstate")
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
            SignalInterval(
                0,
                cycle_ms,
                0.0,
                cycle_ms / 1000.0,
                state,
                command.display_id,
                "command",
            ),
        )
        return SignalGroupTimeline(
            sg_id=sg_id,
            name=sg_name,
            sequence_id=sequence.sequence_id,
            cycle_length_ms=cycle_ms,
            cycle_length_sec=cycle_ms / 1000.0,
            permanent_red=state == "RED",
            commands=_public_commands(commands),
            fixed_states=_public_fixed_states(fixed_durations),
            intervals=intervals,
        )

    events: list[_Event] = [
        _Event(command.begin_ms, command.display_id, "command")
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
        available = (target.begin_ms - current.begin_ms) % cycle_ms
        required = sum(fixed_durations[item] for item in transition_states)
        if required > available:
            raise SignalProgramError(
                f"SG {sg_id} transition {current.display_id}->{target.display_id} "
                f"has {available / 1000.0}s but requires {required / 1000.0}s of fixed states"
            )
        cursor = target.begin_ms
        for display_id in reversed(transition_states):
            cursor -= fixed_durations[display_id]
            events.append(_Event(cursor % cycle_ms, display_id, "fixedstate"))

    intervals = _events_to_intervals(events, display_states, cycle_ms, sg_id)
    _validate_coverage(intervals, cycle_ms, sg_id)
    return SignalGroupTimeline(
        sg_id=sg_id,
        name=sg_name,
        sequence_id=sequence.sequence_id,
        cycle_length_ms=cycle_ms,
        cycle_length_sec=cycle_ms / 1000.0,
        permanent_red=all(item.state == "RED" for item in intervals),
        commands=_public_commands(commands),
        fixed_states=_public_fixed_states(fixed_durations),
        intervals=intervals,
    )


def _public_commands(commands: Sequence[_Command]) -> tuple[SignalCommand, ...]:
    return tuple(
        SignalCommand(item.display_id, item.begin_ms, item.begin_ms / 1000.0)
        for item in commands
    )


def _public_fixed_states(fixed_durations: Mapping[str, int]) -> tuple[SignalFixedState, ...]:
    return tuple(
        SignalFixedState(display_id, duration_ms, duration_ms / 1000.0)
        for display_id, duration_ms in sorted(
            fixed_durations.items(), key=lambda item: _id_sort_key(item[0])
        )
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
    cycle_ms: int,
    sg_id: str,
) -> tuple[SignalInterval, ...]:
    ordered = sorted(
        events,
        key=lambda item: (item.time_ms, item.source_kind, _id_sort_key(item.display_id)),
    )
    deduplicated: list[_Event] = []
    for event in ordered:
        if deduplicated and event.time_ms == deduplicated[-1].time_ms:
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
                f"SG {sg_id} has conflicting events at {event.time_ms / 1000.0}s"
            )
        deduplicated.append(event)

    if not deduplicated:
        raise SignalProgramError(f"SG {sg_id} produced no timeline events")
    pieces: list[SignalInterval] = []
    for index, event in enumerate(deduplicated):
        next_ms = (
            deduplicated[index + 1].time_ms
            if index + 1 < len(deduplicated)
            else cycle_ms + deduplicated[0].time_ms
        )
        if next_ms <= event.time_ms:
            continue
        state = display_states[event.display_id]
        if next_ms <= cycle_ms:
            pieces.append(
                SignalInterval(
                    event.time_ms,
                    min(next_ms, cycle_ms),
                    event.time_ms / 1000.0,
                    min(next_ms, cycle_ms) / 1000.0,
                    state,
                    event.display_id,
                    event.source_kind,
                )
            )
        else:
            pieces.append(
                SignalInterval(
                    event.time_ms,
                    cycle_ms,
                    event.time_ms / 1000.0,
                    cycle_ms / 1000.0,
                    state,
                    event.display_id,
                    event.source_kind,
                )
            )
            pieces.append(
                SignalInterval(
                    0,
                    next_ms - cycle_ms,
                    0.0,
                    (next_ms - cycle_ms) / 1000.0,
                    state,
                    event.display_id,
                    event.source_kind,
                )
            )
    pieces.sort(key=lambda item: item.start_ms)
    return tuple(pieces)


def _validate_coverage(
    intervals: Sequence[SignalInterval], cycle_ms: int, sg_id: str
) -> None:
    cursor = 0
    for interval in intervals:
        if interval.state not in _VALID_STATES:
            raise SignalProgramError(f"SG {sg_id} has invalid state {interval.state}")
        if interval.start_ms != cursor:
            relation = "overlap" if interval.start_ms < cursor else "gap"
            raise SignalProgramError(
                f"SG {sg_id} timeline has {relation} at {cursor / 1000.0}s"
            )
        if interval.end_ms <= interval.start_ms:
            raise SignalProgramError(f"SG {sg_id} has a non-positive interval")
        cursor = interval.end_ms
    if cursor != cycle_ms:
        raise SignalProgramError(
            f"SG {sg_id} timeline ends at {cursor / 1000.0}s, expected {cycle_ms / 1000.0}s"
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
    return _required_ms_int(element, attribute, context) / 1000.0


def _required_ms_int(element: ET.Element, attribute: str, context: str) -> int:
    milliseconds = _required_int(element, attribute, context)
    if milliseconds < 0:
        raise SignalProgramError(f"{context} {attribute} must be non-negative")
    return milliseconds


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
    "DailyProgramList",
    "DailyProgramListItem",
    "SignalCommand",
    "SignalFixedState",
    "SignalGroupTimeline",
    "SignalInterval",
    "SignalProgramError",
    "SignalDefinition",
    "SignalSequence",
    "SignalSequenceState",
    "green_overlap",
    "parse_sig",
    "parse_sig_definition",
    "parse_sig_programs",
    "state_at",
]
