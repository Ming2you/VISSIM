---
name: vissim-price-local-term-drain
description: 현시 가격의 국소항이 도착 없는 배수 모형이라 63.5% 현시에서 0 → 가격이 외부효과가 아니라 전역 한계값 전체가 된다
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-24T21:58:47.304Z
---

현시 교환가격 규약은 `g_i = (전역 방향미분) − (국소 방향미분)` 이고, 상류 docstring 이
이유를 못박아 뒀다 — "국소분을 빼서 팔로워가 이미 보는 몫을 제거한다. 빼지 않으면
팔로워가 자기 비용을 두 번 센다."

그 국소분을 재는 `phase_shape_local_cost`(`priced_wu_link_controller.py:275`)가
**도착이 한 줄도 없는 순수 배수 모형**이다 — `q[pid] -= service` 뿐. 게다가 현시
포화유율을 `len(movements) × movement_capacity_veh_h` 로 잡는데, `len` 은 선언된 leg
교차곱이고([[vissim-movement-leg-crossproduct]]) 용량은 **전역 스칼라 1400** 이라
`urban.capacity.per_lane` 로 심은 movement 별 맵(중앙 206.5)을 아예 안 읽는다 — **6.78배 과대**.
(1800 은 구세대 캘리브레이션 파일 값이다. 실제 쓰는 `core17legs4b_20260820` 에는
`recommended_initial_saturation_flow_vph_approach` 키가 없어 어댑터 기본값 1400 으로 떨어진다.)
그리고 같은 함수가 주기도 전역 150 으로 나눈다 — SC7 은 실제 120 이다.

**실런 리플레이 실측(sc7native seed13 t=3600)**: 채점된 현시 63개 중 **40개(63.5%)**
에서 `local − base_local` 이 **정확히 0**. phased 채점기로는 **1개(1.6%)**.
→ 그 63.5% 에서 가격이 `(전역 ΔTTT)/δ`, 즉 외부효과가 아니라 전역 한계값 전체가 된다.
규약이 막으려던 이중계상 그 자체이고, [[vissim-flat-local-cost-vertex]] 의 꼭짓점
래칫 증상과 같은 뿌리다.

**Why:** 2026-08-22 에 `local_cost_model: "phased"` 로 고친 것은 **정련(refinement)뿐**
이다. 가격 계산(`_refresh_phase_prices` 720·737행)은 그 갈아타기에서 빠졌고 스위치가
그 자리에 닿지 않는다. 그래서 "예전에 고쳤다" 는 기억은 맞지만 절반만 맞다.

**How to apply:** 어댑터 사본 `vissim_stackelberg_adapter_qprice_20260825.py` 가
`_refresh_phase_prices` 를 재정의해 같은 phased 채점기를 쓴다(`phase_price.price_local_model:
"phased"`, 없으면 no-op). 국소항 계산은 전부 부모 프로세스라 몽키패치가 프로세스 경계를
못 넘는 함정([[vissim-workstation-state]] 의 spawn 규칙)에 닿지 않는다 — 워커는 전역
롤아웃만 돈다. ctx 는 `_phase_ctx_cache` 에 있고 `__getstate__` 가 빼고 피클한다.

검증: 스위치 꺼짐 = 녹색 68개 비트 동일(PASS). 켜짐 = 68개 중 **34개** 변화
(SC1002 p3 +42초, SC11 p3 −36초). 비용은 +3초/결정.

## 실런 결과 (2026-08-25)

`allfix_20260825` = A + B(신호별 녹색상자) + C1(정지대수 큐분할) 합본, sc7native 위.

```
TTT 4783.9   무제어 4808.1 대비 **-24.2**   ← 제어가 무제어를 이긴 첫 결과
             sc7native 4829.4 대비 -45.5
```

런 평균으로 옛 배수 모형의 뭉갬은 **80.9%**(최소 65% 최대 100%)로 단일 결정의 63.5%보다
나쁘다 — 가격 국소항은 채점 현시의 5분의 4에서 항등 0 이었다.

기전 확인: SC1002 p3(스필백 접근로를 방류하는 현시)가 sc7native 에서 **23/37 결정을
하한 22.67s** 에 묶여 있었는데 allfix 에서 **1/37** 로 줄고 평균 36.76 → 60.92 가 됐다.

**단, 격차 -24.2 는 무제어 5시드 산포 σ=50.7 의 절반이다.** 시드 13 하나뿐이라
짝지은 시드 검정(14~17) 전에는 논문에 못 쓴다.
