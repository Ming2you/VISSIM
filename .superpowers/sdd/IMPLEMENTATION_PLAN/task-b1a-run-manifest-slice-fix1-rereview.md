# B1a run-manifest slice fix round 1 re-review

## Scope and verdict

Reviewed the two governing briefs, the original seven findings, the fix-round-1
report, and `review-b1a-run-manifest-slice-fix1-current.diff`. This review is limited
to those seven findings and new Critical/Important defects introduced by their fix
delta. VBS, watchdog launch integration, adapter projection, post-run artifacts, and
live replay remain outside scope.

- Original findings: **7 ADDRESSED, 0 NOT_ADDRESSED**.
- New defects: **0 Critical, 1 Important**.
- Overall requirements verdict: **CHANGES_REQUIRED** because the new Important defect
  breaks the controller-independent public validator contract.
- Live VISSIM COM: **NOT_EVALUATED**.
- Live combined p95: **NOT_EVALUATED**.

## Original finding dispositions

### HIGH-1: ADDRESSED

The shared validator now calls the independent approval replay at
`plant/src/vissim_strict/run_evidence.py:728-756`, compares the replayed five-key
approved-topology binding at lines 741-751, and uses only `bundle.preflight` for all
producer/configuration equality checks at lines 752-767. The called implementation
bounded-loads and validates preflight, A1 graph/routes, physical topology, and topology
recompilation in `scripts/approve_physical_stock_topology.py:626-762`; approval shape,
semantic hash, source bindings, supplied topology, and replay result are enforced at
lines 822-925.

The previous skeletal fixture is now a rejection fixture
(`scripts/tests/test_b1a_run_manifest_slice.py:121-275`, rejection at lines 341-348),
while the happy fixture is built from the independently valid official provenance
chain at lines 278-302. Coherently rehashed preflight and skeletal-topology mutations
are rejected at lines 350-407. Existing state consumers still delegate to the shared
validator at `scripts/build_state_manifest_v2_1.py:403-409` and
`scripts/validate_state_projection_v2_1.py:438-444`.

### HIGH-2: ADDRESSED

Normal creation now writes and fsyncs a hidden same-directory temporary file, then
publishes the complete inode with a no-clobber hard link
(`plant/src/vissim_strict/run_evidence.py:843-860`). The final bytes are bounded,
compared byte-for-byte, strict-loaded, and revalidated before success at lines 861-885.
Validate-only similarly performs bounded exact-byte comparison and strict revalidation
without rewriting at lines 825-841.

The process barrier test proves the final pathname is absent before publication and
valid afterward (`scripts/tests/test_b1a_run_manifest_slice.py:632-672`). The strict
reload mutation test at lines 674-702 proves publication does not report success when
final revalidation fails. The original same-target writer exclusion and differing
no-clobber checks remain at lines 604-630.

### HIGH-3: ADDRESSED

The shared normative maps now define all 12 producer roles and all eight configuration
roles with default paths at `plant/src/vissim_strict/run_evidence.py:75-121`.
`scripts/build_preflight_manifest.py:58-80` incorporates those maps into the official
artifact universe; its builder materializes every configured role at lines 629-658,
and its CLI exposes exact per-role overrides plus optional demand profile at lines
788-810.

The independent preflight validator requires the B1a role subset at
`scripts/approve_physical_stock_topology.py:115-123` and validates each exact authored
path, bytes, size, hash, and check record at lines 313-370. The provenance fixture now
invokes the official preflight CLI rather than hand-authoring JSON
(`scripts/tests/test_b1a_core_provenance.py:302-314`), and the producer test confirms
that output passes exact validation before run-manifest creation
(`scripts/tests/test_b1a_run_manifest_slice.py:838-846`). Missing future-slice default
producer files correctly keep the real repository preflight at FAIL and do not reopen
this slice finding.

### MEDIUM-1: ADDRESSED

Creation-result ownership is now explicit. `_request_context` grants ownership only to
the process that creates the normal run directory, while validate-only owns its result
(`scripts/build_run_manifest_v2_1.py:112-165`). The optional CLI fallback context uses
the same exclusive ownership rule before request parsing at lines 168-207. The failure
path writes only when `owns_result` is true at lines 437-464.

The two-process CLI test at `scripts/tests/test_b1a_run_manifest_slice.py:972-992`
proves exit codes `[0, 1]` and a final PASS creation result bound to the winning
manifest, closing the previous schedule-dependent loser overwrite.

### MEDIUM-2: ADDRESSED

Shared bounded reads stat first, read at most `limit + 1`, convert allocation failure to
a strict JSON error, and feed strict parsing at
`plant/src/vissim_strict/physical_projection.py:312-335`. Run-manifest trust limits are
declared at `plant/src/vissim_strict/run_evidence.py:33-37`; approval, topology,
preflight, and policy bindings enforce them before hashing/loading at lines 625-703 and
769-777. The independent replay also uses bounded loads and bounded safe hashes at
`scripts/approve_physical_stock_topology.py:626-762` and bounded approval loading at
lines 822-830.

Requests are stat-limited before open and read with a cap at
`scripts/build_run_manifest_v2_1.py:85-109`. The pre-parse CLI result context and owned
failure path at lines 168-207 and 437-464 permit deterministic stale-result replacement
for oversized/unreadable requests. Tests cover over-limit no-open behavior and stale
replacement at `scripts/tests/test_b1a_run_manifest_slice.py:866-890`, MemoryError at
lines 892-912, and every oversized bound trust artifact without manifest clobber at
lines 914-958.

### MEDIUM-3: ADDRESSED

The new authored-absolute resolver checks exact absolute spelling, exact workspace
prefix/case, native separators, on-disk component case, containment, file type, and
reparse components at `plant/src/vissim_strict/run_evidence.py:330-352`. Both shared
binding comparison (`plant/src/vissim_strict/run_evidence.py:511-527`) and producer
comparison (`scripts/build_run_manifest_v2_1.py:306-347`) use it. Independent preflight
validation applies it before trusting artifact bytes at
`scripts/approve_physical_stock_topology.py:329-349`.

Slash, component-case, and mocked reparse-alias mutations are rejected by
`scripts/tests/test_b1a_run_manifest_slice.py:547-571`.

### LOW-1: ADDRESSED

The copied validator set remains at `plant/src/vissim_strict/run_evidence.py:140-180`,
but the accepted remedy was an exact drift test. The test parses the pinned adapter's
`--controller` choices from source and requires set equality at
`scripts/tests/test_b1a_run_manifest_slice.py:745-766`, covering the adapter declaration
at `evaluation/controllers/vissim_stackelberg_adapter.py:4341-4380`.

## New Important defect

### IMPORTANT-1: exported validator depends on an unpackageable top-level script import

`validate_run_manifest` now performs
`from approve_physical_stock_topology import validate_approval_artifact` inside the
public package implementation (`plant/src/vissim_strict/run_evidence.py:732-740`). That
module exists under `scripts/`, not beside the package, and the import is caught as a
validation failure at lines 755-756. The API is nevertheless exported as a public
package validator by `plant/src/vissim_strict/__init__.py:12-31` and line 63.

The two current script consumers prepend `SCRIPT_ROOT` themselves
(`scripts/build_state_manifest_v2_1.py:12-17` and
`scripts/validate_state_projection_v2_1.py:15-20`), and the focused tests do the same at
`scripts/tests/test_b1a_run_manifest_slice.py:21-24`; this masks the dependency. A
supplemental local import probe from the `plant` package environment successfully
imported `src.vissim_strict` but returned `None` for
`find_spec("approve_physical_stock_topology")`. A valid manifest therefore fails the
independent-replay branch when the exported validator is used as an ordinary package
API without manually mutating `sys.path`.

This is Important because the slice explicitly requires a controller-independent
public validator reusable by consumers. Move the independent replay implementation
behind an importable package module, or otherwise provide a package-stable dependency;
add a subprocess test with only the documented plant/package path available.

## Verification evidence

Controller-supplied final-tree results were accepted as the regression evidence for
this scoped re-review:

- 79 focused/preflight tests: PASS.
- 43 A1/A2 tests: PASS.
- 20 plant compiler/projection/signal tests: PASS.
- `git diff --check`: PASS.

No live COM run or live timing campaign was evaluated. The only supplemental command
was the package import-resolution probe described under IMPORTANT-1; it performed no
network, COM, or source modification.
