# Local response surface - 220w 600s

Demand: urban=1430 vph, freeway=3721 vph, seed=13, control_interval=180s, pulse=none.
The baseline is forced fixed57. Positive delta means worse than baseline.

| rank | case | command | TTT veh-h | delta TTT | stopped veh-h | delta stopped | speed | VSL | D rate | D green | signal major/minor | pred total abs | pred urban q+storage abs |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `fixed57` | baseline VSL120, D open, signal 57/57 | 134.961 | 0.000 (+0.000%) | 31.701 | 0.000 (+0.000%) | 46.921 | 120.0 | 1414.0 | 10.0 | 57.0/57.0 | 169.6 | 57.2 |
| 2 | `ramp_d1364` | D ramp release 1414 -> 1364 vph | 134.961 | 0.000 (+0.000%) | 31.701 | 0.000 (+0.000%) | 46.921 | 120.0 | 1414.0 | 10.0 | 57.0/57.0 | 169.6 | 57.2 |
| 3 | `ramp_d1253` | D ramp release 1414 -> 1253 vph | 134.961 | 0.000 (+0.000%) | 31.701 | 0.000 (+0.000%) | 46.921 | 120.0 | 1414.0 | 10.0 | 57.0/57.0 | 169.6 | 57.2 |
| 4 | `vsl110` | VSL 120 -> 110 kph | 134.961 | 0.000 (+0.000%) | 31.701 | 0.000 (+0.000%) | 46.921 | 120.0 | 1414.0 | 10.0 | 57.0/57.0 | 169.6 | 57.2 |
| 5 | `vsl100` | VSL 120 -> 100 kph | 134.961 | 0.000 (+0.000%) | 31.701 | 0.000 (+0.000%) | 46.921 | 120.0 | 1414.0 | 10.0 | 57.0/57.0 | 169.6 | 57.2 |
| 6 | `signal_minor62` | signals 57/57 -> 52/62 | 134.961 | 0.000 (+0.000%) | 31.701 | 0.000 (+0.000%) | 46.921 | 120.0 | 1414.0 | 10.0 | 57.0/57.0 | 169.6 | 57.2 |
| 7 | `signal_major62` | signals 57/57 -> 62/52 | 136.261 | 1.300 (+0.963%) | 32.819 | 1.118 (+3.527%) | 46.514 | 120.0 | 1414.0 | 10.0 | 58.2/55.8 | 174.2 | 57.3 |

Interpretation:
- Use this as a local plant-response table, not as an optimized policy comparison.
- If every perturbation is worse than fixed57, the useful actuation region around the current baseline is very narrow.
