# Urban joint calibration (turn ratios fixed @route + sat/off/speed fit)

Best: movement_capacity(sat)=1200, off_ramp_split=0.06, urban_avg_speed=70. Fit on low+ramp_d, held-out urban_d. turn_ratios+detector=route-derived.

| regime | metric | baseline | joint-calib | delta% |
| --- | --- | ---: | ---: | ---: |
| low | urban_movement_queue | 46.07 | 65.08 | +41.3% |
| low | urban_link_occupancy | 79.14 | 62.95 | -20.5% |
| low | total_modelicles | 103.19 | 111.65 | +8.2% |
| low | protected_accumulation | 79.88 | 75.86 | -5.0% |
| ramp_d | urban_movement_queue | 109.53 | 25.59 | -76.6% |
| ramp_d | urban_link_occupancy | 81.45 | 26.56 | -67.4% |
| ramp_d | total_modelicles | 26.87 | 33.50 | +24.7% |
| ramp_d | protected_accumulation | 55.98 | 31.14 | -44.4% |
| urban_d | urban_movement_queue | 72.71 | 86.49 | +19.0% |
| urban_d | urban_link_occupancy | 58.88 | 38.19 | -35.1% |
| urban_d | total_modelicles | 88.42 | 105.78 | +19.6% |
| urban_d | protected_accumulation | 58.77 | 42.96 | -26.9% |

## Interpretation (J — urban joint calibration)

- Coordinate descent pushed parameters to the GRID EDGES: movement_capacity(sat)=1200 (lowest),
  urban_avg_speed=70 (highest), off_split unchanged at 0.06. Edge-hitting at non-physical extremes is
  an overfitting / ill-conditioning signal, not a clean physical optimum.
- The aggregate weighted objective improved ~10% (0.222 -> 0.200), but this comes almost entirely from
  the asymmetric ramp_d_bias regime, where movement_queue (-76.6%), link_occupancy (-67.4%) and
  protected (-44.4%) all improve dramatically. On the symmetric low and urban_d regimes the same params
  WORSEN movement_queue (+41%, +19%) and total mass (+8%, +20%). The relative-to-baseline objective is
  dominated by ramp_d's large headroom, so the descent rationally overfits to it.
- Conclusion: there is NO clean joint calibration that improves all component errors across all regimes
  with these parameters. The urban model has a structural trade-off (movement_queue vs total mass vs
  link_occupancy) that parameter tuning cannot remove. Broadly, link_occupancy and protected
  accumulation CAN be reduced (-20..-67% / -5..-44%) and the asymmetric ramp scenario improves a lot,
  but at the cost of movement_queue and total mass on symmetric scenarios.
- Recommendation: do NOT promote a single joint-calibrated parameter set as a general urban model.
  Either (a) accept the model's structural limits and proceed to the controller evaluation (PFO already
  yields -3.6% TTT at mid demand), treating link_occupancy/protected improvements as a candidate for
  asymmetric-scenario studies; or (b) pursue urban MODEL STRUCTURE changes (not just parameters) in the
  Numerical-Sim repo, which is a much larger, upstream-coordinated effort. Parameter-only joint
  calibration has reached its ceiling.
