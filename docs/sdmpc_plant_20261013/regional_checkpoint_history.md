# Regional cut-boundary S-DMPC checkpoint

Baseline: `d2ca825a2dbe2e776e9509cddcb47b411a5c75af` on `codex/solo355-local-information`.

This is an offline prototype. A diagnostic-only tangent-worker branch imports
it under `regional_prediction_prototype`; normal adapter and SDMPC dispatch
do not enable that setting. Existing actuator-only configs are unchanged. No native run,
queue dispatch, freezer, publication, deletion, or push has occurred.

The connector entrance is the split: freeway owns mainline and onramp stock;
urban owns urban roads and offramps. `project_state` copies the allowed physical
objects together, preserving aliases between the urban solver and its offramp
view. Opposite-region runtimes are absent. Zero shape-only shells satisfy
unchanged component APIs and do not contain observed remote quantities.

The inlet is the exact entrance crossing count of the last closed150-second
window, held constant as a future arrival request. It is **not capacity**.
Each local finite receiving limit still applies. Unadmitted requested vehicles
remain in an explicit external arrival backlog. Tests check requested =
admitted + rejected, including a1000-times inlet stress case.

The freeway outlet assumes free discharge up to the adopted static freeway
capacity; the urban outlet offers the adopted static ramp capacity without
remote ramp stock or head/receiving-wave history. Local source congestion and
finite urban road/offramp storage remain in their existing equations. These
are boundary approximations: downstream spillback cannot be inferred from an
entrance count. In particular this assumption does not establish that joint
control is necessary or that either solo controller performs well in VISSIM.
Incoming10638 route classes use the existing `unrouted` law; route/lane tags on
already locally owned vehicles are retained.

The adopted FW5/urban10 physical equations and10-second residence/arrival
quadrature are retained. No new calibrated interior model or numerical
coefficient has been introduced. Reverse AD differentiates the cut dynamics.

`test_regional_prototype.py` passed6 tests in59.607s on saved900 and4500:
closed-window boundary validation; opposite detector exclusion; disjoint,
complete initial stock partition; complete trajectory equality after hidden
opposite-state and demand-forecast perturbation; own-queue sensitivity;
finite-storage/rejected-arrival conservation under overload. This is a
projected-state proof, not yet an upstream observation/compiler proof.
The later solver checkpoint below exercises the real persisted price loader
with an offline receipt fixture; this is not native application evidence.
New inlet lane shares use exact closed-window boundary counts; zero counts
use static uniform shares with zero requested flow, never stale urban offers.

`regional_query_probe.py --mode MODE --output FILE` exercises the actual Query
and tangent worker with all48 freeway or189 urban axes across three blocks.
Saved900 AD responses completed in5.82/9.95s (single candidate, not optimizer).
Regional coverage is explicitly declared:180 freeway and900 urban allocation
visits, no remote frames. Quantities contain only the active regional resource.
The current regional cost matrix has3 freeway or18 urban rows, including
PASSIVE_OMEGA for own-region unassigned stock in the merit/derivative. This is not global Omega701 prediction.
Current worker requests remove follower caches and restrict bootstrap fields.
Full cfg provenance is still a caller obligation, so this is not an end-to-end
local-information or controller-result qualification.

`regional_prototype_probe.py --ad --mode MODE --output FILE` runs a small
two-axis reverse-AD probe. `--capture` selects the captured saved-state pickle.
The default capture is the parent-provided projected900 fixture.

The regional Registry, accepted-resource budget initialization/binding, active
owner costs and passive gradient, central active-resource mask, canonical
callbacks and three-block command evidence are connected to `sdmpc.solve`.
The inactive resource has no dual update, QP bound, recovery row or leader
proposal. Its zero compatibility slot is explicitly reported inactive.
The distributed S-DMPC/PFO/leader algorithm and default dispatch are retained.
The adapter does not yet create or enable the audited regional input context.

`regional_contract_probe.py --mode MODE --output FILE` runs the complete
48/189-axis AD response, own Registry, warm budget binding and actual command
checks for each of three blocks. Saved900 receipts passed with216/4896 state
constraints and feasible commands in5.84/9.52s. Each probe evaluates one
admissible seed, not a full optimizer selection. Urban uses the existing own
storage guard's operating seed. `--entry-only` separately proves actual
`sdmpc.solve` reaches PFO without invoking the old coupled predictor; it
intentionally stops before optimization. The focused regression suite passes
61 tests. Evidence and exact limits are in
`.superpowers/sdd/solo355-local-plan/task-4-report.md`.

Saved4500 contains prior mixed-control commands. The command checks correctly
reject its inactive urban greens/freeway meter commands. A future counterfactual
fixture may retain its measured own state and active command history while
explicitly restoring inactive baseline; it cannot be described as the actual
historical native control at4500.

Outstanding before qualification or activation:

- Audit and filter retained cfg and nested runtime configuration, callback
  context/history/caches, including freeway per-road control-area context.
  Trace retained dynamic values from own raw observations and replay projection;
  changing raw after projection alone does not prove independence.
- Add the canonical opt-in input factory and adapter startup0/1s/failure-hold
  paths; establish inactive native baseline from the start of a new local run.
- Compare complete decision context, bounds, leader domain, callbacks, active
  prices and fresh response/Jacobian under opposite-input mutations. Confirm
  own sensitivity and document the causal outlet closure.
- Only then run one full saved900 selection per mode, save compact qualified
  evidence and complete the final tracked/untracked source closure.

The existing finite executable VSL secant fallback and meter-neighbor audit
remain policy features; no regional continuous AD is replaced with finite
differences. Full-selection fallback counts are not yet available.
Whole-network Omega701 remains a separate posthoc native-evaluation scope.
Native runs, freezer dispatch, queue dispatch and full selections remain zero.
