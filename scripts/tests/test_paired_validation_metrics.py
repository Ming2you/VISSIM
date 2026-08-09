# v3 N9-4 - 짝지은 검증 지표와 합격 게이트의 계약을 고정하는 테스트
"""분모를 코드로 못박는다.

계획 원문(N9-4)이 이유를 밝힌다 — "지표 정의 (분모를 명시하지 않으면 두 사람이 다르게
계산한다)". 같은 런에서 두 사람이 다른 NMAE 를 내면 게이트는 아무것도 판정하지 못한다.

    NMAE       = Σ|pred − obs| / max(Σ obs, 1 veh)
    관측 0인 셀 = MAE <= 1 veh
    speed MAPE = 차량가중, 분모 max(obs_speed, 5 kph)
    TTT APE    = 분모 max(obs_TTT, 1 veh·h)

그리고 "모든 absolute metric 은 같은 분모의 signed bias 를 함께 게이트한다".
분모가 다르면 절대오차는 통과하는데 부호편향은 실패하는 모순이 생긴다.
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import paired_validation_metrics as metrics  # noqa: E402


class DenominatorTests(unittest.TestCase):
    def test_nmae_denominator_is_the_summed_observation_floored_at_one(self) -> None:
        """셀별이 아니라 **합계** 분모다. 셀별로 나누면 작은 관측이 오차를 폭발시킨다."""
        pred = [12.0, 8.0]
        obs = [10.0, 10.0]
        # Σ|pred-obs| = 2 + 2 = 4, Σobs = 20 -> 0.2
        self.assertAlmostEqual(metrics.nmae(pred, obs), 0.2, places=12)

    def test_nmae_denominator_floor_prevents_division_by_zero(self) -> None:
        """관측 총합이 0 이어도 무한대가 아니라 1 veh 로 나눈다."""
        self.assertAlmostEqual(metrics.nmae([0.5], [0.0]), 0.5, places=12)
        self.assertAlmostEqual(metrics.nmae([3.0], [0.0]), 3.0, places=12)

    def test_signed_bias_uses_the_same_denominator_as_nmae(self) -> None:
        """분모가 다르면 절대오차 통과 + 부호편향 실패라는 모순이 생긴다."""
        pred = [12.0, 12.0]
        obs = [10.0, 10.0]
        self.assertAlmostEqual(metrics.signed_bias(pred, obs), 0.2, places=12)
        self.assertAlmostEqual(metrics.nmae(pred, obs), 0.2, places=12)
        # 상쇄되는 경우 - 절대오차는 남고 부호편향은 0 이다.
        self.assertAlmostEqual(metrics.signed_bias([12.0, 8.0], obs), 0.0, places=12)
        self.assertAlmostEqual(metrics.nmae([12.0, 8.0], obs), 0.2, places=12)

    def test_zero_observation_cells_fall_back_to_absolute_mae(self) -> None:
        """관측 0인 셀은 비율이 정의되지 않으므로 MAE <= 1 veh 로 판정한다."""
        self.assertTrue(metrics.zero_observation_cell_passes(pred=0.4, obs=0.0))
        self.assertFalse(metrics.zero_observation_cell_passes(pred=1.4, obs=0.0))
        # 관측이 0 이 아니면 이 판정을 쓰면 안 된다.
        with self.assertRaises(metrics.MetricError):
            metrics.zero_observation_cell_passes(pred=0.4, obs=1.0)

    def test_speed_mape_is_vehicle_weighted_with_a_five_kph_floor(self) -> None:
        """분모 바닥이 없으면 정지 구간(관측 0 kph)이 MAPE 를 발산시킨다."""
        # 관측 2 kph 는 바닥 5 kph 로 올라간다. |10-2|/5 = 1.6
        self.assertAlmostEqual(
            metrics.speed_mape([10.0], [2.0], weights=[1.0]), 1.6, places=12
        )
        # 차량가중 - 대수가 많은 구간이 더 무겁다.
        value = metrics.speed_mape([10.0, 10.0], [20.0, 20.0], weights=[1.0, 3.0])
        self.assertAlmostEqual(value, 0.5, places=12)

    def test_ttt_ape_denominator_is_floored_at_one_veh_hour(self) -> None:
        self.assertAlmostEqual(metrics.ttt_ape(3.0, 0.0), 3.0, places=12)
        self.assertAlmostEqual(metrics.ttt_ape(11.0, 10.0), 0.1, places=12)


class GehTests(unittest.TestCase):
    def test_geh_matches_the_standard_formula(self) -> None:
        # GEH = sqrt(2(m-c)^2 / (m+c))
        self.assertAlmostEqual(
            metrics.geh(110.0, 100.0), math.sqrt(2 * 100.0 / 210.0), places=12
        )

    def test_geh_of_two_zeros_is_zero_not_nan(self) -> None:
        """m+c=0 이면 0/0 이다. NaN 을 흘리면 비율 집계가 통째로 오염된다."""
        self.assertEqual(metrics.geh(0.0, 0.0), 0.0)

    def test_geh_pass_fraction_counts_rows_at_or_below_five(self) -> None:
        pred = [100.0, 100.0, 100.0, 1000.0]
        obs = [100.0, 105.0, 110.0, 500.0]
        fraction = metrics.geh_pass_fraction(pred, obs, threshold=5.0)
        # 마지막 행만 GEH > 5 다.
        self.assertAlmostEqual(fraction, 0.75, places=12)


class GateTableTests(unittest.TestCase):
    def test_gate_table_covers_exactly_the_planned_horizons(self) -> None:
        self.assertEqual(sorted(metrics.GATES), [1, 3, 5, 10, 15])

    def test_h1_thresholds_match_the_plan(self) -> None:
        gate = metrics.GATES[1]
        self.assertAlmostEqual(gate["urban_queue_storage_nmae"], 0.15)
        self.assertAlmostEqual(gate["travel_time_median_sec"], 5.0)
        self.assertAlmostEqual(gate["travel_time_p95_sec"], 15.0)
        self.assertAlmostEqual(gate["queue_tail_mae_m"], 20.0)
        self.assertAlmostEqual(gate["speed_mape"], 0.10)
        self.assertAlmostEqual(gate["count_mae_veh"], 5.0)
        self.assertAlmostEqual(gate["count_mae_fraction"], 0.10)
        self.assertAlmostEqual(gate["geh_pass_fraction"], 0.85)
        self.assertAlmostEqual(gate["flow_signed_bias"], 0.10)
        self.assertAlmostEqual(gate["ttt_ape"], 0.10)

    def test_flow_signed_bias_is_ten_percent_at_every_horizon(self) -> None:
        """계획 - flow signed bias 는 항상 <=10%. H 가 커져도 완화하지 않는다."""
        for horizon, gate in metrics.GATES.items():
            self.assertAlmostEqual(
                gate["flow_signed_bias"], 0.10, msg=f"H={horizon} 에서 완화됐다"
            )

    def test_count_mae_uses_max_of_absolute_and_fractional(self) -> None:
        """계획 표기 max(5 veh, 10%) 는 둘 중 **큰 쪽**을 허용한다는 뜻이다."""
        # 관측 총합 30 veh -> 10% = 3 veh 인데 절대 5 veh 가 더 크므로 5 가 한계다.
        self.assertAlmostEqual(metrics.count_mae_limit(1, observed_total=30.0), 5.0)
        # 관측 총합 200 veh -> 10% = 20 veh 가 더 크다.
        self.assertAlmostEqual(metrics.count_mae_limit(1, observed_total=200.0), 20.0)

    def test_h1_is_an_independent_gate(self) -> None:
        """계획 - H=1 은 독립 게이트이고 다른 H 로 구제하지 않는다."""
        results = {1: {"ttt_ape": 0.30}, 3: {"ttt_ape": 0.01}, 5: {"ttt_ape": 0.01}}
        verdict = metrics.evaluate(results)
        self.assertEqual(verdict["status"], "FAIL")
        self.assertIn(1, verdict["failed_horizons"])

    def test_absolute_metric_is_gated_together_with_its_signed_bias(self) -> None:
        """부호편향이 절대지표 한계를 넘으면 실패다."""
        passing = {1: {"speed_mape": 0.05, "speed_signed_bias": 0.05}}
        self.assertEqual(metrics.evaluate(passing)["status"], "PASS")
        # 절대지표는 통과하는데 부호편향이 한계를 넘는 경우.
        failing = {1: {"speed_mape": 0.05, "speed_signed_bias": 0.12}}
        verdict = metrics.evaluate(failing)
        self.assertEqual(verdict["status"], "FAIL")
        self.assertTrue(
            any("signed_bias" in reason for reason in verdict["reasons"]),
            verdict["reasons"],
        )

    def test_missing_metric_is_not_evaluated_rather_than_passing(self) -> None:
        """없는 지표를 통과로 세면 측정을 덜 할수록 유리해진다."""
        verdict = metrics.evaluate({1: {}})
        self.assertEqual(verdict["status"], "NOT_EVALUATED")

    def test_unknown_horizon_is_rejected(self) -> None:
        with self.assertRaises(metrics.MetricError):
            metrics.evaluate({7: {"ttt_ape": 0.01}})


class SpillbackGateTests(unittest.TestCase):
    def test_low_demand_shortfall_is_not_evaluated(self) -> None:
        """면제는 저수요 셀에 한한다 - positive 5개 미만이면 NOT_EVALUATED."""
        self.assertEqual(
            metrics.spillback_status(positives=3, congested=False), "NOT_EVALUATED"
        )

    def test_congested_shortfall_is_blocked_not_exempt(self) -> None:
        """혼잡 셀에서 positive 10개 미만이면 BLOCKED 다.

        v3 초판은 "저수요" 한정을 빠뜨려 탐지를 덜 할수록 게이트를 피하는 역인센티브를
        만들었다. 그 구멍을 여기서 막는다.
        """
        self.assertEqual(metrics.spillback_status(positives=3, congested=True), "BLOCKED")
        self.assertEqual(metrics.spillback_status(positives=9, congested=True), "BLOCKED")
        self.assertEqual(
            metrics.spillback_status(positives=10, congested=True), "EVALUATED"
        )


if __name__ == "__main__":
    unittest.main()
