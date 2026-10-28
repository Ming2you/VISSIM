---
name: vissim-flat-local-cost-vertex
description: 현시가격 정련의 local 비용이 항등 0 이라 목적함수가 순수 선형 → 해가 상자 꼭짓점으로 래칫. 가격 OFF 는 답이 아니다(균등 뭉갬). 2026-08-22
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-22T04:50:37.374Z
---

2026-08-22 규명. 컨트롤러가 녹색을 극단 배분하는 진짜 이유.

**구조.** 팔로워 `solve()` 는 GNE 를 푼 뒤 `apply_phase_price_refinement` 로
`green_times` 를 **덮어쓴다** — 실측 매 결정 17개 신호 중 평균 **13.7개(80%)**,
덮임 0개인 결정은 33개 중 0개.

정련 채점기 `phase_shape_local_cost` 가 보는 것과 못 보는 것:

| | GNE 팔로워 `rollout_local_tts_phased` | 정련 `phase_shape_local_cost` |
|---|---|---|
| 도착 | 플래툰 `arr_by_substep` | **없음** |
| 용량 | `cap_flow_of[m]` (per-movement) | **`len(movements) x 1400`** |
| 스필백 | `s_eff0` | **없음** |
| offset | substep 겹침 | **없음** |

**왜 항등 0 인가.** `sat[pid] = len(movements) x movement_capacity_veh_h` 라
SC1_p1 이 20 movement x 1400 = **28,000 veh/h** 다(SC1 전체 실측 통과는 2,640 veh/h).
곡률 임계 = `0.005556 x sat` = **155.6 veh** 인데 SC1 큐는 순간 29 · 창평균 25 ·
창최대 56 이다. 어떤 큐도 첫 스텝에 다 빠져 **모든 녹색 벡터에서 local = 0.0000**
(SC1·SC6·SC12). 그러면 `cost = 0 + weight x Σ p_i (g_i - ref_i)` — 순수 선형이다.

**녹색 예산이 단체(simplex)다.** `green_max 78 = 138 - 3 x green_min 20` 이라
상자 꼭짓점이 정확히 "한 현시 78 · 나머지 20". 선형함수는 항상 꼭짓점이 최적.

**신뢰영역은 못 막는다.** `exchange_steps_sec (6.0, 2.0)` 이 결정당 이동을 8초로
묶지만(실측 이동합 16.0초가 331회로 최빈), **보폭을 묶지 목적지를 안 묶는다.**
가격 부호가 매 결정 같으면 래칫이다 — SC1 은 5결정 만에 `[76.0, 20.7, 20.7, 20.7]`
에 닿고 **15결정 연속 이동량 0.00** 으로 갇혔다. 전체 결정의 27%가 이동량 0.
코드 주석(`stackelberg_wu_metered.py:148`)이 "trust 없는 무제한 가격은 +10.3% 폭주
(선형 월권)"이라고 이미 경고하는데, 보폭형 신뢰영역으로는 부족했다.

**가격을 끄는 건 답이 아니다** (실측). `nophaseprice_20260822`:
극단화는 죽었다(하한부착 29.0→9.1, 꼭짓점신호 2.3→0.7, 결정당 이동 185.7→6.9초).
그런데 TTT 는 +7.95% → **+7.25%** 로 거의 안 움직였다 — `local` 이 평평하니 교환이
개선을 못 찾고 시드(균등)에 머문다. SC5 가 고정계획 `[97,23,101,25]` 인데
`[34.0, 34.7, 34.7, 34.7]` 로 뭉갠다. 즉 **가격 ON = 한쪽 끝 / 가격 OFF = 균등 뭉갬**,
둘 다 나쁜데 이유가 정반대다. 필요한 건 가격 제거가 아니라 **상대편(곡률)** 이다.

**수정 ①** (2026-08-22 구현). tuning `phase_price.local_cost_model: "phased"` 로
정련도 `rollout_local_tts_phased` 를 쓰게 한다. 기본 `"drain"` 은 비트 동일.
`_offset_green_fractions_vec`(현시 벡터를 받는 gf) 를 `wu_faithful_follower` 에 추가.
리플레이 실측: 결정 wall **137.2 → 145.5초(+6%)**, 15/17 신호 적용,
**ctx 캐시 적중 0 = 정련은 결정당 1회만 돈다** → 병렬화 불필요.
함정: `solve()` 의 `demand` 는 리스트일 수 있다(첫 스모크가 이걸로 `fallback_fixed`).

관련: [[vissim-ew-axis-observation-blind]] [[vissim-workstation-state]]
[[vissim-parent-run-launch-traps]]
