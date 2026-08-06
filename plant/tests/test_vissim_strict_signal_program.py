from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest

from src.vissim_strict.signal_program import (
    SignalProgramError,
    green_overlap,
    parse_sig,
    parse_sig_programs,
    state_at,
)


def _fixture(path: Path, commands: str, *, offset_ms: int = 0, switchpoint_ms: int = 17_000) -> Path:
    content = f"""
    <sc version="201602" id="99" name="fixture">
      <signaldisplays>
        <display id="1" name="Red" state="RED" />
        <display id="3" name="Green" state="GREEN" />
        <display id="4" name="Amber" state="AMBER" />
      </signaldisplays>
      <signalsequences>
        <signalsequence id="7" name="Red-Green-Amber">
          <state display="1" isFixedDuration="false" isClosed="true" defaultDuration="1000" />
          <state display="3" isFixedDuration="false" isClosed="false" defaultDuration="5000" />
          <state display="4" isFixedDuration="true" isClosed="true" defaultDuration="3000" />
        </signalsequence>
      </signalsequences>
      <sgs><sg id="1" name="main" defaultSignalSequence="7" /></sgs>
      <progs><prog id="1" cycletime="100000" switchpoint="{switchpoint_ms}" offset="{offset_ms}" name="active">
        <sgs><sg sg_id="1" signal_sequence="7">
          <cmds>{commands}</cmds><fixedstates><fixedstate display="4" duration="3000" /></fixedstates>
        </sg></sgs>
      </prog></progs>
    </sc>
    """
    target = path / "fixture.sig"
    target.write_text(textwrap.dedent(content), encoding="utf-8")
    return target


def _multi_program_fixture(path: Path) -> Path:
    target = _fixture(
        path,
        '<cmd display="3" begin="39000" /><cmd display="1" begin="65000" />',
    )
    content = target.read_text(encoding="utf-8")
    second = """
      <prog id="2" cycletime="90000" switchpoint="12000" offset="7000" name="second">
        <sgs><sg sg_id="1" signal_sequence="7">
          <cmds><cmd display="3" begin="21000" /><cmd display="1" begin="51000" /></cmds>
          <fixedstates><fixedstate display="4" duration="3000" /></fixedstates>
        </sg></sgs>
      </prog>
    """
    content = content.replace("<progs>", f"<progs>{textwrap.dedent(second)}")
    target.write_text(content, encoding="utf-8")
    return target


class SignalProgramTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_places_fixed_amber_immediately_before_red(self) -> None:
        program = parse_sig(
            _fixture(self.root, '<cmd display="3" begin="39000" /><cmd display="1" begin="65000" />'),
            1,
        )
        timeline = program.sg_timelines["1"]
        self.assertEqual(
            [(x.start_sec, x.end_sec, x.state) for x in timeline.intervals],
            [(0.0, 39.0, "RED"), (39.0, 62.0, "GREEN"), (62.0, 65.0, "AMBER"), (65.0, 100.0, "RED")],
        )
        self.assertEqual(state_at(62.0, program, 1), "AMBER")
        self.assertAlmostEqual(green_overlap(0.0, 100.0, program, 1), 23.0)

    def test_wraps_timeline_and_overlap(self) -> None:
        program = parse_sig(
            _fixture(self.root, '<cmd display="1" begin="20000" /><cmd display="3" begin="70000" />'),
            1,
        )
        self.assertEqual(state_at(95.0, program, 1), "GREEN")
        self.assertEqual(state_at(10.0, program, 1), "GREEN")
        self.assertAlmostEqual(green_overlap(90.0, 110.0, program, 1), 20.0)

    def test_program_offset_is_positive_lag(self) -> None:
        program = parse_sig(
            _fixture(
                self.root,
                '<cmd display="3" begin="10000" /><cmd display="1" begin="40000" />',
                offset_ms=10_000,
                switchpoint_ms=77_000,
            ),
            1,
        )
        self.assertEqual(program.switchpoint_sec, 77.0)
        self.assertEqual(state_at(19.999, program, 1), "RED")
        self.assertEqual(state_at(20.0, program, 1), "GREEN")
        self.assertEqual(state_at(50.0, program, 1), "RED")

    def test_rejects_transition_shorter_than_fixed_duration(self) -> None:
        path = _fixture(self.root, '<cmd display="3" begin="10000" /><cmd display="1" begin="12000" />')
        with self.assertRaisesRegex(SignalProgramError, "requires 3.0s"):
            parse_sig(path, 1)

    def test_parses_all_programs_in_numeric_order_and_keeps_parse_sig_compatible(self) -> None:
        path = _multi_program_fixture(self.root)
        programs = parse_sig_programs(path)

        self.assertEqual(list(programs), [1, 2])
        self.assertEqual(parse_sig(path, 2), programs[2])
        self.assertEqual(programs[2].cycle_length_sec, 90.0)
        self.assertEqual(programs[2].switchpoint_sec, 12.0)
        self.assertEqual(programs[2].program_offset_sec, 7.0)

    def test_preserves_raw_integer_millisecond_boundaries(self) -> None:
        program = parse_sig(_multi_program_fixture(self.root), 1)
        timeline = program.sg_timelines["1"]

        self.assertEqual(program.cycle_length_ms, 100_000)
        self.assertEqual(program.switchpoint_ms, 17_000)
        self.assertEqual(program.program_offset_ms, 0)
        self.assertEqual(
            [(item.display_id, item.begin_ms) for item in timeline.commands],
            [("3", 39_000), ("1", 65_000)],
        )
        self.assertEqual(
            [(item.start_ms, item.end_ms) for item in timeline.intervals],
            [(0, 39_000), (39_000, 62_000), (62_000, 65_000), (65_000, 100_000)],
        )
        self.assertEqual(timeline.cycle_length_ms, program.cycle_length_ms)
        self.assertTrue(all(isinstance(item.start_ms, int) for item in timeline.intervals))


if __name__ == "__main__":
    unittest.main()
