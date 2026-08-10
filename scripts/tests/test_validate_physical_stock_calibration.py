# v3 N6 - 물리 stock 캘리브레이션 합격 기준을 검사하는 검증기의 계약 테스트
"""캘리브레이션이 합격인지 **판정 가능한 형태로** 못박는다.

계획(N6)의 PASS 는 일곱 항목이다.

    split 중복 0, 포화 독립 lane-group >=30, 표본 >=200,
    jam CI 반폭 <= 추정값의 10%, geometry prior 차이 <=15%,
    training 시드별 적합 차이 <=15%, fallback 분율 사용 <=10%

그리고 절차 요건이 하나 더 있다 — **적합은 training 시드에서만.** holdout 시드는 적합·
임계선택·후보교체에 쓰지 않는다. 이건 숫자가 아니라 출처 요건이라 값만 봐서는 확인할 수 없다.
그래서 아티팩트가 자기 split 을 신고하게 하고, holdout 이 섞이면 거부한다.

## 왜 검증기를 먼저 만드는가

지금 있는 자료(`outputs/urban_storage_capacity_20260805.json`)는 jam 표본이 177 개다.
기준 200 에 미달이고 CI 도 없다. 검증기가 없으면 그 사실을 아무도 체계적으로 말하지 못한다.
"무엇이 부족한가" 를 먼저 판정 가능하게 만드는 것이 새 데이터를 모으는 것보다 앞선다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import validate_physical_stock_calibration as calib  # noqa: E402


def complete_artifact() -> dict:
    """모든 기준을 통과하는 최소 아티팩트."""
    return {
        "schema_version": calib.SCHEMA_VERSION,
        "split": {
            "training_run_ids": ["r13", "r29"],
            "holdout_run_ids": ["r47"],
            "fit_source": "training",
        },
        "estimator": "theil_sen",
        "jam_density": {
            "value_veh_km_lane": 140.0,
            "sample_count": 220,
            "saturated_lane_groups": 34,
            "ci95_low": 133.0,
            "ci95_high": 147.0,
            "selection": {"speed_max_kph": 3.0, "stopped_fraction_min": 0.5},
        },
        "geometry_prior": {
            "vehicle_length_m": 6.0,
            "jam_spacing_m": 6.49,
            "fitted_jam_spacing_m": 6.8,
        },
        "per_training_seed_fit": {"13": 140.0, "29": 148.0},
        "fallback_fraction_used": 0.05,
        "queue_tail_source": "observed",
    }


class SchemaTests(unittest.TestCase):
    def test_missing_section_is_rejected(self) -> None:
        payload = complete_artifact()
        del payload["jam_density"]
        report = calib.validate(payload)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("jam_density.missing", report["reasons"])

    def test_complete_artifact_passes(self) -> None:
        report = calib.validate(complete_artifact())
        self.assertEqual(report["status"], "PASS", report["reasons"])
        self.assertEqual(report["reasons"], [])


class SplitTests(unittest.TestCase):
    def test_overlapping_split_is_rejected(self) -> None:
        payload = complete_artifact()
        payload["split"]["holdout_run_ids"] = ["r13"]
        report = calib.validate(payload)
        self.assertIn("split.overlap", report["reasons"])

    def test_fitting_on_holdout_is_rejected(self) -> None:
        """숫자가 아니라 출처 요건이다. 값만 봐서는 확인할 수 없어 신고를 요구한다."""
        payload = complete_artifact()
        payload["split"]["fit_source"] = "holdout"
        report = calib.validate(payload)
        self.assertIn("split.fit_source", report["reasons"])

    def test_empty_training_split_is_rejected(self) -> None:
        payload = complete_artifact()
        payload["split"]["training_run_ids"] = []
        self.assertIn("split.training_empty", calib.validate(payload)["reasons"])


class JamDensityTests(unittest.TestCase):
    def test_sample_count_below_two_hundred_is_rejected(self) -> None:
        payload = complete_artifact()
        payload["jam_density"]["sample_count"] = 199
        self.assertIn("jam_density.sample_count", calib.validate(payload)["reasons"])

    def test_fewer_than_thirty_saturated_lane_groups_is_rejected(self) -> None:
        payload = complete_artifact()
        payload["jam_density"]["saturated_lane_groups"] = 29
        self.assertIn(
            "jam_density.saturated_lane_groups", calib.validate(payload)["reasons"]
        )

    def test_ci_half_width_above_ten_percent_is_rejected(self) -> None:
        payload = complete_artifact()
        # 반폭 15 / 140 = 10.7%
        payload["jam_density"]["ci95_low"] = 125.0
        payload["jam_density"]["ci95_high"] = 155.0
        self.assertIn("jam_density.ci_half_width", calib.validate(payload)["reasons"])

    def test_missing_ci_is_rejected_not_treated_as_zero(self) -> None:
        """CI 가 없으면 반폭 0 이 아니라 미측정이다. 통과시키면 정밀도를 날조하는 것이다."""
        payload = complete_artifact()
        del payload["jam_density"]["ci95_low"]
        self.assertIn("jam_density.ci_missing", calib.validate(payload)["reasons"])

    def test_selection_thresholds_must_match_the_plan(self) -> None:
        payload = complete_artifact()
        payload["jam_density"]["selection"]["speed_max_kph"] = 5.0
        self.assertIn("jam_density.selection", calib.validate(payload)["reasons"])


class PriorAndSeedTests(unittest.TestCase):
    def test_geometry_prior_gap_above_fifteen_percent_is_rejected(self) -> None:
        payload = complete_artifact()
        payload["geometry_prior"]["fitted_jam_spacing_m"] = 6.49 * 1.16
        self.assertIn("geometry_prior.gap", calib.validate(payload)["reasons"])

    def test_seed_to_seed_fit_gap_above_fifteen_percent_is_rejected(self) -> None:
        payload = complete_artifact()
        payload["per_training_seed_fit"] = {"13": 140.0, "29": 140.0 * 1.16}
        self.assertIn("per_training_seed_fit.gap", calib.validate(payload)["reasons"])

    def test_a_single_training_seed_cannot_show_agreement(self) -> None:
        """시드 하나로는 시드간 차이를 잴 수 없다. 통과로 세면 검사가 무의미하다."""
        payload = complete_artifact()
        payload["per_training_seed_fit"] = {"13": 140.0}
        self.assertIn("per_training_seed_fit.insufficient", calib.validate(payload)["reasons"])

    def test_fallback_fraction_above_ten_percent_is_rejected(self) -> None:
        payload = complete_artifact()
        payload["fallback_fraction_used"] = 0.11
        self.assertIn("fallback_fraction_used", calib.validate(payload)["reasons"])

    def test_observed_queue_tail_is_preferred_over_fixed_fractions(self) -> None:
        """계획 - 큐꼬리 관측이 있으면 고정 분율(0.35/0.50) 대신 관측 분해를 쓴다."""
        payload = complete_artifact()
        payload["queue_tail_source"] = "fixed_fraction"
        report = calib.validate(payload)
        self.assertIn("queue_tail_source", report["reasons"])


class ExistingDataGapTests(unittest.TestCase):
    """지금 있는 자료가 무엇이 모자라는지 구체적으로 드러낸다."""

    STORAGE = REPO / "outputs" / "urban_storage_capacity_20260805.json"

    @unittest.skipUnless(STORAGE.is_file(), "기존 저장용량 산출물 없음")
    def test_current_jam_sample_count_is_below_the_bar(self) -> None:
        import json

        payload = json.loads(self.STORAGE.read_text(encoding="utf-8"))
        self.assertEqual(payload["jam_sample_count"], 177)
        self.assertLess(payload["jam_sample_count"], calib.MIN_JAM_SAMPLES)

    @unittest.skipUnless(STORAGE.is_file(), "기존 저장용량 산출물 없음")
    def test_current_artifact_has_no_confidence_interval(self) -> None:
        import json

        payload = json.loads(self.STORAGE.read_text(encoding="utf-8"))
        self.assertNotIn("jam_density_ci95_low", payload)


if __name__ == "__main__":
    unittest.main()
