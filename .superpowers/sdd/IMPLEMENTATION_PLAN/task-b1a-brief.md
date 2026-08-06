# B1a verified per-vehicle physical-stock projection brief

## Purpose and completion boundary

Establish a fail-closed initial-state identity from one paused VISSIM vehicle collection
to the approved A2 physical stocks. B1a proves only initial projection. It does not
complete B-1, does not emit `mass-ledger-v2.1`, and does not unlock B-2/B-3/B-4 or
promotion; B1b must still implement substep transfer debit/credit, clipping removal,
and `TrafficState.total_physical_vehicles()`.

B1a creates a separate immutable projection ledger. It must not instantiate or mutate
the existing `vissim-strict-raw-observation/v1`, cell-truth projector, legacy strict
`PlantState`, or NumSim queue/storage dynamics.

## Identity and observation universes

- Persistent identity is `(run_id, veh_no)`. Snapshot assignment identity is
  `(run_id, sim_sec, veh_no)`.
- Within one snapshot every positive integral `veh_no` occurs exactly once. The same
  vehicle may and normally will recur at later `sim_sec` in the same run. Reuse across
  runs is also valid.
- `vehicle_records` contains only vehicles present in `Vissim.Net.Vehicles` on A2
  in-network road/connector lanes, including finite `boundary_out` stocks. External
  demand/source queues are a different future observation universe and are not raw
  vehicle records.
- B1a's whole-network oracle has `unobservable_count=0` and
  `external_source_count=0`. Any nonzero value is non-promotable FAIL; do not invent a
  balancing residual or count an external record twice.

Required identities for every nonempty or empty snapshot are:

```text
collection_count_before = collection_count_after = raw_record_count
raw_record_count = unique_snapshot_identity_count = unique_assigned_count
unique_assigned_count = sum(stock_counts)
unobservable_count = external_source_count = 0
```

The two collection counts are independent scalar COM reads. The two full-network
zero-count fields defined below are the only inputs to the B1a zero identities; never
substitute legacy masked `unobservable_vehicle_count`. `total_vehicles` in the state is
retained for compatibility but is no longer called independent; it must equal the
verified scalar count.

## Verified paused COM capture

Extend the existing one-pass scan in
`scripts/run_real_world_stackelberg_controller.vbs`; never add a second aggregation
pass. No VISSIM simulation method may run between the first scalar count, four table
reads, and second scalar count.

1. Read `Vissim.Net.Vehicles.Count` before the tables and read
   `Vissim.Simulation.AttValue("SimSec")` as `capture_sim_sec_before`.
2. Read `GetMultiAttValues("No")`, `("Lane")`, `("Pos")`, and `("Speed")`.
3. Read `Vissim.Net.Vehicles.Count` again and read
   `Vissim.Simulation.AttValue("SimSec")` as `capture_sim_sec_after`. Both time reads
   must equal the `simSec` argument used by `WriteStateJson`.
4. For nonempty tables require valid two-dimensional arrays, identical first- and
   second-dimension bounds, equal row count, and the expected key/value columns.
5. At every row require the first-column COM object key to be equal in all four tables,
   unique in the snapshot, and equal to the integral `No` attribute value. Join/verify
   by that key; row position alone is not identity evidence.
6. Empty collection handling must be explicit and must still prove both scalar counts
   are zero. Shape/mismatch/duplicate/key-relation failure prevents state publication,
   increments COM/observation failure evidence, and exits nonzero.

The state keeps `local_observation.schema_version=2` and the legacy masked aggregates.
Add this exact **root-level** `vehicle_records` envelope as a sibling of
`local_observation`, not as its child. This separation is normative: the new envelope is
the full-network universe and must not inherit the legacy masked namespace or policy.

```json
"vehicle_records": {
  "schema_version": "vissim-vehicle-records-v2.1",
  "complete": true,
  "paused_at_sim_sec": 900.0,
  "capture_sim_sec_before": 900.0,
  "capture_sim_sec_after": 900.0,
  "source_attributes": {
    "vehicle_number": "No", "lane": "Lane", "position": "Pos", "speed": "Speed"
  },
  "stopped_threshold_kph": 1.0,
  "collection_count_before": 0,
  "collection_count_after": 0,
  "record_count": 0,
  "unobservable_count": 0,
  "external_source_count": 0,
  "full_network_link_counts": {},
  "full_network_link_stopped_counts": {},
  "records": []
}
```

Each record has exactly `veh_no`, `link_no`, `lane_no`, `position_m`, `speed_kph`, and
`stopped`. Legacy `link_counts`, `observed_vehicle_count`, and related zero-key policy
remain the `RW_LOCAL_OBSERVABLE_LINKS` masked universe. Full-network identities use only
the new envelope. Reconstruct both full-network count/stopped maps from records and
match them exactly; `stopped` is derived from the unrounded COM speed with
`speed_kph < 1.0` (equality is moving).

Parse the raw `Lane` attribute in the actually called VBS path with this complete ASCII
grammar: `^[ \t]*([1-9][0-9]*)-([1-9][0-9]*)[ \t]*$`. The first capture is `link_no`,
the second is `lane_no`; the delimiter is one ASCII hyphen. Outer horizontal whitespace
is allowed and discarded. Prefix/suffix text, internal whitespace, signs, decimals,
extra components, another delimiter, zero, and 32-bit overflow fail. Pin accepted
`1-1`, `1220012103-2`, and ` 1220012103-2 ` plus rejected `1`, `1/2`, `1-2-3`,
`x1-2`, `1 - 2`, `+1-2`, `1.0-2`, and `0-1` in VBS-path tests. Live evidence stores
representative raw road and connector lane strings and the called parser's outputs.

All identifiers are positive 32-bit integral values. Position is a finite IEEE-754
double permitted down to `-tol` solely for the outer-start tolerance rule; speed is a
finite nonnegative double. Reject booleans, empty strings, overflow, position below
`-tol`, NaN, infinity, and malformed Variants; never coerce them to zero. Serialize
integers as integers and doubles with invariant decimal point and at least 15 significant
digits. JSON escaping
must handle quote, backslash, CR, LF, tab, backspace, form feed, and every U+0000..U+001F
control character; output is UTF-8 without BOM. Python loaders must reject nonstandard
`NaN`/`Infinity` tokens.

VBS emission must be O(N) or O(N log N), with bounded-copy streaming/chunks rather than
repeatedly appending the full BSTR. Raw record order may follow verified COM keys; Python
normalization sorts by integral `veh_no`.

## Approved topology trust and structural validation

The projector accepts only `physical-stock-topology-v2.1` with `status=PASS`, empty
`reasons`, recomputed matching `semantic_sha256`, and all global artifact fields. This
self-consistency is necessary but not an approval anchor.

Implement `scripts/approve_physical_stock_topology.py`. It consumes the exact PASS
`preflight-v3`, A1 graph/routes, and A2 topology, revalidates their hashes/contracts, and
atomically emits `outputs/topology_approval_v2_1.json`, schema
`topology-approval-v2.1`. Its exact command is:

```text
python -B scripts/approve_physical_stock_topology.py \
  --workspace-root . \
  --preflight outputs/preflight_manifest_v3.json \
  --graph outputs/vissim_lane_graph_v2_1.json \
  --routes outputs/lane_route_proofs_v2_1.json \
  --topology outputs/physical_stock_topology_v2_1.json \
  --out outputs/topology_approval_v2_1.json
```

The approval has this full shape; hash strings are populated, never placeholders, in a
real artifact:

```json
{
  "schema_version": "topology-approval-v2.1",
  "input_hashes": {
    "preflight_file_sha256": "...",
    "lane_graph_file_sha256": "...",
    "lane_graph_semantic_sha256": "...",
    "lane_route_proofs_file_sha256": "...",
    "lane_route_proofs_semantic_sha256": "...",
    "topology_file_sha256": "...",
    "topology_semantic_sha256": "..."
  },
  "command_version": {},
  "status": "PASS",
  "reasons": [],
  "sample_dimensions": {"stocks": 7275, "lanes": 2649},
  "units": {"position": "m", "capacity": "veh"},
  "downstream_consumers": ["state-manifest-v2.1", "projection-v2.1"],
  "workspace_root_relative_to_artifact": "..",
  "source_inputs": {
    "preflight": {"path": "outputs/preflight_manifest_v3.json", "file_sha256": "..."},
    "lane_graph": {"path": "outputs/vissim_lane_graph_v2_1.json", "file_sha256": "...", "semantic_sha256": "..."},
    "lane_route_proofs": {"path": "outputs/lane_route_proofs_v2_1.json", "file_sha256": "...", "semantic_sha256": "..."},
    "physical_stock_topology": {"path": "outputs/physical_stock_topology_v2_1.json", "file_sha256": "...", "semantic_sha256": "..."}
  },
  "approved_topology": {
    "topology_path": "outputs/physical_stock_topology_v2_1.json",
    "topology_file_sha256": "...",
    "topology_semantic_sha256": "..."
  },
  "semantic_sha256": "..."
}
```

`semantic_sha256` is canonical JSON SHA-256 over exactly
`schema_version/input_hashes/command_version/sample_dimensions/units/downstream_consumers/workspace_root_relative_to_artifact/source_inputs/approved_topology`.
The consumer separately requires `status=PASS` and empty reasons. All source paths
resolve below the canonical workspace root. Every parseable invocation atomically
replaces `--out`; validation failure writes a deterministic FAIL artifact then exits 1,
PASS exits 0, and an unusable output path exits 1 without claiming evidence. A stale
PASS cannot survive regeneration.

`state-manifest-v2.1.approved_topology` must contain those three values plus
`approving_manifest_path` and `approving_manifest_sha256`. The validator loads that
path, rejects path escape, recomputes its exact file and semantic hashes, requires its
global fields/status/reasons and validated preflight/A1/A2 inputs, then matches its
binding object to the separately supplied topology. Repeating self-declared hashes in
the state manifest is not approval.

Every state entry carries exact state-file SHA-256 and the same run manifest hash. The
CLI matches all anchors before projection. Online, the runner's
`run_provenance.manifest_path` and its exact hash must name the same approved topology;
the adapter aborts before controller evaluation if either hash differs or is absent in
B1a-required mode. One aggregate may contain only one topology identity.

Independently validate unique canonical stock IDs, positive integral link/lane keys,
finite ordered intervals, exact lane cover, no normalized-key collision, sample
dimensions, position tolerance, roles, owner state/weights, visibility, binary objective
weights, units, and required consumer metadata. Reuse shared A2 canonical/hash helpers,
but keep consumer structural checks independent of the projector lookup algorithm.

Required input-hash names are:

```text
topology_file_sha256, topology_semantic_sha256, approving_manifest_sha256,
state_file_sha256, vehicle_records_semantic_sha256
```

## Deterministic interval lookup

Build an immutable binary-search index keyed by numeric `(link_no,lane_no)`. Let
`tol = topology.policies.position_tolerance_m`.

- Reject nonfinite positions, `pos < -tol`, and `pos > lane_end + tol`.
- Snap `-tol <= pos < 0` to `0`; snap `lane_end < pos <= lane_end + tol` to
  `lane_end`. Equality at `-tol` and `lane_end + tol` is accepted; anything farther is
  rejected.
- Do not tolerance-expand or snap internal boundaries. Use exact half-open lookup
  `[start,end)` so an internal split point belongs only to the downstream stock.
- The exact final endpoint belongs only to the final stock.

Tests must pin `split-2tol`, `split-tol`, `split-tol/2`, `split`, `split+tol/2`,
`split+tol`, `end-tol`, `end`, `end+tol`, and values just outside the outer tolerance.
No nearest-stock, owner-ID, or minimum-ID fallback is allowed.

## Public projector and ledger

Implement a controller-independent public module under `plant/src/vissim_strict`, with
an exported pure entry point that accepts the validated topology, state envelope, exact
hash context, and returns an immutable result or a typed projection exception. It is the
sole projector called by both the online adapter and offline validator.

Emit one atomic sidecar beside each input state, named
`<state-stem>.physical_projection_v2_1.json`, schema `projection-v2.1`, containing:

```text
schema_version, input_hashes, command_version, status, reasons,
sample_dimensions, units, downstream_consumers, run_id, sim_sec,
vehicle_assignments, stock_counts, view_summaries, projection_diagnostics,
normalized_projection_sha256, semantic_sha256
```

Assignments are canonical by `(run_id,sim_sec,veh_no)` and contain the stock ID, source
link/lane/position, and closed success enum `exact_interval` or
`outer_endpoint_tolerance_snap`; human detail is separate. Diagnostics report every
identity term, same-snapshot duplicates, malformed/unknown/out-of-range counts,
aggregate map mismatches, per-link residuals, stock total, and global residual.

View rules are:

- `physical_total` and `controller_with_boundary` equal assigned mass.
- `controller_default + boundary_only` equals assigned mass stock by stock.
- Controlled owner weights sum to one; explicit external/uncontrolled owner buckets
  close the owner partition.
- Roles and visibility overlap and are non-partitioning diagnostics; never sum them as
  physical mass.

SC12 lane 2 with through+left memberships, multiple viewers, and multiple owner weights
still has one assignment and contributes one vehicle to global mass.

Hash scopes are distinct. Exact file hashes bind bytes. The normalized vehicle-record
hash sorts validated records and ignores source order. `normalized_projection_sha256`
hashes canonical assignments/counts plus the approved topology semantic hash.
`semantic_sha256` hashes the complete behavioral ledger including exact `input_hashes`,
so byte-reordered source files may have equal normalized hashes but different ledger
hashes. Test equivalent A2 artifacts produced from permuted compiler inputs; never
manually reorder a trusted A2 artifact while retaining its old hash.

## Online adapter and authoritative verdict path

Expose only a bounded reference in action/adapter evidence under the non-colliding key
`physical_stock_projection`: status, sidecar path, sidecar file/semantic hashes,
topology hashes, record/assigned/stock counts, and residual/failure summary. Never copy
all assignments into action JSON.

Legacy `projection_diagnostics` remains compatibility-only and must be marked
`authoritative_for_physical_mass=false`. Update `scripts/audit_plant_fidelity.py` and all
B1a verdict consumers: when a vehicle-record envelope is present, the physical sidecar
is authoritative, and missing/FAIL/hash-mismatched evidence is FAIL. Legacy clipping or
unrepresented thresholds cannot PASS B1a. The adapter must abort before candidate or
fallback controller evaluation on physical projection/topology failure; an action
fallback cannot convert observation corruption into success. States without the new
envelope remain `NOT_EVALUATED` for B1a, not PASS.

Online and offline replay call the same public projector and sidecar writer. For the
same topology/state bytes they must produce equal normalized projection and semantic
hashes.

## Manifest validator, statuses, and exits

Implement `scripts/validate_state_projection_v2_1.py`:

```text
python -B scripts/validate_state_projection_v2_1.py \
  --states outputs/state_manifest_v2_1.json \
  --topology outputs/physical_stock_topology_v2_1.json \
  --out outputs/initial_projection_audit_v2_1.json
```

Implement the sole producer `scripts/build_state_manifest_v2_1.py`. Its exact output
shape is below; the real artifact includes the shown global fields verbatim:

```json
{
  "schema_version": "state-manifest-v2.1",
  "input_hashes": {
    "approving_manifest_sha256": "...",
    "state_selection_file_sha256": "...",
    "state_selection_semantic_sha256": "...",
    "topology_file_sha256": "...",
    "topology_semantic_sha256": "...",
    "state_set_semantic_sha256": "..."
  },
  "command_version": {},
  "status": "PASS",
  "reasons": [],
  "sample_dimensions": {"states": 1},
  "units": {"sim_sec": "s"},
  "downstream_consumers": ["validate_state_projection_v2_1"],
  "base_dir": "..",
  "state_selection": {
    "path": "outputs/state_selection_v2_1.json",
    "file_sha256": "...",
    "semantic_sha256": "...",
    "campaign_id": "campaign-x",
    "expected_entry_count": 1
  },
  "approved_topology": {
    "approving_manifest_path": "outputs/topology_approval_v2_1.json",
    "approving_manifest_sha256": "...",
    "topology_path": "outputs/physical_stock_topology_v2_1.json",
    "topology_file_sha256": "...",
    "topology_semantic_sha256": "..."
  },
  "states": [{
    "state_path": "evaluation/runs/x/state_000900.json",
    "state_file_sha256": "...",
    "run_id": "run-13",
    "sim_sec": 900.0,
    "run_manifest_path": "evaluation/runs/x/run_manifest.json",
    "run_manifest_sha256": "...",
    "required_vehicle_records": true,
    "projection_sidecar_path": "evaluation/runs/x/state_000900.physical_projection_v2_1.json"
  }],
  "semantic_sha256": "..."
}
```

The producer command is:

```text
python -B scripts/build_state_manifest_v2_1.py \
  --workspace-root . \
  --approval outputs/topology_approval_v2_1.json \
  --topology outputs/physical_stock_topology_v2_1.json \
  --selection outputs/state_selection_v2_1.json \
  --out outputs/state_manifest_v2_1.json
```

Broad filesystem discovery is forbidden. The runner/campaign request builder emits the
closed input `state-selection-v2.1` before manifest construction, with the global
artifact fields, `status=PASS`, empty reasons, `campaign_id`,
`expected_entry_count`, and exactly this canonical entry list:

```json
"entries": [{
  "run_manifest_path": "evaluation/runs/x/run_manifest.json",
  "state_path": "evaluation/runs/x/state_000900.json",
  "run_id": "run-13",
  "sim_sec": 900.0,
  "required_vehicle_records": true
}]
```

Its `semantic_sha256` is canonical JSON SHA-256 over exactly
`schema_version/input_hashes/command_version/sample_dimensions/units/downstream_consumers/campaign_id/expected_entry_count/entries`,
with entries sorted by `(run_id,sim_sec,state_path)`. The producer and validator load
the selection path from the manifest binding, recompute its file and semantic hashes,
require schema/status/reasons, and match campaign ID, expected count, and every entry.
The manifest's selection binding and both selection hashes in `input_hashes` are
mandatory.

No glob, retry directory, archive, sidecar, or unlisted state may be inferred or added.
The producer requires list length=`expected_entry_count`, unique resolved state paths,
unique `(run_id,sim_sec)`, one exact immutable run manifest per entry, matching
run/time provenance, and existence of every listed state. Missing required entries are
FAIL; listed states lacking a required envelope remain listed and later FAIL validation,
never silently disappear. An explicitly empty selection is permitted only with
`expected_entry_count=0` and yields NOT_EVALUATED downstream.

`state_set_semantic_sha256` is canonical JSON SHA-256 over the list of
`state_path/state_file_sha256/run_id/sim_sec/run_manifest_path/run_manifest_sha256/required_vehicle_records/projection_sidecar_path`,
sorted by `(run_id,sim_sec,state_path)`. The state-manifest `semantic_sha256` is
canonical JSON SHA-256 over exactly
`schema_version/input_hashes/command_version/sample_dimensions/units/downstream_consumers/base_dir/state_selection/approved_topology/states`.
Every manifest state copies `required_vehicle_records` exactly. A true entry with a
missing/partial envelope is FAIL; a false entry without an envelope is NOT_EVALUATED.

`base_dir: ".."` is resolved once from the manifest directory and must equal the
canonical `--workspace-root`; this one root declaration may contain `..`. Every child
path is workspace-relative and must resolve below that root. Absolute child paths,
child `..` escape, duplicate resolved paths, and symlink/reparse escape fail.
The producer loads every state/run/approval/topology input and computes real hashes;
it never accepts caller-supplied hash values.

The aggregate schema is `initial-projection-audit-v2.1`, not a mass-ledger schema. The
validator requires this exact manifest shape, unique state paths, exact hashes, unique
`(run_id,sim_sec)`, approved topology, approving manifest, and sidecar paths. Duplicate
or escaping paths fail.

Every parseable invocation atomically replaces the output, including FAIL and
NOT_EVALUATED, so a stale PASS cannot survive. Missing/malformed global inputs produce a
minimal deterministic FAIL artifact when `--out` is usable. Aggregate status is FAIL if
any supplied state or global contract fails; otherwise NOT_EVALUATED if zero promotable
live states or any required live gate is missing; otherwise PASS. Exit codes are
`0=PASS`, `1=FAIL`, `2=NOT_EVALUATED`. Preserve every per-state reason/status.

## Required tests and live gates

- Synthetic roads/connectors and all interval boundary cases above.
- Same-snapshot duplicate failure; same vehicle at later sim time allowed; cross-run
  reuse allowed; scalar count/table shape/key relation/misalignment failure.
- `run_id` must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`. Root
  `run_provenance.run_id`, manifest entry, online run manifest, assignment, and sidecar
  must match exactly. The immutable online run manifest binds only run ID, approved
  topology, configuration, and optional allowed capture times; it never stores one
  mutable actual snapshot time. Root `sim_sec`, envelope `paused_at_sim_sec`, both
  capture-time reads, post-run state-manifest entry, assignment, and sidecar must be
  finite, nonnegative, and exactly equal as decoded doubles before projection.
  Empty/whitespace/invalid run IDs and every time-source mismatch fail closed.
- Malformed lane, unknown link/lane, invalid numeric tokens/types, aggregate count and
  stopped-map mismatch, total mismatch, nonzero unobservable, missing/partial records,
  topology envelope/structure/hash/approval tamper all fail closed.
- Boundary-out, multi-owner, overlapping roles/viewers, and SC12 shared-lane identities.
- Ten vehicle-record permutations: equal normalized record/projection hashes; exact
  ledger hash changes iff exact state-file hash changes. Ten equivalent compiler-input
  permutations yield approved-equivalent A2 semantic hashes and equal projection.
- Static VBS tests trace the actually called one-scan path, key-level table checks,
  scalar count bracketing, fail branch, numeric formatting, escaping, and envelope.
- Adapter tests prove fail-before-controller, bounded action reference, legacy
  non-authority, and online/offline projector parity. Auditor tests prove missing/FAIL
  physical evidence cannot be masked by legacy PASS.
- Run all focused tests and A1/A2, adapter, auditor, and runner regressions.

Static/synthetic tests cannot certify COM behavior. A supported-version live capture
must have nonzero population, at least one connector and one multi-lane road, raw
key/value samples for all four attributes, both scalar counts, runner-produced UTF-8
state parsed by the public projector, and zero identity residual. Without VISSIM this
gate is `NOT_EVALUATED`, and B1a is implemented but not promotable; a zero-vehicle live
run is insufficient.

Performance evidence records count, bytes, and wall time. Synthetic qualification uses
20,000 records: state envelope <=8 MiB, sidecar <=16 MiB, action reference <=32 KiB;
serialization is O(N) or O(N log N), Python parse+projection is O(N log S), and combined
capture/serialize/parse/project p95 must be <=3.0 s and <=10% of the 30 s decision
budget on the qualification host. Missing live timing stays NOT_EVALUATED.

## Reason codes, scope, and report

Use a closed reason vocabulary including `com_count_changed`, `invalid_table_shape`,
`com_row_key_mismatch`, `duplicate_vehicle_in_snapshot`, `invalid_numeric_value`,
`unknown_lane`, `position_out_of_range`, `aggregate_mismatch`, `state_total_mismatch`,
`state_stopped_mismatch`, `topology_trust_mismatch`, `topology_structure_invalid`,
`projection_mass_residual`, and `live_com_not_evaluated`.

Do not modify substep dynamics, travel-time buffers, boundary/ramp flow rules, signal
actions, calibration, SPSA, or scheduling. Do not weaken A1/A2 anchors.

Write `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-report.md` with changed files,
schemas, commands/results, bytes/timing, online/offline parity, exact live-COM state,
remaining NOT_EVALUATED gates, and self-review.
