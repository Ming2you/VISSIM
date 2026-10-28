---
name: vissim-default-stack-20260904
description: 새 정본 canon_default_20260904 — 도시 큐/접근 분리 재배선으로 제어 적자 +386.5 소멸(8339.0 → 7946.2)
metadata: 
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-09-04T01:51:04.559Z
---

**정본 = `evaluation/configs/canon_default_20260904.json`.** 이전 `canon_outflow_d00_x18_20260901`
(= 8339.0)은 재현용으로만 보존.

```
arm_qsplit_x18_20260904   7946.2   ← head window 없이 낸 값
무제어 nc_out             7952.4     −6.2   (sigma 50.7 안 = 동률)
제어 기준선 qcread         8339.0   −392.8   (−4.71%, 7.7 sigma)
```
교차검증: 전체속도 21.7→23.4, 정지 2858→2597, 최종재차 7293→6328, 고속속도 30.3→35.0,
램프 전폐 readback RED 84/296 → 14/296. 차를 지워 만든 값이 아니다(TTT 는 VISSIM 실차량 계수).

## 켠 것 — 전부 정합성 수정이라 결과와 무관하게 기본

```
0 link_to_origins +9         미표현 161.32 → 0.0 veh/결정 (실런 37결정 전부 0.0)
                             31·10479·10483·10703 → SC1001_W_out, 68·10645·10682 → SC1004_W_out,
                             78 → in_SC2001_W, 259 → SC5_to_SC11. .fzp 상류 위상 유도 + 용량 검산.
                             고속(2·24·26·74)·램프미터 8개는 도시 저류 대상이 아니라 제외.
1 urban.queue.contiguous     정지선 **차로별** 연속 walk + head window 30 m.
                             walk 를 끊는 것은 공간 갭이 아니라 움직이는 차량이다
                             (갭 20/40/100/inf 전부 동일값). 차로 풀링 금지(36.8% 대 48.2%).
2 urban.arrival.seed_...     잔차를 urban_arrival_buffer 에 이봉 tau — 이동 15 s / 정지-비큐 105 s.
3 warm_start 자동 억제        시더 ON 이면 어댑터가 끈다(82링크 492.4 veh 이중 예약 방지)
4 urban.tau.storage_lanes_fzp 저류 차로 보정 149 → 204개
```

## 핵심 발견 (게이트 0, VISSIM 없이)

어댑터가 `urban_arrival_buffer` 를 **한 번도 쓴 적이 없었다.** 관측 저류를 싣고 수요 0 으로
90 substep(=450 s) 굴리면 `movement_queue` 가 **정확히 0.00**. 즉 큐/접근 분리가 결정하던 것은
"대기 대 접근"이 아니라 **"서비스 가능 재고 대 지평 내 폐기"** 였다.

```
시더 OFF   s1..s90 전부 0.00
시더 ON    s6=728.99  s31=1321.60  s90=866.87   (예약 170항목 2,506 veh)
```

## 안 건드린 것과 그 이유

- **`_link_delay_steps` 의 "부호 역전"은 고치지 마라.** docstring 이 그 설계를 명시한다 —
  도착 지점이 링크 끝이 아니라 **큐 꼬리**라 거리는 여유공간이 맞고, occupied 를 쓰던 것이
  이전 버그였다. `lane_delay_correction` 이 속도에 차로수를 곱해
  `(차로별 여유거리)/(이동차속도)` 와 **항등**을 만든다(근사가 아니다).
- **큐카운터를 split 소스로 쓰지 마라.** 속성이 QLen/QLenMax/QStops 셋뿐이고 **대수 속성이 없다**
  (probe 확정). QLen 은 미터·최장차로라 차로수 곱하면 2.12배 과대, 카운터별 m/veh 가 2.04~7.09
  (3.5배 산포)로 단일 상수가 없다. 500 m 포화가 링크 420 에 닿는 유일 카운터를 76% 구간에서 자른다.
  정당한 용도는 **스필백 탐지**뿐. [[vissim-queue-projection-fixed-fraction]] 갱신.

## 남은 것

- head window 적용 후 walk/정지 = 0.717 (.fzp 참조 0.569). 장링크는 맞는다:
  32 = 0.127(참조 0.080) · 30 = 0.224(0.161) · 66 = 0.386(0.449).
- 재기준선 2런(nc_canon / ctl_canon, 2026-09-04) 이후가 진짜 성적표.
- 다음 검정 1순위: `urban.queue.window_stat` (순시 r 0.674 → 30초 창평균 0.967, 62/62 승).

관련: [[vissim-gate-outside-config-is-dead]] [[vissim-onramp-coupling-promoted]]
