# B1a Slice 2 Fix Round 4 Re-review

## Findings

No Critical or Important finding remains within the scoped Fix Round 4 delta.

## Finding Disposition

### Residual Split-value Parser/Preparse Critical: ADDRESSED

The adapter now constructs and fully configures its sole `ArgumentParser` with `allow_abbrev=False` before preparsing at `evaluation/controllers/vissim_stackelberg_adapter.py:4958-5021`. `_preparse_projection_roles` receives that same parser, and `_parser_accepts_split_value` delegates token classification to its `_parse_optional` semantics at lines `160-170`.

Both split-token paths use the shared classifier: exact projection value roles at `evaluation/controllers/vissim_stackelberg_adapter.py:186-195` and rejected protected prefixes at lines `204-221`. Consequently, an unknown single-dash token is not consumed by either path. For an exact split `--out-projection-reference -victim.json`, no reference value is recorded, so parser-failure invalidation returns before mutation at lines `521-530`. The focused regression proves the existing file remains byte-for-byte unchanged at `plant/tests/test_vissim_strict_physical_projection_reference.py:875-893`.

Parser-accepted negative-looking values remain aligned because the same configured parser classifies them. The `-1` regression reaches the later invalid-choice failure and removes the exact stale reference at `plant/tests/test_vissim_strict_physical_projection_reference.py:913-930`. Exact `--option=value` remains a direct exact-role form at adapter lines `198-202`, including leading-dash inline values. The rejected-prefix regression at test lines `895-911` confirms that a parser-rejected split single-dash token is not captured as the rejected prefix's value, while the independently parser-accepted exact inline reference remains the authorized invalidation target.

## Scoped Regression Audit

Existing exact invalid-choice, unknown-option, and missing-value failures still carry complete exact projection roles into stale-reference invalidation at `plant/tests/test_vissim_strict_physical_projection_reference.py:817-837` and `857-873`. The nonzero parser-exit hook is unchanged at `evaluation/controllers/vissim_stackelberg_adapter.py:5022-5029`.

The prior role-identity safeguards remain intact. Parsed effective inputs and all effective role equality checks precede mutation at `evaluation/controllers/vissim_stackelberg_adapter.py:299-334`; rejected-prefix identities, exact raw inputs, and superseded outputs remain reserved at lines `335-394`. Manifest, approval, approval-bound A1, and topology authorization remains at lines `395-495`; output path and existing-file identities are checked at lines `496-509`; and the first possible unlink remains line `510`.

No new Critical or Important breakage was introduced by moving parser construction before the raw scan or by sharing its optional-token classifier.

## Minor

The snapshot-value recursive-immutability Minor remains deferred as directed. `BoundedJsonSnapshot.value` is still returned without recursive freezing at `plant/src/vissim_strict/physical_projection.py:349-363`.

## Verdicts

**Residual Critical: ADDRESSED**

**Requirements verdict: PASS**

**Code quality: APPROVED**

Live COM and p95 remain `NOT_EVALUATED`.

## Evidence Basis

No tests were rerun. Execution evidence is the implementer's reported **155 PASS, 0 failed** and the controller's independently reported **3 new focused tests PASS**. Static conclusions are based on `review-b1a-adapter-projection-reference-fix4-current.diff`, the appended Fix Round 4 report, and the Fix Round 3 re-review.
