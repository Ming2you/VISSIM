---
name: vissim-has-ramps-drain-fallback
description: SC1001·SC1004 만 has_ramps 라 phased 국소항을 통째로 건너뛰고 drain(항등 0)으로 폴백 — 가격이 외부효과가 아닌 전역 한계값 전체가 되어 꼭짓점 래칫을 만든다
metadata:
  node_type: memory
  type: project
---

2026-09-04. **꼭짓점 래칫의 근본 원인.** 한 줄이다.

```python
# priced_wu_link_controller.py:299  _phase_refine_signal_setup
model = self._local_models.get(signal)
if model is None or model.has_ramps:
    return None            # -> local_cost 가 phase_shape_local_cost(drain) 로 폴백
```

`has_ramps` 신호는 **SC1001·SC1004 둘뿐**이다(17개 중, 실측). 그리고 그 둘이 정확히

- 현시가격 국소항이 **항등 0.000000** 인 신호 (다른 신호는 phased 라 곡률이 있다)
- 매 결정 `22.0 / 22.7 / 70.7 / 22.7` 꼭짓점으로 가는 신호
- b2(p1 스칼라) 가격과 현시가격이 **부호까지 어긋나는** 신호
  (SC1001 부호일치 5/31 · SC1004 15/30 · 나머지 11신호는 상관 0.84~0.98)

국소항이 0 이면 `g_i = (전역 ΔTTT)/δ` 가 되어 **외부효과가 아니라 전역 한계값 전체**다.
규약(docstring)이 막으려던 이중계상 그 자체이고, 그 부풀려진 선형항이 정련 목적함수를
지배해 상자 꼭짓점으로 민다. [[vissim-price-local-term-drain]] 이 "63.5% 현시에서 0" 이라고
적은 것의 **잔여분**이다 — 2026-09-04 정본에서 phased 로 옮겼는데 has_ramps 두 개만 남았다.

**왜 램프 신호를 뺐나**: 국소 모형이 램프 저수지 결합을 표현 못 해서다. 고치려면 국소
모형에 램프 항을 넣거나, 최소한 drain 대신 **0 이 아닌** 대체 곡률을 줘야 한다. 그냥
`has_ramps` 가드를 지우면 국소 모형이 램프를 무시한 값을 내므로 그것도 답이 아니다.

## 더 근본적인 것 — 가격 롤아웃은 팔로워를 다시 안 푼다

`evaluate_price_point`(rollout_endpoint.py:388-394) 는 `apply_action_schedule` + `_rollout`
둘뿐이다. 팔로워를 import 도 안 한다. 그래서 g_i 는 **다른 레버(미터링·VSL·offset·타 신호)를
전부 `previous` 에 고정한 편미분**이지, 팔로워 반응을 통과한 전미분이 아니다.
Stackelberg 리더는 팔로워 최선응답을 통과해 미분해야 하는데 지금은 plant 편미분이다.
"p1 스칼라냐 현시 벡터냐" 보다 상위의 문제다.

관련: [[vissim-phase-price-surrogate-leak]] [[vissim-price-rollout-budget]]
[[vissim-flat-local-cost-vertex]] [[vissim-price-local-term-drain]]
