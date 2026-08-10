# v3 사전등록 상수 두 벌(FD 스텝 · 레버 진폭)이 섞이지 않게 고정하는 테스트
"""이름이 비슷한 두 진폭을 코드에서 분리한다.

계획에 진폭이 두 벌 있고 **서로 다른 양**이다. 문서만 보면 헷갈린다.

    전진폭 (N8-1, `:749` `:970`)   FD 미분 스텝. 기울기 추정용
        녹색 6 s · VSL 10 km/h · offset C/8 · 램프미터 max(300 veh/h, 0.20·capacity)

    진폭   (N9-2, `:886-889`)      짝지은 검증 레버 low/base/high
        녹색 ±10 s · VSL ±10 km/h · 램프미터 ±150 veh/h · offset ±10 s

둘 다 사전등록이라 런 후 수정이 금지된다. 그런데 계획의 "사전 등록" 절에는 FD 스텝만 적혀
있어, 거기만 읽은 사람은 N9 레버 진폭을 못 찾거나 FD 스텝을 레버 진폭으로 오해한다.

앞서 같은 부류의 사고가 있었다 — N9 행렬의 holdout 시드를 임의로 정했다가 N5 부모 런과
어긋났고, 두 명세가 서로 다른 절에 있어 놓쳤다. 그래서 이번엔 **코드에서 교차 정합을 건다.**
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import build_experiment_matrix_v3 as matrix  # noqa: E402
import build_parent_run_spec as parents  # noqa: E402
import preregistration_v3 as prereg  # noqa: E402


class SeparationTests(unittest.TestCase):
    def test_the_two_amplitude_sets_share_no_key(self) -> None:
        """키 어휘가 겹치면 한쪽을 다른 쪽 키로 잘못 인덱싱해도 조용히 값이 나온다.

        FD_STEP 은 'green_sec' 처럼 단위를 붙이고 LEVER_AMPLITUDE 는 'green' 처럼 레버
        이름을 쓴다. 그 차이가 실수를 KeyError 로 만든다.
        """
        self.assertTrue(prereg.FD_STEP)
        self.assertTrue(prereg.LEVER_AMPLITUDE)
        self.assertEqual(set(prereg.FD_STEP) & set(prereg.LEVER_AMPLITUDE), set())

    def test_indexing_one_with_the_other_key_raises(self) -> None:
        with self.assertRaises(KeyError):
            prereg.FD_STEP["green"]
        with self.assertRaises(KeyError):
            prereg.LEVER_AMPLITUDE["green_sec"]

    def test_fd_step_matches_the_plan(self) -> None:
        self.assertAlmostEqual(prereg.FD_STEP["green_sec"], 6.0)
        self.assertAlmostEqual(prereg.FD_STEP["vsl_kph"], 10.0)
        self.assertAlmostEqual(prereg.FD_STEP["offset_cycle_fraction"], 1.0 / 8.0)
        self.assertAlmostEqual(prereg.FD_STEP["ramp_meter_floor_veh_h"], 300.0)
        self.assertAlmostEqual(prereg.FD_STEP["ramp_meter_capacity_fraction"], 0.20)

    def test_ramp_fd_step_takes_the_larger_of_floor_and_fraction(self) -> None:
        """max(300 veh/h, 0.20·capacity) 는 둘 중 큰 쪽이다."""
        self.assertAlmostEqual(prereg.ramp_fd_step(1000.0), 300.0)
        self.assertAlmostEqual(prereg.ramp_fd_step(2000.0), 400.0)

    def test_offset_fd_step_is_cycle_dependent(self) -> None:
        """C/8 이므로 주기가 다르면 스텝도 다르다. 실망 주기는 100~170 s 다."""
        self.assertAlmostEqual(prereg.offset_fd_step(150.0), 18.75)
        self.assertAlmostEqual(prereg.offset_fd_step(100.0), 12.5)

    def test_lever_amplitude_matches_the_n9_matrix(self) -> None:
        """두 파일이 다른 값을 들면 봉인이 무의미해진다."""
        for lever, amplitudes in prereg.LEVER_AMPLITUDE.items():
            with self.subTest(lever=lever):
                self.assertEqual(amplitudes, matrix.LEVER_AMPLITUDES[lever])

    def test_fd_step_and_lever_amplitude_are_not_interchangeable(self) -> None:
        """혼동 방지의 핵심. 녹색은 6 s 대 ±10 s 로 실제로 다르다."""
        self.assertNotEqual(prereg.FD_STEP["green_sec"], prereg.LEVER_AMPLITUDE["green"][2])


class SeedTests(unittest.TestCase):
    def test_seeds_match_across_all_three_specs(self) -> None:
        """사전등록 · N9 행렬 · N5 부모 런이 같은 시드를 써야 한다."""
        self.assertEqual(prereg.TRAINING_SEEDS, (13, 29))
        self.assertEqual(prereg.HOLDOUT_SEEDS, (47,))

        n9 = matrix.default_spec()
        self.assertEqual(tuple(n9["development_seeds"]), prereg.TRAINING_SEEDS)
        self.assertEqual(tuple(n9["holdout_seeds"]), prereg.HOLDOUT_SEEDS)

        n5_seeds = {run["seed"] for run in parents.expand(parents.default_spec())}
        self.assertEqual(n5_seeds, set(prereg.TRAINING_SEEDS) | set(prereg.HOLDOUT_SEEDS))

    def test_holdout_is_excluded_from_fitting_and_threshold_choice(self) -> None:
        """계획 - holdout 은 N6 적합과 N8/N9 임계선택에 쓰지 않는다."""
        self.assertEqual(set(prereg.TRAINING_SEEDS) & set(prereg.HOLDOUT_SEEDS), set())
        self.assertEqual(prereg.HOLDOUT_USAGE, "promotion_only")


class HorizonTests(unittest.TestCase):
    def test_horizons_match_the_matrix(self) -> None:
        self.assertEqual(prereg.HORIZONS, (1, 3, 5, 10, 15))
        self.assertEqual(tuple(matrix.default_spec()["H"]), prereg.HORIZONS)

    def test_h1_is_an_independent_gate(self) -> None:
        self.assertTrue(prereg.H1_INDEPENDENT_GATE)


class NoiseFloorTests(unittest.TestCase):
    def test_noise_floors_reference_the_n5_constants(self) -> None:
        """두 잡음 바닥이 여기서도 갈라져 있어야 한다. 합치면 지지 요건이 무너진다."""
        self.assertAlmostEqual(
            prereg.EPS_J_VISSIM_FLOOR_VEH_H, parents.EPS_J_VISSIM_FLOOR_VEH_H
        )
        self.assertAlmostEqual(
            prereg.EPS_J_ENDPOINT_FLOOR_VEH_H, parents.EPS_J_ENDPOINT_FLOOR_VEH_H
        )
        self.assertNotEqual(
            prereg.EPS_J_VISSIM_FLOOR_VEH_H, prereg.EPS_J_ENDPOINT_FLOOR_VEH_H
        )


if __name__ == "__main__":
    unittest.main()
