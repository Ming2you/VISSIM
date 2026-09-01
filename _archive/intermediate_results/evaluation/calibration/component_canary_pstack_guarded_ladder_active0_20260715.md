# Component canary report

Canary components: `leader_hinge`, `np_deadband`, `leader_mfd_far`.

| decision dir | active decisions | recalib rate | mismatch max | wall mean/max | recommendation |
| --- | ---: | ---: | ---: | ---: | --- |
| `evaluation\runs\pstack_guarded_ladder_20260715\decisions_pstack_155w_guarded_seed13` | 11 | 1.000 | 3 | 21.361/23.632 | `recalibrate_components` |
| `evaluation\runs\pstack_guarded_ladder_20260715\decisions_pstack_190w_guarded_seed13` | 11 | 1.000 | 3 | 23.909/25.816 | `recalibrate_components` |
| `evaluation\runs\pstack_guarded_ladder_20260715\decisions_pstack_220w_guarded_seed13` | 11 | 1.000 | 3 | 24.090/25.551 | `recalibrate_components` |

Interpretation:

- `recalibrate_components` means at least half of the active decisions asked for recalibration, or the max fingerprint mismatch covers all three canary components.
- This script diagnoses the drift; it does not silently change controller parameters.
