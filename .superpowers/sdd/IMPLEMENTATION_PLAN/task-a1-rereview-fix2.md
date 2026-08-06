# Task A1 Fix Round 2 Independent Scoped Re-review

## Verdict

- **Spec compliance: FAIL**
- **Quality: FAIL (blocking)**
- **Approval: NOT APPROVED**
- **Remaining findings:** C2 ADDRESSED, I2 NOT_ADDRESSED, M1 ADDRESSED
- **Existing regressions:** C1/C3/I1/I3 representative targeted checks PASS
- **New findings:** Critical 0, Important 0

Fix round 2 closes the same-start-state path suppression in C2 and closes M1's
command-source closure gap. Most of I2 is also repaired: road nodes are bound to
their parent records, terminal bounds use the parent link length, and malformed
parents, edges, positional stoplines, and dimensions fail after rehashing. I2 is
still open because a supplied graph can contain a semantically malformed stopline,
be rehashed, and certify a `PASS` route proof.

The four reviewed worktree files exactly match the new blobs declared by
`review-a1-fix2.diff`: `95debd5`, `deafe44`, `714a6bb`, and `e2e211c`. No
implementation code was modified during this review.

## Finding Adjudication

| Finding | Result | Basis |
|---|---|---|
| C2 | **ADDRESSED** | Exact connector entries and positive-distance forced lane-change entries are collected together for each start state. Explicit and sparse routes have identical four-path support: two exact paths, two lane-change paths, two paths per start lane, and normalized shares of `0.25`. |
| I2 | **NOT_ADDRESSED** | Parent/node lengths, parent universes, edge semantics, stopline lane/position, and dimensions are checked, and terminal length is read from the parent link. However, required stopline signal identity is not validated: `signal_controller_no=None` survives rehash validation and produces a `PASS` artifact containing a stopline proof with a null controller. |
| M1 | **ADDRESSED** | The graph command hashes `plant/src/__init__.py`, every Python module under `plant/src/vissim_strict` including its initializer, and the graph script. The route command adds the resolver. The unit test asserts exact set equality for both command closures. |

## Blocking Evidence

### I2 - rehashed malformed stopline identity can false-PASS

**Files/lines:** `scripts/build_vissim_lane_graph.py:877`,
`scripts/resolve_lane_routes.py:551`; test blind spot at
`scripts/tests/test_vissim_lane_graph.py:553`.

The canonical graph builder treats `signal_controller_no` and
`signal_group_no` as required stopline evidence. The supplied-artifact validator,
however, checks only whether the referenced lane exists, the link/lane fields match,
and the position is finite and within lane length. It does not revalidate the
required signal identity fields.

Targeted reproducer:

1. Build the existing `manifest_fixture()` graph.
2. Set `signal_heads[0].signal_controller_no` to `None`.
3. Recompute the graph semantic hash.
4. Compile the existing valid route XML against the supplied graph.

Observed result:

```text
validator failures=[]
route artifact status=PASS
reason_codes=[]
first stopline signal_controller_no=None
```

The same validator also returned no failure when the targeted mutation was applied
individually to `signal_group_no` or `head_no`. This is a residual form of original
I2, not a new finding: the requested full-graph semantic gate still does not make
every invalid stopline fail.

### I2 portions that are closed

The independent mutation matrix confirmed `FAIL` after semantic rehash for:

- road lane-node length tamper;
- road parent-link length tamper;
- orphan node parent and duplicate node;
- unknown connector parent;
- unknown edge endpoint, unsupported edge kind, and negative edge position;
- stopline position beyond its parent lane;
- mismatched sample dimensions.

The resolver obtains `destination_length` from the parent object at
`scripts/resolve_lane_routes.py:623`. With only the terminal lane node length
tampered to `1000 m`, a direct resolver call for destination position `500 m` on
the `100 m` parent link returned zero paths and
`destination position is upstream or outside all executable terminal lanes`.

## Addressed Evidence

### C2 - exact and lane-change entries coexist

`scripts/resolve_lane_routes.py:339` now appends exact outgoing transitions and
then independently enumerates other source lanes with positive available distance;
the old `if not state_result` suppression is absent. The targeted two-lane fixture
at an `80 m` connector entry produced:

```text
explicit: 4 paths, exact=2, lane_change=2, by_start={lane:1:1:2, lane:1:2:2}
sparse:   4 paths, exact=2, lane_change=2, by_start={lane:1:1:2, lane:1:2:2}
explicit artifact: PASS, 4 proofs, shares=[0.25]
sparse artifact:   PASS, 4 proofs, shares=[0.25]
```

The support triples `(start lane, terminal lane, traversed edge IDs)` were exactly
equal between explicit and sparse forms.

### M1 - exact behavioral source closure

`scripts/build_vissim_lane_graph.py:76` hashes the graph script,
`plant/src/__init__.py`, and all 11 Python files under
`plant/src/vissim_strict`, including `vissim_strict/__init__.py`. The observed graph
closure had exactly 13 entries; the route closure had exactly those entries plus
`scripts/resolve_lane_routes.py`. The exact-equality assertions at
`scripts/tests/test_vissim_lane_graph.py:676` passed.

## Regression And New-Finding Check

- C1 representative connector-universe/mapping/orientation tests: PASS.
- C3 closed-node and zero-distance forced lane-change test: PASS.
- I1 malformed/missing/explicit-empty relative-flow tests: PASS.
- I3 eight-path end-to-end normalization test: PASS.
- I3 actual real-network ten-shuffle semantic-hash test: PASS.
- No new Critical or Important finding was identified. The null stopline identity
  false-PASS remains within original I2.

## Targeted Verification

- Selected unit reproducers for C1, C2, C3, I1, I2, I3, and M1:
  **10 passed in 0.250 s**.
- Actual real-network ten-shuffle I3 test: **1 passed in 50.986 s**.
- Independent C2 support/share reproducer: explicit and sparse each PASS with four
  identical supports and `0.25` shares.
- Independent I2 mutation matrix: all requested physical/parent/edge/position/
  dimension mutations failed; malformed stopline signal identity false-PASSed.
- Independent terminal-bound reproducer: node-only `1000 m` tamper could not extend
  a `100 m` parent link.
- Independent M1 closure inspection: graph 13 exact entries; route adds only the
  resolver.

Only these targeted checks were run. No broad test suite was executed.
