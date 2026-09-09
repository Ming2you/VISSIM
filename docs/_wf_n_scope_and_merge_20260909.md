## Q1 — N 의 범위

### 1. N 은 우리가 제어하는 곳만 세는가 — **아니다 (No)**

`far` 의 N 은 저수지 둘이다 (`vendor/NumSim-mine/src/controllers/stackelberg_mpc.py`):

- `n_u = protected_accumulation_veh(net) + boundary_in_queue_vehicles(net)` (:113)
- `n_main = total_freeway_vehicles(net) − Σ ramp_queue` (:119-120), 평지항은 `:177` 의 `n_main²·tc_h/(2·g_fw)`

`protected_accumulation_veh` (`vendor/NumSim-mine/src/models/state.py:1395-1414) 의 필터는 딱 둘이다 — `if link in off_ramp_storage_links: continue` (:1407) 과 `protected_kinds = {internal, boundary_out, off_ramp}` (:1410). 함수 안에 `net.signals` 도 `net.uncontrolled_nodes` 도 **한 번도 안 나온다.** 소유권 필터가 없다.

저류 키 전수분류 (내가 `evaluation/configs/n21g_g1_20260909.json` 에서 재계산. 이름 접두사가 아니라 **각 movement 의 `origin`→`signal` 선언**으로 판정. 201키 / 58,939.8 veh):

| 분류 | n | cap veh |
|---|---|---|
| 우리 17 이 방류하는 도로 | 59 | 24,125.2 |
| **감시 신호가 방류하는 도로** | **21** | **7,783.8** |
| 우리 17 로 들어가는 `in_*` 게이트 | 24 | 5,953.5 |
| **감시 노드로 들어가는 `in_*` 게이트** | **15** | **4,140.1** |
| 우리 노드의 `*_out` 배출 sink | 24 | 4,868.2 |
| **감시 노드의 `*_out` sink** | **15** | **3,057.5** |
| movement 가 아예 없는 죽은 링크 | 39 | 8,531.5 |
| `OR_*_storage` — **유일한 제외** | 4 | 480.0 |

런타임 루프는 226키를 돈다 (`default.yaml` 의 벤더 장난감 25키가 `_deep_update` 로 합쳐진다; 차량은 0).

### 2. 감시 전용 도로는 N 안에 있다 — 실제 대수

`state_*.json` 의 `local_observation.link_counts` 를 detector mapping 의 `link_to_origins` 로 귀속시켜 재계산했다. **런이 스스로 적은 `urban_total_veh` 를 정확히 재현한다** (1649.0 / 3563.0 / 3216.0). 런 = `evaluation/runs/n21x15f_f3_spill_rl_meter_mf1_20260909`.

| t=900 (n_u=1649.0) | veh | % |
|---|---|---|
| 우리 17 이 방류하는 도로 | 813.7 | 49.3 |
| 우리 게이트 | 263.8 | 16.0 |
| 우리 sink | 141.0 | 8.6 |
| **감시 도로** | **206.5** | **12.5** |
| **감시 게이트** | **167.0** | **10.1** |
| **감시 sink** | **57.0** | **3.5** |

- **신호 레버가 전혀 없는 몫 = 430.5 veh = 26.1%** (t=2700: 917.5 = 25.8% / t=5400: 465.5 = 14.5%)
- 우리 sink 까지 더하면 (그것도 신호가 아니라 출구용량이 뺀다) 571.5 = **34.7%** / 1058.5 = 29.7% / 582.5 = 18.1%

**렌즈 넷의 수치 불일치는 정의 차이일 뿐이고 전부 같은 귀속에서 나온다**: 26.1%(movement-accounting) · 34.7%(empirical-N) · 19.2%(freeway-extent 의 엄격컷 = 감시↔감시 도로 92.5 + 감시게이트 167.0 + 감시sink 57.0) · 22.6%(storage-membership 의 감시도로+감시게이트 373.5). 전부 내 계산에서 재현된다. 평균 내지 말고 정의를 붙여 인용해라.

감시 9개 교차로는 **실재하는 활성 신호기**다: `evaluation/real_world_modi_inventory/signal_controller_roles.csv` 의 102(한티역)·103(은마아파트입구)·104(학여울역)·106(대모산사거리)·2001~2005 가 전부 `role=urban_signal_controller, active=true, type=FIXEDTIME`. 런은 34노드(17제어+17비제어) 전부의 네이티브 VISSIG 스케줄을 컴파일하고 하나라도 없으면 fail-close 한다 (`monitor_fixed_signal_expected_count = schedule_count = 34.0`). 즉 그들은 실제 녹색으로 외생 서비스되고, 리더는 손잡이가 없는데 큐 값은 청구받는다.

부수 사실: `link_to_movements` 로 닿는 259 movement 는 **전부 우리 17 소속**(감시 0, on_ramp 0)이라, 시드 시점 movement 큐(337 veh)는 100% 우리 정지선에 있다. 감시 몫은 순수하게 링크 저류 현상이고, 감시 큐는 롤아웃 안에서만 생긴다.

### 3. 게이트 / sink / 손 닿지 않는 본선 / 램프큐

- **`in_*` 진입 게이트: 들어간다.** 39키 / 10,093.6 veh cap, t=900 에 430.8 veh. 더 나쁜 건 **얼어 있다는 것**: 39개 전부 movement 의 `origin` 이고 `receiving_link` 인 것은 **0개**(내가 확인). `urban_link_storage` 는 receiving link · sink · release pop 에서만 쓰이므로 롤아웃 내내 값이 안 변한다. 게다가 config 에 `urban.boundary` 절이 없어 `seed_boundary_inflow` 는 no-op 이다. 못 빼는 상수인데 `far` 기울기 N/G 는 올린다. (docstring 위반은 아니다 — :1396-1403 은 boundary_in **movement 큐** 제외를 약속하고 kind 필터가 그건 지킨다. 다만 `far` 가 :113 에서 그 큐를 도로 더하므로 결과적으로 boundary_in 은 아무것도 제외되지 않는다.)
- **`*_out` 배출 sink: 들어간다.** 39링크(7,925.7 veh cap; `SC107_E_out`·`SC109_W_out` 은 이름만 `_out` 이고 어떤 movement 의 receiving_link 도 아니라 죽은 분류로 간다). t=900 에 198.0 veh. 이건 **설계 의도**다 — `urban_queue_model.py` 유한출구 블록 주석: "그 잔류는 kind=boundary_out 이므로 protected_kinds 에 들어가 far 도시항 n_u^2 에도 실린다".
- **VSL/미터 손 밖의 본선: 들어간다.** `total_freeway_vehicles` (state.py:1269-1274) 는 42셀 전부를 도달범위 필터 없이 합한다. 실제 권한은 방향당 VSL 존 머리 3개(셀 0/5/10; 존3 = 셀 15-20 은 `vsl_max` 로 고정) + 미터 4개. **37결정 전체에서 120 km/h 를 벗어난 셀은 42 중 10개뿐**(FW_E seg0~seg9, 히스토그램 {120.0: 1199, 100.0: 16, 80.0: 161}, FW_W 는 한 번도 없음).
  - 정정: 셀별 `state_aware` far 분기(`stackelberg_mpc.py:126-175`)는 **죽은 코드**다. :125 의 `getattr(cfg.mpc, "leader_mfd_far_freeflow_offset", False)` 가 게이트인데 그 필드는 `MPCConfig` 에 없고 어느 config/parameters.json 에도 없다(grep 결과: 그 한 줄 + probe 스크립트 2개 + false 로 기록한 probe 출력뿐). 살아 있는 건 :177 의 평지 `n_main²` 항이다.
- **램프 큐: 2차 저수지에 안 들어간다.** `n_main` 이 `Σ ramp_queue` 를 **빼고**, 보상하는 이중선형 항(:189-205)은 `if q <= 0.0: continue` 로 건너뛴다. t=900 에 `leader_ramp_queue_veh = 0.0`(전 롤아웃 상태) → far 의 램프항은 그 결정에서 항등적으로 0이다.

### 4. TTD 결과 — **게임 가능하다. 다만 경계는 예상한 자리가 아니다**

보존 항등식으로 정확히 따지면:

```
total_physical_vehicles (state.py:1224-1260) = total_urban + total_freeway + off_ramp_storage_occupancy + urban_inflow_transit
far 의 N = n_u + n_main       = (total_urban − Σ on_ramp movement 큐) + (total_freeway − Σ ramp_queue)
⇒ total_physical = N + L,   L = Σ on_ramp 큐 + Σ ramp_queue + off_ramp_storage + inflow_transit
⇒ TTD = const − N(T) − L(T)
```

즉 **`TTT − TTD` 는 `TTT + N(T)` 가 아니다. `TTT + N(T) + L(T)` 다.** 빠진 `L` 이 정확히 구멍이다.

**진짜 완료인 경계 (안전):**
- `*_out` sink 의 **유한 출구 게이트** (`urban_queue_model.py:1049-1091`): `departed = min(arrived, boundary_out_capacity_veh_h·T_u_h)`, `arrived = occupancy − pending release buffer`. 게이트를 넘기 전까지 차량은 `*_out` 점유로 N 안에 남는다. **배출 sink 로 밀어넣는 건 공짜가 아니다.**
- freeway `terminal_out` (`metanet.py:545/578`, `mainline_exit_acc`).
- **감시 전용 도로도 구멍이 아니다** — N 안에 있다. SC102 접근로로 밀면 N 이 **올라간다.** 오히려 과청구다(못 빼는 큐를 청구받는다).

**회계 인공물인 경계 (게임 가능):**

| 채널 | 기구 | 상한 |
|---|---|---|
| **(a) off-ramp 저수지 `OR_*_storage`** | `load_off_ramp_storage` (`urban_queue_model.py:466-480`)가 본선 차량을 OR 링크에 적재. OR 은 `protected_accumulation_veh` 의 **유일한 제외**이고 `total_freeway_vehicles` 는 그걸 안 더한다 → **어느 저수지에도 없다.** `total_physical_vehicles` docstring 이 직접 지목: *"두 함수의 합만 쓰면 그 차량이 어느 계정에도 없다 — 실측으로 4 스텝 전진 후 35.46 veh 가 사라졌다."* | 480 veh (4×120). t=1050 예측 종단에 79.716 veh = `total_model_vehicles` 4260.559 의 1.87% |
| **(b) freeway `ramp_queue`** | `n_main` 에서 빼고 보상항은 q=0 에서 skip. q>0 에서도 회계가 어긋난다 — 내가 t=900 에 계산한 **본선→램프큐 1대 이동의 d(far)** = `+0.00299 (R_F_E) / +0.01180 (R_D_W) / −0.02478 (R_D_E) / −0.01800 (R_F_W)` veh·h. **넷 중 둘에서 far 가 미터링을 보상한다.** 혼잡 때문이 아니라 합류셀이 링크 하류(idx 14/13)라 램프항이 잔여 통과시간(0.0345/0.0413 h)만 청구하고 본선 저수지는 한계배수 0.0593 h 전부를 청구하기 때문이다 — 순수 기하 인공물 | Σ `ramp_queue_max_veh_by_ramp` = 111.2+153.2+153.6+174.5 = 592.5 veh |
| **(c) on-ramp 도시 접근 큐** | `protected_kinds` 밖. far 는 :113 에서 boundary_in 만 도로 더하고 on_ramp 는 안 더한다. 현재는 0(관측이 안 닿아 0으로 시드; 259 관측 movement 중 on_ramp 0) — 그러나 롤아웃이 채우는 걸 막는 건 없다 | 점큐, 상한 없음 |
| **(d) `urban_inflow_transit_buffer`** | `total_physical_vehicles` 만 센다(:1262-1267). 두 저수지 어디에도 없다 | 상한 없음 |
| **(e) boundary_out 램프 분할 — 이 런에서 활성** | `boundary_out_ramp_split_enabled = 1.0`, 2링크 (`SC1001_W_out` {free .25, R_D_W .5, R_D_E .25}, `SC1004_W_out` {free ⅓, R_F_E ⅓, R_F_W ⅓}). 램프행 몫은 `ramp_exit_cap = min(ramp_space, metering_release·T_u_h)` 로 sink 점유를 떠나고(N 감소), 코드가 명시적으로 **램프 저수지에 안 더한다** ("여기서는 제약만 건다"). ⇒ **미터를 열면 도시 차량이 모델 어디에도 없이 N 에서 삭제된다.** 제어 의존적 1차 효과 | — |

경화된 누출 저수지만 **≥ 1,072.5 veh** + 상한 없는 채널 둘. n_u 는 1,650~4,900 이다. 반올림 수준의 구멍이 아니다.

**편향의 방향**: 미터를 **열고** off-ramp 로 **돌리는** 쪽이다. 즉 Q2 의 고장과 같은 방향이다.

### 5. 명시적 출구 누산기로 TTD 를 구현하면 답이 바뀌는가 — **바뀐다. 결정적으로**

`−N(T)` 를 TTD 와 같게 만드는 항등식이 깨지는 자리가 정확히 `L` 이다. 출구 누산기는 **실제 완료 사건 둘만** 세고 나머지 질량이 어디 있는지 아예 안 본다. 그래서 (a)~(e) 어느 저수지도 — 세어지든 안 세어지든, 통제든 감시든 — 게임할 수 없다. 그리고 **싸다: 두 누산기가 이미 있고 이미 구간 합산된다.**

- 도시: `boundary_out_sink_veh` (`urban_queue_model.py:1090`, `:1413` 의 `sum_keys` 집합에 포함)
- 본선: `mainline_exit_flow_total` (`metanet.py:784`, `mainline_exit_acc` ← :578/:721)

부수 이득 둘: (i) `−N(T)` 는 "움직이기만 한 재고 감소"도 보상하는데 누산기는 실제로 모델링된 출구용량을 넘은 것만 보상한다. (ii) 감시 전용 도로 과청구가 무해해진다 — 감시 큐가 목적함수에 TTT 를 통해서만 들어오고, 그건 원래 있어야 할 자리다.

**확인 못 한 것**: `boundary_out_sink_veh + mainline_exit_flow_total` 이 substep 질량장부의 `sink_out` 과 정확히 같은지는 확인 못 했다 (`state.py:1230-1240` 이 `N_close = N_open + accepted_external − sink_out` 항등식을 언급하지만 `sink_out` 계산 지점을 못 찾았다). 배선 전에 검증해라.

---

## Q2 — 합류 교란항

### 6. 항이 너무 작은가 — **그렇다. 대략 20배**

식은 교과서 Messmer–Papageorgiou 그대로다 (`vendor/NumSim-mine/src/models/metanet.py:640-644`, 팔로워 복제 `local_freeway_plant.py:311-320`):
`Δv = −δ·T·q_ramp·v / (L·λ_eff·(ρ+κ))`, T[h] · ρ,κ[veh/km/lane] — **문헌 δ≈0.0122 와 같은 단위계**다 (`state.py:225-229`). 단위 환산으로 격차를 메울 여지는 없다. 분모는 정적 λ 가 아니라 `lanes_now[i]`(유효차로)를 쓴다.

확인된 크기 (FW_E 셀 9, t=900: ρ=9.2498, v=63.1295, λ=4, L=0.513441, κ=40, τ=18 s, δ=0.3):

| q_ramp | 스텝당 Δv | 정상상태 결손 | 복원력 25.50 km/h/step 대비 |
|---|---|---|---|
| 428.2 (실측 커넥터 유량) | −0.2227 | 0.538 | 0.87% |
| **638.0 (`demand.ramp_arrival` — 모델 자신의 값)** | **−0.3318** | **0.799** | **1.30%** |
| 1358.0 (arrival + queue/T_f, substep1) | −0.7063 | 1.683 | 2.77% |
| 1800.0 (지령 미터율) | −0.9362 | 2.217 | 3.67% |

q 논쟁 정리: **리더/plant 결합 롤아웃은 `compute_ramp_release_flows` 를 안 쓴다** — `vendor/NumSim-mine/src/simulation/coupling.py:198` 이 도시 모델의 실현 `ramp_metering_release_actual_*` 를 `_actual_ramp_release_flows` 로 갈아끼운다. 팔로워 링크별 롤아웃은 `_local_ramp_release` (`wu_faithful_follower.py:1975-1978`, `available = ramp_queue/T_f_h`, arrival 제외)를 쓰고 매 substep `u_on_{ramp}` 로 재적재된다. 둘 다 도시측 방출 ≈ 도착률에 수렴하므로 **638 이 옳은 자릿수**다.

**필요한 크기:**
- 브리핑의 44 km/h 는 **링크 스칼라 FD** (120/27/1.6) 기준이다. 이 런에서 **셀별 D-lit 표가 실제로 무장돼 있다** (`fw_seg_param_segments = 42.0`, `fw_seg_param_links = 2.0`, `fw_seg_rebind_ved = 2.0`). `FW_E_S9 = {v_free 91.31, rho_crit 25.0, a 2.0, lanes 4}` → V=85.269, **진짜 격차는 22.140 km/h**.
- 런 전체(모델 자신의 차로 프로파일 FW_E 4×13+3×8, FW_W 3×7+4×14 사용. bottleneck CSV 의 `lanes` 열은 링크 스칼라 4/3 이고 42셀 중 22개에서 어긋난다): 합류셀 D-lit FD 대비 **−5.86** 평균, 비합류셀 **+3.52** → **합류 고유 잔차 9.38 km/h 평균 / 9.18 중앙값** (703 vs 6666 표본).
- q = 모델 자신의 도착예보로 완화균형을 각 합류셀 관측마다 역산: n=92, **중앙값 δ = 5.95**, IQR 2.13–16.35, min 0.04, max 420. **δ=0.3 은 합류셀 결손의 중앙값 6.2% 만 설명한다.**
- t=900 셀 9 단일점: 완화만 균형 → δ=11.12 (q=638); 4항 전체 균형(112 km/h 상류셀에서 오는 대류 +16.73 도 이겨야 한다) → δ=23.05.

**0.3 의 출처**: `scripts/calibrate_metanet_ver2n21_20260907.py:299` 의 **문헌제약 격자 `[0.005, 0.0122, 0.05, 0.1, 0.3]` 의 최댓값**이고, 두 문헌 팔이 정확히 거기 붙었다 (`outputs/metanet_calibration_ver2n21_20260907.json`: cell_lit δ=0.3, mid2_lit δ=0.3; mid2_lit 의 `{tau 18, nu 30, kappa 40, phi 3.0}` 이 D-lit 표의 `dynamics` 블록이자 라이브 config 그대로다). 자유 격자(:282)는 40까지 가고 **자유 팔 전부가 δ 를 0→1.0 으로, arm A 는 2.0 까지 올렸다** (`outputs/metanet_calibration_ver2n21_4arm.log:20/26/59/82/98`). 같은 스크립트 :269-271 이 "경계에 붙은 값은 최적이 아니라 더 갈 데가 없었다는 뜻"이라고 적어 놨다. **단서**: 자유 팔은 τ·κ 도 같이 재적합했다(승자: `tau_sec 7→15`, `kappa 25→12`). δ 는 `A = δτq/(Lλ(ρ+κ))` 로만 들어가므로 팔 간 원시 δ 비교는 무효다.

### 7. 원인은 δ 값인가 구조인가 — **구조다. 결정적으로**

독립적인 다섯 줄기:

1. **스크립트가 스스로 그렇게 말한다.** `LIT_STAGES` 주석(:294-296): *"자유 적합이 문헌 밖으로 나가면 그것은 결과가 아니라 **증상**이다 — 다른 오차를 그 축이 흡수하고 있다는."* 자유 적합은 실제로 밖으로 나갔다(1.0~2.0 vs 문헌 천장 0.3). 저장소 자신의 기준으로 δ 는 다른 오차를 흡수 중이다.
2. **단일 δ 로는 못 맞춘다.** 92개 합류셀 관측의 요구 δ 가 0.04~420 (IQR 2.1~16.4). δ 는 전역 스칼라다 — `metanet.py:358` 이 링크 루프 **전에** 한 번 읽고, 셀별 표의 `_keys`(`adapter:8206-8207`)는 v_free/rho_crit/rho_max/a/tau/nu/kappa/length 만 실어서 δ 는 그 기구를 탈 수 없다. 스칼라 하나가 8배 IQR 을 못 맞춘다.
3. **상태 자체가 FD 다양체 밖이다.** t=900 셀 9 는 ρ=9.25 에서 63.13 km/h 를 유지한다. 셀별 FD 가 63.13 을 내려면 **ρ=21.48** 이 필요하다(관측의 2.3배). 단분지 지수 FD 에는 저밀도-저속 분지가 없고, 합류항은 스텝당 감산일 뿐 두 번째 분지를 만들 수 없다.
4. **빠른 완화가 시드를 지운다.** 어댑터가 매 결정 관측 속도를 심는데(`vissim_stackelberg_adapter.py:9418/9425`) 완화+대류 = **+29.03 km/h/step** 이 22.14 km/h 격차를 덮는다. 롤아웃은 45 substep(지평 3 × K_cf 15)이라 **관측은 45 중 1 substep 만 살아남는다.** 이걸 붙잡을 δ(23~34)는 명시적 오일러 사상이 단조를 잃는 구간이다.
5. **FD 가 이미 합류 효과를 한 번 먹었다.** 합류 4셀의 셀별 `v_free` 순위가 42 중 **2·3·7·9위**다 (FW_E_S14 78.1 · FW_W_S7 84.41 · FW_W_S13 88.84 · FW_E_S9 91.31), 평균 85.66 vs 나머지 38셀 112.49. **D-lit 적합이 26.8 km/h 의 합류 감속을 이미 v_free 로 흡수했다.** δ 는 그러고도 남은 9.4 km/h 를, 이미 합류보정된 FD 위에서 설명하라고 요구받는 중이다. δ 를 올리면 이중계상이다.
   *(이 항목은 렌즈 간 미해결 쟁점이었다 — merge-magnitude 조사자가 주장하고 검증자가 "최저 v_free 셀 FW_E_S15 75.96 은 합류셀이 아니다" 로 기각했다. **순위 분포가 결정적이고 조사자가 옳다.**)*

⇒ δ 값은 틀렸지만(0.3 은 경계 인공물), **값을 고쳐도 모델은 안 고쳐진다.** 구조 결함은 (i) 합류셀에 무장된 capacity-drop/이분지가 없다 — 관측을 낸 f3 런은 `capacity_drop_discharge_phi` 가 config 에 없어 1.0=OFF 다(0.85 는 `n21g_g1` 에만), (ii) 합류에 기하 병목이 없다 — FW_E 셀 9 는 4차로에 차로감소 없음(`lane_drop_cell_FW_E = 12.0`), (iii) τ=18 s 완화가 관측을 한 substep 에 덮어쓴다.

### 8. 비혼잡 합류에서 미터링에 비용감소 경로가 있는가 — **하나 있고, 0.45% 다. FW_E 에서는 아예 평가조차 안 된다**

넷을 섞지 마라:

1. **합류 채널은 존재하지만 0.45% 다.** t=900 에 R_F_E 를 완전히 닫으면(q 638→0) 셀 9 의 정상상태 결손 0.799 km/h 가 사라진다. 450초에 그 셀을 통과하는 394.4 veh 에 대해 **TTT 절감 0.02247 veh·h**, 대가는 **램프큐 4.984 veh·h**(638 vph 를 450초 억류, 삼각형). 비 = **0.45%**. δ=6(요구 중앙값)에서도 ~9% 다. 이게 "미터링에 비용감소 경로가 있는가" 의 정직한 답이다 — 있다, 그리고 이 작동점에서 두 자릿수 배로 모자란다.
2. **나머지 경로는 전부 휴면이거나 양수다.** 팔로워 own-TTS 는 `link_vehicles + ramp_queue + offramp_storage + blocked_queue` 를 단위가중으로 청구한다(`wu_faithful_follower.py:2362`) — 미터링은 순수 이전 + 대기손실. capacity-drop 분지는 ρ>ρ_crit 이 필요한데 t=900 에 27.0 을 넘는 셀은 FW_W 셀 4 하나뿐이고 합류셀은 9.25 다. 네 합류의 `recv` 가 전부 **1.0000** (ρ 6.33/13.64/9.25/7.79 대 rho_max 95.02) — 혼잡인지 배수율 할인이 한 번도 안 걸린다. CTM 수용 예약은 ~30배 여유.
3. **far 는 부호가 섞이고 그건 물리가 아니라 기하다.** 위 표: −0.0248 (R_D_E) · −0.0180 (R_F_W) · +0.0030 (R_F_E) · +0.0118 (R_D_W) veh·h/대. 그리고 t=900 에 far 램프항은 통째로 죽어 있다(`leader_ramp_queue_veh = 0.0`).
4. **가격 채널은 구조적으로 "더 열라" 밖에 못 한다.** t=900 `wu_b3_meter_price`: R_D_E 0.0 · R_F_E 0.0 · R_D_W −7.570e-06 · R_F_W −3.661e-05 — 전부 ≤ 0, 기준점 전부 1800=cap. 두 정확한 0 은 **탐침 인공물**이지 구조적 0 이 아니다: `d_r = max(300, 0.20·1800) = 360` 이라 `m_lo = 1440` 인데 모델의 방출 상한은 `available = ramp_queue/T_f_h` = 1080(R_D_E)/720(R_F_E) 라 두 모서리가 비트동일한 롤아웃을 낸다(`wu_b3_meter_fd3_R_F_E_lo == _hi == 550.359371699381`).
5. **FW_E 의 지배적 결함은 약한 기울기가 아니라 사각지대다.** 등예산 미터링 탐색(`wu_faithful_follower.py:3610-3644`, `metering_price_split=True` 라 이 분기가 산다)의 FW_E 격자는 `linspace(ω_E·N_UF* − 1800, 1800, 7)` = **[1122.33, 1235.27, 1348.22, 1461.16, 1574.11, 1687.05, 1800.00]**. 내가 `0.5278631356412602 × 5536.142448979592 − 1800 = 1122.3255124750526` 을 16자리로 재현했고 이는 커밋된 `R_D_E` 와 **동일하다.** 모든 후보가 `available`(시드 1080/720, 이후 `u_on` ≈ 336~638)을 넘으므로 방출이 비트동일하고, 승자는 격자 순서(`best_cost = inf`, 엄격 `<`)가 정한다. **t=900 의 FW_E 미터링 "결정" 은 어떤 δ 에서도 payoff 정보를 담고 있지 않다.** FW_W 는 다르다 — 격자가 813.82 에서 시작하고 `available`(7 veh/T_f_h → cap 1800 로 클립)이 물린다. 0이 아닌 두 가격도 FW_W 램프 둘이다.

⇒ **"컨트롤러가 미터링이 필요 없다고 생각한다" 의 직답: 자기 모델 안에서 컨트롤러가 맞다(+4.96 veh·h 대 −0.02 veh·h). 그리고 동측 링크에서는 질문 자체를 안 한다. δ 만 고쳐서는 둘 다 안 바뀐다.**

### 9. 처방 (순위 · 파급범위 · 요구사항)

**싼 A/B 팔 (config 키 하나, 재적합 없음)**

1. **δ 스윕 0.3 → 3 / 6 / 12** — `config_overrides.network.metanet_delta_merge`. 파급: 양 경로의 모든 롤아웃(`metanet.py:640`, `local_freeway_plant.py:311`). 가치: **귀무 검정**이다 — TTT 가 안 움직이면 §7 진단이 확정된다. 수치 허용범위(단조성 `1 − T/τ − δTq/den > 0`, q=cap): 셀 9 에서 δ<9.0, 3차로 합류셀 FW_E_S14 에서 **δ<6.5**. 3·6 은 안전, 12 는 S14 에서 경계 밖. **먼저 돌리되 수정으로 승격하지 마라.**
2. **미터 가격 탐침 반경을 작동점을 가로지르게 넓혀라** — `metering_price_delta_veh_h` / `metering_price_trust_frac` (`adapter:7000-7001`, 현재 300.0 / 0.20). t=900 R_F_E 에서 모서리가 갈리려면 `d_r > ~1080`. 파급 최소(가격 채널만), 정확한 0 둘이 실제 할선으로 바뀐다.
3. **FW_E 사각지대 제거: 미터링 격자를 N_UF 예산이 아니라 `available` 에서 유도** — 하한을 `min(available, ω·N_UF* − cap)` 로. 재적합 없음. **싼 것 중 가치가 가장 크다** — 이것 없이는 δ·가격·FD 작업 어느 것도 동측 미터링 결정에 닿지 못한다.
4. **`capacity_drop_discharge_phi = 0.85`** — `n21g_g1_20260909.json` 에 이미 있고 `n21f_f3_20260909.json` 에는 없다. 현재 모델에서 합류항이 아니라 **혼잡 완화**로 미터링이 이득을 내는 유일한 기구다. 다만 합류셀에서 ρ>ρ_crit 이 필요한데 FW_E 는 t=1200 이전엔 안 넘는다 → (5)와 묶어야 한다.

**진짜 작업**

5. **합류셀 이분지 / capacity-drop FD** — §7.3 의 구조적 수정. `vsl_fd_two_branch` 는 구현돼 있으나(`metanet.py:20-38, 51-68`) 어디에도 설정되지 않고, 그 `rho_crit_two_branch` 는 getattr 로 읽는 **링크 스칼라**다. 그냥 켜면 (a) 용량이 `v_free·ρ_crit/q_cap` = **1.87배** 부풀고 (b) 셀별 ρ_crit 캘리브레이션을 버린다. 셀별 이분지 파라미터로의 FD 재적합 + 어댑터 `_keys`(:8206-8207) 확장이 필요하다. **가치 최고, 비용 최고.**
6. **합류셀에 기하 병목을 주라** — 물리 FW_E S9 는 on-ramp 와 off-ramp 를 둘 다 물고 있다(D-lit 행의 `ramps` 필드가 "ON R_F_E2 · OFF OR_F_E2" 라고 적혀 있다). 그런데 모델은 4차로 온전, 차로감소 없음. 합류셀 유효차로 감소를 넣으면 합류항 분모(`lanes_now[i]`)를 통해 δ 레버리지가 커지는 **동시에** 진짜 용량 제약이 생긴다. 중비용, 재적합이 아니라 기하 감사가 필요.
7. **δ 를 τ·κ 와 합류셀만 대상으로 공동 재적합** — δ 는 `A = δτq/(Lλ(ρ+κ))` 로만 들어가므로 기존 팔들은 비교 불가고, 현행 0.3 은 `merge_vf_scale = 1.0`(합류 전용 FD 처리 없음)에서 적합됐는데 셀별 v_free 는 이미 합류 감속을 흡수한 상태였다. `scripts/calibrate_metanet_ver2n21_20260907.py` 를 합류 전용 목적함수로 재실행. 중비용.
8. **far 의 램프 회계를 되살려라** — `n_main` 이 램프큐를 빼고 보상항은 q=0 에서 skip 이며 기하 의존적이다(Q1.4b). 램프항을 본선과 같은 2차 저수지 형태로 바꾸면 +0.012/−0.025 부호 뒤집힘이 사라진다. **주의: 이 성분의 캘리브레이션 canary 는 이미 선언으로 억눌러져 있다** (`adapter_calibration_fingerprint_override_active = 1.0`, 상류 `CALIBRATION_FINGERPRINTS["leader_mfd_far"]` 는 여전히 merge {4,6} 인데 라이브 기하는 {7,9,13,14}). 즉 여기 손대면 가드가 없다. 덧붙여 그 지문이 지키는 상수 넷(g_free/g_cong/g_fw/ncrit) 중 셋은 이제 매 결정 온라인 실측되지만(`far_measured_*`) **`leader_mfd_far_ncrit = 1700.0` 은 `evaluation/` 어디에도 없어 벤더 장난감 기본값이 그대로 쓰이고**(`stackelberg_mpc.py:114`), t=900 의 n_u=1649.0 은 그 문턱 51 veh 아래다 — 아무도 이 망에 맞춰 보정한 적 없는 수가 g_free/g_cong 분기를 정한다.

Q1.4 의 TTD 누출과 여기 3·5 는 맞물린다 — **명시적 출구 누산기를 쓰면 리더가 off-ramp 저수지와 램프큐로 질량을 미는 대가를 더는 보상받지 못하고, 그게 현재 유일하게 미터링을 적극적으로 반대하는 유인 자리다.**

---

## 확정하지 못한 것 · 조사자와 검증자가 여전히 갈리는 것

1. **far 가 커밋된 제어에 실제로 미친 영향.** far 는 코드상 살아 있다(`leader_mfd_far_at_d0=True` ← flagship overrides `adapter:6934` → `stackelberg_mpc.py:2410-2413` 의 `far_mode` → `rollout_endpoint.py:408-410` 이 `states[-1]` 에 가산). 런은 `far_measured_*` 메타데이터를 싣고 `whose_code.py` 는 세 렌즈에서 LIVE 7 / DEAD 0 을 냈다. **그러나 런 산출물에 `far` 나 `n_u` 스칼라가 한 건도 없어**, 어떤 후보의 랭킹이 실제로 far 로 갈렸는지는 산출물로 못 보인다. 한 렌즈는 9→3 프리필터가 far-blind(`leader_proxy_near_far` 미설정)라 far 가 결정당 3~4 후보 + PFO 폴백에만 닿는다고 보고했다 — 나는 이건 검증 안 했다.
2. **출구 누산기의 완전성** (Q1.5 단서).
3. **spawn 된 가격 워커 10개가 monitor-fixed-signal 패치를 재설치했는지.** 인프로세스 설치만 입증된다(`patched_module_count 5.0`).
4. **"라이브 팔" 이 어느 런인지.** 브리핑은 `evaluation/configs/n21g_g1_20260909.json` 을 지명하지만, 브리핑이 인용한 t=900 관측은 전부 `evaluation/runs/n21x15f_f3_spill_rl_meter_mf1_20260909` 에서 왔고 그 `run_provenance` 의 tuning 은 `evaluation/configs/n21f_f3_20260909.json` 이다. 두 config 는 도시 토폴로지와 모든 METANET 파라미터가 동일하고 `capacity_drop_discharge_phi` 하나만 다르다(g1=0.85, f3=부재→1.0). **위 Q2 수치는 전부 f3 런, 즉 capacity drop OFF 상태다.**
5. **미해결 쟁점**: t=900 의 FW_W 미터링 선택(`splits[0]` = 격자 최솟값 813.82)이 진짜 최적인지 FW_E 와 같은 격자순서 동률파기인지 못 갈랐다. 그쪽 가격은 0 이 아니므로 비용은 달라야 하지만, `splits[0]` 은 동률일 때도 나오는 값이라 산출물로는 구분이 안 된다.