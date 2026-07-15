# Route-bias forecast ON(0.98) vs OFF — held-out no-control evidence replay

Same repo-root (new clone) and states; only `prediction.route_bias_forecast.enabled` differs.

Values = mean one-step abs error over chained held-out decisions (n in parens). Negative delta(ON-OFF) means the 0.98 route-bias forecast REDUCES error.

| scenario | metric | OFF | ON(0.98) | delta(ON-OFF) | delta% | n |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| d_ramp_bias | freeway_total_veh | 20.726 | 20.711 | -0.014 | -0.1% | 5 |
| d_ramp_bias | protected_accumulation_veh | 55.988 | 55.975 | -0.013 | -0.0% | 5 |
| d_ramp_bias | urban_queue_plus_link_occupancy_total_veh | 25.186 | 25.115 | -0.071 | -0.3% | 5 |
| d_ramp_bias | total_model_vehicles | 27.672 | 26.869 | -0.803 | -2.9% | 5 |
| f_ramp_bias | freeway_total_veh | 19.535 | 19.828 | +0.293 | +1.5% | 20 |
| f_ramp_bias | protected_accumulation_veh | 143.093 | 142.198 | -0.894 | -0.6% | 20 |
| f_ramp_bias | urban_queue_plus_link_occupancy_total_veh | 129.699 | 131.310 | +1.611 | +1.2% | 20 |
| f_ramp_bias | total_model_vehicles | 99.073 | 100.181 | +1.109 | +1.1% | 20 |

## Interpretation (audit follow-up B2)

- route_bias ON(0.98) produces NO meaningful component-error improvement on d_ramp_bias
  (freeway -0.1%, protected -0.0%, urban q+storage -0.3%); only total_model_vehicles moves
  (-2.9%), which calibration explicitly says must not be optimized alone.
- On f_ramp_bias the forecast is net WORSE: freeway +1.5%, urban q+storage +1.2%, total +1.1%.
- This empirically confirms the conceptual mis-channeling. VISSIM d/f_ramp_bias sets
  RelFlow(1)=100/0.01 across ALL static routing decisions (run_stackelberg_vissim_controller.vbs
  ApplyRouteBias), leaving VehicleInput volumes unchanged; the actual effect is a global route
  split (which on-ramp + which freeway direction + which urban turns vehicles take). The adapter
  instead redistributes on-ramp arrival while preserving a hardcoded total (ramp_vph 250 x 4 ramps)
  and keeps urban turn/off-ramp splits and freeway-direction loading static.
- Verdict: KEEP route_bias_forecast demoted (candidate_pending_holdout_evidence). Do NOT
  re-promote on this evidence. A correct redefinition is required before re-promotion:
  (a) base the redistribution on the re-routed urban-origin demand (allow total on-ramp inflow
  to change), (b) couple d_ramp_bias -> FW_WB / f_ramp_bias -> FW_EB freeway-direction loading,
  (c) shift the urban movement/off-ramp split for routes traversing link 25 / 31. Re-promote only
  if held-out component errors (freeway_total, protected, urban q+storage) improve.
