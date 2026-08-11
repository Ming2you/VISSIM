# N4-0 작업1 관문 - 실 .sig 15개의 현 프로그램과 4현시 재배분 가능성을 고정하는 계약 테스트
"""목표 스펙(주기 150 · 4현시 · clearance 3 · green_min 20)이 실 산출물에서 성립하는가.

합성 픽스처를 쓰지 않는다. 검사는 전부 `modi_eval_rw_control.inpx` 가 `supplyFile2` 로
가리키는 실 `.sig` 15개(SG 136개)에 건다. 통과할 수밖에 없는 검사를 넣지 않기 위해,
수치는 전부 실측값으로 박고 **위반이 나는 SC 를 이름으로** 고정한다.

## 이 검사가 드러내는 것

`.sig` 를 4현시로 다시 쓰려면 네 현시 각각에 실제 이동류가 있어야 한다. 그런데 inpx 의
`signalHead` 를 세어 보면 15 SC 중 8 SC 가 **등두가 하나도 없는 현시**를 가진다. 등두 없는
SG 는 VISSIM 에서 차량에 아무 영향을 주지 않으므로, 그 현시에 green_min 20 s 를 주는 것은
주기의 13.3 % 를 처리량 0 으로 버리는 것이다.

SC107·SC108·SC109 는 그 위에 산술 위반까지 겹친다 — 현 배분을 138 s 로 비례 축소하면
빈 현시가 20 s 미만이 되고, SC108·SC109 는 major 직진이 green_max 78 s 를 넘는다.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import survey_signal_programs as survey  # noqa: E402


NETWORK = REPO / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
MAPPING = (
    REPO
    / "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core15n41_20260805.json"
)


def _table() -> dict:
    if not hasattr(_table, "cache"):
        _table.cache = survey.survey(NETWORK, MAPPING)
    return _table.cache


def _by_sc(table: dict) -> dict[int, dict]:
    return {int(row["sc_no"]): row for row in table["controllers"]}


class ProgramResolutionTests(unittest.TestCase):
    """어떤 `.sig` 를 읽는지가 먼저 맞아야 나머지 수치가 의미를 가진다."""

    def test_covers_the_fifteen_controlled_controllers_and_136_groups(self) -> None:
        table = _table()
        self.assertEqual(
            [row["sc_no"] for row in table["controllers"]],
            [1, 5, 6, 11, 12, 101, 105, 107, 108, 109, 1001, 1002, 1003, 1004, 1005],
        )
        self.assertEqual(table["counts"]["signal_groups"], 136)

    def test_resolves_the_four_controllers_whose_sig_name_differs_from_the_sc_number(self) -> None:
        """SC5/6/11/12 는 파일명 끝자리와 inpx 배정이 다르다. 여기서 틀리면 표 전체가 거짓이다."""
        rows = _by_sc(_table())
        self.assertTrue(rows[5]["sig_file"].endswith("test-bed7.sig"))
        self.assertTrue(rows[6]["sig_file"].endswith("test-bed9.sig"))
        self.assertTrue(rows[11]["sig_file"].endswith("test-bed3.sig"))
        self.assertTrue(rows[12]["sig_file"].endswith("test-bed5.sig"))

    def test_native_cycles_are_a_four_way_mix_with_150_in_seven_controllers(self) -> None:
        rows = _by_sc(_table())
        cycles: dict[float, list[int]] = {}
        for sc_no, row in rows.items():
            cycles.setdefault(row["cycle_sec"], []).append(sc_no)
        self.assertEqual(sorted(cycles), [140.0, 150.0, 160.0, 170.0])
        self.assertEqual(cycles[140.0], [12])
        self.assertEqual(cycles[150.0], [11, 105, 1001, 1002, 1003, 1004, 1005])
        self.assertEqual(cycles[160.0], [1, 5, 6, 101])
        self.assertEqual(cycles[170.0], [107, 108, 109])

    def test_sc5_is_the_only_controller_with_more_than_eight_groups(self) -> None:
        """SC5 의 24개 중 16개는 midblock 슬레이브다. 현시 평균에서 빠져야 한다."""
        rows = _by_sc(_table())
        wide = {sc: len(row["signal_groups"]) for sc, row in rows.items() if len(row["signal_groups"]) != 8}
        self.assertEqual(wide, {5: 24})
        midblock = [g for g in rows[5]["signal_groups"] if g["midblock_parent_sg"]]
        self.assertEqual(len(midblock), 16)
        self.assertEqual(
            {g["sg_id"]: g["midblock_parent_sg"] for g in midblock if g["head_count"] > 0},
            {"10": "2", "14": "6", "18": "2", "20": "4", "24": "8"},
        )


class NativeStructureTests(unittest.TestCase):
    """현 프로그램이 몇 단계이고 배리어 총량이 얼마인지를 실측으로 고정한다."""

    def test_twelve_controllers_are_four_stage_three_are_not(self) -> None:
        rows = _by_sc(_table())
        stages = {sc: row["implied_stage_count"] for sc, row in rows.items()}
        self.assertEqual(stages[107], 3)
        self.assertEqual(stages[108], 3)
        self.assertIsNone(stages[109], "SC109 는 EBT 가 두 단계에 걸쳐 단계 수가 정수가 아니다")
        four = sorted(sc for sc, value in stages.items() if value == 4)
        self.assertEqual(four, [1, 5, 6, 11, 12, 101, 105, 1001, 1002, 1003, 1004, 1005])

    def test_sc1001_barrier_totals_match_the_hand_measured_dual_ring(self) -> None:
        """링 A EBT45->WBL24 ‖ SBT40->NBL29, 링 B WBT45->EBL24 ‖ NBT51->SBL18."""
        row = _by_sc(_table())[1001]
        self.assertEqual(row["cycle_sec"], 150.0)
        self.assertEqual(row["phases"]["major_through"]["mean_green_sec"], 45.0)
        self.assertEqual(row["phases"]["major_left"]["mean_green_sec"], 24.0)
        self.assertEqual(row["phases"]["minor_through"]["mean_green_sec"], 45.5)
        self.assertEqual(row["phases"]["minor_left"]["mean_green_sec"], 23.5)
        self.assertEqual(row["barrier_major_green_sec"], 69.0)
        self.assertEqual(row["barrier_minor_green_sec"], 69.0)
        self.assertEqual(row["effective_green_total_sec"], 138.0)
        self.assertEqual(row["implied_lost_sec"], 12.0)

    def test_every_native_clearance_is_a_three_second_amber_with_no_all_red(self) -> None:
        """실 `.sig` 의 clearance 는 amber 3 뿐이다. N4-0 작업3 이 러너를 여기에 맞췄다."""
        table = _table()
        durations = {
            round(end - start, 6)
            for row in table["controllers"]
            for group in row["signal_groups"]
            for start, end in group["amber_windows"]
        }
        self.assertEqual(durations, {3.0})


class HeadCoverageTests(unittest.TestCase):
    """등두가 없는 SG 는 신호를 줘도 차량에 닿지 않는다. 4현시 가능성의 물리적 근거다."""

    def test_thirty_five_signal_groups_carry_no_signal_head(self) -> None:
        table = _table()
        dead = sorted(
            f"SC{row['sc_no']}:{group['sg_id']}"
            for row in table["controllers"]
            for group in row["signal_groups"]
            if group["head_count"] == 0
        )
        self.assertEqual(len(dead), 35)
        self.assertIn("SC1:1", dead)   # WBL - major 좌회전이 물리적으로 없다
        self.assertIn("SC1:5", dead)   # EBL
        self.assertIn("SC107:4", dead) # SBT - minor 직진이 없다
        self.assertIn("SC107:8", dead) # NBT
        self.assertNotIn("SC1001:1", dead)

    def test_eight_controllers_have_a_target_phase_with_no_head_at_all(self) -> None:
        """목표 현시 순서를 그대로 강제하면 이 SC 들은 빈 현시에 녹색을 버린다."""
        rows = _by_sc(_table())
        empty = {
            sc: sorted(name for name, phase in row["phases"].items() if phase["head_count"] == 0)
            for sc, row in rows.items()
        }
        self.assertEqual(empty[1], ["major_left"])
        self.assertEqual(empty[11], ["minor_left"])
        self.assertEqual(empty[105], ["major_left"])
        self.assertEqual(empty[107], ["minor_through"])
        self.assertEqual(empty[108], ["minor_left"])
        self.assertEqual(empty[109], ["minor_through"])
        self.assertEqual(empty[1003], ["major_through"])
        self.assertEqual(empty[1005], ["major_left", "minor_through"])
        self.assertEqual(
            sorted(sc for sc, names in empty.items() if names),
            [1, 11, 105, 107, 108, 109, 1003, 1005],
        )
        self.assertEqual(empty[6], [])
        self.assertEqual(empty[1001], [])


class RedistributionTests(unittest.TestCase):
    """배리어 총량 비례 보존 규칙을 138 s 에 적용한 결과."""

    def test_rule_preserves_the_barrier_share_and_sums_to_138(self) -> None:
        table = _table()
        for row in table["controllers"]:
            target = row["target"]
            total = sum(target[name]["green_sec"] for name in survey.PHASE_ORDER)
            self.assertAlmostEqual(total, 138.0, places=6, msg=f"SC{row['sc_no']}")

    def test_the_seven_150_second_controllers_keep_their_absolute_greens(self) -> None:
        """주기가 이미 150 이면 비례 축소가 항등이라 절대 초가 보존된다."""
        row = _by_sc(_table())[1001]
        self.assertEqual(row["target"]["major_through"]["green_sec"], 45.0)
        self.assertEqual(row["target"]["major_left"]["green_sec"], 24.0)
        self.assertEqual(row["target"]["minor_through"]["green_sec"], 45.5)
        self.assertEqual(row["target"]["minor_left"]["green_sec"], 23.5)

    def test_sc1_minor_left_lands_just_above_green_min(self) -> None:
        """SC1 은 148 -> 138 축소로 minor 좌회전이 22 -> 20.51 이 된다. 여유가 0.51 s 뿐이다."""
        row = _by_sc(_table())[1]
        self.assertAlmostEqual(row["target"]["minor_left"]["green_sec"], 20.514, places=3)

    def test_three_controllers_violate_the_target_spec(self) -> None:
        table = _table()
        offenders = {
            row["sc_no"]: sorted(row["violations"])
            for row in table["controllers"]
            if row["violations"]
        }
        self.assertEqual(sorted(offenders), [107, 108, 109])
        self.assertIn("minor_through green 0.00s < green_min 20s", offenders[107])
        self.assertIn("minor_left green 0.00s < green_min 20s", offenders[108])
        self.assertIn("major_through green 86.57s > green_max 78s", offenders[108])
        self.assertIn("major_through green 109.95s > green_max 78s", offenders[109])
        self.assertIn("minor_left green 9.05s < green_min 20s", offenders[109])

    def test_status_is_fail_so_the_gate_stops_before_rewriting_sig(self) -> None:
        table = _table()
        self.assertEqual(table["status"], "FAIL")
        self.assertEqual(table["counts"]["controllers_violating_target"], 3)
        self.assertEqual(table["counts"]["controllers_with_empty_phase"], 8)


class PureRedistributionTests(unittest.TestCase):
    """규칙 자체는 순함수다. 실 표와 별개로 산술을 고정한다."""

    def test_scaling_is_proportional_and_exact(self) -> None:
        scaled = survey.scale_to_total({"a": 74.0, "b": 74.0}, 138.0)
        self.assertAlmostEqual(scaled["a"], 69.0)
        self.assertAlmostEqual(scaled["b"], 69.0)

    def test_zero_total_is_refused_rather_than_dividing_by_zero(self) -> None:
        with self.assertRaises(survey.SurveyError):
            survey.scale_to_total({"a": 0.0}, 138.0)


if __name__ == "__main__":
    unittest.main()
