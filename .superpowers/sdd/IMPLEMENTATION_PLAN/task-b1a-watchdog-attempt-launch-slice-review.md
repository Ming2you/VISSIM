# B1a Slice 3A independent requirements and code-quality review

## Verdict

`CHANGES_REQUIRED`

- Critical: 2
- Important: 6
- Minor: 0
- SDD status: `REVIEWED_CHANGES_REQUIRED`
- Live VISSIM COM and runtime p95: `NOT_EVALUATED`

The no-COM regression suite passed 52/52 and `git diff --check` passed, but the
focused watchdog tests do not exercise several required production paths. Adversarial
no-COM probes reproduced invalid schedules, stale run-directory acceptance, and PASS
evidence written by dry-run.

## Findings

### Critical 1: required mode bypasses the stall watchdog and can wait forever

- Evidence: `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:33`
  accepts `StallSec`, but the required path calls an unbounded
  `$proc.WaitForExit()` at `:380`. The only `HasExited`/progress/idle loop and
  `Kill-Vissim` timeout are in the legacy path at `:737-771`.
- Reproduction/exploit: launch required mode with a child that remains alive while
  producing no new state/log output. Even with `-StallSec 1 -MaxAttempts 2`, control
  remains at line 380; the process is not killed and attempt 2 is never created.
- Violated requirement: required mode must retain `StallSec` kill/retry behavior and
  must not use an indefinite `WaitForExit`.
- Smallest safe correction: move the production progress polling/idle timeout into a
  shared called-path helper, use attempt-local outputs as progress sources, kill the
  cscript process tree and VISSIM on timeout, perform a bounded final wait, mark the
  attempt failed, and continue with a new run ID/directory.

### Critical 2: the bytes actually passed as generated config are not rechecked

- Evidence: the copy hash is captured but never used after
  `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:349`; the copy is
  the file executed at `:367`; post-exit line `:381` only reloads the manifest, whose
  configuration binding is the original `$vbsConfig`, not `$configCopy`.
- Reproduction/exploit: mutate `attempt_*/generated_config.vbs` after line 349 and
  before cscript reads it, or while the child runs. The original manifest-bound config
  remains unchanged, validate-only succeeds, and lines `:383-384` can select the
  attempt although unbound bytes were executed.
- Violated requirement: immediately before launch and after exit, verify every exact
  source/config byte, including the attempt-local executed copy.
- Smallest safe correction: compare the copy to both the saved pre-copy hash and the
  original source bytes immediately before `Start-Process` and again after termination;
  any mismatch must prevent launch/selection and remain recorded as a failed attempt.

### Important 1: `allowed_capture_times` does not model the actual VBS modes

- Evidence: `Get-B1aAllowedCaptureTimes` unconditionally emits time 1, every control
  multiple, `ControlStartSec`, and every parseable anchor at
  `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:265-279`. The VBS
  instead selects continuous-static, continuous-event, or stepwise at
  `scripts/run_real_world_stackelberg_controller.vbs:374-408`; their decision/log
  schedules differ at `:411-551`, and an audit anchor is written only from an actual
  `LogStateCsv` event at `:1641-1647`.
- Reproduction: executing the real PowerShell helper with period 180, interval 60,
  start 95, and anchors `30,31,90,150` returned the identical list
  `[1,30,31,60,90,95,120,150,180]` for continuous-static, stackelberg event, and
  force-stepwise modes. For no-control static the actual permitted union is
  `[1,30,90,95,150]`; anchor 31 is not a log event and 60/120/180 are not decisions.
  For stackelberg/stepwise, start 95 is not a decision and anchor 31 is not logged.
- Violated requirement: enumerate exact mode-specific decision and actual audit-log
  events, sorted and unique; malformed/non-event anchors must not be authorized.
- Smallest safe correction: implement one pure schedule function that mirrors all VBS
  mode predicates, initial decision, repeated/single control rules, state-log cadence,
  final-period logging, and exact integer anchor matching. Add table-driven behavioral
  tests for no-control static, diagnostic static, diagnostic single-decision,
  diagnostic repeated-event, stackelberg, and `ForceStepwise`.

### Important 2: dry-run neither validates the real request path nor remains evidence-free

- Evidence: direct watchdog dry-run returns at
  `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:328-330`, before
  request-template construction/validation at `:332-365`. Matrix dry-run invokes the
  runtime-source and preflight producers at
  `scripts/run_plant_fidelity_matrix.ps1:90-103`, then skips the watchdog entirely at
  `:140-143`.
- Reproduction: an actual matrix baseline dry-run returned zero, created no run
  directory, but wrote `runtime.json` with status `PASS` (`preflight.json` was `FAIL`).
  Thus `B1aDryRun = $DryRun` in the splat is dead for matrix dry-run and PASS evidence
  is produced.
- Violated requirement: dry-run must validate required path propagation and manifest
  request construction while creating no attempt, manifest, PASS evidence, cscript,
  or COM process.
- Smallest safe correction: route matrix dry-run through a no-write watchdog planning
  entry point that calls the same pure schedule/path/request validator in memory. Do
  not invoke evidence producers or write/replace evidence outputs in dry-run.

### Important 3: CLI context accepts an arbitrary pre-populated run directory

- Evidence: `_prepare_cli_result_context` treats any existing directory as watchdog
  owned at `scripts/build_run_manifest_v2_1.py:215-221`; `_request_context` then permits
  it via `precreated_run_directory` at `:168-174`. No ownership receipt, emptiness, or
  allowed-sibling check ties that directory to this invocation.
- Reproduction: using the official fixture, precreate the declared attempt directory
  with `stale_preexisting.bin`, then call the producer with the watchdog's
  `--workspace-root/--run-directory/--creation-result-output` tuple. It returned 0,
  preserved the stale file, and created `run_manifest_v2_1.json`.
- Violated requirement: the request-template CLI extension must not weaken create-once
  ownership or allow stale/pre-populated run directories.
- Smallest safe correction: stage the template outside the attempt and let the pinned
  producer exclusively create the absent attempt directory, or require a producer-
  created create-once ownership receipt and reject every unexpected pre-existing child.
  Remove the unconditional `run_dir.exists()` ownership assertion.

### Important 4: present-empty environment values cannot be restored by this mechanism

- Evidence: lines
  `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:368-376` save values
  with `GetEnvironmentVariable` and restore them with `SetEnvironmentVariable`. Under
  the production Windows PowerShell/.NET runtime, setting a process variable to `""`
  results in an absent variable; a no-COM API probe returned `is_null=true` after the
  empty assignment. The code therefore cannot preserve the required absent versus
  present-empty distinction. No called-path test covers it.
- Reproduction/exploit: start the watchdog from a process environment containing an
  explicitly empty `RW_RUN_ID` or another managed key. The save/restore API collapses
  that state to absent after the launch transaction.
- Violated requirement: restore absent and present-empty exactly on normal and all
  exceptional paths.
- Smallest safe correction: do not mutate the watchdog process environment. Launch the
  child with a cloned explicit `ProcessStartInfo` environment block containing the
  attempt overrides, leaving the parent environment untouched. Test inherited absent,
  empty, and nonempty values at process level.

### Important 5: matrix legacy/non-strict behavior was removed

- Evidence: `scripts/run_plant_fidelity_matrix.ps1:38-40` unconditionally throws unless
  both `-Strict` and `-RequireComplete` are supplied.
- Reproduction: invoke the matrix with its default/legacy CLI; it exits before case
  expansion instead of following the previous legacy path.
- Violated requirement: strict/complete must pass explicit B1a inputs, while legacy or
  non-strict invocations remain legacy.
- Smallest safe correction: reject only a mismatched one-of-two strict flag state;
  when neither flag is present, retain the original non-B1a invocation and filenames.
  Pass B1a parameters only when both flags are present.

### Important 6: mandatory process-level watchdog tests are absent

- Evidence: `scripts/tests/test_b1a_watchdog_attempt_launch.py:15-81` checks source
  strings; its only executable helper test at `:83-127` does not invoke the watchdog.
  Matrix tests do not invoke it in dry-run because production code continues at
  `scripts/run_plant_fidelity_matrix.ps1:140-143`. The existing manifest concurrency
  test covers only file publication, not same-name watchdog campaigns, retries,
  process monitoring, or environment ownership.
- Impact: concurrent same-name isolation, failed/killed retry preservation, absent vs
  empty environment restoration, and argument/`Start-Process` exception cleanup are
  not established. The critical indefinite wait and dry-run defects passed all 52
  focused tests.
- Violated requirement: process-level tests are mandatory for concurrency and
  environment ownership and must execute production called paths rather than decoys.
- Smallest safe correction: extract the production attempt/process transaction into a
  shared called helper and exercise it with a harmless synthetic child. Test two
  concurrent same-name watchdog processes, hung-child timeout, fail-then-success retry,
  config mutation, all environment states, and launch exceptions. A fake child must be
  restricted to `synthetic_fixture` and must never emit live PASS evidence.

## Requirement audit

| Requirement | Result | Basis |
|---|---|---|
| Required CLI parameters and explicit approval/preflight | PASS | Parameters and required checks are on the called path. |
| One campaign, fresh run ID/attempt directory, no shared cleanup | PASS | GUID identities and exclusive directories are present; process concurrency remains below. |
| Concurrent same-name invocations and retry preservation | NOT_EVALUATED | No process-level test; timeout retry is currently impossible because of Critical 1. |
| Exact Windows path/case/reparse/containment in live prelaunch | PASS | Final request construction delegates to the exact shared Python resolvers. |
| Dry-run exact path/request propagation | FAIL | Returns/skips before request validation. |
| Config create-once and pre-copy equality | PASS | The copy helper uses create-new temp publication and byte/hash comparison. |
| Exact executed config before launch and after exit | FAIL | Critical 2. |
| Mode-specific `allowed_capture_times` | FAIL | Important 1. |
| Exact 12 producer and 8 input roles | PASS | Closed constants and template maps match the required role universes. |
| Duplicate adapter/policy/preflight bindings | PASS | Shared producer/validator enforces the equality constraints. |
| Immutable manifest create and strict reload | PASS | Official producer is used before launch and reloaded validate-only. |
| Request CLI create-once run ownership | FAIL | Important 3. |
| Environment restore: absent/nonempty | PASS | One `try/finally` encloses mutation and launch. |
| Environment restore: present-empty | FAIL | The production API collapses an empty value to absent. |
| Environment restore on argument/launch exceptions | NOT_EVALUATED | The structure has `finally`, but no called-path process test exercises the exception matrix. |
| Stall kill and bounded retry | FAIL | Critical 1. |
| Matrix strict/complete propagation | PASS | Required switch, approval, and preflight are passed in production mode. |
| Matrix legacy behavior | FAIL | Important 5. |
| Dry-run creates no PASS evidence/process/artifact | FAIL | Important 2; no cscript/COM was started, but PASS evidence was written. |
| Live VISSIM COM correctness | NOT_EVALUATED | No live COM run was performed. |
| Runtime p95 | NOT_EVALUATED | No qualified timing campaign exists. |

## Verification performed

- `python -B -m unittest scripts.tests.test_b1a_watchdog_attempt_launch scripts.tests.test_run_plant_fidelity_matrix scripts.tests.test_b1a_run_manifest_slice`: 52 PASS.
- `git diff --check`: PASS, with line-ending warnings only.
- Executed the production schedule helper for three VBS modes: reproduced one identical,
  over-authorized schedule.
- Invoked the official manifest producer against a pre-populated attempt fixture:
  reproduced successful stale-directory acceptance.
- Ran the real matrix dry-run in a temporary directory: reproduced a PASS runtime-source
  artifact with no run directory and no COM launch.

Final verdict: `CHANGES_REQUIRED` (Critical 2, Important 6, Minor 0).
SDD status: `REVIEWED_CHANGES_REQUIRED`.
