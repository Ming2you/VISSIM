# A2 one-stock physical topology implementation report

## Result

**DONE**

Implemented the A2 physical topology compiler without modifying S0R, A1, adapter, or
NumSim files. Generated graph, route, and topology artifacts used for verification were
written only below `%TEMP%\a2-inspect` and `%TEMP%\a2-final`; no tracked output artifact
was regenerated.

## Changed files

- `scripts/compile_physical_stock_topology.py`
- `scripts/tests/test_compile_physical_stock_topology.py`
- `scripts/tests/test_compile_physical_stock_topology_real_network.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-a2-report.md`

## Compiler contract

The compiler consumes `vissim-lane-graph-v2.1`, `lane-route-proofs-v2.1`, legacy
ownership, adjacency, and capacity evidence. It revalidates both A1 schemas, PASS status,
empty reasons, semantic SHA-256, canonical collection order, graph/route binding, route
coverage gates, lane segments, edge references, and normalized flow evidence before
building stocks.

Each stock ID canonically encodes `(link_no, lane_no, start_m, end_m)`. Split evidence
includes lane endpoints, connector entry/exit positions, signal heads, routing decisions,
destinations, proof-segment endpoints, and lane-change branch points. Points within
`1e-6 m` are coalesced. Stocks retain A1 lane membership, parent kind, half-open interval,
length, incident stock/edge IDs, route/proof memberships and shares, ownership,
visibility, objective weights, split provenance, and interval capacity prior.

The following axes are deliberately separate:

- A1 parent kind: `link` or `connector`;
- legacy partition: `urban_owned`, `freeway_bound`, `boundary_out`, or outside;
- physical roles: `urban`, `interface`, `boundary_out`, `freeway`, `ramp`, and
  `connector`.

This preserves all 771 A1 connector links and does not coerce the 14 objects outside the
legacy 1,205-ID partition into that partition. Four mainline roads are anchored by the
freeway-bound target identities and propagated only through exact A1 unpartitioned
connectors. Eight ramp connectors and two mainline connectors are then classified from
their directed endpoints. Seven production stocks have multiple legitimate owners and
use normalized A1 route-flow shares; no minimum-ID tie-break is used.

The visibility helper deduplicates by stock ID. External boundary stocks retain the typed
principal `external:boundary-out`. Objective evaluation changes only binary weights; it
does not rebuild or mutate stock or edge traces.

Capacity is `length_km * 140.54304101885097 veh/km/lane` for each one-lane interval.
The capacity evidence semantic hash and source file hash are retained. Named evidence is
preserved exactly for `R_D_E=93.0`, `R_D_W=128.0`, `R_F_E=128.4`, and `R_F_W=145.9 veh`.
The source artifact does not contain a lane-membership map for those names, so the
compiler records that fact rather than assigning a scalar or inventing membership.

## Production result

The final atomic CLI run used the regenerated A1 artifacts under `%TEMP%\a2-final` and
the three tracked evidence inputs. Result:

```text
status=PASS stocks=7275 edges=7418 gaps=0 owners=0
semantic_sha256=3d74ecd488e065ef0641d43dc583cec7fa29e3e51cbec1792802f19b8f786cf2
```

A1 and command hashes:

- lane graph semantic SHA-256:
  `6c3671b8e6c5bbc801aff359722e9f62ac6ed653c956d1f4f1a5f857240b670b`
- lane route proofs semantic SHA-256:
  `4ee8f2cfc2c61388f7a51e799e935120ce14d96e7bcc3e73942d82146bf1735a`
- A2 command hash:
  `ddcb23936b53197ec0b4de47f467a6b231128b0f8cb6aca1452d669a951eee14`

Production dimensions:

| Measure | Count |
|---|---:|
| A1 road links | 448 |
| A1 connector links | 771 |
| A1 lane nodes | 2,649 |
| Physical stocks | 7,275 |
| Link-parent stocks | 5,840 |
| Connector-parent stocks | 1,435 |
| Stock edges | 7,418 |
| Route memberships | 29,967 |
| Multi-owner stocks | 7 |

Legacy link counts are exact: urban-owned 957, freeway-bound 22, boundary-out 226,
total 1,205, duplicate 0, missing from A1 0. There are four remaining A1 road links and
all 771 A1 connectors remain explicit. Stock counts by legacy partition are 6,245
urban-owned, 150 freeway-bound, 735 boundary-out, and 145 outside the legacy partition.

Physical role stock counts are urban 6,245, interface 150, boundary-out 735, freeway
125, ramp 20, and connector 1,435. Roles are orthogonal, so connector stocks can also
carry a legacy-derived role.

Capacity prior totals:

| Partition | Capacity (veh) |
|---|---:|
| Urban-owned | 33,580.099872614766 |
| Freeway-bound | 3,681.3294290962535 |
| Boundary-out | 5,534.120649889526 |
| Outside legacy partition | 12,610.468314882737 |
| Physical total | 55,406.01826648328 |

Objective weight-one counts:

| Mode | Stocks included |
|---|---:|
| `physical_total` | 7,275 |
| `controller_default` | 6,540 |
| `controller_with_boundary` | 7,275 |
| `boundary_only` | 735 |

`controller_with_boundary - controller_default = boundary_only = 735` stocks. Synthetic
weighted-state tests also verify that the scalar difference equals the exact boundary
contribution while serialized stock/edge/value traces remain byte-identical.

All production gates are zero: gap, overlap, missing lane, nonpositive interval,
duplicate stock ID, legacy duplicate/missing, unexplained owner, objective violation, and
visibility-uncovered stock. Maximum owner-weight sum error is `0.0`; named ramp evidence
count is four.

## SC12

SC12 shared lane `lane:1220012103:2` compiles to four physical interval stocks. Through
connector `10241` memberships cover two stocks; left connector `10242` memberships cover
two stocks; both movements reference the same two stock IDs:

```text
stock:1220012103:2:0.524808:107.366358943901773
stock:1220012103:2:107.366358943901773:110.663306000000006
```

No movement-specific stock copies exist.

## Tests

```text
python -B -m unittest scripts.tests.test_compile_physical_stock_topology -v
```

PASS: 9 tests in 0.177 s. Covers serial, parallel, split, merge, multi-owner shared route,
duplicate split coalescing, missing parent/owner/adjacency, stale graph and route hashes,
duplicate legacy identity, objective trace identity, visibility mass deduplication, and
transitive command hashes.

```text
python -B -m unittest scripts.tests.test_compile_physical_stock_topology_real_network -v
```

PASS: 5 tests in 55.451 s. Covers A1 revalidation, all production gates, interval capacity,
global visibility mass, SC12 identity, and ten shuffled manifest/ownership/adjacency/
capacity input orders. All ten shuffled compiles produced the single A2 semantic hash
`3d74ecd488e065ef0641d43dc583cec7fa29e3e51cbec1792802f19b8f786cf2`.

```text
python -B -m unittest scripts.tests.test_vissim_lane_graph -q
```

PASS: the existing 18 A1 unit tests in 0.423 s.

Static self-review also compiled all three new Python files from source, found no
non-ASCII characters, and confirmed no `scripts/__pycache__` was left behind. The final
production artifact was 30,666,951 bytes and remained under `%TEMP%\a2-final`.

## Self-review

- A1 artifacts are validated before any stock is emitted; corrupted semantic payloads
  return a FAIL artifact rather than an exception or false PASS.
- Legacy ownership IDs are evidence only and never appear as stock IDs.
- Input byte hashes are retained as provenance but excluded from the semantic payload;
  normalized evidence semantic hashes keep shuffled JSON ordering deterministic.
- Boundary and uncontrolled states are typed. Production has zero uncontrolled stocks.
- Named ramp capacity is preserved without a scalar fallback or fabricated lane mapping.
- Atomic output uses the approved A1 temporary-file, flush, fsync, and `os.replace` path.
- Existing dirty-worktree files were not edited or reverted.
