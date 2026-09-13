# One canonical rollout with disjoint owner costs

**Recommendation:** use a disjoint responsibility-stock projection of the
canonical ledger as the correctness reference for the new 19-owner game,
provided it is explicitly introduced as a **new payoff definition**. This is a
smaller and more auditable way to make every owner score use the same physical
response than extending both existing urban and freeway local plants to
consume a full shared trajectory. It does not preserve the current local
payoffs, remove the need to define shared feasibility, or establish a cheap
oracle. Keep the existing game unchanged outside an explicit new mode.

This review only reads source. No patch, model, endpoint, test, COM/VISSIM or
production change was made. The earlier `joint_owner_oracle_integration_plan`
describes preservation of the old local payoff; the alternative below
deliberately replaces that part of the proposal.

## What the existing ledger can and cannot supply

`control_area_objective.model_stock_values:152` exposes six distinct families:
`movement`, `ramp`, `origin`, `storage`, `freeway`, and `transit`. Storage is
occupied capacity, not available space. Arrival/release reservations are not
extra stocks. Freeway stock is aggregated **per direction**, not per cell.
`area_runtime.seed_from_projection:25` seeds physical inside/outside cohorts,
with freeway initially inside and mainline-origin queues initially outside.
Only the inside amount belongs in an Ω-based local cost.

`ModelAreaLedger.residence:301` currently accumulates a single scalar TTT.
`transfer:243` updates cohorts and accumulates actual accepted-transfer TD,
including the explicit physical-path crossing/remap branch. Neither keeps
per-stock cumulative costs. `flow_counts` counts accepted route flow, not
necessarily Ω departures; many calls have no event ID. The final stock and
`explicit_events` therefore cannot reconstruct exact owner TTT/TD afterward.

Additive, candidate-private accounting at these **existing two primitives** is
needed. Preserve their global arithmetic and timing. Accumulate owner
residence from `dt_h * stock['inside']` when the original residence call runs;
attribute the TD increment actually computed by `transfer` once, without
replacing it with accepted count or terminal-stock subtraction. An optional
immutable responsibility map and small owner counters on the existing ledger
are sufficient; a second allocator, state evolution, or local plant is not.
They must survive `clone` and the fresh endpoint ledger reset in
`area_runtime.evaluate_price_point:199`.

Urban residence remains at the existing post-urban-step `T_u` point
(`urban_flow_accounting:788`); FW/origin residence remains after off-ramp
scheduling at `T_f` (`area_freeway_accounting:368`). Reclassifying an OR stock's
cost owner must not move its integration clock or also add the legacy
`offramp_storage_ttt_moved_to_freeway` result. That old result is an accounting
presentation in the coupled return, not another ledger residence.

## A control owner is not yet a cost owner

`joint_owner_addresses_candidate.build_ownership` defines 17 selected SCs and
two FW directions from final cfg, mapping and physical write addresses. It
does **not** define responsibility for stock. Build the new responsibility
contract after all canonical route/native-input/corridor and projection
configuration, not from the initial config's names or deleted aliases.

| Stock family | Available join and required decision |
|---|---|
| `freeway:FW_E/FW_W` | The direction's FW owner is an exact address join. Keep all 21 cells' current aggregate cohort/clock; do not invent cell ownership. |
| `ramp:R_*` | `cfg.network.ramp_to_freeway` provides the owner of the two model rates. This is a defensible responsibility rule, separately declared from the upstream SC that feeds the reservoir. Count each ledger stock once. |
| `origin:FW_*` | Direction join is available, but initial outside-Ω stock contributes zero Ω residence. The new payoff cannot silently import the old outside-origin queue penalty. |
| `movement:*` | Join through final `urban_movements[...].intersection/signal/phase`, checking agreement and selected-owner membership. Native/unsignalized service is not proof of a controlled owner merely because its name starts with SC. An assigned responsibility remains a policy choice, not a newly discovered actuator. |
| Generic `storage:*` | Inspect all final movements whose `origin` is this store and their physical route support. A unique controlled downstream service can support a declared rule; zero or several owners require an explicit assignment. Do not infer ownership by splitting an underscore name. |
| OR/shared/corridor storage | OR stores are charged by old FW and urban-local mechanisms in different ways. Shared69, SC1004's 1129 prechoice store, the 1128 prefix/local stores, native SC15 generated prefixes, and known W_out cohorts do not get a unique owner from the ledger key. Choose one whole-stock responsibility or explicitly classify as unowned. Neither the source-name prefix nor the future branch prior supplies an ownership weight. |
| `transit:<source>` | This is actual `urban_inflow_transit_buffer` mass. Join its configured source and owned route, not the separate arrival/release reservation schedules. If an aggregate key contains destinations with different proposed responsibilities, use an explicit single responsibility/unowned rule; splitting it requires retained cohort evidence and additional accounting. |

Prefer a fixed **0/1 map** for a first version, with an explicit `unowned`
bucket, over dynamic fractional weights. An intentionally unowned inside stock
stays in global JΩ and its effect remains in external-price construction.
“Unowned” must not mean silently missing: enumerate every initial and
potentially created stock, reject unknown new keys, and publish positive-stock
coverage. Do not relabel missing physical route/ownership evidence as known;
the existing held-unknown/route-completeness gates still apply.

For an exit, assign the actual TD increment to the source stock's declared
responsibility, or an explicit route rule where the source is external or the
grouped physical-path remap needs a different declared attribution. Record
the rule. Moving from one owner's inside stock to another's is **not TD**.
An Ω outward crossing is attributed once even if several physical/model views
reference it. Existing proportional mixing and grouped stopline/path timing
approximations remain approximations; the new attribution does not fix them
or justify earlier rewards.

## Payoff and price contract

For fixed context `z`, realized joint control `u`, and its one canonical
response `A_z(u)`, define

```
Ji(u; z) = TTT_i(u; z) - (beta_seconds / 3600) TD_i(u; z)
JΩ = sum(Ji for the 19 owners) + J_unowned
Ci = Ji + declared fixed external-price term + declared quantity term
```

The decomposition identity includes unowned/native costs. It is not a claim
that the 19 owners cover the whole Ω. TTT uses veh·h, TD uses vehicles, and β
uses the existing seconds-to-hours conversion. Compare component sums with
an explicit floating-point accounting tolerance while leaving the old global
sum order untouched; do not manufacture bit identity by rewriting its sum.

This drops or redefines the former local queue/speed/density/blocked-ramp and
optional terminal/regularization terms. For example,
`P._phase_local_cost_phased:330` is queue TTS with frozen arrivals/receiving;
the old FW kernel contains weighted queue/density terms. Even keeping λ and
price-weight numbers unchanged changes their relative influence when the
base payoff changes scale. List removed/retained terms explicitly. Do not
silently add the old local result to Ji, or give every owner all of JΩ.

Rebuild **all enabled price channels** from the same two realized actions and
the same canonical response:

```
external directional secant = [JΩ(u_probe)-JΩ(u_ref)]
                              - [Ji(u_probe)-Ji(u_ref)]
```

Use the actual feasible displacement in its declared coordinates. Green
projection/quantization, signed offset wrap, full expanded VSL aliases, and
physical meter schedules must match on both differences; a meter probe must
not internally optimize VSL. Zero displacement is not an estimated derivative.
For several green directions, a scalar/vector price representation must fit
or report the rank/residual of those secants instead of pretending a clipped
nominal δ is the actual direction.

Old `D JΩ - D L_i` prices are invalid for this new base. Keep β and the effective
weights unchanged during the redesign (current phase weight 0.25; other
channel weights/modes from the effective controller). The local first-order
combination is `(1-w) D Ji + w D JΩ` only on the same represented direction;
weight 0.25 is not a global-gradient cancellation theorem. Use phase-vector
and offset channels once, not phase plus an overlapping scalar-green charge.
Freeze prices, references, leader target, λ and ω through every sweep and
final unilateral check. A price/dual refresh starts another game context.

## Shared feasibility remains a separate obligation

The canonical allocator provides a consistent physical response with finite
storage, ready clocks and single accepted-only head budgets. A residence
partition need not touch its resource ownership: shared 10634 still has one
budget, irrespective of the number of cost owners or movement aliases.

However, accepted clipping and ledger closure do not show that independent
offered-flow promises jointly fit a head or receiver. Choose the contract:

* If strategies are physical commands and excess offered flow simply queues
  under the canonical allocator, most resource constraints are dynamics of
  `A_z(u)`. Coupled costs alone do not make the product command domain a GNE.
* If strategies also commit flows or have joint hard constraints, expose and
  check those same commitments/reservations against the canonical resource
  schedule. Successful clipping cannot certify an infeasible promise. The
  small ledger owner counters alone do not supply this witness.

N_P and N_UF must also retain explicit definitions. The existing
`W._agent_net_inflow_veh:634` is a forecast/cycle-average protected net-flow
quantity in vehicles, not owner residence or Ω entry/TD; it still reconstructs
greens from p1. Its full-vector extraction remains necessary if retained.
N_UF uses finalized equivalent meter rates in veh/h, not accepted release
vehicles. A new accepted-flow target would require coordinated producer and
follower changes. A tracking dual is not a hard equality, and an exact shared
equality can leave an owner only the incumbent: label the resulting zero gap
vacuous rather than claiming useful freedom or a global optimum.

## Minimal implementation order and cost

1. Declare and validate the responsibility/exit-attribution contract on final
   cfg; retain native/unowned costs explicitly. Add passive owner counters to
   the current ledger primitives and return all 19 components plus unowned
   from the current endpoint. Global objective and physical transitions stay
   unchanged.
2. Use one fixed-candidate canonical rollout for each unique full physical
   action/context. Return all Ji, JΩ and physical/quantity diagnostics from
   that same run. Connect this result directly to the proposed finite loop;
   bypass the old local optimization/phase/offset searches in the new mode.
3. Rebuild the matching FD subtraction and price representation, then do the
   final complete 19-owner unilateral audit under the same fixed context.
   Any later guard or optimization invalidates that certificate.

This eliminates the need to pass the full `Gamma_i` into two separately
evolving local models **for the cost definition**, and removes their mutable
flow-cache/setup dependencies from the new score. It does not make the
canonical global hooks pure: retain private state/action, scoped global lane
context, worker reset, and source/plan/schedule fingerprints.

Each unique neighbor still costs a full held canonical rollout. Obtaining all
owner costs together saves repeated incumbent queries and duplicate FD work,
but does not make 19 owners or all joint green×offset/VSL×meter neighbors free.
Never take owner costs from different candidate trajectories. Exact memoization
can use full immutable action/context values; incremental locality or cheap
surrogates require a later equivalence proof. Report evaluation/time limits
and incomplete gaps honestly; no speed or convergence claim follows from this
read-only design.

Before live use, the decisive small proofs are: owner+unowned conservation of
TTT/TD at both clocks; internal responsibility transfer adds zero TD; mixed
cohort/physical-path exits allocated once; native generation and pending
transit counted once; final cfg catches a deleted alias/new stock; clone/spawn
and query-order isolation; unchanged global JΩ/physical trajectory; matching
FD directions; and final incomplete/infeasible domains remaining uncertified.
No such new implementation or test has been executed here.
