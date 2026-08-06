# B1a run-manifest slice fix round 2 re-review

## Scope and verdict

Reviewed the original slice brief, fix-round-1 re-review, appended fix-round-2 report,
and `review-b1a-run-manifest-slice-fix2-current.diff`. This review is limited to
IMPORTANT-1 and new Critical/Important defects introduced by its fix delta. Future VBS,
watchdog, adapter projection, post-run artifact, and live replay slices remain outside
scope.

- IMPORTANT-1: **ADDRESSED**.
- New defects: **0 Critical, 1 Important**.
- Overall verdict: **CHANGES_REQUIRED** for the new non-ASCII protocol defect below.
- Live VISSIM COM: **NOT_EVALUATED**.
- Live combined p95: **NOT_EVALUATED**.

## IMPORTANT-1 disposition

### IMPORTANT-1: ADDRESSED

The exported package no longer imports the top-level workspace script. Instead,
`plant/src/vissim_strict/run_evidence.py:22` imports the package-local
`validate_approval_replay`, and the run-manifest validator obtains the already resolved
and byte-checked `producer_sources.topology_approval_validator` path at lines 729-748.
Producer source bindings, including that validator, are canonical-path and current-file
hash checked before replay at `plant/src/vissim_strict/run_evidence.py:659-675`.

The package-local client executes that exact bound file in a child without importing it
or changing consumer `sys.path` (`plant/src/vissim_strict/approval_replay.py:64-100`).
The child validation-only mode forbids build arguments and calls the existing sole
`validate_approval_artifact` implementation at
`scripts/approve_physical_stock_topology.py:986-1024`; approval, preflight, A1/A2, and
topology replay logic is not duplicated into the package client.

The child result is not accepted as an unverified summary. The package process requires:

- bounded post-exit output size and empty stderr
  (`plant/src/vissim_strict/approval_replay.py:81-100`, `:132-138`);
- an exact closed result field set and canonical framing at lines 139-147;
- PASS status, empty reasons, and zero worker exit at lines 143-147;
- exact workspace identity plus canonical contained approval/preflight/topology paths at
  lines 148-155;
- fresh approval, preflight, and topology file hashes at lines 156-163;
- a bounded strict reload of the exact replayed preflight at lines 167-179.

`validate_run_manifest` then compares the replayed five-key topology binding and exact
preflight path/fingerprint at `plant/src/vissim_strict/run_evidence.py:750-763`, and all
producer/configuration records must equal the child-validated preflight at lines
768-778. This preserves the independent approval replay and source-equality trust
checks while removing the consumer-side `scripts/` import requirement.

The package-boundary regression launches outside the workspace with only `plant` on
`PYTHONPATH`, proves the top-level approval module is unavailable, validates through the
exported API, and verifies consumer `sys.path` is unchanged
(`scripts/tests/test_b1a_run_manifest_slice.py:584-628`). This directly covers the prior
finding.

## New Important defect

### IMPORTANT-2: the claimed ASCII child protocol rejects valid non-ASCII workspace paths

The validation result contains absolute `workspace_root`, approval, preflight, and
topology paths (`scripts/approve_physical_stock_topology.py:956-983`). The worker emits
it with:

`(canonical_json_text(result) + "\n").encode("ascii")`

at `scripts/approve_physical_stock_topology.py:1023`. However, the shared canonical
serializer deliberately preserves Unicode strings with `ensure_ascii=False`
(`plant/src/vissim_strict/topology.py:59-85`, specifically lines 73-74). Any valid
non-ASCII workspace or bound path therefore raises `UnicodeEncodeError` after the
worker's fail-closed exception boundary, writes a traceback to stderr, and returns no
protocol result.

The parent has the same incompatibility: it decodes stdout strictly as ASCII at
`plant/src/vissim_strict/approval_replay.py:134-138` and reconstructs canonical output
with `.encode("ascii")` at lines 139-142. Thus the protocol is package-stable only for
ASCII paths, despite the slice's explicit Windows non-ASCII path contract. The focused
package test uses an ordinary ASCII temporary root
(`scripts/tests/test_b1a_run_manifest_slice.py:584-628`) and does not exercise this case.

Required fix: define one exact ASCII wire serializer that escapes non-ASCII JSON text
and use it identically in worker and parent, or define the wire as strict UTF-8 without
BOM and validate that exact framing. Add a subprocess package-boundary test whose
workspace and relevant bound paths contain non-ASCII characters.

No other new Critical or Important defect was identified in the scoped fix delta.

## Verification evidence

- Implementer-reported final suite: **143 tests PASS**.
- Controller-independent focused rerun: **30 tests PASS**.
- No additional regression suite was rerun for this document; review was by the scoped
  snapshot and supplied final-tree results.
- Live COM and live p95 remain **NOT_EVALUATED**.
