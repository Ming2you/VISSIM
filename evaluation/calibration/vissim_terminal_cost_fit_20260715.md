# VISSIM Terminal Cost Fit

- horizon_sec: 300.0
- samples: 2709
- rmse_vehicle_hours: 5.521357
- mae_vehicle_hours: 4.417545
- r2: 0.960646

## Raw Linear Coefficients

| term | vehicle_hours coefficient |
|---|---:|
| intercept | 21.932638017 |
| total_vehicles | 0.038128753 |
| urban_vehicles | 0.013769547 |
| freeway_vehicles | -0.000841143 |
| ramp_vehicles | 0.087256342 |
| boundary_vehicles | 0.020632515 |
| stopped_vehicles | 0.049553588 |
| mean_speed_kph | 0.680882023 |
| freeway_mean_speed_kph | -0.371367710 |

## Standardized Coefficients

| feature | standardized coefficient |
|---|---:|
| total_vehicles | 13.878491511 |
| urban_vehicles | 1.922978086 |
| freeway_vehicles | -0.057400564 |
| ramp_vehicles | 3.099666918 |
| boundary_vehicles | 2.462481364 |
| stopped_vehicles | 10.458918597 |
| mean_speed_kph | 7.855746963 |
| freeway_mean_speed_kph | -5.922637852 |

## Per Case Fit

| case | n | rmse | mae | r2 |
|---|---:|---:|---:|---:|
| state_no_control_155w_mfd277_smoke | 301 | 5.253181 | 4.611165 | -0.153435 |
| state_no_control_190w_seed13 | 301 | 4.007216 | 3.215025 | 0.905638 |
| state_no_control_220w_seed13 | 301 | 7.158626 | 5.664113 | 0.894648 |
| state_pstack_155w_mfd277_combined_no_pfoinc_smoke | 301 | 5.230717 | 4.582391 | -0.121211 |
| state_pstack_155w_mfd277_combined_smoke | 301 | 5.195226 | 4.525364 | -0.104363 |
| state_pstack_190w_combined_seed13 | 301 | 4.150810 | 3.341187 | 0.912873 |
| state_pstack_190w_no_pfoinc_seed13 | 301 | 3.662598 | 2.909549 | 0.948261 |
| state_pstack_220w_combined_seed13 | 301 | 6.876028 | 5.416657 | 0.915150 |
| state_pstack_220w_no_pfoinc_seed13 | 301 | 6.869821 | 5.492449 | 0.926663 |
