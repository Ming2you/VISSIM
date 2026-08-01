# VISSIM 실측 ↔ NumSim METANET ↔ strict plant freeway 커널 3자 비교 하네스 준비도 보고

작성일 2026-08-01 · 대상 `C:/Users/alsrj/Desktop/학술/찐찐막/Claude/VISSIM/plant`
· 코드 미수정(읽기·실행만) · 플랜트 테스트 75/75 PASS 재확인

---

## 0. 요약 — 결론 6줄

| # | 결론 | 근거 |
|---|---|---|
| 1 | **strict plant freeway 커널은 NumSim METANET과 기계정밀도(≤1.4e-14)로 일치시킬 수 있다.** `w_mps = L/dt`, `q_max` 비바인딩, 종단 off-ramp sink 3가지만 맞추면 자유류·전이·혼잡 전 영역에서 ρ와 v가 모두 일치한다 | §2-4, 탐침 `exactness_probe.py` |
| 2 | **공통 좌표계의 최대 결함은 FW_E 세그먼트 정의 3중 불일치다.** 실측은 link2+connector10702+link24(8038.582 m)를 8등분, control_mapping은 link2만(4691.599 m)을 8등분, NumSim cfg는 스칼라 0.795059 km. 같은 `segment_index 3`이 세 곳에서 **서로 다른 도로 구간**을 가리킨다 | §1-1 |
| 3 | **VSL 비구속 문제는 플랜트에 없다. 반대 문제가 있다.** 플랜트는 VSL을 FD 지수식의 prefactor로 곱해 **모든 밀도에서 항상 구속**한다(ρ_bind = ∞). NumSim은 FD 출력에 min-cap이라 ρ>25.84에서 비구속 | §4 |
| 4 | **δ_merge는 3자 비교로 적합 불가능하다.** 플랜트 속도식에 merge 항 자체가 없다(hybrid.py:607-616은 3항뿐). τ/ν/κ/a/v_free/ρ_crit은 적합 가능 | §5 |
| 5 | **§11 게이트는 실측 대조를 이미 포함한다(G5, G6).** 따라서 이 작업은 "플랜트를 기준기로 쓰는 것"이 아니라 **"플랜트를 G5 피검체로 세우는 것"** 이어야 한다. 순서를 뒤집으면 순환논증이 된다 | §6-1 |
| 6 | **붙일 것의 대부분은 플랜트 밖(별도 하네스)이다.** 플랜트 안에 넣어야 하는 것은 계약이 이미 요구하는데 미구현인 2개(freeway 세그먼트 분류, freeway 관측 투영)뿐이다 | §3 |

---

## 0-1. 보고서 간 모순 판정

4개 선행 보고서 사이에 어긋난 항목을 코드로 직접 판정했다.

| 쟁점 | A/B/C/D 주장 | 판정 | 근거 |
|---|---|---|---|
| VSL 진입 형태 | 사용자 전제·A "NumSim과 동일 구조" / C·D "구조가 다르다" | **C·D가 맞다.** 플랜트는 prefactor, NumSim은 output cap | `hybrid.py:431-435` vs `NumSim-mine/src/models/metanet.py:93-96` |
| NumSim ρ_max | C "95.01964207118104" | **틀렸다(dataclass 기본값을 읽었다).** 실제 운용값은 `default.yaml`의 180.0 | `NumSim-mine/src/config/default.yaml:30`; dataclass 기본값 `state.py` 는 override됨 |
| NumSim 용량 6900이 차로당인가 | 명시 없음 | **링크 전체(4차로)다.** 차로당 1725 veh/h | `metanet.py:524` `terminal_cap = q_cap * lanes_now[i] / net.freeway_lanes` |
| receiving 구조 정합 가능성 | C "원리적으로 다른 답, 자유류로 제한해야" | **틀렸다.** `w = L/dt`로 두면 플랜트 w-항이 NumSim 저장용량 supply와 **항등적으로 같아진다**(CFL 등호에서 통과) | §2-4 실측 |
| 세그먼트 격자 | D "어댑터는 균등 8등분 FW_E 586.45 m" | **부분적으로만 맞다.** 제어 매핑은 586.45 m, 실측 수집은 1004.823 m로 서로 다르다 | §1-1 |
| bridge가 legacy state를 변환하는가 | A·B·D 모두 "projector/copy_back 미구현" | **맞다** | `bridge.py:495-558` |

---

## 1. 공통 좌표계 — 무엇을 정규화해야 하는가

### 1-1. 세그먼트 정의 — 최우선 블로커

사용자가 지적한 "실측 1.0048 km vs NumSim cfg 0.795059 km" 불일치의 정체를 확정했다. **불일치는 2중이 아니라 3중이고, 원인은 반올림이나 단위가 아니라 서로 다른 도로 구간을 덮고 있다는 것이다.**

| 소스 | FW_E 세그먼트 길이 | FW_E 총연장 | 덮는 실제 구간 | 근거 |
|---|---|---|---|---|
| **VISSIM 실측 FD** | 1.004823 km | 8038.580 m | `link:2` + `connector:10702` + `link:24` | `outputs/no_control_fd_mfd_20260724_freeway_fd_points.csv:2` |
| **제어 매핑(VSL·램프미터 앵커)** | 0.586450 km | 4691.599 m | `link:2` 만 | `evaluation/real_world_modi_control/control_mapping.json:70`, `freeway_model_links.FW_E.segment_bounds_m` |
| **NumSim cfg** | 0.795059 km (스칼라, FW_E·FW_W 공용) | 6360.47 m | 없음(FW_E·FW_W 16세그 산술평균) | `evaluation/configs/real_world_modi_pstack_adapter_v0_20260719.json` `config_overrides.network.freeway_segment_length_km`; 산출식은 `evaluation/controllers/vissim_stackelberg_adapter.py:998` |

실측 총연장의 정체를 컴파일된 토폴로지로 역산해 확정했다.

```
link:2            = 4691.599000000157 m
connector:10702   =    1.001500000010 m   (link 2 @4691.598 → link 24 @0.0005, 4차로)
link:24           = 3345.981430444359 m
                    ─────────────────────
합계              = 8038.581930444527 m ;  /8 = 1004.822741 m
CSV 실측값 8 × (1.004823/1.004822 교대) = 8038.580 m   →  차이 1.9 mm
```

즉 **실측 수집기의 FW_E는 본선 연속체(link 2 → link 24)를 따라간다.** 반면 `control_mapping.json`의 FW_E는 link:2에서 끊긴다. FW_W는 문제가 없다 — `link:26` 단독 8029.342 m를 8등분한 1003.668 m가 실측과 소수 6자리까지 일치한다(`canonical_topology_modi.json` link:26 = 8029.342157418707, /8 = 1003.6677697).

**귀결 — 이것이 왜 치명적인가.**

| 문제 | 내용 |
|---|---|
| 위치 불일치 | 실측 `RW_FW_E_S3`는 3014–4019 m 구간, 제어 `FW_E__seg3`는 1759–2346 m 구간이다. **겹치지 않는다.** VSL을 seg3에 걸고 seg3 속도를 관측하면 서로 다른 도로를 보는 것이다 |
| 밀도 스케일 | 밀도는 `count/(length_km·lanes)`(`vissim_stackelberg_adapter.py:1811`)로 나뉜다. 두 정의의 길이비가 1.7134배이므로, 어느 쪽이 옳든 나머지 하나의 밀도는 계통적으로 71% 틀린다 |
| 램프 merge 인덱스 | `ramp_merge_segment_index.R_F_E=3, R_D_E=7`(adapter v0 config)은 어느 격자 기준인지 문서화돼 있지 않다. 격자가 바뀌면 merge 위치가 통째로 이동한다 |
| NumSim 스칼라 | 0.795059는 두 방향 평균이라 **어느 방향에도 물리적으로 맞지 않는다.** `NetworkConfig.freeway_segment_length_km`가 스칼라 단일 필드라 방향별 길이를 담을 수 없는 구조적 한계다 |

**권고 — 정본을 하나로 고정한다.**

1. 실측 수집기 쪽 정의(link2+conn+link24, 1004.823 m)를 정본으로 채택한다. 이유는 본선 연속체를 끊지 않고, FW_W(1003.668 m)와 세그먼트 길이가 0.115% 이내로 맞아 방향 간 대칭성이 확보되기 때문이다.
2. `control_mapping.json`의 `FW_E.segment_bounds_m`을 재생성해 8개 경계를 새 격자로 옮기고, VSL DSD 배치와 `ramp_merge_segment_index`를 재산출한다.
3. NumSim은 세그먼트별 길이 프로파일을 받을 수 없으므로(스칼라 필드), 하네스가 **세그먼트별 길이를 명시 전달하는 플랜트 쪽**을 기준으로 삼고 NumSim에는 방향별로 별도 실행하거나 길이 오차를 잔차에서 분리 표기한다.
4. 재생성 전에는 **FW_W만으로 3자 비교를 수행한다.** FW_W는 세 소스가 이미 정합한다.

### 1-2. 단위 정규화표

| 물리량 | VISSIM 실측 CSV | NumSim | strict plant | 변환 |
|---|---|---|---|---|
| 속도 | `mean_speed_kph` km/h | km/h | m/s | ÷3.6 (`bridge.py:31` `KM_PER_HOUR_TO_M_PER_SEC`) |
| 밀도 | `density_veh_km_lane` veh/km/lane | veh/km/lane | 저장 안 함 — `count/(L_m·lanes)` = veh/m/lane | ÷1000 (`hybrid.py` `veh_per_km_lane_to_veh_per_m_lane`) |
| 유량 | `flow_vph` veh/h | veh/h | veh/s | ÷3600 (`bridge.py:30`) |
| 재고 | `count` veh | ρ·L_km·λ (파생) | `VehicleStock.vehicle_count_veh` veh (**1차 상태**) | 동일 |
| 용량 | — | `freeway_capacity_veh_h` = 6900 veh/h **링크 전체** | `q_max_vehps_per_lane` veh/s/**차로** | ÷(lanes·3600) → 0.479167 |
| 후진파 | — | **필드 없음** | `w_mps` m/s **필수** | §2-4 참조 |
| anticipation ν | — | `metanet_nu_km2_h` = 65.0 km²/h | `anticipation_m2ps` m²/s | ×1e6/3600 = 18055.5556 |
| κ | — | `metanet_kappa_veh_km_lane` = 40.0 | `kappa_veh_per_m_lane` (**기본값 0.001 = 1 veh/km/lane**) | ÷1000 → 0.040. **기본값이 40배 작다 — 명시 주입 필수** |
| τ | — | `metanet_tau_sec` = 18.0 | `tau_sec` | 동일 |
| a | — | `metanet_a_m` = 1.867 | `desired_speed_shape` (기본 1.867) | 동일 |
| ν 기본값 | — | 65.0 (항상 활성) | `anticipation_m2ps = 0.0` (**항 자체가 꺼짐**) | **명시 주입 필수** |

NumSim 파라미터 출처는 `NumSim-mine/src/models/state.py:270-276`, ρ_max는 `src/config/default.yaml:30`(180.0), 실세계 v_free/ρ_crit/용량은 `evaluation/configs/real_world_modi_pstack_adapter_v1_response_calibrated_20260721.json`의 `calibration_override.operational.network`(v_free_kph=120.0, rho_crit_veh_km_lane=30.0, freeway_capacity_veh_h=6900.0)다.

**함정 2개를 다시 강조한다.** 플랜트의 `kappa_veh_per_m_lane` 기본값 0.001과 `anticipation_m2ps` 기본값 0.0은 NumSim과 전혀 다른 모델이다(`hybrid.py:124-125`). 빌더가 이 둘을 명시 주입하지 않으면 조용히 다른 물리를 비교하게 된다.

### 1-3. 시간 격자

| 항목 | 값 | 근거 |
|---|---|---|
| NumSim `T_f` | 10 s | `NumSim-mine/src/config/default.yaml:3` |
| NumSim `T_u` | 5 s | `default.yaml:4` |
| NumSim `control_interval` | 180 s (실세계 config 체인 10단계 전부 `simulation` override 없음) | `default.yaml:5`, 체인 확인 완료 |
| VISSIM 실측 집계 주기 | **60 s** (900–4500 s, 61 스탬프 × 16 세그 = 976점) | `no_control_fd_mfd_20260724_freeway_fd_points.csv` sim_sec 분포 |
| plant freeway `dt` | `dt == freeway.dt_sec` **정확 일치 강제** | `hybrid.py:389-390` `unsupported_dt_sec` |
| plant `advance_interval` | `end_time − sim_time`이 `dt`의 정수배여야 함 | `hybrid.py:715-717` `end_time_off_grid` |
| plant CFL | `dt ≤ min(L/v_free, L/w, τ)` — 세그먼트 생성 시점에 강제 | `hybrid.py:230-233` |

**정합 판정.**

- `T_f = 10 s`는 정합한다. 실측 캘리브레이션(L=795.059 m, v_free=33.333 m/s, τ=18 s)에서 CFL 상한은 `min(23.852, L/w, 18.0) = 18.0 s`로 확인했다(탐침 출력). 실측 격자 L=1004.823 m면 상한은 더 여유롭다.
- **60 s 실측 = 6 × T_f** 이므로 `advance_interval(end_time = t0 + 60)`으로 정확히 맞출 수 있다. 잔차 비교는 60 s 격자에서 수행하고 그 사이 6스텝은 내부 전개로 둔다.
- **`T_u = 5 s`는 결합 운전에서 재현 불가능하다.** `StrictHybridPlant.step`이 `dt == freeway.dt_sec`을 강제한 뒤 **같은 dt를 그대로 `urban_plant.step`에 넘긴다**(`hybrid.py:503-505`). 계약 §3.2가 허용한 정수비 subcycle이 미구현이라 결합 시 T_u와 T_f가 강제로 같아진다. 게다가 urban CTM은 20–50 m 셀 + v_free 14 m/s에서 CFL 상한이 약 1.4–3.5 s다(`plant.py:247-253`).
  → **이번 단계는 `StrictHybridPlant(freeway, urban_plant=None)`로 freeway 커널 단독 비교로 범위를 좁힌다.** 3자 비교 목적에는 이쪽이 오히려 깨끗하다.
- τ 하한 제약을 인지해야 한다. CFL이 `τ ≥ dt`를 강제하므로 `T_f=10 s`에서 **τ < 10 s는 파라미터 객체 생성 단계에서 SchemaError**다. 적합 탐색 공간을 τ ≥ 10 s로 제한하거나 더 작은 dt로 돌려야 한다.

### 1-4. 세그먼트 ID·차로수·경계 규약

| 항목 | 규약 | 근거 |
|---|---|---|
| 세그먼트 ID | `{link}__seg{i}` — **NumSim과 플랜트가 이미 같다** | `NumSim-mine/src/models/state.py:1135-1142` `control.vsl.get(f"{link}__seg{i}")` / `bridge.py:253-254` `f"{link_id}__seg{int(segment_index)}"` |
| 실측 ID | `RW_FW_E_S{i}` / `RW_FW_W_S{i}` | FD CSV `segment_id` 열 |
| 차로수 | 세 소스 전부 **4** — 불일치 없음 | FD CSV `lanes=4.0`; `control_mapping.json` `lanes:4`; adapter config `freeway_lanes: 4`; 컴파일된 `link:2`/`link:26` `lane_count=4` |
| 차종 | 플랜트는 class별 재고, NumSim은 단일 class | 플랜트를 `{"default": N}` 단일 class로 고정 |
| 상태 표현 | 플랜트 1차 상태는 **재고(veh)**, 밀도는 파생. NumSim 1차 상태는 밀도 | 재고 기준으로 왕복해야 반올림 손실이 없다 |

세 이름공간을 잇는 매핑 함수는 **코드베이스 어디에도 없다.** 하네스가 만들어야 한다.

---

## 2. 이미 있는 것 — 그대로 쓸 수 있는 부분

### 2-1. 재사용 가능 자산표

| 자산 | 위치 | 그대로 쓸 수 있는가 | 비고 |
|---|---|---|---|
| 세그먼트 ID 규약 | `bridge.py:253` / `state.py:1141` | **그대로** | 무변환 정합. `FW_E__seg0`…로 명명하면 VSL·lane_loss가 자동으로 붙는다 |
| 단위 변환 상수 | `bridge.py:30-31`, `hybrid.py:33-54` | **그대로** | veh/h→veh/s, km/h→m/s, veh/km/lane→veh/m/lane. **ν 변환(km²/h→m²/s)만 없다** |
| `legacy_to_strict` / `strict_to_legacy` | `bridge.py:272, 414` | **그대로** | NumSim `ControlAction`/`DemandStep` dataclass를 duck-typing으로 받는다(`bridge.py:288-295`). NumSim 입력을 strict 입력으로 옮기는 유일한 공식 경로 |
| canonical-json / SHA-256 | `topology.py:59, 88` | **그대로** | 모든 hash·evidence 직렬화의 기반. 계약 §10.1 `canonical-json/v1` |
| `FreewaySegmentParameters` / `FreewayNetworkParameters` | `hybrid.py:114, 212` | **그대로** | 적합 대상 파라미터가 전부 노출돼 있고 CFL·안정성 검증과 `parameter_hash` 자동 산출이 붙어 있다 |
| `StrictHybridPlant.step / advance_interval / rollout` | `hybrid.py:372, 707, 753` | **그대로** | 순수함수. `advance_interval`은 매 스텝 action을 현재 state_hash로 자동 재베이스(`hybrid.py:720-737`) |
| observation envelope 검증 | `observation.py:283-307` | **그대로** | `schema_version`/`observation_id`/`network_hash`/`captured_interval` 검증, 미래 관측 거부 |
| `project_vissim_oracle` | `observation.py:81-155` | **조건부** | `count`와 `speed_mps`를 둘 다 산출한다. **manifest cell의 `model_type`이 freeway로 찍혀야** freeway로 분류된다(`observation.py:687`) |
| `project_detector_realistic` 누출 차단 | `observation.py:316-335` | **그대로** | 화이트리스트 + 재귀 truth 스캔. 이번 단계엔 불필요하나 G4 증거에는 필요 |
| shadow 리포트 골격 | `shadow.py:302-314, 931-934` | **형식만** | `report_digest_sha256` 자기서명 + canonical JSON 바이트 결정성. **판정 로직은 재사용 불가**(아래) |
| `parse_sig` / `green_overlap` | `signal_program.py:159, 125` | 이번 단계 무관 | urban 대조 시 필요 |
| 컴파일러 | `compiler.py:53`, `topology.py:1019` | **조건부** | `modi.inpx`는 valid, **`modi_eval_rw_control.inpx`는 valid=False**(§6-4) |

### 2-2. shadow.py는 3자 비교에 쓸 수 없다 — 확정

| 이유 | 근거 |
|---|---|
| 레코드당 스칼라 목적함수 **2개**만 받는다 | `shadow.py:37-52` `_REQUIRED_FIELDS` 15개에 시계열·셀·세그먼트 필드가 없다 |
| 지표가 전부 순위·비율 통계다 | `DEFAULT_THRESHOLDS`(`shadow.py:24-35`) = Spearman ρ, pairwise 일치율, spillback F1, 런타임 분위수, fallback 비율. **MAPE·MAE·RMSE 없음** |
| 임계값 딕셔너리가 화이트리스트로 잠겨 있다 | `shadow.py:326-329` `unknown thresholds` 예외 |
| 레코드 계약이 무겁다 | `action_hash`/`policy_hash`/`build_hash`/`action_schema_hash` 4개 모두 64자 hex 필수, `shadow_mode=True`·`actuation_attempted=False` 강제 |

**결론.** shadow는 G6/G7/G8 감사기이고 우리가 필요한 것은 G5 계산기다. `shadow.py`에서 가져올 것은 **리포트 자기서명 형식과 게이트 판정 우선순위(FAIL > NOT_EVALUATED > PASS, `shadow.py:288-294`)** 뿐이고 나머지는 새로 쓴다.

### 2-3. 실측 데이터 현황

| 항목 | 값 |
|---|---|
| 파일 | `outputs/no_control_fd_mfd_20260724_freeway_fd_points.csv` |
| 규모 | 976점 = 61 스탬프(900–4500 s, 60 s 간격) × 16 세그먼트 |
| 밀도 분포 | min 2.49 / p50 13.95 / p90 24.40 / p95 27.95 / max 40.85 veh/km/lane |
| 속도 분포 | min 24.77 / p50 66.37 / p95 91.74 / max 114.24 km/h |
| 셀 단위 진값 여부 | **예.** `count`, `mean_speed_kph`가 세그먼트별로 직접 있으므로 `cell_truth` 행으로 바로 매핑 가능 |
| 결측 | `captured_interval`이 없다(단일 `sim_sec` 스탬프). 봉투 합성 필요 |
| v_min 위험 | 속도 < 5 km/h 인 점이 **0%** → NumSim `v_min=5.0` 하한과 플랜트 하한 0의 차이는 이 데이터셋에서 발현하지 않는다 |

`evaluation/runs/*/state_*.csv`는 네트워크 총량 시계열(total/urban/freeway_vehicles, mean_speed_kph)이라 **셀별 잔차에 쓸 수 없다.**

### 2-4. 핵심 발견 — 플랜트 커널을 NumSim과 정확히 일치시킬 수 있다

선행 보고서 C·D는 flux 구조 차이(플랜트 CTM supply/demand vs NumSim q=ρvλ + 순수 저장용량)를 "원리적으로 다른 답"이라고 판정했다. **이것은 틀렸다.** 세 설정만 맞추면 항등적으로 같아진다.

| 설정 | 값 | 왜 |
|---|---|---|
| `w_mps = L_m / dt_sec` | 795.059/10 = **79.5059 m/s** (=286.221 km/h) | 플랜트 receiving의 w-항 `w·(ρ_jam−ρ)·λ`가 NumSim의 `(ρ_max−ρ)·L·λ/dt`와 **항등적으로 같아진다**. CFL은 `dt ≤ L/w`를 요구하므로 **정확히 등호에서 통과**한다(`hybrid.py:232`, 부등호가 `dt > cfl + _EPS`) |
| `q_max_vehps_per_lane` 비바인딩 | 5.0 veh/s/lane (=18000 veh/h/lane) | 플랜트는 sending·receiving **양쪽에 같은 q_max**를 건다(`hybrid.py:437-451`). NumSim은 세그먼트 sending에 캡이 없다 |
| 종단 `OffRampInterface` | `max_rate_vehps = q_cap/3600`, `target_storage_capacity_veh` 대형 | NumSim `terminal_out = min(sending, q_cap·λ/λ_nom)`(`metanet.py:523-525`)를 재현. 없으면 플랜트 마지막 세그먼트는 유출구가 0이라 차량이 무한 적재된다 |

검증 결과(`scratchpad/exactness_probe.py`, 4세그먼트 체인, v_free=120 km/h, ρ_crit=30, ρ_max=180, τ=18 s, ν=65 km²/h, κ=40, a=1.867, L=795.059 m, dt=10 s).

| 케이스 | 초기 ρ (veh/km/lane) | ρ 최대오차 | v 최대오차 |
|---|---|---|---|
| 자유류 | [8, 12, 15, 10] | 3.55e-15 | 1.42e-14 |
| 전이 | [10, 22, 28, 18] | 0.00e+00 | 1.42e-14 |
| **혼잡** | [45, 70, 95, 60] | 0.00e+00 | 3.55e-15 |

**혼잡 영역까지 일치한다.** 이것은 하네스 설계를 근본적으로 바꾼다 — "모델 구조 차이"와 "파라미터 오차"를 분리할 필요 없이, 플랜트를 NumSim의 **비트 등가 재구현**으로 세운 뒤 3자 잔차 전부를 파라미터에 귀속시킬 수 있다.

**반대로, 캘리브레이션 값을 그대로 쓰면(q_max=6900 veh/h 링크, w=삼각FD 등가 11.5 km/h) 어긋난다.**

| ρ (veh/km/lane) | 플랜트 sending | NumSim sending | 상태 |
|---|---|---|---|
| 10 | 4480.5 | 4480.5 | 일치 |
| **17.475** | **6900.0** | **6900.0** | **q_max 캡이 구속되기 시작하는 임계** |
| 20 | 6900.0 | 7467.2 | 어긋남 |
| 30 | 6900.0 | 8428.4 | 어긋남 (−18.1%) |

METANET FD의 최대유량은 **8428.4 veh/h @ ρ=30**으로 cfg 용량 6900을 **+22.2% 초과**한다. 즉 NumSim은 자기 cfg 용량을 세그먼트 내부에서 강제하지 않는다. 실측 976점 중 ρ ≤ 17.475인 비율은 **68.2%**다. 캘리브레이션 값을 그대로 쓰면 데이터의 31.8%가 구조 차이로 오염된다.

---

## 3. 붙여야 하는 것

### 3-1. 배치 원칙

플랜트 코드는 계약 §12(phase 승격)·§14(변경관리) 대상이라 손대면 schema/parameter version 증가와 독립 reviewer PASS가 따라온다. 따라서

> **플랜트 안에는 "계약이 이미 요구하는데 미구현인 것"만 넣는다. 나머지는 전부 별도 하네스에 둔다.**

### 3-2. 플랜트 안(`plant/src/vissim_strict/`)에 넣어야 하는 것 — 2개

| # | 모듈/함수 | 왜 플랜트 안인가 | 현 상태 |
|---|---|---|---|
| P1 | **freeway 세그먼트 분류기** — `topology.py`가 freeway 셀의 `model_type`을 `"metanet"`으로 찍고 `freeway_interfaces`를 채우도록 | 계약 §5.1이 `freeway_interfaces`를 topology manifest의 필수 산출로 정의한다. 하네스에서 우회하면 `topology_hash`가 계약 산출물과 달라져 §14 evidence가 성립하지 않는다 | 미구현. `model_type`은 `"ctm"`/`"lane_group_ctm"`만(`topology.py:608, 635, 721`), `freeway_interfaces`는 항상 `[]`(`topology.py:1108`). `freeway_interface_candidates` 770개가 전부 `status="classification_required"` |
| P2 | **freeway 관측 투영 경로** — `StrictPlant.project_observation`(또는 `StrictHybridPlant`의 신규 메서드)이 `freeway_segment_stock_id`·`freeway_speed_mps`를 채우도록 | 계약 §6.1이 PlantState에 freeway 블록을, §6.2가 관측 투영을 요구한다. 지금은 `observation.py`가 만든 `state["freeway"]`를 래퍼가 **버린다** | 미구현. `observation.py:683-705`가 freeway를 채우지만 `plant.py:1391-1420`이 `urban_refs`만 읽고 `set(urban_refs) != set(self._cells)`면 **예외로 죽는다**. 결과적으로 `hybrid.py:396-398`이 `freeway_state_coverage`로 거부 |

**주의.** P1·P2는 이번 단계에서 하지 않아도 된다. 하네스가 `FreewayNetworkParameters`를 손으로 구성하고 `topology_hash`를 문자열로만 맞추면 커널은 돈다(hybrid 테스트가 `"hybrid-test-topology"` 리터럴을 쓴다). 다만 **그 산출물은 계약 §14 evidence가 아니라 임시 진단물임을 명시해야 한다.**

### 3-3. 별도 하네스에 넣을 것 — 8개

권장 위치 `C:/Users/alsrj/Desktop/학술/찐찐막/Claude/VISSIM/harness/threeway/`

| # | 모듈 | 인터페이스(제안) | 왜 하네스인가 |
|---|---|---|---|
| H1 | `segment_registry.py` | `SegmentRegistry.resolve(vissim_id) -> (plant_segment_id, numsim_link, index, bounds_m, lanes)` | 3중 이름공간·3중 격자 매핑(§1-1). 실측 정본이 확정될 때까지 **자주 바뀐다.** 플랜트에 넣으면 매번 topology_hash가 흔들린다 |
| H2 | `vissim_fd_adapter.py` | `to_raw_observation(csv_rows, manifest, interval_sec=60) -> dict` | FD CSV → `vissim-strict-raw-observation/v1` 봉투. `sim_sec` 단일 스탬프에서 `captured_interval{start,end}` 합성, `network_hash`를 manifest `topology_hash`로 정렬, km/h→m/s. 실험 데이터 포맷은 플랜트 계약이 아니다 |
| H3 | `freeway_state_builder.py` | `build_plant_state(registry, rows, t) -> PlantState` | `VehicleStock(owner_kind="freeway_segment")` + `freeway_speed_mps` 직접 조립. P2가 들어오기 전의 **가교**이며 P2 완성 후 폐기 대상 |
| H4 | `numsim_runner.py` | `step_numsim(state, cfg, K) -> traj` | `freeway_substep`이 state를 **in-place 변형**하므로(`metanet.py:639-642`) 매 스텝 deepcopy 격리 필요. 플랜트는 순수함수라 이 문제가 없다 |
| H5 | `param_builder.py` | `numsim_cfg_to_freeway_params(cfg, registry, mode) -> FreewayNetworkParameters` | §1-2 변환표 + §2-4의 3설정 적용. `mode="exact"`(w=L/dt, q_max 대형) / `mode="calibrated"`(실제 캘리브레이션 값) 두 가지를 낼 것. **ν·κ 명시 주입 필수** |
| H6 | `residuals.py` | `compute(obs, numsim, plant) -> {segment, t, (dρ, dv, dq)}` + `mape/mae/rmse/geh` | G5 지표(freeway mean-speed MAPE, cell count MAE) 계산기. shadow에 대응물이 없다 |
| H7 | `holdout.py` | `split(records, by=("seed","demand_profile","control_policy"))` | 계약 §11 G5가 승인 조건으로 **명시**한다. 결정적·재현 가능해야 한다 |
| H8 | `fit.py` | `sweep(space, evaluate) -> best, trace` | `FreewaySegmentParameters`가 frozen dataclass라 후보마다 새 객체·새 `parameter_hash`가 생긴다. 그 해시 추적을 포함해야 한다 |

### 3-4. 공통 유틸 — §14 evidence emitter

계약 §14는 모든 artifact에 14개 키를 요구한다(`contract_version`, `repo_commit`, `network_hash`, `topology_schema_version`, `plant_parameter_version`, `parameter_hash`, `canonical_json_version`, `observation_mode`, `state_hash`, `action_hash`, `demand_schedule_id`, `subgraph_id`, `seed`, `sim_time_sec`). **이 블록을 찍는 헬퍼는 코드에 없다.** `shadow.py:575-584`는 자기 리포트용 별개 provenance 스키마다.

`repo_commit`은 plant 디렉터리가 git repo가 아니므로(env 확인) 어디서 가져올지 먼저 정해야 한다. 임시로 `network_hash + parameter_hash + 소스 트리 SHA`로 대체하고 그 사실을 명시하는 것이 현실적이다.

### 3-5. 이번 단계에서 **하지 않아도 되는 것**

| 항목 | 이유 |
|---|---|
| VISSIM COM 실측 수집기 | 이미 있는 `no_control_fd_mfd_*.csv`가 셀 단위 진값이다. 새 시나리오가 필요해질 때 붙인다 |
| 차량 레코드 → cell_truth 집계기 | 위와 같음. FD CSV가 이미 집계돼 있다 |
| urban/freeway 정수비 subcycle | freeway 단독 비교로 범위를 좁히면 불필요(§1-3) |
| `StrictCouplingBridge` projector/copy_back | 결합 운전용. 3자 잔차 비교에는 불필요 |
| `plant_parameters` 스키마 확장 | 결과를 `FreewayNetworkParameters.parameter_hash`로만 추적하는 임시 방식임을 문서에 명시하면 된다. 확장은 §14상 schema version 증가 사유이므로 G5 통과 후에 한다 |

---

## 4. VSL 구조 확인 — 비구속 문제는 플랜트에 없다

### 4-1. 두 구현의 VSL 진입 지점

```
NumSim   (metanet.py:93-96)
    no_vsl = v_free · exp( −(ρ/ρ_crit)^a / a )
    V_eff  = min( no_vsl, (1+α_vsl)·vsl )          ← FD 출력에 cap

플랜트  (hybrid.py:431-435)
    limit   = min( v_free·speed_factor, vsl )       ← v_free 슬롯에 min
    V_des   = limit · exp( −(ρ/ρ_crit)^a / a )      ← 지수식의 prefactor
```

사용자 전제("플랜트도 `min(v_free*factor, vsl)` 형태 — NumSim과 동일 구조")는 **문자열로는 맞지만 의미로는 틀리다.** `min`이 지수함수 **앞**에 있느냐 **뒤**에 있느냐가 전부를 바꾼다.

### 4-2. ρ_bind 계산 — 플랜트 파라미터 기본값 기준

플랜트 기본값 `desired_speed_shape = 1.867`(`hybrid.py:126`) + 실세계 캘리브레이션 `v_free = 120 km/h`, `ρ_crit = 30 veh/km/lane`로 계산했다(`scratchpad/vsl_form_probe.py`).

| VSL (km/h) | NumSim ρ_bind | 플랜트 ρ_bind |
|---|---|---|
| 50 | 39.03 | **∞** |
| 60 | 34.44 | **∞** |
| 70 | 30.10 | **∞** |
| **80** | **25.84** | **∞** |
| 90 | 21.50 | **∞** |
| **100** | **16.84** | **∞** |
| 110 | 11.33 | **∞** |
| 120 | 0.00 (무제어 앵커) | 0 (무제어) |

플랜트에서 `vsl < v_free`이면 `V_des(vsl)/V_des(무제어) = vsl/v_free`가 **모든 밀도에서 상수**다. VSL=80이면 어디서나 0.6667배, VSL=100이면 0.8333배다. 즉 **비구속 구간이 존재하지 않는다.**

밀도별 desired speed 비교(km/h).

| ρ | V(무제어) | NumSim V(80) | 구속? | 플랜트 V(80) | 구속? | PL/NS |
|---|---|---|---|---|---|---|
| 5 | 117.755 | 80.000 | YES | 78.504 | YES | 0.981 |
| 12 | 108.928 | 80.000 | YES | 72.619 | YES | 0.908 |
| 16.84 | 100.008 | 80.000 | YES | 66.672 | YES | 0.833 |
| **25.84** | **80.010** | **80.000** | **YES(경계)** | **53.340** | **YES** | **0.667** |
| 28 | 74.934 | 74.934 | **no** | 49.956 | YES | 0.667 |
| 30 | 70.237 | 70.237 | **no** | 46.825 | YES | 0.667 |
| 45 | 38.306 | 38.306 | **no** | 25.538 | YES | 0.667 |
| 60 | 17.008 | 17.008 | **no** | 11.339 | YES | 0.667 |

### 4-3. 판정

| 질문 | 답 |
|---|---|
| 플랜트도 min-form인가 | **형식은 그렇다. 의미는 아니다.** min이 `v_free` 슬롯에 있어 VSL이 FD 전체를 스케일한다(Hegyi/Wu 계열 `v_free` 치환형) |
| NumSim의 비구속 문제(ρ_bind(80)=25.84 < ρ_crit=30)가 플랜트에도 있는가 | **없다.** ρ_bind = ∞ |
| 그러면 플랜트가 더 나은가 | **아니다. 반대 방향으로 틀렸다.** ρ=45에서 플랜트는 25.5 km/h를 목표속도로 삼는다 — VSL 80을 걸었는데 25 km/h로 달리라는 뜻이다. 물리적으로 VSL은 **상한**이지 **감속 명령**이 아니다 |
| 플랜트에도 min-form 경로가 있는가 | **있다. 2군데.** `sending`의 `min(v_current, limit)`(`hybrid.py:441`)과 갱신 후 `speed_ceiling` clamp(`hybrid.py:621-622`). 둘 다 **현재/갱신 속도**에 대한 min이라 `v < vsl`이면 무해하다. 실측 속도가 80 km/h를 넘는 시간은 17.8%(`outputs/vsl_sensitivity_20260801.md:137`)이므로 **82.2%의 시간에는 이 두 경로가 비구속**이다. 그러나 prefactor 경로가 100% 구속하므로 총효과는 항상 존재한다 |

### 4-4. 하네스에의 함의

**1차 비교는 반드시 VSL 비활성 구간(`vsl_mps` 미지정)으로 한정한다.** VSL이 걸린 데이터를 섞으면 τ·ν·κ·a 잔차가 VSL 구조 차이(ρ=45에서 38.3 vs 25.5 km/h, 33% 괴리)로 오염된다. 다행히 실측 정본은 `no_control` 런이라 이 조건이 자동 충족된다.

VSL 구조 정합은 **별도 결정 사항**이다. 어느 쪽을 물리 정본으로 볼지 정하고, 그에 맞춰 플랜트 커널을 고치거나(§6의 G2 재검증 대상) NumSim을 고치거나 해야 한다. 다만 `outputs/vsl_sensitivity_20260801.md:138`이 제시한 실측 재적합 FD(`v_free≈95.3, ρ_crit≈40.8, a≈1.0`, RMSE 8.9 vs 현행 36.4)에서는 **VSL 80이 ρ≤7.1에서만 구속**하므로, min-form을 유지하면 VSL이 사실상 무력해진다. 이 결정은 3자 비교 결과가 나온 뒤에 하는 것이 옳다.

---

## 5. 파라미터 적합 가능성

### 5-1. 파라미터별 판정

| 파라미터 | NumSim 필드 | 플랜트 대응 | 적합 가능? | 비고 |
|---|---|---|---|---|
| **τ** (완화시간) | `metanet_tau_sec=18.0` (`state.py:273`) | `tau_sec` (`hybrid.py:122`) | **가능** | **제약: CFL이 τ ≥ dt를 강제**(`hybrid.py:232`). T_f=10 s면 τ<10은 객체 생성 단계에서 SchemaError |
| **ν** (anticipation) | `metanet_nu_km2_h=65.0` (`state.py:274`) | `anticipation_m2ps` (`hybrid.py:124`) | **가능** | **기본값 0.0 — 항이 꺼져 있다. 명시 주입 필수.** 변환 ×1e6/3600 |
| **κ** | `metanet_kappa_veh_km_lane=40.0` (`state.py:275`) | `kappa_veh_per_m_lane` (`hybrid.py:125`) | **가능** | **기본값 0.001 = 1 veh/km/lane, NumSim의 1/40. 명시 주입 필수** |
| **a** (FD 형상) | `metanet_a_m=1.867` (`state.py:276`) | `desired_speed_shape` (기본 1.867) | **가능** | 기본값이 이미 같다 |
| **v_free** | `v_free` | `v_free_mps` | **가능** | |
| **ρ_crit** | `rho_crit` | `rho_critical_veh_per_m_lane` | **가능** | 불변식 `ρ_crit < ρ_jam`(`hybrid.py:145`) |
| **δ_merge** | `metanet_delta_merge=0.0` (`state.py:200`) | **없음** | **불가능** | 플랜트 속도식은 relaxation/convection/anticipation 3항뿐(`hybrid.py:607-616`). 속도 갱신 루프가 `on_ramps`를 **전혀 참조하지 않는다** |

부수적으로 플랜트에 대응물이 없는 NumSim 기능 3개도 확인했다. 3자 비교에서는 **반드시 꺼둔 상태**로 NumSim을 돌려야 한다(전부 기본값이 OFF라 별도 조치는 불필요하다).

| 기능 | NumSim | 플랜트 | 기본값 |
|---|---|---|---|
| capacity drop (anticipation ν 이중분기) | `capacity_drop_anticipation` + `metanet_nu_cong_km2_h` (`state.py:281`) | 없음 — ν가 세그먼트 상수 | `False` (OFF) |
| capacity drop (queue-discharge φ) | `capacity_drop_discharge_phi` (`state.py:195`) | 없음 | `1.0` (OFF) |
| two-branch VSL FD | `vsl_fd_two_branch` + `rho_crit_two_branch` (`metanet.py:88-91`) | 없음 — ρ_crit이 상수 | `False` (OFF) |

### 5-2. δ_merge — 대안 3가지

δ_merge는 "적합할 파라미터"이기 이전에 **아직 커널에 없는 항**이다. 대안을 우선순위 순으로 제시한다.

| 대안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| **A. δ=0 고정, 6개만 적합 (권장)** | 이번 단계 적합 대상에서 δ를 제외하고 NumSim도 δ=0(기본값)으로 돌린다. 플랜트는 δ=0 기준선 역할 | 코드 수정 0, 3자 비교가 즉시 성립, 나머지 6개 파라미터가 δ 오염 없이 깨끗하게 적합된다 | merge 물리를 재현하지 못한다. metering의 교과서적 payoff가 모델에 없다 |
| **B. 2자 잔차로 δ만 별도 적합** | δ는 VISSIM↔NumSim **2자** 잔차로만 적합한다. 플랜트는 이 항목에서 제외 | 플랜트 미수정. merge 지점 실측(램프 8개 위치가 manifest에 전부 존재)을 활용 가능 | 플랜트가 검증 대상에서 빠지므로 최종 플랜트는 merge 물리를 갖지 못한다 |
| **C. 플랜트 커널에 merge 항 추가** | `hybrid.py` 속도 갱신에 `−δ·dt·q_ramp·v/(L·λ·(ρ+κ))` 추가 | 완전한 3자 비교 | **물리 커널 변경 = 계약상 G2 재검증 대상.** §14상 contract/schema version 판단 필요. 이번 단계 범위를 크게 벗어난다 |

**권고는 A다.** 이유는 (1) 실측 정본이 `no_control` 런이라 램프 미터링 개입이 없어 δ 식별력 자체가 약하고, (2) δ를 넣지 않아도 τ/ν/κ/a/v_free/ρ_crit 6개가 §2-4의 기계정밀도 등가 조건 위에서 깨끗하게 적합되며, (3) 계약 변경 없이 G5 evidence를 생산할 수 있기 때문이다. C는 G5 통과 후 별도 phase로 미룬다.

### 5-3. 적합 가능성 ≠ 식별 가능성 — 경고

파라미터가 노출돼 있다고 해서 데이터로 구별된다는 뜻은 아니다.

| 위험 | 내용 |
|---|---|
| τ–ν 상관 | 두 항이 모두 "속도가 평형에 접근하는 속도"를 조절한다. 평형 근처 데이터만으로는 분리되지 않는다. **강제 응답(forced response) 데이터가 필요하다** — `real_world_modi_pstack_adapter_v1_response_calibrated_20260721.json` notes도 "full METANET calibration still needs a forced-response grid"라고 적어 두었다 |
| 데이터 규모 | 976점(61 스탬프 × 16 세그) 단일 시나리오. seed/demand/policy 홀드아웃(G5 필수)을 나누면 학습셋이 더 줄어든다 |
| 시간 해상도 | 실측이 60 s 집계라 τ=18 s 스케일의 동역학이 3분의 1로 평활화돼 있다. τ 식별력이 근본적으로 약하다 |
| κ 감도 | ρ ≫ κ 영역에서 anticipation 항의 κ 의존성이 사라진다. κ=40 veh/km/lane인데 실측 밀도 p95가 27.95 → 같은 오더라 다행히 식별 가능 구간에 있다 |
| ρ_crit–v_free 교락 | 현행 캘리브레이션이 **평균 회귀가 아니라 상단 포락선**으로 잡혀 있다(`vsl_sensitivity_20260801.md:141-142`). 재적합 시 `v_free≈95.3, ρ_crit≈40.8, a≈1.0`으로 크게 이동하며, `a≈1.0`은 지수형 FD를 Greenshields 근처로 끌어내린다 |
| 초기값 함정 | 재적합으로 `v_free < 120`(VSL 메뉴 최대값)이 되면 two_branch에서 VSL=100이 **v_free보다 빠른 자유류 branch**를 만들어 비물리적 이득이 생긴다(`vsl_sensitivity_20260801.md:340`) |

---

## 6. 위험 — 플랜트를 기준기로 쓸 때의 함정

### 6-1. §11 게이트는 실측 대조를 포함한다 — 그러나 플랜트는 아직 통과하지 않았다

**질문에 대한 직접 답: 예, 포함한다. 두 곳에서.**

| 게이트 | 내용 | 근거 |
|---|---|---|
| **G5: Model selection and calibration** | freeway mean-speed MAPE ≤ 10%, cell count MAE ≤ max(5 veh, 10%), urban one-step queue/storage error ≤ 25%(승격 15%). **seed / demand profile / control policy 단위 holdout 분리 필수.** 선택한 model과 parameter version, uncertainty 범위 기록 | `docs/vissim_strict_plant_g0_contract.md:792-798` |
| **G6: VISSIM parity and ranking** | 동일 초기상태·demand·fixed action의 1-step 및 H=3/H=5 open-loop 비교, forced green/offset/VSL/ramp perturbation 포함, spillback F1 ≥ 0.80(release 0.90), Spearman ≥ 0.70, top-action pairwise ≥ 80% | `contract:800-806` |

**따라서 이번 작업은 새 게이트가 아니라 G5 evidence 생산이다.** 그런데 결정적 사실이 하나 있다.

> **G5 판정을 계산하는 코드가 존재하지 않는다.** `shadow.py`는 G6/G7/G8 전용이고 MAPE·MAE·holdout 개념이 없다(§2-2).

즉 **플랜트는 G5를 통과한 적이 없다.** 통과 여부를 계산할 수단조차 없었다. 이것이 최대 위험의 근원이다.

### 6-2. 순환논증 위험 — 가장 중요한 함정

임무 문구는 "3자 비교로 METANET 파라미터를 적합한다"이지만, 그 안에는 **두 개의 서로 다른 작업**이 섞여 있다.

| 작업 | 플랜트의 역할 | 성립 조건 |
|---|---|---|
| (a) NumSim METANET 파라미터를 실측에 적합 | **불필요하다.** VISSIM↔NumSim 2자로 충분 | 없음 |
| (b) strict plant를 G5 기준으로 검증 | **피검체** | 실측이 정본 |
| (c) 플랜트를 "정답"으로 삼아 NumSim을 교정 | **기준기** | **플랜트가 먼저 G5를 통과해야 함 — 아직 아님** |

**(c)를 (b)보다 먼저 하면 순환논증이다.** 미검증 모델을 기준으로 다른 모델을 교정하고, 그 결과로 원래 모델을 정당화하는 구조가 된다.

게다가 §2-4에서 확인했듯 **플랜트를 NumSim의 비트 등가로 설정할 수 있다.** 그렇게 설정한 플랜트는 NumSim에 대해 **독립적인 정보를 하나도 주지 않는다.** 그 구성에서 "3자 비교"는 실질적으로 2자 비교(VISSIM vs METANET)이고, 플랜트는 구현 무결성 교차검증(cross-check) 역할만 한다.

**권고 — 3자 비교의 목적을 다음과 같이 재정의한다.**

| 층 | 목적 | 산출물 |
|---|---|---|
| 층 1 | 플랜트 ≡ NumSim 등가 확인(§2-4 조건) | 구현 무결성 증거. 잔차 ≤ 1e-12면 두 구현 중 하나의 코딩 오류가 배제된다 |
| 층 2 | (플랜트=NumSim) vs VISSIM 실측 잔차로 파라미터 적합 | **실질적 파라미터 적합.** 어느 커널로 계산해도 같으므로 플랜트로 계산해도 무방 |
| 층 3 | 적합 파라미터로 플랜트 G5 판정 | **G5 evidence.** holdout 분리 필수 |
| 층 4 | 캘리브레이션 값(q_max=6900, w=삼각FD)에서의 플랜트-NumSim 괴리를 별도 기록 | 구조 차이의 크기를 정량화. §2-4 표 |

### 6-3. 캘리브레이션 자체의 순환성

현행 `v_free=120, ρ_crit=30`은 **저밀도 세그먼트 속도 p95 ≈ 121 km/h**에서 온 상단 포락선이다(`vsl_sensitivity_20260801.md:141`). 그 결과 모델은 ρ=15에서 108 km/h로 달린다고 보지만 실측은 70 km/h다(현행 cfg FD RMSE 36.4, bias +35.1). 이 편향은 숨은 버그가 아니라 **문서화된 잠정 캘리브레이션**이다.

**위험.** 이 값을 초기값으로 적합을 시작하면 최적화가 국소해에 갇힐 수 있고, 반대로 재적합 결과(`v_free≈95.3`)를 그대로 채택하면 VSL 메뉴(80/100/120)가 v_free를 넘어서는 비물리 구성이 생긴다(§5-3). **적합 시작 전에 VSL 메뉴와 v_free의 정합 규칙을 먼저 정해야 한다.**

### 6-4. 네트워크 정본 불일치

| 네트워크 | 컴파일 결과 | topology_hash |
|---|---|---|
| `modi.inpx` | **valid=True**, errors=0, controllers=37 | `0c0ecd1e9136792152d3041cc56a53839fb6b134176bd38af584e436362a75ec` |
| `modi_eval_rw_control.inpx` (**실측이 나오는 네트워크**) | **valid=False**, errors=8 (전부 `missing_signal_program`, `sc:9101`~`sc:9108` = 램프미터 SC, `.sig` 부재) | `f52bd9447473606047f1d45bb440131ed516d662b86cfe5dbb2e3a411d63a1ef` |

**모든 strict 스키마가 `topology_hash`에 바인딩된다**(`PlantState`, `DemandSchedule`, `StepAction` 전부). 실측이 나오는 네트워크가 컴파일되지 않으면 계약 정합 evidence를 만들 수 없다. 다만 링크 기하는 두 네트워크가 동일함을 확인했다(link:2/24/26/74 길이가 소수 12자리까지 일치). 따라서 **freeway 물리 비교는 진행 가능하고, evidence 형식화만 이 문제에 막힌다.**

추가로 컴파일러는 `desSpeedDecision`(VSL 액추에이터 64개)을 **아예 파싱하지 않는다.**

### 6-5. 나머지 위험 목록

| # | 위험 | 근거 | 완화 |
|---|---|---|---|
| R1 | **FW_E 격자 불일치** — 측정 위치와 제어 위치가 겹치지 않는다 | §1-1 | 정본 확정 전까지 FW_W 단독 비교 |
| R2 | **질량보존 하드 게이트** — 클래스별 잔차 > 1e-6 veh면 `NUMERICAL_ERROR`로 스텝 자체가 실패 | `hybrid.py:655-670`, `schema.py:18` | 실측 주입 시 stock 합을 정확히 맞춰야 한다. urban 도착/이탈만 외부 항으로 인정되므로 freeway 진입/이탈은 **반드시 가상 stock 경유** |
| R3 | **freeway 본선 진입 경계 부재** — `step`이 `demand.rates_for_interval`을 커버리지 검증용으로만 호출하고 반환값을 버린다 | `hybrid.py:406-409` | 가상 소스 stock + `OnRampInterface`로 우회. 채워 넣기는 `step` 밖에서 PlantState 재구성 |
| R4 | **freeway 종단 이탈 경계 부재** — 하류 연결 없는 마지막 세그먼트는 유출구가 0 | 탐침에서 ρ 25→35 확인(선행 보고 C) | §2-4의 종단 `OffRampInterface` sink로 해결됨 |
| R5 | **stale action 엄격 검사** — `based_on_state_hash`가 현재 `state_hash`와 정확히 같지 않으면 거부 | `hybrid.py:392-393` | `advance_interval`/`rollout`의 재베이스 로직(`hybrid.py:720-737`)을 그대로 따라 할 것 |
| R6 | **경계 세그먼트 규약 차이** — 플랜트는 상류 없으면 convection=0, 하류 없으면 anticipation=0. NumSim은 `v_free`/`min(ρ,ρ_crit)` 기본값 | `hybrid.py:590-606` vs `metanet.py:576, 586-590` | 적합에 **내부 세그먼트만** 쓰거나 NumSim 완충 세그먼트(`freeway_buffer_segments>0`)를 켠다 |
| R7 | **v_min 차이** — NumSim 하한 5 km/h, 플랜트 하한 0 | `metanet.py:122` vs `hybrid.py:622` | 현행 실측에서는 속도 < 5 km/h가 **0%**라 무해. 혼잡 시나리오 추가 시 재확인 |
| R8 | **`freeway_interfaces` 미분류** — 후보 770개가 전부 `classification_required` | `topology.py:1108`, `canonical_topology_*.json` | P1까지는 `FreewayNetworkParameters`를 손으로 구성 |
| R9 | **`StrictPlant`가 freeway 토폴로지를 거부** | `plant.py:157, 168` | freeway 단독 운전(`urban_plant=None`)으로 회피 |
| R10 | **실패 fixture 보존 의무** — §12가 실패 결과·fixture를 삭제하지 말고 versioned output으로 보존하라고 못박는다 | `contract:827-829` | 스윕 중간 산출물도 버리지 말 것 |
| R11 | **독립 reviewer PASS 미정** — G5 evidence를 만들어도 이 승인 없이는 다음 phase production path를 켤 수 없다 | `contract:826` | 누가 어떻게 수행할지 먼저 합의 |
| R12 | **`plant_parameter_version` 증가 의무** — 단순 파라미터 캘리브레이션도 반드시 올려야 한다 | `contract:887` | 적합 산출물마다 버전 부여 |

---

## 7. 권고 실행 순서

| 단계 | 작업 | 산출물 | 선행 |
|---|---|---|---|
| 0 | FW_E 세그먼트 정본 확정(§1-1 권고 1–3) | 갱신된 `control_mapping.json`, `SegmentRegistry` | — |
| 1 | H5 `param_builder` + §2-4 등가 검증 재현 | 플랜트≡NumSim 잔차 ≤ 1e-12 증거 | 0 (또는 FW_W 단독으로 선행 가능) |
| 2 | H2 `vissim_fd_adapter` + H3 `freeway_state_builder` | 실측 → PlantState 경로 | 0 |
| 3 | H6 `residuals` + H7 `holdout` | G5 지표 계산기 | 2 |
| 4 | H8 `fit` — τ/ν/κ/a/v_free/ρ_crit 6개 적합(δ=0 고정) | 적합 파라미터 + `parameter_hash` 추적 | 1,3 |
| 5 | §14 evidence emitter + G5 판정 리포트 | G5 evidence artifact | 4 |
| 6 | (별도 phase) P1·P2 플랜트 반영, δ_merge 항 결정, VSL 구조 정합 | 계약 정합 evidence | 5 + reviewer PASS |

**단계 1은 지금 당장 가능하다.** FW_W는 세 소스가 이미 정합하고, §2-4 탐침이 이미 통과했다.

---

## 부록 A. 재현용 탐침 스크립트

플랜트 소스는 **전혀 수정하지 않았다.** 모든 탐침은 아래 scratchpad에 있다.

```
C:/Users/alsrj/AppData/Local/Temp/claude/C--Users-alsrj-Desktop--------Claude/
  01a4e47a-5c39-4540-824b-c4f338c39ec8/scratchpad/
    vsl_form_probe.py      §4  VSL 진입 형태 및 ρ_bind 대조
    parity_probe_rw.py     §2-4 캘리브레이션 값에서의 구조 괴리 + 바인딩 진단
    exactness_probe.py     §2-4 w=L/dt·q_max 대형화 시 기계정밀도 등가 검증
    canonical_topology_modi.json / canonical_topology_rwcontrol.json  (컴파일 산출물)
```

검증 명령.

```
cd C:/Users/alsrj/Desktop/학술/찐찐막/Claude/VISSIM/plant
"C:/Users/alsrj/anaconda3/python.exe" -B -m unittest discover -s tests -p "test_vissim_strict_*.py"
  → Ran 75 tests in 0.190s / OK
```

## 부록 B. FW_E 총연장 역산 근거

```
link:2          = 4691.599000000157 m   (canonical_topology_modi.json, lane_count 4)
connector:10702 =    1.001500000010 m   (from link 2 @4691.598 → to link 24 @0.0005, lanes 4)
link:24         = 3345.981430444359 m   (lane_count 4)
합계            = 8038.581930444527 m
/8              = 1004.822741305566 m

FD CSV 실측:  4×1.004823 + 4×1.004822 = 8.038580 km = 8038.580 m
차이:         1.93 mm  →  실측 FW_E = link:2 + connector:10702 + link:24 로 확정

FW_W 대조:    link:26 = 8029.342157418707 /8 = 1003.667770 m
              FD CSV = 1.003668/1.003667 km  →  정합
```
