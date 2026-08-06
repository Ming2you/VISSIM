# Task 2 integration report

Status: DONE

Changed file: `IMPLEMENTATION_PLAN.md`

## Coverage

- Reframed the target as the complete VISSIM adapter + rollout plant + MPC decision + paired-future validation system.
- Reopened S0 and made source/import/EOL, strict runner, provenance, and 31/31 tests blocking.
- Corrected SC12 to shared through+left lane stocks and required SG/stage coupling.
- Added one-stock topology, exact projection/substep conservation, boundary/ramp/freeway stocks, observed-speed delay, and frozen whole-run calibration.
- Made native per-SC cycles prerequisite and profile-scoped offset fail-closed.
- Defined exact FD/SPSA statistical and production-decision parity.
- Defined t=0 paired replay, run identity, action epochs/levels, dynamic gates, and runtime deadline.
- Added one dependency graph, gate summary, and v2-to-v2.1 traceability.

## Deliberate choices

- Kept the 30/45-second runtime targets as promotion gates while labeling current evidence NO-GO.
- Used original 25% initial and 15% promotion urban queue/storage thresholds, with stricter physical conservation as a separate invariant.
- Did not adopt the signal review's erroneous SC12 left-only conclusion.
- Did not implement plant source code in this documentation task.

## Verification

- `git diff --check`: PASS.
- Final reviewed Markdown line count after fix loops: 721.
- Contradiction search confirms no S0-complete claim, arbitrary active program 0, SC12 left-only claim, or stale missing-speed task remains.
- Baseline unit evidence is scripts 21/21, root tests 9/10, and plant 75/75: 105/106 overall. The known stale snapshot expectation is explicitly the first S0R blocker.
