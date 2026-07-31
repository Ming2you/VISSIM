# P-Stack non-improvement audit - 2026-07-18

Source run: `long_warmup1800_eval3600_220w_20260716`, seed=13, demand urban=1430 vph, freeway=3721 vph.
Evaluation window is 1800-5400s; P-Stack is active from 1800s after fixed57 warmup.

## Time-slice TTT

| window | fixed TTT | pstack TTT | delta | fixed stopped | pstack stopped | stopped delta | total veh delta | stopped veh delta | boundary delta | ramp delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `1800-2700` | 452.894 | 452.411 | -0.483 (-0.107%) | 240.176 | 240.557 | 0.381 (+0.158%) | -1.9 | 1.5 | 0.6 | 0.1 |
| `2700-3600` | 487.575 | 491.136 | 3.561 (+0.730%) | 264.924 | 269.825 | 4.901 (+1.850%) | 14.2 | 19.6 | 1.6 | 1.4 |
| `3600-4500` | 510.982 | 508.496 | -2.486 (-0.487%) | 288.421 | 283.054 | -5.367 (-1.861%) | -9.9 | -21.5 | 7.9 | 1.9 |
| `4500-5400` | 523.592 | 531.513 | 7.921 (+1.513%) | 304.808 | 315.814 | 11.006 (+3.611%) | 31.7 | 44.0 | 5.2 | 6.7 |

## P-Stack action by slice

| window | decisions | D rate mean/min | F rate mean | VSL mean | signal major/minor |
| --- | ---: | ---: | ---: | ---: | ---: |
| `1800-2700` | 5 | 1385.7/1378.7 | 237.1 | 120.0 | 57.0/57.0 |
| `2700-3600` | 5 | 1350.4/1343.3 | 237.1 | 120.0 | 57.0/57.0 |
| `3600-4500` | 5 | 1369.4/1343.3 | 237.1 | 120.0 | 57.0/57.0 |
| `4500-5400` | 5 | 1357.4/1343.3 | 237.1 | 120.0 | 57.0/57.0 |

## Decision metadata summary

- controller variants: `stackelberg-wu-metered`
- mean best objective: 279.883
- mean objective gap: 0.003
- mean best projected/realized N_P*: 959.964/959.964
- mean follower TTT base: 96.088
- mean density/storage/boundary penalties: 4.906/5.774/9.177
- fallback guard active/rejected/selected no-control: 1.000/0.000/0.000

## P-Stack signed prediction errors

| metric | n | mean signed | mean abs | min signed | max signed |
| --- | ---: | ---: | ---: | ---: | ---: |
| `freeway_total_veh` | 20 | 34.7 | 36.5 | -18.2 | 104.6 |
| `protected_accumulation_veh` | 20 | -384.7 | 384.7 | -489.0 | -270.8 |
| `total_model_vehicles` | 20 | -247.7 | 247.7 | -371.0 | -132.0 |
| `urban_link_occupancy_total_veh` | 20 | -262.1 | 262.1 | -365.0 | -162.9 |
| `urban_movement_queue_total_veh` | 20 | -20.3 | 50.4 | -108.8 | 78.4 |
| `urban_queue_plus_link_occupancy_total_veh` | 20 | 220.4 | 220.4 | 118.9 | 335.9 |

Initial diagnosis:
- The long-run loss is concentrated after the first evaluation slice, not at activation.
- P-Stack mainly changes D ramp metering; VSL and signal commands remain effectively fixed.
- The controller reduces total prediction abs error while badly missing protected accumulation and urban queue+storage components.
- That means the scalar fit and the control objective are not aligned with the VISSIM TTT/stopped-delay objective.
