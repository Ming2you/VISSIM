# B1a Core Fix Round 1 Report

## Status

**C1/C2/I1/I2/I3/M1 FIXED; I4 OPEN; LIVE READINESS NOT_EVALUATED**

This round stayed within the B1a core/script/test scope. No VBS, watchdog, adapter,
auditor, A1/A2 implementation/test, NumSim, or B1b dynamics file was edited.

## Finding Disposition

### C1 - independent A2/preflight trust anchor: FIXED

- Approval now validates the exact preflight top-level contract, producer hash,
  fingerprint, artifact hash universe, required artifact check records, and required
  A2 source artifact names.
- Every preflight source artifact and resolved signal-program path is resolved and
  required to remain below the canonical workspace root. `python_executable` is the
  sole non-source exception and must resolve exactly to the currently executing Python
  interpreter.
- A1 graph and route producer command records are reconstructed from current behavioral
  sources. Their network byte hash, graph semantic hash, and route source bindings are
  replayed against the contained preflight network.
- Approval reloads contained ownership, adjacency, and capacity evidence, reconstructs
  the five raw A2 source-file hashes, reruns
  `compile_physical_stock_topology()`, requires replay PASS, and compares the complete
  replayed artifact to the candidate topology. Default production evidence paths retain
  A2's pinned production file and semantic hashes.
- Consumer structural validation now closes the A2 top-level shape, canonical JSON
  version, semantic/raw input hash names and bindings, command provenance, exact sample
  dimensions, route-membership shape, and stock-edge endpoint positions.
- Approval `command_version` must be exactly `{}` and
  `workspace_root_relative_to_artifact` must be exactly `".."`; the producer only
  writes the specified `outputs/topology_approval_v2_1.json` path.
- Adversarial tests reject coherently rehashed owner/view, canonical-version,
  command/source-command-hash, input/source-artifact hash, extra dimension, edge
  position, and route-membership mutations. Rehashed approval command/root mutations
  also reject.

### C2 - huge standard-JSON integers and stale outputs: FIXED

- Finite-number validation catches `OverflowError` before every float conversion used
  by topology, state-selection, manifest, and projection validation.
- Approval, manifest, and audit producer boundaries convert remaining
  `OverflowError`/type failures into typed FAIL artifacts when `--out` is usable.
- Reproducers using `10**400` in topology `length_m`, selection `sim_sec`, and state
  `speed_kph` all exit 1 and atomically replace seeded stale PASS approval, manifest,
  audit, and projection sidecar outputs. Tests assert the closed typed reason codes.

### I1 - optional envelope masking trust failure: FIXED

An absent optional envelope becomes `NOT_EVALUATED` only when state bytes, run-manifest
bytes, approved topology, run/time provenance, and all path bindings already pass.
Accumulated trust failures force a FAIL sidecar and aggregate FAIL. The exact state-byte
tamper reproducer is checked in.

### I2 - nested preflight containment: FIXED

Both nested preflight artifact paths and resolved signal-program paths are contained
after canonical resolution. Sibling-directory artifact and signal-file reproducers now
exit 1 and replace stale approval output.

### I3 - unreachable audit PASS: FIXED AS A CONTRACT, LIVE GATE NOT RUN

`validate_state_projection_v2_1.py` accepts optional `--live-evidence`. The exact new
`projection-live-evidence-v2.1` contract binds:

- exact state-manifest file/semantic and state-set hashes;
- exact approval and topology file/semantic hashes;
- every selected state byte hash, run/time identity, scalar COM counts, projection
  counts, stock total, and zero residual;
- nonzero raw four-attribute COM samples with called lane-parser outputs bound back to
  exact state records and A1 lanes;
- representative connector and multi-lane-road samples, supported-version attestation,
  UTF-8-without-BOM state bytes, and public-projector parse success;
- a 20,000-record performance qualification, size limits, at least 20 combined
  `live_com_capture+serialize+strict_parse+public_project+atomic_sidecar_write` samples,
  recomputed nearest-rank p95, the 3.0 s ceiling, and 10% of the 30 s budget.

Its `semantic_sha256` covers exactly
`schema_version/input_hashes/command_version/sample_dimensions/units/downstream_consumers/states/performance`.
Missing evidence remains `NOT_EVALUATED`; malformed, stale, incomplete, zero-population,
or over-budget supplied evidence is FAIL. A temporary synthetic contract fixture proves
the PASS branch is reachable and that coherently rehashed timing failure rejects; it is
not live VISSIM evidence and creates no checked-in PASS claim. Actual live COM and live
p95 remain `NOT_EVALUATED`.

### M1 - performance scope mismatch: FIXED

The checked-in 20,000-record test now starts timing before atomic state serialization,
then performs strict file parse, envelope normalization, public projection, and atomic
sidecar serialization/write before stopping. It asserts the 8 MiB state, 16 MiB
sidecar, and 3.0 s synthetic-core limits. The claim remains explicitly offline and
does not include COM capture or an adapter action reference.

### I4 - VBS/run-manifest compatibility: OPEN BY REQUEST

No VBS or watchdog runner was edited in this round. The current worker/runner alignment
with immutable `run-manifest-v2.1`, including `manifest_sha256`, remains for the
separately scoped VBS rereview and is still a promotion blocker.

## Changed Files

- `plant/src/vissim_strict/physical_projection.py`
- `plant/src/vissim_strict/__init__.py`
- `plant/tests/test_vissim_strict_physical_projection.py`
- `scripts/approve_physical_stock_topology.py`
- `scripts/build_state_manifest_v2_1.py`
- `scripts/validate_state_projection_v2_1.py`
- `scripts/tests/test_b1a_core_provenance.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-core-fix1-report.md`

## Verification

```text
python -B -m unittest \
  plant.tests.test_vissim_strict_physical_projection \
  scripts.tests.test_b1a_core_provenance -v
```

Result: **24 passed in 4.759 s**.

```text
python -B -m unittest \
  scripts.tests.test_build_preflight_manifest \
  scripts.tests.test_vissim_lane_graph \
  scripts.tests.test_vissim_lane_graph_real_network \
  scripts.tests.test_compile_physical_stock_topology \
  scripts.tests.test_compile_physical_stock_topology_real_network -v
```

Result: **54 passed in 114.986 s**.

```text
PYTHONPATH=plant python -B -m unittest \
  plant.tests.test_vissim_strict_compiler -v
```

Result: **5 passed in 24.705 s**.

AST parsing of all six changed Python implementation/test files: **6 passed**.
`py_compile` was not used because this sandbox denied creation of package
`__pycache__`; all tests ran with `-B`, and the no-write AST parse covered syntax.

## Remaining Concerns

- I4 is open exactly as requested; current VBS/watchdog provenance compatibility is not
  certified by this core round.
- Supported-version live COM capture, real connector/multi-lane samples, and live
  combined p95 are `NOT_EVALUATED`; B1a is not promotable from synthetic evidence.
- Online adapter bounded-reference parity and authoritative auditor consumption remain
  outside this exclusive core scope.
