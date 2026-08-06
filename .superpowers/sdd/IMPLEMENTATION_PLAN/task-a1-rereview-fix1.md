# Task A1 Fix Round 1 Independent Scoped Re-review

## Verdict

- **Spec compliance: FAIL**
- **Quality: FAIL (blocking)**
- **Approval: NOT APPROVED**
- **Original findings:** 4 ADDRESSED, 3 NOT_ADDRESSED
- **New findings:** Critical 0, Important 0

The package closes C1, C3, I1, and I3. C2 still omits legal paths from an
individual start state whenever that state also has an exact connector-lane
transition. I2 still accepts internally inconsistent, rehashed graph evidence and
can use it to certify a physically impossible terminal position. M1's manually
enumerated source closure still omits Python package initializers executed during
the imports.

The reviewed worktree files exactly match the four new blobs declared by
`review-a1-fix1.diff` (`a1ed186`, `4f3238c`, `02e7049`, and `e2e211c`). No
implementation code was modified during this review.

## Original Finding Adjudication

| Finding | Result | Basis |
|---|---|---|
| C1 | **ADDRESSED** | Declared connector lane ranges seed the expected universe; one-to-one mappings, exact endpoint lane IDs and positions, stable edge IDs, and exact connector-node degree are checked. Missing, duplicate, swapped, and reversed evidence fails in targeted fixtures. |
| C2 | **NOT_ADDRESSED** | Per-state fallback fixes cross-state suppression, but an exact transition still suppresses other legal lane-change transitions from that same state. A PASS artifact is normalized over the incomplete support. |
| C3 | **ADDRESSED** | Closed current/source/connector/exit/terminal nodes are rejected, and a forced lateral transition requires more than `1e-6 m` of available distance. Closed-node and zero-distance fixtures pass. |
| I1 | **ADDRESSED** | Missing `relFlow` is distinct from explicit empty and fails; explicit empty preserves raw/presence/default evidence; `bogus-prefix` fails while prefix `2` supports preserve raw tokens and raw time/value fields. |
| I2 | **NOT_ADDRESSED** | Hash/schema/status/gate and connector-local checks exist, but the validator does not validate road node/link consistency. Rehashed contradictory physical evidence can validate cleanly and produce a PASS route artifact. |
| I3 | **ADDRESSED** | The targeted real-network test rewrites and shuffles actual decision and route XML children for 10 seeds and retains one graph/route semantic hash. The single-route fixture compiles eight paths end to end with shares of `0.125`. |
| M1 | **NOT_ADDRESSED** | The hash list covers the named implementation modules but omits executed `plant/src/__init__.py` and `plant/src/vissim_strict/__init__.py`; the tests assert only a subset, not the transitive execution closure. |

## Blocking Evidence

### C2 - same-start-state explicit waypoint paths are still omitted

**Files/lines:** `scripts/resolve_lane_routes.py:311-377`; blind spot at
`scripts/tests/test_vissim_lane_graph.py:274-287`.

`_transition_to_object()` collects exact transitions into `state_result`, then runs
lane-change alternatives only under `if not state_result`. This is now scoped per
state, but it still means a start state with one exact entry never explores another
connector lane that is reachable by a positive-distance lane change.

Using the existing two-lane source and two-lane connector fixture at an 80 m entry
position, both source lanes can stay in lane or change to the other mapped lane.
The sparse route retains four paths, two per start lane. Adding connector `100` as
an explicit waypoint returns only two paths, one per start lane:

```text
explicit status=PASS proofs=2 by_start={lane:1:1: 1, lane:1:2: 1}
explicit normalized shares=[0.5, 0.5]
sparse   status=PASS proofs=4 by_start={lane:1:1: 2, lane:1:2: 2}
sparse   normalized shares=[0.25, 0.25, 0.25, 0.25]
```

The existing C2 regression uses a one-lane connector, so each start state has at
most one legal entry and cannot expose this remaining suppression. This is the same
root finding as original C2, not a new finding.

### I2 - rehashed contradictory road evidence can false-PASS

**Files/lines:** `scripts/build_vissim_lane_graph.py:507-645` and
`scripts/resolve_lane_routes.py:575-601`; blind spot at
`scripts/tests/test_vissim_lane_graph.py:450-500`.

`validate_lane_graph_artifact()` validates connector nodes, mappings, edges, degree,
and the connector-lane dimension, but it does not cross-check road lane nodes against
the corresponding `links` records or validate the other dimensions. The resolver
then trusts each terminal node's `length_m` when accepting destination positions and
computing physical path length.

In the one-lane connector fixture, changing only node `lane:2:1.length_m` from the
link's 100 m to 1000 m and recomputing the semantic hash produced:

```text
validator_failures=[]
route status=PASS proofs=2 reasons=[]
terminal_position_m=500.0 physical_path_length_m=580.0
```

Thus a destination 400 m beyond the link can be certified after a semantic payload
tamper whose hash is internally current. The fix test's recomputed-hash case mutates
connector degree, which the connector-local checks detect; it does not close other
route-critical graph semantics. This remains original I2, not a new finding.

## Minor Evidence

### M1 - transitive source closure is still incomplete

**Files/lines:** `scripts/build_vissim_lane_graph.py:72-84`,
`scripts/resolve_lane_routes.py:625-626`, and subset-only tests at
`scripts/tests/test_vissim_lane_graph.py:502-511` and
`scripts/tests/test_vissim_lane_graph_real_network.py:157-168`.

Importing `src.vissim_strict.compiler` executes both `plant/src/__init__.py` and
`plant/src/vissim_strict/__init__.py`. Neither path is in `source_sha256`, so changes
to executable package initialization can leave both advertised command hashes
unchanged. This is the same provenance gap as original M1.

## New Findings

No new Critical or Important breakage was found. The blocking counterexamples above
are residual forms of original C2 and I2; the source-closure gap remains original M1.

## Targeted Verification

- Selected A1 unit tests for C1-C3, I1-I3, and M1: **9 passed in 0.081 s**.
- Real-network actual XML decision/route ten-shuffle test: **1 passed in 43.266 s**.
- Custom in-memory C2 explicit-vs-sparse reproducer: explicit PASS with 2 paths;
  sparse PASS with 4 paths.
- Custom rehashed I2 graph reproducer: validator returned no failures and route
  compilation false-PASSed `destPos=500 m` on a 100 m link.
- Custom M1 import-closure check: two executed repository package initializers were
  absent from the command source hash map.

Only these targeted checks were run. No broad test suite was executed.
