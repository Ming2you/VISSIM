# Vissim MPC tuning summary

- Warmup excluded from vehicle-hour metrics: 60 s
- Case count: 7
- Completed usable cases: 7
- Failed/empty cases: 0
- Current best tuning: `04_smooth_low`
- Best mean total vehicle-hours: 63.057
- Best mean stopped vehicle-hours: 23.790

## Group ranking

| rank | tuning | cases | total veh-h | stopped veh-h | speed kph | VSL step | ramp step | signal step | fallback rows |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `04_smooth_low` | 1 | 63.057 | 23.790 | 33.846 | 0.000 | 0.000 | 0.000 | 0 |
| 2 | `00_calibrated_base` | 1 | 63.067 | 23.962 | 33.762 | 0.000 | 0.000 | 0.000 | 0 |
| 3 | `01_freeway_priority` | 1 | 63.067 | 23.962 | 33.762 | 0.000 | 0.000 | 0.000 | 0 |
| 4 | `02_urban_priority` | 1 | 63.067 | 23.962 | 33.762 | 0.000 | 0.000 | 0.000 | 0 |
| 5 | `03_smooth_high` | 1 | 63.067 | 23.962 | 33.762 | 0.000 | 0.000 | 0.000 | 0 |
| 6 | `05_activation_early` | 1 | 63.067 | 23.962 | 33.762 | 0.000 | 0.000 | 0.000 | 0 |
| 7 | `06_activation_late` | 1 | 63.067 | 23.962 | 33.762 | 0.000 | 0.000 | 0.000 | 0 |

## Case-level notes

| case | status | total veh-h | stopped veh-h | mean speed | decisions | decision wall s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `mpc_00_calibrated_base_u2600_fw2400_seed13_300s` | ok | 63.067 | 23.962 | 33.762 | 6 | 4.401 |
| `mpc_01_freeway_priority_u2600_fw2400_seed13_300s` | ok | 63.067 | 23.962 | 33.762 | 6 | 4.356 |
| `mpc_02_urban_priority_u2600_fw2400_seed13_300s` | ok | 63.067 | 23.962 | 33.762 | 6 | 4.250 |
| `mpc_03_smooth_high_u2600_fw2400_seed13_300s` | ok | 63.067 | 23.962 | 33.762 | 6 | 4.318 |
| `mpc_04_smooth_low_u2600_fw2400_seed13_300s` | ok | 63.057 | 23.790 | 33.846 | 6 | 4.228 |
| `mpc_05_activation_early_u2600_fw2400_seed13_300s` | ok | 63.067 | 23.962 | 33.762 | 6 | 4.247 |
| `mpc_06_activation_late_u2600_fw2400_seed13_300s` | ok | 63.067 | 23.962 | 33.762 | 6 | 4.228 |
