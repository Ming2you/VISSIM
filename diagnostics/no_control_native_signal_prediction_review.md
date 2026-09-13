# No-control prediction does not currently replay the native selected signals

The mismatch is present in the live no-control prediction path as well as the diagnostic replay. Dropping action metadata in the replay helper is not its sole cause. The actual no-control plant keeps native urban SIG ownership, while the prediction uses the serialized equal-green, zero-offset action for the selected 17 controllers. Consequently, the four existing 150-second replay cases are conditional model checks under a known signal-execution mismatch, not exact native-signal prediction validation.

This is a source and small JSON/XML review. The separately authorized `build_config` comparison constructs configurations only: no `configure_runtime`, projection, forecast, endpoint, MPC, COM or VISSIM call. No FZP was read and no production or existing input was changed. Companion JSON retains source hashes, all 17 selected native program attributes, raw SG commands and the actual action. These files are new diagnostics.

## Actual paths

| Path | Current behavior and source |
|---|---|
| Live no-control | `vissim_stackelberg_adapter.py:12540` selects `ControlAction.uncontrolled`, then line 12766 calls `build_one_step_prediction`. The latter, at 10189–10202, sends the control directly to the canonical endpoint with depth 1 and box walking disabled. |
| Meaning of uncontrolled | `vendor/NumSim-mine/src/models/state.py:1684` sets maximum VSL/meter rates, equal live-phase greens and zero offsets. It does not read SIG programs. |
| Plant execution | `vissim_stackelberg_adapter.py:11884` checks the separately supplied metadata variant and `apply_to_no_control`. With variant `no-control` and this flag false, urban CSV rows are omitted. The actual action900 CSV has 74 rows: 66 VSL and 8 meter rows, with zero urban rows. |
| Diagnostic replay | `probe_corrected_prediction_fidelity.py:24` calls `control_from_json`, then the same depth-1, no-box-walk endpoint. `control_from_json` at adapter 9670 preserves **all diagnostics**, including `no_control_active=1`, then calls `prepare_control`; it does not copy top-level metadata into the control. Neither endpoint path interprets `no_control_active` as native clock ownership. |
| Selected model clock | `signal_actuation_contract.py:325` derives fractions from candidate greens and written offset. `wrap_clock` at 358 consults this function before the old native/monitor callback. The actual config enables this contract for all 17 selected nodes. |
| Existing native validation switch | Adapter 1576 captures `RW_VALIDATION_FIXED_SIGNAL` during callback installation. However, adapter 1649 wraps that callback with the physical signal contract. For a selected signal with a phase, the outer contract returns a fraction first, so setting this environment variable alone does **not** select the native schedule. The old inner controlled-node branch also falls back if a native schedule is absent. |

The actual config is `diagnostics/contract_observer_off_configs_v3/n7_area_beta0.json`, SHA `201b7b6d5c759736201dd9a08b036dd3cd4891501a9d2de922b59651d3fd910d`. It has `urban.physical_signal_contract=true` and `actuation.real_world_signal_control.apply_to_no_control=false`. All four helper invocations have `RW_environment={}`. The actual no-control action retains its diagnostics. The actual network is SHA `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`.

Do not treat monitor nodes or explicitly native fixed service resources as having this same defect merely because the selected-node path does. Their ownership paths already differ. Conversely, repairing the general callback alone is insufficient evidence that every shared/local physical service consumer has changed consistently.

## Native programs cannot all be encoded by the current 17 green vectors and offsets

The model/writer layout is `major_maps_to`, followed by the other phases in fixed numeric order (`signal_group_plan.py:266`). For these selected examples the order is p2, p1, p3, p4. Each positive phase consumes its green span plus the fixed three-second clearance. The contract explicitly requires full, identical SG windows within a phase (`signal_actuation_contract.py:137`) because the existing local cache is phase based.

The following intervals are program-relative seconds read from the raw SIG GREEN/RED commands and their explicit three-second AMBER fixed states; they are not a new COM/LSA validation run.

| SC | Native evidence | Necessary incompatibility |
|---|---|---|
| SC1004 | 150-second cycle; program offset 75; p3 GREEN [0,45), p4 [48,72), p1 [75,121), p2 [124,147). SG pairs are p1=4/8, p2=3/7, p3=2/6, p4=1/5. | Native order p3→p4→p1→p2 is not a cyclic rotation of p2→p1→p3→p4. One offset cannot reorder phases. Correct durations alone still do not reproduce all eight SGs. |
| SC7 | 120-second cycle; program offset 1; p1 SG4/8 GREEN [0,67), p2 SG7 [0,90), p4 SG1 [93,117). | Different phases overlap for 67 seconds. A serialized nonoverlapping layout cannot reproduce this. Its actual equal-action cycle is 150 seconds. |
| SC16 | 150-second cycle; program offset 149; p3 [0,27), p2 [64,81), p1 [84,147). | There is an additional all-red [30,64) gap after AMBER [27,30). Native green spans plus the current three clearances total 116, not 150 seconds. Copying durations loses 34 seconds of native all-red. |

For SC1004, including its program offset gives absolute modulo-150 GREEN windows p3 [75,120), p4 [123,147), p1 [0,46), p2 [49,72). The actual equal action has continuous layout p2 [0,34.5), p1 [37.5,72), p3 [75,109.5), p4 [112.5,147). The model samples that latter clock on the one-second event grid; fractional endpoints must not be reported as identical continuous GREEN exposure.

Even copying the selected native axis durations at offset zero only happens to align SC1004 SG2/6 and SG1/5; it misplaces SG3/7 and SG4/8. Therefore a match on the previously audited SG2/SG5 pair cannot certify the controller. `native_fixed_control` already states at adapter 11540 that it serializes native-derived axes and **does not replay original overlap/gaps**.

All 17 active original controllers use program 1 and controller offset 0. Native SIG cycles are 150 seconds except SC7's 120 seconds; program offsets are retained separately in the JSON. Program offset is not automatically the writer offset: native `state_at` uses time minus program/controller offsets, whereas the writer-compatible clock uses time plus written offset, with an additional phase-layout origin. A sign change alone cannot fix the overlap/order/gap counterexamples.

## Flagship difference: effective configuration, not a guessed cause

`probe_model_area_integration.py:84` calls `build_config(..., flagship=True)`; live no-control at adapter 12312 uses false. The actual build was compared with the same 201b config, calibration, 900 snapshot, mode `fast-smoke`, 150-second interval, 5400-second period and `local_observation=True`. It took 0.236 seconds, and the pinned source/input hashes did not change.

Exactly eight effective fields differ:

| MPC field | Live NC | Helper |
|---|---:|---:|
| baseline_move_box | false | true |
| leader_bias_sample_pow | 1 | 0.4 |
| leader_rollout_box_walk | false | true |
| leader_rollout_box_walk_vg | false | true |
| np_bias_correction | false | true |
| np_primal_dual_iters | 0 | 4 |
| seg13_meter_box_veh_h | null | 300 |
| seg13_vsl_box_kmh | null | 20 |

Network, simulation and both follower configuration sections are identical at this build stage. The endpoint's meter/VSL walking reads are guarded by `ObjectiveSpec.box_walk` (`rollout_endpoint.py:193–215`), which is false in these comparisons. The remaining differing fields are search/correction settings, rather than evidence of a changed held physical trajectory. This review does not establish full runtime/live parity or prove these eight fields affected the four outputs. `no_control_build_config_comparison.json` preserves the effective diff and scope.

## Minimal true native-held comparison contract

1. Carry an explicit **native signal execution context** into the common prediction path, alongside the complete unchanged action: actual network/SIG hashes, active program, controller offset, absolute time origin and the selected physical SG/head-to-service resource mapping. The same source of ownership must explain why the writer omitted urban commands. Retain meter finalization, routes, observation flags, capacity fields, physical membership, initial state and demand; do not strip model fields to make a replay pass.
2. Reuse `compile_fixed_signal_schedules`, `ControllerProgram.state_at/green_overlap` and `FixedControllerSchedule.movement_green_fraction` for native interval exposure. An explicit native-owned branch must precede the candidate contract for this policy scope and fail if its required schedule or exact SG authority is unresolved. It must not silently use equal greens or an approach-wide SG union. Controlled policies retain the writer clock.
3. Verify each consuming path against the same native resource clock: regular urban service, pre-head/shared corridor budgets, local rollout caches and restored worker aliases. Native overlap requires SG/resource-specific exposure where the present phase-only cache cannot represent it. Preserve the verified unsignalized bypass and explicitly fixed native resource contracts. This is a small common clock/ownership integration, not a new adapter or a 17-value input-only workaround.
4. Before new fidelity predictions, compare native per-SG state/exposure with the actual LSA over the intended windows, including program offset, interval boundaries, AMBER, overlap and gaps. Then keep all non-signal inputs identical and recompute the four held cases. Do not disable `physical_signal_contract` globally or change candidate geometry merely to reach the legacy environment branch.

Until that is done, the existing four cases can expose numerical behavior and residual patterns under their recorded equal-green policy; they cannot isolate native physical capacity, native urban discharge or signal-independent model error. Agreement in one E8 snapshot does not remove the documented urban control mismatch, and disagreement is not evidence that signal mismatch alone caused the error. No counterfactual effect size is claimed here.
