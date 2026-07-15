# Route-bias forecast: OFF vs v1(0.98) vs v2(direction-aware) sweep

Held-out no-control states; same repo-root (new clone). v2 loads the direction-feeding ramp (d->R_D_W/FW_W, f->R_F_E/FW_E) with multiplier x ramp_vph; cross_share=0.15, off_share=0.02. Values = mean one-step abs error (lower better).

| scenario | metric | OFF | v1_098 | v2_m1 | v2_m2 | v2_m4 | v2_m6 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| d_ramp_bias | freeway_total_veh | 20.726 | 20.711 | **20.277** | 20.455 | 20.820 | 21.221 |
| d_ramp_bias | protected_accumulation_veh | 55.988 | 55.975 | **55.936** | 55.950 | 55.978 | 56.005 |
| d_ramp_bias | urban_queue_plus_link_occupancy_total_veh | 25.186 | 25.115 | 26.747 | 25.969 | **25.016** | 25.842 |
| d_ramp_bias | total_model_vehicles | 27.672 | **26.869** | 29.632 | 28.687 | 26.933 | 27.415 |
| f_ramp_bias | freeway_total_veh | **19.535** | 19.828 | 19.708 | 19.739 | 19.739 | 19.739 |
| f_ramp_bias | protected_accumulation_veh | 143.093 | 142.198 | 143.504 | 142.988 | 142.148 | **141.592** |
| f_ramp_bias | urban_queue_plus_link_occupancy_total_veh | 129.699 | 131.310 | **125.432** | 127.535 | 131.938 | 137.372 |
| f_ramp_bias | total_model_vehicles | 99.073 | 100.181 | **94.166** | 96.274 | 100.735 | 106.111 |

## Interpretation (audit follow-up E3)

- All arms differ by only a few percent on every metric; no arm dominates. This confirms that the
  one-step (60 s) prediction error is fundamentally INSENSITIVE to the on-ramp arrival forecast:
  over one interval the ramp merge is a small fraction of the freeway/urban state.
- The direction-aware v2 at LOW multiplier (v2_m1) does beat v1(0.98) on f_ramp_bias urban
  queue+storage (-4.5%) and total (-6.1%) and marginally on d_ramp_bias freeway, but it is WORSE
  than v1 on d_ramp_bias total (+10%). Higher multipliers (m4/m6) are generally worse. OFF is
  competitive or best on several metrics. There is no robust, scenario-stable winner.
- The large errors (protected_accumulation ~56/142, urban queue+storage ~25/130) do not move with
  any ramp-forecast variant. They are driven by urban-state dynamics (turn/off-ramp split and urban
  propagation), not by the demand-side ramp forecast.

## Verdict

- KEEP route_bias_forecast demoted (candidate). Do NOT promote v1(0.98) or v2 on this evidence.
- v2 (direction-aware) is conceptually more correct than v1 (it loads only the WB-feeding D ramp /
  EB-feeding F ramp instead of splitting across both directions, and unties magnitude from a
  hardcoded ramp_vph total). It is now available opt-in via route_bias_forecast.version=2, but is
  left INACTIVE (version unset -> v1/demoted) because it does not robustly reduce held-out error.
- The real lever is the urban turn/off-ramp split under route bias. Recommended next step is a
  dedicated live VISSIM A/B: run no-control d_ramp_bias / f_ramp_bias and fit the model urban
  turning ratios + off-ramp split to the observed urban link/movement counts, rather than tuning the
  ramp-arrival forecast. Only after that should any route_bias_forecast version be re-promoted.
