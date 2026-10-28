---
name: vissim-lever-activation-roadmap
description: green 을 살려낸 6항목 진단서를 offset·metering·VSL 에 각각 적용하고 통합하는 것이 다음 목표 (2026-08-25 사용자 지시)
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-25T05:02:20.020Z
---

**사용자 지시(2026-08-25):** *"default 결과 본 다음에는 offset 팔 거야. 그리고 metering
이랑 vsl 각각 lever도 파서, 우리가 결국 green을 activate 시켰던 것처럼 metering이랑 vsl,
offset에 어떤 문제가 있고 이걸 어떻게 해결할지 각각 파서, 통합하는 걸 목표로 할 거야."*

순서: **default 결과 → offset → metering·VSL → 통합**.

## green 을 살려낸 6항목 진단서 — 이걸 각 레버에 그대로 적용한다

각 항목의 뜻은 green 에서 실제로 나온 것이 정의한다.

1. **컨트롤러가 그 레버를 움직이는가** — offset 은 561개(17×33) 전부 0 을 의도한다.
2. **목적함수가 반응하는가(죽은 항)** — green 은 가격 국소항이 도착 없는 배수 모형이라
   채점 현시의 **80.9%** 에서 미분이 0 이었다([[vissim-price-local-term-drain]]).
3. **탐색 상자가 물리 도달범위와 맞는가** — green 은 78 대 101([[vissim-green-max-78-wall]]).
   metering 은 전례가 있다(N_UF [0,5000] 대 물리 7200, 2026-08-20 수정).
4. **주문이 플랜트에 도달하는가(실행채널)** — green 은 0.4433 배로 깎였다
   ([[vissim-midblock-plan-pollution]]).
5. **관측이 수집만 되고 안 쓰이는가** — `link_stopped_counts` 는 죽어 있었고
   `link_queue_tail_pos_m` 은 소비처 0개([[vissim-queue-projection-fixed-fraction]]).
6. **심어 놓고 안 읽는 값(배선)** — `clamp_primary_green` 의 signal 인자, movement 용량 맵.

**Why:** green 에서 이 여섯 중 넷이 동시에 걸려 있었고, 고치니 무제어 대비 −84.2 가 나왔다
([[vissim-default-stack-20260825]]). 같은 양식이 다른 레버에도 반복되는지가 핵심 질문이고,
반복된다면 그것은 개별 버그가 아니라 **이 시스템의 구조적 결함**이다.

**How to apply:** 개별 ablation 대신 **합본으로 재고 지면 그때 분해**한다(사용자 원칙,
기대비용 2.5런 대 3런). 팔 하나는 82분. 발사 전 리플레이로 "스위치 끄면 비트 동일" 을
반드시 확인한다 — 이 규칙이 오늘 여러 번 사고를 막았다.

**제약(되돌리기 금지):** leader obj 의 TTT 와 lever 의 marginal price 는 끌 수 없다(가중치
조절은 가능). 현시 가격도 임의로 끄지 않는다. SG 9 이상(미드블록)은 건드리지 않는다.
