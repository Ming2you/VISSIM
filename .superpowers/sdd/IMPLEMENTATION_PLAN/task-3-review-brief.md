# Task 3 whole-plan review brief

Review the integrated `IMPLEMENTATION_PLAN.md` against the following gates.

## Spec compliance

- The deliverable is a rollout plant for MPC: state projection + controller-independent dynamics + lever response, while MPC owns action selection.
- VISSIM microscopic trajectory identity is not required; conservation, signal/time semantics, congestion propagation, lever-effect sign/magnitude/ranking, and operational latency are required.
- S0 is not marked complete while tests, hashes, source identity, strict runner, canonical signal reference, or SC12 evidence remain open.
- SC12 source lane 2 is shared through+left: connector 10241/10238 has two connector lanes and carries lane-2 through traffic, while 10242/10240 carries lane-2 left traffic. Lane-2 movements obey head 50201/SG5 or 50601/SG1; SG-pair equality is a profile policy, not a physical invariant.
- Physical stock is represented once. Ownership, visibility, control, and objective attribution are separate views.
- Calibration and certification are disjoint by whole run.
- Native per-SC cycles precede native fidelity tests. Normalized-150s evidence cannot promote native behavior.
- Offset stays disabled per profile until exact timing/readback and paired VISSIM effect/ranking gates pass for that same profile.
- Paired VISSIM futures replay from t=0 and prove identical prefixes before action application.
- Exact FD and SPSA evaluate the identical production endpoint/objective and compare both gradients and final decisions.
- Runtime is measured around production `decide_with_info`, with a 45-second hard deadline, explicit fallback, and no silent parallel fallback.

## Executability

Every blocking task states inputs, implementation paths, command, artifact/schema, dependencies, quantitative PASS/FAIL/NOT_EVALUATED rules, and stop condition. Search for vague terms such as `threshold below`, `later decide`, or aggregate-only gates.

## Internal consistency

- Body, gate table, dependency graph, and traceability table agree.
- Initial acceptance versus promotion targets are labeled and do not conflict.
- Required low-demand metrics are not waived merely because spillback is absent.
- No H=1, demand, seed, channel, or lever failure can be hidden by pooling.
- Runtime target is a promotion requirement, not claimed feasible from current evidence.
- Commands and referenced paths exist or are explicitly marked as new deliverables.

## Verdict contract

Report Critical/Important/Minor findings with exact file:line and replacement text. Approve only if both spec compliance and document quality pass. Write the report to the path supplied by the dispatch prompt.
