# A2 fix round 1 independent re-review

## Verdict

**FAIL**

Original findings: **4 ADDRESSED / 0 OPEN**.

Current finding count: **Critical 0 / Important 1 / Minor 0**. The implementation fixes
all four original findings, but the supplied `review-a2-fix1.diff` package cannot be
applied because its paths use invalid backslash separators.

## Original finding disposition

### Critical 1 - ADDRESSED

**Files:**

- `scripts/compile_physical_stock_topology.py:51-60`
- `scripts/compile_physical_stock_topology.py:220-235`
- `scripts/compile_physical_stock_topology.py:715-835`

Production mode now compares normalized ownership, adjacency, capacity, and exact legacy
partition identity hashes to embedded approved anchors. It separately checks the three
raw evidence file hashes and returns the FAIL artifact before partition inference or
stock construction. Fixture mode requires an explicit `expected_evidence_hashes` map.

Independent production mutations used the unchanged approved raw hashes where
applicable:

```text
partition identity swap 10000/10001: FAIL, stocks=0, edges=0
  legacy_partition_identity_hash_mismatch, trusted_evidence_hash_mismatch
fake adjacency urban:999999: FAIL, stocks=0, edges=0
  trusted_evidence_hash_mismatch
doubled jam density: FAIL, stocks=0, edges=0
  trusted_evidence_hash_mismatch
wrong ownership raw SHA-256 only: FAIL, stocks=0, edges=0
  trusted_evidence_file_hash_mismatch
```

A valid synthetic graph compiled without `expected_evidence_hashes` also returned
`FAIL`, `stocks=0`, with `missing_trusted_evidence_hashes`. Its FAIL artifact retained
all required global contract keys.

### Critical 2 - ADDRESSED

**Files:**

- `scripts/compile_physical_stock_topology.py:551-653`
- `scripts/compile_physical_stock_topology.py:1044-1087`

The owner calculation now considers only the nearest routing decision on the stock's own
parent. An independently executed urban direct-owner split produced exactly
`urban:2=0.75` and `urban:3=0.25`, with basis
`a1_local_decision_route_flow_shares` and decision `7`.

Two decisions at the same position with opposing 0.75/0.25 and 0.25/0.75 distributions
returned `FAIL` with `unsupported_multi_decision_owner_weights`; the reason preserved
both conditional distributions instead of combining them.

Production stock
`stock:70:1:67.915467926212969:180.143228351476381` still carries memberships from
decisions 1133/1134/1140, but its owner state is now
`legacy_freeway_bound` with `freeway:2=1.0` and no route-decision denominator list. The
48 route-derived production stocks each cite exactly one decision; no stock combines
those three denominators.

### Important 1 - ADDRESSED

**Files:**

- `scripts/compile_physical_stock_topology.py:678-711`
- `scripts/compile_physical_stock_topology.py:1174-1227`

Both independently inspected PASS and FAIL artifacts contain all exact required
top-level fields:

```text
schema_version, input_hashes, command_version, status, reasons,
sample_dimensions, units, downstream_consumers
```

The production `input_hashes` includes both A1 semantic/raw hashes, all three evidence
semantic/raw hashes, and the legacy partition identity hash. `command_version.sha256`
matches the current compiler bytes. The production semantic hash recomputed exactly and
all recorded evidence raw hashes match the current files.

### Important 2 - ADDRESSED

**Files:**

- `scripts/compile_physical_stock_topology.py:1254-1284`
- `scripts/tests/test_compile_physical_stock_topology.py:310-344`
- `scripts/tests/test_compile_physical_stock_topology_real_network.py:168-188`

SC12 lane 2 has four unique physical stocks. The independently reconstructed through
and left route-covered sets are exactly equal and contain the same two stock IDs:

```text
stock:1220012103:2:0.524808:107.366358943901773
stock:1220012103:2:107.366358943901773:110.663306000000006
```

`objective_evaluation()` was called independently for all four modes with nonuniform
stock values and edge flows. Every result echoed the requested mode; the four serialized
physical traces had one byte sequence and one SHA-256. The
`controller_with_boundary - controller_default` delta and `boundary_only` value both
equaled the exact boundary contribution with zero error.

## New finding

### Important 1 - The fix package uses invalid patch paths and is not applyable

**File:**

- `review-a2-fix1.diff:1`
- `review-a2-fix1.diff:1343`
- `review-a2-fix1.diff:1860`

All three `diff --git`/`+++` paths use quoted Windows backslashes, for example:

```text
diff --git "a/scripts\\compile_physical_stock_topology.py" "b/scripts\\compile_physical_stock_topology.py"
```

A clean-target check fails before applying content:

```text
git apply --check --directory=C:/tmp/a2patchcheck review-a2-fix1.diff
error: invalid path 'C:/tmp/a2patchcheck/scripts\compile_physical_stock_topology.py'
```

The three reconstructed added-file payloads do match the current worktree files
byte-for-byte, so this is a package-path defect rather than an implementation mismatch.
It still blocks consuming the submitted review package and must be regenerated with
canonical forward-slash Git paths.

## Regression verification

- A2 synthetic and real-network suites: **19/19 PASS** in 59.496 s.
- Targeted A1 unit and real-network suites: **24/24 PASS** in 51.106 s.
- Production artifact: PASS, 2,649 lanes, 7,275 stocks, 7,418 edges.
- Independent cover: missing/gap/overlap/nonpositive/duplicate tuple/duplicate ID/orphan
  all 0.
- Semantic hash, command source hash, and three evidence raw hashes all match.
- No new implementation-level Critical or Important regression was found.

## Required disposition

The implementation is acceptable for the four original findings, but fix round 1 is not
deliverable as submitted. Regenerate `review-a2-fix1.diff` with forward-slash paths and
verify it with `git apply --check` against a clean target before marking the round PASS.
