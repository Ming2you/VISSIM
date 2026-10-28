---
name: vissim-sdmpc31-live-check-tools-blind
description: "resolve_live_controller.py 와 whose_code.py 는 SDMPC-31 의 LIVE 경로를 판정하지 못한다(21셀 top-level cfg·wu-link 리더만 봄, effective_lane_profile 거짓 음성). 코드 추적 + T4/T5 훅 호출 계수 + 배포 메타로 판정 (2026-09-27 P0-1)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-27T11:12:35.298Z
---

FW_E P0-1(scratchpad fwe-struct/p0/P0_REPORT.md):
- `resolve_live_controller.py --controller wu-link` 는 "freeway 셀 2×21=42" 를 찍는다. SDMPC-31 롤아웃은 31셀 LPR 성분이고, 리더·가격·Nash 절은 SDMPC 가 우회한다.
- `whose_code.py` 는 vendor/NumSim-mine/src 만 훑어서 `effective_lane_profile` 을 "LIVE 0 · DEAD 5" 로 판정했지만, 실제로는 T4 롤아웃(450 s)마다 450회 호출된다(AFA:158).
- SDMPC-31 에서 LIVE 인 것: AFA `_freeway_substep_events`(lane_coupling 경유), 어댑터 φ·세그먼트 패치(스텝당 φ 발화 경계 4개 — 18|19 만 실제, 나머지 3개는 부동소수 4e-16), Carlson `literature_desired_speed`/`VSLExposure`, `joint_owner_game.py:146`(매 결정). `joint_owner_neighbors.py:1172-1176`·`:1260` 은 SDMPC 에서 호출 0.
- 배포 경로의 램프 gap 수용 노드 적용 위치는 `lane_ramp_runtime.py:104-128` 이다(CH `:889-924` 는 T4 rollout 경로).
- 결정 메타 `lane_drop_cell_FW_E=12`/`lane_drop_cells=1` 은 정제 **전** 21셀 값이라 plant 발화와 다르다.

**Why:** 해석기 결과를 믿고 LIVE 코드를 DEAD 로 오판하면 고칠 곳을 놓친다([[vissim-arm-confusion-whose-code]], [[vissim-resolve-live-controller-first]] 는 wu-link 옛 팔 기준).
**How to apply:** SDMPC-31 코드를 고치기 전에는 sitecustomize 훅으로 T4/T5 재생의 호출 수를 세고(p0/p0356/hook_site), 배포 메타(`controller_variant`, `sdmpc_active`, `lane_plant_enabled`)를 확인한다.
