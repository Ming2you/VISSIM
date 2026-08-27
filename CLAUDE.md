# VISSIM Stackelberg MPC — 작업 규칙

## 정본 (default). 재유도하지 말고 읽어서 써라

2026-08-19 에 토폴로지를 전면 재생성하고 사용자가 전수 검토해 확정했다.
**이보다 이전 세대(core15\*, n4dr150\*, pedovr/pedovrx\*, up10701\*, adjacency8\*, pedfold\*,
core17legs4(=b 없는 판))를 기본값으로 쓰지 마라.** 되돌아간 적이 두 번 있다.

| 역할 | 경로 |
| --- | --- |
| 진입점 | `scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1` (유일한 정본 러너) |
| 망 원본 | 아래 "망 정본이 둘로 갈려 있다" 참조 |
| **어댑터** | `evaluation/controllers/vissim_stackelberg_adapter.py` — **유일하다.** 사본을 만들지 마라 |
| **값** | `evaluation/parameters.json` — 값의 단일 출처. 읽는 문은 `evaluation/parameters.py` 뿐 |
| **시나리오** | `evaluation/configs/canon_{tau,bstoA,plantfix,fdfit}_20260827.json` — 자립(extends 없음) |

### 2026-08-27 정본 통합 — 되돌리지 마라

어댑터 19벌(155,827행)·config 139개(사슬 24단)를 어댑터 1벌·config 4개로 합쳤다. 구버전은
`evaluation/controllers/_superseded_20260827/` 와 `evaluation/configs/_superseded_20260827/`
에 MANIFEST(sha256 + 그것을 쓴 런)와 함께 있다. **거기서 꺼내 쓰지 마라.**

값은 `parameters.json` 하나에만 적는다. 규칙 셋을 코드가 강제한다.

1. 코드에 상수를 박지 않는다. `parameters.require()` 에는 **기본값 인자가 없다** — 키가
   없으면 예외다. 조용한 폴백이 FD 사고(재적합값이 컨트롤러에 한 번도 도달 못 함)의 원인이었다.
2. 파생량은 `parameters.py` 의 함수로만 계산한다 — `leader_rollout_depth`,
   `effective_green_total`, `phase_green_max`, `urban_occupancy`. 같은 식을 두 곳에 쓰면
   `leader_value_depth` 사고(지평 3인 줄 알았는데 리더는 6)가 재발한다.
3. 시나리오가 값을 다르게 가져가려면 **config 에 명시**한다. 그 차이는
   `_canonical_parameters.overridden_by_tuning` 진단에 남고, 아래 검사기가 확인한다.

```bash
python scripts/verify_parameters.py evaluation/configs/canon_plantfix_20260827.json
```

정본 파라미터가 실효값이 됐는지, 선언 없는 어긋남·순수 중복이 없는지, 파생량이 정합한지
검사한다. 정본 런처 7개가 사전점검 뒤에 자동으로 부른다. **순수 중복(config 가
parameters 와 같은 값을 또 적는 것)은 FAIL 이다** — tuning 이 parameters 를 이기므로
`parameters.json` 편집이 조용히 무시된다.

plant 나 모델 상태를 고칠 때는 사본을 만들어 검증한 뒤 정본으로 승격하고 **사본을 지운다.**
사본을 남긴 채 플래그로 옛 경로를 보존하는 것이 어댑터 19벌을 만든 습관이다.
| player 권역 | `outputs/urban_player_territory_v1_20260819.json` |
| 인접표 | `outputs/intersection_adjacency_core17legs4b_20260819.json` |
| 제어 매핑 | `evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json` |
| 경계 leg | `evaluation/real_world_modi_inventory/boundary_extra_legs_legs4b_20260819.csv` |
| 유입 게이트맵 | `evaluation/real_world_modi_inventory/urban_input_gate_map_legs4b_20260819.csv` |
| 액추에이션 계획 | `outputs/signal_group_actuation_plan_v3.json` (17 SC) · 형제 `evaluation/generated/<config>_sgplan.vbs` |
| SG 타이밍 | `outputs/signal_group_timing_v3.json` (17 SC) |
| movement→SG | `outputs/movement_signal_group_map_v3.json` (권역 기반 link_to_origins 로 유도) |
| link_to_origins | detector mapping 안. 생성기 `scripts/build_link_to_origins_territory.py` |
| 저류 용량 | config 인라인 160키 · 근거 `outputs/urban_storage_capacity_core17legs4b_20260819.json` |
| 보호망 경계 회전 | `outputs/pn_boundary_turns_v1_20260819.json` |
| 예측 보정 | `evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json` |

## 망 정본이 둘로 갈려 있다 (미해결)

- 정본 러너 `scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1:84` 의 기본값은
  `network/real_world_gaepo_modi/modi_eval_rw_control.inpx` 다.
- 권역 정본 `outputs/urban_player_territory_v1_20260819.json` 의 `sources` 는
  `network/real_world_gaepo_modi/modi_eval_userfix_20260814d.inpx` 를 sha256 과 함께 pin 한다.

세 망(rw_control 3,029,864 B / userfix_d 3,028,367 B / userfix_e 3,047,783 B)은 서로 다른 파일이다.
**단순 경로 치환으로 맞추지 마라.** 어느 쪽이 정본인지 별도 판정이 필요하다.

다만 보호망 경계 판정은 두 망에서 **완전히 같다** (2026-08-19 확인). 회전 303개의
`(from_link, connector, to_link, class, controllable, flow)` 가 전부 일치하고
`control_surface` · `constant_load` · `leg_zone` 도 동일하다. 두 망의 차이는
커넥터 1개(`10613`: 387 -> 1220000201, rw_control 에만 있음)와 신호두 배치 3링크
(`29` · `10696` · `57` — SC1001 sg1 이 링크에서 커넥터로 옮겨간 것 등)뿐이고,
어느 것도 경계 판정에 닿지 않는다.

## 두 가지는 절대 재유도하지 않는다

**player 권역** — `outputs/urban_player_territory_v1_20260819.json` 을 읽어서 쓴다.
자동 규칙이 실제 망과 어긋나는 자리가 여럿이다: `link 21` 은 신호두가 SC108 인데 권역은 SC109,
`SC1·N_SC11` 은 신호군이 WBT 라 실제로는 E, 지상/지하차도를 갈라야 하는 SC107·SC1004·SC1005 등.
파일 안에 `regeneration_policy`, `decision_log`(15건, 근거 포함), `sources`(sha256) 가 다 있다.

**보호망 경계 판정** — 생성기로만 다시 만든다.

```bash
python scripts/derive_pn_boundary_turns.py
```

```bash
python scripts/build_pn_boundary_map.py
```

leg 에 구역(내부/경계면/외부)을 매기고 전이표로 판정한 뒤, leg 의 **정지선 링크**에서 나가는
커넥터로 실체화한다. `(from_link, connector, to_link)` 가 VISSIM 런타임 주소다.

```
내부->내부 internal · 내부->외부 outflow · 경계면->내부 inflow
경계면->외부 external · 외부->내부 inflow · 외부->외부 outside_pn
```

기대 산출: leg 내부 67 · 경계면 18 · 외부 36 / 회전 306 / **통제 가능 경계 74**
(유입 32 · 유출 34 · 외부통과 8) / **상수 부하 3,920 veh/h**.
수치가 다르게 나오면 입력이 바뀐 것이다. 규칙을 고치지 말고 입력을 확인해라.

### 되돌리면 안 되는 규칙 다섯

1. **경계면 우선** — 한 링크를 경계면 leg 와 내부 leg 가 같이 물면 경계면이 이긴다.
   내부로 흡수되면 그 자리의 유입·유출이 사라진다 (SC107·S 의 링크 378·379).
2. **도착 구역은 하류로 걷는다** — 교차로 직후 진출 카리지웨이 25곳이 무소유다.
   그대로 두면 통제 SC 사이 구간인데도 유출로 찍힌다.
3. **양끝이 버퍼면 횡단이 아니다** — 정지선 앞 회랑 안의 이동이라 세면 이중계상이다.
   제외 5개: `10229 10604 10605 10637 10640`.
4. **relFlow 는 비어 있으면 1** (0 아님). 0 으로 읽으면 지하차도 경로가 통째로 사라진다.
   static route decision 130개 중 68개가 빈 relFlow 를 갖는다.
5. **정지선 바깥 진입도 줍는다** — 진입 줄기가 무소유면 그 횡단이 통째로 안 보인다.
   단 상류가 있는 mid-block 링크와 freeway 는 제외한다(259·336 이 가짜 유입으로 잡혔다).
6. **`FORCE_PERI = {("SC1","S")}`** — 1220042300 구룡터널_NB 1336 veh/h 주입점.
   나머지 내부 주입점 14곳은 경계면으로 올리지 **않고** 상수 부하로만 기록한다 (사용자 지시).

### config 의 `urban_movements` 474개를 회전 목록으로 쓰지 마라

leg 교차곱 선언이라 물리 회전보다 많다. SC1 은 4갈래 교차로인데 56개가 선언돼 있고 실제는 17개다.
통제 17 SC 합계로 선언 364 대 회전 201. 회전이 필요하면 위 생성기 산출을 써라.

## 런 관련 함정

- Vissim COM 은 **PowerShell 로만** 띄운다. 한글 경로 때문에 Git Bash 에서 깨진다.
- 러너가 모든 SG 에 `ContrByCOM=True` 를 걸어 inpx 신호 프로그램을 통째로 우회한다
  (`evaluation/controllers/plant_cycle.py`). `.sig` 의 주기·녹색은 제어 런에서 재생되지 않는다.
- 장기 런은 5분 무진행이면 kill 하고 재실행한다.
- 커넥터를 지우면 정적 경로가 미완성이 되어 시뮬이 시작조차 안 된다. 망 편집 뒤에는
  `.err` 의 Error 델타부터 봐라.

## SC1004 서측 — 분기 전 줄기는 아무도 소유하지 않는다

`link 69` 는 신호두 없는 서측 진입점(1,400 veh/h)이고 세 갈래로 갈린다.

```
69 ─10644→ 26   966 (69%)  램프미터 RM_C10644, freeway 로 빠짐
   ─10636→ 75   193        지하차도 → SC1005
   ─10637→ 70   193 ┐
   ─10640→ 71    48 ┘      SC1004 신호 접근부
```

한 player 에 통째로 주면 그 게이트 도착량이 3배 넘게 부풀려진다. 그래서 **69 는 무소유**로 두고
분기 이후부터 소유한다 (2026-08-19 사용자 지시, `decision_log/sc1004-west-split-20260819`).

```
SC1004·W      71 · 10640 · 10634 · 10635 · 10642                   신호 정지선(sg 2·5)과 그 진출
SC1004·W_RAMP 70 · 10637 · 10641 · 10700 · 10638 · 10643            램프 접속부 · off-ramp 도착 · 70→71 합류
SC1005·W      75 · 10701 · 10636                                    지하차도 분기
freeway       10644 · 10639                                         램프미터 걸린 on-ramp
```

결과: 보호망 횡단이 정지선 71 에서 잡힌다 — `10634`·`10635` 유입, 둘 다 신호 제어된다.
게이트맵에서 `no 1101`(link 69)은 게이트를 주지 않고 `shared_stem_unmapped` 로 둔다.
회계는 닫히고(게이트합+미배정+내부발생 == 도시부 총량) `urban_unmapped_volume_vph` 로 보인다.

## 유입 게이트맵 — 반드시 legs4b 를 넘겨라

```bash
python scripts/build_urban_input_gate_map_legs4b.py
```

VBS 가 vehicleInput 을 게이트에 조인해 `state.demand.urban_volume_vph_by_gate` 를 만들고,
어댑터(`vissim_stackelberg_adapter.py:3120`)가 그 이름이 config 의 `boundary_in_links` /
`boundary_out_links` 에 없으면 **`ValueError` 로 런을 세운다.** 조용한 오염이 아니라 하드 크래시다.

옛 대장 셋은 전부 legs4b 가 모르는 이름을 낸다 — `_20260811`(VBS 기본값)과 `legfix` 는
`in_SC9001_S` 1개, `pedovr` 는 `in_SC1004_SE` · `in_SC1004_SW` · `in_SC13_S` · `in_SC9001_S` 4개.
원인은 8방위 잔재와 mid-block 으로 강등한 노드(SC13 · SC9001)를 아직 가리키는 것뿐이다.

legs4b 대장은 pedovr 를 바탕으로 그 4개만 옮겼다. 규칙은 **게이트 = 진입 링크를 소유한
경계면 leg**(권역 정본 기준), 통제 SC 의 경계면 leg 를 먼저 쓰고, 못 가리면
`boundary_extra_legs_legs4b` 의 분담이 큰 쪽.

```
no  114  in_SC9001_S  -> in_SC1_W      link 364          우리은행포이_NB
no  194  in_SC13_S    -> in_SC12_E     link 1220013100   개포주민센터_NB
no 1100  in_SC1004_SE -> in_SC1004_S   link 66
no 1101  in_SC1004_SW -> (미배정)      link 69   공용 줄기
```

검증: 두 후보 망 모두 mapped 21 = `expected_mapped`, 미등재 0, config 가 모르는 게이트 0.

**분담이 갈리는 진입 링크 2개는 근사다** (사용자 승인). 대장 형식이 유입당 게이트 하나라
나눌 수 없어 큰 쪽에 몰아줬다 — `364`(SC1·W 111 vs SC105·E 85),
`1220013100`(SC12·E vs SC106·W, 여기는 분담이 아니라 통제 SC 를 택했다).
`69` 는 근사하지 않고 미배정으로 뒀다 (위 SC1004 서측 절 참조).

## link_to_origins 는 권역 정본에서 만든다 (2026-08-19 전면교체)

```bash
python scripts/build_link_to_origins_territory.py
```

옛 표는 링크 279개뿐이고 config origin 이름 123개 중 56개만 알았다. 그대로 movement map 을
재유도하면 `SC1001_to_SC1003` 의 **실측 근거**(링크 39 가 SG 4·7 을 단다)를 잃고 SG4 가
이름 규칙으로 엉뚱한 현시에 붙어, SC1003 의 p2 에 금지쌍 (3,4)·(4,7) 이 함께 들어간다.

**전수 수집으로는 안 풀린다** — "링크 39가 `SC1001_to_SC1003` 에 속한다" 는 소유 관계 선언이지
차량을 세어 나오는 사실이 아니다. 그 선언은 권역 정본에 있다.

```
링크                     279 → 1,011
config origin 이름 인식    80 → 119
관측이 닿는 origin 중 모델이 모르는 것   44 → 0
movement 해석            149 → 254   미해결은 전부 synthetic_boundary_leg
origin_link_head           0 → 228
전 SC 같은 현시 금지쌍     2 → 0
```

관측 링크 170개의 origin 집합이 바뀌었으므로 어댑터의 저류/대기 분할이 달라진다.
**2026-08-19 이전 런과의 비트 재현 비교는 여기서 끊긴다.**

## 예측 보정은 2026-08-20 에 재적합했다 (감사 전용, 제어에 안 먹음)

옛 파일 `real_world_prediction_calibration_pshb4500fix_20260724.json` 은 core17legs4b 이전
세대에서 맞춘 값이라 도시부 양에 0.14~0.24 배를 곱한다. 그 결과 `protected_accumulation` 이
실측 대비 **-79%** 로 보고됐다. 원시 모델은 같은 구간에서 **+8~19%** 로 따라가고 있었다 —
보고된 오차의 대부분이 보정 자체였다.

```
평균 |상대오차| (지표 8개)      iv150(적재)   iv60(경부하)
원시 모델                          25.8%        14.8%
옛 보정 pshb4500fix                61.3%        62.2%
새 보정 core17legs4b               10.2%        11.5%
```

**적용 범위**: `prediction` / `prediction_error` 페이로드에만 들어간다. MPC 롤아웃은 원시
`state` 를 쓰고, `post_guard`·`component_penalty` 경로는 비활성이라 제어 결과가 바뀌지 않는다.

### 배율을 안 씌운 것들 — 되돌리지 마라

- `protected_accumulation_veh` · `freeway_total_veh` — 원시 편의가 10% 안이고 부하영역마다
  방향이 갈린다. 배율을 씌우면 표본외에서 12.3% → 17.5% 로 **나빠진다**. 전면 적합안이
  표본외 15.5% 로 원시(14.8%)보다 진 이유가 이것이다.
- `off_ramp_storage_veh` · `boundary_queue_total_veh` — VISSIM 관측이 **39/39 표본 전부 0**
  인데 모델은 비영을 낸다. 관측 채널 결측이다. 0 에 맞추면 계측 결함을 적합하는 것이다.
- `ramp_queue_total_veh` — 반대 방향 결측. 관측은 38/39 비영(최대 56)인데 **모델이 전부 0**.

### 아직 남은 것

- 적합 궤적이 시드 13 하나다. iv150 의 10.2% 는 표본내라 **논문에 예측정확도로 인용하면
  순환이다.** 인용 가능한 값은 표본외 11.5% 이거나 보류 시드로 다시 잰 값이다.
- `urban_movement_queue` 는 비율이 1.05 → 2.41 로 표류한다(모델 큐 성장률이 느리다).
  배율 1.5 는 40.2% → 22.6% 로 줄이는 절충일 뿐 편의를 없애지 못한다. 근원은 동역학이다.
- `scripts/build_preflight_manifest.py:80` 등 다른 스크립트 기본값은 아직 옛 보정이다
  (pedovrx 세대 전체를 가리키는 별도 백로그).

## 리더 탐색 박스는 2026-08-20 에 재산정했다 — 물리는 축은 N_UF 였다

`N_P_star` 는 **horizon 순유입[veh]** 이고 `N_UF_star` 는 **램프 미터링 합[veh/h]** 이다.
누적 수준이 아니다. 둘 다 `evaluation/controllers/vissim_stackelberg_adapter.py` 에
하드코딩돼 있었고 둘 다 물리 도달범위보다 좁았다.

```
축      옛 값        새 값             근거
N_P    [0, 780]     [-250, 2400]     movement 도달가능 실측 [-216.3, 2135.9] (18결정)
N_UF   [0, 5000]    [0, 7200]        ramp_capacity_veh_h = 1800 x 4 = 물리 용량
```

### N_UF 가 진범이다

폴백(무제어)은 `ControlAction.uncontrolled` 가 램프를 용량 그대로 열어 **7,200** 을 실현한다.
리더는 `_leader_metering_projection` 이 합을 `N_UF_star` 에 맞추는데, `_candidate_bounds` 가
자유류에서 `feasible_nuf = max(feasible_nuf, total_ramp_capacity)` = 7,200 을 계산해도
`nuf_upper = min(5000, 7200) = 5000` 으로 잘렸다. 전 결정에서 `leader_nuf_bound_upper = 5000`,
`leader_nuf_heuristic_target` 마저 5000 으로 클립됐다.

**리더는 매 결정 램프 유입을 30.6% 강제 차단당했다.** 완료차량이 폴백 대비 14~17% 적었던
직접 원인이고, 가드가 `ttt_worse` + `completed_severe` 로 **7/7 기각**한 이유다.

### N_P 축만 넓힌 대조군이 이걸 증명한다 (npbox, 2026-08-20)

```
                    옛 박스[0,780]   새 박스[-250,2400]
리더 의도 N_P*            780.00          1078.69
사영 순유입              1097.93          1106.45
리더 완료차량            1520.61          1520.61   <- 소수점까지 동일
가드 판정                   기각             기각
```

의도는 움직였는데 결과가 안 움직였다. `allocation_module_active = 0` 이고 그리드 프리체크가
후보 310개 중 **0개**를 거른다 — 이 구성에서 `N_P_star` 는 제어를 거의 안 바꾼다.

### 앵커 붕괴 (N_P 쪽 부수 효과)

`_np_anchor_values` 는 movement 양끝과 **직전 `N_P_star`**(≈1,576)를 앵커로 쓰는데 셋 다
[0,780] 으로 클립돼 앵커 집합이 `{0, 780}` 으로 무너졌다. linspace 는
`n_np = round(sqrt(9)) = 3` 개뿐이라 사실상 후보 전체가 두 점이었다.

### 상류 설계 의도

`vendor/NumSim-mine/src/tests/test_constraints.py:1799` 가 파생 경계는 base 범위 **안에**
들어간다고 검사한다(상류 기본 `[-3500, 3500]`). 우리 `[0, 780]` 이 그 관계를 뒤집고 있었다.

## far(MFD tail) terminal cost 는 배선이 끊겨 있었다 (2026-08-20 연결, 기본 꺼짐)

`mfd_far_cost_to_go` 는 구현돼 있고 `cfg.mpc.leader_mfd_far_enabled` 도 **상류 기본이 True** 다
(state.py:492, "2026-07-09 기본 ON"). 그런데 분산 경로
`distributed_coordinator._evaluate_grid_candidate` 가 `ObjectiveSpec` 을 기본값
(`score_mode="raw"`, `far_enabled=False`)으로 만들어 far 를 **계산조차 하지 않았다.**
실런 진단에 `far` 키가 0건이다. 가격 팔(`stackelberg_wu_metered.py:2606`)만 쓰고 있었다.

그리고 코디네이터는 `point.objective` 를 아예 안 본다 — `point.partial_ttt` 로 자기 objective 를
다시 만든다. 그래서 `far_enabled=True` 만 켜도 far 는 계산되고 **버려진다.**

```
tuning 절 rollout_far.enabled = true  ->  cfg.mpc.distributed_rollout_far_enabled
  far 가 (1) 후보 랭킹 objective (2) guard 가 읽는 distributed_response_rollout_ttt 양쪽에 실림
  폴백 PFO 도 leader=None 으로 같은 _evaluate_grid_candidate 를 타므로 대칭이다
기본 False = 비트동일 (PricePointResult.far 기본 0.0, score_mode!="raw" 안에서만 대입)
A/B arm: evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_far_20260820.json
```

**미조치**: 이 vendor 변경은 앵커 재등재가 필요하다(아래 승인 사슬 절 참조).

## 액추에이션은 맞고 모델이 틀렸다 (2026-08-20 판정)

```bash
python scripts/audit_actuation_and_flow_fidelity.py evaluation/runs/<이름>
```

리더가 기각당하는 원인을 셋으로 가르는 도구다. shape_off · boxfix 두 런 판정:

```
녹색  PASS   되읽기 96,896행 · 불일치 0 · SG창 768 중 허용초과 0 (최대 편차 4.0s)
유량  FAIL   차량회계 닫힘 · 모델/VISSIM 완료차량 평균비 0.744

  결정      모델(450s)   VISSIM(450s)   비율
   900       1,769.2        2,206      0.802
  1050       1,885.8        2,449      0.770
  1200       1,916.3        2,633      0.728
  1350       1,914.2        2,832      0.676
```

**모델은 ~1,900 에서 포화한다고 보는데 VISSIM 은 2,832 까지 계속 늘어난다.** 격차가 벌어진다.
프록시 구성은 본선 진출 1,681.6 + 도시 경계유출 87.6 이라, 부족분은 도시부 방류에 몰려 있다.

### 되돌리면 안 되는 측정 규칙 셋

1. **`signal_sg` 행의 `green_sec` 은 녹색 길이가 아니다** — 플랜 주기[s]다(러너 VBS:1008).
   실제 창은 `p1_green`(시작)·`p2_green`(끝)이고 `dsd_no`=SG 번호, `link`=창 인덱스다.
   컬럼 재사용이라 헤더만 보면 반드시 오독한다.
2. **비교 대상은 SG 자기 계획창이지 현시 녹색이 아니다.** SC5·SC7·SC109 는 SG 가 현시의
   일부만 녹색인 설계다(SC5 SG2: 34.5s 현시 안에 계획 16.1s). 현시 녹색과 맞대면 40%
   밖에 안 나오는 것처럼 보인다.
3. **마지막 결정의 창은 채점에서 뺀다.** 시뮬 종료 뒤로 뻗어 되읽기가 없어 실현 0 으로
   잡힌다. 첫 판에서 128건이 그렇게 위반으로 나왔다.

### 유량 실측은 `veh_no` 대조로 뽑는다

`local_observation` 은 저량만 수집한다(링크 위 차량 수·속도·정지수·큐꼬리) — **유량이 없다.**
대신 `state_<t>.json` 의 `vehicle_records.records` 가 전 차량 스냅샷이라, `veh_no` 를 인접
결정 간에 대조하면 사라진 차량 = 완료, 새로 나타난 차량 = 진입이다. 회계가
`재고(t+1) = 재고(t) + 진입 - 완료` 로 정확히 닫힌다(전 구간 검증).

## 가드가 통과시키기 전에는 리더 수정이 plant 에 닿지 않는다

shape_off 와 boxfix 의 VISSIM 궤적이 **12개 구간 전부 비트 동일**하다 — 재고·완료·진입이
한 자리도 안 다르다. 가드가 두 런 모두 리더를 7/7 기각해 커밋된 제어가 폴백으로 같았기 때문이다.

**리더 쪽 파라미터를 아무리 고쳐도 가드가 막으면 아무것도 측정되지 않는다.** 박스 재산정
(N_P `[0,780]`->`[-250,2400]`, N_UF `[0,5000]`->`[0,7200]`)이 그렇게 통째로 무효화됐다.

리더를 강제로 커밋시키려면 `stackelberg_enable_fallback: false` 하나면 된다 —
`_pfo_incumbent_fallback_enabled()` 가 하드코딩 `False` 라 조건이 이 플래그 하나로 줄어든다.
A/B arm 셋을 만들어 뒀다(`..._lead_` · `..._leaddirect_` · `..._leadpso_20260820.json`).

## 작업 전에 이걸 먼저 돌려라 — 추론하지 마라

```bash
python scripts/resolve_live_controller.py --tuning <config> --controller stackelberg
```

2026-08-20 하루에 구성을 **여섯 번** 오독했다. 전부 코드를 읽고 추론해서 생긴 일이다.

```
green_sec 을 녹색 길이로 읽음       실제로는 플랜 주기 (CSV 컬럼 재사용, 러너 VBS:1008)
현시 녹색과 SG 계획창을 맞댐         SC5·SC7·SC109 는 SG 가 현시 일부만 녹색인 설계
flagship=True 로 오프라인 검증       실런은 -Controller stackelberg -> flagship=False
                                     이 한 글자가 leader_value_depth 를 0/3 으로 가른다
N_P 를 누적량으로 읽음               horizon 순유입[veh] 이다 (N_P_crit 만 누적 임계)
450초 예측과 900초 실측을 맞댐       창이 달랐다
가격이 어느 컨트롤러에 있는지        분산 팔엔 없고 flagship 팔에만 있다
```

해석기가 찍는 것: 리더/팔로워 클래스 · player 수와 id · 레버 수 · budget 범위 ·
가격 채널 8개 + λ_P/λ_UF · 게이트 10개 · 리더 목적함수 가중치 ·
그리고 **이 팔이 import 로 닿지 않는 controllers/ 파일과 그 바깥 참조**.

`--controller` 는 러너의 `-Controller` 와 **같은 값**을 넘겨라. 이 인자가 flagship 분기를 정한다.

### 컨트롤러를 지우지 마라

controllers/ 27개 중 정말로 아무도 안 쓰는 것은 `gradseed_mpc.py`(77줄) 하나뿐이다.
나머지는 experiments·tests·어댑터가 물고 있다. 그리고 **vendor 파일을 지우면 앵커의
`anchor_python_file_set`(121개 핀)이 깨지고, 삭제는 `local_patches` 스키마로 표현할 수도
없다**(`patched_blob` 이 40-hex OID 를 요구한다). 헷갈림은 위 해석기로 막는다.

## freeway agent 입도 — 16(세그먼트) / 2(링크)

```
tuning 절   "agent_topology": { "freeway_granularity": "link" }      기본 "segment" = 비트동일
```

**plant 모델을 바꾸지 않는다.** `freeway_segments_per_link=8` · `ramps=4` 가 그대로라
METANET 롤아웃은 여전히 **2링크 x 8세그먼트 = 16셀 + 램프 4개**를 굴린다. 바뀌는 건
agent 분할뿐이다.

```
segment  agent 16개. 각자 자기 1셀만 본다.
         VSL 은 링크당 1개뿐인데 8 agent 가 공유 -> 합의 안 됨(vsl_selected 100.0/120.0 로 갈림).
         병합은 out.vsl[link] 한 줄이라 사실상 마지막 승자.
         agent 별 projected_freeway_tts 합 67.77 대 결합 롤아웃 87.40 — 22% 적게 본다.

link     agent 2개(F_W · F_E). 각자 VSL 1 + 램프 2 = 액션 3개를 정확히 소유.
         segment_index=-1 이라 해석부가 자기 링크 8셀을 전부 본다.
         F_W=(R_D_W,R_F_W)+(OR_D_W,OR_F_W) · F_E=(R_D_E,R_F_E)+(OR_D_E,OR_F_E), 4/4 누락 없음.
```

`segment_index<0` 은 상류가 이미 상정한 값이다 — `AgentSpec.segment_index` 기본이 -1,
`_freeway_agent_id(link, None)` 이 `F_E`/`F_W` 를 내고, 소비처 전부가 음수를 명시 처리한다
(2510행 `indices=range(전체)` · 2641행 `rhos=all_rhos` · 572행 이웃압력 0).

**단 한 자리만 보정이 필요했다.** 링크 agent 는 램프를 둘 소유하므로 merge 세그먼트를
`len//2`(중앙)로 떨어뜨리면 `ramp_merge_segment_index`({R_D_W:2, R_F_W:4, R_F_E:3, R_D_E:5})를
통째로 잃는다. `_agent_merge_index` 헬퍼가 램프별 설정값을 쓴다.

## freeway <-> urban 결합은 양방향이지만 얇다

```
urban -> freeway   coupling["u_on_{ramp}"]        도시 agent 가 정한 램프 유입률
freeway -> urban   freeway_response               agent_U_*_freeway_pressure_used = 1.0
ablation 스위치     u_to_f · f_to_u · u_to_u · f_to_f   (기본 전부 활성)
```

freeway agent 가 계상하는 도시 비용은 **자기가 램프 저수지를 넘치게 해서 유발한 역류뿐**이다.

```python
blocked_to_urban = max(0, ramp_start + incoming - release - capacity)
urban_tts        = 0.5 * blocked_to_urban * horizon_h
# 주석: "Existing urban on-ramp approach queues are already charged by the urban model."
```

즉 저수지가 **차기 전까지는 미터링의 도시 비용이 0** 으로 보인다 — 문턱 비선형이다.
λ_UF 주석의 "metering 이 절벽 레버" 와 같은 현상이다.

**`AgentSpec.neighbors` 는 죽은 필드다.** 최인접 교차로를 선언해 두지만 해석부가 안 읽고
`tests/test_constraints.py:696` 만 읽는다. 램프-교차로 결합을 제대로 걸려면 여기가 그 자리다.

## 팔이 셋이다 — 헷갈리지 마라 (2026-08-20)

```bash
python scripts/resolve_live_controller.py --controller <이름>
```

| `--controller` | 리더 | 팔로워 | player | 가격 | GNE |
| --- | --- | --- | --- | --- | --- |
| `stackelberg` | StackelbergMPC | DistributedCoordinator | 17 + 16(세그먼트) | **없음** | 블록 Jacobi + 블록간 Gauss-Seidel |
| `pstack-flagship` | StackelbergWuMetered | WuFaithfulFollower | 17 + 16(`segment_agents=True`) | 4채널 + λ_P | 순수 Jacobi |
| `wu-link` | 〃 | LinkAgentWuFollower | 17 + **2**(링크) | 〃 | 〃 |

`wu-link` 가 2026-08-20 에 만든 것이다. **`pstack-flagship` 과 딱 한 줄 다르다** —
`segment_agents = False`. Wu 의 GNE·오라클 7개·λ_P/λ_UF·가격 소비 경로를 한 줄도 안 건드린다.

왜 링크 단위인가. VSL 은 **링크당 1개**인데 세그먼트 agent 8개가 그 하나를 공유하고
합의가 안 된다(실측 `vsl_selected` 가 100.0/120.0 로 갈리고 병합은 `out.vsl[link]` 한 줄이라
사실상 마지막 승자). 링크 단위면 agent 가 VSL 1 + 램프 2 = **액션 3개를 정확히 소유**한다.

**plant 모델은 어느 팔에서도 안 바뀐다.** `freeway_segments_per_link = 8` · `ramps = 4` 라
METANET 롤아웃은 항상 2링크 x 8세그먼트 = 16셀 + 램프 4개를 굴린다. agent 분할만 바뀐다.

### 초판(커밋 `fe52cfd`)은 요청과 달랐다 — 기록해 둔다

`priced_distributed_coordinator.py`(333줄)는 `DistributedCoordinator` 를 베이스로 가격
오라클 3개·λ_P·neighbor 결합항을 **직접 구현**했다. 요청은 "wu 구조를 홀드하고 player 만"
이었는데 초판은 리더의 가격 기구만 보존하고 **팔로워의 GNE 를 분산 것으로 바꿔놨다.**

```
순수 Jacobi (wu)            대   블록 Jacobi + 블록간 Gauss-Seidel (분산)
결합변수 4키                대   48키 (세그먼트별 밀도·속도·유량 x8)
국소 최선응답 + 국소 롤아웃  대   structured grid + 전 망 450초 롤아웃
```

그리고 직접 구현한 것이 전부 불필요하거나 열등했다.

- 가격 오라클 3개 — wu 에 **7개**가 이미 있다
- λ_P 듀얼 — wu 의 `_lambda_np_update` + `use_dual_np`(기본 True)가 이미 한다
- neighbor 결합항 — 문턱은 **물리적으로 옳다**(저수지에 공간이 있는 동안 차량은 램프에
  대기하고 그건 `link_ramp_queue` 로 이미 계상된다). wu 는 그 회계를 substep FIFO 로
  돌려 더 정교하고(`count_blocked_ramp_inflow`), 근시 병리는
  `follower_terminal_cost_enabled`(Q²/2R 삼각 배수)가 더 잘 다룬다

2026-08-20 에 wu 베이스로 전면 재작성하고 파일명을 `priced_wu_link_controller.py` 로
바로잡았다. **초판 코드는 남아 있지 않다 — git 이력에만 있다.**

### 앵커에 `local_additions` 를 신설했다

`local_patches` 는 상류 파일의 **수정**이라 `upstream_blob` 을 요구한다. 상류에 없는
**신규 파일**은 그 지문이 존재하지 않아 표현할 수 없었다. `python_blobs` 에 끼워 넣으면
앵커가 "상류 커밋에 이 파일이 있다" 는 거짓을 주장하게 되므로 별도 절을 둔다.
등재된 `(path, blob)` 조합만 파일집합 비교에서 예외로 인정하고, 지문이 다르거나 파일이
사라지면 그대로 실패다. `python_file_count` 121 은 **상류 기준**이라 안 바뀐다.

## 승인 사슬 — 앵커 등재 하나 남았다

```bash
python scripts/verify_runtime_source.py --repo . --out <경로>/runtime_source.json
```

2026-08-19 에 `distributed_coordinator.py` 를 커밋했다(`e407adf`). `tracked_source_clean` 은
통과했으나 **`anchor_python_blobs` 가 남는다** — 앵커 `vendor/NumSim-mine/UPSTREAM_TREE.json` 은
**상류 커밋의** blob 해시를 적으므로 로컬 커밋으로는 안 맞는다.

설계된 경로는 앵커의 `local_patches` 등재다(이미 `stackelberg_mpc.py` 한 건이 그렇게 있다).
blob OID 를 조용히 갱신하면 앵커가 "commit 에 이 내용이 있다" 는 거짓을 주장하게 되므로 그렇게 하지 않는다.

```
path           src/controllers/distributed_coordinator.py
upstream_blob  e5d7824ef90694b807746dee68a2e3cf7a8a12a0
patched_blob   d29b1b02c98787a19339731615af9019469cef58
```

**두 열쇠를 같이 돌려야 한다** — 앵커에 항목을 넣고, `scripts/verify_runtime_source.py:24` 의
`EXPECTED_ANCHOR_SEMANTIC_SHA256` 을 새 앵커 해시로 갱신한다. `vendor/` 쓰기가 필요하다.

## 런타임 몽키패치는 프로세스 경계를 못 넘는다 (2026-08-20 실측)

어댑터는 vendor 를 안 고치려고 **런타임에 모듈을 몽키패치**한다. 그중 하나가
`install_monitor_fixed_signal_runtime_patch` 의 `_phase_green_fraction` 이고, 모듈 5개
(`urban_queue_model`·`distributed_coordinator`·`local_signal_plant`·`wu_distributed`·
`wu_faithful_follower`)에 실제 VISSIG 스케줄로 만든 클로저를 심는다. 모델의
**green -> 유량** 변환을 진짜 신호 프로그램에 맞추는 패치다.

Windows 의 `ProcessPoolExecutor` 는 **spawn** 이다. 워커는 새 인터프리터라 모듈을 새로
import 하고, 부모가 런타임에 심은 것은 하나도 안 따라온다. 그래서 **가격 롤아웃을
병렬화하면 워커가 조용히 다른 plant 로 가격을 매긴다.** 실패가 아니라 틀린 값이라 더 나쁘다.

무엇이 넘어가고 무엇이 안 넘어가는가:

| 패치 | 대상 | spawn |
|---|---|---|
| `install_monitor_fixed_signal_runtime_patch` | 모듈 5개의 `_phase_green_fraction` | **유실** |
| `install_vsl_metanet_rollout_runtime_patch` | `DistributedCoordinator` 클래스 속성 | 유실(단 wu 팔은 그 클래스를 안 쓴다) |
| `install_vissim_calibration_runtime_patches` | `cfg.network` 속성 | 살아남음(컨트롤러와 함께 피클) |

`phasepar_20260820` 이 이걸 맞았다. `phaseprice3`(직렬)과 t=600 입력이 비트 동일한데
결과가 갈렸다 — 가격 15개 중 14개 불일치(SC5 27%, SC6 부호 반전), 커밋된 녹색이
SC1002·SC12·SC5 에서 8초씩 반대. `ramp_metering`·`vsl`·`offsets` 는 비트 동일했고,
이게 "green 전용 패치" 예측과 정확히 맞는다. **그 런의 가격·TTT 는 무효다.**

판별 방법(재현 비용 4분): 같은 결정을 워커 수만 바꿔 재실행한다.
`w4 == w10` 인데 `w1` 만 다르면 청킹·해시시드·부동소수 순서가 아니라 **프로세스 경계**다.

지금은 `PricedWuLinkStackelbergController.__setstate__` 가 언피클 직후 패치를 되살린다
(어댑터가 `install_price_worker_bootstrap` 으로 최소 페이로드를 실어 보낸다 — 설치 함수는
`state_json` 에서 network_path 하나만 읽으므로 상태 전체를 싣지 않는다). 되살리기 실패나
부트스트랩 부재는 **raise** 한다 — 직렬 재실행 + `price_parallel_serial_rerun_count` 로
떨어지지 조용히 넘어가지 않는다.

### 리더 후보 병렬은 켜지 마라 — 느린 게 아니라 틀린다

`leader_candidate_parallel_backend` 를 `process` 로 두면 워커가
`_stackelberg_candidate_worker` 에서 `StackelbergMPCController(payload["cfg"])` 를 **새로
만든다**. 우리 컨트롤러도, wu 팔로워도, 가격도 아닌 기반 클래스다. 몽키패치까지 없다.
상류가 `serial` 로 둔 이유가 이것이고, flagship 이 그대로 물려받은 것도 맞는 판단이다.
그래서 "가격 병렬화 후 남은 1.5배 병목" 은 설정 한 줄로 풀 자리가 아니다.

스레드 백엔드(`grid_parallel.py` 의 `ThreadPoolExecutor`)는 같은 프로세스라 이 함정이
없다. 다만 롤아웃이 순수 파이썬이면 GIL 때문에 가속이 안 붙는다 — 쓰려면 먼저 재야 한다.

## 롤백 위험 지점 (2026-08-19 감사, 미조치)

고치려면 근원을 봐야 한다. 단순 경로 치환은 대부분 더 나쁘다.

| # | 자리 | 문제 |
|---|---|---|
| ~~R2~~ (해결) | `…core17legs4b.ps1:34` `$UrbanInputGateMap = ""` | **2026-08-19 게이트맵은 만들었다** (`urban_input_gate_map_legs4b_20260819.csv`). 다만 러너 기본값이 아직 비어 있어 VBS `:4659` 의 옛 맵이 열린다. **2026-08-19 러너 기본값에 박았다.** 이제 안 넘겨도 legs4b 대장이 열린다 |
| ~~R3~~ (해결) | `…core17legs4b.ps1:195-198` | 2026-08-19 provenance 를 core17legs4b 세대로 옮겼다 — 권역 정본 · legs4b 인접표 · legs4b 저류 · 경계 회전 |
| R6 | `scripts/derive_urban_storage_capacity.py:35-36` (대체 생성기 있음 → `derive_urban_storage_core17legs4b.py`) | 기본 인접표가 `intersection_adjacency8_20260804`(저장소 최고령). 인자 없이 돌리면 8월 4일 근거로 재유도한다. **경로만 바꾸면 안 된다** — 링크배정 아티팩트가 옛 8방위라 `SC1004_SE_out` 같은 이름이 나온다 |
| R7 | `scripts/derive_urban_input_gate_map.py:35`, `derive_urban_exit_gate_map.py:45-48` | 기본값이 core15n41 / n4dr150 세대 |
| R8 | `scripts/run_readiness.py:99` | 사람에게 `…core15n41.ps1` 을 추천한다. `…core17legs4b.ps1` 로 바꿔야 한다 |
| R9 | `scripts/run_plant_fidelity_matrix.ps1:43` | `core15n41` 워치독을 박아두고 Network/Tuning 을 CLI 로 덮을 수 없다 |
| R11 | `outputs/README.md:11-19` | 20260805 세대를 "살아 있는 아티팩트", 현행 슬러그를 `core15n41` 로 선언한다 |

## 손대지 않는 것

- `git add -A` 금지 — 파일을 명시해서 스테이징한다.
- `vendor/` 직접 편집 금지.
- 원본 덮어쓰기 금지: 원 `.sig`, 원 inpx, 생산 config, `reports/`.
- push 는 별도 승인이 있어야 한다.
- `_archive/` 와 `outputs/_superseded_20260819/` 는 격리 보관이다. 거기서 파일을 꺼내 쓰지 마라.
  `_archive/README.md` 에 왜 옮겼는지, `_archive/manifest.csv` 에 원래 경로가 있다.
- pedovrx / pedfold / jam168 / userfix_20260814e 세대는 **살아 있다**. 승인 사슬의
  `is_production` 판정과 어댑터 `execution_fingerprint_sha256` 이 이 경로들을 문자열로 물고 있다.
  옮기면 승인이 조용히 약한 경로로 떨어지고 비트 재현 기준선이 깨진다.
