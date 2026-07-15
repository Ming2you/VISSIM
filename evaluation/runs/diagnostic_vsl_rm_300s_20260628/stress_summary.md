# Vissim controller stress sweep

Negative `% vs no-control` for vehicle-hours/stopped-hours means improvement.

## Scenario-level comparison

| category | scenario | controller | total veh-h | total % | stopped veh-h | stopped % | speed | speed % | pred abs err | wall s | action movement |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1_ramp_metering | `ramp_d_bias` | `diagnostic-vsl-rm` | 66.674 | 3.254% | 29.001 | 3.116% | 27.937 | -8.632% | 42.857 | 0.327 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 1_ramp_metering | `ramp_d_bias` | `no-control` | 64.572 | 0.000% | 28.125 | 0.000% | 30.576 | 0.000% | 27.449 | 0.326 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |

## Controller/category aggregate

| category | controller | cases | mean total % | mean stopped % | mean speed % | mean pred err % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1_ramp_metering | `diagnostic-vsl-rm` | 1 | 3.254% | 3.116% | -8.632% | 56.135% | 0.327 |
| 1_ramp_metering | `no-control` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.326 |
