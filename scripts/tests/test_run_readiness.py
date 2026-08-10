# 실 VISSIM 런 착수 준비도를 판정하는 도구의 계약 테스트 (v3)
"""무엇이 갖춰졌고 무엇이 막고 있는지를 **코드가 판정하게** 한다.

지금 v3 의 절반 이상이 실 런에 걸려 있다 — N4-6 · N4-7 · N6 · N8-1 · N8-4 · N1b · N9 · N10.
런을 돌리기 전에 갖춰야 할 것과 런이 무엇을 푸는지가 계획 여러 절에 흩어져 있어, 사람이
순서를 짜려면 문서를 다시 읽어야 한다.

이 도구는 그 판정을 자동화한다. 목적은 두 가지다.

**착수 전 차단.** 사슬(runtime_source / preflight / approval)이 PASS 가 아니거나 봉인된
명세가 없으면 런을 시작하면 안 된다. 1,620 셀을 돌린 뒤에 아는 것은 되돌릴 수 없다.

**순서 제시.** 부모 런(N5)이 N6 캘리브레이션과 N9 의 eps_J_vissim 을 공급하므로 먼저다.
그 의존을 코드로 표현해 두면 순서를 기억에 의존하지 않는다.

준비되지 않은 것을 준비된 것처럼 세지 않는다 — 여기서도 미측정은 통과가 아니다.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

import run_readiness  # noqa: E402


class StageOrderTests(unittest.TestCase):
    def test_stages_are_declared_in_dependency_order(self) -> None:
        names = [stage["name"] for stage in run_readiness.STAGES]
        self.assertEqual(names[0], "N5_parent_runs")
        # N6 은 N5 의 관측을 쓰고, N9 는 N5 의 eps_J_vissim 을 쓴다.
        self.assertLess(names.index("N5_parent_runs"), names.index("N6_calibration"))
        self.assertLess(names.index("N5_parent_runs"), names.index("N9_paired_matrix"))
        # N1b 는 N8-4 런타임 계약에 걸려 있다.
        self.assertLess(names.index("N8_4_runtime_contract"), names.index("N1b_mpc_capture"))
        # N10 승격은 마지막이다.
        self.assertEqual(names[-1], "N10_promotion")

    def test_every_stage_declares_a_command(self) -> None:
        for stage in run_readiness.STAGES:
            with self.subTest(stage=stage["name"]):
                self.assertTrue(stage["command"], stage["name"])

    def test_only_the_terminal_stage_unblocks_nothing(self) -> None:
        """중간 단계가 아무것도 안 푼다면 순서에 넣을 이유가 없다는 뜻이다."""
        terminal = [s["name"] for s in run_readiness.STAGES if not s["unblocks"]]
        self.assertEqual(terminal, ["N10_promotion"])


class PreconditionTests(unittest.TestCase):
    def test_a_missing_chain_artifact_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = run_readiness.evaluate(Path(directory))
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(report["blocking"])

    def test_a_failing_chain_artifact_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outputs").mkdir()
            for name in run_readiness.CHAIN_ARTIFACTS:
                (root / "outputs" / name).write_text(
                    json.dumps({"status": "FAIL"}), encoding="utf-8"
                )
            report = run_readiness.evaluate(root)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(
                any("status" in reason for reason in report["blocking"]), report["blocking"]
            )

    def test_a_sealed_spec_must_carry_its_seal(self) -> None:
        """봉인이 없는 명세로 런을 시작하면 사후 조정을 막을 수 없다."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outputs").mkdir()
            for name in run_readiness.CHAIN_ARTIFACTS:
                (root / "outputs" / name).write_text(
                    json.dumps({"status": "PASS"}), encoding="utf-8"
                )
            for name in run_readiness.SEALED_SPECS:
                (root / "outputs" / name).write_text(json.dumps({}), encoding="utf-8")
            report = run_readiness.evaluate(root)
            self.assertTrue(
                any("seal" in reason for reason in report["blocking"]), report["blocking"]
            )


class RealRepositoryTests(unittest.TestCase):
    """지금 저장소가 실제로 런을 시작할 수 있는 상태인지 판정한다."""

    def test_report_is_produced_for_the_real_repository(self) -> None:
        report = run_readiness.evaluate(REPO)
        self.assertIn(report["status"], {"READY", "BLOCKED"})
        self.assertEqual(len(report["stages"]), len(run_readiness.STAGES))

    def test_chain_artifacts_are_currently_passing(self) -> None:
        """사슬이 깨져 있으면 런 준비 이전에 그것부터 고쳐야 한다."""
        for name in run_readiness.CHAIN_ARTIFACTS:
            path = REPO / "outputs" / name
            with self.subTest(artifact=name):
                self.assertTrue(path.is_file(), f"{name} 없음")
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload.get("status"), "PASS", name)

    def test_sealed_specs_exist_with_seals(self) -> None:
        for name in run_readiness.SEALED_SPECS:
            path = REPO / "outputs" / name
            with self.subTest(spec=name):
                self.assertTrue(path.is_file(), f"{name} 없음")
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(payload.get("seal_sha256"), name)


class CliTests(unittest.TestCase):
    def test_main_reports_and_exits_by_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "readiness.json"
            code = run_readiness.main(["--repo", str(REPO), "--out", str(out)])
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(code, 0 if payload["status"] == "READY" else 1)
            self.assertEqual(payload["schema_version"], run_readiness.SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
