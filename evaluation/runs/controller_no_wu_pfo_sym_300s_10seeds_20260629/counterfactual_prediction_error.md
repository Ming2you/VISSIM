# Counterfactual prediction audit error

- Counterfactual calibration: `evaluation\calibration\vissim_network_calibration_v3_prediction_audit_20260629.json`
- Active means the prediction summary already stored in existing action JSONs.
- Counterfactual reapplies the candidate audit scales to the raw source prediction summary.

| controller | metric | n | raw abs | active abs | counterfactual abs | cf vs active |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `no-control` | `freeway_segment_total_veh` | 50 | 40.845 | 24.883 | 9.226 | -62.9% |
| `no-control` | `freeway_total_veh` | 50 | 40.845 | 24.883 | 9.226 | -62.9% |
| `no-control` | `total_model_vehicles` | 50 | 99.371 | 58.416 | 68.803 | 17.8% |
| `no-control` | `urban_queue_plus_link_occupancy_total_veh` | 50 | 68.790 | 75.801 | 49.333 | -34.9% |
| `pfo` | `freeway_segment_total_veh` | 50 | 45.296 | 22.141 | 10.327 | -53.4% |
| `pfo` | `freeway_total_veh` | 50 | 45.296 | 22.141 | 10.327 | -53.4% |
| `pfo` | `total_model_vehicles` | 50 | 66.842 | 32.709 | 37.545 | 14.8% |
| `pfo` | `urban_queue_plus_link_occupancy_total_veh` | 50 | 34.162 | 38.844 | 33.561 | -13.6% |
| `wu` | `freeway_segment_total_veh` | 50 | 40.893 | 24.832 | 9.336 | -62.4% |
| `wu` | `freeway_total_veh` | 50 | 40.893 | 24.832 | 9.336 | -62.4% |
| `wu` | `total_model_vehicles` | 50 | 98.169 | 57.546 | 67.723 | 17.7% |
| `wu` | `urban_queue_plus_link_occupancy_total_veh` | 50 | 67.541 | 74.558 | 48.718 | -34.7% |
