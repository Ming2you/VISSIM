# Independent review: final shared refinement installation

No additional blocker was found for the current single-config main process and workers receiving that same cfg. The two production hunks restore the intended SC1004 ready-seed path after the adapter's late ramp-aware installer. This is a source/connection review plus one bounded local-cost lifecycle probe, not another full-MPC success claim.

Reviewed `local_signal_service.install_refinement`, the end of `build_priced_wu_link_controller`, the later actual main calls, worker bootstrap, and `test_shared_service_main_stack.py`. No production or index writes were made. Source hashes and exact probe results are in `shared_service_main_stack_peer_review.json`.

- The final builder hook runs after every phase adapter. Actual main subsequently installs terminal cost and worker bootstrap; neither writes these three phase methods.
- The helper checks context, setup, and cost markers together. If the late adapter replaced setup/cost, it reinstalls those wrappers while retaining the already installed context wrapper. Same-config repeated installation does not stack context wrappers.
- SC1004 setup supplies an explicit `ReadySeed`, so price refresh does not depend on a follower-solve `ContextVar`. SC1001 and other non-pooled signals delegate to the existing setup/cost. The new test verifies SC1001's cost before/after reinstall.
- Cold OFF exits before changing any method. Fresh worker deserialization invokes the actual controller bootstrap, which calls the common shared installer and restores the explicit-seed setup/cost. The new fresh-interpreter test exercises SC1004; the author separately reports actual v2 state900 local refresh across 17 signals. I did not rerun those whole test suites or their endpoint stubs.

## Reproduced scope boundary

One mixed-config lifecycle remains unsupported. Using the actual `built_inputs()` fixture and builder, in one isolated Python process:

| Operation | Result |
|---|---|
| Construct ON controller and score its SC1004 setup | 21.05318282418348 veh·h |
| Construct a separate OFF cfg/controller, then reuse the original ON controller | `ValueError: Shared service caller is missing its own ready context` |
| Explicitly reinstall ON shared refinement and repeat | 21.05318282418348 veh·h |

The bounded probe took 2.43 s. It ran actual local costs only; no endpoint, full optimizer, VISSIM, or source mutation.

The older ramp-aware adapter writes class methods. An OFF controller built after an ON controller replaces setup/cost globally, while the final OFF guard correctly remains a no-op for its own cfg. The retained ON instance then reaches the shared rollout dispatcher through the older setup, which supplies no ready seed. This does not occur in the current one-controller-per-main-process path or same-config worker restoration, so it is not a blocker for the current preflight. It should remain a documented limitation of mixed-config controller reuse; a future owner-aware or instance-scoped installer can address it separately without relaxing missing-context validation or changing cold OFF behavior.

The parent explicitly chose to retain the production freeze and document this boundary. The numerical source/rate, physical capacity, receiving constraints, and clock behavior are outside these two installer hunks and were not changed or recalibrated during this review.
