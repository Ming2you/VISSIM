# Prediction audit Bayesian calibration update

- Source decisions: `180`
- Prior calibration: `evaluation\calibration\vissim_network_calibration_v2_20260628.json`
- Ratio basis: `observed / source prediction.state_summary raw value`
- Policy: patch artifact only; active calibration is not overwritten.

| target | status | samples | prior | posterior | raw median ratio | calibrated median ratio | raw abs err | active abs err | posterior abs err | posterior vs active |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `freeway_total_veh` | `ok` | 150 | 0.6507 | 0.7770 | 0.7784 | 1.1962 | 42.345 | 23.952 | 9.630 | -59.8% |
| `urban_queue_plus_link_occupancy_total_veh` | `ok` | 150 | 1.0126 | 0.9543 | 0.9502 | 0.9384 | 56.831 | 63.068 | 43.870 | -30.4% |

## Caveat

This is a one-step audit correction fitted from completed controller decisions. The posterior is an absolute scale against the raw source prediction, not a multiplier on the already calibrated prediction. Promote only after held-out validation.
