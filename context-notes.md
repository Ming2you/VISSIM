# 컨텍스트 노트 — 플랜트 모사층 (2026-08-04 ~)

작업 중 내린 결정과 그 근거를 **시간순으로 append** 한다. 다음 세션이 재유도 없이
이어받기 위한 기록이므로, 지난 항목은 고치지 않는다 — 틀린 것으로 판명되면 새 항목에
"정정" 으로 적는다(실제로 여러 번 그렇게 했다).

- 남은 일과 우선순위 → `checklist.md`
- 저장소 안내·실행법 → `README.md`
- 플랜트 충실도 감사 요청 → `PLANT_FIDELITY_AUDIT_REQUEST.md`

착수 시점의 국면은 "램프 축 복구"였고(2026-08-04, 아래 초반부), 그 뒤 도시부 토폴로지 →
관측 배선 → **플랜트 충실도 검증**으로 옮겨 왔다. 초반부 서술의 국면 전제는 지금과 다르다.

---

## 2026-08-04 — 리더 목적함수를 J = TTT + far 로 환원하기로 결정

**결정.** 리더 벌점항(`w_ramp_queue`, `w_F`, `w_P`, `w_L`, `w_boundary_in`, `mfd_storage_weight`)을
전부 0 으로 내리고 far 를 항상 ON 으로 둔다. 사용자 지시.

**왜.** 운영 리더 실측 분해에서 base(TTT)가 J 의 98.2~98.6 % 였고 벌점 5개 중 3개는
전 스텝 정확히 0 이었다. 남은 둘(`w_ramp_queue` 1.36 %, `w_F` 0.04~0.90 %)도 미미하다.
"초기 디자인은 TTT + terminal cost 뿐이었다"는 사용자 기억이 실측과 맞았다.

**결정적 근거(사후).** 같은 v6 궤적을 v5 목적함수로 재채점하니 G6 순위 상관이
**rho −0.080 → +0.705** 로 뒤집혔다. 벌점은 임계 비선형을 잡아주고 있던 게 아니라
모델-플랜트 상태 차이를 증폭하고 있었다(ΔTTT +127.90 → ΔJ +28,712, 216배).

**부수 결정 두 가지.**
- `sup_pfo.enabled = false`. far 를 항상 ON 하면 어댑터 L1411
  `sup_off = (sup_gate=="fargate" and leader_mfd_far_enabled)` 때문에 감독자가 자동으로
  영구히 꺼진다. 암묵적으로 두지 않고 명시했다(사용자 선택).
- `w_ramp_queue = 6.0` 삭제. 이 항은 커밋 `0f36b50`(2026-07-07)이 "방류=ramp→freeway
  이동이라 realized TTT 가 net-0(위치 불변성)" 진단의 처방으로 넣은 선형 terminal cost 다.
  far 의 램프 항 `q²/(2·merge_rate)·T_c_h` 가 대체한다는 전제로 뺐다(사용자 선택).
  **미해결 위험** — far 는 가격 rollout 에 안 들어간다(`price_far_enabled = False`).
  후보 채점에만 있으므로 metering 신호가 가격 채널에서는 여전히 비어 있다.

**되돌리기.** `real_world_modi_pstack_v5_tttfar_20260804.json` 을 안 쓰기만 하면 된다.
부모 체인 무변경.

---

## 2026-08-04 — "도시부 route design 을 IC 로" 는 불필요로 판정

**한때의 결론(철회).** 본선 유량이 온램프 합류 세그먼트 네 곳 전부에서 떨어지고
(−178/−747/−374/−822) 양의 단차 합이 +5 veh/h 뿐이라, "도시부가 IC 로 차를 안 보낸다"고
결론냈다. 사용자에게도 그렇게 보고했다.

**철회 근거.** 그 측정은 같은 세그먼트의 오프램프 유출과 온램프 유입을 분리하지 못한다.
커넥터 단위로 다시 재니 **온램프 유입 4,436 veh/h, 오프램프 유출 6,681 veh/h** 였다.
순이 음수인 것은 온램프가 없어서가 아니라 오프램프가 더 크기 때문이다.
**램프 수요는 충분하다.** route design 은 건드리지 않는다.

**교훈.** 합류 세그먼트의 순 단차로 온램프 유입을 추론하면 안 된다.
같은 구간에 오프램프가 있으면 부호가 뒤집힌다.

---

## 2026-08-04 — 커넥터 유량 측정법을 찾았다 (`.inpx` 무수정)

**문제.** `bottleneck_links` 의 `count` 는 스냅샷 점유지 유량이 아니다
(`run_real_world_stackelberg_controller.vbs:1277` `AddDictNumber linkCounts, key, 1.0`).
그래서 플랜트 온램프 유량을 읽을 수단이 없다고 판단했고, 데이터수집점 신설을 검토했다.

**해결.** 커넥터에도 기하가 있다 — 단 `<geometry><linkPolyPts><linkPolyPoint x y zOffset>`
이지 `point3D` 가 아니다. 앞선 감사가 `point3D` 로 찾아 0 을 읽고 "기하 없음"으로 오판했다.
길이가 있으면 `k = N/L`, `q = k·v` 로 유량이 나온다.
**이미 수집된 CSV 로 닫힌다 — `.inpx` 수정도 VISSIM 재실행도 불필요.**

**산출물.** `scripts/measure_ramp_connector_flow.py`.
커넥터 길이 149~730 m 로 전부 타당하다. 네트워크에 데이터수집점이 198개 있으나
램프 미터·접근링크 위에는 0개이고 VBS 는 DataCollection 을 아예 안 읽는다(grep 0건) —
그래서 이 경로가 아니라 기하 기반으로 갔다.

---

## 2026-08-04 — 램프 축 실패의 근본 원인 확정

**원인.** 모델이 온램프 수요를 과소추정한다.

| 그룹 | 모델 forecast | 플랜트 실측 | 배율 |
|---|---:|---:|---:|
| R_D_W | 180 | 1,050 | 5.8 |
| R_F_W | 810 | 1,225 | 1.5 |
| R_D_E | 180 | 1,188 | 6.6 |
| R_F_E | 120 | 972 | 8.1 |
| 합계 | **1,290** | **4,436** | **3.4** |

**메커니즘.** `calibration.prediction.local_ramp_arrival_forecast` 가

```python
observed_vph = ramp_counts[r] × 3600 / queue_drain_horizon_sec × multiplier
observed_vph = clamp(observed_vph, 0, max_vph_by_ramp.get(r, max_vph_per_ramp=900))
```

로 유도한다(`adapter:1714-1767`). `queue_drain_horizon_sec` 가 **스칼라 120 s 고정**이라
점유에 일률적으로 30 을 곱한다. 실제 통과시간은 램프별로 다르다 —
실측에서 역산한 필요값이 R_F_E 7.4 s / R_D_E 18.2 s / R_D_W 20.6 s / R_F_W 79.3 s 다.
게다가 cap 900 이 실측 최대 1,225 보다 낮아 위쪽이 잘린다.

**귀결.** 모델 세계에서는 램프 수요(그룹당 120~810)가 미터 섭동 하한(1440)보다 한참 아래라
`dTTT/dm` 이 **정의상 0** 이다. 플랜트에서는 수요가 972~1,225 라 그룹 600(c15)이 확실히
구속한다. **모델과 플랜트가 서로 다른 영역에 있다.** 이것이 램프 축 부호 불일치의 원인이다.

**앞선 진단 정정.** "미터 작동범위가 수요 위에 있다"는 맞지만 그건 **모델 안에서만** 참이다.
플랜트에서는 c15 가 온램프 유입을 4,436 → 2,849 (−36 %) 로 실제로 줄인다. **metering 은 작동한다.**

---

## 2026-08-04 — 한계가격에 terminal cost 를 넣어도 램프는 안 살아난다

2×4 격자(깊이 360 s/900 s × TTT/+hinge/+far/+both)를 실측 t0 상태에서 계산했다.

- 가격은 램프별로 잘 갈린다(폭/평균 3.3~3.8). `R_F_W` 가 30배 크고 `R_F_E` 는 0.
  **차별화가 아니라 절대 크기(1e-7~1.5e-4 h²)가 문제다.**
- **far 는 설계대로 작동한다** — 깊이 6 의 `+far`(−1.53e-04)가 깊이 15 의 순수
  TTT(−1.15e-04)를 근사한다. "terminal cost 로 긴 지평을 싸게 대신한다"가 실측 확인됐다.
- `+hinge` 는 오히려 가격을 60 % 줄인다. 코드 주석의 기대와 반대다(원인 미규명).
- 관측 ΔJ 예측은 전 8조건 실패(예측 +0.00~0.02 대 관측 −137~−473).

**해석.** 가격 목적함수가 문제가 아니었다. 입력 수요가 틀려서 어떤 목적함수를 써도
미분이 0 인 영역에 있었다. **먼저 수요를 고치고 나서 가격 실험을 다시 해야 한다.**

---

## 2026-08-04 — G6 관측 목적함수가 도시부의 1.4 %만 본다 (최상위 결함)

**증상.** green 축 부호가 0/2 로 틀리고, 램프 축도 부호가 흔들린다.

**측정.** 앵커 15스텝 누적에서 플랜트 실측 도시부 69,495대인데 투영 도시부는 **987대(1.4 %)**다.
고속도로는 32,991 → 33,978 (103 %) 로 정확하다. 즉 `J_vissim` 은 사실상 고속도로 전용이다
(도시부 기여 2.8 %, 실제 네트워크는 도시부가 68 %).

그래서 도시부로 차를 미는 레버가 전부 반대로 채점된다.

| 후보 | Δ실측 총 | Δ투영 총 | 부호 |
|---|---:|---:|---|
| c20_major75 | +1,973 | −461 | **반전** |
| c15_rampall300 | +853 | −1,030 | **반전** |
| c21_minor75 | +1,023 | +1,022 | 같음 |
| c06_vsl50 | +7,282 | +7,122 | 같음 |

VSL 만 맞는 이유는 그 효과가 고속도로 내부라 관측 채널에 그대로 잡히기 때문이다.

**원인 확정.** 모델 저류 용량 부족이 아니다 — `urban_link_storage_veh` 총 5,580대에 투영 점유가
83.5대(1 %)이고 **상한에 붙은 링크가 0개**다. 입력 자체가 없다.

`state_*.json` 의 `local_observation` 을 보면

```
detector_mapping_json : evaluation/real_world_modi_control/detector_local_mapping.json   <- base 22링크
link_counts           : 22개, 합 2,085 (그중 고속도로 2/24/26/74 가 1,875)
```

**플랜트 런이 base 22링크 detector 매핑으로 상태를 기록했다.** 채점은 분산 175링크 매핑으로
투영하므로 153개 링크에 데이터가 없다.

`run_real_world_stackelberg_controller.vbs:107` 이
`RW_DETECTOR_MAPPING_PATH = "evaluation/real_world_modi_control/detector_local_mapping.json"` 를
**하드코딩**하고 `:120` 이 무조건 대입한다. 러너 `run_real_world_single_watchdog.ps1` 의 param 에도
detector 매핑 인자가 없다(`-Mapping` 은 있고 VBS 위치인자 10 으로 간다).
`control_mapping` 만 오버라이드 가능하고 `detector_local_mapping` 은 불가능한 비대칭이다.

**수정 방안.** VBS 위치인자는 24 까지 쓰고 있으므로 25 를 신설한다.
`detectorMappingPath = ArgOrDefaultText(25, RW_DETECTOR_MAPPING_PATH)`, 러너에 `-DetectorMapping`,
그리드 스크립트에 `-DetectorMappingOverride`. **기존 state json 에는 데이터가 없으므로
그리드 재실행이 필요하다(재채점으로는 못 고친다).**

**주의.** 탐침이 이 스크립트들을 쓰는 중에는 수정하면 안 된다(케이스 중간에 스크립트가 바뀐다).

## 2026-08-04 — 램프 복합체 토폴로지와 신호 (사용자 정정)

- **링크 70/68 에 신호가 없다는 내 서술은 불완전했다.** 링크 70 은 커넥터 10641/10700 으로
  **링크 71** 로 나가고 링크 71 에 `SG 1004-2, 1004-5` 가 있다. 오프램프 방류는 **SC 1004** 가 통제한다.
- **SC 1004 는 사실상 F측 인터체인지 신호다.** 링크 71(SG 2,5)이 링크 70(오프램프 수용)을 배수하고,
  링크 52(SG 1,6)·46(SG 4,7)·66(SG 3,8)이 링크 68 을 먹이는데 링크 68 의 유일한 출구가
  온램프 미터 10646/10681 이다.
- 그런데 `signal_controller_roles.csv` 에서 `interface_head_count > 0` 인 제어기는 **SC1001 하나뿐**이다.
  SC1001 은 신호두가 링크 32 에 있고 링크 32 에 오프램프 커넥터가 직접 물리는데,
  SC1004 는 커넥터가 한 홉 더 있어(70 → 10641/10700 → 71) 탐지에서 빠졌다.
  **역할 분류기가 한 홉만 본다.**
- 축 자체는 우연히 맞는다. 모델의 오프램프 방류 movement(`*_off*_to_*`)는 D·F 양쪽 다 p1 이고,
  SC1004 는 `major_maps_to=p2` 라 minor↔p1 → 링크 71(SG2)=minor=p1 로 대응한다.
- **관측 공백.** `U_D`/`U_F` 의 `visible_links` 는 램프 커넥터 8개씩뿐이고 C-D 저류 링크가 없다.
  `observable_links` 에도 31/68/69/70 이 없다(32/71 만 있다 — 신호두가 있어서).
  커넥터는 물리 상한에 포화하므로(10646 k=94.4, 10638 k=95.4) **그 뒤에 쌓인 큐가 통째로 안 보인다.**
  실측 중앙값으로 커넥터 16개 합 195대 대 C-D 링크 6개 합 322대다.

## 2026-08-04 — 도시부 토폴로지: 5노드 격자 -> 36교차로 연결형

**사용자 요구.** 도시부 플랜트의 모든 링크·교차로를 **동일한 movement 큐/링크 저류 모델**로 예측하고,
그중 선택한 교차로만 통제·보호망으로 삼아 TTT 를 잰다. 나중 분석이 "통제 15 SC 의 TTT 절감 대
인접 비통제 구간의 TTT 증가"라서, 비통제 교차로를 뭉뚱그리면 안 된다.

**출발점의 오해 정정.** "플랜트에 모델 도시부가 다 반영됐다"는 내 말은 절반만 맞았다.
분산 생성기는 플랜트 아티팩트뿐 아니라 **모델 쪽 SC 이름공간 토폴로지까지 만들어 뒀다**
(`evaluation/configs/real_world_modi_pstack_distributed_15core_20260728.json` 의 `config_overrides.network`).
그런데 **우리 튜닝 체인이 그 가지를 상속하지 않는다** — 둘 다 `vsl_rollout_vissimdsd_20260725` 에서
갈라진 형제이고 우리는 flagship 쪽만 탔다. 그래서 플랜트는 15 SC 로 구동되는데 모델만
default.yaml 의 6노드 격자였다. **확장이 아니라 체인 병합 문제였다.**

**막고 넘어간 결함 셋.**
1. `distributed_15core` 는 `on_ramp_to_movement` 가 **전부 빈 리스트**다.
   `include_sc1_coupling = args.selector != "core15"` 가 하드코딩이라 core15 만 결합이 꺼진다.
   그대로 병합하면 도시부->온램프 연결이 사라져 metering 이 조일 대상을 잃는다.
2. 램프 넷을 SC1 하나에 몰면 D/F 구분이 모델에서 사라진다. 실측 구조는 인터체인지가 둘이다 —
   D측 SC1001(신호두가 링크 32, 오프램프 10481/10491 직결), F측 SC1004(링크 71 이 링크 70 배수,
   링크 52/46/66 이 링크 68 공급, 링크 68 출구는 온램프 10646/10681 뿐).
3. `config_overrides` 는 `_deep_update` 라 dict 가 **병합**된다. `urban_link_storage_veh` 에
   구 격자 25개가 유령으로 남아 용량만 부풀린다(점유는 항상 0). 0 으로 명시 무력화해야 한다.

**"core15" 는 UF ID 다.** 사용자가 말한 "1~16 중 11 제외 15개"가 곧 `core15` selector 이고,
그건 **Urban Follower ID** 지 SC 번호가 아니다(생성기 L37-39, 2026-07-31 정정 이력).
core15 -> SC [1,5,6,11,12,101,105,107,108,109,1001,1002,1003,1004,1005] 로 **SC1001·SC1004 가 둘 다 들어 있다.**
SC 번호로 1~16 을 골랐다면 인터페이스 둘이 빠졌을 것이다.

**교차로 간 연결.** `scripts/derive_intersection_adjacency.py` 신설 —
정지선 링크에서 커넥터 그래프를 하류로 훑어 처음 만나는 다른 SC 를 인접으로 본다.
방향성 인접쌍 116개, 평균 차수 3.2, 고립 0. 차수 최대는 SC1004 의 7 이다.

leg 방위 배정이 문제였다. 실제 도로망이 격자가 아니라 한 방위에 이웃이 둘 이상 붙는다.

| 방식 | leg 로 표현 | 보존율 |
|---|---:|---:|
| 4방위 단일이웃 | 95/116 | 81.9 % |
| 8방위 단일이웃 | 103/116 | 88.8 % |
| **8방위 + '방위_이웃' 복합 키** | **116/116** | **100 %** |

버려지던 13쌍 중 10쌍이 인터체인지 클러스터라 4/8방위 단일이웃은 쓸 수 없었다.

**모델 코어 수정** (`NumSim-mine/src/models/grid_topology.py`, 이 파일 하나뿐).
- `LEG_DIRECTIONS` 8방위, `OPPOSITE_LEG` 대각 4쌍, `NS_AXIS = {N,S,NE,SW}`.
  2-phase 는 유지하고 **축 방위각**으로 묶는다 — 축각 [45°,135°) 는 세로축에 가까우니 p1.
- `leg_base_dir()` 신설: `'N_SC1002' -> 'N'`. 접두사가 알려진 방위가 아니면 키 전체 반환(하위호환).
- 직진 유도: 정반대 **방위**를 가진 leg 후보를 모아 균등 분배(단일 후보면 구 동작과 동일).
- `_token_leg_dir(token, legs)`: 램프 leg 키를 하드코딩 `"S"` 대신 실제 키로 탐색.
  실제 토폴로지에서는 S 가 이미 인접 도로에 쓰여 램프를 다른 방위에 심어야 하는 노드가 생긴다.

**생성기 수정** (`scripts/generate_real_world_distributed_players.py`).
- `--sc1-coupling {auto,on,off}` — 결합을 selector 이름에서 분리(auto=기존 규칙, 하위호환)
- `--ramp-interface-sc` — 램프->SC 귀속 표. 기본 `R_D_*:1001, R_F_*:1004`
- `--adjacency-json` — 인접을 `type: grid` leg 로 심는다(관대 대칭화)
- `--slug` / `--stamp` — 기존 산출물 미덮어씀
- 통제(rows) + 비통제(monitor_rows)를 **같은 모델로** 세우고 `uncontrolled_nodes` 로 내보낸다
- `urban_movements`/`turning_ratios`/`on·off_ramp_to_movement` 를 **비워 보내 모델이 자동 유도**하게 했다
  (수동 나열은 저장소가 금한다). 주의 — 하나라도 채워 보내면 `if not self.urban_movements` 가
  막혀 **나머지 전체 유도가 억제된다**(한 번 물렸다).

**결과.** 노드 36, leg = grid 126 + boundary 108 + ramp 2, `urban_movements` **1,406**
(통제 734 / 비통제 672), 저류 267(내부 directed link 140 포함).
램프 결합도 인접을 타고 확장됐다 — R_D_W 가 SC1001 의 5개 approach, R_F_W 가 SC1004 의 7개에서 유입.

**회귀.** 매 수정 후 default.yaml 4방위 격자가 비트 동일함을 확인했다(movement 78, storage 29, 램프 결합 동일).

## 2026-08-05 — 교차검토가 오늘 성과 여럿을 무너뜨렸다

사용자 요청으로 5차원 독립 검토 + 적대적 반증 워크플로를 돌렸다(총 50건 지적).
**내가 보고했던 수치 상당수가 측정 인공물이었다.** 아래는 그중 내가 직접 재확인한 것만 적는다.

### spillback F1 0.031 -> 1.000 은 개선이 아니다 (확인)

`g6_records.jsonl` 72개 전부 (예측, 관측) = (True, True), TP=72 / TN=FP=FN=0.

검토 에이전트는 "유령링크를 용량 0 으로 무력화한 것과 `spillback_flag` 의 `max(cap,1e-9)` 가
충돌해 항상 참"이라고 진단했고 나는 그것을 그대로 옮겨 보고했다. **그러나 틀렸다.**
`g6_core.spillback_flag` 에 용량 0 건너뛰기를 넣고 재채점해도 **F1 은 1.000 그대로**다.

실제 원인은 **용량 과소**다. `SC1001_to_SC1004` 의 모델 용량이 120 대인데
(오프램프 기본값 120 이 내부 링크에 잘못 붙었다) 물리 용량은 8,896 대다. 그래서 그 링크
하나가 모든 상태에서 v/c = 1.000 이고, 예측·관측 양쪽 다 무조건 spillback=True 가 된다.

→ **교훈 반복.** 검토 에이전트의 진단도 확인 없이 옮기면 안 된다. 오늘만 두 번째다.

### 포착률 45.9 % 는 목적함수가 쓰는 값이 아니다 (확인·수정 완료)

`scripts/verify_urban_topology_merge.py` 가 `objective_urban_vehicles(net, False)` 로
`exclude_boundary_legs=False` 를 하드코딩하고 있었다. 그러나 `leader._state_accumulation_base`
(leader.py:767)는 `cfg.leader.state_accumulation_exclude_boundary_legs`(기본 True)를 쓴다.

| | boundary leg 포함 | **목적함수 기준** |
|---|---:|---:|
| 15SC 독립섬 | 37.6 % | **17.4 %** |
| 36SC 연결형 | 45.9 % | **20.2 %** |

스크립트를 리더 설정을 읽도록 고치고 두 값을 다 찍게 했다.

### H=1 에서 오히려 퇴행했고 매크로평균이 가렸다 (검토 지적, 미재확인)

obsfix -> urban36 에서 H1 은 rho 0.789 -> 0.438, pairwise 1.000 -> 0.000 이고
H5/H10/H15 만 좋아졌다. **H=1 이 실제로 집행되는 지평**이다.
축별 부호도 H=900 만 봤는데 H=600 에서는 ramp 3/6, green 1/2 로 더 나쁘다.

### rho 비교는 사과와 오렌지가 맞다 (검토 지적, 미재확인)

`g6_core.py:235-236` 이 `score_cfg = deepcopy(cfg)` 후 `objective_mode` 만 덮으므로
**채점 네트워크가 모델 네트워크와 같은 객체**다. 토폴로지를 바꾸면 J_vissim 도 같이 바뀐다.
또 `decision_count=4` 는 독립 표본이 아니라 단일 시드·단일 앵커의 지평 4개다.

### 그 외 검토 지적 (미재확인, 요확인)

- v7 생성기가 내부 구간 93개 중 **81개를 조용히 버린다**(storage_keys 필터). 12/93 만 달성.
- v7 follower solve 가 **156 초** — 제어주기 60 초 초과로 폐루프 불가.
  대응: `real_world_modi_pstack_v8_urban36_budget_20260805.json` 작성(후보 49->9, nash 10->4,
  PSO 18/24->6/8). 분산 config 가 이 문제 크기용으로 이미 줄여 둔 값인데 "flagship 과 충돌"로
  안 가져온 것이 오판이었다. `follower_solver_mode`/`allocation_mode` 는 여전히 안 가져온다.
- 경계 게이트 수가 토폴로지 부산물인데 수요는 게이트당 주입 — v6->v7 에서 외생 도시부 수요 1.8배.
- `assign_links_to_players.py` 의 BFS 가 `defaultdict(set)` 순회라 **실행마다 결과가 달라진다**.
- leg 방위를 링크 **시작점**으로 계산해 32.7 % 가 틀리고 정반대 접근로가 한 저류로 합쳐진다.
- 8방위를 2-phase 로 접으면 같은 phase 에 상충하는 두 축이 동시 녹색이 된다.
- 직선거리 비율로 직렬/병렬을 가르는 판정(사용자 제안)은 **통계적으로 거의 무정보**로 나왔다.

### 살아남은 것

모델 코어 8방위 확장은 기계적으로 정합하다. 4방위 격자가 movement 키 순서까지 비트 동일,
36교차로 238개 approach 의 β 합 오차 0.0, 이름 충돌·중복 0.
`_token_leg_dir` 수정은 **선택이 아니라 필수**였다 — HEAD 코드는 36노드 config 에서
`KeyError 'S'` 로 아예 돌지 않는다(SC1001 의 램프 leg 가 'N' 이라서).
유령 25개를 용량 0 으로 두는 것 자체는 무해하다(소비처 전수 확인, 전부 max(0, cap-avail) 형태).

## 미해결 / 다음 세션 주의

- `leader_value_depth = 3` 은 튜닝 JSON 이 아니라 **어댑터 코드**(`flagship_config_overrides()` L1105)가
  주입한다. 튜닝만 보고 0 이라고 판단하면 틀린다(내가 한 번 틀렸다).
  이 값이 0 이 되면 `stackelberg_mpc.py:2366` 게이트가 닫혀 far 가 통째로 빠진다.
- `core.build_runtime` 은 튜닝의 `calibration_override` 를 적용한다.
  `ad.profiled_demand_rates` 를 직접 호출하면서 원본 캘리브레이션만 넘기면 값이 달라진다.
- `observable_links` 는 base 매핑 22개, **분산 15core 매핑 175개**로 다르다.
  G6 그리드는 분산 매핑을 쓴다. 예전 보고서의 "접근링크가 관측 밖" 서술은 base 기준이라 과했다
  (링크 32 는 분산 매핑에 있다).
- `leader_hinge_enabled` 는 기본 False 이고 튜닝 체인 어디서도 안 켠다 —
  `leader_hinge_cost` 호출은 무조건 실행되지만 즉시 0 을 반환한다. 이미 죽은 항이다.
- VISSIM 배치는 **한 번에 하나만**. `run_real_world_single_watchdog.ps1` 의 Kill-Vissim 이
  모든 VISSIM200/cscript 를 죽여서 병렬 배치가 서로를 죽인다(2026-08-04 실제 사고).

---

## 2026-08-05 — 용량 유도 / solve 실측 / 교차검토 종합

### solve 시간 (진입점 `controller.decide_with_info(state, forecast, previous, cfg)`)

| 조건 | solve | 60s 주기 |
|---|---:|:-:|
| v6 (15SC) | 17.0 s | OK |
| v7 (36SC) | 77.0 s | 초과 |
| v8 (36SC, 예산 축소) | 60.6 s | 초과 |

후보를 49->9 로 5.4배 줄여도 77->60.6 (21%) 밖에 안 준다. 프로파일 결과 병목이
리더 탐색이 아니기 때문이다.

| 구간 | 누적 | 비중 |
|---|---:|---:|
| `_maybe_refresh_signal_prices` | 162.7 s | 77 % |
| ↳ `_offset_price_relinearize_walk` | 84.1 s | 40 % |
| `decide_with_info` (MPC 본체) | 48.3 s | 23 % |

가격 갱신이 전역 롤아웃을 83회 돌린다. movement 68->1406 (20.7배)로 롤아웃 단가가
뛴 것이 그대로 곱해졌다. **후보 수 축소로는 못 푼다** — 가격 갱신 주기가 레버다.
잎 최다 호출은 `_phase_green_fraction` 612만 회(spec 에서 `phase` 만 읽으므로
(phase, step_idx) 메모이제이션이 순수 항등). 아직 미적용.

### 용량 유도 — 방위 조인 결함과 수정

처음엔 (SC, leg방위) 로 묶어 인접표와 방위로 조인했다. **성공률 126쌍 중 79쌍(63%)**.
원인은 방위를 두 번 따로 계산한 것 — 인접표는 교차로-교차로 벡터, 배정은 링크 기하.
굽거나 편심인 접근로에서 어긋난다. 실패한 47쌍이 경계 저류로 새면서 "인접 없는 방위
47개" 로 보고됐는데 그건 정상 결과가 아니라 조인 실패의 증상이었다. 게다가 7쌍은
이웃이 여럿인데 복합키가 접히며 덮어써졌다.

수정 — `assign_links_to_players.py` 가 owner 를 구할 때 쓴 커넥터 그래프를 **뒤집어**
상류 SC 를 직접 구하고(`link_upstream`, 248/367 확정), 용량 스크립트는 방위를 경유하지
않는다. 내부 저류 79 -> **99개**, 인접표 93쌍과 독립 대조해 76개 일치(82%).

### 정정 — "SC1001_to_SC1004 물리 8,896 대 vs 모델 120 대" 는 틀렸다

방향을 뒤집어 잰 값이었다. 6,646 m 회랑은 반대 방향 `SC1004_to_SC1001`(2,816대)이고,
실제 `SC1001_to_SC1004` 접근로는 링크 70·71 의 421 m, **유도 143.5 대**로 현행 120 과
거의 같다. 따라서 **용량을 고쳐도 spillback F1 = 1.000 은 안 풀린다.**

### 정정 — 용량이 포착률 병목이라는 예상도 틀렸다

저류 132 -> 224개, 유효 용량 52,200 -> 57,590 으로 올렸는데 포착률 20.2 -> **20.7%**,
비영 저류 56 -> 57/271. 어댑터 `min(capacity, ...)` 절단이 원인이 아니었다. 목적함수가
제외하는 boundary leg 가 2,292 중 1,268 을 쥔 것이 실제 구조다. 둘 다 `--min-capture`
0.25 미달로 **36노드 토폴로지 작업은 아직 검증 게이트를 통과하지 못했다**.

### NS_AXIS 대각축이 반대였다 (2026-08-04 8방위 확장 시 유입)

`NS_AXIS = {"N","S","NE","SW"}`. "축각 mod 180 이 [45,135) 면 남북축" 기준 자체는
맞지만 NE/SW 를 45° 로 가정한 것이 틀렸다. 개포동 격자가 좌표축에서 15~37° 돌아가 있다.

| leg | 실측 축각 | 실제 축 | 현행 |
|---|---:|---|---|
| NE | 36.1° | 동서 | 남북 ✗ |
| SW | 37.2° | 동서 | 남북 ✗ |
| NW | 122.2° | 남북 | 동서 ✗ |
| SE | 121.6° | 남북 | 동서 ✗ |

**현행이 맞는 대각 leg 0개, 뒤집으면 76개.** 45° 동률처럼 보인 것은
`derive_intersection_adjacency` 의 22.5° 이산화 산물이다. `{"N","S","NW","SE"}` 로 수정.
재생성 결과 movement **287개(20.4%)** 가 phase 를 옮긴다(p1->p2 174, p2->p1 113).

모델 테스트는 이걸 못 잡는다 — `default.yaml` 에 대각 방위 문자열이 **0건**이라
4방위 격자에서는 대각 원소를 조회조차 안 한다(=기존 회귀는 비트 동일). 그래서 검증을
`scripts/verify_phase_axis_assignment.py` 로 VISSIM 쪽에 뒀다.
회귀 규율 확인: 작성 -> PASS(116/116) -> 수정 되돌림 -> **FAIL(34.5%)** -> 복원 -> PASS.

### 교차검토(에이전트 26개, 확정 17건)에서 남은 미해결

- **H=1 퇴행이 최우선** — rho 0.4378, pairwise **0.000** (H=5/10/15 는 0.985/0.921/0.862).
  MPC 는 첫 구간만 집행하므로 폐루프를 좌우하는 지평이 여기다. 매크로 평균 0.8015 가
  이 퇴행을 흡수하고 있다.
- **G6 게이트는 여전히 FAIL** — `top_action_pairwise` 0.75 < 0.80. PASS 로 바뀐 것은
  `spillback_f1` 하나뿐이고 그건 TP=72/TN=FP=FN=0 인 상수 라벨 인공물이다.
  `shadow.py:255-271` 은 전부 음성일 때만 NOT_EVALUATED 를 내고 전부 양성이면 통과시킨다.
- **rho 체인은 A/B 가 아니다** — -0.080 -> +0.7135(obsfix) -> +0.8015(urban36).
  `score_cfg` 가 `cfg` 의 deepcopy 라 채점망이 곧 모델망이고, 이 설계에서는 측정 변경과
  모델 개선을 원리적으로 분리할 수 없다.
- **SC1004 major/minor 가 램프 채널에서 반대** — `major_maps_to=p2` 인데 모델은 오프램프
  접근 movement 18/18 을 p1 에 둔다(NS_AXIS 수정 후에도 그대로 — 램프 슬롯이 "S" 라
  이 수정이 안 닿는다). 플랜트 F측 방류 정지선 link 71 은 EW=MAJOR 로 75초를 받는데
  모델은 25초를 준다. `context-notes.md:176` 의 "SG2 는 minor 라 축이 우연히 맞는다"
  메모는 **사실과 반대**이며 여기가 결함을 통과시킨 지점으로 보인다.
- **램프 leg 슬롯이 임의 배정** — `generate_...py:337` `slot = "S" if "S" in free else free[0]`.
  SC1001 램프 소스 링크 31/32 는 실제 W 방위 1,040 m 인데 W 가 비어 있었는데도 N 을 집었다.
  결과로 on-ramp β 질량 1.9028 -> **3.9500 (2.08배)**. 회귀를 보존하는 수정은
  "램프 leg 방위를 VISSIM 링크 좌표에서 유도" 하는 쪽뿐이다(straight_keys 제외안은 회귀를 깬다).
- **phase 확장은 채택 금지** — VBS `SignalStateForGroup`(`run_real_world_stackelberg_controller.vbs:893-907`)
  이 EB*/WB* 를 전부 major, NB*/SB* 를 전부 minor 로 보내 런타임 2그룹으로 덮는다.
  모델의 2-phase 는 플랜트에 실제 적용되는 제어를 반영한 것이다. 진짜 비대칭은 플랜트
  conflictArea 1,819개가 모델에 0개인 것이고, 권고는 교차로/상충군 단위 포화유율 캡.
- **준-U턴 β 누출** 1.78% (238 approach 중 37개). 원인은 U턴 배제가 정확 키 비교인 것
  (`grid_topology.py:129`)이고, 정확 키로 되돌리는 안은 누출을 오히려 키운다(0.0178 -> 0.0280).
- **새 튜닝 config 에 유령 저류 0 처리가 없다** — 구 6노드 격자 잔존(`A_to_B` 등) 25개가
  용량 0 에서 양수로 돌아왔다. 생성기가 유령을 명시적으로 0 으로 깔아야 한다.

### 이번 세션 산출

- `scripts/verify_phase_axis_assignment.py` (신규)
- `scripts/derive_urban_storage_capacity.py` — 상류 조인으로 교체
- `scripts/assign_links_to_players.py` — `link_upstream` 추가
- `scripts/generate_real_world_distributed_players.py` — `--storage-capacity-json`
- `NumSim-mine/src/models/grid_topology.py` — `NS_AXIS` 정정
- 산출물 슬러그: `core15cap`(용량만), `core15axis`(용량+축 수정)

### 2026-08-05 (2) — 귀속 기준 100% 달성 + 라우팅 수정

**포착률 지표들의 정체.** 세 숫자가 재는 대상이 다르다.
- 88.8% = 인접쌍 **보존율**(116쌍 중 leg 로 표현되는 비율). 차량과 무관. 게다가 그 안은 채택 안 함(복합키 100%).
- 86.7% = 분할 **커버리지**(도시부 차량 중 플레이어 귀속 링크 위 비율).
- 20.7% = 그게 **목적함수까지 살아남는** 비율. 사이에 관측 허용목록과 경계 오분류가 있다.

**커넥터가 분할에서 빠져 있었다.** VBS 는 RW_CLASSIFY_UNMATCHED_AS_URBAN=True 라 커넥터 위
차량도 urban_vehicles 에 넣는데, assign 은 `not is_connector` 로 걸러 냈다. 실측 결과
교차로 커넥터 426개가 359 대(8.7%) — 분모에는 있고 분자에는 없었다.

**분류를 목적지 종류로 바꿨다(사용자 확정).**

| 하류로 훑어 처음 만나는 것 | 귀속 |
|---|---|
| 신호 정지선 | 그 플레이어 (approach queue) |
| 고속도로 링크 | **freeway follower** (기존엔 '출구'로 섞였다) |
| 아무것도 없음(종단) | 출구, 모니터링 전용 |

함정 — 커넥터를 urban 에 넣기만 하면 안 된다. `downstream` 이 fl->tl 로 커넥터를 **건너뛰어**
만들어져 있어서 커넥터에 진입 간선이 없었고, BFS 가 즉시 끊겨 836개가 전부 '출구'가 됐다.
`downstream[fl].add(커넥터); downstream[커넥터].add(tl)` 로 커넥터를 노드로 넣어야 한다.

결과 (링크 1,204 = 커넥터 포함, 고속도로·램프미터커넥터 제외).

| 구분 | 링크 | 대수 | 도시부 대비 |
|---|---:|---:|---:|
| 도시부 플레이어 | 952 (일반 359 + 커넥터 593) | 3,761 | 90.8 % |
| freeway follower | 26 (일반 8 + 커넥터 18) | 169 | 4.1 % |
| 출구(모니터링) | 226 (일반 77 + 커넥터 149) | 212 | 5.1 % |

**귀속 분모 3,930 에 대해 3,761 + 169 = 3,930, 정확히 100%.**
부수 확인 — 일반 링크 8개가 하류가 고속도로인데 도시부 approach 로 잘못 세고 있었다.

**link_to_origins 를 상류 기준 권위 라우팅으로 교체.** 기존 585~595행은 소유 링크마다
`{sid}_{leg}_out` 을 N/S/E/W **네 개 전부** 박았다(기하 무관 살포, 전부 경계 sink).
실측: 경계 sink 로 가는 관측 링크 66개 중 65개가 배정 링크, 그중 53개는 모델에 내부 링크가
있는데도 샜다. SC15/SC107/SC9002/SC2 -> SC1 네 접근로가 전부 SC1_N_out 으로 접혔다.
리더가 경계 leg 를 설계대로 빼므로 제어 가능한 approach 651 대가 목적함수 밖으로 나갔다.
이제 `SC{상류}_to_SC{owner}`, 상류 없으면 `SC{owner}_{leg}_out`. 952개 전부 라우팅, 탈락 0.

경계 저류도 필터에 추가해야 했다 — 351행은 **이웃이 있는 방위만** `_out` 저류를 만들어서,
진짜 유입구(이웃 없는 방위)에 저류가 없어 224개가 탈락했었다.

**효과 (옛 state, 아직 175링크만 관측).**

| | v7 기존 | full 상류라우팅 |
|---|---:|---:|
| 포착률(목적함수) | 20.2 % | **40.4 %** |
| 투영 도시부 | 997.0 | 1,998.8 |
| 경계 leg 분 | 1,273.1 | **626.4** |
| 비영 저류 | 56/271 | **116/327** |
| 용량 0 유령 | 25개 | **0개** |

`--min-capture 0.25` **RESULT PASS**.

**VBS 코드 변경은 불필요.** `LocalObservationLinkCountsJson` 이 허용목록으로 거르는 건 맞지만
그 목록이 생성물이다. core15full 의 `RW_LOCAL_OBSERVABLE_LINKS` 는 이미 **1,201개**라
다음 런부터 전 링크 count 가 나온다. 이전엔 목록이 짧았을 뿐이다.

**유령 저류 29개(default.yaml 6노드 격자)는 무해 확인.** movement 참조 0, detector origin 참조 0.
점유가 항상 0 이라 spillback 도 안 걸린다. `D_R_*`/`OR_*_storage` 는 램프계 이름이라
일괄 0 처리는 오히려 위험 — 그대로 둔다.

**검증 분모 변경.** `--link-assignment-json` 주면 분모 = urban - 출구링크 차량(귀속 기준).
출구가 하나도 관측 안 되면 분모 과대라 경고를 낸다.

**다음.** core15full 로 VISSIM 1회 런 -> 1,201 링크 state 로 실제 포착률 재측정.
산출물: `control_mapping_distributed_core15full_20260805.json`,
`detector_local_mapping_distributed_core15full_20260805.json`,
`real_world_modi_pstack_distributed_core15full_20260805.json`,
`run_real_world_single_watchdog_distributed_core15full.ps1`

### 2026-08-05 (3) — 전 링크 관측 런 + 도시부/고속도로 포착률

런: `capture_core15full_c00_seed13` (diagnostic-fixed57, seed 13, 3000s, 200초 소요).
`link_counts` 175 -> **1,201개**. 합 3,162 = urban 2,252 + freeway 943 + ramp 33 (정합).
출구 링크 226/226 전부 관측 -> 분모 2,252 - 134 = **2,118**(귀속 기준).

**포착률 (최종).**

| | 값 | 비고 |
|---|---:|---|
| 도시부 (목적함수 기준) | **83.5 %** | 경계 leg 제외 후 |
| 도시부 (투영 기준) | 95.3 % | 경계 포함 2,018.8/2,118 |
| 고속도로 | **100.0 %** | 943/943, 잔차 +0.0 |

고속도로는 세그먼트 count -> density -> count 왕복이라 체인이 링크를 다 덮으면 100% 다.
**100% 를 벗어나면 관측 누락이 아니라 길이·차로 프로파일 불일치**를 뜻한다 — 도시부와
의미가 다르므로 그렇게 표기했다. 이탈 2% 초과면 FAIL.

**전 링크 관측만으로는 50.7% 에서 멈췄다. 두 결함이 더 있었다.**

1. **movement 매핑 없는 링크의 queue 분이 증발.** 투영은 링크 대수를 저류분/큐분으로
   쪼개고 큐분을 `link_to_movements` 로 배분하는데, 매핑이 없는 링크는 그 루프를 아예
   안 돈다. 실측: 관측된 배정 링크 952개 중 **882개가 매핑 없음, 1,415 대**. 그 882개는
   신호두 링크가 아니라 링크 본체라 물리적으로도 저류가 맞다.
   -> `vissim_stackelberg_adapter.py`: 매핑 없으면 `storage_fraction = 1.0`.

2. **고속도로 본선이 도시부 저류로 흘러들었다.** `internal_link_members` 는 커넥터
   **경로 기반**이라 SC 사이 경로가 고속도로를 타면 본선 링크까지 멤버로 넣는다
   (`SC1001_to_SC1004` 멤버 = 2, 26, 31, 70 — 2와 26이 고속도로). ⑴을 고치자
   링크 2(178대)·26(510대)의 **688 대**가 도시부 저류로 쏟아져 포착률이 **114.6%** 로
   100% 를 넘었다. 100% 초과가 아니었으면 못 잡았을 결함이다.
   -> 생성기: 도시부 분할 밖(owner/출구/freeway행 어디에도 없는) 링크의 origin 을 제거.

**주의 — 과거 G6 점수와 비교 불가.** ⑴은 어댑터 투영을 바꾸므로 모든 config 의 투영이
달라진다. 재채점 필요.

**남은 것.** 경계 leg 251 대(11.8%)가 여전히 목적함수 밖이다. 이제 대부분이 `boundary_in`
movement 큐다(sink 저류는 651 -> 7.7 로 이미 해결). 어떤 플레이어의 approach 에 서 있는
차를 빼는 게 원래 의도(외부 네트워크 제외)에 맞는지 판단이 남았다.

### 2026-08-05 (4) — 신규 SC 5개 반영 + 램프 저류 유도

**사용자가 modi_eval_rw_control.inpx 에 SC2001~2005 추가** (UF13/14 북쪽 간선, 각 SG 8개,
신호두 링크 3~4개짜리 정상 교차로. 미드블록 아님). active 37 -> 42.
인벤토리 백업: `evaluation/real_world_modi_inventory/_backup_20260805/`.

**첫 런이 전멸했다 — 원인은 네트워크의 끊긴 경로였다.**
증상: `actual_sim_sec=0` 고정, 차량 0, `FAILED_SET_SIGSTATE` 28,056건.
`ContrByCOM`/`SigState` 실패를 원인으로 의심했으나 **결과**였다 — 시뮬이 안 도니 신호를 못 건드린 것.
진짜 원인은 `network/real_world_gaepo_modi/modi_eval_rw_control.err` 에 있었다.
```
Error   Static Vehicle Route 1157 - 3 is not complete.
```
경로결정 1157(링크 117, SC2005 신호두 링크)의 route 3 링크열이 비어 있었다.
VISSIM 은 불완전 경로가 하나라도 있으면 시작 직후 시뮬을 중단·리셋한다.
격리 방법 — 옛 config(core15full)를 새 네트워크로 돌려 동일 증상 확인 -> 네트워크 탓 확정.
**교훈: 런이 이상하면 `.err` 부터 읽는다. VBS 로그의 실패는 후속 증상일 수 있다.**
(링크열이 빈 경로 14개는 정상이다 — 옛 정상 네트워크도 14~15개. 직결 경로는 중간 링크가 없다.)

**41노드 최종 포착률** (state_002700, urban 2657 / freeway 980 / ramp 56).

| | 값 |
|---|---:|
| 도시부 (목적함수 기준) | **76.8 %** (분모 2,489 = 2,657 - 출구 168) |
| 도시부 (투영 기준) | **96.3 %** |
| 고속도로 | **100.0 %** |

83.5 -> 76.8 은 퇴행이 아니라 네트워크 변경이다. 신호 5개가 새로 생겨 대기행렬이 실제로
생겼고 경계 leg 분이 251 -> 486 으로 늘었다. 투영 기준은 95.3 -> 96.3% 로 올랐다.

**램프미터 신호두 이동(사용자).** 램프 시작 -> 끝(길이의 98~99%). 커넥터 ID 는 그대로라
`RW_RAMP_METER_CONNECTORS` 는 유효. 다만 큐가 커넥터 전체에 쌓이게 되어 저류 용량이 중요해졌다.

**램프 저류 유도** — `scripts/derive_ramp_queue_capacity.py` 신설.
커넥터 2개가 모델 램프 1개에 붙는데 실측 **병렬**이다(R_D_W: 10480<-31, 10482<-32) -> 합산.

| 저류 | 기존 | 유도 |
|---|---:|---:|
| SC1001_R_W | 180 | **128.0** |
| SC1001_R_E | 180 | **93.0** |
| SC1004_R_W | 180 | **145.9** |
| SC1004_R_E | 180 | **128.4** |

실제로 쓰이는 것은 on_ramp receiving 저류 `SC{sc}_R_{dir}` 4개다.
`SC1001_R_D_W_queue`(180) / `OR_D_W_storage`(120) 는 **참조 0개인 유령**이라 안 건드렸다.

**미해결 — `ramp_queue_max_veh` 가 스칼라 180 이다.**
리더 `_ramp_queue_pressure`(leader.py:757)가 램프별 구분 없이 이 하나로 정규화한다.
유도 실제값은 93.0~145.9(평균 123.8)라 가장 좁은 SC1001_R_E 에서 **1.9배 과소평가**한다.
`_ramp_queue_pressure` 가 `state.ramp_queue.values()` 로 키를 버려서 램프별로 못 나눈다.
고치려면 ramp key -> 저류 이름 매핑이 필요하고(on_ramp movement 의 ramp/receiving_link 로 가능),
리더 목적함수가 바뀌므로 G6 재채점이 따라온다.

### 2026-08-05 (5) — 램프 큐 상한 램프별 정규화

**스칼라 `ramp_queue_max_veh`(180)가 리더 압력항만이 아니라 물리를 지배하고 있었다.**
`f1_wu_faithful_follower:517` 의 `min(cap, q+adm)`, `freeway_follower:432` 의
`state.ramp_queue[ramp] = min(cap, ...)` 가 전부 이 스칼라를 큐 상한으로 쓴다.
리더만 고치면 **리더는 93 에서 꽉 찼다고 보는데 팔로워는 180 까지 채우는** 불일치가 생긴다.

**설계.** `NetworkConfig.ramp_queue_max_veh_by_ramp: Dict[str,float]`(기본 빈 dict) 신설 +
`NetworkConfig.ramp_queue_cap(ramp)` 헬퍼. **비어 있으면 스칼라 폴백이라 기존 비트 동일.**
`ramp_capacity_veh_h` 가 이미 램프별 dict 라 그 선례를 따랐다.

**적용 지점 (ramp 키가 스코프에 있는 곳 전부).**

| 파일 | 건수 | 성격 |
|---|---:|---|
| leader.py `_ramp_queue_pressure` | 1 | `.values()` -> `.items()` 로 램프별 정규화 |
| f1_wu_faithful_follower.py | 3 | 큐 상한 = 물리 |
| freeway_follower.py | 3 | 큐 상한 + overflow 집계 |
| distributed_coordinator.py | 4 | ramp_space, agent 용량 합, overflow 카운트 |
| classical_hierarchical.py | 3 | 압력 비율 |

agent 단위 합계는 `sum(cap(r) for r in agent.ramps) if agent.ramps else scalar` 로 바꿨다.
기존 `scalar * max(len,1)` 과 매핑이 비면 정확히 같다.

손대지 않은 곳 — `urban_follower.py:94,213,474` 와 `spillback_constraints.py:23` 은 램프 키가
없고 값을 **일반 크기 척도**로 쓴다. 램프별로 바꿀 의미가 없어 스칼라를 유지했다.

**효과 (state_002700).**

| 램프 | 큐 | 상한 구->신 | 압력 구->신 |
|---|---:|---|---|
| R_D_W | 11.0 | 180 -> 128.0 | 0.061 -> 0.086 |
| R_F_W | 26.0 | 180 -> 145.9 | 0.144 -> 0.178 |
| **R_D_E** | 11.0 | 180 -> **93.0** | 0.061 -> **0.118 (1.94배)** |
| R_F_E | 8.0 | 180 -> 128.4 | 0.044 -> 0.062 |
| 평균 | | | 0.078 -> 0.111 (**+42.9%**) |

**검증.** 램프 관련 테스트 4파일: 43 passed, 1 failed.
그 1개(`test_wu_faithful_follower::TestLambdaDualIntegralUpdate::test_commit_green_equals_last_consensus_sweep`)는
**변경을 되돌려도 동일하게 실패** -> 기존 실패 확정(`set(last_p1)` 이 비는 문제, 램프와 무관).
기본 NetworkConfig 에서 `ramp_queue_cap` 이 전부 스칼라 180 을 돌려주는 것도 확인.

**배선.** `derive_ramp_queue_capacity.py` 가 `ramp_queue_max_veh_by_ramp` 를 용량 JSON 에
같이 내고, 생성기가 `--storage-capacity-json` 에서 읽어 network override 에 싣는다.

---

## 2026-08-07 — 계획 v3 채택과 토폴로지 해시 고정

`IMPLEMENTATION_PLAN_V3_LEAN.md` 를 활성 계획으로 채택했다. v2.1 은 참조용으로 보존한다.
축소 근거와 원복 조건은 v3 서두에 있다.

### 토폴로지 정본 해시 (v3 N0)

실 네트워크 `network/real_world_gaepo_modi/modi_eval_rw_control.inpx` 에서 컴파일한 결과다.
**산출물 자체는 커밋하지 않는다**(42 MB, 결정적 재생성 가능). 이 해시가 정본이다.

**N0-1/N0-2/N0-3 완료 후 확정값이다 (2026-08-07). 여섯 개 전부 `status=PASS`.**

| 산출물 | SHA-256 | 요약 |
|---|---|---|
| `runtime_source_v2_1.json` | `1b324b24e6688e8379e37d47a18016d1888b88ace30aa028fd560770e4cb76fc` | PASS (`RW_PYTHON_EXE` 필요) |
| `preflight_manifest_v3.json` | `5bb43d775209b4102c0d7642662e03f5ed9be8a4ac6fbd2d7f508c64a3ae2674` | PASS, reasons 0 |
| `lane_route_graph_v2_1.json` | `100245c8302fb11b51908bdfdd84e54686c7bc19669b0db01e54b804fa939381` | PASS, 차로 2,649 / 엣지 2,792 / 커버리지 1.000 |
| `lane_route_proofs_v2_1.json` | `0a7cc5b6b8363da60f42a538c020a5a2cb8a735fc41a1fccd6e21e85f062788a` | PASS, 경로 339 / 증명 2,684 / 미해결 0 / 유량오차 1.11e-16 |
| `physical_stock_topology_v2_1.json` | `8548d529ad3bc0b31846e8aca5d076f3055ec035343a731e903f215fa2d983e8` | PASS, stock 7,275 / edge 7,418 / 전 게이트 0 위반 |
| `topology_approval_v2_1.json` | `f0659a093a386189d8f3ec4fb6d71e0cb234c2d1df22a9a1109b3728b30cc284` | **PASS** (2.2 KB, 커밋 대상) |

**재생성은 반드시 이 순서다.** graph → routes → topology → approval.
승인이 그래프·경로의 **생산자 출처**와 **독립 A2 재현**을 대조하므로, 앞 단계를 갱신하지 않고
뒤만 돌리면 `lane graph producer provenance mismatch` / `topology differs from independent A2 replay`
로 FAIL 한다. 이 세 사유는 preflight 가 PASS 가 된 뒤에야 드러난다(그 전에는 더 앞에서 막힌다).

재생성 명령은 v3 의 N0 절에 있다.

**토폴로지 해시는 N0-2 수정 후 값이다** (2026-08-07). 수정 전은
`ba75101daab882f71ddc037c44db3a07f454751a8a591023ea73dc98a0245195` 였다.
컴파일러가 출력하는 `hash=` 는 **의미 해시**이지 파일 해시가 아니다 — 현재 값은
`a01a4f3362d3705698e53812d04e62a4ea5fa1242b8393765497d7e2e04ab529` 다. 표의 값은 파일 SHA-256 이다.

### N0-2 완료 (2026-08-07)

커넥터 진입 엣지 35건의 `stock edge position mismatch` 를 닫았다.

**원인.** `compile_physical_stock_topology.py` 가 `:1010/:1014` 에서 **허용오차로** 출발/도착 stock 을
찾아 놓고, 기록할 때는 graph edge 의 **원시값**을 썼다. VISSIM 이 커넥터 `Pos` 를 6자리로 저장하고
차로 길이는 좌표에서 전정밀도로 계산되므로 둘이 최대 4.96e-07 m 어긋난다.
`validate_physical_stock_topology` 는 **정확 일치**를 요구한다.
같은 함수의 `lane_continuation`(`:1001/:1004`)은 이미 stock 경계값을 쓰고 있었다.

**수정.** 커넥터 엣지도 `source["end_m"]` / `target["start_m"]` 를 쓴다.
원시값은 `source_graph_edge_id` 로 A1 그래프에서 추적 가능하다.

**검증.** 실 네트워크 위치 불일치 **35 → 0/7418**.
`validate_physical_stock_topology(topo, lane_graph=graph)` 구조 오류 0.
승인의 `topology_structure_invalid` 완전 소멸(남은 것은 v2.2 관련 4건뿐, N0-1 소관).
실네트워크+컴파일러 36/36, plant 132/132.

**주의 — 검증기를 직접 호출할 때는 `lane_graph` 를 반드시 넘겨라.** 생략하면
`physical_projection.py:930-935` 가 `a1_*` 기대 키를 만들지 않아 `sample_dimensions mismatch` 가
난다. 결함이 아니라 호출 방식 문제다.

### N0-1 완료 (2026-08-07)

v2.2 생산자 두 역할을 필수 소스 역할에서 뺐다(12 → 10). **같은 계약이 여섯 곳에 박혀 있었다.**

| 위치 | 조치 |
|---|---|
| `run_evidence.py:86-99` `PRODUCER_SOURCE_ROLES` | 두 항목 제거 |
| `run_evidence.py:100-113` `PRODUCER_SOURCE_DEFAULT_PATHS` | 두 항목 제거 |
| `run_real_world_single_watchdog_...ps1:553` `$sourceBindings` | 두 바인딩 제거 (ASCII 유지) |
| `test_build_preflight_manifest.py:419-441` | FAIL 기대 → PASS 기대로 뒤집음 |
| `test_validate_baseline_snapshot.py:186-196` | 픽스처가 두 역할 파일을 만들지만 통과 |

파이썬만 고치면 워치독이 부재 파일로 throw 하고, 워치독만 고치면
`build_run_manifest_v2_1.py` 의 `producer_sources` **정확 집합** 검증이 거부한다. 함께 바꿔야 한다.

### N0-3 완료 (2026-08-07)

승인 아티팩트가 **PASS** 다. v3 초판이 승인 사슬을 뺀 것은 오판이었고
(`validate_state_projection_v2_1.py:22-26` 이 `validate_approval_artifact` 를 import 한다)
N0-3 에서 되살렸다. 2.2 KB 라 크기 제외 대상이 아니며 **커밋한다.**

### 환경 규약

`verify_runtime_source.py` 는 `RW_PYTHON_EXE` 환경변수를 요구한다. 없으면
`python.rw_python_exe_present/exists`, `python.executable_matches` 3건으로 FAIL 한다.

```powershell
$env:RW_PYTHON_EXE = "C:\Users\alsrj\anaconda3\python.exe"
```

이 저장소의 `runtime_source_v2_1.json` 과 `preflight_manifest_v3.json` 은 원래 Codex 워크트리
(`C:\tmp\vissim-pstack-controller`)에서 생성돼 절대경로가 전부 거기를 가리켰다. 이번에 이
워크스페이스에서 재생성했다.

---

## 2026-08-07 — N1 첫 실 런: 결함 7건과 운영 규칙

**플랜트가 실 차량을 A2 stock 에 투영하는 데 성공했다.** 이 저장소에서 처음이다.

```
sim_sec 1.0   record_count 6   unobservable_count 0   external_source_count 0
veh 1 -> link 55 lane 1 pos 4.605 m 43.2 kph
full_network_link_counts {55:1, 66:1, 74:2, 99:1, 164:1}
```

B1a 가 요구하는 `unobservable_count = 0`, `external_source_count = 0` 을 실 데이터로 만족했다.

### 결함이 층층이 쌓여 있었다

각 결함이 다음 결함을 가리고 있어서, 실 런을 반복해야 한 겹씩 드러났다.

| # | 결함 | 드러난 방식 | 상태 |
|---|---|---|---|
| 1 | 경로 헬퍼 `'\'` 이스케이프 | dry-run `escapes the workspace` | 수정 |
| 2 | stdin BOM | dry-run `UTF-8 BOM is forbidden` | 수정 |
| 3 | VBS 헬퍼 타임아웃 10초 | 실 런 `EXEC_TIMEOUT` | 수정 |
| 4 | COM 고아 프로세스 | `CO_E_SERVER_EXEC_FAILURE` 연쇄 | 운영 규칙 |
| 5 | 어댑터 cp949 | `DECISION_EXIT_NONZERO` 매회 | 수정 |
| 6 | COM 키 == 차량번호 가정 | `com_row_key_mismatch row=7` | 수정 |
| 7 | solve 시간 | `timeout=True`, decision 미완료 | **미해결** |

### 운영 규칙 (반드시 지킬 것)

**`CO_E_SERVER_EXEC_FAILURE` 가 나면 잔여 프로세스를 전부 정리하고 재시도하라.**
실패한 시도가 `VISSIM200` 고아를 남기고, 그 고아가 다음 COM 활성화를 막아 **연쇄 실패**를 만든다.
워치독의 3회 재시도가 전부 같은 이유로 죽는 패턴이 이것이다. 정리 후 첫 시도에 바로 성공했다.
설치·등록·라이선스는 정상이다(직접 실행 시 GUI 기동 확인).

**워치독을 죽여도 자식 파이썬은 죽지 않는다.** 14:49 에 죽인 런의 어댑터가 20분 넘게
CPU 701초를 먹으며 살아 있었고 다음 런과 코어를 다퉜다. 측정 전에 반드시 확인하라.
v3 N8-4 가 요구하는 "고아 워커 0" 계약이 현재 지켜지지 않는다.

```powershell
Get-Process | Where-Object { $_.ProcessName -match "VISSIM|cscript|python" } |
  Select-Object ProcessName,Id,CPU,StartTime
```

### solve 성능 오프라인 재현 (VISSIM 불필요)

캡처된 상태 파일 하나로 어댑터를 그대로 돌릴 수 있다. **반복 측정과 최적화에 이 경로를 쓴다.**

```bash
python evaluation/controllers/vissim_stackelberg_adapter.py \
  --state-json <decisions/state_000001.json> \
  --out-action-json <out.json> --out-action-csv <out.csv> \
  --mapping-json evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core15n41_20260805.json \
  --controller stackelberg \
  --calibration-json evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json \
  --tuning-json evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json
```

**측정: 차량 6대짜리 초기 상태에서 240초를 넘긴다.** 알려진 최악값(H=3, 154.7초)보다 나쁘다.

`faulthandler.dump_traceback_later(60)` 로 잡은 정체 지점 — 두 번의 덤프가 같은 사슬이다.

```
decide_with_info                 stackelberg_mpc.py:546
 _evaluate_fallback_candidates   stackelberg_mpc.py:1791   <- fallback 후보 평가 아래다
  solve                          distributed_coordinator.py:1803
   _structured_grid_refinement   :985
    _evaluate_grid_stage         :947
     evaluate_grid_items         grid_parallel.py:100
      evaluate_item              :925
       _rollout_grid_objective   :673
        run_coupled_interval     coupling.py:180
         urban_substep           urban_queue_model.py:974
          patched_phase_green_fraction  adapter:1328
```

멈춘 것이 아니라 순수 계산량이다(코어 하나 포화). 격자 후보마다 전체 롤아웃을 돌린다.
**본 경로가 아니라 `_evaluate_fallback_candidates` 아래라는 점이 특히 조사 대상이다.**

---

## 2026-08-07 — solve 성능 진단 (v3 N8-4/I-3 로 이월)

**결론 — 탐색 공간 문제가 아니라 롤아웃 내부 비용이다.** 최적화는 N8-4/I-3 에서 다룬다.

### 실측

차량 6대짜리 `state_000001.json` 하나로 단일 decision 을 재현했다(VISSIM 불필요).

| 조건 | 결과 |
|---|---|
| 기본 | 1200초 초과 |
| `grid_parallel_backend: thread` × 8 | 180초 초과 (GIL 이라 무효) |
| `grid_parallel_backend: process` × 8 | 1200초 초과 |
| fallback off + 지평 1 + 후보 1 | **300초 초과** |

마지막 줄이 핵심이다. 탐색 축을 전부 최소로 줄여도 종료하지 않으므로 **비용은 롤아웃 한 번 안에 있다.**

### 프로파일 (150초)

```
523,389,192  dict.get                                     46.9초
   654,056  distributed_coordinator.py:1120 <genexpr>     27.5초
 1,003,889  distributed_coordinator.py:1114 <genexpr>     27.1초
     1,323  _leader_direct_feasible_set_diagnostics(:735)  누적 47.1초
```

`_allocation_control_map`(`:1106`)이 경계 링크마다 전체 movement 를 재순회한다 —
**1,414 movements × 236 boundary links × 2 = 호출당 667,408회 dict 조회.**
`cfg.network` 는 런 중 불변이므로 인덱스를 한 번만 만들면 된다.

**시험 결과 (되돌림): dict.get 523M → 160M, 전체 호출 638M → 403M, 약 31% 개선.**
종료를 만들 크기는 아니었다.

수정 후 재프로파일의 1위는 어댑터 monitor 몽키패치다.

```
2,132,847  fixed_signal_schedule.py:140 _union_green_overlap  19.7초 (누적 30.1초)
4,212,409  adapter:1316 patched_phase_green_fraction          누적 57.2초  (48%)
    2,956  _leader_direct_feasible_set_diagnostics            누적 106.3초 (89%)
```

monitor 노드는 "고정 스케줄, 제어 불가" 라 `(node, group_ids, start_sec, duration_sec)` 에 대해
녹색분율이 런 내내 상수인데 420만 회 재계산한다. `FixedControllerSchedule._green_fraction`
메모이즈가 자연스러운 수정이며 **이 파일은 벤더가 아니라 저장소 코드다.**

`_leader_direct_feasible_set_diagnostics` 는 이름과 달리 진단 출력이 아니다.
7개 지점에서 호출되고 탐색 루프 안에서 시행마다 돌며 `best_diag`/`base_diag` 로 판정에 쓰인다.
끌 수 없고 등가성 증명이 필요하다.

### 구조적 제약 — 벤더 앵커 (선행 과제)

`vendor/NumSim-mine` 은 상류 커밋 `0240ba8` 에 해시로 고정돼 있고
`verify_runtime_source.py` 가 96개 파이썬 blob OID 를 전부 대조한다.
`distributed_coordinator.py` 를 고치자 즉시 FAIL 했다.

```
canonical.anchor_python_blobs / canonical.tracked_source_clean
```

**재스냅샷 도구가 없다.** `UPSTREAM_TREE.json` 을 소비하는 코드만 있고 생성하는 코드가 없다.
NumSim 을 고치려면 **앵커 갱신 파이프라인을 먼저 만들어야 한다.** 이번 시험 수정은 되돌렸고
`verify_runtime_source` 는 PASS 로 복구했다.

### 재현 절차

```bash
# 단일 decision 타이밍
python evaluation/controllers/vissim_stackelberg_adapter.py --state-json <state_000001.json> ...
# 프로파일 (scratchpad/profprobe.py: N초 후 덤프하고 강제 종료)
PROF_SECONDS=150 PROF_DUMP=prof.out python profprobe.py <adapter.py> <같은 인자>
# 정체 지점만 빠르게
python -c "import faulthandler; faulthandler.dump_traceback_later(60, repeat=True)" 방식
```

---

## 2026-08-07 — N1 완주. 플랜트가 실 네트워크 전 구간을 투영했다

`no-control` + audit anchor 로 3600초를 완주했다. MPC 61회 캡처는 solve 시간(N8-4)에
막혀 있으므로, 캡처·투영 자체를 증명하는 경로로 anchor 를 썼다.

```
시점              차량    정지    레코드   미관측  외부   링크수
anchor_000900    2,193    536    2,193      0     0     282
anchor_001500    3,365    873    3,365      0     0     334
anchor_002100    3,776  1,126    3,776      0     0     346
anchor_002700    4,088  1,355    4,088      0     0     334
state_000001         6      0        6      0     0       5
```

**B1a 계약 충족** — `unobservable_count = 0`, `external_source_count = 0`,
`record_count == total_vehicles` 가 5시점 모두에서 성립한다.
`sim=3600` 완주, `observation_failures=0`, `decisions_failed=0`, `signal_failures=0`.

산출물은 `state_000001` + `anchor_000900/001500/002100/002700` 과 각각의
`.vehicle_capture_v2_1.json`, 그리고 `run_manifest_v2_1.json` 및 생성/검증 결과다.
**앵커 캡처는 `state_*` 가 아니라 `anchor_*` 로 저장된다** - 파일을 셀 때 주의.

### 결함 8 — 경계 진입 음수 위치

```
veh_no=16426  VarType 5 (Double)  Pos = -1.49989317546481  (sim_sec 2430)
```

VISSIM 은 차량 기준점이 링크 시작선에 닿기 전에 소유권을 그 링크로 넘긴다. 그래서 혼잡
구간에서 `Pos` 가 잠시 음수가 된다. 데이터 오류가 아니라 실제 경계 걸침이다.
기존 계약 `Pos >= -1e-6` 은 이를 거부해 캡처 전체를 실패시켰다.

**조치** — `B1A_ENTRY_TOLERANCE_M = 8.0`(차량 한 대분) 이내의 음수는 링크 시작(0)으로
클램프하고 `B1A_ENTRY_CLAMPED` 로 매 건을 기록한다. 그 범위를 넘으면 여전히 fail-closed 다.
VISSIM 이 이미 소유권을 넘겼으므로 첫 stock 이 정직한 배정이고, 버리면
`unobservable_count = 0` 계약이 깨진다.

**3600초 전 구간에서 클램프는 단 1건, 1.5 m 였다.** 8 m 관용이 과하지 않음을 실측이 뒷받침한다.

봉투 스키마에 클램프 카운트를 넣는 것은 **미뤘다.** 그 필드는 `physical_projection.py` 의
`_VEHICLE_ENVELOPE_FIELDS` 와 `build_state_manifest_v2_1.py` 가 정확 집합으로 강제하고
테스트 픽스처 4개가 고정한다. 현재는 runlog 기록으로 감사 가능하다.

### 남은 것 — COM 경고 2건 (별건)

```
WARN=FAILED_SET_EVALUATION_ATT att=DatabaseConnection err=module not active
WARN=FAILED_SET_ATT att=SimSpeed value=0 err=Value 0 is lower than minimum
```

시뮬레이션·캡처에 영향이 없으나 `COM_FAILURES=2` 를 만들어 `RUN_INTEGRITY_FAILURE` 를 낸다.
나머지 실패 카운터는 전부 0이다. 이번 변경과 무관한 기존 설정 문제이며
`SimSpeed=0` 은 "최대 속도" 의도로 보이나 VISSIM 2020 이 0을 거부한다.

---

## 2026-08-07 — N2 착수: 대상 확정, RED 미달성 (다음 세션 인계)

### 고칠 지점 (확정)

`vendor/NumSim-mine/src/models/urban_queue_model.py:1022-1032`

```python
for movement, spec in specs.items():
    qmax = _queue_max(cfg, movement, spec)
    q = state.urban_movement_queue.get(movement, 0.0)
    if q > qmax:
        overflow_count += 1.0
        projection_count += q - qmax              # 파괴량을 세기만 한다
        state.urban_movement_queue[movement] = qmax   # 질량 삭제
```

진단 키 — `movement_queue_projection_veh`(`:1077`), `movement_queue_projection_protected_veh`(`:1078`).
N2 의 PASS 조건 `clipped-away mass 0` 이 정확히 이것을 겨냥한다.

### RED 를 못 만든 이유 (여기서 이어받을 것)

`_queue_max`(`:139-156`)가 **어떤 설정을 줘도 1e9 를 반환한다.** 확인한 것:

- movement spec 키에 `storage_capacity_veh` 가 **없다**
  (`approach, beta, destination, exit, intersection, kind, origin, phase, receiving_link, signal`)
  → 첫 분기가 아니다
- `boundary_queue_max_veh` 기본값은 **240** 이고 `with_updates` 로 50 으로 바뀌는 것도 확인했다
- `urban_link_storage_veh['A_to_D']` 는 **220** 으로 존재한다
- 그런데도 `_queue_max` 는 1e9 를 낸다

즉 세 경로 어느 것으로도 1e9 가 나올 수 없는데 나온다. **`movement_specs` 가 캐시되거나
다른 cfg 를 참조할 가능성**이 가장 유력하다. 거기부터 보면 된다.

큐를 1e6 으로 채우고 `urban_substep` 을 돌려도 `projection_veh = 0` 이므로 clipping 이
아예 발동하지 않는다. **실 네트워크 설정에서는 발동한다**(실 런에서 관측됨).
합성 설정 대신 실 네트워크 설정으로 RED 를 잡는 편이 빠를 수 있다.

실패를 본 적 없는 테스트는 남기지 않았다. 상류 저장소는 깨끗하다.

### NumSim 수정 절차 (반드시 지킬 것)

상류 `Claude/NumSim-mine` 에서 커밋 → `scripts/update_numsim_snapshot.py` →
`verify_runtime_source` → `build_preflight_manifest` → `approve_physical_stock_topology`.
**벤더를 직접 고치면 앵커가 깨진다.**

### 정정 — `_queue_max` 미스터리 해결 (쫓지 마라)

`urban_queue_model.py:532` 에 진짜 정의가 있다. 내가 읽은 `:139` 는
**`movement_storage_capacity`** 라는 다른 함수였다.

```python
def _queue_max(cfg, movement, spec) -> float:
    """movement 큐 클립 상한 - 사실상 비활성(점큐 모델, 보존 우선).
    큐 클립은 차량을 삭제해 보존 회계와 베이스라인 대비 공정성을 깬다.
    공간 제약(spillback)은 receiving-space allocation 이 담당하므로
    여기서는 수치 가드 수준의 큰 값만 둔다."""
    return 1.0e9
```

**즉 N2 의 "post-update clipping 제거" 는 이미 되어 있다.** `:1022-1032` 코드는 남아
있으나 `qmax = 1e9` 라 절대 발동하지 않는다. 결함이 아니라 의도된 설계다.
그 RED 는 만들 수 없다.

### N2 에 실제로 남은 것

| N2 요구 | 상태 |
|---|---|
| post-update clipping 제거 | **이미 완료** |
| `TrafficState.total_physical_vehicles()` | **없음 - 신설 필요** |
| transfer ledger (transfer_id, 복식부기) | 미확인 |
| 내부 분해 항등식 | 미확인 |

### 별건 - 경계 링크 저장용량이 기본값이다

실 설정 `urban_link_storage_veh` 302개 중 `SC1_N_out/S_out/E_out` 등이 전부 220.0 이다.
이는 실측이 아니라 `default.yaml` 의 `grid_link_storage_veh: 220.0` 이 경계 링크에
그대로 들어간 값으로 보인다. 우리는 실측 데이터를 이미 갖고 있다 -
`outputs/urban_storage_capacity_20260805.json`(jam density 140.5 veh/km/lane,
182 storage / 82.7 km)과 A2 토폴로지의 stock 별 `capacity_prior`.
**실 링크 길이 기준으로 재실측해 반영할 것.**

---

## 2026-08-10 — N4-3 / N4-4. native 녹색배분 배선과 fail-closed

### 실물로 확인한 것 (선행 조사값 검증)

- `evaluation/controllers/vissim_stackelberg_adapter.py:1317` 의
  `if str(spec.get("phase", "")): return original(...)` — 있었다. phase 가 있는 movement 는
  전부 2현시 원본으로 되돌아가고 있었다.
- 같은 함수의 fail-open 3곳(네트워크 파일 부재 / 컴파일 예외 / 노드 schedule None) — 있었다.
  원본은 blank phase 에 1.0 을 돌려주므로 셋 다 "monitor 전부 항상녹색" 으로 조용히 샌다.
- `plant/src/vissim_strict/signal_program.py:85-110 green_overlap_phase` — 완전 사이클 +
  나머지 + 경계 wrap 을 나눠 적분한다. 새로 만들 필요 없었다.
- `outputs/signal_group_timing_v3.json` SC1001 — 녹색창이 WBL[48,72] EBT[0,45] NBL[118,147]
  SBT[75,115] EBL[48,72] WBT[0,45] SBL[129,147] NBT[75,126] 이다.
  브리핑의 `.193/.267` 은 반올림 표기이고 정확값은 29/150, 40/150 이다.
  1e-9 게이트를 통과하려면 유리수를 써야 한다.

### 정규화를 union 으로 고른 이유 (설계 결정)

배분 `share(m) = union_green(m 의 SG) / union_green(축의 SG)` 다.
정본 표(`derive_signal_group_timing.py`)의 `axis_overestimate` 는 분모로 **axis_max** 를
쓰는데, 그것을 그대로 쓰면 한 origin 이 여러 SG 를 잡을 때 share 가 1 을 넘는다
(SC1001 `SC1004_to_SC1001` → EBT+EBL = 69 s vs axis_max 45 s → 1.53). 넘은 값을 clamp 로
덮으면 그 자체가 새 fail-open 이다.

union 분모는 셋을 동시에 준다.

1. 분자의 SG 집합이 분모의 부분집합이므로 `share <= 1` 이 **구조적으로** 보장된다.
2. 축의 녹색 예산을 보존한다 — 겹치지 않는 movement 들의 share 합이 1 이다.
3. **N=2 에서 정확히 1.0.** 2현시는 한 축의 SG 가 같은 녹색창을 쓰므로 분자=분모다.
   호출부는 배분이 1.0 인 항목을 표에 담지 않으므로 원본 호출이 **그대로** 반환된다 —
   `almostEqual` 이 아니라 `==` 가 성립하는 이유가 "곱셈이 정확하다" 가 아니라
   "곱셈이 아예 없다" 는 것이다.

### 값이 실제로 얼마나 바뀌나

실 config(core15n41) 기준 phase 를 가진 movement 698개.

| | 건수 | 비고 |
|---|---:|---|
| scaled (share < 1) | 229 | 최소 0.25 = 4.0배 축소 |
| unit (share == 1) | 165 | 비트동일 경로 |
| unresolved | 304 | 2현시 원본 유지, 사유와 함께 계상 |

unresolved 내역은 `no_signal_group_mapping` 282 + `axis_mismatch` 22 다.

### 미해결을 예외로 만들지 않은 이유

N4-4 는 "조용한 폴백" 을 예외로 만들라고 했고, 그 대상은 **항상녹색으로 새는 경로**다.
제어 SC 의 배분이 없으면 기존 2현시 값으로 떨어질 뿐 항상녹색이 되지 않는다.
그래서 비대칭으로 뒀다 — monitor 노드 스케줄 부재는 **예외**, 제어 movement 매핑 부재는
**진단 계상**이다. 진단 키는 `native_phase_share_unresolved_count` /
`native_phase_share_unresolved_reasons` / `native_phase_share_min` 이다.

### 아직 열려 있는 것 (숨기지 않는다)

1. **N4-3 의 PASS 기준을 아직 못 맞춘다.** "native production 에서 scalar-cycle fallback 0"
   인데 304건(43.6%)이 여전히 2현시다. 원인은 신호두의 `lane` 이 링크 단위라 한 접근로의
   직진과 좌회전이 같은 SG 집합으로 묶이고, 경계 유입(`in_SC*_*`)은 링크 매핑 자체가
   없기 때문이다. **N4-2(커넥터 추적 매핑)가 선행조건**이다.
2. **`axis_mismatch` 22건은 실제 불일치다.** 예: SC5 의 접근로 leg `S` 는 신호두가 SG 18
   (=EBT, major) 을 가리키는데 모델 movement 의 phase 는 `SC5_p1`(minor) 이다. SC5 는 SG 가
   24개(이름이 3벌 반복)라 이름 규칙이 특히 심하게 뭉갠다. 섞어서 계산하지 않고 남겼다.
3. **모델 ↔ 플랜트 비대칭이 생겼다.** 러너는 controlled SC 를 여전히 이름 규칙 2현시로
   구동한다(`run_real_world_stackelberg_controller.vbs:1298-1312`,
   `ApplyRuntimeSignalController:1210-1233` 이 SC 의 모든 SG 를 major/minor 로 덮어쓴다).
   지금 상태는 **모델만** N현시 배분을 쓴다. 액추에이션은 N4-5(action 스키마 N현시)가 닫는다.
   이 비대칭을 감수한 것은 계획이 N4-3(모델)과 N4-5(액추에이션)를 나눠 두었기 때문이고,
   N4-5 전에는 controlled SC 의 예측이 플랜트보다 보수적(녹색 과소)으로 간다.
4. **hot path 오버헤드 +9.2%.** `_phase_green_fraction` 200k 회 벤치에서 3.069 → 3.350 us/call.
   배분이 있는 movement 에서만 곱셈이 붙는다. solve 당 129만 회이므로 N8 런타임 예산에서
   다시 볼 것.

### base config 는 이제 예외로 죽는다 (의도)

`uncontrolled_nodes=['E']` 같은 합성 격자 config 는 `E` 스케줄이 없어
`MonitorFixedSignalPatchError` 를 던진다. N4-4 의 계약("uncontrolled 공집합만 정당한 대상 없음")
그대로다. 실런은 전부 core15n41 이고 41/41 이 컴파일된다.

## 2026-08-10 — N3-1b. 관측 링크속도를 지연 산식에 싣는다

### 막혀 있던 지점은 VBS 가 아니라 상태였다

checklist 의 "VBS 가 `link_speeds` 로 안 내보낸다" 는 낡은 서술이었다. `link_speeds_kph` 는
이미 나오고 있었고(`run_real_world_stackelberg_controller.vbs:1580`), 어댑터도 읽고
있었다(`:1459`). 다만 진단(`observed_mean_link_speed_kph`)으로만 흐르고 상태 반영
블록(`:2941-2957`)이 ramp_queue / boundary_queue / urban_movement_queue /
urban_link_storage 넷만 써서, 지연 산식이 그 값을 볼 방법이 없었다.
NumSim 쪽 `local_observation_summary` 참조는 0건이었다.

### 0 속도 함정 (계획이 가리킨 것)

`_link_delay_steps` 는 `available × L_veh / v` 다. VBS 의 링크속도는 `speed_sum / count` 라
**표본이 없는 링크에서 0** 이다 — 정체라서 0 이 아니라 관측이 없어서 0 이다.
그 0 을 `max(v, 1e-9)` 로만 막고 분모에 꽂으면 지연이 약 1e12 substep 이 되고,
`_pop_buffer` 가 정확일치 pop(`urban_queue_model.py:476-478`)이라 그 예약은 다시 꺼내지지
않는다. 차량과 링크 저류 공간이 **함께** 영구 격리된다. 그래서 이 RED 를 가장 먼저 썼다
(`src/tests/test_observed_link_speed_delay.py`).

막는 방법을 두 겹으로 뒀다.
1. **모델** — 관측 속도에 하한(`OBSERVED_SPEED_DELAY_CAP_RATIO`)을 둬 지연 상한을 자유류의
   그 배수로 묶는다.
2. **어댑터** — 애초에 표본 없는 링크는 접기에 기여시키지 않는다(`count > 0` 이고 속도 키가
   실제로 있을 때만). 하한에 의존하지 않고 "관측 없음" 을 "관측 없음" 으로 넘긴다.

### 하한 배수 2.5 는 실측으로 정했다 (5.0 에서 내렸다)

처음엔 5.0(하한 10 km/h)을 골랐다. 정체 주행속도의 현실적 하단이라는 이유였는데,
`test_cross_substep_fifo_margin` 의 여유 부등식이 속도에 직접 걸린다는 걸 확인하고 실측했다.

  RHS(지연 1 substep 에 해당하는 available 폭) = v × T_u_h × 1000 / L_veh

속도가 낮을수록 RHS 가 줄어 substep 경계 추월이 쉬워진다. urban_gridlock 200 substep
실측(모든 링크에 같은 관측 속도 주입).

| 관측 v [km/h] | RHS [veh] | 부등식 | 실제 역전 건수 | 최대 역전폭 |
|---:|---:|---|---:|---:|
| 50 (관측 없음) | 11.5741 | OK | 0 | 0 |
| 30 | 6.9444 | LOST | 0 | 0 |
| 20 | 4.6296 | LOST | 0 | 0 |
| 18 | 4.1667 | LOST | 0 | 0 |
| 15 | 3.4722 | LOST | 1 | 1 |
| 12 | 2.7778 | LOST | 12 | 1 |
| 10 | 2.3148 | LOST | 25 | 2 |

LHS 는 7.7778 veh 로 고정이다. 부등식은 30 km/h 부터 깨지지만 **실제 역전은 15 km/h 부터**
나타난다(부등식이 충분조건이라 그렇다 — 기존 테스트 docstring 이 같은 말을 한다).
그래서 하한을 20 km/h(=배수 2.5)로 잡았다. 관측 0 을 전 링크에 꽂아도 역전 0 건이다.

배수를 더 키우지 않은 두 번째 이유는 이중계상이다. 정체 표현은 이미 `available`
(큐 꼬리까지 거리)이 대부분 담당한다. 속도까지 바닥으로 떨어뜨리면 같은 정체를 두 번 센다.

### 방침 결정 — 나머지 4곳은 상수를 유지한다

계획이 판단을 요구한 곳이다. **플랜트만 바꾸면 예측-플랜트 불일치가 생긴다** 는 우려에는
전제가 하나 어긋나 있다. VISSIM 결선에서 플랜트는 VISSIM 이고 `_link_delay_steps` 는
**예측기(NumSim) 안에서** 돈다. 관측 속도를 여기 싣는 것은 불일치를 만드는 게 아니라
예측기를 실제 플랜트 쪽으로 당기는 것이다. 나머지 4곳은 성격이 다르다.

1. `src/analysis/free_flow_reference.py:27` — **유지.** 정의상 "자유류" 기준선이다. 관측을
   넣으면 실현 교통에 따라 기준선이 움직여 개선율이 controller·시나리오 간 비교 불가능해진다.
2. `src/controllers/urban_follower.py:618` (offset t_link) — **유지.** 이미 `available` 이 아니라
   **공칭 만차 길이**(`grid_link_storage_veh`=220 상수)를 쓴다. 실 config 의 per-link 저류는
   120~220 로 흩어져 있으니 플랜트 지연과의 불일치는 내가 만드는 게 아니라 이미 있던 설계
   상수다. 여기에 속도만 관측으로 바꾸면 불일치가 줄지 않고, offset 목표가 매 interval
   관측을 따라 흔들려 green wave 정렬이 진동한다. 제대로 하려면 t_link 를 per-link ×
   available 기반으로 갈아야 하고 그건 N3-1b 범위 밖이다.
3. `src/controllers/wu_distributed.py:215` — **유지.** 같은 공칭 상수를 쓰는데, 그 값이
   "local solve 동안 고정된다" 는 결합변수 계약(`:206`) 위에 있다. 관측 의존으로 바꾸면
   Wu 분산 수렴 근거를 건드린다. 별도 항목으로 다뤄야 한다.
4. 어댑터 `vissim_terminal_feature_vector` (`urban_speed`) — **유지.** 이 함수는 **예측 상태**를
   VISSIM CSV 적합용 집계 특징으로 사상한다. horizon 내부 예측 상태에는 관측이 없다.
   step 0 에만 관측을 쓰면 같은 특징벡터가 step 0 과 step k 에서 정의가 달라져 적합 계수가
   오염된다.

한 줄로 — **예측-플랜트 불일치를 줄이는 변경만 했다.**

### 접기 규칙 (어댑터)

관측은 VISSIM 링크 키, 모델은 storage 링크 키다. `link_to_origins` →
`_storage_links_for_observed_origin` 경로로 접고 **대수 가중평균**을 쓴다. 단순평균이면
1대짜리 링크와 30대짜리 링크가 같은 무게를 갖는다. 진단 키
`urban_link_speed_observed_count` 를 추가했다.

### 아직 열려 있는 것 (숨기지 않는다)

1. **실런에서는 아직 안 돈다.** `DEFAULT_REPO_ROOT`(`:55-59`)가 `vendor/NumSim-mine`
   해시고정 스냅샷을 먼저 잡는데 그쪽 `TrafficState` 에는 이 필드가 없다. 어댑터는
   `hasattr` 가드로 조용히 건너뛴다(그 경로를 `test_legacy_state_without_the_field_still_builds`
   가 고정한다). **상류 재스냅샷이 선행조건**이다. 그 전까지 실런은 전역 상수 그대로다.
2. **관측 속도는 horizon 동안 얼어 있다.** `urban_substep` 은 이 필드를 갱신하지 않으므로
   rollout 내내 step 0 관측이 유지되고, 매 control interval 에 새 관측으로 갱신된다.
   수요 프로파일과 같은 취급이지만, 예측 후반부일수록 근거가 약해진다.
3. **정체 이중계상 여부를 아직 실 런으로 못 봤다.** `available` 과 관측 속도가 같은 정체를
   얼마나 겹쳐 세는지는 위 표(합성 시나리오)로는 답이 안 나온다. 재스냅샷 후 실런에서
   도시부 TTT 가 어느 쪽으로 움직이는지 봐야 한다.

---

## N4-5 / N4-6 (2026-08-10)

### N4-5 — 무엇이 비대칭이었나

모델은 N4-3 이후 축 녹색에 native 배분을 곱해 예측한다. 러너는 SG 상태를 이름
부분문자열로만 정해서(`SignalStateForGroup`) 축 전체를 그 축의 **모든** SG 에 줬다.
같은 지시값이 모델에서는 SG 별로 갈리고 플랜트에서는 뭉개졌다. 이 상태로 N9 를 돌리면
ΔJ 가 무엇의 효과인지 말할 수 없다.

닫는 방식은 축 녹색 시간의 **단조 재매개화**다. 축의 native 녹색 합집합 U 를 시간축으로
삼고 `cum(t)/|U|` 로 정규화해 지시된 축 창에 편다. 성질 셋이 이 선택의 근거다.

1. SG g 의 realize 녹색 = 지시 축 녹색 × |g 의 녹색| / |U| — 모델 share 와 **같은 분수**다.
2. cum 이 단조라 native 에서 떨어져 있던 쌍은 편 뒤에도 떨어져 있다. 동시녹색을
   새로 만들지 않는다.
3. 축 SG 들의 realize 녹색 합집합이 지시 축 창을 빈틈없이 채운다(예산 보존).

축의 위치·길이·주기 공식(`cycle = major + amber + all_red + minor + amber + all_red`)은
건드리지 않았다. **축 안의 분배만** 바뀐다.

### 정본 타이밍 표를 쓰지 않은 이유 (중요)

`outputs/signal_group_timing_v3.json` 은 파일명 번호로 `.sig` 를 골랐다. inpx 의
`supplyFile2` 와 4/15 SC 에서 다르다.

    SC5  표 140 s (test-bed5)  ↔ inpx 160 s (test-bed7)
    SC6  표 100 s (test-bed6)  ↔ inpx 160 s (test-bed9)
    SC11 표 160 s (test-bed11) ↔ inpx 150 s (test-bed3)
    SC12 표 150 s (test-bed12) ↔ inpx 140 s (test-bed5)

VISSIM 이 읽는 것은 inpx 쪽이고, 모델의 `compile_fixed_signal_schedules` 도 inpx 를 읽는다.
그래서 계획은 inpx 에서 나온다. 표는 고치지 않고 `timing_table_disagreements` 로 남겼다
(표 생산자의 몫이다).

### 계약을 행이 아니라 config 에 둔 이유

기대 SG 집합과 동시녹색 금지 쌍이 action CSV 안에 있으면 행이 자기 자신을 인증한다.
그것은 fail-closed 가 아니다. 그래서 `<config>_sgplan.vbs` 에 두고 러너가 ExecuteGlobal 한다.

### 헤더를 늘리지 않은 이유

13열 헤더를 늘리면 러너의 `UBound(parts) <> 12` 계약과 기존 action CSV 소비자가 전부
함께 깨진다. 대신 `kind=signal_sg` 행을 추가하고 열을 재사용했다(dsd_no→sg, link→창
인덱스, major_green→창 시작, minor_green→창 끝, offset→SC offset, green_sec→플랜 주기).
재사용 열의 의미는 어댑터·러너·테스트 세 곳에 같은 말로 적어 뒀다.

### 작업 중 발견한 실제 버그

러너는 매초 돌지 않는다. `NextSignalTransitionAfter` 가 `SignalCompositeStateAt` 이
바뀌는 초를 찾아 거기까지 `RunContinuous` 한다. 그 합성 상태가 2현시 축 상태만 보고
있어서, 계획이 쪼갠 **축 안의** SG 경계가 이벤트가 아니었다. 그러면 SG 전이가 다음
이벤트까지 늦게 쓰인다 — 계획대로 구동되지 않는다. 재현: major=20/minor=20 에서
SG1 0–12, SG2 12–20 일 때 `NextSignalTransitionAfter(10)` 이 12 가 아니라 20 이었다.

### N4-6 — valid-interval 계약

    stage=immediate (t):  t 에 쓴 값이 그 자리에서 되읽혔다.
    stage=post_step (t'): t 에 쓴 값이 t' 까지 유지되었다.

값 v 의 유효 구간은 `[t, t')` 이고 증거는 **양 끝점 두 표본뿐**이다. 구간 내부는 표본이
없다(`interior_sampled=False`). 이것을 숨기면 "유지되었다"가 근거 없이 커진다.

### N4-6 판정 (실측)

실 계획(major 57 / minor 63)에 대해 실 런 없이 낼 수 있는 판정.

| gate | 결과 |
|---|---|
| plan_self_conflict | PASS — 금지 쌍이 계획 어디에서도 겹치지 않는다 |
| cycle_wrap | PASS — 모든 창이 [0, cycle) 안이다 |
| command_quantization_sec | **FAIL 0.990 s** (게이트 0.5 s) |
| min_green_sec | NOT_EVALUATED — 최소녹색을 선언하는 권위가 없다(.sig 의 intergreenmatrices 가 비었다). 최단 계획 녹색 7.28 s (SC1001 SG7) |
| transition_time_error_sec | **BLOCKED** — readback 격자 1 s > 게이트 0.5 s |
| readback 5개 게이트 | NOT_EVALUATED — 실 런 필요 |

`command_quantization_sec` 가 핵심이다. 계획의 창 경계는 실수인데(지시 축 녹색 × native
분율) 러너는 정수 초에만 쓴다. 그래서 실현 전이는 의도의 올림이고 오차가 최대 0.99 s 다.
**실 런 없이 재진다** — 계획과 러너의 쓰기 격자만으로 결정되기 때문이다.

이 값이 0.5 s 를 넘으므로 D-core 는 PASS 가 아니고, 계획 N4-7 의 삼중 잠금에 따라
offset production writer 는 계속 잠겨 있다.

### 남은 비대칭 (숨기지 않는다)

1. **주기가 여전히 다르다.** 모델은 `net.signal_cycle_length(signal)` 로 예측하는데
   `cycle_length_by_signal` 은 의도적으로 비어 있어 전역 스칼라로 떨어진다. 플랜트 주기는
   `major + minor + 10` 이다. N4-5 는 **축 안의 분배**만 닫았고 주기 자체는 열려 있다.
2. **경계 양자화 0.99 s.** 위 표. 이것을 닫으려면 러너가 초 미만 격자로 쓰거나(구조 변경),
   계획이 정수 경계만 내도록 제약해야 한다(배분이 그만큼 뭉개진다).
3. **영구 적색 SG 20개.** inpx 프로그램에서 녹색창이 없는 SG 다. 이름 규칙은 이들에게
   축 녹색을 통째로 줬다 — 즉 지금까지 과대 서비스였다. 계획은 적색으로 둔다.
4. **최단 계획 녹색 7.28 s.** 최소녹색 기준이 정해지면 다시 판정해야 한다.

## N4-7 — offset 승격 잠금 (2026-08-10)

### 먼저 확인한 것 — 잠금 이전에 offset 은 이미 플랜트에 닿고 있었다

모델. `NumSim-mine/src/controllers/urban_follower.py` 가 offset 을 실제로 최적화한다.
`_offsets()` 가 회랑 진행(green wave) 휴리스틱으로 앵커를 잡고, `_offset_candidate_values`
가 그 주변 후보를 만들고, `_urban_stage2_signal_cost` 의 green × offset argmin 이 고른다
(`UrbanControl.offsets`). 어댑터는 `offset_price_enabled` / `joint_green_offset_enabled` /
`ramp_offset_enabled` 를 전부 켠다(vissim_stackelberg_adapter.py:2358-2364).

플랜트 전달. `control.offsets` → action JSON `offsets` → action CSV `signal` 행 10번째 열
`offset` → 러너 `sigOffset(scNo)` → `pos = FMod(simSec + offset, cycle)`
(run_real_world_stackelberg_controller.vbs:756, :1407 부근). 즉 **끊긴 데 없이 COM 까지**
간다. core15n41 은 `network.signals` 와 매핑 `signals[].id` 가 둘 다 "SC1".. 라
`control.offsets.get(signal)` 이 빗나가지도 않는다.

실제 기록도 있다. `evaluation/**/action*.csv` 9831개 중 191개 파일이 nonzero `signal` offset
을 담고 있다(예: `runs/g6_v4_signalfix_20260804/action_v4_c30_offset30_seed13.csv` SC1 = 30).

즉 계획 N4-7 의 "D-core PASS 전까지 production writer 는 intent_only" 는 **지켜지지 않고
있었다.** 이것이 이번에 닫은 구멍이다.

### 잠금의 모양

권위는 `evaluation/controllers/offset_promotion.py` 하나다. 판정은 상수가 아니라 증거에서
나온다 — `outputs/offset_promotion_{d_core,n9_offset_effect,n8_4_runtime}.json` 세 개가
모두 있고, 모두 `status=PASS` 이고, 셋이 **같은** `signal_profile_id` + `topology_sha256`
를 가리킬 때만 `promoted=True` 다. 하나라도 없으면 NOT_EVALUATED, 서로 다른 프로필을
가리키면 BLOCKED 다. 계획의 곱을 그대로 코드로 옮긴 것이다.

    D-offset-enable = D-core(같은 profile + 같은 topology SHA-256) ∧ N9 ∧ N8-4

writer 3단.

| writer | 누가 정하나 | 무엇을 쓰나 |
|---|---|---|
| `intent_only` | 기본값 | 아무것도. 의도는 action JSON `offsets` 에 그대로 남는다 |
| `test_only` | 격리 harness 가 config 로 선언 | **강제 arm 만**. 최적화기 offset 은 여기서도 안 나간다 |
| `production` | **증거만** | 최적화기 offset |

`production` 은 설정 파일로 선언할 수 없다. 선언하면 `OffsetPromotionError` 다 — 설정으로
열 수 있으면 삼중 잠금이 장식이기 때문이다.

### 왜 "조용히 0" 이 아니라 예외인가

강제 arm(`diagnostic-signal-offset30` 등)을 선언 없는 런에서 부르면 `guard_forced_arm` 이
런을 세운다. 조용히 0 으로 뭉개면 "돌긴 돌았는데 레버가 없는" 자료가 남고, 그 자료는
나중에 **offset 효과 없음**으로 읽힌다. 잠금보다 그쪽이 위험하다.

### 자물쇠는 두 겹이다

러너의 `RW_OFFSET_WRITER`(기본 `intent_only`)는 권위가 아니다. 러너는 증거 산출물을 읽을
수 없다. 러너가 보장하는 것은 하나 — "선언하지 않은 런은 offset 을 액추에이션하지 못한다".
손으로 고친 action CSV 도, 옛 어댑터가 만든 CSV 도, nonzero offset 이 있으면
`OffsetPromotionRejectReason` 이 사유를 내고 기존 `:874-882` 자리(같은 `planReason` 조건)
에서 CSV 전체가 거부된다. 부분 적용은 없다.

### N9 행렬은 유도한다

`scripts/build_experiment_matrix_v3.py` 의 `LEVER_STATUS["offset"]` / `LEVER_WRITER["offset"]`
을 손으로 적지 않고 `offset_promotion.matrix_lever_status/writer()` 에서 받는다. 행렬 상수와
실제 writer 동작이 어긋나면 런을 다 돌린 뒤에야 드러나기 때문이다. 오늘 값은 여전히
`BLOCKED` / `test_only` 이고, seal 은 `d397fa07d1c05692` 로 바뀌지 않았다(seal 은 spec 만
덮는다). 증거가 갖춰지면 이 파일을 고치지 않아도 두 값이 함께 열린다.

### 못 한 것

- 실 런은 이 세션에서도 못 돌렸다. 러너 게이트는 cscript 로 `OffsetPromotionRejectReason`
  을 실제 실행해 검증했지만(VBS 실행 TDD), VISSIM COM 에 붙여 본 적은 없다.
- 증거 산출물 3개는 하나도 못 만든다. D-core 가 `command_quantization_sec` FAIL 0.990 s /
  `transition_time_error_sec` BLOCKED 라서다. 즉 잠금은 **열 수 없는 상태가 맞다**.
- N8-4 런타임 게이트는 아직 존재하지 않는다. 증거 파일 이름만 잡아 뒀다.

---

## N4-5 잔여 — 주기 분모 3중 불일치 (2026-08-10)

### 원안("native 주기를 채운다")은 틀렸다

`cycle_length_by_signal` 을 실측 native 주기(140/150/160/170)로 채우자는 것이 N4-1 의
후속 계획이었다. **제어 런에서 native 프로그램은 재생되지 않는다.** 러너는 제어 15 SC 의
모든 SG 에 `ContrByCOM = True` 를 걸어(`run_real_world_stackelberg_controller.vbs:1402`)
inpx 프로그램을 통째로 우회하고, `major + amber + all_red + minor + amber + all_red`
(:764, :1442)로 합성한 주기를 매초 COM 으로 밀어 넣는다. native 주기를 채우면 모델은
**플랜트가 한 번도 돌리지 않는 주기**로 예측하게 된다.

native 주기가 권위를 갖는 곳은 monitor 26 SC 뿐이고, 그쪽은 이미
`fixed_signal_schedule` 이 `program.cycle_length_sec` 를 직접 쓴다 — 이 매핑과 무관하다.

### 채우면 정확히 무엇이 깨지는가 (수치)

`effective_green_total` 은 **스칼라** `cycle_length` 에서만 나오고(state.py:400) 컨트롤러는
예외 없이 `p2 = effective_green_total - p1` 로 배분한다. 주기만 늘리고 예산은 그대로 두면
`_phase_green_fraction` 의 창 배치가 주기를 못 채운다. `src/tests/test_cycle_green_budget_accounting.py`
가 실제 함수로 적분해 재는 값(고정 액션 56/56).

| native C | 결과 |
|---:|---|
| 140 s | 암흑시간 20 s/cycle (녹색도 clearance 도 아닌 구간) |
| 150 s | 30 s/cycle — SC1001~1005 다섯 곳 |
| 160 s | 40 s/cycle |
| 170 s | 50 s/cycle |
| 100 s | 반대로 **모자란다**. p2 창이 잘려 16 s 손실, 주기평균 분기는 자르지 않아 두 현시 합이 **1.12** — 물리적으로 불가능 |

### 실제 간극은 상수 하나였다

모델은 이미 플랜트와 **같은 항등식**을 갖고 있다(`src/evaluation/metrics.py:242` 가 위반을
카운트한다).

    모델    C = p1 + p2 + lost_time
    플랜트  C = minor + major + 2 x (AMBER_SEC + ALL_RED_SEC)

어댑터가 `major <- p2`, `minor <- p1` 을 그대로 싣기 때문에(:5120-5123) 차이는
`lost_time` 8 s 대 `2 x (3 + 2)` = 10 s 하나뿐이다. 그래서 고친 것도 하나다 —
생산 tuning 의 `config_overrides.network.lost_time = 10.0`.

주의: 이 8.0 은 측정값이 아니다. 캘리브레이션 파일에 `recommended_initial_lost_time_sec`
가 없어 어댑터 :2178 의 **하드코딩 기본값**으로 떨어진 값이다(어댑터 base 는 6.0 인데
캘리브레이션 층이 8.0 으로 덮는다). NumSim 의 `lost_time` 소비처 5곳은 전부 주기 기하이고
포화유율/서비스 계산에는 쓰이지 않으므로, 10 으로 바꿔도 용량 캘리브레이션을 훼손하지 않는다.

### 곁가지로 닫은 것 — write clamp

어댑터는 축 녹색을 `[5, 90]` 으로 잘라 싣는데 모델 상자는 `green_max = 92` 였다. p1=20 을
고르면 p2=92 가 90 으로 잘려 플랜트 주기가 2 s 더 짧아졌다. `lost_time=10` 이면 예산이
110 이 되어 p1,p2 ∈ [20,90] 이라 클램프가 **아예 물지 않는다**. green_max 는 안 건드렸다.
클램프 상수는 `plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC` 단일 출처로 옮겼다 — 사본을
재는 테스트는 의미가 없다.

### 얼마나 줄었나

`plant_cycle.green_fraction_overestimate(net)` (리더 액션 상자 전체의 최댓값).

| | 모델 C | 플랜트 C | g/C 과대 |
|---|---:|---:|---:|
| 이전 (lost_time 8) | 120 s | 120~122 s | **+1.667%** |
| 이전, 실 캡처 액션 57/57 | 120 s | 124 s | **+3.333%** |
| 이후 (lost_time 10) | 120 s | 120 s | **0.000%** |

계획서의 "130 s / 8.3% 과대"는 재현되지 않는다. 130 s 는 `major + minor = 120` 을 요구하는데
모델 액션 공간이 그 합을 예산(112)으로 강제한다. 실제로 기록된 모든 런의 녹색 합은
114(37,915 스텝) / 100(1,470) / 95(490) / 112(60) 였고 120 은 한 번도 없다. 8.3% 라는
**크기**는 `diagnostic-signal-major/minor`(75/25 → 플랜트 110 s) arm 에서 나오지만 부호가
반대(과소)다.

### 못 한 것

- 실 런 검증은 못 했다(NOT_EVALUATED). 주기 항등식 자체는 런 없이 정적으로 증명되지만,
  `lost_time` 8 → 10 은 신호당 녹색 예산을 112 → 110 s 로 2 s 줄인다. 서비스율 -1.8% 가
  TTT 에 어떻게 나타나는지는 돌려 봐야 안다.
- 예산면을 벗어나는 진단 arm(57/57 등)은 여전히 어긋난다. 모델 주기는 config 상수인데
  플랜트 주기는 액션에서 유도되기 때문이다. 완전히 닫으려면 `_phase_green_fraction` 이
  `C = g1 + g2 + lost_time` 을 쓰도록 상류를 바꿔야 하는데, 그러면 N4-1 이 고정한
  `cycle_length_by_signal` 계약과 충돌한다. 설계 결정이 필요해 손대지 않았다.
- `cycle_length_by_signal` 은 비운 채로 뒀다. 위 이유로 **채우면 안 된다**.

## 2026-08-10 — N10 감사 게이트 (18 → 28)

**무엇이 없었나.** 감사에는 게이트가 18개 있었고 범주로는 신호·토폴로지·투영·런타임뿐이었다.
질량은 `projection_diagnostics` 안에 묻혀 있어 표에서 구분되지 않았고, 캘리브레이션·짝동역학·
순위·승격은 아예 없었다. 상태 어휘도 `PASS/FAIL/NOT_EVALUATED` 셋뿐이라 N9-4 가 요구하는
`BLOCKED`(혼잡 셀 표본 미달)를 표현할 수 없었다.

**추가한 10개.** `canonical_topology` · `signal_timing_canon` · `signal_actuation_plan` ·
`movement_signal_group_map` · `mass_conservation` · `stock_calibration` · `paired_dynamics` ·
`spillback_detection` · `gradient_ranking` · `promotion_readiness`.

**임계를 다시 적지 않았다.** N6 판정은 `validate_physical_stock_calibration.validate`,
N9-4 지표·게이트는 `paired_validation_metrics.evaluate` / `spillback_status` 를 **불러서** 쓴다.
`sibling_module()` 이 같은 `scripts/` 안의 모듈을 파일 경로로 적재한다 — 감사가 임계를
복제하면 두 벌이 갈라지고, 갈라진 순간 어느 쪽이 정본인지 아무도 모른다.
판정 모듈을 못 읽는데 증거는 있으면 그 게이트는 NOT_EVALUATED 가 아니라 **FAIL** 이다.

**대조 산출물이 없으면 PASS 가 아니다.** `signal_timing_canon` 은 액추에이션 계획이 없으면
NOT_EVALUATED 로 끝난다. 교차검증 없이 통과시키면 "산출물을 덜 낼수록 유리" 해진다.

**새 인자의 기본값은 빈 문자열이다.** 감사의 원래 계약이 "호출자가 명시한 살아 있는 산출물만
현재 증거" 이고, 기본값을 저장소 outputs/ 로 박으면 baseline 스냅샷 픽스처(자기 임시 망을 쓴다)가
`signal_actuation_plan` 의 망 동일성 검사에서 무너진다. 실행 예시는 checklist 위 항목 참고.

**승격 규칙.** `promotion_readiness` 는 (a) 감사 자신의 나머지 게이트와 (b) N5 부모 런 명세가
정한 holdout(demand 0.75/1.0/1.25 × seed 47) 각 셀의 필수 게이트를 함께 본다. 필수 게이트는
`paired_dynamics · spillback_detection · gradient_ranking · mass_conservation · runtime` 이고,
**저수요 면제는 spillback 하나뿐**이다(혼잡 demand 는 명세의 `congested.demand` 에서 읽는다).
계획 초판의 역인센티브 — 저수요라고 전 지표를 면제하면 측정을 덜 하는 쪽이 이긴다 — 를 코드로 막았다.

**지금 판정.** v3 산출물을 물려 돌린 결과 PASS 11 / FAIL 3 / BLOCKED 0 / NOT_EVALUATED 14.
FAIL 3 중 `assignment_ties` 는 기존 것이고, 새로 드러난 것은 `signal_timing_canon` 이다 —
`signal_group_timing_v3.json` 이 SC5/6/11/12 에서 inpx supplyFile2 와 **다른 `.sig` 와 주기**를
가리킨다(SC5 140 s vs 160 s 등). VISSIM 이 읽는 것은 inpx 쪽이므로, 정본 표로 계산한 녹색·offset 은
그 넷에서 틀린 주기 위에 놓인다. `derive_signal_group_actuation_plan.py` 가 이미
`timing_table_disagreements` 로 남겨 두고 있었는데 아무도 게이트로 걸지 않았다. 이제 걸린다.
`promotion_readiness` 는 그 FAIL 을 물려받아 FAIL 이다 — 설계대로다.

**스키마 3.** 매니페스트 모양이 바뀌었으므로 `SCHEMA_VERSION` 을 2 → 3 으로 올리고
`validate_baseline_snapshot.py:30` 의 `AUDIT_SCHEMA` 도 3 으로 맞췄다(한 줄). 옛 감사 산출물을
새 소비자가 조용히 받아들이면 안 된다.

**못 한 것.** 실 런은 여전히 못 돌린다. 새 게이트 5개(`stock_calibration`, `paired_dynamics`,
`spillback_detection`, `gradient_ranking`, `promotion_readiness`)는 N5/N6/N9 산출물이 생기기
전까지 NOT_EVALUATED 로 남는다. 출처 게이트(해시 사슬·변조 탐지)는 계획대로 넣지 않았다.
`run_plant_fidelity_matrix.ps1` 의 required-gate 목록도 손대지 않았다 — 실 런 프로필이 정해진 뒤에 할 일이다.

## N8-2 결정 동등성 · N8-3 통합 rollout 스케줄러 (2026-08-10)

두 항목 모두 컨트롤러 쪽 일이라 코드는 상류 `NumSim-mine` 에 넣었다. `vendor/`(5a2fe7d)는
건드리지 않았으므로 어댑터 실행 경로의 거동은 **재스냅샷 전까지 바뀌지 않는다**.

### N8-3 — 병렬화가 결정을 바꾸던 자리 두 곳

`stackelberg_mpc._evaluate_candidate_set` 의 thread/process 분기는 `as_completed` 완료 순서로
결과를 쌓았다. 선택은 `min(evaluations, key=objective)` 이고 파이썬 `min` 은 **첫** 최소값을
고르므로, 동점 후보가 있으면 **worker 수에 따라 선택 action 이 바뀐다**. 실측으로 잡았다 —
목적함수 `(30,20,10,40,25,10,35)`, 완료 지연을 인덱스 역순으로 준 stub 에서
workers 2 → 결과 순서 `[0,2,1,4,3,6,5]`, workers 5 → `[0,5,6,4,3,2,1]` 이고
동점(인덱스 2 와 5) 최소값 선택이 workers 5 에서 인덱스 **5** 로 뒤집혔다.
고친 방식은 반환 직전 `results.sort(key=index)` 한 줄이다(직렬 경로는 이미 인덱스 순서라 무영향).

`stackelberg_wu_metered._green_price_rollouts` 는 병렬 풀이 터지면 **조용히** 직렬로 재실행했다.
계획 N8-3 의 PASS 는 "병렬 예외 뒤 조용한 직렬 재실행 0" 이다. 진단
`price_parallel_serial_rerun_count` / `price_parallel_last_error` 를 남기고
`wu_price_parallel_serial_rerun_count` 로 meta 에 실었다. 이 계측이 실제로 필요하다는 증거도
같이 나왔다 — main guard 없는 프로브 스크립트에서 자식 프로세스 bootstrap 실패가 조용히
직렬로 접혔고, 계측이 없었으면 "병렬과 직렬이 같다" 는 결론이 공허하게 통과했을 것이다.

**실 런 config 는 원래 안 물린다.** `real_world_modi_pstack_crossgate_high_budget_20260723.json`
과 어댑터 flagship 기본값이 `stackelberg_leader_parallel_backend: serial` ·
`grid_parallel_backend: serial` · `grid_reuse_process_pool: false` 이고,
`F1StackelbergWuMeteredController` 는 `StackelbergWuMeteredController._evaluate_candidate_set`
(후보 평가 직렬 강제)을 물려받는다. `price_parallel_workers` 도 어댑터에서 설정되지 않아 0 이다.
즉 이번에 고친 것은 **잠재 결함**이고, 병렬을 켜는 순간 실 런에서 재현됐을 것이다.

### N8-2 — 계획의 `36` 이 무엇이고 무엇이 안 되는가

계획의 36 은 `holdout 상태 12(= demand 3 × anchor 4) × 방향 seed 3` 이고 비교는
**FD 대 SPSA** 다. 그 12 상태는 N5 부모 런의 VISSIM holdout anchor 라 실 런 없이 못 만든다.
그래서 같은 **모양**을 플랜트 모델 상태로 재현해 36 twin 을 실제로 돌렸다.
후보 수는 계획대로 36 이고, 다른 값이 나오지 않았다.

실측(모델 anchor 36 twin, lean config).

| 필드 | 정확 일치 |
|---|---|
| feasibility | 36/36 |
| 안전 인증서(B3CERT `wu_b3cert_*`) | 36/36 |
| fallback 등급 | 36/36 |
| 리더 후보열 `(index, stage, N_P*, N_UF*)` | 36/36 |
| 종단 예측 상태 | **3/36** |
| 명령(정확) | **3/36** |
| 명령(양자화 1단계 이내) | 36/36 |

**계획 PASS 의 두 조항은 함께 성립할 수 없다.** 명령에 양자화 1단계를 허용하면서 상태
정확 일치를 요구하는데, 명령이 한 칸 움직이면 종단 예측 상태도 반드시 움직인다.
실제로 상태가 갈라진 twin 은 전부 명령이 갈라진 twin 이었고, 그 불변식을 검사로 고정했다
(`test_state_mismatch_only_ever_follows_a_command_mismatch`).
따라서 계획 문안은 "상태" 를 명령 일치 조건부로 다시 쓰거나, 명령 여유를 없애야 한다.

### N8-2 의 두 번째 twin — endpoint 경유 대 직접

`evaluate_price_point` 를 우회하는 독립 구현으로 같은 결정을 다시 내고, **평가 궤적**
(호출 열의 목적함수·부분 TTT·abort·상태수)과 다섯 필드·명령이 전부 정확 일치함을 확인했다.

**결정 지문만으로는 이빨이 없다는 것을 먼저 실측했다.** 이 fixture 에서는 가격 schedule 의
레버를 통째로 빼도(green/meter/vsl/offset 전부) 결정 지문이 안 움직인다 — 후보가 포화하고
fallback(PFO)이 선택되기 때문이다. 심지어 모든 가격점 목적함수를 5% 부풀여도 결정이 같다
(기울기가 비례 배율이면 follower 반응이 안 뒤집힌다). 그래서 궤적 비교를 함께 넣었고,
되돌림 증명은 `depth+1` · `drop-green` · `drop-meter` · `drop-offset` · `no-green-budget`
다섯 교란이 전부 궤적을 갈라놓는 것으로 했다.

**vsl 축은 되돌림 증명에서 뺐다.** 이 fixture 의 vsl 가격점 32개가 **전부 같은 목적함수**를
낸다 — 운영점 100 km/h 에 delta 를 얹은 105/115 가 자유류 상한 위라 plant 가 반응하지 않는다.
교란해도 안 잡히는 검사를 통과로 세지 않으려고 뺐고, 그 사실 자체를
`VslChannelInertnessTests` 가 못박는다. vsl 이 다시 물리면 그쪽이 먼저 깨져 교란 축 복구를 강제한다.

### 남는 것

계획 N8-2 자체(**VISSIM holdout anchor** 위의 FD 대 SPSA)는 실 런 전까지 NOT_EVALUATED 다.
N8-1 자격심사 하네스(`eps_J_endpoint`/`eps_g`)도 아직 없어서
`exact-FD 재채점 regret < max(2·eps_J_endpoint, 0.5%·|J_FD|)` 조항은 판정 불가다.

---

## 2026-08-10 — 코드 잔여 착지와 vendor 재앵커

### N8-3 정렬이 직렬을 바꾸고 있었다 (상류 e4bf4d0)

`deb3134` 이 `results.sort(key=item.index)` 로 backend 독립성을 만들었는데, 그 주석의
"직렬은 무영향" 이 **거짓**이었다. `_prefilter_leader_candidates` 는 `selected` 를
`ranked[:top_k]` 의 **proxy 랭킹 순서**로 쌓으므로(`stackelberg_mpc.py:2020-2036`) 직렬
결과 순서는 인덱스 순서가 아니었다. 정렬 한 줄이 직렬의 동점 선택도 5 → 2 로 바꿨다.

기존 검사가 못 잡은 이유가 중요하다. `test_parallel_determinism.py` 가 `selected_indices` 로
`list(range(n))` 을 넘겨 **prefilter 재정렬을 우회**했다. 실배선에서 prefilter 는 항상
활성이다(`default.yaml` top_k 4 / 후보 49, core15n41 top_k 3 / 후보 9).

**정본 순서는 `selected_indices` 순서로 정했다.** 직렬이 내던 순서이고, flagship override
(`stackelberg_wu_metered.py:2782-2790`)가 정렬 없이 내는 순서와도 같다. 인덱스 순서를
택했으면 병렬을 직렬에 맞추는 대신 직렬 쪽을 옮기는 것이고, 두 구현의 순서 규약도 갈린 채
남았을 것이다.

### 정본 타이밍 표가 틀린 `.sig` 를 읽고 있었다

`derive_signal_group_timing._sig_path_for` 가 **파일명 끝자리 번호**로 `.sig` 를 골랐다.
VISSIM 이 읽는 것은 inpx `signalController/@supplyFile2` 이고, 4/15 SC 에서 달랐다.

수치가 이렇게 바뀐다 — SG **128 → 136**, 동시녹색 쌍 **160 → 222**, 최악 녹색 과대
**5.00 → 5.47배**, native 주기에서 100 s 소멸. **문제는 보고돼 있던 것보다 39% 크다.**

`--network` 를 명시 입력으로 뒀다. 네트워크 디렉터리에 `.inpx` 가 8개라 자동 탐색이
못미덥고, 배정된 파일이 없을 때 다른 파일로 **대신 고르지 않고** `unresolved` 로
떨어뜨린다 — 대신 고르던 것이 애초의 결함이었다.

체인이 timing → movement map → actuation plan → sgplan.vbs → 감사다. 그 과정에서
**커밋돼 있던 sgplan.vbs 가 계획과 어긋난 채**였음을 발견했다. 기존 검사가 집계(SG 수·창
수·충돌 쌍 수)만 봐서 sha 드리프트를 못 잡았다. 원본 sha 대조를 추가했다.

### 통과할 수밖에 없던 검사 둘

`uncovered_signal_groups` 는 식이 `sg_no not in window_counts` 인데 `window_counts` 가
같은 sg_id 목록으로 초기화돼(`signal_group_plan.py:158`) **구조적으로 항상 0** 이었다.
"native 에 녹색이 있는데 계획에 창이 없는 SG" 로 바꿨고 실측은 여전히 0 이다 — 실질은
멀쩡했고 검사만 공허했다.

`run_plant_fidelity_matrix.ps1` 은 N10 새 게이트 10개를 요구도 안 하고 산출물도 안
넘겼다. 규칙을 뒤집어 **모든 게이트는 요구되거나 `$matrixUnavailableGates` 에 명시**돼야
하도록 검사를 걸었다. 요구 15 → 22, 불가 선언 6.

주의 — 다음 매트릭스 런은 새로 요구한 7개가 PASS 하지 않으면 **실패한다**. 의도한
fail-closed 이고, 조용한 NOT_EVALUATED 보다 낫다고 판단했다.

### vendor 재앵커

`5a2fe7d → e4bf4d0`, 115 파일. 재앵커 전까지 실 런의 NumSim 층은 **5곳에서 endpoint 를
우회**했다(stage2_mechanism:133, centralized_mpc:299/328, distributed_coordinator:673,
wu_distributed:862). 상류만 고치고 vendor 를 안 옮기면 N7 은 실 런에서 미완이다.

사슬 3단 재생성 PASS. `run_readiness.py` status=READY.

## 2026-08-10 — assignment_ties 를 질량 기준으로 닫았다 (설계 판단 A)

### 조사에서 드러난 것

33건은 **8개 종단 쌍**뿐이고 전부 2지선다였다. 그리고 33건 중 **22건이 freeway_bound
링크 전부**와 정확히 일치했다(`counts.freeway_bound = 22`).

처음에 "33건 전부 질량 0" 이라고 판단했는데 **틀렸다**. `urban_link_storage_veh` 는
도시부 전용 표라 freeway 쪽 링크가 없는 게 당연했다. 실 관측 204표본으로 다시 재니
tie 링크가 관측 차량의 **중앙값 1.68% · 최대 6.94%** 를 나르고 있었다(개별 최대 58 veh).
잘못된 표를 근거로 세운 안이라 폐기했다. 선결 확인을 안 했으면 그대로 갔다.

### 6건은 애초에 tie 가 아니었다

차를 싣던 6건이 전부 `detector_local_mapping.off_ramp_connectors` 에 등록된 off-ramp
커넥터였다(커넥터 8개 중 6개). **정답이 이미 다른 산출물에 `from_link` 로 있는데 감사
BFS 가 그 파일을 안 봤다.** BFS 는 이미 `stop_owners` 로 같은 제외를 하고 있었다(:517) —
선언을 하나만 알고 둘째를 몰랐던 것이다.

사용자가 망에서 직접 확인한 값과 매핑이 일치했다 — **10645 → FW:26, 10682 → FW:2**.
그리고 이 off-ramp 들은 **망 밖으로 나가는(termination) 차량**을 나르므로 종단이 프리웨이
노드가 아니라 망 밖이다. BFS 가 틀린 질문을 하고 있었다. 다만 FW:26 쪽에는 on-ramp 도
있으므로 이 구역 자체를 무시해선 안 된다.

`declared_owner_links` 로 제외해 **33 → 27**. 빠진 6건이 정확히 차를 싣던 것들이다.

### 게이트를 질량 기준으로

tie 는 위상 사실이고, 해로운지는 그 링크가 차를 나르는지에 달렸다. 게이트를
"질량을 나르는 링크에 tie 가 없다" 로 바꿨다. 남은 27건은 관측 차량이 0 이다.

**미측정은 통과가 아니다.** 관측이 없으면 NOT_EVALUATED 이고 PASS 는 실 런 감사에서만
나온다. 저장소 정적 감사는 이제 FAIL 이 아니라 NOT_EVALUATED 다 — 거짓말을 안 한다.

**커버리지 요건을 따로 넣었다.** 점유 집합만 보면 좁은 관측이 공짜 PASS 를 산다. 실제로
`seed_repl_20260803` 은 link_counts 가 22개뿐이라 tie 27건을 하나도 안 담았는데 처음
구현에서 PASS 가 나왔다. "관측돼서 0" 과 "관측 안 됨" 을 갈라 후자는 NOT_EVALUATED 다.

### 부수 효과

감사 FAIL 2 → 0 (PASS 12 / NE 16). `promotion_readiness` 는 최악 게이트를 물려받으므로
FAIL → NOT_EVALUATED 다. 승격은 여전히 막혀 있다(NE 는 통과가 아니다). 그리고 FAIL 이
사라지자 spillback BLOCKED 시나리오에서 승격이 BLOCKED 로 드러났다 — 예전엔 FAIL 이
덮고 있었다.

## 2026-08-11 — 설계 판단 (B) 를 되돌리고, N4-3 의 진짜 원인을 찾았다

### (B) 주기 항등식 — 구현했다가 되돌렸다

`_phase_green_fraction` 이 config 상수 `cycle_length` 로 나누는 대신 모델 자신의 항등식
`C = g1 + g2 + lost_time` 을 쓰게 했다. 근거는 튼튼했다.

- 모델은 이미 그 항등식을 주장하고 `metrics.py` 가 위반을 센다. 주기는 자유 파라미터가 아니다.
- 플랜트도 같은 식이다 — 러너가 `major + minor + 2*(AMBER + ALL_RED)` 로 합성한다.
- **제어 런에서 native 주기는 재생되지 않는다.** 러너가 15 SC 의 모든 SG 에
  `ContrByCOM = True` 를 걸어 inpx 프로그램을 통째로 우회한다
  (`evaluation/controllers/plant_cycle.py:18-23`). 그래서 `cycle_length_by_signal` 에
  native 주기를 채우는 것으로는 간극이 안 닫힌다. "N4-1 과 정면충돌" 은 과장이었다.
- 실측 — 액션 아카이브 31,020 표본에서 **예산면(p1+p2=110) 위 액션이 0건**이다.
  114 (94.7%, +3.33%), 100 (4.0%, -8.33%), 95 (1.3%, -12.50%).

**되돌린 이유.** `test_cycle_green_budget_accounting` 모듈이 통째로 무효가 된다(10 subtest).
그 파일은 "`cycle_length_by_signal` 을 채우면 무엇이 깨지는가"를 측정하는데, 이 변경이 그
깨짐을 전부 없앤다. 다시 쓰려면 **"그 매핑은 무엇을 위한 것인가"** 를 정해야 하고 그것은
N4-3 질문이다. 승인 없이 테스트 편집으로 N4-3 을 결정하게 되므로 멈췄다.

역설적이지만 그 테스트 파일의 docstring 이 이 변경과 **같은 주장**을 한다 —
"`cycle_length` 는 자유 파라미터가 아니라 녹색 예산이 결정한 값이다". 변경 자체는 옳고,
N4-3 안에서 N현시 일반형 `C = Σ gᵢ + lost_time` 으로 다시 하면 된다.

### N4-3 — 진단이 세 번 뒤집혔다

**1차(틀림).** "미해결 282건은 synthetic boundary leg 이라 VISSIM 에 없다. 구조적 부재다."
계획서 문장을 그대로 받았다.

**2차(틀림).** 사용자가 "비씸에 없는 게 플랜트에 있단 건가?" 라고 물어 다시 봤다.
모델 config 에 `boundary_in_links` 가 **117개** 있고, 미해결 origin 44개가 그 목록과
**정확히 일치**한다. VISSIM 에도 vehicle input 이 34개 있다. 없는 게 아니었다.

**3차(맞음).** 원인은 **스키마에 칸이 없는 것**이다. `grid_node_legs` 의 boundary leg 는

    "N": {"type": "boundary", "in": "in_SC1_N", "out": "out_SC1_N", "out_link": "SC1_N_out"}

유출은 `out_link` 칸이 있어 `link_to_origins` 에 매핑돼 있는데(SC1 기준 4개),
**유입은 `in_link` 칸 자체가 없다.** 그래서 조인될 수가 없었고 `boundary_link_to_queue`
도 0 항목이다. 표가 안 채워진 게 아니라 채울 자리가 없다.

계획서의 "잔차 뭉개기가 아니라 구조적 부재다" 는 결론(링크 0개)은 맞지만 **원인 진단이
틀렸다**. 고칠 수 있는 문제를 못 고치는 문제로 적어 둔 셈이다.

### 다음 세션 출발점

1. `grid_node_legs` 의 boundary leg 에 `in_link` 를 추가한다 — **스키마 결정**
2. 유입 링크는 매핑된 `out_link` 의 반대 방향 짝으로 유도한다 — **규칙 결정**
3. vehicle input 34개를 하류 SC 로 BFS 조인하는 것은 **34/34 동작을 확인했다**
   (`audit_plant_fidelity._network_downstream` + `read_stop_owners` 재사용)

N4-3 현황 재확인 — movement 698 / resolved 416 / unresolved 282(전부 synthetic_boundary_leg).
효과는 실재한다: SC1001 movement 54개 중 21개 분율 변경, 실측 대비 1.56x/1.21x -> 1.01x/0.97x.
질량 보존은 N4-1+N4-3 동시 적용에서 24스텝 잔차 1.148e-11 veh.

### 이번 회차에서 반복된 실패 양상

세 번 다 **잘못된 표를 근거로 단정**했다. urban 저장 표로 "질량 0", 계획서 문장으로
"구조적 부재", 그리고 (B) 를 "검사 2건이면 끝"이라고 추정. 실물을 열면 매번 달랐다.
계획서에 적힌 진단도 근거를 다시 열어봐야 한다.

## 2026-08-11 (이어서) — 경계 수요는 시간축만 앵커돼 있다

### 오경보 정정

`DemandProfile` 로 실 config 를 열었더니 경계 게이트 117개가 등차수열(500/550/600/650...)
합계 397,800 veh/h 였다. 플랜트 실측(28,360 veh/h 피크)의 14배라 크게 놀랐는데,
**결합 런은 그 경로를 쓰지 않는다.** 어댑터가 state 의 `demand` 에서 읽는다
(`vissim_stackelberg_adapter.py:2804-2816`). standalone NumSim 시뮬레이션 전용 값이었다.

### 실제로 앵커된 것과 안 된 것

실 런 state 의 수요 필드는 이렇다.

    demand_profile   = "real_world_inpx_time_profile"   (또는 _scaled)
    urban_volume_vph = 355 -> 515 -> 603 -> 662 -> 735 -> 772   (시간에 따라 변함)

**시간 프로파일은 inpx 에 앵커돼 있다.** 문제는 공간이다.

    urban_vph = float(demand.get("urban_volume_vph", 60.0))
    urban_boundary = {str(link): urban_vph for link in boundary_in_links + boundary_out_links}

**한 스칼라를 모든 게이트에 똑같이 뿌린다.** 플랜트는 그렇지 않다.

| | 플랜트 (inpx) | 모델 (결합 런) |
|---|---|---|
| 유입 지점 | **34개** vehicle input, 위치·이름 있음 | 117개 경계 게이트 |
| 지점별 유량 | **376 ~ 6,000 veh/h 로 제각각** | 전 게이트 동일 스칼라 |
| 망 전체 | 18,907 ~ 28,360 veh/h (15분 6구간) | 스칼라 x 게이트 수 |

VISSIM 은 양재 EB/NB 에 수천 대를 넣고 Dummy Link 9 에 291 대를 넣는데 모델은 둘을 같게 본다.

### 재료는 다 있다

- inpx vehicle input 34개 - 링크·이름·`timeIntervalVehVolume` (읽었다)
- vehicle input -> 하류 SC BFS 조인 **34/34 성공** (확인했다,
  `audit_plant_fidelity._network_downstream` + `read_stop_owners` 재사용)
- 시간 프로파일 배선 (이미 있다)

**빠진 것은 지점별 배분 규칙 하나다.** 34 -> 117 을 어떻게 나눌 것인가.

### N4-3 과의 순서

사용자 판단 - "실측이어야지". 틀린 유량 위에 정확한 녹색분율을 얹는 것은 의미가 없으므로
**수요 공간 앵커링이 N4-3 보다 먼저다.**

### 이번 회차 실패 양상 (계속)

네 번째 오진이었다. 이번에는 **쓰이지 않는 코드 경로를 재고 놀랐다**. 값을 재기 전에
"그 값이 실 런에서 쓰이는가" 를 먼저 봤어야 했다.

## 2026-08-11 (3) — 모델이 도시부 수요를 3.66배 주입하고 있다

### 측정

| 구간 | VISSIM 실제 도시부 유입 | 모델 주입 | 배율 |
|---|---:|---:|---:|
| 1 0 | 12,747 veh/h | 46,607 | 3.66 |
| 1 900000 | 18,209 | 66,577 | 3.66 |
| 1 1800000 | 19,120 | 69,909 | 3.66 |
| 1 2700000 | 16,389 | 59,922 | 3.66 |
| 1 3600000 | 12,747 | 46,607 | 3.66 |
| 1 4500000 | 9,106 | 33,292 | 3.66 |

배율이 모든 구간에서 동일하다. 117 게이트 / 32 유입지점 = 3.656 이다. 구조적이다.

### 경로

    러너   (vbs:2950)   demandUrbanBySec(key) = urbanSumBySec(key) / urbanNBySec(key)
                        -> VISSIM 도시부 유입 **지점당 평균** 을 state 에 쓴다

    어댑터 (adapter:2814) urban_boundary = {link: urban_vph for link in boundary_in_links}
                        -> 그 평균을 **117개 게이트 전부** 의 값으로 쓴다

지점이 32개였으면 총량이 맞는다. 117개라 3.66배가 된다. 러너와 어댑터 중 한쪽이 틀린 게
아니라 **둘의 규약이 어긋나** 있다 - 러너는 "평균" 을 주는데 어댑터는 "각 게이트의 값" 으로 읽는다.

### 크기 비교 (이번 회차에 찾은 것들)

    도시부 유입 총량      +266%          <- 이것
    신호 녹색분율 과대     최대 5.47배     (movement 단위)
    주기 불일치           +3.33%
    tie 링크 질량         1.68%

모델의 큐·지체·TTT 예측이 전부 실제의 3.66배 수요 위에 있다. N9 합격 게이트
(큐/저장 NMAE <=15%, TTT APE <=10%)는 이 상태로 통과할 수 없다.

### 유입 32개의 분류 (사용자 확정)

| 종류 | 개수 | peak 합 | 모델 격자 상태 |
|---|---:|---:|---|
| named (실제 위치) | 14 | 10,361 veh/h | leg없음 13, grid 1 - **전부 안 맞음** |
| unnamed | 8 | 6,533 | **boundary 5** OK, leg없음 2, 노드없음 1 |
| dummy (내부 발생) | 10 | 2,226 | 경계 아님 - 격자 대상 아님 |

진짜 망 입구 = 22개, 16,894 veh/h. 모델이 제대로 아는 것은 5개뿐이다.
모델 격자는 실제 입구 17곳을 모르고, 없는 입구 약 95곳을 갖고 있다.

### "먼저 확인" 이 옳았다

95개를 바로 지웠으면 총량은 맞았겠지만 **원인을 모른 채** 넘어갔을 것이다. 원인이 게이트
수가 아니라 러너-어댑터 규약 불일치라는 것을 알았으므로, 격자를 고치든 분배를 고치든
근거를 갖고 할 수 있다.

---

## 2026-08-11 — `state.demand` 계약을 문서·검사로 고정했다 (작업 A)

3.66배의 근본 원인은 격자도 유입도 아니라 **러너-어댑터 규약이 어디에도 없던 것**이다.
이번에는 배율을 고치지 않고 의미를 못박고 어긋남을 검사로 드러내는 데까지 했다.

### 새로 확인한 것 (계획서에 없던 것들)

1. **freeway 는 지금 맞다. 그러나 우연이다.**
   유입 지점 2개(no=1098 link 74, no=1099 link 26) vs 모델 `freeway_links` 2개라 총량이 맞고,
   두 유입의 시간구간별 volume 이 **완전히 동일**(3080/4400/4620/3960/3080/2200)해서
   "평균 == 각 값" 이 되어 방향 분해까지 맞는다. 둘 중 하나만 깨지면 도시부와 같은 오류가 난다.
   -> "freeway 도 3.66배 같은 게 있나" 를 재 보기 전에 **개수를 세는 것**이 먼저였다.

2. **ramp 는 실 런에서 0 이다.** 러너가 `""ramp_volume_vph"": 0` 리터럴을 쓰고(vbs:2123),
   실 캘리브레이션(`real_world_prediction_calibration_pshb4500fix_20260724.json`)의
   `prediction` 키는 `["audit_calibration"]` 뿐이라 `onramp_route_forecast` /
   `local_ramp_arrival_forecast` / `route_bias` 세 경로가 전부 꺼져 있다.
   어댑터의 기본값 `max(120, 0.12*freeway_vph)` 는 키가 존재하므로 **절대 발동하지 않는다**.

3. **`boundary_out` 는 주입에 안 쓰인다 — 확인했다.** 모든 도착 계산이
   `kind == "boundary_in"` movement 의 `origin` 만 본다(8개 소비 지점 전수 확인).
   실 cfg 에서 `boundary_in` movement 641개의 서로 다른 origin 이 정확히 117개이고
   `boundary_in_links` 와 일치하며 `boundary_out_links` 와 교집합이 없다.

4. **그런데 진단값은 샌다.** `stackelberg_mpc._forecast_demand_metadata`(:2237-2246)가
   `urban_boundary` 의 **전 키**를 합산한다. t=1800 s 에서 실제 주입 69,909 veh/h 인데
   로그의 `leader_forecast_boundary_*` 는 141,012 veh/h — `(117+119)/117 = 2.0171` 배다.
   `classical_hierarchical:408-411` 도 전 키를 합산하지만 그 컨트롤러는 실 런에서
   생성되지 않는다(어댑터는 Stackelberg/StackelbergWuMetered/DistributedCoordinator 만 만든다).
   -> "쓰이지 않는 코드 경로를 재지 마라" 를 여기서 적용했다. 둘을 갈라서 적었다.

5. **배율은 망마다 다르다.** 같은 117 게이트 격자에 붙였을 때
   `modi_eval_rw_control.inpx` 32지점 -> 3.656, `..._peakplateau_20260729.inpx` 및
   `..._peakhold4500_recovery_20260729.inpx` 는 29지점 -> 4.034.
   게이트는 `generate_real_world_distributed_players.py:391-396` 이 VISSIM 을 안 보고
   만들므로 두 수를 이어 주는 것이 아무것도 없다.

### 산출물

- `evaluation/controllers/demand_contract.md` — 필드별 의미(스칼라 1개, 소비자가 복제),
  생산자·소비자 코드 위치, 알려진 불일치 `KNOWN-URBAN-GATE-MEAN`, 6구간 실측표
- `tests/test_demand_contract.py` — `python -m unittest tests.test_demand_contract`
  기대: **Ran 8, FAILED (failures=7)**. 불변식 6 PASS + 알려진 불일치 2 FAIL(6 subTest 포함)

### 검사 설계 판단

- **문자열 대조 대신 양쪽에서 단위를 계산했다.** 생산자 쪽은 `LoadInpxDemandSchedule`
  의 산식(분류 -> 구간별 sum/n -> 평균)을 실 `.inpx` + `vehicle_input_roles.csv` 로
  재현하고, 소비자 쪽은 `adapter.profiled_demand_rates` 를 실 cfg 로 **실제 호출**한다.
- **xfail 을 안 썼다.** 이 저장소에는 CI 가 없어서(`.github` 없음) FAIL 이 막는 것이 없다.
  대신 클래스를 갈라 `DemandContractKnownMismatchTests` 로 이름 붙이고 문서 §4 와 1:1 대응시켰다.
  대장 상수(117/32)는 `DemandContractInvariantTests` 쪽에서 드리프트 감지로 따로 지킨다 —
  누가 격자를 118 로 바꾸면 문서 갱신 없이는 통과 못 한다.
- **되돌림 증명 6/6.** 각 불변식이 지키는 성질을 인위로 깨서 FAIL 로 뒤집히는 것을 확인했다
  (고속부 유입 오분류 / 대장 117->118 / 램프 예측 주입 / `boundary_out` 비우기 /
  필드 집합 변조 / 가짜 게이트 추가). 통과만 하고 아무것도 안 지키는 검사가 아니다.

### 한 번 헛디딘 것

producer 필드 집합 검사가 처음에 FAIL 했다. 원인은 정규식 `""([a-z_]+)"":` 이 바깥 래퍼
`""demand"":` 까지 잡은 것 — 계약 위반이 아니라 검사 오타였다. 첫 `{` 이후만 보게 고쳤고,
줄 번호 인덱스 대신 `""demand"": {` 를 포함한 줄을 찾아 **정확히 하나**임을 함께 확인하도록 바꿨다.


## 2026-08-11 (2) — 경계 게이트를 VISSIM 유입에 맞춘다 (작업 1)

**문제.** `generate_real_world_distributed_players.py` 의 경계 leg 루프는 이웃이 안 쓴
정방위마다 게이트를 기계적으로 만든다. VISSIM 을 보지 않으므로 실제 유입이 없는 게이트가
생긴다. 실측: 경계 leg 119개 중 **100개가 대응 유입 없음**.

**바꾼 것.** `--boundary-input-alignment` 를 주면 그 (노드, 방위) 조합에만 게이트를 만든다.
인자가 없으면 기존 동작(하위호환).

### 방위 우선순위 — 이름 접미사가 정본

유입 이름의 진행방향 접미사가 접근 leg 을 정한다(NB->S, SB->N, EB->W, WB->E).
이름이 없을 때만 기하(`leg.link_geometry`)를 쓴다. 근거 22개 중 name_suffix 14 / geometry 8.

이걸 뒤집으면(기하 primary) 게이트 집합이 달라진다 — SC9001 이 S 대신 SE 로,
SC13 이 S 대신 SE 로 간다. 되돌림 증명으로 확인했다: 우선순위를 뒤집으면 검사 2개 FAIL,
되돌리면 11/11 PASS.

### leg 병합 스키마 — 새 type 을 만들지 않았다

SC13_S 는 grid 이웃(SC16)이 점유한다. 사용자 결정은 병합이다.
**같은 방위에 boundary leg 을 나란히 심는 방식**을 택했다 — grid 키는 항상 `방위_이웃ID`
복합 키라 맨 방위 키(`"S"`)가 비어 있다.

새 leg type(예: `grid_boundary`)을 만드는 안은 버렸다. 상류 `_approach_tokens` 가
grid/boundary/ramp 아닌 type 을 **조용히 버리기** 때문에 주입한 수요가 어디에도 안 간다.
grid leg spec 에 `in` 키를 얹는 안도 같은 이유로 버렸다(상류가 안 읽는다).

상류는 이 형태를 이미 지원한다 — `leg_base_dir`(:189-198)이 두 키에서 같은 방위를 뽑고,
`derive_turning_ratios`(:143-151)가 같은 방위 leg 이 여럿인 경우를 균등분배로 처리한다.
phase 도 방위로 정해지므로 병합된 두 접근로는 같은 phase 로 서비스된다.

**부작용.** 상류는 **같은 키**만 배제하지 같은 방위를 배제하지 않는다. 그래서
`SC13_S_to_S_SC16`(외부 유입 -> SC16 방면)과 `SC13_S_SC16_to_S`(SC16 -> 외부 게이트)가
생긴다. U-turn 처럼 보이지만 실제로는 남쪽 측도에서 들어와 남쪽 간선을 타는 회전이라
물리적으로 말이 된다. β 는 각각 0.2.

램프 leg 이 맨 방위 키를 쓰는 경우(SC1001_N, SC1004_S)는 **끊는다**. 그냥 대입하면
램프 leg 를 덮어써 고속도로 결합이 사라진다. 이 상황은 사용자가 결정한 바 없다.

### 확인 못 한 것

- `--link-assignment-json` 을 못 썼다. `link_player_assignment_20260805.json` 에
  `tie_status` 가 없어 N10 가드가 거부한다. 재생성하면 UNRESOLVED(downstream 33 / upstream 6).
  그래서 비교 기준선을 같은 조건(정렬 없음)으로 따로 만들었다.
- 저류 이름 `SC{n}_{leg}_out` 중 62개가 leg 없이 남는다. 생성기 :478 이 용량 JSON 의
  `*_out` 이름을 leg 존재와 무관하게 다시 깔기 때문이다. **기존 동작이고 고치지 않았다.**

---

## 2026-08-11 — 도시부 수요를 지점별로 앵커링했다 (작업 B)

3.66배는 게이트 수 문제가 아니라 **한 스칼라를 117개에 복제하던 구조** 였다.
러너가 게이트별 벡터를 쓰게 바꿨다. 시간축은 이미 앵커돼 있었으므로 공간만 고쳤다.

### 왜 러너 쪽인가 (두 갈래 중 선택)

어댑터가 정렬 산출물을 읽는 안을 버렸다. 근거 셋.

1. **값이 런타임에만 결정된다.** 러너는 `volume × scale × roleMultiplier` 를 곱해서 쓴다
   (`LoadInpxDemandSchedule`). 정적 산출물을 읽는 어댑터는 `-DemandScale` /
   `-DemandProfile` 런에서 조용히 어긋난다. 어긋나도 아무도 모른다 — 3.66배와 같은 종류다.
2. **state JSON 이 실 런의 유일한 계약면이다.** 게이트별 값을 state 에 실으면
   모델이 무엇을 주입했는지 state 파일 하나로 감사할 수 있다. 대장을 어댑터가 들면
   state 만으로는 총량을 못 잰다.
3. **러너는 이미 plant→model 조인을 한다.** `ramp_counts` 가 `RW_RAMP_METER_MODEL_KEYS` 로
   VISSIM 커넥터를 `R_D_W` 같은 모델 키로 바꿔서 같은 state 블록에 쓴다. 새 패턴이 아니다.

어댑터가 inpx 를 파싱하게 하면 `LoadInpxDemandSchedule` 전체(timeInt 파싱, roles CSV,
scale, 역할 배수)를 두 언어로 중복 구현하게 된다.

### 방위 규칙 — 이름이 정본이라는 것을 수치로 확인했다

유입 이름의 진행방향 접미사(`NB→S`, `SB→N`, `EB→W`, `WB→E`)를 1순위로,
없으면 기하 추정(`leg.link_geometry`)을 쓴다. 실측 비교.

    기하만          mapped 11  /  leg_absent 10  /  occupied 1
    이름 + 기하     mapped 19  /  leg_absent  2  /  occupied 1

정렬 산출물 자체가 근거를 준다 — `bearing_convention.ground_truth` 가
"신호그룹 이름 NBT/SBT/EBT/WBT 가 진행방향을 선언하고 접근 leg 은 그 반대" 라고 적혀 있고,
1순위 추정자 `link_chord_reversed` 의 중앙값 오차가 23.7°, 45° 초과 오분류가 11건이다.
선언된 것을 두고 추정을 쓸 이유가 없다.

`구룡터널_NB(터널직진)` 처럼 접미사 뒤에 괄호가 붙는 것이 있어서 정규식은
`_(NB|SB|EB|WB)(?![A-Za-z])` 다. 끝자리 고정으로 잡으면 1,336 veh/h 짜리 입구 하나를 놓친다.

### 전/후 (peak, t=1800 s)

    VISSIM 도시부 총량 32개 입력   19,120 veh/h
      ├ 진짜 입구 22개             16,894
      │   ├ 게이트 붙은 19개       14,564   -> 모델 주입
      │   └ 격자에 없는 3곳         2,331   -> urban_unmapped_volume_vph
      └ 내부 발생 10개              2,226   -> urban_internal_volume_vph

    모델 주입   개정 전 69,909 (3.6562배)  ->  개정 후 14,564 (입구 대비 0.8620)

배율은 6구간 전부 동일하다(전 3.6562 / 후 0.8620) — 시간이 아니라 구조였다는 것이 다시 확인된다.

### 덤으로 닫힌 것 — 진단 부풀림

`stackelberg_mpc._forecast_demand_metadata` 가 `urban_boundary` 전 키를 합산해서
`leader_forecast_boundary_*` 가 (117+119)/117 = 2.0171 배였다. 게이트 앵커링에서
`boundary_out` 값을 0 으로 두니 t=1800 s 에서 진단 합 == 주입 합 == 14,563.6 veh/h 다.
`boundary_out` 이 외생 도착에 안 쓰인다는 판정은 코드로 다시 확인했다(주입 경로 8곳 전부
`kind=="boundary_in"` origin, `models/demand.py:305` 는 모델 자체 시나리오 생성기라 어댑터
경로가 아니고, `rl/*` 는 실 런에서 안 만들어진다).

### fail-closed 를 넣은 이유

대장이 이 망의 유입을 하나도 모르면 `by_gate` 가 통째로 비고, 어댑터는 스칼라 폴백으로
돌아가 **3.66배가 조용히 되살아난다**. 그래서 러너가 `ERROR=URBAN_INPUT_GATE_MAP_UNUSABLE`
로 런을 세운다. 어댑터 쪽도 대칭으로, 모델이 모르는 게이트 이름이 오면 `ValueError` 다.
격자를 재생성하면 대장도 재생성해야 한다 — 안 하면 런이 선다. 그것이 의도다.

망 변형 6종에 대해 대장 적중을 미리 쟀다(34입력 29적중 / 31입력 26적중). 어느 것도
fail-closed 에 걸리지 않는다.

### 남은 것과 하지 않은 것

- **입구 3곳**(`SC1004_SW` 1,400 / `SC1004_SE` 849 / `SC13_S` 81, peak 합 2,331 veh/h).
  게이트 신설 2 + leg 병합 1 은 `config_overrides.network` 재생성의 몫이다
  (`urban_movements` 1,414 와 `turning_ratios` 41 노드가 같이 바뀐다). 검사는 FAIL 로 남겨 뒀다.
  가정으로 3개를 채우면 6구간 전부 **정확히** 보존된다는 것은 검사로 증명해 뒀다
  (`test_gate_anchoring_conserves_entry_demand_on_a_complete_grid`).
- **dummy 10개는 판단하지 않았다.** 경계에서 뺐고, 사실만 state 와 문서에 남겼다.
- **freeway 는 손대지 않았다.** 유입 2 == 링크 2 라 총량 배율은 1.0000 이다. 다만
  기존 검사가 (합, 개수)만 보므로 방향 비대칭이 생기면 못 잡는다는 것을 §4.3 에 적었다.
  램프는 러너가 리터럴 0 이고, `.inpx` vehicle input 34개 중 램프 링크에 놓인 것이
  하나도 없다(확인). VISSIM 램프 교통은 도시부 origin 의 static route 로 들어온다.

### 검사 설계

- 생산자 쪽을 **cscript 로 실제 실행**한다(`scripts/tests/test_urban_gate_demand_vbs_behavior.py`).
  기존 b1a harness 패턴을 재활용해 프로시저만 떼어 낸다. 두 번째 검사는 `WriteStateJson` 의
  demand 줄을 **그대로 떼어 실행**하고 그 출력을 `json.loads` 로 파싱한다 — 콤마 하나
  빠뜨리면 잡힌다.
- 계약 검사의 `test_each_gate_carries_its_own_vissim_input_volume` 가 §4.2 의 약점
  (합·개수만 보는 검사는 방향 비대칭을 못 잡는다)을 도시부에서 닫는다. 고속부는 아직 열려 있다.
- 되돌림 증명 6/6. 어댑터 앵커링 제거 / 미지 게이트 무시 / `boundary_out` 스칼라 /
  러너 조인 제거 / state 필드 제거 / 방위 규칙 뒤집기 — 전부 FAIL 로 뒤집힌다.

### 규율을 어긴 것 하나

대장 생성기(`derive_urban_input_gate_map.py`)는 **검사보다 코드를 먼저 썼다**.
산출물을 사용자가 독립적으로 준 분해(19 / 2 / 1 / 10)와 대조해서 맞는 것을 확인한 뒤
순수 함수 검사 9개를 붙였다. 되돌림 증명은 했다(방위 규칙 뒤집기 → 3건 FAIL).

### 후속 확인 — 22게이트 후보 격자에서는 계약이 완전히 닫힌다

같은 회차에 커밋된 경계 게이트 22개 후보 config
(`real_world_modi_pstack_distributed_core15n41gated_20260811.json`, 승격 아님)에 대해
대장을 재생성하고 계약 검사를 돌려 봤다.

    현 격자 117게이트   불변식 13 PASS / 알려진 불일치 2 FAIL   주입/입구 0.8620
    후보 격자 22게이트  **15/15 PASS**                          주입/입구 1.0000 (6구간 전부)

앵커링 기구는 이미 맞고, 남은 것은 격자뿐이라는 뜻이다. 승격하면 대장을 그 config 로
재생성(`--config`)하고 러너의 `DefaultUrbanInputGateMapPath()` 를 옮기면 된다.

---

## 2026-08-11 (3) — 배정 혈통과 141 대 72 (작업 1)

### 메커니즘 — `tie_status` 가 아니라 `link_to_origins` 가 끊긴다

`tie_status` 자체는 아무 계산에도 안 쓰인다. 오직 생성기의 문지기
(`generate_real_world_distributed_players.validate_link_assignment:151`)가 읽는
승인 플래그다. 실제로 물리량을 바꾸는 것은 그 문 뒤의 `--link-assignment-json` 이다.

    배정 있음   link_to_origins  1,194개   32 -> ['SC1004_to_SC1001']
    배정 없음   link_to_origins    326개   32 -> ['SC1001_N_out','SC1001_S_out','SC1001_E_out','SC1001_W_out']

`derive_movement_signal_group_map.derive_signal_group_phase` 는 SG 의 신호두 링크를
`link_to_origins` 로 origin 에 붙이고, 그 origin 들의 모델 축이 **하나로 모이면**
`origin_movement` 로 phase 를 정한다. 배정이 없으면 링크 32 가 저류 4개에 동시에 붙어
축이 p1·p2 로 갈리고 → `signal_group_name_after_conflict` → SG 이름 규칙으로 떨어진다.

    배정 있음   signal_group_phase_by_method = {origin_movement: 87, signal_group_name: 49}
    배정 없음   signal_group_phase_by_method = {signal_group_name: 136}   ← 전량 폴백

그 결과가 `native_phase_green` 의 분모다.

    SC1001/SC1004  p1 = SG{2,3,4,5,7,8} -> 141.0 s   (배정 있음)
                   p1 = SG{3,4,7,8}     ->  72.0 s   (배정 없음, 이름 규칙)

gated 와 ungated 에서 값이 같다 — 격자 재정렬 탓이 아니라는 브리핑의 판단은 맞다.

### 판정 — 72.0 이 실망이다. 141.0 은 현시가 아니다

`.sig` 원본(`개포동 test-bed1001.sig` prog 1 `mor_peak`)을 XML 로 직접 읽었다.
주기 150 s, 현시 넷이다.

    [0,45]     SG2 EBT  · SG6 WBT
    [48,72]    SG1 WBL  · SG5 EBL
    [75,115/126]  SG4 SBT · SG8 NBT
    [118/129,147] SG3 NBL · SG7 SBL

`.inpx` 신호두 기하로 SG 를 물리 접근 방위에 붙이면 (SG 이름을 안 쓰고) 축이 갈린다.

    링크 32(W 접근) SG2·SG5 | 링크 29·10696(E) SG6·SG1  -> EW 축 69.0 s
    링크 40(S)      SG3·SG8 | 링크 37(NW)        SG4·SG7 -> NS 축 72.0 s

두 축의 동시 녹색은 **0 s** 다. 141.0 = 69 + 72 로, 두 축의 합집합이지 현시가 아니다.
한 현시가 주기의 94% 를 먹을 수는 없다.

### 그러면 왜 141.0 이 나오나 — 격자 leg 방위가 물리 접근과 어긋난다

`derive_intersection_adjacency.py:183` 이 leg 방위를 **두 교차로 중심 사이 방위각**으로
정한다. SC1004 는 SC1001 의 남쪽이라 leg 키가 `S_SC1004` 다. 그런데 그 접근을 나르는
정지선 링크 32 는 SC1001 에 **서쪽에서** 들어온다. 배정 산출물 자신이 이미
`link_leg["32"] = "W"`, `link_leg["71"] = "SW"` 로 알고 있다.

`fixed_signal_schedule.NS_AXIS` 가 leg 키의 방위로 phase 를 정하므로 `S_SC1004` 는 p1 이
되고, 그 origin 을 잡는 SG2·SG5(실제로는 EW 축)가 p1 으로 끌려 들어간다.

되돌림 증명으로 이걸 못박았다 — 검사에서 축 분류에 `W` 를 NS 쪽으로 옮기니
p1 이 정확히 `{2,3,4,5,7,8}` = 141.0 s 가 되고 두 축 겹침이 69.0 s 로 나온다.
**생산 표의 141.0 은 "서쪽 접근을 남쪽으로 본" 결과와 비트 단위로 같다.**

### 혈통 복구 — 승인 경로가 유일하다

`assign_links_to_players` 의 `tie_evidence.status` 는 tie 가 하나라도 있으면
정책과 무관하게 UNRESOLVED 다. 세 정책 전부 downstream 33 · ambiguous upstream 6 이다.
**이 망에서 CLEAR 는 도달 불가능** 이므로 "CLEAR 를 재생성" 은 실재하는 선택지가 아니다.
남는 길은 `--assignment-approval-manifest` 뿐이고, 가드 주석도 그렇게 설계돼 있다.

정책은 `freeway-first` 를 골랐다. 근거는 재현 불가능성이다 — 생산 산출물
`link_player_assignment_20260805.json` 은 구판(897fc0f)이 만든 것인데 그 판은
`downstream` **집합**을 순회하는 deque BFS 라 tie 해소가 문자열 해시 순서에 달렸다.
같은 입력으로 5회 돌리니 귀속이 968 / 972 / 972 / 962 / 958 로 매번 달랐고
생산 산출물(957)과 같은 것은 하나도 없었다. 생산 배정은 **한 번의 난수 추첨** 이다.

    freeway-first  957 / 22 / 226   생산과 범주 개수 일치. 차이는 tie 항목 안에만
                                    (link_owner 3, freeway_bound 값 11, upstream 6)
    lowest-id      957 / 22 / 226   owner 2건 차이 (141, 360)
    signal-first   973 /  6 / 226   16개 링크가 freeway -> signal 로 이동

링크 32·71 의 owner/leg/upstream 은 다섯 번의 구판 실행과 세 정책 전부에서 동일하다.
141.0 판정은 tie 난수의 영향을 받지 않는다.

### 복구 후 실측 (작업 1-4)

새 격자(gated, 경계 leg 22) + 복구된 배정으로 생성하고 매핑을 다시 유도했다.

    미해결 movement  123 -> 37 (전부 synthetic_boundary_leg)
    해소 방법        {name fallback 136} -> {origin_movement 87, signal_group_name 49}
    SC1001/SC1004 p1        141.0 s   ← 생산과 같다. "유지" 된다
    SC1001/SC1004 p2         69.0 s

즉 혈통 복구는 매핑 커버리지를 실제로 되살리고, 그러면서 141.0 결함을 **다시 드러낸다**.
141.0 은 혈통이 만든 것이 아니라 격자 leg 방위가 만든 것이고, 혈통은 그걸 충실히 옮길 뿐이다.

### 하지 않은 것

- **승인 매니페스트에 서명하지 않았다.** `outputs/link_player_assignment_approval_20260811.draft.json`
  은 `approved:false` 초안이다. 이 가드의 목적이 사람의 명시적 승인이므로 에이전트가
  대신 서명하면 가드를 위조하는 것이다. 위 실측은 스크래치패드의 진단용 fixture 로 돌렸고
  그 산출물은 지웠다.
- **격자 leg 방위를 고치지 않았다.** `S_SC1004` -> `W_SC1004` 로 바꾸면 SC1001·SC1004 의
  movement 집합·phase·저류 이름이 전부 바뀐다. 파급이 크고 사용자 결정 사항이다.
- **141.0 이 실 런 TTT 에 얼마나 영향을 주는지는 안 쟀다.** 런이 필요하다.

---

## 2026-08-11 (4) — 유령 저류 62개 (작업 2)

### 먼저 질량을 쟀다

실 관측(`evaluation/runs/capture_n41_20260805`, 상태 51개, 전 링크 평균 2,652.3대)에서
유령 저류로 라우팅되는 링크가 나르는 차량.

    생산 core15n41_20260805 (혈통 있음)   링크 218개   평균 360.9대   전 관측의 13.6%
    gated 후보 (혈통 없음)                링크  15개   평균 119.5대   전 관측의  4.5%
    gated 후보 + 결정적 배정(모의)        링크 237개   평균 325.2대

**브리핑의 "규모 확대" 는 뒤집힌다.** 유령 *이름* 수는 56 -> 62 로 늘지만, 실제로 차가
들어가는 양은 생산 쪽이 크다. 무시할 수준이 아니다.

### 유령이 정말 얼어붙는가 — 코드를 읽지 않고 돌려서 봤다

pre-fix gated config 로 모델을 세우고 `SC5_N_out` 에 50.0대를 넣은 뒤 6스텝 전진.

    유령 SC5_N_out          50.0 대 -> 50.0000 대   (movement 참조 0, sink_storage_links 밖)
    실 게이트 SC1004_SW_out 50.0 대 ->  1.2500 대   (유한 출구용량 게이트가 뺀다)

그런데 `state.total_urban_vehicles(net)` 는 저류 키 **전수**를 더하고
(`models/state.py:1129-1132`), `boundary_leg_vehicles` 는 movement 가 참조하는 경계 저류만
빼므로(`:1209-1221`) 유령 점유는 `objective_urban_vehicles` 와 `protected_accumulation_veh`
에 그대로 남는다. **제어할 수 없는 상수가 목적함수에 앉아 있는 것이다.**

### 원인 — 이름 공간이 셋인데 아무도 대조하지 않는다

    derive_urban_storage_capacity.py:124   상류 SC 가 없는 링크 -> `SC{n}_{링크기하 8방위}_out`
    generate_real_world_distributed_players.py:576  노드 이름만 맞으면 그 이름을 저류로 채택
    grid_topology.build_urban_movements    `{n}_{방위}_out` 은 **그 방위에 boundary leg 이
                                           있을 때만** movement 의 receiving_link 가 된다

세 번째 조건을 두 번째가 안 봤다. 576행의 주석은 "그 방위의 링크가 갈 데를 잃어 224개가
탈락했다" 는 2026-08-05 관측을 근거로 든다 — 탈락을 막으려고 **존재하지 않는 저류를
만들어 준 것**이다. 탈락은 막았지만 차는 죽은 스톡으로 갔다.

### 유령으로 가는 차의 출처 (생산 218링크)

    VISSIM 유입이 링크에 직접 있다(진짜 입구)   34링크  270.9대
    격자에 그 접근 자체가 없다                 180링크   87.5대
    모델 내부구간 멤버인데 상류 BFS 가 놓쳤다     4링크    2.6대

유입 링크 34개는 `boundary_input_alignment_20260811.json` 이 이미 알고 있다. 그중
8개는 `link_geometry` 방위로는 실 게이트에 `aligned` 인데 `assignment` 방위로는
`unaligned` 다 — 같은 접근로에 방위 이름이 두 개 붙은 것이다(배정=centroid_to_link_start,
게이트 대장=유입명 진행방향/링크기하). 즉 **수요는 실 게이트로 들어오고 관측은 유령으로
들어간다.**

### 고친 것

1. `build_network_override` — 유도 용량 대장의 `*_out` 이름은 **그 이름의 boundary leg 이
   실제로 있을 때만** 저류로 받는다. 거부한 이름 수를 콘솔에 찍는다.
2. `build_detector_mapping` — 권위 라우팅이 저류를 못 찾으면 `continue` 로 방위 살포를
   남기지 않고 `link_to_origins[link] = []` 로 비우고 `link_partition.unrouted_links` 에
   {링크: 원했던 이름} 으로 계상한다.

후보 2종을 재생성했다. **저류 키만 바뀐다** — `grid_node_legs`, `urban_movements`,
나머지 값 전부 동일함을 대조했다(gated 211->149, ungated 302->246, 각각 유령 62/56 삭제).

### 질량은 어디로 갔나

어댑터 투영을 실 상태 51개로 전/후 비교했다(생산은 승인 가드 때문에 재생성이 막혀 있어
추적 산출물에 같은 규칙을 메모리에서 적용).

    생산  저류적재 1392.10 -> 1095.32 (유령 296.78 -> 0)
          movement 적재  309.57 ->  344.08 (+34.51)
          미표현          10.37 ->  272.64 (+262.27)
          total_urban   1695.30 -> 1433.03   objective 1374.51 -> 1095.07 (-20.3%)

    gated 저류적재  500.05 ->  460.10 (유령 26.68 -> 0)
          movement 적재  399.17 ->  440.98 (+41.81)
          미표현         934.38 ->  932.53 (-1.85)   용량절단 6.80 -> 4.95

플랜트에서 차가 사라지는 것이 아니다. 모델이 **가지고 있는 척을 그만두는 것**이다.
262.3대는 애초에 어느 movement 도 빼내지 못하는 스톡에 있었다. 이제 그 양이
`unrepresented_by_link` 로 드러난다. gated 후보는 미표현이 오히려 1.85대 줄었다 —
실 게이트와 유령이 나눠 갖던 몫이 실 게이트로 모이기 때문이다.

모델 내부 질량 항등식은 영향을 받지 않는다. 유령은 유입도 유출도 없어 개폐 양변에 같은
상수로 들어갔었다. `src/tests/test_global_mass_conservation.py` 등 vendor 16건 OK 로 확인.

### 남긴 검사

`scripts/tests/test_storage_leg_backing.py` 11건.
- 생성기 단위 — leg 없는 `*_out` 은 저류가 안 되고, 게이트를 주면 살아난다(음성 대조),
  내부 구간은 불변, 저류 키 전수가 leg/movement 참조 안에 있다.
- 라우팅 단위 — 저류 없는 링크는 origin 이 비고 `unrouted_links` 에 잡힌다.
- 산출물 불변식 — `evaluation/configs/*.json` 전수. 아직 못 닫은 것은 `KNOWN_OPEN` 에
  **개수까지** 적었다(늘어나면 실패, 0 이 되면 "목록에서 빼라" 고 실패).

RED 5건을 먼저 봤고, 되돌림 증명은 구 config 를 되돌려 2 FAIL 을 확인한 뒤 재생성으로
복구했다(`git checkout --` 금지 규칙 준수 — 백업 복사본을 썼다).

### 하지 않은 것

- **생산 config 의 유령 56개는 그대로다.** `--link-assignment-json` 재생성이 미서명 승인
  가드에 막힌다(작업 1이 남긴 상태). 위 생산 수치는 그래서 **추적 산출물에 같은 규칙을
  메모리에서 적용해** 잰 것이지 재생성한 것이 아니다.
- **유입 링크 34개를 게이트로 다시 붙이지 않았다.** 물리적으로 그 차들은 그 노드
  boundary_in 대기열에 있어야 하는데, 그러려면 방위 규약 두 갈래를 하나로 정해야 한다.
  임의 휴리스틱으로 붙이는 것은 모델링 결정이라 사용자 몫이다.
- **`_out` 의 의미 충돌을 고치지 않았다.** 모델에서 `out_link` 는 유출 sink 인데 용량
  대장은 유입 approach 기하로 값을 매긴다. 그 결과 실 게이트 22개 중 16개(생산 119개 중
  107개)가 상수 220.0 으로 남고 실측 기하는 전부 유령 쪽에 실려 있었다. 유령을 지운 지금
  실 게이트 용량은 여전히 220.0 이다.
- **default.yaml 의 장난감 격자 이름 7개**(`A_top_out` 등)가 실 config 런타임 저류에
  그대로 남는다(`NetworkConfig` 병합). 관측이 닿지 않아 점유는 0 이지만 leg 없는 스톡이다.
- **실 런을 돌리지 않았다.** TTT 영향은 안 쟀다.

## 2026-08-11 — 정렬 봉인 드리프트와 승격 판단

### (a) 드리프트는 정렬 파일 하나가 아니었다

브리핑은 `boundary_input_alignment_20260811.json` 의 `sources.config.sha256` 한 건을
지목했다. 맞다 — 재생성하니 정확히 그 한 줄만 바뀌었고(e5f8adcb -> aaa7caf7) 게이트 계획
자체(`vehicle_inputs`/`summary`/`bearing_convention`)는 byte 동일이었다. 원인도 지목대로
`a1e73da`(green_max 92 -> 90) 다.

그런데 그 해시로 저장소를 훑으니 같은 값이 네 곳 더 나왔다. 추적 `outputs/*.json` +
`reports/*.json` 100개에서 (경로, sha256) 쌍 229건을 전부 디스크와 대조한 결과.

    낡은 봉인 8건 / 파일 3개
      evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json
        e5f8adcb -> aaa7caf7   (a1e73da)
      evaluation/controllers/vissim_stackelberg_adapter.py
        270478bc -> e7064fab   (700ac87)
      scripts/run_real_world_stackelberg_controller.vbs
        1f70c8be -> dcc5305d   (700ac87, 00ffa40)

    담고 있는 산출물
      outputs/preflight_manifest_v3.json                 (4 포인터)
      reports/plant_fidelity_evidence_manifest.json      (4 포인터)

`preflight_manifest_v3.json` 은 `f31a54e` 에서 마지막으로 재생성됐고 그 뒤로 **26 커밋**이
지났다. 즉 프리플라이트 사슬은 낡은 어댑터 + 낡은 러너 + 낡은 config 에 묶여 있다.

### 왜 26 커밋 동안 아무것도 안 깨졌나 — 검증이 셋 다 공허하다

세 곳이 해시를 **기록만** 하고 **대조하지 않는다.** 코드를 직접 읽고 확인했다.

    audit_plant_fidelity.py:2950   input_provenance 게이트는 `is_file` 만 본다.
                                   매 실행 새로 해싱하고 이전 봉인과 비교하지 않는다.
    preflight_manifest_v3.json     artifact.*.sha256 검사의 expected 가
                                   "non-empty SHA-256" 이다. 비지 않으면 PASS.
    run_readiness.py:160           seal_sha256 이 **있는지**만 본다 (작업 4가 이미 지적).

그래서 감사 게이트 `input_provenance` 는 낡은 봉인 3건을 안고도 PASS 다. 실제로 재실행해
확인했다 — 게이트 12 PASS / 16 NE / 0 FAIL 로 추적본과 **완전히 동일**하다.

이번에 넣은 `TrackedArtifactSealTests` 는 정렬 파일 하나에 대해서만 그 구멍을 막는다.
나머지 둘(preflight, evidence manifest)은 **여전히 무방비다.**

### (b) 승격 판단 — NO-GO. 세 가지가 각각 독립적으로 막는다

**1. 혈통을 실은 재생성이 미서명 승인 가드에 막힌다.** 실행해서 확인했다.

    --link-assignment-json 만                 -> "link assignment has unresolved or
                                                 unverifiable topology ties; refusing
                                                 to generate live artifacts"
    + --assignment-approval-manifest (초안)   -> "assignment approval is not approved"

가드는 `generate_real_world_distributed_players.py:151-170` 에서 네 겹이다 —
CLEAR 여부 / 매니페스트 유무 / `approved is True` / `approved_by`+`reason` 비어있지 않음.
초안은 `approved:false`, `approved_by:""`, `reason:""` 라 세 겹에 걸린다.
**에이전트가 대신 서명하면 가드를 위조하는 것이므로 하지 않는다.** 작업 1의 판단을 유지한다.

**2. 지금 있는 후보를 그대로 승격하면 혈통이 사라진다.** 후보 2종은 혈통 없이 생성됐다.

    산출물                          link_to_origins   observable_links   link_partition
    production core15n41_20260805        1,194             1,207            있음
    gated_20260811 후보                    326               339            **없음**
    ungated_20260811 후보                  326               339            **없음**

`link_partition` 이 없다는 것이 `--link-assignment-json` 없이 만들어졌다는 직접 증거다.
이대로 승격하면 라우팅 혈통 868링크가 날아가고 SG phase 가 전량 이름규칙 폴백이 된다
(작업 1 측정: resolved 416 -> 187, `signal_group_name` 136건).

**3. 새 격자는 141.0 결함을 고치지도 않는다.** 승격 기준이 "141.0 유지" 였는데,
격자 leg 방위를 직접 대조하니 세 config 가 전부 동일하다.

    배정이 아는 물리 접근 leg    link 32 = W (SC1001<-SC1004) · link 71 = SW (SC1004<-SC1001)
    production                   S_SC1004 / N_SC1001
    gated_20260811 후보          S_SC1004 / N_SC1001   <- 같다
    ungated_20260811 후보        S_SC1004 / N_SC1001   <- 같다

이번 격자 재정렬이 건드린 것은 **경계 leg**(119 -> 22)이고 `grid` leg 은 안 건드렸다.
141.0 의 원인은 grid leg 방위이므로 승격해도 그대로 옮겨온다. `tests/
test_native_phase_axis_composition.py` 의 KNOWN MISMATCH 4건은 승격해도 안 닫힌다.

정리하면 승격의 이득은 수요 주입 0.8620 -> 1.0 하나뿐인데, 비용은 (1) 사람 서명 위조 또는
(2) 혈통 868링크 상실이다. 어느 쪽도 받을 수 없다. **승격하지 않는다.**

### 하지 않은 것

- (c)(d)(e) 사슬·신호 체인·봉인 재생성 — 전부 승격을 전제로 한 작업이라 안 했다.
  특히 (e)는 작업 4가 정한 "격자 semantic hash" 생산자가 아직 **코드로 없다.**
- 감사 `reports/` 정본을 안 건드렸다. 임시 경로로만 돌렸고 `git status` 로 확인했다.
- 실 런을 안 돌렸다. 141.0 의 TTT 영향은 여전히 미측정이다.

### (g) 전 스위트 실측 — vendor 스위트가 원래 초록이 아니다

작업 1이 못 돌린 `scripts/tests` 40모듈을 모듈별 subprocess 로 전부 돌렸다(552건 OK).
`plant/tests` 11모듈 132건도 OK. `tests/` 154건 중 11 FAIL 은 전부 의도된 KNOWN MISMATCH
(demand 7 + axis 4)다.

vendor 스위트는 이번에 처음 전수로 돌렸다. 지난 회차는 16건만 봤다.

    45 모듈 중 37 OK / 8 not OK   (실행된 모듈 합계 278건)
      TIMEOUT 200s      test_constraints, test_six_controller_comparison
      NO TESTS RAN      test_demand_scenarios
      FAILED            test_forecast_awareness (4F+1E)  test_post_analysis (2F)
                        test_rl_ddqn (1E = torch 미설치)  test_segment_local_plant (2F)
                        test_wu_faithful_follower (1F+2skip)

내 변경 탓이 아니다. `vendor/` 는 `b879269` 이후 이 브랜치의 어느 커밋도 안 건드렸고
(`git log 3379f1b..HEAD -- vendor/` 비어 있음, working tree 도 clean), 실패 내용도
freeway VSL / off-ramp forecast / segment coupling 같은 상류 모델 거동이다. 다만
**이 상태가 언제부터였는지는 확인하지 못했다** — 이전 회차들이 전수를 안 돌렸다.
vendor 수정 금지라 손대지 않았다.

## N4-0 작업 1 — 4현시 재작성이 왜 관문에서 막혔나 (2026-08-12)

### 먼저 실물을 열었다

`.sig` 만 읽었으면 15 SC 전부 4현시로 접을 수 있다고 보고했을 것이다. 실제로 SG 이름은
15 SC 전부 WBL/EBT/NBL/SBT/EBL/WBT/SBL/NBT 여덟 개(SC5 만 24개)로 똑같고, 녹색창도 전부
존재한다. 그런데 inpx 의 `signalHead` 를 세면 다른 그림이 나온다.

    SC1    WBL·EBL      등두 0   -> major 좌회전이 물리적으로 없다
    SC105  WBL·EBL      등두 0
    SC11   NBL·SBL·EBL  등두 0
    SC107  SBT·NBT      등두 0   -> minor 직진이 없다(좌회전만 있는 부도로)
    SC108  NBL·SBL      등두 0   -> minor 좌회전이 없다
    SC109  WBL·NBL·SBT·NBT 등두 0 -> T 형(EBT·WBT·EBL·SBL 만 존재)
    SC1003 EBT·WBT·EBL·NBL 등두 0
    SC1005 WBL·EBL·SBT·NBT·NBL 등두 0
    SC5    9~24 중 11개 등두 0 (나머지 5개는 midblock 슬레이브)

등두가 없는 SG 는 VISSIM 에서 차량 흐름에 아무 영향을 주지 않는다. 그 SG 에 녹색을 준
현시는 **처리량 0 으로 주기를 태우는 현시**다. 이름이 있고 `.sig` 에 녹색창이 있다는
것만으로 "그 이동류가 있다"고 단정했으면 또 뒤집혔다.

### SC5 의 24개는 교차로 24개 이동류가 아니다

SG 9~24 는 midblock 슬레이브다. 부모 SG = `((n-1) mod 8) + 1`
(`outputs/urban_follower_midblock_signal_mapping_20260731.md` 가 정본). 이걸 현시 평균에
넣으면 SC5 major 직진이 50 → 61 s 로 부풀고 단계 수가 4에서 어긋난다. 생산자에서 제외했고
검사가 그 제외를 잡는다(제외를 지우면 3건 RED).

### 러너 상수와 실 `.sig` 의 clearance 가 다르다

실 `.sig` 136 SG 의 amber 는 **전부 3.0 s 정확히 하나**다. all-red 는 없다. 러너의
`AMBER_SEC 3 + ALL_RED_SEC 2 = 5` 는 실 프로그램과 이미 다르다. 목표 스펙의 clearance 3 은
러너를 바꾸는 것이지 `.sig` 를 바꾸는 것이 아니다.

### 재배분 규칙 — 왜 "현시별 평균"인가

dual-ring 을 하나로 접을 때 각 현시의 값을 두 링의 **평균**으로 잡으면, 같은 배리어 안에서
두 링이 각각 총량 B 를 채우므로 두 현시 평균의 합이 자동으로 B 가 된다. max 를 잡으면
SC1001 minor 가 51+29=80 > 69 로 넘치고, min 을 잡으면 40+18=58 로 모자란다. 평균만이
배리어 총량을 보존한다. 실측으로 15 SC 전부에서 성립했다.

주기가 이미 150 인 7 SC(11·105·1001~1005)는 유효녹색이 이미 138 이라 축소율이 1.0 이고
절대 초까지 보존된다. 160 은 148→138(×0.932), 140 은 128→138(×1.078), 170 은 161→138(×0.857).

### 멈춘 이유 — 산술 위반 3 SC

    SC107  minor 직진 0.00 s  < 20   (SBT·NBT 자체가 없음)
    SC108  minor 좌   0.00 s  < 20   (NBL·SBL 자체가 없음)
           major 직진 86.57 s > 78
    SC109  major 직진 109.95 s > 78,  major 좌 19.00 < 20,
           minor 직진 0.00 < 20,      minor 좌 9.05 < 20

SC109 는 그 위에 구조가 더 깨져 있다. EBT 가 0~144 s 로 **두 단계에 걸쳐** 녹색을 유지해
`(주기 − 유효녹색)/3` 이 17.5 로 정수가 아니다. 현시 개념 자체가 안 선다.

이 셋은 배분 조정으로 못 푼다. 없는 이동류에 20 s 를 주는 문제이기 때문이다.

### 확인 못 한 것

- SC107 의 부도로가 정말 좌회전 전용인지 **지도로 확인하지 않았다.** 근거는 inpx 의
  등두 배정 하나뿐이다(`SBT`·`NBT` 에 head 0, `NBL` 3개·`SBL` 3개).
- 등두 0 이 "기하가 없다"인지 "비신호 이동류"인지 구분하지 않았다. 어느 쪽이든 VISSIM
  거동은 같지만(녹색을 줘도 무영향) 스펙 판단은 갈릴 수 있다.
- `.sig` 를 하나도 안 썼다. 원본 15개 전부 손대지 않았고 inpx `supplyFile2` 도 그대로다.

## N4-0 작업 3 — 러너 clearance 를 실 프로그램에 맞추면 무엇이 따라 움직이나 (2026-08-12)

### 실물부터 열었다 — 실 `.sig` 의 clearance 는 amber 3 뿐이다

제어 15 SC 의 활성 프로그램(inpx `supplyFile2` + `progNo`)을 `parse_sig` 로 전부 열었다.
`signalsequence` 는 15 SC 전부 하나뿐이다.

    display 1:RED(1.0) -> 3:GREEN(5.0) -> 4:AMBER fixed 3.0

녹색창 118개 중 116개에서 amber = 3.0 s 이고, 녹색이 끝나고 **다음 SG 의 녹색이 시작될
때까지의 간격**도 3.0 s 다. 즉 all-red 는 0 이다. 나머지 2개(SC5 SG10·SG14)는 주기 경계에서
잘린 같은 녹색의 두 조각이라 전이가 아니다.

amber 만 재면 "3 s 다"까지밖에 못 말한다. all-red 가 없다는 것은 **다른 자**로 확인했다 —
SC 마다 `|녹색창 ∪ 황색창| == 주기` 다(15/15, 오차 0). 전 SG 이 동시에 적색인 순간이
한 번이라도 있으면 그 구멍만큼 합집합이 짧아진다.

그래서 목표 clearance 3 은 `AMBER_SEC 3 + ALL_RED_SEC 0` 이다. amber 를 줄이는 것이 아니라
all-red 를 없애는 것이다.

### 한 곳만 고치면 조용히 어긋나는 자리가 실제로 있었다

`ALL_RED_SEC` 는 러너 안에서만 쓰이는 값이 아니다. 어댑터가 action CSV 의 `signal_sg` 행에
싣는 **계획 주기**가 같은 상수로 계산되고, 러너는 그것을 자기 축 주기와 대조해
0.001 s 라도 다르면 그 SC 를 통째로 거부한다(`ERROR=SIGNAL_SG_PLAN_CYCLE_STALE`, :1453).

    scripts/derive_signal_group_actuation_plan.py:54  AMBER_SEC/ALL_RED_SEC 리터럴
      -> outputs/signal_group_actuation_plan_v3.json 의 amber_sec/all_red_sec
      -> vissim_stackelberg_adapter.signal_group_action_rows 가 읽어 plan_cycle_sec
      -> action CSV green_sec 열
      -> 러너 :1453 대조

러너만 고치고 이 사슬을 안 고쳤으면 런은 **15 SC 전량 거부**로 죽는다. 검사로는 안 잡혔을
것이다 — 정적 검사가 아니라 런타임 대조이기 때문이다. 그래서 생산자와 어댑터가 러너 원문을
읽게 바꾸고(`plant_cycle.runner_clearance_sec`), 계획 표에 키가 없을 때 떨어지는 기본값도
리터럴에서 러너 유도값으로 바꿨다. 그 기본값이 리터럴로 돌아가면 깨지는 검사를 새로 넣었다
(되돌림 증명 확인).

추적 계획 산출물은 재생성했다. `all_red_sec` 한 줄만 2.0 -> 0.0 이고 나머지는 바이트 동일이다
(SG 136 · 창 118 · 충돌쌍 312 · 위반 0 전부 그대로). `*_sgplan.vbs` 형제 3개는 sha 한 줄만
바뀐다. `reports/plant_fidelity_evidence_manifest.json` 이 이 계획의 옛 sha 를 들고 있는데,
감사 재실행으로 추적 `reports/` 를 덮지 말라는 지시라 **그대로 뒀다 — 이제 낡았다.**

### 러너를 실제로 돌려서 잰 것

`cscript` 로 러너에서 프로시저를 그대로 떼어 돌렸다(실 COM 런은 못 한다).

    MaxSignalCycleSec       69 / 69 (유효녹색 138)  ->  주기 144      150 이 아니다
                            57 / 57 (실 캡처)       ->  주기 120
    SignalActionValuesValid 118 / 20 (상자 끝)       ->  거부(상한 90)

실 계획 15 SC 를 먹여 `SignalGroupStateFromPlan` 을 주기 전체에 대해 조각으로 재면
amber 정확히 **6.00 s/주기**(= 2 전이 x 3 s), dark 0.00 s, amber-over-green 0 셀이다.
축 경계 amber 는 all-red 가 사라져도 살아 있다 — 다음 축의 녹색이 `major + 3` 에서
시작하므로 `[major, major+3)` 구간에는 녹색인 SG 가 없기 때문이다.

### 150 이 왜 아직 안 나오나 — 두 겹의 벽

첫째, 러너 주기 식은 clearance 를 **두 번**만 더한다. 축이 둘이라 축 경계도 둘이다.
계획 구동이 켜져도 축 **안의** SG 경계에는 clearance 가 없다(`_cumulative` 가 native 간격을
짜내 창을 붙여 펴고, 러너가 그 경계의 amber 를 억제한다). 4현시란 그 축 안 경계를 전이로
승격시키는 일이고, 그때 비로소 lost_time 이 4 x 3 = 12 가 된다.

둘째, 설령 식을 4전이로 바꿔도 **두 축짜리 지시값**으로는 138 을 실을 수 없다. green_min 20
을 한쪽에 주면 반대쪽이 118 s 인데, 러너의 쓰기 계약(`SignalActionValuesValid`)과 어댑터
클램프가 축당 [5, 90] 이다. 4현시로 쪼개면 현시당 최대 78 이라 그 벽에 안 닿는다.

### 모델 주기 5건이 빨간불인 채로 둔 이유

플랜트 lost_time 이 10.0 -> 6.0 이 됐는데 생산 config 는 `lost_time 10.0` 그대로다.
`tests/test_model_plant_cycle_identity` 의 생산 항등성 3건 + 승격 후보 2건이 그 4 s 를
빨간불로 들고 있다. 단언을 느슨하게 하는 것은 이 파일의 존재 이유를 지우는 일이라 안 했다.

닫는 길 둘 다 모델 쪽 결정이다.

  (a) 2현시 유지 + 모델 주기 116 — 녹색 예산 110 과 상자 [20, 90] 이 그대로라 리더 행동은
      비트동일하고 분모만 정확해진다. 다만 `green_budget_contract` 가 `cycle_length` 를
      부모에서 읽고 `green_max` 를 유도하는 구조라 유도 방향을 뒤집어야 한다. 그대로 두고
      `lost_time` 만 6 으로 내리면 `green_max` 가 94 가 되고 쓰기 클램프 90 에 물려
      주기가 다시 어긋난다(계산 확인).
  (b) 목표 스펙대로 4현시 — lost 12 · 주기 150 · green_max 78. 러너 주기 식과 어댑터의
      축 2개 지시 구조를 같이 바꿔야 한다.

### 확인 못 한 것

- **실 COM 런은 못 했다.** VISSIM 을 띄우지 않았다. 위 수치는 전부 러너 프로시저를 떼어낸
  cscript 실행과 파이썬 재현이다. 실제 런에서 `SIGNAL_SG_PLAN_CYCLE_STALE` 이 안 뜨는지는
  런을 해야 안다.
- 다른 러너 5개(`_perf`, `_8seg`, `com_fixed_time`, `calibration_probe`,
  `run_stackelberg_vissim_controller`)와 분석 스크립트 2개(`analyze_signal_green_fit`,
  `analyze_signal_service_curve`)에 같은 상수 사본이 남아 있다. 실 런 경로가 아니라
  안 건드렸다. 분석 스크립트는 **과거 런**을 해석하는 도구라 바꾸면 옛 런을 잘못 읽는다.
- `scripts/generate_real_world_distributed_players.py:164` 주석의 "러너 clearance 가 10 s"
  는 이제 틀렸다. 그 파일은 직전 회차의 미커밋 작업이 올라가 있어 손대지 않았다.

---

## N4-0 작업 4 — action CSV 스키마 v3(축 2값) → v4(현시 4값) (2026-08-12)

### 무엇이 정본인가 — 지시서가 물은 것

`signal_sg` 행이 이미 SG별 타이밍을 싣는데 현시 4값과 무엇이 정본인지 정하라고 했다.
플랜트 실물을 읽고 정했다.

러너의 계획 구동 경로(`ApplyRuntimeSignalControllerFromPlan`)는 축 녹색을 **쓰지 않는다.**
그 함수가 받는 것은 `pos` 와 `cycle` 뿐이고, SG 상태는 `CommitSignalGroupPlan` 이 저장해
둔 창에서 나온다. 즉 v3 시점에도 `major_green`/`minor_green` 은 이미 (a) 주기의 가수와
(b) 계획 staleness 대조값 두 가지 역할뿐이었다.

그래서 v4 의 결정은 이렇다.

    signal 행의 현시 4값   = 모델의 결정. **정본**.
    signal_sg 창           = 어댑터가 signal_group_plan 으로 유도한 **파생**.
    러너                    파생을 다시 만들지 않는다. 만들 수 없다 - 창 분수는 실 .sig
                            파싱에서 나오고 그 파서는 파이썬에 있다. 러너는 대조만 한다.

대조식은 `Sum(현시 녹색) + (녹색 있는 현시 수) x clearance == 모든 signal_sg 행의 green_sec`
이고, 어긋나면 `SignalGroupPlanRejectReason` 이 그 CSV 를 통째로 거부한다. VISSIM 에 실제로
실리는 값이 파생이라는 것과 정본이 `signal` 행이라는 것은 모순되지 않는다 - 매 결정마다
파생이 정본에서 나왔음이 위 항등식으로 증명되기 때문이다.

### clearance 계수를 데이터로 만든 이유

v3 러너는 주기에 clearance 를 **두 번** 더했다(축이 둘). 목표 스펙은 4현시 4회다.
그런데 지금 계획 산출물은 현시가 둘뿐이다 - `.sig` 재작성(작업 1)이 사용자 결정 대기라
4현시 phase→SG 귀속이 아직 없다. 상수 4 로 박으면 오늘 15 SC 가 전량 거부되고, 상수 2 로
두면 4현시가 와도 주기가 6 s 모자란다.

그래서 계수를 **녹색이 있는 현시의 수**로 만들었다(`live_phases`). 오늘 데이터(p3=p4=0)에서
2 가 나와 v3 과 값이 같고, 계획이 4현시가 되는 날 코드 변경 없이 4 가 된다. 어댑터와 러너가
같은 식을 각자 구현하므로(파이썬/VBScript) 둘이 갈라지면 위 대조가 잡는다.

**0 을 조용한 폴백으로 쓰지 않기 위해** 어댑터에 짝이 되는 게이트를 걸었다 - 액션이 녹색을
준 현시 집합과 계획이 SG 를 붙여 둔 현시 집합이 다르면 예외다. 계획이 4현시인데 모델이
2현시 값을 주면(= 지금 vendor 스냅샷 상태) 그 순간 죽는다.

### 창 배치 순서 — 아직 임시다

`phase_layout_order(major_maps_to)` 는 major 축 현시를 맨 앞에 두고 나머지를 모델 phase
순서로 둔다. major 를 앞에 두는 것은 v3 배치와 2현시에서 **비트 동일**하게 만드는 조건이고
(`tests/test_signal_group_plan` 13건이 창 좌표를 그대로 고정한다), 나머지 셋의 상대 순서는
근거가 없다. 목표 스펙의 순서(major 직진 → major 좌 → minor 직진 → minor 좌)는 phase →
이동류 귀속이 있어야 쓸 수 있고 그것이 작업 1의 미결 사항이다. **4현시 계획이 실제로 생기면
이 함수가 순서를 받아야 한다.**

### 옛 action CSV 8,201개 — 버전 필드를 두지 않았다

헤더가 이미 판별자다(`major_green` 이 있으면 v3, `p1_green` 이 있으면 v4). 열을 하나 더
늘려 버전을 싣는 것은 모든 행에 같은 값을 반복하면서 헤더가 이미 주는 정보를 중복하는 일이라
안 했다. 옛 파일은 다시 쓰지 않는다 - 읽는 쪽 4곳을 `action_csv_schema.phase_green_sum_sec`
/ `window_bounds_sec` 으로 옮겨 두 세대를 같은 코드로 읽게 했다.

`validate_baseline_snapshot` 은 **두 헤더 목록 중 하나와 정확히 같을 것**을 요구한다.
느슨해진 것이 아니라 세대가 둘이다(봉인된 스냅샷은 v3, 새로 뽑으면 v4).

### 이름 규칙 폴백을 잘라낸 판단

v3 러너는 계획이 없으면 `SignalStateForGroup` 의 이름 규칙(EB/WB→major, NB/SB→minor)으로
떨어졌다. 현시 4값을 그 두 상태로 재생하면 네 현시가 조용히 두 축으로 접힌다. 그래서
`signal` 행이 계획 없이 오면 CSV 를 거부한다(`ACTION_CSV_SIGNAL_WITHOUT_PLAN_CONFIG`).

이것이 실질적 변화가 아닌 근거 - 어댑터는 계획 산출물이 있으면 `signal_sg` 행을 **무조건**
싣고(`write_action_csv` 호출부가 하나뿐이고 `load_signal_group_actuation_plan()` 을 그대로
넘긴다), 계획 config 가 없는 러너는 그 행들을 이미 전부 invalid 로 셌다. 즉 이름 규칙
경로는 **이미 도달 불가능**했다. 바뀐 것은 그 사실이 명시적이 된 것뿐이다.

`SignalStateForGroup`/`ApplyRuntimeSignalController` 는 지우지 않았다 -
`scripts/tests/test_signal_group_plan_real_plan_actuation.py` 가 "이름 규칙이었다면 어땠는지"
의 **대조군**으로 이 두 프로시저를 cscript 로 떼어 돌린다. 대신 `SIGNAL_NAME_RULE_FALLBACKS`
echo 는 이제 자명하게 0 이므로 증거로 쓸 수 없다.

### 확인 못 한 것

- **실 COM 런은 안 했다.** VISSIM 을 띄우지 않았다. 러너 쪽 수치는 전부 러너에서 프로시저를
  떼어낸 cscript 실행이다. 실 런에서 15 SC 가 통과하는지는 런을 해야 안다.
- **4현시를 15 SC 전부로 재지 못했다.** 실 4현시 계획이 없다. `Real4PhaseWindowTests` 는
  실 `.sig` 의 SC1001 하나를 SG 이름으로 네 현시에 묶어 잰다. 나머지 14 SC 는 안 쟀고,
  작업 1의 조사에 따르면 그중 8개는 목표 현시 중 등두 0 인 현시를 갖는다.
- **다른 러너 3개(`_perf`, `run_stackelberg_vissim_controller`, `_8seg`)를 안 옮겼다.**
  셋 다 같은 어댑터를 부르므로 지금 그 셋으로는 못 돈다(헤더 불일치 → 전량 거부).
  실 런 경로가 아니라는 판단이고, 인벤토리 검사가 이 목록을 고정한다.
- **미추적 `scripts/test_strict_actuation_contract.py` 에 v3 헤더 리터럴이 남아 있다.**
  직전 회차의 미커밋 작업이라 손대지 않았다.
- **모델 주기 동일성 5건은 그대로 빨간불이다.** 작업 3이 남긴 것과 같은 건이고, 이 작업은
  모델 config(`lost_time`)를 건드리지 않았다.
- **vendor 스냅샷은 여전히 2현시다**(`vendor/NumSim-mine/src/models/state.py` 에
  `MODEL_PHASES` 가 없다 = 4현시 이전 스냅샷). 실 런의 모델은 p1/p2 만 낸다. 어댑터는
  p3/p4 를 0.0 으로 채우고 계획도 2현시라 오늘은 정합하지만, **상류와 vendor 가 어긋나 있다**
  는 사실은 작업 2가 남긴 그대로다.
