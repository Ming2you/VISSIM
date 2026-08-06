# B1a Slice 3A fix round 2 fresh independent rereview

## Verdict

`APPROVED`

- Critical: 0
- Important: 0
- Minor: 0
- SDD status: `REREVIEW_APPROVED`
- Live VISSIM COM: `NOT_EVALUATED`
- Runtime p95: `NOT_EVALUATED`

I reread the Slice 3A brief, the governing live-trust architecture brief, the
original independent review, the fix-round-1 rereview, the implementer/fix report,
and the current watchdog, matrix, manifest-producer, validator, and focused tests.
The original 2 Critical + 6 Important findings are addressed on the inspected
no-COM production paths. The fix1 Critical numeric-type finding is also addressed:
the production watchdog template now emits `allowed_capture_times` as decoded JSON
doubles, and both dry-run and normal producer flows pass through the shared
request-to-manifest validation kernel.

## Fix1 Critical numeric-type finding

`ADDRESSED`.

- `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:267-335`
  still computes sorted unique schedule epochs from integral VBS times, but stores
  `allowed_capture_times` as `[double]` values.
- `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:340-363`
  rewrites the JSON `allowed_capture_times` array with invariant decimal tokens
  such as `1.0`, avoiding PowerShell's integral-looking double serialization.
- `scripts/build_run_manifest_v2_1.py:107-118` now validates dry-run templates by
  building the canonical request, constructing the in-memory manifest, and calling
  `validate_run_manifest(...)`.
- `plant/src/vissim_strict/run_evidence.py:713-724` still rejects non-float capture
  times, so integer JSON tokens remain a hard failure.
- `scripts/tests/test_b1a_run_manifest_slice.py:1183-1288` uses the production
  PowerShell helper/template writer, verifies Python-decoded floats, creates the
  manifest through the official producer, then validate-only reloads it.
- The same test mutates `allowed_capture_times` to `[1, 60]` and proves the no-write
  dry-run validation rejects it without publishing manifest/result files.

## Original finding disposition

| Original finding | Result | Evidence |
|---|---|---|
| Critical 1: required mode can wait forever | `ADDRESSED` | `Invoke-B1aMonitoredProcess` at `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:444-492` polls attempt-local progress, applies `StallSec`, kills the process tree/VISSIM, performs bounded waits, and reports timeout. Synthetic called-path retry/timeout tests pass. |
| Critical 2: executed generated config not rechecked | `ADDRESSED` | `Assert-B1aConfigMatch` at `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:366-379` compares source/copy hashes and bytes; required launch checks before launch, immediately before launch, and after termination at `:574-585`. |
| Important 1: schedule over-authorizes actual VBS modes | `ADDRESSED` | `Get-B1aSchedulePlan` at `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:267-335` separates static, event, single-decision diagnostic, and stepwise schedules; anchors are admitted only if they are actual log epochs. Numeric JSON contract is now covered by fix2. |
| Important 2: dry-run skips request path and writes PASS evidence | `ADDRESSED` | Direct watchdog dry-run calls `Invoke-B1aTemplateValidationNoWrite` at `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:538-542`; matrix dry-run routes into watchdog planning and skips runtime/preflight producers at `scripts/run_plant_fidelity_matrix.ps1:91-155`. My temp matrix dry-run created no OutDir. |
| Important 3: pre-populated run directory accepted | `ADDRESSED` | `scripts/build_run_manifest_v2_1.py:168-182` and `:210-219` reject non-validate create when the run directory already exists; focused producer tests pass. |
| Important 4: present-empty env cannot be restored | `ADDRESSED` | Required/synthetic launch now uses child-only `ProcessStartInfo.EnvironmentVariables` overrides at `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:444-463`, so the parent environment is not mutated. Synthetic process test observes inherited empty env. |
| Important 5: matrix legacy/non-strict removed | `ADDRESSED` | `scripts/run_plant_fidelity_matrix.ps1:38-40` rejects only one-of-two strict flags; legacy neither-strict-nor-complete path remains available, and B1a arguments are only added in B1a mode. |
| Important 6: process-level watchdog tests absent | `ADDRESSED` | `scripts/tests/test_b1a_watchdog_attempt_launch.py` exercises synthetic called paths for timeout/retry preservation, config mutation, inherited empty env, and concurrent campaigns. |

## Focused verification

- `python -B -m unittest scripts.tests.test_b1a_watchdog_attempt_launch scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_run_plant_fidelity_matrix -v`
  - Result: 57/57 PASS.
- `git diff --check`
  - Result: PASS, with line-ending warnings only.
- Matrix no-COM probe:
  - Command shape: strict/complete baseline dry-run with a temp `OutDir`.
  - Result: exited through `DRY_RUN_B1A_NOT_EVALUATED` because the checked-out repo
    currently lacks `outputs/topology_approval_v2_1.json`; the temp `OutDir` was not
    created, and no cscript/COM/PASS artifact was produced.

## Regression scan

No new Critical or Important regressions were found in the inspected areas:
watchdog timeout/retry, attempt identity, config copy binding, child environment
ownership, official manifest create + validate-only reload, dry-run no-write
validation, matrix strict/legacy split, or synthetic fixture isolation.

Live COM correctness, required live execution, and runtime p95 remain honestly
`NOT_EVALUATED` until the later post-run v2.2/live-replay producers and a real
qualified VISSIM campaign exist.

Final verdict: `APPROVED` (Critical 0, Important 0, Minor 0).
SDD status: `REREVIEW_APPROVED`.
