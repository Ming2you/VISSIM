# B1a preflight architecture review

## Verdict

**REVISE**

The brief has the right direction and is feasible after contract repair, but it is not
safe to implement as written. Nine critical requirements are contradictory or
underspecified enough to permit a false PASS or incompatible implementations. Eight
important issues leave performance, failure, and integration behavior open. Three minor
schema details should also be made explicit.

Counts: **Critical 9 / Important 8 / Minor 3**.

## Reviewed scope

- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-brief.md`
- `IMPLEMENTATION_PLAN.md`, especially A-2, B-1, the execution matrix, and the global
  machine-artifact contract
- `scripts/compile_physical_stock_topology.py` and its A2 tests
- `scripts/run_real_world_stackelberg_controller.vbs`, especially `WriteStateJson`,
  `ScanVehicleState`, `ReadVehicleLanePosSpeed`, `MultiValue`, `FirstInt`,
  `Utf8LineWriter`, and `Num`
- `evaluation/controllers/vissim_stackelberg_adapter.py`, especially
  `build_local_observation_summary`, `traffic_state_from_vissim`, action metadata, and
  CLI wiring
- `plant/src/vissim_strict/observation.py`, `schema.py`, and `topology.py`
- Existing state/projection checks in `scripts/audit_plant_fidelity.py` and adapter tests

## Critical findings

### C1. "Aligned arrays" does not define the COM identity check required for a trustworthy row

`GetMultiAttValues` returns a two-dimensional table containing a COM object key and an
attribute value. The current `MultiValue` helper discards the key and the current scan
zips `Lane`, `Pos`, and `Speed` by row number. The brief adds `No` and says the arrays
must be aligned, but does not require equality of rank, both-dimension bounds, row count,
or the first-column COM key at every row. Equal lengths and matching row positions are
not sufficient evidence. Four independently returned arrays could be permuted and still
produce well-formed but fictitious vehicle records.

Revise the contract to require one paused simulation instant; valid 2-D shapes; identical
bounds; identical, unique COM row keys in all four arrays; and a declared relationship
between the `No` attribute value and the COM key. Records must be joined or verified by
the COM key, not merely zipped by row index. Any mismatch must prevent state publication
and exit nonzero. The static test must inspect this key-level behavior, and live COM
evidence must confirm the actual table shape and relationship.

### C2. `(run_id, VehNo)` persistence is confused with per-snapshot uniqueness

The approved plan uses `(run_id,VehNo)` as vehicle identity. A vehicle legitimately
appears at several state times in the same run, so a manifest-wide rejection of duplicate
`(run_id,VehNo)` would reject nearly every real run. The brief says to reject duplicate
`(run_id,VehNo)` and asks for "duplicate VehNo in one run" to fail, without limiting that
rule to one state snapshot.

Define two separate keys:

- persistent vehicle identity: `(run_id, veh_no)`;
- observed assignment identity: `(run_id, sim_sec, veh_no)`.

Within one state, each `veh_no` must occur exactly once. Across different `sim_sec` values
in the same run, reuse is expected. The test matrix must include this allowed case, in
addition to same-state duplicate failure and cross-run reuse.

### C3. The stated mass identities double-count external records and do not define an independent total

The brief states both:

```text
records = unique assigned + explicit external
total_vehicles = records + explicit unobservable/external source records
```

This counts explicit external records once inside `records` and again in the total. It
also conflicts with the whole-network oracle premise: every vehicle returned by
`Vissim.Net.Vehicles` should be on an A2 in-network road/connector lane, including
`boundary_out` stocks. A queued vehicle outside the network is not a scanned vehicle and
cannot have a raw COM vehicle record of the same kind.

The brief also calls `total_vehicles`, record cardinality, and aggregates independent,
but current `total_vehicles` is incremented from the same `Lane` array rows. It is not an
independent observation. Require a separate scalar COM count (for example the collection
count, if confirmed by the supported VISSIM API), define exactly when it is sampled, and
compare it with the verified aligned row count. For B1a, the safest bounded identity is:

```text
com_vehicle_count = raw_record_count
raw_record_count = unique_assigned_count
unique_assigned_count = sum(stock_counts)
unobservable_count = 0
external_source_count = 0
```

If future source/origin queues are retained in the schema, define them as a separate
typed observation universe and do not include them in `vehicle_records` or count them
twice.

### C4. The state-record envelope and aggregate universe are not defined and conflict with the current masked `link_counts`

The phrase "emit `local_observation.vehicle_records` with schema" does not establish
whether that field is an array or an envelope containing `schema_version`, source
attributes, completeness, count, and records. It also does not say whether the existing
numeric `local_observation.schema_version=2` changes. The adapter and validator therefore
have no exact shared input contract.

More seriously, current `local_observation.link_counts` contains only
`RW_LOCAL_OBSERVABLE_LINKS`, including explicit zero-valued entries, while the requested
records cover every network vehicle. Reconstructing full-network counts from all records
cannot be identical to that masked object. `observed_vehicle_count` is likewise the sum
over the local mask, not all records.

Specify an exact nested schema and separate the universes. For example, retain legacy
masked aggregates under their existing names and add a canonical full-network
`vehicle_record_link_counts` (or explicitly define reconstruction as applying the same
mask and zero-key policy). State which count feeds each identity. Without this, a test can
compare two derived local subsets while silently omitting most COM vehicles.

### C5. Interval tolerance has no deterministic, non-overlapping boundary algorithm

"Half-open except the final endpoint within tolerance" does not define what happens at
an internal split within `position_tolerance_m`, whether values slightly above the lane
end are accepted, or how a value slightly below zero is handled. It also conflicts with
"positions outside the approved lane extent" always being rejected. Applying tolerance
to both adjacent intervals can make an internal point match two stocks; using nearest
interval would violate the brief.

Define normalization and lookup exactly. A safe rule is to validate finite values, reject
outside a precisely stated tolerated or strict lane extent, snap only the lane start and
final endpoint under stated inequalities, and otherwise use exact half-open binary search
so an internal split belongs to the downstream stock. Give expected assignments for
`split - 2tol`, `split - tol`, `split - tol/2`, `split`, `split + tol/2`, `split + tol`,
`end - tol`, `end`, and `end + tol`, including equality behavior. The current test list
does not settle these cases.

### C6. The permutation/hash requirement conflicts with A2 trust validation and exact input hashes

A2's `semantic_payload` includes the `stocks` list in list order. The compiler first sorts
that list, so A2 guarantees stable hashes for equivalent compiler inputs; a consumer may
not arbitrarily reorder a trusted topology artifact and still retain its stored semantic
hash. The B1a test requiring ten permutations of topology stock order to produce the same
projection hash conflicts with the requirement to recompute and match the A2
`semantic_sha256`.

Likewise, if the projection ledger's semantic hash covers an exact state-file byte hash,
permuting vehicle-record order changes that byte hash and therefore must change the
ledger hash. The brief asks for exact input hashes and an invariant semantic projection
hash without distinguishing these scopes.

Revise the tests and hash contract to distinguish:

- exact source-file SHA-256;
- normalized vehicle-record semantic SHA-256;
- trusted A2 topology semantic SHA-256;
- assignment/projection semantic SHA-256 and its exact payload.

Test equivalent A2 artifacts produced by permuted compiler inputs, not manually shuffled
trusted JSON. If raw record permutations should preserve an assignment hash, make that a
separate normalized hash; the containing ledger may still differ when bound to exact
source bytes.

### C7. `--topology` alone cannot prove that an artifact is the approved A2 topology

Checking `status=PASS`, empty reasons, and a self-consistent semantic hash proves internal
consistency, not approval. Any different topology can be given a newly computed matching
hash. The current state JSON has no A2 topology hash, and the proposed validator command
does not name a preflight/approval manifest containing the expected hash. "Bind every
projection artifact to that exact topology semantic hash" records what was used but does
not establish that it was the approved input.

Require an external trust anchor: the state manifest or run preflight must carry the
expected A2 semantic hash and exact topology file hash, and the validator/adapter must
match both before projection. Define the required input-hash names and where they come
from. Also require one topology hash across all states in the aggregate artifact and a
state/action reference to it. A self-declared topology must fail.

### C8. The required view-summary global identities are impossible for the actual A2 weights

A2 gives `boundary_out` stocks empty `control_owner_weights` with an explicit external
owner state. It also intentionally defines objective views that exclude mass:
`controller_default` excludes boundary stocks and `boundary_only` includes only those
stocks. `visible_to` and `roles` are overlapping views and may count a vehicle multiple
times. Therefore owner, objective, visibility, and role summaries cannot each "reproduce
the global count" as currently worded.

Define separate view identities consistent with A2:

- physical objectives (`physical_total`, `controller_with_boundary`) equal assigned mass;
- `controller_default + boundary_only` equals assigned mass stock by stock;
- control-owner weights sum to one only for controlled stocks, with explicit
  external/uncontrolled buckets closing the owner partition;
- role and visibility summaries are non-partitioning diagnostics and must not be summed
  as physical mass.

Tests must include a `boundary_out` stock, multi-owner weights, multiple viewers, and an
SC12 shared stock.

### C9. Existing adapter/auditor behavior can still certify the legacy aggregate split

`build_local_observation_summary` currently produces a legacy object named
`projection_diagnostics`. The action JSON exposes it at top level, and
`scripts/audit_plant_fidelity.py` can PASS that contract while allowing nonzero
unrepresented mass under a threshold and explained clipping. The B1a brief asks only for
adapter metadata exposure and an adapter test; it does not require changing this existing
verdict path. Consequently the old movement/storage split can remain the machine verdict
source even when a physical ledger exists, directly defeating B1a's purpose.

Bring the current auditor/consumer contract into B1a scope. Give the new evidence a
non-colliding field such as `physical_stock_projection`, mark legacy diagnostics
explicitly non-authoritative, and require all verdict consumers to prefer the physical
ledger and fail if it is missing/FAIL when records are present. Define whether the action
contains the full ledger or only its hash/status/path and summary. The adapter must abort
before controller evaluation on a physical projection or topology trust failure; a
controller fallback must not turn observation corruption into a successful action.

## Important findings

### I1. Per-state ledger location, manifest schema, and online/offline ownership are unspecified

The validator takes `state_manifest_v2_1.json`, but no schema is given for state entries,
their byte hashes, run preflight linkage, duplicate paths, or relative-path resolution.
The brief also says to emit one ledger per state while naming only one aggregate output.
Specify sidecar naming/location, whether ledgers are embedded or referenced, atomic write
behavior for all outputs, and which single projector implementation is called by both the
adapter and validator. Define how an online adapter ledger is matched to an offline
replay so two subtly different implementations cannot both claim authority.

### I2. The size/performance requirement is too weak for the current VBS writer

`Utf8LineWriter.WriteLine` repeatedly concatenates the complete BSTR buffer. Emitting one
line per vehicle through it is quadratic. Canonical sorting also requires deliberate
memory handling, and embedding full assignments in state, projection output, and action
metadata can multiply disk and parse cost.

Replace "where practical" with a normative linear or `O(N log N)` construction and
bounded-copy write requirement. Define a representative and maximum nonzero vehicle
count, maximum state/action/aggregate bytes, serialization and Python parse timing, and
the allowed share of the existing decision deadline. Record bytes and wall time in the
performance evidence. Prefer action hash/path/summary references over duplicating full
assignments in action JSON.

### I3. Numeric parsing and precision are not sufficient to preserve interval semantics

The current VBS path converts malformed `Pos`/`Speed` to zero and formats numbers with six
decimal places through locale-sensitive `FormatNumber`. B1a requires fail-closed parsing,
while A2 uses a `1e-6 m` position tolerance and can store boundaries at greater precision.
Rounding at the tolerance scale can change which side of a split a vehicle occupies.

Specify accepted COM numeric Variant types, invariant JSON number formatting, retained
precision, integer rules for `veh_no/link_no/lane_no`, and rejection of booleans,
overflow, empty strings, NaN, and infinity. Python's default JSON decoder accepts
nonstandard `NaN`/`Infinity`, so file-level tests must explicitly reject those tokens.

### I4. Topology validation needs structural invariants, not only envelope and hash checks

The A2 semantic hash does not include `status`, `reasons`, `input_hashes`,
`command_version`, `sample_dimensions`, `units`, `downstream_consumers`, or production
gates. The projection consumer should validate required global fields and recompute lane
indexes independently: unique stock IDs; canonical numeric link/lane keys; finite ordered
intervals; exact lane cover; no normalized-key collision; required roles/owner/visibility/
objective fields; valid weight types; and consistency with sample dimensions. Define
which A2 validator is reused or moved into shared code so tests do not validate with the
same unchecked assumptions as the projector.

### I5. The relationship to existing strict observation and `PlantState` schemas is unclear

`plant/src/vissim_strict/observation.py` currently accepts
`vissim-strict-raw-observation/v1` and projects per-cell truth, while `schema.PlantState`
uses the older strict topology and requires every physical stock to be referenced by one
of its owner categories. A2 stock IDs and views do not fit that schema directly.

State explicitly that B1a creates a separate immutable projection ledger and does not
construct or mutate the current `PlantState`/cell-truth projection. Name the public module
entry point, exception/result contract, and package exports. Later B1 work can perform an
explicit schema migration instead of accidentally mixing two topology hashes.

### I6. The required static VBS test can pass without proving real COM behavior

A source-text test can find four `GetMultiAttValues` strings, bounds checks, and a failure
branch in dead or unused code. Python synthetic tests bypass VBS lane parsing, Variant
typing, 2-D array bounds, row keys, locale formatting, UTF-8 output, and live connector
lane values. A zero-vehicle COM run also passes all cardinality identities vacuously.

Require captured live-COM contract evidence from the supported VISSIM version with a
nonzero population, at least one connector and multi-lane road, raw key/value samples for
all four attributes, and a runner-produced state parsed by the Python projector. Keep
that gate `NOT_EVALUATED` without VISSIM; static and synthetic tests must never promote it
to PASS. If automated live execution is unavailable, the implementation report must say
so and B1a remains non-promotable.

### I7. B1a must not claim completion of approved B-1 or occupy the mass-ledger verdict

Approved B-1 includes the substep transfer ledger, immutable transfer IDs, clipping
removal, and `TrafficState.total_physical_vehicles()`. B1a intentionally excludes all of
those. The execution matrix names `projection-v2.1` and `mass-ledger-v2.1`, while the
brief introduces an aggregate `projection-mass-v2.1` result.

Define the aggregate schema name without implying that `mass-ledger-v2.1` or B-1 is
complete. Its downstream status should be "B1a initial projection" only; B-2/B-3/B-4 and
promotion must remain blocked until the remaining B-1 transfer/substep identities pass.

### I8. FAIL/NOT_EVALUATED artifact and process-exit behavior needs a complete matrix

The brief says failed identities exit nonzero, missing live states are `NOT_EVALUATED`,
and malformed supplied evidence is FAIL, but does not define exit codes or whether a
complete deterministic artifact must still be written before exit. It also does not say
how mixed PASS/FAIL/NOT_EVALUATED manifests aggregate.

Require an atomically written aggregate artifact for every parseable invocation, with
per-state reasons and counts, followed by distinct documented exit behavior for PASS,
FAIL, and NOT_EVALUATED. Missing manifest/topology or malformed global inputs should
still fail closed and must not leave a stale prior PASS output in place.

## Minor findings

### M1. JSON escaping needs an explicit test for all control characters

Current `JsonEscape` handles only backslash and quote. The new schema should require
correct escaping of CR, LF, tab, backspace, form feed, and other U+0000..U+001F
characters in all emitted strings, while preserving UTF-8 without BOM. Add a
runner-level parse test, not only a Python serializer test.

### M2. `stopped` semantics and aggregate consistency are unstated

The current threshold is `speed < 1 kph`. Declare the threshold, strict/equal boundary,
and whether `stopped` is derived from the serialized speed or the unrounded COM speed.
Require reconstructed stopped totals (and, where retained, per-link stopped counts) to
match the raw records.

### M3. Field types, source-attribute shape, and reason vocabulary should be fixed

Define positive integral ranges for vehicle/link/lane numbers, exact units, the shape of
the source-attribute mapping (for example `veh_no -> No`), and machine-readable reason
codes. `projection_reason` should be a closed enum for successful assignments rather
than arbitrary prose, with human detail stored separately.

## Feasibility and safe boundary

After the critical contracts are repaired, B1a is technically feasible as a bounded
change: one verified paused COM table capture plus scalar count, a standalone strict A2
projector, thin fail-closed adapter exposure, and an offline manifest validator. It should
not instantiate the existing strict `PlantState`, alter NumSim queue/storage dynamics, or
claim substep conservation. The live-COM and performance gates must remain explicit
non-promotable evidence requirements rather than being inferred from static tests.
