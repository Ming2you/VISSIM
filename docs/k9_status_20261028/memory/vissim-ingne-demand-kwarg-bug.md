---
name: vissim-ingne-demand-kwarg-bug
description: in_gne 벡터 탐색이 demand 를 kwargs 로만 읽는데 호출부는 위치로 넘긴다 — 채점기가 17신호 전부 drain(항등 0)으로 떨어져 전 신호가 꼭짓점으로 간다. in_gne 두 팔이 진 진짜 이유
metadata:
  node_type: memory
  type: project
---

2026-09-04. **`phase_price.in_gne` 를 켠 팔이 두 번 진 원인은 in_gne 설계가 아니라 인자 전달 버그다.**

```python
# priced_wu_link_controller.py:599-608 (LinkAgentWuFollower._solve_urban_agent_local override)
previous = kwargs.get("previous")
if previous is None:
    previous = args[5] if len(args) > 5 else None    # <- previous 는 위치 폴백이 있다
...
demand = kwargs.get("demand")                         # <- demand 는 없다
ctx = self._phase_refine_context(state, previous, demand)
setup = self._phase_refine_signal_setup(signal, state, ctx) if ctx else None
```

호출부 5곳이 전부 **위치**로 넘긴다 (`wu_faithful_follower.py:4340` 등):

```python
self._solve_urban_agent_local(
    signal, state, coupling, arr_movement, s_eff_frozen,
    reservoir_drain, freeway_congestion, snapshot, leader,
    lam_fixed, forecast_arrivals, horizon_h, demand,   # 13번째 위치인자 = args[10]
    committed_prev=previous)
```

→ `kwargs.get("demand")` 는 **항상 None** → `_phase_refine_context` 가 `if demand is None: return None`
→ **17신호 전부 setup=None** → 채점이 `phase_shape_local_cost`(도착 없는 배수 모형, 항등 0)
→ 목적함수 `0 + w·Σ price·Δg` = **순수 선형** → 상자 꼭짓점이 항상 최적 → 매 결정 trust 폭만큼 걸어간다.

## 실측 — 깊이에 비례해 나빠진다

```
ctl_start900 (in_gne 꺼짐)          7829.0
arm_ingne900_lcd1000  rounds 2      8557.4   +728   (14.4 sigma)
arm_ramplocal_ingne900 rounds 12   10579.0  +2750   (54.2 sigma)
```

`in_gne_rounds` 를 지정 안 하면 어댑터가 `refine_rounds`(12)를 물려준다 — 6배 깊게 걸어가서 4배 더 졌다.

**"돌았다" 진단은 참이라 안 잡힌다.** `wu_phase_price_in_gne_signals = 17` · `errors = 0` 이 정상으로
보인다. 잡아낸 것은 `phase_local_ramp_scored = 10` 이 정확히
(SC1001 4현시 + SC1004 4현시 + base 2) = **가격 생성부 몫뿐**이라는 계수였다.
in_gne 에서는 램프 채점이 0회였다. 채점기가 무엇을 썼는지는 진단에 없다.

## 수선

`install_in_gne_demand_fix`(어댑터). `_solve_urban_agent_local` 을 감싸 **11번째 이후 위치인자를
이름인자로 정규화**한다(demand · candidates_override · committed_prev). 앞 10개는 위치로 둔다 —
상류가 `args[5]`(previous)를 위치로 읽으므로 자리를 흔들면 안 된다.
`phase_price.in_gne` 가 꺼져 있으면 no-op = 비트 동일. vendor 무수정.

검증: in_gne 경로를 위치인자로 호출하면 SC1(비램프)·SC1001(램프) 둘 다 `ctx=True setup=True`.
수정 전에는 둘 다 None 이었다.

## 교훈

**`*args, **kwargs` 로 상류 메서드를 오버라이드할 때 위치 폴백을 하나만 쓰면 나머지는 조용히 죽는다.**
같은 함수 안에서 `previous` 는 폴백이 있고 `demand` 는 없었다. 진단이 "켜졌다·돌았다"까지만
말하고 "무엇으로 채점했는가"를 안 말하면 이런 건 폐루프 TTT 로만 드러난다.

관련: [[vissim-has-ramps-drain-fallback]] [[vissim-gate-outside-config-is-dead]]
[[vissim-phase-price-surrogate-leak]]

## 수정 후 실측 (2026-09-04, 같은 망·같은 시드)

```
ctl_start900 (in_gne 꺼짐)                    7829.0
arm_ramplocal_ingne900  (demand 버그)        10579.0   +2750
arm_ramplocal_ingne900b (demand 수정)         9268.4   +1439   <- 버그 수정이 -1310 회수
```

수정이 발화한 증거: `in_gne_demand_fix_normalized = 289`/결정 ·
`phase_local_ramp_scored` **10 -> 242** · `phase_local_ramp_setup_built` 2 -> 30.
꼭짓점 지표(하한 20~23초 부착)도 47.0% -> **33.7%** 로 기준(35.4%)보다 좋아졌다.
즉 **병리는 사라졌다.** 남은 +1439 는 다른 원인이다 — 아래.

## 남은 손실은 램프 미터링이다 (녹색이 아니다)

```
레버별 기준 대비 L1 (31결정)   ramp_metering 82,510  >>  green 18,221 > vsl 220 > offsets 0
평균 미터율   기준 합 6049  ->  수정판 합 3573        41% 더 조인다
leader_selected_N_UF_star  6048.6 -> 3573.0
```

그런데 **고속도로는 멀쩡하다** — 재차 2281 -> 2263, 속도 42.2 -> 41.7.
손실은 전부 도시다: 도시 재차 3520.6 -> **4605.5**(+1085), 램프 53 -> 130.
즉 미터링으로 본선을 지키고 그 값을 도시 누적으로 냈고, 순손실이다.

가설: 패치 ②(`urban.ramp.local_queue_cap`, ramp_queue_max 0 -> 111/153)가
저수지를 "실재"하게 만들어 모델이 그걸 지키려 미터를 조인 것. 세 스위치가 따로 게이트돼
있으므로 **cap 단독 팔**로 분해 가능하다. 미검정.
