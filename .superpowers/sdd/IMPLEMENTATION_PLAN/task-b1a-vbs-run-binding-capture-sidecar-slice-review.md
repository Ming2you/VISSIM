# B1a Slice 3B independent adversarial review

Status: CHANGES_REQUIRED

## Findings

### Critical

1. Actual approved A1/A2 topology stocks are incompatible with the vehicle-capture producer.

Evidence:

- `scripts/compile_physical_stock_topology.py` emits `stock["link_no"]` as `parent_no = str(node["link_no"])` and stores it directly in each stock.
- `scripts/build_state_manifest_v2_1.py::_topology_lane_sets` requires `link_no` to be a JSON integer: `if not isinstance(link_no, int) ... raise VehicleCaptureEvidenceError`.
- The B1a slice tests use synthetic topology stocks with integer `link_no`, so they do not exercise the real approved A1/A2 topology schema.

Impact:

The real sidecar producer reads the manifest-approved topology and then calls `_topology_lane_sets`. With the actual A1/A2 topology output, required live capture evidence can fail before producing a PASS sidecar even when VBS captured valid vehicle rows. This violates the required compatibility with the approved A1/A2 topology schema/output and means the tested path is materially easier than the real invoked path.

Required fix:

Accept and canonicalize the actual approved topology stock identity type, or change the approved topology contract and all validators consistently. Add a no-VISSIM test that builds/uses a real `compile_physical_stock_topology.py`-style stock with string `link_no` and proves evidence production succeeds or fails for the intended reason.

### Important

1. Required startup binding and sidecar producer subprocesses are not bounded.

Evidence:

- `ValidateB1aRunBinding` calls `RunCapture3(cmd, outText, errText)`, which waits in `Do While exec.Status = 0` with no timeout.
- `PublishB1aVehicleCaptureEvidence` also calls `RunCapture3(...)` with no timeout.
- Only `ReadRequiredMonotonicClock` uses `RunCapture3Timeout(cmd, 5, ...)`.

Impact:

The slice brief requires startup run binding to happen before COM creation and be bounded so a helper cannot hang. Ordering before COM is correct, but a stuck `build_state_manifest_v2_1.py --validate-run-binding` can hang before COM creation forever. A stuck producer can also hang after immutable state publication and before sidecar failure reporting.

Required fix:

Use a bounded subprocess wrapper for required-mode run-binding validation and capture evidence production, with strict stdout/stderr/exit handling comparable to the monotonic helper. Add fake-helper tests that stall both paths and prove VBS exits closed.

2. State publication does not independently strict-validate the final state bytes before immutable rename.

Evidence:

- `WriteStateJson` writes the state to a temp path, closes it, checks final nonexistence, then calls `fso.MoveFile tempPath, finalPath`.
- The first strict Python parse/run-binding validation of the exact final bytes happens indirectly inside `PublishB1aVehicleCaptureEvidence`, after the final state is already immutable.

Impact:

The brief says strict Python parsing and run binding must accept the exact final bytes as part of the atomic state transaction. Current implementation can leave a final state that the producer rejects, with no PASS sidecar. The orphan allowance is reasonable after sidecar-production failure, but this still weakens the state-publication gate because invalid final bytes are published before the validation result is known.

Required fix:

Validate the temp state bytes with the pinned builder before final rename, then validate the final bytes again or prove same-bytes after rename. Keep the valid-orphan behavior only for failures after a validated immutable state exists.

### Minor

1. The report overstates evidence coverage for real-path topology compatibility.

Evidence:

- Report says deterministic sample selection uses the approved topology.
- The implemented test fixture topology is schema-shaped differently from the actual compiler output for `link_no`.

Impact:

This is mostly documentation/test-evidence drift, but it hides the Critical compatibility issue above.

## Positive checks

- `ValidateB1aRequiredStartup` is called before `CreateObject("Vissim.Vissim")`.
- Required `WriteStateJson` validates allowed capture time before `ScanVehicleState`.
- The monotonic clock helper itself is bounded and enforces single-line `python_perf_counter_ns=<positive decimal>` framing with empty stderr and exit zero.
- Required `vehicle_records` evidence is kept outside the state record schema; the state adds `run_provenance` at the root, not inside records.
- Sidecar publication uses same-directory temp creation and `os.link` create-once semantics on the Python side.
- Empty captures are supported by the VBS table-reader path and producer sample selection logic.

## Focused no-VISSIM review actions

- Read the slice brief and implementation report.
- Reviewed the real invoked VBS path: `ValidateB1aRequiredStartup -> CreateObject("Vissim.Vissim")`, and `WriteStateJson -> ValidateB1aCaptureTime -> ReadRequiredMonotonicClock -> ScanVehicleState -> ReadVerifiedVehicleTables -> atomic state move -> ReadRequiredMonotonicClock -> PublishB1aVehicleCaptureEvidence`.
- Reviewed `scripts/build_state_manifest_v2_1.py` vehicle-capture producer/validator and A1/A2 run-manifest validation path.
- Reviewed `scripts/compile_physical_stock_topology.py` stock schema emission relevant to approved topology compatibility.
- Attempted a focused Python repro for the topology type mismatch, but the local shell did not have `python` on PATH; no production code or tests were edited.
- Checked for active `python`, `cscript`, `wscript`, or `Vissim` processes after interruption; none were found.

## Verdict

CHANGES_REQUIRED

Critical: 1
Important: 2
Minor: 1
