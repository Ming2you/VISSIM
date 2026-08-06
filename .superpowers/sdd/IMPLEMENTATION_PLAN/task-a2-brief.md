# A2 one-stock physical topology brief

## Purpose

Compile the approved A1 lane graph and route proofs into the sole physical stock
identity used by projection and rollout. Ownership, visibility, and objective views
must reference these stocks without copying vehicle mass.

## Inputs and output

- A1 `vissim-lane-graph-v2.1` artifact and `lane-route-proofs-v2.1` artifact. Revalidate
  both schemas/status/semantic hashes before use.
- `outputs/link_player_assignment_20260805.json` is legacy ownership evidence only; its
  `link_owner` keys must never become state/stock IDs.
- `outputs/intersection_adjacency8_20260805.json` is visibility evidence.
- `outputs/urban_storage_capacity_20260805.json` supplies the current jam-density prior
  and named ramp capacity evidence; calibration promotion happens later.
- Implement `scripts/compile_physical_stock_topology.py` and focused tests.
- Atomic output: `outputs/physical_stock_topology_v2_1.json`, schema
  `physical-stock-topology-v2.1`.

## Stock identity and partition

- One stock is an exact `(link_no, lane_no, [start_m,end_m))` lane interval. Stable ID
  must encode all four values canonically; no stock is keyed by owner or movement.
- Split each lane at 0/parent length, connector entry/exit positions, signal heads,
  routing-decision/destination positions, and other A1 route branch/merge positions that
  affect ownership or movement. Coalesce duplicate points within an explicit tolerance.
- Every A1 lane covers `[0,length]` exactly once: no gap, overlap, zero/negative interval,
  duplicate ID, or orphan interval. Connector lane stock remains a physical stock.
- Preserve members, parent kind, interval length, upstream/downstream stock/edge IDs,
  control-owner weights, visibility mask, objective weights, route/provenance evidence,
  and capacity prior.

## Kind and capacity

- Reconstruct the current road-link partition independently: urban-owned 957,
  freeway-bound 22, boundary-out/exit 226, total 1,205, duplicate/missing 0.
- Keep A1's remaining road links and 771 connector links explicitly classified; never
  force them into the 1,205 legacy partition to make counts fit.
- Classify freeway/ramp/interface/urban/boundary-out/connector stocks from exact A1
  connectivity and current mapping evidence. Preserve ambiguity as a reason, not an
  arbitrary ID tie-break.
- Capacity prior for a one-lane interval is
  `length_km * jam_density_veh_km_lane`; preserve value, units, and source hash. Do not
  use a scalar ramp fallback when named per-ramp evidence exists.

## Ownership, visibility, and objective views

- `control_owner_weights` is a sorted mapping whose values sum to one for controlled
  stocks. If multiple legitimate downstream owners exist, use A1 route-flow shares;
  do not choose minimum ID. Uncontrolled/external stocks must have an explicit typed
  owner state, not an unexplained empty residual.
- `visible_to` is a sorted set derived from owner plus current adjacency/mapping. It is
  a view only. Summing stocks through any visibility/player iteration must deduplicate
  by stock ID and reproduce the global mass exactly.
- Provide binary named objective weights with explicit policies:
  `physical_total` includes every in-network stock; `controller_default` excludes
  boundary-out stocks; `controller_with_boundary` differs only by including them;
  `boundary_only` includes exactly boundary-out stocks. The physical state/flow trace is
  identical across objective modes; only weights differ.
- A shared lane such as SC12 lane 2 is one stock interval sequence with multiple route
  memberships, never one stock per movement.

## Artifact and gates

Require global artifact metadata, transitive command hashes, atomic write, deterministic
semantic SHA-256, and explicit units/downstream consumers.

PASS gates:

- lane-interval gap/overlap/missing/duplicate 0;
- legacy 957+22+226=1,205 partition exact;
- owner weights sum `1 +/- 1e-9` where applicable, unexplained owner 0;
- objective weights are binary and obey named include/exclude policy;
- global stock mass from any agent-mask iteration differs by `<=1e-9 veh` in synthetic
  weighted-state tests;
- ten shuffled A1/ownership/adjacency input orders produce one semantic hash.

## Required tests

- Synthetic serial, parallel, split, merge, multi-owner shared-route, and duplicate split
  fixtures; missing parent/owner/adjacency and tampered A1 hash fail closed.
- SC12 lane-2 through+left memberships share the same physical stock IDs.
- Boundary objective modes change only the scalar weighted objective by the exact
  boundary contribution; stock/edge traces remain byte-identical.
- Real network asserts all production gates and ten-shuffle determinism.

## Scope

Do not modify adapter state projection or NumSim dynamics in A2. This task produces and
validates topology only.
