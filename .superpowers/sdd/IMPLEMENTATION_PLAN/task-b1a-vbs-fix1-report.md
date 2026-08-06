# B1a VBS fix round 1 report

## Status

- Scoped VBS fix status: **IMPLEMENTED**.
- Independent-review accepted findings: **FIXED**.
- Review Critical 2 envelope-location finding: **REJECTED BY ADJUDICATION**.
  The revised brief normatively requires root-level `vehicle_records` as a sibling of
  legacy masked `local_observation`; that placement is preserved and directly tested.
- Supported-version live VISSIM COM: **NOT_EVALUATED**. No live COM PASS or promotion
  claim is made.

## Changed files

- `scripts/run_real_world_stackelberg_controller.vbs`
  - Recurring `RunStepwiseMode` now reaches `stepNo` with `RunSingleStep` before
    `RunControllerDecision stepNo`. State capture, action filenames, action CSV
    application, and runtime action calls retain the `stepNo` epoch.
  - Full-network stopped counts now initialize an explicit zero for every counted
    link and increment that same link key for stopped records.
  - Both scan callers now invoke `AbortVehicleObservation`, which increments one
    observation failure and prints exact `OBSERVATION_FAILURES` and `COM_FAILURES`
    before exit 13.
  - Removed end-of-run synthesis of COM failures from signal/observation counters;
    independently counted failure classes are no longer folded together.
  - Root-level `vehicle_records` placement remains unchanged and normative.
- `scripts/tests/test_b1a_vbs_verified_capture_static.py`
  - Adds caller-order assertions for initial and recurring stepwise, continuous-static,
    and event-continuous modes while verifying the action epoch remains unchanged.
  - Adds a normative root-sibling placement test.
  - Adds exact record link/lane assignments, explicit stopped zero-key construction,
    one-read-per-table, early-reader reachability, finite guard, locale normalization,
    and exact abort/counter path assertions.
  - Adversarially rejects every listed mutation: dead reader early exit, duplicate No
    read, record link/lane swap, stopped map keyed by lane, finite guard removal, and
    locale normalization removal.
- `scripts/tests/test_b1a_vbs_capture_helpers_behavior.py`
  - Fixes discovery and dotted-module imports.
  - Executes production `ReadVerifiedVehicleTables` and `ScanVehicleState` with a
    fake COM hierarchy and verifies one read per table, exact records/maps/times, and
    explicit moving-link stopped zero.
  - Emits the actual scan result with production VBS helpers, parses the UTF-8 JSON,
    and passes its root `vehicle_records` directly to core
    `normalize_vehicle_records`; parity passes.
  - Executes German LCID 1031 numeric formatting and exact capture-failure exit output.
- `scripts/tests/test_run_plant_fidelity_matrix.py`
  - Updates the dedicated VBS counter fixture to require exact reachable summaries
    and reject the removed counter-synthesis expression.
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-vbs-fix1-report.md`
  - This report.

## Finding disposition

### Critical 1 - recurring stepwise timing

**FIXED.** The recurring order is now:

```text
RunSingleStep -> ValidateRuntimeSignalPersistence -> RunControllerDecision stepNo
-> ApplyRuntimeSignals/ApplyRuntimeRampMeters/ApplyIncidentLaneClosure stepNo
```

COM is paused at the same `stepNo` supplied to `WriteStateJson`. The action epoch is
not silently shifted: state/action filenames, adapter invocation, action application,
and runtime action calls remain labeled `stepNo`. All three run modes have caller-order
tests, including their initial decision.

### Critical 2 - envelope location

**REJECTED BY ADJUDICATION / NO CODE MOVE.** The current brief explicitly requires
root-level `vehicle_records` as a sibling of `local_observation`. Static and parsed JSON
tests now assert root presence and absence under `local_observation`.

### Critical 3 - core stopped-map parity

**FIXED.** Every key in `full_network_link_counts` is initialized in
`full_network_link_stopped_counts`, including zero for moving-only links. The fake-COM
scan emits `{"1": 1, "1220012103": 0}` and the actual parsed VBS envelope is accepted
by core `normalize_vehicle_records` with the same normalized map.

### Important 1 - reachable failure counters

**FIXED.** A production failure-path harness calls `RecordVehicleCaptureFailure` then
`AbortVehicleObservation` and observes exit 13 with exactly:

```text
ERROR=B1A_VEHICLE_CAPTURE_FAILED reason=invalid_table_shape test=failure_path
ERROR=VEHICLE_OBSERVATION_SCAN_FAILED sim_sec=900
OBSERVATION_FAILURES=1
COM_FAILURES=1
```

The abort helper does not increment COM failures, and the end-of-run max/sum synthesis
was removed.

### Important 2 - load-bearing false PASSes

**FIXED.** The suite now rejects all six listed source mutations. The executable fake-
COM flow covers the called reader/scan, record link/lane assignment, table read counts,
stopped-map keys, and emitter-to-core interface. Static checks retain coverage for the
nonfinite guard that cannot be reliably synthesized as a VBScript numeric value.

### Minor 1 - dotted-module import

**FIXED.** Both discovery and
`python -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior -v`
pass.

## Verification

- B1a VBS static/fake-COM/helper/core-parity: **11/11 PASS**.
- Dotted helper module invocation: **2/2 PASS**.
- Runner regression: **11/11 PASS**.
- Physical projection core: **9/9 PASS**.
- Auditor regression: **31/31 PASS**.
- Adapter-fidelity regression: **2/2 PASS**.
- A1 lane graph/routes, synthetic and real network: **24/24 PASS**.
- A2 physical-stock topology, synthetic and real network: **19/19 PASS**.
- Whole-file VBS compilation reached the expected argument-usage gate without COM.
- Scoped `git diff --check`: **PASS**; only the existing VBS LF-to-CRLF warning was
  reported.

## Performance

- Synthetic records: **20,000**.
- Revised envelope size: **2,692,009 bytes**, below 8 MiB.
- Ten fake-COM/helper process samples: p95 **0.423576 s**
  (minimum 0.383442 s, maximum 0.423576 s), below 3.0 s on this host.
- Live capture + serialization + parse + projection p95 remains **NOT_EVALUATED**.

## Self-review and remaining gates

- Confirmed root-level full-network and nested legacy masked universes remain separate.
- Confirmed recurring stepwise state/action epoch is `stepNo` after COM reaches
  `stepNo`, matching continuous-mode capture ordering.
- Confirmed moving-only counted links emit explicit stopped zeros and pass the core
  normalizer without test-side envelope repair.
- Confirmed every capture-failure branch records one COM/observation event, then both
  callers publish exact counters before nonzero exit and before state publication.
- Confirmed no projector, approval, manifest, validator, adapter, auditor, A1/A2,
  NumSim, dynamics, or control-policy implementation file was edited in this fix.
- Remaining live gates: supported-version nonzero VISSIM population, connector and
  multi-lane road samples, raw four-table key/value evidence, runner state accepted by
  the public projector, zero live identity residual, and live p95 timing. All remain
  **NOT_EVALUATED**.
