# N12 — 코드·plant 읽기: 206.53 이 들어가는 길(N1)과 링크 129·70 표현(N2)

- 판 r1, 2026-10-24 14:50 KST. 과제 D-K9-78 의 N1·N2. 읽기 전용입니다.
- 한 일: c20aff1d 코드를 `git show` 로 `r2c_n/n12/src/` 에 뽑아 읽음, 이미 있는 V-A 결정 JSON·U4 표·O4/VERIFY 분할 표를 읽음, 정적 재구성 스크립트 2개를 새로 씀(`n12/tools/`).
- 안 한 일: FZP 스캔 0, 새 VISSIM·COM·러너 0, 결정·plant 재생 0, 프로젝트 코드 import·실행 0, 커밋·푸시·체크아웃·동결 0, kill 0. 런 폴더·`D:/VISSIM-merge/frozen/*` 쓰기 0(읽기만: 동결 .inpx 한 개). 봉인 시드 37/59/61/67 자료 0, codex 64cf-s59/61/67 수치 0.
- 이 문서는 교통 지표 결과(주 지표 FW_E 본선 7링크 등)를 새로 내지 않습니다. 그래서 주 지표·옮겨 간 대기 표는 없습니다.

줄임말(처음 한 번만 풉니다)
- SDMPC: 우리 공간 분해 모형예측제어. plant: SDMPC 가 예측에 쓰는 모형. V-A: 2026-10-23 V-A 폐루프 런(`D:/VISSIM_runs/20261023_sdmpc31_k92/`). FZP: VISSIM 차량 기록 파일. NC: 무제어.
- U4 표: FZP 로 잰 정지선 헤드 그룹 포화류율 표(v3b 망, 무제어 5시드; `scratchpad/urban-b2/u4_saturation_table.json`, sha256 `22384c00…292b` = K9-2 W 증거가 핀한 값).
- 파일 약칭(모두 c20aff1d, 괄호는 blob id): RS `evaluation/controllers/runtime_setup.py`(bcf7a777), ADP `…/vissim_stackelberg_adapter.py`(3fd00007), UQM `vendor/NumSim-mine/src/models/urban_queue_model.py`(9e64b9e8), UFA `…/urban_flow_accounting.py`(3962a05e), RCC `…/route_choice_corridor.py`(cd35a0b5), HSR `…/head_service_resources.py`(78da444c), SHO `…/signal_head_observation.py`(37076a29), LUR `…/lane_urban_runtime.py`(6ef782a0), LOR `…/lane_offramp_runtime.py`(7927c452), LPR `…/lane_plant_runtime.py`(e788f596), SA `…/stopline_approach.py`(d9e9fe90; SC1001 동행 정지선 접근 모형), LRR `…/lane_ramp_runtime.py`(f9366026), PRBD `…/physical_ramp_boundary.py`(4492d2ef), PRB `…/physical_ramp_branches.py`(cef8bfea), AFA `…/area_freeway_accounting.py`(88b0256f), MSP `…/meter_spill.py`(55dfbdee), NIP `…/native_input_prehead.py`(8e7aa14b), LSS `…/local_signal_service.py`(4fa04c63), CFG `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`(b6ccd50d; 동결본과 sha256 `c8e3ee2c…1866` 같음 [실행]).
- S_eff(L): 링크 저장고 L 의 유효 빈자리 = 남은 저장 − L 을 출발지로 둔 movement 대기열 합(UQM:231-256).

---

## 0. 쉬운 답

1. **206.53 은 상수로 적혀 있지 않습니다.** 설정 `per_lane true`·`equivalent_uniform_veh_h 330`·`perimeter "all"`(CFG:7823-7825)에서 ADP:3832-3835 가 차로당 값 = 330 × 184 / 294 = 206.53061224489795 veh/h 를 만듭니다. 184 는 내부 movement 수, 294 는 그 차로 합입니다 [읽음; 산술 실행 = 런 기록값과 같음].
2. **경계 movement 는 ADP:3860-3896 에서 "206.53 × 차로수"를 받고, 뒤의 실측 갱신은 내부 movement 만 고칩니다**(ADP:4355 `lane_group_kinds` 기본 `["internal"]`, ADP:4588-4598) [읽음].
3. **SC1004 S→W 는 차로 1(물리 회전에서 확인), N→W 는 차로 1(같은 회전 종류 중앙값으로 추정)이라 둘 다 206.53 veh/h 입니다.** plant 의 UFA:589-591 이 `T_u × 녹색비 × 206.53` 을 서비스로 씁니다. V-A v3c3-s31 T=1950 기록에서 S→W 서비스 3.4422 대/450 s = 206.53 × (3 × 20 s)/3600, N→W 3.6256·3.5339 대 = 206.53 × 63.197 s·61.6 s /3600 입니다 [실행].
4. **같은 계열 값을 지금도 가진 경계 movement 는 165개입니다**(V-A 최종 목록 179개 중; 진입 107·진출 44·오프램프 movement 14). 이 중 **plant 가 실제로 읽는 것은 148개**입니다(일반 정지선 루프 146, 경로 회랑 예산 2). 나머지 17개는 plant 가 읽지 않습니다(SA 차로 대기열 3, 오프램프 movement 14) [실행 재구성 + 읽음].
5. **K9-2 W 키는 movement 하나만 바꿨습니다:** `SC109_W_SC108_to_E` 619.59(= 3 × 206.53) → 5209.8 veh/h(U4 F2 1736.6 × 3차로). 맵에서 다른 키는 그대로이도록 코드가 검사합니다(RS:279-280) [읽음; 실행 기록값]. SC109 의 다른 경계 movement 셋은 206.53 계열 그대로입니다.
6. **VISSIM 실측과 비교할 수 있는 것은 23개뿐입니다**(U4 측정 그룹). 차로당 206.53 은 그 그룹 포화류율의 0.105–0.164배, 중앙 0.109배입니다. SC1004 S→W 그룹(66|p2)은 1919.7 veh/h/차로 → 0.108배 [실행; 망 v3b 표].
7. **링크 129(10491 착지 + 10490 미터 접근)와 70(10638 착지 + 10639 미터 접근)은 모형에서 각각 저장고 하나(`in_SC1001_W`, `in_SC1004_W`)에 들어갑니다.** 미터 대기는 그 저장고의 점 대기열로 쌓여 S_eff 를 줄이고, 이것이 진출 포트 방출 상한이 되며, 포트가 차면 FW_W 본선 셀이 막힙니다. **길은 있습니다.** 다만 문턱의 모양이 다릅니다: 모형은 저장고 전체(129 쪽 설정 1,237.8대, 70 쪽 약 285.6대)의 남은 자리가 0 에 가까워야 막히고, VISSIM 기하로는 미터 커넥터 앞 저장(약 45·52대)을 넘은 뒤 착지 지점까지 약 10대(129)·23대(70)면 착지 차로가 막힙니다 [읽음 코드·.inpx; 크기 비교는 추론].

---

## 1. N1 — 206.53 계열이 SC1004 S→W·N→W 서비스까지 들어가는 길

### 1.1 사슬 (file:line)

| 순서 | 위치 | 하는 일 | 태그 |
|---|---|---|---|
| 1 | CFG:7823-7825 | `urban.capacity.per_lane: true`, `equivalent_uniform_veh_h: 330.0`, `perimeter: "all"`. `perimeter_include_boundary_out` 은 없음 → 기본 true(ADP:3874) | [읽음] |
| 2 | RS:400 | `a.install_movement_capacity_by_lanes(cfg, tuning)` 호출. 병합(RS:391) 뒤, 실측 갱신(RS:419) 앞 | [읽음] |
| 3 | ADP:3808-3836 | 내부 movement 184개의 차로(`outputs/movement_lanes_core17legs4b_20260821.json`)로 per_lane = 330 × 184 / Σ차로(294) = **206.53061224489795** | [읽음; 런 기록 `metadata.movement_capacity_by_lanes_per_lane_veh_h` 와 같음 실행] |
| 4 | ADP:3860-3896 | perimeter(`boundary_in/boundary_out/on_ramp/off_ramp`, ADP:1760) 각 movement 에 `caps[m] = per_lane × 차로`. 차로 = `outputs/movement_lanes_perimeter_20260824.json` 값, 없으면 같은 turn 의 해결된 perimeter 중앙값(ADP:3880-3894; left 1·through 2·right 1) | [읽음; 실행 재구성] |
| 5 | RS:401 → ADP:3380-3410 | 게이트발 on-ramp movement 3개만 1,800 veh/h·무신호로 덮음(`gate_onramp_queue_registered = 3`) | [읽음; 실행 기록] |
| 6 | RS:419-420 → ADP:4234-4549 → (head_observation 켜짐, ADP:4434-4439) SHO:114-271 | 실측 하한은 헤드 그룹 단위로 `_distribute_lane_group_capacity_to_movements` 가 나눔. 그 대상 kind = `_LG_KINDS`, 설정에 `lane_group_kinds` 없음 → `{"internal"}`(ADP:4355, :4588-4598). **경계 movement 는 바뀌지 않음** | [읽음; CFG 에 키 0건 실행 grep] |
| 7 | RS:421-424 | K8b-1(SC1002 W 내부 3개), K9-1 W1(SC1001→W_RAMP 3개), K9-2 W(SC109 1개)만 키별로 덮음 | [읽음; 실행 기록] |
| 8 | RS:454-456 → RCC:397, :431-438 | 경로 회랑 진입 회전: 보정값이 없으면 `service = 커넥터 차로 × per_lane`(206.53 이 metadata 로 다시 전달됨) | [읽음] |
| 9 | RS:462 → HSR:161-199 | 물리 헤드 자원 10629(SC1004 E→W 두 movement)만 실측 공유 풀 값(T=1950 2,990.77)으로 덮음 | [읽음; 실행 기록] |
| 10 | RS:538 → LPR:358-362 → LUR:100-128 | SC1004 W 접근 출구 10634·10635·10642 movement 는 lane CTM FD 값으로 덮음 | [읽음] |
| 11 | plant 한 스텝: UFA:579-591 | 램프·오프램프가 아닌 movement: `intended = min(대기, T_u × 녹색비 × cap_flow)`. SA 구성원은 UFA:584-586 에서 표를 읽지 않음 | [읽음] |
| 12 | UQM:730-764 | `cap_flow`: perimeter 는 `min(배분값, ceiling)`, `ceiling = movement_capacity_by_movement_veh_h[m]`(UQM:739, :757). V-A 배분값은 비어 있음(`inflow_outflow_allocation` 0개) → ceiling = 206.53 | [읽음; 실행] |
| 13 | UFA:77-89, :617-618 | 회랑·네이티브 입력·헤드 풀 상한이 위 값을 더 줄일 수만 있음. SC1004 S→W·N→W 는 어느 회랑·풀에도 없음 | [읽음; 실행 재구성] |

- RS:116, :245, :272 의 "206.53" 은 위 사슬을 가리키는 설명문입니다. 숫자는 코드 어디에도 없고(`git grep 206.53` 은 설명문·진단·시험만) 위 3번 계산에서 나옵니다 [실행 grep; 읽음].
- 같은 맵은 추종자 국소 모형도 읽습니다(`vendor/NumSim-mine/src/controllers/local_signal_plant.py:90` `cap_flow_of = _movement_capacity_flow(...)`). SDMPC 국소 비용이 이 경로를 실제로 쓰는지는 이번에 추적하지 않았습니다 [읽음; LIVE 여부 미확인].

### 1.2 SC1004 S→W·N→W 두 movement

| movement | kind | 현시 | 모형 차로 | 출처 | cap (veh/h) | T=1950 기록 서비스(450 s) | 같은 기록 도착 | 태그 |
|---|---|---|---|---|---|---|---|---|
| SC1004_S_to_W | boundary_in | SC1004_p2 | 1 | perimeter 파일(물리 회전) | 206.53 | 3.4422 대 = 206.53 × 60 s/3600 (p2 20 s × 3) | 121.9 대 | [실행] |
| SC1004_N_SC1003_to_W | boundary_out | SC1004_p1 | 1 | 'right' 중앙값(파일에 없음) | 206.53 | 3.6256 / 3.5339 대 = 206.53 × 63.197 / 61.6 s /3600 | 17.0 대 | [실행] |

- 두 movement 모두 도착이 서비스보다 커서 이 상한에 묶여 있습니다(같은 450 s 기록) [실행].
- 받는 저장고는 `SC1004_W_out`(링크 68, RM_C10681 접근)입니다 [읽음 CFG movement spec].
- VISSIM 실측: U4 그룹 66|p2(SC1004 S, 1차로) 1919.7 veh/h/차로, 녹색 평균 유량 1773.3 → 모형 차로당 206.53 은 0.108배. N 쪽 46|p1 은 U4 에서 '측정 못 함(default)'입니다(대기 칸 0개) [실행 U4 표; 망 v3b]. 같은 V-A v3c3-s31 의 링크 68 유입은 S 쪽 280, N 쪽 328 veh/h(O4:128-129) [읽음 O4].

### 1.3 같은 계열 값을 가진 다른 경계 movement

재구성 방법: 위 4번 규칙을 그대로 다시 계산하고(설정 movement·병합 계획·차로 파일), 뒤 훅이 덮은 키는 같은 결정 JSON 의 기록값으로 바꿨습니다. 목록 = V-A v3c3-s31 T=1950 결정의 서비스 목록(소유 + 비소유 356개) [실행 `n12/tools/n12_caps.py`].

검산 [실행 `n12/tools/n12_validate.py`, `n12/out/n12_validate.txt`]
- 설치 시점 perimeter 수 187·물리 회전으로 확인 66·추정 121 → 런 기록(`movement_capacity_perimeter_count 187`, `…_estimated 121`)과 같음.
- 런이 스스로 기록한 '바꾸기 전' 값 14개(K9-1 W1 3, K9-2 W 1, 경로 회랑 병합 전 용량 10)가 재구성 값과 1e−9 안에서 모두 같음.
- U4 표의 v3b 시절 재생 용량(cap_T1) 57개 중 49개가 같고, 다른 8개는 정확히 뒤에서 덮는 키(게이트 on-ramp 1,800 셋, lane CTM 출구 다섯)입니다.
- v3c3-s41·s43 T=4950 결정도 per_lane 206.53·187·121·목록 356·K9-2 W 619.59→5209.8·게이트 3 이 같습니다. 헤드 풀 10629 값만 실측에 따라 다릅니다(3,347.4 / 3,291.4) [실행].

V-A 최종 목록의 경계 movement 179개 [실행]

| 묶음 | 개수 | plant 가 읽는 곳 | 태그 |
|---|---|---|---|
| 206.53 × k 를 가진 진입·진출, plant 가 읽음 | **148**(boundary_in 104, boundary_out 44) | 일반 정지선 루프 UFA:579-591 146개, 경로 회랑 예산 RCC:691-709 2개(SC1004_S_to_E_SC1005 무신호라 녹색비 1 → 450 s 내내 206.53, SC107_S_to_W_SC1005 3차로 619.59) | [실행; 읽음] |
| 206.53 × k, plant 가 읽지 않음: SA 구성원 | 3(SC1001_W_to_E_SC1002·S_SC1003·N_SC2002) | SA 차로 FIFO 의 차로 포화류율 2,030.9 / 1,581.7 / 2,101.9(UFA:584-586) | [읽음; 실행] |
| 206.53 × k, plant 가 읽지 않음: off_ramp movement | 14(SC1001 offW/offE 8, SC1004 offW/offE 6) | 일반 루프는 off_ramp 를 건너뜀(UFA:582-583). 진출 포트 8개는 SA·local_upstream·direct 길만 쓰고 movement 용량을 읽지 않음(LOR:46-64, LPR:378-387, SA:782-783). LOR:65-77 의 movement 길은 이 배치에서 쓰이지 않음 | [읽음; 쓰이지 않음은 설치 코드 추론] |
| 206.53 계열이 아님 | 11 | K9-1 W1 3(3,454.2·917.0·1,732.4), K9-2 W 1(5,209.8), 헤드 풀 10629 2(2,990.77, 공유), lane CTM 출구 5(값은 기록 안 됨; v3b 시절 U4 cap_T1 은 4,747.45·3,164.97·1,582.48) | [실행] |
| 게이트 on-ramp 3(SC1001_W_to_onE·onW, SC1004_W_to_onE) | (위 179 안, 206.53 아님) | 1,800 veh/h·무신호(ADP:3380-3410). onW 기록 서비스 217.5 대/450 s(1,800 상한 225 대) | [읽음; 실행] |

- 148개의 차로 출처: 물리 회전 확인 62, turn 중앙값 추정 86. 차로수 k: 1차로 93·2차로 45·3차로 5·4차로 5 [실행].
- 신호별 개수(148): SC1 12, SC1004 7, SC1005 2, SC101 3, SC102 6, SC103 10, SC104 10, SC105 3, SC106 13, SC107 6, SC108 7, SC109 3, SC11 6, SC12 6, SC16 12, SC2001 12, SC2002 6, SC2003 4, SC2004 6, SC2005 6, SC5 3, SC6 3, SC7 2 [실행]. 이름 전체는 부록 A, 행별 값은 `n12/out/n12_caps.csv`.
- 묶여 있는지 [실행, T=1950 기록 하나]: 148개 중 37개는 서비스 0. 제어 현시의 25개는 서비스 = 206.53 × k × (3 × 지금 녹색)/3600 이 10 % 안(또는 무신호 450 s)이라 이 상한에 묶인 모양입니다. 나머지 86개 중 67개는 이 결정의 녹색 명령이 없는 고정 신호 교차로(SC102·103·104·106·2001–2005)이고, 그중 36개는 역산 녹색 합이 정수 초(예 159·177·195·201 s)라 고정 신호 녹색에서 상한에 묶인 것으로 보입니다. 남은 19개는 제어 현시인데 10 % 밖입니다(도착이 상한보다 작거나 블록마다 녹색이 다름) [실행 셈; 해석은 추론, 고정 신호 시간표는 대조 안 함].
- J1_CAVEAT.md:24 의 "경계 movement 169개"(K9-1 J1 기준, LGK 분석)와 셈 범위가 다릅니다. 여기 165개는 K9-2 W 로 하나가 빠진 뒤, off_ramp 를 포함한 V-A 최종 목록 기준입니다. 같은 셈법인지는 확인하지 않았습니다 [읽음 자료로만; 추론].

VISSIM 실측(U4, v3b 망·무제어 5시드)이 있는 23개 [실행 `n12_caps.csv` 의 `u4_*` 열]

| 그룹(정지선 링크\|현시) | 차로 | 포화류율 veh/h/차로 | 206.53 / 포화 | 이 그룹의 206.53 계열 movement(모형 차로) |
|---|---|---|---|---|
| 1220008201\|p3 (SC1 E) | 2 | 1876.0 | 0.110 | E_to_N_SC101(1), E_to_S_SC107(1), E_to_W_SC105(2) |
| 66\|p1 (SC1004 S) | 3 | 1888.3 | 0.109 | S_to_E_SC1005(1, 회랑), S_to_N_SC1003(3) |
| 66\|p2 (SC1004 S) | 1 | 1919.7 | 0.108 | S_to_W(1) |
| 1220043200\|p2 (SC107 N) | 2 | 1260.0 | 0.164 | N_SC1_to_S(2) |
| 382\|p2 (SC107 S) | 3 | 1423.9 | 0.145 | S_to_E_SC108(1), S_to_W_SC1005(3, 회랑) |
| 1220000201\|p3 (SC107 W) | 4 | 1960.8 | 0.105 | W_SC1004_to_S(1), W_SC1005_to_S(1) |
| 1220007401\|p1 (SC108 N) | 2 | 1941.3 | 0.106 | N_SC7_to_S(2) |
| 1220044500\|p1 (SC108 S) | 2 | 1724.6 | 0.120 | S_to_E_SC109(1), S_to_N_SC7(2), S_to_W_SC107(1) |
| 178\|p3 (SC108 W) | 4 | 1905.4 | 0.108 | W_SC107_to_S(1) |
| 1210008303\|p3 (SC11 W) | 2 | 1958.7 | 0.105 | W_to_E_SC12(2), W_to_N_SC5(1), W_to_S_SC7(1) |
| 1220011200\|p3 (SC16 E) | 1 | 1890.3 | 0.109 | E_to_N_SC12(1), E_to_S_SC109(1), E_to_W_SC7(1) |
| 1210009700\|p3 (SC16 W) | 1 | 1461.2 | 0.141 | W_SC7_to_E(2) |

- U4 에 그룹은 있으나 측정 못 한(default) 것 11개: SC1004 E_SC1005/E_SC107_to_S(52|p4), N_SC1003_to_S·to_W(46|p1), SC107_E_SC108_to_S, SC108_E_SC109_to_S, SC109 E_to_N_SC16·E_to_W_SC108(1220000704|p3), SC109_N_SC16_to_E, SC16_N_SC12_to_E, SC16_S_SC109_to_E [실행].
- 나머지 114개는 U4 헤드 그룹에 없습니다(고유 헤드가 없거나 고정 신호 교차로). 이들의 VISSIM 방류율은 기존 FZP 파생 표에서 찾지 못했습니다 [실행 대조; 열림].
- U4 는 v3b 망 자료입니다. 표 머리에 헤드·커넥터·신호기가 무제어 적합 5시드 망에서 같다고 적혀 있습니다. v3c3 에서 헤드가 같은지는 이번에 대조하지 않았습니다 [읽음; 미확인].

### 1.4 K9-2 W 키가 SC109 에 바꾼 것

- 키: `urban.sc109w_through_saturation`(CFG:7981), 증거 `diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json`(evidence_sha256 `b4b7294d…1712`), 훅 RS:236-286, 호출 RS:423-424(per_lane 를 metadata 로 받음) [읽음].
- 바뀐 것: `SC109_W_SC108_to_E`(boundary_out, SC109_p3, 출발 SC108_to_SC109) 619.59 = 3 × 206.53 → 5209.8 = U4 `173|p3` 의 `s_from_green_start_incl_startup` 1736.6 × 3차로 [실행 기록 `metadata.k92_w`].
- 검사(RS:264-281): 차로당 ≤ 2,000(A1), 같은 물리 그룹 합 ≤ 차로 × 2,000(A2), 바꾸기 전 값 = 차로 × per_lane(A5, "the 206.53 path"), movement spec 일치(A6), **맵에서 이 키 하나만 다름**(A7) [읽음].
- 짝 키 H-b `urban.capacity.head_floor_seed`(CFG:7853, SHO:280-329)는 W 키가 있어야 켜집니다(SHO:296-297). 이것은 내부 movement `SC109_W_SC108_to_N_SC16`(그룹 173|p4)의 헤드 하한을 max(규칙값, 1045.16)로 올립니다(SHO:209-215, :258-260; 설치 때 기준값 413.06) [읽음; 실행 기록 `metadata.k92_hb`]. 경계 movement 는 바꾸지 않습니다.
- SC109 에 남은 206.53 계열 경계 movement: E_to_N_SC16(1차로 206.53), E_to_W_SC108(4차로 826.12), N_SC16_to_E(3차로 619.59). 셋 다 U4 default 그룹입니다 [실행].

### 1.5 206.53 이 movement 표 밖에서 쓰이는 곳(값은 이번에 세지 않음)

- 경로 회랑 분기 서비스: `service = per_lane × 분기 커넥터 차로`(RCC:871; 네이티브 보정값이 있으면 그것, RCC:873-876, :884). 회랑 넷(1129 SC1004 E, 1128, 1099, 1100) [읽음].
- 네이티브 입력 첫 헤드 예산: `녹색비 × T_u × 헤드 차로 × cap_flow(기준 좌회전 movement)`(NIP:101-105, :266-268). 입력 1093 의 기준은 내부 movement `SC11_E_SC12_to_S_SC7`, 헤드 차로 2 [읽음; 실행 기록]. 내부 movement 라 헤드 하한으로 올라갔을 수 있습니다 [추론].
- 진출 포트(SA 두 포트, 10638 local_upstream, direct 넷)의 방출 서비스는 206.53 이 아니라 `movement_capacity_veh_h`(= 1,400, `evaluation/parameters.json:55`) × 커넥터 차로입니다(LOR:53, :62; SA:1471). 10-01 기록의 "10491 배수 206.53 계열"은 c20aff1d 의 이 배치에서는 쓰이지 않는 길(LOR:65-77)입니다 [읽음; 기억 파일은 자료로만].

---

## 2. N2 — 링크 129·70 의 plant 표현

### 2.1 VISSIM 기하 (v3c3 .inpx, sha256 `3de889f0…2e`, 동결본 읽기만) [실행]

| 링크 | 길이·차로 | 들어옴 | 나감 |
|---|---|---|---|
| 129 | 301.9 m, 3차로 | 10778(32 에서, 3차로, 0 m), **10491**(FW_W 진출, 1차로 → 129 차로 1, **239.38 m**) | **10490**(FW_E 미터, 1차로, 129 차로 1 의 **299.99 m** 에서, 길이 368.4 m, 헤드 272.6 m), 10777(3차로 → 127, 301.93 m) |
| 70 | 180.5 m, 2차로 | 10637(69 에서 shared_69 분기, 2차로, 1.99 m), **10638**(FW_W 진출, 2차로 → 70 차로 1–2, **40.27 m**) | **10639**(FW_E 미터, 1차로, 70 차로 1 의 **180.14 m** 에서, 길이 408.5 m, 헤드 314.8 m), 10776(2차로 → 126, 180.55 m) |

- 착지와 미터 출발 사이 같은 차로 거리: 129 는 60.6 m(6 m 간격으로 약 10대), 70 은 139.9 m(약 23대). 미터 커넥터 헤드 앞 저장은 10490 약 45대, 10639 약 52대(헤드 위치 × 1차로 / 6 m; 6 m = `evaluation/parameters.json` `urban_avg_vehicle_length_m`) [실행 산술; 차량 간격 6 m 가정은 추론].
- 기존 분할 표(V-A v3c3-s31 전체 런, `o1o4/vnext/out/split_va_s31.json`, VERIFY_NEXT 가 만든 표) [실행 읽기]
  - 129: 32→129 1,976대, 10491→129 1,555대 / 129→10490 1,415대, 129→127 2,121대, 129→10777 22대.
  - 70: 10637→70 905대, 10638→70 1,549대 / 70→10639 905대, 70→126 1,544대, 70→10776 5대.
  - 이 표는 차량 번호가 없어 출처별 출구를 가를 수 없습니다. 70 은 905 = 905, 1,549 ≈ 1,544 + 5 라 "10637 → 10639, 10638 → 126" 로 보입니다 [추론]. 129 는 가를 수 없습니다 [열림].

### 2.2 링크 129 — 모형

| 구성 | 모형 표현 | 위치 | 태그 |
|---|---|---|---|
| 저장고 | 32·10778·129·10777·127 이 저장고 하나 `in_SC1001_W`(설정 1,237.8대). SA 가 127 의 3차로만 FIFO 로 색인(저장 81 / 63 / 103.6대, `observed_full`) | CFG `urban_link_storage_veh`, SA:1-10, :337-449, 기록 `stopline_approach_storage_veh` | [읽음; 실행 기록] |
| 10491 착지(FW_W 진출 OR_D_W) | 포트 저장고 `OR_D_W_storage` 38.58대(DelayedPort). 방출은 SA 경로: `approach` 표시(SA:782-783) → LOR:56-59 → SA:1464-1506. 서비스 1,400 × 1차로, 127 차로별 빈자리(지퍼, 10481 과 공유), 그리고 **S_eff(in_SC1001_W)** 로 막음(SA:1487-1489) | LPR:378-391, LOR:46-59, :79, SA:116-118 | [읽음; 실행 기록 `physical_branch_projection_capacity`] |
| 10491 차량의 목적지 | 127 의 E/S/N 세 정지선 movement 로만. 그 밖으로 가는 오프램프 β 는 0 이어야 함(SA:692-696) → **모형에서 10491 → 10490 흐름은 0** | SA:678-709(:692-696), :1517-1578 | [읽음] |
| 10490 미터 대기 | 램프 저장고 = 커넥터 10490(PhysicalRampBoundary, 헤드 앞 칸 = 헤드위치 × 차로 / 간격, PRBD:360-375; 램프 저장 61.96대, PRB:131, :207). 공급원은 movement `SC1001_W_to_onE`(TOPO `movement_receivers`, PRB:213-215; 출발지 `in_SC1001_W`, 1,800 veh/h 무신호) | LRR:67-72, :184-191 | [읽음; 실행 산술] |
| 미터가 막을 때 | UFA:521-543: 램프 빈자리로 요청을 줄이고(:527-528), 못 간 몫은 `SC1001_W_to_onE` 대기열에 남음(:543). MSP:1-8 도 "upstream feeder stock 에 남는다" | UFA:509-555, MSP:1-30 | [읽음] |
| 대기열이 129 를 차지하는가 | 점 대기열이라 차로·위치가 없음. 상한 없음(UQM:661-667, 1e9). 출발지 `in_SC1001_W` 가 저장고 목록에 있으므로 S_eff(in_SC1001_W) 에서 빠짐(UQM:210-229, :231-256) | UQM | [읽음] |
| FW_W 로 번지는가 | S_eff(in_SC1001_W) → 10491 포트 상한(SA:1487-1489) → 포트가 차면 받을 자리 = 포트 빈자리(LOR:138-146) → 본선 오프램프 흐름 `min(수요, 자리)`, 못 간 몫은 셀에 남고 셀 속도 상한(AFA:322-354). plant 매니페스트가 `lane_groups: false`(`diagnostics/sdmpc_n31_20260924/plant_n31_v2.json`)라 두 방향 모두 차로 그룹 없는 집계 모형이고(`evaluation/controllers/lane_freeway_runtime.py:36-38, :65`), 상한이 단면 전체에 걸림 | LOR, AFA, `diagnostics/sdmpc_n31_20260924/plant_n31_v2.json` | [읽음] |

정리 [추론]
- 한 저장고인가: **그렇습니다.** 10491 착지 차량(127 차로로 가는 이동 묶음)과 10490 대기(`SC1001_W_to_onE` 점 대기열)는 모두 `in_SC1001_W` 안입니다.
- 미터 대기가 FW_W 진출·본선으로 번질 수 있는가: **길은 있습니다**(위 표 마지막 줄). 그러나 10490 대기는 127 차로 빈자리를 줄이지 않고, 저장고 전체 S_eff 만 줄입니다. 그래서 저장고 전체(설정 1,237.8대: 32 의 1 km 3차로 포함)의 남은 자리가 거의 0 이 되어야 10491 이 막힙니다. VISSIM 에서는 10490 대기가 커넥터 앞 칸(약 45대)을 넘어 129 차로 1 로 약 10대 더 쌓이면 10491 착지(239 m)에 닿습니다. 모형에는 이 '차로 1 국소 문턱'이 없습니다. 모형 쪽 남은 자리가 실제로 몇 대인지는 상태마다 다릅니다(열린 질문 6).
- V-A 에서는 미터가 늘 g10 이어서 이 길이 쓰인 기록은 없습니다. O1 의 v3c3-s41 규칙 RM 사슬(10490 g2–6 → 10491 재고 2.3–2.8배 → 1099 미삽입 +644.6)은 VISSIM 에서만 본 것이고, 모형이 같은 상태에서 무엇을 예측하는지는 재생 없이 알 수 없습니다 [열림].

### 2.3 링크 70 — 모형

| 구성 | 모형 표현 | 위치 | 태그 |
|---|---|---|---|
| 저장고 | lane plant 가 `in_SC1004_W` 를 70·10776·10640·10637 기하로 다시 만듦: Σ 길이 × 차로 / 6 m ≈ 285.6대(설정 681.2 를 대체). 126·71 등 국소 도로는 lane CTM 저장고로 빠짐 | LPR:718-738, :358-367 | [읽음; 실행 산술] |
| 10638 착지(FW_W 진출 OR_F_W) | 포트 `OR_F_W_storage` 96.05대. `local_upstream`(LPR:387) → LOR:51-55: 대상 = `in_SC1004_W`(LUR:93), 서비스 1,400 × 2차로, **자리 = S_eff(in_SC1004_W)** | LOR:51-55, :107-109 | [읽음; 실행 기록] |
| 10638 차량의 목적지 | `schedule_upstream(entry='off10638')` → 결정 1140 의 relFlow 로 국소 출구 셋(10634·10635·10642)에만 나눔(LPR:746-760). 미터행 `SC1004_W_to_onE` 는 1134:3(10637 쪽)에서만 옴(LPR:720-722, :772-773) → **모형에서 10638 → 10639 흐름은 0** | LUR:130-151, LPR:746-781 | [읽음] |
| 10639 미터 대기 | 램프 저장고 = 커넥터 10639(램프 저장 68.7대, 헤드 앞 약 52대). 공급원 `SC1004_W_to_onE`(출발지 `in_SC1004_W`, 1,800 veh/h 무신호). 막히면 그 대기열에 남음(UFA:543) | TOPO, PRB:213-215, UFA:521-543 | [읽음] |
| FW_W 로 번지는가 | `SC1004_W_to_onE` 대기 → S_eff(in_SC1004_W) ↓ → 10638 포트 자리 ↓(LOR:54) → 포트 96.05대가 차면 → AFA:322-354 로 FW_W 셀 막힘 | 같은 사슬 | [읽음] |

정리 [추론]
- 한 저장고인가: **그렇습니다**(`in_SC1004_W`). 국소 출구 셋의 준비 대기열(lane CTM 입장 전)도 같은 S_eff 를 줄입니다(LUR:154-163 `consume_upstream` → movement 대기열, :160).
- 번지는 문턱: 모형은 약 285.6대 저장고(10640 처럼 70 밖의 도로 포함)의 남은 자리, VISSIM 은 10639 커넥터 앞 칸(약 52대)을 넘어 70 차로 1 로 약 23대. 129 보다 차이가 작지만 여전히 차로 위치가 없습니다.

### 2.4 두 링크 한 표

| | 129 | 70 |
|---|---|---|
| 모형 저장고 | `in_SC1001_W` 1,237.8대(설정) | `in_SC1004_W` 약 285.6대(lane plant 재구성) |
| 진출 포트 | 10491 → `OR_D_W_storage` 38.58대, SA 지퍼(10481 과 공유) | 10638 → `OR_F_W_storage` 96.05대, local_upstream |
| 포트 방출 상한 | min(1,400 × 1차로, 127 차로 빈자리, S_eff) | min(1,400 × 2차로, S_eff) |
| 진출 차량 → 반대 방향 미터 | 0(SA:692-696) | 0(결정 1140 분할) |
| 미터 공급 movement | `SC1001_W_to_onE` → RM_C10490, 1,800 무신호 | `SC1004_W_to_onE` → RM_C10639, 1,800 무신호 |
| 미터 대기 → 진출 차단 | S_eff 경유, 저장고 전체가 찰 때 | S_eff 경유, 저장고 전체가 찰 때 |
| VISSIM 기하 문턱(추론) | 커넥터 약 45대 + 129 차로 1 약 10대 | 커넥터 약 52대 + 70 차로 1 약 23대 |
| 진출 차단 → 본선 | AFA:322-354 셀 속도 상한(FW_W 집계, 단면 전체) | 같음 |

- 124(10483 착지 + 10480 미터)·121(10682 착지 + 10646 미터)은 direct 진출 커넥터라 LOR:60-64 의 다른 길(대상 = `offramp_direct_tail_by_offramp`, 서비스 1,400 × 차로)입니다. 기록에는 `SC1001_W_tail` 655.2대·`SC1004_W_tail` 1,150.3대 저장고가 있으나 어느 진출이 어느 꼬리로 가는지와 미터 대기와의 결합은 이번에 추적하지 않았습니다 [읽음 코드·기록; 대응은 미확인].

---

## 3. 열린 질문

1. 114개 경계 movement(U4 그룹 밖)와 default 11개의 VISSIM 방류율. 기존 FZP 파생 표에 없습니다. 새 FZP 스캔이 필요합니다(이번 범위 밖).
2. U4(v3b) 헤드 그룹이 v3c3 망에서 같은지 대조하지 않았습니다.
3. 경로 회랑 분기 서비스(RCC:871)·네이티브 입력 예산(NIP:268)의 실제 206.53 계열 값과 그것이 묶이는지.
4. lane CTM 출구 다섯의 c20aff1d 값(기록 없음; v3b U4 cap_T1 만 있음).
5. 129 의 출처별 출구(32 쪽 대 10491 쪽 → 10490). 차량 번호가 있는 표가 없습니다. 모형은 10491 → 10490 을 0 으로 둡니다.
6. 모형 S_eff(in_SC1001_W)·S_eff(in_SC1004_W) 가 실제로 몇 대까지 내려가는지(결정 JSON 에 저장고 값이 직접 없음). 미터 조임 상태에서 이 길이 켜지는지는 재생(P1 류, 승인 필요) 없이 알 수 없습니다.
7. 추종자 국소 모형(local_signal_plant.py:90)이 SDMPC-31 에서 LIVE 인지.
8. J1_CAVEAT "169개"와 이 문서 165·148개의 셈법 차이.

---

## 4. 산출과 sha256 [실행]

| 파일 | sha256 |
|---|---|
| `r2c_n/n12/tools/n12_caps.py` | d38a032ef4a38bc4b9c815882d2bd55a78d257c9aa8c4925de43cca49eb2a309 |
| `r2c_n/n12/tools/n12_validate.py` | 64c17a4eafc5a7c9387c97d4d020175ec2c632316e807028c5e972d45a6b680e |
| `r2c_n/n12/out/n12_caps.json` | cfda10d41edb5d196056faa3b387a3e555c0cd4c25d95ec59e6c20ebe8da87de |
| `r2c_n/n12/out/n12_caps.csv` | 73400afbe0abe95260a6ded153fd1aa1677bebe3f5cb3f208e032b099793544d |
| `r2c_n/n12/out/n12_validate.txt` | cd55bf43b5c2461f30ea52f520be9f9a3c69f3820f5a636e84fdaa39ce356860 |
| `r2c_n/n12/out/n12_family_by_signal.txt` | 6003d439a989c198971e0901380b2f776b26d17afa5c09c827b686dd1d47d985 |

입력
- 결정 JSON `D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/decisions_sdmpc31_v3c3_k92va_s31/action_001950.json` sha256 fd5763de017891f26271cfeec01b1d9333601b3a3fae154d0fb96eedabdf555e(v3c3-s31). 대조: 같은 폴더 구조의 v3c3-s41·s43 `action_004950.json`(metadata 만 읽음).
- U4 표 sha256 22384c00313a0104a9febf5344914acd15f20058a0a62fe91d2bc085dcbb292b.
- `git show c20aff1d:` 로 뽑은 JSON(`n12/src/`): config_n31_v2 c8e3ee2c…1866, movement_lanes_core17legs4b 090f01c7…3c44, movement_lanes_perimeter 5fd8d84b…8115, movement_merge_plan a2788ab2…e06, sc1001eb_evidence 05c821f6…305a, topology_routes_v2_8ac6fd 089238ed…36b4, boundary_out_ramp_split_20260905_measured 927d0ba4…6437.
- `.inpx` `D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx` sha256 3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e(읽기만).
- 분할 표 `rmcause/o1o4/vnext/out/split_va_s31.json`(VERIFY_NEXT 산출, 읽기만).

---

## 부록 A. plant 가 읽는 206.53 계열 경계 movement 148개 (신호: 이름 뒤쪽(i=진입·o=진출, 모형 차로))

SC1 [12]: E_to_N_SC101(i,1), E_to_S_SC107(i,1), E_to_W_SC105(i,2), N_to_E_SC11(i,1), N_to_S_SC107(i,2), N_to_W_SC105(i,1), S_to_E_SC11(i,1), S_to_N_SC101(i,2), S_to_W_SC105(i,1), W_to_E_SC11(i,2), W_to_N_SC101(i,1), W_to_S_SC107(i,1)
SC1004 [7]: E_SC1005_to_S(o,1), E_SC107_to_S(o,1), N_SC1003_to_S(o,2), N_SC1003_to_W(o,1), S_to_E_SC1005(i,1), S_to_N_SC1003(i,3), S_to_W(i,1)
SC1005 [2]: W_to_E_SC107(i,2), W_to_N_SC105(i,1)
SC101 [3]: S_to_E_SC5(i,1), S_to_N_SC2005(i,2), S_to_W_SC1002(i,1)
SC102 [6]: E_SC103_to_N(o,1), N_to_E_SC103(i,1), N_to_S_SC5(i,2), N_to_W_SC2005(i,1), S_SC5_to_N(o,2), W_SC2005_to_N(o,1)
SC103 [10]: E_to_N(i,1), E_to_S_SC6(i,1), E_to_W_SC102(i,4), N_to_E(i,1), N_to_S_SC6(i,3), N_to_W_SC102(i,1), S_SC6_to_E(o,1), S_SC6_to_N(o,2), W_SC102_to_E(o,2), W_SC102_to_N(o,1)
SC104 [10]: E_to_N(i,1), E_to_S_SC106(i,2), E_to_W_SC6(i,4), N_to_E(i,2), N_to_S_SC106(i,4), N_to_W_SC6(i,1), S_SC106_to_E(o,1), S_SC106_to_N(o,2), W_SC6_to_E(o,2), W_SC6_to_N(o,1)
SC105 [3]: E_to_N_SC1002(i,1), E_to_S_SC1005(i,1), E_to_W_SC1003(i,2)
SC106 [13]: E_to_N_SC104(i,1), E_to_S(i,1), E_to_W_SC12(i,2), N_SC104_to_E(o,1), N_SC104_to_S(o,2), S_to_E(i,1), S_to_N_SC104(i,4), S_to_W_SC12(i,1), W_SC12_to_E(o,2), W_SC12_to_S(o,1), W_to_E(i,2), W_to_N_SC104(i,1), W_to_S(i,1)
SC107 [6]: E_SC108_to_S(o,2), N_SC1_to_S(o,2), S_to_E_SC108(i,1), S_to_W_SC1005(i,3), W_SC1004_to_S(o,1), W_SC1005_to_S(o,1)
SC108 [7]: E_SC109_to_S(o,1), N_SC7_to_S(o,2), S_to_E_SC109(i,1), S_to_N_SC7(i,2), S_to_W_SC107(i,1), W_SC107_to_S(o,1), W_to_E_SC109(i,2)
SC109 [3]: E_to_N_SC16(i,1), E_to_W_SC108(i,4), N_SC16_to_E(o,3)
SC11 [6]: E_to_N_SC5(i,1), E_to_S_SC7(i,1), E_to_W_SC1(i,2), W_to_E_SC12(i,2), W_to_N_SC5(i,1), W_to_S_SC7(i,1)
SC12 [6]: E_to_N_SC6(i,1), E_to_S_SC16(i,1), E_to_W_SC11(i,2), W_to_E_SC106(i,2), W_to_N_SC6(i,1), W_to_S_SC16(i,1)
SC16 [12]: E_to_N_SC12(i,1), E_to_S_SC109(i,1), E_to_W_SC7(i,1), N_SC12_to_E(o,1), S_SC109_to_E(o,1), S_to_E(i,1), S_to_N_SC12(i,2), S_to_W_SC7(i,1), W_SC7_to_E(o,2), W_to_E(i,2), W_to_N_SC12(i,1), W_to_S_SC109(i,1)
SC2001 [12]: E_SC2002_to_N(o,1), E_SC2002_to_S(o,1), E_SC2002_to_W(o,2), N_to_E_SC2002(i,1), N_to_S(i,2), N_to_W(i,1), S_to_E_SC2002(i,1), S_to_N(i,2), S_to_W(i,1), W_to_E_SC2002(i,2), W_to_N(i,1), W_to_S(i,1)
SC2002 [6]: E_SC2003_to_N(o,1), N_to_E_SC2003(i,1), N_to_S_SC1001(i,2), N_to_W_SC2001(i,1), S_SC1001_to_N(o,2), W_SC2001_to_N(o,1)
SC2003 [4]: E_SC2004_to_N(o,1), N_to_E_SC2004(i,2), N_to_W_SC2002(i,1), W_SC2002_to_N(o,2)
SC2004 [6]: E_SC2005_to_N(o,1), N_to_E_SC2005(i,1), N_to_S_SC1002(i,2), N_to_W_SC2003(i,1), S_SC1002_to_N(o,2), W_SC2003_to_N(o,1)
SC2005 [6]: E_SC102_to_N(o,1), N_to_E_SC102(i,1), N_to_S_SC101(i,2), N_to_W_SC2004(i,1), S_SC101_to_N(o,3), W_SC2004_to_N(o,1)
SC5 [3]: S_to_E_SC6(i,1), S_to_N_SC102(i,2), S_to_W_SC101(i,1)
SC6 [3]: S_to_E_SC104(i,1), S_to_N_SC103(i,2), S_to_W_SC5(i,1)
SC7 [2]: E_to_N_SC11(i,1), E_to_S_SC108(i,1)
