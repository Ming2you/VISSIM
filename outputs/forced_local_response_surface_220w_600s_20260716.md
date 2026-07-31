# Forced local response surface - 220w 600s

Demand: urban=1430 vph, freeway=3721 vph, seed=13, control_interval=180s, pulse=none.
The baseline is forced fixed57. Positive delta means worse than baseline.

| rank | case | command | TTT veh-h | delta TTT | stopped veh-h | delta stopped | speed | VSL | D rate | D green | signal major/minor | pred total abs | pred urban q+storage abs |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `fixed57` | baseline VSL120, D open, signal 57/57 | 134.961 | 0.000 (+0.000%) | 31.701 | 0.000 (+0.000%) | 46.921 | 120.0 | 1414.0 | 10.0 | 57.0/57.0 | 236.8 | 76.7 |
| 2 | `ramp_d1364` | D ramp release 1414 -> 1364 vph | 135.504 | 0.543 (+0.402%) | 32.122 | 0.421 (+1.327%) | 46.751 | 120.0 | 1364.0 | 6.0 | 57.0/57.0 | 236.1 | 76.6 |
| 3 | `signal_major62` | signals 57/57 -> 62/52 | 135.992 | 1.031 (+0.764%) | 32.376 | 0.675 (+2.129%) | 46.557 | 120.0 | 1414.0 | 10.0 | 62.0/52.0 | 228.5 | 66.2 |
| 4 | `ramp_d1253` | D ramp release 1414 -> 1253 vph | 136.008 | 1.047 (+0.776%) | 32.040 | 0.339 (+1.069%) | 46.583 | 120.0 | 1253.0 | 4.0 | 57.0/57.0 | 246.6 | 80.6 |
| 5 | `vsl110` | VSL 120 -> 110 kph | 136.126 | 1.165 (+0.863%) | 32.837 | 1.136 (+3.584%) | 46.860 | 110.0 | 1414.0 | 10.0 | 57.0/57.0 | 219.6 | 68.8 |
| 6 | `signal_minor62` | signals 57/57 -> 52/62 | 136.540 | 1.579 (+1.170%) | 33.943 | 2.242 (+7.071%) | 46.312 | 120.0 | 1414.0 | 10.0 | 52.0/62.0 | 237.7 | 77.4 |
| 7 | `vsl100` | VSL 120 -> 100 kph | 137.264 | 2.303 (+1.706%) | 33.567 | 1.865 (+5.884%) | 46.907 | 100.0 | 1414.0 | 10.0 | 57.0/57.0 | 235.1 | 51.3 |

Interpretation:
- Forced diagnostics bypass ramp-release and post-guard safety policy guards.
- Use this as a local plant-response table, not as an optimized policy comparison.
- If every perturbation is worse than fixed57, the useful actuation region around the current baseline is very narrow.
