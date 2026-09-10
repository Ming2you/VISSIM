# Shared pool + ready transit handoff — unapplied

**Integration update:** the superseding patch `a4f1abf91fe6c8393fbd2c9c9408262803a108a0dbaf253a39ddb26672024f29` is now applied after parent released the completed-run freeze. The shared25 and objective14 tests passed together using actual production imports, including fresh worker ON/OFF checks, after Flow's calibration and Hubble's observer hooks were saved. Current evidence is `objective_shared_production_validation.md/.json` and `shared_service_ready_production_validation.json`. The original unapplied validation JSON and the preparation details below remain historical evidence.

`shared_service_pool.patch` **supersedes** its previous version. Apply it once to the current production baseline; do not apply the archived old patch first. It still introduces only one canonical helper, `evaluation/controllers/local_signal_service.py`, with small `route_choice_corridor.py` service and `runtime_setup.py` installation hunks. The helper is 611 lines including the already proposed single extracted ramp-aware stepper; no vendor, adapter, global urban drain, global Ω accounting, or other local-plant copy is changed.

The previous patch/test raw bytes are preserved in `shared_service_pool_pre_ready.zip`, with original length/SHA manifest, CRC validation and member-byte comparison. Its old patch SHA was `6bd3df267bd13aa2c3dfd5a3f19e16e048478586fc96fd42ca0c79677a2c962a`. The archive is historical evidence, not an executable source dependency.

## What the opt-in now guarantees

`urban.shared_local_service_pool: true` retains the evidenced SC1004/connector10634 group and the existing configured rate, turning fractions and receiver. It requires the physical signal contract. Global service still uses its existing correct maturity implementation. The local helper uses the same due<=service-step meaning, verified against actual canonical global drain on copied state900.

`ReadySeed` is an immutable per-solve snapshot of start index, Tu, Tf/Tu, canonical inflow delay, exact storage/capacity/initial counts, direct shares and due reservations. Every candidate creates fresh pending dictionaries. No pending state is stored in the shared config/model or inherited from a previous candidate. Initial physical stock remains unchanged; pending vehicles remain in own-TTS and in the untouched global Ω inventory/residence. Only discharge eligibility uses `stock − future_pending`. Accepted source departures alone reduce stock and consume shared service/receiving budgets.

New local arrivals use the existing frozen **gross group offered rate**. At each Tf boundary, the existing direct share is applied once; only the signal branch is offered to local OR storage. Acceptance is limited by existing storage space, and the same accepted vehicles are reserved at `admission_step + canonical_delay`. Landing occurs **after** that urban substep's service/cost, matching global urban-before-FW ordering. At the current 900 start, the first block lands at910 and matures at945; it cannot be served at905. No extra capacity, fitted delay, route split prior, FD or speed correction is introduced.

The rejected amount is not silently called accepted or an exit. Optional `ready_trace`/`ready_diagnostics` provide exact offered, accepted, rejected, overflow and conservation values. Actual Link.solve output also receives `shared_service_ready_candidate_count`, `overflow_candidate_count`, and `candidate_max_*` numeric diagnostics in the response and control. Those summarize **searched local candidates**; they are not selected physical flow or measured traffic. A small response-interface fixture tests only this output transport and exception restoration; it does not pretend to execute a full solve.

## Actual caller attachment and concurrency scope

The original green and ramp-offset methods are delegated to, not copied. Scoped ContextVars bind the exact caller state/model seed and reset in `finally`. The phase-refinement setup passes the same seed explicitly. The same installer runs in the worker, where the seed is rebuilt from its serialized state. The final regression uses actual default `ramp_aware_phase_resolved=False` and does not manually turn it on.

One required adjustment was exposed during review: the original ramp green solver chooses cycle-average service unless `ramp_aware_phase_resolved` or its per-signal active set is enabled (`wu_faithful_follower.py:853–860`). Merely setting `phase_price.ramp_local_model=ramp_aware` controls refinement and does not prove this green branch is enabled. Under the pool flag, the entry wrapper temporarily adds **only SC1004** to `_phase_resolved_active_signals`, delegates to the original physical-profile/platoon branch, then restores the exact prior set object on success or exception. Other signals and OFF retain their original path. Static initialization alone is insufficient: vendor.solve resets the active set at `:4150` on every solve.

The active Wu implementation calls the same follower's signal agents sequentially (`wu_faithful_follower.py:4338`, and local/residual loops3739/4714). Wu candidate evaluation reports a serial backend (`stackelberg_wu_metered.py:2755–2758`). Price parallelism uses `ProcessPoolExecutor`, with controller/state passed through each process initializer (`:623`, `priced_wu_link_controller.py:955`). Thus this scoped instance-set change is safe for the verified current execution path. ContextVar by itself does **not** make that mutable instance set thread-safe. Concurrent thread solves sharing one follower are not supported or claimed here; base StackelbergMPC's separate generic ThreadPool path is outside this verified Wu path. No blanket all-signal True flag or hidden test-only activation is used.

## Reproduction and limits

The final suite has **25 PASS**, 5.258 seconds, plus `git apply --check` PASS. No production files, config/input data or Git index were changed. `shared_service_ready_validation.json` records the exact patch SHA and representative traces. All pre-existing pool tests remain, including accepted-only consumption, partial greens/receiver limits, source order, OFF lifecycle, malformed physical profiles and stale refinement-context rejection.

New tests cover actual default green single-candidate, ramp offset single-candidate and refinement seed identity; canonical global due-now/next source priority; immutable candidate copies; pending residence; FW block and maturity boundaries; finite receiving rejection; nested/exception context restoration; actual worker ON and OFF local-caller equivalence; serialized direct-kernel worker equivalence; and output diagnostic scope. These are bounded local evaluations, not a network MPC or price endpoint. The worker's ON cost differs from OFF as expected; each worker exactly matches its respective same-mode parent calculation.

For a synthetic empty OR_F_W and720veh/h gross offer, a10-second block offers2 vehicles, splits into0.968 direct outside this local OR and1.032 signal vehicles using the existing0.484 direct share. Signal acceptance first appears at step182 and eligibility at189. Ten local substeps accept5.16 signal vehicles with zero rejected and zero stock residual. A separate full-storage/red case rejects its signal offer, creates no pending reservation, removes no stock and records one overflow block.

Remaining limitations are explicit. Initial observed OR buffers are empty, so this does not infer unobserved initial travel age. The future boundary is still a frozen offered-flow approximation; rejection here does not reproduce the full coupled FW backlog. Direct branch stock and its receiver are outside this signal-local OR accounting, as before. External receiving renewal, upstream arrival profiles, on-ramp approximations and phase-local objective scope are not promoted to complete global-horizon equivalence. The separate `LocalLandingState` clock fix is required for its own freeway-local path and is not contained in this shared patch.

## Calibration and safe application order

Recommended root sequence, after production freeze ends:

1. Apply the **current superseding** `shared_service_pool.patch` once.
2. Apply Flow's `sc1004_resource_service.patch` after its independent evidence/tests pass.
3. Apply the independent `local_landing_clock.patch` after root review.

The first two patches edit separate regions of `route_choice_corridor.py`. In-memory strict hunk application in both orders produces identical combined route source; `shared_service_ready_patch_order.json` pins those patch versions. This is mechanical applicability/compile validation, not a combined configured endpoint claim. At runtime, calibrated corridor configuration still precedes local pool configuration. The pool reads a single identical `turn.service_veh_h`/movement-capacity value; it never hardcodes619.59 or1509.33, multiplies by the three aliases, or recalibrates it.

A configured10634 `calibrated_service_resources` requires the shared pool in both main configuration and worker installation; missing/OFF pool fails explicitly. Legacy OFF without this new calibration remains exact. Calibration's train-only derivation and evidence are Flow's separate responsibility; this handoff does not call the observed rate a validated saturation capacity.

Use new contract-candidate configurations as root directed; do not overwrite the baseline area-candidate fixtures. After integration, switch these tests to actual imports before doing a full main preflight.

## Independent review of the small landing-clock patch

Moving `self.step += 1` to the end of each `LocalLandingState.advance` urban iteration preserves its post-two-step FW boundary182 and new OR due189. It also corrects receiving travel reservations: the existing `_schedule(receiving, value, _link_delay_steps(...))` now uses the current service boundary, matching global accounted drain's `arrival_step = step_idx + delay_steps` (`urban_flow_accounting.py:113–118`). Moving the initial index to179 instead would not be equivalent.

The added peer test `test_local_landing_clock_receiving.py` reuses root's pending-method selector and actual delay calculation. A declared1-vehicle accepted service at boundary0 enters the receiver once, schedules at0+3 (not1+3), preserves source+receiver stock and advances the object's next boundary to1. **1 PASS /0.003 seconds**. The accepted-service amount is an explicit tiny fixture; this test validates clock/schedule/conservation, not signal saturation or full receiving-model fidelity. No actionable clock-hunk contradiction was found.
