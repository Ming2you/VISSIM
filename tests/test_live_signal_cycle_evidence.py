# N4-1 실측 고정 - VISSIM 안에서 잰 주기·현시를 .sig 정적 유도가 그대로 재현하는지 본다
"""VISSIM 을 띄우지 않고 도는 검사다. 근거는 `outputs/live_signal_cycle_probe_*.json`
이고, 그 값은 `scripts/probe_live_signal_cycle.vbs` 로 실제 VISSIM 을 400 초 돌려
SG 상태를 초당 받아 만든 것이다. 검사는 그 실측을 정답으로 두고 `.sig` 를 정적으로
다시 유도해 맞춰 본다 - 누가 `.sig` 를 건드리면 여기서 깨진다.

실측이 답한 것 셋.
- 재작성 `.sig` 는 원본과 같은 checkSum 을 그대로 달고 있는데도 VISSIM 이 받아들였다.
- 통제 15 SC 가 전부 정확히 150 s 로 돈다(원본은 140/150/160/170 네 종류였다).
- 현시는 11 SC 가 4, SC107/108/109 가 3(배리어 예외), SC5 가 6(SG 24개)이다.
"""
from __future__ import annotations

import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from plant.src.vissim_strict.signal_program import parse_sig  # noqa: E402

EVIDENCE = REPO / "outputs" / "live_signal_cycle_probe_n4dr150_20260812.json"
NETWORK_DIR = REPO / "network" / "real_world_gaepo_modi"


def _green_sets(program) -> int:
    """주기를 1 초 격자로 훑어 서로 다른 **동시녹색 집합** 개수를 센다.

    실측이 SG 상태를 초당 받아 같은 방식으로 셌으므로 격자도 1 초로 맞춘다.
    빈 집합(전현시 적색)은 현시가 아니므로 빼다.
    """
    cycle = int(round(program.cycle_length_sec))
    seen = set()
    for second in range(cycle):
        green = frozenset(
            sg_id
            for sg_id, timeline in program.sg_timelines.items()
            for interval in timeline.intervals
            if interval.state == "GREEN" and interval.start_sec <= second < interval.end_sec
        )
        if green:
            seen.add(green)
    return len(seen)


class LiveSignalCycleEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not EVIDENCE.is_file():
            raise AssertionError(f"실측 증거가 없다: {EVIDENCE}")
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.controllers = cls.evidence["controllers"]

    def test_the_rewritten_sig_keeps_the_original_checksum(self) -> None:
        """VISSIM 이 받아준 이유다. 누가 checkSum 을 새로 계산해 넣으면 깨진다."""
        for sc_no, entry in sorted(self.controllers.items(), key=lambda kv: int(kv[0])):
            with self.subTest(sc=sc_no):
                original = ET.parse(NETWORK_DIR / entry["original_sig"]).getroot()
                rewritten = ET.parse(NETWORK_DIR / entry["rewritten_sig"]).getroot()
                self.assertEqual(
                    original.attrib.get("checkSum"),
                    rewritten.attrib.get("checkSum"),
                    f"SC{sc_no} checkSum 이 원본과 달라졌다",
                )

    def test_the_static_cycle_matches_what_vissim_actually_ran(self) -> None:
        for sc_no, entry in sorted(self.controllers.items(), key=lambda kv: int(kv[0])):
            with self.subTest(sc=sc_no):
                program = parse_sig(NETWORK_DIR / entry["rewritten_sig"], entry["prog_no"])
                self.assertAlmostEqual(
                    float(entry["rewritten"]["cycle_sec"]),
                    program.cycle_length_sec,
                    places=6,
                    msg=f"SC{sc_no}",
                )

    def test_the_static_green_sets_match_the_measured_phase_count(self) -> None:
        for sc_no, entry in sorted(self.controllers.items(), key=lambda kv: int(kv[0])):
            with self.subTest(sc=sc_no):
                program = parse_sig(NETWORK_DIR / entry["rewritten_sig"], entry["prog_no"])
                self.assertEqual(
                    int(entry["rewritten"]["green_sets"]),
                    _green_sets(program),
                    f"SC{sc_no}",
                )

    def test_the_probe_discriminates_because_the_original_was_not_150(self) -> None:
        """되돌림 증명 - 원본을 같은 도구로 재면 140/150/160/170 네 종류가 나왔다.

        이 값이 전부 150 이었다면 위 검사들은 무엇도 증명하지 못한다.
        """
        measured = {int(entry["original"]["cycle_sec"]) for entry in self.controllers.values()}
        self.assertEqual({140, 150, 160, 170}, measured)
        self.assertEqual(
            {150},
            {int(entry["rewritten"]["cycle_sec"]) for entry in self.controllers.values()},
        )


if __name__ == "__main__":
    unittest.main()
