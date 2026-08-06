# B1a trusted runner/live-evidence brief fix-round-5 scoped rereview

## Verdict

**FAIL**

Re-evaluated findings: **ADDRESSED 3 / NOT_ADDRESSED 0**.

| Finding | Disposition |
|---|---|
| I14 required stderr framing | **ADDRESSED** |
| I15 exact runlog and wall-time numeric contracts | **ADDRESSED** |
| I16 equal-time state/action binding | **ADDRESSED** |

New defects introduced by fix round 5: **Critical 0 / Important 1**.

Live VISSIM COM and live p95 remain **NOT_EVALUATED**.

## Finding dispositions

### I14 - ADDRESSED

`Exact preserved-artifact contracts` now makes decoded-empty stderr the sole framing
exception and atomically publishes it as exactly zero bytes. Every nonempty decoded
stderr stream receives deterministic CRLF normalization and one final CRLF, then forces
FAIL. The text supplies exact byte examples, per-file and per-record bounds, and the four
requested byte-exact tests. Zero-byte PASS no longer conflicts with record termination.

### I15 - ADDRESSED

`Stdout and stderr` replaces both placeholders with one anchored ASCII grammar. It fixes
token widths and ranges, derives decision wall time from monotonic integer endpoints,
serializes integer microseconds without locale or floating-point formatting, and uses
bounded, unpadded, round-tripped base64url for captured child streams.

`Versioned wall-time evidence` removes `elapsed_wall_sec` from the exact schema. Duration
is now only the rational value derived from bounded integer ticks and frequency; no
authored float, binary64 serialization, tolerance, or locale-dependent comparison
remains. The required tests cover comma-decimal locale behavior, token boundaries, and
reintroduction of either adjacent float.

### I16 - ADDRESSED

`State CSV` now binds each row to the last successfully accepted action published before
entry to that specific `LogStateCsv` invocation. It expressly excludes a same-time action
accepted afterward and enumerates initial, stepwise, continuous-static, event single-
decision, and event repeated-control ordering. Replay reconstructs the pinned VBS event
order, and the tests cover coincident and noncoincident schedules. The prior greatest-
simulation-time ambiguity is closed without changing the 13-column schema.

## New finding

### I17 - Base64 decision fields conceal adapter `ERROR=` evidence

**Fix-round-5 sections:** `Exact preserved-artifact contracts` -> `Stdout and stderr`
(lines 543-564) and `Required tests` (lines 835-841).

Fix5 moves the exact captured adapter stdout from visible `OneLine` text into an
unpadded base64url token. Replay validates and round-trips the token, but the mandatory
`ERROR=` predicate is still applied only to decoded outer runlog lines. Base64url cannot
contain `=`, so adapter stdout containing `ERROR=...` is hidden from that predicate after
the representation change. The listed delimiter-looking-token tests do not require an
`ERROR=` scan after decoding. An exit-zero adapter that publishes an otherwise valid
action and emits an error line can therefore satisfy the new decision grammar and evade
the previously gating fail-on-any-`ERROR=` rule.

**Concrete amendment:** After strict base64url round-trip validation, replay must split
the decoded UTF-8 adapter stdout by the explicitly defined CRLF/bare-CR/bare-LF logical
record rules and apply the same literal `ERROR=` policy to every decoded record. Any
decoded record containing `ERROR=` must force FAIL, including embedded or malformed
forms. Add fixtures for an exact error record, an embedded error token, line-boundary
variants, and benign delimiter-looking text. Decoded stderr remains independently
required to be empty.
