# B1a trusted runner/live-evidence integration brief review

## Verdict

**FAIL**

Findings: **Critical 3 / Important 8 / Minor 3**.

The proposed chain improves replay coverage but is not yet sufficient to establish a
live PASS. In particular, synthetic/fake-COM artifacts can still be presented as live,
and the mutable post-run JSON chain has no independent proof that the pinned producers
actually produced it. The current B1a `vehicle_records` envelope can remain unchanged,
but the brief needs an exact field-set invariant to make that boundary enforceable.

## Critical findings

### C1 - Mutable JSON still authenticates its own live/process facts

**Brief sections:** `Governing trust model`; `3. VBS run binding and raw capture
evidence`; `4. Post-run artifact trust and live evidence replay`.

Reopening states, sidecars, and `run-artifact-manifest-v2.1` and recomputing their
unkeyed hashes proves internal consistency, not that the pinned watchdog/VBS produced
the version, process-exit, run-window, COM-source, or timing facts. A caller can derive
a matching capture sidecar from state bytes, author supported-version and timing data,
author a matching run-artifact manifest, and then build a coherent replay summary
without changing the state or checked-in sources. Binding producer source hashes through
preflight is still only a claim about which code should have run; it does not
authenticate a particular output as an execution of that code. This contradicts the
stated protection against manually copied and coherently rehashed summary artifacts.

**Concrete amendment:** Define the external trust root for post-run facts. Either (a)
require a runner receipt authenticated by a key/attestation boundary not writable with
the run artifacts, covering a pre-run nonce, run-manifest hash, process identity/window,
qualification mode, and final run-artifact-manifest hash, and make replay verify it; or
(b) explicitly narrow the threat model to accidental stale/mixed files and require both
live gates to remain `NOT_EVALUATED` because local mutable files cannot independently
prove live execution. Source hashes and `command_version` must not substitute for this
receipt.

### C2 - Synthetic qualification is a label with no mandatory trust-path binding

**Brief sections:** `2. Immutable pre-run manifest`, final paragraph; `3. VBS run
binding and raw capture evidence`; `4. Post-run artifact trust and live evidence
replay`, final paragraph; `Required tests`.

The brief says fixtures carry an explicit synthetic marker but does not place a closed
qualification field in the exact pre-run schema, say who sets it, bind it through every
sidecar/manifest, or require fake-COM entry points to set it. The same pinned VBS path
can be exercised by executable fake COM and can emit a plausible version string and raw
samples. Omitting the marker then satisfies the stated live-only inputs. Therefore the
brief does not establish the requested invariant that synthetic fixtures can never
claim live PASS.

**Concrete amendment:** Add a mandatory closed `qualification.mode` to the immutable
run manifest (`live_required` or `synthetic_fixture`), set only by the trusted runner
entry point before launch. Bind the exact value and run-manifest hash into every state,
capture sidecar, projection/action reference, post-run manifest, and replay result.
Require all fake-COM/test launchers to construct only `synthetic_fixture` manifests.
Replay must return `NOT_EVALUATED` for a valid synthetic chain and FAIL for any
synthetic artifact in a `live_required` chain or any missing/mixed marker. Add a mutation
test that removes/changes the marker and coherently rehashes all mutable descendants;
it must not PASS. If C1 is solved with a receipt, the receipt must also cover this mode.

### C3 - The live timing gate has no realizable, replayable measurement protocol

**Brief sections:** `3. VBS run binding and raw capture evidence`, sidecar publication;
`4. Post-run artifact trust and live evidence replay`, timing bullet; `Required tests`.

The per-state capture sidecar records only capture start/end, while the claimed sample
spans VBS COM capture, state serialization, a separate Python strict parse/project, and
atomic projection-sidecar write. The brief does not identify one clock, the process
that starts/stops it, the raw timing record, or the minimum sample count. Offline replay
can measure a new parse/project but cannot reconstruct historical end-to-end live
latency. A timing document also cannot include the completed atomic write of itself.
With no minimum cardinality, even one authored sample can produce a p95 PASS.

**Concrete amendment:** Specify one production measurement protocol: VBS starts a
monotonic elapsed timer immediately before the first scalar COM read, waits for the
adapter to finish strict parse/public projection and atomically publish the projection
sidecar/action reference, then stops the timer and atomically writes a separate timing
receipt. Define clock source, midnight/wrap handling, exact endpoints, failure behavior,
one-to-one `(run_id, sim_sec)` binding, and a minimum live sample count. The post-run
manifest must hash the timing receipts; replay recomputes nearest-rank p95 only from
those receipts. Synthetic 20,000-record size/complexity tests remain a separate
non-live gate and cannot populate the live p95 gate.

## Important findings

### I1 - Immutable creation conflicts with stale-output replacement

**Brief sections:** `1. Close malformed-input stale-output paths`; `2. Immutable
pre-run manifest`.

Section 1 requires every manifest invocation to replace old output with FAIL, while
section 2 makes the pre-run manifest immutable for the whole run and reuses its validator
online/offline. Replacing a PASS run manifest after launch changes the hash embedded in
already published states; allowing a second producer invocation also creates a race.

**Concrete amendment:** Give `run-manifest-v2.1` create-once semantics distinct from
derived audit manifests. Creation uses an exclusive no-clobber publish into a unique run
directory; an existing byte-identical manifest may be validated/reused, but an existing
different file fails without modification. `--validate-only` never writes. Producer
failure before launch writes a separate deterministic creation-result/diagnostic file,
not over the immutable manifest. Keep stale-PASS replacement for approval, state
manifest, replay, and audit outputs.

### I2 - A run is not defined relative to watchdog retries or concurrent names

**Brief sections:** `2. Immutable pre-run manifest`; `4. Post-run artifact trust and
live evidence replay`.

The current watchdog creates one `$runId` before its retry loop
(`run_real_world_single_watchdog_distributed_core15n41.ps1:185,457`) and launches
multiple independent `cscript`/VISSIM processes with it. It also derives mutable paths
from `$OutDir` and `$Name`. The brief does not say whether each process attempt gets a
new run ID/manifest, how failed-attempt artifacts are excluded, or how two same-name
watchdogs are prevented from overwriting each other. This undermines unique
`(run_id,sim_sec)` evidence and process-window checks.

**Concrete amendment:** Define one `run_id` as exactly one `cscript` process attempt.
Create a fresh exclusive run directory and immutable manifest per retry, with a separate
campaign ID linking attempts. Never reuse state/action names across attempt directories.
Write and retain a FAIL post-run manifest for every failed/killed attempt; only one
successful attempt may be selected for live qualification. Add concurrent same-name
and retry-after-partial-output tests.

### I3 - Three changed schemas are not specified or versioned exactly

**Brief sections:** `2. Immutable pre-run manifest`; `4. Post-run artifact trust and
live evidence replay`.

No exact run-manifest field set or semantic-hash payload is given. The brief says to
extend `run-artifact-manifest-v2.1` with new fields and replace
`projection-live-evidence-v2.1` with raw-manifest references, although current consumers
use exact field sets. Reusing `v2.1` for incompatible shapes makes producer/consumer
behavior and hash scopes ambiguous and invites permissive validation. The current
`validate_run_manifest` is deliberately permissive about extra fields and optional
status/reasons (`build_state_manifest_v2_1.py:296-338`), so the proposed source bindings
would not automatically become mandatory.

**Concrete amendment:** Publish exact JSON shapes, exact/optional field sets, closed
enums, cardinalities, path bases, and canonical semantic-hash payloads for all three
artifacts. Use new schema identifiers for incompatible shapes (for example
`run-artifact-manifest-v2.2` and `projection-live-replay-v2.2`) or define one explicit
versioned extension object accepted by all consumers. Make the shared run-manifest
validator reject missing and extra fields.

### I4 - State/companion publication is not a complete atomic transaction

**Brief sections:** `3. VBS run binding and raw capture evidence`; `4. Post-run artifact
trust and live evidence replay`.

The brief requires an atomic capture sidecar but only says the state is published first.
The current `Utf8LineWriter` writes directly to the final state path through
`ADODB.Stream.SaveToFile` (`run_real_world_stackelberg_controller.vbs:2901-2925`), so a
crash can leave a partial state. If sidecar publication then fails, a finalized state
remains. Existing same-name files are not addressed at the per-capture boundary.

**Concrete amendment:** Require state bytes to be written to a same-directory temporary
file, closed, strictly parsed/checked, and atomically renamed to an initially absent
unique destination. Only then may companions be finalized. Any later companion or
adapter failure must make the process/run manifest FAIL, and selection must require the
complete state/capture/projection/action/timing companion set. Use unique attempt paths
so Windows does not need a non-atomic delete-before-rename replacement. Test termination
at every publication boundary and prove no partial set can qualify.

### I5 - Windows path and environment behavior is underspecified

**Brief sections:** `2. Immutable pre-run manifest`; `3. VBS run binding and raw capture
evidence`; `Required tests`.

“Canonical manifest path” does not define drive-letter case, slash form, UNC/long-path
form, junction/reparse handling, or whether VBS must echo the exact environment string
or independently canonicalize it. The current runner allows `$OutDir` outside the
workspace, while state-manifest consumers require contained workspace paths. It mutates
process-wide environment variables and restores them only after a successful
`Start-Process` call (`...core15n41.ps1:474-506`), not in `finally`; an exception leaks
the required-mode identity into later launches.

**Concrete amendment:** In B1a-required mode require a unique non-reparse run directory
below the canonical workspace root. Define one Python-produced canonical
workspace-relative path for JSON and one absolute Windows path string passed through
the environment; validators resolve both and compare final contained paths using
Windows case-insensitive semantics. Wrap all environment changes, including
`RW_RUN_ID`, `RW_RUN_MANIFEST_PATH`, `RW_RUN_MANIFEST_SHA256`, and `RW_B1A_REQUIRED`, in
`try/finally`, restoring absent versus empty values exactly. Add non-ASCII, spaces,
mixed-case drive, slash, junction, launch-exception, and inherited-stale-env tests.

### I6 - Producer roster and execution bytes remain vulnerable to ambiguity/TOCTOU

**Brief sections:** `2. Immutable pre-run manifest`; `4. Post-run artifact trust and
live evidence replay`.

“Producer/preflight source bindings” and “builder/replayer bytes” do not enumerate the
required source roles. It is unclear whether the preflight must pin the run-manifest
producer, its shared validators, state-manifest builder, projection module, live replay
builder, and post-run manifest producer. Also, hashing the checked-in VBS/adapter and
then executing those paths leaves a hash-to-execution time-of-check/time-of-use gap.

**Concrete amendment:** Define a closed source-role map and require exact hashes for
every executable module and shared trust helper used by creation or replay. Materialize
same-byte run-local copies before manifest creation, hash them into the immutable
manifest, and execute/import those copies, or revalidate exact bytes immediately before
launch and again post-run with any mismatch forcing FAIL. Preflight regeneration order
must be explicit and acyclic: sources -> preflight -> approval -> run manifest -> raw
artifacts -> post-run manifest -> replay.

### I7 - Supported VISSIM version is not a reproducible policy

**Brief sections:** `3. VBS run binding and raw capture evidence`; `4. Post-run artifact
trust and live evidence replay`.

The brief requires the raw COM version and says replay recomputes whether it is supported,
but provides no COM attribute contract, normalization grammar, or closed allowlist.
Current VBS emits `SafeAtt(Vissim, "VERSION")` only to stdout
(`run_real_world_stackelberg_controller.vbs:206-214`). Different formatting, empty
fallbacks, or a fake-COM supported-looking string can yield inconsistent decisions.

**Concrete amendment:** Define the exact COM property read, raw string preservation,
strict parser, normalized version tuple, and checked-in closed supported-version policy
whose file/source hash is pinned by preflight and run manifest. Sidecars store only the
raw value; replay derives support from the pinned policy. Unknown, malformed, or empty
versions FAIL supplied live evidence; synthetic mode remains `NOT_EVALUATED` regardless
of version text.

### I8 - The unchanged B1a envelope is asserted but not made testable

**Brief sections:** `3. VBS run binding and raw capture evidence`; `Required tests`;
governing brief `Verified paused COM capture`.

The prose says the root-level `vehicle_records` envelope remains unchanged, but the new
tests do not require exact field-set equality and the raw sample/parser/timing additions
are not expressly forbidden inside it. This leaves room to alter the B1a contract while
implementing sidecar evidence.

**Concrete amendment:** State normatively that `vehicle_records` has exactly the fields
and record shape in `task-b1a-brief.md:72-99`, with no trust, sample, version, timing, or
qualification additions. New data may appear only in root `run_provenance` and separate
versioned sidecars. Add exact-key regression tests for empty and nonempty states and
online/offline fixtures. Preserve all existing B1a identities, lane grammar, numeric
rules, and projection hash behavior unchanged.

## Minor findings

### M1 - Required-mode CLI activation is not defined

**Brief sections:** `2. Immutable pre-run manifest`, final paragraph; `Required tests`.

The brief refers to `-Strict -RequireComplete`, but the named watchdog currently has
neither parameter (`...core15n41.ps1:8-38`) and has no topology-approval argument. It is
unclear which caller decides to set `RW_B1A_REQUIRED=1`, which makes legacy-preservation
tests non-deterministic.

**Concrete amendment:** Specify the exact watchdog and matrix CLI parameters, defaults,
and truth table for legacy, dry-run, strict incomplete, and B1a-required modes, including
the mandatory approval path and exit codes. Required mode must be explicit and must fail
before COM creation on any trust-input failure.

### M2 - Mtime rules are not portable trust evidence on Windows

**Brief section:** `4. Post-run artifact trust and live evidence replay`.

“Outside the declared process window tolerance” does not define the timestamp source,
tolerance derivation, filesystem behavior, or treatment of pre-run preserved inputs.
Mtime can be copied or adjusted and may produce both false FAIL and false confidence.

**Concrete amendment:** Treat mtime only as a supplemental diagnostic, define UTC
`LastWriteTime` comparison and a conservative documented tolerance, and classify each
artifact as pre-run, in-process, or post-exit before applying a window. Exact bytes,
run/attempt identities, companion closure, and the authenticated receipt from C1 must
determine trust.

### M3 - Bounds and closed reason vocabulary are not enumerated

**Brief sections:** `3. VBS run binding and raw capture evidence`; `4. Post-run artifact
trust and live evidence replay`; `5. Online/offline readiness interfaces`.

“Bounded” raw samples/action references and “closed” reason codes have no numeric limits,
selection algorithm, truncation behavior, or complete vocabulary. Different producers
can therefore hash different semantic content or hide required connector/multi-lane
coverage behind truncation.

**Concrete amendment:** Define numeric byte/count bounds, deterministic sample selection
and ordering, required aggregate coverage, oversize behavior, and the full reason-code
table with exact FAIL versus `NOT_EVALUATED` mapping. A valid synthetic chain is
`NOT_EVALUATED`; a missing marker, live/synthetic mismatch, unsupported live version,
or malformed supplied artifact is FAIL.
