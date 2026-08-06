# B1a Slice 3B report: VBS run binding and capture sidecar

Status: IMPLEMENTED_PENDING_INDEPENDENT_REREVIEW

## Scope implemented

- Required-mode VBS startup now binds `RW_RUN_ID`, `RW_RUN_MANIFEST_PATH`, `RW_RUN_MANIFEST_SHA256`, `RW_B1A_REQUIRED=1`, `RW_QUALIFICATION_MODE=live_required`, and the resolved Python path before VISSIM/COM work.
- Required startup binding, temp/final state validation, and vehicle-capture sidecar production all use bounded pinned-Python subprocesses, require empty stderr, exact one-line PASS stdout framing, and fail closed on timeout/nonzero/exec failure.
- Required state roots carry exactly `run_provenance.run_id`, canonical workspace-relative `manifest_path`, and lowercase `manifest_sha256`. Legacy mode preserves the original two-field provenance (`run_id`, `manifest_path`) and cannot emit a required PASS sidecar.
- Required `WriteStateJson` now validates immutable allowed capture time before scan, calls the pinned monotonic helper immediately before the called vehicle table scan, writes state to a same-directory unique temp, strict-validates the temp state bytes with the pinned builder, publishes the final by no-clobber `MoveFile`, strict-validates the immutable final bytes, calls the pinned monotonic helper again, and then creates the capture sidecar.
- `vehicle_records` envelope and six-field per-record schema are unchanged; only VBS internal scan output now also retains `Lane` raw text for capture evidence.
- `scripts/build_state_manifest_v2_1.py` now owns the pinned `state_manifest_builder` vehicle-capture-evidence producer/validator role. It builds, strict-reloads, validates, and create-once publishes `<state-stem>.vehicle_capture_v2_1.json`.
- Capture evidence schema is `vehicle-capture-evidence-v2.1` with exact top-level key order, exact nested counts/timer/sample fields, canonical semantic hash, workspace-relative paths, run/time/qualification binding, strict count agreement, strict timer arithmetic, topology-aware sample validation, and create-once publication.
- Deterministic sample selection uses the approved A1/A2 compiler-shaped topology, including canonical decimal-string `link_no`: lowest occupied connector lane, lowest occupied multi-lane road lane, then lowest remaining vehicle IDs, with <=64 samples and 20,000-row bounded input support.

## Fix round 2 scope

- Required state, vehicle-capture request, and vehicle-capture sidecar byte paths now use a no-BOM strict JSON boundary while leaving the shared legacy `strict_load_json` behavior unchanged for non-required callers.
- Capture evidence producer and validator now bound authored/accepted vehicle, link, and lane identifiers to positive signed 32-bit integers; counts to the 20,000-record request limit; and monotonic timer endpoints to positive signed 64-bit integers.
- Added mutation coverage for valid-body BOM on state/request/sidecar paths, huge timer endpoints, huge vehicle/lane identifiers, count overflow, and a real simultaneous create-once publish race with exactly one immutable winner.

## Fix round 3 scope

- Required state reads in capture production, reusable capture validation, and CLI `--validate-state-run-binding` now all use the existing 8 MiB `MAX_STATE_BYTES` bound before schema/run-binding acceptance.
- State vehicle records are validated on the shared producer/validator path for exact six-field shape, positive signed-32-bit vehicle/link/lane IDs, JSON-double-only `position_m` and `speed_kph`, finite/nonnegative speed, bounded negative position tolerance, boolean `stopped == (speed_kph < 1.0)`, and unique vehicle ID. Coercive `float(...)` comparison of state fields was removed.
- Preserved `lane_raw` is independently reparsed with the called VBS lane grammar (horizontal trim, one hyphen, canonical positive signed-32-bit ASCII decimal components) and must equal `parsed_link_no/parsed_lane_no` before topology/sample validation.
- Added producer and reusable-validator mutations for string, bool, integer, nonfinite state numeric fields, stopped mismatch, extra/missing state fields, malformed/non-ASCII `lane_raw`, raw/parsed disagreement, and a real oversized state artifact through the CLI state-run-binding gate.
- The separate watchdog shared-parent race fix is unchanged in this round; its independent rereview is APPROVED with Critical/Important/Minor 0.

## Fix round 4 scope

- `scripts/build_state_manifest_v2_1.py` now has one shared vehicle-records envelope validator used by both `build_vehicle_capture_evidence` and `validate_vehicle_capture_evidence`.
- The shared validator enforces exact vehicle-records field completeness, schema/version/source attributes/stopped threshold, nonnegative bounded count scalars, `unobservable_count == external_source_count == 0`, strict record uniqueness, canonical positive-decimal link-map keys, bounded integer map values, and root `total_vehicles`/`stopped_vehicles` agreement when those root fields are present.
- It rederives `full_network_link_counts` from record `link_no` totals and `full_network_link_stopped_counts` from `speed_kph < 1.0`, requiring the stopped map to include zero-valued keys for every occupied link and no missing/extra keys.
- Added producer and reusable-validator mutation coverage for wrong/missing/extra link-count keys, wrong/missing/extra stopped-count keys, bool/string/negative/oversize map values, noncanonical map keys, scalar count drift, unobservable drift, envelope extra/missing fields, root total drift, and a valid stopped-threshold boundary case.

## Fix round 5 scope

- `scripts/build_state_manifest_v2_1.py` now applies one exact required-state envelope validator to the capture producer, reusable capture validator, and CLI `--validate-state-run-binding` pre-rename binding path.
- The shared validator requires `stopped_threshold_kph`, `paused_at_sim_sec`, `capture_sim_sec_before`, `capture_sim_sec_after`, and root `sim_sec` to be finite JSON doubles, rejecting bool and integer coercion.
- All envelope count scalars now pass through the bounded JSON-integer helper before comparison; `unobservable_count=false` and `external_source_count=false` are rejected rather than accepted as zero.
- Root `total_vehicles` and `stopped_vehicles` are now mandatory bounded JSON integers on required states and must equal totals rederived from the six-field records. Missing, null, bool, string, negative, overflow, or drift fails.
- `build_manifest_artifact` keeps optional and required states distinct by invoking the strict vehicle-records validator only when the state-selection entry has `required_vehicle_records=true`.
- Focused tests now mutate every fix4 repro across producer, reusable validator, and CLI paths, while preserving the valid empty-capture case. The adjacent B1a core fixture was updated to emit required `stopped_vehicles`.

## Explicitly not implemented in this slice

- Projection-only invocation from VBS.
- Combined projection timing receipt.
- Post-run `run-artifact-manifest-v2.2`.
- Live replay `projection-live-replay-v2.2`.
- B1b rollout dynamics.
- Any VISSIM/COM live run.

## Files changed

- `scripts/build_state_manifest_v2_1.py`
- `scripts/run_real_world_stackelberg_controller.vbs`
- `scripts/tests/test_b1a_vehicle_capture_evidence.py`
- `scripts/tests/test_b1a_core_provenance.py`
- `scripts/tests/test_b1a_vbs_verified_capture_static.py`
- `scripts/tests/test_b1a_vbs_capture_helpers_behavior.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/progress.md`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-vbs-run-binding-capture-sidecar-slice-report.md`

## Verification

- `python -B -m unittest scripts.tests.test_b1a_vehicle_capture_evidence`: 17/17 PASS.
- `python -B -m unittest scripts.tests.test_b1a_vbs_verified_capture_static`: 12/12 PASS.
- `python -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior`: 3/3 PASS outside sandbox; no VISSIM/COM started.
- `python -B -m unittest scripts.tests.test_b1a_watchdog_attempt_launch`: 10/10 PASS.
- `python -B -m unittest scripts.tests.test_b1a_vbs_verified_capture_static scripts.tests.test_b1a_watchdog_attempt_launch`: 22/22 PASS.
- `python -B -m unittest scripts.tests.test_b1a_run_manifest_slice`: 36/36 PASS.
- `python -B -m unittest scripts.tests.test_b1a_core_provenance`: 19/19 PASS.
- `python -B -m unittest plant.tests.test_vissim_strict_physical_projection`: 9/9 PASS.
- `python -B -m unittest plant.tests.test_vissim_strict_physical_projection_reference`: 41/41 PASS.
- `python -B -m unittest tests.test_vissim_stackelberg_adapter_fidelity scripts.tests.test_audit_plant_fidelity`: 33/33 PASS.
- `PYTHONPATH=plant python -B -m unittest plant.tests.test_vissim_strict_signal_program plant.tests.test_vissim_strict_compiler`: 11/11 PASS.
- `cscript.exe //nologo scripts\run_real_world_stackelberg_controller.vbs`: full VBS parse OK; expected usage exit before any COM creation. Sandbox run is blocked by Windows Script Host settings access, so this check was rerun outside sandbox.
- `git diff --check`: PASS with line-ending warnings only.

Fix round 3 bounded regressions: 40/40 PASS, counting vehicle-capture 15/15, VBS static + watchdog 22/22, and VBS helper 3/3 outside sandbox after WSH settings denial.

Fix round 4 bounded regressions: 114/114 PASS, counting vehicle-capture 17/17, VBS static + watchdog 39/39, VBS helper 3/3 outside sandbox after WSH settings denial, run-manifest 36/36, and B1a core provenance 19/19. `git diff --check -- scripts\build_state_manifest_v2_1.py scripts\tests\test_b1a_vehicle_capture_evidence.py ...` PASS.

Fix round 5 bounded regressions:
- `python -B -m unittest scripts.tests.test_b1a_vehicle_capture_evidence`: 18/18 PASS.
- `python -B -m unittest scripts.tests.test_b1a_vehicle_capture_evidence scripts.tests.test_b1a_vbs_verified_capture_static scripts.tests.test_b1a_watchdog_attempt_launch`: 40/40 PASS.
- `python -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior`: sandbox FAIL with Windows Script Host settings access denied; outside-sandbox rerun 3/3 PASS, no VISSIM/COM.
- `git diff --check`: PASS on final file state, with line-ending warnings only.
- `python -B -m unittest scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_b1a_core_provenance`: attempted adjacent broad rerun before fixture alignment; it timed out once at 120s, then failed 44/55 PASS-equivalent with 11 B1a core fixture failures caused by the test fixture omitting required root `stopped_vehicles`. The fixture has been aligned, but per user instruction no additional broad suites were run afterward.

Unique focused/adjacent regressions counted once before fix round 3: 186/186 PASS.

## Honest gates

- Live COM required run: NOT_EVALUATED.
- Supported real VISSIM version readback coverage: NOT_EVALUATED.
- Connector/multilane live sample coverage across a qualified run: NOT_EVALUATED.
- Combined projection timing and p95 runtime: NOT_EVALUATED.
- Post-run v2.2/replay live gates: NOT_EVALUATED.
- B1b rollout dynamics and controller action ranking: NOT_EVALUATED.

## Self-review notes

- The VBS layer remains intentionally thin: it validates immutable binding and performs same-directory publication, but schema/hash/path/sample truth is delegated to the pinned Python producer.
- Sidecar publication failure can leave a valid immutable state without a PASS sidecar, matching the slice brief's orphan-state inventory allowance.
- The capture request's authored `elapsed_sec` is ignored by the producer; the final evidence always recomputes `(end_ns-start_ns)/1e9` from integer endpoints to avoid VBScript integer-width loss.
- The original review's report overclaim is corrected: real-path topology compatibility is now covered by a validator-backed fixture whose A1/A2 stocks use string `link_no`.
