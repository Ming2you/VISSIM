# S0R Fix Round 3 Independent Scoped Re-review

## Scope

Independent re-review of `review-s0r-fix3.diff` and the current worktree for the two
remaining findings from `task-s0r-rereview-fix2.md`. No production or test code was
modified. No runtime-source CLI/import probe, VISSIM process, or COM action was run.

## Verdict

- **Spec verdict: PASS**
- **Quality verdict: PASS**
- **Disposition: 2 ADDRESSED, 0 NOT_ADDRESSED**
- **New Critical/Important findings: 0**

| Finding | Decision |
|---|---|
| C2 current audit semantics are not independently recomputed | **ADDRESSED** |
| I2 stale output/decision mtime can be rewrapped as a fresh run | **ADDRESSED** |

## Finding Decisions

### C2 - ADDRESSED

The baseline validator now loads the exact current `audit_plant_fidelity.py`, rebuilds a
complete audit from the supplied deterministic invocation, and requires strict-complete PASS,
canonical projection equality, and independently recomputed projection-hash equality
(`scripts/validate_baseline_snapshot.py:683-720`). The auditor's projection includes the
global evidence containers, all input and artifact evidence, state/action semantics, every
gate and summary, completion policy, strict result, and replay invocation
(`scripts/audit_plant_fidelity.py:2371-2428`). Replay rejects missing or extra invocation
fields and forbids the `.err` copy-target side effect
(`scripts/audit_plant_fidelity.py:2436-2457`).

Independent mutation tests started from a real current-auditor PASS artifact, recomputed the
supplied semantic hash after each mutation, and observed:

```text
status-only gate inventory                       FAIL
empty sample_dimensions/units/downstream/evidence FAIL
semantic projection field tamper                 FAIL
```

All three failures included the current-auditor replay mismatch reason. On the untouched
artifact, the rebuilt audit exited 0 and both canonical object equality and canonical hash
equality were true. A self-declared semantic hash is therefore insufficient to pass, and C2
is ADDRESSED.

### I2 - ADDRESSED

The run manifest now classifies simulation outputs, post-exit evidence, and the preserved
pre-run input, binds its run window exactly to the wall-time profile, and declares a fixed
2-second filesystem tolerance (`scripts/validate_baseline_snapshot.py:1880-1923`). Every
state/action/log/readback output and every decision/anchor artifact is checked against the
process start/finish interval in addition to its path, hash, size, and recorded current mtime
(`scripts/validate_baseline_snapshot.py:1924-1982`). The watchdog emits the matching role and
window records after process completion (`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:402-446`,
`:518-521`).

Independent rewrapping reproducers observed:

```text
state CSV mtime = 2000-01-01; manifest + audit rebuilt     FAIL
decision JSON mtime = 2000-01-01; manifest + audit rebuilt FAIL
state CSV mtime = run start - 1.75s with tolerance = 2.0s  PASS
```

The first two failures were specifically attributed to the simulation run-window check. The
within-tolerance package passed both `run_artifact_manifest` and the complete baseline. This
closes the reported stale-mtime rewrapping path without imposing a zero-tolerance timestamp
assumption, so I2 is ADDRESSED.

## I3 Regression Check

The focused existing stale-error tests passed for malformed records, hash mismatch, FATAL
archives, source recreation, and absence-marker recreation. An additional independent case
used a structurally valid, hash-matching, non-error stale archive; it still failed in both the
current auditor and baseline validator because any nonempty `stale_pre_run` inventory is
fail-closed (`scripts/audit_plant_fidelity.py:1719-1782`,
`scripts/validate_baseline_snapshot.py:1738-1777`). Prior I3 behavior has not regressed.

## Quality Assessment

No new Critical or Important behavioral breakage was found. PowerShell parsing reported zero
errors for the matrix and watchdog scripts. A simple top-level AST reference audit found no
unreferenced validator/auditor functions in the reviewed path.

Parts of the manual audit checks following replay in `_validate_audit_artifact` are now
logically duplicated by canonical replay, especially global-key, gate-summary, and current-file
identity checks. The same block also supplies independent baseline-directory and preflight
bindings that replay alone does not establish. The checks are reachable, fail-closed, and did
not conflict at the acceptance/tolerance boundaries, so this is not a new Important finding;
it is a maintainability opportunity rather than dead validation requiring this round to fail.

## Verification Performed

- Seven focused existing tests: **PASS**, 7 tests in 26.245 s.
- Independent combined reproducer: **PASS**, covering canonical equality, three C2 mutations,
  stale state rewrap, stale decision rewrap, explicit mtime tolerance, and clean stale `.err`.
- PowerShell parser checks for the two changed execution scripts: **PASS**, zero errors.
- No source probe, matrix dry-run that invokes a source probe, VISSIM process, or COM action.
