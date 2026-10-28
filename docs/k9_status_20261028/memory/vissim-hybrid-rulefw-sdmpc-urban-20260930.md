---
name: vissim-hybrid-rulefw-sdmpc-urban-20260930
description: "하이브리드 시험(고속도로 Carlson MTFC-VSL+ALINEA 규칙 × 도시 SDMPC, v3c1 s31 9000 s) 결과와 종료 — 사용자가 확장(S5·split-range·큐 override)까지 중단시킴"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-29T18:57:57.247Z
---

- 시험용 별개 자료: 워크트리 D:/VISSIM-merge/sim3-n31-hybrid, 브랜치 claude/hybrid-rulefw-sdmpc-urban-20260929(92fa4b8, 로컬만), 런 D:/VISSIM_runs/20260929_hybrid/sdmpc31_v3c1_hybrid_s31b(EXIT 0, 61결정, FRZ sdmpc31_92fa4b8e_202609291737). 비교 스크립트·결과 = 세션 scratchpad hybrid/final/final_compare.json.
- 결과(무제어 s31 대비, 9000 s): ① FW_E 본선 +72.2(+3.4%) ② 동측 local +30.6 ③ Ω −186.5(−2.6%), 도시 Ω +148.0(+6.0%) ④ 전체+미삽입 −180.4(−1.4%).
- Ω 이득은 오프램프 −290(FW_E off-ramp 링크 127 −203 = OR_D_E1)·FW_W 본선 −95·FW_W 진입 1099 대기 −213 에서 나왔다. 규칙층은 FW_W 에서 아무것도 안 했다(미터 전부 10, VSL 110) → 도시 SDMPC 또는 궤적 분기 효과 [추론].
- FW_E 악화 = 링크 2 셀 6–9(3.1–5.1 km, 10639·10681 합류 상류)에 VSL S4 가동 구간(2250–4650 s)에만 대기 증가. B2(셀 13–14)는 무변화 → MTFC 가 비용만 치르고 이득(용량 강하 회피)은 없음. ALINEA 10639 는 3600 s 부터 최소 녹색 2 s 고착.
- 도시 악화 = 링크 174 +203(SC109 p3 굶김, [[vissim-boundary-movement-capacity-206]])·링크 66 +138.
- 시드 1개라 J1 상 판정 아님. 사용자가 S5 구역·split-range·큐 override 3팔 확장을 요청했다가 곧바로 "하이브리드 그만" (2026-09-30) → 워크플로 중단, 코드 변경 없음.

**Why:** 하이브리드 결과를 다시 물을 때 재계산 없이 답하고, 사용자가 접은 방향을 다시 제안하지 않기 위해.
**How to apply:** 하이브리드 관련 새 작업은 사용자가 다시 요청할 때만. 정리 후보(옛 FRZ 43150c8e·d34fd1aa, sim3-n31-hybrid-base, 브랜치)는 사용자 요청 시에만 삭제. 관련 [[vissim-fwe-plant-structure-20260927]], [[vissim-vsl-fixed-dsd-20260928]].
