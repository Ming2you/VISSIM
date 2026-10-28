---
name: vissim-offset-hurts-guard-was-right
description: "offset 은 τ 를 고쳐도 안 산다 — τ+offset 이 τ 단독보다 +90.3 악화, churn 은 오히려 56% 증가. 다음 용의자는 전이비용"
metadata:
  node_type: memory
  type: project
  originSessionId: ab16ebe2-114b-4182-9877-9977f80eb5f9
  modified: 2026-08-25T00:00:00.000Z
---

**2026-08-25 정정. 이전 판("offset 켜니 +43.8 악화, 가드가 옳았다")은 틀린 해석이었다.**
사용자가 "네이티브 .sig 대 offset 뺀 것이 200 차이였는데 왜 못 메우냐" 고 물어 다시 팠다.

## 이 망은 네이티브로 연동이 걸려 있고, 우리는 그걸 0 으로 뭉갠다

`.sig` 45개 프로그램 **전부** offset 이 0 이 아니다(ms 단위, 150000=150s).
활성 inpx `modi_eval_userfix_20260814e.inpx` 가 바인딩하는 값 — 제어 대상 17개:

```
SC1 131 · SC5 5 · SC6 1 · SC7 36 · SC11 61 · SC12 50 · SC16 29
SC101 125 · SC105 35 · SC107 138 · SC108 112 · SC109 111 · SC1001~1005 각 75   [s]
```

`_n4dr150` 변종이 존재하는 이유가 **주기를 150 으로 통일해 연동을 성립시키기 위해서**다.

그런데 `default_20260825` 의 action CSV 는 **signal 행 561개 전부 offset 0** 이다.
러너 `ApplyRuntimeSignals`(run_real_world_stackelberg_controller.vbs:1595)가
`pos = FMod(simSec + offset, cycle)` 로 SG 창을 놓고, `sigOffset` 기본값이 0.0(:888)이다.
제어 대상 SC 는 .sig 프로그램이 아예 안 돈다 — 우리가 SigState 를 직접 쓴다.
**즉 17개 신호가 전부 절대시각에 동기화된다. 설계된 연동이 사라진다.**

## 그래서 offarm 은 offset 의 가치를 잰 실험이 아니다

`0`(연동 파괴) 대 `모델 격자 offset`(역시 비네이티브)의 비교였다. 어느 쪽도 네이티브
협조를 복원하지 않는다. 실제로 offarm 이 고른 offset 은 네이티브와의 원형거리가
**평균 42.6 s** 로 무작위 기대 37.5 s 보다 오히려 멀다 — 모델은 연동을 재발견하지 못했다.

측정 자체는 유효하다(거부 0/37, 254/561 행에 0 아닌 offset). 다만 결론이 달라진다:
**"offset 이 해롭다" 가 아니라 "비연동 상태에서 임의 offset 을 얹으면 해롭다".**

## 파생: default 의 -84.2 는 연동 페널티를 물고 낸 값이다

```
nocontrol_native_20260821  4809.3   ← .sig 네이티브(signal 행 자체를 안 쓴다)
nativefixed_20260824       5009.1   ← 네이티브 현시를 우리 러너로 재생 = offset 0
                           -----
                           199.8    ← 사용자가 기억한 그 200
default_20260825           4723.9   ← 우리 green 제어, 역시 offset 0
```
사용자 직관이 맞다. 우리는 연동을 버리고도 84.2 를 이겼다. **연동 여유분은 미측정이다.**
(199.8 은 주기 팽창과 섞여 있어 순수 offset 몫은 아직 못 가름 — [[vissim-nativefixed-cycle-inflation]])

## 주기는 대부분 이미 맞다 — 연동을 복원할 수 있다

플랜 주기 실측(청산 = AMBER 3 + ALL_RED **0**, 5 아니다):
**13/17 이 정확히 150.0 s** 로 네이티브와 같다. 표류하는 넷만 예외 —
SC7 123 · SC16 116 (고정), SC107 139.1~150(4종) · SC109 140.4~150(3종) (결정마다 변동).

**How to apply:** 다음 실험은 **네이티브 offset 표를 강제로 싣는 팔**이다. offarm 어댑터의
강제표 기구(FORCED_ARM_TABLE_KEY + `RW_OFFSET_WRITER=test_only`)를 그대로 쓰고 표만
네이티브 값으로 바꾼다. 150 그룹 13개는 그대로, SC7·SC16 은 주기비로 환산, SC107·SC109 는
주기가 흔들려 별도 취급. 이것이 "연동 복원" 을 격리한다.
`offset_keep_margin 0.005` 가드는 **최적화된** offset 에 대한 것이고 고정 네이티브 표에는
적용되지 않는다 — 강제표 경로는 가드를 안 탄다.


---

## 2026-08-26 추가 — **τ 를 고쳐도 offset 은 안 살아난다**

가설은 "τ(링크 통과시간)가 맞으면 플래툰 위상이 맞아 offset 최적점이 매끄럽게 움직이고
churn 이 준다" 였다. **반증됐다.**

```
tau_20260826      4688.4   -119.7   τ 만 (offset 꺼짐)   ← 현 최선
default_20260825  4723.9    -84.2
tauoff_20260826   4778.7    -29.4   τ + offset  ->  **tau 대비 +90.3 악화**
nocontrol_s13     4808.1     +0.0
```

offarm(τ 없이 offset)이 default 대비 +43.8 이었는데 **τ 를 얹으니 +90.3 으로 더 나빠졌다.**

실험은 유효하다 — plan_reject **0건**, signal 행 629 중 **308개(49%)** 에 0 아닌 offset(9종),
τ 스위치 37결정 전부 활성(moving_speed 1.0 · lane_delay 1.0 · τ 평균 107.0 s).

**churn 이 줄기는커녕 늘었다:**
```
                전이 횟수   평균 점프   최대
offarm (τ 없음)    204      26.8 s    75.0 s
tauoff (τ 있음)  **318**    29.8 s    75.0 s      +56%
```

**Why:** τ 는 플랜트 충실도를 확실히 개선한다(도시 저류 정합 86.7→75.0%, TTT −35.5).
그런데 그 개선이 offset 을 살리지 않는다. 남은 용의자는 **전이 비용**이다 — 러너가
`pos = FMod(simSec + offset, cycle)` 로 즉시 점프시키므로, 주기의 20% 를 평균으로 하는
점프가 318회면 offset 값이 옳든 그르든 손해다. 실무 컨트롤러는 short-way 전이로
주기당 10~20% 로 제한한다.

**How to apply:** offset 다음 수순은 τ 가 아니라 **슬루 제한**이다.
`offset_marginal_price_trust_sec`(wu_faithful_follower.py:1664)이 지금 `None` 이라
제한이 아예 없고, 후보 격자도 1/8 주기(18.75 s)라 한 칸이 이미 한계치다.
그 둘을 같이 조여야 한다. **τ 는 offset 과 분리해서 단독으로 승격하는 것이 맞다.**
