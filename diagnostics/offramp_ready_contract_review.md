# Off-ramp ready availability contract — diagnosis only

The shared service pool needs a distinct **eligible discharge stock**. Subtracting pending transit from physical occupancy or Ω residence would remove real vehicles. The current global drain already makes the right distinction. Signal-local candidates receive total occupancy without its maturity schedule. A separate freeway-local path has a one-step clock mismatch. These are three different interfaces; copying only one initial scalar does not make the entire horizon equivalent.

No production patch was created. The diagnostic uses installed canonical methods on copies of the actual 900-second state. It runs only isolated OR drain services, one signal-local service step, one freeway-local landing advance, and one signal-only arrival admission. No endpoint, full urban interval, optimizer, VISSIM, calibration, capacity or phase change ran. `offramp_ready_contract_review.json` pins all controller source files plus the state/actions/config; source changes are empty and input pickle bytes are unchanged.

## Verified current semantics

| Interface | Source | Exact meaning |
|---|---|---|
| Physical OR stock | `urban_flow_accounting.py:73` | `max(0, storage_capacity − available_storage)` vehicles. |
| Pending alias | vendor `models/state.py:1133` | `offramp_transit_buffer[storage][absolute_urban_step]` is a subset of already counted OR stock, not another stock. |
| Global maturity | vendor `urban_queue_model.py:523–539`; accounted drain `:77` | Remove reservations with `due_step <= service_step`; remaining reservations are in transit. Eligible stock is total occupancy minus that remaining sum. The helper named `_mature_offramp_transit` actually returns **still pending vehicles**, not matured vehicles. |
| Global movement request | `urban_flow_accounting.py:83–102` | `min(turn_beta × eligible_stock, green_fraction × capacity_veh_h × Tu_h)`, then the same corridor pool and receiving checks. Only accepted departures reduce physical OR stock. |
| Global clock | `area_freeway_accounting.py:338–363` | Service indices are interval-start index plus `f*K_fu+u`. All `K_fu` urban steps precede that FW step. FW→OR landings are scheduled at the next urban boundary. |
| Global new signal-branch arrival | `urban_flow_accounting.py:727–754`; vendor `urban_queue_model.py:447–484,617` | Direct/signal split occurs once. Accepted signal vehicles occupy storage immediately and receive due=`admission_step + _inflow_delay_steps(cfg)`. The current delay is a common geometric approximation, not identified ramp-specific travel time. |
| Signal-local initial stock | vendor `wu_faithful_follower.py:589,831,1885` | `_offramp_occupancy` passes total `cap−available`; no pending schedule or ready count. |
| Signal-local future inflow | vendor `local_signal_plant.py:393–424` | Drain total occupancy first, then add frozen `offramp_inflow × Tu_h`, clipped to local storage cap. The newly added amount is discharge-eligible at the next local substep. |
| Local coupling provenance | vendor `wu_faithful_follower.py:533–547` | `_last_offramp_flow` or current FW-flow fallback is a frozen rate; the API carries neither admission timestamps nor signal-branch accepted receipt events. Do not silently rename this rate an accepted signal-only profile. |
| Ω stock/residence | `control_area_objective.py:152–200,302–310`; `urban_flow_accounting.py:781–784` | All OR storage stock remains in the inventory/ledger. Pending reservations add no extra inventory, entry, or exit. Production integrates end-of-urban-step inside stocks. |

At actual state900: `Tu=5s`, `Tf=10s`, `K_fu=2`, start index180, inflow delay7 urban steps (35 seconds). Observed OR storage counts are DW1, FW10, DE5, FE4 vehicles and **all four initial pending dictionaries are empty**. This proves the initialized model treats all these vehicles as ready. It does not prove every observed vehicle was physically at a stop line. Copying the existing buffer cannot recover missing initial age information.

## Bounded reproductions

All rows retain the actual selected control, physical clock fractions, existing movement rates and actual receiver stocks. The service harness executes only the two OR eastbound movements of SC1004. It explicitly initializes the existing per-step service counters and native tag lifecycle. It does not advance unrelated route travel, ordinary W-source service, external generation or the FW model.

| OR_F_W reservation in otherwise unchanged 900 state | OR_F_W total / eligible at step180 | Actual global shared-pool receipt |
|---|---:|---|
| Empty, past179, or due180 | 10 / 10 veh | offW → east: 0.860544217687 veh |
| 10 vehicles due181 or due187 | 10 / 0 veh | offE → east: 0.860544217687 veh |

Sequential canonical drain checks confirm that due181 is ineligible during step180 `[900,905)` and eligible during step181 `[905,910)`. The source receiving the shared service changes from offE to offW. Total stock and the complete Ω ledger inventory close after every isolated drain. Before service, the 10 inside OR vehicles contribute `10×5/3600 = 0.013888888889 veh·h` residence even when eligible stock is zero. This is an accounting identity test; its before-service quadrature is not reported as the production interval TTT.

The current signal-local function still releases offW with the due181 reservation because that reservation is not passed to it. Its original independent service budgets are also still present in this probe; compare the offW eligibility error, not aggregate local/global service equality. The separate unapplied shared-pool proposal addresses budgets and does not yet implement this readiness contract.

New arrivals expose a second clock difference. The canonical signal-only scheduler admits one test vehicle at step182 (910 seconds), increases physical stock exactly once, and schedules one alias at step189 (945 seconds). In the coupled global order that is the first positive FW block after a 900 start. The original signal-local positive frozen inflow added after its first service can discharge at step181 (905 seconds). The **40-second earliest-eligibility difference** combines FW block placement and the existing 35-second transit delay; it is not an empirically fitted ramp travel time or a claim about actual vehicle crossing times. Changing only initial `offramp_occ0` does not fix it.

The existing `link_predictor.LocalLandingState` is closer: it already copies pending reservations and queries stock minus future reservations (`:87–94,122–124`). However, `advance` increments `self.step` **before** service (`:185–186`), starting from180 (`:60`). One actual `advance(Tu)` on due181/stock10 queries eligible10 at step181, whereas the first global service uses step180 and eligible0. Its stock ledger still closes to `1.42e−14` vehicles. Conservation alone cannot detect this timing mismatch. This path's drain uses its existing frozen service formulation; this probe does not establish full green/receiving equivalence with the global model.

## Minimum attachment contract

No scalar `ready0` replacement for occupancy. Use a read-only seed plus a candidate-owned reservation map:

```text
ReadySeed:
    start_urban_step: int
    Tu_sec: finite positive number
    pending_by_offramp: {offramp: {absolute_due_step: finite_nonnegative_veh}}
    storage_key_by_offramp: exact configured physical OR storage mapping

ready(total_stock, pending, service_step):
    total_stock - sum(n for due,n in pending if due > service_step)
```

Validate the complete relevant OR set, exact step lattice, finite nonnegative quantities and `pending <= physical_stock` before accepting the seed. Reject mismatched storage, noninteger due indices, NaN and oversized pending; global currently clips an inconsistent subset to zero, which should not conceal a new malformed attachment. Due<=start rows can be discarded from the copied reservation map without a physical event. Keep total occupancy unchanged for TTS, capacity/receiving and conservation. At each substep, limit source service using `turn_beta × ready` and accepted departures only; the existing common pool and receiver checks still apply. All movement departures from one OR collectively cannot exceed ready stock. Maturity changes eligibility, not inventory or Ω membership.

The new local-service module proposed in `shared_service_pool.patch` is the right small implementation location once approved. Its one extracted ramp-aware stepper can accept an explicit `ready_seed`/arrival timeline; it should not acquire state through a mutable global cache or mutate the shared static `LocalSignalModel`.

There are three caller attachments:

1. Actual `WuFaithfulFollower._solve_urban_agent_local` (`wu_faithful_follower.py:758`, rollout calls939/948) has `state` and owns the green candidate loop.
2. Actual `_solve_offset_local_ramp` (`:1831`, rollout call1932) has `state` and owns the offset candidate loop.
3. Phase refinement has `state` at the existing adapter setup (`vissim_stackelberg_adapter.py:2508`) and at the proposed `ramp_refinement_setup`. It can pass the immutable seed explicitly in `setup`; it must rebuild it with the state-dependent context and clone pending inside every candidate rollout.

The first two vendor methods do not currently pass state or arbitrary kwargs into the local rollout. To avoid copying these large methods or editing vendor, the smallest potential adapter is a **scoped ContextVar binding** at each of these method entries: construct an immutable seed from the exact method `state`, bind with a token, delegate to the original method, and reset in `finally`. The local dispatch resolves that bound seed and passes it explicitly to the extracted stepper, rejecting missing context or mismatched config/signal/clock. Each candidate copies only pending maps from this seed. Nested calls must reset to their outer token; exceptions, repeat candidates and interleaved contexts need tests. This is a proposed attachment, not implemented or claimed validated here. If scoped context is not accepted, the alternative requires explicit caller extraction; silently attaching mutable state to cached models is not an equivalent solution.

Worker installation must wrap these same method entries and refinement setup. The seed is derived in the worker from the serialized candidate state, not inherited from a parent-process context. OFF must call the captured original before any binding or transformation. The common setup must validate that GF profiles start at exactly the seed step and have the same `Tu`/length, not merely the right number of samples.

For `LocalLandingState`, distinguish `service_step` from the boundary **after** that service. Service/maturity must use180 then181, while the first post-FW landing remains boundary182. Merely changing the initial index to179 would alter new-arrival scheduling. A prospective narrow fix would use the current boundary for service and increment after that service; audit every `_schedule` call for its admission boundary before applying it. This report leaves existing production code untouched.

## Future inflow cannot be silently conflated with initial readiness

An accepted-arrival event needs `{offramp, admission_step, due_step, vehicles, branch='signal'}` in vehicles. Reuse the canonical delay function and direct/signal share semantics; do not create another capacity. Store the accepted amount once, and schedule that same amount once. Consume a pre-service boundary admission before its first service at that boundary; a FW block ending at boundary182 is absent from services180/181.

A rate-only frozen coupling needs an explicit conversion contract before this can claim full-horizon consistency. Global supplies blocks of `Tf_h × actual group flow`, then splits and gates accepted landings. Local currently uses `Tu_h × frozen flow` every substep. Simply delaying that existing scalar by seven steps still preserves a different arrival cadence and potentially a different branch denominator. A coupled **accepted** timeline is appropriate as a bounded validation oracle. For arbitrary candidates, a frozen **offered** signal-branch timeline must retain receiving checks and record accepted/rejected separately; actual acceptance can depend on that candidate's storage. No raw cap-clamp loss may be relabelled as an exit or accepted receipt. This is a separate coupling-semantic prerequisite, not completed by the current shared-pool repair.

The narrow initial-reservation wiring can be validated first without changing new-inflow assumptions. Any deployment of only that slice must explicitly retain the future-inflow and initial-observation-age limitations. No positive feedback, FD, capacity, routing prior or delay calibration is justified by these arithmetic tests.

## Validation and next checks

`python -X utf8 -m unittest diagnostics.offramp_ready_contract_review -v`: **4 PASS**, approximately1.6 seconds. The producer writes the JSON evidence separately. Tests cover due-before/equal/after, invalid subsets/timestamps, reservation-vs-stock accounting, original-input preservation, copied canonical services, exact boundary source priority, and one local-landing advance. The ledger and stock checks are stronger than service totals alone, but not a complete local/global horizon equivalence test.

Before an implementation is enabled: test seed cloning and exception restoration, concurrent/nested candidate bindings, OFF exact, worker same-state readiness, frozen GF start-step equality, admitted-but-not-ready residence, receiver rejection consuming neither stock nor service, and a held arrival timeline over at least the first two FW boundaries plus the first maturity boundary. No full optimization or simulation is needed for those regressions.
