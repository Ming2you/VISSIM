# Vissim controller stress sweep

Negative `% vs no-control` for vehicle-hours/stopped-hours means improvement.

## Scenario-level comparison

| category | scenario | controller | total veh-h | total % | stopped veh-h | stopped % | speed | speed % | pred abs err | wall s | action movement |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1_ramp_metering | `ramp_d_bias` | `no-control` | 583.893 | 0.000% | 422.315 | 0.000% | 10.407 | 0.000% | 148.062 | 0.384 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 1_ramp_metering | `ramp_d_bias` | `pfo` | 588.754 | 0.833% | 428.810 | 1.538% | 10.136 | -2.603% | 130.944 | 11.044 | split=12.800s, offset=12.524s, vsl-step=0.000, ramp-step=0.000 |
| 1_ramp_metering | `ramp_d_bias` | `wu` | 583.893 | 0.000% | 422.315 | 0.000% | 10.407 | 0.000% | 148.062 | 0.924 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 1_ramp_metering | `ramp_f_bias` | `no-control` | 601.626 | 0.000% | 440.778 | 0.000% | 10.493 | 0.000% | 159.093 | 0.291 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 1_ramp_metering | `ramp_f_bias` | `pfo` | 605.129 | 0.582% | 442.696 | 0.435% | 10.248 | -2.333% | 149.827 | 10.932 | split=11.886s, offset=9.190s, vsl-step=0.000, ramp-step=0.000 |
| 1_ramp_metering | `ramp_f_bias` | `wu` | 601.626 | 0.000% | 440.778 | 0.000% | 10.493 | 0.000% | 159.093 | 0.925 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 2_vsl | `fw_eb_heavy` | `no-control` | 392.144 | 0.000% | 179.714 | 0.000% | 27.272 | 0.000% | 120.492 | 0.291 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 2_vsl | `fw_eb_heavy` | `pfo` | 387.626 | -1.152% | 169.588 | -5.635% | 27.850 | 2.119% | 88.128 | 10.966 | split=10.400s, offset=18.667s, vsl-step=0.000, ramp-step=0.000 |
| 2_vsl | `fw_eb_heavy` | `wu` | 392.144 | 0.000% | 179.714 | 0.000% | 27.272 | 0.000% | 120.492 | 0.813 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 2_vsl | `fw_wb_heavy` | `no-control` | 391.922 | 0.000% | 177.932 | 0.000% | 27.147 | 0.000% | 122.730 | 0.334 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 2_vsl | `fw_wb_heavy` | `pfo` | 387.656 | -1.089% | 173.790 | -2.328% | 27.260 | 0.416% | 85.236 | 11.005 | split=12.343s, offset=19.190s, vsl-step=0.000, ramp-step=0.000 |
| 2_vsl | `fw_wb_heavy` | `wu` | 391.922 | 0.000% | 177.932 | 0.000% | 27.147 | 0.000% | 122.730 | 0.829 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 3_signal_split | `urban_d_heavy` | `no-control` | 338.456 | 0.000% | 140.696 | 0.000% | 30.934 | 0.000% | 177.307 | 0.302 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 3_signal_split | `urban_d_heavy` | `pfo` | 336.699 | -0.519% | 138.104 | -1.842% | 31.123 | 0.609% | 173.787 | 10.578 | split=0.000s, offset=6.238s, vsl-step=0.000, ramp-step=0.000 |
| 3_signal_split | `urban_d_heavy` | `wu` | 338.456 | 0.000% | 140.696 | 0.000% | 30.934 | 0.000% | 177.307 | 0.725 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 3_signal_split | `urban_f_heavy` | `no-control` | 341.438 | 0.000% | 146.560 | 0.000% | 30.334 | 0.000% | 178.808 | 0.285 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 3_signal_split | `urban_f_heavy` | `pfo` | 340.881 | -0.163% | 145.247 | -0.896% | 30.398 | 0.210% | 173.237 | 10.723 | split=0.686s, offset=5.762s, vsl-step=0.000, ramp-step=0.000 |
| 3_signal_split | `urban_f_heavy` | `wu` | 341.438 | 0.000% | 146.560 | 0.000% | 30.334 | 0.000% | 178.808 | 0.712 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `no-control` | 449.704 | 0.000% | 215.399 | 0.000% | 25.389 | 0.000% | 190.707 | 0.286 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `pfo` | 442.797 | -1.536% | 212.964 | -1.130% | 25.461 | 0.281% | 156.416 | 11.113 | split=9.600s, offset=20.095s, vsl-step=0.000, ramp-step=0.000 |
| 4_symmetric_high | `sym_high` | `wu` | 449.704 | 0.000% | 215.399 | 0.000% | 25.389 | 0.000% | 190.707 | 0.873 | split=0.000s, offset=0.000s, vsl-step=0.000, ramp-step=0.000 |

## Controller/category aggregate

| category | controller | cases | mean total % | mean stopped % | mean speed % | mean pred err % | wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1_ramp_metering | `no-control` | 2 | 0.000% | 0.000% | 0.000% | 0.000% | 0.338 |
| 1_ramp_metering | `pfo` | 2 | 0.707% | 0.986% | -2.468% | -8.693% | 10.988 |
| 1_ramp_metering | `wu` | 2 | 0.000% | 0.000% | 0.000% | 0.000% | 0.925 |
| 2_vsl | `no-control` | 2 | 0.000% | 0.000% | 0.000% | 0.000% | 0.313 |
| 2_vsl | `pfo` | 2 | -1.120% | -3.981% | 1.267% | -28.705% | 10.986 |
| 2_vsl | `wu` | 2 | 0.000% | 0.000% | 0.000% | 0.000% | 0.821 |
| 3_signal_split | `no-control` | 2 | 0.000% | 0.000% | 0.000% | 0.000% | 0.294 |
| 3_signal_split | `pfo` | 2 | -0.341% | -1.369% | 0.410% | -2.550% | 10.651 |
| 3_signal_split | `wu` | 2 | 0.000% | 0.000% | 0.000% | 0.000% | 0.719 |
| 4_symmetric_high | `no-control` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.286 |
| 4_symmetric_high | `pfo` | 1 | -1.536% | -1.130% | 0.281% | -17.981% | 11.113 |
| 4_symmetric_high | `wu` | 1 | 0.000% | 0.000% | 0.000% | 0.000% | 0.873 |
