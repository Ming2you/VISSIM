# v3 N4-5 - SG 단위 액추에이션 계획(축 녹색창의 native 분할)을 고정한다
"""N4-5 의 핵심 계약을 고정한다.

러너는 지금 축(major/minor) 전체를 그 축의 모든 SG 에 그대로 준다. 모델은 N4-3 이후
축 녹색에 native 배분(share)을 곱해 예측한다. 이 모듈이 그 배분을 **플랜트 쪽에서**
같은 값으로 재현하는지를 본다.

    plant SG g 의 녹색 = 지시된 축 녹색 x union_green(g) / union_green(축)
    model movement m 의 녹색 = 지시된 축 녹색 x union_green(m 의 SG) / union_green(축)

두 식의 우변이 같은 정의여야 비대칭이 닫힌다.
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from evaluation.controllers import native_phase_green
from evaluation.controllers import signal_group_plan


@dataclass(frozen=True)
class FakeInterval:
    state: str
    start_sec: float
    end_sec: float


@dataclass(frozen=True)
class FakeTimeline:
    name: str
    intervals: tuple
    permanent_red: bool = False


@dataclass(frozen=True)
class FakeProgram:
    controller_id: str
    cycle_length_sec: float
    program_offset_sec: float
    sg_timelines: dict


def green(*spans: tuple[float, float]) -> tuple:
    return tuple(FakeInterval("GREEN", start, end) for start, end in spans)


def program(
    cycle: float, spans: dict[str, tuple], permanent_red: tuple[str, ...] = ()
) -> FakeProgram:
    return FakeProgram(
        controller_id="SCX",
        cycle_length_sec=cycle,
        program_offset_sec=0.0,
        sg_timelines={
            sg_id: FakeTimeline(
                name=f"SG{sg_id}",
                intervals=green(*value),
                permanent_red=sg_id in permanent_red,
            )
            for sg_id, value in spans.items()
        },
    )


def axis_windows(plan, major_green, minor_green, major_maps_to, amber_sec, all_red_sec):
    """축 2값 호출을 현시 매핑으로 옮긴 이 파일 전용 어댑터 (N4-0).

    이 파일의 픽스처는 두 현시만 쓴다. 축 -> 현시 대응만 바꾸고 나머지 현시는 녹색 0 이라
    주기에서 자리를 차지하지 않으므로 v3 배치와 값이 같다. 스키마 자체는
    `tests/test_action_csv_contract` / `tests/test_action_csv_signal_group_rows` 가 잰다.
    """
    major_phase = str(major_maps_to)
    minor_phase = "p1" if major_phase == "p2" else "p2"
    greens = {phase: 0.0 for phase in signal_group_plan.MODEL_PHASES}
    greens[major_phase] = float(major_green)
    greens[minor_phase] = float(minor_green)
    return signal_group_plan.plan_windows(
        plan,
        phase_greens=greens,
        phase_order=signal_group_plan.phase_layout_order(major_phase),
        amber_sec=amber_sec,
        all_red_sec=all_red_sec,
    )


class PermanentRedPhaseTests(unittest.TestCase):
    """SC107·108·109 - 한 현시의 SG 가 `.sig` 에서 영구적색이라 네이티브 녹색이 0 이다.

    실측(`outputs/live_signal_cycle_probe_n4dr150_20260812.json`)에서 15 SC 중 그 셋만
    현시가 3 이었다. 모델의 어휘는 4현시이므로 계획은 남는 현시를 **녹색 0 으로 실어야**
    한다. 거부하면 그 셋은 계획 자체가 안 만들어진다.

    가드를 없애는 게 아니다. `.sig` 가 영구적색이라고 선언한 SG 일 때만 허용한다.
    """

    def test_a_phase_whose_groups_are_all_permanently_red_takes_zero_green(self) -> None:
        prog = program(
            100.0,
            {"1": ((0.0, 30.0),), "2": ((40.0, 50.0),), "9": ()},
            permanent_red=("9",),
        )
        plan = signal_group_plan.build_node_plan(
            node_id="SC107",
            program=prog,
            phase_signal_groups={"p1": ["9"], "p2": ["1"], "p3": ["2"], "p4": []},
            signal_group_ids=["1", "2", "9"],
        )
        self.assertEqual(0.0, plan.axis_green_sec["p1"])
        self.assertEqual((), plan.phase_segments["p1"])
        # 나머지 현시는 그대로 살아 있어야 한다.
        self.assertEqual(30.0, plan.axis_green_sec["p2"])
        self.assertEqual(10.0, plan.axis_green_sec["p3"])

    def test_a_dark_group_that_is_not_declared_permanently_red_still_raises(self) -> None:
        """되돌림 증명의 반대편 - 선언 없이 녹색만 없으면 여전히 죽는다.

        이게 없으면 매핑이 틀려 엉뚱한 SG 가 붙은 현시도 조용히 0 이 된다.
        """
        prog = program(100.0, {"1": ((0.0, 30.0),), "9": ()})
        with self.assertRaises(signal_group_plan.SignalGroupPlanError):
            signal_group_plan.build_node_plan(
                node_id="SC107",
                program=prog,
                phase_signal_groups={"p1": ["9"], "p2": ["1"], "p3": [], "p4": []},
                signal_group_ids=["1", "9"],
            )


class BuildNodePlanTests(unittest.TestCase):
    def test_axis_window_is_split_by_native_green_share(self) -> None:
        prog = program(100.0, {"1": ((0.0, 30.0),), "2": ((40.0, 50.0),)})
        plan = signal_group_plan.build_node_plan(
            node_id="SC1",
            program=prog,
            phase_signal_groups={"p2": ["1", "2"], "p1": []},
            signal_group_ids=["1", "2"],
        )
        # 축 union green = 40 s. SG1 은 30/40, SG2 는 10/40.
        rows = axis_windows(
            plan, major_green=40.0, minor_green=20.0, major_maps_to="p2",
            amber_sec=3.0, all_red_sec=2.0,
        )
        by_sg = {row.sg_no: (row.start_sec, row.end_sec) for row in rows}
        self.assertEqual(by_sg["1"], (0.0, 30.0))
        self.assertEqual(by_sg["2"], (30.0, 40.0))

    def test_minor_axis_window_starts_after_major_clearance(self) -> None:
        prog = program(100.0, {"1": ((0.0, 30.0),), "3": ((60.0, 90.0),)})
        plan = signal_group_plan.build_node_plan(
            node_id="SC1",
            program=prog,
            phase_signal_groups={"p2": ["1"], "p1": ["3"]},
            signal_group_ids=["1", "3"],
        )
        rows = axis_windows(
            plan, major_green=40.0, minor_green=20.0, major_maps_to="p2",
            amber_sec=3.0, all_red_sec=2.0,
        )
        by_sg = {row.sg_no: (row.start_sec, row.end_sec) for row in rows}
        self.assertEqual(by_sg["1"], (0.0, 40.0))
        self.assertEqual(by_sg["3"], (45.0, 65.0))
        self.assertEqual(
            signal_group_plan.plan_cycle_sec(
                {"p1": 20.0, "p2": 40.0, "p3": 0.0, "p4": 0.0}, 3.0, 2.0
            ),
            70.0,
        )

    def test_major_maps_to_p1_sends_p1_groups_to_the_major_window(self) -> None:
        prog = program(100.0, {"1": ((0.0, 30.0),), "3": ((60.0, 90.0),)})
        plan = signal_group_plan.build_node_plan(
            node_id="SC1001",
            program=prog,
            phase_signal_groups={"p2": ["1"], "p1": ["3"]},
            signal_group_ids=["1", "3"],
        )
        rows = axis_windows(
            plan, major_green=40.0, minor_green=20.0, major_maps_to="p1",
            amber_sec=3.0, all_red_sec=2.0,
        )
        by_sg = {row.sg_no: (row.start_sec, row.end_sec) for row in rows}
        self.assertEqual(by_sg["3"], (0.0, 40.0))
        self.assertEqual(by_sg["1"], (45.0, 65.0))

    def test_natively_overlapping_groups_stay_overlapping(self) -> None:
        prog = program(100.0, {"1": ((0.0, 30.0),), "2": ((0.0, 30.0),), "3": ((60.0, 90.0),)})
        plan = signal_group_plan.build_node_plan(
            node_id="SC1",
            program=prog,
            phase_signal_groups={"p2": ["1", "2"], "p1": ["3"]},
            signal_group_ids=["1", "2", "3"],
        )
        rows = axis_windows(
            plan, major_green=40.0, minor_green=20.0, major_maps_to="p2",
            amber_sec=3.0, all_red_sec=2.0,
        )
        by_sg = {row.sg_no: (row.start_sec, row.end_sec) for row in rows}
        self.assertEqual(by_sg["1"], by_sg["2"])
        self.assertEqual(by_sg["1"], (0.0, 40.0))

    def test_group_without_native_green_gets_no_window(self) -> None:
        prog = program(100.0, {"1": ((0.0, 30.0),), "2": (), "3": ((60.0, 90.0),)})
        plan = signal_group_plan.build_node_plan(
            node_id="SC1",
            program=prog,
            phase_signal_groups={"p2": ["1", "2"], "p1": ["3"]},
            signal_group_ids=["1", "2", "3"],
        )
        self.assertEqual(plan.window_counts["2"], 0)
        rows = axis_windows(
            plan, major_green=40.0, minor_green=20.0, major_maps_to="p2",
            amber_sec=3.0, all_red_sec=2.0,
        )
        self.assertNotIn("2", {row.sg_no for row in rows})

    def test_axis_without_native_green_is_rejected(self) -> None:
        prog = program(100.0, {"1": (), "3": ((60.0, 90.0),)})
        with self.assertRaises(signal_group_plan.SignalGroupPlanError):
            signal_group_plan.build_node_plan(
                node_id="SC1",
                program=prog,
                phase_signal_groups={"p2": ["1"], "p1": ["3"]},
                signal_group_ids=["1", "3"],
            )

    def test_group_outside_both_phases_is_declared_red_only(self) -> None:
        prog = program(100.0, {"1": ((0.0, 30.0),), "3": ((60.0, 90.0),), "9": ((10.0, 20.0),)})
        plan = signal_group_plan.build_node_plan(
            node_id="SC1",
            program=prog,
            phase_signal_groups={"p2": ["1"], "p1": ["3"]},
            signal_group_ids=["1", "3", "9"],
        )
        self.assertEqual(plan.red_only_signal_groups, ("9",))
        rows = axis_windows(
            plan, major_green=40.0, minor_green=20.0, major_maps_to="p2",
            amber_sec=3.0, all_red_sec=2.0,
        )
        self.assertNotIn("9", {row.sg_no for row in rows})


class ConflictTests(unittest.TestCase):
    def test_natively_disjoint_pair_is_a_conflict_and_plan_never_co_greens_it(self) -> None:
        prog = program(100.0, {"1": ((0.0, 30.0),), "2": ((40.0, 50.0),), "3": ((60.0, 90.0),)})
        plan = signal_group_plan.build_node_plan(
            node_id="SC1",
            program=prog,
            phase_signal_groups={"p2": ["1", "2"], "p1": ["3"]},
            signal_group_ids=["1", "2", "3"],
        )
        self.assertIn(("1", "2"), plan.conflict_pairs)
        self.assertIn(("1", "3"), plan.conflict_pairs)
        rows = axis_windows(
            plan, major_green=40.0, minor_green=20.0, major_maps_to="p2",
            amber_sec=3.0, all_red_sec=2.0,
        )
        self.assertEqual(signal_group_plan.conflict_violations(rows, plan.conflict_pairs), ())

    def test_overlapping_pair_is_not_a_conflict(self) -> None:
        prog = program(100.0, {"1": ((0.0, 30.0),), "2": ((10.0, 30.0),), "3": ((60.0, 90.0),)})
        plan = signal_group_plan.build_node_plan(
            node_id="SC1",
            program=prog,
            phase_signal_groups={"p2": ["1", "2"], "p1": ["3"]},
            signal_group_ids=["1", "2", "3"],
        )
        self.assertNotIn(("1", "2"), plan.conflict_pairs)

    def test_hand_built_co_green_of_a_conflicting_pair_is_reported(self) -> None:
        rows = (
            signal_group_plan.PlanWindow(sg_no="1", window_index=0, start_sec=0.0, end_sec=20.0),
            signal_group_plan.PlanWindow(sg_no="2", window_index=0, start_sec=10.0, end_sec=30.0),
        )
        violations = signal_group_plan.conflict_violations(rows, (("1", "2"),))
        self.assertEqual(len(violations), 1)
        self.assertIn("1", violations[0])
        self.assertIn("2", violations[0])

    def test_touching_windows_are_not_a_co_green_violation(self) -> None:
        rows = (
            signal_group_plan.PlanWindow(sg_no="1", window_index=0, start_sec=0.0, end_sec=20.0),
            signal_group_plan.PlanWindow(sg_no="2", window_index=0, start_sec=20.0, end_sec=30.0),
        )
        self.assertEqual(signal_group_plan.conflict_violations(rows, (("1", "2"),)), ())


class ModelSymmetryTests(unittest.TestCase):
    """플랜트가 realize 하는 배분이 모델이 예측에 쓰는 share 와 같은 값인가."""

    def test_realized_share_equals_native_phase_green_share(self) -> None:
        prog = program(
            150.0,
            {
                "1": ((48.0, 72.0),),
                "6": ((0.0, 45.0),),
                "2": ((0.0, 45.0),),
                "3": ((118.0, 147.0),),
                "4": ((75.0, 115.0),),
                "5": ((48.0, 72.0),),
                "7": ((129.0, 147.0),),
                "8": ((75.0, 126.0),),
            },
        )
        phases = {"p1": ["2", "3", "4", "5", "7", "8"], "p2": ["1", "6"]}
        plan = signal_group_plan.build_node_plan(
            node_id="SC1001",
            program=prog,
            phase_signal_groups=phases,
            signal_group_ids=[str(index) for index in range(1, 9)],
        )
        major_green = 61.0
        rows = axis_windows(
            plan, major_green=major_green, minor_green=79.0, major_maps_to="p1",
            amber_sec=3.0, all_red_sec=2.0,
        )
        realized: dict[str, float] = {}
        for row in rows:
            realized[row.sg_no] = realized.get(row.sg_no, 0.0) + (row.end_sec - row.start_sec)

        axis_green = native_phase_green.union_green_seconds(prog, phases["p1"])
        for sg_id in phases["p1"]:
            model_share = native_phase_green.union_green_seconds(prog, (sg_id,)) / axis_green
            self.assertAlmostEqual(realized[sg_id], major_green * model_share, places=9)

    def test_axis_union_of_realized_windows_fills_the_whole_axis_window(self) -> None:
        prog = program(150.0, {"1": ((0.0, 40.0),), "2": ((50.0, 60.0),), "3": ((80.0, 120.0),)})
        plan = signal_group_plan.build_node_plan(
            node_id="SC1",
            program=prog,
            phase_signal_groups={"p2": ["1", "2"], "p1": ["3"]},
            signal_group_ids=["1", "2", "3"],
        )
        rows = axis_windows(
            plan, major_green=50.0, minor_green=30.0, major_maps_to="p2",
            amber_sec=3.0, all_red_sec=2.0,
        )
        spans = sorted(
            (row.start_sec, row.end_sec) for row in rows if row.sg_no in ("1", "2")
        )
        merged_total = 0.0
        edge = float("-inf")
        for start, end in spans:
            merged_total += max(0.0, end - max(start, edge))
            edge = max(edge, end)
        self.assertAlmostEqual(merged_total, 50.0, places=9)


if __name__ == "__main__":
    unittest.main()
