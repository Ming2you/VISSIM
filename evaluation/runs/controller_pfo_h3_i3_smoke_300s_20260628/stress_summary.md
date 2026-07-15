# Vissim controller stress sweep

Negative `% vs no-control` for vehicle-hours/stopped-hours means improvement.

## Scenario-level comparison

| category | scenario | controller | total veh-h | total % | stopped veh-h | stopped % | speed | speed % | pred abs err | wall s | action movement |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4_symmetric_high | `sym_high` | `no-control` | 68.160 | 0.000% | 24.746 | 0.000% | 35.949 | 0.000% | 101.403 | 0.377 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 68.065 | -0.139% | 24.117 | -2.543% | 36.183 | 0.649% | 102.177 | 33.500 | split=4.800s, offset=7.167s, vsl-step=0.000, ramp-step=0.000 |

## Controller/category aggregate

| category | controller | cases | mean total % | mean stopped % | mean speed % | mean pred err % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4_symmetric_high | `no-control` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.377 |
| 4_symmetric_high | `pfo` | 1 | -0.139% | -2.543% | 0.649% | 0.763% | 33.500 |
