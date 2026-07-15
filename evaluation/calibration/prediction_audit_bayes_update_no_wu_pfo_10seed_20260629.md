# Prediction audit Bayesian calibration update

- Source decisions: `180`
- Prior calibration: `evaluation\calibration\vissim_network_calibration_v2_20260628.json`
- Policy: patch artifact only; active calibration is not overwritten.

| target | status | samples | prior | posterior | median ratio | p10 | p90 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `freeway_total_veh` | `ok` | 150 | 0.6507 | 1.1908 | 1.1962 | 1.0676 | 1.3341 |
| `urban_queue_plus_link_occupancy_total_veh` | `ok` | 150 | 1.0126 | 0.9424 | 0.9384 | 0.8293 | 1.0470 |

## Caveat

This is a one-step audit correction fitted from completed controller decisions. It should be promoted into the active controller only after the same update improves prediction error on a held-out demand profile or seed.
