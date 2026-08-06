# Independent review 2: B1a run-manifest slice

## Verdicts

- Requirements: **FAIL / changes required**.
- Code quality: **NEEDS_CHANGES**. The implementation is generally focused and readable,
  but trust validation is split across unequal code paths and several concurrency/path
  contracts are asserted more strongly in the report than the code guarantees.
- Live VISSIM COM: **NOT_EVALUATED**.
- Live combined p95: **NOT_EVALUATED**.

## Severity counts

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 3 |
| Medium | 3 |
| Low | 1 |
| Total | 7 |

## Findings

### HIGH-1: the shared validator does not independently replay approval or preflight trust

`validate_run_manifest` loads the bound preflight and checks only
`schema_version/status/reasons/fingerprint_sha256`, then derives role bindings from its
`artifacts` map (`plant/src/vissim_strict/run_evidence.py:655-679`). It similarly accepts
an approval after checking only four selected values and checks the topology only by its
authored `semantic_sha256` field (`plant/src/vissim_strict/run_evidence.py:681-710`). It
does not call `validate_preflight_artifact`, `validate_approval_artifact`, or the physical
topology validator. This is materially weaker than creation, which does call the two
independent validators (`scripts/build_run_manifest_v2_1.py:199-214`).

The focused test makes the gap explicit: its approval and preflight fixtures contain
only skeletal self-declared PASS objects (`scripts/tests/test_b1a_run_manifest_slice.py:94-140`),
yet the shared validator accepts them as the happy path at line 241. The existing state
consumers do delegate at `scripts/build_state_manifest_v2_1.py:400-406` and
`scripts/validate_state_projection_v2_1.py:435-441`, but delegation to this weaker
validator does not preserve creation-time trust. A mixed or coherently rehashed
preflight can therefore be accepted after creation.

Required fix: make the public validator independently replay the exact approval,
preflight, topology, source universe, and five-key binding, or require and verify one
shared validated bundle that proves all of them. Replace the skeletal happy-path fixture
with artifacts that pass the independent validators, then add coherent-rehash rejection
tests.

### HIGH-2: create-once publication is exclusive but not atomic to readers

The destination becomes visible as soon as `os.open(...O_EXCL)` succeeds, before the
payload is written, flushed, and fsynced (`plant/src/vissim_strict/run_evidence.py:777-790`).
A simultaneous reader or validate-only invocation can observe an empty or partial
manifest. The function also hashes but does not strictly reload and revalidate the
published bytes (`plant/src/vissim_strict/run_evidence.py:796`). This does satisfy
single-winner writer exclusion, but not the brief's atomic-publication/reload contract.

The race test at `scripts/tests/test_b1a_run_manifest_slice.py:420-430` checks only that
one thread reports `created`, one reports `failed`, and the final file validates after
both finish. It cannot detect partial visibility.

Required fix: use a no-clobber publication protocol whose final pathname is exposed only
after complete durable bytes exist, and strictly reload/revalidate the final bytes before
returning success. Add a process-level writer/reader barrier test, not only a same-process
thread race.

### HIGH-3: the official preflight producer cannot create the required closed role universe

The run manifest requires the 12 producer roles and eight configuration roles declared
at `plant/src/vissim_strict/run_evidence.py:68-91`. The checked-in preflight producer's
source map contains legacy names such as `runner` and `generated_vbs`, and omits
`run_manifest_producer`, `state_manifest_builder`, `monotonic_clock_helper`, the policy,
and the other new roles (`scripts/build_preflight_manifest.py:46-62`). Its CLI can only
override those existing keys (`scripts/build_preflight_manifest.py:766-771`).

The passing provenance fixture works around this by manually authoring arbitrary extra
artifacts and checks (`scripts/tests/test_b1a_core_provenance.py:306-327`); those bytes
cannot be reproduced by the claimed `build_preflight_manifest.py` CLI. Consequently the
run-manifest producer has no legitimate local preflight-production path for its own
required inputs, even though the report says the complete source universe can be rebuilt
through the approved preflight flow.

Required fix: teach the official preflight producer and its exact validator the normative
role constants and paths, then exercise producer -> preflight validation -> approval ->
run-manifest creation without manually fabricating the preflight.

### MEDIUM-1: concurrent CLI writers can leave a schedule-dependent creation result

Two normal writers for the same absent run directory race in `mkdir` at
`scripts/build_run_manifest_v2_1.py:129-140`. The winner later writes PASS at lines
321-333; the loser recovers the same `creation_result_output` and writes FAIL at lines
335-360. Whichever atomic replacement happens last controls the final evidence, so a
successfully created immutable manifest can be paired with FAIL, or vice versa, based
only on scheduling.

The current concurrency test bypasses the CLI and creation-result path entirely
(`scripts/tests/test_b1a_run_manifest_slice.py:420-430`). Add a two-process CLI test and
define one ownership rule that prevents the losing invocation from overwriting the
winner's result for that attempt.

### MEDIUM-2: oversized JSON does not meet stale-result/fail-closed handling

`_read_request` reads the whole request before checking the 1 MiB limit
(`scripts/build_run_manifest_v2_1.py:82-98`). A request over the limit is rejected before
it is parsed, leaving `request` empty and preventing recovery of an otherwise usable
`creation_result_output` at lines 335-344. Extremely large files can also exhaust memory
before the size check, and `MemoryError` is not caught. Bound preflight, approval,
topology, and policy JSON are loaded with no byte limit at
`plant/src/vissim_strict/run_evidence.py:659`, `:685`, `:703`, and `:715`.

The advertised large-value test uses only a 100,000-character field
(`scripts/tests/test_b1a_run_manifest_slice.py:557-562`), below the request limit. Add
over-limit and bounded-artifact tests that seed stale PASS evidence and prove a
deterministic FAIL replacement without unbounded reads.

### MEDIUM-3: preflight path comparison normalizes away exact spelling and reparse aliases

`_preflight_artifact_binding` resolves the preflight-authored absolute path and converts
the resolved target back to a relative path before equality (`plant/src/vissim_strict/run_evidence.py:452-468`).
The producer repeats this normalization at `scripts/build_run_manifest_v2_1.py:223-260`.
Unlike manifest bindings, these paths are not walked component-by-component for exact
case/spelling and reparse rejection. A junction/symlink alias to a contained canonical
file can therefore be normalized into agreement, contrary to the exact decoded path and
non-reparse duplicate-binding policy.

The reparse unit test mocks only the final manifest file resolver
(`scripts/tests/test_b1a_run_manifest_slice.py:385-391`); it does not mutate a preflight
artifact path. Validate the preflight-authored lexical path itself and compare the exact
canonical spelling rather than only the resolved target.

### LOW-1: adapter controller policy is duplicated manually

`ADAPTER_CONTROLLERS` is a copied 40-value set in
`plant/src/vissim_strict/run_evidence.py:109-149`, while the pinned adapter owns a second
choices list at `evaluation/controllers/vissim_stackelberg_adapter.py:4341-4380`. They
match today, but nothing enforces continued equality. A parser change can make manifest
validation disagree with the pinned executable parser while all source hashes remain
internally valid. Share one controller-choice definition or add an exact drift test.

## Contract checklist

| Contract | Result | Notes |
|---|---|---|
| Two simultaneous local writers | Partial | O_EXCL gives one manifest writer; atomic visibility and CLI result ownership fail. |
| Validate-only / serial deterministic result | PASS | Byte-identical reuse preserves mtime; differing bytes do not clobber. |
| Exact nested fields/types/hashes | Partial | Manifest-local shapes are strong; bound approval/preflight/topology replay is shallow. |
| Independent topology/preflight/source checks | FAIL | Strong only in producer creation path, not shared/downstream validation. |
| Duplicate source/config equality | Partial | Adapter and policy equality work; preflight lexical paths are normalized. |
| Contained Windows paths / reparse | Partial | Manifest paths are strict; preflight-authored aliases are not. |
| Supported-version policy | PASS | Exact policy/hash and `20`/`2020` normalization tests pass. |
| Malformed / very-large JSON | FAIL | Ordinary malformed/bounded values fail closed; over-limit/unbounded cases do not. |
| Monotonic helper contract | PASS | One Windows >=3.10 reading, exact ASCII frame, empty normal stderr, strict parser. |
| Existing state-consumer delegation | Partial | Both delegate, but the delegated validator is weaker than creation. |

## Local verification

All requested local unit suites passed: 130 tests, 0 failures, 0 skips.

- `scripts.tests.test_b1a_run_manifest_slice`: 17 PASS.
- `scripts.tests.test_b1a_core_provenance`: 19 PASS.
- `scripts.tests.test_build_preflight_manifest` plus
  `scripts.tests.test_validate_baseline_snapshot`: 31 PASS.
- `scripts.tests.test_vissim_lane_graph` plus real-network variant: 24 PASS.
- `scripts.tests.test_compile_physical_stock_topology` plus real-network variant: 19 PASS.
- Plant compiler, physical-projection, and signal-program suites: 20 PASS.
- `git diff --check`: PASS with existing LF-to-CRLF warnings only.

Passing tests do not change the requirements verdict because the independent replay,
atomic visibility, official preflight-production, concurrent CLI result, and oversized
input cases above are absent from the suite.
