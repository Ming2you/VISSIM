# Prediction-response calibrated validation - 220w 600s

Demand: urban=1430 vph, freeway=3721 vph, seed=13, control_interval=180s, pulse=none.

| case | TTT veh-h | delta TTT | stopped veh-h | delta stopped | mean speed | mean VSL | mean ramp rate | signal major/minor | pred total abs | pred protected abs | pred freeway abs | pred urban q+storage abs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `fixed57` | 134.961 | +0.00% | 31.701 | +0.00% | 46.921 | 120.0 | 825.5 | 57.0/57.0 | 169.6 | 133.1 | 25.9 | 57.2 |
| `pstack_prcal` | 134.963 | +0.00% | 31.733 | +0.10% | 46.896 | 120.0 | 807.5 | 57.0/57.0 | 168.1 | 132.8 | 27.3 | 57.0 |

Notes:
- The candidate uses `urban_avg_speed_km_h=130`, `freeway_total_scale=1.1`, and `urban_queue_plus_storage_scale=0.7`.
- Prediction metrics are one-step component errors stored in adapter action JSONs.
