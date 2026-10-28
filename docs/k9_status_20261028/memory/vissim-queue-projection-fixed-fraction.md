---
name: vissim-queue-projection-fixed-fraction
description: 큐 투영은 이중계상 없음. 다만 고정 저류분율 0.35/0.50 이라 합계는 맞고 분포가 무너진다
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-24T21:59:09.511Z
---

`vissim_stackelberg_adapter.py:~2626` 의 큐 투영은 **이중계상이 없다**.
`storage_count = count × storage_fraction`, `queue_count = count − storage_count`,
그 다음 `assigned = count × weight / weight_sum` 으로 **정규화**해 배분한다.
(2026-08-24 에 정규화를 빠뜨리고 재구성해 "이중계상" 이라고 잘못 판단한 적이 있다.)

문제는 **`storage_fraction` 이 고정 상수**라는 것이다 — 내부 0.35 / off-ramp 0.50.
그리고 movement 큐는 `count`(링크 위 전 차량)로만 만들어진다. `link_stopped_counts` 는
이미 수집돼 있지만 **저류 몫의 정지 비율에만** 쓰이고 큐 배정은 한 번도 안 본다.

**실측(conv seed13 t=3600).** 고정 0.65 는 **망 합계로는 맞다** — 관측 2,724대 중
정지 1,799대(66.0%). 그래서 총량 점검으로는 절대 안 잡힌다. 그런데 분포가 무너져 있다:

```
막힌 곳 과소                        뚫린 곳 과대
SC7    정지 97% 모델 65%  −32pt     SC1004  17% 65%  +48pt
SC106       93%      65%  −28pt     SC1003  30% 65%  +35pt
SC101       85%      65%  −20pt     SC109   36% 65%  +29pt
SC5         83%      65%  −18pt     SC1001  37% 65%  +28pt
```

균일 분율은 신호 **내부**에서 공통 배수라 상쇄되지만, 현시 배분은 count 대 stopped 에서
실제로 뒤집힌다 — SC1005 p3 는 count 로 29.7대인데 정지차는 **1.4대**(점유 −36.7pt).
신호별 최대 변동: SC1005 36.7 / SC1003 29.5 / SC11 28.0 / SC6 24.4 pt. 큰 신호는 덜
흔들린다(SC1002 5.1 / SC1 1.3) — 거기는 이미 거의 다 정지다.

**Why:** 모델 큐가 구속력이 없다고 넘겨짚기 쉬운데 **큰 신호에서는 구속한다** —
SC5 최대 movement 큐 48.1대 대 주기 방류능 8.8대, SC1002 는 123.1 대 8.8. 통제 신호
16개 중 5개가 구속이다. 그러니 "큐가 작아서 아무것도 안 바뀐다" 는 설명은 틀렸다.
실제 병목은 하류의 가격 국소항이다([[vissim-price-local-term-drain]]).

**How to apply:** 어댑터 사본 `vissim_stackelberg_adapter_qstop_20260825.py` 가
`RW_STOPPED_SPLIT=1` 일 때 `storage_fraction = 1 − stopped/count` 로 갈아탄다(관측 없으면
종전 고정값). 질량은 거의 안 바뀌고(1,771 → 1,799) 배분만 바뀐다.
`RW_QUEUE_ORIGIN_FILTER` 는 별개 스위치이고 여전히 기본 꺼짐이다.

## 더 아까운 채널이 있다 — `link_queue_tail_pos_m`

VBS 가 매 결정 **정지차 중 가장 상류에 있는 차의 위치**를 링크별로 잰다
(`run_real_world_stackelberg_controller.vbs:2781-2785`, 정지차만 대상, `min(pos)`).
큐가 정지선에서 뒤로 얼마나 뻗었는지를 직접 잰 값이다. **기능 소비처가 0개**다 —
진단에 적히고(3060행) 비영 개수만 세고(3046행) 끝이다.

실측(sc7native 37결정, 정지차 있는 링크-결정 표본 3,479개): 꼬리 위치 중앙 105.4 m,
그리고 **16.8%** 가 링크 시작 15 m 안까지 뻗어 있다 = 상류 교차로로 스필백.
집중돼 있다 — SC1002 의 `E_SC101` 접근로는 링크 6개가 29~31 결정 중 거의 매번 그렇다.
그 SC1002 p3 가 큐의 66.6%(193.9대)를 담고도 녹색 22.67초에 묶여 있던 자리다.

**Why:** 모델은 스필백을 자기 저류 점유(`s_eff`)로 내부 추정만 하고 **관측과 대조하지
않는다**. 큐 대수보다 큐 **길이**가 필요한 곳이 정확히 여기다.
