# B1a run-manifest slice 1 report

## Result

Implemented immutable per-attempt identity, exact `run-manifest-v2.1` validation,
create-once publication, deterministic creation-result evidence, supported-version
policy parsing, and the Windows cross-process monotonic-clock helper. Live VISSIM COM
and live p95 remain `NOT_EVALUATED`.

## Changed files

- `plant/src/vissim_strict/run_evidence.py`
- `plant/src/vissim_strict/__init__.py`
- `plant/policies/supported_vissim_versions_v2_1.json`
- `scripts/build_run_manifest_v2_1.py`
- `scripts/read_monotonic_clock.py`
- `scripts/build_state_manifest_v2_1.py`
- `scripts/validate_state_projection_v2_1.py`
- `scripts/tests/test_b1a_run_manifest_slice.py`
- `scripts/tests/test_b1a_core_provenance.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-manifest-slice-report.md`

No VBS, watchdog, adapter, vehicle-record root, post-run artifact producer, or live
replay behavior was changed by this slice.

## Exact schemas

`run-manifest-v2.1` top-level fields are exactly:

`schema_version/run_id/campaign_id/attempt/qualification/approved_topology/preflight/producer_sources/configuration/allowed_capture_times/supported_version_policy/semantic_sha256`.

- `qualification`: `mode`.
- `approved_topology`:
  `approving_manifest_path/approving_manifest_sha256/topology_path/topology_file_sha256/topology_semantic_sha256`.
- `preflight`: `schema_version/path/file_sha256/fingerprint_sha256`.
- Every producer source: `path/file_sha256`; the role set is the closed 12-role set in
  the governing brief.
- `configuration`: `inputs/simulation`; inputs use the closed eight-role set and exact
  `path/file_sha256` records, with paired nulls allowed only for `demand_profile`.
- `simulation` uses the exact 15 fields in the brief with JSON integer, finite-number,
  enum, range, and duplicate demand-profile checks.
- `supported_version_policy`:
  `schema_version/path/file_sha256/semantic_sha256`.

`run-manifest-request-v2.1` fields are exactly:

`schema_version/workspace_root/run_directory/run_id/campaign_id/attempt/qualification/topology_approval/preflight/producer_sources/configuration/allowed_capture_times/output_manifest/creation_result_output/validate_only/semantic_sha256`.

`run-manifest-creation-result-v2.1` fields are exactly:

`schema_version/status/reasons/outcome/run_id/campaign_id/attempt/qualification/run_manifest/semantic_sha256`, where `run_manifest` is exactly
`path/file_sha256/semantic_sha256`.

`supported-vissim-versions-v2.1` fields are exactly:

`schema_version/canonical_json_version/accepted_leading_majors/normalized_major/semantic_sha256`.
The policy accepts leading majors `20` and `2020`, normalizing both to integer `2020`.

The monotonic helper success frame is exactly one ASCII byte line:
`python_perf_counter_ns=<positive decimal integer>\n`.

All semantic hashes use the existing shared canonical JSON v1 helper. File hashes,
strict JSON loading, canonical contained-path handling, A2 approval replay, preflight
validation, physical topology validation, and the five-key approved binding reuse the
existing helpers.

## Publication behavior

- Normal mode exclusively creates an absent manifest and never replaces it.
- Explicit validate-only mode accepts only canonical byte-identical existing bytes and
  does not change mtime.
- A differing or concurrently won destination returns a typed failure without clobber.
- Creation-result evidence is a separate deterministic atomic replacement; stale PASS
  content is replaced on every parseable invocation with a usable result path.
- Run directories and all bound files are canonical non-reparse descendants of the
  workspace with exact on-disk case and forward-slash spelling.

## Commands and results

- `python -B -m unittest scripts.tests.test_b1a_run_manifest_slice -q`
  - 17 tests, PASS.
- `python -B -m unittest scripts.tests.test_b1a_core_provenance -q`
  - 19 tests, PASS.
- `python -B -m unittest scripts.tests.test_build_preflight_manifest scripts.tests.test_validate_baseline_snapshot -q`
  - 31 tests, PASS.
- `python -B -m unittest scripts.tests.test_vissim_lane_graph scripts.tests.test_vissim_lane_graph_real_network -q`
  - 24 tests, PASS.
- `python -B -m unittest scripts.tests.test_compile_physical_stock_topology scripts.tests.test_compile_physical_stock_topology_real_network -q`
  - 19 tests, PASS.
- From `plant`: `python -B -m unittest tests.test_vissim_strict_compiler tests.test_vissim_strict_physical_projection tests.test_vissim_strict_signal_program -q`
  - 20 tests, PASS.
- `git diff --check`
  - PASS; only existing line-ending warnings were reported.

Total: 130 tests passed, 0 failed, 0 skipped.

## Source and preflight compatibility

The producer invokes the existing independent `topology-approval-v2.1` replay and exact
PASS `preflight-v3` validator, then requires every producer and present configuration
role to equal the corresponding preflight artifact path and raw-byte hash. The adapter
and supported-policy duplicate bindings are additional equality constraints.

The checked-in real PASS artifacts were not regenerated. The current checked-in
preflight output predates this slice's complete closed producer-role universe and the
new producer/policy bytes, so it remains honestly invalid for a live-required run until
the complete current source universe can be rebuilt through the approved preflight
flow.

## Self-review

- Rechecked normal-create versus explicit validate-only semantics; only validate-only
  can reuse existing immutable bytes.
- Verified manifest and creation-result destinations cannot escape the workspace or
  traverse reparse components.
- Verified missing/extra fields, type/range/enum mutations, path spelling, duplicate
  bindings, policy tamper, malformed/large request values, stale-result replacement,
  mtime preservation, and the concurrent create race.
- Verified both existing state-manifest consumers delegate to the one shared strict
  validator; no permissive local run-manifest checker remains.
- Confirmed root `vehicle_records` and excluded runtime surfaces were not edited.

## Live gates

- Supported VISSIM COM capture: `NOT_EVALUATED`.
- Live combined capture/serialize/parse/project p95: `NOT_EVALUATED`.
