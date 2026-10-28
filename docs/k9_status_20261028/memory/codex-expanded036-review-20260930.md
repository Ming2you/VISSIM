---
name: codex-expanded036-review-20260930
description: "사용자 codex 브랜치(codex/sdmpc31-upstream-20260926 @7ecace6) expanded036 동측 159계수 검토 — 값은 우리 v3c1 plant 에 얹지 않음(망 64cf·κ5·VSL A0.5/E2·구조결함 보상), 31셀 분할만 비트 동일"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-30T07:31:32.490Z
---

- 커밋 7ecace6 = 문서·설정·계수표 51개(코드 없음, 그쪽 실험 코드는 미커밋). 망 64cf5f55(FW80–U90, DSD110 75–145), seed 29/43/47(+64cf-s61/s67), κ 5, VSL Carlson A0.5/E2.0, vsl_set 50..110, sign cell 16. 상태 NOT_GAIN_QUALIFIED, 블라인드 검증 없음, seed43 순위 개선 없음(불일치 1/6→2/6).
- 검토(세션 scratchpad codex7ec_review/REVIEW.md, REVIEW_CHECK.md): **값 불채택**(159계수·셀별 δ 2.2–5.1·VSL 법칙·candidate_config·head-service 9=10 평탄표). 계수는 셀 12·23(사람이 넣은 초기값)·18·24 에서 우리 구조 결함(F1–F4)을 보상하는 모양 → 구조 수정 위에 얹으면 이중 계산. candidate_config 는 옛 4그룹 램프 키로 조용히 폴백(cd06a39 결함 재발).
- 그대로 쓸 수 있는 것: 31셀 물리 분할(양방향 62셀 ΔL 0, 합류 셀 10/12/21/23 = 10639/10681/10490/10484, 진출 9/11/18/20). 방법(같은 상태 짝 반응, 순위·후회, source 항 분리)은 N2 설계 아이디어로만.
- 검토가 찾은 **우리 쪽 잠복 결함**: (1) v3c1 배포 head-service 10490 {2:1.0,3:1.0} 비유일 → SDMPC 경로도 physical_ramp_branches 디코드에서 멈출 수 있음(수정은 하이브리드 브랜치에만) (2) state_response 셀 인덱스 검증이 31셀 분할 전에 돎(canonical_harness.py:301 → 셀 21–30 override 거부) (3) PLANT_PORTING_GUIDE 의 "조용한 무시 방지" 설치 검사가 _load_sources_v2 에 미구현.
- 시드 주의: 64cf-s61/s67 과 우리 봉인 s61/s67 은 독립이라 단정 못함(같은 FW_E 진입 부피) → 그쪽 s61/s67 수치를 우리 선택·보정에 쓰지 않는 규칙 권장.

**사용자 결정(09-30)**: 값 불채택 동의 / 정적 점검 2a(입구 셀 0 편향)·2b(셀별 FD 용량 ≥ VISSIM 통과 p95) 실행(기준은 REVIEW.md:137-138 제안값으로 동결, 워크플로 wf_c986b41e-9af, 산출 scratchpad static_checks/) / 셀별 FD(physical_cell_fd 류)는 우리 F 수정에 필요하다고 판단될 때 가져다 씀(그쪽 diff 요청 안 함) / **시드 표기는 내가 정함**: 망 접두어로 인용(v3c1-s31, v3b-s31, 64cf-s61), 64cf-s59/s61/s67 수치는 우리 선택·보정·판정에 쓰지 않음, 우리 봉인 59/61/67 은 계속 봉인.

**Why:** 사용자가 셀별 재보정(expanded036)을 우리 plant 수정에 얹을지 물었고, 답은 "값은 아니오, 분할 규약·검증 방법만".
**How to apply:** CONTRACT.md:713 이 이미 physical_cell_fd·anticipation 18.375·v_free 108.159 를 "옮기지 않음"으로 정해 둠. v3c1 이전 묶음에 10490 유일성 수정 포함 고려. 관련 [[vissim-fwe-plant-structure-20260927]], [[vissim-vsl-fixed-dsd-20260928]].
