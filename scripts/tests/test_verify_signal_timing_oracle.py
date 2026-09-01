# v3 N4-6 - oracle CLI 가 실 산출물에서 무엇을 판정하고 무엇을 못 하는지 고정한다
"""실 계획(15 SC / SG 136)에 대해 실 런 없이 낼 수 있는 판정을 고정한다.

여기서 PASS 가 나오는 것은 계획 자체의 성질뿐이다. readback 게이트는 런이 없으면
반드시 NOT_EVALUATED 여야 한다 - 그것을 PASS 로 미끄러뜨리지 않는 것이 이 검사의 몫이다.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts import verify_signal_timing_oracle as cli


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "outputs" / "signal_group_actuation_plan_v3.json"


class VerifyCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not PLAN_PATH.is_file():
            raise unittest.SkipTest(f"actuation plan missing: {PLAN_PATH}")
        cls.plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))

    def test_simulated_rows_command_exactly_the_live_phases(self) -> None:
        """두 인자를 그 SC 가 **켤 수 있는 현시**에 편다. 현시 수는 계획이 정한다.

        축 두 값을 `major_maps_to` 와 그 짝에만 놓으면 4현시 계획에서 어댑터가
        fail-closed 로 죽는다(`action commands green on ('p1','p2') but the plan has
        signal groups on ('p1','p2','p3','p4')`). SC107·108·109 는 현시가 셋이므로
        그 셋에만 실려야 한다 - 영구적색 현시에 실으면 실현이 0 이다.
        """
        from evaluation.controllers import action_csv_schema
        from evaluation.controllers import vissim_stackelberg_adapter as adapter

        rows = cli.simulated_action_rows(self.plan, major_green=57.0, minor_green=63.0)
        signal_rows = {int(row["sc_no"]): row for row in rows if row["kind"] == "signal"}
        # 2026-08-19: 계획이 15 -> 17 SC (SC7·SC16 복원). 계획에서 읽는다.
        self.assertEqual(len(self.plan["controllers"]), len(signal_rows))
        for sc_no, row in sorted(signal_rows.items()):
            with self.subTest(sc=sc_no):
                greens = action_csv_schema.phase_greens(row)
                lit = tuple(phase for phase in sorted(greens) if float(greens[phase]) > 0.0)
                self.assertEqual(adapter.plan_live_phases(self.plan, sc_no), lit)

    def test_simulated_rows_cover_every_planned_window(self) -> None:
        rows = cli.simulated_action_rows(self.plan, major_green=57.0, minor_green=63.0)
        sg_rows = [row for row in rows if row["kind"] == "signal_sg"]
        self.assertEqual(len(sg_rows), self.plan["counts"]["planned_windows"])
        signal_rows = [row for row in rows if row["kind"] == "signal"]
        self.assertEqual(len(signal_rows), self.plan["counts"]["controllers"])

    def test_run_free_gates_decide_and_readback_gates_stay_unevaluated(self) -> None:
        from evaluation.controllers import signal_timing_oracle as oracle

        rows = cli.simulated_action_rows(self.plan, major_green=57.0, minor_green=63.0)
        report = oracle.evaluate(self.plan, rows, readback_rows=None)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["plan_self_conflict"]["status"], "PASS")
        self.assertEqual(by_name["cycle_wrap"]["status"], "PASS")
        for name in (
            "request_readback_mismatch",
            "post_step_persistence",
            "intent_vs_request",
            "command_lag_sign",
            "runtime_cogreen",
        ):
            self.assertEqual(by_name[name]["status"], "NOT_EVALUATED", name)

    def test_integer_second_write_grid_breaks_the_half_second_gate(self) -> None:
        """실 계획의 경계는 실수인데 러너는 정수 초에만 쓴다. 실 런 없이도 재진다."""
        from evaluation.controllers import signal_timing_oracle as oracle

        rows = cli.simulated_action_rows(self.plan, major_green=57.0, minor_green=63.0)
        report = oracle.evaluate(self.plan, rows, readback_rows=None)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        gate = by_name["command_quantization_sec"]
        self.assertEqual(gate["status"], "FAIL")
        self.assertGreater(gate["value"], 0.5)
        self.assertEqual(by_name["transition_time_error_sec"]["status"], "BLOCKED")
        self.assertEqual(report["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
