# Shared ready setup survives the actual main installer stack

The failed 900-second full MPC preflight exposed an installer-order defect. This repair is applied to canonical production code. The bounded regressions pass; a new full MPC preflight remains necessary.

`configure_runtime` first installs shared local service. Later, `build_priced_wu_link_controller` installs the older ramp-aware phase adapter, replacing the shared phase setup and cost methods. Its setup has no `ReadySeed`. Price refresh runs before follower `solve`, outside the solve's context binding. Consequently the actual stack reached adapter `patched_cost` and correctly failed with `Shared service caller is missing its own ready context`.

The new test first reproduced this exact error **before the repair**, using the actual controller builder. The prior 25 tests constructed the vendor follower directly and did not include these late main installers. They were insufficient integration coverage.

The builder now installs the existing shared refinement wrapper last, after its phase adapters. Only the configured shared signal uses the common setup/cost with an explicit state-derived ready seed. Other ramp signals still delegate to the adapter's ramp-aware implementation. The helper checks all three installed methods and avoids wrapping the existing context method again. Flag OFF does not install anything. No empty ready fallback, timing rule, capacity, stock equation, vendor file, runtime configuration or evidence data changed.

Production scope:

- `evaluation/controllers/vissim_stackelberg_adapter.py`: four added lines at the end of `build_priced_wu_link_controller`.
- `evaluation/controllers/local_signal_service.py`: OFF guard, complete wrapper-presence check and idempotent context reinstallation.

`runtime_setup.install_worker_runtime` already calls the shared installer. A real controller pickle invokes its existing `__setstate__` bootstrap in a fresh interpreter; the regression exercises that path without replacing the worker initializer. No new runtime setup path was necessary. The helper retains its original CRLF bytes policy and the adapter retains LF.

Validation:

- Original shared-service 25 + actual main-stack 5 + landing-clock 5: **35 tests PASS, 15.530 seconds**. Includes pending stock/due boundaries, future FW block admissions, candidate isolation, missing-context rejection, ON/OFF worker restore, unchanged SC1001 cost, and repeated installation.
- Failed-manifest replay: `diagnostics/shared_service_actual900_main_stack.json`, **PASS, 18.319 seconds**. It uses the exact NC v2 state900, action750 and contract v2 configuration from the failed command. Actual `configure_runtime`, controller builder, terminal installer, bootstrap and phase refresh run in order. All local phase costs run; SC1004's five calls carry identical ready seeds with no bound solve context. Input state/action/demand objects and source/data bytes remain unchanged.
- The replay stubs only global finite-difference values to zero (63 tasks are explicitly **not executed**). Its resulting prices are not valid optimization results. A fresh interpreter unpickles the actual controller and reproduces the same local score/seed. This establishes the installer and local consumer contract, not full MPC success or traffic performance.
- `git diff --check` passes for both changed production files.

The failed full preflight is preserved at `diagnostics/area_production_preflight/wu-link_t900_beta0_20260910T015723765013Z/manifest.json` (exit 1, 60.344 seconds). Its source/input unchanged and zero surviving-worker assertions remain valid historical evidence. The before-repair production hashes are in `shared_service_main_stack_before.json`.

Reproduce bounded verification:

```powershell
python -X utf8 -m unittest diagnostics.test_shared_service_pool diagnostics.test_shared_service_main_stack diagnostics.test_local_landing_clock diagnostics.test_local_landing_clock_receiving -v
python -X utf8 -m diagnostics.probe_shared_service_main_stack --manifest diagnostics/area_production_preflight/wu-link_t900_beta0_20260910T015723765013Z/manifest.json --output diagnostics/shared_service_actual900_main_stack_NEW.json
```

The new output must not already exist. Historical evidence and E8 diagnosis were not overwritten. Git staging/commit and full MPC retry remain with the parent task.

Subsequent independent review found a remaining mixed-controller lifecycle limit: in one interpreter, build an ON controller, then build a different OFF controller, then reuse the first ON controller. The second builder replaces class methods and its OFF final hook intentionally does not install wrappers, so the first controller can again fail the ready-context check. Reinstalling for its ON cfg restores the same cost. The current actual main creates one controller per process and the tested worker restores that same cfg; this is not a blocker for that lifecycle. Mixed ON/OFF controller construction and reuse in one interpreter is not covered as supported behavior. No production change was made after the freeze to address it.
