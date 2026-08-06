# B1a revised-brief architecture re-review

## Verdict

**REVISE**

The replacement brief resolves most of the original review and remains technically
feasible without implementing B1b. However, four original findings remain open and two
new load-bearing omissions remain. They affect the observation universe, boundary
acceptance, topology approval, manifest interoperability, lane parsing, and snapshot
identity. These must be fixed before implementation can safely begin.

Disposition counts:

- Original findings: **ADDRESSED 16 / OPEN 4**
- New findings: **OPEN 2**
- Total: **ADDRESSED 16 / OPEN 6**
- Open severity: **Critical 5 / Important 1 / Minor 0**

## Original finding dispositions

### Critical

| Finding | Disposition | Basis |
|---|---|---|
| C1 COM array alignment | **ADDRESSED** | The revised brief requires paused capture, two scalar count reads, valid 2-D shapes, identical bounds, equal rows, per-row first-column key equality, key uniqueness, and equality between the COM key and integral `No`. Row position alone is explicitly rejected. |
| C2 persistent versus snapshot vehicle identity | **ADDRESSED** | Persistent `(run_id,veh_no)` and snapshot `(run_id,sim_sec,veh_no)` identities are separated. Same-snapshot duplicates fail; recurrence at later times and reuse across runs are explicitly valid and tested. |
| C3 external/unobservable identities and independent total | **OPEN** | The double-counting equation is repaired and independent before/after `Vehicles.Count` reads are required. However, `unobservable_count` and `external_source_count` are absent from the exact `vehicle_records` envelope. The only existing similarly named state field is legacy `local_observation.unobservable_vehicle_count`, which the brief also requires to retain in its masked-link universe and which can legitimately be nonzero. The projector therefore has no unambiguous input for the new zero identities, and the required nonzero-unobservable failure test has no defined field to mutate. |
| C4 state envelope and aggregate universes | **ADDRESSED** | The nested envelope is exact, `local_observation.schema_version=2` is retained, legacy masked aggregates are distinguished from new full-network maps, and full-network count/stopped maps must be reconstructed from records. |
| C5 deterministic interval tolerance | **OPEN** | Internal split handling and outer endpoint inequalities are now exact. But the numeric contract says serialized positions are nonnegative while lookup accepts and snaps raw positions in `[-tol,0)`. A conforming numeric validator must reject those values before the lookup rule can accept them. The brief must choose whether small negative raw COM positions are valid tolerance inputs or invalid numeric values. |
| C6 deterministic hash scopes and permutation tests | **ADDRESSED** | Exact byte hashes, normalized record hashes, normalized projection hashes, and complete-ledger semantic hashes have distinct scopes. Trusted topology JSON may not be manually reordered; equivalent compiler-input permutations are tested instead. |
| C7 approved topology trust anchor | **OPEN** | The revised brief adds topology file/semantic hashes and an approving manifest hash, but the offline `approved_topology` contract does not unambiguously provide an approving-manifest path or require loading, validating, and recomputing that manifest's hash and its topology binding. Matching self-declared hashes among the state manifest and its entries is not an external approval anchor. The CLI still has only `--states` and `--topology`; the exact route to the approving manifest must be specified. |
| C8 view-summary identities | **ADDRESSED** | Physical objectives, complementary objective views, controlled-owner weights plus explicit residual buckets, and overlapping role/visibility diagnostics now have separate valid identities. Boundary-out, multi-owner, overlapping-view, and SC12 tests are required. |
| C9 legacy adapter/auditor authority | **ADDRESSED** | New evidence uses `physical_stock_projection`, action evidence is bounded, legacy diagnostics are explicitly non-authoritative, auditor/consumer changes are in scope, missing or bad physical evidence fails when records exist, and projection failure aborts before controller fallback. |

### Important

| Finding | Disposition | Basis |
|---|---|---|
| I1 sidecars, manifest schema, and online/offline ownership | **OPEN** | Sidecar naming, atomicity, the single public projector/writer, bounded action references, path checks, and online/offline parity are specified. The `state-manifest-v2.1` JSON shape is still only prose: exact top-level global-contract fields and exact state-entry key names for path, `run_id`, `sim_sec`, state hash, preflight path/hash, and sidecar path are not given. No existing producer contract is named. Validator fixtures could therefore define their own private shape and pass while a later runner/manifest builder is incompatible. |
| I2 state size and performance | **ADDRESSED** | Complexity, bounded-copy emission, 20,000-record qualification, byte ceilings, action-reference ceiling, asymptotic projection cost, p95 timing, budget share, and missing-live-timing status are specified. |
| I3 numeric parsing and precision | **ADDRESSED** | Variant/type failures no longer coerce to zero; identifiers, overflow, booleans, nonfinite tokens, invariant decimal formatting, significant digits, and Python nonstandard-token rejection are covered. The remaining negative-position contradiction is tracked under C5. |
| I4 topology structural validation | **ADDRESSED** | Global fields and independent structural checks cover IDs, normalized keys, intervals, lane cover, sample dimensions, tolerance, views, weights, units, and consumers while separating shared canonical/hash helpers from lookup checks. |
| I5 relationship to strict observation and `PlantState` | **ADDRESSED** | B1a is explicitly a separate immutable ledger and may not instantiate or mutate the existing raw-observation projector, legacy strict `PlantState`, or NumSim dynamics. A public pure module and typed result/exception boundary are required. |
| I6 static tests versus live COM evidence | **ADDRESSED** | Static and synthetic evidence cannot certify COM. A supported-version, nonzero live capture with connector, multi-lane road, raw four-table samples, scalar counts, UTF-8 runner state, public-projector parse, and zero residual is required; absence remains `NOT_EVALUATED`. |
| I7 B1a versus complete B-1/B1b | **ADDRESSED** | The brief explicitly does not emit `mass-ledger-v2.1`, does not unlock downstream tasks, and leaves transfer debit/credit, clipping removal, and `TrafficState.total_physical_vehicles()` to B1b. The aggregate is named `initial-projection-audit-v2.1`. |
| I8 FAIL/NOT_EVALUATED outputs and exits | **ADDRESSED** | Atomic replacement, stale-PASS prevention, mixed-status aggregation, minimal global FAIL artifacts, preserved per-state reasons, and exit codes `0/1/2` are defined. |

### Minor

| Finding | Disposition | Basis |
|---|---|---|
| M1 JSON control-character escaping | **ADDRESSED** | All JSON control characters, UTF-8 without BOM, invariant output, and runner-level/static coverage are required. |
| M2 stopped semantics | **ADDRESSED** | `speed_kph < 1.0` uses unrounded COM speed, equality is moving, and both full-network count and stopped maps must reconstruct exactly. |
| M3 field types, source mapping, and reason vocabulary | **ADDRESSED** | Identifier ranges, record fields, exact source-attribute mapping, assignment success enums, separate human detail, units implied by typed field names/global units, and a closed reason vocabulary are specified. |

## New open findings

### N-C1. Lane-string parsing still has no exact grammar or source-level contract

The revised brief requires `link_no` and `lane_no` but never defines how the VISSIM
`Lane` reference string is parsed. The current VBS implementation uses `FirstInt`, which
extracts only the leftmost integer and accepts surrounding garbage. A malformed-lane
test does not fix the accepted language unless the grammar is normative.

Define a full-string parser for the supported VISSIM reference representation, including
the exact delimiter and whitespace policy, and require exactly two positive 32-bit
integers with no prefix, suffix, extra component, sign, decimal, or alternate delimiter.
The live-COM gate must preserve representative road and connector raw `Lane` strings and
prove that the same called parser produces both IDs. Pin accepted and rejected examples
in VBS-level tests; Python-only parsed-record fixtures are insufficient.

### N-C2. `run_id` and simulation-time bindings are not validated end to end

The replacement dropped the earlier explicit nonempty `run_provenance.run_id`
requirement. It also does not require equality among root `sim_sec`,
`vehicle_records.paused_at_sim_sec`, the manifest entry's `(run_id,sim_sec)`, the
sidecar identity, and the actual paused VISSIM time passed to the capture. Hashes can all
be internally consistent while an assignment is attributed to the wrong or empty run
or time.

Require a nonempty canonical `run_id`, finite nonnegative simulation time, and exact
cross-checks among all state, envelope, manifest, sidecar, and online capture values
before projection. Include empty/whitespace run IDs and each time-source mismatch in the
fail-closed tests.

## Required brief repairs

1. Add explicit new-envelope fields or exact derivations for `unobservable_count` and
   `external_source_count`; forbid using the legacy masked
   `unobservable_vehicle_count` for the full-network identity.
2. Resolve whether raw positions in `[-tol,0)` are valid and serialized or are rejected;
   keep the numeric and interval rules consistent.
3. Add the approving manifest's exact path/schema/status/hash validation and verify that
   its content binds the supplied topology file and semantic hashes.
4. Publish an exact `state-manifest-v2.1` JSON contract, including inherited global
   artifact fields and exact state-entry field names.
5. Define and test the anchored VISSIM `Lane` string grammar in the actually called VBS
   path.
6. Require nonempty run identity and exact simulation-time equality across capture,
   state, manifest, and sidecar.

## Feasibility and B1b boundary

The revised scope remains feasible after these repairs. Its implementation boundary is
still clean: verified paused COM capture, initial per-vehicle A2 lookup, immutable
projection sidecars, bounded adapter references, and authoritative initial-projection
auditing. Updating the legacy verdict path does not require changing NumSim state or
dynamics.

Nothing in the revised brief requires substep opening/closing stocks, transfer IDs,
source debit/destination credit, accepted external flow, sink flow, receiving/sending
constraints, clipping removal, travel-time buffers, or
`TrafficState.total_physical_vehicles()`. Those remain B1b work. The B1a report and
aggregate must continue to state that downstream B tasks and promotion are blocked even
if every B1a gate passes.
