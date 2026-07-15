# Vissim controller stress sweep

Negative `% vs no-control` for vehicle-hours/stopped-hours means improvement.

## Scenario-level comparison

| category | scenario | controller | total veh-h | total % | stopped veh-h | stopped % | speed | speed % | pred abs err | wall s | action movement |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2_vsl | `fw_eb_heavy` | `no-control` | 142.811 | 0.000% | 51.543 | 0.000% | 33.086 | 0.000% | 97.394 | 0.397 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 2_vsl | `fw_eb_heavy` | `pfo` | 143.418 | 0.425% | 53.069 | 2.961% | 32.447 | -1.930% | 61.809 | 31.332 | split=8.509s, offset=14.636s, vsl-step=0.000, ramp-step=0.000 |

## Controller/category aggregate

| category | controller | cases | mean total % | mean stopped % | mean speed % | mean pred err % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2_vsl | `no-control` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.397 |
| 2_vsl | `pfo` | 1 | 0.425% | 2.961% | -1.930% | -36.537% | 31.332 |
