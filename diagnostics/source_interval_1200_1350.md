codex_area_sources_beta0_s13_20260910: 1200–1350 s (complete).

Source/config match executed manifest: True. Actual signal/meter/VSL audit valid: True.

| Residence | Model veh·h | Physical veh·h | Error veh·h |
|---|---:|---:|---:|
| omega | 111.600511 | 106.012500 | +5.588011 |
| freeway | 50.065939 | 46.571389 | +3.494550 |
| urban_and_ramps | 61.534572 | 59.441111 | +2.093461 |

Residence error cancellation: 0.000000 veh·h.

| End stock | Model veh | FZP veh | COM veh |
|---|---:|---:|---:|
| omega_veh | 2910.056163 | 2642 | 2641 |
| freeway_veh | 1285.088157 | 1115 | 1114 |
| urban_and_ramps_veh | 1624.968005 | 1527 | 1527 |

TD: model 484.779891; physical 575 observed + 243 terminal inferred. Interior disappearance unresolved: 1 vehicles.
Model inside generation: 205.950000 vehicles. Source closure residual: -4.01e-12 vehicles.

| Native input | Source | Model desired | Model admitted | Model unadmitted | Observed source births lower bound | Source final / stopped <5 |
|---|---|---:|---:|---:|---:|---:|
| 1091 | 236 | 6.667 | 6.667 | 0.000 | 6 | 0 / 0 |
| 1085 | 138 | 16.667 | 16.667 | 0.000 | 17 | 2 / 0 |
| 1095 | 164 | 10.000 | 10.000 | 0.000 | 7 | 0 / 0 |
| 1097 | 256 | 6.667 | 6.667 | 0.000 | 9 | 1 / 0 |
| 1083 | 21 | 16.667 | 16.667 | 0.000 | 22 | 12 / 11 |
| 1092 | 217 | 2.500 | 2.500 | 0.000 | 3 | 0 / 0 |
| 1086 | 343 | 11.667 | 11.667 | 0.000 | 8 | 0 / 0 |
| 1087 | 341 | 11.667 | 11.667 | 0.000 | 20 | 4 / 1 |
| 1093 | 225 | 2.500 | 2.500 | 0.000 | 3 | 0 / 0 |
| 1096 | 201 | 3.333 | 3.333 | 0.000 | 0 | 0 / 0 |

All 42 freeway cells: nonempty-cell speed MAE 18.176 km/h; speed bias -7.291 km/h; summed stock error +171.088 vehicles.

| Cell (zero based) | Initial observed speed | Predicted final speed | Observed final speed | Speed error | Predicted / observed final N | Predicted / observed evolution |
|---|---:|---:|---:|---:|---:|---|
| E8 | 36.173 | 96.116 | 40.485 | 55.631 | 33.313 / 66 | recovery / persistent_congestion |
| E9 | 51.287 | 84.791 | 43.168 | 41.623 | 30.367 / 26 | recovery / persistent_congestion |

Unweighted cell speed errors on nonempty observed cells; exact same cell indices/bounds as paused COM. Density geometry conventions are both reported.
60 km/h is a diagnostic threshold, not a calibrated FD or control parameter. Observed evolution uses two COM endpoints; within-interval onset/recovery time is not inferred. Model threshold crossings are sampled at 10 s.

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
