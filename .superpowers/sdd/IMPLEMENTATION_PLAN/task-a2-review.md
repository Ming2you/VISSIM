# A2 one-stock physical topology independent review

## Verdict

**FAIL**

Finding count: **Critical 2 / Important 2 / Minor 0**.

The production artifact satisfies the interval-cover, split-point, binary-objective,
visibility-deduplication, capacity-formula, and SC12 physical-identity checks. It does
not satisfy the independent/hash-bound evidence contract or the multi-owner flow-share
contract, and required tests contain false-PASS paths.

## Findings

### Critical 1 - Legacy/evidence inputs are self-hashed, not trust-anchored, so count-fitting and tampering PASS

**Files:**

- `scripts/compile_physical_stock_topology.py:138-198`
- `scripts/compile_physical_stock_topology.py:579-621`
- `scripts/compile_physical_stock_topology.py:1029-1064`
- `scripts/tests/test_compile_physical_stock_topology.py:321-355`

Ownership, adjacency, and storage inputs have no accepted schema/status/hash contract.
The compiler normalizes their current contents, computes new semantic hashes from those
contents, and records current file hashes. It never compares either hash to a trusted
expected hash such as the preflight manifest. The legacy gate then verifies only set
counts, overlap, declared total, and A1 membership. It does not independently verify the
partition identities.

Targeted production reproducer swapped connector `10000` from `urban_owned` with
connector `10001` from `boundary_out`, preserving the union and all counts. Compilation
still returned `PASS`, no reasons, and `957 + 22 + 226 = 1205`. Separate mutations added
fake adjacency principal `urban:999999` and doubled jam density; both also returned
`PASS` (the fake principal became visible on 156 stocks). Thus count-correct but wrong
classification and ownership/adjacency/storage tampering are accepted rather than
failing closed.

The existing tamper test changes only A1 graph/route payloads. It has no ownership,
adjacency, or capacity hash-tamper case, so it cannot detect this defect.

### Critical 2 - Multi-owner weights are not valid A1 flow shares

**Files:**

- `scripts/compile_physical_stock_topology.py:804-843`
- `scripts/tests/test_compile_physical_stock_topology.py:250-266`

`use_route_weights` is disabled for an urban parent that has a direct legacy owner.
Consequently, a physical stock with two legitimate downstream route owners is assigned
`{legacy_owner: 1.0}` even though both route memberships and their 0.75/0.25 A1 shares
are present. A minimal variant of the submitted split fixture returned:

```text
status=PASS
stock:1:1:10:80 memberships=[route:7:1, route:7:2]
control_owner_state=legacy_link_owner
control_owner_weights={urban:2: 1.0}
```

There is a second error on the path where route weights are used: membership shares are
summed across routing decisions and normalized as though their denominators were common.
Production stock `stock:70:1:67.915467926212969:180.143228351476381` mixes conditional
shares from decisions `1133`, `1134`, and `1140` without decision inflow evidence. The
result sums to one, but is not a supported physical flow split.

The submitted multi-owner test avoids the first defect by marking the shared parent as
`freeway_bound`; it has no urban-owned shared-route case and no multiple-decision case.

### Important 1 - The output violates the required global artifact key contract

**Files:**

- `IMPLEMENTATION_PLAN.md:708-710`
- `scripts/compile_physical_stock_topology.py:931-985`

The global contract requires top-level `input_hashes` and `command_version`. The emitted
artifact has neither. It instead has non-contract substitutes
`source_artifacts` and `command.version`. A direct key check of the reported production
artifact returned:

```text
missing_global_contract_keys=['command_version', 'input_hashes']
```

Atomic replacement, deterministic semantic hashing, source hashes, units, and downstream
consumer metadata are present, but generic downstream contract validation cannot accept
this artifact as specified.

### Important 2 - Required SC12/trace/tamper tests admit false PASS results

**Files:**

- `scripts/tests/test_compile_physical_stock_topology.py:292-309`
- `scripts/tests/test_compile_physical_stock_topology.py:321-355`
- `scripts/tests/test_compile_physical_stock_topology_real_network.py:120-141`

The objective trace test serializes the same manually constructed stock/edge/value object
for every mode and discards `weighted_objective`'s return value before serialization. It
would remain byte-identical without exercising a mode-dependent trace path. The SC12 test
requires only a nonempty intersection between through and left stock IDs; it does not
require equality, so movement-specific copies plus one accidental shared stock could
pass. Evidence tampering and the multi-owner false-PASS cases above are absent.

The suite is not merely a `7,275` count pin and does contain useful behavioral fixtures,
but these weak assertions miss the two critical defects.

## Independent verification

Reviewed `review-a2.diff` (3 new files, 1,651 inserted lines) against the working tree.
No implementation code was modified.

- Existing tests: synthetic **9/9 PASS**; real-network **5/5 PASS**.
- Independent exact cover: 2,649/2,649 lanes; 7,275 unique stocks; gap 0, overlap 0,
  nonpositive 0, duplicate tuple/ID 0, missing lane 0, orphan 0.
- Required split occurrences: 56,349 checked; missing 0. This covered graph connector
  endpoints, signal heads, route decisions/destinations, proof segment endpoints, and
  lane-change endpoints.
- Raw legacy reconstruction: 957 urban-owned, 22 freeway-bound, 226 boundary-out,
  total 1,205, overlap 0, A1-missing 0; 4 remaining road links and 771 connector links.
  Identity trust still fails as described in Critical 1.
- Owner numeric sums: error count 0. Semantic attribution fails as described in
  Critical 2; no minimum-ID owner fallback was found.
- Visibility: submitted ten-order tests and independent global mass check passed; stock
  IDs are deduplicated across viewers.
- Capacity: all stock values equal `length_m / 1000 * jam_density`, with `veh` units and
  evidence hash; four named ramp values are retained exactly.
- Objectives: all weights are integer binary and `controller_default` versus
  `controller_with_boundary` differs exactly on boundary-out stocks.
- SC12 lane 2: four unique physical stocks; through and left membership sets are equal
  and share the same two route-covered stock IDs in the current production artifact.
- Determinism/atomicity: ten shuffled real-input compiles produced one semantic hash;
  the writer flushes, fsyncs, and uses `os.replace`.

## Required disposition

Do not accept A2 as DONE. Require trusted expected hashes (or validated semantic artifact
wrappers) for ownership, adjacency, and storage; identity-level legacy partition checks;
flow-share derivation that handles urban shared parents and does not combine unrelated
routing-decision denominators; exact global artifact keys; and adversarial tests for all
reproducers above.
