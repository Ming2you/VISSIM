---
name: vissim-price-rollout-budget
description: 가격 롤아웃은 결정당 173회다(디스크 진단 43은 4배 축소 오보) — 채널 5개 내역과 계수가 새는 이유
metadata:
  node_type: memory
  type: project
---

2026-09-04 계측(`scripts/probe_price_channels_20260904.py`, `probe_price_disk_match_20260904.py`).
"가격이 너무 빨리 계산된다" 는 의심에서 시작해 전수 계측했다. **아무것도 안 건너뛴다.**

## 결정당 전역 롤아웃 173회

```
green   p1 **스칼라** lo/hi     17 x 2 = 34   _global_rollout_metrics_with_green
meter    4 램프 x 2 + base     =      9      _global_rollout_metrics_with_metering
offset  17 x 2                =     34      _global_rollout_ttt_with_offset
vsl     16 세그 x 2            =     32      _global_rollout_ttt_with_vsl
                        레버 합       109     (계수기 wu_price_rollout_count 가 세려는 대상)
현시가격 63 단측 + base 1       =     64      _global_ttt_with_phases  (별도 계수기)
                        총           173
```

**green 채널은 현시 벡터가 아니라 p1 스칼라 하나다.** 그래서 17x4x2=136 이 아니라 34 다.
현시별 차원은 `_refresh_phase_prices` 가 따로 낸다 — 그쪽은 **단측**(+δ)이고 base 를 공유해
17x4x2=136 이 아니라 63+1=64 다. 방향이 예산보존 재배분이라 −δ 는 나머지 현시 +δ 들의
평균과 중복이다.

롤아웃 1회 = 3 horizon x 30 substep = **urban 90 substep · freeway 45 · movement 386**
(`_phase_green_fraction` 호출 34,633회/롤아웃 = 90 x 386 으로 정확히 맞는다).
직렬 0.673 s/롤아웃. 173 x 0.673 = 116 s 인데 실제 결정 wall 은 98.7 s — 병렬이 필수다.

## 디스크 진단 43 은 오보다 (4배 축소)

```
디스크 wu_price_rollout_count  43  =  green 34 + meter 9
실제                          173
```

`_price_rollout_count += 1` 이 `_global_rollout_ttt_with_vsl`(:757)·`_..._with_offset`(:774)
안에 있는데, 이 둘은 **워커 프로세스로 디스패치된다**(`_price_worker_vsl`·`_price_worker_offset_walk`).
워커에서 올린 계수는 부모로 안 돌아온다. green 은 `_green_price_rollouts` 가 부모에서
`+= len(tasks)` 로 세고, meter 는 부모 직렬이라 살아남는다. 현시가격 64 는
`_phase_price_rollout_count` 로 따로 있고 **action JSON 에 아예 안 실린다.**

→ 런 결과물만 보면 43 으로 보인다. 실제는 173 이다. 고치려면 워커 반환값에 계수를 싣거나
부모에서 `len(tasks)` 로 세라. [[vissim-gate-outside-config-is-dead]] 규칙 3과 같은 부류.

## 검증 — 값은 비트 일치한다

오프라인 재현(충실 하네스, 직렬)의 레버 가격 52개가 실런 디스크와 **최대절대차 3.8e-14**.
green 17 · meter 4 · vsl 16 · offset 15 전부 완전일치. 즉 실런도 173회 다 돌았다.
`price_lite` · `price_spsa` 는 둘 다 꺼져 있다(진단에 키 자체가 없음).

## 가격 크기가 채널마다 1000배 갈린다

```
green   1e-2  (0.005 ~ 0.085)
offset  1e-3  (0.0003 ~ 0.008)
vsl     1e-3  (4e-5 ~ 0.008)
meter   1e-4~1e-5  (1.4e-5 ~ 2.7e-4)   <- green 의 약 1/1000
```
네 채널 모두 31결정 내내 매번 변한다(고정 0개). 미터링 레버가 안 움직이는 것과
[[vissim-offset-rejected-not-dead]] 를 다시 볼 때 이 비대칭이 출발점이다.

## 오프라인 하네스는 `offline_harness_20260904.py` 를 써라

`probe_far_components_20260901.build_cfg_and_state` 는 main() 설치 중 **롤아웃에 닿는 4종**을
빠뜨린다 — `apply_nonexistent_movement_beta_zero` · `install_boundary_out_ramp_split` ·
**`install_monitor_fixed_signal_runtime_patch`**(green→유량 변환 자체) ·
`install_local_observation_runtime_guards`. 그걸로 잰 값은 실런과 다른 plant 다.

관련: [[vissim-phase-price-surrogate-leak]] [[vissim-workstation-state]]
[[vissim-gate-outside-config-is-dead]]
