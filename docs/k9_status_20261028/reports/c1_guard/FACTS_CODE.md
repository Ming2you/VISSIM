# FACTS_CODE — 링크 129·10491 보호 장치가 작용할 수 있는 자리 (코드 사실, 2026-10-27 KST)

- 무엇: D-K9-100(⟨Q2⟩ 를 (가)에서 (나)로: 링크 129·10491 저장 한계 보호(METER_NEXT2 D5 꼴)를 C1 에 더함. 꼴·문턱·작용 대상은 이 설계 초안 뒤 사용자 결정)의 앞 단계입니다 [읽음 `SP/K9_1_J1_NOTES_20261013.md:335`]. 이 문서는 **코드에서 보호 장치가 걸 수 있는 자리만** 적습니다. 꼴·문턱·대상 권장은 적지 않습니다.
- 기준 코드: GWT8 `c20aff1d` + C1 탐침 패치 `5cdc6eb1…`(= 탐침 트리 `probe_5cdc6eb1`, build `ok`, 파일 10,583) [실행].
- 줄 번호 규칙
  - 패치가 건드리지 않은 파일은 c20aff1d 줄 = 탐침 트리 줄입니다(줄 끝 CRLF 만 다름, `diff --strip-trailing-cr` 0) [실행]. 이런 파일은 이름만 적습니다.
  - 패치가 건드린 파일(`sdmpc.py`, `physical_ramp_branches.py`, `lane_plant_runtime.py`, `runtime_setup.py`, `vissim_stackelberg_adapter.py`, `area_follower_objective.py`, 새 파일 `c1_port.py`)은 탐침 트리 줄에 **PT**, c20aff1d 줄에 **OU** 를 붙입니다. 붙이지 않은 경우 두 쪽 줄이 같습니다(패치 덩어리보다 앞 줄).
- 표시: **[실행]** 이번에 읽기 전용 명령으로 확인 · **[읽음]** 코드·문서·설정에서 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술. 판정 낱말은 쓰지 않습니다. 시드는 망 접두로 적고 평균 내지 않습니다.
- **데이터 뒤**: §3.2 와 §4.2 의 숫자는 이번에 기존 산출(V-A·B 결정 시각 상태 파일, B 결정 JSON)에서 읽은 값입니다. 여기서 문턱을 만들지 않았습니다. 이 숫자를 보고 문턱을 정하면 그 문턱은 "데이터 뒤" 입니다.

## 줄임말 (처음 한 번)

- plant = 제어기 안의 교통 예측 모형. SDMPC = 이 계열 분산 모형예측제어기. 결정 = 150 s 마다 내는 명령, 예측 지평 450 s = 150 s 블록 3개.
- SA = SC1001 동쪽행 정지선 접근 모형(`stopline_approach.py`, 127 의 3차로 FIFO 색인). FIFO = 먼저 온 차가 먼저 나감.
- 포트 = 고속도로에서 나가는 진출 커넥터의 유한 저장(`DelayedPort`). 10491 = FW_W 진출 OR_D_W 의 신호 쪽 커넥터(링크 26 → 링크 129 차로 1, 착지 239.38 m). 10479 = 같은 진출의 직접 커넥터(→ 링크 125).
- in_SC1001_W = plant 의 SC1001 서쪽 접근 저장고(설정 1,237.8대). S_eff = 그 저장고의 유효 빈자리(점 대기 뺀 값).
- SG2 = SC1001 동쪽행 직진 신호 그룹(EBT) = 현시 p3. SG5 = 동쪽행 좌회전(EBL) = 현시 p4 [읽음 `C1D/P0_PROBE.md` §3-2].
- M4 = C1 의 미터 저장 보호(머리 앞 저장 90 %면 그 결정의 녹색 하한을 올림). RV-2 = 그 하한을 표 안 녹색으로 내리는 C1 고침. G-A7 = `c1_port.operating_bounds` 의 하한 검사.
- USG = codex `urban_storage_guard.py`(도시 저장 보호, R_MECH 의 C5 묶음). 머리 자원 v11 = codex 머리 실측 서비스 계약 v11.
- QC = VISSIM 대기 계수기(queue counter). DCP = 자료 수집 지점(data collection point). FZP = VISSIM 차량 궤적 파일.
- ④b = 미삽입 대기(입력에서 생겼지만 망에 못 들어간 차). Ω = 목적 영역.
- A1 = v2 lane plant 의 고속도로 원천 경계(최근 150 s 넣은 율과 밀린 양으로 넣을 율을 예측).
- 경로 약칭: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, C1D = `SP/c_port/c1`, GD = `C1D/guard`. OU 트리 = `D:/VISSIM-merge/sim3-n31-k8`, PT 트리 = `D:/VISSIM-merge/k8_gate_trees/c1/trees/probe_5cdc6eb1`, CX = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff`(codex `a49981ff`).
- 코드 약칭(모두 `evaluation/controllers/` 아래, 따로 적은 것 빼고): SA `stopline_approach.py`, LOR `lane_offramp_runtime.py`, AFA `area_freeway_accounting.py`, LFR `lane_freeway_runtime.py`, LC `lane_coupling.py`, LPR `lane_plant_runtime.py`, SB `source_boundary.py`, SAC `signal_actuation_contract.py`, SEQ `sdmpc_sequence.py`, PFO `sdmpc_pfo.py`, AFO `area_follower_objective.py`, AMF `area_meter_finalization.py`, ADP `vissim_stackelberg_adapter.py`, RS `runtime_setup.py`, PRB `physical_ramp_branches.py`, SD `sdmpc.py`, C1P `c1_port.py`, PS `projection_support.py`, OR `offramp_routing.py`, UQM `vendor/NumSim-mine/src/models/urban_queue_model.py`, HAR `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py`, VBS `scripts/run_real_world_stackelberg_controller.vbs`.
- 런 약칭(읽기만): V-A = `D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{31,41,43}`, B = `D:/VISSIM_runs/20261026_codex_b_v3c3/s{31,41,43}`. V-A 결정 JSON 은 `…/decisions_…/action_NNNNNN.json`, 관측은 `…/state_NNNNNN.json`.

---

## 0. 쉬운 요약 (판정 아님)

1. **plant 에는 127 → 10491 → FW_W 칸 9 사슬이 있습니다** [읽음]. 127 차로가 차면 10491 포트 방류가 막히고, 포트(38.58대)가 차면 FW_W 칸 9(3,638–3,822 m)의 진출 몫이 칸에 남고 칸 속도가 묶입니다. 상류 칸 8 → 0 으로 번지고, 칸 0 에서 못 넣은 차는 Ω 밖 원천 대기로 갑니다(§1.2).
2. **plant 에 없는 것** [읽음]: 링크 129 차로 1 의 국소 저장(착지 239.4 m 와 10490 갈림 300.0 m 사이, 약 10대), 링크 26 차로 1(FW_W 는 3차로 집계), 1099 밀린 줄의 상태(원천 대기는 0 에서 시작하고 밀린 양은 A1 예측 안에만 있음)(§1.4).
3. 10491 포트를 막는 plant 조건은 **127 차로 빈자리**(차로 저장 81 / 63 / 103.58대)와 S_eff(in_SC1001_W) 합동 상한입니다. 129 차로 1 자리는 조건에 없습니다(§1.3).
4. **SC1001 p3(SG2) 하한을 넣을 자리는 세 곳** 입니다: (가) 좌표의 현시 한계 행 하한, (나) codex USG 꼴 반공간 행, (다) 후보 가능 검사에 예측량 조건. 지금 현시별·신호별 하한 키는 없고 하한은 모든 현시에 같은 `green_min` 입니다(§2.1).
5. **미터 10490 의 M4 경로는 두 번째 저장 대상을 지금 받지 않습니다**. 발동은 그 미터 자기 머리 앞 버퍼(약 45.4대)만 봅니다. 넣을 자리는 `c1_port.operating_bounds` 안이고, 129 차로 1 대수는 상태에 없어 관측에서 따로 세어 실어야 합니다(§2.2).
6. **설정에 켜져 있으나 V-A 결정 길에 닿지 않는 보호가 하나 있습니다**: `spillback_guard`(옛 묶음 R_D_E → 링크 129 차로 1 정지 차)(§2.3).
7. **결정 시각에 관측되는 것**: 전체 차량 기록(차로·위치·속도·정지), 차량 경로 번호, 7 m 차로 칸, 대기 계수기 4개(127·129·26 두 곳), DCP 수(10491 진입·26 @3,525.6·10771·입구 40 m), 입구 밀린 양 `backlog_veh`. 대기 계수기는 관측에 있으나 결정 코드가 쓰지 않습니다(§3).
8. V-A 와 B 의 1,800–3,300 s 상태 파일(시드마다 6상태)에서 대기 계수기 200122(129)·200141(26)과 10491 정지 차는 B 에서만 0 이 아닙니다(QC 200122 평균 최대: V-A 0, B 345.5–500.4 m)(§3.2, 데이터 뒤).
9. **codex 에는 FW_W 입구·엮임 보호가 없습니다**. USG 는 신호 머리 차로를 원천으로 보므로 129·10491(머리 없음)을 그대로는 못 봅니다. 차로 구간 점유 함수·반공간 행·seed 투영은 따로 떼어 쓸 수 있는 꼴입니다(§4).
10. B 에서 codex USG 가 SC1001 p3 에 걸린 결정은 v3c3-s31 의 3,300·4,650 s 둘뿐이고, v3c3-s41·s43 은 0, 세 시드 모두 900–2,700 s 에는 0 이었습니다(§4.2, 데이터 뒤).

---

## 1. plant 표현 (127·129·10491·26, in_SC1001_W, 진출 포트)

### 1.1 대상별 표현

| 대상 | plant 표현 | 자리 | 태그 |
|---|---|---|---|
| 링크 26 (FW_W 첫 링크, 3,818.55 m, 3차로) | FW_W 31칸 중 칸 0–9. 칸 0–5 는 546.05 m. 칸 6 = 3,276.3–3,401.0 m, 칸 7 = 3,401.0–3,525.6, 칸 8 = 3,525.6–3,638.4, 칸 9 = 3,638.4–3,822.4(26 끝 180.2 m + 10771 3.8 m). 차로를 나누지 않음 | geometry.json(v3c3, sha `2e3d8bfe…`, plant manifest `/sources/geometry`) `/bounds/FW_W`, `/cells`, `/chains/FW_W`; `plant_n31_v2.json` `/lane_groups` = false; LFR:108-127(집계 길) | [실행 파일 읽기; 읽음] |
| INPUT1099 의 "26 차로 1 끝 3,200–3,700 m" | 칸 6–9 에 걸침, 3차로 합쳐서 | 위 bounds | [계산] |
| 입구 1099 | 칸 0 의 원천. 넣을 율 = A1 예측 `min(recent, demand + backlog·3600/step)` 재귀 | SB:37-60, :106-123, :126-160; LPR:603-608(원천 대기 0 에서 시작, 아니면 ValueError) | [읽음] |
| 진출 10479 (OR_D_W direct) | 칸 7 에서 나감(3,425.4 m) | geometry `/boundaries` OR_D_W_direct; V-A `/metadata/n31_binding/off_from_cell/10479` = 7 | [실행] |
| 합류 RM_C10480 | 칸 8 로 들어옴(3,625.8 m) | geometry `/boundaries` RM_C10480 `to_cell` 8 | [실행] |
| 진출 10491 (OR_D_W signal) | 칸 9 에서 나감(3,650.9 m). 저장 = `DelayedPort` 38.58대(= 커넥터 231.5 m ÷ 6 m). 첫 재고 = 결정 시각 10491 위 관측 차량 | geometry `/boundaries` OR_D_W_signal `from_cell` 9; LPR:378-391; HAR:76-180; V-A `/metadata/physical_branch_projection_capacity/OR_D_W_storage` `effective_veh` 38.582 | [실행; 읽음] |
| 10491 포트 방류 | SA 지퍼 합동 배분: 요청 = min(1,400 × 1차로 ÷ 3600 /s, 준비 대수); 차로별 몫은 127 차로 빈자리(10481 과 지퍼로 나눔); 합동 상한 = S_eff(in_SC1001_W) | SA:1464-1506; LOR:56-59, :78-81 | [읽음] |
| 링크 129 | 따로 된 저장 없음. 32·10778·129·10777·127 이 한 저장고 in_SC1001_W(설정 1,237.8대). 129 위 "꼬리"(포트 경로이고 `tail129_from_m` 하류인 차)만 127 차로 이동 꾸러미로 놓임. 10491 에서 나간 차는 **방류 순간** 127 차로 재고에 더해지고, 129 나머지·10777 통과는 도착 시각(due)으로만 남음 | OUC `/config_overrides/network/urban_link_storage_veh/in_SC1001_W` 1237.8; SA:929-950; SA:1535-1541; N12 §2.2 | [실행; 읽음] |
| 링크 127 | SA 3차로 FIFO 색인. 차로 저장 S = 81 / 63 / 103.58대(`observed_full` 팔). 차로 1 = {E, S}, 2 = {E}, 3 = {N} | SA:7-10, :337-449; V-A `/metadata/stopline_approach_storage_veh` | [실행; 읽음] |
| 미터 10490 대기 | 램프 커넥터 버퍼(머리 272.6 m × 1차로 ÷ 6 m ≈ 45.4대). 공급 movement `SC1001_W_to_onE` 의 점 대기는 차로·위치가 없고 S_eff(in_SC1001_W) 만 줄임 | N12 §2.2; UQM:231-256; PT PRB:462-466 | [읽음; 계산] |

- OUC = `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`(sha `c8e3ee2c…`). V-A 결정 JSON 값은 v3c3-s31 T=2,700(`action_002700.json`) 입니다 [실행].

### 1.2 10491·129 쪽이 찰 때 plant 가 하는 일 (1 s 스텝마다)

1. 127 차로 재고(이동 꾸러미 포함)가 차로 저장 S_l 에 닿으면 그 차로 빈자리 = 0 입니다(SA:1467). 10491 몫 배분과 FIFO 몫이 0 이 되고, 방류 상한이 요청보다 작으면 `port_blocked_steps_10491` 을 셉니다(SA:1474-1495) [읽음].
2. 포트에 차가 쌓입니다. 포트 재고 ≥ 용량 − 1(= 37.58대)이면 `port_full_steps_10491` 을 셉니다(SA:1502-1504) [읽음].
3. 고속도로 스텝 전에 `LaneOfframpRuntime.capacities` 가 포트 빈자리 × 3600 을 진출 수용으로 넘깁니다(LOR:138-141, LC:95-98) [읽음].
4. FW_W 는 집계 칸 길(AFA `_freeway_substep_events`)로 갑니다(LFR:116-127). 칸 9 의 10491 요청 = 분할비 × 칸 흐름, 받는 양 = min(요청, 수용)(AFA:324-331). 분할비는 K9-1 F17b 예측입니다(V-A `/metadata/k9_f17b/per_exit/10491` `forecast` 0.2455, T=2,700) [실행; 읽음].
5. 못 나간 몫은 칸 9 에 남습니다(칸 유출에서 빠짐, AFA:349-352, :363). 그리고 칸 9 속도에 `boundary_speed_cap = 유출 ÷ (밀도 × 차로)` 를 겁니다(AFA:353-354, :399-401). 이 상한은 칸 전체(3차로)에 걸립니다. J1 문서가 F13 "10491 막힘 때 단면 상한이 3차로 전체" 로 적은 것과 같은 자리입니다 [읽음 `SP/j1/analysis/ANALYSIS.md:38`].
6. 상류로 번지는 길: 칸 받을 자리 = (ρ_max − ρ) × 길이 × 차로 ÷ dt(AFA:219), 칸 사이 흐름 = min(보냄, 받을 자리)(AFA:253), 속도 갱신의 하류 밀도 항(AFA:392). 칸 9 → 8 → … → 0 [읽음].
7. 칸 0: 넣은 양 = min(요청, 원천 용량, 받을 자리)(AFA:281). 못 넣은 차는 `mainline_origin_queue` 에 쌓입니다(AFA:288). 외부 → 원천 전이는 Ω 밖(AFA:264-265), 원천 → 칸은 Ω 안(AFA:289-290) 입니다. 그래서 **목적 Ω 는 FW_W 칸 재고는 보고, 입구 밀린 줄은 보지 않습니다** [읽음; Ω 소속은 `SP/c_port/INPUT1099.md:30`].

### 1.3 언제 막히나 — 코드 조건과 기존 산출

- 코드 조건 [읽음 SA:1464-1506]: 10491 포트가 막히려면 (i) 10491 이 쓰는 127 차로의 빈자리가 0 이거나 (ii) S_eff(in_SC1001_W) 합동 상한이 묶여야 합니다. 129 차로 1 의 국소 자리(착지 239.38 m → 10490 갈림 299.99 m, 60.6 m, 6 m 간격으로 약 10대 [읽음 N12 §2.1])는 조건에 없습니다.
- 미터 대기 길과 SG2 길이 다릅니다 [읽음]: 10490 대기(`SC1001_W_to_onE` 점 대기)는 127 차로 빈자리를 줄이지 않고 S_eff 만 줄입니다(N12 §2.2, UQM:231-256). SG2 단축으로 127 차로가 차는 길은 127 차로 빈자리(81 / 63 / 103.58대)에서 바로 묶입니다(SA:1467). METER_NEXT2 N2 의 "모형 문턱 = 저장고 전체 1,237.8대" 는 앞의 길(미터 대기)에 대한 문장입니다 [읽음 `N/METER_NEXT2.md:162-177`].
- V-A v3c3-s31 T=2,700 첫 상태: 127 차로 재고 44.41 / 33.13 / 9.46대, 넘침(`excess_veh`) 0, 129 꼬리 포트 차 2.0대, 10491 커넥터 2대 [실행 `/metadata/stopline_approach_initial`, `/metadata/physical_branch_projection_target_veh/OR_D_W_storage`].
- C1 탐침 OFF 팔 plant 잡(R-obs v3c3-s31 T=1,500, 450 s): 10491 재고 3.08 → 최대 약 3.6대(용량 38.58), 블록별 막힘 스텝 0, `first_block_t/10491` null, `offramp_blocked_flow_10491` 모두 0 [실행 `D:/VISSIM-merge/k8_gate_trees/c1/out/probe/plant/sa/jobs/c1poff/TL3_1500_SAF_OBS_H3/summary.json`].
- K8 SA 관문(트리 k86h, 판정 팔 SAF = 지금 배포 저장 팔) [읽음 `SP/sagate/SA_GATE_REPORT.md`(sha `89eb0aac…`)]
  - FH 표본 SAF: 사건 상태 10491 막힘 적중 v3c3-s31 5/5, s41 2/2, s43 4/4. 비사건 상태 막힘 v3c3-s31 0/4, s41 2/7, s43 1/5 (:274-279).
  - 사건 상태의 plant 첫 막힘은 VISSIM 127 대기 500 m 첫 시각보다 늦게 옵니다(G-EB-6 (d), :119). 이 범위는 v3c3-s47 상태가 섞인 표본이라 숫자는 옮기지 않습니다.
  - v3c3-s31 사건 상태(2,700·3,000·3,600·4,200·4,950 s)에서 SC1001 p3 녹색 +6 s 의 plant FW_W(T+450) 미분 × 6 = −24.6 / −25.1 / −22.2 / −31.3 / −32.5대, 비사건(900·1,200·1,800·2,250 s)은 +0.162–+0.176 (:130-139). 같은 문서는 p3 축 녹색 벡터를 블록 0·1 에서 {p3: +1, p4: −1} 로 적습니다(:140). → **사건 상태에서는 plant 안에 SG2 → FW_W 길이 있습니다** [읽음].
- K8 보충 20 §2.2·§2.4(v3c3-s43 긴 L1 기간, sha `2cfbddbf…`) [읽음]: VISSIM 은 127 차로 1 이 67–78대(관측 만차 81 밑)일 때도 10491 느린 차 27–35대가 생깁니다(착지 합류 간격, M2). 같은 기간 plant 포트 막힘은 0, 커넥터 재고 최대 3.72대입니다.

### 1.4 plant 에 없는 것 [읽음]

1. 링크 129 차로 1 국소 저장: 없음. 129 는 in_SC1001_W 에 녹아 있고, 10491 차는 방류 순간 127 차로 재고로 셉니다(SA:1535-1541).
2. 링크 26 차로 1: 없음. FW_W 는 차로 그룹이 꺼진 집계 칸입니다(`plant_n31_v2.json` `/lane_groups` false; LFR:116-127). VISSIM 의 "10479·10491 차로 바꿈 거리 9999 m 로 75.7 m 부터 차로 1 에 모임" [읽음 INPUT1099:39, :103] 은 표현되지 않습니다.
3. 링크 26 이라는 이름: P0-10 은 plant 코드·manifest·OUC 에서 걸림 0 으로 적었습니다 [읽음 P0_PROBE §3-3]. 덧붙임 [실행]: plant 가 읽는 기하 파일은 26 을 FW_W 사슬 첫 링크(`/chains/FW_W/0`, offset 0)로 갖고, 진출 목록 파일 `offramp_route_inventory_v1.json` 은 `/groups/OR_D_W/decision_link` = "26"(결정 1132)로 갖습니다. 칸 단위 대응(§1.1)은 있고 차로 단위 대응은 없습니다.
4. 1099 밀린 줄의 상태: 원천 대기는 0 에서 시작합니다(LPR:603-608). 밀린 양은 A1 의 `backlog_veh` 로만 넣을 율 예측에 들어갑니다(SB:37-60). 그 값은 관측입니다(§3.1 7번).

### 1.5 참고 — 모형 쪽에서 129·10491 을 바꾸는 자리 (장치가 아니라 plant 수정)

- 포트 방류 조건: SA:1464-1506(`_joint_ports`)에 129 차로 1 국소 빈자리 항을 더하는 자리. 진출 수용: LOR:138-146. 단면 상한(F13): AFA:349-354 [읽음; 바꾸면 G-K0 류 관문 대상이라는 것은 추론].

---

## 2. 결정 층

### 2.1 SC1001 현시 후보 — SG2(p3) 하한을 넣을 수 있는 자리

**지금 구조** [읽음]

| 항목 | 내용 | 자리 |
|---|---|---|
| 좌표 | 신호마다 녹색 축. 동시 현시 기준(`concurrent_p1_p2`)이 아니면 축 = 마지막 현시를 뺀 현시들, 각 축 벡터 = {그 현시 +1, 마지막 현시 −1}. SC1001 은 p1·p2·p3 축, p4 가 받침 | PT SD:347-351 (OU SD:318-322); 관문 기록 {p3: +1, p4: −1} [읽음 SA_GATE_REPORT:140] |
| 현시 한계 행 | 현시마다 행 (max(lo, a − 6) − a, min(hi, a + 6) − a). a = 직전 실행 녹색, lo/hi = `phase_bounds` | PT SD:355-360 (OU SD:326-331) |
| lo 의 원천 | 모든 현시 같은 전역 `green_min`(기본 20 s). 현시별·신호별 하한 키 없음 | SAC:44-80, :83-103; `vendor/NumSim-mine/src/models/state.py:291` |
| 이동 한도 | 녹색 6 s, 미터 2 s(설정 `max_green_change_sec`), offset 은 신호별 | AFO:1290-1299 |
| 3블록 | 블록 k 는 직전 실행 기준 한도 × (k+1), 블록 사이 ±한도. 블록마다 같은 `Coordinates` 를 만듦 | SEQ:101-107, :109-153(:116-117, :145-153) |
| 후보가 모두 지나는 곳 | PFO 의 QP 가 `coord.G·glo·ghi·lower·upper` 를 씀; `decode` 는 valid 가 아니면 ValueError; 가능 검사 `feasible` | PFO:32-34; PT SD:417-424; PT SD:805-811 (OU SD:618) |
| 운영 seed 투영 | 직전 명령이 범위 밖이면 **미터 축만** 자름 | PT SD:766-773 |

- V-A v3c3-s31 T=2,700 의 SC1001 실행 녹색: p1 34.253 / p2 20.0 / p3 50.294 / p4 33.453 s, offset 8.091 s [실행 `action_002700.json` `/green_times`, `/offsets/SC1001`]. p2 = 20.0 = `green_min` 입니다.

**p3 하한을 넣을 수 있는 자리 셋** [읽음 코드; 각 줄의 주의는 추론]

| # | 자리 | 꼴 | 코드가 이미 가진 것 | 넣을 때 걸리는 것 |
|---|---|---|---|---|
| (가) | PT SD:355-360 의 SC1001 p3 행 하한 | 하한 = max(전역 lo, 새 하한) | 행 구조, 3블록 복제(SEQ:116-117) | 새 하한 > a + 6 이면 그 행이 빈 범위가 되어 풀 수 없음. 직전 명령이 새 하한 밖이면 `coord.valid(reference)` 거짓 → 지금 seed 투영은 미터 축만 고치므로 `decode` 예외(PT SD:766-773, :421-424). 녹색 축 투영(codex USG `operating_seed` 꼴)이 함께 필요 [추론] |
| (나) | `Coordinates.__init__` 끝(PT SD:400 `self.owners` 줄 뒤)에 반공간 행 추가 | w·z ≥ required, w = SC1001_p3 무게를 녹색 벡터로 옮긴 것 | codex 가 같은 자리에서 부름(CX SD:438-439), 식 CX USG:102-145, seed 투영 CX USG:148-166 | required = min(예비 녹색, 0.5 × 이동 한도 안 최대)라 늘 풀 수 있음. 직전 명령 대비 "더 줌" 이라 절대 하한이 아님 [읽음 CX USG:133-134] |
| (다) | 가능 검사 `feasible`(PT SD:805-811) | plant 예측량 조건(예: 포트 만차 스텝, 칸 9 막힘) | 미터 하한도 같은 함수 안에서 `coord.valid` 로 거름(PT SD:807-808) | 관측이 아니라 예측. §1.3 의 늦은 막힘·L1 과소 막힘을 그대로 받음 [추론] |

- 다른 SC1001 지렛대(offset, 하류 SC1002 녹색)는 이 문서 범위 밖입니다.

### 2.2 미터 10490 후보 거르기 — C1 M4 경로와 두 번째 저장 대상

**경로** [읽음]

1. `solve` 가 직전 실행 기준(`reference`)을 만든 뒤 `c1_port.operating_bounds(state, cfg, reference)` 를 부릅니다(PT SD:744-750).
2. 그 안에서 PRB `configure_operating_bounds` 를 부릅니다(PT C1P:263-267). 이 함수 본문은 codex 와 바이트가 같습니다(PT PRB:444-482 = CX PRB:871-909, `diff` 0) [실행].
3. 발동: 미터마다 자기 버퍼 차로별 (상류 이동 + 머리 준비) ÷ (머리 위치 × 차로 ÷ 간격) ≥ 0.9(PT PRB:458-472). RM_C10490 은 머리 272.6 m × 1차로 ÷ 6 m ≈ 45.4대 [계산]. 이것은 D5 의 VISSIM 기하 문턱 "커넥터 약 45대 + 129 차로 1 약 10대" 의 앞부분입니다 [읽음 N12 §2.1·§2.4; 대응은 계산].
4. 하한 = max(2, min(10, 직전 + 2))(PT PRB:474). 직전이 g10 이면 하한 10 → 그 결정은 10490 조임 없음.
5. `cfg.network.ramp_operating_green_floors` 에 씀(PT PRB:478) → RV-2 내림과 G-A7 검사(PT C1P:268-285).
6. 쓰는 곳: 미터 허용 집합(|g − a| ≤ 2, g ≥ 하한, 녹색 0 금지; PT SD:367-380), 이웃 후보(축 `allowed` 만 씀, PT SD:550-594), 가능 검사(PT SD:805-808), 운영 seed(PT SD:766-773), 기록 `/metadata/meter_operating_bounds`(PT SD:1177).
- P0-5: 5상태 모두 발동 0, 차로 점유율 최대 0.227 [읽음 P0_PROBE §2].

**두 번째 저장 대상을 받을 수 있나** [읽음]

- 지금 꼴로는 받지 않습니다.
  - 정책 키는 정확히 `{"enabled", "trigger_fraction"}` 만 받습니다(PT C1P:57-61). 모르는 하위 키는 ValueError 입니다(PT C1P:79-81).
  - 발동은 그 미터 자기 버퍼 차로만 봅니다(PT PRB:458-472).
- 넣을 수 있는 자리
  - `c1_port.operating_bounds`(PT C1P:263-286) 안, `configure_operating_bounds` 결과 뒤에서 RM_C10490 의 `triggered` 를 OR 로 켜고 같은 하한식을 쓰는 자리. G-A7 검사(PT C1P:283-285)는 발동 시 하한 ≥ min(직전 + 1, 10) 을 요구하므로 같은 하한식이면 맞습니다 [읽음; 맞음은 산술].
  - 키는 `c1_port` 새 하위 키(또는 `storage_release_guard` 의 새 필드)로 넣어야 합니다. 지금 검사가 둘 다 막습니다(PT C1P:57-61, :79-81).
- 그 자리에서 이미 쓸 수 있는 상태 값(관측으로 시작한 값)
  - 10491 포트 재고 `state.lane_offramp_runtime.ports['10491'].stock`(LPR:388-391, 첫 값 = 10491 위 관측 차량).
  - 127 차로 재고 `state.stopline_approach_state['stock']`·넘침 `['init_excess']`(SA:1064-1068).
- 상태에 없는 값: 129 차로 1 위치별 대수, 26 차로 1 구간 대수. 이것은 RS 에서 관측(`state_json`)으로 세어 `cfg.network` 에 실어야 합니다. codex USG 는 같은 일을 RS 의 물리 미터 설정 뒤에서 합니다(CX RS:253-254). 우리 RS 의 대응 자리: 물리 미터 설정 PT RS:496(OU RS:490) → 상태 만들기 PT RS:503(OU RS:497) → lane plant PT RS:544(OU RS:538) → SA PT RS:551(OU RS:545) [실행 grep].
- 작용 뜻 [추론]: 10490 녹색 하한은 129 차로 1 위 **10490 행** 차를 빼는 쪽만 돕습니다. 129 차로 1 이 127 넘침(10491 착지 → 127 행 차)으로 찼을 때는 10490 녹색이 그 줄을 줄이지 않습니다. 두 무리는 관측 경로 번호로 가를 수 있습니다(§3.1 2번). INPUT1099 는 B 의 1099 사슬에서 미터 10490 기구(H3a)를 세 시드 모두 반박으로 적었습니다 [읽음 INPUT1099:187-195].

### 2.3 설정에 켜져 있지만 V-A 결정 길에 닿지 않는 보호 [읽음]

- OUC `/actuation/real_world_ramp_metering/spillback_guard` = {enabled true, 문턱 8대, 하한 1,800 veh/h}(OUC:7499-7503).
- 부르는 곳은 둘입니다.
  - AMF:150(`finalize`). 그러나 물리 미터면 AMF:133-134 에서 먼저 돌아갑니다.
  - ADP:14143(PT ADP:14148). 이것은 control area 가 꺼진 가지입니다(ADP:14137-14144). V-A 는 control area 를 켭니다(`area_runtime.py:212`, OUC `/control_area_objective`).
- 그래서 이 보호는 V-A 결정에 닿지 않습니다.
- 그 관측 `ramp_spillback`(ADP:6643-6676)은 검지 매핑 `ramp_spillback_links`(파일 `evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json`, sha `f8c90e57…`)의 `R_D_E[0]` = 링크 129 차로 1 정지 차(위치 상한 없음, 10490 앞)를 셉니다 [실행 파일 읽기].
  - 키가 옛 묶음 이름(R_D_E)이라, 물리 미터 키(RM_C*)만 있는 `ramp_queue` 에서 건너뜁니다(ADP:6632, :6655). 물리 미터 설정(RS:490)이 상태 만들기(RS:497)보다 먼저라 그때 미터 키는 RM_C* 입니다 [추론, 코드 순서].
  - V-A v3c3-s31 T=2,700 기록의 `ramp_spillback_duplicate_avoided_veh` 는 0.0 입니다 [실행].

---

## 3. 결정 시각에 관측되는 것 (보호 장치를 움직일 수 있는 값)

### 3.1 관측 원천 [실행 V-A·B `state_NNNNNN.json` 키 읽기; 읽음 코드]

| # | 원천 | JSON 경로 | 129·10491·26 에 대해 무엇 | 지금 결정 코드가 쓰는 곳 |
|---|---|---|---|---|
| 1 | 전체 차량 기록(결정 시각 멈춘 스냅샷, `complete` true) | `/vehicle_records/records[]` = {veh_no, link_no, lane_no, position_m, speed_kph, stopped(< 1 km/h)} | 129 차로 1 위치 구간 대수·정지, 10491 대수·정지, 26 차로 1 3,200–3,700 m 대수·정지 모두 셀 수 있음 | PS:16-36(검사); SA 초기화(127·10777·129 꼬리, SA:765-955); 포트 첫 재고(LPR:388-390) |
| 2 | 차량 경로 | lane frame `/obs150/frames/current` {path, sha256}(`lane_observations/frame_NNNNNN.json`, UTF-16, 행 = [veh, link, lane, pos, speed, 길이, RoutDecNo, RouteNo, RoutDecType, …]) → `vehicle_routes` 로 붙임 | 26 위 차 중 결정 1132 의 10491 행 경로 차(보충 20 §2.2 는 "1132-2" 로 씀), 129 위 차 중 10490 행(…129→10490→119)과 127 행(…129→10777→127) | LPR:208-235(`bind_current_routes`); SA:799-800; 경로 목록 꼴은 CX PRB:290-291 [읽음] |
| 3 | 링크 합계 | `/vehicle_records/full_network_link_counts`, `/full_network_link_stopped_counts`; `/local_observation/link_counts`, `link_speeds_kph`, `link_stopped_counts`, `link_queue_tail_pos_m` | 링크 단위(차로 없음) | ADP:6282-6320(요약), :6701-6702 |
| 4 | 7 m 차로 칸 | `/local_observation/queue_bins` 키 "링크\|차로\|칸" → [대수, 정지], `queue_bin_m` 7 | 129·10491·26 칸(차가 있을 때만 키) | 127 은 ADP:5424-5470 → SA 초기화. 129·10491·26 칸은 쓰는 곳 없음 [읽음] |
| 5 | 대기 계수기(150 s 구간, 러너 env `RW_QUEUE_COUNTER=1`) | `/local_observation/queue_counters/counters/<번호>` = [QLen 평균, QLen 최대] (m) | 2012 = 127 @624.05 m, **200122 = 129 @300.03 m**(10490 갈림 끝), **200141 = 26 @3,387.7 m**, **200142 = 26 @3,675.5 m**(10491 갈림 25 m 하류), 30004 = 10490 @272.6 m, 200121 = 32 @1,023.7 m [실행 .inpx `3de889f0…`] | 키 목록에만 있음(`obs150_observation.py:799`). 결정 코드 소비자 없음 [실행 git grep] |
| 6 | DCP 150 s 수 | `/obs150/detectors/<번호>`(구간), `/obs150/detectors_cum` | 960225 = 10491 진입(1 m); 960232–960234 = 26 @3,525.6 m 차로 1–3(through:10479); 960241–960243 = 10771 @3.7 m 차로 1–3(through:10491); **960282–960284 = 26 @40 m 차로 1–3(입구)**; 960272 = 10490 램프 도착; 960219 = 10490 머리; 960155–960157 = 127 머리 [실행 `obs150_detectors_v2.csv` sha `108debbb…`] | obs150 계약·관측(`obs150_contract.py:1060-1090`), 원천 경계 |
| 7 | 입구 밀린 양 | `/obs150/source_cumulative_vehs/FW_W`(= 960282–960284 누적, `obs150_contract.py:1067-1088`) → 결정 JSON `/metadata/n31_binding/source_boundary/by_road/FW_W/{backlog_veh, recent_vph, admitted_window}` | backlog = 1099 일정 적분 − 40 m 통과 누적. V-A v3c3-s31 T=2,700: 585.0대 / 4,584 veh/h / 191대 [실행] | SB:106-123 → A1 넣을 율(SB:37-60) |
| 8 | 링크 평가 유량 | `/local_observation/far_measurement/link_volume_veh_h`(53 링크; 10491·10490·10479·10480 있음, 26·129·127 없음), `/obs150/linkeval_volume_veh_h`(커넥터 10개, 10491 있음) | 10491 유량(150 s) | far 배수율 갱신 |
| 9 | 신호 기록 | `/obs150/signal_log` | SC1001 SG 상태 구간(SG2 녹색 이력) | `obs150_contract.py:960-961` |
| 10 | 관측으로 만든 상태 값(결정 JSON 기록) | `/metadata/stopline_approach_initial/{stock_veh, excess_veh, tail129_port_veh, other_link_ready_veh}`, `/metadata/physical_branch_projection_target_veh/OR_D_W_storage`, `/metadata/k9_f17b/per_exit/10491` | 127 차로 재고, 127 넘침, 129 꼬리, 10491 커넥터 차, 10491 분할 예측 | SA·LPR·F17b |

- 망 안 DCP 910001–910003(26 @3,575.1 m), 910059–910061(26 @3,675.8 m)은 `.inpx` 에 있지만 관측 JSON 에 오지 않습니다(`rule_crosscheck` 는 910030–910047 만) [실행].
- VISSIM 링크 평가는 26·129·10491 에서 켜져 있지만(`linkEvalAct` true, 10 m) 밀도·속도 칸 값은 관측 JSON 에 오지 않습니다 [실행 .inpx·state 키].
- `.inpx` 의 신호용 검지기(detector)는 0개입니다 [실행].

### 3.2 기존 상태 파일에서 본 값 — 관측이 움직이는지 (데이터 뒤, 판정 아님) [실행 `GD/work/obs_probe.json` sha `43eb221b…`]

- 범위: V-A·B, v3c3-s31·s41·s43, T = 1,800·2,100·2,400·2,700·3,000·3,300 s(시드마다 6상태). 표 값은 6상태 중 최대(입구 40 m 수는 최소–최대).

| 팔·시드 | 10491 대수 / 정지 | 129 차로 1 대수 / 정지 | 26 차로 1 3,200–3,700 m 대수 / 정지 | QC 2012(127) 평균 범위 m | QC 200122(129) 평균 최대 m (처음 > 0 인 T) | QC 200141(26 @3,387.7) 평균 최대 m | QC 200142 최대 | 입구 40 m 150 s 수 | 10491 진입 150 s 수 |
|---|---|---|---|---|---|---|---|---|---|
| V-A s31 | 4 / 0 | 9 / 0 | 21 / 2 | 238.7–394.3 | 0 | 0 | 0 | 166–186 | 39–48 |
| V-A s41 | 5 / 0 | 13 / 0 | 17 / 0 | 189.8–349.7 | 0 | 0 | 0 | 162–197 | 37–45 |
| V-A s43 | 8 / 0 | 11 / 1 | 18 / 0 | 147.9–280.9 | 0 | 0 | 0 | 170–200 | 28–51 |
| B s31 | 26 / 18 | 23 / 15 | 57 / 29 | 317.3–505.5 | 500.4 (2,400) | 471.6 | 0 | 145–180 | 13–52 |
| B s41 | 34 / 33 | 36 / 29 | 39 / 28 | 449.1–503.5 | 439.3 (2,100) | 436.2 | 0 | 94–187 | 13–48 |
| B s43 | 29 / 17 | 18 / 7 | 25 / 9 | 411.8–501.7 | 345.5 (2,400) | 253.8 | 0 | 169–196 | 32–48 |

- 대기 계수기 값은 약 505–510 m 근처에서 더 오르지 않습니다(B s31 QC 2012 최대 510.2 m 등) [실행]. 까닭(대기 정의의 최대 길이 설정 등)은 확인하지 않았습니다 [추론].
- QC 200142(10491 갈림 25 m 하류)는 B 에서도 모든 표본이 0 입니다 [실행]. 그 지점의 차로들이 흐르는 동안 0 이 되는 자리로 보입니다 [추론].
- 정지 판정은 `stopped`(< 1 km/h, `/vehicle_records/stopped_threshold_kph` 1.0) 입니다 [실행].

### 3.3 관측되지 않는 것 [읽음·실행]

- VISSIM 입력 1099 의 실제 대기 차량 목록(망 밖)은 관측에 없습니다. 있는 것은 일정 적분 − 40 m 통과 누적(§3.1 7번)입니다.
- 26·129·127 의 링크 평가 밀도·속도 칸 값.

---

## 4. codex 코드 — FW_W 입구·엮임·도시 저장 보호와 재사용 가능성

### 4.1 기구별 [읽음 CX 코드; 실행 git grep·파일 읽기]

| 기구 | codex 자리 (sha 앞 16자) | 하는 일 | 129·10491 에 쓸 수 있는가 |
|---|---|---|---|
| FW_W 입구·엮임 보호 | 없음. `git grep -i "weav\|1099\|entrance"` 결정 코드 걸림은 LOR:236 설명문("discretionary weaving 아님") 하나 [실행] | — | 해당 없음 |
| 도시 저장 보호 USG 관측 `configure` | CX USG:13-99 (`2c24b570…`), 부르는 곳 CX RS:253-254 | 신호 머리 차로마다 원천 점유 = 그 링크 0 → 머리 위치 차 수 ÷ (길이 ÷ 6 m), 받는 쪽 = 머리 하류 커넥터의 착지 차로. 점수: 받는 쪽 모두 ≥ 0.9 이면 −1, 원천 ≥ 0.9 이면 원천 점유율. 관측은 전체 차량 기록(CX USG:27-34) | 그대로는 못 봄. 원천은 신호 머리가 있는 링크 차로만이고(CX USG:60-66), 129·10491 에는 머리가 없음. 받는 쪽은 머리 하류만 봄(CX USG:68-76) — 129 는 127 의 상류 |
| USG 점유 함수 `occupancy(link, lane, start, end)` | CX USG:51-56 | 차로 구간 차 수와 점유율 | 그대로 쓸 수 있는 꼴. 예: 129 차로 1 [239.38, 299.99], 10491 [0, 231.5], 26 차로 1 [3,200, 3,700] [읽음; 구간 값은 §1.1·§3 의 기하] |
| USG 반공간 `constrain(coord)` | CX USG:102-145, 부르는 곳 CX SD:438-439(`Coordinates.__init__` 끝, 블록마다) | 신호마다 현시 무게 w → 녹색 축 행 w·z ≥ required, required = min(예비 녹색 2 s, 0.5 × LP 최대) | 무게를 {SC1001_p3: …} 로 주면 그대로 쓰는 꼴. 우리 `Coordinates`(PT SD:329-400)에는 이 부름이 없음 |
| USG seed 투영 `operating_seed` | CX USG:148-166, 부르는 곳 CX SD:853-855 | 직전 명령을 새 제약 안으로 QP 투영(녹색 축 포함) | 우리 seed 투영은 미터 축만(PT SD:766-773). 녹색 하한을 넣으면 이 꼴이 필요 [추론] |
| 미터 저장 보호 | CX PRB:871-909 (`0ab140ac…`) | §2.2 와 같은 식 | PT PRB:444-482 와 본문 같음 [실행 diff]. 두 번째 대상은 없음 |
| 머리 자원 v11 | CX `head_service_resources.py`(`777fc1f9…`), 계약 `diagnostics/repin_v3c3_review_20261001/urban_rm269/sc6_queue/head_resources.json`(`73916c41…`) | 머리 그룹별 실측 서비스율로 movement 용량을 덮음 | 127·129·10491 자원 없음. SC1001 자원은 10698(40\|p2)·10119(29\|p3) 둘 [실행 JSON 훑기]. 저장 보호가 아니라 서비스 측정 |
| 단일 차로 램프 진입 수용 | CX `ramp_entry_receiving.py:11-49`(`f47602a8…`) | 1차로 램프 합류 받을 자리(뒤로 가는 파)를 plant 에 붙임 | 램프 합류 쪽. 129·10491 저장과 무관 |
| SC1001 공유 접근(plant) | CX LOR:13-75(관측 출처 꼬리표), :79-…(`SharedSignalApproach`), :440-500(설치) (`9203f596…`) | 127 차로 저장 = (머리 위치 + 10777 길이) ÷ 6 m, 10491 진입은 도착 지연 뒤 목적 차로 빈자리로 받음 | 129 차로 1 국소 저장 없음(우리 SA 와 같은 구조 한계). codex HANDOFF 도 D5 를 남은 한계로 적음 [읽음 R_MECH:160]. 관측 쪽 129 차 출처 가르기(CX LOR:27-37: 32·10778 또는 129 착지 앞 = 도시, 10491·10481 = 진출)는 떼어 쓸 수 있는 꼴 |
| 옛 묶음 미터 넘침 보호 | CX AMF:283-290 = OU AMF(같은 sha `017c6eaa…`) | 넘침 > 8대면 그 묶음 율 하한 1,800 | §2.3 과 같음. 물리 미터 길에서 닿지 않음 |

### 4.2 B 에서 codex USG 가 SC1001 에 걸린 기록 (데이터 뒤) [실행 `GD/work/b_usg_sc1001.json` sha `4a4f4eb0…`]

- 읽은 것: B 결정 JSON `/metadata/joint_leader_selection/urban_storage_guard/{observation, blocks}`, v3c3-s31·s41·s43, T = 900–9,000 s(시드마다 55결정).
- SC1001 p3 에 점수 > 0 이고 반공간이 걸린 결정: v3c3-s31 의 3,300 s(127 차로 1 점유율 0.9265, 96대)·4,650 s(0.9169, 95대) 둘. 그때 required 2 s, 블록 0·1·2 가능 최대 6 / 12 / 18 s.
- v3c3-s41·s43: 0결정. 세 시드 모두 900–2,700 s 에는 0결정.
- 127 차로 1 점유율 최대: 0.9265 / 0.8783 / 0.7625(v3c3-s31 / s41 / s43). 분모는 차로 1 머리 위치 ÷ 6 m ≈ 103.6대입니다 [실행]. 우리 SA 차로 1 저장 S = 81대와 다릅니다 [읽음 §1.1].
- SC1001 의 codex 머리 차로 목록: 127 차로 1·2 = p3(받는 쪽 링크 30·39), 127 차로 3 = p4(받는 쪽 38), 그 밖 29·37·40 [실행]. 129·10491 은 목록에 없습니다.

---

## 5. 한 표 — 보호 장치가 작용할 수 있는 자리 (꼴·문턱·대상 결정은 사용자)

| 작용 대상 | 코드 자리 | 쓸 수 있는 관측(§3.1 번호) | 지금 있는 꼴 | 넣을 때 걸리는 것 |
|---|---|---|---|---|
| SC1001 p3(SG2) 녹색 | (가) PT SD:355-360 현시 행 하한 / (나) PT SD:400 뒤 반공간 행(codex CX USG:102-145 꼴) / (다) PT SD:805-811 예측 조건 | 1·2·4·5·6·10 (127 차로, 129 차로 1, 10491, 26 차로 1, QC 2012·200122·200141) | 현시별 하한 없음(전역 `green_min`); 반공간 행 없음 | 이동 한도 6 s(AFO:1290-1299); 녹색 축 seed 투영 없음(PT SD:766-773); 3블록마다 적용(SEQ:116-117) |
| 미터 RM_C10490 녹색 | PT C1P:263-286(`operating_bounds`) 안에서 RM_C10490 발동을 OR; 관측 값은 RS(PT RS:496–551 사이)에서 `cfg.network` 에 실음 | 1·2·4·5(129 차로 1 의 10490 행/127 행 구분), 10(10491 포트 재고는 상태에 있음) | M4 = 자기 버퍼 90 %, 하한 = max(2, min(10, 직전 + 2)) | 정책 키 모양 고정(PT C1P:57-61, :79-81); 129 차로 1 이 127 넘침으로 찬 경우 10490 녹색은 그 줄과 무관 [추론] |
| (참고) plant 수정 | SA:1464-1506, LOR:138-146, AFA:349-354 | — | 129 차로 1 국소 저장 없음, 단면 상한 3차로 전체 | 장치가 아니라 모형 변경 |

- 입구 1099 밀린 줄은 지금 목적 밖이고(§1.2 7번), 관측 `backlog_veh` 는 결정 JSON 에 이미 있습니다(§3.1 7번).

---

## 6. 한 일·하지 않은 일·파일

**한 일** [실행, 모두 읽기 전용]
- 코드 읽기: OU(`git show c20aff1d:` 와 작업 트리, status 0줄), PT 트리, CX(`a49981ff`, status 0줄). PT 와 OU 의 패치 밖 파일 `diff --strip-trailing-cr` 대조. 패치 덩어리 머리로 줄 이동 확인.
- 설정·증거 읽기: OUC, plant manifest, 기하 파일, 진출 목록 파일, 검지 매핑, obs150 검지 표, V-A 망 `.inpx`(대기 계수기·DCP·링크 속성).
- 기존 산출 읽기: V-A v3c3-s31 `state_000900.json`·`action_002700.json`, C1 탐침 OFF 팔 plant 잡 `summary.json`, K8 SA 관문 보고, 보충 20, J1 분석.
- 스크래치 스크립트 둘(`GD/work/`): `b_usg_sc1001.py`(`a7142e40…`) → `b_usg_sc1001.json`(`4a4f4eb0…`); `obs_probe.py`(`a0b6a417…`) → `obs_probe.json`(`43eb221b…`).

**하지 않은 일**
- 코드 변경·커밋·브랜치·푸시 0. GWT8 head `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`, status 0줄 [실행]. CX·동결본·런 폴더·인계 사본·Y: 쓰기 0.
- VISSIM·COM·러너·동결·재생·plant 잡 0. FZP 스캔 0. 금지 시험 0. kill 0. 다른 세션(VSL 워크플로·codex) 프로세스·잠금 건드림 0.
- 봉인 시드 37·59·61·67 열람 0. codex 64cf-s59/s61/s67 숫자 0. R-obs v3c3-s47 파일 열람 0.

**파일 (sha256 앞 16자)**

| 이름 | sha256 |
|---|---|
| 이 문서 `GD/FACTS_CODE.md` | 같은 폴더 `FACTS_CODE.md.sha256` 와 반환에 적음(이 폴더 밖 LOG 에는 쓰지 않음) |
| C1 탐침 패치 `C1D/tools/c1_probe.patch` | `5cdc6eb1e4249294` |
| 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` | `4429c003d021998e` |
| `C1D/P0_PROBE.md` r2 | `e467583f2f77b739` |
| `SP/c_port/C1_DESIGN_DRAFT.md` | `c32e1006a2a2c408` |
| `SP/c_port/INPUT1099.md` r2 | `c89011d8d1d7b3a4` |
| `SP/rmcause/r2c_n/METER_NEXT2.md` r2 | `acebbe738677eebc` |
| `SP/rmcause/r2c_n/N12_CODE_PLANT.md` | `1f630c3e851fc4e4` |
| `SP/codex_handoff/R_MECH.md` | `2fc879d62760621f` |
| `SP/sagate/SA_GATE_REPORT.md` | `89eb0aac688104bc` |
| `SP/K8_PREDECLARATION_AMENDMENT_20.md` | `2cfbddbfda027971` |
| `SP/j1/analysis/ANALYSIS.md` | `2be111156961465e` |
| OU SA / LOR / AFA / LFR / LC (c20aff1d 바이트) | `6a0b1788133f68be` / `488a5afed8d27aec` / `d52f8a0c6eb3485b` / `22d0003f06417941` / `527f7b0adf5faf23` |
| OU LPR / SB / SAC / SEQ / AFO / AMF | `493a5bf2e026c1b7` / `cb0aa19521644b35` / `f4f8005c6168a5a3` / `d96a611c590336a6` / `cbffc35966a7f0eb` / `017c6eaa78bf7b64` |
| OU ADP / RS / PRB / SD / OR / PS / UQM / HAR | `e616ade51ac7d5d5` / `70cca680ef9f5dd8` / `08cb370d20fb727c` / `352701a08b106285` / `e9eef95455df833c` / `683faa89a8b11fc1` / `3c5c109933d122e6` / `b539dcade695b866` |
| PT SD / PRB / C1P / LPR / RS | `41563db0606fe6be` / `72bf55d7f8d8b43a` / `dc74748d42d5d1ed` / `b142c1f5baf15880` / `fea820c166059780` |
| CX USG / SD / RS / PRB / LOR / REC / HSR / AMF | `2c24b570ca5ba6f2` / `5c1ba251a3526caf` / `74941f0382868dd3` / `0ab140ac0967348b` / `9203f59685ebac25` / `f47602a8238994f2` / `777fc1f9a0883e4b` / `017c6eaa78bf7b64` |
| OUC / 검지 매핑 / obs150 검지 표 / 세분 기하 | `c8e3ee2c99b66c25` / `f8c90e5769c7c92e` / `108debbb4b021796` / `9769b3a4462f5d9c` |

## 7. 알릴 것 (막힘 아님)

1. `b_usg_sc1001.py` 는 B 결정 JSON(파일당 약 54 MB)을 읽어 3분 20초 걸렸습니다. 묶음 무늬가 `action_*.json` 이라 같은 결정의 `.joint.json`·`.joint_written.json`·`.decision_budget.json` 도 읽혔습니다(시드마다 220파일 중 165개는 그 키가 없어 빠짐, 남은 55결정 값은 결정마다 하나로 겹침 없음). FZP 스캔·plant 잡이 아닌 JSON 읽기라 무거운 일 잠금 없이 돌렸습니다. 2분을 넘었으므로 밝힙니다. 다시 돌리지 않았습니다.
2. 이번에 읽은 기존 보고 두 개(`SA_GATE_REPORT.md` §4.7·G-EB-6 표, 보충 20 §2.3)의 표에는 v3c3-s47 숫자 칸이 있습니다. 이 문서에는 v3c3-s31·s41·s43 값만 옮겼고, s47 이 섞인 범위(G-EB-6 (d))는 숫자를 옮기지 않았습니다. R-obs v3c3-s47 자료 파일은 열지 않았습니다.
3. P0-10 의 "링크 26 = 모형 대응 없음" 은 코드 걸림 기준입니다. 기하 파일·진출 목록 파일에는 26 이 FW_W 사슬 첫 링크와 결정 1132 링크로 있습니다(§1.4 3번). 칸 단위 대응은 있고 차로 단위 대응은 없습니다.
