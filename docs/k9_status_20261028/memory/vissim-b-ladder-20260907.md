---
name: vissim-b-ladder-20260907
description: canon_default_20260905 는 B 시리즈가 아니다(B 는 09-05 밤 기각된 실험 팔). 09-07 사용자 결정 = B0 를 lcd1000 에서 0단으로 뽑고 그 위에 오늘 수정을 METER→SAT/SAT2→PW25→B5 로 누적하는 B 사다리. QB 는 B5 와 충돌해 제외, SAT 는 링크 32(perimeter)를 안 건드림
metadata:
  type: project
---

# B 사다리 (2026-09-07 아침 결정)

**계보 혼동 정리**: canon_default_20260905 = 09-01~05 승격된 물리정합 플랜트(용량 개별값·램프 spillback·09-03 on-ramp 결합·09-04 큐/접근 분리·09-05 매핑 v2).
B·B0·B3·B4·B5·RL·RS·P0 는 그 위에서 09-05 밤 lcd200 으로 시험한 팔(g2~g9)이고 **전부 기각·정본 미반영**. 09-06~07 lcd1000 h 런(h1~h11)에는 B 키가 하나도 없다.
"B 분기 전 물리정합 값" = h1 = h11 = 8629.0 (lcd200 g1 7741.5). config 증거: h_base `urban.ramp: {}`, g_* 는 `leg_split/offramp_direct/gate_onramp_queue`.

**B 계열 정의** (상세는 [[vissim-legsplit-B1-stock-tau]] [[vissim-offramp-reservoir-blockage]] [[vissim-offramp-drain-share-semantics]]):
B = leg_split(W_out 재고를 τ 로 펴 자유/램프별 주입, 실측 방향분율 B2) · B3 = offramp_direct v1(무신호 β0.46 출구, **9115 실패**) ·
B4a 유입시점 분할 / B4b 측별 꼬리·pool / B4c landing_storage(이중계상, 폐기) · **B0 = leg_split+offramp_direct(v2)+실측분율 = 깨끗한 B** ·
B5 = gate_onramp_queue(게이트발 on-ramp movement 복원, β=실측 peel, peel-off 차감 off). 체인 FRAG "B" = B0 + B4c 라 B0 를 써라.
lcd200 결과(기준 7741.5): g3 RL+B0 7920.3(도시 −135·본선 +319) · g6 RL+RS+B0 7940.7 · g7 RL+B0+P0 7822.5(도시 −196·본선 +216) · g9 +B5 7856.6.

**적용 여지 판정(09-07)**: B 의 본선 손실 원인 ①SC1001 현시가격 hold-back(+2.24 vs 국소 −1.3~−1.7) ②미터 폐쇄 는 정확히 오늘 수정 자리 —
PW25 는 ①(가격 ×0.25 = +0.56 < 국소), METER 는 ②(h1 폐쇄 18/35 → h7 2). RL 은 전제(h7 에서도 SC1001 꼭짓점 30/37).
**SAT/SAT2 는 링크 32 를 못 건드린다**(h7 메타: measured 127 movement/60 링크 전부 internal, perimeter 202개는 206.5/차로 → SC1001 W=boundary_in 413 그대로) → B 의 Q_sig 결손엔 무관. SAT3 은 h6 8892.7 사고라 B 정착 뒤 별도 단.
**QB 는 B5 와 충돌**: β 귀속(어댑터 ~5969)이 kind 필터 없이 spec β 로 정지선 큐를 나눠 무신호 램프 movement(β 0.3~0.5)로 30~50% 가 새 나간다. 램프행 차량은 정지선 상류(pos 1028/1330)에서 이탈해 정지선 큐에 없다.

**사다리** (`scripts/chain_b_ladder_20260907.py`, 드라이버 scratchpad/run_b_ladder.sh, 누적·GATE 50 은 판정만):
b0 canon+RL+B0 → b1 +METER → b2 +SAT+SAT2 → b3 +PW25 → b4 +B5. config `h_RL_B0[_METER[_SAT_SAT2[_PW25[_B5]]]]_20260906`, 런 `b{n}_…_lcd1000_x18_20260907`.
비교 기준: 무제어 8082.3 · canon h11 8629.0 · h7 8356.4. 09-07 07:0x ablation 사다리(h12 QB 33결정)는 사용자 지시로 kill.

**How to apply:** B 관련 질문은 canon 과 분리해서 답하라. B 위에 새 수정을 얹을 때 QB 를 같이 켜지 마라. 링크 32 용량은 SAT 로 안 올라간다(SAT3/perimeter 확장이 필요하고 그건 미터 폐쇄 되먹임을 검증해야 한다).

**발사 전 검증 (2026-09-07 07:30~08:00, 워크플로 4 agent)**: b0 오프라인 결정 t=900 SC1001 21/21/45/51(꼭짓점 탈출, lcd200 RL+B4b 와 같은 모양), t=2700 은 canon 상태라 23/20/75/20 그대로(폐루프에서 재판정). B 세 조각 진단 비영, 워커 10개 결과 = 직렬.
**B5 블로커 수정**: `_apply_gate_onramp_beta` 가 kept 별 0.85 클램프만 하고 origin 합을 안 묶어 SC1001 onW+onE 합이 1.44 → 형제 β −0.22(h7 상태 21/37, h11 7/37). 수정 = origin 합 > 0.85 면 비례 축소(진단 `gate_onramp_beta_total_<origin>`·`gate_onramp_beta_clamped` 누적·`gate_onramp_beta_fallback_<name>`). T=4500 재현 β 0.075/0.038/0.038/0.348/0.502. b0~b3 는 경로 자체를 안 탄다(kept 비어 있음). 백업 scratchpad/adapter_backup_before_b5fix.py.
**남은 잠복 함정(수정 안 함)**: in_SC1004_W 게이트 키 없음(링크 69 미배정 설계) → SC1004_W_to_onE β 는 늘 폴백 0.0833(의도 0.20 아님, 폴백이 spec β 우선). `urban.tau.length_cap` 을 켜면 spawn 워커 `_CFG_SWITCHES` 비어 있어 워커만 무상한 tau — 이번 사다리는 length_cap=false 라 무해.

**b0 결과 (2026-09-07 08:55, lcd1000 s13)**: canon+RL+B0 = **8313.4** (canon 8629.0 −315.6 · h7 8356.4 −43 · 무제어 +231). 분해 본선 3751/도시 4524/램프 198
(h7: 3940/4395/180 · canon: 3522/4992/289) → B0 는 **본선 −189·420 링크 194→40** 으로 이기고 도시는 h7 보다 +129 나쁨(회랑 520 vs 380). SC1001 꼭짓점 0/31(평균 39/20/34/46, p4 가 커짐),
SC1004 는 11/31 꼭짓점(p3 71). 미터는 R_F_E 가 0~374 로 자주 닫힘, R_D_W 0↔1800 진동(METER 없음). u_on 709→322 vph 감쇠(실측 W_out 발 램프 합 2277→1439).
lcd200 의 "B 는 도시 이득·본선 손실" 과 **반대 부호** — lcd1000 에서는 본선이 이득. 원인 후보: 링크 32 hold-back 이 풀려(SC1001 p3/p4 배분) off-ramp 역류가 안 생김.

**b1(+METER) 8361.6 = b0 +48.2 (10:09) — 재진단 결과와 조치 (사용자 승인, 11:2x)**
분해: 램프 +54(R_D_W 66.8→91.9·R_F_W +17·R_F_E +13) · 링크 32 적분 320.9→371.0(+50) · 본선 −36 · 회랑 −56. 기전 두 겹:
1. **리더가 TTT-악화 후보로 램프를 닫는다**: t=1800 리더 롤아웃 TTT 844.6 vs 폴백 843.8, 목적함수 6.1(0.29%) 차이로 채택 → R_D_W 0. 가드 진단
   `leader_fallback_guard_insufficient_gain=1` 인데 `rejected_leader=0`(min_ttt_gain_frac 0). b0 에서는 균등분할·정수 green 덕에 요청 300 이 plant 에서 ~770 으로
   **과다 실현**(plant/요청 중앙 1.79)돼 리더의 폐쇄가 묻혔고, METER 는 충실 실현(0.93)이라 폐쇄가 진짜가 됐다. → **LG**(0.002) 오프라인: t=1800 미터 전부 1800, t=2400 R_D_W 300·R_F_E 542.
2. **METER 한쪽 커넥터 폐쇄**: 요청 < 두 커넥터 최소치 합(256+511=767)이면 오차 최소 조합이 2차로 10482(수요 755)를 닫고 1차로 10480 에 몰아줌
   (t=2100~2700, 링크 32 238→496; b1 31결정 중 R_D_W 5·R_F_E 7 회). 균일 100 벌점은 오차에 묻힘. → **F1** `close_penalty_mode: "demand"`(폐쇄 벌점 = 그 커넥터 수요 힌트):
   b1 결정 재현 31/31, 변경 13결정(요청 300 → 둘 다 g2, 767 실현). 어댑터 `_measured_meter_allocation`, config 키 없으면 비트 동일. FRAG `MF1`.
조치: b2(23결정) kill → `_killed_b2_…` 격리, 사다리 RUNGS b1 = METER+MF1+LG 로 교체, start=1 재발사(11:3x). 옛 b1 런은 `b1_rl_b0_meter_…` 로 남음.
**교훈**: 액추에이션을 충실하게 만들면 리더의 나쁜 의도가 드러난다 — b0 의 −43 일부는 plant 가 리더를 무시한 덕. 미터 요청이 767 아래인 구간은 실현 불가 영역이라 리더 박스/양자화와 맞춰야 한다(후속).

**b1' (RL+B0+METER+MF1+LG) = 8282.2 (12:01)**: b0 −31.2 · h7 −74.2 · 무제어 +199.9. lcd1000 제어 최선. 분해 본선 3984/도시 4329/램프 124 (b0 3751/4524/198):
LG 가 **31/31 결정에서 리더를 기각** → 리더 미터링 사실상 꺼짐(R_D_W·R_D_E 폐쇄 0, 폴백 PFO 가 R_F_E 만 673~891 부분). 리더 롤아웃 TTT 이득이 어느 결정에서도 ±1 veh·h(≤0.05%) 라 0.2% 문턱을 절대 못 넘는다 —
리더가 램프를 닫는 근거는 TTT 가 아니라 목적함수 밀도 벌점(obj 이득 6~20). 결과: 도시 −195·램프 −74 이득, 본선 +233 손실(개방 대가). 링크 32 적분 387→375, SC1001 꼭짓점 0/31, SC1004 는 29/31 꼭짓점(p3 71) 으로 악화.
lcd 대조(state 기반, t≥900 적분): 링크 32 재차 nc200 314 / g1(200 제어) 224 / h0(1000) 318 / h11(1000 제어) 425 / b0 321 — 무제어는 lcd 무관, 제어만 lcd1000 에서 32 가 161→498 로 단조 증가(미터 폐쇄 19/31, R_D_W 저수지 적분 143). lcd200 g1 은 폐쇄 11/31 인데 32 가 안 자람(140~240) → fzp 진단(wf_702951eb) 이 기구 규명 중.

**b2 (+SAT+SAT2) = 8451.5 (13:13)**: b1' 대비 +169. SAT 는 링크 32(boundary_in) 를 못 건드리고 회랑만 흔듦 → B 위에서 SAT/SAT2 는 해롭다. 사다리 b3(+PW25)·b4(+B5) 진행 중.
**커밋·푸시 (14:1x, 사용자 요청)**: `bba9a13` on `codex/plant-fidelity-v2-1` — 인계 문서 `docs/HANDOFF_20260907_lcd1000_ramp_spillback.md`(계보·결과표·fzp 기구·플랜트 실명 4가지·수정 6건·우선순위 8개), `AGENTS.md`(Codex 진입점: CLAUDE.md 규칙 + 인계 문서 + VISSIM 한 대 분담), 어댑터·체인·config·fzp 산출물(parquet 는 gitignore). 244 파일.
분담 합의: Codex = 모형/코드/오프라인 재현·fzp 분석, 이 워크스테이션 = 실런 순차. 실런 중 어댑터 편집 금지.

**b3 (+PW25) = 8007.7 (14:19) — lcd1000 첫 무제어 승(−74.6), b2 대비 −443.8, canon −621.** 분해 본선 3810(h0 +41)/도시 4254(−132)/램프 97(+32). 링크 32 적분 384→219(램프 개방 + SC1001 p3 71 이 신호행을 뺌), 회랑 386, 420 은 37→179 재발(SC1001 p3 과녹색→SC105).
**주의**: SC1001·SC1004 가 31/31 결정 전부 22/23/71/23, SC1002 가 전부 25/21/26/66 — 정련이 꼭짓점에 얼어 사실상 **정적 계획 + 미터 개방(LG)** 이 이긴 것. 동적 MPC 의 이득이 아니다. PW25 는 B 위에서도 결정적(h5→h7 −296, b2→b3 −444).

**Ver2 채택 (09-07 15:00~15:30)**: 사용자 망 `modi_eval_userfix Ver2.inpx`(램프별 전용 상류 링크 32/129/127·31/124/125·68/121/123·70/126, 69 단축, 본선 2→2·119(3차로), 26(3차로)·120, 24 3차로) 검토 통과. 매핑 v2 전부 새 경로에 재생성(`evaluation/real_world_modi_control_ver2_20260907/`, `outputs/*_v2_20260907*`, `canon_ver2_20260907.json`). 생성기 체인 CSV 는 env `RW_FREEWAY_CHAIN_CSV`. 러너 `-NoGlobalKill`.
한계: 세그먼트 차로 단일값(FW_W 3 이지만 120 은 4차로) — METANET 세그먼트별 차로 배열 후속.
**자동 시퀀스(드라이버 wait_b4_then_ver2.sh)**: b4 종료 → 어댑터 스필백 패치 적용(백업 scratchpad/adapter_backup_before_spill.py) → v0 무제어(Ver2) → `chain_ver2_20260907.py`(a0 canon_ver2 → a1 +SPILL → a2 +RL → a3 +METER+MF1 → a4 +PW25 → a5 +B5 → a6 +B0). 로그 `TTT a*(`·`VER2_SEQ_DONE`. 커밋 09-07 15:3x 푸시.

**세그먼트별 차로 (09-07 15:20, 사용자 요청)**: vendor 는 `state.freeway_effective_lanes{link: [8]}` 로 세그먼트별 차로를 이미 소비(METANET metanet.py effective_lane_profile·wu 팔로워 lanes0·리더 밀도벌점). 막힌 곳은 어댑터 파서가 VBS 의 모형 링크 단일값 `lanes` 를 그대로 쓰던 것.
수정: 생성기 `segment_lanes`(세그먼트 중점 링크 차로) + 어댑터 `install_freeway_segment_lanes`(config `freeway.segment_lanes: "mapping"`, 패치 `scripts/apply_seglanes_patch_20260907.py`) → 파서가 밀도 = count/(length·lanes_i). 훅 `freeway_segment_params`(합류 세그먼트 파라미터용, 소비처 미정). 검증 h11 t=3600 FW_W S0 밀도 59.9→79.9, 차량 보존. VBS bottleneck CSV 밀도는 단일값 그대로(진단).
정본 적용 시점: chain_ver2 `apply_adapter_patches()`(v0 뒤·a0 앞, VISSIM 유휴 대기, 백업 `_backup_adapter_before_ver2_patches.py` 는 사다리 끝에 삭제). 커밋 09-07 15:2x.

**b4 (+B5) = 8005.5 (15:32)**: b3 대비 −2.2(잡음), 무제어 −76.8. B5 kept 3 movement 작동, u_on 1355~1876 로 b3 보다 큼(게이트발 램프 movement 가 저수지에 공급). SC1001/SC1004 여전히 31/31 꼭짓점 22/23/71/23.
**B 사다리 최종(lcd1000 s13)**: b0 8313.4 · b1' 8282.2 · b2 8451.5 · b3 8007.7 · b4 8005.5 (무제어 8082.3 · canon 8629.0 · h7 8356.4). 결론: PW25 가 결정적(−444), SAT/SAT2 는 B 위에서 해로움(+169), B5 중립, LG = 리더 OFF.

**Ver2 시퀀스 재구성 (09-07 15:4x)**: v0 가 경로 미완성으로 죽어 대기 드라이버가 chain_ver2 로 넘어감 → a0 가 먼저(15:38, 수정된 망). 순서 = a0~a6 → v0(무제어) → Ver2 씨앗 생성 → a7 +SATV2(SAT+SAT2, Ver2 씨앗 `lane_group_sustained_v0_ver2_20260907_v2.json`·`link_queue_class_v0_ver2_20260907.json`) → a8 +SAT3.
씨앗 생성기 Ver2 판은 정지선 링크를 망 신호두에서 뽑는다(SC1001 W = 127). h0 로 스모크: 기존 산출물과 107/107·51/51 동일. 사용자: SAT 계열 결과까지 보고 현시가격 대안(사용자 구상) 판단. 드라이버 `run_after_ladder_v0_20260907.sh` → `run_after_v0_sat_20260907.sh`.

**보류 (09-07 15:5x 사용자 지시)**: Ver2 사다리 a0~a8 은 **나중에**. 지금은 v0(Ver2 무제어 기준선)만 돈다(`scripts/run_ver2_nocontrol_20260907.sh`). a0 부분 런(9결정)은 `_killed_a0_canon_ver2_x18_20260907` 격리.
**재개 방법**: (1) v0 완주 확인 → (2) `python scripts/derive_lane_group_sustained_ver2_20260907.py && python scripts/derive_link_queue_class_ver2_20260907.py`(a7 씨앗) → (3) `python scripts/chain_ver2_20260907.py 0`(a0 canon_ver2 → +SPILL → +RL → +METER+MF1 → +PW25 → +B5 → +B0 → +SATV2 → +SAT3; 완주 런은 RESUME). 어댑터엔 스필백·세그먼트차로 패치가 **이미 적용**되어 있음(config 키 없으면 비트 동일; chain 의 apply_adapter_patches 는 '이미 적용' 으로 건너뜀). 현시가격 대안은 사용자 구상 — SAT 결과 후 판단.

**v0 = Ver2 무제어 기준선 7660.2 (16:17, 13분 완주)**: 본선 3338 / 도시 4379 / 램프 71 (lcd1000 h0 8082.3 = 3769/4386/65 · lcd200 nc 7952.4 = 3622/4395/63). 본선이 −431 — 3차로 병목(119/24·26) + 10613 lnChgDist 1000 + 경로 보완이 본선 흐름을 바꿈. 도시는 동일. **Ver2 결과는 lcd1000/lcd200 과 직접 비교 불가 — 기준선은 7660.2.**
Ver2 링크 적분(t≥900): 127 250 · 32 36 · 129 7 · 125 35 · 123 45 · 69 65 · 120 334 · 2 1013 · 26 551. compare 스크립트의 '31/32' 그룹은 Ver2 에선 32+129+127(접근)·31+124+125(W_out) 로 바꿔야 함(미수정).
Ver2 씨앗 생성 완료: `outputs/lane_group_sustained_v0_ver2_20260907_v2.json`(68 링크·107 차로군, 127 p3 지속(큐) 3560·p4 2250), `outputs/link_queue_class_v0_ver2_20260907.json`(680 링크·큐 57, 127 평균정지 143.5). → a7(SATV2) 준비 끝. 사다리 재개: `python scripts/chain_ver2_20260907.py 0`.
