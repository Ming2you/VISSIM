# VISSIM Terminal Cost Fit

- horizon_sec: 300.0
- samples: 2709
- rmse_vehicle_hours: 6.437861
- mae_vehicle_hours: 5.238960
- r2: 0.946496

## Raw Linear Coefficients

| term | vehicle_hours coefficient |
|---|---:|
| intercept | 23.875878714 |
| total_vehicles | 0.085838059 |
| urban_vehicles | -0.090459291 |
| ramp_vehicles | 0.022097285 |
| boundary_vehicles | -0.015325464 |
| stopped_vehicles | 0.043702476 |

## Standardized Coefficients

| feature | standardized coefficient |
|---|---:|
| total_vehicles | 31.244210098 |
| urban_vehicles | -12.633040151 |
| ramp_vehicles | 0.784977014 |
| boundary_vehicles | -1.829087217 |
| stopped_vehicles | 9.223966592 |

## Per Case Fit

| case | n | rmse | mae | r2 |
|---|---:|---:|---:|---:|
| state_no_control_155w_mfd277_smoke | 301 | 6.721534 | 6.305829 | -0.888363 |
| state_no_control_190w_seed13 | 301 | 3.985708 | 2.808318 | 0.906649 |
| state_no_control_220w_seed13 | 301 | 8.033881 | 6.563423 | 0.867311 |
| state_pstack_155w_mfd277_combined_no_pfoinc_smoke | 301 | 6.727824 | 6.317179 | -0.854874 |
| state_pstack_155w_mfd277_combined_smoke | 301 | 6.707915 | 6.258497 | -0.841103 |
| state_pstack_190w_combined_seed13 | 301 | 4.075447 | 2.933343 | 0.916008 |
| state_pstack_190w_no_pfoinc_seed13 | 301 | 4.198235 | 3.095196 | 0.932021 |
| state_pstack_220w_combined_seed13 | 301 | 8.032983 | 6.612637 | 0.884194 |
| state_pstack_220w_no_pfoinc_seed13 | 301 | 7.640904 | 6.256221 | 0.909276 |
