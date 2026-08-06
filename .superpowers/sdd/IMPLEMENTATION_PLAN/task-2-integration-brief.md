# Task 2 integration brief

Target: rewrite `IMPLEMENTATION_PLAN.md` as an executable v2.1 plan without implementing plant source code yet.

## Binding requirements

1. Reopen S0. Require 31/31 baseline tests, strict gate propagation, runtime import/snapshot consistency, semantic or normalized-EOL NumSim comparison, and hash-bound evidence.
2. Make the SC12 physical decision and reproducible signal-reference generator explicit blockers before movement mapping and dynamic validation.
3. Replace arbitrary `active_program: 0` with a time-indexed program schedule bound to `.inpx`/`.sig` provenance. Validate each SC/program exactly; retain 0.851 only as an aggregate regression statistic.
4. Define movement-stage coverage thresholds, unresolved treatment, and a single conserved physical stock contract for shared links.
5. Correct the speed task: VBS and adapter already expose `link_speeds_kph`; remaining work is rollout delay initialization/evolution and a no-zero-delay test.
6. Specify finite exit/boundary-out state, supply/backpressure semantics, mass identities, and objective-included/excluded parallel reporting.
7. Specify calibration run IDs, train/holdout split, estimator, uncertainty, and acceptance thresholds for jam density, storage fractions, and ramp capacity.
8. Make native per-SC cycle support a prerequisite of native fidelity J/K. Either validate native offset as a production lever or disable it in native production; normalized 150-second experiments cannot promote the native plant.
9. Define paired-future replay from t=0, anchor-prefix parity, action effective time/duration, exact perturbations, canonical run key/schema, sampling cadence, ties, minimum support, and per-demand/seed/anchor/horizon/channel aggregation.
10. Restore all quantitative gates: projection, one-step urban/freeway, multi-step bias/growth/timing, ranking, spillback support/F1, runtime, timeout/fallback, and low-demand NOT_EVALUATED rules.
11. Make SPSA parity executable: equal endpoint/objective, repeats/noise floor, material threshold, sample independence/count, normalized RMSE denominator, regression rules, per-channel/demand/horizon reporting, exact 95% sign-error upper bound, N-phase tangent coordinates, and production decision/certification/fallback parity.
12. Make runtime work deadline-aware: worker timeout/cancel, spawn-safe tests, serial-fallback telemetry, rollout-count accounting, workers 0/1/2/5 parity, end-to-end `decide_with_info` timing, and an evidence-based path from 154.746 seconds to the stated p95/max targets.
13. Every task must state inputs, implementation paths, command, artifact/schema, numeric verdict, prerequisites, and stop condition. No unresolved phrase such as `threshold below` may remain without a value.
14. The dependency graph and promotion rule must agree with the body. Any physical/network decision not proven remains `BLOCKED` or `NOT_EVALUATED`, never PASS.

## Deliverables

- Updated `IMPLEMENTATION_PLAN.md` titled v2.1.
- A v2-to-v2.1 traceability table that maps every binding requirement above to a section.
- No source-code changes in this task.
