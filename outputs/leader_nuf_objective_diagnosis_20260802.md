# 리더 목적함수 N_UF 진단 (임무 #14)

작성 2026-08-02. 대상 코드 `NumSim-mine/src/controllers/leader.py`(브랜치 `freeway-zone-followers`),
어댑터 `VISSIM/evaluation/controllers/vissim_stackelberg_adapter.py`(브랜치 `pstack-flagship-controller`).
실측 근거는 기준선 #8 런 `VISSIM/evaluation/runs/new_baseline_ab_20260801/` 과, 그 런의
`state_*.json` 을 그대로 입력으로 재현한 감도 스윕이다.

---

## 0. 결론 요약

**리더 목적함수에는 N_UF 항이 하나도 없다.** `Leader.objective_terms`(leader.py:860-960)는
`action` 을 `_density_penalty` 의 VSL 인자로만 쓰고 `action.N_UF_star` 를 단 한 번도 읽지 않는다.
N_UF 는 오직 follower rollout 이 만든 `predicted_states` 를 통해서만 간접적으로 목적값에 들어온다.

그 간접 경로가 이 망에서는 두 겹으로 끊겨 있다.

1. **집행 단절 (지배적)** — SEG13 follower 의 METER-BOX 회랑이 리더 예산을 통째로 흡수한다.
   `previous.ramp_metering` 이 4램프 모두 용량 1800 에 앉아 있어 회랑 하한이 링크당
   1500×2=3000, 총 6000 이 된다. 리더가 탐색할 수 있는 `N_UF_star_range` 상단은 5000 이므로
   **탐색 구간 [0, 5000] 전체가 회랑 하한 아래**다. 실측 스윕에서 N_UF ∈ [400, 6000] 의
   목적값이 소수점 12자리까지 완전히 동일했다. 리더 결정변수가 문자 그대로 무효(inert)다.
2. **가격 역전 (구조적)** — 회랑을 넓혀 리더에게 실제 권한을 돌려줘도 목적값은 N_UF 에 대해
   **단조 감소**한다(최소가 상한 코너). 램프 큐 terminal cost(`w_ramp_queue=6.0`)가 차량당
   무조건 부과되는 반면, freeway 는 `max(0, ρ−ρ_crit)` 힌지(`w_F=3.0`)로 **임계 초과분만**
   과금되기 때문이다. 임계 아래 본선에 차를 넣는 것은 목적함수 입장에서 **공짜 이득**이다.
   예측 밀도 초과가 613 veh·km·lane 인 혼잡 스텝에서도 그렇다.

부수적으로, 이 무효 상태가 P-Stack 을 PFO 로 밀어내는 되먹임을 만든다: 리더 목적 개선폭이
평탄(스텝당 0.007~0.014)이라 `stackelberg_wu_metered.py:2350-2357` 의 동률 tie-break 가
48 스텝 중 **40 스텝을 PFO incumbent 로 넘겼고**, 그 중 31 스텝은 전량 방류(7200)였다.
전량 방류가 다음 스텝의 `previous` 를 다시 용량에 고정시켜 회랑 하한 6000 을 유지한다 —
**자기강화 잠금(self-reinforcing lock)** 이다.

---

## 1. N_UF 관련 항 전수 조사

### 1.1 `objective_terms` 총합 식 (leader.py:925-932)

```
total = base
      + target_penalty          # w_P · max(0, N_P − N_P_crit) · T_c_h
      + mfd_storage_penalty     # mfd_storage_weight · (urban halfcap 초과) · T_c_h
      + boundary_in_queue_penalty
      + density_penalty         # w_F · Σ L·λ·max(0, ρ − ρ_crit(VSL)) · T_c_h
      + ramp_queue_penalty      # w_ramp_queue · Σ ramp_queue · T_c_h
```

`smooth`(leader.py:917)와 `conv`(leader.py:918)는 진단 전용이라 total 에 더해지지 않는다.

`objective_mode = follower_ttt` 이므로 `base = follower_objective`, 그리고
`accumulation_penalty_scale = T_c_h`(leader.py:874-876). 실측 `control_interval_sec = 60.0`
(state_002400.json) 이므로 **T_c_h = 1/60 = 0.0166667**.

### 1.2 항별 표 — 수식·단위·가중치·실효값

| # | 항 | 수식 | 단위 | cfg 키 | 설정 출처 | 실효 가중 | ×T_c_h 후 실효계수 | N_UF↑ 효과 |
|---|---|---|---|---|---|---|---|---|
| 1 | `leader_objective_base` | follower rollout TTT (freeway+urban, **램프 큐 포함**) | veh·h | `leader.objective_mode=follower_ttt` | default.yaml:264 | 1.0 | 1.0 | **≈0 (위치 불변)** |
| 2 | `leader_density_penalty` | `w_F·Σ_states Σ_seg L·λ_eff·max(0, ρ−ρ_crit(VSL))·T_c_h` | veh → 무차원 | `leader.w_F` | 튜닝 `config_overrides.leader` (`..._vsl_rollout_unmasked_20260725.json:19`) | **3.0** | 0.05 | **벌점 (+), 단 힌지 초과분만** |
| 3 | `leader_ramp_queue_penalty` | `w_ramp_queue·Σ_states Σ_ramp q_r·T_c_h` | veh → 무차원 | `leader.w_ramp_queue` | 튜닝 (`..._adapter_v1_response_calibrated_20260721.json:55`) | **6.0** | 0.1 | **보상 (−), 차량당 무조건** |
| 4 | `leader_target_penalty` | `w_P·max(0, N_P−N_P_crit)·T_c_h` | veh → 무차원 | `leader.w_P`, `leader.N_P_crit_veh` | default.yaml:265 / 어댑터:1524+캘리브레이션:993-995 | 1.0 / N_P_crit=(캘리브레이션값) | **0 (모드 비활성)** | 발화 안 함 |
| 5 | `leader_mfd_storage_penalty` | `mfd_storage_weight·Σ(큐−0.5·저장용량)⁺·T_c_h` | veh → 무차원 | `leader.mfd_storage_weight` | default.yaml:274 | 1.0 | 0.0167 | **0 (초과 없음)** |
| 6 | `leader_boundary_in_queue_penalty` | `w_boundary_in·Σ boundary_in 큐·T_c_h` | veh → 무차원 | `leader.w_boundary_in` | default.yaml:269 | **0.0** | 0 | 항 자체가 죽음 |
| 7 | `leader_smoothness_penalty` | — | — | (하드코딩 0) | leader.py:917 | 0.0 | 0 | 없음 |
| 8 | `leader_nonconvergence_penalty` | 진단 전용, total 미포함 | — | `leader.non_convergence_penalty` | default.yaml | 500.0 | (미가산) | 없음 |

실효계수는 실측으로 역산 확인했다 — 예: `action_002400.json`(scale 1.70)
`leader_ramp_queue_veh=16.34694`, `leader_ramp_queue_penalty=1.63469` → 정확히 0.1 배;
`leader_density_excess=631.0655`, `leader_density_penalty=31.5533`(action_000900) → 정확히 0.05 배.

### 1.3 무엇이 벌하고 무엇이 보상하는가

| 방향 | 항 | 실측 한계기울기 (scale 1.70, sim 900, N_UF 6000→7200) |
|---|---|---|
| **벌점** | density (#2) | Δ = **+0.0336** |
| **벌점** | base TTT (#1) | Δ = −0.0014 (오히려 미세 감소) |
| **보상** | ramp queue (#3) | Δ = **−0.2289** |
| — | 합계 | Δtotal = **−0.1966** (= 더 넣을수록 좋다) |

즉 **유입을 벌하는 유일한 항(density)은 유입을 보상하는 항(ramp queue)의 1/6.8 규모**다.
그리고 이 스텝은 예측 밀도 초과가 613 veh·km·lane 인 **가장 혼잡한 스텝**이다.

**구조적 비대칭 진단**: 램프 큐는 차량 1대당 `w_ramp_queue·T_c_h = 0.1` 이 **무조건** 붙는다.
본선은 `w_F·T_c_h·(ρ−ρ_crit)⁺·L·λ` 라 **임계를 넘긴 초과분에만** 붙는다. 본선이 임계 아래면
본선 차량 1대의 가격은 **0** 이다. 따라서 "램프에 세워두나 본선에 넣으나 같다"가 아니라
**"본선에 넣는 것이 대당 0.1 만큼 명백히 이득"** 이다.

---

## 2. 수치 감도 실측

### 2.1 방법

기준선 런의 `state_*.json` 을 어댑터 `build_config`/`traffic_state_from_vissim`/`demand_from_state`
로 그대로 복원하고(같은 튜닝 `real_world_modi_pstack_flagship_segvsl_fdrefit_20260802.json`,
같은 캘리브레이션 `real_world_modi_control_v2_fdrefit_20260802.json`),
`F1StackelbergWuMeteredController._evaluate_full_candidate` 를 N_UF 격자에 대해 직접 호출했다.
N_P_star 는 그 스텝에서 실제 커밋된 값으로 고정했다. VISSIM COM 은 사용하지 않았다
(백그라운드 고수요 탐침과 무간섭).

스크립트: `scratchpad/nuf_sweep.py`, `nuf_probe2.py`, `nuf_probe3.py`.

### 2.2 결과 — 현행 설정 (스윕 A)

| 케이스 | 스텝 | 상태 | N_UF ∈ [400, 6000] | N_UF=6600 | N_UF=7200 | 형태 |
|---|---|---|---|---|---|---|
| scale 1.35 혼잡 | sim 2220 | 예측 초과 30.7 | **179.714118 (전부 동일)** | 179.427215 | 179.404020 | 평탄 + 상한 코너 |
| scale 1.35 자유 | sim 2400 | 초과 0 | **171.521968 (전부 동일)** | 171.451741 | 171.425804 | 평탄 + 상한 코너 |
| scale 1.70 혼잡 | sim 900 | 초과 613 | **259.894417 (전부 동일)** | 259.706621 | 259.697854 | 평탄 + 상한 코너 |
| scale 1.70 자유 | sim 2400 | 초과 0 | **188.067191 (전부 동일)** | 188.051384 | 188.039900 | 평탄 + 상한 코너 |

**판정: 단조 감소도 내부 최적도 아니다. 탐색 구간의 83%(400~6000)에서 완전 평탄이고,
반응 구간([6000, 7200])에서는 단조 감소 — 최소는 항상 상한 코너.**

평탄의 원인은 follower 가 N_UF 를 집행하지 않기 때문이다. 같은 스윕에서 실현
`Σ ramp_metering` 을 함께 찍으면:

| N_UF* | 1000 | 2400 | 3600 | 5000 | 6000 | 6600 | 7200 |
|---|---|---|---|---|---|---|---|
| link budget FW_E (=ω·N_UF) | 500 | 1200 | 1800 | 2500 | 3000 | 3300 | 3600 |
| 실현 Σmeter | 6000 | 6000 | 6000 | 6000 | 6000 | 6600 | 7200 |

`wu_seg13_presplit_FW_E = 3600`, `wu_seg13_postsplit_FW_E = 3000` 이 모든 N_UF ≤ 6000 에서
동일하다. 3000 이 바로 회랑 하한이다.

### 2.3 회랑을 열면? (스윕 B: `seg13_meter_box_veh_h` 300 → 1800)

리더가 실제 권한을 갖게 한 뒤의 곡선 (scale 1.70).

| N_UF | Σmeter | total (sim 900, 혼잡) | total (sim 2400, 자유) |
|---|---|---|---|
| 1200 | 1200 | 272.401266 | 216.523264 |
| 2400 | 2400 | 265.295468 | 191.593920 |
| 3600 | 3600 | 264.317989 | 188.219251 |
| 4800 | 4200 | 263.961524 | 188.116942 |
| 6000 | 4950 | 262.088398 | 188.067191 |
| 7200 | 5940 | **259.889037 (최소)** | **188.039900 (최소)** |

**혼잡 스텝에서도 예측 밀도 초과가 296 → 586 으로 두 배가 되는데 목적값은 계속 내려간다.**
평탄이 풀려도 리더는 여전히 "전량 방류"를 고른다 — 문제는 집행 단절만이 아니라 가격 자체다.

---

## 3. 원인 분해

### (a) MFD / 보호네트워크 벌점이 발화하지 않는가 — **사실. 그리고 발화해도 무관.**

| 발화 조건 | 코드 | 현재 값 | 판정 |
|---|---|---|---|
| `mfd_penalty_mode ∈ {protected_exceed, combined}` 이어야 `w_P·(N_P−N_P_crit)⁺` 가 산다 | leader.py:884-885, 894-895 | `all_urban_halfcap` (default.yaml:272, 어댑터:1525) | **비활성** |
| 관측 `leader_mfd_penalty_mode_protected_exceed` | — | 98/98 스텝 **0.0** | 확인 |
| 관측 `leader_target_penalty` | — | 98/98 스텝 **0.0** | 확인 |
| `all_urban_halfcap`: 어떤 movement 큐 > 0.5·저장용량 또는 링크 점유 > 0.5·용량 | leader.py:838-858 | 관측 `leader_mfd_storage_excess_veh` 98/98 스텝 **0.0** | **미발화** |

두 모드 모두 죽어 있다. 단 더 중요한 점은 **설령 살아나도 방향이 반대**라는 것이다.
`N_P` 는 **urban 보호영역** 누적이고 `_urban_halfcap_excess` 도 urban 큐/링크만 본다
(leader.py:838-858). 램프를 방류해 urban 차량을 freeway 로 밀어내면 이 항은 **줄어든다**.
즉 MFD 계열은 구조적으로 freeway 과잉 유입을 벌할 수 없다.

### (b) freeway TTT 항이 유입 비용을 못 보는가 — **사실. 두 가지 이유가 겹친다.**

**b-1. TTT 는 방류에 위치 불변이다.** `metanet.py:715-718` 이 램프 큐와 origin 큐 차량을
freeway TTT 에 그대로 적분한다. 램프에서 본선으로 차를 옮기는 것은 TTT 회계상 net-0 이다.
실측: sim 900 에서 N_UF 6000→7200 의 base 변화는 **−0.0014** (총 기울기의 0.7%).
`state.py:583-590` 의 `w_ramp_queue` 주석이 이 평탄을 명시적으로 인정하고, 그것을 깨려고
**방류 방향으로** terminal cost 를 넣었다고 적어 놓았다 — 설계 의도 자체가 "더 넣어라"다.

**b-2. horizon 이 유입 결과를 담지 못한다.**
`horizon_steps=3`, `T_c=60 s` → 예측 지평 **180 s**
(실측 `leader_pred_horizon_ttt=64.4497` = `leader_pred_interval_ttt=21.4832 × 3`).
회랑 길이는 FW_E 10.773 km(runlog `FW_E_CHAIN ... length_m=10773.109`), 자유류 속도
119.505 km/h → 통과 시간 **≈325 s**. 램프에서 넣은 차가 하류 병목에 도달해 정체를 만들기
전에 지평이 끝난다.

**b-3. 애초에 임계를 거의 안 넘는다.** `bottleneck_segments_*.csv` 분석창(900~4500 s),
세그먼트 표본 976 개 기준 ρ > ρ_crit(16.354) 비율:

| 런 | max ρ | p99 | 평균 | 초과 표본 |
|---|---|---|---|---|
| no_control 1.35 | 23.02 | 17.64 | 9.19 | 16 (1.64%) |
| pstack 1.35 | 22.08 | 17.27 | 9.20 | 16 (1.64%) |
| stackelberg 1.35 | 20.79 | 17.63 | 9.09 | 11 (1.13%) |
| no_control 1.70 | 31.36 | 19.68 | 9.48 | 33 (3.38%) |
| pstack 1.70 | 31.36 | 19.86 | 9.47 | 28 (2.87%) |
| stackelberg 1.70 | 31.36 | 21.16 | 9.52 | 39 (4.00%) |

97~99% 의 시공간에서 본선 차량의 목적함수 가격은 **정확히 0** 이다.

### (c) 램프 큐 비용이 유입 감소 편익을 상쇄하는가 — **상쇄가 아니라 압도한다. 이것이 주범.**

`w_ramp_queue = 6.0`(튜닝) vs `w_F = 3.0`. 가중치 비만 2배인데, 적용 대상이
"모든 램프 대기차량" vs "임계 초과 밀도분" 이라 실효 비는 훨씬 크다.

**결정적 검증 (스윕 C·D, scale 1.70 sim 900, 회랑 개방 상태):**

| N_UF | A/B: 현행 (w_F=3, w_rq=6) | C: **w_rq=0** | D: **w_F=30** |
|---|---|---|---|
| 1200 | 272.401 | **235.583 (최소)** | **405.748 (최소)** |
| 2400 | 265.295 | 239.169 | 418.445 |
| 3600 | 264.318 | 239.509 | 419.871 |
| 4800 | 263.962 | 239.709 | 420.916 |
| 6000 | 262.088 | 243.326 | 448.410 |
| 7200 | **259.889 (최소)** | 253.007 | 523.616 |

`w_ramp_queue` 를 끄면 **부호가 완전히 뒤집혀** 최소가 하한으로 간다. `w_F` 를 10배로 올려도
같다. 즉 현재의 코너해는 이 두 가중치의 상대 스케일이 만든 것이지 물리가 만든 것이 아니다.

**무차별 가중치(실측 역산)** — sim 900 혼잡 상태에서 목적값이 N_UF 에 대해 비감소가 되는 조건:

| 구간 | Δbase | Δdens(w_F=3) | Δrq(w_rq=6) | Δtotal | 요구 w_rq | 요구 w_F |
|---|---|---|---|---|---|---|
| 1200→2400 | +1.385 | +2.200 | −10.691 | −7.106 | ≤ **2.01** | ≥ **12.69** |
| 6000→7200 | +1.081 | +8.601 | −11.881 | −2.199 | ≤ 4.89 | ≥ 3.77 |

전 구간을 덮으려면 `w_ramp_queue ≤ 2.0` 또는 `w_F ≥ 12.7`. 참고로 `w_ramp_queue = 2.0` 은
과거 튜닝 `tuning_turning_ratios_route_manifest_v2_mfd277_combined_guarded_20260715.json:10`
에서 실제로 쓰던 값이다 — **6.0 으로의 상향이 부호를 뒤집은 변경일 가능성이 높다.**

### (d) 가중치 스케일이 어긋나 유입 벌점이 다른 항에 묻히는가 — **사실. 3중으로.**

| 비교 | 규모 |
|---|---|
| `leader_objective_base` vs 벌점 합 (sim 2400, scale 1.70) | 186.43 vs 1.63 → 벌점이 **총목적의 0.87%** |
| 후보 간 목적 스프레드 `leader_candidate_objective_spread` | **0.0070** (총 188 대비 0.004%) |
| fallback guard 요구 개선폭 `required_gain = 0.05·|obj|` (stackelberg_mpc.py:1621) | **9.40** — 실현 개선폭 0.007 의 1300배 |

리더가 N_UF 로 만들 수 있는 목적값 차이(0.007~0.03)가 총목적(188)의 잡음 수준이라,
가드·tie-break·수치오차 어디에도 살아남지 못한다.

### (e) 추가 발견 — 집행 단절과 자기강화 잠금 (임무 후보 목록에 없던 원인)

이것이 **실측상 가장 큰 단일 원인**이다.

`wu_faithful_follower.py:3072-3178` SEG13 예산 사영:

```
budget = min(max(ω_F·N_UF*, 0), Σcap_link)                      # L3077
_rl_lo[r] = max(0, previous.ramp_metering[r] − 300)             # L3090  (METER-BOX)
target    = min(max(target, Σ_rl_lo), Σ_rl_hi)                  # L3110  ★ 예산이 양보
```

L3109 주석이 규약을 명시한다 — "**박스가 target 을 못 담으면 예산이 양보한다(박스=하드)**".

실측 상태: `previous.ramp_metering = {R_D_W:1800, R_F_W:1800, R_D_E:1800, R_F_E:1800}`
(= `ramp_capacity_veh_h` 전부 1800, 튜닝 `config_overrides.network.ramp_capacity_veh_h`).
→ 링크당 `Σ_rl_lo = 2×1500 = 3000`, 전체 6000.
→ `N_UF* ≤ 6000` 인 모든 명령이 **6000 으로 절삭**된다.
→ 그런데 `N_UF_star_range = [0.0, 5000.0]`(어댑터:1527)이라 리더는 6000 을 넘게 요청할 수도 없다.

**리더의 탐색 구간 전체가 follower 의 사각지대다.**

그리고 이 상태가 스스로를 유지한다:

| 관측 (pstack scale 1.70, 48 결정 스텝) | 값 |
|---|---|
| `leader_selected_intent_N_UF_star` = 5000 (탐색 상한) | 47/48 |
| `leader_pfo_incumbent_selected` = 1 | **40/48** |
| 그 중 커밋 Σmeter = 7200 (전량 방류) | **31** |
| `leader_fallback_guard_rejected_leader` = 1 | 40/48 |
| 기각 사유 `ttt_worse`/`terminal_severe`/`completed_severe` | 전부 0 |

기각은 가드 본체(stackelberg_mpc.py:1652)가 아니라
`stackelberg_wu_metered.py:2350-2357` 의 동률 tie-break 다:

```python
if float(best.objective) >= float(pfo_eval.objective) - 1.0e-9:
    best = pfo_eval           # 리더가 '엄격히' 낫지 않으면 PFO 로 넘김
```

리더 목적이 N_UF 에 평탄하니 리더는 PFO 를 이길 수 없다 → PFO 자율 방류(=용량 1800)가
커밋 → 다음 스텝 `previous` 가 다시 1800 → 회랑 하한 6000 유지 → 리더 무효.
**닫힌 고리다.**

---

## 4. flagship 수치모델과의 대조

`NumSim-mine/outputs/_adapt/*/P-STACK-WU-FAITHFUL-ALLPRICE-JOINT/control_timeseries.csv`
(같은 리더 목적함수, 8-seg 수치모델, 80 스텝).

| 런 | N_UF* 고유값 | 범위 | 평균 | 실현 Σmeter 범위 |
|---|---|---|---|---|
| t10h5w0.013_155 | 10 | 0 ~ 6000 | 5255 | 5644 ~ 6000 |
| t10h5w0.013_170 | 7 | 0 ~ 6000 | 4937 | 5085 ~ 6000 |
| t10h5w0.013_170inc | 17 | 0 ~ 6000 | 5183 | **3173** ~ 6000 |
| t10h5w0.013_190 | 11 | 0 ~ 5965 | 5164 | 4500 ~ 6000 |
| t12h3w0.013_170inc | 18 | 0 ~ 6000 | 5036 | 3335 ~ 6000 |

수치모델에서는 N_UF* 가 상한에 고착하지 않고 실현 metering 이 **정확히 추종한다**
(예: `N_UF*=5400 → Σmeter=5400.0`, ramp 별 1342.466/1357.534). 즉 **같은 목적함수인데
수치모델에서는 집행이 살아 있다.** 차이는 다음 세 가지다.

| 항목 | NumSim 8-seg | VISSIM real-world | 결과 |
|---|---|---|---|
| `ramp_capacity_veh_h` (램프당 / 총) | 1500 / **6000** (default.yaml:42-46) | 1800 / **7200** (튜닝 `config_overrides.network`) | — |
| `N_UF_star_range[1]` | **6000 = 총용량** (default.yaml:279-281) | **5000 ≠ 7200** (어댑터:1527) | VISSIM 상한이 "무제어"조차 표현 못 함 |
| METER-BOX / 램프 용량 비 | 300/1500 = **20%** | 300/1800 = **16.7%** | VISSIM 회랑이 상대적으로 더 좁음 |
| 정상상태 `previous` metering | 1342~1500 (**용량 미만**) | **1800 = 용량 고정** | VISSIM 회랑 하한이 6000 에 고정 |
| 회랑 하한 Σ | prev−300 ×4 ≈ 4168~4800 | **6000** | 리더 예산이 하한 아래로 못 감 |

즉 수치모델은 `N_UF_star_range` 상단 = 총 램프용량이라 "6000 = 무제어, 5400 = 10% 조임"이
자연스럽게 표현되고, 정상상태 metering 이 용량 아래에 앉아 회랑이 아래로 열려 있다.
VISSIM 은 (i) 상한이 총용량의 69%(5000/7200)라 의미가 뒤틀렸고, (ii) 무효화된 리더 때문에
metering 이 용량에 고정돼 회랑이 위로만 열려 있다.

**단, 목적함수의 가격 구조 자체는 수치모델에서도 동일하게 "더 넣어라"다.** 수치모델의
N_UF 평균이 4937~5255 (총용량 6000 의 82~88%)로 상단에 몰려 있는 것이 그 방증이다.
수치모델이 작동해 보인 것은 목적함수가 옳아서가 아니라, 집행 채널이 살아 있어서
incident 등 강한 물리 신호가 들어올 때(170inc: 고유값 17~49, Σmeter 3173까지) 반응할 수
있었기 때문이다.

---

## 5. 처방

### 5.1 real-world 튜닝 범위에서 고칠 수 있는 것 (NumSim 코드 무변경)

모두 `evaluation/configs/real_world_modi_pstack_flagship_segvsl_fdrefit_20260802.json`
(또는 그 위의 새 leaf) 의 `config_overrides` 로 끝난다.
**flagship 재현성 영향 없음** — `flagship_config_overrides()`(어댑터:1076-1126)는
`w_F`/`w_ramp_queue`/`N_UF_star_range`/`seg13_meter_box_veh_h` 를 건드리지 않고,
튜닝층이 flagship 층보다 뒤에 적용된다(어댑터:1543-1545). 수치모델 재현 런은
`NumSim-mine/work/run_job.sh` env 를 쓰므로 VISSIM 튜닝 JSON 과 무관하다.

| # | 변경 | 근거 | 검증 | 위험 |
|---|---|---|---|---|
| **P1** | `leader.N_UF_star_range = [0.0, 7200.0]` (= 총 램프용량) | 어댑터:1527 의 5000 은 구 램프용량(1414/316) 시절 값. 현행 총용량 7200 과 불일치. 상한이 "무제어"를 표현해야 수치모델과 의미가 같아진다 | `leader_selected_intent_N_UF_star` 가 5000 에서 풀리는지, `leader_nuf_bound_upper` = 7200 인지 | **낮음.** 단, 단독 적용 시 리더가 7200(전량 방류)을 고를 뿐이라 **효과 없음 → 반드시 P2/P3 와 함께** |
| **P2** | `leader.w_ramp_queue: 6.0 → 2.0` | §3(c) 무차별 역산: 전 구간 비감소 조건 `w_rq ≤ 2.01`. 2.0 은 과거 튜닝(`..._combined_guarded_20260715.json:10`) 실사용값 | 스윕 재실행 → 혼잡 스텝에서 목적 최소가 내부/하한으로 이동하는지. 이어서 scale 1.70 A/B 1런 | **중간.** 자유류에서 과잉 metering(램프 대기 증가) 회귀 가능 — §3(c) C열이 자유류에서도 최소를 1200 으로 밀었다. **P4 와 묶어야 안전** |
| **P3** | `leader.w_F: 3.0 → 12.0` | 같은 역산: `w_F ≥ 12.69` 로 혼잡 구간 부호 반전. **자유류에서는 힌지가 0 이라 부작용 0** (스윕 D 의 자유류 열이 B 와 완전 동일) | 스윕 D 재현 + `leader_density_penalty` 가 혼잡 스텝에서 base 의 10% 이상 차지하는지 | **낮음.** 상태의존적이라 자유류를 건드리지 않는다. **P2 보다 우선 권장** |
| **P4** | `mpc.seg13_meter_box_veh_h: 300 → 600`, 또는 `seg13_meter_box_up_veh_h: 150` (비대칭: 내림 넓게/올림 좁게) | §3(e). 회랑 하한이 6000 이라 리더가 아예 도달 못 한다. 하향 폭을 넓히면 리더 예산이 회랑에 들어온다. 비대칭 상향 억제는 "용량 고정" 잠금을 직접 끊는다 | `wu_seg13_postsplit_*` 가 `wu_seg13_budget_*` 를 따라가는지, `leader_response_N_UF_star_realization_residual` 이 0 에 붙는지 | **중간.** METER-BOX 는 2026-07-17 진동 억제 목적으로 도입됐다(wu_faithful_follower.py:2606-2617). 넓히면 metering 진동 재발 가능 → `ramp_metering` TV(total variation) 감시 필수 |
| **P5** | `leader.mfd_penalty_mode: "combined"` | leader.py:885-886. `protected_exceed` 를 되살려 `w_P·(N_P−N_P_crit)⁺` 가 살아나게 | `leader_target_penalty > 0` 스텝이 생기는지 | **낮음(효과도 낮음).** §3(a) 대로 방향이 유입 촉진 쪽이라 **본 문제 해결에 무의미**. 참고용 |

**권장 조합 (1차)**: **P3 + P4** → P1. `w_F` 상향은 상태의존적이라 자유류 회귀가 없고,
회랑 완화는 집행 단절을 직접 푼다. `w_ramp_queue` 하향(P2)은 자유류 회귀 위험이 있으므로
P3+P4 로 부호가 잡히는지 먼저 확인한 뒤 필요할 때만 적용한다.

**주의**: P1 단독, 또는 P4 단독은 **상황을 악화**시킬 수 있다. 목적함수가 여전히 단조 감소이므로
리더가 실제로 집행 가능한 "전량 방류" 를 더 잘 집행하게 될 뿐이다(§2.3 스윕 B 참조).
**가격 수정(P2/P3)이 반드시 선행하거나 동반해야 한다.**

### 5.2 NumSim 코드 변경이 필요한 것

| # | 변경 | 위치 | 근거 | 검증 | 위험 |
|---|---|---|---|---|---|
| **N1** | `objective_terms` 에 **명시적 N_UF 항** 추가 — 예: `w_UF · max(0, N_UF* − N_UF_ref)·T_c_h`, 또는 램프 큐/본선 잔류를 대칭 가격화 | `leader.py:925-932` | 현재 리더 목적함수는 자기 결정변수를 **읽지도 않는다**. Stackelberg 리더가 자기 액션을 목적에 반영하지 않는 것은 정식화 결함이다 | 단위 테스트: 같은 state·follower 응답에서 N_UF 만 바꿔 목적값이 변하는지 (`test_wu_faithful_follower.py:76` 의 prefilter 회귀 테스트와 동형) | **높음.** 목적함수 정의 변경 → flagship 8-seg 재현 런 전부 비트 불일치. **기본값 `w_UF=0` 으로 넣어 비트동일 보장 후 튜닝으로만 켜는 규약 필수** |
| **N2** | density 벌점을 힌지 → **soft/2차** 로: `max(0, ρ − θ·ρ_crit)` (θ≈0.7) 또는 `(ρ/ρ_crit)^p` | `leader.py:807-815` | §3(b-3) 대로 97~99% 표본이 임계 아래 → 힌지가 항상 0. FD 재적합으로 ρ_crit 가 30 → 16.354 로 내려왔지만 여전히 부족 | `leader_density_excess` 가 0 인 스텝 비율이 유의미하게 떨어지는지, 자유류 TTT 회귀가 없는지 | **높음.** 같은 이유로 기본값(θ=1.0, p=1)에서 비트동일 유지 필요 |
| **N3** | PFO 동률 tie-break 를 **엄격 부등호 + 마진** 으로 완화하거나 플래그화 | `stackelberg_wu_metered.py:2350-2357` | §3(e). 리더 개선폭이 잡음 수준이면 40/48 스텝을 PFO 가 가져간다 → 리더 가격 수정이 반영될 통로 자체가 막힌다 | `leader_pfo_incumbent_tie_break_selected` 비율이 떨어지는지, TTT 가 악화되지 않는지 | **중간~높음.** 이 tie-break 는 리더 회귀 방어 장치다. 끄면 저혼잡 회귀 위험 — **P3 로 리더 목적이 실제로 유의미해진 뒤에만** |
| **N4** | `w_boundary_in` 실사용 (현재 0.0) | `default.yaml:269` | boundary_in 큐가 최종 Total TTT 에 포함되는데 리더 목적에는 0 가중 | `leader_boundary_in_queue_penalty > 0` | 낮음(효과 방향은 본 문제와 직교) |

### 5.3 flagship 재현성 경계

- **깨지지 않는 범위**: `evaluation/configs/*.json` 의 `config_overrides` (P1~P5).
  `flagship_config_overrides()`(어댑터:1076-1126)가 고정하는 키
  (`horizon_steps`, `leader_candidate_count=49`, `max_nash_iter=10`, `leader_value_depth=3`,
  `seg13_meter_box_veh_h=300`, `leader_bias_sample_pow` 등)와 겹치는 것은 **P4 뿐**이다.
  P4 는 flagship 정식 키를 튜닝으로 덮으므로 "flagship 운영점 이식" 주장과 충돌한다 —
  적용 시 `context-notes` 에 **flagship 이탈**로 명시해야 한다.
- **깨지는 범위**: N1~N3 (NumSim `src/` 변경). `NumSim-mine/outputs/_adapt/*` 의 8-seg
  flagship 산출물과 비트 비교가 불가능해진다. 반드시 **기본값에서 비트동일**이 되도록
  플래그/가중치 0 기본으로 넣고, `work/run_job.sh` 재실행 1건으로 비트동일을 확인한 뒤
  튜닝으로만 켜는 순서를 지킬 것.

### 5.4 검증 절차 (제안)

1. 스윕 재실행 (`scratchpad/nuf_sweep.py`, COM 불필요) — P3+P4 적용 cfg 로
   4개 상태(1.35/1.70 × 혼잡/자유)에서 목적 최소가 내부 또는 하한으로 이동하는지.
   **합격 기준**: 혼잡 스텝에서 argmin N_UF < 상한, 자유 스텝에서 argmin ≥ 4800.
2. 통과하면 VISSIM A/B 2런 (pstack-flagship, scale 1.35/1.70, seed 13, warm900+eval3600).
   **합격 기준**: `leader_selected_intent_N_UF_star` 고유값 ≥ 5, `metering_active_steps > 0`,
   TTT 가 scale 1.35 에서 악화(+1.07%)를 벗어날 것.
   ★ 백그라운드 고수요 탐침(`no_control_highdemand_20260802`)과 **다른 출력 디렉터리**를 쓰고,
   VISSIM 라이선스 충돌 시 대기·재시도할 것.
3. `ramp_metering` total variation 을 no-control 대비 감시 (P4 의 진동 재발 확인).

---

## 부록 A. 재현 명령

```
# 감도 스윕 (COM 불필요, 약 3분)
cd C:/Users/alsrj/Desktop/학술/찐찐막/Claude/NumSim-mine
C:/Users/alsrj/anaconda3/python.exe -u <scratchpad>/nuf_sweep.py <out.json>

# 집행 경로 추적 (wu_seg13_budget/presplit/postsplit)
C:/Users/alsrj/anaconda3/python.exe -u <scratchpad>/nuf_probe2.py

# 처방 A/B (METER-BOX·w_F·w_ramp_queue)
C:/Users/alsrj/anaconda3/python.exe -u <scratchpad>/nuf_probe3.py
```

## 부록 B. 핵심 인용

| 주장 | 근거 |
|---|---|
| 목적함수에 N_UF 항 없음 | `leader.py:860-960` — `action` 은 `_density_penalty(states, action)` (L910) 에서만 소비 |
| 램프 큐 항이 방류 유도 설계 | `state.py:583-590` 주석: "방류(N_UF↑)가 ramp를 배수해 penalty↓ → … flat을 깨고 방류 신호를 준다" |
| TTT 위치 불변 | `metanet.py:715-718` — `freeway_ttt += sum(state.ramp_queue.values()) * dt_h` |
| 박스가 예산을 이긴다 | `wu_faithful_follower.py:3108-3110` 주석: "METER-BOX: 박스가 target을 못 담으면 **예산이 양보한다**(박스=하드)" |
| 예산 사영식 | `wu_faithful_follower.py:3077` `budget = min(max(omega_f * n_uf_star, 0.0), cap_sum)` |
| PFO 동률 tie-break | `stackelberg_wu_metered.py:2352-2357` |
| 가드 요구 개선폭 | `stackelberg_mpc.py:1621` `required_gain = 0.05 * max(abs(fallback_obj), 1.0)` |
| N_UF 범위 5000 | `vissim_stackelberg_adapter.py:1527` |
| 램프 용량 1800×4 | 튜닝 체인 병합 `config_overrides.network.ramp_capacity_veh_h` |
| w_F=3.0 / w_ramp_queue=6.0 | `..._vsl_rollout_unmasked_20260725.json:19` / `..._adapter_v1_response_calibrated_20260721.json:55` |
