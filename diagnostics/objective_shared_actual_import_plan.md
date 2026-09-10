# Pending production application and direct-import test migration

**Completed:** parent subsequently authorized application; both patches and the direct-import conversion are now integrated. Combined39 tests passed with source changes empty and no proposal modules loaded. See `objective_shared_production_validation.md/.json`. The following records the preparation plan, not an outstanding application request.

Status: preparation only, after the existing beta0 run completed5400. Parent will explicitly release the production freeze after comparison. No production patch, test-loader migration, model rollout or optimizer has been executed in this preparation step.

## Owned application scope

Apply the reviewed `area_leader_objective.patch` and current superseding `shared_service_pool.patch` once, after parent authorization and a fresh applicability check. Their production targets are disjoint except for runtime installation dependencies:

| Patch | Production targets | Reviewed patch SHA256 |
|---|---|---|
| area_leader_objective.patch | new area_leader_objective.py; area_runtime.py; terminal-cost installer in canonical adapter | edf74d9204e764015f00e8bec00ebd90279124da915455e48df780b0dbdadea3 |
| shared_service_pool.patch | new local_signal_service.py; route_choice_corridor.py; runtime_setup.py | a4f1abf91fe6c8393fbd2c9c9408262803a108a0dbaf253a39ddb26672024f29 |

All paths above are under evaluation/controllers. No vendor changes or adapter copies are needed. Flow's calibration and root's landing-clock patch remain separately owned; parent coordinates their order. No active config, manifest or runtime input is part of this ownership.

## Direct-import conversion after application

`test_area_leader_objective.py` currently has an automatic production-file branch but still imports the proposal builder. Remove that fallback and builder import entirely. Import `evaluation.controllers.area_leader_objective` directly, call the actual adapter terminal installer and actual `area_runtime.install`, and inspect actual `area_runtime.py` for the endpoint-purity contract. Keep the explicit endpoint response fixtures and actual Wu PFO method regression; they test consumer composition without pretending to run a physical endpoint. The fresh child process must import the canonical module name directly. Preserve original OFF callables and every method-restoration context.

`test_shared_service_pool.py` currently compiles patch sections in memory. Remove `patch_sources`, generated ModuleTypes, source execution and module substitution. The test context should import the three actual modules and only restore the class/function hooks installed during each test. Replace the setup source list with explicit canonical helper/runtime/route files plus the existing vendor references. Both worker tests must import actual modules, unpickle only after the helper class is available, and call the actual `runtime_setup.install_worker_runtime`. Keep the actual default phase flag, SC1004-only activation and exception/nested-context checks. Do not set ramp_aware_phase_resolved=True in the fixture.

`probe_model_area_integration.build_projected` already calls actual `runtime_setup.configure_runtime`; it no longer extracts main AST or loads proposal sources. The legacy fixture alias in the objective setup and the explicit live900 inputs in the shared setup retain their respective declared provenance. Neither needs an alternative runtime initializer.

## Validation and evidence

Run the focused objective14 and shared25 tests, including actual fresh-process ON/OFF checks, after conversion. Repeat only for new failures or source changes. Neither suite performs an endpoint rollout, full optimizer or VISSIM run. Parent separately owns the later configured main preflight and full simulation.

Write new production-validation JSON/MD with actual imported module paths and SHA256, tests executed, unchanged production-source pins, and the explicit fixture/consumer scope. Do not overwrite `shared_service_ready_validation.json`, which pins the historical unapplied proposal result. The new direct-import tests must fail when the canonical module is absent instead of silently falling back to a proposal.

Before/after checks cover only approved files, using explicit paths. Do not stage or commit; send parent the exact changed production/test/report paths and results. Existing handoff SHA tables remain historical unless a new integration record explicitly supersedes them.

## Corrected meter interpretation

The2550 numerical intent/realized difference is retained, while the former confirmed-violation claim is withdrawn in `area_leader_objective_patch_handoff.md`. The7200 intent box and1800 grouped request limit are not established as hard realized-rate caps. Guard and discrete table behavior are unchanged by these patches; no scalar clipping or new capacity bound is authorized by this preparation.
