# Calibration independent review — 2026-09-16

## Verdict

The physical geometry and autonomous off-ramp stock bookkeeping are useful corrections, but this fit has **not resolved the east bottleneck prediction or demonstrated correct VSL/RM response direction**. West speed and density improve in both seeds; west flow and total residence do not improve consistently. Do not promote this fit to the full controller on the strength of its normalized training objective.

This is a read-only review of completed JSON/CSV-derived evidence and the scoring/boundary code. No native run, FZP scan, parameter search, canonical source edit, or process intervention was performed. Only this review document was created.

## What was actually compared

- 2 seeds × 4 model variants × 2 boundary modes × 18 cutoffs × 2 directions = 576 scored road windows, each 450 s. The output records no failed or invalid windows; maximum recorded freeway continuity residual is 5.685e-14 vehicles. This establishes numerical bookkeeping in this component experiment, not predictive adequacy.
- Fair coefficient comparison: `aligned_dynamic_reference` versus `aligned_dynamic_refit`, with the same physical grid, off-ramp dynamics and boundary inputs.
- `conditioned_diagnostic` uses future realized source admissions, ramp merges, route shares and off-ramp drainage. Its accuracy is conditional reproduction, **not an online forecast**.
- `history_forecast` uses the previous 150 s interface flows/shares and drain rates, together with the known source-demand schedule. Current code does not read post-cutoff realized traffic for this mode. Ramp merges remain exogenous; the experiment contains no RM/VSL interventions.
- Seed13 travel estimates use completed passages across its full 9000 s. Seed13 temporal checks are descriptive. Seed17 was not used in this fit, but was previously inspected under an earlier model; it is development validation, not a fresh independent holdout.

## Same-grid coefficient comparison

Each cell contains reference → refit. Density is veh/km/lane, speed km/h, total cell outflow veh/h, and TTT is mean absolute **freeway-only** 450 s residence error in veh·h. The TTT metric excludes urban and ramp waiting.

| Seed | Boundary | Road | Density RMSE | Speed RMSE | Flow RMSE | TTT MAE |
|---|---|---|---:|---:|---:|---:|
| 13 | conditioned | FW_E | 9.52 → 9.60 | 20.13 → 19.73 | 1087.60 → 1051.49 | 1.212 → 1.505 |
| 13 | conditioned | FW_W | 8.65 → 4.52 | 21.71 → 19.02 | 893.82 → 868.55 | 2.595 → 4.172 |
| 13 | history | FW_E | 9.73 → 9.81 | 20.34 → 19.97 | 1084.73 → 1057.01 | 3.396 → 3.307 |
| 13 | history | FW_W | 8.71 → 5.45 | 22.12 → 19.64 | 925.26 → 894.19 | 4.239 → 5.226 |
| 17 | conditioned | FW_E | 8.68 → 8.66 | 19.50 → 18.98 | 1036.05 → 991.73 | 1.203 → 1.657 |
| 17 | conditioned | FW_W | 8.50 → 6.25 | 21.20 → 19.21 | 925.27 → 952.28 | 2.794 → 4.501 |
| 17 | history | FW_E | 8.78 → 8.77 | 19.62 → 19.11 | 1058.78 → 1017.89 | 3.890 → 4.241 |
| 17 | history | FW_W | 8.62 → 7.30 | 21.80 → 20.00 | 953.44 → 982.57 | 3.902 → 4.878 |

The seed17 history result is the most relevant development check: east speed improves only 19.62 → 19.11 km/h and flow 1058.78 → 1017.89 veh/h, while east TTT error worsens 3.890 → 4.241 veh·h. West speed improves 21.80 → 20.00 km/h, but flow worsens 953.44 → 982.57 veh/h and TTT 3.902 → 4.878 veh·h. Lower density RMSE does not establish better cost prediction.

**East low-speed failure persists:** on the aligned grid, E14 has sustained low-speed evidence in 6 seed13 and 7 seed17 windows. Every one is missed both before and after the coefficient fit, in both boundary modes. This diagnostic means 5 consecutive 30 s samples with N ≥ 5 and speed < 30 km/h. It is the first sustained interval within each 450 s window, not necessarily first network breakdown; some windows begin already congested. The original grid has 10/12 such windows because its E14 covers another physical interval. The change from 10/12 to 6/7 is **not improved onset prediction**.

## Off-ramp stock and drainage

Values are reference → refit RMSE. Storage has four separate connector samples per direction per 30 s. Drain rate errors compare predicted physical connector exits with realized exits.

| Seed | Boundary | Road | Stock RMSE [veh] | Drain RMSE [veh/h] |
|---|---|---|---:|---:|
| 13 | conditioned | FW_E | 9.38 → 7.69 | 110.87 → 115.70 |
| 13 | conditioned | FW_W | 6.55 → 4.75 | 164.91 → 188.60 |
| 13 | history | FW_E | 14.76 → 13.69 | 419.30 → 419.63 |
| 13 | history | FW_W | 7.19 → 5.79 | 387.90 → 391.12 |
| 17 | conditioned | FW_E | 8.41 → 6.58 | 113.13 → 118.58 |
| 17 | conditioned | FW_W | 6.68 → 4.98 | 178.34 → 211.62 |
| 17 | history | FW_E | 12.45 → 11.20 | 407.62 → 407.49 |
| 17 | history | FW_W | 7.69 → 6.35 | 407.43 → 412.92 |

- Storage errors decrease, but drainage does not generally improve. Seed17 refit history stock biases remain +5.13 east / +3.54 west vehicles per sampled port; drain biases are −45.95 / −102.36 veh/h. Stock agreement is not enough to claim correct release timing.
- Conditioned drainage is constrained by realized future departures offered as a service proxy. Predicted departures cannot exceed that offered amount and may be lower when model vehicles are not yet available. Accordingly all conditioned drain errors have negative bias. The near-perfect use of future service is not a validated signal-capacity forecast.
- History drainage RMSE remains around 407–413 veh/h on seed17. The previous-150-s constant proxy omits future signal phase, platoon and receiving effects; do not credit or blame all of this error to METANET coefficients.
- Off-ramp stock is propagated by accepted entry minus physical drain with travel cohorts and finite space; it is no longer externally reset throughout the horizon. That is a substantive bookkeeping improvement even where RMSE does not improve. Strong spillback/capacity identification still requires conditions that actually load the relevant storage/exit lane.

## Coefficients and identifiability

| Direction | τ [s] | ν | κ | Merge δ | Lane-drop φ |
|---|---:|---:|---:|---:|---:|
| East | 12 (lower bound) | 47.4 | 17 | 1 (upper bound) | 6 (upper bound) |
| West | 12 (lower bound) | 12.6 | 120 (upper bound) | 0 (lower bound) | 3 |

The bounded coordinate search used 46 east and 58 west evaluations, beginning at the prior fit. Training normalized MSE sum changes east 3.0347 → 2.9303 and west 2.6994 → 1.8775. Temporal descriptive scores change east 3.1700 → 3.0700 and west 2.7509 → 1.8461. These values optimize density/speed/total-flow error, not TTT differences or intervention ranking.

Boundary solutions plus a short single-start search provide no unique physical identification. East δ = 1 and φ = 6 are pressure against the selected bounds, not proof of those mechanisms’ true magnitudes; west δ = 0 does not demonstrate that real merges have zero impact. West φ is not materially identifiable from a road with a lane increase rather than the east lane reduction. Do not expand bounds simply to obtain a more dramatic control benefit.

## Metric and provenance limitations to fix or disclose

1. `off_flow_vph` is a **cell aggregate**, not a per-connector metric. The aligned west grid places 10491/10479 together in cell 6 and 10638/10645 together in cell 11 (zero-based). Its off-flow error count is therefore 540 rather than the original-grid 1080. West original/aligned off-flow RMSE cannot be directly interpreted as improved or worse connector accuracy. Dynamic stock/drain metrics still use all four separate connectors.
2. `e14_discharge` and the summary E14 onset key are hard-coded to cell 13. The existing grid warning correctly prevents same-location claims across grids; future reports should use physical station ranges or explicit grid labels.
3. `fit_dynamic_v1/parameters.json` exports only the six base bounds, omitting the actually fitted optional `lane_drop_phi` bound [0, 6]. Its `model_provenance` also displays base scalar length 0.513441 km and φ = 3 although this fitted model uses a physical variable-length profile and direction-specific φ. The fitted values/profile files are explicit and the fitter applies them; these fields should be read as base-model metadata, not effective post-fit values. Preserve this artifact and add corrective metadata in later artifacts rather than altering a frozen fit.
4. Evaluation hashes six direct inputs/sources, but omits its own driver, `evaluate.pooled`, observation files and canonical model dependencies from the before/after guard. Fit provenance is broader. No corruption was detected here; nonetheless the evaluation receipt alone does not pin every executed dependency. Subsequent response evaluation should capture the complete effective source/config/input manifest.
5. Numerical validity does not evaluate the onset miss, bias tradeoffs, startup response, actual actuator execution, intervention-cost ordering, finite urban receiving forecast, or N_UF-feasible controller selection. Neither the fit nor this review proves those.

## Recommended interpretation and next gate

Keep the physical-grid and vehicle-conservation corrections. Retain the new coefficients as a separately labeled candidate while performing the already planned four-arm native experiment. With common initial state and matched physical support, first compare actual stopline service/merge changes and VSL readback; then compare predicted versus observed differences in mainline discharge, ramp stock and shared-component residence. Report unchanged merge candidates separately from physically effective ones. Future-realized-boundary replay can diagnose the internal kernel but must remain separate from cutoff-safe command-response prediction.

Do not tune these coefficients against the four-arm outcomes before recording the first comparison. If a native intervention changes accepted merge or downstream throughput and the frozen model gets the sign wrong, that isolates a control-response defect. If both native and model show no physical change, it does not establish metering’s general lack of benefit. Full Ω cost must include the waiting displaced into urban approaches; a freeway-plus-connectors result alone cannot certify network improvement.

## Evidence

- `evaluation_dynamic_v1/evaluation.json` — completed 576-window development evaluation.
- `fit_dynamic_v1/parameters.json`, `search.jsonl`, `fitted_source_snapshot.zip` — fitted values and frozen fit sources.
- `CALIBRATION_PROTOCOL.json`, `port_profile.json`, `physical_geometry21_v1.json`.
- `evaluate_physical_boundaries.py`; existing `metanet_calibration_v1/{boundary_factory.py,scoring.py,calibrate.py}`.
- `scenario_comparison_report.md` — current ramp throughput is more suitable for response testing, but current 9000 s recovery is worse than the older 80/50 NC example. Raw costs across changed scenarios are not treatment effects.

Reviewed result SHA-256: `d7535b567d7159b2066662bbb77ec6e66043fb1530de550e73418113d156d2bd`.
Reviewed fit SHA-256: `67a329b1f5f60963211e9ad1611c3e1cc6aeb73ac5a55ec3827eb323d2777e2c`.
