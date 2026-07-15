# Prediction error component diagnostics

`error` is observed minus predicted. Positive means the model under-predicted the observed value.

| run | controller | scenario | metric | mean observed | mean predicted | mean error | mean abs error | rel error | density excess | spillback |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s | diagnostic-vsl-rm | ramp_d_bias | `freeway_mean_speed_kph` | 71.934 | 87.038 | -15.104 | 15.104 | -0.175 | 0.000 | 0.000 |
| diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s | diagnostic-vsl-rm | ramp_d_bias | `freeway_segment_total_veh` | 106.688 | 184.060 | -77.371 | 77.371 | -0.423 | 0.000 | 0.000 |
| diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s | diagnostic-vsl-rm | ramp_d_bias | `freeway_total_veh` | 131.888 | 200.294 | -68.406 | 68.406 | -0.346 | 0.000 | 0.000 |
| diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s | diagnostic-vsl-rm | ramp_d_bias | `protected_accumulation_veh` | 241.300 | 244.251 | -2.951 | 34.512 | -0.106 | 0.000 | 0.000 |
| diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s | diagnostic-vsl-rm | ramp_d_bias | `ramp_queue_total_veh` | 25.200 | 16.234 | 8.966 | 12.903 | 2.638 | 0.000 | 0.000 |
| diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s | diagnostic-vsl-rm | ramp_d_bias | `total_model_vehicles` | 874.088 | 912.478 | -38.390 | 42.857 | -0.055 | 0.000 | 0.000 |
| diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s | diagnostic-vsl-rm | ramp_d_bias | `urban_link_occupancy_total_veh` | 0.000 | 167.567 | -167.567 | 167.567 | -1.000 | 0.000 | 0.000 |
| diagnostic-vsl-rm_ramp_d_bias_u2200_fw3000_seed13_300s | diagnostic-vsl-rm | ramp_d_bias | `urban_movement_queue_total_veh` | 742.200 | 544.617 | 197.583 | 197.583 | 0.393 | 0.000 | 0.000 |
| pfo_fw_eb_heavy_u1800_fw3400_seed13_600s | pfo | fw_eb_heavy | `freeway_mean_speed_kph` | 77.171 | 83.589 | -6.418 | 14.197 | -0.065 | 31.634 | 0.000 |
| pfo_fw_eb_heavy_u1800_fw3400_seed13_600s | pfo | fw_eb_heavy | `freeway_segment_total_veh` | 144.184 | 216.070 | -71.886 | 71.886 | -0.322 | 31.634 | 0.000 |
| pfo_fw_eb_heavy_u1800_fw3400_seed13_600s | pfo | fw_eb_heavy | `freeway_total_veh` | 149.184 | 233.773 | -84.589 | 84.589 | -0.345 | 31.634 | 0.000 |
| pfo_fw_eb_heavy_u1800_fw3400_seed13_600s | pfo | fw_eb_heavy | `protected_accumulation_veh` | 295.100 | 371.140 | -76.040 | 76.040 | -0.228 | 31.634 | 0.000 |
| pfo_fw_eb_heavy_u1800_fw3400_seed13_600s | pfo | fw_eb_heavy | `ramp_queue_total_veh` | 5.000 | 17.704 | -12.704 | 14.583 | 0.161 | 31.634 | 0.000 |
| pfo_fw_eb_heavy_u1800_fw3400_seed13_600s | pfo | fw_eb_heavy | `total_model_vehicles` | 874.084 | 935.368 | -61.284 | 61.809 | -0.069 | 31.634 | 0.000 |
| pfo_fw_eb_heavy_u1800_fw3400_seed13_600s | pfo | fw_eb_heavy | `urban_link_occupancy_total_veh` | 0.000 | 281.288 | -281.288 | 281.288 | -1.000 | 31.634 | 0.000 |
| pfo_fw_eb_heavy_u1800_fw3400_seed13_600s | pfo | fw_eb_heavy | `urban_movement_queue_total_veh` | 724.900 | 420.307 | 304.593 | 304.593 | 0.753 | 31.634 | 0.000 |
| pfo_ramp_d_bias_u2200_fw3000_seed13_300s | pfo | ramp_d_bias | `freeway_mean_speed_kph` | 92.941 | 102.545 | -9.604 | 10.661 | -0.094 | 5.229 | 0.000 |
| pfo_ramp_d_bias_u2200_fw3000_seed13_300s | pfo | ramp_d_bias | `freeway_segment_total_veh` | 85.269 | 158.833 | -73.564 | 73.564 | -0.464 | 5.229 | 0.000 |
| pfo_ramp_d_bias_u2200_fw3000_seed13_300s | pfo | ramp_d_bias | `freeway_total_veh` | 109.269 | 173.770 | -64.501 | 64.501 | -0.378 | 5.229 | 0.000 |
| pfo_ramp_d_bias_u2200_fw3000_seed13_300s | pfo | ramp_d_bias | `protected_accumulation_veh` | 237.850 | 245.107 | -7.257 | 31.061 | -0.105 | 5.229 | 0.000 |
| pfo_ramp_d_bias_u2200_fw3000_seed13_300s | pfo | ramp_d_bias | `ramp_queue_total_veh` | 24.000 | 14.937 | 9.063 | 10.498 | 4.907 | 5.229 | 0.000 |
| pfo_ramp_d_bias_u2200_fw3000_seed13_300s | pfo | ramp_d_bias | `total_model_vehicles` | 840.469 | 879.629 | -39.160 | 39.160 | -0.057 | 5.229 | 0.000 |
| pfo_ramp_d_bias_u2200_fw3000_seed13_300s | pfo | ramp_d_bias | `urban_link_occupancy_total_veh` | 0.000 | 173.101 | -173.101 | 173.101 | -1.000 | 5.229 | 0.000 |
| pfo_ramp_d_bias_u2200_fw3000_seed13_300s | pfo | ramp_d_bias | `urban_movement_queue_total_veh` | 731.200 | 532.758 | 198.442 | 198.442 | 0.400 | 5.229 | 0.000 |
| pfo_sym_high_u2600_fw3400_seed13_600s | pfo | sym_high | `freeway_mean_speed_kph` | 84.508 | 85.996 | -1.488 | 6.192 | -0.013 | 18.556 | 0.000 |
| pfo_sym_high_u2600_fw3400_seed13_600s | pfo | sym_high | `freeway_segment_total_veh` | 162.395 | 219.641 | -57.245 | 57.245 | -0.258 | 18.556 | 0.000 |
| pfo_sym_high_u2600_fw3400_seed13_600s | pfo | sym_high | `freeway_total_veh` | 169.895 | 250.841 | -80.945 | 80.945 | -0.306 | 18.556 | 0.000 |
| pfo_sym_high_u2600_fw3400_seed13_600s | pfo | sym_high | `protected_accumulation_veh` | 342.300 | 411.869 | -69.569 | 74.049 | -0.178 | 18.556 | 0.000 |
| pfo_sym_high_u2600_fw3400_seed13_600s | pfo | sym_high | `ramp_queue_total_veh` | 7.500 | 31.200 | -23.700 | 27.780 | 0.853 | 18.556 | 0.000 |
| pfo_sym_high_u2600_fw3400_seed13_600s | pfo | sym_high | `total_model_vehicles` | 1096.695 | 1237.508 | -140.813 | 141.072 | -0.107 | 18.556 | 0.000 |
| pfo_sym_high_u2600_fw3400_seed13_600s | pfo | sym_high | `urban_link_occupancy_total_veh` | 0.000 | 287.338 | -287.338 | 287.338 | -1.000 | 18.556 | 0.000 |
| pfo_sym_high_u2600_fw3400_seed13_600s | pfo | sym_high | `urban_movement_queue_total_veh` | 926.800 | 699.330 | 227.470 | 227.470 | 0.341 | 18.556 | 0.000 |
