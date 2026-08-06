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
                encoding="utf-8",
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
                check=False, capture_output=True, text=True, encoding="utf-8", env=environment, timeout=60,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Static/dynamic evidence aggregation failed", result.stderr)
            self.assertFalse(baseline.exists())
            self.assertFalse(audit_json.exists())
            self.assertFalse(audit_markdown.exists())


if __name__ == "__main__":
    unittest.main()
