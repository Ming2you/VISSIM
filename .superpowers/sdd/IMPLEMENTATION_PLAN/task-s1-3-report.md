# S1-3 SC12 shared-lane validator implementation report

## Status

DONE_WITH_CONCERNS

The requested implementation is present in exactly these two untracked code files:

- `scripts/validate_sc12_shared_lane.py`
- `scripts/tests/test_validate_sc12_shared_lane.py`

No additional code changes were made after the stop request.

## Implemented contract

- Reads the full compiler `signal-reference-v2.1` JSON through `--reference`.
- Writes an atomic JSON artifact through `--out`.
- Implements `--strict` and `--require-complete`; the latter requires `--strict`.
- Verifies the four requested SC12 signal-head assignments.
- Proves the EB and WB through/left source-stock relationships from each connector's `lane_mapping`.
- Declares one physical stock per upstream VISSIM lane and explicitly sets
  `movement_queue_duplication_allowed=false`.
- Verifies programs 1/2/3 for raw-ms equality of SG2/SG5 and SG1/SG6.
- Labels that equality as `current_profile_bundle_policy` with
  `physical_invariant=false`.
- Includes the mandatory global artifact keys, input SHA-256, checks, reasons, and evidence.
- Includes real compiler integration, mutation-failure, completeness, CLI, and atomic-write tests.

## Verification results

Target suite:

```text
python -B -m unittest scripts.tests.test_validate_sc12_shared_lane -v
Ran 7 tests in 14.674s
OK
```

Full scripts suite:

```text
python -B -m unittest discover -s scripts/tests -p 'test_*.py' -v
Ran 62 tests in 37.209s
OK
```

Additional checks:

- `git diff --check -- scripts/validate_sc12_shared_lane.py scripts/tests/test_validate_sc12_shared_lane.py`: PASS
- AST syntax parse for both files: PASS
- Real compiler artifact result: `PASS=6, FAIL=0, NOT_EVALUATED=0`
- Missing-reference result under strict completeness: `NOT_EVALUATED`, exit code 3
- No Python process remained running at the immediate status check.

## Remaining concerns

1. The independent subagent review was interrupted before it produced
   `task-s1-3-review.md`; therefore task-scoped review approval is still absent.
2. Direct `py_compile` could not create `scripts/__pycache__` because of workspace
   permissions. Both the AST syntax check and executable unittest imports passed,
   so this is an environment/write-location issue rather than an observed syntax error.
3. The two implementation files are untracked and have not been staged or committed.

## Current verdict

Implementation and automated verification: PASS.

Independent review gate: NOT_EVALUATED due to the interrupted reviewer run.

## Fix round 1/5

Status: DONE

### Findings addressed

1. Replaced the source-only connector check with an exact topology contract for
   connectors 10241, 10242, 10238, and 10240. Each contract now binds:
   - connector `lane_count`
   - exact `from_endpoint` link/lane/lane ID
   - exact `to_endpoint` link/lane/lane ID
   - declared connector lane IDs from `lanes`
   - every `(from_lane_id, connector_lane_id, to_lane_id)` mapping tuple
2. Added negative tests that preserve the upstream source stock while mutating
   only `connector_lane_id` or only `to_lane_id`; both fail the connector gate
   while the independent one-stock sharing contract remains PASS.
3. Added a lane-count/destination-endpoint mutation test.
4. Kept `movement_queue_duplication_allowed=false` and the four-stock contract.
5. Changed `sample_dimensions.target_connectors` to the fixed target-set size 4
   and added `resolved_target_connectors` for observed availability.

### Latest compiler/network evidence

- 10241: two lanes, 1220012103 lanes 1/2 to 1220013700 lanes 1/2.
- 10242: one lane, 1220012103 lane 2 to 1220015100 lane 3.
- 10238: two lanes, 1220013600 lanes 1/2 to 1220012003 lanes 1/2.
- 10240: one lane, 1220013600 lane 2 to 1220012600 lane 3.
- Real compiler artifact result remains `PASS=6, FAIL=0, NOT_EVALUATED=0`.

### Verification

```text
python -B -m unittest scripts.tests.test_validate_sc12_shared_lane -v
Ran 10 tests in 19.555s
OK
```

```text
python -B -m unittest discover -s scripts/tests -p 'test_*.py' -v
Ran 65 tests in 42.570s
OK
```

- `git diff --check -- scripts/validate_sc12_shared_lane.py scripts/tests/test_validate_sc12_shared_lane.py`: PASS
- Stale source-only constants/evidence strings: none found.
- Self-review: no open implementation concern in this fix scope.
