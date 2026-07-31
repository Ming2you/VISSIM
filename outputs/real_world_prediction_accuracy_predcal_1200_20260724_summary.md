# Real-World MPC One-Step Prediction Accuracy

- decision_dir: `evaluation\runs\rw_cg_predcal_1200_20260724\decisions_pspredcal1200s13`
- warmup_sec: `900.0`
- end_sec: `1200.0`

| group | metric | n | observed | predicted | bias obs-pred | MAE | MAE % obs | RMSE | max AE |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `interface_queue` | `off_ramp_storage_veh` | 6 | 13.667 | 12.623 | 1.043 | 8.272 | 60.5% | 8.976 | 10.957 |
| `interface_queue` | `ramp_queue_total_veh` | 6 | 30.667 | 0.458 | 30.209 | 30.209 | 98.5% | 30.601 | 35.250 |
| `kashani_urban` | `protected_accumulation_veh` | 6 | 13.667 | 13.892 | -0.226 | 2.706 | 19.8% | 3.204 | 6.277 |
| `kashani_urban` | `urban_link_occupancy_total_veh` | 6 | 13.667 | 13.437 | 0.229 | 3.475 | 25.4% | 3.822 | 5.100 |
| `kashani_urban` | `urban_movement_queue_total_veh` | 6 | 13.667 | 13.649 | 0.018 | 2.901 | 21.2% | 3.407 | 4.819 |
| `kashani_urban` | `urban_queue_plus_link_occupancy_total_veh` | 6 | 27.333 | 27.086 | 0.247 | 6.190 | 22.6% | 7.062 | 8.924 |
| `metanet_freeway` | `freeway_mean_density_veh_km_lane` | 6 | 14.632 | 14.677 | -0.045 | 0.418 | 2.9% | 0.451 | 0.693 |
| `metanet_freeway` | `freeway_mean_speed_kph` | 6 | 63.235 | 63.521 | -0.285 | 2.082 | 3.3% | 2.414 | 4.330 |
| `metanet_freeway` | `freeway_total_veh` | 6 | 940.333 | 943.246 | -2.913 | 26.876 | 2.9% | 28.962 | 44.532 |
| `overall` | `total_model_vehicles` | 6 | 967.667 | 973.023 | -5.357 | 21.078 | 2.2% | 23.473 | 30.561 |
