# B1a Slice 3B fix round 5 independent rereview

Status: CHANGES_REQUIRED

## Findings

### Important

1. Adjacent state-manifest/projection inventory path is broken after making required vehicle-record validation strict.

Evidence:

- Fix5 correctly routes the producer, reusable capture validator, and CLI `--validate-state-run-binding` through the same required-state validator: `scripts/build_state_manifest_v2_1.py:626-639`, `scripts/build_state_manifest_v2_1.py:734-742`, and `scripts/build_state_manifest_v2_1.py:1285-1295`.
- The same validator is now also invoked while building the state manifest when a selection entry has `required_vehicle_records=true`: `scripts/build_state_manifest_v2_1.py:1109-1118`.
- That changed the adjacent contract tested by `scripts/tests/test_b1a_core_provenance.py`: malformed/missing required `vehicle_records` now makes `build_manifest()` return `1` before projection validation can inventory the selected state and replace stale projection/audit sidecars with FAIL evidence.
- Independent rerun of `scripts.tests.test_b1a_core_provenance` failed 5/19:
  - `test_required_and_optional_missing_envelope_remain_distinct`
  - `test_huge_state_integer_replaces_stale_audit_and_sidecar_with_fail`
  - `test_malformed_selection_and_state_record_matrix_replaces_stale_outputs` for `state/int`
  - `test_malformed_selection_and_state_record_matrix_replaces_stale_outputs` for `state/list`
  - `test_malformed_selection_and_state_record_matrix_replaces_stale_outputs` for `state/str`
- This directly contradicts the fix5 report claim that optional and required state-manifest paths remain distinct and aligned.

Impact:

The Slice 3B capture sidecar path is now stricter, but the broader B1a state-manifest/projection replay path no longer preserves the intended FAIL-inventory behavior for bad required states. A stale projection/audit artifact can remain outside the downstream validator flow because manifest construction stops earlier than the adjacent tests expect. This is load-bearing for Slice 3C/post-run replay, so I cannot approve Slice 3B as complete.

Required fix:

Restore the adjacent contract deliberately. Either keep state-manifest construction as an inventory operation that records the selected state and lets `validate_state_projection_v2_1.py` emit the FAIL sidecars, or update the state-manifest contract and tests so stale projection/audit cleanup still happens in a bounded, explicit path. Re-run `scripts.tests.test_b1a_core_provenance` after the fix.

## Prior issue closure

- Initial Critical, approved A1/A2 string `link_no` topology incompatibility: CLOSED. Current tests use compiler-shaped string `link_no`, and the producer accepts canonical positive decimal stock IDs while rejecting malformed variants.
- Initial Important, unbounded required startup/sidecar subprocesses: CLOSED by inspection. Required run binding, state binding, monotonic helper, and capture producer use `RunCapture3Timeout`.
- Initial Important, state renamed before strict validation: CLOSED by inspection. Required `WriteStateJson` validates the temp state before no-clobber `MoveFile`, then validates the immutable final before sidecar publication.
- Fix1 Critical, valid-body BOM accepted: CLOSED. Required state/request/sidecar paths use `_strict_load_json_no_bom` with bounded reads where required.
- Fix1 Important, huge integer acceptance: CLOSED for capture counts, timer endpoints, state/sample IDs, lane IDs, and topology IDs.
- Fix1 Important, concurrent create-once coverage: CLOSED. The focused test suite covers simultaneous publication through the real create-once path.
- Fix2 Important, unbounded required state reads: CLOSED. Producer, reusable validator, and CLI state-run-binding loads use `MAX_STATE_BYTES`.
- Fix2 Important, state record bool/string coercion: CLOSED for record IDs, doubles, and stopped derivation.
- Fix3 Important, link/stopped maps not rederived: CLOSED. The shared validator rederives link maps and root totals from records.
- Fix4 Important, envelope bool/int/root presence looseness: CLOSED for the focused capture/CLI paths. Bool/int coercion and missing root totals are rejected in producer, reusable validator, and CLI mutation coverage.
- Exact JSON-double concern: CLOSED by inspection. VBS `JsonDoubleInvariant` appends a decimal point and significant trailing digits for integral-valued doubles, so values such as `60` are emitted as JSON doubles that Python parses as `float`.
- Synthetic/dry live PASS: no path found in this Slice 3B scope. Legacy mode remains unable to emit required PASS capture evidence.
- Live VISSIM/COM, real VISSIM version coverage, connector/multilane live sample coverage, combined timing/p95, post-run v2.2, replay, and B1b remain `NOT_EVALUATED`.

## Test evidence

- PASS: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B -m unittest scripts.tests.test_b1a_vehicle_capture_evidence scripts.tests.test_b1a_vbs_verified_capture_static scripts.tests.test_b1a_watchdog_attempt_launch` -> 40/40.
- PASS: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B -m unittest scripts.tests.test_b1a_run_manifest_slice` -> 36/36.
- FAIL: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B -m unittest scripts.tests.test_b1a_core_provenance` -> 14/19 pass, 5 failures listed above.
- TIMEOUT/INCONCLUSIVE: grouped adjacent command `scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_b1a_core_provenance` timed out at 180s after showing failure markers; split reruns above are the reliable evidence.
- FAIL in sandbox only: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior` -> 0/3 because Windows Script Host settings access was denied before helper logic ran.
- FAIL in sandbox only: `cscript.exe //nologo scripts\run_real_world_stackelberg_controller.vbs` -> Windows Script Host settings access denied before parse/usage output.
- NOT_RERUN outside sandbox: VBS helper and cscript parse/usage checks could not be escalated because the approval system reported a usage-limit block.
- PASS: `git diff --check -- scripts\build_state_manifest_v2_1.py scripts\run_real_world_stackelberg_controller.vbs scripts\tests\test_b1a_vehicle_capture_evidence.py scripts\tests\test_b1a_core_provenance.py scripts\tests\test_b1a_vbs_verified_capture_static.py scripts\tests\test_b1a_vbs_capture_helpers_behavior.py scripts\tests\test_b1a_watchdog_attempt_launch.py scripts\run_real_world_single_watchdog_distributed_core15n41.ps1` with LF-to-CRLF warnings only for the VBS/PS1 files.
- No VISSIM/COM was started.

## Verdict

CHANGES_REQUIRED

Critical: 0
Important: 1
Minor: 0
