# B1a VBS fix-round-1 independent rereview

## Verdict

**FAIL**

Original finding disposition:

- Critical: **ADDRESSED 3 / NOT_ADDRESSED 0**
- Important: **ADDRESSED 1 / NOT_ADDRESSED 1**
- Minor: **ADDRESSED 1 / NOT_ADDRESSED 0**

New fix/current-delta findings:

- Critical: **0**
- Important: **1**

Supported-version live VISSIM COM: **NOT_EVALUATED**

## Original findings

### Critical 1 - Stepwise recurring capture time

**ADDRESSED.**

RunStepwiseMode now executes RunSingleStep and persistence validation before
RunControllerDecision stepNo at
scripts/run_real_world_stackelberg_controller.vbs:423-428. The decision then
applies signals, ramp meters, and incident state for the next interval at lines
430-432, matching the continuous modes' observe-at-time-t ordering.

The caller-order test is at
scripts/tests/test_b1a_vbs_verified_capture_static.py:177-195. The original
reproducer now reports decision_precedes_step=False:

    $s=Get-Content -Raw scripts\run_real_world_stackelberg_controller.vbs
    $b=[regex]::Match($s,'(?ms)^Sub RunStepwiseMode\(\).*?^End Sub$').Value
    $d=$b.IndexOf('RunControllerDecision stepNo')
    $r=$b.IndexOf('Vissim.Simulation.RunSingleStep',$b.IndexOf('For stepNo'))
    "decision_precedes_step=$($d -lt $r)"

### Critical 2 - vehicle_records placement

**ADDRESSED BY NORMATIVE ADJUDICATION.**

The amended brief explicitly requires root-level vehicle_records as a sibling of
local_observation and forbids nesting it under local_observation
(task-b1a-brief.md:68-70). The current writer closes local_observation at VBS line
1513 and emits vehicle_records afterward at lines 1514-1516. The static placement
test is at test_b1a_vbs_verified_capture_static.py:198-204, and parsed-output checks
are at test_b1a_vbs_capture_helpers_behavior.py:392-394.

Placement therefore conforms to the current brief. The original location finding
is not open.

### Critical 3 - VBS stopped-map/core parity

**ADDRESSED.**

For every counted link, ScanVehicleState initializes the corresponding stopped-map
key to zero before optionally incrementing it
(run_real_world_stackelberg_controller.vbs:1832-1835). Production VBS helpers emit
the fake-COM scan result, and the test passes that parsed envelope without repair to
normalize_vehicle_records at
test_b1a_vbs_capture_helpers_behavior.py:409-420.

Observed in the 11-test B1a run:

- full_network_link_counts = {"1": 1, "1220012103": 1}
- full_network_link_stopped_counts = {"1": 1, "1220012103": 0}
- core normalization PASS

### Important 1 - Reachable capture-failure counters

**ADDRESSED.**

Both scan callers invoke AbortVehicleObservation before opening/publishing a state
(VBS lines 1474-1476 and 1626-1628). AbortVehicleObservation increments one
observation failure, emits OBSERVATION_FAILURES and COM_FAILURES, and exits 13
(lines 1453-1458). RecordVehicleCaptureFailure remains the sole capture-side COM
increment. The ambiguous end-of-run max synthesis was removed.

The executable failure harness at
test_b1a_vbs_capture_helpers_behavior.py:317-356 observed exactly:

    ERROR=B1A_VEHICLE_CAPTURE_FAILED reason=invalid_table_shape test=failure_path
    ERROR=VEHICLE_OBSERVATION_SCAN_FAILED sim_sec=900
    OBSERVATION_FAILURES=1
    COM_FAILURES=1

### Important 2 - Load-bearing false-PASS tests

**NOT_ADDRESSED.**

The six literal replacement mutants listed in the fix report are now rejected, and
the fake-COM path materially improves coverage. However, two dead-code variants
still pass the complete 11-test B1a suite:

1. Keep the exact stopped-map increment line inside If False, then perform the live
   increment with CStr(laneNo). The static token check at
   test_b1a_vbs_verified_capture_static.py:54-55 passes. The fake stopped record is
   link 1, lane 1 (helper lines 92-97), so the wrong lane key is observationally
   identical and core parity also passes.
2. Keep the exact nonfinite guard inside If False. The static check at
   test_b1a_vbs_verified_capture_static.py:107-110 passes, and the behavior harness
   cannot synthesize a nonfinite VBScript numeric Variant.

Exact reproducers:

    $py='C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    & $py -B C:\tmp\b1a_mutation_review.py --full stopped_map_dead_decoy
    & $py -B C:\tmp\b1a_mutation_review.py --full finite_guard_dead_decoy

Observed for each:

    Ran 11 tests
    OK
    FALSE_PASS

The original finding specifically concerned dead-code/token false confidence.
Literal mutation checks alone do not close it.

### Minor 1 - Dotted-module helper import

**ADDRESSED.**

The helper now supports package-relative and discovery imports at
test_b1a_vbs_capture_helpers_behavior.py:12-15.

Reproducer:

    python -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior -v

Observed with the bundled Python runtime: **2/2 PASS**.

## New delta finding

### Important - Current review package omits the claimed runner test

The fix report lists scripts/tests/test_run_plant_fidelity_matrix.py as changed
(task-b1a-vbs-fix1-report.md:46) and claims its 11-test verification at line 113.
The live worktree contains the new exact-counter test at
scripts/tests/test_run_plant_fidelity_matrix.py:50-56.

However, review-b1a-vbs-fix1-current.diff contains only these files:

- scripts/run_real_world_stackelberg_controller.vbs
- scripts/tests/test_b1a_vbs_verified_capture_static.py
- scripts/tests/test_b1a_vbs_capture_helpers_behavior.py

The base HEAD also lacks scripts/tests/test_run_plant_fidelity_matrix.py. Applying
the submitted current package therefore cannot reproduce the claimed runner test or
its coverage.

Exact reproducers:

    git cat-file -e HEAD:scripts/tests/test_run_plant_fidelity_matrix.py

Observed: fatal path absent from HEAD, exit 128.

    Select-String review-b1a-vbs-fix1-current.diff -Pattern '^diff --git'

Observed: only the three files listed above; runner test absent.

This is new package/evidence breakage in the fix/current delta. The live worktree
runner suite passes, but the supplied package is incomplete.

## Verification

- B1a VBS static/fake-COM/helper/core parity: **11/11 PASS**.
- Dotted helper module invocation: **2/2 PASS**.
- Runner live-worktree regression: **11/11 PASS**.
- Physical projection core: **9/9 PASS**.
- Auditor regression: **31/31 PASS**.
- Adapter-fidelity regression: **2/2 PASS**.
- Six literal original mutations: all rejected after correcting the disposable
  runner import path.
- Two dead-code decoy mutations: **11/11 FALSE_PASS** each.
- Current package runner-test completeness: **FAIL**.
- Live VISSIM COM: **NOT_EVALUATED**.

## Required disposition

Do not approve fix round 1. Add executable evidence that distinguishes stopped
link number from lane number and eliminates dead-code guard acceptance, and include
the claimed runner test in the current review package. No new runtime Critical defect
was found in the fix delta.
