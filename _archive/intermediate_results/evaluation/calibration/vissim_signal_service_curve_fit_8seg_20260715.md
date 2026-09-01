# Vissim signal service-curve fit

- Batch: `evaluation\runs\calibration_signal_8seg_watchdog_20260715`
- Warmup: `300.0` sec
- Min discharge count per aggregated case: `10.0`
- Policy: `keep_scalar_1800_veh_h_approach_and_6s_lost_time`
- Reason: Signal discharge logs do not identify enough saturated approaches; store per-approach values as diagnostics only.

| approach | status | usable / total | green levels | q_sat rec | lost rec | p85 direct | fit q_sat | fit lost | R² |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `A_L1` | `upper_envelope_only` | 12 / 12 | 4 | 1973.1 | 6.0 | 1973.1 | 356.9 | -158.8 | 0.019 |
| `A_L3` | `upper_envelope_only` | 12 / 12 | 4 | 2482.1 | 6.0 | 2482.1 | 1898.6 | -5.6 | 0.405 |
| `A_L6` | `upper_envelope_only` | 12 / 12 | 4 | 3864.7 | 6.0 | 3864.7 | 2487.7 | -14.2 | 0.373 |
| `A_L8` | `upper_envelope_only` | 12 / 12 | 4 | 863.3 | 6.0 | 863.3 | 196.6 | -101.2 | 0.034 |
| `B_L12` | `upper_envelope_only` | 12 / 12 | 4 | 3896.1 | 6.0 | 3896.1 | -405.2 | 0.0 | 0.014 |
| `B_L14` | `upper_envelope_only` | 12 / 12 | 4 | 667.0 | 6.0 | 667.0 | 523.7 | -4.9 | 0.160 |
| `B_L5` | `underfed_or_unstable` | 12 / 12 | 4 | 4775.0 | 6.0 | 4775.0 | 912.0 | -154.3 | 0.045 |
| `B_L9` | `valid_regression` | 12 / 12 | 4 | 2065.6 | 7.5 | 2388.0 | 2065.6 | 7.5 | 0.414 |
| `C_L11` | `upper_envelope_only` | 12 / 12 | 4 | 3144.8 | 6.0 | 3144.8 | 714.1 | -117.0 | 0.120 |
| `C_L15` | `upper_envelope_only` | 12 / 12 | 4 | 2624.2 | 6.0 | 2624.2 | 2145.9 | 3.5 | 0.329 |
| `C_L18` | `upper_envelope_only` | 12 / 12 | 4 | 1732.9 | 6.0 | 1732.9 | 869.3 | -29.3 | 0.194 |
| `C_L20` | `upper_envelope_only` | 12 / 12 | 4 | 978.4 | 6.0 | 978.4 | 211.0 | -122.1 | 0.017 |
| `D_L21` | `upper_envelope_only` | 12 / 12 | 4 | 2032.4 | 6.0 | 2032.4 | 760.0 | -51.6 | 0.111 |
| `D_L24` | `upper_envelope_only` | 12 / 12 | 4 | 977.2 | 6.0 | 977.2 | 338.8 | -57.4 | 0.067 |
| `D_L26` | `upper_envelope_only` | 12 / 12 | 4 | 1277.8 | 6.0 | 1277.8 | -136.4 | 0.0 | 0.005 |
| `D_L7` | `upper_envelope_only` | 12 / 12 | 4 | 1163.4 | 6.0 | 1163.4 | 593.6 | -28.9 | 0.092 |
| `F_L19` | `upper_envelope_only` | 12 / 12 | 4 | 1234.0 | 6.0 | 1234.0 | 544.9 | -26.4 | 0.139 |
| `F_L27` | `upper_envelope_only` | 12 / 12 | 4 | 2308.0 | 6.0 | 2308.0 | 1092.9 | -26.3 | 0.170 |
| `F_L30` | `upper_envelope_only` | 12 / 12 | 4 | 2316.4 | 6.0 | 2316.4 | 521.0 | -101.7 | 0.042 |
| `F_L32` | `upper_envelope_only` | 11 / 12 | 4 | 897.1 | 6.0 | 897.1 | 487.5 | -7.6 | 0.121 |

## Validation caveat

This fit uses stopline discharge only. It does not directly observe an approach queue/presence state during the green, so under-fed approaches can still pass through the upper-envelope calculation. Per-approach values should not be promoted into controller service curves unless future saturated approach runs confirm queue persistence and monotone green-to-discharge behavior.
