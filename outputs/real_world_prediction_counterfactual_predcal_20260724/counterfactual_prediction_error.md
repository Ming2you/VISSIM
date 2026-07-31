# Counterfactual prediction audit error

- Counterfactual calibration: `evaluation\calibration\real_world_prediction_calibration_pshb4500fix_20260724.json`
- Active means the prediction summary already stored in existing action JSONs.
- Counterfactual reapplies the candidate audit scales to the raw source prediction summary.

| controller | metric | n | observed | active pred | cf pred | active abs | cf abs | cf vs active |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `all` | `total_model_vehicles` | 61 | 996.213 | 1063.903 | 999.582 | 68.970 | 30.721 | -55.5% |
| `all` | `freeway_total_veh` | 61 | 968.787 | 910.728 | 968.787 | 61.129 | 31.353 | -48.7% |
| `all` | `freeway_segment_total_veh` | 61 | 968.787 | 910.728 | 968.787 | 61.129 | 31.353 | -48.7% |
| `all` | `freeway_mean_density_veh_km_lane` | 61 | 15.074 | 14.170 | 15.074 | 0.951 | 0.488 | -48.7% |
| `all` | `freeway_mean_speed_kph` | 61 | 62.858 | 102.526 | 62.858 | 39.668 | 3.293 | -91.7% |
| `all` | `urban_queue_plus_link_occupancy_total_veh` | 61 | 27.426 | 153.175 | 27.426 | 125.749 | 7.546 | -94.0% |
| `all` | `protected_accumulation_veh` | 61 | 13.713 | 74.793 | 13.713 | 61.080 | 3.513 | -94.2% |
| `all` | `urban_movement_queue_total_veh` | 61 | 13.713 | 56.067 | 13.713 | 42.354 | 3.373 | -92.0% |
| `all` | `urban_link_occupancy_total_veh` | 61 | 13.713 | 97.108 | 13.713 | 83.395 | 4.287 | -94.9% |
| `all` | `urban_total_veh` | 61 | 13.713 | 117.090 | 17.082 | 103.376 | 5.411 | -94.8% |
| `all` | `boundary_queue_total_veh` | 61 | 0.000 | 37.537 | 1.877 | 37.537 | 1.877 | -95.0% |
| `all` | `off_ramp_storage_veh` | 61 | 13.713 | 36.085 | 13.713 | 23.943 | 8.843 | -63.1% |
| `all` | `ramp_queue_total_veh` | 61 | 25.508 | 0.418 | 0.418 | 25.090 | 25.090 | 0.0% |
| `all` | `mainline_origin_queue_total_veh` | 61 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
