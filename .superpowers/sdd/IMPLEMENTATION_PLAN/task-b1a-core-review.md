# B1a Core/Provenance Independent Review

## Verdict

**FAIL**

Findings: **Critical 2 / Important 4 / Minor 1**.

The reviewed core package exactly matches `review-b1a-core.diff` by Git blob hash. No
implementation file was edited. This review includes the current VBS state after its
concurrent zero-key update (`run_real_world_stackelberg_controller.vbs` blob
`39ae9c4caced89b832a2b002365ac1598be14027`).

## Critical Findings

### C1. The approval is replayable, but it is not an independent A2 trust anchor

**Locations:**

- `plant/src/vissim_strict/physical_projection.py:400-453`
- `plant/src/vissim_strict/physical_projection.py:563-615`
- `scripts/approve_physical_stock_topology.py:174-315`
- `scripts/approve_physical_stock_topology.py:318-380`
- `scripts/approve_physical_stock_topology.py:443-483`

`validate_physical_stock_topology()` checks that `input_hashes` and `command_version`
are objects, but does not validate their required names/values, producer identity, or
their relationship to the preflight inputs. It does not require or validate
`canonical_json_version` or `command`. Owner/visibility fields are checked only for
local syntactic closure; they are not replayed against ownership/adjacency evidence.
The approval producer then accepts this result and binds the newly changed topology
bytes. The preflight validator also accepts any internally consistent nonempty PASS
check list and hash universe instead of the required preflight contract.

This permits a topology to change behavioral owner/view semantics, recompute its own A2
semantic hash, and receive a new external `topology-approval-v2.1` PASS while the
declared evidence is unchanged. The approval artifact itself also accepts an arbitrary
rehashable `command_version`, and accepts noncanonical equivalent root spellings rather
than the required `".."`.

**Independent reproducers:**

1. Starting from the provenance test's compiler-produced topology, replace the first
   stock's owner with `{"attacker:owner": 1.0}`, replace `visible_to` accordingly,
   recompute `topology.semantic_sha256`, write the topology, and run `approve_main`.

   ```text
   owner_before={'urban:1': 1.0}
   owner_after={'attacker:owner': 1.0}
   approval_exit=0
   approval_status=PASS
   ```

2. Mutate A2 `canonical_json_version`, `input_hashes`, `command_version`, and `command`
   without changing any semantic-scope field. The A2 semantic hash remains unchanged;
   approval again exits 0 with PASS.

3. A coherently rehashed mutation matrix rejected `status`, units, and an interval gap,
   but accepted `command_version`, `input_hashes`, an extra sample dimension, a stock
   edge endpoint position inconsistent with its stock, and a malformed route-membership
   record. A separately rehashed approval accepted arbitrary `command_version` and
   `workspace_root_relative_to_artifact="../outputs/.."`.

This contradicts the report's claims at
`.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-core-report.md:164-166` that rehashed
structural tampering fails and repeated self-declared hashes cannot mask topology
tampering.

### C2. Large standard JSON integers escape typed validation and preserve stale PASS outputs

**Locations:**

- `plant/src/vissim_strict/physical_projection.py:351-356`
- `scripts/build_state_manifest_v2_1.py:109-115`
- `scripts/approve_physical_stock_topology.py:596-627`
- `scripts/build_state_manifest_v2_1.py:562-569`
- `scripts/validate_state_projection_v2_1.py:325-326`
- `scripts/validate_state_projection_v2_1.py:492-500`

Both finite-number helpers call `float(value)` without catching `OverflowError`. A
400-digit integer is valid standard JSON and parses as a Python integer, but conversion
to binary64 raises `OverflowError`. The approval, manifest, and projection CLI exception
boundaries do not catch it. Therefore no deterministic FAIL artifact is written, and a
pre-existing PASS output/sidecar survives.

**Independent reproducers:**

- A state with `speed_kph=10**400` can be included in a freshly built PASS manifest.
  Validation then raises `OverflowError`; both preseeded audit and sidecar remain
  exactly `{"status":"STALE_PASS"}`.
- A rehashed topology with `length_m=10**400` makes approval raise `OverflowError` and
  leaves a preseeded approval PASS untouched.
- A rehashed selection with `sim_sec=10**400` makes manifest construction raise
  `OverflowError` and leaves a preseeded manifest PASS untouched.

This violates strict finite-double rejection, typed projection failure, deterministic
FAIL evidence, and stale-output replacement.

## Important Findings

### I1. Optional envelope absence masks independent state/run trust failures

**Locations:**

- `scripts/validate_state_projection_v2_1.py:294-340`
- `scripts/validate_state_projection_v2_1.py:341-349`
- `scripts/validate_state_projection_v2_1.py:395-418`

`_process_state()` accumulates exact state-hash/run-provenance failures, but if
`vehicle_records` is absent it chooses status solely from `required_vehicle_records`.
For `false`, the state becomes `NOT_EVALUATED` even when `reasons` already contains
`topology_trust_mismatch`. `build_audit()` only treats state status `FAIL` as failure.

**Independent repro:** build a valid optional/no-envelope manifest, then alter the state
bytes (`total_vehicles=99`). Validation returned exit 2, audit `NOT_EVALUATED`, and
sidecar `NOT_EVALUATED`, while the sidecar reasons contained both
`topology_trust_mismatch` and `live_com_not_evaluated`. Exact byte/provenance failure
must remain FAIL; only the authorized envelope absence may be NOT_EVALUATED.

### I2. Nested preflight source paths are not workspace-contained

**Locations:**

- `scripts/approve_physical_stock_topology.py:222-251`
- `scripts/approve_physical_stock_topology.py:278-287`
- Contrast `plant/src/vissim_strict/physical_projection.py:294-311`

Approval source paths are contained correctly, but artifact and signal-program paths
inside the preflight are resolved and hashed without `relative_to(workspace_root)` or
`resolve_contained_path()`. An internally consistent preflight can therefore bind an
external file and still receive approval.

**Independent repro:** move the preflight fixture's sole artifact to a sibling directory
outside the workspace, update its byte evidence/input hash/fingerprint, and approve.

```text
outside_is_contained=False
approval_exit=0
approval_status=PASS
```

Absolute child rejection passed, and a Windows junction from inside the workspace to an
outside directory was independently rejected by `resolve_contained_path`; the defect is
specific to these nested preflight paths.

### I3. The projection validator's PASS/exit-0 branch is unreachable

**Locations:**

- `scripts/validate_state_projection_v2_1.py:395-418`
- `scripts/validate_state_projection_v2_1.py:444-447`
- `scripts/validate_state_projection_v2_1.py:501-502`

For every state set without a FAIL, `build_audit()` unconditionally assigns
`NOT_EVALUATED` and hardcodes both live gates to that value. There is no input or code
path that can make this producer emit PASS, so the advertised exit mapping contains
dead exit 0 behavior. A valid projected state returns 2, and an empty selection returns
2; ordinary failures return 1.

The report correctly labels the slice nonpromotable, but this is more than absent live
evidence: the sole specified validator has no route to consume later PASS evidence.

### I4. Current VBS states cannot satisfy the core run-manifest contract

**Locations:**

- `scripts/run_real_world_stackelberg_controller.vbs:1488`
- `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:300-327`
- `scripts/build_state_manifest_v2_1.py:299-305`
- `scripts/build_state_manifest_v2_1.py:349-367`

The current VBS root emits `run_id` and `manifest_path`, but no `manifest_sha256`. The
current runner target is a schema-1 mutable provenance artifact, while the manifest
producer requires `run-manifest-v2.1`, an exact approved-topology binding, configuration,
and the state's exact manifest hash. Thus a current runner-produced state cannot be
materialized by the B1a state-manifest producer without another implementation change.

The requested `vehicle_records` interface itself now matches: the current VBS inserts a
zero stopped-count key for every observed link at
`run_real_world_stackelberg_controller.vbs:1832-1835`, and its behavior test passes the
emitted envelope directly through `normalize_vehicle_records`. UTF-8 no-BOM emission is
also correct, while Python source-file loading intentionally accepts a BOM via
`physical_projection.py:258-262`; the independent BOM read passed.

## Minor Finding

### M1. The checked-in performance test does not reproduce the reported timing scope

**Locations:**

- `plant/tests/test_vissim_strict_physical_projection.py:411-426`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-core-report.md:145-160`

The test starts its clock after the explicit state-byte serialization, performs no
strict file parse, stops before sidecar serialization/write, and then checks the file
size outside the timer. `hash_context()` does perform an additional in-memory JSON
serialization and normalization during the timed call, so the test is still useful as
a projection-core guard, but it does not reproduce the report's named
`serialize_parse_project_write_sec` scope. No replay command for that separate metric is
included. The report correctly avoids claiming live COM/p95 qualification.

## Verified Behaviors

- Exact interval rules passed independently: internal split values route strictly by
  half-open boundaries; only `-tol..0` and `lane_end..lane_end+tol` snap; both inclusive
  outer tolerance endpoints pass and just-outside values reject.
- Same vehicle at later time and across runs is accepted; same-snapshot duplicates,
  run/time mismatch, unknown lane, aggregate count/total mismatch, and stopped
  derivation mismatch reject.
- Current VBS full count/stopped maps include the moving-link zero key; empty maps remain
  `{}`. The stopped equality boundary (`speed_kph == 1.0`) is moving.
- Normalized record and projection hashes are order-independent, while exact ledger
  hashes differ with exact state-file hashes.
- Physical/controller/boundary and owner-partition identities close; roles and
  visibility remain nonpartitioning.
- `ProjectionResult` is deeply immutable; a nested assignment mutation raises
  `TypeError`.
- Duplicate JSON keys and `NaN` reject. Invalid UTF-8 rejects. A UTF-8 BOM source file is
  accepted; emitted sidecars and current VBS states are UTF-8 without BOM.
- Selection/manifest entry closure, required flag copying, ordinary stale-output
  replacement, exact file hashes, canonical sidecar naming, absolute path rejection,
  and junction escape rejection passed, subject to C2 and I1.

## Test Results

```text
Focused B1a core/provenance: 16 passed in 2.620 s
A1/A2 regressions:           54 passed in 115.130 s
Strict compiler regressions:  5 passed in 26.014 s
Current VBS static/behavior: 11 passed in 0.556 s
```

The WSH behavior tests first failed inside the filesystem sandbox because CScript could
not load user settings; the approved normal-environment rerun passed all 11 tests.

## Exit Matrix Observed

| Producer | PASS | FAIL | NOT_EVALUATED | Unhandled valid-JSON overflow |
|---|---:|---:|---:|---:|
| topology approval | 0 | 1 | n/a | exception; stale output survives |
| state manifest | 0 | 1 | n/a | exception; stale output survives |
| projection audit | unreachable | 1 | 2 | exception; stale audit/sidecar survive |

## Required Disposition

1. Make approval replay the complete preflight/A2 provenance and evidence bindings, and
   independently reject behavior-changing A2 mutations even after semantic rehash.
2. Convert numeric conversion overflow into the closed typed reason vocabulary at every
   boundary, and ensure every usable output is replaced.
3. Preserve trust failures as FAIL even for optional missing envelopes.
4. Contain nested preflight source paths, make the live-gate PASS path reachable, and
   align current VBS/runner run provenance with `run-manifest-v2.1`.
5. Add the independent reproducers above to the test suite, including the exact timed
   performance pipeline if that metric remains claimed.
