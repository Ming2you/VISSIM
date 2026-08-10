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


@dataclass(frozen=True)
class FakeProgram:
    controller_id: str
    cycle_length_sec: float
    program_offset_sec: float
    sg_timelines: dict


def green(*spans: tuple[float, float]) -> tuple:
    return tuple(FakeInterval("GREEN", start, end) for start, end in spans)


def program(cycle: float, spans: dict[str, tuple]) -> FakeProgram:
    return FakeProgram(
        controller_id="SCX",
        cycle_length_sec=cycle,
        program_offset_sec=0.0,
        sg_timelines={
            sg_id: FakeTimeline(name=f"SG{sg_id}", intervals=green(*value))
            for sg_id, value in spans.items()
        },
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
        rows = signal_group_plan.plan_windows(
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
        rows = signal_group_plan.plan_windows(
            plan, major_green=40.0, minor_green=20.0, major_maps_to="p2",
            amber_sec=3.0, all_red_sec=2.0,
        )
        by_sg = {row.sg_no: (row.start_sec, row.end_sec) for row in rows}
        self.assertEqual(by_sg["1"], (0.0, 40.0))
        self.assertEqual(by_sg["3"], (45.0, 65.0))
        self.assertEqual(signal_group_plan.plan_cycle_sec(40.0, 20.0, 3.0, 2.0), 70.0)

    def test_major_maps_to_p1_sends_p1_groups_to_the_major_window(self) -> None:
        prog = program(100.0, {"1": ((0.0, 30.0),), "3": ((60.0, 90.0),)})
        plan = signal_group_plan.build_node_plan(
            node_id="SC1001",
            program=prog,
            phase_signal_groups={"p2": ["1"], "p1": ["3"]},
            signal_group_ids=["1", "3"],
        )
        rows = signal_group_plan.plan_windows(
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
        rows = signal_group_plan.plan_windows(
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
        rows = signal_group_plan.plan_windows(
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
        rows = signal_group_plan.plan_windows(
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
        rows = signal_group_plan.plan_windows(
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
        rows = signal_group_plan.plan_windows(
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
        rows = signal_group_plan.plan_windows(
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
