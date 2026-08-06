# B1a Slice 3B fix round 3 rereview

Status: CHANGES_REQUIRED

## Findings

### Important

1. Reusable capture evidence validation does not rederive the state envelope link-count maps from `records`.

Evidence:

- `scripts/build_state_manifest_v2_1.py::_state_records_by_no` validates the exact six record fields and typed values, but it does not validate the surrounding `vehicle_records` envelope shape beyond the presence of `records`.
- `build_vehicle_capture_evidence` and `validate_vehicle_capture_evidence` check only `collection_count_before`, `collection_count_after`, and `record_count` against the request/evidence counts and `len(records_by_no)`.
- Neither producer nor reusable validator checks that `vehicle_records.full_network_link_counts` equals the per-link totals derived from the records, or that `vehicle_records.full_network_link_stopped_counts` equals the per-link stopped totals derived from records.
- Independent mutation repro changed a valid state to:
  - `full_network_link_counts = {"10": 4}`
  - `full_network_link_stopped_counts = {"10": 4}`
  while leaving records/raw rows/count fields unchanged. Both paths accepted it:
  - `producer_ACCEPTED_BAD_LINK_MAPS`
  - `validator_ACCEPTED_BAD_LINK_MAPS`

Impact:

The actual VBS scan path has a generation-time guard for `B1aCountMapTotal(fullLinkCounts) <> total` and `B1aCountMapTotal(fullLinkStoppedCounts) <> stopped`, so this is not a live producer COM-path break by itself. However, Slice 3B explicitly introduces a reusable validator for later post-run replay. That validator can bless a tampered or stale state whose records and sidecar samples are internally consistent but whose state envelope link maps are physically false. This weakens the evidence replay contract and the requested envelope/count consistency check.

Required fix:

Add a shared Python state-envelope validator that, after exact record validation, rederives:

- total record count;
- per-link counts keyed by canonical decimal `link_no`;
- per-link stopped counts keyed by canonical decimal `link_no`;
- stopped total from `speed_kph < 1.0`.

Require those values to equal the state envelope's `collection_count_before`, `collection_count_after`, `record_count`, `full_network_link_counts`, and `full_network_link_stopped_counts` in both `build_vehicle_capture_evidence` and `validate_vehicle_capture_evidence`. Add producer and reusable-validator mutation tests for wrong link counts, missing/extra link keys, wrong stopped counts, and count-map type coercions.

## Prior issue closure

- Initial Critical, approved A1/A2 string `link_no` topology incompatibility: CLOSED. `_canonical_positive_stock_link_no` accepts compiler-shaped positive decimal string `link_no` and rejects malformed/boolean/overflow variants; a real manifest validation fixture exercises string topology.
- Initial Important, unbounded required startup/sidecar subprocesses: CLOSED. `ValidateB1aRunBinding`, `ValidateB1aStateRunBinding`, `ReadRequiredMonotonicClock`, and `PublishB1aVehicleCaptureEvidence` all use `RunCapture3Timeout`; VBS static tests confirm exact PASS framing and timeout runner usage.
- Initial Important, state rename before strict validation: CLOSED. Required `WriteStateJson` validates the same-directory temp before `MoveFile`, then validates the immutable final state after `MoveFile`, before monotonic end and sidecar publication.
- Fix1 Critical, valid-body BOM accepted: CLOSED. Required state/request/sidecar paths use `_strict_load_json_no_bom` and no-BOM bounded loaders; valid-body BOM CLI tests are present.
- Fix1 Important, huge timer/integer acceptance: CLOSED. Counts and sample/state identifiers are bounded to positive signed 32-bit where applicable, timer endpoints to positive signed 64-bit, and mutation tests cover huge values.
- Fix1 Important, concurrent create-once coverage: CLOSED. `test_concurrent_create_once_publish_has_one_immutable_winner` runs simultaneous workers through the real `publish_vehicle_capture_evidence_create_once` path and checks exactly one immutable winner.
- Fix2 Important, required state reads unbounded: CLOSED. The actual required state loads in capture production, reusable capture validation, and CLI `--validate-state-run-binding` all pass `max_bytes=MAX_STATE_BYTES`, imported from the existing 8 MiB projection state bound.
- Fix2 Important, state record bool/string coercion: CLOSED. `_state_records_by_no` rejects string, bool, int, nonfinite, negative speed, excessive negative position, stopped mismatch, extra fields, and missing fields. Raw/state comparisons no longer coerce with `float(...)`.
- Adjacent raw-lane binding invariant: CLOSED. Python `_parse_vbs_lane_raw` mirrors called VBS `ParseB1aLaneId`: horizontal trim only, one hyphen, canonical positive signed-32-bit ASCII decimal components. Raw lane text must reparse to `parsed_link_no/parsed_lane_no`.
- Legacy provenance compatibility: CLOSED. Required provenance has `run_id`, workspace-relative `manifest_path`, and lowercase `manifest_sha256`; legacy mode preserves the original two-field form and cannot emit required PASS evidence.
- No stale/synthetic/dry live PASS found in this Slice 3B scope. Live COM, real VISSIM version coverage, connector/multilane live sample coverage, combined timing/p95, post-run v2.2, replay, and B1b remain `NOT_EVALUATED`.

## Test evidence

- PASS: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B -m unittest scripts.tests.test_b1a_vehicle_capture_evidence scripts.tests.test_b1a_vbs_verified_capture_static scripts.tests.test_b1a_watchdog_attempt_launch` -> 37/37.
- PASS outside sandbox: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior` -> 3/3, no VISSIM/COM.
- PASS with warnings only: `git diff --check -- scripts\build_state_manifest_v2_1.py scripts\run_real_world_stackelberg_controller.vbs scripts\tests\test_b1a_vehicle_capture_evidence.py scripts\tests\test_b1a_vbs_verified_capture_static.py scripts\tests\test_b1a_vbs_capture_helpers_behavior.py scripts\tests\test_b1a_watchdog_attempt_launch.py scripts\run_real_world_single_watchdog_distributed_core15n41.ps1`; warnings were existing LF-to-CRLF notices for the VBS/PS1 files.
- PASS no-COM parse/usage check outside sandbox: `cscript.exe //nologo scripts\run_real_world_stackelberg_controller.vbs` printed usage and exited before COM creation.
- FAIL by independent mutation repro: producer and validator accepted a state whose `full_network_link_counts` and `full_network_link_stopped_counts` contradicted the exact records.

## Verdict

CHANGES_REQUIRED

Critical: 0
Important: 1
Minor: 0
