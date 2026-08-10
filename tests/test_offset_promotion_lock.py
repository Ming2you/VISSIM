# v3 N4-7 - offset 승격 삼중 잠금(D-offset-enable)을 코드로 못박는다
"""offset 은 승격되기 전까지 플랜트에 도달하면 안 된다.

계획 원문(IMPLEMENTATION_PLAN_V3_LEAN.md N4-7).

    D-offset-enable = D-core(같은 신호 profile + 같은 topology SHA-256)
                    ∧ N9 offset 효과·순위 게이트
                    ∧ N8-4 런타임 게이트

    - D-core PASS 전까지 production writer 는 `intent_only` 다. 의도만 기록하고 COM 에 쓰지 않는다.
    - D-core PASS 후에도 격리된 시험 harness 의 test-only writer 만 강제 offset arm 을 낼 수 있다.
    - 승격되지 않은 profile 의 nonzero offset 기록은 fail-closed 로 거부한다.

잠금을 푸는 조건은 **증거 산출물**이다. 사람이 상수를 고쳐서 푸는 길을 남기지 않는다.
"""

from __future__ import annotations

import csv
import os
import subprocess
import tempfile
import types
import unittest
from pathlib import Path

from evaluation.controllers import offset_promotion
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from scripts import build_experiment_matrix_v3 as matrix


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_real_world_stackelberg_controller.vbs"

PROFILE = "core15n41-sgplan-abc123"
TOPOLOGY = "f" * 64


def passing_evidence() -> dict[str, dict[str, object]]:
    return {
        name: {
            "status": "PASS",
            "signal_profile_id": PROFILE,
            "topology_sha256": TOPOLOGY,
        }
        for name in offset_promotion.LOCK_NAMES
    }


class LockVerdictTests(unittest.TestCase):
    def test_no_evidence_means_locked_and_the_reason_names_what_is_missing(self) -> None:
        verdict = offset_promotion.evaluate({name: None for name in offset_promotion.LOCK_NAMES})
        self.assertFalse(verdict["promoted"])
        self.assertEqual(verdict["writer"], offset_promotion.WRITER_INTENT_ONLY)
        self.assertEqual(verdict["status"], offset_promotion.NOT_EVALUATED)
        locks = {lock["name"]: lock for lock in verdict["locks"]}
        self.assertEqual(set(locks), set(offset_promotion.LOCK_NAMES))
        for lock in locks.values():
            self.assertEqual(lock["status"], offset_promotion.NOT_EVALUATED)
            self.assertTrue(lock["needs"])

    def test_repository_state_today_is_locked_because_d_core_is_blocked(self) -> None:
        """실제 산출물로 판정한다. 오늘은 D-core 가 BLOCKED 라 잠겨 있어야 한다."""
        verdict = offset_promotion.evaluate()
        self.assertFalse(verdict["promoted"])
        self.assertEqual(verdict["writer"], offset_promotion.WRITER_INTENT_ONLY)

    def test_all_three_locks_pass_with_one_profile_opens_production(self) -> None:
        verdict = offset_promotion.evaluate(passing_evidence())
        self.assertTrue(verdict["promoted"])
        self.assertEqual(verdict["writer"], offset_promotion.WRITER_PRODUCTION)
        self.assertEqual(verdict["status"], offset_promotion.PASS)

    def test_one_missing_lock_keeps_it_closed(self) -> None:
        for name in offset_promotion.LOCK_NAMES:
            evidence = passing_evidence()
            evidence[name] = None
            with self.subTest(missing=name):
                self.assertFalse(offset_promotion.evaluate(evidence)["promoted"])

    def test_a_blocked_d_core_keeps_it_closed(self) -> None:
        evidence = passing_evidence()
        evidence["d_core"]["status"] = offset_promotion.BLOCKED
        verdict = offset_promotion.evaluate(evidence)
        self.assertFalse(verdict["promoted"])
        locks = {lock["name"]: lock for lock in verdict["locks"]}
        self.assertEqual(locks["d_core"]["status"], offset_promotion.BLOCKED)

    def test_evidence_from_different_profiles_does_not_compose(self) -> None:
        """세 증거가 같은 신호 profile / topology 를 가리켜야 한다."""
        evidence = passing_evidence()
        evidence["n9_offset_effect"]["signal_profile_id"] = "some-other-profile"
        self.assertFalse(offset_promotion.evaluate(evidence)["promoted"])

        evidence = passing_evidence()
        evidence["n8_4_runtime"]["topology_sha256"] = "0" * 64
        self.assertFalse(offset_promotion.evaluate(evidence)["promoted"])

    def test_evidence_without_a_profile_binding_is_not_evaluated(self) -> None:
        evidence = passing_evidence()
        del evidence["d_core"]["signal_profile_id"]
        verdict = offset_promotion.evaluate(evidence)
        self.assertFalse(verdict["promoted"])
        locks = {lock["name"]: lock for lock in verdict["locks"]}
        self.assertEqual(locks["d_core"]["status"], offset_promotion.NOT_EVALUATED)

    def test_caller_supplied_profile_must_match_the_evidence(self) -> None:
        evidence = passing_evidence()
        self.assertTrue(
            offset_promotion.evaluate(
                evidence, signal_profile_id=PROFILE, topology_sha256=TOPOLOGY
            )["promoted"]
        )
        self.assertFalse(
            offset_promotion.evaluate(evidence, signal_profile_id="other")["promoted"]
        )


class DeclaredWriterTests(unittest.TestCase):
    def test_absent_declaration_is_intent_only(self) -> None:
        locked = offset_promotion.evaluate({name: None for name in offset_promotion.LOCK_NAMES})
        writer = offset_promotion.resolve_writer(
            {"real_world_signal_control": {"enabled": True}}, verdict=locked
        )
        self.assertEqual(writer, offset_promotion.WRITER_INTENT_ONLY)

    def test_a_test_harness_may_declare_the_test_only_writer(self) -> None:
        locked = offset_promotion.evaluate({name: None for name in offset_promotion.LOCK_NAMES})
        writer = offset_promotion.resolve_writer(
            {"real_world_signal_control": {"enabled": True, "offset_writer": "test_only"}},
            verdict=locked,
        )
        self.assertEqual(writer, offset_promotion.WRITER_TEST_ONLY)

    def test_production_is_not_declarable_from_a_config(self) -> None:
        """설정 파일이 production 을 선언할 수 있으면 삼중 잠금이 장식이다."""
        locked = offset_promotion.evaluate({name: None for name in offset_promotion.LOCK_NAMES})
        with self.assertRaises(offset_promotion.OffsetPromotionError):
            offset_promotion.resolve_writer(
                {"real_world_signal_control": {"offset_writer": "production"}}, verdict=locked
            )

    def test_an_unknown_declaration_is_refused_rather_than_ignored(self) -> None:
        locked = offset_promotion.evaluate({name: None for name in offset_promotion.LOCK_NAMES})
        with self.assertRaises(offset_promotion.OffsetPromotionError):
            offset_promotion.resolve_writer(
                {"real_world_signal_control": {"offset_writer": "on"}}, verdict=locked
            )

    def test_promotion_overrides_a_test_only_declaration(self) -> None:
        promoted = offset_promotion.evaluate(passing_evidence())
        writer = offset_promotion.resolve_writer(
            {"real_world_signal_control": {"offset_writer": "test_only"}}, verdict=promoted
        )
        self.assertEqual(writer, offset_promotion.WRITER_PRODUCTION)


def _control(offsets: dict[str, float], diagnostics: dict[str, float] | None = None):
    return types.SimpleNamespace(
        green_times={},
        offsets=dict(offsets),
        diagnostics=dict(diagnostics or {}),
    )


def _cfg():
    return types.SimpleNamespace(
        freeway_follower=types.SimpleNamespace(vsl_set=[80.0, 100.0, 120.0])
    )


def _mapping():
    return {
        "segments": [],
        "signals": [
            {"id": "SC1", "sc_no": 1, "major_maps_to": "p2"},
            {"id": "SC5", "sc_no": 5, "major_maps_to": "p2"},
        ],
        "ramp_meters": [],
    }


def _signal_offsets(path: Path) -> dict[str, float]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["id"]: float(row["offset"])
            for row in csv.DictReader(handle)
            if row["kind"] == "signal"
        }


class ActionCsvOffsetWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._ramp = adapter.physical_ramp_actions
        adapter.physical_ramp_actions = lambda *a, **k: {}
        self.addCleanup(self._restore)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.csv_path = Path(self.tmp.name) / "action.csv"

    def _restore(self) -> None:
        adapter.physical_ramp_actions = self._ramp

    def _write(self, control, writer: str) -> dict[str, float]:
        adapter.write_action_csv(
            self.csv_path,
            control,
            _cfg(),
            _mapping(),
            lambda *a, **k: 100.0,
            {"controller_status": "ok"},
            {"real_world_signal_control": {"enabled": True}},
            offset_writer=writer,
        )
        return _signal_offsets(self.csv_path)

    def test_the_default_writer_is_intent_only(self) -> None:
        """호출자가 아무 말도 하지 않으면 offset 은 플랜트에 가지 않는다."""
        adapter.write_action_csv(
            self.csv_path,
            _control({"SC1": 17.0, "SC5": 33.0}),
            _cfg(),
            _mapping(),
            lambda *a, **k: 100.0,
            {"controller_status": "ok"},
            {"real_world_signal_control": {"enabled": True}},
        )
        self.assertEqual(_signal_offsets(self.csv_path), {"SC1": 0.0, "SC5": 0.0})

    def test_intent_only_zeroes_the_optimizer_offset(self) -> None:
        offsets = self._write(
            _control({"SC1": 17.0, "SC5": 33.0}), offset_promotion.WRITER_INTENT_ONLY
        )
        self.assertEqual(offsets, {"SC1": 0.0, "SC5": 0.0})

    def test_production_writer_carries_the_optimizer_offset(self) -> None:
        """되돌림 증명. 잠금을 빼면(=production) 위 검사는 실패한다."""
        offsets = self._write(
            _control({"SC1": 17.0, "SC5": 33.0}), offset_promotion.WRITER_PRODUCTION
        )
        self.assertEqual(offsets, {"SC1": 17.0, "SC5": 33.0})

    def test_test_only_writer_emits_the_forced_arm_not_the_optimizer_offset(self) -> None:
        control = _control(
            {"SC1": 17.0, "SC5": 33.0},
            {"diagnostic_forced_signal_offset_sec": 30.0},
        )
        self.assertEqual(
            self._write(control, offset_promotion.WRITER_TEST_ONLY),
            {"SC1": 30.0, "SC5": 30.0},
        )

    def test_test_only_writer_without_a_forced_arm_writes_nothing(self) -> None:
        offsets = self._write(
            _control({"SC1": 17.0, "SC5": 33.0}), offset_promotion.WRITER_TEST_ONLY
        )
        self.assertEqual(offsets, {"SC1": 0.0, "SC5": 0.0})

    def test_a_forced_arm_without_a_declared_harness_stops_the_run(self) -> None:
        """조용히 offset 0 으로 도는 것이 가장 나쁜 결과다 - 그 런은 arm 이 아니다.

        g6 의 `diagnostic-signal-offset30` 같은 강제 arm 은 격리된 harness 선언이 있어야
        한다. 선언 없이 부르면 0 으로 뭉개서 "돌긴 돌았는데 레버가 없는" 자료를
        만드는 대신 런을 세운다.
        """
        control = _control({}, {"diagnostic_forced_signal_offset_sec": 30.0})
        with self.assertRaises(offset_promotion.OffsetPromotionError):
            self._write(control, offset_promotion.WRITER_INTENT_ONLY)

    def test_a_zero_forced_arm_is_not_an_arm_and_passes(self) -> None:
        control = _control({"SC1": 17.0}, {"diagnostic_forced_signal_offset_sec": 0.0})
        self.assertEqual(
            self._write(control, offset_promotion.WRITER_INTENT_ONLY),
            {"SC1": 0.0, "SC5": 0.0},
        )

    def test_the_suppressed_intent_is_recorded_not_discarded(self) -> None:
        control = _control({"SC1": 17.0, "SC5": 33.0})
        locked = offset_promotion.evaluate({name: None for name in offset_promotion.LOCK_NAMES})
        recorded = offset_promotion.action_metadata(
            control, offset_promotion.WRITER_INTENT_ONLY, locked
        )
        self.assertEqual(recorded["offset_writer"], offset_promotion.WRITER_INTENT_ONLY)
        self.assertEqual(recorded["offset_production_writes"], 0.0)
        self.assertEqual(recorded["offset_intent_suppressed_signals"], 2.0)
        self.assertEqual(recorded["offset_intent_max_abs_sec"], 33.0)


class MatrixDerivesFromTheLockTests(unittest.TestCase):
    def test_matrix_constants_are_derived_not_hand_written(self) -> None:
        """N9 행렬의 offset 상태/writer 가 잠금 판정과 같은 출처여야 한다."""
        self.assertEqual(matrix.LEVER_STATUS["offset"], offset_promotion.matrix_lever_status())
        self.assertEqual(matrix.LEVER_WRITER["offset"], offset_promotion.matrix_lever_writer())

    def test_today_that_means_blocked_and_test_only(self) -> None:
        self.assertEqual(matrix.LEVER_STATUS["offset"], "BLOCKED")
        self.assertEqual(matrix.LEVER_WRITER["offset"], "test_only")

    def test_promotion_would_flip_both_without_editing_the_matrix(self) -> None:
        promoted = offset_promotion.evaluate(passing_evidence())
        self.assertEqual(offset_promotion.matrix_lever_status(promoted), "PLANNED")
        self.assertEqual(
            offset_promotion.matrix_lever_writer(promoted), offset_promotion.WRITER_PRODUCTION
        )


class RunnerSecondLockTests(unittest.TestCase):
    """러너는 권위가 아니라 **두 번째** 자물쇠다 - 선언하지 않은 런은 offset 을 못 쓴다."""

    def setUp(self) -> None:
        self.runner = RUNNER.read_text(encoding="utf-8-sig")

    def test_the_runner_defaults_to_intent_only(self) -> None:
        self.assertIn("Dim RW_OFFSET_WRITER", self.runner)
        self.assertIn('RW_OFFSET_WRITER = "intent_only"', self.runner)

    def test_the_rejection_reuses_the_existing_all_or_nothing_gate(self) -> None:
        self.assertIn("Function OffsetPromotionRejectReason", self.runner)
        self.assertIn("planReason = OffsetPromotionRejectReason(rowSignalOffset)", self.runner)
        self.assertIn(
            "signalRows <> expectedSignalRows Or sgRows <> expectedSgRows Or invalidRows > 0 "
            'Or planReason <> "" Then',
            self.runner,
        )

    def _run_reject_reason(self, writer: str, offsets: dict[str, float]) -> str:
        start = self.runner.index("Function OffsetPromotionRejectReason")
        end = self.runner.index("End Function", start) + len("End Function")
        body = self.runner[start:end]
        lines = [
            "Option Explicit",
            "Dim RW_OFFSET_WRITER, offsets, key, result",
            'RW_OFFSET_WRITER = "%s"' % writer,
            'Set offsets = CreateObject("Scripting.Dictionary")',
        ]
        for key, value in offsets.items():
            lines.append("offsets.Add \"%s\", %r" % (key, float(value)))
        lines.append("result = OffsetPromotionRejectReason(offsets)")
        lines.append('WScript.Echo "REASON=[" & result & "]"')
        lines.append("")
        lines.append(body)
        script = Path(self.tmpdir) / "probe.vbs"
        script.write_text("\n".join(lines), encoding="utf-8")
        proc = subprocess.run(
            ["cscript", "//Nologo", str(script)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        marker = "REASON=["
        line = [row for row in proc.stdout.splitlines() if row.startswith(marker)][0]
        return line[len(marker):].rstrip("]")

    def test_runner_rejects_a_nonzero_offset_that_was_never_promoted(self) -> None:
        if os.name != "nt":
            self.skipTest("cscript is Windows-only")
        with tempfile.TemporaryDirectory() as tmpdir:
            self.tmpdir = tmpdir
            self.assertEqual(self._run_reject_reason("intent_only", {"1": 0.0, "5": 0.0}), "")
            reason = self._run_reject_reason("intent_only", {"1": 0.0, "5": 12.0})
            self.assertIn("OFFSET_NOT_PROMOTED", reason)
            self.assertIn("sc=5", reason)
            # 선언한 시험 harness 는 통과한다.
            self.assertEqual(self._run_reject_reason("test_only", {"1": 0.0, "5": 12.0}), "")
            # 알 수 없는 값은 조용히 통과하지 않는다.
            self.assertIn(
                "OFFSET_WRITER_UNKNOWN", self._run_reject_reason("on", {"1": 0.0})
            )


if __name__ == "__main__":
    unittest.main()
