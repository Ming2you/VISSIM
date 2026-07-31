# Demand/Bottleneck/Control Overlap Audit

- link_log: `evaluation\runs\rw_peakhold_recovery_d115_7200_20260730\bottleneck_links_peakholdrec_d115_fixed_no_7200s13.csv`
- segment_log: `evaluation\runs\rw_peakhold_recovery_d115_7200_20260730\bottleneck_segments_peakholdrec_d115_fixed_no_7200s13.csv`
- end_sec: 7200
- demand_scale: 1.15
- note: bottleneck link logs contain sampled top links, so shares below are top-log shares, not full-network accounting.

## Coverage

| top | stopped_h | current_control | demand_input | local_obs | signal_inventory | urban_or_other | freeway/freeway_input |
| --- | --- | --- | --- | --- | --- | --- | --- |
| top 10 | 1217.75 | 28.6% | 32.0% | 0.0% | 87.0% | 100.0% | 0.0% |
| top 20 | 1715.48 | 20.3% | 22.7% | 0.0% | 74.6% | 100.0% | 0.0% |

## Signal Expansion Candidates

| rank | signal | top_link_stopped_h |
| --- | --- | --- |
| 1 | SC1 | 348.20 |
| 2 | SC109 | 333.52 |
| 3 | SC9 | 268.58 |
| 4 | SC108 | 108.68 |
| 5 | SC105 | 99.70 |
| 6 | SC2 | 67.42 |
| 7 | SC103 | 43.25 |
| 8 | SC104 | 39.78 |
| 9 | SC9002 | 37.78 |

## Top Bottleneck Links By Stopped-Hours

| rank | link | category | stopped_h | veh_h | max_count | max_stop | avg_kph | run_peak_vph | demand_role | current_control | local_obs | signal_candidates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 57 | urban_or_other | 217.02 | 217.83 | 131 | 131 | 0.16 | - | - | - | - | SC109 |
| 2 | 425 | urban_or_other | 150.50 | 150.92 | 91 | 91 | 0.12 | - | - | - | - | SC9 |
| 3 | 32 | urban_or_other | 143.20 | 223.33 | 192 | 157 | 13.39 | 966 | urban_input | active_signal_SC1,ramp_meter_approach | - | SC1 |
| 4 | 66 | urban_or_other | 137.58 | 203.22 | 166 | 133 | 9.44 | 977 | urban_input | active_signal_SC1 | - | SC1 |
| 5 | 39 | urban_or_other | 118.08 | 134.72 | 102 | 85 | 5.52 | - | - | - | - | SC9 |
| 6 | 403 | urban_or_other | 116.50 | 146.98 | 128 | 123 | 3.06 | - | - | - | - | SC109 |
| 7 | 1220044500 | urban_or_other | 108.68 | 125.28 | 95 | 95 | 3.21 | 1030 | urban_input | - | - | SC108 |
| 8 | 326 | urban_or_other | 83.25 | 110.72 | 107 | 102 | 3.32 | - | - | - | - | - |
| 9 | 421 | urban_or_other | 75.52 | 76.22 | 56 | 56 | 0.39 | - | - | - | - | - |
| 10 | 329 | urban_or_other | 67.42 | 86.38 | 73 | 71 | 2.78 | - | - | active_signal_SC1 | - | SC1,SC2 |
| 11 | 56 | urban_or_other | 62.67 | 73.70 | 90 | 84 | 7.09 | - | - | - | - | - |
| 12 | 420 | urban_or_other | 62.65 | 104.45 | 243 | 203 | 14.23 | - | - | - | - | - |
| 13 | 417 | urban_or_other | 61.93 | 62.38 | 55 | 55 | 0.30 | - | - | - | - | - |
| 14 | 1220007001 | urban_or_other | 61.70 | 64.45 | 67 | 67 | 1.48 | - | - | - | - | SC105 |
| 15 | 325 | urban_or_other | 46.50 | 61.17 | 77 | 74 | 4.05 | - | - | - | - | - |
| 16 | 322 | urban_or_other | 43.47 | 60.57 | 88 | 84 | 5.41 | - | - | - | - | - |
| 17 | 1220024801 | urban_or_other | 43.25 | 51.43 | 47 | 44 | 3.89 | - | - | - | - | SC103 |
| 18 | 1220061200 | urban_or_other | 39.78 | 51.98 | 58 | 58 | 6.40 | - | - | - | - | SC104 |
| 19 | 1220007200 | urban_or_other | 38.00 | 44.08 | 42 | 42 | 2.85 | - | - | - | - | SC105 |
| 20 | 1220007004 | urban_or_other | 37.78 | 42.05 | 91 | 91 | 3.79 | - | - | - | - | SC9002 |

## Top Demand Inputs

| rank | link | run_peak_vph | role | name | bneck_rank | stopped_h | category | current_control | signal_candidates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 74 | 5313 | freeway_feeder_input_candidate | 경부_EB | 174 | 0.53 | freeway_input | - | - |
| 2 | 26 | 5313 | freeway_mainline_input | 경부_NB | 76 | 6.55 | freeway | ramp_meter_merge,vsl_freeway,vsl_segment | - |
| 3 | 55 | 2157 | urban_input | 대치역_WB | 258 | 0.00 | urban_or_other | - | - |
| 4 | 1220000704 | 1548 | urban_input | 개포3,4단지_WB | 54 | 8.88 | urban_or_other | - | SC109 |
| 5 | 1220042300 | 1536 | urban_input | 구룡터널_NB(터널직진) | 270 | 0.00 | urban_or_other | - | - |
| 6 | 1220044500 | 1030 | urban_input | 구룡마을_NB | 7 | 108.68 | urban_or_other | - | SC108 |
| 7 | 308 | 1010 | urban_input | 매봉터널_SB | 340 | 0.00 | urban_or_other | - | - |
| 8 | 66 | 977 | urban_input | - | 4 | 137.58 | urban_or_other | active_signal_SC1 | SC1 |
| 9 | 69 | 966 | urban_input | - | 257 | 0.00 | urban_or_other | ramp_meter_approach | - |
| 10 | 32 | 966 | urban_input | - | 3 | 143.20 | urban_or_other | active_signal_SC1,ramp_meter_approach | SC1 |
| 11 | 113 | 924 | urban_input | 대치역_SB | 122 | 2.58 | urban_or_other | - | - |
| 12 | 60 | 874 | urban_input | 대모산역사거리_SB | 279 | 0.00 | urban_or_other | - | - |
| 13 | 42 | 862 | urban_input | 대모산역사거리_NB | 291 | 0.00 | urban_or_other | - | - |
| 14 | 293 | 718 | urban_input | 도곡역_SB | 303 | 0.00 | urban_or_other | - | - |
| 15 | 21 | 483 | urban_input | Dummy link 1 | 118 | 2.78 | urban_or_other | - | SC108 |
| 16 | 138 | 483 | urban_input | Dummy Link 6 | 206 | 0.15 | urban_or_other | - | - |
| 17 | 379 | 465 | urban_input | 구룡터널_NB | 407 | 0.00 | urban_or_other | - | - |
| 18 | 13 | 357 | urban_input | 대모산역사거리_WB | 337 | 0.00 | urban_or_other | - | - |
| 19 | 343 | 338 | urban_input | Dummy link 3 | 58 | 8.38 | urban_or_other | - | SC15 |
| 20 | 341 | 338 | urban_input | Dummy link 4 | 67 | 7.38 | urban_or_other | - | SC15 |

## Freeway Segment Bottlenecks

| rank | segment | model | idx | physical_link | stopped_h | veh_h | max_density | avg_kph |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | RW_FW_E_S1 | FW_E | 1 | 2 | 3.40 | 145.62 | 38.81 | 53.37 |
| 2 | RW_FW_W_S3 | FW_W | 3 | 26 | 3.35 | 149.22 | 36.62 | 52.58 |
| 3 | RW_FW_E_S4 | FW_E | 4 | 2 | 2.42 | 107.65 | 30.85 | 57.70 |
| 4 | RW_FW_W_S5 | FW_W | 5 | 26 | 1.52 | 122.73 | 32.88 | 60.84 |
| 5 | RW_FW_W_S6 | FW_W | 6 | 26 | 0.63 | 102.10 | 25.91 | 63.57 |
| 6 | RW_FW_E_S3 | FW_E | 3 | 2 | 0.45 | 115.90 | 37.57 | 63.73 |
| 7 | RW_FW_W_S2 | FW_W | 2 | 26 | 0.42 | 135.42 | 33.63 | 60.72 |
| 8 | RW_FW_E_S0 | FW_E | 0 | 2 | 0.35 | 130.05 | 35.33 | 62.42 |
| 9 | RW_FW_W_S1 | FW_W | 1 | 26 | 0.27 | 133.27 | 34.62 | 62.18 |
| 10 | RW_FW_E_S7 | FW_E | 7 | 2 | 0.18 | 84.07 | 30.10 | 71.75 |
| 11 | RW_FW_W_S4 | FW_W | 4 | 26 | 0.15 | 112.10 | 26.90 | 66.83 |
| 12 | RW_FW_E_S2 | FW_E | 2 | 2 | 0.13 | 116.42 | 33.34 | 61.77 |
| 13 | RW_FW_W_S0 | FW_W | 0 | 26 | 0.12 | 129.57 | 26.15 | 64.61 |
| 14 | RW_FW_E_S5 | FW_E | 5 | 2 | 0.12 | 86.35 | 27.87 | 71.85 |
| 15 | RW_FW_E_S6 | FW_E | 6 | 2 | 0.12 | 86.20 | 31.85 | 71.91 |
| 16 | RW_FW_W_S7 | FW_W | 7 | 26 | 0.10 | 96.73 | 26.90 | 70.15 |

