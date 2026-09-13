# E8–E9: current route evidence and the smallest conserved interface

The narrow next model change is to preserve **an ordered, lane/route-tagged partition inside the existing E8/E9 stocks**, then use its accepted receipts consistently in continuity, sending/receiving and speed look-ahead. A one-time prefix-density replacement, a fixed lane loss or a fitted lane-change wait is not established. The new current-route observations make the late congested state's access problem identifiable, but they do not yet identify a predictive lane-change/discharge law or prove that one mechanism explains the1200 breakdown.

This diagnosis reads the completed source run's paused1200 and3300 snapshots only. `complete_records` and `complete_vehicle_routes` validate completeness, time and exact ID correspondence. It does not read a future snapshot into the hypothesis, run an endpoint/MPC/VISSIM, rescan FZP, change a production file or repeat the off-ratio/positive-anticipation experiments. The134 current source pins and manifest remain unchanged. Exact IDs, lane counts, native paths, source hashes and algebraic results are in `e8_ordered_gate_observability.json`.

## What the new observation establishes

The native10682 from-endpoint is mainline link2 **lane1** at4746.884465m. E9 starts4621.726m and ends5135.252m. Thus the approach is125.158465m and the road after the diverge is388.367535m.

| Current paused state | E9 total / prefix / rear N | Whole / prefix / rear density, veh/km/lane | Prefix direct route1130:3 by lane1/2/3/4 | Direct vehicles needing lateral exchange |
|---|---|---|---|---:|
|1200|47 /23 /24|22.881 /45.942 /15.449|10 /0 /0 /0|0|
|3300|59 /57 /2|28.723 /113.856 /1.287|8 /15 /17 /6|38|

At3300,96.6% of E9 vehicles occupy24.4% of its length. Among its46 directly routed vehicles before the node,38 are not in the connector's lane. They require at least67 adjacent lane transitions in total to reach lane1; this counts route obligations, not successful changes, seconds or capacity. At1200, all10 directly routed prefix vehicles are already in lane1, whose11 total vehicles average8.715km/h and include5 below1km/h. At that same instant10682 itself has9 vehicles,34.850km/h mean and no vehicle below1km/h. Therefore missing lateral eligibility is particularly clear at3300, while neither a stopped connector spillback nor out-of-lane direct demand alone explains1200.

At3300 the10639 merge connector has46 vehicles/33 below1km/h;10681 has2/0. Current group aggregation therefore also erases a large asymmetry in where the ramp vehicles will merge. These are complete paused counts, not passage rates or calibrated storage limits.

The stored prediction comparisons refer to the previous source-run implementation and its held commands:1200→1350 E8 predicts96.116 vs observed40.485km/h;3300→3450 predicts12.886 vs1.952. Those endpoint outcomes are evaluation evidence, not inputs to the new current-state partition. The new production objective/observer changes have not been replayed here as a new E8 forecast.

## Ordered route eligibility is now partly proved

The native sequence is10643 exit4386.333 →10639 merge4610.819 →10682 exit4746.884 →10681 merge4899.956m. The actual global code still injects R_F_E at one configured merge index (`area_freeway_accounting.py:69–74`), forms whole-cell receiving and off-subtracted sending (`:122–126`), takes OR_F_E at one cell (`:168–185`) and reads the next whole-cell density (`:203`). The local model stores the same grouped indices (`local_freeway_plant.py:69–95`) and uses matching scalar sending/receiving/anticipation (`:167,199–214,257–268,283–302`). `link_predictor.py:381–413` invokes this local step and then lands its aggregate off flow. Accounting can close while these locations and eligibility remain wrong.

Native1134:3 is69→10637→70→10639→2, with its link2 destination at chain5040.762m, after10682. Its observed prefix vehicles—2 at1200 and8 at3300—are proved through this diverge. They did not traverse decision1130 and must not receive its exit fraction. Native1135:4 enters via10681 after10682, so it cannot take the earlier node. Native1130:3 explicitly traverses10682; route1130:1 takes the earlier10643. The evidence includes the complete native decision/route attributes and ordered link lists. Unrecognized/null/expired current routes are retained as unresolved, not automatically relabeled through.

This prevents a tempting incorrect fix: moving the entire R_F_E group to E8 would misplace10681 and cause a whole-cell off fraction to consume10639's proved-through cohort. Moving only an already computed direct departure from E8 to E9 also leaves E8 sending incorrectly reduced. Both source-cell debit and through sending must come from the same ordered receipt calculation.

## Why a prefix-density constant will not persist correctly

The observed prefix density is a legitimate initial measurement. It is a partition of existing N, not extra vehicles. But two candidate states can have the same macrocell N and speed while their vehicles have moved from prefix to rear, or while the direct-route lane labels differ. A fixed multiplier or a repeated read of the initial prefix cannot distinguish them. Holding that density fixed preserves a queue after it discharges; reverting to the whole-cell value immediately loses the localized queue again. Updating just the speed gradient without the accepted prefix→rear/direct transfers gives contradictory flow and speed states.

The algebraic regression uses46 direct vehicles as an explicit nonbinding-service/receiver illustration. With the observed lane split, only8 have lane1 compatibility; an alternative state with the same total and all46 in lane1 has46. The current scalar density/speed input cannot distinguish these states. These numbers are **not150-second or10-second discharge bounds**: longitudinal travel, signal/downstream service and subsequent lane exchanges are excluded from the illustration. An explicit one-vehicle lateral exchange increases compatible stock by one without increasing physical N. Ineligible and rejected vehicles remain at their source and continue accruing residence. Five small regressions pass for these identities, source order, candidate-copy isolation and accepted-only transfer. They prove an interface requirement, not a repaired speed forecast.

## Macrocell partition versus short-cell integration

| Choice | What it preserves | Main limitation |
|---|---|---|
| Keep E8/E9, add disjoint prefix/rear and route/lane subsets | Existing geometry, coarse N and Ω residence; one accepted receipt is debited/credited once | Must evolve eligibility and both partition stocks; needs a shared gate and consistent look-ahead, not only a new measured density |
| Replace125m prefix by an ordinary METANET cell at Tf10s | Explicit spatial gradient | Existing explicit rho×v outflow can send more than its stock; not acceptable unchanged |
| Nested short-cell/lane solver | Could resolve physical node ordering and travel within a macro step | Requires its own valid step, exchange law, coupling synchronization and verification; larger model change |

The numerical counterexample uses a declared120km/h illustration and the existing rho×v continuity arithmetic. For125.158m, v·10s/L=2.663; a one-vehicle, zero-inflow prefix would give−1.663 vehicles before clipping. A time step no greater than3.755s is necessary for that simple positivity case, not sufficient proof of a new scheme's stability. If all four native nodes **and** current macro boundaries are aligned, the10639-to-E9-boundary fragment is only10.907m; the analogous limit is0.327s. Thus a naive exact-node split adds substantial numerical cost. No short-cell solver was installed or declared stable.

An internal gate within the macrocell avoids applying the existing PDE update to that tiny fragment. It can cap accepted transfers by eligible source stock and reserved receiving space, preserving positivity and mass at the macro step. It still needs event/travel timing: just transferring the maximum eligible count every10s would invent a service law. This is why the partition/gate is the narrower next interface, not a claim that its missing dynamics are already solved.

## Minimum state and attachment contract

1. Seed tagged subset counts from complete current IDs/position/lane/route. Their sum must equal the existing E8/E9 counts exactly. Retain residual unresolved stock separately. They are aliases/partitions; do not seed them again into the Ω ledger or add their residence to macrocell residence.
2. Keep10639/10681 physical ramp queues and accepted branch receipts before `urban_flow_accounting.py:356–365` aggregates meter departures and coupling combines them. Preserve existing four group controls and physical command allocation. A requested equivalent rate is not an accepted branch receipt.
3. Admit each receipt at its real node. A cohort can encounter only downstream nodes contained in its active route. Lateral movement is an explicit accepted subset transfer; do not treat a timer expiring as an observed lane-change success. Return common accepted node receipts, unresolved/rejected quantities and the updated partition.
4. Global and local consumers use those same receipts for sending/receiving, E8/E9 continuity and OR/direct scheduling. `area_freeway_accounting.py:353–364` currently obtains a group receipt then schedules a group off flow; this is the common boundary that needs a branch contract. Candidate state copies must carry their own partition, reservations and timers; config contains static topology only.
5. Speed look-ahead consumes the evolved physical approach state relevant to that route/lane. Do not sum every blocked lane into a permanent lost-lanes coefficient. Through-flow blocking is partial and depends on vehicles sharing the same lane/order or successful exchanges. The current snapshot identifies who needs a change; it does not identify all future FIFO interference.

## Next identifying data and acceptance criteria

Current paused records already supply lane, speed, position, ID and static route. The smallest next observation exercise is to follow **those current IDs** in bounded1s records over the same held-command interval: time to each accepted lane transition, arrival at10682, actual direct/through crossing, merge receipt, and explicit censor/removal. Record lane-order/gap and downstream10682→121 movement at the event. Treat these future measurements as validation/identification data, never forecast inputs. Retain free-flow, breakdown and recovery holdouts; current snapshots and a single persistent jam cannot establish a universal success rate.

No observed lane-change probability, exchange delay law,10682 saturation capacity or partial-FIFO interference width has yet been fitted here. Consequently there is no warranted quantitative claim that this prototype improves96→40 or13→2. What is now stronger than the prior report is the exact current-route proof of the38 incompatible-lane vehicles and the1134 merged cohort that must bypass the exit prior.

Green/offset can change downstream acceptance and approach arrival timing; meters change branch-specific merge receipts; VSL can change upstream arrivals and interactions before the node. The interface preserves these causal channels without an invented VSL capacity bonus. A successful next model must improve branch/through receipts, prefix/rear stock and lane delay together, close mass, preserve OFF and candidate isolation, and handle open-road recovery. Matching only E8 speed would be insufficient.

Reproduction: `python -X utf8 -m diagnostics.probe_e8_ordered_gate_observability` and `python -X utf8 -m unittest diagnostics.test_e8_ordered_gate_contract -v`. The diagnostic has no production hook.
