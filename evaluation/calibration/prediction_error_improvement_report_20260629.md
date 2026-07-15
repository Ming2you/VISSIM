# Prediction error improvement report - 2026-06-29

## What changed

The previous Bayesian audit updater treated `prediction_error.predicted` as if it were the raw METANET prediction. That was wrong for completed Vissim runs because `prediction_error.predicted` already used `prediction.calibrated_state_summary` when available.

The updater now estimates scales from:

`observed / source_action_json.prediction.state_summary`

That makes the posterior an absolute scale against the raw one-step prediction, not an extra multiplier on an already calibrated prediction.

## Corrected scale estimate

Source:

- `evaluation/runs/controller_no_wu_pfo_sym_300s_10seeds_20260629`
- 180 decision files
- Scenario: `sym_high`
- Controllers: `no-control`, `wu`, `pfo`

Corrected artifact:

- `evaluation/calibration/prediction_audit_bayes_update_no_wu_pfo_10seed_raw_20260629.json`
- `evaluation/calibration/prediction_audit_bayes_update_no_wu_pfo_10seed_raw_20260629.md`

| target | active v2 scale | corrected posterior | raw median observed/predicted | active calibrated median observed/predicted |
| --- | ---: | ---: | ---: | ---: |
| `freeway_total_veh` | 0.6507 | 0.7770 | 0.7784 | 1.1962 |
| `urban_queue_plus_link_occupancy_total_veh` | 1.0126 | 0.9543 | 0.9502 | 0.9384 |

Interpretation:

- The active v2 freeway audit scale over-corrects downward. Raw METANET over-predicts freeway vehicles, but not enough to justify scaling by 0.6507 in this scenario.
- The active v2 urban queue/storage scale is also too high for this scenario.
- The earlier `1.1908` freeway posterior was not an absolute METANET scale. It was a ratio against the already scaled prediction and is now marked superseded.

## Counterfactual result

Candidate v3 calibration:

- `evaluation/calibration/vissim_network_calibration_v3_prediction_audit_20260629.json`

Counterfactual artifact:

- `evaluation/runs/controller_no_wu_pfo_sym_300s_10seeds_20260629/counterfactual_prediction_error.md`

Component-level result:

| component | active v2 abs error | candidate v3 abs error | change |
| --- | ---: | ---: | ---: |
| freeway total, no-control | 24.883 | 9.226 | -62.9% |
| freeway total, PFO | 22.141 | 10.327 | -53.4% |
| freeway total, Wu | 24.832 | 9.336 | -62.4% |
| urban queue/storage, no-control | 75.801 | 49.333 | -34.9% |
| urban queue/storage, PFO | 38.844 | 33.561 | -13.6% |
| urban queue/storage, Wu | 74.558 | 48.718 | -34.7% |

But aggregate `total_model_vehicles` got worse under v3:

| controller | active v2 total abs error | candidate v3 total abs error | change |
| --- | ---: | ---: | ---: |
| no-control | 58.416 | 68.803 | +17.8% |
| PFO | 32.709 | 37.545 | +14.8% |
| Wu | 57.546 | 67.723 | +17.7% |

This means the aggregate total error is currently benefiting from cancellation between component errors. It should not be used alone as the calibration target.

## Recommendation

1. Stop using `total_model_vehicles` alone as the prediction quality metric.
2. Use component errors at minimum:
   - `freeway_total_veh`
   - `urban_queue_plus_link_occupancy_total_veh`
   - `protected_accumulation_veh`
   - `urban_total_veh`
   - `off_ramp_storage_veh`
3. Treat v3 as a candidate audit calibration, not final controller dynamics.
4. Run held-out validation on:
   - `fw_eb_heavy`
   - `ramp_d_bias`
   - `urban_d_heavy`
5. Only after held-out component errors improve should v3 replace v2 as default.

## Validation assessment

Overall: needs revision before controller-performance claims.

The corrected updater fixes the ratio-basis bug and improves key component errors offline. However, the aggregate total error exposes cancellation, so the next run must validate component-level prediction quality before controller performance is interpreted.

## Held-out validation result

Held-out no-control runs were executed on:

- `fw_eb_heavy`
- `ramp_d_bias`
- `urban_d_heavy`

Artifacts:

- v2 baseline: `evaluation/runs/prediction_holdout_v2_no_control_20260629`
- v3 candidate: `evaluation/runs/prediction_holdout_v3_no_control_20260629`
- component comparison: `evaluation/calibration/prediction_holdout_v2_v3_components_20260629.md`

Result: v3 is not promoted.

| scenario | v2 total abs error | v3 total abs error | result |
| --- | ---: | ---: | --- |
| `ramp_d_bias` | 22.504 | 23.493 | worse |
| `fw_eb_heavy` | 51.864 | 59.452 | worse |
| `urban_d_heavy` | 109.076 | 125.760 | worse |

Interpretation:

- The symmetric-high posterior did not generalize to held-out asymmetric profiles.
- v3 over-corrected freeway vehicle counts upward relative to v2.
- The correct next fix is not another global audit scale. The forecast and state mapping must match the actual Vissim demand profile and route behavior first.

## Forecast-profile fix

Adapter change:

- `evaluation/controllers/vissim_stackelberg_adapter.py`

The one-step model forecast now mirrors the Vissim runner's `DemandVolumeForInput()` multipliers for:

- `fw_eb_heavy`
- `fw_wb_heavy`
- `urban_west_heavy`
- `urban_east_heavy`
- `urban_north_heavy`
- `urban_d_heavy`
- `urban_f_heavy`

Validation run:

- `evaluation/runs/prediction_holdout_v2_profiled_no_control_20260629`
- component comparison: `evaluation/calibration/prediction_holdout_v2_profiled_components_20260629.md`

| scenario | v2 old total abs error | v2 profile-aware total abs error | change |
| --- | ---: | ---: | ---: |
| `ramp_d_bias` | 22.504 | 22.504 | 0.0% |
| `fw_eb_heavy` | 51.864 | 50.569 | -2.5% |
| `urban_d_heavy` | 109.076 | 79.509 | -27.1% |

Key component movement:

| scenario | metric | old abs error | profile-aware abs error | change |
| --- | --- | ---: | ---: | ---: |
| `urban_d_heavy` | `protected_accumulation_veh` | 76.054 | 50.795 | -33.2% |
| `urban_d_heavy` | `urban_queue_plus_link_occupancy_total_veh` | 120.062 | 90.378 | -24.7% |
| `fw_eb_heavy` | `freeway_mean_speed_kph` | 19.147 | 14.210 | -25.8% |

Remaining issue:

- `ramp_d_bias` is unchanged because the Vissim scenario changes static route decisions, not VehicleInput volumes. The model forecast still uses static Numerical-Sim turning/off-ramp splits.
- `protected_accumulation_veh` remains too high in all held-out cases, so urban propagation/state decomposition still needs calibration.

Next calibration target:

1. Add profile-aware route/off-ramp split approximation for `d_ramp_bias` and `f_ramp_bias`.
2. Fit the urban queue/storage decomposition using observed link counts instead of the fixed `internal_storage_fraction=0.35`.
3. Revisit signal service curves only after the forecast/profile mismatch is eliminated.

## Offline urban-dynamics replay

To avoid rerunning Vissim for every model-only hypothesis, saved Vissim `state_*.json` files were replayed through the adapter with a small tuning grid.

Artifacts:

- replay script: `scripts/replay_prediction_tuning_grid.py`
- replay output: `evaluation/runs/prediction_tuning_replay_20260629`
- replay summary: `evaluation/runs/prediction_tuning_replay_20260629/prediction_tuning_replay_summary.md`
- candidate tuning: `evaluation/configs/pfo_h3_i3_prediction_speed110_candidate.json`

Best component-oriented candidate:

| candidate | total abs | protected abs | urban q+storage abs | freeway abs | note |
| --- | ---: | ---: | ---: | ---: | --- |
| base/profile-aware | 42.384 | 50.563 | 50.792 | 14.416 | current v2 + forecast-profile fix |
| `speed90` | 44.281 | 34.917 | 47.801 | 13.994 | better protected, slightly worse total |
| `speed110` | 44.933 | 32.376 | 47.907 | 13.966 | best protected, slightly worse total |

Interpretation:

- Raising `urban_avg_speed_km_h` reduces the excessive predicted protected accumulation and urban link occupancy.
- Pure movement-capacity increases did not help protected accumulation; they made protected error worse in this replay.
- The candidate is not promoted to default because aggregate `total_model_vehicles` worsened by about 6%, but it is useful for controller tests where `N_P` is the state being penalized.

## Route-bias forecast and observation split fit

Adapter/config changes:

- `evaluation/controllers/vissim_stackelberg_adapter.py`
- `evaluation/calibration/vissim_network_calibration_v2_20260628.json`
- fit script: `scripts/fit_observation_split_grid.py`

### Route-bias forecast split

The adapter now mirrors the Vissim route-bias profiles in the forecast ramp-arrival vector:

- `d_ramp_bias` / `d_ramp_heavy`: preserve total ramp demand and assign 98% to `R_D_W` + `R_D_E`.
- `f_ramp_bias` / `f_ramp_heavy`: preserve total ramp demand and assign 98% to `R_F_W` + `R_F_E`.

The 98% value is stored in calibration as:

- `prediction.route_bias_forecast.target_share = 0.98`

Sanity evidence from replayed `d_ramp_bias` action:

| metadata field | value |
| --- | ---: |
| `forecast_ramp_arrival_total_vph` | 1000.0 |
| `forecast_ramp_arrival_R_D_W_vph` | 490.0 |
| `forecast_ramp_arrival_R_D_E_vph` | 490.0 |
| `forecast_ramp_arrival_R_F_W_vph` | 10.0 |
| `forecast_ramp_arrival_R_F_E_vph` | 10.0 |

### Observation-based queue/storage split

The previous local-observation split used:

- `internal_storage_fraction = 0.35`
- `offramp_storage_fraction = 0.50`

Saved Vissim `state_*.json` files were replayed through the adapter with candidate split values. The refined grid artifact is:

- `evaluation/runs/observation_split_grid_refined_20260629/observation_split_grid_summary.md`

Promoted split:

- `internal_storage_fraction = 0.90`
- `offramp_storage_fraction = 0.20`

Overall held-out replay, all three saved no-control profiles:

| configuration | total abs | protected abs | urban q+storage abs | urban storage abs | movement queue abs | freeway abs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| old/base split `0.35/0.50` | 42.367 | 50.559 | 50.772 | 110.681 | 105.743 | 14.414 |
| promoted split `0.90/0.20` | 48.530 | 49.343 | 53.073 | 58.192 | 63.585 | 14.370 |

`ramp_d_bias` subset:

| configuration | total abs | protected abs | urban q+storage abs | freeway abs |
| --- | ---: | ---: | ---: | ---: |
| old/base split `0.35/0.50` | 18.702 | 60.856 | 29.300 | 18.616 |
| promoted split `0.90/0.20` | 22.992 | 46.592 | 20.911 | 17.923 |

Interpretation:

- The promoted split improves the queue/storage decomposition metrics that were the fit target.
- It does not improve aggregate total vehicle mass; in fact total abs error worsens on this held-out replay.
- Therefore this promotion should be read as a local-observation decomposition calibration, not as a full METANET mass/propagation calibration.
- The next controller validation should track total mass error separately from `N_P`, urban storage, and movement-queue errors.
