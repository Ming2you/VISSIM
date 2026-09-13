# Joint-owner shared feasibility and fixed-price certificate

This is a proposed contract for the next algorithm change, not an implemented GNE or an extension of the clock-cache equivalence claim. It supplements `joint_owner_neighbor_interface_draft.md`. Only this new MD was written; no controller import, model, test, COM or VISSIM execution was performed. The original/cached clock can be exchanged during the parent's performance pair, so no transient clock hash is used here.

The minimal choice is **one shared, time-resolved physical allocation, with local objectives and fixed marginal prices**. A unilateral candidate fixes non-owner **controls**, not their previous accepted flows. The joint allocator recalculates every affected accepted flow and queue under that candidate. Each local cost must use its allocation consistently. Combining independently evaluated proposals requires reevaluation of the combined control. This revision corrects the earlier residual-reservation prescription: guaranteeing other actors' old discharge would add a new constraint to the intended control-only game.

## 1. Variables and the frozen game

Keep 19 owners: 17 urban owners each choose their complete green vector plus offset; two FW owners each choose their free VSL zone heads plus two model meters. Physical eight-meter schedules, SG windows and expanded VSL cell keys remain derived writes. A realized action is `u=R_z(request)`, using the existing physical finalizers and decision-time context `z`. Deduplicate on complete physical writes, not requested values. Each unilateral candidate must keep every non-owner write unchanged.

Freeze a solve context `z` containing initial physical/model state, forecast and its declared local scope, initial ready/pending stocks, source/calibration/config identities, meter realization context, leader mode/targets, price/reference/weight/trust/cross terms and duals. Within round `r`, freeze `c^r`: the agreed exogenous/local approximation inputs, initial coupling seed, allocation rule and every operational cache read by a query. A query clones this context; it does not change standing off-ramp caches or another query's setup. Candidate-dependent accepted flow, end queue and physical receiving space are outputs and must be recomputed. They are not frozen by the phrase 'fixed round coupling'. If a surrogate freezes a receiving curve or other actor's flow, label that approximation separately. Changing the round reference is explicit; changing prices or duals starts a new priced subgame.

Time indices `(k,s)` identify the canonical substep **and its ordered mutation stage**. They must use the actual FW/urban clocks and ready-delay convention. They are not automatically integer 1-second microscopic frames. A scalar 150-second total cannot certify a head/receiver constraint at every substep.

## 2. One resource is counted once

Let `f[m,k,s]` be accepted vehicles on one uniquely identified physical/model transfer, and let `owner(m)` identify which local plan supplies that transfer. Multiple views of one movement are aliases, not additional transfers. Routing-cohort reservations and arrival buffers are subsets/reservations of stock, not additional vehicles. Uncontrolled/native service and generation also participate in the resource balance, although they are not extra strategic owners.

For a evidenced physical head or shared lane service group `h`, define

```
G[h,k] = integral over the canonical substep of GREEN_h(t; realized u) dt       [seconds]
B[h,k] = service_rate[h] * G[h,k] / 3600                                     [vehicles]
sum over all stages and movements using h of f[m,k,s] <= B[h,k] + eps_flow
```

`B` is registered once and consumed across all relevant paths. A rate already aggregated over lanes must not be multiplied by lane count again. Aliased movement capacities are not summed into a larger pool. Actual lane/head membership or an explicitly validated aggregate resource is required; equal phase labels alone do not prove a shared lane budget, and different signal owners do not justify independent receiving capacity. Missing membership is an unresolved certificate boundary, not an invented equal allocation. Current SC1004/10634 and the installed head-resource groups provide concrete canonical groups; this design does not claim that every physical shared lane has already been modeled.

For receiving storage `l`, at the actual stage immediately before its incoming allocation,

```
sum of f[m,k,s] entering l <= S_eff(l, x[k,s-before]) + eps_flow
```

Use canonical effective space, including the model's stopline/point-queue occupancy and existing reservations. The stage's actual completed withdrawals may create space. Planned downstream departure later in the same step does not create space early. Transfers entering the same receiver through generic urban service, off-ramp drainage, native/shared corridors and ramp wrappers consume this **same** space in the declared order. A candidate cannot count one future receiving slot independently at each entrance.

Also require each source debit to be no greater than its available ready stock at that stage. Pending transit is unavailable until its ready step. One canonical stock incidence ledger must reproduce

```
stock_after = stock_before + admitted_generation + accepted_in - accepted_out
```

with nonnegative stocks and the existing storage-admission rules. Preserve initial over-capacity handling where the model explicitly supports it; do not erase observed excess or introduce a new global clipping rule to enforce an assumed `stock <= capacity`. Capacity constrains new admissions according to the canonical model. Ω boundary entries, inside generation and exits remain separate event quantities and are not inferred from resource reservations.

### Recompute allocation under each joint control

Define `A_z(u)=(f(u),x(u))` as the deterministic accepted-flow/state trajectory produced by the canonical coupled physical transition, its existing allocation rule and exact stage order, starting from the same `z`. This is a physical oracle, not a minimization of JΩ. At a shared node, gather all candidate-dependent offers and current ready stock; allocate the single service/receiving budget once, then update every affected source queue and target stock. The upstream actors cannot each spend the whole budget in a private accepted-flow model. The non-owner actions remain fixed; their accepted flows may change because the candidate changes supply, GREEN exposure or downstream congestion.

For example, two streams each offer 4 vehicles to an 8-vehicle head budget. If the controlling actor reduces that budget to 6, an equal-priority allocator may accept 3 from each and retain the two remaining vehicles in their source queues. That candidate is not rejected merely because another actor previously discharged 4. Whether the candidate violates an explicitly declared leader quantity or severe safety constraint is a separate check. Likewise, independently predicted flows of 6 and 6 into 10 available slots require allocation/re-scoring of the combined command; they do not imply that the command itself is physically impossible. These are arithmetic examples, not recorded traffic.

Controls alone are strategic variables. With `C_z` the physical inequalities, ready/stock constraints and declared severe/quantity conditions, define

```
F_z = {u in the realized action domain : A_z(u) is valid and (u,A_z(u)) satisfies C_z}
F_i(u_-i) = {v_i : (v_i,u_-i) belongs to F_z}.
```

Use the actual allocator output as the witness; do not choose a hypothetical low-flow witness only to pass the constraints. Congested controls may all be physically admissible because their excess offers correctly become queues. Shared physical capacity still constrains their outcome, and any declared quantity/state constraints can make `F_i` depend on the other controls. If only action bounds and universally enforced physical allocation remain, that part of the action domain may be a product set; do not manufacture a GNE coupling constraint by promising previous discharge.

After combining simultaneous owner proposals, recompute `A_z(u_combined)`, the affected local payoffs and quantity residuals. If an actual hard condition fails, retain the last feasible incumbent or accept a documented subset of whole proposals after recomputation. If only accepted flows differ from the separate queries, re-score rather than reject by an invented past-flow guarantee. No allocator rewrites another owner's control. This coordinator rule affects convergence and does not itself establish equilibrium.

**Frozen reservations are optional conservative screening only.** The earlier formula `B(candidate)-sum(other owners' old accepted flow)` is a sufficient remaining-budget screen for a different game that guarantees those old flows. A negative result must not exclude the candidate from `F_i` without an exact joint allocation check. Such a screen may prune work only if its rejection is proved necessary for the declared control-only domain; otherwise it can rank/propose candidates, but final gap evaluation must include candidates it would lock out. Its zero gap is not the requested game's certificate.

## 3. Physical clipping and strategic feasibility are separate results

The existing combined rollout uses offered flow, shared service/receiving allocation and actual accepted transfers. This correctly preserves physical stock when demand exceeds service. **Demand saturation, a red signal or a blocked queue does not by itself make a signal plan infeasible.** Requiring all offered demand to be accepted would incorrectly reject ordinary congested traffic.

The distinction is which flows were priced and promised:

| Result | What it establishes | What it does not establish |
|---|---|---|
| Realized control bounds/grid/write check | One executable 19-owner command; no foreign write changed | Receiving feasibility or leader equality |
| Candidate-dependent joint allocation plus `C_z` check | All accepted flows share one resource/stock ledger; declared hard conditions hold | Agreement with an uncorrected independent local approximation |
| Canonical coupled rollout with its ordinary accepted-flow clipping and ledger closure | Physical model trajectory and stock/event conservation for that command | Feasibility of an earlier unclipped local flow promise, its cost, or its leader quantity |
| Final fixed-context unilateral gap | No tested feasible local priced deviation improves by more than tolerance | Continuous/global equilibrium, price fixed point, or real VISSIM optimality |

At every certified candidate, local costs receive the candidate-dependent shared-node result from `A_z(u)`, not the other actors' old accepted-flow reservations. Compare the local/interface accepted flow and ready/receiving use with this result on the same transfer/time keys; report `max |f_local-f_coupled|` in vehicles and a relative coupling residual separately. If the current local evaluator cannot consume/reproduce those boundary flows, its frozen-coupling result remains a surrogate. Reconciliation must rerun the relevant local/shared-node transitions, preserving the same initial state and controls, until the declared interface consistency tolerance is met, or report `uncertified`. Do not force inconsistent flow by deleting queues. This is a necessary new evaluator interface; current scalar local outputs do not already implement it. No future observed trajectory enters either predictor; later observations are validation only.

## 4. Exact local payoff and final deviation test

Let `Gamma_i(A_z(u))` extract owner i's candidate-dependent shared-resource/interface trajectory. Define `Q_i^r(v_i;u_-i)=local_query_i(v_i,c^r,Gamma_i(A_z(v_i,u_-i)))`, returning `(L_i,f_i,quantities_i,diagnostics_i)`. Initial state, operational snapshot, forecast scope, prices and allocation rule are fixed; physical response is not. Hold the chosen green/offset or VSL/meter jointly, without internally reoptimizing the other coordinate. `L_i` retains the explicitly selected local traffic cost and declared regularization/proxies, with blocked service represented in its local queue cost. Supplying a common physical interface does not replace `L_i` by `JΩ` or sum all other owners' costs into it. Where this boundary cannot yet be implemented consistently, report the narrower frozen-coupling surrogate game rather than claim equivalence.

For exactly the same realized candidate define

```
C_i^r(v_i; u_-i) = L_i^r(v_i; c^r, Gamma_i(A_z(v_i,u_-i)))
                   + Phi_i(v_i; fixed prices, references, weights, cross terms)
                   + Psi_i(quantities_i; fixed leader/dual mode).
```

`Phi_i` charges full-vector green prices once, offset displacement on the canonical circular coordinate, or the realized VSL/meter coordinates plus declared cross terms. It does not also charge the overlapping scalar-green channel. Preserve the existing price weights, including phase weight 0.25, rather than claiming weight-one global-gradient cancellation. `Psi_i` is the explicitly configured quantity/dual expression; a quantity enforced as an exact fixed equality gives a constant linear dual contribution on that feasible set. Do not add a new soft penalty to hide equality failure. PFO and leader-constrained modes remain distinct games unless explicitly redesigned.

Marginal prices retain the distributed correction `p_i = D_i JΩ - D_i L_i` at their declared reference and actual feasible displacement. The local derivative must use this fixed-candidate evaluator and physical realization with matching resource/context policy; a VSL-best-response envelope is not the held-VSL meter partial derivative. Differences between the declared local and full-network forecast scope remain an approximation, not a cancellation theorem. Price refresh is outside this fixed-price round. `JΩ=TTTΩ-(beta_seconds/3600)TDΩ` remains the separate physical endpoint measure and outer leader ranking objective, not every actor's payoff.

At final feasible incumbent `u*`, rebuild one final context `c*`, then evaluate the incumbent and each feasible realized unilateral **joint** neighbor with all non-owner controls fixed. Recompute candidate-dependent accepted flow/queues each time using the same canonical allocation rule and initial state. Let `D_i(u*)` be the declared realized neighborhood intersected with `F_i(u_-i*)`, with no additional old-discharge guarantee. Include the incumbent. Then

```
gap_i = max(0, C_i*(u_i*; u_-i*) - min(v_i in D_i(u*)) C_i*(v_i; u_-i*))
gap_max = max_i gap_i.
```

Report all 19 gaps with evaluated/deduplicated/rejected counts, rejection reasons, nonzero realized displacements, score and physical-write fingerprints, quantity residuals, resource residuals, and local/coupled flow consistency. A capped enumeration, invalid incumbent, unresolved resource mapping, or incomplete query yields `uncertified`, not zero. An owner with no nontrivial feasible unilateral move has a vacuous zero local gap; identify that locked domain explicitly. Shared exact equalities can cause this even when coordinated multi-owner changes would improve performance. Do not label a finite-neighborhood result a full-domain or coalition-optimal equilibrium. Any later refinement, box-walk, writer guard or price/dual change invalidates this certificate.

## 5. Empty realized equality domains: preserve the target, return the reason

Keep the quantity units and definitions separate. The existing `_agent_net_inflow_veh` is a cycle-average legacy protected-area net-flow formula integrated over the horizon, in **vehicles**; it is not actual Ω entry or TD. Extract its full-vector version without changing that definition. Existing FW meter equality uses the finalized equivalent meter **rates (veh/h)** per direction, not the demand-limited vehicles actually released. Do not equate `sum(meter_rate)*horizon` with actual admitted FW traffic. The current physical finalizer itself states that its equivalent-rate model is not microscopic meter signal replay.

Apply an N_P hard equality only in a declared hard-equality mode. A current candidate-dual tracking policy does not become an exact shared equality merely because it has a target. If hard mode is selected, define `abs(sum_i n_i(u)-N_P*) <= eps_NP` in vehicles using the same producer/follower quantity formula. If dual mode is selected, retain its declared multiplier/update rule and report the target residual separately.

For each FW direction `l`, use the producer's exact declared target mapping `B_l(T)` (including its existing cap treatment and frozen `omega_F`), and require in equality mode

```
abs(sum(r in owner l) realized_meter_rate[r] - B_l(N_UF*)) <= eps_rate.
```

Tolerances are predeclared numerical tolerances with their units, not widened until a candidate passes. Physical integer-second schedules can map requested simplex points onto a nonuniform rate grid. If no candidate on the **existing** domain satisfies equality after finalization, return `infeasible_realized_quantity`, requested target, reachable sums and distance to the closest sum. Do not round the target, interpolate schedules, loosen a guard, change `omega_F`, or relabel accepted-flow clipping as equality.

Minimal producer/leader follow-up, requiring an explicit later algorithm change: enumerate and deduplicate the existing admissible finalized meter schedules at the decision context, producing `S_l = {sum realized rates}` for each direction. Filter existing leader targets by

```
T_admissible = {T in existing leader candidate set : B_l(T) belongs to S_l for every l}.
```

This keeps the declared leader target and existing physical strategy domain intact. Compatibility with VSL/trust/release guards is checked on the actual paired candidate; membership in `S_l` is only a necessary screen if those constraints couple to VSL. If all existing targets fail, report no feasible leader-constrained candidate. A separately defined PFO incumbent may still be evaluated under its own policy, with that distinction explicit. Adding new reachable targets is a subsequent producer change; nearest-target substitution is not part of the follower. For N_P, independent per-actor reachable sets cannot simply be summed when receiving/head constraints couple them: a joint feasible witness is required. Current settings are not changed by this proposal.

## 6. Small canonical implementation boundary

The proposed `joint_owner_game.py` needs `resource_view`, `allocate_joint_candidate`, `check_joint_witness`, `quantity_feasibility` and `certify_neighbors`, in addition to the earlier domain/fixed-evaluator API. The smallest correctness reference is the existing canonical held coupled rollout per unique realized candidate, exposing its time-resolved shared-node accepted flows and stocks. Reuse `local_signal_service.register_limit/limit_batch/accepted`, `head_service_resources.regular_context/regular_batch/regular_accepted`, canonical `_effective_available_space/_allocate_receiving_counts`, ready-stock rules and meter finalization. Do not copy the urban model into a second allocator. Shared-node work can later be narrowed only after dependency closure and equivalence are demonstrated; this document does not promise a cheap exact allocation oracle.

Initially use cheap frozen-coupling local queries to propose candidates, but certify the final incumbent and each declared unilateral neighbor using the same candidate-dependent joint allocation and consistent local payoff boundary. Memoize only exact full action/context fingerprints. If the allotted work cannot cover that declared domain, report an incomplete certificate; do not convert a conservative screen into proof. Every generic/corridor transfer using an evidenced group must enter the same inventory, including non-strategic traffic. The new trace-to-local-interface contract and its convergence/consistency failure are explicit implementation work; current canonical functions alone do not certify it.

The acceptance order is: realize copied action → canonical candidate-dependent joint allocation → hard resource/quantity check and consistent owner-local cost plus fixed prices → combined-profile recomputation → final unilateral gap → unchanged writer assertions. Physical clipping remains part of the allocation. It is a valid response to excess offered demand; cost/quantity evaluation must use the resulting accepted traffic rather than an earlier independent promise.

Read-only evidence pins (clock module intentionally excluded):

| File | SHA256 |
|---|---|
| `joint_owner_neighbor_interface_draft.md` | `2f89126ec85b4fd88761a6581bd6fb622a248ce273b61d7d46fae77143d17b36` |
| `follower_game_structure_review.md` | `a6218d63eef0db7f504119d07c7afafacd89c86bd97a3388856c7f78027fe3b1` |
| `local_signal_service.py` | `3e1db452f2d6ee929a766a82e0c8459eca4f4e5027c3c8ba7ebc7d2384efdfa5` |
| `head_service_resources.py` | `5843cb62c36d50602feafbc650e8e2999a8f751039f15e7009bb329c59b5fdc5` |
| `urban_flow_accounting.py` | `7b0e9388fbc6a9a8c7f7bff3665b0406d0b642dc3647037b6e48fd3bfad4c36f` |
| `area_meter_finalization.py` | `a34e91b0a38d888adb9e2f8f57cc1ec5e33536ad2545ed627d8f3d131530ab16` |

Source anchors also read: `vendor/NumSim-mine/src/controllers/wu_faithful_follower.py::_agent_net_inflow_veh` and `_solve_freeway_agent_metered`. No validation or physical assertion is proposed for removal.
