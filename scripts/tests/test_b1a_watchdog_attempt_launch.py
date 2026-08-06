from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
WATCHDOG = REPO / "scripts" / "run_real_world_single_watchdog_distributed_core15n41.ps1"
MATRIX = REPO / "scripts" / "run_plant_fidelity_matrix.ps1"


class B1aWatchdogAttemptLaunchStaticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = WATCHDOG.read_text(encoding="utf-8")
        self.matrix = MATRIX.read_text(encoding="utf-8")

    def required_body(self) -> str:
        start = self.source.index("function Invoke-B1aRequiredWatchdog")
        end = self.source.index("if ($B1aRequired)", start)
        return self.source[start:end]

    def test_required_cli_and_matrix_propagation_are_explicit(self) -> None:
        self.assertIn("[switch]$B1aRequired", self.source)
        self.assertIn("[string]$TopologyApproval", self.source)
        self.assertIn("[string]$PreflightManifest", self.source)
        self.assertIn("TopologyApproval = $TopologyApproval", self.matrix)
        self.assertIn("B1aRequired = $true", self.matrix)
        self.assertIn("B1aDryRun = $DryRun", self.matrix)

    def test_required_attempts_are_campaign_scoped_and_never_share_legacy_cleanup(self) -> None:
        body = self.required_body()
        self.assertIn("$campaignId = [guid]::NewGuid().ToString('N')", body)
        self.assertIn("$runId = [guid]::NewGuid().ToString('N')", body)
        self.assertIn("for ($attempt = 1", body)
        self.assertGreaterEqual(body.count("$runId = [guid]::NewGuid().ToString('N')"), 2)
        self.assertIn("attempt_{0:00}_{1}", body)
        self.assertIn("New-B1aExclusiveDirectory", body)
        self.assertNotIn("Clear-DecisionDir", body)
        self.assertNotIn("Archive-AttemptOutputs", body)

    def test_required_prelaunch_uses_pinned_request_and_attempt_local_config(self) -> None:
        body = self.required_body()
        self.assertIn("Copy-B1aConfigCreateOnce $vbsConfig $configCopy", body)
        self.assertIn("--request-template $templateStage --write-request", body)
        self.assertIn("--request $requestStage --workspace-root $repo", body)
        self.assertIn("--validate-only", body)
        self.assertIn("$manifestHash = (Get-FileHash", body)
        self.assertIn("(Q $configCopy)", body)
        self.assertIn("Invoke-B1aMonitoredProcess", body)
        self.assertIn("Assert-B1aConfigMatch $vbsConfig $configCopy $configHash 'immediately before launch'", body)
        self.assertIn("Assert-B1aConfigMatch $vbsConfig $configCopy $configHash 'after termination'", body)
        self.assertLess(body.index("B1a manifest creation failed"), body.index("Invoke-B1aMonitoredProcess"))

    def test_required_environment_is_one_transaction_with_exact_contract(self) -> None:
        body = self.required_body()
        for name in (
            "RW_RUN_ID",
            "RW_RUN_MANIFEST_PATH",
            "RW_RUN_MANIFEST_SHA256",
            "RW_B1A_REQUIRED",
            "RW_QUALIFICATION_MODE",
            "RW_FORCE_STEPWISE",
            "RW_AUDIT_ANCHORS_SEC",
            "RW_PYTHON",
        ):
            self.assertIn(name, body)
        helper_start = self.source.index("function Invoke-B1aMonitoredProcess")
        helper_end = self.source.index("function Get-B1aPython", helper_start)
        helper = self.source[helper_start:helper_end]
        self.assertIn("ProcessStartInfo", helper)
        self.assertIn("UseShellExecute = $false", helper)
        self.assertIn("EnvironmentVariables.Remove", helper)
        self.assertNotIn("EnvironmentVariables.Clear()", helper)
        self.assertNotIn("SetEnvironmentVariable", body)

    def test_capture_schedule_is_bounded_unique_and_contains_anchors(self) -> None:
        self.assertIn("function Get-B1aSchedulePlan", self.source)
        schedule_start = self.source.index("function Get-B1aSchedulePlan")
        schedule_end = self.source.index("function Write-B1aJsonTemplate", schedule_start)
        schedule = self.source[schedule_start:schedule_end]
        self.assertIn("[void]$decisionTimes.Add(1)", schedule)
        self.assertIn("$DecisionIntervalSec", schedule)
        self.assertIn("AuditAnchorsSec", schedule)
        self.assertIn("$logTimes.Contains($time)", schedule)
        self.assertIn("Sort-Object", schedule)

    @unittest.skipUnless(shutil.which("powershell"), "Windows PowerShell is required")
    def test_attempt_helpers_create_once_copy_bytes_and_sort_schedule_without_com(self) -> None:
        helper_start = self.source.index("function Get-B1aWorkspaceRelativeFile")
        helper_end = self.source.index("if ($B1aRequired)", helper_start)
        helpers = self.source[helper_start:helper_end]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "source config.vbs"
            copied = root / "copied config.vbs"
            config.write_bytes(b"alpha\x00beta\r\n")
            harness = root / "helpers.ps1"
            harness.write_text(
                "\n".join(
                    (
                        "$ErrorActionPreference = 'Stop'",
                        f"$repo = '{root}'",
                        "$ControlIntervalSec = 60",
                        "$SimPeriod = 180",
                        "$ControlStartSec = 90",
                        "$AuditAnchorsSec = '90,30,30,150'",
                        helpers,
                        "$first = New-B1aExclusiveDirectory (Join-Path $repo 'attempt') 'attempt'",
                        "$duplicateRejected = $false",
                        "try { New-B1aExclusiveDirectory $first 'attempt' | Out-Null } catch { $duplicateRejected = $true }",
                        f"$hash = Copy-B1aConfigCreateOnce '{config}' '{copied}'",
                        "$static = Get-B1aSchedulePlan 180 60 'no-control' 95 30 '30,31,90,150' $false",
                        "$event = Get-B1aSchedulePlan 180 60 'stackelberg' 95 30 '30,31,90,150' $false",
                        "$stepwise = Get-B1aSchedulePlan 180 60 'stackelberg' 95 30 '30,31,90,150' $true",
                        "$payload = [ordered]@{ duplicate_rejected=$duplicateRejected; copied_hash=$hash; copied_size=(Get-Item -LiteralPath '"
                        + str(copied)
                        + "').Length; static=$static.allowed_capture_times; event=$event.allowed_capture_times; stepwise=$stepwise.allowed_capture_times; allowed_capture_times=$event.allowed_capture_times }",
                        "$jsonPath = Join-Path $repo 'schedule_contract.json'",
                        "Write-B1aJsonTemplate $jsonPath $payload",
                        "Get-Content -Raw -LiteralPath $jsonPath",
                    )
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["duplicate_rejected"])
        self.assertEqual(payload["copied_size"], 12)
        self.assertEqual(payload["static"], [1, 30, 90, 95, 150])
        self.assertEqual(payload["event"], [1, 30, 60, 90, 120, 150, 180])
        self.assertEqual(payload["stepwise"], [1, 30, 60, 90, 120, 150, 180])
        self.assertTrue(all(isinstance(value, float) for value in payload["allowed_capture_times"]))

    def write_synthetic_fixture(
        self,
        root: Path,
        *,
        mode: str,
        max_attempts: int = 1,
        stall_sec: int = 2,
    ) -> Path:
        config = root / "source config.vbs"
        child = root / "synthetic_child.ps1"
        spec = root / f"fixture_{mode}.json"
        observation = root / f"observation_{mode}.json"
        config.write_text("' config\n", encoding="utf-8")
        child.write_text(
            "\n".join(
                (
                    "param([string]$Mode,[string]$Observation)",
                    "$ErrorActionPreference = 'Stop'",
                    "$attempt = [int]$env:RW_SYNTHETIC_ATTEMPT",
                    "$attemptDir = $env:RW_SYNTHETIC_ATTEMPT_DIR",
                    "if ($Mode -eq 'hang' -and $attempt -eq 1) { Start-Sleep -Seconds 30; exit 0 }",
                    "if ($Mode -eq 'retry' -and $attempt -eq 1) { 'failed first' | Set-Content -LiteralPath (Join-Path $attemptDir 'first_failed.txt'); exit 7 }",
                    "if ($Mode -eq 'mutate-config') { Add-Content -LiteralPath $env:RW_SYNTHETIC_CONFIG_COPY -Value 'mutated'; exit 0 }",
                    "$payload = [ordered]@{",
                    "  mode = $Mode",
                    "  attempt = $attempt",
                    "  run_id = $env:RW_RUN_ID",
                    "  qualification = $env:RW_QUALIFICATION_MODE",
                    "  b1a_required_present = [bool]$env:RW_B1A_REQUIRED",
                    "  inherited_empty_present = $true",
                    "  inherited_empty_value = [string]$env:RW_INHERITED_EMPTY",
                    "}",
                    "$payload | ConvertTo-Json -Compress | Set-Content -LiteralPath $Observation -Encoding UTF8",
                    "exit 0",
                )
            ),
            encoding="utf-8",
        )
        payload = {
            "schema_version": "b1a-watchdog-synthetic-fixture-v1",
            "qualification": {"mode": "synthetic_fixture"},
            "out_dir": str(root / "out"),
            "config_source": str(config),
            "child_file": shutil.which("powershell") or "powershell",
            "child_arguments": f"-NoProfile -ExecutionPolicy Bypass -File \"{child}\" -Mode {mode} -Observation \"{observation}\"",
            "stall_sec": stall_sec,
            "max_attempts": max_attempts,
        }
        spec.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        return spec

    def run_synthetic_watchdog(self, spec: Path, *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["RW_PYTHON_EXE"] = sys.executable
        environment["RW_INHERITED_EMPTY"] = ""
        return subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(WATCHDOG),
                "-Name",
                "synthetic",
                "-B1aSyntheticFixtureSpec",
                str(spec),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            timeout=timeout,
        )

    @unittest.skipUnless(shutil.which("powershell"), "Windows PowerShell is required")
    def test_synthetic_called_path_retries_timeout_and_preserves_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            retry_spec = self.write_synthetic_fixture(root, mode="retry", max_attempts=2)
            retry = self.run_synthetic_watchdog(retry_spec)
            self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
            self.assertIn("SYNTHETIC_FIXTURE_NOT_EVALUATED", retry.stdout)
            attempts = sorted((root / "out").glob("*/attempt_*"))
            self.assertEqual(len(attempts), 2)
            self.assertTrue((attempts[0] / "attempt_failure.txt").exists())

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hang_spec = self.write_synthetic_fixture(root, mode="hang", max_attempts=2, stall_sec=1)
            hang = self.run_synthetic_watchdog(hang_spec, timeout=90)
            self.assertEqual(hang.returncode, 0, hang.stdout + hang.stderr)
            attempts = sorted((root / "out").glob("*/attempt_*"))
            self.assertEqual(len(attempts), 2)
            self.assertIn("watchdog_timeout", (attempts[0] / "attempt_failure.txt").read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("powershell"), "Windows PowerShell is required")
    def test_synthetic_called_path_env_and_config_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            env_spec = self.write_synthetic_fixture(root, mode="env")
            env_result = self.run_synthetic_watchdog(env_spec)
            self.assertEqual(env_result.returncode, 0, env_result.stdout + env_result.stderr)
            observed = json.loads((root / "observation_env.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(observed["qualification"], "synthetic_fixture")
            self.assertFalse(observed["b1a_required_present"])
            self.assertEqual(observed["inherited_empty_value"], "")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mutate_spec = self.write_synthetic_fixture(root, mode="mutate-config")
            mutate = self.run_synthetic_watchdog(mutate_spec)
            self.assertNotEqual(mutate.returncode, 0)
            failure_files = list((root / "out").glob("*/attempt_*/attempt_failure.txt"))
            self.assertEqual(len(failure_files), 1)
            self.assertIn("config hash mismatch", failure_files[0].read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("powershell"), "Windows PowerShell is required")
    def test_synthetic_concurrent_same_outdir_invocations_do_not_share_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec_a = self.write_synthetic_fixture(root, mode="env")
            spec_b = self.write_synthetic_fixture(root, mode="retry", max_attempts=2)
            processes = [
                subprocess.Popen(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(WATCHDOG),
                        "-Name",
                        "synthetic",
                        "-B1aSyntheticFixtureSpec",
                        str(spec),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    env={**os.environ, "RW_PYTHON_EXE": sys.executable},
                )
                for spec in (spec_a, spec_b)
            ]
            outputs = [process.communicate(timeout=90) for process in processes]
            self.assertTrue(all(process.returncode == 0 for process in processes), outputs)
            campaigns = sorted(path for path in (root / "out").iterdir() if path.is_dir())
            self.assertEqual(len(campaigns), 2)
            run_ids = [attempt.name.split("_", 2)[2] for attempt in (root / "out").glob("*/attempt_*")]
            self.assertEqual(len(run_ids), len(set(run_ids)))

    @unittest.skipUnless(shutil.which("powershell"), "Windows PowerShell is required")
    def test_watchdog_parses_without_invoking_vissim(self) -> None:
        command = (
            "$tokens=$null;$errors=$null;"
            f"[System.Management.Automation.Language.Parser]::ParseFile('{WATCHDOG}',[ref]$tokens,[ref]$errors)|Out-Null;"
            "if($errors.Count){$errors|% Message;exit 1}"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
