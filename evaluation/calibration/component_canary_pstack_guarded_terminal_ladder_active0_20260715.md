# Component canary report

Canary components: `leader_hinge`, `np_deadband`, `leader_mfd_far`.

| decision dir | active decisions | recalib rate | mismatch max | wall mean/max | recommendation |
| --- | ---: | ---: | ---: | ---: | --- |
| `evaluation\runs\pstack_guarded_terminal_ladder_20260715\decisions_pstack_155w_guarded_terminal_seed13` | 11 | 0.000 | 0 | 21.423/23.676 | `canary_clean` |
| `evaluation\runs\pstack_guarded_terminal_ladder_20260715\decisions_pstack_190w_guarded_terminal_seed13` | 11 | 0.000 | 0 | 24.359/26.086 | `canary_clean` |
| `evaluation\runs\pstack_guarded_terminal_ladder_20260715\decisions_pstack_220w_guarded_terminal_seed13` | 11 | 0.000 | 0 | 24.501/25.847 | `canary_clean` |

Interpretation:

- `recalibrate_components` means at least half of the active decisions asked for recalibration, or the max fingerprint mismatch covers all three canary components.
- This script diagnoses the drift; it does not silently change controller parameters.
