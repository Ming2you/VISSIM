# B1a Core/Provenance Slice Report

## Status

**IMPLEMENTED_CORE / NOT PROMOTABLE**

The controller-independent A2 trust validator, immutable interval index, per-vehicle
projector, atomic projection ledger writer, topology approval producer, closed
state-manifest producer, and offline projection validator are implemented. Synthetic
projection can produce a `projection-v2.1` PASS sidecar. The aggregate remains
`NOT_EVALUATED` because supported-version live COM capture and live end-to-end timing
were not evaluated in this scope.

B1a as a whole is not complete or promotable: the VBS capture path, online adapter,
bounded action reference, authoritative auditor path, and live qualification were
outside the exclusive write scope. B1b dynamics remain unimplemented by this slice.

## Changed Files

- `plant/src/vissim_strict/physical_projection.py`
- `plant/src/vissim_strict/__init__.py`
- `plant/tests/test_vissim_strict_physical_projection.py`
- `scripts/approve_physical_stock_topology.py`
- `scripts/build_state_manifest_v2_1.py`
- `scripts/validate_state_projection_v2_1.py`
- `scripts/tests/test_b1a_core_provenance.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-core-report.md`

No existing A1/A2 implementation or test, VBS file, adapter, auditor, NumSim file, or
B1b dynamics file was edited by this slice.

## Implemented Contracts

### A2 validation and lookup

- Requires `physical-stock-topology-v2.1`, `status=PASS`, empty reasons, all global
  artifact fields, exact units/consumer/objective metadata, and a recomputed matching
  A2 semantic hash.
- Independently validates A1 lane coverage, numeric lane-key normalization, canonical
  stock IDs, unique stocks/edges, exact contiguous intervals, exact final lane ends,
  finite values, roles, owner state and weights, visibility, objective weights,
  sample dimensions, and production gates.
- Constructs an immutable numeric `(link_no,lane_no)` binary-search index.
- Uses exact internal half-open intervals. Only the outer start/final end use the A2
  tolerance, inclusive at `-tol` and `lane_end+tol`.

### Vehicle projection

- Strict JSON rejects duplicate object keys and `NaN`/`Infinity` tokens.
- The exact `vissim-vehicle-records-v2.1` envelope and six-field record shape are
  required for projection. IDs, times, scalar identities, stopped derivation, complete
  full-network count/stopped maps (including zero stopped counts), and state total are
  checked fail-closed.
- `project_vehicle_records()` accepts only `ValidatedPhysicalTopology`, returns an
  immutable `ProjectionResult`, or raises typed `ProjectionError`.
- Assignments are sorted by `(run_id,sim_sec,veh_no)` and expose only
  `exact_interval` or `outer_endpoint_tolerance_snap` as the success enum.
- Stock counts include the complete stock universe. Objective, owner, role, and
  visibility summaries keep role/visibility overlap non-partitioning.
- Sidecars are atomically written beside states as
  `<state-stem>.physical_projection_v2_1.json`.

### Approval and state provenance

- `topology-approval-v2.1` recomputes preflight fingerprint/source bytes, A1 graph and
  route contracts/hashes, A2 bytes/semantic hash/structure, all cross-bindings, and all
  contained workspace-relative source paths.
- `state-selection-v2.1` is a closed input. No glob, retry, archive, or sidecar discovery
  exists. Selection path/file/semantic hashes, campaign ID, count, policy flags, and
  canonical entries are revalidated by both producer and consumer.
- `state-manifest-v2.1` uses `base_dir: ".."`, requires it to resolve exactly to the
  supplied canonical workspace, hashes every state/run manifest, derives the one exact
  sidecar name, and rejects path escape, absolute child paths, duplicate states, and
  duplicate run/time identities.
- A run ID may bind only one immutable run-manifest path/hash. Run manifests bind the
  approved topology and configuration, may contain a closed allowed-capture-time list,
  and reject mutable actual snapshot-time fields.
- Every usable invocation replaces `--out` atomically with PASS, FAIL, or
  NOT_EVALUATED evidence. Exit codes are approval/manifest `0=PASS,1=FAIL`; projection
  audit `0=PASS,1=FAIL,2=NOT_EVALUATED`.

## Hash Scopes

- Approval `semantic_sha256`: canonical JSON over exactly
  `schema_version/input_hashes/command_version/sample_dimensions/units/downstream_consumers/workspace_root_relative_to_artifact/source_inputs/approved_topology`.
- Selection `semantic_sha256`: canonical JSON over exactly
  `schema_version/input_hashes/command_version/sample_dimensions/units/downstream_consumers/campaign_id/expected_entry_count/entries`.
- `state_set_semantic_sha256`: canonical sorted list of the eight required state-entry
  fields, including `required_vehicle_records` and derived sidecar path.
- State-manifest `semantic_sha256`: canonical JSON over exactly the required manifest
  scope through `states`, excluding status/reasons and the hash itself as specified.
- `vehicle_records_semantic_sha256`: the complete validated vehicle envelope with
  records normalized and sorted by integral `veh_no`; source row order is excluded.
- `normalized_projection_sha256`: canonical assignments plus complete stock counts and
  the approved topology semantic hash.
- Projection `semantic_sha256`: the complete behavioral ledger, including exact byte
  hashes in `input_hashes`, status/reasons, summaries, diagnostics, and normalized hash.

The projection input hash names are exactly
`topology_file_sha256`, `topology_semantic_sha256`,
`approving_manifest_sha256`, `state_file_sha256`, and
`vehicle_records_semantic_sha256`.

## Verification

Focused tests:

```text
python -B -m unittest \
  plant.tests.test_vissim_strict_physical_projection \
  scripts.tests.test_b1a_core_provenance -v
```

Result: **16 passed**. Coverage includes all named split/end tolerance values, just
outside both outer tolerances, duplicate identity, same vehicle at later time/across
runs, invalid run/time/numeric inputs, unknown lanes, aggregate/stopped/total failures,
immutable outputs, strict JSON, boundary and
multi-owner closure, ten record permutations, ten independently compiled input
orders, approval/selection/state tampering, absolute child rejection, empty selection,
required versus optional missing envelopes, and stale PASS replacement.

A1/A2 regressions:

```text
python -B -m unittest \
  scripts.tests.test_build_preflight_manifest \
  scripts.tests.test_vissim_lane_graph \
  scripts.tests.test_vissim_lane_graph_real_network \
  scripts.tests.test_compile_physical_stock_topology \
  scripts.tests.test_compile_physical_stock_topology_real_network -v
```

Result: **54 passed**.

```text
PYTHONPATH=plant python -B -m unittest \
  plant.tests.test_vissim_strict_compiler -v
```

Result: **5 passed**. The first combined invocation omitted `PYTHONPATH=plant` for this
module and produced an import-only harness error; the corrected command above passed.

Final focused rerun after hardening: **16 passed**.

## Synthetic Performance Evidence

One 20,000-record synthetic run measured state serialization, strict parse, envelope
normalization, projection, and sidecar serialization/write:

```text
state_bytes=1827488
sidecar_bytes=5406964
serialize_parse_project_write_sec=1.462580
assigned=20000
residual=0
```

This is below the 8 MiB state, 16 MiB sidecar, and 3.0 s synthetic core limits on this
host. It excludes VBS COM capture and the bounded adapter action reference, so it is not
claimed as the required live combined p95.

## Self-Review

- Rehashed structural topology tampering fails independently of lookup behavior.
- Byte tampering in graph, selection, state, run manifest, approval, or topology cannot
  be masked by repeated self-declared hashes.
- Internal boundaries are never tolerance-expanded; no nearest/minimum/owner fallback
  exists.
- Failed state replay atomically replaces a stale PASS sidecar; malformed global replay
  atomically replaces a stale PASS audit; failed approval/manifest construction replaces
  stale PASS outputs.
- Required missing vehicle records are FAIL; policy-authorized absence is
  NOT_EVALUATED; empty closed selection is NOT_EVALUATED.
- No live PASS or performance PASS is fabricated.

## Remaining Concerns and Gates

- Supported VISSIM COM capture: **NOT_EVALUATED**.
- Live nonzero road/connector/multilane samples and parser evidence: **NOT_EVALUATED**.
- Live combined capture/serialize/parse/project p95: **NOT_EVALUATED**.
- Bounded online action reference and online/offline parity through the adapter:
  **NOT_EVALUATED** (public projector/offline side is implemented).
- VBS one-scan table/key/count/format/escape behavior and fail-before-controller adapter
  behavior remain outside this exclusive write scope.
- Authoritative `audit_plant_fidelity.py` consumption remains outside this scope.
- B1b substep debit/credit, clipping removal, and physical total dynamics remain open.
