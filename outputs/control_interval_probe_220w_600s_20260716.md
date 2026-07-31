# P-Stack control interval probe - 220w 600s

Demand: urban=1430 vph, freeway=3721 vph, seed=13, pulse=none.
Positive delta means worse than fixed57 at the same control interval.

| interval | controller | decisions | TTT veh-h | delta vs fixed | stopped veh-h | delta stopped | mean speed | pred total abs | pred protected abs | pred freeway abs | pred urban q+storage abs | VSL | D rate | signal major/minor |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 180 | `fixed57` | 4 | 134.961 | 0.000 (+0.000%) | 31.701 | 0.000 (+0.000%) | 46.921 | 169.6 | 133.1 | 25.9 | 57.2 | 120.0 | 1414.0 | 57.0/57.0 |
| 180 | `pstack_prcal` | 4 | 134.963 | 0.001 (+0.001%) | 31.733 | 0.032 (+0.101%) | 46.896 | 168.1 | 132.8 | 27.3 | 57.0 | 120.0 | 1378.0 | 57.0/57.0 |
| 90 | `fixed57` | 7 | 134.961 | 0.000 (+0.000%) | 31.701 | 0.000 (+0.000%) | 46.921 | 195.1 | 62.1 | 51.6 | 49.1 | 120.0 | 1414.0 | 57.0/57.0 |
| 90 | `pstack_prcal` | 7 | 135.706 | 0.744 (+0.552%) | 32.362 | 0.661 (+2.085%) | 46.654 | 164.7 | 127.1 | 51.0 | 68.3 | 120.0 | 1379.6 | 57.0/57.0 |
| 60 | `fixed57` | 11 | 134.961 | 0.000 (+0.000%) | 31.701 | 0.000 (+0.000%) | 46.921 | 183.4 | 49.0 | 57.9 | 59.6 | 120.0 | 1414.0 | 57.0/57.0 |
| 60 | `pstack_prcal` | 11 | 135.953 | 0.992 (+0.735%) | 32.756 | 1.054 (+3.325%) | 46.522 | 176.0 | 67.3 | 59.5 | 68.0 | 120.0 | 1378.1 | 57.0/57.0 |

Verdict:
- Best overall TTT: `fixed57` at 180s (134.961 veh-h).
- Best P-Stack TTT: 180s (134.963 veh-h), +0.001% vs same-interval fixed57.
- Shorter control intervals did not rescue TTT if P-Stack remains above the same-interval fixed baseline.
