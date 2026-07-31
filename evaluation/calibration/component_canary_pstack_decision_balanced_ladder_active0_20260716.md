# Component canary report

Canary components: `leader_hinge`, `np_deadband`, `leader_mfd_far`.

| decision dir | active decisions | recalib rate | mismatch max | wall mean/max | recommendation |
| --- | ---: | ---: | ---: | ---: | --- |
| `evaluation\runs\pstack_decision_balanced_ladder_20260716\decisions_pstack_155w_decision_balanced_seed13` | 11 | 0.000 | 0 | 21.456/22.769 | `canary_clean` |
| `evaluation\runs\pstack_decision_balanced_ladder_20260716\decisions_pstack_190w_decision_balanced_seed13` | 11 | 0.000 | 0 | 20.705/21.975 | `canary_clean` |
| `evaluation\runs\pstack_decision_balanced_ladder_20260716\decisions_pstack_220w_decision_balanced_seed13` | 11 | 0.000 | 0 | 21.143/22.434 | `canary_clean` |

Interpretation:

- `recalibrate_components` means at least half of the active decisions asked for recalibration, or the max fingerprint mismatch covers all three canary components.
- This script diagnoses the drift; it does not silently change controller parameters.
