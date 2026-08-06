# A2 fix round 1 report

## Result

**DONE**

All Critical 1-2 and Important 1-2 findings in `task-a2-review.md` are fixed. The
changes remain limited to the A2 topology compiler, its focused tests, and this report.
A1, S0R, adapter, and NumSim files were not modified. All generated graph, route, and
topology artifacts remained under `%TEMP%`.

## Changed files

- `scripts/compile_physical_stock_topology.py`
- `scripts/tests/test_compile_physical_stock_topology.py`
- `scripts/tests/test_compile_physical_stock_topology_real_network.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-a2-fix1-report.md`

## Critical 1: trusted evidence and partition identity

### Root cause

The original compiler computed hashes from the supplied ownership, adjacency, and
capacity values and then trusted those newly computed hashes. Production count gates
checked cardinality, overlap, and A1 membership but had no independent identity anchor.
Consequently, count-preserving partition swaps and changed adjacency/capacity values
could certify themselves.

### Fix

Production compilation now binds the three evidence inputs to the approved hashes
recorded by `preflight-v3`:

| Evidence | Trusted raw SHA-256 |
|---|---|
| `link_player_assignment_20260805.json` | `ba9c13ba9fe9e05c51866a50221a1054d73a3379315bf97c108a0552397eb01f` |
| `intersection_adjacency8_20260805.json` | `a7cafe52693dfc46098f14763e37772a6f680ec56af28ac432bfcbfb907ae8ae` |
| `urban_storage_capacity_20260805.json` | `f196de2c444c72b117fec7f0e16f2c81189acada686b76f3def273096d8f87d5` |

The compiler also compares normalized semantic hashes for all three inputs. Legacy
partition identities are independently projected as the exact sorted ID sets for
`urban_owned`, `freeway_bound`, and `boundary_out`; that projection is pinned to:

```text
d386df06e9d583c6263741a80c6038d0ec80534566a44f5f0bf02947172a22e6
```

Production mode always uses the embedded approved anchors and ignores caller-provided
fixture expectations. Focused fixture calls must supply an independently captured
`expected_evidence_hashes` mapping; omitting it returns FAIL with no stocks. Hash or
identity mismatch is checked before partition inference or stock construction.

Adversarial production outcomes:

| Reproducer | Result | Reasons |
|---|---|---|
| Swap connector `10000` urban with `10001` boundary | FAIL, 0 stocks | `legacy_partition_identity_hash_mismatch`, `trusted_evidence_hash_mismatch` |
| Add fake adjacency principal `999999` | FAIL, 0 stocks | `trusted_evidence_hash_mismatch` |
| Double jam density | FAIL, 0 stocks | `trusted_evidence_hash_mismatch` |
| Supply wrong ownership raw file hash | FAIL, 0 stocks | `trusted_evidence_file_hash_mismatch` |

The exact production partition remains 957 urban-owned + 22 freeway-bound + 226
boundary-out = 1,205, with duplicate/missing 0. The PASS artifact records the partition
identity hash in both `input_hashes` and `legacy_partition.identity_sha256` and exposes a
zero `legacy_partition_identity_mismatch` production gate.

## Critical 2: valid multi-owner shares

### Root cause

The original `use_route_weights` condition excluded urban parents with direct legacy
ownership. The alternate route path then summed conditional shares from unrelated
routing-decision denominators as if decision inflows were known.

### Fix

Owner attribution is now scoped to physical routing evidence:

1. Consider only route memberships whose routing decision is on the stock's own parent.
2. Use the nearest local decision at or upstream of the stock interval.
3. Aggregate normalized A1 path shares only within that one decision and its earliest
   common flow support.
4. Permit multiple same-position decisions only when their normalized owner
   distributions are equal within `1e-9`; no inflow weighting is then needed because the
   resulting distribution is invariant.
5. If same-position decision distributions differ and no decision-inflow evidence is
   available, return `unsupported_multi_decision_owner_weights` rather than combining
   denominators.
6. Use a local multi-owner distribution even when the parent is urban-owned and has a
   direct legacy owner. A single-owner local result does not displace valid direct
   ownership evidence.

The corrected urban shared-parent fixture returns `urban:2=0.75` and `urban:3=0.25`
from decision 7. A paired decision at the same position with the opposite 0.25/0.75
distribution returns FAIL. The review's production stock
`stock:70:1:67.915467926212969:180.143228351476381` now uses its direct
`legacy_freeway_bound` owner and does not combine decisions 1133, 1134, and 1140.

Production has 48 supported multi-owner stocks: 37 urban-owned, six freeway-bound, and
five outside the legacy partition. Every route-derived owner state records its exact
decision number(s), decision position, and flow support time. Maximum owner-weight sum
error is `1.1102230246251565e-16`; unexplained owner count remains zero.

## Important 1: global artifact keys

Both PASS and FAIL artifacts now contain the exact required top-level keys:

```text
schema_version
input_hashes
command_version
status
reasons
sample_dimensions
units
downstream_consumers
```

`input_hashes` contains A1 semantic hashes, normalized evidence hashes, the exact legacy
partition identity hash, and raw input hashes when paths are available. The exact command
record is:

```json
{
  "command": "scripts/compile_physical_stock_topology.py",
  "version": "compile-physical-stock-topology/2.1.1",
  "sha256": "b060eb7a48ee03727a3b1fb67f30d46787a8bf47085f71f8609e4fbb76280330"
}
```

The existing transitive source closure remains under `command`; its final command hash
is `91e8b6e1772ccf7d0accafbe3d54fcd09f3fb4cbadd1a6ab9f565b7f6a99f854`.

## Important 2: stronger tests

- SC12 now requires exact equality of through and left stock-ID sets, not a nonempty
  intersection. Both sets remain the same two route-covered physical stocks.
- Objective testing calls the mode-aware `objective_evaluation()` path for all four
  modes, asserts the exact boundary scalar delta, and compares the returned physical
  stock/edge traces byte-for-byte.
- Synthetic and production tests cover ownership partition swap, fake adjacency,
  changed capacity, wrong raw hash, and missing trusted expectations.
- The shared-route fixture is urban-owned, so direct-owner precedence can no longer hide
  the multi-owner requirement.
- A separate fixture supplies two unrelated decision denominators and requires
  fail-closed behavior.
- The reported production multi-decision stock is pinned against denominator mixing.
- The full generic artifact key contract is asserted on both PASS and FAIL outputs.

## Production result

The final atomic CLI run wrote only
`%TEMP%\a2-fix1\physical_stock_topology_v2_1.json`:

```text
status=PASS stocks=7275 edges=7418 gaps=0 owners=0
semantic_sha256=137cd1a19d50d7b026e9021f770adc5f0b24753e0d8a36e09816e04ef990b920
```

All original physical gates remain satisfied: 2,649/2,649 lanes covered, gap/overlap/
missing/nonpositive/duplicate 0, connector-parent stocks 1,435, objective violations 0,
visibility-uncovered stocks 0, and four named ramp capacities retained. Objective
weight-one counts remain 7,275 physical total, 6,540 controller default, 7,275 controller
with boundary, and 735 boundary only. The temporary artifact is 30,676,637 bytes.

## Verification

```text
python -B -m unittest scripts.tests.test_compile_physical_stock_topology -q
```

PASS: 12 synthetic tests in 0.244 s.

```text
python -B -m unittest scripts.tests.test_compile_physical_stock_topology scripts.tests.test_compile_physical_stock_topology_real_network -v
```

PASS: the then-current 18 A2 tests in 59.169 s, including all seven real-network tests
and ten shuffled source-order compiles. The subsequently added missing-trust synthetic
test passed in the final 12-test synthetic run, giving 19 current A2 tests total.

```text
python -B -m unittest scripts.tests.test_vissim_lane_graph scripts.tests.test_vissim_lane_graph_real_network -v
```

PASS: all 24 existing A1 unit and real-network tests in 51.257 s, including A1's own ten
shuffle test and unchanged SC12 connector mappings.

## Self-review

- Recomputed the final topology semantic payload and matched the stored semantic hash.
- Rehashed all three production evidence files and matched every embedded trusted raw
  anchor exactly.
- Confirmed all four independent review reproducers now fail before stock construction.
- Confirmed route-derived distributions are sorted and decision-scoped; no unrelated
  denominator accumulator remains.
- Compiled all three new Python sources directly; syntax passed.
- Found zero non-ASCII characters and zero trailing-whitespace lines in the A2 files.
- Confirmed no `scripts/__pycache__` and no tracked graph/route/topology output update.
- Existing dirty-worktree files outside A2 were neither edited nor reverted.

## Concerns

None. An intentional future change to any approved ownership, adjacency, or capacity
evidence now requires an explicit reviewed update of the A2 trusted anchors and command
version; silent evidence drift is rejected.
