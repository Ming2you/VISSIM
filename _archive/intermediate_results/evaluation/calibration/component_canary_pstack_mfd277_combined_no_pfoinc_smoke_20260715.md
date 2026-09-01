# Component canary report

Canary components: `leader_hinge`, `np_deadband`, `leader_mfd_far`.

| decision dir | active decisions | recalib rate | mismatch max | wall mean/max | recommendation |
| --- | ---: | ---: | ---: | ---: | --- |
| `evaluation\runs\pstack_mfd277_combined_no_pfoinc_smoke_20260715\decisions_pstack_155w_mfd277_combined_no_pfoinc_smoke` | 11 | 1.000 | 3 | 19.927/22.248 | `recalibrate_components` |

Interpretation:

- `recalibrate_components` means at least half of the active decisions asked for recalibration, or the max fingerprint mismatch covers all three canary components.
- This script diagnoses the drift; it does not silently change controller parameters.
