# Follower game and price structure at dd13e08

The installed code scores the finalized physical command with the requested Ω objective, but it does not yet solve or certify a common four-lever equilibrium. Green, offset, VSL and meter have identifiable owners; their update order, local objectives and price reference points differ. A performance-only change must preserve these differences and the solver state that carries between calls. Resetting those states, moving an update into Jacobi, or parallelizing leader candidates would be an algorithm change.

This is a read-only audit of the parent-frozen dd13e08 sources and the completed actual-main t900 β300 decision in `area_production_preflight/wu-link_t900_beta300_20260910T032525335593Z`. The accompanying JSON pins 17 source files, the v4 config and the original action/CSV/manifest. Its producer imports no controller and executes no endpoint, local cost, MPC or VISSIM. It checks three recorded objective identities and source stability. No candidate permutation experiment or new convergence test was performed.

## Actual update order and strategy ownership

| Stage | Owner and action | What is held, changed or tested |
|---|---|---|
| Price refresh before leader search | PricedWuLinkStackelbergController; scalar green, phase-vector, offset, VSL and meter price channels | Prices are finite differences around previous control. Default `price_iter_max=1`; configured worker count is 10 for price jobs. This is one refresh before candidate search, not a price-and-strategy fixed point. |
| Candidate follower entry | LinkAgentWuFollower, inherited WuFaithfulFollower | Receives a copied physical state, candidate leader quantities, forecast and previous action. The follower object and its warm coupling/flow caches are reused. |
| Jacobi city update | 17 urban signal agents | The current config omits `phase_price.in_gne`, so the class default is False. The inner city oracle chooses primary green and redistributes the vector through the existing mapping. Full phase-price refinement is outside this iteration. |
| Jacobi freeway update | Two freeway link agents | `metering_in_gne=True`: each owns its link VSL vector and the two ramps selected by `ramp_to_freeway`. Meter trials call a nested VSL best response. Their proposals are committed with the city green proposals at the end of the sweep. |
| Optional candidate N_P dual iterations | The same follower | Source defaults give `np_candidate_lambda=True`; flagship supplies four PD iterations. A leader-present candidate can repeat Jacobi with candidate-local λ_P; PFO has `leader=None` and skips this quantity-price loop. |
| Offset pass after Jacobi | City signal owners | Non-ramp signals can jointly change primary green and offset. Ramp signals use the ramp offset oracle. No following freeway Jacobi response is made to these offset changes. |
| Phase-vector refinement | Same city owners, canonical finalization wrapper | With current config, pairwise phase exchanges use local cost plus weighted phase price, step 6s, up to 12 rounds. They run after Jacobi and offset work, before the first Ω on/off endpoint. No all-lever re-convergence follows. |
| Final physical action and score | Canonical phase/meter finalizers and area endpoint | Final phase vector is shared by offset-on/off/final score; meter rates/schedules are finalized. Exact late assertions require the written/returned action to agree with the scored action. |
| Leader/PFO comparison and commit | Leader full/proxy/PFO consumers | Ω endpoint objective ranks these policies; physical/severe feasibility guards remain. The selected candidate supplies the committed command and eligible standing-dual diagnostics. |

Source anchors: `priced_wu_link_controller.py:141,543,546,698`; `wu_faithful_follower.py:4092,4319,4372,4433,4534,4612,4686,4854`; canonical builder `vissim_stackelberg_adapter.py:7016`; finalization `area_follower_objective.py:27,116,151`.

Within Jacobi, the snapshot is copied and proposals are applied together; relaxed coupling uses α=0.5. The stopping test is relative change in the coupling vector with configured tolerance 0.05. It is not an all-lever best-response gap, objective improvement, or final-vector fixed point. `NashResult.residual_objective` is assigned `0.0` in the return constructor (`wu_faithful_follower.py:4897`); zero is not a measured objective residual.

The recorded chosen PFO reports `nash_converged=1`, one iteration and coupling residual 0.0199780323, then records 59 changed phase-green values from `phase_refinement`. `control_area_phase_outer_matches_scored=1` is valuable evidence of final score alignment. It does not turn the earlier convergence flag into a certificate for that final vector.

Simply enabling the dormant `phase_price.in_gne` flag is insufficient to establish the requested joint game. Offset remains after Jacobi, and the optional vector city oracle returns the original scalar oracle's cost/evaluation/net-inflow tuple after changing the green-vector override (`priced_wu_link_controller.py:684`). That branch needs its own returned-quantity and coupling audit before use. Physical ownership of active-but-headless phase dimensions is being audited separately by Hubble; this report does not certify every SG's direct service authority.

## Ω objective and the external-price subtraction

Let `JΩ(u)=TTTΩ(u)−(β_seconds/3600)TDΩ(u)`, in veh·h, and `L_i` be agent i's local cost. Current global price methods return `evaluate_price_point(...).objective`, which the installed area endpoint replaces by JΩ. Names such as `_global_rollout_ttt_with_metering` retain historical TTT wording but are not proof that β is absent.

For a coordinate or feasible exchange direction, the intended external price is

```
p_i = D_i JΩ − D_i L_i
local surrogate = L_i(u_i) + w_i p_i · (u_i − u_i_ref)
derivative at a matched reference = (1−w_i) D_i L_i + w_i D_i JΩ
```

Therefore adding the local cost after subtracting its matching derivative is not, by itself, a second β reward or a duplicated local TTT term. With weight 1 and matching models/reference/actions, it matches the global first-order gradient. It remains a finite-difference linearization, not equality of finite-action objectives. The area ledger counts the TD reward once. If a future local model explicitly adds its own TD reward, its matching local derivative must be subtracted; adding TD independently would require a new derivation.

The current conditions fall short of exact cancellation:

* **Phase weight is 0.25.** The intended matched first-order expression is 0.75·D L_i + 0.25·D JΩ, not pure D JΩ. This is a configured blend, with no claim here that either weight improves performance. If the actual perturbation is exactly one phase +δ and every other live phase −δ/(n_live−1), the `(n_live−1)/n_live` multiplier converts its directional derivative to a zero-mean gradient. That is a coordinate conversion, not an extra traffic reward (`adapter:2279–2288`). At bounds this condition can fail: vendor `_phase_direction` box-projects the vector (`priced_wu_link_controller.py:881–891`), and the physical signal contract can project it again. The producer still divides by nominal δ, so exact coordinate conversion is not established for clipped/quantized perturbations. Hubble's independent read identified this qualification; no new directional probe was run.
* **Meter price derivatives use different action paths.** Global meter probes alter only meter at previous VSL (`stackelberg_wu_metered.py:646`). `local_metering_costs` calls `_solve_freeway_agent_local` without a fixed VSL override, after removing meter/VSL prices, so it subtracts a local VSL-best-response envelope rather than the partial derivative of the same held-VSL global probe (`wu_faithful_follower.py:1051–1100`). In the later meter game, the nested VSL oracle can again include the VSL price. This is a structural mismatch; no numeric error size has been measured here.
* **Local and global prediction scopes differ.** Local queries use the first DemandStep and frozen coupling/receiving estimates; global endpoint probes use their declared forecast and full network. Local costs can include smoothing and blocked upstream queue proxies. Canonical final J excludes legacy leader penalties, but that does not remove every surrogate inside local best responses. The local model's returned cost is the quantity that must be matched in any cancellation proof.
* **Physical meter finalization occurs later.** The global endpoint finalizes requested rates through measured mapping/spill context, but native local best-response candidates are not passed through that finalizer while being searched. Consequently a finite requested-rate probe can have a different physical step than the local probe. Final writer alignment is repaired; a common realizable strategy domain is not thereby proven.
* **Prices need not remain a local linearization of the final action.** The selected action can move during Jacobi, the offset pass and phase refinement while price surfaces remain tied to the previous-control refresh. Repeated price/strategy reconciliation is not enabled by the current `price_iter_max=1`.

Scalar green, meter, offset and VSL subtraction sites are `stackelberg_wu_metered.py:1338,1440,1555,1710`; the configured phased-price producer is the canonical adapter override at `:2217–2330`, not the old drain-only vendor implementation. Shared local service installation corrects its physical ready/service context, not the mathematical objective or game schedule.

Scalar-green and phase-vector price channels also address overlapping green directions at different stages. The primary-green oracle and joint primary-green/offset pass use their scalar price; the later vector refinement uses `local + phase_weight * phase_external_term`. Current code does not simply add both green-price tables to one final Ω ranking value. The problem is successive strategy updates under different local surrogates, rather than evidence of two explicit β subtractions in the endpoint.

## Leader quantities, PFO and state that is not frozen

For leader-present equality-mode meter allocation, each freeway owner receives budget `ω_F[link]·N_UF_star`, clipped to its physical rate capacities, and searches an allocation simplex. The class default link share mode is **density**, so `_omega_f` is computed from the decision state before price/search; the builder does not force uniform shares. The conditional post-selection link-share search mode is inactive. λ_UF's optional dual mode is distinct from this equality path.

The PFO incumbent is an alternative policy, not the same game at a different numerical target. It uses `leader=None`, zero quantity fields on a copied previous action, and no candidate N_P dual loop. With current split-meter pricing and equality mode, `_price_metering_cost` explicitly returns zero for this PFO path; autonomous meter coordinate descent still nests VSL best responses and other enabled signal/VSL/offset price channels remain. The resulting action is converted to equivalent clipped leader quantities and reevaluated with the canonical Ω endpoint. Ω ranking makes the policy comparison explicit but does not make their local strategic objectives identical (`stackelberg_wu_metered.py:2155–2217`; `wu_faithful_follower.py:3364–3413`).

Candidate λ_P/λ_UF next-values are mostly diagnostics until selection/commit (`stackelberg_wu_metered.py:2435–2497`). This is narrower than “all follower state is fixed.” A mode-dependent solve-start corrector can write standing λ_P once per observed time when candidate λ is enabled without PD. Current leader candidates use PD; the recorded PFO skips it. Candidate-local λ updates are part of the algorithm, not a performance cache.

The following state must be retained in any performance-preservation trace:

| Owner | Fields and relevant lifecycle |
|---|---|
| `controller.nash_solver` (LinkAgentWuFollower/WuFaithfulFollower) | `_prev_coupling` read at solve entry, written by every completed follower solve. State.copy does not clone this object. |
| `controller.nash_solver._wu` (WuDistributedController) | `_last_offramp_flow`, `_has_last_offramp_flow`, `_omega_f`. Canonical local FW cost writes the selected query's flow into the cache; subsequent coupling/frozen-off-inflow reads consume it. |
| Follower dual/corrector state | `_lambda_P`, `_lambda_UF`, `_np_last_sum_nin`, `_np_corrector_pending`, `_np_step_time`, `_np_prev_accum`, `_np_last_real_q`, `_np_bias_ratio`; mode-dependent entry/commit semantics above. |
| Follower temporary context | `_seg_traj` is reset per solve; `_gne_phase_override`, `_phase_resolved_active_signals`, `_phase_ctx_cache` and area finalization contexts have distinct lifetimes. Shared ON phase context is rebuilt; that does not freeze all other caches. |
| Follower price surfaces | All scalar/phase price dictionaries, matching reference/weight/trust values and cross-price surfaces. Local derivative helpers temporarily remove selected price channels and restore them. |
| Outer controller | `previous_control`, `_pfo_incumbent_center`, `_pfo_incumbent_eval`, `_signal_price_last_step`; candidate dedupe cache and link-share context only in their enabled modes. `_signal_price_meta` read sites found report/copy values rather than numeric strategy decisions. |

The concrete active side effect is `link_predictor.py:500–508`: every local FW query writes `_wu._last_offramp_flow`. `local_metering_costs` restores only the temporary price fields, not this cache. `_wu._coupling` (`wu_distributed.py:250`) and `_frozen_off_inflow` (`wu_faithful_follower.py:542`) read it later. Reusing the follower for full and PFO candidate solves also carries `_prev_coupling` (`:4131,4686`). These dependencies are sufficient to reject a claim that candidates are presently independent merely because physical state is copied. Their quantitative order effect has not been tested. Resetting or snapshotting them would change the baseline algorithm and is outside the current clock-cache performance patch.

## What was already fixed, with recorded checks

| Existing repair | Current evidence |
|---|---|
| Final green refinement formerly occurred after its score | `area_follower_objective` finalizes before first on/off/final endpoint; token/equality assertions prevent a late vector change. Actual900 has 59 changed values and final equality flag 1. |
| Global-TTT offset veto and ambiguous follower score | Offset guard uses JΩ and zero relative margin; separate global TTT, ΩTTT, TD and J fields remain. Negative J is handled additively. |
| Late meter quantization/spill guard changed scored action | Canonical finalizer is shared by candidate endpoint and writer, uses decision context, and asserts no late change. It does not establish local-search physical-grid equivalence. |
| Legacy density/target/queue/terminal add-ons and proxy β omission | `area_leader_objective` normalizes supported Wu full/proxy/PFO ranking to endpoint JΩ; six old components remain excluded diagnostics. Unknown extra costs and unsupported base scalar consumers fail closed. Terminal wrappers call the same final normalization. |

The completed t900 action supplies these directly recomputed identities:

| Evaluation | ΩTTT (veh·h) | TD (veh) | J at β=300s (veh·h) |
|---|---:|---:|---:|
| Final follower / offset on | 310.17403469406946 | 1505.229854541694 | 184.73821348226164 |
| Offset off | 311.2093370226962 | 1503.658345687859 | 185.9044748820413 |

`additional_cost_veh_h=0`. The selected leader/PFO value is 184.50790879831837, compared with 185.6660211863658 for the guarded leader alternative. The follower endpoint holds its command (`box_walk=False`); leader evaluation can use its existing future box-walk policy. Their unequal J values are therefore not, by themselves, evidence of another stale final score. The chosen PFO records zero candidate-PD iterations and zero standing λ commits.

## Next algorithm gate, after performance work

This audit proposes no production change. A later common-game design must specify (1) each physical action owner's full realizable vector, (2) the same candidate/forecast/ready-state context for local and global derivatives, (3) which portion of ΩTTT/TD each local cost represents and how its derivative is subtracted, (4) quantity constraints/dual rules shared or deliberately different for leader and PFO, and (5) a termination check after the final joint vector. Changing the phase flag alone, resetting solver caches, or dropping local costs without rederiving the prices does not satisfy these conditions.

For the current performance-only work, preserve candidate order, all operational state transitions, local price-removal scopes, exact action/cost outputs, and parent/worker ownership. The immutable signal-clock cache is separate and remains unapplied at this review. Its microbenchmark and exact-function regressions do not certify a modified game.
