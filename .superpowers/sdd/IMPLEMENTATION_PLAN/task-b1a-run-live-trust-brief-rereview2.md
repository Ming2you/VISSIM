# B1a trusted runner/live-evidence brief fix-round-2 rereview

## Verdict

**FAIL**

Re-evaluated findings: **ADDRESSED 2 / NOT_ADDRESSED 1**.

| Finding | Disposition |
|---|---|
| I3 exact nested schemas and hash scopes | **NOT_ADDRESSED** |
| I9 monotonic cross-process timing | **ADDRESSED** |
| I10 projection-only boundary before controller work | **ADDRESSED** |

New in-scope defects: **Critical 0 / Important 3**.

Live VISSIM COM and live p95 remain **NOT_EVALUATED**.

## Finding dispositions

### I3 - NOT_ADDRESSED

Round 2 closes most top-level and nested field lists and now gives explicit full-document
semantic-hash scopes for both v2.2 artifacts. It still does not define one unambiguous
strict schema for all required cases:

- `run_artifact_set_semantic_sha256` is mandatory in replay `input_hashes`, but its exact
  canonical payload, sort order, and included file versus semantic hashes are not
  defined.
- `run-artifact-manifest-v2.2.process` is exact even for
  `launch_failure/watchdog_timeout`, but no type or sentinel/null representation is
  defined for a missing PID, process start, finish, or exit code. Different strict
  producers can emit incompatible artifacts while each follows the prose.
- `artifact_roles.phase` is closed only to three values but has no required role-to-phase
  mapping. `min_count/max_count` types and exact values are not defined for failed
  attempts, despite failed/killed attempts being required to retain FAIL manifests.
- The top-level `run_manifest` binding and the `artifacts` record whose role is
  `run_manifest` are not expressly required to be identical.
- Run-manifest simulation field types/ranges and the use of shared canonical JSON v1 for
  its semantic hash remain implicit rather than exact.

**Required amendment:** Define `run_artifact_set_semantic_sha256` as canonical JSON v1
over an exact sorted record list; provide exact JSON types and failure sentinels for
every process field; fix the phase and successful/failed cardinality values per role;
require equality of duplicate run-manifest bindings; and state exact simulation types,
ranges/enums, and canonical hash algorithm. All missing/extra/wrong-type values must
fail before semantic comparison.

### I9 - ADDRESSED

`Exact timing protocol` now forbids VBScript `Timer`, pins a helper and Python >=3.10 on
Windows, uses `time.perf_counter_ns()`, requires the shared system-wide clock ID, invokes
the helper synchronously at both historical boundaries, validates raw unsigned integer
output and failures, and has replay derive elapsed seconds from `start_ns/end_ns`.
Windows CPython's performance counter is comparable across the helper processes in one
attempt, so the prior midnight/multiple-wrap defect is removed.

This disposition applies to the combined projection timing receipt. The separate new
capture-sidecar contradiction is I11 below.

### I10 - ADDRESSED

Lines 151-160 define a production `--projection-only` subprocess that validates trust
before any NumSim import, performs only strict parse/public projection/sidecar/reference
publication, and exits before controller construction or candidate evaluation. VBS
stops the B1a clock at that return, then invokes the normal controller separately. The
normal path must revalidate and consume the exact reference before candidate or fallback
evaluation, so controller work no longer contaminates the B1a p95 scope.

The newly introduced reference artifact itself lacks an exact contract; that is I12,
not a reopening of the corrected timing boundary.

## New findings

### I11 - Capture timing conflicts with the two-call monotonic protocol

**Amended brief sections:** `Exact state and companion transaction`, lines 126-130;
`Exact timing protocol`, lines 139-170.

The exact capture sidecar still requires `capture_timer` with a clock ID and start/end
seconds and must be finalized before the projection-only adapter runs. The new timing
protocol forbids `Timer` and specifies helper calls before the first count and again only
after projection-only returns. Its second endpoint therefore does not exist when the
capture sidecar is finalized, and its units/field names are nanoseconds rather than the
sidecar's unspecified “seconds.” The two normative contracts cannot be implemented as
written without inventing an unmentioned third clock read or retaining the forbidden
timer.

**Concrete amendment:** Define a third pinned-helper read at the end of raw capture and
make `capture_timer` exactly `clock/start_ns/end_ns/elapsed_sec`, with the combined timing
receipt reusing the same `start_ns` and the later post-projection endpoint. Alternatively
remove capture end timing from that sidecar and bind only the combined receipt, but keep
one explicit source of truth. State the helper output framing and UTF-8/newline contract
for every call.

### I12 - The projection reference is trust-critical but has no schema or hash scope

**Amended brief sections:** `Exact timing protocol`, lines 151-170; `Versioned post-run
and replay schemas`, lines 172-220.

Round 2 introduces `physical_projection_reference_v2_1.json` as the only object passed
from projection-only execution into the normal controller. The brief requires an
existence/hash/schema check but never defines that schema, exact keys, semantic hash,
status/reasons, or required bindings to run manifest, state, topology, and physical
projection sidecar. The post-run manifest and replay bind only its file path/hash. This
leaves “revalidates and consumes that reference without rerunning or bypassing
projection” underspecified at the exact controller trust boundary.

**Concrete amendment:** Define the reference's exact versioned field set and canonical
hash scope, including qualification, run/time identity, run-manifest hash, state
path/file hash, topology hashes, projection-sidecar path/file/semantic hashes,
record/assigned/stock counts, residual summary, status, and closed reasons. Require both
normal adapter and replay to reopen the sidecar/state and recompute every bounded value;
extra/missing/mismatched fields fail before controller or fallback evaluation.

### I13 - The closed v2.2 artifact-role list drops existing required run evidence

**Amended brief sections:** `Versioned post-run and replay schemas`, lines 172-191;
governed `Post-run artifact trust and live evidence replay`, lines 304-318.

The new exact `artifact_roles` list omits current required outputs such as stdout/stderr
run logs, state/action CSVs, signal readback, and other existing simulation outputs.
The less-specific governed section requires the preserved generated config and all
existing required artifacts, but the normative closure's exact key list overrides it
and makes those roles invalid. In particular, replay loses raw `STAGE=SIM_DONE`/error
log evidence that can corroborate normal process completion, while the manifest's own
`process` object remains authored by the post-run producer.

**Concrete amendment:** Add closed v2.2 roles and cardinality/phase rules for every
existing required simulation output and stdout/stderr log, or explicitly version and
justify each retired artifact with a raw replacement carrying the same checkable facts.
Replay must reopen them and recompute process-completion/error predicates; the post-run
manifest's authored status/process fields cannot establish PASS by themselves.
