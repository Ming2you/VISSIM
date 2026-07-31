# Safe component guard long warmup comparison (2026-07-18)

Demand: urban 1430 vph, freeway 3721 vph, seed 13. Warmup 1800s, evaluation 3600s.

| case | TTT veh-h | delta | stopped veh-h | delta stopped | D rate | pred total abs | pred protected abs | pred q+storage abs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed57 | 1975.043 | +0.000 (+0.000%) | 1098.329 | +0.000 (+0.000%) | 1414.000 | 379.894 | 184.583 | 126.633 |
| pstack_delayed | 1983.556 | +8.513 (+0.431%) | 1109.250 | +10.921 (+0.994%) | 1366.351 | 247.737 | 384.683 | 220.362 |
| pstack_safe_component_guard | 1974.564 | -0.479 (-0.024%) | 1097.036 | -1.293 (-0.118%) | 1414.000 | 44.782 | 43.549 | 40.761 |

## Safe Config Checks

- Eval controller status: ok
- Mean D ramp rate: 1414.000 vph
- Mean ramp guard adjusted count: 2.900
- No-control fallback count: 0
- Max calibrated queue/storage identity error: 0.000000 veh
