# B1a trusted runner/live-evidence brief fix-round-3 rereview

## Verdict

**FAIL**

Re-evaluated findings: **ADDRESSED 2 / NOT_ADDRESSED 2**.

| Finding | Disposition |
|---|---|
| I3 exact nested shapes/types/hash scopes/cardinalities | **NOT_ADDRESSED** |
| I11 three-read monotonic capture/combined timing | **ADDRESSED** |
| I12 projection reference schema and consumer validation | **ADDRESSED** |
| I13 preservation/replay of existing run evidence | **NOT_ADDRESSED** |

New in-scope defects introduced by round 3: **Critical 0 / Important 0**.

Live VISSIM COM and live p95 remain **NOT_EVALUATED**.

## Finding dispositions

### I3 - NOT_ADDRESSED

Round 3 addresses the prior hash and process-shape gaps: it defines run-manifest numeric
rules and canonical JSON v1 scope, defines process sentinels, maps role phases, requires
the duplicate run-manifest bindings to agree, and defines
`run_artifact_set_semantic_sha256` over an exact sorted record list.

The remaining cardinality contract is not exact and is partly self-declared by the
artifact being validated. Every `artifact_roles` entry carries
`success_min_count/failure_min_count/max_count`, but the brief does not provide the
required constant tuple for each closed role. “Exactly one for every singleton role”
does not enumerate which roles are singleton, and “at least one ... action” does not say
whether both `control_action_json` and `control_action_csv` are required or require equal
cardinality. Failed-attempt minima/maxima are likewise not fixed per role. A producer and
validator can therefore disagree, or accept authored thresholds that weaken companion
requirements, while satisfying the stated field shape and semantic hash.

There is also an unresolved duplicated configuration binding: `demand_profile` appears
both as `configuration.inputs.demand_profile` (`path/file_sha256`, nullable together)
and as `configuration.simulation.demand_profile`, but the latter's exact string/null
representation and equality to the input binding are not defined. The same exact-byte
equality should be stated wherever an executed adapter/config path is repeated between
`producer_sources` and `configuration.inputs`.

**Required amendment:** Provide a normative per-role table containing fixed phase,
success minimum, failure minimum, maximum, and cross-role cardinality equations. At
minimum, define the action JSON/CSV pairing and every singleton explicitly; validators
must compare the authored role table to those constants rather than trusting it. Define
the absent/present simulation `demand_profile` value and require it to match the input
binding, plus equality for every duplicated executed-source binding.

### I11 - ADDRESSED

Lines 137-167 now define three ordered calls to the same pinned
`python_perf_counter_ns` helper: one before the first scalar count, one after atomic state
publication and before capture-sidecar serialization, and one after projection-only
completion. The capture sidecar has exact
`clock/start_ns/end_ns/elapsed_sec` fields and reuses the combined sample's first
endpoint; the timing receipt uses the first and final endpoints. Output encoding,
framing, stderr, positivity, ordering, timeout, process-window, source, and Python checks
are fail-closed. Replay recomputes both elapsed values from raw integers. The prior
publication-order contradiction is closed.

The phrase “third ... call” at line 140 refers to the added helper call, while lines
159-161 unambiguously establish its chronological position as the middle of three; this
wording is not material to the executable contract.

### I12 - ADDRESSED

Lines 180-187 now specify an exact `physical-projection-reference-v2.1` field set,
bounded content, status/reasons rule, canonical JSON v1 hash scope, run/state/topology
and projection-sidecar bindings, counts and residual, and no assignments. Both the
normal adapter and replay must reopen the state and sidecar and recompute file hashes,
semantic hashes, counts, and residuals. Any malformed, escaping, non-PASS, or mismatched
reference fails before candidate or fallback evaluation. This closes the trust boundary
between projection-only execution and the normal controller.

### I13 - NOT_ADDRESSED

Round 3 restores closed roles for the requested existing artifacts: state and cumulative
action CSVs, per-decision action JSON/CSV, stdout/stderr logs, signal readback, VISSIM
error evidence, wall-time evidence, and the generated config. It also requires replay to
reopen them rather than trust the post-run status/process object.

However, the replay predicates are not exact enough to implement consistently.
“Acceptable stderr” is undefined, and “no integrity `ERROR=`” supplies neither a closed
line grammar nor whether every `ERROR=` line fails. The stdout
`STAGE=SIM_DONE` check is not defined as an anchored decoded line/token. No exact CSV
schemas, encoding rules, row-identity/cardinality relationships, or signal-readback PASS
conditions are given, so “reopens ... CSVs, readback ... and recomputes these predicates”
has no stated predicate for those files. Merely reopening and hashing them does not prove
their existing required evidence semantics.

**Required amendment:** Define strict encoding/BOM and line grammar for stdout/stderr,
an anchored unique completion token, and a closed stderr/`ERROR=` acceptance policy.
Define exact headers/types/order and required row/count/identity relations for state,
cumulative action, per-decision action, and signal-readback CSV evidence, plus the exact
VISSIM-error and wall-time PASS schemas. State which checks are required for run PASS and
which are diagnostic only; replay must derive each predicate from bytes before accepting
the authored process/status fields.

## New findings

No separate Critical or Important contradiction was introduced by round 3. The remaining
defects above are incomplete dispositions of I3 and I13 rather than new regressions.
