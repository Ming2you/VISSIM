# Task A1 Fix Round 3 Independent Scoped Re-review

## Verdict

- **Spec compliance: PASS**
- **Quality: PASS**
- **Approval: APPROVED**
- **Finding adjudication:** I2 ADDRESSED; C2 and M1 remain ADDRESSED
- **Regression checks:** C1/C3/I1/I3 representative targeted checks PASS
- **New findings:** Critical 0, Important 0

Fix round 3 closes the remaining I2 stopline-identity false-PASS. A supplied graph
with a rehashed semantic payload now fails closed when any required signal identity
is null, empty, nonnumeric, noncanonical, or duplicated. Canonical lane/link/position
binding remains enforced, and a first-stopline proof is emitted only from a graph
that passed the full validator.

The four reviewed worktree files exactly match the new blobs declared by
`review-a1-fix3.diff`: `6ff316c`, `176e15e`, `219525a`, and `e2e211c`. No
implementation code was modified during this review.

## Finding Adjudication

| Finding | Result | Basis |
|---|---|---|
| I2 | **ADDRESSED** | `signal_controller_no`, `signal_group_no`, and `head_no` must normalize to positive canonical integer identities. Stable head ID, normalized head uniqueness, composite `(SC, SG, head)` uniqueness, canonical lane/link/lane-number binding, and finite in-range position are all checked after semantic rehash. Invalid supplied graphs produce `FAIL` with no proofs. |
| C2 | **REMAINS ADDRESSED** | The explicit/sparse per-state path-support regression still passes, as does the two-path normalization check. |
| M1 | **REMAINS ADDRESSED** | Exact graph and route behavioral source-closure assertions still pass. |

`signal_controller_no` and `signal_group_no` are not individually required to be
globally unique because multiple legitimate heads share a controller and signal group.
The duplicate requirement is correctly applied to globally stable `head_no` and the
complete normalized `(SC, SG, head)` identity.

## I2 Evidence

### Required signal identity fails after semantic rehash

`scripts/build_vissim_lane_graph.py:60-73` accepts only positive Python integers or
canonical ASCII decimal strings. The validator at
`scripts/build_vissim_lane_graph.py:890-958` requires all three normalized identity
parts, verifies `id == signal-head:<head_no>`, and rejects duplicate normalized head
numbers or duplicate composite signal identities.

An independent mutation matrix changed each of the following values, recomputed the
graph semantic hash, then called both `validate_lane_graph_artifact()` and route
compilation:

- `signal_controller_no`: `None`, `""`, and `"bogus"`;
- `signal_group_no`: `None`, `""`, and `"bogus"`;
- `head_no`: `None`, `""`, and `"bogus"`;
- duplicate stable head record/composite identity.

All ten cases returned `invalid_lane_graph_stopline_identity`. Route compilation
returned `status=FAIL` and `proofs=[]` in every case. The duplicate case additionally
reported the generic duplicate artifact ID, as expected.

### Canonical physical identity remains closed

The same independent matrix rehashed mutations to `lane_id`, `link_no`, `lane_no`,
and an out-of-parent `position_m`. Every mutation returned
`invalid_lane_graph_stopline`, compiled to `FAIL`, and emitted no proof. The binding
at `scripts/build_vissim_lane_graph.py:926-937` resolves the lane from the canonical
parent-derived node universe, then requires exact link/lane equality and a finite,
nonnegative position no greater than the parent lane length.

### First-stopline proof contains validated IDs

Route compilation gates all resolution on an empty validator result at
`scripts/resolve_lane_routes.py:688-721`. The first-stopline projection at
`scripts/resolve_lane_routes.py:531-557` copies only the stable head ID, SC/SG/head
identity, lane ID, and position from that validated graph record.

The valid fixture produced `PASS` and two stopline proofs. Each proof had the exact
allowed field set and matched graph identity
`signal-head:501 / SC 12 / SG 3 / head 501 / lane:2:1 / 60.0 m`.

## Regression And New-Finding Check

- C1 connector universe, exact mapping, and reversal rejection: PASS.
- C2 explicit/sparse same-state support and normalized multipath behavior: PASS.
- C3 closed-node and zero-distance forced lane-change rejection: PASS.
- I1 missing versus explicit-empty `relFlow` evidence: PASS.
- I3 eight-path end-to-end normalization: PASS.
- I3 actual real-network ten-shuffle graph/route determinism: PASS.
- M1 exact transitive command-source closures: PASS.
- Real-network production gates remain PASS with 541 valid signal heads.
- No new Critical or Important breakage was identified.

## Targeted Verification

- Selected unit checks for I2, C1, C2, C3, I1, I3, and M1:
  **10 passed in 0.299 s**.
- Independent rehashed identity/physical-reference matrix:
  **14 malformed cases failed closed; valid proof identity passed**.
- Real-network production-gate and ten-shuffle I3 checks:
  **2 passed in 50.945 s**.

Only these targeted checks were run. No broad test suite was executed.
