# Vissim MPC tuning summary

- Warmup excluded from vehicle-hour metrics: 60 s
- Case count: 15
- Completed usable cases: 15
- Failed/empty cases: 0
- Current best group: `04_smooth_low / urban_d_heavy`
- Best mean total vehicle-hours: 53.788
- Best mean stopped vehicle-hours: 18.400

## Group ranking

| rank | tuning | demand | cases | total veh-h | stopped veh-h | speed kph | VSL step | ramp step | signal step | fallback rows |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `04_smooth_low` | `urban_d_heavy` | 1 | 53.788 | 18.400 | 39.794 | 0.000 | 0.900 | 0.200 | 0 |
| 2 | `08_mfd_strong` | `urban_d_heavy` | 1 | 53.788 | 18.400 | 39.794 | 0.000 | 0.900 | 0.200 | 0 |
| 3 | `00_calibrated_base` | `urban_d_heavy` | 1 | 53.678 | 19.275 | 39.498 | 0.000 | 0.000 | 0.080 | 0 |
| 4 | `05_activation_early` | `urban_d_heavy` | 1 | 53.678 | 19.275 | 39.498 | 0.000 | 0.000 | 0.080 | 0 |
| 5 | `07_boundary_queue_priority` | `urban_d_heavy` | 1 | 53.789 | 18.932 | 39.729 | 0.000 | 0.000 | 0.080 | 0 |
| 6 | `07_boundary_queue_priority` | `sym` | 1 | 66.496 | 27.251 | 34.585 | 0.000 | 0.000 | 0.080 | 0 |
| 7 | `08_mfd_strong` | `sym` | 1 | 66.500 | 27.367 | 34.338 | 0.000 | 0.900 | 0.240 | 0 |
| 8 | `00_calibrated_base` | `sym` | 1 | 66.482 | 27.639 | 34.382 | 0.000 | 0.000 | 0.080 | 0 |
| 9 | `05_activation_early` | `sym` | 1 | 66.482 | 27.639 | 34.382 | 0.000 | 0.000 | 0.080 | 0 |
| 10 | `04_smooth_low` | `sym` | 1 | 66.829 | 27.544 | 34.255 | 0.000 | 0.900 | 0.240 | 0 |
| 11 | `07_boundary_queue_priority` | `d_ramp_bias` | 1 | 71.442 | 34.393 | 26.127 | 0.000 | 0.000 | 0.080 | 0 |
| 12 | `08_mfd_strong` | `d_ramp_bias` | 1 | 72.232 | 33.132 | 25.478 | 0.000 | 0.900 | 0.160 | 0 |
| 13 | `04_smooth_low` | `d_ramp_bias` | 1 | 71.967 | 34.864 | 25.377 | 0.000 | 0.000 | 0.080 | 0 |
| 14 | `00_calibrated_base` | `d_ramp_bias` | 1 | 72.850 | 37.049 | 24.680 | 0.000 | 0.000 | 0.080 | 0 |
| 15 | `05_activation_early` | `d_ramp_bias` | 1 | 72.850 | 37.049 | 24.680 | 0.000 | 0.000 | 0.080 | 0 |

## Case-level notes

| case | demand | status | total veh-h | stopped veh-h | mean speed | decisions | decision wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `mpc_00_calibrated_base_d_ramp_bias_u2600_fw3400_seed13_300s` | `d_ramp_bias` | ok | 72.850 | 37.049 | 24.680 | 6 | 3.205 |
| `mpc_00_calibrated_base_sym_u2600_fw3400_seed13_300s` | `sym` | ok | 66.482 | 27.639 | 34.382 | 6 | 3.014 |
| `mpc_00_calibrated_base_urban_d_heavy_u2600_fw3400_seed13_300s` | `urban_d_heavy` | ok | 53.678 | 19.275 | 39.498 | 6 | 3.244 |
| `mpc_04_smooth_low_d_ramp_bias_u2600_fw3400_seed13_300s` | `d_ramp_bias` | ok | 71.967 | 34.864 | 25.377 | 6 | 3.237 |
| `mpc_04_smooth_low_sym_u2600_fw3400_seed13_300s` | `sym` | ok | 66.829 | 27.544 | 34.255 | 6 | 3.205 |
| `mpc_04_smooth_low_urban_d_heavy_u2600_fw3400_seed13_300s` | `urban_d_heavy` | ok | 53.788 | 18.400 | 39.794 | 6 | 3.261 |
| `mpc_05_activation_early_d_ramp_bias_u2600_fw3400_seed13_300s` | `d_ramp_bias` | ok | 72.850 | 37.049 | 24.680 | 6 | 3.109 |
| `mpc_05_activation_early_sym_u2600_fw3400_seed13_300s` | `sym` | ok | 66.482 | 27.639 | 34.382 | 6 | 3.209 |
| `mpc_05_activation_early_urban_d_heavy_u2600_fw3400_seed13_300s` | `urban_d_heavy` | ok | 53.678 | 19.275 | 39.498 | 6 | 3.224 |
| `mpc_07_boundary_queue_priority_d_ramp_bias_u2600_fw3400_seed13_300s` | `d_ramp_bias` | ok | 71.442 | 34.393 | 26.127 | 6 | 3.049 |
| `mpc_07_boundary_queue_priority_sym_u2600_fw3400_seed13_300s` | `sym` | ok | 66.496 | 27.251 | 34.585 | 6 | 3.125 |
| `mpc_07_boundary_queue_priority_urban_d_heavy_u2600_fw3400_seed13_300s` | `urban_d_heavy` | ok | 53.789 | 18.932 | 39.729 | 6 | 3.165 |
| `mpc_08_mfd_strong_d_ramp_bias_u2600_fw3400_seed13_300s` | `d_ramp_bias` | ok | 72.232 | 33.132 | 25.478 | 6 | 3.102 |
| `mpc_08_mfd_strong_sym_u2600_fw3400_seed13_300s` | `sym` | ok | 66.500 | 27.367 | 34.338 | 6 | 3.106 |
| `mpc_08_mfd_strong_urban_d_heavy_u2600_fw3400_seed13_300s` | `urban_d_heavy` | ok | 53.788 | 18.400 | 39.794 | 6 | 3.216 |
