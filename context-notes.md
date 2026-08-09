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
