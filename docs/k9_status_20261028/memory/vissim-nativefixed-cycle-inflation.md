---
name: vissim-nativefixed-cycle-inflation
description: native-fixed 팔은 깨끗한 대조가 아니다 — 동시현시 SC 의 합성 주기가 팽창한다(SC5 240s · SC7 213s · SC16 116s). 2026-08-24
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-24T12:15:23.205Z
---

2026-08-24. `--controller native-fixed` 는 `signal_group_actuation_plan_v3.json` 의
`axis_green_sec` 를 그대로 집행한다. 17/17 신호가 계획과 정확히 일치하고 offset 은 전부
0 이다(검증 완료). **그런데 주기가 계획대로 안 나온다.**

러너의 합성 주기는 `녹색합 + 3 x 살아있는 현시수`(VBS:867-871)다. 그래서 동시현시로
녹색합이 주기를 넘는 SC 는 주기가 팽창한다:

    SC5   97+23+101+25 = 246  ->  **240초** (native 150)
    SC7   91+90+0+24   = 205  ->  **213초** (native 120)
    SC16  63+17+27+0   = 107  ->  **116초** (native 150)
    나머지 14개                    150초

**함의.** `nativefixed_20260824` TTT 5009.1 (무제어 4808.1 대비 +201.0) 을
"native 분할 + offset 0 의 비용"으로 읽으면 안 된다. 그 안에 세 SC 의 주기 팽창이
섞여 있다 — 주기가 1.6배면 그 교차로의 주기당 서비스 횟수가 그만큼 줄고, 인접 신호와
주기가 달라 연동 자체가 성립하지 않는다.

시간 서명이 단조 증가라 지속적 서비스 결손과 맞는다:

    구간          nativefixed−무제어   merge−무제어
    600-1800            +7.3            −2.1
    1800-3000          +39.0           +13.3
    3000-4200          +68.5            +6.8
    4200-5400          +86.1           +12.6

**그래도 남는 사실 하나.** 같은 집행 채널(offset 0 · 순차 4현시 · 부분창)에서
**제어(merge 4838.7)가 native 분할(5009.1)보다 170.4 좋다.** 최적화 자체는 작동한다.

깨끗한 대조를 만들려면 주기 150 에 들어가는 14개 SC 만 native 분할로 고정하고
SC5·SC7·SC16 은 제어에 맡기는 팔이 필요하다(주기 팽창 없이 offset·부분창 효과만 남는다).

관련: [[vissim-why-control-loses]] [[vissim-seed-variance]]
