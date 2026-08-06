# B1a brief repair round 2 re-review

## Verdict

**REVISE**

Three of the six prior OPEN items are now fully addressed. Three remain open because
the newly specified path rules make the approval/state inputs resolve to the wrong
locations, the topology approval artifact is still not an exact independently
replayable schema, and the run-level manifest is assigned an impossible per-snapshot
time identity. No B1b behavior has leaked into scope.

Counts: **ADDRESSED 3 / OPEN 3**. Open severity: **Critical 3 / Important 0**.

## Per-item disposition

### 1. Full-network zero fields

**ADDRESSED**

The exact `vehicle_records` envelope now contains typed `unobservable_count` and
`external_source_count` fields, both fixed to zero for B1a. The identities explicitly
name them as the only B1a zero-count inputs and prohibit substitution of legacy masked
`local_observation.unobservable_vehicle_count`. Nonzero-input failure remains in the
test matrix. This closes the former observation-universe ambiguity.

### 2. Negative-position consistency

**ADDRESSED**

The numeric contract now permits a finite raw position down to `-tol` solely for the
outer-start rule, rejects values below `-tol`, and retains the exact lookup inequalities:
`[-tol,0)` snaps to zero, while values above the final endpoint are accepted only through
`lane_end + tol`. Internal boundaries remain exact half-open intervals. The numeric and
lookup contracts no longer reject and accept the same input simultaneously.

Range rejection may be performed by the public projector, which has the validated A2
tolerance; VBS still must preserve the finite raw double without zero coercion. This
does not require adding topology-dependent dynamics to VBS.

### 3. Loaded external topology approval artifact/path/schema/hash/binding

**OPEN**

The revision correctly introduces a separate `topology-approval-v2.1` artifact, an
approval producer, exact topology file/semantic hashes, an `approving_manifest_path`,
an exact approval file hash, required loading/recomputation, and matching to the
separately supplied topology. Self-declared state-manifest hashes are explicitly
insufficient.

Two load-bearing gaps remain:

1. The state manifest's new path-resolution rule makes the shown approval path invalid.
   With the manifest at `outputs/state_manifest_v2_1.json`, `base_dir: "."`, and
   `approving_manifest_path: "outputs/topology_approval_v2_1.json"`, resolution relative
   to `manifest_directory + base_dir` produces
   `outputs/outputs/topology_approval_v2_1.json`. Because absolute paths and escaping
   `..` are forbidden, the exact example cannot name the actual approval artifact.
2. The approval artifact is not given an exact replayable input schema for the preflight,
   A1 graph, and A1 routes: their path field names, file-hash field names, semantic-hash
   field names, and the approval `semantic_sha256` payload are unspecified. The validator
   is told to revalidate those inputs but is not told how to locate or interpret them.
   The producer also lacks an exact invocation/exit contract, so a fixed-path stale PASS
   is not explicitly replaced by FAIL when approval regeneration fails.

Repair by publishing the full approval JSON shape and semantic payload, including paths
and hashes for every preflight/A1/A2 input; an exact command and PASS/FAIL exit/write
matrix; and one consistent path root shared with the state manifest.

### 4. Exact state-manifest producer/schema/path rules

**OPEN**

The sole producer, exact top-level/state-entry fields, hash computation ownership,
sidecar field, path de-duplication, symlink/reparse checks, and validator expectations are
now specified. However, the exact example and its normative resolution rule contradict
each other.

For the required output location `outputs/state_manifest_v2_1.json`, `base_dir: "."`
sets the path root to `outputs`. The shown paths then resolve incorrectly:

```text
outputs/topology_approval_v2_1.json -> outputs/outputs/topology_approval_v2_1.json
outputs/physical_stock_topology_v2_1.json -> outputs/outputs/physical_stock_topology_v2_1.json
evaluation/runs/x/state_000900.json -> outputs/evaluation/runs/x/state_000900.json
```

The brief says the real artifact includes the shown global fields verbatim, so an
implementation cannot silently change `base_dir`; the ban on absolute and escaping
paths prevents recovery. Set an unambiguous root, for example a canonical workspace root
represented by `base_dir: ".."` relative to `outputs`, then require all child paths to
remain under that resolved root. Alternatively make every example path relative to the
`outputs` directory and define how non-output state files are safely represented. Also
give the producer's exact CLI and ensure `input_hashes` is populated rather than left as
the literal empty object shown under an "exact/verbatim" contract.

### 5. Full `Lane` grammar in the called VBS path

**ADDRESSED**

The brief now defines an anchored ASCII grammar, exact delimiter and whitespace policy,
positive 32-bit captures, complete accepted/rejected examples, overflow rejection, and
called-VBS-path tests. Live evidence must retain representative raw road/connector
strings and the called parser's outputs. This prevents the current `FirstInt` behavior
from passing through prefix/suffix garbage or losing the lane number.

### 6. Run/simulation-time end-to-end binding

**OPEN**

The nonempty bounded `run_id` grammar and equality across root state provenance,
manifest entry, assignment, and sidecar are now explicit. Root `sim_sec`, envelope
pause time, before/after COM times, manifest entry, assignment, and sidecar are also
proper snapshot-level equality sources.

The added requirement that the **online run manifest** carry the same exact per-snapshot
`sim_sec` is not feasible for a normal run containing multiple states. The existing
`run_provenance.manifest_path` points to a pre-run, run-level immutable provenance
artifact. If that file is updated for each snapshot, its hash changes and invalidates
all earlier state references; if it contains one scalar `sim_sec`, only one snapshot can
match. The brief does not define a per-state table in an immutable predeclared manifest,
and actual capture times cannot safely be asserted before execution.

Keep the immutable online run manifest responsible for `run_id`, approved topology,
run configuration, and optionally expected/allowed capture times. Bind actual snapshot
time only among the root state, three vehicle-record time fields, post-run state-manifest
entry, assignment, and sidecar. If the run manifest is intended to carry a state table,
define an append-free/finalized artifact and do not use its changing hash as the online
pre-controller trust anchor.

## New contradiction check

The repair introduced no additional independent Critical or Important issue beyond the
three OPEN items above. The material new contradictions are contained in those items:

- workspace-relative example paths conflict with manifest-relative `base_dir: "."`;
- an immutable run-level manifest is required to equal every snapshot's actual time;
- the new approval producer is required for trust but lacks a complete replayable
  artifact/command/failure contract.

The distinction between a state with no new envelope (`NOT_EVALUATED`) and a present but
missing/partial envelope (`FAIL`) remains coherent. Hash scopes for state bytes,
normalized records/projection, and complete ledgers also remain coherent.

## Feasibility and B1b boundary

After the three repairs, B1a remains feasible as paused COM capture, strict initial A2
lookup, immutable sidecars, bounded adapter references, and initial-projection auditing.
The approval and state-manifest producers are provenance infrastructure, not substep
dynamics.

The brief still excludes opening/closing substep inventories, transfer IDs, source
debits, destination credits, accepted external flow, sink flow, receiving/sending
constraints, clipping removal, travel-time buffers, and
`TrafficState.total_physical_vehicles()`. It therefore does not accidentally complete
B1b and must continue to leave B-2/B-3/B-4 and promotion blocked.
