---
name: vissim-tau-fix-record
description: "τ(링크 통과시간) 수정이 신기록 4688.4 (−119.7). 이동차 기준 속도 + 차로 차원 보정"
metadata:
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-26T00:00:00.000Z
---

**2026-08-26. τ 를 고쳐 새 최선을 냈다.**

```
tau_20260826       4688.4   **-119.7 (-2.49%)**   새 최선
default_20260825   4723.9     -84.2               직전 최선
nocontrol_s13      4808.1      +0.0               기준 (5시드 sigma 50.7)
```

## 무엇을 고쳤나 — 둘 다 `urban_queue_model.py:629-636` 의 distance/speed 한 줄

1. **속도에 정지차가 섞여 있었다.** 러너의 링크속도는 `speedSum/count` 인데 count 가 링크 위
   **전 차량**이다(run_real_world_stackelberg_controller.vbs:3131). 정지차(임계 1.0 km/h)가
   분모만 키운다. 그런데 그 속도를 쓰는 유일한 곳(`_link_delay_steps`)의 거리는
   `available`(= 링크 **여유공간**)이라 **큐가 이미 빠져 있다.** 거리에서는 뺐는데 속도에서는
   안 뺐다. -> `speedSum/(count − stopped)`. 실측 3,340대 중 정지 1,483(44%), 배수 평균 5.3.
2. **거리가 차로수 배였다.** distance = available[veh] × 6 m 인데 available 이 전 차로 합계다.
   보정(`_apply_lane_delay_correction`)은 이미 있었고 **기본 꺼짐**이었다. 실측 배수 중앙 2.69.

```
τ 평균  202.5 -> 108.3 s   ·  p90 460 -> 160 s  ·  horizon(450s) 초과 11.9% -> 3.8%
플래툰 도착 위상(τ mod 150s) 중앙 90 -> 80 s
도시 저류 예측 정합 중앙 86.7% -> 75.0%,  p90 141.3% -> 100.0%
```

**세 지표가 전부 같은 방향이다** — 예측 정합 · 위상 · TTT. 이런 일치는 드물다.

## 함정 둘

- **집계층만 보면 반대로 보인다.** 집계 예측오차는 10.4% -> 14.2% 로 **나빠진다**. 상쇄로
  가려지는 층이라 그렇다. τ 가 지배하는 층은 도시 저류(공간)다.
- **감사 도구의 도시층이 조용히 죽어 있었다.** `audit_rollout_spatial_accuracy.py:278` 이
  `want_sec.add(float(anchor + 60 * k))` 로 제어주기를 60 s 하드코딩한다. 우리는 150 s 라
  저류 관측이 전량 걸러지고도 `status=PASS` 가 나온다. 이것 때문에 그동안 3층 지표 중
  도시층을 실제로 본 적이 없을 가능성이 크다. 그리고 `rollout_from_anchor` 는
  `install_config_switches` 와 `install_measured_turn_beta` 를 **안 부른다** — config 스위치로
  켜는 팔은 감사에 안 실린다.

**How to apply:** 사본 `vissim_stackelberg_adapter_tau_20260825.py` + config
`..._tau_20260825.json`(`urban.tau.moving_only` · `urban.tau.lane_delay_correction`).
**offset 과 분리해서 승격해라** — [[vissim-offset-hurts-guard-was-right]] 대로 τ+offset 은
τ 단독보다 나쁘다. 그리고 −35.5(default 대비)는 시드 sigma 50.7 안이므로
**시드 14~17 짝지음 재현이 논문 인용 전 필수**다.
