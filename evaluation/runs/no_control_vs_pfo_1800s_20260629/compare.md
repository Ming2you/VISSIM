# no-control vs PFO — 1800s live VISSIM comparison

Setup: `modi_eval_vsl_segmented.inpx`, u2600 / fw3400 / sym / seed13, 1800 s, control_interval 60 s,
new clone repo-root (0e07c1c), calibration v2. Warmup 300 s for metrics. Both runs exit 0, 31/31
decisions ok, no fallback.

## Result

| metric | no-control | pfo | delta |
| --- | ---: | ---: | ---: |
| vehicle_hours_total (TTT proxy) | 685.086 | 685.101 | **+0.0%** |
| vehicle_hours_urban | 212.039 | 199.994 | -5.7% |
| vehicle_hours_freeway | 73.176 | 76.149 | +4.1% |
| stopped_vehicle_hours | 357.121 | 339.276 | -5.0% |
| mean_speed_kph | 22.414 | 23.352 | +4.2% |
| freeway_mean_speed_kph | 84.357 | 80.713 | -4.3% |
| mean_stopped_vehicles | 854.2 | 811.6 | -5.0% |
| mean_decision_wall_sec | 0.305 | 10.453 | (PFO computes ~10 s/decision) |

## Control activation (PFO, 31 decisions)

- metering_active_steps (D ramp < 1300 vph): **0 / 31** — ramp metering NEVER restricts (R_D_W/R_D_E always 1414 vph = max release).
- vsl_active_steps (any seg < 115 kph): **0 / 31** — VSL NEVER reduces (all segments 120 kph = free flow).
- N_UF_star = 0.0 for all decisions, N_P_star = 0.0 (expected: PFO = DistributedCoordinator runs leaderless; the adapter calls `solve(state, None, forecast, previous)`).
- F ramps pinned at 237.1 (always-green guard).

## Diagnosis

1. PFO does NOT meaningfully improve total TTT (+0.0%). It gives a modest URBAN improvement
   (-5.7% urban VHT, +4.2% mean speed, -5.0% stops) at the cost of a small freeway worsening
   (+4.1% freeway VHT, -4.3% freeway speed). Net wash on aggregate TTT.
2. The freeway is FREE-FLOWING (80-84 kph). PFO's freeway controls (ramp metering, VSL) correctly
   stay inactive because there is no freeway congestion to relieve. This is NOT a controller-objective
   failure — it is the right action for an uncongested freeway.
3. The bottleneck is URBAN: urban VHT (~200) is ~3x freeway VHT (~75), ~850 vehicles are stopped,
   and overall speed is 22 kph while the freeway is at 84 kph. The only lever PFO has here is urban
   green-time/offset, which produced the modest urban gains.
4. At u2600/fw3400 the urban network is near gridlock (~850 stopped ~= ~50% of vehicles present),
   which limits how much any controller can recover.

## Recommendation

- The limited PFO benefit is an URBAN problem, not a freeway one. Freeway metering/VSL calibration is
  not the priority (freeway is uncongested here).
- Priority calibration target = the URBAN side (consistent with the prior audit): per-approach signal
  saturation flow / lost time (current scalar 1800 vph fallback, valid_regression_count 0), urban link
  storage, and the urban turn / off-ramp split. The urban turn-split is also the lever the route-bias
  E3 sweep pointed to.
- Recommended quick diagnostic before committing: re-run no-control vs PFO at a MID demand
  (e.g., u1800 / fw3000) to confirm the urban gridlock is physical (network capacity) rather than pure
  oversaturation, and to see whether PFO's urban control shows a clearer gain off the gridlock ceiling.
