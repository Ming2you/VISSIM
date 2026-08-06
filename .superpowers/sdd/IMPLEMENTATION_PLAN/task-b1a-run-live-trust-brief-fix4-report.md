# B1a trusted runner/live-evidence brief fix-round-4 report

## Scope

Planning-only amendment. Changed only:

- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-brief.md`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-brief-fix4-report.md`

No implementation, fixture, generated output, or live VISSIM artifact was edited. No
live COM or live p95 PASS is claimed.

## Changed sections

### Fix-round-4 precedence

Added a short controlling amendment. Its duplicate-binding, role-constant, and
preserved-artifact contracts override less-specific older wording. Legacy post-exit
markers and locale-dependent redirected logs cannot qualify a required-mode run.

### I3: exact bindings and cardinality

- Defined absent demand profile as null/null input binding plus null simulation value;
  a present simulation value must be the exact input path string.
- Required exact path/hash equality for every producer/config intersection (currently
  `adapter`), the supported-version policy duplicate, all preflight producer duplicates,
  action-provenance execution sightings, the preserved generated-config bytes, and the
  post-run run-manifest duplicate.
- Added a normative constant table for all 16 closed artifact roles with fixed phase,
  success minimum, failure minimum, and maximum. Validators compare the authored table
  to constants rather than consume authored thresholds.
- Added success equations for every singleton, the state/capture/projection/reference/
  timing bijection, action JSON/CSV pairing, decision identities, and cumulative rows.
  Failed attempts have explicit zero-to-maximum in-process inventory rules and can never
  qualify.

Disposition: **ADDRESSED**.

### I13: preserved evidence predicates

- Fixed strict ASCII-as-UTF-8/no-BOM CSV framing, exact headers and column order for the
  13-column state CSV, 13-column per-decision action CSV, 15-column cumulative action
  CSV, and 7-column signal-readback CSV.
- Defined typed row identities, state cadence/cardinality, per-kind action fields and
  mapping-derived order, action/cumulative row equality, and exact signal immediate/
  post-step pairing plus stdout-counter equations.
- Defined a unique anchored `STAGE=SIM_DONE` token, exact anchored counters and decision
  lines, fail-on-any `ERROR=`, and byte-empty stderr. Unknown well-framed stdout and
  opaque metadata are diagnostic-only.
- Required `runlog-capture-v2.2` because direct redirected cscript logs do not guarantee
  a replayable encoding contract.
- Required `vissim-error-evidence-v2.2`: absent or zero-byte run-bound `.err` evidence is
  the only PASS case; nonzero raw bytes fail without unsupported replacement decoding.
- Required monotonic `wall-time-profile-v2.2`; its identity/arithmetic/normal-exit fields
  gate run integrity, while total duration is diagnostic and cannot replace projection
  timing receipts.
- Added an explicit gating-versus-diagnostic table. Authored status/count/hash fields are
  comparison targets only.

Disposition: **ADDRESSED**.

## Grounding used

- VBS CSV headers and completion/failure counters:
  `scripts/run_real_world_stackelberg_controller.vbs` lines 179-188 and 276-314.
- Decision state/action pairing and action CSV validation/application:
  the same VBS lines 713-900.
- State CSV row writer and cadence: the same VBS lines 411-579 and 1613-1638.
- Signal immediate and post-step writers: the same VBS lines 1127-1182, 1287-1339, and
  1988-2024.
- Adapter per-decision CSV order/fields:
  `evaluation/controllers/vissim_stackelberg_adapter.py` lines 4195-4327.
- Watchdog stdout/stderr, VISSIM-error, wall-time, and artifact-manifest writers:
  `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1` lines 359-446 and
  474-525.
- Existing offline predicates:
  `scripts/validate_baseline_snapshot.py` lines 1126-1187, 1281-1350, and 1603-1822;
  `scripts/audit_plant_fidelity.py` lines 1460-1605 and 2020-2074.

## Self-review

- Every closed role now has one fixed tuple; all singletons and repeated pairings have
  explicit success equations and explicit failed-attempt behavior.
- Demand-profile null/present duplication and every currently repeated producer/config
  path/hash are equality constraints checked before semantic hashes.
- Exact headers, types, column/row order, identities, cardinalities, readback predicates,
  log anchors, stderr policy, and post-exit PASS schemas are stated.
- Broad or non-replayable content is diagnostic-only. The brief does not infer physical
  PASS from opaque metadata, warnings, mtimes, wall duration, or permissively decoded
  `.err` text.
- Required-mode incompatible evidence uses versioned replacements rather than assigning
  a false predicate to legacy artifacts.
- The brief still leaves both live gates `NOT_EVALUATED` until supported live COM evidence
  and at least 20 valid projection timing receipts exist.

Verification was document self-review only; implementation tests were not run because
this round explicitly forbids implementation edits.
