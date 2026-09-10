codex_area_sources_beta0_s13_20260910: 3300–3450 s

One held-action endpoint. TTT, TD, entries, event count and every accepted-flow count match the previous audited result exactly.

| Model exit category | TD vehicles |
|---|---:|
| freeway | 232.194462 |
| legsplit | 33.432726 |
| movement | 164.351541 |
| offramp_direct | 29.822067 |
| sc2001 | 5.229366 |
| arrival | 0.354307 |

Total model TD 465.384468; spatial-remap component 0.000000 (included in the categories above).

| Largest model exit route | Accepted vehicles | TD vehicles | Remap TD |
|---|---:|---:|---:|
| freeway:FW_W->external:terminal:FW_W | 169.648715 | 169.648715 | 0.000000 |
| freeway:FW_E->external:terminal:FW_E | 62.545747 | 62.545747 | 0.000000 |
| legsplit:SC1004_W_out | 91.473149 | 30.488000 | 0.000000 |
| movement:SC101_S_SC1_to_N_SC2005 | 27.894375 | 27.894375 | 0.000000 |
| offramp_direct:OR_D_W | 17.962549 | 17.962549 | 0.000000 |
| movement:SC109_W_SC108_to_E | 14.285034 | 14.285034 | 0.000000 |
| movement:SC6_S_SC12_to_N_SC103 | 13.326224 | 13.326224 | 0.000000 |
| offramp_direct:OR_F_W | 11.859517 | 11.859517 | 0.000000 |
| movement:SC1004_W_to_S | 11.703401 | 11.703401 | 0.000000 |
| movement:SC1002_S_SC105_to_N_SC2004 | 9.897425 | 9.897425 | 0.000000 |
| movement:SC5_S_SC11_to_N_SC102 | 7.397992 | 7.397992 | 0.000000 |
| movement:SC108_N_SC7_to_S | 7.343311 | 7.343311 | 0.000000 |
| movement:SC6_W_SC5_to_E_SC104 | 6.163062 | 6.163062 | 0.000000 |
| sc2001:outside_125 | 5.229366 | 5.229366 | 0.000000 |
| movement:SC107_W_SC1005_to_S | 4.704308 | 4.704308 | 0.000000 |
| movement:SC107_N_SC1_to_S | 4.245351 | 4.245351 | 0.000000 |
| movement:SC1004_offW_to_S | 3.901134 | 3.901134 | 0.000000 |
| movement:SC1001_E_SC1002_to_N_SC2002 | 3.490248 | 3.490248 | 0.000000 |
| movement:SC1004_offE_to_S | 3.454861 | 3.454861 | 0.000000 |
| movement:SC101_E_SC5_to_N_SC2005 | 3.428100 | 3.428100 | 0.000000 |

| Unique predicted boundary | Model vehicles | Physical exact sampled pair |
|---|---:|---:|
| 1220011503->10538 | 27.894375 | 56 |
| 173->10285 | 14.285034 | 50 |
| 1210018302->10205 | 13.326224 | 39 |
| 1220006803->10597 | 4.245351 | 31 |
| 1220018504->10197 | 6.163062 | 24 |
| 71->10642 | 19.059396 | 19 |
| 1220000201->10616 | 4.893609 | 17 |
| 427->10689 | 9.897425 | 11 |
| 1220014100->10418 | 7.397992 | 9 |
| 30->10694 | 3.214529 | 9 |
| 127->10695 | 3.649562 | 9 |
| 1220018401->10428 | 1.286601 | 9 |
| 329->10692 | 1.676639 | 7 |
| 52->10630 | 1.579257 | 7 |
| 183->10620 | 2.294785 | 6 |
| 1220018504->10198 | 2.984626 | 5 |
| 1210009402->10283 | 2.500000 | 5 |
| 1210012600->10250 | 1.147392 | 5 |
| 1220007401->10298 | 7.343311 | 4 |
| 1220014201->10510 | 3.428100 | 4 |

Exact replay comparison covers accounting metrics and all accepted-flow counts, not full state identity. Only a unique physical path whose crossings close its route TD is mapped to a boundary pair. Other model exit categories are left unmapped. A skipped connector in 1s recording can change the sampled pair; exact-pair counts are not a complete movement-flow measurement. Proportional grouped-stock remapping, terminal inference and interior disappearance retain the original audit definitions.
