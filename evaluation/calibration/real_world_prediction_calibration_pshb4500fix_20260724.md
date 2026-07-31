# Real-world prediction calibration candidate

- calibration: `real_world_prediction_calibration_pshb4500fix_20260724`
- source run: `evaluation\runs\rw_cg_hb_4500_fixguard_0723\decisions_pshb4500fixs13`
- fit window: `900-4500s`
- basis: one-step `prediction_error.scalar_errors`, mean observed / mean predicted

| model area | metric | observed | predicted | scale |
| --- | --- | ---: | ---: | ---: |
| METANET | `freeway_total_veh` | 968.787 | 910.728 | 1.063750 |
| METANET | `freeway_mean_density_veh_km_lane` | 15.074 | 14.170 | 1.063746 |
| METANET | `freeway_mean_speed_kph` | 62.858 | 102.526 | 0.613091 |
| Kashani/local | `protected_accumulation_veh` | 13.713 | 74.793 | 0.183348 |
| Kashani/local | `urban_movement_queue_total_veh` | 13.713 | 56.067 | 0.244584 |
| Kashani/local | `urban_link_occupancy_total_veh` | 13.713 | 97.108 | 0.141216 |
| Kashani/local | `urban_queue_plus_link_occupancy_total_veh` | 27.426 | 153.175 | 0.179052 |
| interface | `off_ramp_storage_veh` | 13.713 | 36.085 | 0.380019 |

Implementation notes:

- `freeway_total_scale` also scales `freeway_segment_total_veh` and mean density inside the adapter.
- Urban queue+storage, urban total, and total model vehicles are recomputed from calibrated components instead of using one independent aggregate scale.
- `ramp_queue_total_veh` is not promoted here because the observed/predicted scale is about `61.06`, outside the adapter's safe audit-scale range. That needs a separate ramp-arrival/queue-state calibration.
