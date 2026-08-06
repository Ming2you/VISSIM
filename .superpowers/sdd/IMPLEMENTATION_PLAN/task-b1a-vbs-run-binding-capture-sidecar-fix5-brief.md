# B1a Slice 3B fix round 5

## Objective

Close the sole Important finding in
`task-b1a-vbs-run-binding-capture-sidecar-fix4-rereview.md` by making the shared
required-state envelope validator exact on producer, reusable replay, and pre-rename
CLI state-binding paths. No later-slice or live VISSIM work.

## Required fix

- Require `stopped_threshold_kph` to be a finite JSON double exactly `1.0`; reject bool
  and integer `1`.
- Require `paused_at_sim_sec`, `capture_sim_sec_before`, and
  `capture_sim_sec_after` to be finite nonnegative JSON doubles exactly equal to the
  root/capture time; reject bool and integer coercion.
- Validate every envelope count scalar with the bounded JSON-integer helper before
  comparison. In particular, `unobservable_count` and `external_source_count` must be
  integer zero, not bool `false`.
- Require root `total_vehicles` and `stopped_vehicles` to be present JSON integers and
  equal rederived totals; omission, null, bool, string, negative, overflow, or drift
  fails.
- Invoke this same exact envelope validator from CLI
  `--validate-state-run-binding`, so malformed required temp state fails before rename,
  as well as from capture producer and reusable capture validator.
- Add producer, reusable-validator, and CLI mutations for every independent repro in
  the fix4 rereview. Preserve every prior fix and the valid empty-capture case.

Update report/progress, run bounded no-VISSIM tests and `git diff --check`, and end
`IMPLEMENTED_PENDING_INDEPENDENT_REREVIEW`.

## Acceptance

All fix4 independent repros fail on all applicable paths; the 39-test focused suite
grows and remains green; live-only gates remain `NOT_EVALUATED`.
