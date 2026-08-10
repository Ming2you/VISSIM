# v3 N4-5 - action CSV 의 signal_sg 행(SG 단위 타이밍)을 고정한다
"""어댑터가 SG 단위 녹색창을 action CSV 에 실는지, 그리고 그 값이 모델 share 와 같은지.

행 열은 13열 헤더를 **바꾸지 않는다**. `signal_sg` 행은 기존 열을 재사용한다.

    dsd_no        -> sg 번호
    link          -> 녹색창 인덱스
    major_green   -> 녹색창 시작[s]   (플랜 주기 좌표)
    minor_green   -> 녹색창 끝[s]
    offset        -> 그 SC 의 offset (같은 SC 의 signal 행과 같아야 한다)
    green_sec     -> 플랜 주기[s]     (= major + minor + 2*amber + 2*all_red)

헤더를 늘리지 않은 이유는 하위호환이다. 늘리면 기존 action CSV 소비자가 전부 깨지고,
러너의 `UBound(parts) <> 12` 계약도 함께 바뀐다. 대신 재사용 열의 의미를 여기와
어댑터·러너 세 곳에 같은 말로 적어 둔다.
"""

from __future__ import annotations

import csv
import json
import tempfile
import types
import unittest
from pathlib import Path

from evaluation.controllers import signal_group_plan
from evaluation.controllers import vissim_stackelberg_adapter as adapter


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "outputs" / "signal_group_actuation_plan_v3.json"


def load_plan() -> dict:
    if not PLAN_PATH.is_file():
        raise unittest.SkipTest(f"actuation plan missing: {PLAN_PATH}")
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


class SignalGroupRowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = load_plan()

    def test_rows_cover_every_planned_window_of_the_controller(self) -> None:
        rows = adapter.signal_group_action_rows(
            self.plan, sc_no=1001, major_green=61.0, minor_green=79.0, offset=7.0,
            metadata="ok",
        )
        expected = sum(self.plan["controllers"]["1001"]["window_counts"].values())
        self.assertEqual(len(rows), expected)
        for row in rows:
            self.assertEqual(row["kind"], "signal_sg")
            self.assertEqual(int(row["sc_no"]), 1001)
            self.assertEqual(float(row["green_sec"]), 150.0)
            self.assertEqual(float(row["offset"]), 7.0)
            self.assertLess(float(row["major_green"]), float(row["minor_green"]))
            self.assertGreaterEqual(float(row["major_green"]), 0.0)
            self.assertLessEqual(float(row["minor_green"]), 150.0)
        self.assertEqual(len({row["id"] for row in rows}), len(rows))

    def test_row_green_matches_the_model_native_share(self) -> None:
        rows = adapter.signal_group_action_rows(
            self.plan, sc_no=1001, major_green=61.0, minor_green=79.0, offset=0.0,
            metadata="ok",
        )
        realized: dict[str, float] = {}
        for row in rows:
            key = str(row["dsd_no"])
            realized[key] = realized.get(key, 0.0) + (
                float(row["minor_green"]) - float(row["major_green"])
            )
        node = self.plan["controllers"]["1001"]
        axis = float(node["axis_green_sec"]["p1"])
        for sg_no in node["phase_signal_groups"]["p1"]:
            share = float(node["native_green_sec"][sg_no]) / axis
            self.assertAlmostEqual(realized[sg_no], 61.0 * share, places=5)

    def test_plan_rows_never_co_green_a_conflicting_pair(self) -> None:
        for sc_no, node in self.plan["controllers"].items():
            rows = adapter.signal_group_action_rows(
                self.plan, sc_no=int(sc_no), major_green=57.0, minor_green=63.0,
                offset=0.0, metadata="ok",
            )
            windows = tuple(
                signal_group_plan.PlanWindow(
                    sg_no=str(row["dsd_no"]),
                    window_index=int(row["link"]),
                    start_sec=float(row["major_green"]),
                    end_sec=float(row["minor_green"]),
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
                self.plan, sc_no=424242, major_green=40.0, minor_green=40.0, offset=0.0,
                metadata="ok",
            )


class WriteActionCsvTests(unittest.TestCase):
    """`write_action_csv` 가 실제로 그 행을 파일에 쓰는가."""

    def _cfg(self):
        network = types.SimpleNamespace(ramp_capacity_veh_h={})
        freeway_follower = types.SimpleNamespace(vsl_set=[60.0, 80.0, 100.0])
        return types.SimpleNamespace(network=network, freeway_follower=freeway_follower)

    def _control(self):
        return types.SimpleNamespace(
            green_times={},
            offsets={},
            ramp_metering={},
            diagnostics={},
        )

    def test_signal_sg_rows_are_written_next_to_the_signal_rows(self) -> None:
        plan = load_plan()
        mapping = {
            "segments": [],
            "signals": [{"id": "SC1001", "sc_no": 1001, "major_maps_to": "p1"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "action.csv"
            adapter.write_action_csv(
                path,
                self._control(),
                self._cfg(),
                mapping,
                lambda control, link, index, cfg: 80.0,
                {"controller_status": "ok"},
                {},
                signal_group_plan_table=plan,
            )
            with path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        kinds = [row["kind"] for row in rows]
        self.assertIn("signal", kinds)
        self.assertIn("signal_sg", kinds)
        signal_sg = [row for row in rows if row["kind"] == "signal_sg"]
        self.assertEqual(
            len(signal_sg), sum(plan["controllers"]["1001"]["window_counts"].values())
        )
        signal_row = next(row for row in rows if row["kind"] == "signal")
        for row in signal_sg:
            self.assertEqual(row["offset"], signal_row["offset"])
            self.assertAlmostEqual(
                float(row["green_sec"]),
                float(signal_row["major_green"]) + float(signal_row["minor_green"]) + 10.0,
                places=6,
            )

    def test_no_plan_table_keeps_the_legacy_row_set(self) -> None:
        mapping = {
            "segments": [],
            "signals": [{"id": "SC1001", "sc_no": 1001, "major_maps_to": "p1"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "action.csv"
            adapter.write_action_csv(
                path,
                self._control(),
                self._cfg(),
                mapping,
                lambda control, link, index, cfg: 80.0,
                {"controller_status": "ok"},
                {},
            )
            with path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        self.assertNotIn("signal_sg", {row["kind"] for row in rows})


if __name__ == "__main__":
    unittest.main()
