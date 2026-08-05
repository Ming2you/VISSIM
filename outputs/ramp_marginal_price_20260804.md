# 램프 미터율 한계가격과 그룹 내 비균등 분배 — 종합 판정

작성 2026-08-04. 읽기 전용 조사. VISSIM/COM 미접속, 저장소 파일 미수정.
검증 스크립트는 스크래치패드 `mpprobe/` 아래에만 만들었다.

---

## 0. 세 줄 요약

1. 한계가격은 **이미 있다**. `wu_b3_meter_price_{ramp}`, 램프 그룹 4개 단위, 단위 h².
   그러나 **실측 플래그십 런 76스텝 전부에서 같은 고속도로 링크의 두 모델 램프가
   완전히 동일한 미터율을 받았다**(차이 0건). 가격은 나오는데 행동 차별화가 0이다.
2. 층 2(모델 무변경 그룹 내 분배)는 **구현 가능하다**. 단 "한계가격 기반"이 아니라
   "관측·기하 기반 휴리스틱"이고, 액추에이터가 정수 초 녹색시간이라 **분배 가능한
   스텝이 24.3 %뿐**이다(플래그십 실측 304 램프-스텝 중 230개는 분배 자유도가 0).
3. 층 3(램프 4→8)의 진짜 비용은 코드 수정량이 아니라 **`ramp_queue_max_veh` 가
   네트워크 스칼라 하나**라는 것이다. 이걸 램프별 dict 로 올리지 않으면 8개로 쪼개도
   같은 그룹의 두 램프가 파라미터상 구별되지 않아 목적 자체가 달성되지 않는다.

---

## 1. 한계가격이 지금 코드에 있는가

### 1.1 있다 — 이름·위치·정의 (확인)

| 항목 | 값 |
|---|---|
| 이름 | `wu_b3_meter_price_{ramp}` (B3 metering marginal price) |
| 계산 | `NumSim-mine/src/controllers/stackelberg_wu_metered.py:1352-1460` |
| 섭동 rollout | 같은 파일 `:697-722` `_global_rollout_metrics_with_metering` |
| 국소비용 차감 | `src/controllers/wu_faithful_follower.py:1026-1076` `local_metering_costs` |
| 정의 | `g_ext = (TTT_hi − TTT_lo)/span − (own_TTS_hi − own_TTS_lo)/span` (`:1406`, `:1428`) |
| 단위 | veh·h ÷ (veh/h) = **h²** |
| 입도 | **램프 그룹 4개** (`:1358` `for ramp, x0 in op_meter.items()`, op_meter 는 `net.ramps`) |
| 섭동폭 | `d_r = max(δ, trust_frac·cap)`, VISSIM 에서 δ=300 veh/h, trust=0.20 → 360 veh/h (`:1362-1366`) |
| 부수 진단 | `wu_b3_meter_price_ref_{ramp}`, `wu_b3cert_{ramp}`, `wu_b3_meter_fd3_{ramp}_{lo,base,hi,curv,nonlin,cliffup}` |
| 배달 | `:1830` → `:512-514` `result.metadata.update` + `result.control.diagnostics.update` |
| VISSIM 활성 | `VISSIM/evaluation/controllers/vissim_stackelberg_adapter.py:1158` `metering_price_enabled = True`, `:1170-1171` δ·trust |

**소비처는 SEG13 경로다.** 어댑터 `:1173-1174` 가 `nash_solver.segment_agents = True` 로
켜므로 `wu_faithful_follower.py:4513-4516` 이

```python
if self.segment_agents and self.metering_enabled:
    continue
```

로 `_solve_freeway_agent_metered`(:3220 이하, 2-ramp 7점 심플렉스 SPLIT-PRICE 포함)를
**통째로 건너뛴다**. 실제 가격 소비는 `_solve_freeway_segment_agents` 안의 `:2850-2864`

```python
if own_ramps and m_map is not None and (leader_present or self.seg13_meter_price_standing):
    ...
    cost += self.metering_marginal_price_weight * float(g_m) * (m_r - m_ref)
```

이다(`metering_marginal_price_weight = 1.0`, `:252`). 즉 가격은 "두 램프 사이 배분 랭킹"이
아니라 **각 세그먼트 에이전트의 METER-BOX 5점 레벨 선택**에 붙는다. 예산 맞춤은 그 뒤
`:3106-3140` `_scale_to` 의 **비례 사영 + 잔여 재분배**로 따로 이뤄진다.

### 1.2 실측값 (확인)

`VISSIM/evaluation/runs/new_baseline_ab_20260801/` 의 플래그십 결정 2세트, 각 76스텝.

| 런 | 가격 키 있는 스텝 | SUP_PFO 대체 스텝 | R_D_W | R_F_W | R_D_E | R_F_E |
|---|---|---|---|---|---|---|
| scale135 | 50/76 | 11 | 24/50 nonzero | 45/50 | 22/50 | 38/50 |
| scale170 | 48/76 | 13 | 28/48 nonzero | 46/48 | 30/48 | 35/48 |

크기는 `|g_ext| ≤ 1.19e-04 h²`, 대부분 1e-5~1e-6 대. 부호는 거의 전부 음수(방류를
늘리면 전역 TTT 감소). **램프마다 값이 다르다** — R_F_W(세그먼트 걸침 램프)가 일관되게
가장 크다. 즉 가격 자체는 퇴화하지 않았다.

다만 운영점이 상한에 붙어 있다. scale170 기준 `wu_b3_meter_price_ref_*` 히스토그램은
**1800.0 이 48스텝 중 37**(77 %)이고 나머지가 1500/1200/1102.5/1397.5 다. ref = cap 이면
`m_hi = min(cap, x0+d_r) = x0` 라 secant 가 한쪽 팔뿐이다.
`wu_b4_barrier_enabled = 0.0` — B4 barrier 는 전 스텝 OFF 이므로 `:1429-1432` 의
barrier 합산은 발화하지 않는다. `nonlin` 은 48스텝 중 1~2회, `cliffup` 0회.

### 1.3 결정적 실측 — 가격이 있어도 배분이 갈리지 않는다 (확인)

scale170 플래그십 76스텝 전량에서

```
R_D_W == R_F_W  (76/76),   R_D_E == R_F_E  (76/76)
```

**같은 고속도로 링크의 두 모델 램프 미터율이 한 스텝도 갈리지 않았다.**
값 분포는 R_D_W/R_F_W ∈ {1800×57, 1500×9, 1200×4, 1102×4, 1402×1, 1702×1},
R_D_E/R_F_E ∈ {1800×58, 1500×13, 1398×4, 1698×1}.

원인 추정(확인 아님). 가격 항의 크기가 `|g_ext|·Δm ≈ 1.2e-4 × 300 ≈ 0.036 veh·h` 인데
**같은 런**(`new_baseline_ab_20260801` scale170)의 `leader_follower_ttt_base` 는
80.24~215.89, 평균 147.40 veh·h 다. 외부성 기여가 **2.4e-4** 수준이라 METER-BOX
5점 선택을 뒤집지 못하고, 두 램프의 preferred 가 같아지면 `_scale_to` 의 비례 사영이
그 등가성을 그대로 보존한다.

> **정정 2026-08-04.** 이 문단은 처음에 "같은 rollout 의 기준 TTT 가 93.85 veh·h" 라고
> 썼는데 **분모를 다른 런에서 가져왔다.** 93.85 는
> `mode_probe_20260802/decisions_pstack_event_600s/action_000300.json` 의 값이고
> (이벤트 모드, t=300 워밍업 중), 가격 크기 1.2e-4 는 `new_baseline_ab_20260801`
> 플래그십 런에서 나왔다. 두 런은 수요·모드·시각이 전부 다르다.
> 같은 런의 분모로 고치면 비율은 4e-4 가 아니라 2.4e-4 이므로 결론(가격이 너무 작아
> 선택을 못 뒤집는다)의 방향은 그대로이고 오히려 강해진다. 숫자만 교차 인용이었다.

**93.85 의 정체(확인).** 지평이 길어서 나온 값이 아니다. 같은 파일에서
`leader_state_accumulation_base = 5643.709` veh-step 이고 `T_c_h = 60/3600 h` 이므로
`5643.709 × 1/60 = 94.06 ≈ 93.85`(차 0.21 은 boundary leg 제외분). 상태 3개로 나누면
**상태당 1,881대**다. 즉 93.85 veh·h = 네트워크 전체 약 1,881대 × 3스텝 × 60초 =
**180초**어치 누적이다. 값이 큰 이유는 지평이 아니라 `_state_accumulation_base`
(`leader.py:765-778`)가 고속도로만이 아니라 **도시부까지 전 네트워크 대수를 세기**
때문이다. 같은 시각 실측 state 는 total 1,601대 중 도시부 970대(61 %), 고속도로 615대다.

**함의.** "4그룹 가격을 8미터로 내려보내자"는 층 2·층 3 논의 이전에, **4그룹 가격이
4그룹 배분조차 못 가르고 있다**는 사실을 먼저 인정해야 한다.

### 1.4 없는 것 — 저류 초과의 한계가격 (확인)

과제가 원하는 것은 "넘칠 위험이 큰 램프의 한계비용이 높다"인데, 그 신호를 만들 항이
목적함수에 없다.

- `leader.py:888-892` 가 전 램프·전 horizon 램프 큐를 **스칼라 하나로 합산**하고
  `:913` 이 `w_ramp_queue · ramp_queue_veh · scale` 로 **선형·단일가중**이다.
  따라서 `∂/∂q_r` 이 전 램프 동일 상수, 곡률 0.
- `w_ramp_queue` 는 코드 기본 0.0(`state.py:587`)이지만 **플래그십에서는 6.0 이다**.
  extends 체인을 실제로 풀어 확인했다.
  `flagship_segvsl_fdrefit_20260802 → flagship_segvsl_20260801 → flagship_20260731 →
  vsl_rollout_vissimdsd_20260725 → … → adapter_v1_response_calibrated_20260721`
  의 `config_overrides.leader = {"w_ramp_queue": 6.0, "w_F": 3.0}`.
  값이 켜져 있어도 램프 무차별 상수라는 점은 그대로다.
- `ramp_queue_max_veh` 는 **네트워크 스칼라 float 180.0**이다
  (`state.py:211`, `default.yaml:55`). 어댑터도 `:1014-1016` 에서 `scalar_key` 로 취급한다.
  램프별 저류 19대 vs 99대를 담을 자리가 스키마에 없다.
- 모델 rollout 에서 램프 큐는 **상한 없이 누적**된다.
  `metanet.py:383  state.ramp_queue[ramp] = max(0.0, next_queue)` — 클립 없음.
  `ramp_queue_max_veh` 는 `metanet.py:747-748` 의 `ramp_queue_overflow_count` 진단에만 쓰인다.
- ALINEA 식 큐 오버라이드 훅은 존재한다. `wu_faithful_follower.py:2400-2414`
  `_meter_spillback_floor`. 그러나 `meter_queue_constraint_enabled` 가 기본 False 이고
  **VISSIM configs 어디에도 설정돼 있지 않다**(전수 grep 0건). 게다가 이것도 스칼라
  `net.ramp_queue_max_veh` 를 쓴다.

### 1.5 대체 가능한 것 (판단)

- 저류 압력을 가격에 넣는 가장 싼 경로는 `_barrier_from_states`(`stackelberg_wu_metered.py:631-652`)
  에 램프 큐 hinge 를 더하는 것이지만, **플래그십에서 B4 가 OFF(실측 `wu_b4_barrier_enabled=0.0`)**
  이므로 그것만으로는 `g_ext` 가 1비트도 안 바뀐다. B4 를 함께 켜거나 `_price_ttt`
  (`:654-680`)로 옮겨야 한다.
- 그러나 어느 쪽이든 **저류 상한이 램프별로 없으면 hinge 가 램프를 구별하지 못한다.**
  결국 `state.py:211` 의 스칼라→dict 승격이 모든 경로의 필요조건이다.

---

## 2. 층 2 — 모델 토폴로지를 안 바꾸고 그룹 내 분배가 가능한가

### 2.1 결론

**가능하다. 단 세 가지를 인정하고 시작해야 한다.**

(a) 이건 한계가격 기반이 아니다. 4그룹 가격은 그룹 내 두 미터에 **같은 값**이므로
    비대칭을 만드는 것은 가중치 w_i 이고, 그건 어댑터가 별도로 만든 휴리스틱이다.
(b) 분배 자유도가 액추에이터에 의해 이산·유한하게 제한된다.
(c) 필요한 관측(미터별 램프 저류/큐)이 **현재 관측계약 밖**에 있다.

### 2.2 액추에이터 실체 — VISSIM 은 rate 를 안 쓴다 (확인)

`write_action_csv` 필드 순서(`adapter:3756-3768`)는
`[kind, id, dsd_no, sc_no, link, lane, speed_kph, major_green, minor_green, offset, rate_vph, green_sec, metadata]`
이고 0-기반 index 10 = `rate_vph`, 11 = `green_sec` 이다.
VBS 는 `run_real_world_stackelberg_controller.vbs:725-726`

```vbs
rampGreen(scNo) = CDbl(ToDbl(parts(11)))
readback = ApplyRampMeterSignal(CLng(scNo), CDbl(rampGreen(scNo)), simSec)
```

로 **parts(11) = green_sec 만 읽는다. rate_vph 는 VISSIM 에 한 번도 안 들어간다.**

분배·양자화는 `adapter:2613-2615` 단 3줄이다.

```python
per_meter_rate = group_rate / float(group_count) if distribute else group_rate
green = cycle * per_meter_rate / per_meter_capacity
green = clamp(round(green), min_green, max_green)
```

운영값은 플래그십 tuning 체인을 실제로 풀어 확인했다.
`{cycle_sec: 10.0, min_green_sec: 2.0, max_green_sec: 10.0, per_meter_capacity_vph: 900.0,
distribute_model_rate_across_meters: true}`.

→ **미터당 실효 방류는 90 veh/h 격자, 구간 [180, 900]** (녹색 2~10초).
→ 그룹 실현 방류 = `180 × (g1 + g2)`, 하한 360 veh/h, 상한 1800 veh/h.
→ 모델이 0을 지시해도 플랜트는 360 veh/h 를 계속 방류한다.

### 2.3 올바른 층 2 설계 — rate 가 아니라 **정수 녹색초**를 분배하라

두 검토자가 모두 `per_meter_rate_i = group_rate · w_i / Σw` 형태를 가정하고
"Σ가 안 지켜진다"를 지적했다. 실측으로도 그렇다(수요비례 분배, G=1800 → 실현 1620, −10 %;
저류비례 19:99 → 실현 1170, −35 %). 그러나 그건 공식을 잘못 고른 결과다.

**exact-Σ 설계.** 현재 균등분배가 만드는 녹색초 `g = clamp(round(G/180), 2, 10)` 에 대해
`S ≡ 2g` 를 총 녹색초 예산으로 고정하고, `S` 를 `(g1, g2)` 로 쪼갠다
(각 `∈ [2, 10]`, `g1 + g2 = S`).

- 가중치가 균등이면 `g1 = g2 = g` 로 **현행과 비트 동일**.
- 어떤 분배를 골라도 `Σ realized = 90(g1+g2) = 180g` 로 **총량이 정확히 보존**된다.
- 분배 단위는 1초 = 미터당 90 veh/h.

**분배 자유도 표**(내가 계산, `mpprobe/mp_quantcheck.py` 계열).

| 그룹율 G | 현행 균등 green | 실현 | S | g1 가능범위 | 분할 수 | 최대 비대칭 |
|---:|---:|---:|---:|---|---:|---|
| 1800 | 10/10 | 1800 | 20 | [10,10] | 1 | 1.00:1 |
| 1500 | 8/8 | 1440 | 16 | [6,10] | 5 | 1.67:1 |
| 1364 | 8/8 | 1440 | 16 | [6,10] | 5 | 1.67:1 |
| 1253 | 7/7 | 1260 | 14 | [4,10] | 7 | 2.50:1 |
| 1000 | 6/6 | 1080 | 12 | [2,10] | 9 | **5.00:1** |
| 800 | 4/4 | 720 | 8 | [2,6] | 5 | 3.00:1 |
| 691 | 4/4 | 720 | 8 | [2,6] | 5 | 3.00:1 |
| 600 | 3/3 | 540 | 6 | [2,4] | 3 | 2.00:1 |
| ≤400 | 2/2 | 360 | 4 | [2,2] | 1 | 1.00:1 |

**양 끝에서 분배가 수학적으로 불가능하다.** G=1800 은 두 미터가 동시에 cap,
G≤400 은 동시에 min_green 이다.

### 2.4 층 2 가 실제로 발화하는 비율 (확인)

플래그십 scale170 런의 실제 `ramp_metering` 값 304개(램프 4 × 76스텝)에 위 규칙을 적용.

| 가능한 분할 수 | 램프-스텝 | 비율 |
|---:|---:|---:|
| 1 (분배 불가) | 230 | **75.7 %** |
| 3 | 4 | 1.3 % |
| 5 | 54 | 17.8 % |
| 7 | 8 | 2.6 % |
| 9 (최대 5:1) | 8 | 2.6 % |

**현재 운영점에서 층 2 는 램프-스텝의 24.3 %에서만 무언가를 할 수 있고,
5:1 을 낼 수 있는 스텝은 2.6 %다.** 이것이 층 2 효과의 상한이다.

### 2.5 가중치 w_i 재료가 없다 (확인)

- **미터별 저류 상한이 매핑에 없다.** `control_mapping.json` 의 `ramp_meters` 8개는
  `capacity_vph`(전부 900), `from_link`, `from_pos_m`, `to_model_segment_index` 등만 갖고
  `storage_veh` 류 필드가 **8개 전부 없다**. 과제 표의 19/99/36/50/42/77/40/95 를
  넣을 자리를 새로 만들어야 한다.
- **미터별 큐가 관측 불가능하다.** `detector_local_mapping.json` 의
  `observable_links = [2, 24, 26, 74, 10479, 10480, 10481, 10482, 10483, 10484, 10490,
  10491, 10638, 10639, 10643, 10644, 10645, 10646, 10681, 10682, 10699, 10702]` 에는
  램프 접근링크 **31/32/68/69/70 이 하나도 없다**.
  `guardrails.follower_visibility = "real_world_connector_local_links_only"`.
  관측되는 건 짧은 합류 커넥터의 점유뿐이다.
- **그 커넥터 점유는 포화한다.** g6_v3_full/v6/mixed 전 후보의 t≥2700 최대치를 스캔한
  결과 10482 는 모든 후보에서 정확히 10, 10644 는 v3 전 후보에서 정확히 18(mixed 16).
  즉 커넥터 물리 상한에 붙어 있고, 그 위로 쌓이는 접근링크 큐는 **보이지 않는다.**
  10480 max 4~11, 10646 max 10~35. 과제 표의 저류 19/99 근처에 도달한 관측치는 없다.
- **모델 램프 큐 = 커넥터 2개 합.** `adapter:593-602` 가
  `ramp_link_to_queues` 로 8→4 합산한다. 실측 예(v6 anchor, t=3600):
  `R_F_W = 10646(31) + 10644(6) = 37`, `R_D_W = 1 + 4 = 5`. state json 의
  `ramp_counts` 와 정확히 일치한다. 모델 상한 180 에 한참 못 미치므로
  `spillback_flag`(`g6_core.py:322-333`)의 램프 채널(0.90×180 = 162)은 **원리적으로
  절대 발화하지 못한다**.

### 2.6 접근링크가 그룹 간에 공유된다 (확인, 새 발견)

`control_mapping.json` 의 `from_link` 를 펼치면

| 접근링크 | 미터 (모델 그룹) |
|---|---|
| 31 | RM_C10480 (**R_D_W**, pos 734.9) + RM_C10484 (**R_D_E**, pos 412.1) |
| 32 | RM_C10482 (**R_D_W**, pos 1028.6) + RM_C10490 (**R_D_E**, pos 1330.6) |
| 68 | RM_C10646 (**R_F_W**, pos 352.0) + RM_C10681 (**R_F_E**, pos 117.4) |
| 69 | RM_C10644 (R_F_W) |
| 70 | RM_C10639 (R_F_E) |

5개 접근링크 중 **3개가 서로 다른 모델 그룹의 미터를 함께 이고 있다.**
게다가 `detector_local_mapping.json` 의 `off_ramp_connectors` 를 보면
`OR_D_W → to_link 31, 32` 로, 이 링크들은 **오프램프 유입도 동시에 받는다**.
즉 링크 31/32/68/69/70 은 방향 간 연결로(collector-distributor)이고
저류가 그룹 사이에 공유된다.

**함의.** "그룹 총량 보존 → 그룹 간 영향 없음"은 물리적으로 성립하지 않는다.
R_D_W 안에서 10480 의 녹색을 줄이면 링크 31 큐가 늘고, 그 큐는 같은 링크의
10484(=R_D_E)와 상류 오프램프 10479 를 막는다. 모델에는 이 공유 저류를 담을 상태가 없다
(`state.ramp_queue` 는 그룹당 스칼라).

### 2.7 배관 (확인)

`real_world_ramp_meter_actions` 호출 지점은 저장소 전체에서 `adapter:3848` 하나뿐이다
(정의 `:2563` 제외). 그 함수가 받는 `control` 은 `:4391 write_action_csv(...)` 에 넘어가는
바로 그 객체이므로, `control.diagnostics["wu_b3_meter_price_*"]` 는 **배관 추가 0줄로**
읽을 수 있다.

반면 **관측은 못 읽는다.** `write_action_csv(path, control, cfg, mapping, segment_vsl_func,
metadata, actuation)` 시그니처에 상태·관측 인자가 없다.
`state_json` 은 main 스코프에 있으므로(`:3957` 에서 사용) 인자 2개 추가로 뚫린다 —
난이도는 낮지만 "0줄"은 아니다.

### 2.8 SUP_PFO 구멍 (확인)

`adapter:1414-1432` 에서 감독자가 PFO 를 고르면 `control = pfo_control` 로 통째로 갈린다.
pfo_control 은 별도 `WuFaithfulFollower(sup_cfg).solve(...)` 산출물이라 리더의 가격 meta 가 없다.
실측 — scale170 런 76스텝 중 13스텝(17 %), scale135 런 11스텝이 `sup_pick_pfo = 1.0` 이고
그 스텝들에 `wu_b3_meter_price_*` 키가 없다. **가격 게이트를 걸든 안 걸든 균등 폴백은 필수다.**

---

## 3. 층 3 — 모델 램프 4 → 8 의 실제 비용

### 3.1 주입 경로 (확인)

- `model_topology_overrides` 는 **죽은 키다**. `.py` 전수 grep 결과 소비처 0.
  쓰기는 `generate_real_world_control_mapping.py:888-894`, 언급은
  `adapter:1485` **주석 안**뿐이다.
- 살아 있는 경로는 tuning JSON 의 `config_overrides.network` 다.
  `adapter:1020-1032 tuning_to_config_overrides` → `:1548-1552` (base < flagship <
  calibration < tuning) → `:1558 ExperimentConfig.from_file(..., overrides=...)` →
  `state.py:697-700 NetworkConfig(**raw["network"])`.
- 이 경로는 **이론이 아니라 현재 가동 중이다.** 플래그십 tuning 체인을 실제로 풀면
  `config_overrides.network` 에 `ramp_merge_segment_index = {R_D_W:2, R_F_W:4, R_F_E:3, R_D_E:5}`,
  `ramp_capacity_veh_h = {네 램프 1800.0}` 이 실려 있다.

### 3.2 깨지는 곳 목록

| # | 지점 | 무엇이 깨지나 | 난이도 | 비고 |
|---|---|---|---|---|
| 1 | `state.py:211` `ramp_queue_max_veh: float = 180.0` → `Dict[str, float]` | 램프별 저류 표현 불가. **이걸 안 하면 층 3 의 목적 자체가 달성 안 됨** | **높음** | 소비처가 산술로 스칼라를 쓴다: `urban_queue_model.py:745,934` / `freeway_follower.py:421,432,565` / `leader.py:761` / `distributed_coordinator.py:779,2108,2581` / `spillback_constraints.py:23` / `metanet.py:748` / `wu_faithful_follower.py:2409` / `g6_core.py:323`. 집계형(`× len(...)`)은 `sum(cap(r) ...)` 로 바꿔야 한다 |
| 2 | `grid_topology.py:12` `RAMP_SIDES = ("W","E")` 및 `:84, :133, :196-208` | `urban_movements` / `on_ramp_to_movement` 자동유도가 신규 램프를 조용히 드롭 | 높음 | 손으로 movement 를 나열하는 것은 repo 가 명시적으로 금한다(`state.py:290`, `grid_topology.py:156`) |
| 3 | 유령 램프 무검증 | `ramps` 만 8개로 바꾸면 `on_ramp_to_movement` 가 구 4키를 `setdefault` 로 보존(`state.py:317-322`)해 **차량 보존이 깨진 채 폐루프가 완주한다**. assert·경고 0 | 중간 | `set(on_ramp_to_movement) == set(ramps)` 불변식 검사가 어디에도 없다. 무엇을 하든 이건 먼저 넣어야 한다 |
| 4 | `adapter:3371-3375` `_diagnostic_fixed_control` 이 `control.ramp_metering` 을 4키로 **전체 치환** | G6 후보 전량이 이 함수를 탄다(`g6_core.py:154-166`). 8램프면 신규 키가 없어 `metanet.py:299` 가 cap 으로 폴백 → c10~c15 의 J_model 이 앵커와 비트 동일 | 낮음 | 고치기는 쉬우나 **안 고치고 8램프로 G6 를 돌리면 순위가 조용히 오염된다** |
| 5 | `g6_core.py:57-65` `Candidate.d_ramp_vph / f_ramp_vph` 노브 2개, `:70 _RAMP_OPEN = 1800.0` | 후보 설계가 "4램프 각 1800" 전제 | 낮음 | |
| 6 | `adapter:987-992` `calibration_to_config_overrides` 의 `ramp_capacity_veh_h` 4키 | deep_update 병합이라 최종 12키가 됨(수치는 `net.ramps` 순회라 안전하지만 잠복 함정) | 낮음 | |
| 7 | `stackelberg_mpc.py:24 _CALIB_MERGE_OLD_46`, `:265-295` 지문 대조 | dict 통째 비교라 8램프면 영구 불일치. `leader_hinge` / `np_deadband` / `leader_mfd_far` 3성분 경고 | 낮음(경고만) | 다만 그 튜닝값이 8램프 기하에서 유효하다는 근거는 없다 |
| 8 | `leader.py:544-563, 604-620` N_UF share = `ramp_capacity[r] / total_ramp_cap` | 램프당 share 절반 → 후보 생성 분포 변화 | 중간 | `total_ramp_capacity` 는 900×8 = 1800×4 = 7200 로 불변이므로 상한(`:322,328`)은 안 변한다 |
| 9 | `control_mapping.json` 의 `model_ramp_key` 8개 고유값 + `generate_real_world_control_mapping.py:84-89 MODEL_RAMP_TO_URBAN_SIGNAL` | 이걸 바꾸면 `group_count = 1` → `adapter:2613` 균등 반분이 자동 항등이 됨 | 중간 | 어댑터 코드 수정 불필요 |
| 10 | 테스트 하드코딩 | 램프명 직접 인덱싱 44 hit(`test_metanet_equations.py:105-106` 등) | 중간 | |
| 11 | 가격 rollout 비용 | 램프당 2회 → refresh 당 8→16 rollout | 낮음(비용만) | `price_spsa_enabled` 로 O(1) 근사 가능하나 fd3 곡률 진단을 잃는다(`:1394-1398`) |

### 3.3 층 3의 함정 — 8개로 나눠도 등분이 재현될 가능성 (추정)

§1.3 의 실측(76/76 스텝 링크 내 등분)은 다음 사슬의 결과다.
가격 항이 너무 작아 METER-BOX 선택을 못 뒤집는다 → preferred 가 같다 →
`_scale_to`(`:3106-3121`)의 비례 사영이 등가성을 보존한다.
**램프를 8개로 늘려도 이 사슬은 그대로 남는다.** 그러므로 층 3 만으로는
8개가 4쌍의 등분으로 나올 가능성이 높다고 **추정**한다. 확인은 아니다 — 돌려봐야 안다.

세 그룹(R_D_W / R_D_E / R_F_E)은 두 미터의 `to_model_segment_index` 가 같으므로
(2/2, 5/5, 3/3) 본선 채널에서 오는 차별화가 0 이다.
`R_F_W` 만 4/5 로 갈리고 `segment_straddle: true` 다.
따라서 **항목 1(저류 상한 dict 승격) 없이는 층 3 의 8개 가격 중 6개가 3쌍의 중복이 된다.**

---

## 4. 모델-플랜트 일관성과 G6

### 4.1 G6 가 무엇을 재는가 (확인)

`harness/g6/g6_core.py:265 objective_from_states` 가 `Leader.objective_terms(...)
["leader_total_objective"]` 를 **모델 rollout 상태열과 VISSIM 관측 투영 상태열에
똑같이** 적용한다(`run_g6_shadow.py:139`, `:161`). 순위 상관은
`analyze_g6_ranking.py:73-77` 의 Spearman ρ 와 `shadow.py:391-403` 의 pairwise 다.
게이트는 `plant/src/vissim_strict/shadow.py:24-28` — ρ ≥ 0.70, pairwise ≥ 0.80.

G6 채점 cfg 는 `DEFAULT_TUNING = real_world_modi_pstack_flagship_segvsl_fdrefit_20260802.json`
(`g6_core.py:36`)이므로 **`w_ramp_queue = 6.0` 이 G6 목적함수에 살아 있다.**
`objective_mode` 만 `state_accumulation` 으로 고정된다(`:236`, scale = 1.0).

정량 감도. `state.py:984-989 total_freeway_vehicles` 가 `ramp_queue` 를 포함하므로
**램프 큐의 차량 1대는 J 에서 1(base) + 6(w_ramp_queue) = 7 단위**다.
반면 접근링크(31/32/68/69/70)에 서 있는 차량은 `observable_links` 밖이라
**J_vissim 에서 0 단위**다.

### 4.2 램프 축은 이미 실패해 있다 (확인)

`VISSIM/outputs/g6_v4_verdict_20260804.md`

| 축 부분집합 | ρ | pairwise |
|---|---:|---:|
| anchor + vsl | +0.914 | 0.940 |
| **anchor + ramp** | **−0.350** | **0.333** |
| anchor + green | −0.400 | 0.333 |
| 전체 15후보 | +0.145 | 0.593 |

후보별 예측 ΔJ +0.49 / +0.72 / +4.48 vs 관측 ΔJ +135.11 / +22.13 / +21.67
(문서 표현 "램프 응답이 30~300 배 약하다"). c10 대 c11 의 쌍대순위는 이미 뒤집혀 있다.

**지켜야 할 램프축 순위가 애초에 없다.** "층 2 를 하면 G6 가 나빠지는가"라는 질문은
정상 작동하는 기준선을 전제하는데, 그 기준선이 없다.

### 4.3 층 2 를 하면 G6 가 어떻게 되는가

세 갈래로 정확히 갈린다.

**(a) 가격 게이트를 건 층 2 → G6 궤적 비트 동일 (확인).**
G6 후보 control 은 `_diagnostic_fixed_control` 산출물이라 `diagnostics` 에
`diagnostic_*` 만 있고 `wu_b3_meter_price_*` 가 없다. 가격 키가 없으면 균등 폴백이므로
후보 집행이 안 바뀐다. **단 이건 "모델을 안 건드려서 안전"이 아니라
"가격 경로가 진단 후보에서 발화하지 않아서"다.**

**(b) 관측·기하 기반 가중치(과제가 실제로 원하는 것) → 후보 전량 재실행 필요 (확인).**
게이트가 없으므로 c10~c15, c40, c41 의 플랜트 집행이 바뀐다.
`run_g6_matrix.py:2-4` 가 "플랜트 런은 FD 와 무관하므로 한 번만 돌린 관측 궤적을
여러 FD 구성으로 재채점하면 된다"고 명시한 재사용 전제가 깨진다.
동결 산출물이므로 **기존 리포트가 소급 오염되지는 않지만 재사용은 불가**하다.

**(c) 정량 — §2.3 의 exact-Σ 설계를 쓰면 총량은 정확히 보존된다.**
그러면 J_vissim 이 바뀌는 경로는 두 개로 좁혀진다.

1. **차량이 관측 채널 사이를 이동한다.** 짧은 미터의 녹색을 줄이면 그 커넥터 점유가
   줄고(관측 −7 단위/대), 그 차량은 관측 밖 접근링크에 선다(0 단위).
   반대로 늘리면 +7 단위/대. 램프 축 후보의 관측 ΔJ 분리폭이 21.67~135.11 이므로
   **차량-스텝 3~19대만 옮겨도 후보 간 순위가 뒤집힐 수 있다.**
   커넥터 점유는 스텝당 4~35대 범위이므로 이 크기는 충분히 도달 가능하다.
2. **R_F_W 만 세그먼트가 갈린다**(10646 → S4, 10644 → S5, `segment_straddle: true`,
   모델 대표값 4). 10646 쪽에 실으면 모델에 가까워지고 10644 쪽에 실으면 멀어진다.
   나머지 3그룹은 두 미터가 같은 세그먼트라 본선 주입이 분배 불변이다.

**판정.** 층 2 가 G6 를 나쁘게 만든다고 단정할 수 없고, 좋게 만든다고도 단정할 수 없다.
방향을 사전에 예측할 근거가 코드에 없다. 확실한 것은
**재측정 없이 "G6 무영향"이라고 말할 수 없다**는 것뿐이다.
그리고 g6_v4 문서가 기록한 플랜트 잡음 바닥(셀 대수 MAE 22.858 ≈ 시드간 재현성 22.013)이
하위 램프 후보의 관측 분리폭(21.67, 22.13)과 같은 크기라, 램프 축은 재측정해도
신호와 잡음을 가르기 어렵다.

### 4.4 지금도 이미 어긋나 있는 것 (확인)

층 2/3 과 무관하게 다음 세 가지가 이미 모델-플랜트 불일치다.

1. **균등 반분에서도 Σ가 안 지켜진다.** `round()` 때문이다.
   G=1500 → 1440(−4 %), G=1364 → 1440(+5.6 %), G=1000 → 1080(+8 %),
   G=800 → 720(−10 %), G=600 → 540(−10 %), **G=0 → 360(모델 완전폐쇄, 플랜트 360 veh/h 방류)**.
2. **모델의 큐 상한(180)이 플랜트 물리 저류보다 크다.** 그룹 총 저류는
   R_D_W 118 / R_D_E 86 / R_F_E 119 / R_F_W 135(과제 표 기준)로 전부 180 미만이다.
   모델은 플랜트가 겪는 overflow 를 **원리적으로 표현하지 못한다.**
3. **관측 램프 큐가 커넥터 점유에서 포화한다.** §2.5. 접근링크 큐는 J_vissim 에서
   0 단위이므로, 미터를 조이면 관측 목적함수가 **좋아지는 방향으로 편향**된다.
   이것이 g6_v4 의 "램프 응답이 30~300 배 약하다"의 후보 설명 중 하나다(추정).

---

## 5. 권고 순서

### 5.1 지금 당장 (층 0 — 진단, VISSIM 무관, 위험 0)

1. **`_diagnostic_fixed_control` 이 만드는 액션과 플랜트 실현의 대조표를 남겨라.**
   `mpprobe/mp_quantcheck.py` 식 산술로 충분하다. G6 램프 후보 c10~c15 의
   "모델이 지시한 그룹율 vs 플랜트가 실제 낸 방류"가 −10 %~+8 % 어긋난다는 사실은
   램프 축 ρ = −0.350 의 후보 원인이고, 이건 층 2/3 이전에 해결해야 한다.
2. **순수 `dJ/d(rate_r)` 를 진단으로 내보내라.**
   `stackelberg_wu_metered.py:1406` 뒤에 한 줄
   `meta[f"wu_b3_meter_gi_{ramp}"] = float(g_i)` — 기존 값 비트 동일, 진단만 증가.
   현재 발행되는 `g_ext` 는 총미분이 아니라 외부성 가격이다.
3. **`set(on_ramp_to_movement) == set(net.ramps)` 불변식 검사를 넣어라.**
   차량 보존이 깨진 채 폐루프가 완주하는 현 상태는 층 3 을 시도하는 순간 즉시 물린다.

### 5.2 다음 (층 1 — 관측·매핑 보강)

4. **`control_mapping.json` 의 `ramp_meters` 에 미터별 저류 상한 필드를 신설하고,
   접근링크 31/32/68/69/70 을 관측 대상에 추가할 수 있는지 판정하라.**
   지금은 `guardrails.follower_visibility = "real_world_connector_local_links_only"` 가
   막고 있다. 이걸 못 풀면 층 2 의 가중치는 정적 기하값(길이/저류)만 쓸 수 있고,
   "지금 넘칠 위험"에 반응하지 못한다 — 즉 폐루프 제어가 아니라 고정 배분이 된다.
5. **접근링크 공유(§2.6)를 어떻게 회계할지 먼저 정하라.** 링크 31/32/68 이
   두 모델 그룹의 미터와 오프램프 유입을 함께 이고 있는 이상, "그룹 총량 보존"은
   그룹 간 무영향을 보장하지 않는다.

### 5.3 층 2 — 조건부로 한다

**하되, 다음 5개를 전부 만족시켜라.**

- §2.3 의 **정수 녹색초 예산 분할**로 구현할 것(rate 비례 분배 금지). Σ 정확 보존.
- 가중치는 **가격이 아니라 잔여저류 휴리스틱**임을 논문·코드 주석에 명시할 것.
- 폴백 조건: `sup_pick_pfo=1`, `wu_b3_meter_fd3_*_nonlin=1`, `cliffup=1`,
  `wu_b3cert_*=0`, 그리고 **`ref == cap`(운영점이 상한에 붙어 secant 가 편측)** 인 스텝은
  균등으로 되돌릴 것.
- G6 램프 축·combined 축을 **재실행**할 것. 재사용 불가다.
- 기대치를 낮게 잡을 것. **램프-스텝의 75.7 %에서 분배 자유도가 0 이다.**

**층 2 의 정직한 기대효과는 "일부 국면에서 짧은 램프의 넘침을 늦추는 것"이지
"상충을 자동으로 푸는 것"이 아니다.**

### 5.4 층 3 — 지금은 하지 마라

이유 셋.

1. **선행조건이 안 풀렸다.** `ramp_queue_max_veh` 스칼라→dict 승격 없이는 8개 가격 중
   6개가 3쌍의 중복이 된다(§3.3). 그 승격은 소비처 10곳 이상을 건드리는 별도 작업이다.
2. **가격→배분 사슬이 이미 등분으로 붕괴해 있다.** 4그룹에서 76/76 스텝 등분이므로,
   8개로 늘려도 4쌍 등분이 재현될 가능성이 높다(추정). 층 3 을 하기 전에
   **왜 4그룹조차 안 갈리는지를 먼저 규명해야 한다.**
3. **G6 가 통째로 무효화된다.** `net.ramps` 카디널리티가 바뀌면 후보 생성·N_UF share·
   캘리브레이션 지문이 전부 달라진다. 지금 G6 전체 ρ 가 +0.145 인 상태에서
   기준선을 리셋하면 무엇이 개선인지 판정할 수 없다.

### 5.5 진짜 우선순위 (판단)

가장 큰 효과는 층 2 도 층 3 도 아니다.
**§1.3 의 "가격이 있는데 배분이 안 갈린다"와 §4.4 의 "관측 램프 큐가 포화한다"를
먼저 푸는 것**이다. 전자는 가격 크기(1e-4 h²)가 own-TTS 스케일 대비 4자리 작다는
문제이고, 후자는 관측계약 문제다. 이 둘을 두고 층 2/3 을 얹으면
"작동하지 않는 메커니즘의 입도를 두 배로 늘리는" 일이 된다.

---

## 6. 확인한 것 / 추정한 것

### 6.1 확인 — 코드를 직접 읽거나 산출물을 직접 스캔했다

| 사실 | 근거 |
|---|---|
| B3 metering 한계가격 계산·발행 코드가 존재한다 | `stackelberg_wu_metered.py:1352-1460` 직접 읽음 |
| `price_lite` 는 기본 False 이고 어댑터가 켜지 않는다 | `:150`, `:1238-1250`, 어댑터 grep 0건 |
| VISSIM 플래그십에서 활성 | `adapter:1158, 1170-1171` |
| 실측 가격값 |g|≤1.19e-04, 램프별로 다름, 48~50/76 스텝 | `runs/new_baseline_ab_20260801/decisions_pstack_flagship_*` 전수 스캔 |
| `wu_b4_barrier_enabled = 0.0` (B4 OFF) | 같은 런 진단 |
| `ref = 1800`(cap)이 48스텝 중 37 | 같은 런 진단 히스토그램 |
| **링크 내 두 램프 미터율이 76/76 스텝 동일** | 같은 런 `ramp_metering` 전수 비교 |
| SUP_PFO 스텝 13/76 에 가격 키 없음 | 같은 런 `sup_pick_pfo` 스캔 |
| SEG13 이 `_solve_freeway_agent_metered` 를 스킵 | `wu_faithful_follower.py:4513-4516` |
| 가격 소비는 `:2850-2864`, weight = 1.0 | 직접 읽음, `:252` |
| leader 램프 큐 항이 합산·선형 | `leader.py:888-892, 913` |
| **flagship 에서 `w_ramp_queue = 6.0`** | extends 체인 실제 해석(스크립트로 병합) |
| `ramp_queue_max_veh` 스칼라 180.0 | `state.py:211`, `default.yaml:55` |
| 모델 램프 큐가 클립되지 않는다 | `metanet.py:383`, `:747-748` |
| `_meter_spillback_floor` 존재하나 기본 OFF, VISSIM configs 설정 0건 | `wu_faithful_follower.py:2400-2414`, grep |
| VBS 가 `parts(11) = green_sec` 만 읽는다 | `run_real_world_stackelberg_controller.vbs:725-726` + CSV 필드 순서 `adapter:3756-3768` |
| 양자화 파라미터 cycle 10 / min 2 / max 10 / cap 900 / distribute true | 플래그십 tuning 체인 실제 해석 |
| 균등 반분에서도 Σ가 −10 %~+8 % 어긋나고 G=0 이어도 360 veh/h 방류 | 내 산술 재현 |
| 분배 자유도: 램프-스텝 304 중 230(75.7 %)이 분할 1가지 | 플래그십 실측 rate 에 규칙 적용 |
| `storage_veh` 필드 부재(8개 미터 전부) | `control_mapping.json` 파싱 |
| 접근링크 31/32/68/69/70 이 `observable_links` 에 없음 | `detector_local_mapping.json` |
| 커넥터 점유 포화(10482 max 정확히 10, 10644 max 정확히 18) | g6_v3/v6/mixed 전 후보 t≥2700 스캔 |
| 관측 `ramp_queue` = 커넥터 2개 합 | `adapter:593-602` + state json `ramp_counts` 대조 |
| 접근링크 3개가 그룹 간 공유(31, 32, 68) | `control_mapping.json` `from_link` |
| 접근링크 31/32 이 오프램프 유입도 받는다 | `detector_local_mapping.json` `off_ramp_connectors` |
| `model_topology_overrides` 소비처 0(죽은 키) | `.py` 전수 grep |
| 살아 있는 주입 경로가 `config_overrides.network` | `adapter:1020-1032, 1548-1558`, 플래그십 체인에 실제로 실려 있음 |
| `_diagnostic_fixed_control` 이 4키 전체 치환 | `adapter:3371-3375` |
| G6 목적함수 = `leader_total_objective`, 채점 tuning = 플래그십 | `g6_core.py:265-311, 36, 236` |
| G6 spillback 램프 채널이 원리적으로 미발화(0.90×180 = 162 vs 관측 max 37) | `g6_core.py:322-333` + 관측 스캔 |
| 램프 축 ρ = −0.350, pairwise 0.333 | `outputs/g6_v4_verdict_20260804.md` |
| `real_world_ramp_meter_actions` 호출 지점 1곳, `write_action_csv` 에 상태 인자 없음 | `adapter:3848, 3741-3749` |
| `ramp_probe_20260804` 는 실패했다(상태 파일 0, WATCHDOG FAIL) | 런 디렉터리 확인 |

### 6.2 추정 — 근거는 있으나 실행으로 확인하지 않았다

| 추정 | 근거 | 확인 방법 |
|---|---|---|
| 링크 내 등분의 원인이 "가격 크기가 own-TTS 스케일 대비 4자리 작아 METER-BOX 선택을 못 뒤집는다" | `|g_ext|·Δm ≈ 0.036 veh·h` vs **같은 런**의 `leader_follower_ttt_base` 평균 147.40 veh·h (비 2.4e-4). 소비 지점(`:2850-2864`)과 사영(`:3106-3121`) 구조 | `preferred_meter` 를 진단으로 내보내 두 램프 값이 실제로 같은지 확인 |
| **가격 롤아웃 지평(180초)이 램프 축을 보기에 너무 짧다** | `_predict` 깊이 = `horizon_steps(3) + leader_value_depth(0)` = 3스텝 × 60초 (`stackelberg_mpc.py:2405`, `state.py:358`, 실측 `metadata.mpc_horizon_steps=3.0`·`prediction.control_interval_sec=60.0`). g6_v4 지평표에서 H=180초일 때 램프 축 구분폭 0.061 km/h = H=900초 값(0.818)의 **7.5 %** | `leader_value_depth` 를 올려 같은 상태에서 `wu_b3_meter_price_*` 가 램프별로 갈리는지 오프라인 비교 |
| 층 3 을 해도 8개가 4쌍 등분으로 나온다 | 위 사슬이 램프 수와 무관하게 유지됨 | 8램프 config 로 폐루프 1회 |
| 관측 램프 큐 포화가 "램프 응답 30~300배 과소"의 원인 중 하나 | 접근링크 큐가 J_vissim 에서 0 단위이므로 미터 조임이 관측 J 를 좋게 만드는 편향 | 접근링크를 관측에 넣고 g6 재실행 |
| 층 2 가 램프 축 ρ 를 개선/열화시키는 방향 | 예측 불가. 차량-스텝 3~19대면 순위가 뒤집힘 | 재실행 외에 방법 없음 |
| 8램프 확장 시 `R_F_W` 만 유의미한 가격 차이가 날 것 | 유일하게 merge segment 가 갈림(4/5) | 실행 |
| 과제 표의 저류값(19/99 등)이 접근링크 기준인지 커넥터 기준인지 | 관측 커넥터 max 는 4~35 로 표의 값에 못 미친다. 링크 31 에 10480(pos 734.9)과 10484(pos 412.1)가 함께 있어 "램프 길이" 정의가 모호 | 저류값의 산출 근거를 확인 |

### 6.3 앞선 조사에서 정정한 것

- "flagship 에는 `leader` 블록이 없어 `w_ramp_queue = 0`" → **틀렸다.**
  extends 체인으로 `adapter_v1_response_calibrated_20260721.json` 의 6.0 이 상속된다.
- "SPLIT-PRICE 7점 심플렉스(`wu_faithful_follower.py:3572-3593`)가 이미 예산 고정 +
  가격 배분을 하고 있다" → **플래그십에서는 죽은 코드다**(`:4513-4516` continue).
  실제 경로는 `:2850-2864` 레벨 선택 + `:3106-3121` 비례 사영이다.
- "`_ramp_candidates` / `FreewayFollower` 를 고치면 된다" → 그 클래스는 `NashSolver`
  경유로만 살아나며 플래그십에서는 생성되지 않는다.
- "`stackelberg_allocation_mode`" 논의 전체 → 플래그십은 `DistributedCoordinator` 를
  쓰지 않으므로 배분 모듈 3종(`inflow_outflow_allocation.py`,
  `simplified_inflow_outflow_allocation.py`, `distributed_coordinator.py`)이 전부 비활성이다.
  배분 모듈에 가격을 넣는 선택지는 검토 대상에서 제외한다.
- "Σ per_meter_rate 보존이면 모델이 보는 세계는 안 바뀐다" → 액추에이터가
  정수 초 녹색이라 rate 비례 분배로는 Σ가 안 지켜진다. §2.3 의 정수 녹색초 분할로
  바꿔야 성립한다.
