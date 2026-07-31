# Real-World modi.inpx Demand 1.00, 8100 s Comparison

Run directory: `evaluation/runs/rw_demand100_8100_20260728`

Demand setting: original INPX demand, `DemandScale=1.0`, no demand profile.

Runs:

- No control: `demand100_no_stepwise_8100s13_r2`
- P-Stack: `demand100_pstack_8100s13`
- Seed: 13
- Sim period: 8100 s
- Control interval: 60 s

Operational note: no-control was completed with `ForceStepwise` after COM/background-run interference caused earlier continuous attempts to fail. P-Stack completed with the event-continuous controller path.

## Main Metrics

| Metric | No control | P-Stack | Delta | Delta % |
|---|---:|---:|---:|---:|
| Total TTT (veh-h) | 5747.879 | 5644.046 | -103.833 | -1.806% |
| Urban accumulation TTT (veh-h) | 4279.085 | 4168.535 | -110.550 | -2.583% |
| Freeway accumulation TTT (veh-h) | 1422.586 | 1429.078 | +6.492 | +0.456% |
| Ramp accumulation TTT (veh-h) | 46.208 | 46.433 | +0.225 | +0.487% |
| Stopped vehicle-hours | 2213.305 | 2104.438 | -108.867 | -4.919% |
| Time-weighted mean speed (kph) | 34.646 | 35.329 | +0.683 | +1.971% |
| Time-weighted freeway speed (kph) | 74.747 | 74.279 | -0.468 | -0.626% |
| Peak total vehicles | 3785 | 3667 | -118 | -3.118% |
| Peak stopped vehicles | 1406 | 1246 | -160 | -11.380% |
| Final total vehicles at 8100 s | 2117 | 2159 | +42 | +1.984% |
| Final stopped vehicles at 8100 s | 1095 | 1139 | +44 | +4.018% |

## Segment Breakdown

| Segment (s) | No-control TTT | P-Stack TTT | TTT Delta | TTT Delta % | Stopped VH Delta | Stopped VH Delta % |
|---|---:|---:|---:|---:|---:|---:|
| 1-1800 | 992.67 | 981.49 | -11.18 | -1.13% | -14.52 | -6.55% |
| 1800-3600 | 1780.68 | 1729.82 | -50.86 | -2.86% | -67.03 | -11.80% |
| 3600-5400 | 1350.63 | 1297.85 | -52.78 | -3.91% | -35.40 | -5.78% |
| 5400-7200 | 1087.87 | 1091.88 | +4.01 | +0.37% | -0.56 | -0.10% |
| 7200-8100 | 536.03 | 543.02 | +6.98 | +1.30% | +8.64 | +3.21% |
| 1-4500 | 3526.70 | 3429.31 | -97.38 | -2.76% | -113.30 | -10.17% |
| 4500-8100 | 2221.18 | 2214.73 | -6.45 | -0.29% | +4.43 | +0.40% |

## Checkpoints

| t (s) | No total | P total | Delta total | No stopped | P stopped | Delta stopped | No FW speed | P FW speed |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1200 | 2467 | 2490 | +23 | 609 | 556 | -53 | 70.65 | 67.28 |
| 1800 | 3260 | 3268 | +8 | 836 | 766 | -70 | 58.26 | 56.40 |
| 2400 | 3713 | 3667 | -46 | 1087 | 1007 | -80 | 60.07 | 63.38 |
| 3000 | 3457 | 3371 | -86 | 1330 | 1151 | -179 | 63.10 | 61.88 |
| 3600 | 3461 | 3356 | -105 | 1406 | 1244 | -162 | 64.92 | 64.11 |
| 4200 | 2825 | 2674 | -151 | 1270 | 1123 | -147 | 78.14 | 77.50 |
| 4500 | 2849 | 2693 | -156 | 1269 | 1201 | -68 | 78.46 | 76.38 |
| 5400 | 2169 | 2168 | -1 | 1156 | 1162 | +6 | 82.84 | 80.78 |
| 6060 | 2194 | 2203 | +9 | 1013 | 1033 | +20 | 73.34 | 73.85 |
| 6600 | 2231 | 2203 | -28 | 1121 | 1098 | -23 | 87.87 | 90.40 |
| 7200 | 2129 | 2155 | +26 | 1086 | 1145 | +59 | 86.39 | 85.49 |
| 8100 | 2117 | 2159 | +42 | 1095 | 1139 | +44 | 80.26 | 82.30 |

## Lever Movement

P-Stack action rows: 10336.

| Lever kind | Rows | Observed range / values |
|---|---:|---|
| VSL | 9112 | 80-120 kph; counts: 120 kph = 6563, 100 kph = 2138, 80 kph = 411 |
| Ramp meter | 1088 | 180-900 vph; counts: 900 = 872, 625 = 176, 675 = 8, 712.5 = 16, 180 = 16 |
| Signal | 136 | one signal controller (`SC 1`), major green 20-56 s, offset 0-20 s |

Selected action checkpoints:

| t (s) | VSL values | Ramp meter values | Signal sample |
|---:|---|---|---|
| 1 | 120/100 | 180 | SC1 green 56, offset 0 |
| 1200 | 120 | 900 | SC1 green 56, offset 0 |
| 1800 | 100 | 900 | SC1 green 44, offset 0 |
| 2400 | 100/80 | 625 | SC1 green 44, offset 0 |
| 3000 | 100/80 | 625 | SC1 green 56, offset 0 |
| 3600 | 100 | 625 | SC1 green 56, offset 0 |
| 4200 | 100 | 625 | SC1 green 56, offset 0 |
| 4500 | 120 | 900 | SC1 green 56, offset 0 |
| 5400 | 120 | 900 | SC1 green 56, offset 0 |
| 7200 | 120 | 900 | SC1 green 56, offset 0 |
| 8100 | 120 | 900 | SC1 green 56, offset 0 |

## Interpretation

The original demand is congested enough to matter. No-control reaches 1406 stopped vehicles around 3600 s and still has 1095 stopped vehicles at 8100 s.

P-Stack is doing useful work, but mostly in the front/middle of the run. From 1-4500 s it reduces TTT by 2.76% and stopped vehicle-hours by 10.17%. After 5400 s, the benefit mostly disappears and the final tail is slightly worse.

This suggests the current controller is not inactive; the levers move and reduce the peak queue. The bigger issue is alignment with the late residual urban bottleneck. VSL and ramp metering affect the freeway/entry side, while the signal authority currently appears to be only one signal controller. Once the freeway recovers, the remaining urban stopped queue is not strongly cleared by the available mapped levers, so the 8100 s total improvement stays modest.
