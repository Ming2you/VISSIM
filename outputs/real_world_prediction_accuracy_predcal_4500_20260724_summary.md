# Real-World MPC One-Step Prediction Accuracy

- decision_dir: `evaluation\runs\rw_cg_predcal_4500_20260724\decisions_pspredcal4500s13`
- warmup_sec: `900.0`
- end_sec: `4500.0`

| group | metric | n | observed | predicted | bias obs-pred | MAE | MAE % obs | RMSE | max AE |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `interface_queue` | `off_ramp_storage_veh` | 61 | 13.713 | 13.713 | 0.000 | 8.843 | 64.5% | 10.051 | 18.552 |
| `interface_queue` | `ramp_queue_total_veh` | 61 | 25.508 | 0.418 | 25.090 | 25.090 | 98.4% | 26.094 | 43.000 |
| `kashani_urban` | `protected_accumulation_veh` | 61 | 13.713 | 13.713 | 0.000 | 3.513 | 25.6% | 4.519 | 11.546 |
| `kashani_urban` | `urban_link_occupancy_total_veh` | 61 | 13.713 | 13.713 | 0.000 | 4.287 | 31.3% | 4.996 | 11.314 |
| `kashani_urban` | `urban_movement_queue_total_veh` | 61 | 13.713 | 13.713 | -0.000 | 3.373 | 24.6% | 4.112 | 9.974 |
| `kashani_urban` | `urban_queue_plus_link_occupancy_total_veh` | 61 | 27.426 | 27.426 | 0.000 | 7.546 | 27.5% | 8.726 | 18.730 |
| `metanet_freeway` | `freeway_mean_density_veh_km_lane` | 61 | 15.074 | 15.074 | -0.000 | 0.488 | 3.2% | 0.589 | 1.702 |
| `metanet_freeway` | `freeway_mean_speed_kph` | 61 | 62.858 | 62.858 | -0.000 | 3.293 | 5.2% | 4.145 | 10.061 |
| `metanet_freeway` | `freeway_total_veh` | 61 | 968.787 | 968.787 | 0.000 | 31.353 | 3.2% | 37.870 | 109.398 |
| `overall` | `total_model_vehicles` | 61 | 996.213 | 999.582 | -3.369 | 30.721 | 3.1% | 36.945 | 96.905 |
