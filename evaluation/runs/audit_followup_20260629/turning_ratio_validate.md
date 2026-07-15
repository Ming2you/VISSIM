# Turning-ratio alignment validation (low-demand clean + held-out)

baseline=default model+assumed detector; detector_only=route detector weights; model_only=route turning_ratios; both=both aligned. Mean one-step abs error (lower better).

| scenario | metric | baseline | detector_only | model_only | both_aligned |
| --- | --- | ---: | ---: | ---: | ---: |
| low_u1000 | urban_movement_queue_total_veh | 32.05 | 32.66 | 31.03 | **30.88** |
| low_u1000 | urban_link_occupancy_total_veh | **79.62** | 84.02 | 86.19 | 90.82 |
| low_u1000 | urban_queue_plus_link_occupancy_total_veh | **95.76** | 100.93 | 104.94 | 109.92 |
| low_u1000 | total_model_vehicles | **74.81** | 79.34 | 83.44 | 87.90 |
| ramp_d_bias | urban_movement_queue_total_veh | 109.53 | 102.07 | 84.26 | **68.18** |
| ramp_d_bias | urban_link_occupancy_total_veh | **81.45** | 86.38 | 88.07 | 86.82 |
| ramp_d_bias | urban_queue_plus_link_occupancy_total_veh | 25.11 | 28.04 | **24.28** | 31.83 |
| ramp_d_bias | total_model_vehicles | 26.87 | 30.48 | **25.06** | 37.68 |
| urban_d_heavy | urban_movement_queue_total_veh | **72.71** | 74.21 | 76.90 | 77.95 |
| urban_d_heavy | urban_link_occupancy_total_veh | **58.88** | 62.06 | 64.98 | 67.78 |
| urban_d_heavy | urban_queue_plus_link_occupancy_total_veh | **99.90** | 105.42 | 116.16 | 124.06 |
| urban_d_heavy | total_model_vehicles | **88.42** | 94.05 | 105.03 | 110.60 |

## Interpretation (H — turning-ratio alignment)

- Aligning the MODEL turning_ratios (route-derived, injected via tuning network.turning_ratios; no repo
  change) does what it should to its DIRECT target: urban_movement_queue improves on low (-3.6%) and
  dramatically on ramp_d_bias (-38%). model_only also improves ramp_d q+storage (-3%) and total (-7%).
- BUT it WORSENS urban_link_occupancy / q+storage / total on the clean low-demand and urban_d cases
  (+14..+17%). Same trade-off seen with the detector-weight-only change (G2): redistributing flow to
  the correct movements moves link-occupancy and total mass away from what the model's storage /
  propagation predicts.
- Conclusion: the turn-split is demonstrably wrong and aligning it is NECESSARY (it fixes the
  movement-queue decomposition, esp. on asymmetric ramp_d), but NOT SUFFICIENT. No single adapter/model
  parameter (turn ratios, detector weights, observation split, route-bias) robustly improves urban
  prediction across regimes; they trade one component error for another. This is strong evidence that
  the urban model needs a JOINT multi-parameter fit (turning ratios + link storage + signal saturation
  flow + propagation/MFD) calibrated together against multi-regime data, not piecemeal.
- Practical note: `model_only` (route turning_ratios, keep assumed detector weights) is the least-bad
  single change and clearly helps the asymmetric ramp_d_bias scenario; it could be adopted as a partial
  improvement if asymmetric-ramp fidelity is the priority, but it should not be promoted as a general
  fix on this evidence.
