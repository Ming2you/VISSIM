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

    모델    C = p1 + p2 + lost_time                       (당시 lost_time = 8)
    플랜트  C = minor + major + 2 x (AMBER + ALL_RED)      (당시 = 10)

`major/minor` 는 어댑터가 `p2/p1` 을 그대로 실은 값이므로 차이는 `8 대 10` 뿐이었다.

## N4-0 작업3 이후 — 지금 이 파일이 무엇을 말하고 있는가

러너 clearance 를 실 `.sig` 에 맞췄다(`ALL_RED_SEC` 2 -> 0, 전이당 5 s -> 3 s). 근거는
`NativeClearanceTests` 가 실 프로그램 15개에서 직접 잰다. 그래서 플랜트 lost_time 은
2 x 3 = **6.0** 이 됐는데 생산 config 의 `network.lost_time` 은 아직 **10.0** 이다.

    플랜트  C = p1 + p2 + 6      (지시 57/57 이면 120)
    모델    C = 120,  lost_time 10,  effective 110,  green_min 20,  green_max 90

`ProductionCycleIdentityTests` 와 `GeneratorGreenBudgetContractTests` 는 그 4 s 를 지금
**빨간불로** 들고 있다. 이 파일의 존재 이유가 그 어긋남을 소리내는 것이므로 단언을
느슨하게 하지 않는다. 닫는 길은 둘뿐이고 둘 다 모델 쪽 결정이다.

  (a) 2현시를 유지한 채 모델 주기를 116 으로 내린다 — 녹색 예산(110)과 상자
      [20, 90] 이 그대로라 리더 행동은 비트동일하고 분모만 정확해진다. 다만
      `green_budget_contract` 가 `cycle_length` 를 부모에서 **읽고** `green_max` 를
      유도하는 구조라, 유도 방향을 뒤집어야 한다(그대로 두면 green_max 가 94 가 되고
      쓰기 클램프 90 에 물려 주기가 다시 어긋난다).
  (b) 목표 스펙대로 4현시로 간다 — lost_time 4 x 3 = 12, 주기 150, green_max 78.
      러너의 주기 식이 clearance 를 **두 번**만 더하므로(축이 둘이다) 이쪽은 러너
      주기 식 자체를 4전이로 바꿔야 성립한다. 지금 그대로는 지시 녹색 합 138 에
      대해 러너가 합성하는 주기는 150 이 아니라 **144** 다.
"""

from __future__ import annotations

import json
import sys
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
# 제어 15 SC 의 정본 목록. `.sig` 선택은 여기서 나온 SC 번호 + inpx supplyFile2 다.
CONTROL_MAPPING = (
    WORKSPACE_ROOT
    / "evaluation"
    / "real_world_modi_control_distributed_20260728"
    / "control_mapping_distributed_core15n41_20260805.json"
)

# 실 캡처가 낸 축 녹색. evaluation/runs/capture_n41_20260805/
# decisions_capture_n41_c00_seed13/action_*.json 51개 x 15 SC 전부 (57.0, 57.0) 이다.
CAPTURED_GREEN_P1_P2 = (57.0, 57.0)


# 승격 후보. 생산과 같은 생성기가 같은 인자 계열로 만든 산출물이라, 계약이 생성기에
# 실려 있지 않으면 여기서만 깨진다(생산은 a1e73da 가 손으로 넣어 뒀다).
PROMOTION_CANDIDATES = (
    WORKSPACE_ROOT / "evaluation" / "configs"
    / "real_world_modi_pstack_distributed_core15n41gated_20260811.json",
    WORKSPACE_ROOT / "evaluation" / "configs"
    / "real_world_modi_pstack_distributed_core15n41ungated_20260811.json",
)


def _config_from_tuning(tuning_path: Path):
    """실 런 스크립트가 쓰는 것과 같은 경로로 cfg 를 만든다.

    scripts/run_real_world_single_watchdog_distributed_*.ps1 의 $Tuning /
    $Calibration 을 그대로 쓴다.
    """
    from evaluation.controllers import vissim_stackelberg_adapter as adapter

    tuning = adapter.load_optional_json(str(tuning_path))
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


def _production_config():
    return _config_from_tuning(TUNING)


class RunnerConstantsTests(unittest.TestCase):
    """상수를 복사하지 않고 러너 원문에서 읽는다."""

    def test_clearance_constants_come_from_the_runner_source(self) -> None:
        from evaluation.controllers import plant_cycle

        self.assertEqual(plant_cycle.runner_clearance_sec(), (3.0, 0.0))
        self.assertEqual(plant_cycle.plant_lost_time_sec(), 6.0)

    def test_a_runner_without_the_constant_is_an_error_not_a_default(self) -> None:
        import tempfile

        from evaluation.controllers import plant_cycle

        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "no_consts.vbs"
            fake.write_text("Const RAMP_CYCLE_SEC = 10\n", encoding="utf-8")
            with self.assertRaises(plant_cycle.RunnerConstantMissing):
                plant_cycle.plant_lost_time_sec(fake)


class PlantCycleFormulaTests(unittest.TestCase):
    """러너 :769 의 식을 그대로 옮겼는지."""

    def test_cycle_is_the_two_axis_greens_plus_two_clearances(self) -> None:
        from evaluation.controllers import plant_cycle

        self.assertEqual(plant_cycle.plant_cycle_sec(50.0, 60.0), 116.0)
        self.assertEqual(plant_cycle.plant_cycle_sec(*CAPTURED_GREEN_P1_P2), 120.0)

    def test_the_two_axis_formula_cannot_reach_the_target_cycle(self) -> None:
        """목표 150 은 clearance 를 고쳐도 2현시 식으로는 안 나온다.

        유효녹색 138 을 두 축에 실으면 러너는 138 + 2 x 3 = 144 를 합성한다. 150 은
        전이가 **넷** 이어야 나오는 값이다(138 + 4 x 3). 게다가 두 축으로 138 을 나누면
        한 축은 최소 69 s 인데, 상자 끝(green_min 20 을 준 반대편)은 118 s 라 러너의
        쓰기 계약 `SignalActionValuesValid` 의 상한 90 을 넘는다.
        """
        from evaluation.controllers import plant_cycle

        target_effective_green = 138.0
        self.assertEqual(
            plant_cycle.plant_cycle_sec(
                target_effective_green / 2.0, target_effective_green / 2.0
            ),
            144.0,
        )
        _, clamp_high = plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC
        self.assertGreater(target_effective_green - 20.0, clamp_high)

    def test_the_write_clamp_shortens_the_plant_cycle(self) -> None:
        """모델이 92 s 를 지시해도 어댑터는 90 s 만 싣는다 - 주기가 2 s 짧아진다."""
        from evaluation.controllers import plant_cycle

        low, high = plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC
        self.assertEqual(plant_cycle.written_axis_green_sec(92.0), high)
        self.assertEqual(plant_cycle.written_axis_green_sec(2.0), low)
        self.assertEqual(plant_cycle.plant_cycle_sec(20.0, 92.0), 116.0)

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
        # N4-0. 현시 4값은 한 자리(현시 루프)에서 클램프된다. 개수를 세는 대신 실제로
        # 실리는 값을 재서, 어느 현시로 들어와도 클램프가 물리는지 본다.
        self.assertGreaterEqual(source.count("plant_cycle.written_axis_green_sec"), 1)
        self.assertNotIn("), 5.0, 90.0)", source)

        import csv
        import json
        import tempfile
        import types
        from pathlib import Path

        from evaluation.controllers import action_csv_schema, signal_group_plan

        plan_path = WORKSPACE_ROOT / "outputs" / "signal_group_actuation_plan_v3.json"
        if not plan_path.is_file():
            self.skipTest("actuation plan artifact is not built")
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        low, high = plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC
        # 계획이 실제로 구동하는 현시에만 녹색을 준다(그 밖은 어댑터가 fail-closed 로 죽는다).
        live = adapter.plan_live_phases(plan, 1001)
        self.assertEqual(live, ("p1", "p2"))
        for phase, raw, expected in (
            (live[0], high + 50.0, high),
            (live[0], low / 2.0, low),
            (live[1], high + 50.0, high),
            (live[1], low / 2.0, low),
        ):
            with self.subTest(phase=phase, raw=raw):
                control = types.SimpleNamespace(
                    green_times={f"SC1001_{name}": 40.0 for name in live},
                    offsets={},
                    ramp_metering={},
                    diagnostics={},
                )
                control.green_times[f"SC1001_{phase}"] = raw
                cfg = types.SimpleNamespace(
                    network=types.SimpleNamespace(ramp_capacity_veh_h={}),
                    freeway_follower=types.SimpleNamespace(vsl_set=[80.0]),
                )
                mapping = {
                    "segments": [],
                    "signals": [
                        {"id": "SC1001", "sc_no": 1001, "major_maps_to": "p1"}
                    ],
                }
                with tempfile.TemporaryDirectory() as tmp:
                    out = Path(tmp) / "action.csv"
                    adapter.write_action_csv(
                        out, control, cfg, mapping,
                        lambda control_arg, link, index, cfg_arg: 80.0,
                        {"controller_status": "ok"}, {},
                        signal_group_plan_table=plan,
                    )
                    with out.open(encoding="utf-8") as handle:
                        rows = list(csv.DictReader(handle))
                signal_row = next(row for row in rows if row["kind"] == "signal")
                written = action_csv_schema.phase_greens(signal_row)
                self.assertEqual(written[phase], expected)
                # 클램프가 걸린 뒤에도 계획 주기와 러너 주기가 같은 식에서 나와야 한다.
                sg_row = next(row for row in rows if row["kind"] == "signal_sg")
                self.assertAlmostEqual(
                    float(sg_row["green_sec"]),
                    signal_group_plan.plan_cycle_sec(
                        written, *plant_cycle.runner_clearance_sec()
                    ),
                    places=6,
                )


class NativeClearanceTests(unittest.TestCase):
    """러너 clearance 는 **실 프로그램의** clearance 여야 한다 (N4-0 작업3).

    러너는 제어 15 SC 의 SG 를 전부 `ContrByCOM` 으로 바꿔 inpx 프로그램을 우회하므로,
    clearance 는 러너가 고르는 값이다. 그렇다고 아무 값이나 되는 것은 아니다 - 현장
    프로그램이 쓰는 값과 다르면 플랜트는 실망을 재생하지 않는다.

    합성 픽스처가 아니라 inpx `supplyFile2` + `progNo` 가 고르는 **실 `.sig` 15개**
    (SG 136개)를 직접 잰다. `scripts/survey_signal_programs` 와 같은 선택 경로다.
    """

    @classmethod
    def setUpClass(cls) -> None:
        import sys

        if str(WORKSPACE_ROOT) not in sys.path:
            sys.path.insert(0, str(WORKSPACE_ROOT))
        from scripts import survey_signal_programs

        if not survey_signal_programs.DEFAULT_NETWORK.is_file():
            raise unittest.SkipTest("run network is unavailable")
        cls.table = survey_signal_programs.survey(
            survey_signal_programs.DEFAULT_NETWORK, CONTROL_MAPPING
        )

    @staticmethod
    def _union_sec(spans) -> float:
        merged: list[list[float]] = []
        for start, end in sorted(tuple(span) for span in spans):
            if end <= start:
                continue
            if merged and start <= merged[-1][1] + 1e-9:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        return sum(end - start for start, end in merged)

    def test_the_survey_really_covers_the_fifteen_controlled_programs(self) -> None:
        """이 검사가 무엇을 재고 있는지부터 못박는다 - 15 SC · 136 SG 다."""
        self.assertEqual(self.table["counts"]["controllers"], 15)
        self.assertEqual(self.table["counts"]["signal_groups"], 136)

    def test_every_native_amber_is_exactly_the_runner_amber(self) -> None:
        from evaluation.controllers import plant_cycle

        amber_sec, _ = plant_cycle.runner_clearance_sec()
        durations = {
            round(end - start, 6)
            for row in self.table["controllers"]
            for group in row["signal_groups"]
            for start, end in group["amber_windows"]
        }
        self.assertEqual(durations, {amber_sec})

    def test_no_native_program_holds_any_all_red(self) -> None:
        """녹색과 황색의 합집합이 주기를 빈틈없이 덮으면 all-red 는 0 이다.

        전 SG 이 동시에 적색인 순간이 한 번이라도 있으면 그 구멍만큼 합집합이 짧아진다.
        """
        for row in self.table["controllers"]:
            with self.subTest(sc=row["sc_no"]):
                covered = self._union_sec(
                    tuple(window)
                    for group in row["signal_groups"]
                    for key in ("green_windows", "amber_windows")
                    for window in group[key]
                )
                self.assertAlmostEqual(covered, float(row["cycle_sec"]), places=6)

    def test_the_runner_clearance_equals_the_native_clearance(self) -> None:
        """본체. 러너 상수가 실 프로그램에서 잰 값과 같아야 한다.

        `ALL_RED_SEC` 를 2 로 되돌리면 여기가 깨진다 - 실 `.sig` 에는 all-red 가 없다.
        """
        from evaluation.controllers import plant_cycle

        native_amber = {
            round(end - start, 6)
            for row in self.table["controllers"]
            for group in row["signal_groups"]
            for start, end in group["amber_windows"]
        }
        self.assertEqual(len(native_amber), 1, native_amber)
        self.assertEqual(
            plant_cycle.runner_clearance_sec(), (native_amber.pop(), 0.0)
        )


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


class GreenBudgetContractTests(unittest.TestCase):
    """`lost_time` 을 10 으로 옮겼으면 상자 상한도 같이 따라와야 한다.

    다섯 값의 계약은 `plant_cycle` 모듈 docstring 에 한 번만 적혀 있다. 자유 파라미터는
    `cycle_length`, `lost_time`, `green_min` 셋이고 `effective_green_total` 과
    `green_max` 는 유도값이다. 여기서는 **생산 config** 가 그 계약을 지키는지만 본다.

    이 검사가 없으면 `lost_time` 만 바꿔도 아무것도 깨지지 않는다 — 사영이 상자를
    조용히 되돌려 놓기 때문이다(`distributed_coordinator._bounded_leader_green`).
    깨지는 것은 숫자가 아니라 **상한의 의미**다.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.net = _production_config().network

    def test_the_two_box_ends_sum_to_the_budget(self) -> None:
        from evaluation.controllers import plant_cycle

        net = self.net
        self.assertEqual(
            plant_cycle.green_box_residual_sec(net),
            0.0,
            f"green_min({net.green_min}) + green_max({net.green_max}) 는 "
            f"effective_green_total({net.effective_green_total}) 이어야 한다 — "
            f"green_max 는 {net.effective_green_total - net.green_min} 이어야 한다",
        )

    def test_the_upper_bound_is_a_green_the_leader_can_actually_reach(self) -> None:
        """죽은 상한은 산수가 아니라 도달 가능성의 문제다.

        사영을 거친 리더 상자에서 어떤 현시도 `green_max` 에 닿지 못하면 그 값은
        설정에만 있는 숫자다.
        """
        from evaluation.controllers import plant_cycle

        net = self.net
        reached = max(
            max(p1, p2) for p1, p2 in plant_cycle.leader_green_box(net)
        )
        self.assertEqual(reached, float(net.green_max))


class GeneratorGreenBudgetContractTests(unittest.TestCase):
    """계약이 **생성기** 에 실려 있는지. 생산 config 한 건만 보면 안 보인다.

    a1e73da 는 `lost_time` / `green_max` 를 생산 config **파일에 손으로** 넣었다.
    `scripts/generate_real_world_distributed_players.py` 는 두 키를 쓰지 않으므로
    새로 만든 config 에는 아예 없고, 그러면 값이 NumSim `NetworkConfig` 기본값
    (`lost_time=8.0`, `green_max=92.0`)으로 되돌아간다. 러너 clearance 와 다른 값이면
    그만큼 모델 주기가 플랜트 주기와 어긋난다(N4-0 작업3 이후 러너는 2 x 3 = 6.0).

    숫자로는 아무것도 안 깨진다 — 기본값 자신은 `20 + 92 == 120 - 8` 로 예산 항등식을
    만족하기 때문이다. 깨지는 것은 **플랜트와의 주기 동일성** 이다.
    """

    @classmethod
    def setUpClass(cls) -> None:
        import importlib.util

        path = (
            WORKSPACE_ROOT / "scripts" / "generate_real_world_distributed_players.py"
        )
        spec = importlib.util.spec_from_file_location(
            "generate_real_world_distributed_players", path
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        cls.gen = module

    def test_every_promotion_candidate_keeps_the_plant_cycle_identity(self) -> None:
        """실 산출물 검사 — 후보 config 를 실 런과 같은 경로로 세워서 본다."""
        from evaluation.controllers import plant_cycle

        for path in PROMOTION_CANDIDATES:
            with self.subTest(config=path.name):
                net = _config_from_tuning(path).network
                self.assertEqual(
                    float(net.lost_time),
                    plant_cycle.plant_lost_time_sec(),
                    f"{path.name}: lost_time 이 러너 clearance 와 다르다",
                )
                self.assertEqual(
                    plant_cycle.green_box_residual_sec(net),
                    0.0,
                    f"{path.name}: green_min({net.green_min}) + green_max({net.green_max}) "
                    f"!= effective_green_total({net.effective_green_total})",
                )
                self.assertEqual(
                    plant_cycle.cycle_disagreement_sec(net),
                    0.0,
                    f"{path.name}: 리더 상자 어딘가에서 플랜트 주기가 모델 주기와 다르다",
                )

    def test_the_generator_writes_the_two_derived_keys_into_every_config(self) -> None:
        """생성기 함수 자체 — network_override 내용과 무관하게 두 키가 실려야 한다.

        후보 두 건은 같은 인자 계열로 만들었으니 실 산출물 검사만으로도 걸리지만,
        슬러그·선택자가 다른 다음 config 는 여기서만 걸린다.
        """
        from evaluation.controllers import plant_cycle

        gen = self.gen
        tuning = gen.build_tuning_config(
            {"signals": []},
            WORKSPACE_ROOT / "evaluation" / "m.json",
            WORKSPACE_ROOT / "evaluation" / "d.json",
            "core15", "slugtest", [], "29991231",
        )
        network = tuning["config_overrides"]["network"]
        self.assertIn("lost_time", network)
        self.assertIn("green_max", network)
        # 값은 그 config **자신의** 부모 체인에 묶여야 한다. 다른 부모의 값을 베껴
        # 오면(또는 리터럴이면) 부모를 바꿔도 안 따라온다.
        contract = gen.green_budget_contract(gen.CONFIG_DIR / tuning["extends"])
        self.assertEqual(network["lost_time"], plant_cycle.plant_lost_time_sec())
        self.assertEqual(network["green_max"], contract["green_max"])

    def test_green_max_follows_the_parent_chain_not_a_literal(self) -> None:
        """되돌림 증명 — 유도를 리터럴로 바꾸면 이 검사가 깨진다.

        부모가 `green_min` 을 5 s 올리면 `green_max` 는 5 s 내려가야 한다. 생성기가
        90.0 을 박아두면 두 부모가 같은 값을 내서 두 번째 단언이 실패한다.
        """
        import tempfile

        gen = self.gen
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "parent.json"
            parent.write_text(
                json.dumps({"config_overrides": {"network": {"green_min": 25.0}}}),
                encoding="utf-8",
            )
            shifted = gen.green_budget_contract(parent)
        baseline = gen.green_budget_contract(gen.CONFIG_DIR / gen.PARENT_CONFIG)
        self.assertEqual(shifted["lost_time"], baseline["lost_time"])
        self.assertEqual(shifted["green_max"], baseline["green_max"] - 5.0)


if __name__ == "__main__":
    unittest.main()
