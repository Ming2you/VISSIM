# Vissim controller stress sweep

Negative `% vs no-control` for vehicle-hours/stopped-hours means improvement.

## Scenario-level comparison

| category | scenario | controller | total veh-h | total % | stopped veh-h | stopped % | speed | speed % | pred abs err | wall s | action movement |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4_symmetric_high | `sym_high` | `no-control` | 68.160 | 0.000% | 24.746 | 0.000% | 35.949 | 0.000% | 67.892 | 0.504 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 68.151 | -0.012% | 23.800 | -3.822% | 36.262 | 0.870% | 25.770 | 32.266 | split=6.400s, offset=11.167s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 68.190 | 0.045% | 24.786 | 0.163% | 35.928 | -0.059% | 67.892 | 1.756 | split=0.267s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |

## Controller/category aggregate

| category | controller | cases | mean total % | mean stopped % | mean speed % | mean pred err % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4_symmetric_high | `no-control` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.504 |
| 4_symmetric_high | `pfo` | 1 | -0.012% | -3.822% | 0.870% | -62.043% | 32.266 |
| 4_symmetric_high | `wu` | 1 | 0.045% | 0.163% | -0.059% | -0.000% | 1.756 |
