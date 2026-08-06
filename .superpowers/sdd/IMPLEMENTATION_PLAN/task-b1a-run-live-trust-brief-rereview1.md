# B1a trusted runner/live-evidence brief fix-round-1 rereview

## Verdict

**FAIL**

Original findings: **ADDRESSED 13 / NOT_ADDRESSED 1**.

Original severity dispositions: **Critical 3/3 addressed; Important 7/8 addressed;
Minor 3/3 addressed**.

New in-scope defects: **Critical 0 / Important 2**.

Live VISSIM COM and live p95 remain **NOT_EVALUATED**.

## Disposition summary

| Finding | Disposition |
|---|---|
| C1 mutable JSON authenticates its own live/process facts | **ADDRESSED** |
| C2 synthetic qualification is not trust-path bound | **ADDRESSED** |
| C3 live timing protocol is not realizable/replayable | **ADDRESSED** |
| I1 immutable creation conflicts with stale replacement | **ADDRESSED** |
| I2 run identity is undefined across retries/concurrency | **ADDRESSED** |
| I3 changed schemas are not specified/versioned exactly | **NOT_ADDRESSED** |
| I4 state/companion publication is not an atomic transaction | **ADDRESSED** |
| I5 Windows path/environment behavior is underspecified | **ADDRESSED** |
| I6 producer roster and execution-byte TOCTOU are ambiguous | **ADDRESSED** |
| I7 supported VISSIM version policy is not reproducible | **ADDRESSED** |
| I8 unchanged B1a envelope is not testable | **ADDRESSED** |
| M1 required-mode CLI activation is undefined | **ADDRESSED** |
| M2 mtime is treated as Windows trust evidence | **ADDRESSED** |
| M3 bounds and reason vocabulary are not enumerated | **ADDRESSED** |

## Original findings

### C1 - ADDRESSED

The normative closure now states the intended non-cryptographic local reproducibility
boundary explicitly (`Verdict meaning and trust boundary`, lines 20-32). It does not
claim protection against a workspace owner rewriting the complete producer/preflight/raw
campaign, and it expressly says source hashes are not execution attestation. Within
that boundary, a replay summary cannot establish facts by authoring and rehashing them;
the v2.2 replay must reopen raw manifests and companions and recompute derived fields
(`Versioned post-run and replay schemas`, lines 137-151). No external signing system is
required by this B1a architecture.

This disposition depends on the stated boundary: rehashing only the replay/summary is
rejected, while coherent fabrication of the entire raw campaign is explicitly out of
scope.

### C2 - ADDRESSED

`Exact qualification and retry identity` (lines 34-55) makes qualification mandatory in
the exact immutable manifest, closes it to `live_required` or `synthetic_fixture`, and
restricts all fake-COM/unit launchers to synthetic mode. Capture evidence, timing,
post-run manifests, and replay carry or compare that value and the immutable manifest
hash (lines 105-109, 128-151). Valid synthetic evidence is `NOT_EVALUATED`; missing or
mixed mode is FAIL (lines 153-161). This prevents a conforming synthetic fixture from
claiming live PASS.

### C3 - ADDRESSED

`Exact timing protocol` (lines 118-135) now identifies the measuring process, clock,
start/stop boundaries, synchronous adapter step, separate post-measurement receipt,
one-to-one identity, historical-receipt replay, nearest-rank p95, and a minimum of 20
live samples. It also separates the 20,000-record synthetic gate. The two new timing
defects below concern the chosen clock and adapter boundary rather than the original
absence of a protocol.

### I1 - ADDRESSED

Lines 47-51 give the immutable run manifest exclusive no-clobber creation, byte-identical
validate-only reuse, no-write validation, and a separate creation-result artifact while
retaining stale-output replacement for mutable derived outputs.

### I2 - ADDRESSED

Lines 36-41 define one `run_id` per `cscript` attempt, a campaign ID for the retry group,
exclusive per-attempt directories, retained FAIL evidence, and at most one selected
success. This closes retry and same-name concurrency ambiguity.

### I3 - NOT_ADDRESSED

The amendment versions the incompatible outputs and gives exact top-level key lists,
but it does not finish the exact schemas requested by I3. In `run-manifest-v2.1`, the
shapes and required keys of `preflight`, `producer_sources`, `configuration`,
`allowed_capture_times`, and `supported_version_policy` are not specified, including
how the nominally optional capture-time list is represented despite being an exact
top-level key. In `run-artifact-manifest-v2.2`, `run_manifest`, `process`,
`artifact_roles`, and artifact-record shapes/cardinalities are incomplete. In
`projection-live-replay-v2.2`, the nested `input_hashes`, `producer`, `states`,
`performance`, and `live_gates` shapes are likewise absent. Neither v2.2 artifact has an
exact semantic-hash payload/canonicalization scope.

**Required amendment:** Define exact nested field sets, types, closed enums,
cardinalities, path bases, optional-value representation, and canonical semantic-hash
payload for all three schemas. Require shared validators to reject every extra or
missing nested key, not only top-level shape differences.

### I4 - ADDRESSED

`Exact state and companion transaction` (lines 92-116) requires same-directory
temporary state publication, close/check before atomic rename to an absent final path,
atomic capture publication, complete companion closure, FAIL on later producer failure,
unique attempt paths, and termination tests at every boundary.

### I5 - ADDRESSED

`Exact CLI and path contract` (lines 57-72) now constrains required-mode output below the
canonical non-reparse workspace, defines relative JSON versus absolute environment path
forms and Windows comparison semantics, and requires one `try/finally` that restores
absent versus empty environment values. The requested Windows path/launch tests are
listed.

### I6 - ADDRESSED

`Exact source and version policy` (lines 74-82) supplies a closed source-role roster,
pre-launch and post-exit byte revalidation with FAIL on mismatch, and an acyclic
production order. Under the expressly narrowed threat model, the two byte checks are a
sufficient local TOCTOU control; swapping and restoring every source/raw trust input is
the excluded full-campaign rewrite.

### I7 - ADDRESSED

Lines 84-90 define the exact COM property, preservation of the raw version string, a
pinned checked-in policy, accepted normalization, rejection behavior, replay-derived
support, removal of authored support booleans, and unconditional synthetic
`NOT_EVALUATED` treatment.

### I8 - ADDRESSED

Lines 92-96 normatively preserve the governing `vehicle_records` exact field set and
six-field record shape, prohibit all new trust/timing/sample fields there, and require
exact-key empty/nonempty tests. The existing B1a envelope remains unchanged.

### M1 - ADDRESSED

Lines 57-63 define the watchdog's `-B1aRequired` and `-TopologyApproval` parameters,
legacy defaults, strict-matrix activation, mandatory trust inputs, pre-COM failure, and
dry-run no-PASS behavior.

### M2 - ADDRESSED

Lines 139-144 classify artifact roles, make mtime a supplemental UTC diagnostic only,
and state that bytes, identities, and companion closure determine verdict. It is no
longer a trust anchor.

### M3 - ADDRESSED

Lines 111-116 and 153-161 define deterministic sample selection, byte/count bounds,
coverage behavior, oversize behavior, additional closed reason codes, and FAIL versus
`NOT_EVALUATED` mapping.

## New findings

### I9 - `Timer` cannot detect the multiple-wrap condition the protocol rejects

**Amended brief section:** `Exact timing protocol`, lines 118-135.

The receipt stores only VBScript `Timer` start/end seconds. Those two values cannot
distinguish a short interval from the same interval plus one or more complete days, so
the producer cannot implement “multiple-wrap ... publish no PASS timing receipt.” The
same clock is wall-clock based rather than monotonic, so a system-clock adjustment can
also be misclassified as a midnight wrap. Required-mode `SimPeriod` and `StallSec` are
not bounded below 24 hours. A long or clock-adjusted sample can therefore produce a
wrong historical elapsed value and potentially a false live p95 PASS.

**Concrete amendment:** Add an independent date/day or UTC timestamp pair to the raw
timing receipt and cross-check it against the post-run process window, or use a
monotonic counter exposed by a pinned helper. If retaining `Timer`, enforce a required
mode maximum per-decision duration below 24 hours, record start/end dates, distinguish
clock rollback from midnight, and fail any mismatch. Replay must recompute and compare
both the day span and `Timer` endpoints.

### I10 - The stop boundary includes controller work outside the named B1a metric

**Amended brief sections:** `Exact timing protocol`, lines 118-135; `Online/offline
readiness interfaces`, lines 274-282.

The protocol stops only when the adapter returns after producing an action reference.
The current production call waits for the full Stackelberg adapter action
(`run_real_world_stackelberg_controller.vbs:713-738`), which can import NumSim and
perform controller/candidate evaluation after projection. The brief elsewhere requires
run-manifest/projection validation before NumSim or controller evaluation, and the
governing B1a metric is capture + serialization + strict parse + public projection +
atomic projection-sidecar write. As written, the historical sample has an
implementation-dependent tail outside that scope and can falsely fail B1a because of
controller work that B1a explicitly does not implement or qualify.

**Concrete amendment:** Define a production projection-only adapter mode/process that
validates the run manifest, parses/projects, atomically publishes the physical sidecar
and bounded projection reference, and returns before NumSim import or controller
evaluation; stop the VBS timing there. Run controller evaluation afterward using the
already validated reference. Alternatively rename and govern the gate as full
end-to-end decision latency, but do not claim it is the narrower B1a projection metric.
