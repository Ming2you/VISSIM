# Physical turn → merged movement join

`control_area_join.py` joins the final635-link Ω partition to the **actual n7 runtime-merged371 movements**. No production event/objective hook is installed here. The exported `control_area_route_contract.json` is ready for the explicit cohort event API.

The join uses canonical PN306 turn triplets, runtime stopline/approach support, actual receiver storage support, and physical destination paths up to the first supported storage. A compass-only match was rejected as insufficient: curved exits at SC11/SC101 made real turns appear missing. Destination storage support resolves those cases, and the recorded path makes the inference reviewable. Every canonical connector endpoint was checked against the pinned Ver2 INPX.

Results: **unique281, same-transition2, mixed-transition1, no-match87**. All triplets retain connector membership, so an inside→outside→inside path records both an exit and an entry. No equal branch weights are inferred. The route contract also supplies `arrival:<movement>` with the physical stopline side; transporting mixed origin cohorts to that stopline requires an explicit model approximation.

## Actual accepted flow coverage

A diagnostic Python line observer read `actual=min(before,departed)` from the unchanged vendor during one5-second urban step on a copied state with its actual previous action and observed demand. It did not read intended flow, infer departure from net stock change, or modify the simulator.

| State | Joined accepted flow | Unresolved positive flow |
|---|---:|---:|
| NC900 |51.953111veh|.536848veh|
| n73300 |59.700850veh|2.008212veh|

Unresolved positive movements at n73300:

- SC101_N_SC2005_to_W_SC1002 (.532929veh): no supported physical turn from this approach reaches the configured receiver. Its physical choices are exported for a movement/topology correction.
- SC107_N_SC1_to_W_SC1004 (.5), SC107_S_to_W_SC1004 (.114739), SC107_S_to_N_SC1 (.229478), SC107_N_SC1_to_S (.229478), SC107_S_to_E_SC108 (.114739): physical source/receiver routing requires reconciliation. For example10618 reaches SC107_to_SC1005, while the model names SC107_to_SC1004;10610 lands on385 supported by SC1005_to_SC1004/SC107_to_SC1005, while the model names SC107_S_out. These cannot be classified by the word `out`.
- SC1004_S_to_E_SC107 (.286848): actual10632→56 belongs to SC1004_to_SC1005; the model points at SC1004_to_SC107. A multi-node physical route or receiver correction is needed.

One unresolved mixed movement has zero accepted flow in these two particular5-second probes: **SC107_W_SC1005_to_E_SC108** may match10023 (inside→inside) or10616 (inside→outside). It needs an accepted branch split, a verified route mapping, or separate movement representation. Zero now is not a coverage guarantee for future candidates.

Missing positive flow must remain a coverage error. Do not assign zero TTD or outside by default, and do not switch objective definitions between candidates. Direct freeway/off-ramp arrivals, ramp transfers, external sinks, and storage→movement maturation are separate event sites; this join alone does not cover them.

Artifacts: `control_area_movement_join.json`, `control_area_route_contract.json`, `control_area_movement_flow_coverage.json`. The latter preserves every actual accepted movement plus unresolved source-approach physical choices. Reproduce with `python diagnostics/probe_control_area_movement_join.py`. Seven mapping regressions pass, including shared transitions, mixed routes, connector excursions, curved exits, bridge traversal, missing membership, and arrival side.
