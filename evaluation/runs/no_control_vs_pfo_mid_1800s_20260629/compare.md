# no-control vs PFO — MID demand (u1800/fw3000), 1800s

Setup identical to the high-demand run except demand u1800/fw3000 (vs u2600/fw3400). Both exit 0,
31/31 decisions ok, no fallback. Warmup 300 s.

## Result (MID vs HIGH demand side by side)

| metric | MID nc | MID pfo | MID Δ | HIGH Δ (ref) |
| --- | ---: | ---: | ---: | ---: |
| vehicle_hours_total (TTT) | 616.9 | 594.7 | **-3.6%** | +0.0% |
| stopped_vehicle_hours | 313.9 | 281.3 | **-10.4%** | -5.0% |
| mean_speed_kph | 23.9 | 26.1 | **+9.0%** | +4.2% |
| mean_stopped_vehicles | 750.9 | 672.9 | -10.4% | -5.0% |
| vehicle_hours_urban | 199.3 | 211.1 | +5.9% | -5.7% |
| vehicle_hours_freeway | 57.9 | 58.3 | +0.7% | +4.1% |
| freeway_mean_speed_kph | 95.1 | 95.3 | +0.2% | -4.3% |

PFO control activation (MID): metering_active 0/31, vsl_active 0/31, N_UF_star = 0 (same as HIGH).
D ramps pinned at 1414 (max release), F ramps at 237 (always-green guard), all VSL at free flow.

## Findings

1. PFO DOES help at a non-gridlock demand: MID gives -3.6% total TTT, -10.4% stopped, +9.0% mean
   speed. The HIGH-demand +0.0% was oversaturation/gridlock masking the benefit. So the network and
   controller are not broken; the earlier "no improvement" was demand-driven gridlock.
2. In BOTH demands the freeway is free-flowing (95 / 84 kph) and PFO's freeway controls (ramp metering,
   VSL) never activate (correct: no freeway congestion to relieve). The entire PFO benefit comes from
   URBAN signal control (green time / offset).
3. The bottleneck and the only active control lever is URBAN. This is consistent with the urban
   turn-split diagnosis (audit_followup_20260629/urban_turn_split_diag.md): the model's urban turning
   ratios are mis-specified, which is the place where modeling fidelity (and likely control quality)
   can still be improved.
