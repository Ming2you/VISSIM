---
name: vissim-approach-blind-audit-20260905
description: 전수조사 — origin 에는 관측 차량이 있는데 movement 가 0 을 받는 곳이 6신호 30 movement. 전체 귀속의 33.5%가 외래 origin 에서 온다
metadata:
  node_type: memory
  type: project
---

2026-09-05. [[vissim-sc5-sc6-vertex-gridlock]] 의 SC5 실명이 단발이 아닌지 전수조사했다.
기준: `link_to_origins`(링크 -> origin)와 `link_to_movements`(링크 -> movement)를
`urban_movements[*].origin` 으로 대조. 재차는 C 팔 t>=3600 평균.

## 세 층위

```
1. origin 이 **하나도 안 겹치는** 링크        4개 / 매핑 링크 1057
   1210014303  SC101_to_SC5   -> SC102/SC11/in_SC5_S movement 로 감   185.0 대
   1220014203  SC5_to_SC101   -> 동상                                 125.0
   21          SC108_to_SC109 -> SC7_to_SC108/in_SC108_S                5.1
   259         SC5_to_SC11    -> 동상                                   2.0

2. 외래 귀속 비율 (전체)      외래 4262.5 / (자기 8465.6 + 외래) = **33.5%**

3. origin 에는 관측이 있는데 movement 수신 0     **30 movement · 6 신호**
```

## 실명 목록 (origin 관측 > 20대, 수신 <= 0.5)

```
361.1  SC1001_W_to_on{W,E}          in_SC1001_W       SC1001_p3
282.9  SC1004_S_to_on{W,E}          in_SC1004_S       SC1004_p2
186.0  SC5_W_SC101_to_*  (4개)      SC101_to_SC5      SC5_p3 · p4
125.0  SC101_E_SC5_to_*  (4개)      SC5_to_SC101      SC101_p3 · p4
110.9  SC1001_S_SC1003_to_on{W,E}   SC1003_to_SC1001  SC1001_p2
 45.0  SC11_W_SC1_to_*   (5개)      SC1_to_SC11       SC11_p3 · p4
 41.9  SC1004_W_to_on{W,E}          in_SC1004_W       SC1004_p3
 33.1  SC1004_E_SC1005_to_on{W,E}   SC1005_to_SC1004  SC1004_p3
 23.1  SC1_E_SC11_to_W_SC105        SC11_to_SC1       SC1_p3
신호별  SC1 7 · SC1004 6 · SC11 5 · SC1001 4 · SC5 4 · SC101 4
```

**두 부류다.**
- **접근로 leg 실명** (SC5_W_SC101 · SC101_E_SC5 · SC11_W_SC1 · SC1_E_SC11) — 전부 **p3/p4** 다.
  [[vissim-ew-axis-observation-blind]] 와 같은 부류이고 2026-08-22 수정이 다 못 걷었다.
  컨트롤러가 흔들릴 때마다 그 현시를 green_min 으로 굶는 직접 원인.
- **on_ramp movement 실명** (`*_to_on{W,E}`, 2026-09-03 승격분) — SC1001 · SC1004 에 몰린다.
  이쪽은 승격 당시 관측 배선이 안 따라간 것으로 보인다. [[vissim-onramp-coupling-promoted]] 확인 필요.

## 왜 중요한가

242/492 movement 가 아무 관측도 못 받는데, 그 대부분은 leg 교차곱 산물이라 정상이다
([[vissim-movement-leg-crossproduct]]). 위 30개는 **origin 에 실제 차량이 있는데도 0** 인 것이라
정상 아닌 부분집합이다. q0 = 0 인 현시는 국소 모형에서 "서비스할 게 없다"로 보이고,
가격이 반대로 말해도([[vissim-sc5-sc6-vertex-gridlock]]: SC5 b2 +0.11 = p1 줄여라) 국소가 이긴다.

관련: [[vissim-sc5-sc6-vertex-gridlock]] [[vissim-ew-axis-observation-blind]]
[[vissim-movement-leg-crossproduct]] [[vissim-onramp-coupling-promoted]]
