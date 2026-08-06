# B1a VBS fix round 2 report

## Status

- Scoped fix status: **IMPLEMENTED**.
- Remaining original Important false-PASS: **FIXED**.
- Accepted VBS runtime semantics were not changed in this round.
- I4 run-manifest compatibility was not implemented and remains a separate integration task.
- Supported-version live VISSIM COM: **NOT_EVALUATED**.

## Changed files

- `scripts/tests/test_b1a_vbs_verified_capture_static.py`
  - Replaced regex-only procedure extraction with a unique procedure lexer and
    logical-statement/control-flow extraction.
  - Called-path checks now ignore comments, string contents, literal-dead branches,
    and statements after an unconditional procedure exit.
  - Requires the reachable stopped-map update to use the previously assigned link
    key exactly once.
  - Requires the reachable finite probe and nonfinite guard to precede the success
    assignment exactly once.
  - Adds the independent review's stopped-map and finite-guard dead-decoy mutations.
- `scripts/tests/test_b1a_vbs_capture_helpers_behavior.py`
  - Changes the executable stopped vehicle from link 1/lane 1 to link 101/lane 7.
  - Updates emitted-envelope and core-normalization parity expectations.
  - Executes the stopped-map dead-decoy mutant and requires the fake-COM harness to
    fail on `called_scan_stopped_counts`.
  - Makes source injection dynamic so the independent mutation runner exercises the
    supplied mutant instead of a function-definition-time source snapshot.
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-vbs-fix2-report.md`
  - This report.

Retained from fix round 1 and not edited in round 2:

- `scripts/run_real_world_stackelberg_controller.vbs`
- `scripts/tests/test_run_plant_fidelity_matrix.py`

The runner test remains present in the live worktree and was included in verification.
Any review package must include that currently untracked file.

## Finding disposition

### Stopped-map dead decoy

**FIXED.** The fake COM stopped row is now link 101/lane 7. A live update keyed by
`CStr(laneNo)` produces stopped key 7 while the counted link key is 101, so it is no
longer observationally equivalent to correct behavior. The focused suite also runs
the exact reviewer mutant; it exits 1 with `FAIL=called_scan_stopped_counts`.

The reachable-statement assertion independently ignores the correct update retained
inside `If False Then` and rejects the reachable lane-key update.

### Finite-guard dead decoy

**FIXED.** Static evidence is tied to the unique called `TryB1aFiniteDouble`
procedure. Logical statements inside `If False Then` are excluded, and the reachable
probe, nonfinite guard, and success assignment must occur exactly once in that order.
The reviewer's exact dead-decoy mutation is rejected.

VBScript cannot portably synthesize a nonfinite numeric Variant, so no live-COM or
fabricated numeric PASS is claimed for that value class.

## Exact verification

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest discover -s scripts\tests -p 'test_b1a_vbs*.py' -v
```

Result: **13/13 PASS**.

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B 'C:\tmp\b1a_mutation_review.py' --full stopped_map_dead_decoy
```

Result: **CAUGHT**, 2 failures in the mutant suite, including static called-path and
executable stopped-count evidence; no false PASS.

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B 'C:\tmp\b1a_mutation_review.py' --full finite_guard_dead_decoy
```

Result: **CAUGHT**, 1 static called-path failure in the mutant suite; no false PASS.

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior -v
```

Result: **3/3 PASS**.

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest discover -s scripts\tests -p 'test_run_plant_fidelity_matrix.py' -v
```

Result: **11/11 PASS**.

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest discover -s plant\tests -p 'test_vissim_strict_physical_projection.py' -v
```

Result: **9/9 PASS**. The focused B1a behavior test separately passes the actual
emitted VBS `vehicle_records` envelope to `normalize_vehicle_records` without repair.

```powershell
& 'C:\Windows\System32\cscript.exe' //nologo 'scripts\run_real_world_stackelberg_controller.vbs'
```

Result: **COMPILE GATE PASS**. The whole file compiled and reached the expected
no-argument usage gate; exit code 1 is expected for omitted required arguments.

```powershell
git diff --check -- scripts/run_real_world_stackelberg_controller.vbs
```

Result: **PASS**; only the existing LF-to-CRLF working-copy warning was emitted.

## Self-review and concerns

- Root-level `vehicle_records` remains the normative sibling of
  `local_observation`; no envelope-location change was made.
- No Python projector, approval, manifest, validator, adapter, auditor, A1/A2,
  NumSim, dynamics, or control-policy implementation file was edited.
- I4 compatibility is intentionally deferred.
- Live supported-version VISSIM capture, raw four-table evidence, and live p95 timing
  remain **NOT_EVALUATED**.
