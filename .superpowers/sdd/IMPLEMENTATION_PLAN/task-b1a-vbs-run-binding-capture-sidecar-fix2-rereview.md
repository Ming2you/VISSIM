# B1a Slice 3B fix round 2 rereview

Status: CHANGES_REQUIRED

## Findings

### Important

1. Required state JSON reads are still unbounded on the actual evidence paths.

Evidence:

- `scripts/build_state_manifest_v2_1.py:218` added `_strict_load_json_no_bom(path, max_bytes=None)`, and the bounded path is only used when a caller passes `max_bytes`.
- The actual required-state consumers call it without a bound: producer state load at `scripts/build_state_manifest_v2_1.py:444`, reusable evidence validator state load at `scripts/build_state_manifest_v2_1.py:550`, and CLI `--validate-state-run-binding` at `scripts/build_state_manifest_v2_1.py:1099`.
- Request and sidecar are bounded (`MAX_CAPTURE_REQUEST_BYTES`, `MAX_CAPTURE_EVIDENCE_BYTES`), but state is not. `plant/src/vissim_strict/physical_projection_reference.py:41` already has an 8 MiB state bound used elsewhere, so the missing bound is not a deliberate global contract.

Impact:

The user-requested adversarial check explicitly required bounded state input. A required VBS helper or post-run validator can still read an arbitrarily large state file into memory before failing, which violates the fail-closed evidence boundary and weakens the no-VISSIM replay validator.

Required fix:

Define a Slice-3B state JSON byte limit, reuse the existing projection state bound if that is the intended contract, and pass it on every required state load in `build_vehicle_capture_evidence`, `validate_vehicle_capture_evidence`, and `--validate-state-run-binding`. Add a real CLI oversize-state test proving failure before schema/run-binding acceptance.

2. State record numeric fields can still pass through bool/string coercion.

Evidence:

- `scripts/build_state_manifest_v2_1.py:400-402` strictly bounds `veh_no`, `link_no`, and `lane_no`, but `_state_records_by_no` does not validate `position_m` or `speed_kph`.
- `_normalize_raw_rows` compares state and raw rows with `float(state_record.get("position_m")) != position` and `float(state_record.get("speed_kph")) != speed` at `scripts/build_state_manifest_v2_1.py:344-345`.
- Therefore otherwise matching state records with `"position_m": "1.0"` / `"speed_kph": "10.0"` or boolean numeric values can compare equal to valid raw JSON doubles instead of failing exact state-record type validation.

Impact:

The brief preserves the exact six-field vehicle-record schema and the requested rereview specifically required that state record numeric types not exploit bool/string coercion. The current producer/validator can accept a malformed or tampered state record and still publish/validate a PASS capture sidecar if the raw row numerically matches after Python coercion.

Required fix:

Validate state `position_m` and `speed_kph` as JSON doubles or otherwise as the exact numeric contract requires, explicitly rejecting bool and string values before any `float(...)` comparison. Add producer and reusable-validator mutation tests for string and boolean `position_m`/`speed_kph` on otherwise valid records.

## Fix2 closure checks

- Original Critical, valid-body BOM accepted: ADDRESSED for the required paths I inspected. `_strict_load_json_no_bom` rejects leading UTF-8 BOM before `strict_json_loads`, and the actual CLI paths for `--validate-state-run-binding`, `--produce-vehicle-capture`, and `--validate-vehicle-capture` use it.
- Original Important, huge capture integers accepted: ADDRESSED for capture request, evidence validator, topology stock identities, raw sample IDs, state vehicle/link/lane IDs, counts, and timer endpoints. Positive signed 32-bit and 64-bit bounds are present at `scripts/build_state_manifest_v2_1.py:123-124` and applied on producer and validator paths.
- Original Important, missing concurrent create-once coverage: ADDRESSED. `scripts/tests/test_b1a_vehicle_capture_evidence.py:261` runs simultaneous workers through the real `publish_vehicle_capture_evidence_create_once` path and checks exactly one immutable winner.
- Prior topology, timeout, pre-rename validation, and legacy-provenance fixes remain closed from this rereview. VBS startup, state validation, and sidecar producer use bounded `RunCapture3Timeout`; `WriteStateJson` validates temp before `MoveFile` and final after `MoveFile`; legacy provenance remains two-field and required provenance is three-field.
- Duplicate-key, nonfinite-token, and bounded request/sidecar protections are preserved because the no-BOM loader still delegates to `strict_json_loads`, which uses `object_pairs_hook` duplicate rejection and `parse_constant` nonfinite rejection, after `read_bounded_bytes` where a bound is supplied.
- I did not find a path where synthetic/dry evidence becomes live PASS in this slice. Missing live COM, supported-version readback, connector/multilane live sample coverage, combined timing/p95, post-run v2.2, replay, and B1b remain honestly `NOT_EVALUATED`.

## Focused tests rerun

- PASS: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B -m unittest scripts.tests.test_b1a_vehicle_capture_evidence scripts.tests.test_b1a_vbs_verified_capture_static scripts.tests.test_b1a_watchdog_attempt_launch` -> 34/34.
- PASS outside sandbox: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior` -> 3/3, no VISSIM/COM.
- PASS with warning only: `git diff --check -- scripts/build_state_manifest_v2_1.py scripts/run_real_world_stackelberg_controller.vbs scripts/tests/test_b1a_vehicle_capture_evidence.py scripts/tests/test_b1a_vbs_verified_capture_static.py scripts/tests/test_b1a_vbs_capture_helpers_behavior`; warning was the existing VBS LF-to-CRLF notice.

## Verdict

CHANGES_REQUIRED

Critical: 0
Important: 2
Minor: 0
