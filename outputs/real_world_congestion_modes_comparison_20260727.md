# Real-world VISSIM congestion-mode comparison, seed 13

Controller config: `real_world_modi_pstack_vsl_rollout_vissimdsd_20260725`.

| Scenario | Horizon | Congestion knob | No-control TTT (veh-h) | P-Stack TTT (veh-h) | Delta (veh-h) | Delta (%) | No-control final total | P-Stack final total |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| Base extreme | 600 s | Existing freeway-stress profile | 268.393 | 268.510 | +0.117 | +0.04% | 2777 | 2777 |
| Base extreme | 1200 s | Longer simulation | 846.001 | 837.101 | -8.900 | -1.05% | 4168 | 4140 |
| Base extreme | 4500 s | Longer simulation | 4810.368 | 4586.268 | -224.100 | -4.66% | 3374 | 2908 |
| Demand +15% | 600 s | DemandScale 1.15 | 281.447 | 278.647 | -2.800 | -0.99% | 2920 | 2834 |
| Incident | 600 s | Link 2 lane 1, 1200 m, RED 180-300 s | 268.260 | 268.326 | +0.067 | +0.02% | 2775 | 2777 |

Interpretation:

- Longer simulation time clearly lets the P-Stack benefit accumulate: +0.04% at 600 s, -1.05% at 1200 s, -4.66% at 4500 s.
- Raising demand by 15% makes the 600 s horizon congested enough for P-Stack to improve TTT by about 1%.
- The tested one-lane incident did not materially change network TTT. RED/GREEN readbacks were valid, but the closure was likely too early, too short, and too easy to bypass to hit the active bottleneck.

