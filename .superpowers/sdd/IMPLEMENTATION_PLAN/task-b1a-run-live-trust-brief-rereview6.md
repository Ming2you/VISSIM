# B1a trusted runner/live-evidence brief fix-round-6 scoped rereview

## Verdict

**PASS**

Re-evaluated findings: **ADDRESSED 1 / NOT_ADDRESSED 0**.

| Finding | Disposition |
|---|---|
| I17 base64 decision fields conceal adapter `ERROR=` evidence | **ADDRESSED** |

New defects introduced by the exact fix-round-6 I17 lines: **Critical 0 / Important 0**.

Live VISSIM COM and live p95 remain **NOT_EVALUATED**.

## Finding disposition

### I17 - ADDRESSED

`Exact preserved-artifact contracts` -> `Stdout and stderr` now requires replay to
canonical-decode and byte-for-byte re-encode the unpadded base64url token, strictly
decode its captured adapter stdout as UTF-8, split CRLF, bare-CR, and bare-LF logical
records, and fail on literal ASCII `ERROR=` anywhere in every decoded record. Exact,
embedded, and malformed forms all fail, so base64 decision framing can no longer conceal
the gating error predicate. Captured adapter stderr remains independently required to be
byte-empty.

The required-test delta pins correct source bytes and tokens for exact and embedded
errors, all three line-boundary forms, malformed base64url, invalid UTF-8, and benign
delimiter-looking decoded text without `ERROR=`. The stated fixture tokens round-trip to
their declared bytes. No new load-bearing Critical or Important contradiction is
introduced by these I17-only lines.
