---
name: vissim-freeway-entry-dsd40-defect-20260930
description: "v3b/v3c/v3c1 고속도로 입구 1098·1099 가 도시 기본 차량구성(DSD 40/30)으로 투입 → 40 km/h 투입·셀0 가속구간·입구 대기 97–99% 상시. 64cf 망은 구성 14 \"Freeway entry DSD110\" 으로 이미 고쳐져 있었음 → v3c2 로 수정 (2026-09-30)"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-30T08:49:36.570Z
---

- 발견 경위: 정적 점검 2a(입구 셀 0) OPEN — plant 셀0 재고 −24~−28대, 속도 +30 km/h. VISSIM 0–40 m 속도 31–33 km/h(p95 47). 사용자가 "투입 차량 desired speed 를 110 으로" 제안 → inpx 확인.
- 원인: v3c1 입력 1098(link 74)·1099(link 26) = vehComp 1 'Default'(vehType 100/150 → DSD 40 = 40–45 km/h, 200 → DSD 30). 첫 desSpeedDecision 은 link 74 pos 11.5 m, link 26 pos 1.6 m. 램프 8개는 미터 링크에 DSD110 결정이 있어 문제없음.
- 결과: 입구 대기 비지 않는 비율 1098 97.5%·1099 99%, 1098 평균 736대 망 밖 대기(v3c1 NC s31). 투입 용량 자체가 낮아 FW 수요가 입구에서 조여져 있었음.
- 64cf(사용자 인계 망)는 구성 14 "Freeway entry DSD110"(세 유형 DSD110, 비율 동일)을 1098·1099 에 씀. 우리 줄기는 그 전 기준망 86af2ac8 에서 갈라져 누락.
- 조치(사용자 결정 09-30): v3c2 = v3c1 + 구성 14 복사 + 1098·1099 만 사용. NC 5시드(+s37 봉인) → 같은 방법으로 2a·2b 재실행 → 그 뒤 F10(입구 셀)·F11(FW_W 상류 용량) 필요 여부 판단. 산출 D:/VISSIM_runs/20260930_v3c2.

- **v3c2 NC 결과(09-30 21:4x, 5시드, 독립 검증)**: G4 탈락 — DSD110 으로도 입구 조임 안 풀림. FW_E 는 수요 > 투입 용량(포화 중 투입 23–26 km/h, 높은 희망속도가 투입 간격을 늘려 투입 용량 −4% 7,668→7,340), FW_W 는 하류 엮임 대기 역류. 자유류 투입만 83–89 km/h. Ω −255(−2.9 sd)지만 1098 미삽입 +292 → 전체+미삽입 +14(동일) = 지연이 망 밖으로 이동. 2a OPEN(−24~−26대), 2b FAIL 14셀(FW_E 0, FW_W 0–7, 11–15).
- **사용자 결정(09-30)**: v3c2 채택(물리적으로 맞음, G4 는 전제 틀린 기준). F10·F11 은 v3c2 위에서. 재핀은 묶음 2·단일값 VSL 이전과 함께, R-obs·RM 팔은 재핀 뒤 재실행. 결정문 D:/VISSIM_runs/20260930_v3c2/reports/DECISION_v3c2_adopt.md.

**Why:** 입구 조임이 FW_E/FW_W 혼잡 양상·미삽입 대기·plant 입구 편향 전부에 걸려 있어, v3c1 기준 결론(2a/2b, FW_E 진단 수치)을 v3c2 에서 다시 봐야 함.
**How to apply:** v3c2 NC 가 나오기 전 FW 결론은 "v3c1(입구 DSD40)" 조건부로 인용. 재핀·묶음 2·단일값 VSL 이전 대상은 v3c2. 관련 [[vissim-network-v3c-20260927]], [[codex-expanded036-review-20260930]].
