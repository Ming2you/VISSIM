---
name: vissim-sdmpc31-obs150-state-20260924
description: "SDMPC-31 + obs150 현황 — G1b 검증 통과, V5b 9000초 진행, VSL 모형·50..110 집합 커밋(75f0151), RM 이득 추적 결론(Ω 에선 플랜트가 맞다)"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-25T15:03:59.467Z
---

**2026-09-24 현재 SDMPC-31 경로**
- 조합: v2 망(FW80/U90, base 110, 수요 v2), SimRes 10, 결정 때만 150 s 1회 관측, 31셀 boundary+기준 FD 플랜트.
- 네이티브에서 끝까지 검증했다.

**코드**
- `Ming2you/VISSIM` 브랜치 `claude/sdmpc-n31-20260924`, 워크트리 `D:\VISSIM-merge\sim3-n31`.
- 커밋: e161c8e 구현 → c585d2b 발사기 사본 → ea14026 미터 program-less → b5f1104 검증 도구 3건 → 7216e25 71차로 초과 투영 → 3af123f 이식 안내서 → 75f0151 VSL 모형(A0.5_E4)+집합 {50..110}+코호트 초기화+RM 추적 문서.
- 문서: `D:\VISSIM-merge\evidence\` 의 SDMPC31_OBS150_PLAN / SDMPC31_INTEGRATION / OBS150_PROBE (모두 20260924).
- 스위치는 튜닝 키 `freeway.lane_plant` 하나다.
  - v2 manifest = 31셀·obs150
  - v1 = 옛 21셀·SimRes 1

**G1b 확인 런** (`D:\VISSIM_runs\20260924_sdmpc31\sdmpc31_g1b`, 1350 s, GT 창 750–900·1050–1200)
- D6 대조: 경계 254개 전부, 원점 양방향, 헤드와 녹색 통과, 10643 대장, 분기율 모두 0.1 s 정답과 차량 단위로 일치했다.
- D10(COM 쓰기 → 헤드 1 s 지연)은 154/154 일치했다.
- 남은 GT 이상은 link 72 분기(SC1002) 애매 이탈 6/12건뿐이다. 이건 .mer 로 통과 0 이 확인되지만 GT 로는 판정할 수 없는 경우다.
- 결정 시간: 900 = 606 s, 1050 = 548 s, 1200 = 495 s.
- V3 재생: 900·1050 모두 IDENTICAL.
- V3b 플랜트 관문: FW_E 21.4, FW_W 12.3 km/h 로 PASS.

**V5 발사**
- `sdmpc31_v2_s31`, 9000 s, seed 31. 2026-09-24 13:39 에 WMI 로 분리 발사했다.
- 예상 10–11 h.
- 짝 무제어 V4(`-Controller no-control`)는 그 뒤다.

**V5 → V5b**: V5 는 1950 에서 71 차로3 초과로 죽음(7216e25 로 수정). V5b `sdmpc31_v2_s31b` 15:12 발사, 19:30 에 4800 s(결정당 340–510 s). V5b 는 VSL 이식 **전** frozen 이라 VSL 110 고정·미터 전부 cap.

**VSL (75f0151)**: 110 전부면 옛 예측과 비트동일. 3000 s 재생에서 FW_E 구역5=100·구역10=90, 이득 −0.35 veh·h(0.07%, 판정 불가). 계수는 90 에서만 맞춘 것 → 50–80 외삽. v2 분포가 50–70 좁은 균등 / 80–110 긴 오른꼬리로 한 계열이 아니다. native 짝 비교 전엔 폐루프 금지.

**RM 추적 (N31D/RM_GAIN_TRACE_20260924.md)**: VISSIM FW_E 〔가림: 봉인·블라인드 시드 값〕 의 〔가림: 봉인·블라인드 시드 값〕 는 램프 대기 전가, Ω+미삽입은 규칙 RM 도 〔가림: 봉인·블라인드 시드 값〕 손해(FW_W 10491 역류). 플랜트의 "미터 안 함"은 Ω 판정으로는 맞다. 틀린 건 FW_E 내부 — B1(셀 8–13)이 플랜트에서 풀린다(상류 진입 qmax 7300 < 〔가림: 봉인·블라인드 시드 값〕, 출구·진출 과다). 용량 강하 아님(〔가림: 봉인·블라인드 시드 값〕). SDMPC 미터 이동폭 ±2 s/150 s 라 블록0 {8,9,10}, g2 도달 불가.

**V5b 완료 (2026-09-24 23:36)**: 결정 61/61 OK, 실패 0, wall 30,204 s, SKIPS>0·(5,14) 행 없음(정상). s31_v2nc 와 900.1 s 까지 프레임 동일 → **유효한 짝**(별도 V4 런 불필요). V5b − NC: Ω **+417.3**, fw_e_main +252.7, urban +311.4, offramp −149.7, 망전체 +653.6, 미삽입 −101.9 veh·h. 미터·VSL 은 안 움직였으니 손실은 SDMPC 의 도시 신호 제어 쪽(과 그 spillback)에서 와야 한다 — 미분해. 스캔: scratchpad v5b_scan/analysis.

**v3b 재핀 커밋 cd06a39 (2026-09-25, 푸시함)**: 망 be0075bf, 램프 예측 RM_C 키+strict_ramp_keys(v3b NC 3시드 재유도), routing beta `routing_v3b` e81d545f. beta 유도(scripts/derive_routing_turn_beta.py)의 목적지집합 역추론이 램프 교차로에서 틀림 → `--explicit-approach N31D/beta/explicit_approach_v3b_20260925.json`(1117→SC1001 W/offW/offE, 1140→SC1004 W/offW, 1138→W, 1126→offE, 1124→S; FZP 출처별 실측 근거 포함). plant a087aa67, config 16c5f8bc. v2 사전값(B110) 재적합 안 함. 남은 beta 한계(held 몫, 이름없는 경계유출 균등분배, 474↔492 합>1)는 도시 플랜트 수정(F4a) 단계로.

**v3b 첫 런 결함 2건 수정 (2026-09-25, 푸시함)**: 40e5933 = SC1004 서측 link 126 차로 저장 초과(v3b NC 프레임 1.5~4.7%, 26~28대 vs 25.4)를 옆 차로로 투영 / 9152821 = solve_qp 가 SLSQP 실패('Inequality constraints incompatible', 'Positive directional derivative…' — 둘 다 풀리는 QP)일 때만 Dykstra 투영(정지조건은 반복점+보정항 둘 다; 반복점만 보면 틀린 답). 재생 도구: make_replay_state_v2.py prepare + replay_decision_n31.ps1 -Root <tree> -SkipFreezeVerify, QP 덤프는 -ExtraPythonPath sitecustomize.
**R-obs-b** (sdmpc31_v3b_nc_s31b, 무제어+obs150): FZP 가 s31_v3bnc 와 5.1~9000 s 레코드 동일 → 상태 61개 = v3b NC 궤적(T3 오프라인 시험용). S0c 는 PC 종료(09-25 22:11, 원격 세션 뒤 정상 종료)로 3000 s 에서 끊겨 S0d 로 재발사(09-26 00:02, frozen sdmpc31_91528210).

**Why:** 다음 세션이 무엇이 검증됐고 무엇이 남았는지 다시 조사하지 않게.

**How to apply:**
- 새 런은 `D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Freeze -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name <sdmpc31_*> ...` 를 WMI 로 띄운다 ([[vissim-launch-detached-from-session]]).
- 결정 실패는 `make_replay_state_v2.py prepare` 와 `replay_decision_n31.ps1` 로 재생해서 고친다.
- VSL 은 110 에서 플랜트 도함수 0 이라 움직이지 않는다(보류된 수정).
- 7개 보정 사전은 prior_mismatch 상태다(첫 9000 s 뒤 재적합).
- 관련 [[vissim-sdmpc-native-state-20260923]], [[vissim-legacy-watchdog-global-kill]].
