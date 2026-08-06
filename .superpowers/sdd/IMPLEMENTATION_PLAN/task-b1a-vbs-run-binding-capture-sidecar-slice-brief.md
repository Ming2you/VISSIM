# B1a slice 3B: VBS run binding and atomic capture evidence

## Purpose and boundary

Implement the required-mode VBS half from immutable run binding through one complete
raw state/capture-evidence transaction. Read
`task-b1a-run-live-trust-brief.md` first; its exact path, source, state, timing, and
sidecar contracts govern. Reuse the approved Slice 1 run-manifest APIs, approved Slice
3A child environment, the existing verified one-scan VBS capture, and the pinned
`scripts/read_monotonic_clock.py` helper.

This slice does not call projection-only, change normal controller candidate logic,
write the combined projection timing receipt, build post-run v2.2/replay, or implement
B1b. A state plus capture sidecar is necessary but not sufficient for a successful
required attempt. Live COM and p95 remain `NOT_EVALUATED`.

## Required startup binding

In required mode, VBS reads and validates before any state publication:

- `RW_RUN_ID`, `RW_RUN_MANIFEST_PATH`, `RW_RUN_MANIFEST_SHA256`,
  `RW_B1A_REQUIRED=1`, `RW_QUALIFICATION_MODE=live_required`, and `RW_PYTHON`;
- the canonical existing immutable manifest and its exact file hash;
- manifest `run_id`, `qualification`, allowed times, approved topology, pinned
  `state_manifest_builder`, `monotonic_clock_helper`, and supported-version policy.

Delegate canonical JSON, path, hash, approval replay, and manifest validation to the
pinned Python interfaces. VBS must fail closed before opening a state output when any
binding is missing, malformed, stale, unsupported, outside the workspace, or disagrees.
Legacy mode remains behavior-compatible and cannot emit required PASS evidence.

Every required state root has `run_provenance` with exactly matching `run_id`, canonical
workspace-relative `manifest_path`, and lowercase `manifest_sha256`. Add no trust,
version, timing, or sample fields to `vehicle_records`; its exact existing envelope and
six-field record schema remain unchanged.

## Atomic state transaction

For every permitted decision or audit-anchor capture:

1. Confirm `sim_sec` is one of the immutable manifest's exact JSON-double
   `allowed_capture_times` before scanning.
2. Call the pinned monotonic helper synchronously immediately before the first
   `Vehicles.Count` read. Require exactly one ASCII line
   `python_perf_counter_ns=<positive decimal integer>\n`, empty stderr, exit zero,
   bounded completion, and the manifest-bound Python/helper bytes.
3. Run the already approved single paused No/Lane/Pos/Speed capture without an
   intervening simulation step. Retain bounded raw values needed by evidence in
   addition to the unchanged normalized records.
4. Serialize the state to a same-directory unique temp, close/flush it, reject an
   existing final, and atomically rename without delete/replace. Strict Python parsing
   and run binding must accept the exact final bytes.
5. Call the same pinned monotonic helper after atomic state publication and before
   capture-sidecar serialization. Require `end_ns > start_ns`.
6. Atomically create the exact capture sidecar. Check termination after state and
   sidecar publication boundaries. A later slice may leave a valid orphan state on a
   subsequent failure, but no incomplete pair may qualify.

Required capture failure before state publication emits neither final state nor PASS
sidecar. Sidecar-production failure may retain the already immutable state for later
FAIL inventory but emits no PASS sidecar. Never overwrite a prior final file. Clean
unique temporary request/output files without deleting immutable evidence.

`Timer`, `Now`, file mtimes, and wall-clock subtraction cannot author either timing
endpoint or elapsed value. They may be used only for a bounded subprocess timeout if
clearly isolated from evidence values.

## Capture sidecar contract

Use the pinned `state_manifest_builder` producer role for the controller-independent
capture request/validation/publication entry point; do not add an unpinned helper
script. Its production API must create once, strict-reload, and export a reusable
validator for later post-run replay.

Sidecar name is `<state-stem>.vehicle_capture_v2_1.json`, UTF-8 without BOM and one
final LF. Top-level keys are exactly, in order:

`schema_version/run_id/sim_sec/qualification/run_manifest_path/run_manifest_sha256/state_path/vissim_version_raw/counts/capture_timer/raw_attribute_samples/semantic_sha256`.

- `schema_version` is `vehicle-capture-evidence-v2.1`.
- `sim_sec` is a JSON double and is allowed by the immutable manifest.
- `qualification` exactly copies the manifest object.
- manifest and state paths are canonical workspace-relative forward-slash paths.
- `counts` is exactly
  `collection_count_before/collection_count_after/record_count`; all are
  nonnegative JSON integers, equal each other, and equal the state envelope/records.
- `capture_timer` is exactly `clock/start_ns/end_ns/elapsed_sec`; clock is
  `python_perf_counter_ns`, endpoints are positive JSON integers with end greater than
  start, and elapsed is the canonical `(end_ns-start_ns)/1e9` value recomputed by every
  validator.
- `vissim_version_raw` is the exact nonempty bounded string read only from
  `Vissim.AttValue("VERSION")`; no authored support boolean is allowed.
- semantic hash is shared canonical JSON v1 over every prior field.

Each raw sample has the established exact fields
`com_key/no_value/lane_raw/parsed_link_no/parsed_lane_no/position_value/speed_value`.
It binds the actual called four-table row and the exact normalized state record.
Samples are unique and ascending by `no_value`, at most 64. Select deterministically
from the complete raw capture using the approval-bound A1 topology: first the lowest
vehicle on an occupied connector lane, then the lowest vehicle on an occupied road
object with at least two lanes, then the lowest remaining vehicle IDs. One vehicle may
satisfy only its single position in the unique list. Zero vehicles yields an empty
sample list; missing connector or multi-lane occupancy is valid but later live coverage
is `NOT_EVALUATED`. Malformed raw rows, ordering, duplicates, unknown lanes, sample/state
disagreement, or oversize input fail.

## Tests and evidence

Add static and executable no-COM tests on the actual called path:

- required environment and manifest/hash/run/time mutations fail before state open;
- legacy output remains compatible and cannot claim required evidence;
- state temp is same-directory/create-once, final is never replaced, invalid UTF-8/BOM
  or malformed state cannot produce a sidecar, and sidecar follows final state;
- helper framing mutations: missing/final extra newline, stderr, extra stdout, nonzero,
  timeout, nonpositive/overflow, reversed/equal endpoints, wrong Python/helper bytes;
- exact empty/nonempty `vehicle_records` keys remain unchanged;
- capture sidecar exact-key/type/hash/count/path/run/time mutation matrix, stale PASS
  replacement behavior where specified, huge integers, nonfinite values, path escape,
  reparse/case/non-ASCII paths, and create-once concurrency;
- deterministic 64-sample selection with connector and multi-lane priority, duplicate
  candidates, absent target occupancy, zero vehicles, and 20,000-record bounded input;
- executable fake-COM trace proves the production `WriteStateJson -> ScanVehicleState ->
  ReadVerifiedVehicleTables -> atomic state -> capture producer` path and rejects dead
  decoy writers/parsers;
- no test starts VISSIM. `cscript` compile/helper tests may run outside the sandbox when
  Windows Script Host settings access is denied.

Run VBS capture, run-manifest/watchdog, physical projection/reference, compiler/signal,
and adapter regressions. Record exact counts in
`task-b1a-vbs-run-binding-capture-sidecar-slice-report.md`. Final status is pending
independent review; live COM, combined timing/p95, post-run, replay, and B1b stay
`NOT_EVALUATED`.
