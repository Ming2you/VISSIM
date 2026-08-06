# Task A1 Independent Review

## Verdict

- **Spec compliance: FAIL**
- **Quality: FAIL (blocking)**
- **Approval: NOT APPROVED**
- **Findings:** Critical 3, Important 3, Minor 1 (total 7)

The current real-network fixture compiles to the reported 339 routes, all 12 supplied
tests pass, the SC12 mappings are locked correctly, and the search has no arbitrary hop
cap or BFS minimum-ID winner. Those positives do not close the production contract:
small targeted fixtures produce `PASS` artifacts while connector evidence is incomplete
or reversed, valid lane paths are omitted, physically impossible paths are admitted, a
`relFlow` attribute is missing, or the graph semantic hash does not match its payload.

## Findings

### Critical

#### C1. Connector degree, orientation, and coverage gates can PASS an incomplete or reversed exact-lane graph

**Files/lines:** `scripts/build_vissim_lane_graph.py:127-217`, especially
`scripts/build_vissim_lane_graph.py:323-353`; test blind spot at
`scripts/tests/test_vissim_lane_graph_real_network.py:50-63`.

The expected connector-lane universe is seeded from `lane_mapping`, not from the exact
connector lane nodes or the declared lane range. `connector_lane_count` is then taken
from `lane_count`, while `executable_count` subtracts only malformed entries that were
present in `lane_mapping`. A missing mapping is therefore absent from `degree` and is
never counted as malformed. The reverse-edge gate also only asks whether an entry
edge's source ID starts with the connector's own ID; it does not verify that entry and
exit endpoints belong to the connector's canonical `from_link_no` and `to_link_no`.

Targeted reproducers showed:

- Removing one mapping from a two-lane connector produced `status=PASS`, six edges for
  four declared connector lanes, `coverage=1.0`, and orphan node `lane:100:2`.
- Swapping one mapping's source and destination produced
  `lane:2:1 -> lane:100:1 -> lane:1:1`, yet `status=PASS` and
  `reverse_synthetic_edges=0`.

This violates the exact two directed edges per exact connector lane, reverse-edge
absence, and 100% executable coverage gates. Validation must derive expected lane IDs
from connector nodes/ranges, require a one-to-one mapping for every lane, and compare
edge endpoint object IDs and positions with the canonical connector endpoints.

#### C2. Explicit connector waypoints discard legitimate lane-change paths

**Files/lines:** `scripts/resolve_lane_routes.py:288-370` and
`scripts/resolve_lane_routes.py:415-420`.

`_transition_to_object` gathers exact-lane transitions for all input states, but runs
the lane-change fallback only when the global `result` list is empty. Thus, if any lane
can enter an explicit connector continuously, states on other lanes that can
legitimately change into the connector's lane range are silently discarded.
`_advance_to_waypoint` immediately returns that partial adjacent result and never
recovers the omitted paths.

In a two-lane source road with one connector from lane 1, the same physical route
resolved from both start lanes when the connector was a sparse waypoint, but adding
that connector to the explicit `linkSeq` returned only the lane-1 path:
`explicit_count=1`, `sparse_count=2`, with no error in either case.

The artifact consequently remains `PASS`, and equal shares are normalized over an
incomplete path set. A sum of one is not sufficient when the support itself is missing.
Fallback/reachability must be evaluated per state and all distinct executable paths
must be retained.

#### C3. The resolver certifies non-executable lane paths, so length and first-stopline evidence need not describe a physical path

**Files/lines:** `scripts/resolve_lane_routes.py:298-359`,
`scripts/resolve_lane_routes.py:373-412`, and downstream evidence construction at
`scripts/resolve_lane_routes.py:459-491` and `scripts/resolve_lane_routes.py:540-563`.

Forced road-lane changes accept every nonnegative `available_distance`, including zero,
and transition code does not reject a closed target connector/destination lane. Two
targeted checks demonstrated both failures:

- A connector exiting to road lane 2 at position 50 followed by a connector sourced
  from lane 1 at the same position resolved successfully with a recorded lane change
  from lane 2 to lane 1 and `available_distance_m=0.0`.
- Marking an exact connector lane closed still yielded a successful proof traversing
  that closed lane.

The first case is not a forward executable lane path: there is no physical road length
on which the required lateral transition can occur. Once such a state is accepted,
`physical_path_length_m` and `first_downstream_stopline_or_terminal` are computed from
the post-change synthetic segment and can false-PASS as evidence of an actual lane
path. Closed current/source/target nodes must be enforced, and zero-distance forced
lane changes must be rejected (or supported by explicit canonical lane-change
evidence).

### Important

#### I1. Missing and malformed `relFlow` representations can PASS as valid flow evidence

**Files/lines:** `scripts/resolve_lane_routes.py:79-140`,
`scripts/resolve_lane_routes.py:170-188`, and
`scripts/resolve_lane_routes.py:639-648`.

`route.get("relFlow", "")` makes an absent attribute indistinguishable from an explicit
empty VISSIM value. The latter may legitimately carry the repository's default-1
semantics, but the former is missing evidence and must not silently receive that
default. A route with no `relFlow` attribute compiled with `status=PASS`, no reasons,
and `defaulted=True` value 1.0.

For time-supported values, every token before the first `time:value` token is preserved
but never validated. For example, `bogus-prefix 0:1` is accepted as valid. Negative and
non-finite numeric values are correctly rejected, and raw support text is preserved,
but the missing/malformed cases still violate the false-PASS requirement. Attribute
presence and the supported VISSIM encoding prefix must be validated separately from an
explicit empty value.

#### I2. Route proof compilation trusts a stale graph semantic hash instead of verifying artifact integrity

**Files/lines:** `scripts/resolve_lane_routes.py:595-602` and
`scripts/resolve_lane_routes.py:612-638`.

The route compiler checks only that `graph["semantic_sha256"]` is nonempty. It never
recomputes the graph hash from the supplied semantic payload. After changing a
connector name without updating the stored hash, the stored and actual graph hashes
differed, but route compilation still returned `status=PASS` and embedded the stale
hash in its own semantic payload.

Individual output replacement is atomic and generated timestamps/absolute paths do not
pollute the declared semantic payloads. However, the graph-to-route artifact chain is
not integrity-closed: a semantically modified or corrupted persisted graph can be
certified by a PASS route artifact. The graph schema, canonical ordering, semantic hash,
status, and required gate fields must be recomputed/validated before route resolution.

#### I3. The required shuffle and multi-path tests do not exercise the stated invariants end to end

**Files/lines:** `scripts/tests/test_vissim_lane_graph.py:210-263` and
`scripts/tests/test_vissim_lane_graph_real_network.py:88-125`.

The ten-shuffle test meaningfully checks graph compilation from shuffled canonical
manifest arrays and checks route resolver insensitivity to graph array order. It does
not shuffle the INPX routing-decision/route element order: every route compile reads the
same `REAL_INPX`. It also shuffles a serialized graph while retaining its old semantic
hash, which masks the missing integrity verification in I2 rather than testing hash
regeneration from the supplied graph payload.

The test named for two legitimate paths actually creates two routes with one proof each
and verifies route-flow normalization. The sparse-waypoint test creates multiple paths
within one route but calls only `resolve_route_paths`, so it does not verify normalized
path shares for that multi-path route. The 339-route count, current-network exact
dimensions, aggregate share sum, unresolved count, and SC12 mapping assertions are
useful regression checks, but they do not detect C1-C3 or satisfy the requested
input-order and multi-path-share fixtures.

### Minor

#### M1. Command hashes omit executable dependencies used by the compilers

**Files/lines:** `scripts/build_vissim_lane_graph.py:65-70` and
`scripts/resolve_lane_routes.py:587-592`.

The graph command hash covers only `build_vissim_lane_graph.py`, although execution also
depends on canonical `compiler.py` and `topology.py`. The route command hash covers the
two A1 scripts but not the canonical hashing implementation it imports. Compiler
version/topology/signal evidence partly mitigates this, but the advertised command hash
can remain unchanged when executable dependency code changes. Include all behavioral
source dependencies, or define and enforce a transitive compiler hash contract.

## Compliance Summary

| Area | Result | Notes |
|---|---|---|
| Exact lane nodes and two directed connector edges | **FAIL** | C1 false-PASSes omitted and reversed mappings. |
| Forward explicit route execution; no hop cap/min-ID winner | **PARTIAL** | No hop cap or BFS min-ID winner, but C2 drops valid explicit paths and C3 admits invalid ones. |
| Multiple paths/terminals and normalized shares | **FAIL** | Numeric normalization is within tolerance for retained paths; retained support can be incomplete. |
| Raw/time-supported `relFlow` and invalid evidence | **FAIL** | Numeric negatives/non-finite values fail; missing attribute and malformed prefix pass. |
| Physical length and first downstream stopline/terminal | **FAIL** | Calculations are coherent only after path validity; C3 invalidates that premise. |
| Canonical connector/head interpretation and SC12 | **PASS** | A1 imports `compile_network`; no second connector/head XML parser; SC12 exact mappings are asserted. |
| Atomic artifact and deterministic semantic hash | **PARTIAL** | Atomic replace and canonical output ordering are present; graph hash integrity is not verified and command provenance is incomplete. |
| Real network 339 routes / coverage / ten shuffles | **PARTIAL** | Current-network regression passes, but coverage can false-PASS and route input order is not shuffled. |

## Verification Performed

- Reviewed `task-a1-brief.md`, `task-a1-report.md`, `review-a1.diff`, and all four A1
  source/test files against the canonical compiler/topology connector and head parsing.
- Ran the supplied combined suite: **12 tests passed in 32.665 s**.
- Ran targeted in-memory/temporary-fixture reproducers for missing/swapped connector
  mappings, omitted explicit paths, zero-distance lane changes, closed connector lanes,
  missing/malformed `relFlow`, and stale graph semantic hashes.
- No implementation code was modified by this review.
