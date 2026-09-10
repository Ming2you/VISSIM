codex_area_sources_beta0_s13_20260910: 3300–3450 s (complete).

Source/config match executed manifest: True. Actual signal/meter/VSL audit valid: True.

| Residence | Model veh·h | Physical veh·h | Error veh·h |
|---|---:|---:|---:|
| omega | 223.728728 | 215.347222 | +8.381506 |
| freeway | 131.398723 | 124.601250 | +6.797473 |
| urban_and_ramps | 92.330006 | 90.745972 | +1.584033 |

Residence error cancellation: 0.000000 veh·h.

| End stock | Model veh | FZP veh | COM veh |
|---|---:|---:|---:|
| omega_veh | 5578.156924 | 5214 | 5211 |
| freeway_veh | 3306.294819 | 3008 | 3005 |
| urban_and_ramps_veh | 2271.862105 | 2206 | 2206 |

TD: model 465.384468; physical 540 observed + 221 terminal inferred. Interior disappearance unresolved: 11 vehicles.
Model inside generation: 185.380000 vehicles. Source closure residual: -8.33e-12 vehicles.

| Native input | Source | Model desired | Model admitted | Model unadmitted | Observed source births lower bound | Source final / stopped <5 |
|---|---|---:|---:|---:|---:|---:|
| 1091 | 236 | 6.000 | 6.000 | 0.000 | 4 | 0 / 0 |
| 1085 | 138 | 15.000 | 15.000 | 0.000 | 16 | 0 / 0 |
| 1095 | 164 | 9.000 | 9.000 | 0.000 | 10 | 1 / 0 |
| 1097 | 256 | 6.000 | 6.000 | 0.000 | 1 | 0 / 0 |
| 1083 | 21 | 15.000 | 15.000 | 0.000 | 15 | 4 / 0 |
| 1092 | 217 | 2.250 | 2.250 | 0.000 | 4 | 1 / 0 |
| 1086 | 343 | 10.500 | 10.500 | 0.000 | 13 | 2 / 2 |
| 1087 | 341 | 10.500 | 10.500 | 0.000 | 7 | 0 / 0 |
| 1093 | 225 | 2.250 | 2.250 | 0.000 | 1 | 0 / 0 |
| 1096 | 201 | 3.000 | 3.000 | 0.000 | 2 | 0 / 0 |

All 42 freeway cells: nonempty-cell speed MAE 12.398 km/h; speed bias -6.198 km/h; summed stock error +301.295 vehicles.

| Cell (zero based) | Initial observed speed | Predicted final speed | Observed final speed | Speed error | Predicted / observed final N | Predicted / observed evolution |
|---|---:|---:|---:|---:|---:|---|
| E8 | 2.424 | 12.886 | 1.952 | 10.933 | 157.972 / 289 | persistent_congestion / persistent_congestion |
| E9 | 5.625 | 24.226 | 3.303 | 20.923 | 110.655 / 72 | persistent_congestion / persistent_congestion |

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
