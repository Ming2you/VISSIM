# Four control groups with physical route and branch receipts

The four control groups can remain. The smallest useful structural change is to preserve **route-tagged portions of existing stock and physical accepted receipts**, before aggregating them for the four levers. A new percentage in `off_ramp_split_ratio` cannot restore information already discarded at observation, merge and landing. A metadata-only tag added after the current freeway update would document the error but would not fix it.

This is a read-only interface review, not an implemented node law or calibration. No production/vendor/config/evidence bytes were changed and no endpoint, optimizer or VISSIM run was executed. `audit_freeway_route_observability.py` reads the completed observed-NC paused snapshots at900 and2700. Its JSON preserves each selected vehicle's physical position/lane/current-route tuple and source hashes, checks the complete route envelope and exact physical-FW versus cell count equality, and reports source changes0.

## Where current information disappears

|Current stage|Exact source location|Retained information / loss|
|---|---|---|
|Paused observation to FW state|`vissim_stackelberg_adapter.py:9513–9542`|`freeway_segments` becomes one count-derived density and count-weighted speed per cell. Complete ID/lane/position/current-route records are available alongside it but not used for freeway state. The new urban route corridor consumes those records only for its declared urban partitions.|
|Physical meter connector observation to group queue|`vissim_stackelberg_adapter.py:6088–6097`|Physical connector counts contribute once to `ramp_queue[group]`; provenance still knows the original link, but the dynamic queue no longer carries physical-connector identity or route composition.|
|Actual metered departure|`urban_flow_accounting.py:354–365`, `coupling.py:116–128`|A single group's actual accepted vehicles leave its queue, then become one scalar veh/h summed over urban substeps. There is no branch-addressed receipt vector. This is a loss of physical allocation, not a failure of total mass conservation.|
|Merge placement|`area_freeway_accounting.py:71–77`; local `local_freeway_plant.py:165–167`|The entire group's accepted release enters one configured merge index. FE10639 is physically before the second exit; grouped FE release is placed at the same index as10681 after it.|
|Freeway split before continuity|`area_freeway_accounting.py:123–126,170–181,198–202`|`mainline_sending=(1-p)q` and `normal_off=pq` act on the whole cell. Off sending is capped once per group; accepted total is deducted from this one cell. Neither route population nor branch order survives this step.|
|Direct/signal landing|`urban_flow_accounting.py:727–755`|Only after FW deduction, selected group vehicles are split by a fixed direct share into existing signal/direct storages. The current capacity guard prevents selected vehicles from disappearing, but cannot recover which branch they used or move an exit back to its actual position.|
|Receiving guard|`observation_projection.py:198–249`; `link_predictor.py:24–34,139–150`|`min(signal_space/(1-share),direct_space/share)/dt` safely fits the prescribed fixed split. This is a total-flow cap for that mixture, not a route-resolved two-exit node. A blocked branch currently constrains the whole mixture.|
|Local candidate|`local_freeway_plant.py:65–95,203–212,258–265`; `link_predictor.py:57–64,166–178`|Copies group split/index/one signal occupancy, then repeats total split and post-FW landing. Updating the global endpoint alone would leave candidate response using a different interface.|

Current physical branch projection and the Omega ledger already prevent duplicated stock. They should remain the physical accounts. Route/lane tags must be **partitions of those same accounts**, with `sum(tags[cell]) == continuity N[cell]`, `sum(tags[ramp]) == ramp_queue[ramp]`, and corresponding existing landing-storage partitions. Do not add a second copy of tagged stock to TTT. `TrafficState.copy` (`state.py:1187–1188`) already uses deepcopy, so a candidate-owned serializable attribute can use this mechanism; local candidate initialization and spawned-worker installation still require explicit tests.

## Native joint choices and order

|Group|Ordered physical interfaces, chain metres|Eligible native decision weights: signal/direct/through|Conditional last-branch share **only among surviving members of that same decision cohort**|
|---|---|---|---|
|FE|10643 exit4386.333 →10639 merge4610.819 →10682 exit4746.884 →10681 merge4899.956|1130:1.6 /4 /8|direct4/(4+8)=1/3|
|DE|10481 exit6826.843 →10490 merge7153.367 →10483 exit7240.272 →10484 merge7448.366|1131:4 /3 /8|direct3/(3+8)=3/11|
|DW|10479 exit3425.401 →10480 merge3525.124 →10491 exit3650.905 →10482 merge3832.586|1132:3 /3 /10|signal3/(3+10)=3/13|
|FW|10645 exit5909.740 →10646 merge6075.357 →10638 exit6224.840 →10644 merge6777.115|1133:1 /3 /8|signal1/(1+8)=1/9|

These denominators explain the ordering; an implementation with already chosen route tags must **not sample a new choice at each exit**. Select once when an eligible unchosen cohort reaches its actual decision plane, or preserve an observed current route. Future native choice is an expectation from a pinned conditional prior, not identification of an individual vehicle's realized choice. After-first-exit merge cohorts cannot take that passed exit. Their route contracts or explicitly identified conditional priors are separate from1130–1133. An unconditional0.2, a native total prior, and a direct-given-off share are three different inputs.

The existing matched-ID600–750 evidence is decisive: intermediate FE/DE/DW/FW merge cohorts had respectively0/7,5/10,6/6,14/15 off outcomes, versus mainline decision cohorts84/193,61/119,84/205,46/148. Those are different populations and times, not four fitted cell ratios. Likewise native joint prior corrects the total-only FE signal-share error but does not identify E8's receiving/lane-change dynamics.

## Available paused observation is already useful

Within each decision-to-second-diverge region:

|Time|Group stock|Matching group's current native label|Null current route|Other current decision|
|---:|---|---:|---:|---:|
|900|FE207|207|0|0|
|900|DE66|66|0|0|
|900|DW214|214|0|0|
|900|FW70|63|6|1|
|2700|FE1659|1652|0|7|
|2700|DE48|48|0|0|
|2700|DW412|407|3|2|
|2700|FW74|70|4|0|

These are snapshot stocks, not flow fractions or decision-gate denominators. The regions do not cover all FW stock; observed total FW at900 is W468/E373 and at2700 W718/E1814. No vehicle from an unrepresented region is silently dropped or routed by this audit.

“Other current decision” is **not automatically an unknown route**. All seven FE exceptions at2700 carry1134:3, whose pinned path69→10637→70→10639→2 ends at link2 position2306.235. Its destination is beyond10682's diverge at2012.357; the remaining selected path on link2 therefore specifies through at this exit. Their chain positions4621.054–4718.830 place them after10639 and before10682. The existing shared-69 route engine has upstream source identity but the group ramp queue loses it before FW injection.

In contrast,900 FW vehicle350 has1135:2 ending on120 at2272.298 (chain6094.657), **before** the second exit at6224.840. The2700 DW1137:3 routes end on26 at3591.078, before the second exit at3650.905. A current route that ends before the next branch is insufficient to assign the subsequent outcome. Null identities are observed absence of a current route; `vehicle_routes.py:10–15` deliberately does not equate null with eligibility for another decision. Preserve explicit uncertainty or recover qualified history/next-route evidence, rather than silently applying the upstream native prior to these vehicles.

The actual new `codex_area_sources_beta0_s13_20260910` decision900 raw was independently read after it completed. Its W468/E373 counts and **every selected group record's ID/position/lane/speed/current-route tuple exactly match** the observed-NC900 audit above. This is a checked equality, not an assumption that warmup must be identical. `freeway_route_observability_actual900_final.json` records the comparison and pins the actual raw snapshot. Thus the route composition needed for the first prediction was already observable when its command was chosen.

The independently completed aligned held-action900–1050 replay (`source_interval_900_1050.json`) passes source/config identity, actual213-row CSV alignment,130SG/ramp1s readback and15 held FW steps. It still predicts FW1176.087 versus COM917 (FZP918), and Omega TD442.756 versus483 observed plus227 terminal-inferred exits. The ten explicit internal inputs admit all88.333 expected vehicles with backlog0; total inside generation including other existing sources is205.95. This does not mean all source processes are exact or that the TD gap is entirely freeway-related.

Summing that replay's **accepted group off flow** at its recorded step lengths and comparing only explicit physical source-road→offconnector entries gives:

|Group|Model accepted veh|Physical first branch entry veh|Physical second branch entry veh|Physical total veh|
|---|---:|---:|---:|---:|
|FE|38.504|10643:23|10682:45|68|
|DE|26.886|10481:35|10483:32|67|
|DW|42.812|10479:32|10491:45|77|
|FW|33.143|10645:41|10638:28|69|
|Sum|141.345| | |281|

The branch-source identities are checked against the pinned physical geometry; connector discharge, initial connector stock and disappearance are not added. These FW→off transfers are largely internal to Omega, so the139.655 difference must **not** be reported as an equal TD reward error. This identifies persistent gross routing/interface underprediction in the actual first interval while the parent separately follows E8's growing speed/stock error. It does not identify a new capacity or prove that changing a probability alone would reproduce the plant.

## Minimum transition/API contract

The signatures below are proposed integration contracts, not new production APIs. All quantities returned as receipts are **accepted vehicles over an explicitly stated time interval**, not a requested veh/h rate.

|Observation/state needed|Minimum transition/API|Current attachment and invariant|
|---|---|---|
|Complete paused ID/link/lane/position/speed and current decision/route/type; pinned route path, decision placement and native combination semantics|`seed_tags(raw, geometry, route_contracts, existing_inventory) -> partitions, unresolved`|Immediately after actual physical projection and before area seed. Reconcile every existing cell/ramp/landing stock. Initial tag assignment causes zero entry/exit/TTT events. Track all current route decisions, not only1130–1133.|
|Cell's before/after-decision and before/after-physical-interface portion; existing accepted mainline cell receipts|`transport_tags(source_partition, accepted_veh, downstream_partition, interface_progress)`|Where `q_inter`/entry/terminal values are chosen. Need an explicit conservative selection/order rule; proportional selection would itself be a model approximation and must not be hidden. Every transferred tag leaves its source once. Mere cell labels cannot resolve both ordered nodes inside one cell.|
|Eligible unchosen future cohort crossing a pinned decision plane|`choose_native_once(cohort, decision, route_weights, interval)`|Only a real future decision transition. Preserve observed/chosen tags. Reject re-choice for past-decision arrivals; do not confuse static-route combination with a new physical inflow. Choice changes composition, not total N.|
|Physical ramp connector partition, associated existing meter waveform/service and FW receiver; incoming urban/shared/sc2001 route/source tags|`accept_merge(physical_connector, requested_tags, existing_receiving, dt) -> accepted_tags, held_tags`|Before group queue depletion/`merge_pending`. Attach only accepted branch receipts to the correct chain interface; their sum is the same group's actual release used for the existing control/price diagnostic. Do not split the group total afterward using a stale observed ratio, and do not give each connector the full shared group budget.|
|Route eligibility at each actual diverge, signal/direct existing landing space, lane-access evidence|`accept_diverge(physical_connector, eligible_tags, existing_receiving, dt) -> receipt`|Replace the grouped `p*q` selection **before** FW continuity. Route-specific sending and existing space bound the receipt. Remaining tags stay in their actual source portion. A partial-FIFO or lane-change acceptance law is still unidentified; no numeric restriction is proposed here.|
|Receipt's physical connector and accepted branch identity|`land_receipt(receipt, existing_signal_or_direct_storage, urban_step)`|Use the accepted amount unchanged at current scheduler and emit one existing Omega transfer. Do not apply `offramp_direct_share` a second time. Downstream mixed W_out populations remain tagged portions of the same storage; no extra reservoir capacity or duplicate arrival reservation.|
|One candidate-owned partition and interface state shared by global/local implementation|`copy_view / snapshot_receiving / commit_receipts` with one transition implementation|Global `area_freeway_accounting` and local plant/candidate must call the same receipt function. Four existing lever variables/control groups stay; physical branch event keys are finer than their control IDs. Repeated endpoints and fresh workers must reproduce identical receipts and preserve the original input.|
|Per-lane approach stock/speed/queue front, route compatibility with lane and next node|Read-only lane/route diagnostics first, then a separately evidenced receiving law|Current mean downstream rho combines queued and open portions. Tags alone cannot change that speed look-ahead correctly. The136m FE weaving interface at120km/h has about4.1s transit time, below10s FW update; adding a fine cell with the current time step is not a justified repair.|

Existing urban `route_choice_corridor` demonstrates candidate-private tagged storage, explicit current-route/null handling, accepted-only transfers and finite shared service budgets. Reuse these **invariants**, not its queue-delay engine unchanged: a freeway interface also participates in METANET continuity, convection and anticipation on a different time grid. A second independent “mini freeway” would leave the original mean cell taking the same vehicles' flow twice.

Before any opt-in dynamics implementation, the acceptance law must close the presently unresolved cases: current route ends before the next exit; repeated urban↔FW visits; source-specific physical ramp split after aggregation; and blocked route versus unblocked through-lane access. Minimum tests then cover initial partition equality, first-exit impossibility for intermediate arrivals,1134:3 through preservation, no resampling on repeated substeps, rejected receipt retained at source, shared receiver/service budget consumed once, exactly one land/area transfer, closed/reopened receiving, source/terminal accounting, global/local equality and candidate/worker isolation. A metadata-only shadow ledger can validate these observations first but should not be presented as repaired prediction dynamics.

Read-only reproduction: `python -X utf8 -m diagnostics.audit_freeway_route_observability`. For the actual first action and recorded held-action evidence: `python -X utf8 -m diagnostics.audit_freeway_route_observability --run codex_area_sources_beta0_s13_20260910 --times 900 --reference-audit diagnostics/freeway_route_observability.json --interval-evidence diagnostics/source_interval_900_1050.json --out diagnostics/freeway_route_observability_actual900_final.json`. The output JSON pins network/mapping, completed raw snapshots, reviewed code and prior evidence; all sources were unchanged during the run. The interval option summarizes existing evidence and does not execute another endpoint. No probabilities, capacities, lane-loss coefficients or production settings were fitted or promoted.
