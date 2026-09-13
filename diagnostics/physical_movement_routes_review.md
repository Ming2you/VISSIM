# Physical movement routing repair — Ver2

The two audited five-second steps now have no positive unresolved movement departure. This is **not** full-horizon coverage: 75 inactive movement paths remain unresolved, and arrival-at-stopline membership must be validated independently of departure-path membership.

## Evidence and results

All paths are verified against `network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx`, SHA256 `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`. `physical_movement_routes_ver2.json` cites actual static decision/route IDs for every edge; `load_evidence()` verifies connectivity, cited native routes, all vehicle types, static routing, and the single interval beginning at zero. No future observations or equal weighting of unknown paths are used.

| Model state | Unresolved accepted flow before | After physical path joins | After topology repair | Projection total-stock change |
|---|---:|---:|---:|---:|
| NC seed13,900 sec |0.536848 veh|0|0|0|
| n7 seed13,3300 sec |2.008212 veh|0.229478 veh|0|0|

The final accepted total changes from61.709062 to61.364844veh at3300 because the incorrect initial queue and phantom service are removed. This is a changed model prediction, not evidence of better VISSIM performance. Full output is `physical_movement_route_replay.json`.

The relevant physical findings are:

- SC101 north→west uses channelized right314→10504→316 (native1013:3), before the canonical1220016001 stopline. This is an outside→inside crossing.
- SC107 south→east uses378→10608→383 (native1064:3), before the left-only382 stopline. This is outside→inside.
- SC1004→SC107 and SC107→SC1004 are distinct real bypasses10621 and10501, proven by native1129:1 and1128:2. They must not be merged into surface SC1005 receivers. Full compound paths resolve the earlier detector-receiver mismatch.
- SC107 west through10023 and right10616 have different Ω transitions. Native1061:2 versus1061:3 disambiguates them even though the old geometric compass labels both east. The first remains inside; the right exits.
- SC107 north through is the actual tunnel branch1220006803→10597→1220006801 (native1063:2), which exits Ω. The old canonical turn10610 is a right turn, not this through route. Charging its crossing at modeled signal service is temporally aggregated; the tunnel branch itself bypasses the signal.
- **SC107 south→north is impossible from physical input379.** Its reachable graph has only the left/right paths, and native1064 has left279/right202 with no through route. Northbound tunnel traffic originates on independent input1220042300, already mapped to `in_SC1_S`.

## Optional repair and projection

`urban.movements.physical_route_topology = "diagnostics/physical_movement_routes_ver2.json"` enables `configure_topology_repair()`; absence returns the identical detector object and empty metadata without changes. Integrate this function after merged movement/capacity configuration and **before** `traffic_state_from_vissim()`. Reproject the original physical snapshot; do not delete an existing queue from a projected state.

The south approach's new beta uses native1064's279/481 left and202/481 right. Left continuation to SC1004 versus SC1005 uses native1128's two empty relFlow values, each defaulting to1; this is an explicit conditional static prior, not measured truth. The beta sum is1. The downstream decision is applied after the turn and can have a congestion-dependent realized split.

At3300 the physical link382 contains four queue vehicles, but the old detector projected one into each N/E/W1004/W1005 movement. Link382 is already past the right branch and can only turn left. The repaired detector projects two into each permitted west continuation; all four vehicles remain. The phantom movement and its capacity/rename aliases are removed. Vendor identity caches for this changed network are explicitly invalidated; other networks' cached movement specs are preserved.

The source hash is also checked against the snapshot's **referenced provenance manifest**, including matching run ID. `offramp_routing.py` now uses this same actual manifest reader; its earlier inline-files assumption would have rejected real snapshots when enabling that optional prior.

## Contracts and remaining coverage

`control_area_movement_join_physical_routes.json` contains293 unique,2 same-transition,75 unresolved movement paths and no mixed transition. `control_area_route_contract_physical_routes.json` retains movement/arrival keys plus input:gate/input:ramp keys. The input contract validates21 actual mapped input locations,4 ramp receiving memberships, and leaves18 generated gate origins without matching native input unresolved. Ten actual internal urban inputs and shared-stem input1101 are explicitly listed as unmodeled injections.

Names beginning `in_` do not determine Ω membership: `in_SC1001_W` generates on inside link32; `in_SC107_S` generates on outside379. Ramp receiving connectors are inside, but no independent native vehicle inputs lie on them; their configured exogenous ramp arrival remains a modeled injection, not proof of an external network-entry crossing.

Arrival-source membership can be proven even when a departure destination is unresolved. The current contract intentionally does not silently make those two claims equivalent; full-horizon consumers must extend source-only joins where supported and fail if future positive unresolved transfers arise. The full spatial paths remain temporally aggregated at model service; removing the signal effect from the tunnel bypass requires a separate physically routed travel model.

Validation:11 physical-route tests pass, including actual900/3300 replay, mass-preserving projection, native beta closure, stale-cache eviction, wrong-route rejection, optional-off identity, manifest matching, and input classification. The7 existing join tests and4 optional offramp-prior tests also pass. No adapter, VBS, or vendor source was changed by this subtask.
