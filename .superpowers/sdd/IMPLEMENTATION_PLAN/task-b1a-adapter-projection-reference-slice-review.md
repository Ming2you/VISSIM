# B1a Adapter Projection/Reference Slice Review

## Findings

### Critical

1. **Coherently rehashed boolean numerics can be accepted as a valid sidecar/reference chain.**

   Evidence: `plant/src/vissim_strict/physical_projection_reference.py:268-294` validates only the sidecar's top-level shape and then compares all reconstructed nested values with ordinary Python `!=`. Python considers `True == 1` and `False == 0`. The expected normalized hash at `plant/src/vissim_strict/physical_projection_reference.py:216-220` is computed from the reconstructed values, not from the authored sidecar values, and the reference aggregate comparison at `plant/src/vissim_strict/physical_projection_reference.py:446-452` repeats the same non-type-strict equality. An attacker can, for example, replace a `stock_counts` value of `1` with `true`, leave the original normalized hash in place, recompute the sidecar semantic/file hashes and reference semantic hash, and pass all these comparisons.

   Required fix: validate the complete nested `projection-v2.1` schema with exact JSON types, rejecting booleans in every numeric position. Recompute the normalized projection hash directly from the authored assignment/stock payload as well as independently reconstructing the expected payload, and use a recursive type-strict comparison rather than Python value equality. Add coherent-rehash tests for booleans and integer/float type substitutions in assignments, stock counts, views, diagnostics, sample dimensions, and residuals.

2. **Projection-only can leave an old or newly written PASS reference after a failed invocation.**

   Evidence: missing-argument rejection and state/manifest/topology/output resolution occur before stale-reference removal at `evaluation/controllers/vissim_stackelberg_adapter.py:4525-4543`. A parseable invocation with a usable `--out-projection-reference` can therefore fail first and leave an earlier PASS reference intact. In addition, the final PASS reference is published at `evaluation/controllers/vissim_stackelberg_adapter.py:4571` and only then bounded-reopened/validated at lines `4572-4576`; the exception path at lines `4577-4578` does not remove or replace that PASS file. This contradicts the implementer report's stale-PASS claim at `task-b1a-adapter-projection-reference-slice-report.md:64-65`.

   Required fix: establish and invalidate a usable reference destination before any other fallible projection work, including required-input rejection. Serialize and size-check sidecar/reference bytes before final publication, validate same-directory temporary files, and rename a reference to its final name only after the complete chain passes. Every failure path must leave the final reference absent or deterministically non-PASS; no oversized or post-validation-failed PASS final may remain.

3. **Parsed artifacts and their claimed file hashes are not bound to the same bytes, permitting mixed atomic versions.**

   Evidence: `validate_physical_projection_reference` parses the reference and manifest at `plant/src/vissim_strict/physical_projection_reference.py:351-352`, parses state and sidecar at lines `401-402`, and later reopens those paths independently for hashes at lines `393`, `405`, `425`, `428`, `439`, and `457`. The normal adapter performs yet another independent reference hash read after validation at `evaluation/controllers/vissim_stackelberg_adapter.py:4606-4612`. Because producers publish by atomic replacement, these separate opens can each observe a complete but different version. The validator can consequently return an artifact parsed from one reference/state/sidecar version while recording or accepting the hash of another.

   Required fix: for every bounded JSON input, read one bounded byte snapshot, compute SHA-256 from that exact buffer, and strict-parse that same buffer. Carry those byte-bound hashes in `ValidatedProjectionReference`. Compare the caller's expected reference hash directly with the hash of the exact parsed reference bytes, not a subsequent path read. Apply the same coherent-snapshot rule to manifest, state, sidecar, approval/topology companions, and provenance construction.

4. **Projection output paths can alias and destroy immutable trust inputs.**

   Evidence: the five paths are resolved independently at `evaluation/controllers/vissim_stackelberg_adapter.py:4536-4540`, with no distinctness check before the reference is unlinked at lines `4541-4543` or the sidecar/reference are replaced at lines `4560` and `4571`. Setting the reference destination to the state or run-manifest path deletes that immutable input; setting the sidecar destination to one of those paths overwrites it; and making the two outputs equal creates a self-overwriting publication sequence.

   Required fix: before any unlink or write, reject path identity among both outputs and every immutable input/source, and reject sidecar/reference aliasing. Preserve the exact canonical/non-reparse checks while doing the identity comparison, and add collision tests for state, manifest, topology, approval, adapter source, and the two output roles.

### Important

1. **The validator contains a second projector implementation.**

   Evidence: `_expected_projection` at `plant/src/vissim_strict/physical_projection_reference.py:102-221` duplicates lane location, assignment construction, stock accumulation, view summaries, diagnostics, partition identities, and normalized hashing from `project_vehicle_records` at `plant/src/vissim_strict/physical_projection.py:1181-1347`. The public-symbol call counter in `plant/tests/test_vissim_strict_physical_projection_reference.py:170-188` cannot detect drift in this copied implementation.

   Required fix: factor the deterministic projection calculation into one shared internal implementation used by the public producer and independent validator wrappers. Keep `project_vehicle_records` as the sole public projector and call it exactly once in projection-only, while avoiding a second algorithm that can diverge.

2. **Required normal mode gates on the ledger but does not actually consume it in model-state construction.**

   Evidence: `traffic_state_from_vissim` derives freeway state, ramp queues, boundary queues, and urban queues entirely from detector/global aggregate fields at `evaluation/controllers/vissim_stackelberg_adapter.py:2364-2460`. The validated sidecar is only assigned to a new attribute at lines `2461-2464`; the full snapshot contains no later read of `physical_projection_ledger`. The call site at lines `4663-4668` therefore carries the ledger as decoration while controller input remains the legacy aggregate path.

   Required fix: define and use an explicit B1a state-construction boundary whose physical projection input is the validated ledger and whose provenance is inseparable from it. The fix need not add B1b transfer dynamics, but it must demonstrate a real consumer of the validated B1a stock/assignment view rather than an unused dynamic attribute. Add a required-mode success test proving that poisoned or contradictory legacy projection data cannot replace the validated ledger.

3. **Projection provenance is incomplete, especially in the CSV action output.**

   Evidence: `_projection_provenance` at `evaluation/controllers/vissim_stackelberg_adapter.py:127-144` omits qualification, exact topology path, reference semantic hash, and the reference aggregates/identity fields. `_action_csv_metadata` at lines `4311-4321` carries only run ID, reference file hash, and normalized projection hash. Thus the report's claim that exact projection provenance is carried into both outputs (`task-b1a-adapter-projection-reference-slice-report.md:20-23`) is not supported.

   Required fix: define one exact action-provenance schema derived from the validated object, including qualification, `(run_id, sim_sec)`, manifest path/hash as applicable, state path/hash, topology path/file/semantic hashes, sidecar path/file/semantic hashes, reference path/file/semantic hashes, normalized hash, and bound aggregates. Emit and test that schema in JSON and an unambiguous equivalent in every CSV action row, including controller-exception fallback output.

4. **The five focused tests do not cover the required mutation and ordering matrix.**

   Evidence: the report records only five focused tests at `task-b1a-adapter-projection-reference-slice-report.md:81-83`. The reference test at `plant/tests/test_vissim_strict_physical_projection_reference.py:95-118` covers seven value mutations and missing fields but no extra fields or comprehensive type/range/hash cases. The sidecar test at lines `120-142` replaces only five entire top-level values. Adapter tests at lines `192-210` poison only `repo_imports` and exercise only an expected-reference-hash failure. There are no focused tests for duplicate/nonfinite JSON, pre-read bounds, stale PASS, partial visibility, path case/slash/escape/reparse, spaces/non-ASCII, output aliasing, state/run/approval/topology identity matrices, nested coherent rehashes/mass residuals, poisoned config/forecast/candidate/fallback/action writers, valid normal consumption, no normal reprojection, or exact provenance in both outputs.

   Required fix: add the complete focused matrix from the slice brief. In particular, reproduce the boolean coherent-rehash and stale-reference defects above, test atomic reader visibility, poison every forbidden projection-only and pre-trust normal entry point, and execute a valid required-mode path through both action serializers. The existing report evidence may remain as regression evidence, but five focused tests are not adequate acceptance evidence.

5. **Large JSON integers can escape fail-closed numeric validation as raw `OverflowError`.**

   Evidence: `_finite_number` performs `float(value)` without an overflow guard at `plant/src/vissim_strict/physical_projection_reference.py:89-90`. Projection-only similarly accepts any non-boolean integer/float at `evaluation/controllers/vissim_stackelberg_adapter.py:112-114` and converts it at line `119`. The adapter catches only `OSError` and `ValueError` at lines `4577` and `4615`; `OverflowError` is not covered.

   Required fix: mirror the guarded finite-number helper already present in `physical_projection.py`, reject unrepresentable/range-invalid numerics at their owning schema boundary, and keep a final fail-closed CLI guard. Add huge-integer mutations for reference, sidecar, and state numeric fields.

### Minor

1. **Validated projection objects are only shallowly immutable.**

   Evidence: `plant/src/vissim_strict/physical_projection_reference.py:455-459` wraps shallow `dict` copies in `MappingProxyType`; nested assignments, diagnostics, reasons, and state objects remain mutable. The adapter then makes additional shallow copies at `evaluation/controllers/vissim_stackelberg_adapter.py:4624-4629` and `2461-2464`.

   Required fix: recursively freeze validated artifacts, or expose detached immutable typed snapshots and perform explicit deep copies only at a documented mutable adapter boundary.

## Requirements Verdict

**FAIL**

The implementation satisfies several important ordering properties: required normal trust validation occurs before `repo_imports`; the controller exception fallback at `evaluation/controllers/vissim_stackelberg_adapter.py:4868-5056` cannot absorb those earlier trust failures; projection-only calls the public projector once and returns before action/controller work; the three specified reads use their nominal bounds; and canonical path resolution plus atomic replacement primitives are present. However, direct coherent-rehash acceptance, stale PASS retention, mixed byte/hash binding, destructive output aliasing, duplicate projection logic, unused ledger consumption, incomplete action provenance, and missing focused coverage violate binding requirements.

Live COM and p95 remain correctly `NOT_EVALUATED`. VBS/timing/post-run/B1b are not assessed because they are out of scope.

## Code Quality Verdict

**NEEDS_CHANGES**

The code is organized around shared APIs and keeps the trust gate visibly ahead of controller imports, but the trust-critical implementation relies on duplicated algorithms, non-type-strict equality, repeated path reopens, shallow immutability, and post-publication validation. Those are structural integrity risks, not cosmetic concerns.

## Evidence Basis

Per review instructions, the implementer's tests were not rerun. Test conclusions above use only the commands, counts, and PASS results reported in `task-b1a-adapter-projection-reference-slice-report.md:76-97` and static inspection of the supplied full code snapshot.
