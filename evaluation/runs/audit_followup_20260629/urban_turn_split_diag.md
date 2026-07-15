# Urban turn-split: actual (route_manifest) vs assumed (detector weights)

For each approach link, 'actual' = share of route rel_flow going to each downstream link; 'assumed' = detector_local_mapping link_to_movements weights. Large gaps are urban turn-split calibration targets.


## approach link 1  (in_A_left)  total_rel=6.80
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 5 | A_to_B |  76.5% | |
| 7 | A_to_D |  23.5% | |

assumed movement weights: A_W_to_E=50%(boundary_in), A_W_to_N=25%(boundary_in), A_W_to_S=25%(boundary_in)

## approach link 3  (in_A_top)  total_rel=6.40
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 5 | A_to_B |  76.6% | |
| 7 | A_to_D |  23.4% | |

assumed movement weights: A_N_to_S=50%(boundary_in), A_N_to_E=25%(boundary_in), A_N_to_W=25%(boundary_in)

## approach link 5  (A_to_B)  total_rel=9.10
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 11 | B_to_C |  59.3% | |
| 13 | B_to_E |  40.7% | |

assumed movement weights: B_W_to_E=50%(internal), B_W_to_N=25%(boundary_out), B_W_to_S=25%(internal)

## approach link 6  (B_to_A)  total_rel=2.90
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 7 | A_to_D | 100.0% | |

assumed movement weights: A_E_to_W=50%(boundary_out), A_E_to_N=25%(boundary_out), A_E_to_S=25%(internal)

## approach link 7  (A_to_D)  total_rel=1.50
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 25 | link25 | 100.0% | |

assumed movement weights: D_N_to_onW=25%(on_ramp), D_N_to_onE=25%(on_ramp), D_N_to_E=25%(internal), D_N_to_W=25%(boundary_out)

## approach link 8  (D_to_A)  total_rel=2.00
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 5 | A_to_B | 100.0% | |

assumed movement weights: A_S_to_N=50%(boundary_out), A_S_to_E=25%(internal), A_S_to_W=25%(boundary_out)

## approach link 9  (in_B_top)  total_rel=7.70
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 11 | B_to_C |  41.6% | |
| 6 | B_to_A |  37.7% | |
| 13 | B_to_E |  20.8% | |

assumed movement weights: B_N_to_S=50%(boundary_in), B_N_to_E=25%(boundary_in), B_N_to_W=25%(boundary_in)

## approach link 11  (B_to_C)  total_rel=1.10
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 19 | C_to_F | 100.0% | |

assumed movement weights: C_W_to_E=50%(boundary_out), C_W_to_N=25%(boundary_out), C_W_to_S=25%(internal)

## approach link 12  (C_to_B)  total_rel=7.00
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 6 | B_to_A |  90.0% | |
| 13 | B_to_E |  10.0% | |

assumed movement weights: B_E_to_W=50%(internal), B_E_to_N=25%(boundary_out), B_E_to_S=25%(internal)

## approach link 13  (B_to_E)  total_rel=6.00
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 27 | E_to_F |  75.0% | |
| 24 | E_to_D |  25.0% | |

assumed movement weights: E_N_to_E=50%(internal), E_N_to_W=50%(internal)

## approach link 14  (E_to_B)  total_rel=3.00
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 6 | B_to_A |  86.7% | |
| 11 | B_to_C |  13.3% | |

assumed movement weights: B_S_to_N=50%(boundary_out), B_S_to_E=25%(internal), B_S_to_W=25%(internal)

## approach link 15  (in_C_top)  total_rel=6.60
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 12 | C_to_B |  72.7% | |
| 19 | C_to_F |  27.3% | |

assumed movement weights: C_N_to_S=50%(boundary_in), C_N_to_E=25%(boundary_in), C_N_to_W=25%(boundary_in)

## approach link 18  (in_C_right)  total_rel=6.60
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 12 | C_to_B |  63.6% | |
| 19 | C_to_F |  36.4% | |

assumed movement weights: C_E_to_W=50%(boundary_in), C_E_to_N=25%(boundary_in), C_E_to_S=25%(boundary_in)

## approach link 19  (C_to_F)  total_rel=2.10
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 31 | link31 |  66.7% | |
| 28 | F_to_E |  33.3% | |

assumed movement weights: F_N_to_onW=25%(on_ramp), F_N_to_onE=25%(on_ramp), F_N_to_E=25%(boundary_out), F_N_to_W=25%(internal)

## approach link 20  (F_to_C)  total_rel=1.00
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 12 | C_to_B | 100.0% | |

assumed movement weights: C_S_to_N=50%(boundary_out), C_S_to_E=25%(boundary_out), C_S_to_W=25%(internal)

## approach link 21  (in_D_left)  total_rel=8.10
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 8 | D_to_A |  46.9% | |
| 23 | D_to_E |  40.7% | |
| 25 | link25 |  12.3% | |

assumed movement weights: D_W_to_E=50%(boundary_in), D_W_to_N=25%(boundary_in), D_W_to_onW=12%(boundary_in), D_W_to_onE=12%(boundary_in)

## approach link 23  (D_to_E)  total_rel=3.70
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 27 | E_to_F |  89.2% | |
| 14 | E_to_B |  10.8% | |

assumed movement weights: E_W_to_E=50%(internal), E_W_to_N=50%(internal)

## approach link 24  (E_to_D)  total_rel=3.20
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 25 | link25 | 100.0% | |

assumed movement weights: D_E_to_W=50%(boundary_out), D_E_to_N=25%(internal), D_E_to_onW=12%(on_ramp), D_E_to_onE=12%(on_ramp)

## approach link 26  (OR_D_W)  total_rel=1.40
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 8 | D_to_A |  71.4% | |
| 23 | D_to_E |  28.6% | |

assumed movement weights: D_offW_to_N=50%(off_ramp), D_offW_to_E=25%(off_ramp), D_offW_to_W=25%(off_ramp), D_offE_to_N=50%(off_ramp), D_offE_to_E=25%(off_ramp), D_offE_to_W=25%(off_ramp)

## approach link 27  (E_to_F)  total_rel=4.40
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 31 | link31 |  75.0% | |
| 20 | F_to_C |  25.0% | |

assumed movement weights: F_W_to_E=50%(boundary_out), F_W_to_N=25%(internal), F_W_to_onW=12%(on_ramp), F_W_to_onE=12%(on_ramp)

## approach link 28  (F_to_E)  total_rel=5.40
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 24 | E_to_D |  51.9% | |
| 14 | E_to_B |  48.1% | |

assumed movement weights: E_E_to_W=50%(internal), E_E_to_N=50%(internal)

## approach link 30  (in_F_right)  total_rel=8.10
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 28 | F_to_E |  53.1% | |
| 20 | F_to_C |  34.6% | |
| 31 | link31 |  12.3% | |

assumed movement weights: F_E_to_W=50%(boundary_in), F_E_to_N=25%(boundary_in), F_E_to_onW=12%(boundary_in), F_E_to_onE=12%(boundary_in)

## approach link 32  (OR_F_W)  total_rel=1.40
| downstream link | downstream model | actual share | kind |
| --- | --- | ---: | --- |
| 20 | F_to_C |  71.4% | |
| 28 | F_to_E |  28.6% | |

assumed movement weights: F_offW_to_N=50%(off_ramp), F_offW_to_E=25%(off_ramp), F_offW_to_W=25%(off_ramp), F_offE_to_N=50%(off_ramp), F_offE_to_E=25%(off_ramp), F_offE_to_W=25%(off_ramp)
