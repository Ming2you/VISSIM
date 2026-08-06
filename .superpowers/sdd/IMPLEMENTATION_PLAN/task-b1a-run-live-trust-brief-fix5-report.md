# B1a trusted runner/live-evidence brief fix-round-5 report

## Scope

Final planning-only amendment. Changed only:

- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-brief.md`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-brief-fix5-report.md`

No code, test, fixture, generated output, or live VISSIM artifact was edited. No live COM
or live p95 PASS is claimed.

## Finding dispositions

### I14 - ADDRESSED

Decoded-empty required-mode stderr is now the sole record-framing exception and is
published atomically as exactly zero bytes. Every nonempty stderr stream is normalized
to CRLF with one final CRLF and fails. The brief gives exact expected bytes and tests for
zero-byte, CRLF-only, whitespace-only, and one-line diagnostic inputs, plus explicit
per-file and per-record byte bounds.

### I15 - ADDRESSED

The decision log now has one literal anchored ASCII regex. `sim_sec` and `wall_sec` have
explicit token widths, ranges, and a locale-free integer-microsecond serialization rule.
Captured stdout/stderr are unambiguously represented as bounded unpadded base64url over
their exact UTF-8 bytes; delimiter-looking content cannot alter field boundaries.

`wall-time-profile-v2.2` no longer authors `elapsed_wall_sec`. Its only duration rule is
the exact rational `(end_tick-start_tick)/frequency_hz` from bounded schema integers, so
there is no locale, binary64 serialization, equality, or tolerance choice. Tests cover a
comma-decimal locale, adjacent-representable-float cases, and rejection of a reintroduced
elapsed field.

### I16 - ADDRESSED

State rows now bind the last successfully accepted action published before entry to that
specific `LogStateCsv` invocation, not the greatest action simulation time. The brief
enumerates initial, stepwise, continuous-static, event single-decision, and event
repeated-control ordering, including both equal-time orderings. Replay is required to
reconstruct the pinned VBS publication sequence, so the exact existing 13-column v2.2
state CSV remains sufficient without an inferred or unversioned identity column.

## Grounding used

- `scripts/run_real_world_stackelberg_controller.vbs` lines 411-551 establish all run-
  mode decision/log orderings, including the two log-before-decision control-start ties.
- The same VBS lines 713-753 show locale-sensitive `CStr(Round(...))`, captured adapter
  stdout/stderr, and that `lastActionJson` advances only after successful action
  validation/application.
- The same VBS lines 1613-1638 and 2644-2691 show that each state row reads status and
  numeric text from `lastActionJson` at `LogStateCsv` time.
- `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1` lines 388-399 show
  the legacy wall-clock subtraction and authored rounded float replaced by the v2.2
  monotonic tick contract.

## Self-review

- Zero-byte stderr no longer conflicts with a mandatory final terminator.
- No angle-bracket numeric or text placeholder remains in the decision grammar; every
  variable token has a literal alphabet/production, semantic range, and byte bound.
- Decision numeric output is independent of the Windows decimal separator, and total
  wall duration has exactly one integer-tick-derived meaning with no authored float.
- Equal simulation time cannot select a future action: publication order controls in all
  current modes, including failed decisions that do not advance the binding.
- Scope remains planning-only and limited to the requested brief and this report. Live
  VISSIM COM capture and live p95 remain `NOT_EVALUATED`.

Verification was document self-review and source inspection only; implementation tests
were not run because this round explicitly forbids code edits.
