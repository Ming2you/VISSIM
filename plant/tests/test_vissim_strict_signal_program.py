from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest

from src.vissim_strict.signal_program import (
    SignalProgramError,
    green_overlap,
    parse_sig,
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


if __name__ == "__main__":
    unittest.main()
