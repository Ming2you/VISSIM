# B1a Core Fix Round 1 Independent Rereview 2

## Verdict

**FAIL**

Fix dispositions: **ADDRESSED 4 / NOT_ADDRESSED 2**.

Newly introduced or residual in-scope defects: **Critical 1 / Important 1**.

I4 is separately **OPEN**. Live VISSIM COM and live timing remain
**NOT_EVALUATED**.

## Disposition Summary

| Finding | Disposition |
|---|---|
| C1 independent A2/preflight trust anchor | **ADDRESSED** |
| C2 malformed/very-large JSON values and stale outputs | **NOT_ADDRESSED** |
| I1 optional envelope masking provenance failure | **ADDRESSED** |
| I2 nested preflight path containment | **ADDRESSED** |
| I3 reachable, independently trustworthy live PASS | **NOT_ADDRESSED** |
| M1 performance test timing scope | **ADDRESSED** |

## C1 - ADDRESSED

The approval now reconstructs A2 from the contained graph, routes, ownership,
adjacency, and capacity evidence, then requires exact equality with the supplied
topology. Nested evidence inputs are loaded independently of the topology's own hashes.

**Implementation:**

- `scripts/approve_physical_stock_topology.py:432-492` resolves contained evidence,
  calls `compile_physical_stock_topology()`, and rejects any replay difference.
- `scripts/approve_physical_stock_topology.py:496-564` combines preflight, A1, A2
  structural validation, provenance bindings, and replay before approval.
- `plant/src/vissim_strict/physical_projection.py:468-870` independently validates
  topology metadata, source/command bindings, stock ownership/visibility, memberships,
  edges, dimensions, and lane cover.

**Minimal local unit-test reproducer:**

```text
python -B -m unittest \
  scripts.tests.test_b1a_core_provenance.B1aProvenanceScriptTests.test_independent_a2_replay_rejects_coherently_rehashed_mutation_matrix -v
```

The test at `scripts/tests/test_b1a_core_provenance.py:775-839` changes owner/view,
metadata, input hashes, producer command, dimensions, edge position, and route
membership, rehashes each topology, and requires approval exit 1 plus FAIL.

## C2 - NOT_ADDRESSED

The exact `10**400` topology, selection, and state cases are fixed: finite conversion
catches `OverflowError`, producer boundaries catch it, and the checked tests replace
stale approval, manifest, audit, and sidecar artifacts with FAIL
(`plant/src/vissim_strict/physical_projection.py:405-411`,
`scripts/build_state_manifest_v2_1.py:109-116`,
`scripts/tests/test_b1a_core_provenance.py:643-689`).

However, the broader brief requirement that every parseable malformed invocation
replace stale output is still violated. A standard JSON number used as a malformed
`resolved_signal_programs` record reaches `record.get()` at
`scripts/approve_physical_stock_topology.py:350-359` and raises `AttributeError`.
The approval CLI boundary at `scripts/approve_physical_stock_topology.py:792` does not
catch `AttributeError`, so atomic FAIL publication at line 825 is never reached and a
stale PASS survives.

**Minimal local unit-test reproducer:**

```python
def test_numeric_signal_record_replaces_stale_approval(self):
    preflight = strict_load_json(self.preflight_path)
    preflight["network"]["resolved_signal_programs"] = [1]
    atomic_write_json(self.preflight_path, preflight)
    self.approval_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
    self.assertEqual(self.approve(), 1)
    self.assertEqual(strict_load_json(self.approval_path)["status"], "FAIL")
```

Observed independently: `AttributeError: 'int' object has no attribute 'get'`; approval
bytes remained exactly `{"status":"STALE_PASS"}`.

## I1 - ADDRESSED

An optional missing envelope is now NOT_EVALUATED only when all prior state/run/hash
checks passed. Existing reasons force FAIL at
`scripts/validate_state_projection_v2_1.py:436-445`.

**Minimal local unit-test reproducer:**

```text
python -B -m unittest \
  scripts.tests.test_b1a_core_provenance.B1aProvenanceScriptTests.test_optional_missing_envelope_cannot_mask_state_hash_tamper -v
```

The checked reproducer at `scripts/tests/test_b1a_core_provenance.py:621-641` mutates
optional-envelope state bytes and requires exit 1, FAIL sidecar, and FAIL audit.

## I2 - ADDRESSED

Both nested artifact paths and resolved signal-program paths are canonically resolved
and required to remain under the workspace at
`scripts/approve_physical_stock_topology.py:273-289` and
`scripts/approve_physical_stock_topology.py:346-355`. A2 replay repeats containment at
lines 442-451.

**Minimal local unit-test reproducer:**

```text
python -B -m unittest \
  scripts.tests.test_b1a_core_provenance.B1aProvenanceScriptTests.test_nested_preflight_artifact_and_signal_paths_must_be_contained -v
```

The test at `scripts/tests/test_b1a_core_provenance.py:871-910` binds first an outside
artifact and then an outside signal file; both approval attempts exit 1 and publish
FAIL.

## I3 - NOT_ADDRESSED

The exit-0 branch is reachable, but its new live gate is not independently trustworthy.
The validator requires the evidence producer identity to be the empty object at
`scripts/validate_state_projection_v2_1.py:535-536`. It then trusts JSON-authored
`capture_source`, version support, parse-success booleans, byte sizes, and timing samples
at lines 644-655 and 720-755. Rehashing the same document is sufficient to assert these
facts; no runner/live-capture producer or immutable timing record is authenticated.

The state-universe comparison at `scripts/validate_state_projection_v2_1.py:577-583`
also compares sets and does not reject duplicate live-state records. Two evidence rows
for one manifest state can therefore pass after updating self-declared dimensions and
semantic hash.

**Minimal local unit-test reproducer:**

```python
def test_self_declared_duplicate_live_evidence_must_not_pass(self):
    evidence_path = self.write_live_evidence(state_path)  # no VISSIM producer
    evidence = strict_load_json(evidence_path)
    evidence["states"].append(dict(evidence["states"][0]))
    evidence["sample_dimensions"].update(states=2, nonzero_live_states=2)
    evidence["semantic_sha256"] = canonical_json_sha256(
        live_evidence_semantic_payload(evidence)
    )
    atomic_write_json(evidence_path, evidence)
    self.assertNotEqual(self.validate(evidence_path), 0)
```

Observed independently: exit `0`, audit `PASS`. The checked fixture already proves the
self-declaration half of the defect: it constructs the entire evidence document locally
at `scripts/tests/test_b1a_core_provenance.py:479-568`, and lines 692-721 require that
synthetic document to produce both live gates PASS.

## M1 - ADDRESSED

The 20,000-record timer now begins before atomic state serialization and ends after
strict parse, normalization, public projection, and atomic sidecar serialization/write
at `plant/tests/test_vissim_strict_physical_projection.py:433-459`. This matches the
claimed offline `serialize+strict_parse+public_project+atomic_sidecar_write` pipeline.
It correctly makes no live COM or action-reference timing claim.

**Minimal local unit-test reproducer:**

```text
python -B -m unittest \
  plant.tests.test_vissim_strict_physical_projection.PhysicalProjectionCoreTests.test_synthetic_20000_record_serialize_parse_project_write_meets_limits -v
```

## I4 - OPEN (Separate)

I4 remains open exactly as requested and is not counted as fixed. The VBS state still
emits only `run_id` and `manifest_path` at
`scripts/run_real_world_stackelberg_controller.vbs:1488`, while the runner still writes
schema 1 provenance at
`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:300-326` and the core
requires `run-manifest-v2.1` plus exact `manifest_sha256` at
`scripts/build_state_manifest_v2_1.py:296-374`.

## Verification

```text
Focused B1a core/provenance: 24 passed in 4.770 s
A1/A2 regressions:           54 passed in 116.468 s
Strict compiler regressions:  5 passed in 25.001 s
Malformed preflight probe:    uncaught AttributeError; stale PASS survived
Duplicate live-state probe:   exit 0; audit PASS
Live VISSIM COM:              NOT_EVALUATED
```

No implementation file was edited.
