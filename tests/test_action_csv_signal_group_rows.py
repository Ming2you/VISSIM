# N4-0 - action CSV 의 현시 4값(signal 행)과 그 파생인 signal_sg 행을 고정한다
"""어댑터가 현시 녹색을 action CSV 에 어떻게 싣는지, 그 값이 모델 share 와 같은지.

## 무엇이 정본인가

    signal 행     p1_green..p4_green = 모델의 결정. **정본**.
    signal_sg 행  그 4값을 SG 녹색창으로 편 것. **파생**.

파생 쪽 열 재사용은 `action_csv_schema` 가 정본으로 적어 둔다.

    dsd_no    -> sg 번호            link      -> 녹색창 인덱스
    p1_green  -> 녹색창 시작[s]      p2_green  -> 녹색창 끝[s]
    p3_green / p4_green -> 반드시 빈 칸 (두 행 종류의 판별자)
    offset    -> 그 SC 의 offset     green_sec -> 플랜 주기[s]

## 4현시를 실 데이터로 잰다

지금 저장소의 계획 산출물은 현시가 둘뿐이다(`.sig` 재작성이 막혀 있다 - 작업 1).
그래서 `Real4PhaseWindowTests` 는 계획 산출물이 아니라 **실 inpx 가 배정한 `.sig`** 를
직접 파싱해 SC1001 의 SG 8개를 이름으로 네 현시에 묶고, 그 위에서 창 배치·주기·share 를
잰다. 합성 픽스처가 아니라 실 프로그램(주기 150 s, 녹색창 8개)이다.
"""

from __future__ import annotations

import csv
import json
import tempfile
import types
import unittest
from pathlib import Path

from evaluation.controllers import action_csv_schema, plant_cycle, signal_group_plan
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.fixed_signal_schedule import compile_fixed_signal_schedules


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "outputs" / "signal_group_actuation_plan_v3.json"
NETWORK = ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
# clearance 는 러너 원문에서 읽는다 - 여기에 숫자를 적어 두면 러너가 clearance 를 바꿔도
# 이 검사가 옛 주기를 계속 정답이라고 우긴다.
AMBER_SEC, ALL_RED_SEC = plant_cycle.runner_clearance_sec()
CLEARANCE_SEC = AMBER_SEC + ALL_RED_SEC


def load_plan() -> dict:
    if not PLAN_PATH.is_file():
        raise unittest.SkipTest(f"actuation plan missing: {PLAN_PATH}")
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


# 계획이 유도된 주기. `.sig` 실측 150 s 와 같아야 한다.
PLAN_CYCLE_SEC = 150.0


def plan_greens(plan: dict, sc_no: int) -> dict[str, float]:
    """그 SC 가 **실제로 켤 수 있는** 현시에만 녹색을 고르게 싣는다.

    값을 손으로 적지 않는다. 살아 있는 현시 수 N 을 계획에서 읽고 예산을
    `cycle - N x clearance` 로 유도한다 — SC107·108·109 는 N=3 이라 141 이 나오고
    나머지는 N=4 라 138 이 나온다. 138/141 을 리터럴로 두면 현시 수가 바뀔 때
    검사가 조용히 틀린 값을 통과시킨다.
    """
    live = adapter.plan_live_phases(plan, int(sc_no))
    budget = PLAN_CYCLE_SEC - plant_cycle.clearance_sec() * float(len(live))
    each = budget / float(len(live))
    return {
        phase: (each if phase in live else 0.0)
        for phase in signal_group_plan.MODEL_PHASES
    }


class SignalGroupRowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = load_plan()

    def test_rows_cover_every_planned_window_of_the_controller(self) -> None:
        greens = plan_greens(self.plan, 1001)
        rows = adapter.signal_group_action_rows(
            self.plan, sc_no=1001, phase_greens=greens, offset=7.0, metadata="ok",
        )
        expected = sum(self.plan["controllers"]["1001"]["window_counts"].values())
        live = [value for value in greens.values() if value > 0.0]
        plan_cycle = sum(live) + len(live) * CLEARANCE_SEC
        self.assertEqual(len(rows), expected)
        for row in rows:
            self.assertEqual(row["kind"], "signal_sg")
            self.assertEqual(int(row["sc_no"]), 1001)
            self.assertEqual(float(row["green_sec"]), plan_cycle)
            self.assertEqual(float(row["offset"]), 7.0)
            start, end = action_csv_schema.window_bounds_sec(row)
            self.assertLess(start, end)
            self.assertGreaterEqual(start, 0.0)
            self.assertLessEqual(end, plan_cycle)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))

    def test_derived_rows_leave_the_unused_phase_columns_blank(self) -> None:
        """`signal_sg` 는 p1/p2 열을 창 시작·끝으로 재사용한다. 나머지 둘은 비어야 한다.

        비어 있는 것이 `signal` 행과의 판별자다 - 러너가 이 칸이 차 있으면 그 행을
        invalid 로 센다(`SignalSgRowValid`).
        """
        rows = adapter.signal_group_action_rows(
            self.plan, sc_no=1001, phase_greens=plan_greens(self.plan, sc_no=1001), offset=0.0,
            metadata="ok",
        )
        self.assertTrue(rows)
        for row in rows:
            for field in action_csv_schema.WINDOW_BLANK_FIELDS:
                self.assertEqual(row[field], "", field)

    def test_a_plan_without_clearance_keys_still_lands_on_the_runner_cycle(self) -> None:
        """계획 표에 clearance 가 없어도 러너와 같은 주기가 나와야 한다.

        러너는 이 `green_sec` 을 자기 현시 주기와 대조해 다르면 그 SC 의 창을 통째로
        거부한다(`SIGNAL_SG_PLAN_CYCLE_STALE`). 어댑터의 기본값이 리터럴이면 러너가
        clearance 를 바꾼 순간 15 SC 가 전부 거부되고, 그 거부는 런 중에만 보인다.
        """
        stripped = dict(self.plan)
        stripped.pop("amber_sec", None)
        stripped.pop("all_red_sec", None)
        rows = adapter.signal_group_action_rows(
            stripped, sc_no=1001, phase_greens=plan_greens(self.plan, sc_no=1001), offset=0.0,
            metadata="ok",
        )
        self.assertTrue(rows)
        for row in rows:
            live = [value for value in plan_greens(self.plan, 1001).values() if value > 0.0]
            self.assertEqual(
                float(row["green_sec"]), sum(live) + len(live) * CLEARANCE_SEC
            )

    def test_row_green_matches_the_model_native_share(self) -> None:
        rows = adapter.signal_group_action_rows(
            self.plan, sc_no=1001, phase_greens=plan_greens(self.plan, sc_no=1001), offset=0.0,
            metadata="ok",
        )
        realized: dict[str, float] = {}
        for row in rows:
            key = str(row["dsd_no"])
            start, end = action_csv_schema.window_bounds_sec(row)
            realized[key] = realized.get(key, 0.0) + (end - start)
        node = self.plan["controllers"]["1001"]
        axis = float(node["axis_green_sec"]["p1"])
        for sg_no in node["phase_signal_groups"]["p1"]:
            share = float(node["native_green_sec"][sg_no]) / axis
            self.assertAlmostEqual(
                realized[sg_no], plan_greens(self.plan, 1001)["p1"] * share, places=5
            )

    def test_plan_rows_never_co_green_a_conflicting_pair(self) -> None:
        for sc_no, node in self.plan["controllers"].items():
            rows = adapter.signal_group_action_rows(
                self.plan, sc_no=int(sc_no), phase_greens=plan_greens(self.plan, int(sc_no)),
                offset=0.0, metadata="ok",
            )
            windows = tuple(
                signal_group_plan.PlanWindow(
                    sg_no=str(row["dsd_no"]),
                    window_index=int(row["link"]),
                    start_sec=action_csv_schema.window_bounds_sec(row)[0],
                    end_sec=action_csv_schema.window_bounds_sec(row)[1],
                )
                for row in rows
            )
            pairs = tuple((str(a), str(b)) for a, b in node["conflict_pairs"])
            self.assertEqual(
                signal_group_plan.conflict_violations(windows, pairs), (), f"sc={sc_no}"
            )

    def test_unknown_controller_is_rejected_rather_than_silently_skipped(self) -> None:
        with self.assertRaises(signal_group_plan.SignalGroupPlanError):
            adapter.signal_group_action_rows(
                self.plan, sc_no=424242, phase_greens=plan_greens(self.plan, sc_no=1001), offset=0.0,
                metadata="ok",
            )

    def test_commanding_a_phase_the_plan_cannot_actuate_is_refused(self) -> None:
        """계획이 SG 를 붙여 두지 않은 현시에 녹색을 주면 죽어야 한다.

        조용히 넘어가면 러너는 주기가 맞는 CSV 를 받고, 녹색을 받기로 한 이동류는 창
        하나 없이 통째로 적색이 된다. 실 계획 15 SC 가 지금 두 현시뿐이므로, p3 에
        녹색을 주는 것은 그 상황을 정확히 재현한다.
        """
        for sc_no in sorted(self.plan["controllers"], key=int):
            with self.subTest(sc=sc_no):
                with self.assertRaises(signal_group_plan.SignalGroupPlanError):
                    adapter.signal_group_action_rows(
                        self.plan,
                        sc_no=int(sc_no),
                        phase_greens={"p1": 40.0, "p2": 40.0, "p3": 30.0, "p4": 0.0},
                        offset=0.0,
                        metadata="ok",
                    )

    def test_live_phases_are_the_ones_the_plant_can_actually_serve(self) -> None:
        """살아 있는 현시 = SG 가 붙어 있고 **그 SG 가 켜질 수 있는** 현시.

        SG 가 붙어 있기만 하면 살아 있다고 세면 안 된다. SC107·108·109 는 한 현시의 SG 가
        `.sig` 에서 영구적색이라 아무리 녹색을 명령해도 0 초가 실현된다. 그 현시를 세면
        러너가 clearance 를 한 번 더 물고, 모델은 켜지지 않을 현시에 예산을 붓는다.

        정답은 실측이다 — VISSIM 안에서 400 초를 돌려 SG 상태를 초당 받아 센 서로 다른
        동시녹색 집합의 수(`outputs/live_signal_cycle_probe_n4dr150_20260812.json`).
        여기 값을 손으로 적지 않는다.
        """
        probe = json.loads(
            (ROOT / "outputs" / "live_signal_cycle_probe_n4dr150_20260812.json")
            .read_text(encoding="utf-8")
        )["controllers"]
        live = {
            str(sc_no): adapter.plan_live_phases(self.plan, int(sc_no))
            for sc_no in self.plan["controllers"]
        }
        self.assertEqual(len(live), 15)
        for sc_no, phases in sorted(live.items(), key=lambda kv: int(kv[0])):
            with self.subTest(sc=sc_no):
                measured = int(probe[sc_no]["rewritten"]["green_sets"])
                # SC5 는 SG 24개짜리 대형 교차로라 실측 동시녹색 집합이 6 이다. 모델의
                # 어휘는 4현시이므로 그 SC 만 min 을 취한다 - 나머지 14 개는 실측 그대로다.
                self.assertEqual(min(measured, 4), len(phases), f"SC{sc_no} {phases}")

    def test_the_probe_says_three_controllers_run_three_phases(self) -> None:
        """되돌림 증명 - 실측이 15 SC 전부 4현시였다면 위 검사는 아무것도 안 든다."""
        probe = json.loads(
            (ROOT / "outputs" / "live_signal_cycle_probe_n4dr150_20260812.json")
            .read_text(encoding="utf-8")
        )["controllers"]
        three = {sc for sc, entry in probe.items() if entry["rewritten"]["green_sets"] == 3}
        self.assertEqual({"107", "108", "109"}, three)


class Real4PhaseWindowTests(unittest.TestCase):
    """실 `.sig` 를 네 현시로 묶어 4현시 배치·주기·share 를 잰다.

    계획 산출물이 아직 2현시라서 합성 픽스처를 쓰고 싶어지는 자리다. 대신 실 inpx 가
    SC1001 에 배정한 프로그램(주기 150 s, SG 8개, 녹색창 8개)을 그대로 읽고 SG 이름으로
    묶는다. 값은 전부 실측이다.
    """

    # 실 SC1001 의 SG 이름 - EBT/WBT 가 주도로 직진, WBL/EBL 이 주도로 좌회전이다.
    PHASE_GROUPS = {
        "p1": ["2", "6"],   # EBT, WBT   major 직진
        "p2": ["1", "5"],   # WBL, EBL   major 좌
        "p3": ["4", "8"],   # SBT, NBT   minor 직진
        "p4": ["3", "7"],   # NBL, SBL   minor 좌
    }

    @classmethod
    def setUpClass(cls) -> None:
        if not NETWORK.is_file():
            raise unittest.SkipTest(f"network missing: {NETWORK}")
        schedules, errors = compile_fixed_signal_schedules(NETWORK, ["SC1001"])
        if "SC1001" not in schedules:
            raise unittest.SkipTest(f"no compiled schedule for SC1001: {errors}")
        cls.program = schedules["SC1001"].program
        cls.plan = signal_group_plan.build_node_plan(
            node_id="SC1001",
            program=cls.program,
            phase_signal_groups=cls.PHASE_GROUPS,
            signal_group_ids=[str(index) for index in range(1, 9)],
        )

    def test_the_real_program_really_supports_four_phases(self) -> None:
        """네 현시 전부 native 녹색이 있다. 없으면 아래 검사들이 의미가 없다."""
        self.assertEqual(float(self.program.cycle_length_sec), 150.0)
        for phase in signal_group_plan.MODEL_PHASES:
            with self.subTest(phase=phase):
                self.assertGreater(float(self.plan.axis_green_sec[phase]), 0.0)
        self.assertEqual(sum(self.plan.window_counts.values()), 8)

    def test_four_live_phases_bite_clearance_four_times(self) -> None:
        greens = {"p1": 45.0, "p2": 24.0, "p3": 45.0, "p4": 24.0}
        self.assertEqual(signal_group_plan.live_phases(greens), ("p1", "p2", "p3", "p4"))
        self.assertEqual(
            signal_group_plan.plan_cycle_sec(greens, AMBER_SEC, ALL_RED_SEC),
            138.0 + 4 * CLEARANCE_SEC,
        )

    def test_four_phase_windows_are_laid_out_in_order_without_overlap(self) -> None:
        greens = {"p1": 45.0, "p2": 24.0, "p3": 45.0, "p4": 24.0}
        windows = signal_group_plan.plan_windows(
            self.plan,
            phase_greens=greens,
            phase_order=signal_group_plan.phase_layout_order("p1"),
            amber_sec=AMBER_SEC,
            all_red_sec=ALL_RED_SEC,
        )
        by_phase: dict[str, list[tuple[float, float]]] = {}
        for phase, ids in self.PHASE_GROUPS.items():
            spans = [
                (w.start_sec, w.end_sec) for w in windows if w.sg_no in ids
            ]
            by_phase[phase] = spans
        cursor = 0.0
        for phase in ("p1", "p2", "p3", "p4"):
            span = greens[phase]
            low = min(start for start, _ in by_phase[phase])
            high = max(end for _, end in by_phase[phase])
            self.assertAlmostEqual(low, cursor, places=6, msg=phase)
            self.assertAlmostEqual(high, cursor + span, places=6, msg=phase)
            cursor += span + CLEARANCE_SEC
        self.assertAlmostEqual(
            cursor, signal_group_plan.plan_cycle_sec(greens, AMBER_SEC, ALL_RED_SEC),
            places=6,
        )

    def test_four_phase_windows_reproduce_the_native_share_inside_each_phase(self) -> None:
        greens = {"p1": 45.0, "p2": 24.0, "p3": 45.0, "p4": 24.0}
        windows = signal_group_plan.plan_windows(
            self.plan,
            phase_greens=greens,
            phase_order=signal_group_plan.phase_layout_order("p1"),
            amber_sec=AMBER_SEC,
            all_red_sec=ALL_RED_SEC,
        )
        realized: dict[str, float] = {}
        for window in windows:
            realized[window.sg_no] = realized.get(window.sg_no, 0.0) + (
                window.end_sec - window.start_sec
            )
        for phase, ids in self.PHASE_GROUPS.items():
            union = float(self.plan.axis_green_sec[phase])
            for sg_no in ids:
                native = sum(
                    interval.end_sec - interval.start_sec
                    for interval in self.program.sg_timelines[sg_no].intervals
                    if interval.state == "GREEN"
                )
                with self.subTest(phase=phase, sg=sg_no):
                    self.assertAlmostEqual(
                        realized[sg_no], greens[phase] * native / union, places=6
                    )

    def test_a_dropped_phase_shrinks_the_cycle_by_one_clearance(self) -> None:
        """현시 하나를 0 으로 두면 전이도 하나 줄어야 한다.

        clearance 를 상수 4회로 두면 이 검사가 깨진다 - 실제로 2현시 계획에서 그 상수는
        틀린 값이 된다.
        """
        four = {"p1": 45.0, "p2": 24.0, "p3": 45.0, "p4": 24.0}
        three = {"p1": 45.0, "p2": 24.0, "p3": 45.0, "p4": 0.0}
        self.assertEqual(
            signal_group_plan.plan_cycle_sec(four, AMBER_SEC, ALL_RED_SEC)
            - signal_group_plan.plan_cycle_sec(three, AMBER_SEC, ALL_RED_SEC),
            24.0 + CLEARANCE_SEC,
        )


class WriteActionCsvTests(unittest.TestCase):
    """`write_action_csv` 가 실제로 그 행을 파일에 쓰는가."""

    def _cfg(self):
        network = types.SimpleNamespace(ramp_capacity_veh_h={})
        freeway_follower = types.SimpleNamespace(vsl_set=[60.0, 80.0, 100.0])
        return types.SimpleNamespace(network=network, freeway_follower=freeway_follower)

    def _control(self, plan_table):
        """SC1001 의 살아 있는 현시에만 녹색을 싣는다.

        비워 두면 어댑터가 기본값으로 떨어져 두 현시만 지시하고, 4현시 계획과 부딪혀
        `signal_group_action_rows` 가 죽는다 - 그 죽음은 픽스처 문제이지 계약 위반이 아니다.
        """
        if plan_table is None:
            # 계획 없이 도는 legacy 경로. 어댑터가 기본값을 쓰는 것이 검사 대상이다.
            return types.SimpleNamespace(
                green_times={}, offsets={}, ramp_metering={}, diagnostics={}
            )
        greens = plan_greens(plan_table, 1001)
        return types.SimpleNamespace(
            green_times={f"SC1001_{phase}": value for phase, value in greens.items()},
            offsets={},
            ramp_metering={},
            diagnostics={},
        )

    def _write(self, plan_table):
        mapping = {
            "segments": [],
            "signals": [{"id": "SC1001", "sc_no": 1001, "major_maps_to": "p1"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "action.csv"
            adapter.write_action_csv(
                path,
                self._control(plan_table),
                self._cfg(),
                mapping,
                lambda control, link, index, cfg: 80.0,
                {"controller_status": "ok"},
                {},
                signal_group_plan_table=plan_table,
            )
            with path.open(encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                return list(reader.fieldnames or ()), list(reader)

    def test_the_written_header_is_the_v4_schema(self) -> None:
        header, _ = self._write(load_plan())
        self.assertEqual(header, list(action_csv_schema.ACTION_CSV_FIELDS))
        self.assertNotIn("major_green", header)
        self.assertNotIn("minor_green", header)

    def test_signal_sg_rows_are_written_next_to_the_signal_rows(self) -> None:
        plan = load_plan()
        _, rows = self._write(plan)
        kinds = [row["kind"] for row in rows]
        self.assertIn("signal", kinds)
        self.assertIn("signal_sg", kinds)
        signal_sg = [row for row in rows if row["kind"] == "signal_sg"]
        self.assertEqual(
            len(signal_sg), sum(plan["controllers"]["1001"]["window_counts"].values())
        )
        signal_row = next(row for row in rows if row["kind"] == "signal")
        greens = action_csv_schema.phase_greens(signal_row)
        expected_cycle = signal_group_plan.plan_cycle_sec(greens, AMBER_SEC, ALL_RED_SEC)
        for row in signal_sg:
            self.assertEqual(row["offset"], signal_row["offset"])
            self.assertAlmostEqual(float(row["green_sec"]), expected_cycle, places=6)

    def test_the_signal_row_carries_four_phase_columns(self) -> None:
        _, rows = self._write(load_plan())
        signal_row = next(row for row in rows if row["kind"] == "signal")
        greens = action_csv_schema.phase_greens(signal_row)
        self.assertEqual(sorted(greens), ["p1", "p2", "p3", "p4"])
        # 살아 있는 현시는 계획이 정한다 - 여기에 ("p1","p2") 를 적어 두면 4현시
        # 계획이 들어와도 검사가 옛 상태를 정답이라 우긴다.
        self.assertEqual(
            signal_group_plan.live_phases(greens),
            adapter.plan_live_phases(load_plan(), 1001),
        )
        for phase, value in greens.items():
            if phase not in adapter.plan_live_phases(load_plan(), 1001):
                self.assertEqual(value, 0.0, phase)

    def test_no_plan_table_keeps_the_legacy_row_set(self) -> None:
        _, rows = self._write(None)
        self.assertNotIn("signal_sg", {row["kind"] for row in rows})


if __name__ == "__main__":
    unittest.main()
