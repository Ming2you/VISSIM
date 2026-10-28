---
name: feedback-minimize-new-vissim-runs
description: "사용자가 \"작업마다 run 을 새로 돌려 보정하는데 꼭 그래야 하냐\" 고 물음(10-01) — 보정은 기존 FZP/R-obs 자료 은행 우선, 새 VISSIM 런은 망 변경·반응 측정·폐루프에만, 증명용 런 최소화, 망 변경은 모아서"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-10-01T07:37:47.331Z
---

새 VISSIM 런이 정당한 경우는 셋뿐: (1) 망·시나리오가 바뀌어 옛 FZP 가 무효, (2) 제어 반응 측정(N1/N1F 계단, N2 같은 상태 짝), (3) 폐루프 평가. plant 상태 예측 보정·정적 점검·구조 진단은 기존 자료 은행(v3b/v3c1/v3c2=v3c3 NC fit5, R-obs v3c1, N1·N1F, hybrid·S1·S0e)으로 먼저 한다. 바이트 동일이 예상되는 증명용 런은 1시드 또는 논증으로 대신하고 기록한다. 망 변경은 모아서 한 번에(v3c→v3c1→v3c2→v3c3 를 며칠 새 바꾸며 매번 NC 재실행한 것이 반성점; v3c3 NC 6런은 새 정보 없음).

**Why:** 사용자가 런 남발을 지적(2026-10-01). 다만 같은 질문에서 재핀 뒤 R-obs·RM 3팔은 "계획대로" 돌리기로 함 — 이미 승인된 계획은 유지.
**How to apply:** 새 런을 제안할 때 위 세 경우 중 무엇인지 밝히고, 기존 자료로 대체 가능한지 먼저 확인해 말한다. 관련 [[calibration-roadmap-after-plant-fix-20260930]].
