# Vissim controller stress sweep

Negative `% vs no-control` for vehicle-hours/stopped-hours means improvement.

## Scenario-level comparison

| category | scenario | controller | total veh-h | total % | stopped veh-h | stopped % | speed | speed % | pred abs err | wall s | action movement |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4_symmetric_high | `sym_high` | `no-control` | 181.467 | 0.000% | 77.732 | 0.000% | 28.558 | 0.000% | 158.613 | 0.372 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 179.925 | -0.850% | 75.419 | -2.975% | 28.807 | 0.869% | 141.072 | 31.168 | split=7.680s, offset=10.364s, vsl-step=0.000, ramp-step=0.000 |

## Controller/category aggregate

| category | controller | cases | mean total % | mean stopped % | mean speed % | mean pred err % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4_symmetric_high | `no-control` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.372 |
| 4_symmetric_high | `pfo` | 1 | -0.850% | -2.975% | 0.869% | -11.059% | 31.168 |
