# nu_cong 65 vs 250 isolation replay (held-out no-control)

Repo-roots differ only in default.yaml `metanet_nu_cong_km2_h`(65 vs 250) and `capacity_drop_anticipation`(false vs true). metanet/urban models are 0-diff.

Values = mean one-step abs error over chained held-out decisions (n in parens).

| scenario | metric | nu65(old) | nu250(new) | delta(new-old) | delta% |
| --- | --- | ---: | ---: | ---: | ---: |
| fw_eb_heavy | freeway_total_veh | 19.675 | 17.842 | -1.833 | -9.3% |
| fw_eb_heavy | protected_accumulation_veh | 62.958 | 62.835 | -0.123 | -0.2% |
| fw_eb_heavy | urban_queue_plus_link_occupancy_total_veh | 66.068 | 67.340 | +1.272 | +1.9% |
| fw_eb_heavy | total_model_vehicles | 58.692 | 61.085 | +2.393 | +4.1% |
| ramp_d_bias | freeway_total_veh | 21.508 | 20.711 | -0.797 | -3.7% |
| ramp_d_bias | protected_accumulation_veh | 55.910 | 55.975 | +0.065 | +0.1% |
| ramp_d_bias | urban_queue_plus_link_occupancy_total_veh | 25.093 | 25.115 | +0.022 | +0.1% |
| ramp_d_bias | total_model_vehicles | 27.590 | 26.869 | -0.721 | -2.6% |
| urban_d_heavy | freeway_total_veh | 10.548 | 10.548 | +0.000 | +0.0% |
| urban_d_heavy | protected_accumulation_veh | 58.767 | 58.767 | +0.000 | +0.0% |
| urban_d_heavy | urban_queue_plus_link_occupancy_total_veh | 99.901 | 99.901 | +0.000 | +0.0% |
| urban_d_heavy | total_model_vehicles | 88.425 | 88.425 | +0.000 | +0.0% |

## Interpretation

- Sanity: stored(orig nu65) vs recomputed nu65 freeway mean abs match within a few vehicles
  (16.8/19.7, 22.3/21.5, 8.5/10.5). The same harness drives both A/B arms, so the systematic
  offset cancels and the delta is valid.
- nu_cong 65->250 + capacity_drop false->true does NOT degrade freeway prediction: fw_eb_heavy
  -9.3%, ramp_d_bias -3.7% (both slightly better), urban_d_heavy 0.0% (freeway uncongested so
  the congestion-wave term is inactive). Other metrics move <=+/-4%.
- Conclusion: the source update is neutral-to-slightly-beneficial for freeway one-step
  prediction. The freeway audit scale 0.6507 does NOT need an urgent re-fit due to this change
  alone. Re-fit remains a separate follow-up if/when freeway-heavy controller runs demand it.
