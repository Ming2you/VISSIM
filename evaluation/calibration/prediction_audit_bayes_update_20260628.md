# Prediction audit Bayesian calibration update

- Source decisions: `531`
- Prior calibration: `evaluation\calibration\vissim_network_calibration_v2_20260628.json`
- Policy: patch artifact only; active calibration is not overwritten.

| target | status | samples | prior | posterior | median ratio | p10 | p90 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `freeway_total_veh` | `ok` | 495 | 0.6507 | 0.7234 | 0.6753 | 0.5527 | 1.0793 |
| `urban_queue_plus_link_occupancy_total_veh` | `ok` | 75 | 1.0126 | 0.9210 | 0.9324 | 0.8221 | 1.1047 |

## Caveat

This is a one-step audit correction fitted from completed controller decisions. It should be promoted into the active controller only after the same update improves prediction error on a held-out demand profile or seed.
