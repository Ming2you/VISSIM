# Real-World Peak-Hold Recovery 7200s Demand 1.15 Comparison

Network: `network/real_world_gaepo_modi/modi_eval_rw_control_peakhold4500_recovery_20260729.inpx`

Runs:
- Baseline: `peakholdrec_d115_fixed_no_7200s13`
- Candidate: `peakholdrec_d115_pstack_7200s13`
- Note: Seed 13; sim 7200 s; original INPX peak-hold/recovery demand scaled in memory by 1.15

## Main Metrics

| Metric | Baseline | Candidate | Delta | Delta % |
|---|---:|---:|---:|---:|
| Total TTT (veh-h) | 7130.582 | 7006.048 | -124.533 | -1.746% |
| Urban vehicle-hours | 5227.132 | 5128.882 | -98.250 | -1.880% |
| Freeway vehicle-hours | 1853.383 | 1827.867 | -25.517 | -1.377% |
| Ramp vehicle-hours | 50.067 | 49.300 | -0.767 | -1.531% |
| Stopped vehicle-hours | 2764.550 | 2639.633 | -124.917 | -4.519% |
| Avg network speed (kph) | 33.467 | 34.193 | +0.726 | +2.169% |
| Avg freeway speed (kph) | 63.928 | 64.270 | +0.342 | +0.534% |
| Peak total vehicles | 4362.000 | 4278.000 | -84.000 | -1.926% |
| Peak stopped vehicles | 2297.000 | 2282.000 | -15.000 | -0.653% |
| Final total vehicles | 4300.000 | 4236.000 | -64.000 | -1.488% |
| Final stopped vehicles | 2222.000 | 2282.000 | +60.000 | +2.700% |

## Segment Metrics

| Segment | Time (s) | Baseline TTT | Candidate TTT | TTT Delta | TTT Delta % | Baseline stopped h | Candidate stopped h | Stopped Delta % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Build-up | 1-1800 | 1066.148 | 1049.332 | -16.817 | -1.577% | 239.283 | 221.283 | -7.522% |
| Peak hold | 1800-4500 | 2917.150 | 2873.567 | -43.583 | -1.494% | 1024.483 | 989.683 | -3.397% |
| Recovery | 4500-6300 | 2079.233 | 2041.133 | -38.100 | -1.832% | 960.633 | 907.900 | -5.489% |
| Tail | 6300-7200 | 1068.050 | 1042.017 | -26.033 | -2.437% | 540.150 | 520.767 | -3.589% |

## Candidate Action Summary

| Lever | Min | Mean | Max |
|---|---:|---:|---:|
| VSL speed (kph) | 120.000 | 120.000 | 120.000 |
| Ramp green (s) | 2.000 | 4.793 | 7.000 |
| Ramp rate field (vph) | 180.000 | 429.462 | 625.000 |
| Signal major green (s) | 22.000 | 24.439 | 57.000 |
| Signal minor green (s) | 57.000 | 87.727 | 90.000 |
| Offset (s) | 0.000 | 0.000 | 0.000 |

Decision wall time: average 2.400 s, max 3.475 s.

## Interpretation

The higher demand produced a stronger residual-congestion case. The candidate lowered total vehicle-hours and final accumulation, with the clearest TTT benefit in recovery/tail. Stopped vehicle-hours improved overall, but the final stopped count is slightly worse, so the controller is still shifting queue timing/location rather than fully discharging the network.
