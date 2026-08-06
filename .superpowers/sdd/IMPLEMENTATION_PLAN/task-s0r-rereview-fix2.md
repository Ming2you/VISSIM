# S0R Fix Round 2 Independent Scoped Re-review

## Scope

Independent re-review of `review-s0r-fix2.diff` and the current worktree for the three
remaining S0R findings from `task-s0r-rereview-fix1.md`. No production or test code was
modified. No long runtime-source probe and no VISSIM COM run were performed.

## Verdict

- **Spec verdict: CHANGES_REQUIRED (FAIL)**
- **Quality verdict: CHANGES_REQUIRED**
- **Disposition: 1 ADDRESSED, 2 NOT_ADDRESSED**
- **New Critical/Important findings: 0**. The two reproduced false-PASS paths map directly
  to existing C2 and I2.

| Finding | Decision |
|---|---|
| C2 skeletal/self-declared runtime-source/preflight/audit evidence can baseline-PASS | **NOT_ADDRESSED** |
| I2 13-column state/fresh-run linkage and cumulative readback completeness | **NOT_ADDRESSED** |
| I3 stale pre-run and post-marker source `.err` lifecycle | **ADDRESSED** |

## Finding Decisions

### C2 - NOT_ADDRESSED

The round closes several specifically requested counterexamples. The baseline validator now
rejects a runtime-source artifact missing `checks`, `expected_snapshot_commit`, or the current
verifier hash (`scripts/validate_baseline_snapshot.py:393-407`), rejects a fabricated current
preflight command hash even when the preflight fingerprint is recomputed
(`scripts/validate_baseline_snapshot.py:571-583`), and rejects the extremely small audit object
used by the new negative test. The runtime source is also re-bound to the 96-file anchor and
current source/import path hashes (`scripts/validate_baseline_snapshot.py:410-548`).

However, the audit half of the exact-validator contract remains self-declared. For every
required semantic gate, `_validate_audit_artifact` requires only that the value be a mapping
whose `status` is `PASS`; it does not require or validate gate-specific evidence
(`scripts/validate_baseline_snapshot.py:663-689`). The nominal global fields
`sample_dimensions`, `units`, `downstream_consumers`, and `artifact_evidence` are checked only
for key presence (`scripts/validate_baseline_snapshot.py:659-661`). The accepted positive test
fixture makes all required gates only `{status, reason}` objects
(`scripts/tests/test_validate_baseline_snapshot.py:423-435`) rather than production audit gate
payloads, and `test_complete_synthetic_baseline_passes` requires that fixture to PASS
(`scripts/tests/test_validate_baseline_snapshot.py:519-528`).

Independent reproducer 1 used that production-shaped outer audit with only status/reason gate
records:

```text
overall=PASS
chain=PASS
required_gate_shapes=[..., ('state_observation_contract', ['reason', 'status']), ...]
```

Independent reproducer 2 additionally replaced `artifact_evidence` and `sample_dimensions`
with `{}`, `units` with `{}`, and `downstream_consumers` with `[]`:

```text
overall=PASS
chain=PASS
chain_reasons=[]
```

The validator does independently hash the primary inputs and baseline artifact inventory at
`scripts/validate_baseline_snapshot.py:691-762`, but those hashes do not establish that audit
semantics such as `state_observation_contract`, `action_inventory`,
`projection_diagnostics`, and `runtime_provenance` were evaluated by the current auditor. A
status-only fabricated gate inventory can still certify them. C2 therefore remains Critical
and NOT_ADDRESSED despite the narrower whole-object skeletal test now failing.

### I2 - NOT_ADDRESSED

The schema and readback portions are addressed. `_validate_state_csv` requires the exact
13-column VBS header, all 721 canonical times, finite/ranged measurements, nonnegative integer
counts, category mass identity, no-control mode, and `ok` status
(`scripts/validate_baseline_snapshot.py:1214-1272`). Cumulative action validation now rejects
empty/`ERR` VSL readback, non-state ramp readback, and any no-control signal row
(`scripts/validate_baseline_snapshot.py:1577-1609`). The requested two-column, NaN/negative,
and `ERR:VSL readback mismatch` cases all failed.

Hash and declared-run mismatch checks are also present. The artifact manifest compares each
expected path, hash, size, and recorded mtime to the current file and checks the manifest run
ID/attempt (`scripts/validate_baseline_snapshot.py:1760-1812`). An independent mutation of the
manifest run ID plus the state CSV hash produced:

```text
overall=FAIL
run_manifest=FAIL
reasons=['run artifact manifest schema/status/run linkage is invalid',
         'run artifact manifest hash/link mismatch: state_csv']
```

Fresh-run linkage is still not proven. `_recorded_mtime_matches` only checks that the manifest
timestamp equals the file's current filesystem timestamp (`scripts/validate_baseline_snapshot.py:300-308`).
The artifact loop repeats that same comparison (`scripts/validate_baseline_snapshot.py:1802-1812`),
while the wall-time linkage checks only attempt equality and `finalized >= finished`; it never
requires output/decision mtimes to fall within the run's `started_at_utc`/`finished_at_utc`
interval (`scripts/validate_baseline_snapshot.py:1844-1857`). The 13-column state CSV itself has
no run ID by design, so a newly self-declared manifest can wrap a stale CSV.

Independent reproducer set the otherwise valid state CSV mtime to 2000-01-01, regenerated the
manifest and audit around the unchanged stale file, and validated it against a run beginning in
2026:

```text
overall=PASS
state=PASS
run_manifest=PASS
state_mtime=2000-01-01T09:00:00
run_started=2026-08-05T17:25:26.179905+00:00
```

The matrix's new/empty output-directory guard (`scripts/run_plant_fidelity_matrix.ps1:66-71`)
reduces this risk for that one invocation path, but the baseline validator still certifies a
stale externally supplied package and its own tests build manifests synthetically. Because the
finding explicitly includes fresh-run linkage, I2 remains Important and NOT_ADDRESSED.

### I3 - ADDRESSED

Both independent validators now require `stale_pre_run` to be an explicit list, validate every
record's attempt/source/archive path/hash/timestamp, inspect archive text, and fail whenever the
list is nonempty (`scripts/audit_plant_fidelity.py:1719-1760` and
`scripts/validate_baseline_snapshot.py:1660-1699`). Absence markers are rechecked against the
live network `.err`, while present markers require current source and preserved artifact hashes
to agree (`scripts/audit_plant_fidelity.py:1762-1786` and
`scripts/validate_baseline_snapshot.py:1700-1720`).

The focused malformed/hash-mismatch/FATAL stale archive cases, clean stale presence behavior,
post-absence source recreation, and present-source hash drift all fail closed. I3 is ADDRESSED.

## Required Counterexamples

| Counterexample | Observed result |
|---|---|
| Runtime source missing checks/full commit/current command hash | FAIL |
| Fabricated preflight command hash with recomputed fingerprint | FAIL |
| Whole-object skeletal audit from the round-2 negative test | FAIL |
| Status-only required audit gates and empty nominal global evidence containers | **PASS (C2 residual)** |
| Two-column state CSV | FAIL |
| Nonnumeric, negative, or NaN measurement | FAIL |
| Cumulative `ERR:VSL readback mismatch` | FAIL |
| Output hash or manifest run-bound provenance mismatch | FAIL |
| Stale state predating the run but re-recorded in a new manifest | **PASS (I2 residual)** |
| `stale_pre_run` present/malformed/hash mismatch/FATAL archive | FAIL |
| Absence marker followed by source `.err` recreation | FAIL |

## Quality Assessment

The round introduces a 2,032-line baseline validator and duplicates substantial audit/error
evidence validation. No clearly unreachable function was found in the reviewed path, but there
is a material schema inconsistency: several advertised audit evidence fields are accepted when
empty, and required gate payloads are reduced to status strings. That complexity therefore has
not produced an independently enforced audit contract. The run artifact schema likewise records
mtime without using it to establish run-time bounds. These are functional quality defects already
accounted for under C2 and I2, so they are not counted again as new findings.

## Verification Performed

- Target suites: 59 tests, all PASS in 47.929 s.
- Focused required-counterexample subset: 9 tests, all PASS in 12.393 s.
- Four independent short synthetic reproducers: missing runtime contract FAIL; fabricated
  preflight command FAIL; output hash/run mismatch FAIL; status-only audit and stale-mtime
  package exposed the two false-PASS paths above.
- No standalone runtime-source import probe, long source probe, VISSIM process, or COM action was
  executed.
