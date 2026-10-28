---
name: vissim-urban-batch1-and-rmcal-20260926
description: "SDMPC-31 v3b 도시 플랜트 묶음 1(U1 β·U2·U3) 결과와 사용자 결정, FW_E RM 보정 1~3라운드가 전부 선택 단계에서 멈춘 이유(09-26)"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-28T02:09:39.956Z
---

**묶음 1** (worktree D:/VISSIM-merge/sim3-n31-urban, 브랜치 claude/urban-fix-v3b-20260925, 9152821 위):
- U1 routing_v3b2 = 492 movement 전부, 물리 경로 없으면 0(152개, 사유 기록), 있으면 relFlow. 경계 유출 이름은 물리 out 링크 표 우선(방위 규칙이 SC104 10171 을 N 으로 오매핑했던 blocker). 독립 FZP 판정(차량 궤적, β 표 미사용) 119 접근로 ±0.05: 기본 48 → 105.
- U3 무신호 23개(헤드 없음+전용 차로), 헤드 차로군 용량 분배에서 제외. U2(경로 귀속)는 **S1 에서 뺀다**: 큐를 정확한 movement 에 모으면 206.5 veh/h/차로 용량(U4)에 묶여 한 스텝 오차가 커진다 → 묶음 2 에서 U4 와 함께 재측정.
- S1 후보 = config_n31_v2_urban_b1_u1u3.json (make_config_n31.py --urban-batch1 --components U1,U3). 기본 튜닝 재생 61/61 IDENTICAL.
- 사용자 결정(09-26): SC7 E/E_SC16→N_SC11 은 비존재 선언을 고치고 p4(헤드 SG 7-1)로 옮겨 relFlow 적용; SC2001 회랑은 NC13 값 유지; SC104 S_SC106 은 config 기본값 유지; 커밋·푸시 후 S0e(기본)·S1(U1+U3) 병렬.
- T2(V5b 재생)는 불가: 증거가 v3b 망에 핀, 재핀 전 트리 없음.

**RM 보정(FW_E, v3b)**: 1라운드(시드별 관문)·2라운드(시드 평균 관문+범위 확장)·3라운드(B2 붕괴 전환 H1, 온라인 용량 H2) 전부 선택 단계에서 멈춤, 보류 자료는 plant 평가에 안 씀(기술 통계는 1라운드 전부터 알려져 있었음 — 감사 공개). 원인: 결정론적 plant 로 s31(산발 혼잡)·s41(붕괴)의 셀 단위 혼잡 위치(Jaccard M/B2)를 동시에 못 맞춤, B1 I 는 10 vphpl 당 seg5 ±55 칼날. 사용자 결정: v3b 무제어 시드 43/47/53 추가(09-26 07:4x 발사, extra_seeds_receipt.json).

**커밋·런 (09-26 오전)**: 메인 886a014 = 7650 멈춤 수정(램프 미러 반올림 −ULP→0, 실패 시 traceback 을 .error.txt 로·stderr 1줄 — VBS RunCapture3 가 종료 후에만 파이프를 읽어 4 KB 초과 stderr 가 교착). 도시 3632fdf(묶음1+SC7 p4) + 병합 cf3ce37, 둘 다 푸시. S0e(886a014, 기본) 09:40·S1(cf3ce37, U1+U3 f88d05f1) 발사. 알려진 모형 전반 한계: 공유 1차로에서 목적지마다 차로 용량을 따로 받음(81곳) → 묶음 2(U4/U5).

**S0e·S1 결과 (09-27 분석, 둘 다 9000 s·실패 0, s31_v3bnc 와 900.1 s 까지 FZP 동일=유효 짝)**: 스캔은 scratchpad sdmpc_v3b_scan/(run.json+vissim_eval 정션 래퍼, SDMPC FZP 는 0.1 s 프레임 1개 더 있음 — 무시 가능), 표 compare_s31.json.
- S0e−NC: Ω −55.2, urban +16.0, fw_e_main +314.4(link 2 +266.6), 동측 국소 19링크 +267.9, offramp −256.3, 전체+미삽입 −8.9. FW_E 손실 = VSL 이 seg5 100→90·seg10 80–100 인 2400–6000 s 에 B1 큐가 셀 5–7 로 1.5 km 연장(stage-1 513 m 셀). 미터는 전부 열림(900).
- S1−NC: Ω +53.3, urban +303.4. S1−S0e urban +287.4 중 link 174(SC108→SC109 서측) +251.7·link 21 +45.6. SC109 p3(SG2+6 직진)가 3600 s 부터 하한 20 s 고정, p4(SG5 서측 좌회전)는 54–80 s. 근본원인은 50:50 분할이 아니라 경계 movement 용량 206.53(실측 1/9) — [[vissim-boundary-movement-capacity-206]]. 두 트리 공통 기존 결함, U1 기여는 미판정.

**사용자 결정 (09-27 오후)**: 경계 용량 결함은 **묶음 2 에 C3(U4+U5+U6, lane_group_kinds 네 종류)로 통합**(C1 단독 시험 안 함) / **C6 굶김 감시 경보도 묶음 2 에 넣는다**(처음엔 '안 넣음'이었다가 바로 번복) / U1 이 잠김을 밀었는지 가르는 오프라인 교차 재생 28회 발사(scratchpad xreplay/, WMI 분리, 1800–3600 s, S0e 상태×U1U3·S1 상태×기본·재현 2) / **v3c 망 검토 시작**(결정점 1081 하류 합류 → 경로 없는 차량 유형; 제안서 net-v3c/V3C_PROPOSAL.md, 편집·NC 재실행은 별도 승인).

**묶음 2 계획 (09-28, scratchpad urban-b2/BATCH2_PLAN.md + u4_saturation_table.json·u5_contract_draft.json·u6_diagnosis.md·code_map.md)**: C3=U4+U5+U6 코드 수준 all-or-nothing. U4 실측 65그룹(중앙 1,860 veh/h/차로, 현 plant 의 2.57배) + 기본 40그룹 1,850; 현 헤드 하한(qualified/녹색)은 실측의 0.35배만 잡음; lane_group_kinds 4종 = internal/boundary_out/boundary_in/off_ramp(on_ramp kind 없음); 구성원은 U5 계약에서; U4 켜면 헤드 하한 배분을 차로 비율로. U5 과대 그룹은 v3b 에서 53(58 은 v2 수치), 모듈 경계 공유는 SC1001 link 127 두 그룹뿐. U6 진입 여유 식은 구속 0초라 불변, `physical_diverge_v1` 로 분기 모형 일괄. R-obs-b 는 no-control 이라 61/61 IDENTICAL 이 SDMPC 최적화 경로를 안 덮음 → S1·S0e 결정 재생 추가. 일정 19–26 작업일 + 재생 11–17 h. 사용자 결정(09-28): Q1 native 그룹도 U4·U5 적용 / Q2 SC105·SC1 공유 좌회전 차로 현시 권한을 p3 로 고치는 증거 파일(+SC7 직렬 헤드 정적 축소, 그 전까지 정적 축소) / Q3 v3b 단일 시드 폐루프 안 함. 구현 시작: 워크트리 D:/VISSIM-merge/sim3-n31-urban-b2, 브랜치 claude/urban-batch2-20260928(cf3ce37 에서, 커밋 안 함), 단계 0–2 워크플로 wf_a65fee6a-960, 보고 urban-b2/impl/STAGE*.md.
**묶음 2 단계 0–2 완료 (09-29 04시, 독립 검증 blocking 0, 커밋 안 함, diff sha 36ac3916)**: 단계 0 기준선 비트 재현·R-obs-b 61/61; 단계 1 U4-0(코드 기본값 4개 → 필수 키, install_lane_group_membership 분리, 죽은 키 15개 제거, 옛 튜닝 재생용 u40_former_defaults 는 is_post_u40 로 실운영 격리) G-ID (a)(b)(c) 통과; 단계 2 C6 starvation_monitor.py(582줄, 키 urban.diagnostics.starvation_monitor 1.0/8/3/3, 읽기 전용) G-C6-0·1·1b·2·4 통과, S1 6300 SC109 p3 flag, S1 첫 경보 4650 s, S0e 0건, 행동 비트 동일. 열린 것: G-C6-3 no-control 결정에서 +0.5 s(2.25 %)·JSON +6.8 %(사용자 판단), 경계 규칙은 206.53 결함 때문에 상시 경보(35–38 movement, U4 뒤 줄어야 함), 후보 config 에 C6 키 추가, 커밋 전 __pycache__ 삭제, 다음 = 단계 3–9.

**Why:** 다음 세션이 결정과 근거를 다시 묻지 않게.
**How to apply:** S1 은 U1+U3 만; U2·U4·U5·U6 은 묶음 2. RM 4라운드는 시드 6개로 다시 사전 등록. 관련 [[vissim-sdmpc31-obs150-state-20260924]], [[vissim-network-v3-decisions-20260925]].
