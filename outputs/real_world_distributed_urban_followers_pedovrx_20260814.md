# Real-world distributed urban followers, copy-only config

Generated on 2026-07-28.

## Selected Urban Signal Players

| player | sc_no | name | signal heads | observed links |
| --- | ---: | --- | ---: | ---: |
| U_SC1 | 1 | 구룡초교 | 14 | 4 |
| U_SC5 | 5 | 도곡역 | 31 | 10 |
| U_SC6 | 6 | 대치역 | 18 | 4 |
| U_SC11 | 11 | 개포고교 | 10 | 5 |
| U_SC12 | 12 | 영동5교 | 12 | 4 |
| U_SC101 | 101 | 매봉터널 | 20 | 4 |
| U_SC105 | 105 | 포이사거리 | 12 | 4 |
| U_SC107 | 107 | 구룡터널 | 17 | 4 |
| U_SC108 | 108 | 구룡마을입구 | 16 | 5 |
| U_SC109 | 109 | 개포3,4단지 | 12 | 3 |
| U_SC1001 | 1001 |  | 12 | 5 |
| U_SC1002 | 1002 |  | 12 | 4 |
| U_SC1003 | 1003 |  | 9 | 3 |
| U_SC1004 | 1004 |  | 17 | 4 |
| U_SC1005 | 1005 |  | 6 | 3 |

## Monitoring-Only Signal Controllers

| monitor | sc_no | name | signal heads | observed links |
| --- | ---: | --- | ---: | ---: |
| MON_SC4 | 4 | 청실종합 | 30 | 8 |
| MON_SC7 | 7 | 개포도서관 | 10 | 5 |
| MON_SC9 | 9 | 대치은마아파트 | 19 | 7 |
| MON_SC10 | 10 | 대치선경아파트 | 7 | 2 |
| MON_SC13 | 13 | 개포주민센터 | 9 | 4 |
| MON_SC14 | 14 | 대치미도아파트 | 11 | 3 |
| MON_SC15 | 15 | 개포경남아파트 | 12 | 4 |
| MON_SC16 | 16 | 경기여고 | 10 | 4 |
| MON_SC102 | 102 | 한티역 | 23 | 6 |
| MON_SC103 | 103 | 은마아파트입구 | 19 | 4 |
| MON_SC104 | 104 | 학여울역 | 23 | 4 |
| MON_SC106 | 106 | 대모산사거리 | 15 | 4 |
| MON_SC2001 | 2001 |  | 10 | 4 |
| MON_SC2002 | 2002 |  | 12 | 4 |
| MON_SC2003 | 2003 |  | 9 | 3 |
| MON_SC2004 | 2004 |  | 12 | 4 |
| MON_SC2005 | 2005 |  | 14 | 4 |
| MON_SC9001 | 9001 | 우리은행포이 | 9 | 5 |
| MON_SC9003 | 9003 | 대도초교 | 8 | 2 |

## Files

- control mapping: `evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_pedovrx_20260814.json`
- detector mapping: `evaluation\real_world_modi_control_distributed_20260728\detector_local_mapping_distributed_pedovrx_20260814.json`
- player config: `evaluation\real_world_modi_control_distributed_20260728\player_config_distributed_pedovrx_20260814.json`
- P-Stack tuning: `evaluation\configs\real_world_modi_pstack_distributed_pedovrx_20260814.json`
- generated VBS config: `evaluation\generated\real_world_modi_control_config_distributed_pedovrx_20260814.vbs`
- watchdog wrapper: `scripts\run_real_world_single_watchdog_distributed_pedovrx.ps1`

## Structure

- Urban follower count in model config: `15`
- Controlled urban SC agent count in detector mapping: `15`
- Monitoring-only SC agent count in detector mapping: `19`
- Observable links scanned by VBS: `1208`
- Freeway/ramp VSL and metering mapping are copied from the validated base mapping.
- Signal-head link queue attribution is derived from `.inpx` signal-head/SG names: EB/WB links feed EW/major movements and NB/SB links feed NS/minor movements.
- In `core15`, SC1 is strict approach-only; ramp/off-ramp observations stay in freeway/base local observation rather than the SC1 urban follower.
- `.layx` is treated as visual/layout validation only; `.inpx` is the plant and topology source.
- Monitoring-only signals are not emitted as `kind=signal` rows in the action CSV.
- Original files are not overwritten; use the distributed wrapper/config paths explicitly.
