# Vissim controller stress sweep

Negative `% vs no-control` for vehicle-hours/stopped-hours means improvement.

## Scenario-level comparison

| category | scenario | controller | total veh-h | total % | stopped veh-h | stopped % | speed | speed % | pred abs err | wall s | action movement |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1_ramp_metering | `ramp_d_bias` | `no-control` | 65.779 | 0.000% | 28.904 | 0.000% | 30.122 | 0.000% | 22.504 | 0.511 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 2_vsl | `fw_eb_heavy` | `no-control` | 52.499 | 0.000% | 15.097 | 0.000% | 39.802 | 0.000% | 51.864 | 0.347 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 3_signal_split | `urban_d_heavy` | `no-control` | 47.624 | 0.000% | 13.846 | 0.000% | 42.167 | 0.000% | 109.076 | 0.354 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |

## Controller/category aggregate

| category | controller | cases | mean total % | mean stopped % | mean speed % | mean pred err % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1_ramp_metering | `no-control` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.511 |
| 2_vsl | `no-control` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.347 |
| 3_signal_split | `no-control` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.354 |
