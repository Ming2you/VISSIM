# Vissim controller stress sweep

Negative `% vs no-control` for vehicle-hours/stopped-hours means improvement.

## Scenario-level comparison

| category | scenario | controller | total veh-h | total % | stopped veh-h | stopped % | speed | speed % | pred abs err | wall s | action movement |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1_ramp_metering | `ramp_d_bias` | `no-control` | 64.572 | 0.000% | 28.125 | 0.000% | 30.576 | 0.000% | 27.449 | 0.389 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 1_ramp_metering | `ramp_d_bias` | `pfo` | 64.526 | -0.071% | 27.706 | -1.491% | 30.708 | 0.432% | 39.160 | 33.368 | split=2.000s, offset=6.667s, vsl-step=0.000, ramp-step=0.000 |

## Controller/category aggregate

| category | controller | cases | mean total % | mean stopped % | mean speed % | mean pred err % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1_ramp_metering | `no-control` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.389 |
| 1_ramp_metering | `pfo` | 1 | -0.071% | -1.491% | 0.432% | 42.666% | 33.368 |
