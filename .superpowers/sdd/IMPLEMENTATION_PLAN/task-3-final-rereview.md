# IMPLEMENTATION_PLAN Final Narrow Re-review

## Scope

This review is limited to the six findings from `task-3-final-whole-plan-review.md`. No new scope or unrelated findings were considered.

## Findings

### C1. Production MPC endpoint ownership: PASS

`IMPLEMENTATION_PLAN.md:414-436` now assigns an explicit blocking task, H, to a new production endpoint at `vendor/NumSim-mine/src/simulation/production_rollout.py`. It requires integration into `stackelberg_mpc.py`, `stackelberg_wu_metered.py`, and the adapter's real `decide_with_info` path; preserves MPC ownership of candidate generation, objective comparison, and action selection; routes leader/follower, exact-FD, SPSA, no-control, and audit scoring through the same endpoint; and forbids direct production bypasses. The H execution-contract row at `IMPLEMENTATION_PLAN.md:689` adds the verifier artifact, channel coverage, zero-bypass gate, and blocking prerequisites. I-0/I-1 and CERT-PREP explicitly consume H at `IMPLEMENTATION_PLAN.md:690-693`.

### C2. Paired VISSIM schedule parity: PASS

`IMPLEMENTATION_PLAN.md:535-560` requires the paired harness to obtain the exact production `ActionSchedule` emitted by H and makes plant and VISSIM consume byte-identical schedule entries, activation boundaries, half-open intervals, move-blocking/walk behavior, and restoration commands. Prefix equality is tied to the first effective transition rather than a fixed `anchor+1`. `IMPLEMENTATION_PLAN.md:567-569` correctly holds the current move-blocked action through `[anchor_sec, anchor_sec+60*H)` while making any different production schedule authoritative. The J execution row at `IMPLEMENTATION_PLAN.md:698` runs the registered branches from `t=0` using that exact schedule and blocks partial cells.

### I1. Producer and workload enumeration: PASS

`IMPLEMENTATION_PLAN.md:328-345` defines an executable DEV-DATA producer for the four named development manifests plus `development-campaign-v2.1`, covering six calibration parents, three qualification-only parents, four anchors, and at least 20 independent base replays per parent-anchor. I-0 at `IMPLEMENTATION_PLAN.md:440-446` produces the SPSA and runtime request manifests. The role matrix at `IMPLEMENTATION_PLAN.md:351-362` totals 18 disjoint physical parents: 6 calibration-development, 3 qualification-only, and 9 certification. CERT-PREP/CERT-WAVE at `IMPLEMENTATION_PLAN.md:693-694` freeze and link 9 parents, all enumerated paired children, 108 decision twins, and every runtime stratum with at least 100 attempts and 10 independent VISSIM runs. J now has an actual `t=0` campaign runner at `IMPLEMENTATION_PLAN.md:698`; evidence inferred from an incomplete or parent-only campaign is expressly blocked.

### I2. Lever-effect magnitude and noise gate: PASS

`IMPLEMENTATION_PLAN.md:330-344` preregisters at least 20 independent `t=0` base replays per development parent-anchor and freezes the conservative pairwise-max noise floor before certification; repeats do not inflate support. `IMPLEMENTATION_PLAN.md:587-598` applies that frozen noise floor to paired effects and blocks incomplete arms. `IMPLEMENTATION_PLAN.md:623-630` adds the requested per-`demand x H x channel x certification_seed` material-effect support, `effect_NMAE <= 0.25`, absolute signed-effect bias `<= 0.15`, 100% material sign agreement, and both point-estimate and parent-then-anchor cluster-bootstrap lower-bound gates for Spearman and top-pairwise ranking. Pooling cannot rescue a failed stratum or lever.

### I3. Offset-enable artifact: PASS

The policy at `IMPLEMENTATION_PLAN.md:321-326` keeps production offset writing `intent_only` until same-profile D-core, paired offset effect/ranking, and runtime evidence pass, and rejects non-promoted profiles fail-closed. The D-offset-enable execution row at `IMPLEMENTATION_PLAN.md:699` provides a concrete issuer command, profile-scoped `offset-enable-v2.1` artifact, exact evidence/code hashes, and an adapter/VBS startup guard. Requested offset enablement exits nonzero for invalid evidence; stale, normalized, cross-profile, or `NOT_EVALUATED` evidence remains `intent_only`. K explicitly consumes the offset disposition and requires enable PASS when offset is requested at `IMPLEMENTATION_PLAN.md:700`.

### I4. Fallback current-state revalidation: PASS

`IMPLEMENTATION_PLAN.md:516-523` now copies only the last feasible payload, binds a fresh command to the current observation and state hash, and revalidates topology/profile, authority, current phase, min-green/conflict, actuator bounds, mass state, spillback guard, and the safety certificate before COM application. Any failed check selects the validated native fixed plan; repeated failures latch it, stale CSV/hash reuse is forbidden, and generation through readback remains inside the hard deadline.

## Verdict

**APPROVED**

All six previously reported findings are substantively resolved in the current `IMPLEMENTATION_PLAN.md` by owned implementation tasks, executable producers/runners, machine-readable artifacts, quantitative gates, and fail-closed prerequisites.
