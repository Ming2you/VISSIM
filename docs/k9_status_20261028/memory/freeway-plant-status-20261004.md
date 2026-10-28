---
name: freeway-plant-status-20261004
description: "배포(K7 6c4c740) 고속도로 plant 실측 현황(10-04 코드 대조·검증): 31셀 집계 METANET, 병목 방류 제약 없음, φ 3.0 살아 있음(F2 φ0 승인됐으나 미구현), FW_W VSL 은 legacy 법칙, 입구 속도 110/123.2 고정, 고속도로 206.53 은 10491·10481 뿐(SA 소유), plant 는 GB-9 에서 VSL 110·미터 10만 고름"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-10-04T11:26:42.679Z
---

보고서: scratchpad fw_status/FREEWAY_STATUS.md(검증 반영), A_CODE.md·B_FIDELITY.md·C_PLAN.md·VERIFY.md.

- 구조: 방향별 31셀 집계 METANET(차로 구분 없음), 150 s 마다 obs150 으로 재초기화, 1 s × 450 s 롤아웃. 칸 계수는 v2 NC s31 사전값 이월(v3c3 재적합 없음). **plant 가 읽는 설정은 REF `reference_config_n31_v2.json`**(TUN 의 같은 키는 plant 에 안 닿음 — φ 바꾸려면 REF+매니페스트 재핀).
- 살아 있는 것: 수용 = 잼 여유뿐(AFA:218), **B1/B2 방류 제약 없음**, φ(차로감소) 3.0(셀 18 발화), φ_cd 1.0(꺼짐), occupancy_lane_loss false, 단면 FIFO 속도 상한(AFA:346-351), 입구 상류 속도 110/123.2 고정, 종단비용 없음. VSL L2 는 **FW_E 만**, FW_W 는 legacy min(V,명령)(적합된 적 없음).
- F 수정: 배포에 들어간 건 F6(C) L2 뿐. **F2 φ0(09-27 승인)도 미구현**, F1·F3·F4·F8·F10–F17 없음.
- 206.53: 고속도로에서 이 상수로 배수되는 진출은 10491·10481 뿐(둘 다 K8 SA 소유). 10645·10638 FIFO 재발은 1,400 스칼라·고정 분율 탓. 169 개는 도시 경계 movement 수.
- 충실도: FW_E 셀0 −24~−26(v3c2), 셀12 속도 72–74 vs 28–34(v3b), 셀18 가짜 병목(v3b). FW_W 는 배포 경로에서 T+300 안에 10491 만차(9/9), T+450 재고 +147(v3c1), 장기 2,215 vs 557–712.
- RM 은 VISSIM 에 기구 있음(v2: B2 대기 붙잡아 B1 방류 +173–329) 하지만 순손실; plant 는 B2→B1 결합 재현 못 함. GB-9 반사실 7회 전부 VSL 110·미터 10 → 고속도로 축 사실상 휴면.

**Why:** "고속도로 동역학 어떻게 되고 있나" 질문에 기억이 아니라 코드로 답한 결과. 내 첫 답(기억 기반)에서 FW_W 단기 충실도를 과소평가했음.
**How to apply:** K9 설계(FW_E 구조) 출발점. 결정 대기: F2 φ0 보류 확정(F3 와 함께), FW_E 진단 v3c3 재측정 시점, K9 순서(FW_W F13 vs FW_E). 관련 [[vissim-fwe-plant-structure-20260927]], [[vissim-fww-offramp-drain-206-20261001]], [[codex-85e3454b-review-k8-20261004]].
