# A1 directed lane-route graph brief

## Purpose

Build the deterministic, lane-level physical route graph used by every later stock,
projection, movement, and action gate. This is production evidence, not a diagnostic
link-level BFS.

## Inputs and outputs

- Input network: `network/real_world_gaepo_modi/modi_eval_rw_control.inpx`.
- Reuse exact connector/head parsing from `plant/src/vissim_strict/compiler.py` where
  practical; do not maintain a conflicting second interpretation.
- Implement `scripts/build_vissim_lane_graph.py` as the canonical graph compiler.
- Implement `scripts/resolve_lane_routes.py` as the route proof compiler/library. The
  legacy `scripts/audit_static_routes.py` may call the new library or remain a thin
  compatibility wrapper, but production logic must not depend on its hop-count/set BFS.
- Atomically write `outputs/vissim_lane_graph_v2_1.json` and
  `outputs/lane_route_proofs_v2_1.json` from explicit CLI arguments.

## Directed graph contract

- A node is an exact VISSIM lane object, including connector lanes, with stable ID
  `lane:<link_no>:<lane_no>`.
- For each connector lane, emit exactly one directed source-lane -> connector-lane edge
  and one connector-lane -> destination-lane edge from the connector's INPX lane range.
- Preserve link/connector lengths, positions, lane counts, source/destination coordinates,
  and the exact connector lane mapping. Never add a reverse edge unless INPX contains a
  separate reverse connector.
- Preserve signal-head stopline `(SC, SG, head, link, lane, pos)` references from the
  canonical compiler.
- Canonical sort keys are numeric object ID, lane number, position, and route ID. XML/input
  iteration order must never be a tie-breaker.

## Static route contract

- Parse every active `vehicleRoutingDecisionStatic` and `vehicleRouteStatic`, including
  decision link/position, destination link/position, explicit `linkSeq`, name/ID, and
  time-dependent `relFlow` values without losing their source representation.
- Resolve executable lane paths in the forward direction through the explicit route
  sequence. Respect positions on the current link, connector source positions, lane
  ranges, and destination position. Do not use an arbitrary hop cap.
- Report all physically valid lane paths. If multiple valid paths share a terminal, retain
  them with normalized flow/path shares; do not select the smallest ID. An unresolved or
  reverse-only route is a hard production failure.
- For each proof preserve physical path length, first downstream stopline or terminal,
  traversed lane/connector edges, and raw route evidence.
- Normalize active route flow within each decision/time support so shares sum to
  `1 +/- 1e-9`; reject invalid/negative/non-finite `relFlow`.
- Compass/tangent geometry is reporting metadata only and must not define stock identity.

## Artifact contract

Both artifacts require: schema version, input hashes, command version/hash, status,
reasons, sample dimensions, units, downstream consumers, deterministic semantic SHA-256,
and atomic writes. Missing evidence is `FAIL` or `NOT_EVALUATED`, never PASS.

Production gates:

- unresolved routes 0;
- reverse synthetic edges 0;
- executable connector path coverage 100%;
- normalized flow share error <= `1e-9`;
- ten shuffled input-order compiles produce one identical semantic hash.

## Tests

- Unit fixtures for multi-lane connector ranges, position ordering, an attempted reverse
  traversal, two legitimate paths to one terminal, invalid relFlow, and a route whose
  next connector is upstream of the current position.
- Real-network test asserts all routes resolve, all graph connector lanes have exact two
  directed edges, coverage is 100%, and ten deterministic compiles have one hash.
- Preserve the user-corrected SC12 mappings: connector 10241 lanes 1/2 from EB lanes 1/2,
  10242 from EB lane 2; 10238 lanes 1/2 from WB lanes 1/2, 10240 from WB lane 2.

## Scope

Only the graph/route scripts and their tests. Do not implement physical stock capacities,
adapter projection, NumSim dynamics, controller actions, or calibration in this task.
