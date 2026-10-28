# RB_RULE_ADD1 — 비교 열 하나 더함 (데이터 뒤 추가, 2026-10-27 05:35 KST)

- 무엇: RB_RULE §4 K7 의 비교 기준에 **codex 머리 서비스 곡선** 열을 더합니다. 다른 정의·블록·조건·숫자는 바꾸지 않습니다.
- 왜 (데이터 뒤): K9 의 K0b 검산에서 B 명령 CSV metadata `group_rate_vph` 가 FW_E 미터 4개(10639·10681·10490·10484)에서 표 × 차로 와 달랐습니다(예: RM_C10639 g8 1,440 대 표 1,166.4) [실행 `RB/out/discharge.json` `/runs/b31/K0b_group_rate`]. 따라가 보니 B 설정에 미터별 곡선 `physical_ramp_head_service_veh_per_cycle` 이 따로 있고(FRZ_B1 `diagnostics/b0_v3c3/config_b0_v3c3.json:8161-8202`), codex lane plant 가 이 곡선으로 그 미터의 `service_by_green_veh_h` 를 덮어씁니다(FRZ_B1 `evaluation/controllers/lane_plant_runtime.py:616-620`) [읽음]. 곧 B 제어기의 모형 표는 FW_W 미터 4개 = `per_lane_veh_per_cycle`, FW_E 미터 4개 = 머리 서비스 곡선입니다. 이 곡선은 D-K9-91 첫 묶음 후보의 "머리 서비스 표" 와 같은 이름의 기구로 봅니다 [추론].
- 더하는 열: 미터·차로·g 마다 `머리 곡선 = 360 × curve[미터][g] ÷ 차로 수` (veh/h/차로; 10681 은 곡선이 2차로 합이라 ÷ 2) 와 1차 중앙의 비. FW_W 미터는 곡선이 없어 "해당 없음".
- 도구: `RB/tools/rb_headcurve.py` (`RB/out/discharge.json` 과 설정만 읽음, 가벼움). sha 는 실행 전 LOG 에 적습니다.
