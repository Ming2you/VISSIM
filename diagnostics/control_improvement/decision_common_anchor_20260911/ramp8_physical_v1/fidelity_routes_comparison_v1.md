# Recorded900 held450 fidelity comparison

Window 900–1350; stored JSON only. Same initial model inventory, forecast hash and held physical commands. This is prediction validation, not closed-loop control benefit.

| Metric | Native | Legacy | SC1005 unsignalized only | Route inventory |
|---|---:|---:|---:|---:|
| TTT (veh*h) | 166.565 | 191.099 | 191.011 | 187.907 |
| TD (veh) | 1558.000 | 1138.374 | 1141.229 | 1131.833 |
| Terminal exits (veh) | 492.000 | 658.636 | 658.782 | 525.090 |
| Live Omega exits (veh) | 1066.000 | 479.739 | 482.447 | 606.744 |
| 8 off-ramp entries (veh) | 790.000 | 402.745 | 403.187 | 611.195 |
| 8 ramp merges (veh) | 301.000 | 235.941 | 238.892 | 249.187 |

| Error grain | Legacy MAE | SC1005 only MAE | Route inventory MAE |
|---|---:|---:|---:|
| 2 terminal directions | 83.318 | 83.391 | 16.545 |
| 8 off-ramp branches | 48.407 | 48.352 | 25.956 |
| 8 ramp merges | 10.917 | 10.549 | 10.978 |

Off-ramp and terminal errors decrease. Aggregate TD absolute bias increases 419.626→426.167 veh; 8-ramp MAE increases 10.917→10.978 veh despite a smaller total merge deficit. Model TTT remains 21.342 veh*h above native.

The legacy 900 input has no qualified head-free floor. This rollout retains 206.531 veh/h; 312 veh/h was not active here.

Native TD 1558 retains its existing review flag; 12 unresolved inside disappearances are excluded. Model/native initial Omega stocks are 1033/1034. The 8 off-ramp and 8 merge rows are separate physical boundaries and must not be added to TD.

Source SHA256s, identity checks, per-branch errors and adjacent150s terminal/live bins are in [fidelity_routes_comparison_v1.json](fidelity_routes_comparison_v1.json). No new model, native or FZP work was performed.
