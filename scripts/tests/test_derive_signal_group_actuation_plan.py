# v3 N4-5 - SG 액추에이션 계획 생산자를 실 네트워크 기준으로 고정한다
"""생산자가 만드는 두 산출물의 계약을 고정한다.

  outputs/signal_group_actuation_plan_v3.json   모델·플랜트가 같이 읽는 정본
  evaluation/generated/*_sgplan.vbs             러너가 ExecuteGlobal 하는 상수

정본 타이밍 표(`signal_group_timing_v3.json`)를 쓰지 않는 것이 핵심이다. 그 표는 파일명
번호로 `.sig` 를 골라서 4/15 SC 에서 VISSIM 이 실제로 읽는 프로그램과 다르다
(`movement_signal_group_map_v3.json` 의 `timing_cross_check.agrees=False`). 계획은 inpx
`supplyFile2` 에서 나와야 한다 — 모델의 `compile_fixed_signal_schedules` 와 같은 출처다.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import derive_signal_group_actuation_plan as producer


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_PLAN = ROOT / "outputs" / "signal_group_actuation_plan_v3.json"
NETWORK = ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
MOVEMENT_MAP = ROOT / "outputs" / "movement_signal_group_map_v3.json"
MAPPING = (
    ROOT
    / "evaluation"
    / "real_world_modi_control_distributed_20260728"
    / "control_mapping_distributed_core15n41_20260805.json"
)


class DeriveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not NETWORK.is_file():
            raise unittest.SkipTest(f"run network missing: {NETWORK}")
        cls.table = producer.derive(NETWORK, MAPPING, MOVEMENT_MAP)

    def test_every_controlled_sc_is_planned(self) -> None:
        self.assertEqual(self.table["status"], "PASS")
        self.assertEqual(len(self.table["controllers"]), 15)
        self.assertEqual(sorted(int(key) for key in self.table["controllers"]), [
            1, 5, 6, 11, 12, 101, 105, 107, 108, 109, 1001, 1002, 1003, 1004, 1005
        ])

    def test_plan_covers_every_signal_group_the_controller_declares(self) -> None:
        counts = self.table["counts"]
        self.assertEqual(counts["signal_groups"], 136)
        self.assertEqual(counts["uncovered_signal_groups"], 0)

    def test_program_source_is_the_inpx_supply_file_not_the_timing_table(self) -> None:
        # SC5/SC6/SC11/SC12 는 두 출처가 다르다. 계획은 inpx 쪽을 따라야 한다.
        cycles = {
            str(key): float(value["native_cycle_sec"])
            for key, value in self.table["controllers"].items()
        }
        self.assertEqual(cycles["5"], 160.0)
        self.assertEqual(cycles["6"], 160.0)
        self.assertEqual(cycles["11"], 150.0)
        self.assertEqual(cycles["12"], 140.0)
        # 표 생산자가 파일명 번호로 `.sig` 를 고르던 동안 이 넷이 어긋나 있었다. 표가 inpx
        # supplyFile2 를 읽게 된 뒤로는 비어 있어야 한다 - 값이 아니라 **비어 있음**을 고정한다.
        self.assertEqual(sorted(self.table["timing_table_disagreements"]), [])

    def test_uncovered_counts_signal_groups_the_plan_dropped_not_never_green_ones(self) -> None:
        """`uncovered` 는 실패할 수 있어야 한다.

        예전 식은 `sg_no not in plan.window_counts` 였는데 `window_counts` 가 같은 sg_id
        목록으로 초기화되므로 **구조적으로 항상 0** 이었다. 통과해도 아무것도 보장하지 않는다.

        의미 있는 정의는 "native 프로그램에서 녹색이 있는데 계획에는 창이 없는 SG" 다.
        native 가 영원히 적색인 SG(실측 20개)가 창 0 인 것은 정상이라 세지 않는다.
        """
        self.assertEqual(
            producer.uncovered_signal_groups("SC9", {"1": 0, "2": 3}, {"1": 42.0, "2": 30.0}),
            ["SC9:1"],
        )
        self.assertEqual(
            producer.uncovered_signal_groups("SC9", {"1": 0, "2": 3}, {"1": 0.0, "2": 30.0}),
            [],
        )

    def test_the_real_plan_drops_no_natively_green_signal_group(self) -> None:
        dropped = [
            name
            for sc_no, node in self.table["controllers"].items()
            for name in producer.uncovered_signal_groups(
                f"SC{sc_no}", node["window_counts"], node["native_green_sec"]
            )
        ]
        self.assertEqual(dropped, [])
        self.assertEqual(self.table["counts"]["uncovered_signal_groups"], 0)
        # 창 0 인 20개는 전부 native 가 영원히 적색인 SG 다.
        self.assertEqual(self.table["counts"]["never_green_signal_groups"], 20)

    def test_conflict_pairs_are_recorded_and_the_plan_never_violates_them(self) -> None:
        self.assertGreater(self.table["counts"]["conflict_pairs"], 0)
        self.assertEqual(self.table["counts"]["conflict_violations"], 0)

    def test_canonical_simultaneous_green_pairs_are_covered_for_every_controller(self) -> None:
        """정본 표의 동시녹색 쌍을 우리 충돌 집합이 덮는가 - 15 SC 전부에 대해.

        예전에는 표가 다른 `.sig` 를 기술하는 4 SC 를 통째로 건너뛰었다. 표가 inpx
        supplyFile2 를 읽게 된 지금은 건너뛸 SC 가 없으므로, 제외는 **쌍 단위**로만 한다.

          - `vacuous`  한쪽이 영원히 적색이라 동시녹색이 구조적으로 불가능한 쌍.
          - `ambiguous` 표의 쌍은 SG **이름** 키인데 그 이름이 여러 sg_id 에 걸려
            (SC5 는 24 SG 중 8개가 중복 이름) 어느 조합인지 정할 수 없는 쌍.

        모호한 쌍을 빼도 남는 미커버가 있으면 그것이 결함이다.
        """
        timing = json.loads(
            (ROOT / "outputs" / "signal_group_timing_v3.json").read_text(encoding="utf-8")
        )
        covered = 0
        vacuous = 0
        ambiguous = 0
        uncovered: list[tuple[int, tuple[str, str]]] = []
        for controller in timing["controllers"]:
            sc_no = int(controller["sc_no"])
            node = self.table["controllers"][str(sc_no)]
            counts = node["window_counts"]
            pairs = {tuple(sorted(pair, key=int)) for pair in node["conflict_pairs"]}
            names: dict[str, list[str]] = {}
            for group in controller["groups"]:
                names.setdefault(group["name"], []).append(group["sg_id"])
            for pair in timing["conflicting_pairs"]:
                if int(pair["sc_no"]) != sc_no:
                    continue
                first_ids = names.get(pair["a"], [])
                second_ids = names.get(pair["b"], [])
                for first in first_ids:
                    for second in second_ids:
                        key = tuple(sorted((first, second), key=int))
                        if key in pairs:
                            covered += 1
                        elif counts.get(first, 0) == 0 or counts.get(second, 0) == 0:
                            vacuous += 1
                        elif len(first_ids) > 1 or len(second_ids) > 1:
                            ambiguous += 1
                        else:
                            uncovered.append((sc_no, key))
        self.assertEqual(uncovered, [])
        self.assertEqual(covered, 149)
        self.assertEqual(vacuous, 838)
        self.assertEqual(ambiguous, 171)

    def test_vbs_config_lists_expected_groups_and_conflicts(self) -> None:
        text = producer.render_vbs(self.table)
        self.assertIn("RW_SIGNAL_SG_PLAN_SCHEMA = 1", text)
        self.assertIn("RW_SIGNAL_SG_EXPECTED = ", text)
        self.assertIn("RW_SIGNAL_SG_CONFLICTS = ", text)
        self.assertIn("RW_SIGNAL_SG_PLAN_SOURCE_SHA256 = ", text)

        expected = producer.expected_token_list(self.table)
        self.assertEqual(len(expected), 136)
        self.assertTrue(all(token.count(":") == 2 for token in expected))
        # 창이 하나도 없는 SG 는 계획상 영구 적색이고, 그 사실이 토큰에 0 으로 남는다.
        self.assertTrue(any(token.endswith(":0") for token in expected))

        conflicts = producer.conflict_token_list(self.table)
        self.assertEqual(len(conflicts), self.table["counts"]["conflict_pairs"])
        self.assertTrue(all("-" in token and ":" in token for token in conflicts))

    def test_action_rows_reproduce_the_model_share(self) -> None:
        # SC1001 은 major_maps_to=p1 이라 축 귀속이 이름 규칙과 반대다. 여기서
        # 지시 녹색을 넣었을 때 SG 별 녹색이 native 분율대로 갈리는지 본다.
        rows = producer.action_windows(
            self.table, sc_no=1001,
            phase_greens={"p1": 61.0, "p2": 79.0, "p3": 0.0, "p4": 0.0},
        )
        realized: dict[str, float] = {}
        for row in rows:
            realized[row.sg_no] = realized.get(row.sg_no, 0.0) + (row.end_sec - row.start_sec)
        plan = self.table["controllers"]["1001"]
        axis_green = float(plan["axis_green_sec"]["p1"])
        for sg_no in plan["phase_signal_groups"]["p1"]:
            share = float(plan["native_green_sec"][sg_no]) / axis_green
            self.assertAlmostEqual(realized[sg_no], 61.0 * share, places=6)


class RenderSiblingFromCanonicalPlanTests(unittest.TestCase):
    """`--from-plan` — 이미 있는 계획 산출물에서 sgplan 형제 파일만 뽑는다.

    러너의 sgplan 은 **config 마다** 형제 파일이어야 하는데(`<config>_sgplan.vbs`),
    지금까지 그것을 만드는 길은 `main()` 뿐이었고 그 길은 계획 JSON 을 **다시 유도해
    덮어쓴다**. 그래서 config 하나 더 붙이려면 추적 산출물을 건드려야 했다.

    형제 파일이 실을 sha 는 **어댑터가 실제로 읽는 파일**(`SIGNAL_GROUP_ACTUATION_PLAN_PATH`)
    의 sha 여야 한다. 재유도한 사본의 sha 면 `test_action_csv_contract` 의 드리프트
    대조가 통과할 수 없다.
    """

    def setUp(self) -> None:
        if not CANONICAL_PLAN.is_file():
            self.skipTest("signal group actuation plan artifact is not built")

    def test_renders_the_sibling_without_rederiving_or_touching_the_plan(self) -> None:
        before = CANONICAL_PLAN.read_bytes()
        with tempfile.TemporaryDirectory() as temp_dir:
            out_vbs = Path(temp_dir) / "some_config_sgplan.vbs"
            code = producer.main(
                ["--from-plan", str(CANONICAL_PLAN), "--out-vbs", str(out_vbs)]
            )
            self.assertEqual(code, 0)
            text = out_vbs.read_text(encoding="utf-8")
        self.assertEqual(CANONICAL_PLAN.read_bytes(), before)
        self.assertIn(
            f'RW_SIGNAL_SG_PLAN_SOURCE_SHA256 = "{hashlib.sha256(before).hexdigest()}"',
            text,
        )
        table = json.loads(before.decode("utf-8"))
        joined = text.replace('" & _\n    "', "")
        self.assertIn(",".join(producer.expected_token_list(table)), joined)
        self.assertIn(";".join(producer.conflict_token_list(table)), joined)

    def test_the_rendered_sibling_is_byte_identical_to_the_committed_one(self) -> None:
        """같은 계획에서 나온 형제 파일은 config 이름과 무관하게 같은 바이트여야 한다.

        계약(SG 집합·충돌 쌍·원본 sha)은 계획에서만 나온다. config 이름이 들어가면
        그 순간 형제 파일마다 내용이 갈리고 드리프트 대조가 의미를 잃는다.
        """
        committed = (
            ROOT
            / "evaluation"
            / "generated"
            / "real_world_modi_control_config_distributed_core15n41_20260805_sgplan.vbs"
        )
        if not committed.is_file():
            self.skipTest("committed sgplan sibling is not present")
        with tempfile.TemporaryDirectory() as temp_dir:
            out_vbs = Path(temp_dir) / "other_config_sgplan.vbs"
            self.assertEqual(
                producer.main(["--from-plan", str(CANONICAL_PLAN), "--out-vbs", str(out_vbs)]),
                0,
            )
            self.assertEqual(out_vbs.read_bytes(), committed.read_bytes())

    def test_from_plan_refuses_a_plan_that_did_not_pass(self) -> None:
        """FAIL 계획으로 형제 파일을 만들 수 없다 - 그러면 fail-closed 가 아니다."""
        table = json.loads(CANONICAL_PLAN.read_text(encoding="utf-8"))
        table["status"] = "FAIL"
        with tempfile.TemporaryDirectory() as temp_dir:
            broken = Path(temp_dir) / "broken_plan.json"
            broken.write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
            out_vbs = Path(temp_dir) / "broken_sgplan.vbs"
            self.assertEqual(
                producer.main(["--from-plan", str(broken), "--out-vbs", str(out_vbs)]), 1
            )
            self.assertFalse(out_vbs.exists())


if __name__ == "__main__":
    unittest.main()
