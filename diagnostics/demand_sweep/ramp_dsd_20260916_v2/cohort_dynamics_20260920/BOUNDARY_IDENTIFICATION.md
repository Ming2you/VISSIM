# 2026-09-20: control-response identification checkpoint

**Gain prediction remains NOT_QUALIFIED. No model/config/controller or network was promoted in this checkpoint.** Existing native runs were analysed; no new VISSIM process was started. The goal remains active.

## What the extra diagnostics established

1. Current rear-half stock/speed improves local10s boundary-flow RMSE by30–41%. A position-only linear reconstruction failed. The two-half initial snapshots aggregate exactly to the existing group counts and speeds (maximum rounding difference5.7e-14km/h).
2. A conservative transport-only diagnostic with *future actual velocities and boundary entries* reproduces much of the port-free regional450s response even at the original coarse resolution. For seed23 before10643, actual ΔTTT−0.73778veh·h versus coarse10s−0.59957, coarse1s−0.51939, two-half1s−0.62169, four-part1s−0.68777. The downstream actual+0.76056 is already coarse10s+0.73257. Refinement helps local state error, but is not sufficient justification to replace the entire grid. This is **not a causal controller forecast**; no future inventories were reset.
3. The earlier speed oracle only replaced the METANET speed equation, after which merge/FIFO projections could change the speed used by the next ramp-supply query. The diagnostic now also restores the observed end-step speed.7,293 nonempty group/time samples match native velocities exactly. This diagnostic repair does not change the production model. It barely changes the substantive failure: seed23 VSL−0.22541 versus actual approximately−0.99, and seed33 spread−0.13879 versus actual approximately+0.63. Adding future average lane-exchange hazards also fails (−0.25457/−0.17420).
4. Future measured off-ramp drainage can make the total look right while component costs are wrong. Seed23 future-speed + future-drainage gives total−1.01891, but predicts off-connector−0.74514 when its actual change is+0.03694. That is error cancellation, **not successful calibration**. Unlimited direct-exit service changes little; it was only an upper-bound diagnostic, never an operational capacity.

Evidence: `flux_moments_v2/assessment.json`, `port_subcells_v1/aggregation_validation.json`, `resolution_oracle_v1/summary.json`, `complete_speed_oracle_v2/`, `combined_speed_exchange_oracle_v1/`, `external_speed_oracle_v3/`.

## The native treatment contrast includes changing interface flows

The exact1s residence identity was independently checked from native vehicle transitions:

`TTT = initial_N * duration + sum((end - entry_time + 1)s) - sum((end - exit_time + 1)s)`.

The scope is **located FW_E mainline + four east on-connectors + four east off-connectors**. Negative source coordinates are outside that located scope. This differs by only a few milliveh·h from the older whole-link totals, but the two conventions must not be silently mixed. All unexplained component transitions are zero. Terminal disappearances are geometrically inferred at the actual final link; they are not proof about every network disappearance.

| 2400–2850s | seed23 VSL100 | seed33 dispersion-only |
|---|---:|---:|
| Actual component ΔTTT [veh·h] |−0.99111|+0.63028|
| Main source admission count difference |+7|+5|
| Main source time-weighted entry contribution |+0.31028|+0.64222|
| Terminal time-weighted exit contribution |−0.53278|+0.56639|
| Initial in-component cohort ΔTTT |−1.00667|+0.01528|
| Later entrant cohort ΔTTT |+0.01556|+0.61500|

**Do not subtract the entry contribution and call the remainder a causal control benefit.** Entries and subsequent exits interact; native admission differences may be endogenous. The source is configured STOCHASTIC, but that alone does not identify the reason for each difference. The original causal plant holds the same forecast admitted-interface flows for candidate arms and cannot exactly reproduce a different realised arrival sequence by fitting a speed coefficient.

Seed33's worsening therefore cannot be used as an unqualified target for a VSL speed-loss coefficient. It includes later-entrant and source-interface effects. This does not establish that VSL is beneficial: mainline terminal timing also worsened.

Evidence: `component_boundary_cohorts_v2/summary.json`, `cohort_timing_summary.json`, each full per-arm result. The trace field `signed_interface_moments` retains weights to the fixed2850s end; it is **not** a prefix-horizon residence identity. The cumulative TTT/cohort fields are actual prefixes.

##10643 drainage is coupled to a short urban road with route failures

Actual geometry:

-10643 enters126 at150.21m;126 is156.72m long.
-10641 then enters71 in lanes2–3, while10700 enterslane1.
-71 is82.60m long. Straight exit10634 useslanes1–3 near81.24m; left exit10635 useslanes4–5 near80.89m; right exit10642 leaveslane1 at37.49m.
- City connector10640 feeds71 lanes4–5. Decision1138 on10640 chooses all three destinations. Some right-bound vehicles must therefore reachlane1 before37.49m; native evidence shows failures, not just a theoretical concern.
- Decision1126 on10643 and1140 on70 both use126→10641→71 for all three destinations. Left-bound cars consequently enter71 inlanes2–3 before needinglanes4–5. Routes are selected earlier, but the physical receiving-lane restriction remains.

The saved network's driving behavior1 has `diffusTm=45`. The error record and1s FZP jointly confirm vehicles disappearing from71 after45s lane-change waiting. A separate vehicle15068 passed its intended10642 turn, reached the end of71, received a `route_next_link_not_found` warning at2048s, and was absent in2049s. This latter warning alone was not labelled removal; the FZP establishes the abnormal loss.

The local audit preserves these losses as separate terms. They are **never counted as signal discharge, off-ramp service or TTD**. Every second of off-stock and urban movement-group conservation reconciles once the explicit abnormal losses are included. SC1004SG2/5 program states agree with native LDP for8,408 samples across the four recordings. Native green time is unchanged across each treatment pair.

|2400–2850s|23 NC|23 VSL|33 NC|33 spread|
|---|---:|---:|---:|---:|
|10643 normal departures|107|112|87|88|
|71 normal departures|201|215|203|191|
|71 abnormal losses|10|6|7|9|
|SG2 green seconds|135|135|135|135|
|SG5 green seconds|72|72|72|72|

The33 counts include respectively one `next_link_not_found` + FZP absence. Seed23 loses2 versus1 vehicles that were **already on10643 at2400** after those vehicles reached71. Their disappearance is outside the current freeway component but changes a coupled downstream queue. "Zero removals inside the component" is therefore insufficient to establish that its receiving boundary is unaffected by deletion.

The past150s10643 discharge is24/25 vehicles; simply extending those observed rates yields72/75 over450s, whereas native NC actually releases107/87. A past throughput proxy is not a physical discharge capacity or a queue-responsive urban boundary.

### What is and is not proved

There is a real response before differential losses: off10643 departure timing first differs at2467→2468s (seed23), while different71 losses first occur at2590→2591s. Seed33's corresponding departure difference is2475→2476s, preceding different losses at2634→2635s. Thus **the gains are not proved to be caused entirely by deletion**.

At2550s, total component contrasts are only−0.02500/−0.00528veh·h. They grow to−0.99111/+0.63028 by2850s, during a period with differing boundary flows and abnormal urban losses. The existing pair cannot uniquely assign all that change to a METANET merge, weaving or anticipation coefficient.

Evidence: `urban_drain_observations_v5/` (4×1,050 current-state/next-flow rows and per-run native proof), `summary.json`; original ERR/FZP retained. Earlier extractorv1–v4 stopped on a missing network path or on the discovered abnormal losses. They are incomplete and superseded byv5.

## Next action, preserving the user's choice of network

A scope question has been sent: use a separate trial network to repair71 destination access, keeping the original network, demands and destination proportions; or keep the current network and explicitly separate normal transport from abnormal-loss effects. **No network modification was made while that choice is pending.**

If a trial network is selected, first trace1138/1126/1140 upstream choices and connector lane access. Preserve origin/time/destination demand exactly and prevent downstream re-selection. Changing a lane-change distance or diffusion timeout alone is not assumed to repair the issue. Validate routes and actual absence of abnormal losses, then repeat the matched-control short test before new gain fitting. Keep the old runs as the historical condition.

If the network is retained, qualify normal response on identified interfaces/windows and model a finite downstream queue/service boundary separately; report the unexplained450s response rather than fitting vehicle deletion into conservation laws. A constant past discharge rate is not an adequate validation surrogate for the shared71 approach.

`diagnostic_validation_v1.json` passes the transport invariants, short-link transition checks, exact speed oracle, native signal checks and cohort residence identities. The previous100 core tests and default12+previous12 exact predictions remain the latest core verification; no new core edit occurred during this diagnostic checkpoint. FullGNE/Ω improvement remains unverified.
