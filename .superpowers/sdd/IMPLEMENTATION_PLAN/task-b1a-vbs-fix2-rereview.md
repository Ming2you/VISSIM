# B1a VBS fix-round-2 independent rereview

## Verdict

**APPROVED**

Scoped disposition:

- Remaining original Important false-PASS finding: **ADDRESSED 1 / NOT_ADDRESSED 0**
- Previous new Important package-completeness finding: **ADDRESSED 1 / NOT_ADDRESSED 0**
- New fix2-delta findings: **Critical 0 / Important 0**
- Supported-version live VISSIM COM: **NOT_EVALUATED**

## Remaining original finding

### Important - load-bearing false-PASS tests

**ADDRESSED.**

The static test now extracts the unique called VBS procedure and reduces it to
logical, reachable statements. Literal-dead branches and statements following an
unconditional procedure exit do not contribute evidence
(scripts/tests/test_b1a_vbs_verified_capture_static.py:113-205).

For the stopped map, the called-path assertion requires exactly one reachable
fullLinkStoppedCounts increment and requires it to use the previously assigned
link key (static test lines 240-247). The executable fake-COM fixture now makes the
stopped vehicle link 101/lane 7 (helper test line 95), so a lane-key implementation
is observably wrong. Dynamic source injection is at helper line 29 and the dedicated
executable mutant check is at lines 360-389.

Exact independent reproducer:

    & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B 'C:\tmp\b1a_mutation_review.py' --full stopped_map_dead_decoy

Observed: **CAUGHT**, 2 failures, 0 errors, across 13 tests. The reachable-path
assertion failed and the fake-COM harness exited 1 with
FAIL=called_scan_stopped_counts. This is no longer a false PASS.

For the finite guard, the called-path assertion requires one reachable probe, one
reachable nonfinite guard, and one reachable success assignment in that order
(static test lines 299-308). The exact dead-decoy mutation is also embedded at
lines 387-397.

Exact independent reproducer:

    & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B 'C:\tmp\b1a_mutation_review.py' --full finite_guard_dead_decoy

Observed: **CAUGHT**, 1 failure, 0 errors, across 13 tests. The called-path finite
guard assertion failed. This is no longer a false PASS.

## Previous new finding

### Important - current review package omitted the runner test

**ADDRESSED.**

review-b1a-vbs-fix2-current.diff contains exactly one diff section for each required
file and no unexpected section:

- VBS runtime at package line 3
- Static B1a test at package line 897
- Executable/helper B1a test at package line 1375
- Runner test at package line 1865

Exact reproducer:

    Select-String review-b1a-vbs-fix2-current.diff -Pattern '^diff --git '

Observed: the four sections above, including the complete 191-line new runner test.
The omission from review-b1a-vbs-fix1-current.diff is closed.

## Fix2 delta review

No new Critical or Important breakage was found in the fix2 changes. The VBS diff
section in the fix2 package is byte-for-byte identical to the VBS section in the
fix1 package. After removing the package section-separator blank line, it also
matches the live git diff for scripts/run_real_world_stackelberg_controller.vbs.
Accepted runtime code semantics are therefore unchanged in fix round 2.

The current brief still normatively requires root-level vehicle_records as a sibling
of local_observation. The executable test asserts both root presence and absence
under local_observation (helper lines 425-426), then passes the emitted envelope
without repair to normalize_vehicle_records (lines 442-452). The observed stopped
maps retain explicit zero keys for every counted link. This contract remains green;
no envelope-placement change occurred in fix2.

The previously repaired dotted-module helper import also remains green:

    & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior -v

Observed: **3/3 PASS**. No test-import failure remains.

## Verification

- B1a VBS static/fake-COM/helper/core-projector parity: **13/13 PASS**.
- stopped_map_dead_decoy: **CAUGHT**, 2 failures / 0 errors.
- finite_guard_dead_decoy: **CAUGHT**, 1 failure / 0 errors.
- Dotted-module helper invocation: **3/3 PASS**.
- Runner regression: **11/11 PASS**.
- Required package sections: **4/4 present exactly once**.
- VBS runtime change from fix1 to fix2: **none**.
- Live supported-version VISSIM COM: **NOT_EVALUATED**.

The cscript runs above use synthetic helper and fake-COM objects only. They are not
claimed as live VISSIM COM evidence.
