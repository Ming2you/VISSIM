---
name: vissim-gne-coupling-is-live-price-bypasses-it
description: 도시→freeway 램프 결합(u_on)은 이미 살아 있고 녹색에 반응한다 — 고장은 현시가격 채점이 그 물리를 통째로 우회하는 것뿐이다
metadata:
  node_type: memory
  type: project
---

2026-09-04. **결합을 새로 만들 필요가 없다.** 세 번 틀린 끝에 실측으로 확정.

## 이미 있는 것 (전부 라이브, 실측 확인)

```
도시 -> freeway   coupling["u_on_{ramp}"] = estimate_onramp_reservoir_inflow(state, control, ...)
                  = min(대기+수요, green x 포화). movement 별로 먼저 제한 후 램프별 합산이라
                  **현시 분할 효과가 보존된다**(주석 Spec 3.3.1).
                  실측: SC1001 p3 22.7 -> 45.0 -> 70.7  =>  u_on_R_D_W 168.3 -> 209.3 -> 256.5
freeway -> 도시   rollout_local_tts_ramp_aware(..., freeway_congestion, ramp_metering_weight, ...)
                  램프 신호의 GNE 국소비용은 램프큐·off-ramp 저류·freeway 혼잡을 다 받는다.
Jacobi 갱신       스윕마다 predicted = _wu._coupling(state, control, demand) 재계산 후
                  under-relaxation 합성 + residual 수렴판정 (wu_faithful_follower.py:4377-4398)
```

**`whose_code.py` 가 이걸 놓친다.** `estimate_onramp_reservoir_inflow` 는 `WuDistributedController`
소속이라 "LIVE 0 · DEAD 2 / 다른 팔 코드"로 판정된다. 그런데 라이브 팔로워가
`self._wu` 로 **그 클래스의 인스턴스를 들고** `_coupling` 을 부른다. whose_code 는 클래스 단위라
**합성(composition)을 못 본다.** 클래스가 DEAD 여도 인스턴스가 살아 있을 수 있다.

## 유일한 고장

```python
# priced_wu_link_controller.py:299
if model is None or model.has_ramps:
    return None      # -> phase_shape_local_cost(drain) -> 항등 0
```

현시가격 채점(정련 + in_gne)만 위 물리를 **통째로 우회**한다. SC1001·SC1004 를 램프큐도
freeway 혼잡도 없는 모형으로 채점하고 0 을 돌려준다. 그러면 목적함수가 `0 + Σ가격·Δg` =
순수 선형이라 상자 꼭짓점이 항상 최적. 그리고 그 결과가 **제대로 결합된 GNE 해를 덮어쓴다.**
리포지토리 주석의 "GNE 가 최적화 -> 정련이 되돌림" 이 정확히 이것이다.

`in_gne` 가 진 이유(-728)도 이것이다 — 평평한 채점기를 스윕 **안**으로 넣으면 매 반복이
오염되어 결합이 오염된 균형으로 수렴한다. 정련(스윕 밖)보다 나쁜 게 당연하다.

## 고치는 법 — 물리를 새로 짜지 마라

`_phase_refine_signal_setup` 이 has_ramps 에서 None 대신 램프 인자
(`offramp_inflow` `offramp_occ0` `ramp_queue0` `reservoir_drain` `freeway_congestion`)를 담은
setup 을 만들고, 현시 국소비용이 `rollout_local_tts_phased` 대신 GNE 가 이미 쓰는
**`rollout_local_tts_ramp_aware`** 를 부르게 한다. 인자는 팔로워가 이미 다 모아 둔다
(wu_faithful_follower.py:798-870). 어댑터 패치 범위, vendor 무수정.

관련: [[vissim-has-ramps-drain-fallback]] [[vissim-arm-confusion-whose-code]]
[[vissim-phase-price-surrogate-leak]] [[vissim-onramp-coupling-promoted]]
