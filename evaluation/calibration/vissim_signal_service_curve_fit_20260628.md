# Vissim signal service-curve fit

- Batch: `evaluation\runs\calibration_signal_vector_20260626`
- Warmup: `300.0` sec
- Min discharge count per aggregated case: `10.0`
- Policy: `keep_scalar_1800_veh_h_approach_and_6s_lost_time`
- Reason: Signal discharge logs do not identify enough saturated approaches; store per-approach values as diagnostics only.

| approach | status | usable / total | green levels | q_sat rec | lost rec | p85 direct | fit q_sat | fit lost | R² |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `A_L1` | `upper_envelope_only` | 12 / 12 | 4 | 2373.7 | 6.0 | 2373.7 | 729.3 | -69.5 | 0.052 |
| `A_L3` | `upper_envelope_only` | 12 / 12 | 4 | 3072.3 | 6.0 | 3072.3 | 2414.2 | -2.1 | 0.540 |
| `A_L6` | `upper_envelope_only` | 12 / 12 | 4 | 3849.3 | 6.0 | 3849.3 | 1729.7 | -40.6 | 0.316 |
| `A_L8` | `underfed_or_unstable` | 12 / 12 | 4 | 433.4 | 6.0 | 433.4 | 512.6 | 18.1 | 0.251 |
| `B_L12` | `upper_envelope_only` | 12 / 12 | 4 | 3896.9 | 6.0 | 3896.9 | -223.7 | 0.0 | 0.006 |
| `B_L14` | `upper_envelope_only` | 10 / 12 | 4 | 507.2 | 6.0 | 507.2 | -129.9 | 0.0 | 0.038 |
| `B_L5` | `underfed_or_unstable` | 12 / 12 | 4 | 5219.4 | 6.0 | 5219.4 | 93.1 | -2125.1 | 0.000 |
| `B_L9` | `upper_envelope_only` | 12 / 12 | 4 | 2524.8 | 6.0 | 2524.8 | 1589.6 | -13.4 | 0.436 |
| `C_L11` | `upper_envelope_only` | 12 / 12 | 4 | 2288.9 | 6.0 | 2288.9 | 929.2 | -54.1 | 0.260 |
| `C_L15` | `upper_envelope_only` | 12 / 12 | 4 | 3188.3 | 6.0 | 3188.3 | 2635.4 | 6.0 | 0.224 |
| `C_L18` | `upper_envelope_only` | 12 / 12 | 4 | 2026.8 | 6.0 | 2026.8 | 1183.5 | -15.1 | 0.334 |
| `C_L20` | `upper_envelope_only` | 12 / 12 | 4 | 619.6 | 6.0 | 619.6 | 382.2 | -4.7 | 0.253 |
| `D_L21` | `upper_envelope_only` | 12 / 12 | 4 | 2413.0 | 6.0 | 2413.0 | 1309.1 | -17.8 | 0.263 |
| `D_L24` | `upper_envelope_only` | 12 / 12 | 4 | 1259.3 | 6.0 | 1259.3 | 590.3 | -18.9 | 0.153 |
| `D_L26` | `underfed_or_unstable` | 4 / 12 | 2 | 213.1 | 6.0 | 213.1 | 90.5 | -50.1 | 0.267 |
| `D_L7` | `upper_envelope_only` | 12 / 12 | 4 | 1348.6 | 6.0 | 1348.6 | 30.6 | -1652.4 | 0.000 |
| `F_L19` | `upper_envelope_only` | 12 / 12 | 4 | 1452.2 | 6.0 | 1452.2 | 360.0 | -83.7 | 0.060 |
| `F_L27` | `upper_envelope_only` | 12 / 12 | 4 | 2457.9 | 6.0 | 2457.9 | 1753.5 | -2.2 | 0.465 |
| `F_L30` | `upper_envelope_only` | 12 / 12 | 4 | 2418.0 | 6.0 | 2418.0 | 987.5 | -40.1 | 0.153 |
| `F_L32` | `insufficient_observations` | 0 / 12 | 0 | 0.0 | 6.0 | 0.0 | 0.0 | 0.0 | 0.000 |

## Validation caveat

This fit uses stopline discharge only. It does not directly observe an approach queue/presence state during the green, so under-fed approaches can still pass through the upper-envelope calculation. Per-approach values should not be promoted into controller service curves unless future saturated approach runs confirm queue persistence and monotone green-to-discharge behavior.
