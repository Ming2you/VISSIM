# Vissim MPC tuning summary

- Warmup excluded from vehicle-hour metrics: 60 s
- Case count: 4
- Completed usable cases: 4
- Failed/empty cases: 0
- Current best tuning: `00_calibrated_base`
- Best mean total vehicle-hours: 37.311
- Best mean stopped vehicle-hours: 6.307

## Group ranking

| rank | tuning | cases | total veh-h | stopped veh-h | speed kph | VSL step | ramp step | signal step | fallback rows |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `00_calibrated_base` | 1 | 37.311 | 6.307 | 54.625 | 0.000 | 0.000 | 0.000 | 0 |
| 2 | `01_freeway_priority` | 1 | 37.311 | 6.307 | 54.625 | 0.000 | 0.000 | 0.000 | 0 |
| 3 | `05_activation_early` | 1 | 37.311 | 6.307 | 54.625 | 0.000 | 0.000 | 0.000 | 0 |
| 4 | `04_smooth_low` | 1 | 38.249 | 7.179 | 52.951 | 0.000 | 0.000 | 0.000 | 0 |

## Case-level notes

| case | status | total veh-h | stopped veh-h | mean speed | decisions | decision wall s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `mpc_00_calibrated_base_u1000_fw4200_seed13_300s` | ok | 37.311 | 6.307 | 54.625 | 6 | 3.818 |
| `mpc_01_freeway_priority_u1000_fw4200_seed13_300s` | ok | 37.311 | 6.307 | 54.625 | 6 | 3.897 |
| `mpc_04_smooth_low_u1000_fw4200_seed13_300s` | ok | 38.249 | 7.179 | 52.951 | 6 | 3.869 |
| `mpc_05_activation_early_u1000_fw4200_seed13_300s` | ok | 37.311 | 6.307 | 54.625 | 6 | 4.007 |
