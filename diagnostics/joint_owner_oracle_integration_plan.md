# Joint-owner core v2 → actual 19-owner oracle

This is a read-only integration proposal, not an applied patch or model result. The source snapshot is pinned in `joint_owner_oracle_integration_plan.json`. No production, driver, configuration or Git changes, controller imports, tests, endpoint/MPC, COM or VISSIM operations were performed for this note.

The finite loop can be connected with ordinary functions in the existing canonical modules. The missing part is the evaluation contract: current local functions neither consume nor return the candidate-dependent shared trajectory needed to certify the requested physical game. A thin call to the existing scalar best responses would conceal this gap. The earlier 14 synthetic tests certify the loop's mechanics only.

## 1. Entry and return: bypass later strategy searches in the ON branch

The current path is outer price refresh → leader or PFO follower call → `LinkAgentWuFollower.solve` → inherited `WuFaithfulFollower.solve` → `_solve_followers` → offset work → canonical phase finalization/endpoint → outer Link phase handling. References:

| Existing location | Minimal future change |
|---|---|
| `vissim_stackelberg_adapter.build_priced_wu_link_controller`, final installs at 7212–7218 | Validate an explicit joint-game mode, its 19-owner catalog and required oracle/domain settings only after physical signals, area follower objective and shared-ready refinement are installed. Keep the existing builder; add no alternate adapter. |
| `area_follower_objective._install_link_phase_finalization`, nested `solve` at 167 | Put the explicit joint ON branch before invoking the saved original Link solve. Dispatch to an ordinary `solve_joint` function in this same existing module. The OFF branch remains the original call and original exceptions. This reuses the existing entry hook instead of stacking another solve wrapper or copying vendor code. |
| `joint_owner_game.solve` v2 | Supply the catalog, full realized incumbent, frozen round context and four required callbacks. Use catalog order, complete domains and explicit caller limits. Do not call `_solve_followers`, a local best-response search, or `_maybe_refresh_signal_prices` from inside a callback. |
| `area_follower_objective._finalize_link_phases` at 116 | For the joint ON branch, validate and mark the already-finalized joint vector; do not run `apply_phase_price_refinement` or apply `_gne_phase_override`. Preserve the existing phase equality assertions and use a distinct `joint_owner_game` source marker. |
| `area_follower_objective` final Ω score at 27–58 | Reuse the installed canonical endpoint for the final complete action, with `box_walk=False`; preserve real Ω/global TTT labels. Before and after scoring, require identical full command/lever fingerprints. No offset-on/off selector or phase refinement may replace the certified result afterward. |
| Existing NashResult boundary, vendor `WuFaithfulFollower.solve` at 4854–4900 | Construct the same result type in the canonical ON function. Set `converged` only from the finite certificate. Preserve per-owner nullable gaps and failures in diagnostics; do not assign the old hardcoded zero objective residual. A finite-gap scalar has payoff units, not the old relative coupling-residual units. Any legacy consumer that assumes those old units must be adapted or explicitly reject the new mode. |

Returning a joint solution through unchanged `_solve_followers` is insufficient: that routine also executes quantity updates, offsets, caches and its existing guard. Returning through unchanged Link solve can apply vector overrides/refinement after the result. Those mutations would invalidate the final same-context gap. The proposed early ON branch avoids both searches; it does not merely set `phase_price_in_gne=True`.

The full result still undergoes the outer leader's existing evaluation/feasibility and PFO policy comparison. Leader future box-walk evaluates a different future-response policy; retain that distinction. A leader-selected command from a different policy cannot inherit the joint game's certificate. Any later physical guard that changes the joint action requires re-evaluation/re-certification or an explicit uncertified result.

## 2. One fixed round: inputs, duals and payoff components

Create the round value snapshot once at follower entry, after the outer price-production stage. It contains state and all transit/route/native-input cohorts, forecast, cfg/source/plan/table identities, committed previous control, leader presence/quantities, price surfaces and references, effective weights/trust, allocator policy, and current operational follower state. The mutable current joint incumbent is a separate argument, not the smoothness reference.

Hold `_lambda_P`, `_lambda_UF`, `_wu._omega_p`, `_wu._omega_f`, leader quantities and price references fixed for every owner, sweep and final check in that round. If the retained candidate-PD policy needs several dual rounds, update the dual only between complete joint solves, then re-run all owners and the final audit under the new context. Do not reuse an earlier certificate after a price/dual/quantity change. Choose the existing producer's quantity mode explicitly; do not manufacture a hard N_P equality from a tracking policy or silently zero its multiplier.

For each owner return a separately recorded breakdown:

```
cost_veh_h = local_base_veh_h + external_price_veh_h + quantity_term_veh_h
```

`JΩ = TTTΩ − (beta_seconds / 3600) TDΩ` remains the physical endpoint/outer ranking value. Do not use it as every owner's local payoff, add it to local cost, or subtract β again. Keep each cfg's β. The current v4 input specifies phase weight 0.25, exchange step 6 s and phased local cost; the builder enables green/meter/VSL/offset prices and disables both cross channels. Other weights and mode-dependent activation must be copied from the effective instance, not guessed from class defaults.

| Component | Existing source and required preservation |
|---|---|
| Urban local base | `P._phase_local_cost_phased:330` for non-ramp signals; installed ramp setup/cost below. These do not add the scalar-green price/NP quantity terms. Preserve the selected local cost definition and explicitly retain any applicable regularizer/protected-queue/congestion term. Full-vector refinement currently has a different base from the earlier scalar oracle; joining the two is an algorithm choice, not OFF-equivalence. |
| Urban external | One full-vector green channel plus one offset channel using the actual signed circular displacement. Do not also add scalar-green price. Where the old two-live-phase signal has only scalar price, map its one actual vector direction with the existing weight; absent/rank-deficient direction prices are unresolved, not silently zero. |
| Urban quantity | `W._agent_net_inflow_veh:632` currently reconstructs all greens from p1, uses cycle-average capacity/forecast counts, and ignores offset. Extract its vector-input arithmetic once and use that same definition in the quantity producer and game. Do not pass a selected full vector back through p1. This legacy protected net-flow quantity is not Ω entry or TD and is not made physically accepted flow merely by renaming it. A later accepted-flow quantity is a separate coordinated leader/follower definition change. |
| FW local base | The unapplied `fixed_freeway_query_preparation_v2` extraction separates applied candidate from reference, evaluates one held expanded VSL vector and both owned meters, and rejects nonfinite/count≠1/vector mismatch. Use `include_price_terms=False`; keep the independent price-dependent smoothness policy fixed. It still contains the selected local landing/blocked-queue/optional terminal/protected-queue costs. |
| FW external | Add configured VSL and meter terms once outside the base. Use zone-authority price coordinates, not a duplicated price per alias. Any existing sum over expanded keys needs its installed effective-price mapping verified. Cross channels currently remain OFF. |
| FW quantity | `W._solve_freeway_agent_metered:3344–3417` separates equality/split, priced soft anchor and standing-dual cases. In equality mode constrain the finalized two-meter equivalent-rate sum to the existing `B_link(N_UF*)`, including its current cap treatment and frozen omega. In dual mode add the existing λ_UF rate term once; do not add a soft anchor as well. Units are veh/h, not actual demand-limited released vehicles. |
| PFO | Preserve explicit `leader=None` semantics. Current split-price PFO can suppress the meter price when standing dual is inactive. It is a distinct policy/game; do not quietly impose leader equality or label two different payoff contexts one equilibrium. |

The new fixed local function must also be the function subtracted by the global price FD. Existing `local_metering_costs` internally reoptimizes VSL and old `local_offset_costs` reconstructs scalar greens/returns zero for ramp signals; neither is the new fixed-candidate subtraction oracle. Existing adapter `install_phased_price_local` and the installed price-refresh method are the direct modification points. Use the same realized base/probe and actual displacement for `D JΩ − D L_i`, preserve weights and signed offset lifts, and record the unresolved green-direction rank/secant residual. Do not refresh prices for each BR candidate and call that a fixed-price round.

## 3. Existing fixed local primitives and the missing shared interface

| Actual function | Usable portion | Necessary change/limitation |
|---|---|---|
| `P._phase_refine_context:238` | Normalizes the current demand and constructs coupling, snapshot, start index and horizon. | It writes `_phase_ctx_cache`, then setup writes `ctx['setups']`. Build scoped query state and restore it. Candidate-dependent shared inputs must not come from a stale incumbent context. |
| `P._phase_refine_signal_setup:293` → `_phase_local_cost_phased:330` | Existing movement model, initial queues, platoon arrival profiles, physical GREEN and `rollout_local_tts_phased`. | Cost reads offset from `ctx['snapshot']`. Pass a private context with the full trial snapshot. The local plant has `s_eff_by_substep`, but a receiver-space scalar alone does not reproduce joint competition with other signals. Its float return exposes no accepted-movement witness. |
| `local_signal_service.ramp_refinement_setup:532` / `ramp_refinement_cost:564` | Existing shared head budgets, ready seed, true GREEN fractions, finite OR storage and accepted-only release. | `off_inflow` and `reservoir_drain` are frozen scalars; setup reads `_wu` flow cache. Full candidate-dependent off arrivals, ramp transfers, shared-stage space and ready histories cannot currently be supplied. Extend these existing functions with explicit trajectory inputs/results; do not create another ramp plant. |
| `link_predictor.solve_freeway_agent_local:250` | Local METANET + existing `LocalLandingState` and its cost expression. | Current function enumerates VSL and writes `_wu._last_offramp_flow` and `_last_local_landing_diagnostics`. Use the narrow fixed-query extraction, not this solver. Its frozen urban approach/drain/other-link receiving assumptions still need the shared trajectory contract. |

Only initial stock, immutable topology and truly candidate-independent input portions can be reused across neighbors. Hubble's private `trial_ctx['snapshot']` fix is enough to avoid stale offset for a frozen-interface local query; it is not proof of candidate-dependent shared-flow agreement.

Two possible output scopes must stay distinct:

* **Frozen-interface surrogate query:** the current local primitives can evaluate a declared approximate payoff once the fixed vector/reference and globals are isolated. A coupled trajectory can separately check physical feasibility, but that does not prove the local cost consumed the same accepted flows. Do not return `witness_complete=True` for the stronger shared-interface claim.
* **Requested shared physical game:** expose `Gamma_i(A_z(u))`, feed/reproduce those transfer-time inputs in the existing local kernels and record local/coupled accepted-flow agreement. If an optional trajectory API cannot represent a shared stage, return incomplete. Alternatively, deriving each local cost from the canonical joint trajectory would require an explicit per-owner cost projection, including existing blocked/landing/protected terms; it is a payoff-definition change that must also change the matched price subtraction. It is not an automatic shortcut to `JΩ`.

## 4. Shared allocation: reuse the installed Ω body once per candidate

The actual ON allocation path is:

```
area_runtime.evaluate_price_point(state_copy, finalized_action, forecast, (),
    ObjectiveSpec(cfg=cfg, box_walk=False, depth_override=declared_horizon,
                  score_mode='raw', split_ttt=True))
  → endpoint._rollout
  → installed area_freeway_accounting._run_coupled_interval_events
  → installed urban_flow_accounting.legsplit_substep_accounted
  → urban_substep_accounted / ready and head/corridor primitives
```

Use this body as `A_z(u)`; do not copy `run_coupled_interval`, add a parallel shared allocator, or reserve other owners' previous accepted discharge. Its order is release-request from the opening ramp reservoir → all Tu urban service steps → actual ramp release → FW step → accepted off-ramp landing for subsequent readiness. Inside the urban step, on-ramp service precedes off-ramp drainage, which precedes ordinary movement receiving allocation. Preserve current route/native/fixed-signal traffic as participants even when they have no strategic owner.

Resource hooks already exist: `route_choice_corridor.limit_intended_batch`, `head_service_resources.regular_context/regular_batch/regular_accepted`, `local_signal_service.register_limit/limit_batch/accepted`, `_effective_available_space` and `_allocate_receiving_counts`. SC1004 10634 and 10629 stay distinct resources; the aliases consume one accepted budget. Do not multiply a shared aggregate capacity by its number of views or lanes.

The smallest required observation extension is an optional query-owned witness sink in these existing canonical functions, inactive otherwise. Record values where they already exist, without allocating twice:

| Exact stage | Needed record, in vehicles unless stated otherwise |
|---|---|
| `urban_substep_accounted` head context and each existing intended/batch/accepted point (notably 423 and 429–479) | Absolute Tu index and stage ordinal; resource/receiver; ready stock; physical GREEN; capacity×dt; full contributing movement requests and accepted counts; receiving space before/after. Include corridor/prehead/shared69 service paths and non-strategic contributors, not just ordinary movements. |
| `area_freeway_accounting._run_coupled_interval_events:323–375` | Request and actual meter release by ramp, local urban interval boundaries, off-ramp acceptance and due-time, before/after native/corridor transit inventories. Keep the same initial-reservoir and FW-block timing. |
| Existing `control_area_objective.emit_transfer` / residence sites | Unique ordered transfer keys and owner-relevant inventories at the actual quadrature point. Current `flow_counts` is an aggregate counter; macro snapshots/aggregate totals cannot reconstruct all Tu ready/space checks. |
| Local phased/shared-ramp/fixed-FW loops | Same time/transfer keys, accepted flow and queue/landing residence used to calculate L_i; compare to the candidate-dependent shared interface. Expose additive cost components rather than a single unexplained scalar. |

No snapshot tapping alone proves a local model matches the joint trajectory. Missing keys, unresolved attribution or inconsistent interface produce an incomplete witness. Excess demand becoming a queue is normal; it must not be rejected merely because offered flow exceeds accepted flow. Physical hard constraints, quantity residuals and local-interface residuals have separate names and units. Infeasible finalized equality domains retain their original target and show reachable sums/distances, without target rounding or tolerance inflation.

A full held endpoint per unique candidate is a correctness reference, not a speed claim. Do not reduce the declared joint neighborhood to meet a deadline while retaining a complete certificate. After purity and dependency closure are demonstrated, exact full-value action/context reuse is possible; mutable cfg/controller ID caches and cross-round old-flow reuse are not proposed here.

## 5. Physical fingerprint and exact replay of a candidate

Use `joint_owner_addresses` to partition the complete 213-row writer output: 17 signal axes, 122 urban SG rows, 66 DSD rows and 8 meter rows in the present mapping. Recompute the rows for every supplied action; do not trust a candidate's stored hash.

The smallest common writer change is extracting the existing `write_action_csv:11841` row construction into a pure iterator in that same adapter file, then letting the current CSV writer consume it. Reuse its exact nearest-VSL, `_segment_dsd_controls`, `signal_group_action_rows`, written-offset and measured-meter schedule logic. No new CSV dispatcher, fallback mapping or approximate rate-to-green converter is needed. Tests must prove unchanged existing CSV bytes before using the iterator as authority.

The urban and FW neighbor proposals already expose compatible keys/full rows. VSL's `owner_physical_fingerprints(ownership, rows)` now partitions those rows into owner SHA strings and rejects silently changed incumbent realization. Bind core `physical_fingerprint(action, context)` to the canonical iterator plus this catalog partition. The context token separately pins source/plan/mapping/calibration/native clocks and horizon. Preserve schema/column presence and all semantic fields; discard only proven output metadata. Include eight actual meter schedules and 42 expanded VSL cells/link aliases, not just four rates or six free heads.

Realize each copied request once before evaluation with the existing signal projection/written offset, zone expansion and `area_meter_finalization.finalize`. Check foreign/fixed values and rows. The current finalizer may change rates after a guard/quantization; if that crosses owner bounds or violates the fixed quantity, reject the realized candidate with evidence. The finalizer's decision-context identity and `assert_writer(require_scored=True)` remain in force. Its grouped equivalent rates are still a model approximation to the native schedules, not proof that microscopic pulses are simulated inside the endpoint.

The core separately re-evaluates incumbent and neighbors in the final pass. Complete physical and lever fingerprints must match after every callback, final Ω score and writer assertion. New refinement/guard/price/dual changes after that point invalidate the finite certificate.

## 6. Operational/global isolation and workers

Use narrow `try/finally` scopes around existing calls and explicit value snapshots; do not reset legacy caches globally or parallelize owner visits. The actual callback may operate on a private follower operational snapshot, but the original instance must be restored on success, exception and deadline overrun. Committing standing dual/coupling state remains one explicit outer-selected-policy operation, separate from candidate evaluation.

| Scope | Exact current hazards and treatment |
|---|---|
| Follower | `_prev_coupling`; `_lambda_P/_lambda_UF`; `_np_last_sum_nin`, `_np_corrector_pending`, `_np_step_time`, `_np_prev_accum`, `_np_last_real_q`, `_np_bias_ratio`; `_seg_traj`; phase override/resolved-active sets; `_phase_ctx_cache`; local landing diagnostics; all price/reference/trust/weight dictionaries. Snapshot consumed fields; query caches must be local, not reused from another candidate. |
| Follower `_wu` | `_last_offramp_flow`, `_has_last_offramp_flow`, `_omega_f`, `_omega_p`. The existing FW solver commits selected first-step flow here, and later urban coupling reads it. Fixed queries return those flows as data instead. |
| Adapter METANET globals | `_FW_SEG_CTX` and `_FW_SEG_CTX_STATE`. Snapshot and restore both, preserving dictionary identity for existing closures. More than restore is needed: local `_local_lane_profile` currently returns candidate lanes without setting the global profile, while patched `segment_vsl` reads `_FW_SEG_CTX_STATE['profile']`. A fixed local FW substep must bind its own current effective lanes for that link before speed updates, then restore. Reusing a previous global endpoint's last profile, or setting only the initial profile for the whole horizon, is insufficient. Extend the existing local lane/step hook for this scoped ON query; do not change the OFF path. |
| Shared service | `_READY_CONTEXT` / `_READY_METRICS` are ContextVars; set/reset their tokens in `finally`, carry candidate-owned ready seeds, and do not share mutable setup maps. Refinement already carries explicit seeds; keep that path. |
| Endpoint | State.copy plus fresh Ω score ledger preserves physical cohorts. `_ACTIVE` uses its existing `finally`. Call counters/diagnostic summaries are output-only and distinct from strategy inputs; do not put an intentionally accumulating counter into a frozen-input token. |
| Installation | Build the callable chain once after the final builder restores shared setup/cost. `runtime_setup.install_worker_runtime:202` and existing controller pickle/bootstrap must restore the same named functions/flags. Persist serializable cfg/data, not callback closures or transient state. Use ordinary module-level functions bound in the worker after installation. |

The lane-profile observation above is a source-derived hazard, not a new measured numeric failure: this task ran no model. An A→B→A fixed-query comparison plus exception injection and a spawned worker are required before the purity contract can be claimed. Source/plan/global fingerprints alone detect changes; they do not automatically construct the correct candidate lane profile or restore a leaked global.

## 7. Small implementation sequence and stop conditions

1. Review/install the separate address, neighbor and fixed-FW-query proposals without changing the current runtime dispatch. Introduce one canonical writer-row iterator and prove existing outputs unchanged. Complete strict full-action/quantity/domain checks, including no incumbent projection.
2. Add one fixed-vector urban query in `local_signal_service` using the existing phased/ramp kernels and private explicit offset snapshot; add structured cost/flow results there and in the fixed-FW extraction. Route new-mode price subtraction through exactly those functions. Implement local lane-profile scoping at the existing geometry hook.
3. Add the optional witness sink at the existing coupled/service transfer sites and wire candidate-dependent trajectory consumption/consistency checks. Keep incomplete witnesses explicit. Do not fill core `Evaluation(witness_complete=True)` from an aggregate ledger alone.
4. Add the single early ON branch in `area_follower_objective`, supply its callbacks to the core, and adapt final result/phase-marker reporting. All 19 owners, caller-defined full joint domains and final same-context rechecks are mandatory for the stated scope. Skip all later legacy strategy refinement in that branch.
5. Verify source-pinned actual state/action data through fixed queries, foreign-owner stability, realizer idempotence, local/global flow keys, price breakdown, quantity modes, A→B→A/error restoration, final writer equality, and worker bootstrap. OFF must call the original chain exactly. Only then run a bounded actual 19-owner solve, with incomplete budget/domain results preserved honestly.

No concrete work budget, new candidate step, beta/price weight, global capacity, route prior or soft quantity penalty is selected here. The unresolved shared trajectory, quantity definition and lane-context pieces are implementation blockers for a **certified physical** oracle; the loop alone does not close them.
