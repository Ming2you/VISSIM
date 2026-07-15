# Vissim MPC tuning summary

- Warmup excluded from vehicle-hour metrics: 60 s
- Case count: 10
- Completed usable cases: 10
- Failed/empty cases: 0
- Current best group: `00_calibrated_base / urban_d_heavy`
- Best mean total vehicle-hours: 45.136
- Best mean stopped vehicle-hours: 11.425

## Group ranking

| rank | tuning | demand | cases | total veh-h | stopped veh-h | speed kph | VSL step | ramp step | signal step | fallback rows |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `00_calibrated_base` | `urban_d_heavy` | 1 | 45.136 | 11.425 | 46.427 | 0.000 | 0.000 | 0.000 | 0 |
| 2 | `00_calibrated_base` | `urban_f_heavy` | 1 | 46.369 | 11.994 | 45.928 | 0.000 | 0.000 | 0.000 | 0 |
| 3 | `00_calibrated_base` | `urban_west_heavy` | 1 | 50.508 | 14.996 | 42.163 | 0.000 | 0.000 | 0.000 | 0 |
| 4 | `00_calibrated_base` | `urban_east_heavy` | 1 | 51.875 | 16.097 | 42.434 | 0.000 | 0.000 | 0.000 | 0 |
| 5 | `00_calibrated_base` | `urban_north_heavy` | 1 | 52.011 | 16.593 | 39.227 | 0.000 | 0.000 | 0.000 | 0 |
| 6 | `00_calibrated_base` | `sym` | 1 | 58.406 | 18.219 | 39.927 | 0.000 | 0.000 | 0.000 | 0 |
| 7 | `00_calibrated_base` | `fw_wb_heavy` | 1 | 58.526 | 18.681 | 36.837 | 0.000 | 0.000 | 0.000 | 0 |
| 8 | `00_calibrated_base` | `fw_eb_heavy` | 1 | 58.800 | 18.836 | 36.908 | 0.000 | 0.000 | 0.000 | 0 |
| 9 | `00_calibrated_base` | `d_ramp_bias` | 1 | 64.326 | 27.565 | 30.852 | 0.000 | 0.000 | 0.000 | 0 |
| 10 | `00_calibrated_base` | `f_ramp_bias` | 1 | 65.688 | 27.631 | 30.808 | 0.000 | 0.000 | 0.000 | 0 |

## Case-level notes

| case | demand | status | total veh-h | stopped veh-h | mean speed | decisions | decision wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `mpc_00_calibrated_base_d_ramp_bias_u2200_fw3000_seed13_300s` | `d_ramp_bias` | ok | 64.326 | 27.565 | 30.852 | 6 | 4.333 |
| `mpc_00_calibrated_base_f_ramp_bias_u2200_fw3000_seed13_300s` | `f_ramp_bias` | ok | 65.688 | 27.631 | 30.808 | 6 | 3.694 |
| `mpc_00_calibrated_base_fw_eb_heavy_u2200_fw3000_seed13_300s` | `fw_eb_heavy` | ok | 58.800 | 18.836 | 36.908 | 6 | 4.031 |
| `mpc_00_calibrated_base_fw_wb_heavy_u2200_fw3000_seed13_300s` | `fw_wb_heavy` | ok | 58.526 | 18.681 | 36.837 | 6 | 4.063 |
| `mpc_00_calibrated_base_sym_u2200_fw3000_seed13_300s` | `sym` | ok | 58.406 | 18.219 | 39.927 | 6 | 3.775 |
| `mpc_00_calibrated_base_urban_d_heavy_u2200_fw3000_seed13_300s` | `urban_d_heavy` | ok | 45.136 | 11.425 | 46.427 | 6 | 3.976 |
| `mpc_00_calibrated_base_urban_east_heavy_u2200_fw3000_seed13_300s` | `urban_east_heavy` | ok | 51.875 | 16.097 | 42.434 | 6 | 4.014 |
| `mpc_00_calibrated_base_urban_f_heavy_u2200_fw3000_seed13_300s` | `urban_f_heavy` | ok | 46.369 | 11.994 | 45.928 | 6 | 4.005 |
| `mpc_00_calibrated_base_urban_north_heavy_u2200_fw3000_seed13_300s` | `urban_north_heavy` | ok | 52.011 | 16.593 | 39.227 | 6 | 3.960 |
| `mpc_00_calibrated_base_urban_west_heavy_u2200_fw3000_seed13_300s` | `urban_west_heavy` | ok | 50.508 | 14.996 | 42.163 | 6 | 3.989 |
