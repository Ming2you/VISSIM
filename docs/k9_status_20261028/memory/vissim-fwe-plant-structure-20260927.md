---
name: vissim-fwe-plant-structure-20260927
description: "FW_E plant 구조 진단(v3b, fit 시드 31/41/43/47/53) — B1 대기 결손 80%는 머리 셀 12 속도 인공물, 붕괴 기원은 10681 합류 차로 2, 배포 plant 엔 B1 본선 방류 제약 없음, VSL 이득은 Carlson 용량 허구, S0e FW_E +314 는 B2 붕괴 동반(한 쌍으로 판정 불가)"
metadata:
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-28T05:39:21.496Z
---

제안서 scratchpad fwe-struct/FWE_STRUCT_PROPOSAL.md (항목 P0·V0·F1–F9·J1, 사용자 결정 13개 §7).
- **N_B1 −269 의 78%** = 셀 12(0.184 km) 속도 인공물: 밀도는 맞고(53–57) 속도만 72–74 (VISSIM 28–34). 수용 상한이 유량만 자르고 속도는 METANET anticipation(1/L 증폭 +8.6 km/h/s)이 끌어올림. B2 머리 셀 23 도 같음. F1(수용 제한 속도 폐합)이 −269→−77 이지만 TTT 편향 +21→+46 악화.
- **셀 18 가짜 병목**: 21→31셀 정제(0.526→0.175 km)가 1/L 도약 항(φ, 차로당 밀도 4/3)을 3배로. VISSIM link 2 는 "통과 3차로 + 보조 차로 1" 인데 plant 는 균질 4차로(F2+F3 함께만).
- **붕괴 기원(v3b)**: 10681 2차로 합류(5,042 m, 셀 12)에서 **차로 2** 가 먼저. 옛 "off-ramp 차로 1" 은 기원으로서 기각.
- **배포 SDMPC plant 에는 B1 본선 방류 제약이 없다**(RM 보정 하네스의 const I·bdo/bdp 는 scratch 전용). 관측으로 초기화돼도 +150 s 에 B1 차량 134 vs VISSIM 216 — plant 가 대기를 비운다. 램프 쪽 gap-acceptance 수용 노드(RM_C10681/10484)는 있음.
- **VSL plant 이득은 Carlson FD 의 용량 증가(100 에서 +5.8%)에서 나온다**(φ 무관, 26/26). VISSIM 포화 방류는 안 늘었다(NC 7,101 / S0e@100 6,997). → V0: 새 폐루프 런은 VSL 110 고정 권장(`max_vsl_step: 0` 은 110 에서 시작하는 런에서만 유효).
- **S0e fw_e_main +314** 는 NC31 에 없던 B2 붕괴(2040 s)와 함께. s31 은 fit 시드 중 유일한 비붕괴·임계 근처 시드. 붕괴 직전 1950–2100 s 램프 유입 S0e +456·S1 +312 vph(미터 열림 → 도시 신호 방출). → J1: FW_E 효과는 3시드 이상 짝 비교로만 판정.
- 배포 포트 프로필 `occupancy_lane_loss: false` 라 off-ramp 차로폐쇄는 "굶은" 게 아니라 **꺼져 있다**.

**사용자 결정 (09-27)**: P0 사전 점검 진행(코드 변경 없음) / VSL 은 **F6(C) native VSL 계단 실험 N1 으로 재적합**(설계서 fwe-struct/p0/N1_DESIGN.md 먼저, VISSIM 발사는 별도 승인) / J1 동의(FW_E 효과는 3시드 이상 짝 비교만) / FW_E 수정·도시 묶음 2·v3c 순서는 v3c 제안서와 교차 재생 결과를 본 뒤.

**P0 결과 (09-27, fwe-struct/p0/P0_REPORT.md)**: V0 경로 = (b) `max_vsl_step: 0` 별도 튜닝·110 에서 시작하는 새 런만((a) vsl_zone_free [] 는 매 결정 예외) / δ_merge 1.0 은 31셀 정제 격자·v2 s31·φ3 에서 적합·상한에 붙음 → F2 (c) 안 넣음, φ 는 단순형 0 권장 / F3b 보류(열면 셀 8–13 위빙 2+2) / B2 방류는 m10484 만(10490 계수 −0.03, 위빙 아님: 10483 진출이 2.8 m 앞) / F7 은 허용목록+용량키 정렬(120 vs 106.33)+φ 셀8 차단 세 가지라 범위 밖 권장 / gap 노드가 혼잡 롤아웃 스텝 73–88% 구속 → F4 b=0(N2 전) 권장 / T5 결정 재생 10/10 IDENTICAL(ps1 판정은 VSL<110 에서 항상 DIFFERENT 라 `--tuning` 없는 비교기 기준). N1 설계 = fwe-struct/p0/N1_DESIGN.md(핵심 16런 s41/43/47/53×c90/c100/c80/S5 대조, 약 7 h, 망 사본 scDetRec writeFile=true 한 줄, fast_nc_run 고정 프로필, 사양 n1_plan_v3.json 0db0d1c6).

**사용자 결정 (09-27 저녁)**: N1 핵심 16런 승인(도구 준비 워크플로 → 산출 D:/VISSIM_runs/20260927_n1_vsl, 큐는 메인이 WMI 로 발사, v3c NC 1차 뒤) / P0 권장안 일괄 승인: V0 (b)는 N1 재적합 전 폐루프 런에만(확인 재생 1회 먼저), F2 = φ 0 단순형·(c) 제외, F4 b=0(N2 전), F7 제외, F3 = 스칼라 통과 3차로+10481 우회 저장(경계 셀 13/14 는 구현 때 질문), 시간 관문 = 결정론 계수 1차+교대 반복 벽시계, 제안서 정정 17건 반영. 도시 묶음 2 U5 = 과대 그룹 전부(58/105).

**V0 확인 재생 통과 (09-27 22:4x, scratchpad v0check/V0_CHECK.md)**: `config_overrides.freeway_follower.max_vsl_step` 40→0 사본 튜닝으로 S0e 900 결정 2회 재생 — 예외 없음, VSL 동측 34·서측 32 행 전부 110, 두 번 바이트 동일(결정적), 녹색 L1 차 8.3 s.

**N1 발사 (09-28 00:14)**: 도구 D:/VISSIM_runs/20260927_n1_vsl/scripts (n1_build/queue/g0/extract/fzp_pass/moments/fit), 건식 시험 D1–D9 통과, 독립 검증 blocking 0, 분석 동결 reports/analysis_freeze.json(3b54d484; 계획 문구 밖 구현 선택 17개 = n1_fit.py IMPLEMENTATION_CHOICES, 분석 전 사용자 검토 권장). 큐 = WMI 분리 `n1_queue.py --run`(queue.log, --status), B1 c90 → B2 c100 → B3 c80 → B4 대조, 좌석 4 공유·소유권 120 s·G0 2750 s·STOP 파일, 아무것도 kill 안 함. 미결: B5 규칙 문구(전원 노출 절반 2.9/3.2%) vs 노출 가중(2.38/2.62%) — 판정이 갈리면 사용자 결정.

**N1 16런 완료 (09-28 07:08)**: 네 배치 모두 G0(2,700 s 접두 v3b NC 동일)·G1·G2 통과, STOP 없음. 분석은 동결 규칙 그대로(사용자가 17개 선택·B5 규칙 변경 요청 없음) 워크플로 wf_ff48ef4b-bde 로 → reports/N1_RESULTS.md.

**N1 결과 (09-28, reports/N1_RESULTS.md, 독립 검증 일치)**: **VSL 은 병목 방류를 늘리지 않는다.** B2 Δq/q c100/90/80 = −0.11/−0.25/−0.27% (CI ±2.3%p), B1 −0.08/−1.70/−1.16% (±3.6%p) vs 배포 Carlson L0 예측 +6.3/+7.8/+5.9% → **L0 기각**(B2·M2 두 경로). 준수 자유류 저하는 실재 −9/−19/−29 km/h(명령보다 2–3 km/h 빠름). 용량 강하도 모든 수준에서 남음. held-out 선택 = **L1 Carlson A 0.94 / E 1.44**(용량 ±1% @100·90, −3.6% @80·4차로; 손실 149.7 vs L2 141.7 = 10% 이내라 모수 적은 L1). 단 rule (b)(i) χ²/df 4.19>2 로 계열 형식 기각 — 동결 계획에 처리 규칙 없음. B5 조건 충족(두 기준 모두). 함의: F4 VSL 항 불필요(a(c)=1), F5 Qd 명령 무관, 재핀 전 폐루프는 V0 필수. **사용자 결정(09-28)**: VSL 법칙 = **L1 (A 0.94, E 1.44, alpha 0) + 행동 집합 {80,90,100,110}** 으로 재핀(v3c1 재핀과 함께, 계열 형식 기각·c80 비관은 한계로 기록) / B5(s31 4팔, 빌드 완료 sha 2a231bc4)는 v3c1 s47·s53 끝난 뒤 `n1_queue.py --run --batches optional_B5` 로 발사, 분석은 `n1_fit.py --run --with-b5`(k=4 판정 유지).

**B5 완료 (09-28 12:31 런, 14:37 분석, N1_RESULTS.md 부록 B5)**: 4팔 G0·G1·G2 통과. k=5(보고용) = L0 기각 유지, B2 −0.56/−0.25/−0.87%(s31 은 세 수준 모두 방류 감소), L1 (0.94, 1.44) 그대로 선택 → 결정 변경 근거 없음. fit_results.json 은 k=4 원본 a81eb5cf 그대로(재핀 저장소가 이 경로+sha 를 출처로 인용 → README §7 개명은 되돌림), k=5 는 fit_results_k5_with_b5.json 7e4b7cf0. 제안서 P0 정정 17건 반영 완료(fwe-struct/FWE_STRUCT_PROPOSAL.md, 옛판 _v1_before_p0.md).

**Why:** 옛 메모(off-ramp 차로 1, 방아쇠 굶음)를 v3b 에 그대로 적용하지 않게, 그리고 VSL 이득을 plant 예측으로 믿지 않게.
**How to apply:** FW_E plant 수정은 P0 사전 점검부터. RM 5라운드는 새 사전등록 필요(4라운드 B 포괄 규칙은 VISSIM 오라클도 6/32 실패). 관련 [[vissim-urban-batch1-and-rmcal-20260926]], [[vissim-fwe-collapse-is-offramp-lane1]], [[vissim-offramp-lane-closure-trigger-starved]].
