---
name: vissim-lane-delay-dimension-bug
description: plant 지연 산식이 차로수로 안 나눠 거리를 2.7배 과대 - 상쇄하면 예측은 좋아지고 폐루프 J 는 나빠진다
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-17T02:23:08.147Z
---

vendor `src/models/urban_queue_model.py:622` 의 `_link_delay_steps` 가 큐 꼬리까지 거리를
`available[veh] × 차량길이 / 1000` 으로 잡는다. `available` 은 **전 차로 합계 대수**라
차로수로 안 나눈 만큼 거리가 부풀려진다 — 실측 배수가 정확히 차로수(중앙 2.69, p90 4.04).

vendor 수정 금지라 `urban_link_speed_kph` 로 상쇄한다. 그 필드는 이 산식 **한 곳에서만**
읽히므로 속도에 차로수를 곱하면 `distance/speed` 가 항등으로 같아진다. 하한
(`OBSERVED_SPEED_DELAY_CAP_RATIO`)이 주입 뒤 `max()` 로 걸리니 하한을 먼저 적용하고 곱한다.
플래그 `RW_LANE_DELAY_CORRECTION`, **기본 꺼짐**.

**왜 껐나 (2026-08-17 실런 A/B 9런, 시드 13, 1800 s, 제어창 [900,1800])**

| | rollout 예측 | 폐루프 J |
|---|---|---|
| 스텝3 보존단위 | 54.3% → **47.7%** (개선) | |
| d0.75 | | +0.000 (결정 동일, action CSV 바이트 동일) |
| d1.00 | | **+3.389 veh·h (+0.433%)** 악화 |
| d1.25 | | **+2.217 veh·h (+0.216%)** 악화 |

**물리적으로 옳은 지연이 더 나은 제어로 이어지지 않는다.** 이게 이 프로젝트의 열린 긴장이다.

한계 둘: leader 탐색폭이 1(fast-smoke)이라 "탐색폭 1에서 악화"이지 보편 결론이 아니다.
그리고 Δ 는 rollout 지연 단축 + 그로 인해 달라진 warm-start 버퍼의 **합**이라 메커니즘
분해가 아니다 — 분해하려면 `lane × RW_WARMSTART_SEC{0,900}` 4셀이 필요하다.

곁가지: `RW_NARROW_AXIS_SG` 는 통제 movement 275개 중 **3개(전부 SC5)** 만 움직여 ΔJ = 0.
검증 경로 좁힘(`RW_VALIDATION_FIXED_SIGNAL`)이 예측 오차를 44.9%→36.4% 로 줄인 것과 **다른
플래그**다. 혼동하면 안 된다.

관련: [[vissim-workstation-state]] [[vissim-plant-fidelity-three-layers]]
