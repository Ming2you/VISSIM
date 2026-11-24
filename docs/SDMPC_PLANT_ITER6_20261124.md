# S-DMPC and plant snapshot: 2026-11-24

This experimental branch builds on `codex/sdmpc-vsl-selection-20261123`. It updates the controller and plant/runtime initialization used by the in-progress fifteen-condition simulation queue. It is not a production release or a completed performance comparison.

## Iteration policy

The lower S-DMPC follower runs at most six iterations per budget candidate. After accepting an improved feasible point, it stops that candidate when the relative improvement in predicted network objective from the previous feasible point is at most 0.001. It records `relative_improvement_at_most_0.1pct`; this is a stopping rule, not proof of global optimality or convergence. The PFO iteration limit remains two, and the existing budget candidate, physical, discrete and final validation mechanisms are retained.

## Recorded initial-state approximations

SC1001 mixed physical ownership is handled using the existing modeled owner fraction uniformly over observed vehicles on that link. The other stock owners are retained. Individual destination ownership is not observed; the approximation and its per-link counts and shares are recorded in `sc1001_degraded_ownership`.

SC105 can reconstruct a missing initial arrival calendar from complete current vehicle records where recorded source and ledger stock are consistent. Where a physical link has mixed ownership, its source share is applied uniformly over records. The `sc105_degraded_initialization` receipt records missing calendars, reservation differences, ready-queue differences and fractional owner shares. These are approximations, not repaired observations.

Each decision records `degraded_area_stock_audit`: observed Omega vehicles, modeled initial Omega stock, their signed difference and unmapped record count. The experiment intentionally allows a nonzero difference and does not silently correct it. In a saved 1.2-demand state at 4,500 s, the offline check found 4,778 observed versus 4,763 modeled vehicles; it records the -15 difference and continues. This is a material limitation of the prediction. Incomplete records, conflicting stock ownership, invalid commands and violated final physical constraints can still fail; this experiment does not promise that all errors are ignored.

A group whose screening QP fails is retained for optimization, with the failure receipt stored rather than assigning a zero sensitivity. A failed pre-selection owner QP may still prevent price initialization. PFO retains its existing verified-warm-start handling.

## Verification and provenance

The source is the runtime freeze with manifest SHA256 `9a99bd7a9964e4aeb6b717abbaa6689f697fb68197270cad64d062e3cfe41e6e`, local package commit `ea11f0666ccfdb2678de9832f40db09b5a652775` (not a parent of this Git branch). Some Windows line endings are normalized for the repository. The default network, demand profile, VSL finite-step screening and other plant components remain those of the parent snapshot.

Saved-state checks covered the SC1001 41 observed / 31 assigned mixed link, SC105 missing calendar and mixed ownership, and an offline full 1.2-demand 4,500 s decision. That full decision used explicitly cold dual prices because the saved prior policy differs: it selected a feasible command, passed NP/NUF checks and had one candidate stop after two iterations on the 0.1% rule. It does not establish native VISSIM performance.

The native queue comprises demand scales 1.0, 1.1 and 1.2, each with no control and pre-PFO selection thresholds 0, 0.01, 0.05 and 0.1. These runs were in progress at publication. No completed native result or TTT benefit is claimed here. Prior runs and user worktrees are not altered by this branch.
