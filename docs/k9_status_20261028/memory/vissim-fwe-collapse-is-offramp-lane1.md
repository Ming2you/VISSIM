---
name: vissim-fwe-collapse-is-offramp-lane1
description: FW_E 붕괴 원인 확정 — on-ramp도 하류 spillback도 아니고 OR_F_E off-ramp 출구 대기열이 차로 1을 막는 것. 차로별 실측이 지문
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-28T05:35:48.591Z
---

2026-09-09 확정. x15 무제어·제어 런이 **동일하게** 무너지므로 제어 실패가 아니라 물리다.

**발생 순서 (무제어, 셀별 최초 ρ>27):**
`셀8 t=1350 → 7 t=1500 → 6 t=1650 → 5·0 t=1800 → 4 t=1950 → 2·3 t=2100 → 9 t=2400`
셀 8 에서 시작해 **상류로만** 번진다. 하류 셀 10·11 은 끝까지 자유류(ρ 3~11, v 90~103)
→ **하류 spillback 아님.** 합류셀(셀 9, R_F_E)은 1,050 초 늦고 t=1500 엔 오히려 66 km/h 로 회복
→ **on-ramp 아님.**

**차로별 실측이 결정적이다** (`vehicle_records.records` 의 `lane_no`, 링크 2):
```
t=1200 셀8  차로1 30대 20.0kph | 차로2  8대 69.8 | 차로3  3대 126.6 | 차로4  7대 104.3
t=1350 셀8  차로1 54대  7.8kph | 차로2 14대 29.3 | 차로3 15대  53.5 | 차로4 16대  74.3
t=2700 셀8  차로1 72대  2.0    | 차로2 72대  2.4 | 차로3 37대  11.6 | 차로4 29대  14.9
```
차로 1 만 죽는데 차로 3·4 가 126·104 로 달린다 = **출구 대기열**. 전 차로 잠김(t=2700)은 결과다.
셀 8 = `off_ramp_segment_index[OR_F_E]` 다이버지.

**도시부 역류도 아니다.** OR_F_E 착지 커넥터 10682 는 **t=600 부터 19~23 대로 포화**(본선은 그때
완전 자유류)인데, 하류 도시 회랑(링크 68·121·123)은 끝까지 안 막힌다 — 링크 123 이 시뮬 내내
83~104 km/h. 출구 자신의 처리량 문제다.

**함의**: 동측 on-ramp 미터링·VSL·capacity drop 은 전부 원인이 아닌 곳을 겨눈다. 동측 램프는
합류 방류의 9~12% 뿐이라 애초에 권한이 부족하다. 레버가 있다면 off-ramp 배출 쪽이다.

관련: [[vissim-offramp-lane-closure-trigger-starved]] · [[vissim-capdrop-refuted-merge-structural]] ·
[[vissim-metering-grid-blindspot]]

**v3b 재검증 (2026-09-27):** 이 결론은 옛 21셀 시나리오 것이다. v3b 에서는 [[vissim-fwe-plant-structure-20260927]] 참조 — 붕괴 기원은 10681 합류 차로 2, off-ramp 차로폐쇄는 배포 프로필에서 꺼져 있음(occupancy_lane_loss false). 차로 1 저속은 출구 대기열이 아니고 체제와 무관하다(P0-4; 가장 느린 차로는 차로 2, 예외 4.7–5.0 km 에서 출구행 초과분 기여 약 3%p).
