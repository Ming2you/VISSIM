codex_area_observed_nc_s13_20260910: 900–1050 s (validation_only).

Source/config match executed manifest: False. Actual signal/meter/VSL audit valid: False.

| Residence | Model veh·h | Physical veh·h | Error veh·h |
|---|---:|---:|---:|
| omega | 85.629410 | 80.158611 | +5.470799 |
| freeway | 42.761060 | 35.849306 | +6.911754 |
| urban_and_ramps | 42.868350 | 44.309306 | -1.440956 |

Residence error cancellation: 2.881911 veh·h.
| End stock | Model veh | FZP veh | COM veh |
|---|---:|---:|---:|
| omega_veh | 2313.934612 | 2063 | unavailable |
| freeway_veh | 1183.156769 | 922 | unavailable |
| urban_and_ramps_veh | 1130.777843 | 1141 | unavailable |

TD: model 432.184764; physical 481 observed + 227 terminal inferred. Interior disappearance unresolved: 10 vehicles.
Model inside generation: 205.950000 vehicles. Source closure residual: -5.26e-12 vehicles.

| Native input | Source | Model desired | Model admitted | Model unadmitted | Observed source births lower bound | Source final / stopped <5 |
|---|---|---:|---:|---:|---:|---:|
| 1091 | 236 | 6.667 | 6.667 | 0.000 | 14 | 0 / 0 |
| 1085 | 138 | 16.667 | 16.667 | 0.000 | 21 | 1 / 0 |
| 1095 | 164 | 10.000 | 10.000 | 0.000 | 13 | 0 / 0 |
| 1097 | 256 | 6.667 | 6.667 | 0.000 | 6 | 0 / 0 |
| 1083 | 21 | 16.667 | 16.667 | 0.000 | 15 | 2 / 0 |
| 1092 | 217 | 2.500 | 2.500 | 0.000 | 1 | 0 / 0 |
| 1086 | 343 | 11.667 | 11.667 | 0.000 | 7 | 1 / 1 |
| 1087 | 341 | 11.667 | 11.667 | 0.000 | 11 | 4 / 4 |
| 1093 | 225 | 2.500 | 2.500 | 0.000 | 2 | 0 / 0 |
| 1096 | 201 | 3.333 | 3.333 | 0.000 | 4 | 0 / 0 |

The JSON retains source/config/action SHA256, bounded FZP range SHA256, each input’s finite target occupancy and physical support, component errors, actuation evidence, and per-step actual model flows.

Observed TTD plus terminal inference excludes interior disappearance; no unknown sink reward.
Same-side excursions entirely between1s snapshots can be missed; this is not an absolute lower/upper confidence interval.
Terminal inference uses10m position margin,3m/s² reach and1s-step overshoot; normal departure and deletion near a terminal are not distinguishable.
Left/right residence rules are time-discretization alternatives, not statistical uncertainty bounds.
Physical first-seen IDs on isolated input roads give an admitted-input lower bound under complete recording/unique IDs; 1 s skipped source roads remain unattributed.
Appeared-inside is a sampled stock-balance term, not verified internal generation. Unresolved disappearances receive no exit credit.
Unadmitted desired model demand is outside model stock and TTT. Shared approach occupancy is not the count of its input source road.
Source-generation and SC15 changes are jointly active; this single replay measures final-model error, not a causal ablation of either change.
Validation-only permits historical source mismatch and native uncontrolled signal clocks. It does not verify executed-model prediction accuracy.
