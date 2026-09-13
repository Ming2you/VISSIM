# Route choice corridor1129 — canonical hooks for root

Module: `evaluation/controllers/route_choice_corridor.py`. Evidence: `diagnostics/route_choice_corridor_ver2.json`. Focused tests: `python -m unittest diagnostics.test_route_choice_corridor -v` (11 PASS, actual1350 projection/ledger plus independent copies and fresh spawned process).

Flag, absent = untouched:

```json
"urban": {"route_choice_corridor": {
  "evidence_path": "diagnostics/route_choice_corridor_ver2.json",
  "unknown_policy": "error"
}}
```

`hold_diagnostic` is the other explicitly accepted policy. It retains unobserved post-choice cohorts without assigning a posterior. Metadata `route_choice_held_unknown_route_veh>0` and `route_choice_prediction_route_complete=0` must invalidate claims of complete traffic prediction. Actual historical1350 has4 prefix vehicles and1 local57 vehicle with missing route; its counted stock and zero initial events are exact, but that local vehicle is held in diagnostic mode. The root's optional current-route collector allows error-mode initialization with observed1129:2/3 on57 and observed1129:1/2/3 after56@253.172. Module uses canonical `complete_vehicle_routes`; JSONnull remains unobserved.

## Runtime setup

After `shared_approach.configure` and before `projection_support.configure`:

```python
if tuning.get('urban', {}).get('route_choice_corridor') is not None:
    from evaluation.controllers import route_choice_corridor
    detector_mapping, extra = route_choice_corridor.configure(
        cfg, tuning, state_json, detector_mapping,
        per_lane_capacity_veh_h=metadata['movement_capacity_by_lanes_per_lane_veh_h'])
    metadata.update(extra)
    detector_mapping, state_json, extra = route_choice_corridor.prepare_projection(
        cfg, detector_mapping, state_json)
    metadata.update(extra)
```

This captures the existing normalized per-lane scalar, not a new tuning constant. W/offE/offW share one10634 three-lane budget; N uses10627 one lane; S uses10632 one lane and no selected signal gate because its connector leaves before SG8. Source receipts consume a budget once, after the actual accepted quantity is known.

Hubble already added verified claim validation to`projection_support.configure`. The claim includes the exact cfg/evidence partition, raw physical counts, singleton origins, transit marker and absence of movement projection. It is not a global exemption of unresolved links.

After physical state creation, conservative initial transit pairing, shared69/SC2001 initialization, and before area seed:

```python
if getattr(cfg.network, 'route_choice_corridor', None):
    metadata.update(route_choice_corridor.initialize(state, cfg, state_json, detector_mapping))
    metadata.update(urban_flow_accounting.install(a, cfg))
```

Worker setup installs the accounted urban body but never reinitializes the corridor. Native`TrafficState.copy()` deep-copies its cohorts and budgets. A standalone physics-enabled/Ω-disabled configuration must select the accounted body too.

## Urban body hooks

1. `urban_substep_accounted`: after `ensure_urban_state`, **before** `shared_approach.advance`, invoke:

```python
choice = getattr(cfg.network, 'route_choice_corridor', None)
choice_meta = {}
if choice:
    from evaluation.controllers import route_choice_corridor
    choice_meta = route_choice_corridor.advance(
        state, control, demand, cfg,
        _uqm._urban_step_index(state, cfg) if urban_step_index is None else urban_step_index)
```

Merge numeric/string validity metadata and accepted-flow diagnostics into the returned diagnostics after its dictionary exists. Both ordinary source receipts and shared69 branch2 receipts require the same explicit step's advance first.

2. `_receive_corridor`: try `route_choice_corridor.receive_accepted(...)` before SC2001 dispatch. True means caller already changed the source and destination stocks, and the module reserved only its private travel. Keep the two existing `_receive_corridor` call sites in the off drain and ordinary actual-departure branch; their generic arrival/release scheduling is skipped on True.

3. **Before** the off drain's receiving-space minimum, just after its current `intended=min(beta*occupancy,dt*green*cap)`:

```python
choice_intended = route_choice_corridor.intended_departure(
    state, control, cfg, movement, beta * occupancy, step_idx)
if choice_intended is not None:
    intended = choice_intended
```

Guard the import/call on the corridor flag or import the module once; disabled helper returns None.

4. **Before** ordinary movements enter `intended_by_storage`, just after current `intended=min(available,dt*green*cap)`, use the same helper with `available` instead of`beta*occupancy`. In the subsequent`for storage_link, intended in intended_by_storage.items()` loop, run`intended = route_choice_corridor.limit_intended_batch(state, cfg, intended, step_idx)` immediately before the existing receiving allocator. This batch cap shares the remaining physical-connector service among simultaneously computed requests using the configured receiving rule; scalar intended queries alone cannot prevent two sources reserving the same service. The existing receiving allocator then limits actual quantities against the one shared prefix storage. OffE/offW drain first and debit accepted10634 service; the later ordinary W request sees only the remaining physical budget. N/S are different physical connectors. Rejecting after acceptance would be too late; receipt asserts no overbooking.

5. Exclude `set(choice['capacity_veh'])` (prefix and local stores) from generic storage-release, generic arrival, and sink loops. Typed local2/3 arrival is performed by the module as one storage→the specified SC1005 movement queue transfer. No generic0.9/0.1 draw occurs for those same vehicles. The old local source remains a queue origin for normal signal service.

6. `urban_flow_accounting.install` enabled/body dispatch must include `cfg.network.route_choice_corridor`, even with Ω disabled. Its end-of-step residence loop already counts every storage; the new cohort bins are annotations on that storage, not additional physical inventory.

## Shared69 continuation hook

Native1134:2 ends on75@67.103.75 has no signal, no independent input, and exactly one outgoing10701→56@249.407,3.765m before decision1129. Configure validates this continuation, changes shared69 branch2's target from`in_SC1005_W` to the new prefix, and projects10636/75/10701 into it. No new external demand is created.

In`shared_approach.advance`, inside the urban-target accepted branch **after** `state.urban_link_storage[target] -= accepted`, call:

```python
handled = route_choice_corridor.receive_shared_accepted(
    state, cfg, source, key, accepted, urban_step_index)
if not handled:
    # existing target routing membership assertion and generic arrival/release schedule
emit_transfer(state, cfg, 'storage:' + source, 'storage:' + target,
              accepted, preserve_area=True)
```

Receipt does not emit another ledger event. It checks that accepted physical transfer happened exactly once and reserves geometry-based travel from10636 entry to1129. This avoids applying SC1005's phase before reaching the1129 split. The old `in_SC1005_W` gate has no identified independent native source; the module fails explicitly if a forecast nevertheless provides positive external demand there. It never silently drops such a demand.

## Area routes and removed aliases

Configure coalesces each source's two east destination aliases, retaining the`...to_E_SC1005` key but changing its receiver to the shared prefix and summing only beta. The`...to_E_SC107` alias is removed. `area_dynamic_routes.extend_routes` must skip a document movement only when it is in the active corridor's explicit`renames` mapping; otherwise keep its existing strict behavior. Those removed aliases' old full bypass contracts no longer own the later branch transfer.

After area configuration has created`cfg.network.control_area_routes`, call `route_choice_corridor.extend_area_routes(cfg)` (as with SC2001). It replaces kept incoming paths by their actual source→connector→56 membership and removes obsolete alias contracts. Every outgoing shared-prefix/local/bypass transition is internal toΩ and calls preserve_area once; downstream normal movement crossings retain their own existing contracts.

## Integration checks still required

Focused tests pass actual raw1350 inventory, initial event0, inherited beta sum and typed branch behavior, receiving rejection with original stock retained, current-route preservation, two source receipts sharing one physical budget, shared69 source continuation, duplicate receipt rejection, and fresh-process copy equivalence. Root must still run the canonical fully hooked urban body for150/450s, ensure dynamic route installation skips only explicitly coalesced aliases, and validate full main/worker action output. Historical raw900/1350 lacks route capture; use explicit`hold_diagnostic` only for those diagnostics, and report its validity flag. Live config should use`error` plus the qualified collector.

The inherited per-lane service scalar is a prediction calibration, not a newly measured physical capacity. Existing SC1005 through/left phase authority and downstream receiver delay remain separate model fidelity questions; preserving a current route tag does not prove every downstream phase association correct.
