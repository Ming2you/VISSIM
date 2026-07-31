# Real-World Peak-Hold Recovery 7200s Comparison

Network:
`network/real_world_gaepo_modi/modi_eval_rw_control_peakhold4500_recovery_20260729.inpx`

Runs:
- Baseline: `peakholdrec_fixed_no_7200s13`
- P-Stack: `peakholdrec_pstack_7200s13`
- Seed: 13
- Sim period: 7200 s
- Demand: original scale 1.0, INPX peak hold to 3600 s, recovery rows at 4500/5400/6300 s

Note: `peakholdrec_no_7200s13` is discarded because the earlier demand edit removed the 2700/3600 peak-hold rows.

## Main Metrics

| Metric | Baseline | P-Stack | Delta | Delta % |
|---|---:|---:|---:|---:|
| Total TTT (veh-h) | 6992.104 | 6845.021 | -147.083 | -2.104% |
| Urban vehicle-hours | 5124.660 | 4962.027 | -162.633 | -3.174% |
| Freeway vehicle-hours | 1818.403 | 1831.253 | +12.850 | +0.707% |
| Ramp vehicle-hours | 49.042 | 51.742 | +2.700 | +5.506% |
| Stopped vehicle-hours | 2697.080 | 2519.571 | -177.509 | -6.582% |
| Avg network speed (kph) | 34.062 | 34.981 | +0.919 | +2.698% |
| Avg freeway speed (kph) | 65.435 | 64.844 | -0.591 | -0.903% |
| Peak total vehicles | 4348 | 4201 | -147 | -3.381% |
| Peak stopped vehicles | 2276 | 2171 | -105 | -4.613% |
| Final total vehicles | 4340 | 4176 | -164 | -3.779% |
| Final stopped vehicles | 2240 | 2171 | -69 | -3.080% |

## Segment Metrics

| Segment | Time (s) | Baseline TTT | P-Stack TTT | TTT Delta | TTT Delta % | Baseline stopped h | P-Stack stopped h | Stopped Delta % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Build-up | 1-1800 | 992.671 | 981.129 | -11.542 | -1.163% | 221.697 | 207.371 | -6.462% |
| Peak hold | 1800-4500 | 2893.083 | 2850.542 | -42.542 | -1.470% | 998.492 | 937.475 | -6.111% |
| Recovery | 4500-6300 | 2046.583 | 1988.283 | -58.300 | -2.849% | 936.233 | 872.058 | -6.855% |
| Tail | 6300-7200 | 1059.767 | 1025.067 | -34.700 | -3.274% | 540.658 | 502.667 | -7.027% |

## P-Stack Action Summary

| Lever | Min | Mean | Max |
|---|---:|---:|---:|
| VSL speed (kph) | 80.0 | 106.935 | 120.0 |
| Ramp green (s) | 2.0 | 8.537 | 10.0 |
| Ramp rate field (vph) | 180.0 | 765.785 | 900.0 |
| Signal major green (s) | 20.0 | 45.527 | 56.0 |
| Signal minor green (s) | 56.0 | 66.060 | 90.0 |
| Offset (s) | 0.0 | 7.479 | 40.0 |

Decision wall time: average 19.171 s, max 35.429 s.

## Interpretation

P-Stack is no longer flat. It reduced total TTT by about 2.1% and stopped vehicle-hours by about 6.6%.
The benefit is smallest during build-up/peak hold and largest in recovery/tail, which suggests the controller is mainly helping discharge residual congestion rather than preventing the initial breakdown.

The tradeoff is visible: urban accumulation improves, while freeway and ramp vehicle-hours increase slightly. That matches the observed action pattern: VSL and ramp metering are used to protect/rebalance the network, with stronger stopped-vehicle gains than raw freeway TTT gains.
