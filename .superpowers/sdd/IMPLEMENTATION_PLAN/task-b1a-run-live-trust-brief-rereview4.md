# B1a trusted runner/live-evidence brief fix-round-4 scoped rereview

## Verdict

**FAIL**

Re-evaluated findings: **ADDRESSED 2 / NOT_ADDRESSED 0**.

| Finding | Disposition |
|---|---|
| I3 exact nested schemas, bindings, and cardinalities | **ADDRESSED** |
| I13 preservation and replay of existing run evidence | **ADDRESSED** |

New defects introduced by fix round 4: **Critical 0 / Important 3**.

Live VISSIM COM and live p95 remain **NOT_EVALUATED**.

## Finding dispositions

### I3 - ADDRESSED

`Normative artifact-role constants` now fixes the exact phase, success minimum, failure
minimum, and maximum for all 16 closed roles. The authored `artifact_roles` object must
equal that table field-for-field, while producer and validator decisions come from one
checked-in constant rather than the authored thresholds. The success equations close
all singletons, the five-way state companion bijection, action JSON/CSV pairing, and the
decision identities; failed attempts have explicit zero-to-maximum inventory rules and
cannot qualify.

`Exact duplicate bindings` also closes the remaining repeated sources: the current
producer/config intersection is exactly `adapter`; policy, preflight producer, action
provenance, generated-config-copy, and post-run run-manifest sightings are mandatory
equality checks. Demand-profile absence and presence have exact null/string behavior.
The differently shaped existing action sightings are compared by canonical resolved
path and byte hash under `Exact CLI and path contract`, not accepted as independent
claims. These checks occur before semantic-hash comparison.

### I13 - ADDRESSED

`Exact preserved-artifact contracts` now supplies byte framing and CSV dialect rules,
exact headers, typed fields, row order/cardinality, action/cumulative equality, signal
write/readback reconstruction, anchored completion/counter/decision log predicates,
fail-on-any `ERROR=`, an empty-stderr policy, and exact v2.2 error and wall-time field
sets. Replay derives these predicates from the preserved bytes before comparing authored
status, counts, or hashes. The original omission of these artifacts and their replay
predicates is therefore closed.

The three contradictions below are defects in the new fix-round-4 contracts, rather
than continuations of the prior summary-only I13 design.

## New findings

### I14 - Required stderr framing has no satisfiable PASS representation

**Amended brief sections:** `Exact preserved-artifact contracts` -> `Encoding, framing,
and CSV dialect` and `Stdout and stderr` (lines 381-391 and 496-518).

The runlog helper must write both stdout and stderr with the stated CRLF and final-CRLF
rules, but PASS stderr must be exactly zero bytes. A zero-byte singleton cannot also end
in CRLF. Implementations that follow the shared framing sentence will emit two bytes and
fail the empty-stderr predicate; implementations that emit zero bytes violate the helper
framing contract. Required-mode PASS is therefore ambiguous at a mandatory singleton.

**Concrete amendment:** State that decoded-empty stderr is the sole exception to record
termination: publish an atomic zero-byte `stderr_runlog_v2_2.txt`. For a nonempty decoded
stream, normalize records to CRLF with one final CRLF and fail the run. Add byte-exact
tests for zero bytes, CRLF-only, whitespace-only, and one diagnostic line.

### I15 - Runlog and wall-time numeric comparisons reference undefined grammars

**Amended brief sections:** `Exact preserved-artifact contracts` -> `Stdout and stderr`
and `Versioned wall-time evidence` (lines 496-518 and 554-577).

The claimed exact decision-line regex contains the undefined metavariables `<finite>`
and `<bounded-one-line-text>`; no byte bound, delimiter rule, or numeric production rule
is attached to them. This matters on Windows because the grounded VBS producer emits
`wall_sec` with locale-sensitive `CStr(Round(...))`
(`scripts/run_real_world_stackelberg_controller.vbs`, line 738), while
`runlog-capture-v2.2` only changes stream encoding. Separately,
`elapsed_wall_sec` must agree under a "shared exact numeric comparison rule," but no such
rule is defined in this brief or the governing brief. Producers and replay validators
can therefore disagree on decimal grammar, binary64 rounding, or tolerance.

**Concrete amendment:** Replace both placeholders with a literal anchored grammar,
explicit maximum UTF-8 byte lengths, and an unambiguous rule for locating or escaping
the stdout/stderr fields. Require a locale-invariant producer for decision `wall_sec` and
state whether it is a canonical nonnegative JSON number. For wall-time, either remove
the redundant diagnostic float and derive duration only from ticks/frequency, or define
the exact IEEE-754 operation, canonical JSON serialization, and equality/tolerance rule
used by both producer and replay. Add comma-decimal locale and adjacent-representable-
float tests.

### I16 - State-row action binding is ambiguous at equal simulation time

**Amended brief section:** `Exact preserved-artifact contracts` -> `State CSV`
(lines 393-413).

The row must copy the most recent successful action "at or before that row," but the
ordering domain is not defined. In current continuous-static and single-decision event
paths, when control start is also a state-log instant, `LogStateCsv` runs before
`RunControllerDecision` at the same `sim_sec`
(`scripts/run_real_world_stackelberg_controller.vbs`, lines 470-479 and 529-541). A
validator choosing the greatest action `sim_sec <= row.sim_sec` selects the later
same-time action, while a validator replaying publication order selects the previous
action. Both readings satisfy the prose and can produce opposite integrity results.

**Concrete amendment:** Define the relation by replayed VBS event/publication order:
each state row binds the last action JSON successfully accepted before that specific
`LogStateCsv` invocation, and an equal-`sim_sec` action published afterward is excluded.
Enumerate the control-start/log tie for each run mode and test both coincident and
noncoincident schedules. If replay is not required to reconstruct invocation order, add
an explicit action identity/hash column or companion binding rather than inferring from
simulation time alone.
