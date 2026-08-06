# B1a trusted runner/live-evidence brief fix-round-6 report

## Scope

Planning-only I17 closure. No code, schema, producer, or live-run implementation was
changed. Live VISSIM COM and live p95 remain `NOT_EVALUATED`.

## Changed files

- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-brief.md`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-brief-fix6-report.md`

## I17 disposition

**ADDRESSED.** The controlling `Stdout and stderr` contract now requires replay, after
strict canonical unpadded-base64url round-trip and strict UTF-8 decoding of captured
adapter stdout, to split decoded logical records at CRLF, bare CR, and bare LF and fail
on literal ASCII `ERROR=` anywhere in any record. Exact, embedded, and malformed forms
all fail. The decoded adapter stderr contract remains independently byte-empty.

The required-test matrix now pins exact source bytes and base64url tokens for an exact
error record, an embedded token, all three line-boundary variants, invalid UTF-8,
padding/length/alphabet/non-round-trip base64url failures, and benign delimiter-looking
decoded text with no literal `ERROR=`.

## Self-review

The amendment is limited to I17 and preserves all outer runlog, framing, size, stderr,
and gating predicates. It does not broaden B1a scope or claim implementation or live
evidence completion.
