# B1a Slice 3B fix round 1

## Objective

Address every Critical/Important finding in
`task-b1a-vbs-run-binding-capture-sidecar-slice-review.md` and close the adjacent
real-path and compatibility gaps confirmed by the main reviewer. Keep the work inside
Slice 3B: no projection-only invocation, combined timing receipt, post-run v2.2,
live replay, B1b dynamics, or live VISSIM run.

## Required fixes

1. Make vehicle-capture topology lookup compatible with the approved A1/A2 artifact,
   whose stock `link_no` is a canonical positive decimal string and `lane_no` is an
   integer. Reject malformed/noncanonical/boolean identities. Exercise the actual
   production compiler output or an exact compiler-shaped artifact, not an integer-only
   substitute.
2. Bound every required Python subprocess used by startup/capture-time run binding,
   prepublication state validation, and sidecar production. Quote the pinned Python
   path. On timeout, nonzero exit, unexpected stdout/stderr, or execution failure,
   fail closed with no PASS sidecar. A producer timeout after state publication may
   retain only the already validated immutable state.
3. Strict-parse and validate the exact same-directory state temp with the pinned
   `state_manifest_builder` before rename. After the no-replace rename, verify that the
   immutable final bytes have the same hash and pass the same run binding. Invalid temp
   state must not create a final state or PASS sidecar. Clean unique temp/request files
   on handled failure without deleting immutable evidence.
4. Preserve legacy state JSON compatibility: outside `RW_B1A_REQUIRED=1`, emit the
   original two-field `run_provenance` (`run_id`, `manifest_path`) and never emit a
   required PASS sidecar. Required mode emits exactly the three bound fields including
   lowercase `manifest_sha256`.
5. Deepen the no-VISSIM test matrix on the actual invoked path. Include real manifest
   validation/approval replay rather than relying only on a mocked validator; exact
   topology string IDs; 64-sample priority and 20,000-row bound; empty/nonempty exact
   vehicle-record keys; state/capture BOM or malformed UTF-8 rejection; count/type/hash/
   path/run/time/sample mutations; huge integer/nonfinite rejection; concurrent
   create-once publication; helper timeout/framing/stderr/nonzero; and final no-clobber
   behavior. Tests must not launch VISSIM.

## Evidence and handoff

- Update the Slice 3B implementation report with corrected claims and exact test counts.
- Append fix-round status to `progress.md`.
- Do not mark Slice 3B approved; end at
  `IMPLEMENTED_PENDING_INDEPENDENT_REREVIEW`.
- Run focused Slice 3B tests plus adjacent run-manifest/watchdog, B1a core/projection/
  reference, adapter/audit, compiler/signal regressions and `git diff --check`.
