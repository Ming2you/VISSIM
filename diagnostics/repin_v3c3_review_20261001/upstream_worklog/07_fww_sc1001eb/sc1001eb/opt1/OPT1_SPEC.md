# OPT1_SPEC — SC1001 EB 정지선 결합 항목, 안 1(구조형) 구현 명세

- 작성 2026-10-01. 사용자 결정(2026-10-01): SC1001 EB 결합 항목 = **안 1(구조형)**. 나머지 결정은 선택지 문서의 권고값입니다(§1 표).
- 이 문서는 **명세**입니다. 코드·config·커밋·VISSIM은 건드리지 않았습니다. 쓴 곳은 `<O>`뿐입니다.
- 표기: [실행] 이번에 명령으로 확인(산출물 있음) / [읽음] 코드·문서 확인 / [계산] 입력을 밝힌 산술 / [추론] 시험하지 않은 판단
- 경로
  - `<E>` = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/sc1001eb`, `<O>` = `<E>/opt1`, `<P>` = `<O>/probe`
  - `<K6>` = `D:/VISSIM-merge/sim3-n31-v3c3-k6gate` (detached 54d821c). **줄 번호는 모두 이 트리 기준**입니다.
  - `<K>` = `D:/VISSIM-merge/sim3-n31-v3c3` (K7 커밋 진행 중, HEAD 69f44ef; 읽기만)
  - `<T>` = 같은 scratchpad의 `termcost`, `<F2>` = `<E>/f2`
- 코드 약어(`<K6>` 기준): LOR `evaluation/controllers/lane_offramp_runtime.py`, UFA `…/urban_flow_accounting.py`, LPR `…/lane_plant_runtime.py`, RS `…/runtime_setup.py`, AR `…/area_runtime.py`, CAO `…/control_area_objective.py`, LC `…/lane_coupling.py`, PRB `…/physical_ramp_branches.py`, LSS `…/local_signal_service.py`, HSR `…/head_service_resources.py`, ADP `…/vissim_stackelberg_adapter.py`, UQM `vendor/NumSim-mine/src/models/urban_queue_model.py`, CH `diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py`, VBS `scripts/run_real_world_stackelberg_controller.vbs`. 새 모듈은 **SA** `evaluation/controllers/stopline_approach.py`.

## 요약

1. **구조**: 포트(10491·10481)는 커넥터만 맡고, 커넥터를 지난 차량을 거리/속도 지연 뒤 **W 정지선 movement 큐**(`SC1001_W_to_{E,S,N}`)로 보냅니다. 그 큐가 곧 link 127 차로군 저장입니다(1-a, 그래프 불변). 차로군 SG2 = {E, S}(차로 1–2, p3), SG5 = {N}(차로 3, p4)에 예산 s_g·n_g·T·φ_g와 저장 상한 S_g를 둡니다. 포트 방출은 커넥터 FIFO `min_g(여유_g/β_g)`와 10481 지점 지퍼로 정합니다. 그래서 차로군이 차면 10491이 차고, 그다음 기존 LC→AFA 경로로 FW_W 진출이 막힙니다(사건이 내생).
2. **바뀌는 코드**: 새 모듈 SA 하나와 다섯 곳의 짧은 분기입니다. LOR 접근 분기(LOR:49-58 옆), UFA 도착 분할(UFA:363 앞)과 차로군 예산(UFA:547과 :549 사이), RS 두 줄(RS:185 뒤, RS:253 뒤), ADP 차로별 걷기 분리(ADP:5382-5459)입니다. **LPR·UQM·AR·CAO·LC는 바꾸지 않습니다.**
3. **127 관측 귀속(1/14) 수정**은 ADP 루프(ADP:6459-6538)를 고치지 않습니다. 투영이 남긴 출처 기록(`physical_stock_assignment_by_link["127"]`)을 SA.initialize가 되돌리고 차로대로 다시 배정합니다. LPR `move_link`(LPR:308-328)와 같은 방식입니다. 그래야 배포 경로와 하네스가 **같은 함수**를 부릅니다.
4. **키 없음 = 비트 동일**: 모든 분기는 `urban.stopline_approach`가 있을 때만 생기는 `cfg.network.stopline_approach`에 묶입니다. 키가 없으면 새 속성·새 진단 키·새 import·새 부동소수 연산이 하나도 없습니다(§9). ADP 분리는 합산 순서를 지켜 비트 동일함을 시험으로 고정합니다.
5. **K3 서비스 표와의 관계**: 미터 서비스 표(LPR:508-516)는 건드리지 않습니다. 다만 127 잔차의 가짜 램프 몫(게이트 β 0.85)이 사라지므로 RM_C10482·RM_C10490 큐 입력이 달라집니다. 표와 격자는 그대로입니다(§8).
6. **사용자 질문("왜 6–8일? 이미 있는 FZP로 하면 안 되나?")**: FZP로 됩니다. 추정기 재계산과 섬(island) 판정을 기존 FZP 5시드에서 합니다. 섬 판정은 FZP 상태에서 배포 LOR·UFA·SA를 돌리는 하네스로 하며, 사건 상태 14개·비사건 31개가 이미 있습니다. 다시드 R-obs VISSIM 런은 필요 없습니다. 실측한 잡 시간으로 다시 세면 에이전트 작업은 **직렬 약 1.5–2일**, 하네스 잡 3개를 병렬로 돌리면 **약 1일**입니다(`OPT1_PREDECLARATION.md` §7). 6–8일은 사람 작업일 기준에 다시드 R-obs 런을 전제한 값이었습니다.

---

## 0. 기준 트리와 줄 번호 [실행·읽음]

- `<K6>`과 `<K>` 작업 트리를 `cmp`로 비교했습니다. LOR·UFA·LPR·SB·AFA·LUR·OP·RS·AR·UQM·PRB·LSS·LC·HSR은 **바이트 동일**하고, ADP만 다릅니다.
- ADP의 K7 변경은 β 원천 이름(`routing_v3c1*` → `routing_v3c3*`)뿐입니다. 그 결과 **약 4003행 뒤의 줄 번호가 +2** 밀립니다. 예: `_contiguous_stopline_queue` 5382 → 5384, 귀속 루프 6459 → 6461, `seed_urban_arrival_buffer` 10024 → 10026 [실행 grep].
- 구현은 D-EB-13대로 **K7 커밋 확정 뒤 그 HEAD에서 만든 별도 워크트리**에서 합니다. 아래 줄 번호는 K6 기준이므로 ADP는 +2로 읽으면 됩니다.

## 1. 결정 반영

| 결정 | 이 명세에서 | 근거 |
|---|---|---|
| D-EB-1 안 1 | 저장 상한·커넥터 FIFO·사건 내생을 포함한 한 번 구현. 안 2(값 수준)는 만들지 않음 | 사용자 결정 |
| D-EB-2 U8 방향 | 모형 쪽(u8b형): 포트가 W 정지선 접근으로 방출. **U8 2차 판정은 아직 없습니다**(`urban-b2/diag_c3_r2/u8/run/chain.log` 16:11 기준 `CAP_c3sgsu7abu8b_T8700`까지 포착만 함, U8 결과 문서 없음). 그래서 충돌은 없고, u8a를 지지하는 판정이 나오면 다시 봅니다 | [실행 ls·tail] |
| D-EB-3 | 1-a. 그래프·movement 집합 불변 | |
| D-EB-4 | E1 승인. v3c3 핀에서 재계산(G-EB-0). 127행 s는 이 항목이 소유하고, C3 v2 F2 표에서는 127\|p3·127\|p4 행을 뺌 | F1 §3 |
| D-EB-5 | S_g = 기하(6.0 m). 129 꼬리 = 도시 게이트 저장(in_SC1001_W) 소유이고, off-ramp 출신(경로 1132:2)은 "포트 방출 진행 중" 꼬리표를 담. 10481 합류 = **지퍼 1:1**(VISSIM "127 @210.3 지퍼 합류", 선택지 §1 표). 커넥터 FIFO `min_g(여유_g/β_g)` | 선택지 §3.1·§3.3 |
| D-EB-6 | 이 항목이 U4·U5·U6 A2·U7a/b의 127 몫을 소유하고, G-v3b (a) SC1001\|W, G-U5-127, G6-7을 판정 | |
| D-EB-7 | FW_W 관문은 OBS판으로 판정하고 A1판을 함께 적음. F17-A′는 지금 넣지 않음. G-F12-3은 10638 차단 전에서 자름 | F2 §4 |
| D-EB-8 | 수용 압축은 WAVEJ 진단 팔만 | F2 §2.4 |
| D-EB-9 | F13은 이번 세대에 없음. 사건 창 FW_W 관문은 보고만 | |
| D-EB-10 | **기존 FZP 최대 활용, 새 다시드 R-obs 없음.** FZP 초기화 하네스(배포 LOR·UFA·SA 실행) + v3c1-s31 R-obs 템플릿 + v3c3-s31 R-obs(재핀이 어차피 돌리는 것) | 사용자 질문 |
| D-EB-11 | 기존 문턱 재사용. 새 문턱은 선택지 제안대로. 127 구속 지표 = **W + 포트** | |
| D-EB-13 | K7 HEAD에서 별도 워크트리를 만들어 구현. `<K>`는 읽기만 | |

## 2. 구조 [읽음·추론]

### 2.1 재고(stock)

| 재고 | ledger 이름 | 내용 | 변경 |
|---|---|---|---|
| 10491 포트 | `storage:OR_D_W_storage` | DelayedPort(CH:76-170), 용량 38.58, 커넥터 위 차량만 | 방출 대상만 바뀜 |
| 10481 포트 | `storage:OR_D_E_storage` | 용량 151.47 | 같음 |
| W 게이트 저장 | `storage:in_SC1001_W` | 32 + 129 + 127 비큐(1,237.8). **꼬리표 달린 정지선행 이동분**(포트 방출, 127 잔차, 129 꼬리 off-ramp 출신)과 꼬리표 없는 도시 차량 | 꼬리표 추가(재고 아님) |
| 127 차로군 큐 | `movement:SC1001_W_to_{E_SC1002,S_SC1003}` (SG2), `movement:SC1001_W_to_N_SC2002` (SG5) | 출신 무관 정지선 큐 | 예산·상한 |
| off-ramp movement 8개 | `movement:SC1001_off{W,E}_to_*` | 키가 있으면 늘 0 | 비활성 |

- 새 ledger 노드 종류는 없습니다. 모든 이동은 기존 노드 사이의 `emit_transfer`입니다.

### 2.2 1초 안의 순서 (UFA `urban_substep_accounted`, LC:76-116이 매초 부름)

1. 저장 release pop(UFA:252-262): 변경 없음
2. sink 이탈(UFA:264-350): 변경 없음
3. 도착 pop(UFA:352-381): `in_SC1001_W`이면 **SA.split_arrival**이 먼저 꼬리표 몫을 W 구성원에 넣습니다. 꼬리표 없는 몫은 기존 β(램프 포함)로 나뉩니다.
4. 게이트 착지(UFA:386-407): 변경 없음. 도시 W 몫은 무조건 큐에 합류합니다(§5.6).
5. 램프 이송(UFA:409-516): 변경 없음
6. off-ramp 배수(UFA:521 → LOR.drain LOR:34-110): 접근 포트는 **SA.allocate**의 몫만큼 방출하고 `storage:port → storage:in_SC1001_W`로 옮깁니다. 꼬리표는 도착 스텝에 답니다.
7. movement 서비스(UFA:527-621): W 구성원의 intended를 차로군 예산으로 묶습니다(**SA.limit_groups**).
8. LC:95-115: `ports.capacities`(LOR:112-120) → freeway → `ports.land`. 변경 없음. 포트가 차면 여기서 FW_W 진출이 막힙니다.

## 3. config 키와 스키마

### 3.1 tuning 키 `urban.stopline_approach` (팔 config에만)

```json
"stopline_approach": {
  "schema": "stopline-approach/v1",
  "evidence": {"path": "diagnostics/sdmpc_n31_20260924/stopline/sc1001eb_evidence_v3c3_<YYYYMMDD>.json", "sha256": "<64 hex>"},
  "approaches": ["SC1001_EB"],
  "merge_rule": "zipper",
  "city_admission": "unconditional",
  "origin_tags": "report"
}
```

- 필드 6개는 모두 필수입니다. 모르는 필드, 다른 값(`merge_rule`, `city_admission`, `origin_tags`는 위 값 하나만 허용), sha 불일치는 `ValueError`로 거부합니다. env 폴백과 getattr 기본값은 쓰지 않습니다.
- `freeway.lane_plant`가 없으면 거부합니다. 포트가 LOR에 있어야 하기 때문입니다.
- **배포 기본 config(`config_n31_v2.json`)는 바꾸지 않습니다.**
  - 팔 config `diagnostics/sdmpc_n31_20260924/config_n31_v2_sc1001eb.json`은 `make_config_n31.py`에 새 플래그(`--stopline-approach <evidence>`)를 주어 만듭니다.
  - 기본 config 바이트가 그대로인지는 생성기 시험으로 고정합니다.

### 3.2 증거 JSON `stopline-approach-evidence/v1` (sha 고정, G-EB-0이 생성)

```json
{"schema": "stopline-approach-evidence/v1",
 "network": {"path": "...baseline_s31_v3c3nc.inpx", "sha256": "3de889f0…"},
 "declarations": {"E1": {"script": "<E>/tools/a1_stopline.py", "script_sha256": "b437988a…", "declaration_sha16": "77304deded2de68a",
                         "result_sha256": "<v3c3 재계산 결과>"},
                  "geometry": {"script_sha256": "<g1_inpx.py>", "extract_sha12": "<g1 extract_sha>"}},
 "approaches": {"SC1001_EB": {
   "signal": "SC1001", "stopline_link": "127", "receiver": "in_SC1001_W",
   "link_length_m": 629.7760393736908, "jam_spacing_m": 6.0, "speed_floor_kmh": 20.0, "stopline_anchor_pos_m": 627.43,
   "groups": {
     "SG2": {"phase": "SC1001_p3", "lanes": [1, 2], "members": ["SC1001_W_to_E_SC1002", "SC1001_W_to_S_SC1003"],
             "s_veh_h_lane": 1783.399209486166, "storage_veh": 209.92534645789693},
     "SG5": {"phase": "SC1001_p4", "lanes": [3], "members": ["SC1001_W_to_N_SC2002"],
             "s_veh_h_lane": 2060.625, "storage_veh": 104.96267322894847}},
   "ports": {
     "10491": {"off_ramp": "OR_D_W", "stream": "upstream", "landing": ["129", 239.38422422843928], "distance_m": 689.97277577},
     "10481": {"off_ramp": "OR_D_E", "stream": "merge",    "landing": ["127", 210.27144602258932], "distance_m": 417.15855397}},
   "route_labels": {"1117": {"3": "SC1001_W_to_E_SC1002", "1": "SC1001_W_to_S_SC1003", "2": "SC1001_W_to_N_SC2002"},
                    "port_progress": {"1132:2": "OR_D_W"}, "tail_129_from_m": 239.38422422843928},
   "origin_prior": {"OFF_W": 0.6103, "OFF_E": 0.1966, "URB": 0.1931}}}}
```

- 값의 출처는 `OPT1_PREDECLARATION.md` §1에 있습니다.
- configure가 다시 확인하는 것
  - `storage_veh == link_length_m × len(lanes) / jam_spacing_m` (1e-9 이내)
  - `jam_spacing_m == cfg.network.urban_avg_vehicle_length_m`. LPR:296-298과 같은 확인입니다.
  - `s_veh_h_lane ∈ [1500, 2200]` (PR P0-W1 범위)
- β(회전 몫)는 증거에 넣지 않습니다. 실행 중 cfg의 `SC1001_off{W,E}_to_*` β를 쓰고, W_RAMP(β 0)를 뺀 세 정지선 목적지로 다시 정규화합니다. 그래프 값은 0.7193 / 0.2090 / 0.0716으로 결정 1117(0.719 / 0.209 / 0.072)과 같습니다 [실행 graph.json]. 새 값을 들이지 않습니다.

## 4. 상태 변수

| 위치 | 이름 | 생기는 때 | 내용 |
|---|---|---|---|
| `cfg.network` | `stopline_approach` | 키가 있을 때 configure가 설정 | 위 증거의 접근 명세, 증거 sha, 파생값(구성원 상한 `s_g·n_g`, β_g, 구성원→그룹 표) |
| `cfg.network.movement_capacity_by_movement_veh_h` | 구성원 3개 | 같음 | E·S = 1783.40 × 2 = **3566.80**, N = **2060.63** veh/h (구성원 상한 = 그룹 용량). 키가 없으면 기존 206.53/차로 정규값(ADP:3832-3836, :3896)이 그대로 남음 |
| `state` | `stopline_approach_state` (동적 속성, LOR·LUR와 같은 방식) | SA.initialize | `tags` {step: {"<member>\|<kind>": veh}}, kind ∈ {`port:OR_D_W`, `port:OR_D_E`, `resid`}. `speed_kmh`(지평 동안 유지). `origin` {member: {OFF_W, OFF_E, URB}}(보고). `alloc` {step, ports{off: L_p}, groups{g: room_g}}. `counters`. `last_step` |
| `state.lane_offramp_runtime.descriptions[off]` | `approach` = `"SC1001_EB"` | SA.initialize(10491, 10481 행만) | LOR 분기 선택자 |

- R_g(예약)는 저장하지 않습니다. 매번 `tags`에서 다시 셉니다(미래 스텝 꼬리표 전부의 그룹 합; kind는 `port:*`, `resid` 두 가지뿐). 드리프트를 막기 위해서입니다.
- 키가 없으면 위 속성들은 **존재하지 않습니다**. 그래서 pickle 바이트가 같습니다.

## 5. 동역학 규칙 (모두 SA 안, AD 안전: min·max·상수 나눗셈만 씀)

### 5.1 차로군 예산 (UFA:547과 :549 사이)
- B_g(t) = s_g · n_g · T_u_h · φ_g(t). φ_g는 첫 구성원 spec으로 부르는 `_uqm._phase_green_fraction(control, cfg, spec, urban_step_index=t)`입니다(UQM:670-727).
  - 연속 예측에서는 `signal_actuation_contract.phase_fraction` 패치(sdmpc_continuous.py:134-137)를 그대로 따릅니다. 그래서 **연속·tangent 경로가 같은 제약을 갖습니다**(C3K §9-4 지적 해소).
- 구성원 intended `i_m = min(q_m, T·φ_m·cap_m)`은 기존 계산 그대로입니다(UFA:536-540). allocation min(UQM:752-767)도 그대로입니다.
- Σ i_m > B_g이면 `i'_m = _uqm._allocate_receiving_counts(cfg.urban_follower.receiving_space_rule, {m: i_m}, B_g)`(UQM:770-785, 배포 규칙 "proportional" [실행 p0])로 줄입니다. 그다음 기존 receiving 배분(UFA:549-574)을 탑니다.
- 한 구성원이 receiving에 막혀 못 쓴 몫은 같은 스텝 안에서 다른 구성원에게 넘기지 않습니다(차로 FIFO 근사).
- SG2와 SG5 사이에는 결합이 없습니다(F1 §7).
- 수락 기록: UFA:590 옆에서 `SA.accepted(movement, actual)`를 부르고, Σ 수락 ≤ B_g + 1e-9를 단언합니다(G-EB-2 #1). LSS:104-108 `accepted`와 같은 형태입니다.

### 5.2 차로군 여유
- room_g(t) = max(0, S_g − Q_g(t) − R_g(t))이고, 배수 시점(3단계 도착 뒤, 7단계 서비스 앞)에 계산합니다.
- Q_g = Σ_{m∈g} `urban_movement_queue[m]`, R_g = 미래 스텝 꼬리표(`port:*`, `resid`) 중 그룹 g 몫의 합입니다.

### 5.3 포트 요청과 지퍼(D-EB-5)
- 포트 p의 요청: r_p = min(c_p · T_u_h, ready_p)
  - c_p = `cfg.network.movement_capacity_veh_h × lanes_p`. LOR:51·:56의 direct 분기와 같은 관례이고, 새 값이 아닙니다.
  - ready_p = `port.ready + Σ pending(due ≤ t+1)` (CH:101-118의 필드)
- r_{p,g} = β_g · r_p. β_g = Σ_{m∈g} β(포트의 목적지 m) / Σ(세 정지선 목적지 β)
- 127 @210.3 지퍼(그룹마다)
  - alloc_{E,g} = min(r_{E,g}, max(room_g/2, room_g − r_{W,g}))
  - alloc_{W,g} = min(r_{W,g}, room_g − alloc_{E,g})
  - E = 10481(merge), W = 10491(upstream)
- 한 스텝의 배분은 첫 접근 포트를 만났을 때 두 포트를 함께 계산해 `alloc`에 둡니다. 포트 dict 순서와 무관합니다.

### 5.4 커넥터 FIFO
- L_p = min(c_p · T_u_h, min_{g: β_g>0} alloc_{p,g} / β_g)
- n = `port.release(t, 1., L_p·3600)`(LOR:73)이고, 기존 단언 LOR:74-75가 그대로 걸립니다.
- 10491은 1차로라, SG5가 차면 E·S행도 뒤에서 막힙니다(선택지 §3.1).

### 5.5 착지(포트 → 접근)
- 구성원별 n_m = n · β_m / Σβ. 이동은 `emit_transfer(storage:port → storage:in_SC1001_W)`이고, 멤버십 인자는 LOR:92-94(direct)와 같습니다.
- `storage[in_SC1001_W]`에서 `_debit_stock`으로 차감하고, `storage[port] += n`(LOR:86-87과 같음)입니다.
- 도착 스텝: due_g = t + max(1, ⌈max(0, D_p − 6.0·Q_g/n_g) / (v/3.6) / T_u⌉). v = `speed_kmh`(≥ 20)입니다.
- `urban_arrival_buffer[in_SC1001_W][due] += n_m`, `urban_storage_release_buffer[in_SC1001_W][due] += n_m`. LOR:95-99와 같은 쌍 예약입니다.
- `tags[due]["m|port:<off>"] += n_m`
- 배수 기록 `departures[group] += n`(LOR:106)은 그대로 둡니다. off-ramp 방출 계상이 같게 유지됩니다.

### 5.6 도착 분할과 입장
- pop된 부모 도착량 A_t, 그 스텝 꼬리표 합 G_t에 대해 **G_t ≤ A_t + 1e-8을 단언**합니다(PRB:303-306과 같은 불변식).
- 꼬리표 몫은 해당 구성원 큐에 넣습니다. 꼬리표 없는 몫 A_t − G_t는 기존 β(게이트 β, 램프 포함)로 나눕니다.
- 반환 형식은 PRB:292-319와 같은 `[(movement, amount)]`입니다. 그래서 UFA:369-374의 루프(`_lane_ready`, `emit_transfer(..., route_key='arrival:'+m)`)를 그대로 씁니다.
- 꼬리표 몫은 예약되어 있었으므로 Q_g + R_g ≤ S_g가 유지됩니다(단언).
- **도시(꼬리표 없음) W 몫은 무조건 입장**합니다(선언 근사).
  - 129 @239.4 지퍼에서 도시 흐름은 SG2 수요의 약 0.19(F1 §4)라 1/2보다 작습니다. 그래서 지퍼는 도시를 거의 막지 않습니다 [계산·추론].
  - 이 근사의 위반량 `city_over_room_veh` = Σ max(0, Q_g + R_g − S_g)을 매 스텝 기록하고 보고합니다.
  - 게이트 착지(UFA:386-407)와 지연 처리 코드는 바꾸지 않습니다.

### 5.7 보존·FIFO 불변식 (G-EB-2에서 매 스텝 확인)
- I1: 모든 k에 대해 Σ tags[k] ≤ `urban_arrival_buffer[in_SC1001_W][k]` + 1e-8
- I2: Σ_k Σ tags[k] ≤ `occupancy(in_SC1001_W)` + 1e-8
- I3: Q_g + R_g ≤ S_g + `city_over_room_g` + 1e-9
- I4: 포트 방출 ≤ L_p + 1e-9, Σ 수락_g ≤ B_g + 1e-9
- I5: off-ramp movement 8개 큐 ≡ 0
  - UQM:157-160은 이 movement를 `OR_D_*_storage`에서 받게 매핑합니다.
  - 그 도착 버퍼는 AR:72-75가 지우고, 접근 분기는 포트 저장으로 예약하지 않습니다. 그래서 0이 유지됩니다 [읽음].
- I6: ledger `assert_stocks(model_inventory)`(CAO:684-694; LC:116에서 `captures_response`일 때 이미 부름). 새 단언은 SA 안의 I1–I5입니다.

### 5.8 관측 쪽 초기화 (SA.initialize, RS:253 뒤, ledger 시드 RS:254-256 앞)
1. **설치 확인**(§8.2)
2. 10491·10481 행에 `descriptions[off]['approach'] = 'SC1001_EB'`를 답니다(branch `signal`, group OR_D_W/OR_D_E인지 확인).
3. **127 큐 재귀속**(1/14 수정, §6)
4. **127 잔차·129 꼬리 꼬리표**(U6 A2·U7a의 127 몫)
   - provenance `['127']['storage:in_SC1001_W']`(잔차 대수)와 `['129']`, 현재 차량 기록(위치·속도·차로·경로)을 씁니다.
   - 127 위 비큐 차량: 경로가 1117:x면 그 목적지로 보냅니다. 아니면 차로 규칙(1–2 → E·S를 β 비로, 3 → N)을 씁니다. kind `resid`이고, 도착 due는 (627.43 − pos − 6.0·Q_g/n_g)/max(v_veh, 20 km/h)입니다.
   - 129 꼬리(pos ≥ 239.38)에서 현재 경로가 1132:2인 차량: kind `port:OR_D_W`이고, 목적지는 β로 나눕니다.
   - 같은 양을 `urban_arrival_buffer`·`urban_storage_release_buffer`의 `in_SC1001_W` 기존 예약(+15 s / +105 s, ADP:10087-10093; AR:60-84로 짝지음)에서 **비례로 뺍니다**. LPR:414-422의 "옮긴 몫을 옛 예약에서 n/n0 비례 제거"와 같은 방식입니다. 총량은 정확하고, 시각 분할만 근사입니다.
5. 출신 구성(보고): 초기 큐는 `origin_prior`(SG2 포화 주기 0.610 / 0.197 / 0.193)로 둡니다. 꼬리표 도착분은 kind로 출신을 압니다.
6. `speed_kmh` = max(129 ∪ 127 위 움직이는(≥ 1 km/h) 차량 평균 속도, 20). U8C u8b와 같은 정의이고, 지평 동안 유지합니다(선언 closure).
7. `audit_projection_provenance`를 다시 부릅니다(LPR:533-535와 같은 호출).
- 이 단계는 모두 RS:254-256(`area_runtime.configure` → AR:41-57 `seed_from_projection`) **앞**입니다. 그래서 ledger가 바뀐 provenance로 시드되고, 추가 조정이 필요 없습니다.

## 6. 127 관측 귀속(1/14) 수정

- **현재 결함** [읽음]
  - `link_to_movements["127"]`의 14개 항목이 모두 weight 1.0이고, 귀속 키가 없어 기본 가중 분기를 탑니다(ADP:6526-6527).
  - 그래서 127 정지선 큐가 W 3 / off-ramp 8 / E 접근로 3에 1/14씩 갑니다(F1 §8.3). 큐 대수 자체는 contiguous 걷기 합입니다(ADP:6286-6287).
- **수정**(키가 있을 때만, SA.initialize 3단계)
  1. `counts = provenance['127']`. 큐 몫 Q = Σ `movement:*` 배정이고, 잔차는 `storage:in_SC1001_W`입니다.
  2. 14개 movement에 배정된 양을 큐에서 되돌립니다(`urban_movement_queue[m] -= n`, LPR:316 방식).
  3. 차로별 걷기 `ADP._contiguous_stopline_queue_by_lane(state_json)`의 `('127', lane)` 값으로 나눕니다.
     - 차로 1–2 → SG2. 구성원 사이는 차량 경로 1117:3/1117:1이 있으면 그것으로, 없으면 β 비(0.909 / 0.091)로 나눕니다.
     - 차로 3 → N입니다.
     - 걷기 합과 Q의 차가 1e-7보다 크면 차로 비율로 Q를 나눕니다(질량은 Q 그대로).
  4. provenance `['127']`을 새 배정으로 바꿉니다.
- 결과
  - E 접근로 movement와 off-ramp movement가 127에서 받는 몫은 0입니다(G-EB-2 #5).
  - **ADP:6459-6538 루프는 손대지 않습니다.** 다른 링크와 키 없는 경로는 비트 동일합니다.
- **ADP 변경은 한 곳**: `_contiguous_stopline_queue`(ADP:5382-5459)를 두 함수로 나눕니다.
  - `_contiguous_stopline_queue_by_lane(state_json) -> {(link, lane): q}`: 기존 본문(ADP:5418-5458)을 그대로 쓰고, 마지막 누적만 차로 키로 바꿉니다.
  - `_contiguous_stopline_queue(state_json)`: by_lane의 **삽입 순서 그대로** `out[link] = out.get(link, 0.0) + q`. 기존 누적(ADP:5457-5458)과 같은 순서·같은 연산이라 비트 동일합니다(시험 T10).
  - 걷기 정의(머리 창 30 m, ADP:5203; 정지 판정은 러너 `speed < 1.0 km/h`, VBS:352·:3518; 빈 7.0 m, VBS:3545·:3854)는 바꾸지 않습니다. 127은 `_link_lengths_m`에 없어서 머리 창 조건 없이 걷습니다(U8C 주석).
- **mapping 파일을 바꾸는 방식(prepare_projection)을 쓰지 않는 이유**: 하네스(이미 시드된 템플릿 상태)와 배포 경로가 **같은 SA.initialize**를 부르게 하려면, 투영 결과의 출처 기록에서 되돌리는 방식이어야 합니다 [추론].

## 7. 코드 변경 위치 (K6 줄; ADP는 K7에서 +2)

| # | 파일:줄 | 변경 | 키 없음일 때 |
|---|---|---|---|
| 1 | **SA (신규)** `evaluation/controllers/stopline_approach.py` (~400줄) | `view`, `configure`, `observe(raw)`, `initialize`, `allocate`, `land_release`, `split_arrival`, `limit_groups`, `accepted`, `diagnostics`, `install_check` | import되지 않음 |
| 2 | RS:185 뒤 | `metadata.update(stopline_approach.configure(cfg, tuning, state_json))`. HSR.finalize(:184)·LSS.configure(:185) 뒤라 다른 소유자의 구성원 용량 덮어쓰기를 확인한 다음 소유함. 구성원이 LSS `group_of`나 HSR `extra_pool_groups`에 있으면 거부 | 키 없으면 `{}` 반환, 아무것도 설정하지 않음(HSR:28-36 패턴) |
| 3 | RS:253 뒤 (`lane_plant_runtime.initialize` 직후, `area_runtime.configure` :254 앞) | `metadata.update(stopline_approach.initialize(state, cfg, state_json, detector_mapping))` | `{}` |
| 4 | LOR:49-58 | `elif row.get('approach'):` 분기를 `local_upstream`(:49)과 `direct`(:54) 사이에 추가. requests = `[(None, 'in_SC1001_W', L_p, c_p·T, room)]` | `row`에 키가 없어 기존 분기 |
| 5 | LOR:91-99 | `elif movement is None and row.get('approach'):` → `SA.land_release(state, cfg, step, off, row, n)` (§5.5). 기존 `direct` 갈래(:91-99)는 그대로 | 미진입 |
| 6 | UFA:363 앞 (도착 루프 안) | `sa = SA.view(cfg)`이고 `source == sa['receiver']`이면 `tagged = SA.split_arrival(...)`. None이 아니면 :369-374와 같은 루프 후 `continue` | `view`가 None. 속성 조회 1회 외 연산 없음 |
| 7 | UFA:547과 :549 사이 | `SA.limit_groups(state, control, cfg, step_idx, intended_by_storage, no_storage_intended)` (§5.1, 제자리 수정) | 미호출 |
| 8 | UFA:590 옆 | `SA.accepted(movement, actual)` (I4 기록) | 미호출 |
| 9 | ADP:5382-5459 | 차로별 걷기 분리(§6) | 비트 동일(T10) |
| 10 | `diagnostics/sdmpc_n31_20260924/make_config_n31.py` | `--stopline-approach` 플래그로 팔 config 생성 | 기본 출력 바이트 동일(시험) |
| 11 | `diagnostics/sdmpc_n31_20260924/stopline/build_sc1001eb_evidence.py` + 증거 JSON | G-EB-0 산출을 증거로 묶고 sha 고정 | 해당 없음 |
| 12 | `diagnostics/sdmpc_n31_20260924/tests/test_stopline_approach.py` | §10 시험 | |

- **바꾸지 않는 것**: LPR(설명 행 표시는 SA.initialize가 함), UQM, AR, CAO, LC, PRB, LSS, HSR, AFA, SB, VBS, mapping 파일, 배포 config, plant manifest(`plant_n31_v2.json`).
- 이유: 이 항목은 tuning이 켜는 도시 쪽 논리이고 plant 원천 핀을 바꾸지 않습니다. 선택지 §3.2의 "manifest 새 세대"는 팔 config 파일 + 증거 sha 핀으로 대신합니다 [추론].
- **이전 3-origin 별도 계상 경로의 격리**(메모리 "승격하면 구버전은 격리")는 승격 결정 때 합니다. 이번 구현은 키로만 켜는 팔입니다.

## 8. 다른 항목과의 상호작용

### 8.1 K3 서비스 표 (de5ff5f)
- K3는 미터 서비스 표를 두 곳에서 정규화합니다. configure의 이송 표와 LPR.initialize의 측정 머리 곡선(LPR:508-516, PRB:36·:84-87)입니다. 결과 메타데이터는 `lane_ramp_head_service_normalisation` = {'RM_C10490': {'3': '2'}}입니다.
- **SA는 다음을 읽지도 쓰지도 않습니다**: `physical_ramp_branches['ramps'][*]`, `service_by_green_veh_h`, `service_capacity_veh_h`, `ramp_capacity_veh_h`, `minimum_green_sec`.
  - 구성원 3개는 `spec['ramp']`가 None이어야 합니다(configure 단언). 미터 서비스 이름공간과 겹치지 않습니다.
- **행동상 결합은 있습니다** [추론]
  - 배포에서는 127 잔차(R-obs 평균 91.9대)의 게이트 β 0.85가 `SC1001_W_to_onW/onE` → RM_C10482/RM_C10490 큐로 갔습니다(F1 §8.3, 약 78대/결정).
  - 키가 있으면 이 몫이 0이 되어 두 미터 큐 입력이 줄고, 리더의 미터 격자 방문 경로가 달라질 수 있습니다.
  - 표와 격자(10490 {0, 2, 4, …, 10})는 그대로이고, `candidate_from_services`의 거부 규칙도 그대로입니다.
- 관문: G-EB-9에 "키 있음/없음에서 8개 미터 표·정규화 메타데이터 바이트 동일"을 더합니다. 미터 큐 차이는 G-EB-10 보고에 넣습니다.

### 8.2 K6 설치 확인 (54d821c)
- K6의 `REFERENCE_INSTALLED_KEYS`(LPR:74)는 plant reference의 freeway 키 목록이고, 그 기록이 `lane_plant_install_check` 메타데이터(LPR:542)로 나갑니다. **여기에 항목을 더하면 키가 없어도 메타데이터가 바뀝니다.** 그래서 쓰지 않습니다.
- 대신 SA.install_check가 같은 정신으로 거부합니다. 키가 있을 때만 `stopline_approach_install_check` 메타데이터를 냅니다.
  - tuning에 키가 있는데 `cfg.network.stopline_approach`가 없음
  - LOR 10491·10481 행에 `approach`가 없음, 또는 branch/group 불일치
  - 구성원 상한 ≠ s_g·n_g
  - 증거 sha 불일치
  - 다른 풀(LSS·HSR)이 구성원을 소유함
  - `urban.queue.contiguous`가 꺼져 있음(차로별 걷기가 없음)

### 8.3 C2·C3 v2·U7
- C2(`urban.queue.attribution = "route"`, ADP:5254-5378)가 켜져도 link 127은 SA가 마지막에 다시 귀속하므로 SA가 소유합니다. 이 순서를 install_check 메타데이터에 적습니다.
- C3 v2를 v3c3로 옮길 때
  - U4·U5의 127행, U6 A2·U7a/b의 127 몫을 빼야 합니다.
  - SHG·RD가 SA 구성원을 만지면 SA.install_check가 거부합니다(구성원 소유 단언).
- U7 [읽음 U7 §0·§5.3]
  - U7b(127 큐 → W만, 차로대로)와 U7a(운동학 도착)는 SA의 §6·§5.8-4와 같은 방향입니다.
  - G6-7이 U7b+F2에서 +16.7까지 오른 것은 범주가 어긋난 정의에서였습니다. 이 항목은 W 큐에 off-ramp 출신을 넣어 범주를 맞춥니다.

## 9. 키 없음 = 비트 동일 논증

1. **config**: 배포 config에 키가 없습니다. SA.configure는 `{}`를 반환하고 `cfg.network`에 속성을 만들지 않습니다(HSR:28-36과 같음). → cfg pickle 바이트가 같습니다.
2. **초기화**: SA.initialize는 view가 None이면 즉시 `{}`입니다. LOR 설명 행에 키를 더하지 않고, `state.stopline_approach_state`를 만들지 않습니다. → state pickle 바이트가 같습니다.
3. **LOR**: `row.get('approach')`는 부동소수 연산이 없는 dict 조회입니다. 기존 세 분기의 연산 순서가 같습니다.
4. **UFA**: 도착 루프의 `SA.view(cfg)`는 속성 조회 1회입니다. 예산·수락 호출은 view가 None이면 실행되지 않습니다. 진단 키를 더하지 않으므로 action JSON이 같습니다.
5. **ADP**: 걷기 분리는 같은 dict 삽입 순서와 같은 `+` 연산이므로 결과가 비트 동일합니다(T10: 기록된 R-obs 원자료 10개 상태 + 무작위 빈 시험).
6. **import**: SA는 view가 있을 때만 함수 안에서 import합니다. 키가 없으면 모듈이 로드되지 않습니다(numba·전역 상태 무영향).
7. **메타데이터**: K6 `lane_plant_install_check`와 K3 `lane_ramp_head_service_normalisation`이 바뀌지 않습니다. SA의 새 메타데이터는 키가 있을 때만 생깁니다.
- 실행 확인은 G-EB-1(R-obs 템플릿 9상태 × OBS·A1 H3 + 2700 H42, K7 HEAD 대 구현 트리 키 없음: 숫자 필드 차 0)입니다. 이 비교 도구는 이번에 `<K6>`에서 시험했습니다. termcost 트리 결과와 47,861개 숫자 필드가 같았고, 목적값 `513.3271772837957`도 같았습니다 [실행 `<P>/p3_compare_OBS_002700_H3.json`].

## 10. 추가할 단위 시험 (`tests/test_stopline_approach.py`, 금지 시험과 무관)

| ID | 내용 |
|---|---|
| T1 | 스키마: 유효한 절 적재. 필드 누락·모르는 필드·sha 불일치·구성원 없음·kind ≠ boundary_in·phase 불일치·ramp 구성원·다른 풀 소유·contiguous 꺼짐 → 거부 |
| T2 | 키 없음 no-op: configure·initialize가 `{}`. cfg·state pickle 바이트와 LOR 설명 행이 키 없음 전후로 같음. `make_config_n31.py` 기본 출력 바이트 동일 |
| T3 | 차로군 예산: 두 구성원 Σ 서비스 ≤ s·n·T·φ. 비례 배분. 한 구성원이 receiving에 막혀도 예산 이전 없음. φ = 0이면 0 |
| T4 | 지퍼: 여유가 크면 둘 다 요청만큼. 여유가 작으면 10481이 절반. 10481 요청 < 절반이면 10491이 나머지. β_g = 0인 그룹은 건너뜀 |
| T5 | 커넥터 FIFO: SG5만 차면 10491의 E·S행도 L_p로 묶임. 방출 ≤ L_p |
| T6 | 보존: 포트·게이트·구성원이 있는 작은 상태에서 N스텝 → I1–I5, ledger `assert_stocks` 통과 |
| T7 | 지연: due = t + max(1, ⌈(D − 6·Q_g/n_g)/(v/3.6)/T_u⌉), v 하한 20 |
| T8 | 127 재귀속: 1/14 provenance → E 접근로·off-ramp 몫 0, W 차로 분할, 총량 보존, provenance 갱신, `audit_projection_provenance` 통과 |
| T9 | 잔차·129 꼬리 꼬리표: +15/+105 예약에서 비례 제거, 쌍 예약 일치, 경로 1117:x 존중, 1132:2 → `port:OR_D_W` |
| T10 | ADP 걷기 분리 비트 동일: `<T>/replays/*/state_*.json` 10개(읽기 전용 고정 자료) + 무작위 빈 |
| T11 | K3·G-SC109: 키 있음/없음에서 미터 8개 `service_by_green_veh_h`·정규화 메타데이터, SC109 movement 6개 최종 용량·spec 바이트 동일 |
| T12 | 설치 확인: §8.2의 각 경우 거부, 정상 시 메타데이터 기록 |
| T13 | AD: 예산·지퍼·FIFO의 Dual 미분(p3 녹색)이 중앙 차분과 상대 1e-6 이내 |
| T14 | `copy.deepcopy`·pickle 왕복 후 `stopline_approach_state` 동일(후보 복제) |

## 11. 기록(진단, 키 있을 때만, 결정당 ≤ 16키)
- `stopline_approach_binding_steps_{SG2,SG5}`: 예산 구속 스텝
- `stopline_approach_full_steps_{SG2,SG5}`: room = 0
- `stopline_approach_port_blocked_steps_{10491,10481}`: L_p < r_p
- `stopline_approach_port_release_veh_{10491,10481}`
- `stopline_approach_reserved_max_{SG2,SG5}`
- `stopline_approach_city_over_room_veh`
- `stopline_approach_origin_share_{OFF_W,OFF_E}`(보고)
- `stopline_approach_tag_residual_max`(I1 여유)

## 12. 위험·열린 점
1. **F13 부재**: 사건 때 AFA 단면 FIFO(AFA:321-351)가 FW_W 전체를 깎습니다(선택지 §3.5 (1)). 그래서 사건 창 FW_W는 보고만 합니다(D-EB-9) [추론].
2. **S_g가 사건 여부를 정합니다**: 기하 210은 관측 최대 156–169(74–80 %)보다 큽니다. 129 꼬리 31대를 따로 두지 않으므로 사슬 전체로는 38.6 + 210 대 VISSIM 38.6 + 31 + 156–169입니다. FH에서 S_g = 관측 최대인 민감도 팔을 보고합니다(예선언 §5) [추론].
3. **도시 무조건 입장 근사**: `city_over_room_veh`로 위반량을 봅니다. 크면 129 지퍼 입장을 넣는 후속 변경이 필요합니다.
4. **SG2 용량 증가 657 → 1,400 veh/h**는 SC1001 하류(SC1002 회랑, 무제어 포화)를 더 채웁니다(선택지 §3.5 (3)). G-EB-10에서 보고합니다.
5. **가격·듀얼 증폭 전례**(메모리 +1,432): 폐루프 판정은 승인 뒤 J1-W 3시드 짝으로만 합니다(G-EB-12).
6. 예측 캐시(`prediction_cache`, `response_np_cache`)의 상태 토큰이 `stopline_approach_state`를 포함하는지 구현 때 확인해야 합니다 [미확인].
7. 129 꼬리 off-ramp 출신을 현재 경로 1132:2로 식별하는 것은 1117 이전이라 가능합니다(선택지 §3.1). 차선 변경 중 차량은 근사입니다.
