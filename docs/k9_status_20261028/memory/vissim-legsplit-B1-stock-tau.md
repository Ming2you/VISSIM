---
name: vissim-legsplit-B1-stock-tau
description: B(leg_split) 첫 실수 — W_out 점유 전체를 링크끝 재고로 보고 T_f_h(10 s)로 나눠 u_on 이 실측의 9~58배. B1 = 재고를 τ 로 펴서 1~7배. 잔여 과대는 경로결정 분율 vs 실측 방향 분포 불일치(B2 후보)
metadata:
  type: project
---

정본(per_lane 206.5) 상태 ctl_start900 t=2400·3600 에서 실측(링크평가 RM 커넥터 10480/10484/10646/10681 = W_out 발)과 맞댐:

```
                R_D_W   R_D_E   R_F_W   R_F_E     (vph)
실측(W_out발)     456     644     989     456
base(vendor)      258     258     423     397   0.4~0.9배 (on_ramp beta 35% 가 과소)
B                11746    5873    8846    8846   9~58배  ← 재고 64·73대 / 10 s
B1(τ, 1 km 폴백)  1506     753    1059    1059   1.1~3.3배 — 재고항 85%, 길이 폴백이 2배 부풀림
B1'(실제 길이, 40)  879     439     575     575   0.6~1.9배
B1''(60 km/h, req 제거) 980  490     734     734   D합 1.34·F합 1.02 (t=3600 1.49/1.40) — 잔여 = 방향분율(B2)
```

**Why:** `T_f_h` 가 10 s 라 재고를 지평으로 나누면 rate 가 폭주한다. vendor 판은 `min(재고, h·gf·cap)` 으로 용량에 묶고,
plant 의 boundary_out 블록도 exit_cap·T_u 로 묶는데 내 추정기와 주입 래퍼는 안 묶었다. 관측 점유는 링크 전체에 퍼진
이동 중 차량이라 "링크끝 도착"이 아니다(release buffer 는 관측 차량을 모른다).

**How to apply:** B1' 은 `_legsplit_wout_rate`(1/τ)로 substep 도착=min(재고, 재고/τ·T_u), 추정기 재고항=min(재고, 재고/τ·h).
길이·속도는 **parameters.json `runtime.network`**(`boundary_out_link_length_km` 31 1.9595 · 68 1.9902 km, `wout_travel_speed_km_h` 40) —
`network` 절은 NetworkConfig 생성자에 직결이라 새 키를 넣으면 전 빌드가 깨진다(2026-09-05 실수, 즉시 되돌림). config 키
`urban.ramp.leg_split_wout_speed_kmh` 가 있으면 우선. 분기 전 점유만 세면(38%/18%) 과소로 튀어 보류. **B2 후보 = 램프 분율을 실측(링크평가)
러닝평균으로**: 경로결정은 D 에서 W 0.5/E 0.25 인데 실측은 E 가 더 많고, F 는 1/3 씩인데 실측은 W 가 4배.
[[vissim-canon-20260905]] [[vissim-model-flat-where-plant-steep]]

**B1'' 근거 (2026-09-05 19:07):** 링크 31/68 은 관측 링크이고 정지 0 의 자유류, 평균속도 54~99 km/h(평균 ≈65). `(N/L)·v_obs × 램프몫`
이 실측 램프 유출과 맞는다(5표본 평균비 ≈1.0). 커넥터 위치(31: 412/735 m · 68: 117/352 m)는 정상상태 유량엔 무관 —
점유도 링크 전체를 쓰므로 (N/L)·v = 링크 유량(유량 보존). `req`(녹색 방류율)는 같은 유량의 다른 추정치라 더하면 이중계상이고
정본 용량(206.5/차로)에선 plant 의 1/4 이라 제거. u_on 은 이제 후보 녹색에 즉시 반응하지 않는다(τ ≥ 66 s 라 물리적으로도
10 s 안엔 못 반응) — 녹색 영향은 plant 롤아웃의 지연 도착으로만. **결정별 관측속도(local_observation.link_speeds_kph) 사용은
B2 후보**(`state.urban_link_speed_kph` 의 W_out 140 kph 는 τ 보정용 유효속도라 쓰면 안 된다).

**B 치명 결함 둘 (2026-09-05 19:1x, g2 직전 발견):**
1. `coupling.py:15` 가 `urban_substep` 을 **이름으로 import** → 전역 롤아웃(rollout_endpoint→run_coupled_interval)은 원본을
   불러 주입 래퍼가 한 번도 안 돌았다(`cp.urban_substep is uqm.urban_substep` False). 모듈 속성 패치는 **이름 import 한
   모듈마다** 다시 심어야 한다 — 런타임 설치가 `sys.modules` 전수로 원본을 가진 속성을 재바인딩(진단
   `leg_ramp_split_substep_rebound_modules`). 이름 import 하는 vendor 모듈: coupling · local_signal_plant · leader ·
   freeway_follower · distributed_coordinator · classical_hierarchical · inflow_outflow_allocation.
2. vendor boundary_out 블록의 램프 진입 상한 `min(공간, 미터방출)` 은 **빈 저수지 교착**(방출은 큐가 있어야 생김) — 그래서
   9-03 에 on_ramp movement 직접 주입이 필요했던 것. 자유 진출은 share×재고를 매 substep 다시 계산해 1,600 vph 로 재고
   전체를 빼간다. B 래퍼는 진입 상한을 공간·연결로 용량(ramp_capacity)으로, 자유/램프 인출을 τ 도착량 기준으로 정하고
   vendor 인출과의 차이를 저류로 되돌린다. 검증(정본 t=2400, coupling 경로): 구간1 주입 78.5 veh(≈1,900 vph), 점유 64→27→17→14.

**B vs B2 램프별 (2026-09-05 19:23, 정본 상태, u_on 모형/실측 · 결합 1구간 주입/실측):**
```
t=2400  B  2.1/0.8/0.7/1.6 · 주입 1.4/0.5/0.5/1.1      B2  1.1/1.5/1.1/0.8 · 주입 0.7/1.0/0.7/0.5
t=3600  B  3.6/0.7/0.8/4.8 · 주입 2.3/0.4/0.5/3.1      B2  1.8/1.4/1.2/2.4 · 주입 1.1/0.9/0.8/1.6
```
B2 + τ_i(램프 위치) 는 정상상태 율이 B2 와 동일(N·d_i/L ÷ d_i/v = N/L·v) — 시점만 바뀐다. **g2 = B2** 로 결정(드라이버 v4, g1 완주 직후 인계).
주입 총량이 실측의 0.7~0.8배인 건 정본 용량(206.5/차로)으로 모형의 W_out 유입이 plant 보다 작아 재고가 줄기 때문 → uni1800 단계 몫.

