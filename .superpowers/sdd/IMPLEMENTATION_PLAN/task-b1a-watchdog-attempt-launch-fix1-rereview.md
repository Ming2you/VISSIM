# B1a Slice 3A fix round 1 independent rereview

## Verdict

`CHANGES_REQUIRED`

- Critical: 1
- Important: 0
- Minor: 0
- SDD status: `REREVIEW_CHANGES_REQUIRED`
- Live VISSIM COM: `NOT_EVALUATED`
- Runtime p95: `NOT_EVALUATED`

The original Critical 1-2 and Important 2-6 are addressed on the inspected no-COM
paths. Original Important 1 is not fully addressed: the watchdog now computes a
mode-specific schedule, but it serializes `allowed_capture_times` as JSON integers
while the immutable run-manifest validator requires JSON doubles. The required live
path therefore fails manifest creation before any COM launch for any non-empty
schedule, and dry-run does not catch that because it validates only the request
template shape.

## Findings

### Critical 1: required-mode `allowed_capture_times` are emitted as ints that the required manifest rejects

- Evidence:
  - `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:292-335`
    builds `decisionTimes`, `logTimes`, `anchorTimes`, and `allowed` as
    `HashSet[Int64]`, then returns `allowed_capture_times = @($allowed | Sort-Object)`.
  - `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:482-484`
    copies that array directly into the request template.
  - `scripts/build_run_manifest_v2_1.py:435-460` makes dry-run validation call
    `build_request_from_template`, which only reaches request validation and never
    publishes/revalidates a run manifest.
  - `plant/src/vissim_strict/run_evidence.py:713-721` rejects any
    `allowed_capture_times` item that is not a Python `float`.
  - `scripts/tests/test_b1a_watchdog_attempt_launch.py:139-141` currently expects
    integer JSON output from the PowerShell schedule helper, while
    `scripts/tests/test_b1a_run_manifest_slice.py:514` intentionally rejects integer
    capture times in the manifest validator.
- Reproduction:
  - I ran the focused suite:
    `python -B -m unittest scripts.tests.test_b1a_watchdog_attempt_launch scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_run_plant_fidelity_matrix -v`
    and it passed 56/56, showing the regression is not covered by the current tests.
  - I then mutated the official run-manifest fixture to use
    `allowed_capture_times = [1, 30, 60]`, recomputed the semantic hash, and called
    `validate_run_manifest(...)`. It failed with:
    `RunManifestValidationError: allowed_capture_times must contain finite nonnegative JSON doubles`.
- Impact:
  - Required non-dry-run calls reach
    `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:539`, where the
    producer publishes and validates the immutable manifest. Any normal non-empty
    schedule from the current helper will be rejected before launch.
  - Required dry-run can still print `B1A_REQUIRED_DRY_RUN_NOT_EVALUATED` after
    `:518-520` because the dry-run validator never exercises the same manifest
    creation/strict reload contract.
- Required fix:
  - Emit `allowed_capture_times` as decoded JSON doubles from the watchdog request
    template, and update the PowerShell schedule tests to expect `1.0`, `30.0`, etc.
  - Add a no-COM integration test that feeds the actual watchdog-produced template into
    the real producer create/validate path with a PASS fixture, not only
    `--validate-template-stdin`.

## Original Finding Disposition

| Original finding | Rereview result | Evidence |
|---|---|---|
| Critical 1: required mode can wait forever | `ADDRESSED` | `Invoke-B1aMonitoredProcess` at `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:424-470` polls progress, kills on idle timeout, performs bounded waits, and drains stdout/stderr. Synthetic process tests at `scripts/tests/test_b1a_watchdog_attempt_launch.py:220-238` exercise timeout and retry preservation. |
| Critical 2: executed generated config not rechecked | `ADDRESSED` | `Assert-B1aConfigMatch` at `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:346-356` compares source/copy hashes and bytes. Required launch calls it before launch and after termination at `:554-565`; synthetic mutation test covers the after-termination failure at `scripts/tests/test_b1a_watchdog_attempt_launch.py:241-259`. |
| Important 1: `allowed_capture_times` does not model actual VBS modes | `NOT_ADDRESSED` | Mode-specific schedule logic exists at `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:267-335`, and it matches the inspected VBS control/log branches at `scripts/run_real_world_stackelberg_controller.vbs:411-551`; however, the emitted numeric type is incompatible with the immutable run-manifest validator as described above. |
| Important 2: dry-run skips request path and writes PASS evidence | `ADDRESSED_WITH_LIMIT` | Matrix no longer runs runtime/preflight producers during dry-run (`scripts/run_plant_fidelity_matrix.ps1:91` is guarded by `-not $DryRun`), and it invokes the watchdog planning path at `:138-155`. The remaining limit is the Critical 1 dry-run coverage gap: template validation does not catch manifest-publish type failures. |
| Important 3: arbitrary pre-populated run directory accepted | `ADDRESSED` | Both request and CLI contexts reject non-validate pre-existing run directories at `scripts/build_run_manifest_v2_1.py:168-182` and `:210-219`; test coverage is at `scripts/tests/test_b1a_run_manifest_slice.py:839-847`. |
| Important 4: present-empty environment values cannot be restored | `ADDRESSED` | Required/synthetic launch uses child-only `ProcessStartInfo.EnvironmentVariables` overrides at `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:424-441` and no longer mutates parent process variables in the required body. The process test observes inherited empty child env at `scripts/tests/test_b1a_watchdog_attempt_launch.py:194-250`. |
| Important 5: matrix legacy/non-strict behavior removed | `ADDRESSED` | Matrix accepts either both strict flags or neither at `scripts/run_plant_fidelity_matrix.ps1:38-40`, and B1a arguments are attached only in B1a mode at `:131-136`. |
| Important 6: mandatory process-level watchdog tests absent | `ADDRESSED_WITH_LIMIT` | Synthetic process tests now exercise retry, timeout, config mutation, inherited env, and concurrent campaigns through the called watchdog path at `scripts/tests/test_b1a_watchdog_attempt_launch.py:194-294`. The limit is that no process-level test currently proves actual watchdog schedule output can create a strict run manifest, which is the Critical 1 gap. |

## Verification Run

- `python -B -m unittest scripts.tests.test_b1a_watchdog_attempt_launch scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_run_plant_fidelity_matrix -v`
  - Result: 56/56 PASS.
- `git diff --check`
  - Result: PASS, with line-ending warnings only.
- Additional no-COM manifest-type probe:
  - Result: integer `allowed_capture_times` are rejected by `validate_run_manifest`
    with `allowed_capture_times must contain finite nonnegative JSON doubles`.

## New Regression Scan

No additional Critical/Important regressions were found in bounded monitoring,
attempt ownership, config source/copy validation, child environment ownership,
matrix legacy propagation, or synthetic fixture live-PASS suppression. The only
blocking regression is the schedule numeric type and the corresponding dry-run/test
coverage hole.

Final verdict: `CHANGES_REQUIRED` (Critical 1, Important 0, Minor 0).
SDD status: `REREVIEW_CHANGES_REQUIRED`.
