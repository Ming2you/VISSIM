# v3 N5 - 개발용 부모 런 9개와 잡음 바닥 절차의 계약을 고정하는 테스트
"""부모 런과 두 가지 잡음 바닥을 런 전에 봉인한다.

## 왜 두 가지인가 — 절대 혼용하지 마라

계획(N5)이 명시한다.

    이것은 VISSIM 런간 분산 척도이고 N9 의 ΔJ 재료성 판정 전용이다.
    플랜트 endpoint 의 재현성 잡음 eps_J_endpoint 는 별개이며 N8-1 에서 따로 측정한다.

두 값은 하한이 세 자리 다르고(1e-6 veh·h 대 1e-9) 재는 대상이 다르다. v3 초판이 이 둘을
하나로 합쳐 VISSIM 척도를 endpoint 자리에 넣었는데, 그러면 eps_g 가 과대해져
`|intercept| <= median(eps_g)` 가 느슨해지고 재료 표본이 줄어 지지 요건이 무너진다.

그래서 이 모듈은 **두 상수를 이름부터 분리**하고, 하나를 다른 자리에 쓰면 거부한다.

## 부모 런 9개

    training   demand 0.75, 1.0   seed 13, 29    4개
    congested  demand 1.25        seed 13, 29    2개
    holdout    demand 0.75/1.0/1.25  seed 47     3개

시드 집합은 {13, 29, 47} 이고 N9 실험 행렬과 같아야 한다. 어긋나면 부모 런이 없는 셀이
생기고 그것은 런을 다 돌린 뒤에야 드러난다.
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
import build_parent_run_spec as parents  # noqa: E402


class NoiseFloorTests(unittest.TestCase):
    def test_the_two_noise_floors_are_separate_constants(self) -> None:
        self.assertAlmostEqual(parents.EPS_J_VISSIM_FLOOR_VEH_H, 1.0e-6)
        self.assertAlmostEqual(parents.EPS_J_ENDPOINT_FLOOR_VEH_H, 1.0e-9)
        self.assertNotEqual(
            parents.EPS_J_VISSIM_FLOOR_VEH_H, parents.EPS_J_ENDPOINT_FLOOR_VEH_H
        )

    def test_vissim_floor_is_computed_from_base_replay_spread(self) -> None:
        """eps_J_vissim = max(1e-6, max_i,j |J_i − J_j|)."""
        self.assertAlmostEqual(
            parents.eps_j_vissim([10.0, 10.5, 10.2]), 0.5, places=12
        )

    def test_vissim_floor_never_drops_below_its_own_floor(self) -> None:
        self.assertAlmostEqual(
            parents.eps_j_vissim([7.0, 7.0]), parents.EPS_J_VISSIM_FLOOR_VEH_H, places=15
        )

    def test_vissim_floor_requires_the_full_replay_count(self) -> None:
        """계획 - 부모-anchor 당 20회. 이 부분은 축소하지 않는다고 못박혀 있다."""
        self.assertEqual(parents.BASE_REPLAYS_PER_PARENT_ANCHOR, 20)
        with self.assertRaises(parents.ParentRunError):
            parents.eps_j_vissim([1.0] * 19, require_full_count=True)
        self.assertIsNotNone(parents.eps_j_vissim([1.0] * 20, require_full_count=True))

    def test_endpoint_floor_cannot_be_fed_vissim_replays(self) -> None:
        """둘을 섞으면 eps_g 가 과대해져 지지 요건이 무너진다. 자리에서 막는다."""
        with self.assertRaises(parents.ParentRunError):
            parents.eps_j_endpoint([1.0, 2.0], source="vissim_base_replay")

    def test_endpoint_floor_accepts_its_own_source(self) -> None:
        value = parents.eps_j_endpoint([1.0, 1.0], source="plant_endpoint_repeat")
        self.assertAlmostEqual(value, parents.EPS_J_ENDPOINT_FLOOR_VEH_H, places=15)


class ParentRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = parents.default_spec()
        self.runs = parents.expand(self.spec)

    def test_there_are_exactly_nine_parents(self) -> None:
        self.assertEqual(len(self.runs), 9)

    def test_role_counts_match_the_plan(self) -> None:
        counts: dict[str, int] = {}
        for run in self.runs:
            counts[run["role"]] = counts.get(run["role"], 0) + 1
        self.assertEqual(counts, {"training": 4, "congested": 2, "holdout": 3})

    def test_training_and_holdout_seeds_never_overlap(self) -> None:
        training = {r["seed"] for r in self.runs if r["role"] != "holdout"}
        holdout = {r["seed"] for r in self.runs if r["role"] == "holdout"}
        self.assertEqual(training & holdout, set())

    def test_spsa_seed_is_shared_with_training_not_added(self) -> None:
        """계획 - SPSA 전용 seed 31 은 training 과 공유한다(별도 3개를 만들지 않는다)."""
        self.assertIn(self.spec["spsa_seed"], {r["seed"] for r in self.runs})
        self.assertEqual(len(self.runs), 9)

    def test_every_parent_carries_every_anchor(self) -> None:
        for run in self.runs:
            self.assertEqual(tuple(run["anchor_sec"]), (900, 1500, 2100, 2700))

    def test_no_duplicate_parent_identities(self) -> None:
        keys = [(r["demand"], r["seed"]) for r in self.runs]
        self.assertEqual(len(keys), len(set(keys)))

    def test_seeds_match_the_n9_experiment_matrix(self) -> None:
        """어긋나면 부모 런이 없는 셀이 생기고 런을 다 돌린 뒤에야 안다."""
        n9 = matrix.default_spec()
        n9_seeds = set(n9["development_seeds"]) | set(n9["holdout_seeds"])
        self.assertEqual({r["seed"] for r in self.runs}, n9_seeds)
        self.assertEqual(tuple(sorted({r["demand"] for r in self.runs})), n9["demand"])


class CliTests(unittest.TestCase):
    def test_main_writes_a_sealed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "parent_runs_v3.json"
            self.assertEqual(parents.main(["--out", str(out)]), 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], parents.SCHEMA_VERSION)
            self.assertEqual(payload["sample_dimensions"]["parents"], 9)
            self.assertEqual(
                payload["sample_dimensions"]["base_replays_total"],
                9 * 4 * parents.BASE_REPLAYS_PER_PARENT_ANCHOR,
            )
            self.assertEqual(payload["seal_sha256"], parents.seal_hash(parents.default_spec()))
            # 두 잡음 바닥이 서로 다른 이름으로 함께 실려야 한다.
            self.assertIn("eps_j_vissim_floor_veh_h", payload["noise_floors"])
            self.assertIn("eps_j_endpoint_floor_veh_h", payload["noise_floors"])


if __name__ == "__main__":
    unittest.main()
