---
name: vissim-green-max-78-wall
description: "GNE 후보 생성기가 신호별 green_max(101)를 못 읽고 전역 78 로 훑는다 — 주현시만, 정련이 기어 나온다"
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-24T22:38:39.093Z
---

`NetworkConfig.signal_green_max(signal)` 이 신호별 주현시 상한을 낸다 — SC107/108/109 는
3현시 141 예산이라 **101**, SC7 은 74, SC16 은 67(런 metadata `native_signal_green_max_*`).
docstring 자신이 못박아 뒀다: *"스칼라를 그대로 걸면 컨트롤러가 **고정계획을 재현조차
못 한다**"*(`vendor/NumSim-mine/src/models/state.py:504-522`).

**그런데 GNE 후보 생성기가 그것을 안 읽는다.**

```
wu_faithful_follower.py:744   np.linspace(net.green_min, net.green_max, 13)   <- 전역 78
                    :751      clamp_primary_green(net, raw)                    <- signal 인자 없음
relaxed_quantization.py:138   total = net.effective_green_total (138 전역)
                    :140      gmax  = net.green_max (78 전역)                  <- 함수에 signal 인자 자체가 없다
```

읽는 쪽은 둘뿐이다 — `state.py:1539 distribute_phase_green`(나머지 현시 사영)과
`priced_wu_link_controller.py:310`(정련의 교환 후보).

**실측(sc7native 37결정).** 벽은 **주현시에만** 걸린다:

```
SC108_p1   정련전 최대 = 정확히 78.00   ->   커밋 98.00   (신호 상한 101)
SC107_p3   정련전 100.49  안 걸림       p1 이 죽어 주현시가 아니다
SC109_p3   정련전  96.50  안 걸림       같은 이유
```

**Why:** GNE 가 답이 있는 영역 **밖**을 훑고, 정련이 6초 걸음으로 기어 나오는 데
라운드를 쓴다(`refine_rounds: 12`). [[vissim-why-control-loses]] 의 "고정계획을 재현
못 한다" 축과 같은 뿌리다. 그리고 [[vissim-price-local-term-drain]] 과 **정확히 같은
실패 양식** — 신호별 값을 심어 놓고 소비처 일부만 읽는 것. 이게 세 번째 사례다
(첫째: movement 용량 맵이 perimeter 에 안 닿음, 2026-08-24 수정).

**How to apply:** 최소 수정은 `_urban_green_candidates` 와 `repair_green_phases` 에
signal 을 흘려 주는 것인데 `repair_green_phases` 는 서명에 signal 이 없어 vendor 를
건드려야 한다. 어댑터 사본에서 `_urban_green_candidates` 를 재정의하는 쪽이 vendor 를
피한다 — 그 함수는 부모 프로세스에서만 돌지 확인이 필요하다(가격 워커는 spawn 이다,
[[vissim-price-local-term-drain]] 의 워커 경계 절 참조).
