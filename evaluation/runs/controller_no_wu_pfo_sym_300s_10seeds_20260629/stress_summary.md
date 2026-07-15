# Vissim controller stress sweep

Negative `% vs no-control` for vehicle-hours/stopped-hours means improvement.

## Scenario-level comparison

| category | scenario | controller | total veh-h | total % | stopped veh-h | stopped % | speed | speed % | pred abs err | wall s | action movement |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 4_symmetric_high | `sym_high` | `no-control` | 67.168 | 0.000% | 23.569 | 0.000% | 37.041 | 0.000% | 61.149 | 0.326 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `no-control` | 68.160 | 0.000% | 24.746 | 0.000% | 35.949 | 0.000% | 67.892 | 0.312 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `no-control` | 67.639 | 0.000% | 24.001 | 0.000% | 36.427 | 0.000% | 41.569 | 0.312 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `no-control` | 70.565 | 0.000% | 25.335 | 0.000% | 34.646 | 0.000% | 69.072 | 0.385 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `no-control` | 67.385 | 0.000% | 22.514 | 0.000% | 36.203 | 0.000% | 42.197 | 0.375 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `no-control` | 65.971 | 0.000% | 23.829 | 0.000% | 36.120 | 0.000% | 65.202 | 0.374 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `no-control` | 67.468 | 0.000% | 24.129 | 0.000% | 37.360 | 0.000% | 51.945 | 0.384 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `no-control` | 65.318 | 0.000% | 22.301 | 0.000% | 37.940 | 0.000% | 53.062 | 0.355 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `no-control` | 67.883 | 0.000% | 24.476 | 0.000% | 35.143 | 0.000% | 56.689 | 0.376 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `no-control` | 71.421 | 0.000% | 25.850 | 0.000% | 34.130 | 0.000% | 75.386 | 0.386 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 67.250 | 0.122% | 22.929 | -2.717% | 37.299 | 0.697% | 40.831 | 32.501 | split=4.000s, offset=10.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 68.151 | -0.012% | 23.800 | -3.822% | 36.262 | 0.870% | 25.770 | 31.991 | split=6.400s, offset=11.167s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 67.361 | -0.411% | 23.163 | -3.495% | 36.818 | 1.074% | 34.142 | 31.925 | split=3.600s, offset=10.333s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 70.414 | -0.215% | 25.053 | -1.113% | 34.610 | -0.104% | 36.861 | 31.800 | split=7.600s, offset=11.333s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 71.132 | -0.404% | 25.358 | -1.902% | 34.254 | 0.362% | 46.770 | 31.678 | split=8.800s, offset=16.667s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 67.029 | -0.528% | 21.363 | -5.114% | 36.566 | 1.001% | 25.921 | 31.501 | split=6.400s, offset=14.667s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 65.635 | -0.509% | 22.444 | -5.811% | 36.660 | 1.493% | 18.477 | 32.124 | split=9.200s, offset=16.833s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 67.272 | -0.290% | 23.025 | -4.576% | 37.771 | 1.100% | 34.023 | 31.849 | split=2.800s, offset=10.333s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 65.368 | 0.077% | 21.508 | -3.556% | 37.935 | -0.013% | 46.675 | 32.235 | split=3.760s, offset=14.500s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 67.497 | -0.569% | 23.121 | -5.538% | 35.591 | 1.275% | 17.621 | 32.115 | split=7.200s, offset=11.667s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 67.185 | 0.025% | 23.624 | 0.230% | 37.006 | -0.094% | 60.149 | 1.729 | split=1.067s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 68.190 | 0.045% | 24.786 | 0.163% | 35.928 | -0.059% | 67.892 | 1.823 | split=0.267s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 67.639 | 0.000% | 24.001 | 0.000% | 36.427 | 0.000% | 41.569 | 1.620 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 70.581 | 0.022% | 25.347 | 0.049% | 34.627 | -0.056% | 66.725 | 1.885 | split=1.067s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 71.403 | -0.025% | 25.812 | -0.145% | 34.128 | -0.008% | 76.708 | 1.759 | split=1.600s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 67.478 | 0.138% | 22.751 | 1.055% | 36.082 | -0.336% | 39.657 | 1.836 | split=4.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 65.990 | 0.029% | 23.821 | -0.035% | 36.092 | -0.079% | 63.802 | 1.500 | split=0.533s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 67.504 | 0.054% | 24.153 | 0.098% | 37.297 | -0.170% | 49.597 | 1.511 | split=3.200s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 65.353 | 0.053% | 22.544 | 1.090% | 37.813 | -0.334% | 52.917 | 1.700 | split=1.533s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 67.881 | -0.004% | 24.546 | 0.284% | 35.094 | -0.138% | 56.444 | 1.697 | split=1.600s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |

## Controller/category aggregate

| category | controller | cases | mean total % | mean stopped % | mean speed % | mean pred err % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4_symmetric_high | `no-control` | 10 | 0.000% | 0.000% | 0.000% | 0.000% | 0.359 |
| 4_symmetric_high | `pfo` | 10 | -0.274% | -3.764% | 0.775% | -42.342% | 31.972 |
| 4_symmetric_high | `wu` | 10 | 0.034% | 0.279% | -0.127% | -1.667% | 1.706 |
