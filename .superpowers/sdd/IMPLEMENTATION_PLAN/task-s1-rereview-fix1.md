# S1 fix round 1 scoped re-review

## Final verdict

- Spec verdict: PASS
- Quality verdict: PASS

Implementation tests were not re-run for this re-review; this is a scoped code/package review against `review-s1-fix1.diff` and the current files.

## Finding verdicts

### 1) SC9004 외 headless selected/model controller가 자동 model_excluded되어 false PASS

**Verdict: ADDRESSED**

Evidence:

- `plant/src/vissim_strict/compiler.py:25-27` limits explicit model exclusions to SC9004 only.
- `plant/src/vissim_strict/compiler.py:116-121` now classifies `supplyFile2 && no heads` as:
  - `model_excluded` only for controller `9004`;
  - `invalid` with reason `missing_signal_head_provenance` for every other controller.
- `plant/src/vissim_strict/compiler.py:376-390` turns that non-SC9004 case into a validation error instead of silently skipping it.
- `plant/tests/test_vissim_strict_compiler.py:198-212` adds the negative regression test proving a non-exception headless controller fails closed.

Conclusion: the prior false-PASS path from broad automatic exclusion is closed.

### 2) SC12 connector가 from_lane만 맞고 connector_lane_id/to_lane_id/destination이 변조되어도 PASS

**Verdict: ADDRESSED**

Evidence:

- `scripts/validate_sc12_shared_lane.py:27-122` now encodes exact expected connector contracts for all four target connectors, including `lane_count`, `from_endpoint`, `to_endpoint`, `connector_lane_ids`, and full `(from_lane_id, connector_lane_id, to_lane_id)` tuples.
- `scripts/validate_sc12_shared_lane.py:291-313` reads `connector_lane_id` and `to_lane_id` into the actual mapping evidence.
- `scripts/validate_sc12_shared_lane.py:365-380` compares the full actual connector object against the exact expected contract and fails on any mismatch.
- `scripts/tests/test_validate_sc12_shared_lane.py:182-215` adds explicit mutations for `connector_lane_id` and `to_lane_id`, both of which now fail the connector gate while preserving the independent stock-sharing check.
- `scripts/tests/test_validate_sc12_shared_lane.py:217-231` adds a destination-endpoint and lane-count mutation failure.

Conclusion: the validator no longer PASSes on source-only equality when connector-lane or downstream semantics are corrupted.

### 3) per-controller dailyProgLists/time-indexed active program/runtime/readback provenance 미보존과 임의 fallback 위험

**Verdict: ADDRESSED**

Evidence:

- `plant/src/vissim_strict/signal_program.py:224-325` adds `parse_sig_definition(...)`, `SignalDefinition`, and deterministic parsing/storage of per-controller SIG `dailyProgLists`.
- `plant/src/vissim_strict/compiler.py:233-254` stores per-controller active-program evidence including:
  - configured `progNo`,
  - `daily_program_lists`,
  - simulation start provenance,
  - runtime readback status `NOT_EVALUATED`,
  - `fallback_used = False`.
- `plant/src/vissim_strict/compiler.py:256-345` handles ambiguous, unresolved, and daily-list-gap cases by producing `NOT_EVALUATED`/validation-error evidence rather than inventing a fallback active program.
- `plant/src/vissim_strict/compiler.py:449-468` emits that active-program evidence per controller in each compiled schedule.
- `plant/src/vissim_strict/compiler.py:481-487` also marks the top-level artifact boundary explicitly as `active_program_runtime_readback_status = NOT_EVALUATED` with a compile-time reason.
- `plant/tests/test_vissim_strict_compiler.py:214-247` verifies daily-list expansion at runtime start with `fallback_used == False` and runtime readback `NOT_EVALUATED`.
- `plant/tests/test_vissim_strict_compiler.py:146-162` verifies the current network's no-daily-list / no-runtime-readback boundary is explicit rather than fabricated from fallback.

Conclusion: the current artifact now preserves the missing-evidence boundary and avoids arbitrary active-program PASS/fallback behavior.

### 4) sample_dimensions.target_connectors가 fixed target 4가 아닌 resolved count

**Verdict: ADDRESSED**

Evidence:

- `scripts/validate_sc12_shared_lane.py:589-594` now sets:
  - `target_connectors = len(EXPECTED_CONNECTORS)` (fixed target set size = 4)
  - `resolved_target_connectors = len(source_maps)` (observed availability)
- `scripts/tests/test_validate_sc12_shared_lane.py:83-84` verifies the full-case values `4/4`.
- `scripts/tests/test_validate_sc12_shared_lane.py:262-265` verifies the incomplete-case split `4/3`.

Conclusion: the artifact now separates fixed target cardinality from resolved availability.

## New Critical / Important breakage from this fix diff

No new Critical or Important breakage was identified in the reviewed fix package.

## Overall assessment

All four scoped findings are addressed in the current package, and no new Critical/Important regression was found from this fix diff.
