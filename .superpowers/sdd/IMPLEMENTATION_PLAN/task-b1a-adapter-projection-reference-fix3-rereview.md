# B1a Slice 2 Fix Round 3 Re-review

## Findings

### Critical

1. **Original Critical 2 is NOT_ADDRESSED because split-value token recognition still differs from the sole full parser and can unlink a path the full parser did not accept.**

   The full parser correctly disables long-option abbreviations at `evaluation/controllers/vissim_stackelberg_adapter.py:4944-4956`. The raw preparse, however, accepts every following token that does not start with two hyphens as a split value at lines `177-183`; rejected-prefix capture repeats the same rule at lines `199-205`. `argparse` does not consume an unknown single-dash token such as `-victim.json` as the required value of `--out-projection-reference`; it classifies that token as an option and reports a missing value. The raw preparse instead records `-victim.json` as the reference value.

   With exact `--projection-only`, valid exact state/manifest/topology/sidecar roles, and `--out-projection-reference -victim.json`, the nonzero parser exit enters the hook at lines `5008-5015`. The hook sees a raw reference at lines `507-531`; preparation accepts that path as the mutation candidate at lines `279-281`, replays trust at lines `388-495`, and can unlink it at line `496`. A leading-hyphen workspace filename is not forbidden by canonical destination validation (`plant/src/vissim_strict/run_evidence.py:356-389`). Thus raw preparse and full parser still do not have the exact same language, and a parser-rejected value can identify a deletion target.

   **Required fix:** make split-value classification identical to the sole parser, including unknown single-dash option-like tokens while preserving forms the parser really accepts (such as exact `--option=value`). Add a focused regression that creates a protected or stale `-victim.json`, supplies it in parser-rejected split form, and proves no unlink occurs. The existing exact invalid-choice/unknown/missing-value cases with an independently valid exact reference must continue to invalidate that reference.

### Important

No new Important finding was introduced by the Fix Round 3 delta. The residual issue above is the original parser/preparse Critical, not new breakage from disabling abbreviations.

## Finding Dispositions

### Original Critical 2: NOT_ADDRESSED

Long-option spelling is aligned: `_PROJECTION_OPTIONS` enumerates the protected exact names at `evaluation/controllers/vissim_stackelberg_adapter.py:150-157`, strict prefixes are not accepted as roles at lines `160-216`, and the sole adapter parser uses `allow_abbrev=False` at line `4946`. Exact split-value language is nevertheless still mismatched at lines `177-183` and `199-205`, enabling the destructive parser-failure path described above.

### Original Critical 4: ADDRESSED

Every successfully parsed effective state, manifest, topology, sidecar, and reference role participates in the pre-mutation equality gate at `evaluation/controllers/vissim_stackelberg_adapter.py:285-320`; effective input paths are independently reserved at lines `307-310`. Every exact raw input occurrence, superseded output, and rejected-prefix value is also retained at lines `321-379`. Manifest, approval, approval-bound A1 lane graph, and topology authorization is completed at lines `388-480`, output/file identities are checked at lines `482-495`, and the first possible unlink is line `496`. The abbreviated-input omission that caused this original finding is closed.

### Original Important 4: ADDRESSED

The focused matrix now contains explicit rejected-prefix cases for projection-only and reference preservation at `plant/tests/test_vissim_strict_physical_projection_reference.py:875-901`, plus state, run-manifest, and topology source-preservation cases at lines `903-940`. The helper asserts parser rejection and byte-for-byte preservation at lines `839-850`. These five tests adequately cover the original abbreviation finding, while the separate split-value mismatch under Critical 2 still needs its own regression.

### New Abbreviated-state Critical Regression: ADDRESSED

`--state-j=...` is rejected because the sole full parser disables abbreviation at `evaluation/controllers/vissim_stackelberg_adapter.py:4946`. The raw scanner records a strict-prefix value only as rejected identity at lines `192-208`, and preparation adds it to the immutable universe at lines `321-331`; it cannot become an effective state or output target. Successfully parsed state is independently immutable at lines `285-314`. The direct state/reference-alias regression preserves the state bytes at `plant/tests/test_vissim_strict_physical_projection_reference.py:903-914`.

## Scoped Regression Audit

Rejected protected prefixes do not establish projection mode or an output role (`evaluation/controllers/vissim_stackelberg_adapter.py:173-208`), while their nonempty values are retained as immutable identities at lines `321-331`. Parser/preparse equality covers all successful effective roles before mutation at lines `285-320`. Non-projection parser failures cannot enter invalidation because of the exact projection guard at lines `507-515`; help exits with code zero and bypasses the hook at lines `5008-5015`.

The prior exact-option and trust guarantees remain present. Exact invalid-choice, unknown-option, and missing-value regressions are retained at `plant/tests/test_vissim_strict_physical_projection_reference.py:857-873`. Manifest, approval, and A1 snapshots precede unlink at adapter lines `388-496`. Projection-only validates its inputs, calls the sole public projector once, and publishes through the shared publisher at lines `5041-5098`. Publication still validates bounded temporary sidecar bytes, atomically replaces the sidecar, validates the temporary reference against its expected hash, and atomically replaces the reference last at `plant/src/vissim_strict/physical_projection_reference.py:570-669`.

Required normal mode still validates the bounded manifest and exact expected reference hash before `repo_imports` at `evaluation/controllers/vissim_stackelberg_adapter.py:5121-5195`; it consumes the validated ledger-derived state construction at lines `5167-5174` and `604-611`. Complete projection provenance is built at lines `538-563`, installed before controller execution at lines `5280-5296`, survives the controller fallback at lines `5600-5604`, and is serialized to JSON and CSV at lines `5653-5662` and `4781-4804`. No additional Critical or Important regression was found in those unchanged guarantees.

## Minor

The snapshot-value recursive-immutability Minor remains deferred as directed. `BoundedJsonSnapshot.value` is still returned without recursive freezing at `plant/src/vissim_strict/physical_projection.py:349-363`.

## Verdicts

**Requirements verdict: FAIL**

**Code quality: NEEDS_CHANGES**

Live COM and p95 remain `NOT_EVALUATED`. Future slices remain out of scope.

## Evidence Basis

No tests were rerun. Execution evidence is the implementer's reported **152 PASS, 0 failed** and the controller's independently reported **38 focused tests PASS**. Static conclusions are based on `review-b1a-adapter-projection-reference-fix3-current.diff`, the Fix Round 3 report, and the Fix Round 2 re-review.
