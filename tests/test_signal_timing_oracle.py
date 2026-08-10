# v3 N4-6 - 신호 timing oracle(D-core)의 판정 논리와 valid-interval 계약을 고정한다
"""명령한 신호가 VISSIM 에 **그 시각에** 들어갔는지를 되읽어 판정하는 oracle.

여기서 고정하는 것은 판정 논리다. 실 런 없이 확인 가능한 것(계약·스키마·양자화)과
실 런이 필요한 것(readback 대조)을 구분해서, 후자는 PASS 가 아니라 NOT_EVALUATED 로
남는다는 것까지 검사한다. 측정 불가를 통과로 처리하지 않는 것이 이 절의 요구다.
"""

from __future__ import annotations

import unittest

from evaluation.controllers import signal_timing_oracle as oracle


def plan_table(cycle: float = 50.0) -> dict:
    return {
        "amber_sec": 3.0,
        "all_red_sec": 2.0,
        "controllers": {
            "7": {
                "node_id": "SC7",
                "sc_no": 7,
                "major_maps_to": "p2",
                "native_cycle_sec": cycle,
                "conflict_pairs": [["1", "2"]],
                "window_counts": {"1": 1, "2": 1},
            }
        },
    }


def action_rows(offset: float = 0.0) -> list[dict]:
    """한 번의 결정이 실은 signal / signal_sg 행. sim_sec 은 결정 시각이다."""
    rows = [
        {
            "sim_sec": "0", "kind": "signal", "id": "SC7", "sc_no": "7",
            "major_green": "20", "minor_green": "20", "offset": str(offset),
            "green_sec": "", "dsd_no": "", "link": "",
        }
    ]
    for sg_no, (start, end) in (("1", (0.0, 12.0)), ("2", (12.0, 20.0))):
        rows.append({
            "sim_sec": "0", "kind": "signal_sg", "id": f"SC7_SG{sg_no}_W0",
            "dsd_no": sg_no, "sc_no": "7", "link": "0",
            "major_green": str(start), "minor_green": str(end),
            "offset": str(offset), "green_sec": "50",
        })
    return rows


def readback(sim_sec, sc_no, sg_no, requested, read=None, ok="1", stage="immediate") -> dict:
    return {
        "sim_sec": str(sim_sec), "sc_no": str(sc_no), "sg_no": str(sg_no),
        "requested_state": requested,
        "readback_state": requested if read is None else read,
        "ok": ok, "stage": stage,
    }


class IntendedStateTests(unittest.TestCase):
    def test_state_function_mirrors_the_runner(self) -> None:
        windows = ((0.0, 12.0),)
        self.assertEqual(oracle.intended_state(windows, 0.0, 50.0, 3.0), "GREEN")
        self.assertEqual(oracle.intended_state(windows, 11.999, 50.0, 3.0), "GREEN")
        self.assertEqual(oracle.intended_state(windows, 12.0, 50.0, 3.0), "AMBER")
        self.assertEqual(oracle.intended_state(windows, 15.0, 50.0, 3.0), "RED")
        self.assertEqual(oracle.intended_state((), 5.0, 50.0, 3.0), "RED")

    def test_amber_wraps_over_the_cycle_boundary(self) -> None:
        windows = ((45.0, 50.0),)
        self.assertEqual(oracle.intended_state(windows, 1.0, 50.0, 3.0), "AMBER")
        self.assertEqual(oracle.intended_state(windows, 3.0, 50.0, 3.0), "RED")


class RunFreeGateTests(unittest.TestCase):
    def test_plan_without_a_run_is_not_evaluated_not_passed(self) -> None:
        report = oracle.evaluate(plan_table(), action_rows(), readback_rows=None)
        self.assertEqual(report["status"], "BLOCKED")
        by_name = {gate["name"]: gate for gate in report["gates"]}
        for name in (
            "request_readback_mismatch",
            "post_step_persistence",
            "intent_vs_request",
            "command_lag_sign",
            "runtime_cogreen",
        ):
            self.assertEqual(by_name[name]["status"], "NOT_EVALUATED", name)
            self.assertTrue(by_name[name]["needs"], name)

    def test_transition_time_gate_is_blocked_by_readback_resolution(self) -> None:
        report = oracle.evaluate(plan_table(), action_rows(), readback_rows=None)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        gate = by_name["transition_time_error_sec"]
        self.assertEqual(gate["status"], "BLOCKED")
        self.assertIn("0.5", gate["detail"])
        self.assertIn("1", gate["detail"])

    def test_plan_self_conflict_gate_passes_on_a_disjoint_plan(self) -> None:
        report = oracle.evaluate(plan_table(), action_rows(), readback_rows=None)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["plan_self_conflict"]["status"], "PASS")

    def test_plan_self_conflict_gate_fails_when_a_forbidden_pair_overlaps(self) -> None:
        rows = action_rows()
        # SG2 의 창을 SG1 위로 끌어 겹치게 만든다.
        rows[2]["major_green"] = "5"
        rows[2]["minor_green"] = "18"
        report = oracle.evaluate(plan_table(), rows, readback_rows=None)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["plan_self_conflict"]["status"], "FAIL")
        self.assertEqual(report["status"], "FAIL")

    def test_quantization_gate_measures_the_boundary_rounding_without_a_run(self) -> None:
        rows = action_rows()
        rows[1]["minor_green"] = "12.4"
        rows[2]["major_green"] = "12.4"
        report = oracle.evaluate(plan_table(), rows, readback_rows=None)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        gate = by_name["command_quantization_sec"]
        self.assertEqual(gate["status"], "FAIL")
        self.assertAlmostEqual(gate["value"], 0.6, places=6)

    def test_min_green_gate_is_not_evaluated_without_a_declared_authority(self) -> None:
        report = oracle.evaluate(plan_table(), action_rows(), readback_rows=None)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["min_green_sec"]["status"], "NOT_EVALUATED")
        self.assertIn("intergreen", by_name["min_green_sec"]["needs"].lower())

    def test_min_green_gate_fails_when_a_threshold_is_supplied_and_violated(self) -> None:
        report = oracle.evaluate(plan_table(), action_rows(), readback_rows=None, min_green_sec=10.0)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["min_green_sec"]["status"], "FAIL")
        self.assertAlmostEqual(by_name["min_green_sec"]["value"], 8.0, places=6)


class ReadbackGateTests(unittest.TestCase):
    def _clean_readback(self) -> list[dict]:
        rows: list[dict] = []
        for sec in range(0, 25):
            for sg_no, windows in (("1", ((0.0, 12.0),)), ("2", ((12.0, 20.0),))):
                state = oracle.intended_state(windows, float(sec) % 50.0, 50.0, 3.0)
                rows.append(readback(sec, 7, sg_no, state))
                rows.append(readback(sec, 7, sg_no, state, stage="post_step"))
        return rows

    def test_clean_run_passes_the_readback_gates(self) -> None:
        report = oracle.evaluate(plan_table(), action_rows(), self._clean_readback())
        by_name = {gate["name"]: gate for gate in report["gates"]}
        for name in (
            "request_readback_mismatch",
            "post_step_persistence",
            "intent_vs_request",
            "command_lag_sign",
            "runtime_cogreen",
        ):
            self.assertEqual(by_name[name]["status"], "PASS", f"{name}: {by_name[name]}")
        # 전이 시각 게이트는 여전히 측정 불가다. 그래서 전체는 PASS 가 아니다.
        self.assertEqual(report["status"], "BLOCKED")

    def test_readback_that_disagrees_with_the_request_fails(self) -> None:
        rows = self._clean_readback()
        rows[0]["readback_state"] = "RED"
        rows[0]["ok"] = "0"
        report = oracle.evaluate(plan_table(), action_rows(), rows)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["request_readback_mismatch"]["status"], "FAIL")
        self.assertEqual(by_name["request_readback_mismatch"]["count"], 1)
        self.assertEqual(report["status"], "FAIL")

    def test_request_that_disagrees_with_the_delivered_plan_fails(self) -> None:
        """러너가 VISSIM 에 잘 썼더라도, 쓴 값이 계획과 다르면 통과가 아니다."""
        rows = self._clean_readback()
        for row in rows:
            if row["sim_sec"] == "5" and row["sg_no"] == "1":
                row["requested_state"] = "RED"
                row["readback_state"] = "RED"
        report = oracle.evaluate(plan_table(), action_rows(), rows)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["intent_vs_request"]["status"], "FAIL")
        self.assertGreaterEqual(by_name["intent_vs_request"]["count"], 1)

    def test_post_step_drift_fails_the_persistence_gate(self) -> None:
        rows = self._clean_readback()
        for row in rows:
            if row["stage"] == "post_step" and row["sim_sec"] == "3":
                row["readback_state"] = "RED"
                row["ok"] = "0"
        report = oracle.evaluate(plan_table(), action_rows(), rows)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["post_step_persistence"]["status"], "FAIL")

    def test_simultaneous_green_of_a_conflicting_pair_fails(self) -> None:
        rows = self._clean_readback()
        for row in rows:
            if row["sim_sec"] == "5" and row["sg_no"] == "2":
                row["requested_state"] = "GREEN"
                row["readback_state"] = "GREEN"
        report = oracle.evaluate(plan_table(), action_rows(), rows)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["runtime_cogreen"]["status"], "FAIL")
        self.assertGreaterEqual(by_name["runtime_cogreen"]["count"], 1)

    def test_a_transition_written_before_its_intended_time_fails_the_lag_sign(self) -> None:
        rows = self._clean_readback()
        # SG1 의 GREEN->AMBER 는 sec 12 가 의도다. sec 10 에 미리 쓰면 음의 lag 다.
        for row in rows:
            if row["sg_no"] == "1" and int(row["sim_sec"]) in (10, 11):
                row["requested_state"] = "AMBER"
                row["readback_state"] = "AMBER"
        report = oracle.evaluate(plan_table(), action_rows(), rows)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["command_lag_sign"]["status"], "FAIL")


class VacuousEvidenceTests(unittest.TestCase):
    """비교를 한 번도 못 했으면 PASS 가 아니다. 이 절의 요구가 정확히 그것이다."""

    def test_readback_without_a_delivered_plan_cannot_pass_the_intent_gates(self) -> None:
        rows = [readback(sec, 7, "1", "GREEN") for sec in range(5)]
        report = oracle.evaluate(plan_table(), action_rows=[], readback_rows=rows)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["intent_vs_request"]["status"], "NOT_EVALUATED")
        self.assertEqual(by_name["command_lag_sign"]["status"], "NOT_EVALUATED")
        self.assertTrue(by_name["intent_vs_request"]["needs"])

    def test_empty_readback_log_cannot_pass_the_readback_gates(self) -> None:
        report = oracle.evaluate(plan_table(), action_rows(), readback_rows=[])
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["request_readback_mismatch"]["status"], "NOT_EVALUATED")
        self.assertEqual(by_name["post_step_persistence"]["status"], "NOT_EVALUATED")
        self.assertEqual(by_name["runtime_cogreen"]["status"], "NOT_EVALUATED")

    def test_cogreen_gate_needs_a_controller_with_declared_conflicts_in_the_log(self) -> None:
        rows = [readback(sec, 99, "1", "GREEN") for sec in range(5)]
        report = oracle.evaluate(plan_table(), action_rows(), readback_rows=rows)
        by_name = {gate["name"]: gate for gate in report["gates"]}
        self.assertEqual(by_name["runtime_cogreen"]["status"], "NOT_EVALUATED")


class ReportShapeTests(unittest.TestCase):
    def test_report_states_the_valid_interval_contract_explicitly(self) -> None:
        report = oracle.evaluate(plan_table(), action_rows(), readback_rows=None)
        contract = report["valid_interval_contract"]
        self.assertIn("immediate", contract["stages"])
        self.assertIn("post_step", contract["stages"])
        self.assertIn("[t, t')", contract["statement"])
        self.assertTrue(contract["interior_sampled"] is False)

    def test_status_is_fail_when_any_gate_fails_even_if_others_are_blocked(self) -> None:
        rows = action_rows()
        rows[2]["major_green"] = "5"
        rows[2]["minor_green"] = "18"
        report = oracle.evaluate(plan_table(), rows, readback_rows=None)
        self.assertEqual(report["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
