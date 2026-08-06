# B1a Watchdog Shared-Parent Race Rereview

Scope: `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1`,
`scripts/tests/test_b1a_watchdog_attempt_launch.py`, and the new progress line.
No production or test files were edited during this review.

## Verdict

APPROVED

Severity counts:

- Critical: 0
- Important: 0
- Minor: 0

## Findings

No findings.

## Review Notes

- The former `Test-Path` then `New-Item` race on shared required `OutDir` is closed. `Invoke-B1aRequiredWatchdog` now validates workspace containment before and after calling `New-B1aSharedDirectory`, and the helper creates the directory with `New-Item -Force` then rechecks that the result is a real directory and not a reparse point.
- The same shared-parent race is closed for synthetic `fixtureOut`. The synthetic harness now uses `New-B1aSharedDirectory` for the parent output root before creating the campaign directory.
- Shared parents are intentionally idempotent, while campaign and attempt directories remain exclusive. Required mode still creates the campaign directory with `New-B1aExclusiveDirectory`, each attempt directory is derived from a fresh `runId`, and the attempt-local `decisions` directory is also exclusive. Synthetic mode likewise uses exclusive campaign and attempt directories.
- File, reparse-point, and path containment safety is not weakened in the required path. `OutDir` still goes through `Get-B1aWorkspaceRelativeDestination` before and after creation, and both shared/exclusive helpers reject reparse-point final directories. The synthetic fixture path is external-test-only and still rejects non-directory/reparse-point output roots after creation.
- I do not see stale evidence or cross-attempt sharing introduced by this fix. Required staged request files remain campaign-scoped with attempt/run-specific names and are moved into the exclusive attempt directory. Synthetic observations may share fixture-level files by test design, but run artifacts and config copies remain attempt-local.

## Evidence

- Required shared parent: `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:555` to `:558`
- Shared helper: `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:237` to `:245`
- Required exclusive campaign/attempt/decision directories: `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:558`, `:561`, `:584`
- Synthetic shared parent and exclusive campaign/attempt directories: `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:629` to `:632`
- Concurrent regression coverage: `scripts/tests/test_b1a_watchdog_attempt_launch.py:267` to `:299`
- Progress ledger line reviewed: `.superpowers/sdd/IMPLEMENTATION_PLAN/progress.md:53`

## Verification

Command:

```powershell
$py='C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'; for($i=1; $i -le 10; $i++){ & $py -B -m unittest scripts.tests.test_b1a_watchdog_attempt_launch.B1aWatchdogAttemptLaunchStaticTests.test_synthetic_concurrent_same_outdir_invocations_do_not_share_attempts; if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE } }; & $py -B -m unittest scripts.tests.test_b1a_watchdog_attempt_launch
```

Result:

- Concurrent same-outdir regression: 10/10 repeated runs PASS.
- Full `test_b1a_watchdog_attempt_launch`: 10/10 PASS.
- VISSIM/COM: not invoked.

APPROVED
