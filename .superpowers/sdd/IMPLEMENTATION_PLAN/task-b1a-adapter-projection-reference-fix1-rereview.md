# B1a Slice 2 Fix Round 1 Re-review

## Findings

### Critical

1. **Original Critical 2 remains open because parser-level argument failures still preserve stale PASS evidence.**

   `argparse` performs full option/choice validation at `evaluation/controllers/vissim_stackelberg_adapter.py:4652-4715`, before the projection-only branch and `_prepare_projection_output_roles` at lines `4717-4728`. The fix handles missing required values after a successful parse (`4729-4740`), but an invalid `--mode`/`--controller`, an unknown option, or a missing option value exits inside `parse_args()` while a canonical `--out-projection-reference` may still name an old PASS file. That old reference can later be supplied to required normal mode. The focused stale test at `plant/tests/test_vissim_strict_physical_projection_reference.py:850-861` covers only the post-parse missing-`--approved-topology` path.

   The newly written-reference half is fixed: `plant/src/vissim_strict/physical_projection_reference.py:573-657` serializes, bounds, snapshots, and validates temporary bytes, publishes the final reference last at line `663`, and removes it on downstream failure at lines `672-679`. The remaining required fix is a minimal projection-role preparse or parser error hook that can safely authorize and invalidate a usable canonical reference before any full-parser failure, with focused invalid-choice/unknown-option/missing-value stale-PASS tests.

2. **Original Critical 4 remains open because early stale invalidation can delete the approved A1 lane graph.**

   Before invalidation, `_declared_manifest_role_paths` extracts approval, A2 topology, preflight, producer/configuration inputs, and policy at `evaluation/controllers/vissim_stackelberg_adapter.py:148-184`, but it never opens the approval to discover its `source_inputs.lane_graph.path`. `_prepare_projection_output_roles` then unlinks the reference at lines `187-243`. If `--out-projection-reference` is the canonical lane-graph path, or a hardlink to it, no collision is present in the early immutable set and line `242` deletes the A1 trust input. The lane graph is added only after full validation at lines `4758-4769`, too late to protect it from that unlink. The collision test's immutable map also omits the lane graph at `plant/tests/test_vissim_strict_physical_projection_reference.py:581-605`.

   The same unsafe assumption appears at lines `226-235`: a malformed input spelling can fail before its role is recorded, after which the reference-only recheck may unlink the same underlying file through its canonical output spelling. Required fix: authorize the reference output against a complete immutable-role set, including an exact bounded approval snapshot and A1 graph identity, before any unlink. If required trust inputs are absent or malformed, invalidation needs an independently reserved/authorized reference role rather than the assumption that an unrecorded input cannot alias it. Add A1 path/hardlink and malformed-spelling alias tests.

### Important

1. **Original Important 4 remains open because the focused matrix misses both residual Critical paths.**

   The suite is substantially expanded to 26 focused tests, but `plant/tests/test_vissim_strict_physical_projection_reference.py:850-889` covers only post-parse missing arguments and state/manifest collisions, while the generic immutable collision map at lines `581-605` omits A1. There is no parser-stage stale-PASS case or pre-invalidation reference/A1 alias case. Those omissions allowed the report's closure claims at `task-b1a-adapter-projection-reference-slice-report.md:130-148` and `167-173` to overstate the implementation.

   Required fix: add the cases above and retain the existing 26-test matrix. Per instructions, this review does not rerun tests; it accepts the reported **140 PASS** and the controller's independent **26 focused PASS** as execution evidence, but those passing cases do not cover the remaining defects.

### New Breakage

No separate new Critical or Important regression was found in the fix delta. The issues above are incomplete closures of original Critical 2, Critical 4, and their associated test-coverage finding.

## Original Finding Disposition

### Critical 1: Boolean/type-coercion coherent rehash

**ADDRESSED.** `plant/src/vissim_strict/physical_projection_reference.py:211-219` recomputes the normalized hash from the authored assignments and stock counts. Lines `222-233` reconstruct the complete sidecar through the shared kernel and compare it with recursive type-strict equality. `json_type_strict_equal` at `plant/src/vissim_strict/physical_projection.py:378-391` requires exact scalar types, so booleans, integers, and doubles cannot compare interchangeably.

### Critical 2: Stale/new PASS after failure

**NOT_ADDRESSED.** Temporary publication and post-publication cleanup are addressed at `plant/src/vissim_strict/physical_projection_reference.py:573-679`, and post-parse missing required arguments are addressed at `evaluation/controllers/vissim_stackelberg_adapter.py:4729-4740`. Full parser failures still precede all invalidation at `evaluation/controllers/vissim_stackelberg_adapter.py:4652-4728`.

### Critical 3: Mixed parsed-byte/file-hash versions

**ADDRESSED.** `load_bounded_json_snapshot` at `plant/src/vissim_strict/physical_projection.py:349-363` hashes and parses one bounded byte buffer. Reference/manifest/state/sidecar snapshots are used at `plant/src/vissim_strict/physical_projection_reference.py:330-364`; approval/A1/A2 snapshots are used at lines `135-185`; all companion reconstruction uses those carried hashes at lines `372-424`. Required normal mode passes the expected hash into the exact reference snapshot and compares both manifest snapshots before runtime work at `evaluation/controllers/vissim_stackelberg_adapter.py:4837-4858`.

Temporary reference validation followed by rename is coherent in the ordinary publication path: the reference schema does not bind its own filename, validation uses the complete temp bytes at `plant/src/vissim_strict/physical_projection_reference.py:643-657`, and `os.replace` moves those bytes to the final path before the returned snapshot path is updated at lines `663-671`.

### Critical 4: Output alias destroys trust input

**NOT_ADDRESSED.** Generic canonical path and existing-file identity checks are present at `plant/src/vissim_strict/physical_projection_reference.py:447-490`, and most manifest roles are protected. However, the pre-invalidation role discovery at `evaluation/controllers/vissim_stackelberg_adapter.py:148-243` omits the approval-bound A1 lane graph and can delete it before lines `4758-4769` add it to the immutable set.

### Important 1: Duplicate projector implementation

**ADDRESSED.** The deterministic algorithm now exists once as `_project_vehicle_records_kernel` at `plant/src/vissim_strict/physical_projection.py:1236-1402`; the sole public projector is the thin wrapper at lines `1405-1412`; and sidecar validation calls the shared kernel at `plant/src/vissim_strict/physical_projection_reference.py:222-225`. The adapter's production call remains one projection-only call at `evaluation/controllers/vissim_stackelberg_adapter.py:4785-4787` and there is no normal-mode call.

### Important 2: Validated ledger is decorative rather than consumed

**ADDRESSED.** `_b1a_state_construction_input` at `evaluation/controllers/vissim_stackelberg_adapter.py:274-309` derives link counts, speeds, stopped counts, and queue tails from validated assignments and state records while binding full provenance. `_state_json_from_b1a_projection` replaces legacy local-observation/projection fields at lines `312-319`. `traffic_state_from_vissim` uses that local observation to construct queues at lines `2527-2586` and retains the provenance-bound input at lines `2638-2642`. The actual-consumption test at `plant/tests/test_vissim_strict_physical_projection_reference.py:689-746` proves the validated count wins over a poisoned legacy aggregate without adding B1b transfer dynamics.

### Important 3: Incomplete JSON/CSV action provenance

**ADDRESSED.** `_projection_provenance` contains the exact 22-field schema at `evaluation/controllers/vissim_stackelberg_adapter.py:246-271`. JSON carries it at lines `2689-2691`; CSV metadata serializes the same full object as canonical compact JSON at lines `4489-4512`, including row-local ramp metadata without replacing provenance. Provenance is installed before controller evaluation at lines `4990-4996`, so the controller fallback status update at lines `5300-5304` preserves it for both serializers. The fallback JSON/VSL/signal/ramp assertions are at `plant/tests/test_vissim_strict_physical_projection_reference.py:1095-1120`.

### Important 4: Five-test matrix was inadequate

**NOT_ADDRESSED.** The expansion from 5 to 26 focused tests closes most of the original matrix, including nested coherent rehash, bounds, malformed JSON, exact snapshots, consumption, no reprojection, and fallback provenance. It is not complete while parser-stage stale PASS and A1 pre-invalidation aliasing remain untested and broken.

### Important 5: Raw `OverflowError`

**ADDRESSED.** `_finite_number` catches overflow at `plant/src/vissim_strict/physical_projection_reference.py:108-114`; reference and sidecar boundaries include overflow in their typed handling at lines `218`, `226`, `365`, and `418`; projection-only requires an actual finite JSON double at `evaluation/controllers/vissim_stackelberg_adapter.py:124-128`; and adapter trust exceptions include `OverflowError` at lines `4804-4816` and `4861-4862`.

## Minor Disposition

The original shallow-immutability Minor is **partially, but not fully, resolved**. The validated `artifact`, `state`, and `sidecar` views are recursively frozen at `plant/src/vissim_strict/physical_projection_reference.py:428-443`, and the B1a construction input is frozen at `evaluation/controllers/vissim_stackelberg_adapter.py:300-309`. However, public `BoundedJsonSnapshot.value` is stored without recursive freezing at `plant/src/vissim_strict/physical_projection.py:349-363`, and mutable snapshot values are exposed through `ValidatedProjectionReference` at `plant/src/vissim_strict/physical_projection_reference.py:81-97`. Mutating `.value` can make a snapshot's parsed value disagree with its retained bytes/hash. Freeze snapshot values on construction, or make the mutable parsed copy private and expose an immutable view.

## Verdicts

**Requirements verdict: FAIL**

**Code quality: NEEDS_CHANGES**

Fix Round 1 closes Critical 1 and 3 and Important 1, 2, 3, and 5. Critical 2 and 4 remain open, with Important 4 still incomplete. Live COM and p95 remain correctly `NOT_EVALUATED`; VBS/timing/post-run/B1b remain out of scope.

## Evidence Basis

No tests were rerun for this re-review. Execution evidence is the implementer's reported **140 PASS, 0 failed** and the controller's independently reported **26 focused tests PASS**. Static conclusions come from the supplied full current snapshot `review-b1a-adapter-projection-reference-fix1-current.diff`.
