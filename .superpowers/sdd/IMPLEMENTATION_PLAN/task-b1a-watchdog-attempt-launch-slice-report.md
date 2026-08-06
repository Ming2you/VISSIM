# B1a Slice 3A watchdog attempt/launch report

## Fix round 1 status

`IMPLEMENTED_PENDING_INDEPENDENT_REREVIEW`. This fix round addresses the prior
independent review's 2 Critical and 6 Important findings. No VISSIM COM process was
started; live COM correctness and runtime p95 remain `NOT_EVALUATED`.

### Finding disposition

| Finding | Disposition |
|---|---|
| Critical 1 required mode can wait forever | Fixed. Required and synthetic called paths use `Invoke-B1aMonitoredProcess`, which polls attempt-local progress, kills the child/tree plus non-baseline VISSIM processes on `StallSec`, performs bounded final waits, preserves failed attempts, and retries with fresh attempt directories/run IDs. |
| Critical 2 executed generated config not rechecked | Fixed. The attempt-local config copy is byte/hash checked at copy time, immediately before launch, and after termination; post-launch mismatch prevents success selection. |
| Important 1 `allowed_capture_times` over-authorized | Fixed. `Get-B1aSchedulePlan` mirrors VBS continuous-static, continuous-event, single-decision diagnostic, and stepwise schedules; audit anchors are authorized only when they are actual log epochs. |
| Important 2 dry-run created evidence and skipped request path | Fixed with honest limit. Matrix dry-run routes through watchdog planning and creates no runtime/preflight PASS evidence or attempt directory. In the current repo, missing future post-run/live replay producers make strict B1a dry-run planning `NOT_EVALUATED`, recorded per case without claiming PASS. |
| Important 3 arbitrary pre-populated attempt dir accepted | Fixed. `build_run_manifest_v2_1.py` rejects non-validate create when the run directory already exists. Request templates are staged outside the attempt; the producer exclusively creates the absent attempt directory. |
| Important 4 present-empty env cannot be restored | Fixed. Required/synthetic process launch no longer mutates parent process environment and no longer clears/reconstructs `ProcessStartInfo.EnvironmentVariables`; it applies child-only overrides to the inherited block. |
| Important 5 matrix legacy behavior removed | Fixed. Matrix allows either both `-Strict -RequireComplete` for B1a or neither for legacy mode; one-of-two remains rejected. |
| Important 6 process-level tests absent | Fixed. Added real process-level no-COM synthetic watchdog tests for retry, timeout, concurrent campaigns, child-only env, launch path, and config mutation; removed stale assumptions about dead helper paths. |

### Fix round 1 verification

| Command | Result |
|---|---:|
| `python -B -m unittest scripts.tests.test_b1a_watchdog_attempt_launch scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_run_plant_fidelity_matrix -v` | 56/56 PASS |
| `python -B -m unittest scripts.tests.test_b1a_core_provenance scripts.tests.test_b1a_vbs_capture_helpers_behavior scripts.tests.test_b1a_vbs_verified_capture_static plant.tests.test_vissim_strict_compiler plant.tests.test_vissim_strict_signal_program -v` | 40/43 PASS in sandbox; the 3 failures were `cscript` settings access denial |
| Same `scripts.tests.test_b1a_vbs_capture_helpers_behavior -v` outside sandbox | 3/3 PASS |
| `python -B -m unittest tests.test_vissim_stackelberg_adapter_fidelity -v` | 2/2 PASS |
| `python -B -m unittest plant.tests.test_vissim_strict_physical_projection plant.tests.test_vissim_strict_physical_projection_reference -v` | 50/50 PASS when run with projection package context |
| `git diff --check` | PASS, line-ending warnings only |
| Static search for obsolete required watchdog / old schedule helper / env clear / unbounded required wait | PASS, no matches |

### Honest gates

- Live VISSIM COM: `NOT_EVALUATED`.
- Required live execution: `NOT_EVALUATED` because later post-run v2.2 and live replay
  producers are still absent by design.
- Runtime p95: `NOT_EVALUATED`.
- Slice 3B/post-run/B1b: not implemented in this round.

## SDD status

`IMPLEMENTED_PENDING_INDEPENDENT_REVIEW`. This report covers only the watchdog
attempt identity and required prelaunch trust half. No VISSIM COM process was started.

## Changed files

- `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1`
- `scripts/run_plant_fidelity_matrix.ps1`
- `scripts/build_run_manifest_v2_1.py`
- `scripts/tests/test_b1a_watchdog_attempt_launch.py`
- `scripts/tests/test_b1a_run_manifest_slice.py`
- `scripts/tests/test_run_plant_fidelity_matrix.py`

## Required-mode contract implemented

- The watchdog now accepts `-B1aRequired`, `-TopologyApproval`, the existing
  `-PreflightManifest`, and `-B1aDryRun`. Legacy execution bypasses the new branch and
  keeps its prior filenames/cleanup behavior.
- One watchdog invocation creates a new `campaign_id`; each retry creates a fresh
  `run_id` and exclusive `<OutDir>/<campaign_id>/attempt_<NN>_<run_id>/` directory.
  Required attempts keep their own decisions, CSVs, logs, request/template, manifest
  creation/validation results, and preserved generated config. They never call the
  legacy shared decision cleanup/archive helpers.
- Required prelaunch uses `build_run_manifest_v2_1.py` for both canonical request
  completion and immutable manifest create/reload. The new request-template entrypoint
  lives in that already pinned producer, so PowerShell does not duplicate canonical
  JSON, semantic hashing, approval replay, or schema validation.
- The original generated config is the manifest-bound configuration input. It is copied
  once through a same-directory temporary file, byte-compared and hash-compared, then
  the attempt-local copy is passed to VBS. A validate-only manifest reload runs before
  launch and after process exit, thereby rehashing every closed producer/configuration
  binding before selection.
- The allowed capture schedule is the sorted unique union of first/repeated VBS decision
  times, an in-range control-start time, and finite in-range audit anchors.
- `RW_FORCE_STEPWISE`, `RW_AUDIT_ANCHORS_SEC`, `RW_PYTHON`, `RW_RUN_ID`,
  `RW_RUN_MANIFEST_PATH`, `RW_RUN_MANIFEST_SHA256`, `RW_B1A_REQUIRED`, and
  `RW_QUALIFICATION_MODE` are saved and restored in one `try/finally`, preserving both
  absent and present-empty values.
- Strict matrix invocations explicitly pass required mode, preflight, and topology
  approval. Its dry-run records a failed future-preflight as
  `DRY_RUN_PREFLIGHT_NOT_EVALUATED` instead of producing live PASS evidence.

## Verification

All commands ran from `C:\tmp\vissim-pstack-controller` with
`C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

| Command | Result |
|---|---:|
| PowerShell parser + `python -m unittest scripts.tests.test_b1a_watchdog_attempt_launch scripts.tests.test_run_plant_fidelity_matrix` | 18 PASS |
| `python -m unittest scripts.tests.test_b1a_run_manifest_slice` | 34 PASS |
| `python -m unittest scripts.tests.test_b1a_core_provenance scripts.tests.test_b1a_vbs_capture_helpers_behavior scripts.tests.test_b1a_vbs_verified_capture_static plant.tests.test_vissim_strict_compiler plant.tests.test_vissim_strict_signal_program` | 43 PASS |
| `python -m unittest tests.test_vissim_stackelberg_adapter_fidelity` with no `PYTHONPATH` override | 2 PASS |
| `python -m unittest plant.tests.test_vissim_strict_physical_projection plant.tests.test_vissim_strict_physical_projection_reference` | 50 PASS |
| `git diff --check` | PASS (only pre-existing CRLF conversion warnings) |

The VBS behavior suite initially hit sandbox-only `cscript` settings access denial; the
same fake-COM/no-VISSIM suite was rerun outside that sandbox and passed as part of the
43-test command. A combined adapter/projection command was discarded because adding
`plant` to `PYTHONPATH` shadows NumSim's `src`; the adapter test was rerun in its normal
environment and passed.

## Remaining honest limits and deferred work

- Current checked-in real required preflight can remain FAIL because the later
  `build_run_artifact_manifest_v2_2.py` and
  `build_projection_live_evidence_v2_2.py` producers are deliberately absent. Required
  mode therefore fails before cscript/COM rather than claiming a live PASS.
- VBS capture companion transaction, projection timing receipt, normal adapter
  projection-reference invocation, post-run v2.2 artifacts/replay, and B1b dynamics are
  outside Slice 3A.
- Live VISSIM COM correctness and runtime p95 remain `NOT_EVALUATED`.

## Self-review concerns for the independent reviewer

- Confirm the request-template extension is acceptable as part of the existing pinned
  `run_manifest_producer` role and has no unintended CLI ambiguity.
- Stress-test the PowerShell exclusive directory path under concurrent processes and
  inspect exact environment restoration with absent/empty values using a fake launcher.
- Verify that the later VBS slice consumes `RW_QUALIFICATION_MODE` under the exact name
  selected here and that required VBS paths remain attempt-local after companion support
  is added.

## Fix round 2 status

`IMPLEMENTED_PENDING_INDEPENDENT_REREVIEW`. This round addresses the single blocking
fix-round-1 rereview finding: production watchdog request templates emitted integral
`allowed_capture_times` as JSON integers, while the immutable run-manifest validator
requires JSON doubles.

### Fix round 2 changes

- `Get-B1aSchedulePlan` still computes sorted unique integral epoch values, but stores
  `allowed_capture_times` as doubles for the request contract.
- `Write-B1aJsonTemplate` now preserves the `allowed_capture_times` JSON numeric
  contract when PowerShell would otherwise collapse integral doubles to `1`/`30`.
  The emitted template decodes in Python as floats such as `1.0` while retaining exact
  integral epoch values.
- `build_run_manifest_v2_1.py --validate-template-stdin` now shares the exact
  request-to-manifest validation kernel: template -> canonical request -> in-memory
  manifest -> `validate_run_manifest`, with no publication and no PASS evidence.
- Added a no-COM integration test that uses the actual production PowerShell helper and
  template writer, then runs the pinned producer request build, manifest create, and
  validate-only reload path against the PASS synthetic fixture.
- Added a negative no-write assertion that integer `allowed_capture_times` are rejected
  by the same dry-run validation kernel without creating manifest/result artifacts.

### Fix round 2 verification

| Command | Result |
|---|---:|
| `python -B -m unittest scripts.tests.test_b1a_run_manifest_slice.ProducerCliTests.test_watchdog_production_template_schedule_creates_and_validates_manifest -v` | PASS |
| `python -B -m unittest scripts.tests.test_b1a_watchdog_attempt_launch scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_run_plant_fidelity_matrix -v` | 57/57 PASS |
| `git diff --check` | PASS, line-ending warnings only |

No VISSIM/COM process was started. Live COM correctness, required live execution, and
runtime p95 remain `NOT_EVALUATED`.
