# Real-World MPC One-Step Prediction Accuracy

- decision_dir: `evaluation\runs\rw_cg_hb_4500_fixguard_0723\decisions_pshb4500fixs13`
- warmup_sec: `900.0`
- end_sec: `4500.0`

| group | metric | n | observed | predicted | bias obs-pred | MAE | MAE % obs | RMSE | max AE |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `interface_queue` | `off_ramp_storage_veh` | 61 | 13.713 | 36.085 | -22.372 | 23.943 | 174.6% | 32.208 | 63.691 |
| `interface_queue` | `ramp_queue_total_veh` | 61 | 25.508 | 0.418 | 25.090 | 25.090 | 98.4% | 26.094 | 43.000 |
| `kashani_urban` | `protected_accumulation_veh` | 61 | 13.713 | 74.793 | -61.080 | 61.080 | 445.4% | 62.680 | 91.523 |
| `kashani_urban` | `urban_link_occupancy_total_veh` | 61 | 13.713 | 97.108 | -83.395 | 83.395 | 608.1% | 84.622 | 109.723 |
| `kashani_urban` | `urban_movement_queue_total_veh` | 61 | 13.713 | 56.067 | -42.354 | 42.354 | 308.9% | 42.851 | 54.287 |
| `kashani_urban` | `urban_queue_plus_link_occupancy_total_veh` | 61 | 27.426 | 153.175 | -125.749 | 125.749 | 458.5% | 126.685 | 163.202 |
| `metanet_freeway` | `freeway_mean_density_veh_km_lane` | 61 | 15.074 | 14.170 | 0.903 | 0.951 | 6.3% | 1.133 | 2.808 |
| `metanet_freeway` | `freeway_mean_speed_kph` | 61 | 62.858 | 102.526 | -39.668 | 39.668 | 63.1% | 39.778 | 46.815 |
| `metanet_freeway` | `freeway_total_veh` | 61 | 968.787 | 910.728 | 58.059 | 61.129 | 6.3% | 72.851 | 180.451 |
| `overall` | `total_model_vehicles` | 61 | 996.213 | 1063.903 | -67.690 | 68.970 | 6.9% | 77.664 | 146.762 |
