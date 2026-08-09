# v3 N9-1/N9-2 - 실험 행렬 전개와 13필드 런 키의 계약을 고정하는 테스트
"""짝지은 VISSIM 검증의 실험 행렬을 **런 전에 봉인**한다.

계획 원문(N9-2)이 요구하는 것이다.

    세 값이 서로 구별되지 않으면 그 셀을 NOT_EVALUATED 로 기록하고 더 작은 대칭 step 을
    한 번만 시도한다. 값을 사후 조정하지 않고 요청 매니페스트에 정확한 값을 먼저 봉인한다.

사후 조정 금지가 이 모듈의 존재 이유다. 진폭을 런 결과를 보고 고치면 사전등록이 무의미해진다.
그래서 전개는 순수 함수이고, 산출물은 해시로 봉인되며, 같은 spec 은 항상 같은 행렬을 낸다.
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

import build_experiment_matrix_v3 as matrix  # noqa: E402


class RunKeyTests(unittest.TestCase):
    def test_run_key_has_exactly_the_thirteen_planned_fields(self) -> None:
        """v2.1 은 21필드였고 v3 는 13필드로 줄였다. 수와 순서를 고정한다."""
        self.assertEqual(
            matrix.RUN_KEY_FIELDS,
            (
                "experiment_id",
                "inpx_hash",
                "topology_sha256",
                "calibration_version",
                "controller_version",
                "demand",
                "seed",
                "anchor_sec",
                "H",
                "channel",
                "lever_id",
                "action_payload_hash",
                "replicate",
            ),
        )

    def test_run_key_is_order_independent_over_the_input_mapping(self) -> None:
        """dict 순서가 키를 바꾸면 같은 셀이 두 런으로 갈린다."""
        cell = {name: str(index) for index, name in enumerate(matrix.RUN_KEY_FIELDS)}
        shuffled = dict(reversed(list(cell.items())))
        self.assertEqual(matrix.run_key(cell), matrix.run_key(shuffled))

    def test_run_key_rejects_a_missing_field(self) -> None:
        """빠진 필드를 빈 값으로 때우면 서로 다른 셀이 같은 키를 갖는다."""
        cell = {name: "x" for name in matrix.RUN_KEY_FIELDS}
        del cell["anchor_sec"]
        with self.assertRaises(matrix.MatrixError):
            matrix.run_key(cell)

    def test_run_key_rejects_an_unknown_field(self) -> None:
        cell = {name: "x" for name in matrix.RUN_KEY_FIELDS}
        cell["extra"] = "y"
        with self.assertRaises(matrix.MatrixError):
            matrix.run_key(cell)


class LeverAmplitudeTests(unittest.TestCase):
    def test_preregistered_amplitudes_match_the_plan(self) -> None:
        """사전등록 진폭. 이 숫자가 바뀌면 사전등록이 깨진 것이다."""
        self.assertEqual(matrix.LEVER_AMPLITUDES["green"], (-10.0, 0.0, 10.0))
        self.assertEqual(matrix.LEVER_AMPLITUDES["vsl"], (-10.0, 0.0, 10.0))
        self.assertEqual(matrix.LEVER_AMPLITUDES["ramp_meter"], (-150.0, 0.0, 150.0))
        self.assertEqual(matrix.LEVER_AMPLITUDES["offset"], (-10.0, 0.0, 10.0))

    def test_offset_is_blocked_until_the_signal_oracle_passes(self) -> None:
        """offset 은 N4-6 D-core PASS 전까지 test-only writer 전용이고 BLOCKED 다.

        계획 원문 - "실현 readback 이 같은 valid-interval 계약을 입증하지 못하면 offset 은
        NOT_EVALUATED/BLOCKED 이고 production writer 는 intent_only 로 남는다".
        """
        self.assertEqual(matrix.LEVER_STATUS["offset"], "BLOCKED")
        self.assertEqual(matrix.LEVER_WRITER["offset"], "test_only")
        for lever in ("green", "vsl", "ramp_meter"):
            self.assertEqual(matrix.LEVER_WRITER[lever], "production")


class MatrixExpansionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = matrix.default_spec()

    def test_default_spec_matches_the_plan(self) -> None:
        self.assertEqual(self.spec["demand"], (0.75, 1.0, 1.25))
        self.assertEqual(self.spec["anchor_sec"], (900, 1500, 2100, 2700))
        self.assertEqual(self.spec["H"], (1, 3, 5, 10, 15))
        self.assertEqual(self.spec["sim_period_sec"], 3600)
        self.assertEqual(self.spec["warmup_sec"], 900)
        self.assertEqual(self.spec["control_interval_sec"], 60)
        # development 진단은 13/29, 승격 판정은 holdout 만.
        self.assertEqual(self.spec["development_seeds"], (13, 29))
        # holdout 은 N5 가 정한 **단일 시드 47** 이다. v2.1 의 인증 wave 3시드(47/59/71)를
        # 대신한 값이므로 여기서 임의로 늘리면 N5 부모 런 9개와 어긋난다.
        self.assertEqual(self.spec["holdout_seeds"], (47,))
        self.assertEqual(
            set(self.spec["development_seeds"]) & set(self.spec["holdout_seeds"]), set()
        )

    def test_seed_set_matches_the_n5_parent_runs(self) -> None:
        """N5 부모 런은 demand 3 x seed 3 = 9 개다. 행렬 시드가 그것과 같아야 한다.

        N5 표를 풀면 training(0.75,1.0)x(13,29)=4, congested(1.25)x(13,29)=2,
        holdout(0.75,1.0,1.25)x47=3 으로 총 9 이고, 시드 집합은 {13,29,47} 이다.
        행렬이 다른 시드를 쓰면 부모 런이 없는 셀이 생긴다 - 런을 다 돌린 뒤에야 안다.
        """
        seeds = set(self.spec["development_seeds"]) | set(self.spec["holdout_seeds"])
        self.assertEqual(seeds, {13, 29, 47})
        self.assertEqual(len(self.spec["demand"]) * len(seeds), 9)

    def test_expansion_is_one_lever_at_a_time(self) -> None:
        """기본은 레버 하나씩이다. joint action 은 별도 experiment_id 다."""
        cells = matrix.expand(self.spec)
        self.assertTrue(cells)
        for cell in cells:
            self.assertIn(cell["lever_id"], matrix.LEVER_AMPLITUDES)

    def test_every_cell_carries_a_complete_run_key(self) -> None:
        for cell in matrix.expand(self.spec):
            matrix.run_key(cell)  # 불완전하면 MatrixError 로 죽는다

    def test_run_keys_are_unique(self) -> None:
        cells = matrix.expand(self.spec)
        keys = [matrix.run_key(cell) for cell in cells]
        self.assertEqual(len(keys), len(set(keys)))

    def test_anchor_plus_horizon_never_exceeds_the_run(self) -> None:
        """anchor 2700 에서 H=15 면 2700 + 15x60 = 3600 이라 딱 맞는다. 넘으면 잘린 셀이다."""
        for cell in matrix.expand(self.spec):
            end = cell["anchor_sec"] + cell["H"] * self.spec["control_interval_sec"]
            self.assertLessEqual(end, self.spec["sim_period_sec"], str(cell))

    def test_blocked_levers_are_marked_not_run(self) -> None:
        cells = matrix.expand(self.spec)
        offsets = [c for c in cells if c["lever_id"] == "offset"]
        self.assertTrue(offsets)
        for cell in offsets:
            self.assertEqual(cell["status"], "BLOCKED")

    def test_material_comparisons_per_demand_H_channel_reach_sixteen(self) -> None:
        """계획 - 레버 효과는 demand x H x 채널마다 재료 비교 16개 이상.

        재료 비교 = base 가 아닌 셀(low/high)의 수다. 이 수가 모자라면 행렬 설계가 틀린 것이고,
        런을 다 돌린 뒤에 알게 되면 되돌릴 수 없다. 그래서 전개 단계에서 센다.
        """
        counts = matrix.material_comparison_counts(self.spec)
        self.assertTrue(counts)
        short = {k: v for k, v in counts.items() if v < 16}
        self.assertEqual(short, {}, f"재료 비교가 16개 미만인 셀: {short}")


class SealTests(unittest.TestCase):
    def test_seal_is_deterministic(self) -> None:
        spec = matrix.default_spec()
        self.assertEqual(matrix.seal_hash(spec), matrix.seal_hash(matrix.default_spec()))

    def test_changing_an_amplitude_changes_the_seal(self) -> None:
        """사후 조정을 하면 봉인이 깨져야 한다. 안 깨지면 봉인이 아니다."""
        spec = matrix.default_spec()
        tampered = matrix.default_spec()
        tampered["lever_amplitudes"] = dict(tampered["lever_amplitudes"])
        tampered["lever_amplitudes"]["green"] = (-5.0, 0.0, 5.0)
        self.assertNotEqual(matrix.seal_hash(spec), matrix.seal_hash(tampered))

    def test_main_writes_a_manifest_with_the_seal_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "experiment_matrix_v3.json"
            self.assertEqual(matrix.main(["--out", str(out)]), 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], matrix.SCHEMA_VERSION)
            self.assertEqual(payload["seal_sha256"], matrix.seal_hash(matrix.default_spec()))
            self.assertEqual(payload["run_key_fields"], list(matrix.RUN_KEY_FIELDS))
            self.assertEqual(len(payload["cells"]), payload["sample_dimensions"]["cells"])
            self.assertGreater(payload["sample_dimensions"]["runnable_cells"], 0)
            # BLOCKED 는 실행 대상에서 빠지되 행렬에는 남아야 한다 - 빠지면 사후에
            # "원래 없었다" 와 구별되지 않는다.
            self.assertGreater(payload["sample_dimensions"]["blocked_cells"], 0)
            self.assertEqual(
                payload["sample_dimensions"]["cells"],
                payload["sample_dimensions"]["runnable_cells"]
                + payload["sample_dimensions"]["blocked_cells"],
            )

    def test_manifest_states_the_simulation_cost_before_any_run(self) -> None:
        """행렬 규모를 런 전에 드러낸다. 이 도구의 존재 이유다.

        실측 - 실행 대상 2160셀, 총 시뮬 1325시간, 제어 결정 79,488회. 결정당 solve 가
        300초면 6,600시간이다. 즉 N8 solve 성능은 N9 의 선택지가 아니라 성립 조건이다.
        런을 다 돌린 뒤에 알면 되돌릴 수 없으므로 매니페스트에 새긴다.
        """
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "m.json"
            self.assertEqual(matrix.main(["--out", str(out)]), 0)
            dims = json.loads(out.read_text(encoding="utf-8"))["sample_dimensions"]

            spec = matrix.default_spec()
            runnable = [c for c in matrix.expand(spec) if c["status"] != "BLOCKED"]
            expected_sec = sum(c["horizon_end_sec"] for c in runnable)
            self.assertEqual(dims["total_simulated_sec"], expected_sec)
            self.assertEqual(
                dims["control_decisions"],
                sum(
                    c["horizon_end_sec"] // spec["control_interval_sec"] for c in runnable
                ),
            )
            # BLOCKED 셀은 비용에 넣지 않는다. 넣으면 돌지도 않을 런의 예산을 잡는다.
            self.assertLess(dims["total_simulated_sec"], 3600 * dims["cells"])


if __name__ == "__main__":
    unittest.main()
