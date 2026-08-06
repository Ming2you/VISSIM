# B1a Slice 3B fix round 4 final independent rereview

Status: CHANGES_REQUIRED

## Findings

### Important

1. Required vehicle_records envelope type/presence checks are still not exact enough for reusable replay validation.

Evidence:

- `scripts/build_state_manifest_v2_1.py::_state_records_by_no` now rederives
  `full_network_link_counts` and `full_network_link_stopped_counts` from strict
  records and compares them on both producer and reusable validator paths. That closes
  the prior bad-link-map finding.
- However, the same shared validator still accepts non-exact envelope scalar types:
  `stopped_threshold_kph` is checked with `!= 1.0`, so JSON `true` and integer `1`
  pass because Python treats `True == 1.0` and `1 == 1.0`.
- `validate_state_run_binding` checks `paused_at_sim_sec`,
  `capture_sim_sec_before`, and `capture_sim_sec_after` with `_finite_nonnegative`
  and `float(value) == sim_sec`, so integer `60` passes where the required live
  state shape uses JSON doubles.
- `unobservable_count` and `external_source_count` are checked with direct
  equality to zero, so JSON `false` passes as `0`.
- Root `total_vehicles` and `stopped_vehicles` are only checked when present:
  `if state.get("total_vehicles") is not None` and the same for stopped. A
  required-mode state with both root totals omitted is accepted by
  `build_vehicle_capture_evidence` and `validate_vehicle_capture_evidence`.

Independent repro results:

- `MISSING_ROOT_TOTALS_ACCEPTED`
- `unobservable_count=BOOL_FALSE_ACCEPTED`
- `external_source_count=BOOL_FALSE_ACCEPTED`
- `stopped_threshold_bool=ACCEPTED`
- `stopped_threshold_int=ACCEPTED`
- `paused_int=ACCEPTED`
- `capture_before_int=ACCEPTED`
- `capture_after_int=ACCEPTED`

Impact:

The live VBS writer currently emits root `total_vehicles`, root
`stopped_vehicles`, and double-shaped capture times, so this is not a direct
called-path COM producer failure. But Slice 3B explicitly introduces a reusable
validator for later post-run replay. That validator can still bless a tampered or
stale required state whose exact live state envelope type contract and root totals
are missing or coercive. This weakens the evidence replay boundary the slice is
supposed to make trustworthy.

Required fix:

Use one shared required-state vehicle-records validator that rejects bool/int
coercion for `stopped_threshold_kph` and capture-time fields, rejects bool values
for all integer count scalars, and requires root `total_vehicles` and
`stopped_vehicles` to be present and equal to the rederived record/stopped totals
on the required capture-evidence producer and reusable validator paths. Add
producer and reusable-validator mutations for each case above.

## Prior issue closure

- Initial Critical, approved A1/A2 string `link_no` incompatibility: CLOSED.
  `_canonical_positive_stock_link_no` accepts compiler-shaped positive decimal
  string stock IDs and rejects malformed/bool/overflow variants. The current
  tests use string `link_no` topology stocks.
- Initial Important, unbounded required startup/sidecar subprocesses: CLOSED.
  VBS required run binding, state binding, monotonic helper, and capture producer
  paths use bounded `RunCapture3Timeout` and exact PASS framing.
- Initial Important, state rename before strict validation: CLOSED. Required
  `WriteStateJson` validates the temp state before no-clobber `MoveFile` and the
  immutable final state before sidecar publication.
- Fix1 Critical, valid-body BOM accepted: CLOSED. Required state/request/sidecar
  paths reject UTF-8 BOM via `_strict_load_json_no_bom`.
- Fix1 Important, huge integer acceptance: CLOSED for capture counts, timer
  endpoints, state/sample IDs, lane IDs, and topology IDs.
- Fix1 Important, concurrent create-once coverage: CLOSED. The test matrix covers
  simultaneous publication through `publish_vehicle_capture_evidence_create_once`.
- Fix2 Important, unbounded required state reads: CLOSED. Producer, validator, and
  CLI state-run-binding paths pass the 8 MiB `MAX_STATE_BYTES` bound.
- Fix2 Important, state record bool/string coercion: CLOSED for per-record
  `veh_no/link_no/lane_no/position_m/speed_kph/stopped` values.
- Fix3 Important, link/stopped maps not rederived from records: CLOSED. The former
  bad link-map mutation is now rejected by producer and validator.
- Raw lane grammar/BOM/bounds/concurrency/topology/timeout/rename/legacy/synthetic
  trust checks remain closed in this rereview. Live VISSIM/COM, real VISSIM version
  readback, live connector/multilane coverage, combined timing/p95, post-run v2.2,
  replay, and B1b remain honestly `NOT_EVALUATED`.

## Test evidence

- PASS: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B -m unittest scripts.tests.test_b1a_vehicle_capture_evidence scripts.tests.test_b1a_vbs_verified_capture_static scripts.tests.test_b1a_watchdog_attempt_launch` -> 39/39.
- PASS: former bad-link-map regression reproduced through
  `scripts.tests.test_b1a_vehicle_capture_evidence.VehicleCaptureEvidenceTests.test_state_envelope_counts_are_rederived_in_producer_and_validator`.
- PASS outside sandbox: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior` -> 3/3, no VISSIM/COM.
- Sandbox helper run failed with Windows Script Host settings access denied before the approved outside-sandbox rerun.
- No VISSIM/COM run was started.

## Verdict

CHANGES_REQUIRED

Critical: 0
Important: 1
Minor: 0
