# v3 N4-1/N4-2/N4-3 - 실 .sig 에서 SG 타이밍 정본을 뽑는 생산자의 계약 테스트
"""이름 접두사로 SG 를 major/minor 로 접는 현행 규칙이 무엇을 망가뜨리는지 수치로 고정한다.

## 배경

지금 실런에서 SG 상태를 정하는 **유일한** 경로는 이름 부분문자열이다 —
`run_real_world_stackelberg_controller.vbs:1285-1299` 의 `SignalStateForGroup` 이
이름에 EB/WB 가 있으면 major, NB/SB 면 minor 를 준다. `(SC, SG번호) -> 모델 phase` 매핑은
저장소 어디에도 없다.

실 `.sig` 로 확인한 결과다(SC1001, 주기 150 s, SG 8개).

    WBL 0.160  EBT 0.300  NBL 0.193  SBT 0.267
    EBL 0.160  WBT 0.300  SBL 0.120  NBT 0.340

이름 규칙은 이것을 major 0.300 / minor 0.340 두 값으로 뭉갠다. 좌회전이 1.76~2.83 배
과대평가된다. 그리고 WBL(48-72 s)과 EBT(0-45 s)는 실제로 겹치지 않는데 둘 다 major 를
받아 **동시녹색**이 된다 — 대향 좌회전이 대향 직진을 횡단한다.
`.sig` 의 `<intergreenmatrices />` 가 비어 있어 VISSIM 도 막지 않는다.

## 이 생산자가 만드는 것

N4-1(SC별 native 주기), N4-2(충돌 SG 쌍), N4-3(SG별 녹색분율)이 공통으로 쓸 정본 표다.
셋을 따로 만들면 같은 `.sig` 를 세 번 파싱하고 서로 어긋난다.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import derive_signal_group_timing as timing  # noqa: E402


NETWORK_DIR = REPO / "network" / "real_world_gaepo_modi"
MAPPING = (
    REPO
    / "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core15n41_20260805.json"
)


class NameRuleTests(unittest.TestCase):
    def test_axis_rule_mirrors_the_vbs_substring_test(self) -> None:
        """VBS 와 같은 판정을 파이썬으로 미러링한다. 다르면 이 표가 거짓말을 한다."""
        self.assertEqual(timing.axis_for_name("EBT"), "major")
        self.assertEqual(timing.axis_for_name("WBL"), "major")
        self.assertEqual(timing.axis_for_name("NBT"), "minor")
        self.assertEqual(timing.axis_for_name("SBL"), "minor")
        # 어느 접두사도 없으면 축이 없다 - 조용히 major 로 떨어뜨리면 안 된다.
        self.assertIsNone(timing.axis_for_name("PED1"))
        self.assertIsNone(timing.axis_for_name(""))

    def test_axis_rule_is_case_insensitive_like_the_vbs(self) -> None:
        self.assertEqual(timing.axis_for_name("ebt"), "major")
        self.assertEqual(timing.axis_for_name("nbT"), "minor")


class OverlapTests(unittest.TestCase):
    def test_disjoint_windows_do_not_overlap(self) -> None:
        self.assertFalse(timing.windows_overlap([(0.0, 45.0)], [(48.0, 72.0)]))

    def test_touching_windows_do_not_overlap(self) -> None:
        """경계가 맞닿는 것은 겹침이 아니다. 아니면 모든 연속 현시가 충돌로 잡힌다."""
        self.assertFalse(timing.windows_overlap([(0.0, 45.0)], [(45.0, 60.0)]))

    def test_partial_overlap_counts(self) -> None:
        self.assertTrue(timing.windows_overlap([(0.0, 45.0)], [(44.0, 60.0)]))

    def test_wrapped_windows_are_compared_on_the_same_cycle(self) -> None:
        self.assertTrue(timing.windows_overlap([(140.0, 150.0)], [(145.0, 150.0)]))


@unittest.skipUnless(NETWORK_DIR.is_dir(), "실 네트워크 디렉터리 없음")
@unittest.skipUnless(MAPPING.is_file(), "core15n41 매핑 없음")
class RealNetworkTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.table = timing.derive(NETWORK_DIR, MAPPING)

    def test_every_controlled_controller_is_resolved(self) -> None:
        """미해결을 조용히 빼면 표가 통과한 것처럼 보이는데 자료가 없다."""
        self.assertEqual(len(self.table["controllers"]) + len(self.table["unresolved"]), 15)
        self.assertEqual(self.table["unresolved"], [], self.table["unresolved"])

    def test_native_cycles_are_not_the_model_scalar(self) -> None:
        """모델은 전역 120 s 하나뿐이다. 실망이 그렇지 않다는 것이 N4-1 의 근거다."""
        cycles = {c["sc_no"]: c["cycle_sec"] for c in self.table["controllers"]}
        self.assertTrue(cycles)
        self.assertNotEqual(set(cycles.values()), {120.0})

    def test_sc1001_green_fractions_match_the_measured_values(self) -> None:
        """직접 실측한 값이다. 파서나 프로그램 선택이 바뀌면 여기서 걸린다."""
        sc = next(c for c in self.table["controllers"] if c["sc_no"] == 1001)
        self.assertEqual(sc["cycle_sec"], 150.0)
        expected = {
            "WBL": 0.160, "EBT": 0.300, "NBL": 0.193, "SBT": 0.267,
            "EBL": 0.160, "WBT": 0.300, "SBL": 0.120, "NBT": 0.340,
        }
        actual = {g["name"]: round(g["green_fraction"], 3) for g in sc["groups"]}
        self.assertEqual(actual, expected)

    def test_the_name_rule_produces_simultaneous_green_on_disjoint_pairs(self) -> None:
        """N4-2 의 핵심 결함. 0 이 되면 이 테스트를 뒤집어야 한다(그때가 목표 상태다)."""
        conflicts = self.table["conflicting_pairs"]
        self.assertGreater(len(conflicts), 0, "충돌이 0 이면 결함이 사라진 것이다")
        for pair in conflicts:
            with self.subTest(pair=(pair["sc_no"], pair["a"], pair["b"])):
                self.assertEqual(pair["axis"], timing.axis_for_name(pair["a"]))
                self.assertEqual(pair["axis"], timing.axis_for_name(pair["b"]))
                self.assertFalse(pair["actually_overlaps"])

    def test_sc1001_wbl_and_ebt_are_reported_as_conflicting(self) -> None:
        """실측으로 확인한 구체 사례. 대향 좌회전이 대향 직진을 횡단한다."""
        pairs = {
            (p["a"], p["b"]) for p in self.table["conflicting_pairs"] if p["sc_no"] == 1001
        }
        self.assertIn(("EBT", "WBL"), {tuple(sorted(p)) for p in pairs})

    def test_overestimate_factor_is_reported_per_group(self) -> None:
        sc = next(c for c in self.table["controllers"] if c["sc_no"] == 1001)
        by_name = {g["name"]: g for g in sc["groups"]}
        self.assertAlmostEqual(by_name["NBT"]["axis_overestimate"], 1.0, places=6)
        self.assertGreater(by_name["SBL"]["axis_overestimate"], 2.0)


class CliTests(unittest.TestCase):
    @unittest.skipUnless(NETWORK_DIR.is_dir(), "실 네트워크 디렉터리 없음")
    @unittest.skipUnless(MAPPING.is_file(), "core15n41 매핑 없음")
    def test_main_writes_the_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "signal_group_timing_v3.json"
            self.assertEqual(
                timing.main(
                    ["--network-dir", str(NETWORK_DIR), "--mapping", str(MAPPING), "--out", str(out)]
                ),
                0,
            )
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], timing.SCHEMA_VERSION)
            self.assertEqual(
                payload["sample_dimensions"]["controllers"], len(payload["controllers"])
            )
            self.assertEqual(
                payload["sample_dimensions"]["conflicting_pairs"],
                len(payload["conflicting_pairs"]),
            )


if __name__ == "__main__":
    unittest.main()
