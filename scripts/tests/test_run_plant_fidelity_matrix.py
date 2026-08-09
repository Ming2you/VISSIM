from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "run_plant_fidelity_matrix.ps1"
WATCHDOG = SCRIPT.with_name("run_real_world_single_watchdog_distributed_core15n41.ps1")
VBS = SCRIPT.with_name("run_real_world_stackelberg_controller.vbs")


@unittest.skipUnless(shutil.which("powershell"), "Windows PowerShell is required")
class PlantFidelityMatrixCliTests(unittest.TestCase):
    def test_matrix_passes_its_actual_watchdog_to_preflight(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(
            '$watchdog = Join-Path $PSScriptRoot "run_real_world_single_watchdog_distributed_core15n41.ps1"',
            source,
        )
        self.assertRegex(
            source,
            r"\$preflightBuilder\s+--repo\s+\$repo.*--watchdog\s+\$watchdog",
        )

    def test_watchdog_publishes_atomic_run_bound_evidence(self) -> None:
        source = WATCHDOG.read_text(encoding="utf-8")
        self.assertIn("function Write-JsonAtomic", source)
        self.assertIn("Archive-StaleVissimError $attempt", source)
        self.assertIn('schema_version = "vissim-error-evidence-v2.1"', source)
        self.assertIn('schema_version = "wall-time-profile-v2.1"', source)
        self.assertIn('schema_version = "run-artifact-manifest-v2.1"', source)
        self.assertIn("function Write-RunArtifactManifest", source)
        self.assertIn("decision_artifacts = $decisionArtifacts", source)
        self.assertIn("run_window = [ordered]@{", source)
        self.assertIn("artifact_roles = [ordered]@{", source)
        self.assertIn('filesystem_mtime_tolerance_sec = 2.0', source)
        self.assertIn('decision_artifacts = "simulation_output"', source)
        self.assertIn("Write-RunArtifactManifest $attempt $exitCode", source)
        self.assertIn("stale_pre_run = @($staleErrEvidence)", source)
        self.assertIn("preserved_generated_vbs_config", source)
        self.assertIn("version_triplet", source)
        self.assertIn("if ($done -and $exitCode -eq 0)", source)
        self.assertLess(source.index("Archive-StaleVissimError $attempt"), source.rindex("Start-Process -FilePath"))

    def test_vbs_emits_exact_reachable_com_failure_summary(self) -> None:
        source = VBS.read_text(encoding="utf-8")
        self.assertIn('WScript.Echo "COM_FAILURES=" & CStr(comFailures)', source)
        self.assertIn('WScript.Echo "OBSERVATION_FAILURES=" & CStr(observationFailures)', source)
        self.assertIn("Sub AbortVehicleObservation(simSec)", source)
        self.assertNotIn("If comFailures < signalFailures + observationFailures Then", source)
        self.assertIn("Or comFailures > 0 Then", source)

    def test_two_unreachable_optional_settings_do_not_count_as_com_failures(self) -> None:
        """실측으로 매 런 COM_FAILURES=2 를 만들던 두 설정을 제어 실패와 분리한다.

        실 런로그의 정확한 문구다.
          WARN=FAILED_SET_EVALUATION_ATT att=DatabaseConnection err=put_AttValue failed - module not active
          WARN=FAILED_SET_ATT att=SimSpeed value=0 err=Value 0 is lower than minimum value ... (Min: 0)

        둘 다 실패해도 의도가 이미 보장된다.
          DatabaseConnection="" 의 의도는 "결과를 DB 로 내보내지 않는다" 인데, 모듈이 비활성이면
          DB 출력 자체가 불가능하다. 실패가 곧 보장이다.
          SimSpeed=0 의 의도는 "최대 속도로 돌린다" 인데, 바로 앞줄 UseMaxSimSpeed=True 가 이미
          보장한다. 그 상태에서 SimSpeed 는 무시된다. 게다가 Vissim 은 Min 이 0 이라면서 0 을 거부한다.

        그런데 이 둘이 신호 액추에이션 실패와 같은 카운터에 들어가 RUN_INTEGRITY_FAILURE 를
        일으켰다. 게이트를 느슨하게 만들지 않으려면 **면제는 이 둘로 못박아야 한다.**
        범용 optional 탈출구를 만들면 다음 사람이 진짜 실패를 여기로 숨긴다.
        """
        source = VBS.read_text(encoding="utf-8")

        # 면제 경로는 별도 이름으로 존재하고, 건수는 버리지 않고 따로 센다.
        self.assertIn("Sub TrySetUnreachableAtt(obj, att, value, why)", source)
        self.assertIn("Sub TrySetUnreachableEvaluationAtt(att, value, why)", source)
        self.assertIn("optionalAttSkips = optionalAttSkips + 1", source)
        self.assertIn('WScript.Echo "OPTIONAL_ATT_SKIPS=" & CStr(optionalAttSkips)', source)

        # 면제 대상은 정확히 둘이다.
        self.assertEqual(source.count("TrySetUnreachableAtt "), 1)
        self.assertEqual(source.count("TrySetUnreachableEvaluationAtt "), 1)
        self.assertIn('TrySetUnreachableAtt Vissim.Simulation, "SimSpeed", 0,', source)
        self.assertIn('TrySetUnreachableEvaluationAtt "DatabaseConnection", "",', source)

        # 면제 경로는 comFailures 를 절대 올리지 않는다.
        for name in ("TrySetUnreachableAtt", "TrySetUnreachableEvaluationAtt"):
            start = source.index("Sub %s(" % name)
            body = source[start : source.index("End Sub", start)]
            self.assertNotIn("comFailures", body, f"{name} 이 comFailures 를 건드린다")

        # 의도를 보장하는 짝은 그대로 남아 있어야 한다. 이게 없으면 면제 근거가 사라진다.
        self.assertIn('TrySetAtt Vissim.Simulation, "UseMaxSimSpeed", True', source)

        # 나머지 액추에이션은 여전히 세어야 한다.
        self.assertIn('TrySetAtt sg, "SigState", "GREEN"', source)
        self.assertIn('TrySetEvaluationAtt "EvalOutDir", path', source)

    def run_script(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["RW_PYTHON_EXE"] = sys.executable
        dry_run = "-DryRun" in arguments
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            command = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
                "-RuntimeSourceManifest",
                str(root / "runtime-source.json"),
                "-AuditJsonManifest",
                str(root / "audit.json"),
                "-AuditMarkdownReport",
                str(root / "audit.md"),
                "-BaselineSnapshotManifest",
                str(root / "baseline.json"),
            ]
            if dry_run:
                command.extend([
                    "-PreflightManifest",
                    str(REPO / "outputs" / "preflight_manifest_v3.json"),
                    "-TopologyApproval",
                    str(REPO / "outputs" / "runtime_source_v2_1.json"),
                ])
            else:
                command.extend([
                    "-PreflightManifest",
                    str(root / "preflight.json"),
                    "-TopologyApproval",
                    str(root / "topology.json"),
                ])
            return subprocess.run(
                [*command, *arguments],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8", errors="replace",
                env=environment,
                timeout=180,
            )

    def test_baseline_only_dry_run_expands_exactly_one_case(self) -> None:
        result = self.run_script("-Strict", "-RequireComplete", "-BaselineOnly", "-DryRun")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("DRY_RUN "), 1)
        self.assertIn("demand=1", result.stdout)
        self.assertIn("seed=13", result.stdout)

    def test_full_dry_run_expands_nine_cases(self) -> None:
        result = self.run_script("-Strict", "-RequireComplete", "-DryRun")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("DRY_RUN "), 9)

    def test_require_complete_cannot_hide_failures_without_strict(self) -> None:
        result = self.run_script("-RequireComplete", "-DryRun")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("require both -Strict and -RequireComplete", result.stderr)

    def test_baseline_only_rejects_noncanonical_timing(self) -> None:
        result = self.run_script("-Strict", "-RequireComplete", "-BaselineOnly", "-SimPeriod", "600", "-DryRun")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SimPeriod=3600", result.stderr)

    def test_help_aliases_never_expand_or_run_cases(self) -> None:
        for flag in ("--help", "-?"):
            with self.subTest(flag=flag):
                result = self.run_script(flag)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("DRY_RUN ", result.stdout)
                self.assertNotIn("RUN fixed_", result.stdout)
                if flag == "--help":
                    self.assertIn("RUN THE STRICT VISSIM", result.stdout.upper())

    def test_nonempty_output_directory_is_rejected_before_vissim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "stale.txt").write_text("stale", encoding="utf-8")
            result = self.run_script(
                "-Strict",
                "-RequireComplete",
                "-BaselineOnly",
                "-OutDir",
                str(root),
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("new or empty", result.stderr)

    def test_generic_audit_precedes_baseline_validator_and_passes_exact_manifests(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        audit_call = source.index("& $python @auditArguments")
        validator_call = source.index("& $python -B $baselineValidator")
        self.assertLess(audit_call, validator_call)
        self.assertIn('"--json-out", $AuditJsonManifest', source)
        self.assertIn('"--markdown-out", $AuditMarkdownReport', source)
        self.assertIn("--runtime-source $RuntimeSourceManifest --preflight $PreflightManifest --audit $AuditJsonManifest", source)

    def test_audit_failure_cannot_leave_or_publish_baseline_pass_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            matrix = scripts / SCRIPT.name
            matrix.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            (scripts / "verify_runtime_source.py").write_text("import sys; raise SystemExit(0)\n", encoding="utf-8")
            (scripts / "build_preflight_manifest.py").write_text("import sys; raise SystemExit(0)\n", encoding="utf-8")
            (scripts / "audit_plant_fidelity.py").write_text("import sys; raise SystemExit(2)\n", encoding="utf-8")
            (scripts / "validate_baseline_snapshot.py").write_text(
                "from pathlib import Path; import sys; Path(sys.argv[sys.argv.index('--out')+1]).write_text('false-pass'); raise SystemExit(0)\n",
                encoding="utf-8",
            )
            (scripts / "run_real_world_single_watchdog_distributed_core15n41.ps1").write_text(
                "param([string]$Name,[string]$OutDir,[int]$SimPeriod,[int]$ControlIntervalSec,[int]$ControlStartSec,[string]$WarmupController,[string]$Controller,[int]$Seed,[int]$StateLogIntervalSec,[double]$DemandScale,[string]$AuditAnchorsSec,[string]$PreflightManifest,[int]$MaxAttempts); New-Item -ItemType Directory -Force -Path $OutDir | Out-Null; exit 0\n",
                encoding="utf-8",
            )
            out_dir = root / "run"
            baseline = root / "baseline.json"
            baseline.write_text("stale-pass", encoding="utf-8")
            audit_json = root / "audit.json"
            audit_markdown = root / "audit.md"
            audit_json.write_text("stale-audit", encoding="utf-8")
            audit_markdown.write_text("stale-audit", encoding="utf-8")
            environment = dict(os.environ)
            environment["RW_PYTHON_EXE"] = sys.executable
            result = subprocess.run(
                [
                    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(matrix),
                    "-Strict", "-RequireComplete", "-BaselineOnly", "-OutDir", str(out_dir),
                    "-RuntimeSourceManifest", str(root / "runtime.json"), "-PreflightManifest", str(root / "preflight.json"),
                    "-AuditJsonManifest", str(audit_json), "-AuditMarkdownReport", str(audit_markdown),
                    "-BaselineSnapshotManifest", str(baseline),
                ],
                check=False, capture_output=True, text=True, encoding="utf-8", errors="replace", env=environment, timeout=60,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Static/dynamic evidence aggregation failed", result.stderr)
            self.assertFalse(baseline.exists())
            self.assertFalse(audit_json.exists())
            self.assertFalse(audit_markdown.exists())


if __name__ == "__main__":
    unittest.main()
