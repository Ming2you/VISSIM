# Task A1 Implementation Report

Status: DONE

## Scope and changed files

- `scripts/build_vissim_lane_graph.py`
  - Canonical directed exact-lane graph compiler and atomic JSON writer.
  - Reuses `plant/src/vissim_strict/compiler.py::compile_network`; it does not implement a second connector or signal-head parser.
- `scripts/resolve_lane_routes.py`
  - Active static-route parser, no-hop-cap directed lane-position resolver, flow normalizer, and atomic proof compiler.
- `scripts/tests/test_vissim_lane_graph.py`
  - Unit fixtures for multi-lane connector ranges, position ordering, reverse traversal, multiple paths to one terminal, invalid/time-dependent `relFlow`, an upstream next connector, and sparse waypoints.
- `scripts/tests/test_vissim_lane_graph_real_network.py`
  - Real-network gates, SC12 mapping lock, proof-share checks, and ten shuffled-order compiles.
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-a1-report.md`
  - This report.

No S0R, baseline, existing compiler, SC12 contract, or tracked output file was changed by A1. Generated artifacts were written only under `C:\tmp\vissim-a1-check`.

## Schema and API

### `vissim-lane-graph-v2.1`

Canonical CLI:

```text
python -B scripts/build_vissim_lane_graph.py --inpx INPUT.inpx --output OUTPUT.json
```

Library API:

- `build_lane_graph(manifest) -> artifact`
- `semantic_payload(artifact) -> semantic graph payload`
- `atomic_write_json(path, artifact)`
- `load_graph(path) -> artifact`

The artifact contains:

- provenance: INPX SHA-256, canonical compiler/topology hash, signal-reference-v2.1 compiler hash;
- command version, source hashes, command hash, canonical JSON version, semantic hash scope;
- status/reasons, dimensions, units, downstream consumers, production gates;
- `links`: numeric ID, length, lane count/IDs, exact source/destination coordinates;
- `nodes`: stable `lane:<link_no>:<lane_no>` IDs for road and connector lanes;
- `connectors`: exact endpoint links/positions, length, lane count, coordinates, and lane mapping;
- `edges`: one source-lane to connector-lane entry and one connector-lane to destination-lane exit per connector lane;
- `signal_heads`: `(SC, SG, head, link, lane, pos)` and raw canonical references.

Graph semantic SHA-256 excludes byte/provenance ordering metadata and covers schema, links, nodes, edges, connectors, and signal heads.

### `lane-route-proofs-v2.1`

Canonical CLI:

```text
python -B scripts/resolve_lane_routes.py --inpx INPUT.inpx --graph GRAPH.json --output OUTPUT.json
```

Library API:

- `parse_relative_flow(raw) -> lossless flow evidence and numeric supports`
- `parse_static_routes(inpx) -> sorted active decisions/routes`
- `resolve_route_paths(route, graph) -> all finite directed path proofs or reason`
- `compile_route_proofs(inpx, graph) -> artifact`

The resolver walks exact `(lane_id, position_m)` states through the explicit sequence. Adjacent evidence is used directly; omitted intermediate objects are reached by finite directed-state search with per-path visited states and no arbitrary hop cap. Road-lane changes are evidence records and never alter connector-node degree. Reverse and upstream transitions are rejected.

Every proof preserves route/raw XML evidence, lane IDs, graph edge IDs, lane-change evidence, physical segment/path length, terminal, first downstream stopline or terminal, and normalized route/path shares. Empty `relFlow` preserves its source representation and uses the repository's VISSIM default `1.0`. Negative and non-finite flow is rejected. Input/graph SHA mismatch is a production failure.

Both CLIs write a same-directory temporary file, flush/fsync it, then atomically replace the requested output.

## Real-network result

Input:

- `network/real_world_gaepo_modi/modi_eval_rw_control.inpx`
- SHA-256: `f3ce390f281c2bd60a367435dd5567767edafb4681cb66a2c566a480aa74d635`
- Canonical topology hash: `50a9541de3556bd39544701711fca896a1321544686692f0dc4e8bad22dcbc90`
- Canonical compiler: `vissim-strict-phase0/1.1.1`
- Signal reference: `signal-reference-v2.1`

Graph:

- status: PASS
- road links: 448
- connector links: 771
- lane nodes: 2,649
- connector lanes: 1,396
- directed connector edges: 2,792
- signal heads: 541
- unresolved connector mappings: 0
- reverse synthetic edges: 0
- executable connector paths: 1,396 / 1,396
- executable connector path coverage: 100%
- semantic SHA-256: `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3`
- command hash: `2176923ea909c228cc20ee89e9555e636cf030ae1431761d51a1eb2b73ecd9a7`

Route proofs:

- status: PASS
- active static routing decisions parsed: 130
- active static routes parsed: 339
- executable exact-lane proofs: 585
- required connector lanes represented: 1,067
- unresolved routes: 0
- reverse synthetic edges: 0
- graph executable connector coverage: 100%
- maximum route/path normalized-flow error: `1.1102230246251565e-16`
- proofs with recorded lane changes: 83; lane-change events: 96
- first downstream signal head: 466 proofs; terminal: 119 proofs
- semantic SHA-256: `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32`
- command hash: `f0e5df6b1cd87f6dc7757bf754b2394880f8c30668103d458512b2e4e4dd7bf6`

SC12 exact mappings remained:

- 10241 lanes 1/2: `1220012103` lanes 1/2 to `1220013700` lanes 1/2.
- 10242 lane 1: `1220012103` lane 2 to `1220015100` lane 3.
- 10238 lanes 1/2: `1220013600` lanes 1/2 to `1220012003` lanes 1/2.
- 10240 lane 1: `1220013600` lane 2 to `1220012600` lane 3.

## Ten shuffled-order compiles

The real canonical manifest's links, connectors, connector lanes/mappings, and signal heads were independently shuffled with seeds 0 through 9. Each resulting graph was compiled, then its nodes, edges, connectors, and heads were independently shuffled before route-proof compilation.

| Seed | Graph semantic SHA-256 | Route semantic SHA-256 |
|---:|---|---|
| 0 | `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3` | `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32` |
| 1 | `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3` | `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32` |
| 2 | `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3` | `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32` |
| 3 | `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3` | `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32` |
| 4 | `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3` | `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32` |
| 5 | `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3` | `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32` |
| 6 | `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3` | `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32` |
| 7 | `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3` | `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32` |
| 8 | `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3` | `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32` |
| 9 | `cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3` | `c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32` |

Unique graph hashes: 1. Unique route hashes: 1.

## Commands and results

Python runtime used: `C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

```text
python -B -m unittest -v scripts.tests.test_vissim_lane_graph scripts.tests.test_vissim_lane_graph_real_network
```

Result: PASS, 12 tests, 32.809 s in the final combined run.

```text
python -B scripts/build_vissim_lane_graph.py --inpx network/real_world_gaepo_modi/modi_eval_rw_control.inpx --output C:\tmp\vissim-a1-check\vissim_lane_graph_v2_1.json
```

Result: `status=PASS nodes=2649 edges=2792 coverage=1.000000000000 hash=cddaa612d5a669458edcfaf4bbed6260f72437638829aa3316e9b8e4d718ede3`.

```text
python -B scripts/resolve_lane_routes.py --inpx network/real_world_gaepo_modi/modi_eval_rw_control.inpx --graph C:\tmp\vissim-a1-check\vissim_lane_graph_v2_1.json --output C:\tmp\vissim-a1-check\lane_route_proofs_v2_1.json
```

Result: `status=PASS routes=339 proofs=585 unresolved=0 flow_error=1.11e-16 hash=c3aa5e278f8ca218f9d6971e42fd2d1973058a763a160ce481bc747697f05a32`.

Cache-free `compile()` syntax checks passed for all four Python files. The two temporary artifacts were 2,397,962 and 1,745,813 bytes. No tracked output was refreshed.

## Self-review and remaining concerns

- Connector/head semantics come only from the current canonical compiler manifest and signal-reference-v2.1; there is no conflicting XML connector/head parser.
- Connector lanes have exactly two directed graph edges. No graph reverse edge is synthesized.
- Canonical numeric sort keys are used for object IDs, lane numbers, positions, route IDs, and proof IDs; list/XML iteration order is not a tie-breaker.
- Missing canonical validation, signal-reference-v2.1 evidence, input hashes, graph semantic hash, or matching graph/route input hash produces `FAIL` rather than `PASS`.
- Directed sparse-waypoint search has no arbitrary hop cap and rejects repeated lane-position states per path. As with any all-path compiler, a deliberately sparse route in a highly cyclic network can have a large simple-path result set; this is intrinsic to retaining all valid paths rather than selecting one.
- Lane-change evidence uses forward available distance and exact connector lane ranges. A1 does not contain calibrated VISSIM lane-change behavior parameters, so no unsupported minimum lane-change-distance threshold is invented.
- Path shares are equal within a route because the INPX supplies route flow but no lane-path allocation evidence. The artifact records `path_share_basis=equal_share_without_lane_demand_evidence`; normalized shares pass the required tolerance.

No blocking concern remains for A1.

---

## Fix Round 1/5 - 2026-08-06

Status: DONE

This section supersedes the earlier A1 proof count, semantic hashes, command versions,
and command hashes. The input network and SC12 contract are unchanged.

### Review findings closed

#### C1 - exact connector universe, mapping, orientation, position, and degree

- Expected connector lanes now come from the declared connector `lane_count` range and
  exact connector lane nodes, never from `lane_mapping` itself.
- Declared node IDs/numbers must equal `lane:<connector_no>:1..N` one-to-one.
- Every expected lane requires exactly one mapping. Missing, duplicate, and unexpected
  mappings fail.
- Mapping endpoints must exactly equal the connector endpoint link/lane ranges. An exact
  source/destination reversal is separately counted by `reverse_synthetic_edges`.
- Entry/exit edges are validated against exact endpoint links, lane numbers, connector
  length, source/destination positions, and stable IDs.
- Every connector node must have exactly one incoming entry, one outgoing exit, and two
  total incident edges.
- Added false-PASS fixtures for deleted mapping, duplicate mapping, missing declared node,
  swapped mapping, and endpoint reversal.

#### C2 - per-input-state explicit waypoint reachability

- Explicit connector transitions now evaluate exact transition and forced lane-change
  fallback independently for each input lane-position state.
- A valid transition from one state no longer suppresses a valid fallback from another.
- Sparse-waypoint search likewise evaluates unresolved states independently.
- The explicit versus sparse one-lane connector fixture now preserves the same two start
  lane paths. The existing two-route fixture grew from two to four proofs because each
  route now retains both executable start-lane paths.

#### C3 - closed nodes and physical lane-change distance

- Closed current, source, connector target, exit target, and terminal nodes are rejected.
- A lateral lane change requires `available_distance_m > 1e-6 m`; zero-distance and
  tolerance-scale lateral jumps fail.
- Every accepted lane-change event includes the exact entry edge, source lane, source
  position, and positive available distance as canonical evidence.
- Added source-closed, connector-closed, target-closed, and zero-distance fixtures.

#### I1 - lossless and validated `relFlow`

- `relFlow` attribute absence is represented as `None` and fails as missing evidence.
- Explicit `relFlow=""` remains distinct, preserves raw empty text, and uses the existing
  VISSIM default `1.0` contract.
- Scalar numeric encoding remains supported. Time-supported encoding requires the observed
  VISSIM prefix token `2`; arbitrary prefixes such as `bogus-prefix` fail.
- Raw text, prefix tokens, `time_raw`, `value_raw`, and attribute-presence evidence are
  preserved.
- Real network evidence remains 192 nonempty and 147 explicit-empty attributes, with zero
  missing attributes.

#### I2 - supplied graph integrity closure

- `validate_lane_graph_artifact()` runs before any route resolution.
- It recomputes and compares the semantic SHA-256 and validates schema, canonical JSON
  version, PASS status, empty reasons, all required production gates, dimensions,
  top-level canonical ordering, nested link lane ordering, nested connector mapping
  ordering, exact mapping/edge evidence, and connector node degree.
- Invalid graphs are not passed to `resolve_route_paths`; route artifacts still fail closed
  with explicit reasons.
- Added stale hash, wrong schema, FAIL status/reasons, missing gate, noncanonical ordering,
  and recomputed-hash invalid-degree fixtures.

#### I3 - actual XML shuffle and multipath shares

- The real-network ten-shuffle test now parses and rewrites the INPX while independently
  shuffling actual `vehicleRoutingDecisionStatic` and `vehicleRouteStatic` XML children.
- All ten temporary INPX files have distinct byte SHA-256 values. All ten route compiles
  produce one semantic hash. Temporary files remain outside tracked outputs.
- The single-route sparse fixture compiles end to end to eight paths, each with path share
  `0.125`; the path shares sum to exactly `1.0` within test precision.
- Real proof shares continue to sum to one per decision/time support within `1e-9`.

#### M1 - transitive behavioral command hashes

Graph command version is `build-vissim-lane-graph/2.1.1`; route command version is
`resolve-lane-routes/2.1.1`. Both command hashes record repository-relative source hashes
for their behavioral dependency closure:

- `scripts/build_vissim_lane_graph.py`
- `scripts/resolve_lane_routes.py` for the route compiler
- `plant/src/vissim_strict/compiler.py`
- `plant/src/vissim_strict/topology.py`
- `plant/src/vissim_strict/contraction.py`
- `plant/src/vissim_strict/signal_program.py`

Final graph command hash:
`8a85a0e1c7d3925f8d274224aa02933798ce84b3ee1ea4935ee22e7bb741a37e`.

Final route command hash:
`39a6f9bd262797f1b284bad595e02e80fc69009b963cb1dd67e1ffa77546e1fa`.

### Final real-network evidence

Input SHA-256 remains
`f3ce390f281c2bd60a367435dd5567767edafb4681cb66a2c566a480aa74d635`.

Graph:

- status: PASS
- road links: 448
- connector links: 771
- lane nodes: 2,649
- connector lanes: 1,396
- exact directed connector edges: 2,792
- signal heads: 541
- unresolved connector mappings: 0
- reverse synthetic edges: 0
- executable connector coverage: 1,396 / 1,396 = 100%
- standalone supplied-artifact validator failures: 0
- semantic SHA-256:
  `6356d9e72436334426ddaaee6a19eda753ef07767e85ae8ce02483c22147274c`

Routes:

- status: PASS
- active static decisions: 130
- active static routes: 339
- unresolved routes: 0
- exact lane-path proofs: 1,255
- required connector lanes represented: 1,086
- executable graph connector coverage: 100%
- reverse synthetic edges: 0
- maximum normalized route/path flow error: `1.1102230246251565e-16`
- semantic SHA-256:
  `6f967fd58ddfb18ad06b4ad465024d363340cc483551685a8a3c5160cab9cda8`

The proof count increase from 585 to 1,255 is expected C2 behavior: previously omitted
per-state explicit lane-change paths are now retained and receive normalized shares.

SC12 exact connector mappings remain unchanged for 10241, 10242, 10238, and 10240.
The dedicated SC12 regression passed.

Ten actual XML-order shuffled compiles produced:

- unique shuffled input byte hashes: 10
- unique graph semantic hashes: 1, always
  `6356d9e72436334426ddaaee6a19eda753ef07767e85ae8ce02483c22147274c`
- unique route semantic hashes: 1, always
  `6f967fd58ddfb18ad06b4ad465024d363340cc483551685a8a3c5160cab9cda8`

### Commands and results

```text
python -B -m unittest -v scripts.tests.test_vissim_lane_graph scripts.tests.test_vissim_lane_graph_real_network
```

Result: PASS, 21 tests, 43.352 s.

```text
python -B -m unittest discover -s scripts/tests -p test_*.py
```

Final result: PASS, 116 tests, 174.164 s.

```text
python -B scripts/build_vissim_lane_graph.py --inpx network/real_world_gaepo_modi/modi_eval_rw_control.inpx --output C:\tmp\vissim-a1-check\vissim_lane_graph_v2_1.json
```

Result:
`status=PASS nodes=2649 edges=2792 coverage=1.000000000000 hash=6356d9e72436334426ddaaee6a19eda753ef07767e85ae8ce02483c22147274c`.

```text
python -B scripts/resolve_lane_routes.py --inpx network/real_world_gaepo_modi/modi_eval_rw_control.inpx --graph C:\tmp\vissim-a1-check\vissim_lane_graph_v2_1.json --output C:\tmp\vissim-a1-check\lane_route_proofs_v2_1.json
```

Result:
`status=PASS routes=339 proofs=1255 unresolved=0 flow_error=1.11e-16 hash=6f967fd58ddfb18ad06b4ad465024d363340cc483551685a8a3c5160cab9cda8`.

Cache-free syntax compilation passed for all four A1 Python files. No tracked artifact was
regenerated; all manual artifacts were written under `C:\tmp\vissim-a1-check`.

### Fix-round self-review

- C1 builder validation and I2 persisted-artifact validation are independent layers: a
  malformed canonical manifest cannot create PASS, and a post-build graph mutation cannot
  be consumed as PASS even if its attacker recomputes the semantic hash.
- Connector mapping deletion, endpoint reversal, synthetic reverse direction, duplicate
  degree, closed-node traversal, zero-distance lateral transition, missing flow evidence,
  bogus encoding, stale hash, missing gates, and noncanonical order now all have explicit
  failing fixtures.
- Route XML ordering is sorted by numeric decision and route IDs; element iteration order
  is never used as a tie-breaker. Link sequence order remains semantic and is not shuffled.
- Transitive source hashes cover every non-stdlib Python module imported into graph compile
  behavior and the canonical JSON hash helper used by both compilers.
- No S0R, baseline, existing compiler, signal program, SC12 contract, or tracked output was
  modified in this fix round.

No blocking concern remains after fix round 1/5.

## Fix round 2/5 - C2/I2/M1 residuals

Date: 2026-08-06 (Asia/Seoul)

### Changed files

- `scripts/build_vissim_lane_graph.py`
- `scripts/resolve_lane_routes.py`
- `scripts/tests/test_vissim_lane_graph.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-a1-report.md` (this appended report)

No S0R file, baseline file, canonical compiler, signal program, SC12 contract, or
tracked output artifact was changed in round 2.

### Schema and API changes

The external graph schema version remains `vissim-lane-graph-v2.1`. Command versions
are now `build-vissim-lane-graph/2.1.2` and `resolve-lane-routes/2.1.2`.

Parent records now carry enough canonical lane evidence to validate every lane node:

- road link records add `object_kind: link` and canonical `lanes` records;
- connector records add `object_kind: connector`, canonical `lane_ids`, and canonical
  `lanes` records;
- each parent lane record preserves `id`, one-based `lane_no`, `width_m`, and `closed`.

`validate_lane_graph_artifact()` now validates the complete semantic closure before a
supplied artifact can be used:

- exact schema/canonical order/status/reasons/gates/semantic hash;
- unique link, connector, node, edge, and stopline IDs;
- exact parent object ID/type/lane range/lane count/length/coordinates/closed semantics;
- one-to-one node completeness with no orphan or unknown-parent lanes;
- exact connector mapping and edge universes, endpoint existence, kind, direction,
  position bounds, and connector-lane entry-1/exit-1 degree;
- finite nonnegative parent lengths, lane widths, endpoint/edge/stopline positions,
  with strict parent-length upper bounds;
- stopline object/lane identity and position within either a road or connector parent;
- exact dimensions for road links, connectors, nodes, connector lanes, edges, and heads.

The route resolver now checks decision and terminal positions against parent record
lengths, not independently mutable node lengths. A rehashed mutation changing only
`lane:2:1.length_m` from 100 m to 1000 m fails validation, and a route with
`destPos=500` cannot produce a proof.

### C2 state-local transition support

`_transition_to_object()` now explores both the exact mapped transition and every
positive-distance mapped lane-change transition for each input state. Results are
deterministically deduplicated by observable reachability state: start lane, current
lane/position, physical distance, and first reached stopline evidence. Intermediate
explicit waypoints apply this stable state dedupe; final sparse destination resolution
retains its complete directed path support.

The required two-lane source plus two-lane connector fixture now has identical explicit
and sparse support:

- explicit paths: 4, two from each start lane;
- sparse paths: 4, two from each start lane;
- end-to-end single-route path shares: four values of `0.25`, sum `1.0`.

This state equivalence also prevents non-semantic history multiplication on long explicit
routes. Real route `1110:1` (53 explicit objects) resolves deterministically to two
observable supports rather than multiplying equivalent intermediate histories.

### M1 executable dependency closure

The graph command conservatively hashes `plant/src/__init__.py`, every sorted
`plant/src/vissim_strict/**/*.py` source, and the graph script. The route command adds
the route script. Tests assert exact equality with this required closure.

Graph closure: 13 files. Graph command hash:
`6bf3e55bec6de76b12af4dcfd2eaa5c95ba7cc7f370d3a344a3e94f310b3f206`.

Route closure: 14 files. Route command hash:
`c03a3a05341cc4753b58a3b13cce5588b6580993d772dc8a2972c58aaee826f0`.

The graph closure is exactly:

- `plant/src/__init__.py`
- `plant/src/vissim_strict/__init__.py`
- `plant/src/vissim_strict/bridge.py`
- `plant/src/vissim_strict/compiler.py`
- `plant/src/vissim_strict/contraction.py`
- `plant/src/vissim_strict/hybrid.py`
- `plant/src/vissim_strict/observation.py`
- `plant/src/vissim_strict/plant.py`
- `plant/src/vissim_strict/schema.py`
- `plant/src/vissim_strict/shadow.py`
- `plant/src/vissim_strict/signal_program.py`
- `plant/src/vissim_strict/topology.py`
- `scripts/build_vissim_lane_graph.py`

### Final real-network evidence

Graph:

- status: PASS; standalone validator failures: 0
- road links: 448; connector links: 771
- lane nodes: 2,649; connector lanes: 1,396
- directed connector edges: 2,792; signal heads: 541
- unresolved connector mappings: 0; reverse synthetic edges: 0
- executable connector coverage: 1,396 / 1,396 = 100%
- semantic SHA-256:
  `6c3671b8e6c5bbc801aff359722e9f62ac6ed653c956d1f4f1a5f857240b670b`

Routes:

- status: PASS
- active static decisions: 130; active static routes: 339
- executable lane-path proofs: 2,684
- required connector lanes represented: 811
- unresolved routes: 0; reverse synthetic edges: 0
- executable graph connector coverage: 100%
- maximum normalized flow/path share error: `1.1102230246251565e-16`
- semantic SHA-256:
  `3060c3832d89db4a13f03c4690cd2820a7b44fface6f7af2ac7dd584b9e5d512`

The proof count increase from round 1's 1,255 to 2,684 is expected C2 behavior. Exact
mapped transitions no longer suppress positive-distance lane-change support from the
same input state.

SC12 connector mappings 10241, 10242, 10238, and 10240 remain byte-semantically
unchanged and the dedicated regression passed.

Ten actual XML-order shuffled compiles produced:

- unique shuffled input byte hashes: 10
- unique graph semantic hashes: 1, always
  `6c3671b8e6c5bbc801aff359722e9f62ac6ed653c956d1f4f1a5f857240b670b`
- unique route semantic hashes: 1, always
  `3060c3832d89db4a13f03c4690cd2820a7b44fface6f7af2ac7dd584b9e5d512`

### Commands and results

```text
python -B -m unittest scripts.tests.test_vissim_lane_graph -v
```

Final result: PASS, 16 tests, 0.311 s. This includes the 2x2 C2 fixture, rehashed
road/connector length and closed-type contradictions, orphan/duplicate IDs, null
collections, unknown/reversed/unsupported/negative edge evidence, out-of-range stopline,
dimension tamper, and exact M1 closure checks.

```text
python -B -m unittest scripts.tests.test_vissim_lane_graph_real_network -q
```

Final result: PASS, 6 tests, 50.819 s, including SC12 and ten actual route XML shuffles.

```text
python -B -m unittest discover -s scripts/tests -p test_*.py -q
```

Final result: PASS, 117 tests, 197.558 s.

```text
python -B scripts/build_vissim_lane_graph.py --inpx network/real_world_gaepo_modi/modi_eval_rw_control.inpx --output %TEMP%\vissim-a1-round2\vissim_lane_graph_v2_1.json
```

Result:
`status=PASS nodes=2649 edges=2792 coverage=1.000000000000 hash=6c3671b8e6c5bbc801aff359722e9f62ac6ed653c956d1f4f1a5f857240b670b`.

```text
python -B scripts/resolve_lane_routes.py --inpx network/real_world_gaepo_modi/modi_eval_rw_control.inpx --graph %TEMP%\vissim-a1-round2\vissim_lane_graph_v2_1.json --output %TEMP%\vissim-a1-round2\lane_route_proofs_v2_1.json
```

Result:
`status=PASS routes=339 proofs=2684 unresolved=0 flow_error=1.11e-16 hash=3060c3832d89db4a13f03c4690cd2820a7b44fface6f7af2ac7dd584b9e5d512`.

The first manual CLI attempt targeted `C:\tmp\vissim-a1-round2`, but this environment's
ACL denied creation of a sibling directory under `C:\tmp`. The identical command was
rerun successfully under `%TEMP%\vissim-a1-round2`. No tracked output was written.

### Round 2 self-review and remaining concerns

- C2 exact and positive-distance lane-change transitions are evaluated for every input
  state before stable semantic dedupe. Closed nodes and zero-distance lateral jumps remain
  rejected.
- I2 no longer trusts a rehashed but contradictory graph. Parent/node, mapping/edge,
  stopline, dimensions, and destination bounds form one fail-closed validation closure.
- Validator malformed-collection/type paths return FAIL reasons instead of raising.
- M1 closure is generated from the executable package tree and asserted exactly in tests;
  package initializers cannot drift without changing both command hashes.
- The full 117-test regression and real-network 10-shuffle compile passed after the final
  self-review changes.

No blocking or known behavioral concern remains after fix round 2/5.

## Fix round 3/5 - I2 stopline identity residual

Date: 2026-08-06 (Asia/Seoul)

### Changed files

- `scripts/build_vissim_lane_graph.py`
- `scripts/resolve_lane_routes.py`
- `scripts/tests/test_vissim_lane_graph.py`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-a1-report.md` (this appended report)

No S0R, baseline, canonical compiler, signal program, SC12 contract, real-network
fixture, or tracked output artifact was changed.

### Schema and API

The graph schema remains `vissim-lane-graph-v2.1`. Command versions are now
`build-vissim-lane-graph/2.1.3` and `resolve-lane-routes/2.1.3`.

`validate_lane_graph_artifact()` now requires every signal head to have:

- a non-null, non-empty canonical positive integer `signal_controller_no`;
- a non-null, non-empty canonical positive integer `signal_group_no`;
- a non-null, non-empty canonical positive integer `head_no`;
- stable artifact ID `signal-head:<normalized head_no>`;
- globally unique normalized `head_no` and unique `(SC, SG, head)` identity;
- the already-required unique artifact ID and exact canonical parent object/lane/position
  relationship, with finite nonnegative position within the parent length.

Accepted identity representations are positive Python integers or canonical ASCII decimal
strings without signs, whitespace, decimal points, or leading zeroes. Booleans, zero,
negative values, floats, nulls, empty strings, and nonnumeric strings fail closed.

The first-stopline proof API adds `signal_head_id`. A stopline proof now preserves only
the validated stable identity and physical reference fields:

- `signal_head_id`
- `signal_controller_no`
- `signal_group_no`
- `head_no`
- `lane_id`
- `position_m`

plus `kind` and `distance_from_decision_m`. Raw or unvalidated signal references are not
copied into route proofs.

### Regression evidence

The fixture graph was independently rehashed after each of these mutations:

- `signal_controller_no`: `None`, empty string, nonnumeric string;
- `signal_group_no`: `None`, empty string, nonnumeric string;
- `head_no`: `None`, empty string, nonnumeric string;
- duplicate stable head record and duplicate normalized signal identity.

For all ten cases, direct `validate_lane_graph_artifact()` returned
`invalid_lane_graph_stopline_identity`; valid-route compilation returned `FAIL` with no
proofs and the same reason code. Recomputing the semantic hash cannot make malformed
identity evidence usable.

The valid fixture proof is pinned to
`signal-head:501 / SC 12 / SG 3 / head 501 / lane:2:1 / 60.0 m`, with an exact allowed
field set.

### Real-network evidence and determinism

Graph:

- status: PASS; validator failures: 0
- road links: 448; connector links: 771
- lane nodes: 2,649; connector lanes: 1,396
- directed connector edges: 2,792; validated signal heads: 541
- unresolved connector mappings: 0; reverse synthetic edges: 0
- executable connector coverage: 1,396 / 1,396 = 100%
- semantic SHA-256:
  `6c3671b8e6c5bbc801aff359722e9f62ac6ed653c956d1f4f1a5f857240b670b`

Routes:

- status: PASS
- active static decisions: 130; active static routes: 339
- executable lane-path proofs: 2,684
- required connector lanes represented: 811
- unresolved routes: 0; reverse synthetic edges: 0
- executable graph connector coverage: 100%
- maximum normalized flow/path share error: `1.1102230246251565e-16`
- stopline proofs: 2,315; graph-head identity mismatches: 0
- semantic SHA-256:
  `4ee8f2cfc2c61388f7a51e799e935120ce14d96e7bcc3e73942d82146bf1735a`

The graph semantic hash is unchanged because valid graph semantics did not change. The
route semantic hash changed because every stopline proof now includes stable
`signal_head_id`.

Ten actual decision/route XML-order shuffled compiles produced ten distinct input byte
hashes, one graph semantic hash (always
`6c3671b8e6c5bbc801aff359722e9f62ac6ed653c956d1f4f1a5f857240b670b`), and one route
semantic hash (always
`4ee8f2cfc2c61388f7a51e799e935120ce14d96e7bcc3e73942d82146bf1735a`).

SC12 connectors 10241, 10242, 10238, and 10240 remain unchanged and their dedicated
regression passed.

### Command provenance

The exact M1 dependency closures remain 13 graph files and 14 route files. Final command
hashes are:

- graph: `f60f931a57b7b4ed62f7b0927af69a2297ee96cc1704e376d511bad8ebe54edd`
- route: `9e497ef5373ac7da71929e7e72bbfcf859692f1847ee198d831d184a775397dc`

### Commands and results

```text
python -B -m unittest scripts.tests.test_vissim_lane_graph -v
```

Result: PASS, 18 tests, 0.415 s.

```text
python -B -m unittest scripts.tests.test_vissim_lane_graph_real_network -v
```

Result: PASS, 6 tests, 50.613 s, including 339 routes, SC12, 100% connector coverage,
normalized shares, and ten actual XML-order shuffled compiles.

```text
python -B -m unittest discover -s scripts/tests -p test_*.py -q
```

Result: PASS, 119 tests, 197.674 s.

```text
python -B scripts/build_vissim_lane_graph.py --inpx network/real_world_gaepo_modi/modi_eval_rw_control.inpx --output %TEMP%\vissim-a1-round3\vissim_lane_graph_v2_1.json
```

Result:
`status=PASS nodes=2649 edges=2792 coverage=1.000000000000 hash=6c3671b8e6c5bbc801aff359722e9f62ac6ed653c956d1f4f1a5f857240b670b`.

```text
python -B scripts/resolve_lane_routes.py --inpx network/real_world_gaepo_modi/modi_eval_rw_control.inpx --graph %TEMP%\vissim-a1-round3\vissim_lane_graph_v2_1.json --output %TEMP%\vissim-a1-round3\lane_route_proofs_v2_1.json
```

Result:
`status=PASS routes=339 proofs=2684 unresolved=0 flow_error=1.11e-16 hash=4ee8f2cfc2c61388f7a51e799e935120ce14d96e7bcc3e73942d82146bf1735a`.

All manual artifacts were written under `%TEMP%\vissim-a1-round3`; tracked outputs were
not regenerated.

### Round 3 self-review and remaining concerns

- Identity validation occurs before route resolution; any malformed supplied graph makes
  `graph_usable` false, emits no proofs, and preserves explicit failure reasons.
- Numeric normalization prevents alternate string spellings from bypassing stable ID or
  duplicate checks.
- Generic artifact-ID uniqueness and normalized head/triple uniqueness are independent,
  so both exact duplicate records and identity aliases fail.
- Parent lane/link/position validation remains in the same stopline loop and all previous
  C1/C2/C3/I1/I2/I3/M1 tests continue to pass.
- All 2,315 real stopline proofs match one of the 541 validated graph identities exactly.

No blocking or known behavioral concern remains after fix round 3/5.
