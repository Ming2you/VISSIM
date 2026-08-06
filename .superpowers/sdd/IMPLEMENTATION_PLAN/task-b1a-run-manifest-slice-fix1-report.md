# B1a run-manifest slice fix round 1 report

## Status

`DONE_WITH_CONCERNS`.

All three High, all three Medium, and LOW-1 were addressed in code and targeted
adversarial tests. Live VISSIM COM and live combined p95 remain `NOT_EVALUATED`.
The final post-hardening rerun of the preflight regression command was interrupted at
the user's request, so this report does not claim one uninterrupted final-tree pass of
every regression suite.

## Finding dispositions

### HIGH-1: independently replay approval/preflight/topology/source bundle - FIXED

- `validate_run_manifest` now calls the existing `validate_approval_artifact`, which
  reloads and independently validates the exact preflight, A1 lane graph/routes,
  physical topology, topology replay, approval, and five-key approved binding.
- The validated preflight from that replay is the only source for producer and
  configuration equality checks.
- State-manifest production and state projection continue to delegate to the shared
  validator and now bound run-manifest reads.
- The skeletal happy fixture was replaced by an independently valid official fixture.
- Adversarial tests reject a skeletal self-declared PASS bundle, a coherently rehashed
  preflight mutation, and a coherently rehashed skeletal topology mutation.

### HIGH-2: atomic final visibility and strict reload - FIXED

- Publication writes, flushes, and fsyncs a hidden same-directory temporary file, then
  uses a no-clobber hard-link publication step so the final path is never empty or
  partial.
- Created and validate-only paths reload bounded final bytes, require exact canonical
  bytes, and rerun strict manifest validation before success.
- A spawned writer/reader barrier test proves the final path is unavailable while the
  writer is paused before publication and valid after publication.
- A reload mutation test proves success is withheld when strict final revalidation
  fails.

### HIGH-3: official preflight role universe - FIXED

- Shared constants define all 12 producer roles and eight configuration roles with
  normative default paths.
- `build_preflight_manifest.py` exposes CLI overrides for those roles, including the
  optional demand profile; `validate_preflight_artifact` requires the closed B1a role
  subset and independently validates exact bytes and authored paths.
- The provenance fixture now invokes the official preflight CLI and proves
  preflight production -> exact preflight validation -> topology approval ->
  run-manifest creation without hand-authored preflight JSON.
- The real repository remains honestly preflight `FAIL` because the future-slice
  post-run artifact producer and live replay builder do not exist in this slice.

### MEDIUM-1: concurrent creation-result ownership - FIXED

- Normal creation-result ownership belongs only to the process that exclusively
  creates the attempt run directory. A losing normal process cannot overwrite the
  owner's result.
- CLI fallback context allows an owner to deterministically replace stale result
  evidence even when an oversized/unreadable request cannot be parsed.
- A two-process CLI test proves exit codes `[0, 1]` and a final PASS result bound to the
  winning immutable manifest.

### MEDIUM-2: bounded reads, stale result, and MemoryError - FIXED

- Requests are stat-limited before open and read with a `limit + 1` cap.
- Approval, preflight, topology, policy, and run-manifest JSON have explicit limits.
  Size checks now precede both JSON reads and trust-artifact hashing.
- Oversized request and each oversized trust artifact replace seeded stale PASS result
  evidence with deterministic FAIL without changing the immutable manifest.
- The trust-artifact test fails if the oversized path is opened at all.
- `MemoryError` is fail-closed by the CLI and converted to a typed shared-validator
  failure; both paths have targeted tests.

### MEDIUM-3: exact preflight lexical paths - FIXED

- Preflight-authored paths are checked as exact absolute lexical strings before target
  resolution, including exact workspace prefix/case, separator spelling, on-disk
  component case, containment, file type, and reparse rejection.
- Slash, component-case, and mocked reparse-alias mutations are rejected by targeted
  tests.

### LOW-1: adapter controller choice drift - FIXED BY DRIFT TEST

- The adapter remains unedited. A source-AST drift test extracts its `--controller`
  choices and requires exact equality with the run-manifest validator policy.
- The baseline preflight consumer now derives its artifact inventory from the official
  preflight defaults instead of maintaining another stale manual list.

## Changed files

- `plant/src/vissim_strict/physical_projection.py`
- `plant/src/vissim_strict/run_evidence.py`
- `plant/src/vissim_strict/__init__.py`
- `scripts/approve_physical_stock_topology.py`
- `scripts/build_preflight_manifest.py`
- `scripts/build_run_manifest_v2_1.py`
- `scripts/build_state_manifest_v2_1.py`
- `scripts/validate_state_projection_v2_1.py`
- `scripts/validate_baseline_snapshot.py`
- `scripts/tests/test_b1a_core_provenance.py`
- `scripts/tests/test_b1a_run_manifest_slice.py`
- `scripts/tests/test_build_preflight_manifest.py`
- `scripts/tests/test_validate_baseline_snapshot.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-manifest-slice-fix1-report.md`

No VBS, watchdog, adapter controller flow, root `vehicle_records`, post-run artifact
producer, or live replay implementation was edited in this fix round.

## Commands and results

Python executable used below:
`C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

- `& $PY -B -m unittest scripts.tests.test_b1a_run_manifest_slice -q`
  - Final completed run: 29 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_b1a_core_provenance -q`
  - Final completed run: 19 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_build_preflight_manifest scripts.tests.test_validate_baseline_snapshot -q`
  - Completed after fixture/consumer fixes: 31 tests, PASS.
  - A later final-tree rerun after no-open size hardening was interrupted before a
    result and is `NOT_COMPLETED`.
- `& $PY -B -m unittest scripts.tests.test_vissim_lane_graph scripts.tests.test_vissim_lane_graph_real_network -q`
  - Last completed run: 24 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_compile_physical_stock_topology scripts.tests.test_compile_physical_stock_topology_real_network -q`
  - Last completed run: 19 tests, PASS.
- From `plant`, `& $PY -B -m unittest tests.test_vissim_strict_compiler tests.test_vissim_strict_physical_projection tests.test_vissim_strict_signal_program -q`
  - Last completed run: 20 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_b1a_run_manifest_slice.ProducerCliTests.test_oversized_bound_trust_artifacts_fail_without_manifest_clobber -q`
  - Final completed targeted run: 1 test, PASS.
- `& $PY -B -m unittest scripts.tests.test_b1a_run_manifest_slice.RunManifestValidationTests.test_shared_validator_converts_memory_exhaustion_to_typed_failure -q`
  - Final completed targeted run: 1 test, PASS.
- `git diff --check`
  - Completed before the last hardening edit: PASS with pre-existing line-ending
    warnings. Not rerun after the final edit due to the stop request.

Intermediate regression failures exposed incomplete synthetic role fixtures and a
missing `MAX_POLICY_BYTES` import. Both were fixed and their targeted/completed suites
subsequently passed; no known code-level finding remains open.

## Concerns

- The final preflight/A1/A2/compiler matrix was not rerun after the last bounded-hash
  hardening because verification was explicitly stopped. The last completed runs are
  listed above; this is the only delivery concern.
- Checked-in real preflight evidence remains invalid until the excluded future-slice
  post-run and live-replay producers exist and the complete source universe is rebuilt.
- Live VISSIM COM: `NOT_EVALUATED`.
- Live combined capture/serialize/parse/project p95: `NOT_EVALUATED`.

## Fix round 2

### Status and disposition

`DONE` for scoped rereview finding `IMPORTANT-1`.

The exported `src.vissim_strict.run_evidence` validator no longer imports the
top-level `approve_physical_stock_topology` module. It calls the package-local
`src.vissim_strict.approval_replay` client, which executes the exact bound workspace
approval validator in an isolated Python child. The child exposes a validation-only
mode that calls the existing `validate_approval_artifact`; no approval, preflight,
A1, A2, or topology replay logic was copied into the package client.

The worker protocol is exact, canonical ASCII JSON with LF framing, a closed field
set, empty PASS reasons, bounded stdout/stderr, a timeout, no stdin, and strict
path/hash/schema/status revalidation in the package process. Approval, preflight, and
topology paths and hashes are rechecked before the replay result is accepted. The
consumer process neither imports workspace scripts nor mutates `sys.path`.

The new subprocess regression builds a genuine official
preflight -> A1/A2 -> approval -> run-manifest chain, launches from outside the
workspace with only `plant` on `PYTHONPATH`, proves
`find_spec("approve_physical_stock_topology") is None`, validates the manifest through
the exported package API, and proves the consumer `sys.path` remains byte-for-byte
unchanged. Existing skeletal and coherently rehashed preflight/topology rejection tests
also pass through the package-stable replay path.

### Changed files

- `plant/src/vissim_strict/approval_replay.py`
- `plant/src/vissim_strict/run_evidence.py`
- `scripts/approve_physical_stock_topology.py`
- `scripts/tests/test_b1a_run_manifest_slice.py`
- `scripts/tests/test_build_preflight_manifest.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-manifest-slice-fix1-report.md`

The synthetic official-preflight fixture now copies the exact approval/A1/A2 script
dependencies and `plant/src` tree it claims to bind, instead of placeholder bytes.
No VBS, watchdog, adapter, root `vehicle_records`, post-run artifact producer, or live
replay implementation was edited in fix round 2. No commit was created.

### Commands and results

Python executable:
`C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

- `& $PY -B -m unittest scripts.tests.test_b1a_run_manifest_slice.RunManifestValidationTests.test_exported_validator_replays_with_only_plant_on_package_path -q`
  - Before implementation: 1 test, expected FAIL with
    `No module named 'approve_physical_stock_topology'` in the shared validator.
  - Final run: 1 test, PASS.
- `& $PY -B -m unittest scripts.tests.test_b1a_run_manifest_slice.RunManifestValidationTests.test_skeletal_self_declared_pass_bundle_is_rejected scripts.tests.test_b1a_run_manifest_slice.RunManifestValidationTests.test_coherently_rehashed_preflight_summary_still_fails_independent_replay scripts.tests.test_b1a_run_manifest_slice.RunManifestValidationTests.test_coherently_rehashed_skeletal_topology_still_fails_independent_replay -q`
  - 3 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_b1a_run_manifest_slice -q`
  - 30 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_b1a_core_provenance -q`
  - 19 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_build_preflight_manifest scripts.tests.test_validate_baseline_snapshot -q`
  - 31 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_vissim_lane_graph scripts.tests.test_vissim_lane_graph_real_network -q`
  - 24 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_compile_physical_stock_topology scripts.tests.test_compile_physical_stock_topology_real_network -q`
  - 19 tests, PASS.
- From `plant`, `& $PY -B -m unittest tests.test_vissim_strict_compiler tests.test_vissim_strict_physical_projection tests.test_vissim_strict_signal_program -q`
  - 20 tests, PASS.
- `git diff --check`
  - PASS; only pre-existing line-ending and inaccessible global-ignore warnings were
    emitted.

Final required-suite total: **143 tests passed, 0 failed, 0 skipped**.

### Concerns

- The package validator still requires the exact workspace source artifacts bound by
  the run manifest, including the approval validator script. This is the intended
  source trust universe; it no longer requires those scripts to be importable in the
  consumer process.
- Checked-in real preflight evidence remains invalid until the excluded future-slice
  post-run and live-replay producers exist and the complete source universe is rebuilt.
- Live VISSIM COM: `NOT_EVALUATED`.
- Live combined capture/serialize/parse/project p95: `NOT_EVALUATED`.

## Fix round 3

### Status and disposition

`DONE` for scoped rereview finding `IMPORTANT-2`.

The approval replay worker and package parent now share one exact wire serializer:
canonical JSON encoded as strict UTF-8 without a BOM and framed by exactly one LF.
The parent decodes strict UTF-8, rejects a BOM, requires the closed result field set,
and reserializes with the shared serializer to reject non-canonical bytes or framing.
Worker stdout and stderr remain file-backed and are size-checked before reads; either
stream exceeding 65,536 bytes fails closed. The worker also replaces an oversized
validation result with a bounded deterministic FAIL result before writing stdout.

The package-boundary regression constructs a genuine official preflight -> A1/A2 ->
approval -> run-manifest chain under a Korean non-ASCII workspace path, binds the
monotonic-clock source at a non-ASCII path containing a space, and validates it in a
subprocess launched outside that workspace. The consumer receives only `plant` on
`PYTHONPATH`, cannot import the top-level approval script, and does not mutate
`sys.path`. This exercises Unicode absolute approval/preflight/topology result paths
through the exact independent replay path.

### Changed files

- `plant/src/vissim_strict/approval_replay.py`
- `scripts/approve_physical_stock_topology.py`
- `scripts/tests/test_b1a_core_provenance.py`
- `scripts/tests/test_b1a_run_manifest_slice.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-manifest-slice-fix1-report.md`

No VBS, watchdog, adapter, controller flow, post-run replay, or other future-slice
implementation was edited in fix round 3. No commit was created.

### Commands and results

Python executable:
`C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

- `& $PY -B -m unittest scripts.tests.test_b1a_run_manifest_slice.RunManifestValidationTests.test_package_boundary_replay_accepts_non_ascii_workspace_and_bound_path -q`
  - Before implementation: 1 test, expected FAIL because the ASCII worker wire raised
    while serializing Unicode absolute result paths and the parent observed stderr.
  - Final run: 1 test, PASS.
- `& $PY -B -m unittest scripts.tests.test_b1a_run_manifest_slice.ApprovalReplayWireTests scripts.tests.test_b1a_run_manifest_slice.RunManifestValidationTests.test_package_boundary_replay_accepts_non_ascii_workspace_and_bound_path -q`
  - 3 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_b1a_run_manifest_slice -q`
  - 33 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_b1a_core_provenance -q`
  - 19 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_build_preflight_manifest scripts.tests.test_validate_baseline_snapshot -q`
  - 31 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_vissim_lane_graph scripts.tests.test_vissim_lane_graph_real_network -q`
  - 24 tests, PASS.
- `& $PY -B -m unittest scripts.tests.test_compile_physical_stock_topology scripts.tests.test_compile_physical_stock_topology_real_network -q`
  - 19 tests, PASS.
- From `plant`, `& $PY -B -m unittest tests.test_vissim_strict_compiler tests.test_vissim_strict_physical_projection tests.test_vissim_strict_signal_program -q`
  - 20 tests, PASS.
- `git diff --check`
  - PASS; only pre-existing line-ending warnings were emitted.

Final required-suite total: **146 tests passed, 0 failed, 0 skipped**.

### Concerns

- Checked-in real preflight evidence remains invalid until the excluded future-slice
  post-run and live-replay producers exist and the complete source universe is rebuilt.
- Live VISSIM COM: `NOT_EVALUATED`.
- Live combined capture/serialize/parse/project p95: `NOT_EVALUATED`.
