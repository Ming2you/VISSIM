# B1a Core Fix Round 2 Report

## Status

**RESIDUAL C2 FIXED / DUPLICATE LIVE-STATE STRUCTURE FIXED / I3 AND I4 OPEN**

This narrow round changed only the B1a approval, manifest, projection-audit, and focused
provenance test files. It did not edit VBS, watchdog, adapter, auditor, A1/A2
implementation/tests, NumSim, or B1b dynamics.

## C2 Disposition - FIXED

### Owning-boundary validation

- `validate_preflight_artifact()` now checks that model-controller, auxiliary-controller,
  and resolved-signal-program collections are arrays of objects before reading record
  fields. Model-controller `signal_program` and runtime `selected`/`python` values must
  also be objects.
- Numeric, list, and string `resolved_signal_programs` records are converted to typed
  `topology_trust_mismatch` evidence instead of leaking `AttributeError`.
- Preflight artifact records continue to require the exact four-field object shape;
  downstream provenance lookup now independently normalizes malformed artifact records
  rather than calling `.get()` on them.
- Before invoking existing A1 validators, approval checks graph
  `links/nodes/edges/connectors/signal_heads`, parent `lanes`, connector
  `lane_mapping`, and route `routing_decisions/routes/proofs` as arrays of object
  records. Malformed collections skip unsafe downstream validation/replay and publish a
  typed trust failure.
- A1 validation, A1 provenance reconstruction, A2 structural validation, and A2 replay
  each retain a local malformed-input guard so deeper nested malformed fields also
  become closed typed reasons.
- Selection entries, state vehicle records, live-state records, raw COM sample records,
  performance objects, and timing samples are validated at their existing owning
  boundaries. The per-state projection boundary now converts any residual malformed
  nested exception into `invalid_table_shape` and writes a FAIL sidecar.

### Outer fail-closed guards

Approval, state-manifest, and projection-audit CLIs now share the same effective final
guard set for `AttributeError`, `IndexError`, `KeyError`, `OSError`, `OverflowError`,
`TypeError`, and `ValueError`. A usable output path therefore reaches atomic FAIL
publication even if a nested malformed shape escapes an owning validator. Exception
reason conversion is itself type-checked so malformed exception metadata cannot break
the failure writer.

### Adversarial coverage

The approval matrix injects each of integer, array, and string records at seven
boundaries:

- resolved signal program;
- preflight artifact;
- graph node;
- graph connector lane mapping;
- route proof;
- route decision;
- topology stock.

Every case seeds `{"status":"STALE_PASS"}`, requires exit 1 and typed FAIL, repeats
the invocation, and requires byte-identical deterministic approval output.

Additional matrices cover numeric/list/string selection entries and state vehicle
records, plus live-state, raw-attribute-sample, performance-object, and timing-sample
mutations. They require stale manifest/audit/sidecar replacement and closed reason
codes. The rereview's exact numeric `resolved_signal_programs` reproducer now publishes
FAIL and exits 1.

## Duplicate Live-State Disposition - FIXED STRUCTURALLY

`validate_live_evidence()` now builds independent uniqueness indexes for:

- exact `state_path`;
- exact decoded `(run_id, sim_sec)`.

Duplicate path and duplicate identity records are rejected before set-based universe
comparison. Tests cover an exact duplicate, same path with changed identity, and same
identity with changed path; each updates dimensions and recomputes the live-evidence
semantic hash, then requires exit 1 and an atomically replaced FAIL audit containing
the specific duplicate reason.

This is only a structural correction. It does not certify the current self-declared
live evidence model.

## Changed Files

- `scripts/approve_physical_stock_topology.py`
- `scripts/build_state_manifest_v2_1.py`
- `scripts/validate_state_projection_v2_1.py`
- `scripts/tests/test_b1a_core_provenance.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-core-fix2-report.md`

## Commands And Results

Red reproducer before implementation:

```text
python -B -m unittest \
  scripts.tests.test_b1a_core_provenance.B1aProvenanceScriptTests.test_malformed_nested_approval_record_matrix_replaces_stale_output -v
```

Result: **18 uncaught errors** across signal, artifact, graph, and route malformed
records, including the rereview's exact `AttributeError`; stale PASS survived those
cases.

Focused final verification:

```text
python -B -m unittest \
  plant.tests.test_vissim_strict_physical_projection \
  scripts.tests.test_b1a_core_provenance -v
```

Result: **28 passed in 7.910 s**.

No-write AST parse of the four changed Python files: **4 passed**.

## Remaining I3/I4

- **I3 OPEN:** the current summary-only live evidence is self-declared and is not an
  independent trust anchor. This round makes malformed and duplicate records fail but
  does not authenticate live COM, producer identity, or timing. No live PASS is
  claimed; real live COM and p95 remain `NOT_EVALUATED`. Replacement is owned by
  `task-b1a-run-live-trust-brief.md`.
- **I4 OPEN:** immutable pre-run manifest integration and VBS/watchdog provenance remain
  untouched and are owned by the same combined runner/live redesign.
