# v3 N4-5 잔여 - 모델 주기와 러너가 합성하는 주기가 실제로 같은지 고정한다
"""주기 분모 3중 불일치 중 **모델 대 플랜트** 를 닫는다.

## 왜 native 주기를 채우는 것이 답이 아닌가

`NetworkConfig.cycle_length_by_signal` 을 실측 native 주기(140/150/160/170)로 채우자는
것이 원안이었다. 그런데 제어 런에서 native 프로그램은 **재생되지 않는다**. 러너는
제어 15 SC 의 모든 SG 에 `ContrByCOM = True` 를 걸어(:1402) inpx 프로그램을 우회하고,
매초 `major + amber + all_red + minor + amber + all_red` 로 합성한 주기를 COM 으로 밀어
넣는다(:764, :1442). native 주기를 채우면 모델은 **플랜트가 한 번도 돌리지 않는 주기**로
예측하게 된다.

## 실제 간극은 상수 하나다

모델은 `cycle_length == p1 + p2 + lost_time` 을 이미 항등식으로 갖고 있다
(`src/evaluation/metrics.py:242` 가 위반을 카운트한다). 플랜트 식과 나란히 두면

    모델    C = p1 + p2 + lost_time                       (lost_time = 8)
    플랜트  C = minor + major + 2 x (AMBER + ALL_RED)      (= 10)

`major/minor` 는 어댑터가 `p2/p1` 을 그대로 실은 값이므로 차이는 `8 대 10` 뿐이다.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
TUNING = (
    WORKSPACE_ROOT
    / "evaluation"
    / "configs"
    / "real_world_modi_pstack_distributed_core15n41_20260805.json"
)
CALIBRATION = (
    WORKSPACE_ROOT
    / "evaluation"
    / "calibration"
    / "real_world_prediction_calibration_pshb4500fix_20260724.json"
)
VENDOR_NUMSIM = WORKSPACE_ROOT / "vendor" / "NumSim-mine"

# 실 캡처가 낸 축 녹색. evaluation/runs/capture_n41_20260805/
# decisions_capture_n41_c00_seed13/action_*.json 51개 x 15 SC 전부 (57.0, 57.0) 이다.
CAPTURED_GREEN_P1_P2 = (57.0, 57.0)


def _production_config():
    """실 런 스크립트가 쓰는 것과 같은 경로로 생산 cfg 를 만든다.

    scripts/run_real_world_single_watchdog_distributed_core15n41.ps1 의 $Tuning /
    $Calibration 을 그대로 쓴다.
    """
    from evaluation.controllers import vissim_stackelberg_adapter as adapter

    tuning = adapter.load_optional_json(str(TUNING))
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    return adapter.build_config(
        VENDOR_NUMSIM,
        control_interval=60.0,
        sim_period=3600.0,
        mode="real-world",
        calibration=calibration,
        tuning=tuning,
        local_observation=True,
        flagship=True,
    )


class RunnerConstantsTests(unittest.TestCase):
    """상수를 복사하지 않고 러너 원문에서 읽는다."""

    def test_clearance_constants_come_from_the_runner_source(self) -> None:
        from evaluation.controllers import plant_cycle

        self.assertEqual(plant_cycle.runner_clearance_sec(), (3.0, 2.0))
        self.assertEqual(plant_cycle.plant_lost_time_sec(), 10.0)

    def test_a_runner_without_the_constant_is_an_error_not_a_default(self) -> None:
        import tempfile

        from evaluation.controllers import plant_cycle

        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "no_consts.vbs"
            fake.write_text("Const RAMP_CYCLE_SEC = 10\n", encoding="utf-8")
            with self.assertRaises(plant_cycle.RunnerConstantMissing):
                plant_cycle.plant_lost_time_sec(fake)


class PlantCycleFormulaTests(unittest.TestCase):
    """러너 :764 의 식을 그대로 옮겼는지."""

    def test_cycle_is_the_two_axis_greens_plus_two_clearances(self) -> None:
        from evaluation.controllers import plant_cycle

        self.assertEqual(plant_cycle.plant_cycle_sec(50.0, 60.0), 120.0)
        self.assertEqual(plant_cycle.plant_cycle_sec(*CAPTURED_GREEN_P1_P2), 124.0)

    def test_the_write_clamp_shortens_the_plant_cycle(self) -> None:
        """모델이 92 s 를 지시해도 어댑터는 90 s 만 싣는다 - 주기가 2 s 짧아진다."""
        from evaluation.controllers import plant_cycle

        low, high = plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC
        self.assertEqual(plant_cycle.written_axis_green_sec(92.0), high)
        self.assertEqual(plant_cycle.written_axis_green_sec(2.0), low)
        self.assertEqual(plant_cycle.plant_cycle_sec(20.0, 92.0), 120.0)

    def test_the_adapter_writer_uses_this_clamp_not_its_own_literals(self) -> None:
        """되돌림 증명 - 어댑터가 5.0/90.0 리터럴로 돌아가면 이 단언이 깨진다.

        클램프가 두 곳에 복사돼 있으면 여기 테스트는 통과하는데 실제로 실리는 값은
        다를 수 있다. 한 곳에서만 나오게 묶는다.
        """
        from evaluation.controllers import plant_cycle
        from evaluation.controllers import vissim_stackelberg_adapter as adapter

        self.assertIs(
            adapter.plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC,
            plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC,
        )
        source = (
            WORKSPACE_ROOT
            / "evaluation"
            / "controllers"
            / "vissim_stackelberg_adapter.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(source.count("plant_cycle.written_axis_green_sec"), 2)
        self.assertNotIn("), 5.0, 90.0)", source)


class ProductionCycleIdentityTests(unittest.TestCase):
    """본체 - 생산 config 에서 두 주기가 **정확히** 같아야 한다."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.net = _production_config().network

    def test_the_model_lost_time_equals_the_runner_clearance(self) -> None:
        from evaluation.controllers import plant_cycle

        self.assertEqual(float(self.net.lost_time), plant_cycle.plant_lost_time_sec())

    def test_every_reachable_leader_action_reproduces_the_model_cycle(self) -> None:
        from evaluation.controllers import plant_cycle

        self.assertEqual(plant_cycle.cycle_disagreement_sec(self.net), 0.0)

    def test_the_model_no_longer_overestimates_the_green_fraction(self) -> None:
        from evaluation.controllers import plant_cycle

        self.assertEqual(plant_cycle.green_fraction_overestimate(self.net), 0.0)

    def test_the_write_clamp_never_binds_on_the_leader_box(self) -> None:
        """클램프가 물면 모델이 지시한 녹색이 플랜트에서 그대로 재생되지 않는다."""
        from evaluation.controllers import plant_cycle

        low, high = plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC
        for p1, p2 in plant_cycle.leader_green_box(self.net):
            for green in (p1, p2):
                self.assertGreaterEqual(green, low, (p1, p2))
                self.assertLessEqual(green, high, (p1, p2))

    def test_the_green_budget_still_fills_the_cycle_exactly(self) -> None:
        """모델 자신의 항등식(metrics.py:242)이 깨지지 않았는지."""
        self.assertEqual(
            float(self.net.effective_green_total) + float(self.net.lost_time),
            float(self.net.cycle_length),
        )

    def test_the_native_cycle_mapping_stays_empty(self) -> None:
        """native 주기는 제어 런에서 재생되지 않는다 - 채우면 안 된다."""
        self.assertEqual(self.net.cycle_length_by_signal, {})


if __name__ == "__main__":
    unittest.main()
