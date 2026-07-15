# Vissim MPC tuning summary

- Warmup excluded from vehicle-hour metrics: 120 s
- Case count: 5
- Completed usable cases: 5
- Failed/empty cases: 0
- Current best group: `07_boundary_queue_priority / `
- Best mean total vehicle-hours: 165.881
- Best mean stopped vehicle-hours: 74.307

## Group ranking

| rank | tuning | demand | cases | total veh-h | stopped veh-h | speed kph | VSL step | ramp step | signal step | fallback rows |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `07_boundary_queue_priority` | `` | 1 | 165.881 | 74.307 | 27.439 | 0.000 | 0.000 | 0.000 | 0 |
| 2 | `08_mfd_strong` | `` | 1 | 165.881 | 74.307 | 27.439 | 0.000 | 0.000 | 0.000 | 0 |
| 3 | `00_calibrated_base` | `` | 1 | 165.889 | 74.489 | 27.390 | 0.000 | 0.000 | 0.000 | 0 |
| 4 | `05_activation_early` | `` | 1 | 165.889 | 74.489 | 27.390 | 0.000 | 0.000 | 0.000 | 0 |
| 5 | `04_smooth_low` | `` | 1 | 166.125 | 74.331 | 27.367 | 0.000 | 0.000 | 0.000 | 0 |

## Case-level notes

| case | demand | status | total veh-h | stopped veh-h | mean speed | decisions | decision wall s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `mpc_00_calibrated_base_u2600_fw2400_seed13_600s` | `` | ok | 165.889 | 74.489 | 27.390 | 11 | 4.286 |
| `mpc_04_smooth_low_u2600_fw2400_seed13_600s` | `` | ok | 166.125 | 74.331 | 27.367 | 11 | 4.317 |
| `mpc_05_activation_early_u2600_fw2400_seed13_600s` | `` | ok | 165.889 | 74.489 | 27.390 | 11 | 4.264 |
| `mpc_07_boundary_queue_priority_u2600_fw2400_seed13_600s` | `` | ok | 165.881 | 74.307 | 27.439 | 11 | 4.303 |
| `mpc_08_mfd_strong_u2600_fw2400_seed13_600s` | `` | ok | 165.881 | 74.307 | 27.439 | 11 | 4.242 |
