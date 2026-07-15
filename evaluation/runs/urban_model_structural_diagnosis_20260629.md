# Urban model structural diagnosis (2026-06-29)

Goal: localize WHERE the urban_queue_model (src/models/urban_queue_model.py) structurally diverges from
VISSIM, given that controller performance is model-fidelity limited (horizon 1->3 made PFO worse).

## What the model is

A Wu-style movement-level horizontal queue model (`urban_substep`, line 757). State = per-movement
queues `urban_movement_queue` + per-link storage `urban_link_storage`. Mechanics:
- boundary/on-ramp demand arrives and is split into movement queues by turning ratios beta (`routing`).
- each movement discharges min(queue, green_fraction x cap_flow x dt); `_phase_green_fraction` (line 499)
  IS offset-aware (substep overlap with the green window).
- discharge is gated by downstream receiving space `_effective_available_space` (spillback).
- discharged vehicles travel to the next node after `_link_delay_steps` (line 476), an INTEGER number
  of 5 s substeps based on available link space and `urban_avg_speed_km_h`.
- finite boundary-out exit capacity gates departures from the system.

## Empirical localization (signed residual, obs - pred, 124 no-control decisions)

| metric | mean(obs - pred) | reading |
| --- | ---: | --- |
| urban_total_veh | -99.5 | model holds ~100 MORE urban vehicles than VISSIM |
| protected_accumulation_veh | -148.9 | model over-predicts protected accumulation by ~149 |
| urban_link_occupancy_total_veh | -148.7 | too many vehicles in mid-link storage |
| urban_movement_queue_total_veh | +45.5 | too few at the signal stop-lines |
| boundary_queue_total_veh | +41.3 | too few at the boundary |
| freeway_total_veh | +20.1 | slightly too few on the freeway |

Robust (decomposition-independent) signal: the model OVER-ACCUMULATES urban vehicles
(urban_total -99, protected -149). The storage-vs-queue split (-149 / +45) is partly confounded by the
observation split, but its direction is consistent with the totals.

## Structural root causes

1. **Over-accumulation / too-slow discharge through the network.** The model retains ~100-150 more
   urban vehicles than VISSIM and over-predicts protected accumulation. The real network moves/discharges
   vehicles faster than the meso model. Candidates: link-transit delay too long (holds vehicles in
   `urban_link_storage` instead of letting them reach the stop-line), de-platooned service, and
   saturation/exit throughput lower than VISSIM's effective discharge.
2. **Vehicles held in the wrong place.** Too many in mid-link storage, too few in movement (stop-line)
   queues and boundary queues. The available-space-based, integer-5s-quantized `_link_delay_steps` plus
   `urban_avg_speed_km_h=50` over-estimates transit time, parking vehicles in link storage. (Consistent
   with the joint-calibration finding that raising urban_avg_speed to the grid edge helped link occupancy.)
3. **De-platooned arrivals defeat offset/coordination control.** Although `_phase_green_fraction` models
   offset, arrivals are smoothed through the delay buffers + proportional beta split, so there are no
   platoons to align with green. In VISSIM, signal offset/coordination shapes platoons and matters a lot.
   The urban followers optimize green/offset against a model where coordination has little faithful
   effect, so their signal decisions do not translate to VISSIM benefit (and compound badly at horizon 3).
4. **Mean-field, mis-calibrated turning** (beta proportional split, uniform 0.5/0.25/0.25 default vs the
   route-derived truth) further mis-distributes flow across movements/links.

## Why this explains the controller failure

The controllers minimize the model's predicted queues. The model presents a PHANTOM over-accumulated,
mis-distributed urban state (too many vehicles, parked in link storage rather than at stop-lines, with
de-platooned arrivals). Optimizing signal timing/offsets against that phantom state does not help the
real VISSIM network, and a longer horizon (h3) compounds the divergence -> actively harmful.

## Concrete structural fix directions (repo-side, urban_queue_model.py)

1. Re-derive the link-transit delay so mid-link storage does not over-fill: validate `_link_delay_steps`
   and `urban_avg_speed_km_h` against VISSIM link travel times (the low-demand free-flow run gives clean
   travel-time data). Likely raise effective urban speed / shorten transit, moving vehicles to stop-lines.
2. Calibrate effective discharge/exit throughput (saturation flow, boundary_out_capacity) so total urban
   accumulation matches VISSIM (currently +100..150 too high).
3. Introduce arrival platooning (or a coordination-aware service term) so signal offset has a faithful
   effect; otherwise drop offset from the controller's decision space in the VISSIM integration.
4. Adopt route-derived turning_ratios (already available; inject via network.turning_ratios) so flow is
   distributed to the correct movements before any of the above is re-fit.

These are MODEL-STRUCTURE/representation changes in the Numerical-Sim repo, validated against the
low-demand free-flow VISSIM run first (clean regime), then mid/high. Parameter-only tuning has been shown
to hit a ceiling (urban_joint_calib.md).
