# B1a verified paused COM capture VBS report

## Status

- Implementation status: **IMPLEMENTED** for the scoped VBS capture/emission slice.
- Promotion status: **NOT_EVALUATED**. No supported-version live VISSIM COM run was performed.
- B1a completion boundary: this report covers only verified paused capture and the
  `vissim-vehicle-records-v2.1` state envelope. It does not claim B1b, projection
  sidecar, manifest, approval, adapter, auditor, or mass-ledger completion.

## Changed files

- `scripts/run_real_world_stackelberg_controller.vbs`
  - Extends the called `ScanVehicleState` path with one bracketed capture:
    `Vehicles.Count`, `Simulation.AttValue("SimSec")`, No/Lane/Pos/Speed tables,
    then the second Count/SimSec reads.
  - Requires stable scalar counts/times, exact matching two-dimensional table bounds,
    two key/value columns, row-count equality, equal per-row COM keys, key=`No`, and
    unique positive 32-bit vehicle numbers.
  - Parses Lane with the complete anchored ASCII horizontal-whitespace grammar and
    rejects malformed, signed, decimal, zero, extra-component, and overflow forms.
  - Rejects malformed/nonfinite numeric Variants, positions below `-1e-6 m`, and
    negative speeds without coercing failures to zero.
  - Builds records, full-network count maps, stopped maps, and legacy masked
    aggregates in the same row loop; verifies record/unique/map scalar identities.
  - Emits the exact `vehicle_records` envelope and six-field records using invariant
    high-precision doubles, complete U+0000..U+001F JSON escaping, numeric map sorting,
    streamed ADODB writes, and UTF-8 without BOM.
  - Preserves `local_observation.schema_version=2`, its masked universe/zero-key
    behavior, and the existing aggregate/state behavior.
- `scripts/tests/test_b1a_vbs_verified_capture_static.py`
  - Traces `WriteStateJson -> ScanVehicleState -> ReadVerifiedVehicleTables` and the
    called lane/parser/emitter path.
  - Pins bracketing order, no intervening simulation method, shape/key/duplicate/fail
    branches, streamed construction, escaping, precision, and legacy separation.
  - Includes adversarial dead-parser and dead-reader mutants that must fail despite
    decoy strings and unused procedures remaining in the source.
- `scripts/tests/test_b1a_vbs_capture_helpers_behavior.py`
  - Executes extracted production helpers under Windows Script Host without COM.
  - Pins accepted lanes `1-1`, `1220012103-2`, and ` 1220012103-2 ` and all briefed
    rejected examples, plus overflow and control-character cases.
  - Exercises strict numeric types/tolerance, exact 2-D and explicit empty shapes,
    complete control escaping, BOM-free zero/nonzero parsed JSON envelopes, exact
    record keys, stopped-map zero-key exclusion, and 20,000-record serialization.

## Schema emitted

- Envelope: `vehicle_records.schema_version = "vissim-vehicle-records-v2.1"`.
- Envelope fields: `schema_version`, `complete`, `paused_at_sim_sec`, both capture
  times, `source_attributes`, `stopped_threshold_kph`, both collection counts,
  `record_count`, both required zero-count fields, both full-network maps, and
  `records`.
- Record fields, exactly: `veh_no`, `link_no`, `lane_no`, `position_m`, `speed_kph`,
  and `stopped`.
- Stopped rule: unrounded COM speed `< 1.0 kph`; equality is moving.

## Verification

- VBS compile check: `cscript.exe //nologo scripts\run_real_world_stackelberg_controller.vbs`
  reached the expected argument-usage exit, proving whole-file compilation without
  attempting COM.
- B1a focused: `python -B -m unittest discover -s scripts\tests -p 'test_b1a_vbs*.py' -v`
  -> **7/7 PASS**.
- Runner focused: `python -B -m unittest discover -s scripts\tests -p 'test_run_plant_fidelity_matrix.py' -v`
  -> **11/11 PASS**.
- Auditor adjacent: `python -B -m unittest discover -s scripts\tests -p 'test_audit_plant_fidelity.py' -v`
  -> **31/31 PASS**.
- Adapter adjacent: `python -B -m unittest discover -s tests -p 'test_vissim_stackelberg_adapter_fidelity.py' -v`
  -> **2/2 PASS**.
- Scoped `git diff --check` -> **PASS**; only the existing LF-to-CRLF worktree warning
  was reported for the VBS file.

## Performance evidence

- Synthetic record count: **20,000**.
- Serialized envelope bytes: **2,691,962 bytes**, below the 8 MiB state-envelope cap.
- Ten Windows Script Host process/serialization samples: **p95 0.452337 s**
  (minimum 0.388503 s, maximum 0.452337 s), below 3.0 s on this host.
- Construction: record emission is streamed O(N); numeric map ordering is O(K log K)
  over observed link keys; JSON escaping uses a fixed-size piece array and one Join.
- Sidecar/action sizes and combined live capture + parse + projection p95 are
  **NOT_EVALUATED** because they are outside this VBS-only slice and no live capture
  or scoped projector change was permitted.

## Online/offline and live gates

- Online/offline projector parity: **NOT_EVALUATED** in this VBS-only slice.
- Live COM capture: **NOT_EVALUATED**. No claim of live COM PASS is made.
- Missing live evidence: nonzero supported-version population; representative raw
  No/Lane/Pos/Speed key/value samples; raw road and connector Lane strings; one
  multi-lane road; both scalar counts/times; runner-produced UTF-8 state accepted by
  the public projector; zero projection identity residual; and live timing p95.
- A zero-vehicle synthetic envelope passed behavior tests but is not treated as a
  sufficient live gate.

## Self-review

- Confirmed all four tables are read once in the called scan and no simulation method
  occurs inside the bracketing reader.
- Confirmed failure increments COM evidence, leaves `scanOk=False`, increments
  observation evidence in the caller, and exits before opening/publishing state JSON.
- Confirmed legacy masked link aggregates still use `RW_LOCAL_OBSERVABLE_LINKS`; new
  full-network identities use only validated records and do not inherit legacy zero
  keys.
- Confirmed pre-existing worktree changes were retained and no Python projector,
  approval, manifest, validator, adapter, auditor, A1/A2, NumSim, or dynamics file was
  edited for this task.
