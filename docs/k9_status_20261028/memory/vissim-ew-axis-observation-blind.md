---
name: vissim-ew-axis-observation-blind
description: "검지 매핑이 동서 접근로를 못 봐서 p3·p4 가 영구히 큐 0 — 컨트롤러가 동서를 green_min 으로 굶긴 근본 원인 (2026-08-22 특정, 생성기 + 후처리기로 수정)"
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-21T17:09:59.865Z
---

2026-08-22 특정. **검지 매핑이 동서 접근로를 관측하지 못한다.** 이게 컨트롤러가
무제어보다 나쁜(TTT +7.95%) 근본 원인이다.

**사슬**
1. `scripts/generate_real_world_distributed_players.py:911` 의 movement 필터가
   `_p1`·`_p2` 만 검사한다. 그 파일에 `_p3`/`_p4` 는 **한 번도 안 나온다**.
2. `grid_topology.movement_phase_id` 는 2026-08-12 부터 4현시다 —
   **p1=남북직진 · p2=남북좌 · p3=동서직진 · p4=동서좌**. 필터의 의미가 그날 조용히 바뀌었다:
   NS 링크는 좌회전(p2)을 잃고, **EW 링크는 남북 좌회전으로 귀속된다**(축도 회전도 틀림).
3. 결과: p3·p4 가 17개 신호 전부·전 시점 큐 **정확히 0**. 리더는 빈 현시를 굶기는
   비용이 0 이라 `green_min` 으로 밀고 남북에 몰아준다.
   예: SC1 `[76.0, 20.7, 20.7, 20.7]`, SC5_p3 는 고정계획 **101초**(망 최대)를 20.7초로.

**실측 대조 (t=2400s)** — VISSIM 정지차 남북 861 / 동서 702, 모델 큐 합 879.65.
모델이 본 건 남북뿐이다. 동서 비중은 혼잡과 함께 **34% → 45% → 55%** 로 커진다.
"모델이 큐를 −40~50% 과소예측한다"고 부르던 게 사실은 **망의 절반이 없는 것**이었다.
그래서 `sat600`·`lanes330`·`trust`·`gate` 가 전부 몇 %밖에 못 움직였다.

**부수 확인**
- 하류막힘(스필백)은 5개 시점 전부 0건. `bay_m` 을 25 m 까지 낮춰도 880대 중 25대뿐 —
  동서 큐가 없으니 하류가 찰 일이 없다. `bay` 레버는 이 버그를 고친 뒤에 다시 봐라.
- `RW_QUEUE_ORIGIN_FILTER` 는 같은 버그의 **부분 우회책**이었다. origin 이 하나도
  안 맞으면 안 좁히는데, 깨진 링크가 정확히 그 경우라 무력화된다.
- 동서 접근로 50개 **전부 SG 1-8 이 구동**한다. 미드블록(SG 9+) 규칙과 무관하고,
  대상 65개 링크가 전부 이미 `observable_links` 에 있다 — 관측 범위는 그대로고 귀속만 바뀐다.

**수정 (둘 다 했다)**
- 근원: 생성기에 `AXIS_PHASE_SUFFIXES` = NS→(p1,p2), EW→(p3,p4) 도입.
  `prune_network_movements_to_observed_axes` 의 2현시 가정도 같이 고쳤다.
- 정밀: `scripts/build_link_to_movements_approach.py` — 정지선 링크를
  **자기 접근로 movement 에만** 귀속(권역 정본 기준). 산출물
  `detector_local_mapping_distributed_core17legs4c_20260822.json`,
  설정 팔 `..._core17legs4b_phasefix_20260822.json`.

**검산**: 현시분포 p1 246/p2 115/**p3 0/p4 0** → p1 120/p2 54/**p3 103/p4 40**.
권역 정본 일치 36/72 → 68/72. 고정계획 녹색과 모델큐의 순위상관 **+0.009 → +0.315**.

관련: [[vissim-workstation-state]] [[vissim-plant-fidelity-three-layers]]
[[vissim-player-territory-canonical]] [[vissim-resolve-live-controller-first]]
