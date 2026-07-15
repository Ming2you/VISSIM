# Vissim MPC tuning summary

- Warmup excluded from vehicle-hour metrics: 60 s
- Case count: 1
- Completed usable cases: 1
- Failed/empty cases: 0
- Current best tuning: `00_calibrated_base`
- Best mean total vehicle-hours: 63.067
- Best mean stopped vehicle-hours: 23.962

## Group ranking

| rank | tuning | cases | total veh-h | stopped veh-h | speed kph | VSL step | ramp step | signal step | fallback rows |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `00_calibrated_base` | 1 | 63.067 | 23.962 | 33.762 | 0.000 | 0.000 | 0.000 | 0 |

## Case-level notes

| case | status | total veh-h | stopped veh-h | mean speed | decisions | decision wall s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `mpc_00_calibrated_base_u2600_fw2400_seed13_300s` | ok | 63.067 | 23.962 | 33.762 | 6 | 4.479 |
