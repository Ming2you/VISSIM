# B1a Slice 2 Report: Adapter Projection and Reference

## Status

`DONE_WITH_CONCERNS`

The production adapter now has a `--projection-only` path and required B1a normal
mode consumes an exact bounded `physical-projection-reference-v2.1` before NumSim,
configuration, controller, candidate, or fallback work. This report deliberately does
not claim live COM capture or timing p95; both remain `NOT_EVALUATED`.

## Changed Files

- `plant/src/vissim_strict/physical_projection_reference.py`
  - New shared bounded sidecar/reference validators and reference builder.
  - Reopens raw state, sidecar, immutable run manifest, independently replayed approved
    topology/A1 graph, and recomputes all binding hashes and mass identities.
- `plant/src/vissim_strict/__init__.py`
  - Exports the public reference APIs.
- `evaluation/controllers/vissim_stackelberg_adapter.py`
  - Adds `--projection-only` and `--b1a-required` gates.
  - Keeps action outputs conditionally required only on normal action mode.
  - Carries validated B1a projection provenance into JSON and CSV action outputs.
- `plant/tests/test_vissim_strict_physical_projection_reference.py`
  - New focused reference mutation and adapter-ordering tests.

No VBS, watchdog, timing receipt, post-run manifest, live replay, or B1b dynamics
files were edited by this slice.

## Public APIs and Schemas

New `vissim_strict` exports:

- `build_physical_projection_reference(...)`
- `validate_physical_projection_reference(...)`
- `validate_projection_sidecar(...)`
- `load_validated_approved_topology(...)`
- `ProjectionReferenceValidationError`
- `ValidatedProjectionReference`
- `physical_projection_reference_semantic_payload(...)`
- `physical_projection_reference_semantic_sha256(...)`

`physical-projection-reference-v2.1` uses the exact required top-level key set:
`schema_version/status/reasons/qualification/run_id/sim_sec/run_manifest_sha256/state_path/state_file_sha256/topology_file_sha256/topology_semantic_sha256/projection_sidecar_path/projection_sidecar_file_sha256/projection_sidecar_semantic_sha256/normalized_projection_sha256/record_count/assigned_count/stock_total/global_residual/semantic_sha256`.

Reference, sidecar, and state reads are bounded to 32 KiB, 16 MiB, and 8 MiB
respectively. JSON is strict about duplicate keys and nonfinite values. Stored artifact
paths are resolved as canonical workspace-relative forward-slash files with containment,
case, and reparse checks supplied by the run-evidence package.

## Adapter Ordering

`--projection-only` performs:

1. Canonical bounded state/run-manifest load and immutable run-manifest validation.
2. Executed adapter-source binding check and exact caller/manifest approved-topology
   comparison.
3. Independent approved-topology/A1 validation, state provenance/time validation, and
   strict vehicle-record normalization.
4. Exactly one call to `project_vehicle_records`.
5. Atomic sidecar write and strict sidecar revalidation.
6. Atomic reference write and bounded reference replay validation, then immediate exit.

The reference destination is removed before projection validation so a failed invocation
cannot leave a prior PASS reference usable. Projection-only never reaches `repo_imports`,
NumSim, configuration, controller/forecast construction, candidate/fallback evaluation,
or action writers.

In `--b1a-required` normal mode, the adapter validates the immutable manifest and
executed adapter source, reopens/validates the exact reference chain, verifies the
caller-provided reference SHA-256 and state path, and only then calls `repo_imports`.
It does not invoke `project_vehicle_records` on the normal path. The validated ledger is
carried into the existing traffic-state construction boundary as B1a provenance; B1b
remains the owner of plant transfer dynamics.

## Verification

All commands were run from `C:\tmp\vissim-pstack-controller` using the bundled Python
runtime with `PYTHONDONTWRITEBYTECODE=1`.

| Command | Result |
|---|---:|
| `python -B -m unittest plant.tests.test_vissim_strict_physical_projection_reference` | PASS, 5 tests |
| `python -B -m unittest scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_b1a_core_provenance` | PASS, 52 tests |
| `PYTHONPATH=plant python -B -m unittest plant.tests.test_vissim_strict_compiler plant.tests.test_vissim_strict_signal_program plant.tests.test_vissim_strict_physical_projection` | PASS, 20 tests |
| `python -B -m unittest scripts.tests.test_vissim_lane_graph scripts.tests.test_compile_physical_stock_topology scripts.tests.test_validate_sc12_shared_lane` | PASS, 40 tests; SC12 PASS=6/FAIL=0 and expected NOT_EVALUATED fixture also passed |
| `python -B -m unittest tests.test_vissim_stackelberg_adapter_fidelity` | PASS, 2 tests |
| `python -B -c "compile(...physical_projection_reference...); compile(...vissim_stackelberg_adapter...); print('syntax ok')"` | PASS, syntax ok |

The focused tests include rehashed reference and sidecar mutations, all missing reference
top-level fields, projection-only single-projector behavior with poisoned NumSim import,
and required normal-mode rejection of a mismatched reference hash before NumSim.

One combined regression command was intentionally discarded because this repository's
legacy plant tests import `src.vissim_strict`, which collides in-process with NumSim's
`src` package used by adapter fidelity. The listed isolated commands are the valid
regression runs and all pass.

## Self-Review and Remaining Gates

- The normal required path has no aggregate-only bypass: absent, invalid, non-PASS, or
  SHA-mismatched references exit before fallback/candidate/controller work.
- Sidecar validation reconstructs assignment, stock, view, diagnostic, normalized-hash,
  and one-vehicle/one-stock identities without calling the public projector again.
- S0R/S1/A1/A2 contracts remain owned by their existing validators; SC12 semantics were
  checked through the existing shared-lane suite.
- Live COM capture and p95 timing remain `NOT_EVALUATED`. VBS/watchdog timing integration,
  post-run/live replay artifacts, and B1b stock transfer dynamics are future slices.
- The run manifest must be produced after this adapter source is finalized, because
  required mode intentionally verifies its pinned adapter byte binding.

## Fix Round 1

### Status

`DONE`

All four Critical and all five Important findings in the independent round-1 review
are closed. There are no known in-scope implementation concerns. Live COM and timing
p95 remain `NOT_EVALUATED`; this fix does not manufacture those gates.

### Finding-by-Finding Disposition

1. **Critical: exact JSON type semantics - CLOSED.** The sidecar is compared against
   the shared-kernel reconstruction with recursive type-strict JSON equality, so
   `bool`, integer, and double are never interchangeable. The normalized hash is also
   recomputed directly from the authored assignments and stock counts. Coherently
   rehashed substitutions are covered in assignments, stock counts, views,
   diagnostics, sample dimensions, and residuals.
2. **Critical: stale/new PASS after failure - CLOSED.** Projection-only establishes
   canonical output roles, checks output/output and output/input identity, and removes
   a safe stale reference before missing-argument checks or other fallible work. The
   publisher serializes and bounds-checks first, validates complete temporary sidecar
   and reference bytes, and publishes the final reference last. All exception paths,
   including post-publication console failure, recheck roles before removing the final
   reference.
3. **Critical: mixed read/hash snapshots - CLOSED.** `BoundedJsonSnapshot` reads one
   bounded buffer, hashes that buffer, and strict-parses that same buffer. Reference,
   manifest, state, sidecar, approval, lane graph, and topology hashes are carried from
   those snapshots. Required mode compares the expected reference hash to the exact
   parsed reference snapshot and rejects manifest replacement between its two trust
   gates.
4. **Critical: destructive path aliasing - CLOSED.** Output identity checks use
   canonical resolved spelling plus existing-file identity, catching slash/case,
   symlink/reparse, hardlink, output/output, and output/input aliases. Checks precede
   every final unlink, directory/write preparation, and atomic replacement. Inputs
   include state, run manifest, topology, approval, A1 lane graph, adapter source, and
   all paths resolved from a valid run manifest.
5. **Important: duplicate projector - CLOSED.** The deterministic algorithm is now
   `_project_vehicle_records_kernel`; the sole public `project_vehicle_records` wrapper
   and the validator both use it. The adapter calls the public function exactly once in
   projection-only and zero times in required normal mode.
6. **Important: validated ledger unused - CLOSED.** Required mode creates one
   provenance-bound B1a state-construction input from the validated ledger and its
   assignments, derives local link observation from those assignments, replaces
   untrusted legacy projection/local-observation fields, and passes that object into
   `traffic_state_from_vissim`. The success test poisons both legacy fields and proves
   the validated ledger is the consumed value. No B1b transfer dynamics were added.
7. **Important: incomplete action provenance - CLOSED.** JSON and every CSV row use
   one `physical-projection-action-provenance-v2.1` object with exact fields for
   qualification, `(run_id, sim_sec)`, manifest path/hash, state path/hash, topology
   path/file/semantic hashes, sidecar path/file/semantic hashes, reference
   path/file/semantic hashes, normalized hash, and the four bound aggregates. CSV
   metadata is canonical compact JSON containing `controller_status`, the complete
   provenance object, and optional row-local metadata. Fallback VSL, signal, and ramp
   rows are all covered.
8. **Important: focused matrix missing - CLOSED.** The focused file now has 26 tests
   covering top-level missing/extra/type/range/status/hash mutations; nested coherent
   rehash and mass attacks; state/run/qualification/topology/approval identity;
   malformed/duplicate/nonfinite JSON; pre-open bounds; mixed atomic versions; stale
   PASS; temporary publication; spaces and non-ASCII paths; slash/case/escape/reparse;
   output collisions and hardlinks; poisoned ordering entry points; valid required
   consumption; zero normal reprojection; and exact JSON/CSV fallback provenance.
9. **Important: raw `OverflowError` - CLOSED.** Finite-number checks catch overflow,
   package and adapter trust boundaries include `OverflowError` in typed fail-closed
   handling, and huge-integer reference and projection-only state cases are covered.

The optional Minor was naturally improved: validated artifact/state/sidecar values and
the B1a state-construction input are recursively frozen. Byte snapshots remain frozen
carrier objects whose parsed values are retained for validation compatibility.

### Changed Files

- `plant/src/vissim_strict/physical_projection.py`
  - Added bounded byte snapshots, canonical bytes, recursive freeze/thaw, recursive
    type-strict equality, and the one shared internal projection kernel.
- `plant/src/vissim_strict/physical_projection_reference.py`
  - Reworked the complete sidecar/reference validator around exact snapshots; added
    validated approval/topology snapshots, output-role identity validation, and
    temporary validated sidecar/reference publication with final PASS last.
- `plant/src/vissim_strict/__init__.py`
  - Exports the bounded snapshot, validated topology/reference, path guard, publication,
    and validation APIs from an ordinary package environment.
- `evaluation/controllers/vissim_stackelberg_adapter.py`
  - Reordered projection-only invalidation/publication and required-mode trust gates;
    added the B1a state-construction boundary and exact JSON/CSV action provenance.
- `plant/tests/test_vissim_strict_physical_projection_reference.py`
  - Expanded the focused suite from 5 to 26 tests and added the complete review matrix.
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-adapter-projection-reference-slice-report.md`
  - Appended this fix-round disposition and evidence.

No VBS, watchdog, timing, post-run, live-replay, or B1b dynamics file was edited in this
fix round. Other pre-existing uncommitted worktree changes were left untouched.

### Public APIs and Exact Schemas

New or extended package surface exported through `vissim_strict`:

- `BoundedJsonSnapshot`
- `load_bounded_json_snapshot(path, *, max_bytes)`
- `ValidatedApprovedTopology`
- `ValidatedProjectionReference`
- `load_validated_approved_topology(...)`
- `validate_projection_sidecar(...)`
- `build_physical_projection_reference(...)`
- `validate_physical_projection_reference(..., expected_reference_file_sha256=None)`
- `validate_projection_output_paths(...)`
- `publish_projection_outputs(...)`

`physical-projection-reference-v2.1` retains the exact 20-field schema listed in the
original report. `physical-projection-action-provenance-v2.1` has exactly these 22
fields:

`schema_version/qualification/run_id/sim_sec/run_manifest_path/run_manifest_sha256/state_path/state_file_sha256/topology_path/topology_file_sha256/topology_semantic_sha256/projection_sidecar_path/projection_sidecar_file_sha256/projection_sidecar_semantic_sha256/projection_reference_path/projection_reference_file_sha256/projection_reference_semantic_sha256/normalized_projection_sha256/record_count/assigned_count/stock_total/global_residual`.

Every B1a CSV metadata cell is an unambiguous JSON object with exact keys
`controller_status/physical_projection_provenance`, plus `action_row` only when a row
has ramp-specific metadata. The JSON action contains the identical provenance object at
top level and in action metadata.

### Exact Ordering Self-Review

Projection-only now orders work as follows:

1. Parse arguments; resolve the reference role first.
2. Resolve available input/output roles, reject aliases, and invalidate a safe stale
   reference before required-argument rejection.
3. Bounded snapshot and validate the immutable manifest; verify executed adapter bytes.
4. Bounded snapshot and independently validate approval, A1 graph, and A2 topology;
   reject caller topology disagreement.
5. Bounded snapshot and validate state provenance/time; normalize records.
6. Call public `project_vehicle_records` exactly once.
7. Serialize/bound/validate temporary sidecar bytes, then atomically replace sidecar.
8. Build/serialize/bound the reference, validate the complete temporary reference chain
   against its exact temporary-byte hash, then atomically replace the final reference.
9. Emit success and immediately return. Any exception through that point invalidates the
   reference after a fresh role check.

Required normal mode validates the manifest and executed adapter source, then validates
the exact expected-hash reference chain and caller state identity before mapping,
calibration, `repo_imports`, NumSim configuration/state/forecast, previous action,
controller, candidate, fallback, or action serialization. It then derives model-state
input from the validated ledger and never calls the public projector.

### Verification Evidence

All commands ran from `C:\tmp\vissim-pstack-controller` on branch
`codex/plant-fidelity-v2-1` with the bundled Python runtime. Final test total:
**140 passed, 0 failed**.

| Exact command | Result |
|---|---:|
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest plant.tests.test_vissim_strict_physical_projection_reference` | PASS, 26 tests in 68.215 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_b1a_core_provenance` | PASS, 52 tests in 169.751 s |
| `$env:PYTHONPATH='plant'; & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest plant.tests.test_vissim_strict_compiler plant.tests.test_vissim_strict_signal_program plant.tests.test_vissim_strict_physical_projection` | PASS, 20 tests in 26.423 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest scripts.tests.test_vissim_lane_graph scripts.tests.test_compile_physical_stock_topology scripts.tests.test_validate_sc12_shared_lane` | PASS, 40 tests in 19.891 s; SC12 PASS=6/FAIL=0 and expected NOT_EVALUATED fixture passed |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest tests.test_vissim_stackelberg_adapter_fidelity` | PASS, 2 tests in 0.423 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -c "from pathlib import Path; files=['plant/src/vissim_strict/physical_projection.py','plant/src/vissim_strict/physical_projection_reference.py','plant/src/vissim_strict/__init__.py','evaluation/controllers/vissim_stackelberg_adapter.py','plant/tests/test_vissim_strict_physical_projection_reference.py']; [compile(Path(p).read_bytes(),p,'exec') for p in files]; print('syntax ok:',len(files))"` | PASS, `syntax ok: 5` |
| `$env:PYTHONPATH='plant/src'; & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -c "import vissim_strict; required=['load_bounded_json_snapshot','load_validated_approved_topology','publish_projection_outputs','validate_physical_projection_reference','validate_projection_output_paths']; assert all(hasattr(vissim_strict,x) for x in required); print('ordinary package import ok:',len(required))"` | PASS, `ordinary package import ok: 5` |

The focused suite was run before the regression groups and again after final fail-closed
hardening. Static review confirms one adapter call site for public
`project_vehicle_records`, no validator `_expected_projection`, and no normal-mode
projector call.

### Concerns and Live Gates

- No known in-scope code concern remains.
- Live VISSIM COM execution and timing p95 remain `NOT_EVALUATED` and require the later
  live integration slice/environment.
- VBS/watchdog timing integration, post-run/live replay, and B1b transfer dynamics remain
  intentionally out of scope.
- A production run manifest must be regenerated after the finalized adapter source is
  approved because required mode verifies the pinned adapter byte hash exactly.

## Fix Round 2

### Status

`DONE`

Original Critical 2, Critical 4, and Important 4 from the Fix Round 1 re-review are
closed. The original 26 focused tests remain present and passing; seven focused test
methods add the required parser and path-role cases.

### Finding Dispositions

1. **Original Critical 2: parser failures preserve stale PASS - CLOSED.** The adapter
   now preparses only the five projection path roles and `--projection-only` from the
   raw argument vector before constructing or invoking the full parser. A nonzero
   `argparse` `SystemExit` routes through the same complete output-authorization path
   as successful projection-only execution. When the canonical reference role and its
   complete trust inputs are supplied, invalid `--mode`, invalid `--controller`, an
   unknown option, and a missing option value all invalidate the old PASS reference.
   Help/zero exit and non-projection invocation do not mutate projection evidence.
2. **Original Critical 4: pre-invalidation aliases can delete A1/input roles - CLOSED.**
   Raw CLI role spellings and every repeated/superseded output spelling are reserved
   lexically before exact resolution. The bounded run-manifest snapshot contributes all
   authored manifest roles before strict manifest validation. Its exact hash-bound
   approval snapshot is then loaded from one bounded buffer; the approval-bound
   `source_inputs.lane_graph` path and file hash are extracted, snapshotted with the
   production bound, and added to the immutable role universe. Approval/A1 bytes and
   hashes must remain identical across full approval replay. Canonical path and
   existing-file identities are checked against the complete universe before any final
   reference unlink. If trust is absent or malformed, the parser failure remains
   authoritative and files are left untouched. A separately safe stale reference is
   still invalidated when only the sidecar role is unauthorized; the sidecar itself is
   never touched.
3. **Original Important 4: residual focused matrix - CLOSED.** Seven new methods cover
   invalid mode, invalid controller, unknown option, missing option value, reference
   equal to the approval-bound A1 graph, reference hardlinked to that graph, and three
   malformed-spelling aliases (state case, run-manifest slash spelling, and topology
   case). The focused module now contains 33 tests and retains all original 26.

### Changed Files

- `evaluation/controllers/vissim_stackelberg_adapter.py`
  - Added the bounded projection-role preparse and parser-failure invalidation hook.
  - Rebuilt early output authorization from raw lexical roles, one bounded manifest
    snapshot, one exact approval snapshot, and the approval-bound A1 graph snapshot.
  - Preserved reference-last publication and same-buffer snapshot behavior.
- `plant/tests/test_vissim_strict_physical_projection_reference.py`
  - Added the seven focused methods and nine required parser/A1/malformed-alias
    scenarios while retaining the original 26 tests.
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-adapter-projection-reference-slice-report.md`
  - Appended this Fix Round 2 disposition and verification evidence.

No VBS, watchdog, timing, post-run, live-replay, or B1b file was edited in Fix Round 2.
Pre-existing uncommitted worktree changes were left untouched, and no commit was made.

### Ordering and Fail-Closed Self-Review

1. Raw projection roles are collected before `parse_args()` can reject an unrelated
   choice, unknown option, or missing value.
2. Both parser-error invalidation and ordinary projection-only setup invoke
   `_prepare_projection_output_roles`; there is no reduced parser-error unlink path.
3. Direct authored role spellings are reserved before any fallible exact resolver can
   discard them. The manifest, exact approval, and approval-bound A1 graph are read as
   bounded single-buffer snapshots and replayed before final output mutation.
4. Combined output/output and output/immutable identity validation runs against that
   complete universe. The reference receives an independent complete immutable-role
   check immediately before unlink, so a protected reference can never be removed.
5. Projection-only still calls public `project_vehicle_records` exactly once. Required
   normal mode still calls it zero times and consumes only the validated ledger-derived
   state-construction input before any runtime/controller path.
6. The publisher remains unchanged: complete temporary bytes are bounded and validated,
   sidecar is published first, and the final PASS reference is published last. Every
   downstream failure revalidates identities before removing the reference.

### Verification Evidence

All commands ran from `C:\tmp\vissim-pstack-controller` on branch
`codex/plant-fidelity-v2-1` with the bundled Python runtime. Final non-overlapping suite
total: **147 passed, 0 failed**.

Developmental red/green evidence:

- The seven new focused methods initially reproduced the review: `Ran 7 tests in
  16.040s`, `FAILED (failures=5, errors=4)`.
- After the primary fix, the same seven methods passed in `21.193s`.
- The first complete 33-test focused run exposed the retained sidecar/stale-reference
  ordering expectation: `FAILED (failures=1)` in `95.410s`.
- The isolated retained case passed in `1.302s`, followed by the final clean 33-test
  run below.

| Exact command | Result |
|---|---:|
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest plant.tests.test_vissim_strict_physical_projection_reference` | PASS, 33 tests in 96.779 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_b1a_core_provenance` | PASS, 52 tests in 166.408 s |
| `$env:PYTHONPATH='plant'; & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest plant.tests.test_vissim_strict_compiler plant.tests.test_vissim_strict_signal_program plant.tests.test_vissim_strict_physical_projection` | PASS, 20 tests in 26.914 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest scripts.tests.test_vissim_lane_graph scripts.tests.test_compile_physical_stock_topology scripts.tests.test_validate_sc12_shared_lane` | PASS, 40 tests in 20.522 s; SC12 PASS=6/FAIL=0 and expected NOT_EVALUATED fixture passed |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest tests.test_vissim_stackelberg_adapter_fidelity` | PASS, 2 tests in 0.468 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -c "from pathlib import Path; files=['plant/src/vissim_strict/physical_projection.py','plant/src/vissim_strict/physical_projection_reference.py','plant/src/vissim_strict/__init__.py','evaluation/controllers/vissim_stackelberg_adapter.py','plant/tests/test_vissim_strict_physical_projection_reference.py']; [compile(Path(p).read_bytes(),p,'exec') for p in files]; print('syntax ok:',len(files))"` | PASS, `syntax ok: 5` |
| `$env:PYTHONPATH='plant/src'; & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -c "import vissim_strict; required=['load_bounded_json_snapshot','load_validated_approved_topology','publish_projection_outputs','validate_physical_projection_reference','validate_projection_output_paths']; assert all(hasattr(vissim_strict,x) for x in required); print('ordinary package import ok:',len(required))"` | PASS, `ordinary package import ok: 5` |
| `git diff --check` | PASS; only pre-existing LF-to-CRLF warnings |

### Concerns and Live Gates

- No known in-scope Critical or Important concern remains.
- The rereview's optional Minor remains deferred: `BoundedJsonSnapshot.value` itself is
  not recursively frozen, although validated artifact/state/sidecar views are frozen.
- Live VISSIM COM execution and timing p95 remain `NOT_EVALUATED`; VBS/watchdog timing,
  post-run/live replay, and B1b transfer dynamics remain future slices.
- A production run manifest must be regenerated after the finalized adapter source is
  approved because required mode verifies its pinned adapter byte hash exactly.

## Fix Round 3

### Status

`DONE`

Original Critical 2, Critical 4, Important 4, and the new abbreviated-state Critical
regression from the Fix Round 2 re-review are closed. No CLI alias was added.

### Finding Dispositions

1. **Original Critical 2: parser/preparse option-language mismatch - CLOSED.** The sole
   adapter `ArgumentParser` now uses `allow_abbrev=False`; no auxiliary parser exists.
   The raw preparse recognizes only the same exact projection-role option names, in
   split-value and exact `--option=value` forms, and recognizes `--projection-only`
   only as an exact flag. Unique long-option prefixes are therefore rejected by the
   full parser instead of entering projection mode. Exact invalid choice, unknown
   option, and missing-value failures continue through the established safe
   invalidation hook.
2. **Original Critical 4: incomplete pre-mutation role universe - CLOSED.** Every exact
   raw state/manifest/topology occurrence is reserved as immutable, every superseded
   raw output occurrence is reserved, and the successfully parsed effective
   state/manifest/topology paths are independently added before authorization. The
   effective sidecar/reference paths are the only mutation candidates and must equal
   the last exact raw declarations. Any parser/preparse mismatch raises before unlink.
   Values attached to rejected strict prefixes of protected role options are retained
   as untrusted immutable identities, without treating those prefixes as aliases.
3. **Original Important 4: abbreviation matrix missing - CLOSED.** Five new focused
   methods cover rejected prefixes for projection-only, output-reference, state-json,
   run-manifest, and approved-topology. The first two prove a valid PASS reference is
   unchanged; the three input cases make the source path the requested reference
   destination and prove byte-for-byte source preservation. The focused module now
   contains 38 tests and retains all previous 33.
4. **New Critical: abbreviated state can be unlinked - CLOSED.** `--state-j=...` is no
   longer parser-accepted. During its parser-error path the authored value is still
   reserved as an untrusted role identity, so an exact reference destination naming
   the same file fails identity authorization and cannot unlink the state capture.
   Independently, any successfully parsed effective state is always immutable, which
   keeps the mutation guard fail-closed if parser/preparse behavior ever diverges.

### Changed Files

- `evaluation/controllers/vissim_stackelberg_adapter.py`
  - Disabled long-option abbreviation on the sole full parser.
  - Aligned raw projection-role recognition to exact parser spellings.
  - Reserved rejected protected-prefix values and all parsed effective input roles;
    added a parser/preparse equality gate before output mutation.
- `plant/tests/test_vissim_strict_physical_projection_reference.py`
  - Added five prefix rejection tests with stale-reference and source-preservation
    assertions, growing the focused matrix from 33 to 38 tests.
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-adapter-projection-reference-slice-report.md`
  - Appended this Fix Round 3 disposition and evidence.

No VBS, watchdog, timing, post-run, live-replay, or B1b file was edited in Fix Round 3.
Pre-existing uncommitted worktree changes were preserved, and no commit was made.

### Ordering and Fail-Closed Self-Review

1. Raw arguments are scanned before full parse. Exact role declarations and values
   attached to rejected protected prefixes are retained separately; rejected prefixes
   never set effective projection mode or effective output roles.
2. Full parsing rejects every abbreviated long option. On successful projection parse,
   all effective input roles are reserved and all effective projection roles must match
   the exact raw preparse before any bounded trust replay or mutation.
3. On parser failure, only an exact raw `--projection-only` plus exact raw reference role
   can request invalidation. The same complete manifest/approval/A1 authorization and
   path/file identity checks run, including rejected-prefix identities, before unlink.
4. Exact unknown-option, invalid-choice, and missing-value behavior is unchanged: a
   safely authorized canonical stale reference is invalidated. Rejected projection or
   reference prefixes do not identify an accepted mutation target and leave prior
   evidence untouched.
5. The same-buffer snapshots, complete temporary-byte validation, sidecar-first/final-
   PASS-last publication, required-mode ordering, one projection-only projector call,
   and zero required-normal projector calls are unchanged.

### Verification Evidence

All commands ran from `C:\tmp\vissim-pstack-controller` on branch
`codex/plant-fidelity-v2-1` with the bundled Python runtime. Final non-overlapping suite
total: **152 passed, 0 failed**.

Developmental red/green evidence:

- Before the implementation change, the five new prefix methods reproduced the review:
  `Ran 5 tests in 13.653s`, `FAILED (failures=5)`.
- After the implementation change, the same five methods passed in `8.804s`.

| Exact command | Result |
|---|---:|
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest plant.tests.test_vissim_strict_physical_projection_reference` | PASS, 38 tests in 101.348 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_b1a_core_provenance` | PASS, 52 tests in 161.365 s |
| `$env:PYTHONPATH='plant'; & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest plant.tests.test_vissim_strict_compiler plant.tests.test_vissim_strict_signal_program plant.tests.test_vissim_strict_physical_projection` | PASS, 20 tests in 26.850 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest scripts.tests.test_vissim_lane_graph scripts.tests.test_compile_physical_stock_topology scripts.tests.test_validate_sc12_shared_lane` | PASS, 40 tests in 20.652 s; SC12 PASS=6/FAIL=0 and expected NOT_EVALUATED fixture passed |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest tests.test_vissim_stackelberg_adapter_fidelity` | PASS, 2 tests in 0.451 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -c "from pathlib import Path; files=['plant/src/vissim_strict/physical_projection.py','plant/src/vissim_strict/physical_projection_reference.py','plant/src/vissim_strict/__init__.py','evaluation/controllers/vissim_stackelberg_adapter.py','plant/tests/test_vissim_strict_physical_projection_reference.py']; [compile(Path(p).read_bytes(),p,'exec') for p in files]; print('syntax ok:',len(files))"` | PASS, `syntax ok: 5` |
| `$env:PYTHONPATH='plant/src'; & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -c "import vissim_strict; required=['load_bounded_json_snapshot','load_validated_approved_topology','publish_projection_outputs','validate_physical_projection_reference','validate_projection_output_paths']; assert all(hasattr(vissim_strict,x) for x in required); print('ordinary package import ok:',len(required))"` | PASS, `ordinary package import ok: 5` |
| `Select-String` static parser/test/projector audit | PASS: one adapter parser with `allow_abbrev=False`, 38 focused methods, one production projector call site |
| `git diff --check` | PASS; only pre-existing LF-to-CRLF warnings |

### Concerns and Live Gates

- No known in-scope Critical or Important concern remains.
- The snapshot-value recursive-immutability Minor remains deferred as directed.
- Live VISSIM COM execution and timing p95 remain `NOT_EVALUATED`; VBS/watchdog timing,
  post-run/live replay, and B1b transfer dynamics remain future slices.
- A production run manifest must be regenerated after the finalized adapter source is
  approved because required mode verifies its pinned adapter byte hash exactly.

## Fix Round 4

### Status

`DONE`

The residual split-value parser/preparse mismatch from the Fix Round 3 re-review is
closed. The raw projection-role scan now delegates split-token classification to the
sole fully configured `ArgumentParser`, so the preparse and `parse_args()` use the same
option table, `allow_abbrev=False` setting, prefix handling, and negative-number rules.

### Finding Disposition

1. **Residual Critical: parser-rejected single-dash value could be unlinked - CLOSED.**
   The adapter constructs its one full parser before preparsing, then
   `_parser_accepts_split_value` uses that parser's `_parse_optional` result to decide
   whether a required split value would be consumed. Unknown single-dash tokens such
   as `-victim.json` are option-like and are no longer recorded as an effective output
   path. Parser-accepted negative-number tokens such as `-1` remain values. The same
   classifier governs split values following rejected protected prefixes. Exact
   `--option=value` handling is unchanged, including a leading-dash inline value.
2. **Existing language and identity guarantees - RETAINED.** The sole parser still has
   `allow_abbrev=False`; exact invalid-choice, unknown-option, and missing-value errors
   with independently valid exact projection roles still invalidate stale references.
   The complete output/input/manifest/approval/A1 identity authorization path is
   unchanged. Existing canonical Windows absolute, non-ASCII, space, slash/case,
   reparse, escape, hardlink, repeated-role, and source-preservation coverage remains
   in the focused and core suites.

### Changed Files

- `evaluation/controllers/vissim_stackelberg_adapter.py`
  - Builds the sole full parser before projection preparse and passes that parser into
    the scanner.
  - Uses the parser's own optional-token classifier for both exact split roles and
    rejected-prefix split capture.
- `plant/tests/test_vissim_strict_physical_projection_reference.py`
  - Adds a stale `-victim.json` split-value regression proving parser rejection cannot
    unlink it.
  - Adds exact-inline/rejected-prefix and parser-accepted `-1` cases, growing the
    focused module from 38 to 41 tests.
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-adapter-projection-reference-slice-report.md`
  - Appends this Fix Round 4 disposition and verification evidence.

No future-slice, VBS, watchdog, timing, post-run, live-replay, or B1b file was edited.
Pre-existing worktree changes were preserved, and no commit was made.

### Red/Green Evidence

- Before the implementation change, the minimal stale single-dash regression ran
  `1 test in 1.465s` and failed because `-victim.json` had been removed.
- After the implementation change, that same isolated test passed in `0.656s`.
- The three new parser-equivalence tests passed together: `3 tests in 3.254s`.

### Verification Evidence

All commands ran from `C:\tmp\vissim-pstack-controller` with the bundled Python
runtime and `-B`. Final non-overlapping suite total: **155 passed, 0 failed**.

| Exact command | Result |
|---|---:|
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest plant.tests.test_vissim_strict_physical_projection_reference` | PASS, 41 tests in 111.341 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest scripts.tests.test_b1a_run_manifest_slice scripts.tests.test_b1a_core_provenance` | PASS, 52 tests in 167.402 s |
| `$env:PYTHONPATH='plant'; & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest plant.tests.test_vissim_strict_compiler plant.tests.test_vissim_strict_signal_program plant.tests.test_vissim_strict_physical_projection` | PASS, 20 tests in 25.960 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest scripts.tests.test_vissim_lane_graph scripts.tests.test_compile_physical_stock_topology scripts.tests.test_validate_sc12_shared_lane` | PASS, 40 tests in 19.634 s; SC12 PASS=6/FAIL=0 and expected NOT_EVALUATED fixture passed |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest tests.test_vissim_stackelberg_adapter_fidelity` | PASS, 2 tests in 0.432 s |
| `& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -c "from pathlib import Path; files=['plant/src/vissim_strict/physical_projection.py','plant/src/vissim_strict/physical_projection_reference.py','plant/src/vissim_strict/__init__.py','evaluation/controllers/vissim_stackelberg_adapter.py','plant/tests/test_vissim_strict_physical_projection_reference.py']; [compile(Path(p).read_bytes(),p,'exec') for p in files]; print('syntax ok:',len(files))"` | PASS, `syntax ok: 5` |
| `$env:PYTHONPATH='plant/src'; & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -c "import vissim_strict; required=['load_bounded_json_snapshot','load_validated_approved_topology','publish_projection_outputs','validate_physical_projection_reference','validate_projection_output_paths']; assert all(hasattr(vissim_strict,x) for x in required); print('ordinary package import ok:',len(required))"` | PASS, `ordinary package import ok: 5` |
| `Select-String` static parser/test/projector audit | PASS: one adapter parser with `allow_abbrev=False`, 41 focused methods, one production projector call site |
| `git diff --check` | PASS; only pre-existing LF-to-CRLF warnings |

### Concerns and Live Gates

- No known in-scope Critical or Important concern remains.
- The snapshot-value recursive-immutability Minor remains deferred as directed.
- Live VISSIM COM execution and timing p95 remain `NOT_EVALUATED`; VBS/watchdog timing,
  post-run/live replay, and B1b transfer dynamics remain future slices.
- A production run manifest must be regenerated after the finalized adapter source is
  approved because required mode verifies its pinned adapter byte hash exactly.
