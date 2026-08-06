# B1a Core Fix Round 2 Independent Rereview

## Verdict

**ADDRESSED**

Scoped dispositions: **ADDRESSED 2 / NOT_ADDRESSED 0**.

New fix2 defects: **Critical 0 / Important 0**.

I3 summary trust and I4 runner integration remain separately **OPEN** and are not
counted as fix2 regressions. Live VISSIM COM and live timing remain
**NOT_EVALUATED**.

## Disposition Summary

| Scoped residual | Disposition |
|---|---|
| C2 malformed nested record stale-output paths | **ADDRESSED** |
| Duplicate live state/path/identity acceptance | **ADDRESSED** |

## C2 - ADDRESSED

The exact numeric `resolved_signal_programs` reproducer now fails at the owning
boundary. `scripts/approve_physical_stock_topology.py:379-398` normalizes the collection,
rejects each non-object record before field access, and records a typed trust issue.
The approval CLI also catches the complete local malformed-input exception set at
`scripts/approve_physical_stock_topology.py:936-970`, so an escaped nested shape still
reaches atomic FAIL publication when the output path is usable.

Independent exact reproducer result:

```text
preflight["network"]["resolved_signal_programs"] = [1]
seeded approval bytes: {"status":"STALE_PASS"}
approval exit: 1
replacement status: FAIL
reason codes: ["topology_trust_mismatch"]
```

The broader approval matrix at
`scripts/tests/test_b1a_core_provenance.py:912-980` covers numeric, list, and string
records at seven boundaries: resolved signal program, preflight artifact, graph node,
connector lane mapping, route proof, route decision, and topology stock. Each of the 21
cases runs twice, exits 1, publishes typed FAIL, and produces byte-identical output on
repeat.

The focused suite also exercised the additional fix2 matrices for malformed selection
entries and state vehicle records at
`scripts/tests/test_b1a_core_provenance.py:982-1023`, and malformed live-state, raw
sample, performance-object, and timing-sample records at lines 1024-1082. Seeded stale
manifest, sidecar, and audit outputs were replaced with FAIL.

## Duplicate Structure - ADDRESSED

`scripts/validate_state_projection_v2_1.py:583-612` now validates each live state record
and builds independent uniqueness indexes for exact `state_path` and decoded
`(run_id, sim_sec)`. Duplicate issues are returned before the existing set-universe
comparison. `build_audit()` converts any such issue to aggregate FAIL at
`scripts/validate_state_projection_v2_1.py:852-870`.

Independent exact duplicate-and-rehash result:

```text
evidence states: original row plus exact duplicate
sample_dimensions: states=2, nonzero_live_states=2
semantic_sha256: recomputed
seeded audit bytes: {"status":"STALE_PASS"}
validator exit: 1
replacement status: FAIL
issues: duplicate live state_path; duplicate live run/time identity
```

The checked matrix at `scripts/tests/test_b1a_core_provenance.py:1083-1143` separately
covers an exact duplicate, same path with changed identity, and same identity with
changed path. All three coherently rehash the evidence, exit 1, atomically replace the
audit with FAIL, and preserve the specific duplicate reason.

## New Breakage

No new Critical or Important defect was found in the fix2 approval, manifest,
projection-audit, or focused provenance-test changes.

## Separately Open

- **I3 OPEN:** summary-only live evidence is still self-declared and is not an
  independently authenticated live COM/timing trust anchor. This was explicitly outside
  fix2 and is not a regression from these structural corrections.
- **I4 OPEN:** immutable runner manifest and VBS/watchdog provenance integration remains
  outside fix2 and unchanged.

## Verification

```text
Exact numeric resolved-signal reproducer: exit 1; typed FAIL replaced stale PASS
Exact duplicate-and-rehash reproducer:    exit 1; FAIL with both duplicate reasons
Exact two-test run:                       2 passed in 1.742 s
Focused core/provenance suite:            28 passed in 7.909 s
Live VISSIM COM/timing:                   NOT_EVALUATED
```

No implementation file was edited.
