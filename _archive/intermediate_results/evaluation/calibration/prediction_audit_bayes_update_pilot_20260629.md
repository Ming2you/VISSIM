# Prediction audit Bayesian calibration update

- Source decisions: `18`
- Prior calibration: `evaluation\calibration\vissim_network_calibration_v2_20260628.json`
- Policy: patch artifact only; active calibration is not overwritten.

| target | status | samples | prior | posterior | median ratio | p10 | p90 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `freeway_total_veh` | `ok` | 15 | 0.6507 | 1.0962 | 1.1348 | 1.0811 | 1.1818 |
| `urban_queue_plus_link_occupancy_total_veh` | `ok` | 15 | 1.0126 | 0.9532 | 0.9241 | 0.8441 | 1.1001 |

## Caveat

This is a one-step audit correction fitted from completed controller decisions. It should be promoted into the active controller only after the same update improves prediction error on a held-out demand profile or seed.
