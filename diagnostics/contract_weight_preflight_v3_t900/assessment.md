# Same-state objective-weight decision comparison

All four full MPC decisions pass the objective and actuation contract checks on the same actual 900-second input. These are internal model predictions. VISSIM outcomes and a final weight remain pending.

| Reward seconds/vehicle | Follower TTT [veh h] | Follower TTD [veh] | Follower J [veh h] | Leader held J [veh h] | Wall [s] |
|---:|---:|---:|---:|---:|---:|
| 0 | 311.331237 | 1456.188515 | 311.331237 | 311.252664 | 182.91 |
| 60 | 311.185438 | 1460.897530 | 286.837146 | 286.768408 | 218.31 |
| 150 | 310.884974 | 1469.454464 | 249.657705 | 249.397701 | 219.81 |
| 300 | 310.173276 | 1505.229855 | 184.737455 | 184.507150 | 210.12 |

Follower and held leader objectives use different rollout paths and are deliberately reported separately. Scores at different reward coefficients cannot be compared as one common objective.

The complete four-lever command table is `commands.csv`. Coefficient sensitivity is:
- vsl: 0 of 44 fields change across these four decisions.
- ramp_metering: 0 of 4 fields change across these four decisions.
- green_times: 34 of 68 fields change across these four decisions.
- offsets: 4 of 17 fields change across these four decisions.

Predicted follower dominance, when present, is evidence of search sensitivity, not simulator performance:
- beta 0: dominated by [60, 150, 300] among these four searched rollouts.
- beta 60: dominated by [150, 300] among these four searched rollouts.
- beta 150: dominated by [300] among these four searched rollouts.
- beta 300: dominated by [] among these four searched rollouts.

The common state, previous action, runtime sources and configuration equivalence are checked. Configuration differences are restricted to the coefficient and its descriptive name. Source/input hashes and original full preflight manifests are retained in `comparison.json`.
