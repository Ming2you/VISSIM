# Real-world modi demand +15% P-Stack 4500s

Run completed on 2026-07-27.

## Run

- Run: `demand115_pstack_4500s13`
- Output directory: `evaluation/runs/rw_demand115_4500_20260727`
- Controller: `stackelberg`
- Demand profile: `evaluation/configs/demand_profiles/real_world_freeway_stress_extreme_20260725.csv`
- Demand scale: `1.15`
- Sim period: `4500 s`
- Control interval: `60 s`
- Seed: `13`
- Watchdog: no retry; attempt 1 completed
- Wall time: `30551 s`

## State-Integrated Metrics

| metric | value |
| --- | ---: |
| TTT | `4929.722 veh-h` |
| Freeway accumulation integral | `1907.773 veh-h` |
| Urban accumulation integral | `2991.948 veh-h` |
| Ramp accumulation integral | `30.000 veh-h` |
| Stopped accumulation integral | `1356.896 veh-h` |
| Avg mean speed | `34.22 km/h` |
| Avg freeway speed | `50.01 km/h` |
| Peak total vehicles | `5292` |
| Peak stopped vehicles | `1698` |
| Final total vehicles | `3077` |
| Final stopped vehicles | `1510` |

## Checkpoints

| sim_sec | total | urban | freeway | stopped | mean_kph | fw_kph |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 600 | 2834 | 1474 | 1349 | 457 | 41.28 | 53.12 |
| 1200 | 4036 | 2164 | 1842 | 722 | 35.87 | 43.78 |
| 1800 | 4706 | 2608 | 2075 | 1150 | 31.36 | 40.21 |
| 2400 | 5281 | 3170 | 2075 | 1505 | 28.73 | 38.37 |
| 3000 | 4748 | 3037 | 1686 | 1671 | 27.32 | 44.07 |
| 3600 | 4363 | 2834 | 1496 | 1556 | 29.33 | 45.64 |
| 4200 | 3325 | 2498 | 804 | 1488 | 30.71 | 71.00 |
| 4500 | 3077 | 2470 | 587 | 1510 | 28.82 | 78.34 |

## Actuation Audit

- Decision count: `76`
- Action rows: `vsl=5092`, `ramp_meter=608`, `signal=76`
- Readback errors: `0`
- VSL values used: `80, 100, 120 km/h`
- Ramp meter green values used: `2, 3, 4, 7, 8 s`
- Signal major green values used: `20.0, 20.509, 20.8, 24.848, 26.8, 56.0, 57.44 s`
- Signal offsets used: `0, 5, 10, 15, 20 s`

### Lever Movement Detail

| lever | actuator count | commanded range | dominant values | step changes | interpretation |
| --- | ---: | --- | --- | ---: | --- |
| VSL | `67` DSD/lane actuators | `80-120 km/h` | `100 km/h=66.2%`, `120 km/h=28.7%`, `80 km/h=5.1%` | `1465/5025 = 29.2%` | Active and read back correctly. Mostly moderate speed harmonization, not maximum restriction. |
| Ramp metering | `8` ramp controllers | `180-700 veh/h`; green `2-8 s` | green `3 s=30.3%`, `7 s=21.1%`, `8 s=18.4%`, `4 s=17.1%`, `2 s=13.2%` | rate `218/600 = 36.3%`; green `64/600 = 10.7%` | Actuator is alive, but many rate differences collapse to the same discrete green time. Direct ramp accumulation impact is small. |
| Signal green split | `1` signal controller | major `20-57.44 s`; minor `54.56-90 s` | major `20 s=72.4%`; minor `90 s=78.9%` | major `10/75 = 13.3%`; minor `7/75 = 9.3%` | The controller frequently hits green bounds, so this lever is active but often saturated. |
| Signal offset | `1` signal controller | `0-20 s` | `10 s=50.0%`, `0 s=30.3%`, `15 s=9.2%`, `5 s=7.9%`, `20 s=2.6%` | `24/75 = 32.0%` | Offset is changing, but with only one leveraged signal it is a weak progression lever. |

### Lever Movement By 600 s Window

| window end | VSL mean | VSL 80/100/120 share | ramp rate mean | ramp green mean | signal major/minor mean | offset mean | P-Stack - no total | P-Stack - no stopped | freeway speed delta |
| ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 600 | `107.9` | `0.0/60.5/39.5%` | `209.0` | `2.18` | `26.55/83.82` | `0.0` | `-86` | `-33` | `+3.3 km/h` |
| 1200 | `99.0` | `5.2/94.8/0.0%` | `261.3` | `3.00` | `20.00/90.00` | `10.0` | `-129` | `-134` | `+1.0 km/h` |
| 1800 | `99.0` | `10.0/85.2/4.8%` | `300.1` | `3.40` | `23.74/86.46` | `10.0` | `-43` | `+61` | `-2.4 km/h` |
| 2400 | `104.8` | `0.0/76.1/23.9%` | `632.5` | `7.10` | `24.85/87.15` | `10.0` | `-84` | `+16` | `+1.9 km/h` |
| 3000 | `100.0` | `9.6/80.9/9.6%` | `667.5` | `7.40` | `20.54/89.72` | `7.0` | `-313` | `-145` | `+3.7 km/h` |
| 3600 | `111.2` | `9.6/24.8/65.7%` | `648.0` | `7.40` | `23.60/86.60` | `13.0` | `-266` | `-361` | `+2.7 km/h` |
| 4200 | `109.1` | `4.8/44.8/50.4%` | `345.0` | `3.80` | `21.00/89.52` | `5.5` | `-464` | `-149` | `+19.7 km/h` |
| 4500 | `108.0` | `0.0/60.0/40.0%` | `380.0` | `4.00` | `20.00/90.00` | `0.0` | `-516` | `-113` | `+19.0 km/h` |

## Prediction Audit

- Mean prediction total model vehicle abs error: `73.197`
- Mean prediction protected accumulation abs error: `12.339`
- Mean prediction freeway total abs error: `103.475`
- Mean decision wall time: `21.403 s`

## Baseline Comparison

The matching `demand +15%, 4500s, no-control` baseline was run on 2026-07-27 to 2026-07-28.

| metric | no-control | P-Stack | delta | delta % |
| --- | ---: | ---: | ---: | ---: |
| TTT | `5145.555 veh-h` | `4929.722 veh-h` | `-215.833 veh-h` | `-4.19%` |
| Freeway accumulation integral | `2009.790 veh-h` | `1907.773 veh-h` | `-102.017 veh-h` | `-5.08%` |
| Urban accumulation integral | `3105.082 veh-h` | `2991.948 veh-h` | `-113.134 veh-h` | `-3.64%` |
| Ramp accumulation integral | `30.683 veh-h` | `30.000 veh-h` | `-0.683 veh-h` | `-2.23%` |
| Stopped accumulation integral | `1499.788 veh-h` | `1356.896 veh-h` | `-142.892 veh-h` | `-9.53%` |
| Avg mean speed | `32.52 km/h` | `34.22 km/h` | `+1.70 km/h` | `+5.23%` |
| Avg freeway speed | `45.77 km/h` | `50.01 km/h` | `+4.24 km/h` | `+9.27%` |
| Peak total vehicles | `5445` | `5292` | `-153` | `-2.81%` |
| Peak stopped vehicles | `1929` | `1698` | `-231` | `-11.98%` |
| Final total vehicles | `3593` | `3077` | `-516` | `-14.36%` |
| Final stopped vehicles | `1623` | `1510` | `-113` | `-6.96%` |

## Baseline Checkpoints

| sim_sec | no total | P total | no stopped | P stopped | no mean kph | P mean kph | no fw kph | P fw kph |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 600 | 2920 | 2834 | 490 | 457 | 40.58 | 41.28 | 49.86 | 53.12 |
| 1200 | 4165 | 4036 | 856 | 722 | 35.58 | 35.87 | 42.80 | 43.78 |
| 1800 | 4749 | 4706 | 1089 | 1150 | 32.34 | 31.36 | 42.60 | 40.21 |
| 2400 | 5365 | 5281 | 1489 | 1505 | 28.10 | 28.73 | 36.45 | 38.37 |
| 3000 | 5061 | 4748 | 1816 | 1671 | 26.33 | 27.32 | 40.38 | 44.07 |
| 3600 | 4629 | 4363 | 1917 | 1556 | 25.15 | 29.33 | 42.90 | 45.64 |
| 4200 | 3789 | 3325 | 1637 | 1488 | 27.11 | 30.71 | 51.34 | 71.00 |
| 4500 | 3593 | 3077 | 1623 | 1510 | 29.32 | 28.82 | 59.34 | 78.34 |

## Interpretation

P-Stack did not radically transform the run, but under demand +15% it produced a real and consistent improvement. The strongest effect is not early free-flow control; it appears in the congested middle-to-late window, especially around 3000-4200 s, where stopped vehicles and residual accumulation remain lower than no-control.
