# B1a slice 3A: watchdog attempt identity and required launch trust

## Purpose and precedence

Implement the watchdog half of the approved required-mode launch transaction. Before
any VISSIM COM process can be created, each watchdog invocation must own one campaign,
each retry must own one unique run attempt and directory, and that attempt must have an
independently valid immutable `run-manifest-v2.1` bound to the exact config and producer
bytes that will execute.

Read `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-brief.md` first. Its
normative closure, fix-round amendments, exact CLI/path/source rules, and duplicate
bindings govern. Reuse the reviewed public run-evidence APIs and
`scripts/build_run_manifest_v2_1.py`; do not create a PowerShell validator. Slice 1 and
Slice 2 are approved interfaces. This slice does not implement VBS capture companions,
projection timing receipts, post-run v2.2 artifacts, live replay, or B1b dynamics.
Live COM and p95 remain `NOT_EVALUATED`.

## Watchdog CLI and legacy boundary

Update `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1` with exact
parameters `[switch]$B1aRequired`, `[string]$TopologyApproval`, and the existing
`[string]$PreflightManifest`. Add a testable required-mode dry-run mechanism if needed
to prove pre-COM behavior, but dry-run must never create PASS run evidence.

- Defaults preserve the legacy non-B1a launch path and filenames.
- Required mode requires explicit approval and preflight paths and a pinned Python
  executable. It validates them before COM/cscript creation and fails nonzero on any
  missing, non-PASS, stale, mixed, oversized, escaping, reparse, source, topology, or
  version-policy input.
- Required-mode validation and run-manifest production are delegated to the reviewed
  Python producers. PowerShell may parse their small result framing but must not
  reimplement canonical JSON, hashes, approval replay, or schema acceptance.

## Campaign and attempt identity

- Create one fresh `campaign_id` per watchdog invocation. It links retries only.
- Create a fresh `run_id` for every cscript attempt. Never reuse one run ID across
  retries.
- Each attempt exclusively creates
  `<OutDir>/<campaign_id>/attempt_<NN>_<run_id>/` as an initially absent canonical,
  non-reparse descendant. Same-name/concurrent creation fails without sharing or
  clearing another attempt.
- All attempt outputs, decisions, logs, generated config copy, run manifest, manifest
  creation result, and future companion roots are inside that attempt directory. Never
  clear a shared decision directory in required mode. Failed/killed attempts remain
  intact for later FAIL inventory; retries use a new directory.
- At most one successful attempt can be selected by the watchdog. A failed attempt is
  never relabeled or reused as success.

## Pre-launch config and manifest

For each attempt, before launch:

1. Resolve every input with exact Windows spelling, containment, case, file type, and
   reparse checks. Required paths support spaces and non-ASCII.
2. Copy the exact generated VBS config bytes into the attempt directory using a
   complete temporary file and no-clobber final publication. Hash/byte-compare source
   and copy before launch; never use a stale shared copy.
3. Enumerate `allowed_capture_times` deterministically from the actual VBS schedule:
   every permitted decision and audit-anchor time, finite nonnegative decoded doubles,
   strictly increasing and unique. An empty array permits no state publication.
4. Build one exact structured request for `scripts/build_run_manifest_v2_1.py` covering
   workspace, attempt directory, run/campaign/attempt identities, qualification
   `live_required`, approval, preflight, all 12 closed producer roles, all eight
   configuration roles, exact simulation fields, allowed times, immutable manifest
   destination, and creation-result destination.
5. Require creation result PASS and strict validate-only reload of the final immutable
   manifest. Record the exact final manifest file SHA-256. A differing existing
   manifest never gets replaced.
6. Rehash all manifest-bound producer and configuration bytes immediately before
   cscript launch. Any mismatch fails before COM and keeps the attempt directory as
   failed evidence.

The executed generated config binding is the original configured input in the run
manifest; the attempt-local preserved copy must have byte-identical content/hash and is
the file actually passed to VBS. Preserve this duplicate relationship explicitly.

## Environment transaction and process launch

Required launch exports exactly the attempt's values through process environment:

- `RW_RUN_ID`
- `RW_RUN_MANIFEST_PATH`
- `RW_RUN_MANIFEST_SHA256`
- `RW_B1A_REQUIRED`
- the qualification-mode variable defined by the governing architecture

All required environment mutation, plus existing `RW_FORCE_STEPWISE`, audit anchors,
and Python values touched for launch, must be enclosed in one `try/finally`. Restore
each previous process value exactly, distinguishing absent (`null`) from present-empty
(`""`), even if path validation, `Start-Process`, argument construction, or launch
throws. Do not perform a restore only on the success path.

The cscript working directory and every VBS positional path in required mode point to
the attempt-local output/config roots. Launch uses the exact manifest-bound VBS and
adapter sources. A process is never started when preflight/approval/manifest/config or
source checks fail. After cscript exits or is killed, rehash every bound producer and
configuration source; mismatch marks the attempt failed and prevents selection. Full
post-run evidence is deferred to the later post-run slice, so do not author a required
PASS `run-artifact-manifest-v2.2` here.

## Matrix integration

Update `scripts/run_plant_fidelity_matrix.ps1` so strict/complete production runs pass
`-B1aRequired`, explicit topology approval, and explicit preflight to the watchdog.
Legacy/non-strict invocations remain legacy. Dry-run validates intended required paths,
argument propagation, and schedule/manifest request construction without creating a
live manifest, cscript, COM process, or PASS evidence.

Do not regenerate checked-in real PASS preflight evidence while the future post-run and
live-replay producer files are absent. The real repository may honestly remain preflight
FAIL and required live execution `NOT_EVALUATED` until those slices exist.

## Tests

Add focused PowerShell/static/behavior tests covering:

- unique campaign and per-attempt run IDs/directories across retries and concurrent
  same-name invocations; no shared clearing and failed-attempt preservation;
- required input rejection before any `Start-Process`/cscript/COM call;
- official request -> preflight/approval replay -> immutable run-manifest creation and
  validate-only reload with exact 12/8 role universe and duplicate bindings;
- generated config source/copy bytes, actual executed copy, pre/post source rehash, and
  mismatch fail-closed behavior;
- exact schedule expansion, anchors, sorted/unique/empty `allowed_capture_times`, and
  malformed/range cases;
- environment restore for absent versus present-empty values, spaces/non-ASCII paths,
  slash/case variants, junction/reparse escape, stale inherited values, request/launch
  exceptions, and normal exit;
- parser/dry-run propagation from matrix, with no PASS artifact/process creation;
- synthetic fixtures can use only `synthetic_fixture`; required mode cannot be faked
  into live PASS by unit launchers.

Use process-level tests where concurrency or environment ownership matters. Pin called
paths rather than accepting decoy/dead code. Run existing watchdog/matrix, B1a
run-manifest/core, A1/A2, VBS capture, adapter projection/reference, and compiler/signal
regressions. VISSIM itself runs one at a time; this slice should not start it.

## Report

Write
`.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-watchdog-attempt-launch-slice-report.md`
with changed files, exact attempt layout, CLI/request/environment contracts,
commands/counts/results, concurrency evidence, remaining producer/live dependencies,
and self-review. Return one SDD status and keep live gates honest.
