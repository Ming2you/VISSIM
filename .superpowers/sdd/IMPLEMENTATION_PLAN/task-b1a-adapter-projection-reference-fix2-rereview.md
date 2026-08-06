# B1a Slice 2 Fix Round 2 Re-review

## Findings

### Critical

1. **Original Critical 2 is NOT_ADDRESSED because the raw pre-parser and `argparse` accept different option spellings.**

   `_preparse_projection_roles` recognizes only exact `--projection-only` and exact projection value options at `evaluation/controllers/vissim_stackelberg_adapter.py:150-193`. The full parser is constructed with `argparse.ArgumentParser()` at line `4876`, leaving Python's long-option abbreviation behavior enabled. It therefore accepts unique prefixes such as `--projection-onl`, `--state-j`, and `--out-projection-referenc`, while the raw pre-parser does not record them.

   A projection invocation using accepted `--projection-onl` plus complete canonical roles and an invalid `--mode` exits at `parse_args()` (`4938-4945`), but `_invalidate_projection_reference_after_parser_failure` returns at lines `441-442` because the raw pre-parser did not mark projection-only. Likewise, exact `--projection-only` plus an abbreviated accepted reference option leaves `reference_text` empty at lines `443-447`. In either case, an old PASS reference survives the parser failure.

   The exact-option cases are fixed: nonzero parser exits route through the authorization helper at lines `4938-4945`; help/zero exits do not mutate evidence; and non-projection invocations are rejected by the guard at lines `438-447`. The remaining required fix is to make the raw pre-parser and full parser recognize exactly the same CLI language, preferably by disabling abbreviation and explicitly reserving every raw spelling that the parser can accept, then adding abbreviation/prefix regression cases.

2. **Original Critical 4 is NOT_ADDRESSED because an accepted abbreviated input role can still be unlinked as the reference output.**

   `_prepare_projection_output_roles` reserves state/run/topology CLI identities only from the exact raw-option lists at `evaluation/controllers/vissim_stackelberg_adapter.py:262-275`; it does not also reserve the successfully parsed `args.state_json` or `args.approved_topology`. With exact `--projection-only`, accepted abbreviated `--state-j <state>`, complete exact manifest/topology/sidecar roles, and `--out-projection-reference <state>`, the pre-parser records no state identity. The manifest does not contain the per-snapshot state path. After the manifest, approval, A1 graph, and topology authorize successfully, lines `413-427` see no reference/input collision and unlink the state file. The later exact state open fails only after that destructive mutation.

   This is new Critical breakage introduced by the Fix Round 2 raw-role refactor: Fix Round 1's preparation path reserved the parsed state argument, while the new code relies on exact raw recognition. Required fix: align parser/pre-parser syntax and reserve both every raw role spelling and every parsed effective input before mutation. No unlink may occur unless all parser-accepted role identities, including the state capture, are represented in the immutable universe.

### Important

1. **Original Important 4 is NOT_ADDRESSED because the 33-test matrix omits the parser-abbreviation surface.**

   The new parser tests at `plant/tests/test_vissim_strict_physical_projection_reference.py:816-859` use exact `--projection-only` and exact projection path options. The A1 and malformed-path tests at lines `916-992` correctly cover exact A1 path/hardlink and case/slash spellings, but none exercises a unique `argparse` abbreviation for the projection flag, reference role, or state role. Consequently, the reported 33 focused PASS cases do not detect either Critical path above.

   Required fix: add parser-failure tests using abbreviated `--projection-only` and abbreviated reference roles, plus a source-preservation test where abbreviated `--state-json` aliases the final reference. Retain all existing exact-option, A1, malformed spelling, hardlink, publication, snapshot, consumption, and provenance cases.

## Verified Fixes

The approval-bound A1 authorization itself is correctly ordered for exact roles. The manifest is bounded-snapshotted at `evaluation/controllers/vissim_stackelberg_adapter.py:319-328`; its hash-bound approval is snapshotted at lines `330-354`; the approval's exact lane-graph binding is extracted and bounded-snapshotted at lines `356-386`; and both approval/A1 snapshots are compared with full replay at lines `388-412`, all before the first possible reference unlink at line `427`.

Raw exact role spellings are preserved before canonical resolution at lines `262-310`. `validate_projection_output_paths` still combines normalized path identity with existing-file device/inode identity at `plant/src/vissim_strict/physical_projection_reference.py:447-490`, so the exact case/slash and hardlink cases are covered. Missing or malformed manifest, approval, or A1 authorization raises before adapter line `427`, and parser-failure authorization suppresses its own error without unlinking at adapter lines `438-465`.

The previous publication and trust guarantees remain intact in the supplied snapshot: same-buffer reference/manifest/state/sidecar validation remains at `plant/src/vissim_strict/physical_projection_reference.py:321-444`; approval/A1/A2 snapshots remain at lines `135-185`; bounded temporary sidecar/reference validation and reference-last publication remain at lines `509-679`; projection-only still has one public projector call at `evaluation/controllers/vissim_stackelberg_adapter.py:5015-5017`; and required mode still validates before ledger-derived state construction and `repo_imports` at lines `5063-5125`. Complete action provenance and controller-fallback preservation remain in `_projection_provenance` (`468-493`), `_action_csv_metadata` (`4711-4734`), metadata installation (`5221`), fallback status handling (`5530-5534`), and both serializers (`5592`).

## New Breakage

The abbreviated-state destructive alias described under Critical 4 is a new Critical regression introduced by this fix delta. No other new Critical or Important breakage was found within the scoped slice.

## Finding Dispositions

- **Original Critical 2: NOT_ADDRESSED.** Exact invalid-choice/unknown/missing-value parser failures are fixed, but parser-accepted abbreviated projection/reference roles bypass raw preparse invalidation.
- **Original Critical 4: NOT_ADDRESSED.** Exact lexical, A1, malformed case/slash, and hardlink authorization is fixed, but parser-accepted abbreviated state roles are omitted and can be deleted.
- **Original Important 4: NOT_ADDRESSED.** The suite expanded from 26 to 33 focused tests but does not cover the remaining abbreviation mismatch.

## Minor

The snapshot-value immutability Minor remains explicitly deferred. `BoundedJsonSnapshot.value` is still stored without recursive freezing at `plant/src/vissim_strict/physical_projection.py:349-363`; this fix delta does not resolve it.

## Verdicts

**Requirements verdict: FAIL**

**Code quality: NEEDS_CHANGES**

Live COM and p95 remain `NOT_EVALUATED`. VBS/timing/post-run/B1b and later slices are out of scope.

## Evidence Basis

No tests were rerun. Execution evidence is the implementer's reported **147 PASS, 0 failed** and the controller's independently reported **33 focused tests PASS**. Static conclusions are based on `review-b1a-adapter-projection-reference-fix2-current.diff`.
