# B1a Slice 3B fix round 1 rereview

Status: CHANGES_REQUIRED

## Findings

### Critical

1. BOM-prefixed valid state/capture JSON is still accepted by the required evidence path.

Evidence:

- `plant/src/vissim_strict/physical_projection.py:338` uses `encoding="utf-8-sig"` / `.decode("utf-8-sig")` in the shared `strict_load_json` helper.
- `scripts/build_state_manifest_v2_1.py:397` and `scripts/build_state_manifest_v2_1.py:493` validate required state and capture evidence through that helper, so the BOM is stripped before schema/run-binding validation.
- Independent repro with a valid state prefixed by `EF BB BF` printed `STATE_BOM_ACCEPTED run-001 4`; the same test after prefixing an already valid sidecar printed `SIDECAR_BOM_ACCEPTED`.
- The added test at `scripts/tests/test_b1a_vehicle_capture_evidence.py:354` writes `BOM + {}`. It fails because the state body is `{}` and lacks required fields, not because BOM is rejected. It does not cover `BOM + otherwise-valid required state`.

Impact:

The brief explicitly requires invalid UTF-8/BOM or malformed state to fail before producing a PASS sidecar, and the challenge specifically called out BOM coverage. A required PASS sidecar can still be built from a BOM-prefixed state, and a BOM-prefixed capture evidence file can still validate. This means the fix did not fully close the initial strict state validation finding.

Required fix:

Use a no-BOM byte loader for required state/capture request/capture evidence validation or add an explicit leading-BOM rejection at the builder boundary. Add tests for `BOM + otherwise-valid state`, `BOM + otherwise-valid request`, and `BOM + otherwise-valid sidecar`.

### Important

1. Huge timer endpoints are accepted when their difference is small.

Evidence:

- `_json_int` in `scripts/build_state_manifest_v2_1.py:193` has no upper bound.
- Independent repro with `capture_timer.start_ns = 10**1000` and `end_ns = start_ns + 100` printed `start_ns ACCEPTED`.
- The current tests cover 20,000 rows and some malformed VBS lane integers, but I found no Python-side huge-integer rejection test for capture timer endpoints or other evidence integer fields.

Impact:

The challenge required huge integer rejection. Evidence with unrealistic unbounded timing endpoints can be published as valid as long as elapsed computation does not overflow. That weakens the timing receipt contract and leaves future validators with arbitrary-size values outside the intended bounded evidence domain.

Required fix:

Define explicit maximums for capture timer endpoints/count/sample integer fields, reject values above them, and add mutation tests for huge positive integers that remain arithmetically well-formed.

2. Concurrent create-once publication is not covered by the no-VISSIM test matrix.

Evidence:

- `publish_vehicle_capture_evidence_create_once` uses `os.link` create-once behavior, which is a good implementation choice.
- However, `rg` found no thread/process/concurrency test in `scripts/tests/test_b1a_vehicle_capture_evidence.py` or the VBS static/helper tests. Existing coverage only calls publish twice serially.
- The fix brief required “concurrent create-once publication” coverage.

Impact:

The implementation may be race-safe, but the required test evidence is absent. This leaves a specified race/no-clobber gate unproven for the exact producer entry point.

Required fix:

Add a no-VISSIM concurrent publish test against the real `publish_vehicle_capture_evidence_create_once` path, asserting exactly one successful sidecar and all losers fail without replacing bytes.

### Minor

1. Adjacent regression evidence is not independently reproducible as a single bounded command in this environment.

Evidence:

- Focused Slice 3B tests reproduced: `scripts.tests.test_b1a_vehicle_capture_evidence`, `scripts.tests.test_b1a_vbs_verified_capture_static`, and `scripts.tests.test_b1a_watchdog_attempt_launch` ran 31/31 PASS.
- VBS helper behavior reproduced 3/3 PASS outside sandbox; inside sandbox it fails with `CScript Error: Loading your settings failed. (Access is denied.)`, matching the report's stated environment constraint.
- Two broader adjacent unittest bundles timed out at 120s/180s while still printing PASS progress, so I cannot independently endorse the report's full 183/183 count from this rereview run.

## Initial finding closure

- Initial Critical, real A1/A2 string `link_no` incompatibility: ADDRESSED. The producer now canonicalizes positive decimal string stock `link_no`; malformed variants are tested; one test disables the mock and exercises a real manifest validation path with compiler-shaped string topology.
- Initial Important, unbounded required Python subprocesses: ADDRESSED for the required startup, state validation, monotonic helper, and sidecar producer paths. They now use `RunCapture3Timeout`, empty stderr, and one-line PASS framing. Legacy/non-required helper probes still use `RunCapture3`, but those are outside this required evidence path.
- Initial Important, state renamed before strict validation: PARTIALLY ADDRESSED. Temp and final validation now happen before/after rename in VBS, but the validator still accepts BOM-prefixed otherwise-valid state bytes, so the strict-byte contract is not closed.
- Initial Minor, report overclaimed topology coverage: ADDRESSED for topology, but the report now overstates BOM/huge/concurrency coverage.
- Main-review legacy provenance compatibility: ADDRESSED. Required mode emits three fields including lowercase manifest hash; legacy mode preserves two-field `run_id`/`manifest_path` and cannot emit a required PASS sidecar.

## Test evidence

- PASS: `python -B -m unittest scripts.tests.test_b1a_vehicle_capture_evidence scripts.tests.test_b1a_vbs_verified_capture_static scripts.tests.test_b1a_watchdog_attempt_launch` -> 31/31.
- PASS outside sandbox: `python -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior` -> 3/3. Sandbox failure was Windows Script Host settings access, not VBS logic.
- PASS: `git diff --check -- <B1a Slice 3B files>` with only the existing VBS LF-to-CRLF warning.
- FAIL by independent repro: BOM-prefixed valid state and BOM-prefixed valid sidecar are accepted.
- FAIL by independent repro: huge positive `capture_timer.start_ns` is accepted when `end_ns - start_ns` is small.
- NOT REPRODUCED: full adjacent 183/183 claim; broader grouped commands timed out before unittest summary.

## Verdict

CHANGES_REQUIRED

Critical: 1
Important: 2
Minor: 1
