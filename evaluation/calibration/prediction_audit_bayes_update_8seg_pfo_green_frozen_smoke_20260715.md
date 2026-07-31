# Prediction audit Bayesian calibration update

- Source decisions: `4`
- Prior calibration: `evaluation\calibration\vissim_network_calibration_v2_8seg_20260714.json`
- Ratio basis: `observed / source prediction.state_summary raw value`
- Policy: patch artifact only; active calibration is not overwritten.

| target | status | samples | prior | posterior | raw median ratio | calibrated median ratio | raw abs err | active abs err | posterior abs err | posterior vs active |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `freeway_total_veh` | `ok` | 3 | 0.6507 | 0.8030 | 0.8273 | 1.2714 | 27.425 | 42.819 | 12.198 | -71.5% |
| `urban_queue_plus_link_occupancy_total_veh` | `ok` | 3 | 1.0126 | 0.7888 | 0.6431 | 0.6351 | 200.673 | 209.101 | 103.885 | -50.3% |

## Caveat

This is a one-step audit correction fitted from completed controller decisions. The posterior is an absolute scale against the raw source prediction, not a multiplier on the already calibrated prediction. Promote only after held-out validation.
