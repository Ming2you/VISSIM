# VSL 채널 감도 진단 통합 판정 (2026-08-01)

대상 real-world 체인은 `real_world_modi_pstack_flagship_segvsl_20260801.json`(= flagship_20260731 + 세그먼트별 VSL)이고,
플랜트는 NumSim `src/models/metanet.py:freeway_substep`, 솔버는 `WuFaithfulFollower._solve_freeway_segment_agents`다.
재현 스크립트는 `C:/Users/alsrj/Desktop/학술/찐찐막/Claude/VISSIM/scripts/diagnose_vsl_channel_20260801.py`이며
`binding | gain | tiebreak | fd | all` 파트를 인자로 받는다. 아래 모든 수치는 이 스크립트 출력이다.

---

## 0. 한 줄 결론

혼잡 구간의 평탄함(cost spread = 0)은 **정상 물리**다. 그러나 그 물리는 "VSL이 이 설정에서 이득을 낼 방법이 아예 없다"는
더 큰 사실의 부분집합이고, 그 위에 **실제 버그 두 개**(타이브레이크 래칫, 예측-플랜트 배선 불일치)와
**캘리브레이션 편향 하나**(내부 FD가 실측 대비 +35 km/h)가 얹혀 있다. 네 보고서 중 A·B·D의 골자는 실측으로 확인됐고,
C의 처방("메뉴 바닥을 내리면 된다")은 **반증**됐다 — 메뉴를 50까지 내려도 이득은 0건이다.

| 질문 | 판정 |
|---|---|
| 혼잡 평탄함은 물리인가 버그인가 | 물리(비구속). 단 그 물리를 만든 것은 설정 선택이다 |
| VSL 이득 상태·horizon이 존재하는가 | 현행 설정에서 **0건**. 기전(two_branch + drop)을 켜면 생기지만 최대 −1.1% |
| 주범 1위 | 이득 기전 전면 OFF(`vsl_fd_two_branch` 미정의) — 메뉴가 아니다 |
| 즉시 고쳐야 할 버그 | 타이브레이크 래칫(솔버가 근거 없이 VSL 80으로 내려가 고착) |
| zone4 A/B | VSL 채널로는 무의미. 타이브레이크 정합 후 **metering 채널로 평가**해야 한다 |

---

## 1. 물리인가 버그인가 — 세 층으로 분해

VSL이 상태식에 들어가는 경로는 하나뿐이다. `metanet.py:96`

```python
return float(min(no_vsl, (1.0 + alpha_vsl) * vsl))
```

`alpha_vsl=0.0`이므로 `V_eff = min(V(ρ), VSL)`이다. 따라서 `VSL ≥ V(ρ)`이면 VSL은 상태식에서 **항등적으로 사라진다**.
구속 상한은 `ρ_bind(vsl) = ρ_crit·(a·ln(v_free/vsl))^(1/a)`다.

### 1-1. 층 A — 물리 (정상)

| VSL | ρ_bind | ρ_bind/ρ_crit | 실측 밀도 중 구속 비율 |
|---|---|---|---|
| 50 | 39.03 | 1.301 | 0.997 |
| 60 | 34.44 | 1.148 | 0.990 |
| 70 | 30.10 | 1.003 | 0.971 |
| **80** | **25.84** | **0.861** | 0.927 |
| 90 | 21.51 | 0.717 | 0.825 |
| **100** | **16.84** | **0.561** | 0.656 |
| 110 | 11.33 | 0.378 | 0.354 |
| 120 | 0.00 | — | `vsl_active=False`(무제어 앵커) |

현행 메뉴 `[80, 100, 120]`의 최저 rung 80이 `ρ_crit=30`보다 낮은 25.84에서 구속을 끝낸다. 즉 임계밀도 이상에서
구속력을 갖는 메뉴 값이 **하나도 없다**. plant 실측으로 재현했다(K=6 substeps = 제어주기 1스텝, 균일밀도).

| ρ | J(80) | J(100) | J(120) | spread(80 vs 120) |
|---|---|---|---|---|
| 12 | 9.2692 | 9.0514 | 8.9552 | +3.5067% |
| 20 | 15.0740 | 14.8523 | 14.8523 | +1.4927% |
| 28 | 21.3889 | 21.3888 | 21.3888 | +0.0006% |
| **32** | **24.7715** | **24.7715** | **24.7715** | **+0.0000%** |
| **45** | **36.0330** | **36.0330** | **36.0330** | **+0.0000%** |

사용자 관측 "혼잡 구간 cost spread 0.00e+00"은 그대로 재현된다. **버그가 아니다.**

### 1-2. 층 B — 설정 (이득 기전 전면 OFF)

문제는 평탄함이 아니라 **감도가 남은 구간의 부호가 항상 같다**는 것이다. 위 표에서 보듯 VSL을 낮추면 항상 손해다.
이유는 VSL의 이득 경로가 전부 꺼져 있기 때문이다.

| 기전 | 현행 real-world | 근거 |
|---|---|---|
| `vsl_fd_two_branch` (VSL이 ρ_crit을 올림) | **필드 자체가 없음 → False** | `NetworkConfig`에 필드 미정의(`state.py:179~`), `getattr` 기본 False |
| `capacity_drop_anticipation` (ν regime 전환) | False | `state.py:281` 기본값, tuning 체인에 override 없음 |
| `capacity_drop_discharge_phi` (송출 drop) | 1.0(비활성) | `state.py:195` |
| `metanet_delta_merge` (merge 교란) | 0.0 | cfg 덤프 |

`effective_rho_crit`(`metanet.py:61-68`)이 `vsl_fd_two_branch=False`면 `net.rho_crit`을 그대로 반환하므로,
VSL은 ρ_crit도 못 옮기고 capacity drop도 못 피한다. 남는 효과는 "송출 유량을 깎는 것" 하나뿐이다.
**즉 VSL은 구조적 열등전략(strictly dominated)이다.** 이건 물리가 아니라 설정 선택이다.

### 1-3. 층 C — 실제 버그 2건

**(C1) 타이브레이크 래칫 — 실제 솔버로 재현** `wu_faithful_follower.py:2816-2825`

```python
best_cost = float("inf")
...
for v_cand in v_cands:          # v_cands는 vsl_set 오름차순 [80, 100, 120] 필터
    for m_map in m_combos:
        ...
        if cost < best_cost:    # strict <
```

spread가 정확히 0이면 strict `<`는 첫 후보에서만 발화하고, 이후 동률 후보는 전부 기각된다.
결과적으로 **후보 중 최저 VSL이 선택된다**. 실제 솔버 호출 결과(leader=None, 가격 0, ρ=35 균일 = 전 rung 비구속).

| 상태 | previous | flagship(단일세그) 결정 | zone4 결정 |
|---|---|---|---|
| ρ=35 | 120 | `[120,100,100,100,100,100,100,100]` | `[120,120,120,120,120,120,120,120]` |
| ρ=35 | 100 | `[120,80,80,80,100,80,80,80]` | `[120,120,100,100,100,100,100,100]` |
| ρ=45 | 100 | `[120,80,80,80,80,80,80,80]` | `[120,100,100,100,100,100,100,100]` |

`previous`를 직전 결정으로 갱신하며 5스텝 돌리면 래칫이 드러난다(ρ=35 고정, seg3).

```
flagship: 120 -> 100 -> 80 -> 80 -> 80 -> 80   (VSL-BOX 20이라 한 스텝에 한 칸씩 내려가 80에 고착)
zone4   : 120 -> 120 -> 120 -> 120 -> 120 -> 120
```

즉 로그의 `vsl_active_steps`는 **최적화 근거 없이 켜진 것**이며, 지금까지의 "VSL 활성" 판정은 전부 재해석해야 한다.
그리고 VISSIM에서는 그 80이 DSD로 **실제 집행**되므로, 모델이 "무차별"이라 판단한 구간에서 실차량은 비용을 낸다.

**(C2) 예측-플랜트 배선 불일치** — 예측모델이 `select_anticipation_nu`에 vsl을 넘기지 않는다.

| 위치 | 호출 |
|---|---|
| 플랜트 `metanet.py:615` | `select_anticipation_nu(rho, net, vsl_i)` |
| 예측모델 `local_freeway_plant.py:623` | `select_anticipation_nu(rho, net)` — **vsl 없음** |

`select_anticipation_nu`의 docstring이 명시한다 — "two_branch면 capacity-drop 발화 임계를 ρ_crit(VSL)로 …
VSL의 교과서 이득". 현재는 `capacity_drop_anticipation=False`라 동작 불변이지만, 아래 처방 P3에서 기전을 켜는 순간
**follower만 이득을 못 보는** 비정합이 된다.

### 1-4. 층 D — 캘리브레이션 편향(내부 FD가 실측보다 +35 km/h 빠르다)

| 밀도대 | n | VISSIM 실측 평균속도 | 모델 V(ρ) | 편차 |
|---|---|---|---|---|
| 0–5 | 48 | 85.1 | 119.4 | **−34.3** |
| 5–10 | 228 | 79.4 | 115.3 | **−35.9** |
| 10–15 | 275 | 70.0 | 108.1 | **−38.1** |
| 15–20 | 204 | 61.5 | 98.7 | **−37.2** |
| 20–25 | 138 | 55.0 | 87.7 | **−32.7** |
| 25–30 | 54 | 50.4 | 76.1 | **−25.7** |
| 30–40 | 27 | 42.9 | 58.7 | **−15.9** |

(실측 976점, `outputs/no_control_fd_mfd_20260724_freeway_fd_points.csv`, 현행 cfg FD RMSE 36.4 / bias +35.1)

실측 속도가 80을 넘는 시간은 **17.8%**, 100 초과 1.6%, 120 초과 0.0%다. 실측 FD에 지수형을 재적합하면
`v_free≈95.3, ρ_crit≈40.8, a≈1.0`(RMSE 8.9)이고, 이 FD에서는 **VSL 80이 ρ≤7.1에서만, VSL 100은 어디서도 구속하지 않는다**.

이 편향은 숨은 버그가 아니라 **문서화된 잠정 캘리브레이션**이다. `real_world_modi_pstack_adapter_v1_response_calibrated_20260721.json` notes가
"v_free uses low-density freeway segment p95 speed around 121 km/h", "full METANET calibration still needs a forced-response grid"라고 적어 두었다.
즉 v_free/ρ_crit이 **평균 회귀가 아니라 상단 포락선(envelope)** 으로 잡혀 있다. 그 결과 두 가지가 동시에 일어난다.

- 내부 모델이 보는 VSL "구속력"의 상당 부분이 실재하지 않는다(모델은 ρ=15에서 108 km/h로 달린다고 보지만 실제는 70이다).
- 그래서 내부 모델이 계산하는 VSL "페널티"(자유류에서 −3~−15% TTT 손해)도 **상당 부분 가짜**다. 실제로는 DSD 80을 걸어도
  대부분 차량이 이미 80 미만이라 아무 일도 안 일어난다.

---

## 2. VSL이 이득을 내는 상태·horizon 조합이 존재하는가

### 2-1. 현행 설정 — 0건 (C 보고서의 처방 반증)

메뉴를 `[50,60,70,80,90,100,120]`으로 **확장한 채로** ρ 12~45 × K=6/18/36 substep × 균일/계단 밀도를 전수 스윕했다.
`J(VSL) − J(120) < 0`인 셀은 **한 개도 없다**.

K=18 substeps(= MPC horizon 3스텝 × 60s = 180s), 변형 a(현행)

| ρ | J(50) | J(70) | J(80) | J(100) | J(120) | best | Δbest |
|---|---|---|---|---|---|---|---|
| 12 | 28.2571 | 25.7991 | 24.6353 | 22.4483 | **21.3782** | 120 | +0.000e+00 |
| 16 | 35.5714 | 32.3702 | 30.8553 | 28.0127 | **27.4447** | 120 | +0.000e+00 |
| 20 | 43.0912 | 39.1325 | 37.2602 | 34.5073 | **34.3634** | 120 | +0.000e+00 |
| 24 | 50.8027 | 46.0977 | 43.9482 | 42.7140 | **42.6526** | 120 | +0.000e+00 |
| 28 | 58.6816 | 53.4173 | 52.2929 | 52.0546 | **52.0156** | 120 | +0.000e+00 |
| 32 | 66.5667 | 62.2535 | 62.0963 | 62.0017 | **61.9782** | 120 | +0.000e+00 |
| 36 | 74.4991 | 72.4190 | 72.3670 | 72.3243 | **72.3121** | 120 | +0.000e+00 |
| 45 | 96.5279 | 96.4812 | 96.4786 | 96.4752 | **96.4737** | 120 | +0.000e+00 |

**따라서 C 보고서의 "주범은 vsl_set 바닥값, 조치는 메뉴를 [50…]으로 내리는 것"은 틀렸다.**
메뉴를 내리면 *감도(binding)* 는 회복되지만 *부호* 는 회복되지 않는다. C 자신이 open에 적어 둔
"binding != beneficial"이 실측으로 확정됐다. A 보고서의 관측(flagship 수치모델도 argmin이 전 밀도에서 115)과 일치한다.

### 2-2. 기전을 켜면 — 이득 영역이 생긴다 (기전 격리 실험)

`vsl_fd_two_branch`의 nominal 임계밀도는 삼각형 capacity 정합으로 `ρ_c_tb = 6900/4/120 = 14.375`를 썼다.

| 변형 | two_branch | capdrop ν | φ | 이득 셀 (K=6) | 이득 셀 (K=18) | 최대 이득 |
|---|---|---|---|---|---|---|
| a 현행 | — | — | 1.0 | 0 | 0 | — |
| b tb | ON | — | 1.0 | **0** | **0** | — |
| c tb+capdrop | ON | ON | 1.0 | 5 (ρ 20–36) | 3 (ρ 32–45) | −0.093% |
| d tb+capdrop+φ | ON | ON | 0.9 | 6 (ρ 16–36) | 3 (ρ 16–20, 45) | **−1.098%** |
| e φ만 | — | — | 0.9 | 0 | 0 | — |
| f capdrop만 | — | ON | 1.0 | 0 | 0 | — |

스크립트 출력의 `best` 열을 읽는 법 — 동률일 때는 메뉴 열거 순서상 **가장 낮은** VSL이 표시된다(예: 변형 a, K=6, ρ=28에서 `best=90`).
`dJ_best`가 `+0.000e+00`이면 그것은 "VSL 90이 최적"이 아니라 **"90 이상이 전부 동률"** 이라는 뜻이다.
이 표시 규약 자체가 §1-3의 솔버 타이브레이크 병리와 같은 구조다.

핵심 인과 — **`vsl_fd_two_branch`가 마스터 스위치다.** 이것 없이는 `effective_rho_crit`이 VSL과 무관하므로
capacity drop(ν 전환·φ 송출제한) 임계가 VSL에 반응하지 않는다. 그래서 e/f(기전만 켜고 two_branch OFF)는 이득 0건이다.
반대로 two_branch만 켠 b도 이득 0건이다 — 회피할 drop 자체가 없기 때문이다. **둘 다 필요하다.**

변형 d, K=6(제어주기 1스텝)에서의 이득 프로파일

| ρ | best VSL | Δ vs 120 | rel% |
|---|---|---|---|
| 12 | 120 | +0.000e+00 | +0.0000% |
| 16 | 100 | −1.028e-01 | −0.8606% |
| 20 | **80** | −1.611e-01 | **−1.0515%** |
| 24 | 60 | −2.003e-01 | −1.0707% |
| 28 | 50 | −2.120e-01 | −0.9591% |
| 32 | 50 | −1.268e-02 | −0.0497% |
| 45 | 50 | +0.000e+00 | +0.0000% |

주목할 점 — 기전을 켜면 **현행 메뉴 `[80,100,120]` 안에서도 이득이 나온다**(ρ=16에서 100, ρ=20에서 80).
즉 메뉴 확장은 이득의 *필요조건이 아니다*. 다만 ρ≥24에서 최적값이 60/50이므로 메뉴 확장은 이득의 *크기* 를 키운다.

### 2-3. 그 영역이 운영 중 나타나는가

| 구간 | 실측 밀도 점유율(976점) |
|---|---|
| ρ ≤ 16.84 (VSL 100 구속) | 65.6% |
| ρ ≤ 25.84 (VSL 80 구속) | 92.7% |
| ρ ≤ 30 (= ρ_crit) | 97.0% |
| ρ > 30 | 3.0% |

변형 d의 이득 영역(ρ 16~32)은 실측 밀도의 약 30%를 덮는다. **운영 중 나타나는 영역이 맞다.**
다만 예측 이득은 프리웨이 링크 TTT 기준 최대 −1.1%이고, 이건 **내부 모델 안에서의 이득**이다.
내부 FD가 +35 km/h 편향돼 있으므로 VISSIM 실플랜트에서 같은 크기로 재현될 것이라는 근거는 없다.

---

## 3. 주범 순위

| 순위 | 원인 | 성격 | 단독으로 채널을 죽이는가 | 근거 |
|---|---|---|---|---|
| **1** | 이득 기전 전면 OFF (`vsl_fd_two_branch` 미정의 + capdrop OFF + φ=1.0) | 설정 | **예** — 메뉴·horizon·가격 무엇을 바꿔도 이득 0건 | §2-1, §2-2 |
| **2** | 타이브레이크 래칫 (`wu_faithful_follower.py:2816` strict `<` + 오름차순 열거) | 코드 버그 | 감도를 죽이진 않지만 **결정을 오염**시킨다. 근거 없이 VSL 80 고착 | §1-3 (C1) |
| **3** | FD 캘리브레이션 편향 (+35 km/h, envelope 적합) | 캘리브레이션 | 모델의 구속력과 페널티를 **양쪽 다 가짜로** 만든다 | §1-4 |
| **4** | `vsl_set` 바닥 80 | 설정 | 아니오 — 감도는 죽이지만 이득 부호는 못 바꾼다 | §2-1 |
| **5** | 예측-플랜트 vsl 배선 누락 (`local_freeway_plant.py:623`) | 코드 버그 | 현재는 no-op. 기전을 켜는 순간 발화 | §1-3 (C2) |
| 6 | `control_interval=60`(K_cf=6) 짧은 rollout | 설정 | 아니오 — 감도 크기만 약 30% 축소 | C 보고서 |
| 7 | 죽은 노브 3종 (`density_penalty=80`, `vsl_metanet_rollout` 런타임 패치, `vsl_activation_density_ratio`) | 설정 위생 | 아니오 — 다만 "이미 고쳤다"는 착시를 만든다 | §5 |
| **무죄** | **가격 스케일 (`g_vsl`)** | — | 아니오 | §4 |
| 무죄 | `freeway_buffer_segments=0`, `terminal_zero_gradient=False`, `ramp_capacity=1800`, metering 값 | — | 아니오 (SEG13 로컬 rollout에서 비트 동일) | C 보고서 |

### 가격 스케일은 왜 무죄인가

관측 `g_vsl ∈ [1e-6, 7e-5]`을 문턱 `5e-4`와 직접 비교한 것이 착시의 출처다. 가격이 결정을 뒤집으려면
`|g| · Δv`가 후보 간 TTT 차이를 넘어야 하므로, 비교 대상은 **`|ΔJ|/Δv`(뒤집기 문턱)** 다. 링크 전체 TTT 기준(K=18, 변형 a).

| ρ | J(100) − J(120) | 뒤집기 문턱 \|ΔJ/Δv\| [veh·h/(km/h)] | 관측 g 범위와 비교 |
|---|---|---|---|
| 12 | 1.0701 | 5.35e-02 | 가격이 760~53,000배 작다 |
| 20 | 0.1439 | 7.20e-03 | 100~7,200배 작다 |
| 28 | 0.0390 | 1.95e-03 | 28~1,950배 작다 |
| 36 | 0.0122 | 6.10e-04 | 8.7~610배 작다 |
| **45** | **0.0015** | **7.50e-05** | **관측 상한과 동급 — 가격이 실제로 뒤집는다** |

즉 `g_vsl`은 "너무 작은" 게 아니라 **물리 기울기에 비례해 작다**. D 보고서의 측정(`|g_ext/d_local|` 비가 VSL 1.03~1.78,
metering 1.01~1.09로 동일 급, 메뉴 한 칸 이동 시 price_term/own-spread = 0.46~0.51)과 정합한다.
혼잡에서 물리 기울기가 정확히 0이므로 가격도 0이 되는 것이 **정상 동작**이다.
**가격을 손대기 전에 감도를 살리는 것이 순서다.**

---

## 4. 보고서 간 모순 판정

| 쟁점 | A | B | C | D | 판정 |
|---|---|---|---|---|---|
| 혼잡 spread=0의 성격 | 물리 | 물리 | 물리 | 물리 | **전원 일치, 확인** |
| 메뉴 확장이 이득을 만드는가 | 아니오(암시) | 미검증 | **예(처방)** | 아니오(암시) | **C 반증** — 메뉴 50까지 확장해도 이득 0건(§2-1) |
| two_branch만 켜면 이득이 생기는가 | — | **예** | — | — | **부분 반증** — 균일·계단 상태에서는 0건. B의 이득은 램프 폭주 merge 병목 시나리오 한정이며, 재현된 일반 조건은 two_branch **+ drop 기전** 동시 필요(§2-2) |
| 가격 스케일이 원인인가 | 아니오 | 아니오 | 아니오(부수) | **아니오(정량 반증)** | **D 지지** — 뒤집기 문턱 표로 재확인(§3) |
| 타이브레이크가 VSL 80을 켠다 | — | **예** | — | — | **B 지지, 실솔버로 재현 + 래칫 궤적 추가 확인**(§1-3) |
| flagship 수치모델도 argmin=무VSL | **예** | — | — | 아니오(g_ext>0) | **모순 아님** — A는 국소 TTT argmin, D는 외부성 가격 `g_ext = g_i − d_local`. 국소적으로 손해여도 이웃 외부성은 반대 부호일 수 있다 |
| FD 편향 +33~38 km/h | **예** | — | — | — | **A 지지, 독립 재현**(bias +35.1, RMSE 36.4 → 재적합 RMSE 8.9) |
| 세그먼트 길이 불일치 | 예(0.795 vs 1.005) | 예 | — | — | **확인 + 출처 규명** — 0.795059는 캘리브레이션의 FW_E 0.58645와 FW_W 1.003668의 **산술평균**이다. 그런데 실측 CSV는 양 링크 모두 1.0037~1.0048이다. 즉 캘리브레이션의 FW_E 0.58645 자체가 실측과 어긋난다 |

---

## 5. 부수 확인 사항

- `density_penalty`는 `wu_faithful_follower.py`에서 참조 **0건**이다(소비처는 `distributed_coordinator.py`, `freeway_follower.py`, `auto_tuner.py`).
  2026-07-25 체인의 `density_penalty: 12 → 80` 조치는 flagship 경로에 닿지 않는다.
- `install_vsl_metanet_rollout_runtime_patch`(`vissim_stackelberg_adapter.py:334-467`)는 `dc.DistributedCoordinator`를 패치하는데,
  flagship은 `F1StackelbergWuMeteredController`(어댑터 L1142-1144)를 조립하므로 패치가 적용되지 않는다.
- `vsl_activation_density_ratio`는 선언만 있고 소비처가 없다(dead knob).
- VISSIM DSD 액추에이션 충실도 — `modi_eval_rw_control.inpx`의 분포 상한. DSD 50/60/70은 각각 58/68/78로 좁고,
  **DSD 80은 상한 110, DSD 100은 130, DSD 120은 155**다. 즉 현행 메뉴 상단은 이름값대로 집행되지 않으며,
  메뉴를 내리면 감도뿐 아니라 액추에이션 충실도도 함께 올라간다. 50/60/70 분포는 이미 네트워크에 존재해 inpx 수정이 필요 없다.

---

## 6. 처방

flagship 재현성 경계 — **`NumSim-mine/src/config/default.yaml`과 `work/run_job.sh`는 건드리지 않는다.**
아래 변경은 (i) real-world tuning JSON, (ii) real-world 캘리브레이션 JSON, (iii) **기본값이 현행 동작인 cfg 플래그로 감싼 코드 수정**에 한정한다.
수치모델은 `VSL_FD=1` 등 env로 기전을 켜므로 기본값 불변이면 비트 동일이 유지된다.

### P1. 타이브레이크 규약 정합 — 최우선, 저위험

| 항목 | 내용 |
|---|---|
| 변경 | `wu_faithful_follower.py`의 후보 갱신을 tie-aware로 바꾼다. 동률(`|cost − best_cost| ≤ ε`)이면 **무제어(=vsl_set 최대값)에 가까운 후보**를 유지한다. 단일 세그먼트 경로(L2816)와 zone 좌표하강 경로(L2850) **양쪽 모두** 같은 규약을 쓴다 |
| 게이팅 | `cfg.mpc.vsl_tie_prefer_no_control` (기본 False = 현행 동작). real-world tuning에서만 True |
| 검증 | (1) 플래그 OFF에서 `scripts/test_freeway_zone_followers.py` 전체 PASS(비트 동일). (2) 플래그 ON에서 `diagnose_vsl_channel_20260801.py tiebreak` 실행 시 flagship 궤적이 `120→120→…`으로 바뀌고 zone4와 일치. (3) 자유류 ρ=12에서 결정이 120으로 불변 |
| 비용 | 코드 ~15줄, 검증 30분 |
| 위험 | **낮음**. 다만 real-world 로그의 `vsl_active_steps`가 급감하므로 과거 런과의 VSL 통계 비교는 무효가 된다 — 이건 오염 제거이지 성능 저하가 아니다 |
| 왜 "무제어 우선"인가 | 모델이 무차별이라고 판단한 상태에서 VISSIM은 DSD를 실제로 집행한다. 실측 속도가 80을 넘는 시간이 17.8%이므로 근거 없는 감속은 **실플랜트에서만 비용**이 된다. 그리고 이는 metering 규약과 **모순되지 않고 오히려 같다** — `wu_faithful_follower.py:2560-2562` 주석이 "own-TTS는 보존식 때문에 방류에 근사-무차별인 레짐이 흔해서 tie-break가 결정적: 오름차순이면 최소 방류로 쏠려 전면 질식"이라며 내림차순(=전량 방류=무개입)을 선택한 이유를 명시한다. VSL도 동일하게 "동률이면 개입하지 않는다"로 통일하는 것이다. **즉 P1은 새 규약이 아니라 metering에 이미 적용된 규약을 VSL에 누락 없이 적용하는 것이다** |

### P2. 예측-플랜트 vsl 배선 수정 — 지금 하면 무비용

| 항목 | 내용 |
|---|---|
| 변경 | `local_freeway_plant.py:623` `select_anticipation_nu(rho, net)` → `select_anticipation_nu(rho, net, vsl_i)` |
| 검증 | `capacity_drop_anticipation=False`에서는 `effective_rho_crit`이 vsl을 무시하므로 **정의상 비트 동일**이다. `test_freeway_zone_followers.py` 전체 PASS로 확인 |
| 비용 | 1줄 |
| 위험 | **없음**(현행 설정에서 no-op). P3를 켜기 전에 반드시 선행해야 한다 — 안 고치면 follower만 이득을 못 보는 비정합이 된다 |

### P3. VSL 이득 기전 활성화 — real-world tuning 한정, 중위험

| 항목 | 내용 |
|---|---|
| 변경 | 새 tuning `real_world_modi_pstack_vslfd_20260801.json`(flagship_segvsl 상속)의 `config_overrides.network`에 `vsl_fd_two_branch=true`, `rho_crit_two_branch=14.375`(=6900/4/120), `capacity_drop_anticipation=true`를 넣는다. φ는 2단계로 미룬다 |
| 전제 | `NetworkConfig`에 `vsl_fd_two_branch: bool = False` / `rho_crit_two_branch: float = 0.0` 필드를 **추가해야 한다**. 경로 확인 결과 — `calibration_override`는 `calibration_to_config_overrides`(어댑터 L957~)의 **명시적 화이트리스트**를 통과하므로 새 키를 실을 수 없고, `config_overrides`는 `tuning_to_config_overrides`(L1017-1020)가 `deep_update`로 그대로 통과시킨다. 그러나 `ExperimentConfig.from_dict`가 `NetworkConfig(**raw["network"])`(state.py:689)로 생성하므로 **필드가 없으면 TypeError로 죽는다**. 기본값이 현행 동작과 같으므로 필드 추가만으로는 수치모델 비트 동일이 유지된다 |
| 검증 | (1) `diagnose_vsl_channel_20260801.py gain`에서 변형 c가 이득 셀 ≥3개. (2) **무제어 baseline TTT가 바뀐다는 점을 확인** — two_branch는 VSL이 아니라 FD 자체를 바꾸므로 ρ=32/K=18에서 J(120)이 61.98 → 66.44(**+7.2%**)로 이동한다. 따라서 A/B는 반드시 `two_branch ON` 안에서 `VSL 활성 vs VSL 고정 120`으로 잡아야 하고, `two_branch OFF` 런과 TTT를 직접 비교하면 안 된다. (3) VISSIM 단일 시드 스모크로 예측-실측 TTT 괴리가 커지지 않는지 확인 |
| 비용 | 필드 추가 + tuning 1개 + VISSIM 런 1회 |
| 위험 | **중**. two_branch는 real-world FD를 삼각형으로 바꾸는 큰 변경이고, VISSIM 실차량이 그렇게 반응한다는 검증이 없다. 예측모델만 이득을 보고 플랜트가 안 따라오면 현재보다 나빠진다. **먼저 P5(FD 재적합)를 하고 그 위에서 two_branch를 얹는 편이 방법론적으로 옳다** |

### P4. 메뉴·박스 정합 — P3와 묶어서만 의미 있음

| 항목 | 내용 |
|---|---|
| 변경 | `vsl_set`을 `[60, 80, 100, 120]`으로 확장(20 간격 유지). `seg13_vsl_box_kmh=20`을 그대로 두면 스텝당 1 rung 규약이 보존된다 |
| 왜 50/70/90을 넣지 않는가 | 간격이 10이 되면 box 20이 스텝당 **2 rung**을 허용해 이동속도 규약이 바뀐다(flagship json notes가 경고한 함정). 굳이 넣으려면 `seg13_vsl_box_kmh=10`을 함께 내려야 하고, 그러면 VSL이 혼잡에 반응하는 속도가 절반이 된다 |
| 검증 | inpx에 DSD 60이 이미 존재(범위 58 이하)하므로 네트워크 수정 불필요. `run_real_world_stackelberg_controller.vbs:650`이 `CLng(speedKph)`로 그대로 매핑 |
| 비용 | tuning 1줄 |
| 위험 | **낮음**. 단 P3 없이 P4만 하면 **손해만 커진다**(§2-1 표에서 J(60) > J(120)) |

### P5. FD 재적합 — 별도 작업 항목, 가장 큰 파급

| 항목 | 내용 |
|---|---|
| 변경 | `real_world_modi_control_v0_20260719.json`(또는 신규 v2 캘리브레이션)의 `v_free_kph`/`rho_crit_veh_km_lane`를 실측 FD 회귀로 재적합. 지수형 1차 적합 결과는 `v_free≈95.3, ρ_crit≈40.8, a≈1.0`(RMSE 8.9 vs 현행 36.4) |
| 주의 | `a`가 하한 1.0에 붙었고 적합 capacity 1431 veh/h/lane이 실측 최대 1813과 어긋난다. 실무적으로는 `no_control_fd_mfd_20260724_freeway_fd_binned.csv`의 binned 평균에 capacity 제약(관측 포락 ~6500 veh/h/링크)을 걸고 다시 적합해야 한다 |
| 트레이드오프 | 재적합하면 V(ρ)가 내려가 **VSL 구속 구간이 더 좁아진다**(VSL 80은 ρ≤7.1, VSL 100은 비구속). 즉 "편향 교정이 VSL 채널을 더 죽인다"는 A의 우려는 맞다. **그러나 동시에 가짜 페널티도 사라진다** — 현행 모델이 자유류에서 VSL 80에 물리던 −3~−15% TTT 손해가 실재하지 않는 값이기 때문이다. 순효과는 "VSL 메뉴가 60 이하가 아니면 의미 없다"로 정리된다 |
| 함정 | 재적합으로 `v_free < vsl_set 최대값(120)`이 되면, two_branch에서 VSL=100이 **v_free보다 빠른 자유류 branch**를 만들어 물리적으로 무의미한 이득이 생긴다(실측 확인 — fit FD + two_branch에서 ρ=10/15의 −2.07%/−2.19% 이득은 전부 이 아티팩트다). P5와 P3를 같이 할 경우 **무제어 앵커를 v_free와 일치**시켜야 한다 |
| 비용 | 재적합 + metering 포함 전체 baseline 재수립 |
| 위험 | **높음**(metering·leader 예산·N_P_crit까지 전부 영향). VSL 단독 이슈로 착수하면 안 되고 별도 작업으로 세워야 한다 |

### P6. 설정 위생 — 즉시, 무위험

- real-world tuning에서 `density_penalty: 80`을 제거하거나 "SEG13 경로 미사용"이라는 주석을 단다.
- `install_vsl_metanet_rollout_runtime_patch`가 flagship 경로에서 무효임을 어댑터 진단(`vsl_metanet_rollout_patch_enabled`)과 함께 명시한다.
- `vsl_activation_density_ratio`를 dead knob으로 표시한다.
- `freeway_segment_length_km=0.795059`와 실측 1.0037~1.0048 km의 21~26% 불일치를 별도 티켓으로 올린다.
  출처는 확인됐다 — 어댑터 `calibration_to_config_overrides`가 `freeway_segment_length_profile_km`의 **전 링크 평균**
  (`sum(lengths)/len(lengths)`)을 단일 스칼라로 넣는다. 캘리브레이션의 FW_E 0.58645와 FW_W 1.003668의 평균이 정확히 0.795059다.
  문제는 평균화 자체보다 **캘리브레이션의 FW_E 0.58645가 실측 1.0048과 어긋난다**는 점이다.
  TTT 절대값과 밀도→차량수 환산에 직접 영향하므로 **VSL이 아니라 metering 평가에도 영향한다**.

---

## 7. zone4 작업을 어떻게 할 것인가

### 7-1. 지금 상태로 4-zone A/B를 돌리면 안 되는 이유

flagship(단일 세그먼트 에이전트)과 zone4(다중 세그먼트 좌표하강)는 **동률 처리 규약이 서로 다르다**.

| 경로 | 초기값 | 동률 시 결과 |
|---|---|---|
| 단일 세그먼트 (`L2813-2825`) | `best_cost = inf` → 첫 후보가 무조건 채택 | **후보 중 최저 VSL**(=박스 하단) |
| zone 좌표하강 (`L2833-2836`) | `_cur_v` = 앵커(previous/snapshot) | **앵커 유지**(= previous VSL) |

VSL은 운영 밀도의 상당 부분(ρ≥16.84 → 65.6%의 여집합인 34.4%에서 100/120 동률, ρ≥25.84 → 7.3%에서 전 rung 동률)에서
동률이므로, **A/B의 VSL 차이는 zone 구조의 효과가 아니라 타이브레이크 규약 차이**다. §1-3의 표가 그것을 정확히 보여준다
— ρ=35에서 flagship은 80까지 내려가고 zone4는 120에 머문다. 이 상태로 얻은 TTT 차이는 zone 효과로 해석할 수 없다.

### 7-2. 권고 — 3단계

**1단계 (필수, 선행).** P1(타이브레이크 정합) + P2(배선)를 먼저 넣는다. 두 경로가 같은 규약을 쓰게 만들고,
`diagnose_vsl_channel_20260801.py tiebreak`로 flagship 궤적과 zone4 궤적이 일치하는지 확인한다.
이것만으로 A/B의 교란 변수 하나가 제거된다.

**2단계 (본 평가).** VSL 채널을 **의도적으로 고정**하고 4-zone A/B를 **metering 채널로** 평가한다.
구체적으로 real-world zone4 tuning과 그 대조군 모두에 `vsl_set: [120.0]`(또는 VSL 고정 플래그)을 걸어
VSL을 상수로 만들고, 차이가 오직 zone 분할(=metering 조정 범위와 소유 관계)에서만 오도록 한다.

- 근거 — 현행 설정에서 VSL은 이득 상태가 0건이고(§2-1), 결정의 대부분이 타이브레이크 산물이며(§1-3),
  내부 FD 편향 때문에 모델이 보는 VSL 효과 자체가 실재를 반영하지 않는다(§1-4). 이런 레버를 A/B에 섞으면
  **zone 효과에 노이즈만 더한다**.
- 이 구성에서 4-zone A/B는 **의미가 있다**. zone 분할이 실제로 바꾸는 것은 (a) ramp metering 소유·조정 단위,
  (b) 세그먼트 간 결합을 zone 내부에서 명시적으로 푸는지 여부이고, 이 둘은 VSL과 무관하게 살아 있는 채널이다.
  metering 가격은 §3에서 확인했듯 `|g_ext·Δ| / own-spread ≈ 1.0`으로 정상 작동한다.

**3단계 (별도 트랙).** VSL을 살리고 싶으면 P5(FD 재적합) → P3(two_branch + capdrop) → P4(메뉴 60 추가) 순서로
**zone4 A/B와 분리된 트랙**에서 진행한다. 각 단계마다 `diagnose_vsl_channel_20260801.py gain`으로 이득 셀이 생기는지
확인하고, VISSIM 스모크로 예측-실측 괴리를 확인한 뒤에 다음 단계로 간다. 순서를 지키지 않으면
(예: P5 없이 P3만) 편향된 FD 위에 새 물리를 얹는 셈이라 결과 해석이 불가능해진다.

---

## 8. 남은 미검증 항목

- 본 진단은 합성 상태(균일밀도, 4/4 계단)와 `_make_solver_inputs`의 램프 수요 기반이다. 실제 프로덕션 런의
  `control_timeseries.csv` / 세그먼트 밀도 시계열이 `outputs/` 아래에 남아 있지 않아 실상태 궤적으로 재검증하지 못했다.
  다음 real-world 런에서 반드시 산출물을 보존해야 한다.
- B 보고서가 two_branch 단독으로 이득을 봤다는 merge 병목 시나리오(ρ=18 + 램프 1800 vph)는 본 스윕의 상태 집합에 없다.
  two_branch 단독 이득이 **램프 폭주 상태에 한정되는지** 별도 확인이 필요하다. 다만 결론(기전 없이는 이득 없음)은 바뀌지 않는다.
- 리더가 붙은 end-to-end 결정 로그로 §3의 뒤집기 문턱 표를 한 번 더 대조하면 완결된다. 본 측정은 leader=None(가격 0)이다.
- P5 재적합의 `a` 하한 접촉과 capacity 불일치는 binned FD 기반 제약 적합으로 다시 풀어야 한다.

---

## 9. P1/P2 적용 결과 (2026-08-01)

§6의 **P1·P2만** 구현했다. P3~P6은 손대지 않았다(사용자 결정 대기).

### 9-1. 변경 내역

| 파일 | 변경 |
|---|---|
| `NumSim-mine/src/models/state.py` (`MPCConfig`) | `vsl_tie_prefer_no_control: bool = False` 필드 추가 |
| `NumSim-mine/src/controllers/wu_faithful_follower.py` | 모듈 수준 `_vsl_no_control_key` / `_vsl_candidate_better` 추가, `_solve_freeway_segment_agents` 안에 공용 `_accept()` 도입 후 후보 갱신 3곳(단일 세그먼트 열거 1곳 + zone 좌표하강 2곳)을 이걸로 통일 |
| `NumSim-mine/src/controllers/local_freeway_plant.py` | `freeway_substep_local`의 `select_anticipation_nu(rho, net)` → `select_anticipation_nu(rho, net, vsl_i)` (P2) |
| `VISSIM/evaluation/configs/real_world_modi_pstack_flagship_segvsl_20260801.json` | `config_overrides.mpc.vsl_tie_prefer_no_control=true` (자식 zone4가 상속) |
| `VISSIM/scripts/test_freeway_zone_followers.py` | 케이스 5개 추가(10~14) |

§6 P2가 지목한 줄번호(`local_freeway_plant.py:623`)는 실제로 **L304**였다. `grep`으로 재특정했다.
`metanet.py:680`(완충 체인)에도 vsl 없는 호출이 있으나 그 셀은 무제어(`vsl=v_free` 고정)라 P2 범위 밖으로 뒀다.

### 9-2. 규약 — 무엇을 "동률"로 보는가

```python
def _vsl_candidate_better(cost, best_cost, v_by_seg, best_v_by_seg, tie_prefer_no_control):
    if not tie_prefer_no_control:
        return cost < best_cost          # 기존 strict '<' 그대로
    if best_cost == float("inf"):
        return True
    eps = 1e-12 + 1e-12 * max(abs(cost), abs(best_cost))
    if cost < best_cost - eps:  return True
    if cost > best_cost + eps:  return False
    return _vsl_no_control_key(v_by_seg) > _vsl_no_control_key(best_v_by_seg) + 1e-9
```

- **무제어 근접도**는 소유 세그먼트 VSL의 **합**이다. 좌표하강은 한 번에 한 세그먼트만 바꾸므로
  합 비교가 "그 좌표에서 더 높은 VSL"과 정확히 일치하고, 단일 세그먼트에서는 정의상 VSL 값 자체와 같다
  — **두 경로가 같은 규약을 쓴다**.
- **동률이면서 근접도도 같으면 기각**한다. 따라서 먼저 열거된 후보가 남고, `m_list`가 내림차순(전량 방류 우선)
  이므로 **metering 축의 무개입 우선 규약이 그대로 보존**된다. 새 규약이 아니라 `wu_faithful_follower.py`
  m_list 구성 주석("own-TTS는 보존식 때문에 방류에 근사-무차별인 레짐이 흔해서 tie-break가 결정적:
  오름차순이면 최소 방류로 쏠려 전면 질식")이 metering에 이미 적용한 규약을 VSL 축에 맞춘 것이다.
- **ε 근거.** 비구속 레짐의 동률은 원리상 **비트 동일**이다 — `V_eff = min(V(ρ), VSL)`이 두 후보에서 같은
  `V(ρ)`를 돌려주면 궤적 자체가 같아 cost 차이가 정확히 0이다. 따라서 ε=0으로도 충분하고, 상대 1e-12 +
  절대 1e-12는 합산 순서 차이에서 오는 마지막 자리 반올림만 흡수하는 여유다. 상한 근거는 §1-1 —
  본 진단이 측정한 **진짜** spread 중 가장 작은 것이 ρ=45의 (96.4786−96.4737)/96.47 ≈ **5e-5 상대**이므로
  1e-12는 그보다 7자리 아래다. 실재하는 물리 감도를 삼킬 수 없다. 절대항은 가격항 상쇄로 cost가 0 근처일 때
  상대 허용오차가 붕괴하는 것을 막는 방어이며 own-TTS 단위(veh·h)에서 무의미한 크기다.
- 동률 채택 시 앵커는 `best_cost = min(best_cost, cost)`로 유지한다. 채택 후보의 비용을 그대로 앵커로 쓰면
  ε 동률 채택이 연쇄될 때 앵커가 계속 위로 밀려 순서 의존이 생긴다.

### 9-3. 래칫 해소 실측 (`diagnose_vsl_channel_20260801.py tiebreak`)

**다단계 궤적 (ρ=35 고정, previous=직전 결정, seg3)**

| 경로 | 전 (플래그 OFF = 수정 전) | 후 (플래그 ON) |
|---|---|---|
| flagship(단일 세그먼트) | `120 → 100 → 80 → 80 → 80 → 80` | `120 → 120 → 120 → 120 → 120 → 120` |
| zone4(좌표하강) | `120 → 120 → 120 → 120 → 120 → 120` | `120 → 120 → 120 → 120 → 120 → 120` |

**단일 스텝 결정 — 두 경로 일치 여부 (ρ × previous 15셀)**

| | 전 | 후 |
|---|---|---|
| flagship == zone4 인 셀 | **4 / 15** | **15 / 15** |
| flagship이 무제어(120) 미만을 고른 셀 | 13 / 15 | 5 / 15 (전부 previous=80 행 — 박스 20 때문에 한 스텝에 100까지만 올라간다. 다음 스텝에 120) |

불일치했던 대표 셀(전 → 후)

| ρ | previous | flagship 전 | zone4 전 | 양쪽 후 |
|---|---|---|---|---|
| 20 | 120 | `[120,100,100,100,120,100,100,100]` | `[120]*8` | `[120]*8` |
| 28 | 100 | `[120,80,80,80,100,80,80,80]` | `[120,120,120,120,100,100,100,100]` | `[120]*8` |
| 35 | 100 | `[120,80,80,80,100,80,80,80]` | `[120,120,100,100,100,100,100,100]` | `[120]*8` |
| 45 | 80 | `[100,80,80,80,80,80,80,80]` | `[100,100,80,80,80,80,80,80]` | `[100]*8` |

**자유류(ρ=12)는 불변** — 전·후 모두 previous 120→`[120]*8`, 100→`[120]*8`, 80→`[100]*8`.
이 구간은 메뉴 전 rung이 구속하고 J(120) < J(100) < J(80)로 엄격 우열이 있어(§1-1, spread +3.51%)
동률 판정에 걸리지 않는다. 즉 ε가 물리 감도를 삼키지 않았다.

**비용** — zone 좌표하강은 채택이 늘어 sweep이 한 번 더 돌므로 evals가 올라간다(ρ=35/prev=100에서 206 → 234, +13.6%).
단일 세그먼트 경로는 evals 불변(32/48/32).

### 9-4. 플래그 OFF 비트 동일 확인

수정 **전** 코드로 실측한 결정을 골든으로 박아 두고 플래그 OFF에서 재현되는지 확인했다.

- 단일 세그먼트 경로 6셀(ρ 12/35 × previous 120/100/80): VSL·metering·evals 전부 일치. 래칫 궤적
  `[120,100,80,80,80,80]`도 그대로 재현(래칫은 버그지만 플래그 OFF에서는 **보존돼야 하는** 기존 거동이다).
- zone 좌표하강 경로 15셀: VSL·evals 전부 일치.
- OFF 분기는 `cost < best_cost` + `best_cost = cost` — 수정 전 표현식 그 자체다.
- `real_world_modi_pstack_flagship_20260731.json`(부모 flagship)에는 플래그를 넣지 않았다. `default.yaml`,
  `work/run_job.sh` 미변경.

### 9-5. 테스트

`scripts/test_freeway_zone_followers.py`에 케이스 5개 추가.

| # | 이름 | 내용 |
|---|---|---|
| 10 | `vsl_tie_flag_off_regression` | 플래그 OFF에서 수정 전 골든(VSL/metering/evals) + 래칫 궤적 재현 |
| 11 | `vsl_tie_flag_on_no_ratchet` | 플래그 ON, ρ=35 다단계에서 래칫 소멸·무제어 고정(flagship·zone4 양쪽) |
| 12 | `vsl_tie_free_flow_invariant` | 플래그 ON/OFF에서 ρ=12 결정 동일 + 상향(100) 선택으로 감도 생존 양성 확인 |
| 13 | `vsl_tie_path_parity` | ρ×previous 12셀에서 단일 세그먼트 경로 == zone 경로(ON). OFF에서는 **달라야 한다**는 음성 대조 포함 |
| 14 | `prediction_plant_vsl_wiring` | `select_anticipation_nu` 호출 인자를 관찰해 예측모델이 세그먼트 VSL을 넘기는지 직접 확인 + 현행 capdrop OFF에서 ν 불변(no-op) 확인 |

```
"C:/Users/alsrj/anaconda3/python.exe" scripts/test_freeway_zone_followers.py   # 14/14 PASS
"C:/Users/alsrj/anaconda3/python.exe" scripts/test_pstack_flagship_adapter.py  #  4/4  PASS
```

NumSim 쪽 관련 유닛(`test_capacity_drop` / `test_metanet_equations` / `test_wu_faithful_follower` /
`test_segment_local_plant` / `test_f1_follower` / `test_constraints`)은 **132 passed, 7 failed, 2 skipped**다.
그 7건은 **P1/P2와 무관한 선행 실패**임을 직접 확인했다 — 파일 백업 후 P1/P2 편집만 되돌려 같은 7건을
재실행했더니 **실패 목록과 assertion 값이 완전히 동일**했다(예: `fake_freeway_substep_local() got an
unexpected keyword argument 'buffer_bc'` = `buffer_bc` 파라미터 도입 이전의 낡은 test double,
`115.0 not found in [100.0]`, `324.13735 not less than 319.2366625`). 확인 후 편집을 복원하고
`test_freeway_zone_followers.py`를 다시 돌려 14/14 PASS를 재확인했다. 이 7건은 워킹트리에 미커밋 상태로
남아 있는 zone 작업(또는 그 이전)에서 온 것이므로 **별도 처리 항목**이다.

### 9-6. 해석 — P1은 이득을 만들지 않는다

P1 이후 이 합성 스윕에서 VSL은 어떤 밀도에서도 무제어 **아래로 내려가지 않는다**(previous=80에서 100이 나오는 셀은
박스 20의 상향 이동 도중이며 다음 스텝에 120에 도달한다). 이는 §2-1과 정합한다
— 현행 설정에서 VSL 이득 셀은 0건이고, 지금까지 로그에 찍히던 `vsl_active_steps`는 **최적화 근거 없이
타이브레이크가 만든 값**이었다. P1은 이득을 만드는 조치가 아니라 **근거 없는 개입을 제거**하는 조치다.
따라서 (i) 과거 런과의 VSL 활성 통계 비교는 무효이고, (ii) VSL 채널을 실제로 살리려면 §6의 P5 → P3 → P4
순서가 그대로 남아 있다. §7-2의 1단계(P1+P2 선행)는 이로써 완료됐고, 2단계(VSL 고정 + metering 채널로
zone4 A/B)로 진행할 수 있다.

### 9-7. 이번 작업에서 손대지 않은 것

- P3(two_branch + capdrop), P4(메뉴 확장), P5(FD 재적합), P6(설정 위생) — 전부 미착수.
- 비-SEG13(PFO) 경로의 VSL 후보 갱신(`wu_faithful_follower.py`의 `_solve_with` 계열 strict `<` 5곳)은
  건드리지 않았다. flagship은 SEG13 경로만 쓰지만, PFO baseline·SUP_PFO 감독자는 여전히 옛 규약이다.
  공정비교 관점에서 정합을 맞출지는 별도 결정 사항이다.
- `vsl_set` 바닥값·`seg13_vsl_box_kmh`·가격 스케일 미변경.
