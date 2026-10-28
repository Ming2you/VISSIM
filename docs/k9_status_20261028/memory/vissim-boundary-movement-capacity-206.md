---
name: vissim-boundary-movement-capacity-206
description: "경계 movement(boundary_out/in) 용량이 정규화 상수 206.53 veh/h-녹색/차로에 남아 실측의 약 1/9 — 헤드 하한이 internal kind 에만 걸림. S1 SC109 p3 굶김(+252)의 근본원인, 50:50 큐 분할은 기여 거의 0 (2026-09-27)"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-27T08:16:13.979Z
---

SC109 진단(scratchpad sc109-diag/SC109_DIAG.md, 적대적 검토 거침):
- `install_movement_capacity_by_lanes` 가 per_lane = 330×N/Σ차로 = **206.53** 을 모든 movement 에 깔고(perimeter "all"), 헤드 관측 하한은 `urban.capacity.lane_group_kinds` 기본 `["internal"]` 에만 적용 → boundary_out/boundary_in 은 영원히 206.53×차로. SC109 서측 직진 619.6 vs VISSIM 헤드 5,580, 동측 826 vs ~7,600, 북측 619.6.
- plant 반사실(S1 상태 3600/6300, 편미분): 서측 직진 용량만 2,541 로 올려도 "p3+20/p4−20" ΔJ +0.76→−1.72 (부호 반전). 50:50→β 분할은 +0.759→+0.757 (무효, 좌회전 비용↓와 북측 하류 이득↓ 상쇄).
- 결함은 S0e·S1 두 트리 모두 동일(기존 결함). **교차 재생 28회로 판정(09-27, scratchpad xreplay/XREPLAY_RESULT.md): SC109 p3 는 설정이 아니라 상태를 따라간다.** 1800–2700 s 설정 효과 합 p3 +0.9/+0.6 s vs 런 격차 −12.3 s(3600 s −18.2). S1 상태를 기본 설정으로 재생해도 p3 가 똑같이 떨어진다. U1 은 S1 상태에서만 p2 를 +1.5 s/결정 올리고 p4 에서 가져감. 재현 확인 2건 비트 동일. → 경로 의존, S1 +287 을 U1+U3 탓으로 돌리지 말 것. S1 은 3600–4500 s 최대 수요에서 잠김 → 되먹임 → 9000 s 까지 결손 442대.
- 동측 접근로는 Ω 밖이라 p3 가 유입 벌점을 지는데, 그 절반은 동측 용량 결함 산물. 헤드 하한 `qualified/녹색` 은 비포화 접근로에서 과소라 C1(lane_group_kinds 에 boundary 추가)은 포화된 서측 직진만 고침; 동·북은 U4(포화 방류 핀 표)+U5 필요.
- VISSIM 부수 현상: 직진 큐가 174 차로 4 를 막아 SG5 녹색의 64% 가 빈 좌회전 차로. 결정점 1081 이 10112 합류점 상류라 link 21 차량은 경로 없음(차로로 행선).
- 재생 도구 주의: VSL 이 110 아닌 런은 `action_contract` 때문에 DIFFERENT 로 나온다(action·objective 는 바이트 동일).

**Why:** "도시 plant 가 현시를 굶긴다"를 50:50 분할이나 β 탓으로 다시 오진하지 않게.
**How to apply:** 도시 현시 굶김을 보면 먼저 그 movement 의 kind 와 plant 용량(dump)을 보라. 수정 후보 C1~C6 는 SC109_DIAG.md §4. 관련 [[vissim-urban-batch1-and-rmcal-20260926]], [[vissim-queue-projection-fixed-fraction]].
