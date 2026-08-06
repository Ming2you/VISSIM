# B1a run-manifest slice fix round 3 re-review

## Scope and verdict

Reviewed the fix-round-2 re-review, appended fix-round-3 report, and
`review-b1a-run-manifest-slice-fix3-current.diff`. This review is limited to
IMPORTANT-2 and new Critical/Important defects introduced by the framing fix. Future
VBS, watchdog, adapter, post-run, and live-replay slices remain outside scope.

- IMPORTANT-2: **ADDRESSED**.
- New defects introduced by this fix: **0 Critical, 0 Important**.
- Scoped verdict: **PASS**.
- Live VISSIM COM: **NOT_EVALUATED**.
- Live combined p95: **NOT_EVALUATED**.

## IMPORTANT-2 disposition

### IMPORTANT-2: ADDRESSED

The package now owns one shared wire serializer,
`validation_result_wire_bytes`, at
`plant/src/vissim_strict/approval_replay.py:49-55`. It serializes with the existing
canonical JSON function, encodes strict UTF-8, appends exactly one LF, and emits no BOM.
Because the worker imports this exact helper at
`scripts/approve_physical_stock_topology.py:54-57` and uses it at lines 1024 and 1036,
worker and parent cannot silently diverge between ASCII and UTF-8 framing.

The parent decoder at `plant/src/vissim_strict/approval_replay.py:58-72` is the exact
inverse and fails closed:

- line 59 rejects more than 65,536 bytes before decoding;
- lines 61-62 reject a UTF-8 BOM;
- lines 63-67 use strict UTF-8 decoding and strict JSON parsing;
- lines 68-69 require the closed validation-result field set;
- lines 70-71 reserialize with the shared encoder and require byte-for-byte equality,
  which rejects missing/extra output, noncanonical JSON, CRLF, or anything other than
  exactly one final LF.

The child still uses file-backed stdout/stderr, a 120-second timeout, no stdin, and
checks both stream sizes before reading them
(`plant/src/vissim_strict/approval_replay.py:91-127`). The parent rejects any stderr at
lines 156-161. On the worker side, the complete result is serialized and size-checked
before stdout publication; an oversized result is replaced by a fixed deterministic
FAIL result and reserialized at
`scripts/approve_physical_stock_topology.py:1024-1038`. Thus normal PASS output and
failure output are memory-bounded at the protocol read boundary and malformed/oversized
wire data cannot establish PASS.

Unicode support is genuine rather than escaped around the failing code path. Validation
results retain absolute workspace, approval, preflight, and topology strings in
`scripts/approve_physical_stock_topology.py:956-983`; UTF-8 now carries those exact
Unicode strings without a BOM. Unit coverage round-trips Unicode bytes and rejects BOM,
invalid UTF-8, CRLF, and oversize frames at
`scripts/tests/test_b1a_run_manifest_slice.py:313-349`.

The end-to-end package test creates the official chain under a Korean non-ASCII
workspace and moves a bound producer source to a non-ASCII filename containing a space
(`scripts/tests/test_b1a_run_manifest_slice.py:636-665`). It then launches outside that
workspace with only `plant` on `PYTHONPATH`, confirms the top-level approval script is
not importable, invokes the exported validator, and checks that consumer `sys.path`
remains unchanged at lines 669-714.

The framing change does not weaken independent replay or source trust. The worker's
validation-only mode still calls the sole `validate_approval_artifact` implementation
at `scripts/approve_physical_stock_topology.py:987-1010`. The package parent still
requires empty stderr, exact PASS/exit/schema/status, canonical contained paths, and
fresh approval/preflight/topology hashes at
`plant/src/vissim_strict/approval_replay.py:156-190`. Finally,
`validate_run_manifest` still compares the replayed five-key topology and exact
preflight binding, then checks every producer/configuration record against the replayed
preflight at `plant/src/vissim_strict/run_evidence.py:729-778`.

No new Critical or Important defect was identified in this framing-only delta.

## Verification evidence

- Implementer-reported final regression suite: **146 PASS**.
- Controller-independent wire/non-ASCII rerun: **3 PASS**.
- No additional suite was rerun for this document; the review used the scoped snapshot
  and supplied final-tree results.
- Live COM and live p95 remain **NOT_EVALUATED**.
