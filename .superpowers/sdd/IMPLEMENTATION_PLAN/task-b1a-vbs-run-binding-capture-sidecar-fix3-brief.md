# B1a Slice 3B fix round 3

## Objective

Close both Important findings in
`task-b1a-vbs-run-binding-capture-sidecar-fix2-rereview.md` and the adjacent raw-lane
binding invariant before another independent review. Stay within Slice 3B; no
VISSIM/COM, projection timing, post-run/replay, or B1b work.

## Required fixes

1. Apply the existing 8 MiB required-state bound to every state read used by capture
   production, reusable capture validation, and CLI `--validate-state-run-binding`.
   Oversize input must fail before schema/run-binding acceptance. Add a real CLI test
   using an otherwise plausible oversized state artifact.
2. Validate each state vehicle record before comparison: exact six-field shape;
   signed-32-bit positive IDs; finite JSON-double `position_m` and `speed_kph` (reject
   bool, string, integer, NaN/Infinity); nonnegative speed; bounded negative position
   tolerance; boolean `stopped` equal to `speed_kph < 1.0`; unique vehicle ID. Remove
   coercive `float(...)` acceptance. Add producer and reusable-validator mutations for
   string, bool, integer, nonfinite, stopped mismatch, and extra/missing fields.
3. Independently parse each preserved `lane_raw` with the called VBS grammar (horizontal
   trim only, one hyphen, canonical positive signed-32-bit ASCII decimal components) and
   require it to equal `parsed_link_no/parsed_lane_no`. Add raw/parsed disagreement and
   malformed/non-ASCII lane tests so the sidecar actually binds the COM row to parser
   output.
4. Preserve all prior topology, bounded subprocess, temp/final validation, legacy
   provenance, BOM, integer-bound, and create-once concurrency fixes. Update report and
   progress, run bounded no-VISSIM regressions, and end
   `IMPLEMENTED_PENDING_INDEPENDENT_REREVIEW`.

## Acceptance

- Oversize state, coercible/tampered state records, and raw/parsed lane disagreement all
  fail in producer and reusable acceptance paths.
- Focused tests and `git diff --check` pass; live-only gates remain `NOT_EVALUATED`.
