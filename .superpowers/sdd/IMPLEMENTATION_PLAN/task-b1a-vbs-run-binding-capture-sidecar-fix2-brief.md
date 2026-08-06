# B1a Slice 3B fix round 2

## Objective

Close every finding in
`task-b1a-vbs-run-binding-capture-sidecar-fix1-rereview.md` without expanding beyond
Slice 3B. No VISSIM/COM run, projection-only invocation, combined timing receipt,
post-run v2.2, replay, or B1b work.

## Required fixes

1. Required state, vehicle-capture request, and vehicle-capture sidecar byte paths must
   reject a UTF-8 BOM even when the remaining JSON is otherwise valid. Preserve the
   shared loader's legacy behavior where required by other callers; introduce a bounded
   no-BOM strict boundary for this evidence path. Retain strict UTF-8, duplicate-key,
   nonfinite-number, size, and exact-schema checks. Test BOM plus an otherwise valid
   state, request, and sidecar.
2. Bound every integer authored or accepted by capture evidence. Vehicle/link/lane
   identifiers fit signed 32-bit positive integers; counts fit the 20,000-record request
   bound; monotonic endpoints fit positive signed 64-bit integers. Apply the same limits
   in producer and reusable validator, including state-record and sample cross-checks.
   Reject booleans and huge values even when timer subtraction or count equality remains
   arithmetically valid. Add focused mutation tests.
3. Add a real concurrent no-VISSIM create-once test for
   `publish_vehicle_capture_evidence_create_once`. Start simultaneous workers against
   one absent output, require exactly one success, require every loser to fail closed,
   and prove final bytes validate and are not replaced. Keep the test deterministic and
   bounded.
4. Correct the report/progress claims and run the focused Slice 3B plus adjacent bounded
   regressions. End `IMPLEMENTED_PENDING_INDEPENDENT_REREVIEW`; do not self-approve.

## Acceptance

- Independent repros for valid-body BOM and huge timer endpoints now fail.
- Concurrent publisher test proves exactly one immutable winner.
- Former topology, timeout, pre-rename validation, and legacy-provenance fixes remain
  green.
- `git diff --check` passes; live gates remain honestly `NOT_EVALUATED`.
