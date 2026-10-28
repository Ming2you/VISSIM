---
name: vissim-terminal-cost-and-f10f11-20261001
description: "terminal cost 오프라인(plant) 검증 = 판단 불가·선택 거의 불변(RM 은 plant 에 capacity drop 없어 못 이김, plant FW_W 장기 적체 VISSIM 3배) / F10(입구 경계)·F11(FW_W ρc) v3c2 평가 = F10-E·F11 FAIL, 입구 속도 단독은 서술상 통과 (2026-10-01)"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-30T23:34:08.549Z
---

**terminal cost (scratchpad termcost/, v3c1 R-obs 8상태 × 23후보, 286 롤아웃, 독립 검증)**
- 사전 선언 판정 inconclusive. 종단비용 b1 은 argmin 을 7/8 에서 안 바꿈. 큰 오류는 3600 하나(모든 채점기가 C19=SC1001+SC1004 off-ramp 현시 +10 선택, C13 성분이 지연 피해 → T+3600 에서 +17 veh·h) — T+450 재고 기반 종단비용은 이런 지연 효과를 못 봄. 3600 하나 빼면 '병목 아님'.
- RM 조임은 한 번도 C00 을 못 이김(plant capacity_drop_discharge_phi=1.0) → 종단비용으로 RM 이득을 만들 수 없음. TC1 은 오히려 미터링을 손해로 교정.
- 도시 방류(C11) 이득은 plant 의 **허구 FW_W 장기 적체**(T+1800 1,569–1,956대 vs VISSIM 595–673)를 푸는 데서 나옴 → plant 의존.
- 결론: 지금 plant 에선 종단비용이 병목 아님. 우선순위는 plant 충실도(FW_W 장기 발산, 방류 기구).

**F10/F11 (scratchpad f10f11/, 워크트리 sim3-n31-f10f11 커밋 dda0933·0ff3409 로컬, 독립 검증)**
- F10-E(입구 관측 속도 + 셀0 v_free 117.1) FAIL: bias −19~−21(기준 15). 분해: 입구 속도만(A_i) −7~−9 통과, v_free 117 만 −31~−34 악화 → 둘이 상쇄. A_i 는 서술 팔이라 채택하려면 새 선언 필요.
- F10-W: F10 팔 vs BASE 통과(셀0 MAE 5/5) 이나 배포 추정기(MER)가 오프라인보다 +6 km/h(EQ 불충족), FW_W 셀0 v_free 는 규칙 실패로 셀1 행 113.27 대체(B1-R, 사용자 미확인).
- F11(FW_W 셀 0–6 ρc 24.58, 혼잡가지 속도 적합) FAIL: 2b·LOSO 는 통과하나 한 스텝/450 s 예측 크게 악화(R1 MAE 61.8→97.9, 450 s 70→177, 엮임 구역 W 8.6→18.7), LOSO ρc 로도 같음 → 구조 문제. 상류 용량만 올리면 엮임 병목(셀 7–10) 앞에 쌓임.
- 선택 점검(v3c1 상태, 서술): 키 켜면 VSL 구역 명령 3/4 상태 변경, 신호 녹색 다수 변경, 미터 불변. SDMPC 는 경사 기반이라 후보 1개 → 순위 지표 정의 불가.

**사용자 결정(10-01)**: F10 보류(입구 속도 v2 재선언도 안 함) / FW_W 는 구조 진단 먼저(워크플로 wf_c46ed1ef-fb2, 산출 scratchpad fww-struct/FWW_STRUCT_PROPOSAL.md) — 코드 변경은 제안 승인 뒤. 동시에 C3 2차 분해(U7·U8, wf_e9b238e4-7bb)와 v3c2 재핀 계획(단일값 VSL·10490 일반화·state.py 정렬·replay action_contract, wf_9f23a95f-eb5, 산출 D:/VISSIM_runs/20260930_v3c2/reports/repin/) 진행.

**Why:** 사용자가 "terminal cost 없어서 장기 선택을 못 하나" 물음 + F10/F11 승인. 둘 다 결론은 "plant 구조가 먼저".
**How to apply:** FW_W 는 용량 계수 말고 엮임 병목·장기 발산 구조 진단이 먼저. F10 은 입구 속도 단독(v2)을 새 선언으로 재평가 후보. 관련 [[calibration-roadmap-after-plant-fix-20260930]], [[vissim-freeway-entry-dsd40-defect-20260930]].
