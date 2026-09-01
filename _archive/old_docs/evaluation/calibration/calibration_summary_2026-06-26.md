# Vissim calibration summary

Date: 2026-06-26

This summary uses the `GetAll`-free calibration probe. Vehicle state logging was changed to
`Vehicles.GetMultiAttValues("Lane" / "Pos" / "Speed")`, which reduced the 900 s calibration
case wall time to roughly 1.5–2.5 minutes for normal cases.

## Sweep completion

| Sweep | Cases | Status | Mean case wall time |
|---|---:|---|---:|
| FD freeway demand | 12 | complete | 105.0 s |
| Ramp general | 12 | complete | 117.6 s |
| D ramp saturated | 12 | complete | 148.5 s |
| F ramp saturated | 12 | complete | 147.3 s |
| Signal green split | 12 | complete | 139.3 s |
| Urban MFD | 16 | complete | 131.9 s |

Some cases froze at Vissim startup after `STAGE=COM_CREATED`; those were killed and rerun
individually. Completed manifests now show `returncode=0` for all cases.

## Freeway FD

Output:

- `evaluation/calibration/vissim_calibration_fit_fd_vector_20260626.json`

Initial controller values:

| Parameter | Value | Note |
|---|---:|---|
| `v_free` | 123.825 kph | p85 low-density speed |
| `freeway_capacity` | 4574.818 veh/h | instantaneous flow proxy peak |
| `rho_crit` | 20.401 veh/km/lane | density at max flow proxy |
| `rho_max_observed` | 33.130 veh/km/lane | observed max only, not jam density |

Use `v_free`, `capacity`, and `rho_crit` directly for the first MPC pass. Do not treat
`rho_max_observed` as a calibrated jam density yet.

## Ramp metering

Outputs:

- `evaluation/calibration/vissim_calibration_fit_ramp_vector_20260626.json`
- `evaluation/calibration/vissim_calibration_fit_rampD_bias_vector_20260626.json`
- `evaluation/calibration/vissim_calibration_fit_rampF_bias_vector_20260626.json`

D ramp saturated fit is usable as an initial green-to-release map:

| Green sec / 10 s cycle | Raw release veh/h | Initial MPC map veh/h |
|---:|---:|---:|
| 1 | 690.7 | 691 |
| 2 | 684.9 | 691 |
| 4 | 1252.7 | 1253 |
| 6 | 1363.9 | 1364 |
| 8 | 1311.2 | 1364 |
| 10 | 1413.7 | 1414 |

F ramp is not physically trustworthy yet:

| Green sec / 10 s cycle | F saturated release veh/h |
|---:|---:|
| 1 | 96.6 |
| 2 | 122.9 |
| 4 | 283.9 |
| 6 | 307.3 |
| 8 | 316.1 |
| 10 | 237.1 |

The F ramp had sustained queues but low discharge. This strongly indicates a remaining
route/lane/connector bottleneck around link 31, not a metering calibration effect. For the
first controller pass, use F ramp metering only as a conservative fallback or monitor-only
until the network movement is fixed.

## Signal saturation / lost time

Outputs:

- `evaluation/calibration/vissim_calibration_fit_signal_vector_20260626.json`
- `evaluation/calibration/vissim_signal_green_fit_20260626.json`

The 15 s burst max values are too spiky for saturation flow. The green-fit model used:

`q_vph * cycle_sec = saturation_flow_vph * (green_sec - lost_time_sec)`

Current result:

| Parameter | Value |
|---|---:|
| Median fitted lost time | 6.009 s |
| Median fitted saturation flow, approach total | 829.29 veh/h |
| Recommended initial saturation flow, approach total | 1800 veh/h |
| Recommended initial lost time | 6.0 s |

The median fitted saturation flow is likely low because several approaches are underfed.
Use 1800 veh/h per two-lane approach as the initial controller value, then refine with
detector/output-based saturated approach runs.

## Urban MFD

Output:

- `evaluation/calibration/vissim_calibration_fit_mfd_vector_20260626.json`

The raw peak-row candidate is 376 vehicles. Demand-level median production peaks around
urban demand 3000 vph with median urban accumulation around 390 vehicles.

Initial MFD value:

| Parameter | Value |
|---|---:|
| `N_P_crit_veh` | 390 veh |
| Peak median signal production | 12360 veh/h |

Production is currently aggregated signal stop-line discharge, not completed trip production.

## Controller calibration handoff

Use:

- `evaluation/calibration/vissim_calibrated_overrides_vector_20260626.json`

Recommended next MPC tuning sequence:

1. Apply FD values and D ramp green-to-release map.
2. Keep F ramp metering conservative or monitor-only until the F ramp movement is repaired.
3. Use `N_P_crit_veh = 390` for urban accumulation activation.
4. Sweep MPC weight / smoothness / activation ratio under fixed seeds.
