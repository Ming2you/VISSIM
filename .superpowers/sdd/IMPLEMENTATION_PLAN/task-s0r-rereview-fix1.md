# S0R Source/Preflight/Baseline/Evidence Fix Round 1 Re-review

## Scope

Independent scoped re-review of `review-s0r-fix1.diff` against the seven findings in
`task-4-s0r1-s0r3-review.md`. No production or test code was modified.

## Verdict

- **Spec verdict: CHANGES_REQUIRED (FAIL)**
- **Quality verdict: CHANGES_REQUIRED**
- **Disposition: 4 ADDRESSED, 3 NOT_ADDRESSED**
- **New Critical/Important findings: 0**. The remaining breakages map directly to C2, I2, and I3.

| Finding | Decision |
|---|---|
| C1 immutable upstream trust anchor absence/self-proof | **ADDRESSED** |
| C2 baseline PASS not bound to exact runtime/preflight/audit and false-PASS evidence | **NOT_ADDRESSED** |
| C3 preflight hashes a wrapper other than the actual n41 watchdog | **ADDRESSED** |
| I1 strict source verifier is opt-in and preflight does not require a strict report | **ADDRESSED** |
| I2 baseline artifact/CSV/action semantic completeness is shallow | **NOT_ADDRESSED** |
| I3 optional COM summary and stale/malformed/mixed `.err` evidence | **NOT_ADDRESSED** |
| I4 Python path/version/hash not bound to exact preflight/runtime source | **ADDRESSED** |

## Finding Decisions

### C1 - ADDRESSED

`vendor/NumSim-mine/UPSTREAM_TREE.json:2-9` records the supplied full commit, root tree,
src tree, SHA-1 object format, 96-file count, and per-path blob OIDs. The verifier pins
those independent values and the anchor's semantic SHA-256 in
`scripts/verify_runtime_source.py:15-23`, recalculates normalized Git blob OIDs in
`scripts/verify_runtime_source.py:223-268`, and gates both canonical and selected trees
against the anchor in `scripts/verify_runtime_source.py:459-501`.

An independent short check observed the required commit/tree values, 96 declared/listed/local
Python files, semantic SHA-256
`46f09f3ca71f2b9388e86864fe49c1781b35180a1db859d8bea583a3b3bd6cf9`, and zero local
path/blob mismatches. A clean committed vendor drift can no longer become its own reference.

### C2 - NOT_ADDRESSED

The matrix ordering is fixed: the strict generic audit executes before the baseline validator
and the baseline validator is only invoked after audit exit zero
(`scripts/run_plant_fidelity_matrix.ps1:136-175`). Run provenance also carries the preflight
path/hash/fingerprint and live input hashes are compared at
`scripts/validate_baseline_snapshot.py:289-391`.

However, the baseline validator still trusts self-declared PASS summaries instead of proving
that the supplied runtime-source, preflight, and audit artifacts are outputs of the exact
validators:

- `scripts/validate_baseline_snapshot.py:198-229` accepts a runtime-source artifact with no
  expected commit, trust anchor, import evidence, or `checks` array. It only requires schema,
  `status=PASS`, `strict=true`, and empty reasons.
- `scripts/validate_baseline_snapshot.py:203-229` recomputes the preflight fingerprint from
  fields inside the same JSON, but does not require its checks or bind
  `command_version.sha256` to the current preflight builder. A fabricated command hash can be
  included in a newly self-consistent fingerprint.
- `scripts/validate_baseline_snapshot.py:230-263` accepts a skeletal audit based on its own
  status/summary/policy fields and two named gate statuses; it does not bind the audit command
  or re-evaluate the audit evidence.

The repository's positive fixture demonstrates the gap: its runtime-source has no checks or
expected commit (`scripts/tests/test_validate_baseline_snapshot.py:119-128`), its preflight has
no checks and uses an all-`a` fabricated command hash
(`scripts/tests/test_validate_baseline_snapshot.py:130-159`), and its audit is a minimal
self-declaration (`scripts/tests/test_validate_baseline_snapshot.py:243-249`). The fixture is
then required to PASS at `scripts/tests/test_validate_baseline_snapshot.py:260-267`.

Independent reproducer result:

```text
overall=PASS chain_gate=PASS
runtime_has_checks=false runtime_expected_commit=null
preflight_has_checks=false preflight_command_sha256=aaaaaaaa...aaaaaaaa
```

This is still a load-bearing false-PASS path, so C2 remains Critical and NOT_ADDRESSED.

### C3 - ADDRESSED

The preflight default is now the actual distributed core15n41 watchdog
(`scripts/build_preflight_manifest.py:46-62`). The matrix names that same wrapper and passes
it explicitly to preflight (`scripts/run_plant_fidelity_matrix.ps1:41,81-90`). The watchdog
records its own `$PSCommandPath` hash (`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:184-189`),
and the baseline validator compares the run record to the preflight artifact path/hash
(`scripts/validate_baseline_snapshot.py:351-366`).

### I1 - ADDRESSED

The source verifier defaults to strict and requires explicit `--allow-nonstrict` for diagnostic
use (`scripts/verify_runtime_source.py:597-616`). Preflight requires `strict is True` and all
19 named trust-anchor checks to be PASS
(`scripts/build_preflight_manifest.py:408-452`). The matrix invokes both tools with `--strict`
(`scripts/run_plant_fidelity_matrix.ps1:81-90`). Targeted tests for non-strict rejection,
missing trust-check rejection, and the watchdog default passed.

The preflight CLI's own nonzero-on-failure behavior remains opt-in, but this does not reopen I1:
it still emits a FAIL manifest for a non-strict runtime report, and the matrix uses strict exit
handling.

### I2 - NOT_ADDRESSED

The JSON and per-decision action checks are materially deeper, including exact no-control model
VSL/ramp/signal values and physical row inventories
(`scripts/validate_baseline_snapshot.py:645-878`). That is only a partial fix.

Two false-PASS paths remain:

1. `scripts/validate_baseline_snapshot.py:560-575` validates only the `sim_sec` sequence in the
   state CSV. It does not require the actual 13-column plant-state schema emitted at
   `scripts/run_real_world_stackelberg_controller.vbs:180`, validate measurement fields, or
   establish run identity/freshness. The positive fixture's two-column synthetic CSV at
   `scripts/tests/test_validate_baseline_snapshot.py:222-224` is accepted.
2. The cumulative action comparison deliberately excludes the `readback` column at
   `scripts/validate_baseline_snapshot.py:880-896`. That column is the VISSIM COM result written
   by `scripts/run_real_world_stackelberg_controller.vbs:847-885`, not decorative metadata.

Independent reproducer changed one cumulative `readback` to
`ERR:VSL readback mismatch`; the no-control gate and overall snapshot both remained PASS:

```text
overall=PASS no_control_gate=PASS mutated_readback=ERR:VSL readback mismatch
```

Therefore JSON + per-decision CSV + cumulative CSV do not yet jointly prove actual no-control
semantics.

### I3 - NOT_ADDRESSED

The COM-summary portion is fixed: the VBS emits `COM_FAILURES` unconditionally and refuses
`STAGE=SIM_DONE` when any integrity counter is nonzero
(`scripts/run_real_world_stackelberg_controller.vbs:272-306`), while the baseline validator
requires exactly one zero-valued summary (`scripts/validate_baseline_snapshot.py:410-455`).
Present `.err` artifacts with error/fatal text also fail.

The stale `.err` lifecycle is not fail-closed. The watchdog archives pre-run `.err` files in a
sibling directory and records them in `stale_pre_run`
(`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:174-178,338-380`). Neither
the generic audit's marker parser (`scripts/audit_plant_fidelity.py:1612-1754`) nor the baseline
validator (`scripts/validate_baseline_snapshot.py:905-938`) examines `stale_pre_run`. The audit
also does not inspect the source network `.err` path after an absence marker is read.

Independent reproducer added a hash-correct `stale_pre_run` record pointing to a FATAL archived
file. The current generic audit returned:

```text
gate=PASS marker_errors=[] stale_pre_run_count=1
```

The existing "stale" unit test only changes the marker attempt so that it disagrees with the
wall-time profile (`scripts/tests/test_audit_plant_fidelity.py:321-334`); it does not exercise
the watchdog's actual `stale_pre_run` field. Thus stale evidence can still be reported as clean
atomic absence evidence.

### I4 - ADDRESSED

The watchdog directly executes the configured interpreter to obtain `sys.executable`, full
version, normalized triplet, and binary SHA-256, then records that identity in run provenance
(`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:273-320`). The same exact
interpreter is supplied to runtime-source and preflight by the matrix
(`scripts/run_plant_fidelity_matrix.ps1:47-51,81-90`) and to the VBS process through
`RW_PYTHON` (`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:440-445`).

The baseline validator cross-checks every recorded path, hash, and version triplet across run
provenance, runtime-source, preflight, and runlog at
`scripts/validate_baseline_snapshot.py:458-498`. Current-file drift is separately reported and
does not rewrite historical run identity. This satisfies I4's exact recorded-identity contract.

## Verification Performed

- Independent anchor metadata/semantic-hash/local blob check: PASS, 96/96 files, 0 mismatches.
- Five focused unit tests covering non-strict rejection, missing anchor checks, actual watchdog
  selection, matrix watchdog forwarding, and the existing malformed/stale/mixed marker cases:
  5/5 PASS in 0.174 s.
- Three short false-PASS reproducers: C2 skeletal chain PASS, I2 `ERR:` cumulative readback PASS,
  and I3 FATAL `stale_pre_run` audit PASS.

Per review instructions, no long runtime-source import probe and no VISSIM COM execution were
performed. Actual VISSIM COM behavior, live VBS execution, and live `.err` timing therefore
remain a separate **runtime verification gap** and are not promoted to PASS by this code review.
