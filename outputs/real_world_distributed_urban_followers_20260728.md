# Real-world distributed urban followers, copy-only config

Generated on 2026-07-28.

## Selected Urban Signal Players

| player | sc_no | name | signal heads | observed links |
| --- | ---: | --- | ---: | ---: |
| U_SC1 | 1 | 구룡초교 | 54 | 17 |
| U_SC2 | 2 | 개원초교(보) | 17 | 10 |
| U_SC3 | 3 | 수도공고(보) | 9 | 5 |
| U_SC4 | 4 | 청실종합 | 30 | 8 |
| U_SC5 | 5 | 도곡역 | 31 | 10 |
| U_SC6 | 6 | 대치역 | 18 | 4 |
| U_SC7 | 7 | 개포도서관 | 10 | 5 |
| U_SC8 | 8 | 개포중(보) | 6 | 4 |
| U_SC9 | 9 | 대치은마아파트 | 28 | 10 |
| U_SC10 | 10 | 대치선경아파트 | 7 | 2 |
| U_SC11 | 11 | 개포고교 | 10 | 5 |
| U_SC12 | 12 | 영동5교 | 12 | 4 |
| U_SC13 | 13 | 개포주민센터 | 9 | 4 |
| U_SC14 | 14 | 대치미도아파트 | 11 | 3 |
| U_SC15 | 15 | 개포경남아파트 | 12 | 4 |
| U_SC16 | 16 | 경기여고 | 10 | 4 |
| U_SC17 | 17 | 개포주공3단지(보) | 8 | 2 |
| U_SC18 | 18 | 구룡중(보) | 4 | 2 |
| U_SC19 | 19 | 개포우체국(보) | 5 | 3 |

## Files

- control mapping: `evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_19sc_20260728.json`
- detector mapping: `evaluation\real_world_modi_control_distributed_20260728\detector_local_mapping_distributed_19sc_20260728.json`
- player config: `evaluation\real_world_modi_control_distributed_20260728\player_config_distributed_19sc_20260728.json`
- P-Stack tuning: `evaluation\configs\real_world_modi_pstack_distributed_19sc_20260728.json`
- generated VBS config: `evaluation\generated\real_world_modi_control_config_distributed_19sc_20260728.vbs`
- watchdog wrapper: `scripts\run_real_world_single_watchdog_distributed.ps1`

## Structure

- Urban follower count in model config: `19`
- Local-observation agent count in detector mapping: `19`
- Observable links scanned by VBS: `121`
- Freeway/ramp VSL and metering mapping are copied from the validated base mapping.
- Original files are not overwritten; use the distributed wrapper/config paths explicitly.
