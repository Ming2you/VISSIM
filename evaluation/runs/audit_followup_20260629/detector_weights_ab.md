# Detector weights A/B: assumed (0.5/0.25/0.25) vs route-derived

Held-out no-control; only --detector-mapping-json differs. Lower abs error better. Negative delta = route weights reduce error.

| scenario | metric | assumed | route | delta | delta% |
| --- | --- | ---: | ---: | ---: | ---: |
| fw_eb_heavy | urban_movement_queue_total_veh | 46.668 | 45.828 | -0.840 | -1.8% |
| fw_eb_heavy | urban_link_occupancy_total_veh | 72.776 | 79.208 | +6.432 | +8.8% |
| fw_eb_heavy | urban_queue_plus_link_occupancy_total_veh | 67.340 | 71.369 | +4.028 | +6.0% |
| fw_eb_heavy | total_model_vehicles | 61.085 | 64.853 | +3.768 | +6.2% |
| ramp_d_bias | urban_movement_queue_total_veh | 109.531 | 102.071 | -7.460 | -6.8% |
| ramp_d_bias | urban_link_occupancy_total_veh | 81.454 | 86.377 | +4.922 | +6.0% |
| ramp_d_bias | urban_queue_plus_link_occupancy_total_veh | 25.115 | 28.045 | +2.930 | +11.7% |
| ramp_d_bias | total_model_vehicles | 26.869 | 30.483 | +3.614 | +13.5% |
| urban_d_heavy | urban_movement_queue_total_veh | 72.705 | 74.209 | +1.504 | +2.1% |
| urban_d_heavy | urban_link_occupancy_total_veh | 58.879 | 62.063 | +3.183 | +5.4% |
| urban_d_heavy | urban_queue_plus_link_occupancy_total_veh | 99.901 | 105.425 | +5.524 | +5.5% |
| urban_d_heavy | total_model_vehicles | 88.425 | 94.048 | +5.623 | +6.4% |

## Interpretation (G2 urban calibration)

- Route-derived detector weights modestly improve the urban movement-queue decomposition (the
  direct target: -6.8% ramp_d, -1.8% fw_eb) but WORSEN urban link-occupancy, combined queue+storage,
  and total mass on every scenario (+5..+13%).
- Reason: the detector weights only change how OBSERVED VISSIM link counts are decomposed into model
  movements. The model PREDICTION still uses the model-internal urban turning ratios (cfg.network,
  from the Numerical-Sim repo default.yaml / grid_topology), which remain uniform-ish. Making the
  OBSERVED decomposition physically correct (route-based) therefore moves it away from the unchanged
  model prediction -> net worse on most components. Same failure mode as the observation-split and
  route-bias adapter knobs.

## Verdict / next step

- Do NOT apply the route-derived detector weights alone; on their own they do not help.
- The turn-split DIAGNOSIS is nonetheless correct and important (evaluation/runs/audit_followup_20260629/
  urban_turn_split_diag.md): the assumed 0.5/0.25/0.25 weights are demonstrably wrong vs the actual
  static routing (e.g., A_N_to_E 0.25->0.66, E_W_to_E 0.50->0.89, on-ramp shares re-balanced).
- The real lever is the MODEL urban turning/off-ramp split ratios in the Numerical-Sim repo
  (src/config/default.yaml / src/models/grid_topology.py), aligned to the route-derived values, with
  the detector weights updated to match for consistency. This is a model-side (repo) change and should
  be coordinated with the model owner / committed upstream, then re-validated on held-out no-control.
